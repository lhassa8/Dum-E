"""Replay measured policy actions to qualify physics Stop; not a new policy rollout."""

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--actions", type=Path, required=True)
parser.add_argument("--audio", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
base = "http://127.0.0.1:8901"
records = []


def get(route):
    return json.load(urllib.request.urlopen(base + route, timeout=5))


def post(route, body=None):
    request = urllib.request.Request(
        base + route, json.dumps(body or {}).encode(), {"Content-Type": "application/json"}
    )
    return json.load(urllib.request.urlopen(request, timeout=5))


def poll():
    row = {"wall_s": time.monotonic(), "state": get("/state"), "judge": get("/judge")}
    records.append(row)
    return row


episode = json.loads(args.actions.read_text())["episodes"][0]
assert episode["task_id"] == 0 and episode["success"]
actions = episode["actions"]
report = {
    "scope": "Replay of earlier policy actions with continuously stepping physics; "
    "not live inference",
    "protocol": {
        "task_id": 0,
        "hold_seconds": 2,
        "min_lift_m": 0.08,
        "max_translation_m": 0.01,
        "max_joint_range_rad": 0.02,
    },
    "passed": False,
}
try:
    post("/initialize", {"task_id": 0})
    deadline = time.monotonic() + 60
    cursor = 0
    while time.monotonic() < deadline:
        row = poll()
        s, judge = row["state"], row["judge"]
        assert s["phase"] != "failed", s
        if judge and judge["grasp_contacts"] and judge["xyz"][2] - judge["initial_xyz"][2] >= 0.08:
            break
        if s["physics_ready"] and s["phase"] == "running" and not s["queued_actions"]:
            chunk = actions[cursor : cursor + 5]
            assert chunk, "Replay never reached a lifted contact grasp"
            post("/actions", {"epoch": s["epoch"], "actions": chunk})
            cursor += len(chunk)
        time.sleep(0.015)
    else:
        raise AssertionError("Lift not reached")
    old_epoch = s["epoch"]
    clip_ready = time.monotonic()
    if args.audio:
        request = urllib.request.Request(
            "http://127.0.0.1:8876/transcribe",
            args.audio.read_bytes(),
            {"Content-Type": "audio/wav", "X-Dume-Voice-Mode": "interrupt"},
        )
        recognized = json.load(urllib.request.urlopen(request, timeout=5))
        assert recognized["text"].strip().lower().rstrip(".!?") == "stop", recognized
        report["recognized"] = recognized
    cancel_started = time.monotonic()
    stopped = post("/stop")
    stop_response = time.monotonic()
    assert stopped["phase"] == "paused" and stopped["queued_actions"] == 0
    try:
        post("/actions", {"epoch": old_epoch, "actions": actions[:5]})
        raise AssertionError("Stale actions were accepted")
    except urllib.error.HTTPError as caught:
        assert caught.code == 409
    held = []
    while time.monotonic() - stop_response < 2:
        row = poll()
        assert row["state"]["phase"] == "paused"
        assert row["state"]["policy_steps"] == stopped["policy_steps"]
        held.append(row["judge"])
        time.sleep(0.05)
    xyz = np.array([r["xyz"] for r in held])
    joints = np.array([r["joints"] for r in held])
    report.update(
        cancel_http_ms=(stop_response - cancel_started) * 1000,
        clip_ready_to_cancel_ms=(stop_response - clip_ready) * 1000,
        hold_samples=len(held),
        max_translation_m=float(np.max(np.linalg.norm(xyz - xyz[0], axis=1))),
        max_joint_range_rad=float(np.max(np.ptp(joints, axis=0))),
        min_lift_m=float(np.min(xyz[:, 2]) - held[0]["initial_xyz"][2]),
        all_contact_grasps=all(r["grasp_contacts"] for r in held),
        physics_time_advanced_s=held[-1]["sim_time"] - held[0]["sim_time"],
        stale_action_rejected=True,
    )
    assert report["physics_time_advanced_s"] > 1
    assert report["all_contact_grasps"]
    assert report["min_lift_m"] >= 0.08
    assert report["max_translation_m"] < 0.01
    assert report["max_joint_range_rad"] < 0.02
    resumed = post("/resume")
    cursor = stopped["policy_steps"]
    while time.monotonic() < deadline:
        row = poll()
        s = row["state"]
        if s["phase"] == "success":
            assert row["judge"]["success"]
            report["resumed_success"] = True
            break
        assert s["phase"] != "failed", s
        if not s["queued_actions"]:
            chunk = actions[cursor : cursor + 5]
            assert chunk, "Remaining replay did not achieve task success"
            post("/actions", {"epoch": resumed["epoch"], "actions": chunk})
            cursor += len(chunk)
        time.sleep(0.015)
    else:
        raise AssertionError("Resume timed out")
    report["passed"] = True
finally:
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "trace.json").write_text(json.dumps(records) + "\n")
    print(json.dumps(report, indent=2))
