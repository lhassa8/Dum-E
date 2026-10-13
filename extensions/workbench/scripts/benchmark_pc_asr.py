"""Repeat saved local speech; separate cold load from warm decoding, never record."""

import argparse
import json
import math
import statistics
import subprocess
from pathlib import Path

from physical_ai_lab.dume.asr import SpeechInput, model_path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--fixtures", type=Path, required=True)
parser.add_argument("--repeat", type=int, default=5)
args = parser.parse_args()
if args.repeat < 1:
    parser.error("repeat must be positive")
args.output.mkdir(parents=True, exist_ok=False)
voice = SpeechInput()
voice.path = model_path()
expected = {
    "fetch": "bring me the screwdriver",
    "question": "what are you doing",
    "change": "actually bring me the wrench instead",
    "stop": "stop",
    "resume": "resume please",
    "return": "put it back",
}
rows = []
try:
    for repeat in range(args.repeat):
        for name, words in expected.items():
            result = voice._recognize((args.fixtures / f"{name}.wav").read_bytes())
            voice.status = "ready"
            normalized = " ".join(result["text"].lower().strip(".!?,").replace(",", "").split())
            rows.append(
                {
                    "repeat": repeat,
                    "name": name,
                    "correct": normalized == words,
                    "cold": repeat == 0 and name == "fetch",
                    **result,
                }
            )
            (args.output / "rows.json").write_text(json.dumps(rows, indent=2) + "\n")
    warm = [r["recognition_seconds"] * 1000 for r in rows if not r["cold"]]
    gpu = subprocess.run(["nvidia-smi"], capture_output=True, text=True, check=True).stdout
    (args.output / "gpu-contention.txt").write_text(gpu)
    report = {
        "boundary": "saved clip available -> decoded text; excludes microphone, pause, network, "
        "decision, speech and motion",
        "snapshot": voice.snapshot(),
        "sample_size": len(rows),
        "failures": sum(not r["correct"] for r in rows),
        "cold_ms": rows[0]["recognition_seconds"] * 1000,
        "warm_median_ms": statistics.median(warm),
        "warm_p95_ms": sorted(warm)[math.ceil(0.95 * len(warm)) - 1],
    }
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
finally:
    voice.close()
