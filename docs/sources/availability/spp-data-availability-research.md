# SPP as a Comparison Market: Data Availability Research

**Date:** 2026-08-09
**Motivation:** Second of six cross-ISO memos per
`docs/specs/2026-08-09-cross-iso-data-research-design.md`.
**Status:** Research memo. Feeds the Phase-1 checkpoint; no scope decision made here.
**Verification:** Schema and retention claims verified by downloading and reading real files
on 2026-08-09 unless flagged ⚠️. One structural unknown (pre-2025 file naming) survived a
time-boxed probe campaign and is flagged prominently — it is SPP's main open item.
**Corrected 2026-08-10**: that unknown is resolved — see §1 and
`docs/sources/availability/cross-iso-phase2-recon-verification.md` §3.

---

## 1. Headline

**SPP is the market whose *policy posture* is most explicitly pro-data-center — a dedicated
High Impact Large Load (HILL) program promising interconnection agreements within 90 days —
while its *data portal* is the least legible of the markets probed so far.** Everything is
free and ungated (no key, no quota, no registration), with full LMP decomposition and
20-zone load, but the portal's consolidated pre-2025 file naming could not be resolved
programmatically, so **Stage-1 price feasibility is conditional** on a small enumeration
task. The facility-level negative holds here as everywhere.

**Corrected 2026-08-10** (`docs/sources/availability/cross-iso-phase2-recon-verification.md` §3): the naming
problem above is resolved, not conditional. Consolidated pre-2025 archives are per-year
zips at a fixed path (`?path=/{YYYY}/{YYYY}.zip`, verified 200 with ZIP signature) — no
enumeration task was needed. **SPP Stage-1 price feasibility = GO.** See §3, §5, §9.

One premise-relevant wrinkle: SPP's new **CHILL** service (Conditional HILL) grants fast
grid access *in exchange for curtailability during system stress* — meaning future SPP
data-center load traces will have policy-designed curtailment built in. For any later
volatility analysis, SPP large loads are becoming *contractually* price/stress-responsive —
a stronger, formalized version of the ERCOT 4CP endogeneity.

## 2. Facility-level / data-center-specific data hunt

- **No facility-level load telemetry.** SPP publishes no per-resource consumption product;
  demand response participates through registered Demand Response Loads / load-serving
  entities, reported in aggregate. The national negative (CRS R48646 packet) applies
  unmodified.
- **The HILL program creates public *process* artifacts, not data**: monthly Large Load
  Processes Q&A net conferences with posted materials and transcripts (May–July 2026
  verified on the page). These reveal program design — CHILL conditional service,
  HILLGA parallel load+generation studies — but no facility roster or MW registry so far.
- **DC anchors in-footprint** (context, not telemetry): Google's Pryor, OK campus (GRDA
  control zone) is the long-standing anchor; the 2024–26 wave of Oklahoma/Kansas/Missouri
  announcements falls across OKGE/WR/KCPL/SPS zones. ⚠️ Facility-to-zone assignments
  beyond Google-Pryor-GRDA are inference from utility service territory, not verified
  documents — verify per facility before any locational use.
- Settlement-location name scan (1,609 locations in the 2026-08-06 DA file, ERCOT-§1
  methodology): no data-center/crypto/hyperscaler-patterned names. Location names are
  utility/plant/hub codes; nothing like MISO's `GRE.REC.DATA` surfaced.

## 3. What SPP does better / worse than PJM + ERCOT

**Better:**

- **Full LMP decomposition, free**: every settlement location carries
  `LMP, MLC, MCC, MEC` (verified in-file) — congestion and loss split out, PJM-grade,
  at 1,609 locations including the two system hubs (`SPPNORTH_HUB`, `SPPSOUTH_HUB`,
  both verified in-roster) and per-utility hubs.
- **5-minute RTBM prices are the native market cadence** and the 5-minute interval files
  are directly downloadable (`By_Interval/{DD}/RTBM-LMP-SL-{YYYYMMDDHHMM}.csv`,
  verified 200).
- **Dual timestamps in price files**: local interval + `GMTIntervalEnd` in the same row —
  the least ambiguous time encoding of any market probed.
- **No gates**: portal.spp.org needs no key, no login, no quota.

**Worse:**

