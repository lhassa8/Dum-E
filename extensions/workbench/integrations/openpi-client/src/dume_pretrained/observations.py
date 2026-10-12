"""LIBERO observation adaptation following the pinned upstream evaluation example."""

import numpy as np
from openpi_client import image_tools


def libero_observation(raw, prompt):
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("A task instruction is required")
    images = []
    for key in ["agentview_image", "robot0_eye_in_hand_image"]:
        image = np.asarray(raw[key])
        if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
            raise ValueError("LIBERO cameras must supply uint8 RGB images")
        flipped = np.ascontiguousarray(image[::-1, ::-1])
        images.append(image_tools.convert_to_uint8(image_tools.resize_with_pad(flipped, 224, 224)))
    position = np.asarray(raw["robot0_eef_pos"], float)
    quaternion = np.asarray(raw["robot0_eef_quat"], float)
    gripper = np.asarray(raw["robot0_gripper_qpos"], float)
    if (
        position.shape != (3,)
        or quaternion.shape != (4,)
        or gripper.shape != (2,)
        or not all(np.isfinite(x).all() for x in [position, quaternion, gripper])
        or abs(np.linalg.norm(quaternion) - 1) > 0.001
    ):
        raise ValueError("LIBERO pose/gripper measurements are invalid")
    w = np.clip(quaternion[3], -1, 1)
    denominator = np.sqrt(1 - w * w)
    axis_angle = (
        np.zeros(3) if denominator < 1e-8 else quaternion[:3] * 2 * np.arccos(w) / denominator
    )
    return {
        "observation/image": images[0],
        "observation/wrist_image": images[1],
        "observation/state": np.r_[position, axis_angle, gripper],
        "prompt": prompt,
    }
