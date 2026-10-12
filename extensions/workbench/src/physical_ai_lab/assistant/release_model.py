"""Action-conditioned future placement model; pixels/proprioception inputs only.

Outputs future XY residual, resting height, speed and added neighbor disturbance.
Provisional guards are not calibrated safety or success guarantees. Actor outcomes
still require a separate physical or optical judge. No checkpoint is auto-loaded.
"""

from pathlib import Path
from time import perf_counter

import numpy as np

FEATURE_VERSION = 1
FEATURE_COUNT = 76
TOOLS = ("screwdriver", "wrench", "hammer")


class ReleaseRefusal(ValueError):
    """Model cannot support an action; separate from malformed feature/program errors."""

    def __init__(self, message, reason="unsupported_input"):
        super().__init__(message)
        self.reason = reason


def release_features(actor, point, action_xy):
    reading, start = actor.robot.read(), actor.grasp_reading
    if start is None or actor.observation is None or actor.offset_local is None:
        raise ValueError("Release model needs camera/grasp history")
    if reading.joint_velocity is None or reading.actuator_load is None:
        raise ValueError("Release model needs robot velocity/load telemetry")
    known = actor.direction_yaw is not None
    heading = [np.cos(actor.direction_yaw), np.sin(actor.direction_yaw)] if known else [0, 0]
    scene = []
    for name in TOOLS:
        estimate = (actor.initial_scene_estimates or {}).get(name, {})
        observed = estimate.get("status") == "observed" and estimate.get("fit_score", 0) >= 0.8
        position = np.asarray(estimate.get("position_m"), float)
        observed = observed and position.shape == (3,) and np.isfinite(position).all()
        scene.extend([float(observed), *(position if observed else np.zeros(3))])
    action_xy, point = np.asarray(action_xy, float), np.asarray(point, float)
    if action_xy.shape != (2,) or point.shape != (3,) or not np.isfinite(point).all():
        raise ValueError("Invalid release action/point")
    features = np.r_[
        [actor.object == name for name in TOOLS],
        heading,
        float(known),
        np.cos(2 * actor.observation.yaw_mod_pi_rad),
        np.sin(2 * actor.observation.yaw_mod_pi_rad),
        actor.offset_local,
        start.joints,
        start.tcp_m,
        reading.joints,
        reading.tcp_m,
        reading.rotation.ravel(),
        reading.gap_m,
        min(reading.time_s - start.time_s, 40.0),
        reading.joint_velocity,
        reading.actuator_load,
        actor.target,
        point,
        scene,
        action_xy,
    ].astype(float)
    if features.shape != (FEATURE_COUNT,) or not np.isfinite(features).all():
        raise ValueError("Invalid release feature contract")
    return features


