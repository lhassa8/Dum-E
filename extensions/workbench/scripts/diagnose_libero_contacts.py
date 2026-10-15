"""Replay an unpaused recorded LIBERO episode and inspect native contact geometry.

Evaluator-only diagnostic: no new policy inference, motion authority, or change
to the existing grasp qualification. Refuses paused traces and mismatched replay.
"""

import argparse
import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
inputs = parser.add_mutually_exclusive_group(required=True)
inputs.add_argument("--physics", type=Path)
inputs.add_argument("--teacher", type=Path, help="Unpaused failed teacher episode directory")
parser.add_argument("--epoch", type=int, default=1)
parser.add_argument("--task-id", type=int, choices=(0, 1, 2), required=True)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
args = parser.parse_args()
rows = []
initial_state_index = 0
if args.teacher:
    result = json.loads((args.teacher/"result.json").read_text())
    assert result["task_id"] == args.task_id and result["error"] is not None
    assert not json.loads((args.teacher/"hold.json").read_text()), "Paused replay not supported"
    initial_state_index = result["initial_state_index"]
    source_path = args.teacher/"actions.json"
    for original_row in json.loads(source_path.read_text()):
        judge = {**original_row["judge"], "initial_xyz": result["initial_body_xyz"],
                 "success": original_row["judge"]["native_goal"]}
        rows.append({**original_row, "active_steps": original_row["index"]+1, "judge": judge})
else:
    source_path = args.physics
    with source_path.open() as stream:
        for line in stream:
            row = json.loads(line)
            if row["epoch"] == args.epoch and row["task_id"] == args.task_id:
                if row["source"] not in ("policy", "osc_hold"):
                    raise ValueError("This diagnostic only replays unpaused episodes")
                rows.append(row)
                if row["phase"] == "success":
                    break
    assert rows and rows[-1]["phase"] == "success", "Complete successful source required"
assert rows
assert [r["active_steps"] for r in rows] == list(range(1, len(rows) + 1))
args.output.mkdir(parents=True, exist_ok=False)
source = args.openpi.resolve()
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
sys.path.insert(0, str(source / "third_party/libero"))
sys.path.insert(0, str(source / "packages/openpi-client/src"))
sys.path.insert(0, str(source))

import numpy as np  # noqa: E402
from examples.libero.main import LIBERO_DUMMY_ACTION, _get_libero_env  # noqa: E402
from libero.libero import benchmark  # noqa: E402
from PIL import Image  # noqa: E402

