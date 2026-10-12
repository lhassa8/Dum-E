"""Plot measured recovery results without treating progress as acceptance."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1]
e = json.loads((root / "docs/camera-recovery-evidence.json").read_text())
rigid = e["final"]["camera-recovery-validation-rigid-008"]["journeys"]
learned = e["final"]["camera-recovery-validation-model-final-001"]["journeys"]
fig, axes = plt.subplots(2, 2, figsize=(12, 9), facecolor="#f8fafc")
blue, orange, red = "#2563eb", "#f97316", "#dc2626"
ax = axes[0, 0]
counts = [16, 14, 17, 17]
ax.bar(
    ["C3 rigid", "C3 neural", "Recovery", "+ neural"],
    np.array(counts) / 18 * 100,
    color=["#94a3b8", "#cbd5e1", blue, orange],
)
for i, n in enumerate(counts):
    ax.text(i, n / 18 * 100 + 2, f"{n}/18", ha="center")
ax.axhline(95, color=red, linestyle="--")
ax.set(ylabel="Full validation journeys passed (%)", ylim=(0, 110))
ax.set_title("A · Progress; 95% acceptance still fails", loc="left")
ax.text(
    0.02,
    0.04,
    "C3: final displacement judge\nRecovery: maximum sampled displacement judge",
    transform=ax.transAxes,
    fontsize=9,
)
ax = axes[0, 1]
samples = e["wrist"]["samples"]
times = np.array([s["time_s"] for s in samples])
torque = np.array([s["torque_nm"] for s in samples])
ax.plot((times - times[0]) * 1000, torque, color=blue, linewidth=0.8)
ax.axhline(e["wrist"]["mean_torque_nm"], color=orange, linewidth=2, label="Mean: 0 Nm")
ax.set(xlabel="Time since first sample (ms)", ylabel="Wrist torque (Nm)", ylim=(-16, 16))
ax.set_title("B · 2 ms samples reveal servo chatter", loc="left")
ax.legend(loc="upper right")
ax = axes[1, 0]
x = np.arange(18)
for rows, offset, color, label in [
    (rigid, -0.2, blue, "Recovery"),
    (learned, 0.2, orange, "+ neural"),
]:
    errors = [row["physics"]["distance_m"] * 1000 for row in rows]
    ax.bar(x + offset, errors, width=0.4, color=color, label=label)
ax.axhline(35, color=red, linestyle="--", label="35 mm limit")
ax.set(
    xticks=[0, 4, 8, 12, 16, 17],
    xlabel="Frozen validation case index",
    ylabel="Initial placement error (mm)",
    ylim=(0, 43),
)
ax.set_title("C · Wrench redirect misses by 1.4 mm", loc="left")
ax.legend(fontsize=8, loc="upper left")
ax.annotate(
    "36.424 mm",
    (16, 36.424),
    xytext=(10, 40),
    arrowprops={"arrowstyle": "->", "color": red},
    color=red,
)
ax = axes[1, 1]
p = e["pipeline"]
labels = ["Capture", "Localization", "Complete pipeline"]
keys = ["capture_ms", "localization_ms", "pipeline_ms"]
medians = [p[k]["median"] for k in keys]
p95 = [p[k]["p95"] for k in keys]
ax.bar(np.arange(3) - 0.18, medians, width=0.36, color=blue, label="Median")
ax.bar(np.arange(3) + 0.18, p95, width=0.36, color=orange, label="p95")
ax.set(xticks=np.arange(3), xticklabels=labels, ylabel="Wall time (ms)", ylim=(0, 108))
ax.set_title("D · Camera cost: 30 sequential frames", loc="left")
ax.legend(loc="upper left", fontsize=9)
ax.text(
    0.03,
    0.06,
    "One stationary scene; excludes speech,\nmotion, IPC and disk writes",
    transform=ax.transAxes,
    fontsize=9,
)
fig.suptitle("Camera-guided workbench recovery · experimental", fontsize=17, y=0.99)
fig.text(
    0.5,
    0.025,
    "Same frozen 18 validation journeys; physics, force caps and thresholds preserved.\n"
    "24 test layouts remain unopened. Camera controller is not enabled in the public voice app.",
    ha="center",
    fontsize=9,
    color="#334155",
)
fig.tight_layout(rect=(0, 0.075, 1, 0.96), h_pad=3, w_pad=3)
fig.savefig(root / "docs/camera-recovery.png", dpi=170)
plt.close(fig)
