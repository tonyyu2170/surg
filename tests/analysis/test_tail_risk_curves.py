"""Tests for src/surg/analysis/tail_risk_curves.py — sub-q1 item #6."""

import numpy as np
import pandas as pd
import pytest

from surg.analysis.tail_risk_curves import (
    compute_exceedance_probability_with_ci,
    compute_threshold_percentiles,
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
