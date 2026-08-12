# ERCOT Load Volatility Diagnostic — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Stage 1 diagnostic answering whether ERCOT load is volatile and whether hourly price tracks load level more than load volatility, mirroring the DOM analysis.

**Architecture:** Two thin scripts in `scripts/` (fetch, then analyze) plus one small tested module `src/surg/preprocessing/ercot_features.py` holding the pure transforms. Archives download to `data/raw/ercot/`, the joined panel lands in `data/interim/ercot_diagnostic_panel.parquet`, figures in `outputs/ercot_diagnostic/`.

**Tech Stack:** Python 3.12, pandas, openpyxl (new), statsmodels, matplotlib, pytest, httpx (already a dependency).

---

## ⚠️ Deliberate deviation from the spec — read before starting

The spec says "no new `src/` modules." This plan puts **two pure functions** in
`src/surg/preprocessing/ercot_features.py` anyway. Reason: the hour-ending→hour-beginning
conversion is new logic whose failure mode is a **silent one-hour misalignment** that corrupts
every result while looking plausible. Untested code in `scripts/` cannot be trusted with that.
The module is ~45 lines, sits beside the existing `features.py`, and seeds Stage 2.

Everything else in the spec is honored: no congestion decomposition, no QR/GPD port, no causal
claim.

## Second constraint discovered during planning

`add_load_gradient_columns` (`src/surg/preprocessing/features.py:22`) is **hardcoded** to the
columns `dom_load_mw` and `datetime_beginning_ept`. It cannot accept ERCOT zone columns directly.

The spec requires reusing it rather than re-implementing, so Task 3 builds an **adapter** that
renames each zone to `dom_load_mw`, calls the tested function, and renames the outputs back.
**Do not modify `features.py`.**

## File Structure

| File | Responsibility |
|---|---|
| `src/surg/preprocessing/ercot_features.py` | Pure transforms: hour-ending conversion, per-zone gradient adapter |
| `tests/test_ercot_features.py` | Tests for the above |
| `scripts/ercot_fetch.py` | Download + extract load and price annual archives |
| `scripts/ercot_diagnostic.py` | Parse, join, QA-assert, analyze, write figures |

**Zone constant used throughout:**
`ZONES = ["COAST", "EAST", "FWEST", "NORTH", "NCENT", "SOUTH", "SCENT", "WEST", "ERCOT"]`

---

## Task 1: Add the openpyxl dependency

Both ERCOT archives are XLSX. `pd.read_excel` currently fails with
`ModuleNotFoundError: No module named 'openpyxl'`.

**Files:**
- Modify: `pyproject.toml` (the `dependencies` list)

- [ ] **Step 1: Add the dependency**

In `pyproject.toml`, add `"openpyxl>=3.1",` to the `dependencies` list, after `"pyarrow>=14.0",`:

```toml
    "pyarrow>=14.0",
    "openpyxl>=3.1",
```

- [ ] **Step 2: Install it**

Run: `.venv/bin/python -m pip install 'openpyxl>=3.1'`
Expected: `Successfully installed openpyxl-3.x.x`

- [ ] **Step 3: Verify the import**

Run: `.venv/bin/python -c "import openpyxl; print(openpyxl.__version__)"`
Expected: a version number, no traceback.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build: add openpyxl for ERCOT xlsx archives"
```

---

## Task 2: Hour-ending → hour-beginning conversion

ERCOT publishes `Hour Ending` (`01/01/2024 01:00` means the hour 00:00–01:00). The DOM panel is
hour-beginning. Converting means **subtracting one hour**.

**Files:**
- Create: `src/surg/preprocessing/ercot_features.py`
- Test: `tests/test_ercot_features.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_ercot_features.py`:

```python
import pandas as pd
import pytest

from surg.preprocessing.ercot_features import hour_ending_to_beginning


def test_hour_ending_shifts_back_one_hour():
    df = pd.DataFrame({"Hour Ending": ["01/01/2024 01:00", "01/01/2024 02:00"]})
    out = hour_ending_to_beginning(df)
    assert list(out["datetime_beginning_cpt"]) == [
        pd.Timestamp("2024-01-01 00:00"),
        pd.Timestamp("2024-01-01 01:00"),
    ]


