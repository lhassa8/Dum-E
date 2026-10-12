"""Subscription-backed intent inference through the official signed-in Codex CLI."""

import json
import os
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from physical_ai_lab.assistant.lmstudio import INTENT_SCHEMA


class CodexLanguage:
    def __init__(self, system, parser, runner=None, session_factory=None, transport=None):
        self.executable = shutil.which(os.environ.get("WORKBENCH_CODEX_BIN", "codex"))
        if not self.executable:
            raise RuntimeError("Codex CLI is missing. Install Codex and sign in with ChatGPT.")
        self.path = "gpt-6-luna"
        self.parser = parser
        self.system = system
        self.runner = runner or subprocess.run
        self.transport = transport or (
            "exec" if runner else os.environ.get("WORKBENCH_CODEX_TRANSPORT", "session")
        )
        if self.transport not in {"exec", "session"}:
            raise ValueError("WORKBENCH_CODEX_TRANSPORT must be exec or session")
        self.session = None
        self.active_lock = threading.Lock()
        self.active = None
        self.generation = 0
        self.directory = tempfile.TemporaryDirectory(prefix="dume-luna-")
        self.workspace = Path(self.directory.name)
        self.schema = self.workspace / "intent-schema.json"
        self.schema.write_text(json.dumps(INTENT_SCHEMA))
        self.instructions = self.workspace / "instructions.txt"
        self.instructions.write_text(system)
        self.last_profile = {}
        started = time.perf_counter()
        try:
            if self.transport == "session":
                from physical_ai_lab.assistant.subscription_session import SubscriptionSession

                factory = session_factory or SubscriptionSession
                self.session = factory(self.executable, self.workspace)
            self.interpret("What can you help me with?", observations={})
        except BaseException:
            self.close()
            raise
        self.startup_warmup_ms = (time.perf_counter() - started) * 1000
        self.last_profile = {}

    def close(self):
        if self.session is not None:
            self.session.close()
        self.directory.cleanup()

    def interpret(self, request, history=(), observations=None):
        if self.transport == "session":
            return self._session_interpret(request, history, observations)
        return self._exec_interpret(request, history, observations)

    def cancel(self):
        with self.active_lock:
            self.generation += 1
            active = self.active
        if self.session is not None and active and active[1]:
            self.session.fire("turn/interrupt", {"threadId": active[0], "turnId": active[1]})

    def _session_interpret(self, request, history=(), observations=None):
        started = time.perf_counter()
        deadline = started + 30
        with self.active_lock:
            generation = self.generation
        thread_id = None
        raw, usage, first_token_ms = None, {}, None
        try:
            thread = self.session.call(
                "thread/start",
                {
                    "model": self.path,
                    "modelProvider": "openai",
                    "allowProviderModelFallback": False,
                    "ephemeral": True,
                    "cwd": str(self.workspace),
                    "sandbox": "read-only",
                    "approvalPolicy": "untrusted",
                    "baseInstructions": self.system,
                    "developerInstructions": (
                        "Interpret only supplied request/context data. Never use tools."
                    ),
                    "dynamicTools": [],
                    "environments": [],
                },
                timeout=max(0.001, deadline - time.perf_counter()),
            )
            thread_id = thread["thread"]["id"]
            if thread["model"] != self.path or thread["modelProvider"] != "openai":
                raise RuntimeError(
                    "Codex selected a different model/provider; refusing interpretation"
                )
            with self.active_lock:
                if generation != self.generation:
                    raise RuntimeError("Luna interpretation was cancelled")
                self.active = (thread_id, None)
            payload = json.dumps(
                {
                    "request": request,
                    "history": list(history[-8:]),
                    "observations": observations,
                }
            )
            turn = self.session.call(
                "turn/start",
                {
                    "threadId": thread_id,
                    "input": [
                        {
                            "type": "text",
                            "text": "Interpret these request/context data only:\n" + payload,
                        }
                    ],
                    "model": self.path,
                    "effort": "low",
                    "outputSchema": INTENT_SCHEMA,
                },
                timeout=max(0.001, deadline - time.perf_counter()),
            )
            with self.active_lock:
                self.active = (thread_id, turn["turn"]["id"])
                cancelled = generation != self.generation
            if cancelled:
                self.session.fire(
                    "turn/interrupt",
                    {
                        "threadId": thread_id,
                        "turnId": turn["turn"]["id"],
                    },
                )
                raise RuntimeError("Luna interpretation was cancelled")
            while True:
                remaining = deadline - time.perf_counter()
                if remaining <= 0:
                    raise TimeoutError("Luna interpretation exceeded 30 seconds")
                try:
                    event = self.session.events.get(timeout=remaining)
                except queue.Empty as error:
                    raise TimeoutError("Luna interpretation exceeded 30 seconds") from error
                method, params = event["method"], event.get("params", {})
                if method in {"dume/closed", "dume/toolRejected"}:
                    raise RuntimeError(
                        "Codex conversation session closed or attempted a tool operation"
                    )
                if params.get("threadId") != thread_id:
                    continue
                if method == "item/agentMessage/delta" and first_token_ms is None:
                    first_token_ms = (time.perf_counter() - started) * 1000
                if method == "item/started" and params["item"]["type"] not in {
                    "agentMessage",
                    "userMessage",
                    "reasoning",
                }:
                    raise RuntimeError("Luna attempted a tool operation instead of interpretation")
                if method == "item/completed" and params["item"]["type"] == "agentMessage":
                    raw = params["item"]["text"]
                if method == "thread/tokenUsage/updated":
                    usage = params["tokenUsage"]["last"]
                if method == "turn/completed":
                    with self.active_lock:
                        cancelled = generation != self.generation
                    if cancelled or params["turn"]["status"] != "completed" or not raw:
                        raise RuntimeError("Luna interpretation was cancelled or incomplete")
                    break
            self.last_profile = {
                "backend": "codex",
                "transport": "session",
                "model": self.path,
                "authentication": "chatgpt",
                "first_token_ms": first_token_ms,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "usage": usage,
                "scope": "Subscription session to complete interpretation; no speech/motion",
            }
            return self.parser(raw), raw
        except TimeoutError as error:
            self.cancel()
            raise RuntimeError(
                "GPT-6 Luna did not respond within 30 seconds. Try again."
            ) from error
        except RuntimeError:
            self.cancel()
            raise
        finally:
            with self.active_lock:
                self.active = None
            if thread_id:
                try:
                    self.session.fire("thread/unsubscribe", {"threadId": thread_id})
                except (RuntimeError, OSError):
                    pass

    def _exec_interpret(self, request, history=(), observations=None):
        # Use the official CLI auth flow; never read or extract login tokens.
        command = [
            self.executable,
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--model",
            self.path,
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--cd",
            str(self.workspace),
            "--output-schema",
            str(self.schema),
            "--json",
        ]
        for key, value in {
            "forced_login_method": "chatgpt",
            "model_provider": "openai",
            "model_reasoning_effort": "low",
            "model_instructions_file": str(self.instructions),
            "project_doc_max_bytes": 0,
            "web_search": "disabled",
        }.items():
            # JSON is TOML-compatible for these scalar values; this is an argv
            # list passed directly to subprocess, never shell interpolation.
            command.extend(["-c", key + "=" + json.dumps(value)])
        for feature in [
            "shell_tool",
            "unified_exec",
            "code_mode",
            "code_mode_host",
            "apps",
            "plugins",
            "hooks",
            "multi_agent",
            "browser_use",
            "computer_use",
            "image_generation",
            "view_image",
            "workspace_dependencies",
            "skill_search",
            "memories",
        ]:
            command.extend(["--disable", feature])
        command.append("-")
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {"OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"}
        }
        payload = json.dumps(
            {
                "request": request,
                "history": list(history[-8:]),
                "observations": observations,
            }
        )
        started = time.perf_counter()
        try:
            result = self.runner(
                command,
                input="Interpret these request/context data only:\n" + payload,
                text=True,
                capture_output=True,
                timeout=30,
                env=env,
                start_new_session=True,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                "GPT-6 Luna did not respond within 30 seconds. Try again."
            ) from error
        if result.returncode:
            raise RuntimeError("Codex Luna inference failed; check ChatGPT sign-in and allowance.")
        raw, completed, usage = None, False, {}
        for line in result.stdout.splitlines():
            event = json.loads(line)
            if event.get("type") == "item.completed":
                item = event.get("item", {})
                if item.get("type") == "agent_message":
                    raw = item["text"]
                elif item.get("type") not in {"error", "reasoning"}:
                    raise RuntimeError("Conversation model attempted an unexpected tool operation")
            elif event.get("type") == "turn.completed":
                completed, usage = True, event.get("usage", {})
            elif event.get("type") in {"turn.failed", "error"}:
                raise RuntimeError("Codex Luna did not complete interpretation")
        if not completed or not raw:
            raise RuntimeError("Codex Luna returned no completed intent")
        self.last_profile = {
            "backend": "codex",
            "model": self.path,
            "authentication": "chatgpt",
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "usage": usage,
            "scope": "CLI startup plus completed text inference; excludes speech and motion",
        }
        return self.parser(raw), raw
