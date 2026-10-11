"""Physical delivery, honest gestures, and bounded tool intents."""

import json

import numpy as np
import pytest

from physical_ai_lab.assistant.tool_control import Gesture, ToolDelivery
from physical_ai_lab.assistant.tool_language import ToolIntent
from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS, ToolWorkbench


@pytest.mark.parametrize("seed", [42, 51, 52])
@pytest.mark.parametrize("name", list(TOOLS))
def test_physical_tool_delivery_and_return(name, seed):
    bench = ToolWorkbench(seed)
    before = bench.observe()
    delivery = ToolDelivery(bench, name)
    while delivery.advance():
        pass
    assert delivery.outcome.status == "success"
    assert delivery.max_height - delivery.initial_height > 0.08
    assert delivery.outcome.distance_m < 0.035
    assert bench.observe()[name][2] < 0.04
    assert bench.data.qpos[7] > 0.035
    for other, position in before.items():
        if other != name:
            assert np.linalg.norm(bench.observe()[other] - position) < 0.004
    returning = ToolDelivery(bench, name, returning=True)
    while returning.advance():
        pass
    assert returning.outcome.status == "success"
    assert np.linalg.norm(bench.observe()[name][:2] - TOOLS[name]) < 0.035
    bench.close()


@pytest.mark.parametrize("name", ["wave", "nod", "curious", "celebrate"])
def test_gestures_move_arm_but_not_tools(name):
    bench = ToolWorkbench()
    before = bench.observe()
    controller = Gesture(bench, name, "Hello!")
    joints = []
    while controller.advance():
        joints.append(bench.data.qpos[:7].copy())
    assert controller.outcome.status == "expressed"
    assert np.max(np.ptp(joints, axis=0)) > 0.15
    for tool, xyz in before.items():
        assert np.linalg.norm(bench.observe()[tool] - xyz) < 0.004
    bench.close()


def test_failed_grasp_and_gesture_stop_are_honest():
    bench = ToolWorkbench()
    bench.model.actuator_forcerange[7] = [0, 0]
    controller = ToolDelivery(bench, "screwdriver")
    while controller.advance():
        pass
    assert controller.outcome.status == "failed"
    assert "isn't confirmed" in controller.outcome.message
    bench.close()
    bench = ToolWorkbench()
    controller = Gesture(bench, "wave", "Hello")
    for _ in range(15):
        assert controller.advance()
    controller.stop()
    assert not controller.advance()
    assert controller.outcome.status == "interrupted"
    bench.close()


def test_tool_intent_schema_rejects_invented_skills():
    good = ToolIntent.parse(
        json.dumps(
            {
                "action": "fetch",
                "object": "wrench",
                "destination": "handoff",
                "message": "Coming up.",
            }
        )
    )
    assert good.object == "wrench"
    for data in [
        {"action": "hammer", "object": "hammer", "destination": "handoff"},
        {"action": "fetch", "object": "drill", "destination": "handoff"},
        {"action": "fetch", "object": "wrench", "destination": None},
        {"action": "gesture", "object": "hammer", "destination": "wave"},
        {"action": "gesture", "object": None, "destination": "throw"},
        {"action": "answer", "object": None, "destination": "handoff"},
    ]:
        with pytest.raises(ValueError):
            ToolIntent.parse(json.dumps(data))


def test_model_scene_context_matches_observed_locations():
    from physical_ai_lab.assistant.app import Application

    state = Application(tools=True)
    state.observations = {
        "wrench": [*HANDOFF["handoff"], 0.024],
        "screwdriver": [*TOOLS["screwdriver"], 0.024],
    }
    assert state.inventory() == {"wrench": "handoff tray", "screwdriver": "tool rack"}


@pytest.mark.parametrize("name", list(TOOLS))
@pytest.mark.parametrize("phase", ["Approaching tool", "Grasping", "Lifting tool", "Releasing"])
def test_resume_preserves_delivery_progress_and_placement(name, phase):
    from physical_ai_lab.assistant.tool_control import ToolPerformance

    bench = ToolWorkbench()
    controller = ToolPerformance(bench, name)
    for _ in range(2500):
        assert controller.advance()
        if controller.phase == phase:
            break
    else:
        pytest.fail("Expected pause phase was not reached")
    controller.pause()
    assert not controller.advance()
    grip = bench.data.ctrl[7]
    for _ in range(180):
        bench.tick()
    assert bench.data.ctrl[7] == grip
    controller.resume()
    while controller.advance():
        pass
    assert controller.outcome.status == "success"
    assert controller.outcome.distance_m < 0.035
    assert np.linalg.norm(bench.observe()[name][:2] - HANDOFF["handoff"]) < 0.035
    bench.close()


@pytest.mark.parametrize("name", list(TOOLS))
def test_put_back_while_physically_holding_tool(name):
    from physical_ai_lab.assistant.tool_control import ToolPerformance

    bench = ToolWorkbench()
    controller = ToolPerformance(bench, name)
    for _ in range(2500):
        assert controller.advance()
        if controller.phase == "Lifting tool" and bench.observe()[name][2] > 0.13:
            break
    else:
        pytest.fail("Tool was not lifted")
    controller.pause()
    for _ in range(180):
        bench.tick()
    returning = controller.return_to_rack()
    assert returning.delivery.carrying
    assert returning.stage == "delivery"  # No gesture/reopening with a grasped tool.
    while returning.advance():
        pass
    assert returning.outcome.status == "success"
    assert np.linalg.norm(bench.observe()[name][:2] - TOOLS[name]) < 0.035
    assert bench.observe()[name][2] < 0.04
    bench.close()


def test_recovery_context_and_conversation_do_not_release_paused_tool():
    from physical_ai_lab.assistant.app import Application
    from physical_ai_lab.assistant.tool_control import ToolPerformance

    bench = ToolWorkbench()
    state = Application(tools=True)
    state.model_status = "ready"
    paused = ToolPerformance(bench, "wrench")
    state.paused_controller = paused
    state.interrupted = {"intent": {"action": "fetch"}, "request": "Bring a wrench"}
    state.last_tool = "wrench"
    bench.data.ctrl[7] = 0
    before = bench.data.qpos[:7].copy()
    assert (
        state.tool_action(bench, ToolIntent("answer", None, None, "I can help."), "probe") is None
    )
    assert bench.data.ctrl[7] == 0
    np.testing.assert_array_equal(bench.data.qpos[:7], before)
    assert state.paused_controller is paused
    state.chat("Put it back")
    kind, (_, _, intent) = state.commands.get_nowait()
    assert kind == "intent" and intent.object == "wrench" and intent.action == "return"
    bench.close()


def test_expression_does_not_mask_failed_delivery():
    from physical_ai_lab.assistant.tool_control import ToolPerformance

    bench = ToolWorkbench()
    bench.model.actuator_forcerange[7] = [0, 0]
    controller = ToolPerformance(bench, "screwdriver")
    while controller.advance():
        pass
    assert controller.outcome.status == "failed"
    assert controller.stage == "delivery"  # No victory motion after failure.
    assert not controller.notifications
    bench.close()


def test_resume_without_context_is_an_answer_not_a_physical_task():
    from physical_ai_lab.assistant.app import Application

    bench = ToolWorkbench()
    state = Application(tools=True)
    state.model_status = "ready"
    state.chat("Resume")
    kind, (_, job, intent) = state.commands.get_nowait()
    assert kind == "intent" and intent.action == "resume"
    assert state.tool_action(bench, intent, job) is None
    assert state.last_intent["action"] == "answer"
    assert "isn't a stopped task" in state.messages[-1]["content"]
    bench.close()
