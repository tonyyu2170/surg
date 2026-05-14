"""Generalized Pareto Distribution fits on LMP exceedances over a threshold.

Strategy C module — peaks-over-threshold (POT) MLE plus a sweep across
multiple threshold quantiles and a Z-conditional mechanism test. This
file initially contains the point-estimate `fit_gpd` only; the sweep
and conditional functions land in subsequent tasks.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True, slots=True)
class GPDFitResult:
    """Point-estimate result from a single GPD fit at one threshold.

    `shape_bootstrap_ci_95` is `(nan, nan)` on a bare fit_gpd call;
    `gpd_threshold_sweep` and `gpd_conditional_on_z` return new
    `GPDFitResult` instances with the bootstrap CI populated.
    """
    threshold_quantile: float
    threshold_value: float
    shape: float
    shape_se: float
    shape_bootstrap_ci_95: tuple[float, float]
    scale: float
    scale_se: float
    n_exceedances: int


def fit_gpd(Y: np.ndarray | pd.Series, *, threshold: float) -> GPDFitResult:
    """Fit a Generalized Pareto Distribution to exceedances of `Y` over `threshold`.

    Uses `scipy.stats.genpareto` MLE with `floc=0`, after subtracting the
    threshold from the exceedances. Asymptotic SE for (shape, scale) uses
    the closed-form Hosking & Wallis (1987) covariance valid for shape > -0.5.

    Raises ValueError if `threshold` exceeds `max(Y)` (no exceedances) or
    fewer than 10 exceedances remain (fit is too noisy to be useful).
    """
    Y_arr = np.asarray(Y, dtype=float)
    if not np.isfinite(Y_arr).all():
        raise ValueError(
            "Y contains non-finite values (NaN or inf); caller must drop them first"
        )
    if not np.isfinite(threshold):
        raise ValueError(f"threshold must be finite, got {threshold}")
    if threshold > Y_arr.max():
        raise ValueError(
            f"threshold {threshold:.4g} exceeds max(Y) = {Y_arr.max():.4g}; "
            f"no exceedances"
        )
    excess = Y_arr[Y_arr > threshold] - threshold
    n = len(excess)
    if n < 10:
        raise ValueError(
            f"too few exceedances above threshold {threshold:.4g}: n={n} (need >=10)"
        )

    # scipy.stats.genpareto MLE with location fixed at 0 (we subtracted threshold)
    shape, _loc, scale = stats.genpareto.fit(excess, floc=0.0)

    # Asymptotic SE for (shape, scale) — Hosking & Wallis (1987), valid for shape > -0.5
    if shape > -0.5:
        shape_se = (1.0 + shape) / math.sqrt(n)
        scale_se = scale * math.sqrt(2.0 * (1.0 + shape) / n)
    else:
        # Regularity condition violated — MLE is non-regular, asymptotic SE undefined
        shape_se = float("nan")
        scale_se = float("nan")

    threshold_quantile = float(np.mean(Y_arr <= threshold))

    return GPDFitResult(
        threshold_quantile=threshold_quantile,
        threshold_value=float(threshold),
        shape=float(shape),
        shape_se=float(shape_se),
        shape_bootstrap_ci_95=(float("nan"), float("nan")),
        scale=float(scale),
        scale_se=float(scale_se),
        n_exceedances=n,
    )


def _bootstrap_shape_ci(
    Y: np.ndarray,
    *,
    threshold: float,
    n_boot: int,
    seed: int,
) -> tuple[float, float]:
    """Non-parametric pair-bootstrap CI on the GPD shape parameter.

    Resample row indices of `Y` with replacement, refit GPD at the same
    threshold each time, return 2.5%/97.5% quantiles of the shape estimates.

    Skips bootstrap reps that result in < 10 exceedances or fail to converge.
    Returns (nan, nan) if fewer than 20 reps succeed (CI uninformative).
    """
    rng = np.random.default_rng(seed)
    n = len(Y)
    shapes: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        Y_boot = Y[idx]
        try:
            fit = fit_gpd(Y_boot, threshold=threshold)
        except ValueError:
            continue
        shapes.append(fit.shape)
    if len(shapes) < 20:
        return (float("nan"), float("nan"))
    arr = np.asarray(shapes)
    return (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))


@dataclass(frozen=True, slots=True)
class GPDConditionalResult:
    """Z-conditional GPD: fit on low-Z and high-Z halves of the exceedance set."""
    threshold_quantile: float
    threshold_value: float
    z_split_quantile: float
    z_split_value: float
    low_z: GPDFitResult
    high_z: GPDFitResult
    shape_diff: float                                # ξ_high − ξ_low
    shape_diff_bootstrap_ci_95: tuple[float, float]
    shape_diff_bootstrap_p_value: float              # one-sided: P(ξ_high − ξ_low ≤ 0)


def gpd_conditional_on_z(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    *,
    threshold_quantile: float = 0.95,
    z_split_quantile: float = 0.5,
    n_boot: int = 200,
    seed: int = 0,
) -> GPDConditionalResult:
    """Fit GPD separately to low-Z and high-Z halves of the exceedance set.

    Procedure:
      1. threshold = empirical quantile of Y at `threshold_quantile`
      2. exceedances = rows where Y > threshold
      3. z_split = empirical quantile of Z[exceedances] at `z_split_quantile`
      4. low_z subset = exceedances where Z ≤ z_split
         high_z subset = exceedances where Z > z_split
      5. Fit GPD on each subset independently
      6. Bootstrap: resample exceedance row indices (paired Y,Z) with replacement,
         recompute z_split inside each bootstrap rep, refit both subsets, record
         shape_diff = ξ_high - ξ_low. Return 2.5%/97.5% quantiles plus one-sided
         p-value (fraction of bootstrap reps with shape_diff ≤ 0).
    """
    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    if len(Y_arr) != len(Z_arr):
        raise ValueError(f"Y and Z must have equal length; got {len(Y_arr)} vs {len(Z_arr)}")
    if not 0.0 < threshold_quantile < 1.0:
        raise ValueError(f"threshold_quantile must be in (0,1); got {threshold_quantile}")
    if not 0.0 < z_split_quantile < 1.0:
        raise ValueError(f"z_split_quantile must be in (0,1); got {z_split_quantile}")

    threshold = float(np.quantile(Y_arr, threshold_quantile))
    exceed_mask = Y_arr > threshold
    Y_exc = Y_arr[exceed_mask]
    Z_exc = Z_arr[exceed_mask]
    if len(Y_exc) < 20:
        raise ValueError(
            f"too few exceedances ({len(Y_exc)}) above threshold_quantile={threshold_quantile} "
            f"for a Z-split test (need ≥20)"
        )

    z_split = float(np.quantile(Z_exc, z_split_quantile))
    low_mask = Z_exc <= z_split
    high_mask = ~low_mask

    if low_mask.sum() < 10 or high_mask.sum() < 10:
        raise ValueError(
            f"too few exceedances per subset at z_split_quantile={z_split_quantile}: "
            f"low_z={int(low_mask.sum())}, high_z={int(high_mask.sum())} (each needs ≥10)"
        )

    low_z_fit = fit_gpd(Y_exc[low_mask], threshold=threshold)
    high_z_fit = fit_gpd(Y_exc[high_mask], threshold=threshold)
    shape_diff = high_z_fit.shape - low_z_fit.shape

    # Bootstrap on shape_diff: resample exceedance indices, recompute split,
    # refit both. Skip reps where either subset has too few obs.
    rng = np.random.default_rng(seed)
    n_exc = len(Y_exc)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_exc, size=n_exc)
        Y_b = Y_exc[idx]
        Z_b = Z_exc[idx]
        z_split_b = float(np.quantile(Z_b, z_split_quantile))
        low_b = Z_b <= z_split_b
        high_b = ~low_b
        if low_b.sum() < 10 or high_b.sum() < 10:
            continue
        try:
            low_fit_b = fit_gpd(Y_b[low_b], threshold=threshold)
            high_fit_b = fit_gpd(Y_b[high_b], threshold=threshold)
        except ValueError:
            continue
        diffs.append(high_fit_b.shape - low_fit_b.shape)

    if len(diffs) < 20:
        ci = (float("nan"), float("nan"))
        p_value = float("nan")
    else:
        arr = np.asarray(diffs)
        ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
        # One-sided test: alternative is shape_diff > 0
        p_value = float(np.mean(arr <= 0.0))

    return GPDConditionalResult(
        threshold_quantile=float(threshold_quantile),
        threshold_value=threshold,
        z_split_quantile=float(z_split_quantile),
        z_split_value=z_split,
        low_z=low_z_fit,
        high_z=high_z_fit,
        shape_diff=float(shape_diff),
        shape_diff_bootstrap_ci_95=ci,
        shape_diff_bootstrap_p_value=p_value,
    )


def gpd_threshold_sweep(
    Y: np.ndarray | pd.Series,
    *,
    quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    n_boot: int = 200,
    seed: int = 0,
) -> list[GPDFitResult]:
    """Fit GPD at each threshold quantile; report shape stability via bootstrap CI.

    For each `q ∈ quantiles`:
      1. threshold = empirical quantile of Y at q
      2. Fit GPD at that threshold (`fit_gpd`)
      3. Bootstrap CI on shape: pair-resample row indices of Y, refit, take
         2.5%/97.5% quantiles of the shape estimates
      4. Return a list of `GPDFitResult` with bootstrap CIs filled in

    Quantiles must be sorted ascending and in (0, 1). Raises ValueError otherwise.
    """
    Y_arr = np.asarray(Y, dtype=float)
    if not all(0.0 < q < 1.0 for q in quantiles):
        raise ValueError(f"quantiles must be in (0, 1); got {quantiles}")
    if list(quantiles) != sorted(quantiles):
        raise ValueError(f"quantiles must be sorted ascending; got {quantiles}")

    results: list[GPDFitResult] = []
    for i, q in enumerate(quantiles):
        threshold = float(np.quantile(Y_arr, q))
        # Per-quantile seed offset so each fit uses a different bootstrap stream
        ci_lo, ci_hi = _bootstrap_shape_ci(
            Y_arr, threshold=threshold, n_boot=n_boot, seed=seed + i,
        )
        base = fit_gpd(Y_arr, threshold=threshold)
        # Replace the (nan, nan) placeholder with the bootstrap CI
        result = GPDFitResult(
            threshold_quantile=base.threshold_quantile,
            threshold_value=base.threshold_value,
            shape=base.shape,
            shape_se=base.shape_se,
            shape_bootstrap_ci_95=(ci_lo, ci_hi),
            scale=base.scale,
            scale_se=base.scale_se,
            n_exceedances=base.n_exceedances,
        )
        results.append(result)
    return results
