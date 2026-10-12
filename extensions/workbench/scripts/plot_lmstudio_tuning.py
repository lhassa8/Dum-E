"""Plot matched read-only dialogue timings without claiming live speech latency."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.evidence.read_text())
    before, after = data["matched_before"], data["matched_after"]
    if before["fixture_sha256"] != after["fixture_sha256"]:
        parser.error("The two runs must use the same fixture")
    first = {(r["repeat"], r["name"]): r for r in before["rows"]}
    second = {(r["repeat"], r["name"]): r for r in after["rows"]}
    if first.keys() != second.keys():
        parser.error("The runs must contain identical case/repeat pairs")
    keys = list(first)
    old = np.array([first[k]["elapsed_ms"] for k in keys]) / 1000
    new = np.array([second[k]["elapsed_ms"] for k in keys]) / 1000
    y = np.arange(len(keys))
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.hlines(y, new, old, color="#d5dde5", linewidth=2)
    ax.scatter(old, y, color="#c0752b", label="Previous load", s=45, zorder=3)
    ax.scatter(new, y, color="#087b72", label="Explicit GPU / single slot", s=45, zorder=3)
    ax.set_yticks(y, [k[1].replace("_", " ") for k in keys])
    ax.invert_yaxis()
    ax.set_xlim(left=0)
    ax.set_xlabel("Complete read-only text response (seconds)")
    ax.set_title("Same Bonsai model, same 15 requests, different load settings", loc="left", pad=18)
    ax.grid(axis="x", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="lower right")
    fig.text(
        0.02,
        0.015,
        "Sequential before/after samples; speech, motion and model loading excluded. "
        "GPU offload and concurrency changed together.",
        fontsize=9,
        color="#465363",
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(args.output, dpi=170)
    plt.close(fig)


if __name__ == "__main__":
    main()
