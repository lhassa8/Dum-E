"""Independently audit all frozen OpenVLA physical episodes and server replies."""

import argparse
import hashlib
import json
import subprocess
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
validation = protocol.get("stage") == "validation"
expected_count = 9 if validation else 6
assert report["protocol"] == protocol and len(report["episodes"]) == expected_count
assert len(protocol["episodes"]) == expected_count and protocol["max_active_steps"] == 220
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
counts = {"attempted": expected_count, "triggered": 0, "hold_passed": 0, "native_success": 0,
          "fresh_resume": 0, "combined_passed": 0}
for spec, result in zip(protocol["episodes"], report["episodes"], strict=True):
    assert all(result[k] == v for k, v in spec.items())
    key = (spec["task_id"], spec["repeat"], spec.get("head", "original"))
    assert key not in seen and result["error"] is None
    seen.add(key)
    folder = args.folder/f"task{key[0]}-repeat{key[1]}"
    if validation:
        folder = args.folder/f"task{key[0]}-repeat{key[1]}-{key[2]}"
    assert read(folder/"result.json") == result
    terminal = result["terminal_state"]
    terminal_steps += terminal["policy_steps"]
    scene = terminal["scene_request_epoch"]
    assert terminal["native_init_epoch"] == scene and terminal["active_steps"] <= 220
    assert terminal["motion_profile"] == "baseline" and not terminal["carry_governor_experiment"]
    if validation:
        assert terminal["initial_state_index"] == spec["initial_state_index"]
        assert terminal["require_released_placement"]
        release = read(folder/"released-placement.json")
        assert result["released_placement_passed"] == (terminal["phase"] == "success")
        if result["released_placement_passed"]:
            assert release and release["samples"]
            sample = release["samples"]
            times = np.asarray([s["sim_time"] for s in sample])
            assert times[-1]-times[0] >= .5-1e-9
            assert np.diff(times).min() >= -1e-10 and np.diff(times).max() <= .00200001
            xyz = np.asarray([s["xyz"] for s in sample])
            movement = float(np.linalg.norm(xyz-xyz[0], axis=1).max())
            error = float(np.linalg.norm(
                xyz[-1, :2]-np.asarray(sample[0]["initial_plate_xyz"])[:2]))
            assert all(s["success"] and s["plate_contact"] and not s["any_gripper_contact"]
                       for s in sample)
            assert movement == release["movement_m"] <= .005
            assert error == release["placement_xy_error_m"] <= .035
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
    if validation:
        assert all(c["head"] == spec["head"] and c["head_sha256"] ==
                   metadata["heads"][spec["head"]]["sha256"] for c in calls)
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
    if validation:
        import imageio_ffmpeg

        frames = read(folder/"frames.json")
        assert frames and all(b["wall_s"] >= a["wall_s"] for a, b in zip(frames, frames[1:]))
        lines = []
        for index, frame in enumerate(frames):
            path = (folder/"frames"/frame["file"]).resolve()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == frame["sha256"]
            assert "'" not in str(path)
            lines.append(f"file '{path}'")
            duration = frames[index+1]["wall_s"]-frame["wall_s"] if index+1 < len(frames) else .05
            lines.append(f"duration {max(duration, .001):.9f}")
        timeline = folder/"video-timeline.txt"
        timeline.write_text("\n".join(lines)+"\n")
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", "-f", "concat",
                        "-safe", "0", "-i", str(timeline), "-vsync", "vfr", "-pix_fmt", "yuv420p",
                        str(folder/"actual-validation.mp4")], check=True)
assert len(all_calls) == len(server)
for call, reply in zip(all_calls, server, strict=True):
    assert call["draw"] == reply["request_id"]
    assert call["actions"] == reply["actions"]
    assert call["server_ms"] == reply["server_ms"]
    assert call["observation_sha256"] == reply["observation_sha256"]
    if validation:
        assert call["head"] == reply["head"] and call["head_sha256"] == reply["head_sha256"]
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
if validation:
    audit["scope"] = "Three immutable heads on one validation state; no final evaluation result"
    audit["by_head"] = {head: sum(r["development_passed"] for r in report["episodes"]
                                if r["head"] == head) for head in protocol["heads"]}
(args.folder/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
print(json.dumps(audit))
