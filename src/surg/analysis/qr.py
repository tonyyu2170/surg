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
    kink_coef: float       # the δ₂ coefficient on (Z-c)·I(Z>c)
    kink_p_value: float
    c: float
    tau: float
    n: int


def fit_qr_linear(Y: np.ndarray, Z: np.ndarray, *, tau: float = 0.99) -> QRLinearResult:
    """Linear quantile regression: Q_τ(Y|Z) = γ₀ + γ₁·Z."""
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
    kink = np.where(Z > c, Z - c, 0.0)
    X = np.column_stack([np.ones(len(Z)), Z, kink])
    model = sm.QuantReg(Y, X).fit(q=tau)
    return QRThresholdDummyResult(
        intercept=float(model.params[0]),
        slope=float(model.params[1]),
        kink_coef=float(model.params[2]),
        kink_p_value=float(model.pvalues[2]),
        c=c,
        tau=tau,
        n=len(Y),
    )
