"""Show physical hold improvement and the failed reserved-layout gate separately."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "docs/camera-motion-requalification-evidence.json").read_text())
tools = ["screwdriver", "wrench", "hammer"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), constrained_layout=True)
for field, offset, color, label in [
    ("baseline_hold", -0.17, "#c0752b", "Previous camera hold"),
    ("shared_hold", 0.17, "#087b72", "Shared verified hold"),
]:
    rows = data[field]["rows"]
    heights = [
        min(r["hold"]["minimum_tool_height_m"] for r in rows if r["tool"] == t) * 1000
        for t in tools
    ]
    axes[0].scatter(np.arange(3) + offset, heights, color=color, label=label, s=55, zorder=3)
axes[0].axhline(130, color="#ac313a", linestyle="--", label="Existing 130 mm gate")
axes[0].set(
    xticks=np.arange(3),
    xticklabels=tools,
    ylim=(120, 140),
    ylabel="Lowest tool height during 32 simulated seconds (mm)",
    title="Retaining a paused tool",
)
axes[0].legend(loc="upper right", fontsize=8)
for i, key in enumerate(["final_validation", "reserved_test"]):
    cohort = data["cohorts"][key]
    fraction = 100 * cohort["all_criteria_successes"] / cohort["cases"]
    axes[1].bar(i, fraction, color=["#087b72", "#ac313a"][i], width=0.5)
    axes[1].text(
        i,
        fraction + 1.5 if fraction >= 95 else fraction - 7,
        f"{cohort['all_criteria_successes']}/{cohort['cases']}",
        ha="center",
        color="black" if fraction >= 95 else "white",
    )
axes[1].axhline(95, color="#ac313a", linestyle="--", label="Unchanged 95% gate")
axes[1].set(
    xticks=[0, 1],
    xticklabels=["Validation layouts", "Reserved layouts"],
    ylim=(0, 110),
    ylabel="Full journeys passing all physical gates (%)",
    title="New layouts still expose failures",
)
axes[1].legend(loc="lower right", fontsize=9)
for ax in axes:
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.15)
    ax.set_axisbelow(True)
fig.suptitle("Camera motion: long-hold recovery and reserved-layout qualification", fontsize=12)
fig.savefig(root / "docs/camera-motion-requalification.png", dpi=170)
plt.close(fig)
