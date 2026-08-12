# 5-Min Two-Sided Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pull a 1-year, 3-pnode, 5-minute two-sided panel (Z from gridstatus `pjm_load.dom`, nodal LMP from `pjm_lmp_real_time_5_min`), and replicate three pre-registered sub-q1 tests (QR-full, Spec A GPD, decile tail-risk curves) at 5-min resolution.

**Design:** `docs/specs/2026-07-17-5min-two-sided-companion-design.md` (commit `6492184`).

**Architecture:** New gridstatus acquisition module mirroring the PJM client (30-day UTC chunks, cursor pagination, cache-per-chunk, quota preflight); a 5-min preprocessing pipeline reusing the hourly feature functions via small parameterizations; analysis modules reused via new parameters (island-cluster bootstrap for in-filter GPD, constant overrides for tail-risk curves). Pre-reg entry committed BEFORE the pull; results entry after.

**Tech Stack:** Python 3.11+ src-layout, httpx (+ MockTransport in tests), pandas/pyarrow, statsmodels/scipy, pytest. Run all tests with `.venv/bin/python -m pytest`.

**Process:**
- Sibling worktree `../surg-gridstatus-5min/`, branch `feature/gridstatus-5min-companion`.
- Per-task commits on the feature branch (get the user's blanket per-task-commit permission once at kickoff). FF-merge and any push are each their own explicit ask. No AI attribution anywhere.
- Naming note: Z-column names are kept **identical to the hourly panel** (`dom_load_gradient_abs_mw_per_min` etc.) so analysis-module defaults work unchanged. `datetime_beginning_ept` is derived from `interval_start_utc` so `.dt.hour/.month/.year` extraction in existing modules works unchanged. `interval_start_utc` is the unique key (EPT has DST duplicates).

---

## File structure

| File | Action | Responsibility |
|---|---|---|
| `src/surg/acquisition/gridstatus_client.py` | Create | httpx client: auth, cursor pagination, 1.3 s throttle, retry, `/api_usage`, `/datasets` |
| `src/surg/acquisition/gridstatus_pull.py` | Create | Orchestrator + CLI: preflight, 30-day UTC chunks, resume, cache via existing `storage.py` |
| `src/surg/acquisition/gridstatus_validate.py` | Create | Post-pull validation gates + CLI |
| `src/surg/preprocessing/loaders_5min.py` | Create | Load cached gridstatus chunks → canonical DataFrames (rename, dedupe) |
| `src/surg/preprocessing/schema_5min.py` | Create | 5-min panel schema v1 + validator |
| `src/surg/preprocessing/build_5min.py` | Create | 5-min panel builder + CLI |
| `src/surg/analysis/run_5min.py` | Create | Analysis orchestrator + CLI (QR-full ×5, Spec A ×2, tail-risk curves) |
| `src/surg/preprocessing/features.py` | Modify | `add_load_gradient_columns(minutes_per_interval=)`, `pivot_lmp_long_to_pnode_columns(index_col=)` |
| `src/surg/preprocessing/build.py` | Modify | `write_panel(schema_version=)` |
| `src/surg/analysis/panel.py` | Modify | Generalize version check; add `load_panel_5min` |
| `src/surg/analysis/gpd.py` | Modify | `cluster_ids=` island bootstrap in `gpd_conditional_on_z`; `cluster_col=` in `run_gpd` |
| `src/surg/analysis/tail_risk_curves.py` | Modify | Parameterize `run_tail_risk_curves` (pnode map, z/filter cols) |
| `docs/decisions.md` | Modify | Pre-reg entry (Task 13, BEFORE pull); results entry (Task 16) |

Tests: one `tests/...` file per created module; existing test files extended for modified modules.

---

### Task 0: Worktree setup

- [ ] **Step 1: Create worktree + branch**

```bash
git -C /Users/turdy/docs/NU/Freshman_Year/Summer_2026/SURG/surg worktree add ../surg-gridstatus-5min -b feature/gridstatus-5min-companion
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/SURG/surg-gridstatus-5min
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]" -q 2>/dev/null || .venv/bin/pip install -e . -q
.venv/bin/python -m pytest -q 2>&1 | tail -2
```

Expected: `255 passed`. If the editable install needs dev extras and none are defined, `pip install -e . pytest pytest-asyncio` is the fallback.

---

### Task 1: GridStatusClient — query, pagination, throttle, retry

**Files:**
- Create: `src/surg/acquisition/gridstatus_client.py`
- Test: `tests/acquisition/test_gridstatus_client.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the gridstatus.io hosted-API client (mock transport, no network)."""
from __future__ import annotations

import httpx
import pytest

from surg.acquisition.gridstatus_client import GridStatusClient


def _client(handler, **kw):
    kw.setdefault("min_interval_s", 0.0)  # no throttling in tests
    return GridStatusClient(
        api_key="k", transport=httpx.MockTransport(handler), **kw
    )


def test_query_sends_api_key_and_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={"data": [], "meta": {"hasNextPage": False}})

    with _client(handler) as c:
        rows = list(c.query(
            "pjm_load",
            start_time="2025-06-24T04:00:00Z",
            end_time="2025-07-24T04:00:00Z",
            columns="interval_start_utc,interval_end_utc,dom",
        ))
    assert rows == []
    assert seen["headers"]["x-api-key"] == "k"
    assert seen["params"]["start_time"] == "2025-06-24T04:00:00Z"
    assert seen["params"]["columns"] == "interval_start_utc,interval_end_utc,dom"
    assert seen["params"]["page_size"] == "50000"


def test_query_follows_cursor_pagination():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        if "cursor" not in request.url.params:
            return httpx.Response(200, json={
                "data": [{"a": 1}, {"a": 2}],
                "meta": {"hasNextPage": True, "cursor": "C1"},
            })
        return httpx.Response(200, json={
            "data": [{"a": 3}],
            "meta": {"hasNextPage": False},
        })

    with _client(handler) as c:
        rows = list(c.query("pjm_load", start_time="s", end_time="e"))
    assert [r["a"] for r in rows] == [1, 2, 3]
    assert len(calls) == 2 and calls[1]["cursor"] == "C1"


def test_query_passes_filter_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"data": [], "meta": {"hasNextPage": False}})

    with _client(handler) as c:
        list(c.query(
            "pjm_lmp_real_time_5_min", start_time="s", end_time="e",
            filter_column="location_id", filter_value="35010365",
        ))
    assert seen["filter_column"] == "location_id"
    assert seen["filter_value"] == "35010365"
    assert seen["filter_operator"] == "="


def test_retry_on_429_then_success():
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, json={"detail": "Too Many Requests"})
        return httpx.Response(200, json={"data": [{"a": 1}], "meta": {"hasNextPage": False}})

    with _client(handler, backoff_base_s=0.0) as c:
        rows = list(c.query("pjm_load", start_time="s", end_time="e"))
    assert rows == [{"a": 1}] and attempts["n"] == 2


def test_retry_exhaustion_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with _client(handler, backoff_base_s=0.0, max_retries=2) as c:
        with pytest.raises(RuntimeError, match="after 2 retries"):
            list(c.query("pjm_load", start_time="s", end_time="e"))


def test_redirects_not_followed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(307, headers={"location": "http://api.gridstatus.io/v1/x"})

    with _client(handler, backoff_base_s=0.0, max_retries=0) as c:
        with pytest.raises(httpx.HTTPStatusError):
            list(c.query("pjm_load", start_time="s", end_time="e"))


def test_get_api_usage_returns_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/api_usage"
        return httpx.Response(200, json={
            "plan_name": "Free",
            "limits": {"api_rows_returned_limit": 500_000},
            "current_period_usage": {"total_api_rows_returned": 10},
        })

    with _client(handler) as c:
        usage = c.get_api_usage()
    assert usage["plan_name"] == "Free"


def test_get_datasets_no_trailing_slash():
    def handler(request: httpx.Request) -> httpx.Response:
        # Trailing slash triggers a cleartext 307 on the real API; assert we never send it.
        assert request.url.path == "/v1/datasets"
        return httpx.Response(200, json={"data": [{"id": "pjm_load"}]})

    with _client(handler) as c:
        ds = c.get_datasets()
    assert ds[0]["id"] == "pjm_load"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/acquisition/test_gridstatus_client.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.acquisition.gridstatus_client'`

- [ ] **Step 3: Write the implementation**

```python
"""Sync httpx wrapper for the gridstatus.io hosted API.

Mirrors `client.PJMClient` in shape. Facts encoded here come from
`docs/sources/gridstatus-api-constraints.md`:
  - auth header `x-api-key`; base https://api.gridstatus.io/v1
  - NEVER follow redirects (the /datasets/ trailing-slash 307 downgrades
    to cleartext HTTP and would replay the api key)
  - server enforces 1 req/s -> self-pace >= 1.3 s
  - cursor pagination: loop while meta.hasNextPage, pass meta.cursor back
  - retriable statuses {429, 500, 502, 503, 504}, exponential backoff
  - >= 180 s read timeout for range pulls
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx

_BASE_URL = "https://api.gridstatus.io/v1"
_RETRIABLE = {429, 500, 502, 503, 504}


class GridStatusClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _BASE_URL,
        min_interval_s: float = 1.3,
        max_retries: int = 5,
        backoff_base_s: float = 2.0,
        timeout_s: float = 180.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._min_interval_s = min_interval_s
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._last_request_ts: float = 0.0
        self._client = httpx.Client(
            headers={"x-api-key": api_key, "Accept": "application/json"},
            timeout=timeout_s,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> "GridStatusClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def query(
        self,
        dataset: str,
        *,
        start_time: str,
        end_time: str,
        columns: str | None = None,
        filter_column: str | None = None,
        filter_value: str | None = None,
        page_size: int = 50_000,
    ) -> Iterator[dict[str, Any]]:
        """Yield rows of `dataset` for [start_time, end_time), cursor-paginating."""
        url = f"{self._base_url}/datasets/{dataset}/query"
        params: dict[str, Any] = {
            "start_time": start_time,
            "end_time": end_time,
            "page_size": page_size,
        }
        if columns is not None:
            params["columns"] = columns
        if filter_column is not None:
            params["filter_column"] = filter_column
            params["filter_value"] = filter_value
            params["filter_operator"] = "="

        cursor: str | None = None
        while True:
            q = dict(params)
            if cursor is not None:
                q["cursor"] = cursor
            payload = self._get_with_retry(url, q)
            yield from payload.get("data", [])
            meta = payload.get("meta", {})
            if not meta.get("hasNextPage"):
                return
            cursor = meta.get("cursor")

    def get_api_usage(self) -> dict[str, Any]:
        return self._get_with_retry(f"{self._base_url}/api_usage", {})

    def get_datasets(self) -> list[dict[str, Any]]:
        """List all dataset metadata. ~500 rows in one call — cache the result."""
        payload = self._get_with_retry(f"{self._base_url}/datasets", {})
        return payload.get("data", payload) if isinstance(payload, dict) else payload

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_request_ts = time.time()

    def _get_with_retry(self, url: str, params: dict[str, Any]) -> Any:
        attempt = 0
        while True:
            self._throttle()
            r = self._client.get(url, params=params)
            if r.status_code in _RETRIABLE:
                if attempt >= self._max_retries:
                    raise RuntimeError(
                        f"{r.status_code} from gridstatus after {attempt} retries: "
                        f"url={url}"
                    )
                time.sleep(self._backoff_base_s * (2 ** attempt))
                self._last_request_ts = time.time()
                attempt += 1
                continue
            r.raise_for_status()
            return r.json()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/acquisition/test_gridstatus_client.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add src/surg/acquisition/gridstatus_client.py tests/acquisition/test_gridstatus_client.py
git commit -m "feat(acquisition): GridStatusClient — cursor pagination, throttle, retry, no-redirect"
```

---

### Task 2: UTC chunking helper

**Files:**
- Modify: `src/surg/acquisition/chunking.py` (append function; extend the datetime import)
- Test: `tests/acquisition/test_chunking.py` (append tests)

- [ ] **Step 1: Write the failing tests** (append to `tests/acquisition/test_chunking.py`)

```python
from datetime import datetime, timezone

import pytest

from surg.acquisition.chunking import utc_datetime_chunks


def test_utc_datetime_chunks_half_open_contiguous():
    start = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
    end = datetime(2025, 8, 24, 4, tzinfo=timezone.utc)
    chunks = list(utc_datetime_chunks(start, end, days=30))
    assert chunks[0][0] == start
    assert chunks[-1][1] == end
    for (s1, e1), (s2, e2) in zip(chunks, chunks[1:]):
        assert e1 == s2  # contiguous, non-overlapping
    for s, e in chunks:
        assert (e - s).days <= 30


def test_utc_datetime_chunks_single_short_window():
    start = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
    end = datetime(2025, 6, 25, 4, tzinfo=timezone.utc)
    assert list(utc_datetime_chunks(start, end, days=30)) == [(start, end)]


def test_utc_datetime_chunks_rejects_reversed():
    start = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        list(utc_datetime_chunks(start, start, days=30))
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/acquisition/test_chunking.py -q`
Expected: FAIL — `ImportError: cannot import name 'utc_datetime_chunks'`

- [ ] **Step 3: Implement** (append to `src/surg/acquisition/chunking.py`; change the import line to `from datetime import date, datetime, timedelta`)

```python
def utc_datetime_chunks(
    start: datetime,
    end: datetime,
    days: int = 30,
) -> Iterator[tuple[datetime, datetime]]:
    """Yield contiguous half-open [chunk_start, chunk_end) UTC windows.

    Used by the gridstatus pull: the query API takes exact datetimes, so
    unlike `date_chunks` there is no calendar-year constraint and windows
    are half-open (end exclusive) to avoid boundary-row duplication.
    """
    if end <= start:
        raise ValueError(f"end ({end}) must be > start ({start})")
    if days < 1:
        raise ValueError(f"days must be >= 1, got {days}")
    step = timedelta(days=days)
    cur = start
    while cur < end:
        nxt = min(cur + step, end)
        yield (cur, nxt)
        cur = nxt
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/acquisition/test_chunking.py -q`
Expected: all pass (existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/surg/acquisition/chunking.py tests/acquisition/test_chunking.py
git commit -m "feat(acquisition): utc_datetime_chunks for gridstatus half-open windows"
```

---

### Task 3: gridstatus_pull orchestrator + CLI

**Files:**
- Create: `src/surg/acquisition/gridstatus_pull.py`
- Test: `tests/acquisition/test_gridstatus_pull.py`

Pull targets are fixed by the design: `pjm_load` (columns `interval_start_utc,interval_end_utc,dom`) plus `pjm_lmp_real_time_5_min` per pnode (`35010365, 35010371, 1356178195`), cached as 30-day chunks via the existing `storage.write_chunk` under `data/raw/gridstatus/`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the gridstatus pull orchestrator. No network: fake client."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from surg.acquisition.gridstatus_pull import (
    FIVEMIN_PNODE_IDS,
    check_quota,
    pull_gridstatus,
)


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
            "limits": {"api_rows_returned_limit": 500_000},
            "current_period_usage": {"total_api_rows_returned": 1_000},
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
                "limits": {"api_rows_returned_limit": 500_000},
                "current_period_usage": {"total_api_rows_returned": 90_000},
            }

    with pytest.raises(RuntimeError, match="quota"):
        check_quota(LowClient({}), min_remaining_rows=430_000)


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
    assert len(lmp_files) == 3  # one per pnode
    df = pd.read_parquet(load_files[0])
    assert list(df.columns) == ["interval_start_utc", "interval_end_utc", "dom"]
    lmp_calls = [c for c in client.calls if c["dataset"] == "pjm_lmp_real_time_5_min"]
    assert {c["filter_value"] for c in lmp_calls} == {str(p) for p in FIVEMIN_PNODE_IDS}
    assert all(c["filter_column"] == "location_id" for c in lmp_calls)


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
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/acquisition/test_gridstatus_pull.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Orchestrator: pull the 5-min two-sided panel inputs from gridstatus.io.

Design: docs/specs/2026-07-17-5min-two-sided-companion-design.md
Datasets and constraints: docs/sources/gridstatus-api-constraints.md
Pull plan: docs/gridstatus-5min-pull-plan.md

Chunks are 30-day half-open UTC windows cached via storage.write_chunk:
    <data_root>/pjm_load/<year>/dom__<start>_to_<end>.parquet
    <data_root>/pjm_lmp_real_time_5_min/<year>/<pnode_id>__<start>_to_<end>.parquet
Skip-if-exists gives resumability; a partial run never re-spends quota
on chunks already on disk.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from surg.acquisition.chunking import utc_datetime_chunks
from surg.acquisition.gridstatus_client import GridStatusClient
from surg.acquisition.storage import chunk_exists, write_chunk

# Free-tier pnode set (design §2; pull plan table).
FIVEMIN_PNODE_IDS: tuple[int, ...] = (35010365, 35010371, 1356178195)

LOAD_DATASET = "pjm_load"
LMP_DATASET = "pjm_lmp_real_time_5_min"
LOAD_COLUMNS = "interval_start_utc,interval_end_utc,dom"
LMP_COLUMNS = (
    "interval_start_utc,interval_end_utc,location,location_id,"
    "location_short_name,location_type,lmp,energy,congestion,loss"
)


def check_quota(client, *, min_remaining_rows: int = 430_000) -> dict:
    """Abort (RuntimeError) if the remaining monthly row quota is too low."""
    usage = client.get_api_usage()
    limit = usage["limits"]["api_rows_returned_limit"]
    used = usage["current_period_usage"]["total_api_rows_returned"]
    remaining = limit - used
    if remaining < min_remaining_rows:
        raise RuntimeError(
            f"insufficient gridstatus row quota: {remaining:,} remaining "
            f"< {min_remaining_rows:,} required (plan={usage.get('plan_name')})"
        )
    return usage


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pull_series(
    client,
    data_root: Path,
    *,
    dataset: str,
    group_label: str,
    columns: str,
    window_start: datetime,
    window_end: datetime,
    filter_column: str | None = None,
    filter_value: str | None = None,
) -> int:
    """Pull one series in 30-day chunks; returns number of chunks fetched."""
    fetched = 0
    for cs, ce in utc_datetime_chunks(window_start, window_end, days=30):
        if chunk_exists(data_root, dataset, group_label, cs.date(), ce.date()):
            continue
        rows = list(client.query(
            dataset,
            start_time=_iso_z(cs), end_time=_iso_z(ce),
            columns=columns,
            filter_column=filter_column, filter_value=filter_value,
        ))
        df = pd.DataFrame(rows, columns=columns.split(","))
        write_chunk(data_root, dataset, group_label, cs.date(), ce.date(), df)
        fetched += 1
        print(f"  wrote {dataset}/{group_label} {cs.date()} -> {ce.date()} ({len(df):,} rows)")
    return fetched


def pull_gridstatus(
    client,
    *,
    data_root: Path,
    window_start: datetime,
    window_end: datetime,
) -> None:
    """Pull DOM 5-min load once + 5-min LMP per pnode for the window."""
    _pull_series(
        client, data_root,
        dataset=LOAD_DATASET, group_label="dom", columns=LOAD_COLUMNS,
        window_start=window_start, window_end=window_end,
    )
    for pid in FIVEMIN_PNODE_IDS:
        _pull_series(
            client, data_root,
            dataset=LMP_DATASET, group_label=str(pid), columns=LMP_COLUMNS,
            window_start=window_start, window_end=window_end,
            filter_column="location_id", filter_value=str(pid),
        )


def _parse_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"window datetimes must be timezone-aware UTC, got {s!r}")
    return dt.astimezone(timezone.utc)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-gridstatus-pull",
        description="Pull the 5-min two-sided panel inputs from gridstatus.io.",
    )
    # No defaults on the window: the pre-registered window must be passed
    # explicitly (design §2 — the pre-reg records the final window first).
    p.add_argument("--start", required=True, help="Window start, ISO-8601 UTC (e.g. 2025-06-24T04:00:00Z)")
    p.add_argument("--end", required=True, help="Window end (exclusive), ISO-8601 UTC")
    p.add_argument("--data-root", default="data/raw/gridstatus")
    p.add_argument("--skip-preflight", action="store_true",
                   help="Skip the /api_usage quota check (resume of a mostly-done pull).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    load_dotenv()
    api_key = os.environ.get("GRIDSTATUS_API_KEY")
    if not api_key:
        print("GRIDSTATUS_API_KEY is not set. Add it to .env or export it.", file=sys.stderr)
        return 2

    window_start = _parse_utc(args.start)
    window_end = _parse_utc(args.end)

    with GridStatusClient(api_key) as client:
        if not args.skip_preflight:
            usage = check_quota(client)
            used = usage["current_period_usage"]["total_api_rows_returned"]
            print(f"preflight OK: plan={usage.get('plan_name')}, rows used this period={used:,}")
        pull_gridstatus(
            client, data_root=Path(args.data_root),
            window_start=window_start, window_end=window_end,
        )
    print("pull complete")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/acquisition/test_gridstatus_pull.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/surg/acquisition/gridstatus_pull.py tests/acquisition/test_gridstatus_pull.py
git commit -m "feat(acquisition): gridstatus pull orchestrator — preflight, 30-day chunks, resume"
```

---

### Task 4: gridstatus_validate — post-pull gates

**Files:**
- Create: `src/surg/acquisition/gridstatus_validate.py`
- Test: `tests/acquisition/test_gridstatus_validate.py`

Gates (design §2): exact interval count per series; unique keys; LMP identity `energy+congestion+loss ≈ lmp` (tolerance $0.011 — one cent per component plus rounding); pnode identity by `location_id`; `dom` and LMP components ≥ 99% non-null.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for post-pull validation gates. Synthetic chunk fixtures on tmp_path."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from surg.acquisition.gridstatus_validate import validate_pull
from surg.acquisition.storage import write_chunk

WINDOW_START = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
WINDOW_END = datetime(2025, 6, 24, 5, tzinfo=timezone.utc)  # 1 hour -> 12 intervals
PNODES = (35010365, 35010371)


def _intervals():
    return pd.date_range(WINDOW_START, WINDOW_END, freq="5min",
                         inclusive="left", tz="UTC")


def _write_load(tmp_path: Path, drop_last: bool = False):
    ts = _intervals()
    if drop_last:
        ts = ts[:-1]
    df = pd.DataFrame({
        "interval_start_utc": ts.astype(str),
        "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
        "dom": 11000.0,
    })
    write_chunk(tmp_path, "pjm_load", "dom",
                WINDOW_START.date(), WINDOW_END.date(), df)


def _write_lmp(tmp_path: Path, pid: int, break_identity: bool = False):
    ts = _intervals()
    energy, congestion, loss = 24.0, 1.0, 0.1
    lmp = energy + congestion + loss + (5.0 if break_identity else 0.0)
    df = pd.DataFrame({
        "interval_start_utc": ts.astype(str),
        "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
        "location": "X", "location_id": pid,
        "location_short_name": "X", "location_type": "AGGREGATE",
        "lmp": lmp, "energy": energy, "congestion": congestion, "loss": loss,
    })
    write_chunk(tmp_path, "pjm_lmp_real_time_5_min", str(pid),
                WINDOW_START.date(), WINDOW_END.date(), df)


def test_validate_passes_on_clean_pull(tmp_path: Path):
    _write_load(tmp_path)
    for pid in PNODES:
        _write_lmp(tmp_path, pid)
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is True
    assert report["expected_intervals"] == 12
    assert all(g["passed"] for g in report["gates"].values())


def test_validate_fails_on_missing_interval(tmp_path: Path):
    _write_load(tmp_path, drop_last=True)
    for pid in PNODES:
        _write_lmp(tmp_path, pid)
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is False
    assert report["gates"]["interval_count"]["passed"] is False


def test_validate_fails_on_lmp_identity_violation(tmp_path: Path):
    _write_load(tmp_path)
    _write_lmp(tmp_path, PNODES[0], break_identity=True)
    _write_lmp(tmp_path, PNODES[1])
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is False
    assert report["gates"]["lmp_identity"]["passed"] is False


def test_validate_fails_on_unexpected_pnode(tmp_path: Path):
    _write_load(tmp_path)
    _write_lmp(tmp_path, PNODES[0])
    _write_lmp(tmp_path, 99999)  # wrong pnode on disk
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is False
    assert report["gates"]["pnode_identity"]["passed"] is False
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/acquisition/test_gridstatus_validate.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Post-pull validation gates for the gridstatus 5-min pull (design §2).

All gates must pass before the panel build; `main` exits non-zero on
any failure so the execution runbook can gate on it.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

LMP_IDENTITY_TOL = 0.011  # dollars; components are published to the cent


def _read_series(data_root: Path, dataset: str) -> pd.DataFrame:
    files = sorted((data_root / dataset).rglob("*.parquet"))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    return df


def validate_pull(
    data_root: Path,
    *,
    window_start: datetime,
    window_end: datetime,
    pnode_ids: tuple[int, ...],
) -> dict:
    """Run all gates; returns a report dict with per-gate pass/fail."""
    expected = pd.date_range(window_start, window_end, freq="5min",
                             inclusive="left", tz="UTC")
    n_expected = len(expected)

    load = _read_series(data_root, "pjm_load")
    lmp = _read_series(data_root, "pjm_lmp_real_time_5_min")

    gates: dict[str, dict] = {}

    # Gate 1: interval counts — load series and each pnode's LMP series.
    counts = {"pjm_load": int(load["interval_start_utc"].nunique()) if len(load) else 0}
    for pid in pnode_ids:
        sub = lmp[lmp["location_id"] == pid] if len(lmp) else pd.DataFrame()
        counts[f"lmp_{pid}"] = int(sub["interval_start_utc"].nunique()) if len(sub) else 0
    gates["interval_count"] = {
        "passed": all(c == n_expected for c in counts.values()),
        "detail": {**counts, "expected": n_expected},
    }

    # Gate 2: unique keys.
    load_dup = int(load.duplicated("interval_start_utc").sum()) if len(load) else 0
    lmp_dup = int(lmp.duplicated(["interval_start_utc", "location_id"]).sum()) if len(lmp) else 0
    gates["unique_keys"] = {
        "passed": load_dup == 0 and lmp_dup == 0,
        "detail": {"load_duplicates": load_dup, "lmp_duplicates": lmp_dup},
    }

    # Gate 3: LMP identity energy + congestion + loss == lmp (within tolerance).
    if len(lmp):
        resid = (lmp["energy"] + lmp["congestion"] + lmp["loss"] - lmp["lmp"]).abs()
        n_bad = int((resid > LMP_IDENTITY_TOL).sum())
        max_resid = float(resid.max())
    else:
        n_bad, max_resid = -1, float("nan")
    gates["lmp_identity"] = {
        "passed": n_bad == 0,
        "detail": {"n_violations": n_bad, "max_abs_residual": max_resid,
                   "tolerance": LMP_IDENTITY_TOL},
    }

    # Gate 4: pnode identity — exactly the requested location_ids, nothing else.
    found = set(int(x) for x in lmp["location_id"].unique()) if len(lmp) else set()
    gates["pnode_identity"] = {
        "passed": found == set(pnode_ids),
        "detail": {"found": sorted(found), "expected": sorted(pnode_ids)},
    }

    # Gate 5: nullness — dom and LMP components >= 99% non-null.
    null_fracs: dict[str, float] = {}
    if len(load):
        null_fracs["dom"] = float(load["dom"].isna().mean())
    if len(lmp):
        for col in ("lmp", "energy", "congestion", "loss"):
            null_fracs[col] = float(lmp[col].isna().mean())
    gates["nullness"] = {
        "passed": bool(null_fracs) and all(v <= 0.01 for v in null_fracs.values()),
        "detail": null_fracs,
    }

    return {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "expected_intervals": n_expected,
        "gates": gates,
        "passed": all(g["passed"] for g in gates.values()),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="surg-gridstatus-validate")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--data-root", default="data/raw/gridstatus")
    p.add_argument("--pnodes", default="35010365,35010371,1356178195")
    p.add_argument("--report-out", default="outputs/gridstatus_pull_validation.json")
    args = p.parse_args(argv)

    ws = datetime.fromisoformat(args.start.replace("Z", "+00:00")).astimezone(timezone.utc)
    we = datetime.fromisoformat(args.end.replace("Z", "+00:00")).astimezone(timezone.utc)
    pnodes = tuple(int(x) for x in args.pnodes.split(","))

    report = validate_pull(Path(args.data_root), window_start=ws, window_end=we,
                           pnode_ids=pnodes)
    out = Path(args.report_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    for name, gate in report["gates"].items():
        print(f"  [{'PASS' if gate['passed'] else 'FAIL'}] {name}: {gate['detail']}")
    if not report["passed"]:
        print("VALIDATION FAILED", file=sys.stderr)
        return 1
    print("validation passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/acquisition/test_gridstatus_validate.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add src/surg/acquisition/gridstatus_validate.py tests/acquisition/test_gridstatus_validate.py
git commit -m "feat(acquisition): gridstatus post-pull validation gates + CLI"
```

---

### Task 5: features.py parameterization

**Files:**
- Modify: `src/surg/preprocessing/features.py:22-38` (`add_load_gradient_columns`), `features.py:41-71` (`pivot_lmp_long_to_pnode_columns`)
- Test: `tests/preprocessing/test_features.py` (append; add `import pytest` if absent)

- [ ] **Step 1: Write the failing tests** (append)

```python
def test_add_load_gradient_columns_5min_interval():
    import pandas as pd
    from surg.preprocessing.features import add_load_gradient_columns

    df = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2026-03-01", periods=3, freq="5min"),
        "dom_load_mw": [10000.0, 10050.0, 10020.0],
    })
    out = add_load_gradient_columns(df, minutes_per_interval=5.0)
    # Z_t = (dom_t - dom_{t-1}) / 5 (design §3 default formula)
    assert out["dom_load_gradient_signed_mw_per_min"].iloc[1] == pytest.approx(10.0)
    assert out["dom_load_gradient_abs_mw_per_min"].iloc[2] == pytest.approx(6.0)
    # per-hr column is the rate-normalized diff: diff * (60 / 5)
    assert out["dom_load_gradient_mw_per_hr"].iloc[1] == pytest.approx(600.0)


def test_add_load_gradient_columns_default_stays_hourly():
    import pandas as pd
    from surg.preprocessing.features import add_load_gradient_columns

    df = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2026-03-01", periods=2, freq="h"),
        "dom_load_mw": [10000.0, 10060.0],
    })
    out = add_load_gradient_columns(df)
    assert out["dom_load_gradient_mw_per_hr"].iloc[1] == pytest.approx(60.0)
    assert out["dom_load_gradient_abs_mw_per_min"].iloc[1] == pytest.approx(1.0)


