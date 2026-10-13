"""Compare exact detector outputs and paired timing on saved optical frames."""

import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.perception import CameraCalibration, RGBDFrame, locate_tools


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--frames", type=Path, nargs="*", default=[])
    parser.add_argument("--dataset", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location("frozen_perception", args.baseline_source)
    baseline = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = baseline
    spec.loader.exec_module(baseline)
    frames = []
    for path in args.frames:
        data = np.load(path)
        camera = CameraCalibration(
            data["rgb"].shape[1],
            data["rgb"].shape[0],
            float(data["fovy"]),
            data["position"],
            data["rotation"],
        )
        frames.append((str(path), RGBDFrame(data["rgb"], data["depth"], camera)))
    if args.dataset:
        manifest = json.loads((args.dataset / "dataset.json").read_text())
        for case in manifest["cases"]:
            folder = args.dataset / case["id"]
            for name, digest in case["frame_hashes"].items():
                assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == digest
            calibration = json.loads((folder / "calibration.json").read_text())
            for key in ["position_m", "rotation"]:
                calibration[key] = np.asarray(calibration[key])
            frames.append(
                (
                    case["id"],
                    RGBDFrame(
                        np.asarray(Image.open(folder / "rgb.png")),
                        np.load(folder / "depth.npy"),
                        CameraCalibration(**calibration),
                    ),
                )
            )
    if not frames:
        raise ValueError("Supply saved optical frames or a dataset")
    rows = []
    for name, frame in frames:
        timings = {"baseline": [], "candidate": []}
        outputs = {}
        for repeat in range(5):
            order = [("baseline", baseline.locate_tools), ("candidate", locate_tools)]
            for label, detector in order if repeat % 2 == 0 else reversed(order):
                started = time.perf_counter()
                outputs[label] = detector(frame)
                timings[label].append(1000 * (time.perf_counter() - started))
            assert outputs["baseline"] == outputs["candidate"], f"Detector outputs changed: {name}"
        row = {
            "frame": name,
            "exact_match": True,
            "timings_ms": timings,
            "median_ms": {key: statistics.median(value) for key, value in timings.items()},
        }
        rows.append(row)
        print(
            json.dumps({key: value for key, value in row.items() if key != "timings_ms"}),
            flush=True,
        )
    (args.output / "results.json").write_text(
        json.dumps(
            {
                "scope": (
                    "Exact optical outputs, paired CPU timings; "
                    "no labels, fitting, robot or acoustic timing"
                ),
                "baseline_raw_sha256": hashlib.sha256(
                    args.baseline_source.read_bytes()
                ).hexdigest(),
                "rows": rows,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
