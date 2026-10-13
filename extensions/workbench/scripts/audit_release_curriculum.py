"""Check training-only curriculum exposure, replay integrity and unchanged validation data."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("dataset", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--baseline", type=Path, required=True)
parser.add_argument("--fixture", type=Path, default=Path("fixtures/release_model_cases.json"))
parser.add_argument(
    "--protocol", type=Path, default=Path("fixtures/release_reorientation_protocol.json")
)
args = parser.parse_args()
manifest = json.loads((args.dataset / "manifest.json").read_text())
fixture = json.loads(args.fixture.read_text())
protocol = json.loads(args.protocol.read_text())
assert manifest["limited_pilot"] is None
assert manifest["curriculum_sha256"] == hashlib.sha256(args.protocol.read_bytes()).hexdigest()
assert (
    manifest["data_sha256"] == hashlib.sha256((args.dataset / "data.npz").read_bytes()).hexdigest()
)
assert manifest["fixture_sha256"] == protocol["base_fixture_sha256"]
records = manifest["records"]
expected = {c["id"] for c in fixture["cases"] if c["split"] != "test"}
assert {r["case"]["id"] for r in records} == expected and len(records) == len(expected)
yaws = {
    c["id"]: protocol["preferred_body_yaws_rad"][i % 4]
    for i, c in enumerate(c for c in fixture["cases"] if c["split"] == "train")
}
states, rejected, turns, angles = 0, [], 0, []
for record in records:
    assert record["requested_body_yaw_rad"] == yaws.get(record["case"]["id"])
    for leg in record["legs"]:
        if not leg["rows"]:
            rejected.append(
                {"case": record["case"]["id"], "leg": leg["leg"], "status": leg["status"]}
            )
            continue
        states += 1
        assert leg["rows"] == 9
        assert leg["normal_continuation_max_state_error"] <= 1e-8
        assert leg["repeat_max_state_error"] <= 1e-8
        if record["case"]["split"] == "train":
            assert leg["release_plan"]["requested_body_yaw_rad"] == yaws[record["case"]["id"]]
            turns += int(leg["deliberately_reoriented"])
            angles.append(leg["release_plan"]["orientation_change_rad"])
        else:
            assert leg["release_plan"]["requested_body_yaw_rad"] is None
with (
    np.load(args.dataset / "data.npz", allow_pickle=False) as current,
    np.load(args.baseline / "data.npz", allow_pickle=False) as baseline,
):
    f, y = current["features"], current["labels"]
    assert f.shape == (manifest["rows"], 76) and y.shape == (manifest["rows"], 5)
    assert np.isfinite(f).all() and np.isfinite(y).all()
    assert not np.any(current["splits"] == "test")
    counts = {name: int(np.sum(current["splits"] == name)) for name in ("train", "validation")}
    assert not set(current["episodes"][current["splits"] == "train"]) & set(
        current["episodes"][current["splits"] == "validation"]
    )

    def validation_rows(data):
        return {
            (str(data["episodes"][i]), int(data["legs"][i]), int(data["action_ids"][i])): (
                data["features"][i],
                data["labels"][i],
            )
            for i in np.flatnonzero(data["splits"] == "validation")
        }

    old, new = validation_rows(baseline), validation_rows(current)
    assert set(old) == set(new)
    feature_error = max(float(np.max(np.abs(old[k][0] - new[k][0]))) for k in old)
    label_error = max(float(np.max(np.abs(old[k][1] - new[k][1]))) for k in old)
    assert feature_error <= 1e-8 and label_error <= 1e-8
report = {
    "passed": True,
    "scope": "Collection audit, not fitted-model or full-loop acceptance",
    "records": len(records),
    "release_states": states,
    "rows": manifest["rows"],
    "split_rows": counts,
    "training_reorientation_states": turns,
    "training_turns_over_0_035_rad": sum(a > 0.035 for a in angles),
    "all_normal_and_repeat_checks_passed": True,
    "validation_feature_max_error": feature_error,
    "validation_label_max_error": label_error,
    "rejected_legs": rejected,
    "dataset_sha256": manifest["data_sha256"],
    "curriculum_sha256": manifest["curriculum_sha256"],
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "rejected_legs"}, indent=2))
