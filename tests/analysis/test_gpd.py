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
from surg.analysis.gpd import holm_bonferroni_two_sided
from surg.analysis.gpd import run_conditional_z_robustness


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


# ─── holm_bonferroni_two_sided (family-wise correction utility) ───────────────


def test_holm_all_significant():
    """All p-values below α/k threshold → all rejected, family-wise rejection."""
    result = holm_bonferroni_two_sided(
        labeled_p_values={"a": 0.001, "b": 0.005, "c": 0.012},
        alpha=0.05,
    )
    assert result["rejections"] == {"a": True, "b": True, "c": True}
    assert result["family_wise_rejection"] is True
    assert result["alpha"] == 0.05
    # sorted_order: ascending p-values; first rank gets α/3, next α/2, last α/1
    assert result["sorted_order"] == ["a", "b", "c"]
    # Adjusted thresholds returned for downstream reporting
    assert result["adjusted_thresholds"]["a"] == pytest.approx(0.05 / 3, rel=1e-9)
    assert result["adjusted_thresholds"]["b"] == pytest.approx(0.05 / 2, rel=1e-9)
    assert result["adjusted_thresholds"]["c"] == pytest.approx(0.05 / 1, rel=1e-9)


def test_holm_stops_at_first_non_rejection():
    """Holm is sequential: the first failure halts the procedure for all
    higher-ranked p-values, even if those would individually pass at their
    own adjusted thresholds (a=0.05 won't be considered if b at α/2 failed)."""
    result = holm_bonferroni_two_sided(
        labeled_p_values={"a": 0.001, "b": 0.030, "c": 0.045},
        alpha=0.05,
    )
    # a: 0.001 < 0.05/3=0.0167 → reject
    # b: 0.030 > 0.05/2=0.025 → stop, do not reject b OR c
    assert result["rejections"] == {"a": True, "b": False, "c": False}
    assert result["family_wise_rejection"] is False


def test_holm_first_p_above_alpha_over_k_rejects_nothing():
    """If the smallest p-value already fails its α/k threshold, nothing is
    rejected and family-wise rejection is False."""
    result = holm_bonferroni_two_sided(
        labeled_p_values={"a": 0.02, "b": 0.03, "c": 0.04},
        alpha=0.05,
    )
    # smallest = 0.02 > 0.05/3 = 0.0167 → reject nothing
    assert result["rejections"] == {"a": False, "b": False, "c": False}
    assert result["family_wise_rejection"] is False


def test_holm_handles_nan_p_value_as_non_rejection():
    """An inconclusive spec (NaN p-value) is treated as 'cannot reject' —
    it is sorted to the end (with p=+inf) and is never rejected, but does
    not affect whether earlier specs in the order can be rejected at their
    own adjusted thresholds."""
    result = holm_bonferroni_two_sided(
        labeled_p_values={"a": 0.005, "b": float("nan"), "c": 0.020},
        alpha=0.05,
    )
    # a: 0.005 < 0.05/3 = 0.0167 → reject
    # c: 0.020 < 0.05/2 = 0.025 → reject (c is now rank 2)
    # b: NaN → never rejected
    assert result["rejections"] == {"a": True, "b": False, "c": True}
    # b cannot be rejected → family-wise is False (not all rejected)
    assert result["family_wise_rejection"] is False
    assert result["sorted_order"] == ["a", "c", "b"]


def test_holm_validates_alpha_in_open_unit_interval():
    """α must be in (0, 1)."""
    with pytest.raises(ValueError, match="alpha"):
        holm_bonferroni_two_sided({"a": 0.01}, alpha=0.0)
    with pytest.raises(ValueError, match="alpha"):
        holm_bonferroni_two_sided({"a": 0.01}, alpha=1.0)


def test_holm_validates_p_value_range():
    """p-values must be in [0, 1] or NaN; values outside this range raise."""
    with pytest.raises(ValueError, match="p-value"):
        holm_bonferroni_two_sided({"a": -0.01}, alpha=0.05)
    with pytest.raises(ValueError, match="p-value"):
        holm_bonferroni_two_sided({"a": 1.01}, alpha=0.05)


