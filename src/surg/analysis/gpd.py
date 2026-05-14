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


def _assign_groups(Z: np.ndarray, edges: tuple[float, ...]) -> list[np.ndarray]:
    """Return a list of boolean masks partitioning Z into len(edges)+1 groups.

    Group 0: Z ≤ edges[0]; group k (1 ≤ k ≤ N-1): edges[k-1] < Z ≤ edges[k];
    group N: Z > edges[N-1]. Lower bound of group 0 is −∞; upper bound of
    group N is +∞. Edges should be sorted ascending; behavior on unsorted
    edges is undefined.
    """
    masks: list[np.ndarray] = []
    prev = -np.inf
    for edge in edges:
        masks.append((Z > prev) & (Z <= edge))
        prev = edge
    masks.append(Z > prev)
    return masks


@dataclass(frozen=True, slots=True)
class GPDQuantileSplitResult:
    """N-way Z-quantile split of GPD fits on exceedances of a fixed threshold.

    `quantile_fits` has length `len(split_quantiles) + 1` (N+1 groups for N
    split points). `quantile_edges` are the empirical Z values at each
    `split_quantile` computed within the exceedance set. `extreme_contrast`
    is the (last − first) shape contrast — for quartile split this is the
    headline Q4 − Q1.

    The two-sided bootstrap p-value tests H0: extreme_contrast = 0 against
    a two-sided alternative; the sign of the CI determines the direction
    of any rejection. Bootstrap protocol: resample exceedance row indices
    (paired Y,Z), recompute quantile edges inside each rep, refit all N+1
    GPDs per rep.
    """
    threshold_quantile: float
    threshold_value: float
    split_quantiles: tuple[float, ...]
    quantile_edges: tuple[float, ...]
    quantile_fits: tuple[GPDFitResult, ...]
    extreme_contrast: float                                    # ξ_last − ξ_first
    extreme_contrast_bootstrap_ci_95: tuple[float, float]
    extreme_contrast_bootstrap_p_value: float                  # two-sided


def gpd_quantile_split_on_z(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    *,
    threshold_quantile: float = 0.95,
    split_quantiles: tuple[float, ...] = (0.25, 0.5, 0.75),
    n_boot: int = 200,
    seed: int = 0,
) -> GPDQuantileSplitResult:
    """N-way GPD fit conditional on Z-quantile groups within exceedances of Y.

    Generalizes `gpd_conditional_on_z` (which is fixed at N=2). Procedure:
      1. threshold = empirical quantile of Y at `threshold_quantile`
      2. exceedances = rows where Y > threshold
      3. quantile_edges = empirical quantile of Z[exceedances] at each
         `split_quantile` — yields N edges for N+1 groups
      4. Fit GPD on each of the N+1 groups independently (each carries the
         parent `threshold_quantile`, same convention as `gpd_conditional_on_z`)
      5. Bootstrap: resample exceedance row indices, recompute edges per rep,
         refit all groups, record extreme_contrast = ξ_last − ξ_first. Report
         empirical 2.5%/97.5% quantiles of resampled contrasts as the 95% CI,
         and two-sided bootstrap p-value = 2 * min(P(contrast ≤ 0), P(contrast ≥ 0)).

    Note on p-value semantics: the returned two-sided p-value is an empirical
    bootstrap "achieved significance level" (2 * min(P(arr ≤ 0), P(arr ≥ 0))),
    matching the heuristic convention used by `gpd_conditional_on_z`. It is
    not a formal hypothesis-test p-value; Holm–Bonferroni corrections applied
    downstream inherit this heuristic status.

    Raises:
      ValueError if length(Y) ≠ length(Z), if `split_quantiles` is unsorted /
      out-of-range, if too few exceedances overall (< 20), or if any quantile
      group ends up with < 10 exceedances (fit too noisy).
    """
    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    if len(Y_arr) != len(Z_arr):
        raise ValueError(f"Y and Z must have equal length; got {len(Y_arr)} vs {len(Z_arr)}")
    if not 0.0 < threshold_quantile < 1.0:
        raise ValueError(f"threshold_quantile must be in (0,1); got {threshold_quantile}")
    if len(split_quantiles) == 0:
        raise ValueError("split_quantiles must have at least one entry")
    if not all(0.0 < q < 1.0 for q in split_quantiles):
        raise ValueError(f"split_quantiles must be in (0,1); got {split_quantiles}")
    if len(split_quantiles) != len(set(split_quantiles)):
        raise ValueError(
            f"split_quantiles must be unique; got {split_quantiles}"
        )
    if list(split_quantiles) != sorted(split_quantiles):
        raise ValueError(
            f"split_quantiles must be strictly ascending; got {split_quantiles}"
        )

    threshold = float(np.quantile(Y_arr, threshold_quantile))
    exceed_mask = Y_arr > threshold
    Y_exc = Y_arr[exceed_mask]
    Z_exc = Z_arr[exceed_mask]
    if len(Y_exc) < 20:
        raise ValueError(
            f"too few exceedances ({len(Y_exc)}) above threshold_quantile={threshold_quantile} "
            f"for an N-way Z-split test (need ≥20)"
        )

    # N edges → N+1 groups indexed 0..N
    edges = tuple(float(np.quantile(Z_exc, q)) for q in split_quantiles)
    group_masks = _assign_groups(Z_exc, edges)
    counts = tuple(int(m.sum()) for m in group_masks)
    if any(c < 10 for c in counts):
        raise ValueError(
            f"too few exceedances per subset at split_quantiles={split_quantiles}: "
            f"counts={counts} (each needs ≥10)"
        )

    fits: list[GPDFitResult] = []
    for mask in group_masks:
        _base = fit_gpd(Y_exc[mask], threshold=threshold)
        fits.append(GPDFitResult(
            threshold_quantile=float(threshold_quantile),
            threshold_value=_base.threshold_value,
            shape=_base.shape,
            shape_se=_base.shape_se,
            shape_bootstrap_ci_95=_base.shape_bootstrap_ci_95,
            scale=_base.scale,
            scale_se=_base.scale_se,
            n_exceedances=_base.n_exceedances,
        ))
    extreme_contrast = fits[-1].shape - fits[0].shape

    # Bootstrap: pair-resample exceedance indices, recompute edges per rep,
    # refit all groups. Skip reps where any group ends up with < 10 obs.
    rng = np.random.default_rng(seed)
    n_exc = len(Y_exc)
    contrasts: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_exc, size=n_exc)
        Y_b = Y_exc[idx]
        Z_b = Z_exc[idx]
        edges_b = tuple(float(np.quantile(Z_b, q)) for q in split_quantiles)
        masks_b = _assign_groups(Z_b, edges_b)
        if any(m.sum() < 10 for m in masks_b):
            continue
        try:
            shapes_b = [fit_gpd(Y_b[m], threshold=threshold).shape for m in masks_b]
        except ValueError:
            continue
        contrasts.append(shapes_b[-1] - shapes_b[0])

    if len(contrasts) < 20:
        ci: tuple[float, float] = (float("nan"), float("nan"))
        p_two_sided = float("nan")
    else:
        arr = np.asarray(contrasts)
        ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
        p_left = float(np.mean(arr <= 0.0))
        p_right = float(np.mean(arr >= 0.0))
        p_two_sided = min(1.0, 2.0 * min(p_left, p_right))

    return GPDQuantileSplitResult(
        threshold_quantile=float(threshold_quantile),
        threshold_value=threshold,
        split_quantiles=tuple(float(q) for q in split_quantiles),
        quantile_edges=edges,
        quantile_fits=tuple(fits),
        extreme_contrast=float(extreme_contrast),
        extreme_contrast_bootstrap_ci_95=ci,
        extreme_contrast_bootstrap_p_value=p_two_sided,
    )


