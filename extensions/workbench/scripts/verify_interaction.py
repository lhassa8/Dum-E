"""Saved speech -> task-aware dialogue -> verified tool change with interruption."""

import argparse
import json
import subprocess
import time
from pathlib import Path

import httpx
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
client = httpx.Client(base_url="http://127.0.0.1:8766", timeout=90, trust_env=False)
evidence = {
    "capture": "saved synthetic speech and actual ASR, not live microphone",
    "interactions": [],
}
audio = {}
for name, text in [
    ("fetch", "Bring me the screwdriver."),
    ("question", "What are you doing?"),
    ("change", "Actually bring me the wrench instead."),
    ("stop", "Stop."),
    ("resume", "Resume, please."),
    ("return", "Put it back."),
]:
    aiff, wav = args.output / f"{name}.aiff", args.output / f"{name}.wav"
    subprocess.run(["/usr/bin/say", "-o", str(aiff), text], check=True)
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(aiff),
            "-ar",
            "16000",
            "-ac",
            "1",
            str(wav),
        ],
        check=True,
    )
    audio[name] = wav.read_bytes()


def state():
    response = client.get("/state")
    response.raise_for_status()
    s = response.json()
    with (args.output / "trace.jsonl").open("a") as file:
        file.write(json.dumps({"time": time.time(), "state": s}) + "\n")
    return s


def post(route, data=None):
    r = client.post(route, json=data or {})
    r.raise_for_status()
    return r.json()


def wait(predicate, limit=120):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        s = state()
        if predicate(s):
            return s
        time.sleep(0.06)
    raise AssertionError("Condition timed out: " + json.dumps(state()))


def task(s, tid):
    return next(t for t in s["tasks"] if t["task_id"] == tid)


def voice(name, interrupt=False):
    started = time.monotonic()
    r = client.post(
        "/transcribe",
        content=audio[name],
        headers={
            "Content-Type": "audio/wav",
            "X-Dume-Voice-Mode": "interrupt" if interrupt else "request",
        },
    )
    r.raise_for_status()
    recognized = r.json()
    result = (
        post("/stop")
        if name == "stop"
        else post("/interact", {"message": recognized["text"], "source": "voice"})
    )
    evidence["interactions"].append(
        {
            "name": name,
            "recognized": recognized,
            "response": result,
            "asr_plus_dispatch_ms": (time.monotonic() - started) * 1000,
        }
    )
    return result


wait(
    lambda s: (
        not s["busy"] and s["model_status"] == "ready" and s["speech_input"]["status"] == "ready"
    )
)
post("/reset")
wait(lambda s: s["phase"] == "Ready" and s["last_intent"] is None)
original = voice("fetch")["task_id"]
before = wait(lambda s: s["phase"] == "Lifting tool" and s["objects"]["screwdriver"][2] > 0.13)
answer = voice("question", True)
after = state()
assert answer["mode"] == "conversation" and "lifting" in answer["message"].lower()
assert before["job_id"] == after["job_id"] and task(after, original)["status"] == "running"
assert before["gripper_command"] < 128 and after["gripper_command"] < 128
change = voice("change", True)
assert change["mode"] == "change"
changed_id = change["task_id"]
returning = wait(
    lambda s: s["busy"] and s["phase"].startswith("Returning screwdriver before wrench")
)
assert returning["gripper_command"] < 128
assert task(returning, original)["status"] == "cancelled"
voice("stop", True)
paused = wait(
    lambda s: (
        not s["busy"] and s["phase"] == "Stopped" and task(s, changed_id)["status"] == "cancelled"
    )
)
assert paused["gripper_command"] < 128 and paused["recovery"]["can_resume"]
resumed = voice("resume")["task_id"]
finished = wait(lambda s: not s["busy"] and task(s, resumed)["status"] == "completed")
assert finished["last_result"]["physical_success"]
steps = finished["last_result"]["verified_steps"]
assert [(s["object"], s["destination"], s["status"]) for s in steps] == [
    ("screwdriver", "rack", "success"),
    ("wrench", "handoff", "success"),
]
assert all(s["distance_m"] < 0.035 for s in steps)
assert (
    task(finished, original)["status"] == "cancelled"
    and task(finished, changed_id)["status"] == "cancelled"
)
assert finished["inventory"]["screwdriver"] == "tool rack"
assert finished["inventory"]["wrench"] == "handoff tray"
return_id = voice("return")["task_id"]
returned = wait(lambda s: not s["busy"] and task(s, return_id)["status"] == "completed")
assert (
    returned["last_result"]["physical_success"] and returned["inventory"]["wrench"] == "tool rack"
)
assert (
    np.linalg.norm(np.array(returned["objects"]["hammer"]) - np.array(before["objects"]["hammer"]))
    < 0.004
)
evidence.update(
    original_task=original,
    changed_task=changed_id,
    resumed_task=resumed,
    completed_change=finished["last_result"],
    return_result=returned["last_result"],
)

