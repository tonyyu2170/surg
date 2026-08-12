# Cross-ISO Stage-1 Plan B: MISO, ISO-NE, SPP + Capstone

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the Stage-1 level-vs-volatility diagnostic on the three remaining
cross-ISO markets (MISO, ISO-NE, SPP) and produce the eight-market capstone synthesis.

**Architecture:** Each market gets three files following the Plan A pattern exactly — a
fetch script (`scripts/<mkt>_fetch.py`), a parse module
(`src/surg/preprocessing/<mkt>_features.py`) with unit tests, and a driver
(`scripts/<mkt>_diagnostic.py`) that calls the shared, already-shipped
`surg.diagnostics.stage1` API. No changes to `stage1.py` or to any Plan A market script.
The three fetch scripts come first so their downloads run in the background while the
parse modules are built against synthetic fixtures.

**Tech Stack:** Python 3.12, pandas, httpx, statsmodels, pytest, openpyxl + xlrd (both
already installed in the main venv as of Plan A Task 13).

---

## Source of truth

**`docs/sources/availability/cross-iso-phase2-recon-verification.md` (commit `ef583a0`) is authoritative for
every URL, schema, roster, and time convention in this plan.** Every structure below was
verified by downloading and reading real files on 2026-08-10. Where the Phase-1 memos
disagree, they are wrong — three of four checked memo claims have been falsified.

**Do not re-probe the endpoints.** They are recorded here and in the recon doc.

## Locked decisions (user, 2026-08-10)

1. **Zone price for nodal markets = zone-average nodal LMP.** SPP and MISO publish nodal
   prices, not zonal. SPP: mean LMP over all settlement locations whose name is prefixed
   by the zone code. MISO: node names carry **no** LRZ code, so Task 9 Step 1 resolves
   the mapping empirically with a defined hub fallback — see that task.
2. **SPP max window = 2016-01 →, 17 zones, one panel.** Avoids the 2011–2015 16-zone era
   and the 2026 RTO-West additions entirely. Conveniently matches ISO-NE's 2016 start.
3. Windows: max per market **and** the common-overlap window
   (`COMMON_OVERLAP_START` → `COMMON_OVERLAP_END`, i.e. 2023-01-01 → 2025-05-01 excl.),
   overlap being the capstone headline. Unchanged from Plan A.
4. Stage 1 uses **total price only** — no congestion decomposition. Unchanged from Plan A.

## Deviations shipped during execution (2026-08-10)

Recorded here so the plan matches what is actually on the branch.

1. **ISO-NE hour convention — plan code was wrong, fixed in `a390c68`.** Task 4's module
   asserted a uniform fixed 24-hour grid and `dst_pairs_per_year=0`. Verified against all
   11 workbooks: the convention **changes at 2024**. 2016–2023 is a fixed grid with int64
   `Hr_End`; 2024 onward is real local prevailing time with a **string** `Hr_End`, a
   25-row fall-back day marking the repeated hour `'02X'`, and a 23-row spring-forward
   day. The Phase-2 recon sampled 2016, 2023 and 2026 only, and the 2026 workbook stops at
   2026-06-30, so it never reached a November fall-back — a real sampling gap in the
   recon, not a memo error. Shipped fix: `parse_hour_ending` maps `'02X'` → hour 2 so the
   pair becomes a genuine duplicate timestamp; `build_panel` assembles zones
   **positionally** rather than merging on `TIME` (a key merge fans duplicate rows out
   combinatorially); the driver drops its `drop_duplicates(subset=[TIME])` (years never
   overlap, and it would delete half of each fall-back pair) and passes
   `dst_pairs_per_year=1`. Four tests added; `tests/test_isone_features.py` is now 10, not 6.
2. **`outputs/` is gitignored by project convention.** Tasks 7–9 Step 4 as originally
   written say `git add scripts/<mkt>_diagnostic.py outputs/<mkt>_diagnostic`, which fails
   — `.gitignore` excludes everything under `outputs/` except two `.gitkeep` files.
   Diagnostic outputs are regeneratable and stay untracked, exactly as in Plan A. **Commit
   the driver script only.** Corrected inline in Tasks 8 and 9 below.

## Standing execution rules (carried from Plan A, proven)

- **Verify plan code blocks by regex-extract + `difflib`** against the on-disk files after
  each batch, rather than spending a reviewer subagent on transcription. Scripts modelled
  on `scratchpad/verify_t2.py`. This caught all four Plan A defects at near-zero cost.
- **Paste literal pytest byte counts** and stop if the collected-test count is off.
- Always invoke `.venv/bin/python` explicitly; bare `python3` resolves to a pipless venv.
- Plain commit messages, **no trailers, no Claude attribution**.
- Commits are pre-authorised for the implementation tasks below. **Push, FF-merge, and any
  change to `main` still require their own separate user ask.**

## Disk budget

SPP is the heavy market: DA LMP annual zips 2016–2024 total **2.53 GB**, plus ~1.6 GB of
2025→2026-03-24 dailies. Budget ~4.5 GB free before starting Task 2. Raw SPP price
archives may be deleted after Task 8 writes its panel parquet; the load archives are small
(≤1.45 MB/yr) and should be kept.

---

## File Structure

| File | Responsibility |
|---|---|
| `scripts/isone_fetch.py` | Download 11 SMD annual workbooks to `data/raw/isone/` |
| `src/surg/preprocessing/isone_features.py` | Parse one workbook → wide hourly panel (load + DA LMP, 8 zones) |
| `tests/test_isone_features.py` | Unit tests, synthetic fixtures |
| `scripts/isone_diagnostic.py` | Build panel, run Stage-1, write `outputs/isone_diagnostic/` |
| `scripts/spp_fetch.py` | Download load + DA LMP annual zips and 2025→ dailies to `data/raw/spp/` |
| `src/surg/preprocessing/spp_features.py` | Era-aware load parse + nodal→zone price aggregation |
| `tests/test_spp_features.py` | Unit tests, synthetic fixtures covering the eras |
| `scripts/spp_diagnostic.py` | Build panel, run Stage-1, write `outputs/spp_diagnostic/` |
| `scripts/miso_fetch.py` | Download daily `df_al.xls` + `da_expost_lmp.csv` to `data/raw/miso/` |
| `src/surg/preprocessing/miso_features.py` | Parse 7-day load workbook + wide hourly LMP |
| `tests/test_miso_features.py` | Unit tests, synthetic fixtures |
| `scripts/miso_diagnostic.py` | Build panel, run Stage-1, write `outputs/miso_diagnostic/` |
| `docs/decisions.md` | Capstone entry (Task 10) |

Shared API used by all three drivers, already shipped in
`src/surg/diagnostics/stage1.py` — **do not modify**:

```text
add_zone_gradients(df, zones, *, time_col) -> pd.DataFrame
assert_panel_quality(panel, zones, *, time_col, dst_pairs_per_year=1) -> None
data_quality_report(panel, price_cols, *, time_col, window_start, figdir) -> pd.DataFrame
trend_tables(panel, zones, *, time_col, figdir, market) -> pd.DataFrame
level_vs_volatility(panel, zones, price_cols, *, time_col, window_start, window_end,
                    figdir, market, label, min_rows=1000) -> pd.DataFrame
COMMON_OVERLAP_START  # 2023-01-01
COMMON_OVERLAP_END    # 2025-05-01, exclusive
```

Panel contract every driver must satisfy: `time_col` is naive local hour-**beginning**;
one `load_mw_<zone>` column per zone; a bool `dst_transition_hour` column.

---

## Task 1: ISO-NE fetch script

**Files:**
- Create: `scripts/isone_fetch.py`
- Test: `tests/test_isone_fetch.py`

ISO-NE switched from dated folders to numeric document-ids after 2023. The three numeric
ids are **verified constants, not a derivable pattern** — a formula prediction was off by
one for all three. Hard-code the table.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_isone_fetch.py
from __future__ import annotations

from scripts.isone_fetch import URLS, target_path


def test_urls_cover_2016_through_2026():
    assert sorted(URLS) == list(range(2016, 2027))


def test_2016_is_xls_and_others_are_xlsx():
    assert URLS[2016].endswith(".xls")
    for year in range(2017, 2027):
        assert URLS[year].endswith(".xlsx")


def test_numeric_document_ids_are_verified_constants():
    assert "/100008/" in URLS[2024]
    assert "/100020/" in URLS[2025]
    assert "/100032/" in URLS[2026]


def test_target_path_keeps_the_source_extension(tmp_path):
    assert target_path(tmp_path, 2016).name == "2016_smd_hourly.xls"
    assert target_path(tmp_path, 2023).name == "2023_smd_hourly.xlsx"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_isone_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.isone_fetch'`

- [ ] **Step 3: Write the fetch script**

