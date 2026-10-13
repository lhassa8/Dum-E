"""Evaluate a CPU-only positive Stop candidate on retained semantic/noise cohorts."""

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path

import numpy as np

from physical_ai_lab.dume.asr import decode_audio, trim_speech_edges, validate_decoded_audio
from physical_ai_lab.dume.interrupt_asr import CpuStopRecognizer

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--cohorts", type=Path, nargs="+", required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
root = Path(__file__).resolve().parents[1]
freeze = {"model": "Systran/faster-whisper-tiny.en",
          "revision": "0d3d19a32d3338f10357c0889762bd8d64bbdeba",
          "code_sha256": {file: hashlib.sha256((root / file).read_bytes()).hexdigest()
                          for file in ["src/physical_ai_lab/dume/interrupt_asr.py",
                                       "src/physical_ai_lab/dume/asr.py",
                                       "src/physical_ai_lab/dume/audio_decode.py"]},
          "cohort_manifest_sha256": {str(folder): hashlib.sha256(
              (folder / "manifest.json").read_bytes()).hexdigest() for folder in args.cohorts}}
(args.output / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
recognizer = CpuStopRecognizer()
warmup_started = time.monotonic()
warmup_file = root / "src/physical_ai_lab/dume/fixtures/recognition-warmup.wav"
warmup = decode_audio(warmup_file.read_bytes())
warmup, _ = trim_speech_edges(warmup)
recognizer.inspect(warmup)
warmup_seconds = time.monotonic() - warmup_started
rows = []
for folder in args.cohorts:
    manifest = json.loads((folder / "manifest.json").read_text())
    for case in manifest["cases"]:
        data = (folder / case["file"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == case["pcm_sha256"]
        pcm = np.frombuffer(data, dtype="<f4").copy()
        # Fixed prefix beyond the retained clean-word boundary, not a search.
        # Browser capture ends near this point; do not send 12 s of trailing
        # silence to the original amplitude gate for a 0.4 s quiet word.
        if case["last_clean_voiced_ms"] is not None:
            pcm = pcm[:int((case["last_clean_voiced_ms"] + 1000) * 16)]
        started = time.monotonic()
        try:
            pcm = validate_decoded_audio(pcm)
            pcm, edges = trim_speech_edges(pcm)
            if len(pcm) < 16000:
                pcm = np.pad(pcm, (0, 5600))
            result = recognizer.inspect(pcm)
        except ValueError as error:
            result = {"text": "", "positive_stop": False, "rejected": str(error)}
            edges = None
        expected_stop = case["id"].startswith("stop")
        rows.append({"id": case["id"], "cohort": str(folder), "expected_stop": expected_stop,
                     "passed": result["positive_stop"] == expected_stop,
                     "total_ms": (time.monotonic() - started) * 1000,
                     "edges": edges, "result": result})
values = sorted(row["total_ms"] for row in rows if row["expected_stop"])
report = {"scope": "Saved PCM to real CPU-only positive Stop recognition; no browser/motion",
          "rows": rows, "count": len(rows), "failures": sum(not r["passed"] for r in rows),
          "false_stops": sum(r["result"]["positive_stop"] and not r["expected_stop"] for r in rows),
          "load_seconds": recognizer.load_seconds, "warmup_seconds": warmup_seconds,
          "positive_stop_ms": {"count": len(values), "median": statistics.median(values),
                               "p95": values[math.ceil(len(values) * .95) - 1]}}
(args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({key: value for key, value in report.items() if key != "rows"}))
