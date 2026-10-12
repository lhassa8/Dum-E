"""Copy immutable saved speech for the browser/physics Stop judge; no recording."""

import argparse
import hashlib
import json
import shutil
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def prepare(output):
    protocol_file = ROOT / "fixtures/physical_voice_stop_protocol.json"
    protocol = json.loads(protocol_file.read_text())
    frozen = json.loads((ROOT / "runs/voice-endpoint-001/manifest.json").read_text())
    source = ROOT / protocol["question_source"]
    with wave.open(str(source)) as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (16000, 1, 2):
            raise ValueError("Expected retained mono 16 kHz PCM16 question")
        question = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
    output.mkdir(parents=True, exist_ok=False)
    (output / "question.f32").write_bytes((question.astype(np.float32) / 32768).tobytes())
    rows = []
    for case_id in protocol["stop_cases"]:
        case = next(row for row in frozen["cases"] if row["id"] == case_id)
        original = ROOT / "runs/voice-endpoint-001" / case["file"]
        if hashlib.sha256(original.read_bytes()).hexdigest() != case["pcm_sha256"]:
            raise ValueError(f"Frozen PCM identity changed: {case_id}")
        shutil.copyfile(original, output / case["file"])
        rows.append(case)
    manifest = {
        "protocol": protocol,
        "protocol_sha256": hashlib.sha256(protocol_file.read_bytes()).hexdigest(),
        "endpoint_protocol_sha256": frozen["protocol_sha256"],
        "question": {
            "file": "question.f32",
            "source": protocol["question_source"],
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "pcm_sha256": hashlib.sha256((output / "question.f32").read_bytes()).hexdigest(),
        },
        "cases": rows,
    }
    (output / "physical-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Frozen browser/physics Stop clips:", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    prepare(parser.parse_args().output.resolve())
