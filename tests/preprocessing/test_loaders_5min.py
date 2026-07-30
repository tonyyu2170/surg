"""Tests for gridstatus chunk loaders. Synthetic chunks on tmp_path."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from surg.acquisition.storage import write_chunk
from surg.preprocessing.loaders_5min import (
    load_gridstatus_dom_load,
    load_gridstatus_lmp_long,
)


def _write_load_chunk(root: Path):
    df = pd.DataFrame({
        "interval_start_utc": ["2025-06-24T04:00:00+00:00", "2025-06-24T04:05:00+00:00",
                               "2025-06-24T04:05:00+00:00"],  # deliberate duplicate
        "interval_end_utc": ["2025-06-24T04:05:00+00:00", "2025-06-24T04:10:00+00:00",
                             "2025-06-24T04:10:00+00:00"],
        "dom": [11000.0, 11010.0, 11010.0],
    })
    write_chunk(root, "pjm_load", "dom", date(2025, 6, 24), date(2025, 7, 24), df)


def _write_lmp_chunk(root: Path, pid: int):
    df = pd.DataFrame({
        "interval_start_utc": ["2025-06-24T04:00:00+00:00"],
        "interval_end_utc": ["2025-06-24T04:05:00+00:00"],
        "location": "X", "location_id": pid, "location_short_name": "X",
        "location_type": "AGGREGATE",
        "lmp": [25.1], "energy": [24.0], "congestion": [1.0], "loss": [0.1],
    })
    write_chunk(root, "pjm_lmp_real_time_5_min", str(pid),
                date(2025, 6, 24), date(2025, 7, 24), df)


def test_load_dom_load_renames_dedupes_and_types(tmp_path: Path):
    _write_load_chunk(tmp_path)
    df = load_gridstatus_dom_load(tmp_path)
    assert list(df.columns) == ["interval_start_utc", "dom_load_mw"]
    assert len(df) == 2  # duplicate dropped
    assert str(df["interval_start_utc"].dtype) == "datetime64[ns, UTC]"
    assert df["interval_start_utc"].is_monotonic_increasing


def test_load_lmp_long_renames_to_panel_conventions(tmp_path: Path):
    _write_lmp_chunk(tmp_path, 35010365)
    _write_lmp_chunk(tmp_path, 35010371)
    df = load_gridstatus_lmp_long(tmp_path)
    assert set(df.columns) == {
        "interval_start_utc", "pnode_id", "total_lmp_rt",
        "system_energy_price_rt", "congestion_price_rt", "marginal_loss_price_rt",
    }
    assert set(df["pnode_id"].unique()) == {35010365, 35010371}
