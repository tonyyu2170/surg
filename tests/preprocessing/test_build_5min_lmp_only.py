"""Tests for src/surg/preprocessing/build_5min_lmp_only.py — sub-q1 item #8 Part B."""
from pathlib import Path
import pandas as pd
import pytest

from surg.preprocessing.build_5min_lmp_only import build_lmp_only_5min_panel


def _make_lmp_only_data_root(tmp_path: Path) -> Path:
    lmp_dir = tmp_path / "rt_fivemin_hrl_lmps" / "2026"
    lmp_dir.mkdir(parents=True)
    rows = []
    for pid in (35010371, 35010365, 1356178195):
        rows.append(pd.DataFrame({
            "datetime_beginning_ept": pd.date_range(
                "2026-04-15", periods=12, freq="5min"
            ),
            "pnode_id": [pid] * 12,
            "pnode_name": [f"P{pid}"] * 12,
            "voltage": [500] * 12,
            "type": ["EHV"] * 12,
            "zone": ["DOM"] * 12,
            "system_energy_price_rt": list(range(12)),
            "total_lmp_rt": [25.0 + i for i in range(12)],
            "congestion_price_rt": [0.0] * 12,
            "marginal_loss_price_rt": [1.0] * 12,
        }))
    pd.concat(rows, ignore_index=True).to_parquet(lmp_dir / "test.parquet")
    return tmp_path


def test_build_lmp_only_5min_panel_keeps_all_pnodes(tmp_path):
    data_root = _make_lmp_only_data_root(tmp_path)
    panel = build_lmp_only_5min_panel(data_root=data_root)
    assert len(panel) == 12 * 3  # 12 stamps × 3 pnodes
    assert panel["pnode_id"].nunique() == 3
    assert "total_lmp_rt" in panel.columns
    assert "datetime_beginning_ept" in panel.columns


def test_build_lmp_only_5min_panel_no_filter_columns(tmp_path):
    """Part B is descriptive — no filter columns added."""
    data_root = _make_lmp_only_data_root(tmp_path)
    panel = build_lmp_only_5min_panel(data_root=data_root)
    for c in ("passes_proposal_filter", "in_2_5am_window", "in_shoulder_season"):
        assert c not in panel.columns


def test_build_lmp_only_5min_panel_5min_cadence_per_pnode(tmp_path):
    data_root = _make_lmp_only_data_root(tmp_path)
    panel = build_lmp_only_5min_panel(data_root=data_root)
    one = panel[panel["pnode_id"] == 35010371].sort_values("datetime_beginning_ept")
    diffs = one["datetime_beginning_ept"].diff().dropna()
    assert (diffs == pd.Timedelta(minutes=5)).all()


def test_build_lmp_only_5min_panel_empty_dir_returns_empty(tmp_path):
    panel = build_lmp_only_5min_panel(data_root=tmp_path)
    assert panel.empty
