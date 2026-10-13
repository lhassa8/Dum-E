"""Live adapter contracts, using real physics and evaluator-only truth."""

import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

import physical_ai_lab.assistant.camera_tasks as tasks
from physical_ai_lab.assistant.app import Application
from physical_ai_lab.assistant.camera_control import CameraDelivery
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


def test_cancelled_held_camera_generation_resumes_with_original_destination(hub):
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
    target = controller.actor.target.copy()
    budgets = controller.actor.grip_recovery_attempts, controller.actor.correction_attempts
    assert app.tool_action(hub.bench, ToolIntent("resume", None, None, ""), "test") is controller
    np.testing.assert_array_equal(controller.actor.target, target)
    assert (
        controller.actor.grip_recovery_attempts,
        controller.actor.correction_attempts,
    ) == budgets
    assert not controller.cancelled_generation
    for _ in range(2000):
        if not controller.advance():
            break
    assert controller.outcome.status == "success"


def recovery_observation_state():
    before = SimpleNamespace(gap_m=0.001, closing_command=True, tcp_m=np.array([0.4, 0, 0.3]))
    after = SimpleNamespace(gap_m=0.001, closing_command=True, tcp_m=np.array([0.4, 0, 0.3]))
    robot = SimpleNamespace(read=lambda: after, hold=Mock())
    actor = CameraDelivery.__new__(CameraDelivery)
    actor.robot = robot
    actor.recover_grip, actor.carrying = True, True
    actor.grip_recovery_attempts = 1
    actor.phase = "Observing supported tool after grip loss"
    actor.evidence = []
    hub = tasks.CameraTasks.__new__(tasks.CameraTasks)
    hub.active = SimpleNamespace(actor=actor, robot=robot)
    return hub, actor, before, after


def test_owned_empty_hand_observation_does_not_demand_held_handle():
    hub, actor, before, _ = recovery_observation_state()
    hub._check_perception_hold(before)
    assert actor.carrying  # Fresh tabletop evidence is still required to clear uncertainty.
    assert actor.grip_recovery_attempts == 1


@pytest.mark.parametrize("change", ["nan", "negative", "handle", "open", "before_handle"])
def test_recovery_observation_refuses_inconsistent_empty_hand(change):
    hub, actor, before, after = recovery_observation_state()
    if change == "nan":
        after.gap_m = float("nan")
    elif change == "negative":
        after.gap_m = -0.001
    elif change == "handle":
        after.gap_m = 0.015
    elif change == "open":
        after.closing_command = False
    else:
        before.gap_m = 0.02
    with pytest.raises(ValueError, match="Empty-hand recovery state changed"):
        hub._check_perception_hold(before)
    actor.robot.hold.assert_called_once()


@pytest.mark.parametrize("change", ["phase", "zero_budget", "exhausted", "disabled"])
def test_observation_exception_cannot_bypass_normal_carry_gate(change):
    hub, actor, before, _ = recovery_observation_state()
    if change == "phase":
        actor.phase = "Moving to target"
    elif change == "zero_budget":
        actor.grip_recovery_attempts = 0
    elif change == "exhausted":
        actor.grip_recovery_attempts = 2
    else:
        actor.recover_grip = False
    with pytest.raises(ValueError):
        hub._check_perception_hold(before)


def test_slow_planning_advances_physics_and_refuses_stale_robot_snapshot(hub, monkeypatch):
    controller = hub.task(hub.bench, "screwdriver")
    original = tasks.SimRobot.cartesian_path

    def delayed(*args, **kwargs):
        time.sleep(0.3)
        return original(*args, **kwargs)

    monkeypatch.setattr(tasks.SimRobot, "cartesian_path", delayed)
    reading = controller.robot.read()
    grip = hub.bench.data.ctrl[7]
    with pytest.raises(ValueError, match="planning snapshot is stale"):
        controller.robot.cartesian_path(
            reading.tcp_m, reading.tcp_m + [0, 0, 0.02], reading.rotation, 40
        )
    assert hub.bench.data.time - reading.time_s > 0.25
    assert hub.bench.data.ctrl[7] == grip


def test_cancelled_planning_discards_result_without_gripper_command(hub, monkeypatch):
    epoch = [0]
    hub.epoch = lambda: epoch[0]
    controller = hub.task(hub.bench, "screwdriver")
    original = tasks.SimRobot.cartesian_path

    def delayed(*args, **kwargs):
        time.sleep(0.15)
        return original(*args, **kwargs)

    monkeypatch.setattr(tasks.SimRobot, "cartesian_path", delayed)
    reading = controller.robot.read()
    grip = hub.bench.data.ctrl[7]
    timer = threading.Timer(0.05, lambda: epoch.__setitem__(0, 1))
    timer.start()
    try:
        with pytest.raises(tasks.MotionCancelled):
            controller.robot.cartesian_path(
                reading.tcp_m, reading.tcp_m + [0, 0, 0.02], reading.rotation, 40
            )
    finally:
        timer.join()
    assert hub.bench.data.ctrl[7] == grip


