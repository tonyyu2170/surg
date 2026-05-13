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


def hansen_bootstrap_test(
    Y: np.ndarray,
    Y_lag: np.ndarray,
    Z: np.ndarray,
    tar_result: TARResult,
    *,
    n_boot: int = 1000,
    trim: float = 0.15,
    n_grid: int = 300,
    seed: int = 0,
) -> float:
    """Bootstrap p-value for H₀: no threshold (single AR(1) for all data).

    Steps:
      1. Fit AR(1) to the *full* sample (no regime split) → get residuals ε̂.
      2. Compute the SSR-improvement statistic on observed data:
           T = SSR_full - SSR_joint (observed)
      3. For each bootstrap rep b in 1..B:
           - Resample residuals with replacement → ε*ᵦ
           - Generate Y*ᵦ recursively under the null AR(1)
           - Re-fit TAR on (Y*, Y*_lag, Z)
           - Compute T*ᵦ = SSR_full(b) - SSR_joint(b)
      4. p = (1 + #{T*ᵦ ≥ T}) / (1 + B)
    """
    rng = np.random.default_rng(seed)

    coef_full, ssr_full = _fit_ar1_ols(Y, Y_lag)
    resid_full = Y - (coef_full[0] + coef_full[1] * Y_lag)

    T_obs = ssr_full - tar_result.ssr_joint

    n = len(Y)
    T_boot = np.empty(n_boot)
    for b in range(n_boot):
        eps = rng.choice(resid_full, size=n, replace=True)
        Y_star = np.empty(n)
        Y_star[0] = Y_lag[0]  # initialize with the observed first lag
        for t in range(1, n):
            Y_star[t] = coef_full[0] + coef_full[1] * Y_star[t-1] + eps[t]
        Y_star_lag = np.r_[Y_star[0], Y_star[:-1]]

        _, ssr_full_b = _fit_ar1_ols(Y_star, Y_star_lag)
        boot_result = fit_tar(Y_star, Y_star_lag, Z, trim=trim, n_grid=n_grid)
        T_boot[b] = ssr_full_b - boot_result.ssr_joint

    return (1 + int(np.sum(T_boot >= T_obs))) / (1 + n_boot)
