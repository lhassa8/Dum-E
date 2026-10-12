"""Inventory current simulation geometry without rendering, stepping or hardware IO."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import mujoco
import numpy as np

from physical_ai_lab.assistant.tool_geometry import parts
from physical_ai_lab.assistant.tool_scene import HANDOFF, TOOLS, tool_scene_xml

LAB = Path(__file__).resolve().parents[1]


def inventory():
    model = mujoco.MjModel.from_xml_string(tool_scene_xml())
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    records = []
    for name, xy in TOOLS.items():
        lower, upper = np.full(3, np.inf), np.full(3, -np.inf)
        boxes, capsules = parts(name)
        for center, half in boxes:
            center, half = np.asarray(center), np.asarray(half)
            lower, upper = np.minimum(lower, center - half), np.maximum(upper, center + half)
        for center, half, radius in capsules:
            center, extent = np.asarray(center), np.array([radius, half + radius, radius])
            lower, upper = np.minimum(lower, center - extent), np.maximum(upper, center + extent)
        # Separate verifier: compiled physics geometry rather than the catalog.
        body = model.body(name).id
        physical_lower, physical_upper = np.full(3, np.inf), np.full(3, -np.inf)
        for geom in range(
            model.body_geomadr[body], model.body_geomadr[body] + model.body_geomnum[body]
        ):
            rotation = data.geom_xmat[geom].reshape(3, 3)
            center = data.geom_xpos[geom] - data.xpos[body]
            size = model.geom_size[geom]
            if model.geom_type[geom] == mujoco.mjtGeom.mjGEOM_BOX:
                extent = np.abs(rotation) @ size
            elif model.geom_type[geom] == mujoco.mjtGeom.mjGEOM_CAPSULE:
                extent = size[0] + size[1] * np.abs(rotation[:, 2])
            else:
                raise ValueError("Unsupported geometry in the current tool inventory")
            physical_lower = np.minimum(physical_lower, center - extent)
            physical_upper = np.maximum(physical_upper, center + extent)
        np.testing.assert_allclose(upper - lower, physical_upper - physical_lower, atol=1e-10)
        records.append(
            {
                "tool": name,
                "mass_g": float(model.body_mass[body] * 1000),
                "catalog_axis_aligned_size_mm": ((upper - lower) * 1000).tolist(),
                "compiled_geometry_matches_catalog": True,
                "center_of_mass_from_body_origin_mm": (model.body_ipos[body] * 1000).tolist(),
                "handle_box_size_mm": [44, 56, 44],
                "rack_xy_m": list(xy),
                "rack_xy_distance_from_base_origin_m": float(np.linalg.norm(xy)),
            }
        )
    paths = [
        "src/physical_ai_lab/assistant/tool_scene.py",
        "src/physical_ai_lab/assistant/tool_geometry.py",
        "src/physical_ai_lab/assistant/camera_robot.py",
        "src/physical_ai_lab/assistant/perception_scene.py",
        "scripts/inspect_hardware_requirements.py",
    ]
    return {
        "scope": "Current simulated tool/geometry inventory; no hardware or simulation motion",
        "root_commit": subprocess.check_output(
            ["git", "-C", str(LAB), "rev-parse", "HEAD"], text=True
        ).strip(),
        "mujoco": mujoco.__version__,
        "tools": records,
        "handoff_xy_m": list(HANDOFF["handoff"]),
        "handoff_xy_distance_from_base_origin_m": float(np.linalg.norm(HANDOFF["handoff"])),
        "handoff_mat_size_mm": [170, 250],
        "source_hashes": {p: hashlib.sha256((LAB / p).read_bytes()).hexdigest() for p in paths},
        "real_tool_measurements": False,
        "hardware_ready": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Use a fresh output path")
    report = inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
