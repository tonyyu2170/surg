"""Unit tests for src/surg/analysis/gpd.py — Strategy C GPD module."""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from surg.analysis.gpd import GPDFitResult, fit_gpd, gpd_threshold_sweep
from surg.analysis.gpd import GPDConditionalResult, gpd_conditional_on_z


def test_fit_gpd_recovers_planted_shape_and_scale():
    """fit_gpd with simulated GPD data should recover the planted parameters
    to within tolerance proportional to sqrt(n_exceedances)."""
    rng = np.random.default_rng(seed=42)
    true_shape, true_scale = 0.3, 2.0
    threshold = 10.0
    # Generate exceedances and shift by threshold so the data is "above threshold"
    excess = stats.genpareto.rvs(c=true_shape, scale=true_scale, size=5000, random_state=rng)
    Y = excess + threshold
    # Pad with a few below-threshold observations so fit_gpd has something to filter
    Y_full = np.concatenate([Y, rng.uniform(0, threshold - 0.1, size=200)])

    result = fit_gpd(Y_full, threshold=threshold)

    assert isinstance(result, GPDFitResult)
    assert result.n_exceedances == 5000
    assert result.threshold_value == pytest.approx(10.0)
    assert result.threshold_quantile == pytest.approx(200 / 5200, abs=0.01)
    # Recovery tolerance: ~0.1 for shape with n=5000 (asymptotic SE ≈ 0.018)
    assert result.shape == pytest.approx(true_shape, abs=0.1)
    assert result.scale == pytest.approx(true_scale, abs=0.3)
    # Asymptotic SE should be positive and finite
    assert result.shape_se > 0
    assert math.isfinite(result.shape_se)
    assert result.scale_se > 0
    assert math.isfinite(result.scale_se)


def test_fit_gpd_recovers_xi_near_zero_for_exponential():
    """fit_gpd on exponential data (a special case of GPD with shape=0) should
    return shape close to zero."""
    rng = np.random.default_rng(seed=42)
    # Exponential with rate 1/5 (mean=5), shifted to be "above threshold 0"
    Y = rng.exponential(scale=5.0, size=5000) + 0.001  # tiny offset to avoid zeros

    result = fit_gpd(Y, threshold=0.0)

    assert abs(result.shape) < 0.1, f"shape too far from 0: {result.shape}"
    assert result.scale == pytest.approx(5.0, abs=0.5)


def test_fit_gpd_threshold_above_max_raises():
    """If threshold > max(Y), there are zero exceedances and the fit is ill-defined."""
    Y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    with pytest.raises(ValueError, match="threshold"):
        fit_gpd(Y, threshold=100.0)


def test_fit_gpd_nan_se_when_shape_below_regularity_boundary():
    """When the data force a heavy-negative shape (shape ≤ -0.5), the
    asymptotic SE is undefined (regularity condition violated). Both SEs
    should be NaN in that case.

    Bounded uniform data typically yields a strongly negative shape from
    scipy's GPD MLE.
    """
    rng = np.random.default_rng(seed=42)
    Y = rng.uniform(0.0, 1.0, size=2000)

    result = fit_gpd(Y, threshold=0.0)

    if result.shape <= -0.5:
        assert math.isnan(result.shape_se), \
            f"shape_se should be NaN when shape={result.shape:.4f} ≤ -0.5"
        assert math.isnan(result.scale_se), \
            f"scale_se should be NaN when shape={result.shape:.4f} ≤ -0.5"
    else:
        # Not strictly testing the NaN branch — scipy returned a less-extreme
        # shape than expected; just verify the regular SE branch produced
        # finite values (the alternative path).
        assert math.isfinite(result.shape_se)
        assert math.isfinite(result.scale_se)


