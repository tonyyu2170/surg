# Cross-ISO Phase-2 Recon: Empirical Verification Before Plan B

**Date:** 2026-08-10
**Purpose:** Settle the four data-access unknowns that blocked writing the Plan B
implementation plan (MISO → ISONE → SPP → capstone). Every claim below was verified by
downloading and reading real files on 2026-08-10. Where this contradicts a Phase-1 memo,
**this document wins** and the memo is wrong.
**Why this exists:** Plan A shipped four defects, all traceable to code written against
assumed file structure. Three Phase-1 memo claims have now been falsified against real
files. Plan B's code blocks are therefore written only against structures observed here.

---

## 0. Summary of verdict changes

| Market | Phase-1 verdict | Phase-2 verdict | What changed |
|---|---|---|---|
| **MISO** | GO (2023-01 →) | **GO, unchanged** | No recon needed; Stage-1 window sits inside already-verified families |
| **ISONE** | GO, "one access fork" | **GO — fork dissolved** | Load is open; and one workbook replaces the entire planned price pull |
| **SPP** | **CONDITIONAL** ⚠️ | **GO — blocker eliminated** | Consolidated naming found; no browser enumeration needed |

---

## 1. ISONE price depth — memo claim FALSIFIED

The ISONE memo (§3, §5) states the DA LMP dailies are "verified 200 at 2015-08-06,
2023-08-06, 2026-08-06" and that the SMD era is "nominally 2003 →".

**`WW_DALMP_ISO_20150806.csv` returns HTTP 200 with a 31-byte body: `No data exists for
this period.`** The memo verified status codes, not payloads. Same for every probed date
in 2003–2015.

**⚠️ Parser requirement:** for this endpoint, `HTTP 200` does **not** mean "file". A
fetcher that trusts the status code writes thousands of 31-byte junk files and the panel
silently loses those days. Treat `len(body) < 1000` (or the literal sentinel string) as a
MISS.

**Actual coverage** (monthly sampling, 15th of each month):

| Years | Result |
|---|---|
| 2016 – 2025 | **12/12 every year — dense** |
| 2026 | 7/8 (8th sample postdates today; not a gap) |
| Dec 2015 | patchy, deterministic: 11-30 ✓, 12-01 ✗, 12-03/04/05 ✓, 12-06/07 ✗, 12-08 ✓, 12-09 ✗, 12-10 ✓ |
| ≤ Nov 2015 | absent |

Empties are reproducible across 3 passes — real absence, not transient error.

**Usable ISONE price history = 2016-01 → present**, not 2003. This matches ISO-NE's own
note that the series was "restated back to January 2016."

## 2. ISONE zonal load — access fork dissolved, and the pull design changes

The checkpoint chose "hunt the public SMD annual-file URLs — no registration". The hunt
succeeded, but first a correction: the **`zone-info` page's download interface sits behind
a CAPTCHA**. That interface was not used and must not be. The annual workbooks are
published separately as **open static assets** requiring no CAPTCHA, no registration, and
no login.

### Verified URLs (all 11 years, confirmed by file-signature download)

| Year | URL | Format |
|---|---|---|
| 2016 | `/static-assets/documents/2016/02/smd_hourly.xls` | xls (OLE2), 13.3 MB |
| 2017 – 2023 | `/static-assets/documents/{Y}/02/{Y}_smd_hourly.xlsx` | xlsx, ~7.5–7.9 MB |
| 2024 | `/static-assets/documents/100008/2024_smd_hourly.xlsx` | xlsx, 7.7 MB |
| 2025 | `/static-assets/documents/100020/2025_smd_hourly.xlsx` | xlsx, 7.8 MB |
| 2026 | `/static-assets/documents/100032/2026_smd_hourly.xlsx` | xlsx, 3.9 MB (partial) |

Base: `https://www.iso-ne.com`. ISO-NE switched from dated folders to numeric document-ids
after 2023; the ids are **not** reliably derivable by formula (predictions were off by
one) — treat the three above as verified constants, not as a computed pattern.

⚠️ Probing these with a `Range:` header returns non-Excel content. Use plain GET, or
stream and read the first chunk.

### Structure (verified in 2016, 2023, 2026 — identical across all three)

- **Sheets:** `Notes`, `ISO NE CA` (system), then the 8 zones: `ME, NH, VT, CT, RI, SEMA,
  WCMA, NEMA`.
- **Columns (every zone sheet):** `Date, Hr_End, DA_Demand, RT_Demand, DA_LMP, DA_EC,
  DA_CC, DA_MLC, RT_LMP, RT_EC, RT_CC, RT_MLC, Dry_Bulb, Dew_Point`.
