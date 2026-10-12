"""Replay C3 perception and inspect raw wrist servo substeps; no gain changes."""

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import mujoco
import numpy as np

import physical_ai_lab.assistant.camera_control as control
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.release_model import ReleaseModel
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
# Either lab or independently exported fork's known C3 commit. No arbitrary code.
for reference, path in [
    ("9ad4c4e", "src/physical_ai_lab/assistant/perception.py"),
    ("50d8c76", "extensions/workbench/src/physical_ai_lab/assistant/perception.py"),
]:
    source = subprocess.run(["git", "show", f"{reference}:{path}"], capture_output=True)
    if source.returncode == 0:
        break
else:
    raise ValueError("The frozen C3 perception source is unavailable")
prior = args.output / "prior_perception.py"
prior.write_bytes(source.stdout)
spec = importlib.util.spec_from_file_location("prior_perception", prior)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
control.locate_tools = module.locate_tools
case = next(
    c
    for c in json.loads(Path("fixtures/release_model_cases.json").read_text())["cases"]
    if c["id"] == "validation-000"
)
b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case))
b.model.vis.headlight.diffuse[:] *= case["light"]
sensor = CameraSensor(b)
model = ReleaseModel(
    "src/physical_ai_lab/assistant/assets/learned/release-outcome-v2-experimental.npz"
)
first = control.CameraDelivery(
    SimRobot(b), sensor, case["tool"], HANDOFF["handoff"], release_model=model
)
try:
    for _ in range(3000):
        if not first.advance():
            break
    returned = control.CameraDelivery(
        SimRobot(b), sensor, case["tool"], first.rack_xy, release_model=model
    )
    for _ in range(3000):
        if not returned.advance() or returned.phase == "Choosing release action":
            break
    readings = []
    for _ in range(128):
        mujoco.mj_step(b.model, b.data)
        readings.append(
            {
                "time_s": float(b.data.time),
                "velocity_rad_s": float(b.data.qvel[6]),
                "torque_nm": float(b.data.actuator_force[6]),
                "position_rad": float(b.data.qpos[6]),
                "command_rad": float(b.data.ctrl[6]),
            }
        )
    summary = {
        "case": case["id"],
        "phase": returned.phase,
        "samples": readings,
        "scope": "Raw2ms steps at unchanged servo command; oldC3 perception; "
        "no model/gain/force changes",
        "source_reference": reference,
        "source_sha256": hashlib.sha256(source.stdout).hexdigest(),
        "mean_torque_nm": float(np.mean([r["torque_nm"] for r in readings])),
        "torque_sign_changes": int(
            sum(
                np.sign(a["torque_nm"]) != np.sign(c["torque_nm"])
                for a, c in zip(readings, readings[1:])
            )
        ),
        "joint7_drift_rad": readings[-1]["position_rad"] - readings[0]["position_rad"],
    }
    (args.output / "results.json").write_text(json.dumps(summary, indent=2) + "\n")
    print({k: v for k, v in summary.items() if k != "samples"})
    print(readings[:8])
finally:
    sensor.close()
    b.close()
