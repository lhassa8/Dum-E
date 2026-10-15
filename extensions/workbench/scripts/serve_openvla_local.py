"""Local warmed OpenVLA-OFT HTTP inference boundary; no simulator or hardware access."""

import argparse
import copy
import hashlib
import io
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import numpy as np
import torch
from openvla_inference_utils import configuration, load_helpers, native_actions, observation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--source", type=Path, required=True)
parser.add_argument("--preparation", type=Path, required=True)
parser.add_argument("--observation", type=Path, required=True)
parser.add_argument("--port", type=int, default=8900)
parser.add_argument("--adaptation", type=Path,
                    help="Local pilot directory with saved step50/200 heads")
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
head_spec = next(s for s in manifest["verified_files"] if s["name"].startswith("action_head"))
heads = {"original": head}
head_identity = {"original": {"step": 0, "sha256": head_spec["local_sha256"]}}
if args.adaptation:
    adaptation = json.loads((args.adaptation/"report.json").read_text())
    assert adaptation["base_revision"] == manifest["revision"]
    for step in (50, 200):
        spec = next(s for s in adaptation["checkpoints"] if s["step"] == step)
        path = args.adaptation/f"action-head-step{step:04d}.pt"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == spec["sha256"]
        candidate = copy.deepcopy(head)
        candidate.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
        heads[f"step{step}"] = candidate.eval().requires_grad_(False)
        head_identity[f"step{step}"] = {"step": step, "sha256": spec["sha256"]}
torch.cuda.synchronize()
load_s = time.monotonic()-started
with np.load(args.observation, allow_pickle=False) as data:
    raw = dict(data)
prompt = "pick up the black bowl between the plate and the ramekin and place it on the plate"
def predict(raw_observation, task_prompt, head_name="original"):
    inputs = observation(raw_observation, geometry)
    torch.cuda.synchronize()
    started = time.monotonic()
    actions = np.asarray(helpers.get_vla_action(cfg, model, processor, inputs, task_prompt,
                                              action_head=heads[head_name],
                                              proprio_projector=proprio))
    converted = native_actions(actions)
    torch.cuda.synchronize()
    return converted, (time.monotonic()-started)*1000


warm_actions, warm_ms = predict(raw, prompt)
warmup_by_head = {"original": warm_ms}
for name in heads:
    if name != "original":
        _, warmup_by_head[name] = predict(raw, prompt, name)
metadata = {**provenance, "checkpoint_revision": manifest["revision"],
            "heads": head_identity, "warmup_ms_by_head": warmup_by_head,
            "actor_sha256": hashlib.sha256(actor_path.read_bytes()).hexdigest(),
            "bootstrap_sha256": hashlib.sha256(bootstrap_path.read_bytes()).hexdigest(),
            "preparation_sha256": hashlib.sha256((args.preparation/"preparation.json").read_bytes()
                                                  ).hexdigest(),
            "device": str(next(model.parameters()).device),
            "dtype": str(next(model.parameters()).dtype), "torch": torch.__version__,
            "cuda_build": torch.version.cuda, "load_s": load_s, "warmup_ms": warm_ms,
            "warmup_complete": True, "discarded_warmup_actions": 8,
            "action_contract": "8x7 native LIBERO OSC inputs; publisher gripper conversion",
            "scope": "Deterministic local policy; no voice, simulator or hardware access"}
(args.output/"metadata.json").write_text(json.dumps(metadata, indent=2)+"\n")
print(json.dumps(metadata), flush=True)
trace = (args.output/"inference.jsonl").open("w", buffering=1)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *unused):
        pass

    def reply(self, value, status=200):
        data = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.reply(metadata if self.path == "/metadata" else {"error": "Unknown route"},
                   200 if self.path == "/metadata" else 404)

    def do_POST(self):
        if self.path != "/infer":
            return self.reply({"error": "Unknown route"}, 404)
        try:
            size = int(self.headers["Content-Length"])
            assert 0 < size <= 2*1024*1024
            task_prompt = self.headers["X-Task-Prompt"]
            request_id = int(self.headers["X-Request-Id"])
            head_name = self.headers.get("X-Action-Head", "original")
            assert head_name in heads
            assert task_prompt and len(task_prompt) <= 256
            encoded = self.rfile.read(size)
            assert len(encoded) == size
            with np.load(io.BytesIO(encoded), allow_pickle=False) as data:
                raw_request = dict(data)
            for key in ("agentview_image", "robot0_eye_in_hand_image"):
                assert raw_request[key].shape == (256, 256, 3)
                assert raw_request[key].dtype == np.uint8
            actions, elapsed = predict(raw_request, task_prompt, head_name)
            result = {"request_id": request_id, "actions": actions.tolist(), "server_ms": elapsed,
                      "head": head_name, "head_sha256": head_identity[head_name]["sha256"],
                      "observation_sha256": hashlib.sha256(encoded).hexdigest()}
            trace.write(json.dumps({**result, "prompt": task_prompt})+"\n")
            self.reply(result)
        except Exception as caught:
            trace.write(json.dumps({"error": repr(caught)})+"\n")
            self.reply({"error": repr(caught)}, 500)


server = HTTPServer(("127.0.0.1", args.port), Handler)
print(f"Warmed local OpenVLA boundary http://127.0.0.1:{args.port}", flush=True)
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    trace.close()
