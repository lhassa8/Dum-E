"""Camera-only localization baseline for the current primitive tool handles.

No simulator imports or state inputs: pixels, axial depth and camera calibration
are the complete observation contract. Known handle dimensions are a catalog
assumption, not learned object recognition. Fit scores are not probabilities.
"""

from dataclasses import dataclass

import numpy as np

TOOLS = ("screwdriver", "wrench", "hammer")


@dataclass(frozen=True)
class CameraCalibration:
    width: int
    height: int
    fovy_degrees: float
    position_m: np.ndarray
    rotation: np.ndarray  # Camera axes -> world axes; camera looks along -Z.

    def __post_init__(self):
        if self.width < 2 or self.height < 2 or not 0 < self.fovy_degrees < 180:
            raise ValueError("Invalid image size or field of view")
        if np.shape(self.position_m) != (3,) or np.shape(self.rotation) != (3, 3):
            raise ValueError("Invalid camera extrinsics")
        if not np.isfinite(self.position_m).all() or not np.isfinite(self.rotation).all():
            raise ValueError("Camera calibration must be finite")
        if not np.allclose(self.rotation.T @ self.rotation, np.eye(3), atol=1e-6):
            raise ValueError("Camera rotation must be orthonormal")
        if not np.isclose(np.linalg.det(self.rotation), 1, atol=1e-6):
            raise ValueError("Camera rotation must be right handed")

    @property
    def focal_pixels(self):
        return self.height / (2 * np.tan(np.deg2rad(self.fovy_degrees) / 2))

    def unproject(self, u, v, depth_m):
        """Integer u/v index pixel centers; depth is optical-axis distance."""
        d = np.asarray(depth_m)
        points = np.stack(
            [
                (np.asarray(u) - (self.width - 1) / 2) * d / self.focal_pixels,
                -(np.asarray(v) - (self.height - 1) / 2) * d / self.focal_pixels,
                -d,
            ],
            axis=-1,
        )
        return points @ self.rotation.T + self.position_m

    def project(self, world_points):
        local = (np.asarray(world_points) - self.position_m) @ self.rotation
        depth = -local[..., 2]
        return np.stack(
            [
                local[..., 0] * self.focal_pixels / depth + (self.width - 1) / 2,
                -local[..., 1] * self.focal_pixels / depth + (self.height - 1) / 2,
            ],
            axis=-1,
        )


@dataclass(frozen=True)
class RGBDFrame:
    rgb: np.ndarray
    depth_m: np.ndarray
    camera: CameraCalibration

    def __post_init__(self):
        shape = (self.camera.height, self.camera.width)
        if self.rgb.shape != (*shape, 3) or self.rgb.dtype != np.uint8:
            raise ValueError("RGB frame must match calibrated uint8 HxWx3")
        if self.depth_m.shape != shape:
            raise ValueError("Depth frame must match calibrated HxW")
        if not np.issubdtype(self.depth_m.dtype, np.floating):
            raise ValueError("Depth must contain floating point meters")


@dataclass(frozen=True)
class CameraSample:
    frame: RGBDFrame
    captured_s: float  # Same clock as the robot port; simulation time in MuJoCo.


def components(mask):
    """Four-connected pixel islands without adding a vision dependency."""
    seen = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    for y, x in np.argwhere(mask):
        if seen[y, x]:
            continue
        stack, island = [(int(y), int(x))], []
        seen[y, x] = True
        while stack:
            row, col = stack.pop()
            island.append((row, col))
            for nr, nc in [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]:
                if 0 <= nr < height and 0 <= nc < width and mask[nr, nc] and not seen[nr, nc]:
                    seen[nr, nc] = True
                    stack.append((nr, nc))
        if len(island) >= 40:
            yield np.asarray(island)


