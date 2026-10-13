"""Serve the official verified JAX checkpoint on loopback only; no robot actuation."""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--checkpoint", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--port", type=int, default=8900)
parser.add_argument(
    "--warmup", type=Path, help="Actual preprocessed observation NPZ; discard actions"
)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
source = args.openpi.resolve()
checkpoint = args.checkpoint.resolve()
revision = subprocess.check_output(
    ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
).strip()
if revision != "215abfb217dbac7d5f1273282331b9b1866c0479":
    raise RuntimeError("Unexpected OpenPi revision; requalify before serving")
if any(checkpoint.rglob("*.partial")) or any(checkpoint.rglob("*.sha256")):
    raise RuntimeError("Checkpoint preparation incomplete; finish integrity helper first")
objects = (checkpoint / "checkpoint-objects.json").read_bytes()
os.environ["JAX_PLATFORMS"] = "cuda"
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"
sys.path.insert(0, str(source / "src"))
sys.path.insert(0, str(source / "packages/openpi-client/src"))
logging.basicConfig(level=logging.INFO)

import jax  # noqa: E402
import numpy as np  # noqa: E402
from openpi.policies import policy_config  # noqa: E402
from openpi.serving.websocket_policy_server import WebsocketPolicyServer  # noqa: E402
from openpi.training import config  # noqa: E402

devices = jax.devices("gpu")
if not devices or jax.default_backend() != "gpu":
    raise RuntimeError("CUDA unavailable; CPU policy fallback is prohibited")
started = time.monotonic()
policy = policy_config.create_trained_policy(config.get_config("pi05_libero"), checkpoint)
metadata = {
    **policy.metadata,
    "openpi_commit": revision,
    "config": "pi05_libero",
    "checkpoint_uri": "gs://openpi-assets/checkpoints/pi05_libero",
    "checkpoint_objects_sha256": hashlib.sha256(objects).hexdigest(),
    "jax_version": jax.__version__,
    "device": str(devices[0]),
    "load_wall_s": time.monotonic() - started,
    "action_contract": "LIBERO OSC_POSE, 7 inputs; not joint positions",
}
if args.warmup:
    with np.load(args.warmup, allow_pickle=False) as data:
        observation = dict(data)
    observation["prompt"] = str(observation["prompt"].item())
    warmup_started = time.monotonic()
    result = policy.infer(observation)
    actions = np.asarray(result["actions"])
    if actions.ndim != 2 or actions.shape[1] != 7 or not np.isfinite(actions).all():
        raise RuntimeError("Real checkpoint warmup returned invalid actions")
    metadata.update(
        warmup_wall_s=time.monotonic() - warmup_started,
        warmup_input_sha256=hashlib.sha256(args.warmup.read_bytes()).hexdigest(),
        warmup_complete=True,
        discarded_warmup_actions=len(actions),
        startup_rng_draws=1,
    )
else:
    metadata["warmup_complete"] = False
(args.output / "loaded.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(json.dumps(metadata, indent=2), flush=True)
WebsocketPolicyServer(policy, host="127.0.0.1", port=args.port, metadata=metadata).serve_forever()
