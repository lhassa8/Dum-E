"""Three frozen supported tasks using official policy preprocessing and simulator success."""

import argparse
import collections
import json
import os
import sys
import time
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--protocol", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
parser.add_argument("--port", type=int, default=8900)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
source = args.openpi.resolve()
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
sys.path.insert(0, str(source / "third_party/libero"))
sys.path.insert(0, str(source / "packages/openpi-client/src"))
sys.path.insert(0, str(source))

import imageio  # noqa: E402
import numpy as np  # noqa: E402
from examples.libero.main import LIBERO_DUMMY_ACTION, _get_libero_env, _quat2axisangle  # noqa: E402
from libero.libero import benchmark  # noqa: E402
from openpi_client import image_tools  # noqa: E402
from openpi_client.websocket_client_policy import WebsocketClientPolicy  # noqa: E402

protocol = json.loads(args.protocol.read_text())
assert protocol == {
    "suite": "libero_spatial",
    "task_ids": [0, 1, 2],
    "initial_state_index": 0,
    "seed": 7,
    "replan_steps": 5,
    "max_policy_steps": 220,
}, protocol
np.random.seed(protocol["seed"])
client = WebsocketClientPolicy("127.0.0.1", args.port)
metadata = client.get_server_metadata()
assert metadata["config"] == "pi05_libero" and metadata["device"].startswith("cuda")
report = {
    "scope": "Actual official pretrained policy and supported LIBERO simulator; no hardware",
    "protocol": protocol,
    "metadata": metadata,
    "episodes": [],
}
suite = benchmark.get_benchmark_dict()[protocol["suite"]]()
for task_id in protocol["task_ids"]:
    task = suite.get_task(task_id)
    env, prompt = _get_libero_env(task, 256, protocol["seed"])
    frames, timings, action_rows = [], [], []
    success, error, steps = False, None, 0
    try:
        env.reset()
        obs = env.set_init_state(suite.get_task_init_states(task_id)[0])
        assert env.env.robots[0].controller.name == "OSC_POSE"
        for _ in range(10):
            obs, _, _, _ = env.step(LIBERO_DUMMY_ACTION)
        plan = collections.deque()
        for steps in range(protocol["max_policy_steps"]):
            image = image_tools.convert_to_uint8(
                image_tools.resize_with_pad(
                    np.ascontiguousarray(obs["agentview_image"][::-1, ::-1]), 224, 224
                )
            )
            wrist = image_tools.convert_to_uint8(
                image_tools.resize_with_pad(
                    np.ascontiguousarray(obs["robot0_eye_in_hand_image"][::-1, ::-1]), 224, 224
                )
            )
            frames.append(image)
            if not plan:
                request = {
                    "observation/image": image,
                    "observation/wrist_image": wrist,
                    "observation/state": np.concatenate(
                        (
                            obs["robot0_eef_pos"],
                            _quat2axisangle(obs["robot0_eef_quat"].copy()),
                            obs["robot0_gripper_qpos"],
                        )
                    ),
                    "prompt": prompt,
                }
                started = time.monotonic()
                reply = client.infer(request)
                timings.append(
                    {
                        "client_ms": (time.monotonic() - started) * 1000,
                        **reply.get("server_timing", {}),
                    }
                )
                actions = np.asarray(reply["actions"])
                assert actions.ndim == 2 and actions.shape[1] == 7 and len(actions) >= 5
                assert np.isfinite(actions).all()
                plan.extend(actions[:5])
            action = plan.popleft()
            action_rows.append(action.tolist())
            obs, _, done, _ = env.step(action.tolist())
            if done:
                success = bool(env.env._check_success())
                assert success, "Done without the independent LIBERO task success predicate"
                break
    except Exception as caught:
        error = repr(caught)
    finally:
        env.close()
    episode = {
        "task_id": task_id,
        "prompt": prompt,
        "success": success,
        "steps": steps + 1,
        "inference_calls": len(timings),
        "error": error,
        "timings": timings,
        "actions": action_rows,
    }
    if frames:
        video = f"task-{task_id}-{'success' if success else 'failure'}.mp4"
        imageio.mimwrite(args.output / video, frames, fps=10)
        episode["video"] = video
    report["episodes"].append(episode)
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({key: episode[key] for key in ["task_id", "success", "steps", "error"]}),
        flush=True,
    )
    if error:
        # An infrastructure exception is not a reason to repeat the same failed
        # runtime on the remaining frozen tasks. Preserve what actually ran.
        report["not_run_task_ids"] = protocol["task_ids"][len(report["episodes"]) :]
        (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        break
print(
    "Supported task successes:",
    sum(e["success"] for e in report["episodes"]),
    "/",
    len(report["episodes"]),
    flush=True,
)
if any(not e["success"] for e in report["episodes"]):
    raise SystemExit(1)
