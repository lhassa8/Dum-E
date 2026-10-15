"""Training-state teacher collection; no learned adaptation or evaluation-state access."""

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
parser.add_argument("--complete-placement", action="store_true")
parser.add_argument("--training-cohort", action="store_true")
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
from libero_grasp_teacher import calibrated_rim, collision_vertices, native_servo  # noqa: E402
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
report["complete_placement_requested"] = args.complete_placement
planned = ([{"task_id": task, "initial_state_index": state}
            for task in protocol["tasks"]
            for state in protocol["state_split"]["training_and_teacher_calibration"]]
           if args.training_cohort else protocol["first_teacher_assay"])
report["planned_cases"] = planned
(args.output/"planned-cases.json").write_text(json.dumps(planned, indent=2)+"\n")
for spec in planned:
    directory = args.output/f"task{spec['task_id']}-state{spec['initial_state_index']}"
    directory.mkdir()
    (directory/"observations").mkdir()
    (directory/"hold-observations").mkdir()
    env, prompt = _get_libero_env(suite.get_task(spec["task_id"]), 256, 7)
    result = {**spec, "error": None, "teacher_passed": False}
    records, held, resting = [], [], []
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
        bowl_ids = {native.sim.model.geom_name2id(name) for name in contact_geoms}
        gripper_ids = {native.sim.model.geom_name2id(name) for name in robot.gripper.contact_geoms}
        plate_geoms = native.objects_dict["plate_1"].contact_geoms
        plate_ids = {native.sim.model.geom_name2id(name) for name in plate_geoms}
        plate_vertices = collision_vertices(native, plate_geoms)
        plate_target = native.sim.data.body_xpos[native.obj_body_id["plate_1"]].copy()
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
        rest_active = False
        joint = JointPositionController(
            sim=controller.sim, eef_name=controller.eef_name,
            joint_indexes={"joints": controller.joint_index, "qpos": controller.qpos_index,
                           "qvel": controller.qvel_index},
            actuator_range=controller.actuator_limits, kp=300, damping_ratio=2)

        def measure():
            pairs = [{int(c.geom1), int(c.geom2)} for c in
                     native.sim.data.contact[:native.sim.data.ncon]]
            return {"xyz": native.sim.data.body_xpos[body].tolist(),
                    "joints": robot._joint_positions.tolist(),
                    "grasp_contacts": bool(native._check_grasp(robot.gripper, contact_geoms)),
                    "sim_time": float(native.sim.data.time),
                    "any_gripper_contact": any(p & bowl_ids and p & gripper_ids for p in pairs),
                    "plate_contact": any(p & bowl_ids and p & plate_ids for p in pairs),
                    "native_goal": bool(native._check_success())}

        def control():
            torque = original()
            if hold_active:
                held.append(measure())
                return joint.run_controller()
            if rest_active:
                resting.append(measure())
            return torque

        controller.run_controller = control
        def execute_phases(observation, sequence):
            for phase, goal, grip, speed, fixed in sequence:
                count = 0
                while True:
                    action, error, angular = native_servo(controller, goal, rotation, grip,
                                                          max_translation_m=speed)
                    if fixed is None and error < .002 and angular < .015:
                        break
                    assert len(records) < 220, "Original220 active-step budget exceeded"
                    count += 1
                    index = len(records)
                    fields = ("agentview_image", "robot0_eye_in_hand_image", "robot0_eef_pos",
                              "robot0_eef_quat", "robot0_gripper_qpos")
                    np.savez(directory/"observations"/f"{index:04d}.npz",
                             **{k: observation[k] for k in fields})
                    started = time.monotonic()
                    observation, _, _, _ = env.step(action.tolist())
                    records.append({"index": index, "phase": phase, "action": action.tolist(),
                                    "position_error_m": error, "orientation_error_rad": angular,
                                    "judge": measure(), "privileged_teacher": True})
                    if rest_active:
                        resting.append(measure())
                    time.sleep(max(0, .05-(time.monotonic()-started)))
                    if fixed is not None and count >= fixed:
                        break
            return observation

        obs = execute_phases(obs, phases)
        result["hold_insertion_index"] = len(records)
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
        if args.complete_placement:
            assert result["teacher_passed"], "Failed grasp/hold excluded from placement"
            placement = protocol["placement_teacher"]
            hold_active = False
            controller.update(force=True)
            offset = native.sim.data.body_xpos[body]-controller.ee_pos
            bowl_vertices = collision_vertices(native, contact_geoms)
            bottom_offset = bowl_vertices[:, 2].min()-native.sim.data.body_xpos[body][2]
            placed_body = plate_target.copy()
            placed_body[2] = plate_vertices[:, 2].max()-bottom_offset+.002
            placed_eef = placed_body-offset
            carry = placed_eef.copy()
            carry[2] = controller.ee_pos[2]
            retreat = placed_eef+np.array([0., 0., .12])
            speed = placement["max_translation_m"]
            result["placement_target_xyz"] = placed_body.tolist()
            result["initial_plate_xyz"] = plate_target.tolist()
            obs = execute_phases(obs, [("carry", carry, 1., speed, None),
                                      ("lower", placed_eef, 1., speed, None),
                                      ("release", placed_eef, -1., .003,
                                       placement["release_steps"]),
                                      ("retreat", retreat, -1., speed, None)])
            controller.update(force=True)
            rest_active = True
            resting.append(measure())
            obs = execute_phases(obs, [("settle", controller.ee_pos.copy(), -1., .003,
                                       placement["settle_steps"])])
            window = [s for s in resting if s["sim_time"] >=
                      resting[-1]["sim_time"]-placement["rest_window_sim_s"]-1e-10]
            xyz = np.array([s["xyz"] for s in window])
            result.update(
                final_native_goal=bool(native._check_success()),
                rest_sim_s=window[-1]["sim_time"]-window[0]["sim_time"],
                all_rest_no_gripper_contact=all(not s["any_gripper_contact"] for s in window),
                all_rest_plate_contact=all(s["plate_contact"] for s in window),
                all_rest_native_goal=all(s["native_goal"] for s in window),
                rest_translation_m=float(np.linalg.norm(xyz-xyz[0], axis=1).max()),
                placement_xy_error_m=float(np.linalg.norm(xyz[-1, :2]-plate_target[:2])))
            result["complete_teacher_passed"] = (
                result["teacher_passed"] and result["all_rest_native_goal"]
                and result["all_rest_no_gripper_contact"] and result["all_rest_plate_contact"]
                and result["rest_sim_s"] >= placement["rest_window_sim_s"]-1e-9
                and result["rest_translation_m"] <= placement["rest_translation_limit_m"]
                and result["placement_xy_error_m"] <= placement["placement_xy_limit_m"])
            np.savez(directory/"terminal-observation.npz", **{k: obs[k] for k in fields})
            Image.fromarray(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])).save(
                directory/"placed.png")
    except Exception as caught:
        result["error"] = repr(caught)
        Image.fromarray(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])).save(
            directory/"failed.png")
    finally:
        env.close()
    result["active_steps"] = len(records)
    result["phase_counts"] = dict(Counter(row["phase"] for row in records))
    for name, value in (("actions.json", records), ("hold.json", held),
                        ("rest.json", resting), ("result.json", result)):
        (directory/name).write_text(json.dumps(value, indent=2)+"\n")
    report["episodes"].append(result)
    (args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(result), flush=True)
