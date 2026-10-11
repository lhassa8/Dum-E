"""Train a small carry-position estimator and compare episode-held validation.

Torch is used only for fitting; exported inference is pure NumPy. The untouched
physical test split is not read. Targets are simulator labels, not actor inputs.
"""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import torch
from torch import nn

from physical_ai_lab.assistant.carry_model import FEATURE_VERSION, CarryModel

parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--fixture", type=Path, default=Path("fixtures/carry_model_cases.json"))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
fixture = json.loads(args.fixture.read_text())
manifest = json.loads((args.dataset / "manifest.json").read_text())
assert manifest["fixture_sha256"] == hashlib.sha256(args.fixture.read_bytes()).hexdigest()
assert (
    manifest["data_sha256"] == hashlib.sha256((args.dataset / "data.npz").read_bytes()).hexdigest()
)
config = fixture["training"]
torch.manual_seed(config["seed"])
torch.set_num_threads(4)
with np.load(args.dataset / "data.npz", allow_pickle=False) as d:
    features, labels, splits, episodes = [
        d[k].copy() for k in ("features", "labels", "splits", "episodes")
    ]
train, val = splits == "train", splits == "validation"
assert not set(episodes[train]) & set(episodes[val])
assert not np.any(splits == "test")
mean = features[train].mean(0)
scale = np.maximum(features[train].std(0), 0.01)
x = torch.tensor((features[train] - mean) / scale, dtype=torch.float32)
y = torch.tensor(labels[train] * 1000, dtype=torch.float32)
width = config["hidden_width"]
model = nn.Sequential(
    nn.Linear(x.shape[1], width), nn.ReLU(), nn.Linear(width, width), nn.ReLU(), nn.Linear(width, 3)
)
optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
start = perf_counter()
for _ in range(config["epochs"]):
    for batch in torch.randperm(len(x)).split(config["batch_size"]):
        optimizer.zero_grad()
        loss = (model(x[batch]) - y[batch]).square().mean()
        loss.backward()
        optimizer.step()
elapsed = perf_counter() - start
weights = {"mean": mean, "scale": scale, "feature_version": np.array(FEATURE_VERSION)}
for i, layer in enumerate([model[0], model[2], model[4]]):
    weights[f"weight_{i}"] = layer.weight.detach().numpy()
    weights[f"bias_{i}"] = layer.bias.detach().numpy()
np.savez_compressed(args.output / "model.npz", **weights)
metadata = {
    "fixture_sha256": manifest["fixture_sha256"],
    "dataset_sha256": manifest["data_sha256"],
    "model_sha256": hashlib.sha256((args.output / "model.npz").read_bytes()).hexdigest(),
    "config": config,
    "additional_training_fixture_sha256": manifest.get("additional_training_fixture_sha256"),
    "feature_version": FEATURE_VERSION,
    "train_rows": int(train.sum()),
    "validation_rows": int(val.sum()),
    "train_episodes": len(set(episodes[train])),
    "validation_episodes": len(set(episodes[val])),
    "training_s": elapsed,
    "torch_version": torch.__version__,
    "device": "cpu",
    "parameter_count": sum(p.numel() for p in model.parameters()),
}
# Preserve fit provenance even if a later evaluation fails.
(args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
runtime = CarryModel(args.output / "model.npz")
rows, timings = [], []
for i in np.flatnonzero(val):
    started = perf_counter()
    try:
        prediction = runtime.predict(features[i])
        refusal = None
    except ValueError as error:
        prediction, refusal = None, str(error)
    timings.append((perf_counter() - started) * 1000)
    rows.append(
        {
            "episode": str(episodes[i]),
            "rigid_error_m": float(np.linalg.norm(labels[i])),
            "learned_error_m": None
            if prediction is None
            else float(np.linalg.norm(prediction - labels[i])),
            "actual_residual_local_m": labels[i].tolist(),
            "predicted_residual_local_m": None if prediction is None else prediction.tolist(),
            "refusal": refusal,
        }
    )
summary = {
    "scope": (
        "Episode-held validation of hidden carried-position estimate; "
        "not next-state prediction or physical acceptance"
    ),
    **metadata,
    "validation_rows_evidence": rows,
}
for kind in ["rigid", "learned"]:
    errors = np.array([r[f"{kind}_error_m"] for r in rows if r[f"{kind}_error_m"] is not None])
    summary[kind] = {
        "rows": len(errors),
        "rmse_m": float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
        "p95_m": float(np.quantile(errors, 0.95)) if len(errors) else None,
        "max_m": float(errors.max()) if len(errors) else None,
    }
matched = np.array([r["rigid_error_m"] for r in rows if r["learned_error_m"] is not None])
summary["rigid_on_learned_coverage"] = {
    "rows": len(matched),
    "rmse_m": float(np.sqrt(np.mean(matched**2))) if len(matched) else None,
    "p95_m": float(np.quantile(matched, 0.95)) if len(matched) else None,
    "max_m": float(matched.max()) if len(matched) else None,
}
summary["inference_ms"] = {
    "median": float(np.median(timings)),
    "p95": float(np.quantile(timings, 0.95)),
}
summary["withheld_rows"] = sum(r["refusal"] is not None for r in rows)
summary["offline_gate_passed"] = (
    bool(rows)
    and summary["withheld_rows"] == 0
    and summary["learned"]["p95_m"] < fixture["criteria"]["validation_position_p95_m"]
    and summary["learned"]["rmse_m"] < summary["rigid"]["rmse_m"]
    and summary["inference_ms"]["p95"] < fixture["criteria"]["inference_p95_ms"]
)
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "validation_rows_evidence"}, indent=2))
