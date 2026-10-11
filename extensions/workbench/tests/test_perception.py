"""Independent optical, calibration and ambiguous-observation checks."""

import copy
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from physical_ai_lab.assistant.perception import CameraCalibration, RGBDFrame, locate_tools
from physical_ai_lab.assistant.perception_scene import CameraDatasetScene, camera_scene_xml


def case(occluded=None):
    return {
        "seed": 64983,
        "light": 0.93,
        "occluded": occluded,
        "layout": {
            "screwdriver": [0.40, 0.24, 0.77],
            "wrench": [0.47, -0.23, -1.16],
            "hammer": [0.45, 0, 2.52],
        },
    }


def test_calibration_uses_optical_axis_depth_and_pixel_centers():
    camera = CameraCalibration(640, 480, 90, np.array([1.0, 2.0, 3.0]), np.eye(3))
    center = camera.unproject(319.5, 239.5, 2.0)
    np.testing.assert_allclose(center, [1.0, 2.0, 1.0])
    np.testing.assert_allclose(camera.unproject(559.5, 239.5, 2.0), [3.0, 2.0, 1.0])
    np.testing.assert_allclose(camera.unproject(319.5, 479.5, 2.0), [1.0, 0.0, 1.0], atol=1e-12)


def test_invalid_camera_and_frame_contracts_are_rejected():
    with pytest.raises(ValueError, match="right handed"):
        CameraCalibration(10, 10, 40, np.zeros(3), np.diag([1.0, 1.0, -1.0]))
    with pytest.raises(ValueError, match="orthonormal"):
        CameraCalibration(10, 10, 40, np.zeros(3), np.eye(3) * 2)
    camera = CameraCalibration(10, 10, 40, np.zeros(3), np.eye(3))
    with pytest.raises(ValueError, match="uint8"):
        RGBDFrame(np.zeros((10, 10, 3)), np.ones((10, 10)), camera)
    with pytest.raises(ValueError, match="floating"):
        RGBDFrame(np.zeros((10, 10, 3), dtype=np.uint8), np.ones((10, 10), dtype=int), camera)


def test_missing_depth_does_not_invent_rack_positions():
    camera = CameraCalibration(30, 30, 40, np.array([1.0, 0.0, 1.0]), np.eye(3))
    frame = RGBDFrame(np.full((30, 30, 3), 180, dtype=np.uint8), np.full((30, 30), np.nan), camera)
    assert all(
        r["status"] == "missing" and r["position_m"] is None for r in locate_tools(frame).values()
    )


def test_actual_rgbd_rotated_permuted_tools_and_depth_scale():
    scene = CameraDatasetScene(case())
    try:
        frame = scene.capture()
        predictions = locate_tools(frame)
        # Ground truth is used only after camera-only inference.
        truth = scene.annotations()
        for name, prediction in predictions.items():
            assert prediction["status"] == "observed"
            assert (
                np.linalg.norm(np.array(prediction["position_m"]) - truth[name]["position_m"])
                < 0.005
            )
            rotation = scene.bench.data.xmat[scene.bench.model.body(name).id].reshape(3, 3)
            actual_yaw = np.arctan2(rotation[1, 0], rotation[0, 0])
            yaw_error = (prediction["yaw_mod_pi_rad"] - actual_yaw + np.pi / 2) % np.pi - np.pi / 2
            assert abs(yaw_error) < 0.05
        # Known static mat plane: verify actual rendered axial-depth conversion
        # despite the classic Mac OpenGL clip-control warning.
        u, v = np.rint(frame.camera.project([0.66, -0.18, 0.002])).astype(int)
        point = frame.camera.unproject(u, v, frame.depth_m[v, u])
        assert abs(point[2] - 0.002) < 0.0005
    finally:
        scene.close()


def test_actual_occluded_handle_is_not_a_position_fallback():
    scene = CameraDatasetScene(case("hammer"))
    try:
        predictions = locate_tools(scene.capture())
        assert predictions["hammer"]["status"] != "observed"
        assert predictions["hammer"]["position_m"] is None
    finally:
        scene.close()


def test_identical_visible_handles_are_ambiguous(monkeypatch):
    original = camera_scene_xml(case())
    xml = ET.fromstring(original)
    world = xml.find("worldbody")
    duplicate = copy.deepcopy(world.find("body[@name='wrench']"))
    duplicate.set("name", "decoy")
    duplicate.set("pos", "0.63 0.23 0.026")
    duplicate.find("freejoint").set("name", "decoy_joint")
    world.append(duplicate)
    monkeypatch.setattr(
        "physical_ai_lab.assistant.perception_scene.camera_scene_xml",
        lambda _: ET.tostring(xml, encoding="unicode"),
    )
    scene = CameraDatasetScene(case())
    try:
        prediction = locate_tools(scene.capture())["wrench"]
        assert prediction["status"] == "ambiguous"
        assert prediction["candidate_count"] == 2 and prediction["position_m"] is None
    finally:
        scene.close()