- **Corrected 2026-08-10** (`docs/sources/availability/cross-iso-phase2-recon-verification.md` §3): the
  "opaque pre-2025 naming" problem below is resolved — no browser-UI enumeration needed.
  The listing API never revealed it, but the consolidated pre-2025 archives are per-year
  zips at a fixed, guessable path: `https://portal.spp.org/file-browser-api/download/
  {fileset}?path=/{YYYY}/{YYYY}.zip` (verified 200 with ZIP signature; `hourly-load`
  2011–2024, `da-lmp-by-settlement-location` verified 2022–2024). **SPP Stage-1 price
  feasibility flips CONDITIONAL → GO** (see §9). Original open item, for the record: year
  folders back to 2011 render in the UI, but the file-browser's listing API returns empty
  to every programmatic shape tried (plain, JSON-Accept, XHR headers, session cookies,
  same-origin browser fetch), and current daily filenames 404 before ~2025.
- **Two footprint changes, one very recent**: the Integrated System (WAUE et al.) joined
  October 2015, and **RTO West expansion went live 2026** — the load roster already
  carries `WACM`, `WAUW`, `PRPA` (verified in the 2026-08-06 file). Any SPP trend window
  crossing April 2026 must handle a boundary jump *mid-analysis-window* — worse than
  MISO's 2013 join, which at least sits a decade back.
- **Market history is short anyway**: the Integrated Marketplace (DA + RTBM with LMPs)
  dates to March 2014; before that only the EIS imbalance market (2007–14).

## 4. Zonal load archive

**Series: hourly load by control zone, long format, `Market Hour, Balancing Area Name,
Control Zone Name, Forecast Area Type, Load MW` (verified).**

- **20 control zones** in the current file: CSWS, EDE, GRDA, INDN, KACY, KCPL, LES, MPS,
  NPPD, OKGE, OPPD, PRPA, SECI, SPRM, SPS, WACM, WAUE, WAUW, WFEC, WR — the finest zonal
  granularity of any market probed (vs. MISO's 6 groups, ERCOT's 8 zones). PRPA/WACM/WAUW
  are RTO-West additions; WAUE arrived with the 2015 IS join. **Corrected 2026-08-10**:
  this 20-zone long-format roster is the 2026-03-25 → present era only. 2011–2015 is wide
  format with 16 zones (no WAUE); 2016–2025 is wide with 17 zones (WAUE present, the
  Oct-2015 IS join); 2026-03-25 → is long with 20 zones
  (`docs/sources/availability/cross-iso-phase2-recon-verification.md` §3 era table).
- **Timezone — Corrected 2026-08-10, RESOLVED.** `Market Hour` is GMT, hour-ending,
  verified on both 2025-11-02 (fall back, 25 rows, `11/02 06:00` → `11/03 06:00`) and
  2026-03-08 (spring forward, 23 rows, `03/08 07:00` → `03/09 05:00`). Row counts follow
  the **local** Central day (23/24/25); the timestamp itself is GMT — convert to
  America/Chicago before any join, and cross-check against the DA LMP files' explicit
  local + `GMTIntervalEnd` columns in the same row.
- **Verified access**: `portal.spp.org/file-browser-api/download/hourly-load?path=
  /{YYYY}/DAILY_HOURLY_LOAD-{YYYYMMDD}.csv` for 2025 → present (200 at 2025-08-06 and
  2026-08-06; 404 at 2024-08-06 and every earlier year probed).
- **Schema break**: wide format until **2026-03-24**, long after (per the gridstatus
  parser constant; the 2026-08 file verified long). A pull spanning the break parses two
  families.
- **Pre-2025 history — Corrected 2026-08-10.** The consolidated naming is resolved (§3):
  `…download/hourly-load?path=/{YYYY}/{YYYY}.zip` returns the full year as a ZIP,
  verified 2011–2024 (2025, 2026 → 404, as expected — those years are daily-file only).
  **⚠️ Double-count trap inside the zips**: each year's zip holds both daily CSVs
  (`DAILY_HOURLY_LOAD-YYYYMMDD.csv`, present 2019 partial, dense 2022–2024) *and* 12
  monthly rollups (`HOURLY_LOAD-YYYYMM.csv`) covering the same hours — globbing the zip
  double-counts the year. **The monthly family is the only one present in every archived
  year (2011–2024)** — parse from monthlies, not dailies, for the annual-zip era.
  Backstops verified reachable: **EIA-930** (SPP BA total, hourly, 2015 →) and
  **FERC-714** (planning-area hourly, annual filings, decades deep) — totals only, no
  control-zone split.
