"""Scientific figure from actual camera frames and independent physics evidence."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

root = Path(__file__).resolve().parents[1]
e = json.loads((root / "docs/camera-delivery-evidence.json").read_text())
frames = root / "runs/camera-delivery-final-002/heldout-02"
fig = plt.figure(figsize=(13, 10), facecolor="#f8fafc")
grid = fig.add_gridspec(3, 4, height_ratios=[1, 1, 1.1], hspace=0.4, wspace=0.5)
for i, (file, title) in enumerate(
    [
        ("0000.png", "1 · Observe a changed layout"),
        ("0191.png", "2 · Physical grasp and lift"),
        ("0323.png", "3 · Release at handoff"),
        ("returned.png", "4 · Fresh camera pickup and return"),
    ]
):
    ax = fig.add_subplot(grid[i // 2, (i % 2) * 2 : (i % 2) * 2 + 2])
    ax.imshow(Image.open(frames / file))
    ax.set_title(title, loc="left", fontsize=12)
    ax.axis("off")
ax = fig.add_subplot(grid[2, :2])
rows = e["journeys"]
positions = np.arange(len(rows))
primary = [r["physics"]["distance_m"] * 1000 for r in rows]
ax.bar(positions, primary, color="#2563eb", label="Initial placement")
ret = [r["return"]["distance_m"] * 1000 if r["return"] else np.nan for r in rows]
ax.scatter(positions, ret, color="#f97316", marker="D", label="Fresh-camera return", zorder=3)
ax.axhline(35, color="#64748b", linestyle="--", label="35mm placement limit")
ax.set_ylim(0, 42)
ax.set_xticks(positions, [f"{i:02d}" for i in positions])
ax.set_xlabel("Frozen varied-layout case")
ax.set_ylabel("Placement error (mm)")
ax.set_title("Placement passes; the full journey still fails", loc="left", fontsize=12)
ax.legend(fontsize=8, loc="upper left", ncol=2)
ax = fig.add_subplot(grid[2, 2:])
disturbance = [r["physics"]["other_tool_disturbance_m"] * 1000 for r in rows]
ax.bar(positions, disturbance, color=["#dc2626" if not r["passed"] else "#0d9488" for r in rows])
ax.axhline(4, color="#dc2626", linestyle="--", label="Fixed 4mm disturbance limit")
ax.set_ylim(0, 5.5)
ax.set_xticks(positions, [f"{i:02d}" for i in positions])
ax.set_xlabel("Frozen varied-layout case")
ax.set_ylabel("Other-tool disturbance (mm)")
ax.set_title("Retained failure: returned hammer nudges screwdriver", loc="left", fontsize=12)
ax.legend(fontsize=8, loc="upper left")
ax.annotate(
    "4.14mm",
    xy=(5, disturbance[5]),
    xytext=(6.6, 4.75),
    color="#b91c1c",
    arrowprops={"arrowstyle": "->", "color": "#b91c1c"},
    fontsize=10,
)
fig.suptitle("Camera-informed workbench manipulation · experimental D2", fontsize=17, y=0.99)
fig.text(
    0.5,
    0.018,
    "Actor: camera + robot telemetry + declared catalog/rigid-grasp inference. "
    "Truth is used only by the independent judge.\n"
    "12 initial moves + 8 fresh-camera returns; 11/12 full journeys pass. "
    "Public controller unchanged; no hardware claim.",
    ha="center",
    fontsize=10,
    color="#334155",
)
fig.subplots_adjust(top=0.93, bottom=0.095, left=0.065, right=0.975)
fig.savefig(root / "docs/camera-delivery.png", dpi=170)
plt.close(fig)
