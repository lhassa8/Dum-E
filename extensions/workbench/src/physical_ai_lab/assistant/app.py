"""Local browser application; simulation/rendering run on the macOS main thread."""

import argparse
import io
import json
import os
import queue
import re
import socket
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from PIL import Image
from pydantic import BaseModel, Field

from physical_ai_lab.assistant.control import PickPlace
from physical_ai_lab.assistant.language import LocalLanguage
from physical_ai_lab.assistant.scene import TARGETS, Workbench

WEB = Path(__file__).parent / "web"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1500)


class Application:
    def __init__(self, model_path=None, log_path=None, tools=False):
        self.lock = threading.RLock()
        self.commands = queue.Queue()
        self.requests = queue.Queue()
        self.stop_event = threading.Event()
        self.closed = threading.Event()
        self.language = None
        self.model_status = "loading"
        self.model_error = None
        self.busy = False
        self.epoch = 0
        self.phase = "Starting workbench"
        self.task = None
        self.last_intent = None
        self.last_outcome = None
        self.job_id = None
        self.messages = []
        self.observations = {}
        self.image = b""
        self.model_path = model_path
        self.log_path = log_path
        self.events = []
        self.tools = tools
        self.joint_positions = []
        self.scene_targets = TARGETS
        self.interrupted = None
        self.paused_controller = None
        self.last_tool = None
        self.current_request = None
        if tools:
            from physical_ai_lab.assistant.tool_scene import HANDOFF

            self.scene_targets = HANDOFF
        self.add_message(
            "assistant",
            "Hello! Ready to lend a hand. Ask for a screwdriver, wrench or hammer, "
            "or say hello and watch me wave."
            if tools
            else "Welcome. I can move the red, blue or yellow block "
            "to the green or purple target. Try: “Put the red block in the green area.”",
        )

    def event(self, kind, **data):
        with self.lock:
            entry = {"time": time.time(), "kind": kind, **data}
            self.events.append(entry)
            if self.log_path:
                with self.log_path.open("a") as file:
                    file.write(json.dumps(entry) + "\n")

    def add_message(self, role, content):
        with self.lock:
            self.messages.append({"role": role, "content": content})
            self.event("message", role=role, content=content)

    def snapshot(self):
        with self.lock:
            return {
                "backend": "workbench",
                "schema_version": 2,
                "profile": "tools" if self.tools else "blocks",
                "messages": list(self.messages),
                "phase": self.phase,
                "busy": self.busy,
                "model_status": self.model_status,
                "model_error": self.model_error,
                "objects": self.observations,
                "targets": self.scene_targets,
                "robot_joints": self.joint_positions,
                "inventory": self.inventory(),
                "job_id": self.job_id,
                "task": self.task,
                "last_intent": self.last_intent,
                "last_outcome": self.last_outcome,
                "epoch": self.epoch,
                "recovery": {
                    "can_resume": self.interrupted is not None,
                    "tool": self.last_tool,
                    "interrupted": self.interrupted,
                },
            }

    def chat(self, text):
        text = text.strip()
        if not text:
            raise ValueError("Please enter a request")
        with self.lock:
            if self.busy:
                raise ValueError("A request is running. Use Stop before starting another one.")
            if self.stop_event.is_set():
                raise ValueError("The arm is stopping. Try again when it has stopped.")
            if self.model_status != "ready":
                raise ValueError("The language model is not ready yet.")
            history = [
                {"role": row["role"], "content": row["content"]}
                for row in self.messages
                if row["role"] in {"user", "assistant"}
            ][-8:]
            self.add_message("user", text)
            self.busy = True
            self.last_intent = None
            self.last_outcome = None
            self.phase = "Understanding your request"
            self.job_id = uuid.uuid4().hex[:8]
            self.current_request = text
            if self.tools:
                from physical_ai_lab.assistant.tool_language import ToolIntent

                words = re.sub(r"[^a-z\s]", " ", text.lower())
                words = " ".join(words.split())
                if words in {
                    "resume",
                    "resume please",
                    "please resume",
                    "continue",
                    "continue please",
                    "carry on",
                    "resume the task",
                    "continue the task",
                    "keep going",
                }:
                    if self.interrupted and self.interrupted["intent"] is None:
                        text = self.interrupted["request"]
                        self.current_request = text
                    else:
                        self.commands.put(
                            (
                                "intent",
                                (self.epoch, self.job_id, ToolIntent("resume", None, None, "")),
                            )
                        )
                        return
                elif words in {
                    "put it back",
                    "put it back please",
                    "please put it back",
                    "put that back",
                    "put that tool back in its rack please",
                    "return it",
                    "return the tool",
                }:
                    intent = (
                        ToolIntent("return", self.last_tool, "rack", "")
                        if self.last_tool
                        else ToolIntent("clarify", None, None, "Which tool should I put back?")
                    )
                    self.commands.put(("intent", (self.epoch, self.job_id, intent)))
                    return
            self.requests.put((self.epoch, self.job_id, text, history))

    def stop(self):
        with self.lock:
            if self.tools and self.busy and self.paused_controller is None:
                self.interrupted = {
                    "request": self.current_request,
                    "intent": self.last_intent,
                    "phase": self.phase,
                }
            self.epoch += 1
            self.stop_event.set()
            self.commands.put(("stop", None))
            self.busy = False
            self.phase = "Stopping"
            self.event("stop_requested")

    def language_worker(self):
        try:
            if self.tools:
                from physical_ai_lab.assistant.tool_language import ToolLanguage

                self.language = ToolLanguage(self.model_path)
            else:
                self.language = LocalLanguage(self.model_path)
            with self.lock:
                self.model_status = "ready"
                self.event("model_ready", model=str(self.language.path))
        except Exception as error:
            with self.lock:
                self.model_status = "unavailable"
                self.model_error = str(error)
            return
        while not self.closed.is_set():
            try:
                epoch, job, text, history = self.requests.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if self.tools:
                    with self.lock:
                        positions = dict(self.observations)
                    intent, raw = self.language.interpret(
                        text,
                        history,
                        observations={
                            "positions_m": positions,
                            "locations": self.inventory(positions),
                            "recent_tool": self.last_tool,
                            "interrupted_task": self.interrupted,
                        },
                    )
                else:
                    intent, raw = self.language.interpret(text, history)
                self.event(
                    "interpretation", job_id=job, request=text, raw=raw, intent=asdict(intent)
                )
                with self.lock:
                    if epoch != self.epoch:
                        continue
                    self.commands.put(("intent", (epoch, job, intent)))
            except Exception as error:
                with self.lock:
                    if epoch == self.epoch:
                        self.commands.put(("language_error", (epoch, str(error))))

    def inventory(self, positions=None):
        if not self.tools:
            return {}
        import numpy as np

        from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS

        positions = self.observations if positions is None else positions
        inventory = {}
        for name, xyz in positions.items():
            if xyz[2] > 0.06:
                location = "moving with the arm"
            elif np.linalg.norm(np.array(xyz[:2]) - HANDOFF["handoff"]) < 0.035:
                location = "handoff tray"
            elif np.linalg.norm(np.array(xyz[:2]) - TOOLS[name]) < 0.035:
                location = "tool rack"
            else:
                location = "elsewhere on the workbench"
            inventory[name] = location
        return inventory

    def tool_action(self, bench, intent, job):
        """Bounded recovery and expression run on the same native control thread."""
        from physical_ai_lab.assistant.tool_control import Gesture, ToolPerformance

        controller = None
        reply = intent.message
        if intent.action == "resume":
            if self.paused_controller is None:
                reply = "There isn't a stopped task to resume. Tell me what you'd like next."
                self.last_intent = {
                    "action": "answer",
                    "object": None,
                    "destination": None,
                    "message": reply,
                }
            else:
                controller = self.paused_controller
                controller.resume()
                self.last_intent = self.interrupted["intent"]
                self.current_request = self.interrupted["request"]
                reply = "Resuming the stopped task from where I paused."
                self.interrupted = self.paused_controller = None
        elif intent.action in {"fetch", "return"}:
            paused = self.paused_controller
            if intent.action == "return" and isinstance(paused, ToolPerformance):
                if paused.object == intent.object:
                    controller = paused.return_to_rack()
            if controller is None and bench.data.ctrl[7] < 128 and paused:
                reply = "I'm holding a stopped tool. Say resume or put it back first."
            else:
                controller = controller or ToolPerformance(
                    bench, intent.object, returning=intent.action == "return"
                )
                self.last_tool = intent.object
                self.interrupted = self.paused_controller = None
                reply = (
                    f"I'll bring you the {intent.object}."
                    if intent.action == "fetch"
                    else f"I'll put the {intent.object} back in its rack."
                )
        elif intent.action == "stop":
            self.stop()
            return None
        else:
            reply = reply or (
                "Which tool would you like: screwdriver, wrench or hammer?"
                if intent.action == "clarify"
                else "I can bring tools, put them back, resume a stopped task, and wave or nod."
            )
            # Conversation cannot move a paused grip or destroy its recovery state.
            if self.paused_controller is None and bench.data.ctrl[7] >= 128:
                gesture = (
                    intent.destination
                    if intent.action == "gesture"
                    else "curious"
                    if intent.action in {"clarify", "unsupported"}
                    else "nod"
                )
                controller = Gesture(bench, gesture, reply, brief=intent.action != "gesture")
        self.add_message("assistant", reply)
        self.busy = controller is not None
        self.phase = controller.phase if controller else "Ready"
        self.task = (
            {"object": controller.object, "destination": controller.destination}
            if controller
            else None
        )
        if controller:
            self.event("execution_started", job_id=job, **self.task)
        return controller

    def loop(self, bench):
        controller = None
        last_render = 0
        self.phase = "Ready"
        while not self.closed.is_set():
            started = time.monotonic()
            # Stop takes priority over pending intent, reset and all simulation actions.
            if self.stop_event.is_set():
                if controller:
                    if self.tools:
                        controller.pause()
                        self.paused_controller = controller
                    else:
                        controller.stop()
                    self.last_outcome = asdict(controller.outcome)
                    self.event("outcome", outcome=asdict(controller.outcome), job_id=self.job_id)
                    controller = None
                else:
                    bench.data.ctrl[:7] = bench.data.qpos[:7]
                with self.lock:
                    self.stop_event.clear()
                    self.busy = False
                    self.phase = "Stopped"
                    self.task = None
                    self.add_message(
                        "assistant", "Stopped. I have not confirmed completion of that task."
                    )
            while not self.commands.empty():
                kind, value = self.commands.get_nowait()
                if kind == "reset":
                    bench.reset(42)
                    controller = None
                    with self.lock:
                        self.interrupted = self.paused_controller = self.last_tool = None
                        self.last_intent = self.last_outcome = None
                        self.phase = "Ready"
                        self.task = None
                    self.add_message(
                        "assistant",
                        "The tool tray is reset. Ready for your next request."
                        if self.tools
                        else "Workbench reset. All blocks are back at their starting positions.",
                    )
                elif kind == "language_error":
                    epoch, error = value
                    if epoch != self.epoch:
                        continue
                    self.add_message(
                        "assistant",
                        "I could not interpret that request reliably. "
                        "No movement was started. Please try again.",
                    )
                    self.event("language_error", error=error)
                    with self.lock:
                        self.busy = False
                        self.phase = "Ready"
                elif kind == "intent":
                    epoch, job, intent = value
                    with self.lock:
                        if epoch != self.epoch:
                            continue
                        self.last_intent = asdict(intent)
                        if self.tools:
                            controller = self.tool_action(bench, intent, job)
                        elif intent.action == "move":
                            controller = PickPlace(bench, intent.object, intent.destination)
                            self.task = {"object": intent.object, "destination": intent.destination}
                            self.add_message(
                                "assistant",
                                f"I’ll move the {intent.object} block "
                                f"to the {intent.destination} target.",
                            )
                            self.event("execution_started", job_id=job, **self.task)
                        elif intent.action == "stop":
                            self.stop()
                        else:
                            if self.tools:
                                reply = intent.message or (
                                    "Which tool would you like: screwdriver, wrench or hammer?"
                                    if intent.action == "clarify"
                                    else "I can fetch tools to the handoff tray and wave or nod."
                                )
                            elif intent.action == "unsupported":
                                reply = "I can move blocks to the green or purple target, "
                                reply += "but I can’t perform that task."
                            elif intent.action == "clarify":
                                if intent.object is None and intent.destination is None:
                                    reply = "Which block (red, blue or yellow) and "
                                    reply += "which target (green or purple) would you like?"
                                elif intent.object is None:
                                    reply = "Which block would you like: red, blue or yellow?"
                                else:
                                    reply = "Which target would you like: green or purple?"
                            else:
                                reply = (
                                    intent.message or "I can move colored blocks between targets."
                                )
                            self.add_message("assistant", reply)
                            self.busy = False
                            self.phase = "Ready"
            if controller:
                more = controller.advance()
                for message in getattr(controller, "notifications", []):
                    self.add_message("assistant", message)
                if hasattr(controller, "notifications"):
                    controller.notifications.clear()
                if more:
                    with self.lock:
                        self.phase = controller.phase
                else:
                    outcome = controller.outcome
                    self.last_outcome = asdict(outcome)
                    if self.messages[-1]["content"] != outcome.message:
                        self.add_message("assistant", outcome.message)
                    self.event(
                        "outcome",
                        job_id=self.job_id,
                        object=controller.object,
                        destination=controller.destination,
                        outcome=asdict(outcome),
                        observed={k: v.tolist() for k, v in bench.observe().items()},
                        lift_m=controller.max_height - controller.initial_height,
                    )
                    controller = None
                    with self.lock:
                        self.busy = False
                        self.phase = (
                            "Ready" if outcome.status in {"success", "expressed"} else "Task failed"
                        )
                        self.task = None
                        self.interrupted = self.paused_controller = None
            else:
                bench.tick()
            with self.lock:
                self.observations = {k: v.tolist() for k, v in bench.observe().items()}
                self.joint_positions = bench.data.qpos[:7].tolist()
            if time.monotonic() - last_render >= 0.09:
                buffer = io.BytesIO()
                Image.fromarray(bench.render()).save(buffer, format="JPEG", quality=87)
                with self.lock:
                    self.image = buffer.getvalue()
                last_render = time.monotonic()
            time.sleep(max(0, 0.032 - (time.monotonic() - started)))


