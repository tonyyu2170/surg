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
    fig.suptitle("F1 — The premise: load grew, volatility did not", y=0.98)

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

    fig.suptitle("F2 — Congestion tracks load level, not ramp volatility", y=0.99)
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

    fig.suptitle("F3 — Total LMP decomposed: locational vs system-wide", y=0.98)
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
