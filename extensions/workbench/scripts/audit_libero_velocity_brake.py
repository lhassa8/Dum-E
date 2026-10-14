"""Recompute frozen replay scores and every measured-velocity brake torque."""

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
assert protocol["velocity_brake"] and protocol["velocity_brake_window_s"] == .05
assert len(report["trials"]) == 20
for name, key in (("probe_libero_braking.py", "actor_sha256"),
                  ("libero_velocity_brake.py", "velocity_brake_sha256")):
    assert hashlib.sha256((args.folder/name).read_bytes()).hexdigest() == protocol[key]
reference = json.loads(args.reference.read_text())
original = {r["case"]: r for r in reference["trials"] if r["profile"]["name"] == "baseline"}
seen, durations, rates, velocity_errors = set(), [], [], []
counts = {p: 0 for p in ("baseline", "velocity-brake")}
decisions = 0
for result in report["trials"]:
    case, profile = result["case"], result["profile"]["name"]
    assert (case, profile) not in seen
    seen.add((case, profile))
    directory = args.folder/(case+"-"+profile)
    assert json.loads((directory/"result.json").read_text()) == result
    assert result["error"] is None and result["goal_capture_error_rad"] == 0
    assert result["max_prebrake_reference_error"] <= 1e-6
    assert result["entry_joint_error_rad"] <= 1e-6
    samples = json.loads((directory/"samples.json").read_text())
    assert len(samples) == result["sample_count"]
    held = json.loads((args.source_run/case/"hold.json").read_text())
    xyz = np.array([s["xyz"] for s in samples])
    joints = np.array([s["joints"] for s in samples])
    metrics = {
        "min_lift_m": float(np.min(xyz[:, 2])-held[0]["initial_xyz"][2]),
        "max_translation_m": float(np.max(np.linalg.norm(xyz-xyz[0], axis=1))),
        "max_joint_range_rad": float(np.max(np.ptp(joints, axis=0))),
        "all_grasp_contacts": all(s["grasp_contacts"] for s in samples),
    }
    assert all(metrics[k] == result[k] for k in metrics)
    assert result["physical_window_s"] == held[-1]["sim_time"]-held[0]["sim_time"] > 1
    passed = (metrics["min_lift_m"] >= .08 and metrics["max_translation_m"] <= .01
              and metrics["max_joint_range_rad"] <= .02 and metrics["all_grasp_contacts"])
    assert result["physical_window_passed"] == passed
    counts[profile] += int(passed)
    if profile == "baseline":
        for k in metrics:
            assert abs(result[k]-original[case][k]) <= 1e-6, (case, k)
        assert result["sample_count"] == original[case]["sample_count"]
    records = json.loads((directory/"torques.json").read_text())
    brake_times = []
    previous_brake = None
    for record in records:
        brake = record["velocity_brake"]
        if brake is None:
            assert record["allocated"] == record["command"]
            previous_brake = None
            continue
        assert profile == "velocity-brake"
        brake_times.append(record["sim_time"])
        mass, velocity = np.array(brake["mass_matrix"]), np.array(brake["joint_velocity"])
        assert mass.shape == (7, 7) and np.linalg.eigvalsh(mass).min() > 0
        bias = np.array(brake["bias"])
        low, high = np.array(brake["torque_low"]), np.array(brake["torque_high"])
        assert np.array_equal(low, [-80]*5+[-12]*2)
        assert np.array_equal(high, [80]*5+[12]*2)
        assert np.all(bias >= low) and np.all(bias <= high)
        momentum = mass @ velocity
        assert np.allclose(momentum, brake["momentum"], atol=1e-12, rtol=1e-12)
        reserve = np.where(momentum >= 0, bias-low, high-bias)
        moving = np.abs(momentum) > 1e-12
        feasible = float(np.min(reserve[moving]/np.abs(momentum[moving]))) if moving.any() else (
            1/brake["step_s"])
        assert np.isclose(feasible, brake["feasible_rate_s_inv"], atol=1e-12, rtol=1e-12)
        rate = min(feasible, 1/brake["step_s"])
        assert np.isclose(rate, brake["rate_s_inv"], atol=1e-12, rtol=1e-12)
        expected = np.clip(bias-rate*momentum, low, high)
        assert np.allclose(expected, record["allocated"], atol=1e-12, rtol=1e-12)
        assert record["allocated"] == brake["torque"]
        assert np.all(expected >= low) and np.all(expected <= high)
        durations.append(brake["elapsed_ns"]/1e6)
        rates.append(rate)
        decisions += 1
        if previous_brake is not None:
            expected_velocity = np.array(previous_brake["joint_velocity"])*(
                1-previous_brake["rate_s_inv"]*previous_brake["step_s"])
            velocity_errors.append(float(np.max(np.abs(velocity-expected_velocity))))
        previous_brake = brake
    assert len(brake_times) == (25 if profile == "velocity-brake" else 0)
    if brake_times:
        assert np.allclose(np.diff(brake_times), .002, atol=1e-9)
        assert abs(brake_times[0]-result["reference_prefix_end_s"]) < 1e-9
        assert abs(brake_times[-1]-brake_times[0]-.048) < 1e-9
assert all((c, p) in seen for c in protocol["cases"] for p in counts)
audit = {"audit": "pass", "trials": 20, "physical_passes": counts,
         "brake_decisions": decisions, "source_no_trigger_episodes": 2,
         "brake_rate_s_inv": {"n": len(rates), "minimum": min(rates),
                              "median": float(np.median(rates)), "maximum": max(rates)},
         "brake_extra_ms": {"n": len(durations), "median": float(np.median(durations)),
                            "p95": float(np.percentile(durations, 95, method="higher")),
                            "maximum": max(durations)},
         "local_model_next_velocity_max_joint_error_rad_s": {
             "n": len(velocity_errors), "median": float(np.median(velocity_errors)),
             "p95": float(np.percentile(velocity_errors, 95, method="higher")),
             "maximum": max(velocity_errors)},
         "scope": "Known-window replay and bounded-torque audit; no live policy/voice claim"}
(args.folder/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
print(json.dumps(audit))
