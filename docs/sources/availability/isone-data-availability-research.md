# ISO-NE as a Comparison Market: Data Availability Research

**Date:** 2026-08-09
**Motivation:** Sixth of six cross-ISO memos per
`docs/specs/2026-08-09-cross-iso-data-research-design.md`. ISO-NE is the
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

**Corrected 2026-08-10** (`docs/sources/availability/cross-iso-phase2-recon-verification.md` §1–§2): two
claims above are wrong. The "verified back to at least 2015" price claim checked HTTP
status, not payload — 2015-08-06 returns an HTTP 200 with a 31-byte "No data exists for
this period." body; real usable price depth is **2016-01 → present**. And the "hourly
zonal load...sits behind a gate" framing does not hold either: the annual SMD workbooks
are published as **open static assets at 11 verified URLs, requiring no CAPTCHA, no
registration, and no login** — "URLs move year to year (⚠️ unresolved)" is resolved by
the 11 fixed URLs, not by enumeration. (The `zone-info` page's own download interface
*is* CAPTCHA-gated, but that interface is not the route used.) Load is therefore open on
the same no-gate terms as price; see §3, §4, §5, §9.

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

- **Open, decomposed prices without login**: `static-transform/csv/histRpts/da-lmp/
  WW_DALMP_ISO_{YYYYMMDD}.csv` — schema `Date, Hour Ending, Location ID, Location Name,
  Location Type, LMP, Energy Component, Congestion Component, Marginal Loss Component`;
  one daily CSV carries every location (network nodes, LOAD ZONE rows, hub). 5-minute RT
  files exist under the sibling `histRpts/5min-rt-prelim/` pattern. **Corrected
  2026-08-10**: the "verified 200 at 2015-08-06" claim checked status codes, not
  payloads — that date returns an HTTP 200 with a 31-byte empty-sentinel body ("No data
  exists for this period."). Real usable depth is **2016-01 → present** (dense monthly
  sampling every year 2016–2025); see
  `docs/sources/availability/cross-iso-phase2-recon-verification.md` §1.
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
- **Corrected 2026-08-10**: the depth edge is now probed, and the "2015 verified;
  SMD-era nominally 2003" framing above was wrong — 2015-08-06 and every probed date
  ≤ Nov 2015 return an empty sentinel, not data. Real depth is **2016-01 → present**
  (December 2015 is patchy); see `docs/sources/availability/cross-iso-phase2-recon-verification.md` §1.

## 4. Zonal load archive

- **Structure**: 8 load zones + system total, hourly, hour-ending, Eastern prevailing
  with DST conventions (the SMD workbooks carry the 02X/duplicate-hour handling —
  ⚠️ verify exact encoding when the files are in hand).
- **Access routes** (§3): SMD annual xlsx **or** web-services API (registration) or
  EIA-930 totals (ungated, 2015 →, no zonal split). **Corrected 2026-08-10**: "URLs to
  enumerate" is resolved — all 11 SMD workbook URLs (2016–2026) are verified open
  static-asset constants, no CAPTCHA/registration/login/enumeration needed
  (`docs/sources/availability/cross-iso-phase2-recon-verification.md` §2); see §9.
- **Depth**: SMD era begins March 2003 — 23 years of 8-zone hourly load. **Corrected
  2026-08-10**: the "once the file URLs are enumerated" caveat no longer applies for
  2016–2026 (11 workbooks, all verified). Recon confirmed those 11 URLs only; the
  2003–2015 portion of this depth claim was not probed and remains unverified either
  way.
- RT 5-minute demand per zone exists via API only — no deep open 5-min load, same as
  every market except NYISO.

## 5. Price archive (verified)

- **DA hourly**: `WW_DALMP_ISO_{YYYYMMDD}.csv` daily files, open, decomposition columns.
  LOAD ZONE rows give the 8 zonal price series; `.H.INTERNAL_HUB` is the hub.
  **Corrected 2026-08-10**: "verified at 2015/2023/2026" checked HTTP status only — the
  2015 file is an empty sentinel. Real depth is **2016-01 → present**
  (`docs/sources/availability/cross-iso-phase2-recon-verification.md` §1). Stage 1 does not use this daily-CSV
  route at all — see the §9 workbook route.
- **RT**: hourly final and 5-minute prelim under sibling `histRpts` paths (pattern from
  the gridstatus scraper, partially verified via the DA family; ⚠️ verify RT-final path
  shape at pull time).
- **Window fit**: DOM-matched horse race (2022-10 →) fully covered by verified-open
  files. **Corrected 2026-08-10**: full-history depth is **2016-01 → present**, not
  2003 → (the "pending the depth-edge check" note above resolved false).
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

**Corrected 2026-08-10** (`docs/sources/availability/cross-iso-phase2-recon-verification.md` §2): the daily
`WW_DALMP_ISO` CSV route below is superseded for Stage 1. One annual SMD workbook per
year carries load *and* decomposed DA/RT LMP *and* weather, per zone, in a single file —
11 workbooks (~85 MB) replace the ~1.4K daily CSVs this table originally budgeted for
price, and the load-access fork closes: **no CAPTCHA, no registration, no login**. (The
`zone-info` page's own download interface *is* CAPTCHA-gated and must not be used; the
11 workbooks are published separately as open static assets and are unaffected by that
gate.)

| Need | Source | Est. volume |
|---|---|---|
| DA/RT LMP + load + weather, 8 zones + system, 2016-01 → 2026-06-30 | 11 annual SMD workbooks (`static-assets/documents/...`; 2016 `.xls`, 2017–2023 dated-folder `.xlsx`, 2024–2026 numeric-id `.xlsx` — verified constants, not a computed pattern) | ~85 MB total |
| System total hourly (backstop) | EIA-930 six-month CSVs | trivial |
| RT / 5-min | histRpts RT families | out of Stage-1 scope |

- **Blocking decision resolved**: the prior "SMD-file enumeration vs. API registration"
  fork is gone — all 11 workbook URLs are verified constants requiring no registration.
- **Horse race**: 8 zones × own-zone DA LMP (+ hub) — NYISO-style one-to-one alignment.
  Window: 2016-01 → 2026-06-30 (workbook depth), or DOM-matched (2022-10 →) as a subset.
- Excel engines required: `xlrd` for the 2016 `.xls` workbook, `openpyxl` for 2017+
  `.xlsx` (both already a Phase-2 prerequisite via MISO).
- **Recommendation to checkpoint**: run ISO-NE — as the control market its value is
  highest per byte; the load-access fork has dissolved, so there is no remaining fork.

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
