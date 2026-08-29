"""Schematic of PJM's two-step operating reserve demand curve (ORDC).

Question it answers: what does "a $850 step followed by a $300 step on every
reserve demand curve" look like? Commissioned by the final-report review of
2026-08-27 for docs/final_report.md section 0 ("How PJM prices form"). The
PJM reserve-shortage paper (docs/reference/papers/) has no figure of the
curve, so this draws it from PJM Manual 11 section 4.3.3 (Rev. 137):
Step 1 = $850/MWh for every MW short of the reliability requirement,
Step 2 = $300/MWh for the next 190 MW, zero beyond. Reads no data; the
requirement R is placed at an illustrative position on the axis.

Usage: .venv/bin/python scripts/plot_ordc.py
Writes docs/assets/final_report/ordc_two_step.png
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parents[1] / "docs" / "assets" / "final_report" / "ordc_two_step.png"

R = 1000.0          # illustrative requirement position on the x axis
STEP2 = 190.0       # width of step 2 in MW (M11 4.3.3)
XMAX = R + STEP2 + 400

fig, ax = plt.subplots(figsize=(9, 4.6))
ax.fill_between([0, R], 0, 850, color="#1E5D70", alpha=0.18, lw=0)
ax.fill_between([R, R + STEP2], 0, 300, color="#1E5D70", alpha=0.35, lw=0)
ax.plot([0, R], [850, 850], color="#1E5D70", lw=3)
ax.plot([R, R], [850, 300], color="#1E5D70", lw=3)
ax.plot([R, R + STEP2], [300, 300], color="#1E5D70", lw=3)
ax.plot([R + STEP2, R + STEP2], [300, 0], color="#1E5D70", lw=3)
ax.plot([R + STEP2, XMAX], [0, 0], color="#1E5D70", lw=3)

ax.annotate("Step 1: $850/MWh\nevery MW short of the requirement\nis valued at this penalty factor",
            xy=(R / 2, 850), xytext=(R / 2, 620), ha="center", va="top", fontsize=10)
ax.annotate("Step 2: $300/MWh\nthe next 190 MW", xy=(R + STEP2 / 2, 300),
            xytext=(R + STEP2 / 2 + 60, 470), ha="left", va="bottom", fontsize=10,
            arrowprops={"arrowstyle": "-", "color": "0.4", "lw": 0.8})
ax.annotate("Above R + 190 MW:\nno reserve penalty\nin the price",
            xy=(R + STEP2 + 40, 0), xytext=(R + STEP2 + 40, 60), ha="left", va="bottom", fontsize=10)

ax.set_xlim(0, XMAX)
ax.set_ylim(0, 950)
ax.set_xticks([0, R, R + STEP2])
ax.set_xticklabels(["0", "R\n(reliability requirement)", "R + 190 MW"])
ax.set_yticks([0, 300, 850])
ax.set_yticklabels(["$0", "$300", "$850"])
ax.set_xlabel("Reserve MW held")
ax.set_ylabel("Reserve penalty factor ($/MWh)")
ax.set_title("PJM's operating reserve demand curve: the same two steps on every reserve product")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.text(0.01, 0.01,
         "Schematic from PJM Manual 11 section 4.3.3 (Rev. 137). The curve is identical for Synchronized, Primary and\n"
         "30-minute reserve, RTO and Mid-Atlantic/Dominion sub-zone; only R differs. When reserves fall short, the penalty\n"
         "enters the system energy component of every PJM LMP (PJM reserve-shortage pricing paper, 2023).",
         fontsize=8, color="0.35", va="bottom")
fig.tight_layout(rect=(0, 0.12, 1, 1))
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=200)
print(f"wrote {OUT}")
