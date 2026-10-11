"""Fixed synthetic language -> read-only native understanding; never actuates."""

import argparse
import hashlib
import json
import math
import statistics
import time
from pathlib import Path

import httpx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--repeat", type=int, default=3)
parser.add_argument("--url", default="http://127.0.0.1:8765")
parser.add_argument("--fixture", type=Path)
args = parser.parse_args()
if args.repeat < 1:
    parser.error("--repeat must be positive")
args.output.mkdir(parents=True, exist_ok=False)
fixture = args.fixture or Path(__file__).resolve().parents[1] / "fixtures/dialogue_cases.json"
cases = json.loads(fixture.read_text())
client = httpx.Client(base_url=args.url, timeout=90, trust_env=False)
ready_started = time.perf_counter()
while True:
    try:
        initial = client.get("/state").json()
        if initial["model_status"] == "ready":
            break
        assert initial["model_status"] != "unavailable", initial.get("model_error")
    except httpx.ConnectError:
        pass
    assert time.perf_counter() - ready_started < 90, "Model never became ready"
    time.sleep(0.1)
ready_wait_ms = (time.perf_counter() - ready_started) * 1000
assert initial["model_status"] == "ready" and not initial["busy"]
rows = []
for repeat in range(args.repeat):
    for case in cases:
        started = time.perf_counter()
        response = client.post(
            "/understand",
            json={"message": case["message"], "history": case.get("history", [])},
        )
        elapsed = (time.perf_counter() - started) * 1000
        response.raise_for_status()
        result = response.json()
        intent = result["intent"]
        correct = intent["action"] in case["actions"] and intent["object"] == case["object"]
        row = {
            "repeat": repeat,
            "name": case["name"],
            "elapsed_ms": elapsed,
            "correct": correct,
            "result": result,
        }
        rows.append(row)
        with (args.output / "rows.jsonl").open("a") as file:
            file.write(json.dumps(row) + "\n")
        print(
            f"{len(rows)}/{args.repeat * len(cases)} {case['name']}: {elapsed:.0f}ms "
            f"{'correct' if correct else 'FAIL'}",
            flush=True,
        )
after = client.get("/state").json()
assert after["job_id"] == initial["job_id"] and not after["busy"]
ordered = sorted(r["elapsed_ms"] for r in rows)
summary = {
    "scope": "Synthetic text and real read-only local inference; "
    "excludes speech, capture, audible onset and motion.",
    "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
    "ready_wait_ms": ready_wait_ms,
    "count": len(rows),
    "incorrect": sum(not r["correct"] for r in rows),
    "median_ms": statistics.median(ordered),
    "p95_ms": ordered[math.ceil(len(ordered) * 0.95) - 1],
    "initial_job": initial["job_id"],
    "final_job": after["job_id"],
    "rows": rows,
}
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=2))
