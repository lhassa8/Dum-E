"""Frozen RGB-only catalog grounding; labels remain outside the model request."""

import argparse
import hashlib
import io
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.scene import Workbench
from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS
from physical_ai_lab.assistant.vision_language import LMStudioVision


def labels_for_view(bench, sensor, present, view):
    sensor.renderer.enable_segmentation_rendering()
    sensor.renderer.update_scene(bench.data, camera=view)
    ids = sensor.renderer.render()[:, :, 0]
    sensor.renderer.disable_segmentation_rendering()
    labels = {}
    for name in TOOLS:
        if name not in present:
            labels[name] = {"visible": False, "pixels": 0, "center_pixels": None}
            continue
        body = bench.model.body(name).id
        first, count = bench.model.body_geomadr[body], bench.model.body_geomnum[body]
        v, u = np.nonzero(np.isin(ids, np.arange(first, first + count)))
        visible = len(u) >= 20
        labels[name] = {
            "visible": visible,
            "pixels": len(u),
            "center_pixels": [
                (float(u.min()) + float(u.max())) / 2,
                (float(v.min()) + float(v.max())) / 2,
            ]
            if visible
            else None,
        }
    return labels


def render_case(case, folder, alternate=False):
    root = ET.fromstring(camera_scene_xml(case, alternate_view=alternate))
    world = root.find("worldbody")
    for name in TOOLS:
        if name not in case["present"]:
            world.remove(world.find(f"body[@name='{name}']"))
    bench = Workbench(
        case["seed"],
        xml=ET.tostring(root, encoding="unicode"),
        objects={name: TOOLS[name] for name in case["present"]},
        targets=HANDOFF,
    )
    sensor = None
    try:
        bench.model.vis.headlight.diffuse[:] *= case["light"]
        sensor = CameraSensor(bench)
        frame = sensor.capture()
        image = io.BytesIO()
        Image.fromarray(frame.rgb).save(image, format="JPEG", quality=95)
        jpeg = image.getvalue()
        (folder / "frame.jpg").write_bytes(jpeg)
        labels = labels_for_view(bench, sensor, case["present"], "workbench_camera")
        (folder / "evaluation_labels.json").write_text(json.dumps(labels, indent=2) + "\n")
        side = None
        if alternate:
            other = sensor.capture_view("workbench_camera_side")
            image = io.BytesIO()
            Image.fromarray(other.rgb).save(image, format="JPEG", quality=95)
            side_jpeg = image.getvalue()
            side_labels = labels_for_view(bench, sensor, case["present"], "workbench_camera_side")
            (folder / "side.jpg").write_bytes(side_jpeg)
            (folder / "side_evaluation_labels.json").write_text(
                json.dumps(side_labels, indent=2) + "\n"
            )
            side = (side_jpeg, side_labels)
        return jpeg, labels, frame.camera.width, frame.camera.height, side
    finally:
        if sensor:
            sensor.close()
        bench.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--url", default="http://127.0.0.1:1234")
    parser.add_argument("--split", choices=["pilot", "validation"], default="pilot")
    parser.add_argument("--format", choices=["expanded", "compact"], default="expanded")
    parser.add_argument(
        "--coordinates", choices=["normalized_xy", "grid1000_yx"], default="normalized_xy"
    )
    parser.add_argument(
        "--alternate", action="store_true", help="Bounded second optical view on uncertainty"
    )
    args = parser.parse_args()
    fixture = Path(__file__).resolve().parents[1] / "fixtures/vision_language_cases.json"
    spec = json.loads(fixture.read_text())
    args.output.mkdir(parents=True, exist_ok=False)
    model = LMStudioVision(
        args.model, args.url, compact=args.format == "compact", coordinates=args.coordinates
    )
    (args.output / "system-prompt.txt").write_text(model.system)
    rows = []
    try:
        for case in spec["cases"]:
            if case["split"] != args.split:
                continue
            folder = args.output / case["id"]
            folder.mkdir()
            jpeg, labels, width, height, side = render_case(case, folder, args.alternate)
            row = {
                "id": case["id"],
                "labels": labels,
                "frame_sha256": hashlib.sha256(jpeg).hexdigest(),
                "passed": False,
            }
            try:
                observation = model.observe(jpeg)
                calls = [observation["elapsed_ms"]]
                row["view"] = "front"
                if side and any(not item["visible"] for item in observation["tools"].values()):
                    other = model.observe(side[0])
                    calls.append(other["elapsed_ms"])
                    if sum(item["visible"] for item in other["tools"].values()) > sum(
                        item["visible"] for item in observation["tools"].values()
                    ):
                        observation, jpeg, labels = other, side[0], side[1]
                        row["view"] = "side"
                row["selected_labels"] = labels
                row["selected_frame_sha256"] = hashlib.sha256(jpeg).hexdigest()
                row["total_vision_ms"] = sum(calls)
                row["timing_target_met"] = (
                    sum(calls) <= spec["criteria"]["complete_response_target_ms"]
                )
                row["observation"] = observation
                row["presence_correct"] = all(
                    labels[n]["visible"] == observation["tools"][n]["visible"] for n in TOOLS
                )
                errors = {}
                for name, label in labels.items():
                    center = observation["tools"][name]["center"]
                    if label["visible"] and center is not None:
                        errors[name] = float(
                            np.linalg.norm(
                                np.array(center) * [width, height] - label["center_pixels"]
                            )
                        )
                row["center_error_pixels"] = errors
                row["false_positives"] = sum(
                    observation["tools"][n]["visible"] and not labels[n]["visible"] for n in TOOLS
                )
                row["passed"] = row["presence_correct"] and all(
                    error <= spec["criteria"]["visible_center_error_max_pixels"]
                    for error in errors.values()
                )
            except Exception as error:
                row["failure"] = repr(error)
                row["rejected_response"] = model.last_response
            rows.append(row)
            (folder / "result.json").write_text(json.dumps(row, indent=2) + "\n")
            summary = {
                "scope": spec["scope"],
                "split": args.split,
                "model": args.model,
                "format": args.format,
                "coordinates": args.coordinates,
                "alternate": args.alternate,
                "system_prompt_sha256": hashlib.sha256(model.system.encode()).hexdigest(),
                "criteria": spec["criteria"],
                "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
                "rows": rows,
            }
            (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        "id": row["id"],
                        "passed": row["passed"],
                        "presence_correct": row.get("presence_correct"),
                        "false_positives": row.get("false_positives"),
                        "elapsed_ms": row.get("observation", {}).get("elapsed_ms"),
                        "failure": row.get("failure"),
                    }
                ),
                flush=True,
            )
    finally:
        model.close()


if __name__ == "__main__":
    main()
