"""Conditional quantile regression at τ=0.99 — robustness check on TAR.

Three specifications per the design spec §5:
  1. Linear baseline: Q_τ(Y|Z) = γ₀ + γ₁·Z
  2. Threshold dummy at TAR's ĉ: Q_τ(Y|Z) = δ₀ + δ₁·Z + δ₂·(Z−c)·I(Z>c)
  3. B-spline non-parametric: Q_τ(Y|Z) = f(Z); kink location estimated
     by finding where the second derivative of f peaks.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.interpolate import UnivariateSpline


@dataclass(frozen=True, slots=True)
class QRLinearResult:
    intercept: float
    slope: float
    slope_p_value: float
    tau: float
    n: int


@dataclass(frozen=True, slots=True)
class QRThresholdDummyResult:
    intercept: float
    slope: float
    slope_p_value: float   # p-value on the within-regime slope (delta_1)
    kink_coef: float       # the δ₂ coefficient on (Z-c)·I(Z>c)
    kink_p_value: float
    c: float
    tau: float
    n: int


def fit_qr_linear(Y: np.ndarray, Z: np.ndarray, *, tau: float = 0.99) -> QRLinearResult:
    """Linear quantile regression: Q_τ(Y|Z) = γ₀ + γ₁·Z."""
    Y, Z = np.asarray(Y), np.asarray(Z)
    if len(Y) != len(Z):
        raise ValueError(f"Y and Z must have equal length, got {len(Y)} vs {len(Z)}")
    X = sm.add_constant(Z)
    model = sm.QuantReg(Y, X).fit(q=tau)
    return QRLinearResult(
        intercept=float(model.params[0]),
        slope=float(model.params[1]),
        slope_p_value=float(model.pvalues[1]),
        tau=tau,
        n=len(Y),
    )


def fit_qr_threshold_dummy(
    Y: np.ndarray, Z: np.ndarray, *, c: float, tau: float = 0.99,
) -> QRThresholdDummyResult:
    """Quantile regression with explicit threshold dummy at c."""
    Y, Z = np.asarray(Y), np.asarray(Z)
    if len(Y) != len(Z):
        raise ValueError(f"Y and Z must have equal length, got {len(Y)} vs {len(Z)}")
    if not (Z.min() <= c <= Z.max()):
        raise ValueError(
            f"c={c} is outside Z range [{Z.min():.4g}, {Z.max():.4g}]; "
            f"kink basis would be degenerate"
        )
    kink = np.where(Z > c, Z - c, 0.0)
    X = np.column_stack([np.ones(len(Z)), Z, kink])
    model = sm.QuantReg(Y, X).fit(q=tau)
    return QRThresholdDummyResult(
        intercept=float(model.params[0]),
        slope=float(model.params[1]),
        slope_p_value=float(model.pvalues[1]),
        kink_coef=float(model.params[2]),
        kink_p_value=float(model.pvalues[2]),
        c=c,
        tau=tau,
        n=len(Y),
    )


@dataclass(frozen=True, slots=True)
class QRSplineResult:
    kink_location: float       # Z value where the slope curvature peaks
    curve_z: np.ndarray        # grid of Z values
    curve_q: np.ndarray        # estimated Q_τ at each curve_z
    tau: float
    n: int


def fit_qr_bspline(
    Y: np.ndarray, Z: np.ndarray, *, tau: float = 0.99,
    n_knots: int = 5, n_grid: int = 200,
) -> QRSplineResult:
    """Non-parametric quantile regression via B-spline basis on Z.

    Strategy: place knots at evenly-spaced Z quantiles; build the spline
    basis manually using piecewise-linear (truncated power) functions;
    run statsmodels QuantReg. Then for kink-location, fit a smoothing
    spline to (Z_grid, Q_grid) and report where its second derivative
    is largest.
    """
    # Knots at interior quantiles
    knot_qs = np.linspace(0.1, 0.9, n_knots)
    knots = np.quantile(Z, knot_qs)

    # Piecewise-linear basis: 1, Z, (Z - knot_k)_+ for k=1..n_knots
    basis_cols = [np.ones(len(Z)), Z]
    for k in knots:
        basis_cols.append(np.maximum(Z - k, 0.0))
    X = np.column_stack(basis_cols)
    model = sm.QuantReg(Y, X).fit(q=tau)

    # Evaluate the fitted curve on a Z grid
    z_lo, z_hi = float(np.quantile(Z, 0.02)), float(np.quantile(Z, 0.98))
    z_grid = np.linspace(z_lo, z_hi, n_grid)
    basis_grid_cols = [np.ones(n_grid), z_grid]
    for k in knots:
        basis_grid_cols.append(np.maximum(z_grid - k, 0.0))
    X_grid = np.column_stack(basis_grid_cols)
    q_grid = X_grid @ model.params

    # Kink location: argmax of |second derivative| of the curve
    second_deriv = np.gradient(np.gradient(q_grid, z_grid), z_grid)
    kink_idx = int(np.argmax(np.abs(second_deriv)))
    kink_location = float(z_grid[kink_idx])

    return QRSplineResult(
        kink_location=kink_location,
        curve_z=z_grid,
        curve_q=q_grid,
        tau=tau,
        n=len(Y),
    )
