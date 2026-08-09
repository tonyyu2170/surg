# ISO-NE as a Comparison Market: Data Availability Research

**Date:** 2026-08-09
**Motivation:** Sixth of six cross-ISO memos per
`docs/superpowers/specs/2026-08-09-cross-iso-data-research-design.md`. ISO-NE is the
designated low-data-center **control market** — the design's contrast case.
**Status:** Research memo. Feeds the Phase-1 checkpoint; no scope decision made here.
**Verification:** Claims verified by probing real endpoints on 2026-08-09 unless
flagged ⚠️.

---

## 1. Headline

**ISO-NE confirms its control-market role in its own words: "New England itself has not
experienced similar growth so far, and only a small amount is expected in the coming
decade" — from the ISO's May 2026 announcement of its first-ever large-load forecast
framework.** On data: the price side is open and deep — daily all-locations LMP CSVs
with energy/congestion/loss columns, verified back to at least 2015 with no login — while
the *hourly zonal load* side is the one series in this whole project that sits behind a
gate: the free-registration web-services API (401 verified) or annually-posted SMD files
whose URLs move year to year (⚠️ unresolved). The facility-level negative holds,
trivially — there is very little facility to find.

## 2. Facility-level / data-center-specific data hunt

- **No facility-level load telemetry**, and — uniquely — not much facility either: New
  England's data-center inventory is small (Boston-area colo, scattered university/HPC),
  with no hyperscale campus operating in-region during the study window. The national
  negative (CRS R48646) is almost moot here.
- **The ISO's own framing (verified quote, isonewswire 2026-05-18):** large loads are
  "rapidly increasing demand for electricity *outside* New England… New England itself
  has not experienced similar growth so far, and only a small amount is expected in the
  coming decade." The ISO built the forecast framework *proactively* — the control
  market preparing for treatment it has not received.
- First artifacts: the **2026–2035 CELT Report** (public xlsx, link verified) now carries
  a large-load forecast component; future editions become the tracking series.
- Demand response: aggregate program data via the API; no facility traces.

## 3. What ISO-NE does better / worse than PJM + ERCOT

**Better:**

- **Open, deep, decomposed prices without login**: `static-transform/csv/histRpts/da-lmp/
  WW_DALMP_ISO_{YYYYMMDD}.csv` — verified 200 at 2015-08-06, 2023-08-06, 2026-08-06;
  schema `Date, Hour Ending, Location ID, Location Name, Location Type, LMP, Energy
  Component, Congestion Component, Marginal Loss Component`; one daily CSV carries
  every location (network nodes, LOAD ZONE rows, hub). 5-minute RT files exist under
  the sibling `histRpts/5min-rt-prelim/` pattern.
- The **IRTT public interconnection queue** (irtt.iso-ne.com) is a clean, queryable
  tracking tool.
- Stable footprint (8 load zones: ME, NH, VT, CT, RI, SEMA, WCMA, NEMA) since the 2003
  SMD start — like NYISO, no boundary breaks.

**Worse:**

