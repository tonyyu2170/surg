# Cross-ISO Data Availability — Checkpoint Summary

**Date:** 2026-08-09
**Purpose:** Phase-1 closing deliverable per
`docs/superpowers/specs/2026-08-09-cross-iso-data-research-design.md`. One table across
all eight markets, then the decisions the checkpoint needs. Full detail per market lives
in the six memos (`docs/<iso>-data-availability-research.md`) plus the ERCOT memo and the
PJM/DOM project history.

---

## The comparison table

| | **PJM/DOM** | **ERCOT** | **MISO** | **SPP** | **CAISO** | **IESO** | **NYISO** | **ISONE** |
|---|---|---|---|---|---|---|---|---|
| **Load zones** | zones/pnodes | 8 weather zones + total | 6 LRZ groups + total | 20 control zones | 5 TACs + total | 10 zones + Ontario | 11 zones | 8 zones |
| **Zonal load history (hourly)** | 2022-10 → (built) | 2004 → (clean schema 2017 →) | **2013-06 →** | 2025 → verified; 2011 → visible ⚠️ naming | **2009-04 →** | **2003 →** (best archive) | **2001-06 →** | 2003 → (SMD) ⚠️ access |
| **Deep 5-min load?** | bought (quota) | 31-day rolling only | no | no | no | no | **yes — `pal` to 2001** ⚠️ cadence | API only |
| **Price history** | 2022-10 → (built) | 2010 → | 2023 → daily; pre-2023 in bundles ⚠️ | 2025 → verified; 2014 → behind naming ⚠️ | **2009-04 →** | HOEP 2002 → 2025-04; LMP era ⚠️ ~90-day rolling | **DA 1999-11 →, RT 2001 →** | ≥2015 → verified open (2003 nominal) |
| **Congestion decomposed?** | yes | no (derivation) | **yes** (MCC/MLC) | **yes** (MCC/MLC/MEC) | **yes** (MCC/MCL/MCE) | LMP era only | **yes, to 1999** | **yes** |
| **Free 5-min prices?** | quota workaround | yes (SPP files) | **yes, final, 2023 →** | yes (By_Interval) | yes (PRC_INTVL_LMP) | yes but ⚠️ rolling | yes (realtime files) | prelim files |
| **Gates** | quota (gridstatus.io) | none | **none** | none (but UI-only listing) | **none** | none | **none** | load: registration or file-hunt ⚠️ |
| **Timezone regime** | EPT | Central prevailing, hour-ending | **fixed EST** (no DST) | GMT + local ⚠️ load col unlabeled | **GMT** | **fixed EST** (no DST) | Eastern + explicit EST/EDT flag | Eastern, hour-ending |
| **Footprint breaks** | none | none | South joins **2013-12-19** (in-data) | IS 2015; **RTO West 2026** (in-window!) | WEIM roster growth in report | none (load); market regime break 2025-05 | **none since 1999** | none since 2003 |
| **DC-load visibility** | none (pnode geography) | partial registry (no hyperscalers) | 1 named pricing node (`GRE.REC.DATA`) | none | none — Santa Clara invisible (muni) | none; LDC filings | **Gold Book Table IV-7: >12 GW load requests** | ~nothing to see (control) |
| **DC growth scale** | the treatment market | large (LFL ~11% of energy) | **largest forecast: +32 GW peak by 2046; LF 63→68%** | near-doubling of peak in 10 yr (HILL/CHILL) | small: +1.8 GW by 2030 | DC = 8.6% of 2050 demand; EV-dominated | modest; near-term revised **down** | **~none — the control** |
| **Dominant confound** | system-wide 2026 escalation | wind (FWEST) + 4CP | wind (LRZ1/3_5) | **wind (strongest)** + CHILL curtailment | **BTM solar (strongest)** | **ICI/GA peak-shaving (strongest endogeneity)** | Zone J weather; 2022 crypto moratorium | BTM solar + winter gas tail |
| **Stage-1 verdict** | done (home market) | done (132/135 level wins) | **GO** (window 2023-01 →) | **CONDITIONAL** ⚠️ naming task first | **GO** (easiest, full window) | **GO** (load + HOEP; LMP era prospective) | **GO** (strongest candidate) | **GO** (one access fork) |