- `Hr_End` is int 1–24; `Date` is a date.

**CORRECTION (2026-08-10, found during Plan B Task 4 execution):** the "identical across
all three" claim above is wrong from 2024 onward. This section sampled only 2016, 2023,
and 2026 (which stops at 2026-06-30, before that year's November fall-back) — a real
sampling gap, not a memo error. Verified against all 11 workbooks: **2016–2023** matches
the structure above, with `Hr_End` as int64. **2024 onward** uses real local prevailing
clock time and `Hr_End` is a **string**: the fall-back day carries 25 rows with the
repeated hour written `'02X'` (verified 2024-11-03, 2025-11-02), and the spring-forward
day carries 23 rows with hour 2 absent (verified 2024-03-10, 2025-03-09, 2026-03-08).

### The finding that changes the plan

**The workbook carries load *and* decomposed DA/RT LMP *and* weather, per zone, in one
file.** ISONE Stage 1 therefore needs **11 file downloads (~85 MB)** — not the ~1,400
daily `WW_DALMP_ISO` CSVs the memo's pull spec (§9) budgeted. The daily-CSV route is only
needed for sub-zonal/nodal detail, which Stage 1 does not use.

This also means §1's "HTTP 200 ≠ file" trap **does not apply to the Stage-1 path**. Keep
it documented for any future nodal work.

### Time convention

2023 has **8760 rows = 365 × 24**, and **both** DST transition days (2023-03-12 and
2023-11-05) have exactly 24 rows. 2016 has 8784 = 366 × 24 (leap year). So the series
carries no DST pairs and no short days *in the years sampled here (2016, 2023)*.

**`dst_pairs_per_year = 0` for ISONE** — same gate setting as MISO and IESO, not the
NYISO/CAISO setting of 1.

**CORRECTION (2026-08-10, found during Plan B Task 4 execution): the two claims above
are FALSE from 2024 onward.** This section sampled 2016, 2023, and 2026 only, and the
2026 workbook ends 2026-06-30 — before that year's November fall-back — so the sampling
never reached the failure case. Verified against all 11 workbooks: 2016–2023 is a fixed
24-hour grid (matches the claim above, `Hr_End` int64); **2024 onward is real local
prevailing clock time**, and `Hr_End` is a **string**: the fall-back day carries 25 rows
with the repeated hour written `'02X'` (verified 2024-11-03, 2025-11-02), and the
spring-forward day carries 23 rows with hour 2 absent (verified 2024-03-10, 2025-03-09,
2026-03-08). **The correct setting is `dst_pairs_per_year = 1`, not 0.**

⚠️ 2026 partial file: 4343 rows spanning 2026-01-01 → 2026-06-30, one short of 181 × 24 =
4344. Data ends **2026-06-30**. **Resolved by the correction above**: the missing hour is
2026-03-08 02:00, the spring-forward hour that correctly does not exist — not a data
defect, and not something a quality gate needs to locate as an anomaly.

### Engines

2016 is `.xls` → needs `xlrd`; 2017+ are `.xlsx` → need `openpyxl`. Both are present in
the main venv as of Plan A Task 13.

## 3. SPP archive naming — blocker eliminated, no browser needed

The SPP memo (§3, §5) flags pre-2025 naming as unresolved and recommends holding SPP for
a "~15-minute browser-UI enumeration". **That task is unnecessary.** The consolidated
archives are per-year zips at a path the listing API never revealed:

```
https://portal.spp.org/file-browser-api/download/{fileset}?path=/{YYYY}/{YYYY}.zip
```

Verified 200 with ZIP signature:

| Fileset | Coverage | Size |
|---|---|---|
| `hourly-load` | **2011 – 2024** (2025, 2026 → 404) | 0.58 – 1.45 MB/yr |
| `da-lmp-by-settlement-location` | 2022, 2023 verified | ~280 – 286 MB/yr |
| `rtbm-lmp-by-location` | 2022 verified | **5.02 GB/yr** — confirms 5-min stays out of Stage 1 |

So the complete SPP load series = **annual zips 2011–2024 + daily files 2025 → present**.
**SPP Stage-1 verdict flips from CONDITIONAL to GO.**

### ⚠️ Double-count trap inside the zips

`2023.zip` holds **377 CSVs for a 365-day year**: 365 dailies
(`DAILY_HOURLY_LOAD-YYYYMMDD.csv`) **plus 12 monthly rollups**
(`HOURLY_LOAD-YYYYMM.csv`) covering the same hours. Globbing the archive double-counts the
entire year.

Which family exists depends on the year:

| Years | dailies | monthlies |
|---|---|---|
| 2011 – 2016 | **0** | 12 |
| 2019 | 105 (partial) | 12 |
| 2022 – 2024 | 365 / 366 | 12 |

**The monthly family is the only one present in every archived year.**

### The SPP era table — use this, not four separate rules

The parse family, schema, roster, and CF/NC rule all change on different dates. Implement
from one table, not from independent conditionals:

| Era | Source | Format | Zones | Sum CF+NC? | Datetime |
|---|---|---|---|---|---|
| 2011-01 – 2024-12 | annual zip, **monthlies only** | wide | 16 → 17 (WAUE @ 2016) | n/a | `1/1/11 7:00` (early), no space in header ≤2014 |
| 2025-01 – 2026-03-24 | dailies | wide | 17 | n/a | `MM/DD/YYYY HH:MM:SS` |
| 2026-03-25 → | dailies | **long** | 20 (PSCO/PRPA churn) | **YES** | `MM/DD/YYYY HH:MM:SS` |

Note the daily era spans **both** schema families, and the 20-zone roster exists only in
the final ~4 months of the panel.

### DA LMP availability mirrors load exactly (verified)

| Path | Result |
|---|---|
| `da-lmp-by-settlement-location?path=/2024/2024.zip` | 200 ZIP, 294 MB |
| `…?path=/2025/2025.zip` | **404** |
| `…?path=/2025/08/By_Day/DA-LMP-SL-202508060100.csv` | 200 CSV, 3.1 MB |
| `…?path=/2026/08/By_Day/DA-LMP-SL-202608060100.csv` | 200 CSV, 4.2 MB |

Same era boundary as load: **annual zips through 2024, dailies 2025 →**. The locked
common-overlap headline window (2023-01 → 2025-05) is therefore fully covered on both
the load and price sides.

### Roster growth (verified in-data)

| Period | Zones | Note |
|---|---|---|
| 2011 – 2014 | 16 | no WAUE |
| 2016 – 2025 | 17 | WAUE present — the Oct-2015 Integrated System join ✓ memo correct |
| 2026-03-25 → | 20 | RTO West: adds WACM, WAUW, PRPA (and PSCO on 2026-03-25 only) |

This is the same roster-growth defect class that broke Plan A's CAISO driver (defect #4).
Any SPP panel must either pin a zone set with a start date per panel, or split panels.

⚠️ The 2026-03-25 file lists `PSCO` and BAs `PSCO/WACM/WAUW/SPP`; from 2026-04-01 the
roster carries `PRPA` instead of `PSCO` and BAs settle to `SPP/SWPW`. Treat late-March
2026 as a transition period, not a stable footprint.

### Schema and format drift

- **Wide → long break at 2026-03-24 ✓ memo correct.** Wide (`MarketHour, <zone cols>`)
  through 2026-03-08; long (`Market Hour, Balancing Area Name, Control Zone Name,
  Forecast Area Type, Load MW`) from 2026-03-25.
- **Header whitespace drift:** 2011–2014 have no space after commas
  (`MarketHour,CSWS,EDE`); 2015+ do (`MarketHour, CSWS, EDE`). **Strip column names.**
- **Datetime format drift:** early monthlies use `1/1/11 7:00` (2-digit year, no seconds);
  dailies use `11/22/2023 07:00:00`. **Do not hardcode one format string.**

### ⚠️ The long format is a level trap: sum CF + NC

`Forecast Area Type` takes values `CF` and `NC`. Seven zones carry **both** (KCPL, LES,
NPPD, OPPD, WACM, WAUE, WR); the other thirteen carry CF only. A pivot on
`(Market Hour, Control Zone Name)` alone collides on those seven.

Verified against the wide file two days earlier (2026-03-23 vs 2026-03-25):

| Zone | ratio, CF only | ratio, CF + NC |
|---|---|---|
| OPPD | 0.691 | **1.017** |
| LES | 0.831 | **0.996** |
| NPPD | 0.907 | **0.995** |
| CF-only zones (e.g. CSWS, OKGE) | 1.096 / 1.139 | identical |

**The wide column equals CF + NC.** Long-format parsing must sum both types per
(hour, zone), or the seven dual-type zones drop 5–31% of their load at the schema break.

### Timezone — RESOLVED, `MarketHour` is GMT hour-ending

The memo flagged this as unlabeled and unresolved. Verified on both transition days:

| Date | Rows | First → last `MarketHour` |
|---|---|---|
| 2025-08-06 (ordinary) | 24 | `08/06 06:00` → `08/07 05:00` |
| 2025-11-02 (fall back) | **25** | `11/02 06:00` → `11/03 06:00` |
| 2026-03-08 (spring fwd) | **23** | `03/08 07:00` → `03/09 05:00` |

Row counts follow the **local** Central day (23/24/25), while the timestamps are **GMT,
hour-ending**: `06:00Z` = hour ending 01:00 CDT, `07:00Z` = hour ending 01:00 CST. One
file = one local Central day. Convert GMT → America/Chicago before any join; do not read
`MarketHour` as local.

⚠️ Cross-check at implementation time against the DA LMP files, which carry explicit local
and `GMTIntervalEnd` columns in the same row.

## 4. MISO — no recon required

MISO's Stage-1 window (2023-01 →) sits entirely inside families already verified during
Phase 1 and cached in the session-state memory (daily `{YYYYMMDD}_<fam>` files with
current+3-calendar-year retention; weekly `_5MIN_LMP.zip` from 2023-01-02). `xlrd` and
`openpyxl` landed with Plan A Task 13. The only open MISO item — enumerating pre-2023
hourly LMP bundles on `cdn.misoenergy.org` — lies **outside** the Stage-1 window and is
not a Plan B prerequisite.

⚠️ Standing hazard, unchanged: never POST to `misoenergy.org/api/find/...`; it is an
Elasticsearch write endpoint.

---

## 5. Memo reliability scorecard

Four Phase-1 memo claims have now been checked against real files. **Three were false.**
A fourth claim was checked during Plan B execution — this time **this recon document's
own claim, not a memo's** — and it was also false.

| Claim | Source | Reality |
|---|---|---|
| NYISO footprint "stable since 1999" | nyiso memo §6 | **FALSE** — combined `N.Y.C._LONGIL` pre-2005-01-31; 4 external proxy buses in every price file (Plan A defect #3) |
| CAISO price depth "2010 →" | caiso memo | **FALSE** — `PRC_LMP` retention ~3 yr; real data starts 2023-04-12 |
| ISONE price depth "2015 verified / 2003 nominal" | isone memo §3, §5 | **FALSE** — 2015 returns an empty sentinel; real start is 2016-01 |
| SPP wide→long break at 2026-03-24 | spp memo §4 | **TRUE** ✓ |
| ISONE SMD workbook structure "verified identical in 2016, 2023, 2026," `dst_pairs_per_year = 0` | **this document, §2** (not a memo) | **FALSE** — checked 2026-08-10 against all 11 workbooks: the convention changes at 2024 (string `Hr_End`, 25-row fall-back day with the repeated hour written `'02X'`, 23-row spring-forward day). Correct setting is `dst_pairs_per_year = 1`. Root cause: this section sampled only 2016/2023/2026, and the 2026 workbook ends 2026-06-30 — before that year's fall-back — so the sampling never reached the failure case. |

The failure mode for the four memo claims is consistent: **claims verified by HTTP
status or by UI appearance, never by reading the payload.** The fifth (this document's
own) failed for a related but distinct reason: **verified against too few sampled years
to reach the failure case.** Any remaining unverified memo claim — MISO/ISONE/SPP
footprint and depth assertions not listed above — should be treated as a hypothesis until
a real file confirms it.

## 6. What Plan B must carry as requirements

1. **Payload-not-status verification** on every fetcher: a 200 with a sentinel body is a
   MISS. Log it to a module-level `FAILED` list, continue, and print a loud end-of-run
   summary that is checked before any panel is trusted (the `757b5e3` pattern).
2. **Catch `httpx.HTTPError` inside the retry loop** — `ReadTimeout` is a subclass and
   killed the CAISO fetch nine times before that fix.
3. **SPP: implement from the §3 era table**, not from independent conditionals — parse
   family, schema, roster, CF/NC rule and datetime format each change on a different
   date, and the daily era spans both schema families. Never glob a zip.
4. **SPP: strip column names** (whitespace drift at 2015) and **infer datetime format per
   era**; handle roster growth (16 → 17 → 20) by panel, per the CAISO precedent.
7. **ISONE: one workbook per year, 11 URLs**, three of them numeric-id constants.
8. **ISONE: `dst_pairs_per_year = 1`** (corrected 2026-08-10; this section originally
   said `= 0`, which was itself a falsified claim — see §2 and §5).
9. **Verify plan code blocks by regex-extract + `difflib`** against on-disk files per
   batch — it caught all four Plan A defects at near-zero cost.

## 7. Window implications for the capstone

| Market | Verified usable window (Stage 1) |
|---|---|
| MISO | 2023-01 → present |
| ISONE | 2016-01 → 2026-06-30 |
| SPP | 2011-01 → present (load); DA LMP 2022–2024 zips + 2025 → dailies, all verified |

The locked common-overlap headline window (2023-01 → 2025-05 excl.) is **satisfied by all
three**. ISONE's end-of-data at 2026-06-30 bounds any max-window run.
