"""Frozen, known-trace 3 mm grasp alignment experiment; not a new policy rollout."""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--physics", type=Path, required=True)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
args = parser.parse_args()
rows = []
with args.physics.open() as stream:
    for line in stream:
        row = json.loads(line)
        if row["epoch"] == 1 and row["task_id"] == 0:
            assert row["source"] in ("policy", "osc_hold")
            rows.append(row)
            if row["phase"] == "success":
                break
assert len(rows) == 103 and rows[-1]["phase"] == "success"
assert [r["active_steps"] for r in rows] == list(range(1, 104))
closure = next(i for i, r in enumerate(rows) if r["action"][6] > 0)
assert closure > 0 and rows[closure - 1]["source"] == "policy"
variants = [{"name": "baseline", "offset_m": [0.0, 0.0, 0.0]}]
for axis, axis_name in enumerate("xyz"):
    for sign in (-1, 1):
        offset = [0.0, 0.0, 0.0]
        offset[axis] = sign * 0.003
        variants.append({"name": axis_name + ("-3mm" if sign < 0 else "+3mm"),
                         "offset_m": offset})
args.output.mkdir(parents=True, exist_ok=False)
protocol = {
    "scope": "Known-trace development, not fresh policy inference or held-out qualification",
    "source_sha256": hashlib.sha256(args.physics.read_bytes()).hexdigest(),
    "actor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "task_id": 0, "epoch": 1, "seed": 7, "initial_state_index": 0,
    "source_steps": len(rows), "variants": variants,
    "intervention_step": rows[closure - 1]["active_steps"],
    "intervention": "One world-frame OSC displacement offset on last open-gripper action",
    "input_contract": "LIBERO OSC_POSE; convert metres using verified native action scaling",
    "trigger": "Evaluator sees native bilateral-pad grasp and lift >=80mm at completed step",
    "hold": "Native JointPositionController kp300 damping_ratio2, unchanged torque caps",
    "min_lift_m": 0.08, "max_translation_m": 0.01,
    "max_joint_range_rad": 0.02, "min_hold_wall_s": 2.0,
    "min_hold_sim_s_exclusive": 1.0, "max_hold_wall_s": 5.0,
    "max_baseline_replay_error": 1e-6,
    "resumption": "Remaining recorded actions; no refreshed learned-policy observations",
    "attempt_budget": "One frozen seven-variant grid; retain all outcomes; no grid retuning",
}
(args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
(args.output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
source = args.openpi.resolve()
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
sys.path.insert(0, str(source / "third_party/libero"))
sys.path.insert(0, str(source / "packages/openpi-client/src"))
sys.path.insert(0, str(source))

import imageio  # noqa: E402
import numpy as np  # noqa: E402
from examples.libero.main import LIBERO_DUMMY_ACTION, _get_libero_env  # noqa: E402
from libero.libero import benchmark  # noqa: E402
from robosuite.controllers.joint_pos import JointPositionController  # noqa: E402

suite = benchmark.get_benchmark_dict()["libero_spatial"]()
report = {"protocol": protocol, "episodes": []}
for variant in variants:
    samples, held, frames, actions = [], [], [], []
    episode = {**variant, "error": None, "trigger_reached": False,
               "hold_passed": False, "native_success": False}
    env = None
    try:
        env, _ = _get_libero_env(suite.get_task(0), 256, 7)
        env.env.ignore_done = True
        env.reset()
        env.set_init_state(suite.get_task_init_states(0)[0])
        for _ in range(10):
            env.step(LIBERO_DUMMY_ACTION)
        native = env.env
        robot = native.robots[0]
        osc = robot.controller
        assert osc.name == "OSC_POSE" and osc.use_delta and osc.impedance_mode == "fixed"
        assert osc.interpolator_pos is None and osc.interpolator_ori is None
        osc.scale_action(np.zeros(6))
        assert np.allclose(osc.action_scale[:3], 0.05)
        assert np.allclose(osc.input_min[:3], -1) and np.allclose(osc.input_max[:3], 1)
        assert np.allclose(osc.action_input_transform[:3], 0)
        assert np.allclose(osc.action_output_transform[:3], 0)
        episode["translation_action_scale_m"] = osc.action_scale[:3].tolist()
        body = native.obj_body_id["akita_black_bowl_1"]
        target = native.objects_dict["akita_black_bowl_1"].contact_geoms
        initial = native.sim.data.body_xpos[body].copy()
        assert np.max(np.abs(initial - rows[0]["judge"]["initial_xyz"])) < 1e-9
        joint = JointPositionController(
            sim=osc.sim, eef_name=osc.eef_name,
            joint_indexes={"joints": osc.joint_index, "qpos": osc.qpos_index,
                           "qvel": osc.qvel_index},
            actuator_range=osc.actuator_limits, kp=300, damping_ratio=2,
        )
        paused = False
        original = osc.run_controller

        def measure(origin):
            return {"origin": origin, "sim_time": float(native.sim.data.time),
                    "xyz": native.sim.data.body_xpos[body].tolist(),
                    "lift_m": float(native.sim.data.body_xpos[body][2] - initial[2]),
                    "joints": robot._joint_positions.tolist(),
                    "grasp_contacts": bool(native._check_grasp(robot.gripper, target)),
                    "success": bool(native._check_success())}

        def run_controller():
            torques = original()
            if paused:
                held.append(measure("torque_callback"))
                return joint.run_controller()
            return torques

        osc.run_controller = run_controller
        baseline_errors = []
        for i, row in enumerate(rows):
            action = np.array(row["action"], dtype=float)
            if i == closure - 1:
                action[:3] += np.asarray(variant["offset_m"]) / osc.action_scale[:3]
                assert np.all(action[:3] >= osc.input_min[:3])
                assert np.all(action[:3] <= osc.input_max[:3])
            actions.append(action.tolist())
            obs, _, _, _ = env.step(action.tolist())
            frames.append(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1]))
            measured = measure("step_end")
            samples.append(measured)
            if variant["name"] == "baseline":
                expected = row["judge"]
                baseline_errors.append(max(
                    np.max(np.abs(np.asarray(measured["xyz"]) - expected["xyz"])),
                    np.max(np.abs(np.asarray(measured["joints"]) - expected["joints"])),
                    abs(measured["sim_time"] - expected["sim_time"]),
                ))
                assert measured["grasp_contacts"] == expected["grasp_contacts"]
                assert measured["success"] == expected["success"]
            if (not episode["trigger_reached"] and measured["grasp_contacts"]
                    and measured["lift_m"] >= protocol["min_lift_m"]):
                episode["trigger_reached"] = True
                episode["trigger_step"] = row["active_steps"]
                joint.update(force=True)
                joint.set_goal(np.zeros(7), set_qpos=joint.joint_pos.copy())
                held.append(measured)
                paused = True
                started = time.monotonic()
                while (time.monotonic() - started < 2
                       or held[-1]["sim_time"] - held[0]["sim_time"] <= 1):
                    assert time.monotonic() - started < 5, "Hold physics stalled"
                    hold_action = [0.0] * 6 + [float(action[6])]
                    obs, _, _, _ = env.step(hold_action)
                    held.append(measure("hold_step_end"))
                    frames.append(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1]))
                    time.sleep(0.025)
                paused = False
                episode["hold_wall_s"] = time.monotonic() - started
                xyz = np.array([s["xyz"] for s in held])
                joints = np.array([s["joints"] for s in held])
                episode.update(
                    hold_sim_s=held[-1]["sim_time"] - held[0]["sim_time"],
                    min_hold_lift_m=min(s["lift_m"] for s in held),
                    max_hold_translation_m=float(np.max(np.linalg.norm(xyz - xyz[0], axis=1))),
                    max_hold_joint_range_rad=float(np.max(np.ptp(joints, axis=0))),
                    all_hold_grasp_contacts=all(s["grasp_contacts"] for s in held),
                )
                episode["hold_passed"] = (
                    episode["min_hold_lift_m"] >= protocol["min_lift_m"]
                    and episode["max_hold_translation_m"] <= protocol["max_translation_m"]
                    and episode["max_hold_joint_range_rad"] <= protocol["max_joint_range_rad"]
                    and episode["all_hold_grasp_contacts"]
                )
            if measured["success"]:
                break
        episode["native_success"] = bool(native._check_success())
        episode["applied_recorded_steps"] = len(actions)
        episode["max_lift_m"] = max(s["lift_m"] for s in samples)
        episode["max_bilateral_lift_m"] = max(
            (s["lift_m"] for s in samples if s["grasp_contacts"]), default=None
        )
        if baseline_errors:
            episode["max_baseline_replay_error"] = float(max(baseline_errors))
            assert episode["max_baseline_replay_error"] <= 1e-6
    except Exception as caught:
        episode["error"] = repr(caught)
    finally:
        if env is not None:
            env.close()
    trial = args.output / variant["name"]
    trial.mkdir()
    for filename, data in (("samples.json", samples), ("hold.json", held),
                           ("actions.json", actions), ("episode.json", episode)):
        (trial / filename).write_text(json.dumps(data, indent=2))
    if frames:
        imageio.mimwrite(trial / "replay.mp4", frames, fps=20)
    report["episodes"].append(episode)
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(episode), flush=True)
    if episode["error"]:
        report["not_run_variants"] = variants[len(report["episodes"]):]
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        raise SystemExit("Infrastructure failure retained; remaining variants not attempted")
