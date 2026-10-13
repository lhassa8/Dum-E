"""Diagnostic camera-adapter replay; all truth is confined to the evaluator."""

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image

from physical_ai_lab.assistant.camera_tasks import CameraTasks
from physical_ai_lab.assistant.perception_scene import camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--pace", type=float, default=0, help="Owner frame wall interval, seconds")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    protocol_bytes = (root / "fixtures/camera_live_recovery_diagnostic.json").read_bytes()
    protocol = json.loads(protocol_bytes)
    fixture_bytes = (root / protocol["known_fixture"]).read_bytes()
    assert hashlib.sha256(fixture_bytes).hexdigest() == protocol["known_fixture_sha256"]
    case = next(c for c in json.loads(fixture_bytes)["cases"] if c["id"] == protocol["known_case"])
    args.output.mkdir(parents=True, exist_ok=False)
    rows = []
    for mode, tool in [("known_loss_redirect", case["tool"])] + [
        ("continued_returns", name) for name in protocol["repeat_tools"]
    ]:
        bench = ToolWorkbench(
            case["seed"] if mode == "known_loss_redirect" else 42,
            xml=camera_scene_xml(
                case if mode == "known_loss_redirect" else {"layout": {}}, alternate_view=True
            ),
        )
        if mode == "known_loss_redirect":
            bench.model.vis.headlight.diffuse[:] *= case["light"]
        epoch = [0]
        hub = CameraTasks(bench, epoch=lambda: epoch[0])
        truth = bench.observe
        racks = {name: xyz[:2].copy() for name, xyz in truth().items()}
        native_tick = bench.tick
        evaluation = {}

        def measured_tick(*inputs, **options):
            native_tick(*inputs, **options)
            if evaluation:
                positions = truth()
                evaluation["maximum"] = max(evaluation["maximum"], positions[tool][2])
                evaluation["disturbance"] = max(
                    evaluation["disturbance"],
                    max(
                        float(np.linalg.norm(xyz - evaluation["initial"][name]))
                        for name, xyz in positions.items()
                        if name != tool
                    ),
                )

        bench.tick = measured_tick

        def denied(*unused):
            raise AssertionError("Actor requested privileged object state")

        bench.observe = bench.tool_support_height = denied
        try:
            count = 1 if mode == "known_loss_redirect" else protocol["repeat_cycles"]
            for cycle in range(count):
                failed = False
                for returning in [False] if mode == "known_loss_redirect" else [False, True]:
                    initial = truth()
                    evaluation = {
                        "initial": initial,
                        "maximum": initial[tool][2],
                        "disturbance": 0.0,
                    }
                    controller = hub.select(tool, returning)
                    stopped = False
                    phases = []
                    for step in range(protocol["frame_limit"]):
                        started = time.monotonic()
                        more = controller.advance()
                        if not phases or phases[-1] != controller.phase:
                            phases.append(controller.phase)
                        if not more:
                            break
                        if (
                            not returning
                            and not stopped
                            and controller.phase == protocol["stop_phase"]
                        ):
                            epoch[0] += 1
                            controller.pause()
                            for _ in range(protocol["stop_frames"]):
                                bench.tick()
                                controller.measure()
                            if mode == "known_loss_redirect":
                                controller.return_to_rack()
                            else:
                                controller.resume()
                            stopped = True
                        time.sleep(max(0, args.pace - (time.monotonic() - started)))
                    actual = truth()[tool]
                    target = (
                        racks[tool]
                        if returning or mode == "known_loss_redirect"
                        else HANDOFF["handoff"]
                    )
                    distance = float(np.linalg.norm(actual[:2] - target))
                    address = bench.model.joint(f"{tool}_joint").dofadr[0]
                    speed = float(np.linalg.norm(bench.data.qvel[address : address + 3]))
                    lift = float(evaluation["maximum"] - initial[tool][2])
                    opened = bool(bench.data.qpos[7:9].sum() > 0.070)
                    criteria = protocol["criteria"]
                    passed = bool(
                        distance < criteria["placement_m"]
                        and actual[2] < criteria["rest_height_m"]
                        and speed < criteria["rest_speed_m_s"]
                        and lift >= criteria["lift_m"]
                        and evaluation["disturbance"] < criteria["unrelated_translation_m"]
                        and opened
                    )
                    row = {
                        "mode": mode,
                        "tool": tool,
                        "cycle": cycle,
                        "returning": returning,
                        "stopped": stopped,
                        "steps": step,
                        "phases": phases,
                        "outcome": asdict(controller.outcome) if controller.outcome else None,
                        "lift_m": float(controller.max_height - controller.initial_height),
                        "unrelated_m": controller.disturbance,
                        "diagnostics": controller.diagnostics(),
                        "independent_judge": {
                            "distance_m": distance,
                            "height_m": float(actual[2]),
                            "speed_m_s": speed,
                            "lift_m": lift,
                            "unrelated_m": evaluation["disturbance"],
                            "gripper_open": opened,
                            "passed": passed,
                        },
                    }
                    rows.append(row)
                    print(
                        json.dumps({k: v for k, v in row.items() if k != "diagnostics"}), flush=True
                    )
                    (args.output / "results.json").write_text(
                        json.dumps(
                            {
                                "protocol_sha256": hashlib.sha256(protocol_bytes).hexdigest(),
                                "pace_s": args.pace,
                                "rows": rows,
                            },
                            indent=2,
                        )
                        + "\n"
                    )
                    if (
                        not passed
                        or not controller.outcome
                        or controller.outcome.status != "success"
                    ):
                        Image.fromarray(hub.sensor.capture().rgb).save(
                            args.output / f"failure-{mode}-{tool}-{cycle}.png"
                        )
                        failed = True
                        break
                if failed:
                    break
        finally:
            hub.close()
            bench.close()


if __name__ == "__main__":
    main()
