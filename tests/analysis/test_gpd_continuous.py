"""Unit tests for src/surg/analysis/gpd_continuous.py — Spec B module."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from surg.analysis.gpd_continuous import (
    GPDContinuousFitResult,
    _design_matrix,
    _initial_params,
)


def test_gpd_continuous_fit_result_is_frozen_slots_dataclass():
    """GPDContinuousFitResult must be a frozen+slots dataclass (matching module convention)."""
    result = GPDContinuousFitResult(
        form="linear",
        threshold_quantile=0.95,
        threshold_value=10.0,
        n_exceedances=100,
        shape_coefficients=(0.5, -0.01),
        shape_coefficients_bootstrap_ci_95=((0.4, 0.6), (-0.02, 0.0)),
        scale_coefficients=(2.0, 0.05),
        scale_coefficients_bootstrap_ci_95=((1.8, 2.2), (0.03, 0.07)),
        headline_slope_or_lrt=-0.01,
        headline_p_value=0.04,
        convergence_status="converged",
    )
    assert result.form == "linear"
    with pytest.raises(Exception):
        result.form = "spline"  # frozen


def test_design_matrix_linear_returns_two_columns():
    """Linear form: design matrix has columns [1, Z] for shape regression."""
    Z = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    X = _design_matrix(Z, form="linear")
    assert X.shape == (5, 2)
    assert np.allclose(X[:, 0], 1.0)
    assert np.allclose(X[:, 1], Z)


def test_design_matrix_spline_returns_four_columns_polynomial_basis():
    """Spline form: design matrix has columns [1, Z, Z², Z³] (polynomial-degree-3 basis,
    4 DOF total, equivalent capability to a 4-DOF natural cubic spline)."""
    Z = np.array([0.0, 1.0, 2.0, 3.0])
    X = _design_matrix(Z, form="spline")
    assert X.shape == (4, 4)
    assert np.allclose(X[:, 0], 1.0)
    assert np.allclose(X[:, 1], Z)
    assert np.allclose(X[:, 2], Z ** 2)
    assert np.allclose(X[:, 3], Z ** 3)


def test_design_matrix_validates_form():
    """Invalid form raises ValueError."""
    Z = np.array([1.0, 2.0])
    with pytest.raises(ValueError, match="form"):
        _design_matrix(Z, form="quadratic")


def test_design_matrix_scale_always_linear():
    """Scale design matrix is always linear ([1, Z]) regardless of shape form;
    `for_scale=True` flag returns the scale matrix."""
    Z = np.array([1.0, 2.0, 3.0])
    X_sigma = _design_matrix(Z, form="linear", for_scale=True)
    assert X_sigma.shape == (3, 2)
    assert np.allclose(X_sigma[:, 0], 1.0)
    assert np.allclose(X_sigma[:, 1], Z)
    # Even with form="spline" for shape, scale design matrix is linear
    X_sigma_spline_scale = _design_matrix(Z, form="spline", for_scale=True)
    assert X_sigma_spline_scale.shape == (3, 2)


def test_initial_params_linear_uses_stationary_fit_as_intercepts():
    """Initial params for linear form: stationary GPD fit gives [β₀, 0, σ₀, 0]
    where β₀=shape and σ₀=log(scale) from the stationary fit."""
    rng = np.random.default_rng(seed=42)
    Y_exc = stats.genpareto.rvs(c=0.3, scale=2.0, size=500, random_state=rng)
    init = _initial_params(Y_exc, form="linear")
    # Linear shape: [β₀, β₁]; Scale: [σ₀ (log scale), σ₁]
    assert len(init) == 4
    beta_0, beta_1, sigma_0_log, sigma_1 = init
    # β₀ should be near the planted shape (0.3) within MLE noise
    assert abs(beta_0 - 0.3) < 0.2, f"β₀ initial too far from stationary: {beta_0}"
    # β₁ should be 0 (no Z dependence in initial guess)
    assert beta_1 == 0.0
    # σ₀ = log(scale) should be near log(2.0) = 0.693
    assert abs(sigma_0_log - math.log(2.0)) < 0.5, f"σ₀ initial off: {sigma_0_log}"
    # σ₁ should be 0
    assert sigma_1 == 0.0


def test_initial_params_spline_returns_six_params():
    """Spline form initial params: 4 shape params + 2 scale params = 6 total."""
    rng = np.random.default_rng(seed=42)
    Y_exc = stats.genpareto.rvs(c=0.3, scale=2.0, size=500, random_state=rng)
    init = _initial_params(Y_exc, form="spline")
    assert len(init) == 6
    # First 4 are shape (β₀, β₁, β₂, β₃); β₀ ≈ planted shape, others 0
    assert abs(init[0] - 0.3) < 0.2
    assert init[1] == 0.0
    assert init[2] == 0.0
    assert init[3] == 0.0
    # Last 2 are scale (σ₀ log, σ₁)
    assert abs(init[4] - math.log(2.0)) < 0.5
    assert init[5] == 0.0
