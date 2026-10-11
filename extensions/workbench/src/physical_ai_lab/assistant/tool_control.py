"""Physical tool delivery and bounded expressive joint gestures."""

import numpy as np

from physical_ai_lab.assistant.control import Outcome, PickPlace
from physical_ai_lab.assistant.scene import HOME
from physical_ai_lab.assistant.tasks import Step
from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS


class ToolDelivery(PickPlace):
    def __init__(self, bench, tool, returning=False):
        self.returning = returning
        targets = {**HANDOFF, "rack": TOOLS[tool]}
        super().__init__(bench, tool, "rack" if returning else "handoff", targets)
        self.carrying = False

    def pause(self):
        # Retain the generator, grip and waypoint progress; Stop never opens fingers.
        self.bench.data.ctrl[:7] = self.bench.data.qpos[:7]
        self.outcome = Outcome("interrupted", "Stopped. Placement is not confirmed.")

    def resume(self):
        # The arm settles during speech/ASR. Old interpolation frames can jerk from
        # a stale joint target, so rebuild the remaining path from measured state.
        self._replan()

    def _replan(self):
        xyz = self.bench.observe()[self.object]
        tcp = self.bench.data.site_xpos[self.bench.tcp]
        self.carrying = self.bench.data.ctrl[7] < 128 and np.linalg.norm(xyz - tcp) < 0.065
        self.initial_height = self.max_height = xyz[2]
        self.cancelled = False
        self.outcome = None
        self.frames = self._run()

    def redirect_to_rack(self):
        self.returning, self.destination = True, "rack"
        self._replan()
        return self

    def plan(self):
        if self.carrying:
            yield from self._carry_plan()
            return
        for step in super().plan():
            if step.phase == "Placing block":
                # A newly grasped tool can also settle inside the fingers. The
                # same measured offset used after a paused hold prevents pushing
                # it into the table when arriving from a different previous task.
                offset = (
                    self.bench.data.site_xpos[self.bench.tcp] - self.bench.observe()[self.object]
                )
                target = np.array(
                    [
                        *self.targets[self.destination],
                        max(0.026, self.bench.tool_support_height(self.object)),
                    ]
                )
                yield Step(step.phase, step.gripper, target + offset + [0, 0, 0.008])
            else:
                yield step

    def _carry_plan(self):
        # After a hold, the tool can settle lower within the fingers. Observe its
        # offset at each waypoint rather than pushing it into the table on descent.
        target = np.array([*self.targets[self.destination], 0.026])
        tcp = self.bench.data.site_xpos[self.bench.tcp].copy()
        yield Step("Lifting tool", 0, tcp + [0, 0, 0.12])
        yield Step("Checking grasp", 0, check_lift=True)
        offset = self.bench.data.site_xpos[self.bench.tcp] - self.bench.observe()[self.object]
        yield Step("Moving to target", 0, target + offset + [0, 0, 0.20])
        offset = self.bench.data.site_xpos[self.bench.tcp] - self.bench.observe()[self.object]
        target[2] = max(0.026, self.bench.tool_support_height(self.object))
        yield Step("Placing tool", 0, target + offset + [0, 0, 0.008])
        yield Step("Releasing", 255, ticks=28)
        yield Step("Withdrawing gripper", 255, target + [0, 0, 0.20])
        yield Step("Checking placement", 255, ticks=30)

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

    def __init__(self, bench, gesture, message, brief=False):
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
        self.brief = brief
        self.frames = self._run(gesture)

    def pause(self):
        self.bench.data.ctrl[:7] = self.bench.data.qpos[:7]
        self.outcome = Outcome("interrupted", "Stopped. I'll hold still.")

    def resume(self):
        self.outcome = None

    def _run(self, gesture):
        start = self.bench.data.qpos[:7].copy()
        # First withdraw to the elevated vendor home pose with the gripper open.
        poses = [HOME.copy()]
        for sign in [1, -1] if self.brief else [1, -1, 1, -1]:
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
            ticks = 14 if self.brief else 20
            for i in range(1, ticks + 1):
                amount = i / ticks
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


