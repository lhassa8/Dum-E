"""Independent action units, uncertainty refusals and unprivileged feature checks."""

from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import RobotReading, ToolObservation
from physical_ai_lab.assistant.release_model import (
    FEATURE_COUNT,
    FEATURE_VERSION,
    ReleaseModel,
    release_features,
)


def checkpoint(path, disagreements=False):
    actions = np.array([[x, y] for x in [-0.02, 0, 0.02] for y in [-0.02, 0, 0.02]])
    # Independent final-outcome specification: +15mm/-7mm bias plus requested
    # XY offset; rest at22mm, zero speed and added neighbor movement.
    bias = np.array([15.0, -7.0, 22.0, 0.0, 0.0])
    w = {
        "mean": np.zeros(FEATURE_COUNT),
        "scale": np.ones(FEATURE_COUNT),
        "feature_version": np.array(FEATURE_VERSION),
        "max_feature": np.array(8.0),
        "max_xy_std_m": np.array(0.008),
        "actions_xy_m": actions,
        "constant": np.tile(bias, (3, 1)),
        "linear": np.vstack([np.zeros((FEATURE_COUNT, 5)), bias]),
    }
    for member in range(3):
        for layer, (rows, columns) in enumerate([(4, FEATURE_COUNT), (4, 4), (5, 4)]):
            w[f"weight_{member}_{layer}"] = np.zeros((rows, columns))
            w[f"bias_{member}_{layer}"] = bias.copy() if layer == 2 else np.zeros(rows)
        if disagreements:
            w[f"bias_{member}_2"][0] += [0, 20, -20][member]
    np.savez(path, **w)


def actor():
    reading = RobotReading(
        np.zeros(7),
        np.array([0.64, -0.16, 0.24]),
        np.eye(3),
        0.044,
        True,
        2.0,
        np.zeros(7),
        np.zeros(8),
    )
    # This narrow object has no simulator, true object state, or geometry API.
    return SimpleNamespace(
        robot=SimpleNamespace(read=lambda: reading, solve=lambda p, r: np.zeros(7)),
        orientation=np.eye(3),
        evidence=[],
        grasp_reading=reading,
        observation=ToolObservation("hammer", np.array([0.43, 0, 0.022]), 0.5, 0.9, 0.0),
        offset_local=np.array([0, 0, 0.004]),
        direction_yaw=None,
        initial_scene_estimates={
            "hammer": {"status": "observed", "fit_score": 0.9, "position_m": [0.43, 0, 0.022]}
        },
        target=np.array([0.64, -0.16]),
        object="hammer",
    )


def test_future_prediction_preserves_action_translation_and_units(tmp_path):
    path = tmp_path / "model.npz"
    checkpoint(path)
    f = np.zeros((2, FEATURE_COUNT))
    f[:, 2] = 1
    f[1, -2:] = [-0.02, 0.02]
    expected = [[0.015, -0.007, 0.022, 0, 0], [-0.005, 0.013, 0.022, 0, 0]]
    for kind in ["constant", "linear", "ensemble"]:
        p, std, valid = ReleaseModel(path, kind).predict(f)
        np.testing.assert_allclose(p, expected)
        assert valid.all()
        np.testing.assert_allclose(std, 0, atol=1e-15)


def test_planner_chooses_from_predicted_future_without_simulation_truth(tmp_path):
    path = tmp_path / "model.npz"
    checkpoint(path)
    a = actor()
    point = np.array([0.64, -0.16, 0.04])
    chosen, evidence = ReleaseModel(path).choose(a, point)
    np.testing.assert_allclose(chosen, [0.62, -0.16, 0.04])
    assert evidence["action_xy_m"] == [-0.02, 0.0]
    np.testing.assert_allclose(evidence["predicted_future"][:2], [-0.005, -0.007])
    features = release_features(a, point, [0, 0])
    assert features.shape == (FEATURE_COUNT,)
    assert features[5] == 0  # Unknown heading explicitly encoded, never invented.
    assert features[-6] == 1  # Historical observed hammer flag.
    assert "bench" not in vars(a) and "actual_position" not in vars(a)


def test_disagreement_invalid_input_and_unsafe_future_cannot_select_motion(tmp_path):
    path = tmp_path / "model.npz"
    checkpoint(path, disagreements=True)
    model = ReleaseModel(path)
    f = np.zeros((2, FEATURE_COUNT))
    f[:, 2] = 1
    p, std, valid = model.predict(f)
    assert not valid.any() and np.all(std[:, 0] > 0.008)
    with pytest.raises(ValueError, match="supported predicted"):
        model.choose(actor(), [0.64, -0.16, 0.04])
    checkpoint(path)
    model = ReleaseModel(path)
    f[0, 0] = np.nan
    f[1, 0] = 9
    assert not model.predict(f)[2].any()
    with pytest.raises(ValueError, match="batch shape"):
        model.predict(np.zeros(FEATURE_COUNT))
    a = actor()
    a.robot.read = lambda: RobotReading(np.zeros(7), np.zeros(3), np.eye(3), 0.044, True, 2.0)
    with pytest.raises(ValueError, match="telemetry"):
        release_features(a, [0.64, -0.16, 0.04], [0, 0])


def test_unreachable_best_prediction_cannot_be_selected(tmp_path):
    path = tmp_path / "model.npz"
    checkpoint(path)
    a = actor()

    def solve(point, orientation):
        if np.allclose(point, [0.62, -0.16, 0.04]):
            raise ValueError("Unreachable robot pose")
        return np.zeros(7)

    a.robot.solve = solve
    point, evidence = ReleaseModel(path).choose(a, [0.64, -0.16, 0.04])
    np.testing.assert_allclose(point, [0.62, -0.14, 0.04])
    assert not evidence["candidate_reachable"][1]
    assert not evidence["candidate_valid"][1]
