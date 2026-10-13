"""Reject altered speech evidence without changing the retained real run."""

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
args = parser.parse_args()
folder = args.folder.resolve()
original = json.loads((folder / "browser.json").read_text())
checks = []


def check(name, alter, expected):
    with tempfile.TemporaryDirectory(prefix="windows-dialogue-evidence-") as location:
        target = Path(location)
        for file in ["manifest.json", "speech.jsonl", "speech-playback.jsonl"]:
            shutil.copyfile(folder / file, target / file)
        shutil.copytree(folder / "speech-audio", target / "speech-audio")
        data = copy.deepcopy(original)
        alter(data)
        (target / "browser.json").write_text(json.dumps(data))
        result = subprocess.run([sys.executable, str(Path(__file__).with_name(
            "judge_windows_dialogue.py")), str(target)], capture_output=True, text=True)
        passed = result.returncode == 0 and json.loads(
            (target / "judged.json").read_text())["passed"]
        assert passed == expected, name
        checks.append({"case": name, "expected_pass": expected, "actual_pass": passed})


check("unaltered twelve replies pass", lambda data: None, True)
check("missing reply rejected", lambda data: data["rows"].pop(), False)
check("wrong voice rejected", lambda data: data["rows"][0]["result"].update(
    voice="Other voice"), False)
check("incomplete playback rejected", lambda data: data["rows"][0].update(
    ended_ms=data["rows"][0]["playing_ms"] + 100, playback_ms=100), False)
check("late audio advertised rejected", lambda data: data["late_result"].update(
    audio="/speech-audio/13"), False)


def late(data):
    data["rows"][0]["playing_ms"] += 1000
    data["rows"][0]["start_delay_ms"] += 1000
    data["rows"][0]["playback_ms"] -= 1000


check("late playback rejected", late, False)
(folder / "evidence-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
print(f"PASS: {len(checks)} altered-record checks; original evidence unchanged.")
