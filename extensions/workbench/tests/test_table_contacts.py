"""Measured contact contracts for tabletop stability and physical release."""

import httpx
import mujoco
import numpy as np
import pytest

from physical_ai_lab.assistant.tool_control import ToolPerformance
from physical_ai_lab.assistant.tool_scene import ToolWorkbench


def test_table_sliding_contacts_preserve_grip_contacts_and_force_limits():
    baseline = ToolWorkbench(table_contact_dim=None)
    candidate = ToolWorkbench()
    try:
        assert np.array_equal(candidate.model.body_mass, baseline.model.body_mass)
        assert np.array_equal(candidate.model.geom_size, baseline.model.geom_size)
        assert np.array_equal(
            candidate.model.actuator_forcerange, baseline.model.actuator_forcerange
        )
        for bench, expected in [(baseline, 6), (candidate, 3)]:
            for _ in range(100):
                bench.tick()
            floor = bench.model.geom("workbench").id
            contacts = [c for c in bench.data.contact if floor in (c.geom1, c.geom2)]
            assert contacts and all(c.dim == expected for c in contacts)
            for contact in contacts:
                assert np.array_equal(contact.friction, [1.5, 1.5, 0.04, 0.01, 0.01])
                assert np.array_equal(contact.solref, [0.02, 1])
                assert np.array_equal(contact.solimp, [0.9, 0.95, 0.001, 0.5, 2])
            performance = ToolPerformance(bench, "screwdriver")
            for _ in range(2500):
                assert performance.advance()
                if performance.phase == "Lifting tool" and bench.observe()["screwdriver"][2] > 0.13:
                    break
            else:
                raise AssertionError("Physical grasp not reached")
            held_contacts = [c for c in bench.data.contact if floor not in (c.geom1, c.geom2)]
            assert held_contacts and all(c.dim == 6 for c in held_contacts)
            assert bench.model.neq == 1
            for _ in range(100):
                bench.tick(gripper=255)
            assert bench.observe()["screwdriver"][2] < 0.04
    finally:
        baseline.close()
        candidate.close()


def test_returned_tool_stays_near_its_placement_and_can_be_picked_up_again():
    # Fast regression; the frozen qualification separately covers30 simulated
    # minutes, three tools and three starting variations with Stop/resume.
    bench = ToolWorkbench()
    try:
        for returning in [False, True]:
            controller = ToolPerformance(bench, "screwdriver", returning)
            while controller.advance():
                pass
            assert controller.outcome.status == "success"
        mujoco.mj_forward(bench.model, bench.data)
        reference = bench.observe()
        for _ in range(1000):
            bench.tick()
            assert max(np.linalg.norm(bench.observe()[n] - p) for n, p in reference.items()) < 0.004
        controller = ToolPerformance(bench, "screwdriver")
        while controller.advance():
            pass
        assert controller.outcome.status == "success"
        assert controller.outcome.distance_m < 0.035
    finally:
        bench.close()


def test_launcher_rejects_reusing_old_or_unverified_tool_contacts(monkeypatch, tmp_path):
    from physical_ai_lab.assistant.tool_scene import TOOL_PHYSICS_PROFILE
    from physical_ai_lab.dume.app import ensure_simulator

    snapshot = {
        "backend": "workbench",
        "last_outcome": None,
        "busy": False,
        "profile": "tools",
        "language_backend": "mlx",
    }
    monkeypatch.delenv("WORKBENCH_MODEL", raising=False)
    monkeypatch.setenv("WORKBENCH_LANGUAGE_BACKEND", "mlx")
    monkeypatch.setattr(
        "physical_ai_lab.dume.app.httpx.get",
        lambda *a, **k: httpx.Response(200, json=snapshot, request=httpx.Request("GET", a[0])),
    )
    for profile in [None, "tool_contacts_v1"]:
        snapshot["physics_profile"] = profile
        with pytest.raises(RuntimeError, match="older or unverified tool contacts"):
            ensure_simulator(8775, tmp_path, tools=True)
    snapshot["physics_profile"] = TOOL_PHYSICS_PROFILE
    assert ensure_simulator(8775, tmp_path, tools=True) is None
