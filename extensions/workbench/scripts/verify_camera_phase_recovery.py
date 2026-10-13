"""Independent full physical journeys after long interruptions across actor phases."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--phase-recovery", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
protocol_bytes = (root / "fixtures/camera_phase_recovery_protocol.json").read_bytes()
protocol = json.loads(protocol_bytes)
fixture = (root / "fixtures" / protocol["layout_fixture"]).read_bytes()
assert hashlib.sha256(fixture).hexdigest() == protocol["layout_fixture_sha256"]
cases = {c["id"]: c for c in json.loads(fixture)["cases"]}
args.output.mkdir(parents=True, exist_ok=False)
rows = []
c = protocol["criteria"]
for ident in protocol["cases"]:
    case = cases[ident]
    for phase in protocol["phases"]:
        bench = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=True))
        bench.model.vis.headlight.diffuse[:] *= case["light"]
        sensor = CameraSensor(bench)
        robot = SimRobot(bench, recover_ik=True)
        flags = {k: v for k, v in protocol["profile"].items() if k != "recover_ik"}
        if args.phase_recovery:
            flags["phase_recovery"] = True
        actor = CameraDelivery(robot, sensor, case["tool"], HANDOFF["handoff"], **flags)
        truth = bench.observe
        initial = truth()
        name = case["tool"]

        def denied(*unused):
            raise AssertionError("Actor accessed privileged object state")

        bench.observe = bench.tool_support_height = denied
        max_height = initial[name][2]
        disturbance = 0.0

        def measure():
            global max_height, disturbance
            positions = truth()
            max_height = max(max_height, positions[name][2])
            disturbance = max(
                disturbance,
                max(
                    float(np.linalg.norm(positions[n] - p)) for n, p in initial.items() if n != name
                ),
            )
            return positions[name]

        row = {"case": ident, "tool": name, "phase": phase, "passed": False}
        try:
            for _ in range(3000):
                if not actor.advance():
                    raise RuntimeError("Actor ended before pause phase")
                position = measure()
                if actor.phase == phase and (
                    not actor.carrying or position[2] > protocol["held_pause_height_min_m"]
                ):
                    break
            else:
                raise RuntimeError("Pause phase not reached")
            joints = robot.read().joints
            grip = float(bench.data.ctrl[7])
            carried = actor.carrying
            stopped = position.copy()
            actor.pause()
            start = bench.data.time
            drift = translation = 0.0
            retained = True
            for _ in range(int(round(protocol["hold_seconds"] / 0.032))):
                bench.tick()
                position = measure()
                drift = max(drift, float(np.max(np.abs(robot.read().joints - joints))))
                translation = max(translation, float(np.linalg.norm(position - stopped)))
                retained &= bench.data.ctrl[7] == grip
            held = (
                drift < c["joint_drift_max_rad"]
                and retained
                and (not carried or translation < c["held_translation_max_m"])
            )
            row["hold"] = {
                "simulation_seconds": bench.data.time - start,
                "joint_drift_rad": drift,
                "tool_translation_m": translation,
                "grip_command_retained": bool(retained),
                "carrying": carried,
                "passed": bool(held),
            }
            actor.resume()
            for _ in range(3000):
                if not actor.advance():
                    break
                measure()
            else:
                raise RuntimeError("Continuation exceeded bound")
            actual = measure()
            address = bench.model.joint(f"{name}_joint").dofadr[0]
            speed = float(np.linalg.norm(bench.data.qvel[address : address + 3]))
            distance = float(np.linalg.norm(actual[:2] - HANDOFF["handoff"]))
            opened = bool(bench.data.qpos[7:9].sum() > 0.07)
            row.update(
                actor_status=actor.outcome.status if actor.outcome else None,
                actor_message=actor.outcome.message if actor.outcome else None,
                distance_m=distance,
                height_m=float(actual[2]),
                speed_m_s=speed,
                lift_m=float(max_height - initial[name][2]),
                unrelated_m=disturbance,
                gripper_open=opened,
                evidence=actor.evidence,
            )
            row["passed"] = bool(
                held
                and distance < c["placement_distance_max_m"]
                and actual[2] < c["rest_height_max_m"]
                and speed < c["rest_speed_max_m_s"]
                and max_height - initial[name][2] >= c["lift_min_m"]
                and disturbance < c["unrelated_translation_max_m"]
                and opened
                and actor.outcome
                and actor.outcome.status == "released_unverified"
            )
        except (ValueError, RuntimeError) as error:
            row["error"] = str(error)
        finally:
            sensor.close()
            bench.close()
        rows.append(row)
        (args.output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(json.dumps({k: v for k, v in row.items() if k != "evidence"}), flush=True)
summary = {
    "scope": protocol["scope"],
    "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
    "phase_recovery": args.phase_recovery,
    "cases": len(rows),
    "passes": sum(r["passed"] for r in rows),
    "passed": all(r["passed"] for r in rows),
}
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
