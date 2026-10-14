"""Controlled old-step/reset interleaving against archived and current runtime classes."""

import argparse
import ast
import collections
import io
import json
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--before", type=Path, required=True)
args = parser.parse_args()
results = []
for name, source in (("archived", args.before),
                     ("current", Path(__file__).with_name("libero_runtime.py"))):
    with tempfile.TemporaryDirectory(prefix="scene-generation-") as directory:
        module = ast.parse(source.read_text())
        definition = next(node for node in module.body if isinstance(node, ast.ClassDef)
                          and node.name == "Runtime")
        isolated = ast.Module(body=[definition], type_ignores=[])
        env = {"args": SimpleNamespace(output=Path(directory), hold_profile="native",
                                        carry_governor_experiment=False, dense_hold_capture=False),
               "np": np, "json": json, "time": time, "io": io, "Image": Image,
               "collections": collections, "threading": threading,
               "benchmark": SimpleNamespace(get_benchmark_dict=lambda: {
                   "libero_spatial": lambda: object()})}
        exec(compile(isolated, str(source), "exec"), env)
        runtime = env["Runtime"]()
        runtime.phase, runtime.epoch = "failed", 1
        runtime.native_init_epoch = runtime.scene_request_epoch = 1
        runtime.task_id = 0
        runtime.observation_bytes = b"old-scene"
        runtime.judge = lambda: {"scene": "old"}
        observation = {"agentview_image": np.zeros((2, 2, 3), dtype=np.uint8),
                       "robot0_eye_in_hand_image": np.zeros((2, 2, 3), dtype=np.uint8),
                       "robot0_eef_pos": np.zeros(3), "robot0_eef_quat": np.array([0, 0, 0, 1]),
                       "robot0_gripper_qpos": np.zeros(2)}

        class FinishingOldStep:
            def step(self, action):
                # Equivalent to HTTP initialize arriving before the old step publishes.
                runtime.initialize(2)
                return observation, 0, False, {}

        runtime.env = FinishingOldStep()
        runtime.tick()
        leaked = runtime.observation_bytes is not None
        assert leaked == (name == "archived"), name
        assert runtime.phase == "initializing" and runtime.task_id == 2
        results.append({"source": name, "old_cache_republished": leaked})
        runtime.trace.close()
print(json.dumps({"passed": True, "interleavings": results,
                  "scope": "Cache concurrency regression; simulated step completion, not physics"}))