def test_pivot_lmp_long_supports_custom_index_col():
    import pandas as pd
    from surg.preprocessing.features import pivot_lmp_long_to_pnode_columns

    long_df = pd.DataFrame({
        "interval_start_utc": pd.to_datetime(
            ["2025-06-24T04:00:00Z", "2025-06-24T04:00:00Z"]),
        "pnode_id": [35010365, 35010371],
        "congestion_price_rt": [1.0, 2.0],
        "total_lmp_rt": [25.0, 26.0],
    })
    wide = pivot_lmp_long_to_pnode_columns(long_df, index_col="interval_start_utc")
    assert "congestion_price_rt_35010365" in wide.columns
    assert "interval_start_utc" in wide.columns
    assert len(wide) == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/preprocessing/test_features.py -q`
Expected: new tests FAIL (`TypeError: ... unexpected keyword argument`), existing tests pass.

- [ ] **Step 3: Implement** — modify the two functions in place.

`add_load_gradient_columns` becomes:

```python
def add_load_gradient_columns(
    df: pd.DataFrame,
    *,
    minutes_per_interval: float = 60.0,
) -> pd.DataFrame:
    """Add gradient columns to a DOM-load DataFrame.

    Requires `datetime_beginning_ept` (sorted, uniform cadence) and
    `dom_load_mw`. `minutes_per_interval` is the row cadence: 60 for the
    hourly panel (default, unchanged behaviour), 5 for the 5-min panel.

    Adds:
    - dom_load_gradient_mw_per_hr: diff * (60 / minutes_per_interval)
    - dom_load_gradient_signed_mw_per_min: diff / minutes_per_interval
    - dom_load_gradient_abs_mw_per_min: abs(diff) / minutes_per_interval

    First row gets NaN for each (no prior interval).
    """
    out = df.copy()
    diff = out["dom_load_mw"].diff(1)
    out["dom_load_gradient_mw_per_hr"] = diff * (60.0 / minutes_per_interval)
    out["dom_load_gradient_signed_mw_per_min"] = diff / minutes_per_interval
    out["dom_load_gradient_abs_mw_per_min"] = diff.abs() / minutes_per_interval
    return out
