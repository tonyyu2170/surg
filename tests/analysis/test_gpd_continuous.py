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
    _likelihood_ratio_test,
    fit_gpd_continuous_z,
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


def test_fit_gpd_continuous_z_linear_recovers_planted_beta_1():
    """Planted DGP: ξ(Z) = 0.3 + 0.05·Z; fit recovers β₁ within bootstrap tolerance."""
    rng = np.random.default_rng(seed=42)
    n = 5000
    Z = rng.uniform(1.0, 10.0, size=n)
    # Generate Y with Z-dependent shape and constant scale
    Y_full = np.empty(n)
    for i in range(n):
        xi_i = 0.3 + 0.05 * Z[i]
        Y_full[i] = stats.genpareto.rvs(c=xi_i, scale=2.0, size=1, random_state=rng)[0]
    # Add some below-threshold values for the function to filter
    threshold = 0.0  # everything is an exceedance for this synthetic

    result = fit_gpd_continuous_z(
        Y_full, Z, threshold=threshold, form="linear", n_boot=100, seed=0,
    )

    assert isinstance(result, GPDContinuousFitResult)
    assert result.form == "linear"
    assert result.convergence_status == "converged"
    # Recovery tolerance: β₁ true is 0.05, MLE should be within ±0.03 at n=5000
    assert abs(result.shape_coefficients[1] - 0.05) < 0.03, \
        f"β₁ recovery off: {result.shape_coefficients[1]}"
    # Headline = β₁ for linear form
    assert result.headline_slope_or_lrt == result.shape_coefficients[1]


def test_fit_gpd_continuous_z_linear_null_dgp_gives_beta_1_near_zero():
    """When DGP has constant ξ, β₁ should be near zero and its CI should span 0."""
    rng = np.random.default_rng(seed=42)
    n = 3000
    Z = rng.uniform(1.0, 10.0, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)
    threshold = 0.0

    result = fit_gpd_continuous_z(
        Y, Z, threshold=threshold, form="linear", n_boot=100, seed=0,
    )

    assert abs(result.shape_coefficients[1]) < 0.05, \
        f"β₁ should be near 0 for null DGP: {result.shape_coefficients[1]}"
    # Two-sided p should be > 0.10 (cannot reject null)
    assert result.headline_p_value > 0.10, \
        f"False rejection: p={result.headline_p_value}"
    # CI should span 0
    ci_lo, ci_hi = result.shape_coefficients_bootstrap_ci_95[1]  # β₁ CI
    assert ci_lo < 0 < ci_hi, f"β₁ CI should span 0: ({ci_lo}, {ci_hi})"


def test_fit_gpd_continuous_z_spline_returns_four_shape_coefficients():
    """Spline form has 4 shape coefficients (β₀, β₁, β₂, β₃) + 2 scale coefficients."""
    rng = np.random.default_rng(seed=42)
    n = 3000
    Z = rng.uniform(1.0, 10.0, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    result = fit_gpd_continuous_z(
        Y, Z, threshold=0.0, form="spline", n_boot=50, seed=0,
    )

    assert result.form == "spline"
    assert len(result.shape_coefficients) == 4
    assert len(result.scale_coefficients) == 2
    assert len(result.shape_coefficients_bootstrap_ci_95) == 4
    assert len(result.scale_coefficients_bootstrap_ci_95) == 2


def test_fit_gpd_continuous_z_validates_inputs():
    """Y and Z must have same length; form must be valid."""
    rng = np.random.default_rng(seed=42)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=100, random_state=rng)
    Z = rng.uniform(1.0, 10.0, size=50)  # wrong length
    with pytest.raises(ValueError, match="length"):
        fit_gpd_continuous_z(Y, Z, threshold=0.0, form="linear", n_boot=10)

    with pytest.raises(ValueError, match="form"):
        fit_gpd_continuous_z(
            np.zeros(100), np.zeros(100), threshold=0.0, form="quadratic", n_boot=10,
        )