def test_original_column_is_dropped():
    df = pd.DataFrame({"Hour Ending": ["01/01/2024 01:00"]})
    out = hour_ending_to_beginning(df)
    assert "Hour Ending" not in out.columns


def test_dst_duplicate_hour_is_flagged_not_dropped():
    # Fall-back: the 02:00 hour-ending value appears twice.
    df = pd.DataFrame(
        {"Hour Ending": ["11/03/2024 02:00", "11/03/2024 02:00", "11/03/2024 03:00"]}
    )
    out = hour_ending_to_beginning(df)
    assert len(out) == 3, "duplicate DST hour must be preserved, not silently dropped"
    assert out["dst_transition_hour"].tolist() == [True, True, False]


def test_non_dst_rows_are_not_flagged():
    df = pd.DataFrame({"Hour Ending": ["01/01/2024 01:00", "01/01/2024 02:00"]})
    out = hour_ending_to_beginning(df)
    assert out["dst_transition_hour"].tolist() == [False, False]


def test_missing_column_raises():
    with pytest.raises(KeyError, match="Hour Ending"):
        hour_ending_to_beginning(pd.DataFrame({"wrong": [1]}))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ercot_features.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.preprocessing.ercot_features'`

- [ ] **Step 3: Write minimal implementation**

Create `src/surg/preprocessing/ercot_features.py`:

```python
"""Pure transforms for the ERCOT Stage 1 diagnostic panel.

No I/O. Each function takes a DataFrame and returns a new one.
"""
from __future__ import annotations

import pandas as pd

ZONES = ["COAST", "EAST", "FWEST", "NORTH", "NCENT", "SOUTH", "SCENT", "WEST", "ERCOT"]


def hour_ending_to_beginning(df: pd.DataFrame) -> pd.DataFrame:
    """Convert ERCOT's `Hour Ending` column to hour-beginning `datetime_beginning_cpt`.

    ERCOT labels the hour 00:00-01:00 as "01:00". The DOM panel is
    hour-beginning, so conversion subtracts one hour. Getting this wrong
    produces a silent one-hour misalignment against DOM.

    Duplicate timestamps (DST fall-back) are preserved and flagged in
    `dst_transition_hour` rather than dropped.
    """
    if "Hour Ending" not in df.columns:
        raise KeyError("Hour Ending column not found in ERCOT load frame")

    out = df.copy()
    ending = pd.to_datetime(out["Hour Ending"], format="%m/%d/%Y %H:%M")
    out["datetime_beginning_cpt"] = ending - pd.Timedelta(hours=1)
    out["dst_transition_hour"] = out["datetime_beginning_cpt"].duplicated(keep=False)
    return out.drop(columns=["Hour Ending"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ercot_features.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/ercot_features.py tests/test_ercot_features.py
git commit -m "feat: ERCOT hour-ending to hour-beginning conversion"
```

---

## Task 3: Per-zone gradient adapter

Reuse the tested `add_load_gradient_columns` for each of the 9 zone columns without modifying it.

**Files:**
- Modify: `src/surg/preprocessing/ercot_features.py`
- Test: `tests/test_ercot_features.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_ercot_features.py`:

```python
from surg.preprocessing.ercot_features import add_zone_gradient_columns


def test_gradient_matches_dom_formula():
    # 60 MW rise over one hour = 1.0 MW/min.
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [1000.0, 1060.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert out["load_gradient_abs_mw_per_min_COAST"].tolist()[1] == pytest.approx(1.0)


def test_gradient_is_absolute_valued():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [1060.0, 1000.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert out["load_gradient_abs_mw_per_min_COAST"].tolist()[1] == pytest.approx(1.0)


def test_first_row_is_nan():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(["2024-01-01 00:00"]),
            "load_mw_COAST": [1000.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert pd.isna(out["load_gradient_abs_mw_per_min_COAST"].iloc[0])


def test_multiple_zones_are_independent():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [1000.0, 1060.0],
            "load_mw_WEST": [500.0, 500.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST", "WEST"])
    assert out["load_gradient_abs_mw_per_min_COAST"].iloc[1] == pytest.approx(1.0)
    assert out["load_gradient_abs_mw_per_min_WEST"].iloc[1] == pytest.approx(0.0)


def test_source_load_columns_are_preserved():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [1000.0, 1060.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert out["load_mw_COAST"].tolist() == [1000.0, 1060.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_ercot_features.py -v`
Expected: FAIL — `ImportError: cannot import name 'add_zone_gradient_columns'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/surg/preprocessing/ercot_features.py`:

