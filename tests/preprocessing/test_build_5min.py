"""Tests for the 5-min panel builder. Synthetic chunks on tmp_path."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from surg.acquisition.storage import write_chunk
from surg.preprocessing.build_5min import build_analysis_panel_5min
from surg.preprocessing.schema_5min import EXPECTED_COLUMNS_5MIN, FIVEMIN_PNODE_IDS

# Two EPT nights of 5-min data in a shoulder month:
# 2026-03-02 00:00 EPT = 2026-03-02 05:00 UTC (EST).
UTC_START = pd.Timestamp("2026-03-02T05:00:00Z")
N = 288 * 2  # two days


def _seed_chunks(root: Path):
    ts = pd.date_range(UTC_START, periods=N, freq="5min", tz="UTC")
    load = pd.DataFrame({
        "interval_start_utc": ts.astype(str),
        "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
        "dom": 11000.0 + pd.Series(range(N), dtype=float),
    })
    write_chunk(root, "pjm_load", "dom", date(2026, 3, 2), date(2026, 3, 4), load)
    for pid in FIVEMIN_PNODE_IDS:
        lmp = pd.DataFrame({
            "interval_start_utc": ts.astype(str),
            "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
            "location": "X", "location_id": pid, "location_short_name": "X",
            "location_type": "AGGREGATE",
            "lmp": 25.1, "energy": 24.0, "congestion": 1.0, "loss": 0.1,
        })
        write_chunk(root, "pjm_lmp_real_time_5_min", str(pid),
                    date(2026, 3, 2), date(2026, 3, 4), lmp)


def test_build_produces_schema_complete_panel(tmp_path: Path):
    _seed_chunks(tmp_path)
    panel = build_analysis_panel_5min(
        tmp_path,
        window_start_utc=UTC_START, window_end_utc=UTC_START + pd.Timedelta(days=2),
    )
    assert set(EXPECTED_COLUMNS_5MIN) <= set(panel.columns)
    assert len(panel) == N
    assert panel["interval_start_utc"].is_unique


def test_build_z_is_diff_over_5(tmp_path: Path):
    _seed_chunks(tmp_path)
    panel = build_analysis_panel_5min(
        tmp_path,
        window_start_utc=UTC_START, window_end_utc=UTC_START + pd.Timedelta(days=2),
    )
    # dom increments by exactly 1.0 per interval in the fixture -> Z = 0.2
    assert panel["dom_load_gradient_abs_mw_per_min"].iloc[1] == pytest.approx(0.2)


def test_build_filter_and_island_columns(tmp_path: Path):
    _seed_chunks(tmp_path)
    panel = build_analysis_panel_5min(
        tmp_path,
        window_start_utc=UTC_START, window_end_utc=UTC_START + pd.Timedelta(days=2),
    )
    in_filter = panel[panel["passes_proposal_filter"]]
    # March is a shoulder month; 2-5 AM EPT x 12 intervals/hr x 3 hrs x 2 nights = 72
    assert len(in_filter) == 72
    assert in_filter["datetime_beginning_ept"].dt.hour.isin([2, 3, 4]).all()
    # Two distinct nights -> two distinct island ids
    assert in_filter["night_island_id"].nunique() == 2


def test_build_cluster_mean_over_three_pnodes(tmp_path: Path):
    _seed_chunks(tmp_path)
    panel = build_analysis_panel_5min(
        tmp_path,
        window_start_utc=UTC_START, window_end_utc=UTC_START + pd.Timedelta(days=2),
    )
    assert panel["congestion_price_rt_cluster_mean"].iloc[0] == pytest.approx(1.0)
    assert panel["total_lmp_rt_cluster_mean"].iloc[0] == pytest.approx(25.1)


def _seed_chunks_with_load_gap(root: Path):
    """Same fixture as _seed_chunks, but with one interval dropped from the
    middle of the load spine (LMP chunks stay complete)."""
    ts = pd.date_range(UTC_START, periods=N, freq="5min", tz="UTC")
    ts_load = ts.delete(N // 2)  # drop one interval -> a 10-min gap in the spine
    load = pd.DataFrame({
        "interval_start_utc": ts_load.astype(str),
        "interval_end_utc": (ts_load + pd.Timedelta(minutes=5)).astype(str),
        "dom": 11000.0 + pd.Series(range(len(ts_load)), dtype=float),
    })
    write_chunk(root, "pjm_load", "dom", date(2026, 3, 2), date(2026, 3, 4), load)
    for pid in FIVEMIN_PNODE_IDS:
        lmp = pd.DataFrame({
            "interval_start_utc": ts.astype(str),
            "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
            "location": "X", "location_id": pid, "location_short_name": "X",
            "location_type": "AGGREGATE",
            "lmp": 25.1, "energy": 24.0, "congestion": 1.0, "loss": 0.1,
        })
        write_chunk(root, "pjm_lmp_real_time_5_min", str(pid),
                    date(2026, 3, 2), date(2026, 3, 4), lmp)


def test_build_nans_gradient_at_gap_boundary(tmp_path: Path):
    """A genuine spine gap must NaN-mask the affected row's Z rather than
    raise or silently compute a wrong gradient across the missing interval."""
    _seed_chunks_with_load_gap(tmp_path)
    panel = build_analysis_panel_5min(
        tmp_path,
        window_start_utc=UTC_START, window_end_utc=UTC_START + pd.Timedelta(days=2),
    )
    assert len(panel) == N - 1  # one interval genuinely missing from the spine

    gradient_cols = [
        "dom_load_gradient_mw_per_hr",
        "dom_load_gradient_signed_mw_per_min",
        "dom_load_gradient_abs_mw_per_min",
    ]
    # The dropped interval was at original position N//2; the row now
    # immediately after the gap sits at new index N//2 (one slot shifted
    # down by the removal) and must have NaN gradients, not a wrong value.
    gap_row = panel.iloc[N // 2]
    assert gap_row[gradient_cols].isna().all()
    # Its other columns (dom_load_mw, LMP) are still populated.
    assert pd.notna(gap_row["dom_load_mw"])
    assert pd.notna(gap_row["total_lmp_rt_cluster_mean"])
    # Only the true first row and this gap row lack a valid gradient.
    assert panel[gradient_cols[0]].notna().sum() == len(panel) - 2
