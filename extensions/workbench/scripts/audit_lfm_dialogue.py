"""Independently audit saved dialogue runs without inference or robot commands."""

import argparse
import hashlib
import json
import math
import statistics
from dataclasses import asdict
from pathlib import Path

from physical_ai_lab.assistant.tool_language import ToolIntent

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("runs", type=Path, nargs="+")
args = parser.parse_args()
for directory in args.runs:
    report = json.loads((directory / "summary.json").read_text())
    protocol = json.loads((directory / "protocol.json").read_text())
    assert report["protocol"] == protocol
    assert protocol["repeats"] == 3
    assert protocol["fixture_sha256"] == (
        "aed016fa54905b47478d8181fadd701435dae51fa81a604933bf2ac7dedf4593")
    assert hashlib.sha256((directory / "merged-fixture.json").read_bytes()).hexdigest() == (
        protocol["fixture_sha256"])
    assert hashlib.sha256((directory / "benchmark_lfm_dialogue.py").read_bytes()).hexdigest() == (
        protocol["actor_sha256"])
    fixture = json.loads((directory / "merged-fixture.json").read_text())
    assert len(fixture) == protocol["unique_cases"] == 31
    planned = [(repeat, case) for repeat in range(3) for case in fixture]
    row_file = directory / "rows.jsonl"
    rows = ([json.loads(line) for line in row_file.read_text().splitlines()]
            if row_file.exists() else [])
    assert 0 <= len(rows) <= len(planned) == protocol["planned_cases"] == 93
    assert len(rows) == 93 or "startup_error" in report
    assert rows == report["rows"]
    assert report["count"] == len(rows)
    assert report["not_run"] == 93 - len(rows)
    for row, (repeat, case) in zip(rows, planned, strict=False):
        assert (row["repeat"], row["case"]) == (repeat, case)
        if "intent" in row:
            intent = ToolIntent.parse(row["raw"])
            assert asdict(intent) == row["intent"]
            assert row["correct"] == (
                intent.action in case["actions"] and intent.object == case["object"])
            assert row["profile"]["returned_model"] == protocol["model"]
            assert row["profile"]["finish_reason"] == "stop"
        else:
            assert row["error"] and row["correct"] is False
    assert report["incorrect"] == sum(not row["correct"] for row in rows)
    values = sorted(row["elapsed_ms"] for row in rows)
    if values:
        assert report["median_ms"] == statistics.median(values)
        assert report["p95_ms"] == values[math.ceil(.95 * len(values)) - 1]
        assert report["max_ms"] == max(values)
    result = {
        "run": directory.name, "attempted": len(rows), "correct": len(rows)-report["incorrect"],
        "not_run": report["not_run"], "fixture_sha256": protocol["fixture_sha256"],
        "raw_audit": "pass", "reply_quality": "requires separate human-readable review",
    }
    (directory / "audit.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result))