- **Hourly zonal load is the gated series** — the only one among all six markets. Routes:
  (a) **web-services API**: free registration, rate-limited, verified 401 without
  credentials — **registration is a user decision per the design spec**; (b) **SMD
  Hourly annual files**: public xlsx workbooks (one sheet per zone) exist for each year,
  but posting URLs vary by year and my two pattern guesses 404'd — ⚠️ locating the
  per-year URLs is a small enumeration task (they are linked from the ISO's "Energy,
  Load, and Demand" pages); (c) EIA-930 gives ISO-NE *total* hourly demand 2015 →
  ungated; FERC-714 covers deeper totals.
- DA LMP daily files are all-locations (~thousands of rows/day) — trivial compute, just
  bulkier than zone-only files.
- ⚠️ Exact histRpts depth edge unprobed (2015 verified; SMD-era nominally 2003) —
  confirm the earliest daily file during the pull.

## 4. Zonal load archive

- **Structure**: 8 load zones + system total, hourly, hour-ending, Eastern prevailing
  with DST conventions (the SMD workbooks carry the 02X/duplicate-hour handling —
  ⚠️ verify exact encoding when the files are in hand).
- **Access routes** (§3): SMD annual xlsx (public, URLs to enumerate) or web-services
  API (registration) or EIA-930 totals (ungated, 2015 →, no zonal split).
- **Depth**: SMD era begins March 2003 — 23 years of 8-zone hourly load once the file
  URLs are enumerated.
- RT 5-minute demand per zone exists via API only — no deep open 5-min load, same as
  every market except NYISO.

## 5. Price archive (verified)

- **DA hourly**: `WW_DALMP_ISO_{YYYYMMDD}.csv` daily files, open, decomposition columns,
  verified at 2015/2023/2026. LOAD ZONE rows give the 8 zonal price series; `.H.INTERNAL_HUB`
  is the hub.
- **RT**: hourly final and 5-minute prelim under sibling `histRpts` paths (pattern from
  the gridstatus scraper, partially verified via the DA family; ⚠️ verify RT-final path
  shape at pull time).
- **Window fit**: DOM-matched horse race (2022-10 →) fully covered by verified-open
  files; full-history 2003 → available pending the depth-edge check.
- Winter price spikes (gas constraints) dominate the tail of any ISO-NE price series —
  see §6.

## 6. Market-specific confounds

- **Behind-the-meter solar is large relative to system size** (~multi-GW in a ~25 GW
  system): New England's metered load now dips mid-day; minimum-load records fall in
  spring. Same CAISO-class caveat: load-level trends conflate consumption with BTM
  adoption; ramp structure reflects solar, not consumers. ⚠️ pin the current BTM GW from
  ISO-NE's PV forecast in Phase 2.
- **Winter gas scarcity drives the price tail**: Dec 2022 (Elliott) and the January
  2018 cold snap produced the era's price extremes — fuel-security events, zero
  data-center content. Any tail-focused price statistic is a gas story here.
- **Peak-response endogeneity**: capacity-tag (ICR) and transmission-charge peak-shaving
  incentives exist — weaker than 4CP/ICI, similar to NYISO; SMD-era stable.
- **Control-market caveat symmetry**: with almost no DC growth, ISO-NE tests the null
  side — if level-beats-volatility and flat-normalized-volatility hold *here too*, the
  pattern is a property of power systems, not of data-center presence. That is exactly
  what the capstone comparison needs from this market.

## 7. Interconnection queue / large-load tracking

- **CELT 2026–2035** (public xlsx, verified link) — debut of the large-load forecast
  component; small expected additions. The annual CELT becomes the tracking series for
  whether the control market stays a control.
- **Forecast framework announcement** (isonewswire, 2026-05-18, verified): proactive
  framework, informed by other regions' experience; quote in §1.
- **IRTT queue** (public): generation-dominated; large-load service requests are not a
  published queue — consistent with every non-ERCOT market except NYISO's Gold Book
  table.
- New England's story is the *absence* of the MISO/SPP wave — which is the point.

## 8. Academic / institutional dataset leads

- **CELT Report workbooks** (annual, public) — zone-level forecasts, now with large-load
  components; the ISO's PV (BTM solar) forecast accompanies it and quantifies §6's
  confound.
- **ISO-NE Economic Studies / 2050 Transmission Study** — long-horizon load scenarios
  (electrification-dominated, not DC-dominated).
- NEPOOL/state channels (e.g., MA DOER, CT DEEP filings) for any future DC-specific
  proceedings — currently thin, as expected for the control market.
- Shared packet applies (LBNL/Brattle NE rows; DELTa; EEI list).

## 9. Concrete Stage-1 pull spec

| Need | Source | Est. volume |
|---|---|---|
| DA LMP (8 zones + hub), 2022-10 → (or 2003 →) | daily `WW_DALMP_ISO` CSVs, open | ~1.4K files for DOM window; zones extracted from LOAD ZONE rows |
| Hourly zonal load 2003 → | SMD annual xlsx (URLs to enumerate) **or** API (user registration decision) | ~24 workbooks |
| System total hourly (backstop) | EIA-930 six-month CSVs | trivial |
| RT / 5-min | histRpts RT families | out of Stage-1 scope |

- **Blocking decision for the checkpoint**: SMD-file enumeration (no gate, small task)
  vs. API registration (cleaner, but a gate the design reserves to the user). Either
  unblocks the full Stage 1.
- **Horse race**: 8 zones × own-zone DA LMP (+ hub) — NYISO-style one-to-one alignment.
  Window: DOM-matched exactly.
- Excel engine required for SMD workbooks (openpyxl — already a Phase-2 prerequisite
  via MISO).
- **Recommendation to checkpoint**: run ISO-NE — as the control market its value is
  highest per byte; the load-access decision is the only fork.

## 10. Source index

- Open DA LMP dailies (verified): `https://www.iso-ne.com/static-transform/csv/histRpts/da-lmp/WW_DALMP_ISO_{YYYYMMDD}.csv`
- 5-min RT prelim pattern: `…/histRpts/5min-rt-prelim/lmp_5min_{date}_{interval}.csv`
- Web services API (401 wall verified): https://webservices.iso-ne.com/
- CELT 2026 workbook: https://www.iso-ne.com/static-assets/documents/100035/2026_celt.xlsx
- Large-load forecast framework: https://isonewswire.com/2026/05/18/iso-ne-establishes-forecast-framework-for-data-centers-other-large-loads/
- IRTT public queue: https://irtt.iso-ne.com/reports/external
- Pricing-node tables: https://www.iso-ne.com/markets-operations/settlements/pricing-node-tables/
- gridstatus ISONE modules (endpoint corroboration): https://github.com/gridstatus/gridstatus/blob/master/gridstatus/isone.py and `gridstatus/isone_api/`
- EIA-930 (totals backstop): https://www.eia.gov/electricity/gridmonitor/
- Shared packet: CRS R48646 (see design spec)
