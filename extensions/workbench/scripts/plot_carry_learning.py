"""Show improved state estimates and failed physical acceptance together."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1]
e = json.loads((root / "docs/carry-learning-evidence.json").read_text())
fig, axes = plt.subplots(2, 2, figsize=(12, 9), facecolor="#f8fafc")
rigid, learned = "#2563eb", "#f97316"
v = e["candidate2_validation"]
ax = axes[0, 0]
values = [v["rigid_on_learned_coverage"]["rmse_m"] * 1000, v["learned"]["rmse_m"] * 1000]
ax.bar(["Rigid estimate", "Learned estimate"], values, color=[rigid, learned], width=0.5)
for i, value in enumerate(values):
    ax.text(i, value + 0.4, f"{value:.2f}", ha="center", fontsize=12)
ax.set_ylim(0, 16)
ax.set_ylabel("Position RMSE (mm)")
ax.set_title("A · Better estimates in free space", loc="left")
ax.text(0.02, 0.94, "603 matched validation samples; 1 withheld", transform=ax.transAxes, va="top")
ax = axes[0, 1]
names = ["Existing 12 cases", "New 24 test cases"]
baseline = [11 / 12 * 100, 21 / 24 * 100]
candidate = [10 / 12 * 100, 20 / 24 * 100]
positions = np.arange(2)
ax.bar(positions - 0.18, baseline, width=0.36, color=rigid, label="Rigid controller")
ax.bar(positions + 0.18, candidate, width=0.36, color=learned, label="Learned XY correction")
for i, (a, b) in enumerate([(11, 10), (21, 20)]):
    ax.text(i - 0.18, baseline[i] + 1.5, f"{a}/{12 if i == 0 else 24}", ha="center")
    ax.text(i + 0.18, candidate[i] + 1.5, f"{b}/{12 if i == 0 else 24}", ha="center")
ax.axhline(95, color="#dc2626", linestyle="--", linewidth=1)
ax.text(1.43, 95, "95% gate", ha="right", va="bottom", color="#b91c1c", fontsize=9)
ax.set_xticks(positions, names)
ax.set_ylabel("Full journeys passed (%)")
ax.set_ylim(0, 110)
ax.set_title("B · Handling did not improve", loc="left")
ax.legend(loc="lower left", fontsize=9)
ax = axes[1, 0]
a = e["physical"]["carry-test-rigid-001"]["journeys"]
b = e["physical"]["carry-test-learned-001"]["journeys"]
pairs = [
    (x, y) for x, y in zip(a, b, strict=True) if x["physics"]["placed"] and y["physics"]["placed"]
]
ax.scatter(
    [x["physics"]["distance_m"] * 1000 for x, _ in pairs],
    [y["physics"]["distance_m"] * 1000 for _, y in pairs],
    color=learned,
    edgecolor="#9a3412",
)
ax.plot([0, 35], [0, 35], "--", color="#64748b")
ax.set(
    xlim=(0, 36),
    ylim=(0, 36),
    xlabel="Rigid initial placement error (mm)",
    ylabel="Learned initial placement error (mm)",
)
ax.set_title("C · Some placements improve, others worsen", loc="left")
ax.text(
    0.04,
    0.94,
    "21 paired placements; 3 initial failures\ncounted in panel B",
    transform=ax.transAxes,
    va="top",
    fontsize=9,
)
ax = axes[1, 1]
for kind, color, label in [("rigid", rigid, "Rigid"), ("learned_xy", learned, "Learned XY")]:
    rows = {r["phase"]: r for r in e["diagnostic"][kind]}
    phases = ["Placing tool", "Releasing"]
    residual = [rows[p]["current_world_residual_m"][0] * 1000 for p in phases]
    ax.plot([0, 1], residual, "o-", color=color, label=label)
ax.axhline(0, color="#64748b", linewidth=1)
ax.set_xticks([0, 1], ["Before lowering", "Before opening gripper"])
ax.set_ylim(-8, 20)
ax.set_ylabel("Actual minus rigid tool X position (mm)")
ax.set_title("D · Contact changes the needed correction", loc="left")
ax.text(
    0.03,
    0.12,
    "One retained screwdriver diagnostic.\n"
    "Learned descent correction: +9.63mm;\n"
    "at release the actual residual is −3.76mm.",
    transform=ax.transAxes,
    fontsize=9,
)
ax.legend(loc="upper right", fontsize=9)
fig.suptitle("Learned carry estimator · rejected for default motion", fontsize=17, y=0.99)
fig.text(
    0.5,
    0.015,
    "Current hidden-position estimation is not future-outcome prediction. "
    "Independent physics judges include refusals, returns and disturbance.\n"
    "Public assistant remains on its accepted controller; all physical thresholds unchanged.",
    ha="center",
    fontsize=10,
    color="#334155",
)
fig.tight_layout(rect=(0, 0.075, 1, 0.96), h_pad=3, w_pad=3)
fig.savefig(root / "docs/carry-learning.png", dpi=170)
plt.close(fig)