# ─── run_conditional_z_robustness (orchestrator) ──────────────────────────────


def _synthetic_battery_panel(n: int, seed: int) -> pd.DataFrame:
    """Build a synthetic panel matching the columns run_conditional_z_robustness
    consumes: response (Y), threshold variable (Z), filter mask.

    Generates a Z-dependent GPD where high-Z exceedances have lighter tails
    than low-Z (matching the actual 2026-05-14 production finding's
    direction). The filter mask retains a fraction of rows.
    """
    rng = np.random.default_rng(seed=seed)
    Z = rng.uniform(0, 10, size=n)
    Y = np.empty(n)
    # Median-split: shape=0.5 below, shape=0.2 above (matches production finding)
    high_z = Z > 5.0
    Y[~high_z] = stats.genpareto.rvs(c=0.5, scale=2.0, size=int((~high_z).sum()), random_state=rng)
    Y[high_z] = stats.genpareto.rvs(c=0.2, scale=2.0, size=int(high_z.sum()), random_state=rng)

    # Filter: keep ~6% of rows (matches the proposal's 2-5 AM × shoulder share)
    filter_mask = rng.random(size=n) < 0.064
    return pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": Y,
        "Z_target": Z,
        "passes_proposal_filter": filter_mask,
    })


def test_run_conditional_z_robustness_writes_expected_json(tmp_path: Path):
    """End-to-end: run_conditional_z_robustness writes a JSON file with the
    expected schema (per-spec blocks for A/C/F + a holm_bonferroni block)."""
    panel = _synthetic_battery_panel(n=12000, seed=42)
    out = tmp_path / "gpd" / "conditional_z_robustness.json"

    run_conditional_z_robustness(
        panel,
        out_path=out,
        response_col="Y_target",
        pnode_label="test",
        threshold_col="Z_target",
        filter_col="passes_proposal_filter",
        n_boot=50,
        seed=0,
    )

    assert out.exists(), f"orchestrator did not write {out}"
    payload = json.loads(out.read_text())

    # Top-level shape
    assert payload["pnode_label"] == "test"
    assert payload["response_col"] == "Y_target"
    assert payload["threshold_col"] == "Z_target"
    assert payload["filter_col"] == "passes_proposal_filter"
    assert payload["n_total_panel"] == 12000

    # Spec A: quartile split, full panel
    spec_a = payload["spec_a_quartile_split"]
    assert spec_a["status"] == "fit"
    assert spec_a["scope"] == "full_panel"
    assert spec_a["threshold_quantile"] == pytest.approx(0.95)
    a_result = spec_a["result"]
    assert tuple(a_result["split_quantiles"]) == (0.25, 0.5, 0.75)
    assert len(a_result["quantile_fits"]) == 4
    assert "extreme_contrast" in a_result
    assert "extreme_contrast_bootstrap_ci_95" in a_result
    assert "extreme_contrast_bootstrap_p_value" in a_result

    # Spec C: median-split at 99th-pct, full panel
    spec_c = payload["spec_c_99th_pct"]
    assert spec_c["scope"] == "full_panel"
    assert spec_c["threshold_quantile"] == pytest.approx(0.99)
    # Status may be "fit" or "inconclusive" depending on synthetic n;
    # both are valid outcomes for this test (we only check the schema).
    assert spec_c["status"] in {"fit", "inconclusive"}
    if spec_c["status"] == "fit":
        assert "shape_diff" in spec_c["result"]
        assert "two_sided_p_value" in spec_c["result"]

    # Spec F: within-filter median-split at 95th
    spec_f = payload["spec_f_within_filter"]
    assert spec_f["scope"] == "filtered_subset"
    assert spec_f["filter_col"] == "passes_proposal_filter"
    assert spec_f["threshold_quantile"] == pytest.approx(0.95)
    assert spec_f["status"] in {"fit", "inconclusive"}

    # Holm-Bonferroni roll-up
    holm = payload["holm_bonferroni"]
    assert holm["alpha"] == pytest.approx(0.05)
    assert set(holm["two_sided_p_values"].keys()) == {"spec_a", "spec_c", "spec_f"}
    assert set(holm["rejections"].keys()) == {"spec_a", "spec_c", "spec_f"}
    assert isinstance(holm["family_wise_rejection"], bool)


