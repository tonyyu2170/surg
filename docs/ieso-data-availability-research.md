# IESO as a Comparison Market: Data Availability Research

**Date:** 2026-08-09
**Motivation:** Fourth of six cross-ISO memos per
`docs/superpowers/specs/2026-08-09-cross-iso-data-research-design.md`.
**Status:** Research memo. Feeds the Phase-1 checkpoint; no scope decision made here.
**Verification:** Every schema and depth claim verified by downloading and reading real
files from `reports-public.ieso.ca` on 2026-08-09 unless flagged ⚠️.

---

## 1. Headline

**IESO offers the deepest, cleanest zonal load archive in the entire project — 10 zones,
hourly, 2003 → present, one tidy CSV per year, fixed-EST with no DST rows — and the most
complicated price story.** Ontario switched market designs mid-stream: the uniform HOEP
price ran 2002 → April 2025, then Market Renewal introduced nodal/zonal LMPs on
May 1, 2025 — and the LMP-era public files appear to be a **~90-day rolling window**
(⚠️ listing-based inference), meaning the durable price series for any backward-looking
analysis is HOEP. Ontario also contributes the project's sharpest endogeneity specimen:
the Industrial Conservation Initiative, under which large (Class A) consumers shave the
five annual system peaks to cut Global Adjustment charges — peak-shaving so
institutionalized that IESO runs a public "Peak Tracker" to help them do it. The
facility-level negative holds; IESO's 2026 planning outlook expects data centres at
**8.6% of Ontario demand by 2050** — a real but EV-dominated growth story.

## 2. Facility-level / data-center-specific data hunt

- **No facility-level load telemetry.** The national negative (CRS R48646) has its
  Canadian counterpart: no per-facility consumption product exists in IESO public data;
  Class A/ICI participation details are settlement-confidential.
- **The 2026 "Large Computational Loads" engagement is process, not data (verified):**
  IESO identified "a clear gap [in] technical performance requirements … for the
  integration of large computational loads such as AI facilities and cryptocurrency
  facilities" and ran a formal 2026 stakeholder process (May–July, requirements document
  + feedback from Toronto Hydro, Hydro One, Hydro Ottawa, Enova, and consultants; to be
  folded into Market Rules). Excellent evidence of *where* the loads are connecting
  (the LDCs that filed), zero MW-level data.
- Pricing-location roster (verified, ~1,046 locations in the DA LMP file): plant/station
  codes; no data-center-patterned names on scan — no MISO-style `GRE.REC.DATA` find.
- **The real channels**: LDC rate filings (Toronto Hydro et al. at the OEB), and the APO
  forecast (§7). Toronto is Canada's largest DC market; its load sits inside the
  `Toronto` zone series along with everything else.

## 3. What IESO does better / worse than PJM + ERCOT

**Better:**

- **Load archive quality is the best in the project**: one CSV per year
  (`PUB_DemandZonal_{YYYY}.csv`), 10 zones + Ontario total, hourly, **2003 → present all
  verified 200**, self-describing header, no key, no quota, no registration. Ontario
  total (`PUB_Demand_{YYYY}.csv`) reaches 2002. Structural bonus: files carry exactly
  24 rows/day year-round (verified row count) — fixed EST, no DST handling at all.
- **MRP-era prices come pre-decomposed**: `Delivery Hour, Pricing Location, LMP,
  Energy Loss Price, Energy Congestion Price` (verified) — congestion as a column,
  PJM-grade, plus dedicated zonal and Ontario-zonal-price reports and 5-minute real-time
  LMP files.
- Everything sits in one browsable open directory (`reports-public.ieso.ca/public/`) —
  the most transparent file layout of the six markets.

**Worse:**

- **The price regime splits mid-window.** HOEP (uniform, no locational signal) until
  2025-04-30; LMPs after. No congestion series exists before May 2025 anywhere in
  Ontario — the pre-2025 horse race can only use a uniform price, answering "does
  *system* price track level vs. volatility," never a locational question.
- ⚠️ **LMP-era public retention looks like a ~90-day rolling window**: the dated file
  listings for `RealtimeEnergyLMP` and `DAHourlyOntarioZonalPrice` begin ~90 days before
  today (earliest observed 2026-05-08/11 on 2026-08-09). If no durable archive exists
  elsewhere, the LMP era is only analyzable prospectively (collect-as-you-go) — the
  ERCOT 5-minute retention trap, applied to an entire market era. **Phase-2 task: locate
  a durable MRP-era archive or start a collector.**
- Prices are CAD/MWh — standardized coefficients absorb it; raw cross-market levels
  don't compare.
- Zonal *prices* exist only post-MRP; the deep zonal series is load-only.

