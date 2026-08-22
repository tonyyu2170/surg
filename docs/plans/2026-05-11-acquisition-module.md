# PJM Acquisition Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Project commit policy (overrides default skill behavior):** This project's `CLAUDE.md` requires explicit user permission for every commit/push. **Do NOT auto-commit between tasks.** Commit suggestions are noted at end-of-plan; ask the user before running them.

**Goal:** Build a reusable, idempotent CLI-driven acquisition module for PJM Data Miner 2 that pulls feed data into `data/raw/` for the locked 11-pnode target set, respecting the 6/min rate limit, archive cutoffs, and 366-day range cap.

**Architecture:** Sync httpx client with built-in throttling and 429 backoff; pure-function date/pnode chunkers; filesystem-based skip via deterministic parquet paths; thin CLI entrypoint. Hardcoded pnode constants in `targets.py` (per `decisions.md` 2026-05-10 §5).

**Tech Stack:** Python 3.11+, httpx 0.27+, pandas, pyarrow, pytest. Mock httpx with `httpx.MockTransport` — no real API calls in the test suite.

---

## File Structure

```
src/surg/acquisition/
├── __init__.py            # public re-exports
├── targets.py             # 11-pnode constants + helpers
├── chunking.py            # date_chunks, pnode_batches (pure functions)
├── storage.py             # parquet path layout, exists/write helpers
├── client.py              # PJMClient: httpx wrapper with throttle, retry, gzip
└── pull.py                # pull_feed orchestrator + CLI

tests/acquisition/
├── __init__.py
├── test_targets.py        # the 11 pnodes are present, tier helpers work
├── test_chunking.py       # date split + pnode batching, edge cases
├── test_storage.py        # path generation, skip-if-exists, write
├── test_client.py         # throttle, pagination, 429 retry, gzip — all mocked
└── test_pull.py           # orchestrator wires the pieces correctly — mocked
```

**Responsibility split:** `chunking.py` and `targets.py` are pure functions / data; `storage.py` only touches the filesystem; `client.py` only touches the network; `pull.py` is the orchestrator that composes them. This isolation lets each be tested in isolation with cheap fakes.

---

## Task 1: Package skeleton + targets.py

**Files:**
- Modify: `src/surg/acquisition/__init__.py`
- Create: `src/surg/acquisition/targets.py`
- Create: `tests/acquisition/__init__.py`
- Create: `tests/acquisition/test_targets.py`

- [ ] **Step 1.1: Write the failing tests**

Create `tests/acquisition/__init__.py` as an empty file, then write `tests/acquisition/test_targets.py`:

