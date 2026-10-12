"""Measure changed grasp geometry outside the camera actor's information boundary."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception import locate_tools
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
parser.add_argument("--case", default="validation-016")
parser.add_argument("--alternate-view", action="store_true")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
fixture = Path("fixtures/release_model_cases.json")
case = next(c for c in json.loads(fixture.read_text())["cases"] if c["id"] == args.case)
if case["split"] == "test":
    raise ValueError("Unopened test layouts are protected")
b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=args.alternate_view))
b.model.vis.headlight.diffuse[:] *= case.get("light", 1)
sensor = CameraSensor(b)
initial_truth = b.observe()[case["tool"]].copy()
actor = CameraDelivery(
    SimRobot(b, recover_ik=True),
    sensor,
    case["tool"],
    HANDOFF["handoff"],
    verify_motion=True,
    safe_handoff=True,
)
body = b.model.body(case["tool"]).id
samples, captures, previous, last, redirected = [], [], None, None, False


def label():
    reading = actor.robot.read()
    center = b.observe()[case["tool"]]
    rotation = b.data.xmat[body].reshape(3, 3).copy()
    row = {
        "phase": actor.phase,
        "time_s": reading.time_s,
        "actual_center_m": center.tolist(),
        "actual_rotation": rotation.tolist(),
        "tcp_m": reading.tcp_m.tolist(),
        "tcp_rotation": reading.rotation.tolist(),
        "gap_m": reading.gap_m,
        "actual_offset_local_m": (reading.rotation.T @ (reading.tcp_m - center)).tolist(),
        "actual_body_rotation_local": (reading.rotation.T @ rotation).tolist(),
    }
    if actor.offset_local is not None:
        inferred, inferred_r = actor._estimate()
        row.update(
            {
                "inferred_center_m": inferred.tolist(),
                "inferred_rotation": inferred_r.tolist(),
                "center_error_m": float(np.linalg.norm(inferred - center)),
                "rotation_error_rad": float(
                    np.arccos(np.clip((np.trace(inferred_r.T @ rotation) - 1) / 2, -1, 1))
                ),
                "inferred_offset_local_m": actor.offset_local.tolist(),
            }
        )
    return row


def capture_view(row, view):
    index = len(captures)
    frame = sensor.capture_view(view)
    folder = args.output / f"frame-{index:03d}"
    folder.mkdir()
    Image.fromarray(frame.rgb).save(folder / "rgb.png")
    np.save(folder / "depth.npy", frame.depth_m)
    calibration = {
        "width": frame.camera.width,
        "height": frame.camera.height,
        "fovy_degrees": frame.camera.fovy_degrees,
        "position_m": frame.camera.position_m.tolist(),
        "rotation": frame.camera.rotation.tolist(),
    }
    (folder / "calibration.json").write_text(json.dumps(calibration, indent=2) + "\n")
    # Segmentation labels belong only to the independent offline diagnostic.
    sensor.renderer.enable_segmentation_rendering()
    ids = sensor.renderer.render()[:, :, 0]
    sensor.renderer.disable_segmentation_rendering()
    handle_id = int(b.model.body_geomadr[body])
    visibility = int((ids == handle_id).sum())
    captures.append(
        {
            "frame": folder.name,
            "view": view,
            "visible_handle_pixels_label": visibility,
            "label": row,
            "tabletop_detection": locate_tools(frame)[case["tool"]],
        }
    )


def capture(row):
    capture_view(row, "workbench_camera")
    if args.alternate_view:
        capture_view(row, "workbench_camera_side")


try:
    for _ in range(3000):
        if not actor.advance():
            break
        row = label()
        samples.append(row)
        if actor.phase != previous:
            capture(row)
            previous = actor.phase
        last = row
        if case["journey"] == "redirect" and not redirected and actor.phase == "Moving to target":
            actor.pause()
            for _ in range(19):
                b.tick()
            capture(label())
            actor.return_to_rack()
            redirected = True
    if last is not None:
        capture(label())
    initial = initial_truth[:2]
    final = b.observe()[case["tool"]]
    result = {
        "case": case,
        "scope": "Offline truth labels only; unchanged final D2d actor profile; "
        "captures do not advance physics",
        "outcome": None if actor.outcome is None else actor.outcome.__dict__,
        "final_xy_error_m": float(np.linalg.norm(final[:2] - initial)),
        "samples": samples,
        "captures": captures,
        "actor_evidence": actor.evidence,
    }
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["outcome"], "final error mm", result["final_xy_error_m"] * 1000)
    endpoints = {r["phase"]: r for r in samples}
    for phase, row in endpoints.items():
        print(
            phase,
            "center error mm",
            row.get("center_error_m", 0) * 1000,
            "rotation rad",
            row.get("rotation_error_rad"),
            "gap mm",
            row["gap_m"] * 1000,
        )
finally:
    sensor.close()
    b.close()
