"""Verify browser Stop trials against native model/physics events, not UI verdicts."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.tool_routing import is_stop_request

ROOT = Path(__file__).resolve().parents[1]


def judge(folder, log):
    manifest = json.loads((folder / "physical-manifest.json").read_text())
    protocol_file = ROOT / "fixtures/physical_voice_stop_protocol.json"
    if hashlib.sha256(protocol_file.read_bytes()).hexdigest() != manifest["protocol_sha256"]:
        raise ValueError("Frozen Stop protocol changed")
    if manifest["protocol"] != json.loads(protocol_file.read_text()):
        raise ValueError("Embedded Stop criteria differ from frozen protocol")
    frozen_corpus = json.loads((ROOT / "docs/speech-detector-evidence.json").read_text())[
        "pcm_manifest"
    ]
    if manifest["endpoint_protocol_sha256"] != frozen_corpus["protocol_sha256"]:
        raise ValueError("Endpoint corpus protocol changed")
    for item in manifest["cases"]:
        frozen_item = next(case for case in frozen_corpus["cases"] if case["id"] == item["id"])
        if item != frozen_item:
            raise ValueError("Stop clip/boundary differs from retained published corpus")
    criteria = manifest["protocol"]["criteria"]
    for item in [manifest["question"], *manifest["cases"]]:
        if hashlib.sha256((folder / item["file"]).read_bytes()).hexdigest() != item["pcm_sha256"]:
            raise ValueError(f"PCM identity changed: {item['file']}")
    report = json.loads((folder / "physical-stop-browser.json").read_text())
    if report.get("protocol_sha256") != manifest["protocol_sha256"]:
        raise ValueError("Browser report protocol identity mismatch")
    events = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
    rows = []
    for row in report.get("rows", []):
        failures = []
        fixture = next((item for item in manifest["cases"] if item["id"] == row["id"]), None)
        if fixture is None or len(row.get("captures", [])) != 2:
            failures.append("Unknown fixture or capture count")
            reference = row["reference_last_voiced_epoch_s"]
        else:
            reference = (
                row["captures"][1]["started_epoch_s"] + fixture["last_clean_voiced_ms"] / 1000
            )
            if row["captures"][1]["file"] != fixture["file"]:
                failures.append("Captured Stop source mismatch")
            if abs(reference - row["reference_last_voiced_epoch_s"]) > 0.000001:
                failures.append("Timing reference differs from frozen source boundary")
        stops = [
            e
            for e in events
            if e["kind"] == "stop_requested"
            and row["stop_post_epoch_s"] - 0.05 <= e["time"] <= row["stop_done_epoch_s"] + 0.05
        ]
        model = [
            e
            for e in events
            if e["kind"] == "understanding"
            and e.get("active_job") == row["before_stop"]["job_id"]
            and e.get("request") == row["recognized"][0]["text"]
        ]
        if len(stops) != 1 or len(model) != 1:
            failures.append("Native event identity/count mismatch")
        native_ms = None
        verified_pending = False
        if len(stops) == 1 and len(model) == 1:
            native_ms = (stops[0]["time"] - reference) * 1000
            profile = model[0].get("profile") or {}
            first_token = model[0]["time"] - profile.get("elapsed_ms", 0) / 1000
            first_token += profile.get("first_token_ms", 0) / 1000
            verified_pending = (
                model[0]["route"] == "model" and first_token < stops[0]["time"] < model[0]["time"]
            )
            if not 0 <= native_ms <= criteria["maximum_end_to_native_stop_ms"]:
                failures.append("End to native Stop exceeds frozen timing gate")
            if row["pending_reply"] and not verified_pending:
                failures.append("Browser pending flag lacks native generation evidence")
        physical, later, before = row["after_stop"], row["after_settling"], row["before_stop"]
        drift = float(
            np.max(np.abs(np.array(physical["robot_joints"]) - np.array(later["robot_joints"])))
        )
        motion = float(
            np.max(
                np.abs(
                    np.array(row["first_held"]["robot_joints"]) - np.array(before["robot_joints"])
                )
            )
        )
        checks = {
            "actual_motion_before_stop": motion > criteria["minimum_pre_stop_joint_motion_rad"],
            "settled_joint_drift": drift < criteria["maximum_settled_joint_drift_rad"],
            "native_busy_before_stop": before["busy"],
            "tool_remains_elevated": min(
                physical["objects"]["screwdriver"][2], later["objects"]["screwdriver"][2]
            )
            > criteria["minimum_tool_height_m"],
            "retained_gripper_command": before["gripper_command"]
            == physical["gripper_command"]
            == later["gripper_command"],
            "cancelled_without_queued_work": row["task_status"] == "cancelled"
            and not row["remaining_work"],
            "stopped_phase": row["stopped_phase"] == "Stopped",
            "owned_tracks_ended": len(row["captures"]) == 2
            and all(c["tracks_ended"] for c in row["captures"]),
            "two_actual_transcriptions": len(row["recognized"]) == 2,
            "positive_stop_transcript": len(row["recognized"]) == 2
            and is_stop_request(row["recognized"][1]["text"]),
            "pending_reply_superseded": not verified_pending
            or (
                row["question_result"]["mode"] == "superseded"
                and row["question_result"]["accepted"] is False
            ),
        }
        # Preserve the existing 4 mm unrelated-body-center displacement criterion.
        unrelated = {
            name: float(
                np.linalg.norm(
                    np.array(later["objects"][name]) - np.array(row["first_held"]["objects"][name])
                )
            )
            for name in ["hammer", "wrench"]
        }
        checks["unrelated_tools_undisturbed"] = all(value <= 0.004 for value in unrelated.values())
        failures.extend(name for name, passed in checks.items() if not passed)
        rows.append(
            {
                "id": row["id"],
                "passed": not failures,
                "failures": failures,
                "end_to_native_stop_ms": native_ms,
                "verified_pending_generation": verified_pending,
                "joint_motion_rad": motion,
                "settled_joint_drift_rad": drift,
                "unrelated_tool_displacement_m": unrelated,
                "native_stop_event": stops[0] if len(stops) == 1 else None,
                "native_understanding_event": model[0] if len(model) == 1 else None,
            }
        )
    failures = []
    if report.get("failed"):
        failures.append("Browser run failed: " + report.get("error", "unknown"))
    if {r["id"] for r in rows} != set(manifest["protocol"]["stop_cases"]) or len(rows) != 6:
        failures.append("Missing/duplicate frozen trials")
    if any(not r["passed"] for r in rows):
        failures.append("One or more native/physical criteria failed")
    if (
        sum(r["verified_pending_generation"] for r in rows)
        < criteria["minimum_verified_pending_reply_interruptions"]
    ):
        failures.append("No independently verified Stop during active generation")
    timings = [r["end_to_native_stop_ms"] for r in rows if r["end_to_native_stop_ms"] is not None]
    evidence = {
        "scope": manifest["protocol"]["scope"],
        "protocol_sha256": manifest["protocol_sha256"],
        "browser_report_sha256": hashlib.sha256(
            (folder / "physical-stop-browser.json").read_bytes()
        ).hexdigest(),
        "native_log": str(log),
        "native_model_ready_event": next(
            (e for e in reversed(events) if e["kind"] == "model_ready"), None
        ),
        "passed": not failures,
        "failures": failures,
        "rows": rows,
        "timing_ms": {
            "count": len(timings),
            "median": float(np.median(timings)) if timings else None,
            "p95": float(np.percentile(timings, 95)) if timings else None,
            "max": max(timings) if timings else None,
        },
        "limitations": "Six saved synthetic utterance variants; no live mic, speakers, hardware, "
        "general acoustic reliability or policy-based manipulation proof. "
        "Browser source-start epoch and native wall time share the Mac clock; "
        "audio scheduling/reference quantization remains in the timing boundary.",
    }
    (folder / "physical-stop-judged.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({key: evidence[key] for key in ["passed", "failures", "timing_ms"]}, indent=2))
    return evidence["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--native-log", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if judge(args.folder.resolve(), args.native_log.resolve()) else 1)
