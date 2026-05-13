from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest


def _write_lmp_chunk(data_root: Path, year: int, fname: str, rows: list[dict]) -> Path:
    """Helper: write a synthetic rt_hrl_lmps chunk."""
    chunk_dir = data_root / "rt_hrl_lmps" / str(year)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    out = chunk_dir / fname
    pd.DataFrame(rows).to_parquet(out, index=False)
    return out


def test_load_rt_hrl_lmps_concatenates_chunks(tmp_path: Path):
    from surg.preprocessing.loaders import load_rt_hrl_lmps

    _write_lmp_chunk(tmp_path, 2024, "dom_targets__2024-01-01_to_2024-12-31.parquet", [
        {"datetime_beginning_ept": "2024-12-31T20:00:00",
         "pnode_id": 35010365, "pnode_name": "LOUDOUN",
         "congestion_price_rt": 10.0, "total_lmp_rt": 50.0},
        {"datetime_beginning_ept": "2024-12-31T20:00:00",
         "pnode_id": 35010371, "pnode_name": "PLEASANT VIEW",
         "congestion_price_rt": 12.0, "total_lmp_rt": 52.0},
    ])
    _write_lmp_chunk(tmp_path, 2025, "dom_targets__2025-01-01_to_2025-12-31.parquet", [
        {"datetime_beginning_ept": "2025-01-01T00:00:00",
         "pnode_id": 35010365, "pnode_name": "LOUDOUN",
         "congestion_price_rt": 15.0, "total_lmp_rt": 55.0},
    ])

    df = load_rt_hrl_lmps(tmp_path)

    assert len(df) == 3
    assert "datetime_beginning_ept" in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["datetime_beginning_ept"])
    assert df["pnode_id"].dtype.kind in "iu"  # integer
    # Sorted by datetime
    assert df["datetime_beginning_ept"].is_monotonic_increasing


def test_load_rt_hrl_lmps_empty_dir_returns_empty_df(tmp_path: Path):
    from surg.preprocessing.loaders import load_rt_hrl_lmps
    df = load_rt_hrl_lmps(tmp_path)
    assert df.empty
    # But still has the expected columns
    assert "datetime_beginning_ept" in df.columns
    assert "pnode_id" in df.columns


def _write_load_chunk(data_root: Path, year: int, fname: str, rows: list[dict]) -> Path:
    chunk_dir = data_root / "hrl_load_metered" / str(year)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    out = chunk_dir / fname
    pd.DataFrame(rows).to_parquet(out, index=False)
    return out


def test_load_dom_load_returns_one_row_per_hour(tmp_path: Path):
    from surg.preprocessing.loaders import load_dom_load

    _write_load_chunk(tmp_path, 2024, "dom__2024-01-01_to_2024-12-31.parquet", [
        {"datetime_beginning_ept": "2024-12-31T20:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 12500.5, "is_verified": True},
        {"datetime_beginning_ept": "2024-12-31T21:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 12600.0, "is_verified": True},
    ])

    df = load_dom_load(tmp_path)

    assert len(df) == 2
    assert list(df.columns) == ["datetime_beginning_ept", "dom_load_mw"]
    assert pd.api.types.is_datetime64_any_dtype(df["datetime_beginning_ept"])
    assert df["dom_load_mw"].iloc[0] == 12500.5
    assert df["datetime_beginning_ept"].is_monotonic_increasing


def test_load_dom_load_rejects_rows_not_in_dom_zone(tmp_path: Path):
    """Defensive: even if a chunk has stray non-DOM rows, drop them."""
    from surg.preprocessing.loaders import load_dom_load

    _write_load_chunk(tmp_path, 2024, "test__chunk.parquet", [
        {"datetime_beginning_ept": "2024-01-01T00:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 12000.0, "is_verified": True},
        {"datetime_beginning_ept": "2024-01-01T00:00:00", "zone": "PEPCO",
         "load_area": "PEPCO", "mw": 5000.0, "is_verified": True},
    ])

    df = load_dom_load(tmp_path)
    assert len(df) == 1
    assert df["dom_load_mw"].iloc[0] == 12000.0
