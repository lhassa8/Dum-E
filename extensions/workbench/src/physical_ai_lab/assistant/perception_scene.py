"""Offline sensor/annotation adapter; simulator truth stays outside the detector."""

import xml.etree.ElementTree as ET

import mujoco
import numpy as np

from physical_ai_lab.assistant.perception import CameraCalibration, CameraSample, RGBDFrame
from physical_ai_lab.assistant.scene import Workbench
from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS, tool_scene_xml


def add_camera(world, name, position):
    position = np.asarray(position, float)
    z = position - np.array([0.46, 0, 0.03])
    z /= np.linalg.norm(z)
    x = np.cross([0, 0, 1], z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    ET.SubElement(
        world,
        "camera",
        name=name,
        pos=" ".join(map(str, position)),
        xyaxes=" ".join(map(str, np.r_[x, y])),
        fovy="40",
        ipd="0",
    )


def camera_scene_xml(case, alternate_view=False):
    root = ET.fromstring(tool_scene_xml())
    world = root.find("worldbody")
    add_camera(world, "workbench_camera", [1.05, 0, 0.9])
    # Optional recovery viewpoint; optics only, no collision/physics change.
    if alternate_view:
        add_camera(world, "workbench_camera_side", [1.05, -0.38, 0.95])
    for name, pose in case["layout"].items():
        body = world.find(f"body[@name='{name}']")
        body.set("pos", f"{pose[0]} {pose[1]} 0.026")
        body.set("quat", f"{np.cos(pose[2] / 2)} 0 0 {np.sin(pose[2] / 2)}")
    if case.get("occluded"):
        name = case["occluded"]
        px, py, _ = case["layout"][name]
        ET.SubElement(
            world,
            "geom",
            name="visual_occluder",
            type="box",
            pos=f"{px} {py} 0.16",
            size="0.095 0.095 0.02",
            rgba="0.16 0.11 0.19 1",
            contype="0",
            conaffinity="0",
        )
    return ET.tostring(root, encoding="unicode")


class CameraSensor:
    """Rendered sensor port; only pixels, calibration and capture time leave it."""

    def __init__(self, bench, width=640, height=480):
        self.bench = bench
        self.renderer = mujoco.Renderer(self.bench.model, height=height, width=width)
        self.width, self.height = width, height
        self.camera_id = self.bench.model.camera("workbench_camera").id
        self.calibration = CameraCalibration(
            width,
            height,
            float(self.bench.model.cam_fovy[self.camera_id]),
            self.bench.data.cam_xpos[self.camera_id].copy(),
            self.bench.data.cam_xmat[self.camera_id].reshape(3, 3).copy(),
        )

    def capture(self):
        return self.capture_view("workbench_camera")

    def capture_view(self, view):
        camera_id = self.bench.model.camera(view).id
        calibration = CameraCalibration(
            self.width,
            self.height,
            float(self.bench.model.cam_fovy[camera_id]),
            self.bench.data.cam_xpos[camera_id].copy(),
            self.bench.data.cam_xmat[camera_id].reshape(3, 3).copy(),
        )
        self.renderer.disable_segmentation_rendering()
        self.renderer.disable_depth_rendering()
        self.renderer.update_scene(self.bench.data, camera=view)
        rgb = self.renderer.render().copy()
        self.renderer.enable_depth_rendering()
        depth = self.renderer.render().copy()
        self.renderer.disable_depth_rendering()
        return RGBDFrame(rgb, depth, calibration)

    def capture_alternate_timed(self):
        captured_s = float(self.bench.data.time)
        return CameraSample(self.capture_view("workbench_camera_side"), captured_s)

    def capture_timed(self):
        captured_s = float(self.bench.data.time)
        return CameraSample(self.capture(), captured_s)

    def close(self):
        self.renderer.close()


class CameraDatasetScene(CameraSensor):
    def __init__(self, case, width=640, height=480):
        bench = Workbench(
            seed=case["seed"], xml=camera_scene_xml(case), objects=TOOLS, targets=HANDOFF
        )
        bench.model.vis.headlight.diffuse[:] *= case.get("light", 1)
        super().__init__(bench, width, height)

    def annotations(self):
        """Privileged evaluation labels, never part of RGBDFrame."""
        self.renderer.enable_segmentation_rendering()
        ids = self.renderer.render()[:, :, 0]
        self.renderer.disable_segmentation_rendering()
        labels = {}
        for name, xyz in self.bench.observe().items():
            body = self.bench.model.body(name).id
            handle = self.bench.model.body_geomadr[body]
            labels[name] = {
                "position_m": xyz.tolist(),
                "visible_handle_pixels": int((ids == handle).sum()),
            }
        return labels

    def close(self):
        super().close()
        self.bench.close()
