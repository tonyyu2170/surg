"""Multi-quantile QR on the full panel with time-of-day + season covariates.

Strategy C module — operates on the full 31,536-hour analysis panel
(no `passes_proposal_filter` filtering). Each fit produces point
estimates and asymptotic SE; bootstrap CI is added in Task 7 of the
implementation plan. Year-FE robustness specification is added in
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

    `z_slope_bootstrap_ci_95` is `(nan, nan)` until Task 7 wires bootstrap.
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


def fit_qr_full(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    hour: np.ndarray | pd.Series,
    month: np.ndarray | pd.Series,
    *,
    tau: float = 0.99,
    n_boot: int = 0,
    seed: int = 0,
) -> QRFullFitResult:
    """Fit Q_τ(Y | Z, sin/cos(hour), sin/cos(month)).

    All four arrays must have equal length and contain no NaN. (Caller drops
    NaN rows before passing.) `n_boot=0` skips bootstrap CI and returns
    `(nan, nan)` for `z_slope_bootstrap_ci_95`; non-zero `n_boot` will be
    wired in a subsequent task.
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

    basis = _build_periodic_basis(hour_arr, month_arr)
    X = np.column_stack([
        np.ones(n),                  # intercept
        Z_arr,                       # primary regressor
        basis["hour_sin"],
        basis["hour_cos"],
        basis["month_sin"],
        basis["month_cos"],
    ])
    model = sm.QuantReg(Y_arr, X).fit(q=tau)
    z_slope = float(model.params[1])
    z_slope_se = float(model.bse[1])
    z_slope_p = float(model.pvalues[1])
    intercept = float(model.params[0])

    covariate_coefs = {
        name: float(model.params[i + 2])  # +2 to skip [intercept, Z]
        for i, name in enumerate(("hour_sin", "hour_cos", "month_sin", "month_cos"))
    }

    # Bootstrap CI is wired in Task 7; for now return placeholder
    ci: tuple[float, float] = (float("nan"), float("nan"))

    return QRFullFitResult(
        tau=float(tau),
        z_slope=z_slope,
        z_slope_se=z_slope_se,
        z_slope_p_value=z_slope_p,
        z_slope_bootstrap_ci_95=ci,
        intercept=intercept,
        covariate_coefs=covariate_coefs,
        spec="primary",
        n=n,
    )
