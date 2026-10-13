"""Bounded refinement cannot turn a discontinuous or unsolved path into motion."""

from types import SimpleNamespace

import mujoco
import numpy as np
import pytest

from physical_ai_lab.assistant.camera_robot import CartesianStepRefusal, SimRobot
from physical_ai_lab.assistant.tool_scene import ToolWorkbench


@pytest.mark.parametrize("enabled,expected", [(False, [40]), (True, [40, 80, 160])])
def test_persistent_discontinuity_refuses_without_physics_changes(enabled, expected):
    bench = ToolWorkbench()
    try:
        robot = SimRobot(bench, recover_ik=True, refine_cartesian=enabled)
        counts = []
        original = robot._cartesian_path

        def counted(start, point, rotation, ticks):
            counts.append(ticks)
            return original(start, point, rotation, ticks)

        robot._cartesian_path = counted
        robot._seed_solution = lambda point, rotation, seed: seed + 0.076
        before = bench.data.qpos.copy(), bench.data.qvel.copy(), bench.data.ctrl.copy()
        reading = robot.read()
        with pytest.raises(CartesianStepRefusal):
            robot.cartesian_path(reading.tcp_m, reading.tcp_m + [0, 0, 0.2], reading.rotation, 40)
        assert counts == expected and not robot.ik_events
        for actual, old in zip(
            [bench.data.qpos, bench.data.qvel, bench.data.ctrl], before, strict=True
        ):
            np.testing.assert_array_equal(actual, old)
    finally:
        bench.close()


def test_unsolved_ik_is_not_retried_as_a_sampling_problem():
    robot = SimRobot(SimpleNamespace(orientation=np.eye(3)), refine_cartesian=True)
    robot.recover_ik = True
    calls = []

    def unsolved(*args):
        calls.append(1)
        raise ValueError("No supported IK pose")

    robot._cartesian_path = unsolved
    with pytest.raises(ValueError, match="No supported IK"):
        robot.cartesian_path(np.zeros(3), np.ones(3), np.eye(3), 40)
    assert calls == [1]


def test_refinement_has_an_absolute_waypoint_cap():
    robot = SimRobot(SimpleNamespace(orientation=np.eye(3)), refine_cartesian=True)
    robot.recover_ik = True
    counts = []

    def refused(start, point, rotation, ticks):
        counts.append(ticks)
        raise CartesianStepRefusal("Continuity limit")

    robot._cartesian_path = refused
    with pytest.raises(CartesianStepRefusal, match="exhausted"):
        robot.cartesian_path(np.zeros(3), np.ones(3), np.eye(3), 150)
    assert counts == [150, 300]


def test_cartesian_carry_changes_full_pose_continuously_without_physics_writes():
    bench = ToolWorkbench()
    robot = SimRobot(bench, recover_ik=True, refine_cartesian=True)
    try:
        reading = robot.read()
        point = reading.tcp_m + [0.03, 0.015, 0.03]
        angle = 0.2
        yaw = np.array(
            [[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]]
        )
        rotation = yaw @ reading.rotation
        original = bench.data.qpos.copy(), bench.data.qvel.copy(), bench.data.ctrl.copy()
        path = robot.cartesian_path(reading.tcp_m, point, rotation, 40, interpolate_rotation=True)
        assert np.max(np.abs(np.diff(np.vstack([reading.joints, path]), axis=0))) <= 0.075
        independent = mujoco.MjData(bench.model)
        previous = reading.rotation
        for joints in path:
            independent.qpos[:7] = joints
            mujoco.mj_forward(bench.model, independent)
            measured = independent.site_xmat[bench.tcp].reshape(3, 3).copy()
            step_angle = np.arccos(np.clip((np.trace(previous.T @ measured) - 1) / 2, -1, 1))
            assert step_angle < 0.04
            previous = measured
        assert np.linalg.norm(independent.site_xpos[bench.tcp] - point) < 0.0008
        assert np.arccos(np.clip((np.trace(previous.T @ rotation) - 1) / 2, -1, 1)) < 0.008
        for actual, before in zip(
            [bench.data.qpos, bench.data.qvel, bench.data.ctrl], original, strict=True
        ):
            np.testing.assert_array_equal(actual, before)
    finally:
        bench.close()
