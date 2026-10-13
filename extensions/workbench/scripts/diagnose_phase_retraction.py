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
    robot = SimRobot(bench, recover_ik=True)
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
        for _ in range(3000):
            if not actor.advance():
                break
        row["actor_message"] = actor.outcome.message if actor.outcome else None
    finally:
        camera.close()
        bench.close()
    rows.append(row)
(args.output / "diagnosis.json").write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps(rows, indent=2))
