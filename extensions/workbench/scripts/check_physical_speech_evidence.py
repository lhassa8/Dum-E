"""Reject altered full-journey speech evidence without changing original records."""

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--events", type=Path, required=True)
args = parser.parse_args()
folder = args.folder.resolve()
manifest = json.loads((folder / "physical-manifest.json").read_text())
original = json.loads((folder / "physical-stop-browser.json").read_text())
checks = []


def check(name, alter, expected):
    with tempfile.TemporaryDirectory(prefix="physical-speech-evidence-") as location:
        target = Path(location)
        shutil.copyfile(folder / "physical-manifest.json", target / "physical-manifest.json")
        for item in [*manifest["cases"], *[manifest[key] for key in
                     ["fetch", "question", "resume", "return"]]]:
            shutil.copyfile(folder / item["file"], target / item["file"])
        report = copy.deepcopy(original)
        alter(report)
        (target / "physical-stop-browser.json").write_text(json.dumps(report))
        result = subprocess.run([sys.executable, str(Path(__file__).with_name(
            "judge_physical_speech.py")), str(target), "--events", str(args.events.resolve())],
            capture_output=True, text=True)
        passed = result.returncode == 0 and json.loads(
            (target / "physical-speech-judged.json").read_text())["passed"]
        assert passed == expected, name
        checks.append({"case": name, "expected_pass": expected, "actual_pass": passed})


check("unaltered complete journeys pass", lambda report: None, True)
check("missing speech rejected", lambda report: report["rows"][0].pop("speech_output"), False)


def truncated(report):
    record = next(r for r in report["rows"][0]["speech_output"]["records"] if r["ended_ms"])
    record["ended_ms"] = record["playing_ms"] + 100
    record["ended_position_s"] = .1


check("truncated acknowledgment rejected", truncated, False)


def no_stop(report):
    for record in report["rows"][0]["speech_output"]["records"]:
        if record["text"].startswith("Stopped"):
            record["ended_ms"] = None
            record["cancelled_ms"] = record["playing_ms"] + 100


check("missing complete Stop confirmation rejected", no_stop, False)
check("output error rejected", lambda report: report["rows"][0]["speech_output"]
      ["errors"].append("Playback failed"), False)


def late_ack(report):
    record = next(r for r in report["rows"][0]["speech_output"]["records"]
                  if r["kind"] == "acknowledgment" and r["ended_ms"])
    record["completed_ms"] -= 1000


check("late acknowledgment rejected", late_ack, False)
(folder / "speech-evidence-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
print(f"PASS: {len(checks)} altered speech records checked; original evidence unchanged.")