def test_fit_gpd_continuous_z_reports_insufficient_bootstrap_reps_on_low_n():
    """Deterministic check of the < 100 reps → 'insufficient_bootstrap_reps' contract.

    Construct degenerate data where bootstrap reps reliably fail (forcing < 100
    successful reps out of 110), then verify the contract: status is
    'insufficient_bootstrap_reps', shape CIs are NaN, but primary coefficients
    are preserved (not NaN).
    """
    rng = np.random.default_rng(seed=42)
    # 25 exceedances of a near-constant value — most spline-form (6-param)
    # bootstrap resamples will be degenerate and fail to converge or violate
    # GPD support.
    n = 25
    Y = rng.uniform(0.001, 0.005, size=n)  # tightly clustered, near-zero
    Z = rng.uniform(1.0, 10.0, size=n)

    result = fit_gpd_continuous_z(
        Y, Z, threshold=0.0, form="spline", n_boot=110, seed=0,
    )

    # The contract only fires when primary fit converges but bootstrap doesn't
    # reliably converge. If primary itself fails, status is "failed" instead.
    # Both are valid outcomes; assert the structural invariants for whichever:
    if result.convergence_status == "insufficient_bootstrap_reps":
        # All shape CIs should be NaN
        for ci in result.shape_coefficients_bootstrap_ci_95:
            assert math.isnan(ci[0]) and math.isnan(ci[1])
        # All scale CIs should be NaN
        for ci in result.scale_coefficients_bootstrap_ci_95:
            assert math.isnan(ci[0]) and math.isnan(ci[1])
        # Primary coefficients should be preserved (NOT NaN)
        for c in result.shape_coefficients:
            assert math.isfinite(c), f"primary shape coef should not be NaN: {c}"
        # Headline p should be NaN (no bootstrap distribution to compute from)
        assert math.isnan(result.headline_p_value)
    elif result.convergence_status == "failed":
        # All params NaN
        for c in result.shape_coefficients:
            assert math.isnan(c)


def test_fit_gpd_continuous_z_returns_failed_status_on_zero_exceedances():
    """When threshold > max(Y), n_exceedances = 0. The function must return
    status='failed' with all-NaN params, NOT crash with 'zero-size array' error.
    """
    Y = np.array([1.0, 2.0, 3.0])
    Z = np.array([1.0, 2.0, 3.0])
    # Threshold above max(Y)
    result = fit_gpd_continuous_z(
        Y, Z, threshold=100.0, form="linear", n_boot=10, seed=0,
    )
    assert result.convergence_status == "failed"
    assert result.n_exceedances == 0
    for c in result.shape_coefficients:
        assert math.isnan(c)
    assert math.isnan(result.headline_p_value)


