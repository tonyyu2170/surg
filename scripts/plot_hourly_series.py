"""Hourly DOM load and Loudoun-cluster price over the full hourly panel, as two time series.

Question it answers: what does the hourly data behind section 3.1 of
docs/final_report.md actually look like over time, before any statistics are
run on it? Commissioned by the final-report review of 2026-08-28 (a figure of
load vs time and price vs time under "The data" in section 3.1).

Reads data/interim/analysis_panel.parquet (the hourly DOM panel built by
surg-prep): dom_load_mw, total_lmp_rt_cluster_mean and
congestion_price_rt_cluster_mean. Writes
docs/assets/final_report/hourly__dom_load_and_lmp.png.

Usage: .venv/bin/python scripts/plot_hourly_series.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "interim" / "analysis_panel.parquet"
OUT = ROOT / "docs" / "assets" / "final_report" / "hourly__dom_load_and_lmp.png"

TEAL = "#1E5D70"
ORANGE = "#eb6834"

df = pd.read_parquet(SRC, columns=["datetime_beginning_ept", "dom_load_mw",
                                   "total_lmp_rt_cluster_mean", "congestion_price_rt_cluster_mean"])
df = df.sort_values("datetime_beginning_ept")
t = df["datetime_beginning_ept"]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10.5, 7.2), sharex=True,
                               gridspec_kw={"hspace": 0.12})

ax1.plot(t, df["dom_load_mw"] / 1000, color=TEAL, lw=0.5)
ax1.set_ylabel("DOM zonal load (GW)")
ax1.set_title("The hourly panel behind section 3.1: DOM load (top) and the Loudoun cluster price (bottom)",
              fontsize=11, loc="left")
ax1.text(0.005, 0.95, "(a) hourly metered load for the Dominion zone", transform=ax1.transAxes,
         va="top", fontsize=9, color="0.3")

ax2.plot(t, df["total_lmp_rt_cluster_mean"], color=TEAL, lw=0.5, label="total LMP, cluster mean")
ax2.plot(t, df["congestion_price_rt_cluster_mean"], color=ORANGE, lw=0.5, alpha=0.9,
         label="congestion component, cluster mean")
ax2.set_yscale("symlog", linthresh=50)
ax2.set_yticks([-100, 0, 50, 100, 500, 1000, 4000])
ax2.set_yticklabels(["-$100", "$0", "$50", "$100", "$500", "$1,000", "$4,000"])
ax2.set_ylabel("$/MWh (symlog scale)")
ax2.text(0.005, 0.95, "(b) real-time price averaged over the six 500 kV Loudoun nodes", transform=ax2.transAxes,
         va="top", fontsize=9, color="0.3")
ax2.legend(loc="lower left", frameon=False, fontsize=9, ncol=2)
ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
for ax in (ax1, ax2):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color="0.9", lw=0.6)
fig.text(0.01, 0.005,
         f"PJM Data Miner 2, hourly, {t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}. "
         "Prices are the mean of LOUDOUN, PLEASANT VIEW, GOOSECRE, BRAMBLET, MOSBY and SKFFSCRK; the symlog axis is linear\n"
         "between -$50 and $50 and logarithmic beyond, so both the everyday $20 to $60 range and the $1,000-plus spikes are visible.",
         fontsize=7.5, color="0.35", va="bottom")
fig.subplots_adjust(left=0.08, right=0.99, top=0.94, bottom=0.13)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=160)
print(f"wrote {OUT}")