## 4. Zonal load archive (verified)

**Series: `https://reports-public.ieso.ca/public/DemandZonal/PUB_DemandZonal_{YYYY}.csv`**

- Schema (verified): comment lines prefixed `\\`, then
  `Date, Hour, Ontario Demand, Northwest, Northeast, Ottawa, East, Toronto, Essa, Bruce,
  Southwest, Niagara, West, Zone Total, Diff`. Hour = 1–24 hour-ending, **fixed EST**
  (24 rows every day; 5,284 lines for 2026-to-date ✓).
- **Depth verified**: 2003 and 2004 files return 200; 2026 file current through
  yesterday. One file per year — a full backfill is **24 files, ~4 MB total**, the
  cheapest acquisition in the project.
- `Diff` column = Ontario Demand − Zone Total (zonal sums don't exactly reconcile —
  embedded/loss accounting); parser keeps both and asserts tolerance.
- **The zone map is DC-relevant as-is**: `Toronto` isolates Canada's largest DC market;
  `Ottawa` second; `Northwest`/`Northeast` are the low-DC hydro zones — a natural
  within-market treatment/control geography, better aligned to the question than
  MISO's zone-groups.
- ⚠️ "Ontario Demand" excludes load served by embedded (distribution-connected)
  generation — Ontario has GW-scale embedded solar/CHP, so the same
  metered-vs-consumption caveat as CAISO applies, milder.

## 5. Price archive (verified)

**Two eras, split 2025-05-01 by Market Renewal:**

| Era | Series | Access | Depth |
|---|---|---|---|
| 2002 → 2025-04 | **HOEP** (uniform Ontario hourly energy price) + predispatch + OR prices | `PriceHOEPPredispOR/PUB_PriceHOEPPredispOR_{YYYY}.csv` — annual CSVs | 2002 file verified 200 |
| 2025-05 → | **Nodal LMP** (DA hourly, predispatch, RT 5-min) + 10-zone zonal prices + Ontario Zonal Price (load settlement) | `DAHourlyEnergyLMP/`, `RealtimeEnergyLMP/` (CSV, decomposed); `DAHourlyZonal/`, `DAHourlyOntarioZonalPrice/` (XML, daily files) | ⚠️ dated files appear ~90-day rolling; durable archive unlocated |

- DA LMP schema (verified): `Delivery Hour, Pricing Location, LMP, Energy Loss Price,
  Energy Congestion Price`; ~1,046 pricing locations; 25.1K rows/day. RT 5-min files
  (`PUB_RealtimeEnergyLMP_{YYYYMMDDHH}.csv`, ~516 KB/hour-file) same idea.
- **Horse-race implication**: 2022-10 → 2025-04 runs on HOEP (uniform — fine for the
  level-vs-volatility question, mirrors what ERCOT hub regressions test); the LMP era
  adds locational congestion but only ~15 months exist and possibly only ~90 days are
  publicly retained. Statistical use of the LMP era is prospective, not retrospective.

## 6. Market-specific confounds

- **ICI / Global Adjustment — the strongest peak-response endogeneity in the project.**
  Class A consumers pay Global Adjustment (a large non-energy charge recovering
  contracted generation costs) pro-rata to their share of the **top five Ontario demand
  peaks**; shaving those hours cuts bills massively, an industry of peak-prediction
  services exists, and **IESO itself publishes a "Peak Tracker"** to watch candidate
  peaks. Consequences: (a) observed zonal load *at system peaks* is behaviorally
  suppressed — load data is endogenous to forecast peaks by design; (b) any data center
  electing Class A inherits this incentive. This must be front-of-caption in any IESO
  volatility analysis: Ontario's top-hour load shape is partly a policy artifact.
- **Regime change 2025-05-01** (Market Renewal): price formation, dispatch, and
  settlement all changed — any price series crossing the boundary mixes mechanisms;
  the load series is unaffected.
- **Embedded generation** nets out of "Ontario Demand" (§4) — CAISO-style metered-load
  caveat, milder scale.
- **Currency** (CAD) and **holiday/weather calendar** differences vs. US markets —
  standardization handles the first; the second is noise.
- Global Adjustment also means HOEP alone understates the all-in price large consumers
  face — HOEP-based horse races measure the *wholesale energy* signal only; fine for
  comparability, worth one caption line.

## 7. Interconnection queue / large-load tracking

