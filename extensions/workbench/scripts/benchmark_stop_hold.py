"""Compare the original hold, contact correction, and gravity-compensated hold."""

import argparse
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.tool_control import ToolPerformance
from physical_ai_lab.assistant.tool_scene import TOOLS, ToolWorkbench

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
summary = []
for mode in ["baseline", "contact_only", "fixed"]:
    for tool in TOOLS:
        for seed in [42, 51, 52]:
            bench = ToolWorkbench(seed)
            rows = []
            evidence = {"mode": mode, "tool": tool, "seed": seed, "rows": rows}
            try:
                if mode == "baseline":
                    bench.model.opt.noslip_iterations = 0
                controller = ToolPerformance(bench, tool)
                for _ in range(2500):
                    assert controller.advance()
                    if controller.phase == "Lifting tool" and bench.observe()[tool][2] > 0.13:
                        break
                else:
                    raise AssertionError("Expected early lift not reached")
                initial = bench.observe()[tool].copy()
                joints = bench.data.qpos[:7].copy()
                grip = float(bench.data.ctrl[7])
                controller.pause()
                if mode != "fixed":
                    # Exact original arm hold; keep the same closed gripper command.
                    bench.data.ctrl[:7] = joints
                for tick in range(1000):
                    bench.tick()
                    assert bench.data.ctrl[7] == grip
                    rows.append({
                        "seconds": (tick + 1) * 0.032,
                        "height_m": float(bench.observe()[tool][2]),
                        "joint_drift_rad": float(np.max(np.abs(bench.data.qpos[:7] - joints))),
                        "grip_force_N": float(bench.data.actuator_force[7]),
                    })
                evidence.update(
                    initial_height_m=float(initial[2]),
                    final_height_m=rows[-1]["height_m"],
                    minimum_height_m=min(r["height_m"] for r in rows),
                    maximum_joint_drift_rad=max(r["joint_drift_rad"] for r in rows),
                    retained=all(r["height_m"] > 0.13 and r["joint_drift_rad"] < 0.02
                                 for r in rows),
                )
                assert bench.model.neq == 1
                summary.append({k: v for k, v in evidence.items() if k != "rows"})
                print(json.dumps(summary[-1]), flush=True)
            finally:
                (args.output / f"{mode}-{tool}-{seed}.json").write_text(
                    json.dumps(evidence, indent=2) + "\n"
                )
                (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
                bench.close()
