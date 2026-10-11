"""New Dum-E interfaces backed by the native, locally running physics workbench."""

import asyncio
import json
import time
from dataclasses import asdict
from datetime import datetime

import httpx

# isort: split
from physical_ai_lab.dume import upstream  # noqa: F401 -- loads original absolute imports

# isort: split
from shared import (  # noqa: E402
    IRobotAgent,
    IRobotController,
    Message,
    MessageType,
    TaskStatus,
    ToolDefinition,
)


class SimulationController(IRobotController):
    """No serial devices or physical cameras; all commands go to localhost physics."""

    def __init__(self, url="http://127.0.0.1:8765"):
        self.url = url
        self.connected = False
        self.client = httpx.AsyncClient(base_url=url, timeout=5, trust_env=False)

    @property
    def id(self):
        return "dume_sim_panda"

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def is_connected(self):
        return self.connected

    def get_observation(self):
        response = httpx.get(self.url + "/state", timeout=5, trust_env=False)
        response.raise_for_status()
        return response.json()

    async def request(self, method, path, **kwargs):
        response = await self.client.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    async def state(self):
        return (await self.request("GET", "/state")).json()

    async def stop(self):
        await self.request("POST", "/stop")


class SimulationAgent(IRobotAgent):
    """Original Dum-E task/broker contract, with measured MuJoCo outcomes."""

    def __init__(self, controller, task_manager, broker, log_path, tools=False):
        self.controller = controller
        self.tasks = task_manager
        self.broker = broker
        self.log_path = log_path
        self.active_id = None
        self.messages = [
            {
                "role": "assistant",
                "content": "Hello! I'm your workshop sidekick. Ask me for a screwdriver, "
                "wrench or hammer, or say hello and I'll wave."
                if tools
                else "Dum-E is connected to the simulated Panda arm. "
                "Ask me to move a colored block to the green or purple target.",
            }
        ]
        self.last_result = None
        self.tools = tools
        self.lock = asyncio.Lock()
        from physical_ai_lab.dume.interaction import InteractionCoordinator

        self.interaction = InteractionCoordinator(self)

    def log_interaction(self, request, result, elapsed_ms):
        with (self.log_path.parent / "interactions.jsonl").open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "time": time.time(),
                        "request": request,
                        "result": result,
                        "elapsed_ms": elapsed_ms,
                    }
                )
                + "\n"
            )

    @property
    def id(self):
        return self.controller.id

    async def publish(self, kind, task_id, **data):
        message = Message(kind, task_id, datetime.now(), data)
        await self.broker.publish(message)
        with self.log_path.open("a") as file:
            file.write(
                json.dumps(
                    {
                        "type": kind.value,
                        "task_id": task_id,
                        "timestamp": message.timestamp.isoformat(),
                        "data": data,
                    }
                )
                + "\n"
            )

    async def submit(self, instruction, resolved_intent=None):
        metadata = {"robot_id": self.id, "source": "dume_sim_browser", "simulation": True}
        if resolved_intent:
            metadata["resolved_intent"] = resolved_intent
        task_id = await self.tasks.create_task(instruction, metadata)
        await self.publish(
            MessageType.TASK_CREATED, task_id, instruction=instruction, robot_id=self.id
        )
        return task_id

    async def worker(self):
        async for message in self.broker.subscribe(message_types=[MessageType.TASK_CREATED]):
            if message.data.get("robot_id") not in {None, self.id}:
                continue
            task_id = message.task_id
            if await self.tasks.claim_task(task_id, self.id):
                await self.arun(message.data["instruction"], task_id)

    async def arun(self, instruction, task_id=None):
        async with self.lock:
            task_id = task_id or await self.tasks.create_task(
                instruction, {"robot_id": self.id, "simulation": True}
            )
            record = await self.tasks.get_task(task_id)
            if record.status == TaskStatus.CANCELLED:
                return {"task_id": task_id, "status": "cancelled"}
            await self.tasks.update_task(task_id, TaskStatus.RUNNING)
            self.active_id = task_id
            self.messages.append({"role": "user", "content": instruction})
            await self.publish(MessageType.TASK_STARTED, task_id, instruction=instruction)
            try:
                before = await self.controller.state()
                if before["busy"]:
                    raise RuntimeError("The simulation is already handling another request.")
                payload = {"message": instruction}
                if record.metadata.get("resolved_intent"):
                    payload["intent"] = record.metadata["resolved_intent"]
                response = await self.controller.request("POST", "/chat", json=payload)
                job_id = response.json()["job_id"]
                seen_messages = len(before.get("messages", []))
                start, phase = time.monotonic(), None
                while True:
                    record = await self.tasks.get_task(task_id)
                    if record.status == TaskStatus.CANCELLED:
                        await self.controller.stop()
                        result = {
                            "status": "cancelled",
                            "message": self.stopped_message(),
                            "physical_success": False,
                        }
                        break
                    state = await self.controller.state()
                    if state["epoch"] != before["epoch"] and state["phase"] in {
                        "Stopping",
                        "Stopped",
                    }:
                        result = {
                            "status": "cancelled",
                            "message": self.stopped_message(),
                            "physical_success": False,
                        }
                        break
                    if state["job_id"] != job_id or state["epoch"] != before["epoch"]:
                        raise RuntimeError("The simulation request was interrupted or replaced.")
                    for message in state["messages"][seen_messages:]:
                        if message.get("role") == "assistant" and (
                            self.messages[-1].get("content") != message.get("content")
                        ):
                            self.messages.append(message)
                    seen_messages = len(state["messages"])
                    if state["phase"] != phase:
                        phase = state["phase"]
                        await self.publish(MessageType.TASK_PROGRESS, task_id, message=phase)
                    if not state["busy"]:
                        outcome = state["last_outcome"]
                        intent = state["last_intent"]
                        if outcome:
                            status = {
                                "success": "completed",
                                "expressed": "completed",
                                "interrupted": "cancelled",
                                "failed": "failed",
                            }[outcome["status"]]
                        else:
                            status = (
                                "completed"
                                if intent
                                and intent["action"] in {"clarify", "unsupported", "answer"}
                                else "failed"
                            )
                        result = {
                            "status": status,
                            "message": state["messages"][-1]["content"],
                            "physical_success": bool(outcome and outcome["status"] == "success"),
                            "intent": intent,
                            "outcome": outcome,
                            "observed": state["objects"],
                            "targets": state["targets"],
                            "verified_steps": state.get("verified_steps", []),
                        }
                        break
                    if time.monotonic() - start > 120:
                        await self.controller.stop()
                        raise TimeoutError("Simulation task exceeded two minutes and was stopped.")
                    await asyncio.sleep(0.12)
            except Exception as error:
                try:
                    await self.controller.stop()
                except httpx.HTTPError:
                    pass
                result = {"status": "failed", "message": str(error), "physical_success": False}
            finally:
                self.active_id = None
            result["task_id"] = task_id
            record = await self.tasks.get_task(task_id)
            if record.status == TaskStatus.CANCELLED:
                result.update(
                    status="cancelled",
                    physical_success=False,
                    message=self.stopped_message(),
                )
            status = TaskStatus(result["status"])
            await self.tasks.update_task(
                task_id, status, result["message"], {**record.metadata, "result": result}
            )
            self.last_result = result
            if self.messages[-1].get("content") != result["message"]:
                self.messages.append({"role": "assistant", "content": result["message"]})
            kind = {
                TaskStatus.COMPLETED: MessageType.TASK_COMPLETED,
                TaskStatus.FAILED: MessageType.TASK_FAILED,
                TaskStatus.CANCELLED: MessageType.TASK_FAILED,
            }[status]
            await self.publish(
                kind,
                task_id,
                result=result["status"],
                error=result["message"] if status != TaskStatus.COMPLETED else None,
                physical_success=result["physical_success"],
            )
            return result

    async def astream(self, instruction, task_id=None):
        # Broker supplies detailed streaming; interface iterator returns the final result.
        yield await self.arun(instruction, task_id)

    async def get_available_tools(self):
        return [
            ToolDefinition(
                "execute_robot_instruction",
                "Bring or return tools, resume a stopped task, or converse in simulation"
                if self.tools
                else "Move a block in simulation",
                self.submit,
                {
                    "type": "object",
                    "properties": {"instruction": {"type": "string"}},
                    "required": ["instruction"],
                },
                False,
                "simulation",
            )
        ]

    async def get_status(self):
        return {"robot_id": self.id, "simulation": True, "active_task": self.active_id}

    async def cancel(self, invalidate_interaction=True):
        # Physical stop first, then cancel both the active request and queued tasks.
        if invalidate_interaction:
            self.interaction.invalidate()
        await self.controller.stop()
        for task in await self.tasks.list_tasks():
            if task.status in {TaskStatus.PENDING, TaskStatus.RUNNING}:
                await self.tasks.cancel_task(task.task_id)

    def stopped_message(self):
        return (
            "Stopped. This task was cancelled; placement is not confirmed. "
            + ("Say resume to continue, or put it back to return the tool." if self.tools else "")
        ).strip()

    async def task_records(self):
        return [
            {
                **asdict(task),
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }
            for task in await self.tasks.list_tasks(limit=32)
        ]
