# ERRATA — ERCOT Load Volatility Diagnostic Implementation Plan

**Date:** 2026-08-07
**Applies to:** `docs/superpowers/plans/2026-08-07-ercot-load-volatility-diagnostic.md`
**Status:** Tasks 1–3 complete. Tasks 4–9 must be executed against the corrections below, not the plan as written.

The plan was written from an unverified reading of ERCOT's archive pages. Direct
inspection of the real files on 2026-08-07 found four defects. All facts below were
observed by downloading and parsing the actual archives, not inferred.

---

## E1 — Task 2's committed parser cannot read real ERCOT data (BLOCKING)

`hour_ending_to_beginning` (committed in `5f2e628`) parses with
`format="%m/%d/%Y %H:%M"`. Real ERCOT `Hour Ending` values break this two ways:

| Real value | Why it fails | Frequency |
|---|---|---|
| `12/31/2024 24:00` | `%H` accepts 00–23 only | **365–366× per year** (every day) |
| `11/03/2024 02:00 DST` | unconverted ` DST` suffix remains | 1× per year (fall-back) |

Verified crash against the committed function:

```
ValueError: unconverted data remains when parsing with format "%m/%d/%Y %H:%M": " DST"
ValueError: time data "11/03/2024 24:00" doesn't match format "%m/%d/%Y %H:%M"
```

**Until this is fixed, Tasks 5–8 cannot run at all.** Fix first.

### The committed test encodes a false assumption

`test_dst_duplicate_hour_is_flagged_not_dropped` feeds
`["11/03/2024 02:00", "11/03/2024 02:00", ...]` — two *identical* labels. ERCOT never
emits that. The real repeated hour is disambiguated by a ` DST` **suffix**, so
`duplicated()` on the raw column never fires on real data. The test passes while
testing something that does not exist.

### Correct parsing rule

1. Coerce to string first (see E2 — 2022 has mixed dtypes).
2. Strip an optional trailing ` DST`.
3. Split the date from `HH:MM`; hour-ending runs **1–24**.
4. `datetime_beginning_cpt = date + (hour_ending - 1) hours`.
5. Compute `dst_transition_hour = duplicated(keep=False)` **after** conversion — both
   rows of the ambiguous pair then flag True, the existing test stays green, and Task 5's
   `assert_panel_quality` logic keeps working unchanged.

### Year-seam boundary — verified correct

Every file runs `01/01/YYYY 01:00` → `12/31/YYYY 24:00`. Under the rule above,
`12/31/2024 24:00` → `2024-12-31 23:00` and the next file's `01/01/2025 01:00` →
`2025-01-01 00:00`. **No gap, no overlap at the year seam.** This was the highest-risk
off-by-one and it checks out.

### DST row counts (2024, representative)

- `2024-11-03` (fall-back): **25** load rows — the extra is the ` DST`-suffixed one.
- `2024-03-10` (spring-forward): **23** load rows — the 02:00 hour is absent.

Net effect on Task 5's gap assertion is ~zero per year; the `> 48` tolerance is safe.

---

## E2 — Load archive schema varies by year; scope changed to 2017–2026

The plan's `FIRST_ZONE_YEAR = 2004` and "~190,000 rows" are unreachable. ERCOT publishes
**four different schema families**, and the plan's case-sensitive regex
`Native_Load_\d{4}\.zip` only matches 2019–2026 (8 of 12 files).

| Years | URL pattern | Timestamp column | Zone names |
|---|---|---|---|
| 2002–2014 | `YYYY_ercot_hourly_load_data.xls` | unverified | unverified; pre-Apr-2003 uses 11 control areas |
| 2015 | `native_load_2015.xls` | unverified | needs `xlrd` (not installed) |
| 2016 | `native_Load_2016.zip` | `Hour_End` (**Timestamp**, `.003` sec) | `FAR_WEST` `NORTH_C` `SOUTHERN` `SOUTH_C` |
| **2017–2026** | `native_load_` / `Native_Load_` + `.zip` | `Hour Ending` / `HourEnding` | **matches the plan's `ZONES` exactly** |

**Decision (user, 2026-08-07): use 2017–2026.** Ten years, ~87,000 rows, one schema
family. Covers the entire data-center growth era. Rejected: 2015–2026 (three schema
families + `xlrd` + a zone-rename map) and 2002–2026 (unverified format, 11-control-area
structure, unbounded discovery).

### Per-file facts, all ten files (verified)

| File | Timestamp column | dtype | rows |
|---|---|---|---|
| `native_Load_2017.xlsx` | `Hour Ending` | str | 8,760 |
| `Native_Load_2018.xlsx` | **`HourEnding`** | str | 8,760 |
| `Native_Load_2019.xlsx` | **`HourEnding`** | str | 8,760 |
| `Native_Load_2020.xlsx` | **`HourEnding`** | str | 8,784 |
| `Native_Load_2021.xlsx` | `Hour Ending` | str | 8,760 |
| `Native_Load_2022.xlsx` | `Hour Ending` | **mixed `str` + `datetime`** | 8,760 |
| `Native_Load_2023.xlsx` | `Hour Ending` | str | 8,760 |
| `Native_Load_2024.xlsx` | `Hour Ending` | str | 8,784 |
| `Native_Load_2025.xlsx` | `Hour Ending` | str | 8,760 |
| `Native_Load_2026.xlsx` | `Hour Ending` | str | 5,831 (partial, through 07/31) |

