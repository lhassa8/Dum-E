"""Experimental image-informed manipulation through narrow sensor/robot ports.

No object-state or simulator-model access in the actor. Carrying uses an explicit
rigid-grasp estimate from the last camera pose and robot forward kinematics. It
is an inference, not a visual measurement of a held tool or proof of success.
"""

from dataclasses import dataclass
from time import perf_counter

import numpy as np

from physical_ai_lab.assistant.control import Outcome
from physical_ai_lab.assistant.perception import locate_tools


def rotation_z(yaw):
    c, s = np.cos(yaw), np.sin(yaw)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


@dataclass(frozen=True)
class RobotReading:
    joints: np.ndarray
    tcp_m: np.ndarray
    rotation: np.ndarray
    gap_m: float
    closing_command: bool
    time_s: float


@dataclass(frozen=True)
class ToolObservation:
    name: str
    position_m: np.ndarray
    yaw_mod_pi_rad: float
    fit_score: float
    captured_s: float


def validate_observation(name, prediction, captured_s, now_s):
    """Provisional motion gate, separate from the frozen D1 accuracy judge."""
    if name not in {"screwdriver", "wrench", "hammer"}:
        raise ValueError("Unknown tool")
    if (
        not np.isfinite([captured_s, now_s]).all()
        or now_s < captured_s
        or now_s - captured_s > 0.25
    ):
        raise ValueError("Camera observation is stale; no motion planned")
    score = float(prediction.get("fit_score", 0))
    if prediction.get("status") != "observed" or not np.isfinite(score) or not 0.8 <= score <= 1:
        raise ValueError("Handle is missing, ambiguous or a weak geometric fit; no motion planned")
    xyz = np.asarray(prediction.get("position_m"), dtype=float)
    yaw = float(prediction.get("yaw_mod_pi_rad", np.nan))
    if xyz.shape != (3,) or not np.isfinite(xyz).all() or not np.isfinite(yaw):
        raise ValueError("Camera pose is invalid; no motion planned")
    if not (0.30 < xyz[0] < 0.78 and abs(xyz[1]) < 0.36 and 0.015 < xyz[2] < 0.05):
        raise ValueError("Camera target is outside the supported tabletop volume")
    return ToolObservation(name, xyz.copy(), yaw, float(prediction["fit_score"]), captured_s)


def support_clearance(name, rotation):
    """Known tool catalog, not simulator geometry or measured object rotation.

    Conservative over the unknown 180-degree handle sign. Covers the current
    primitive boxes and capsules only; cannot establish real-tool clearance.
    """
    boxes = [([0, 0, 0], [0.022, 0.028, 0.022])]
    capsules = []  # local center, half length along local Y, radius
    if name == "screwdriver":
        capsules = [([0, -0.015, 0], 0.040, 0.020), ([0, 0.070, 0], 0.045, 0.004)]
        boxes.append(([0, 0.116, 0], [0.007, 0.011, 0.003]))
    elif name == "wrench":
        capsules = [([0, -0.005, 0], 0.055, 0.017)]
        boxes += [([0, 0.060, 0], [0.028, 0.014, 0.017])]
        boxes += [([side * 0.022, 0.085, 0], [0.010, 0.020, 0.017]) for side in [-1, 1]]
    elif name == "hammer":
        capsules = [([0, 0, 0], 0.070, 0.019)]
        boxes.append(([0, 0.080, 0], [0.045, 0.022, 0.022]))
    else:
        raise ValueError("Unknown tool catalog")
    clearance = 0.0
    for sign in [1, -1]:
        row = (rotation @ np.diag([sign, sign, 1]))[2]
        for center, size in boxes:
            clearance = max(clearance, float(np.abs(row) @ size - row @ center))
        for center, half, radius in capsules:
            clearance = max(clearance, float(radius + half * abs(row[1]) - row @ center))
    return clearance


