"""Cache frozen pretrained action-token features from native pre-action observations."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from openvla_inference_utils import configuration, load_helpers, native_actions, observation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("dataset", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--preparation", type=Path, required=True)
args = parser.parse_args()
dataset_path = args.dataset/"manifest.json"
dataset = json.loads(dataset_path.read_text())
preparation = json.loads((args.preparation/"preparation.json").read_text())
assert preparation["verified"] and torch.cuda.is_available()
assert torch.cuda.get_device_capability() == (12, 0)
assert {s["task_id"] for s in dataset["episode_sources"]} == {0, 1, 2}
assert not dataset["padding"] and not dataset["crosses_explicit_pause"]
args.output.mkdir(parents=True, exist_ok=False)
for path in (Path(__file__), Path(__file__).with_name("openvla_inference_utils.py")):
    (args.output/path.name).write_bytes(path.read_bytes())
checkpoint = args.preparation/"checkpoint"
for spec in preparation["verified_files"]:
    path = checkpoint/spec["name"]
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            digest.update(block)
    assert path.stat().st_size == spec["bytes"] and digest.hexdigest() == spec["local_sha256"]
helpers, geometry, provenance = load_helpers(args.source)
from prismatic.extern.hf.configuration_prismatic import OpenVLAConfig  # noqa: E402
from prismatic.extern.hf.modeling_prismatic import OpenVLAForActionPrediction  # noqa: E402
from prismatic.extern.hf.processing_prismatic import (  # noqa: E402
    PrismaticImageProcessor,
    PrismaticProcessor,
)
from prismatic.vla.constants import PROPRIO_DIM  # noqa: E402
from transformers import AutoConfig, AutoImageProcessor, AutoProcessor  # noqa: E402

AutoConfig.register("openvla", OpenVLAConfig)
AutoImageProcessor.register(OpenVLAConfig, PrismaticImageProcessor)
AutoProcessor.register(OpenVLAConfig, PrismaticProcessor)
cfg = configuration(checkpoint)
started = time.monotonic()
config = OpenVLAConfig.from_pretrained(checkpoint, local_files_only=True)
model = OpenVLAForActionPrediction.from_pretrained(
    checkpoint, config=config, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True,
    local_files_only=True).to("cuda:0").eval().requires_grad_(False)
model.vision_backbone.set_num_images_in_input(2)
model.norm_stats = json.loads((checkpoint/"dataset_statistics.json").read_text())
processor = PrismaticProcessor.from_pretrained(checkpoint, local_files_only=True,
                                               trust_remote_code=False)
head = helpers.get_action_head(cfg, model.llm_dim).eval().requires_grad_(False)
proprio = helpers.get_proprio_projector(cfg, model.llm_dim, PROPRIO_DIM)
proprio.eval().requires_grad_(False)
torch.cuda.synchronize()
load_s = time.monotonic()-started
captured = {}
original = model.predict_action


def capture(*positional, **keywords):
    result = original(*positional, **keywords)
    captured["features"] = result[1]
    return result


model.predict_action = capture
entries, predictions = [], []
(args.output/"features").mkdir()
for index, window in enumerate(dataset["windows"]):
    path = Path(window["observation"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == window["observation_sha256"]
    with np.load(path, allow_pickle=False) as data:
        raw = dict(data)
    assert set(raw) == {"agentview_image", "robot0_eye_in_hand_image", "robot0_eef_pos",
                        "robot0_eef_quat", "robot0_gripper_qpos"}
    torch.cuda.synchronize()
    tick = time.monotonic()
    actions = np.asarray(helpers.get_vla_action(
        cfg, model, processor, observation(raw, geometry), window["task_prompt"],
        action_head=head, proprio_projector=proprio))
    hidden = captured.pop("features")
    assert hidden.shape == (1, 56, model.llm_dim) and torch.isfinite(hidden).all()
    with torch.inference_mode():
        reconstructed = head.predict_action(hidden).reshape(8, 7).float().cpu().numpy()
    decoded = model._unnormalize_actions(reconstructed, cfg.unnorm_key)
    assert np.array_equal(native_actions(decoded), native_actions(actions))
    torch.cuda.synchronize()
    elapsed = (time.monotonic()-tick)*1000
    feature_path = args.output/"features"/f"{index:05d}.pt"
    torch.save(hidden.detach().cpu().contiguous(), feature_path)
    entries.append({"index": index, "sha256": hashlib.sha256(feature_path.read_bytes()).hexdigest(),
                    "inference_ms": elapsed})
    predictions.append(native_actions(actions))
    if index == 0 or (index+1) % 50 == 0:
        print(json.dumps({"cached": index+1, "total": len(dataset["windows"])}), flush=True)
np.savez(args.output/"base-native-actions.npz", actions=np.asarray(predictions))
metadata = {**provenance, "checkpoint_revision": preparation["revision"], "load_s": load_s,
            "dataset_manifest_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
            "device": str(next(model.parameters()).device), "dtype": str(hidden.dtype),
            "hidden_shape": list(hidden.shape), "feature_head_identity_checks": len(entries),
            "frozen": True, "trained": False, "complete": True, "entries": entries}
(args.output/"manifest.json").write_text(json.dumps(metadata, indent=2)+"\n")
print(json.dumps({"complete": True, "features": len(entries), "load_s": load_s}), flush=True)
