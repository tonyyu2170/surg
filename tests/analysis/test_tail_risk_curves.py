"""Tests for src/surg/analysis/tail_risk_curves.py — sub-q1 item #6."""

import numpy as np
import pandas as pd
import pytest

from surg.analysis.tail_risk_curves import (
    compute_exceedance_probability_with_ci,
    compute_threshold_percentiles,
    run_pnode_tail_risk_curves,
    compute_z_deciles,
)


def test_compute_z_deciles_returns_11_edges_and_correct_bin_indices():
    """Decile binning produces 11 edges + 10 bins; each obs assigned to its decile."""
    rng = np.random.default_rng(seed=0)
    panel = pd.DataFrame({"z": rng.uniform(0, 10, size=1000)})

    edges, bin_indices = compute_z_deciles(panel, "z")

    assert len(edges) == 11, "expected 11 edges (10 bins + upper bound)"
    assert len(bin_indices) == 1000, "one bin index per row"
    assert bin_indices.min() == 0
    assert bin_indices.max() == 9

    # Each bin should have ~100 observations (equal-count quantile bins)
    bin_counts = np.bincount(bin_indices, minlength=10)
    assert bin_counts.min() >= 95, f"bin counts too uneven: {bin_counts}"
    assert bin_counts.max() <= 105, f"bin counts too uneven: {bin_counts}"


def test_compute_z_deciles_handles_ties_at_boundary():
    """When Z has many ties at the lower end, quantile edges collapse and affected interior bins are empty; the function still returns 11 edges and valid [0, 9] indices, and tied values land in bin 0 (pins the right=True contract)."""
    panel = pd.DataFrame({"z": np.concatenate([np.zeros(500), np.linspace(1, 10, 500)])})
    edges, bin_indices = compute_z_deciles(panel, "z")
    assert len(edges) == 11
    assert bin_indices.min() == 0
    assert bin_indices.max() == 9
    # Pin the right=True contract: all tied zeros must land in bin 0,
    # not be pushed up to bin 4 (where right=False would put them).
    assert (bin_indices[:500] == 0).all(), "all tied zeros should land in bin 0 under right=True"


def test_compute_threshold_percentiles_returns_dict_per_threshold():
    """For known thresholds in a uniform [0, 100] distribution, the percentile-of-score should match the threshold itself."""
    panel = pd.DataFrame({"resp": np.linspace(0, 100, 10001)})
    thresholds = [25.0, 50.0, 75.0, 99.0]

    out = compute_threshold_percentiles(panel, "resp", thresholds)

    assert set(out.keys()) == {25.0, 50.0, 75.0, 99.0}
    # P(resp <= threshold) should equal threshold/100 for a uniform [0,100] series
    assert abs(out[25.0] - 0.25) < 0.001
    assert abs(out[50.0] - 0.50) < 0.001
    assert abs(out[75.0] - 0.75) < 0.001
    assert abs(out[99.0] - 0.99) < 0.001


def test_compute_threshold_percentiles_handles_threshold_above_max():
    """A threshold higher than the panel max returns percentile 1.0."""
    panel = pd.DataFrame({"resp": np.linspace(0, 100, 1001)})
    out = compute_threshold_percentiles(panel, "resp", [200.0])
    assert out[200.0] == pytest.approx(1.0)


def test_exceedance_probability_point_estimate_matches_empirical():
    """Point estimate is sum(resp > threshold) / n; matches naive count for any (Z, resp) panel."""
    rng = np.random.default_rng(seed=42)
    panel = pd.DataFrame({
        "z": rng.uniform(0, 1, size=1000),
        "resp": rng.normal(loc=50, scale=20, size=1000),
    })
    mask = np.ones(1000, dtype=bool)  # all rows
    threshold = 60.0

    p_hat, n_exc, n_total, ci_low, ci_high = compute_exceedance_probability_with_ci(
        panel, response_col="resp", threshold=threshold, z_bin_mask=mask, n_boot=50, seed=0
    )

    expected_p_hat = (panel["resp"] > threshold).sum() / len(panel)
    assert p_hat == pytest.approx(float(expected_p_hat))
    assert n_exc == (panel["resp"] > threshold).sum()
    assert n_total == 1000
    assert ci_low <= p_hat <= ci_high


