"""Two new training-state teacher assays; no learned adaptation or evaluation-state access."""

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
source = args.openpi.resolve()
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
for path in (source, source/"third_party/libero", source/"packages/openpi-client/src"):
    sys.path.insert(0, str(path))
import numpy as np  # noqa: E402
from examples.libero.main import LIBERO_DUMMY_ACTION, _get_libero_env  # noqa: E402
from libero.libero import benchmark  # noqa: E402
from libero_grasp_teacher import calibrated_rim, native_servo  # noqa: E402
from PIL import Image  # noqa: E402
from robosuite.controllers.joint_pos import JointPositionController  # noqa: E402

protocol = json.loads((Path(__file__).resolve().parents[1]/
                       "docs/grasp-adaptation-protocol.json").read_text())
for name in (Path(__file__).name, "libero_grasp_teacher.py"):
    path = Path(__file__).with_name(name)
    (args.output/name).write_bytes(path.read_bytes())
    protocol[name+"_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
(args.output/"protocol.json").write_text(json.dumps(protocol, indent=2)+"\n")
suite = benchmark.get_benchmark_dict()["libero_spatial"]()
report = {"protocol": protocol, "episodes": []}
for spec in protocol["first_teacher_assay"]:
    directory = args.output/f"task{spec['task_id']}-state{spec['initial_state_index']}"
    directory.mkdir()
    (directory/"observations").mkdir()
    (directory/"hold-observations").mkdir()
    env, prompt = _get_libero_env(suite.get_task(spec["task_id"]), 256, 7)
    result = {**spec, "error": None, "teacher_passed": False}
    records, held = [], []
    try:
        env.env.ignore_done = True
        env.reset()
        obs = env.set_init_state(suite.get_task_init_states(spec["task_id"])[
            spec["initial_state_index"]])
        for _ in range(10):
            obs, _, _, _ = env.step(LIBERO_DUMMY_ACTION)
        native, robot = env.env, env.env.robots[0]
        body = native.obj_body_id["akita_black_bowl_1"]
        contact_geoms = native.objects_dict["akita_black_bowl_1"].contact_geoms
        initial = native.sim.data.body_xpos[body].copy()
        result["initial_body_xyz"] = initial.tolist()
        result["task_prompt"] = prompt
        controller = robot.controller
        grasp, rotation, calibration = calibrated_rim(native, robot)
        (directory/"oracle-calibration.json").write_text(json.dumps(calibration, indent=2))
        above = grasp.copy()
        # Approach at a fixed clearance instead of carrying the initial high
        # pose through a long vertical descent. Training-only trajectory choice.
        above[2] = grasp[2]+protocol["teacher"]["approach_clearance_m"]
        lift = grasp+np.array([0., 0., .12])
        speeds = protocol["teacher"]["max_command_translation_m"]
        phases = [("above", above, -1., speeds["above"], None),
                  ("descend", grasp, -1., speeds["descend"], None),
                  ("close", grasp, 1., .003, 12),
                  ("lift", lift, 1., speeds["lift"], None)]
        original = controller.run_controller
        hold_active = False
        joint = JointPositionController(
            sim=controller.sim, eef_name=controller.eef_name,
            joint_indexes={"joints": controller.joint_index, "qpos": controller.qpos_index,
                           "qvel": controller.qvel_index},
            actuator_range=controller.actuator_limits, kp=300, damping_ratio=2)

        def measure():
            return {"xyz": native.sim.data.body_xpos[body].tolist(),
                    "joints": robot._joint_positions.tolist(),
                    "grasp_contacts": bool(native._check_grasp(robot.gripper, contact_geoms)),
                    "sim_time": float(native.sim.data.time)}

        def control():
            torque = original()
            if hold_active:
                held.append(measure())
                return joint.run_controller()
            return torque

        controller.run_controller = control
        active = 0
        for phase, goal, grip, speed, fixed in phases:
            count = 0
            while True:
                action, error, angular = native_servo(controller, goal, rotation, grip,
                                                      max_translation_m=speed)
                if fixed is None and error < .002 and angular < .015:
                    break
                assert active < 220, "Original220 active-step budget exceeded"
                count += 1
                index = len(records)
                fields = ("agentview_image", "robot0_eye_in_hand_image", "robot0_eef_pos",
                          "robot0_eef_quat", "robot0_gripper_qpos")
                np.savez(directory/"observations"/f"{index:04d}.npz", **{k: obs[k] for k in fields})
                started = time.monotonic()
                obs, _, _, _ = env.step(action.tolist())
                active += 1
                records.append({"index": index, "phase": phase, "action": action.tolist(),
                                "position_error_m": error, "orientation_error_rad": angular,
                                "judge": measure(), "privileged_teacher": True})
                time.sleep(max(0, .05-(time.monotonic()-started)))
                if fixed is not None and count >= fixed:
                    break
        result["active_steps"] = active
        result["lift_before_hold_m"] = float(native.sim.data.body_xpos[body][2]-initial[2])
        result["grasp_before_hold"] = bool(native._check_grasp(robot.gripper, contact_geoms))
        assert result["grasp_before_hold"] and result["lift_before_hold_m"] >= .08, (
            "Teacher did not achieve original qualified grasp/lift")
        joint.update(force=True)
        joint.set_goal(np.zeros(7), set_qpos=joint.joint_pos.copy())
        held.append(measure())
        hold_active = True
        fields = ("agentview_image", "robot0_eye_in_hand_image", "robot0_eef_pos",
                  "robot0_eef_quat", "robot0_gripper_qpos")
        np.savez(directory/"hold-observations"/"0000.npz", **{k: obs[k] for k in fields})
        started, origin = time.monotonic(), held[0]["sim_time"]
        hold_frames = 0
        while time.monotonic()-started < 2 or held[-1]["sim_time"]-origin <= 1:
            tick = time.monotonic()
            obs, _, _, _ = env.step([0.]*6+[1.])
            held.append(measure())
            hold_frames += 1
            np.savez(directory/"hold-observations"/f"{hold_frames:04d}.npz",
                     **{k: obs[k] for k in fields})
            time.sleep(max(0, .05-(time.monotonic()-tick)))
        xyz = np.array([s["xyz"] for s in held])
        joints = np.array([s["joints"] for s in held])
        result.update(min_hold_lift_m=float(xyz[:, 2].min()-initial[2]),
                      max_hold_translation_m=float(np.linalg.norm(xyz-xyz[0], axis=1).max()),
                      max_hold_joint_range_rad=float(np.ptp(joints, axis=0).max()),
                      all_hold_grasp_contacts=all(s["grasp_contacts"] for s in held),
                      native_hold_samples=len(held), hold_wall_s=time.monotonic()-started,
                      hold_sim_s=held[-1]["sim_time"]-origin)
        result["teacher_passed"] = (result["min_hold_lift_m"] >= .08
                                    and result["max_hold_translation_m"] <= .01
                                    and result["max_hold_joint_range_rad"] <= .02
                                    and result["all_hold_grasp_contacts"])
        Image.fromarray(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])).save(
            directory/"held.png")
    except Exception as caught:
        result["error"] = repr(caught)
        Image.fromarray(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])).save(
            directory/"failed.png")
    finally:
        env.close()
    result["active_steps"] = len(records)
    result["phase_counts"] = dict(Counter(row["phase"] for row in records))
    for name, value in (("actions.json", records), ("hold.json", held), ("result.json", result)):
        (directory/name).write_text(json.dumps(value, indent=2)+"\n")
    report["episodes"].append(result)
    (args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(result), flush=True)
