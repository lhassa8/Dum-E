"""Judge browser speech/Stop/continuation against native events and simulator truth."""

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.tool_routing import is_stop_request

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("folder", type=Path)
parser.add_argument("--events", type=Path, required=True)
args = parser.parse_args()
manifest = json.loads((args.folder / "physical-manifest.json").read_text())
protocol = json.loads((root / "fixtures/pc_physical_voice_stop_protocol.json").read_text())
assert manifest["protocol"] == protocol
assert hashlib.sha256((root / "fixtures/pc_physical_voice_stop_protocol.json").read_bytes())\
    .hexdigest() == manifest["protocol_sha256"]
protected = (root / "fixtures/physical_voice_stop_protocol.json").read_bytes()
assert hashlib.sha256(protected).hexdigest() == manifest["protected_criteria_sha256"]
for name, value in json.loads(protected)["criteria"].items():
    assert protocol["criteria"][name] == value, name
for file, digest in manifest["implementation_sha256"].items():
    assert hashlib.sha256((root / file).read_bytes()).hexdigest() == digest, file
for item in [*manifest["cases"], manifest["fetch"], manifest["question"],
             manifest["resume"], manifest["return"]]:
    assert hashlib.sha256((args.folder / item["file"]).read_bytes()).hexdigest() == (
        item["pcm_sha256"]
    ), item["id"]
report = json.loads((args.folder / "physical-stop-browser.json").read_text())
events = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
criteria = protocol["criteria"]
rows, global_failures, timings = [], [], []
pending_count = 0
for row in report.get("rows", []):
    failures = []
    case = next(case for case in manifest["cases"] if case["id"] == row["id"])
    assert [capture["file"] for capture in row["captures"]] == [
        manifest["question"]["file"], case["file"]
    ], "Captured source identities differ from frozen question/Stop"
    reference = row["captures"][1]["started_epoch_s"] + case["last_clean_voiced_ms"] / 1000
    assert abs(reference - row["reference_last_voiced_epoch_s"]) < 1e-6
    stops = [e for e in events if e["kind"] == "stop_requested"
             and e.get("job_id") == row["before_stop"]["job_id"]]
    native_ms, pending = None, False
    if len(stops) != 1:
        failures.append("Native Stop event count/identity mismatch")
    else:
        stop = stops[0]
        # Windows browser and WSL wall clocks demonstrably diverge. The
        # acknowledged native Stop event occurs between POST and response in
        # the same browser clock; require its conservative upper bound <=1 s.
        lower_ms = (row["stop_post_epoch_s"] - reference) * 1000
        native_ms = (row["stop_done_epoch_s"] - reference) * 1000
        timings.append(native_ms)
        if not 0 <= native_ms <= criteria["maximum_end_to_native_stop_ms"]:
            failures.append("Conservative Stop upper bound exceeds 1000 ms; deadline unproven")
        assert stop["job_id"] == row["before_stop"]["job_id"]
        if stop["phase"] in {"Ready", "Stopped", "Task failed", "Understanding your request"}:
            failures.append("Native Stop was not during active physical work")
        starts = [e for e in events if e["kind"] in {
            "camera_inference_started", "language_inference_started"
        } and e["active_job"] == stop["job_id"]
            and e["request"] == row["recognized"][0]["text"] and e["time"] < stop["time"]]
        for start in starts:
            finish_kind = start["kind"].replace("started", "finished")
            finish = next((e for e in events if e["kind"] == finish_kind
                           and e["active_job"] == start["active_job"]
                           and e["request"] == start["request"]
                           and e["time"] >= start["time"]), None)
            if finish and stop["time"] < finish["time"]:
                pending = True
        if pending:
            pending_count += 1
            if not (row["question_result"]["mode"] == "superseded"
                    and row["question_result"]["accepted"] is False):
                failures.append("Actual pending inference not superseded")
    before, physical, later = row["before_stop"], row["after_stop"], row["after_settling"]
    drift = float(np.max(np.abs(np.array(physical["robot_joints"]) - later["robot_joints"])))
    motion = float(np.max(np.abs(np.array(row["first_held"]["robot_joints"])
                                 - before["robot_joints"])))
    held_motion = float(np.linalg.norm(np.array(physical["objects"]["screwdriver"])
                                       - later["objects"]["screwdriver"]))
    checks = {
        "natural_fetch_cuda_asr": row.get("initial_request", {}).get("recognized", {})
        .get("device") == "cuda" and row.get("initial_request", {}).get("result", {})
        .get("task_id") == row["task_id"],
        "recent_before_stop_sample": row.get("before_stop_sample_age_s", 1) <= .25,
        "actual_motion": before["busy"] and motion > criteria["minimum_pre_stop_joint_motion_rad"],
        "settled_joint_drift": drift < criteria["maximum_settled_joint_drift_rad"],
        "held_tool_drift": held_motion < criteria["maximum_held_tool_translation_m"],
        "elevated_tool": min(
            physical["objects"]["screwdriver"][2], later["objects"]["screwdriver"][2]
        ) > criteria["minimum_tool_height_m"],
        "gripper_retained": before["gripper_command"] == physical["gripper_command"]
        == later["gripper_command"],
        "cancelled_no_queue": row["task_status"] == "cancelled" and not row["remaining_work"],
        "stopped": row["stopped_phase"] == "Stopped",
        "tracks_ended": len(row["captures"]) == 2 and all(
            c["tracks_ended"] for c in row["captures"]
        ),
        "actual_configured_asr": len(row["recognized"]) == 2
        and row["recognized"][0]["device"] == protocol["recognizer_profile"]["general_device"]
        and row["recognized"][1]["device"] == protocol["recognizer_profile"]["stop_device"]
        and row["recognized"][1].get("model") == protocol["recognizer_profile"]["stop_model"]
        and row["recognized"][1].get("revision") == protocol["recognizer_profile"]["stop_revision"]
        and row["recognized"][1].get("device_fallback") is False
        and all(r.get("speech_edge_preprocessing") for r in row["recognized"]),
        "positive_stop": is_stop_request(row["recognized"][1]["text"]),
        "resume_job": row.get("resume", {}).get("result", {}).get("mode") == "task",
        "completed_resume_no_pickup": row.get("completed_resume", {}).get("result", {})
        .get("mode") == "conversation" and row.get("after_completed_resume", {}).get("job_id")
        == row.get("delivered", {}).get("job_id")
        and not row.get("after_completed_resume", {}).get("busy", True)
        and row.get("completed_resume", {}).get("result", {}).get("task_id") is None,
        "continuation_cuda_asr": all(
            row.get(name, {}).get("recognized", {}).get("device") == "cuda"
            and row.get(name, {}).get("recognized", {}).get("speech_edge_preprocessing")
            for name in ["resume", "completed_resume", "return"]
        ),
    }
    lifts = []
    for key in ["delivered", "returned"]:
        state = row.get(key) or {}
        outcome = state.get("last_outcome") or {}
        checks[key + "_placement"] = outcome.get("status") == "success" and (
            outcome.get("distance_m", float("inf")) < criteria["maximum_placement_distance_m"]
        )
        native_outcomes = [e for e in events if e["kind"] == "outcome"
                           and e.get("job_id") == state.get("job_id") and "lift_m" in e]
        lift = native_outcomes[-1]["lift_m"] if native_outcomes else 0
        lifts.append(lift)
        checks[key + "_lift"] = lift >= criteria["minimum_lift_m"]
        for other in ["wrench", "hammer"]:
            checks[key + "_undisturbed_" + other] = bool(state) and float(np.linalg.norm(
                np.array(state["objects"][other]) - row["first_held"]["objects"][other]
            )) <= criteria["maximum_unrelated_displacement_m"]
    failures.extend(name for name, passed in checks.items() if not passed)
    rows.append({"id": row["id"], "passed": not failures, "failures": failures,
                 "end_to_native_stop_ms": native_ms, "verified_pending_generation": pending,
                 "native_stop_timing_kind": "conservative upper bound at RPC acknowledgment",
                 "native_stop_lower_bound_ms": lower_ms if len(stops) == 1 else None,
                 "settled_joint_drift_rad": drift, "held_tool_translation_m": held_motion,
                 "joint_motion_rad": motion, "lift_m": lifts})
