"""Training-only calibrated rim targets and native OSC expert actions.

Privileged object geometry is deliberately confined to this demonstration
teacher. It must never be imported by a camera/proprioception learned actor.
"""

import itertools

import numpy as np
from scipy.spatial.transform import Rotation


def collision_vertices(native, names):
    vertices = []
    for name in names:
        geom = native.sim.model.geom_name2id(name)
        kind = int(native.sim.model.geom_type[geom])
        if kind == 6:
            points = np.array(list(itertools.product((-1, 1), repeat=3)))*(
                native.sim.model.geom_size[geom])
        elif kind == 7:
            mesh = native.sim.model.geom_dataid[geom]
            assert mesh >= 0
            begin, count = native.sim.model.mesh_vertadr[mesh], native.sim.model.mesh_vertnum[mesh]
            points = native.sim.model.mesh_vert[begin:begin+count]
        else:
            raise ValueError(f"Unsupported collider type: {kind}")
        orient = native.sim.data.geom_xmat[geom].reshape(3, 3)
        vertices.extend(points @ orient.T+native.sim.data.geom_xpos[geom])
    return np.array(vertices)


def calibrated_rim(native, robot):
    controller = robot.controller
    controller.update(force=True)
    pad_ids = [native.sim.model.geom_name2id(robot.gripper.important_geoms[s+"_fingerpad"][0])
               for s in ("left", "right")]
    pads = native.sim.data.geom_xpos[pad_ids].copy()
    pad_local = (pads-controller.ee_pos) @ controller.ee_ori_mat
    closing = pad_local[0]-pad_local[1]
    index = int(np.argmax(np.abs(closing)))
    assert index in (0, 1) and abs(closing[2]) < 1e-6
    target = native.objects_dict["akita_black_bowl_1"].contact_geoms
    vertices = collision_vertices(native, target)
    center = (vertices.min(axis=0)+vertices.max(axis=0))/2
    radial = controller.ee_pos[:2]-center[:2]
    radial /= np.linalg.norm(radial)
    half_pad = float(native.sim.model.geom_size[pad_ids[0], 2])
    top = vertices[:, 2].max()
    band = vertices[vertices[:, 2] >= top-half_pad]
    relative = band[:, :2]-center[:2]
    aligned = relative @ radial/np.linalg.norm(relative, axis=1)
    patch = band[aligned >= np.cos(np.deg2rad(20))]
    assert len(patch) >= 2
    radii = (patch[:, :2]-center[:2]) @ radial
    pad_target = np.r_[center[:2]+radial*(radii.min()+radii.max())/2,
                       patch[:, 2].max()-half_pad]
    depth = np.array([0., 0., -1.])
    axis = np.r_[radial, 0.]*np.sign(closing[index])
    desired = np.zeros((3, 3))
    desired[:, index], desired[:, 2] = axis, depth
    desired[:, 1-index] = np.cross(depth, axis) if index == 0 else np.cross(axis, depth)
    assert np.allclose(desired.T @ desired, np.eye(3)) and np.linalg.det(desired) > .999
    eef_target = pad_target-desired @ pad_local.mean(axis=0)
    return eef_target, desired, {"pad_target": pad_target.tolist(),
                                 "eef_target": eef_target.tolist(),
                                 "desired_rotation": desired.tolist(),
                                 "pad_local": pad_local.tolist(),
                                 "rim_top_m": float(patch[:, 2].max()),
                                 "scope": "Privileged training teacher calibration only"}


def native_servo(controller, xyz, rotation, grip, *, max_translation_m,
                 max_rotation_rad=.1):
    controller.update(force=True)
    error = xyz-controller.ee_pos
    length = np.linalg.norm(error)
    delta = error*min(1., max_translation_m/max(length, 1e-12))
    angular = Rotation.from_matrix(rotation @ controller.ee_ori_mat.T).as_rotvec()
    angular *= min(1., max_rotation_rad/max(np.linalg.norm(angular), 1e-12))
    action = np.r_[delta/.05, angular/.5, grip]
    assert action.shape == (7,) and np.isfinite(action).all() and np.max(np.abs(action)) <= 1+1e-9
    return action, float(length), float(np.linalg.norm(
        Rotation.from_matrix(rotation @ controller.ee_ori_mat.T).as_rotvec()))