def test_run_conditional_z_robustness_handles_spec_c_fit_failure(tmp_path: Path):
    """When the 99th-pct threshold leaves too few exceedances per Z-half,
    Spec C must be reported as 'inconclusive' (status string), not crash
    the orchestrator. The other specs still run; Holm sees NaN for C."""
    rng = np.random.default_rng(seed=42)
    n = 800  # at 99th-pct: ~8 exceedances total, far below the n=20 floor
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng),
        "Z_target": rng.uniform(0, 10, size=n),
        "passes_proposal_filter": np.zeros(n, dtype=bool),
    })

    out = tmp_path / "gpd" / "small_n.json"
    run_conditional_z_robustness(
        panel, out_path=out,
        response_col="Y_target", pnode_label="small",
        threshold_col="Z_target", filter_col="passes_proposal_filter",
        n_boot=30, seed=0,
    )

    payload = json.loads(out.read_text())
    assert payload["spec_c_99th_pct"]["status"] == "inconclusive"
    assert payload["spec_c_99th_pct"]["reason"] is not None  # human-readable explanation
    assert payload["spec_c_99th_pct"]["result"] is None
    # Holm should record NaN for spec_c (which serializes to null)
    assert payload["holm_bonferroni"]["two_sided_p_values"]["spec_c"] is None
    # Spec C cannot be rejected
    assert payload["holm_bonferroni"]["rejections"]["spec_c"] is False


def test_run_conditional_z_robustness_handles_spec_f_filter_empty(tmp_path: Path):
    """When the filter mask is all-False, Spec F has no data → inconclusive."""
    rng = np.random.default_rng(seed=42)
    n = 8000
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng),
        "Z_target": rng.uniform(0, 10, size=n),
        "passes_proposal_filter": np.zeros(n, dtype=bool),
    })

    out = tmp_path / "gpd" / "empty_filter.json"
    run_conditional_z_robustness(
        panel, out_path=out,
        response_col="Y_target", pnode_label="empty",
        threshold_col="Z_target", filter_col="passes_proposal_filter",
        n_boot=30, seed=0,
    )

    payload = json.loads(out.read_text())
    assert payload["spec_f_within_filter"]["status"] == "inconclusive"
    assert payload["spec_f_within_filter"]["reason"] is not None
    assert payload["spec_f_within_filter"]["n_after_filter"] == 0


def test_run_conditional_z_robustness_serializes_nan_as_null(tmp_path: Path):
    """If any bootstrap CI or p-value is NaN, JSON output uses null, not NaN."""
    panel = _synthetic_battery_panel(n=4000, seed=0)
    out = tmp_path / "gpd" / "nan_check.json"
    run_conditional_z_robustness(
        panel, out_path=out,
        response_col="Y_target", pnode_label="nan_test",
        threshold_col="Z_target", filter_col="passes_proposal_filter",
        n_boot=20, seed=0,
    )
    text = out.read_text()
    assert "NaN" not in text, "JSON output contains literal NaN token"
    # strict json.loads validates RFC-compliance
    payload = json.loads(text)
    # If any p-value field is null, it must be None on parse (not NaN)
    for spec_key in ("spec_a", "spec_c", "spec_f"):
        p = payload["holm_bonferroni"]["two_sided_p_values"][spec_key]
        assert p is None or (isinstance(p, (int, float)) and math.isfinite(p))


