"""Normalize audited teacher targets using verified original checkpoint statistics."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("dataset", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--preparation", type=Path, required=True)
args = parser.parse_args()
assert not args.output.exists()
manifest = json.loads((args.dataset/"manifest.json").read_text())
targets = args.dataset/"targets-native-osc.npz"
assert hashlib.sha256(targets.read_bytes()).hexdigest() == manifest["target_sha256"]
preparation = json.loads((args.preparation/"preparation.json").read_text())
assert preparation["verified"]
assert preparation["revision"] == "6d0231af0e48c5985f1ff86908f4674b84bc049b"
stats_path = args.preparation/"checkpoint/dataset_statistics.json"
spec = next(s for s in preparation["verified_files"] if s["name"] == stats_path.name)
stats_digest = hashlib.sha256(stats_path.read_bytes()).hexdigest()
assert stats_digest == spec["local_sha256"]
stats = json.loads(stats_path.read_text())["libero_spatial_no_noops"]["action"]
low, high, mask = (np.asarray(stats[k]) for k in ("q01", "q99", "mask"))
assert mask.tolist() == [True]*6+[False] and np.all(high > low)
with np.load(targets, allow_pickle=False) as data:
    native = data["actions"].astype(np.float64)
assert native.shape == (len(manifest["windows"]), 8, 7) and np.isfinite(native).all()
assert np.isin(native[..., -1], [-1., 1.]).all()
publisher = native.copy()
publisher[..., -1] = (1-native[..., -1])/2
before_clip = np.where(mask, 2*(publisher-low)/(high-low+1e-8)-1, publisher)
normalized = np.where(mask, np.clip(before_clip, -1, 1), publisher)
decoded = np.where(mask, .5*(normalized+1)*(high-low)+low, normalized)
decoded[..., -1] = -np.sign(2*decoded[..., -1]-1)
clipped = mask & ((before_clip < -1) | (before_clip > 1))
assert np.max(np.abs(decoded-native)[~clipped]) < 1e-6
args.output.mkdir(parents=True, exist_ok=False)
np.savez(args.output/"targets-normalized.npz", actions=normalized.astype(np.float32))
(args.output/"dataset-statistics.json").write_bytes(stats_path.read_bytes())
(args.output/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
report = {"status": "Normalized labels only; no model training or qualification",
          "checkpoint_revision": preparation["revision"], "statistics_sha256": stats_digest,
          "dataset_manifest_sha256": hashlib.sha256(
              (args.dataset/"manifest.json").read_bytes()).hexdigest(),
          "normalization": "Publisher BOUNDS_Q99 with1e-8 denominator and masked clipping",
          "gripper": "Native+1closed/-1open maps to publisher0closed/1open; mask=False",
          "shape": list(normalized.shape),
          "clipped_values_by_dimension": clipped.sum(axis=(0, 1)).tolist(),
          "max_native_roundtrip_difference_by_dimension":
              np.abs(decoded-native).max(axis=(0, 1)).tolist()}
(args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report, indent=2))
