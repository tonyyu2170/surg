# NYISO as a Comparison Market: Data Availability Research

**Date:** 2026-08-09
**Motivation:** Fifth of six cross-ISO memos per
`docs/specs/2026-08-09-cross-iso-data-research-design.md`.
**Status:** Research memo. Feeds the Phase-1 checkpoint; no scope decision made here.
**Verification:** Every schema and depth claim verified by downloading and reading real
files from `mis.nyiso.com` on 2026-08-09 unless flagged ⚠️.

---

## 1. Headline

**NYISO has the deepest usable archive of any market in this project — 11-zone load and
decomposed zonal prices, every probe returning 200 on the first try: hourly integrated
load to 2001, 5-minute actual load to 2001, DA zonal LBMP with congestion and loss
columns to 1999.** It also turns out to publish the thing no other non-ERCOT market
does: the Gold Book's **Table IV-7 "Load Interconnection Requests" — a public inventory
of pending large-load requests, now totaling over 12,000 MW** — the closest thing to
ERCOT's large-load queue outside Texas. The substantive story is contrarian: NYISO just
revised near-term large-load impacts *down* (2026: 1,023 → 538 MW) while raising 2040,
and its baseline 30-year energy growth rate fell from 2.0% to 1.1%/yr. New York is a
data-rich, growth-modest market — the second-best control case after ISONE, with far
better data.

## 2. Facility-level / data-center-specific data hunt

- **No facility-level load telemetry** — the national negative (CRS R48646) holds. NYISO
  zone files aggregate; Special Case Resources (demand response) report as program
  totals (927 MW summer 2026, down from 1,487 MW — public but aggregate).
- **The Gold Book is the partial exception, twice over (verified via 2026 coverage):**
  - **Table IV-7, Load Interconnection Requests** — pending large-load requests with
    summer-capability MW, >12,000 MW in the 2026 edition. A load-side request funnel,
    published annually. ⚠️ Per-row granularity (facility vs. aggregated) to confirm
    directly from the Gold Book file in Phase 2.
  - **Large-load impact forecasts** by year (2026: 538 MW; 2027: 1,075 MW;
    2040: 2,880 MW) — explicit, revisable, and quotable.
- **Known upstate crypto context**: Greenidge (Zone C) and the Massena/North Country
  operations (Zone D) are the documented crypto loads; New York's 2022 PoW-mining
  moratorium (behind-the-meter fossil) capped that channel. Zone J (NYC) hosts the
  dense-but-small-MW colo market. No zone isolates "data centers" — but Zones C/D vs.
  J gives a usable industrial-vs-urban contrast geography.
- Names in the zone files are zones (CAPITL, CENTRL, …), so the ERCOT-style name scan
  does not apply at this granularity; nodal rosters exist but were not scanned (no DC
  lead to chase).

## 3. What NYISO does better / worse than PJM + ERCOT

**Better:**

- **Depth with decomposition**: DA zonal LBMP files carry
  `LBMP, Marginal Cost Losses, Marginal Cost Congestion` back to **1999-11 (verified)**;
  RT zonal files to **2001-06 (verified)**. Twenty-five-plus years of congestion series,
  free — deeper than PJM's practical access and far deeper than ERCOT's 2010 price wall.
- **5-minute actual load with deep history**: `pal` files verified to **2001-06** —
  no other market in this project offers deep sub-hourly *load* publicly (ERCOT keeps
  31 days; MISO none; PJM cost quota). ⚠️ Verify early-era cadence in-file (the 2001
  files may be 6-minute or irregular snapshots) before advertising a uniform 5-min
  series.
- **Explicit DST handling**: load files carry a `Time Zone` column (EST/EDT flags,
  verified) — the fall-back duplicate hour is labeled, not implicit.
- **A published load-interconnection request table** (§2) — no other market here except
  ERCOT has one.
- Simple access: monthly zips per series (`{YYYYMM01}{family}_csv.zip`), no key, no
  quota, HTTP that answers HEAD honestly.

**Worse:**

- Genuinely little. The main caveats are substantive, not data-mechanical: modest DC
  growth (the market is a near-control), and NYC-centric weather dominance in Zone J.
  Mechanically: monthly-zip granularity means ~300 zips per series for a full backfill —
  trivial but numerous.

## 4. Zonal load archive (verified)

**Two series, both by 11 zones (A–K: CAPITL, CENTRL, DUNWOD, GENESE, HUD VL, LONGIL,
MHK VL, MILLWD, N.Y.C., NORTH, WEST):**

| Series | Path | Cadence | Depth verified |
|---|---|---|---|
| Integrated hourly | `mis.nyiso.com/public/csv/palIntegrated/{YYYYMM01}palIntegrated_csv.zip` | hourly | 2001-06 ✓, 2026-07 ✓ |
| Actual (RT) | `…/pal/{YYYYMM01}pal_csv.zip` | ~5-min ⚠️ (verify early-era cadence) | 2001-06 ✓ |

- Schema (verified): `"Time Stamp","Time Zone","Name","PTID","Integrated Load"` —
  prevailing Eastern with explicit EST/EDT flags; monthly zips contain daily CSVs.
- Hourly panel volume: 11 zones × ~220K hours ≈ 2.4M zone-hours; ~300 monthly zips.
- NYCA total = sum of zones (assert; no separate total series needed).

## 5. Price archive (verified)

| Series | Path | Depth verified |
|---|---|---|
| DA zonal LBMP | `…/damlbmp/{YYYYMM01}damlbmp_zone_csv.zip` | **1999-11 ✓**, 2026-07 ✓ |
| RT zonal LBMP | `…/realtime/{YYYYMM01}realtime_zone_csv.zip` | 2001-06 ✓ |