## What generalized across all six markets

1. **The facility-level negative is universal** — now citable nationally via CRS R48646
   (EIA's mandatory collection died in court; data destroyed). No market's public data
   shows individual data centers; the partial exceptions are ERCOT's DR registry, MISO's
   one named pricing node, and NYISO's load-request table.
2. **Congestion decomposition is free everywhere except ERCOT** — the PJM acquisition
   pain was a PJM problem, not an industry norm.
3. **Every market has a peak-response endogeneity analog** on a spectrum: ICI/GA
   (Ontario, strongest) > 4CP (ERCOT) > SPP's CHILL (contractual, forward-looking) >
   ICAP/SCR (NYISO) ≈ ICR (ISONE) > MISO/CAISO (diffuse). Load traces are never fully
   exogenous at system peaks.
4. **Institutional corroboration of the flat-profile premise keeps appearing**: MISO's
   LTLF says DC growth *raises* load factor 63→68% ("tighter without peakier"); IESO
   buckets DCs into a "growth margin" of *variable* drivers; LBNL/Brattle found DC-heavy
   states saw *retail price decreases* 2019–25. The level-not-volatility framing now has
   three independent institutional echoes.
5. **Deep sub-hourly load basically doesn't exist publicly** — except NYISO's `pal`
   series (to 2001, cadence to verify), which may be unique in North America.
6. **Request pipelines inflate everywhere the funnel is visible**: ERCOT's 1.6%
   queue-to-operating conversion; NYISO's >12 GW of requests against a 538 MW near-term
   forecast (revised *down* from 1,023 MW). Announced MW ≠ load.

## Decisions the checkpoint needs

1. **Which markets proceed to Stage 1.** Recommendation: all six, staged by readiness —
   NYISO, CAISO, IESO first (zero blockers); MISO next (venv engines prerequisite);
   ISONE after its load-access fork; SPP last, gated on the naming enumeration.
2. **SPP naming enumeration** (~15-min browser-UI task) — approve doing it during
   Phase 2; without it SPP is 2025-only and not horse-race-comparable.
3. **ISONE load access fork**: hunt the public SMD annual-file URLs (no gate, small
   task) vs. register for the free web-services API (your call per spec policy) vs.
   defer ISONE zonal load and run its price side only.
4. **IESO LMP-era collector**: the MRP price era appears to be a ~90-day rolling public
   window. Decide whether to stand up a small scheduled collector now (before more
   history rolls off) or write the LMP era off as prospective-only.
5. **Horse-race window harmonization**: exact DOM window (2022-10 →) is available for
   CAISO/NYISO/ISONE(price)/IESO(HOEP); MISO starts 2023-01; SPP TBD. Options: run each
   market at its maximum window and *also* report the common-overlap window
   (2023-01 → 2025-04, bounded by MISO start and HOEP end) for the capstone table — or
   pick one. Recommendation: both, common-overlap as the headline.
6. **Venv prerequisite**: approve adding `xlrd` + `openpyxl` to the main venv in
   Phase 2 (also un-breaks the merged ERCOT scripts, which currently cannot run from
   the main checkout).

## Corrections to the design spec's starting leads

- MISO: LRZ-group load **is** public (spec's "key risk" resolved positively); zonal load
  starts 2013-06 not just "3-region granularity."
- SPP: hourly load is by ~20 control zones (finer than the spec's "reporting area"
  lead); the real risk was retention naming, not zone coarseness.
- IESO: zonal demand starts 2003 as the spec guessed, but MRP-era public price retention
  (~90 days) was not anticipated.
- ISONE: prices turned out *open* (histRpts) — the registration wall applies only to the
  load side; the spec's "which files are open" question is answered.
- CAISO: the Santa Clara/SVP question is resolved — no TAC; the cluster is invisible by
  structure, not by oversight.