if report.get("failed"):
    global_failures.append(report.get("error", "Browser failed"))
if report.get("in_progress"):
    global_failures.append("Browser run not finalized")
if sorted(row["id"] for row in rows) != sorted(case["id"] for case in manifest["cases"]):
    global_failures.append("Frozen case identities/counts differ")
if len(rows) != len(manifest["cases"]):
    global_failures.append("Not all frozen cases completed")
if pending_count < criteria["minimum_verified_pending_reply_interruptions"]:
    global_failures.append("No verified pending inference interruption")
global_failures.extend(
    f"{row['id']}: {', '.join(row['failures'])}" for row in rows if not row["passed"]
)
ordered = sorted(timings)
judged = {"rows": rows, "passed": not global_failures, "failures": global_failures,
          "verified_pending_reply_interruptions": pending_count,
          "timing_ms": {"count": len(timings), "median": statistics.median(timings),
                        "p95": ordered[math.ceil(len(ordered) * 0.95) - 1]} if timings else None,
          "scope": protocol["scope"], "protocol_sha256": manifest["protocol_sha256"]}
judged["timing_kind"] = (
    "Conservative browser-clock upper bounds; native event matched by unique job"
)
(args.folder / "physical-stop-judged.json").write_text(json.dumps(judged, indent=2) + "\n")
print(json.dumps({"passed": judged["passed"], "rows": len(rows), "failures": global_failures,
                  "pending": pending_count, "timing_ms": judged["timing_ms"]}))
