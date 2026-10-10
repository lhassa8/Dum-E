import json

import numpy as np
import pytest

from physical_ai_lab.assistant.control import PickPlace
from physical_ai_lab.assistant.language import Intent
from physical_ai_lab.assistant.scene import TARGETS, Workbench
from physical_ai_lab.assistant.tasks import MoveTask, plan_pick_place


@pytest.mark.parametrize(
    "name,destination,seed",
    [
        ("red", "green", 42),
        ("red", "purple", 11),
        ("blue", "green", 12),
        ("blue", "purple", 13),
        ("yellow", "green", 14),
        ("yellow", "purple", 15),
    ],
)
def test_real_grasp_release_and_measured_placement(name, destination, seed):
    bench = Workbench(seed)
    initial = bench.observe()
    controller = PickPlace(bench, name, destination)
    while controller.advance():
        pass
    actual = bench.observe()[name]
    assert controller.outcome.status == "success"
    assert controller.max_height - initial[name][2] > 0.08
    assert np.linalg.norm(actual[:2] - TARGETS[destination]) < 0.035
    assert actual[2] < 0.04
    assert bench.data.qpos[7] > 0.035  # Open gripper, free block on table.
    for other in initial:
        if other != name:
            assert np.linalg.norm(bench.observe()[other] - initial[other]) < 0.004
    bench.close()


def test_failed_grasp_and_interruption_never_claim_placement():
    bench = Workbench()
    bench.model.actuator_forcerange[7] = [0, 0]  # Physical gripper fault, not a mocked outcome.
    failed = PickPlace(bench, "red", "green")
    while failed.advance():
        pass
    assert failed.outcome.status == "failed"
    assert failed.max_height - failed.initial_height < 0.005
    bench.close()
    bench = Workbench()
    stopped = PickPlace(bench, "red", "green")
    for _ in range(20):
        assert stopped.advance()
    before = bench.data.ctrl[:7].copy()
    stopped.stop()
    assert stopped.outcome.status == "interrupted"
    assert not stopped.advance()
    assert not np.array_equal(before, bench.data.ctrl[:7])
    assert "not confirmed" in stopped.outcome.message
    bench.close()


def test_bounded_intents_reject_unknown_actions_and_entities():
    good = Intent.parse(json.dumps({"action": "move", "object": "red", "destination": "green"}))
    assert good.object == "red"
    for fields in [
        {"action": "shell", "object": None, "destination": None},
        {"action": "move", "object": "orange", "destination": "green"},
        {"action": "move", "object": "red", "destination": None},
    ]:
        with pytest.raises(ValueError):
            Intent.parse(json.dumps(fields))
    with pytest.raises(json.JSONDecodeError):
        Intent.parse("I already did it")


def test_task_planner_uses_observations_and_does_not_mutate_them():
    observations = {"red": np.array([0.42, -0.12, 0.022])}
    before = observations["red"].copy()
    steps = plan_pick_place(observations, MoveTask("red", "green"))
    np.testing.assert_array_equal(observations["red"], before)
    np.testing.assert_allclose(steps[0].point, before + [0, 0, 0.2])
    assert any(step.check_lift for step in steps)
    with pytest.raises(ValueError):
        plan_pick_place(observations, MoveTask("missing", "green"))
