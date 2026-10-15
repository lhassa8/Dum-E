"""Audit actual recorded replay physics/action identity and render local videos."""

import argparse
import hashlib
import json
from pathlib import Path

import h5py
import imageio_ffmpeg
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path)
parser.add_argument("--preparation", type=Path, required=True)
args = parser.parse_args()
report = json.loads((args.run/"report.json").read_text())
assert len(report["episodes"]) == len(report["protocol"]["cases"])
preparation = json.loads((args.preparation/"preparation.json").read_text())
audited = []
for expected, result in zip(report["protocol"]["cases"], report["episodes"]):
    assert all(result[k] == v for k, v in expected.items())
    directory = args.run/f"task{result['task_id']}-{result['demo']}"
    records = json.loads((directory/"actions.json").read_text())
    samples = json.loads((directory/"samples.json").read_text())
    checks = json.loads((directory/"checks.json").read_text())
    if result["error"] is not None:
        audited.append({**expected, "error": result["error"], "applied_steps": len(records)})
        continue
    spec = next(s for s in preparation["files"] if s["sha256"] == result["source_sha256"])
    with h5py.File(args.preparation/spec["name"], "r") as data:
        source = data[f"data/{result['demo']}/actions"][:]
    assert len(records) == len(source)+report["protocol"]["settle_steps"] <= 220
    actual = np.asarray([r["action"] for r in records])
    assert np.array_equal(actual[:len(source)], source)
    assert np.array_equal(actual[len(source):, :6], np.zeros((21, 6)))
    assert np.all(actual[len(source):, -1] == source[-1, -1])
    assert len(checks) == len(source)
    reference = max(c["pre_reference_state_error"] for c in checks)
    assert reference == result["max_reference_state_error"]
    times = np.asarray([s["sim_time"] for s in samples])
    assert np.diff(times).min() >= -1e-10 and np.diff(times).max() <= .00200001
    lift = [s for s in samples if s["grasp"] and s["xyz"][2]-result["initial_xyz"][2] >= .08]
    window = [s for s in samples if s["sim_time"] >= times[-1]-.5-1e-10]
    xyz = np.asarray([s["xyz"] for s in window])
    metrics = {"qualified_lift": bool(lift),
               "final_plate_contact": all(s["plate_contact"] for s in window),
               "final_no_gripper_contact": all(not s["any_gripper_contact"] for s in window),
               "final_native_goal": all(s["native_goal"] for s in window),
               "rest_movement_m": float(np.linalg.norm(xyz-xyz[0], axis=1).max()),
               "placement_xy_error_m": float(np.linalg.norm(
                   xyz[-1, :2]-np.asarray(result["initial_plate_xyz"])[:2]))}
    for key, value in metrics.items():
        assert abs(value-result[key]) < 1e-10, key
    physical = (bool(lift) and metrics["final_plate_contact"]
                and metrics["final_no_gripper_contact"] and metrics["final_native_goal"]
                and metrics["rest_movement_m"] <= .005 and metrics["placement_xy_error_m"] <= .035
                and window[-1]["sim_time"]-window[0]["sim_time"] >= .5-1e-9)
    fidelity = reference <= report["protocol"]["reference_state_max_error"]
    assert physical == result["physical_passed"] and fidelity == result["fidelity_passed"]
    frames = sorted((directory/"observations").glob("*.npz"))
    assert len(frames) == len(records)
    frames.append(directory/"terminal-observation.npz")
    writer = imageio_ffmpeg.write_frames(str(directory/"observed-replay.mp4"), (512, 256),
                                        fps=20, codec="libx264", pix_fmt_in="rgb24")
    writer.send(None)
    try:
        for path in frames:
            with np.load(path, allow_pickle=False) as observation:
                assert set(observation.files) == {"agentview_image", "robot0_eye_in_hand_image",
                                                  "robot0_eef_pos", "robot0_eef_quat",
                                                  "robot0_gripper_qpos"}
                images = [observation[k] for k in ("agentview_image", "robot0_eye_in_hand_image")]
                assert all(im.shape == (256, 256, 3) and im.dtype == np.uint8 for im in images)
                writer.send(np.ascontiguousarray(np.concatenate(
                    [im[::-1, ::-1] for im in images], axis=1)))
    finally:
        writer.close()
    audited.append({**expected, **metrics, "physical_passed": physical,
                    "fidelity_passed": fidelity, "max_reference_state_error": reference,
                    "source_actions": len(source), "active_steps": len(records),
                    "dense_samples": len(samples), "qualified_lift_samples": len(lift),
                    "pre_eef_error_median_m": result["pre_eef_error_median_m"],
                    "post_eef_error_median_m": result["post_eef_error_median_m"],
                    "video_sha256": hashlib.sha256(
                        (directory/"observed-replay.mp4").read_bytes()).hexdigest()})
audit = {"audit_completed": True, "planned": len(audited), "episodes": audited,
         "physical_passes": sum(r.get("physical_passed", False) for r in audited),
         "fidelity_passes": sum(r.get("fidelity_passed", False) for r in audited),
         "scope": "Recorded human-action replay; no learned-policy qualification"}
(args.run/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
print(json.dumps(audit, indent=2))
