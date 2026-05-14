"""Unit tests for src/surg/analysis/gpd_continuous.py — Spec B module."""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from surg.analysis.gpd_continuous import (
    GPDContinuousFitResult,
    _design_matrix,
    _initial_params,
    _neg_log_likelihood_nonstationary_gpd,
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
    # slots=True prevents __dict__ creation
    assert not hasattr(result, '__dict__'), "slots=True should prevent instance __dict__"


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
    where β₀ and σ₀ are taken directly from fit_gpd's output (exact equality)."""
    from surg.analysis.gpd import fit_gpd
    rng = np.random.default_rng(seed=42)
    Y_exc = stats.genpareto.rvs(c=0.3, scale=2.0, size=500, random_state=rng)
    init = _initial_params(Y_exc, form="linear")
    base = fit_gpd(Y_exc, threshold=0.0)
    # Linear shape: [β₀, β₁]; Scale: [σ₀ (log scale), σ₁]
    assert len(init) == 4
    beta_0, beta_1, sigma_0_log, sigma_1 = init
    # Exact equality: β₀ comes from base.shape
    assert beta_0 == base.shape, \
        f"β₀ should equal stationary fit_gpd.shape: {beta_0} vs {base.shape}"
    # β₁ should be 0 (no Z dependence in initial guess)
    assert beta_1 == 0.0
    # σ₀ = log(scale) — exact equality via math.log
    assert sigma_0_log == math.log(base.scale), \
        f"σ₀ should equal math.log(fit_gpd.scale): {sigma_0_log} vs {math.log(base.scale)}"
    # σ₁ should be 0
    assert sigma_1 == 0.0


def test_initial_params_spline_returns_six_params():
    """Spline form initial params: 4 shape params + 2 scale params = 6 total.
    Intercepts come exactly from fit_gpd."""
    from surg.analysis.gpd import fit_gpd
    rng = np.random.default_rng(seed=42)
    Y_exc = stats.genpareto.rvs(c=0.3, scale=2.0, size=500, random_state=rng)
    init = _initial_params(Y_exc, form="spline")
    base = fit_gpd(Y_exc, threshold=0.0)
    assert len(init) == 6
    # First 4 are shape (β₀, β₁, β₂, β₃); β₀ exact from fit_gpd, others 0
    assert init[0] == base.shape
    assert init[1] == 0.0
    assert init[2] == 0.0
    assert init[3] == 0.0
    # Last 2 are scale (σ₀ log, σ₁) — σ₀ exact from log(fit_gpd.scale)
    assert init[4] == math.log(base.scale)
    assert init[5] == 0.0


def test_neg_log_likelihood_finite_on_valid_params():
    """For valid parameters, the negative log-likelihood returns a finite float."""
    rng = np.random.default_rng(seed=42)
    Y_exc = stats.genpareto.rvs(c=0.3, scale=2.0, size=200, random_state=rng)
    Z_exc = rng.uniform(1.0, 10.0, size=200)
    X_xi = _design_matrix(Z_exc, form="linear")
    X_sigma = _design_matrix(Z_exc, form="linear", for_scale=True)
    # Reasonable params: shape ≈ 0.3, scale ≈ 2.0
    params = np.array([0.3, 0.0, math.log(2.0), 0.0])  # β₀, β₁, σ₀_log, σ₁
    nll = _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)
    assert math.isfinite(nll), f"NLL not finite: {nll}"
    assert nll > 0, f"NLL should be > 0 for positive sample: {nll}"


def test_neg_log_likelihood_returns_inf_on_negative_scale_implied():
    """If σ(Z) implied is non-positive for any observation, NLL returns +inf.

    Constructed: σ₀ = log(0.1), σ₁ = very negative → at high Z, σ(Z) underflows.
    Actually since we use exp(σ₀ + σ₁·Z), σ(Z) is always positive — this test
    instead probes the support violation: 1 + ξ(Z) * Y_exc / σ(Z) <= 0.
    """
    Y_exc = np.array([100.0, 200.0, 50.0])  # large exceedances
    Z_exc = np.array([1.0, 2.0, 3.0])
    X_xi = _design_matrix(Z_exc, form="linear")
    X_sigma = _design_matrix(Z_exc, form="linear", for_scale=True)
    # Force ξ(Z) very negative such that 1 + ξ·u/σ ≤ 0 for at least one obs
    params = np.array([-1.0, -0.5, math.log(1.0), 0.0])  # β₀=-1, β₁=-0.5 → ξ(3) = -2.5
    nll = _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)
    assert math.isinf(nll) and nll > 0, f"Expected +inf for support violation; got {nll}"


def test_neg_log_likelihood_matches_stationary_genpareto_when_z_terms_zero():
    """When β₁ = σ₁ = 0 (stationary special case), the non-stationary NLL
    matches scipy.stats.genpareto's log-pdf sum."""
    rng = np.random.default_rng(seed=42)
    true_shape, true_scale = 0.3, 2.0
    Y_exc = stats.genpareto.rvs(c=true_shape, scale=true_scale, size=300, random_state=rng)
    Z_exc = rng.uniform(1.0, 10.0, size=300)  # Z doesn't matter for stationary case
    X_xi = _design_matrix(Z_exc, form="linear")
    X_sigma = _design_matrix(Z_exc, form="linear", for_scale=True)
    params = np.array([true_shape, 0.0, math.log(true_scale), 0.0])

    nll_ours = _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)
    nll_scipy = -np.sum(stats.genpareto.logpdf(Y_exc, c=true_shape, loc=0.0, scale=true_scale))

    assert math.isclose(nll_ours, nll_scipy, rel_tol=1e-6), \
        f"Stationary NLL mismatch: ours={nll_ours}, scipy={nll_scipy}"


def test_neg_log_likelihood_handles_xi_near_zero_via_exponential_limit():
    """When ξ(Z) ≈ 0 for all Z (exponential tail), NLL uses the exponential
    log-density limit, not the genpareto formula (which would have 1/0 issues)."""
    Y_exc = np.array([1.0, 2.0, 3.0, 0.5, 4.0])
    Z_exc = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    X_xi = _design_matrix(Z_exc, form="linear")
    X_sigma = _design_matrix(Z_exc, form="linear", for_scale=True)
    # ξ exactly 0 at intercept, β₁=0 → ξ(Z) = 0 for all
    params = np.array([0.0, 0.0, math.log(2.0), 0.0])
    nll = _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)
    # Expected exponential NLL: sum(log σ + Y/σ) = n*log(2) + sum(Y)/2
    n = len(Y_exc)
    expected = n * math.log(2.0) + Y_exc.sum() / 2.0
    assert math.isclose(nll, expected, rel_tol=1e-6), \
        f"Exponential-limit NLL mismatch: got {nll}, expected {expected}"
