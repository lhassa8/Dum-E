"""Fresh supported evidence is mandatory before any placement correction."""

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception import CameraSample, RGBDFrame
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench


def test_release_verification_requires_existing_motion_and_clearance_guards():
    with pytest.raises(ValueError, match="safe handoff and verified motion"):
        CameraDelivery(SimpleNamespace(), None, "wrench", [0.64, -0.16], verify_release=True)


@pytest.mark.parametrize("bad_frame", ["missing_depth", "stale"])
def test_unusable_postrelease_view_cannot_trigger_another_pickup(bad_frame):
    root = Path(__file__).resolve().parents[1]
    case = next(
        c
        for c in json.loads((root / "fixtures/release_model_cases.json").read_text())["cases"]
        if c["id"] == "validation-001"
    )
    bench = ToolWorkbench(case["seed"], xml=camera_scene_xml(case))
    sensor = CameraSensor(bench)
    blocked_state = []

    def capture():
        sample = sensor.capture_timed()
        if actor.phase == "Checking released tool with camera":
            blocked_state.append((bench.data.qpos.copy(), bench.data.ctrl.copy(), bench.data.time))
            if bad_frame == "stale":
                return CameraSample(sample.frame, sample.captured_s - 1)
            frame = sample.frame
            return CameraSample(
                RGBDFrame(frame.rgb, np.full_like(frame.depth_m, np.nan), frame.camera),
                sample.captured_s,
            )
        return sample

    actor = CameraDelivery(
        SimRobot(bench, recover_ik=True, refine_cartesian=True),
        SimpleNamespace(capture_timed=capture),
        case["tool"],
        HANDOFF["handoff"],
        verify_motion=True,
        linear_lifts=True,
        center_grasp=True,
        safe_handoff=True,
        verify_release=True,
    )
    try:
        for _ in range(3000):
            if not actor.advance():
                break
        assert blocked_state and actor.outcome.status == "failed"
        assert actor.correction_attempts == 0 and not actor.carrying
        qpos, ctrl, time = blocked_state[-1]
        np.testing.assert_array_equal(bench.data.qpos, qpos)
        assert bench.data.time == time
        assert bench.data.ctrl[7] == ctrl[7] == 255
    finally:
        sensor.close()
        bench.close()
