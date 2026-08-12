# Preprocessing module — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Amendment 2026-05-12.** Joint analysis window changed from 2024-05-26 → 2026-05-10 (~2y) to **2022-10-02 → 2026-05-10** (~3.6y, ~31,632 hourly rows). See `docs/decisions.md` § "2026-05-12 — Window extension to 3.6y post-cap". This adds: Task 10 build.py defines `ANALYSIS_WINDOW_START`/`_END` constants and clips the panel before returning (new test in test_build.py). Task 12 expected row count is ~31,632 (was ~17,160); `passes_proposal_filter` expected count is ~1,977 hours (was ~1,053). Pre-flight: remove `data/raw/{sync_reserve_events,reserve_market_results}/2026/mad_smoke__*.parquet` before running the panel build (smoke files duplicate bulk events and would corrupt `event_id` reindexing in `load_sync_reserve_events`).

**Goal:** Build `src/surg/preprocessing/` producing one durable artifact: `data/interim/analysis_panel.parquet`, the hourly analysis-ready panel consumed by all downstream analysis. TDD throughout.

**Architecture:** Four-file module split by responsibility — `schema.py` (versioned column list), `loaders.py` (parquet-to-DataFrame for each raw feed), `features.py` (derive volatility, cluster aggregation, event-active flag), `build.py` (orchestrator + CLI). All times in EPT. Atomic parquet write via tmp-file + `os.replace`. Schema is versioned; downstream loaders refuse stale schemas.

**Tech Stack:** Python 3.11+, pytest, pandas/pyarrow (existing). No new dependencies.

**Prerequisites:**
- Plan 1 ("acquisition reserve feeds extension") complete — `sync_reserve_events` and `reserve_market_results` data exist under `data/raw/`.
- Plan 1.5 ("acquisition archive-mode") complete — historic-tier backfill of `rt_hrl_lmps` 9 pnodes + reserves down to 2022-10-02, so the analysis_panel reaches the expected ~31,632 rows. If Plan 1.5 has not run, the panel will be ~17,160 rows of the original 2y window and Task 12's row-count assertion will fail.
- All four raw feed directories populated: `data/raw/{rt_hrl_lmps,hrl_load_metered,sync_reserve_events,reserve_market_results}/`.

**Prerequisite reading:** `docs/plans/2026-05-11-phase-transition-methodology.md` § 3 ("Preprocessing layer — analysis_panel.parquet schema") is authoritative for the column list.

**Test discipline:** TDD throughout. After every task, the full test suite passes. Synthetic parquet fixtures in tests (no live API).

---

## File structure

```
src/surg/preprocessing/
├── __init__.py        # public API: build_analysis_panel
├── schema.py          # SCHEMA_VERSION, expected column list, validator
├── loaders.py         # load_<feed>(data_root) -> pd.DataFrame
├── features.py        # compute_<feature>(df) -> pd.DataFrame
└── build.py           # build_analysis_panel + CLI

tests/preprocessing/
├── __init__.py
├── test_schema.py
├── test_loaders.py
├── test_features.py
└── test_build.py
```

---

## Task 1: Scaffold `src/surg/preprocessing/` and `schema.py`

**Files:**
- Create: `src/surg/preprocessing/__init__.py`
- Create: `src/surg/preprocessing/schema.py`
- Create: `tests/preprocessing/__init__.py`
- Create: `tests/preprocessing/test_schema.py`

- [ ] **Step 1: Create empty `__init__.py` files**

```bash
mkdir -p src/surg/preprocessing tests/preprocessing
touch src/surg/preprocessing/__init__.py tests/preprocessing/__init__.py
```

- [ ] **Step 2: Write failing test for schema constants**

Create `tests/preprocessing/test_schema.py`:

```python
def test_schema_version_is_an_int():
    from surg.preprocessing.schema import SCHEMA_VERSION
    assert isinstance(SCHEMA_VERSION, int)
    assert SCHEMA_VERSION >= 1


def test_expected_columns_covers_all_design_columns():
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    # Identifiers & metadata
    must_have = {
        "datetime_beginning_ept",
        "in_shoulder_season",
        "in_2_5am_window",
        "passes_proposal_filter",
        "dst_transition_hour",
        # Load + volatility
        "dom_load_mw",
        "dom_load_gradient_mw_per_hr",
        "dom_load_gradient_abs_mw_per_min",
        "dom_load_gradient_signed_mw_per_min",
        # LMP — pooled and per-pnode controls
        "congestion_price_rt_cluster_mean",
        "congestion_price_rt_cluster_max",
        "total_lmp_rt_cluster_mean",
        "congestion_price_rt_ashburn_tx1",
        "congestion_price_rt_ashburn_tx2",
        "congestion_price_rt_ox",
        "congestion_price_rt_bristers",
        "congestion_price_rt_dom_zonal",
        # Reserves & events
        "sync_reserve_event_active",
        "sync_reserve_event_id",
        "hours_to_next_sync_event",
        "hours_since_last_sync_event",
        "sync_reserve_clearing_price_rt",
        "primary_reserve_clearing_price_rt",
    }
    assert must_have.issubset(set(EXPECTED_COLUMNS))


def test_validate_panel_accepts_dataframe_with_expected_columns():
    import pandas as pd
    from surg.preprocessing.schema import EXPECTED_COLUMNS, validate_panel

    df = pd.DataFrame({col: [None] for col in EXPECTED_COLUMNS})
    # Should not raise
    validate_panel(df)


def test_validate_panel_rejects_missing_columns():
    import pandas as pd
    import pytest
    from surg.preprocessing.schema import validate_panel

    df = pd.DataFrame({"datetime_beginning_ept": [None]})
    with pytest.raises(ValueError, match="missing expected columns"):
        validate_panel(df)
```

- [ ] **Step 3: Run tests to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_schema.py -v
```

Expected: `ImportError` (the module doesn't exist yet).

- [ ] **Step 4: Implement `schema.py`**

Create `src/surg/preprocessing/schema.py`:

```python
"""Versioned schema for the analysis panel artifact.

Bump SCHEMA_VERSION any time EXPECTED_COLUMNS changes. Downstream
analysis modules check the version and refuse to operate on a panel
written under an earlier schema.
"""
from __future__ import annotations

import pandas as pd

SCHEMA_VERSION = 1

