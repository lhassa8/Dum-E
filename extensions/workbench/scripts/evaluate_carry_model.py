"""Evaluate an already frozen NumPy checkpoint without another training run."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from physical_ai_lab.assistant.carry_model import CarryModel

parser = argparse.ArgumentParser()
parser.add_argument("dataset", type=Path)
parser.add_argument("model", type=Path)
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
runtime = CarryModel(args.model)
rows, times = [], []
with np.load(args.dataset / "data.npz", allow_pickle=False) as data:
    for i in np.flatnonzero(data["splits"] == "validation"):
        began = perf_counter()
        try:
            prediction = runtime.predict(data["features"][i])
            refusal = None
        except ValueError as error:
            prediction, refusal = None, str(error)
        times.append((perf_counter() - began) * 1000)
        truth = data["labels"][i]  # Only the evaluator sees the labeled residual.
        rows.append(
            {
                "episode": str(data["episodes"][i]),
                "rigid_error_m": float(np.linalg.norm(truth)),
                "learned_error_m": None
                if prediction is None
                else float(np.linalg.norm(prediction - truth)),
                "actual_residual_local_m": truth.tolist(),
                "predicted_residual_local_m": None if prediction is None else prediction.tolist(),
                "refusal": refusal,
            }
        )
summary = {
    "scope": "Frozen checkpoint re-evaluation; no retraining; episode-held validation",
    "fixture_sha256": manifest["fixture_sha256"],
    "model_sha256": hashlib.sha256(args.model.read_bytes()).hexdigest(),
    "dataset_sha256": hashlib.sha256((args.dataset / "data.npz").read_bytes()).hexdigest(),
    "rows": len(rows),
    "withheld_rows": sum(r["refusal"] is not None for r in rows),
    "evidence": rows,
    "inference_ms": {"median": float(np.median(times)), "p95": float(np.quantile(times, 0.95))},
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
summary["offline_gate_passed"] = (
    bool(rows)
    and summary["withheld_rows"] == 0
    and summary["learned"]["p95_m"] < fixture["criteria"]["validation_position_p95_m"]
    and summary["learned"]["rmse_m"] < summary["rigid"]["rmse_m"]
    and summary["inference_ms"]["p95"] < fixture["criteria"]["inference_p95_ms"]
)
(args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "evidence"}, indent=2))
