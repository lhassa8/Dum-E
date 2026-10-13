"""Independent gravity witness: open a policy-lifted grip while the arm stays paused."""

import argparse
import json
import time
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)


def get(route):
    return json.load(urllib.request.urlopen("http://127.0.0.1:8901" + route, timeout=5))


def post(url, body):
    request = urllib.request.Request(
        url, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    return json.load(urllib.request.urlopen(request, timeout=35))


report = {
    "passed": False,
    "scope": "Extra typed policy episode, not part of the frozen three-layout qualification",
    "min_drop_m": 0.03,
}
rows = []
try:
    started = post(
        "http://127.0.0.1:8896/interact",
        {"message": "Pick up the black bowl next to the ramekin and place it on the plate."},
    )
    assert started["mode"] == "start" and started["state"]["task_id"] == 1
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        state, judge = get("/state"), get("/judge")
        assert state["phase"] not in ("success", "failed"), state
        if judge and judge["grasp_contacts"] and judge["xyz"][2] - judge["initial_xyz"][2] >= 0.08:
            break
        time.sleep(0.01)
    else:
        raise AssertionError("No 80 mm contact grasp to release")
    stopped = post("http://127.0.0.1:8896/stop", {})
    assert stopped["phase"] == "paused"
    before = get("/stop-judge")
    post("http://127.0.0.1:8901/release-held-grasp", {})
    wall = time.monotonic()
    while time.monotonic() - wall < 2 or not rows or rows[-1]["sim_time"] - before["sim_time"] <= 1:
        assert time.monotonic() - wall < 5, "Physics stalled"
        rows.append(get("/judge"))
        time.sleep(0.05)
    after = rows[-1]
    state = get("/state")
    report.update(
        before=before, after=after, drop_m=before["xyz"][2] - after["xyz"][2], final_state=state
    )
    assert report["drop_m"] >= 0.03
    assert not after["grasp_contacts"]
    assert state["phase"] == "paused" and state["policy_steps"] == stopped["policy_steps"]
    report["passed"] = True
except Exception as caught:
    report["error"] = repr(caught)
    raise
finally:
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output / "trace.json").write_text(json.dumps(rows) + "\n")
    print(json.dumps(report, indent=2))
