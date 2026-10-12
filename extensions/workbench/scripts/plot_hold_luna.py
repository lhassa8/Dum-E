"""Plot the recorded contact-hold and alternating Luna transport measurements."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

root = Path(__file__).resolve().parents[1]
evidence = json.loads((root / "docs/hold-luna-evidence.json").read_text())
figure, axes = plt.subplots(1, 2, figsize=(11, 4.4), constrained_layout=True)
colors = ["#d55e00", "#e69f00", "#009e73"]
for mode, label, color in zip(
    ["baseline", "contact_only", "fixed"],
    ["Original: slips to table", "Contact correction: arm sags", "Final: contact + gravity hold"],
    colors,
):
    rows = evidence["hold_plot"][mode]
    axes[0].plot([r["seconds"] for r in rows], [r["height_m"] * 1000 for r in rows],
                 label=label, color=color, linewidth=2)
axes[0].axhline(130, color="#777777", linestyle=":", label="Unchanged retention gate")
axes[0].set(xlabel="Simulated seconds after Stop", ylabel="Screwdriver height (mm)",
            title="The gripper now holds through a long pause", ylim=(0, 145))
axes[0].legend(fontsize=8, loc="lower left")
axes[0].grid(alpha=0.2)

for index, transport in enumerate(["exec", "session"]):
    values = [r["elapsed_ms"] / 1000 for r in evidence["paired"]["rows"]
              if r["transport"] == transport]
    axes[1].scatter(index + np.linspace(-0.12, 0.12, len(values)), values,
                    color=["#d55e00", "#009e73"][index], s=30)
    median = float(np.median(values))
    axes[1].plot([index - 0.22, index + 0.22], [median, median], color="black", linewidth=2)
    axes[1].text(index + 0.23, median, f"{median:.2f}s", fontsize=9, va="center")
axes[1].set(xticks=[0, 1], xticklabels=["Fresh CLI", "Persistent connection"],
            ylabel="Complete text interpretation (seconds)", ylim=(0, 7.5),
            xlim=(-0.4, 1.65), title="Luna: faster median, cloud delays remain")
axes[1].grid(axis="y", alpha=0.2)
axes[1].text(0.01, 0.98, "10 calls per path · alternating paired requests\n"
             "No speech or motion included", transform=axes[1].transAxes,
             fontsize=8, va="top")
figure.savefig(root / "docs/hold-luna-comparison.png", dpi=180)
plt.close(figure)
