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


def locate_tools(frame):
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
    masks = {
        "screwdriver": valid & (r > 0.48) & (g > 0.23) & (b < 0.13),
        "hammer": valid & (r > 0.43) & (g > 0.23) & (b >= 0.13) & (b < 0.23),
        "wrench": valid & (chroma < 0.16) & (rgb.mean(axis=-1) > 0.28),
    }
    result = {}
    for name, mask in masks.items():
        candidates = []
        for pixels in components(mask):
            points = cloud[pixels[:, 0], pixels[:, 1]]
            top = np.quantile(points[:, 2], 0.95)
            top_points = points[np.abs(points[:, 2] - top) < 0.001]
            if len(top_points) < 40:
                continue
            xy = top_points[:, :2]
            _, axes = np.linalg.eigh(np.cov(xy.T))
            projected = xy @ axes
            low, high = np.quantile(projected, [0.01, 0.99], axis=0)
            sides = np.sort(high - low)
            if not (0.035 < sides[0] < 0.050 and 0.048 < sides[1] < 0.065):
                continue
            center = ((low + high) / 2) @ axes.T
            area = np.prod(sides)
            density = len(top_points) / max(len(points), 1)
            score = float(np.exp(-np.linalg.norm(sides - [0.044, 0.056]) / 0.01))
            candidates.append(
                {
                    "position_m": [float(center[0]), float(center[1]), float(top - 0.022)],
                    "fit_score": score,
                    "surface_pixels": len(top_points),
                    "observed_sides_m": sides.tolist(),
                    "area_m2": float(area),
                    "top_fraction": density,
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
