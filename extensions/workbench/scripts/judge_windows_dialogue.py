"""Independently verify real speech API, WAV identity and complete browser playback."""

import argparse
import hashlib
import json
import math
import statistics
import wave
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
args = parser.parse_args()
manifest = json.loads((args.folder / "manifest.json").read_text())
report = json.loads((args.folder / "browser.json").read_text())
logs = [json.loads(line) for line in (args.folder / "speech.jsonl").read_text().splitlines()]
playback_file = args.folder / "speech-playback.jsonl"
playback_events = [json.loads(line) for line in playback_file.read_text().splitlines()]
for file, digest in manifest["source_sha256"].items():
    assert hashlib.sha256((root / file).read_bytes()).hexdigest() == digest, file
expected = [f"reply-{repeat}-{index}" for repeat in range(2) for index in range(6)]
assert [item["id"] for item in manifest["cases"]] == expected
assert manifest["maximum_reply_to_player_ms"] == 500
failures, timings, waves = [], [], []
if report.get("failed") or report.get("in_progress"):
    failures.append("Browser run failed or unfinished")
if [row["id"] for row in report["rows"]] != expected:
    failures.append("Not all twelve protected cases completed")
for item, row in zip(manifest["cases"], report["rows"]):
    result = row["result"]
    generation = result["generation"]
    matching = [entry for entry in logs if entry["generation"] == generation]
    assert len(matching) == 1 and matching[0]["text"] == item["text"] == row["text"]
    assert all(matching[0][key] == value for key, value in result.items())
    assert result["backend"] == "windows-sapi" and result["local"] is True
    assert result["voice"] == "Microsoft David Desktop"
    assert result["audio"] == f"/speech-audio/{generation}"
    for kind in ["started", "finished"]:
        assert sum(event["kind"] == kind and event["generation"] == generation
                   and event["accepted"] for event in playback_events) == 1
    file = args.folder / "speech-audio" / f"{generation}.wav"
    with wave.open(str(file)) as audio:
        duration = audio.getnframes() / audio.getframerate()
        assert audio.getnchannels() == 1 and audio.getsampwidth() == 2 and duration > .35
    assert abs(duration - result["duration_s"]) < 1e-9
    delay = row["playing_ms"] - row["requested_ms"]
    playback = row["ended_ms"] - row["playing_ms"]
    assert abs(delay - row["start_delay_ms"]) < 1e-6
    assert abs(playback - row["playback_ms"]) < 1e-6
    if not 0 <= delay <= 500 or playback < duration * 1000 - 80:
        failures.append(item["id"] + ": late or incomplete playback")
    timings.append(delay)
    waves.append({"id": item["id"], "file": str(file), "duration_s": duration,
                  "sha256": hashlib.sha256(file.read_bytes()).hexdigest()})
if not report.get("stale_response_rejected"):
    failures.append("Late playback not rejected")
late = report.get("late_result") or {}
if not late.get("superseded") or late.get("browser") is not False or "audio" in late:
    failures.append("Pending native result not rejected by generation")
if late.get("generation") is not None:
    assert not (args.folder / "speech-audio" / f"{late['generation']}.wav").exists()
ordered = sorted(timings)
result = {"passed": not failures, "failures": failures, "scope": manifest["scope"],
          "count": len(timings), "median_ms": statistics.median(timings) if timings else None,
          "p95_ms": ordered[math.ceil(len(ordered) * .95) - 1] if timings else None,
          "waves": waves}
(args.folder / "judged.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({key: value for key, value in result.items() if key != "waves"}))
