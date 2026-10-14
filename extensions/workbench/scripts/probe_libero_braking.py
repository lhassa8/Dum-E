"""Replay all ten recorded lifted stops with frozen native braking profiles."""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--source-run", type=Path, required=True)
parser.add_argument("--physics", type=Path, required=True)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
parser.add_argument("--saturation-case", help="Audit torques on one named baseline window only")
parser.add_argument("--torque-allocation", action="store_true",
                    help="Separate baseline versus bounded acceleration-allocation experiment")
parser.add_argument("--carry-governor", action="store_true",
                    help="Separate known-window pre-Stop OSC command-limiter diagnostic")
parser.add_argument("--velocity-brake", action="store_true",
                    help="Measured-velocity torque brake for the first50ms after Stop")
args = parser.parse_args()
diagnostics = (args.saturation_case, args.torque_allocation,
               args.carry_governor, args.velocity_brake)
assert sum(bool(v) for v in diagnostics) <= 1, "Use one diagnostic mode"
source_report = json.loads((args.source_run / "report.json").read_text())
physics = [json.loads(line) for line in args.physics.open()]
cases = []
for result in source_report["episodes"]:
    if not result["trigger_reached"]:
        continue
    name = "task%s-seed%s-%s" % (result["task_id"], result["seed"], result["variant"])
    held = json.loads((args.source_run / name / "hold.json").read_text())
    epoch = result["resume_epoch"] - 2
    # State tags can change while the previous native step is finishing. Require
    # the actual reset and match diagnostics to this exact Stop, not an old one.
    begin = next(i for i, r in enumerate(physics) if r["task_id"] == result["task_id"]
                 and r["epoch"] == epoch and r["active_steps"] == 1
                 and r["phase"] == "running")
    rows = []
    for row in physics[begin:]:
        rows.append(row)
        if row["judge"]["sim_time"] >= held[-1]["sim_time"] - 1e-10:
            break
    stop_wall = result["terminal_state"]["stop_requested_wall_s"]
    brake = next(r["hold_diagnostics"] for r in rows if r.get("hold_diagnostics")
                 and r["hold_diagnostics"]["stop_requested_wall_s"] == stop_wall)
    cases.append({"name": name, "task_id": result["task_id"], "rows": rows,
                  "held": held, "brake": brake,
                  "source_captured_hold_passed": result["hold_passed"]})
assert len(cases) == 10
profiles = [{"name": "baseline", "kp": 300, "damping_ratio": 2},
            {"name": "damping4", "kp": 300, "damping_ratio": 4},
            {"name": "kp600", "kp": 600, "damping_ratio": 2}]
if args.torque_allocation:
    assert not args.saturation_case, "Allocation and single-case diagnostics are separate"
    profiles = profiles[:1] + [{"name": "allocation", "kp": 300, "damping_ratio": 2}]
if args.carry_governor:
    profiles = profiles[:1] + [{"name": "carry-governor", "kp": 300, "damping_ratio": 2}]
if args.velocity_brake:
    profiles = profiles[:1] + [{"name": "velocity-brake", "kp": 300, "damping_ratio": 2}]
if args.saturation_case:
    cases = [c for c in cases if c["name"] == args.saturation_case]
    assert len(cases) == 1, "Unknown saturation diagnostic case"
    profiles = profiles[:1]
args.output.mkdir(parents=True, exist_ok=False)
protocol = {
    "scope": "Known-window physical replay; no inference, voice or live wall-time qualification",
    "physics_sha256": hashlib.sha256(args.physics.read_bytes()).hexdigest(),
    "source_report_sha256": hashlib.sha256(
        (args.source_run / "report.json").read_bytes()).hexdigest(),
    "actor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "profiles": profiles, "cases": [c["name"] for c in cases],
    "source_episodes_without_trigger": 2, "simulator_seed": 7,
    "initial_state_index": 0, "min_lift_m": .08, "max_translation_m": .01,
    "max_joint_range_rad": .02, "max_reference_error": 1e-6,
    "measurement_window": "Original Stop sensor timestamp through original last held timestamp",
    "sampling": "Every native torque callback and completed step in that fixed physical window",
    "pause_entry": "Exact recorded native torque-callback sim time; same measured joint target",
    "camera": "Automatic image observations off for replay; physics equivalence must be verified",
    "attempt_budget": "One frozen three-profile grid; retain every case; no retuning",
    "saturation_diagnostic_case": args.saturation_case,
    "torque_allocation": args.torque_allocation,
    "carry_governor": args.carry_governor,
    "velocity_brake": args.velocity_brake,
}
if args.velocity_brake:
    protocol.update(attempt_budget="One frozen two-profile diagnostic; no retuning",
                    velocity_brake_window_s=.05,
                    velocity_brake_inputs="Joint velocity, inertia, bias and native limits",
                    velocity_brake_limit="Local model omits contact and changing dynamics")
    helper = Path(__file__).with_name("libero_velocity_brake.py")
    protocol["velocity_brake_sha256"] = hashlib.sha256(helper.read_bytes()).hexdigest()
    (args.output / helper.name).write_bytes(helper.read_bytes())
