"""Behavioral guards for the experimental coordinator; no simulator/model required."""

import importlib.util
import io
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

spec = importlib.util.spec_from_file_location(
    "libero_coordinator", Path(__file__).resolve().parents[3] / "scripts/libero_coordinator.py"
)
lab = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lab)


@pytest.fixture
def coordinator(monkeypatch):
    c = lab.Coordinator.__new__(lab.Coordinator)
    c.lock, c.decisions = threading.RLock(), threading.Lock()
    c.dialogue_epoch, c.thinking = 0, False
    c.error = None
    c.messages = []
    c.connection, c.event = Mock(), Mock()
    monkeypatch.setattr(lab, "args", SimpleNamespace(lmstudio_url="http://local", model="test"))
    state = {"epoch": 4, "phase": "running", "prompt": "Move a bowl"}
    monkeypatch.setattr(lab, "physics", Mock(return_value=state))
    intent = {"action": "start", "task_id": 0, "message": "Move"}
    data = {"choices": [{"message": {"content": json.dumps(intent)}}]}
    monkeypatch.setattr(
        lab, "request", Mock(return_value=(json.dumps(data).encode(), "application/json"))
    )
    return c


@pytest.mark.parametrize(
    "text",
    [
        "What are you doing?",
        "Where is the bowl?",
        "Don't move the bowl.",
        "Imagine moving the bowl.",
        "If you moved the bowl, would it fall?",
    ],
)
def test_non_commands_cannot_start_even_when_model_says_start(coordinator, text):
    result = coordinator.interact(text)
    assert result["mode"] == "answer"
    assert [call.args[0] for call in lab.physics.call_args_list] == ["/state"]


def test_stop_invalidates_physics_before_client_and_never_calls_model(coordinator):
    order = []
    lab.physics.side_effect = lambda *unused: order.append("physics") or {"phase": "paused"}
    coordinator.connection.stop.side_effect = lambda: order.append("client")
    assert coordinator.interact("Please stop now.")["mode"] == "stop"
    assert order == ["physics", "client"]
    lab.request.assert_not_called()


def test_model_decision_finishing_after_stop_is_discarded(coordinator):
    response = lab.request.return_value

    def delayed(*unused, **kwargs):
        coordinator.stop()
        return response

    lab.request.side_effect = delayed
    assert coordinator.interact("Pick up the bowl.")["mode"] == "cancelled"
    assert "/initialize" not in [call.args[0] for call in lab.physics.call_args_list]


def test_scene_decision_carries_observed_epoch(coordinator):
    assert coordinator.interact("Pick up the bowl.")["mode"] == "start"
    assert lab.physics.call_args.args == ("/initialize", {"task_id": 0, "expected_epoch": 4})


def test_dont_stop_is_not_stop(coordinator):
    assert coordinator.interact("Don't stop.")["mode"] == "answer"
    coordinator.connection.stop.assert_not_called()


def test_proxy_preserves_json_bytes():
    handler = lab.Handler.__new__(lab.Handler)
    handler.send_response = handler.send_header = handler.end_headers = Mock()
    handler.wfile = io.BytesIO()
    payload = b'{"text":"Stop"}'
    handler.reply(payload)
    assert handler.wfile.getvalue() == payload


def test_failed_policy_blocks_resume_and_new_motion_but_stop_still_works(coordinator):
    coordinator.error = "GPU inference failed"
    with pytest.raises(ValueError, match="restart"):
        coordinator.resume()
    assert coordinator.interact("Pick up the bowl.")["mode"] == "clarify"
    lab.physics.assert_not_called()
    lab.request.assert_not_called()
    assert coordinator.interact("Stop")["mode"] == "stop"
