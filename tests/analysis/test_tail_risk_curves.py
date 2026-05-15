"""Tests for src/surg/analysis/tail_risk_curves.py — sub-q1 item #6."""

import json

import numpy as np
import pandas as pd
import pytest

from surg.analysis.tail_risk_curves import (
    _ensure_total_lmp_columns,
    aggregate_cross_pnode_summary,
    compute_exceedance_probability_with_ci,
    compute_threshold_percentiles,
    compute_z_deciles,
    plot_tail_risk_curves,
    run_pnode_tail_risk_curves,
    run_tail_risk_curves,
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
    assert len(result["decile_edges_mw_per_min"]) == 11
    assert len(result["decile_n_obs"]) == 10
    assert "threshold_percentiles" in result
    assert "results" in result

    for resp_key in ("total_lmp", "congestion"):
        assert resp_key in result["results"]
        deciles = result["results"][resp_key]
        assert len(deciles) == 10
        for decile_entry in deciles:
            assert "decile" in decile_entry
            assert "z_range_mw_per_min" in decile_entry
            assert "n_total" in decile_entry
            assert "by_threshold" in decile_entry
            for t in (50.0, 100.0):
                cell = decile_entry["by_threshold"][t]
                assert "p_hat" in cell
                assert "n_exc" in cell
                assert "ci_95" in cell
                assert len(cell["ci_95"]) == 2


def test_aggregate_cross_pnode_summary_extracts_top_decile():
    """Given 2 fake per-pnode results, summary picks top-decile entries per (response, threshold)."""
    per_pnode = [
        {
            "pnode_label": "primary",
            "thresholds": [100.0, 500.0],
            "n_boot": 200,
            "decile_edges_mw_per_min": [0.0] + [float(i) for i in range(1, 11)],
            "decile_n_obs": [100] * 10,
            "results": {
                "total_lmp": [
                    {
                        "decile": d + 1,
                        "z_range_mw_per_min": [d * 1.0, (d + 1) * 1.0],
                        "n_total": 100,
                        "by_threshold": {
                            100.0: {"p_hat": 0.01 * d, "n_exc": d, "ci_95": [0.0, 0.02 * d]},
                            500.0: {"p_hat": 0.005 * d, "n_exc": d // 2, "ci_95": [0.0, 0.01 * d]},
                        },
                    }
                    for d in range(10)
                ],
                "congestion": [
                    {
                        "decile": d + 1,
                        "z_range_mw_per_min": [d * 1.0, (d + 1) * 1.0],
                        "n_total": 100,
                        "by_threshold": {
                            100.0: {"p_hat": 0.02 * d, "n_exc": 2 * d, "ci_95": [0.0, 0.04 * d]},
                            500.0: {"p_hat": 0.01 * d, "n_exc": d, "ci_95": [0.0, 0.02 * d]},
                        },
                    }
                    for d in range(10)
                ],
            },
        },
        {
            "pnode_label": "dom_zonal",
            "thresholds": [100.0, 500.0],
            "n_boot": 200,
            "decile_edges_mw_per_min": [0.0] + [float(i) for i in range(1, 11)],
            "decile_n_obs": [100] * 10,
            "results": {
                "total_lmp": [
                    {
                        "decile": d + 1,
                        "z_range_mw_per_min": [d * 1.0, (d + 1) * 1.0],
                        "n_total": 100,
                        "by_threshold": {
                            100.0: {"p_hat": 0.005 * d, "n_exc": d, "ci_95": [0.0, 0.01 * d]},
                            500.0: {"p_hat": 0.002 * d, "n_exc": d // 3, "ci_95": [0.0, 0.005 * d]},
                        },
                    }
                    for d in range(10)
                ],
                "congestion": [
                    {
                        "decile": d + 1,
                        "z_range_mw_per_min": [d * 1.0, (d + 1) * 1.0],
                        "n_total": 100,
                        "by_threshold": {
                            100.0: {"p_hat": 0.01 * d, "n_exc": d, "ci_95": [0.0, 0.02 * d]},
                            500.0: {"p_hat": 0.005 * d, "n_exc": d // 2, "ci_95": [0.0, 0.01 * d]},
                        },
                    }
                    for d in range(10)
                ],
            },
        },
    ]

    summary = aggregate_cross_pnode_summary(per_pnode)

    assert summary["scope"] == "top_decile_only"
    assert summary["thresholds"] == [100.0, 500.0]
    assert len(summary["pnodes"]) == 2

    primary_entry = next(p for p in summary["pnodes"] if p["pnode_label"] == "primary")
    # Top decile (d=9) values: 0.01 * 9 = 0.09 (total_lmp @ 100)
    assert primary_entry["results"]["total_lmp"][100.0]["p_hat"] == pytest.approx(0.09)
    assert primary_entry["results"]["total_lmp"][500.0]["p_hat"] == pytest.approx(0.045)

    # Verify structural properties:
    assert summary["n_boot"] == 200  # propagated from input
    assert primary_entry["z_range_top_decile_mw_per_min"] == [9.0, 10.0]
    assert primary_entry["n_top_decile"] == 100
    assert 500.0 in primary_entry["results"]["congestion"]  # congestion response present
    dom_zonal_entry = next(p for p in summary["pnodes"] if p["pnode_label"] == "dom_zonal")
    assert dom_zonal_entry["results"]["total_lmp"][100.0]["p_hat"] == pytest.approx(0.045)
    # ci_95 propagated:
    assert primary_entry["results"]["total_lmp"][100.0]["ci_95"] == [0.0, pytest.approx(0.18)]


def test_plot_tail_risk_curves_writes_png(tmp_path):
    """Plot smoke test: given a per-pnode result dict, writes a non-empty PNG."""
    rng = np.random.default_rng(seed=99)
    n = 1000
    panel = pd.DataFrame({
        "z": rng.exponential(scale=1.0, size=n),
        "total_lmp_rt_cluster_mean": rng.lognormal(mean=3.5, sigma=1.0, size=n),
        "congestion_price_rt_cluster_mean": rng.exponential(scale=10.0, size=n),
    })
    per_pnode = run_pnode_tail_risk_curves(
        panel=panel,
        pnode_label="test_pnode",
        response_cols={
            "total_lmp": "total_lmp_rt_cluster_mean",
            "congestion": "congestion_price_rt_cluster_mean",
        },
        z_col="z",
        thresholds=[10.0, 50.0, 100.0],
        n_boot=20,
        seed=11,
    )

    out_path = tmp_path / "test_plot.png"
    plot_tail_risk_curves(per_pnode, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 5_000  # non-trivial PNG


def _make_synthetic_panel(n: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Synthetic panel covering the 7 pnodes + filter column."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"dom_load_gradient_abs_mw_per_min": rng.exponential(scale=2.0, size=n)})
    df["passes_proposal_filter"] = True
    for pnode in ("cluster_mean", "ox", "bristers", "dom_zonal", "ashburn_tx1", "ashburn_tx2"):
        df[f"total_lmp_rt_{pnode}"] = rng.lognormal(mean=3.5, sigma=1.0, size=n)
        df[f"congestion_price_rt_{pnode}"] = rng.exponential(scale=10.0, size=n)
    return df


def test_run_tail_risk_curves_writes_all_expected_outputs(tmp_path):
    """End-to-end: run_tail_risk_curves writes 5 JSONs + 4 PNGs + 1 CSV under out_root."""
    panel = _make_synthetic_panel(n=2000, seed=0)
    out_root = tmp_path / "outputs"
    out_root.mkdir()

    run_tail_risk_curves(
        panel=panel,
        out_root=out_root,
        n_boot=5,
        seed=0,
    )

    tr_dir = out_root / "tail_risk_curves"
    assert tr_dir.exists()

    expected_jsons = [
        "primary.json",
        "dom_zonal.json",
        "ashburn_tx1.json",
        "ashburn_tx2.json",
        "cross_pnode_summary.json",
    ]
    for name in expected_jsons:
        assert (tr_dir / name).exists(), f"missing {name}"

    expected_pngs = [
        "primary.png",
        "dom_zonal.png",
        "ashburn_tx1.png",
        "ashburn_tx2.png",
    ]
    for name in expected_pngs:
        assert (tr_dir / name).exists(), f"missing {name}"
        assert (tr_dir / name).stat().st_size > 5_000

    assert (tr_dir / "cross_pnode_summary.csv").exists()

    # Sanity-check the primary JSON structure (post-rename keys)
    with open(tr_dir / "primary.json") as f:
        primary = json.load(f)
    assert primary["pnode_label"] == "primary"
    assert "decile_edges_mw_per_min" in primary
    assert "results" in primary
    assert "total_lmp" in primary["results"]
    assert "congestion" in primary["results"]
    assert "filter" in primary  # added by top-level orchestrator


def test_ensure_total_lmp_columns_derives_missing_via_lmp_identity():
    """For a pnode with all 3 components but no labeled total_lmp, derive total_lmp = sum."""
    panel = pd.DataFrame({
        "system_energy_price_rt_ox": [10.0, 20.0, 30.0],
        "congestion_price_rt_ox": [1.0, 2.0, 3.0],
        "marginal_loss_price_rt_ox": [0.1, 0.2, 0.3],
        # No total_lmp_rt_ox column present
    })
    result = _ensure_total_lmp_columns(panel, ("ox",))

    assert "total_lmp_rt_ox" in result.columns
    assert list(result["total_lmp_rt_ox"]) == pytest.approx([11.1, 22.2, 33.3])
    # Source panel unchanged (function returns a copy)
    assert "total_lmp_rt_ox" not in panel.columns


def test_ensure_total_lmp_columns_preserves_existing_columns():
    """For a pnode that already has total_lmp_rt_<pnode>, the existing column is preserved unchanged."""
    panel = pd.DataFrame({
        "total_lmp_rt_ashburn_tx1": [100.0, 200.0],
        "system_energy_price_rt_ashburn_tx1": [50.0, 60.0],
        "congestion_price_rt_ashburn_tx1": [40.0, 130.0],
        "marginal_loss_price_rt_ashburn_tx1": [10.0, 10.0],
    })
    result = _ensure_total_lmp_columns(panel, ("ashburn_tx1",))

    # Existing column unchanged, NOT overwritten by the derived sum (100, 200)
    assert list(result["total_lmp_rt_ashburn_tx1"]) == [100.0, 200.0]


def test_ensure_total_lmp_columns_skips_pnodes_without_components():
    """If components are missing for a pnode, the function leaves the panel as-is without crashing."""
    panel = pd.DataFrame({"unrelated": [1.0, 2.0]})
    result = _ensure_total_lmp_columns(panel, ("ox",))

    assert "total_lmp_rt_ox" not in result.columns