class ToolPerformance:
    """Verified delivery starts immediately; social gestures remain separate skills."""

    def __init__(self, bench, tool, returning=False, delivery=None):
        self.delivery = delivery or ToolDelivery(bench, tool, returning)
        self.bench = bench
        # A serial nod used to delay pickup by ~2 seconds and release the task
        # ~2 seconds late. Speech acknowledges handling; manipulation takes priority.
        # Different preceding skills can leave a very different IK branch. An
        # empty gripper takes a bounded elevated transit to the known ready pose
        # before a fresh grasp. This is motion preparation, not a social gesture.
        transit = (
            bench.data.ctrl[7] >= 128
            and not self.delivery.carrying
            and np.max(np.abs(bench.data.qpos[:7] - HOME)) > 0.4
        )
        self.current = EmptyTransit(bench) if transit else self.delivery
        self.stage = "transit" if transit else "delivery"
        self.outcome = None
        self.notifications = []

    @property
    def object(self):
        return self.delivery.object

    @property
    def destination(self):
        return self.delivery.destination

    @property
    def initial_height(self):
        return self.delivery.initial_height

    @property
    def max_height(self):
        return self.delivery.max_height

    @property
    def phase(self):
        return self.current.phase

    def pause(self):
        self.current.pause()
        self.outcome = Outcome("interrupted", "Stopped. Placement is not confirmed.")

    def stop(self):
        self.pause()

    def resume(self):
        self.outcome = None
        self.current.resume()

    def return_to_rack(self):
        return ToolPerformance(
            self.bench, self.object, returning=True, delivery=self.delivery.redirect_to_rack()
        )

    def redirect_to_handoff(self):
        self.delivery.returning, self.delivery.destination = False, "handoff"
        self.delivery._replan()
        return ToolPerformance(self.bench, self.object, delivery=self.delivery)

    def advance(self):
        if self.outcome:
            return False
        if self.current.advance():
            return True
        if self.stage == "transit":
            self.current, self.stage = self.delivery, "delivery"
            return True
        self.outcome = self.delivery.outcome
        return False


class EmptyTransit:
    """Move an empty hand to the elevated ready pose without a decorative detour."""

    def __init__(self, bench):
        if bench.data.ctrl[7] < 128:
            raise ValueError("Ready-pose transit requires an open, empty grip")
        self.bench = bench
        self.phase = "Repositioning above the workbench"
        self.outcome = None
        self.frames = self._run()

    def _run(self):
        start = self.bench.data.qpos[:7].copy()
        ticks = max(40, int(np.max(np.abs(HOME - start)) / 0.025))
        for t in range(1, ticks + 1):
            a = t / ticks
            a = a * a * (3 - 2 * a)
            self.bench.tick(start + (HOME - start) * a, 255)
            yield
        for _ in range(12):
            self.bench.tick(HOME, 255)
            yield
        self.outcome = Outcome("expressed", "")

    def pause(self):
        self.bench.data.ctrl[:7] = self.bench.data.qpos[:7]
        self.outcome = Outcome("interrupted", "Stopped. I'll hold still.")

    def resume(self):
        self.outcome = None
        self.frames = self._run()

    def advance(self):
        if self.outcome:
            return False
        try:
            next(self.frames)
            return True
        except StopIteration:
            return False


class ToolChange:
    """Return an interrupted tool, verify its rack placement, then start the new skill."""

    def __init__(self, bench, paused, tool, returning=False):
        self.bench = bench
        self.current = paused.return_to_rack()
        self.previous_tool = self.current.object
        self.requested_tool, self.returning = tool, returning
        self.stage = "return_previous"
        self.outcome = None
        self.notifications = []
        self.verified_steps = []

    @property
    def object(self):
        return self.current.object

    @property
    def destination(self):
        return self.current.destination

    @property
    def initial_height(self):
        return self.current.initial_height

    @property
    def max_height(self):
        return self.current.max_height

    @property
    def phase(self):
        if self.stage == "return_previous":
            return (
                f"Returning {self.previous_tool} before {self.requested_tool}: {self.current.phase}"
            )
        return self.current.phase

    def pause(self):
        self.current.pause()
        self.outcome = Outcome("interrupted", "Stopped. Placement is not confirmed.")

    def stop(self):
        self.pause()

    def resume(self):
        self.outcome = None
        self.current.resume()

    def return_to_rack(self):
        return self.current.return_to_rack()

    def redirect_to_handoff(self):
        return self.current.redirect_to_handoff()

    def advance(self):
        if self.outcome:
            return False
        if self.current.advance():
            return True
        outcome = self.current.outcome
        self.verified_steps.append(
            {
                "object": self.object,
                "destination": self.destination,
                "status": outcome.status,
                "distance_m": outcome.distance_m,
            }
        )
        if self.stage == "return_previous":
            if outcome.status != "success":
                self.outcome = Outcome(
                    "failed",
                    f"I couldn't return the {self.previous_tool} "
                    "reliably. I haven't started the new pickup.",
                    outcome.distance_m,
                )
                return False
            self.notifications.append(outcome.message)
            self.current = ToolPerformance(self.bench, self.requested_tool, self.returning)
            self.stage = "requested"
            return True
        self.outcome = outcome
        return False
