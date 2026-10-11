"""Numerical units, refusal and telemetry boundaries for the learned estimator."""

from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import RobotReading
from physical_ai_lab.assistant.carry_model import FEATURE_VERSION, CarryModel, carry_features


def checkpoint(path, version=FEATURE_VERSION):
    # Independently specified three-layer arithmetic: input feature0=1 gives
    # 2 then6, then output millimeters [6,-3,12]. No tool/simulator data.
    first = np.zeros((64, 54))
    first[0, 0] = 2
    second = np.zeros((64, 64))
    second[0, 0] = 3
    third = np.zeros((3, 64))
    third[:, 0] = [1, -0.5, 2]
    np.savez(
        path,
        mean=np.zeros(54),
        scale=np.ones(54),
        feature_version=version,
        weight_0=first,
        bias_0=np.zeros(64),
        weight_1=second,
        bias_1=np.zeros(64),
        weight_2=third,
        bias_2=np.zeros(3),
    )


def test_checkpoint_preserves_translation_units_and_numerical_refusals(tmp_path):
    path = tmp_path / "model.npz"
    checkpoint(path)
    model = CarryModel(path)
    features = np.zeros(54)
    features[0] = 1
    np.testing.assert_allclose(model.predict(features), [0.006, -0.003, 0.012])
    for invalid in [np.zeros(53), np.full(54, np.nan), np.full(54, 9)]:
        with pytest.raises(ValueError):
            model.predict(invalid)
    features[0] = 4  # Correctly shaped/in-range input, excessive output correction.
    with pytest.raises(ValueError, match="correction bound"):
        model.predict(features)


def test_checkpoint_feature_version_cannot_silently_change(tmp_path):
    path = tmp_path / "model.npz"
    checkpoint(path, version=999)
    with pytest.raises(ValueError, match="feature version"):
        CarryModel(path)


def test_features_use_camera_history_and_robot_telemetry_only():
    reading = RobotReading(
        np.zeros(7), np.array([0.45, 0.1, 0.2]), np.eye(3), 0.044, True, 2, np.zeros(7), np.zeros(8)
    )
    actor = SimpleNamespace(
        grasp_reading=reading,
        direction_yaw=np.pi / 2,
        object="hammer",
        offset_local=np.array([0, 0, 0.004]),
    )
    features = carry_features(actor, reading)
    assert features.shape == (54,)
    np.testing.assert_array_equal(features[:3], [0, 0, 1])
    np.testing.assert_allclose(features[3:5], [0, 1], atol=1e-12)
    actor.direction_yaw = None
    with pytest.raises(ValueError, match="camera direction"):
        carry_features(actor, reading)
