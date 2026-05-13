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

import json
from dataclasses import asdict, dataclass
from pathlib import Path

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
        # Y_lag[0] is the pre-sample conditioning value; generate Y_star[0]
        # under the null DGP using eps[0] so every row in the bootstrap
        # regression is a valid draw (no fixed-row artifact).
        Y_star[0] = coef_full[0] + coef_full[1] * Y_lag[0] + eps[0]
        for t in range(1, n):
            Y_star[t] = coef_full[0] + coef_full[1] * Y_star[t-1] + eps[t]
        Y_star_lag = np.r_[Y_lag[0], Y_star[:-1]]

        _, ssr_full_b = _fit_ar1_ols(Y_star, Y_star_lag)
        boot_result = fit_tar(Y_star, Y_star_lag, Z, trim=trim, n_grid=n_grid)
        T_boot[b] = ssr_full_b - boot_result.ssr_joint

    return (1 + int(np.sum(T_boot >= T_obs))) / (1 + n_boot)


def run_tar(
    panel,
    out_path: Path,
    *,
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    trim: float = 0.15,
    n_grid: int = 300,
    n_boot: int = 1000,
    seed: int = 42,
) -> TARResult:
    """End-to-end TAR fit on the panel, writing JSON output.

    Selects rows where passes_proposal_filter is True; constructs Y_lag
    from the full (unfiltered) time series so the AR(1) structure is
    natural at any retained row.

    Methodology caveats (see docs/decisions.md):
    - The c_hat_ci_95 here is a pair bootstrap (iid resampling of
      (Y, Y_lag, Z) rows). It ignores AR serial correlation in the
      subset and tends to be tighter than the true sampling
      distribution. T13's subsample bootstrap is the canonical CI.
    - After filter (shoulder + 2-5 AM), consecutive subset rows are
      not adjacent in real time (~21 hours apart). The Hansen
      bootstrap's recursive Y* generation treats the subset as one
      AR(1) path, which is an interpretive approximation. We accept
      this as a feature of the proposal's signal-isolation design.
    """
    import pandas as pd

    # Order by datetime to ensure lag alignment
    panel = panel.sort_values("datetime_beginning_ept").reset_index(drop=True)
    # Guard against silently-misaligned lags if the panel has hourly gaps.
    # shift(1) walks rows, not real time; with a gap, _Y_lag at row t would
    # be the value many hours earlier rather than one hour earlier.
    deltas = panel["datetime_beginning_ept"].diff().dropna()
    if not (deltas == pd.Timedelta(hours=1)).all():
        n_gaps = int((deltas != pd.Timedelta(hours=1)).sum())
        raise ValueError(
            f"panel has {n_gaps} non-hourly gap(s); _Y_lag would be "
            f"misaligned. Rebuild the panel with surg-prep, or pre-fill gaps."
        )
    # Y_{t-1} on the FULL time series (per design spec §4)
    panel["_Y_lag"] = panel[response_col].shift(1)
    # Then subset to the proposal filter
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[response_col, "_Y_lag", threshold_col])

    Y = subset[response_col].to_numpy()
    Y_lag = subset["_Y_lag"].to_numpy()
    Z = subset[threshold_col].to_numpy()

    point = fit_tar(Y, Y_lag, Z, trim=trim, n_grid=n_grid)
    p_value = hansen_bootstrap_test(
        Y, Y_lag, Z, point,
        n_boot=n_boot, trim=trim, n_grid=n_grid, seed=seed,
    )

    # Bootstrap CI for c_hat: resample (Y, Y_lag, Z) tuples and re-fit
    rng = np.random.default_rng(seed + 1)
    c_boot = np.empty(min(500, n_boot))
    n = len(Y)
    for i in range(len(c_boot)):
        idx = rng.integers(0, n, size=n)
        b = fit_tar(Y[idx], Y_lag[idx], Z[idx], trim=trim, n_grid=n_grid // 3)
        c_boot[i] = b.c_hat
    ci_lo, ci_hi = float(np.quantile(c_boot, 0.025)), float(np.quantile(c_boot, 0.975))

    payload = {
        "c_hat": point.c_hat,
        "c_hat_ci_95": [ci_lo, ci_hi],
        "alpha": point.alpha.tolist(),
        "beta": point.beta.tolist(),
        "regime_counts": {"low": point.n_low, "high": point.n_high},
        "ssr_low": point.ssr_low,
        "ssr_high": point.ssr_high,
        "ssr_joint": point.ssr_joint,
        "hansen_p_value": p_value,
        "n_boot": n_boot,
        "trim": trim,
        "n_grid": n_grid,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    return point