```python
from surg.acquisition.targets import (
    Pnode,
    PNODES,
    all_pnode_ids,
    pnodes_by_tier,
)


def test_eleven_pnodes_locked():
    assert len(PNODES) == 11
    ids = {p.pnode_id for p in PNODES}
    assert len(ids) == 11, "pnode IDs must be unique"


def test_specific_pnodes_present():
    by_id = {p.pnode_id: p for p in PNODES}
    assert by_id[35010365].name == "LOUDOUN"
    assert by_id[34964545].name == "DOM"
    assert by_id[34886139].name == "ASHBURN 35 KV TX1"


def test_tiers_partition():
    tiers = {p.tier for p in PNODES}
    assert tiers == {
        "primary_transmission",
        "primary_distribution",
        "control",
        "zonal",
    }
    counts = {t: len(pnodes_by_tier(t)) for t in tiers}
    assert counts == {
        "primary_transmission": 6,
        "primary_distribution": 2,
        "control": 2,
        "zonal": 1,
    }


def test_all_pnode_ids_returns_int_list():
    ids = all_pnode_ids()
    assert isinstance(ids, list)
    assert len(ids) == 11
    assert all(isinstance(i, int) for i in ids)


def test_pnode_is_hashable_and_frozen():
    p = PNODES[0]
    {p}  # hashable
    try:
        p.pnode_id = 999
        raised = False
    except Exception:
        raised = True
    assert raised, "Pnode should be frozen"
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `cd "~/docs/NU/Freshman_Year/Summer 2026/SURG/surg" && .venv/bin/pytest tests/acquisition/test_targets.py -v`
Expected: collection error (module doesn't exist) or ImportError.

- [ ] **Step 1.3: Implement `src/surg/acquisition/targets.py`**

```python
"""Locked target pnode set for the SURG analysis.

See `docs/decisions.md` 2026-05-10 §5 for the rationale behind
this set. Identifying by pnode_id is required (the LMP feed
truncates pnode_name; see `docs/sources/pjm-api-constraints.md`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal[
    "primary_transmission",
    "primary_distribution",
    "control",
    "zonal",
]


@dataclass(frozen=True, slots=True)
class Pnode:
    pnode_id: int
    name: str
    tier: Tier


PNODES: tuple[Pnode, ...] = (
    # Primary nodal — Loudoun-area transmission cluster (500 KV AGGREGATE/EHV)
    Pnode(35010365,   "LOUDOUN",            "primary_transmission"),
    Pnode(35010371,   "PLEASANT VIEW",      "primary_transmission"),
    Pnode(1356178195, "GOOSECRE",           "primary_transmission"),
    Pnode(1356178171, "BRAMBLET",           "primary_transmission"),
    Pnode(1356178181, "MOSBY",              "primary_transmission"),
    Pnode(1356178201, "SKFFSCRK",           "primary_transmission"),
    # Primary nodal — Ashburn distribution (35 KV BUS/LOAD)
    Pnode(34886139,   "ASHBURN 35 KV TX1",  "primary_distribution"),
    Pnode(34886141,   "ASHBURN 35 KV TX2",  "primary_distribution"),
    # Control / outside the Loudoun cluster
    Pnode(35010369,   "OX",                 "control"),
    Pnode(62871513,   "BRISTERS",           "control"),
    # DOM zonal baseline
    Pnode(34964545,   "DOM",                "zonal"),
)


def all_pnode_ids() -> list[int]:
    return [p.pnode_id for p in PNODES]


def pnodes_by_tier(tier: Tier) -> list[Pnode]:
    return [p for p in PNODES if p.tier == tier]
```

- [ ] **Step 1.4: Update `src/surg/acquisition/__init__.py`**

```python
from surg.acquisition.targets import (
    PNODES,
    Pnode,
    all_pnode_ids,
    pnodes_by_tier,
)

__all__ = ["PNODES", "Pnode", "all_pnode_ids", "pnodes_by_tier"]
```

- [ ] **Step 1.5: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/acquisition/test_targets.py -v`
Expected: 5 passed.

---

## Task 2: chunking.py — date_chunks + pnode_batches

**Files:**
- Create: `src/surg/acquisition/chunking.py`
- Create: `tests/acquisition/test_chunking.py`

- [ ] **Step 2.1: Write the failing tests**

Create `tests/acquisition/test_chunking.py`:

```python
from datetime import date

import pytest

from surg.acquisition.chunking import date_chunks, pnode_batches


# ---------- date_chunks ----------

def test_single_chunk_within_calendar_year():
    chunks = list(date_chunks(date(2024, 3, 1), date(2024, 6, 30)))
    assert chunks == [(date(2024, 3, 1), date(2024, 6, 30))]


def test_splits_at_calendar_year_boundary():
    chunks = list(date_chunks(date(2024, 12, 1), date(2025, 2, 28)))
    assert chunks == [
        (date(2024, 12, 1),  date(2024, 12, 31)),
        (date(2025, 1, 1),   date(2025, 2, 28)),
    ]


def test_full_year_is_one_chunk():
    chunks = list(date_chunks(date(2024, 1, 1), date(2024, 12, 31)))
    assert chunks == [(date(2024, 1, 1), date(2024, 12, 31))]


def test_multi_year_splits_per_calendar_year():
    chunks = list(date_chunks(date(2022, 1, 1), date(2024, 12, 31)))
    assert chunks == [
        (date(2022, 1, 1), date(2022, 12, 31)),
        (date(2023, 1, 1), date(2023, 12, 31)),
        (date(2024, 1, 1), date(2024, 12, 31)),
    ]


def test_max_days_subdivides_within_year():
    # max_days=30: a 100-day window in one calendar year splits into 4
    chunks = list(date_chunks(date(2024, 1, 1), date(2024, 4, 10), max_days=30))
    # 30 + 30 + 30 + 11 = 101 days
    assert len(chunks) == 4
    assert chunks[0] == (date(2024, 1, 1),  date(2024, 1, 30))
    assert chunks[-1][1] == date(2024, 4, 10)
    # No chunk exceeds 30 days inclusive
    for s, e in chunks:
        assert (e - s).days + 1 <= 30


def test_single_day():
    chunks = list(date_chunks(date(2024, 5, 15), date(2024, 5, 15)))
    assert chunks == [(date(2024, 5, 15), date(2024, 5, 15))]


def test_end_before_start_raises():
    with pytest.raises(ValueError):
        list(date_chunks(date(2024, 5, 2), date(2024, 5, 1)))


# ---------- pnode_batches ----------

def test_pnode_batches_simple():
    assert list(pnode_batches([1, 2, 3, 4, 5], batch_size=2)) == [[1, 2], [3, 4], [5]]


def test_pnode_batches_exact_fit():
    assert list(pnode_batches([1, 2, 3, 4], batch_size=2)) == [[1, 2], [3, 4]]


def test_pnode_batches_single_batch_when_under_size():
    assert list(pnode_batches([1, 2, 3], batch_size=50)) == [[1, 2, 3]]


def test_pnode_batches_empty_input():
    assert list(pnode_batches([], batch_size=10)) == []


def test_pnode_batches_invalid_size():
    with pytest.raises(ValueError):
        list(pnode_batches([1, 2, 3], batch_size=0))
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/acquisition/test_chunking.py -v`
Expected: collection / import error.

- [ ] **Step 2.3: Implement `src/surg/acquisition/chunking.py`**

```python
"""Pure-function helpers for splitting work into API-compatible chunks.

