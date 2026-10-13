"""Render an official fixed LIBERO initial state; no pretrained-policy claim."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--openpi", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
source = args.openpi.resolve()
libero = source / "third_party/libero"
benchmark_root = libero / "libero/libero"
config_dir = args.output.resolve() / "config"
config_dir.mkdir()
config = {
    "benchmark_root": str(benchmark_root),
    "bddl_files": str(benchmark_root / "bddl_files"),
    "init_states": str(benchmark_root / "init_files"),
    "assets": str(benchmark_root / "assets"),
    "datasets": str(libero / "libero/datasets"),
}
(config_dir / "config.yaml").write_text(
    "\n".join(key + ": " + json.dumps(value) for key, value in config.items()) + "\n"
)
os.environ["LIBERO_CONFIG_PATH"] = str(config_dir)
os.environ["MUJOCO_GL"] = "egl"
sys.path.insert(0, str(libero))
sys.path.insert(0, str(source / "packages/openpi-client/src"))
sys.path.insert(0, str(source))

import numpy as np  # noqa: E402
from examples.libero.main import LIBERO_DUMMY_ACTION, _get_libero_env  # noqa: E402
from libero.libero import benchmark  # noqa: E402
from PIL import Image  # noqa: E402

suite = benchmark.get_benchmark_dict()["libero_spatial"]()
protocol = {
    "suite": "libero_spatial",
    "task_ids": [0, 1, 2],
    "initial_state_index": 0,
    "seed": 7,
    "replan_steps": 5,
    "max_policy_steps": 220,
}
(args.output / "frozen-protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
task = suite.get_task(0)
env, description = _get_libero_env(task, 256, 7)
try:
    env.reset()
    states = suite.get_task_init_states(0)
    obs = env.set_init_state(states[0])
    for _ in range(10):
        obs, _, done, _ = env.step(LIBERO_DUMMY_ACTION)
    fields = [
        "agentview_image",
        "robot0_eye_in_hand_image",
        "robot0_eef_pos",
        "robot0_eef_quat",
        "robot0_gripper_qpos",
    ]
    np.savez(args.output / "observation.npz", **{key: obs[key] for key in fields})
    Image.fromarray(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])).save(
        args.output / "initial-scene.png"
    )
    controller = env.env.robots[0].controller
    controller_name = controller.name
    assert controller_name == "OSC_POSE", controller_name
    report = {
        "scope": "Actual LIBERO rendered initial state and ten stabilization steps; no policy",
        "task": description,
        "controller": controller_name,
        "action_units": "seven OSC_POSE inputs, not Panda joint positions",
        "images": {
            key: {"shape": list(obs[key].shape), "dtype": str(obs[key].dtype)} for key in fields[:2]
        },
        "initial_state_sha256": hashlib.sha256(np.asarray(states[0]).tobytes()).hexdigest(),
        "success_after_idle": bool(done),
        "closed_loop_demonstrated": False,
    }
    (args.output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
finally:
    env.close()
