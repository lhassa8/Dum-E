"""Exercise the real release predicate without importing the native simulator."""

import ast
import threading
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def predicate():
    source = Path(__file__).resolve().parents[1]/"scripts/libero_runtime.py"
    module = ast.parse(source.read_text())
    runtime = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == "Runtime")
    method = next(n for n in runtime.body if isinstance(n, ast.FunctionDef)
                  and n.name == "placement_ready")
    scope = {"np": np}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), scope)
    return scope["placement_ready"]


def samples():
    return [{"sim_time": i*.002, "xyz": [0., 0., .9], "success": True,
             "plate_contact": True, "any_gripper_contact": False} for i in range(251)]


def check(rows):
    runtime = SimpleNamespace(release_samples=deque(rows[:-1], maxlen=1000),
                              judge=lambda: rows[-1], initial_plate_xyz=[0., 0., .9],
                              released_placement=None)
    return predicate()(runtime), runtime.released_placement


def test_stable_supported_release_passes():
    passed, evidence = check(samples())
    assert passed and len(evidence["samples"]) == 251


@pytest.mark.parametrize("field,value", [("success", False), ("plate_contact", False),
                                         ("any_gripper_contact", True)])
def test_one_bad_native_contact_or_goal_sample_rejects(field, value):
    rows = samples()
    rows[100][field] = value
    assert check(rows) == (False, None)


def test_short_support_window_rejects():
    assert check(samples()[:-1]) == (False, None)


def test_outside_original_placement_limit_rejects():
    rows = samples()
    for row in rows:
        row["xyz"][0] = .035001
    assert check(rows) == (False, None)


def test_rest_motion_limit_rejects():
    rows = samples()
    rows[-1]["xyz"][0] = .005001
    assert check(rows) == (False, None)


def test_resume_cannot_execute_step221():
    source = Path(__file__).resolve().parents[1]/"scripts/libero_runtime.py"
    module = ast.parse(source.read_text())
    runtime = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == "Runtime")
    tick = next(n for n in runtime.body if isinstance(n, ast.FunctionDef) and n.name == "tick")
    scope = {"np": np, "time": time, "args": SimpleNamespace(hold_profile="joint")}
    exec(compile(ast.Module(body=[tick], type_ignores=[]), str(source), "exec"), scope)
    state = SimpleNamespace(lock=threading.RLock(), pending_init=None, env=object(),
                            phase="running", epoch=3, native_init_epoch=1,
                            active_steps=220, queue=deque([[0.]*7]))
    scope["tick"](state)
    assert state.phase == "failed" and state.active_steps == 220 and not state.queue


def test_running_generation_rejects_pre_stop_actions():
    source = Path(__file__).resolve().parents[1]/"scripts/libero_runtime.py"
    module = ast.parse(source.read_text())
    runtime = next(n for n in module.body if isinstance(n, ast.ClassDef) and n.name == "Runtime")
    enqueue = next(n for n in runtime.body if isinstance(n, ast.FunctionDef)
                   and n.name == "enqueue")
    scope = {"np": np}
    exec(compile(ast.Module(body=[enqueue], type_ignores=[]), str(source), "exec"), scope)
    state = SimpleNamespace(phase="running", epoch=3, queue=deque())
    with pytest.raises(ValueError, match="Stale"):
        scope["enqueue"](state, 1, [[0.]*7])
    assert not state.queue
