"""Tests for src/surg/preprocessing/loaders_5min.py — sub-q1 item #8."""
from pathlib import Path
import pandas as pd
import pytest

from surg.preprocessing.loaders_5min import (
    load_rt_lmp_5min,
    load_dom_load_5min,
    forward_fill_reserves_to_5min,
)


def test_load_rt_lmp_5min_returns_5min_frequency(tmp_path):
    raw_dir = tmp_path / "rt_fivemin_hrl_lmps" / "2026"
    raw_dir.mkdir(parents=True)
    df = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range(
            "2026-04-15", periods=12, freq="5min"
        ),
        "pnode_id": [35010371] * 12,
        "pnode_name": ["LOUDOUN"] * 12,
        "voltage": [500] * 12,
        "type": ["EHV"] * 12,
        "zone": ["DOM"] * 12,
        "system_energy_price_rt": list(range(12)),
        "total_lmp_rt": list(range(20, 32)),
        "congestion_price_rt": [0.0] * 12,
        "marginal_loss_price_rt": [1.0] * 12,
    })
    df.to_parquet(raw_dir / "test.parquet")

    result = load_rt_lmp_5min(tmp_path)
    assert len(result) == 12
    assert "datetime_beginning_ept" in result.columns
    assert "total_lmp_rt" in result.columns
    diffs = result["datetime_beginning_ept"].diff().dropna()
    assert (diffs == pd.Timedelta(minutes=5)).all()


def test_load_rt_lmp_5min_dedupes_and_sorts_per_pnode(tmp_path):
    raw_dir = tmp_path / "rt_fivemin_hrl_lmps" / "2026"
    raw_dir.mkdir(parents=True)
    base = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range(
            "2026-04-15", periods=4, freq="5min"
        ),
        "pnode_id": [35010371, 35010371, 35010365, 35010365],
        "pnode_name": ["A", "A", "B", "B"],
        "total_lmp_rt": [1.0, 2.0, 3.0, 4.0],
        "congestion_price_rt": [0.0] * 4,
    })
    base.to_parquet(raw_dir / "f1.parquet")
    # File 2 has overlap with f1's first row for pnode 35010371
    overlap = base.iloc[[0]].copy()
    overlap.to_parquet(raw_dir / "f2.parquet")

    result = load_rt_lmp_5min(tmp_path)
    # 4 unique (datetime, pnode_id) combos; the dup is dropped
    assert len(result) == 4
    # Per-pnode group is sorted ascending
    g = result[result["pnode_id"] == 35010371]
    assert g["datetime_beginning_ept"].is_monotonic_increasing


def test_load_rt_lmp_5min_empty_dir_returns_empty(tmp_path):
    result = load_rt_lmp_5min(tmp_path)
    assert result.empty


def test_load_dom_load_5min_dedupes_overlap(tmp_path):
    raw_dir = tmp_path / "inst_load"
    raw_dir.mkdir(parents=True)
    df1 = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range(
            "2026-04-15", periods=8, freq="5min"
        ),
        "area": ["PJM SOUTHERN REGION"] * 8,
        "instantaneous_load": [10000.0 + i * 50 for i in range(8)],
    })
    # df2 overlaps df1 at indices 5,6,7 (timestamps 00:25,00:30,00:35)
    df2 = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range(
            "2026-04-15 00:25", periods=8, freq="5min"
        ),
        "area": ["PJM SOUTHERN REGION"] * 8,
        "instantaneous_load": [10000.0 + i * 50 for i in range(5, 13)],
    })
    df1.to_parquet(raw_dir / "f1.parquet")
    df2.to_parquet(raw_dir / "f2.parquet")

    result = load_dom_load_5min(tmp_path)
    # 8 + 8 - 3 overlap = 13 unique timestamps
    assert len(result) == 13
    assert result["datetime_beginning_ept"].is_monotonic_increasing
    assert result["datetime_beginning_ept"].is_unique
    assert "dom_load_mw" in result.columns


def test_load_dom_load_5min_filters_to_southern_region(tmp_path):
    raw_dir = tmp_path / "inst_load"
    raw_dir.mkdir(parents=True)
    df = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range(
            "2026-04-15", periods=4, freq="5min"
        ),
        "area": ["PJM RTO", "PJM SOUTHERN REGION",
                 "PJM WESTERN REGION", "PJM SOUTHERN REGION"],
        "instantaneous_load": [99.0, 100.0, 99.0, 200.0],
    })
    df.to_parquet(raw_dir / "f1.parquet")

    result = load_dom_load_5min(tmp_path)
    assert len(result) == 2
    assert sorted(result["dom_load_mw"].tolist()) == [100.0, 200.0]


def test_load_dom_load_5min_empty_dir_returns_empty(tmp_path):
    result = load_dom_load_5min(tmp_path)
    assert result.empty


def test_forward_fill_reserves_to_5min_preserves_hourly_value():
    hourly = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range(
            "2026-04-15", periods=2, freq="h"
        ),
        "sync_reserve_clearing_price_rt": [5.0, 7.0],
        "primary_reserve_clearing_price_rt": [3.0, 4.0],
    })
    target_5min = pd.date_range("2026-04-15", periods=24, freq="5min")
    result = forward_fill_reserves_to_5min(hourly, target_5min)
    assert len(result) == 24
    # First 12 obs (hour 0): SR = 5.0
    assert (result["sync_reserve_clearing_price_rt"].iloc[:12] == 5.0).all()
    # Next 12 obs (hour 1): SR = 7.0
    assert (result["sync_reserve_clearing_price_rt"].iloc[12:] == 7.0).all()
    # PR equally
    assert (result["primary_reserve_clearing_price_rt"].iloc[:12] == 3.0).all()
    assert (result["primary_reserve_clearing_price_rt"].iloc[12:] == 4.0).all()


def test_forward_fill_reserves_to_5min_missing_hour_returns_nan():
    hourly = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range(
            "2026-04-15", periods=1, freq="h"
        ),
        "sync_reserve_clearing_price_rt": [5.0],
        "primary_reserve_clearing_price_rt": [3.0],
    })
    # Target index extends past the hourly window
    target_5min = pd.date_range("2026-04-15", periods=24, freq="5min")
    result = forward_fill_reserves_to_5min(hourly, target_5min)
    # First 12 obs: hour-0 mapped to 5.0
    assert (result["sync_reserve_clearing_price_rt"].iloc[:12] == 5.0).all()
    # Next 12 obs: hour 01:00 missing → NaN
    assert result["sync_reserve_clearing_price_rt"].iloc[12:].isna().all()
