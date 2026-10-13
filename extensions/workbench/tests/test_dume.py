"""Contract probes using Dum-E's original shared-memory task store and broker."""

import asyncio
import hashlib
import json
import signal
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


def test_launcher_termination_unwinds_cleanup_and_restores_signal_handler(monkeypatch):
    import physical_ai_lab.dume.app as launcher

    previous = signal.getsignal(signal.SIGTERM)
    cleaned = []

    def owned_runtime():
        try:
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
        finally:
            cleaned.append(True)

    monkeypatch.setattr(launcher, "_main", owned_runtime)
    launcher.main()
    assert cleaned == [True]
    assert signal.getsignal(signal.SIGTERM) == previous


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


@pytest.mark.parametrize("scenario", ["completed", "paused", "working", "idle"])
def test_proceed_uses_current_state_without_reclassifying_old_fetch(
    upstream_backends, tmp_path, scenario
):
    class ContinuationProbe(ControllerProbe):
        async def state(self):
            value = await super().state()
            value.update(
                busy=scenario == "working",
                recovery={"tool": "screwdriver", "can_resume": scenario == "paused"},
                last_outcome={"status": "success", "message": "Your screwdriver is ready."}
                if scenario == "completed" else None,
            )
            return value

        async def request(self, *args, **kwargs):
            raise AssertionError("Proceed must never ask the model to repeat a pickup")

    async def run():
        tasks, broker = upstream_backends
        controller = ContinuationProbe()
        agent = SimulationAgent(controller, tasks, broker, tmp_path / "events.jsonl", tools=True)
        # Pending conversational clarification must not change continuation semantics.
        agent.interaction.clarification = {"request": "Bring a tool", "question": "Which one?"}
        result = await agent.interaction.interact("Proceed.")
        if scenario == "paused":
            task = await tasks.get_task(result["task_id"])
            assert task.metadata["resolved_intent"]["action"] == "resume"
        else:
            assert result["mode"] == "conversation" and result["task_id"] is None
            assert len(await tasks.list_tasks()) == 0
            if scenario == "completed":
                assert result["message"] == "Your screwdriver is ready."

    asyncio.run(run())


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


def test_conversation_during_work_preserves_original_task(upstream_backends, tmp_path):
    class WorkingProbe(ControllerProbe):
        async def state(self):
            value = await super().state()
            value.update(busy=True, phase="Lifting tool")
            return value

        async def request(self, *args, **kwargs):
            intent = {
                "action": "answer",
                "object": None,
                "destination": None,
                "message": "I'm lifting the screwdriver. Placement isn't confirmed yet.",
            }
            return type(
                "Response", (), {"json": lambda self: {"intent": intent, "route": "state"}}
            )()

    async def run():
        tasks, broker = upstream_backends
        controller = WorkingProbe()
        agent = SimulationAgent(controller, tasks, broker, tmp_path / "events.jsonl", tools=True)
        tid = await tasks.create_task("Bring me the screwdriver")
        await tasks.update_task(tid, TaskStatus.RUNNING)
        result = await agent.interaction.interact("What are you doing?")
        assert result["mode"] == "conversation" and result["task_id"] is None
        assert (await tasks.get_task(tid)).status == TaskStatus.RUNNING
        assert not controller.stopped and not controller.sent
        assert len(await tasks.list_tasks()) == 1

    asyncio.run(run())


def test_idle_tool_question_does_not_enter_physical_task_queue(upstream_backends, tmp_path):
    class IdleProbe(ControllerProbe):
        async def request(self, *args, **kwargs):
            assert args[:2] == ("POST", "/understand")
            return type(
                "Response",
                (),
                {
                    "json": lambda self: {
                        "intent": {
                            "action": "answer",
                            "object": None,
                            "destination": None,
                            "message": "A wrench helps tighten nuts.",
                        },
                        "route": "model",
                    }
                },
            )()

    async def run():
        tasks, broker = upstream_backends
        controller = IdleProbe()
        agent = SimulationAgent(controller, tasks, broker, tmp_path / "events.jsonl", tools=True)
        result = await agent.interaction.interact("Which tool helps tighten nuts?")
        assert result["mode"] == "conversation" and result["task_id"] is None
        assert not await tasks.list_tasks() and not controller.sent and not controller.stopped
        assert agent.messages[-1]["content"] == "A wrench helps tighten nuts."
        # A familiar physical request still submits immediately, without LLM work.
        physical = await agent.interaction.interact("Bring me the screwdriver.")
        assert physical["mode"] == "task" and physical["task_id"]
        assert len(await tasks.list_tasks()) == 1

    asyncio.run(run())


def test_change_cancels_original_request_before_worker_claim(upstream_backends, tmp_path):
    class PendingProbe(ControllerProbe):
        async def state(self):
            value = await super().state()
            value["phase"] = "Stopped" if self.stopped else "Ready"
            return value

        async def request(self, *args, **kwargs):
            intent = {
                "action": "fetch",
                "object": "wrench",
                "destination": "handoff",
                "message": "",
            }
            return type(
                "Response", (), {"json": lambda self: {"intent": intent, "route": "familiar"}}
            )()

    async def run():
        tasks, broker = upstream_backends
        controller = PendingProbe()
        agent = SimulationAgent(controller, tasks, broker, tmp_path / "events.jsonl", tools=True)
        old = await agent.submit("Bring me the screwdriver")
        result = await agent.interaction.interact("Actually bring me the wrench instead")
        assert controller.stopped and result["mode"] == "change"
        assert (await tasks.get_task(old)).status == TaskStatus.CANCELLED
        assert not await tasks.claim_task(old, agent.id)
        new = await tasks.get_task(result["task_id"])
        assert new.status == TaskStatus.PENDING
        assert new.metadata["resolved_intent"]["object"] == "wrench"

    asyncio.run(run())


