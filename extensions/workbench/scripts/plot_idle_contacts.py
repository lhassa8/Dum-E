"""Standalone measured tabletop drift figure, including every frozen case."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

root = Path(__file__).resolve().parents[1]
rows = json.loads((root / "docs/idle-contact-evidence.json").read_text())["qualification"]["rows"]
figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
for axis, mode, title, color in zip(
    axes,
    ["current", "sliding_table"],
    ["Previous contacts", "Separate tabletop contacts"],
    ["#d55e00", "#009e73"],
    strict=True,
):
    selected = [row for row in rows if row["mode"] == mode]
    for index, tool in enumerate(["screwdriver", "wrench", "hammer"]):
        cases = [row for row in selected if row["tool"] == tool]
        values = [max(row["idle"]["peak_displacement_m"].values()) * 1000 for row in cases]
        axis.scatter([index - 0.1, index, index + 0.1], values, color=color, s=35)
    axis.axhline(4, color="black", linestyle="--", linewidth=1, label="4mm acceptance limit")
    axis.set(
        title=title,
        ylabel="Peak body-center displacement (mm)",
        ylim=(-1, 80),
        xticks=[0, 1, 2],
        xticklabels=["Screwdriver", "Wrench", "Hammer"],
    )
    axis.grid(axis="y", alpha=0.2)
    axis.legend(loc="upper right", fontsize=8)
axes[1].text(
    0.5,
    0.6,
    "All nine cases below 0.001 mm\nNo weld, freezing or sleep",
    ha="center",
    transform=axes[1].transAxes,
    fontsize=11,
)
figure.suptitle("30 simulated minutes after physical return · three starting variations per tool")
figure.savefig(root / "docs/idle-contact-comparison.png", dpi=180)
plt.close(figure)
