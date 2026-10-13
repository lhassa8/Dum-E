"""A second optical measurement may recover coverage, never bypass the motion gate."""

import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception import CameraSample, RGBDFrame
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench


def setup(alternate_view=True):
    spec = json.loads((Path(__file__).parents[1] / "fixtures/release_model_cases.json").read_text())
    case = next(c for c in spec["cases"] if c["id"] == "validation-000")
    bench = ToolWorkbench(case["seed"], xml=camera_scene_xml(case, alternate_view=alternate_view))
    return bench, CameraSensor(bench)


def bad_depth(sample):
    frame = sample.frame
    return CameraSample(
        RGBDFrame(frame.rgb, np.full_like(frame.depth_m, np.nan), frame.camera), sample.captured_s
    )


def test_one_failed_primary_view_recovers_real_delivery_with_tool_truth_denied(monkeypatch):
    bench, sensor = setup()
    truth = bench.observe
    before = truth()
    calls = [0, 0]

    class RecoveringCamera:
        def capture_timed(self):
            calls[0] += 1
            sample = sensor.capture_timed()
            return bad_depth(sample) if calls[0] == 1 else sample

        def capture_alternate_timed(self):
            calls[1] += 1
            return sensor.capture_alternate_timed()

    def denied(*unused):
        raise AssertionError("Actor accessed privileged object state")

    monkeypatch.setattr(bench, "observe", denied)
    monkeypatch.setattr(bench, "tool_support_height", denied)
    actor = CameraDelivery(
        SimRobot(bench, recover_ik=True),
        RecoveringCamera(),
        "screwdriver",
        HANDOFF["handoff"],
        verify_motion=True,
        linear_lifts=True,
        center_grasp=True,
        safe_handoff=True,
        alternate_view=True,
    )
    maximum = before["screwdriver"][2]
    try:
        for _ in range(3000):
            if not actor.advance():
                break
            maximum = max(maximum, truth()["screwdriver"][2])
            assert (
                max(np.linalg.norm(truth()[n] - p) for n, p in before.items() if n != "screwdriver")
                < 0.004
            )
        else:
            raise AssertionError("Camera delivery exceeded its unchanged bound")
        actual = truth()["screwdriver"]
        assert actor.outcome.status == "released_unverified"
        assert maximum - before["screwdriver"][2] >= 0.08
        assert np.linalg.norm(actual[:2] - HANDOFF["handoff"]) < 0.035 and actual[2] < 0.04
        assert bench.data.qpos[7:9].sum() > 0.07
        assert calls[1] == 1
        assert any(e.get("view") == "alternate" and e["accepted"] for e in actor.evidence)
    finally:
        sensor.close()
        bench.close()


def test_two_unusable_views_refuse_without_advancing_physics():
    bench, sensor = setup()

    class UnusableCamera:
        def capture_timed(self):
            return bad_depth(sensor.capture_timed())

        def capture_alternate_timed(self):
            return bad_depth(sensor.capture_alternate_timed())

    robot = SimRobot(bench)
    robot.hold()  # Refusal must preserve the existing gravity hold, not nominal HOME targets.
    actor = CameraDelivery(
        robot, UnusableCamera(), "screwdriver", HANDOFF["handoff"], alternate_view=True
    )
    position, controls, clock = bench.data.qpos.copy(), bench.data.ctrl.copy(), bench.data.time
    try:
        assert not actor.advance()
        assert actor.outcome.status == "failed"
        np.testing.assert_array_equal(bench.data.qpos, position)
        np.testing.assert_array_equal(bench.data.ctrl, controls)
        assert bench.data.time == clock
        assert len([e for e in actor.evidence if e["kind"] == "camera"]) == 2
    finally:
        sensor.close()
        bench.close()


def test_unavailable_alternate_calibration_refuses_without_motion():
    bench, sensor = setup(alternate_view=False)

    class MissingCalibration:
        def capture_timed(self):
            return bad_depth(sensor.capture_timed())

        def capture_alternate_timed(self):
            return sensor.capture_alternate_timed()

    actor = CameraDelivery(
        SimRobot(bench),
        MissingCalibration(),
        "screwdriver",
        HANDOFF["handoff"],
        alternate_view=True,
    )
    position, clock = bench.data.qpos.copy(), bench.data.time
    try:
        assert not actor.advance()
        assert actor.outcome.status == "failed" and "unavailable" in actor.outcome.message
        np.testing.assert_array_equal(bench.data.qpos, position)
        assert bench.data.time == clock
    finally:
        sensor.close()
        bench.close()
