"""Counterfactual physical release trajectories; truth never enters actor inputs."""

import argparse
import hashlib
import inspect
import json
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

from physical_ai_lab.assistant.camera_control import CameraDelivery
from physical_ai_lab.assistant.camera_robot import SimRobot
from physical_ai_lab.assistant.perception_scene import CameraSensor, camera_scene_xml
from physical_ai_lab.assistant.release_model import FEATURE_VERSION, release_features
from physical_ai_lab.assistant.tool_scene import HANDOFF, ToolWorkbench

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
parser.add_argument("--fixture", type=Path, default=Path("fixtures/release_model_cases.json"))
parser.add_argument("--limit", type=int)
parser.add_argument("--case", help="One non-test diagnostic case; never a training dataset")
parser.add_argument("--recovery-profile", action="store_true")
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
fixture = json.loads(args.fixture.read_text())
actions = np.array(fixture["actions_xy_m"])
zero = int(np.flatnonzero(np.linalg.norm(actions, axis=1) == 0)[0])
spec = mujoco.mjtState.mjSTATE_INTEGRATION
xs, ys, episodes, splits, legs, action_ids, records = [], [], [], [], [], [], []
cases = [c for c in fixture["cases"] if c["split"] != "test"]
if args.case:
    cases = [c for c in cases if c["id"] == args.case]
    if len(cases) != 1:
        raise ValueError("Choose exactly one known non-test case")
if args.limit is not None:
    cases = cases[: args.limit]
profile = {"verify_motion": True, "safe_handoff": True} if args.recovery_profile else {}


def camera_actor(bench, sensor, tool, target):
    return CameraDelivery(
        SimRobot(bench, recover_ik=args.recovery_profile), sensor, tool, target, **profile
    )


