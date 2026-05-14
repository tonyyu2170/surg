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
      5. Fit GPD on each subset independently; nested `threshold_quantile`
         is the parent's input value (the subset arrays contain only
         exceedances by construction, so a recomputed quantile would be 0.0)
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

    _low = fit_gpd(Y_exc[low_mask], threshold=threshold)
    low_z_fit = GPDFitResult(
        threshold_quantile=float(threshold_quantile),
        threshold_value=_low.threshold_value,
        shape=_low.shape,
        shape_se=_low.shape_se,
        shape_bootstrap_ci_95=_low.shape_bootstrap_ci_95,
        scale=_low.scale,
        scale_se=_low.scale_se,
        n_exceedances=_low.n_exceedances,
    )
    _high = fit_gpd(Y_exc[high_mask], threshold=threshold)
    high_z_fit = GPDFitResult(
        threshold_quantile=float(threshold_quantile),
        threshold_value=_high.threshold_value,
        shape=_high.shape,
        shape_se=_high.shape_se,
        shape_bootstrap_ci_95=_high.shape_bootstrap_ci_95,
        scale=_high.scale,
        scale_se=_high.scale_se,
        n_exceedances=_high.n_exceedances,
    )
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


def _nan_to_none(obj):
    """Recursively replace float NaN/inf with None for JSON serialization."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, list):
        return [_nan_to_none(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _nan_to_none(v) for k, v in obj.items()}
    return obj


def _gpd_fit_result_to_dict(fit: GPDFitResult) -> dict:
    return {
        "threshold_quantile": fit.threshold_quantile,
        "threshold_value": fit.threshold_value,
        "n_exceedances": fit.n_exceedances,
        "shape": fit.shape,
        "shape_se": fit.shape_se,
        "shape_bootstrap_ci_95": list(fit.shape_bootstrap_ci_95),
        "scale": fit.scale,
        "scale_se": fit.scale_se,
    }


def run_gpd(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    response_col: str,
    pnode_label: str,
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    sweep_quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    conditional_threshold_quantile: float = 0.95,
    z_split_quantile: float = 0.5,
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """End-to-end GPD analysis on the full panel: threshold sweep + Z-conditional split.

    Writes a JSON file at `out_path` matching the schema documented in
    `docs/plans/2026-05-13-strategy-c-modules.md` § "Module: gpd.py".

    Drops NaN rows in [response_col, threshold_col] only; does NOT filter by
    `passes_proposal_filter` — Strategy C operates on the full panel.

    Raises:
        ValueError: propagated from fit_gpd if any threshold quantile in
        sweep_quantiles produces fewer than 10 exceedances. Callers (such
        as run_all in Task 10) should guard against small or bounded
        response columns before invoking this function.
    """
    n_total = len(panel)
    subset = panel.dropna(subset=[response_col, threshold_col])
    Y = subset[response_col].to_numpy()
    Z = subset[threshold_col].to_numpy()
    n_after_dropna = len(subset)

    sweep_results = gpd_threshold_sweep(
        Y, quantiles=sweep_quantiles, n_boot=n_boot, seed=seed,
    )
    cond_result = gpd_conditional_on_z(
        Y, Z,
        threshold_quantile=conditional_threshold_quantile,
        z_split_quantile=z_split_quantile,
        n_boot=n_boot,
        seed=seed + 100,  # offset so sweep and conditional use disjoint bootstrap streams
    )

    payload = {
        "pnode_label": pnode_label,
        "response_col": response_col,
        "threshold_col": threshold_col,
        "n_total_panel": int(n_total),
        "n_after_dropna": int(n_after_dropna),
        "threshold_sweep": [_gpd_fit_result_to_dict(fit) for fit in sweep_results],
        "conditional_z": {
            "threshold_quantile": cond_result.threshold_quantile,
            "threshold_value": cond_result.threshold_value,
            "z_split_quantile": cond_result.z_split_quantile,
            "z_split_value": cond_result.z_split_value,
            "low_z": _gpd_fit_result_to_dict(cond_result.low_z),
            "high_z": _gpd_fit_result_to_dict(cond_result.high_z),
            "shape_difference": {
                "diff": cond_result.shape_diff,
                "bootstrap_ci_95": list(cond_result.shape_diff_bootstrap_ci_95),
                "bootstrap_p_value": cond_result.shape_diff_bootstrap_p_value,
            },
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_nan_to_none(payload), indent=2))