```

`pivot_lmp_long_to_pnode_columns`: add `index_col: str = "datetime_beginning_ept"` keyword parameter; replace the three occurrences of the literal `"datetime_beginning_ept"` inside the function body with `index_col` (the two empty-input early-returns and the `pivot_table(index=...)` call). Docstring gains one line: `index_col: timestamp column to pivot on (5-min panel passes "interval_start_utc").`

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/preprocessing/ -q`
Expected: all pass (existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/features.py tests/preprocessing/test_features.py
git commit -m "refactor(preprocessing): parameterize gradient cadence + pivot index for 5-min reuse"
```

---

### Task 6: loaders_5min

**Files:**
- Create: `src/surg/preprocessing/loaders_5min.py`
- Test: `tests/preprocessing/test_loaders_5min.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/preprocessing/test_loaders_5min.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Load cached gridstatus chunks into canonical DataFrames.

Column renames map gridstatus names onto the repo's PJM-panel
conventions (docs/sources/gridstatus-api-constraints.md, dataset table):
    lmp        -> total_lmp_rt
    energy     -> system_energy_price_rt
    congestion -> congestion_price_rt
    loss       -> marginal_loss_price_rt
    location_id -> pnode_id
Timestamps stay tz-aware UTC here; EPT derivation happens in the
panel builder. Dedupe on the unique key defends against any
inclusive-end boundary rows the API might return.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

_LMP_RENAME = {
    "location_id": "pnode_id",
    "lmp": "total_lmp_rt",
    "energy": "system_energy_price_rt",
    "congestion": "congestion_price_rt",
    "loss": "marginal_loss_price_rt",
}


def _read_all_chunks(data_root: Path, dataset: str) -> pd.DataFrame:
    files = sorted((data_root / dataset).rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no chunks found under {data_root / dataset}")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def load_gridstatus_dom_load(data_root: Path) -> pd.DataFrame:
    """Return [interval_start_utc, dom_load_mw], deduped, sorted."""
    df = _read_all_chunks(data_root, "pjm_load")
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    df = df.rename(columns={"dom": "dom_load_mw"})[["interval_start_utc", "dom_load_mw"]]
    df = df.drop_duplicates("interval_start_utc").sort_values("interval_start_utc")
    return df.reset_index(drop=True)


def load_gridstatus_lmp_long(data_root: Path) -> pd.DataFrame:
    """Return long-format LMP with panel-convention column names."""
    df = _read_all_chunks(data_root, "pjm_lmp_real_time_5_min")
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    df = df.rename(columns=_LMP_RENAME)
    df["pnode_id"] = df["pnode_id"].astype(int)
    cols = ["interval_start_utc", "pnode_id", "total_lmp_rt",
            "system_energy_price_rt", "congestion_price_rt", "marginal_loss_price_rt"]
    df = df[cols].drop_duplicates(["interval_start_utc", "pnode_id"])
    return df.sort_values(["interval_start_utc", "pnode_id"]).reset_index(drop=True)
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/preprocessing/test_loaders_5min.py -q`
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/loaders_5min.py tests/preprocessing/test_loaders_5min.py
git commit -m "feat(preprocessing): gridstatus chunk loaders with panel-convention renames"
```

---

### Task 7: schema_5min + build_5min + write_panel version param + load_panel_5min

**Files:**
- Create: `src/surg/preprocessing/schema_5min.py`, `src/surg/preprocessing/build_5min.py`
- Modify: `src/surg/preprocessing/build.py:112-121` (`write_panel`), `src/surg/analysis/panel.py`
- Test: `tests/preprocessing/test_build_5min.py`

- [ ] **Step 1: Write schema_5min** (covered by the build tests; it is constants + a 6-line validator)

```python
"""Versioned schema for the 5-min analysis panel artifact.

Separate from the hourly schema (schema.py): the two panels evolve
independently. Z-column names deliberately match the hourly panel so
analysis-module defaults (threshold_col, Z_COL) work unchanged.
"""
from __future__ import annotations

import pandas as pd

FIVEMIN_SCHEMA_VERSION = 1

FIVEMIN_PNODE_IDS: tuple[int, ...] = (35010365, 35010371, 1356178195)

EXPECTED_COLUMNS_5MIN: tuple[str, ...] = (
    # Keys & metadata
    "interval_start_utc",           # unique key (tz-aware UTC)
    "datetime_beginning_ept",       # derived; DST fall-back rows share stamps
    "in_shoulder_season",
    "in_2_5am_window",
    "passes_proposal_filter",
    "night_island_id",              # days-since-epoch of EPT date; cluster id for island bootstrap
    # Load + Z (names match hourly panel)
    "dom_load_mw",
    "dom_load_gradient_mw_per_hr",
    "dom_load_gradient_abs_mw_per_min",
    "dom_load_gradient_signed_mw_per_min",
    # Per-pnode LMP (4 components x 3 pnodes)
    "congestion_price_rt_35010365",
    "congestion_price_rt_35010371",
    "congestion_price_rt_1356178195",
    "total_lmp_rt_35010365",
    "total_lmp_rt_35010371",
    "total_lmp_rt_1356178195",
    "system_energy_price_rt_35010365",
    "system_energy_price_rt_35010371",
    "system_energy_price_rt_1356178195",
    "marginal_loss_price_rt_35010365",
    "marginal_loss_price_rt_35010371",
    "marginal_loss_price_rt_1356178195",
    # Cluster aggregates (3-pnode cluster — narrower than the hourly 6-pnode cluster)
    "congestion_price_rt_cluster_mean",
    "congestion_price_rt_cluster_max",
    "total_lmp_rt_cluster_mean",
    "system_energy_price_rt_cluster_mean",
    "marginal_loss_price_rt_cluster_mean",
)


def validate_panel_5min(df: pd.DataFrame) -> None:
    """Raise ValueError if df is missing any expected 5-min panel column."""
    missing = set(EXPECTED_COLUMNS_5MIN) - set(df.columns)
    if missing:
        raise ValueError(f"missing expected 5-min panel columns: {sorted(missing)}")
```

- [ ] **Step 2: Write the failing build tests**

```python
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
```

- [ ] **Step 3: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/preprocessing/test_build_5min.py -q`
Expected: FAIL — module not found.

- [ ] **Step 4: Implement build_5min**

```python
"""Orchestrator: build the 5-min analysis panel from gridstatus chunks.

Pipeline: gridstatus chunks -> loaders -> pivot -> cluster aggregates
-> EPT derivation -> Z (diff/5) -> filter + island columns -> clip ->
validate -> atomic write (schema-stamped parquet).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from surg.preprocessing.build import write_panel
from surg.preprocessing.features import (
    add_filter_columns,
    add_load_gradient_columns,
    add_loudoun_cluster_columns,
    pivot_lmp_long_to_pnode_columns,
)
from surg.preprocessing.loaders_5min import (
    load_gridstatus_dom_load,
    load_gridstatus_lmp_long,
)
from surg.preprocessing.schema_5min import (
    EXPECTED_COLUMNS_5MIN,
    FIVEMIN_PNODE_IDS,
    FIVEMIN_SCHEMA_VERSION,
    validate_panel_5min,
)

_EPT_TZ = "America/New_York"


def build_analysis_panel_5min(
    data_root: Path,
    *,
    window_start_utc: pd.Timestamp,
    window_end_utc: pd.Timestamp,
) -> pd.DataFrame:
    """Build the validated 5-min panel for [window_start_utc, window_end_utc)."""
    load_df = load_gridstatus_dom_load(data_root)
    lmp_long = load_gridstatus_lmp_long(data_root)

    lmp_wide = pivot_lmp_long_to_pnode_columns(lmp_long, index_col="interval_start_utc")
    lmp_wide = add_loudoun_cluster_columns(lmp_wide, FIVEMIN_PNODE_IDS)

    # Left-join from load (the spine), keyed on the unique UTC interval.
    panel = load_df.merge(lmp_wide, on="interval_start_utc", how="left")
    panel = panel.sort_values("interval_start_utc").reset_index(drop=True)

    # Z at native 5-min cadence: Z_t = (dom_t - dom_{t-1}) / 5 (design §3).
    panel = add_load_gradient_columns(panel, minutes_per_interval=5.0)

    # EPT derivation for filter/hour/month features. tz-naive like the
    # hourly panel; fall-back duplicates are tolerated because
    # interval_start_utc stays the unique key.
    ept = panel["interval_start_utc"].dt.tz_convert(_EPT_TZ).dt.tz_localize(None)
    panel["datetime_beginning_ept"] = ept

    panel = add_filter_columns(panel)

    # Island id = EPT calendar date as days-since-epoch (the 2-5 AM window
    # never crosses midnight, so one night == one date == one island).
    panel["night_island_id"] = (
        panel["datetime_beginning_ept"].dt.normalize()
        - pd.Timestamp("1970-01-01")
    ).dt.days.astype("int32")

    panel = panel[
        (panel["interval_start_utc"] >= window_start_utc)
        & (panel["interval_start_utc"] < window_end_utc)
    ].reset_index(drop=True)

    validate_panel_5min(panel)
    return panel[list(EXPECTED_COLUMNS_5MIN)]


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-prep-5min",
        description="Build the 5-min analysis panel from gridstatus chunks.",
    )
    p.add_argument("--start", required=True, help="Window start, ISO UTC")
    p.add_argument("--end", required=True, help="Window end (exclusive), ISO UTC")
    p.add_argument("--data-root", default="data/raw/gridstatus")
    p.add_argument("--output", default="data/interim/analysis_panel_5min.parquet")
    p.add_argument("--force", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    out_path = Path(args.output)
    if out_path.exists() and not args.force:
        print(f"{out_path} exists; pass --force to overwrite.", file=sys.stderr)
        return 2
    panel = build_analysis_panel_5min(
        Path(args.data_root),
        window_start_utc=pd.Timestamp(args.start),
        window_end_utc=pd.Timestamp(args.end),
    )
    write_panel(panel, out_path, schema_version=FIVEMIN_SCHEMA_VERSION)
    print(f"wrote {out_path} ({len(panel):,} rows)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 5: Modify `write_panel` in build.py** — signature and metadata line:

```python
def write_panel(panel: pd.DataFrame, out_path: Path, *, schema_version: int = SCHEMA_VERSION) -> None:
    """Atomic write via tmp file + os.replace. Stamps schema_version in parquet custom_metadata."""
```
and inside: `new_meta = {**existing_meta, b"schema_version": str(schema_version).encode()}`.

- [ ] **Step 6: Modify `analysis/panel.py`** — generalize the version check and add the 5-min loader:

```python
from surg.preprocessing.schema_5min import FIVEMIN_SCHEMA_VERSION, validate_panel_5min


def load_panel_5min(path: Path) -> pd.DataFrame:
    """Load the 5-min analysis panel from `path` and validate its schema."""
    _check_schema_version(path, expected=FIVEMIN_SCHEMA_VERSION)
    df = pd.read_parquet(path)
    validate_panel_5min(df)
    return df
```

`_check_schema_version` gains `expected: int | None = None` (None → hourly `SCHEMA_VERSION`, so `load_panel` is unchanged) and compares `file_version != str(expected)`.

- [ ] **Step 7: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/preprocessing/ tests/analysis/test_panel.py -q`
Expected: all pass (4 new + all existing).

- [ ] **Step 8: Commit**

```bash
git add src/surg/preprocessing/schema_5min.py src/surg/preprocessing/build_5min.py \
        src/surg/preprocessing/build.py src/surg/analysis/panel.py \
        tests/preprocessing/test_build_5min.py
git commit -m "feat(preprocessing): 5-min panel schema v1 + builder + versioned loader"
```

---

### Task 8: Island-cluster bootstrap in gpd.py

**Files:**
- Modify: `src/surg/analysis/gpd.py:186-304` (`gpd_conditional_on_z`), `gpd.py:790+` (`run_gpd`)
- Test: `tests/analysis/test_gpd.py` (append; extend the existing `from surg.analysis.gpd import ...` line with `gpd_conditional_on_z, run_gpd` if absent)

The in-filter Spec A test resamples **night-islands** (clusters), not rows: the proposal filter creates 3-hour islands separated by 21-hour gaps, so iid row resampling would understate CI width (design §3; old item #8 pre-reg rationale).

- [ ] **Step 1: Write the failing tests** (append to `tests/analysis/test_gpd.py`)

```python
def test_gpd_conditional_on_z_cluster_bootstrap_runs():
    rng = np.random.default_rng(7)
    n = 4000
    Y = rng.pareto(3.0, size=n) * 10.0
    Z = rng.uniform(0, 100, size=n)
    clusters = np.repeat(np.arange(100), n // 100)  # 100 islands of 40 obs
    res = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.90, n_boot=50, seed=1, cluster_ids=clusters,
    )
    lo, hi = res.shape_diff_bootstrap_ci_95
    assert np.isfinite(lo) and np.isfinite(hi) and lo < hi


def test_gpd_conditional_cluster_ids_length_mismatch_raises():
    rng = np.random.default_rng(7)
    Y = rng.pareto(3.0, size=500) * 10.0
    Z = rng.uniform(0, 100, size=500)
    with pytest.raises(ValueError, match="cluster_ids"):
        gpd_conditional_on_z(Y, Z, n_boot=30, seed=1, cluster_ids=np.arange(10))


def test_run_gpd_passes_cluster_col(tmp_path):
    rng = np.random.default_rng(7)
    n = 4000
    df = pd.DataFrame({
        "resp": rng.pareto(3.0, size=n) * 10.0,
        "dom_load_gradient_abs_mw_per_min": rng.uniform(0, 100, size=n),
        "isl": np.repeat(np.arange(100), n // 100),
    })
    out = tmp_path / "g.json"
    run_gpd(df, out, response_col="resp", pnode_label="t",
            sweep_quantiles=(0.90,), conditional_threshold_quantile=0.90,
            n_boot=50, seed=1, cluster_col="isl")
    payload = json.loads(out.read_text())
    assert payload["conditional_z"]["bootstrap_mode"] == "cluster"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/analysis/test_gpd.py -q`
Expected: new tests FAIL (`TypeError: unexpected keyword argument 'cluster_ids'`).

- [ ] **Step 3: Implement.**

In `gpd_conditional_on_z`, add parameter `cluster_ids: np.ndarray | None = None` and, after the `Y/Z` length check:

```python
    cluster_arr: np.ndarray | None = None
    if cluster_ids is not None:
        cluster_arr = np.asarray(cluster_ids)
        if len(cluster_arr) != len(Y_arr):
            raise ValueError(
                f"cluster_ids length {len(cluster_arr)} != Y length {len(Y_arr)}"
            )
```

After `Z_exc = Z_arr[exceed_mask]` add:

```python
    C_exc = cluster_arr[exceed_mask] if cluster_arr is not None else None
```

Replace the bootstrap loop's index draw with a mode-dependent draw:

```python
    unique_clusters = np.unique(C_exc) if C_exc is not None else None
    for _ in range(n_boot):
        if C_exc is None:
            idx = rng.integers(0, n_exc, size=n_exc)
        else:
            # Island-cluster bootstrap: resample islands with replacement,
            # take every exceedance row of each drawn island.
            drawn = rng.choice(unique_clusters, size=len(unique_clusters), replace=True)
            idx = np.concatenate([np.flatnonzero(C_exc == c) for c in drawn])
        Y_b = Y_exc[idx]
        Z_b = Z_exc[idx]
        # ... (rest of the loop body unchanged: recompute split, refit, append diff)
```

Extend the docstring: `When cluster_ids is given, step 6 resamples unique cluster ids with replacement (island-cluster bootstrap) instead of rows; used by the in-filter 5-min Spec A run where the proposal filter creates ~180 3-hour night-islands.`

In `run_gpd`, add parameter `cluster_col: str | None = None`; extract `cluster_ids = subset[cluster_col].to_numpy() if cluster_col is not None else None` after the dropna; pass `cluster_ids=cluster_ids` into `gpd_conditional_on_z`; add to the payload's `conditional_z` dict:

```python
            "bootstrap_mode": "cluster" if cluster_col is not None else "iid",
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/analysis/test_gpd.py -q`
Expected: all pass (existing + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "feat(analysis): island-cluster bootstrap option for conditional-Z GPD"
```

---

### Task 9: Parameterize tail_risk_curves

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py:380-441` (`run_tail_risk_curves`)
- Test: `tests/analysis/test_tail_risk_curves.py` (append)

- [ ] **Step 1: Write the failing test** (append; uses the file's existing `numpy as np` / `pandas as pd` imports)

```python
def test_run_tail_risk_curves_accepts_custom_pnode_map(tmp_path):
    rng = np.random.default_rng(3)
    n = 2000
    panel = pd.DataFrame({
        "dom_load_gradient_abs_mw_per_min": rng.uniform(0, 60, n),
        "passes_proposal_filter": True,
        "congestion_price_rt_35010365": rng.normal(2, 5, n),
        "total_lmp_rt_35010365": rng.normal(30, 15, n),
    })
    pnode_map = {"loudoun": {"congestion": "congestion_price_rt_35010365",
                             "total_lmp": "total_lmp_rt_35010365"}}
    run_tail_risk_curves(
        panel, out_root=tmp_path, thresholds=[100.0], n_boot=30, seed=1,
        pnode_to_response=pnode_map,
        cross_pnode_pnodes=("loudoun",),
        plotted_pnodes=("loudoun",),
    )
    tr = tmp_path / "tail_risk_curves"
    assert (tr / "loudoun.json").exists()
    assert (tr / "loudoun.png").exists()
    assert (tr / "cross_pnode_summary.json").exists()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/analysis/test_tail_risk_curves.py -q`
Expected: new test FAILS (`TypeError: unexpected keyword argument`).

- [ ] **Step 3: Implement.** Change `run_tail_risk_curves`'s signature to:

```python
def run_tail_risk_curves(
    panel: pd.DataFrame,
    *,
    out_root: Path,
    thresholds: list[float] | None = None,
    n_boot: int = 200,
    seed: int = 0,
    pnode_to_response: dict[str, dict[str, str]] | None = None,
    cross_pnode_pnodes: tuple[str, ...] | None = None,
    plotted_pnodes: tuple[str, ...] | None = None,
    z_col: str = Z_COL,
    filter_col: str = FILTER_COL,
) -> None:
```

At the top of the body resolve defaults:

```python
    if pnode_to_response is None:
        pnode_to_response = PNODE_TO_RESPONSE
    if cross_pnode_pnodes is None:
        cross_pnode_pnodes = CROSS_PNODE_PNODES
    if plotted_pnodes is None:
        plotted_pnodes = PER_PNODE_PLOTTED
```

Then, inside the function body only, swap module constants for the locals: `FILTER_COL` → `filter_col` (provenance strings become `f"{filter_col} == True"` in place of `FILTER_DESC`), `CROSS_PNODE_PNODES` → `cross_pnode_pnodes`, `PNODE_TO_RESPONSE[...]` → `pnode_to_response[...]`, `Z_COL` → `z_col`, `PER_PNODE_PLOTTED` → `plotted_pnodes`. `_ensure_total_lmp_columns(filtered, cross_pnode_pnodes)` keeps working — the custom map's columns already exist, and it only derives missing ones.

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/analysis/test_tail_risk_curves.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "refactor(analysis): parameterize tail_risk_curves pnode map for 5-min reuse"
```

---

### Task 10: run_5min analysis orchestrator + CLI

**Files:**
- Create: `src/surg/analysis/run_5min.py`
- Test: `tests/analysis/test_run_5min.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/analysis/test_run_5min.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""5-min companion analysis orchestrator (design §3).

Three pre-registered replications on the 5-min two-sided panel:
  1. QR-full z_slope at tau in {0.90, 0.95, 0.99} — full panel,
     5 response labels (3 per-pnode congestion, cluster congestion,
     cluster total_lmp). Same iid pair-bootstrap as the hourly prior
     (comparability); year-FE auto-skips on a 1-year panel via
     run_qr_full's existing guard.
  2. Spec A median-split GPD on cluster congestion — twice:
     full-panel (iid bootstrap; comparator to the hourly -0.18 prior)
     and in-filter (island-cluster bootstrap over ~180 night-islands).
  3. Decile tail-risk curves — in-filter (run_tail_risk_curves applies
     the filter itself), 3 pnodes + cluster.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from surg.analysis.gpd import run_gpd
from surg.analysis.panel import load_panel_5min
from surg.analysis.qr_full import run_qr_full
from surg.analysis.tail_risk_curves import run_tail_risk_curves

FIVEMIN_QR_RESPONSES: dict[str, str] = {
    "loudoun":            "congestion_price_rt_35010365",
    "pleasant_view":      "congestion_price_rt_35010371",
    "goosecre":           "congestion_price_rt_1356178195",
    "cluster":            "congestion_price_rt_cluster_mean",
    "cluster_total_lmp":  "total_lmp_rt_cluster_mean",
}

FIVEMIN_TAIL_RISK_MAP: dict[str, dict[str, str]] = {
    "loudoun": {"congestion": "congestion_price_rt_35010365",
                "total_lmp": "total_lmp_rt_35010365"},
    "pleasant_view": {"congestion": "congestion_price_rt_35010371",
                      "total_lmp": "total_lmp_rt_35010371"},
    "goosecre": {"congestion": "congestion_price_rt_1356178195",
                 "total_lmp": "total_lmp_rt_1356178195"},
    "cluster": {"congestion": "congestion_price_rt_cluster_mean",
                "total_lmp": "total_lmp_rt_cluster_mean"},
}

SPEC_A_RESPONSE = "congestion_price_rt_cluster_mean"


def run_all_5min(
    panel: pd.DataFrame,
    *,
    out_root: Path,
    n_boot: int = 200,
    seed: int = 42,
    taus: tuple[float, ...] = (0.90, 0.95, 0.99),
    qr_n_boot: int | None = None,
) -> None:
    """Run all three pre-registered 5-min replications; write JSON/PNG/CSV."""
    out_root = Path(out_root)
    qr_boot = qr_n_boot if qr_n_boot is not None else n_boot

    # 1. QR-full (full panel; run_qr_full skips year-FE on 1-year panels).
    qr_dir = out_root / "qr_full"
    for i, (label, col) in enumerate(FIVEMIN_QR_RESPONSES.items()):
        run_qr_full(
            panel, qr_dir / f"{label}.json",
            response_col=col, pnode_label=label,
            taus=taus, n_boot=qr_boot, seed=seed + 1000 * i,
        )

    # 2. Spec A — full-panel (iid) + in-filter (island cluster bootstrap).
    gpd_dir = out_root / "gpd"
    run_gpd(
        panel, gpd_dir / "cluster_full_panel.json",
        response_col=SPEC_A_RESPONSE, pnode_label="cluster_full_panel",
        sweep_quantiles=(0.90, 0.95, 0.99, 0.995),
        conditional_threshold_quantile=0.95,
        n_boot=n_boot, seed=seed + 100,
    )
    in_filter = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)]
    run_gpd(
        in_filter, gpd_dir / "cluster_in_filter.json",
        response_col=SPEC_A_RESPONSE, pnode_label="cluster_in_filter",
        sweep_quantiles=(0.90, 0.95),
        conditional_threshold_quantile=0.95,
        n_boot=n_boot, seed=seed + 200,
        cluster_col="night_island_id",
    )

    # 3. Decile tail-risk curves (module applies the proposal filter itself).
    run_tail_risk_curves(
        panel, out_root=out_root, n_boot=n_boot, seed=seed + 300,
        pnode_to_response=FIVEMIN_TAIL_RISK_MAP,
        cross_pnode_pnodes=tuple(FIVEMIN_TAIL_RISK_MAP),
        plotted_pnodes=tuple(FIVEMIN_TAIL_RISK_MAP),
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="surg-run-5min",
        description="Run the pre-registered 5-min companion analyses.",
    )
    p.add_argument("--panel", default="data/interim/analysis_panel_5min.parquet")
    p.add_argument("--out-root", default="outputs/fivemin")
    p.add_argument("--n-boot", type=int, default=1000,
                   help="Bootstrap reps for GPD + tail-risk (pre-reg: 1000).")
    p.add_argument("--qr-n-boot", type=int, default=500,
                   help="Bootstrap reps for QR-full (pre-reg: 500 — each rep refits on ~105K rows).")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    panel = load_panel_5min(Path(args.panel))
    run_all_5min(
        panel, out_root=Path(args.out_root),
        n_boot=args.n_boot, qr_n_boot=args.qr_n_boot, seed=args.seed,
    )
    print(f"5-min analysis outputs written under {args.out_root}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify pass**

Run: `.venv/bin/python -m pytest tests/analysis/test_run_5min.py -q`
Expected: `2 passed` (takes a few minutes — QR bootstrap across 5 responses even at n_boot=25).

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/run_5min.py tests/analysis/test_run_5min.py
git commit -m "feat(analysis): 5-min companion orchestrator — QR-full x5, Spec A x2, tail-risk"
```

---

### Task 11: Full suite green + merge gate

- [ ] **Step 1: Run the complete suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (255 pre-existing + ~25 new), zero failures. Fix anything broken before proceeding.

- [ ] **Step 2: ASK the user for FF-merge permission**

Present the branch summary (`git log --oneline main..HEAD`) and test count. On yes:

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/SURG/surg
git merge --ff-only feature/gridstatus-5min-companion
git worktree remove ../surg-gridstatus-5min
git branch -d feature/gridstatus-5min-companion
.venv/bin/python -m pytest -q   # confirm green on main
```

Do NOT push unless separately asked.

---

### Task 12: Window re-verification (1 metadata request)

Runs on `main`, after merge, before the pre-reg is written — the pre-reg must record the **final** window (design §2).

- [ ] **Step 1: Fetch dataset metadata (cached; costs at most 1 request)**

```bash
.venv/bin/python - <<'EOF'
import json, os
from pathlib import Path
from dotenv import load_dotenv
from surg.acquisition.gridstatus_client import GridStatusClient

load_dotenv()
cache = Path("data/raw/gridstatus/datasets_metadata.json")
if cache.exists():
    datasets = json.loads(cache.read_text())
    print("using cached metadata")
else:
    with GridStatusClient(os.environ["GRIDSTATUS_API_KEY"]) as c:
        datasets = c.get_datasets()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(datasets, indent=2))
for d in datasets:
    if d.get("id") in ("pjm_load", "pjm_lmp_real_time_5_min"):
        print(d["id"], d.get("earliest_available_time_utc"), "->", d.get("latest_available_time_utc"))
EOF
```

- [ ] **Step 2: Decide the final window**

If `latest_available_time_utc` ≥ `2026-06-24T04:00Z` for both datasets, keep the default window `2025-06-24T04:00Z → 2026-06-24T04:00Z`. Otherwise slide the 1-year window back so it ends at the latest EPT-aligned 04:00Z boundary both datasets cover. The chosen window goes verbatim into the pre-reg (Task 13) and into every later `--start/--end` argument.

---

### Task 13: Pre-registration entry in decisions.md (BEFORE pull)

**Files:**
- Modify: `docs/decisions.md` (append)

- [ ] **Step 1: Append the pre-reg entry**, substituting the final window and the run date for the `XX` placeholders in the heading/date lines:

```markdown
## 2026-07-XX — Sub-q1 5-min two-sided companion: pre-registration

**Design:** `docs/specs/2026-07-17-5min-two-sided-companion-design.md`
(commit `6492184`). This entry locks every spec BEFORE any 5-min pull
or result computation. Data limitation, disclosed once here and once in
the eventual methods/limitations section: Z is measured via gridstatus's
`pjm_load.dom` column, which is empirically identical to PJM's
Southern-Region aggregate 5-min load.

**Window (locked):** `<FINAL_START>Z -> <FINAL_END>Z` (1 year, verified
against `latest_available_time_utc` on 2026-07-XX).

**Panel:** Z = `(dom_t − dom_{t−1}) / 5` MW/min, no smoothing, native
5-min cadence. LMP = `pjm_lmp_real_time_5_min` for pnodes 35010365
(LOUDOUN), 35010371 (PLEASANT VIEW), 1356178195 (GOOSECRE); cluster =
mean over these 3 (narrower than the hourly 6-pnode cluster —
disclosed). Filter = shoulder months × 2–5 AM EPT, unchanged.

**Test 1 — QR-full z_slope** (τ = 0.90/0.95/0.99; primary read at 0.95;
responses: 3 per-pnode congestion + cluster congestion + cluster
total_lmp; iid pair-bootstrap, qr_n_boot=500, seed=42, matching the
hourly method for comparability; year-FE auto-skipped, 1-year window):
- Hourly prior: positive slope, CI excluding 0, on 5/7 response labels
  at τ=0.90/0.95.
- CONFIRMS: ≥2 of the 3 per-pnode congestion fits at τ=0.95 have
  positive z_slope with bootstrap CI excluding 0.
- CONTRADICTS: ≥2 of 3 have negative z_slope with CI excluding 0.
- UNDERPOWERED/MIXED: anything else.

**Test 2 — Spec A median-split GPD on cluster congestion**
(threshold_quantile=0.95, z_split=median, n_boot=1000, seed=42):
- (a) Full-panel, iid exceedance bootstrap — direct comparator to the
  hourly prior shape_diff = −0.180, CI [−0.371, −0.044].
  CONFIRMS the hourly rejection: shape_diff < 0 with 95% CI excluding 0.
  CONTRADICTS: shape_diff > 0 with CI excluding 0. Else UNDERPOWERED.
- (b) In-filter, island-cluster bootstrap (night-islands ≈ 180;
  above the 50-cluster floor). Same rules; secondary read.

**Test 3 — Decile tail-risk curves** (in-filter; thresholds
$100/$250/$500/$1000/$2000; n_boot=1000, seed=42): descriptive only.
Report decile monotonicity and d10/d1 exceedance ratios next to the
hourly item #6/#9 values; no confirm/contradict rule.

**Quota discipline:** preflight `GET /api_usage`; abort if remaining
monthly rows < 430,000. ~420,480 rows, ~54 requests expected.

**Revisit when:** the results entry lands (same title, "results"
suffix), or the advisor meeting (item #5, deferred to post-run)
reframes which resolution is the headline.
```

- [ ] **Step 2: ASK the user for permission to commit**, then:

```bash
git add docs/decisions.md
git commit -m "docs(decisions): pre-register 5-min two-sided companion (window, Z, 3 tests)"
```

---

### Task 14: Execute the pull + validate (network; spends quota)

Only after Task 13's pre-reg commit exists.

- [ ] **Step 1: Pull** (~50 requests, ~420K rows, ~35 min wall at 1.3 s pacing; resumable — rerun the same command if interrupted)

```bash
.venv/bin/python -m surg.acquisition.gridstatus_pull \
  --start <FINAL_START>Z --end <FINAL_END>Z
```

Expected: `preflight OK`, per-chunk `wrote ...` lines, `pull complete`. On quota abort: STOP and surface to the user (do not retry, do not shorten the window unilaterally).

- [ ] **Step 2: Validate**

```bash
.venv/bin/python -m surg.acquisition.gridstatus_validate \
  --start <FINAL_START>Z --end <FINAL_END>Z
```

Expected: 5 `[PASS]` lines + `validation passed` (exit 0). Interval-count note: a 365-day window = 105,120 intervals; the validator derives the expected count from the window, so a leap-day window is handled automatically. On any FAIL: stop, diagnose against `docs/sources/gridstatus-api-constraints.md`, surface to the user before re-spending quota.

---

### Task 15: Build panel + smoke run + production run

- [ ] **Step 1: Build the panel**

```bash
.venv/bin/python -m surg.preprocessing.build_5min \
  --start <FINAL_START>Z --end <FINAL_END>Z
```

Expected: `wrote data/interim/analysis_panel_5min.parquet (105,120 rows)`.

- [ ] **Step 2: Smoke run** (n_boot=30, ~10–20 min)

```bash
.venv/bin/python -m surg.analysis.run_5min \
  --out-root outputs/fivemin_smoke --n-boot 30 --qr-n-boot 30
```

Expected: outputs under `outputs/fivemin_smoke/{qr_full,gpd,tail_risk_curves}/`. Sanity checks: JSONs parse; in-filter n ≈ 6,500 (`n_total_panel` in `cluster_in_filter.json`); `panel[panel.passes_proposal_filter].night_island_id.nunique()` ≈ 180.

- [ ] **Step 3: Production run** (pre-reg params: n_boot=1000 / qr_n_boot=500, seed=42; hours-long — run detached)

```bash
nohup .venv/bin/python -m surg.analysis.run_5min \
  --out-root outputs/fivemin --n-boot 1000 --qr-n-boot 500 --seed 42 \
  > ~/surg-5min-production-run.log 2>&1 &
```

Monitor the log; on completion confirm all outputs exist (5 QR JSONs, 2 GPD JSONs, tail_risk_curves dir).

---

### Task 16: Results entry + regression fixtures + closeout

- [ ] **Step 1: Apply the pre-reg rules mechanically.** For each test, state the verdict (CONFIRMS / CONTRADICTS / UNDERPOWERED-MIXED) using ONLY Task 13's rules — no post-hoc reinterpretation. Post-hoc observations go in a clearly-labeled "post-hoc notes" subsection.

- [ ] **Step 2: Append the results entry to `docs/decisions.md`** titled `## 2026-07-XX — Sub-q1 5-min two-sided companion: results`, containing: per-test verdicts with headline numbers (z_slopes + CIs at τ=0.95; shape_diffs + CIs for both variants; decile summary vs hourly), the one-line dom/Southern-Region disclosure repeated, and pointers to `outputs/fivemin/`.

- [ ] **Step 3: Regression fixtures** — fixture-scale rerun + reference outputs per the repo convention (n_boot=50, seed=42, mirroring commit `07798da` for the hourly items):

```bash
.venv/bin/python -m surg.analysis.run_5min \
  --out-root tests/fixtures/fivemin_reference --n-boot 50 --qr-n-boot 50 --seed 42
```

Add `tests/analysis/test_regression_5min.py` asserting the production code path reproduces the fixture JSONs' headline numbers (z_slope, shape_diff) when rerun with the same seed/n_boot on the real panel, guarded with `@pytest.mark.skipif(not Path("data/interim/analysis_panel_5min.parquet").exists(), reason="needs real 5-min panel")` like the hourly regression fixtures.

- [ ] **Step 4: ASK permission, then commit** (results entry + fixtures + regression test).

- [ ] **Step 5: Update the roadmap + memory.** Mark the 5-min companion done in `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md` (supersedes the never-executed item #8 two-part shape; cite this plan + the results entry). Write the session-state memory file + MEMORY.md pointer. Remind the user: the advisor meeting (item #5) is now the only gate left before sub-q2 unlocks.

---

## Self-review notes

- **Spec coverage:** design §1 framing → pre-reg entry (Task 13); §2 pull mechanics/gates → Tasks 1–4, 12, 14; §3 Z formula/tests/power → Tasks 5, 7, 8, 10, 13; §4 code shape/order → file structure + task ordering (pre-reg precedes pull; code precedes both but produces no results). Starter tier, Part B, Spec B, Ashburn, year-FE: absent by design (out of scope).
- **Type consistency:** `write_chunk(data_root, feed, group_label, chunk_start, chunk_end, df)` matches `storage.py`; `run_qr_full` / `run_gpd` / `run_tail_risk_curves` signatures extended, never renamed; Z/filter column names identical to the hourly panel throughout.
- **Known judgment calls (inherited from the design session, not new):** QR-full keeps the iid pair-bootstrap at 5-min for hourly comparability — serial correlation makes its CIs, if anything, anti-conservative, and the pre-reg locks the method; the island-bootstrap Spec A variant is the serial-correlation-aware counterpart. The Spec A hourly prior (−0.18) is a full-panel result, so the full-panel variant is the primary comparator and the in-filter variant is secondary.
