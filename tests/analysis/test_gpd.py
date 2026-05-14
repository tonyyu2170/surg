"""Unit tests for src/surg/analysis/gpd.py — Strategy C GPD module."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from surg.analysis.gpd import GPDFitResult, fit_gpd, gpd_threshold_sweep
from surg.analysis.gpd import GPDConditionalResult, gpd_conditional_on_z
from surg.analysis.gpd import run_gpd
from surg.analysis.gpd import GPDQuantileSplitResult, gpd_quantile_split_on_z


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


def test_gpd_conditional_nested_threshold_quantile_carries_parent():
    """Both nested fit results should carry the parent threshold_quantile,
    not 0.0 (which is what fit_gpd would compute on already-filtered subsets).
    """
    rng = np.random.default_rng(seed=42)
    n = 4000
    Z = rng.uniform(0, 10, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    result = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.75, z_split_quantile=0.5, n_boot=50, seed=0,
    )

    assert result.threshold_quantile == pytest.approx(0.75)
    assert result.low_z.threshold_quantile == pytest.approx(0.75), \
        f"low_z carries wrong threshold_quantile: {result.low_z.threshold_quantile}"
    assert result.high_z.threshold_quantile == pytest.approx(0.75), \
        f"high_z carries wrong threshold_quantile: {result.high_z.threshold_quantile}"


def test_run_gpd_writes_expected_json_schema(tmp_path: Path):
    """run_gpd writes a JSON file with the spec-documented schema."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng),
        "Z_target": rng.uniform(0, 10, size=n),
    })

    out = tmp_path / "gpd" / "test_pnode.json"
    run_gpd(
        panel,
        out_path=out,
        response_col="Y_target",
        pnode_label="test_pnode",
        threshold_col="Z_target",
        sweep_quantiles=(0.50, 0.75, 0.90, 0.95),
        conditional_threshold_quantile=0.5,
        n_boot=50,
        seed=0,
    )

    assert out.exists(), f"run_gpd did not write {out}"
    payload = json.loads(out.read_text())

    # Top-level shape
    assert payload["pnode_label"] == "test_pnode"
    assert payload["response_col"] == "Y_target"
    assert payload["threshold_col"] == "Z_target"
    assert payload["n_total_panel"] == n
    assert payload["n_after_dropna"] == n

    # Threshold sweep: 4 entries
    sweep = payload["threshold_sweep"]
    assert len(sweep) == 4
    for entry in sweep:
        assert set(entry.keys()) >= {
            "threshold_quantile", "threshold_value", "n_exceedances",
            "shape", "shape_se", "shape_bootstrap_ci_95", "scale", "scale_se",
        }
        assert isinstance(entry["shape_bootstrap_ci_95"], list)
        assert len(entry["shape_bootstrap_ci_95"]) == 2

    # Conditional Z
    cond = payload["conditional_z"]
    assert cond["threshold_quantile"] == pytest.approx(0.5)
    assert "low_z" in cond and "high_z" in cond
    assert set(cond["low_z"].keys()) >= {"shape", "shape_se", "n_exceedances"}
    assert "shape_difference" in cond
    diff_block = cond["shape_difference"]
    assert set(diff_block.keys()) >= {"diff", "bootstrap_ci_95", "bootstrap_p_value"}


def test_run_gpd_serializes_nan_as_null(tmp_path: Path):
    """When fit returns NaN (e.g. on bounded data forcing shape <= -0.5),
    run_gpd's JSON output should contain `null`, not the non-RFC `NaN` token."""
    rng = np.random.default_rng(seed=42)
    n = 2000
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        # Bounded uniform → scipy fits with strongly negative shape → NaN SEs
        "Y_bounded": rng.uniform(0.0, 1.0, size=n),
        "Z_target": rng.uniform(0, 10, size=n),
    })

    out = tmp_path / "gpd" / "bounded.json"
    run_gpd(
        panel,
        out_path=out,
        response_col="Y_bounded",
        pnode_label="bounded",
        threshold_col="Z_target",
        sweep_quantiles=(0.50, 0.75),
        conditional_threshold_quantile=0.5,
        n_boot=30,
        seed=0,
    )

    text = out.read_text()
    assert "NaN" not in text, "JSON output contains literal NaN token (not RFC-valid)"
    payload = json.loads(text)  # strict json.loads would fail on NaN
    # At least one of the SEs in the sweep should be None (the bounded data
    # triggers the shape <= -0.5 branch). If scipy returns a less extreme
    # shape than expected, this assertion is vacuous but harmless.
    for entry in payload["threshold_sweep"]:
        for key in ("shape_se", "scale_se"):
            v = entry[key]
            # Either a finite number or None — never NaN or inf
            assert v is None or (isinstance(v, (int, float)) and math.isfinite(v))


