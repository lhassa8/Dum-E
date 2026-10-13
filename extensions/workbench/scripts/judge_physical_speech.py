"""Combine unchanged physical judges with real native speech lifecycle evidence."""

import argparse
import json
import math
import statistics
import subprocess
import sys
import wave
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--events", type=Path, required=True)
args = parser.parse_args()
subprocess.run([sys.executable, str(root / "scripts/judge_pc_physical_voice.py"),
                str(args.folder), "--events", str(args.events)], check=True)
physical = json.loads((args.folder / "physical-stop-judged.json").read_text())
report = json.loads((args.folder / "physical-stop-browser.json").read_text())
manifest = json.loads((args.folder / "physical-manifest.json").read_text())
profile = manifest["speech_output"]
assert profile["backend"] == "windows-sapi"
assert profile["maximum_acknowledgment_start_ms"] == 500
assert profile["maximum_post_to_playing_ms"] == 500
assert profile["minimum_acknowledgments_per_case"] == 4
native = args.events.parent.parent
spoken = [json.loads(line) for line in (native / "speech.jsonl").read_text().splitlines()]
events = [json.loads(line) for line in (native / "speech-playback.jsonl").read_text().splitlines()]
rows, ack_times, reply_times = [], [], []
for row in report["rows"]:
    output = row.get("speech_output") or {}
    records = output.get("records", [])
    failures = list(output.get("errors", []))
    acknowledgments = 0
    completed = []
    for record in records:
        result = record.get("api")
        if not result:
            if record.get("cancelled_ms") is None:
                failures.append("Unresolved speech record")
            continue
        generation = result["generation"]
        matches = [entry for entry in spoken if entry["generation"] == generation]
        assert len(matches) == 1
        assert matches[0]["text"] == record["text"][:500]
        assert all(matches[0][key] == value for key, value in result.items())
        if record["playing_ms"] is not None:
            assert sum(event["kind"] == "started" and event["generation"] == generation
                       and event["accepted"] for event in events) == 1
            elapsed = record["playing_ms"] - record["posted_ms"]
            if not 0 <= elapsed <= 500:
                failures.append("Speech API to playback exceeds 500 ms")
            reply_times.append(elapsed)
        if record["ended_ms"] is not None:
            assert record["playing_ms"] is not None
            assert any(event["kind"] == "finished" and event["generation"] == generation
                       for event in events)
            file = (root / ".cache/local-speech/acknowledgment.wav"
                    if record["kind"] == "acknowledgment"
                    else native / "speech-audio" / f"{generation}.wav")
            with wave.open(str(file)) as audio:
                duration_ms = audio.getnframes() / audio.getframerate() * 1000
            if record["ended_ms"] - record["playing_ms"] < duration_ms - 80:
                failures.append("Spoken confirmation truncated")
            if (abs(record.get("media_duration_s", -1) * 1000 - duration_ms) > 1
                    or abs(record.get("ended_position_s", -1) * 1000 - duration_ms) > 20
                    or not 0 <= record.get("playing_position_s", -1) <= duration_ms / 1000):
                failures.append("Media clock does not reach the complete WAV endpoint")
            completed.append(record["text"])
            if record["kind"] == "acknowledgment":
                elapsed = record["playing_ms"] - record["completed_ms"]
                ack_times.append(elapsed)
                acknowledgments += 1
                if not 0 <= elapsed <= 500:
                    failures.append("Detected completion to acknowledgment exceeds 500 ms")
            elif result.get("backend") != "windows-sapi" or not result.get("local"):
                failures.append("Ordinary reply used a different provider")
        elif record.get("cancelled_ms") is None:
            failures.append("Speech neither completed nor cancelled")
    if acknowledgments < 4:
        failures.append("Missing one of four complete idle-request acknowledgments")
    if not any(text.startswith("Stopped") for text in completed):
        failures.append("No complete spoken Stop confirmation")
    for key in ["delivered", "returned"]:
        message = row[key]["last_outcome"]["message"]
        if message not in completed:
            failures.append(f"No complete verified {key} confirmation")
    if row["completed_resume"]["result"]["message"] not in completed:
        failures.append("No completion-aware Proceed spoken confirmation")
    rows.append({"id": row["id"], "passed": not failures, "failures": failures,
                 "complete_acknowledgments": acknowledgments,
                 "complete_replies": len(completed) - acknowledgments})


def timing(values):
    if not values:
        return None
    ordered = sorted(values)
    return {"count": len(values), "median_ms": statistics.median(values),
            "p95_ms": ordered[math.ceil(len(values) * .95) - 1]}


result = {"passed": physical["passed"] and all(row["passed"] for row in rows),
          "physical_passed": physical["passed"], "rows": rows,
          "acknowledgment": timing(ack_times), "speech_api_to_player": timing(reply_times),
          "scope": profile["scope"]}
(args.folder / "physical-speech-judged.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
