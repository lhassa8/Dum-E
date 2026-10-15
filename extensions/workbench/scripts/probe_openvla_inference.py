"""Real local BF16 OpenVLA-OFT checkpoint inference; outputs never reach a simulator."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
from openvla_inference_utils import configuration, load_helpers, native_actions, observation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--preparation", type=Path, required=True)
parser.add_argument("--observation", type=Path, required=True)
args = parser.parse_args()
manifest = json.loads((args.preparation/"preparation.json").read_text())
assert manifest.get("verified") and torch.cuda.is_available()
assert torch.cuda.get_device_capability() == (12, 0)
args.output.mkdir(parents=True, exist_ok=False)
actor_path = Path(__file__)
bootstrap_path = actor_path.with_name("openvla_inference_utils.py")
for path in (actor_path, bootstrap_path):
    (args.output/path.name).write_bytes(path.read_bytes())
checkpoint = args.preparation/"checkpoint"
for spec in manifest["verified_files"]:
    path = checkpoint/spec["name"]
    assert path.stat().st_size == spec["bytes"]
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            digest.update(block)
    assert digest.hexdigest() == spec["local_sha256"]
helpers, geometry, provenance = load_helpers(args.source)
from prismatic.extern.hf.configuration_prismatic import OpenVLAConfig  # noqa: E402
from prismatic.extern.hf.modeling_prismatic import OpenVLAForActionPrediction  # noqa: E402
from prismatic.extern.hf.processing_prismatic import (  # noqa: E402
    PrismaticImageProcessor,
    PrismaticProcessor,
)
from prismatic.vla.constants import ACTION_DIM, NUM_ACTIONS_CHUNK, PROPRIO_DIM  # noqa: E402
from transformers import AutoConfig, AutoImageProcessor, AutoProcessor  # noqa: E402

assert (ACTION_DIM, NUM_ACTIONS_CHUNK, PROPRIO_DIM) == (7, 8, 8)
AutoConfig.register("openvla", OpenVLAConfig)
AutoImageProcessor.register(OpenVLAConfig, PrismaticImageProcessor)
AutoProcessor.register(OpenVLAConfig, PrismaticProcessor)
cfg = configuration(checkpoint)
started = time.monotonic()
config = OpenVLAConfig.from_pretrained(checkpoint, local_files_only=True)
model = OpenVLAForActionPrediction.from_pretrained(
    checkpoint, config=config, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True,
    local_files_only=True).to("cuda:0").eval()
model.vision_backbone.set_num_images_in_input(2)
model.norm_stats = json.loads((checkpoint/"dataset_statistics.json").read_text())
assert cfg.unnorm_key in model.norm_stats
processor = PrismaticProcessor.from_pretrained(checkpoint, local_files_only=True,
                                               trust_remote_code=False)
head = helpers.get_action_head(cfg, model.llm_dim)
proprio = helpers.get_proprio_projector(cfg, model.llm_dim, PROPRIO_DIM)
torch.cuda.synchronize()
load_s = time.monotonic()-started
with np.load(args.observation, allow_pickle=False) as data:
    raw = dict(data)
prompt = "pick up the black bowl between the plate and the ramekin and place it on the plate"
outputs, timings = [], []
for index in range(6):
    inputs = observation(raw, geometry)
    torch.cuda.synchronize()
    started = time.monotonic()
    actions = np.asarray(helpers.get_vla_action(cfg, model, processor, inputs, prompt,
                                              action_head=head, proprio_projector=proprio))
    torch.cuda.synchronize()
    elapsed = (time.monotonic()-started)*1000
    converted = native_actions(actions)
    outputs.append(converted)
    timings.append(elapsed)
    print(json.dumps({"call": index, "ms": elapsed, "shape": list(actions.shape)}), flush=True)
np.savez(args.output/"actions.npz", actions=np.stack(outputs))
report = {"passed": True, **provenance, "checkpoint_revision": manifest["revision"],
          "actor_sha256": hashlib.sha256(actor_path.read_bytes()).hexdigest(),
          "bootstrap_sha256": hashlib.sha256(bootstrap_path.read_bytes()).hexdigest(),
          "preparation_sha256": hashlib.sha256((args.preparation/"preparation.json").read_bytes()
                                               ).hexdigest(),
          "observation_sha256": hashlib.sha256(args.observation.read_bytes()).hexdigest(),
          "device": str(next(model.parameters()).device),
          "dtype": str(next(model.parameters()).dtype),
          "torch": torch.__version__, "cuda_build": torch.version.cuda,
          "load_s": load_s, "discarded_warmup_ms": timings[0], "warmed_calls_ms": timings[1:],
          "repeat_max_action_difference": float(np.max(np.abs(np.stack(outputs[1:])-outputs[1]))),
          "action_contract": "8x7 LIBERO OSC inputs; publisher gripper sign conversion",
          "scope": "Six real GPU calls on one saved observation; no closed-loop, voice or hardware"}
assert report["device"] == "cuda:0" and report["dtype"] == "torch.bfloat16"
(args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report))
