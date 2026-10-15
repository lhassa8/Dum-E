"""Independently audit recorded teacher physics and render local observation videos."""

import argparse
import hashlib
import json
from pathlib import Path

import imageio_ffmpeg
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("run", type=Path)
args = parser.parse_args()
report = json.loads((args.run/"report.json").read_text())
protocol = report["protocol"]
planned = report.get("planned_cases", protocol["first_teacher_assay"])
assert report["episodes"] and len(report["episodes"]) == len(planned)
for name in ("collect_libero_grasp_teacher.py", "libero_grasp_teacher.py"):
    assert hashlib.sha256((args.run/name).read_bytes()).hexdigest() == protocol[name+"_sha256"]
audited = []
for expected, result in zip(planned, report["episodes"]):
    assert all(result[k] == v for k, v in expected.items())
    training_states = protocol["state_split"]["training_and_teacher_calibration"]
    assert result["initial_state_index"] in training_states
    directory = args.run/f"task{result['task_id']}-state{result['initial_state_index']}"
    actions = json.loads((directory/"actions.json").read_text())
    hold = json.loads((directory/"hold.json").read_text())
    assert len(actions) <= protocol["teacher"]["max_active_steps"]
    observations = sorted((directory/"observations").glob("*.npz"))
    assert len(observations) == len(actions)
    for index, action in enumerate(actions):
        assert action["index"] == index and action["privileged_teacher"] is True
        vector = np.asarray(action["action"])
        assert vector.shape == (7,) and np.isfinite(vector).all() and np.abs(vector).max() <= 1+1e-9
    qualified = (result["error"] is None and result["teacher_passed"]
                 and (not report.get("complete_placement_requested")
                      or result.get("complete_teacher_passed", False)))
    if not qualified:
        audited.append({**expected, "passed": False, "active_steps": len(actions),
                        "error": result["error"], "excluded_from_training": True})
        continue
    assert hold and len(actions) > 0
    xyz = np.asarray([row["xyz"] for row in hold])
    joints = np.asarray([row["joints"] for row in hold])
    times = np.asarray([row["sim_time"] for row in hold])
    assert np.isfinite(xyz).all() and np.isfinite(joints).all()
    assert joints.shape[1] == 7 and xyz.shape[1] == 3
    assert times[-1]-times[0] > 1 and np.diff(times).min() >= -1e-10
    assert np.diff(times).max() <= .00200001, "Dense native holding sample missing"
    measured = {
        "min_hold_lift_m": float(xyz[:, 2].min()-result["initial_body_xyz"][2]),
        "max_hold_translation_m": float(np.linalg.norm(xyz-xyz[0], axis=1).max()),
        "max_hold_joint_range_rad": float(np.ptp(joints, axis=0).max()),
        "all_hold_grasp_contacts": all(row["grasp_contacts"] is True for row in hold),
    }
    for key, value in measured.items():
        assert abs(value-result[key]) < 1e-10, key
    assert measured["min_hold_lift_m"] >= .08
    assert measured["max_hold_translation_m"] <= .01
    assert measured["max_hold_joint_range_rad"] <= .02
    assert measured["all_hold_grasp_contacts"] and result["teacher_passed"]
    assert result["hold_wall_s"] >= 2
    placement_measured = {}
    if report.get("complete_placement_requested"):
        assert result["complete_teacher_passed"], "Incomplete placement excluded from training"
        rest = json.loads((directory/"rest.json").read_text())
        rest_times = np.asarray([s["sim_time"] for s in rest])
        assert np.diff(rest_times).min() >= -1e-10
        assert np.diff(rest_times).max() <= .00200001
        limits = protocol["placement_teacher"]
        window = [s for s in rest if s["sim_time"] >=
                  rest[-1]["sim_time"]-limits["rest_window_sim_s"]-1e-10]
        assert window[-1]["sim_time"]-window[0]["sim_time"] >= .5-1e-9
        assert all(s["native_goal"] is True and s["plate_contact"] is True
                   and s["any_gripper_contact"] is False for s in window)
        placed = np.asarray([s["xyz"] for s in window])
        placement_measured = {
            "placement_xy_error_m": float(np.linalg.norm(
                placed[-1, :2]-np.asarray(result["initial_plate_xyz"])[:2])),
            "rest_translation_m": float(np.linalg.norm(placed-placed[0], axis=1).max())}
        for key, value in placement_measured.items():
            assert abs(value-result[key]) < 1e-10
        assert placement_measured["placement_xy_error_m"] <= limits["placement_xy_limit_m"]
        assert placement_measured["rest_translation_m"] <= limits["rest_translation_limit_m"]
        assert all(row["action"][-1] == -1 for row in actions if row["phase"] == "settle")
    insertion = result.get("hold_insertion_index", len(observations))
    hold_frames = sorted((directory/"hold-observations").glob("*.npz"))
    # The first resumed pre-action observation is the final hold observation.
    # Include this boundary once to preserve the 20Hz simulation timeline.
    if insertion < len(observations):
        assert (hold_frames[-1].read_bytes()
                == observations[insertion].read_bytes())
        hold_frames = hold_frames[:-1]
    frames = observations[:insertion]+hold_frames+observations[insertion:]
    if (directory/"terminal-observation.npz").exists():
        frames.append(directory/"terminal-observation.npz")
    assert len(frames) > len(observations)+20
    video = directory/"observed-teacher.mp4"
    writer = imageio_ffmpeg.write_frames(str(video), (512, 256), fps=20,
                                        codec="libx264", pix_fmt_in="rgb24")
    writer.send(None)
    digest = hashlib.sha256()
    try:
        for path in frames:
            digest.update(path.name.encode()+path.read_bytes())
            with np.load(path, allow_pickle=False) as observation:
                assert set(observation.files) == {"agentview_image", "robot0_eye_in_hand_image",
                                                  "robot0_eef_pos", "robot0_eef_quat",
                                                  "robot0_gripper_qpos"}
                images = []
                for key in ("agentview_image", "robot0_eye_in_hand_image"):
                    image = observation[key]
                    assert image.shape == (256, 256, 3) and image.dtype == np.uint8
                    images.append(image[::-1, ::-1])
                for key in ("robot0_eef_pos", "robot0_eef_quat", "robot0_gripper_qpos"):
                    assert np.isfinite(observation[key]).all()
                writer.send(np.ascontiguousarray(np.concatenate(images, axis=1)))
    finally:
        writer.close()
    audited.append({**expected, **measured, **placement_measured, "passed": True,
                    "active_steps": len(actions),
                    "dense_hold_samples": len(hold), "frame_count": len(frames),
                    "observation_sha256": digest.hexdigest(),
                    "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                    "video_scope": "Recorded front/wrist at simulation20Hz; privileged teacher"})
audit = {"passed": all(s["passed"] for s in audited), "audit_completed": True,
         "planned": len(planned), "qualified": sum(s["passed"] for s in audited),
         "episodes": audited,
         "complete_placement": report.get("complete_placement_requested", False),
         "scope": "Recorded teacher physics/source/input audit; no learned-policy qualification"}
(args.run/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
print(json.dumps(audit, indent=2))
