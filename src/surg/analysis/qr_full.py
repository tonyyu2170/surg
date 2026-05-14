"""Multi-quantile QR on the full panel with time-of-day + season covariates.

Strategy C module — operates on the full 31,536-hour analysis panel
(no `passes_proposal_filter` filtering). Each fit produces point
estimates with asymptotic SE and (when n_boot >= 20) a pair-bootstrap
95% CI on the Z slope. Year-FE robustness specification is added in
Task 8.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(frozen=True, slots=True)
class QRFullFitResult:
    """Single QR fit at one quantile, one specification (primary or year_fe).

    `z_slope_bootstrap_ci_95` is `(nan, nan)` when `n_boot < 20` (skipped);
    otherwise it carries the pair-bootstrap 2.5%/97.5% quantiles of the
    z_slope sampling distribution.
    """
    tau: float
    z_slope: float
    z_slope_se: float
    z_slope_p_value: float
    z_slope_bootstrap_ci_95: tuple[float, float]
    intercept: float
    covariate_coefs: dict[str, float]
    spec: str   # "primary" or "year_fe"
    n: int


def _build_periodic_basis(hour: np.ndarray, month: np.ndarray) -> dict[str, np.ndarray]:
    """Return the four sin/cos basis columns for hour and month."""
    return {
        "hour_sin":  np.sin(2.0 * np.pi * hour / 24.0),
        "hour_cos":  np.cos(2.0 * np.pi * hour / 24.0),
        "month_sin": np.sin(2.0 * np.pi * (month - 1) / 12.0),
        "month_cos": np.cos(2.0 * np.pi * (month - 1) / 12.0),
    }


def _bootstrap_z_slope_ci(
    Y: np.ndarray,
    Z: np.ndarray,
    hour: np.ndarray,
    month: np.ndarray,
    *,
    tau: float,
    n_boot: int,
    seed: int,
    extra_X: np.ndarray | None = None,
) -> tuple[float, float]:
    """Pair-bootstrap 95% CI on the Z slope coefficient in fit_qr_full.

    Resamples row indices with replacement, refits QR each time, returns
    2.5%/97.5% quantiles of the Z-slope sampling distribution. Returns
    (nan, nan) if n_boot < 20 or fewer than 20 reps converge.

    `extra_X` is an optional matrix of additional design columns (used by
    the year-FE spec in Task 8). When None, only the sin/cos basis is used.
    """
    if n_boot < 20:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    n = len(Y)
    slopes: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        basis = _build_periodic_basis(hour[idx], month[idx])
        cols = [
            np.ones(n),
            Z[idx],
            basis["hour_sin"], basis["hour_cos"],
            basis["month_sin"], basis["month_cos"],
        ]
        if extra_X is not None:
            cols.append(extra_X[idx])
        X_boot = np.column_stack(cols)
        try:
            m = sm.QuantReg(Y[idx], X_boot).fit(q=tau)
            # statsmodels rarely raises on QR; it can also return NaN/inf
            # params under degenerate subsets (extreme tau, collinear cols).
            # Treat non-finite estimates as failed reps.
            val = float(m.params[1])
            if not np.isfinite(val):
                continue
            slopes.append(val)
        except Exception:  # statsmodels failure modes vary (LinAlgError, ValueError, etc.); broad catch is intentional
            continue
    if len(slopes) < 20:
        return (float("nan"), float("nan"))
    arr = np.asarray(slopes)
    return (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))


def fit_qr_full(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    hour: np.ndarray | pd.Series,
    month: np.ndarray | pd.Series,
    *,
    year: np.ndarray | pd.Series | None = None,
    tau: float = 0.99,
    n_boot: int = 0,
    seed: int = 0,
) -> QRFullFitResult:
    """Fit Q_τ(Y | Z, sin/cos(hour), sin/cos(month) [, year dummies]).

    Primary spec (year is None): design matrix is [1, Z, hour_sin, hour_cos,
    month_sin, month_cos]. Z slope captures contemporaneous + secular response.

    Year-FE spec (year is provided): same design matrix plus K-1 year dummies
    (earliest year as baseline). Z slope captures contemporaneous response only.

    All input arrays must have equal length and contain no NaN. Caller drops
    NaN rows first.

    Notes:
        The returned asymptotic `z_slope_se` and `z_slope_p_value` come from
        statsmodels' Koenker-Bassett sandwich estimator. This is reliable at
        central quantiles (τ ≈ 0.5) but is known to underperform at high τ
        (≥ 0.99) on autocorrelated time-series data. Task 7 of the Strategy
        C implementation plan adds a pair-bootstrap CI on `z_slope` that is
        the more honest interval at the tail quantiles used in the
        production analysis.
    """
    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    hour_arr = np.asarray(hour, dtype=int)
    month_arr = np.asarray(month, dtype=int)

    n = len(Y_arr)
    if not (len(Z_arr) == len(hour_arr) == len(month_arr) == n):
        raise ValueError(
            f"all inputs must have equal length; got Y={len(Y_arr)}, "
            f"Z={len(Z_arr)}, hour={len(hour_arr)}, month={len(month_arr)}"
        )
    if any(np.isnan(arr).any() for arr in (Y_arr, Z_arr)):
        raise ValueError("Y or Z contains NaN; caller must drop NaN rows first")

    if not (np.all((hour_arr >= 0) & (hour_arr <= 23)) and
            np.all((month_arr >= 1) & (month_arr <= 12))):
        raise ValueError(
            "hour must be in [0, 23] and month in [1, 12] (integers); "
            "check for NaN or out-of-range values before calling fit_qr_full"
        )

    basis = _build_periodic_basis(hour_arr, month_arr)
    base_cols = [
        np.ones(n),
        Z_arr,
        basis["hour_sin"], basis["hour_cos"],
        basis["month_sin"], basis["month_cos"],
    ]
    covariate_names = ["hour_sin", "hour_cos", "month_sin", "month_cos"]

    if year is None:
        spec = "primary"
        X = np.column_stack(base_cols)
        extra_X_for_boot: np.ndarray | None = None
    else:
        spec = "year_fe"
        year_arr = np.asarray(year, dtype=int)
        if len(year_arr) != n:
            raise ValueError(
                f"year length {len(year_arr)} != Y length {n}"
            )
        distinct_years = sorted(np.unique(year_arr).tolist())
        if len(distinct_years) < 2:
            raise ValueError(
                f"year_fe spec requires ≥2 distinct years; got {distinct_years}"
            )
        year_dummy_cols: list[np.ndarray] = []
        year_dummy_names: list[str] = []
        for y in distinct_years[1:]:
            year_dummy_cols.append((year_arr == y).astype(float))
            year_dummy_names.append(f"year_{y}")
        extra_X_for_boot = np.column_stack(year_dummy_cols)
        X = np.column_stack(base_cols + year_dummy_cols)
        covariate_names = covariate_names + year_dummy_names

    model = sm.QuantReg(Y_arr, X).fit(q=tau)
    z_slope = float(model.params[1])
    z_slope_se = float(model.bse[1])
    z_slope_p = float(model.pvalues[1])
    intercept = float(model.params[0])

    covariate_coefs = {
        name: float(model.params[i + 2])  # +2 to skip [intercept, Z]
        for i, name in enumerate(covariate_names)
    }

    ci: tuple[float, float] = _bootstrap_z_slope_ci(
        Y=Y_arr, Z=Z_arr, hour=hour_arr, month=month_arr,
        tau=tau, n_boot=n_boot, seed=seed,
        extra_X=extra_X_for_boot,
    )

    return QRFullFitResult(
        tau=float(tau),
        z_slope=z_slope,
        z_slope_se=z_slope_se,
        z_slope_p_value=z_slope_p,
        z_slope_bootstrap_ci_95=ci,
        intercept=intercept,
        covariate_coefs=covariate_coefs,
        spec=spec,
        n=n,
    )
