"""Saved voice -> real checkpoint -> moving LIBERO -> Stop/hold/resume, independent judge."""

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--start-audio", type=Path, required=True)
parser.add_argument("--stop-audio", type=Path, required=True)
parser.add_argument("--task-id", type=int, choices=(0, 1, 2), default=0)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
protocol_path = (
    Path(__file__).resolve().parents[1]
    / "integrations/openpi-client/fixtures/libero-live-pc-smoke.json"
)
protocol_bytes = protocol_path.read_bytes()
protocol = json.loads(protocol_bytes)
assert args.task_id in protocol["task_ids"]
base = "http://127.0.0.1:8896"
rows = []


def get(url):
    return json.load(urllib.request.urlopen(url, timeout=10))


def post(route, body):
    request = urllib.request.Request(
        base + route, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    return json.load(urllib.request.urlopen(request, timeout=35))


def voice(path):
    started = time.monotonic()
    request = urllib.request.Request(
        base + "/transcribe", path.read_bytes(), {"Content-Type": "audio/wav"}
    )
    result = json.load(urllib.request.urlopen(request, timeout=10))
    report.setdefault("recognition", []).append(result)
    response = post("/interact", {"message": result["text"]})
    report.setdefault("voice_dispatch", []).append(
        {
            "text": result["text"],
            "response": response,
            "clip_ready_to_response_ms": (time.monotonic() - started) * 1000,
        }
    )
    return response


def poll():
    row = {
        "wall_s": time.monotonic(),
        "state": get(base + "/state"),
        "judge": get("http://127.0.0.1:8901/judge"),
    }
    rows.append(row)
    return row


report = {
    "scope": "Real warmed GPU policy; saved synthetic voice; no live microphone or hardware",
    "protocol": {
        "min_lift_m": 0.08,
        "max_translation_m": 0.01,
        "max_joint_range_rad": 0.02,
        "hold_wall_seconds": 2,
        "min_physics_seconds_exclusive": 1,
        "conversation_before_lift_trigger": True,
    },
    "passed": False,
    "task_id": args.task_id,
    "frozen_protocol": protocol,
    "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
}
try:
    start = voice(args.start_audio)
    assert start["mode"] == "start" and start["state"]["task_id"] == args.task_id, start
    assert start["state"]["pause_joint_kp"] == 300
    assert start["state"]["pause_joint_damping_ratio"] == 2
    deadline = time.monotonic() + 90
    # Exercise conversation early, before the lifted-object Stop trigger.
    while time.monotonic() < deadline:
        early = poll()["state"]
        if early["phase"] == "running" and early["policy_steps"] >= 10:
            break
        time.sleep(0.025)
    old_epoch = early["epoch"]
    before_question = early["policy_steps"]
    answer = post("/interact", {"message": "What are you doing?"})
    after_question = poll()
    assert answer["mode"] == "answer"
    assert after_question["state"]["epoch"] == old_epoch
    assert after_question["state"]["policy_steps"] >= before_question
    report["conversation"] = answer
    while time.monotonic() < deadline:
        row = poll()
        s, j = row["state"], row["judge"]
        assert s["phase"] != "failed" and not s["policy_error"], s
        assert s["phase"] != "success", (
            "Placement finished before reaching the 80 mm lift qualification trigger"
        )
        if j and j["grasp_contacts"] and j["xyz"][2] - j["initial_xyz"][2] >= 0.08:
            break
        time.sleep(0.015)
    else:
        raise AssertionError("Real policy did not reach a lifted contact grasp")
    old_epoch = s["epoch"]
    stopped = voice(args.stop_audio)
    assert stopped["mode"] == "stop" and stopped["state"]["phase"] == "paused"
    stopped_state = stopped["state"]
    hold_started = time.monotonic()
    held = [get("http://127.0.0.1:8901/stop-judge")]
    assert held[0] is not None
    while (
        time.monotonic() - hold_started < 2
        or not held
        or held[-1]["sim_time"] - held[0]["sim_time"] <= 1
    ):
        assert time.monotonic() - hold_started < 5, "Physics stalled during hold"
        row = poll()
        assert row["state"]["phase"] == "paused"
        assert row["state"]["policy_steps"] == stopped_state["policy_steps"]
        held.append(row["judge"])
        time.sleep(0.05)
    xyz = np.array([r["xyz"] for r in held])
    joints = np.array([r["joints"] for r in held])
    report.update(
        max_translation_m=float(np.max(np.linalg.norm(xyz - xyz[0], axis=1))),
        max_joint_range_rad=float(np.max(np.ptp(joints, axis=0))),
        min_lift_m=float(np.min(xyz[:, 2]) - held[0]["initial_xyz"][2]),
        all_contact_grasps=all(r["grasp_contacts"] for r in held),
        physics_time_advanced_s=held[-1]["sim_time"] - held[0]["sim_time"],
        stopped_policy_steps=stopped_state["policy_steps"],
        measured_hold_wall_seconds=time.monotonic() - hold_started,
        stop_sensor_age_ms=(stopped_state["stop_requested_wall_s"] - held[0]["sampled_wall_s"])
        * 1000,
    )
    assert report["max_translation_m"] < 0.01 and report["max_joint_range_rad"] < 0.02
    assert report["min_lift_m"] >= 0.08 and report["all_contact_grasps"]
    assert report["physics_time_advanced_s"] > 1
    # The boundary must also reject a syntactically valid late old-generation chunk.
    request = urllib.request.Request(
        "http://127.0.0.1:8901/actions",
        json.dumps({"epoch": old_epoch, "actions": [[0.0] * 7]}).encode(),
        {"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(request, timeout=5)
        raise AssertionError("Late action accepted")
    except urllib.error.HTTPError as caught:
        assert caught.code == 409
    report["stale_action_rejected"] = True
    resumed = post("/interact", {"message": "Resume, please."})
    assert resumed["mode"] == "resume"
    while time.monotonic() < deadline:
        row = poll()
        assert row["state"]["phase"] != "failed" and not row["state"]["policy_error"], row
        if row["state"]["phase"] == "success":
            assert row["judge"]["success"]
            report["resumed_success"] = True
            report["final_state"] = row["state"]
            break
        time.sleep(0.025)
    else:
        raise AssertionError("Real-policy resume did not complete within the unchanged budget")
    report["passed"] = True
except Exception as caught:
    report["error"] = repr(caught)
    raise
finally:
    valid_judges = [r["judge"] for r in rows if r["judge"] is not None]
    if valid_judges:
        report["max_observed_lift_m"] = max(j["xyz"][2] - j["initial_xyz"][2] for j in valid_judges)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "trace.json").write_text(json.dumps(rows) + "\n")
    print(json.dumps(report, indent=2))
