"""Independently audit all frozen OpenVLA physical episodes and server replies."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--server", type=Path, required=True)
parser.add_argument("--physics", type=Path, required=True)
args = parser.parse_args()


def read(path):
    return json.loads(path.read_text())


report = read(args.folder/"report.json")
protocol = read(args.folder/"protocol.json")
assert report["protocol"] == protocol and len(report["episodes"]) == 6
assert len(protocol["episodes"]) == 6 and protocol["max_active_steps"] == 220
for name, key in (("verify_openvla_physical.py", "actor_sha256"),
                  ("libero_runtime.py", "runtime_sha256")):
    assert hashlib.sha256((args.folder/name).read_bytes()).hexdigest() == protocol[key]
metadata = read(args.server/"metadata.json")
assert metadata == report["metadata"]
assert metadata["device"] == "cuda:0" and metadata["dtype"] == "torch.bfloat16"
for name, key in (("serve_openvla_local.py", "actor_sha256"),
                  ("openvla_inference_utils.py", "bootstrap_sha256")):
    assert hashlib.sha256((args.server/name).read_bytes()).hexdigest() == metadata[key]
server = [json.loads(s) for s in (args.server/"inference.jsonl").read_text().splitlines()]
server = server[protocol["server_trace_offset"]:]
assert not any("error" in s for s in server)
server = [s for s in server if s["request_id"] >= 0]
all_calls, seen = [], set()
selected_expected, terminal_steps = {}, 0
counts = {"attempted": 6, "triggered": 0, "hold_passed": 0, "native_success": 0,
          "fresh_resume": 0, "combined_passed": 0}
for spec, result in zip(protocol["episodes"], report["episodes"], strict=True):
    assert all(result[k] == v for k, v in spec.items())
    key = (spec["task_id"], spec["repeat"])
    assert key not in seen and result["error"] is None
    seen.add(key)
    folder = args.folder/f"task{key[0]}-repeat{key[1]}"
    assert read(folder/"result.json") == result
    terminal = result["terminal_state"]
    terminal_steps += terminal["policy_steps"]
    scene = terminal["scene_request_epoch"]
    assert terminal["native_init_epoch"] == scene and terminal["active_steps"] <= 220
    assert terminal["motion_profile"] == "baseline" and not terminal["carry_governor_experiment"]
    assert result["native_success"] == (terminal["phase"] == "success")
    for row in read(folder/"trace.json"):
        state = row["state"]
        if state["physics_ready"]:
            assert state["native_init_epoch"] == state["scene_request_epoch"] == scene
    held = read(folder/"hold.json")
    if result["trigger_reached"]:
        dense = read(folder/"dense-hold.json")
        assert len(dense) == result["native_hold_samples"] > 400
        measured = dense+held
        assert all(s["native_init_epoch"] == scene for s in measured)
        times = np.array([s["sim_time"] for s in dense])
        assert np.allclose(np.diff(times), .002, atol=1e-9)
        assert abs(times[0]-held[0]["sim_time"]) < 1e-9
        assert abs(times[-1]-held[-1]["sim_time"]) < 1e-9
        xyz = np.array([s["xyz"] for s in measured])
        joints = np.array([s["joints"] for s in measured])
        metrics = {
            "min_hold_lift_m": min(s["xyz"][2]-s["initial_xyz"][2] for s in measured),
            "max_hold_translation_m": float(np.max(np.linalg.norm(xyz-xyz[0], axis=1))),
            "max_hold_joint_range_rad": float(np.max(np.ptp(joints, axis=0))),
            "all_hold_grasp_contacts": all(s["grasp_contacts"] for s in measured),
        }
        assert all(metrics[k] == result[k] for k in metrics)
        assert result["hold_wall_s"] >= 2
        assert result["hold_sim_s"] == held[-1]["sim_time"]-held[0]["sim_time"] > 1
        passed = (metrics["min_hold_lift_m"] >= .08
                  and metrics["max_hold_translation_m"] <= .01
                  and metrics["max_hold_joint_range_rad"] <= .02
                  and metrics["all_hold_grasp_contacts"])
        assert passed == result["hold_passed"]
    else:
        assert not held and not result["hold_passed"]
    calls = read(folder/"calls.json")
    assert sorted(c["draw"] for c in calls) == list(range(len(calls)))
    all_calls.extend(calls)
    by_draw = {c["draw"]: c for c in calls}
    fresh = False
    parts_by_draw = {}
    for submission in read(folder/"submissions.json"):
        call = by_draw[submission["draw"]]
        part = submission["part"]
        assert part in (0, 1)
        expected = call["actions"][:5] if part == 0 else call["actions"][5:]
        assert submission["actions"] == expected
        assert len(submission["actions"]) <= 5
        parts_by_draw.setdefault(submission["draw"], []).append(part)
        assert submission["state"]["epoch"] == submission["epoch"]
        assert submission["state"]["queued_actions"] <= 5
        base_step = submission["state"]["policy_steps"]
        for index, action in enumerate(submission["actions"], 1):
            selection_key = (scene, submission["epoch"], base_step+index)
            assert selection_key not in selected_expected
            selected_expected[selection_key] = action
        assert np.array(call["actions"]).shape == (8, 7)
        assert not call.get("discarded_after_stop") and not call.get("discarded_at_terminal")
        if submission["epoch"] == result.get("resume_epoch"):
            assert call["requested_at_wall_s"] >= result["resume_wall_s"]
            fresh = True
    assert all(parts in ([0], [0, 1]) for parts in parts_by_draw.values())
    assert fresh == result["fresh_resume_inference"]
    assert result["development_passed"] == (
        result["hold_passed"] and result["native_success"] and fresh)
    for target, source in (("triggered", "trigger_reached"), ("hold_passed", "hold_passed"),
                           ("native_success", "native_success"),
                           ("fresh_resume", "fresh_resume_inference"),
                           ("combined_passed", "development_passed")):
        counts[target] += int(result[source])
assert len(all_calls) == len(server)
for call, reply in zip(all_calls, server, strict=True):
    assert call["draw"] == reply["request_id"]
    assert call["actions"] == reply["actions"]
    assert call["server_ms"] == reply["server_ms"]
    assert call["observation_sha256"] == reply["observation_sha256"]
native_selected = 0
for line in (args.physics/"physics.jsonl").read_text().splitlines():
    row = json.loads(line)
    if row.get("source") != "policy":
        continue
    key = (row["native_init_epoch"], row["selected_epoch"], row["policy_steps"])
    assert row["action"] == selected_expected[key]
    native_selected += 1
assert native_selected == terminal_steps


def timing(field):
    values = [c[field] for c in all_calls]
    return {"n": len(values), "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95, method="higher")), "maximum": max(values)}


audit = {"audit": "pass", "outcomes": counts, "client_ms": timing("client_ms"),
         "native_selected_policy_actions": native_selected,
         "server_ms": timing("server_ms"),
         "scope": "Six known-layout repetitions; no voice, workshop or hardware qualification"}
(args.folder/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
print(json.dumps(audit))
