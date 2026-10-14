"""Recalculate the frozen pre-Stop replay and inspect recorded governor inputs."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--source-run", type=Path, required=True)
parser.add_argument("--reference", type=Path, required=True)
args = parser.parse_args()
report = json.loads((args.folder/"report.json").read_text())
protocol = report["protocol"]
assert protocol["carry_governor"] and len(report["trials"]) == 20
assert hashlib.sha256((args.folder/"probe_libero_braking.py").read_bytes()).hexdigest() == (
    protocol["actor_sha256"])
assert hashlib.sha256((args.folder/"libero_carry_governor.py").read_bytes()).hexdigest() == (
    protocol["governor_sha256"])
reference = json.loads(args.reference.read_text())
original = {r["case"]: r for r in reference["trials"] if r["profile"]["name"] == "baseline"}
counts = {"baseline": 0, "carry-governor": 0}
decisions, elapsed = 0, []
seen = set()
for result in report["trials"]:
    profile, case = result["profile"]["name"], result["case"]
    assert (case, profile) not in seen
    seen.add((case, profile))
    directory = args.folder/(case+"-"+profile)
    assert json.loads((directory/"result.json").read_text()) == result
    assert result["error"] is None and result["goal_capture_error_rad"] == 0
    assert result["max_prebrake_reference_error"] <= 1e-6
    samples = json.loads((directory/"samples.json").read_text())
    assert len(samples) == result["sample_count"]
    initial = json.loads((args.source_run/case/"hold.json").read_text())[0]["initial_xyz"]
    xyz = np.array([s["xyz"] for s in samples])
    joints = np.array([s["joints"] for s in samples])
    metrics = {
        "min_lift_m": float(np.min(xyz[:, 2])-initial[2]),
        "max_translation_m": float(np.max(np.linalg.norm(xyz-xyz[0], axis=1))),
        "max_joint_range_rad": float(np.max(np.ptp(joints, axis=0))),
        "all_grasp_contacts": all(s["grasp_contacts"] for s in samples),
    }
    assert all(metrics[k] == result[k] for k in metrics)
    passed = (metrics["min_lift_m"] >= .08 and metrics["max_translation_m"] <= .01
              and metrics["max_joint_range_rad"] <= .02 and metrics["all_grasp_contacts"]
              and result["physical_window_s"] > 1)
    assert passed == result["physical_window_passed"]
    counts[profile] += int(passed)
    if profile == "baseline":
        for key in (*metrics, "sample_count", "physical_window_s"):
            assert result[key] == original[case][key], (case, key)
    records = json.loads((directory/"governor.json").read_text())
    assert bool(records) == (profile == "carry-governor")
    for record in records:
        delta = np.array(record["requested_delta"])
        applied = np.array(record["applied_delta"])
        alpha = record["alpha"]
        assert 0 <= alpha <= 1 and np.allclose(applied, delta*alpha, atol=1e-12)
        assert record["grip_command"] == record["source_action"][6] > 0
        assert record["period_s"] == .05
        jacobian = np.array(record["jacobian"])
        velocity = np.linalg.pinv(jacobian, rcond=1e-4) @ (delta/.05)
        assert np.allclose(velocity, record["joint_velocity_proposal"], atol=1e-12)
        mass = np.array(record["mass_matrix"])
        assert mass.shape == (7, 7) and np.linalg.eigvalsh(mass).min() > 0
        momentum = mass @ velocity
        bias = np.array(record["bias"])
        low, high = np.array(record["torque_low"]), np.array(record["torque_high"])
        assert np.array_equal(low, [-80]*5+[-12]*2)
        assert np.array_equal(high, [80]*5+[12]*2)
        reserve = np.where(momentum >= 0, bias-low, high-bias)*.5
        blocked = bool(np.any((reserve <= 0) & (np.abs(momentum) > 1e-12)))
        assert blocked == record["reserve_unavailable"]
        if not blocked:
            speed = float(np.max(np.abs(velocity)))
            duration = float(np.max(np.abs(momentum)/np.maximum(reserve, 1e-12)))
            scaled = .5*speed*duration*alpha*alpha+record["ideal_joint_peak_s"]*speed*alpha
            assert abs(scaled-record["predicted_scaled_range_rad"]) < 1e-12
            assert scaled <= .01+1e-12
        elapsed.append(record["elapsed_ns"]/1e6)
        decisions += 1
assert len(seen) == 20 and all((c, p) in seen for c in protocol["cases"] for p in counts)
result = {"audit": "pass", "trials": 20, "physical_passes": counts,
          "governor_decisions": decisions, "source_no_trigger_episodes": 2,
          "scope": "Recorded-state/command audit; modeled range is not a physical guarantee"}
(args.folder/"audit.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps(result))
