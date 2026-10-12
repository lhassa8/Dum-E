"""Readiness/inference probe; never execute returned robot actions."""

import argparse
import json
from pathlib import Path

import numpy as np

from dume_pretrained.connection import PolicyConnection
from dume_pretrained.observations import libero_observation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observation-npz", type=Path)
    parser.add_argument("--prompt", default="pick up the bowl")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    evidence = {
        "scope": "OpenPi connection probe; no robot actions executed",
        "model_identity_verified": False,
        "closed_loop_demonstrated": False,
        "connected": False,
        "passed": False,
    }
    try:
        with PolicyConnection(args.endpoint) as connection:
            evidence["connected"] = True
            evidence["server_metadata"] = connection.metadata
            if args.observation_npz:
                with np.load(args.observation_npz, allow_pickle=False) as data:
                    raw = {k: data[k].copy() for k in data.files}
                obs = libero_observation(raw, args.prompt)
                generation = connection.begin_task()
                evidence["inference"] = connection.infer(obs, generation)
                connection.stop()
                evidence["returned_actions_executed"] = 0
            evidence["passed"] = True
    except (ValueError, RuntimeError, TimeoutError, OSError) as error:
        evidence["error"] = str(error)
    (args.output / "probe.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    if not evidence["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
