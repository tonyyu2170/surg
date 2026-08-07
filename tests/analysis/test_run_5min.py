"""End-to-end smoke test for the 5-min analysis orchestrator (synthetic panel)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.run_5min import run_all_5min


def _synthetic_panel(n_days: int = 40) -> pd.DataFrame:
    """March-dated 5-min panel: in-filter rows form n_days night-islands."""
    rng = np.random.default_rng(11)
    ts = pd.date_range("2026-03-01", periods=288 * n_days, freq="5min")
    n = len(ts)
    z = rng.exponential(5.0, n)
    df = pd.DataFrame({
        "interval_start_utc": ts.tz_localize("UTC"),
        "datetime_beginning_ept": ts,
        "dom_load_mw": 11000.0,
        "dom_load_gradient_mw_per_hr": z * 60,
        "dom_load_gradient_abs_mw_per_min": z,
        "dom_load_gradient_signed_mw_per_min": z,
        "in_shoulder_season": True,
        "in_2_5am_window": ts.hour.isin([2, 3, 4]),
        "night_island_id": (ts.normalize() - pd.Timestamp("1970-01-01")).days,
    })
    df["passes_proposal_filter"] = df["in_shoulder_season"] & df["in_2_5am_window"]
    for pid in (35010365, 35010371, 1356178195):
        cong = rng.pareto(3.0, n) * 3.0
        energy = rng.normal(24, 3, n)
        loss = rng.normal(0.1, 0.05, n)
        df[f"congestion_price_rt_{pid}"] = cong
        df[f"system_energy_price_rt_{pid}"] = energy
        df[f"marginal_loss_price_rt_{pid}"] = loss
        df[f"total_lmp_rt_{pid}"] = cong + energy + loss
    cong_cols = [f"congestion_price_rt_{p}" for p in (35010365, 35010371, 1356178195)]
    df["congestion_price_rt_cluster_mean"] = df[cong_cols].mean(axis=1)
    df["congestion_price_rt_cluster_max"] = df[cong_cols].max(axis=1)
    for comp in ("total_lmp_rt", "system_energy_price_rt", "marginal_loss_price_rt"):
        df[f"{comp}_cluster_mean"] = df[
            [f"{comp}_{p}" for p in (35010365, 35010371, 1356178195)]
        ].mean(axis=1)
    return df


def test_run_all_5min_writes_all_outputs(tmp_path: Path):
    panel = _synthetic_panel()
    run_all_5min(panel, out_root=tmp_path, n_boot=25, seed=42,
                 taus=(0.90, 0.95))
    for label in ("loudoun", "pleasant_view", "goosecre", "cluster", "cluster_total_lmp"):
        assert (tmp_path / "qr_full" / f"{label}.json").exists()
    full = json.loads((tmp_path / "gpd" / "cluster_full_panel.json").read_text())
    infl = json.loads((tmp_path / "gpd" / "cluster_in_filter.json").read_text())
    assert full["conditional_z"]["bootstrap_mode"] == "iid"
    assert infl["conditional_z"]["bootstrap_mode"] == "cluster"
    assert (tmp_path / "tail_risk_curves" / "cross_pnode_summary.json").exists()


def test_run_all_5min_infilter_uses_only_filtered_rows(tmp_path: Path):
    panel = _synthetic_panel()
    run_all_5min(panel, out_root=tmp_path, n_boot=25, seed=42, taus=(0.90,))
    infl = json.loads((tmp_path / "gpd" / "cluster_in_filter.json").read_text())
    n_filtered = int(panel["passes_proposal_filter"].sum())
    assert infl["n_total_panel"] == n_filtered
