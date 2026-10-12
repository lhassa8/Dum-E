"""Subscription-backed intent inference through the official signed-in Codex CLI."""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from physical_ai_lab.assistant.lmstudio import INTENT_SCHEMA


class CodexLanguage:
    def __init__(self, system, parser, runner=None):
        self.executable = shutil.which(os.environ.get("WORKBENCH_CODEX_BIN", "codex"))
        if not self.executable:
            raise RuntimeError("Codex CLI is missing. Install Codex and sign in with ChatGPT.")
        self.path = "gpt-6-luna"
        self.parser = parser
        self.runner = runner or subprocess.run
        self.directory = tempfile.TemporaryDirectory(prefix="dume-luna-")
        self.workspace = Path(self.directory.name)
        self.schema = self.workspace / "intent-schema.json"
        self.schema.write_text(json.dumps(INTENT_SCHEMA))
        self.instructions = self.workspace / "instructions.txt"
        self.instructions.write_text(system)
        self.last_profile = {}
        started = time.perf_counter()
        try:
            self.interpret("What can you help me with?", observations={})
        except BaseException:
            self.close()
            raise
        self.startup_warmup_ms = (time.perf_counter() - started) * 1000
        self.last_profile = {}

    def close(self):
        self.directory.cleanup()

    def interpret(self, request, history=(), observations=None):
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
