"""Render the retained bounded prompt study from public synthetic evidence.

Run from the lab's locked environment (Matplotlib is optional for the fork).
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "docs/dialogue-revision-evidence.json").read_text())
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), layout="constrained")
fig.suptitle("Dum-E: decision correctness comes before speed", fontsize=16)

names = ["Baseline", "No cache", "Revision 1", "Revision 2"]
keys = [
    "small_baseline_pairs",
    "small_uncached_pairs",
    "small_attempt1_pairs",
    "small_final_pairs",
]
counts = [data["native"][key]["count"] for key in keys]
failed = [data["native"][key]["incorrect"] for key in keys]
axes[0].bar(names, [100 * n / total for n, total in zip(failed, counts, strict=True)])
for x, (n, total) in enumerate(zip(failed, counts, strict=True)):
    axes[0].text(x, 100 * n / total + 2, f"{n}/{total}", ha="center")
axes[0].set(ylim=(0, 72), ylabel="Incorrect decisions (%)", title="Small-model tool-pair judge")
axes[0].tick_params(axis="x", rotation=15)

groups = ["common", "general", "guards"]
x = np.arange(len(groups))
for offset, key, label, color in [
    (-0.18, "large_before", "Before", "#617eae"),
    (0.18, "large_final", "Revised", "#d48440"),
]:
    stats = data["speech"][key]
    medians = [stats[group]["median_ms"] / 1000 for group in groups]
    tails = [stats[group]["p95_ms"] / 1000 for group in groups]
    axes[1].bar(x + offset, medians, width=0.35, label=label, color=color)
    axes[1].scatter(x + offset, tails, marker="_", color="black", zorder=3)
axes[1].set_xticks(x, ["Familiar (18)", "General (6)", "Guards (6)"])
axes[1].set(ylabel="Seconds", title="Accepted model: saved speech → decision")
axes[1].legend(title="Bars: median; ticks: p95", fontsize=9)
axes[1].tick_params(axis="x", rotation=15)

for i, model in enumerate(["large", "small"]):
    rows = data["quality_review"][model]
    passed = sum(row["verdict"] == "pass" for row in rows)
    partial = sum(row["verdict"] == "partial" for row in rows)
    axes[2].bar(i, passed, color="#52947e", label="Meets criterion" if i == 0 else None)
    axes[2].bar(
        i, partial, bottom=passed, color="#d48440", label="Partial reply" if i == 0 else None
    )
    axes[2].text(i, 31, f"{passed}/30 complete", ha="center")
axes[2].set_xticks([0, 1], ["Kept default", "Experimental small"])
axes[2].set(ylim=(0, 42), ylabel="Actual replies", title="Final factual/capability reading")
axes[2].legend(fontsize=9)
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.18)
    ax.set_axisbelow(True)
fig.text(
    0.01,
    -0.03,
    "Synthetic speech; unchanged timing boundaries. Audible onset and live room accuracy excluded. "
    "Quality review by lead agent, not human approval.",
    fontsize=9,
)
output = root / "docs/dialogue-revision.png"
fig.savefig(output, dpi=150, bbox_inches="tight")
print(output)