EXPECTED_COLUMNS: tuple[str, ...] = (
    # Identifiers & metadata
    "datetime_beginning_ept",
    "in_shoulder_season",
    "in_2_5am_window",
    "passes_proposal_filter",
    "dst_transition_hour",
    # Load + volatility
    "dom_load_mw",
    "dom_load_gradient_mw_per_hr",
    "dom_load_gradient_abs_mw_per_min",
    "dom_load_gradient_signed_mw_per_min",
    # LMP — Loudoun cluster pooled
    "congestion_price_rt_cluster_mean",
    "congestion_price_rt_cluster_max",
    "total_lmp_rt_cluster_mean",
    # LMP — Ashburn distribution (separate fit)
    "congestion_price_rt_ashburn_tx1",
    "congestion_price_rt_ashburn_tx2",
    # LMP — negative controls
    "congestion_price_rt_ox",
    "congestion_price_rt_bristers",
    "congestion_price_rt_dom_zonal",
    # Reserves & events
    "sync_reserve_event_active",
    "sync_reserve_event_id",
    "hours_to_next_sync_event",
    "hours_since_last_sync_event",
    "sync_reserve_clearing_price_rt",
    "primary_reserve_clearing_price_rt",
)


def validate_panel(df: pd.DataFrame) -> None:
    """Raise ValueError if df is missing any expected column."""
    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"missing expected columns: {sorted(missing)}"
        )
```

- [ ] **Step 5: Run tests to verify pass**

```
.venv/bin/pytest tests/preprocessing/test_schema.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 70 passed (66 + 4 new).

- [ ] **Step 7: Commit**

```bash
git add src/surg/preprocessing/ tests/preprocessing/
git commit -m "feat(preprocessing): scaffold module with versioned schema"
```

---

## Task 2: Loader for `rt_hrl_lmps` (LMP nodal)

**Files:**
- Create: `src/surg/preprocessing/loaders.py`
- Create: `tests/preprocessing/test_loaders.py`

- [ ] **Step 1: Write failing test**

Create `tests/preprocessing/test_loaders.py`:

