"""Replay RGB-D measurements; read physical labels only after camera inference."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.held_perception import locate_held_face
from physical_ai_lab.assistant.perception import CameraCalibration, RGBDFrame, locate_held_tool

parser = argparse.ArgumentParser()
parser.add_argument("diagnostic", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
source = args.diagnostic / "results.json"
e = json.loads(source.read_text())
rows = []
for capture in e["captures"]:
    folder = args.diagnostic / capture["frame"]
    calibration = json.loads((folder / "calibration.json").read_text())
    calibration["position_m"] = np.asarray(calibration["position_m"])
    calibration["rotation"] = np.asarray(calibration["rotation"])
    frame = RGBDFrame(
        np.asarray(Image.open(folder / "rgb.png")),
        np.load(folder / "depth.npy", allow_pickle=False),
        CameraCalibration(**calibration),
    )
    reading = capture["label"]  # Robot fields only are passed into either fit.
    row = {
        "frame": capture["frame"],
        "view": capture.get("view", "workbench_camera"),
        "phase": reading["phase"],
        "predictions": {},
    }
    for name, fit in [("complete_face", locate_held_tool), ("robust_plane", locate_held_face)]:
        prediction = fit(frame, e["case"]["tool"], reading["tcp_m"])
        # Physical labels are evaluation only, after prediction is fixed.
        error = (
            None
            if prediction["status"] != "observed"
            else float(
                np.linalg.norm(np.asarray(prediction["position_m"]) - reading["actual_center_m"])
            )
        )
        row["predictions"][name] = {"prediction": prediction, "error_m": error}
    row["airborne_label"] = reading["actual_center_m"][2] > 0.05
    row["visible_handle_pixels_label"] = capture.get("visible_handle_pixels_label")
    rows.append(row)
summary = {
    "scope": "One known validation scene, paired front/side; not held-out generalization",
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "airborne_frames": sum(r["airborne_label"] for r in rows),
    "accepted_airborne": {
        name: sum(
            r["airborne_label"] and r["predictions"][name]["prediction"]["status"] == "observed"
            for r in rows
        )
        for name in ["complete_face", "robust_plane"]
    },
    "rows": rows,
}
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print({k: v for k, v in summary.items() if k != "rows"})