```python
# scripts/isone_fetch.py
"""Download ISO-NE SMD hourly annual workbooks.

Usage: .venv/bin/python scripts/isone_fetch.py

One workbook per year carries load, decomposed DA/RT LMP and weather for all
eight load zones, so Stage 1 needs 11 files (~85 MB) rather than the ~1,400
daily WW_DALMP_ISO CSVs the Phase-1 memo budgeted. See
docs/sources/availability/cross-iso-phase2-recon-verification.md section 2.

The numeric document ids for 2024-2026 are verified constants: ISO-NE moved off
dated folders after 2023 and the ids are not reliably derivable.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

BASE = "https://www.iso-ne.com/static-assets/documents"
RAW = Path("data/raw/isone")
SLEEP_S = 2.0

URLS: dict[int, str] = {
    2016: f"{BASE}/2016/02/smd_hourly.xls",
    2017: f"{BASE}/2017/02/2017_smd_hourly.xlsx",
    2018: f"{BASE}/2018/02/2018_smd_hourly.xlsx",
    2019: f"{BASE}/2019/02/2019_smd_hourly.xlsx",
    2020: f"{BASE}/2020/02/2020_smd_hourly.xlsx",
    2021: f"{BASE}/2021/02/2021_smd_hourly.xlsx",
    2022: f"{BASE}/2022/02/2022_smd_hourly.xlsx",
    2023: f"{BASE}/2023/02/2023_smd_hourly.xlsx",
    2024: f"{BASE}/100008/2024_smd_hourly.xlsx",
    2025: f"{BASE}/100020/2025_smd_hourly.xlsx",
    2026: f"{BASE}/100032/2026_smd_hourly.xlsx",
}

FAILED: list[str] = []


def target_path(root: Path, year: int) -> Path:
    suffix = ".xls" if URLS[year].endswith(".xls") else ".xlsx"
    return root / f"{year}_smd_hourly{suffix}"


def is_excel(payload: bytes) -> bool:
    """xlsx is a zip (PK); xls is an OLE2 compound file."""
    return payload[:2] == b"PK" or payload[:4] == b"\xd0\xcf\x11\xe0"


def pull(client: httpx.Client, year: int, out: Path) -> None:
    """Fetch one workbook, retrying transport failures as well as bad responses.

    Never send a Range header to this host: ranged requests return non-Excel
    content (verified 2026-08-10).
    """
    if out.exists() and out.stat().st_size > 0:
        print(f"  {out.name} already present", flush=True)
        return
    for attempt in range(5):
        wait = 15 * (attempt + 1)
        try:
            resp = client.get(URLS[year], timeout=180.0)
        except httpx.HTTPError as exc:
            print(f"  retry {out.name}: {type(exc).__name__}; sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        if resp.status_code == 200 and is_excel(resp.content):
            out.write_bytes(resp.content)
            print(f"  {out.name} ({len(resp.content)//1024} KB)", flush=True)
            time.sleep(SLEEP_S)
            return
        print(
            f"  retry {out.name}: HTTP {resp.status_code}, "
            f"excel={is_excel(resp.content)}; sleeping {wait}s",
            flush=True,
        )
        time.sleep(wait)
    FAILED.append(out.name)
    print(f"  GAVE UP on {out.name} - continuing", flush=True)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "surg-research/1.0 (academic research)"}
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for year in sorted(URLS):
            pull(client, year, target_path(RAW, year))
    if FAILED:
        print(f"\n=== {len(FAILED)} WORKBOOKS NEVER FETCHED - rerun to retry ===", flush=True)
        for name in FAILED:
            print(f"  {name}", flush=True)
    else:
        print(f"\nall {len(URLS)} workbooks present under {RAW}", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_isone_fetch.py -v`
Expected: PASS, 4 passed

- [ ] **Step 5: Launch the fetch in the background**

```bash
nohup caffeinate -i .venv/bin/python scripts/isone_fetch.py >> ~/isone-fetch.log 2>&1 &
```

Expected: 11 downloads, a few minutes total. Check with `tail -5 ~/isone-fetch.log`.
Do not block on it — continue to Task 2.

- [ ] **Step 6: Commit**

```bash
git add scripts/isone_fetch.py tests/test_isone_fetch.py
git commit -m "feat(isone): SMD annual workbook fetch script"
```

---

## Task 2: SPP fetch script

**Files:**
- Create: `scripts/spp_fetch.py`
- Test: `tests/test_spp_fetch.py`

Two eras per series (recon doc §3): annual zips through 2024, dailies from 2025. Load and
DA LMP share the same boundary.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spp_fetch.py
from __future__ import annotations

import pandas as pd

from scripts.spp_fetch import (
    DAILY_ERA_START, MAX_START, PANEL_END, daily_dates, daily_url, zip_url,
)


def test_zip_url_shape():
    assert zip_url("hourly-load", 2019) == (
        "https://portal.spp.org/file-browser-api/download/hourly-load"
        "?path=/2019/2019.zip"
    )


def test_daily_load_url_shape():
    url = daily_url("hourly-load", pd.Timestamp("2025-08-06"))
    assert url.endswith("?path=/2025/DAILY_HOURLY_LOAD-20250806.csv")


def test_daily_price_url_shape():
    url = daily_url("da-lmp-by-settlement-location", pd.Timestamp("2025-08-06"))
    assert url.endswith("?path=/2025/08/By_Day/DA-LMP-SL-202508060100.csv")


def test_daily_dates_span_the_daily_era_only():
    dates = daily_dates()
    assert dates[0] == DAILY_ERA_START
    assert dates[-1] <= PANEL_END


def test_window_constants_match_the_locked_decision():
    assert MAX_START == pd.Timestamp("2016-01-01")
    assert PANEL_END == pd.Timestamp("2026-03-24")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_spp_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.spp_fetch'`

- [ ] **Step 3: Write the fetch script**

```python
# scripts/spp_fetch.py
"""Download SPP hourly load and DA LMP archives.

Usage: .venv/bin/python scripts/spp_fetch.py

Two eras per series (docs/sources/availability/cross-iso-phase2-recon-verification.md section 3):
  * 2016-2024: one annual zip per year at ?path=/{YYYY}/{YYYY}.zip
  * 2025 ->  : daily CSVs; no annual zip exists (404 verified)

The panel stops at 2026-03-24, the last day before the wide->long schema break
and the RTO-West roster jump, per the locked 17-zone single-panel decision.

Disk: DA LMP annual zips 2016-2024 total ~2.53 GB; the daily era adds ~1.6 GB.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

BASE = "https://portal.spp.org/file-browser-api/download"
RAW = Path("data/raw/spp")
SLEEP_S = 1.0

MAX_START = pd.Timestamp("2016-01-01")
DAILY_ERA_START = pd.Timestamp("2025-01-01")
PANEL_END = pd.Timestamp("2026-03-24")  # inclusive last day, pre-schema-break

LOAD = "hourly-load"
PRICE = "da-lmp-by-settlement-location"

FAILED: list[str] = []


def zip_url(fileset: str, year: int) -> str:
    return f"{BASE}/{fileset}?path=/{year}/{year}.zip"


def daily_url(fileset: str, day: pd.Timestamp) -> str:
    if fileset == LOAD:
        path = f"/{day:%Y}/DAILY_HOURLY_LOAD-{day:%Y%m%d}.csv"
    else:
        path = f"/{day:%Y}/{day:%m}/By_Day/DA-LMP-SL-{day:%Y%m%d}0100.csv"
    return f"{BASE}/{fileset}?path={path}"


def daily_dates() -> list[pd.Timestamp]:
    return list(pd.date_range(DAILY_ERA_START, PANEL_END, freq="D"))


def pull(client: httpx.Client, url: str, out: Path, *, expect_zip: bool) -> None:
    """Fetch one artifact, retrying transport failures as well as bad responses."""
    if out.exists() and out.stat().st_size > 0:
        return
    for attempt in range(5):
        wait = 20 * (attempt + 1)
        try:
            resp = client.get(url, timeout=600.0)
        except httpx.HTTPError as exc:
            print(f"  retry {out.name}: {type(exc).__name__}; sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        ok = resp.status_code == 200 and len(resp.content) > 0
        if ok and expect_zip:
            ok = resp.content[:2] == b"PK"
        if ok:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(resp.content)
            print(f"  {out.name} ({len(resp.content)//1024} KB)", flush=True)
            time.sleep(SLEEP_S)
            return
        print(f"  retry {out.name}: HTTP {resp.status_code}; sleeping {wait}s", flush=True)
        time.sleep(wait)
    FAILED.append(out.name)
    print(f"  GAVE UP on {out.name} - continuing", flush=True)


def main() -> None:
    headers = {"User-Agent": "surg-research/1.0 (academic research)"}
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for fileset, tag in [(LOAD, "load"), (PRICE, "price")]:
            for year in range(MAX_START.year, DAILY_ERA_START.year):
                out = RAW / tag / "zips" / f"{year}.zip"
                pull(client, zip_url(fileset, year), out, expect_zip=True)
            for day in daily_dates():
                name = (
                    f"DAILY_HOURLY_LOAD-{day:%Y%m%d}.csv"
                    if fileset == LOAD
                    else f"DA-LMP-SL-{day:%Y%m%d}0100.csv"
                )
                out = RAW / tag / "daily" / name
                pull(client, daily_url(fileset, day), out, expect_zip=False)

    if FAILED:
        print(f"\n=== {len(FAILED)} SPP FILES NEVER FETCHED - rerun to retry ===", flush=True)
        for name in FAILED:
            print(f"  {name}", flush=True)
    else:
        print(f"\nSPP fetch complete under {RAW}", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_spp_fetch.py -v`
