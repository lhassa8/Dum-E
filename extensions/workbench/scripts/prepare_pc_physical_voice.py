"""Freeze PC saved speech and protected physical Stop criteria before browser trials."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

from physical_ai_lab.dume.asr import decode_audio

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--sources", type=Path, required=True)
parser.add_argument("--speech-output", action="store_true")
args = parser.parse_args()
protocol_file = root / "fixtures/pc_physical_voice_stop_protocol.json"
protocol_bytes = protocol_file.read_bytes()
protocol = json.loads(protocol_bytes)
protected_bytes = (root / "fixtures/physical_voice_stop_protocol.json").read_bytes()
protected = json.loads(protected_bytes)
for name, value in protected["criteria"].items():
    assert protocol["criteria"][name] == value, name
endpoint_folder = root / protocol["endpoint_directory"]
endpoint = json.loads((endpoint_folder / "manifest.json").read_text())
assert endpoint["protocol_sha256"] == protocol["endpoint_protocol_sha256"]
args.output.mkdir(parents=True, exist_ok=False)
manifest = {
    "protocol": protocol, "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
    "protected_criteria_sha256": hashlib.sha256(protected_bytes).hexdigest(),
    "endpoint_protocol_sha256": endpoint["protocol_sha256"],
    "implementation_sha256": {
        file: hashlib.sha256((root / file).read_bytes()).hexdigest() for file in [
            "integrations/speech-vad/physical-stop.html",
            "scripts/serve_voice_endpoint_probe.py",
            "src/physical_ai_lab/dume/asr.py",
            "src/physical_ai_lab/dume/audio_decode.py",
            "src/physical_ai_lab/dume/interrupt_asr.py",
            "src/physical_ai_lab/dume/app.py",
            "src/physical_ai_lab/dume/bridge.py",
            "src/physical_ai_lab/dume/web/voice-input.mjs",
            "src/physical_ai_lab/dume/web/speech-detector.mjs",
            "src/physical_ai_lab/assistant/app.py",
            "src/physical_ai_lab/assistant/camera_tasks.py",
            "src/physical_ai_lab/assistant/camera_control.py",
        ]
    }, "cases": [],
}
if args.speech_output:
    manifest["speech_output"] = {
        "backend": "windows-sapi", "maximum_acknowledgment_start_ms": 500,
        "maximum_post_to_playing_ms": 500, "minimum_acknowledgments_per_case": 4,
        "scope": "Windows playback during saved-voice physics journeys; no mic/acoustic check",
    }
    for file in ["integrations/speech-vad/physical-speech.mjs",
                 "src/physical_ai_lab/dume/web/local-speech.mjs",
                 "src/physical_ai_lab/dume/windows_speech.py",
                 "src/physical_ai_lab/dume/speech.py", "scripts/windows_speech_worker.ps1",
                 ".cache/local-speech/acknowledgment.wav"]:
        manifest["implementation_sha256"][file] = hashlib.sha256(
            (root / file).read_bytes()).hexdigest()
for case_id in protocol["stop_cases"]:
    case = next(row for row in endpoint["cases"] if row["id"] == case_id)
    data = (endpoint_folder / case["file"]).read_bytes()
    assert hashlib.sha256(data).hexdigest() == case["pcm_sha256"]
    shutil.copyfile(endpoint_folder / case["file"], args.output / case["file"])
    manifest["cases"].append(case)
for name in protocol["source_text"]:
    data = (args.sources / (name + ".wav")).read_bytes()
    pcm = decode_audio(data)
    file = name + ".f32"
    samples = pcm.astype("<f4").tobytes()
    (args.output / file).write_bytes(samples)
    ends = [min(offset + 640, len(pcm)) / 16 for offset in range(0, len(pcm), 640)
            if np.sqrt(np.mean(pcm[offset:offset + 640]**2)) >= 0.008]
    assert ends
    manifest[name] = {"id": name, "file": file, "source_sha256": hashlib.sha256(data).hexdigest(),
                      "pcm_sha256": hashlib.sha256(samples).hexdigest(),
                      "last_clean_voiced_ms": ends[-1]}
(args.output / "physical-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"cases": len(manifest["cases"]), "protocol_sha256":
                  manifest["protocol_sha256"]}))