Two constraints from PJM Data Miner 2 (see `docs/sources/pjm-api-constraints.md`):
  - A single date-filtered query may not span more than 366 days.
  - For archived feeds, a query must stay within a single calendar year.

`date_chunks` enforces both: chunks are always within one calendar year
and never longer than `max_days`.

`pnode_batches` packs pnode IDs for semicolon-joined `pnode_id=A;B;C`
queries — the major efficiency under the 6/min rate limit.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import date, timedelta


def date_chunks(
    start: date,
    end: date,
    max_days: int = 365,
) -> Iterator[tuple[date, date]]:
    """Yield (chunk_start, chunk_end) inclusive windows.

    Windows never cross a calendar year boundary and never exceed
    `max_days` days inclusive.
    """
    if end < start:
        raise ValueError(f"end ({end}) must be >= start ({start})")
    if max_days < 1:
        raise ValueError(f"max_days must be >= 1, got {max_days}")

    cur = start
    while cur <= end:
        year_end = date(cur.year, 12, 31)
        max_end = cur + timedelta(days=max_days - 1)
        chunk_end = min(year_end, max_end, end)
        yield (cur, chunk_end)
        cur = chunk_end + timedelta(days=1)


def pnode_batches(
    pnode_ids: Sequence[int],
    batch_size: int = 50,
) -> Iterator[list[int]]:
    """Yield successive batches of pnode IDs of length up to `batch_size`."""
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")
    for i in range(0, len(pnode_ids), batch_size):
        yield list(pnode_ids[i : i + batch_size])
```

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/acquisition/test_chunking.py -v`
Expected: 12 passed.

---

## Task 3: storage.py — parquet path layout + skip helpers

**Files:**
- Create: `src/surg/acquisition/storage.py`
- Create: `tests/acquisition/test_storage.py`

- [ ] **Step 3.1: Write the failing tests**

Create `tests/acquisition/test_storage.py`:

```python
from datetime import date
from pathlib import Path

import pandas as pd

from surg.acquisition.storage import (
    chunk_exists,
    chunk_path,
    write_chunk,
)


def test_chunk_path_layout(tmp_path: Path):
    p = chunk_path(
        data_root=tmp_path,
        feed="rt_hrl_lmps",
        group_label="dom_targets",
        chunk_start=date(2026, 4, 1),
        chunk_end=date(2026, 4, 30),
    )
    assert p == tmp_path / "rt_hrl_lmps" / "2026" / "dom_targets__2026-04-01_to_2026-04-30.parquet"


def test_chunk_path_uses_chunk_start_year(tmp_path: Path):
    # Chunks never cross calendar years (per chunking.py invariant), so the
    # year in the path is the chunk_start year.
    p = chunk_path(tmp_path, "rt_hrl_lmps", "dom", date(2024, 12, 31), date(2024, 12, 31))
    assert "2024" in p.parts


def test_chunk_exists_false_then_true(tmp_path: Path):
    args = dict(
        data_root=tmp_path,
        feed="rt_hrl_lmps",
        group_label="dom",
        chunk_start=date(2026, 4, 15),
        chunk_end=date(2026, 4, 15),
    )
    assert chunk_exists(**args) is False

    df = pd.DataFrame({"a": [1, 2, 3]})
    written = write_chunk(df=df, **args)
    assert written.exists()
    assert chunk_exists(**args) is True


def test_write_chunk_creates_parent_dirs(tmp_path: Path):
    df = pd.DataFrame({"x": [1.0]})
    out = write_chunk(
        data_root=tmp_path,
        feed="hrl_load_metered",
        group_label="dom",
        chunk_start=date(2024, 1, 1),
        chunk_end=date(2024, 12, 31),
        df=df,
    )
    assert out.parent.is_dir()
    # Round-trip the data
    loaded = pd.read_parquet(out)
    assert list(loaded["x"]) == [1.0]


def test_write_chunk_overwrites_existing(tmp_path: Path):
    args = dict(
        data_root=tmp_path,
        feed="rt_hrl_lmps",
        group_label="dom",
        chunk_start=date(2026, 1, 1),
        chunk_end=date(2026, 1, 1),
    )
    write_chunk(df=pd.DataFrame({"v": [1]}), **args)
    write_chunk(df=pd.DataFrame({"v": [2]}), **args)
    loaded = pd.read_parquet(chunk_path(**args))
    assert list(loaded["v"]) == [2]
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/acquisition/test_storage.py -v`
Expected: collection / import error.

- [ ] **Step 3.3: Implement `src/surg/acquisition/storage.py`**

