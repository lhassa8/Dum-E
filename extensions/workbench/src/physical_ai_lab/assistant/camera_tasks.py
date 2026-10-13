"""Camera-only motion/task routing with a separate simulation outcome evaluator."""

import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from physical_ai_lab.assistant.camera_control import CameraDelivery, validate_observation
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.control import Outcome
from physical_ai_lab.assistant.perception import locate_tools
from physical_ai_lab.assistant.perception_scene import CameraSensor
from physical_ai_lab.assistant.tool_control import ToolChange
from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS


class MotionCancelled(Exception):
    """The owner must hold; a stale camera result cannot command a tick."""


class GuardedRobot(SimRobot):
    def __init__(self, bench, cancelled):
        super().__init__(bench, recover_ik=True, refine_cartesian=True)
        self.cancelled = cancelled

    def tick(self, joints=None, gripper=None):
        if self.cancelled():
            raise MotionCancelled()
        super().tick(joints, gripper)


class CameraTasks:
    def __init__(self, bench, epoch=lambda: 0, stopping=lambda: False):
        self.bench = bench
        self.epoch, self.stopping = epoch, stopping
        self.sensor = CameraSensor(bench)
        self.racks = {}
        self.delivered = None
        self.active = None
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="camera-perception")
        # Evaluator-only callback and targets; never supplied to motion ports.
        self.truth = bench.observe
        self.judge_racks = {name: xyz[:2].copy() for name, xyz in self.truth().items()}
        for capture in [self.sensor.capture_timed, self.sensor.capture_alternate_timed]:
            sample = capture()
            predictions = self.perceive(sample.frame)
            for name in TOOLS:
                if name in self.racks:
                    continue
                try:
                    observed = validate_observation(
                        name, predictions[name], sample.captured_s, bench.data.time
                    )
                except ValueError:
                    continue
                self.racks[name] = observed.position_m[:2].copy()
            if len(self.racks) == len(TOOLS):
                break

    def task(self, bench, tool, returning=False):
        if bench is not self.bench or tool not in self.racks:
            raise ValueError("No camera-confirmed rack context for that tool")
        task = CameraPerformance(self, tool, returning)
        self.active = task
        return task

    def select(self, tool, returning=False, paused=None):
        if tool not in self.racks:
            raise ValueError("No camera-confirmed rack context for that tool")
        if paused is not None and not isinstance(paused, (CameraPerformance, ToolChange)):
            raise ValueError("Resume the interrupted gesture before changing tasks")
        if paused is not None:
            if paused.object == tool:
                return paused.return_to_rack() if returning else paused.redirect_to_handoff()
            return ToolChange(self.bench, paused, tool, returning, task_factory=self.task)
        if not returning and self.delivered and self.delivered != tool:
            previous = self.task(self.bench, self.delivered, returning=True)
            return ToolChange(self.bench, previous, tool, task_factory=self.task)
        return self.task(self.bench, tool, returning)

    def inventory(self):
        return {
            name: "handoff tray (verified previous task)"
            if name == self.delivered
            else "camera-confirmed initial rack; current location not recently observed"
            if name in self.racks
            else "rack not visually confirmed"
            for name in TOOLS
        }

    def perceive(self, frame):
        expected = self.active.expected_epoch if self.active else self.epoch()
        if self.stopping() or self.epoch() != expected:
            raise MotionCancelled()
        future = self.pool.submit(locate_tools, frame)
        self.bench.hold_joints()
        while not future.done():
            started = time.monotonic()
            if self.stopping() or self.epoch() != expected:
                future.cancel()
                raise MotionCancelled()
            before = self.active.robot.read() if self.active else None
            self.bench.tick()
            if self.active:
                self.active.measure()  # Evaluator only; no return value feeds perception.
                self.active.actor._check_carry_grip(before)
            time.sleep(max(0, 0.032 - (time.monotonic() - started)))
        if self.stopping() or self.epoch() != expected:
            raise MotionCancelled()
        return future.result()

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)
        self.sensor.close()


