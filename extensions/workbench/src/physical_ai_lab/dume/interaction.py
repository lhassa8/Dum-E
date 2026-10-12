"""Task-aware dialogue and explicit changes; physical skills still use the original bus."""

import asyncio
import json
import time
from dataclasses import asdict

import httpx

from physical_ai_lab.assistant.tool_language import ToolIntent
from physical_ai_lab.assistant.tool_routing import declined_tool, is_stop_request, known_intent


class InteractionCoordinator:
    def __init__(self, agent):
        self.agent = agent
        self.lock = asyncio.Lock()
        self.epoch = 0
        self.busy = False
        self.request = None
        self.clarification = None

    def snapshot(self):
        return {"busy": self.busy, "request": self.request, "clarification": self.clarification}

    def invalidate(self):
        self.epoch += 1

    def reply(self, text, message):
        self.agent.messages.extend(
            [{"role": "user", "content": text}, {"role": "assistant", "content": message}]
        )

    async def interact(self, text):
        if is_stop_request(text):
            await self.agent.cancel()
            return {"accepted": True, "mode": "stop", "task_id": None}
        epoch = self.epoch
        async with self.lock:
            if epoch != self.epoch:
                return {"accepted": False, "mode": "superseded", "task_id": None}
            self.busy, self.request = True, text
            started = time.monotonic()
            try:
                state = await self.agent.controller.state()
                records = await self.agent.task_records()
                working = state["busy"] or any(
                    t["status"] in {"pending", "running"} for t in records
                )
                decline = declined_tool(text)
                completed_fetch = state.get("last_intent") or {}
                withdraw_delivered = (
                    decline
                    and completed_fetch.get("action") == "fetch"
                    and completed_fetch.get("object") == decline
                    and state.get("inventory", {}).get(decline) == "handoff tray"
                )
                if not working and self.clarification is None and not withdraw_delivered:
                    familiar, _ = known_intent(text, state.get("recovery", {}).get("tool"))
                    if familiar and familiar.action in {"fetch", "return", "resume", "gesture"}:
                        return {
                            "accepted": True,
                            "mode": "task",
                            "task_id": await self.agent.submit(text, asdict(familiar)),
                        }
                    # Other text needs classification before it can become a
                    # physical job. Answers/clarifications do not actuate even
                    # when the arm is idle, and model decisions are reused below.
                response = await self.agent.controller.request(
                    "POST",
                    "/understand",
                    timeout=60,
                    json={
                        "message": text,
                        "history": [
                            {"role": m["role"], "content": m["content"][:1500]}
                            for m in self.agent.messages[-8:]
                        ],
                    },
                )
                interpretation = response.json()
                intent = ToolIntent.parse(json.dumps(interpretation["intent"]))
                if epoch != self.epoch:
                    return {"accepted": False, "mode": "superseded", "task_id": None}
                state = await self.agent.controller.state()
                if intent.action == "stop":
                    # Only the bounded positive Stop route can cancel immediately.
                    # A model must not turn an ambiguous/negated discussion into Stop.
                    intent = ToolIntent(
                        "clarify", None, None, "Did you want me to pause? Say stop to interrupt."
                    )
                    interpretation["intent"] = asdict(intent)
                    interpretation["route"] = "stop_clarification"
                active = state.get("last_intent") or {}
                if (
                    interpretation["route"] == "decline"
                    and active.get("action") == "fetch"
                    and active.get("object") == declined_tool(text)
                ):
                    tool = (state.get("task") or {}).get("object") or state["recovery"]["tool"]
                    intent = ToolIntent("return", tool, "rack", "")
                    interpretation["intent"] = asdict(intent)
                    interpretation["route"] = "withdraw_request"
                if intent.action in {"answer", "clarify", "unsupported", "gesture", "resume"}:
                    if not working and intent.action in {"gesture", "resume"}:
                        return {
                            "accepted": True,
                            "mode": "task",
                            "task_id": await self.agent.submit(text, asdict(intent)),
                        }
                    message = intent.message
                    if intent.action == "clarify":
                        self.clarification = {"request": text, "question": message}
                    if intent.action == "resume":
                        message = (
                            "I'm already working. You can ask what I'm doing or change the tool."
                        )
                    elif intent.action == "gesture":
                        message = "Hello! I'm keeping the arm on this task while we talk."
                    self.reply(text, message or "Which tool would you like next?")
                    result = {
                        "accepted": True,
                        "mode": "conversation",
                        "task_id": None,
                        "message": message,
                        **interpretation,
                    }
                else:
                    self.clarification = None
                    if state["busy"] and all(
                        active.get(k) == getattr(intent, k)
                        for k in ("action", "object", "destination")
                    ):
                        message = (
                            f"I'm already working on the {intent.object}: {state['phase'].lower()}."
                        )
                        self.reply(text, message)
                        result = {
                            "accepted": True,
                            "mode": "conversation",
                            "task_id": None,
                            "message": message,
                            **interpretation,
                        }
                    else:
                        queued = any(
                            t["status"] in {"pending", "running"}
                            for t in await self.agent.task_records()
                        )
                        if state["busy"] or self.agent.active_id or queued:
                            await self.agent.cancel(invalidate_interaction=False)
                            deadline = time.monotonic() + 5
                            while time.monotonic() < deadline:
                                state = await self.agent.controller.state()
                                if (
                                    not state["busy"]
                                    and state["phase"] == "Stopped"
                                    and not self.agent.active_id
                                ):
                                    break
                                await asyncio.sleep(0.025)
                            else:
                                raise RuntimeError(
                                    "The arm hasn't confirmed a stop. "
                                    "The new request hasn't started."
                                )
                        if epoch != self.epoch:
                            return {"accepted": False, "mode": "superseded", "task_id": None}
                        result = {
                            "accepted": True,
                            "mode": "change",
                            "task_id": await self.agent.submit(text, asdict(intent)),
                            **interpretation,
                        }
                self.agent.log_interaction(text, result, (time.monotonic() - started) * 1000)
                return result
            except httpx.HTTPError:
                if epoch != self.epoch:
                    return {"accepted": False, "mode": "superseded", "task_id": None}
                raise
            finally:
                self.busy, self.request = False, None
