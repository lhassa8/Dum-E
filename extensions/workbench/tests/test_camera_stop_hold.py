"""Camera-port Stop must retain a free tool and then physically finish its task."""

import json
from pathlib import Path

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench


@pytest.mark.parametrize("case_id", ["validation-000", "validation-001", "validation-002"])
@pytest.mark.parametrize("continuation", ["resume", "return"])
def test_camera_long_hold_and_continuation_with_tool_truth_denied(
    case_id, continuation, monkeypatch
):
    fixture = json.loads(
        (Path(__file__).parents[1] / "fixtures/release_model_cases.json").read_text()
    )
    case = next(c for c in fixture["cases"] if c["id"] == case_id)
    bench = ToolWorkbench(case["seed"], xml=camera_scene_xml(case))
    bench.model.vis.headlight.diffuse[:] *= case["light"]
    camera = CameraSensor(bench)
    robot = SimRobot(bench, recover_ik=True)
    actor = CameraDelivery(
        robot,
        camera,
        case["tool"],
        HANDOFF["handoff"],
        verify_motion=True,
        release_fallback=True,
        linear_lifts=True,
        center_grasp=True,
        safe_handoff=True,
    )
    truth = bench.observe
    initial = truth()
    name = case["tool"]

    def denied(*args):
        raise AssertionError("Camera actor accessed privileged tool state")

    monkeypatch.setattr(bench, "observe", denied)
    monkeypatch.setattr(bench, "tool_support_height", denied)

    def check_neighbors():
        actual = truth()
        assert max(np.linalg.norm(actual[n] - p) for n, p in initial.items() if n != name) < 0.004
        return actual[name]

    try:
        for _ in range(3000):
            assert actor.advance()
            position = check_neighbors()
            if actor.phase == "Lifting tool" and position[2] > 0.13:
                break
        else:
            pytest.fail("Camera actor did not reach the frozen early-lift Stop point")
        stopped_position = position.copy()
        joints, grip = robot.read().joints, float(bench.data.ctrl[7])
        actor.pause()
        for _ in range(1000):
            bench.tick()
            actual = check_neighbors()
            assert actual[2] > 0.13
            assert np.linalg.norm(actual - stopped_position) < 0.01
            assert np.max(np.abs(robot.read().joints - joints)) < 0.02
            assert bench.data.ctrl[7] == grip
        if continuation == "resume":
            actor.resume()
            target = HANDOFF["handoff"]
        else:
            actor.return_to_rack()
            target = initial[name][:2]
        for _ in range(3000):
            if not actor.advance():
                break
            check_neighbors()
        else:
            pytest.fail("Camera continuation exceeded its existing frame bound")
        actual = check_neighbors()
        assert actor.outcome.status == "released_unverified"
        assert np.linalg.norm(actual[:2] - target) < 0.035
        assert actual[2] < 0.04
        address = bench.model.joint(f"{name}_joint").dofadr[0]
        assert np.linalg.norm(bench.data.qvel[address : address + 3]) < 0.03
        assert bench.data.qpos[7:9].sum() > 0.07
        assert bench.model.neq == 1  # Original finger coupling, no object weld.
    finally:
        camera.close()
        bench.close()
