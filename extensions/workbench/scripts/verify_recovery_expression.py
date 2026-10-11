"""Independent local ASR/task/physics acceptance; no browser or live microphone fixture."""

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
client = httpx.Client(base_url="http://127.0.0.1:8766", timeout=30, trust_env=False)
evidence = {"voice_capture": "saved synthetic speech, not live microphone", "journeys": []}


def state():
    r = client.get("/state")
    r.raise_for_status()
    snapshot = r.json()
    with (args.output / "trace.jsonl").open("a") as stream:
        stream.write(json.dumps({"time": time.time(), "state": snapshot}) + "\n")
    return snapshot


def post(route, data=None):
    r = client.post(route, json=data or {})
    r.raise_for_status()
    return r.json()


def wait(predicate, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        s = state()
        if predicate(s):
            return s
        time.sleep(0.1)
    raise AssertionError("Acceptance condition timed out: " + json.dumps(state()))


def task(s, tid):
    return next(t for t in s["tasks"] if t["task_id"] == tid)


def finished(tid):
    return wait(lambda s: not s["busy"] and task(s, tid)["status"] not in {"pending", "running"})


def voice(name, text):
    source, wav = args.output / (name + ".aiff"), args.output / (name + ".wav")
    subprocess.run(["/usr/bin/say", "-o", str(source), text], check=True)
    subprocess.run(
        [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-i",
            str(source),
            "-ar",
            "16000",
            "-ac",
            "1",
            str(wav),
        ],
        check=True,
    )
    r = client.post("/transcribe", content=wav.read_bytes(), headers={"Content-Type": "audio/wav"})
    r.raise_for_status()
    recognized = r.json()
    evidence.setdefault("transcripts", []).append(recognized)
    return post("/chat", {"message": recognized["text"]})["task_id"]


def placement(s, name, destination):
    result = s["last_result"]
    assert result["status"] == "completed" and result["physical_success"], result
    assert result["outcome"]["distance_m"] < 0.035, result
    assert s["objects"][name][2] < 0.04
    assert s["inventory"][name] == destination, s["inventory"]


wait(
    lambda s: (
        s["model_status"] == "ready" and s["speech_input"]["status"] == "ready" and not s["busy"]
    )
)
post("/reset")
wait(lambda s: s["phase"] == "Ready" and not s["recovery"]["can_resume"])
original = post("/chat", {"message": "Bring me the screwdriver, please."})["task_id"]
before_stop = wait(lambda s: s["phase"] == "Lifting tool" and s["objects"]["screwdriver"][2] > 0.13)
post("/stop")
stopped = finished(original)
assert task(stopped, original)["status"] == "cancelled"
assert stopped["recovery"]["can_resume"] and stopped["recovery"]["tool"] == "screwdriver"
resumed = voice("resume", "Resume, please.")
assert resumed != original
complete = finished(resumed)
placement(complete, "screwdriver", "handoff tray")
assert task(complete, original)["status"] == "cancelled"
evidence["journeys"].append(
    {
        "name": "stop holding -> spoken resume -> handoff",
        "original_task": original,
        "resumed_task": resumed,
        "result": complete["last_result"],
    }
)
returned = voice("return", "Put it back.")
complete = finished(returned)
placement(complete, "screwdriver", "tool rack")
evidence["journeys"].append(
    {"name": "spoken contextual return after handoff", "result": complete["last_result"]}
)

original = post("/chat", {"message": "Bring me the wrench, please."})["task_id"]
wait(lambda s: s["phase"] == "Lifting tool" and s["objects"]["wrench"][2] > 0.13)
post("/stop")
stopped = finished(original)
assert stopped["recovery"]["tool"] == "wrench"
returned = voice("held-return", "Put it back, please.")
complete = finished(returned)
placement(complete, "wrench", "tool rack")
assert task(complete, original)["status"] == "cancelled"
evidence["journeys"].append(
    {"name": "stop holding -> spoken return -> rack", "result": complete["last_result"]}
)

before = state()
conversation = post("/chat", {"message": "What can you help me with?"})["task_id"]
expressing = wait(lambda s: s["phase"] == "Nodding" and s["busy"])
reply = expressing["messages"][-1]["content"]
post("/speak", {"message": reply})
assert wait(lambda s: s["speech"]["speaking"], timeout=5)["speech"]["last_text"] == reply
joints = []
while True:
    s = state()
    joints.append(s["robot_joints"])
    if not s["busy"]:
        break
    time.sleep(0.05)
assert np.max(np.ptp(joints, axis=0)) > 0.10, "No expressive joint motion measured"
assert s["last_result"]["status"] == "completed" and not s["last_result"]["physical_success"]
for name, xyz in before["objects"].items():
    assert np.linalg.norm(np.array(s["objects"][name]) - xyz) < 0.004
post("/speech-stop")
evidence["journeys"].append(
    {
        "name": "conversation + native speech + nod, tools undisturbed",
        "joint_excursion_rad": float(np.max(np.ptp(joints, axis=0))),
        "reply": reply,
    }
)

gesture = post("/chat", {"message": "Wave hello, please."})["task_id"]
wait(lambda s: s["phase"] == "Waving hello")
post("/stop")
finished(gesture)
resumed = voice("gesture-resume", "Resume.")
complete = finished(resumed)
assert task(complete, gesture)["status"] == "cancelled"
assert (
    complete["last_result"]["status"] == "completed"
    and not complete["last_result"]["physical_success"]
)
evidence["journeys"].append(
    {"name": "stop expression -> spoken resume", "result": complete["last_result"]}
)

post("/reset")
wait(lambda s: s["phase"] == "Ready" and not s["recovery"]["can_resume"])
missing = post("/chat", {"message": "Resume"})["task_id"]
complete = finished(missing)
assert (
    complete["last_result"]["status"] == "completed"
    and not complete["last_result"]["physical_success"]
)
assert "isn't a stopped task" in complete["last_result"]["message"]
evidence["journeys"].append(
    {"name": "reset clears recovery; absent resume is honest", "result": complete["last_result"]}
)
(args.output / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
print(
    "PASS: original cancelled tasks remain cancelled; spoken resume/return deliver physically; "
    "conversational speech/nod leaves tools untouched; expression resumes; reset clears recovery."
)
