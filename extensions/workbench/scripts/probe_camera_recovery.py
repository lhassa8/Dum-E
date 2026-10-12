"""Ground motion tracking and alternate optics before changing the controller."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception import locate_tools
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.release_model import ReleaseModel
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
fixture = json.loads(Path("fixtures/release_model_cases.json").read_text())
rows = []
for ident in ["validation-000", "validation-014", "validation-002"]:
    case = next(c for c in fixture["cases"] if c["id"] == ident)
    b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=True))
    b.model.vis.headlight.diffuse[:] *= case["light"]
    sensor = CameraSensor(b)
    model = ReleaseModel(
        "src/physical_ai_lab/assistant/assets/learned/release-outcome-v2-experimental.npz"
    )

    class Traced(CameraDelivery):
        def _motion(self, point, phase, grip):
            self.requested_point = np.asarray(point).copy()
            yield from super()._motion(point, phase, grip)

    first = Traced(SimRobot(b), sensor, case["tool"], HANDOFF["handoff"], release_model=model)
    record = {"case": ident, "legs": []}
    try:
        for leg in range(2):
            actor = (
                first
                if leg == 0
                else Traced(SimRobot(b), sensor, case["tool"], first.rack_xy, release_model=model)
            )
            samples, paused = [], False
            for _ in range(3000):
                if not actor.advance():
                    break
                if hasattr(actor, "requested_point"):
                    reading = actor.robot.read()
                    angle = float(
                        np.arccos(
                            np.clip(
                                (np.trace(reading.rotation.T @ actor.orientation) - 1) / 2, -1, 1
                            )
                        )
                    )
                    row = {
                        "phase": actor.phase,
                        "tcp_error_m": float(np.linalg.norm(reading.tcp_m - actor.requested_point)),
                        "orientation_error_rad": angle,
                        "joint_velocity": reading.joint_velocity.tolist(),
                        "actuator_load": reading.actuator_load.tolist(),
                    }
                    # Contact labels are external diagnostic evidence only.
                    if abs(reading.actuator_load[6]) > 8:
                        row["contacts_evaluation_only"] = [
                            [b.model.body(b.model.geom_bodyid[g]).name for g in (c.geom1, c.geom2)]
                            for c in b.data.contact[: b.data.ncon]
                        ]
                    samples.append(row)
                if case["journey"] == "resume" and not paused and actor.phase == "Moving to target":
                    actor.pause()
                    for _ in range(19):
                        b.tick()
                    actor.resume()
                    paused = True
            record["legs"].append({"outcome": actor.outcome.__dict__, "samples": samples})
        rows.append(record)
    finally:
        sensor.close()
        b.close()
optics = []
for ident in ["validation-001", "validation-004"]:
    case = next(c for c in fixture["cases"] if c["id"] == ident)
    b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=True))
    b.model.vis.headlight.diffuse[:] *= case["light"]
    sensor = CameraSensor(b)
    r = {"case": ident, "views": []}
    try:
        actor = CameraDelivery(SimRobot(b), sensor, case["tool"], HANDOFF["handoff"])
        for _ in range(3000):
            if not actor.advance():
                break
        r["failed_stage_outcome"] = actor.outcome.__dict__
        for view in ["workbench_camera", "workbench_camera_side"]:
            frame = sensor.capture_view(view)
            prediction = locate_tools(frame)[case["tool"]]
            truth = b.observe()[case["tool"]]  # Read only after inference.
            error = (
                None
                if prediction["position_m"] is None
                else float(np.linalg.norm(prediction["position_m"] - truth))
            )
            r["views"].append({"view": view, "prediction": prediction, "error_m": error})
            Image.fromarray(frame.rgb).save(args.output / f"{ident}-{view}.png")
        optics.append(r)
    finally:
        sensor.close()
        b.close()
(args.output / "results.json").write_text(
    json.dumps({"motion": rows, "optics": optics}, indent=2) + "\n"
)
for r in rows:
    print(r["case"])
    for i, leg in enumerate(r["legs"]):
        endpoints = {s["phase"]: s for s in leg["samples"]}
        print(
            "leg",
            i,
            leg["outcome"],
            {
                p: (
                    round(s["tcp_error_m"] * 1000, 2),
                    round(s["orientation_error_rad"], 3),
                    round(s["actuator_load"][6], 2),
                )
                for p, s in endpoints.items()
            },
        )
        contacts = next(
            (
                s.get("contacts_evaluation_only")
                for s in reversed(leg["samples"])
                if "contacts_evaluation_only" in s
            ),
            None,
        )
        if contacts:
            print("saturated contacts", contacts)
for r in optics:
    print(
        r["case"],
        [
            (v["view"], v["prediction"]["status"], v["prediction"].get("fit_score"), v["error_m"])
            for v in r["views"]
        ],
    )
