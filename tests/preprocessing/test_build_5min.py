"""Tests for src/surg/preprocessing/build_5min.py — sub-q1 item #8."""
from pathlib import Path
import pandas as pd
import pytest

from surg.preprocessing.build_5min import build_joint_5min_panel
from surg.preprocessing.build import LOUDOUN_CLUSTER_IDS


PNODE_IDS_FOR_TEST = list(LOUDOUN_CLUSTER_IDS)  # 6 cluster pnodes


def _make_synthetic_data_root(tmp_path: Path, periods: int = 288) -> Path:
    """Build a minimal data_root with `periods` 5-min stamps of data."""
    lmp_dir = tmp_path / "rt_fivemin_hrl_lmps" / "2026"
    lmp_dir.mkdir(parents=True)
    rows = []
    for pid in PNODE_IDS_FOR_TEST:
        rows.append(pd.DataFrame({
            "datetime_beginning_ept": pd.date_range(
                "2026-04-15", periods=periods, freq="5min"
            ),
            "pnode_id": [pid] * periods,
            "pnode_name": [f"P{pid}"] * periods,
            "voltage": [500] * periods,
            "type": ["EHV"] * periods,
            "zone": ["DOM"] * periods,
            "system_energy_price_rt": [25.0] * periods,
            "total_lmp_rt": [30.0 + i * 0.1 for i in range(periods)],
            "congestion_price_rt": [0.0] * periods,
            "marginal_loss_price_rt": [1.0] * periods,
        }))
    pd.concat(rows, ignore_index=True).to_parquet(lmp_dir / "test.parquet")

    load_dir = tmp_path / "inst_load"
    load_dir.mkdir(parents=True)
    pd.DataFrame({
        "datetime_beginning_ept": pd.date_range(
            "2026-04-15", periods=periods, freq="5min"
        ),
        "area": ["PJM SOUTHERN REGION"] * periods,
        "instantaneous_load": [10000.0 + i * 5 for i in range(periods)],
    }).to_parquet(load_dir / "test.parquet")

    # Hourly reserves (the loader aggregates 5-min source to hourly mean).
    # Provide raw 5-min source rows; load_reserve_market_results will floor.
    reserves_dir = tmp_path / "reserve_market_results"
    reserves_dir.mkdir(parents=True)
    n_hours = max(1, periods // 12)
    rmr_rows = []
    for h in range(n_hours):
        ts = pd.Timestamp("2026-04-15") + pd.Timedelta(hours=h)
        for svc in ("SR", "PR"):
            rmr_rows.append({
                "datetime_beginning_ept": ts,
                "locale": "MAD",
                "service": svc,
                "mcp": 5.0 if svc == "SR" else 3.0,
            })
    pd.DataFrame(rmr_rows).to_parquet(reserves_dir / "test.parquet")
    return tmp_path


def test_build_joint_5min_panel_basic(tmp_path):
    data_root = _make_synthetic_data_root(tmp_path)
    panel = build_joint_5min_panel(data_root=data_root)
    assert len(panel) > 0
    # 5-min frequency check (cadence per consecutive timestamps after dedupe)
    ts = panel["datetime_beginning_ept"].drop_duplicates().sort_values()
    diffs = ts.diff().dropna()
    assert (diffs == pd.Timedelta(minutes=5)).all()
    # Required columns
    required = [
        "datetime_beginning_ept",
        "dom_load_mw",
        "dom_load_gradient_abs_mw_per_min",
        "sync_reserve_clearing_price_rt",
        "primary_reserve_clearing_price_rt",
        "in_shoulder_season",
        "in_2_5am_window",
        "passes_proposal_filter",
        # PNODE_RESPONSES targets (cluster mean derived from synthetic pnodes)
        "congestion_price_rt_cluster_mean",
        "total_lmp_rt_cluster_mean",
    ]
    for col in required:
        assert col in panel.columns, f"Missing column: {col}"
    # Filter logic spot check: 2:30 AM in April (shoulder + 2-5am) = in filter
    row = panel[panel["datetime_beginning_ept"] == pd.Timestamp("2026-04-15 02:30")]
    assert not row.empty
    assert bool(row["passes_proposal_filter"].iloc[0]) is True
    # 12 noon = NOT in filter
    row = panel[panel["datetime_beginning_ept"] == pd.Timestamp("2026-04-15 12:00")]
    assert not row.empty
    assert bool(row["passes_proposal_filter"].iloc[0]) is False


def test_build_joint_5min_panel_z_at_5min_cadence(tmp_path):
    data_root = _make_synthetic_data_root(tmp_path, periods=24)
    panel = build_joint_5min_panel(data_root=data_root)
    # Dom load: 10000 + i*5 → delta = 5 MW per 5min = 1.0 MW/min
    z = panel["dom_load_gradient_abs_mw_per_min"].dropna()
    # All non-NaN values should be 1.0
    assert z.unique().tolist() == [1.0]


def test_build_joint_5min_panel_empty_inputs_returns_empty(tmp_path):
    panel = build_joint_5min_panel(data_root=tmp_path)
    assert panel.empty
