"""Plot the optical baseline from retained synthetic evidence only.

Matplotlib is supplied by the lab environment, optional for the fork runtime.
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "docs/camera-perception-evidence.json").read_text())
fig, axes = plt.subplots(2, 2, figsize=(13, 9), layout="constrained")
fig.suptitle("Dum-E camera baseline: visible tools and honest uncertainty", fontsize=17)
for ax, key, title in [
    (axes[0, 0], "clear", "Shuffled, rotated tools: green truth / magenta camera"),
    (axes[0, 1], "occluded", "Obscured handle: detector withholds its position"),
]:
    ax.imshow(Image.open(root / "docs" / data["images"][key]))
    ax.set_title(title, fontsize=12)
    ax.axis("off")
for key, label, color in [
    ("pilot", "Pilot (36)", "#d48440"),
    ("heldout", "Held-out clear (72)", "#52947e"),
]:
    errors = [
        e * 1000
        for row in data[key]["rows"]
        if row["occluded"] is None
        for e in row["errors_m"].values()
        if e is not None
    ]
    axes[1, 0].hist(errors, bins=np.linspace(0, 6, 31), alpha=0.65, label=label, color=color)
axes[1, 0].axvline(5, color="black", linestyle="--", label="Provisional p95 gate: 5mm")
axes[1, 0].set(
    xlabel="Position error (mm)",
    ylabel="Tool estimates",
    title="Retained errors include the pilot outlier",
)
axes[1, 0].legend(fontsize=9)
pipeline = data["pipeline"]
categories = ["capture_ms", "localization_ms", "pipeline_ms"]
medians = [pipeline[k]["median"] for k in categories]
tails = [pipeline[k]["p95"] for k in categories]
axes[1, 1].bar(range(3), medians, color="#617eae")
axes[1, 1].scatter(range(3), tails, marker="_", color="black", label="p95", zorder=3)
for i, value in enumerate(medians):
    axes[1, 1].text(i, tails[i] + 1, f"{value:.1f}ms median", ha="center", fontsize=10)
axes[1, 1].set_xticks(range(3), ["RGB/depth capture", "Localization", "Whole pipeline"])
axes[1, 1].set(ylabel="Milliseconds", title="30 actual stationary-frame captures")
axes[1, 1].set_ylim(0, max(tails) * 1.3)
axes[1, 1].legend()
for ax in axes[1]:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
fig.text(
    0.01,
    -0.02,
    "Known primitive handles and calibrated simulated RGB/depth. "
    "No camera-driven motion yet; simulator truth is used only for labels/judging.",
    fontsize=10,
)
output = root / "docs/camera-perception.png"
fig.savefig(output, dpi=150, bbox_inches="tight")
print(output)
