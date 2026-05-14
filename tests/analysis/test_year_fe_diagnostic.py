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


def test_bootstrap_secular_component_returns_ci_per_tau():
    from surg.analysis.year_fe_diagnostic import bootstrap_secular_component

    panel = _two_year_panel(per_year=1500, seed=2)
    result = bootstrap_secular_component(
        panel,
        response_col="Y",
        z_col="Z",
        year_col="datetime_beginning_ept",
        taus=(0.50, 0.95),
        n_boot=30,
        seed=0,
    )
    for key in ("tau_0.50", "tau_0.95"):
        assert key in result
        entry = result[key]
        assert "primary_z_slope" in entry
        assert "year_fe_z_slope" in entry
        assert "secular_component_point" in entry
        assert "secular_component_ci" in entry
        assert len(entry["secular_component_ci"]) == 2


def test_run_year_fe_diagnostic_writes_per_pnode_json(tmp_path: Path):
    from surg.analysis.year_fe_diagnostic import run_year_fe_diagnostic

    panel = _two_year_panel(per_year=1200, seed=3)
    out_path = tmp_path / "year_fe_diagnostic" / "test_pnode.json"
    run_year_fe_diagnostic(
        panel=panel,
        out_path=out_path,
        pnode_label="test_pnode",
        response_col="Y",
        z_col="Z",
        taus=(0.50, 0.95),
        n_boot=20,
        seed=0,
    )
    assert out_path.exists()
    payload = json.loads(out_path.read_text())
    assert payload["pnode_label"] == "test_pnode"
    assert payload["response_col"] == "Y"
    assert "layer1_raw_per_year" in payload
    assert "layer2_year_dummy_bootstrap" in payload
    assert "layer3_secular_component_bootstrap" in payload
    assert len(payload["layer1_raw_per_year"]) == 2


def test_write_cross_pnode_summary_aggregates_per_pnode_jsons(tmp_path: Path):
    from surg.analysis.year_fe_diagnostic import write_cross_pnode_summary

    out_dir = tmp_path / "year_fe_diagnostic"
    out_dir.mkdir()
    for label in ("pnode_a", "pnode_b"):
        (out_dir / f"{label}.json").write_text(json.dumps({
            "pnode_label": label,
            "layer3_secular_component_bootstrap": {
                "tau_0.95": {"primary_z_slope": 1.0, "year_fe_z_slope": 0.5,
                              "secular_component_point": 0.5,
                              "secular_component_ci": [0.0, 1.0]},
            },
        }))
    write_cross_pnode_summary(out_dir, ("pnode_a", "pnode_b"))
    summary = json.loads((out_dir / "cross_pnode_summary.json").read_text())
    assert len(summary["rows"]) == 2
    labels = {r["pnode_label"] for r in summary["rows"]}
    assert labels == {"pnode_a", "pnode_b"}
