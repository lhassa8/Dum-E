"""Posthoc replay of evaluated failures; proprioception and truth labels never feed the actor."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--fixture", type=Path, required=True)
parser.add_argument(
    "--case-ids",
    nargs="+",
    default=["pc-reserved-000", "pc-reserved-009", "pc-reserved-014", "pc-reserved-029"],
)
parser.add_argument("--phase-recovery", action="store_true")
parser.add_argument("--refine-cartesian", action="store_true")
parser.add_argument("--verify-release", action="store_true")
parser.add_argument("--recover-grip", action="store_true")
parser.add_argument(
    "--final-hold",
    action="store_true",
    help="Independent32s hold judge after a carried-tool refusal",
)
parser.add_argument(
    "--gap-brake", action="store_true", help="Post-hoc 2mm shrink trigger and physical 32s hold"
)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
fixture = json.loads(args.fixture.read_text())
reports = []


class Traced(CameraDelivery):
    def _motion(self, point, phase, grip):
        self.requested = (np.array(point).copy(), self.orientation.copy(), phase)
        yield from super()._motion(point, phase, grip)


for ident in args.case_ids:
    case = next(c for c in fixture["cases"] if c["id"] == ident)
    bench = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=True))
    bench.model.vis.headlight.diffuse[:] *= case["light"]
    sensor = CameraSensor(bench)
    truth = bench.observe

    def denied(*unused):
        raise AssertionError("Actor accessed privileged tool state")

    bench.observe = bench.tool_support_height = denied
    name = case["tool"]
    initial = truth()[name].copy()
    target_body = bench.model.body(name).id
    address = bench.model.joint(f"{name}_joint").dofadr[0]
    first = Traced(
        SimRobot(bench, recover_ik=True, refine_cartesian=args.refine_cartesian),
        sensor,
        name,
        HANDOFF["handoff"],
        verify_motion=True,
        linear_lifts=True,
        center_grasp=True,
        safe_handoff=True,
        release_fallback=True,
        alternate_view=True,
        phase_recovery=args.phase_recovery,
        verify_release=args.verify_release,
        recover_grip=args.recover_grip,
    )
    folder = args.output / ident
    folder.mkdir()
    report = {
        "case": ident,
        "scope": "Posthoc diagnostic replay, not new qualification",
        "legs": [],
    }
    try:
        for leg in range(2):
            if leg == 0:
                actor = first
            else:
                if case["journey"] == "redirect" or first.outcome.status != "released_unverified":
                    break
                actor = Traced(
                    SimRobot(bench, recover_ik=True, refine_cartesian=args.refine_cartesian),
                    sensor,
                    name,
                    first.rack_xy,
                    verify_motion=True,
                    linear_lifts=True,
                    center_grasp=True,
                    safe_handoff=True,
                    release_fallback=True,
                    alternate_view=True,
                    phase_recovery=args.phase_recovery,
                    verify_release=args.verify_release,
                    recover_grip=args.recover_grip,
                )
            rows = []
            paused = False

            def measure():
                r = actor.robot.read()
                xyz = truth()[name]
                row = {
                    "time_s": r.time_s,
                    "phase": actor.phase,
                    "gap_m": r.gap_m,
                    "joints": r.joints.tolist(),
                    "joint_velocity": r.joint_velocity.tolist(),
                    "actuator_load": r.actuator_load.tolist(),
                    "tcp_m": r.tcp_m.tolist(),
                    "tool_xyz_evaluator_only": xyz.tolist(),
                    "tool_speed_m_s": float(np.linalg.norm(bench.data.qvel[address : address + 3])),
                }
                if hasattr(actor, "requested"):
                    point, rotation, phase = actor.requested
                    row.update(
                        motion_phase=phase, tcp_error_m=float(np.linalg.norm(r.tcp_m - point))
                    )
                if actor.carrying and actor.offset_local is not None:
                    estimate, _ = actor._estimate()
                    row["rigid_estimate_error_m_evaluator_only"] = float(
                        np.linalg.norm(estimate - xyz)
                    )
                row["tool_contacts_evaluator_only"] = [
                    [bench.model.body(bench.model.geom_bodyid[g]).name for g in (c.geom1, c.geom2)]
                    for c in bench.data.contact[: bench.data.ncon]
                    if target_body
                    in (bench.model.geom_bodyid[c.geom1], bench.model.geom_bodyid[c.geom2])
                ]
                rows.append(row)

            for _ in range(3000):
                before_reading = actor.robot.read()
                was_carrying = actor.carrying
                active = actor.advance()
                measure()
                if not active:
                    break
                shrink = before_reading.gap_m - actor.robot.read().gap_m
                if args.gap_brake and was_carrying and actor.carrying and shrink > 0.002:
                    trigger = rows[-1].copy()
                    stopped = actor.robot.read().joints
                    actor.pause()
                    max_drift = 0.0
                    min_height = float("inf")
                    both_fingers = True
                    for _ in range(1000):
                        bench.tick()
                        measure()
                        max_drift = max(
                            max_drift, float(np.max(np.abs(actor.robot.read().joints - stopped)))
                        )
                        min_height = min(min_height, rows[-1]["tool_xyz_evaluator_only"][2])
                        contacts = {
                            body
                            for pair in rows[-1]["tool_contacts_evaluator_only"]
                            for body in pair
                        }
                        both_fingers &= {"left_finger", "right_finger"} <= contacts
                    report["gap_brake"] = {
                        "threshold_m": 0.002,
                        "shrink_m": shrink,
                        "trigger": trigger,
                        "hold_seconds": 32,
                        "max_joint_drift_rad": max_drift,
                        "minimum_tool_height_m": min_height,
                        "both_finger_contacts_retained": both_fingers,
                        "final_gap_proxy": actor._grip_present(),
                    }
                    break
                if (
                    leg == 0
                    and case["journey"] in ("resume", "redirect")
                    and not paused
                    and actor.phase == "Moving to target"
                ):
                    actor.pause()
                    for _ in range(19):
                        bench.tick()
                        measure()
                    actor.return_to_rack() if case["journey"] == "redirect" else actor.resume()
                    paused = True
            else:
                raise RuntimeError("Diagnostic exceeded original frame bound")
            for view in ("workbench_camera", "workbench_camera_side"):
                Image.fromarray(sensor.capture_view(view).rgb).save(
                    folder / f"leg-{leg}-{view}.png"
                )
            summary = {
                "leg": leg,
                "outcome": actor.outcome.__dict__,
                "samples": len(rows),
                "max_joint_speed_rad_s": max(
                    float(np.max(np.abs(r["joint_velocity"]))) for r in rows
                ),
                "max_tool_speed_m_s": max(r["tool_speed_m_s"] for r in rows),
                "max_rigid_estimate_error_m": max(
                    (r.get("rigid_estimate_error_m_evaluator_only", 0) for r in rows)
                ),
                "final": rows[-1],
                "camera_evidence": actor.evidence,
            }
            (folder / f"leg-{leg}-trace.json").write_text(json.dumps(rows) + "\n")
            report["legs"].append(summary)
        if args.final_hold and actor.carrying and actor.outcome.status == "failed":
            stopped = actor.robot.read().joints
            tool_start = truth()[name].copy()
            command = bench.data.ctrl[7]
            drift = translation = 0.0
            minimum = tool_start[2]
            retained = both_contacts = True
            for _ in range(1000):
                bench.tick()
                xyz = truth()[name]
                drift = max(drift, float(np.max(np.abs(actor.robot.read().joints - stopped))))
                translation = max(translation, float(np.linalg.norm(xyz - tool_start)))
                minimum = min(minimum, xyz[2])
                retained &= bench.data.ctrl[7] == command
                contacts = {
                    bench.model.body(bench.model.geom_bodyid[g]).name
                    for contact in bench.data.contact[: bench.data.ncon]
                    if target_body
                    in (
                        bench.model.geom_bodyid[contact.geom1],
                        bench.model.geom_bodyid[contact.geom2],
                    )
                    for g in (contact.geom1, contact.geom2)
                }
                both_contacts &= {"left_finger", "right_finger"} <= contacts
            report["final_refusal_hold"] = {
                "simulation_seconds": 32,
                "max_joint_drift_rad": drift,
                "max_tool_translation_m": translation,
                "minimum_tool_height_m": float(minimum),
                "gripper_command_retained": bool(retained),
                "both_finger_contacts_retained": both_contacts,
                "passed": bool(
                    drift < 0.02
                    and translation < 0.01
                    and minimum > 0.13
                    and retained
                    and both_contacts
                ),
            }
        reports.append(report)
        (args.output / "report.json").write_text(json.dumps(reports, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "id": ident,
                    "legs": [
                        {k: v for k, v in entry.items() if k not in ("final", "camera_evidence")}
                        for entry in report["legs"]
                    ],
                }
            ),
            flush=True,
        )
    finally:
        sensor.close()
        bench.close()
