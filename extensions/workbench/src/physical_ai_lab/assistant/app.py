"""Local browser application; simulation/rendering run on the macOS main thread."""

import argparse
import hashlib
import io
import json
import os
import queue
import signal
import socket
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Literal

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


class ResolvedChatRequest(ChatRequest):
    intent: dict | None = None


class DialogueRow(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=1500)


class UnderstandingRequest(ChatRequest):
    history: list[DialogueRow] = Field(default_factory=list, max_length=8)


class Application:
    def __init__(self, model_path=None, log_path=None, tools=False, camera_tools=False):
        self.lock = threading.RLock()
        self.commands = queue.Queue()
        self.requests = queue.Queue()
        self.stop_event = threading.Event()
        self.closed = threading.Event()
        self.language = None
        self.language_lock = threading.Lock()
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
        self.camera_tools = camera_tools
        self.camera_hub = None
        self.physics_profile = None
        self.vision = None
        self.vision_lock = threading.Lock()
        self.camera_image = self.camera_answer_image = b""
        self.camera_alternate_image = b""
        self.camera_captured_s = None
        self.last_camera_read = None
        self.language_backend = (
            os.environ.get("WORKBENCH_LANGUAGE_BACKEND", "mlx") if tools else "mlx"
        )
        self.joint_positions = []
        self.gripper_command = 255
        self.scene_targets = TARGETS
        self.interrupted = None
        self.paused_controller = None
        self.last_tool = None
        self.current_request = None
        self.responsiveness = {}
        self.request_clock = None
        self.verified_steps = []
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
                "tool_control": "camera" if self.camera_tools else "baseline",
                "physics_profile": self.physics_profile,
                "camera": {
                    "model": getattr(self.vision, "model", None),
                    "coordinates": getattr(self.vision, "coordinates", None),
                    "endpoint": getattr(self.vision, "url", None),
                    "last_read": self.last_camera_read,
                },
                "messages": list(self.messages),
                "phase": self.phase,
                "busy": self.busy,
                "model_status": self.model_status,
                "model_error": self.model_error,
                "language_backend": self.language_backend,
                "language_model": str(getattr(self.language, "path", "unknown"))
                if self.language
                else None,
                "language_endpoint": getattr(self.language, "url", None),
                "objects": self.observations,
                "targets": self.scene_targets,
                "robot_joints": self.joint_positions,
                "gripper_command": self.gripper_command,
                "inventory": self.inventory(),
                "job_id": self.job_id,
                "task": self.task,
                "last_intent": self.last_intent,
                "last_outcome": self.last_outcome,
                "epoch": self.epoch,
                "responsiveness": dict(self.responsiveness),
                "verified_steps": list(self.verified_steps),
                "recovery": {
                    "can_resume": self.interrupted is not None,
                    "tool": self.last_tool,
                    "interrupted": self.interrupted,
                },
            }

    def chat(self, text, resolved=None):
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
            self.verified_steps = []
            self.phase = "Understanding your request"
            self.job_id = uuid.uuid4().hex[:8]
            self.current_request = text
            self.request_clock = time.monotonic()
            self.responsiveness = {"job_id": self.job_id, "route": "model"}
            self.event("request_received", job_id=self.job_id, request=text)
            if self.tools:
                from physical_ai_lab.assistant.tool_routing import known_intent

                continuation, _ = known_intent(text, self.last_tool)
                intent, route = (
                    (continuation, "context")
                    if continuation and continuation.action == "resume"
                    else (resolved, "resolved") if resolved else known_intent(text, self.last_tool)
                )
                if intent and intent.action == "resume":
                    if self.interrupted and self.interrupted["intent"] is None:
                        text = self.interrupted["request"]
                        self.current_request = text
                        intent, route = known_intent(text, self.last_tool)
                if intent is not None:
                    self.responsiveness["route"] = route
                    self.event(
                        "interpretation",
                        job_id=self.job_id,
                        request=text,
                        raw=None,
                        intent=asdict(intent),
                        route=route,
                    )
                    self.timing_point("interpretation_ms", self.job_id)
                    self.commands.put(("intent", (self.epoch, self.job_id, intent)))
                    return
            self.requests.put((self.epoch, self.job_id, text, history))

    def understand(self, text, history=()):
        """Read-only interpretation; never changes the active job, grip or path."""
        from physical_ai_lab.assistant.tool_routing import known_intent, status_intent

        started = time.monotonic()
        snapshot = self.snapshot()
        profile = None
        if self.tools:
            from physical_ai_lab.assistant.tool_language import ToolIntent
            from physical_ai_lab.assistant.vision_language import camera_question, describe_snapshot

            matched, requested_tool = camera_question(text)
            if matched:
                if self.vision is None:
                    intent = ToolIntent(
                        "answer", None, None, "The simulated camera isn't enabled in this session."
                    )
                else:
                    with self.vision_lock:
                        with self.lock:
                            jpeg, captured, epoch = (
                                self.camera_image,
                                self.camera_captured_s,
                                self.epoch,
                            )
                            alternate = self.camera_alternate_image
                        if captured is None or time.monotonic() - captured > 0.75:
                            raise ValueError("The simulated camera frame isn't fresh; try again.")
                        try:
                            self.event("camera_inference_started", request=text,
                                       active_job=snapshot["job_id"], epoch=epoch)
                            observation = self.vision.observe(jpeg)
                            view, calls = "front", [observation["elapsed_ms"]]
                            names = (
                                [requested_tool] if requested_tool else list(observation["tools"])
                            )
                            if alternate and any(
                                not observation["tools"][n]["visible"] for n in names
                            ):
                                with self.lock:
                                    if epoch != self.epoch:
                                        raise ValueError("Camera request was superseded.")
                                other = self.vision.observe(alternate)
                                calls.append(other["elapsed_ms"])
                                # Choose one complete optical observation. Never fill a
                                # missing class or coordinate from simulator object state.
                                if sum(other["tools"][n]["visible"] for n in names) > sum(
                                    observation["tools"][n]["visible"] for n in names
                                ):
                                    observation, jpeg, view = other, alternate, "side"
                        except Exception as error:
                            self.event("camera_failed", error=repr(error))
                            raise ValueError(
                                "I couldn't reliably inspect that simulator snapshot."
                            ) from error
                        finally:
                            self.event("camera_inference_finished", request=text,
                                       active_job=snapshot["job_id"], epoch=epoch)
                        profile = {
                            **observation,
                            "captured_monotonic_s": captured,
                            "frame_sha256": hashlib.sha256(jpeg).hexdigest(),
                            "view": view,
                            "view_call_ms": calls,
                        }
                        with self.lock:
                            if epoch != self.epoch:
                                raise ValueError("Camera request was superseded.")
                            self.camera_answer_image = jpeg
                            self.last_camera_read = profile
                        intent = ToolIntent(
                            "answer", None, None, describe_snapshot(observation, requested_tool)
                        )
                elapsed = (time.monotonic() - started) * 1000
                self.event(
                    "understanding",
                    request=text,
                    intent=asdict(intent),
                    route="camera",
                    elapsed_ms=elapsed,
                    profile=profile,
                    active_job=snapshot["job_id"],
                )
                return {
                    "intent": asdict(intent),
                    "route": "camera",
                    "elapsed_ms": elapsed,
                    "profile": profile,
                }
        intent = status_intent(text, snapshot)
        route = "state"
        if intent is None:
            intent, route = known_intent(text, snapshot["recovery"]["tool"])
        if intent is None:
            if self.model_status != "ready":
                raise ValueError("The language model is not ready.")
            with self.language_lock:
                self.event("language_inference_started", request=text,
                           active_job=snapshot["job_id"], epoch=snapshot["epoch"])
                try:
                    intent, _ = self.language.interpret(
                        text,
                        history,
                        observations={
                            "positions_m": {} if self.camera_tools else snapshot["objects"],
                            "locations": snapshot["inventory"],
                            "recent_tool": snapshot["recovery"]["tool"],
                            "interrupted_task": snapshot["recovery"]["interrupted"],
                            "active_task": snapshot["task"],
                            "phase": snapshot["phase"],
                        },
                    )
                except RuntimeError as error:
                    raise ValueError(str(error)) from error
                finally:
                    self.event("language_inference_finished", request=text,
                               active_job=snapshot["job_id"], epoch=snapshot["epoch"])
                profile = dict(getattr(self.language, "last_profile", {}))
            route = "model"
        elapsed = (time.monotonic() - started) * 1000
        self.event(
            "understanding",
            request=text,
            intent=asdict(intent),
            route=route,
            elapsed_ms=elapsed,
            active_job=snapshot["job_id"],
            profile=profile,
        )
        return {"intent": asdict(intent), "route": route, "elapsed_ms": elapsed, "profile": profile}

    def timing_point(self, name, job):
        with self.lock:
            if job == self.job_id and self.request_clock is not None:
                elapsed = round((time.monotonic() - self.request_clock) * 1000, 3)
                self.responsiveness[name] = elapsed
                self.event("timing", job_id=job, stage=name, elapsed_ms=elapsed)

    def stop(self):
        cancel = getattr(self.language, "cancel", None)
        with self.lock:
            # Browser and task bridge can acknowledge the same cancellation.
            # Repeated Stop must not restart stopping or invalidate a later reset.
            if not (self.stop_event.is_set() or (self.phase == "Stopped" and not self.busy)):
                previous_phase = self.phase
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
                self.event("stop_requested", phase=previous_phase, job_id=self.job_id,
                           task=self.task)
        if cancel:
            try:
                cancel()
            except (RuntimeError, OSError) as error:
                self.event("language_cancel_failed", error=str(error))

    def language_worker(self):
        try:
            started = time.perf_counter()
            if self.tools:
                from physical_ai_lab.assistant.tool_language import make_tool_language

                self.language = make_tool_language(self.model_path)
            else:
                self.language = LocalLanguage(self.model_path)
            with self.lock:
                self.model_status = "ready"
                self.event(
                    "model_ready",
                    model=str(self.language.path),
                    preparation_ms=(time.perf_counter() - started) * 1000,
                    prefix_prepare_ms=getattr(self.language, "prefix_prepare_ms", 0),
                    startup_warmup_ms=getattr(self.language, "startup_warmup_ms", 0),
                    cached_prefix_tokens=len(getattr(self.language, "prefix_tokens", [])),
                    residency=getattr(self.language, "residency", None).profile()
                    if getattr(self.language, "residency", None)
                    else None,
                    residency_error=getattr(self.language, "residency_error", None),
                )
        except Exception as error:
            with self.lock:
                self.model_status = "unavailable"
                self.model_error = str(error)
            return
        while not self.closed.is_set():
            try:
                epoch, job, text, history = self.requests.get(timeout=0.2)
            except queue.Empty:
                keeper = getattr(self.language, "residency", None)
                if keeper is not None and self.language_lock.acquire(blocking=False):
                    try:
                        keeper.refresh()
                    except Exception as error:
                        self.language.residency = None
                        try:
                            keeper.close()
                        except Exception as cleanup_error:
                            self.event("residency_cleanup_failed", error=str(cleanup_error))
                        self.event("residency_disabled", error=str(error))
                    finally:
                        self.language_lock.release()
                continue
            try:
                with self.lock:
                    if epoch != self.epoch:
                        continue
                self.timing_point("interpretation_started_ms", job)
                if self.tools:
                    with self.lock:
                        positions = {} if self.camera_tools else dict(self.observations)
                    with self.language_lock:
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
                        profile = dict(getattr(self.language, "last_profile", {}))
                else:
                    with self.language_lock:
                        intent, raw = self.language.interpret(text, history)
                        profile = dict(getattr(self.language, "last_profile", {}))
                self.event(
                    "interpretation",
                    job_id=job,
                    request=text,
                    raw=raw,
                    intent=asdict(intent),
                    route="model",
                    profile=profile,
                )
                self.timing_point("interpretation_ms", job)
                with self.lock:
                    if epoch != self.epoch:
                        continue
                    self.commands.put(("intent", (epoch, job, intent)))
            except Exception as error:
                with self.lock:
                    if epoch == self.epoch:
                        self.commands.put(("language_error", (epoch, str(error))))
        keeper = getattr(self.language, "residency", None)
        if keeper is not None:
            with self.language_lock:
                try:
                    keeper.close()
                except Exception as error:
                    self.event("residency_cleanup_failed", error=str(error))
        close = getattr(self.language, "close", None)
        if close is not None:
            close()

    def inventory(self, positions=None):
        if not self.tools:
            return {}
        if self.camera_tools:
            return self.camera_hub.inventory() if self.camera_hub else {}
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
        import numpy as np

        from physical_ai_lab.assistant.tool_control import Gesture, ToolChange, ToolPerformance
        from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS

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
                if (
                    self.camera_tools
                    and controller.outcome
                    and controller.outcome.status == "failed"
                ):
                    self.add_message("assistant", controller.outcome.message)
                    self.busy = False
                    self.phase = "Stopped"
                    self.task = None
                    return None
                self.last_intent = self.interrupted["intent"]
                self.current_request = self.interrupted["request"]
                reply = (
                    controller.outcome.message
                    if controller.outcome and controller.outcome.status == "failed"
                    else "Resuming the stopped task from where I paused."
                )
                self.interrupted = self.paused_controller = None
        elif intent.action in {"fetch", "return"}:
            paused = self.paused_controller
            if self.camera_tools:
                try:
                    controller = self.camera_hub.select(
                        intent.object, returning=intent.action == "return", paused=paused
                    )
                except ValueError as error:
                    self.event("camera_request_refused", error=str(error), job_id=job)
                    self.add_message(
                        "assistant", "I cannot confirm a safe camera task. Resume or reset first."
                    )
                    self.busy = False
                    self.phase = "Stopped" if paused else "Task failed"
                    return None
                self.last_tool = controller.object
                self.interrupted = self.paused_controller = None
                verb = "bring you" if intent.action == "fetch" else "put back"
                reply = f"I'll {verb} the {intent.object}."
                if isinstance(controller, ToolChange):
                    reply = (
                        f"I'll return the {controller.previous_tool} first, "
                        f"then handle the {intent.object}."
                    )
                self.add_message("assistant", reply)
                self.busy = True
                self.phase = controller.phase
                self.task = {"object": controller.object, "destination": controller.destination}
                self.event("execution_started", job_id=job, **self.task)
                return controller
            if isinstance(paused, (ToolPerformance, ToolChange)):
                if paused.object == intent.object:
                    controller = (
                        paused.return_to_rack()
                        if intent.action == "return"
                        else paused.redirect_to_handoff()
                    )
                elif (
                    bench.data.ctrl[7] < 128
                    or np.linalg.norm(bench.observe()[paused.object][:2] - TOOLS[paused.object])
                    > 0.035
                ):
                    controller = ToolChange(
                        bench, paused, intent.object, returning=intent.action == "return"
                    )
            if controller is None and bench.data.ctrl[7] < 128 and paused:
                reply = "I'm holding a stopped tool. Say resume or put it back first."
            else:
                if controller is None and intent.action == "fetch":
                    occupied = [
                        name
                        for name, xyz in bench.observe().items()
                        if name != intent.object
                        and xyz[2] < 0.04
                        and np.linalg.norm(xyz[:2] - HANDOFF["handoff"]) < 0.035
                    ]
                    if occupied:
                        previous = ToolPerformance(bench, occupied[0], returning=True)
                        controller = ToolChange(bench, previous, intent.object)
                controller = controller or ToolPerformance(
                    bench, intent.object, returning=intent.action == "return"
                )
                self.last_tool = controller.object
                self.interrupted = self.paused_controller = None
                reply = (
                    f"I'll bring you the {intent.object}."
                    if intent.action == "fetch"
                    else f"I'll put the {intent.object} back in its rack."
                )
                if isinstance(controller, ToolChange):
                    reply = f"I'll put the {controller.previous_tool} back first, then " + (
                        f"bring you the {intent.object}."
                        if intent.action == "fetch"
                        else f"return the {intent.object}."
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
        last_camera = 0
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
                    bench.hold_joints()
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
                    if self.camera_hub:
                        self.camera_hub.close()
                    bench.reset(42)
                    if self.camera_tools:
                        from physical_ai_lab.assistant.camera_tasks import CameraTasks

                        self.camera_hub = CameraTasks(
                            bench, lambda: self.epoch, self.stop_event.is_set
                        )
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
                        self.timing_point("decision_ms", job)
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
                if (
                    controller.phase == "Approaching tool"
                    and "pickup_started_ms" not in self.responsiveness
                ):
                    self.timing_point("pickup_started_ms", self.job_id)
                for message in getattr(controller, "notifications", []):
                    self.add_message("assistant", message)
                if hasattr(controller, "notifications"):
                    controller.notifications.clear()
                if more:
                    with self.lock:
                        self.verified_steps = list(getattr(controller, "verified_steps", []))
                        self.phase = controller.phase
                        if self.tools and controller.object:
                            self.last_tool = controller.object
                            self.task = {
                                "object": controller.object,
                                "destination": controller.destination,
                            }
                else:
                    outcome = controller.outcome
                    self.verified_steps = list(getattr(controller, "verified_steps", []))
                    self.timing_point("task_finished_ms", self.job_id)
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
                        verified_steps=getattr(controller, "verified_steps", []),
                        camera_control=(
                            self.camera_hub.active.diagnostics()
                            if self.camera_hub
                            and self.camera_hub.active
                            and controller.object == self.camera_hub.active.object
                            else None
                        ),
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
            if self.camera_hub and self.camera_hub.active:
                self.camera_hub.active.measure()
            with self.lock:
                self.observations = {k: v.tolist() for k, v in bench.observe().items()}
                self.joint_positions = bench.data.qpos[:7].tolist()
                self.gripper_command = float(bench.data.ctrl[7])
            if time.monotonic() - last_render >= 0.09:
                buffer = io.BytesIO()
                Image.fromarray(bench.render()).save(buffer, format="JPEG", quality=87)
                with self.lock:
                    self.image = buffer.getvalue()
                last_render = time.monotonic()
            if self.vision and time.monotonic() - last_camera >= 0.5:
                views = []
                for view in ["tool_view", "tool_view_side"]:
                    buffer = io.BytesIO()
                    Image.fromarray(bench.render(view)).resize((640, 480)).save(
                        buffer, format="JPEG", quality=95
                    )
                    views.append(buffer.getvalue())
                with self.lock:
                    self.camera_image, self.camera_alternate_image = views
                    self.camera_captured_s = time.monotonic()
                last_camera = time.monotonic()
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

    @api.get("/camera.jpg")
    def camera_frame(frame: str | None = None):
        with state.lock:
            if not state.camera_answer_image:
                raise HTTPException(404, "Ask a camera question to capture a snapshot.")
            if frame and frame != state.last_camera_read["frame_sha256"]:
                raise HTTPException(409, "That snapshot was superseded by another camera answer.")
            return Response(
                state.camera_answer_image,
                media_type="image/jpeg",
                headers={"Cache-Control": "no-store"},
            )

    @api.post("/chat")
    def chat(request: ResolvedChatRequest):
        try:
            resolved = None
            if request.intent is not None:
                if not state.tools:
                    raise ValueError("Resolved tool intents require the tool scene.")
                from physical_ai_lab.assistant.tool_language import ToolIntent

                resolved = ToolIntent.parse(json.dumps(request.intent))
            state.chat(request.message, resolved)
        except ValueError as error:
            raise HTTPException(409, str(error)) from error
        return {"accepted": True, "job_id": state.job_id}

    @api.post("/understand")
    def understand(request: UnderstandingRequest):
        if not state.tools:
            raise HTTPException(409, "Dialogue during work requires the tool scene.")
        try:
            return state.understand(request.message, [r.model_dump() for r in request.history])
        except ValueError as error:
            raise HTTPException(409, str(error)) from error

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
    parser.add_argument("--model", help="MLX model folder or LM Studio model ID")
    parser.add_argument("--language-backend", choices=["mlx", "lmstudio", "codex"])
    parser.add_argument("--lmstudio-url", help="LM Studio server, default http://127.0.0.1:1234")
    parser.add_argument("--tools", action="store_true")
    parser.add_argument(
        "--camera-tools", action="store_true", help="Opt-in camera-based tool motion"
    )
    parser.add_argument("--vision-model", help="Optional already loaded LM Studio vision instance")
    parser.add_argument(
        "--vision-coordinates", choices=["normalized_xy", "grid1000_yx"], default="normalized_xy"
    )
    parser.add_argument("--log-dir", type=Path)
    parser.add_argument("--test-gripper-fault", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    from physical_ai_lab.assistant.tool_language import configure_tool_language

    try:
        if args.camera_tools and not args.tools:
            raise ValueError("Camera tool motion requires --tools")
        if args.vision_model and not args.tools:
            raise ValueError("Camera questions require --tools")
        if not args.tools and args.language_backend not in {None, "mlx"}:
            raise ValueError("External language backends currently require --tools")
        configure_tool_language(
            args.language_backend if args.tools else "mlx", args.model, args.lmstudio_url
        )
    except ValueError as error:
        parser.error(str(error))
    if not args.tools and args.model is None:
        args.model = os.environ.get("WORKBENCH_MODEL")
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
    state = Application(
        args.model, logdir / "events.jsonl", tools=args.tools, camera_tools=args.camera_tools
    )
    if args.tools:
        from physical_ai_lab.assistant.tool_scene import ToolWorkbench

        if args.camera_tools:
            from physical_ai_lab.assistant.camera_tasks import CameraTasks
            from physical_ai_lab.assistant.perception_scene import camera_scene_xml

            bench = ToolWorkbench(xml=camera_scene_xml({"layout": {}}, alternate_view=True))
            state.camera_hub = CameraTasks(bench, lambda: state.epoch, state.stop_event.is_set)
        else:
            bench = ToolWorkbench()
        state.physics_profile = bench.physics_profile
        if args.vision_model:
            from physical_ai_lab.assistant.vision_language import LMStudioVision

            state.vision = LMStudioVision(
                args.vision_model,
                os.environ.get("WORKBENCH_LMSTUDIO_URL", "http://127.0.0.1:1234"),
                compact=True,
                coordinates=args.vision_coordinates,
            )
    else:
        bench = Workbench()
    if args.test_gripper_fault:
        bench.model.actuator_forcerange[7] = [0, 0]
        state.event("verification_fault", fault="disabled gripper force")
    server = uvicorn.Server(
        uvicorn.Config(make_api(state), host="127.0.0.1", port=args.port, log_level="warning")
    )
    threading.Thread(target=server.run, daemon=True).start()
    language_thread = threading.Thread(target=state.language_worker, daemon=True)
    language_thread.start()
    # The launcher terminates owned simulators with SIGTERM. Let the native loop
    # clean up its persistent subscription child instead of abandoning it.
    signal.signal(signal.SIGTERM, lambda *_: state.closed.set())
    print(f"Workbench: http://127.0.0.1:{args.port}\nSession log: {logdir.resolve()}", flush=True)
    try:
        state.loop(bench)
    except KeyboardInterrupt:
        pass
    finally:
        state.closed.set()
        server.should_exit = True
        cancel = getattr(state.language, "cancel", None)
        if cancel:
            try:
                cancel()
            except (RuntimeError, OSError) as error:
                state.event("language_cancel_failed", error=str(error))
        language_thread.join(timeout=5)
        if state.vision:
            state.vision.close()
        if state.camera_hub:
            state.camera_hub.close()
        bench.close()


if __name__ == "__main__":
    main()
