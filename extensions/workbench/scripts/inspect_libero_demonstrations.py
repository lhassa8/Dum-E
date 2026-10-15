"""Read verified demonstration structure and object-layout identity; never apply actions."""

import argparse
import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("preparation", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
args = parser.parse_args()
manifest = json.loads((args.preparation/"preparation.json").read_text())
assert manifest["verified"]
args.output.mkdir(parents=True, exist_ok=False)
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
source = args.openpi.resolve()
for path in (source, source/"third_party/libero", source/"packages/openpi-client/src"):
    sys.path.insert(0, str(path))
import h5py  # noqa: E402
import numpy as np  # noqa: E402
from examples.libero.main import _get_libero_env  # noqa: E402
from libero.libero import benchmark  # noqa: E402

suite = benchmark.get_benchmark_dict()["libero_spatial"]()
report = {"scope": "Read-only identity inspection, no demonstration actions or model training",
          "revision": manifest["revision"], "tasks": [],
          "near_duplicate_exclusion": {"all_free_objects_xy_m": .01,
                                       "all_free_objects_rotation_rad": .05}}
for task_id in (0, 1, 2):
    task = suite.get_task(task_id)
    name = f"libero_spatial/{task.name}_demo.hdf5"
    spec = next(f for f in manifest["files"] if f["name"] == name)
    path = args.preparation/name
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            digest.update(block)
    assert digest.hexdigest() == spec["sha256"] and path.stat().st_size == spec["bytes"]
    initial_states = np.asarray(suite.get_task_init_states(task_id))
    env, _ = _get_libero_env(task, 256, 7)
    try:
        env.reset()
        native = env.env
        model = native.sim.model
        qpos_indices, quaternion_slices, free_indices = [], [], []
        for obj in native.objects_dict.values():
            for name in obj.joints or []:
                joint = model.joint_name2id(name)
                begin = int(model.jnt_qposadr[joint])
                kind = int(model.jnt_type[joint])
                width = 7 if kind == 0 else 4 if kind == 1 else 1
                offset = len(qpos_indices)
                qpos_indices.extend(range(begin+1, begin+width+1))
                if kind in (0, 1):
                    quaternion_slices.append(slice(offset+(3 if kind == 0 else 0), offset+width))
                if kind == 0:
                    free_indices.append(list(range(begin+1, begin+8)))

        def layouts(states):
            result = states[:, qpos_indices].copy()
            for rotation in quaternion_slices:
                result[:, rotation] *= np.where(result[:, rotation.start] < 0, -1, 1)[:, None]
            return result

        free_indices = np.asarray(free_indices, dtype=int)
        initial_layouts = layouts(initial_states)
        episodes = []
        with h5py.File(path, "r") as data:
            root = data["data"]
            for key in sorted(root, key=lambda s: int(s.split("_")[-1])):
                demo = root[key]
                xml = ET.fromstring(demo.attrs["model_file"])
                joints = [node.attrib["name"] for node in xml.findall(".//worldbody//joint")]
                assert joints == list(model.joint_names), "Joint topology differs"
                state = demo["states"][0]
                assert state.shape == initial_states.shape[1:]
                distance = np.abs(initial_layouts-layouts(state[None, :])).max(axis=1)
                matches = np.flatnonzero(distance < 1e-6).tolist()
                free = initial_states[:, free_indices]
                demo_free = state[free_indices]
                # Z can differ before gravity settling; do not count that as a
                # new tabletop layout when excluding reserved-scene overlap.
                position_error = np.linalg.norm(free[:, :, :2]-demo_free[:, :2], axis=2).max(1)
                qa = free[:, :, 3:]/np.linalg.norm(free[:, :, 3:], axis=2, keepdims=True)
                qb = demo_free[:, 3:]/np.linalg.norm(demo_free[:, 3:], axis=1, keepdims=True)
                angular_error = (2*np.arccos(np.clip(np.abs((qa*qb).sum(2)), 0, 1))).max(1)
                near = np.flatnonzero((position_error <= .01) & (angular_error <= .05)).tolist()
                closest = int(np.maximum(position_error/.01, angular_error/.05).argmin())
                actions = demo["actions"][:]
                assert actions.shape[1:] == (7,) and np.isfinite(actions).all()
                episodes.append({"demo": key, "steps": len(actions),
                                 "action_min": actions.min(axis=0).tolist(),
                                 "action_max": actions.max(axis=0).tolist(),
                                 "state_shape": list(demo["states"].shape),
                                 "observation_shapes": {k: list(v.shape)
                                                        for k, v in demo["obs"].items()},
                                 "matching_initial_object_layout_indices": matches,
                                 "closest_initial_object_layout_index": int(distance.argmin()),
                                 "closest_object_qpos_max_error": float(distance.min()),
                                 "near_duplicate_initial_layout_indices": near,
                                 "closest_free_object_layout_index": closest,
                                 "closest_free_xy_error_m": float(position_error[closest]),
                                 "closest_free_rotation_error_rad": float(angular_error[closest]),
                                 "excluded_state_overlap": bool(set(near) & {0, 5, 6, 7, 8})})
            entry = {"task_id": task_id, "file": path.name, "episodes": episodes,
                     "object_qpos_dimensions": len(qpos_indices),
                     "initial_state_count": len(initial_states),
                     "image_convention": str(root.attrs.get("macros_image_convention")),
                     "environment_arguments": json.loads(root.attrs["env_args"])}
        report["tasks"].append(entry)
        (args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
        print(json.dumps({"task": task_id, "episodes": len(episodes),
                          "overlap_excluded": sum(e["excluded_state_overlap"] for e in episodes),
                          "any_exact_layout_match": sum(bool(e[
                              "matching_initial_object_layout_indices"]) for e in episodes)}),
              flush=True)
    finally:
        env.close()