def make_api(state):
    api = FastAPI()

    @api.middleware("http")
    async def local_only(request: Request, call_next):
        # Bind locally and reject cross-site requests to robot-control endpoints.
        origin = request.headers.get("origin")
        host = request.headers.get("host", "")
        if origin and origin not in {f"http://{host}", f"https://{host}"}:
            return Response("Local workbench requests only", status_code=403)
        return await call_next(request)

    @api.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    @api.get("/state")
    def snapshot():
        return state.snapshot()

    @api.get("/frame.jpg")
    def frame():
        with state.lock:
            return Response(
                state.image, media_type="image/jpeg", headers={"Cache-Control": "no-store"}
            )

    @api.post("/chat")
    def chat(request: ChatRequest):
        try:
            state.chat(request.message)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return {"accepted": True, "job_id": state.job_id}

    @api.post("/stop")
    def stop():
        state.stop()
        return {"stopping": True}

    @api.post("/reset")
    def reset():
        with state.lock:
            if state.busy:
                raise HTTPException(409, "Stop the current request before resetting.")
            state.epoch += 1
            state.commands.put(("reset", None))
        return {"resetting": True}

    return api


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default=os.environ.get("WORKBENCH_MODEL"))
    parser.add_argument("--tools", action="store_true")
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument("--test-gripper-fault", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", args.port))
        except OSError:
            parser.error(
                f"Port {args.port} is already in use. Open the existing app or choose --port."
            )
    logdir = args.log_dir or Path("runs") / ("workbench-" + uuid.uuid4().hex[:8])
    logdir.mkdir(parents=True, exist_ok=False)
    state = Application(args.model, logdir / "events.jsonl", tools=args.tools)
    if args.tools:
        from physical_ai_lab.assistant.tool_scene import ToolWorkbench

        bench = ToolWorkbench()
    else:
        bench = Workbench()
    if args.test_gripper_fault:
        bench.model.actuator_forcerange[7] = [0, 0]
        state.event("verification_fault", fault="disabled gripper force")
    server = uvicorn.Server(
        uvicorn.Config(make_api(state), host="127.0.0.1", port=args.port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()
    threading.Thread(target=state.language_worker, daemon=True).start()
    print(f"Workbench: http://127.0.0.1:{args.port}\nSession log: {logdir.resolve()}", flush=True)
    try:
        state.loop(bench)
    except KeyboardInterrupt:
        pass
    finally:
        state.closed.set()
        server.should_exit = True
        bench.close()


if __name__ == "__main__":
    main()
