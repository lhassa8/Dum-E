"""Generate settled physics scenes; save optical frames separately from labels."""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.perception_scene import CameraDatasetScene

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--fixture", type=Path, default=Path("fixtures/camera_cases.json"))
args = parser.parse_args()
spec = json.loads(args.fixture.read_text())
args.output.mkdir(exist_ok=False, parents=True)
manifest = {
    "fixture_sha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
    "criteria": spec["criteria"],
    "cases": [],
}
for case in spec["cases"]:
    folder = args.output / case["id"]
    folder.mkdir()
    scene = CameraDatasetScene(case)
    try:
        frame = scene.capture()
        Image.fromarray(frame.rgb).save(folder / "rgb.png")
        np.save(folder / "depth.npy", frame.depth_m)
        calibration = asdict(frame.camera)
        calibration["position_m"] = calibration["position_m"].tolist()
        calibration["rotation"] = calibration["rotation"].tolist()
        (folder / "calibration.json").write_text(json.dumps(calibration, indent=2) + "\n")
        labels = scene.annotations()
        record = {**case, "labels_evaluation_only": labels}
        record["frame_hashes"] = {
            name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
            for name in ["rgb.png", "depth.npy", "calibration.json"]
        }
        manifest["cases"].append(record)
    finally:
        scene.close()
    print(case["id"], {k: v["visible_handle_pixels"] for k, v in labels.items()}, flush=True)
(args.output / "dataset.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("Saved", len(manifest["cases"]), "actual RGB/depth frames")
