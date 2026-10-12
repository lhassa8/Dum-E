"""Locate retained contact failure phases outside the actor's information boundary."""

import argparse
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
case = next(
    c
    for c in json.loads(Path("fixtures/release_model_cases.json").read_text())["cases"]
    if c["id"] == "validation-004"
)
b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case))
b.model.vis.headlight.diffuse[:] *= case["light"]
sensor = CameraSensor(b)
initial = b.observe()
records = []
first = CameraDelivery(
    SimRobot(b, recover_ik=True),
    sensor,
    case["tool"],
    HANDOFF["handoff"],
    verify_motion=True,
    linear_lifts=True,
    center_grasp=True,
)
try:
    for leg in range(2):
        actor = (
            first
            if leg == 0
            else CameraDelivery(
                SimRobot(b, recover_ik=True),
                sensor,
                case["tool"],
                first.rack_xy,
                verify_motion=True,
                linear_lifts=True,
                center_grasp=True,
            )
        )
        samples = []
        paused = False
        for _ in range(3000):
            if not actor.advance():
                break
            truth = b.observe()  # Labels only, never fed back to the actor.
            row = {
                "phase": actor.phase,
                "other_displacement_m": {
                    n: float(np.linalg.norm(p - initial[n]))
                    for n, p in truth.items()
                    if n != case["tool"]
                },
                "actual_tool_center_m": truth[case["tool"]].tolist(),
            }
            if actor.offset_local is not None:
                estimate, rotation = actor._estimate()
                row["inferred_center_m"] = estimate.tolist()
                body = b.model.body(case["tool"]).id
                actualR = b.data.xmat[body].reshape(3, 3)
                row["inferred_rotation_error_rad"] = float(
                    np.arccos(np.clip((np.trace(rotation.T @ actualR) - 1) / 2, -1, 1))
                )
                row["support_height_truth_m"] = float(b.tool_support_height(case["tool"]))
            samples.append(row)
            if (
                leg == 0
                and case["journey"] == "resume"
                and not paused
                and actor.phase == "Moving to target"
            ):
                actor.pause()
                for _ in range(19):
                    b.tick()
                actor.resume()
                paused = True
        records.append({"leg": leg, "outcome": actor.outcome.__dict__, "samples": samples})
    (args.output / "results.json").write_text(json.dumps(records, indent=2) + "\n")
    for r in records:
        print("leg", r["leg"], r["outcome"])
        endpoint = {s["phase"]: s for s in r["samples"]}
        for phase, s in endpoint.items():
            print(phase, s)
finally:
    sensor.close()
    b.close()
