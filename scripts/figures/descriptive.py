"""Descriptive figures.

F1: the premise -- load grew, ramp volatility did not.
F2: congestion tracks load level, not ramp volatility.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from scripts.figures import _style as S

PANEL_5MIN = "analysis_panel_5min.parquet"

Z_COL = "dom_load_gradient_abs_mw_per_min"
LOAD_COL = "dom_load_mw"
CONG_COL = "congestion_price_rt_cluster_mean"
ENERGY_COL = "system_energy_price_rt_cluster_mean"
TOTAL_COL = "total_lmp_rt_cluster_mean"
TIME_COL = "datetime_beginning_ept"


def prepare_f1(monthly_json: Path) -> dict:
    d = json.loads(Path(monthly_json).read_text())
    rows = d["rows"]
    months = [r["month"] for r in rows]
    load = np.array([r["mean_load_mw"] for r in rows], float)
    p90 = np.array([r["ramp_p90_mw_per_min"] for r in rows], float)
    pct = np.array([r["ramp_p90_pct_of_load"] for r in rows], float)
    x = np.arange(len(rows), dtype=float)

    # p90 can be exactly flat (that's panel (b)'s premise); scipy returns a
    # nan p-value for zero-variance input (divide-by-zero in the standard
    # error), even though "no variance" is itself definitive evidence of no
    # trend. Report that as slope=0, p=1 rather than propagating a nan.
    if np.ptp(p90) == 0:
        ols_slope, ols_p = 0.0, 1.0
        rho, rho_p = 0.0, 1.0
    else:
        ols = stats.linregress(x, p90)
        ols_slope, ols_p = float(ols.slope), float(ols.pvalue)
        rho, rho_p = stats.spearmanr(x, p90)
        rho, rho_p = float(rho), float(rho_p)

    year = np.array([int(m[:4]) for m in months])
    mon = np.array([int(m[5:7]) for m in months])
    first, last = year.min(), year.max()

    # Load growth must be LIKE-FOR-LIKE. Comparing the first month to the
    # last (Feb 2023 vs Jun 2026) mixes a winter shoulder month with an early
    # summer one and reports +37.4% where the real growth is +28.0%. Average
    # only over the calendar months present in EVERY year.
    common = sorted({int(m) for m in mon if all(
        ((year == y) & (mon == m)).any() for y in range(first, last + 1))})
    if not common:
        raise ValueError("no calendar month is present in every year; "
                          "cannot compute a like-for-like growth rate")

    def _block(y):
        sel = (year == y) & np.isin(mon, common)
        return float(load[sel].mean())

    growth = 100.0 * (_block(last) - _block(first)) / _block(first)

    return {
        "months": months, "n_months": len(rows),
        "mean_load_mw": load, "ramp_p90": p90, "ramp_p90_pct": pct,
        "load_growth_pct": growth,
        "growth_basis_months": common,
        "growth_first_year": int(first), "growth_last_year": int(last),
        "mean_load_by_year": {int(y): _block(y) for y in range(first, last + 1)},
        "ramp_p90_min": float(p90.min()), "ramp_p90_max": float(p90.max()),
        "ramp_pct_first_year": float(pct[year == first].mean()),
        "ramp_pct_last_year": float(pct[year == last].mean()),
        "ols_slope_per_month": ols_slope,
        "ols_p_value": ols_p,
        "spearman_rho": rho, "spearman_p_value": rho_p,
        "n_obs": int(sum(r["n"] for r in rows)),
        "window": f"{months[0]} to {months[-1]}",
    }


def plot_f1(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(9, 8.5), sharex=True)
    x = np.arange(d["n_months"])

    axes[0].plot(x, d["mean_load_mw"], color=S.COLOR["load"], lw=1.8)
    axes[0].set_ylabel("Mean DOM load (MW)")
    axes[0].set_title(
        f"(a) Load grew {d['load_growth_pct']:+.1f}% "
        f"({d['growth_first_year']}→{d['growth_last_year']}, like-for-like)")

    axes[1].plot(x, d["ramp_p90"], color=S.COLOR["primary"], lw=1.8)
    axes[1].set_ylabel("Ramp p90 (MW/min)")
    axes[1].set_title(
        f"(b) Ramp volatility did not "
        f"({d['ramp_p90_min']:.1f}–{d['ramp_p90_max']:.1f} MW/min); "
        f"OLS {d['ols_slope_per_month']:+.3f}/mo, p={d['ols_p_value']:.3f}")

    axes[2].plot(x, d["ramp_p90_pct"], color=S.COLOR["total_lmp"], lw=1.8)
    axes[2].set_ylabel("Ramp p90 (% of load)")
    axes[2].set_title(
        f"(c) Normalised against load it fell "
        f"({d['ramp_pct_first_year']:.4f}% → {d['ramp_pct_last_year']:.4f}%)")

    step = max(1, d["n_months"] // 12)
    axes[2].set_xticks(x[::step])
    axes[2].set_xticklabels(d["months"][::step], rotation=45, ha="right")
    fig.suptitle(f"{S.label('F1')} — The premise: load grew, volatility did not", y=0.98)

    footer = S.provenance(source=PANEL_5MIN, n=d["n_obs"], window=d["window"],
                           spec="descriptive, monthly", resolution="5-min")
    basis = ", ".join(str(m) for m in d["growth_basis_months"])
    caption = (f"Spearman ρ={d['spearman_rho']:+.3f}, p={d['spearman_p_value']:.3f}. "
               f"Growth is like-for-like: mean load over the calendar months "
               f"present in every year (months {basis}), "
               f"{d['growth_first_year']} vs {d['growth_last_year']}. "
               f"Comparing the panel's first month to its last would mix "
               f"different seasons and overstate growth. "
               + S.ZONAL_DISCLOSURE)
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)


def _decile_stats(sub: pd.DataFrame, by: str) -> dict:
    # duplicates="drop" can yield fewer than 10 bins when the variable has a
    # point mass (Z has one near zero), so take the labels from the
    # aggregated index rather than assuming ten.
    dec = pd.qcut(sub[by], 10, labels=False, duplicates="drop")
    g = sub.groupby(dec)
    return {
        "decile": [int(k) + 1 for k in g[ENERGY_COL].median().index],
        "energy_median": g[ENERGY_COL].median().tolist(),
        "cong_median": g[CONG_COL].median().tolist(),
        "cong_p95": g[CONG_COL].quantile(0.95).tolist(),
        "mean_load_mw": g[LOAD_COL].mean().tolist(),
        "n": g.size().tolist(),
    }


def prepare_f2(panel: pd.DataFrame) -> dict:
    by_load = _decile_stats(panel, LOAD_COL)
    tercile = pd.qcut(panel[LOAD_COL], 3, labels=False, duplicates="drop")
    top = panel[tercile == 2]
    by_ramp = _decile_stats(top, Z_COL)
    t = pd.to_datetime(panel[TIME_COL])
    return {
        "by_load": by_load,
        "by_ramp_top_tercile": by_ramp,
        "n": int(len(panel)),
        "n_top_tercile": int(len(top)),
        "window": f"{t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}",
    }


def plot_f2(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    L, R = d["by_load"], d["by_ramp_top_tercile"]
    xl, xr = L["decile"], R["decile"]

    axes[0][0].plot(xl, L["energy_median"], "o-", color=S.COLOR["system_energy"])
    axes[0][0].set_title("(a) System energy vs load decile")
    axes[0][0].set_ylabel("Median system energy ($)")

    axes[0][1].plot(xr, R["energy_median"], "o-", color=S.COLOR["system_energy"])
    axes[0][1].set_title(
        f"(b) System energy vs ramp decile\n(top load tercile; "
        f"${min(R['energy_median']):.2f}–${max(R['energy_median']):.2f})")
    # (a) and (b) plot the same quantity, so they share a scale. Left to
    # autoscale, (b) spans only its own ~$4 range and a 10% decline reads as
    # a collapse comparable to (a)'s real $17->$62 climb -- overstating the
    # ramp effect in the direction that flatters the thesis. Shared limits
    # show the true relative magnitude; the exact range is in the title so
    # the compressed view hides nothing.
    axes[0][1].sharey(axes[0][0])

    axes[1][0].plot(xl, L["cong_median"], "o-", color=S.COLOR["primary"],
                    label="median")
    axes[1][0].plot(xl, L["cong_p95"], "s--", color=S.COLOR["ashburn_tx1"],
                    label="p95")
    axes[1][0].set_title("(c) Congestion vs load decile — a switch, not a slope")
    axes[1][0].set_ylabel("Congestion ($)")
    axes[1][0].set_xlabel("Load decile")
    axes[1][0].legend()

    axes[1][1].plot(xr, R["cong_median"], "o-", color=S.COLOR["primary"],
                    label="median")
    axes[1][1].plot(xr, R["cong_p95"], "s--", color=S.COLOR["ashburn_tx1"],
                    label="p95")
    axes[1][1].set_title("(d) Congestion vs ramp decile\n(top load tercile)")
    axes[1][1].set_xlabel("Ramp decile")
    axes[1][1].legend()

    fig.suptitle(f"{S.label('F2')} — Congestion tracks load level, not ramp volatility", y=0.99)
    footer = S.provenance(source=PANEL_5MIN, n=d["n"], window=d["window"],
                          spec="decile descriptive", resolution="5-min")
    caption = (
        f"Right column holds level roughly fixed (top load tercile, "
        f"n={d['n_top_tercile']:,}). Mechanism note: 'load volatility → "
        f"reserve depletion' is UNSUPPORTED (M11 §6/§9). " + S.ZONAL_DISCLOSURE)
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)


def prepare_f3(panel: pd.DataFrame) -> dict:
    t = pd.to_datetime(panel[TIME_COL])
    day = t.dt.floor("D")
    g = panel.groupby(day)
    total = g[TOTAL_COL].median()
    year = t.dt.year
    return {
        # Take the date axis from an aggregated series rather than from
        # g.groups: the axis and the plotted values then provably come from
        # one aggregation, and cannot drift out of order relative to it.
        "dates": [d.to_pydatetime() for d in total.index],
        "total_lmp": total.tolist(),
        "congestion": g[CONG_COL].median().tolist(),
        "system_energy": g[ENERGY_COL].median().tolist(),
        "cong_p90_by_year": {str(y): float(panel.loc[year == y, CONG_COL].quantile(0.90))
                             for y in sorted(year.unique())},
        "energy_p90_by_year": {str(y): float(panel.loc[year == y, ENERGY_COL].quantile(0.90))
                               for y in sorted(year.unique())},
        "n": int(len(panel)),
        "window": f"{t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}",
    }


def _log_series(ax, x, y, color, label):
    """Plot on a symlog axis so near-zero medians stay visible."""
    ax.plot(x, y, color=color, lw=1.0)
    S.symlog_axis(ax, linthresh=1.0, label=label)


def prepare_f3_annotation(d: dict) -> str:
    parts = " / ".join(f"{y} ${v:,.2f}" for y, v in d["cong_p90_by_year"].items())
    return f"Congestion p90 by year: {parts}"


def plot_f3(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True)
    x = d["dates"]
    _log_series(axes[0], x, d["total_lmp"], S.COLOR["total_lmp"],
                "Total LMP ($)")
    axes[0].set_title("(a) What a data center actually pays — total LMP")
    _log_series(axes[1], x, d["congestion"], S.COLOR["primary"],
                "Congestion ($)")
    axes[1].set_title("(b) Congestion — spiky, regime-shifting (locational)")
    _log_series(axes[2], x, d["system_energy"], S.COLOR["system_energy"],
                "System energy ($)")
    axes[2].set_title("(c) System energy — smooth, seasonal (system-wide)")
    axes[2].set_xlabel("Date")

    fig.suptitle(f"{S.label('F3')} — Total LMP decomposed: locational vs system-wide", y=0.98)
    footer = S.provenance(source=PANEL_5MIN, n=d["n"], window=d["window"],
                          spec="daily medians, symlog axis", resolution="5-min")
    caption = (
        prepare_f3_annotation(d) + ". "
        "Panel (c): system energy price is locationally uniform across PJM, "
        "so its 2026 rise is NOT a Northern-Virginia phenomenon. "
        "Daily medians on a symlog axis; linear axes would flatten "
        "everything before 2026 into a baseline smear.")
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)


THRESHOLDS = [100, 250, 500, 1000]
TRAILING_MONTHS = 12


def prepare_f4(panel: pd.DataFrame) -> dict:
    t = pd.to_datetime(panel[TIME_COL])
    month = t.dt.to_period("M")
    months = sorted(month.unique())
    cong = panel[CONG_COL]

    abs_counts, rel_counts, thresholds = [], [], []
    for m in months:
        cur = cong[month == m]
        abs_counts.append(int((cur > 100).sum()))
        # The trailing window is strictly prior months, so the threshold a
        # month is judged against never contains that month's own values.
        prior = cong[(month < m) & (month >= m - TRAILING_MONTHS)]
        if (m - months[0]).n < TRAILING_MONTHS or len(prior) == 0:
            thresholds.append(float("nan"))
            rel_counts.append(0)
        else:
            thr = float(prior.quantile(0.99))
            thresholds.append(thr)
            rel_counts.append(int((cur > thr).sum()))

    return {
        "months": [str(m) for m in months],
        "count_gt_100": abs_counts,
        "count_gt_trailing_p99": rel_counts,
        "trailing_p99": thresholds,
        # Carried rather than recomputed at draw time: the plot shades this
        # span, and a zero bar inside it means "no threshold yet", not "no
        # events". The data and the shading must not be able to disagree.
        "n_undefined_months": int(sum(1 for v in thresholds
                                      if not np.isfinite(v))),
        "n": int(len(panel)),
        "window": f"{t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}",
    }


def _month_ticks(ax, months: list[str]) -> None:
    x = np.arange(len(months))
    step = max(1, len(x) // 12)
    ax.set_xticks(x[::step])
    ax.set_xticklabels(months[::step], rotation=45, ha="right")


def prepare_f4_annotation(d: dict) -> str:
    """Quote the first and last defined trailing thresholds.

    Panel (b)'s yardstick moves, and by how much is the actual finding --
    stating it from the data keeps the caption from asserting a divergence
    the numbers may not support.
    """
    defined = [(m, v) for m, v in zip(d["months"], d["trailing_p99"])
               if np.isfinite(v)]
    if not defined:
        return ("No month has a full trailing-12-month window, so panel (b) "
                "is undefined throughout")
    (m0, v0), (m1, v1) = defined[0], defined[-1]
    return (f"The trailing-12-month p99 threshold itself climbs from "
            f"${v0:,.2f} ({m0}) to ${v1:,.2f} ({m1})")


def plot_f4(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    x = np.arange(len(d["months"]))
    axes[0].bar(x, d["count_gt_100"], color=S.COLOR["primary"])
    axes[0].set_ylabel("Intervals > $100")
    axes[0].set_title("(a) Absolute risk — intervals above a fixed $100")

    axes[1].bar(x, d["count_gt_trailing_p99"], color=S.COLOR["dom_zonal"])
    axes[1].set_ylabel("Intervals > trailing p99")
    axes[1].set_title(
        "(b) Risk relative to its own era — trailing-12-month 99th pct")
    n_undef = d["n_undefined_months"]
    if n_undef:
        # Without this, the opening months read as a genuine run of zeros.
        axes[1].axvspan(-0.5, n_undef - 0.5, color=S.MUTED, alpha=0.15,
                        zorder=0)
        axes[1].text(n_undef / 2 - 0.5, axes[1].get_ylim()[1] * 0.9,
                     "no trailing\nwindow yet", ha="center", va="top",
                     fontsize=7, color=S.MUTED)
    _month_ticks(axes[1], d["months"])

    fig.suptitle(f"{S.label('F4')} — Large congestion events per month", y=0.98)
    footer = S.provenance(source=PANEL_5MIN, n=d["n"], window=d["window"],
                          spec="monthly exceedance counts", resolution="5-min")
    caption = (
        prepare_f4_annotation(d) + ", so panel (b) scores each month against "
        "a moving yardstick: absolute exceedance can climb while era-relative "
        "exceedance does not, because the recent past has itself become more "
        "extreme. Shaded months in (b) have no trailing window — their zeros "
        "mean 'undefined', not 'no events'. The first bucket is a partial "
        "month.")
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)


def prepare_f4b(panel: pd.DataFrame) -> dict:
    t = pd.to_datetime(panel[TIME_COL])
    month = t.dt.to_period("M")
    months = sorted(month.unique())
    cong = panel[CONG_COL]

    counts = {}
    for thr in THRESHOLDS:
        per_month = (cong > thr).groupby(month).sum()
        counts[thr] = [int(per_month.get(m, 0)) for m in months]

    return {
        "months": [str(m) for m in months],
        "thresholds": THRESHOLDS,
        # Observed counts. Monthly buckets are what make this honest: every
        # bucket is one month, so partial years never need annualising and a
        # storm-driven half-year is never extrapolated across a season it
        # did not occur in.
        "counts": counts,
        "n": int(len(panel)),
        "window": f"{t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}",
    }


def prepare_f4b_annotation(d: dict) -> str:
    """Name the worst month at the mildest and the harshest threshold.

    Computed rather than written into the caption: a hardcoded month would
    silently go stale the next time the panel is extended.
    """
    lo, hi = d["thresholds"][0], d["thresholds"][-1]
    worst_lo = d["months"][int(np.argmax(d["counts"][lo]))]
    worst_hi = d["months"][int(np.argmax(d["counts"][hi]))]
    return (f"Worst month above ${lo:,} is {worst_lo}; "
            f"above ${hi:,} it is {worst_hi}")


def plot_f4b(d: dict, out_path: Path) -> None:
    thrs = d["thresholds"]
    fig, axes = plt.subplots(len(thrs), 1, figsize=(11, 9), sharex=True)
    x = np.arange(len(d["months"]))
    palette = [S.COLOR["primary"], S.COLOR["dom_zonal"],
               S.COLOR["total_lmp"], S.COLOR["ashburn_tx1"]]
    top = max(max(d["counts"][thr]) for thr in thrs)

    for ax, thr, color in zip(axes, thrs, palette):
        # Markers, not bars. A bar encodes magnitude by length, and length
        # on a log axis means nothing -- a single event would draw a bar a
        # third the height of one carrying 271. Position is the only honest
        # encoding here, which is why F3 plots its symlog series the same way.
        ax.plot(x, d["counts"][thr], color=color, lw=0.9,
                marker="o", ms=3, mew=0)
        # One shared symlog scale. These panels plot the same quantity at
        # different severities, so independent scales would make 25 events
        # above $1000 look like 1,632 above $100, while a shared linear
        # scale would flatten the rare panels onto the baseline.
        S.symlog_axis(ax, linthresh=1.0, label=f"> ${thr:,}")
        ax.set_ylim(0, top * 1.15)
    _month_ticks(axes[-1], d["months"])

    fig.suptitle(f"{S.label('F4b')} — Severity escalation, by month", y=0.98)
    footer = S.provenance(source=PANEL_5MIN, n=d["n"], window=d["window"],
                          spec="monthly exceedance counts, observed",
                          resolution="5-min")
    caption = (
        prepare_f4b_annotation(d) + ". Counts are observed, never "
        "annualised. Panels share a symlog scale. CAVEAT — do not read this "
        "as a data-center congestion story: much of the 2026 rise is "
        "SYSTEM-WIDE (PJM system energy price roughly tripled in the same "
        "month), the driver is UNIDENTIFIED, and this panel contains no "
        "non-DOM control pnode.")
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)