Expected: PASS, 5 passed

- [ ] **Step 5: Launch the fetch in the background**

```bash
nohup caffeinate -i .venv/bin/python scripts/spp_fetch.py >> ~/spp-fetch.log 2>&1 &
```

Expected: ~4.2 GB across 18 zips, ~450 load dailies and ~450 price dailies. Several hours.
Do not block on it — continue to Task 3.

- [ ] **Step 6: Commit**

```bash
git add scripts/spp_fetch.py tests/test_spp_fetch.py
git commit -m "feat(spp): annual-zip and daily archive fetch script"
```

---

## Task 3: MISO fetch script

**Files:**
- Create: `scripts/miso_fetch.py`
- Test: `tests/test_miso_fetch.py`

Each `{YYYYMMDD}_df_al.xls` covers a **7-day reporting period** but carries `ActualLoad`
for exactly **one** market day — the day before publication. Daily fetching is therefore
required; the parser drops the six forecast-only days.

⚠️ **Never POST to `misoenergy.org/api/find/...`** — it is an Elasticsearch write
endpoint. This script only GETs `docs.misoenergy.org/marketreports/`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_miso_fetch.py
from __future__ import annotations

import pandas as pd

from scripts.miso_fetch import MAX_START, family_url, market_days


def test_load_url_shape():
    assert family_url("df_al", pd.Timestamp("2023-01-03")) == (
        "https://docs.misoenergy.org/marketreports/20230103_df_al.xls"
    )


def test_price_url_shape():
    assert family_url("da_expost_lmp", pd.Timestamp("2025-08-06")) == (
        "https://docs.misoenergy.org/marketreports/20250806_da_expost_lmp.csv"
    )


def test_market_days_start_at_the_stage1_window():
    assert market_days()[0] == MAX_START
    assert MAX_START == pd.Timestamp("2023-01-01")


def test_market_days_are_contiguous_daily():
    days = pd.Series(market_days())
    assert (days.diff().dropna() == pd.Timedelta(days=1)).all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_miso_fetch.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.miso_fetch'`

- [ ] **Step 3: Write the fetch script**

```python
# scripts/miso_fetch.py
"""Download MISO daily load and DA ex-post LMP reports.

Usage: .venv/bin/python scripts/miso_fetch.py

Retention on docs.misoenergy.org/marketreports is current + 3 calendar years,
so the Stage-1 window (2023-01 ->) is inside it. Each df_al.xls covers a 7-day
reporting period but carries ActualLoad for only the single day before
publication, so every market day needs its own file.

NEVER POST to misoenergy.org/api/find/... - it is an Elasticsearch write
endpoint. This script only issues GETs.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

BASE = "https://docs.misoenergy.org/marketreports"
RAW = Path("data/raw/miso")
SLEEP_S = 0.5

MAX_START = pd.Timestamp("2023-01-01")
SUFFIX = {"df_al": "xls", "da_expost_lmp": "csv"}

FAILED: list[str] = []


def family_url(family: str, day: pd.Timestamp) -> str:
    return f"{BASE}/{day:%Y%m%d}_{family}.{SUFFIX[family]}"


def market_days() -> list[pd.Timestamp]:
    """Every day from the Stage-1 start through yesterday."""
    end = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
    return list(pd.date_range(MAX_START, end, freq="D"))


def pull(client: httpx.Client, family: str, day: pd.Timestamp) -> None:
    out = RAW / family / f"{day:%Y%m%d}_{family}.{SUFFIX[family]}"
    if out.exists() and out.stat().st_size > 0:
        return
    url = family_url(family, day)
    for attempt in range(4):
        wait = 15 * (attempt + 1)
        try:
            resp = client.get(url, timeout=120.0)
        except httpx.HTTPError as exc:
            print(f"  retry {out.name}: {type(exc).__name__}; sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        if resp.status_code == 200 and len(resp.content) > 1000:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(resp.content)
            time.sleep(SLEEP_S)
            return
        if resp.status_code == 404:
            FAILED.append(f"{out.name} (404)")
            return
        print(f"  retry {out.name}: HTTP {resp.status_code}; sleeping {wait}s", flush=True)
        time.sleep(wait)
    FAILED.append(out.name)
    print(f"  GAVE UP on {out.name} - continuing", flush=True)


def main() -> None:
    headers = {"User-Agent": "surg-research/1.0 (academic research)"}
    days = market_days()
    print(f"fetching {len(days)} market days x 2 families", flush=True)
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for family in SUFFIX:
            for i, day in enumerate(days, 1):
                pull(client, family, day)
                if i % 100 == 0:
                    print(f"  {family}: {i}/{len(days)}", flush=True)

    if FAILED:
        print(f"\n=== {len(FAILED)} MISO FILES NEVER FETCHED ===", flush=True)
        for name in FAILED:
            print(f"  {name}", flush=True)
    else:
        print(f"\nMISO fetch complete under {RAW}", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_miso_fetch.py -v`
Expected: PASS, 4 passed

- [ ] **Step 5: Launch the fetch in the background**

```bash
nohup caffeinate -i .venv/bin/python scripts/miso_fetch.py >> ~/miso-fetch.log 2>&1 &
```

Expected: ~1,300 days × 2 families ≈ 2,600 files, a few hours. Continue to Task 4.

- [ ] **Step 6: Commit**

```bash
git add scripts/miso_fetch.py tests/test_miso_fetch.py
git commit -m "feat(miso): daily load and DA ex-post LMP fetch script"
```

---

## Task 4: ISO-NE parse module

**Files:**
- Create: `src/surg/preprocessing/isone_features.py`
- Test: `tests/test_isone_features.py`

Workbook structure (verified identical in 2016, 2023, 2026): sheets `Notes`, `ISO NE CA`,
then the eight zone sheets. Each zone sheet has columns `Date, Hr_End, DA_Demand,
RT_Demand, DA_LMP, DA_EC, DA_CC, DA_MLC, RT_LMP, RT_EC, RT_CC, RT_MLC, Dry_Bulb,
Dew_Point`, with `Hr_End` an int 1–24 and exactly 24 rows per calendar day — including
both DST transition days. Load = `RT_Demand` (metered actual). Price = `DA_LMP` (total).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_isone_features.py
from __future__ import annotations

import pandas as pd
import pytest

from surg.preprocessing.isone_features import SHEETS, ZONES, build_panel, parse_smd_sheet


def _sheet(day: str = "2023-06-15", hours: int = 24) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": [pd.Timestamp(day)] * hours,
            "Hr_End": list(range(1, hours + 1)),
            "DA_Demand": [900.0 + h for h in range(hours)],
            "RT_Demand": [1000.0 + h for h in range(hours)],
            "DA_LMP": [30.0 + h for h in range(hours)],
            "DA_CC": [0.0] * hours,
        }
    )


def test_zone_list_and_sheet_names():
    assert ZONES == ["me", "nh", "vt", "ct", "ri", "sema", "wcma", "nema"]
    assert SHEETS["me"] == "ME"
    assert SHEETS["sema"] == "SEMA"


def test_parse_converts_hour_ending_to_hour_beginning():
    out = parse_smd_sheet(_sheet(), "me")
    assert out["datetime_beginning_ept"].iloc[0] == pd.Timestamp("2023-06-15 00:00")
    assert out["datetime_beginning_ept"].iloc[-1] == pd.Timestamp("2023-06-15 23:00")


def test_parse_uses_rt_demand_for_load_and_da_lmp_for_price():
    out = parse_smd_sheet(_sheet(), "me")
    assert out["load_mw_me"].iloc[0] == 1000.0
    assert out["da_lmp_me"].iloc[0] == 30.0


def test_parse_rejects_hour_outside_1_to_24():
    bad = _sheet()
    bad.loc[0, "Hr_End"] = 25
    with pytest.raises(ValueError, match="Hr_End"):
        parse_smd_sheet(bad, "me")


