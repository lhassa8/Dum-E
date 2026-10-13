"""Experimental maintained IK backend; leaves all real physics in SimRobot.

Only robot joint readings enter this planner. Non-robot DOFs are constrained
to zero velocity in an independent kinematic configuration. This first adapter
has joint/velocity limits; it does not yet enable scene collision constraints.
"""

import time

import mink
import numpy as np

from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.scene import HOME


class MinkRobot(SimRobot):
    def __init__(self, bench, recover_ik=False, refine_cartesian=False):
        super().__init__(bench, recover_ik, refine_cartesian)
        if not recover_ik:
            raise ValueError("This experimental backend requires the bounded recovery port")
        assert np.array_equal(bench.model.jnt_dofadr[:7], np.arange(7))
        self.configuration = mink.Configuration(bench.model)
        self.task = mink.FrameTask("tcp", "site", position_cost=1.0, orientation_cost=1.0)
        self.freezing = mink.DofFreezingTask(bench.model, list(range(7, bench.model.nv)))
        self.limits = [
            mink.ConfigurationLimit(bench.model),
            mink.VelocityLimit(bench.model, {bench.model.joint(i).name: 12.0 for i in range(7)}),
        ]

    def _seed_solution(self, point, rotation, seed):
        began = time.perf_counter()
        q = self._bench.model.qpos0.copy()
        q[:7] = seed
        frozen = q[7:].copy()
        self.configuration.update(q)
        self.task.set_target(
            mink.SE3.from_rotation_and_translation(mink.SO3.from_matrix(rotation), point)
        )
        for iteration in range(120):
            joints = self.configuration.q[:7].copy()
            position_error, angle_error = self._pose_error(joints, point, rotation)
            if position_error < 0.0008 and angle_error < 0.008:
                self.ik_events.append(
                    {
                        "kind": "mink_pose_solve",
                        "iterations": iteration,
                        "position_error_m": position_error,
                        "orientation_error_rad": angle_error,
                        "latency_ms": (time.perf_counter() - began) * 1000,
                    }
                )
                return joints
            velocity = mink.solve_ik(
                self.configuration,
                [self.task],
                0.01,
                solver="daqp",
                damping=0.002,
                limits=self.limits,
                constraints=[self.freezing],
            )
            assert np.isfinite(velocity).all()
            assert np.max(np.abs(velocity[:7] * 0.01)) <= 0.120000001
            self.configuration.integrate_inplace(velocity, 0.01)
            q = self.configuration.q.copy()
            assert np.allclose(q[7:], frozen, atol=1e-12, rtol=0)
            q[:7] = np.clip(
                q[:7],
                self._bench.model.jnt_range[:7, 0] + 0.005,
                self._bench.model.jnt_range[:7, 1] - 0.005,
            )
            self.configuration.update(q)
        raise ValueError("Bounded Mink IK found no supported pose")

    def solve(self, point, rotation):
        point, rotation = np.asarray(point, float), np.asarray(rotation, float)
        if (
            point.shape != (3,)
            or rotation.shape != (3, 3)
            or not np.isfinite(point).all()
            or not np.isfinite(rotation).all()
        ):
            raise ValueError("Invalid robot target pose")
        try:
            return self._seed_solution(point, rotation, self.read().joints)
        except ValueError:
            return self._seed_solution(point, rotation, HOME)
