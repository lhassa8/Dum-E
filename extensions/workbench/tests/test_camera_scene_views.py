"""A scene retry must keep uncertain neighbors gated and select one complete view."""

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

import physical_ai_lab.assistant.camera_control as control
import physical_ai_lab.assistant.handoff_planning as planning


def prediction(x):
    return {
        "status": "observed",
        "fit_score": 0.99,
        "position_m": [x, 0.22, 0.022],
        "yaw_mod_pi_rad": 0.0,
        "surface_normal": [0, 0, 1],
    }


def actor():
    a = control.CameraDelivery.__new__(control.CameraDelivery)
    a.object = "screwdriver"
    a.alternate_view = True
    a.phase = "Checking clear space for release"
    a.evidence = []
    a.scene_history = {}
    a.robot = SimpleNamespace(read=lambda: SimpleNamespace(time_s=4.0))
    a.camera = SimpleNamespace(
        capture_timed=lambda: SimpleNamespace(frame="primary", captured_s=4.0),
        capture_alternate_timed=lambda: SimpleNamespace(frame="alternate", captured_s=4.0),
    )
    return a


def test_neighbor_ambiguity_selects_complete_fresh_alternate_frame(monkeypatch):
    a = actor()
    primary = {
        "screwdriver": prediction(0.44),
        "wrench": {"status": "ambiguous"},
        "hammer": prediction(0.43),
    }
    alternate = {
        "screwdriver": prediction(0.45),
        "wrench": prediction(0.46),
        "hammer": prediction(0.47),
    }
    monkeypatch.setattr(
        control, "locate_tools", lambda frame: primary if frame == "primary" else alternate
    )
    planner = Mock(return_value=(np.eye(3), {"mode": "inherited"}))
    monkeypatch.setattr(planning, "choose_handoff", planner)
    a._handoff_plan()
    assert planner.call_args.args[1].frame == "alternate"
    assert planner.call_args.args[2] is alternate
    assert a.evidence[-1]["view"] == "alternate"
    assert set(a.scene_history) == {"wrench", "hammer"}


def test_two_ambiguous_views_do_not_use_cached_neighbor_as_identification(monkeypatch):
    a = actor()
    ambiguous = {
        "screwdriver": prediction(0.44),
        "wrench": {"status": "ambiguous"},
        "hammer": prediction(0.43),
    }
    a.scene_history["wrench"] = control.validate_observation("wrench", prediction(0.46), 4.0, 4.0)
    monkeypatch.setattr(control, "locate_tools", lambda frame: ambiguous)
    with pytest.raises(ValueError, match="ambiguous"):
        a._handoff_plan()
    assert a.evidence[-1]["view"] == "primary" and len(a.evidence[-1]["refusals"]) == 2


def test_alternate_frame_with_one_invalid_neighbor_is_not_partially_merged(monkeypatch):
    a = actor()
    primary = {
        "screwdriver": prediction(0.44),
        "wrench": {"status": "ambiguous"},
        "hammer": prediction(0.43),
    }
    partial = {
        "screwdriver": prediction(0.45),
        "wrench": prediction(0.46),
        "hammer": {"status": "ambiguous"},
    }
    monkeypatch.setattr(
        control, "locate_tools", lambda frame: primary if frame == "primary" else partial
    )
    with pytest.raises(ValueError, match="ambiguous"):
        a._handoff_plan()
    assert a.scene_history == {} and a.evidence[-1]["view"] == "primary"
