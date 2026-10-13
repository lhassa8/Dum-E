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
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
fixture = json.loads(args.fixture.read_text())
reports = []


class Traced(CameraDelivery):
    def _motion(self, point, phase, grip):
        self.requested = (np.array(point).copy(), self.orientation.copy(), phase)
        yield from super()._motion(point, phase, grip)


for ident in ("pc-reserved-000", "pc-reserved-009", "pc-reserved-014", "pc-reserved-029"):
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
        SimRobot(bench, recover_ik=True),
        sensor,
        name,
        HANDOFF["handoff"],
        verify_motion=True,
        linear_lifts=True,
        center_grasp=True,
        safe_handoff=True,
        release_fallback=True,
        alternate_view=True,
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
                    SimRobot(bench, recover_ik=True),
                    sensor,
                    name,
                    first.rack_xy,
                    verify_motion=True,
                    linear_lifts=True,
                    center_grasp=True,
                    safe_handoff=True,
                    release_fallback=True,
                    alternate_view=True,
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
                active = actor.advance()
                measure()
                if not active:
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
