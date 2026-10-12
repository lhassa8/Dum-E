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
from physical_ai_lab.assistant.tool_geometry import parts


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
    joint_velocity: np.ndarray | None = None
    actuator_load: np.ndarray | None = None


@dataclass(frozen=True)
class ToolObservation:
    name: str
    position_m: np.ndarray
    yaw_mod_pi_rad: float
    fit_score: float
    captured_s: float
    signed_yaw_rad: float | None = None
    surface_normal: np.ndarray | None = None


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
    signed = prediction.get("signed_yaw_rad")
    if signed is not None and not np.isfinite(signed):
        raise ValueError("Camera direction is invalid")
    normal = np.asarray(prediction.get("surface_normal", [0, 0, 1]), float)
    if (
        normal.shape != (3,)
        or not np.isfinite(normal).all()
        or normal[2] < 0.95
        or abs(np.linalg.norm(normal) - 1) > 0.01
    ):
        raise ValueError("Camera face normal is unsupported")
    return ToolObservation(
        name,
        xyz.copy(),
        yaw,
        float(prediction["fit_score"]),
        captured_s,
        signed,
        normal / np.linalg.norm(normal),
    )


def observed_rotation(observation):
    normal = observation.surface_normal
    if normal is None:
        return rotation_z(observation.yaw_mod_pi_rad)
    yaw = observation.yaw_mod_pi_rad
    y = np.array([-np.sin(yaw), np.cos(yaw), 0.0])
    y -= normal * (y @ normal)
    y /= np.linalg.norm(y)
    return np.stack([np.cross(y, normal), y, normal], axis=1)