```python
"""Filesystem layout for raw acquisition output.

Layout:
    <data_root>/<feed>/<year>/<group_label>__<start>_to_<end>.parquet

Skip-if-exists is the resumability mechanism. A chunk that has been
written is treated as complete; pass `force=True` to the orchestrator
to override.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd


def chunk_path(
    data_root: Path,
    feed: str,
    group_label: str,
    chunk_start: date,
    chunk_end: date,
) -> Path:
    """Return the deterministic path for a chunk's parquet file."""
    fname = f"{group_label}__{chunk_start.isoformat()}_to_{chunk_end.isoformat()}.parquet"
    return data_root / feed / str(chunk_start.year) / fname


def chunk_exists(
    data_root: Path,
    feed: str,
    group_label: str,
    chunk_start: date,
    chunk_end: date,
) -> bool:
    return chunk_path(data_root, feed, group_label, chunk_start, chunk_end).exists()


def write_chunk(
    data_root: Path,
    feed: str,
    group_label: str,
    chunk_start: date,
    chunk_end: date,
    df: pd.DataFrame,
) -> Path:
    """Write `df` to the chunk's path, creating parent dirs. Overwrites."""
    out = chunk_path(data_root, feed, group_label, chunk_start, chunk_end)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return out
```

- [ ] **Step 3.4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/acquisition/test_storage.py -v`
Expected: 5 passed.

---

## Task 4: PJMClient — throttle + paginated GET

Mocked entirely with `httpx.MockTransport`. No real API in the suite.

**Files:**
- Create: `src/surg/acquisition/client.py`
- Create: `tests/acquisition/test_client.py`

- [ ] **Step 4.1: Write the failing tests**

Create `tests/acquisition/test_client.py`:

```python
import time

import httpx
import pytest

from surg.acquisition.client import PJMClient


def _mock_transport(handler):
    """Wrap a handler function as an httpx.MockTransport."""
    return httpx.MockTransport(handler)


def test_auth_header_attached():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"items": [], "totalRows": 0})

    client = PJMClient(api_key="test-key-123", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("pnode", {"zone": "DOM"}))

    assert captured["headers"].get("ocp-apim-subscription-key") == "test-key-123"
    assert rows == []


def test_paginates_until_total_rows_reached():
    calls = {"n": 0, "starts": []}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        params = dict(request.url.params)
        start = int(params["startRow"])
        rc = int(params["rowCount"])
        calls["starts"].append(start)
        # Simulate 5 total rows; the loop should request startRow=1,3,5
        # with page_size=2 → batches of [2,2,1]
        all_rows = [{"i": i} for i in range(1, 6)]
        page = all_rows[start - 1 : start - 1 + rc]
        return httpx.Response(200, json={"items": page, "totalRows": 5})

    client = PJMClient(api_key="k", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("rt_hrl_lmps", {"foo": "bar"}, page_size=2))

    assert calls["n"] == 3
    assert calls["starts"] == [1, 3, 5]
    assert rows == [{"i": 1}, {"i": 2}, {"i": 3}, {"i": 4}, {"i": 5}]


def test_throttle_sleeps_between_requests(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [{"i": 1}], "totalRows": 1})

    client = PJMClient(api_key="k", min_interval_s=11.0,
                       transport=_mock_transport(handler))
    list(client.get_feed("pnode", {}))
    list(client.get_feed("pnode", {}))

    # First call: no sleep. Second: should sleep ~11s (less the tiny elapsed).
    assert len(sleeps) == 1
    assert 9.5 <= sleeps[0] <= 11.5


def test_max_rows_caps_pagination():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        # API claims 1000 rows total, but max_rows=3 should stop us early
        return httpx.Response(200, json={
            "items": [{"i": calls["n"]}],
            "totalRows": 1000,
        })

    client = PJMClient(api_key="k", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("pnode", {}, page_size=1, max_rows=3))

    assert calls["n"] == 3
    assert rows == [{"i": 1}, {"i": 2}, {"i": 3}]


def test_429_retries_with_backoff(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] <= 2:
            return httpx.Response(429, json={"error": "rate-limited"})
        return httpx.Response(200, json={"items": [{"ok": True}], "totalRows": 1})

    client = PJMClient(api_key="k", min_interval_s=0.0, max_retries=3,
                       backoff_base_s=2.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("pnode", {}))

    assert state["n"] == 3
    assert rows == [{"ok": True}]
    # Two backoff sleeps: 2.0, 4.0 (exponential)
    assert sleeps == [2.0, 4.0]


def test_429_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    client = PJMClient(api_key="k", min_interval_s=0.0, max_retries=2,
                       transport=_mock_transport(handler))
    with pytest.raises(RuntimeError, match="429"):
        list(client.get_feed("pnode", {}))


