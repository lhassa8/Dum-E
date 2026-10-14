"""Audit the complete fresh carry-governor cohort from preserved raw measurements."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--physics", type=Path, required=True)
args = parser.parse_args()


def read(path):
    return json.loads(path.read_text())


def stats(values):
    return {"n": len(values), "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95, method="higher")),
            "maximum": float(max(values))}


report = read(args.folder / "report.json")
protocol = read(args.folder / "protocol.json")
assert protocol == report["protocol"]
assert len(report["episodes"]) == len(protocol["episodes"]) == 12
for name, key in (("verify_libero_carry_governor.py", "actor_sha256"),
                  ("libero_runtime.py", "runtime_sha256"),
                  ("libero_carry_governor.py", "governor_sha256")):
    assert hashlib.sha256((args.folder/name).read_bytes()).hexdigest() == protocol[key]
assert report["metadata"]["device"].startswith("cuda")
assert report["metadata"]["checkpoint_objects_sha256"] == (
    "450f2d7b90db37ff3db84074fd9a67ba49fba05c1c482c430b1d1c5de8772084")
counts = {p: {"attempted": 0, "triggered": 0, "hold_passed": 0,
              "native_success": 0, "full_passed": 0}
          for p in ("baseline", "carry-governor")}
seen, latencies, scene_ids = set(), [], set()
for spec, result in zip(protocol["episodes"], report["episodes"], strict=True):
    assert all(result[k] == v for k, v in spec.items())
    key = (result["task_id"], result["seed"], result["variant"])
    assert key not in seen and result["error"] is None
    seen.add(key)
    directory = args.folder / f"task{key[0]}-seed{key[1]}-{key[2]}"
    assert read(directory/"result.json") == result
    terminal = result["terminal_state"]
    scene = terminal["scene_request_epoch"]
    assert scene == terminal["native_init_epoch"] and scene not in scene_ids
    scene_ids.add(scene)
    assert terminal["active_steps"] <= 220
    assert result["native_success"] == (terminal["phase"] == "success")
    for row in read(directory/"trace.json"):
        state = row["state"]
        if state["physics_ready"]:
            assert state["native_init_epoch"] == state["scene_request_epoch"] == scene
        # /state and /judge are sequential HTTP reads, not an atomic observation.
    held = read(directory/"hold.json")
    if result["trigger_reached"]:
        dense = read(directory/"dense-hold.json")
        assert len(dense) == result["native_hold_samples"] > 400
        measured = dense+held
        assert all(s["native_init_epoch"] == scene for s in measured)
        assert all(held[0]["sim_time"]-1e-10 <= s["sim_time"] <=
                   held[-1]["sim_time"]+1e-10 for s in dense)
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
    calls = read(directory/"calls.json")
    assert sorted(c["draw"] for c in calls) == list(range(len(calls)))
    latencies.extend(c["client_ms"] for c in calls)
    by_draw = {c["draw"]: c for c in calls}
    fresh = False
    for submission in read(directory/"submissions.json"):
        call = by_draw[submission["draw"]]
        assert submission["actions"] == call["actions"]
        assert not call.get("discarded_after_stop") and not call.get("discarded_at_terminal")
        if submission["epoch"] == result.get("resume_epoch"):
            assert call["requested_at_wall_s"] >= result["resume_wall_s"]
            fresh = True
    assert fresh == result["fresh_resume_inference"]
    assert result["development_passed"] == (
        result["hold_passed"] and result["native_success"] and fresh)
    counter = counts[key[2]]
    counter["attempted"] += 1
    for field, source in (("triggered", "trigger_reached"), ("hold_passed", "hold_passed"),
                          ("native_success", "native_success"),
                          ("full_passed", "development_passed")):
        counter[field] += int(result[source])

records = [json.loads(line) for line in (args.physics/"governor.jsonl").read_text().splitlines()]
records = [r for r in records if r["native_init_epoch"] in scene_ids]
assert records
for record in records:
    alpha = record["alpha"]
    assert 0 <= alpha <= 1 and record["grip_command"] > 0
    assert np.allclose(record["applied_delta"], np.array(record["requested_delta"])*alpha,
                       atol=1e-12)
    assert record["budget_rad"] == .01 and record["reserve_fraction"] == .5
    assert record["torque_low"] == [-80]*5+[-12]*2
    assert record["torque_high"] == [80]*5+[12]*2
    if not record["reserve_unavailable"]:
        assert record["predicted_scaled_range_rad"] <= .01+1e-12
audit = {"audit": "pass", "episodes": 12, "outcomes": counts,
         "client_inference_ms": stats(latencies),
         "governor_alpha": stats([r["alpha"] for r in records]),
         "governor_extra_ms": stats([r["elapsed_ns"]/1e6 for r in records]),
         "scope": "Dense physics and saved command audit; no voice/hardware qualification"}
(args.folder/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
print(json.dumps(audit))