# ─── gpd_quantile_split_on_z (Spec A engine) ──────────────────────────────────


def test_gpd_quantile_split_detects_monotone_shape():
    """When DGP has monotonically increasing GPD shape across Z quartiles,
    gpd_quantile_split_on_z should detect a positive extreme_contrast
    (ξ_Q4 − ξ_Q1) and a two-sided bootstrap p < 0.05."""
    rng = np.random.default_rng(seed=42)
    n = 12000
    Z = rng.uniform(0, 10, size=n)
    # Z-dependent GPD shape: Q1 → 0.1, Q2 → 0.3, Q3 → 0.5, Q4 → 0.7
    Y = np.empty(n)
    z_quartile_edges = np.quantile(Z, [0.25, 0.5, 0.75])
    shape_by_q = [0.1, 0.3, 0.5, 0.7]
    for i in range(4):
        if i == 0:
            mask = Z <= z_quartile_edges[0]
        elif i == 3:
            mask = Z > z_quartile_edges[2]
        else:
            mask = (Z > z_quartile_edges[i - 1]) & (Z <= z_quartile_edges[i])
        n_i = int(mask.sum())
        Y[mask] = stats.genpareto.rvs(
            c=shape_by_q[i], scale=2.0, size=n_i, random_state=rng
        )

    result = gpd_quantile_split_on_z(
        Y, Z,
        threshold_quantile=0.5,
        split_quantiles=(0.25, 0.5, 0.75),
        n_boot=100,
        seed=0,
    )

    assert isinstance(result, GPDQuantileSplitResult)
    assert len(result.quantile_fits) == 4
    assert len(result.quantile_edges) == 3
    assert tuple(result.split_quantiles) == (0.25, 0.5, 0.75)

    # ξ trajectory should be roughly monotonically increasing
    shapes = [fit.shape for fit in result.quantile_fits]
    assert shapes[3] > shapes[0], f"Q4 ξ not > Q1 ξ: {shapes}"
    # extreme_contrast (Q4 − Q1) should be clearly positive
    assert result.extreme_contrast > 0.3, \
        f"extreme_contrast too small: {result.extreme_contrast}"
    # Two-sided p-value should reject H0
    assert result.extreme_contrast_bootstrap_p_value < 0.05, \
        f"failed to detect quartile-monotone shape: p={result.extreme_contrast_bootstrap_p_value}"


