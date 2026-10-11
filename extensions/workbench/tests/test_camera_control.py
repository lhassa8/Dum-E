"""Physics and denied-truth checks for image-informed experimental manipulation."""

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import CameraDelivery, validate_observation
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception import CameraSample, RGBDFrame
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench


def scene():
    return {
        "seed": 99333,
        "layout": {
            "screwdriver": [0.42, 0.23, 0.72],
            "wrench": [0.47, -0.23, -0.85],
            "hammer": [0.43, 0, 0.63],
        },
    }


def reject_truth(*args):
    raise AssertionError("Actor accessed privileged tool state")


@pytest.mark.parametrize("name", ["screwdriver", "wrench", "hammer"])
def test_camera_pickup_with_privileged_tool_access_denied(name, monkeypatch):
    b = ToolWorkbench(99333, xml=camera_scene_xml(scene()))
    sensor = CameraSensor(b)
    observer = b.observe
    initial = observer()[name].copy()
    controller = CameraDelivery(SimRobot(b), sensor, name, HANDOFF["handoff"])
    monkeypatch.setattr(b, "observe", reject_truth)
    monkeypatch.setattr(b, "tool_support_height", reject_truth)
    maximum = initial[2]
    try:
        while controller.advance():
            # Saved truth observer is available only to this independent judge.
            maximum = max(maximum, observer()[name][2])
        assert controller.outcome.status == "released_unverified"
        assert maximum - initial[2] > 0.08
        actual = observer()[name]
        assert np.linalg.norm(actual[:2] - HANDOFF["handoff"]) < 0.035
        assert actual[2] < 0.04
        assert b.data.qpos[7:9].sum() > 0.07
    finally:
        sensor.close()
        b.close()


def test_unknown_camera_target_cannot_trigger_a_fallback_move():
    b = ToolWorkbench(99333, xml=camera_scene_xml(scene()))
    sensor = CameraSensor(b)
    frame = sensor.capture()

    class MissingDepth:
        def capture_timed(self):
            return CameraSample(
                RGBDFrame(frame.rgb, np.full_like(frame.depth_m, np.nan), frame.camera),
                float(b.data.time),
            )

    before = b.data.qpos.copy()
    start_time = b.data.time
    controller = CameraDelivery(SimRobot(b), MissingDepth(), "wrench", HANDOFF["handoff"])
    try:
        assert not controller.advance()
        assert controller.outcome.status == "failed"
        np.testing.assert_array_equal(b.data.qpos, before)
        assert b.data.time == start_time
    finally:
        sensor.close()
        b.close()


@pytest.mark.parametrize("change", ["stale", "ambiguous", "weak", "invalid", "nan_score"])
def test_motion_gate_rejects_unusable_observations(change):
    prediction = {
        "status": "observed",
        "fit_score": 0.95,
        "position_m": [0.43, 0, 0.022],
        "yaw_mod_pi_rad": 0.3,
    }
    if change == "ambiguous":
        prediction["status"] = "ambiguous"
    elif change == "weak":
        prediction["fit_score"] = 0.65
    elif change == "invalid":
        prediction["position_m"][0] = np.nan
    elif change == "nan_score":
        prediction["fit_score"] = np.nan
    with pytest.raises(ValueError):
        validate_observation("wrench", prediction, 1, 2 if change == "stale" else 1)


def test_cached_camera_frame_is_rejected_before_motion():
    b = ToolWorkbench(99333, xml=camera_scene_xml(scene()))
    sensor = CameraSensor(b)
    sample = sensor.capture_timed()
    for _ in range(10):
        b.tick()

    class CachedCamera:
        def capture_timed(self):
            return sample

    controller = CameraDelivery(SimRobot(b), CachedCamera(), "wrench", HANDOFF["handoff"])
    before = b.data.qpos.copy()
    try:
        assert not controller.advance()
        assert controller.outcome.status == "failed"
        assert "stale" in controller.outcome.message
        np.testing.assert_array_equal(b.data.qpos, before)
    finally:
        sensor.close()
        b.close()


def test_empty_jaw_failure_is_not_claimed_as_delivery():
    b = ToolWorkbench(99333, xml=camera_scene_xml(scene()))
    sensor = CameraSensor(b)
    b.model.actuator_forcerange[7] = [0, 0]
    controller = CameraDelivery(SimRobot(b), sensor, "screwdriver", HANDOFF["handoff"])
    try:
        while controller.advance():
            pass
        assert controller.outcome.status == "failed"
        assert "pickup unconfirmed" in controller.outcome.message
        assert b.observe()["screwdriver"][2] < 0.04
    finally:
        sensor.close()
        b.close()