def _locate_tools(frame, shadow_recovery=False, names=None, tilted_face=False):
    """Find complete 44x56mm top faces by appearance and measured depth.

    Supports tabletop tools with roughly horizontal primitive handles. Refuses
    missing/ambiguous matches; never fills a miss with a rack-slot position.
    """
    v, u = np.indices(frame.depth_m.shape)
    cloud = frame.camera.unproject(u, v, frame.depth_m)
    valid = (
        np.isfinite(cloud).all(axis=-1)
        & (frame.depth_m > 0)
        & (cloud[..., 0] > 0.26)
        & (cloud[..., 0] < 0.82)
        & (np.abs(cloud[..., 1]) < 0.40)
        & (cloud[..., 2] > 0.008)
        & (cloud[..., 2] < 0.12)
    )
    rgb = frame.rgb.astype(float) / 255
    total = rgb.sum(axis=-1)
    normalized = rgb / np.maximum(total[..., None], 1e-9)
    r, g, b = np.moveaxis(normalized, -1, 0)
    chroma = rgb.max(axis=-1) - rgb.min(axis=-1)
    # Neutral material remains neutral in an arm shadow. Absolute brightness
    # wrongly loses a visible metal handle during pre-grasp reobservation.
    # Depth/tabletop geometry still gates candidates; truly dark/noisy pixels
    # are withheld and colored handles stay outside this normalized hue range.
    brightness = rgb.mean(axis=-1)
    neutral = (chroma < 0.16) & (brightness > 0.28)
    if shadow_recovery:
        neutral |= (
            (normalized.max(axis=-1) - normalized.min(axis=-1) < 0.14)
            & (brightness > 0.04)
            & (brightness <= 0.28)
        )
    masks = {
        "screwdriver": valid & (r > 0.48) & (g > 0.23) & (b < 0.13),
        "hammer": valid & (r > 0.43) & (g > 0.23) & (b >= 0.13) & (b < 0.23),
        "wrench": valid & neutral,
    }
    result = {}
    for name, mask in masks.items():
        if names is not None and name not in names:
            continue
        candidates = []
        for pixels in components(mask):
            points = cloud[pixels[:, 0], pixels[:, 1]]
            top = np.quantile(points[:, 2], 0.95)
            top_points = points[np.abs(points[:, 2] - top) < 0.001]
            if len(top_points) < 40:
                continue
            normal = np.array([0.0, 0.0, 1.0])
            anchor = np.array([0.0, 0.0, top])
            basis = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]])
            if tilted_face:
                anchor = top_points.mean(0)
                _, _, axes3 = np.linalg.svd(top_points - anchor, full_matrices=False)
                normal = axes3[-1]
                if normal[2] < 0:
                    normal = -normal
                if normal[2] < 0.95:
                    continue  # Limited tabletop tilt, not arbitrary tool pose.
                horizontal = np.array([1.0, 0.0, -normal[0] / normal[2]])
                horizontal /= np.linalg.norm(horizontal)
                basis = np.stack([horizontal, np.cross(normal, horizontal)], axis=1)
            density = len(top_points) / max(len(points), 1)
            # Color supplies identity seeds; coplanar depth supplies geometry.
            # Specular edge pixels can lose the handle's material hue. Expand
            # only through a connected measured plane, never an inferred edge.
            plane = valid & (np.abs((cloud - anchor) @ normal) < 0.001)
            seed = np.zeros(valid.shape, dtype=bool)
            seed[pixels[:, 0], pixels[:, 1]] = True
            patches = list(components(plane))
            if patches:
                patch = max(patches, key=lambda p: seed[p[:, 0], p[:, 1]].sum())
                if seed[patch[:, 0], patch[:, 1]].sum() >= 40:
                    top_points = cloud[patch[:, 0], patch[:, 1]]
            xy = (top_points - anchor) @ basis
            # PCA depends on pixel density and perspective; it can rotate a
            # rectangular face even when its edges are clear. Fit the enclosing
            # rectangle instead, using only the measured top-face points.
            angles = np.deg2rad(np.arange(0, 90, 0.5))
            c, s = np.cos(angles), np.sin(angles)
            projections = np.stack(
                [xy[:, 0, None] * c + xy[:, 1, None] * s, -xy[:, 0, None] * s + xy[:, 1, None] * c],
                axis=-1,
            )
            bounds = np.quantile(projections, [0.001, 0.999], axis=0)
            index = np.argmin(np.prod(bounds[1] - bounds[0], axis=-1))
            axes = np.array([[c[index], -s[index]], [s[index], c[index]]])
            low, high = bounds[:, index]
            sides = np.sort(high - low)
            if not (0.035 < sides[0] < 0.050 and 0.048 < sides[1] < 0.065):
                continue
            plane_center = ((low + high) / 2) @ axes.T
            center3 = anchor + basis @ plane_center - normal * 0.022
            center = center3[:2]
            # Handle local Y is the longer (56mm) side. The sign remains
            # ambiguous by 180 degrees, which a parallel gripper does not need.
            long_axis = basis @ axes[:, np.argmax(high - low)]
            yaw = float(np.arctan2(long_axis[1], long_axis[0]) - np.pi / 2)
            yaw = float((yaw + np.pi / 2) % np.pi - np.pi / 2)
            # The rectangle alone has a 180-degree ambiguity. A declared tool
            # catalog supplies a separate pixel/depth cue: distal metal shaft
            # or wider hammer head. Missing/contradictory cues stay unknown.
            across = np.array([np.cos(yaw), np.sin(yaw)])
            along = np.array([-np.sin(yaw), np.cos(yaw)])
            relative = cloud[..., :2] - center
            lateral, longitudinal = relative @ across, relative @ along
            distal = 0.05 if name == "hammer" else 0.08
            limit = 0.052 if name == "hammer" else 0.045
            metal = (valid & neutral,)
            cue = (
                metal
                & (np.abs(lateral) < limit)
                & (np.abs(longitudinal) > distal)
                & (np.abs(longitudinal) < 0.135)
                & (np.abs(cloud[..., 2] - (top - 0.022)) < 0.025)
            )
            positive = int((cue & (longitudinal > 0)).sum())
            negative = int((cue & (longitudinal < 0)).sum())
            signed_yaw = None
            if max(positive, negative) >= 20 and max(positive, negative) > 3 * min(
                positive, negative
            ):
                signed_yaw = float(yaw if positive > negative else yaw + np.pi)
                signed_yaw = float((signed_yaw + np.pi) % (2 * np.pi) - np.pi)
            area = np.prod(sides)
            score = float(np.exp(-np.linalg.norm(sides - [0.044, 0.056]) / 0.01))
            candidates.append(
                {
                    "position_m": center3.tolist(),
                    "surface_normal": normal.tolist(),
                    "fit_score": score,
                    "surface_pixels": len(top_points),
                    "observed_sides_m": sides.tolist(),
                    "area_m2": float(area),
                    "top_fraction": density,
                    "yaw_mod_pi_rad": yaw,
                    "signed_yaw_rad": signed_yaw,
                    "direction_cue_pixels": {"positive": positive, "negative": negative},
                }
            )
        if len(candidates) == 1:
            result[name] = {"status": "observed", **candidates[0]}
        else:
            result[name] = {
                "status": "missing" if not candidates else "ambiguous",
                "position_m": None,
                "fit_score": 0,
                "candidate_count": len(candidates),
            }
    return result


def locate_tools(frame):
    predictions = _locate_tools(frame)
    # Broader shadow seeds can join otherwise separate surfaces. Preserve the
    # accepted bright-material estimate; try a separate pass only on a miss.
    # An ambiguous primary observation stays ambiguous.
    if predictions["wrench"]["status"] == "missing":
        recovered = _locate_tools(frame, shadow_recovery=True, names={"wrench"})["wrench"]
        recovered["appearance_recovery"] = "normalized_color_in_shadow"
        predictions["wrench"] = recovered
    for name, prediction in predictions.items():
        if prediction["status"] == "missing" or (
            prediction["status"] == "observed" and prediction["fit_score"] < 0.8
        ):
            recovered = _locate_tools(
                frame, shadow_recovery=name == "wrench", names={name}, tilted_face=True
            )[name]
            recovered["appearance_recovery"] = "measured_tilted_face"
            predictions[name] = recovered
    return predictions
