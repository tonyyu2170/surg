"""Tests for the gridstatus pull orchestrator. No network: fake client."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from surg.acquisition.chunking import utc_datetime_chunks
from surg.acquisition.gridstatus_pull import (
    FIVEMIN_PNODE_IDS,
    LOAD_COLUMNS,
    check_quota,
    pull_gridstatus,
)
from surg.acquisition.storage import write_chunk


class FakeClient:
    """Duck-typed stand-in for GridStatusClient."""

    def __init__(self, rows_by_dataset):
        self.rows_by_dataset = rows_by_dataset
        self.calls = []

    def query(self, dataset, *, start_time, end_time, columns=None,
              filter_column=None, filter_value=None, page_size=50_000):
        self.calls.append({
            "dataset": dataset, "start_time": start_time, "end_time": end_time,
            "filter_column": filter_column, "filter_value": filter_value,
        })
        yield from self.rows_by_dataset.get(dataset, [])

    def get_api_usage(self):
        return {
            "plan_name": "Free",
            "limits": {"api_rows_returned_limit": 500_000, "api_requests_limit": 250},
            "current_period_usage": {"total_api_rows_returned": 1_000, "total_requests": 10},
        }


WINDOW_START = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
WINDOW_END = datetime(2025, 7, 24, 4, tzinfo=timezone.utc)  # 30 days -> 1 chunk


def _load_rows():
    return [
        {"interval_start_utc": "2025-06-24T04:00:00+00:00",
         "interval_end_utc": "2025-06-24T04:05:00+00:00", "dom": 11000.0},
    ]


def _lmp_rows():
    return [
        {"interval_start_utc": "2025-06-24T04:00:00+00:00",
         "interval_end_utc": "2025-06-24T04:05:00+00:00",
         "location": "LOUDOUN", "location_id": 35010365,
         "location_short_name": "LOUDOUN", "location_type": "AGGREGATE",
         "lmp": 25.1, "energy": 24.0, "congestion": 1.0, "loss": 0.1},
    ]


def test_check_quota_passes_when_enough_rows():
    check_quota(FakeClient({}), min_remaining_rows=430_000)  # no raise


def test_check_quota_aborts_when_low():
    class LowClient(FakeClient):
        def get_api_usage(self):
            return {
                "plan_name": "Free",
                "limits": {"api_rows_returned_limit": 500_000, "api_requests_limit": 250},
                "current_period_usage": {"total_api_rows_returned": 90_000, "total_requests": 10},
            }

    with pytest.raises(RuntimeError, match="quota"):
        check_quota(LowClient({}), min_remaining_rows=430_000)


def test_check_quota_aborts_when_requests_low():
    class LowRequestsClient(FakeClient):
        def get_api_usage(self):
            return {
                "plan_name": "Free",
                "limits": {"api_rows_returned_limit": 500_000, "api_requests_limit": 250},
                "current_period_usage": {"total_api_rows_returned": 1_000, "total_requests": 240},
            }

    with pytest.raises(RuntimeError, match="quota"):
        check_quota(LowRequestsClient({}), min_remaining_rows=430_000)


def test_pull_writes_load_and_per_pnode_lmp_chunks(tmp_path: Path):
    client = FakeClient({
        "pjm_load": _load_rows(),
        "pjm_lmp_real_time_5_min": _lmp_rows(),
    })
    pull_gridstatus(
        client, data_root=tmp_path,
        window_start=WINDOW_START, window_end=WINDOW_END,
    )
    load_files = list((tmp_path / "pjm_load").rglob("*.parquet"))
    lmp_files = list((tmp_path / "pjm_lmp_real_time_5_min").rglob("*.parquet"))
    assert len(load_files) == 1
    # 30-day window / 7-day LMP chunks -> 5 chunks per pnode (7,7,7,7,2).
    assert len(lmp_files) == 5 * len(FIVEMIN_PNODE_IDS)
    df = pd.read_parquet(load_files[0])
    assert list(df.columns) == ["interval_start_utc", "interval_end_utc", "dom"]
    lmp_calls = [c for c in client.calls if c["dataset"] == "pjm_lmp_real_time_5_min"]
    assert {c["filter_value"] for c in lmp_calls} == {str(p) for p in FIVEMIN_PNODE_IDS}
    assert all(c["filter_column"] == "location_id" for c in lmp_calls)


def test_lmp_chunks_are_narrower_than_load_chunks(tmp_path: Path):
    """The location_id-filtered LMP query hits a ~180s server-side limit at
    30-day chunk width (empirically observed 2026-07-18, docs/gridstatus-api-constraints.md);
    LMP chunks must stay narrower than the load series' 30-day chunks."""
    window_end = WINDOW_START + timedelta(days=40)
    client = FakeClient({
        "pjm_load": _load_rows(),
        "pjm_lmp_real_time_5_min": _lmp_rows(),
    })
    pull_gridstatus(client, data_root=tmp_path,
                    window_start=WINDOW_START, window_end=window_end)

    load_files = list((tmp_path / "pjm_load").rglob("*.parquet"))
    lmp_files = list((tmp_path / "pjm_lmp_real_time_5_min").rglob("*.parquet"))
    assert len(load_files) == 2  # 40 days / 30-day chunks -> 2 (30, 10)
    # 40 days / 7-day chunks -> 6 per pnode (7,7,7,7,7,5).
    assert len(lmp_files) == 6 * len(FIVEMIN_PNODE_IDS)