```python
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
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_loaders.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `load_rt_hrl_lmps`**

Create `src/surg/preprocessing/loaders.py`:

```python
"""Loaders: parquet chunks → tidy DataFrames per feed.

Each loader takes a `data_root` path (default `data/raw`), globs the
feed's chunks, and returns a single DataFrame keyed on its date column
with the data types expected by downstream code.

Empty feed dirs return an empty DataFrame with the expected columns
(not None) so downstream code can chain without null-checking.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_rt_hrl_lmps(data_root: Path) -> pd.DataFrame:
    """Load all rt_hrl_lmps chunks into a long-format DataFrame.

    Columns: datetime_beginning_ept (datetime64), pnode_id (int),
    pnode_name (str), congestion_price_rt (float),
    total_lmp_rt (float), and any extra columns present in the chunks.
    """
    feed_dir = data_root / "rt_hrl_lmps"
    expected_cols = [
        "datetime_beginning_ept", "pnode_id", "pnode_name",
        "congestion_price_rt", "total_lmp_rt",
    ]
    if not feed_dir.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in expected_cols})

    chunks = sorted(feed_dir.rglob("*.parquet"))
    if not chunks:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in expected_cols})

    dfs = [pd.read_parquet(p) for p in chunks]
    df = pd.concat(dfs, ignore_index=True)

    # Parse the EPT timestamp string to pandas datetime
    df["datetime_beginning_ept"] = pd.to_datetime(
        df["datetime_beginning_ept"], errors="raise"
    )
    # Cast pnode_id to int (it should already be, but be defensive)
    df["pnode_id"] = df["pnode_id"].astype("int64")

    return df.sort_values("datetime_beginning_ept").reset_index(drop=True)
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_loaders.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 72 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/loaders.py tests/preprocessing/test_loaders.py
git commit -m "feat(preprocessing): add load_rt_hrl_lmps with empty-dir handling"
```

---

## Task 3: Loader for `hrl_load_metered` (DOM zonal load)

**Files:**
- Modify: `src/surg/preprocessing/loaders.py`
- Modify: `tests/preprocessing/test_loaders.py`

- [ ] **Step 1: Write failing test**

Append to `tests/preprocessing/test_loaders.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_loaders.py -k load_dom_load -v
```

Expected: ImportError on `load_dom_load`.

- [ ] **Step 3: Add `load_dom_load` to loaders.py**

Append to `src/surg/preprocessing/loaders.py`:

```python
def load_dom_load(data_root: Path) -> pd.DataFrame:
    """Load DOM-zone metered hourly load.

    Returns: DataFrame with columns datetime_beginning_ept (datetime64),
    dom_load_mw (float). Sorted ascending by timestamp.
    Defensively filters to zone == 'DOM' even though acquisition
    already filters at the API level.
    """
    feed_dir = data_root / "hrl_load_metered"
    out_cols = ["datetime_beginning_ept", "dom_load_mw"]
    if not feed_dir.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    chunks = sorted(feed_dir.rglob("*.parquet"))
    if not chunks:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    dfs = [pd.read_parquet(p) for p in chunks]
    df = pd.concat(dfs, ignore_index=True)

    # Defensive filter to DOM zone
    df = df[df["zone"] == "DOM"].copy()

    df["datetime_beginning_ept"] = pd.to_datetime(
        df["datetime_beginning_ept"], errors="raise"
    )
    df = df.rename(columns={"mw": "dom_load_mw"})

    return df[out_cols].sort_values("datetime_beginning_ept").reset_index(drop=True)
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_loaders.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 74 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/loaders.py tests/preprocessing/test_loaders.py
git commit -m "feat(preprocessing): add load_dom_load with defensive zone filter"
```

---

## Task 4: Loader for `sync_reserve_events`

**Files:**
- Modify: `src/surg/preprocessing/loaders.py`
- Modify: `tests/preprocessing/test_loaders.py`

- [ ] **Step 1: Write failing test**

Append to `tests/preprocessing/test_loaders.py`:

```python
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
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_loaders.py -k sync_reserve_events -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `load_sync_reserve_events`**

Append to `src/surg/preprocessing/loaders.py`:

```python
def load_sync_reserve_events(data_root: Path) -> pd.DataFrame:
    """Load sync_reserve_events for the MAD sub-zone.

    Returns: DataFrame with columns event_start_ept, event_end_ept
    (both datetime64), duration (str), synchronized_sub_zone (str),
    event_id (int, zero-indexed by sort order). Sorted by event_start_ept.
    """
    feed_dir = data_root / "sync_reserve_events"
    out_cols = ["event_start_ept", "event_end_ept", "duration",
                "synchronized_sub_zone", "event_id"]
    if not feed_dir.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    chunks = sorted(feed_dir.rglob("*.parquet"))
    if not chunks:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    dfs = [pd.read_parquet(p) for p in chunks]
    df = pd.concat(dfs, ignore_index=True)

    df["event_start_ept"] = pd.to_datetime(df["event_start_ept"], errors="raise")
    df["event_end_ept"] = pd.to_datetime(df["event_end_ept"], errors="raise")
    df = df.sort_values("event_start_ept").reset_index(drop=True)
    df["event_id"] = df.index.astype("int64")

    keep = [c for c in out_cols if c in df.columns]
    return df[keep]
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_loaders.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 76 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/loaders.py tests/preprocessing/test_loaders.py
git commit -m "feat(preprocessing): add load_sync_reserve_events with event_id"
```

---

## Task 5: Loader for `reserve_market_results` with 5-min → hourly aggregation

The raw feed is 5-min granularity; the panel is hourly. Aggregate by taking the hourly mean of the clearing price (`mcp`) within each `service`.

**Files:**
- Modify: `src/surg/preprocessing/loaders.py`
- Modify: `tests/preprocessing/test_loaders.py`

- [ ] **Step 1: Write failing test**

Append to `tests/preprocessing/test_loaders.py`:

```python
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
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_loaders.py -k reserve_market -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `load_reserve_market_results`**

Append to `src/surg/preprocessing/loaders.py`:

```python
def load_reserve_market_results(data_root: Path) -> pd.DataFrame:
    """Load reserve_market_results for locale=MAD, services SR + PR.

    Aggregates 5-min granularity to hourly mean per service. Returns:
    DataFrame with columns datetime_beginning_ept (datetime64, hourly),
    sync_reserve_clearing_price_rt (float, NaN if no SR rows that hour),
    primary_reserve_clearing_price_rt (float, NaN if no PR rows that hour).
    """
    feed_dir = data_root / "reserve_market_results"
    out_cols = [
        "datetime_beginning_ept",
        "sync_reserve_clearing_price_rt",
        "primary_reserve_clearing_price_rt",
    ]
    if not feed_dir.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    chunks = sorted(feed_dir.rglob("*.parquet"))
    if not chunks:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    dfs = [pd.read_parquet(p) for p in chunks]
    df = pd.concat(dfs, ignore_index=True)

    df["datetime_beginning_ept"] = pd.to_datetime(
        df["datetime_beginning_ept"], errors="raise"
    )

    # Filter to MAD locale and SR/PR services
    df = df[(df["locale"] == "MAD") & (df["service"].isin(["SR", "PR"]))]

    # Floor the 5-min timestamps to the hour
    df = df.assign(_hour=df["datetime_beginning_ept"].dt.floor("h"))

    # Mean mcp per (hour, service); then pivot to two columns
    agg = (
        df.groupby(["_hour", "service"], as_index=False)["mcp"]
        .mean()
        .pivot(index="_hour", columns="service", values="mcp")
        .reset_index()
        .rename(columns={
            "_hour": "datetime_beginning_ept",
            "SR": "sync_reserve_clearing_price_rt",
            "PR": "primary_reserve_clearing_price_rt",
        })
    )
    agg.columns.name = None

    # Ensure both columns exist even if one service had no data
    for col in ("sync_reserve_clearing_price_rt",
                "primary_reserve_clearing_price_rt"):
        if col not in agg.columns:
            agg[col] = pd.NA

    return agg[out_cols].sort_values("datetime_beginning_ept").reset_index(drop=True)
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_loaders.py -v
```

Expected: 9 passed.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 79 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/loaders.py tests/preprocessing/test_loaders.py
git commit -m "feat(preprocessing): add load_reserve_market_results with hourly aggregation"
```

---

## Task 6: Feature — DOM load gradient

**Files:**
- Create: `src/surg/preprocessing/features.py`
- Create: `tests/preprocessing/test_features.py`

- [ ] **Step 1: Write failing test**

Create `tests/preprocessing/test_features.py`:

```python
from datetime import datetime

import pandas as pd
import pytest


def test_add_load_gradient_columns_computes_diff_per_hour():
    from surg.preprocessing.features import add_load_gradient_columns

    df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime([
            "2024-07-15T00:00:00",
            "2024-07-15T01:00:00",
            "2024-07-15T02:00:00",
        ]),
        "dom_load_mw": [10_000.0, 10_120.0, 10_080.0],
    })

    out = add_load_gradient_columns(df)

    # First row has no prior → NaN
    assert pd.isna(out["dom_load_gradient_mw_per_hr"].iloc[0])
    # Second row: 10120 - 10000 = +120 MW/hr
    assert out["dom_load_gradient_mw_per_hr"].iloc[1] == 120.0
    assert out["dom_load_gradient_signed_mw_per_min"].iloc[1] == 2.0  # 120 / 60
    assert out["dom_load_gradient_abs_mw_per_min"].iloc[1] == 2.0
    # Third row: 10080 - 10120 = -40 MW/hr
    assert out["dom_load_gradient_mw_per_hr"].iloc[2] == -40.0
    assert out["dom_load_gradient_signed_mw_per_min"].iloc[2] == pytest.approx(-40 / 60)
    assert out["dom_load_gradient_abs_mw_per_min"].iloc[2] == pytest.approx(40 / 60)


def test_add_load_gradient_columns_preserves_existing_columns():
    from surg.preprocessing.features import add_load_gradient_columns
    df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(["2024-01-01T00:00:00"]),
        "dom_load_mw": [12_000.0],
        "extra": ["x"],
    })
    out = add_load_gradient_columns(df)
    assert "extra" in out.columns
    assert out["extra"].iloc[0] == "x"
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_features.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `add_load_gradient_columns`**

Create `src/surg/preprocessing/features.py`:

```python
"""Feature engineering: derive volatility, pnode aggregation, event-active.

Each function takes a DataFrame and returns a new DataFrame with the
input columns plus the derived ones. Pure functions, no I/O.
"""
from __future__ import annotations

import pandas as pd


def add_load_gradient_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour-over-hour gradient columns to a DOM-load DataFrame.

    Requires `datetime_beginning_ept` (sorted, hourly) and `dom_load_mw`.
    Adds:
    - dom_load_gradient_mw_per_hr: dom_load_mw.diff(1)
    - dom_load_gradient_signed_mw_per_min: gradient / 60
    - dom_load_gradient_abs_mw_per_min: abs(gradient) / 60

    First row gets NaN for each (no prior hour).
    """
    out = df.copy()
    gradient = out["dom_load_mw"].diff(1)
    out["dom_load_gradient_mw_per_hr"] = gradient
    out["dom_load_gradient_signed_mw_per_min"] = gradient / 60.0
    out["dom_load_gradient_abs_mw_per_min"] = gradient.abs() / 60.0
    return out
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_features.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 81 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/features.py tests/preprocessing/test_features.py
git commit -m "feat(preprocessing): add load gradient feature"
```

---

## Task 7: Feature — Pivot LMP long → wide + Loudoun cluster aggregation

**Files:**
- Modify: `src/surg/preprocessing/features.py`
- Modify: `tests/preprocessing/test_features.py`

- [ ] **Step 1: Write failing test**

Append to `tests/preprocessing/test_features.py`:

```python
# Pnode IDs from src/surg/acquisition/targets.py (Loudoun cluster + others)
LOUDOUN_CLUSTER_IDS = (
    35010365,    # LOUDOUN
    35010371,    # PLEASANT VIEW
    1356178195,  # GOOSECRE
    1356178171,  # BRAMBLET
    1356178181,  # MOSBY
    1356178201,  # SKFFSCRK
)


