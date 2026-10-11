"""Time actual simulated optical capture plus camera-only localization."""

import argparse
import json
import math
import statistics
import time
from pathlib import Path

from physical_ai_lab.assistant.perception import locate_tools
from physical_ai_lab.assistant.perception_scene import CameraDatasetScene

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
case = json.loads(Path("fixtures/camera_cases.json").read_text())["cases"][0]
started = time.perf_counter()
scene = CameraDatasetScene(case)
preparation_ms = (time.perf_counter() - started) * 1000
rows = []
try:
    for _ in range(30):
        start = time.perf_counter()
        frame = scene.capture()
        captured = time.perf_counter()
        result = locate_tools(frame)
        ended = time.perf_counter()
        rows.append(
            {
                "capture_ms": (captured - start) * 1000,
                "localization_ms": (ended - captured) * 1000,
                "pipeline_ms": (ended - start) * 1000,
                "observed": [name for name, r in result.items() if r["status"] == "observed"],
            }
        )
finally:
    scene.close()
summary = {
    "scope": "30 sequential captures of one stationary physics scene; no motion, IPC or disk IO.",
    "scene_preparation_ms": preparation_ms,
    "first_sample": rows[0],
    "rows": rows,
}
for key in ["capture_ms", "localization_ms", "pipeline_ms"]:
    values = sorted(r[key] for r in rows)
    summary[key] = {
        "median": statistics.median(values),
        "p95": values[math.ceil(len(values) * 0.95) - 1],
    }
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
