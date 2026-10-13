"""Saved Stop -> cancellation -> measured physics hold, resume and rack placement."""

import argparse
import json
import time
from pathlib import Path

import httpx
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--audio", type=Path, required=True)
parser.add_argument("--url", default="http://127.0.0.1:8876")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
client = httpx.Client(base_url=args.url, trust_env=False, timeout=30)
trace = []


def state():
    s = client.get("/state")
    s.raise_for_status()
    row = s.json()
    trace.append({"wall_s": time.monotonic(), "state": row})
    return row


def post(route, payload=None):
    r = client.post(route, json=payload or {})
    r.raise_for_status()
    return r.json()


def wait(predicate, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        row = state()
        if predicate(row):
            return row
        time.sleep(0.03)
    raise RuntimeError("Physical condition timed out")


def completed(task_id):
    row = wait(
        lambda s: (
            not s["busy"]
            and any(t["task_id"] == task_id and t["status"] == "completed" for t in s["tasks"])
        )
    )
    assert row["last_result"]["physical_success"]
    assert row["last_result"]["outcome"]["distance_m"] < 0.035
    return row


try:
    initial = state()
    assert not initial["busy"] and all(v == "tool rack" for v in initial["inventory"].values())
    task_id = post("/interact", {"message": "Bring me the screwdriver."})["task_id"]
    before = wait(lambda s: s["phase"] == "Lifting tool" and s["objects"]["screwdriver"][2] > 0.13)
    (args.output / "before.jpg").write_bytes(client.get("/frame.jpg").content)
    started = time.monotonic()
    response = client.post(
        "/transcribe",
        content=args.audio.read_bytes(),
        headers={"Content-Type": "audio/wav", "X-Dume-Voice-Mode": "interrupt"},
    )
    response.raise_for_status()
    recognized = response.json()
    assert recognized["text"].strip().lower().rstrip(".!?") == "stop"
    asr_finished = time.monotonic()
    post("/stop")
    cancel_finished = time.monotonic()
    stopped = wait(lambda s: not s["busy"] and s["phase"] == "Stopped")
    observed_stopped = time.monotonic()
    assert stopped["recovery"]["can_resume"] and stopped["gripper_command"] < 128
    hold_rows = []
    hold_start = time.monotonic()
    while time.monotonic() - hold_start < 2:
        hold_rows.append(state())
        time.sleep(0.05)
    hold_end = time.monotonic()
    (args.output / "held.jpg").write_bytes(client.get("/frame.jpg").content)
    joints = np.array([s["robot_joints"] for s in hold_rows])
    xyz = np.array([s["objects"]["screwdriver"] for s in hold_rows])
    assert all(s["gripper_command"] < 128 for s in hold_rows)
    assert min(xyz[:, 2]) - initial["objects"]["screwdriver"][2] > 0.08
    resumed = completed(post("/interact", {"message": "Resume."})["task_id"])
    (args.output / "handoff.jpg").write_bytes(client.get("/frame.jpg").content)
    assert any(t["task_id"] == task_id and t["status"] == "cancelled" for t in resumed["tasks"])
    returned = completed(post("/interact", {"message": "Put it back."})["task_id"])
    assert returned["inventory"]["screwdriver"] == "tool rack"
    report = {
        "scope": "saved synthetic clip ready -> ASR -> HTTP Stop; excludes live capture and pause",
        "sample_size": 1,
        "recognition": recognized,
        "asr_http_ms": (asr_finished - started) * 1000,
        "cancel_http_ms": (cancel_finished - asr_finished) * 1000,
        "clip_ready_to_cancel_response_ms": (cancel_finished - started) * 1000,
        "cancel_response_to_observed_stopped_ms": (observed_stopped - cancel_finished) * 1000,
        "hold_samples": len(hold_rows),
        "hold_wall_s": hold_end - hold_start,
        "joint_range_rad": np.ptp(joints, axis=0).tolist(),
        "max_tool_displacement_m": float(np.max(np.linalg.norm(xyz - xyz[0], axis=1))),
        "min_tool_height_m": float(min(xyz[:, 2])),
        "resume": resumed["last_result"],
        "return": returned["last_result"],
        "note": "Stopped means cancellation state; assess settling from the joint/tool trace.",
    }
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
finally:
    (args.output / "trace.json").write_text(json.dumps(trace) + "\n")
    client.close()
