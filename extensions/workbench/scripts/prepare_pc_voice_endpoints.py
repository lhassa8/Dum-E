"""Freeze local PC saved speech identities and generate endpoint checks without recording."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.dume.asr import decode_audio

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--sources", type=Path, required=True)
parser.add_argument(
    "--protocol", type=Path, default=root / "fixtures/pc_voice_endpoint_protocol.json"
)
args = parser.parse_args()
protocol_bytes = args.protocol.read_bytes()
protocol = json.loads(protocol_bytes)
sources = {name: (args.sources / file).read_bytes() for name, file in protocol["sources"].items()}
source_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()}
args.output.mkdir(parents=True, exist_ok=False)
# Persist protocol/source identities before deriving cases or model outputs.
freeze = {"protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
          "source_sha256": source_hashes, "protocol": protocol,
          "implementation_sha256": {
              file: hashlib.sha256((root / file).read_bytes()).hexdigest() for file in [
                  "scripts/speech_edge_preprocessing.py",
                  "scripts/serve_voice_endpoint_probe.py",
                  "integrations/speech-vad/benchmark.html",
                  "src/physical_ai_lab/dume/asr.py",
                  "src/physical_ai_lab/dume/web/voice-input.mjs",
                  "src/physical_ai_lab/dume/web/speech-detector.mjs",
              ]
          }}
(args.output / "freeze.json").write_text(json.dumps(freeze, indent=2) + "\n")
rng = np.random.default_rng(protocol["seed"])
rate = protocol["sample_rate"]
count = rate * protocol["capture_max_s"]
cases = []


def make(name, pcm, onset_ms, gain, background, amplitude, voiced_end):
    onset = int(onset_ms * rate / 1000)
    values = np.zeros(count, dtype=np.float32)
    if background == "white":
        values += rng.normal(0, amplitude, count).astype(np.float32)
    elif background == "hum":
        t = np.arange(count) / rate
        hum = np.sin(2 * np.pi * 60 * t) + 0.4 * np.sin(2 * np.pi * 180 * t)
        values += (hum * amplitude / np.sqrt(np.mean(hum**2))).astype(np.float32)
    if pcm is not None:
        assert onset + len(pcm) <= count
        values[onset:onset + len(pcm)] += gain * pcm
    case_id = f"{name}-onset{onset_ms}-gain{gain}-{background}"
    data = values.astype("<f4").tobytes()
    file = case_id + ".f32"
    (args.output / file).write_bytes(data)
    cases.append({"id": case_id, "file": file, "expected_speech": pcm is not None,
                  "expected_text": protocol.get("expected_text", {
                      "screwdriver": "screwdriver", "question": "doing"
                  }).get(name),
                  "voice_mode": "interrupt" if name.startswith("stop") or name in
                  protocol.get("interrupt_sources", []) else "request",
                  "pause_ms": protocol["stop_pause_ms"] if name.startswith("stop") or name in
                  protocol.get("interrupt_sources", [])
                  else protocol["request_pause_ms"],
                  "last_clean_voiced_ms": None if voiced_end is None else onset_ms + voiced_end,
                  "pcm_sha256": hashlib.sha256(data).hexdigest(), "sample_count": count})


for name, data in sources.items():
    pcm = decode_audio(data)
    ends = [min(offset + 640, len(pcm)) / 16 for offset in range(0, len(pcm), 640)
            if np.sqrt(np.mean(pcm[offset:offset + 640]**2)) >= 0.008]
    assert ends, name
    for onset_ms in protocol["stop_onsets_ms"] if name.startswith("stop") else [0]:
        for gain in protocol["gains"]:
            for background, amplitude in protocol["backgrounds"].items():
                make(name, pcm, onset_ms, gain, background, amplitude, ends[-1])
for background, amplitude in protocol["backgrounds"].items():
    make("control", None, 0, 1, background, amplitude, None)
manifest = {**freeze, "cases": cases, "stream_cases": [row["id"] for row in cases]}
(args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"cases": len(cases), "protocol_sha256": freeze["protocol_sha256"]}))
