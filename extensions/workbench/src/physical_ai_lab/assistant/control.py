"""Bounded waypoint controller, physical grasp, release and outcome checks."""

from dataclasses import dataclass

import numpy as np

from physical_ai_lab.assistant.tasks import MoveTask, plan_pick_place


@dataclass(frozen=True)
class Outcome:
    status: str
    message: str
    distance_m: float | None = None


class PickPlace:
    def __init__(self, bench, object_name, destination, targets=None):
        self.targets = bench.targets if targets is None else targets
        if object_name not in bench.observe() or destination not in self.targets:
            raise ValueError("Unknown object or target")
        self.bench, self.object, self.destination = bench, object_name, destination
        self.cancelled = False
        self.phase = "Preparing"
        self.outcome = None
        self.initial_height = bench.observe()[object_name][2]
        self.max_height = self.initial_height
        self.frames = self._run()

    def stop(self):
        self.cancelled = True
        self.bench.hold_joints()
        self.outcome = Outcome(
            "interrupted", "Stopped. The task was interrupted; placement is not confirmed."
        )
        self.phase = "Stopped"

    def _motion(self, point, label, gripper=255):
        self.phase = label
        start = self.bench.data.qpos[:7].copy()
        end = self.bench.solve(point)
        ticks = max(40, int(np.max(np.abs(end - start)) / 0.025))
        for t in range(1, ticks + 1):
            if self.cancelled:
                return
            amount = t / ticks
            amount = amount * amount * (3 - 2 * amount)
            self.bench.tick(start + (end - start) * amount, gripper)
            self.max_height = max(self.max_height, self.bench.observe()[self.object][2])
            yield
        for _ in range(12):
            if self.cancelled:
                return
            self.bench.tick(end, gripper)
            yield

    def _wait(self, ticks, gripper):
        for _ in range(ticks):
            if self.cancelled:
                return
            self.bench.tick(gripper=gripper)
            self.max_height = max(self.max_height, self.bench.observe()[self.object][2])
            yield

    def _run(self):
        try:
            steps = self.plan()
            for step in steps:
                if self.cancelled:
                    return
                self.phase = step.phase
                if step.check_lift:
                    if self.max_height - self.initial_height < 0.08:
                        self.outcome = Outcome(
                            "failed",
                            "The block did not lift with the gripper. "
                            "I have not completed the move.",
                        )
                        return
                elif step.point is not None:
                    yield from self._motion(step.point, step.phase, step.gripper)
                else:
                    yield from self._wait(step.ticks, step.gripper)
            if self.cancelled:
                return
            target = np.array(self.targets[self.destination])
            actual = self.bench.observe()[self.object]
            distance = float(np.linalg.norm(actual[:2] - target))
            address = self.bench.model.joint(f"{self.object}_joint").dofadr[0]
            speed = float(np.linalg.norm(self.bench.data.qvel[address : address + 3]))
            placed = distance < 0.035 and actual[2] < 0.04 and speed < 0.03
            self.outcome = Outcome(
                "success" if placed else "failed",
                f"The {self.object} block is in the {self.destination} target. Placement checked."
                if placed
                else "The block is not resting in the requested target. "
                "I have not completed the move.",
                distance,
            )
            self.phase = "Complete" if placed else "Placement failed"
        except (ValueError, FloatingPointError) as error:
            self.outcome = Outcome("failed", str(error))
            self.phase = "Task failed"

    def plan(self):
        return plan_pick_place(
            self.bench.observe(), MoveTask(self.object, self.destination), self.targets
        )

    def advance(self):
        if self.outcome is not None:
            return False
        try:
            next(self.frames)
            return True
        except StopIteration:
            if self.outcome is None:
                self.outcome = Outcome("failed", "The task ended without a verified placement.")
            return False
