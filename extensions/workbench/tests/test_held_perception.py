"""Independent optical geometry specification; never simulation object state."""

import numpy as np
import pytest

from physical_ai_lab.assistant.held_perception import locate_held_face
from physical_ai_lab.assistant.perception import CameraCalibration, RGBDFrame, locate_held_tool


def face(name, partial=False):
    camera = CameraCalibration(640, 480, 40, np.array([0.45, 0, 0.85]), np.eye(3))
    v, u = np.indices((480, 640))
    plane = camera.unproject(u, v, np.full((480, 640), 0.85 - 0.242))
    mask = (np.abs(plane[..., 0] - 0.45) < 0.022) & (np.abs(plane[..., 1]) < 0.028)
    if partial:
        mask &= plane[..., 0] > 0.45
    rgb = np.zeros((480, 640, 3), dtype=np.uint8)
    rgb[mask] = {"wrench": [80, 80, 80], "screwdriver": [180, 115, 5], "hammer": [130, 95, 45]}[
        name
    ]
    depth = np.full((480, 640), np.nan)
    depth[mask] = 0.608
    return RGBDFrame(rgb, depth, camera)


@pytest.mark.parametrize("name", ["screwdriver", "wrench", "hammer"])
def test_complete_airborne_face_has_independently_known_position(name):
    frame = face(name)
    for fit in [locate_held_tool, locate_held_face]:
        result = fit(frame, name, [0.45, 0, 0.22])
        assert result["status"] == "observed"
        np.testing.assert_allclose(result["position_m"], [0.45, 0, 0.22], atol=0.0015)
        assert result["fit_score"] >= 0.8


def test_clipped_face_missing_depth_and_invalid_robot_prior_are_withheld():
    for fit in [locate_held_tool, locate_held_face]:
        assert fit(face("wrench", partial=True), "wrench", [0.45, 0, 0.22])["status"] == "missing"
        assert fit(face("wrench"), "wrench", [0.75, 0, 0.22])["status"] == "missing"
        with pytest.raises(ValueError, match="TCP"):
            fit(face("wrench"), "wrench", [float("nan"), 0, 0.22])
