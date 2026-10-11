"""Judge camera estimates against labels; no simulator access or motion."""

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from physical_ai_lab.assistant.perception import CameraCalibration, RGBDFrame, locate_tools

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("dataset", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--split", choices=["pilot", "heldout"], required=True)
args = parser.parse_args()
args.output.mkdir(exist_ok=False, parents=True)
manifest = json.loads((args.dataset / "dataset.json").read_text())
rows = []
for case in manifest["cases"]:
    if case["split"] != args.split:
        continue
    folder = args.dataset / case["id"]
    for name, expected in case["frame_hashes"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected
    calibration = json.loads((folder / "calibration.json").read_text())
    calibration["position_m"] = np.asarray(calibration["position_m"])
    calibration["rotation"] = np.asarray(calibration["rotation"])
    camera = CameraCalibration(**calibration)
    frame = RGBDFrame(
        np.asarray(Image.open(folder / "rgb.png")), np.load(folder / "depth.npy"), camera
    )
    started = time.perf_counter()
    predictions = locate_tools(frame)  # This call receives NO labels or layout.
    elapsed_ms = (time.perf_counter() - started) * 1000
    labels = case["labels_evaluation_only"]  # Read only after inference.
    errors = {}
    image = Image.fromarray(frame.rgb)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 640, 26), fill="black")
    draw.text((8, 6), case["id"] + "  green=truth; magenta=camera estimate", fill="white")
    for name, label in labels.items():
        predicted = predictions[name]["position_m"]
        truth = label["position_m"]
        errors[name] = float(np.linalg.norm(np.asarray(predicted) - truth)) if predicted else None
        u, v = camera.project(truth)
        draw.line((u - 5, v, u + 5, v), fill="#3aff88", width=2)
        draw.line((u, v - 5, u, v + 5), fill="#3aff88", width=2)
        draw.text((u + 7, v + 7), name, fill="#3aff88")
        if predicted:
            px, py = camera.project(predicted)
            draw.ellipse((px - 4, py - 4, px + 4, py + 4), outline="#ff40dd", width=2)
            draw.line((px, py, u, v), fill="#ff40dd", width=1)
    image.save(args.output / (case["id"] + ".png"))
    row = {
        "case": case["id"],
        "occluded": case["occluded"],
        "elapsed_ms": elapsed_ms,
        "predictions": predictions,
        "errors_m": errors,
        "labels": labels,
    }
    rows.append(row)
    with (args.output / "rows.jsonl").open("a") as file:
        file.write(json.dumps(row) + "\n")
    print(
        case["id"],
        {k: round(e * 1000, 2) if e is not None else "MISS" for k, e in errors.items()},
        flush=True,
    )
clear = [r for r in rows if r["occluded"] is None]
errors = sorted(e for r in clear for e in r["errors_m"].values() if e is not None)
coverage = len(errors) / (len(clear) * 3)


def tails(values):
    return values[math.ceil(len(values) * 0.95) - 1] if values else None


false_confident = [
    r["case"]
    for r in rows
    if r["occluded"] and r["predictions"][r["occluded"]]["status"] == "observed"
]
confusions = []
for row in rows:
    for name, prediction in row["predictions"].items():
        if prediction["position_m"] is None:
            continue
        nearest = min(
            row["labels"],
            key=lambda key: np.linalg.norm(
                np.asarray(prediction["position_m"]) - row["labels"][key]["position_m"]
            ),
        )
        if nearest != name:
            confusions.append({"case": row["case"], "predicted_identity": name, "nearest": nearest})
times = sorted(r["elapsed_ms"] for r in rows)
summary = {
    "scope": "Rendered RGB, metric axial depth and known calibration/catalog; no state inputs.",
    "dataset_fixture_sha256": manifest["fixture_sha256"],
    "split": args.split,
    "cases": len(rows),
    "clear_cases": len(clear),
    "clear_tool_count": len(clear) * 3,
    "observed_clear_tools": len(errors),
    "clear_coverage": coverage,
    "clear_median_error_m": statistics.median(errors) if errors else None,
    "clear_p95_error_m": tails(errors),
    "maximum_error_m": max(errors) if errors else None,
    "confident_occluded_cases": false_confident,
    "identity_confusions": confusions,
    "localization_median_ms": statistics.median(times),
    "localization_p95_ms": tails(times),
    "criteria": manifest["criteria"],
    "passed": coverage >= manifest["criteria"]["clear_detection_coverage_min"]
    and bool(errors)
    and tails(errors) <= manifest["criteria"]["clear_position_p95_max_m"]
    and not false_confident
    and not confusions,
}
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