@pytest.mark.parametrize("old_plan_fails", [False, True])
def test_new_camera_snapshot_waits_for_abandoned_real_plan(hub, old_plan_fails):
    epoch = [0]
    hub.epoch = lambda: epoch[0]
    controller = hub.select("screwdriver")
    for _ in range(1000):
        assert controller.advance()
        if controller.phase == "Moving to target":
            break
    else:
        pytest.fail("Actual held tool never reached transport")
    reading = controller.robot.read()
    tool_before = hub.truth()["screwdriver"].copy()
    started, release = threading.Event(), threading.Event()
    planner = tasks.SimRobot(hub.bench, recover_ik=True, refine_cartesian=True)

    def old_work():
        started.set()
        assert release.wait(timeout=3)
        point = np.array([3.0, 0.0, 0.3]) if old_plan_fails else reading.tcp_m + [0, 0, 0.02]
        return planner.cartesian_path(reading.tcp_m, point, reading.rotation, 40,
                                      initial_reading=reading)

    def interrupt():
        assert started.wait(timeout=2)
        epoch[0] += 1

    interrupter = threading.Thread(target=interrupt)
    interrupter.start()
    try:
        with pytest.raises(tasks.MotionCancelled):
            hub.compute(old_work)
        abandoned = hub.pending_computation
        assert abandoned is not None and not abandoned.done()
        controller.pause()
        controller.expected_epoch = epoch[0]
        before_capture_time = hub.bench.data.time
        finish = threading.Timer(0.20, release.set)
        finish.start()
        try:
            sample = hub.sensor.capture_timed()
        finally:
            finish.join()
        assert abandoned.done() and hub.pending_computation is None
        if old_plan_fails:
            assert isinstance(abandoned.exception(), ValueError)
        assert sample.captured_s - before_capture_time >= 0.128
        assert np.max(np.abs(controller.robot.read().joints - reading.joints)) < 0.02
        assert np.linalg.norm(hub.truth()["screwdriver"] - tool_before) < 0.01
        assert np.linalg.norm(controller.robot.read().tcp_m - reading.tcp_m) < 0.01
        assert controller.robot.read().closing_command
    finally:
        release.set()
        interrupter.join()


def test_redirect_after_cancelled_release_reacquires_for_actual_return(hub):
    controller = hub.select("screwdriver")
    for _ in range(2000):
        assert controller.advance()
        if controller.phase == "Withdrawing gripper":
            break
    else:
        pytest.fail("Actual release never reached withdrawal")
    assert not controller.actor.carrying
    assert not controller.robot.read().closing_command
    controller.actor.frames.close()
    controller.cancelled_generation = True
    controller.pause()
    budgets = (controller.actor.grip_recovery_attempts, controller.actor.correction_attempts)
    controller.return_to_rack()
    assert controller.destination == "rack"
    assert not controller.cancelled_generation
    for _ in range(2000):
        if not controller.advance():
            break
    assert controller.outcome.status == "success"
    assert controller.outcome.distance_m < 0.035
    assert controller.max_height-controller.initial_height >= 0.08
    assert (
        controller.actor.grip_recovery_attempts, controller.actor.correction_attempts
    ) == budgets


@pytest.mark.parametrize("invalid", ["ended", "phase", "transform", "grasp_reading"])
def test_cancelled_held_resume_refuses_invalid_context_before_replacing_frames(hub, invalid):
    controller = hub.select("screwdriver")
    for _ in range(1000):
        assert controller.advance()
        if controller.phase == "Moving to target":
            break
    else:
        pytest.fail("Actual held transport was not reached")
    controller.actor.frames.close()
    controller.cancelled_generation = True
    controller.pause()
    old_frames = controller.actor.frames
    budgets = (controller.actor.grip_recovery_attempts, controller.actor.correction_attempts)
    grip = hub.bench.data.ctrl[7]
    joints = controller.robot.read().joints
    if invalid == "ended":
        controller.actor.outcome = SimpleNamespace(status="success")
    elif invalid == "phase":
        controller.actor.paused_phase = "Unknown operation"
    elif invalid == "transform":
        controller.actor.offset_local = np.full(3, np.nan)
    else:
        controller.actor.grasp_reading = SimpleNamespace(tcp_m=np.full(3, np.nan))
    controller.resume()
    assert controller.outcome.status == "failed"
    assert controller.cancelled_generation
    assert controller.actor.frames is old_frames
    assert (
        controller.actor.grip_recovery_attempts, controller.actor.correction_attempts
    ) == budgets
    assert hub.bench.data.ctrl[7] == grip
    np.testing.assert_array_equal(controller.robot.read().joints, joints)