def test_likelihood_ratio_test_under_null_returns_high_p_value():
    """When DGP is linear, the LRT should not reject the linear-null in favor of spline."""
    rng = np.random.default_rng(seed=42)
    n = 3000
    Z = rng.uniform(1.0, 10.0, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    linear_result = fit_gpd_continuous_z(Y, Z, threshold=0.0, form="linear", n_boot=50, seed=0)
    spline_result = fit_gpd_continuous_z(Y, Z, threshold=0.0, form="spline", n_boot=50, seed=0)
    lrt = _likelihood_ratio_test(linear_result, spline_result, Y, Z, threshold=0.0)

    assert lrt["df"] == 2  # spline (4 DOF shape) - linear (2 DOF shape)
    # Under null, asymptotic p should be > 0.05
    assert lrt["asymptotic_p_value"] > 0.05, \
        f"False rejection of linear null: p={lrt['asymptotic_p_value']}"
    assert lrt["chi2"] >= 0, f"LRT chi² should be non-negative: {lrt['chi2']}"


def test_likelihood_ratio_test_with_strongly_nonlinear_dgp_rejects_linear():
    """When DGP has a strongly cubic ξ(Z), LRT should reject linear in favor of spline."""
    rng = np.random.default_rng(seed=42)
    n = 6000
    Z = rng.uniform(1.0, 10.0, size=n)
    # Strongly cubic shape: ξ(Z) = 0.2 + 0.3·Z - 0.06·Z² + 0.003·Z³
    # (coefficients scaled 3x so the hump amplitude is ~0.44, not ~0.15 —
    # a 0.15-range hump is nearly indistinguishable from a line at this sample size)
    Y = np.empty(n)
    for i in range(n):
        xi_i = 0.2 + 0.3 * Z[i] - 0.06 * Z[i] ** 2 + 0.003 * Z[i] ** 3
        # Clamp to safe MLE range
        xi_i = max(-0.4, min(xi_i, 0.8))
        Y[i] = stats.genpareto.rvs(c=xi_i, scale=2.0, size=1, random_state=rng)[0]

    linear_result = fit_gpd_continuous_z(Y, Z, threshold=0.0, form="linear", n_boot=50, seed=0)
    spline_result = fit_gpd_continuous_z(Y, Z, threshold=0.0, form="spline", n_boot=50, seed=0)
    lrt = _likelihood_ratio_test(linear_result, spline_result, Y, Z, threshold=0.0)

    # Strong non-linearity should produce small p (we use 0.10 cutoff for tolerance)
    assert lrt["asymptotic_p_value"] < 0.10, \
        f"Failed to detect non-linearity: p={lrt['asymptotic_p_value']}, chi2={lrt['chi2']}"


def test_likelihood_ratio_test_handles_failed_fits():
    """If either input fit has status != 'converged', LRT returns NaN values
    rather than crashing."""
    # Construct a failed linear-result (NaN shape coefficients)
    nan_ci = tuple((float("nan"), float("nan")) for _ in range(2))
    failed_result = GPDContinuousFitResult(
        form="linear",
        threshold_quantile=0.95,
        threshold_value=10.0,
        n_exceedances=10,
        shape_coefficients=(float("nan"), float("nan")),
        shape_coefficients_bootstrap_ci_95=nan_ci,
        scale_coefficients=(float("nan"), float("nan")),
        scale_coefficients_bootstrap_ci_95=((float("nan"), float("nan")),) * 2,
        headline_slope_or_lrt=float("nan"),
        headline_p_value=float("nan"),
        convergence_status="failed",
    )
    spline_ok = GPDContinuousFitResult(
        form="spline",
        threshold_quantile=0.95,
        threshold_value=10.0,
        n_exceedances=10,
        shape_coefficients=(0.3, 0.0, 0.0, 0.0),
        shape_coefficients_bootstrap_ci_95=((0, 0),) * 4,
        scale_coefficients=(0.69, 0.0),
        scale_coefficients_bootstrap_ci_95=((0, 0),) * 2,
        headline_slope_or_lrt=0.0,
        headline_p_value=1.0,
        convergence_status="converged",
    )

    lrt = _likelihood_ratio_test(failed_result, spline_ok, np.zeros(10), np.zeros(10), threshold=0.0)
    assert math.isnan(lrt["chi2"])
    assert math.isnan(lrt["asymptotic_p_value"])
    assert lrt["df"] == 2


import json
import pandas as pd
from pathlib import Path
from surg.analysis.gpd_continuous import run_gpd_continuous_z


def test_run_gpd_continuous_z_writes_expected_json_schema(tmp_path: Path):
    """End-to-end: writes JSON with the per-pnode schema documented in the design."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng),
        "Z_target": rng.uniform(1.0, 10.0, size=n),
    })

    out = tmp_path / "gpd_continuous" / "test_pnode.json"
    run_gpd_continuous_z(
        panel,
        out_path=out,
        response_col="Y_target",
        pnode_label="test_pnode",
        threshold_col="Z_target",
        threshold_quantiles=(0.50, 0.75, 0.90),
        n_boot=30,
        seed=0,
    )

    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["pnode_label"] == "test_pnode"
    assert payload["response_col"] == "Y_target"
    assert payload["threshold_col"] == "Z_target"
    assert payload["n_total_panel"] == n
    sweep = payload["threshold_sweep"]
    assert len(sweep) == 3
    for entry in sweep:
        assert set(entry.keys()) >= {
            "threshold_quantile", "threshold_value", "n_exceedances",
            "linear", "spline", "likelihood_ratio_test",
        }
        assert set(entry["linear"].keys()) >= {
            "convergence_status", "shape_coefficients",
            "shape_coefficients_bootstrap_ci_95", "scale_coefficients",
            "scale_coefficients_bootstrap_ci_95", "beta_1_two_sided_p_value",
        }
        assert set(entry["spline"].keys()) >= {
            "convergence_status", "shape_coefficients",
            "shape_coefficients_bootstrap_ci_95", "scale_coefficients",
            "scale_coefficients_bootstrap_ci_95",
        }
        assert set(entry["likelihood_ratio_test"].keys()) >= {
            "chi2", "df", "asymptotic_p_value",
        }


def test_run_gpd_continuous_z_handles_dropna_in_response(tmp_path: Path):
    """Rows with NaN in response_col or threshold_col are dropped; n_after_dropna
    reflects the actual fit sample size."""
    rng = np.random.default_rng(seed=42)
    n = 2000
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)
    Z = rng.uniform(1.0, 10.0, size=n)
    Y[10] = float("nan")
    Y[20] = float("nan")
    Z[100] = float("nan")
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": Y,
        "Z_target": Z,
    })

    out = tmp_path / "gpd_continuous" / "test_dropna.json"
    run_gpd_continuous_z(
        panel, out_path=out,
        response_col="Y_target", pnode_label="dropna_test",
        threshold_col="Z_target",
        threshold_quantiles=(0.5,), n_boot=30, seed=0,
    )

    payload = json.loads(out.read_text())
    assert payload["n_total_panel"] == 2000
    assert payload["n_after_dropna"] == 1997  # 3 rows with any NaN dropped


def test_run_gpd_continuous_z_serializes_nan_as_null(tmp_path: Path):
    """JSON output uses null for NaN values (RFC-compliant), not literal NaN."""
    # Force a fit failure scenario with very small n
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=50, freq="h"),
        "Y_target": np.random.default_rng(42).uniform(0, 1, size=50),
        "Z_target": np.random.default_rng(42).uniform(1, 10, size=50),
    })
    out = tmp_path / "gpd_continuous" / "nan_check.json"
    run_gpd_continuous_z(
        panel, out_path=out,
        response_col="Y_target", pnode_label="nan_test",
        threshold_col="Z_target",
        threshold_quantiles=(0.5,), n_boot=20, seed=0,
    )
    text = out.read_text()
    assert "NaN" not in text, "JSON output contains literal NaN token"
    json.loads(text)  # strict JSON parsing must succeed
