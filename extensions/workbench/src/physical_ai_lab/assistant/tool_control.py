"""Physical tool delivery and bounded expressive joint gestures."""

import numpy as np

from physical_ai_lab.assistant.control import Outcome, PickPlace
from physical_ai_lab.assistant.scene import HOME
from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS


class ToolDelivery(PickPlace):
    def __init__(self, bench, tool, returning=False):
        self.returning = returning
        targets = {**HANDOFF, "rack": TOOLS[tool]}
        super().__init__(bench, tool, "rack" if returning else "handoff", targets)

    def advance(self):
        more = super().advance()
        self.phase = self.phase.replace("block", "tool").replace("target", "handoff tray")
        if not more and self.outcome:
            if self.outcome.status == "success":
                message = (
                    f"The {self.object} is back in its tool tray."
                    if self.returning
                    else f"Your {self.object} is ready in the handoff tray."
                )
                self.outcome = Outcome("success", message, self.outcome.distance_m)
            elif self.outcome.status == "failed":
                self.outcome = Outcome(
                    "failed",
                    "I couldn't deliver the tool reliably. It isn't confirmed ready for you.",
                    self.outcome.distance_m,
                )
        return more


class Gesture:
    """Expressive motion is joint control, never object movement or fake task success."""

    def __init__(self, bench, gesture, message):
        if gesture not in {"wave", "nod", "curious", "celebrate"}:
            raise ValueError("Unknown gesture")
        self.bench, self.message = bench, message
        self.object, self.destination = None, gesture
        self.initial_height = self.max_height = 0
        self.phase = {
            "wave": "Waving hello",
            "nod": "Nodding",
            "curious": "Listening",
            "celebrate": "A little victory wiggle",
        }[gesture]
        self.outcome = None
        self.frames = self._run(gesture)

    def _run(self, gesture):
        start = self.bench.data.qpos[:7].copy()
        # First withdraw to the elevated vendor home pose with the gripper open.
        poses = [HOME.copy()]
        for sign in [1, -1, 1, -1]:
            pose = HOME.copy()
            if gesture in {"wave", "celebrate"}:
                pose[0] += sign * 0.16
                pose[6] += sign * 0.18
            elif gesture == "nod":
                pose[5] += sign * 0.12
            else:
                pose[6] += sign * 0.18
            poses.append(pose)
        poses.append(HOME.copy())
        for pose in poses:
            pose = np.clip(
                pose,
                self.bench.model.jnt_range[:7, 0] + 0.01,
                self.bench.model.jnt_range[:7, 1] - 0.01,
            )
            for i in range(1, 21):
                amount = i / 20
                amount = amount * amount * (3 - 2 * amount)
                self.bench.tick(start + (pose - start) * amount, 255)
                yield
            start = pose
        self.outcome = Outcome("expressed", self.message)

    def stop(self):
        self.bench.data.ctrl[:7] = self.bench.data.qpos[:7]
        self.outcome = Outcome("interrupted", "Stopped. I'll hold still.")
        self.phase = "Stopped"

    def advance(self):
        if self.outcome:
            return False
        try:
            next(self.frames)
            return True
        except StopIteration:
            return False
