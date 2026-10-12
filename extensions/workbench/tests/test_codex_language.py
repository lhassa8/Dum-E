"""Subscription transport rejects failed, tool-using and incomplete replies."""

import json
import subprocess
from types import SimpleNamespace

import pytest

from physical_ai_lab.assistant.codex_language import CodexLanguage
from physical_ai_lab.assistant.tool_language import TOOL_SYSTEM, ToolIntent

ANSWER = '{"action":"answer","object":null,"destination":null,"message":"Hello."}'


def result(events=None, returncode=0):
    events = (
        events
        if events is not None
        else [
            {"type": "item.completed", "item": {"type": "agent_message", "text": ANSWER}},
            {"type": "turn.completed", "usage": {"input_tokens": 100}},
        ]
    )
    return SimpleNamespace(
        stdout="\n".join(json.dumps(e) for e in events), stderr="", returncode=returncode
    )


def test_subscription_argv_auth_and_context_are_isolated(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/verified/codex")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-inherited")
    seen = []

    def run(command, **kwargs):
        seen.append((command, kwargs))
        return result()

    backend = CodexLanguage(TOOL_SYSTEM, ToolIntent.parse, runner=run)
    try:
        backend.interpret("First", [{"role": "assistant", "content": "Old context"}], {"rack": 1})
        intent, _ = backend.interpret("Second", observations={"rack": 2})
        assert intent.action == "answer"
        command, kwargs = seen[-1]
        assert command[command.index("--model") + 1] == "gpt-6-luna"
        assert 'forced_login_method="chatgpt"' in command
        assert "--ignore-user-config" in command and "--ephemeral" in command
        assert "shell_tool" in command and "multi_agent" in command
        assert "OPENAI_API_KEY" not in kwargs["env"]
        assert kwargs["start_new_session"]
        assert "Old context" not in kwargs["input"]
        assert json.loads(backend.schema.read_text())["additionalProperties"] is False
        assert backend.instructions.read_text() == TOOL_SYSTEM
        assert backend.last_profile["authentication"] == "chatgpt"
    finally:
        workspace = backend.workspace
        backend.close()
        assert not workspace.exists()


def test_timeout_is_bounded_and_next_request_can_recover(monkeypatch):
    from fastapi.testclient import TestClient

    from physical_ai_lab.assistant.app import Application, make_api

    monkeypatch.setattr("shutil.which", lambda _: "/verified/codex")
    calls = 0

    def run(command, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return result()

    backend = CodexLanguage(TOOL_SYSTEM, ToolIntent.parse, runner=run)
    app = Application(tools=True)
    app.language, app.model_status = backend, "ready"
    client = TestClient(make_api(app))
    try:
        failed = client.post("/understand", json={"message": "Tell me a story"})
        assert failed.status_code == 409 and "30 seconds" in failed.json()["detail"]
        assert app.commands.empty() and app.requests.empty() and app.job_id is None
        recovered = client.post("/understand", json={"message": "How was your day?"})
        assert recovered.status_code == 200
        assert recovered.json()["intent"]["action"] == "answer"
        assert calls == 3  # No automatic retry consumes subscription allowance.
    finally:
        backend.close()


@pytest.mark.parametrize(
    "bad",
    [
        result(returncode=1),
        result([{"type": "turn.failed"}]),
        result([{"type": "item.completed", "item": {"type": "agent_message", "text": ANSWER}}]),
        result(
            [
                {"type": "item.completed", "item": {"type": "command_execution"}},
                {"type": "turn.completed"},
            ]
        ),
    ],
)
def test_failed_or_unexpected_cli_results_do_not_become_intents(monkeypatch, bad):
    monkeypatch.setattr("shutil.which", lambda _: "/verified/codex")
    calls = []

    def run(*args, **kwargs):
        calls.append(args)
        return result() if len(calls) == 1 else bad

    backend = CodexLanguage(TOOL_SYSTEM, ToolIntent.parse, runner=run)
    try:
        with pytest.raises(RuntimeError):
            backend.interpret("Bring a tool")
        assert len(calls) == 2  # Never silently retry, change models or use API-key billing.
    finally:
        backend.close()
