"""Experimental held-face measurement using RGB-D and a measured robot TCP.

Known colors/dimensions and upward-facing handles only. Robust plane hypotheses
may join visible parts around an occluding jaw; no missing edge is synthesized.
No simulator objects, segmentation, physical labels or inferred tool pose inputs.
"""

from time import perf_counter

import numpy as np

from physical_ai_lab.assistant.perception import TOOLS


def locate_held_face(frame, name, tcp_m):
    began = perf_counter()
    if name not in TOOLS:
        raise ValueError("Unknown held tool")
    tcp = np.asarray(tcp_m, float)
    if tcp.shape != (3,) or not np.isfinite(tcp).all():
        raise ValueError("Invalid measured TCP")
    v, u = np.indices(frame.depth_m.shape)
    cloud = frame.camera.unproject(u, v, frame.depth_m)
    rgb = frame.rgb.astype(float) / 255
    normalized = rgb / np.maximum(rgb.sum(-1)[..., None], 1e-9)
    r, g, b = np.moveaxis(normalized, -1, 0)
    brightness = rgb.mean(-1)
    colors = {
        "wrench": (normalized.max(-1) - normalized.min(-1) < 0.14) & (brightness > 0.04),
        "screwdriver": (r > 0.48) & (g > 0.23) & (b < 0.13),
        "hammer": (r > 0.43) & (g > 0.23) & (b >= 0.13) & (b < 0.23),
    }
    valid = (
        np.isfinite(cloud).all(-1)
        & (frame.depth_m > 0)
        & (np.linalg.norm(cloud - tcp, axis=-1) < 0.08)
        & (cloud[..., 2] > 0.05)
    )
    points = cloud[valid & colors[name]]
    missing = {
        "status": "missing",
        "position_m": None,
        "fit_score": 0,
        "provenance": "Measured held-face RGB-D; no pose fallback",
    }
    if len(points) < 40:
        return missing
    rng = np.random.default_rng(0)
    triples = points[rng.integers(0, len(points), (1200, 3))]
    normals = np.cross(triples[:, 1] - triples[:, 0], triples[:, 2] - triples[:, 0])
    length = np.linalg.norm(normals, axis=1)
    normals = normals[length > 1e-6] / length[length > 1e-6, None]
    anchors = triples[length > 1e-6, 0]
    normals *= np.where(normals[:, 2:3] < 0, -1, 1)
    keep = normals[:, 2] >= 0.95
    normals, anchors = normals[keep], anchors[keep]
    if not len(normals):
        return missing
    distances = np.abs(points @ normals.T - np.sum(anchors * normals, axis=1))
    counts = (distances < 0.001).sum(0)
    order = np.argsort(counts)[::-1]
    hypotheses, candidates = [], []
    for i in order:
        if counts[i] < 40 or len(hypotheses) >= 12:
            break
        normal, anchor = normals[i], anchors[i]
        if any(abs(normal @ (anchor - a)) < 0.0015 and normal @ n > 0.999 for n, a in hypotheses):
            continue
        hypotheses.append((normal, anchor))
        patch = points[distances[:, i] < 0.001]
        anchor = patch.mean(0)
        _, _, axes = np.linalg.svd(patch - anchor, full_matrices=False)
        normal = axes[-1]
        if normal[2] < 0:
            normal = -normal
        if normal[2] < 0.95:
            continue
        horizontal = np.array([1.0, 0.0, -normal[0] / normal[2]])
        horizontal /= np.linalg.norm(horizontal)
        basis = np.stack([horizontal, np.cross(normal, horizontal)], axis=1)
        xy = (patch - anchor) @ basis
        angles = np.deg2rad(np.arange(0, 90, 0.5))
        c, s = np.cos(angles), np.sin(angles)
        projections = np.stack(
            [xy[:, 0, None] * c + xy[:, 1, None] * s, -xy[:, 0, None] * s + xy[:, 1, None] * c],
            axis=-1,
        )
        bounds = np.quantile(projections, [0.001, 0.999], axis=0)
        index = np.argmin(np.prod(bounds[1] - bounds[0], axis=-1))
        low, high = bounds[:, index]
        sides = np.sort(high - low)
        if not (0.035 < sides[0] < 0.050 and 0.048 < sides[1] < 0.065):
            continue
        score = float(np.exp(-np.linalg.norm(sides - [0.044, 0.056]) / 0.01))
        if score < 0.8:
            continue
        inplane = np.array([[c[index], -s[index]], [s[index], c[index]]])
        center = anchor + basis @ (((low + high) / 2) @ inplane.T) - normal * 0.022
        long = basis @ inplane[:, np.argmax(high - low)]
        yaw = float((np.arctan2(long[1], long[0]) - np.pi / 2 + np.pi / 2) % np.pi - np.pi / 2)
        observation = {
            "status": "observed",
            "position_m": center.tolist(),
            "surface_normal": normal.tolist(),
            "yaw_mod_pi_rad": yaw,
            "fit_score": score,
            "observed_sides_m": sides.tolist(),
            "surface_pixels": len(patch),
            "signed_yaw_rad": None,
            "latency_ms": (perf_counter() - began) * 1000,
            "provenance": "Measured held-face RGB-D; no pose fallback",
        }
        if not any(
            np.linalg.norm(center - np.array(p["position_m"])) < 0.003
            and np.dot(normal, p["surface_normal"]) > 0.999
            for p in candidates
        ):
            candidates.append(observation)
    if len(candidates) == 1:
        return candidates[0]
    return {
        **missing,
        "status": "ambiguous" if candidates else "missing",
        "candidate_count": len(candidates),
        "latency_ms": (perf_counter() - began) * 1000,
    }
