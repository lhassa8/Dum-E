"""Freeze saved speech or independently grade browser-local acknowledgment timing."""

import argparse
import hashlib
import json
import math
import shutil
import statistics
import wave
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--prepare-from", type=Path)
args = parser.parse_args()

if args.prepare_from:
    source = json.loads((args.prepare_from / "physical-manifest.json").read_text())
    earlier = json.loads((args.prepare_from / "physical-stop-browser.json").read_text())
    baseline = [row["initial_request"]["recognized"]["recognition_seconds"] * 1000
                + row["initial_request"]["result"]["elapsed_ms"] for row in earlier["rows"]]
    args.folder.mkdir(parents=True, exist_ok=False)
    cases = []
    for repeat in range(2):
        for key in ["fetch", "question", "resume", "return"]:
            item = dict(source[key], id=f"{key}-{repeat + 1}")
            shutil.copyfile(args.prepare_from / item["file"], args.folder / item["file"])
            cases.append(item)
    files = ["src/physical_ai_lab/dume/web/voice-input.mjs",
             "src/physical_ai_lab/dume/web/local-speech.mjs",
             "src/physical_ai_lab/dume/web/index.html",
             "src/physical_ai_lab/dume/app.py",
             "src/physical_ai_lab/dume/speech.py",
             ".cache/local-speech/acknowledgment.wav",
             ".cache/local-speech/acknowledgment.json",
             "scripts/prepare_acknowledgment.ps1",
             "scripts/launch_windows.ps1",
             "integrations/speech-vad/acknowledgment.html",
             "scripts/serve_voice_endpoint_probe.py"]
    manifest = {"cases": cases, "maximum_completion_to_voice_start_ms": 500,
                "acknowledgment": "Let me check.",
                "queued_reply_pressure": True,
                "recorded_voice": json.loads((root / ".cache/local-speech/acknowledgment.json")
                                             .read_text())["voice"],
                "scope": "Browser HTMLAudio playing event for local WAV; no acoustic qualification",
                "earlier_serial_asr_and_decision_lower_bound_ms": baseline,
                "earlier_source": str(args.prepare_from),
                "implementation_sha256": {file: hashlib.sha256(
                    (root / file).read_bytes()).hexdigest()
                                          for file in files}}
    (args.folder / "acknowledgment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Frozen {len(cases)} trials; unchanged 500 ms acknowledgment target.")
else:
    manifest = json.loads((args.folder / "acknowledgment-manifest.json").read_text())
    report = json.loads((args.folder / "acknowledgment-browser.json").read_text())
    speech_events = [json.loads(line) for line in
                     (args.folder / "speech-events.jsonl").read_text().splitlines()]
    with wave.open(str(root / ".cache/local-speech/acknowledgment.wav")) as waveform:
        duration_ms = waveform.getnframes() / waveform.getframerate() * 1000
    for file, digest in manifest["implementation_sha256"].items():
        assert hashlib.sha256((root / file).read_bytes()).hexdigest() == digest, file
    failures = []
    expected_ids = [f"{key}-{repeat}" for repeat in [1, 2]
                    for key in ["fetch", "question", "resume", "return"]]
    if ([item["id"] for item in manifest["cases"]] != expected_ids
            or manifest["maximum_completion_to_voice_start_ms"] != 500
            or manifest["acknowledgment"] != "Let me check."):
        failures.append("Protected acknowledgment cases/target/phrase differ")
    if report.get("failed") or report.get("in_progress"):
        failures.append("Browser run failed or unfinished")
    if [row["id"] for row in report["rows"]] != [item["id"] for item in manifest["cases"]]:
        failures.append("Frozen case identities/counts differ")
    timings, word_timings = [], []
    for item, row in zip(manifest["cases"], report["rows"]):
        assert hashlib.sha256((args.folder / item["file"]).read_bytes()).hexdigest() == (
            item["pcm_sha256"])
        elapsed = row["voice_start_ms"] - row["endpoint_ms"]
        assert abs(elapsed - row["completion_to_voice_start_ms"]) < 1e-6
        word_elapsed = row["voice_start_ms"] - row["source_start_ms"] - item["last_clean_voiced_ms"]
        assert abs(word_elapsed - row["word_end_to_voice_start_ms"]) < 1e-6
        if not (0 <= elapsed <= 500 and row["voice_start_ms"] <= row["voice_end_ms"]
                and row["tracks_ended"] and row["local_voice"]
                and row["recognized"].get("device") == "cuda"):
            failures.append(item["id"])
        generation = row["speech_generation"]
        calls = [event for event in speech_events if event["route"] == "/speak"
                 and (event.get("result") or {}).get("generation") == generation]
        if (len(calls) != 1 or calls[0]["result"].get("audio") != "/acknowledgment.wav"
                or sum(event["route"] == f"/speech-started/{generation}"
                       for event in speech_events) != 1
                or row["local_voice"] != manifest["recorded_voice"]
                or row["playback_backend"] != "local_wav_html_audio"):
            failures.append(item["id"] + ": registered audio identity/start differs")
        if manifest.get("queued_reply_pressure") and not (
            row["reply_requested_ms"] < row["voice_end_ms"]
            and row["voice_end_ms"] - row["voice_start_ms"] >= duration_ms - 80
        ):
            failures.append(item["id"] + ": acknowledgment truncated by queued reply")
        timings.append(elapsed)
        word_timings.append(word_elapsed)

    def summary(values):
        if not values:
            return {"count": 0, "median": None, "p95": None, "max": None}
        ordered = sorted(values)
        return {"count": len(values), "median": statistics.median(values),
                "p95": ordered[math.ceil(len(values) * .95) - 1], "max": max(values)}

    result = {"passed": not failures, "failures": failures, "scope": manifest["scope"],
              "completion_to_voice_start_ms": summary(timings),
              "word_end_to_voice_start_ms": summary(word_timings),
              "earlier_serial_asr_and_decision_lower_bound_ms": summary(
                  manifest["earlier_serial_asr_and_decision_lower_bound_ms"])}
    (args.folder / "acknowledgment-judged.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
