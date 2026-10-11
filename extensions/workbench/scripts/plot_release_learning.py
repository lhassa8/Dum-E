"""Separate future prediction accuracy from full physical journey acceptance."""

import json
from pathlib import Path

import matplotlib.pyplot as plt

root = Path(__file__).resolve().parents[1]
e = json.loads((root / "docs/release-learning-evidence.json").read_text())
fig, axes = plt.subplots(2, 2, figsize=(12, 9), facecolor="#f8fafc")
blue, orange = "#2563eb", "#f97316"
models = e["candidate2"]["models"]
ax = axes[0, 0]
values = [
    models["ensemble"]["rigid_xy_rmse_on_coverage_m"] * 1000,
    models["constant"]["xy_rmse_m"] * 1000,
    models["linear"]["xy_rmse_m"] * 1000,
    models["ensemble"]["xy_rmse_m"] * 1000,
]
ax.bar(
    ["Rigid", "Tool mean", "Linear", "Neural"], values, color=[blue, "#64748b", "#94a3b8", orange]
)
for i, value in enumerate(values):
    ax.text(i, value + 0.3, f"{value:.2f}", ha="center")
ax.set(ylabel="Future XY prediction RMSE (mm)", ylim=(0, 16))
ax.set_title("A · Predicting the result of release", loc="left")
ax.text(
    0.03,
    0.94,
    "234 action outcomes from 16 validation scenes;\n2 pre-release refusals counted in panel B",
    transform=ax.transAxes,
    va="top",
    fontsize=9,
)
ax = axes[0, 1]
ax.bar(
    ["Rigid", "Neural", "Neural + IK gate"],
    [16 / 18 * 100, 14 / 18 * 100, 14 / 18 * 100],
    color=[blue, orange, "#ea580c"],
)
for i, n in enumerate([16, 14, 14]):
    ax.text(i, n / 18 * 100 + 2, f"{n}/18", ha="center")
ax.axhline(95, color="#dc2626", linestyle="--")
ax.text(2.4, 96, "95% full-journey gate", ha="right", fontsize=9, color="#b91c1c")
ax.set(ylabel="Complete validation journeys passed (%)", ylim=(0, 110))
ax.set_title("B · Full-loop acceptance still fails", loc="left")
ax = axes[1, 0]
rigid = e["physical"]["release-validation-rigid-001"]["journeys"]
learned = e["physical"]["release-validation-model-ik-001"]["journeys"]
pairs = [
    (a, b)
    for a, b in zip(rigid, learned, strict=True)
    if a["physics"]["placed"] and b["physics"]["placed"]
]
ax.scatter(
    [a["physics"]["distance_m"] * 1000 for a, b in pairs],
    [b["physics"]["distance_m"] * 1000 for a, b in pairs],
    color=orange,
    edgecolor="#9a3412",
)
ax.plot([0, 25], [0, 25], "--", color="#64748b")
ax.set(
    xlim=(0, 26),
    ylim=(0, 26),
    xlabel="Rigid initial placement error (mm)",
    ylabel="Neural initial placement error (mm)",
)
ax.set_title("C · Initial placement improves", loc="left")
ax.text(
    0.04,
    0.93,
    "16 paired placements · mean 12.49 → 8.82mm\nReturns and refusals still count in panel B",
    transform=ax.transAxes,
    va="top",
    fontsize=9,
)
ax = axes[1, 1]
seeds = e["diagnostic"][1]["decisions"][1]["alternate_seed_results"]
current, home = seeds[0]["position_error_m"] * 1000, seeds[1]["position_error_m"] * 1000
ax.bar(["Current-pose seed", "Home-pose seed"], [current, home], color=["#dc2626", "#0d9488"])
ax.set_yscale("log")
ax.set_ylim(0.1, 200)
ax.set_ylabel("IK target position error (mm, log scale)")
ax.text(0, current * 1.1, f"{current:.2f}", ha="center")
ax.text(1, home * 1.2, f"{home:.3f}", ha="center")
ax.axhline(0.8, color="#64748b", linestyle="--")
ax.set_title("D · Reachable pose, failed solver branch", loc="left")
fig.suptitle(
    "Future release model · offline gain, failed full-loop acceptance", fontsize=17, y=0.99
)
fig.text(
    0.5,
    0.02,
    "Camera history + robot telemetry + proposed actions. "
    "Truth labels and branch resets only in the offline collector.\n"
    "24 new test layouts remain unopened; public assistant unchanged; "
    "all physical thresholds preserved.\n"
    "D: robot-only scratch kinematics; alternate-seed motion remains unverified.",
    ha="center",
    fontsize=9,
    color="#334155",
)
fig.tight_layout(rect=(0, 0.075, 1, 0.96), h_pad=3, w_pad=3)
fig.savefig(root / "docs/release-learning.png", dpi=170)
plt.close(fig)