protocol = {
    "scope": "Exact applied-action replay, evaluator-only contacts; no fresh policy inference",
    "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
    "source_kind": "Failed geometric teacher" if args.teacher else "Recorded policy",
    "actor_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "epoch": args.epoch,
    "task_id": args.task_id,
    "seed": 7,
    "initial_state_index": initial_state_index,
    "steps": len(rows),
    "min_lift_m": 0.08,
    "max_replay_position_error_m": 1e-6,
    "max_replay_joint_error_rad": 1e-6,
    "sample_rate": "Every native torque callback plus completed env.step",
}
(args.output / "protocol.json").write_text(json.dumps(protocol, indent=2))
suite = benchmark.get_benchmark_dict()["libero_spatial"]()
env, prompt = _get_libero_env(suite.get_task(args.task_id), 256, 7)
samples, checks = [], []
try:
    env.env.ignore_done = True
    env.reset()
    env.set_init_state(suite.get_task_init_states(args.task_id)[initial_state_index])
    for _ in range(10):
        env.step(LIBERO_DUMMY_ACTION)
    native = env.env
    robot = native.robots[0]
    assert robot.controller.name == "OSC_POSE"
    name = "akita_black_bowl_1"
    body = native.obj_body_id[name]
    initial = native.sim.data.body_xpos[body].copy()
    assert np.max(np.abs(initial - rows[0]["judge"]["initial_xyz"])) < 1e-9
    target = native.objects_dict[name].contact_geoms
    target_ids = {native.sim.model.geom_name2id(g) for g in target}
    groups = {
        side: robot.gripper.important_geoms[side + "_fingerpad"]
        for side in ("left", "right")
    }

    def sample(origin):
        contacts = []
        for contact in native.sim.data.contact[: native.sim.data.ncon]:
            a, b = int(contact.geom1), int(contact.geom2)
            if a in target_ids or b in target_ids:
                other = b if a in target_ids else a
                contacts.append({
                    "target_geom": native.sim.model.geom_id2name(a if a in target_ids else b),
                    "other_geom": native.sim.model.geom_id2name(other),
                    "distance_m": float(contact.dist),
                })
        result = {
            "origin": origin,
            "sim_time": float(native.sim.data.time),
            "lift_m": float(native.sim.data.body_xpos[body][2] - initial[2]),
            "grasp_contacts": bool(native._check_grasp(robot.gripper, target)),
            "finger_contacts": {
                side: bool(native.check_contact(geoms, target))
                for side, geoms in groups.items()
            },
            "contacts": contacts,
        }
        samples.append(result)
        return result

    original = robot.controller.run_controller

    def observe_controller():
        sample("torque_callback")
        return original()

    robot.controller.run_controller = observe_controller
    peak = -float("inf")
    for row in rows:
        if args.teacher:
            # The teacher refreshed its native OSC cache before each command.
            # Replay that boundary as well as its exact recorded action vector.
            robot.controller.update(force=True)
        obs, _, _, _ = env.step(row["action"])
        measured = sample("step_end")
        judge = row["judge"]
        checks.append({
            "active_step": row["active_steps"],
            "position_error_m": float(np.max(np.abs(
                native.sim.data.body_xpos[body] - judge["xyz"]
            ))),
            "joint_error_rad": float(np.max(np.abs(
                robot._joint_positions - judge["joints"]
            ))),
            "contact_matches": measured["grasp_contacts"] == judge["grasp_contacts"],
            "success_matches": bool(native._check_success()) == judge["success"],
            "time_error_s": abs(measured["sim_time"] - judge["sim_time"]),
        })
        if measured["lift_m"] > peak:
            peak = measured["lift_m"]
            Image.fromarray(np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])).save(
                args.output / "peak-lift.png"
            )
    lifted = [s for s in samples if s["lift_m"] >= protocol["min_lift_m"]]
    report = {
        "protocol": protocol,
        "prompt": prompt,
        "finger_groups": groups,
        "target_geoms": target,
        "native_predicate_sha256": hashlib.sha256(
            inspect.getsource(native._check_grasp).encode()
        ).hexdigest(),
        "samples": len(samples),
        "lifted_samples": len(lifted),
        "bilateral_lifted_samples": sum(s["grasp_contacts"] for s in lifted),
        "finger_lifted_samples": {
            side: sum(s["finger_contacts"][side] for s in lifted) for side in groups
        },
        "other_geoms_when_lifted": sorted({
            c["other_geom"] for s in lifted for c in s["contacts"]
        }),
        "max_lift_m": max(s["lift_m"] for s in samples),
        "max_bilateral_lift_m": max(
            (s["lift_m"] for s in samples if s["grasp_contacts"]), default=None
        ),
        "max_position_error_m": max(c["position_error_m"] for c in checks),
        "max_joint_error_rad": max(c["joint_error_rad"] for c in checks),
        "all_contact_checks_match": all(c["contact_matches"] for c in checks),
        "all_success_checks_match": all(c["success_matches"] for c in checks),
        "max_time_error_s": max(c["time_error_s"] for c in checks),
        "native_success": bool(native._check_success()),
    }
    report["replay_matches"] = (
        report["max_position_error_m"] <= protocol["max_replay_position_error_m"]
        and report["max_joint_error_rad"] <= protocol["max_replay_joint_error_rad"]
        and report["all_contact_checks_match"] and report["all_success_checks_match"]
        and report["max_time_error_s"] < 1e-9
    )
    for filename, data in (("samples.json", samples), ("checks.json", checks),
                           ("report.json", report)):
        (args.output / filename).write_text(json.dumps(data, indent=2))
    print(json.dumps(report, indent=2))
    assert report["replay_matches"], "Replay diverged: contact diagnosis is not qualified"
finally:
    env.close()