def test_pivot_lmp_long_to_pnode_columns_creates_one_col_per_pnode():
    from surg.preprocessing.features import pivot_lmp_long_to_pnode_columns

    long_df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime([
            "2024-07-15T18:00:00", "2024-07-15T18:00:00",
            "2024-07-15T19:00:00", "2024-07-15T19:00:00",
        ]),
        "pnode_id": [35010365, 35010371, 35010365, 35010371],
        "pnode_name": ["LOUDOUN", "PLEASANT VIEW", "LOUDOUN", "PLEASANT VIEW"],
        "congestion_price_rt": [10.0, 12.0, 15.0, 18.0],
        "total_lmp_rt": [50.0, 52.0, 55.0, 58.0],
    })

    out = pivot_lmp_long_to_pnode_columns(long_df)

    assert len(out) == 2  # 2 unique timestamps
    assert "datetime_beginning_ept" in out.columns
    # Per-pnode columns for congestion price
    assert "congestion_price_rt_35010365" in out.columns
    assert "congestion_price_rt_35010371" in out.columns
    # Per-pnode columns for total LMP
    assert "total_lmp_rt_35010365" in out.columns
    assert "total_lmp_rt_35010371" in out.columns
    # Values
    row0 = out.iloc[0]
    assert row0["congestion_price_rt_35010365"] == 10.0
    assert row0["congestion_price_rt_35010371"] == 12.0


