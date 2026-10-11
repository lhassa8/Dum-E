"""Small learned carried-position estimator; runtime uses NumPy, not tool truth.

Predicts actual-minus-rigid position in the gripper frame from camera history and
robot telemetry. This is a hidden-state correction, not a next-state world model.
Training labels may use simulation truth; deployed features cannot.
"""

from pathlib import Path

import numpy as np

FEATURE_VERSION = 2


def carry_features(actor, reading):
    if actor.grasp_reading is None or actor.direction_yaw is None:
        raise ValueError("Carry estimator needs a camera direction and grasp history")
    start = actor.grasp_reading
    if reading.joint_velocity is None or reading.actuator_load is None:
        raise ValueError("Carry estimator needs robot velocity and actuator-load telemetry")
    identity = np.array([actor.object == n for n in ("screwdriver", "wrench", "hammer")], float)
    return np.r_[
        identity,
        np.cos(actor.direction_yaw),
        np.sin(actor.direction_yaw),
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
    ].astype(float)


class CarryModel:
    def __init__(self, path):
        with np.load(Path(path), allow_pickle=False) as data:
            self.weights = {name: data[name].copy() for name in data.files}
        if int(self.weights["feature_version"]) != FEATURE_VERSION:
            raise ValueError("Unsupported carry feature version")

    def predict(self, features):
        w = self.weights
        features = np.asarray(features, dtype=float)
        if features.shape != w["mean"].shape or not np.isfinite(features).all():
            raise ValueError("Invalid carry estimator input")
        x = (features - w["mean"]) / w["scale"]
        if np.max(np.abs(x)) > 8:
            raise ValueError("Carry observation is outside the experimental training range")
        for i in range(3):
            x = x @ w[f"weight_{i}"].T + w[f"bias_{i}"]
            if i < 2:
                x = np.maximum(x, 0)
        correction = x / 1000  # Training targets are millimeters.
        if not np.isfinite(correction).all() or np.linalg.norm(correction) > 0.04:
            raise ValueError("Carry prediction exceeds the experimental correction bound")
        return correction
