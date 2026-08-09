# SPP as a Comparison Market: Data Availability Research

**Date:** 2026-08-09
**Motivation:** Second of six cross-ISO memos per
`docs/superpowers/specs/2026-08-09-cross-iso-data-research-design.md`.
**Status:** Research memo. Feeds the Phase-1 checkpoint; no scope decision made here.
**Verification:** Schema and retention claims verified by downloading and reading real files
on 2026-08-09 unless flagged ⚠️. One structural unknown (pre-2025 file naming) survived a
time-boxed probe campaign and is flagged prominently — it is SPP's main open item.

---

## 1. Headline

**SPP is the market whose *policy posture* is most explicitly pro-data-center — a dedicated
High Impact Large Load (HILL) program promising interconnection agreements within 90 days —
while its *data portal* is the least legible of the markets probed so far.** Everything is
free and ungated (no key, no quota, no registration), with full LMP decomposition and
20-zone load, but the portal's consolidated pre-2025 file naming could not be resolved
programmatically, so **Stage-1 price feasibility is conditional** on a small enumeration
task. The facility-level negative holds here as everywhere.

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

- **The portal's history is opaque.** Year folders back to 2011 render in the UI, but the
  file-browser's listing API returns empty to every programmatic shape tried (plain,
  JSON-Accept, XHR headers, session cookies, same-origin browser fetch), and current
  daily filenames 404 before ~2025. Old files exist under consolidated names that only
  the interactive UI reveals. ⚠️ **Open item: enumerate pre-2025 names via a browser
  session (~15-minute task) before any Phase-2 pull design.**
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
  are RTO-West additions; WAUE arrived with the 2015 IS join.
- **⚠️ Timestamps appear to be GMT** — the daily file's `Market Hour` runs 06:00 → 05:00
  (24 hours, verified), i.e. a GMT day over a Central-time market day. Price files carry
  explicit local + GMT columns; the load file carries one unlabeled column. Pin down in
  Phase 2 before any join — this is the SPP version of the ERCOT hour-ending trap.
- **Verified access**: `portal.spp.org/file-browser-api/download/hourly-load?path=
  /{YYYY}/DAILY_HOURLY_LOAD-{YYYYMMDD}.csv` for 2025 → present (200 at 2025-08-06 and
  2026-08-06; 404 at 2024-08-06 and every earlier year probed).
- **Schema break**: wide format until **2026-03-24**, long after (per the gridstatus
  parser constant; the 2026-08 file verified long). A pull spanning the break parses two
  families.
- **Pre-2025 history**: the portal tree shows year folders **2011 → 2026**, so roughly
  15 years of hourly zonal load exist ungated — behind the unresolved consolidated
  naming (§3). Backstops verified reachable: **EIA-930** (SPP BA total, hourly, 2015 →)
  and **FERC-714** (planning-area hourly, annual filings, decades deep) — totals only,
  no control-zone split.

## 5. Price archive

- **DA LMP by settlement location** (`da-lmp-by-settlement-location` fileset):
  `/{YYYY}/{MM}/By_Day/DA-LMP-SL-{YYYYMMDD}0100.csv`, ~38.6K rows/day = 1,609 locations
  × 24 h, full decomposition. **Verified 200 at 2025-08 and 2026-08; 404 at 2024-08 and
  earlier** — same ~current+1yr daily retention pattern as load, older files behind the
  consolidated naming.
- **RTBM (real-time) LMP** (`rtbm-lmp-by-location`): 5-minute interval files verified
  (`By_Interval/{DD}/RTBM-LMP-SL-{YYYYMMDDHHMM}.csv`, 200 at 2026-08-06 01:05). Daily
  rollups (`By_Day/RTBM-LMP-DAILY-SL-…`) 404'd at every date/suffix tried — ⚠️ exact
  daily-rollup naming unresolved, same enumeration task as above.
- **Window fit is the SPP problem**: the DOM-matched horse-race window (2022-10 →, or
  2023-01 → as run for MISO) sits **almost entirely behind the consolidation boundary**.
  Until the old names are enumerated, the only programmatically-verified SPP price window
  is ~2025 → present (~1.5 yr) — too short for a comparable horse race. **SPP Stage-1
  price feasibility = CONDITIONAL.** The data exists (2014 →, visible in the UI tree);
  only the URL grammar is missing.
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

**Conditional on resolving the consolidated naming (one browser-UI session):**

| Need | Source (verified pattern) | Est. volume |
|---|---|---|
| Zonal load 2025 → present | `hourly-load` dailies (~40 KB/day, ~580 files) | ~23 MB |
| Zonal load 2011 → 2024 | portal tree, consolidated names ⚠️ unresolved | unknown; UI shows full years |
| DA LMP 2025 → present | `da-lmp-by-settlement-location` By_Day dailies (~4 MB/day) | ~2.3 GB raw → extract hubs |
| DA LMP 2014 → 2024 | consolidated names ⚠️ unresolved | unknown |
| RTBM 5-min | By_Interval files (288/day) | out of Stage-1 scope |

- **Horse race design (if unblocked)**: 20 zones × 2 system hubs (+ per-utility hubs
  optional), DA (and RTBM daily if naming resolves). Window 2023-01 → present to match
  MISO, else 2014-03 → for a full-market-life run.
- **Prerequisites**: none beyond stock pandas (CSV throughout — no Excel engines needed,
  unlike MISO). Politeness throttling on portal.spp.org.
- **Timezone task**: resolve the load `Market Hour` GMT question with a DST-transition
  day before any join (assert 23/25-hour local days reconstruct correctly).
- **Recommendation to checkpoint**: hold SPP Stage-1 until the 15-minute enumeration
  task runs; do not design around guessed names.

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
