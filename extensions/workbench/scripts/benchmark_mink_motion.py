"""Compare complete physical journeys through a frozen published camera runtime."""

import argparse
import hashlib
import importlib.metadata
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
from mink_robot_adapter import MinkRobot
from PIL import Image

from physical_ai_lab.assistant import camera_tasks
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-source", type=Path, required=True)
    args = parser.parse_args()
    source = Path(camera_tasks.__file__).resolve()
    assert source.is_relative_to(args.reference_source.resolve()), source
    root = Path(__file__).resolve().parents[1]
    raw = (root / "fixtures/mink_motion_protocol.json").read_bytes()
    protocol = json.loads(raw)
    criteria = protocol["criteria"]
    args.output.mkdir(parents=True, exist_ok=False)
    original_guard = camera_tasks.GuardedRobot

    class MinkGuardedRobot(original_guard, MinkRobot):
        """Keep the original cancellation/worker boundary, replace only IK."""

    report = {
        "reference_revision": protocol["reference_revision"],
        "source_path": str(source),
        "protocol_sha256": hashlib.sha256(raw).hexdigest(),
        "source_hashes": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source.parent.glob("*.py")
        },
        "packages": {
            name: importlib.metadata.version(name)
            for name in ("mink", "mujoco", "qpsolvers", "daqp", "numpy")
        },
        "scope": "Known default layouts, full physical journeys; no acoustic or held-out claim",
        "rows": [],
    }
    for seed in protocol["seeds"]:
        for tool in protocol["tools"]:
            for backend in protocol["backends"]:
                camera_tasks.SimRobot = MinkRobot if backend == "mink" else SimRobot
                camera_tasks.GuardedRobot = (
                    MinkGuardedRobot if backend == "mink" else original_guard
                )
                bench = ToolWorkbench(
                    seed, xml=camera_scene_xml({"layout": {}}, alternate_view=True)
                )
                truth = bench.observe
                racks = {name: xyz[:2].copy() for name, xyz in truth().items()}
                native_tick = bench.tick
                evaluation = {}

                def measured_tick(*inputs, **options):
                    native_tick(*inputs, **options)
                    if evaluation:
                        positions = truth()
                        evaluation["maximum"] = max(evaluation["maximum"], positions[tool][2])
                        evaluation["unrelated"] = max(
                            evaluation["unrelated"],
                            max(
                                float(np.linalg.norm(xyz - evaluation["initial"][name]))
                                for name, xyz in positions.items()
                                if name != tool
                            ),
                        )

                def denied(*unused):
                    raise AssertionError("Actor requested privileged object state")

                bench.tick = measured_tick
                hub = None
                try:
                    epoch = [0]
                    hub = camera_tasks.CameraTasks(bench, epoch=lambda: epoch[0])
                    bench.observe = bench.tool_support_height = denied
                    for returning in (False, True):
                        initial = truth()
                        evaluation = {
                            "initial": initial,
                            "maximum": float(initial[tool][2]),
                            "unrelated": 0.0,
                        }
                        controller = hub.select(tool, returning)
                        hold = None
                        began = time.perf_counter()
                        phases = []
                        for step in range(protocol["frame_limit"]):
                            more = controller.advance()
                            if not phases or phases[-1] != controller.phase:
                                phases.append(controller.phase)
                            if not more:
                                break
                            if (
                                not returning
                                and hold is None
                                and controller.phase == protocol["stop_phase"]
                            ):
                                epoch[0] += 1
                                controller.pause()
                                held_joints = bench.data.qpos[:7].copy()
                                held_tool = truth()[tool].copy()
                                drift_joints, drift_tool, minimum = 0.0, 0.0, float(held_tool[2])
                                hold_started = float(bench.data.time)
                                for _ in range(protocol["hold_frames"]):
                                    bench.tick()
                                    controller.measure()
                                    xyz = truth()[tool]
                                    drift_joints = max(
                                        drift_joints,
                                        float(np.max(np.abs(bench.data.qpos[:7] - held_joints))),
                                    )
                                    drift_tool = max(
                                        drift_tool, float(np.linalg.norm(xyz - held_tool))
                                    )
                                    minimum = min(minimum, float(xyz[2]))
                                held_airborne = held_tool[2] >= criteria["airborne_min_m"]
                                hold = {
                                    "sim_seconds": float(bench.data.time) - hold_started,
                                    "joint_drift_rad": drift_joints,
                                    "tool_drift_m": drift_tool,
                                    "minimum_height_m": minimum,
                                    "passed": drift_joints < criteria["held_joint_drift_rad"]
                                    and drift_tool < criteria["held_tool_drift_m"]
                                    and (
                                        not held_airborne or minimum >= criteria["airborne_min_m"]
                                    ),
                                }
                                controller.resume()
                        actual = truth()[tool]
                        target = racks[tool] if returning else HANDOFF["handoff"]
                        distance = float(np.linalg.norm(actual[:2] - target))
                        address = int(bench.model.joint(f"{tool}_joint").dofadr[0])
                        speed = float(np.linalg.norm(bench.data.qvel[address : address + 3]))
                        lift = evaluation["maximum"] - initial[tool][2]
                        opened = bool(
                            bench.data.qpos[7:9].sum() > 0.075 and bench.data.ctrl[7] > 200
                        )
                        physical_pass = (
                            distance < criteria["placement_m"]
                            and actual[2] < criteria["rest_height_m"]
                            and speed < criteria["rest_speed_m_s"]
                            and lift > criteria["lift_m"]
                            and evaluation["unrelated"] < criteria["unrelated_translation_m"]
                            and opened
                        )
                        passed = (
                            physical_pass
                            and controller.outcome is not None
                            and controller.outcome.status == "success"
                            and (returning or hold is not None and hold["passed"])
                        )
                        row = {
                            "backend": backend,
                            "seed": seed,
                            "tool": tool,
                            "returning": returning,
                            "steps": step,
                            "phases": phases,
                            "elapsed_ms": (time.perf_counter() - began) * 1000,
                            "hold": hold,
                            "distance_m": distance,
                            "lift_m": float(lift),
                            "height_m": float(actual[2]),
                            "speed_m_s": speed,
                            "unrelated_m": evaluation["unrelated"],
                            "gripper_open": opened,
                            "physical_pass": bool(physical_pass),
                            "passed": bool(passed),
                            "outcome": asdict(controller.outcome) if controller.outcome else None,
                            "robot_plans": controller.robot.ik_events,
                            "actor_evidence": controller.actor.evidence,
                        }
                        report["rows"].append(row)
                        print(
                            json.dumps(
                                {
                                    k: v
                                    for k, v in row.items()
                                    if k not in ("robot_plans", "actor_evidence")
                                }
                            ),
                            flush=True,
                        )
                        if not passed:
                            Image.fromarray(hub.sensor.capture().rgb).save(
                                args.output / f"failure-{backend}-{seed}-{tool}-{returning}.png"
                            )
                            break
                except Exception as exc:
                    report["rows"].append(
                        {
                            "backend": backend,
                            "seed": seed,
                            "tool": tool,
                            "passed": False,
                            "error": repr(exc),
                        }
                    )
                    print(repr(exc), flush=True)
                finally:
                    if hub is not None:
                        hub.close()
                    bench.close()
                    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    for backend in protocol["backends"]:
        rows = [row for row in report["rows"] if row["backend"] == backend]
        report[backend] = {
            "planned_legs": len(protocol["seeds"]) * len(protocol["tools"]) * 2,
            "recorded_rows": len(rows),
            "passed_legs": sum(row["passed"] for row in rows),
        }
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({backend: report[backend] for backend in protocol["backends"]}, indent=2))


if __name__ == "__main__":
    main()
