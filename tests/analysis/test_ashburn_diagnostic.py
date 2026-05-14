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


def _make_spec_b_json_fixture(tmp_path: Path, pnode: str) -> Path:
    path = tmp_path / f"{pnode}.json"
    path.write_text(json.dumps({
        "response_col": f"total_lmp_rt_{pnode}",
        "pnode_label": pnode,
        "threshold_sweep": [
            {"threshold_quantile": 0.90, "linear": {"shape_coefficients": [0.5, -0.01],
              "shape_coefficients_bootstrap_ci_95": [[0.3, 0.7], [-0.02, 0.001]],
              "convergence_status": "converged"}},
            {"threshold_quantile": 0.95, "linear": {"shape_coefficients": [0.6, -0.025],
              "shape_coefficients_bootstrap_ci_95": [[0.4, 0.8], [-0.049, -0.004]],
              "convergence_status": "converged"}},
            {"threshold_quantile": 0.99, "linear": {"shape_coefficients": [0.7, 0.09],
              "shape_coefficients_bootstrap_ci_95": [[0.5, 0.9], [0.01, 0.17]],
              "convergence_status": "converged"}},
        ],
    }, indent=2))
    return path


def test_extract_threshold_sweep_summary_parses_spec_b_json(tmp_path: Path):
    from surg.analysis.ashburn_diagnostic import extract_threshold_sweep_summary

    json_path = _make_spec_b_json_fixture(tmp_path, "ashburn_tx1")
    summary = extract_threshold_sweep_summary(
        spec_b_json_path=json_path,
        threshold_qs=(0.90, 0.95, 0.99),
    )
    assert summary["pnode_label"] == "ashburn_tx1"
    assert len(summary["entries"]) == 3
    entry_99 = next(e for e in summary["entries"] if e["threshold_quantile"] == 0.99)
    assert entry_99["beta_1"] == 0.09
    assert entry_99["beta_1_ci_95"] == [0.01, 0.17]


def test_plot_lmp_vs_z_scatter_writes_nonempty_png(tmp_path: Path):
    from surg.analysis.ashburn_diagnostic import plot_lmp_vs_z_scatter

    panel = _ashburn_fixture(n_rows=3000, seed=7)
    out_path = tmp_path / "scatter_overlay.png"
    plot_lmp_vs_z_scatter(
        panel=panel,
        pnode_response_cols={"ashburn_tx1": "total_lmp_rt_ashburn_tx1",
                             "ashburn_tx2": "total_lmp_rt_ashburn_tx2"},
        z_col="dom_load_gradient_abs_mw_per_min",
        threshold_qs=(0.90, 0.95, 0.99, 0.995),
        out_path=out_path,
        fitted_slopes={"ashburn_tx1": {0.95: -0.025, 0.99: 0.093},
                       "ashburn_tx2": {0.95: -0.012, 0.99: -0.008}},
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_run_ashburn_diagnostic_writes_all_outputs(tmp_path: Path):
    from surg.analysis.ashburn_diagnostic import run_ashburn_diagnostic

    panel = _ashburn_fixture(n_rows=2000, seed=5)
    spec_b_dir = tmp_path / "gpd_continuous"
    spec_b_dir.mkdir()
    _make_spec_b_json_fixture(spec_b_dir, "ashburn_tx1")
    _make_spec_b_json_fixture(spec_b_dir, "ashburn_tx2")

    out_dir = tmp_path / "ashburn_diagnostic"
    run_ashburn_diagnostic(
        panel=panel,
        out_dir=out_dir,
        spec_b_results_dir=spec_b_dir,
        threshold_quantiles=(0.90, 0.95),  # smaller for test speed
    )
    assert (out_dir / "tx1_loo.json").exists()
    assert (out_dir / "tx2_loo.json").exists()
    assert (out_dir / "cross_threshold_summary.json").exists()
    assert (out_dir / "scatter_overlay.png").exists()