def test_4xx_other_than_429_raises(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"errors": [{"message": "bad params"}]})

    client = PJMClient(api_key="k", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        list(client.get_feed("pnode", {}))


def test_context_manager_closes_underlying_client():
    closed = {"v": False}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "totalRows": 0})

    with PJMClient(api_key="k", min_interval_s=0.0,
                   transport=_mock_transport(handler)) as client:
        list(client.get_feed("pnode", {}))
        # Confirm we have an httpx.Client; close it via context exit
    # No assertion on closed state needed — httpx.Client.is_closed is the truth
    assert client._client.is_closed
```

- [ ] **Step 4.2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/acquisition/test_client.py -v`
Expected: collection / import error.

- [ ] **Step 4.3: Implement `src/surg/acquisition/client.py`**

```python
"""Sync httpx wrapper for PJM Data Miner 2.

Encapsulates: subscription-key auth, JSON envelope unwrapping
(`items` + `totalRows`), pagination, the 6/min rate limit, and
exponential backoff on 429.

`download=true` / gzip handling is intentionally NOT used here for
pulls < ~50K rows — the JSON envelope is more readable for
debugging. A future helper can wrap `download=true` if/when we
ever need it for >50K-row pages.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx


_BASE_URL = "https://api.pjm.com/api/v1"


class PJMClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _BASE_URL,
        min_interval_s: float = 11.0,
        max_retries: int = 3,
        backoff_base_s: float = 2.0,
        timeout_s: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._min_interval_s = min_interval_s
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._last_request_ts: float = 0.0
        self._client = httpx.Client(
            headers={
                "Ocp-Apim-Subscription-Key": api_key,
                "Accept": "application/json",
            },
            timeout=timeout_s,
            transport=transport,
        )

    def __enter__(self) -> "PJMClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_feed(
        self,
        feed: str,
        params: dict[str, Any],
        *,
        page_size: int = 50_000,
        max_rows: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield rows for `feed` filtered by `params`, paginating as needed."""
        start = 1
        emitted = 0
        total: int | None = None
        url = f"{self._base_url}/{feed}"

        while True:
            q = {**params, "startRow": start, "rowCount": page_size}
            payload = self._get_with_retry(url, q)
            batch = payload.get("items", [])
            if total is None:
                total = payload.get("totalRows", len(batch))

            for row in batch:
                if max_rows is not None and emitted >= max_rows:
                    return
                yield row
                emitted += 1

            if not batch:
                return
            if max_rows is not None and emitted >= max_rows:
                return
            if emitted >= total:
                return
            start += len(batch)

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_request_ts = time.time()

    def _get_with_retry(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        attempt = 0
        while True:
            self._throttle()
            r = self._client.get(url, params=params)
            if r.status_code == 429:
                if attempt >= self._max_retries:
                    raise RuntimeError(
                        f"429 from PJM after {attempt} retries: "
                        f"url={url} headers={dict(r.headers)}"
                    )
                wait = self._backoff_base_s * (2 ** attempt)
                time.sleep(wait)
                attempt += 1
                continue
            r.raise_for_status()
            return r.json()
```

- [ ] **Step 4.4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/acquisition/test_client.py -v`
Expected: 8 passed.

---

## Task 5: pull_feed orchestrator

Composes client + chunking + storage. Mocked end-to-end.

**Files:**
- Create: `src/surg/acquisition/pull.py` (orchestrator only — CLI added in Task 6)
- Create: `tests/acquisition/test_pull.py`

- [ ] **Step 5.1: Write the failing tests**

Create `tests/acquisition/test_pull.py`:

```python
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from surg.acquisition.pull import pull_feed


def _mock_client(rows_per_call: list[list[dict]]):
    """Return a mock client whose get_feed yields the next list each call."""
    mc = MagicMock()
    queue = list(rows_per_call)

    def _get_feed(*args, **kwargs):
        return iter(queue.pop(0))

    mc.get_feed.side_effect = _get_feed
    return mc, queue


def test_writes_one_chunk_per_calendar_year(tmp_path: Path):
    rows_per_call = [
        [{"datetime_beginning_ept": "2024-12-15", "v": 1}],
        [{"datetime_beginning_ept": "2025-01-15", "v": 2}],
    ]
    client, _ = _mock_client(rows_per_call)

    written = pull_feed(
        feed="rt_hrl_lmps",
        start=date(2024, 12, 1),
        end=date(2025, 1, 31),
        pnode_ids=[35010365],
        group_label="dom_targets",
        client=client,
        data_root=tmp_path,
    )

    assert client.get_feed.call_count == 2
    assert len(written) == 2
    assert (tmp_path / "rt_hrl_lmps" / "2024").is_dir()
    assert (tmp_path / "rt_hrl_lmps" / "2025").is_dir()


def test_skips_existing_chunks_by_default(tmp_path: Path):
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    # Pre-create the chunk file
    feed_dir = tmp_path / "rt_hrl_lmps" / "2026"
    feed_dir.mkdir(parents=True)
    pd.DataFrame({"v": [99]}).to_parquet(
        feed_dir / "dom__2026-04-15_to_2026-04-15.parquet"
    )

    written = pull_feed(
        feed="rt_hrl_lmps",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=[35010365],
        group_label="dom",
        client=client,
        data_root=tmp_path,
    )

    assert client.get_feed.call_count == 0
    assert written == []


