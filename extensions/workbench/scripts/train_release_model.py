"""Fit future physical outcomes with scene-held validation; no test labels."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from torch import nn

from physical_ai_lab.assistant.release_model import FEATURE_COUNT, FEATURE_VERSION, ReleaseModel

parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--fixture", type=Path, default=Path("fixtures/release_model_cases.json"))
parser.add_argument("--sensor-dropout", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
fixture = json.loads(args.fixture.read_text())
manifest = json.loads((args.dataset / "manifest.json").read_text())
assert manifest["limited_pilot"] is None
assert manifest.get("selected_split") is None
assert manifest["feature_version"] == FEATURE_VERSION
assert manifest["fixture_sha256"] == hashlib.sha256(args.fixture.read_bytes()).hexdigest()
assert (
    manifest["data_sha256"] == hashlib.sha256((args.dataset / "data.npz").read_bytes()).hexdigest()
)
with np.load(args.dataset / "data.npz", allow_pickle=False) as data:
    f, y, splits, episodes, legs, action_ids = [
        data[k].copy() for k in ["features", "labels", "splits", "episodes", "legs", "action_ids"]
    ]
assert f.shape[1] == FEATURE_COUNT and y.shape[1] == 5
assert not np.any(splits == "test")
train, validation = splits == "train", splits == "validation"
assert train.any() and validation.any()
assert not set(episodes[train]) & set(episodes[validation])
config, criteria = fixture["training"], fixture["criteria"]
dropout_hash = None
raw_train_rows = int(train.sum())
recipe = manifest.get("controller_recipe", "C3_legacy")
reoriented_train_legs = sum(
    leg.get("deliberately_reoriented", False)
    for record in manifest["records"]
    if record["case"]["split"] == "train"
    for leg in record["legs"]
    if leg.get("rows", 0) > 0
)
recipe_version = int(
    recipe in ("D2d_verified_camera_recovery", "D2e_training_reorientation_curriculum")
    and manifest.get("outcome_label_version") == 2
    and reoriented_train_legs > 0
)
if args.sensor_dropout:
    dropout = json.loads(args.sensor_dropout.read_text())
    assert dropout["base_fixture_sha256"] == manifest["fixture_sha256"]
    assert dropout["feature_indices"] == [3, 4, 5]
    assert dropout["masked_values"] == [0, 0, 0]
    assert dropout["copies_per_training_row"] == 1
    masked = f[train].copy()
    masked[:, [3, 4, 5]] = 0
    f, y = np.concatenate([f, masked]), np.concatenate([y, y[train]])
    splits = np.r_[splits, splits[train]]
    episodes = np.r_[episodes, episodes[train]]
    legs, action_ids = np.r_[legs, legs[train]], np.r_[action_ids, action_ids[train]]
    train, validation = splits == "train", splits == "validation"
    dropout_hash = hashlib.sha256(args.sensor_dropout.read_bytes()).hexdigest()
torch.set_num_threads(4)
mean = f[train].mean(0)
scale = np.maximum(f[train].std(0), 0.01)
x = torch.tensor((f[train] - mean) / scale, dtype=torch.float32)
target = torch.tensor(y[train] * 1000, dtype=torch.float32)
width = config["hidden_width"]
weights = {
    "mean": mean,
    "scale": scale,
    "feature_version": np.array(FEATURE_VERSION),
    "controller_recipe_version": np.array(recipe_version),
    "actions_xy_m": np.array(fixture["actions_xy_m"]),
    "max_feature": np.array(criteria["guard_max_normalized_feature"]),
    "max_xy_std_m": np.array(criteria["guard_max_ensemble_xy_std_m"]),
}
began = perf_counter()
for member, seed in enumerate(config["seeds"]):
    torch.manual_seed(seed)
    model = nn.Sequential(
        nn.Linear(FEATURE_COUNT, width),
        nn.ReLU(),
        nn.Linear(width, width),
        nn.ReLU(),
        nn.Linear(width, 5),
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
    for _ in range(config["epochs"]):
        for batch in torch.randperm(len(x)).split(config["batch_size"]):
            optimizer.zero_grad()
            loss = (model(x[batch]) - target[batch]).square().mean()
            loss.backward()
            optimizer.step()
    for i, layer in enumerate([model[0], model[2], model[4]]):
        weights[f"weight_{member}_{i}"] = layer.weight.detach().numpy()
        weights[f"bias_{member}_{i}"] = layer.bias.detach().numpy()
# Two simpler learned baselines use exactly the same training targets/episodes.
design = np.c_[x.numpy(), np.ones(len(x))]
penalty = np.eye(design.shape[1]) * 0.01
penalty[-1, -1] = 1e-6
weights["linear"] = np.linalg.solve(design.T @ design + penalty, design.T @ target.numpy())
weights["constant"] = np.array([y[train & (f[:, i] == 1)].mean(0) * 1000 for i in range(3)])
elapsed = perf_counter() - began
np.savez_compressed(args.output / "model.npz", **weights)
metadata = {
    "fixture_sha256": manifest["fixture_sha256"],
    "dataset_sha256": manifest["data_sha256"],
    "model_sha256": hashlib.sha256((args.output / "model.npz").read_bytes()).hexdigest(),
    "config": config,
    "feature_version": FEATURE_VERSION,
    "controller_recipe": recipe,
    "controller_recipe_version": recipe_version,
    "outcome_label_version": manifest.get("outcome_label_version", 1),
    "reoriented_training_legs": reoriented_train_legs,
    "features": FEATURE_COUNT,
    "train_rows": int(train.sum()),
    "original_train_rows": raw_train_rows,
    "sensor_dropout_sha256": dropout_hash,
    "validation_rows": int(validation.sum()),
    "train_episodes": len(set(episodes[train])),
    "validation_episodes": len(set(episodes[validation])),
    "training_s": elapsed,
    "torch_version": torch.__version__,
    "device": "cpu",
    "parameter_count_per_member": sum(p.numel() for p in model.parameters()),
    "linear_ridge_penalty": 0.01,
    "scope": "Future release outcome, not current state estimation",
}
(args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
vf, vy = f[validation], y[validation].copy()
ve, vl, va = episodes[validation], legs[validation], action_ids[validation]
vy[:, :2] += vf[:, -2:]
groups = sorted(set(zip(ve.tolist(), vl.tolist())))
zero = int(np.flatnonzero(np.linalg.norm(weights["actions_xy_m"], axis=1) == 0)[0])
summary = {"metadata": metadata, "models": {}, "validation_groups": len(groups)}
for kind in ["constant", "linear", "ensemble"]:
    runtime = ReleaseModel(args.output / "model.npz", kind=kind)
    predictions, std, valid = runtime.predict(vf)
    errors = np.linalg.norm(predictions[:, :2] - vy[:, :2], axis=1)
    matched_rigid = np.linalg.norm(vy[:, :2] - vf[:, -2:], axis=1)
    times = []
    selections = []
    for episode, leg in groups:
        indices = np.flatnonzero((ve == episode) & (vl == leg))
        assert len(indices) == 9 and set(va[indices]) == set(range(9))
        started = perf_counter()
        pred, uncertainty, covered = runtime.predict(vf[indices])
        elapsed_ms = (perf_counter() - started) * 1000
        eligible = (
            covered
            & (np.linalg.norm(pred[:, :2], axis=1) < 0.035)
            & (pred[:, 2] >= 0.01)
            & (pred[:, 2] < 0.04)
            & (pred[:, 3] < 0.03)
            & (pred[:, 4] < 0.004)
        )
        chosen = (
            int(np.argmin(np.where(eligible, np.linalg.norm(pred[:, :2], axis=1), np.inf)))
            if eligible.any()
            else None
        )
        zero_row = indices[np.flatnonzero(va[indices] == zero)[0]]
        selections.append(
            {
                "episode": episode,
                "leg": leg,
                "chosen_action": None if chosen is None else int(va[indices[chosen]]),
                "zero_error_m": float(np.linalg.norm(vy[zero_row, :2])),
                "chosen_error_m": None
                if chosen is None
                else float(np.linalg.norm(vy[indices[chosen], :2])),
                "chosen_future": None if chosen is None else vy[indices[chosen]].tolist(),
                "predicted_future": None if chosen is None else pred[chosen].tolist(),
            }
        )
        times.append(elapsed_ms)
    covered_errors = errors[valid]
    covered_rigid = matched_rigid[valid]
    usable = [s for s in selections if s["chosen_error_m"] is not None]
    gains = [s["zero_error_m"] - s["chosen_error_m"] for s in usable]
    result = {
        "rows": len(errors),
        "withheld_rows": int((~valid).sum()),
        "xy_rmse_m": float(np.sqrt(np.mean(covered_errors**2))) if len(covered_errors) else None,
        "xy_p95_m": float(np.quantile(covered_errors, 0.95)) if len(covered_errors) else None,
        "rigid_xy_rmse_on_coverage_m": float(np.sqrt(np.mean(covered_rigid**2)))
        if len(covered_rigid)
        else None,
        "inference_batch9_ms": {
            "median": float(np.median(times)),
            "p95": float(np.quantile(times, 0.95)),
        },
        "selection_coverage": len(usable) / len(groups),
        "selection_mean_gain_m": float(np.mean(gains)) if gains else None,
        "selection_mean_error_m": float(np.mean([s["chosen_error_m"] for s in usable]))
        if usable
        else None,
        "selections": selections,
    }
    result["offline_gate_passed"] = bool(
        result["withheld_rows"] == 0
        and result["selection_coverage"] == 1
        and result["xy_p95_m"] < criteria["validation_position_p95_m"]
        and result["inference_batch9_ms"]["p95"] < criteria["inference_p95_ms"]
        and result["selection_mean_gain_m"] > 0
    )
    summary["models"][kind] = result
eligible_kinds = [k for k, r in summary["models"].items() if r["offline_gate_passed"]]
summary["selected_kind"] = (
    min(eligible_kinds, key=lambda k: summary["models"][k]["selection_mean_error_m"])
    if eligible_kinds
    else None
)
summary["scope"] = (
    "Validation branches from zero-action baseline states; "
    "not full-loop physical acceptance; test labels excluded"
)
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(
    json.dumps(
        {
            "metadata": metadata,
            "selected_kind": summary["selected_kind"],
            "models": {
                k: {n: v for n, v in r.items() if n != "selections"}
                for k, r in summary["models"].items()
            },
        },
        indent=2,
    )
)