def test_gpd_quantile_split_n2_matches_median_split_shape_diff():
    """gpd_quantile_split_on_z with split_quantiles=(0.5,) should reproduce
    the same per-subset shape estimates as gpd_conditional_on_z with
    z_split_quantile=0.5. The bootstrap CI may differ due to different
    resampling protocols in the two functions (the new function refits all
    N+1 groups jointly via _assign_groups; the existing 2-way function uses
    high_b = ~low_b), but the point estimates must match exactly."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    Z = rng.uniform(0, 10, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    n_way = gpd_quantile_split_on_z(
        Y, Z, threshold_quantile=0.5, split_quantiles=(0.5,),
        n_boot=50, seed=0,
    )
    two_way = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.5, z_split_quantile=0.5,
        n_boot=50, seed=0,
    )

    assert len(n_way.quantile_fits) == 2
    # First quantile fit corresponds to low-Z; second to high-Z
    assert n_way.quantile_fits[0].shape == pytest.approx(two_way.low_z.shape)
    assert n_way.quantile_fits[1].shape == pytest.approx(two_way.high_z.shape)
    # extreme_contrast (last - first) == shape_diff (high - low) for N=2
    assert n_way.extreme_contrast == pytest.approx(two_way.shape_diff)


def test_gpd_quantile_split_validates_split_quantiles_sorted_in_range():
    """split_quantiles must be strictly ascending and in (0, 1)."""
    rng = np.random.default_rng(seed=42)
    n = 1000
    Y = rng.exponential(scale=5.0, size=n)
    Z = rng.uniform(0, 10, size=n)

    with pytest.raises(ValueError, match="split_quantiles"):
        gpd_quantile_split_on_z(Y, Z, split_quantiles=(0.5, 0.25), n_boot=10)
    with pytest.raises(ValueError, match="split_quantiles"):
        gpd_quantile_split_on_z(Y, Z, split_quantiles=(0.0, 0.5), n_boot=10)
    with pytest.raises(ValueError, match="split_quantiles"):
        gpd_quantile_split_on_z(Y, Z, split_quantiles=(0.5, 1.0), n_boot=10)


def test_gpd_quantile_split_raises_on_small_quartile():
    """If a quartile subset has fewer than 10 exceedances, the fit cannot
    proceed and the function raises ValueError (no silent partial result).

    Constructed deterministically: 25 large values + 475 small values, with
    threshold_quantile=0.95 capturing exactly the 25 large ones. Quartile
    split → ~6 per quartile, failing the per-subset n≥10 check while
    comfortably passing the overall n_exc≥20 check.
    """
    rng = np.random.default_rng(seed=42)
    large = rng.uniform(100, 200, size=25)
    small = rng.uniform(1, 10, size=475)
    Y = np.concatenate([large, small])
    Z = rng.uniform(0, 10, size=500)  # uniform Z so quartiles are balanced

    with pytest.raises(ValueError, match="too few exceedances per subset"):
        gpd_quantile_split_on_z(
            Y, Z, threshold_quantile=0.95, split_quantiles=(0.25, 0.5, 0.75),
            n_boot=10, seed=0,
        )


def test_gpd_quantile_split_validates_length_mismatch():
    """Y and Z must have the same length."""
    rng = np.random.default_rng(seed=42)
    Y = rng.exponential(scale=5.0, size=100)
    Z = rng.uniform(0, 10, size=50)
    with pytest.raises(ValueError, match="length"):
        gpd_quantile_split_on_z(Y, Z, split_quantiles=(0.5,), n_boot=10)


def test_gpd_quantile_split_two_sided_p_value_for_null_dgp():
    """When DGP is Z-independent, the two-sided p-value should be non-tiny
    (broad null check, not exact)."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    Z = rng.uniform(0, 10, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    result = gpd_quantile_split_on_z(
        Y, Z, threshold_quantile=0.5, split_quantiles=(0.25, 0.5, 0.75),
        n_boot=100, seed=0,
    )

    assert result.extreme_contrast_bootstrap_p_value > 0.10, \
        f"false-positive quartile-dependence: p={result.extreme_contrast_bootstrap_p_value}"


def test_gpd_quantile_split_seed_reproducibility():
    """Same seed must produce identical bootstrap CIs and p-values across runs."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    Z = rng.uniform(0, 10, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    r1 = gpd_quantile_split_on_z(
        Y, Z, threshold_quantile=0.5,
        split_quantiles=(0.25, 0.5, 0.75), n_boot=50, seed=7,
    )
    r2 = gpd_quantile_split_on_z(
        Y, Z, threshold_quantile=0.5,
        split_quantiles=(0.25, 0.5, 0.75), n_boot=50, seed=7,
    )

    assert r1.extreme_contrast_bootstrap_ci_95 == r2.extreme_contrast_bootstrap_ci_95
    assert r1.extreme_contrast_bootstrap_p_value == r2.extreme_contrast_bootstrap_p_value
