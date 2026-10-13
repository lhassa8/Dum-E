"""Reconstruct every full camera journey verdict from recorded physical measurements."""

import argparse
import hashlib
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("results", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--protocol", type=Path, required=True)
args = parser.parse_args()
spec = json.loads(args.protocol.read_text())
root = Path(__file__).resolve().parents[1]
criterion_path = root / "fixtures" / spec["criterion_fixture"]
assert hashlib.sha256(criterion_path.read_bytes()).hexdigest() == spec["criterion_fixture_sha256"]
c = json.loads(criterion_path.read_text())["criteria"]
rows = json.loads(args.results.read_text())
assert len(rows) == spec["case_count"]
assert {r["case"]["id"] for r in rows} == {
    f"pc-reserved-{i:03d}" for i in range(spec["case_count"])
}


def placement(distance, height, speed):
    return (
        distance < c["position_error_m"]
        and height < c["resting_height_m"]
        and speed < c["speed_m_s"]
    )


audited = []
for r in rows:
    p, returned, held = r["physics"], r["return"], r["hold"]
    lifted = p["max_lift_m"] >= c["lift_m"]
    placed = placement(p["distance_m"], p["final_height_m"], p["speed_m_s"])
    assert lifted == p["lifted"] and placed == p["placed"]
    first = (
        lifted
        and placed
        and p["gripper_open"]
        and r["actor_outcome"]["status"] == "released_unverified"
    )
    holding = r["case"]["journey"] == "deliver" or (
        held is not None
        and held["grip_retained"]
        and held["joint_drift_rad"] < c["hold_joint_drift_rad"]
    )
    back = r["case"]["journey"] == "redirect"
    if returned is not None:
        back = (
            returned["max_lift_m"] >= c["lift_m"]
            and placement(returned["distance_m"], returned["final_height_m"], returned["speed_m_s"])
            and returned["gripper_open"]
            and returned["actor_outcome"]["status"] == "released_unverified"
        )
    passed = bool(
        first and holding and back and p["other_tool_disturbance_m"] < c["untouched_disturbance_m"]
    )
    assert passed == r["passed"], f"Stored verdict differs: {r['case']['id']}"
    audited.append(
        {
            "id": r["case"]["id"],
            "tool": r["case"]["tool"],
            "journey": r["case"]["journey"],
            "passed": passed,
            "first_leg_passed": bool(first),
            "return_passed": bool(back),
            "holding_passed": bool(holding),
            "actor_status": r["actor_outcome"]["status"],
            "actor_message": r["actor_outcome"]["message"],
            "distance_m": p["distance_m"],
            "height_m": p["final_height_m"],
            "speed_m_s": p["speed_m_s"],
            "max_lift_m": p["max_lift_m"],
            "disturbance_m": p["other_tool_disturbance_m"],
            "return_outcome": None if returned is None else returned["actor_outcome"],
        }
    )
n, k = len(audited), sum(r["passed"] for r in audited)
z = 1.959963984540054
center = (k / n + z * z / (2 * n)) / (1 + z * z / n)
half = z * math.sqrt((k / n) * (1 - k / n) / n + z * z / (4 * n * n)) / (1 + z * z / n)
report = {
    "sample_size": n,
    "full_journey_passes": k,
    "fraction": k / n,
    "observed_gate": c["expected_success_fraction"],
    "qualified": k / n >= c["expected_success_fraction"],
    "wilson_95_interval": [center - half, center + half],
    "all_stored_verdicts_reconstructed": True,
    "source_results_sha256": hashlib.sha256(args.results.read_bytes()).hexdigest(),
    "criteria": c,
    "rows": audited,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n")
print(
    json.dumps(
        {
            key: report[key]
            for key in (
                "sample_size",
                "full_journey_passes",
                "fraction",
                "qualified",
                "wilson_95_interval",
                "all_stored_verdicts_reconstructed",
            )
        },
        indent=2,
    )
)
