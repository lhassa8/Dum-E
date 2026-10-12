"""Measured grasp drift, counterfactual futures and missing training exposure."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1]
e = json.loads((root / "docs/held-pose-learning-evidence.json").read_text())
fig, axes = plt.subplots(2, 2, figsize=(12, 9), facecolor="#f8fafc")
blue, orange, red = "#2563eb", "#f97316", "#dc2626"
ax = axes[0, 0]
phases = {
    "Lifting tool",
    "Moving to target",
    "Lifting for return",
    "Choosing release action",
    "Placing tool",
}
rows = [r for r in e["diagnostic"]["samples"] if r["phase"] in phases and "center_error_m" in r]
t = np.array([r["time_s"] for r in rows])
ax.plot(t - t[0], [r["center_error_m"] * 1000 for r in rows], color=blue)
ax.set(
    xlabel="Simulation time since lift began (s)",
    ylabel="Inferred held-center error (mm)",
    ylim=(0, 40),
)
ax.set_title("A · Closed jaws do not prove tool pose", loc="left")
ax.text(
    0.03,
    0.93,
    "Known failing wrench redirect;\nphysical labels only in independent judge",
    transform=ax.transAxes,
    va="top",
    fontsize=9,
)
ax = axes[0, 1]
outcomes = np.asarray(e["counterfactual_pilot"]["records"][0]["legs"][0]["outcomes"])
errors = np.linalg.norm(outcomes[:, :2], axis=1) * 1000
matrix = errors.reshape(3, 3).T
im = ax.imshow(matrix, origin="lower", cmap="viridis_r", vmin=0, vmax=65)
for y in range(3):
    for x in range(3):
        ax.text(
            x,
            y,
            f"{matrix[y, x]:.1f}",
            ha="center",
            va="center",
            color="white" if matrix[y, x] > 35 else "black",
        )
ax.set(
    xticks=range(3),
    yticks=range(3),
    xticklabels=["-20", "0", "+20"],
    yticklabels=["-20", "0", "+20"],
    xlabel="Proposed X release offset (mm)",
    ylabel="Proposed Y release offset (mm)",
)
ax.set_title("B · Measured future error for nine actions", loc="left")
fig.colorbar(im, ax=ax, label="Final XY error (mm)", fraction=0.04)
ax = axes[1, 0]
models = e["fit"]["models"]
values = [models["ensemble"]["rigid_xy_rmse_on_coverage_m"] * 1000] + [
    models[k]["xy_rmse_m"] * 1000 for k in ["constant", "linear", "ensemble"]
]
ax.bar(
    ["Rigid", "Tool mean", "Linear", "Neural"], values, color=["#94a3b8", "#cbd5e1", blue, orange]
)
for i, value in enumerate(values):
    ax.text(i, value + 0.5, f"{value:.2f}", ha="center")
ax.set(ylabel="Future XY RMSE (mm)", ylim=(0, 29))
ax.set_title("C · Better average; accuracy gate fails", loc="left")
ax.text(
    0.03,
    0.93,
    "270 validation outcomes; neural p95 11.11 mm\nexceeds the 10 mm gate",
    transform=ax.transAxes,
    va="top",
    fontsize=9,
)
ax = axes[1, 1]
counts = []
for split in ["train", "validation"]:
    counts.append(
        sum(
            leg.get("deliberately_reoriented", False)
            for r in e["dataset"]["records"]
            if r["case"]["split"] == split
            for leg in r["legs"]
            if leg.get("rows", 0)
        )
    )
ax.bar(["Training", "Validation"], counts, color=[blue, orange])
for i, n in enumerate(counts):
    ax.text(i, n + 0.1, str(n), ha="center")
ax.set(ylabel="Deliberately reoriented release states", ylim=(0, 4.2))
ax.set_title("D · Training is missing the needed turns", loc="left")
fig.suptitle("Held-tool learning · evidence reveals a training gap", fontsize=17, y=0.99)
fig.text(
    0.5,
    0.025,
    "Camera fits withheld all 12 airborne views. Model rejected; public app unchanged.\n"
    "24 test layouts unopened. B shows one physical state, not a learned policy.",
    ha="center",
    fontsize=9,
    color="#334155",
)
fig.tight_layout(rect=(0, 0.075, 1, 0.96), h_pad=3, w_pad=3)
fig.savefig(root / "docs/held-pose-learning.png", dpi=170)
plt.close(fig)
