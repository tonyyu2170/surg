"""Tests for src/surg/analysis/tail_risk_curves.py — sub-q1 item #6."""

import numpy as np
import pandas as pd
import pytest

from surg.analysis.tail_risk_curves import compute_z_deciles


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


from surg.analysis.tail_risk_curves import compute_threshold_percentiles


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