def test_build_panel_merges_zones_and_flags_no_dst():
    panel = build_panel({z: _sheet() for z in ZONES})
    assert len(panel) == 24
    assert not panel["dst_transition_hour"].any()
    for zone in ZONES:
        assert f"load_mw_{zone}" in panel.columns
        assert f"da_lmp_{zone}" in panel.columns


def test_build_panel_rejects_a_zone_with_a_different_time_index():
    frames = {z: _sheet() for z in ZONES}
    frames["nh"] = _sheet(hours=23)
    with pytest.raises(ValueError, match="time index"):
        build_panel(frames)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_isone_features.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.preprocessing.isone_features'`

- [ ] **Step 3: Write the parse module**

```python
# src/surg/preprocessing/isone_features.py
"""Parse ISO-NE SMD hourly annual workbooks into a Stage-1 panel.

One workbook per year carries load, decomposed DA/RT LMP and weather for all
eight load zones. Verified structure (2016, 2023, 2026 all identical) is
recorded in docs/sources/availability/cross-iso-phase2-recon-verification.md section 2.

Time convention: the workbook is a fixed 24-hour-per-day grid - both DST
transition days carry exactly 24 rows, and a full non-leap year is 8760 rows.
There is therefore no fall-back pair to flag, and drivers must call
assert_panel_quality with dst_pairs_per_year=0.

Load is RT_Demand (metered actual), not DA_Demand (day-ahead cleared).
Stage 1 uses the total DA_LMP only; the decomposition columns are left in the
workbook for any later work.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TIME = "datetime_beginning_ept"

SHEETS: dict[str, str] = {
    "me": "ME",
    "nh": "NH",
    "vt": "VT",
    "ct": "CT",
    "ri": "RI",
    "sema": "SEMA",
    "wcma": "WCMA",
    "nema": "NEMA",
}
ZONES: list[str] = list(SHEETS)


def parse_smd_sheet(raw: pd.DataFrame, zone: str) -> pd.DataFrame:
    """One zone sheet -> [TIME, load_mw_<zone>, da_lmp_<zone>], hour-beginning."""
    hours = pd.to_numeric(raw["Hr_End"], errors="coerce")
    if not hours.between(1, 24).all():
        raise ValueError(f"{zone}: Hr_End outside 1..24")

    dates = pd.to_datetime(raw["Date"])
    out = pd.DataFrame(
        {
            TIME: dates + pd.to_timedelta(hours - 1, unit="h"),
            f"load_mw_{zone}": pd.to_numeric(raw["RT_Demand"], errors="coerce"),
            f"da_lmp_{zone}": pd.to_numeric(raw["DA_LMP"], errors="coerce"),
        }
    )
    return out.sort_values(TIME).reset_index(drop=True)


def build_panel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merge per-zone sheets on the shared time index.

    Every zone must share an identical time index; a mismatch means one sheet
    is short or misaligned and is raised rather than silently outer-joined.
    """
    panel: pd.DataFrame | None = None
    for zone in ZONES:
        parsed = parse_smd_sheet(frames[zone], zone)
        if panel is None:
            panel = parsed
            continue
        if not parsed[TIME].equals(panel[TIME]):
            raise ValueError(f"{zone}: time index differs from the first zone")
        panel = panel.merge(parsed, on=TIME, how="left", validate="1:1")

    assert panel is not None
    panel["dst_transition_hour"] = False
    return panel.sort_values(TIME).reset_index(drop=True)


def read_workbook(path: Path) -> dict[str, pd.DataFrame]:
    """Read the eight zone sheets from one annual workbook."""
    engine = "xlrd" if path.suffix == ".xls" else "openpyxl"
    book = pd.ExcelFile(path, engine=engine)
    return {zone: book.parse(SHEETS[zone]) for zone in ZONES}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_isone_features.py -v`
Expected: PASS, 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/isone_features.py tests/test_isone_features.py
git commit -m "feat(isone): SMD workbook parse module"
```

---

## Task 5: SPP parse module

**Files:**
- Create: `src/surg/preprocessing/spp_features.py`
- Test: `tests/test_spp_features.py`

This is the most trap-dense module in the plan. Implement from the recon doc's era table,
not from independent conditionals:

| Era | Source | Format | Zones | Sum CF+NC? | Datetime |
|---|---|---|---|---|---|
| 2016 – 2024 | annual zip, **monthlies only** | wide | 17 | n/a | `M/D/YY H:MM` or `MM/DD/YYYY HH:MM:SS` |
| 2025-01 – 2026-03-24 | dailies | wide | 17 | n/a | `MM/DD/YYYY HH:MM:SS` |
| 2026-03-25 → (excluded by the locked decision) | dailies | long | 20 | **yes** | `MM/DD/YYYY HH:MM:SS` |

Four traps this module must defuse:
1. Annual zips contain **both** dailies and 12 monthly rollups — globbing double-counts.
2. Header whitespace drift — column names must be stripped.
3. Datetime format drift — must be inferred, never hard-coded.
4. `MarketHour` is **GMT hour-ending**; one file is one *local* Central day (23/24/25
   rows). Converting to local prevailing time produces one fall-back duplicate pair per
   year, so SPP uses `dst_pairs_per_year=1`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_spp_features.py
from __future__ import annotations

import pandas as pd

from surg.preprocessing.spp_features import (
    TIME, ZONES, gmt_hour_ending_to_local_beginning, monthly_members,
    parse_wide_load, zone_price_from_nodal,
)


def _wide(stamps: list[str]) -> pd.DataFrame:
    data: dict[str, list] = {"MarketHour": stamps}
    for zone in ZONES:
        data[f" {zone}"] = [100.0 + i for i in range(len(stamps))]
    return pd.DataFrame(data)


def test_zone_roster_is_the_locked_seventeen():
    assert len(ZONES) == 17
    assert "WAUE" in ZONES
    for absent in ("PRPA", "WACM", "WAUW", "PSCO"):
        assert absent not in ZONES


def test_gmt_hour_ending_converts_to_local_hour_beginning():
    # 06:00Z hour-ending == hour beginning 00:00 CDT on an ordinary summer day
    got = gmt_hour_ending_to_local_beginning(pd.Series(["08/06/2025 06:00:00"]))
    assert got.iloc[0] == pd.Timestamp("2025-08-06 00:00")


def test_fall_back_day_yields_twenty_five_rows_with_a_duplicate_pair():
    stamps = [f"11/02/2025 {h:02d}:00:00" for h in range(6, 24)]
    stamps += [f"11/03/2025 {h:02d}:00:00" for h in range(0, 7)]
    out = parse_wide_load(_wide(stamps))
    assert len(out) == 25
    assert out["dst_transition_hour"].sum() == 2


def test_parse_strips_header_whitespace():
    out = parse_wide_load(_wide(["08/06/2025 06:00:00"]))
    assert f"load_mw_{ZONES[0]}" in out.columns


def test_parse_handles_the_two_digit_year_format():
    out = parse_wide_load(_wide(["1/1/11 7:00"]))
    assert out[TIME].iloc[0] == pd.Timestamp("2011-01-01 00:00")


def test_zone_price_averages_nodes_by_prefix():
    nodal = pd.DataFrame(
        {
            TIME: [pd.Timestamp("2025-08-06 00:00")] * 3,
            "location": ["CSWS.A", "CSWS.B", "EDE.A"],
            "lmp": [10.0, 20.0, 99.0],
        }
    )
    out = zone_price_from_nodal(nodal, ["CSWS", "EDE"])
    assert out["da_lmp_CSWS"].iloc[0] == 15.0
    assert out["da_lmp_EDE"].iloc[0] == 99.0


def test_monthly_members_excludes_dailies():
    names = [
        "2023/HOURLY_LOAD-202301.csv",
        "2023/DAILY_HOURLY_LOAD-20230101.csv",
        "2023/",
    ]
    assert monthly_members(names) == ["2023/HOURLY_LOAD-202301.csv"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_spp_features.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.preprocessing.spp_features'`

- [ ] **Step 3: Write the parse module**