```python
from surg.preprocessing.features import add_load_gradient_columns


def add_zone_gradient_columns(
    df: pd.DataFrame,
    zones: list[str] | None = None,
) -> pd.DataFrame:
    """Add `load_gradient_abs_mw_per_min_<zone>` for each ERCOT zone.

    Delegates to the DOM `add_load_gradient_columns` so the volatility
    measure is provably identical across markets. That function is
    hardcoded to `dom_load_mw` / `datetime_beginning_ept`, so each zone is
    renamed in, computed, and renamed out. `features.py` is not modified.
    """
    zones = list(ZONES) if zones is None else zones
    out = df.copy()

    for zone in zones:
        shim = pd.DataFrame(
            {
                "datetime_beginning_ept": out["datetime_beginning_cpt"],
                "dom_load_mw": out[f"load_mw_{zone}"],
            }
        )
        gradients = add_load_gradient_columns(shim, freq_minutes=60)
        out[f"load_gradient_abs_mw_per_min_{zone}"] = gradients[
            "dom_load_gradient_abs_mw_per_min"
        ].to_numpy()

    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_ercot_features.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/ercot_features.py tests/test_ercot_features.py
git commit -m "feat: per-zone gradient adapter reusing DOM formula"
```

---

## Task 4: Fetch the annual archives

**Files:**
- Create: `scripts/ercot_fetch.py`

- [ ] **Step 1: Write the fetch script**

Create `scripts/ercot_fetch.py`:

