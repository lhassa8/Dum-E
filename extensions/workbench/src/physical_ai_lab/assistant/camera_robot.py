"""Simulator implementation of a robot-only motion/proprioception port."""

from physical_ai_lab.assistant.camera_control import RobotReading


class SimRobot:
    def __init__(self, bench):
        self._bench = bench
        self.ready_rotation = bench.orientation.copy()

    def read(self):
        b = self._bench
        return RobotReading(
            b.data.qpos[:7].copy(),
            b.data.site_xpos[b.tcp].copy(),
            b.data.site_xmat[b.tcp].reshape(3, 3).copy(),
            float(b.data.qpos[7:9].sum()),
            bool(b.data.ctrl[7] < 128),
            float(b.data.time),
        )

    def solve(self, point, rotation):
        b = self._bench
        previous = b.orientation
        try:
            b.orientation = rotation
            return b.solve(point)
        finally:
            b.orientation = previous

    def tick(self, joints=None, gripper=None):
        self._bench.tick(joints, gripper)

    def hold(self):
        self._bench.data.ctrl[:7] = self._bench.data.qpos[:7]
