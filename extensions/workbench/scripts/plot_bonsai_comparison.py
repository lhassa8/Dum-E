"""Standalone figure of the paired complete-response measurements."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

root = Path(__file__).resolve().parents[1]
data = json.loads((root / "docs/bonsai-evidence.json").read_text())["paired"]
labels = ["GPT-6 Luna\nChatGPT subscription", "Bonsai-27B\nLM Studio"]
colors = ["#0072b2", "#009e73"]
figure, axes = plt.subplots(1, 2, figsize=(10, 4.3), constrained_layout=True)
for index, backend in enumerate(["codex", "lmstudio"]):
    rows = [r["elapsed_ms"] / 1000 for r in data["rows"] if r["backend"] == backend]
    median = float(np.median(rows))
    axes[0].bar(index, median, width=0.5, color=colors[index])
    axes[0].text(index, median + 0.08, f"{median:.3f}s", ha="center", fontsize=11)
    axes[1].scatter(index + np.linspace(-0.13, 0.13, len(rows)), rows,
                    color=colors[index], s=35)
axes[0].set(title="Median complete response", ylim=(0, 3), ylabel="Seconds")
axes[1].set(title="Every paired trial, including the cloud delay", ylim=(0, 13.5),
            ylabel="Seconds", xlim=(-0.4, 1.4))
for axis in axes:
    axis.set(xticks=[0, 1], xticklabels=labels)
    axis.grid(axis="y", alpha=0.2)
    axis.set_axisbelow(True)
figure.suptitle("Same five requests, twice each · alternating order · text only", fontsize=11)
figure.savefig(root / "docs/bonsai-comparison.png", dpi=180)
plt.close(figure)
