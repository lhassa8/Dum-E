"""Independent physics judge for the experimental narrow-port camera actor."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.carry_model import CarryModel
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.release_model import ReleaseModel
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
parser.add_argument("--fixture", type=Path, required=True)
parser.add_argument("--split", choices=["pilot", "heldout", "validation", "test"], default="pilot")
parser.add_argument("--return-after-delivery", action="store_true")
parser.add_argument("--carry-model", type=Path)
parser.add_argument("--carry-policy", choices=["full_xyz", "xy_descent"], default="xy_descent")
parser.add_argument("--release-model", type=Path)
parser.add_argument("--recover-ik", action="store_true")
parser.add_argument("--verify-motion", action="store_true")
parser.add_argument("--release-fallback", action="store_true")
parser.add_argument("--linear-lifts", action="store_true")
parser.add_argument("--center-grasp", action="store_true")
parser.add_argument("--safe-handoff", action="store_true")
parser.add_argument("--alternate-view", action="store_true")
parser.add_argument(
    "--release-kind", choices=["ensemble", "linear", "constant"], default="ensemble"
)
args = parser.parse_args()
fixture = json.loads(args.fixture.read_text())
args.output.mkdir(parents=True, exist_ok=False)
rows = []
carry_model = CarryModel(args.carry_model) if args.carry_model else None
release_model = (
    ReleaseModel(args.release_model, kind=args.release_kind) if args.release_model else None
)
for case in fixture["cases"]:
    if case["split"] != args.split:
        continue
    b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=args.alternate_view))
    b.model.vis.headlight.diffuse[:] *= case.get("light", 1)
    sensor = CameraSensor(b)
    start_truth = b.observe()
    initial = start_truth[case["tool"]]
    target = HANDOFF["handoff"] if case["journey"] != "redirect" else initial[:2]
    controller = CameraDelivery(
        SimRobot(b, recover_ik=args.recover_ik),
        sensor,
        case["tool"],
        HANDOFF["handoff"],
        carry_model=carry_model,
        carry_policy=args.carry_policy,
        release_model=release_model,
        verify_motion=args.verify_motion,
        release_fallback=args.release_fallback,
        linear_lifts=args.linear_lifts,
        center_grasp=args.center_grasp,
        safe_handoff=args.safe_handoff,
        alternate_view=args.alternate_view,
    )
    images = args.output / case["id"]
    images.mkdir()
    max_height = float(initial[2])
    previous, paused, hold = None, False, None
    began = perf_counter()
    maximum_disturbance = 0.0

    def measured_disturbance():
        return max(
            float(np.linalg.norm(b.observe()[n] - xyz))
            for n, xyz in start_truth.items()
            if n != case["tool"]
        )

    try:
        for tick in range(3000):
            if not controller.advance():
                break
            actual = b.observe()[case["tool"]]
            maximum_disturbance = max(maximum_disturbance, measured_disturbance())
            max_height = max(max_height, float(actual[2]))
            if controller.phase != previous:
                Image.fromarray(sensor.capture().rgb).save(images / f"{tick:04d}.png")
                previous = controller.phase
            if (
                case["journey"] in {"resume", "redirect"}
                and not paused
                and controller.phase == "Moving to target"
            ):
                controller.pause()
                stopped = b.data.qpos[:7].copy()
                grip_command = float(b.data.ctrl[7])
                for _ in range(19):
                    b.tick()
                    maximum_disturbance = max(maximum_disturbance, measured_disturbance())
                hold = {
                    "duration_s": 19 * 0.032,
                    "joint_drift_rad": float(np.max(np.abs(b.data.qpos[:7] - stopped))),
                    "grip_retained": bool(b.data.ctrl[7] == grip_command),
                    "actual_tool_height_m": float(b.observe()[case["tool"]][2]),
                }
                if case["journey"] == "redirect":
                    controller.return_to_rack()
                else:
                    controller.resume()
                paused = True
        else:
            raise RuntimeError("Controller exceeded the fixed 3000-frame limit")
        final = b.observe()[case["tool"]]
        address = b.model.joint(f"{case['tool']}_joint").dofadr[0]
        speed = float(np.linalg.norm(b.data.qvel[address : address + 3]))
        distance = float(np.linalg.norm(final[:2] - target))
        lifted = max_height - initial[2] >= 0.08
        placed = distance < 0.035 and final[2] < 0.04 and speed < 0.03
        gripper_open = bool(b.data.qpos[7:9].sum() > 0.07)
        released = controller.outcome.status == "released_unverified" and gripper_open
        disturbance = max(
            float(np.linalg.norm(b.observe()[n] - xyz))
            for n, xyz in start_truth.items()
            if n != case["tool"]
        )
        return_result = None
        if (
            args.return_after_delivery
            and case["journey"] != "redirect"
            and lifted
            and placed
            and released
        ):
            returned = CameraDelivery(
                SimRobot(b, recover_ik=args.recover_ik),
                sensor,
                case["tool"],
                controller.rack_xy,
                carry_model=carry_model,
                carry_policy=args.carry_policy,
                release_model=release_model,
                verify_motion=args.verify_motion,
                release_fallback=args.release_fallback,
                linear_lifts=args.linear_lifts,
                center_grasp=args.center_grasp,
                safe_handoff=args.safe_handoff,
                alternate_view=args.alternate_view,
            )
            return_initial = b.observe()[case["tool"]].copy()
            return_max = float(return_initial[2])
            for _ in range(3000):
                if not returned.advance():
                    break
                maximum_disturbance = max(maximum_disturbance, measured_disturbance())
                return_max = max(return_max, float(b.observe()[case["tool"]][2]))
            else:
                raise RuntimeError("Return exceeded the fixed 3000-frame limit")
            actual_return = b.observe()[case["tool"]]
            return_distance = float(np.linalg.norm(actual_return[:2] - initial[:2]))
            return_speed = float(np.linalg.norm(b.data.qvel[address : address + 3]))
            return_result = {
                "actor_outcome": returned.outcome.__dict__,
                "observations": returned.evidence,
                "ik_events": returned.robot.ik_events,
                "lifted": bool(return_max - return_initial[2] >= 0.08),
                "gripper_open": bool(b.data.qpos[7:9].sum() > 0.07),
                "placed": bool(
                    return_distance < 0.035 and actual_return[2] < 0.04 and return_speed < 0.03
                ),
                "distance_m": return_distance,
                "final_height_m": float(actual_return[2]),
                "speed_m_s": return_speed,
                "max_lift_m": float(return_max - return_initial[2]),
            }
            disturbance = max(
                disturbance,
                max(
                    float(np.linalg.norm(b.observe()[n] - xyz))
                    for n, xyz in start_truth.items()
                    if n != case["tool"]
                ),
            )
            Image.fromarray(sensor.capture().rgb).save(images / "returned.png")
        final_disturbance = measured_disturbance()
        disturbance = max(disturbance, maximum_disturbance)
        passed = bool(
            lifted
            and placed
            and released
            and disturbance < 0.004
            and (hold is None or (hold["grip_retained"] and hold["joint_drift_rad"] < 0.03))
            and (
                return_result is None
                or (
                    return_result["lifted"]
                    and return_result["placed"]
                    and return_result["gripper_open"]
                    and return_result["actor_outcome"]["status"] == "released_unverified"
                )
            )
        )
        row = {
            "case": case,
            "actor_outcome": controller.outcome.__dict__,
            "physics": {
                "lifted": bool(lifted),
                "placed": bool(placed),
                "gripper_open": gripper_open,
                "actor_released": bool(released),
                "distance_m": distance,
                "max_lift_m": float(max_height - initial[2]),
                "final_height_m": float(final[2]),
                "speed_m_s": speed,
                "other_tool_disturbance_m": disturbance,
                "other_tool_final_displacement_m": final_disturbance,
                "disturbance_scope": "Maximum at every32ms motion/hold frame; both legs",
            },
            "hold": hold,
            "return": return_result,
            "passed": passed,
            "wall_s": perf_counter() - began,
            "observations": controller.evidence,
            "ik_events": controller.robot.ik_events,
        }
        rows.append(row)
        (args.output / "results.json").write_text(json.dumps(rows, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "id": case["id"],
                    "outcome": row["actor_outcome"],
                    "physics": row["physics"],
                    "hold": hold,
                    "return": None
                    if return_result is None
                    else {k: v for k, v in return_result.items() if k != "observations"},
                    "passed": passed,
                }
            ),
            flush=True,
        )
    finally:
        sensor.close()
        b.close()
summary = {
    "fixture_sha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
    "split": args.split,
    "cases": len(rows),
    "physical_successes": sum(r["physics"]["lifted"] and r["physics"]["placed"] for r in rows),
    "all_criteria_successes": sum(r["passed"] for r in rows),
    "fresh_camera_return_count": sum(r["return"] is not None for r in rows),
    "passed": sum(r["passed"] for r in rows) / max(len(rows), 1) >= 0.95,
    "carry_model_sha256": None
    if args.carry_model is None
    else hashlib.sha256(args.carry_model.read_bytes()).hexdigest(),
    "carry_policy": args.carry_policy if args.carry_model else "rigid",
    "release_model_sha256": None
    if args.release_model is None
    else hashlib.sha256(args.release_model.read_bytes()).hexdigest(),
    "release_kind": args.release_kind if args.release_model else None,
    "recover_ik": args.recover_ik,
    "verify_motion": args.verify_motion,
    "release_fallback": args.release_fallback,
    "linear_lifts": args.linear_lifts,
    "center_grasp": args.center_grasp,
    "safe_handoff": args.safe_handoff,
    "alternate_view": args.alternate_view,
    "return_after_delivery": args.return_after_delivery,
    "accepted_alternate_views": sum(
        e.get("view") == "alternate" and e.get("accepted", False)
        for row in rows
        for e in row["observations"]
        + ([] if row["return"] is None else row["return"]["observations"])
    ),
    "disturbance_judge": "Maximum across motion/hold frames, not just final position",
    "release_judge": (
        "Actor finished release/withdrawal and independently measured open gripper; "
        "resting placement still required"
    ),
}
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary), flush=True)
