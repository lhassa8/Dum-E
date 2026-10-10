"""Task planning from observed scene entities; no MuJoCo or language-model dependency."""

from dataclasses import dataclass

import numpy as np

from physical_ai_lab.assistant.entities import TARGETS


@dataclass(frozen=True)
class MoveTask:
    object: str
    destination: str


@dataclass(frozen=True)
class Step:
    phase: str
    gripper: int
    point: np.ndarray | None = None
    ticks: int = 0
    check_lift: bool = False


def plan_pick_place(observations, task, targets=None):
    targets = TARGETS if targets is None else targets
    if task.object not in observations or task.destination not in targets:
        raise ValueError("Unknown object or target")
    pick = np.asarray(observations[task.object], dtype=float).copy()
    target = np.array([*targets[task.destination], pick[2]])
    return (
        Step("Approaching block", 255, pick + [0, 0, 0.20]),
        Step("Lowering gripper", 255, pick + [0, 0, 0.002]),
        Step("Grasping", 0, ticks=35),
        Step("Lifting block", 0, pick + [0, 0, 0.20]),
        Step("Checking grasp", 0, check_lift=True),
        Step("Moving to target", 0, target + [0, 0, 0.20]),
        Step("Placing block", 0, target + [0, 0, 0.008]),
        Step("Releasing", 255, ticks=28),
        Step("Withdrawing gripper", 255, target + [0, 0, 0.20]),
        Step("Checking placement", 255, ticks=30),
    )
