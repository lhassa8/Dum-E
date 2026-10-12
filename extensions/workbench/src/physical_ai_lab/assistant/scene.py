"""Native Panda simulation. Blocks move only through contacts and gravity."""

import xml.etree.ElementTree as ET
from pathlib import Path

import mujoco
import numpy as np

from physical_ai_lab.assistant.entities import COLORS, OBJECTS, TARGETS

ASSETS = Path(__file__).parent / "assets" / "panda"
HOME = np.array([0, 0, 0, -1.57079, 0, 1.57079, -0.7853])


def scene_xml():
    root = ET.parse(ASSETS / "panda.xml").getroot()
    root.find("compiler").set("meshdir", str(ASSETS / "assets"))
    root.find("option").set("timestep", "0.002")
    # Keep the vendor model intact; scene adaptations are applied in memory.
    root.remove(root.find("keyframe"))
    ET.SubElement(root, "visual").append(ET.Element("global", offwidth="960", offheight="720"))
    world = root.find("worldbody")
    ET.SubElement(
        world,
        "geom",
        name="workbench",
        type="box",
        pos="0.4 0 -0.035",
        size="0.65 0.48 0.035",
        rgba="0.17 0.20 0.25 1",
        friction="1 0.01 0.001",
    )
    ET.SubElement(
        world,
        "camera",
        name="overview",
        pos="1.45 -1.5 1.35",
        xyaxes="0.819 0.573 0 -0.321 0.458 0.829",
    )
    for name, (x, y) in OBJECTS.items():
        body = ET.SubElement(world, "body", name=name, pos=f"{x} {y} 0.023")
        ET.SubElement(body, "freejoint", name=f"{name}_joint")
        ET.SubElement(
            body,
            "geom",
            name=f"{name}_block",
            type="box",
            size="0.022 0.022 0.022",
            mass="0.055",
            rgba=COLORS[name],
            friction="1.2 0.01 0.001",
            condim="4",
        )
    for name, (x, y) in TARGETS.items():
        ET.SubElement(
            world,
            "geom",
            name=f"{name}_target",
            type="cylinder",
            pos=f"{x} {y} 0.0005",
            size="0.06 0.0005",
            rgba=COLORS[name],
            contype="0",
            conaffinity="0",
        )
    ET.SubElement(
        root.find(".//body[@name='hand']"), "site", name="tcp", pos="0 0 0.103", size="0.003"
    )
    return ET.tostring(root, encoding="unicode")


class Workbench:
    def __init__(self, seed=42, xml=None, objects=None, targets=None):
        self.objects = OBJECTS if objects is None else objects
        self.targets = TARGETS if targets is None else targets
        self.model = mujoco.MjModel.from_xml_string(scene_xml() if xml is None else xml)
        self.data = mujoco.MjData(self.model)
        self.ik_data = mujoco.MjData(self.model)
        self.hold_data = mujoco.MjData(self.model)
        self.tcp = self.model.site("tcp").id
        self.renderer = None
        self.reset(seed)

    def reset(self, seed=42):
        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:7] = HOME
        self.data.qpos[7:9] = 0.04
        self.data.ctrl[:] = np.r_[HOME, 255]
        rng = np.random.default_rng(seed)
        for name in self.objects:
            address = self.model.joint(f"{name}_joint").qposadr[0]
            self.data.qpos[address : address + 2] += rng.uniform(-0.008, 0.008, 2)
        mujoco.mj_forward(self.model, self.data)
        self.orientation = self.data.site_xmat[self.tcp].reshape(3, 3).copy()
        for _ in range(200):
            mujoco.mj_step(self.model, self.data)

    def observe(self):
        return {name: self.data.xpos[self.model.body(name).id].copy() for name in self.objects}

    def solve(self, position):
        data = self.ik_data
        data.qpos[:] = self.data.qpos
        desired = np.asarray(position)
        jp, jr = np.zeros((3, self.model.nv)), np.zeros((3, self.model.nv))
        for _ in range(120):
            mujoco.mj_forward(self.model, data)
            actual_rotation = data.site_xmat[self.tcp].reshape(3, 3)
            rotation_error = 0.5 * sum(
                np.cross(actual_rotation[:, i], self.orientation[:, i]) for i in range(3)
            )
            error = np.r_[desired - data.site_xpos[self.tcp], rotation_error]
            if np.linalg.norm(error[:3]) < 0.0008 and np.linalg.norm(error[3:]) < 0.008:
                return data.qpos[:7].copy()
            mujoco.mj_jacSite(self.model, data, jp, jr, self.tcp)
            jac = np.vstack([jp[:, :7], jr[:, :7]])
            delta = jac.T @ np.linalg.solve(jac @ jac.T + 0.002 * np.eye(6), error)
            data.qpos[:7] += np.clip(delta, -0.12, 0.12)
            data.qpos[:7] = np.clip(
                data.qpos[:7],
                self.model.jnt_range[:7, 0] + 0.005,
                self.model.jnt_range[:7, 1] - 0.005,
            )
        raise ValueError("I cannot reach that position with this arm.")

    def tick(self, joints=None, gripper=None):
        if joints is not None:
            self.data.ctrl[:7] = joints
        if gripper is not None:
            self.data.ctrl[7] = gripper
        for _ in range(16):
            mujoco.mj_step(self.model, self.data)
        if not np.isfinite(self.data.qpos).all():
            raise FloatingPointError("Simulation became unstable")

    def hold_joints(self):
        """Hold the measured arm pose with static gravity feedforward.

        A plain position servo sags if its target is the measured pose: it must
        develop a position error before producing the gravity-balancing torque.
        Adjust only arm servo targets; never set object poses, velocities or grip.
        """
        data = self.hold_data
        data.qpos[:] = self.data.qpos
        data.qvel[:] = 0
        mujoco.mj_forward(self.model, data)
        gravity = data.qfrc_bias[:7] - data.qfrc_passive[:7]
        target = self.data.qpos[:7] + gravity / self.model.actuator_gainprm[:7, 0]
        self.data.ctrl[:7] = np.clip(
            target, self.model.actuator_ctrlrange[:7, 0], self.model.actuator_ctrlrange[:7, 1]
        )

    def render(self, camera="overview"):
        if self.renderer is None:
            self.renderer = mujoco.Renderer(self.model, height=720, width=960)
        self.renderer.update_scene(self.data, camera=camera)
        return self.renderer.render().copy()

    def close(self):
        if self.renderer is not None:
            self.renderer.close()
