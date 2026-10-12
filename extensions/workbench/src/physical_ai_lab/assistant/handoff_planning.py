"""Choose a supported tabletop orientation from measured neighboring tool poses.

Planar catalog footprints are a conservative geometric proxy, not a guarantee
against slip or collision along a joint path. Physics/visual outcome judges remain
separate. No simulator objects, rack coordinates or true held poses enter here.
"""

import itertools

import numpy as np

from physical_ai_lab.assistant.camera_control import (
    observed_rotation,
    rotation_z,
    validate_observation,
)
from physical_ai_lab.assistant.tool_geometry import parts


class BlockedWorkbenchView(ValueError):
    """A known neighbor is visually missing; a bounded observation move may help."""


def hull(points):
    points = sorted(set(map(tuple, points)))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return np.array(lower[:-1] + upper[:-1])


def footprints(name, center, rotation, uncertain_sign=False):
    boxes, capsules = parts(name)
    result = []
    for sign in [1, -1] if uncertain_sign else [1]:
        r = rotation @ np.diag([sign, sign, 1])
        for local, size in boxes:
            vertices = np.array(list(itertools.product([-1, 1], repeat=3))) * size + local
            result.append(hull((vertices @ r.T)[:, :2] + center[:2]))
        angles = np.arange(16) * 2 * np.pi / 16
        for local, half, radius in capsules:
            ends = np.array(local) + np.array([[0, -half, 0], [0, half, 0]])
            ends = (ends @ r.T)[:, :2] + center[:2]
            circle = np.c_[np.cos(angles), np.sin(angles)] * (radius + 0.0005)
            result.append(hull((ends[:, None, :] + circle).reshape(-1, 2)))
    return result


def separation(a, b):
    axes = []
    for polygon in [a, b]:
        edges = np.roll(polygon, -1, axis=0) - polygon
        normals = np.c_[-edges[:, 1], edges[:, 0]]
        axes.extend(normals / np.linalg.norm(normals, axis=1)[:, None])
    axes = np.asarray(axes)
    pa, pb = a @ axes.T, b @ axes.T
    return float(np.max(np.maximum(pb.min(0) - pa.max(0), pa.min(0) - pb.max(0))))


def scene_clearance(target_parts, neighbors):
    return min(separation(a, b) for a in target_parts for other in neighbors for b in other)


def choose_handoff(actor, sample, predictions):
    reading = actor.robot.read()
    if not np.isfinite([sample.captured_s, reading.time_s]).all() or not (
        0 <= reading.time_s - sample.captured_s <= 0.25
    ):
        raise ValueError("Workbench camera frame is stale; no scene plan updated")
    neighbors = []
    sources = []
    uncertainty = 0.0005
    for name in ["screwdriver", "wrench", "hammer"]:
        if name == actor.object:
            continue
        prediction = predictions[name]
        if prediction.get("status") == "ambiguous":
            raise ValueError(f"Neighboring {name} is ambiguous; no placement planned")
        if prediction.get("status") == "missing" or (
            prediction.get("status") == "observed" and prediction.get("fit_score", 0) < 0.8
        ):
            observation = actor.scene_history.get(name)
            age = np.inf if observation is None else reading.time_s - observation.captured_s
            if observation is None or not np.isfinite(age) or age < 0 or age > 30:
                raise BlockedWorkbenchView(
                    f"No recent observed state for neighboring {name}; holding"
                )
            if prediction.get("position_m") is not None:
                current_position = np.asarray(prediction["position_m"], dtype=float)
                if current_position.shape != (3,) or not np.isfinite(current_position).all():
                    raise ValueError(f"Neighboring {name} has invalid position; holding")
                if np.linalg.norm(current_position - observation.position_m) > 0.005:
                    raise ValueError(f"Neighboring {name} changed; scene prediction invalidated")
            uncertainty = max(uncertainty, 0.0005 + 0.0002 * age)
            sources.append(
                {
                    "tool": name,
                    "mode": "stationary_scene_prediction",
                    "source_capture_s": observation.captured_s,
                    "age_s": age,
                }
            )
        else:
            observation = validate_observation(name, prediction, sample.captured_s, reading.time_s)
            sources.append(
                {"tool": name, "mode": "fresh_camera", "age_s": reading.time_s - sample.captured_s}
            )
        rotation = observed_rotation(observation)
        if (
            observation.signed_yaw_rad is not None
            and np.cos(observation.signed_yaw_rad - observation.yaw_mod_pi_rad) < 0
        ):
            rotation = rotation @ np.diag([-1, -1, 1])
        neighbors.append(
            footprints(name, observation.position_m, rotation, observation.signed_yaw_rad is None)
        )
    current = reading.rotation @ actor.body_rotation_local
    actor.planned_neighbors = neighbors
    actor.scene_prediction_uncertainty = uncertainty
    options = [("inherited", current, actor.orientation)]
    for yaw in [0.0, np.pi / 2, -np.pi / 2, np.pi]:
        desired = rotation_z(yaw)
        options.append(("tabletop_reorientation", desired, desired @ actor.body_rotation_local.T))
    candidates = []
    for kind, body, tcp in options:
        clearance = scene_clearance(
            footprints(actor.object, np.r_[actor.target, 0.022], body, actor.direction_yaw is None),
            neighbors,
        )
        if clearance < 0.006 + 2 * uncertainty:
            continue
        try:
            actor.robot.solve(np.r_[actor.target, 0.24], tcp)
        except ValueError:
            continue
        change = float(np.arccos(np.clip((np.trace(reading.rotation.T @ tcp) - 1) / 2, -1, 1)))
        candidates.append((change, kind, body, tcp, clearance))
    if not candidates:
        raise ValueError("No observed clear handoff orientation; holding for replanning")
    change, kind, body, tcp, clearance = min(candidates, key=lambda x: x[0])
    return tcp, {
        "kind": "camera_handoff_clearance_plan",
        "mode": kind,
        "clearance_m": clearance,
        "orientation_change_rad": change,
        "captured_s": sample.captured_s,
        "provenance": "Fresh neighboring camera poses + declared catalog; held rotation inferred",
        "scene_assumption": "Neighbors remain stationary during high carry; "
        "planned geometry, not continuous measurement",
        "neighbor_sources": sources,
        "scene_prediction_uncertainty_m": uncertainty,
    }
