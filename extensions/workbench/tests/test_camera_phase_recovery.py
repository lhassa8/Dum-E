"""Recovery guards must retain the hold without starting another physical action."""

from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import CameraDelivery, RobotReading
from physical_ai_lab.assistant.control import Outcome


@pytest.mark.parametrize(
    "phase,carrying,gap,closing,height,interrupted",
    [
        ("Approaching tool", False, 0.04, True, 0.20, True),
        ("Grasping", False, 0.04, True, 0.20, True),
        ("Withdrawing gripper", False, 0.04, True, 0.24, True),
        ("Lifting tool", True, 0.005, True, 0.20, True),
        ("Unknown phase", False, 0.08, False, 0.24, True),
        ("Approaching tool", False, 0.08, False, 0.24, False),
    ],
)
def test_unsupported_phase_recovery_retains_hold(
    phase, carrying, gap, closing, height, interrupted
):
    calls = []
    reading = RobotReading(np.zeros(7), np.array([0.4, 0, height]), np.eye(3), gap, closing, 0)
    robot = SimpleNamespace(read=lambda: reading, hold=lambda: calls.append("hold"))
    actor = CameraDelivery(robot, None, "wrench", [0.64, -0.16], phase_recovery=True)
    actor.carrying = carrying
    actor.paused_phase = phase
    actor.outcome = Outcome("interrupted", "Stopped") if interrupted else None
    frames = actor.frames
    actor.resume()
    assert actor.outcome.status == "failed"
    assert actor.frames is frames and actor.revision == 0
    assert calls == ["hold"] and not actor.evidence


def test_duplicate_pause_preserves_the_original_phase():
    robot = SimpleNamespace(hold=lambda: None)
    actor = CameraDelivery(robot, None, "wrench", [0.64, -0.16], phase_recovery=True)
    actor.phase = "Releasing"
    actor.pause()
    actor.phase = "Changed externally"
    actor.pause()
    assert actor.paused_phase == "Releasing"


@pytest.mark.parametrize("status", ["failed", "released_unverified"])
def test_pause_cannot_resurrect_an_ended_task(status):
    robot = SimpleNamespace(hold=lambda: None)
    actor = CameraDelivery(robot, None, "wrench", [0.64, -0.16], phase_recovery=True)
    outcome = Outcome(status, "Ended")
    actor.outcome = outcome
    actor.pause()
    assert actor.outcome is outcome and actor.paused_phase is None