class CameraPerformance:
    def __init__(self, hub, tool, returning=False):
        self.hub, self.object = hub, tool
        self.destination = "rack" if returning else "handoff"
        self.expected_epoch = hub.epoch()
        self.robot = GuardedRobot(hub.bench, self.cancelled)
        self.actor = CameraDelivery(
            self.robot,
            hub.sensor,
            tool,
            hub.racks[tool] if returning else HANDOFF["handoff"],
            rack_xy=hub.racks[tool],
            verify_motion=True,
            linear_lifts=True,
            center_grasp=True,
            safe_handoff=True,
            alternate_view=True,
            release_fallback=True,
            phase_recovery=True,
            verify_release=True,
            recover_grip=True,
            perceive=hub.perceive,
        )
        self.initial = {name: xyz.copy() for name, xyz in hub.truth().items()}
        self.initial_height = self.max_height = self.initial[tool][2]
        self.disturbance = 0.0
        self.outcome = None
        self.notifications = []
        self.verified_steps = []
        self.cancelled_generation = False

    @property
    def phase(self):
        return self.actor.phase

    def cancelled(self):
        return self.hub.stopping() or self.hub.epoch() != self.expected_epoch

    def measure(self):
        positions = self.hub.truth()
        self.max_height = max(self.max_height, positions[self.object][2])
        self.disturbance = max(
            self.disturbance,
            max(
                float(np.linalg.norm(xyz - self.initial[name]))
                for name, xyz in positions.items()
                if name != self.object
            ),
        )

    def pause(self):
        self.actor.pause()
        self.outcome = self.actor.outcome
        self.measure()

    def resume(self):
        self.expected_epoch = self.hub.epoch()
        if self.cancelled_generation and self.actor.carrying:
            self.robot.hold()
            self.outcome = Outcome(
                "failed",
                "Stopped during camera processing. Choose a new destination for a fresh plan.",
            )
            return
        self.actor.resume()
        self.outcome = self.actor.outcome

    def _redirect(self, returning):
        self.expected_epoch = self.hub.epoch()
        self.destination = "rack" if returning else "handoff"
        target = self.hub.racks[self.object] if returning else HANDOFF["handoff"]
        if self.actor.carrying and self.actor._grip_present():
            self.actor.target = np.asarray(target).copy()
            self.actor.orientation = self.robot.read().rotation.copy()
            self.actor.revision += 1
            self.actor.reoriented_carry = False
            self.actor.planned_neighbors = None
            self.actor.outcome = None
            self.actor.frames.close()
            self.actor.frames = self.actor._redirect()
            self.cancelled_generation = False
        elif self.actor.outcome and self.actor.outcome.status == "interrupted":
            self.actor.target = np.asarray(target).copy()
            self.actor.resume()
        elif not self.actor.carrying and self.robot.read().gap_m >= 0.075:
            # Fresh command after an already completed first leg, not an episode reset.
            self.actor.frames.close()
            self.actor.target = np.asarray(target).copy()
            self.actor.outcome = None
            self.actor.frames = self.actor._run()
        else:
            raise ValueError("Cannot redirect an uncertain camera grasp")
        self.outcome = self.actor.outcome
        self.hub.active = self
        return self

    def return_to_rack(self):
        return self._redirect(True)

    def redirect_to_handoff(self):
        return self._redirect(False)

    def advance(self):
        if self.outcome:
            return False
        try:
            more = self.actor.advance()
        except MotionCancelled:
            self.cancelled_generation = True
            self.pause()
            # Keep the owner loop's controller until it consumes the Stop event.
            return True
        self.measure()
        if more:
            return True
        outcome = self.actor.outcome
        if outcome is None:
            self.outcome = Outcome("failed", "Camera task ended without a verified outcome.")
        elif outcome.status != "released_unverified":
            self.outcome = outcome
        else:
            actual = self.hub.truth()[self.object]
            target = (
                self.hub.judge_racks[self.object]
                if self.destination == "rack"
                else HANDOFF["handoff"]
            )
            distance = float(np.linalg.norm(actual[:2] - target))
            bench = self.hub.bench
            address = bench.model.joint(f"{self.object}_joint").dofadr[0]
            speed = float(np.linalg.norm(bench.data.qvel[address : address + 3]))
            passed = (
                distance < 0.035
                and actual[2] < 0.04
                and speed < 0.03
                and self.max_height - self.initial_height >= 0.08
                and self.disturbance < 0.004
                and bench.data.qpos[7:9].sum() > 0.07
            )
            location = "rack" if self.destination == "rack" else "handoff tray"
            self.outcome = Outcome(
                "success" if passed else "failed",
                f"The {self.object} is ready in the {location}."
                if passed
                else "Placement did not pass the independent physical checks.",
                distance,
            )
            if passed:
                self.hub.delivered = (
                    self.object
                    if self.destination == "handoff"
                    else (None if self.hub.delivered == self.object else self.hub.delivered)
                )
        return False