class CameraDelivery:
    """Experimental pickup/release; verified placement belongs to an external judge."""

    def __init__(self, robot, camera, tool, destination_xy, rack_xy=None):
        self.robot, self.camera, self.object = robot, camera, tool
        self.target = np.asarray(destination_xy, dtype=float).copy()
        if self.target.shape != (2,) or not np.isfinite(self.target).all():
            raise ValueError("Invalid destination")
        self.rack_xy = None if rack_xy is None else np.asarray(rack_xy, dtype=float).copy()
        self.phase, self.outcome = "Observing tool", None
        self.carrying = False
        self.observation = None
        self.offset_local = self.body_rotation_local = None
        self.orientation = None
        self.revision = 0
        self.evidence = []
        self.frames = self._run()

    def _observe(self):
        start = perf_counter()
        sample = self.camera.capture_timed()
        captured_s = sample.captured_s
        prediction = locate_tools(sample.frame)[self.object]
        self.evidence.append(
            {
                "kind": "camera",
                "phase": self.phase,
                "captured_s": captured_s,
                "latency_ms": (perf_counter() - start) * 1000,
                "prediction": prediction,
            }
        )
        observation = validate_observation(
            self.object, prediction, captured_s, self.robot.read().time_s
        )
        self.observation = observation
        return observation

    def _grip_present(self):
        reading = self.robot.read()
        # Encoder gap is a simulated tactile proxy, not object identification.
        return reading.closing_command and 0.015 < reading.gap_m < 0.070

    def _motion(self, point, phase, grip):
        self.phase = phase
        end = self.robot.solve(point, self.orientation)
        revision = -1
        remaining = 12
        while remaining:
            if revision != self.revision:
                start = self.robot.read().joints
                ticks = max(40, int(np.max(np.abs(end - start)) / 0.025))
                index, revision = 0, self.revision
                remaining = ticks + 12
            index += 1
            a = min(index / ticks, 1.0)
            a = a * a * (3 - 2 * a)
            self.robot.tick(start + (end - start) * a, grip)
            if self.carrying and not self._grip_present():
                raise ValueError("Gripper no longer indicates a held handle; holding position")
            remaining -= 1
            yield

    def _wait(self, count, grip, phase):
        self.phase = phase
        for _ in range(count):
            self.robot.tick(gripper=grip)
            yield

    def _estimate(self):
        reading = self.robot.read()
        center = reading.tcp_m - reading.rotation @ self.offset_local
        rotation = reading.rotation @ self.body_rotation_local
        return center, rotation

    def _place_point(self):
        reading = self.robot.read()
        _, rotation = self._estimate()
        clearance = max(0.026, support_clearance(self.object, rotation))
        point = np.array([*self.target, clearance + 0.012])
        return point + reading.rotation @ self.offset_local

    def _run(self):
        try:
            obs = self._observe()
            self.orientation = rotation_z(obs.yaw_mod_pi_rad) @ self.robot.ready_rotation
            if self.rack_xy is None:
                self.rack_xy = obs.position_m[:2].copy()
            yield from self._motion(obs.position_m + [0, 0, 0.20], "Approaching tool", 255)
            self.phase = "Reobserving before grasp"
            obs = self._observe()
            yield from self._motion(obs.position_m + [0, 0, 0.002], "Lowering gripper", 255)
            yield from self._wait(35, 0, "Grasping")
            if not self._grip_present():
                raise ValueError("Gripper closed without a supported handle; pickup unconfirmed")
            reading = self.robot.read()
            self.offset_local = reading.rotation.T @ (reading.tcp_m - obs.position_m)
            self.body_rotation_local = reading.rotation.T @ rotation_z(obs.yaw_mod_pi_rad)
            self.carrying = True
            self.evidence.append(
                {
                    "kind": "rigid_grasp_inference",
                    "gap_m": reading.gap_m,
                    "offset_local_m": self.offset_local.tolist(),
                }
            )
            yield from self._motion(reading.tcp_m + [0, 0, 0.20], "Lifting tool", 0)
            yield from self._carry()
        except (ValueError, FloatingPointError) as error:
            self.robot.hold()
            self.outcome = Outcome("failed", str(error))
            self.phase = "Vision task failed"

    def _carry(self):
        point = self._place_point()
        yield from self._motion(point + [0, 0, 0.20], "Moving to target", 0)
        yield from self._motion(self._place_point(), "Placing tool", 0)
        # Release is intentional. A rigid-grasp estimate cannot prove placement.
        self.carrying = False
        yield from self._wait(28, 255, "Releasing")
        yield from self._motion(np.array([*self.target, 0.24]), "Withdrawing gripper", 255)
        yield from self._wait(30, 255, "Awaiting independent placement check")
        self.phase = "Released; placement unverified"
        self.outcome = Outcome(
            "released_unverified", "Released the tool; placement needs checking."
        )

    def pause(self):
        self.robot.hold()
        self.outcome = Outcome("interrupted", "Stopped; retaining the gripper command.")

    def resume(self):
        if not self.carrying or not self._grip_present():
            self.outcome = Outcome(
                "failed", "Resume needs a supported held handle; rescan required."
            )
            return
        self.revision += 1
        self.outcome = None

    def return_to_rack(self):
        if not self.carrying or not self._grip_present() or self.rack_xy is None:
            raise ValueError("Cannot redirect an unconfirmed grasp")
        self.target = self.rack_xy.copy()
        self.revision += 1
        self.outcome = None
        self.frames = self._redirect()
        return self

    def _redirect(self):
        try:
            reading = self.robot.read()
            yield from self._motion(reading.tcp_m + [0, 0, 0.12], "Lifting for return", 0)
            yield from self._carry()
        except (ValueError, FloatingPointError) as error:
            self.robot.hold()
            self.outcome = Outcome("failed", str(error))

    def advance(self):
        if self.outcome is not None:
            return False
        try:
            next(self.frames)
            return True
        except StopIteration:
            return False
