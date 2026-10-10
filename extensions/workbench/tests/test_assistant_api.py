import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from physical_ai_lab.assistant.app import Application, make_api


def test_api_rejects_unknown_inputs_busy_and_cross_origin_calls():
    app = Application()
    client = TestClient(make_api(app))
    assert client.post("/chat", json={"message": "Move red to green"}).status_code == 409
    app.model_status = "ready"
    assert client.post("/chat", json={"message": ""}).status_code == 422
    assert client.post("/chat", json={"message": "Move red to green"}).status_code == 200
    assert client.post("/chat", json={"message": "Move blue to purple"}).status_code == 409
    assert client.post("/reset").status_code == 409
    before = app.epoch
    assert client.post("/stop").status_code == 200
    assert app.stop_event.is_set()
    assert app.epoch == before + 1  # In-flight interpretations cannot start a late action.
    assert (
        client.post(
            "/chat",
            headers={"Origin": "https://unrelated.example"},
            json={"message": "Move red to green"},
        ).status_code
        == 403
    )


def test_chat_whitespace_and_snapshot_are_explicit():
    app = Application()
    app.model_status = "ready"
    with pytest.raises(ValueError):
        app.chat("  ")
    app.chat("Could you move the blue block to green?")
    epoch, job, text, history = app.requests.get_nowait()
    assert text.startswith("Could you")
    assert epoch == app.epoch and job == app.job_id
    assert app.snapshot()["busy"]
    assert history[-1]["role"] == "assistant"
