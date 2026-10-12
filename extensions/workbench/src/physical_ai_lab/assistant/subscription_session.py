"""Persistent official Codex app-server transport using ChatGPT sign-in."""

import json
import os
import queue
import re
import subprocess
import threading
import tomllib
from pathlib import Path

DISABLED_FEATURES = (
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
    "goals",
    "sleep_tool",
    "tool_suggest",
    "auth_elicitation",
)


class SubscriptionSession:
    def __init__(self, executable, workspace):
        self.pending, self.events = {}, queue.Queue()
        self.lock = threading.Lock()
        self.next_id = 0
        self.closed = False
        config_path = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "config.toml"
        config = tomllib.loads(config_path.read_text()) if config_path.exists() else {}
        command = [executable, "app-server", "--stdio"]
        overrides = {
            "forced_login_method": "chatgpt",
            "model_provider": "openai",
            "web_search": "disabled",
            "project_doc_max_bytes": 0,
            "analytics.enabled": False,
            # This interpreter cannot invoke skills. Avoid sending the host's
            # large coding-skill catalog on every workbench utterance.
            "skills.max_context_tokens": 1,
        }
        for name in config.get("mcp_servers", {}):
            if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                raise RuntimeError(
                    "Unsupported MCP configuration name; cannot isolate conversation"
                )
            overrides[f"mcp_servers.{name}.enabled"] = False
        for key, value in overrides.items():
            command.extend(["-c", key + "=" + json.dumps(value)])
        for feature in DISABLED_FEATURES:
            command.extend(["--disable", feature])
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {"OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL"}
        }
        self.process = subprocess.Popen(
            command,
            cwd=workspace,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self.call(
                "initialize",
                {
                    "clientInfo": {
                        "name": "dume_workbench",
                        "title": "Dum-E Workbench",
                        "version": "0.1.0",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            )
            self.send({"method": "initialized", "params": {}})
            account = self.call("account/read", {"refreshToken": False})
            if (account.get("account") or {}).get("type") != "chatgpt":
                raise RuntimeError("Dum-E requires ChatGPT sign-in; API-key billing is disabled")
        except BaseException:
            self.close()
            raise

    def send(self, message):
        with self.lock:
            if self.closed or self.process.poll() is not None:
                raise RuntimeError("Codex subscription session is offline")
            self.process.stdin.write(json.dumps(message) + "\n")
            self.process.stdin.flush()

    def call(self, method, params, timeout=30):
        response = queue.Queue()
        with self.lock:
            self.next_id += 1
            identity = self.next_id
            self.pending[identity] = response
        try:
            self.send({"id": identity, "method": method, "params": params})
            try:
                message = response.get(timeout=timeout)
            except queue.Empty as error:
                raise TimeoutError("Codex subscription RPC timed out") from error
            if "error" in message:
                raise RuntimeError("Codex subscription request failed: " + str(message["error"]))
            return message["result"]
        finally:
            with self.lock:
                self.pending.pop(identity, None)

    def fire(self, method, params):
        with self.lock:
            self.next_id += 1
            identity = self.next_id
        self.send({"id": identity, "method": method, "params": params})

    def _read(self):
        try:
            for line in self.process.stdout:
                message = json.loads(line)
                if "method" in message and "id" in message:
                    # This model is an interpreter, never an autonomous tool operator.
                    self.send(
                        {
                            "id": message["id"],
                            "error": {
                                "code": -32601,
                                "message": "Tool operations are disabled for conversation",
                            },
                        }
                    )
                    self.events.put({"method": "dume/toolRejected", "params": message})
                elif "method" in message:
                    self.events.put(message)
                else:
                    with self.lock:
                        response = self.pending.get(message.get("id"))
                    if response is not None:
                        response.put(message)
        except (ValueError, OSError, RuntimeError):
            pass
        finally:
            failure = {"error": {"message": "Codex subscription session closed"}}
            with self.lock:
                for response in self.pending.values():
                    response.put(failure)
            self.events.put({"method": "dume/closed", "params": {}})

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        self.reader.join(timeout=3)
        self.process.stdin.close()
        self.process.stdout.close()
