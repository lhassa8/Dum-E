"""Reject altered evidence using the retained real browser/physics run."""

import argparse
import contextlib
import copy
import io
import json
import tempfile
from pathlib import Path

from judge_physical_voice_stop import judge


def check(folder, native_log):
    original = json.loads((folder / "physical-stop-browser.json").read_text())
    manifest = json.loads((folder / "physical-manifest.json").read_text())
    checks = []

    def run(name, alter, expected, native_override=None):
        with tempfile.TemporaryDirectory(prefix="dume-stop-judge-") as location:
            target = Path(location)
            for item in [manifest["question"], *manifest["cases"]]:
                (target / item["file"]).symlink_to(folder / item["file"])
            data = copy.deepcopy(original)
            altered_manifest = copy.deepcopy(manifest)
            alter(data, altered_manifest)
            (target / "physical-manifest.json").write_text(json.dumps(altered_manifest))
            (target / "physical-stop-browser.json").write_text(json.dumps(data))
            selected_log = native_log
            if native_override is not None:
                selected_log = target / "native-events.jsonl"
                selected_log.write_text("".join(json.dumps(e) + "\n" for e in native_override))
            with contextlib.redirect_stdout(io.StringIO()):
                try:
                    verdict = judge(target, selected_log)
                except (ValueError, KeyError, IndexError):
                    verdict = False
            if verdict != expected:
                raise AssertionError(f"Unexpected judge verdict: {name}")
            checks.append({"case": name, "expected_pass": expected, "actual_pass": verdict})

    run("unaltered real run passes", lambda data, manifest: None, True)
    run("missing trial rejected", lambda data, manifest: data["rows"].pop(), False)
    run(
        "duplicate trial rejected",
        lambda data, manifest: data["rows"].append(data["rows"][0]),
        False,
    )
    run(
        "false timing reference rejected",
        lambda data, manifest: data["rows"][0].update(
            reference_last_voiced_epoch_s=data["rows"][0]["reference_last_voiced_epoch_s"] + 1
        ),
        False,
    )
    run(
        "frozen protocol mismatch rejected",
        lambda data, manifest: manifest.update(protocol_sha256="0" * 64),
        False,
    )
    run(
        "embedded gate alteration rejected",
        lambda data, manifest: manifest["protocol"]["criteria"].update(
            maximum_end_to_native_stop_ms=10000
        ),
        False,
    )
    run(
        "retained voiced boundary alteration rejected",
        lambda data, manifest: manifest["cases"][0].update(last_clean_voiced_ms=1440),
        False,
    )
    run(
        "no physical motion rejected",
        lambda data, manifest: data["rows"][0]["first_held"].update(
            robot_joints=data["rows"][0]["before_stop"]["robot_joints"]
        ),
        False,
    )
    run(
        "opened gripper rejected",
        lambda data, manifest: data["rows"][0]["after_settling"].update(gripper_command=255),
        False,
    )
    run(
        "dropped tool rejected",
        lambda data, manifest: data["rows"][0]["after_settling"]["objects"].update(
            screwdriver=[0, 0, 0.08]
        ),
        False,
    )
    run(
        "stale dialogue accepted rejected",
        lambda data, manifest: data["rows"][0]["question_result"].update(
            mode="conversation", accepted=True
        ),
        False,
    )
    run(
        "negated Stop transcript rejected",
        lambda data, manifest: data["rows"][0]["recognized"][1].update(text="Don't stop."),
        False,
    )
    run(
        "unrelated tool displacement rejected",
        lambda data, manifest: data["rows"][0]["after_settling"]["objects"].update(
            wrench=[1, 1, 1]
        ),
        False,
    )
    run(
        "unsettled arm rejected",
        lambda data, manifest: data["rows"][0]["after_settling"].update(robot_joints=[0] * 7),
        False,
    )
    late_events = [json.loads(line) for line in native_log.read_text().splitlines() if line.strip()]
    first = original["rows"][0]
    for event in late_events:
        if event["kind"] == "stop_requested" and (
            first["stop_post_epoch_s"] - 0.05 <= event["time"] <= first["stop_done_epoch_s"] + 0.05
        ):
            event["time"] += 1.2
    run(
        "late native Stop rejected",
        lambda data, manifest: data["rows"][0].update(
            stop_post_epoch_s=first["stop_post_epoch_s"] + 1.2,
            stop_done_epoch_s=first["stop_done_epoch_s"] + 1.2,
        ),
        False,
        late_events,
    )
    (folder / "judge-mutation-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(f"PASS: {len(checks)} retained-run judge checks; original evidence unchanged.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--native-log", type=Path, required=True)
    args = parser.parse_args()
    check(args.folder.resolve(), args.native_log.resolve())