def test_exceedance_probability_zero_exceedances_returns_p_hat_zero():
    """When no observation exceeds the threshold, p_hat=0; CI lower=0; CI upper is Wilson exact."""
    panel = pd.DataFrame({
        "z": np.arange(100),
        "resp": np.zeros(100),  # nothing exceeds threshold > 0
    })
    mask = np.ones(100, dtype=bool)

    p_hat, n_exc, n_total, ci_low, ci_high = compute_exceedance_probability_with_ci(
        panel, response_col="resp", threshold=100.0, z_bin_mask=mask, n_boot=50, seed=0
    )

    assert p_hat == 0.0
    assert n_exc == 0
    assert n_total == 100
    assert ci_low == 0.0
    # Wilson exact upper bound for (0, 100) at alpha=0.05 is ~0.036
    assert 0.0 < ci_high < 0.10


def test_exceedance_probability_ci_includes_point_estimate():
    """For a normal-power bin, the 95% CI should bracket the point estimate."""
    rng = np.random.default_rng(seed=7)
    panel = pd.DataFrame({
        "z": rng.uniform(0, 1, size=500),
        "resp": rng.exponential(scale=50, size=500),
    })
    mask = np.ones(500, dtype=bool)
    threshold = 50.0

    p_hat, _, _, ci_low, ci_high = compute_exceedance_probability_with_ci(
        panel, response_col="resp", threshold=threshold, z_bin_mask=mask, n_boot=200, seed=11
    )

    assert ci_low <= p_hat <= ci_high
    assert ci_high - ci_low < 0.15  # for n=500, CI width should be reasonable


def test_exceedance_probability_all_exceedances_returns_wilson_lower():
    """When every observation exceeds the threshold, p_hat=1; CI uses Wilson lower bound."""
    panel = pd.DataFrame({
        "z": np.arange(50),
        "resp": np.full(50, 500.0),  # all exceed threshold=100
    })
    mask = np.ones(50, dtype=bool)

    p_hat, n_exc, n_total, ci_low, ci_high = compute_exceedance_probability_with_ci(
        panel, response_col="resp", threshold=100.0, z_bin_mask=mask, n_boot=50, seed=0
    )

    assert p_hat == 1.0
    assert n_exc == 50
    assert n_total == 50
    assert ci_high == 1.0
    # Wilson lower for (50, 50) at alpha=0.05: 50 / (50 + 1.96^2) = ~0.929
    expected_low = 50 / (50 + 1.96**2)
    assert ci_low == pytest.approx(expected_low, rel=1e-5)


def test_run_pnode_tail_risk_curves_returns_full_schema():
    """Per-pnode orchestrator returns nested dict with all expected fields."""
    rng = np.random.default_rng(seed=3)
    n = 2000
    panel = pd.DataFrame({
        "z": rng.exponential(scale=2.0, size=n),
        "total_lmp_rt_cluster_mean": rng.lognormal(mean=3.5, sigma=1.0, size=n),
        "congestion_price_rt_cluster_mean": rng.exponential(scale=10.0, size=n),
    })

    result = run_pnode_tail_risk_curves(
        panel=panel,
        pnode_label="primary",
        response_cols={
            "total_lmp": "total_lmp_rt_cluster_mean",
            "congestion": "congestion_price_rt_cluster_mean",
        },
        z_col="z",
        thresholds=[50.0, 100.0],
        n_deciles=10,
        n_boot=20,
        seed=5,
    )

    assert result["pnode_label"] == "primary"
    assert result["z_col"] == "z"
    assert result["thresholds"] == [50.0, 100.0]
    assert result["n_boot"] == 20
    assert len(result["decile_edges"]) == 11
    assert len(result["decile_n_obs"]) == 10
    assert "threshold_percentiles" in result
    assert "results" in result

    for resp_key in ("total_lmp", "congestion"):
        assert resp_key in result["results"]
        deciles = result["results"][resp_key]
        assert len(deciles) == 10
        for decile_entry in deciles:
            assert "decile" in decile_entry
            assert "z_range" in decile_entry
            assert "n_total" in decile_entry
            assert "by_threshold" in decile_entry
            for t in (50.0, 100.0):
                cell = decile_entry["by_threshold"][t]
                assert "p_hat" in cell
                assert "n_exc" in cell
                assert "ci_95" in cell
                assert len(cell["ci_95"]) == 2
