"""Live adapter contracts, using real physics and evaluator-only truth."""

import threading
import time

import numpy as np
import pytest

import physical_ai_lab.assistant.camera_tasks as tasks
from physical_ai_lab.assistant.app import Application
from physical_ai_lab.assistant.perception_scene import camera_scene_xml
from physical_ai_lab.assistant.tool_language import ToolIntent
from physical_ai_lab.assistant.tool_scene import ToolWorkbench


@pytest.fixture
def hub():
    bench = ToolWorkbench(xml=camera_scene_xml({"layout": {}}, alternate_view=True))
    hub = tasks.CameraTasks(bench)
    try:
        yield hub
    finally:
        hub.close()
        bench.close()


@pytest.mark.parametrize("tool", ["screwdriver", "wrench", "hammer"])
def test_camera_adapter_complete_journey_without_actor_truth(hub, tool, monkeypatch):
    def denied(*args):
        raise AssertionError("Actor requested simulator tool state")

    monkeypatch.setattr(hub.bench, "observe", denied)
    monkeypatch.setattr(hub.bench, "tool_support_height", denied)
    for returning in [False, True]:
        controller = hub.select(tool, returning)
        for _ in range(2000):
            if not controller.advance():
                break
        assert controller.outcome.status == "success"
        assert controller.max_height - controller.initial_height >= 0.08
        assert controller.disturbance < 0.004
        assert controller.outcome.distance_m < 0.035


def test_epoch_cancellation_cannot_tick_a_late_motion(hub):
    epoch = [0]
    hub.epoch = lambda: epoch[0]
    controller = hub.task(hub.bench, "screwdriver")
    before = hub.bench.data.ctrl.copy()
    start = hub.bench.data.time
    epoch[0] += 1
    with pytest.raises(tasks.MotionCancelled):
        controller.robot.tick(np.zeros(7), 0)
    np.testing.assert_array_equal(hub.bench.data.ctrl, before)
    assert hub.bench.data.time == start


def test_unconfirmed_next_rack_does_not_reroute_paused_task(hub):
    controller = hub.task(hub.bench, "screwdriver")
    del hub.racks["wrench"]
    original = controller.actor.frames
    with pytest.raises(ValueError, match="camera-confirmed"):
        hub.select("wrench", paused=controller)
    assert controller.actor.frames is original
    assert controller.destination == "handoff"


def test_physics_advances_during_detector_and_stop_abandons_result(hub, monkeypatch):
    stopping = threading.Event()
    hub.stopping = stopping.is_set
    original = tasks.locate_tools

    def delayed(frame):
        time.sleep(0.15)
        return original(frame)

    monkeypatch.setattr(tasks, "locate_tools", delayed)
    sample = hub.sensor.capture_timed()
    started = hub.bench.data.time
    hub.perceive(sample.frame)
    assert hub.bench.data.time - started >= 0.096
    sample = hub.sensor.capture_timed()
    timer = threading.Timer(0.05, stopping.set)
    timer.start()
    command = hub.bench.data.ctrl[7]
    try:
        with pytest.raises(tasks.MotionCancelled):
            hub.perceive(sample.frame)
    finally:
        timer.join()
    assert hub.bench.data.ctrl[7] == command


def test_camera_inventory_does_not_use_application_truth(hub):
    app = Application(tools=True, camera_tools=True)
    app.camera_hub = hub
    app.observations = {"screwdriver": [99, 99, 99]}
    assert "99" not in str(app.inventory())
    assert app.snapshot()["tool_control"] == "camera"


def test_cancelled_held_camera_generation_refuses_resume_keeps_redirect(hub):
    controller = hub.task(hub.bench, "screwdriver")
    for _ in range(1500):
        assert controller.advance()
        if controller.phase == "Moving to target":
            break
    assert controller.actor.carrying and controller.actor._grip_present()
    controller.actor.frames.close()
    controller.cancelled_generation = True
    controller.pause()
    app = Application(tools=True, camera_tools=True)
    app.camera_hub = hub
    app.paused_controller = controller
    app.interrupted = {"request": "Bring me the screwdriver", "intent": {"action": "fetch"}}
    assert app.tool_action(hub.bench, ToolIntent("resume", None, None, ""), "test") is None
    assert app.paused_controller is controller
    controller.return_to_rack()
    for _ in range(2000):
        if not controller.advance():
            break
    assert controller.outcome.status == "success"