```python
# src/surg/preprocessing/spp_features.py
"""Parse SPP hourly load and nodal DA LMP into a Stage-1 panel.

Every structure here was verified against real files on 2026-08-10; see
docs/sources/availability/cross-iso-phase2-recon-verification.md section 3 for the era table and the
evidence behind each guard.

Four traps this module exists to defuse:
  1. Annual zips carry BOTH daily files and 12 monthly rollups covering the same
     hours. `monthly_members` keeps only the monthlies, which are the one family
     present in every archived year.
  2. Header whitespace drift: 2011-2014 have no space after commas, 2015+ do.
  3. Datetime format drift: early monthlies use '1/1/11 7:00', dailies use
     '11/22/2023 07:00:00'. Formats are inferred, never hard-coded.
  4. `MarketHour` is GMT hour-ENDING while one file spans one LOCAL Central day
     (23/24/25 rows). Converting to local prevailing time leaves one fall-back
     duplicate pair per year, so drivers pass dst_pairs_per_year=1.
"""
from __future__ import annotations

import re

import pandas as pd

TIME = "datetime_beginning_cpt"
LOCAL_TZ = "America/Chicago"

# Locked 17-zone roster: the stable footprint from the Oct-2015 Integrated
# System join through the 2026-03-24 schema break. The RTO-West additions
# (PRPA, WACM, WAUW, PSCO) are deliberately excluded.
ZONES: list[str] = [
    "CSWS", "EDE", "GRDA", "INDN", "KACY", "KCPL", "LES", "MPS", "NPPD",
    "OKGE", "OPPD", "SECI", "SPRM", "SPS", "WAUE", "WFEC", "WR",
]

_MONTHLY = re.compile(r"/HOURLY_LOAD-\d{6}\.csv$")


def monthly_members(names: list[str]) -> list[str]:
    """Monthly rollups only - never the dailies that share the same zip."""
    return sorted(n for n in names if _MONTHLY.search(n))


def gmt_hour_ending_to_local_beginning(stamps: pd.Series) -> pd.Series:
    """GMT hour-ending -> naive local Central hour-beginning.

    Subtracting one hour turns hour-ending into hour-beginning; converting to
    America/Chicago and dropping the offset yields the naive local clock the
    Stage-1 panel contract requires.
    """
    parsed = pd.to_datetime(stamps, format="mixed", utc=True)
    beginning = parsed - pd.Timedelta(hours=1)
    return beginning.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)


def parse_wide_load(raw: pd.DataFrame) -> pd.DataFrame:
    """Wide-era load file -> [TIME, load_mw_<zone>..., dst_transition_hour]."""
    frame = raw.copy()
    frame.columns = [str(c).strip() for c in frame.columns]

    missing = [z for z in ZONES if z not in frame.columns]
    if missing:
        raise ValueError(f"wide load file missing zones: {missing}")

    out = pd.DataFrame({TIME: gmt_hour_ending_to_local_beginning(frame["MarketHour"])})
    for zone in ZONES:
        out[f"load_mw_{zone}"] = pd.to_numeric(frame[zone], errors="coerce")

    out = out.sort_values(TIME).reset_index(drop=True)
    out["dst_transition_hour"] = out[TIME].duplicated(keep=False)
    return out


def parse_long_load(raw: pd.DataFrame) -> pd.DataFrame:
    """Long-era load file (2026-03-25 ->). Sums CF + NC per (hour, zone).

    Seven zones carry both a CF and an NC row; the wide era's single column
    equals their sum, so summing is what keeps the two eras on one level.
    Retained for completeness - the locked 17-zone panel stops before this era.
    """
    frame = raw.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    for col in ("Control Zone Name", "Forecast Area Type"):
        frame[col] = frame[col].astype(str).str.strip()

    frame[TIME] = gmt_hour_ending_to_local_beginning(frame["Market Hour"])
    summed = frame.groupby([TIME, "Control Zone Name"])["Load MW"].sum().unstack()
    summed = summed.reindex(columns=ZONES)
    summed.columns = [f"load_mw_{z}" for z in summed.columns]

    out = summed.reset_index().sort_values(TIME).reset_index(drop=True)
    out["dst_transition_hour"] = out[TIME].duplicated(keep=False)
    return out


def zone_price_from_nodal(nodal: pd.DataFrame, zones: list[str]) -> pd.DataFrame:
    """Zone price = unweighted mean of nodal LMPs whose name starts with the code.

    This is an explicit estimator choice (locked 2026-08-10): SPP publishes no
    zonal price, only ~1,222 settlement locations, and only 11 of 17 zones have
    any hub - those being vintage-tagged commercial hubs, not clean proxies.
    It is NOT a load-weighted settlement price and must be disclosed as such.
    """
    frame = nodal.copy()
    frame["location"] = frame["location"].astype(str).str.strip()

    out: pd.DataFrame | None = None
    for zone in zones:
        member = frame[frame["location"].str.upper().str.startswith(zone.upper())]
        if member.empty:
            continue
        mean = member.groupby(TIME)["lmp"].mean().rename(f"da_lmp_{zone}").reset_index()
        out = mean if out is None else out.merge(mean, on=TIME, how="outer")

    if out is None:
        raise ValueError("no nodal locations matched any zone prefix")
    return out.sort_values(TIME).reset_index(drop=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_spp_features.py -v`
Expected: PASS, 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/spp_features.py tests/test_spp_features.py
git commit -m "feat(spp): era-aware load parse and nodal-to-zone price aggregation"
```

---

## Task 6: MISO parse module

**Files:**
- Create: `src/surg/preprocessing/miso_features.py`
- Test: `tests/test_miso_features.py`

Verified layouts:

- **`df_al.xls`** — `Sheet1`, header on row index 4, 16 columns:
  `Market Day, HourEnding, LRZ1 MTLF (MWh), LRZ1 ActualLoad (MWh), LRZ2_7 …, LRZ3_5 …,
  LRZ4 …, LRZ6 …, LRZ8_9_10 …, MISO MTLF (MWh), MISO ActualLoad (MWh)`. Row index 5 is a
  spurious date-label row. The file spans 7 market days but only one carries `ActualLoad`.
- **`da_expost_lmp.csv`** — header on row index 4: `Node, Type, Value, HE 1 … HE 24`
  (wide by hour). `Type` ∈ {`Gennode`, `Loadzone`, `Hub`, `Interface`}; `Value` selects
  LMP vs its components. All hours are fixed **EST**, hour-ending, no DST rows →
  `dst_pairs_per_year=0`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_miso_features.py
from __future__ import annotations

import pandas as pd

from surg.preprocessing.miso_features import (
    TIME, ZONES, parse_da_expost_lmp, parse_df_al,
)


def _df_al_raw() -> pd.DataFrame:
    header = ["Market Day", "HourEnding"]
    for zone in ZONES + ["MISO"]:
        header += [f"{zone} MTLF (MWh)", f"{zone} ActualLoad (MWh)"]
    rows: list[list] = [
        ["FORECASTED AND"] + [None] * 15,
        ["ACTUAL LOAD REPORT"] + [None] * 15,
        ["Published Date:", pd.Timestamp("2023-01-03")] + [None] * 14,
        ["Reporting Period:", pd.Timestamp("2023-01-02")] + [None] * 14,
        header,
        ["January 02, 2023"] + [None] * 15,
    ]
    for hour in range(1, 25):
        row: list = [pd.Timestamp("2023-01-02"), hour]
        for _ in ZONES + ["MISO"]:
            row += [1000.0 + hour, 900.0 + hour]
        rows.append(row)
    for hour in range(1, 25):  # forecast-only day: ActualLoad blank
        row = [pd.Timestamp("2023-01-03"), hour]
        for _ in ZONES + ["MISO"]:
            row += [1000.0 + hour, None]
        rows.append(row)
    return pd.DataFrame(rows)


def test_zone_groups_are_the_six_lrz_groups():
    assert ZONES == ["LRZ1", "LRZ2_7", "LRZ3_5", "LRZ4", "LRZ6", "LRZ8_9_10"]


def test_parse_df_al_keeps_only_actual_load_days():
    out = parse_df_al(_df_al_raw())
    assert len(out) == 24
    assert out[TIME].dt.date.nunique() == 1


def test_parse_df_al_converts_hour_ending_to_hour_beginning():
    out = parse_df_al(_df_al_raw())
    assert out[TIME].iloc[0] == pd.Timestamp("2023-01-02 00:00")
    assert out[TIME].iloc[-1] == pd.Timestamp("2023-01-02 23:00")


def test_parse_df_al_uses_actual_not_forecast():
    out = parse_df_al(_df_al_raw())
    assert out["load_mw_LRZ1"].iloc[0] == 901.0


def test_parse_df_al_flags_no_dst():
    assert not parse_df_al(_df_al_raw())["dst_transition_hour"].any()


def _lmp_raw() -> pd.DataFrame:
    header = ["Node", "Type", "Value"] + [f"HE {h}" for h in range(1, 25)]
    rows: list[list] = [
        ["Day Ahead Market ExPost LMPs"] + [None] * 26,
        ["01/03/2023"] + [None] * 26,
        [None] * 27,
        [None, None, None, "All Hours-Ending are Eastern Standard Time (EST)"] + [None] * 23,
        header,
        ["MINN.HUB", "Hub", "LMP"] + [20.0 + h for h in range(24)],
        ["MINN.HUB", "Hub", "MCC"] + [1.0] * 24,
        ["AECI", "Interface", "LMP"] + [30.0] * 24,
    ]
    return pd.DataFrame(rows)


def test_parse_lmp_keeps_only_total_lmp_rows():
    out = parse_da_expost_lmp(_lmp_raw(), pd.Timestamp("2023-01-03"))
    assert set(out["node"]) == {"MINN.HUB", "AECI"}
    assert len(out) == 48


def test_parse_lmp_is_hour_beginning_est():
    out = parse_da_expost_lmp(_lmp_raw(), pd.Timestamp("2023-01-03"))
    first = out[out["node"] == "MINN.HUB"].sort_values(TIME)
    assert first[TIME].iloc[0] == pd.Timestamp("2023-01-03 00:00")
    assert first["lmp"].iloc[0] == 20.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_miso_features.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.preprocessing.miso_features'`

