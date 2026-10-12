"""External inference must fail closed and cannot resurrect cancelled motion."""

import json
import threading
import time

import httpx
import pytest

from physical_ai_lab.assistant.app import Application
from physical_ai_lab.assistant.lmstudio import LMStudioLanguage
from physical_ai_lab.assistant.tool_language import TOOL_SYSTEM, ToolIntent, make_tool_language

MODEL = "qwen/qwen3.8-27b"
ANSWER = '{"action":"answer","object":null,"destination":null,"message":"Hello."}'


def stream(raw=ANSWER, reason="stop", done=True):
    chunks = [
        {"choices": [{"delta": {"reasoning_content": "Ignored reasoning"}}]},
        {"choices": [{"delta": {"content": raw[:15]}}]},
        {"choices": [{"delta": {"content": raw[15:]}, "finish_reason": reason}]},
    ]
    data = "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks)
    if done:
        data += "data: [DONE]\n\n"
    return httpx.Response(200, text=data, headers={"Content-Type": "text/event-stream"})


def language(handler):
    return LMStudioLanguage(
        TOOL_SYSTEM, ToolIntent.parse, model=MODEL, transport=httpx.MockTransport(handler)
    )


def test_http_backend_isolates_history_and_scene_and_validates_full_response():
    seen = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": MODEL}]})
        seen.append(json.loads(request.content))
        return stream()

    backend = language(handler)
    try:
        intent, _ = backend.interpret(
            "First request", [{"role": "assistant", "content": "First context"}], {"rack": 1}
        )
        assert intent.action == "answer"
        backend.interpret("Second request", observations={"rack": 2})
        assert "First context" in json.dumps(seen[-2])
        assert "First context" not in json.dumps(seen[-1])
        assert '\\"rack\\": 2' in json.dumps(seen[-1])
        assert seen[-1]["reasoning_effort"] == "none"
        assert backend.last_profile["first_token_ms"] is not None
    finally:
        backend.close()


@pytest.mark.parametrize(
    "bad",
    [
        lambda: stream(done=False),
        lambda: stream(reason="length"),
        lambda: stream('{"action":"fetch","object":"drill","destination":"handoff"}'),
        lambda: httpx.Response(503, text="Unavailable"),
        lambda: httpx.Response(200, text='data: {"error":"Failure"}\n\n'),
    ],
)
def test_incomplete_unknown_and_failed_http_results_never_become_intents(bad):
    calls = 0

    def handler(request):
        nonlocal calls
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": MODEL}]})
        calls += 1
        return stream() if calls == 1 else bad()

    backend = language(handler)
    try:
        with pytest.raises((RuntimeError, ValueError, httpx.HTTPStatusError)):
            backend.interpret("Bring a tool")
        assert calls == 2  # No automatic retry or silent alternate model.
    finally:
        backend.close()


def test_ready_requires_selected_model_and_real_warmup():
    def handler(request):
        return httpx.Response(200, json={"data": [{"id": "different-model"}]})

    with pytest.raises(RuntimeError, match="requested model"):
        language(handler)


def test_cancelled_remote_reply_cannot_enqueue_motion(monkeypatch):
    entered, release = threading.Event(), threading.Event()
    calls = 0

    def handler(request):
        nonlocal calls
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": MODEL}]})
        calls += 1
        if calls == 1:
            return stream()
        entered.set()
        assert release.wait(3)
        return stream(
            '{"action":"fetch","object":"screwdriver","destination":"handoff","message":""}'
        )

    backend = language(handler)
    monkeypatch.setattr(
        "physical_ai_lab.assistant.tool_language.make_tool_language", lambda _: backend
    )
    app = Application(tools=True)
    worker = threading.Thread(target=app.language_worker)
    worker.start()
    try:
        deadline = time.monotonic() + 2
        while app.model_status == "loading" and time.monotonic() < deadline:
            time.sleep(0.01)
        app.chat("I need something for turning screws")
        assert entered.wait(2)
        app.stop()
        assert app.commands.get_nowait()[0] == "stop"
        app.closed.set()
        release.set()
        worker.join(3)
        assert not worker.is_alive()
        assert app.commands.empty()
        assert backend.client.is_closed
    finally:
        app.closed.set()
        release.set()
        worker.join(3)


def test_backend_configuration_rejects_unknown_values(monkeypatch):
    monkeypatch.setenv("WORKBENCH_LANGUAGE_BACKEND", "typo")
    with pytest.raises(ValueError, match="mlx, lmstudio or codex"):
        make_tool_language()


def test_launcher_does_not_silently_reuse_the_wrong_backend_or_model(monkeypatch, tmp_path):
    from physical_ai_lab.dume.app import ensure_simulator

    state = {
        "backend": "workbench",
        "last_outcome": None,
        "busy": False,
        "profile": "tools",
        "language_backend": "mlx",
        "language_model": "local-mlx-model",
    }
    monkeypatch.setattr(
        "physical_ai_lab.dume.app.httpx.get",
        lambda *a, **kw: httpx.Response(200, json=state, request=httpx.Request("GET", a[0])),
    )
    monkeypatch.setenv("WORKBENCH_LANGUAGE_BACKEND", "lmstudio")
    monkeypatch.setenv("WORKBENCH_LMSTUDIO_MODEL", MODEL)
    with pytest.raises(RuntimeError, match="different language backend"):
        ensure_simulator(8775, tmp_path, tools=True)
    state["language_backend"] = "lmstudio"
    with pytest.raises(RuntimeError, match="different LM Studio model"):
        ensure_simulator(8775, tmp_path, tools=True)
    state["language_model"] = MODEL
    assert ensure_simulator(8775, tmp_path, tools=True) is None
