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
