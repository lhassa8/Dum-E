"""Measured vision accuracy and complete-response times on matched images."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

root = Path(__file__).resolve().parents[1]
evidence = json.loads((root / "docs/vision-language-evidence.json").read_text())
keys = ["qwen_expanded", "qwen_compact", "gemma_grid"]
labels = ["Qwen\nexplicit presence", "Qwen\ncompact", "Gemma\nexplicit grid"]
colors = ["#0072b2", "#d55e00", "#009e73"]
figure, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
for index, key in enumerate(keys):
    rows = evidence[key]["rows"]
    accuracy = 100 * sum(row["passed"] for row in rows) / len(rows)
    times = [row["observation"]["elapsed_ms"] / 1000 for row in rows]
    axes[0].bar(index, accuracy, color=colors[index], width=0.5)
    axes[0].text(index, accuracy + 2, f"{accuracy:.0f}%", ha="center")
    axes[1].scatter(index + np.linspace(-0.12, 0.12, len(times)), times, color=colors[index], s=30)
axes[0].axhline(95, linestyle="--", color="black", linewidth=1)
axes[0].set(
    title="Correct identities and image locations", ylabel="Passed scenes (%)", ylim=(0, 110)
)
axes[1].axhline(2, linestyle="--", color="black", linewidth=1)
axes[1].set(title="Every complete-response measurement", ylabel="Seconds", ylim=(0, 2.3))
for axis in axes:
    axis.set(xticks=[0, 1, 2], xticklabels=labels)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
figure.suptitle("Same ten validation images · includes missing tools · GPU configuration requested")
figure.savefig(root / "docs/vision-language-comparison.png", dpi=180)
plt.close(figure)