- Schema (verified): `Time Stamp, Name, PTID, LBMP ($/MWHr), Marginal Cost Losses
  ($/MWHr), Marginal Cost Congestion ($/MWHr)` — decomposition as columns. NYISO sign
  convention differs from PJM (congestion enters LBMP with opposite sign) — normalize
  at parse ⚠️ (well-documented; assert against a known constrained hour).
- Nodal (generator) variants exist under `damlbmp_gen`/`realtime_gen` — not needed for
  Stage 1.
- RT cadence: 5-minute post-2005-ish; earlier RT files are hourly/half-hourly eras —
  ⚠️ confirm cadence changes during the pull; the DA series is uniformly hourly.
- **Window fit: everything.** DOM-matched horse race (2022-10 →) trivially covered; a
  full-history 1999 → run is available if ever wanted.

## 6. Market-specific confounds

- **Zone J weather dominance**: NYC's summer-peaking A/C load swamps zone-level
  variance; the DC/crypto question lives upstate (C/D), so zone selection matters more
  than in other markets.
- **BTM solar**: growing (multi-GW statewide), strongest in Long Island/Hudson Valley
  zones — the CAISO caveat at perhaps a quarter scale; note in captions.
- **Peak-response endogeneity**: ICAP tags (installed-capacity billing determinants)
  and SCR programs give large consumers peak-shaving incentives — materially weaker
  than 4CP/ICI (annual tag, less predictable), but present; SCR enrollment is public
  and shrinking (1,487 → 927 MW summer 2025→26).
- **Crypto policy shock**: the 2022 PoW moratorium (renewed since) is a policy break in
  exactly the load class of interest — any upstate load trend crossing 2022 carries it.
- **Footprint: stable since 1999** — no joins, no boundary changes, uniquely among the
  six markets researched. One less thing.

## 7. Interconnection queue / large-load tracking

- **Gold Book (Load & Capacity Data), annual, public** — the 2026 edition (verified via
  secondary coverage): 30-yr baseline energy growth revised **2.0% → 1.1%/yr**; winter
  peak revisions down; hydrogen-electrolysis load removed entirely; large-load impact
  538 MW (2026) / 1,075 MW (2027) / 2,880 MW (2040, revised up); **Table IV-7 load
  interconnection requests > 12,000 MW**; SCR enrollment figures; deactivation pipeline
  (48 → 1,307 MW of proposed retirements incl. Danskammer units). One document carries
  the entire §7 for this market, every year.
- 2026 ICAP peak-load forecast PDF published separately (verified link).
- The contrast with MISO is the cross-market story: NYISO's *near-term* large-load
  reality shrank while its *pipeline* table exploded — request inflation vs. realized
  load, the ERCOT funnel lesson (1.6% conversion) in a second market's data.

## 8. Academic / institutional dataset leads

- **The Gold Book itself** — a genuine annual dataset (xlsx tables), not just a report;
  Table IV-7 is the analytical asset.
- **NYSERDA** statewide energy datasets and the CLCPA planning studies — NY-specific
  load-growth scenarios (⚠️ unverified whether DC breakouts exist).
- Utica/SUNY Poly + Micron context: the Micron Clay fab (Zone C, announced ~6 GW-scale
  eventual load in some coverage) is *semiconductor manufacturing*, not a data center —
  keep the categories straight in any NY narrative; its MW dominate upstate large-load
  discussion.
- Shared packet applies (LBNL/Brattle NY rows; DELTa; EEI list).

## 9. Concrete Stage-1 pull spec

| Need | Source | Est. volume |
|---|---|---|
| Hourly load, 11 zones, 2001-06 → | ~302 monthly `palIntegrated` zips | ~2.4M zone-hours; ~150 MB |
| DA zonal LBMP, 1999-11 → | ~322 monthly `damlbmp_zone` zips | ~2.6M zone-hours |
| RT zonal LBMP, 2001-06 → | ~302 monthly `realtime_zone` zips | larger (5-min era); hourly-average at parse |
| 5-min load (companion) | `pal` zips | out of Stage-1 scope; note depth |

- No key, no quota; politeness throttling. No new dependencies (CSV in zips).
- **Horse race**: 11 zones × own-zone DA LBMP (+ RT optional) — the only market where
  load zones and price zones coincide one-to-one, making the cell design cleaner than
  anywhere else. Window: DOM-matched 2022-10 → exactly.
- **Trend window**: 2001 → present (25 years), footprint-stable throughout.
- Parse cautions: `Time Zone` column handling (EST/EDT), congestion sign convention,
  RT-cadence eras, `HUD VL`/`N.Y.C.`-style names with spaces and periods.
- **Recommendation to checkpoint**: NYISO is the strongest Stage-1 candidate of the six
  on pure data quality — full windows, zone-price alignment, no gates, no footprint
  breaks — and doubles as the second control market.

## 10. Source index

- Archive root (verified patterns): `http://mis.nyiso.com/public/csv/{family}/{YYYYMMDD}{family}_csv.zip`
  — families: `palIntegrated`, `pal`, `damlbmp` (`_zone`/`_gen`), `realtime` (`_zone`/`_gen`)
- NYISO market data landing: https://www.nyiso.com/energy-market-operational-data
- Gold Book landing (Load & Capacity Data): https://www.nyiso.com/gold-book-resources
- 2026 ICAP peak-load forecast: https://www.nyiso.com/documents/20142/55861712/02%202026%20Installed%20Capacity%20Market%20Peak%20Load%20Forecast.pdf
- 2026 Gold Book synthesis (numbers cited above): https://www.luminary.energy/articles/2026-nyiso-gold-book-tighter-margins-as-the-system-leans-on-retained-retirements ; also https://www.gridstatus.io/insights/40753238038
- Shared packet: CRS R48646 (see design spec)
