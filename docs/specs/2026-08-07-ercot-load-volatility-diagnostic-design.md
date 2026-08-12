# ERCOT Load Volatility Diagnostic — Design

**Date:** 2026-08-07
**Status:** Approved by user, ready for writing-plans
**Related:** `docs/sources/availability/ercot-data-availability-research.md` (data availability research)

---

## Purpose

Replicate the recent DOM load/price diagnostics on ERCOT to answer two questions:

1. **Is ERCOT load volatile at all?** (and is its volatility rising or flat?)
2. **Is price more correlated with load level than with load volatility?**

This mirrors the 2026-07-30 DOM finding — load grew +21.5% while volatility stayed flat or fell,
and congestion turned out to be level-driven rather than volatility-driven, with the pre-registered
`z_slope` sign-flipping under a load-level control in all 10 cells.

## Staging

Explicitly a **two-stage** effort, per user decision:

- **Stage 1 (this spec):** quick diagnostic acting as a go/no-go gate.
- **Stage 2 (not yet specced):** proper `src/surg/` ERCOT acquisition + preprocessing modules and
  a port of QR-full / GPD, built only if Stage 1 shows the market is worth the investment.

The Stage 1 output parquet is designed to seed Stage 2, so this is not throwaway work.

## Scope decisions (locked)

| Decision | Choice | Rationale |
|---|---|---|
| Geography | **All 8 weather zones + ERCOT total, no treatment label** | Lets the data show which zones are volatile. Avoids assuming West Texas growth is data-center driven — it is substantially Permian oil & gas electrification (see research memo §2c). |
| Resolution | **Hourly** | Free ERCOT history is hourly; sub-hourly actual load is retained only ~31 days. |
| Price variable | **Total price only** | Both gate questions are answerable without decomposing congestion, which sidesteps the unresolved lossless/congestion-derivation dependency. Deferred to Stage 2. |
| Load window | **Full 8-zone history (2004 → 2026)** | The archive runs 1995–2026, but weather-zone breakdown only exists from **April** 2003 — so 2003 is a partial year and 2004 is the first complete one. Before April 2003 it is 11 control areas with different boundaries. Free, and makes "is volatility rising?" far more answerable than the 3.4-year DOM window. |
| Price window | **DOM-matched (2022-10 → 2026)** | Keeps the level-vs-volatility comparison apples-to-apples with the DOM panel. |
| Implementation | **Standalone script, no new `src/` modules** | Approach A. Matches the staged decision; B would invert it. |

## Data sources

**Load — verified.** ERCOT Hourly Load Data Archives, annual zips,
`https://www.ercot.com/gridinfo/load/load_hist`. Public, no API key, no quota. Coverage
1995–2026 continuous (2001 the only gap); 8 weather zones since April 2003. Updated monthly
around the 9th.

**Price — VERIFIED 2026-08-07.** The open risk is now closed. Historical RTM settlement point
prices are published as **annual archives**, no API key, no quota:

```
https://www.ercot.com/misapp/GetReports.do?reportTypeId=13061
  → RTMLZHBSPP_<YYYY>.zip, years 2010–2026 (17 archives)
  → contains rpt.00013061.*.RTMLZHBSPP_<YYYY>.xlsx  (~13 MB uncompressed)
```

Related IDs confirmed: `13060` = DAM equivalent (`DAMLZHBSPP_YYYY.zip`); `12301` = daily
`NP6-905` SPP files (not needed — the annual archive supersedes it for backfill).

**Price history (2010→) is deeper than the 8-zone load history (2003→), so load is the
binding constraint on window length, not price.**

### ⚠️ Three verified gotchas the plan must handle

**1. Both archives are XLSX, not CSV — and `openpyxl` is NOT installed.**
Confirmed by `pd.read_excel` failing with `ModuleNotFoundError: No module named 'openpyxl'` in
the project venv. Adding this dependency is a prerequisite task, not an implementation detail.

**2. ERCOT load is HOUR-ENDING; the DOM panel is hour-BEGINNING.**
Verified column header is `Hour Ending`, with values like `01/01/2024 01:00`. The DOM panel's
key is `datetime_beginning_ept`. **Joining these naively produces a silent one-hour
misalignment** — which would corrupt every level-vs-volatility comparison while looking
perfectly plausible. Convention conversion must be explicit and asserted.

