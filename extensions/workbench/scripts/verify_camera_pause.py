"""Independent long-hold/continuation judge for the existing camera motion profile."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--hold-profile", choices=["position", "shared"], required=True)
    parser.add_argument("--protocol", type=Path, default=Path("fixtures/camera_pause_cases.json"))
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    layouts_path = args.protocol.parent / protocol["layout_fixture"]
    layouts_bytes = layouts_path.read_bytes()
    if hashlib.sha256(layouts_bytes).hexdigest() != protocol["layout_fixture_sha256"]:
        parser.error("The frozen layout fixture has changed")
    layouts = {c["id"]: c for c in json.loads(layouts_bytes)["cases"]}
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    criteria = protocol["criteria"]
    for case_id in protocol["cases"]:
        case = layouts[case_id]
        for continuation in protocol["continuations"]:
            bench = ToolWorkbench(case["seed"], xml=camera_scene_xml(case))
            bench.model.vis.headlight.diffuse[:] *= case.get("light", 1)
            sensor = CameraSensor(bench)
            profile = protocol["profile"]
            robot = SimRobot(bench, recover_ik=profile["recover_ik"])
            if args.hold_profile == "position":
                # Reproduce the old adapter for comparison; never freeze a body.
                def position_hold():
                    bench.data.ctrl[:7] = robot.read().joints

                robot.hold = position_hold
            actor = CameraDelivery(
                robot,
                sensor,
                case["tool"],
                HANDOFF["handoff"],
                **{k: v for k, v in profile.items() if k != "recover_ik"},
            )
            truth = bench.observe  # Used only by the independent judge, never by the actor.
            initial = truth()
            tool = case["tool"]
            maximum_disturbance = 0.0
            maximum_height = initial[tool][2]

            def measure():
                nonlocal maximum_disturbance, maximum_height
                positions = truth()
                maximum_height = max(maximum_height, positions[tool][2])
                maximum_disturbance = max(
                    maximum_disturbance,
                    *(
                        float(np.linalg.norm(positions[n] - p))
                        for n, p in initial.items()
                        if n != tool
                    ),
                )
                return positions[tool]

            row = {"case": case_id, "tool": tool, "continuation": continuation}
            try:
                for _ in range(3000):
                    if not actor.advance():
                        raise RuntimeError("Actor ended before the frozen pause point")
                    position = measure()
                    if actor.phase == protocol["pause_phase"] and (
                        position[2] > protocol["pause_at_tool_height_m"]
                    ):
                        break
                else:
                    raise RuntimeError("Frozen pause point was not reached")
                joints = robot.read().joints
                grip = float(bench.data.ctrl[7])
                stopped_position = position.copy()
                minimum_height, drift, translation = float(position[2]), 0.0, 0.0
                grip_retained = True
                actor.pause()
                start_time = bench.data.time
                ticks = int(round(protocol["hold_seconds"] / 0.032))
                for _ in range(ticks):
                    bench.tick()
                    position = measure()
                    minimum_height = min(minimum_height, float(position[2]))
                    drift = max(drift, float(np.max(np.abs(robot.read().joints - joints))))
                    translation = max(
                        translation, float(np.linalg.norm(position - stopped_position))
                    )
                    grip_retained &= float(bench.data.ctrl[7]) == grip
                held = (
                    minimum_height > criteria["held_height_min_m"]
                    and drift < criteria["joint_drift_max_rad"]
                    and translation < criteria["held_translation_max_m"]
                    and grip_retained
                )
                row["hold"] = {
                    "simulation_seconds": float(bench.data.time - start_time),
                    "minimum_tool_height_m": minimum_height,
                    "maximum_joint_drift_rad": drift,
                    "maximum_tool_translation_m": translation,
                    "grip_retained": bool(grip_retained),
                    "passed": bool(held),
                }
                if continuation == "resume":
                    actor.resume()
                    target = HANDOFF["handoff"]
                else:
                    actor.return_to_rack()
                    target = initial[tool][:2]
                for _ in range(3000):
                    if not actor.advance():
                        break
                    measure()
                else:
                    raise RuntimeError("Continuation exceeded the frozen frame limit")
                actual = measure()
                address = bench.model.joint(f"{tool}_joint").dofadr[0]
                speed = float(np.linalg.norm(bench.data.qvel[address : address + 3]))
                distance = float(np.linalg.norm(actual[:2] - target))
                placed = (
                    distance < criteria["placement_distance_max_m"]
                    and actual[2] < criteria["rest_height_max_m"]
                    and speed < criteria["rest_speed_max_m_s"]
                )
                row.update(
                    distance_m=distance,
                    rest_height_m=float(actual[2]),
                    speed_m_s=speed,
                    max_lift_m=float(maximum_height - initial[tool][2]),
                    max_unrelated_translation_m=maximum_disturbance,
                    actor_status=actor.outcome.status if actor.outcome else None,
                    actor_message=actor.outcome.message if actor.outcome else None,
                    passed=bool(
                        held
                        and placed
                        and maximum_height - initial[tool][2] >= criteria["lift_min_m"]
                        and maximum_disturbance < criteria["unrelated_translation_max_m"]
                        and actor.outcome is not None
                        and actor.outcome.status == "released_unverified"
                    ),
                )
            except (ValueError, RuntimeError, FloatingPointError) as error:
                row.update(passed=False, error=str(error))
            finally:
                sensor.close()
                bench.close()
            rows.append(row)
            (args.output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
            print(json.dumps(row), flush=True)
    summary = {
        "scope": protocol["scope"],
        "hold_profile": args.hold_profile,
        "protocol_sha256": hashlib.sha256(args.protocol.read_bytes()).hexdigest(),
        "cases": len(rows),
        "passes": sum(r["passed"] for r in rows),
        "passed": all(r["passed"] for r in rows),
        "rows": rows,
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}), flush=True)
    raise SystemExit(0 if summary["passed"] else 1)


if __name__ == "__main__":
    main()