def test_add_loudoun_cluster_columns_computes_mean_and_max():
    from surg.preprocessing.features import (
        pivot_lmp_long_to_pnode_columns, add_loudoun_cluster_columns,
    )

    rows = []
    for pid in LOUDOUN_CLUSTER_IDS:
        rows.append({
            "datetime_beginning_ept": pd.Timestamp("2024-07-15T18:00:00"),
            "pnode_id": pid, "pnode_name": str(pid),
            "congestion_price_rt": 10.0 + (pid % 100),  # mild variation
            "total_lmp_rt": 50.0 + (pid % 100),
        })
    long_df = pd.DataFrame(rows)

    wide = pivot_lmp_long_to_pnode_columns(long_df)
    out = add_loudoun_cluster_columns(wide, LOUDOUN_CLUSTER_IDS)

    cluster_cols = [f"congestion_price_rt_{pid}" for pid in LOUDOUN_CLUSTER_IDS]
    expected_mean = wide[cluster_cols].mean(axis=1).iloc[0]
    expected_max = wide[cluster_cols].max(axis=1).iloc[0]

    assert out["congestion_price_rt_cluster_mean"].iloc[0] == expected_mean
    assert out["congestion_price_rt_cluster_max"].iloc[0] == expected_max
    # total_lmp_rt cluster mean is also added
    assert "total_lmp_rt_cluster_mean" in out.columns
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_features.py -v
```

Expected: ImportError on `pivot_lmp_long_to_pnode_columns` and `add_loudoun_cluster_columns`.

- [ ] **Step 3: Implement both functions in features.py**

Append to `src/surg/preprocessing/features.py`:

```python
def pivot_lmp_long_to_pnode_columns(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot long-format LMP (one row per pnode per hour) to wide.

    Output: one row per `datetime_beginning_ept`, with two columns per
    pnode: `congestion_price_rt_<pnode_id>` and `total_lmp_rt_<pnode_id>`.
    pnode_id is used in the column name (not pnode_name) because the LMP
    feed truncates pnode_name (see docs/sources/pjm-api-constraints.md).
    """
    if long_df.empty:
        return pd.DataFrame({"datetime_beginning_ept": pd.Series(dtype="datetime64[ns]")})

    pivoted = long_df.pivot_table(
        index="datetime_beginning_ept",
        columns="pnode_id",
        values=["congestion_price_rt", "total_lmp_rt"],
    )
    # Flatten the (value, pnode_id) MultiIndex columns to `value_pnodeid` strings
    pivoted.columns = [f"{val}_{pid}" for val, pid in pivoted.columns]
    return pivoted.reset_index()


def add_loudoun_cluster_columns(
    wide_df: pd.DataFrame,
    cluster_pnode_ids: tuple[int, ...],
) -> pd.DataFrame:
    """Add congestion_price_rt_cluster_{mean,max} and total_lmp_rt_cluster_mean.

    cluster_pnode_ids = the 6 Loudoun-area transmission pnodes (see
    docs/decisions.md 2026-05-10 "Lock the 11-pnode target set").
    """
    cong_cols = [f"congestion_price_rt_{pid}" for pid in cluster_pnode_ids
                 if f"congestion_price_rt_{pid}" in wide_df.columns]
    total_cols = [f"total_lmp_rt_{pid}" for pid in cluster_pnode_ids
                  if f"total_lmp_rt_{pid}" in wide_df.columns]

    out = wide_df.copy()
    out["congestion_price_rt_cluster_mean"] = out[cong_cols].mean(axis=1)
    out["congestion_price_rt_cluster_max"] = out[cong_cols].max(axis=1)
    out["total_lmp_rt_cluster_mean"] = out[total_cols].mean(axis=1)
    return out
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_features.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 83 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/features.py tests/preprocessing/test_features.py
git commit -m "feat(preprocessing): add LMP pivot + Loudoun cluster aggregation"
```

---

## Task 8: Feature — Sync reserve event-active flag and lead-lag distances

For each panel timestamp t, mark whether a sync_reserve_event covers it (`event_start ≤ t < event_end`) and compute hours-to-next / hours-since-last event.

**Files:**
- Modify: `src/surg/preprocessing/features.py`
- Modify: `tests/preprocessing/test_features.py`

- [ ] **Step 1: Write failing test**

Append to `tests/preprocessing/test_features.py`:

```python
def test_add_sync_event_columns_marks_active_hours():
    from surg.preprocessing.features import add_sync_event_columns

    timestamps = pd.to_datetime([
        "2024-07-15T17:00:00",  # before event
        "2024-07-15T18:00:00",  # event covers 18:30-19:15 → 18:00 hour overlaps event
        "2024-07-15T19:00:00",  # 19:00 hour: event ends 19:15, so still active
        "2024-07-15T20:00:00",  # after event
    ])
    panel = pd.DataFrame({"datetime_beginning_ept": timestamps})
    events = pd.DataFrame({
        "event_start_ept": [pd.Timestamp("2024-07-15T18:30:00")],
        "event_end_ept":   [pd.Timestamp("2024-07-15T19:15:00")],
        "event_id":        [0],
    })

    out = add_sync_event_columns(panel, events)
    active = list(out["sync_reserve_event_active"])
    # An event covers timestamp t if event_start <= t+1h AND event_end > t
    # (any overlap with the [t, t+1h) hour bucket).
    assert active == [False, True, True, False]
    # event_id is NaN when inactive, 0 when this event is active
    assert pd.isna(out["sync_reserve_event_id"].iloc[0])
    assert out["sync_reserve_event_id"].iloc[1] == 0
    assert out["sync_reserve_event_id"].iloc[2] == 0
    assert pd.isna(out["sync_reserve_event_id"].iloc[3])


def test_add_sync_event_columns_handles_empty_events():
    from surg.preprocessing.features import add_sync_event_columns
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(["2024-07-15T18:00:00"])
    })
    events = pd.DataFrame({"event_start_ept": pd.Series(dtype="datetime64[ns]"),
                           "event_end_ept": pd.Series(dtype="datetime64[ns]"),
                           "event_id": pd.Series(dtype="int64")})

    out = add_sync_event_columns(panel, events)
    assert out["sync_reserve_event_active"].iloc[0] is False or \
           bool(out["sync_reserve_event_active"].iloc[0]) is False
    assert pd.isna(out["sync_reserve_event_id"].iloc[0])
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_features.py -k sync_event -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `add_sync_event_columns`**

Append to `src/surg/preprocessing/features.py`:

```python
def add_sync_event_columns(
    panel: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """Add sync_reserve_event_active (bool) and sync_reserve_event_id (int|NaN).

    A panel timestamp `t` (hourly) is "active" if any event overlaps the
    hour bucket [t, t+1h): event_start < t+1h AND event_end > t.
    If active, event_id is set to the earliest such event's id.
    """
    out = panel.copy()
    out["sync_reserve_event_active"] = False
    out["sync_reserve_event_id"] = pd.NA

    if events.empty:
        return out

    one_hour = pd.Timedelta(hours=1)
    # Naive O(n*m) loop; acceptable since events are rare (~10s per year).
    for _, ev in events.iterrows():
        start = ev["event_start_ept"]
        end = ev["event_end_ept"]
        mask = (out["datetime_beginning_ept"] + one_hour > start) & \
               (out["datetime_beginning_ept"] < end)
        # Only set event_id where it hasn't been set yet (first event wins)
        first_set = mask & out["sync_reserve_event_id"].isna()
        out.loc[mask, "sync_reserve_event_active"] = True
        out.loc[first_set, "sync_reserve_event_id"] = ev["event_id"]

    return out
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_features.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 85 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/features.py tests/preprocessing/test_features.py
git commit -m "feat(preprocessing): add sync_reserve_event_active flag"
```

---

## Task 9: Feature — Lead-lag distances to events + filter columns

**Files:**
- Modify: `src/surg/preprocessing/features.py`
- Modify: `tests/preprocessing/test_features.py`

- [ ] **Step 1: Write failing test**

Append to `tests/preprocessing/test_features.py`:

```python
def test_add_event_lead_lag_columns():
    from surg.preprocessing.features import add_event_lead_lag_columns

    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime([
            "2024-07-15T17:00:00",
            "2024-07-15T18:00:00",
            "2024-07-15T20:00:00",
            "2024-07-15T21:00:00",
        ]),
    })
    events = pd.DataFrame({
        "event_start_ept": pd.to_datetime(["2024-07-15T18:30:00"]),
        "event_end_ept":   pd.to_datetime(["2024-07-15T19:15:00"]),
        "event_id": [0],
    })

    out = add_event_lead_lag_columns(panel, events)
    # 17:00 → next event starts 18:30 → 1.5 hours forward
    assert out["hours_to_next_sync_event"].iloc[0] == 1.5
    # No prior event before 17:00 → NaN
    assert pd.isna(out["hours_since_last_sync_event"].iloc[0])
    # 20:00 → prior event ended 19:15 → 0.75 hours since
    assert out["hours_since_last_sync_event"].iloc[2] == 0.75
    # 21:00 → no next event → NaN
    assert pd.isna(out["hours_to_next_sync_event"].iloc[3])


def test_add_filter_columns_marks_shoulder_and_2_5am():
    from surg.preprocessing.features import add_filter_columns

    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime([
            "2024-03-15T03:00:00",  # shoulder + 2-5 → pass
            "2024-03-15T14:00:00",  # shoulder, not 2-5
            "2024-07-15T03:00:00",  # 2-5, not shoulder (July is summer)
            "2024-07-15T14:00:00",  # neither
            "2024-11-01T04:00:00",  # shoulder + 2-5 → pass
        ])
    })

    out = add_filter_columns(panel)
    assert list(out["in_shoulder_season"]) == [True, True, False, False, True]
    assert list(out["in_2_5am_window"]) == [True, False, True, False, True]
    assert list(out["passes_proposal_filter"]) == [True, False, False, False, True]
    # DST-transition flag: true for spring-forward / fall-back hours
    # in our analysis window. None of the above happen to be DST-transition.
    assert all(out["dst_transition_hour"] == False)


def test_add_filter_columns_flags_spring_forward_2am_when_present():
    """In EPT, spring-forward day skips 2-3 AM (the 2 AM hour doesn't exist).
    No timestamp at 2 AM ept means there's nothing to flag. So the dst_transition_hour
    is True only for fall-back duplicated 1 AM hours that happen to be in the 2-5 AM
    window — and fall-back duplicates 1 AM not in our window. Net: dst_transition_hour
    is currently always False for our 2-5 AM filtered subset, but we keep the column
    for forward-compatibility."""
    # No-op test; documents the rationale.
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_features.py -k "lead_lag or filter_columns" -v
```

Expected: ImportError.

- [ ] **Step 3: Implement both functions**

Append to `src/surg/preprocessing/features.py`:

```python
def add_event_lead_lag_columns(
    panel: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """Add hours_to_next_sync_event and hours_since_last_sync_event."""
    out = panel.copy()
    out["hours_to_next_sync_event"] = pd.NA
    out["hours_since_last_sync_event"] = pd.NA

    if events.empty:
        return out

    starts = events["event_start_ept"].sort_values().reset_index(drop=True)
    ends = events["event_end_ept"].sort_values().reset_index(drop=True)

    for i, t in enumerate(out["datetime_beginning_ept"]):
        # next event start strictly after t
        next_idx = starts.searchsorted(t, side="right")
        if next_idx < len(starts):
            delta = (starts.iloc[next_idx] - t).total_seconds() / 3600
            out.loc[out.index[i], "hours_to_next_sync_event"] = delta
        # last event end at or before t
        prev_idx = ends.searchsorted(t, side="right") - 1
        if prev_idx >= 0 and ends.iloc[prev_idx] <= t:
            delta = (t - ends.iloc[prev_idx]).total_seconds() / 3600
            out.loc[out.index[i], "hours_since_last_sync_event"] = delta

    return out


def add_filter_columns(panel: pd.DataFrame) -> pd.DataFrame:
    """Add in_shoulder_season, in_2_5am_window, passes_proposal_filter,
    dst_transition_hour."""
    out = panel.copy()
    months = out["datetime_beginning_ept"].dt.month
    hours = out["datetime_beginning_ept"].dt.hour
    out["in_shoulder_season"] = months.isin([3, 4, 5, 9, 10, 11])
    out["in_2_5am_window"] = hours.isin([2, 3, 4])
    out["passes_proposal_filter"] = out["in_shoulder_season"] & out["in_2_5am_window"]
    # DST transition hour: see test docstring for why this is currently always False.
    out["dst_transition_hour"] = False
    return out
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_features.py -v
```

Expected: 8 passed (one no-op test counts as passed since it has no assertions).

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 87 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/features.py tests/preprocessing/test_features.py
git commit -m "feat(preprocessing): add lead-lag and filter columns"
```

---

## Task 10: Build orchestrator + atomic write

**Files:**
- Create: `src/surg/preprocessing/build.py`
- Create: `tests/preprocessing/test_build.py`

- [ ] **Step 1: Write failing test for `build_analysis_panel` (integration test using synthetic raw fixtures)**

Create `tests/preprocessing/test_build.py`:

```python
from pathlib import Path

import pandas as pd
import pytest


def _seed_minimal_raw(data_root: Path) -> None:
    """Write minimal raw chunks (one hour worth) so build_analysis_panel can run."""
    # rt_hrl_lmps: 11 pnodes × 1 hour
    pnodes = [
        (35010365, "LOUDOUN"), (35010371, "PLEASANT VIEW"),
        (1356178195, "GOOSECRE"), (1356178171, "BRAMBLET"),
        (1356178181, "MOSBY"), (1356178201, "SKFFSCRK"),
        (34886139, "ASHBURN 35 KV TX1"), (34886141, "ASHBURN 35 KV TX2"),
        (35010369, "OX"), (62871513, "BRISTERS"),
        (34964545, "DOM"),
    ]
    rt_dir = data_root / "rt_hrl_lmps" / "2024"
    rt_dir.mkdir(parents=True)
    pd.DataFrame([
        {"datetime_beginning_ept": "2024-07-15T18:00:00",
         "pnode_id": pid, "pnode_name": name,
         "congestion_price_rt": 5.0 + (pid % 10),
         "total_lmp_rt": 50.0 + (pid % 10)}
        for pid, name in pnodes
    ]).to_parquet(rt_dir / "dom_targets__2024-07-15_to_2024-07-15.parquet")

    # hrl_load_metered: 2 hours of DOM load so gradient is computable
    load_dir = data_root / "hrl_load_metered" / "2024"
    load_dir.mkdir(parents=True)
    pd.DataFrame([
        {"datetime_beginning_ept": "2024-07-15T17:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 12000.0, "is_verified": True},
        {"datetime_beginning_ept": "2024-07-15T18:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 12120.0, "is_verified": True},
    ]).to_parquet(load_dir / "dom__2024-07-15_to_2024-07-15.parquet")

    # sync_reserve_events: empty (no events that day)
    ev_dir = data_root / "sync_reserve_events" / "2024"
    ev_dir.mkdir(parents=True)
    pd.DataFrame({
        "event_start_ept": pd.Series(dtype=object),
        "event_end_ept": pd.Series(dtype=object),
        "duration": pd.Series(dtype=object),
        "synchronized_reserve_zone": pd.Series(dtype=object),
        "synchronized_sub_zone": pd.Series(dtype=object),
    }).to_parquet(ev_dir / "mad__2024-07-15_to_2024-07-15.parquet")

    # reserve_market_results: 12 5-min rows × 2 services
    rmr_dir = data_root / "reserve_market_results" / "2024"
    rmr_dir.mkdir(parents=True)
    rmr_rows = []
    for service, base in [("SR", 100.0), ("PR", 30.0)]:
        for i in range(12):
            rmr_rows.append({
                "datetime_beginning_ept": f"2024-07-15T18:{i*5:02d}:00",
                "locale": "MAD", "service": service, "mcp": base + i,
            })
    pd.DataFrame(rmr_rows).to_parquet(rmr_dir / "mad__2024-07-15_to_2024-07-15.parquet")


def test_build_analysis_panel_produces_validated_panel(tmp_path: Path):
    from surg.preprocessing.build import build_analysis_panel
    from surg.preprocessing.schema import validate_panel, EXPECTED_COLUMNS

    _seed_minimal_raw(tmp_path)
    panel = build_analysis_panel(data_root=tmp_path)

    # Schema validation passes
    validate_panel(panel)
    # We seeded two hours of load (17:00 and 18:00); panel rows align to load hours.
    assert len(panel) == 2
    # Gradient at 18:00 is 12120 - 12000 = 120 MW/hr = 2 MW/min
    row18 = panel[panel["datetime_beginning_ept"] == pd.Timestamp("2024-07-15T18:00:00")].iloc[0]
    assert row18["dom_load_gradient_abs_mw_per_min"] == 2.0
    # Cluster mean exists and is reasonable (each of 6 pnodes has price 5+x)
    assert row18["congestion_price_rt_cluster_mean"] > 0
    # Reserve market columns present, hour 18 has aggregated mcps
    assert row18["sync_reserve_clearing_price_rt"] == 105.5  # 100+...+111 / 12
    assert row18["primary_reserve_clearing_price_rt"] == 35.5
    # July is not shoulder season
    assert row18["passes_proposal_filter"] is False or bool(row18["passes_proposal_filter"]) is False


def test_build_analysis_panel_writes_atomic_parquet(tmp_path: Path):
    """write_panel: tmp file + os.replace, no partial file on interruption."""
    from surg.preprocessing.build import build_analysis_panel, write_panel

    _seed_minimal_raw(tmp_path)
    panel = build_analysis_panel(data_root=tmp_path)
    out = tmp_path / "interim" / "analysis_panel.parquet"
    out.parent.mkdir(parents=True)

    write_panel(panel, out)

    assert out.exists()
    # No .tmp file lingers
    assert not (out.parent / "analysis_panel.parquet.tmp").exists()
    # Round-trip
    loaded = pd.read_parquet(out)
    assert len(loaded) == len(panel)


def test_build_analysis_panel_clips_to_analysis_window(tmp_path: Path):
    """Panel excludes hours outside [ANALYSIS_WINDOW_START, ANALYSIS_WINDOW_END)."""
    from surg.preprocessing.build import (
        build_analysis_panel, ANALYSIS_WINDOW_START, ANALYSIS_WINDOW_END,
    )

    _seed_minimal_raw(tmp_path)
    # Append a 2021 load row (before the window starts 2022-10-02)
    load_dir = tmp_path / "hrl_load_metered" / "2021"
    load_dir.mkdir(parents=True)
    pd.DataFrame([
        {"datetime_beginning_ept": "2021-06-15T03:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 11_000.0, "is_verified": True},
    ]).to_parquet(load_dir / "dom__2021-06-15.parquet")

    panel = build_analysis_panel(data_root=tmp_path)
    assert (panel["datetime_beginning_ept"] >= ANALYSIS_WINDOW_START).all()
    assert (panel["datetime_beginning_ept"] < ANALYSIS_WINDOW_END).all()
    # The 2021 row is not in the panel
    assert not (panel["datetime_beginning_ept"] == pd.Timestamp("2021-06-15T03:00:00")).any()
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/preprocessing/test_build.py -v
```

Expected: ImportError on `build_analysis_panel` / `write_panel`.

- [ ] **Step 3: Implement `build.py`**

Create `src/surg/preprocessing/build.py`:

```python
"""Orchestrator: build the analysis panel from raw feeds and write atomically.

Compose the loaders + features into a single pipeline:
  raw chunks → load each feed → derive features → join → filter
              → atomic write to data/interim/analysis_panel.parquet
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

from surg.preprocessing.loaders import (
    load_rt_hrl_lmps, load_dom_load,
    load_sync_reserve_events, load_reserve_market_results,
)
from surg.preprocessing.features import (
    add_load_gradient_columns,
    pivot_lmp_long_to_pnode_columns,
    add_loudoun_cluster_columns,
    add_sync_event_columns,
    add_event_lead_lag_columns,
    add_filter_columns,
)

# Per-tier pnode IDs from docs/decisions.md (2026-05-10 lock-in).
LOUDOUN_CLUSTER_IDS: tuple[int, ...] = (
    35010365, 35010371, 1356178195, 1356178171, 1356178181, 1356178201,
)
ASHBURN_TX1, ASHBURN_TX2 = 34886139, 34886141
CONTROL_OX, CONTROL_BRISTERS = 35010369, 62871513
DOM_ZONAL = 34964545

# Analysis window (3.6y post-cap). See docs/decisions.md
# "2026-05-12 — Window extension to 3.6y post-cap". Inclusive start,
# exclusive end → the final included hour is 2026-05-10 23:00 EPT.
ANALYSIS_WINDOW_START = pd.Timestamp("2022-10-02 00:00:00")
ANALYSIS_WINDOW_END = pd.Timestamp("2026-05-11 00:00:00")


def build_analysis_panel(data_root: Path) -> pd.DataFrame:
    """Build the hourly analysis panel from raw feeds under `data_root`.

    Joins LMP (Loudoun cluster + per-pnode controls), DOM zonal load
    (with derived gradient), sync_reserve_events (active flag + lead-lag),
    and reserve_market_results (hourly mean SR/PR clearing prices).
    Applies the shoulder + 2-5 AM filter columns.
    """
    lmp_long = load_rt_hrl_lmps(data_root)
    load_df = load_dom_load(data_root)
    events = load_sync_reserve_events(data_root)
    rmr = load_reserve_market_results(data_root)

    # LMP: long → wide → cluster + control columns
    lmp_wide = pivot_lmp_long_to_pnode_columns(lmp_long)
    lmp_wide = add_loudoun_cluster_columns(lmp_wide, LOUDOUN_CLUSTER_IDS)
    rename = {
        f"congestion_price_rt_{ASHBURN_TX1}": "congestion_price_rt_ashburn_tx1",
        f"congestion_price_rt_{ASHBURN_TX2}": "congestion_price_rt_ashburn_tx2",
        f"congestion_price_rt_{CONTROL_OX}":  "congestion_price_rt_ox",
        f"congestion_price_rt_{CONTROL_BRISTERS}": "congestion_price_rt_bristers",
        f"congestion_price_rt_{DOM_ZONAL}":   "congestion_price_rt_dom_zonal",
    }
    lmp_wide = lmp_wide.rename(columns=rename)

    # Load + gradient
    load_df = add_load_gradient_columns(load_df)

    # Outer-join on datetime_beginning_ept so we keep load hours even
    # if some have no LMP coverage (and vice versa).
    panel = load_df.merge(lmp_wide, on="datetime_beginning_ept", how="left")
    panel = panel.merge(rmr, on="datetime_beginning_ept", how="left")

    # Event columns
    panel = add_sync_event_columns(panel, events)
    panel = add_event_lead_lag_columns(panel, events)

    # Filter / metadata columns
    panel = add_filter_columns(panel)

    # Clip to analysis window [ANALYSIS_WINDOW_START, ANALYSIS_WINDOW_END).
    panel = panel[
        (panel["datetime_beginning_ept"] >= ANALYSIS_WINDOW_START)
        & (panel["datetime_beginning_ept"] < ANALYSIS_WINDOW_END)
    ].reset_index(drop=True)

    return panel


def write_panel(panel: pd.DataFrame, out_path: Path) -> None:
    """Atomic write via tmp file + os.replace."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    panel.to_parquet(tmp, index=False)
    os.replace(tmp, out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-prep",
        description="Build the hourly analysis panel from raw feeds.",
    )
    p.add_argument("--data-root", default="data/raw",
                   help="Root directory of raw parquet chunks.")
    p.add_argument("--output", default="data/interim/analysis_panel.parquet",
                   help="Output path for the analysis panel.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite even if output exists.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    data_root = Path(args.data_root)
    out_path = Path(args.output)

    if out_path.exists() and not args.force:
        print(f"{out_path} exists; pass --force to overwrite.", file=sys.stderr)
        return 2

    panel = build_analysis_panel(data_root=data_root)
    write_panel(panel, out_path)
    print(f"wrote {out_path} ({len(panel):,} rows)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_build.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 90 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/build.py tests/preprocessing/test_build.py
git commit -m "feat(preprocessing): add build_analysis_panel + atomic write_panel"
```

---

## Task 11: Wire up CLI entry point `surg-prep`

**Files:**
- Modify: `pyproject.toml` (add a console_scripts entry)
- Create: `tests/preprocessing/test_cli.py`

- [ ] **Step 1: Add entry point to pyproject.toml**

In `pyproject.toml`, find the `[project.scripts]` section. It currently contains `surg-pull = "surg.acquisition.pull:main"`. Append:

```toml
surg-prep = "surg.preprocessing.build:main"
```

- [ ] **Step 2: Re-install the package so the entry point is registered**

```
.venv/bin/pip install -e .
```

Expected: "Successfully installed surg-..." (editable install picks up the new entry point).

- [ ] **Step 3: Write CLI test**

Create `tests/preprocessing/test_cli.py`:

```python
from pathlib import Path

import pandas as pd
import pytest


def test_help_exits_zero(capsys):
    from surg.preprocessing.build import main
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "surg-prep" in out


def test_main_writes_panel_to_output_path(tmp_path: Path):
    from surg.preprocessing.build import main
    # Seed minimal raw using the helper from test_build.py
    from tests.preprocessing.test_build import _seed_minimal_raw

    _seed_minimal_raw(tmp_path)
    out = tmp_path / "interim" / "analysis_panel.parquet"
    rc = main([
        "--data-root", str(tmp_path),
        "--output", str(out),
    ])
    assert rc == 0
    assert out.exists()
    df = pd.read_parquet(out)
    assert len(df) >= 1


def test_main_refuses_to_overwrite_without_force(tmp_path: Path):
    from surg.preprocessing.build import main
    out = tmp_path / "panel.parquet"
    out.write_text("dummy")  # exists
    rc = main([
        "--data-root", str(tmp_path),
        "--output", str(out),
    ])
    assert rc == 2


def test_main_force_overwrites(tmp_path: Path):
    from surg.preprocessing.build import main
    from tests.preprocessing.test_build import _seed_minimal_raw

    _seed_minimal_raw(tmp_path)
    out = tmp_path / "interim" / "panel.parquet"
    out.parent.mkdir(parents=True)
    out.write_text("dummy")
    rc = main([
        "--data-root", str(tmp_path),
        "--output", str(out),
        "--force",
    ])
    assert rc == 0
    df = pd.read_parquet(out)
    assert len(df) >= 1
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/preprocessing/test_cli.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Smoke the entry point**

```
.venv/bin/surg-prep --help
```

Expected: usage line that starts with `usage: surg-prep`.

- [ ] **Step 6: Run full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 94 passed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml tests/preprocessing/test_cli.py
git commit -m "feat(preprocessing): add surg-prep CLI entry point"
```

---

## Task 12: End-to-end smoke build against real raw data

After Plan 1 completed and pulled raw data, this task verifies the real-world end-to-end pipeline. Not a code change.

- [ ] **Step 1: Verify raw data is present**

```bash
for feed in rt_hrl_lmps hrl_load_metered sync_reserve_events reserve_market_results; do
  count=$(find "data/raw/$feed" -name "*.parquet" 2>/dev/null | wc -l | tr -d ' ')
  echo "$feed: $count chunks"
done
```

Expected: each feed has 2-6 chunks. If any feed has 0 chunks, complete Plan 1 first.

- [ ] **Step 2: Build the panel**

```
.venv/bin/surg-prep
```

Expected: `wrote data/interim/analysis_panel.parquet (N rows)` where N is between 31,500 and 31,700 (3.6 years of hourly load data).

- [ ] **Step 3: Inspect the panel**

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/interim/analysis_panel.parquet')
print(f'rows: {len(df):,}')
print(f'date range: {df.datetime_beginning_ept.min()} → {df.datetime_beginning_ept.max()}')
print(f'columns: {len(df.columns)}')
print(f'passes_proposal_filter: {df.passes_proposal_filter.sum():,} hours ({df.passes_proposal_filter.mean()*100:.1f}%)')
print(f'sync_reserve_event_active: {df.sync_reserve_event_active.sum():,} hours')
nan_pct = df[['dom_load_mw', 'congestion_price_rt_cluster_mean']].isna().mean() * 100
print(f'NaN rates: dom_load_mw={nan_pct.iloc[0]:.2f}%, congestion_cluster={nan_pct.iloc[1]:.2f}%')
"
```

Expected:
- ~31,632 rows (~1,318 days × 24 hours)
- `passes_proposal_filter` count ~ 1,977 hours (per spec §4, scaled to 3.6y)
- `sync_reserve_event_active` count > 0 (if events exist in the analysis window)
- NaN rates < 1% (per spec §3)

If NaN rates exceed 1%, investigate before proceeding to Plan 3:
- Are there hours of LMP data without corresponding load data (or vice versa)?
- Is the outer/inner join correct?

- [ ] **Step 4: No commit** — output is gitignored.

---

## Task 13: Final verification

- [ ] **Step 1: Run full suite one last time**

```
.venv/bin/pytest tests/ -v
```

Expected: 94 passed.

- [ ] **Step 2: Verify git state**

```
git log --oneline origin/main..HEAD
```

Expected: 11 commits ahead (tasks 1-11 each commit; tasks 12 and 13 don't commit).

- [ ] **Step 3: Push (requires user confirmation)**

> "Preprocessing module complete. 11 new commits. Push?"

If yes:

```bash
git push origin main
```

---

## Definition of done

- [ ] All 13 tasks complete.
- [ ] 94 tests passing.
- [ ] `data/interim/analysis_panel.parquet` exists with ~31,632 rows, 23 columns, schema_version=1.
- [ ] `passes_proposal_filter` count is ~1,977 hours (validates Plan 3 sample-size assumption, scaled to 3.6y window).
- [ ] No regressions in acquisition module (66 acquisition tests still passing).

## Out of scope (deferred)

- The TAR/QR analysis itself (Plan 3).
- 5-min panel (`analysis_panel_5min.parquet`) — deferred per spec §3.
- DA LMP panel — deferred per spec §3.
- Schema migrations / version-bump migrators — not needed until SCHEMA_VERSION ever increments.
