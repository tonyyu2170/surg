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