- [ ] **Step 3: Write the parse module**

```python
# src/surg/preprocessing/miso_features.py
"""Parse MISO daily load and DA ex-post LMP reports into a Stage-1 panel.

Verified layouts (2023-01-03 and 2025-08-06) are recorded in
docs/sources/availability/cross-iso-phase2-recon-verification.md section 4 and in this plan's Task 6.

Time: MISO publishes fixed EST hour-ending with no DST rows, so drivers pass
dst_pairs_per_year=0 and no fall-back pair is ever flagged.

df_al.xls spans a 7-day reporting period but carries ActualLoad for exactly one
market day; the forecast-only days are dropped rather than interpolated.
"""
from __future__ import annotations

import pandas as pd

TIME = "datetime_beginning_est"
HEADER_ROW = 4

ZONES: list[str] = ["LRZ1", "LRZ2_7", "LRZ3_5", "LRZ4", "LRZ6", "LRZ8_9_10"]


def parse_df_al(raw: pd.DataFrame) -> pd.DataFrame:
    """Header-less read of one df_al workbook -> hour-beginning actual load."""
    header = [str(x).strip() for x in raw.iloc[HEADER_ROW].tolist()]
    frame = raw.iloc[HEADER_ROW + 1:].copy()
    frame.columns = header

    hours = pd.to_numeric(frame["HourEnding"], errors="coerce")
    frame = frame[hours.notna()].copy()
    hours = hours[hours.notna()]
    if not hours.between(1, 24).all():
        raise ValueError("HourEnding outside 1..24")

    days = pd.to_datetime(frame["Market Day"], errors="coerce")
    out = pd.DataFrame({TIME: days + pd.to_timedelta(hours - 1, unit="h")})
    for zone in ZONES:
        col = f"{zone} ActualLoad (MWh)"
        if col not in frame.columns:
            raise ValueError(f"df_al missing column {col!r}")
        out[f"load_mw_{zone}"] = pd.to_numeric(frame[col], errors="coerce")

    load_cols = [f"load_mw_{z}" for z in ZONES]
    out = out[out[load_cols].notna().all(axis=1)]
    out = out.dropna(subset=[TIME]).sort_values(TIME).reset_index(drop=True)
    out["dst_transition_hour"] = False
    return out


def parse_da_expost_lmp(raw: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    """Header-less read of one da_expost_lmp file -> long [TIME, node, lmp].

    Only `Value == 'LMP'` rows are kept: Stage 1 uses total price, and the MCC
    and MLC rows would otherwise triple every node.
    """
    header = [str(x).strip() for x in raw.iloc[HEADER_ROW].tolist()]
    frame = raw.iloc[HEADER_ROW + 1:].copy()
    frame.columns = header

    for col in ("Node", "Type", "Value"):
        frame[col] = frame[col].astype(str).str.strip()
    frame = frame[frame["Value"] == "LMP"]

    hour_cols = [f"HE {h}" for h in range(1, 25)]
    melted = frame.melt(
        id_vars=["Node", "Type"], value_vars=hour_cols,
        var_name="hour_ending", value_name="lmp",
    )
    hours = melted["hour_ending"].str.removeprefix("HE ").astype(int)
    out = pd.DataFrame(
        {
            TIME: day + pd.to_timedelta(hours - 1, unit="h"),
            "node": melted["Node"],
            "node_type": melted["Type"],
            "lmp": pd.to_numeric(melted["lmp"], errors="coerce"),
        }
    )
    return out.sort_values([TIME, "node"]).reset_index(drop=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_miso_features.py -v`
Expected: PASS, 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/miso_features.py tests/test_miso_features.py
git commit -m "feat(miso): daily load and DA ex-post LMP parse module"
```

---

## Task 7: ISO-NE diagnostic driver and production run

**Files:**
- Create: `scripts/isone_diagnostic.py`

**Prerequisite:** Task 1's fetch has finished. Verify first:
`ls data/raw/isone/ | wc -l` → expect `11`.

- [ ] **Step 1: Write the driver**

```python
# scripts/isone_diagnostic.py
"""Stage-1 ISO-NE diagnostic. Usage: .venv/bin/python scripts/isone_diagnostic.py

ISO-NE is the designated low-data-center CONTROL market. Windows:
max = 2016-01 -> 2026-06-30 (the workbook series ends there);
overlap = the shared 2023-01 -> 2025-04-30 capstone window.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.isone_features import TIME, ZONES, build_panel, read_workbook

RAW = Path("data/raw/isone")
PANEL = Path("data/interim/isone_diagnostic_panel.parquet")
FIGDIR = Path("outputs/isone_diagnostic")
MAX_START = pd.Timestamp("2016-01-01")
MAX_END = pd.Timestamp("2026-07-01")  # exclusive; series ends 2026-06-30
PRICE_COLS = [f"da_lmp_{z}" for z in ZONES]


def build() -> pd.DataFrame:
    books = sorted(RAW.glob("*_smd_hourly.xls*"))
    if not books:
        raise RuntimeError(f"no workbooks under {RAW} - run scripts/isone_fetch.py")

    frames = [build_panel(read_workbook(path)) for path in books]
    panel = pd.concat(frames, ignore_index=True).sort_values(TIME)
    panel = panel.drop_duplicates(subset=[TIME]).reset_index(drop=True)

    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=0)

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    panel = build()
    data_quality_report(panel, PRICE_COLS, time_col=TIME,
                        window_start=MAX_START, figdir=FIGDIR)
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="ISONE")
    for label, start, end in [
        ("max", MAX_START, MAX_END),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, PRICE_COLS, time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="ISONE", label=label)
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python scripts/isone_diagnostic.py 2>&1 | tee ~/isone-diagnostic.log`

Expected: a panel of roughly 92,000 hourly rows over ~10.5 years, with 8 zones ×
(load + price + gradient) columns plus the time and flag columns.
`assert_panel_quality` must pass with `dst_pairs_per_year=0`.

- [ ] **Step 3: Read the quality report before interpreting anything**

Confirm from stdout: rows-per-year is ~8760 for full years and ~4343 for 2026; the
negative-price share is small and plausible; no zone shows a suspicious zero.

⚠️ The recon found the 2026 workbook one row short of 181 × 24. Locate the missing hour
and record it in the Task 10 entry rather than tolerating it silently.

- [ ] **Step 4: Commit**

```bash
git add scripts/isone_diagnostic.py outputs/isone_diagnostic
git commit -m "feat(isone): Stage-1 diagnostic driver and production results"
```

---

## Task 8: SPP diagnostic driver and production run

**Files:**
- Create: `scripts/spp_diagnostic.py`

**Prerequisite:** Task 2's fetch has finished and its FAILED summary was empty. Check
`tail -20 ~/spp-fetch.log` before starting.

- [ ] **Step 1: Scale-check the price side before building the full panel**

The DA LMP archives are ~4 GB and hold ~1,222 locations per hour. Run this once:

```bash
.venv/bin/python - <<'PY'
import io, zipfile
import pandas as pd
from surg.preprocessing.spp_features import ZONES
zf = zipfile.ZipFile("data/raw/spp/price/zips/2023.zip")
members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
print("members:", len(members), "| first:", members[0])
df = pd.read_csv(io.StringIO(zf.read(members[0]).decode("utf-8", "replace")))
df.columns = [c.strip() for c in df.columns]
print("cols:", list(df.columns))
matched = (df["Settlement Location"].astype(str).str.strip().str.upper()
           .str.startswith(tuple(z.upper() for z in ZONES)))
print("rows:", len(df), "| matched to a zone:", int(matched.sum()))
PY
```

Expected: `cols` includes `Interval, GMTIntervalEnd, Settlement Location, Pnode, LMP,
MLC, MCC, MEC`; a large majority of rows match a zone prefix. **Record the matched
share — it goes in the Task 10 disclosure.**

- [ ] **Step 2: Write the driver**

```python
# scripts/spp_diagnostic.py
"""Stage-1 SPP diagnostic. Usage: .venv/bin/python scripts/spp_diagnostic.py

