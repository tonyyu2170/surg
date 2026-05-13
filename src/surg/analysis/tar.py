"""TAR — Threshold Autoregression estimator (Hansen 1996/2000).

Model:
    Y_t = α₀ + α₁·Y_{t-1} + ε_t   if Z_t ≤ c   (low-volatility regime)
    Y_t = β₀ + β₁·Y_{t-1} + ε_t   if Z_t >  c   (high-volatility regime)

`fit_tar` estimates c via concentrated least squares: grid-search over
candidate values of c (quantiles of Z), fit AR(1) on each regime, pick
c minimizing joint residual SSR.

The Hansen bootstrap test for "is there a threshold" is in a separate
function `hansen_bootstrap_test` (Task 4).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class TARResult:
    c_hat: float          # estimated threshold
    alpha: np.ndarray     # low-regime coefficients [intercept, AR1]
    beta: np.ndarray      # high-regime coefficients [intercept, AR1]
    n_low: int            # observations below threshold
    n_high: int           # observations above
    ssr_low: float        # SSR in low regime
    ssr_high: float       # SSR in high regime
    ssr_joint: float      # ssr_low + ssr_high


def _fit_ar1_ols(Y: np.ndarray, Y_lag: np.ndarray) -> tuple[np.ndarray, float]:
    """Fit Y = β₀ + β₁ Y_lag via OLS. Returns (coefficients, SSR)."""
    X = np.column_stack([np.ones(len(Y)), Y_lag])
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ beta
    return beta, float(resid @ resid)


def fit_tar(
    Y: np.ndarray,
    Y_lag: np.ndarray,
    Z: np.ndarray,
    *,
    trim: float = 0.15,
    n_grid: int = 300,
) -> TARResult:
    """Estimate the TAR threshold c via concentrated least squares.

    Args:
        Y: response vector, length n
        Y_lag: Y_{t-1} aligned with Y, length n
        Z: threshold variable, length n
        trim: minimum fraction of obs in each regime (0.15 = Hansen default)
        n_grid: number of candidate c values to search over

    Grid: `n_grid` evenly-spaced quantiles of Z within [trim, 1-trim].
    """
    Y, Y_lag, Z = np.asarray(Y), np.asarray(Y_lag), np.asarray(Z)
    if not (len(Y) == len(Y_lag) == len(Z)):
        raise ValueError("Y, Y_lag, Z must be the same length")

    # Candidate thresholds: quantiles of Z spaced evenly by rank in [trim, 1-trim].
    candidates = np.quantile(Z, np.linspace(trim, 1.0 - trim, n_grid))

    best = None
    min_n = int(trim * len(Y))
    for c in candidates:
        mask = Z <= c
        n_low, n_high = int(mask.sum()), int((~mask).sum())
        if n_low < min_n or n_high < min_n:
            continue

        alpha, ssr_low = _fit_ar1_ols(Y[mask], Y_lag[mask])
        beta, ssr_high = _fit_ar1_ols(Y[~mask], Y_lag[~mask])
        ssr_joint = ssr_low + ssr_high

        if best is None or ssr_joint < best.ssr_joint:
            best = TARResult(
                c_hat=float(c),
                alpha=alpha, beta=beta,
                n_low=n_low, n_high=n_high,
                ssr_low=ssr_low, ssr_high=ssr_high,
                ssr_joint=ssr_joint,
            )

    if best is None:
        raise RuntimeError("no valid threshold found (trim too aggressive?)")
    return best
