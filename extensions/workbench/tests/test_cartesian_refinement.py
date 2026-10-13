"""Bounded refinement cannot turn a discontinuous or unsolved path into motion."""

from types import SimpleNamespace

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