for case in cases:
    b = ToolWorkbench(case["seed"], xml=camera_scene_xml(case))
    b.model.vis.headlight.diffuse[:] *= case["light"]
    sensor = CameraSensor(b)
    record = {"case": case, "legs": []}
    first = camera_actor(b, sensor, case["tool"], HANDOFF["handoff"])
    try:
        for leg in range(2):
            actor = first if leg == 0 else camera_actor(b, sensor, case["tool"], first.rack_xy)
            paused = False
            for _ in range(3000):
                if not actor.advance():
                    break
                if actor.phase == "Choosing release action":
                    break
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
                raise RuntimeError("Carry exceeded fixed frame limit")
            if actor.phase != "Choosing release action":
                record["legs"].append({"leg": leg, "status": actor.outcome.__dict__, "rows": 0})
                break
            point = actor._place_point()
            # Unprivileged features are formed before snapshot/label truth reads.
            branch_features = [release_features(actor, point, action) for action in actions]
            state = np.empty(mujoco.mj_stateSize(b.model, spec))
            mujoco.mj_getState(b.model, b.data, state, spec)
            before = b.observe()  # Evaluation labels only, outside the actor.
            # Compare branch replay with the normal actor continuation as well
            # as an independent repeated zero-action branch.
            for _ in range(3000):
                if not actor.advance():
                    break
            else:
                raise RuntimeError("Normal release exceeded fixed frame limit")
            normal_final = np.empty_like(state)
            mujoco.mj_getState(b.model, b.data, normal_final, spec)
            normal_status = actor.outcome.__dict__
            outcomes, finals, statuses = [], [], []
            for index in [*range(len(actions)), zero]:
                # Exact branch replay is a collector tool, never a deployed model input.
                mujoco.mj_setState(b.model, b.data, state, spec)
                mujoco.mj_forward(b.model, b.data)
                branch = camera_actor(b, sensor, case["tool"], actor.target)
                for name in [
                    "orientation",
                    "offset_local",
                    "body_rotation_local",
                    "observation",
                    "grasp_reading",
                    "direction_yaw",
                    "initial_scene_estimates",
                    "rack_xy",
                    "last_motion_check",
                    "planned_neighbors",
                    "reoriented_carry",
                ]:
                    setattr(branch, name, getattr(actor, name))
                if hasattr(actor, "scene_prediction_uncertainty"):
                    branch.scene_prediction_uncertainty = actor.scene_prediction_uncertainty
                branch.carrying = True
                proposed = point + np.r_[actions[index], 0]
                branch.frames = branch.finish_release(proposed)
                maximum_disturbance = 0.0
                try:
                    for _ in range(3000):
                        if not branch.advance():
                            break
                        if args.recovery_profile:
                            maximum_disturbance = max(
                                maximum_disturbance,
                                max(
                                    np.linalg.norm(b.observe()[n] - p)
                                    for n, p in before.items()
                                    if n != case["tool"]
                                ),
                            )
                    else:
                        raise RuntimeError("Release exceeded fixed frame limit")
                except ValueError as error:
                    branch.robot.hold()
                    from physical_ai_lab.assistant.control import Outcome

                    branch.outcome = Outcome("failed", str(error))
                actual = b.observe()[case["tool"]]
                adr = b.model.joint(f"{case['tool']}_joint").dofadr[0]
                speed = np.linalg.norm(b.data.qvel[adr : adr + 3])
                disturbance = max(
                    np.linalg.norm(b.observe()[n] - p)
                    for n, p in before.items()
                    if n != case["tool"]
                )
                if args.recovery_profile:
                    disturbance = max(disturbance, maximum_disturbance)
                outcome = np.r_[actual[:2] - actor.target, actual[2], speed, disturbance]
                final_state = np.empty_like(state)
                mujoco.mj_getState(b.model, b.data, final_state, spec)
                if len(outcomes) == len(actions):
                    repeat_error = float(np.max(np.abs(final_state - finals[zero])))
                    if repeat_error > 1e-8:
                        raise RuntimeError(f"Baseline snapshot replay diverged: {repeat_error}")
                    break
                if index == zero:
                    normal_error = float(np.max(np.abs(final_state - normal_final)))
                    if normal_error > 1e-8:
                        raise RuntimeError(f"Normal continuation diverged: {normal_error}")
                xs.append(branch_features[index])
                ys.append(outcome - np.r_[actions[index], 0, 0, 0])
                episodes.append(case["id"])
                splits.append(case["split"])
                legs.append(leg)
                action_ids.append(index)
                outcomes.append(outcome.tolist())
                finals.append(final_state)
                statuses.append(branch.outcome.__dict__)
            # Continue only the zero-action branch's actual physical settled state.
            mujoco.mj_setState(b.model, b.data, finals[zero], spec)
            mujoco.mj_forward(b.model, b.data)
            if case["id"] == cases[0]["id"]:
                Image.fromarray(sensor.capture().rgb).save(args.output / f"baseline-leg-{leg}.png")
            actor.frames.close()
            record["legs"].append(
                {
                    "leg": leg,
                    "rows": len(actions),
                    "outcomes": outcomes,
                    "statuses": statuses,
                    "normal_status": normal_status,
                    "repeat_max_state_error": repeat_error,
                    "normal_continuation_max_state_error": normal_error,
                    "deliberately_reoriented": bool(actor.reoriented_carry),
                }
            )
            print(
                case["id"], "leg", leg, "branches", len(actions), "repeat", repeat_error, flush=True
            )
            if case["journey"] == "redirect" or normal_status["status"] != "released_unverified":
                break
        records.append(record)
        (args.output / "records.json").write_text(json.dumps(records, indent=2) + "\n")
    finally:
        sensor.close()
        b.close()
np.savez_compressed(
    args.output / "data.npz",
    features=np.array(xs),
    labels=np.array(ys),
    episodes=np.array(episodes),
    splits=np.array(splits),
    legs=np.array(legs),
    action_ids=np.array(action_ids),
)
manifest = {
    "fixture_sha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
    "data_sha256": hashlib.sha256((args.output / "data.npz").read_bytes()).hexdigest(),
    "feature_version": FEATURE_VERSION,
    "rows": len(xs),
    "records": records,
    "scope": "Future physical labels and full-state branching only in collector; tests excluded",
    "limited_pilot": 1 if args.case else args.limit,
    "selected_diagnostic_case": args.case,
    "controller_recipe": "D2d_verified_camera_recovery" if args.recovery_profile else "C3_legacy",
    "outcome_label_version": 2 if args.recovery_profile else 1,
    "disturbance_label": "Maximum at every32ms release motion/hold frame"
    if args.recovery_profile
    else "Final displacement only",
    "controller_source_sha256": hashlib.sha256(
        Path(inspect.getfile(CameraDelivery)).read_bytes()
    ).hexdigest(),
}
(args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
