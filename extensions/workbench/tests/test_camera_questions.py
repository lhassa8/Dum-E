"""Camera questions are read-only, fresh and explicitly isolated from motion."""

import hashlib
import threading
import time
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

from physical_ai_lab.assistant.app import Application, make_api
from physical_ai_lab.assistant.vision_language import camera_question


class CameraProbe:
    model, coordinates, url = "test/vision", "grid1000_yx", "http://127.0.0.1:1234"

    def observe(self, jpeg):
        assert jpeg == b"\xff\xd8captured-snapshot"
        return {
            "model": self.model,
            "tools": {
                "screwdriver": {"visible": True, "center": [0.25, 0.5]},
                "wrench": {"visible": False, "center": None},
                "hammer": {"visible": True, "center": [0.75, 0.5]},
            },
            "elapsed_ms": 1,
        }


def prepared():
    app = Application(tools=True)
    app.vision = CameraProbe()
    app.camera_image = b"\xff\xd8captured-snapshot"
    app.camera_captured_s = time.monotonic()
    app.model_status = "ready"
    return app


@pytest.mark.parametrize(
    "text",
    [
        'I said "what can you see"',
        "Bring me the hammer and look around",
        "Can you see my webcam?",
        "Don’t look at the workbench",
    ],
)
def test_camera_route_does_not_infer_a_request_from_mentions(text):
    assert not camera_question(text)[0]


def test_actual_snapshot_answer_preserves_work_and_does_not_use_object_state():
    app = prepared()
    app.busy, app.phase, app.job_id = True, "Lifting tool", "preserved"
    # Misleading simulator truth must not be part of the visual request or reply.
    app.observations = {"wrench": [999, 999, 999]}
    result = app.understand("What can you see on the workbench?")
    assert result["route"] == "camera" and result["intent"]["action"] == "answer"
    assert result["intent"]["object"] is None and result["intent"]["destination"] is None
    assert "can't confidently make out wrench" in result["intent"]["message"]
    assert app.busy and app.phase == "Lifting tool" and app.job_id == "preserved"
    assert app.commands.empty() and app.requests.empty()
    assert result["profile"]["frame_sha256"] == hashlib.sha256(app.camera_image).hexdigest()
    assert TestClient(make_api(app)).get("/camera.jpg").content == app.camera_image
    assert TestClient(make_api(app)).get("/camera.jpg?frame=wrong-snapshot").status_code == 409


def test_stale_failed_or_disabled_camera_cannot_submit_motion():
    app = prepared()
    app.camera_captured_s -= 1
    with pytest.raises(ValueError, match="fresh"):
        app.understand("What do you see?")
    app.camera_captured_s = time.monotonic()
    app.vision = SimpleNamespace(
        observe=lambda jpeg: (_ for _ in ()).throw(ValueError("bad bounds"))
    )
    with pytest.raises(ValueError, match="reliably inspect"):
        app.understand("What do you see?")
    assert app.commands.empty() and app.requests.empty()
    app.vision = None
    assert "isn't enabled" in app.understand("What do you see?")["intent"]["message"]


def test_stop_supersedes_pending_camera_without_waiting_for_model():
    app = prepared()
    underway, release = threading.Event(), threading.Event()
    original = app.vision.observe

    def delayed(jpeg):
        underway.set()
        release.wait(2)
        return original(jpeg)

    app.vision.observe = delayed
    errors = []

    def query():
        try:
            app.understand("What do you see?")
        except ValueError as error:
            errors.append(str(error))

    worker = threading.Thread(target=query)
    worker.start()
    try:
        assert underway.wait(1)
        started = time.monotonic()
        app.stop()
        assert time.monotonic() - started < 0.1 and app.stop_event.is_set()
        release.set()
        worker.join(2)
        assert errors == ["Camera request was superseded."]
        assert app.last_camera_read is None and not app.camera_answer_image
    finally:
        release.set()
        worker.join(2)


def test_launcher_rejects_reusing_wrong_camera_model_or_units(monkeypatch, tmp_path):
    from physical_ai_lab.dume.app import ensure_simulator

    state = {
        "backend": "workbench",
        "last_outcome": None,
        "busy": False,
        "profile": "tools",
        "language_backend": "mlx",
        "physics_profile": "tool_contacts_v2",
    }
    monkeypatch.delenv("WORKBENCH_MODEL", raising=False)
    monkeypatch.setenv("WORKBENCH_LANGUAGE_BACKEND", "mlx")
    monkeypatch.setattr(
        "physical_ai_lab.dume.app.httpx.get",
        lambda *a, **kw: httpx.Response(200, json=state, request=httpx.Request("GET", a[0])),
    )
    with pytest.raises(RuntimeError, match="unverified camera"):
        ensure_simulator(
            8775, tmp_path, tools=True, vision_model="test/vision", vision_coordinates="grid1000_yx"
        )
    state["camera"] = {
        "model": "test/vision",
        "coordinates": "grid1000_yx",
        "endpoint": "http://127.0.0.1:1234",
    }
    assert (
        ensure_simulator(
            8775, tmp_path, tools=True, vision_model="test/vision", vision_coordinates="grid1000_yx"
        )
        is None
    )
    with pytest.raises(RuntimeError, match="unverified camera"):
        ensure_simulator(8775, tmp_path, tools=True, vision_model="test/vision")


def test_alternate_view_uses_one_complete_observation_without_object_state_fill():
    app = prepared()
    original = app.vision.observe
    app.camera_alternate_image = b"\xff\xd8second-view"

    def observe(jpeg):
        if jpeg == app.camera_image:
            return original(jpeg)
        assert jpeg == app.camera_alternate_image
        return {
            "model": app.vision.model,
            "elapsed_ms": 1,
            "tools": {
                name: {"visible": True, "center": [0.6, 0.7]}
                for name in ["screwdriver", "wrench", "hammer"]
            },
        }

    app.vision.observe = observe
    result = app.understand("What do you see?")
    assert result["profile"]["view"] == "side" and len(result["profile"]["view_call_ms"]) == 2
    assert all(item["center"] == [0.6, 0.7] for item in result["profile"]["tools"].values())
    assert app.camera_answer_image == app.camera_alternate_image and app.commands.empty()
    # Both views uncertain: known simulator presence must never become a visual claim.
    app.vision.observe = lambda jpeg: original(app.camera_image)
    app.observations = {"wrench": [0.4, 0, 0.02]}
    result = app.understand("What do you see?")
    assert not result["profile"]["tools"]["wrench"]["visible"]
    assert result["profile"]["view"] == "front"