if args.carry_governor:
    protocol.update(attempt_budget="One frozen two-profile diagnostic; no retuning",
                    pause_entry="Recorded callback time; each variant captures measured joints",
                    governor={"budget_rad": .01, "reserve_fraction": .5,
                              "activation": "Positive grip, last0.2sim seconds before brake",
                              "inputs": "Decoded OSC delta, arm Jacobian/inertia/bias/limits",
                              "limitations": (
                                  "Offline onset uses recorded Stop time; not deployable or "
                                  "fresh-policy qualification")})
    helper = Path(__file__).with_name("libero_carry_governor.py")
    protocol["governor_sha256"] = hashlib.sha256(helper.read_bytes()).hexdigest()
    (args.output / helper.name).write_bytes(helper.read_bytes())
if args.torque_allocation:
    protocol["attempt_budget"] = "One frozen two-profile allocation grid; no gain retuning"
    protocol["allocation"] = (
        "minimize ||inverse(M)*(tau-native_PD_command)||2 with unchanged native torque bounds; "
        "BVLS tol1e-9 max_iter50; identical native command if already within bounds"
    )
(args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
(args.output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
source = args.openpi.resolve()
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
sys.path.insert(0, str(source / "third_party/libero"))
sys.path.insert(0, str(source / "packages/openpi-client/src"))
sys.path.insert(0, str(source))

import numpy as np  # noqa: E402
from examples.libero.main import LIBERO_DUMMY_ACTION  # noqa: E402
from libero.libero import benchmark, get_libero_path  # noqa: E402
from libero.libero.envs import OffScreenRenderEnv  # noqa: E402
from PIL import Image  # noqa: E402
from robosuite.controllers.joint_pos import JointPositionController  # noqa: E402

if args.carry_governor:
    from libero_carry_governor import limit_carry_delta

if args.velocity_brake:
    from libero_velocity_brake import velocity_brake

if args.torque_allocation:
    from scipy.optimize import lsq_linear

    prepared = lsq_linear(np.eye(7), np.ones(7)*2, bounds=(-1, 1),
                          method="bvls", tol=1e-9, max_iter=50)
    assert prepared.success and np.allclose(prepared.x, 1), "Allocator startup check failed"

suite = benchmark.get_benchmark_dict()["libero_spatial"]()
report = {"protocol": protocol, "trials": []}
for case in cases:
    for profile in profiles:
        trial = args.output / (case["name"] + "-" + profile["name"])
        trial.mkdir()
        outcome = {"case": case["name"], "profile": profile, "error": None,
                   "source_captured_hold_passed": case["source_captured_hold_passed"]}
        samples, comparisons, torque_records, governor_records = [], [], [], []
        env = None
        try:
            task = suite.get_task(case["task_id"])
            bddl = Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
            env = OffScreenRenderEnv(bddl_file_name=str(bddl), camera_heights=256,
                                     camera_widths=256, use_camera_obs=False)
            env.seed(7)
            env.env.ignore_done = True
            env.reset()
            env.set_init_state(suite.get_task_init_states(case["task_id"])[0])
            for _ in range(10):
                env.step(LIBERO_DUMMY_ACTION)
            native = env.env
            robot = native.robots[0]
            osc = robot.controller
            assert osc.name == "OSC_POSE"
            body = native.obj_body_id["akita_black_bowl_1"]
            target = native.objects_dict["akita_black_bowl_1"].contact_geoms
            # Match Runtime.tick: reference is captured before constructing the
            # joint controller, which refreshes MuJoCo's kinematic caches.
            initial = native.sim.data.body_xpos[body].copy()
            outcome["initial_reference_error_m"] = float(np.max(np.abs(
                initial - case["held"][0]["initial_xyz"])))
            assert outcome["initial_reference_error_m"] < 1e-9, "Initial reference mismatch"
            joint = JointPositionController(
                sim=osc.sim, eef_name=osc.eef_name,
                joint_indexes={"joints": osc.joint_index, "qpos": osc.qpos_index,
                               "qvel": osc.qvel_index},
                actuator_range=osc.actuator_limits, kp=profile["kp"],
                damping_ratio=profile["damping_ratio"],
            )
            assert np.all(joint.kp == profile["kp"])
            outcome["torque_limits"] = np.asarray(osc.actuator_limits).tolist()
            assert np.array_equal(np.asarray(robot.torque_limits), np.asarray(osc.actuator_limits))
            start, end = case["held"][0]["sim_time"], case["held"][-1]["sim_time"]
            brake_time = case["brake"]["brake_started_sim_time"]
            original = osc.run_controller
            original_scale = osc.scale_action
            command_context = {"grip": -1.0, "index": None, "action": None}

            def scale_action(action):
                delta = original_scale(action)
                if (profile["name"] == "carry-governor" and command_context["grip"] > 0
                        and brake_time-.2-1e-10 <= native.sim.data.time < brake_time-1e-10):
                    delta, record = limit_carry_delta(delta, osc)
                    record.update(sim_time=float(native.sim.data.time),
                                  grip_command=command_context["grip"],
                                  source_index=command_context["index"],
                                  source_action=command_context["action"])
                    governor_records.append(record)
                return delta

            if args.carry_governor:
                assert osc.use_delta and osc.impedance_mode == "fixed" and osc.control_freq == 20
                osc.scale_action = scale_action

            def measure():
                return {"sim_time": float(native.sim.data.time),
                        "xyz": native.sim.data.body_xpos[body].tolist(),
                        "joints": robot._joint_positions.tolist(),
                        "grasp_contacts": bool(native._check_grasp(robot.gripper, target))}

            def capture(origin):
                measured = measure()
                measured["origin"] = origin
                if start - 1e-10 <= measured["sim_time"] <= end + 1e-10:
                    samples.append(measured)

            def run_controller():
                torques = original()
                capture("torque_callback")
                if native.sim.data.time >= brake_time - 1e-10:
                    if not run_controller.paused:
                        joint.update(force=True)
                        joint.set_goal(np.zeros(7), set_qpos=joint.joint_pos.copy())
                        outcome["entry_joint_error_rad"] = float(np.max(np.abs(
                            joint.goal_qpos - case["brake"]["goal_joints"])))
                        run_controller.paused = True
                        outcome["entry_velocity"] = joint.joint_vel.tolist()
                        outcome["captured_goal_joints"] = joint.goal_qpos.tolist()
                        outcome["goal_capture_error_rad"] = float(np.max(np.abs(
                            joint.goal_qpos-joint.joint_pos)))
                        assert outcome["goal_capture_error_rad"] < 1e-12
                    command = joint.run_controller()
                    low, high = robot.torque_limits
                    allocated = command
                    optimized = False
                    started = time.perf_counter_ns()
                    if profile["name"] == "allocation" and (
                        np.any(command < low) or np.any(command > high)
                    ):
                        inverse = np.linalg.inv(joint.mass_matrix)
                        solution = lsq_linear(inverse, inverse @ command, bounds=(low, high),
                                              method="bvls", tol=1e-9, max_iter=50)
                        if not solution.success or not np.isfinite(solution.x).all():
                            raise RuntimeError("Bounded torque allocation failed; no fallback")
                        allocated = solution.x
                        assert np.all(allocated >= low-1e-9) and np.all(allocated <= high+1e-9)
                        optimized = True
                    allocation_ns = time.perf_counter_ns() - started
                    brake_record = None
                    if (profile["name"] == "velocity-brake"
                            and native.sim.data.time < brake_time+.05-1e-10):
                        allocated, brake_record = velocity_brake(
                            joint, step_s=float(native.sim.model.opt.timestep))
                    if args.saturation_case or args.torque_allocation or args.velocity_brake:
                        torque_records.append({
                            "sim_time": float(native.sim.data.time),
                            "command": np.asarray(command).tolist(),
                            "clipped": np.clip(command, low, high).tolist(),
                            "allocated": np.asarray(allocated).tolist(),
                            "optimized": optimized, "allocation_ns": allocation_ns,
                            "velocity_brake": brake_record,
                        })
                    return allocated
                return torques

            run_controller.paused = False
            osc.run_controller = run_controller
            for source_index, row in enumerate(case["rows"]):
                command_context["grip"] = float(row["action"][6])
                command_context.update(index=source_index, action=row["action"])
                env.step(row["action"])
                measured = measure()
                capture("step_end")
                unchanged_until = (brake_time-.2 if profile["name"] == "carry-governor"
                                   else brake_time)
                if measured["sim_time"] < unchanged_until - 1e-10:
                    expected = row["judge"]
                    comparisons.append(float(max(
                        np.max(np.abs(np.array(measured["xyz"]) - expected["xyz"])),
                        np.max(np.abs(np.array(measured["joints"]) - expected["joints"])),
                        abs(measured["sim_time"] - expected["sim_time"]),
                    )))
            assert samples and abs(samples[0]["sim_time"] - start) < 1e-9, "Origin not sampled"
            assert abs(samples[-1]["sim_time"] - end) < 1e-9, "Window end not sampled"
            outcome["max_prebrake_reference_error"] = max(comparisons)
            outcome["reference_prefix_end_s"] = unchanged_until
            assert outcome["max_prebrake_reference_error"] <= 1e-6, "Prebrake mismatch"
            if profile["name"] != "carry-governor":
                assert outcome["entry_joint_error_rad"] <= 1e-6, "Brake-entry mismatch"
            if profile["name"] == "baseline":
                bytime = {}
                for index, sample in enumerate(samples):
                    bytime.setdefault(round(sample["sim_time"], 9), []).append((index, sample))
                errors = []
                matches = []
                for expected in case["held"]:
                    candidates = bytime[round(expected["sim_time"], 9)]
                    def reference_error(candidate):
                        _, measured = candidate
                        return float(max(
                            np.max(np.abs(np.array(measured["xyz"]) - expected["xyz"])),
                            np.max(np.abs(np.array(measured["joints"]) - expected["joints"])),
                        ))
                    index, measured = min(candidates, key=reference_error)
                    errors.append(reference_error((index, measured)))
                    matches.append({"sample_index": index, "error": errors[-1]})
                    assert measured["grasp_contacts"] == expected["grasp_contacts"]
                outcome["max_hold_reference_error"] = max(errors)
                (trial / "reference-matches.json").write_text(json.dumps(matches, indent=2))
                assert outcome["max_hold_reference_error"] <= 1e-6, "Held-state mismatch"
            xyz = np.array([s["xyz"] for s in samples])
            joints = np.array([s["joints"] for s in samples])
            outcome.update(
                sample_count=len(samples), physical_window_s=end-start,
                min_lift_m=float(np.min(xyz[:, 2]) - initial[2]),
                max_translation_m=float(np.max(np.linalg.norm(xyz - xyz[0], axis=1))),
                max_joint_range_rad=float(np.max(np.ptp(joints, axis=0))),
                all_grasp_contacts=all(s["grasp_contacts"] for s in samples),
            )
            outcome["physical_window_passed"] = (
                outcome["min_lift_m"] >= .08 and outcome["max_translation_m"] <= .01
                and outcome["max_joint_range_rad"] <= .02
                and outcome["all_grasp_contacts"] and outcome["physical_window_s"] > 1
            )
            pixels = native.sim.render(camera_name="agentview", width=256, height=256)
            Image.fromarray(np.ascontiguousarray(pixels[::-1, ::-1])).save(trial / "held-end.png")
        except Exception as caught:
            outcome["error"] = repr(caught)
        finally:
            if env is not None:
                env.close()
        (trial / "samples.json").write_text(json.dumps(samples, indent=2))
        if args.saturation_case or args.torque_allocation or args.velocity_brake:
            (trial / "torques.json").write_text(json.dumps(torque_records, indent=2))
        if args.carry_governor:
            (trial / "governor.json").write_text(json.dumps(governor_records, indent=2))
        (trial / "result.json").write_text(json.dumps(outcome, indent=2))
        report["trials"].append(outcome)
        (args.output / "report.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(outcome), flush=True)
        if outcome["error"]:
            raise SystemExit("Replay mismatch retained; remaining grid not attempted")