- **⚠️ CF+NC summing rule (long-format era only, 2026-03-25 →)**: `Forecast Area Type`
  takes values `CF` and `NC`; seven zones (KCPL, LES, NPPD, OPPD, WACM, WAUE, WR) carry
  both. A pivot on `(Market Hour, Control Zone Name)` alone collides on those seven and
  silently drops 5–31% of their load — the wide column equals **CF + NC**, so long-format
  parsing must sum both types per (hour, zone).

## 5. Price archive

- **DA LMP by settlement location** (`da-lmp-by-settlement-location` fileset):
  `/{YYYY}/{MM}/By_Day/DA-LMP-SL-{YYYYMMDD}0100.csv`, ~38.6K rows/day = 1,609 locations
  × 24 h, full decomposition. Verified 200 at 2025-08 and 2026-08; 404 at 2024-08 and
  earlier under the daily-file naming. **Corrected 2026-08-10**: older years are not
  missing — `…?path=/{YYYY}/{YYYY}.zip` returns the full year as a ZIP (verified 2024:
  200, ~294 MB; 2025: 404, as expected — daily-file only), same era boundary as load
  (annual zips through 2024, dailies 2025 →). The locked common-overlap headline window
  (2023-01 → 2025-05) is fully covered on both the load and price sides.
- **RTBM (real-time) LMP** (`rtbm-lmp-by-location`): 5-minute interval files verified
  (`By_Interval/{DD}/RTBM-LMP-SL-{YYYYMMDDHHMM}.csv`, 200 at 2026-08-06 01:05). Annual
  zip verified for 2022 (200 ZIP, **5.02 GB/yr**) — confirms 5-minute RTBM stays out of
  Stage-1 scope on size grounds alone. Daily rollups (`By_Day/RTBM-LMP-DAILY-SL-…`)
  404'd at every date/suffix tried; naming unresolved, but out of scope for Stage 1.
- **Window fit — Corrected 2026-08-10, CONDITIONAL → GO**: the "opaque pre-2025 naming"
  blocker is resolved (§3): `?path=/{YYYY}/{YYYY}.zip` gives the full annual archive with
  no browser-UI enumeration needed. **SPP Stage-1 price feasibility = GO.** The
  DOM-matched and common-overlap windows are both covered by verified annual-zip +
  daily routes.
- WEIS (Western Energy Imbalance Service, pre-RTO-West) prices exist as a separate
  fileset — relevant only if the western zones' pre-2026 history is ever wanted.

## 6. Market-specific confounds

- **Wind dominance (the FWEST analog, strongest of any market).** SPP is the most
  wind-penetrated RTO in North America — record instantaneous renewable penetration
  crossing 90%, frequent negative prices in the west (SPS/Panhandle corridor), and its
  market monitor's State of the Market reports document persistent congestion-driven
  negative pricing. Any congestion-on-load regression in western zones would be
  wind-export-driven, not load-driven. ⚠️ Exact wind-share figures to be pinned from the
  2024 State of the Market report in Phase 2.
- **Footprint changes**: Oct 2015 (IS join) and **April 2026 RTO West** — the latter
  inside every candidate analysis window; zone-level series for legacy zones remain
  clean, but SPP-total series jump.
- **CHILL-designed curtailment (forward-looking).** Conditional large-load service makes
  curtailment-during-stress a *contract feature*; as CHILL customers energize, SPP load
  traces acquire policy-driven price-responsiveness — endogeneity by design, beyond
  ERCOT's 4CP avoidance behavior.
- **Storms**: Uri (Feb 2021) produced SPP's first-ever EEA3 load sheds; Elliott
  (Dec 2022) stressed the south. Both sit before a 2023+ window; inside any longer load
  trend.
- **Schema/format churn**: the 2026-03-24 wide→long load break plus the consolidated
  archive naming — SPP has the most parser families per series of the markets probed.

## 7. Interconnection queue / large-load tracking

- **HILL program** (dedicated public page + monthly Q&A materials): CHILL conditional
  service (fast access, curtailable), HILLGA (parallel study of loads with co-located
  generation), interconnection agreements targeted **within 90 days** — SPP explicitly
  marketing itself as the fastest plug-in destination for data centers.
- **Scale**: SPP anticipates a **near-doubling of peak load within the next 10 years**
  (Utility Dive, on the board-approved accelerated large-load policy).
- **No public large-load queue** with MW-by-stage granularity (ERCOT-style) found; the
  generation interconnection queue is public, and large-load visibility comes through
  the HILL Q&A materials and utility announcements. ⚠️ The Q&A material zips
  (May–Jul 2026, links verified on the HILL page) may contain request-volume figures —
  worth mining in Phase 2.
