"""Independent complete journeys after Stop inside known grip-loss recovery."""

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
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
protocol_bytes = (root / "fixtures/camera_grip_interrupt_protocol.json").read_bytes()
protocol = json.loads(protocol_bytes)
fixture_bytes = (root / protocol["fixture"]).read_bytes()
assert hashlib.sha256(fixture_bytes).hexdigest() == protocol["fixture_sha256"]
case = next(c for c in json.loads(fixture_bytes)["cases"] if c["id"] == protocol["case"])
criteria = protocol["criteria"]
args.output.mkdir(parents=True, exist_ok=False)
rows = []
for phase in protocol["phases"]:
    bench = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=True))
    bench.model.vis.headlight.diffuse[:] *= case["light"]
    sensor = CameraSensor(bench)
    robot = SimRobot(bench, recover_ik=True, refine_cartesian=True)
    actor = CameraDelivery(
        robot,
        sensor,
        case["tool"],
        HANDOFF["handoff"],
        verify_motion=True,
        linear_lifts=True,
        center_grasp=True,
        safe_handoff=True,
        alternate_view=True,
        release_fallback=True,
        phase_recovery=True,
        verify_release=True,
        recover_grip=True,
    )
    truth = bench.observe
    initial = truth()
    name = case["tool"]

    def denied(*unused):
        raise AssertionError("Actor accessed privileged object state")

    bench.observe = bench.tool_support_height = denied
    maximum_height = initial[name][2]
    disturbance = 0.0

    def measure():
        global maximum_height, disturbance
        positions = truth()
        maximum_height = max(maximum_height, positions[name][2])
        disturbance = max(
            disturbance,
            max(
                float(np.linalg.norm(positions[n] - xyz)) for n, xyz in initial.items() if n != name
            ),
        )
        return positions[name]

    redirected = False
    row = {"phase": phase, "passed": False}
    try:
        for _ in range(protocol["frame_limit"]):
            if not actor.advance():
                raise RuntimeError("Recovery interruption phase not reached")
            measure()
            if not redirected and actor.phase == "Moving to target":
                actor.pause()
                for _ in range(19):
                    bench.tick()
                    measure()
                actor.return_to_rack()
                redirected = True
            if actor.grip_recovery_attempts == 1 and actor.phase == phase:
                break
        else:
            raise RuntimeError("Recovery interruption phase not reached within bound")
        actor.pause()
        stopped_joints = robot.read().joints
        grip = bench.data.ctrl[7]
        drift = 0.0
        retained = True
        for _ in range(round(protocol["stop_seconds"] / 0.032)):
            bench.tick()
            measure()
            drift = max(drift, float(np.max(np.abs(robot.read().joints - stopped_joints))))
            retained &= bench.data.ctrl[7] == grip
        row["hold"] = {
            "simulation_seconds": protocol["stop_seconds"],
            "joint_drift_rad": drift,
            "gripper_command_retained": bool(retained),
            "passed": bool(drift < criteria["joint_drift_max_rad"] and retained),
        }
        actor.resume()
        for _ in range(protocol["frame_limit"]):
            if not actor.advance():
                break
            measure()
        else:
            raise RuntimeError("Continuation exceeded original frame bound")
        actual = measure()
        address = bench.model.joint(f"{name}_joint").dofadr[0]
        speed = float(np.linalg.norm(bench.data.qvel[address : address + 3]))
        distance = float(np.linalg.norm(actual[:2] - initial[name][:2]))
        opened = bool(bench.data.qpos[7:9].sum() > 0.07)
        row.update(
            distance_m=distance,
            height_m=float(actual[2]),
            speed_m_s=speed,
            lift_m=float(maximum_height - initial[name][2]),
            unrelated_m=disturbance,
            gripper_open=opened,
            actor_outcome=actor.outcome.__dict__ if actor.outcome else None,
            grip_recovery_attempts=actor.grip_recovery_attempts,
            evidence=actor.evidence,
        )
        row["passed"] = bool(
            row["hold"]["passed"]
            and distance < criteria["placement_distance_max_m"]
            and actual[2] < criteria["rest_height_max_m"]
            and speed < criteria["rest_speed_max_m_s"]
            and maximum_height - initial[name][2] >= criteria["lift_min_m"]
            and disturbance < criteria["unrelated_translation_max_m"]
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
    "cases": len(rows),
    "passes": sum(r["passed"] for r in rows),
    "passed": all(r["passed"] for r in rows),
}
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
