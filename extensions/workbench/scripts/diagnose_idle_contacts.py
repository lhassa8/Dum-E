"""Matched offline post-return contact branches; never touches the live simulator."""

import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np

from physical_ai_lab.assistant.tool_control import ToolPerformance
from physical_ai_lab.assistant.tool_scene import ToolWorkbench

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--tool", default="screwdriver", choices=["screwdriver", "wrench", "hammer"])
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--seconds", type=float, default=1800)
parser.add_argument(
    "--variants",
    nargs="+",
    default=["current", "without_noslip", "tighter_noslip", "elliptic"],
    choices=["current", "without_noslip", "tighter_noslip", "elliptic", "elliptic_noslip"],
)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
bench = ToolWorkbench(args.seed, friction_cone="pyramidal", table_contact_dim=None)
try:
    outcomes = []
    for returning in [False, True]:
        controller = ToolPerformance(bench, args.tool, returning)
        while controller.advance():
            pass
        assert controller.outcome.status == "success"
        outcomes.append(controller.outcome.__dict__)
    spec = mujoco.mjtState.mjSTATE_INTEGRATION
    # mj_step leaves cached body poses at the pre-integration stage. Synchronize
    # kinematics before recording the state and its reference positions.
    mujoco.mj_forward(bench.model, bench.data)
    original = np.empty(mujoco.mj_stateSize(bench.model, spec))
    mujoco.mj_getState(bench.model, bench.data, original, spec)
    initial = bench.observe()
    summary = []
    variants = [
        ("current", mujoco.mjtCone.mjCONE_PYRAMIDAL, 1, 3, 1e-6),
        ("without_noslip", mujoco.mjtCone.mjCONE_PYRAMIDAL, 1, 0, 1e-6),
        ("tighter_noslip", mujoco.mjtCone.mjCONE_PYRAMIDAL, 1, 3, 1e-10),
        ("elliptic", mujoco.mjtCone.mjCONE_ELLIPTIC, 10, 0, 1e-6),
        ("elliptic_noslip", mujoco.mjtCone.mjCONE_ELLIPTIC, 1, 3, 1e-6),
    ]
    for name, cone, impratio, iterations, tolerance in variants:
        if name not in args.variants:
            continue
        bench.model.opt.cone = cone
        bench.model.opt.impratio = impratio
        bench.model.opt.noslip_iterations = iterations
        bench.model.opt.noslip_tolerance = tolerance
        # Counterfactual resets are offline only. There is no subsequent pose/
        # velocity assignment, freeze, attachment or equality constraint.
        mujoco.mj_setState(bench.model, bench.data, original, spec)
        mujoco.mj_forward(bench.model, bench.data)
        rows, maximum = [], {n: 0.0 for n in initial}
        began = float(bench.data.time)
        before = bench.observe()
        assert max(np.linalg.norm(before[n] - initial[n]) for n in before) < 1e-8
        for tick in range(math.ceil(args.seconds / 0.032)):
            bench.tick()
            positions = bench.observe()
            for tool in initial:
                maximum[tool] = max(
                    maximum[tool], float(np.linalg.norm(positions[tool] - initial[tool]))
                )
            if tick % 312 == 0:
                address = bench.model.joint(f"{args.tool}_joint").dofadr[0]
                rows.append(
                    {
                        "seconds": float(bench.data.time) - began,
                        "positions": {n: p.tolist() for n, p in positions.items()},
                        "tool_speed_m_s": float(
                            np.linalg.norm(bench.data.qvel[address : address + 3])
                        ),
                        "max_displacement_m": dict(maximum),
                    }
                )
            if tick % 18750 == 0 and tick:
                print(
                    f"{name}: {(tick + 1) * 0.032:.0f}s, "
                    f"tool drift {maximum[args.tool] * 1000:.3f}mm",
                    flush=True,
                )
        result = {
            "variant": name,
            "cone": int(cone),
            "impratio": impratio,
            "noslip_iterations": iterations,
            "noslip_tolerance": tolerance,
            "simulated_seconds": float(bench.data.time) - began,
            "max_displacement_m": maximum,
            "rows": rows,
            "initial": {n: p.tolist() for n, p in initial.items()},
        }
        (args.output / f"{name}.json").write_text(json.dumps(result, indent=2) + "\n")
        summary.append({k: v for k, v in result.items() if k != "rows"})
        (args.output / "summary.json").write_text(
            json.dumps(
                {
                    "scope": "Offline identical post-return state; no live robot change",
                    "tool": args.tool,
                    "seed": args.seed,
                    "outcomes": outcomes,
                    "variants": summary,
                },
                indent=2,
            )
            + "\n"
        )
        print(json.dumps(summary[-1]), flush=True)
finally:
    bench.close()
