"""τ=0.99 secular sign-flip diagnostic (sub-q1 closure item #3).

Three-layer evidence:
  L1: raw per-year LMP percentile stats (descriptive only).
  L2: pair-bootstrap year-dummy coefficient CIs (per-year LEVEL SHIFTS,
      not a trend test).
  L3: pair-bootstrap secular-component CI = primary_z_slope - year_fe_z_slope
      at each tau (the actual trend test).

Reuses qr_full.fit_qr_full for the year-FE QR.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.qr_full import fit_qr_full


def compute_raw_per_year_stats(
    panel: pd.DataFrame,
    *,
    response_col: str,
    year_col: str,
    pct_list: tuple[float, ...] = (0.90, 0.95, 0.99),
) -> list[dict]:
    """Per-year summary stats of `response_col`. Descriptive only — no model."""
    sub = panel.dropna(subset=[response_col, year_col]).copy()
    sub["__year"] = pd.to_datetime(sub[year_col]).dt.year
    stats: list[dict] = []
    for year, group in sub.groupby("__year"):
        row = {"year": int(year), "n_obs": int(len(group))}
        for p in pct_list:
            row[f"p{int(p*100)}"] = float(np.quantile(group[response_col].to_numpy(), p))
        stats.append(row)
    return sorted(stats, key=lambda r: r["year"])


def _nan_to_none(x: float | None) -> float | None:
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return float(x)


def bootstrap_year_dummy_coefs(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    year_col: str,
    taus: tuple[float, ...],
    n_boot: int = 200,
    seed: int = 0,
) -> dict:
    """Pair-bootstrap CIs for year-dummy coefficients in fit_qr_full's year_fe spec.

    Reports descriptive PER-YEAR LEVEL SHIFTS (from baseline). NOT a trend test.
    """
    sub = panel.dropna(subset=[response_col, z_col, year_col]).copy()
    sub[year_col] = pd.to_datetime(sub[year_col])
    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()
    hour = sub[year_col].dt.hour.to_numpy()
    month = sub[year_col].dt.month.to_numpy()
    year = sub[year_col].dt.year.to_numpy()

    distinct_years = sorted(np.unique(year).tolist())
    if len(distinct_years) < 2:
        return {"skip_reason": f"only {len(distinct_years)} distinct year(s)"}

    baseline = distinct_years[0]
    dummy_years = distinct_years[1:]

    out: dict = {}
    n = len(Y)
    for tau_idx, tau in enumerate(taus):
        # Point estimate from a single fit (no bootstrap of point).
        point_fit = fit_qr_full(Y, Z, hour, month, year=year, tau=tau, n_boot=0,
                                seed=seed + tau_idx * 1000)
        point_coefs = point_fit.covariate_coefs

        # Pair-bootstrap each year dummy.
        rng = np.random.default_rng(seed + tau_idx * 1000 + 7)
        boot_coefs: dict[int, list[float]] = {y: [] for y in dummy_years}
        for rep in range(n_boot):
            idx = rng.integers(0, n, size=n)
            try:
                rep_fit = fit_qr_full(
                    Y[idx], Z[idx], hour[idx], month[idx],
                    year=year[idx], tau=tau, n_boot=0, seed=0,
                )
            except Exception:
                continue
            for y in dummy_years:
                key = f"year_{y}"
                if key in rep_fit.covariate_coefs:
                    val = rep_fit.covariate_coefs[key]
                    if np.isfinite(val):
                        boot_coefs[y].append(val)

        by_year: dict[str, dict] = {}
        for y in dummy_years:
            arr = np.asarray(boot_coefs[y])
            if len(arr) < 20:
                ci = (float("nan"), float("nan"))
            else:
                ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
            by_year[f"year_{y}"] = {
                "point": _nan_to_none(point_coefs.get(f"year_{y}", float("nan"))),
                "ci": [_nan_to_none(ci[0]), _nan_to_none(ci[1])],
                "n_boot_converged": int(len(arr)),
            }
        out[f"tau_{tau:.2f}"] = by_year
        out[f"tau_{tau:.2f}_baseline_year"] = int(baseline)
    return out


def bootstrap_secular_component(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    year_col: str,
    taus: tuple[float, ...],
    n_boot: int = 200,
    seed: int = 0,
) -> dict:
    """Pair-bootstrap CI on primary_z_slope - year_fe_z_slope per tau.

    This IS the trend test for the τ=0.99 secular sign-flip claim.
    """
    sub = panel.dropna(subset=[response_col, z_col, year_col]).copy()
    sub[year_col] = pd.to_datetime(sub[year_col])
    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()
    hour = sub[year_col].dt.hour.to_numpy()
    month = sub[year_col].dt.month.to_numpy()
    year = sub[year_col].dt.year.to_numpy()

    distinct_years = sorted(np.unique(year).tolist())
    if len(distinct_years) < 2:
        return {"skip_reason": f"only {len(distinct_years)} distinct year(s)"}

    out: dict = {}
    n = len(Y)
    for tau_idx, tau in enumerate(taus):
        primary_fit = fit_qr_full(Y, Z, hour, month, tau=tau, n_boot=0, seed=seed)
        yfe_fit = fit_qr_full(Y, Z, hour, month, year=year, tau=tau, n_boot=0, seed=seed)
        point_secular = primary_fit.z_slope - yfe_fit.z_slope

        rng = np.random.default_rng(seed + tau_idx * 1000 + 11)
        diffs: list[float] = []
        for rep in range(n_boot):
            idx = rng.integers(0, n, size=n)
            try:
                pfit = fit_qr_full(Y[idx], Z[idx], hour[idx], month[idx],
                                   tau=tau, n_boot=0, seed=0)
                yfit = fit_qr_full(Y[idx], Z[idx], hour[idx], month[idx],
                                   year=year[idx], tau=tau, n_boot=0, seed=0)
            except Exception:
                continue
            d = pfit.z_slope - yfit.z_slope
            if np.isfinite(d):
                diffs.append(d)
        if len(diffs) < 20:
            ci = (float("nan"), float("nan"))
        else:
            arr = np.asarray(diffs)
            ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
        out[f"tau_{tau:.2f}"] = {
            "primary_z_slope": _nan_to_none(primary_fit.z_slope),
            "year_fe_z_slope": _nan_to_none(yfe_fit.z_slope),
            "secular_component_point": _nan_to_none(point_secular),
            "secular_component_ci": [_nan_to_none(ci[0]), _nan_to_none(ci[1])],
            "n_boot_converged": int(len(diffs)),
        }
    return out
