"""Contract probes using Dum-E's original shared-memory task store and broker."""

import asyncio
import hashlib
import json
import uuid
from multiprocessing.managers import SharedMemoryManager
from pathlib import Path

import pytest

pytest.importorskip("fastmcp")

from physical_ai_lab.dume.bridge import SimulationAgent  # noqa: E402
from physical_ai_lab.dume.upstream import VENDOR  # noqa: E402

# isort: split
from shared import TaskStatus  # noqa: E402
from shared.message_broker import SharedMemoryMessageBroker  # noqa: E402
from shared.task_manager import SharedMemoryTaskManager  # noqa: E402


@pytest.fixture
def upstream_backends():
    with SharedMemoryManager() as manager:
        namespace = "probe_" + uuid.uuid4().hex[:8]
        task_buffer = manager.ShareableList([" " * 8192] * 8)
        broker_buffer = manager.ShareableList([" " * 8192] * 16)
        broker_meta = manager.ShareableList([0])
        tasks = SharedMemoryTaskManager(namespace, task_buffer.shm.name)
        broker = SharedMemoryMessageBroker(namespace, broker_buffer.shm.name, broker_meta.shm.name)
        yield tasks, broker
        for buffer in [tasks.tasks, broker.buffer, broker.meta]:
            buffer.shm.close()


class ControllerProbe:
    id = "dume_sim_panda"

    def __init__(self, outcome=None, action="move", unavailable=False):
        self.outcome = outcome
        self.action = action
        self.unavailable = unavailable
        self.stopped = False
        self.sent = False

    async def state(self):
        if self.unavailable:
            raise ConnectionError("Simulator unavailable")
        return {
            "busy": False,
            "epoch": 0,
            "job_id": "job",
            "phase": "Ready",
            "last_outcome": self.outcome,
            "last_intent": {"action": self.action} if self.sent else None,
            "messages": [{"content": "Observed result"}],
            "objects": {},
            "targets": {},
        }

    async def request(self, *args, **kwargs):
        self.sent = True
        return type("Response", (), {"json": lambda self: {"job_id": "job"}})()

    async def stop(self):
        self.stopped = True


def test_pinned_sources_unmodified():
    manifest = json.loads((Path(__file__).parents[1] / "upstream-source.json").read_text())
    assert manifest["revision"] == "f09a96827ea60e4b18a55fa67e2acb97800dc46b"
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == digest, name


@pytest.mark.parametrize(
    "outcome,action,expected,physical",
    [
        ({"status": "success", "distance_m": 0.004}, "move", "completed", True),
        ({"status": "failed"}, "move", "failed", False),
        (None, "clarify", "completed", False),
        (None, "unsupported", "completed", False),
        (None, "move", "failed", False),
        (None, "answer", "completed", False),
        ({"status": "expressed"}, "gesture", "completed", False),
    ],
)
def test_task_results_depend_on_observation(
    upstream_backends, tmp_path, outcome, action, expected, physical
):
    async def run():
        tasks, broker = upstream_backends
        agent = SimulationAgent(
            ControllerProbe(outcome, action), tasks, broker, tmp_path / "events.jsonl"
        )
        task_id = await agent.submit("Move a block")
        assert await tasks.claim_task(task_id, agent.id)
        result = await agent.arun("Move a block", task_id)
        task = await tasks.get_task(task_id)
        assert result["status"] == expected
        assert task.status == TaskStatus(expected)
        assert task.metadata["result"]["physical_success"] is physical
        assert task.metadata["worker_id"] == agent.id
        history = await broker.get_message_history(task_id=task_id)
        assert history[0].data["physical_success"] is physical

    asyncio.run(run())


def test_backend_loss_fails_task(upstream_backends, tmp_path):
    async def run():
        tasks, broker = upstream_backends
        controller = ControllerProbe(unavailable=True)
        agent = SimulationAgent(controller, tasks, broker, tmp_path / "events.jsonl")
        result = await agent.arun("Move red to green")
        assert result["status"] == "failed"
        assert result["physical_success"] is False
        assert controller.stopped
        assert (await tasks.get_task(result["task_id"])).status == TaskStatus.FAILED

    asyncio.run(run())


def test_cancel_pending_never_starts_motion(upstream_backends, tmp_path):
    async def run():
        tasks, broker = upstream_backends
        controller = ControllerProbe()
        agent = SimulationAgent(controller, tasks, broker, tmp_path / "events.jsonl")
        task_id = await agent.submit("Move red to green")
        await agent.cancel()
        result = await agent.arun("Move red to green", task_id)
        assert result["status"] == "cancelled"
        assert not controller.sent
        assert controller.stopped

    asyncio.run(run())
