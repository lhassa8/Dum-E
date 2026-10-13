"""Run typed simulated camera journeys; never records microphone audio."""

import argparse
import json
import time
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New local evidence directory")
    parser.add_argument("--url", default="http://127.0.0.1:8886")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    with httpx.Client(base_url=args.url, timeout=60, trust_env=False) as client:

        def state():
            response = client.get("/state")
            response.raise_for_status()
            return response.json()

        initial = state()
        if initial.get("tool_control") != "camera" or initial["busy"]:
            raise RuntimeError("Requires an idle camera simulator")
        if initial.get("recovery", {}).get("can_resume") or any(
            "verified previous task" in location for location in initial["inventory"].values()
        ):
            raise RuntimeError("Requires no paused task or previously delivered tool; reset first")

        def say(text):
            started = time.monotonic()
            response = client.post("/interact", json={"message": text})
            response.raise_for_status()
            result = response.json()
            if not result.get("accepted"):
                raise RuntimeError("Request was not accepted")
            rows.append(
                {
                    "request": text,
                    "response": result,
                    "http_ms": 1000 * (time.monotonic() - started),
                }
            )

        def wait(predicate, timeout=90):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                snapshot = state()
                if predicate(snapshot):
                    return snapshot
                time.sleep(0.025)
            raise TimeoutError(f"Interface did not reach expected state: {snapshot['phase']}")

        def finish():
            snapshot = wait(lambda s: not s["busy"] and not s.get("active_task"))
            rows.append(
                {
                    "completion": snapshot["last_outcome"],
                    "timings": snapshot["responsiveness"],
                    "verified_steps": snapshot["verified_steps"],
                }
            )
            if snapshot["last_outcome"]["status"] != "success":
                raise RuntimeError("Independent task judge rejected this journey")

        try:
            say("Bring me the screwdriver")
            wait(lambda s: "Moving to target" in s["phase"])
            say("What are you doing?")
            started = time.monotonic()
            client.post("/stop").raise_for_status()
            stopped = wait(lambda s: s["phase"] == "Stopped")
            rows.append(
                {
                    "stop_http_to_observed_hold_ms": 1000 * (time.monotonic() - started),
                    "gripper_command": stopped["gripper_command"],
                }
            )
            say("Resume")
            finish()
            say("Actually bring me the wrench instead")
            finish()
            say("Put it back")
            finish()
            print("Typed camera interface journeys passed; no voice-latency claim.")
        finally:
            (args.output / "interface.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
