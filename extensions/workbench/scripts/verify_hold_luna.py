"""Real local task bus, paused contacts and subscription cancellation; no live mic."""

import argparse
import concurrent.futures
import json
import time
from pathlib import Path

import httpx
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--url", default="http://127.0.0.1:8766")
parser.add_argument("--hold-seconds", type=float, default=32)
args = parser.parse_args()
if args.hold_seconds < 32:
    parser.error("The acceptance hold must be at least 32 seconds")
args.output.mkdir(parents=True, exist_ok=False)
client = httpx.Client(base_url=args.url, timeout=60, trust_env=False)
evidence = {"scope": "Typed HTTP requests, actual MuJoCo contacts, real Luna; no live voice",
            "journeys": [], "passed": False}


def state():
    response = client.get("/state")
    response.raise_for_status()
    snapshot = response.json()
    with (args.output / "trace.jsonl").open("a") as file:
        file.write(json.dumps({"time": time.time(), "state": snapshot}) + "\n")
    return snapshot


def post(path, **payload):
    response = client.post(path, json=payload)
    response.raise_for_status()
    return response.json()


def wait(predicate, timeout=90):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = state()
        if predicate(snapshot):
            return snapshot
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for acceptance condition")


def record(snapshot, task_id):
    return next(t for t in snapshot["tasks"] if t["task_id"] == task_id)


def finished(task_id):
    return wait(lambda s: not s["busy"] and record(s, task_id)["status"]
                not in {"pending", "running"})


def placement(snapshot, tool, location):
    result = snapshot["last_result"]
    assert result["status"] == "completed" and result["physical_success"], result
    assert result["outcome"]["distance_m"] < 0.035, result
    assert snapshot["objects"][tool][2] < 0.04
    assert snapshot["inventory"][tool] == location
    return result


def pending_question():
    with httpx.Client(base_url=args.url, timeout=60, trust_env=False) as other:
        reply = other.post("/interact", json={
            "message": "Could you explain which tools would help me with screws and nuts?"
        })
        return {"http_status": reply.status_code, "result": reply.json()}


try:
    ready = wait(lambda s: s["model_status"] == "ready" and not s["busy"])
    assert ready["language_model"] == "gpt-6-luna"
    post("/reset")
    wait(lambda s: s["phase"] == "Ready" and not s["recovery"]["can_resume"])
    for tool in ["screwdriver", "wrench", "hammer"]:
        original = post("/interact", message=f"Bring me the {tool}.")["task_id"]
        wait(lambda s: s["phase"] == "Lifting tool" and s["objects"][tool][2] > 0.13)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = None
            if tool == "screwdriver":
                future = executor.submit(pending_question)
                wait(lambda s: s["interaction"]["busy"])
                time.sleep(0.3)  # Ensure the real general-language request is underway.
                assert not future.done(), "Cloud response finished before the cancellation probe"
            stop_started = time.monotonic()
            post("/stop")
            stop_post_ms = (time.monotonic() - stop_started) * 1000
            stopped = wait(lambda s: s["phase"] == "Stopped" and not s["busy"])
            stop_observed_ms = (time.monotonic() - stop_started) * 1000
            assert record(stopped, original)["status"] == "cancelled"
            start_position = np.array(stopped["objects"][tool])
            start_joints = np.array(stopped["robot_joints"])
            grip = stopped["gripper_command"]
            hold_started = time.monotonic()
            cancelled = future.result(timeout=5) if future else None
            cancelled_reply_ms = (time.monotonic() - stop_started) * 1000 if future else None
            heights, drift = [], []
            while time.monotonic() - hold_started < args.hold_seconds:
                s = state()
                heights.append(s["objects"][tool][2])
                drift.append(float(np.max(np.abs(np.array(s["robot_joints"]) - start_joints))))
                assert s["phase"] == "Stopped" and not s["busy"]
                assert s["gripper_command"] == grip
                assert heights[-1] > 0.13
                assert drift[-1] < 0.02
                time.sleep(0.1)
            journey = {"tool": tool, "original_task": original,
                       "stop_post_ms": stop_post_ms, "stop_observed_ms": stop_observed_ms,
                       "hold_wall_seconds": time.monotonic() - hold_started,
                       "minimum_height_m": min(heights), "max_joint_drift_rad": max(drift),
                       "tool_displacement_m": float(np.linalg.norm(
                           np.array(s["objects"][tool]) - start_position))}
            evidence["journeys"].append(journey)
            if future:
                assert future.done(), "Cancelled interpretation still occupied the dialogue lane"
                cancelled = future.result()
                assert cancelled["http_status"] == 200
                assert cancelled["result"]["mode"] == "superseded"
                assert cancelled["result"]["task_id"] is None
                journey["cancelled_interpretation"] = cancelled
                journey["stop_to_cancelled_reply_ms"] = cancelled_reply_ms
                recovery = post("/interact", message="Can you see my webcam right now?")
                assert recovery["intent"]["action"] == "answer"
                assert recovery["route"] == "model"
                journey["next_model_reply"] = recovery
                assert state()["gripper_command"] == grip
        continuation = "Put it back" if tool == "wrench" else "Resume"
        resumed = post("/interact", message=continuation)["task_id"]
        completed = finished(resumed)
        journey["continued_placement"] = placement(
            completed, tool, "tool rack" if tool == "wrench" else "handoff tray"
        )
        assert record(completed, original)["status"] == "cancelled"
        if tool != "wrench":
            returned = post("/interact", message="Put it back")["task_id"]
            journey["returned_placement"] = placement(finished(returned), tool, "tool rack")
        print(f"PASS {tool}: held {journey['hold_wall_seconds']:.1f}s, "
              f"minimum height {min(heights)*1000:.1f}mm, continued/returned", flush=True)
    assert all(v == "tool rack" for v in state()["inventory"].values())
    evidence["passed"] = True
except BaseException as error:
    evidence["failure"] = repr(error)
    raise
finally:
    # Failed attempts remain reviewable, including all samples recorded before failure.
    try:
        evidence["final_state"] = state()
    finally:
        (args.output / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
        client.close()
