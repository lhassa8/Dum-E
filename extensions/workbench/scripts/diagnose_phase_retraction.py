"""Post-hoc robot-only path diagnosis for the two evaluated hammer refusals."""

import argparse
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--refine-cartesian", action="store_true")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
protocol = json.loads((root / "fixtures/camera_phase_recovery_protocol.json").read_text())
case = next(
    c
    for c in json.loads((root / "fixtures/release_model_cases.json").read_text())["cases"]
    if c["id"] == "validation-002"
)
rows = []
for phase in ["Lowering gripper", "Grasping"]:
    bench = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=True))
    bench.model.vis.headlight.diffuse[:] *= case["light"]
    camera = CameraSensor(bench)
    robot = SimRobot(bench, recover_ik=True, refine_cartesian=args.refine_cartesian)
    actor = CameraDelivery(
        robot,
        camera,
        case["tool"],
        HANDOFF["handoff"],
        phase_recovery=True,
        **{k: v for k, v in protocol["profile"].items() if k != "recover_ik"},
    )

    def denied(*unused):
        raise AssertionError("Privileged object state unavailable")

    truth = bench.observe  # Independent diagnostic only; never returned to the actor.
    bench.observe = bench.tool_support_height = denied
    original_path = robot.cartesian_path
    row = {"case": case["id"], "phase": phase, "scope": "post-hoc diagnosis, not qualification"}

    def diagnose(start, point, rotation, ticks):
        try:
            return original_path(start, point, rotation, ticks)
        except ValueError:
            before = bench.data.qpos.copy(), bench.data.qvel.copy(), bench.data.ctrl.copy()
            previous = robot.read().joints
            row.update(
                motion_phase=actor.phase,
                start_m=start.tolist(),
                target_m=point.tolist(),
                ticks=ticks,
            )
            for index in range(1, ticks + 1):
                a = index / ticks
                waypoint = start + (point - start) * (a * a * (3 - 2 * a))
                answer = robot._seed_solution(waypoint, rotation, previous)
                delta = np.abs(answer - previous)
                if delta.max() > 0.075:
                    position_error, angle_error = robot._pose_error(answer, waypoint, rotation)
                    row.update(
                        rejected_waypoint=index,
                        delta_max_rad=float(delta.max()),
                        joint_index=int(delta.argmax()),
                        waypoint_m=waypoint.tolist(),
                        endpoint_position_error_m=position_error,
                        endpoint_angle_error_rad=angle_error,
                        threshold_rad=0.075,
                    )
                    break
                previous = answer
            row["diagnostic_state_unchanged"] = all(
                np.array_equal(a, b)
                for a, b in zip(
                    before, [bench.data.qpos, bench.data.qvel, bench.data.ctrl], strict=True
                )
            )
            refinements = []
            for multiplier in [2, 4]:
                probe = {"ticks": ticks * multiplier, "passed": False}
                try:
                    path = original_path(start, point, rotation, ticks * multiplier)
                    differences = np.diff(np.vstack([robot.read().joints, path]), axis=0)
                    probe.update(passed=True, max_joint_step_rad=float(np.abs(differences).max()))
                except ValueError as error:
                    probe["refusal"] = str(error)
                refinements.append(probe)
            row["fixed_refinement_probe"] = refinements
            row["refinement_state_unchanged"] = all(
                np.array_equal(a, b)
                for a, b in zip(
                    before, [bench.data.qpos, bench.data.qvel, bench.data.ctrl], strict=True
                )
            )
            raise

    robot.cartesian_path = diagnose
    try:
        for _ in range(3000):
            if not actor.advance():
                raise RuntimeError("Pause phase not reached")
            if actor.phase == phase:
                break
        actor.pause()
        for _ in range(1000):
            bench.tick()
        actor.resume()
        carried_samples = {}
        for _ in range(3000):
            if not actor.advance():
                break
            if actor.carrying:
                estimated, _ = actor._estimate()
                actual = truth()[case["tool"]]
                carried_samples[actor.phase] = {
                    "actual_m": actual.tolist(),
                    "estimated_m": estimated.tolist(),
                    "estimate_error_m": float(np.linalg.norm(estimated - actual)),
                    "actual_target_xy_error_m": float(np.linalg.norm(actual[:2] - actor.target)),
                    "gap_m": robot.read().gap_m,
                }
        row["last_carried_sample_per_phase"] = carried_samples
        row["final_actual_m"] = truth()[case["tool"]].tolist()
        row["refine_cartesian"] = args.refine_cartesian
        row["actor_message"] = actor.outcome.message if actor.outcome else None
        if actor.outcome and actor.outcome.status == "released_unverified":
            before = bench.data.qpos.copy(), bench.data.qvel.copy(), bench.data.ctrl.copy()
            actor.phase = "Post-release camera diagnostic"
            try:
                observed = actor._observe()
                actual = truth()[case["tool"]]
                row["postrelease_camera"] = {
                    "accepted": True,
                    "fit_score": observed.fit_score,
                    "observed_target_error_m": float(
                        np.linalg.norm(observed.position_m[:2] - actor.target)
                    ),
                    "actual_target_error_m": float(np.linalg.norm(actual[:2] - actor.target)),
                    "position_error_m": float(np.linalg.norm(observed.position_m - actual)),
                }
            except ValueError as error:
                row["postrelease_camera"] = {"accepted": False, "refusal": str(error)}
            row["postrelease_camera"]["state_unchanged"] = all(
                np.array_equal(a, b)
                for a, b in zip(
                    before, [bench.data.qpos, bench.data.qvel, bench.data.ctrl], strict=True
                )
            )
    finally:
        camera.close()
        bench.close()
    rows.append(row)
(args.output / "diagnosis.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps(rows, indent=2))
