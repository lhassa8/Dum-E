"""Preprocess an actual saved LIBERO observation for non-actuating startup warmup."""

import argparse
import json
from pathlib import Path

import numpy as np
from dume_pretrained.observations import libero_observation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--observation", type=Path, required=True)
parser.add_argument("--description", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    parser.error("Use a fresh output path")
with np.load(args.observation, allow_pickle=False) as data:
    raw = dict(data)
prompt = json.loads(args.description.read_text())["task"]
args.output.parent.mkdir(parents=True, exist_ok=True)
np.savez(args.output, **libero_observation(raw, prompt))
print("Prepared real-observation warmup; predicted actions will not be executed.")
