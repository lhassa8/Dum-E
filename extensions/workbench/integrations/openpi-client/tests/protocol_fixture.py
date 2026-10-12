"""Real upstream server and a plainly labeled synthetic policy, with no GPU."""

import asyncio
import importlib.util
import threading
import time
from pathlib import Path

import numpy as np
from openpi_client.base_policy import BasePolicy

path = Path(__file__).parents[1] / "fixtures/upstream_websocket_policy_server.py"
spec = importlib.util.spec_from_file_location("upstream_test_server", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SyntheticPolicy(BasePolicy):
    def __init__(self, delay=0, bad=False):
        self.delay = delay
        self.bad = bad
        self.started = threading.Event()

    def infer(self, obs):
        assert set(obs) == {
            "observation/image",
            "observation/wrist_image",
            "observation/state",
            "prompt",
        }
        assert obs["observation/image"].shape == (224, 224, 3)
        assert obs["observation/wrist_image"].dtype == np.uint8
        assert obs["observation/state"].shape == (8,)
        self.started.set()
        time.sleep(self.delay)
        actions = np.zeros((50, 7), np.float32)
        actions[:, 0] = 0.1 if obs["prompt"] == "first task" else 0.2
        if self.bad:
            actions[0, 0] = np.nan
        return {"actions": actions}


class FixtureServer:
    def __init__(self, policy):
        self.policy = policy
        self.ready = threading.Event()
        self.stop = threading.Event()
        self.metadata = {
            "implementation": "synthetic_transport_fixture",
            "model_weights_loaded": False,
        }
        self.server = module.WebsocketPolicyServer(
            policy, host="127.0.0.1", port=0, metadata=self.metadata
        )

    def __enter__(self):
        self.thread = threading.Thread(target=lambda: asyncio.run(self.run()), daemon=True)
        self.thread.start()
        assert self.ready.wait(5)
        return self

    async def run(self):
        async with module._server.serve(
            self.server._handler, "127.0.0.1", 0, compression=None, max_size=None
        ) as server:
            self.port = server.sockets[0].getsockname()[1]
            self.ready.set()
            while not self.stop.is_set():
                await asyncio.sleep(0.01)

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join(timeout=5)
        assert not self.thread.is_alive()


def observation():
    image = np.zeros((224, 224, 3), np.uint8)
    return {
        "observation/image": image,
        "observation/wrist_image": image,
        "observation/state": np.zeros(8),
        "prompt": "first task",
    }
