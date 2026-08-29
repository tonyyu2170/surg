"""Node power over time for the rs-7943457 GPU telemetry sessions used in section 3.12.

Question it answers: what does one 8-GPU training node's power draw look like
in the time domain (the periodogram in scripts/aidc_psd.py is the frequency
domain)? Commissioned by the final-report review of 2026-08-28 (a load vs
time figure under "The project's own spectrum" in section 3.12 of
docs/final_report.md).

Reads the four baseline sessions in data/raw/aidc_workload/ (gitignored,
re-downloadable from the rs-7943457 GitHub repository), sums the eight
gpuN_power_W channels into node power, and plots each session in full (left)
and a 60-second window from its steady state (right). Writes
docs/assets/final_report/aidc__node_power_timeseries.png.

Usage: .venv/bin/python scripts/plot_aidc_timeseries.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "aidc_workload"
OUT = ROOT / "docs" / "assets" / "final_report" / "aidc__node_power_timeseries.png"
TEAL = "#1E5D70"

SESSIONS = [
    ("B200 node, diffusion training", "b200_diffusion_baseline.csv"),
    ("H100 node, diffusion training", "h100_diffusion_baseline.csv"),
    ("B200 node, LLM fine-tuning (batch 16)", "b200_llm_baseline.csv"),
    ("H100 node, LLM fine-tuning (batch 16)", "h100_llm_baseline.csv"),
]
ZOOM_S = 60.0


def load(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    ts = pd.to_datetime(df["timestamp"])
    cols = [c for c in df.columns if c.endswith("_power_W") and c.startswith("gpu")]
    node = df[cols].sum(axis=1)
    sec = (ts - ts.iloc[0]).dt.total_seconds()
    return pd.Series(node.values, index=sec.values)


fig, axes = plt.subplots(len(SESSIONS), 2, figsize=(11, 10), gridspec_kw={"width_ratios": [2.2, 1], "hspace": 0.5, "wspace": 0.18})
for (label, fname), (ax_full, ax_zoom) in zip(SESSIONS, axes):
    s = load(RAW / fname)
    start = 0.4 * s.index[-1]
    z = s[(s.index >= start) & (s.index < start + ZOOM_S)]
    ax_full.plot(s.index / 60, s.values / 1000, color=TEAL, lw=0.5)
    ax_full.axvspan(start / 60, (start + ZOOM_S) / 60, color=TEAL, alpha=0.12, lw=0)
    ax_full.set_title(label, fontsize=10, loc="left")
    ax_full.set_ylabel("node power (kW)")
    ax_full.set_xlabel("minutes since session start")
    ax_zoom.plot(z.index - start, z.values / 1000, color=TEAL, lw=0.9)
    ax_zoom.set_title("60-second window (shaded at left)", fontsize=9, loc="left", color="0.3")
    ax_zoom.set_xlabel("seconds")
    ax_zoom.set_xlim(0, ZOOM_S)
    for ax in (ax_full, ax_zoom):
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.grid(axis="y", color="0.9", lw=0.6)
fig.suptitle("Power drawn by one 8-GPU training node, summed over its eight GPUs (rs-7943457 telemetry)",
             fontsize=11, x=0.01, ha="left")
fig.text(0.01, 0.005,
         "Per-GPU power sensors polled every 20 ms (the sensor itself refreshes about every 103 ms). Each session is about 15 minutes.\n"
         "The rise-and-fall cycle every 8 to 16 seconds is the training loop's duty cycle; the cycle is slow, but each drop and recovery inside it is a step of about a second (scripts/aidc_edges.py).",
         fontsize=7.5, color="0.35", va="bottom")
fig.subplots_adjust(left=0.07, right=0.99, top=0.93, bottom=0.08)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=150)
print(f"wrote {OUT}")
