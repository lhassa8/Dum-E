"""Controlled idle -> native text timing; no audio, speech or robot jobs."""

import argparse
import json
import math
import statistics
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--idle-seconds", type=float, default=12)
    parser.add_argument("--repeat", type=int, default=3)
    args = parser.parse_args()
    if not 0 < args.idle_seconds <= 300 or not 1 <= args.repeat <= 5:
        parser.error("Use 0 < idle seconds <= 300 and 1 <= repeats <= 5")
    args.output.mkdir(parents=True, exist_ok=False)
    payload = {"message": "What kinds of help can you offer at this workbench?", "history": []}
    rows = []
    with httpx.Client(base_url=args.url, timeout=45, trust_env=False) as client:
        response = client.get("/state")
        response.raise_for_status()
        initial = response.json()
        if initial["model_status"] != "ready" or initial["busy"]:
            raise RuntimeError("Use a Ready, idle tool simulator")
        for trial in range(args.repeat):
            warm = client.post("/understand", json=payload)
            warm.raise_for_status()
            started_idle = time.monotonic()
            while time.monotonic() - started_idle < args.idle_seconds:
                time.sleep(min(0.5, max(0, args.idle_seconds - (time.monotonic() - started_idle))))
            actual_idle = time.monotonic() - started_idle
            started = time.perf_counter()
            response = client.post("/understand", json=payload)
            elapsed = (time.perf_counter() - started) * 1000
            response.raise_for_status()
            row = {
                "trial": trial,
                "idle_before_request_s": actual_idle,
                "elapsed_ms": elapsed,
                "result": response.json(),
            }
            rows.append(row)
            with (args.output / "rows.jsonl").open("a") as file:
                file.write(json.dumps(row) + "\n")
            print(json.dumps(row), flush=True)
        after = client.get("/state")
        after.raise_for_status()
        final = after.json()
        if final["job_id"] != initial["job_id"] or final["busy"]:
            raise RuntimeError("Another task changed the simulator; idle trial is invalid")
    values = sorted(row["elapsed_ms"] for row in rows)
    summary = {
        "scope": "Controlled idle to read-only native text response; excludes audio, audible onset "
        "and motion; other read-only requests and machine activity are not isolated",
        "payload": payload,
        "rows": rows,
        "count": len(rows),
        "job_unchanged": True,
        "median_ms": statistics.median(values),
        "p95_ms": values[math.ceil(len(values) * 0.95) - 1],
        "p95_note": "Nearest-rank empirical percentile on the stated small sample count",
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
