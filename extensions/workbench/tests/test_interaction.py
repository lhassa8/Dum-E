"""Questions preserve manipulation; switching tools requires verified rack return."""

import json
from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.assistant.app import Application
from physical_ai_lab.assistant.tool_control import ToolChange, ToolPerformance
from physical_ai_lab.assistant.tool_language import ToolIntent
from physical_ai_lab.assistant.tool_scene import TOOLS, ToolWorkbench
from physical_ai_lab.dume.speech import Speech


def lifted(bench, tool):
    controller = ToolPerformance(bench, tool)
    for _ in range(2500):
        assert controller.advance()
        if controller.phase == "Lifting tool" and bench.observe()[tool][2] > 0.13:
            return controller
    pytest.fail("Tool was not lifted")


def test_read_only_question_during_lift_preserves_job_and_grip():
    bench = ToolWorkbench()
    controller = lifted(bench, "screwdriver")
    app = Application(tools=True)
    app.model_status = "ready"
    app.busy, app.phase, app.job_id = True, controller.phase, "original"
    app.task = {"object": "screwdriver", "destination": "handoff"}
    app.last_tool = "screwdriver"
    app.observations = {k: v.tolist() for k, v in bench.observe().items()}
    before = bench.data.ctrl.copy()
    result = app.understand("What are you doing?")
    assert result["intent"]["action"] == "answer"
    assert "lifting" in result["intent"]["message"].lower()
    assert "isn't confirmed" in result["intent"]["message"]
    assert app.job_id == "original" and app.busy
    assert app.commands.empty() and app.requests.empty()
    np.testing.assert_array_equal(bench.data.ctrl, before)
    assert controller.advance()
    bench.close()


@pytest.mark.parametrize("old,new", [(a, b) for a in TOOLS for b in TOOLS if a != b])
def test_different_tool_change_returns_old_before_new_pickup(old, new):
    bench = ToolWorkbench()
    before = bench.observe()
    paused = lifted(bench, old)
    paused.pause()
    for _ in range(180):
        bench.tick()
    change = ToolChange(bench, paused, new)
    assert bench.data.ctrl[7] < 128  # Never open a held grip to start a new task.
    verified_return = False
    while change.advance():
        if change.stage == "requested" and not verified_return:
            assert np.linalg.norm(bench.observe()[old][:2] - TOOLS[old]) < 0.035
            assert change.verified_steps[0]["status"] == "success"
            verified_return = True
    assert verified_return and change.outcome.status == "success"
    assert len(change.verified_steps) == 2
    assert change.outcome.distance_m < 0.035
    for tool in TOOLS:
        if tool not in {old, new}:
            assert np.linalg.norm(bench.observe()[tool] - before[tool]) < 0.004
    bench.close()


def test_stopped_tool_change_resumes_pending_second_skill():
    bench = ToolWorkbench()
    paused = lifted(bench, "screwdriver")
    paused.pause()
    change = ToolChange(bench, paused, "wrench")
    for _ in range(100):
        assert change.advance()
    change.pause()
    for _ in range(180):
        bench.tick()
    change.resume()
    while change.advance():
        pass
    assert change.outcome.status == "success" and len(change.verified_steps) == 2
    assert np.linalg.norm(bench.observe()["screwdriver"][:2] - TOOLS["screwdriver"]) < 0.035
    bench.close()


def test_failed_old_return_prevents_new_pickup():
    bench = ToolWorkbench()
    paused = lifted(bench, "screwdriver")
    paused.pause()
    change = ToolChange(bench, paused, "wrench")
    before = bench.observe()["wrench"]
    bench.model.actuator_forcerange[7] = [0, 0]
    while change.advance():
        pass
    assert change.outcome.status == "failed" and change.stage == "return_previous"
    np.testing.assert_allclose(bench.observe()["wrench"], before, atol=0.004)
    bench.close()


@pytest.mark.parametrize("seed", [42, 51, 52])
def test_late_hammer_return_after_other_skills_preserves_grasp(seed):
    bench = ToolWorkbench(seed)
    paused = lifted(bench, "screwdriver")
    paused.pause()
    change = ToolChange(bench, paused, "wrench")
    change.advance()
    change.pause()
    for _ in range(8):
        bench.tick()
    change.resume()
    while change.advance():
        pass
    assert change.outcome.status == "success"
    returning = ToolPerformance(bench, "wrench", returning=True)
    while returning.advance():
        pass
    assert returning.outcome.status == "success"
    before = bench.observe()
    hammer = ToolPerformance(bench, "hammer")
    for _ in range(2500):
        assert hammer.advance()
        if hammer.phase == "Placing tool":
            break
    else:
        pytest.fail("Hammer did not reach its placement approach")
    hammer.pause()
    for _ in range(3):
        bench.tick()
    returned = hammer.return_to_rack()
    while returned.advance():
        pass
    assert returned.outcome.status == "success" and returned.outcome.distance_m < 0.035
    assert bench.observe()["hammer"][2] < 0.04
    for name in ["screwdriver", "wrench"]:
        assert np.linalg.norm(bench.observe()[name] - before[name]) < 0.004
    bench.close()


def test_spoken_reply_echo_does_not_reject_short_real_commands():
    speech = Speech()
    speech.last_text = "I'll bring you the screwdriver."
    speech.process = SimpleNamespace(poll=lambda: None)
    assert speech.is_echo("I'll bring you the screwdriver.")
    assert not speech.is_echo("Stop.")
    assert not speech.is_echo("Put it back.")
    assert not speech.is_echo("Bring me a wrench.")


def test_resolved_tool_request_is_schema_validated():
    from fastapi.testclient import TestClient

    from physical_ai_lab.assistant.app import make_api

    app = Application(tools=True)
    app.model_status = "ready"
    client = TestClient(make_api(app))
    bad = client.post(
        "/chat",
        json={
            "message": "fake",
            "intent": {"action": "drill", "object": "wrench", "destination": "handoff"},
        },
    )
    assert bad.status_code == 409 and app.commands.empty()
    intent = ToolIntent("fetch", "wrench", "handoff", "")
    good = client.post(
        "/chat",
        json={"message": "I need a spanner", "intent": json.loads(json.dumps(intent.__dict__))},
    )
    assert good.status_code == 200 and app.requests.empty()


def test_next_tool_clears_occupied_handoff_before_delivery():
    bench = ToolWorkbench()
    delivered = ToolPerformance(bench, "screwdriver")
    while delivered.advance():
        pass
    assert delivered.outcome.status == "success"
    app = Application(tools=True)
    controller = app.tool_action(bench, ToolIntent("fetch", "wrench", "handoff", ""), "next")
    assert isinstance(controller, ToolChange)
    while controller.advance():
        pass
    assert controller.outcome.status == "success"
    assert np.linalg.norm(bench.observe()["screwdriver"][:2] - TOOLS["screwdriver"]) < 0.035
    assert len(controller.verified_steps) == 2
    bench.close()


def test_resume_before_command_application_retains_fast_route():
    app = Application(tools=True)
    app.model_status = "ready"
    app.chat("Bring me the wrench.")
    app.stop()
    app.stop_event.clear()
    app.phase = "Stopped"
    app.chat("Resume.")
    assert app.requests.empty()
    app.commands.get_nowait()  # Old intent is epoch-invalidated.
    app.commands.get_nowait()  # Stop notification.
    _, (epoch, _, intent) = app.commands.get_nowait()
    assert epoch == app.epoch and intent.action == "fetch" and intent.object == "wrench"
