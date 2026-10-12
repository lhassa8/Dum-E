"""Independent kinematics, measured tracking and shadow/tilted-face checks."""

import json
from pathlib import Path
from types import SimpleNamespace

import mujoco
import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import (
    CameraDelivery,
    RobotReading,
    observed_rotation,
    validate_observation,
)
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize("index", [0, 1])
def test_robot_ik_home_recovery_is_read_only_and_independently_verified(monkeypatch, index):
    fixture = json.loads((ROOT / "fixtures/robot_recovery_cases.json").read_text())
    case = fixture["cases"][index]
    b = ToolWorkbench()
    try:
        robot = SimRobot(b, recover_ik=True)
        before = b.data.qpos.copy(), b.data.ctrl.copy()

        def unavailable(_):
            raise ValueError("Current-seeded solver failed")

        monkeypatch.setattr(b, "solve", unavailable)
        answer = robot.solve(case["point_m"], case["rotation"])
        # Fresh independent FK buffer, rather than the solver's claimed errors.
        judge = mujoco.MjData(b.model)
        judge.qpos[:7] = answer
        mujoco.mj_forward(b.model, judge)
        rotation = judge.site_xmat[b.tcp].reshape(3, 3)
        angle = np.arccos(np.clip((np.trace(rotation.T @ case["rotation"]) - 1) / 2, -1, 1))
        assert (
            np.linalg.norm(judge.site_xpos[b.tcp] - case["point_m"])
            < fixture["position_error_max_m"]
        )
        assert angle < fixture["rotation_error_max_rad"]
        np.testing.assert_array_equal(b.data.qpos, before[0])
        np.testing.assert_array_equal(b.data.ctrl, before[1])
        assert robot.ik_events[-1]["kind"] == "ik_home_recovery"
    finally:
        b.close()


def test_unreached_robot_target_is_refused_after_bounded_settling():
    count = [0]
    reading = RobotReading(np.zeros(7), np.array([0.4, 0, 0.2]), np.eye(3), 0.04, True, 0.0)

    def tick(*_):
        count[0] += 1

    robot = SimpleNamespace(
        read=lambda: reading, ready_rotation=np.eye(3), solve=lambda p, r: np.zeros(7), tick=tick
    )
    actor = CameraDelivery(robot, None, "hammer", [0.64, -0.16], verify_motion=True)
    actor.orientation = np.eye(3)
    with pytest.raises(ValueError, match="did not reach"):
        list(actor._motion(np.array([0.6, 0, 0.2]), "Testing motion", 255))
    assert count[0] == 112
    assert actor.last_motion_check["extra_frames"] == 60 and not actor.last_motion_check["passed"]
    with pytest.raises(ValueError, match="verified robot motion"):
        CameraDelivery(robot, None, "hammer", [0.64, -0.16], release_fallback=True)


def test_shadowed_wrench_is_observed_before_grasp_without_state_fallback():
    case = next(
        c
        for c in json.loads((ROOT / "fixtures/release_model_cases.json").read_text())["cases"]
        if c["id"] == "validation-001"
    )
    b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case))
    b.model.vis.headlight.diffuse[:] *= case["light"]
    sensor = CameraSensor(b)
    try:
        actor = CameraDelivery(
            SimRobot(b, recover_ik=True), sensor, "wrench", HANDOFF["handoff"], verify_motion=True
        )
        for _ in range(3000):
            if not actor.advance() or actor.phase == "Lowering gripper":
                break
        assert actor.outcome is None and actor.phase == "Lowering gripper"
        observations = [e for e in actor.evidence if e["kind"] == "camera"]
        prediction = observations[-1]["prediction"]
        assert prediction["appearance_recovery"] == "normalized_color_in_shadow"
        # Evaluation truth is read only after image inference and robot commands.
        assert np.linalg.norm(prediction["position_m"] - b.observe()["wrench"]) < 0.005
    finally:
        sensor.close()
        b.close()


def test_measured_face_normal_forms_a_valid_robot_rotation_and_rejects_bad_data():
    prediction = {
        "status": "observed",
        "position_m": [0.45, 0, 0.022],
        "yaw_mod_pi_rad": 0.3,
        "fit_score": 0.9,
        "surface_normal": [0.08, 0, np.sqrt(1 - 0.08**2)],
    }
    observation = validate_observation("wrench", prediction, 1.0, 1.0)
    r = observed_rotation(observation)
    np.testing.assert_allclose(r.T @ r, np.eye(3), atol=1e-12)
    assert np.linalg.det(r) > 0
    for bad in [[0, 0, -1], [0, 0, np.nan], [1, 0, 0]]:
        with pytest.raises(ValueError, match="normal"):
            validate_observation("wrench", prediction | {"surface_normal": bad}, 1.0, 1.0)