def test_force_overrides_skip(tmp_path: Path):
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    feed_dir = tmp_path / "rt_hrl_lmps" / "2026"
    feed_dir.mkdir(parents=True)
    pd.DataFrame({"v": [99]}).to_parquet(
        feed_dir / "dom__2026-04-15_to_2026-04-15.parquet"
    )

    pull_feed(
        feed="rt_hrl_lmps",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=[35010365],
        group_label="dom",
        client=client,
        data_root=tmp_path,
        force=True,
    )

    assert client.get_feed.call_count == 1
    # Overwritten with the new value
    df = pd.read_parquet(feed_dir / "dom__2026-04-15_to_2026-04-15.parquet")
    assert list(df["v"]) == [1]


def test_passes_correct_params_to_client(tmp_path: Path):
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    pull_feed(
        feed="rt_hrl_lmps",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=[35010365, 1356178195],
        group_label="dom",
        client=client,
        data_root=tmp_path,
    )

    args, kwargs = client.get_feed.call_args
    assert args[0] == "rt_hrl_lmps"
    params = args[1]
    # Date filter is the inclusive range with the API's required ` to ` separator
    assert "2026-04-15 00:00 to 2026-04-15 23:59" in params["datetime_beginning_ept"]
    # Multiple pnodes are semicolon-packed
    assert params["pnode_id"] == "35010365;1356178195"
    # row_is_current=true for LMP feeds
    assert params.get("row_is_current") == "true"
    # Sort by date ascending
    assert params.get("sort") == "datetime_beginning_ept"
    assert params.get("order") == "Asc"


def test_zonal_feed_omits_pnode_id(tmp_path: Path):
    """For hrl_load_metered we filter by zone instead of pnode_id."""
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    pull_feed(
        feed="hrl_load_metered",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=None,  # signal: not a nodal pull
        zone="DOM",
        group_label="dom",
        client=client,
        data_root=tmp_path,
    )

    args, _ = client.get_feed.call_args
    params = args[1]
    assert "pnode_id" not in params
    assert params["zone"] == "DOM"
    assert params.get("row_is_current") is None  # not an LMP feed


def test_empty_chunk_still_writes_an_empty_parquet(tmp_path: Path):
    """A chunk that returns zero rows is treated as 'pulled' so we don't re-pull."""
    rows_per_call = [[]]
    client, _ = _mock_client(rows_per_call)

    written = pull_feed(
        feed="rt_hrl_lmps",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=[35010365],
        group_label="dom",
        client=client,
        data_root=tmp_path,
    )

    assert len(written) == 1
    df = pd.read_parquet(written[0])
    assert df.empty
```

- [ ] **Step 5.2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/acquisition/test_pull.py -v`
Expected: collection / import error.

- [ ] **Step 5.3: Implement `src/surg/acquisition/pull.py`**

```python
"""Orchestrator: pull a feed for a date range, writing per-chunk parquet files.

Composes `client.PJMClient` + `chunking.date_chunks` + `storage.*`.
Two feed shapes are supported:
  - Nodal LMP feeds (rt_hrl_lmps, rt_fivemin_hrl_lmps, da_hrl_lmps):
    pass `pnode_ids` (semicolon-packed). `row_is_current=true` is forced.
  - Zonal feeds (hrl_load_metered): pass `zone="DOM"` instead.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from surg.acquisition.chunking import date_chunks
from surg.acquisition.client import PJMClient
from surg.acquisition.storage import chunk_exists, write_chunk

# Feeds that follow LMP versioning semantics.
_LMP_FEEDS = frozenset(
    {"rt_hrl_lmps", "rt_fivemin_hrl_lmps", "da_hrl_lmps"}
)


def pull_feed(
    feed: str,
    start: date,
    end: date,
    *,
    pnode_ids: Sequence[int] | None,
    group_label: str,
    client: PJMClient,
    data_root: Path,
    zone: str | None = None,
    force: bool = False,
    max_days_per_chunk: int = 365,
) -> list[Path]:
    """Pull `feed` for [start, end] in calendar-year chunks.

    Returns the list of parquet paths written this run (skipped chunks
    are excluded from the return value).
    """
    written: list[Path] = []

    for chunk_start, chunk_end in date_chunks(start, end, max_days=max_days_per_chunk):
        if not force and chunk_exists(data_root, feed, group_label, chunk_start, chunk_end):
            continue

        params = _build_params(feed, chunk_start, chunk_end, pnode_ids, zone)
        rows = list(client.get_feed(feed, params))
        df = pd.DataFrame(rows)
        path = write_chunk(
            data_root=data_root,
            feed=feed,
            group_label=group_label,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            df=df,
        )
        written.append(path)

    return written


def _build_params(
    feed: str,
    chunk_start: date,
    chunk_end: date,
    pnode_ids: Sequence[int] | None,
    zone: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "datetime_beginning_ept": (
            f"{chunk_start.isoformat()} 00:00 to "
            f"{chunk_end.isoformat()} 23:59"
        ),
        "sort": "datetime_beginning_ept",
        "order": "Asc",
    }
    if pnode_ids:
        params["pnode_id"] = ";".join(str(p) for p in pnode_ids)
    if zone:
        params["zone"] = zone
    if feed in _LMP_FEEDS:
        params["row_is_current"] = "true"
    return params
```

