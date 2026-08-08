"""Shared style for the sub-q1 report figure set.

Palette harvested from the pre-loss figure script; the 7-slot light-mode
order was validated colorblind-safe.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLOR = {
    "primary": "#2a78d6",       # congestion, Loudoun cluster
    "ox": "#008300",            # control
    "bristers": "#1baf7a",      # control
    "total_lmp": "#eb6834",     # total LMP, Loudoun cluster
    "dom_zonal": "#4a3aa7",     # zonal aggregate
    "ashburn_tx1": "#e34948",   # distribution-side (flagged anomaly)
    "ashburn_tx2": "#eda100",   # distribution-side
    "system_energy": "#6b6b6b", # system energy price
    "load": "#0b0b0b",          # load level
}

NICE = {
    "primary": "Congestion (Loudoun cluster)",
    "total_lmp": "Total LMP (Loudoun cluster)",
    "system_energy": "System energy price",
    "ox": "OX (control)",
    "bristers": "BRISTERS (control)",
    "skffscrk": "SKFFSCRK (control)",
    "dom_zonal": "DOM zonal",
    "ashburn_tx1": "Ashburn TX1",
    "ashburn_tx2": "Ashburn TX2",
}

GRID = "#d8d7d2"
MUTED = "#52514e"
INK = "#0b0b0b"

# Disclosure required on any figure resting on the zonal load aggregate.
ZONAL_DISCLOSURE = (
    "DOM load is a zonal aggregate: individual facilities may swing while "
    "the aggregate smooths. This is structural — DOM resolves to a single "
    "load_area and per-customer load is confidential."
)

# Required on figures touching the Z tail.
ARTIFACT_NOTE = (
    "~4 extreme reversion excursions (>1,500 MW) are probably artifacts "
    "(they moved system energy $0–4 where a confirmed 1,479 MW trip moved "
    "it $81); the broader spike class is not established as artifactual "
    "and is not filtered."
)

plt.rcParams.update({
    "font.size": 11,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.7,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})


def provenance(*, source: str, n: int, window: str, spec: str,
               resolution: str) -> str:
    """Build the mandatory provenance footer.

    `resolution` is required and must be non-empty: every figure states
    hourly vs 5-min explicitly.
    """
    if not resolution:
        raise ValueError("resolution must be stated explicitly on every figure")
    return (f"Source: {source} | n={n:,} | {window} | spec: {spec} | "
            f"resolution: {resolution}")


def finish(fig, out_path: Path, *, footer: str, caption: str = "") -> None:
    """Attach footer (and optional caption) and write the PNG."""
    text = footer if not caption else f"{caption}\n{footer}"
    fig.text(0.01, 0.005, text, fontsize=7, color=MUTED,
             ha="left", va="bottom", wrap=True)
    bottom = 0.16 if caption else 0.09
    fig.subplots_adjust(bottom=bottom)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")


def excludes_zero(lo: float, hi: float) -> bool:
    return lo > 0 or hi < 0


def forest(ax, rows, xlabel: str, title: str | None = None,
           vline: float = 0.0) -> None:
    """Horizontal point-and-CI plot.

    `rows` is a list of (label, point, lo, hi, color) tuples, drawn top-down.
    A CI excluding `vline` is drawn with a filled marker, one spanning it hollow.
    """
    ys = list(range(len(rows)))[::-1]
    for y, (label, point, lo, hi, color) in zip(ys, rows):
        solid = excludes_zero(lo - vline, hi - vline)
        ax.plot([lo, hi], [y, y], color=color, lw=2, solid_capstyle="round")
        ax.plot([point], [y], marker="o", ms=7, color=color,
                markerfacecolor=color if solid else "white", zorder=3)
    ax.axvline(vline, color=MUTED, lw=1, ls="--")
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlabel(xlabel)
    if title:
        ax.set_title(title)
