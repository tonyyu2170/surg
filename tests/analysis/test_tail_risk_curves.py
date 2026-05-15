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
    """When Z has many ties, deciles still produce 10 valid bins (digitize handles)."""
    panel = pd.DataFrame({"z": np.concatenate([np.zeros(500), np.linspace(1, 10, 500)])})
    edges, bin_indices = compute_z_deciles(panel, "z")
    assert len(edges) == 11
    assert bin_indices.min() == 0
    assert bin_indices.max() == 9
