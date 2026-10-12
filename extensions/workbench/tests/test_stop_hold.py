"""Long paused holds retain tools through contacts, then actually release them."""

import numpy as np
import pytest

from physical_ai_lab.assistant.tool_control import ToolPerformance
from physical_ai_lab.assistant.tool_scene import TOOLS, ToolWorkbench


@pytest.mark.parametrize("tool", list(TOOLS))
@pytest.mark.parametrize("seed", [42, 51, 52])
def test_paused_early_lift_retains_tool_for_32_seconds_and_releases(tool, seed):
    bench = ToolWorkbench(seed)
    controller = ToolPerformance(bench, tool)
    try:
        for _ in range(2500):
            assert controller.advance()
            if controller.phase == "Lifting tool" and bench.observe()[tool][2] > 0.13:
                break
        else:
            pytest.fail("Early lift was not reached")
        position = bench.observe()[tool].copy()
        joints = bench.data.qpos[:7].copy()
        grip = float(bench.data.ctrl[7])
        controller.pause()
        for _ in range(1000):
            bench.tick()
            assert bench.observe()[tool][2] > 0.13  # Preserve the earlier retained-tool gate.
            assert np.max(np.abs(bench.data.qpos[:7] - joints)) < 0.02
            assert bench.data.ctrl[7] == grip
        assert np.linalg.norm(bench.observe()[tool] - position) < 0.01
        # No weld/teleport/pose freeze: opening fingers drops the free body.
        for _ in range(100):
            bench.tick(gripper=255)
        assert bench.observe()[tool][2] < 0.04
        assert bench.model.neq == 1  # Original finger coupling, no object equality constraints.
    finally:
        bench.close()


@pytest.mark.parametrize("tool", list(TOOLS))
@pytest.mark.parametrize("continuation", ["resume", "return"])
def test_long_hold_can_continue_to_verified_placement(tool, continuation):
    bench = ToolWorkbench()
    controller = ToolPerformance(bench, tool)
    try:
        for _ in range(2500):
            assert controller.advance()
            if controller.phase == "Lifting tool" and bench.observe()[tool][2] > 0.13:
                break
        else:
            pytest.fail("Early lift was not reached")
        controller.pause()
        for _ in range(1000):
            bench.tick()
        if continuation == "resume":
            controller.resume()
        else:
            controller = controller.return_to_rack()
        while controller.advance():
            pass
        assert controller.outcome.status == "success"
        assert controller.outcome.distance_m < 0.035
        assert bench.observe()[tool][2] < 0.04
    finally:
        bench.close()
