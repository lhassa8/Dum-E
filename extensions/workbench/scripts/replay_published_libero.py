"""Native replay of a frozen public demonstration set; no model inference or training."""

import argparse
import hashlib
import json
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("preparation", type=Path)
parser.add_argument("inspection", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
parser.add_argument("--diagnose-first", action="store_true")
parser.add_argument("--interrupt", action="store_true")
args = parser.parse_args()
manifest = json.loads((args.preparation/"preparation.json").read_text())
inspection = json.loads((args.inspection/"report.json").read_text())
protocol_path = Path(__file__).resolve().parents[1]/"docs/published-replay-protocol.json"
protocol = json.loads(protocol_path.read_text())
protocol["interrupt_enabled"] = args.interrupt
if args.diagnose_first:
    protocol["cases"] = protocol["cases"][:1]
    protocol["diagnostic_scope"] = "First original case only; localize fidelity error"
assert manifest["verified"] and manifest["revision"] == protocol["dataset_revision"]
args.output.mkdir(parents=True, exist_ok=False)
(args.output/"protocol.json").write_text(json.dumps(protocol, indent=2)+"\n")
(args.output/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
source = args.openpi.resolve()
for path in (source, source/"third_party/libero", source/"packages/openpi-client/src"):
    sys.path.insert(0, str(path))
import h5py  # noqa: E402
import numpy as np  # noqa: E402
import robosuite  # noqa: E402
from examples.libero.main import _get_libero_env  # noqa: E402
from libero.libero import benchmark  # noqa: E402
from PIL import Image  # noqa: E402
from robosuite.controllers.joint_pos import JointPositionController  # noqa: E402

suite = benchmark.get_benchmark_dict()["libero_spatial"]()
report = {"protocol": protocol, "episodes": []}
for case in protocol["cases"]:
    task = suite.get_task(case["task_id"])
    entry = next(t for t in inspection["tasks"] if t["task_id"] == case["task_id"])
    identity = next(e for e in entry["episodes"] if e["demo"] == case["demo"])
    assert not identity["excluded_state_overlap"]
    filename = f"libero_spatial/{task.name}_demo.hdf5"
    spec = next(f for f in manifest["files"] if f["name"] == filename)
    path = args.preparation/filename
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            digest.update(block)
    assert digest.hexdigest() == spec["sha256"]
    directory = args.output/f"task{case['task_id']}-{case['demo']}"
    directory.mkdir()
    (directory/"observations").mkdir()
    (directory/"hold-observations").mkdir()
    result = {**case, "error": None, "source_sha256": spec["sha256"],
              "interruption_triggered": False}
    samples, records, checks, replay_states, held = [], [], [], [], []
    env, _ = _get_libero_env(task, 256, 7)
    try:
        with h5py.File(path, "r") as data:
            demo = data[f"data/{case['demo']}"]
            actions, states = demo["actions"][:], demo["states"][:]
            stored_eef, stored_gripper = demo["obs/ee_pos"][:], demo["obs/gripper_states"][:]
            tree = ET.fromstring(demo.attrs["model_file"])
        asset_roots = [source/"third_party/libero/libero/libero/assets",
                       Path(robosuite.__file__).parent/"models/assets"]
        relocated = 0
        for node in tree.findall("./asset/*"):
            old = node.get("file")
            if old:
                assert "/assets/" in old
                suffix = old.split("/assets/", 1)[1]
                candidates = [root/suffix for root in asset_roots]
                candidates = [p.resolve() for p in candidates if p.exists()]
                assert len(candidates) == 1, f"Ambiguous/missing asset: {suffix}"
                assert any(r.resolve() in candidates[0].parents for r in asset_roots)
                node.set("file", str(candidates[0]))
                relocated += 1
        xml = ET.tostring(tree, encoding="unicode")
        (directory/"relocated-model.xml").write_text(xml)
        env.reset()
        env.reset_from_xml_string(xml)
        env.sim.reset()
        obs = env.set_init_state(states[0])
        native, robot = env.env, env.env.robots[0]
        native.ignore_done = True
        robot.controller.update(force=True)
        assert robot.controller.name == "OSC_POSE"
        assert np.all(robot.controller.kp == 150)
        assert np.allclose(robot.controller.output_max, [.05]*3+[.5]*3)
        body = native.obj_body_id["akita_black_bowl_1"]
        target = native.objects_dict["akita_black_bowl_1"].contact_geoms
        bowl = {native.sim.model.geom_name2id(g) for g in target}
        plate = {native.sim.model.geom_name2id(g)
                 for g in native.objects_dict["plate_1"].contact_geoms}
        gripper = {native.sim.model.geom_name2id(g) for g in robot.gripper.contact_geoms}
        initial = native.sim.data.body_xpos[body].copy()
        plate_xyz = native.sim.data.body_xpos[native.obj_body_id["plate_1"]].copy()
        result.update(initial_xyz=initial.tolist(), initial_plate_xyz=plate_xyz.tolist(),
                      relocated_assets=relocated, source_steps=len(actions))
        result["state_layout"] = {"nq": native.sim.model.nq, "nv": native.sim.model.nv,
                                  "joint_names": list(native.sim.model.joint_names),
                                  "qpos_addresses": native.sim.model.jnt_qposadr.tolist(),
                                  "qvel_addresses": native.sim.model.jnt_dofadr.tolist()}
        hold_active = False
        controller = robot.controller
        joint = (JointPositionController(
            sim=controller.sim, eef_name=controller.eef_name,
            joint_indexes={"joints": controller.joint_index, "qpos": controller.qpos_index,
                           "qvel": controller.qvel_index},
            actuator_range=controller.actuator_limits, kp=300, damping_ratio=2)
                 if args.interrupt else None)

        def measure():
            pairs = [{int(c.geom1), int(c.geom2)} for c in
                     native.sim.data.contact[:native.sim.data.ncon]]
            return {"xyz": native.sim.data.body_xpos[body].tolist(),
                    "joints": robot._joint_positions.tolist(), "holding": hold_active,
                    "sim_time": float(native.sim.data.time),
                    "grasp": bool(native._check_grasp(robot.gripper, target)),
                    "any_gripper_contact": any(p & bowl and p & gripper for p in pairs),
                    "plate_contact": any(p & bowl and p & plate for p in pairs),
                    "native_goal": bool(native._check_success())}

        original = robot.controller.run_controller

        def observe():
            sample = measure()
            samples.append(sample)
            torque = original()
            if hold_active:
                held.append(sample)
                return joint.run_controller()
            return torque

        robot.controller.run_controller = observe
        sequence = list(actions)+[[0.]*6+[float(actions[-1, -1])]]*protocol["settle_steps"]
        assert len(sequence) <= protocol["max_active_steps"]
        fields = ("agentview_image", "robot0_eye_in_hand_image", "robot0_eef_pos",
                  "robot0_eef_quat", "robot0_gripper_qpos")
        for index, action in enumerate(sequence):
            action = np.asarray(action)
            assert action.shape == (7,) and np.isfinite(action).all() and np.abs(action).max() <= 1
            np.savez(directory/"observations"/f"{index:04d}.npz", **{k: obs[k] for k in fields})
            pre_eef, pre_gripper = obs["robot0_eef_pos"].copy(), obs["robot0_gripper_qpos"].copy()
            pre_state = env.get_sim_state().copy()
            replay_states.append(pre_state)
            obs, _, _, _ = env.step(action.tolist())
            measured = measure()
            samples.append(measured)
            records.append({"index": index, "action": action.tolist(), "judge": measured,
                            "source": "published" if index < len(actions) else "settle"})
            if index < len(actions):
                checks.append({"index": index,
                               "pre_reference_state_error": float(np.abs(
                                   pre_state-states[index]).max()),
                               "max_state_error_index": int(np.abs(
                                   pre_state-states[index]).argmax()),
                               "qpos_error": float(np.abs(
                                   pre_state[1:1+native.sim.model.nq]
                                   -states[index, 1:1+native.sim.model.nq]).max()),
                               "qvel_error": float(np.abs(
                                   pre_state[1+native.sim.model.nq:]
                                   -states[index, 1+native.sim.model.nq:]).max()),
                               "pre_eef_error_m": float(np.linalg.norm(pre_eef-stored_eef[index])),
                               "post_eef_error_m": float(np.linalg.norm(
                                   obs["robot0_eef_pos"]-stored_eef[index])),
                               "pre_gripper_error": float(np.abs(
                                   pre_gripper-stored_gripper[index]).max()),
                               "post_gripper_error": float(np.abs(
                                   obs["robot0_gripper_qpos"]-stored_gripper[index]).max())})
            if (args.interrupt and not result["interruption_triggered"]
                    and index < len(actions) and measured["grasp"]
                    and measured["xyz"][2]-initial[2] >= .08):
                result.update(interruption_triggered=True, hold_insertion_index=index+1)
                joint.update(force=True)
                joint.set_goal(np.zeros(7), set_qpos=joint.joint_pos.copy())
                hold_active = True
                held.append(measure())
                np.savez(directory/"hold-observations"/"0000.npz",
                         **{k: obs[k] for k in fields})
                started, origin = time.monotonic(), held[0]["sim_time"]
                frame = 0
                while time.monotonic()-started < 2 or held[-1]["sim_time"]-origin <= 1:
                    tick = time.monotonic()
                    obs, _, _, _ = env.step([0.]*6+[1.])
                    sample = measure()
                    held.append(sample)
                    samples.append(sample)
                    frame += 1
                    np.savez(directory/"hold-observations"/f"{frame:04d}.npz",
                             **{k: obs[k] for k in fields})
                    time.sleep(max(0, .05-(time.monotonic()-tick)))
                xyz_hold = np.asarray([s["xyz"] for s in held])
                joints_hold = np.asarray([s["joints"] for s in held])
                result.update(hold_min_lift_m=float(xyz_hold[:, 2].min()-initial[2]),
                              hold_translation_m=float(np.linalg.norm(
                                  xyz_hold-xyz_hold[0], axis=1).max()),
                              hold_joint_range_rad=float(np.ptp(joints_hold, axis=0).max()),
                              hold_all_grasp=all(s["grasp"] for s in held),
                              hold_wall_s=time.monotonic()-started,
                              hold_sim_s=held[-1]["sim_time"]-origin)
                result["hold_passed"] = (result["hold_min_lift_m"] >= .08
                                          and result["hold_translation_m"] <= .01
                                          and result["hold_joint_range_rad"] <= .02
                                          and result["hold_all_grasp"])
                hold_active = False
        result.update(active_steps=len(records),
                      max_reference_state_error=max(c["pre_reference_state_error"] for c in checks),
                      pre_eef_error_median_m=float(np.median(
                          [c["pre_eef_error_m"] for c in checks])),
                      post_eef_error_median_m=float(np.median(
                          [c["post_eef_error_m"] for c in checks])),
                      qualified_lift=any(s["grasp"] and s["xyz"][2]-initial[2] >= .08
                                         for s in samples))
        window = [s for s in samples if s["sim_time"] >= samples[-1]["sim_time"]-.5-1e-10]
        xyz = np.asarray([s["xyz"] for s in window])
        result.update(rest_sim_s=window[-1]["sim_time"]-window[0]["sim_time"],
                      final_plate_contact=all(s["plate_contact"] for s in window),
                      final_no_gripper_contact=all(not s["any_gripper_contact"] for s in window),
                      final_native_goal=all(s["native_goal"] for s in window),
                      rest_movement_m=float(np.linalg.norm(xyz-xyz[0], axis=1).max()),
                      placement_xy_error_m=float(np.linalg.norm(xyz[-1, :2]-plate_xyz[:2])))
        result["fidelity_passed"] = (result["max_reference_state_error"] <=
                                     protocol["reference_state_max_error"])
        result["physical_passed"] = (result["qualified_lift"] and result["final_plate_contact"]
                                     and result["final_no_gripper_contact"]
                                     and result["final_native_goal"]
                                     and result["placement_xy_error_m"] <= .035
                                     and result["rest_movement_m"] <= .005
                                     and result["rest_sim_s"] >= .5-1e-9)
        result["interrupted_journey_passed"] = (result["physical_passed"]
                                                and result.get("hold_passed", False))
        np.savez(directory/"terminal-observation.npz", **{k: obs[k] for k in fields})
        np.savez(directory/"replayed-states.npz", before=np.asarray(replay_states))
        Image.fromarray(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])).save(
            directory/"terminal.png")
    except Exception as error:
        result["error"] = repr(error)
    finally:
        env.close()
    for filename, content in (("actions.json", records), ("samples.json", samples),
                              ("hold.json", held), ("checks.json", checks),
                              ("result.json", result)):
        (directory/filename).write_text(json.dumps(content, indent=2)+"\n")
    report["episodes"].append(result)
    (args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(result), flush=True)
