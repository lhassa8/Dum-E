"""Independent clearance and observed/predicted scene provenance checks."""

from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import RobotReading, validate_observation
from physical_ai_lab.assistant.handoff_planning import choose_handoff, footprints, hull, separation


def prediction(position, yaw):
    return {
        "status": "observed",
        "position_m": position,
        "fit_score": 0.99,
        "yaw_mod_pi_rad": yaw,
        "signed_yaw_rad": yaw,
        "surface_normal": [0, 0, 1],
    }


def scene():
    # Measured-pose style inputs reproduce the diagnosed geometric overlap.
    p = {
        "screwdriver": prediction([0.470, -0.236, 0.022], -1.24),
        "wrench": prediction([0.461, 0.238, 0.022], -1.02),
        "hammer": prediction([0.429, 0, 0.022], -1.21),
    }
    r = np.array([[np.cos(-1.02), -np.sin(-1.02), 0], [np.sin(-1.02), np.cos(-1.02), 0], [0, 0, 1]])
    reading = RobotReading(np.zeros(7), np.array([0.46, 0.24, 0.24]), r, 0.044, True, 4.0)
    robot = SimpleNamespace(read=lambda: reading, solve=lambda p, r: np.zeros(7))
    actor = SimpleNamespace(
        robot=robot,
        object="wrench",
        body_rotation_local=np.eye(3),
        orientation=r,
        target=np.array([0.64, -0.16]),
        direction_yaw=-1.02,
        scene_history={n: validate_observation(n, v, 1.0, 1.0) for n, v in p.items()},
    )
    return actor, p


def test_polygon_separation_detects_overlap_and_measured_gap():
    a = hull([[-1, -1], [-1, 1], [1, -1], [1, 1]])
    assert separation(a, a) < 0
    assert separation(a, a + [2.5, 0]) == pytest.approx(0.5)


def test_unknown_heading_covers_both_possible_tool_tips():
    polygons = footprints("screwdriver", np.zeros(3), np.eye(3), uncertain_sign=True)
    vertices = np.vstack(polygons)
    assert vertices[:, 1].min() < -0.12 and vertices[:, 1].max() > 0.12


def test_handoff_turn_uses_scene_poses_without_a_simulator():
    actor, p = scene()
    orientation, evidence = choose_handoff(actor, SimpleNamespace(captured_s=4.0), p)
    assert evidence["mode"] == "tabletop_reorientation"
    assert evidence["clearance_m"] >= 0.006
    np.testing.assert_allclose(orientation.T @ orientation, np.eye(3), atol=1e-12)
    assert all(s["mode"] == "fresh_camera" for s in evidence["neighbor_sources"])
    assert "bench" not in vars(actor)


def test_occluded_neighbor_prediction_is_labeled_and_bounded():
    actor, p = scene()
    p["screwdriver"] = {"status": "missing", "position_m": None, "fit_score": 0}
    _, e = choose_handoff(actor, SimpleNamespace(captured_s=4.0), p)
    source = next(s for s in e["neighbor_sources"] if s["tool"] == "screwdriver")
    assert source["mode"] == "stationary_scene_prediction" and source["age_s"] == 3
    actor.scene_history = {}
    with pytest.raises(ValueError, match="recent observed"):
        choose_handoff(actor, SimpleNamespace(captured_s=4.0), p)
    actor, p = scene()
    with pytest.raises(ValueError, match="stale"):
        choose_handoff(actor, SimpleNamespace(captured_s=1.0), p)
    p["screwdriver"] = {"status": "ambiguous", "position_m": None, "fit_score": 0}
    with pytest.raises(ValueError, match="ambiguous"):
        choose_handoff(actor, SimpleNamespace(captured_s=4.0), p)
    for position in [[float("nan"), 0, 0], [0, 0], [float("inf"), 0, 0]]:
        p["screwdriver"] = {"status": "missing", "position_m": position, "fit_score": 0}
        with pytest.raises(ValueError, match="invalid position"):
            choose_handoff(actor, SimpleNamespace(captured_s=4.0), p)
