"""Compare bounded native decoding with the original process on saved local speech."""

import argparse
import hashlib
import json
import statistics
import time
from pathlib import Path

import numpy as np

from physical_ai_lab.dume.asr import decode_audio_process
from physical_ai_lab.dume.audio_decode import decode_bounded_pcm

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--sources", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
rows = []
for repeat in range(5):
    for name in ["fetch", "stop", "resume", "return", "question", "change"]:
        data = (args.sources / (name + ".wav")).read_bytes()
        measurements, outputs = {}, {}
        for backend, decoder in [
            ("original_process", decode_audio_process), ("pyav", decode_bounded_pcm)
        ]:
            started = time.perf_counter()
            outputs[backend] = decoder(data)
            measurements[backend] = (time.perf_counter() - started) * 1000
        before, after = outputs["original_process"], outputs["pyav"]
        assert len(before) == len(after), name
        difference = float(np.max(np.abs(before - after)))
        assert difference < 1e-5, (name, difference)
        rows.append({"name": name, "repeat": repeat,
                     "source_sha256": hashlib.sha256(data).hexdigest(),
                     "samples": len(after), "max_difference": difference,
                     "decode_ms": measurements})
summary = {}
for backend in ["original_process", "pyav"]:
    values = sorted(row["decode_ms"][backend] for row in rows if row["repeat"] > 0)
    summary[backend] = {"warm_count": len(values), "median_ms": statistics.median(values),
                        "p95_ms": values[int(np.ceil(len(values) * .95)) - 1],
                        "first_decode_ms": rows[0]["decode_ms"][backend]}
report = {"scope": "Saved WAV decoding only; no browser, ASR, microphone or motion",
          "rows": rows, "summary": summary}
(args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(summary))
