"""F11 (what changed in 2026), F8 (no-filter tail risk), F9 (mechanism tests).

F11 exists to stop the rest of the figure set from being over-read: it is
the honest answer to the question F1 and F4b provoke.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.figures import _style as S

TIME_COL = "datetime_beginning_ept"
LOAD_COL = "dom_load_mw"
CONG_COL = "congestion_price_rt_cluster_mean"
PANEL_5MIN = "analysis_panel_5min.parquet"

BIN_WIDTH = 2000
MIN_SUPPORT = 30  # bins with fewer baseline obs are flagged unsupported


def _rate(cell: dict) -> float:
    """Exceedance as a fraction. An empty bin contributes nothing to a mean.

    Kept apart from the displayed `pct_gt_100`, which is NaN when the bin is
    empty: NaN is right for a line that must break, wrong for a weighted sum
    where the weight is already zero.
    """
    return 0.0 if not cell["n"] else cell["pct_gt_100"] / 100.0


def prepare_f11(panel: pd.DataFrame, *, threshold: float = 100.0) -> dict:
    t = pd.to_datetime(panel[TIME_COL])
    year = t.dt.year
    load = panel[LOAD_COL]

    lo = int(np.floor(load.min() / BIN_WIDTH) * BIN_WIDTH)
    hi = int(np.ceil(load.max() / BIN_WIDTH) * BIN_WIDTH)
    edges = list(range(lo, hi + BIN_WIDTH, BIN_WIDTH))
    labels = [f"{a//1000}-{b//1000} GW" for a, b in zip(edges, edges[1:])]
    binned = pd.cut(load, bins=edges, labels=labels, include_lowest=True)

    years = [str(y) for y in sorted(year.unique())]
    by_year_bin: dict[str, dict[str, dict]] = {}
    for y in years:
        sub = binned[year == int(y)]
        cong = panel.loc[year == int(y), CONG_COL]
        row = {}
        for lab in labels:
            m = (sub == lab).to_numpy()
            # An empty bin is unmeasured, not measured-zero. Reporting 0.0 here
            # would draw 2023 flat along the 24-26 GW bin it never reached,
            # which is the exact misreading this figure exists to prevent.
            row[lab] = {"pct_gt_100": float(100.0 * (cong[m] > threshold).mean())
                                      if m.any() else float("nan"),
                        "n": int(m.sum())}
        by_year_bin[y] = row

    base = years[0]
    base_rate = {lab: _rate(by_year_bin[base][lab]) for lab in labels}
    base_n = {lab: by_year_bin[base][lab]["n"] for lab in labels}
    unsupported = {lab for lab in labels if base_n[lab] < MIN_SUPPORT}

    actual, counterfactual, share = {}, {}, {}
    for y in years:
        row = by_year_bin[y]
        n_tot = sum(c["n"] for c in row.values())
        if not n_tot:
            continue
        act = sum(_rate(c) * c["n"] for c in row.values()) / n_tot
        cf = sum(base_rate[lab] * row[lab]["n"] for lab in labels) / n_tot
        actual[y] = 100.0 * act
        counterfactual[y] = 100.0 * cf
        share[y] = float(100.0 * cf / act) if act > 0 else float("nan")

    return {
        "years": years, "bin_labels": labels, "bin_edges": edges,
        "by_year_bin": by_year_bin,
        "actual_pct": actual, "counterfactual_pct": counterfactual,
        "load_growth_share_pct": share,
        "unsupported_bins": sorted(unsupported),
        "baseline_year": base, "threshold": threshold,
        "n": int(len(panel)),
        "window": f"{t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}",
    }


def plot_f11(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    labels, x = d["bin_labels"], np.arange(len(d["bin_labels"]))
    palette = [S.COLOR["ox"], S.COLOR["bristers"], S.COLOR["dom_zonal"],
               S.COLOR["ashburn_tx1"], S.COLOR["total_lmp"]]
    for i, y in enumerate(d["years"]):
        vals = [d["by_year_bin"][y][lab]["pct_gt_100"] for lab in labels]
        axes[0].plot(x, vals, "o-", color=palette[i % len(palette)], label=y)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    axes[0].set_ylabel(f"P(congestion > ${d['threshold']:.0f}) (%)")
    axes[0].set_title("(a) Same load, different price")
    axes[0].legend(fontsize=8)

    # The baseline year's counterfactual equals its actual by construction
    # (share == 100%), so plotting it invites misreading. Drop it.
    ys = [y for y in d["actual_pct"] if y != d["baseline_year"]]
    xb = np.arange(len(ys), dtype=float)
    axes[1].bar(xb - 0.2, [d["actual_pct"][y] for y in ys], 0.4,
                color=S.COLOR["primary"], label="actual")
    axes[1].bar(xb + 0.2, [d["counterfactual_pct"][y] for y in ys], 0.4,
                color=S.COLOR["system_energy"],
                label=f"counterfactual ({d['baseline_year']} response)")
    for i, y in enumerate(ys):
        axes[1].annotate(f"{d['load_growth_share_pct'][y]:.0f}%",
                         (xb[i], max(d["actual_pct"][y],
                                     d["counterfactual_pct"][y])),
                         ha="center", va="bottom", fontsize=8)
    axes[1].set_xticks(xb)
    axes[1].set_xticklabels(ys)
    axes[1].set_ylabel(f"P(congestion > ${d['threshold']:.0f}) (%)")
    axes[1].set_title("(b) How much does load growth explain?")
    axes[1].legend(fontsize=8)

    fig.suptitle("F11 — What actually changed in 2026", y=0.99)
    footer = S.provenance(source=PANEL_5MIN, n=d["n"], window=d["window"],
                          spec=f"{BIN_WIDTH} MW load bins, "
                               f"{d['baseline_year']} baseline response",
                          resolution="5-min")
    caption = (
        "CAVEAT 1 — the counterfactual share is unreliable in magnitude: "
        f"{d['baseline_year']} barely visited the load levels later years "
        f"reach (bins with fewer than {MIN_SUPPORT} baseline observations, "
        f"flagged unsupported: {', '.join(d['unsupported_bins']) or 'none'}), "
        "so it extrapolates where it has no support. The direction is solid; "
        "the number is not. Panel (a) is the defensible version. "
        f"Panel (b) omits {d['baseline_year']}, whose counterfactual equals "
        "its actual by construction. "
        "CAVEAT 2 — the change is NOT local: it is a step change in January "
        "2026 in both congestion and system energy, and system energy is "
        "locationally uniform across PJM, so a substantial part of the 2026 "
        "escalation is system-wide rather than a data-center-alley "
        "congestion story. The driver is UNIDENTIFIED (cold snap, gas "
        "prices, PJM market-rule changes are all untested) and there is no "
        "non-DOM control pnode in this panel.")
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)