class ReleaseModel:
    def __init__(self, path, kind="ensemble"):
        with np.load(Path(path), allow_pickle=False) as data:
            self.weights = {name: data[name].copy() for name in data.files}
        w = self.weights
        if int(w["feature_version"]) != FEATURE_VERSION or w["mean"].shape != (FEATURE_COUNT,):
            raise ValueError("Unsupported release feature version")
        if kind not in {"ensemble", "linear", "constant"}:
            raise ValueError("Unknown release predictor")
        actions = w["actions_xy_m"]
        if (
            actions.shape != (9, 2)
            or not np.isfinite(actions).all()
            or np.max(np.abs(actions)) > 0.02
            or len(np.unique(actions, axis=0)) != 9
            or not np.any(np.linalg.norm(actions, axis=1) == 0)
        ):
            raise ValueError("Release actions violate the experimental 20mm bound")
        self.kind = kind
        self.recipe_version = int(w.get("controller_recipe_version", np.array(0)))
        if self.recipe_version not in {0, 1}:
            raise ValueError("Unsupported release controller recipe")
        self.supports_reoriented = self.recipe_version == 1

    def predict(self, features):
        w = self.weights
        features = np.asarray(features, float)
        if features.ndim != 2 or features.shape[1] != FEATURE_COUNT:
            raise ValueError("Invalid release batch shape")
        x = (features - w["mean"]) / w["scale"]
        valid = np.isfinite(x).all(1) & (np.max(np.abs(x), axis=1) <= w["max_feature"])
        if self.kind == "ensemble":
            predictions = []
            for member in range(3):
                z = x
                for layer in range(3):
                    z = np.einsum("bi,oi->bo", z, w[f"weight_{member}_{layer}"])
                    z += w[f"bias_{member}_{layer}"]
                    if layer < 2:
                        z = np.maximum(z, 0)
                predictions.append(z / 1000)
            predictions = np.array(predictions)
            output, std = predictions.mean(0), predictions.std(0)
        elif self.kind == "linear":
            output = np.c_[x, np.ones(len(x))] @ w["linear"] / 1000
            std = np.zeros_like(output)  # No uncertainty estimate for this baseline.
        else:
            output = features[:, :3] @ w["constant"] / 1000
            std = np.zeros_like(output)  # No uncertainty estimate for this baseline.
        output[:, :2] += features[:, -2:]  # Explicit proposed-action translation baseline.
        output[:, 2:] = np.maximum(output[:, 2:], 0)
        valid &= np.isfinite(output).all(1)
        if self.kind == "ensemble":
            valid &= np.linalg.norm(std[:, :2], axis=1) <= w["max_xy_std_m"]
        return output, std, valid

    def choose(self, actor, point):
        if self.recipe_version == 1 and not getattr(actor, "safe_handoff", False):
            raise ReleaseRefusal(
                "This release model requires the verified camera-recovery recipe", "changed_recipe"
            )
        began = perf_counter()
        actions = self.weights["actions_xy_m"]
        features = np.array([release_features(actor, point, a) for a in actions])
        prediction, std, valid = self.predict(features)
        input_supported = valid.copy()
        valid &= (
            (np.linalg.norm(prediction[:, :2], axis=1) < 0.035)
            & (prediction[:, 2] >= 0.01)
            & (prediction[:, 2] < 0.04)
            & (prediction[:, 3] < 0.03)
            & (prediction[:, 4] < 0.004)
        )
        geometry_supported = np.ones(len(actions), dtype=bool)
        if hasattr(actor, "placement_clearance"):
            geometry_supported = np.array(
                [actor.placement_clearance(p[:2]) >= 0.006 for p in prediction]
            )
        valid &= geometry_supported
        predicted_supported = valid.copy()
        # A good predicted result cannot make an unreachable robot action valid.
        reachable = np.zeros(len(actions), dtype=bool)
        for i in np.flatnonzero(valid):
            proposed = np.asarray(point, float).copy()
            proposed[:2] += actions[i]
            try:
                actor.robot.solve(proposed, actor.orientation)
                reachable[i] = True
            except ValueError:
                pass
        valid &= reachable
        if not valid.any():
            actor.evidence.append(
                {
                    "kind": "future_release_refusal",
                    "candidate_predictions": prediction.tolist(),
                    "input_supported": input_supported.tolist(),
                    "reachable": reachable.tolist(),
                    "max_normalized_features": np.max(
                        np.abs((features - self.weights["mean"]) / self.weights["scale"]), axis=1
                    ).tolist(),
                    "latency_ms": (perf_counter() - began) * 1000,
                }
            )
            reason = (
                "unsupported_input"
                if not input_supported.any()
                else ("unreachable_future" if predicted_supported.any() else "unsafe_future")
            )
            raise ReleaseRefusal(
                "No release action has a supported predicted outcome; holding", reason
            )
        costs = np.linalg.norm(prediction[:, :2], axis=1)
        index = int(np.argmin(np.where(valid, costs, np.inf)))
        chosen = np.asarray(point, float).copy()
        chosen[:2] += actions[index]
        evidence = {
            "kind": "future_release_prediction",
            "predictor": self.kind,
            "action_xy_m": actions[index].tolist(),
            "predicted_future": prediction[index].tolist(),
            "ensemble_std": std[index].tolist() if self.kind == "ensemble" else None,
            "candidate_predictions": prediction.tolist(),
            "candidate_valid": valid.tolist(),
            "candidate_reachable": reachable.tolist(),
            "latency_ms": (perf_counter() - began) * 1000,
            "provenance": "Camera history + robot telemetry + proposed descent offsets; unverified",
        }
        return chosen, evidence
