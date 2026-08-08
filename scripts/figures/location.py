"""F7 (location) and F10 (the 2024-07-10 NERC event).

F7 is computed on the window common to all pnodes. Ashburn TX1 enters the
hourly panel only on 2024-08-06; because congestion escalated sharply in
2026, comparing Ashburn's late window against other pnodes' full-panel
statistics inflates the locational contrast. See the plan's "Critical
context" section.

SKFFSCRK is *inside* the 6-node cluster it is compared against, which
decisions.md:4275 rules a deliberate asymmetry -- pooling a comparison node
into the cluster it is compared against would contaminate every
cluster-based regression target, so the pooling stays as pre-registered.
What that ruling requires instead is disclosure: part of the cluster's
correlation with SKFFSCRK is self-correlation, so a held-out 5-node cluster
is reported beside the primary 6-node one.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.figures import _style as S

TIME_COL = "datetime_beginning_ept"
PANEL_HOURLY = "analysis_panel.parquet"
PANEL_5MIN = "analysis_panel_5min.parquet"

# SKFFSCRK is pnode id 1356178201 (confirmed by matching the design spec's
# $96.13 p99 / 0.96% exceedance on the full panel -- reproduced at $95.92 /
# 0.96% on the rebuilt panel, and only by congestion_price_rt, never
# total_lmp_rt, which closes the unnamed-variable question at
# decisions.md:4286).
SKFFSCRK = "1356178201"
CLUSTER_6 = ["35010365", "35010371", "1356178171",
             "1356178181", "1356178195", "1356178201"]
HELD_OUT_IDS = [p for p in CLUSTER_6 if p != SKFFSCRK]
HELD_OUT_KEY = "cluster_mean_ex_skffscrk"

F7_PNODES = {
    "ashburn_tx1": "Ashburn TX1",
    "cluster_mean": "Loudoun cluster (6-node)",
    HELD_OUT_KEY: "Loudoun cluster (5-node, held out)",
    "ox": "OX (control)",
    "bristers": "BRISTERS (control)",
    SKFFSCRK: "SKFFSCRK (inside cluster)",
    "dom_zonal": "DOM zonal",
}
REFERENCE = "ashburn_tx1"


def _col(p: str) -> str:
    return f"congestion_price_rt_{p}"


def prepare_f7(panel: pd.DataFrame) -> dict:
    panel = panel.copy()
    # Derived, not stored: cluster_mean on the panel is the 6-node mean
    # (verified to floating-point equality), so the held-out series has to be
    # rebuilt from the five remaining pnodes.
    panel[_col(HELD_OUT_KEY)] = panel[
        [_col(p) for p in HELD_OUT_IDS]].mean(axis=1)

    t = pd.to_datetime(panel[TIME_COL])
    have = panel[_col(REFERENCE)].notna()
    start, end = t[have].min(), t[have].max()
    common = panel[(t >= start) & (t <= end)]

    rows = {}
    for p, label in F7_PNODES.items():
        s_all, s_com = panel[_col(p)], common[_col(p)]
        full_ok = s_all.notna().sum() == len(panel)
        rows[p] = {
            "label": label,
            "p99_common": float(s_com.quantile(0.99)),
            "pct_gt_100_common": float(100.0 * (s_com > 100).mean()),
            "n_common": int(s_com.notna().sum()),
            "p99_full": float(s_all.quantile(0.99)) if full_ok else None,
            "pct_gt_100_full": (float(100.0 * (s_all > 100).mean())
                                if full_ok else None),
        }

    sk = common[_col(SKFFSCRK)]
    primary = float(common[_col("cluster_mean")].corr(sk))
    held_out = float(common[_col(HELD_OUT_KEY)].corr(sk))

    labels = list(F7_PNODES)
    corr = common[[_col(p) for p in labels]].corr()
    return {
        "rows": rows,
        "common_window_start": f"{start:%Y-%m-%d}",
        "common_window_end": f"{end:%Y-%m-%d}",
        "n_common": int(len(common)),
        "n_full": int(len(panel)),
        # The disclosure decisions.md:4281 requires, carried as numbers rather
        # than prose so the caption cannot drift from what was computed.
        "self_correlation": {"primary": primary, "held_out": held_out,
                             "inflation": primary - held_out},
        "correlation": {"labels": labels, "matrix": corr.to_numpy().tolist()},
        "window": f"{t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}",
    }


def prepare_f7_annotation(d: dict) -> str:
    sc = d["self_correlation"]
    return (f"SKFFSCRK sits inside the 6-node cluster, so part of their "
            f"r={sc['primary']:.3f} is self-correlation; holding it out gives "
            f"r={sc['held_out']:.3f} (inflation +{sc['inflation']:.3f})")


def plot_f7(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 6),
                             gridspec_kw={"width_ratios": [1.25, 1]})
    keys = list(d["rows"])
    labels = [d["rows"][k]["label"] for k in keys]
    x = np.arange(len(keys), dtype=float)

    ax = axes[0]
    ax.bar(x - 0.2, [d["rows"][k]["pct_gt_100_common"] for k in keys], 0.4,
           color=S.COLOR["primary"], label="% > $100 (common window)")
    ax.set_ylabel("% of hours > $100")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax2 = ax.twinx()
    ax2.plot(x, [d["rows"][k]["p99_common"] for k in keys], "o",
             color=S.COLOR["ashburn_tx1"], label="p99 ($)")
    ax2.set_ylabel("p99 congestion ($)")
    ax2.grid(False)
    ax.set_title("(a) Exceedance and p99 by pnode\n(common window)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=8)

    m = np.array(d["correlation"]["matrix"], float)
    im = axes[1].imshow(m, vmin=-1, vmax=1, cmap="RdBu_r")
    axes[1].set_xticks(range(len(labels)))
    axes[1].set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    axes[1].set_yticks(range(len(labels)))
    axes[1].set_yticklabels(labels, fontsize=7)
    axes[1].grid(False)
    for i in range(len(labels)):
        for j in range(len(labels)):
            axes[1].text(j, i, f"{m[i, j]:.2f}", ha="center", va="center",
                         fontsize=6,
                         color="white" if abs(m[i, j]) > 0.6 else S.INK)
    fig.colorbar(im, ax=axes[1], shrink=0.8)
    axes[1].set_title("(b) Congestion correlation\n(common window)")

    fig.suptitle("F7 — Location matters even where volatility does not", y=0.99)
    footer = S.provenance(
        source=PANEL_HOURLY, n=d["n_common"],
        window=f"{d['common_window_start']} to {d['common_window_end']}",
        spec="common-window pnode comparison", resolution="hourly")
    caption = (
        f"Computed on the window common to all pnodes "
        f"({d['common_window_start']} → {d['common_window_end']}, "
        f"n={d['n_common']:,} of {d['n_full']:,}) because Ashburn TX1 enters "
        f"the panel only on {d['common_window_start']}; comparing Ashburn's "
        f"late window against other pnodes' full-panel statistics would "
        f"inflate the contrast, since congestion escalated sharply in 2026. "
        + prepare_f7_annotation(d) + ".")
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)


LOAD_COL = "dom_load_mw"
ENERGY_COL = "system_energy_price_rt_cluster_mean"
CONG_COL = "congestion_price_rt_cluster_mean"
STEP = pd.Timedelta(minutes=5)
# decisions.md:4150 screens load-data artifacts at > 1,500 MW. An excursion
# counts as reverting when the next interval hands most of the move back --
# 0.65 separates the panel's three cleanly (each gives back >= 89%) from the
# 2024-07-10 trip, which gives back 2%.
REVERSION_MW = 1500.0
REVERSION_FRAC = 0.65


def _ordered(panel: pd.DataFrame) -> pd.DataFrame:
    p = panel.assign(_t=pd.to_datetime(panel[TIME_COL]))
    return p.sort_values("_t").reset_index(drop=True)


def _five_minute_delta(p: pd.DataFrame) -> pd.Series:
    """Load change per row, blanked where the rows are not 5 minutes apart.

    The panel has holes -- 2024-07-10 21:45 is followed by 2024-07-11 03:35 --
    and a bare .diff() reads that 5h50m overnight decline as a single
    -4,933 MW step, larger than anything real in 3.4 years.
    """
    return p[LOAD_COL].diff().where(p["_t"].diff() == STEP)


def _reversion_screen(p: pd.DataFrame, delta: pd.Series) -> list[dict]:
    """Excursions past REVERSION_MW that the next interval gives straight back.

    That snap-back is the artifact signature: load cannot fall 1,600 MW and
    return five minutes later, so these are reporting glitches rather than
    events. A real trip stays down, which is what makes F10 the positive
    control for this screen.
    """
    nxt = delta.shift(-1)
    reverting = (delta < -REVERSION_MW) & (nxt > -delta * REVERSION_FRAC)
    energy = p[ENERGY_COL]
    return [{
        "time": p["_t"].iloc[i].to_pydatetime(),
        "drop_mw": float(delta.iloc[i]),
        "rebound_mw": float(nxt.iloc[i]),
        "energy_response": float(energy.iloc[i - 1] - energy.iloc[i]),
    } for i in p.index[reverting]]


def prepare_f10(panel: pd.DataFrame, *, event_date: str = "2024-07-10",
                hours: int = 6) -> dict:
    p = _ordered(panel)
    delta = _five_minute_delta(p)
    energy = p[ENERGY_COL]

    on_day = ((p["_t"] >= f"{event_date} 00:00")
              & (p["_t"] < f"{event_date} 23:59"))
    day_delta = delta.where(on_day)
    if not day_delta.notna().any():
        raise ValueError(
            f"no contiguous five-minute interval on {event_date}; the date is "
            "outside the panel, or that day holds a single row")
    i = int(day_delta.idxmin())

    centre = p["_t"].iloc[i]
    lo = centre - pd.Timedelta(hours=hours)
    hi = centre + pd.Timedelta(hours=hours)
    win = p[(p["_t"] >= lo) & (p["_t"] <= hi) & on_day]

    before, after = float(energy.iloc[i - 1]), float(energy.iloc[i])
    rebound = float(delta.shift(-1).iloc[i])
    return {
        "times": [x.to_pydatetime() for x in win["_t"]],
        "load": win[LOAD_COL].tolist(),
        "energy": win[ENERGY_COL].tolist(),
        "congestion": win[CONG_COL].tolist(),
        "event_time": centre.to_pydatetime(),
        "drop_mw": float(delta.iloc[i]),
        "energy_before": before, "energy_after": after,
        "energy_drop_dollars": before - after,
        # The event's own reversion test, reported rather than assumed: if the
        # trip ever did snap back, that would be a finding, not a filter.
        "event_reverts": bool(rebound > -delta.iloc[i] * REVERSION_FRAC),
        "screen": _reversion_screen(p, delta),
        "event_date": event_date,
        # The nominal window is +/-6h, but the panel's own holes truncate it,
        # so the span is reported as measured.
        "window_start": f"{win['_t'].min():%Y-%m-%d %H:%M}",
        "window_end": f"{win['_t'].max():%Y-%m-%d %H:%M}",
        "n": int(len(win)),
    }


def prepare_f10_annotation(d: dict) -> str:
    """State the screen from what was computed, never from a stored number."""
    s = d["screen"]
    if not s:
        return ("No reverting excursion past "
                f"{REVERSION_MW:,.0f} MW appears in this panel, so the screen "
                "has no comparator here")
    worst = max(abs(r["energy_response"]) for r in s)
    up = sum(1 for r in s if r["energy_response"] < 0)
    return (f"The {len(s)} comparably sized excursions in the panel all snap "
            f"back within one interval and move system energy by at most "
            f"${worst:,.2f}"
            + (f", upward in {up} of them" if up else "")
            + f", where this non-reverting trip moved it "
              f"${d['energy_drop_dollars']:,.2f}")


def plot_f10(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(d["times"], d["load"], color=S.COLOR["load"], lw=1.6)
    axes[0].axvline(d["event_time"], color=S.COLOR["ashburn_tx1"], ls="--", lw=1.2)
    axes[0].set_ylabel("DOM load (MW)")
    axes[0].set_title(f"(a) Load: {d['drop_mw']:,.0f} MW in five minutes")

    axes[1].plot(d["times"], d["energy"], color=S.COLOR["system_energy"],
                 lw=1.6, label="system energy")
    axes[1].plot(d["times"], d["congestion"], color=S.COLOR["primary"],
                 lw=1.2, label="congestion")
    axes[1].axvline(d["event_time"], color=S.COLOR["ashburn_tx1"], ls="--", lw=1.2)
    axes[1].set_ylabel("Price ($)")
    axes[1].set_xlabel("Time (EPT)")
    axes[1].legend()
    axes[1].set_title(
        f"(b) System energy ${d['energy_before']:.2f} → ${d['energy_after']:.2f}")

    fig.suptitle(f"F10 — The {d['event_date']} data-center trip", y=0.98)
    footer = S.provenance(source=PANEL_5MIN, n=d["n"],
                          window=f"{d['window_start']} to {d['window_end']}",
                          spec="event study", resolution="5-min")
    caption = (
        "The one place in the panel where a large, externally verified load "
        "loss and a large price response coincide, and the load stays down "
        "rather than snapping back. It doubles as the positive control for "
        "the load-artifact screen: "
        + prepare_f10_annotation(d) + ".")
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)
