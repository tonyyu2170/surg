# CAISO as a Comparison Market: Data Availability Research

**Date:** 2026-08-09
**Motivation:** Third of six cross-ISO memos per
`docs/specs/2026-08-09-cross-iso-data-research-design.md`.
**Status:** Research memo. Feeds the Phase-1 checkpoint; no scope decision made here.
**Verification:** Every schema and depth claim verified by downloading and reading real
OASIS files on 2026-08-09 unless flagged ⚠️.

---

## 1. Headline

**CAISO is the easiest full-window pull of the six: one keyless API (OASIS) serves hourly
actual load by TAC area and decomposed DAM-hourly + RTM-5-minute prices back past 2010 —
the only market so far that can match the DOM horse-race window (2022-10 →) exactly with
zero enumeration risk.** Two things temper it. First, the story is thin: CEC forecasts only
+1.8 GW of data-center load in the ISO grid by 2030 (vs. MISO's +32 GW of peak by 2046) —
California is the *legacy* DC state, not the growth story. Second, the legacy cluster
itself is invisible: Santa Clara's data centers are served by Silicon Valley Power, a
municipal utility with **no TAC area in the OASIS roster (verified)** — the most important
DC load in California cannot be isolated in CAISO's public load data. And every CAISO load
series carries the strongest confound in the project: behind-the-meter solar has
restructured metered load ("duck → canyon") far more than any data center could.

## 2. Facility-level / data-center-specific data hunt

- **No facility-level load telemetry** — the national negative (CRS R48646) holds; CAISO
  publishes no per-facility consumption product, and its demand response (Proxy Demand
  Resources) reports aggregate.
- **The Santa Clara blind spot, resolved negatively (verified):** the OASIS actual-load
  TAC roster contains `CA ISO-TAC, PGE-TAC, SCE-TAC, SDGE-TAC, VEA-TAC, MWD-TAC` plus
  WEIM member BAAs — **no SVP/Santa Clara entry**. The densest legacy DC cluster in the
  West sits inside a publicly owned utility and cannot be separated in CAISO public data.
  ⚠️ Whether SVP load is embedded in `CA ISO-TAC` totals (via its participation
  arrangements) or excluded entirely needs one Phase-2 check before quoting any
  CAISO-total DC share.
- **CAISO's own institutional posture guarantees the gap**: the ISO "does not study load
  interconnections" (official large-loads page) — load connection, rates, and data live
  with utilities and the CPUC. Facility MW appear, if anywhere, in CPUC proceedings and
  CEC filings (SVP itself files CEC comments — one verified example in the source index).
- **The CEC demand forecast is the partial exception**: it maps large loads to
  **substation locations** for transmission studies — the closest thing to a public
  facility-geography dataset any market in this project has offered (§8).

## 3. What CAISO does better / worse than PJM + ERCOT

**Better:**

- **One API for everything, keyless, deep.** OASIS `SingleZip` serves load and prices
  with uniform GMT timestamps back to the April 2009 MRTU start (2010 pull verified).
  No registration, no quota, no per-file archaeology — the cleanest acquisition path in
  the project.
- **Full decomposition at 5-minute resolution**: `PRC_INTVL_LMP` returns
  `LMP_TYPE ∈ {LMP, MCE, MCC, MCL}` rows (congestion row verified in-file) — RTM 5-min
  congestion history reaching a decade-plus back, free.
- **Uniform GMT** intervals everywhere — no hour-ending ambiguity, no DST file quirks.

**Worse:**

- **Zonal granularity is the coarsest yet for the DC question**: three big IOU TACs
  (PGE/SCE/SDGE) plus VEA and MWD. No county-level or muni-level split; the DC-relevant
  geography (Santa Clara) is absent (§2).
- **The load series measures the wrong thing for trend questions**: metered demand net of
  ~20 GW-scale rooftop solar (§6) — "load level" trends in CAISO are dominated by BTM
  adoption, not consumption growth.
- **Roster churn inside one report**: the ACTUAL load report accumulates WEIM member BAAs
  as they joined (AVA, AZPS, BANC…, verified 37 areas in the 2026 file) — a parser must
  filter to CAISO TACs or watch totals jump as members appear.
- Operational lore ⚠️: OASIS enforces informal rate limits and ~31-day maximum query
  windows; pulls must chunk and throttle (not verified to the limit here; universally
  reported by client libraries including gridstatus).

## 4. Zonal load archive (verified)

**Series: OASIS `SLD_FCST`, `market_run_id=ACTUAL` — "Total Actual Hourly Integrated
Load" by TAC area.**

- Schema (verified): `INTERVALSTARTTIME_GMT, INTERVALENDTIME_GMT, LOAD_TYPE, OPR_DT,
  OPR_HR, OPR_INTERVAL, MARKET_RUN_ID, TAC_AREA_NAME, LABEL, XML_DATA_ITEM, POS, MW,
  EXECUTION_TYPE, GROUP`; hourly rows per area; ~889 rows/day across 37 areas in 2026.
- **Depth verified**: a 2010-08-06 request returns real data (`CA ISO-TAC` 17,389 MW
  first hour). Nominal start = MRTU, April 2009. ⚠️ Exact earliest date unprobed; confirm
  during the pull.
- **Analysis subset**: `CA ISO-TAC` (system) + `PGE-TAC, SCE-TAC, SDGE-TAC, VEA-TAC,
  MWD-TAC`. Everything else in the roster is WEIM members (their actuals enter the report
  in later years — do not let the panel absorb them silently).
- Real-time 5-minute demand exists only as short-retention dashboard feeds (Today's
  Outlook) — no deep 5-min actual-load history, same as every other market.
- Access: `https://oasis.caiso.com/oasisapi/SingleZip?queryname=SLD_FCST&market_run_id=
  ACTUAL&startdatetime=…&enddatetime=…&version=1&resultformat=6` → zip of CSV. Must be
  **https** (http returns empty).

## 5. Price archive (verified)

- **DAM hourly**: `PRC_LMP`, `market_run_id=DAM`, `version=12`, per node —
  `DLAP_PGAE-APND` verified; DLAPs exist per IOU TAC (`DLAP_{PGAE,SCE,SDGE,VEA}-APND`)
  plus trading hubs `TH_NP15_GEN-APND, TH_SP15_GEN-APND, TH_ZP26_GEN-APND`.
- **RTM 5-minute**: `PRC_INTVL_LMP`, `version=3` — verified returning `MCC` rows at
  `TH_NP15_GEN-APND`.
- Decomposition: `LMP_TYPE` rows = LMP, MCE (energy), MCC (congestion), MCL (loss) —
  PJM-grade, both markets, full depth.
- Depth: same OASIS window as load (2009-04 →) — **the DOM-matched window 2022-10-02 →
  is fully coverable**, the only market of the six where this needs no workaround.
- Node-level pulls beyond DLAPs/hubs are possible (`grp_type=ALL_APNODES` returns the
  full ~16K-node set per interval) but unnecessary for Stage 1.

## 6. Market-specific confounds

- **Behind-the-meter solar is the dominant confound (the FWEST analog, and then some).**
  California's ~20 GW-scale rooftop fleet nets out of metered load, reshaping the daily
  profile ("duck curve" → "canyon") and pushing minimum net load records lower each
  spring. Two consequences: (a) *level trends* in metered load conflate consumption
  growth with BTM adoption — a falling or flat CAISO load trend says nothing about
  consumption; (b) *volatility trends* pick up solar-ramp structure (evening ramp
  steepening) unrelated to any load-side behavior. Every Stage-1 output needs this
  caveat in-caption; ⚠️ exact BTM GW figure to pin from CEC/CAISO sources in Phase 2.
- **Boundary exclusions**: LADWP, SMUD/BANC, and other non-ISO BAs are outside CAISO
  data entirely — "California load" ≠ CAISO load; SVP ambiguity in §2.
- **WEIM roster growth** inside the ACTUAL report (§4) — filter, don't aggregate.
- **Event contamination**: August 2020 rolling blackouts, September 2022 heat emergency
  (all-time 52-GW peak), wildfire/PSPS de-energizations — all inside any long window;
  the 2022-10 → horse-race window dodges the worst but keeps ordinary heat events.
- **Peak-response endogeneity**: milder than 4CP/ICI — no single coincident-peak
  transmission charge; CPUC TOU/demand-charge structures and DR programs spread the
  response. Note and move on.

## 7. Interconnection queue / large-load tracking

- **CAISO's institutional answer: not our queue.** The ISO does not study load
  interconnections (verified, official page); utilities and the CPUC govern load
  connection and cost recovery; the ISO consumes the **CEC demand forecast** (large
  loads mapped to substations) for its transmission planning. There is no CAISO
  large-load queue to mine — the ERCOT funnel has no counterpart, by design.
- **Forecast numbers (CEC, as relayed by CAISO's large-loads page, Jan 2026 vintage):**
  data-center load in the ISO grid **+1.8 GW by 2030, +4.9 GW by 2040** — with visible
  vintage churn (the June 2025 vintage said +2.3 GW by 2030 / +3.3 GW by 2035). System
  peak forecast: **48.3 GW (2024) → ~68 GW (2040)** (CEC IEPR via RTO Insider), much of
  the increase attributed to data centers — yet still an order of magnitude below MISO's
  DC growth in absolute terms.
- 2022 CEC–CPUC–CAISO MOU tightened forecast→planning linkage; stakeholder processes on
  large-load roles are active (comment dockets verified on the stakeholder center).

## 8. Academic / institutional dataset leads

- **CEC IEPR demand forecast** — the strongest institutional dataset of any market
  researched: public, annually revised, includes data-center scenarios, and maps large
  loads to **substation locations**. If sub-question-2-style projection work ever extends
  to CAISO, this replaces JLARC as the projection backbone. Public workshop data files
  accompany each IEPR cycle.
- **SVP's CEC filings** (verified example in index) — Santa Clara's own load-growth
  statements, the only public numbers for the invisible cluster.
- FactSet "From Duck to Canyon" and the gridstatus.io blog for profile-evolution
  framing; LBNL/Brattle + DELTa from the shared packet (California rows).

## 9. Concrete Stage-1 pull spec

| Need | Source | Est. volume |
|---|---|---|
| Load: 6 TAC series, 2009-04 → present | OASIS `SLD_FCST/ACTUAL`, ~31-day chunks (~205 requests) | ~1.4M rows long → ~150K panel rows |
| DAM LMP: 4 DLAPs + 3 hubs, 2022-10 → present | OASIS `PRC_LMP/DAM` per node (~48 chunks × 7 nodes) | ~235K node-hours |
| RTM 5-min (optional) | `PRC_INTVL_LMP` | out of Stage-1 scope |

- All keyless; throttle ~5–10 s between requests; chunk ≤ 31 days (⚠️ verify limit
  empirically at pull time).
- **Horse race**: 6 load series × 7 price nodes (~42 cells), DAM (RTM optional), on the
  exact DOM window 2022-10-02 → — no window compromise needed.
- **Level/volatility trend window**: 2009-04 → present (17 years), with the BTM-solar
  caveat stapled to every level-trend figure.
- No new dependencies (CSV in zips; stock pandas).
- **Recommendation to checkpoint**: CAISO is the lowest-risk, lowest-cost pull of the
  six — but pre-commit to the BTM-solar framing before running, or the volatility trend
  will be misread.

## 10. Source index

- OASIS API (verified): `https://oasis.caiso.com/oasisapi/SingleZip?queryname=…` —
  `SLD_FCST` v1 (load), `PRC_LMP` v12 (DAM), `PRC_INTVL_LMP` v3 (RTM 5-min);
  resultformat=6 (CSV-in-zip); https required
- CAISO large loads (official role + CEC numbers): https://www.caiso.com/generation-transmission/load/large-loads
- CEC–CPUC–ISO MOU (Dec 2022): https://www.caiso.com/documents/iso-cec-and-cpuc-memorandum-of-understanding-dec-2022.pdf
- CEC IEPR forecast coverage: https://www.rtoinsider.com/96383-cec-data-centers-demand-forecast/
- SVP (Santa Clara) CEC filing example: https://efiling.energy.ca.gov/GetDocument.aspx?tn=267866&DocumentContentId=104873
- Duck→canyon profile evolution: https://insight.factset.com/from-duck-to-canyon-how-caisos-load-profile-has-evolved
- CAISO solar/storage evolution: https://blog.gridstatus.io/caiso-solar-storage-spring-2025/
- Today's Outlook (real-time only): https://www.caiso.com/todays-outlook
- gridstatus CAISO package (endpoint corroboration): https://github.com/gridstatus/gridstatus/tree/master/gridstatus/caiso
- Shared packet: CRS R48646 (see design spec)
