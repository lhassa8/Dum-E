"""Simulation-only gripper comparison; placement checks and force caps stay fixed."""

import argparse
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.tool_control import ToolChange, ToolPerformance
from physical_ai_lab.assistant.tool_scene import ToolWorkbench

parser = argparse.ArgumentParser(
    description="Compare bounded gripper gains on the same late-return sequence."
)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
results = []
for gain in [1, 2, 4]:
    b = ToolWorkbench()
    b.model.actuator_gainprm[7, 0] *= gain / 2
    b.model.actuator_biasprm[7, 1] *= gain / 2
    b.model.actuator_biasprm[7, 2] *= np.sqrt(gain / 2)

    def finish(c):
        while c.advance():
            pass
        return c.outcome

    c = ToolPerformance(b, "screwdriver")
    while c.advance():
        if c.phase == "Lifting tool" and b.observe()["screwdriver"][2] > 0.13:
            break
    c.pause()
    ch = ToolChange(b, c, "wrench")
    ch.advance()
    ch.pause()
    for _ in range(8):
        b.tick()
    ch.resume()
    first = finish(ch)
    second = finish(ToolPerformance(b, "wrench", True))
    other = b.observe()["wrench"].copy()
    h = ToolPerformance(b, "hammer")
    force = []
    while h.advance():
        force.append(float(b.data.actuator_force[7]))
        if h.phase == "Placing tool":
            break
    h.pause()
    for _ in range(3):
        b.tick()
    r = h.return_to_rack()
    o = finish(r)
    results.append(
        {
            "gain_multiplier": gain,
            "change": first.__dict__,
            "return_wrench": second.__dict__,
            "return_hammer": o.__dict__,
            "max_grasp_actuator_force_N": max(map(abs, force)),
            "wrench_disturbance_m": float(np.linalg.norm(b.observe()["wrench"] - other)),
        }
    )
    print(results[-1], flush=True)
    b.close()
(args.output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