@pytest.mark.parametrize("cancelled_http_reply", [False, True])
def test_stop_supersedes_slow_dialogue_before_any_new_task(
    upstream_backends, tmp_path, cancelled_http_reply
):
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()

        class SlowUnderstandingProbe(ControllerProbe):
            async def state(self):
                value = await super().state()
                value.update(
                    busy=not self.stopped, phase="Stopped" if self.stopped else "Lifting tool"
                )
                return value

            async def request(self, *args, **kwargs):
                entered.set()
                await release.wait()
                if cancelled_http_reply:
                    import httpx

                    request = httpx.Request("POST", "http://127.0.0.1/understand")
                    raise httpx.HTTPStatusError(
                        "Cancelled", request=request, response=httpx.Response(409, request=request)
                    )
                intent = {
                    "action": "fetch",
                    "object": "wrench",
                    "destination": "handoff",
                    "message": "",
                }
                return type(
                    "Response", (), {"json": lambda self: {"intent": intent, "route": "model"}}
                )()

        tasks, broker = upstream_backends
        controller = SlowUnderstandingProbe()
        agent = SimulationAgent(controller, tasks, broker, tmp_path / "events.jsonl", tools=True)
        tid = await tasks.create_task("Bring the screwdriver")
        await tasks.update_task(tid, TaskStatus.RUNNING)
        pending = asyncio.create_task(agent.interaction.interact("I need something for nuts"))
        await entered.wait()
        queued = asyncio.create_task(agent.interaction.interact("Bring me the hammer."))
        await asyncio.sleep(0)  # Request arrives while the first holds the dialogue lock.
        await agent.cancel()
        assert controller.stopped and (await tasks.get_task(tid)).status == TaskStatus.CANCELLED
        release.set()
        result = await pending
        assert result["mode"] == "superseded" and not result["accepted"]
        queued_result = await queued
        assert queued_result["mode"] == "superseded" and not queued_result["accepted"]
        assert len(await tasks.list_tasks()) == 1 and not controller.sent

    asyncio.run(run())


@pytest.mark.parametrize(
    "action,route,expected_motion", [("answer", "decline", True), ("stop", "model", False)]
)
def test_withdrawal_and_ambiguous_model_stop_are_explicit(
    upstream_backends, tmp_path, action, route, expected_motion
):
    class WorkingProbe(ControllerProbe):
        async def state(self):
            value = await super().state()
            value.update(
                busy=not self.stopped,
                phase="Stopped" if self.stopped else "Lifting tool",
                task={"object": "wrench", "destination": "handoff"},
                recovery={"tool": "wrench"},
                last_intent={"action": "fetch", "object": "wrench", "destination": "handoff"},
            )
            return value

        async def request(self, *args, **kwargs):
            intent = {"action": action, "object": None, "destination": None, "message": "Okay"}
            return type("Response", (), {"json": lambda self: {"intent": intent, "route": route}})()

    async def run():
        tasks, broker = upstream_backends
        controller = WorkingProbe()
        agent = SimulationAgent(controller, tasks, broker, tmp_path / "events.jsonl", tools=True)
        tid = await tasks.create_task("Bring the wrench")
        await tasks.update_task(tid, TaskStatus.RUNNING)
        result = await agent.interaction.interact(
            "Don't bring me the wrench." if expected_motion else "Don't stop thinking about it"
        )
        assert controller.stopped is expected_motion
        if expected_motion:
            assert result["mode"] == "change"
            new_task = await tasks.get_task(result["task_id"])
            assert new_task.metadata["resolved_intent"]["action"] == "return"
            assert (await tasks.get_task(tid)).status == TaskStatus.CANCELLED
        else:
            assert result["mode"] == "conversation" and result["intent"]["action"] == "clarify"
            assert (await tasks.get_task(tid)).status == TaskStatus.RUNNING

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


@pytest.mark.parametrize(
    "phase,expected", [("Stopping", "cancelled"), ("Stopped", "cancelled"), ("Ready", "failed")]
)
def test_stop_epoch_before_task_record_cancellation(upstream_backends, tmp_path, phase, expected):
    class StopBeforeRecordProbe(ControllerProbe):
        async def state(self):
            value = await super().state()
            if self.sent:
                value.update(epoch=1, phase=phase)
            return value

    async def run():
        tasks, broker = upstream_backends
        agent = SimulationAgent(StopBeforeRecordProbe(), tasks, broker, tmp_path / "events.jsonl")
        result = await agent.arun("Bring me the wrench")
        assert result["status"] == expected and not result["physical_success"]
        assert (await tasks.get_task(result["task_id"])).status == TaskStatus(expected)

    asyncio.run(run())