- Google Pryor (GRDA zone) remains the anchor operating DC; the 2024–26 announcement
  wave (OK/KS/MO) is tracked better by the EEI large-load list and DELTa tariff database
  (shared packet) than by anything SPP publishes.

## 8. Academic / institutional dataset leads

- **SPP Market Monitoring Unit State of the Market reports** (annual, public PDFs) —
  authoritative wind-penetration, negative-price, and congestion statistics for §6.
- **SPP ITP (Integrated Transmission Planning) futures** — load-growth scenarios
  underlying the near-doubling claim; public planning documents.
- Shared packet applies: LBNL/Brattle retail-price rows for SPP states, Frick & Lam +
  DELTa for OK/KS large-load tariffs, EEI project list, Grid Strategies national report.
- No SPP-region academic dataset lead comparable to UT-TRAIL surfaced. (Oklahoma State /
  KU energy programs exist but no dataset claims found — thin section, honestly thin.)

## 9. Concrete Stage-1 pull spec

**Corrected 2026-08-10** (`docs/sources/availability/cross-iso-phase2-recon-verification.md` §3): **Stage-1
verdict flips CONDITIONAL → GO.** The consolidated-naming blocker is resolved — no
browser-UI enumeration needed; annual zips at `?path=/{YYYY}/{YYYY}.zip` cover the
pre-2025 years on both load and price.

| Need | Source (verified pattern) | Est. volume |
|---|---|---|
| Zonal load 2025 → present | `hourly-load` dailies (~40 KB/day, ~580 files) | ~23 MB |
| Zonal load 2011 → 2024 | `hourly-load?path=/{YYYY}/{YYYY}.zip`, **monthly rollups only** (double-count trap: zips also hold dailies covering the same hours) | 0.58–1.45 MB/yr |
| DA LMP 2025 → present | `da-lmp-by-settlement-location` By_Day dailies (~4 MB/day) | ~2.3 GB raw → extract hubs |
| DA LMP 2022 → 2024 | `da-lmp-by-settlement-location?path=/{YYYY}/{YYYY}.zip` | ~280–294 MB/yr |
| RTBM 5-min | By_Interval files (288/day); annual zip confirmed 5.02 GB/yr | out of Stage-1 scope |

- **Horse race design**: 20 zones × 2 system hubs (+ per-utility hubs optional), DA.
  Window 2023-01 → present to match MISO, else 2011-01 → for a full-market-life run
  (subject to the era table in §4 for parse family/schema/roster per date range).
- **Prerequisites**: none beyond stock pandas (CSV/ZIP throughout — no Excel engines
  needed, unlike MISO). Politeness throttling on portal.spp.org.
- **Timezone — RESOLVED**: `Market Hour` is GMT hour-ending; convert to America/Chicago
  before any join (see §4).
- **Recommendation to checkpoint**: run SPP Stage-1 now — the naming blocker is gone;
  implement from the §4 era table (parse family, schema, roster, CF/NC rule, and
  datetime format each change on a different date) rather than independent conditionals,
  and never glob a zip.

## 10. Source index

- Portal file API (download): `https://portal.spp.org/file-browser-api/download/{fileset}?path=/...`
  — filesets verified: `hourly-load`, `da-lmp-by-settlement-location`, `rtbm-lmp-by-location`
- Portal pages (interactive trees): https://portal.spp.org/pages/hourly-load ,
  https://portal.spp.org/pages/da-lmp-by-settlement-location
- HILL program: https://spp.org/markets-operations/high-impact-large-load-hill-integration/
  (incl. monthly Q&A materials/transcripts, May–Jul 2026)
- Accelerated large-load policy: https://www.utilitydive.com/news/southwest-power-pool-spp-large-load-interconnection-policy/760357/
- SPP 2024 State of the Market: https://www.spp.org/documents/73953/2024_annual_state_of_the_market_report.pdf
- Renewable-penetration record coverage: https://www.spglobal.com/energy/en/news-research/latest-news/electric-power/031521-spp-sets-new-renewable-penetration-record-as-power-prices-to-fall-to-negative
- gridstatus SPP module (endpoint corroboration; wide-format end constant):
  https://github.com/gridstatus/gridstatus/blob/master/gridstatus/spp.py
- EIA-930 (SPP BA total backstop): https://www.eia.gov/electricity/gridmonitor/
- FERC-714 (deep planning-area hourly backstop): https://www.ferc.gov/industries-data/electric/general-information/electric-industry-forms/form-no-714-annual-electric
- Shared packet: CRS R48646 (see design spec)
