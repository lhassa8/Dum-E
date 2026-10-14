"""Observe scene-cache validity during real reset; no policy, microphone or hardware."""

import argparse
import json
import time
from pathlib import Path

import httpx

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--url", default="http://127.0.0.1:8901")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
rows = []
with httpx.Client(base_url=args.url, timeout=10, trust_env=False) as client:
    def state():
        return client.get("/state").raise_for_status().json()

    first = state()
    if first["phase"] == "paused":
        client.post("/resume", json={}).raise_for_status()
    if first["phase"] == "idle":
        client.post("/initialize", json={"task_id": 0}).raise_for_status()
    deadline = time.monotonic()+60
    while state()["phase"] not in ("failed", "success"):
        if time.monotonic() > deadline:
            raise TimeoutError("Original active-step budget did not end the neutral episode")
        time.sleep(.01)
    started = time.monotonic()
    response = client.post("/initialize", json={"task_id": 2}).raise_for_status().json()
    while time.monotonic()-started < 10:
        value = state()
        rows.append({"elapsed_s": time.monotonic()-started, "state": value})
        if value["phase"] == "running" and value["physics_ready"]:
            break
        time.sleep(.002)
    stale = [r for r in rows if r["state"]["phase"] == "initializing"
             and r["state"]["physics_ready"]]
    report = {"initialize_response": response, "samples": rows,
              "stale_ready_samples": len(stale), "stale_ready_seen": bool(stale),
              "scope": "Real neutral simulation budget then reset; no inference or hardware"}
    (args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"stale_ready_seen": bool(stale), "samples": len(rows)}))
