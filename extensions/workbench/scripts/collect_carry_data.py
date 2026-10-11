"""Collect separately labeled carry trajectories; no labels enter the actor."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.carry_model import carry_features
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
parser.add_argument("--fixture", type=Path, default=Path("fixtures/carry_model_cases.json"))
parser.add_argument("--additional-training-fixture", type=Path)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
fixture = json.loads(args.fixture.read_text())
cases = fixture["cases"]
extension_hash = None
if args.additional_training_fixture:
    extension = json.loads(args.additional_training_fixture.read_text())
    assert extension["base_fixture_sha256"] == hashlib.sha256(args.fixture.read_bytes()).hexdigest()
    assert all(c["split"] == "train" for c in extension["cases"])
    assert not {c["id"] for c in cases} & {c["id"] for c in extension["cases"]}
    cases = cases + extension["cases"]
    extension_hash = hashlib.sha256(args.additional_training_fixture.read_bytes()).hexdigest()
features, labels, episodes, splits, records = [], [], [], [], []
for case in cases:
    if case["split"] == "test":
        continue  # Untouched physical test cases are not used for training or tuning.
    b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case))
    b.model.vis.headlight.diffuse[:] *= case["light"]
    sensor = CameraSensor(b)
    count_before = len(features)
    outcomes = []
    try:
        first = CameraDelivery(SimRobot(b), sensor, case["tool"], HANDOFF["handoff"])
        for leg in range(2):
            actor = (
                first
                if leg == 0
                else CameraDelivery(SimRobot(b), sensor, case["tool"], first.rack_xy)
            )
            paused = False
            for tick in range(3000):
                if not actor.advance():
                    break
                if actor.carrying and actor.direction_yaw is not None and tick % 4 == 0:
                    reading = actor.robot.read()
                    x = carry_features(actor, reading)
                    # Privileged labels are read AFTER actor inference/actuation.
                    actual = b.observe()[case["tool"]]
                    rigid = actor._estimate()[0]
                    # Fit free-space carrying, not contact with the table.
                    if actual[2] > 0.08:
                        y = reading.rotation.T @ (actual - rigid)
                        features.append(x)
                        labels.append(y)
                        episodes.append(case["id"])
                        splits.append(case["split"])
                if (
                    not paused
                    and case["journey"] != "deliver"
                    and actor.phase == "Moving to target"
                ):
                    actor.pause()
                    for _ in range(19):
                        b.tick()
                    if case["journey"] == "redirect" and leg == 0:
                        actor.return_to_rack()
                    else:
                        actor.resume()
                    paused = True
            else:
                raise RuntimeError("Trajectory exceeded fixed frame limit")
            outcomes.append(actor.outcome.__dict__)
            if actor.outcome.status != "released_unverified" or case["journey"] == "redirect":
                break
        records.append({"case": case, "rows": len(features) - count_before, "outcomes": outcomes})
        print(
            case["id"],
            "rows",
            records[-1]["rows"],
            "outcomes",
            [o["status"] for o in outcomes],
            flush=True,
        )
    finally:
        sensor.close()
        b.close()
np.savez_compressed(
    args.output / "data.npz",
    features=np.array(features),
    labels=np.array(labels),
    episodes=np.array(episodes),
    splits=np.array(splits),
)
manifest = {
    "fixture_sha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
    "data_sha256": hashlib.sha256((args.output / "data.npz").read_bytes()).hexdigest(),
    "records": records,
    "rows": len(features),
    "scope": "Simulator labels only in collector; test scenes excluded",
    "additional_training_fixture_sha256": extension_hash,
}
(args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