Two consequences the plan misses:

- **`HourEnding` (no space) in 2018–2020.** The plan's Task 5 does
  `.strip().upper()` then looks up `"HOUR ENDING"` — `HOURENDING` never matches, so those
  three years raise `KeyError`. Normalize both spellings.
- **2022 has mixed `str` and `datetime` values in one column.** Any `.str` accessor
  yields silent `NaN` on the datetime rows rather than raising. Coerce explicitly.

### Filename case is inconsistent

Extracted names vary: `native_load_2017.xlsx`, `native_Load_2016.xlsx`,
`Native_Load_2019.xlsx`. `RAW.glob("Native_Load_*.xlsx")` appears to work on macOS only
because APFS is case-insensitive — that is a filesystem accident, not correct code. Make
the glob case-insensitive explicitly.

---

## E3 — Task 4 fetch corrections

- Regex must be **case-insensitive** (`re.I`) or it silently drops 2017–2018.
- Filter load archives to **year ≥ 2017**.
- **Download price archives for year ≥ 2022 only.** Task 6 discards everything before
  `DOM_START.year` anyway; the listing offers 2010–2026 at ~14 MB each, so fetching all 17
  wastes ~170 MB and considerable time for data no downstream step reads. Deliberate
  deviation — record it in the commit message.
- Task 4 Step 3's verification (`ls data/raw/ercot/*.xlsx | wc -l`, expect 30+) is wrong.
  Correct expectation: **10 load + 5 price = 15**.

### Verified endpoints (2026-08-07)

Load page `https://www.ercot.com/gridinfo/load/load_hist` — 12 `native_load` archives.
Price listing `https://www.ercot.com/misapp/GetReports.do?reportTypeId=13061` — **17
names, 17 `doclookupId`s, pairing verified sound** in descending year order. The plan's
positional `zip()` approach is correct.

Price `doclookupId`s for the years actually needed:

| Year | doclookupId |
|---|---|
| 2022 | 886632075 |
| 2023 | 969805139 |
| 2024 | 1065471230 |
| 2025 | 1177737535 |
| 2026 | 1257501090 |

---

## E4 — Task 6 price schema verified; `Repeated Hour Flag` noted

**All four of the plan's guessed column names are correct.** Verified header:

```
Delivery Date | Delivery Hour | Delivery Interval | Repeated Hour Flag |
Settlement Point Name | Settlement Point Type | Settlement Point Price
```

Other verified facts:

- Archives extract to `rpt.00013061.0000000000000000.RTMLZHBSPP_YYYY.xlsx`. The plan's
  leading-wildcard glob `*RTMLZHBSPP_*.xlsx` handles this, and
  `path.stem.split("_")[-1]` still yields the year correctly.
- **12 sheets per file, one per month** (`Jan`…`Dec`) — the plan's `sheet_name=None` is right.
- **15 settlement points**, not the "20–40" the plan estimated: `HB_BUSAVG` `HB_HOUSTON`
  `HB_HUBAVG` `HB_NORTH` `HB_PAN` `HB_SOUTH` `HB_WEST` `LZ_AEN` `LZ_CPS` `LZ_HOUSTON`
  `LZ_LCRA` `LZ_NORTH` `LZ_RAYBN` `LZ_SOUTH` `LZ_WEST`.
- Scale: ~68,000 rows per month sheet, ~820,000 rows per year; ~14 MB zipped, ~22 MB
  extracted. Reading five years will take on the order of tens of minutes.

### `Repeated Hour Flag` — document, do not build machinery

The DST fall-back hour is flagged `Y` (92 such rows on `11/03/2024`) but carries the
**same `Delivery Date` + `Delivery Hour`** as the original. The plan's `load_prices()`
builds its timestamp from date + hour only, so both hours average into one value.

This is **not** a crash and **not** a row-count problem: the price frame collapses to one
row per timestamp, the load frame keeps two, and a left many-to-one merge preserves the
row count — Task 6's `len(panel) != before` assertion passes. The cost is one hour per
year, four years, silently averaged. Note it in the `load_prices` docstring and in the
Task 9 decisions entry; do not build DST-disambiguation machinery for it.

---

## E5 — Task 8 caveat for the write-up

`level_vs_volatility` regresses standardized price on standardized load level and
`|gradient|` with **no time controls**. Load level and price both carry strong diurnal and
seasonal structure, so `beta_level` will be large partly because both track time-of-day.

That is acceptable for a Stage 1 descriptive horse race, but the DOM finding it will be
compared against (`z_slope` sign-flips under a load-level control) came from a specification
*with* controls. **Task 9 must not claim the two are directly comparable.** One-line caveat
in the decisions entry; not a plan change.