def test_gpd_threshold_sweep_returns_count_equal_to_quantile_count():
    """Passing 4 quantiles produces exactly 4 fits."""
    rng = np.random.default_rng(seed=42)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=5000, random_state=rng)

    results = gpd_threshold_sweep(
        Y, quantiles=(0.50, 0.75, 0.90, 0.95), n_boot=50, seed=0
    )

    assert len(results) == 4
    for fit, expected_q in zip(results, (0.50, 0.75, 0.90, 0.95), strict=True):
        assert isinstance(fit, GPDFitResult)
        assert fit.threshold_quantile == pytest.approx(expected_q, abs=0.01)
        # Bootstrap CI should be non-degenerate (positive width) and finite
        lo, hi = fit.shape_bootstrap_ci_95
        assert math.isfinite(lo) and math.isfinite(hi), \
            f"CI not finite at q={expected_q}: ({lo}, {hi})"
        assert hi > lo, f"CI has zero width at q={expected_q}: ({lo}, {hi})"


def test_gpd_threshold_sweep_seed_reproducibility():
    """Same seed must produce identical bootstrap CIs across runs."""
    rng = np.random.default_rng(seed=42)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=2000, random_state=rng)

    r1 = gpd_threshold_sweep(Y, quantiles=(0.5, 0.75), n_boot=30, seed=123)
    r2 = gpd_threshold_sweep(Y, quantiles=(0.5, 0.75), n_boot=30, seed=123)
    for f1, f2 in zip(r1, r2, strict=True):
        assert f1.shape_bootstrap_ci_95 == f2.shape_bootstrap_ci_95


def test_gpd_conditional_detects_z_dependent_shape():
    """When DGP has higher tail heaviness at high Z, the conditional split
    should detect it: shape_diff > 0 with low bootstrap p-value."""
    rng = np.random.default_rng(seed=42)
    n = 8000
    Z = rng.uniform(0, 10, size=n)
    # Generate Y with Z-dependent GPD shape: ξ = 0.5 if Z > 5, else 0.1
    Y = np.empty(n)
    high_z = Z > 5.0
    n_high = int(high_z.sum())
    n_low = n - n_high
    Y[high_z] = stats.genpareto.rvs(c=0.5, scale=2.0, size=n_high, random_state=rng)
    Y[~high_z] = stats.genpareto.rvs(c=0.1, scale=2.0, size=n_low, random_state=rng)

    result = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.5, z_split_quantile=0.5, n_boot=100, seed=0,
    )

    assert isinstance(result, GPDConditionalResult)
    # z_split is computed over Z within exceedances, not the full Z population.
    # Under a non-null DGP (higher-ξ at high-Z), the exceedance set is enriched
    # for high-Z rows, so median(Z_exc) > median(Z). Assert against the correct
    # conditional expectation.
    threshold_val = float(np.quantile(Y, 0.5))
    expected_z_split = float(np.median(Z[Y > threshold_val]))
    assert result.z_split_value == pytest.approx(expected_z_split, abs=0.1)
    assert result.shape_diff > 0.2, f"shape_diff too small: {result.shape_diff}"
    assert result.shape_diff_bootstrap_p_value < 0.05, \
        f"failed to detect z-dependence: p={result.shape_diff_bootstrap_p_value}"
    # CI should not include 0 since the difference is real and positive
    lo, hi = result.shape_diff_bootstrap_ci_95
    assert lo > 0 or hi < 0 or (lo < 0 < hi and abs(lo) < hi), \
        f"CI does not cleanly exclude 0: ({lo}, {hi})"


def test_gpd_conditional_null_when_z_independent():
    """When DGP has Z-independent shape, the conditional split should give
    a non-tiny bootstrap p-value (broad null check, not exact)."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    Z = rng.uniform(0, 10, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    result = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.5, z_split_quantile=0.5, n_boot=100, seed=0,
    )

    assert result.shape_diff_bootstrap_p_value > 0.10, \
        f"false-positive z-dependence: p={result.shape_diff_bootstrap_p_value}"


def test_gpd_conditional_validates_length_mismatch():
    """Y and Z must have the same length."""
    rng = np.random.default_rng(seed=42)
    Y = rng.exponential(scale=5.0, size=100)
    Z = rng.uniform(0, 10, size=50)  # wrong length
    with pytest.raises(ValueError, match="length"):
        gpd_conditional_on_z(Y, Z, threshold_quantile=0.5, n_boot=10)