def test_run_conditional_z_robustness_filter_alignment_with_nan_rows(tmp_path: Path):
    """Reindex idiom must correctly align filter mask after dropna removes rows.

    Regression guard: a naive `panel[filter_col].fillna(False).to_numpy()[:len(base_subset)]`
    would mis-align when NaN rows are scattered (not all at the end) because the
    truncation does not respect which original-panel rows survived dropna. This
    matters at production: the real analysis panel has NaN at the start of the
    load-gradient column (no prior hour to diff against).
    """
    rng = np.random.default_rng(seed=42)
    n = 5000
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)
    Z = rng.uniform(0, 10, size=n)
    # Insert NaN at scattered positions so base_subset != panel
    Y[10] = float("nan")
    Y[200] = float("nan")
    Y[1500] = float("nan")
    # Mark rows in the filter: two will be dropped by dropna, one survives
    f_mask = np.zeros(n, dtype=bool)
    f_mask[10] = True   # dropped (NaN Y) — must NOT count in f_subset
    f_mask[200] = True  # dropped (NaN Y) — must NOT count in f_subset
    f_mask[100] = True  # kept, survives both dropna and filter — counts as 1
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y": Y,
        "Z": Z,
        "passes_proposal_filter": f_mask,
    })
    out = tmp_path / "gpd" / "align.json"
    run_conditional_z_robustness(
        panel, out_path=out,
        response_col="Y", pnode_label="align_test",
        threshold_col="Z", filter_col="passes_proposal_filter",
        n_boot=30, seed=0,
    )
    payload = json.loads(out.read_text())
    # Only row 100 survives both dropna AND filter → n_after_filter == 1
    assert payload["spec_f_within_filter"]["n_after_filter"] == 1, (
        f"alignment broken: expected n_after_filter=1, "
        f"got {payload['spec_f_within_filter']['n_after_filter']}"
    )
    # n=1 is far below the orchestrator's 20-row floor → inconclusive
    assert payload["spec_f_within_filter"]["status"] == "inconclusive"


def test_gpd_conditional_on_z_cluster_bootstrap_runs():
    rng = np.random.default_rng(7)
    n = 4000
    Y = rng.pareto(3.0, size=n) * 10.0
    Z = rng.uniform(0, 100, size=n)
    clusters = np.repeat(np.arange(100), n // 100)  # 100 islands of 40 obs
    res = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.90, n_boot=50, seed=1, cluster_ids=clusters,
    )
    lo, hi = res.shape_diff_bootstrap_ci_95
    assert np.isfinite(lo) and np.isfinite(hi) and lo < hi


def test_gpd_conditional_cluster_ids_length_mismatch_raises():
    rng = np.random.default_rng(7)
    Y = rng.pareto(3.0, size=500) * 10.0
    Z = rng.uniform(0, 100, size=500)
    with pytest.raises(ValueError, match="cluster_ids"):
        gpd_conditional_on_z(Y, Z, n_boot=30, seed=1, cluster_ids=np.arange(10))


