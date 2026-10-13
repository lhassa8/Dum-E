"""Check that altered cancellation evidence cannot qualify a retained real run."""

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--events", type=Path, required=True)
    args = parser.parse_args()
    folder, events = args.folder.resolve(), args.events.resolve()
    original = json.loads((folder / "physical-stop-browser.json").read_text())
    manifest = json.loads((folder / "physical-manifest.json").read_text())
    original_verdict = json.loads((folder / "physical-stop-judged.json").read_text())["passed"]
    checks = []

    def run(name, alter, expected, event_override=None):
        with tempfile.TemporaryDirectory(prefix="pc-cancellation-evidence-") as location:
            target = Path(location)
            for item in [*manifest["cases"], *[manifest[key] for key in
                         ["fetch", "question", "resume", "return"]]]:
                destination = target / item["file"]
                if not destination.exists():
                    destination.symlink_to(folder / item["file"])
            report = copy.deepcopy(original)
            alter(report)
            (target / "physical-manifest.json").write_text(json.dumps(manifest))
            (target / "physical-stop-browser.json").write_text(json.dumps(report))
            selected_events = events
            if event_override is not None:
                selected_events = target / "native" / "physics" / "events.jsonl"
                selected_events.parent.mkdir(parents=True)
                selected_events.write_text("".join(json.dumps(event) + "\n"
                                                   for event in event_override))
                (selected_events.parent.parent / "cancellation-timing.jsonl").write_bytes(
                    (events.parent.parent / "cancellation-timing.jsonl").read_bytes()
                )
            result = subprocess.run([
                sys.executable, str(Path(__file__).with_name("judge_pc_physical_voice.py")),
                str(target), "--events", str(selected_events),
            ], capture_output=True, text=True)
            verdict = result.returncode == 0 and json.loads(
                (target / "physical-stop-judged.json").read_text()
            )["passed"]
            assert verdict == expected, f"Unexpected evidence verdict: {name}"
            checks.append({"case": name, "expected_pass": expected, "actual_pass": verdict})

    run("unaltered run retains independent verdict", lambda report: None, original_verdict)
    run("unlogged cancellation identity rejected", lambda report: report["rows"][0]
        ["stop_response"]["cancellation"].update(cancellation_id="unlogged"), False)
    run("inflated cleanup interval rejected", lambda report: report["rows"][0]
        ["stop_response"]["cancellation"].update(after_native_ack_ms=500), False)
    run("reordered cancellation timestamps rejected", lambda report: report["rows"][0]
        ["stop_response"]["cancellation"].update(native_ack_ns=0), False)
    run("late Stop rejected", lambda report: report["rows"][0].update(
        stop_done_epoch_s=report["rows"][0]["stop_done_epoch_s"] + 1), False)
    run("completed Proceed pickup rejected", lambda report: report["rows"][0]
        ["completed_resume"]["result"].update(task_id="unexpected-pickup"), False)
    changed_events = [json.loads(line) for line in events.read_text().splitlines() if line.strip()]
    start = next(event for event in changed_events if event["kind"] == "camera_inference_started"
                 and event.get("active_job") == original["rows"][0]["before_stop"]["job_id"])
    changed_events.append({"kind": "camera_failed", "time": start["time"] + .001,
                           "error": "Different vision model returned; refusing observation"})
    run("wrong camera-model workload rejected", lambda report: None, False, changed_events)
    (folder / "cancellation-evidence-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(f"PASS: {len(checks)} retained-run evidence checks; original records unchanged.")


if __name__ == "__main__":
    main()