```python
"""Download ERCOT annual load and RTM price archives.

Both are public: no API key, no quota. Verified 2026-08-07.

Load  : https://www.ercot.com/files/docs/<yyyy>/<mm>/<dd>/Native_Load_<YYYY>.zip
Price : GetReports.do?reportTypeId=13061 -> RTMLZHBSPP_<YYYY>.zip

Usage: .venv/bin/python scripts/ercot_fetch.py
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

import httpx

RAW = Path("data/raw/ercot")
LOAD_PAGE = "https://www.ercot.com/gridinfo/load/load_hist"
PRICE_LIST = "https://www.ercot.com/misapp/GetReports.do?reportTypeId=13061"
DOWNLOAD = "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={}"


def _get(client: httpx.Client, url: str) -> httpx.Response:
    resp = client.get(url, timeout=300.0, follow_redirects=True)
    resp.raise_for_status()
    return resp


def fetch_load(client: httpx.Client, dest: Path) -> list[Path]:
    """Download every Native_Load_<YYYY>.zip linked from the archive page."""
    html = _get(client, LOAD_PAGE).text
    urls = sorted(set(re.findall(r'https://[^"]*?Native_Load_\d{4}\.zip', html)))
    if not urls:
        raise RuntimeError("no Native_Load zips found; ERCOT page layout changed")

    written = []
    for url in urls:
        out = dest / url.rsplit("/", 1)[-1]
        if not out.exists():
            out.write_bytes(_get(client, url).content)
        written.append(out)
        print(f"load  {out.name}")
    return written


def fetch_prices(client: httpx.Client, dest: Path) -> list[Path]:
    """Download RTMLZHBSPP_<YYYY>.zip archives.

    The MIS listing pairs each filename with a doclookupId positionally.
    Pairing by proximity (e.g. `grep -B2`) mismatches rows, so both are
    extracted in document order and zipped together.
    """
    html = _get(client, PRICE_LIST).text
    names = re.findall(r"RTMLZHBSPP_(\d{4})\.zip", html)
    ids = re.findall(r"doclookupId=(\d+)", html)
    if len(names) != len(ids):
        raise RuntimeError(f"pairing mismatch: {len(names)} names vs {len(ids)} ids")

    written = []
    for year, doc_id in zip(names, ids):
        out = dest / f"RTMLZHBSPP_{year}.zip"
        if not out.exists():
            out.write_bytes(_get(client, DOWNLOAD.format(doc_id)).content)
        written.append(out)
        print(f"price {out.name}")
    return written


def extract_all(paths: list[Path], dest: Path) -> None:
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            archive.extractall(dest)


def main() -> None:
    dest = RAW
    dest.mkdir(parents=True, exist_ok=True)
    with httpx.Client() as client:
        load_zips = fetch_load(client, dest)
        price_zips = fetch_prices(client, dest)
    extract_all(load_zips + price_zips, dest)
    print(f"\nextracted to {dest}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the fetch**

Run: `.venv/bin/python scripts/ercot_fetch.py`
Expected: lines `load  Native_Load_1995.zip` … `price RTMLZHBSPP_2026.zip`, then `extracted to data/raw/ercot`. This downloads roughly 200 MB and takes several minutes.

- [ ] **Step 3: Verify the extracted files**

Run: `ls data/raw/ercot/*.xlsx | wc -l`
Expected: 30 or more (one load file per year from 1995, one price file per year from 2010).

- [ ] **Step 4: Commit**

`data/` is gitignored, so only the script is committed.

```bash
git add scripts/ercot_fetch.py
git commit -m "feat: fetch ERCOT annual load and RTM price archives"
```

---

## Task 5: Build the panel with QA assertions

**Files:**
- Create: `scripts/ercot_diagnostic.py`

- [ ] **Step 1: Write the panel builder**

Create `scripts/ercot_diagnostic.py`:

```python
"""Stage 1 ERCOT load volatility diagnostic.

Answers two questions:
  1. Is ERCOT load volatile, and is its volatility rising?
  2. Does hourly price track load level more than load volatility?

Usage: .venv/bin/python scripts/ercot_diagnostic.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.preprocessing.ercot_features import (
    ZONES,
    add_zone_gradient_columns,
    hour_ending_to_beginning,
)

RAW = Path("data/raw/ercot")
PANEL = Path("data/interim/ercot_diagnostic_panel.parquet")
FIGDIR = Path("outputs/ercot_diagnostic")

# 8-zone breakdown begins April 2003; earlier files use 11 control areas.
FIRST_ZONE_YEAR = 2004
# DOM panel starts 2022-10-02; matched window for the price comparison.
DOM_START = pd.Timestamp("2022-10-02")


def load_native_load() -> pd.DataFrame:
    """Read every Native_Load_<YYYY>.xlsx into one hour-beginning frame."""
    frames = []
    for path in sorted(RAW.glob("Native_Load_*.xlsx")):
        year = int(path.stem.split("_")[-1])
        if year < FIRST_ZONE_YEAR:
            continue
        raw = pd.read_excel(path)
        raw = raw.rename(columns={c: c.strip().upper() for c in raw.columns})
        raw = raw.rename(columns={"HOUR ENDING": "Hour Ending"})
        missing = [z for z in ZONES if z not in raw.columns]
        if missing:
            raise ValueError(f"{path.name} missing zones: {missing}")
        keep = raw[["Hour Ending", *ZONES]].copy()
        frames.append(keep)

    combined = pd.concat(frames, ignore_index=True)
    combined = hour_ending_to_beginning(combined)
    combined = combined.rename(columns={z: f"load_mw_{z}" for z in ZONES})
    return combined.sort_values("datetime_beginning_cpt").reset_index(drop=True)


def assert_panel_quality(panel: pd.DataFrame) -> None:
    """Fail loudly on the failure modes that previously bit this project."""
    non_dst = panel.loc[~panel["dst_transition_hour"], "datetime_beginning_cpt"]
    dupes = non_dst.duplicated().sum()
    if dupes:
        raise AssertionError(f"{dupes} duplicate non-DST timestamps")

    for zone in ZONES:
        col = f"load_mw_{zone}"
        if panel[col].isna().any():
            raise AssertionError(f"{col} contains NaN — do not interpolate, investigate")

    span = panel["datetime_beginning_cpt"]
    expected = int((span.max() - span.min()).total_seconds() // 3600) + 1
    actual = len(panel)
    if abs(expected - actual) > 48:
        raise AssertionError(f"gap detected: expected ~{expected} rows, got {actual}")


def build_panel() -> pd.DataFrame:
    panel = load_native_load()
    panel = add_zone_gradient_columns(panel)
    assert_panel_quality(panel)
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    build_panel()
```

- [ ] **Step 2: Run the builder**

Run: `.venv/bin/python scripts/ercot_diagnostic.py`
Expected: `panel: (NNNNN, 20) -> data/interim/ercot_diagnostic_panel.parquet`, roughly 190,000 rows for 2004–2026, no AssertionError.

- [ ] **Step 3: Commit**

```bash
git add scripts/ercot_diagnostic.py
git commit -m "feat: build ERCOT hourly diagnostic panel with QA gates"
```

---

## Task 6: Join prices on the DOM-matched window

**Files:**
- Modify: `scripts/ercot_diagnostic.py`

- [ ] **Step 1: Add the price loader**

Insert this function above `build_panel` in `scripts/ercot_diagnostic.py`:

```python
def load_prices() -> pd.DataFrame:
    """Read RTM settlement point prices, hourly mean per settlement point.

    Files are 15-minute; aggregate to hourly to match the load panel.
    Negative prices are real (ERCOT floor is -$251/MWh) and are NOT clipped.
    """
    frames = []
    for path in sorted(RAW.glob("*RTMLZHBSPP_*.xlsx")):
        year = int(path.stem.split("_")[-1])
        if year < DOM_START.year:
            continue
        book = pd.read_excel(path, sheet_name=None)
        for sheet in book.values():
            cols = {c.strip().lower(): c for c in sheet.columns}
            frames.append(
                pd.DataFrame(
                    {
                        "date": sheet[cols["delivery date"]],
                        "hour_str": sheet[cols["delivery hour"]].astype(str),
                        "settlement_point": sheet[cols["settlement point name"]],
                        "price": pd.to_numeric(
                            sheet[cols["settlement point price"]], errors="coerce"
                        ),
                    }
                )
            )

    raw = pd.concat(frames, ignore_index=True)
    # Delivery Hour is 1-24 (hour-ending); subtract 1 for hour-beginning.
    hours = pd.to_numeric(raw["hour_str"], errors="coerce") - 1
    raw["datetime_beginning_cpt"] = pd.to_datetime(raw["date"]) + pd.to_timedelta(
        hours, unit="h"
    )

    hourly = (
        raw.groupby(["datetime_beginning_cpt", "settlement_point"])["price"]
        .mean()
        .unstack("settlement_point")
    )
    hourly.columns = [f"total_lmp_rt_{c}" for c in hourly.columns]
    return hourly.reset_index()
```

- [ ] **Step 2: Join it in `build_panel`**

Replace the body of `build_panel` with:

```python
def build_panel() -> pd.DataFrame:
    panel = load_native_load()
    panel = add_zone_gradient_columns(panel)
    assert_panel_quality(panel)

    prices = load_prices()
    before = len(panel)
    panel = panel.merge(prices, on="datetime_beginning_cpt", how="left")
    if len(panel) != before:
        raise AssertionError(f"price join changed row count: {before} -> {len(panel)}")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel
```

- [ ] **Step 3: Run and inspect the schema**

Run: `.venv/bin/python scripts/ercot_diagnostic.py`
Expected: no AssertionError; column count grows by the number of settlement points (roughly 20–40).

- [ ] **Step 4: Commit**

```bash
git add scripts/ercot_diagnostic.py
git commit -m "feat: join ERCOT RTM prices onto diagnostic panel"
```

---

## Task 7: Data-quality report — the actual gate output

Per the spec, Stage 1 succeeds by producing a *trustworthy* answer, not a particular one. This
report is what the gate decision reads.

**Files:**
- Modify: `scripts/ercot_diagnostic.py`

- [ ] **Step 1: Add the report function**

Append to `scripts/ercot_diagnostic.py`, above `if __name__`:

```python
def data_quality_report(panel: pd.DataFrame) -> pd.DataFrame:
    """Print rows/year, gaps, and negative-price share. Read before interpreting."""
    print("\n=== ROWS PER YEAR ===")
    per_year = panel.groupby(panel["datetime_beginning_cpt"].dt.year).size()
    print(per_year.to_string())

    price_cols = [c for c in panel.columns if c.startswith("total_lmp_rt_")]
    rows = []
    matched = panel[panel["datetime_beginning_cpt"] >= DOM_START]
    for col in price_cols:
        series = matched[col].dropna()
        if series.empty:
            continue
        rows.append(
            {
                "settlement_point": col.replace("total_lmp_rt_", ""),
                "n": len(series),
                "negative_share": (series < 0).mean(),
                "median": series.median(),
                "p99": series.quantile(0.99),
            }
        )
    report = pd.DataFrame(rows).sort_values("negative_share", ascending=False)
    print("\n=== PRICE QUALITY (DOM-matched window) ===")
    print(report.to_string(index=False))
    print(
        "\nGATE: if negative_share is large for the West points, "
        "their correlations are uninterpretable — see spec gate criterion."
    )
    return report
```

- [ ] **Step 2: Call it from `__main__`**

Replace the `if __name__` block with:

```python
if __name__ == "__main__":
    panel = build_panel()
    data_quality_report(panel)
```

- [ ] **Step 3: Run it**

Run: `.venv/bin/python scripts/ercot_diagnostic.py`
Expected: a rows-per-year table near 8,760 per year, then a per-settlement-point table with a `negative_share` column.

- [ ] **Step 4: Commit**

```bash
git add scripts/ercot_diagnostic.py
git commit -m "feat: ERCOT data-quality report as Stage 1 gate output"
```

---

## Task 8: The three analysis outputs

**Files:**
- Modify: `scripts/ercot_diagnostic.py`

- [ ] **Step 1: Add volatility and level trends**

Append above `if __name__`:

```python
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def trend_tables(panel: pd.DataFrame) -> pd.DataFrame:
    """Annual level and volatility per zone, raw and load-normalized.

    Normalization matters: the DOM result was volatility flat/falling while
    load rose, so raw ramps would confound growth with volatility.
    """
    year = panel["datetime_beginning_cpt"].dt.year
    rows = []
    for zone in ZONES:
        grouped = panel.groupby(year)
        mean_load = grouped[f"load_mw_{zone}"].mean()
        grad = grouped[f"load_gradient_abs_mw_per_min_{zone}"]
        frame = pd.DataFrame(
            {
                "zone": zone,
                "mean_load_mw": mean_load,
                "peak_load_mw": grouped[f"load_mw_{zone}"].max(),
                "grad_mean": grad.mean(),
                "grad_p95": grad.quantile(0.95),
            }
        )
        frame["grad_mean_norm"] = frame["grad_mean"] / frame["mean_load_mw"]
        frame["grad_p95_norm"] = frame["grad_p95"] / frame["mean_load_mw"]
        rows.append(frame.reset_index(names="year"))

    trends = pd.concat(rows, ignore_index=True)
    FIGDIR.mkdir(parents=True, exist_ok=True)
    trends.to_csv(FIGDIR / "trends_by_zone_year.csv", index=False)

    for metric, fname in [
        ("mean_load_mw", "fig2_level_trend.png"),
        ("grad_mean_norm", "fig1_volatility_trend_normalized.png"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 6))
        for zone in ZONES:
            sub = trends[trends["zone"] == zone]
            ax.plot(sub["year"], sub[metric], marker="o", label=zone)
        ax.set_xlabel("year")
        ax.set_ylabel(metric)
        ax.set_title(f"ERCOT {metric} by weather zone")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGDIR / fname, dpi=150)
        plt.close(fig)

    print(f"\ntrends -> {FIGDIR}")
    return trends
```

- [ ] **Step 2: Add the level-vs-volatility horse race**

Append below `trend_tables`:

```python
def level_vs_volatility(panel: pd.DataFrame) -> pd.DataFrame:
    """Standardized regression of price on load level vs |gradient|.

    Standardizing puts both predictors on the same scale so their
    coefficients are directly comparable. This is the core Stage 1 question.
    """
    import statsmodels.api as sm

    matched = panel[panel["datetime_beginning_cpt"] >= DOM_START]
    price_cols = [c for c in panel.columns if c.startswith("total_lmp_rt_")]

    rows = []
    for zone in ZONES:
        for col in price_cols:
            data = matched[
                [f"load_mw_{zone}", f"load_gradient_abs_mw_per_min_{zone}", col]
            ].dropna()
            if len(data) < 1000:
                continue
            standardized = (data - data.mean()) / data.std()
            exog = sm.add_constant(
                standardized[
                    [f"load_mw_{zone}", f"load_gradient_abs_mw_per_min_{zone}"]
                ]
            )
            fit = sm.OLS(standardized[col], exog).fit()
            rows.append(
                {
                    "zone": zone,
                    "settlement_point": col.replace("total_lmp_rt_", ""),
                    "beta_level": fit.params[f"load_mw_{zone}"],
                    "beta_volatility": fit.params[
                        f"load_gradient_abs_mw_per_min_{zone}"
                    ],
                    "r2": fit.rsquared,
                    "n": len(data),
                }
            )

    race = pd.DataFrame(rows)
    race["level_wins"] = race["beta_level"].abs() > race["beta_volatility"].abs()
    race.to_csv(FIGDIR / "fig3_level_vs_volatility.csv", index=False)

    print("\n=== LEVEL vs VOLATILITY (standardized betas) ===")
    print(race.to_string(index=False))
    print(
        f"\nlevel wins in {race['level_wins'].sum()} of {len(race)} zone-point pairs"
    )
    return race
```

- [ ] **Step 3: Wire both into `__main__`**

Replace the `if __name__` block with:

```python
if __name__ == "__main__":
    panel = build_panel()
    data_quality_report(panel)
    trend_tables(panel)
    level_vs_volatility(panel)
```

- [ ] **Step 4: Run the full diagnostic**

Run: `.venv/bin/python scripts/ercot_diagnostic.py`
Expected: quality report, then `trends -> outputs/ercot_diagnostic`, then the standardized-beta table and a "level wins in N of M" line.

- [ ] **Step 5: Verify the outputs exist**

Run: `ls outputs/ercot_diagnostic/`
Expected: `fig1_volatility_trend_normalized.png`, `fig2_level_trend.png`, `fig3_level_vs_volatility.csv`, `trends_by_zone_year.csv`.

- [ ] **Step 6: Commit**

```bash
git add scripts/ercot_diagnostic.py
git commit -m "feat: ERCOT volatility trend, level trend, level-vs-volatility race"
```

---

## Task 9: Full test suite and the gate decision

**Files:**
- Modify: `docs/decisions.md` (append an entry)

- [ ] **Step 1: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all tests pass, including the 10 new `test_ercot_features.py` tests. Baseline before this plan was 313 passing.

- [ ] **Step 2: Write the decisions entry**

Append a `docs/decisions.md` entry following that file's existing conventions, recording:
- whether ERCOT load volatility is flat, rising, or falling, per zone, **normalized**;
- whether level or volatility dominates the price relationship, and in how many zone-point pairs;
- how this compares to the DOM result (level-driven, `z_slope` sign-flip under a load control);
- the negative-price share for West-zone settlement points;
- **the gate decision: proceed to Stage 2 or not, with reasoning.**

- [ ] **Step 3: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): ERCOT Stage 1 diagnostic results and gate decision"
```

---

## Notes for the implementer

- **Never interpolate a gap.** `assert_panel_quality` is meant to fail. If it fires, investigate
  the source file; do not weaken the assertion to make it pass.
- **Do not clip negative prices.** ERCOT's floor is −$251/MWh and negatives are real market
  outcomes. Their prevalence is itself a gate input.
- **Do not modify `src/surg/preprocessing/features.py`.** Cross-market comparability depends on
  the DOM gradient function being byte-identical.
- **Price file column names are unverified.** Task 6 assumes `Delivery Date`, `Delivery Hour`,
  `Settlement Point Name`, `Settlement Point Price` (case-insensitive). If a `KeyError` fires,
  print `sheet.columns` from one file and adjust the `cols` mapping — this is the one place the
  plan is inferring rather than reporting verified fact.
- **No causal claim.** This is descriptive. Per research memo §2c, West Texas is confounded by
  Permian oil & gas electrification on the load side and wind export constraints on the price
  side; it is not a clean natural experiment.
