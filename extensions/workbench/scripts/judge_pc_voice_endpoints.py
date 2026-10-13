"""Independently check saved-speech identities, meaning, Stop routing and timing scope."""

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--require-frozen-implementation", action="store_true")
args = parser.parse_args()
manifest = json.loads((args.folder / "manifest.json").read_text())
if args.require_frozen_implementation:
    assert manifest.get("implementation_sha256"), "Missing implementation freeze"
    for file, expected in manifest["implementation_sha256"].items():
        assert hashlib.sha256((root / file).read_bytes()).hexdigest() == expected, file
for case in manifest["cases"]:
    assert hashlib.sha256((args.folder / case["file"]).read_bytes()).hexdigest() == (
        case["pcm_sha256"]
    ), case["id"]
report = json.loads((args.folder / "silero-asr-stream.json").read_text())
assert report["protocol_sha256"] == manifest["protocol_sha256"]
assert len(report["rows"]) == len(manifest["cases"])
by_id = {row["id"]: row for row in report["rows"]}
assert len(by_id) == len(report["rows"])
failures, stops, preprocessing, devices = [], [], [], set()
for case in manifest["cases"]:
    row = by_id[case["id"]]
    errors = []
    result = row.get("asr_result") or {}
    positive_stop = case["id"].startswith("stop")
    if case["expected_speech"]:
        if row["submissions"] != 1 or row["completed_ms"] is None or not row["passed"]:
            errors.append("Recognition/completion failed")
        if row["completed_ms"] is not None and row["completed_ms"] < (
            case["last_clean_voiced_ms"] - 40
        ):
            errors.append("Premature completion")
        expected = case.get("expected_text")
        if expected and not re.search(expected, result.get("text", row.get("recognized") or ""),
                                      re.IGNORECASE):
            errors.append("Command meaning not preserved")
        if row["stop_calls"] != int(positive_stop):
            errors.append("Wrong Stop callback count")
        if result:
            devices.add(result["device"])
            edge = result.get("speech_edge_preprocessing")
            if edge:
                assert 0 <= edge["first_sample"] < edge["last_sample"] <= round(
                    edge["original_seconds"] * 16000
                )
                preprocessing.append(result.get("speech_preprocessing_seconds", 0) * 1000)
        if positive_stop and row["completed_ms"] is not None:
            stops.append(row["completed_ms"] - case["last_clean_voiced_ms"])
    elif row["submissions"] or row["stop_calls"]:
        errors.append("Noise-only submission")
    if errors:
        failures.append({"id": case["id"], "failures": errors})


def timing(values):
    ordered = sorted(values)
    return {"count": len(values), "median_ms": statistics.median(values),
            "p95_ms": ordered[math.ceil(0.95 * len(ordered)) - 1], "max_ms": ordered[-1]}


judged = {
    "scope": "Saved audio through real browser capture and ASR to Stop callback; no native Stop",
    "protocol_sha256": manifest["protocol_sha256"], "count": len(by_id),
    "semantic_failures": failures, "semantics_passed": not failures,
    "stop_callback_after_clean_voice": timing(stops) if stops else None,
    "native_preprocessing": timing(preprocessing) if preprocessing else None,
    "observed_asr_devices": sorted(devices),
    "stop_callbacks_over_1000_ms": sum(value > 1000 for value in stops),
    "limitation": "A callback under one second does not prove native cancellation or settling.",
}
(args.folder / "independent-judge.json").write_text(json.dumps(judged, indent=2) + "\n")
print(json.dumps(judged))
