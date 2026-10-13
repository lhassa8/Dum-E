"""Grip-loss recovery cannot open an uncertain hand or loop without a budget."""

from types import SimpleNamespace

import numpy as np
import pytest

from physical_ai_lab.assistant.camera_control import CameraDelivery, RobotReading, UnstableGrip


@pytest.mark.parametrize("gap", [0.04, float("nan")])
def test_uncertain_hand_is_never_opened_after_grip_braking(gap):
    commands = []
    reading = RobotReading(np.zeros(7), np.array([0.5, 0, 0.3]), np.eye(3), gap, True, 0)
    robot = SimpleNamespace(
        read=lambda: reading,
        hold=lambda: None,
        tick=lambda joints=None, gripper=None: commands.append(gripper),
    )
    actor = CameraDelivery(
        robot,
        None,
        "wrench",
        [0.64, -0.16],
        recover_grip=True,
        safe_handoff=True,
        verify_motion=True,
        linear_lifts=True,
    )
    actor.carrying = True
    list(actor._recover_lost_grip())
    assert actor.outcome.status == "failed" and "opening refused" in actor.outcome.message
    assert commands == [0] * 100 and actor.carrying
    assert actor.grip_recovery_attempts == 1


def test_exhausted_grip_budget_keeps_hold_without_another_settle_or_pickup():
    holds = []
    actor = CameraDelivery(
        SimpleNamespace(hold=lambda: holds.append(1)),
        None,
        "wrench",
        [0.64, -0.16],
        recover_grip=True,
        safe_handoff=True,
        verify_motion=True,
        linear_lifts=True,
    )
    actor.grip_recovery_attempts = 1
    list(actor._recover_lost_grip())
    assert actor.outcome.status == "failed" and "budget exhausted" in actor.outcome.message
    assert holds == [1] and actor.grip_recovery_attempts == 1 and not actor.evidence


def test_grip_recovery_requires_existing_motion_guards():
    with pytest.raises(ValueError, match="safe handoff, verified motion and linear lifts"):
        CameraDelivery(SimpleNamespace(), None, "wrench", [0.64, -0.16], recover_grip=True)


@pytest.mark.parametrize(
    "height,gap,refused", [(0.025, 0.042, False), (0.15, 0.042, True), (0.025, 0.009, True)]
)
def test_tabletop_gap_settling_is_distinct_from_loss_without_disabling_binary_gate(
    height, gap, refused
):
    before = RobotReading(np.zeros(7), np.array([0.5, 0, height]), np.eye(3), 0.046, True, 0)
    after = RobotReading(np.zeros(7), before.tcp_m.copy(), np.eye(3), gap, True, 0.032)
    held = []
    actor = CameraDelivery(
        SimpleNamespace(read=lambda: after, hold=lambda: held.append(1)),
        None,
        "wrench",
        [0.64, -0.16],
        recover_grip=True,
        safe_handoff=True,
        verify_motion=True,
        linear_lifts=True,
    )
    actor.carrying = True
    if refused:
        with pytest.raises(UnstableGrip):
            actor._check_carry_grip(before)
        assert held == [1]
    else:
        actor._check_carry_grip(before)
        assert not held and not actor.evidence
