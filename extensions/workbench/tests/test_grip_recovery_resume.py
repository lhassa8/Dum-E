"""Interrupted recovery cannot bypass hand-state or ownership guards."""

from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import CameraDelivery, RobotReading
from physical_ai_lab.assistant.control import Outcome


@pytest.mark.parametrize(
    "phase,attempts,carrying,closing,gap",
    [
        ("Holding after unstable grip", 1, True, False, 0.004),
        ("Holding after unstable grip", 1, True, True, float("nan")),
        ("Opening confirmed empty hand", 1, True, False, 0.080),
        ("Opening confirmed empty hand", 1, False, False, float("nan")),
        ("Opening confirmed empty hand", 1, False, True, 0.040),
        ("Retracting empty hand for rescan", 1, False, True, 0.040),
        ("Retracting empty hand for rescan", 0, False, False, 0.080),
    ],
)
def test_inconsistent_or_unowned_recovery_resume_is_refused(
    phase, attempts, carrying, closing, gap
):
    holds = []
    reading = RobotReading(np.zeros(7), np.array([0.5, 0, 0.3]), np.eye(3), gap, closing, 0)
    actor = CameraDelivery(
        SimpleNamespace(read=lambda: reading, hold=lambda: holds.append(1)),
        None,
        "wrench",
        [0.64, -0.16],
        phase_recovery=True,
        recover_grip=True,
        safe_handoff=True,
        verify_motion=True,
        linear_lifts=True,
    )
    actor.grip_recovery_attempts = attempts
    actor.carrying = carrying
    actor.paused_phase = phase
    actor.outcome = Outcome("interrupted", "Stopped")
    frames = actor.frames
    actor.resume()
    assert actor.outcome.status == "failed" and holds == [1]
    assert actor.frames is frames and actor.revision == 0
    assert actor.grip_recovery_attempts == attempts
