"""Session reuse must isolate requests and reject cancelled/unauthorized output."""

import json
import queue
import threading

import pytest

from physical_ai_lab.assistant.codex_language import CodexLanguage
from physical_ai_lab.assistant.tool_language import TOOL_SYSTEM, ToolIntent


class SessionProbe:
    def __init__(self, *args):
        self.events = queue.Queue()
        self.calls, self.sent = [], []
        self.number = 0
        self.model = "gpt-6-luna"
        self.mode = "complete"
        self.entered = threading.Event()
        self.closed = False

    def call(self, method, params, **kwargs):
        self.calls.append((method, params))
        if method == "thread/start":
            self.number += 1
            return {
                "model": self.model,
                "modelProvider": "openai",
                "thread": {"id": str(self.number)},
            }
        tid = params["threadId"]
        self.entered.set()
        if self.mode == "complete":
            raw = json.dumps(
                {"action": "answer", "object": None, "destination": None, "message": "Hello."}
            )
            # Late data from another thread must not influence the current result.
            self.events.put(
                {
                    "method": "item/completed",
                    "params": {
                        "threadId": "stale",
                        "item": {"type": "agentMessage", "text": "invalid"},
                    },
                }
            )
            self.events.put(
                {
                    "method": "item/agentMessage/delta",
                    "params": {"threadId": tid, "delta": '{"action":'},
                }
            )
            self.events.put(
                {
                    "method": "item/completed",
                    "params": {"threadId": tid, "item": {"type": "agentMessage", "text": raw}},
                }
            )
            self.events.put(
                {
                    "method": "turn/completed",
                    "params": {"threadId": tid, "turn": {"status": "completed"}},
                }
            )
        elif self.mode == "tool":
            self.events.put(
                {
                    "method": "item/started",
                    "params": {"threadId": tid, "item": {"type": "commandExecution"}},
                }
            )
        return {"turn": {"id": "turn-" + tid}}

    def fire(self, method, params):
        self.sent.append((method, params))
        if method == "turn/interrupt":
            self.events.put(
                {
                    "method": "turn/completed",
                    "params": {"threadId": params["threadId"], "turn": {"status": "interrupted"}},
                }
            )

    def close(self):
        self.closed = True


def model(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda _: "/verified/codex")
    return CodexLanguage(
        TOOL_SYSTEM, ToolIntent.parse, session_factory=SessionProbe, transport="session"
    )


def test_requests_reuse_connection_but_not_hidden_conversation(monkeypatch):
    backend = model(monkeypatch)
    try:
        session = backend.session
        backend.interpret("First", [{"role": "assistant", "content": "old"}], {"rack": 1})
        answer, _ = backend.interpret("Second", observations={"rack": 2})
        assert answer.message == "Hello."
        assert backend.session is session
        starts = [p for m, p in session.calls if m == "thread/start"]
        assert all(p["ephemeral"] and not p["allowProviderModelFallback"] for p in starts)
        turns = [p for m, p in session.calls if m == "turn/start"]
        assert "old" not in turns[-1]["input"][0]["text"]
        assert backend.last_profile["first_token_ms"] is not None
        assert sum(m == "thread/unsubscribe" for m, _ in session.sent) == 3
    finally:
        backend.close()
        assert session.closed


def test_interrupt_releases_pending_interpretation_without_an_intent(monkeypatch):
    backend = model(monkeypatch)
    session = backend.session
    session.mode = "pending"
    session.entered.clear()
    outcomes = []

    def interpret():
        try:
            outcomes.append(backend.interpret("Bring another tool"))
        except RuntimeError as error:
            outcomes.append(error)

    worker = threading.Thread(target=interpret)
    try:
        worker.start()
        assert session.entered.wait(2)
        backend.cancel()
        worker.join(2)
        assert not worker.is_alive()
        assert len(outcomes) == 1 and isinstance(outcomes[0], RuntimeError)
        session.mode = "complete"
        assert backend.interpret("How are you?")[0].action == "answer"
    finally:
        backend.cancel()
        worker.join(2)
        backend.close()


@pytest.mark.parametrize("failure", ["tool", "different-model"])
def test_tools_and_model_substitutions_fail_closed(monkeypatch, failure):
    backend = model(monkeypatch)
    try:
        if failure == "tool":
            backend.session.mode = "tool"
        else:
            backend.session.model = "different-model"
        with pytest.raises(RuntimeError):
            backend.interpret("Do something")
    finally:
        backend.close()


def test_deadline_interrupts_without_retry(monkeypatch):
    class EmptyQueue(queue.Queue):
        def get(self, **kwargs):
            raise queue.Empty()

    backend = model(monkeypatch)
    try:
        backend.session.events = EmptyQueue()
        backend.session.mode = "pending"
        with pytest.raises(RuntimeError, match="30 seconds"):
            backend.interpret("Tell a story")
        assert sum(m == "turn/start" for m, _ in backend.session.calls) == 2
        assert any(m == "turn/interrupt" for m, _ in backend.session.sent)
    finally:
        backend.close()


class ProtocolChild:
    """Exercise the real RPC reader without sign-in, network or subprocesses."""

    def __init__(self, account_type="chatgpt"):
        self.incoming = queue.Queue()
        self.messages = []
        self.account_type = account_type
        self.stdin, self.stdout = self, self
        self.exited = False

    def write(self, line):
        request = json.loads(line)
        self.messages.append(request)
        if "method" not in request or "id" not in request:
            return
        result = {}
        if request["method"] == "account/read":
            result = {"account": {"type": self.account_type}}
        self.incoming.put(json.dumps({"id": request["id"], "result": result}) + "\n")

    def flush(self):
        pass

    def __iter__(self):
        while (line := self.incoming.get()) is not None:
            yield line

    def poll(self):
        return 0 if self.exited else None

    def terminate(self):
        self.exited = True
        self.incoming.put(None)

    def wait(self, **kwargs):
        return 0

    def close(self):
        pass


@pytest.mark.parametrize("account_type", ["chatgpt", "apiKey"])
def test_rpc_auth_and_host_tools_are_isolated(monkeypatch, tmp_path, account_type):
    from physical_ai_lab.assistant.subscription_session import SubscriptionSession

    config = tmp_path / "config.toml"
    config.write_text('[mcp_servers.example]\ncommand="unused"\n')
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-sent")
    child = ProtocolChild(account_type)
    captured = []

    def launch(command, **kwargs):
        captured.append((command, kwargs))
        return child

    monkeypatch.setattr("subprocess.Popen", launch)
    if account_type == "apiKey":
        with pytest.raises(RuntimeError, match="ChatGPT sign-in"):
            SubscriptionSession("/verified/codex", tmp_path)
        assert child.exited
    else:
        session = SubscriptionSession("/verified/codex", tmp_path)
        try:
            child.incoming.put(json.dumps({
                "id": "approval-1", "method": "item/commandExecution/requestApproval",
                "params": {},
            }) + "\n")
            assert session.events.get(timeout=2)["method"] == "dume/toolRejected"
            denied = next(m for m in child.messages if m.get("id") == "approval-1")
            assert denied["error"]["code"] == -32601
        finally:
            session.close()
        assert child.exited and not session.reader.is_alive()
    command, options = captured[0]
    assert 'forced_login_method="chatgpt"' in command
    assert "mcp_servers.example.enabled=false" in command
    assert "OPENAI_API_KEY" not in options["env"]
    assert options["start_new_session"]
    assert config.read_text() == '[mcp_servers.example]\ncommand="unused"\n'