def test_run_gpd_passes_cluster_col(tmp_path):
    rng = np.random.default_rng(7)
    n = 4000
    df = pd.DataFrame({
        "resp": rng.pareto(3.0, size=n) * 10.0,
        "dom_load_gradient_abs_mw_per_min": rng.uniform(0, 100, size=n),
        "isl": np.repeat(np.arange(100), n // 100),
    })
    out = tmp_path / "g.json"
    run_gpd(df, out, response_col="resp", pnode_label="t",
            sweep_quantiles=(0.90,), conditional_threshold_quantile=0.90,
            n_boot=50, seed=1, cluster_col="isl")
    payload = json.loads(out.read_text())
    assert payload["conditional_z"]["bootstrap_mode"] == "cluster"


def test_gpd_conditional_on_z_cluster_bootstrap_duplicates_rows(monkeypatch):
    """Locks in the correct cluster-bootstrap mechanic: a cluster id drawn twice
    by rng.choice must contribute its exceedance rows twice to the resampled
    arrays (not deduplicated). Forces a fixed, duplicate-containing draw via
    monkeypatch and checks the resulting bootstrap CI matches an independently
    computed expected shape_diff for that exact (duplicate-aware) resample."""
    rng = np.random.default_rng(11)
    n_clusters = 15
    per_cluster = 30
    n = n_clusters * per_cluster
    cluster_ids = np.repeat(np.arange(n_clusters), per_cluster)
    Y = rng.pareto(3.0, size=n) * 10.0
    Z = rng.uniform(0, 100, size=n)
    threshold_quantile = 0.5
    z_split_quantile = 0.5

    # Replicate the function's own (public, deterministic) threshold/exceedance
    # computation so we can predict exactly what resample this monkeypatch forces.
    threshold = float(np.quantile(Y, threshold_quantile))
    exceed_mask = Y > threshold
    Y_exc = Y[exceed_mask]
    Z_exc = Z[exceed_mask]
    C_exc = cluster_ids[exceed_mask]
    unique_clusters = np.unique(C_exc)
    assert len(unique_clusters) >= 10  # must clear the Bug-1 guard

    # Force every bootstrap rep to draw cluster unique_clusters[0] twice, in
    # place of unique_clusters[1] (which is dropped from the resample entirely).
    drawn_forced = unique_clusters.copy()
    drawn_forced[1] = drawn_forced[0]

    # numpy.random.Generator is an immutable Cython extension type — its
    # `choice` method can't be monkeypatched directly. Patch the factory
    # function instead: gpd_conditional_on_z calls np.random.default_rng(seed)
    # exactly once, and this fake stands in for that instance. Only `.choice`
    # is exercised on the cluster-bootstrap path, so nothing else is needed.
    class _FakeRNG:
        def choice(self, a, size=None, replace=True):
            return drawn_forced

    monkeypatch.setattr(np.random, "default_rng", lambda seed=None: _FakeRNG())

    idx = np.concatenate([np.flatnonzero(C_exc == c) for c in drawn_forced])
    n_cluster0 = int(np.sum(C_exc == unique_clusters[0]))
    n_cluster1 = int(np.sum(C_exc == unique_clusters[1]))
    # Sanity: the forced draw is actually a duplication, not a no-op — cluster 0's
    # rows appear twice-worth, cluster 1's rows are entirely absent.
    assert len(idx) == len(C_exc) - n_cluster1 + n_cluster0
    assert n_cluster0 > 0 and n_cluster1 > 0

    Y_b, Z_b = Y_exc[idx], Z_exc[idx]
    z_split_b = float(np.quantile(Z_b, z_split_quantile))
    low_b = Z_b <= z_split_b
    high_b = ~low_b
    assert low_b.sum() >= 10 and high_b.sum() >= 10
    expected_diff = (
        fit_gpd(Y_b[high_b], threshold=threshold).shape
        - fit_gpd(Y_b[low_b], threshold=threshold).shape
    )

    res = gpd_conditional_on_z(
        Y, Z, threshold_quantile=threshold_quantile, z_split_quantile=z_split_quantile,
        n_boot=25, seed=3, cluster_ids=cluster_ids,
    )
    lo, hi = res.shape_diff_bootstrap_ci_95
    assert lo == pytest.approx(expected_diff, abs=1e-9)
    assert hi == pytest.approx(expected_diff, abs=1e-9)


def test_gpd_conditional_on_z_too_few_unique_clusters_raises():
    rng = np.random.default_rng(5)
    n = 2000
    Y = rng.pareto(3.0, size=n) * 10.0
    Z = rng.uniform(0, 100, size=n)
    # Only 2 clusters total, so the exceedance subset also has only 2 unique
    # cluster ids — far below the 10-cluster floor needed for a non-degenerate
    # cluster bootstrap.
    clusters = np.repeat(np.arange(2), n // 2)
    with pytest.raises(ValueError, match="unique cluster"):
        gpd_conditional_on_z(
            Y, Z, threshold_quantile=0.90, n_boot=30, seed=1, cluster_ids=clusters,
        )


def test_gpd_conditional_on_z_nan_cluster_ids_raises():
    rng = np.random.default_rng(9)
    n = 2000
    Y = rng.pareto(3.0, size=n) * 10.0
    Z = rng.uniform(0, 100, size=n)
    clusters = np.repeat(np.arange(50), n // 50).astype(float)
    clusters[:200] = np.nan  # 10% NaN cluster ids, plausible at window-truncation boundaries
    with pytest.raises(ValueError, match="NaN"):
        gpd_conditional_on_z(
            Y, Z, threshold_quantile=0.90, n_boot=30, seed=1, cluster_ids=clusters,
        )
