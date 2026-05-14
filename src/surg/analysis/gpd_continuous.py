"""Non-stationary Generalized Pareto Distribution fits with covariates on shape and scale.

Spec B module (sub-question 1 closure) — fits ξ(Z) = β₀ + β₁·Z (linear) or
ξ(Z) = β₀ + β₁·Z + β₂·Z² + β₃·Z³ (polynomial-degree-3, 4 DOF). Scale is
always log-linear: log σ(Z) = σ₀ + σ₁·Z.

The polynomial-degree-3 basis (4 DOF: intercept + linear + quadratic + cubic)
matches the design's "4-DOF flexible shape" intent. A natural cubic spline
with K=3 interior knots gives only 3 DOF per ESL convention (basis is K
functions including intercept); a 4-DOF natural cubic spline would need K=4
knots + knot placement. Polynomial basis avoids the knot-placement decision
and gives identical capability within the observed Z range.

Implementation reference: Davison & Smith 1990 (JRSS-B), Coles 2001 §6.3.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats

from surg.analysis.gpd import fit_gpd


@dataclass(frozen=True, slots=True)
class GPDContinuousFitResult:
    """Non-stationary GPD fit with covariate Z on shape and scale.

    `shape_coefficients`: linear form → (β₀, β₁); spline form → (β₀, β₁, β₂, β₃).
    `scale_coefficients`: always (σ₀ (log-scale intercept), σ₁) since scale form
    is fixed at log-linear regardless of shape form.
    `headline_slope_or_lrt`: β₁ for linear (the headline scalar in the pre-reg);
    LRT statistic (chi² value) for spline.
    `headline_p_value`: two-sided bootstrap p-value for β₁ (linear) or bootstrap
    p-value for LRT (spline).
    `convergence_status`: "converged" | "max_iter" | "failed" |
    "insufficient_bootstrap_reps".
    """

    form: Literal["linear", "spline"]
    threshold_quantile: float
    threshold_value: float
    n_exceedances: int
    shape_coefficients: tuple[float, ...]
    shape_coefficients_bootstrap_ci_95: tuple[tuple[float, float], ...]
    scale_coefficients: tuple[float, float]
    scale_coefficients_bootstrap_ci_95: tuple[tuple[float, float], tuple[float, float]]
    headline_slope_or_lrt: float
    headline_p_value: float
    convergence_status: str


def _design_matrix(
    Z: np.ndarray,
    *,
    form: Literal["linear", "spline"],
    for_scale: bool = False,
) -> np.ndarray:
    """Construct the design matrix X for shape regression (or scale, which is
    always linear).

    Linear shape: X = [1, Z], shape=(n, 2).
    Spline shape: X = [1, Z, Z², Z³], shape=(n, 4) — polynomial-degree-3 basis.
    Scale (always linear): X = [1, Z], shape=(n, 2).
    """
    Z_arr = np.asarray(Z, dtype=float)
    if for_scale or form == "linear":
        return np.column_stack([np.ones_like(Z_arr), Z_arr])
    if form == "spline":
        return np.column_stack([np.ones_like(Z_arr), Z_arr, Z_arr ** 2, Z_arr ** 3])
    raise ValueError(f"form must be 'linear' or 'spline'; got {form!r}")


def _initial_params(
    Y_exc: np.ndarray,
    *,
    form: Literal["linear", "spline"],
) -> tuple[float, ...]:
    """Compute MLE initial values from a stationary GPD fit on Y_exc.

    Returns:
      Linear: (β₀, β₁=0, σ₀=log(scale), σ₁=0) — 4 params.
      Spline: (β₀, β₁=0, β₂=0, β₃=0, σ₀=log(scale), σ₁=0) — 6 params.

    The stationary fit handles the case where Y_exc is already exceedance over
    a threshold (in this module's context, Y_exc has already been shifted to
    be exceedance values above 0).
    """
    Y_arr = np.asarray(Y_exc, dtype=float)
    # Stationary GPD fit on the exceedances (Y_exc already over threshold=0)
    base_fit = fit_gpd(Y_arr, threshold=0.0)
    shape_init = base_fit.shape
    log_scale_init = math.log(base_fit.scale)
    if form == "linear":
        return (shape_init, 0.0, log_scale_init, 0.0)
    if form == "spline":
        return (shape_init, 0.0, 0.0, 0.0, log_scale_init, 0.0)
    raise ValueError(f"form must be 'linear' or 'spline'; got {form!r}")