def test_pull_skips_existing_chunks(tmp_path: Path):
    client = FakeClient({
        "pjm_load": _load_rows(),
        "pjm_lmp_real_time_5_min": _lmp_rows(),
    })
    pull_gridstatus(client, data_root=tmp_path,
                    window_start=WINDOW_START, window_end=WINDOW_END)
    n_calls_first = len(client.calls)
    pull_gridstatus(client, data_root=tmp_path,
                    window_start=WINDOW_START, window_end=WINDOW_END)
    assert len(client.calls) == n_calls_first  # all chunks skipped on rerun


def test_pull_resumes_partial_multi_chunk_series(tmp_path: Path):
    """Chunk 1 of N already cached must not stop chunk 2+ from being fetched."""
    multi_window_end = WINDOW_START + timedelta(days=45)  # -> 2 chunks per series
    chunks = list(utc_datetime_chunks(WINDOW_START, multi_window_end, days=30))
    assert len(chunks) == 2
    (chunk1_start, chunk1_end), (chunk2_start, chunk2_end) = chunks

    # Pre-seed only the first chunk of the pjm_load series.
    seed_df = pd.DataFrame(_load_rows(), columns=LOAD_COLUMNS.split(","))
    write_chunk(tmp_path, "pjm_load", "dom",
                chunk1_start.date(), chunk1_end.date(), seed_df)

    client = FakeClient({
        "pjm_load": _load_rows(),
        "pjm_lmp_real_time_5_min": _lmp_rows(),
    })
    pull_gridstatus(client, data_root=tmp_path,
                    window_start=WINDOW_START, window_end=multi_window_end)

    load_calls = [c for c in client.calls if c["dataset"] == "pjm_load"]
    assert len(load_calls) == 1  # chunk 1 skipped, only chunk 2 queried
    assert load_calls[0]["start_time"] == chunk2_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert load_calls[0]["end_time"] == chunk2_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    load_files = sorted((tmp_path / "pjm_load").rglob("*.parquet"))
    assert len(load_files) == 2  # both the pre-seeded chunk and the fetched one exist


def test_pull_respects_custom_pnode_ids(tmp_path: Path):
    """--pnodes lets a split pull (e.g. account B) fetch only its subset."""
    client = FakeClient({
        "pjm_load": _load_rows(),
        "pjm_lmp_real_time_5_min": _lmp_rows(),
    })
    subset = FIVEMIN_PNODE_IDS[:2]
    pull_gridstatus(
        client, data_root=tmp_path,
        window_start=WINDOW_START, window_end=WINDOW_END,
        pnode_ids=subset,
    )
    lmp_files = list((tmp_path / "pjm_lmp_real_time_5_min").rglob("*.parquet"))
    assert len(lmp_files) == 5 * len(subset)
    lmp_calls = [c for c in client.calls if c["dataset"] == "pjm_lmp_real_time_5_min"]
    assert {c["filter_value"] for c in lmp_calls} == {str(p) for p in subset}


def test_pull_skip_load_omits_load_series(tmp_path: Path):
    """--skip-load lets a split pull (e.g. account B) skip the shared load series."""
    client = FakeClient({
        "pjm_load": _load_rows(),
        "pjm_lmp_real_time_5_min": _lmp_rows(),
    })
    pull_gridstatus(
        client, data_root=tmp_path,
        window_start=WINDOW_START, window_end=WINDOW_END,
        skip_load=True,
    )
    load_files = list((tmp_path / "pjm_load").rglob("*.parquet"))
    assert load_files == []
    load_calls = [c for c in client.calls if c["dataset"] == "pjm_load"]
    assert load_calls == []


def test_pull_writes_well_formed_empty_chunk(tmp_path: Path):
    """Zero rows for a chunk must still produce a 0-row parquet with the right schema."""
    client = FakeClient({
        "pjm_load": [],  # no rows returned for this window
        "pjm_lmp_real_time_5_min": _lmp_rows(),
    })
    pull_gridstatus(client, data_root=tmp_path,
                    window_start=WINDOW_START, window_end=WINDOW_END)

    load_files = list((tmp_path / "pjm_load").rglob("*.parquet"))
    assert len(load_files) == 1
    df = pd.read_parquet(load_files[0])
    assert len(df) == 0
    assert list(df.columns) == LOAD_COLUMNS.split(",")


def test_skip_lmp_pulls_load_only(tmp_path):
    """--skip-lmp must issue zero LMP requests and still pull load."""
    client = FakeClient(rows_by_dataset={"pjm_load": _load_rows()})
    pull_gridstatus(
        client,
        data_root=tmp_path,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        skip_lmp=True,
    )
    datasets = [c["dataset"] for c in client.calls]
    assert "pjm_lmp_real_time_5_min" not in datasets
    assert "pjm_load" in datasets


def test_skip_lmp_and_skip_load_together_is_rejected(tmp_path):
    """Pulling neither series is a user error, not a silent no-op."""
    client = FakeClient(rows_by_dataset={})
    with pytest.raises(ValueError, match="nothing to pull"):
        pull_gridstatus(
            client,
            data_root=tmp_path,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
            skip_lmp=True,
            skip_load=True,
        )
