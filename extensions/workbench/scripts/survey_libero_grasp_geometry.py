"""Read native robot/object calibration on a new training state; no policy or motion changes."""

import argparse
import itertools
import json
import os
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", type=Path)
parser.add_argument("--openpi", type=Path, required=True)
parser.add_argument("--config-dir", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
source = args.openpi.resolve()
os.environ["LIBERO_CONFIG_PATH"] = str(args.config_dir.resolve())
os.environ["MUJOCO_GL"] = "egl"
for path in (source, source/"third_party/libero", source/"packages/openpi-client/src"):
    sys.path.insert(0, str(path))
import numpy as np  # noqa: E402
from examples.libero.main import LIBERO_DUMMY_ACTION, _get_libero_env  # noqa: E402
from libero.libero import benchmark  # noqa: E402

suite = benchmark.get_benchmark_dict()["libero_spatial"]()
env, prompt = _get_libero_env(suite.get_task(0), 256, 7)
try:
    env.reset()
    env.set_init_state(suite.get_task_init_states(0)[1])
    for _ in range(10):
        env.step(LIBERO_DUMMY_ACTION)
    native, robot = env.env, env.env.robots[0]
    controller = robot.controller
    controller.update(force=True)
    pad_ids = [native.sim.model.geom_name2id(robot.gripper.important_geoms[s+"_fingerpad"][0])
               for s in ("left", "right")]
    pads = native.sim.data.geom_xpos[pad_ids].copy()
    eef = controller.ee_pos.copy()
    rotation = controller.ee_ori_mat.copy()
    obj = native.objects_dict["akita_black_bowl_1"]
    vertices = []
    for name in obj.contact_geoms:
        geom = native.sim.model.geom_name2id(name)
        kind = int(native.sim.model.geom_type[geom])
        if kind == 6:  # MuJoCo box: metric half sizes, not a mesh reference.
            points = np.array(list(itertools.product((-1, 1), repeat=3)))*(
                native.sim.model.geom_size[geom])
        elif kind == 7:
            mesh = native.sim.model.geom_dataid[geom]
            assert mesh >= 0
            begin, count = native.sim.model.mesh_vertadr[mesh], native.sim.model.mesh_vertnum[mesh]
            points = native.sim.model.mesh_vert[begin:begin+count]
        else:
            raise ValueError(f"Unsupported native collision geometry type: {kind}")
        orient = native.sim.data.geom_xmat[geom].reshape(3, 3)
        vertices.extend(points @ orient.T+native.sim.data.geom_xpos[geom])
    vertices = np.array(vertices)
    report = {"task_id": 0, "initial_state_index": 1, "prompt": prompt,
              "eef_xyz": eef.tolist(), "eef_rotation": rotation.tolist(),
              "pad_centers_world": pads.tolist(),
              "pad_centers_eef": ((pads-eef) @ rotation).tolist(),
              "pad_half_sizes": native.sim.model.geom_size[pad_ids].tolist(),
              "bowl_body_xyz": native.sim.data.body_xpos[
                  native.obj_body_id["akita_black_bowl_1"]].tolist(),
              "bowl_collision_min": vertices.min(axis=0).tolist(),
              "bowl_collision_max": vertices.max(axis=0).tolist(),
              "objects": list(native.objects_dict),
              "native_action_input_limits": [controller.input_min.tolist(),
                                             controller.input_max.tolist()],
              "native_action_output_limits": [controller.output_min.tolist(),
                                              controller.output_max.tolist()],
              "scope": "Training-only calibration; privileged geometry, not actor observation"}
    np.savez(args.output/"collision_vertices.npz", vertices=vertices)
    (args.output/"report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report))
finally:
    env.close()
