"""Tests for ashburn_diagnostic.py — sub-q1 closure item #4 (descriptive)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _ashburn_fixture(n_rows: int = 4000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n_rows, freq="h"),
        "dom_load_gradient_abs_mw_per_min": rng.uniform(0, 10, size=n_rows),
        "total_lmp_rt_ashburn_tx1": rng.exponential(2.0, size=n_rows),
        "total_lmp_rt_ashburn_tx2": rng.exponential(1.8, size=n_rows),
    })


def test_loo_beta_distribution_returns_n_exc_betas():
    from surg.analysis.ashburn_diagnostic import loo_beta_distribution

    panel = _ashburn_fixture()
    result = loo_beta_distribution(
        panel=panel,
        response_col="total_lmp_rt_ashburn_tx1",
        z_col="dom_load_gradient_abs_mw_per_min",
        threshold_quantile=0.95,
    )
    assert result.n_exc > 0
    assert len(result.loo_beta_1_distribution) == result.n_exc
    assert len(result.delta_beta_1_per_exceedance) == result.n_exc
    assert len(result.top5_influential_indices) == min(5, result.n_exc)


def test_loo_beta_distribution_top5_sorted_descending_by_delta():
    from surg.analysis.ashburn_diagnostic import loo_beta_distribution

    panel = _ashburn_fixture(n_rows=2000, seed=42)
    result = loo_beta_distribution(
        panel=panel,
        response_col="total_lmp_rt_ashburn_tx1",
        z_col="dom_load_gradient_abs_mw_per_min",
        threshold_quantile=0.95,
    )
    deltas = result.delta_beta_1_per_exceedance
    top5 = result.top5_influential_indices
    sorted_top5 = sorted(top5, key=lambda i: -abs(deltas[i]))
    assert list(top5) == sorted_top5
