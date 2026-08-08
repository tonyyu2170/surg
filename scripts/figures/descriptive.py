"""F1: the premise -- load grew, ramp volatility did not."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from scripts.figures import _style as S

PANEL_5MIN = "analysis_panel_5min.parquet"


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
