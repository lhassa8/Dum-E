"""External inference must fail closed and cannot resurrect cancelled motion."""

import json
import os
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
        "physics_profile": "tool_contacts_v2",
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
    state["language_endpoint"] = "http://127.0.0.1:1234"
    assert ensure_simulator(8775, tmp_path, tools=True) is None
    monkeypatch.setenv("WORKBENCH_LMSTUDIO_URL", "http://127.0.0.1:4321")
    with pytest.raises(RuntimeError, match="different or unverified LM Studio server"):
        ensure_simulator(8775, tmp_path, tools=True)


def test_selected_model_is_configurable_without_inheriting_a_local_model_folder(monkeypatch):
    from physical_ai_lab.assistant.tool_language import configure_tool_language

    selected = "example/tool-helper-4b"
    monkeypatch.setenv("WORKBENCH_MODEL", "/previous/local/mlx/model")
    monkeypatch.setenv("WORKBENCH_LANGUAGE_BACKEND", "mlx")
    monkeypatch.setenv("WORKBENCH_LMSTUDIO_MODEL", "old-model")
    monkeypatch.setenv("WORKBENCH_LMSTUDIO_URL", "http://old.invalid")
    configure_tool_language("lmstudio", selected, "http://127.0.0.1:1234/v1/")
    seen = []

    def factory(**kwargs):
        seen.append(kwargs)
        return object()

    monkeypatch.setattr("physical_ai_lab.assistant.lmstudio.LMStudioLanguage", factory)
    make_tool_language()
    assert seen[-1]["model"] is None  # Adapter reads the selected provider's environment.
    assert os.environ["WORKBENCH_LMSTUDIO_MODEL"] == selected
    assert os.environ["WORKBENCH_LMSTUDIO_URL"] == "http://127.0.0.1:1234"
    make_tool_language("explicit/another-model")
    assert seen[-1]["model"] == "explicit/another-model"


@pytest.mark.parametrize("backend,model,url", [
    ("codex", "different-model", None),
    ("mlx", None, "http://127.0.0.1:1234"),
    ("lmstudio", "", None),
    ("lmstudio", "selected", "http://secret@127.0.0.1:1234"),
])
def test_invalid_cli_configuration_does_not_partially_change_the_provider(
    monkeypatch, backend, model, url
):
    from physical_ai_lab.assistant.tool_language import configure_tool_language

    monkeypatch.setenv("WORKBENCH_LANGUAGE_BACKEND", "mlx")
    before = dict(os.environ)
    with pytest.raises(ValueError):
        configure_tool_language(backend, model, url)
    assert dict(os.environ) == before


def test_missing_model_selection_does_not_guess_or_load_another_model(monkeypatch):
    monkeypatch.delenv("WORKBENCH_LMSTUDIO_MODEL", raising=False)
    with pytest.raises(ValueError, match="Choose an LM Studio model"):
        LMStudioLanguage(TOOL_SYSTEM, ToolIntent.parse)


def test_different_returned_model_is_rejected_before_creating_an_intent():
    calls = 0

    def handler(request):
        nonlocal calls
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": MODEL}]})
        calls += 1
        if calls == 1:
            return stream()
        data = "data: " + json.dumps({
            "model": "substituted-model",
            "choices": [{"delta": {"content": ANSWER}, "finish_reason": "stop"}],
        }) + "\n\ndata: [DONE]\n\n"
        return httpx.Response(200, text=data)

    backend = language(handler)
    try:
        with pytest.raises(RuntimeError, match="different model"):
            backend.interpret("Bring a tool")
        assert calls == 2
    finally:
        backend.close()


def test_server_timeout_is_explicit_and_next_request_recovers_without_queued_motion():
    from fastapi.testclient import TestClient

    from physical_ai_lab.assistant.app import make_api

    calls = 0

    def handler(request):
        nonlocal calls
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": MODEL}]})
        calls += 1
        if calls == 2:
            raise httpx.ReadTimeout("Stalled stream", request=request)
        return stream()

    backend = language(handler)
    app = Application(tools=True)
    app.language, app.model_status = backend, "ready"
    client = TestClient(make_api(app))
    try:
        failed = client.post("/understand", json={"message": "Tell me a story"})
        assert failed.status_code == 409 and "LM Studio" in failed.json()["detail"]
        assert app.commands.empty() and app.requests.empty() and app.job_id is None
        recovered = client.post("/understand", json={"message": "How are you?"})
        assert recovered.status_code == 200 and recovered.json()["intent"]["action"] == "answer"
        assert calls == 3  # No automatic inference retry or model substitution.
    finally:
        backend.close()


def test_explicit_local_model_choice_is_not_silently_ignored_by_reuse(monkeypatch, tmp_path):
    from physical_ai_lab.dume.app import ensure_simulator

    state = {
        "backend": "workbench", "last_outcome": None, "busy": False, "profile": "tools",
        "language_backend": "mlx", "language_model": str(tmp_path / "old-model"),
        "physics_profile": "tool_contacts_v2",
    }
    monkeypatch.setattr(
        "physical_ai_lab.dume.app.httpx.get",
        lambda *a, **kw: httpx.Response(200, json=state, request=httpx.Request("GET", a[0])),
    )
    monkeypatch.setenv("WORKBENCH_LANGUAGE_BACKEND", "mlx")
    monkeypatch.setenv("WORKBENCH_MODEL", str(tmp_path / "new-model"))
    with pytest.raises(RuntimeError, match="different MLX model"):
        ensure_simulator(8775, tmp_path, tools=True)
    state["language_model"] = None
    with pytest.raises(RuntimeError, match="different MLX model"):
        ensure_simulator(8775, tmp_path, tools=True)
    state["language_model"] = str(tmp_path / "new-model")
    assert ensure_simulator(8775, tmp_path, tools=True) is None