def holm_bonferroni_two_sided(
    labeled_p_values: dict[str, float],
    *,
    alpha: float = 0.05,
) -> dict:
    """Apply Holm–Bonferroni step-down correction to a family of two-sided p-values.

    Procedure (Holm 1979):
      1. Sort p-values ascending. NaN p-values (inconclusive specs) sort to
         the end (treated as p = +inf for ranking; never rejected).
      2. Test the smallest at α/k where k is the family size, the next at
         α/(k-1), … , the largest at α/1.
      3. Stop at the first non-rejection: all p-values not yet considered
         remain non-rejected, regardless of their value.

    Returns a dict with:
      - "alpha": the input α
      - "sorted_order": list of input labels in ascending-p order (NaNs last)
      - "adjusted_thresholds": dict mapping each label to its α/(k-rank) threshold
      - "rejections": dict mapping each label to a bool
      - "family_wise_rejection": True iff every input was rejected (i.e., the
        family-wise inferential statement is supported)

    Raises:
      ValueError if α ∉ (0, 1) or any p-value falls outside [0, 1] (NaN is allowed).
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1); got {alpha}")
    for label, p in labeled_p_values.items():
        if math.isnan(p):
            continue
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p-value for {label!r} must be in [0, 1] or NaN; got {p}")

    k = len(labeled_p_values)
    # Sort ascending; NaN goes last
    def _sort_key(item: tuple[str, float]) -> tuple[int, float]:
        label, p = item
        if math.isnan(p):
            return (1, 0.0)  # NaN bucket — order within doesn't matter for the alg
        return (0, p)

    sorted_items = sorted(labeled_p_values.items(), key=_sort_key)
    sorted_order = [label for label, _ in sorted_items]
    adjusted_thresholds: dict[str, float] = {}
    rejections: dict[str, bool] = {}
    stopped = False
    for rank, (label, p) in enumerate(sorted_items):
        threshold = alpha / (k - rank)
        adjusted_thresholds[label] = threshold
        if stopped or math.isnan(p) or p > threshold:
            rejections[label] = False
            stopped = True
        else:
            rejections[label] = True

    return {
        "alpha": alpha,
        "sorted_order": sorted_order,
        "adjusted_thresholds": adjusted_thresholds,
        "rejections": rejections,
        "family_wise_rejection": all(rejections.values()),
    }


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