# Exercise actual general-model dialogue, and withdraw a specific request whether
# its delivery is still running or has just finished during the answer.
hammer_id = post("/interact", {"message": "Bring me the hammer."})["task_id"]
before_joke = wait(lambda s: s["phase"] == "Lifting tool" and s["objects"]["hammer"][2] > 0.13)
started = time.monotonic()
joke = post("/interact", {"message": "Tell me a short joke about robots."})
after_joke = state()
assert joke["mode"] == "conversation" and joke["intent"]["action"] == "answer"
assert before_joke["job_id"] == after_joke["job_id"]
assert task(after_joke, hammer_id)["status"] in {"running", "completed"}
evidence["general_dialogue"] = {
    "response": joke,
    "elapsed_ms": (time.monotonic() - started) * 1000,
    "task_status_on_response": task(after_joke, hammer_id)["status"],
}
withdrawn = post("/interact", {"message": "Don't bring me the hammer."})
assert withdrawn["mode"] == "change" and withdrawn["intent"]["action"] == "return"
hammer_back = wait(
    lambda s: not s["busy"] and task(s, withdrawn["task_id"])["status"] == "completed"
)
assert (
    hammer_back["last_result"]["physical_success"]
    and hammer_back["inventory"]["hammer"] == "tool rack"
)
evidence["withdrawal"] = hammer_back["last_result"]

# A clarification asked during movement must survive the original task finishing.
clarify_original = post("/interact", {"message": "Bring me the screwdriver."})["task_id"]
wait(lambda s: s["phase"] == "Lifting tool" and s["objects"]["screwdriver"][2] > 0.13)
clarification = post("/interact", {"message": "Bring me a tool."})
assert clarification["mode"] == "conversation" and clarification["intent"]["action"] == "clarify"
wait(lambda s: not s["busy"] and task(s, clarify_original)["status"] == "completed")
chosen = post("/interact", {"message": "Wrench."})
assert chosen["intent"]["action"] == "fetch" and chosen["intent"]["object"] == "wrench"
choice_done = wait(lambda s: not s["busy"] and task(s, chosen["task_id"])["status"] == "completed")
assert (
    choice_done["last_result"]["physical_success"]
    and choice_done["interaction"]["clarification"] is None
)
assert [(s["object"], s["destination"]) for s in choice_done["last_result"]["verified_steps"]] == [
    ("screwdriver", "rack"),
    ("wrench", "handoff"),
]
evidence["clarification_across_completion"] = {
    "question": clarification,
    "choice": chosen,
    "result": choice_done["last_result"],
}
return_choice = post("/interact", {"message": "Put it back."})["task_id"]
wait(lambda s: not s["busy"] and task(s, return_choice)["status"] == "completed")
(args.output / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
print(
    "PASS: spoken question preserves moving task/grip; spoken tool change returns old tool, "
    "Stop/resume preserves both steps, contextual return and withdrawal are physically verified, "
    "general conversation preserves motion, and clarification survives task completion."
)
