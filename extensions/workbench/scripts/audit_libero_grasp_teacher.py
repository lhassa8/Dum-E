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
assert report["episodes"] and len(report["episodes"]) == len(protocol["first_teacher_assay"])
for name in ("collect_libero_grasp_teacher.py", "libero_grasp_teacher.py"):
    assert hashlib.sha256((args.run/name).read_bytes()).hexdigest() == protocol[name+"_sha256"]
audited = []
for expected, result in zip(protocol["first_teacher_assay"], report["episodes"]):
    assert all(result[k] == v for k, v in expected.items())
    training_states = protocol["state_split"]["training_and_teacher_calibration"]
    assert result["initial_state_index"] in training_states
    directory = args.run/f"task{result['task_id']}-state{result['initial_state_index']}"
    actions = json.loads((directory/"actions.json").read_text())
    hold = json.loads((directory/"hold.json").read_text())
    assert 0 < len(actions) <= protocol["teacher"]["max_active_steps"]
    observations = sorted((directory/"observations").glob("*.npz"))
    assert len(observations) == len(actions)
    for index, action in enumerate(actions):
        assert action["index"] == index and action["privileged_teacher"] is True
        vector = np.asarray(action["action"])
        assert vector.shape == (7,) and np.isfinite(vector).all() and np.abs(vector).max() <= 1+1e-9
    assert result["error"] is None and hold, "Failed teacher remains excluded from training"
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
    frames = observations+sorted((directory/"hold-observations").glob("*.npz"))
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
    audited.append({**expected, **measured, "active_steps": len(actions),
                    "dense_hold_samples": len(hold), "frame_count": len(frames),
                    "observation_sha256": digest.hexdigest(),
                    "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                    "video_scope": "Recorded front/wrist at simulation20Hz; privileged teacher"})
audit = {"passed": True, "episodes": audited,
         "scope": "Recorded physics/source/input audit; no learned-policy or release qualification"}
(args.run/"audit.json").write_text(json.dumps(audit, indent=2)+"\n")
print(json.dumps(audit, indent=2))
