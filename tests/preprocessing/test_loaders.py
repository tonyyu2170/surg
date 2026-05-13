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


def _write_event_chunk(data_root: Path, year: int, fname: str, rows: list[dict]) -> Path:
    chunk_dir = data_root / "sync_reserve_events" / str(year)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    out = chunk_dir / fname
    pd.DataFrame(rows).to_parquet(out, index=False)
    return out


def test_load_sync_reserve_events_parses_timestamps(tmp_path: Path):
    from surg.preprocessing.loaders import load_sync_reserve_events

    _write_event_chunk(tmp_path, 2024, "mad__2024-05-26_to_2024-12-31.parquet", [
        {"event_start_ept": "2024-07-15T18:30:00",
         "event_end_ept":   "2024-07-15T19:15:00",
         "duration": "45 mins", "synchronized_reserve_zone": "MAD",
         "synchronized_sub_zone": "MidAtlantic-Dominion (MAD)"},
        {"event_start_ept": "2024-08-22T16:00:00",
         "event_end_ept":   "2024-08-22T16:30:00",
         "duration": "30 mins", "synchronized_reserve_zone": "MAD",
         "synchronized_sub_zone": "MidAtlantic-Dominion (MAD)"},
    ])

    df = load_sync_reserve_events(tmp_path)
    assert len(df) == 2
    assert pd.api.types.is_datetime64_any_dtype(df["event_start_ept"])
    assert pd.api.types.is_datetime64_any_dtype(df["event_end_ept"])
    assert df["event_start_ept"].is_monotonic_increasing
    # event_id is added: zero-indexed sort order
    assert list(df["event_id"]) == [0, 1]


def test_load_sync_reserve_events_empty_returns_typed_empty(tmp_path: Path):
    from surg.preprocessing.loaders import load_sync_reserve_events
    df = load_sync_reserve_events(tmp_path)
    assert df.empty
    assert "event_start_ept" in df.columns
    assert "event_end_ept" in df.columns
    assert "event_id" in df.columns


def _write_rmr_chunk(data_root: Path, year: int, fname: str, rows: list[dict]) -> Path:
    chunk_dir = data_root / "reserve_market_results" / str(year)
    chunk_dir.mkdir(parents=True, exist_ok=True)
    out = chunk_dir / fname
    pd.DataFrame(rows).to_parquet(out, index=False)
    return out


def test_load_reserve_market_aggregates_5min_to_hourly_mean(tmp_path: Path):
    from surg.preprocessing.loaders import load_reserve_market_results

    # Synthesize one hour of 5-min SR + PR data (12 intervals each)
    rows = []
    for service, base in [("SR", 100.0), ("PR", 30.0)]:
        for i in range(12):
            rows.append({
                "datetime_beginning_ept": f"2024-07-15T18:{i*5:02d}:00",
                "locale": "MAD", "service": service,
                "mcp": base + i,  # 100,101,...,111 for SR; 30,31,...,41 for PR
            })
    _write_rmr_chunk(tmp_path, 2024, "mad__2024-05-26_to_2024-12-31.parquet", rows)

    df = load_reserve_market_results(tmp_path)
    # One row per hour with both columns
    assert len(df) == 1
    assert df["datetime_beginning_ept"].iloc[0] == pd.Timestamp("2024-07-15 18:00:00")
    # SR mean = (100+...+111)/12 = 105.5
    assert df["sync_reserve_clearing_price_rt"].iloc[0] == 105.5
    # PR mean = (30+...+41)/12 = 35.5
    assert df["primary_reserve_clearing_price_rt"].iloc[0] == 35.5


def test_load_reserve_market_ignores_other_services_and_locales(tmp_path: Path):
    from surg.preprocessing.loaders import load_reserve_market_results
    _write_rmr_chunk(tmp_path, 2024, "mad__test.parquet", [
        # MAD/SR (kept)
        {"datetime_beginning_ept": "2024-07-15T18:00:00",
         "locale": "MAD", "service": "SR", "mcp": 50.0},
        # MAD/REG (dropped — not SR or PR)
        {"datetime_beginning_ept": "2024-07-15T18:00:00",
         "locale": "MAD", "service": "REG", "mcp": 9999.0},
        # PJM_RTO/SR (dropped — not MAD)
        {"datetime_beginning_ept": "2024-07-15T18:00:00",
         "locale": "PJM_RTO", "service": "SR", "mcp": 8888.0},
    ])

    df = load_reserve_market_results(tmp_path)
    assert len(df) == 1
    assert df["sync_reserve_clearing_price_rt"].iloc[0] == 50.0
    # PR row didn't exist → NaN
    assert pd.isna(df["primary_reserve_clearing_price_rt"].iloc[0])


def test_load_reserve_market_empty_returns_typed_empty(tmp_path: Path):
    from surg.preprocessing.loaders import load_reserve_market_results
    df = load_reserve_market_results(tmp_path)
    assert df.empty
    expected = {"datetime_beginning_ept",
                "sync_reserve_clearing_price_rt",
                "primary_reserve_clearing_price_rt"}
    assert expected.issubset(set(df.columns))