Locked scope (2026-08-10): 17 zones, one panel, 2016-01 -> 2026-03-24. That
window starts after the Oct-2015 Integrated System join and stops before the
wide->long schema break and the RTO-West roster jump, so the footprint is
constant throughout.

Zone price is the unweighted mean of nodal LMPs prefixed by the zone code - an
explicit estimator choice, not a settlement price. SPP publishes no zonal price.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.spp_features import (
    TIME, ZONES, gmt_hour_ending_to_local_beginning, monthly_members,
    parse_wide_load, zone_price_from_nodal,
)

RAW = Path("data/raw/spp")
PANEL = Path("data/interim/spp_diagnostic_panel.parquet")
FIGDIR = Path("outputs/spp_diagnostic")
MAX_START = pd.Timestamp("2016-01-01")
MAX_END = pd.Timestamp("2026-03-25")  # exclusive; last full day is 2026-03-24
PRICE_COLS = [f"da_lmp_{z}" for z in ZONES]


def _read_csv_bytes(payload: bytes) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(payload.decode("utf-8", "replace")))


def load_panel() -> pd.DataFrame:
    frames = []
    for archive in sorted((RAW / "load" / "zips").glob("*.zip")):
        with zipfile.ZipFile(archive) as zf:
            for member in monthly_members(zf.namelist()):
                frames.append(parse_wide_load(_read_csv_bytes(zf.read(member))))
    for daily in sorted((RAW / "load" / "daily").glob("*.csv")):
        frames.append(parse_wide_load(_read_csv_bytes(daily.read_bytes())))
    if not frames:
        raise RuntimeError(f"no load files under {RAW / 'load'}")
    return pd.concat(frames, ignore_index=True)


def _zone_prices(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    nodal = pd.DataFrame(
        {
            TIME: gmt_hour_ending_to_local_beginning(frame["GMTIntervalEnd"]),
            "location": frame["Settlement Location"],
            "lmp": pd.to_numeric(frame["LMP"], errors="coerce"),
        }
    )
    return zone_price_from_nodal(nodal, ZONES)


def price_panel() -> pd.DataFrame:
    """Aggregate nodal LMP to zone means one file at a time.

    The per-file nodal frames are never retained - only their zone means are.
    """
    frames = []
    for archive in sorted((RAW / "price" / "zips").glob("*.zip")):
        with zipfile.ZipFile(archive) as zf:
            for member in sorted(n for n in zf.namelist() if n.lower().endswith(".csv")):
                frames.append(_zone_prices(_read_csv_bytes(zf.read(member))))
    for daily in sorted((RAW / "price" / "daily").glob("*.csv")):
        frames.append(_zone_prices(_read_csv_bytes(daily.read_bytes())))
    if not frames:
        raise RuntimeError(f"no price files under {RAW / 'price'}")
    return pd.concat(frames, ignore_index=True)


def build() -> pd.DataFrame:
    panel = load_panel().sort_values(TIME)
    panel = panel[(panel[TIME] >= MAX_START) & (panel[TIME] < MAX_END)]
    panel = panel.drop_duplicates(subset=[TIME]).reset_index(drop=True)
    panel["dst_transition_hour"] = panel[TIME].duplicated(keep=False)

    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=1)

    prices = price_panel().drop_duplicates(subset=[TIME])
    before = len(panel)
    panel = panel.merge(prices, on=TIME, how="left", validate="m:1")
    if len(panel) != before:
        raise AssertionError(f"price join changed row count: {before} -> {len(panel)}")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    panel = build()
    data_quality_report(panel, PRICE_COLS, time_col=TIME,
                        window_start=MAX_START, figdir=FIGDIR)
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="SPP")
    for label, start, end in [
        ("max", MAX_START, MAX_END),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, PRICE_COLS, time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="SPP", label=label)
```

- [ ] **Step 3: Run it**

Run: `.venv/bin/python scripts/spp_diagnostic.py 2>&1 | tee ~/spp-diagnostic.log`

Expected: roughly 89,000 hourly rows over 2016-01 → 2026-03-24, 17 zones.
`assert_panel_quality` must pass with `dst_pairs_per_year=1`.

⚠️ If it raises on duplicate non-DST timestamps, the likeliest cause is a daily file that
also appears inside an annual zip. Confirm the zip era and the daily era do not overlap in
time before changing any parsing logic.

- [ ] **Step 4: Commit**

```bash
git add scripts/spp_diagnostic.py
git commit -m "feat(spp): Stage-1 diagnostic driver and production results"
```

---

## Task 9: MISO diagnostic driver and production run

**Files:**
- Create: `scripts/miso_diagnostic.py`

**Prerequisite:** Task 3's fetch has finished. `ls data/raw/miso/df_al | wc -l` should be
close to the number of market days requested; a handful of 404s is acceptable and will
appear in the fetch log's FAILED summary.

- [ ] **Step 1: Resolve the zone→price mapping empirically**

MISO node names carry **no** LRZ code, so the prefix rule used for SPP cannot apply.
Determine the mapping before writing the driver:

```bash
.venv/bin/python - <<'PY'
import pandas as pd
from surg.preprocessing.miso_features import parse_da_expost_lmp
raw = pd.read_csv("data/raw/miso/da_expost_lmp/20250806_da_expost_lmp.csv",
                  header=None, skip_blank_lines=False)