- **2026 Annual Planning Outlook (verified page):** Ontario demand forecast to grow
  **65%** long-term; **data centres = 8.6% of Ontario demand in 2050, ~60% above the
  prior forecast**; EVs remain the largest growth driver (>half of the new "growth
  margin," 15% of 2050 consumption). The APO now explicitly buckets DCs into a
  **"growth margin" of particularly *variable* demand drivers** — IESO's institutional
  statement that DC materialization is uncertain, a useful quotable.
- **Large Computational Loads engagement (2026)**: technical connection requirements for
  AI/crypto facilities entering the Market Rules — Ontario's counterpart to ERCOT's
  large-load process and SPP's HILL, at the requirements (not queue) stage.
- **No public large-load queue**; connection assessments run through the standard CAA
  process (Market Manual 1.4) and LDCs. The feedback-filer list (Toronto Hydro, Hydro
  One, Hydro Ottawa, Enova/Kitchener-Waterloo) sketches the connection geography.

## 8. Academic / institutional dataset leads

- **IESO APO data files** — the APO publishes demand-forecast module outputs; check for
  zone-level and driver-level (DC) breakouts in the downloadable tables (⚠️ unverified
  whether zone×driver granularity is public).
- **OEB (Ontario Energy Board) rate filings** — LDC-level load forecasts incl. large
  new connections (Toronto Hydro DC connections appear here if anywhere).
- **Peak Tracker + ICI documentation** — for modeling the endogeneity, IESO's own pages
  plus the commercial peak-prediction literature (CPower, Workbench) describe the
  response function explicitly.
- Shared packet applies loosely (CRS/LBNL are US-scoped; DELTa has no Ontario rows) —
  the Canadian analog literature is thinner; flag honestly.

## 9. Concrete Stage-1 pull spec

| Need | Source | Est. volume |
|---|---|---|
| Zonal load 2003 → present | 24 annual `PUB_DemandZonal_{YYYY}.csv` | ~4 MB, ~200K hourly rows |
| Ontario total 2002 → | annual `PUB_Demand_{YYYY}.csv` (optional pre-2003 extension) | trivial |
| HOEP 2002 → 2025-04 | annual `PUB_PriceHOEPPredispOR_{YYYY}.csv` | ~24 files, trivial |
| LMP era 2025-05 → | ⚠️ retention question first; else prospective collector | — |

- **Horse race**: 11 load series (10 zones + Ontario) × HOEP, window 2022-10-02 →
  2025-04-30 (~2.6 yr — shorter than DOM's 3.7 but fully covered); optionally extend to
  the full HOEP era for a long-run version. LMP-era locational analysis: prospective
  only, pending the retention answer.
- **Trend window**: 2003 → present, 23 years — the longest clean zonal series in the
  project, with the ICI caveat on peak-hour interpretation (ICI in current form since
  ~2011 — ⚠️ pin exact program-change dates in Phase 2 so the trend can be split).
- No new dependencies (CSV; stock pandas). XML parsing needed only if the zonal-price
  era is pursued.
- **Recommendation to checkpoint**: run IESO load trends + HOEP horse race now; treat
  the LMP era as a separate, prospective mini-project (and decide whether to stand up a
  collector before the rolling window buries more history).

## 10. Source index

- Public reports root (browsable): https://reports-public.ieso.ca/public/
- Zonal demand: `DemandZonal/PUB_DemandZonal_{YYYY}.csv` (2003 →, verified)
- Ontario demand: `Demand/PUB_Demand_{YYYY}.csv` (2002 →, verified)
- HOEP + predispatch + OR: `PriceHOEPPredispOR/PUB_PriceHOEPPredispOR_{YYYY}.csv` (2002 →, verified)
- MRP LMP era: `DAHourlyEnergyLMP/`, `RealtimeEnergyLMP/` (CSV, decomposed, verified);
  `DAHourlyZonal/`, `DAHourlyOntarioZonalPrice/` (XML, dated daily, ⚠️ rolling)
- Large Computational Loads engagement: https://www.ieso.ca/Sector-Participants/Engagement-Initiatives/Engagements/Technical-Requirements-for-Large-Computational-Loads-Connecting-to-the-Ontario-Power-System
- 2026 APO summary: https://ieso.ca/Sector-Participants/Planning-and-Forecasting/Annual-Planning-Outlook/2026-APO-Summary
- Peak Tracker (ICI mechanism): https://www.ieso.ca/Sector-Participants/Settlements/Peak-Tracker
- ICI explainers (mechanism documentation): https://workbenchenergy.com/peak-prediction/ici-and-global-adjustment/ ; https://cpowerenergy.com/is-global-adjustment-in-ontario-here-to-stay/
- Ontario DC connection legal overview: https://www.torys.com/en/our-latest-thinking/publications/2025/07/connecting-data-centres-in-ontario
- gridstatus IESO module (endpoint corroboration): https://github.com/gridstatus/gridstatus/blob/master/gridstatus/ieso.py
- Shared packet: CRS R48646 (see design spec)
