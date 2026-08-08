"""Shared style for the sub-q1 report figure set.

Palette harvested from the pre-loss figure script; the 7-slot light-mode
order was validated colorblind-safe.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

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
    # No figure in this set uses mathtext, and captions are full of literal
    # dollar amounts ("$9.56 / $8.81") that would otherwise be parsed as
    # math-mode spans and rendered garbled.
    "text.parse_math": False,
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


def _wrap_to_figure(fig, artist, raw: str, limit_px: float) -> None:
    """Hard-wrap `raw` onto `artist` until it renders inside `limit_px`.

    matplotlib's own `wrap=True` overshoots -- an F3-length caption rendered
    ~32px past the right edge of an 11in figure, clipping the last word of a
    line. Wrapping explicitly and verifying against the measured extent is
    the only version that provably fits. Paragraphs already separated by
    newlines (caption above footer) are wrapped independently so the break
    between them survives.
    """
    renderer = fig.canvas.get_renderer()
    paras = raw.split("\n")
    artist.set_text(raw)
    fig.canvas.draw()
    widest = artist.get_window_extent(renderer).width
    if widest <= limit_px:
        return
    # First guess proportionally from the measured overshoot, then tighten:
    # character counts are only an approximation of width in a proportional
    # font, so the measurement -- not the guess -- decides when to stop.
    ncols = max(20, int(len(max(paras, key=len)) * limit_px / widest))
    for _ in range(12):
        artist.set_text("\n".join(
            "\n".join(textwrap.wrap(p, ncols)) if p else p for p in paras))
        fig.canvas.draw()
        if artist.get_window_extent(renderer).width <= limit_px:
            return
        ncols = int(ncols * 0.95)


def finish(fig, out_path: Path, *, footer: str, caption: str = "") -> None:
    """Attach footer (and optional caption) and write the PNG.

    The bottom margin is measured from the rendered text rather than fixed:
    captions in this set run to several wrapped lines, and a constant margin
    lets them overlap the axes.
    """
    text = footer if not caption else f"{caption}\n{footer}"
    t = fig.text(0.01, 0.005, text, fontsize=7, color=MUTED,
                 ha="left", va="bottom")
    fig.canvas.draw()  # realise the renderer before measuring
    renderer = fig.canvas.get_renderer()
    fig_w = fig.get_window_extent().width
    _wrap_to_figure(fig, t, text, fig_w * 0.98)  # 0.01 left inset, matched right
    frac = t.get_window_extent(renderer).height / fig.get_window_extent().height
    # tight_layout's `rect` reserves the bottom band for the caption and lays
    # the axes out inside the remainder, accounting for tick labels and axis
    # labels -- which subplots_adjust cannot do, since it positions the axes
    # box while tick labels render below it.
    fig.tight_layout(rect=(0, min(frac + 0.03, 0.6), 1, 1))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200)


def symlog_axis(ax, *, linthresh: float = 1.0, label: str | None = None) -> None:
    """Put `ax` on a symlog y-scale with plain-decimal tick labels.

    Both halves matter. The symlog scale keeps near-zero medians visible
    against tail values two or three orders of magnitude larger, which a
    linear axis would flatten into a baseline smear.

    The formatter is not cosmetic. matplotlib's default log/symlog tick
    formatter emits mathtext ("$\\mathdefault{10^{2}}$"), and this module
    sets text.parse_math=False so literal dollar amounts in captions
    survive -- so those tick labels render as that raw string instead of an
    exponent. Plain decimals sidestep it entirely, and for prices they read
    better than powers of ten anyway.
    """
    ax.set_yscale("symlog", linthresh=linthresh)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    if label:
        ax.set_ylabel(label)


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
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel(xlabel)
    if title:
        ax.set_title(title)
