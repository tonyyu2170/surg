"""Tests for spike_exceedance_comparison.py — sub-q1 item #8 Part B."""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from surg.analysis.spike_exceedance_comparison import (
    compute_per_pnode_metrics,
    aggregate_cross_pnode_summary,
    run_spike_exceedance_comparison,
)


def test_hidden_fraction_basic():
    """Hour with one $600 spike + 11 $25 obs. Mean = 72.9 < $100 → hourly
    aggregation hides the $100+ spike."""
    lmp_5min = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2026-04-15", periods=12, freq="5min"),
        "pnode_id": [35010371] * 12,
        "total_lmp_rt": [600.0] + [25.0] * 11,
    })
    lmp_hourly = pd.DataFrame({
        "datetime_beginning_ept": [pd.Timestamp("2026-04-15 00:00")],
        "pnode_id": [35010371],
        "total_lmp_rt": [72.92],
    })
    result = compute_per_pnode_metrics(
        lmp_5min, lmp_hourly, pnode_id=35010371,
        thresholds=[100, 250, 500, 1000],
    )
    m100 = result["by_threshold"][100]
    assert m100["n_5min_exceedances"] == 1
    assert m100["n_hourly_published_exceedances"] == 0
    assert m100["n_hidden_by_hourly"] == 1
    assert m100["hidden_fraction"] == 1.0


def test_hidden_fraction_zero_5min_exceedances_returns_nan():
    """When n_5min_exceedances == 0, hidden_fraction is NaN +
    n_below_inference_floor=True (no division by zero)."""
    lmp_5min = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2026-04-15", periods=12, freq="5min"),
        "pnode_id": [35010371] * 12,
        "total_lmp_rt": [25.0] * 12,
    })
    lmp_hourly = pd.DataFrame({
        "datetime_beginning_ept": [pd.Timestamp("2026-04-15 00:00")],
        "pnode_id": [35010371],
        "total_lmp_rt": [25.0],
    })
    result = compute_per_pnode_metrics(
        lmp_5min, lmp_hourly, pnode_id=35010371,
        thresholds=[100, 250],
    )
    m100 = result["by_threshold"][100]
    assert m100["n_5min_exceedances"] == 0
    assert math.isnan(m100["hidden_fraction"])
    assert m100["n_below_inference_floor"] is True


def test_hidden_fraction_full_visibility():
    """Spike $1000 in 5-min, hourly aggregation $1100 (exceeds threshold)
    → hourly visible, hidden_fraction = 0."""
    lmp_5min = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2026-04-15", periods=12, freq="5min"),
        "pnode_id": [35010371] * 12,
        "total_lmp_rt": [1000.0] * 12,
    })
    lmp_hourly = pd.DataFrame({
        "datetime_beginning_ept": [pd.Timestamp("2026-04-15 00:00")],
        "pnode_id": [35010371],
        "total_lmp_rt": [1000.0],
    })
    result = compute_per_pnode_metrics(
        lmp_5min, lmp_hourly, pnode_id=35010371,
        thresholds=[500],
    )
    m500 = result["by_threshold"][500]
    assert m500["n_5min_exceedances"] == 12
    assert m500["n_hourly_published_exceedances"] == 1
    assert m500["n_hidden_by_hourly"] == 0
    assert m500["hidden_fraction"] == 0.0


def test_compute_per_pnode_metrics_drops_unmatched_hours():
    """Hours where the hourly panel has no row are counted in
    n_dropped_unmatched_hours."""
    lmp_5min = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2026-04-15", periods=24, freq="5min"),
        "pnode_id": [35010371] * 24,
        "total_lmp_rt": [50.0] * 24,
    })
    # Only first hour matched
    lmp_hourly = pd.DataFrame({
        "datetime_beginning_ept": [pd.Timestamp("2026-04-15 00:00")],
        "pnode_id": [35010371],
        "total_lmp_rt": [50.0],
    })
    result = compute_per_pnode_metrics(
        lmp_5min, lmp_hourly, pnode_id=35010371,
        thresholds=[100],
    )
    assert result["n_dropped_unmatched_hours"] == 1


def test_aggregate_cross_pnode_summary_extracts_headline():
    per_pnode_results = [
        {
            "pnode_id": 1, "pnode_label": "P1",
            "by_threshold": {
                100: {"hidden_fraction": 0.5,
                      "n_5min_exceedances": 10,
                      "n_hourly_published_exceedances": 5,
                      "n_hidden_by_hourly": 5,
                      "n_below_inference_floor": False,
                      "threshold_percentile": 0.95},
            },
        },
        {
            "pnode_id": 2, "pnode_label": "P2",
            "by_threshold": {
                100: {"hidden_fraction": 0.8,
                      "n_5min_exceedances": 20,
                      "n_hourly_published_exceedances": 4,
                      "n_hidden_by_hourly": 16,
                      "n_below_inference_floor": False,
                      "threshold_percentile": 0.97},
            },
        },
    ]
    summary = aggregate_cross_pnode_summary(per_pnode_results)
    assert summary["thresholds"] == [100]
    assert len(summary["pnodes"]) == 2


def test_run_spike_exceedance_comparison_writes_outputs(tmp_path: Path):
    """End-to-end: synthetic 5-min + hourly panels → JSON + CSV outputs."""
    n_5min = 96  # 8 hours of 5-min data per pnode
    rows_5min = []
    for pid in (1, 2):
        rows_5min.append(pd.DataFrame({
            "datetime_beginning_ept": pd.date_range(
                "2026-04-15", periods=n_5min, freq="5min"
            ),
            "pnode_id": [pid] * n_5min,
            "total_lmp_rt": [50.0 + i % 30 for i in range(n_5min)],
        }))
    panel_5min = pd.concat(rows_5min, ignore_index=True)

    rows_hourly = []
    for pid in (1, 2):
        rows_hourly.append(pd.DataFrame({
            "datetime_beginning_ept": pd.date_range(
                "2026-04-15", periods=8, freq="h"
            ),
            "pnode_id": [pid] * 8,
            "total_lmp_rt": [60.0] * 8,
        }))
    panel_hourly = pd.concat(rows_hourly, ignore_index=True)

    out_root = tmp_path / "outputs_5min" / "lmp_descriptive_6mo"
    run_spike_exceedance_comparison(
        panel_5min=panel_5min,
        panel_hourly=panel_hourly,
        out_root=out_root,
        thresholds=[50, 100, 250],
    )
    sec_dir = out_root / "spike_exceedance_comparison"
    assert sec_dir.exists()
    # Per-pnode JSON for at least one pnode
    json_files = list(sec_dir.glob("pnode_*.json"))
    assert len(json_files) >= 1
    # Cross-pnode summary
    assert (sec_dir / "cross_pnode_summary.json").exists()
    assert (sec_dir / "cross_pnode_summary.csv").exists()