def support_clearance(name, rotation):
    """Known tool catalog, not simulator geometry or measured object rotation.

    Conservative over the unknown 180-degree handle sign. Covers the current
    primitive boxes and capsules only; cannot establish real-tool clearance.
    """
    boxes, capsules = parts(name)
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

    def __init__(
        self,
        robot,
        camera,
        tool,
        destination_xy,
        rack_xy=None,
        carry_model=None,
        carry_policy="xy_descent",
        release_model=None,
        verify_motion=False,
        release_fallback=False,
        linear_lifts=False,
        center_grasp=False,
        safe_handoff=False,
    ):
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
        self.carry_model = carry_model
        if carry_policy not in {"full_xyz", "xy_descent"}:
            raise ValueError("Unknown experimental carry policy")
        self.carry_policy = carry_policy
        self.grasp_reading = None
        self.direction_yaw = None
        self.initial_scene_estimates = None
        self.release_model = release_model
        self.verify_motion = verify_motion
        self.release_fallback = release_fallback
        if release_fallback and not verify_motion:
            raise ValueError("Conventional release recovery requires verified robot motion")
        self.last_motion_check = None
        self.linear_lifts = linear_lifts
        self.center_grasp = center_grasp
        self.safe_handoff = safe_handoff
        self.reoriented_carry = False
        self.planned_neighbors = None
        self.scene_history = {}
        self.frames = self._run()

    def _observe(self):
        start = perf_counter()
        sample = self.camera.capture_timed()
        captured_s = sample.captured_s
        predictions = locate_tools(sample.frame)
        now_s = self.robot.read().time_s
        for name, observed in predictions.items():
            try:
                cached = validate_observation(name, observed, captured_s, now_s)
            except ValueError:
                continue
            self.scene_history[name] = cached
        prediction = predictions[self.object]
        if self.initial_scene_estimates is None:
            self.initial_scene_estimates = predictions
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
                reading = self.robot.read()
                start = reading.joints
                ticks = max(40, int(np.max(np.abs(end - start)) / 0.025))
                path = None
                if self.linear_lifts and phase in {"Lifting tool", "Lifting for return"}:
                    path = self.robot.cartesian_path(
                        reading.tcp_m, np.asarray(point), self.orientation, ticks
                    )
                    end = path[-1]
                    self.evidence.append(
                        {"kind": "cartesian_lift_plan", "phase": phase, "waypoints": ticks}
                    )
                index, revision = 0, self.revision
                remaining = ticks + 12
            index += 1
            a = min(index / ticks, 1.0)
            a = a * a * (3 - 2 * a)
            command = start + (end - start) * a if path is None else path[min(index, ticks) - 1]
            self.robot.tick(command, grip)
            if self.carrying and not self._grip_present():
                raise ValueError("Gripper no longer indicates a held handle; holding position")
            remaining -= 1
            yield
        if self.verify_motion:
            if self.center_grasp and phase == "Lowering gripper":
                command = end.copy()
                for correction in range(25):
                    reading = self.robot.read()
                    position_error = float(np.linalg.norm(reading.tcp_m - point))
                    angle_error = float(
                        np.arccos(
                            np.clip(
                                (np.trace(reading.rotation.T @ self.orientation) - 1) / 2, -1, 1
                            )
                        )
                    )
                    if position_error < 0.002 and angle_error < 0.012:
                        break
                    if correction % 4 == 0:
                        command = self.robot.correct_joint_command(command, end)
                    self.robot.tick(command, grip)
                    yield
                self.evidence.append(
                    {
                        "kind": "measured_grasp_centering",
                        "tcp_error_m": position_error,
                        "orientation_error_rad": angle_error,
                        "frames": correction,
                    }
                )
                if position_error >= 0.002 or angle_error >= 0.012:
                    raise ValueError("Gripper could not center on the observed handle; holding")
            for extra in range(61):
                reading = self.robot.read()
                position_error = float(np.linalg.norm(reading.tcp_m - point))
                angle_error = float(
                    np.arccos(
                        np.clip((np.trace(reading.rotation.T @ self.orientation) - 1) / 2, -1, 1)
                    )
                )
                passed = (
                    np.isfinite([position_error, angle_error]).all()
                    and position_error < 0.015
                    and angle_error < 0.035
                )
                if passed or extra == 60:
                    break
                self.robot.tick(end, grip)
                if self.carrying and not self._grip_present():
                    raise ValueError("Grip is unconfirmed while settling robot motion")
                yield
            self.last_motion_check = {
                "kind": "robot_motion_check",
                "phase": phase,
                "target_m": np.asarray(point).tolist(),
                "tcp_error_m": position_error,
                "orientation_error_rad": angle_error,
                "extra_frames": extra,
                "passed": bool(passed),
            }
            self.evidence.append(self.last_motion_check)
            if not passed:
                raise ValueError("Robot did not reach the commanded pose; holding for recovery")

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

    def _place_point(self, apply_correction=True):
        reading = self.robot.read()
        _, rotation = self._estimate()
        clearance = max(0.026, support_clearance(self.object, rotation))
        point = np.array([*self.target, clearance + 0.012])
        correction = np.zeros(3)
        if self.carry_model is not None and apply_correction:
            from physical_ai_lab.assistant.carry_model import carry_features

            start = perf_counter()
            correction = reading.rotation @ self.carry_model.predict(carry_features(self, reading))
            if self.carry_policy == "xy_descent":
                correction[2] = 0  # Free-space labels do not establish contact/tilt clearance.
            self.evidence.append(
                {
                    "kind": "learned_carry_inference",
                    "policy": self.carry_policy,
                    "correction_world_m": correction.tolist(),
                    "latency_ms": (perf_counter() - start) * 1000,
                }
            )
        return point + reading.rotation @ self.offset_local - correction

    def _run(self):
        try:
            if self.safe_handoff:
                reading = self.robot.read()
                if reading.closing_command or reading.gap_m < 0.075:
                    raise ValueError(
                        "Fresh pickup needs a confirmed open hand; recover the current grasp first"
                    )
                self.orientation = self.robot.ready_rotation.copy()
                point = self.robot.observation_point()
                angle = np.arccos(
                    np.clip((np.trace(reading.rotation.T @ self.orientation) - 1) / 2, -1, 1)
                )
                if np.linalg.norm(reading.tcp_m - point) > 0.015 or angle > 0.035:
                    yield from self._motion(point, "Surveying workbench with an empty hand", 255)
            obs = self._observe()
            self.direction_yaw = obs.signed_yaw_rad
            if self.carry_model is not None and self.direction_yaw is None:
                raise ValueError("Tool direction is uncertain; learned carry correction withheld")
            self.orientation = observed_rotation(obs) @ self.robot.ready_rotation
            if self.rack_xy is None:
                self.rack_xy = obs.position_m[:2].copy()
            yield from self._motion(obs.position_m + [0, 0, 0.20], "Approaching tool", 255)
            self.phase = "Reobserving before grasp"
            obs = self._observe()
            if obs.signed_yaw_rad is not None:
                self.direction_yaw = obs.signed_yaw_rad
            yield from self._motion(obs.position_m + [0, 0, 0.002], "Lowering gripper", 255)
            yield from self._wait(35, 0, "Grasping")
            if not self._grip_present():
                raise ValueError("Gripper closed without a supported handle; pickup unconfirmed")
            reading = self.robot.read()
            self.grasp_reading = reading
            self.offset_local = reading.rotation.T @ (reading.tcp_m - obs.position_m)
            self.body_rotation_local = reading.rotation.T @ observed_rotation(obs)
            if (
                self.direction_yaw is not None
                and np.cos(self.direction_yaw - obs.yaw_mod_pi_rad) < 0
            ):
                self.body_rotation_local = self.body_rotation_local @ np.diag([-1, -1, 1])
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
        if self.safe_handoff:
            from physical_ai_lab.assistant.handoff_planning import choose_handoff

            self.phase = "Checking clear space for release"
            sample = self.camera.capture_timed()
            predictions = locate_tools(sample.frame)
            self.orientation, plan = choose_handoff(self, sample, predictions)
            self.reoriented_carry = plan["mode"] == "tabletop_reorientation"
            self.evidence.append(plan)
        point = self._place_point(apply_correction=self.carry_policy == "full_xyz")
        if self.reoriented_carry:
            body = self.orientation @ self.body_rotation_local
            point = (
                np.r_[self.target, max(0.026, support_clearance(self.object, body)) + 0.012]
                + self.orientation @ self.offset_local
            )
        yield from self._motion(point + [0, 0, 0.20], "Moving to target", 0)
        # Explicit observation/action boundary for offline counterfactual data.
        # No robot tick, object-state query or extra settling here.
        self.phase = "Choosing release action"
        yield
        point = self._place_point()
        if self.release_model is not None:
            from physical_ai_lab.assistant.release_model import ReleaseRefusal

            try:
                if self.reoriented_carry and not getattr(
                    self.release_model, "supports_reoriented", False
                ):
                    raise ReleaseRefusal(
                        "Release model was not trained on deliberate carry reorientation",
                        "changed_recipe",
                    )
                point, decision = self.release_model.choose(self, point)
                self.evidence.append(decision)
            except ReleaseRefusal as error:
                if (
                    not self.release_fallback
                    or not self._grip_present()
                    or self.last_motion_check is None
                    or not self.last_motion_check["passed"]
                    or error.reason not in {"unsupported_input", "changed_recipe"}
                    or self.placement_clearance([0, 0]) < 0.006
                ):
                    raise
                # Model stays refused. This is the conventional camera/catalog
                # plan, with tracked robot pose and independently judged outcome.
                self.robot.solve(point, self.orientation)
                self.evidence.append(
                    {
                        "kind": "model_refused_conventional_release",
                        "target_m": point.tolist(),
                        "provenance": "Camera/catalog plan; tracked robot; no learned confidence",
                        "model_refusal_reason": error.reason,
                    }
                )
        yield from self.finish_release(point)

    def placement_clearance(self, predicted_xy):
        if self.planned_neighbors is None:
            return np.inf
        from physical_ai_lab.assistant.handoff_planning import footprints, scene_clearance

        _, rotation = self._estimate()
        center = np.r_[self.target + predicted_xy, 0.022]
        return scene_clearance(
            footprints(self.object, center, rotation, self.direction_yaw is None),
            self.planned_neighbors,
        ) - 2 * getattr(self, "scene_prediction_uncertainty", 0.0005)

    def finish_release(self, point):
        """Execute a specified robot descent, opening and withdrawal with physics."""
        yield from self._motion(point, "Placing tool", 0)
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
        # A changed destination also invalidates its queued wrist orientation.
        # Preserve the measured held pose during the initial recovery lift.
        self.orientation = self.robot.read().rotation.copy()
        self.reoriented_carry = False
        self.planned_neighbors = None
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
