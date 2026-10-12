"""Fixed full physics journeys, long idle and real re-pickup; no renderer or model."""

import argparse
import concurrent.futures
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

import mujoco
import numpy as np

from physical_ai_lab.assistant.tool_control import ToolPerformance
from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS, ToolWorkbench


def run_case(output, mode, tool, seed, protocol):
    name = f"{mode}-{tool}-{seed}"
    result = {"id": name, "mode": mode, "tool": tool, "seed": seed, "passed": False}
    bench = ToolWorkbench(seed, table_contact_dim=3 if mode == "sliding_table" else None)
    started = perf_counter()

    def checkpoint():
        path = Path(output) / f"{name}.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(result, indent=2) + "\n")
        temporary.replace(path)

    try:
        initial = bench.observe()
        maximum_other = 0.0

        def update_other():
            nonlocal maximum_other
            positions = bench.observe()
            maximum_other = max(
                maximum_other,
                max(
                    float(np.linalg.norm(positions[n] - xyz))
                    for n, xyz in initial.items()
                    if n != tool
                ),
            )

        def finish(controller, target):
            before = bench.observe()[tool].copy()
            max_height = float(before[2])
            for _ in range(3000):
                more = controller.advance()
                update_other()
                max_height = max(max_height, float(bench.observe()[tool][2]))
                if not more:
                    break
            else:
                raise AssertionError("Fixed controller frame limit exceeded")
            xyz = bench.observe()[tool]
            address = bench.model.joint(f"{tool}_joint").dofadr[0]
            error = float(np.linalg.norm(xyz[:2] - target))
            speed = float(np.linalg.norm(bench.data.qvel[address : address + 3]))
            return {
                "outcome": controller.outcome.__dict__,
                "error_m": error,
                "height_m": float(xyz[2]),
                "speed_m_s": speed,
                "observed_lift_m": float(max_height - before[2]),
                "passed": bool(
                    controller.outcome.status == "success"
                    and error < protocol["maximum_placement_error_m"]
                    and xyz[2] < protocol["maximum_resting_height_m"]
                    and speed < protocol["maximum_resting_speed_m_s"]
                    and max_height - before[2] > protocol["minimum_lift_m"]
                ),
            }

        delivery = ToolPerformance(bench, tool)
        for _ in range(2500):
            assert delivery.advance()
            update_other()
            if delivery.phase == "Lifting tool" and bench.observe()[tool][2] > 0.13:
                break
        else:
            raise AssertionError("Expected early lift not reached")
        joints, grip = bench.data.qpos[:7].copy(), float(bench.data.ctrl[7])
        delivery.pause()
        min_height, max_drift, retained = float("inf"), 0.0, True
        for _ in range(math.ceil(protocol["hold_seconds"] / 0.032)):
            bench.tick()
            update_other()
            min_height = min(min_height, float(bench.observe()[tool][2]))
            max_drift = max(max_drift, float(np.max(np.abs(bench.data.qpos[:7] - joints))))
            retained &= bench.data.ctrl[7] == grip
        result["hold"] = {
            "min_height_m": min_height,
            "max_joint_drift_rad": max_drift,
            "grip_retained": bool(retained),
            "passed": bool(retained)
            and min_height > protocol["minimum_held_height_m"]
            and max_drift < protocol["maximum_hold_joint_drift_rad"],
        }
        checkpoint()
        delivery.resume()
        result["delivery"] = finish(delivery, HANDOFF["handoff"])
        checkpoint()
        result["return"] = finish(ToolPerformance(bench, tool, True), TOOLS[tool])
        checkpoint()
        mujoco.mj_forward(bench.model, bench.data)
        returned = bench.observe()
        peak = {n: 0.0 for n in returned}
        rows = []
        began = float(bench.data.time)
        for tick in range(math.ceil(protocol["idle_seconds"] / 0.032)):
            # The same16 physical substeps and32ms judging cadence. A separate
            # 1000-frame probe verified bitwise-identical integration states.
            # No object/velocity assignment or batching speed claim.
            mujoco.mj_step(bench.model, bench.data, nstep=16)
            positions = bench.observe()
            for n in returned:
                peak[n] = max(peak[n], float(np.linalg.norm(positions[n] - returned[n])))
            if tick % 3125 == 0:
                rows.append(
                    {"seconds": float(bench.data.time) - began, "peak_displacement_m": dict(peak)}
                )
        actual = bench.observe()[tool]
        result["idle"] = {
            "simulated_seconds": float(bench.data.time) - began,
            "peak_displacement_m": peak,
            "rows": rows,
            "rack_error_m": float(np.linalg.norm(actual[:2] - TOOLS[tool])),
            "passed": bool(
                max(peak.values()) < protocol["maximum_idle_displacement_m"]
                and np.linalg.norm(actual[:2] - TOOLS[tool]) < protocol["maximum_placement_error_m"]
            ),
        }
        checkpoint()
        result["repick"] = finish(ToolPerformance(bench, tool), HANDOFF["handoff"])
        result["other_tool_displacement_m"] = maximum_other
        result["object_weld_added"] = bench.model.neq != 1
        result["passed"] = (
            all(
                result[stage]["passed"]
                for stage in ["hold", "delivery", "return", "idle", "repick"]
            )
            and not result["object_weld_added"]
            and maximum_other < protocol["maximum_other_tool_displacement_m"]
        )
    except Exception as error:
        result["failure"] = repr(error)
    finally:
        result["wall_seconds"] = perf_counter() - started
        checkpoint()
        bench.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["current", "sliding_table"],
        default=["current", "sliding_table"],
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    fixture = Path(__file__).resolve().parents[1] / "fixtures/idle_placement_cases.json"
    protocol = json.loads(fixture.read_text())
    rows = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(run_case, str(args.output), mode, tool, seed, protocol)
            for mode in args.modes
            for tool in protocol["tools"]
            for seed in protocol["seeds"]
        ]
        for future in concurrent.futures.as_completed(futures):
            row = future.result()
            rows.append(row)
            summary = {
                "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
                "protocol": protocol,
                "rows": rows,
            }
            (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(
                json.dumps(
                    {k: v for k, v in row.items() if k != "idle"}
                    | {"idle": {k: v for k, v in row.get("idle", {}).items() if k != "rows"}}
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
