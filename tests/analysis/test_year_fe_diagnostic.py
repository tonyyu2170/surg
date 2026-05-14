"""Tests for year_fe_diagnostic.py — sub-q1 closure item #3 (descriptive)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _two_year_panel(per_year: int = 1000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    timestamps = (
        list(pd.date_range("2023-01-01", periods=per_year, freq="h")) +
        list(pd.date_range("2024-01-01", periods=per_year, freq="h"))
    )
    return pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(timestamps),
        "Y": np.concatenate([
            rng.exponential(1.0, size=per_year),
            rng.exponential(2.0, size=per_year),   # 2024 is hotter
        ]),
        "Z": rng.uniform(0, 10, size=2 * per_year),
    })


def test_compute_raw_per_year_stats_returns_one_row_per_year():
    from surg.analysis.year_fe_diagnostic import compute_raw_per_year_stats

    panel = _two_year_panel()
    stats = compute_raw_per_year_stats(
        panel, response_col="Y", year_col="datetime_beginning_ept",
        pct_list=(0.90, 0.95, 0.99),
    )
    assert isinstance(stats, list)
    assert len(stats) == 2
    years = {s["year"] for s in stats}
    assert years == {2023, 2024}
    for s in stats:
        assert "p90" in s
        assert "p95" in s
        assert "p99" in s
        assert "n_obs" in s


def test_compute_raw_per_year_stats_p99_higher_in_hotter_year():
    from surg.analysis.year_fe_diagnostic import compute_raw_per_year_stats

    panel = _two_year_panel(per_year=2000, seed=42)
    stats = compute_raw_per_year_stats(
        panel, response_col="Y", year_col="datetime_beginning_ept",
        pct_list=(0.99,),
    )
    by_year = {s["year"]: s for s in stats}
    assert by_year[2024]["p99"] > by_year[2023]["p99"]


def test_bootstrap_year_dummy_coefs_returns_ci_per_year():
    from surg.analysis.year_fe_diagnostic import bootstrap_year_dummy_coefs

    panel = _two_year_panel(per_year=1500, seed=1)
    result = bootstrap_year_dummy_coefs(
        panel,
        response_col="Y",
        z_col="Z",
        year_col="datetime_beginning_ept",
        taus=(0.50,),
        n_boot=40,
        seed=0,
    )
    assert "tau_0.50" in result
    by_year = result["tau_0.50"]
    # Baseline (2023) excluded; 2024 dummy present.
    assert "year_2024" in by_year
    entry = by_year["year_2024"]
    assert "point" in entry
    assert "ci" in entry
    assert len(entry["ci"]) == 2