- [ ] **Step 5.4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/acquisition/test_pull.py -v`
Expected: 6 passed.

- [ ] **Step 5.5: Update `__init__.py` to re-export the orchestrator**

Replace `src/surg/acquisition/__init__.py` with:

```python
from surg.acquisition.client import PJMClient
from surg.acquisition.pull import pull_feed
from surg.acquisition.targets import (
    PNODES,
    Pnode,
    all_pnode_ids,
    pnodes_by_tier,
)

__all__ = [
    "PJMClient",
    "PNODES",
    "Pnode",
    "all_pnode_ids",
    "pnodes_by_tier",
    "pull_feed",
]
```

---

## Task 6: CLI entrypoint

**Files:**
- Modify: `src/surg/acquisition/pull.py` — add `main()` and arg parsing
- Modify: `pyproject.toml` — register `[project.scripts]` entry point

- [ ] **Step 6.1: Add CLI to `pull.py`**

Append to `src/surg/acquisition/pull.py`:

```python
import argparse
import os
import sys
from datetime import date

from dotenv import load_dotenv

from surg.acquisition.targets import all_pnode_ids


def _parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-pull",
        description="Pull a PJM Data Miner 2 feed for a date range to data/raw/.",
    )
    p.add_argument("--feed", required=True,
                   choices=sorted(_LMP_FEEDS | {"hrl_load_metered"}),
                   help="API feed name.")
    p.add_argument("--start", required=True, type=_parse_iso_date,
                   help="Inclusive start date (YYYY-MM-DD).")
    p.add_argument("--end",   required=True, type=_parse_iso_date,
                   help="Inclusive end date (YYYY-MM-DD).")
    p.add_argument("--group-label", default="dom_targets",
                   help="Slug used in output filenames.")
    p.add_argument("--data-root", default="data/raw",
                   help="Root directory under which feed/year subdirs are created.")
    p.add_argument("--zone", default=None,
                   help="For zonal feeds (e.g. hrl_load_metered). Mutually "
                        "exclusive with the implicit pnode set.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing chunk files.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    load_dotenv()
    api_key = os.environ.get("PJM_API_KEY")
    if not api_key:
        print("PJM_API_KEY is not set. Add it to .env or export it.", file=sys.stderr)
        return 2

    pnode_ids = None if args.zone else all_pnode_ids()

    with PJMClient(api_key=api_key) as client:
        paths = pull_feed(
            feed=args.feed,
            start=args.start,
            end=args.end,
            pnode_ids=pnode_ids,
            zone=args.zone,
            group_label=args.group_label,
            client=client,
            data_root=Path(args.data_root),
            force=args.force,
        )

    if not paths:
        print("No chunks pulled (all already exist; use --force to overwrite).")
    else:
        for p in paths:
            print(f"wrote {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 6.2: Register the entry point in `pyproject.toml`**

Add under `[project]` (after `dependencies = [...]` block):

```toml
[project.scripts]
surg-pull = "surg.acquisition.pull:main"
```

- [ ] **Step 6.3: Reinstall the package to register the entry point**

Run: `.venv/bin/pip install -e .`
Expected: `Successfully installed surg-0.1.0`.

- [ ] **Step 6.4: Test the CLI parses correctly without making API calls**

Run: `.venv/bin/surg-pull --help`
Expected: usage text printed, exit 0.

Run: `unset PJM_API_KEY && .venv/bin/surg-pull --feed rt_hrl_lmps --start 2026-04-15 --end 2026-04-15`
Expected: error message about missing key, exit code 2. (Note: this only works in a shell that doesn't have PJM_API_KEY set; if .env is loaded, you'll get a real run instead — guard with explicit `env -i` if needed.)

---

## Task 7: End-to-end smoke against the real API

The first call against the real API. Pulls one day of hourly LMP for the 11 pnodes — same shape as the spike's comparison cell, but via the new module. Confirms the whole stack works.

**Manual step — no test file.**

- [ ] **Step 7.1: Pull one day of hourly nodal LMP for the 11 pnodes**

Run from project root:
```
.venv/bin/surg-pull --feed rt_hrl_lmps --start 2026-04-15 --end 2026-04-15 --group-label dom_targets
```
Expected: ~12s wall time (one API call after throttle delay), output line ending in `wrote data/raw/rt_hrl_lmps/2026/dom_targets__2026-04-15_to_2026-04-15.parquet`.

- [ ] **Step 7.2: Verify the file matches the spike comparison output**

Run:
```
.venv/bin/python -c "
import pandas as pd
new = pd.read_parquet('data/raw/rt_hrl_lmps/2026/dom_targets__2026-04-15_to_2026-04-15.parquet')
old = pd.read_parquet('data/raw/compare__2026-04-15__multi_pnode_hourly.parquet')
print('new rows:', len(new), 'unique pnodes:', new['pnode_id'].nunique())
print('old rows:', len(old), 'unique pnodes:', old['pnode_id'].nunique())
assert len(new) == len(old) == 264
assert set(new['pnode_id']) == set(old['pnode_id'])
print('match: OK')
"
```
Expected: `new rows: 264 unique pnodes: 11`, `old rows: 264 unique pnodes: 11`, `match: OK`.

- [ ] **Step 7.3: Re-run the same command to verify skip-if-exists**

Run: `.venv/bin/surg-pull --feed rt_hrl_lmps --start 2026-04-15 --end 2026-04-15 --group-label dom_targets`
Expected: `No chunks pulled (all already exist; use --force to overwrite).` Wall time <1s (no API call).

---

## Task 8: Update project documentation

**Files:**
- Modify: `CLAUDE.md` — note the new acquisition CLI
- Modify: `docs/decisions.md` — append a brief decision entry recording the CLI choice

- [ ] **Step 8.1: Add CLI usage to `CLAUDE.md`**

Add a new section after "Tech stack":

```markdown
## Data acquisition

All raw PJM pulls go through `surg-pull`, the CLI registered by
`src/surg/acquisition/pull.py`. Examples:

```
# Hourly nodal LMP, 11-pnode target set, one calendar year
surg-pull --feed rt_hrl_lmps --start 2024-01-01 --end 2024-12-31

# 5-min nodal LMP, Standard window only (last ~6 months from today)
surg-pull --feed rt_fivemin_hrl_lmps --start 2025-11-15 --end 2026-05-10

# DOM zonal hourly load
surg-pull --feed hrl_load_metered --zone DOM --start 2024-01-01 --end 2024-12-31 --group-label dom_load
```

Output goes to `data/raw/<feed>/<year>/<group_label>__<start>_to_<end>.parquet`.
Re-running skips chunks that already exist (`--force` to overwrite).
```

- [ ] **Step 8.2: Append a short decision entry**

Append to `docs/decisions.md`:

```markdown
---

## 2026-05-11 — Acquisition module: sync httpx, filesystem-skip, hardcoded pnode constants

**Context.** Spike (`notebooks/01_data_miner_spike.ipynb`) validated the
end-to-end API shape. Before bulk pulls we need a reusable, idempotent
acquisition layer that respects the 6/min rate limit, archive cutoffs,
366-day range cap, and PJM's quirks (envelope keys, pnode_name truncation).

**Decision.** Three architectural choices:
1. **Sync httpx (not async).** The 6/min rate limit makes us bound by
   wall time, not concurrency. A single API key cannot benefit from
   async multiplexing.
2. **Filesystem-based skip-if-exists** (not a SQLite ledger). Each
   chunk's parquet path is deterministic; presence on disk = pulled.
   `--force` overrides for re-pulls.
3. **Pnode IDs as a Python module constant** (`surg.acquisition.targets.PNODES`),
   not config. They are locked in `decisions.md` and treating them
   as code-level constants matches their stability.

**Rationale.** Each picks the simpler option in its trade-off, given a
single-developer research project with locked targets and a hard rate
ceiling that limits parallelism's value.

**Revisit when.** If we ever obtain a higher-rate API key, async
becomes worth it. If we add multi-target pulls (different pnode
sets per call), targets should move to config.
```

---

## Task 9: Run the full test suite

- [ ] **Step 9.1: Run all acquisition tests**

Run: `.venv/bin/pytest tests/acquisition -v`
Expected: 36 passed (5 + 12 + 5 + 8 + 6).

- [ ] **Step 9.2: Run the project test suite end-to-end**

Run: `.venv/bin/pytest -v`
Expected: 36 passed, 0 failed.

---

## End-of-plan commit suggestions

(**Reminder:** Per `CLAUDE.md`, do NOT run these without explicit user permission.)

Two logical commits, suggested:

1. **Acquisition module (code + tests)**
   ```
   feat(acquisition): add PJM Data Miner 2 acquisition module

   - Sync httpx client with 6/min throttle and 429 backoff
   - Pure-function date_chunks (calendar-year-aware) and pnode_batches
   - Filesystem-based parquet layout with skip-if-exists
   - 11-pnode target set as module constant
   - surg-pull CLI entrypoint
   - 36 tests, mocked httpx, no real API calls in suite
   ```

2. **Docs update**
   ```
   docs: record acquisition module architecture and CLI usage
   ```
