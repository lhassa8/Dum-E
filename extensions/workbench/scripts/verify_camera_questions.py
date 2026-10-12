"""Real speech/vision/task bus and Stop hold; no live microphone or real camera."""

import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import time
from pathlib import Path

import httpx
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--url", default="http://127.0.0.1:8795")
parser.add_argument("--vision-model", default="workbench-vision-gemma")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
client = httpx.Client(base_url=args.url, timeout=30, trust_env=False)
evidence = {
    "scope": "Saved synthetic speech,actual models/task bus/MuJoCo; no live mic or hardware",
    "passed": False,
}


def state():
    r = client.get("/state")
    r.raise_for_status()
    s = r.json()
    with (args.output / "trace.jsonl").open("a") as file:
        file.write(json.dumps({"time": time.time(), "state": s}) + "\n")
    return s


def post(path, **payload):
    r = client.post(path, json=payload)
    r.raise_for_status()
    return r.json()


def wait(predicate, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        s = state()
        if predicate(s):
            return s
        time.sleep(0.05)
    raise AssertionError("Timed out awaiting a real acceptance condition")


def completed(tid):
    return wait(
        lambda s: (
            not s["busy"]
            and any(t["task_id"] == tid and t["status"] == "completed" for t in s["tasks"])
        )
    )


def pending_camera():
    with httpx.Client(base_url=args.url, timeout=30, trust_env=False) as other:
        r = other.post("/interact", json={"message": "What do you see?"})
        r.raise_for_status()
        return r.json()


try:
    before = wait(
        lambda s: (
            s["model_status"] == "ready"
            and s["speech_input"]["status"] == "ready"
            and not s["busy"]
        )
    )
    assert before["camera"]["model"] == args.vision_model
    aiff, wav = args.output / "question.aiff", args.output / "question.wav"
    subprocess.run(
        ["/usr/bin/say", "-o", str(aiff), "What can you see on the workbench?"], check=True
    )
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
    r = client.post("/transcribe", content=wav.read_bytes(), headers={"Content-Type": "audio/wav"})
    r.raise_for_status()
    recognized = r.json()
    started = time.monotonic()
    answer = post("/interact", message=recognized["text"], source="voice")
    after = state()
    assert (
        answer["mode"] == "conversation"
        and answer["route"] == "camera"
        and answer["task_id"] is None
    )
    assert all(o["visible"] for o in answer["profile"]["tools"].values())
    assert before["tasks"] == after["tasks"] and before["job_id"] == after["job_id"]
    image = client.get("/camera.jpg")
    image.raise_for_status()
    (args.output / "snapshot.jpg").write_bytes(image.content)
    assert hashlib.sha256(image.content).hexdigest() == answer["profile"]["frame_sha256"]
    evidence["saved_speech"] = {
        "recognized": recognized,
        "answer": answer,
        "dispatch_to_observed_ms": (time.monotonic() - started) * 1000,
    }
    tid = post("/interact", message="Bring me the screwdriver.")["task_id"]
    moving = wait(lambda s: s["phase"] == "Lifting tool" and s["objects"]["screwdriver"][2] > 0.13)
    readonly = post("/interact", message="Where is the screwdriver in this image?")
    while_working = state()
    assert readonly["route"] == "camera" and readonly["intent"]["action"] == "answer"
    assert readonly["task_id"] is None and while_working["job_id"] == moving["job_id"]
    assert while_working["busy"] and while_working["gripper_command"] < 128
    evidence["while_working"] = readonly
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(pending_camera)
        wait(lambda s: s["interaction"]["busy"])
        time.sleep(0.1)
        assert not future.done(), "Camera finished before the supersession probe"
        started = time.monotonic()
        post("/stop")
        stopped = wait(lambda s: s["phase"] == "Stopped" and not s["busy"])
        evidence["stop_observed_ms"] = (time.monotonic() - started) * 1000
        cancelled = future.result(timeout=20)
        assert cancelled["mode"] == "superseded" and cancelled["task_id"] is None
        evidence["superseded_camera"] = cancelled
    joints = np.array(stopped["robot_joints"])
    grip = stopped["gripper_command"]
    began = time.monotonic()
    min_height = 1.0
    max_joint = 0.0
    while time.monotonic() - began < 32:
        s = state()
        min_height = min(min_height, s["objects"]["screwdriver"][2])
        max_joint = max(max_joint, float(np.max(np.abs(np.array(s["robot_joints"]) - joints))))
        assert (
            s["phase"] == "Stopped"
            and s["gripper_command"] == grip
            and min_height > 0.13
            and max_joint < 0.02
        )
        time.sleep(0.1)
    evidence["hold"] = {
        "wall_seconds": time.monotonic() - began,
        "minimum_height_m": min_height,
        "maximum_joint_drift_rad": max_joint,
    }
    resumed = post("/interact", message="Resume")["task_id"]
    delivered = completed(resumed)
    assert delivered["last_result"]["physical_success"]
    assert delivered["last_result"]["outcome"]["distance_m"] < 0.035
    returned = completed(post("/interact", message="Put it back")["task_id"])
    assert (
        returned["last_result"]["physical_success"]
        and returned["last_result"]["outcome"]["distance_m"] < 0.035
    )
    assert all(v == "tool rack" for v in returned["inventory"].values())
    evidence["delivery"], evidence["return"] = delivered["last_result"], returned["last_result"]
    final = post("/interact", message="What do you see?")
    assert all(o["visible"] for o in final["profile"]["tools"].values())
    evidence["final_camera"] = final
    evidence["passed"] = True
    print(
        "PASS: saved-speech camera answer uses actual snapshot;conversation preserves moving task;"
        "Stop supersedes pending vision,32s physical hold,resume and return verified.",
        flush=True,
    )
except BaseException as error:
    evidence["failure"] = repr(error)
    raise
finally:
    (args.output / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
    client.close()
