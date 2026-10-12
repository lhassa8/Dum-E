"""Simulator implementation of a robot-only motion/proprioception port."""

from time import perf_counter

import mujoco
import numpy as np

from physical_ai_lab.assistant.camera_control import RobotReading
from physical_ai_lab.assistant.scene import HOME


class SimRobot:
    def __init__(self, bench, recover_ik=False):
        self._bench = bench
        self.ready_rotation = bench.orientation.copy()
        self.recover_ik = recover_ik
        self.ik_events = []
        self._kinematic_data = mujoco.MjData(bench.model) if recover_ik else None

    def _pose_error(self, joints, point, rotation):
        b, data = self._bench, self._kinematic_data
        data.qpos[:7] = joints
        mujoco.mj_forward(b.model, data)
        actual_rotation = data.site_xmat[b.tcp].reshape(3, 3)
        angle = np.arccos(np.clip((np.trace(actual_rotation.T @ rotation) - 1) / 2, -1, 1))
        return float(np.linalg.norm(point - data.site_xpos[b.tcp])), float(angle)

    def _seed_solution(self, point, rotation, seed):
        b, data = self._bench, self._kinematic_data
        data.qpos[:7] = seed
        jp, jr = np.zeros((3, b.model.nv)), np.zeros((3, b.model.nv))
        for _ in range(120):
            mujoco.mj_forward(b.model, data)
            actual = data.site_xmat[b.tcp].reshape(3, 3)
            error = np.r_[
                point - data.site_xpos[b.tcp],
                0.5 * sum(np.cross(actual[:, i], rotation[:, i]) for i in range(3)),
            ]
            position_error, angle_error = self._pose_error(data.qpos[:7], point, rotation)
            if position_error < 0.0008 and angle_error < 0.008:
                return data.qpos[:7].copy()
            mujoco.mj_jacSite(b.model, data, jp, jr, b.tcp)
            jac = np.vstack([jp[:, :7], jr[:, :7]])
            delta = jac.T @ np.linalg.solve(jac @ jac.T + 0.002 * np.eye(6), error)
            data.qpos[:7] = np.clip(
                data.qpos[:7] + np.clip(delta, -0.12, 0.12),
                b.model.jnt_range[:7, 0] + 0.005,
                b.model.jnt_range[:7, 1] - 0.005,
            )
        raise ValueError("Bounded robot IK recovery found no supported pose")

    def cartesian_path(self, start, point, rotation, ticks):
        if not self.recover_ik:
            raise ValueError("Cartesian lift planning requires the robot recovery port")
        previous = self.read().joints
        path = []
        for index in range(1, ticks + 1):
            a = index / ticks
            a = a * a * (3 - 2 * a)
            waypoint = start + (point - start) * a
            answer = self._seed_solution(waypoint, rotation, previous)
            if np.max(np.abs(answer - previous)) > 0.075:
                raise ValueError("Cartesian lift would change robot IK branch; holding")
            path.append(answer)
            previous = answer
        return np.asarray(path)

    def read(self):
        b = self._bench
        return RobotReading(
            b.data.qpos[:7].copy(),
            b.data.site_xpos[b.tcp].copy(),
            b.data.site_xmat[b.tcp].reshape(3, 3).copy(),
            float(b.data.qpos[7:9].sum()),
            bool(b.data.ctrl[7] < 128),
            float(b.data.time),
            b.data.qvel[:7].copy(),
            b.data.actuator_force[:8].copy(),
        )

    def solve(self, point, rotation):
        b = self._bench
        point, rotation = np.asarray(point, float), np.asarray(rotation, float)
        if (
            point.shape != (3,)
            or rotation.shape != (3, 3)
            or not np.isfinite(point).all()
            or not np.isfinite(rotation).all()
        ):
            raise ValueError("Invalid robot target pose")
        previous = b.orientation
        try:
            b.orientation = rotation
            began = perf_counter()
            try:
                answer = b.solve(point)
                if not self.recover_ik:
                    return answer
                position_error, angle_error = self._pose_error(answer, point, rotation)
                if position_error < 0.0008 and angle_error < 0.008:
                    return answer
            except ValueError:
                if not self.recover_ik:
                    raise
            answer = self._seed_solution(point, rotation, HOME)
            position_error, angle_error = self._pose_error(answer, point, rotation)
            self.ik_events.append(
                {
                    "kind": "ik_home_recovery",
                    "target_m": point.tolist(),
                    "position_error_m": position_error,
                    "orientation_error_rad": angle_error,
                    "latency_ms": (perf_counter() - began) * 1000,
                }
            )
            return answer
        finally:
            b.orientation = previous

    def tick(self, joints=None, gripper=None):
        self._bench.tick(joints, gripper)

    def correct_joint_command(self, command, desired_joints):
        b = self._bench
        corrected = command + 0.5 * (desired_joints - self.read().joints)
        return np.clip(
            corrected, b.model.jnt_range[:7, 0] + 0.005, b.model.jnt_range[:7, 1] - 0.005
        )

    def hold(self):
        self._bench.data.ctrl[:7] = self._bench.data.qpos[:7]

    def observation_point(self):
        # Known robot home kinematics, not a nominal tool position or teleport.
        data = mujoco.MjData(self._bench.model)
        data.qpos[:7] = HOME
        mujoco.mj_forward(self._bench.model, data)
        return data.site_xpos[self._bench.tcp].copy()