**3. MIS `doclookupId` ↔ filename pairing is positional and easy to mismatch.**
While verifying, a `grep -B2` pairing returned the 2026 archive when the 2024 one was requested.
The listing HTML must be parsed as structured rows, not by proximity heuristics.

### Verified load schema
`Native_Load_<YYYY>.xlsx` columns, confirmed by reading the 2024 file:

```
Hour Ending | COAST | EAST | FWEST | NORTH | NCENT | SOUTH | SCENT | WEST | ERCOT
```

Exactly the 8 weather zones plus system total the design assumes. Note `FWEST` (Far West) and
`WEST` are **separate zones** — consistent with research memo §2c, where conflating them was a
logged error. Direct download URLs, no MIS lookup needed:
`https://www.ercot.com/files/docs/<yyyy>/<mm>/<dd>/Native_Load_<YYYY>.zip`

## Panel schema

Written to `data/interim/ercot_diagnostic_panel.parquet`.

| Column | Type | Notes |
|---|---|---|
| `datetime_hour_cpt` | timestamp | Central Prevailing Time (ERCOT native) |
| `load_mw_<zone>` | float | 8 weather zones + `load_mw_ercot` total |
| `load_gradient_abs_mw_per_min_<zone>` | float | absolute hourly diff ÷ 60 |
| `total_lmp_rt_<settlement_point>` | float | $/MWh, hourly mean of 15-min SPP |
| `dst_transition_hour` | bool | mirrors the DOM panel column |

**The gradient must be computed by importing `add_load_gradient_columns` from
`src/surg/preprocessing/features.py`, not re-implemented.** This guarantees the volatility measure
is identical to DOM's rather than merely similar — which is the entire basis for cross-market
comparability.

## Outputs

Three figures plus a summary table, written to `outputs/`.

1. **Volatility trend** — monthly and annual mean and p95 of `|gradient|` per zone, reported
   **both raw and normalized by mean load**. The normalization is essential: the DOM result was
   volatility flat/falling *while load rose*, so raw ramps would confound growth with volatility.
2. **Level trend** — annual mean and peak load per zone. The `+21.5%` analog.
3. **Level-vs-volatility horse race** — hourly total price regressed on load level versus
   `|gradient|`, per zone, on the DOM-matched window. Report standardized coefficients so the two
   predictors are directly comparable.

## Correctness requirements

- **Timezone.** ERCOT is Central Prevailing; the DOM panel is Eastern Prevailing. Conversion must
  be explicit, with DST duplicate/missing hours handled and flagged via `dst_transition_hour`.
- **Duplicate rows.** A duplicate-row bug already occurred during the 5-minute backfill. Assert
  timestamp uniqueness after every join.
- **Gaps.** Assert expected row counts per year. **Do not silently interpolate** — a gap must
  surface as a failure, not a filled value.
- **Negative prices.** ERCOT West zones post frequent negative prices (to −$244/MWh against a
  −$251 floor). These are real and must not be clipped; they must, however, be reported, since
  they materially affect any correlation on West-zone prices.

## Testing

No new test module — Stage 1 is a script. Correctness rests on:

- the gradient function being imported from already-tested `src/` code;
- inline assertions on row count, timestamp uniqueness, and zone completeness;
- a printed data-quality summary (rows/year, gap count, negative-price share per zone) that must
  be read before the results are interpreted.

## Gate criterion

Stated plainly, because the two branches otherwise read as a contradiction: **the gate is a
data-quality gate, not a results gate.** Both substantive outcomes justify Stage 2 —

- ERCOT behaves *differently* from DOM → a genuine cross-market contrast, clearly worth pursuing.
- ERCOT *reproduces* DOM → a two-market null, which is a stronger result than a one-market null
  and distinguishes "no effect" from "DOM was idiosyncratic."

**The only outcome that stops Stage 2** is ERCOT price data proving too confounded to interpret —
the leading risk being negative-price intervals dominating the West-zone series, which would make
any price correlation there uninterpretable.

Stage 1 therefore succeeds by producing a *trustworthy* answer, not a particular one. The
data-quality summary is the actual gate output.

## Explicit non-goals

- No congestion decomposition (Stage 2).
- No QR-full, GPD, or tail-risk-curve port (Stage 2).
- No facility-level or data-center-specific load. It does not exist publicly in ERCOT; see
  research memo §1.
- No causal claim. This is descriptive. The confounds in research memo §2c — Permian oil & gas
  electrification on the load side, wind export constraints on the price side — mean West Texas
  is not a clean natural experiment and must not be presented as one.
