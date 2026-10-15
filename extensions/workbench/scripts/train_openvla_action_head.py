"""Adapt only the existing action head from frozen features; no policy promotion."""

import argparse
import hashlib
import json
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from openvla_inference_utils import configuration, load_helpers, native_actions

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("features", type=Path)
parser.add_argument("targets", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--preparation", type=Path, required=True)
parser.add_argument("--dataset", type=Path, required=True)
args = parser.parse_args()
protocol_path = Path(__file__).resolve().parents[1]/"docs/action-head-adaptation-protocol.json"
protocol = json.loads(protocol_path.read_text())
cached = json.loads((args.features/"manifest.json").read_text())
target_report = json.loads((args.targets/"report.json").read_text())
assert cached["complete"] and cached["frozen"]
assert cached["dataset_manifest_sha256"] == target_report["dataset_manifest_sha256"]
assert hashlib.sha256((args.dataset/"manifest.json").read_bytes()).hexdigest() == (
    cached["dataset_manifest_sha256"])
assert cached["checkpoint_revision"] == protocol["base_revision"]
assert "no label clipping" in target_report["normalization"]
preparation = json.loads((args.preparation/"preparation.json").read_text())
assert preparation["verified"] and preparation["revision"] == protocol["base_revision"]
head_spec = next(s for s in preparation["verified_files"] if s["name"].startswith("action_head"))
head_digest = hashlib.sha256()
with (args.preparation/"checkpoint"/head_spec["name"]).open("rb") as stream:
    for block in iter(lambda: stream.read(8*1024*1024), b""):
        head_digest.update(block)
assert head_digest.hexdigest() == head_spec["local_sha256"]
assert torch.cuda.is_available() and torch.cuda.get_device_capability() == (12, 0)
args.output.mkdir(parents=True, exist_ok=False)
(args.output/"protocol.json").write_bytes(protocol_path.read_bytes())
(args.output/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
torch.manual_seed(protocol["optimizer"]["seed"])
torch.cuda.manual_seed_all(protocol["optimizer"]["seed"])
features = []
for entry in cached["entries"]:
    path = args.features/"features"/f"{entry['index']:05d}.pt"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
    feature = torch.load(path, map_location="cpu", weights_only=True)
    assert tuple(feature.shape) == tuple(cached["hidden_shape"]) and torch.isfinite(feature).all()
    features.append(feature)
x = torch.cat(features)
with np.load(args.targets/"targets-normalized.npz", allow_pickle=False) as data:
    y = torch.from_numpy(data["actions"].copy())
assert y.shape == (len(features), 8, 7) and torch.isfinite(y).all()
helpers, _, _ = load_helpers(args.source)
from prismatic.extern.hf.modeling_prismatic import OpenVLAForActionPrediction  # noqa: E402

stats_path = args.targets/"dataset-statistics.json"
assert hashlib.sha256(stats_path.read_bytes()).hexdigest() == target_report["statistics_sha256"]
stats = json.loads(stats_path.read_text())["libero_spatial_no_noops"]["action"]
decoded = OpenVLAForActionPrediction._unnormalize_actions(
    SimpleNamespace(get_action_stats=lambda _: stats), y.numpy(), "libero_spatial_no_noops")
with np.load(args.dataset/"targets-native-osc.npz", allow_pickle=False) as data:
    native_targets = data["actions"]
assert np.allclose(np.stack([native_actions(a) for a in decoded]), native_targets,
                   atol=1e-6, rtol=0), "Original publisher decoder must recover all native labels"
cfg = configuration(args.preparation/"checkpoint")
head = helpers.get_action_head(cfg, x.shape[-1]).float().train().requires_grad_(True)
optimizer_cfg = protocol["optimizer"]
optimizer = torch.optim.AdamW(head.parameters(), lr=optimizer_cfg["learning_rate"],
                             weight_decay=optimizer_cfg["weight_decay"])
generator = torch.Generator().manual_seed(optimizer_cfg["seed"])
trace, checkpoints = [], []
started = time.monotonic()


def evaluate():
    total = 0.
    head.eval()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        for start in range(0, len(x), 8):
            prediction = head.predict_action(x[start:start+8].cuda())
            total += float(torch.nn.functional.l1_loss(
                prediction.float(), y[start:start+8].cuda(), reduction="sum"))
    head.train()
    return total/y.numel()


def save(step):
    loss = evaluate()
    path = args.output/f"action-head-step{step:04d}.pt"
    torch.save({k: v.detach().cpu() for k, v in head.state_dict().items()}, path)
    checkpoints.append({"step": step, "training_l1": loss,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    print(json.dumps(checkpoints[-1]), flush=True)


save(0)
for step in range(1, optimizer_cfg["steps"]+1):
    indices = torch.randint(len(x), (optimizer_cfg["batch_size"],), generator=generator)
    optimizer.zero_grad(set_to_none=True)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        prediction = head.predict_action(x[indices].cuda())
        loss = torch.nn.functional.l1_loss(prediction.float(), y[indices].cuda())
    assert torch.isfinite(loss)
    loss.backward()
    grad_norm = torch.nn.utils.clip_grad_norm_(
        head.parameters(), optimizer_cfg["gradient_clip_norm"])
    assert torch.isfinite(grad_norm)
    optimizer.step()
    trace.append({"step": step, "batch_l1": float(loss.detach()),
                  "gradient_norm": float(grad_norm)})
    if step in protocol["checkpoints"]:
        save(step)
report = {"status": "Head-only pilot trained; no physical qualification or promotion",
          "base_revision": cached["checkpoint_revision"], "examples": len(x),
          "trainable_parameters": sum(p.numel() for p in head.parameters()),
          "frozen_feature_manifest_sha256": hashlib.sha256(
              (args.features/"manifest.json").read_bytes()).hexdigest(),
          "checkpoints": checkpoints, "elapsed_s": time.monotonic()-started,
          "trace": trace}
(args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