out = parse_da_expost_lmp(raw, pd.Timestamp("2025-08-06"))
print(out["node_type"].value_counts().to_dict())
zones = sorted(out.loc[out["node_type"] == "Loadzone", "node"].unique())
print("n Loadzone nodes:", len(zones))
print("sample:", zones[:25])
print("hubs:", sorted(out.loc[out["node_type"] == "Hub", "node"].unique()))
PY
```

**Decision rule — apply exactly one:**

- If the `Loadzone` node names resolve to LRZ groups (a documented utility-to-LRZ mapping
  is discoverable, or the names carry a zone token), use the **mean of the Loadzone nodes
  in each LRZ group**. This is the faithful analogue of the locked zone-average decision.
- Otherwise fall back to the **eight named hubs mapped geographically**:

  | LRZ group | Hub |
  |---|---|
  | LRZ1 (MN/ND/SD) | `MINN.HUB` |
  | LRZ2_7 (WI + MI) | `MICHIGAN.HUB` |
  | LRZ3_5 (IA + MO) | `ILLINOIS.HUB` ⚠️ nearest available, not in-zone |
  | LRZ4 (IL) | `ILLINOIS.HUB` |
  | LRZ6 (IN/KY) | `INDIANA.HUB` |
  | LRZ8_9_10 (MISO South) | mean of `ARKANSAS.HUB`, `LOUISIANA.HUB`, `MS.HUB`, `TEXAS.HUB` |

  Under the fallback, LRZ3_5 and LRZ4 share a price series — record this explicitly in
  Task 10, because those two cells are then not independent.

Write the chosen mapping into `scripts/miso_diagnostic.py` as the module-level
`ZONE_PRICE_NODES` and state which rule was applied in the commit message.

- [ ] **Step 2: Write the driver**

```python
# scripts/miso_diagnostic.py
"""Stage-1 MISO diagnostic. Usage: .venv/bin/python scripts/miso_diagnostic.py

Window: 2023-01 -> present, bounded by the current+3-calendar-year retention on
docs.misoenergy.org. Fixed EST throughout, so dst_pairs_per_year=0.

ZONE_PRICE_NODES is filled in by Task 9 Step 1 - MISO node names carry no LRZ
code, so the mapping is resolved empirically rather than by prefix.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.miso_features import (
    TIME, ZONES, parse_da_expost_lmp, parse_df_al,
)

RAW = Path("data/raw/miso")
PANEL = Path("data/interim/miso_diagnostic_panel.parquet")
FIGDIR = Path("outputs/miso_diagnostic")
MAX_START = pd.Timestamp("2023-01-01")
MAX_END = pd.Timestamp("2030-01-01")  # open-ended; panel ends at last fetched day
PRICE_COLS = [f"da_lmp_{z}" for z in ZONES]

# Filled in by Task 9 Step 1. Keys must be exactly ZONES.
ZONE_PRICE_NODES: dict[str, list[str]] = {}


def load_panel() -> pd.DataFrame:
    frames = []
    for path in sorted((RAW / "df_al").glob("*_df_al.xls")):
        raw = pd.ExcelFile(path, engine="xlrd").parse("Sheet1", header=None)
        frames.append(parse_df_al(raw))
    if not frames:
        raise RuntimeError(f"no df_al files under {RAW / 'df_al'}")
    panel = pd.concat(frames, ignore_index=True).sort_values(TIME)
    return panel.drop_duplicates(subset=[TIME], keep="last").reset_index(drop=True)


def price_panel() -> pd.DataFrame:
    if set(ZONE_PRICE_NODES) != set(ZONES):
        raise RuntimeError("ZONE_PRICE_NODES not filled in - see Task 9 Step 1")

    wanted = sorted({node for nodes in ZONE_PRICE_NODES.values() for node in nodes})
    frames = []
    for path in sorted((RAW / "da_expost_lmp").glob("*_da_expost_lmp.csv")):
        day = pd.Timestamp(path.name[:8])
        raw = pd.read_csv(path, header=None, skip_blank_lines=False)
        parsed = parse_da_expost_lmp(raw, day)
        frames.append(parsed[parsed["node"].isin(wanted)])
    if not frames:
        raise RuntimeError(f"no LMP files under {RAW / 'da_expost_lmp'}")

    nodal = pd.concat(frames, ignore_index=True)
    out: pd.DataFrame | None = None
    for zone, nodes in ZONE_PRICE_NODES.items():
        member = nodal[nodal["node"].isin(nodes)]
        mean = member.groupby(TIME)["lmp"].mean().rename(f"da_lmp_{zone}").reset_index()
        out = mean if out is None else out.merge(mean, on=TIME, how="outer")
    assert out is not None
    return out.sort_values(TIME).reset_index(drop=True)


def build() -> pd.DataFrame:
    panel = load_panel()
    panel = panel[panel[TIME] >= MAX_START].reset_index(drop=True)
    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=0)

    prices = price_panel().drop_duplicates(subset=[TIME])
    before = len(panel)
    panel = panel.merge(prices, on=TIME, how="left", validate="m:1")
    if len(panel) != before:
        raise AssertionError(f"price join changed row count: {before} -> {len(panel)}")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    panel = build()
    data_quality_report(panel, PRICE_COLS, time_col=TIME,
                        window_start=MAX_START, figdir=FIGDIR)
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="MISO")
    for label, start, end in [
        ("max", MAX_START, MAX_END),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, PRICE_COLS, time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="MISO", label=label)
```

- [ ] **Step 3: Run it**

Run: `.venv/bin/python scripts/miso_diagnostic.py 2>&1 | tee ~/miso-diagnostic.log`

Expected: roughly 30,000 hourly rows (2023-01 → present), 6 zone groups.
`assert_panel_quality` passes with `dst_pairs_per_year=0`.

⚠️ MISO South (`LRZ8_9_10`) exists throughout this window — the 2013-12-19 join is a
decade before the Stage-1 start and is not a concern here.

- [ ] **Step 4: Commit**

```bash
git add scripts/miso_diagnostic.py
git commit -m "feat(miso): Stage-1 diagnostic driver and production results"
```

---

## Task 10: Eight-market capstone synthesis

**Files:**
- Modify: `docs/decisions.md` (new dated entry)

- [ ] **Step 1: Assemble the capstone table**

From each market's `trends_by_zone_year.csv` and `fig3_level_vs_volatility_overlap.csv`,
plus the recorded DOM and ERCOT results, build one table with a row per market:

| market | load growth % (earliest → latest full year) | normalized-volatility change % | level-wins fraction (overlap) | median R² |

Prior results to reuse rather than recompute — ERCOT: level wins 132/135, load +36.7%,
normalized volatility −20.7%. NYISO, CAISO, IESO: the two 2026-08-09 `decisions.md`
entries. DOM: the figure-set entries.

Compute the three new markets with a short throwaway script; the entry shows the numbers,
not the script.

- [ ] **Step 2: Write the decisions.md entry**

The entry must state, explicitly:

1. What ran — eight markets, both windows, descriptive horse race with no time controls.
2. The table.
3. **Whether the two cross-market regularities survive at eight markets.** Through Plan A
   they were: level beats volatility in 91.7–100% of cells everywhere, and normalized
   volatility falls or is flat in **all eight panels** with zero exceptions. A market that
   breaks either pattern is the single most important thing in this entry — say so
   plainly rather than burying it.
4. **ISO-NE's control-market role.** ISO-NE has almost no data-center growth. If
   level-beats-volatility and flat-normalized-volatility hold *there too*, the pattern is
   a property of power systems generally, not of data-center presence. That is the
   inferential point of including it, and it cuts against a data-center-specific reading.
5. Per-market caveats by reference, not restated: SPP's zone price is an unweighted nodal
   mean and its west is wind-dominated; MISO's price mapping is whichever rule Task 9
   Step 1 selected, with LRZ3_5/LRZ4 sharing a series under the fallback; ISO-NE's load is
   metered demand with large BTM solar; the 2026 partial year is half a year.
6. What it does **not** support: no causal claim, no data-center attribution, and no
   comparison to the DOM controlled `z_slope` specification.

- [ ] **Step 3: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): eight-market cross-ISO Stage-1 capstone"
```

---

## Task 11: Correct the Phase-1 memos

**Files:**
- Modify: `docs/sources/availability/isone-data-availability-research.md`
- Modify: `docs/sources/availability/spp-data-availability-research.md`
- Modify: `docs/sources/availability/cross-iso-data-availability-summary.md`

The memos still assert things this plan disproved. Leaving them uncorrected is how the
Plan A defects happened.

- [ ] **Step 1: Correct the ISO-NE memo**

In §3, §5 and §9, replace the "verified 200 at 2015-08-06" and "2003 nominal" claims with
the verified depth (2016-01 →) and a pointer to
`docs/sources/availability/cross-iso-phase2-recon-verification.md` §1. Replace the §9 pull spec's ~1.4K daily
CSVs with the 11-workbook route. Note the CAPTCHA on the `zone-info` download UI and that
the workbooks are separately published open static assets.

- [ ] **Step 2: Correct the SPP memo**

In §3, §4 and §5, replace "pre-2025 naming unresolved" and the "~15-minute browser-UI
enumeration" recommendation with the verified `?path=/{YYYY}/{YYYY}.zip` grammar. Flip the
§9 Stage-1 verdict from CONDITIONAL to GO. Add the monthly/daily double-count trap, the
CF+NC rule, and the resolved GMT hour-ending timezone finding.

- [ ] **Step 3: Update the summary table**

In `docs/sources/availability/cross-iso-data-availability-summary.md`, update the SPP and ISO-NE columns:
Stage-1 verdicts both GO; ISO-NE price history 2016 → (not "≥2015 verified open, 2003
nominal"); SPP load history 2011 → verified (not "⚠️ naming").

- [ ] **Step 4: Commit**

```bash
git add docs/sources/availability/isone-data-availability-research.md docs/sources/availability/spp-data-availability-research.md docs/sources/availability/cross-iso-data-availability-summary.md
git commit -m "docs(cross-iso): correct ISONE and SPP memos against Phase-2 findings"
```

---

## Self-review (done at write time)

**1. Spec coverage.** The cross-ISO design spec's Phase-2 scope is three markets plus the
capstone. Tasks 1/4/7 cover ISO-NE, 2/5/8 SPP, 3/6/9 MISO, 10 the capstone, and 11 the
memo corrections the recon made necessary. The spec's correctness requirements are each
carried: explicit hour conventions per market (ISO-NE fixed 24h grid, SPP GMT hour-ending
→ local, MISO fixed EST); duplicate/gap/NaN assertions via `assert_panel_quality`;
negative prices left unclipped, with their share reported by `data_quality_report`; no
interpolation (MISO drops forecast-only rows rather than filling); the two-window policy
in all three drivers; and the data-quality gate before interpretation (Task 7 Step 3,
Task 10 Step 1).

**2. Placeholder scan.** One deliberate deferral: `ZONE_PRICE_NODES` in Task 9 is empty in
the code block. It is not a placeholder in the prohibited sense — Task 9 Step 1 gives the
exact command, an explicit two-branch decision rule, and a complete fallback mapping
table, and `price_panel` raises immediately if it is left unfilled. Every other code block
is complete.

**3. Type consistency.** `TIME` is a module constant in all three feature modules and is
imported by each driver rather than restated. `ZONES` is `list[str]` everywhere.
`parse_wide_load`, `parse_long_load`, `parse_smd_sheet` and `parse_df_al` all return a
frame carrying `TIME` plus `load_mw_<zone>` columns; `zone_price_from_nodal` and MISO's
`price_panel` both return `TIME` plus `da_lmp_<zone>`. `dst_pairs_per_year` is 0 for
ISO-NE and MISO and 1 for SPP, matching each market's verified convention. The `stage1`
call signatures match `src/surg/diagnostics/stage1.py` as read on 2026-08-10.

**4. Known risk not designed away.** Task 8's `price_panel` concatenates per-file zone
means across ~9 years; at 24 rows × 17 zones per file that is roughly 1.3 M rows, which
fits in memory. The intermediate nodal frames are never retained — only their zone means.
