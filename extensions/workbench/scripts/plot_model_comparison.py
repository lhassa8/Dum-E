"""Reproduce the measured model-comparison figure from its saved evidence."""

import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence", type=Path, default=ROOT / "docs/model-comparison-evidence.json"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "docs/model-comparison.png")
    args = parser.parse_args()

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    data = json.loads(args.evidence.read_text())["results"]
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.3), layout="constrained")
    colors = ["#455d79", "#b75a32"]
    names = ["Accepted model", "Candidate (rejected)"]
    x, width = np.arange(3), 0.34
    for index, model in enumerate(["large", "small"]):
        values = [
            data[model][key]["median_ms"] / 1000 for key in ["original", "context", "quality"]
        ]
        bars = axes[0, 0].bar(
            x + (index - 0.5) * width, values, width, color=colors[index], label=names[index]
        )
        axes[0, 0].bar_label(bars, fmt="%.2f", padding=3)
        values = [
            data[model]["speech"][key]["p95_ms"] / 1000 for key in ["common", "general", "guards"]
        ]
        bars = axes[0, 1].bar(x + (index - 0.5) * width, values, width, color=colors[index])
        axes[0, 1].bar_label(bars, fmt="%.2f", padding=3)
        if model == "small":
            failures = data[model]["speech"]["guards"]["failures"]
            bars[2].set_hatch("///")
            axes[0, 1].text(
                x[2] + width / 2,
                values[2] + 0.22,
                f"{failures} wrong",
                ha="center",
                color="#963022",
                weight="bold",
            )
    axes[0, 0].set(
        title="Median read-only text response",
        ylabel="Seconds",
        xticks=x,
        xticklabels=["Original (45)", "Context (18)", "Quality (30)"],
        ylim=(0, 1.65),
    )
    axes[0, 1].set(
        title="p95 saved-speech decision",
        ylabel="Seconds",
        xticks=x,
        xticklabels=["Familiar (18)", "General (6)", "Guards (6)"],
        ylim=(0, 3.25),
    )
    for ax, values, title, unit in [
        (
            axes[1, 0],
            [data[m]["original"]["peak_mlx_allocation_gb"] for m in ["large", "small"]],
            "Peak MLX allocation",
            "GB; model process high-water mark",
        ),
        (
            axes[1, 1],
            [data[m]["startup"]["preparation_ms"] / 1000 for m in ["large", "small"]],
            "Model preparation (one sample each)",
            "Seconds",
        ),
    ]:
        bars = ax.bar(names, values, color=colors, width=0.5)
        ax.bar_label(bars, fmt="%.2f", padding=3)
        ax.set(title=title, ylabel=unit, ylim=(0, max(values) * 1.23))
    for ax in axes.flat:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=0.17)
        ax.set_axisbelow(True)
    fig.suptitle("Smaller is not automatically better for Dum-E", fontsize=17, weight="bold")
    fig.legend(
        *axes[0, 0].get_legend_handles_labels(), loc="outside lower center", ncol=2, frameon=False
    )
    fig.savefig(args.output, dpi=150)
    plt.close(fig)
    print(args.output)


if __name__ == "__main__":
    main()
