# SURG Data Catalog

The operational inventory of all data flowing through this project — what's
on disk, where it came from, what each feed is used for, and what's
planned for backfill. Sister docs:

- **Methodology rationale** (why each feed is in scope, what the analysis
  does with it): `docs/plans/2026-05-11-phase-transition-methodology.md`
- **API constraints** (what PJM forces on us — archive cutoffs, filter
  restrictions, retention caps): `docs/pjm-api-constraints.md`
- **Decisions log** (when/why scope changed): `docs/decisions.md`

Update this file whenever a feed's window changes, a new feed is added,
or a derived artifact's schema changes.

**Layout of this file:** §§ 1–5 cover the **PJM core** (the primary case
study, pulled via `surg-pull`). § 6 covers the **eight-market cross-ISO
Stage-1** feeds. § 7 covers the **UKPN data-centre load profiles**. Total
`data/` footprint is **~6.0 GB**, all gitignored.

---

## Snapshot

Joint analysis window: **2022-10-02 → 2026-05-10** (~3.6y, all post-cap;
see decisions.md "2026-05-12 — Window extension to 3.6y post-cap").

| Feed | Disk window | Planned window | Grain | Scope | Role |
|------|-------------|----------------|-------|-------|------|
| `rt_hrl_lmps` | 2022-10-02 → 2026-05-10 (9 EHV+ZONE pnodes); 2024-05-11 → 2026-05-10 (2 LOAD pnodes) | — (Plan 1.5 complete) | hourly | 11 target pnodes | Primary TAR response; controls; mechanism test |
| `da_hrl_lmps` | 2024-05-26 → 2026-05-10 | — (deferred DA-RT spread analysis) | hourly | 11 target pnodes | Deferred |
| `rt_fivemin_hrl_lmps` | 2025-11-12 → 2026-05-10 | — (Historic intractable, no `type` filter) | 5-min | 11 target pnodes | High-resolution volatility within post-2025-11 portion |
| `hrl_load_metered` | 2021-01-01 → 2026-05-07 | already covers | hourly | DOM zone | TAR threshold variable (load gradient); growth-projection baseline |
| `sync_reserve_events` | 2022-10-02 → 2026-03-05 | — (Plan 1.5 complete) | event timestamps | MAD sub-zone | ORDC validation; Granger causality (load → event); rare-event corroboration |
| `reserve_market_results` | 2022-10-02 → 2026-05-10 | — (Plan 1.5 complete) | 5-min → aggregated hourly | MAD locale, services SR + PR | Severity quantification of reserve scarcity; high-clearing-price threshold for stressed regime |
| `dom_pnodes_all` | snapshot | n/a | one row per pnode | DOM zone (2,328 pnodes) | Reference / pnode resolution |

Symbols:
- "— (Plan 1.5 complete)" means the disk window now matches the post-Plan-1.5 target — no more backfill scheduled for this feed. See `docs/plans/2026-05-12-acquisition-archive-mode.md`.
- "— (deferred)" means no backfill planned; the existing window stays.

---

## 1. Raw API feeds

Each entry below covers: what the feed is in PJM's terms, our filter
scope, our column usage, how the data lands on disk, and what analysis
artifacts consume it.

### `rt_hrl_lmps` — Real-Time hourly nodal LMP

**PJM:** hourly locational marginal price at every priced node, settled
real-time. Field set: `datetime_beginning_utc/ept`, `pnode_id`,
`pnode_name`, `voltage`, `equipment`, `type` (=pnode_subtype, *not*
pnode_type — empirically verified 2026-05-12), `zone`,
`system_energy_price_rt`, `total_lmp_rt`, `congestion_price_rt`,
`marginal_loss_price_rt`, `row_is_current`, `version_nbr`.

**Our filter scope:** the 11 target pnodes (see § 2). Within those, we
keep `row_is_current=true` (current LMP version per
pjm-api-constraints.md § "LMP versioning").

**Columns we use downstream:** `datetime_beginning_ept`, `pnode_id`,
`pnode_name`, `congestion_price_rt`, `total_lmp_rt`. Other columns
(voltage, equipment, version_nbr) are stored verbatim but not consumed
by the analysis panel.

**Disk:** `data/raw/rt_hrl_lmps/<YYYY>/<group>__<YYYY-MM-DD>_to_<YYYY-MM-DD>.parquet`.
Post-Plan-1.5: ~319,500 rows across multiple group-labeled chunks:
- `dom_targets__*` (existing Standard, 11 pnodes, 2024-05-26 → 2026-05-10)
- `dom_targets_gap_fill__*` (Standard, 11 pnodes, 2024-05-12 → 2024-05-25)
- `dom_targets_boundary_day__*` (Standard, 11 pnodes, 2024-05-11 single day)
- `dom_targets_archive_ehv__*` (Historic, 8 EHV pnodes, 2022-10-02 → 2024-05-10)
- `dom_targets_archive_zone__*` (Historic, DOM zonal, 2022-10-02 → 2024-05-10)

Per-pnode hour counts: 9 EHV+ZONE pnodes get ~31,608 hours each (full 3.6y);
2 LOAD pnodes get ~17,520 hours each (2y plus the 15-day boundary+gap fill).

**Pull:** `surg-pull --feed rt_hrl_lmps --target-group dom_targets …`
(Standard tier, pnode_id filter) for current data. For 2022-10-02 →
2024-05-10 backfill (Historic tier), use the archive-mode flags added in
Plan 1.5: `--archive-tier --archive-subtype <EHV|ZONE>` (LOAD
intentionally skipped — see "Asymmetric LOAD coverage" below). The
empirical Historic/Standard boundary at the 731-day cutoff slides one
day per day; Plan 1.5 added a `dom_targets_boundary_day__*` Standard
pull for whichever day straddles the boundary at execution time.

**Analysis role:**
- **Primary TAR fit** — `congestion_price_rt` averaged across the
  6-pnode Loudoun cluster, regressed on DOM load gradient (panel column
  `congestion_price_rt_cluster_mean`)
- **Mechanism test** — `total_lmp_rt` parallel fit; ORDC penalty lands
  in system energy, so total LMP is the cleaner mechanism response
  (`total_lmp_rt_cluster_mean`)
- **Negative controls** — separate TARs on OX, BRISTERS, DOM zonal;
  should NOT show a threshold at the cluster's c (panel columns
  `congestion_price_rt_ox`, `_bristers`, `_dom_zonal`)
- **Distribution-side fit** — separate TAR on ASHBURN TX1/TX2 (35 KV,
  different physics from 500 KV cluster) — at 2y window only

**Constraints:** 731-day archive cutoff (Standard ⇄ Historic boundary,
currently ~2024-05-11 UTC). Historic tier: no `pnode_id` filter,
calendar-year ranges only, sort/order rejected. Filterable only on
`dates`, `type` (= pnode_subtype), `row_is_current`, `version_nbr`.
See pjm-api-constraints.md § "Archived (Historic) data".

---

### `da_hrl_lmps` — Day-Ahead hourly nodal LMP

**PJM:** same shape as `rt_hrl_lmps` but cleared in the day-ahead market
(forecast-based). `_da` price suffixes instead of `_rt`.

**Our filter scope:** same 11 target pnodes.

**Disk:** `data/raw/da_hrl_lmps/`. 188,760 rows, 2024-05-26 →
2026-05-10.

**Analysis role:** **deferred.** The methodology spec lists DA-RT
spread as a future analysis (Phase 3 robustness), but it's not on the
critical path for the threshold question. Data is pulled and stored so
the analysis can be enabled without re-pulling.

**Constraints:** same archive cutoff as `rt_hrl_lmps`.

---

### `rt_fivemin_hrl_lmps` — Real-Time 5-min nodal LMP

**PJM:** same field shape as the hourly RT feed, but at 5-min granularity
(288 rows/day/pnode on a non-DST day). Same `type` column meaning as
`rt_hrl_lmps`.

**Our filter scope:** 11 target pnodes.

**Disk:** `data/raw/rt_fivemin_hrl_lmps/`. 570,108 rows, 2025-11-12 →
2026-05-10 (≈ the 186-day Standard cutoff at acquisition time).

**Analysis role:** **high-resolution volatility characterization** within
the post-2025-11 portion. Used for sub-hourly spike inspection and for
visualizing the gap between 5-min and hourly-averaged volatility. NOT
the primary TAR response (the hourly grain is the load-gradient
counterpart).

**Constraints:** 186-day archive cutoff. Historic tier is essentially
intractable for our use case — the `type` filter is **rejected** on
this feed in both Standard and Historic (API guide page 52), so any
Historic pull would require downloading the entire feed unfiltered
(~10B rows/year). Therefore: **no historical backfill planned.**

---

### `hrl_load_metered` — DOM hourly zonal load

**PJM:** company-verified hourly metered load at the zone / load-area
granularity. Field set: `datetime_beginning_utc/ept`, `nerc_region`,
`mkt_region`, `zone`, `load_area`, `mw`, `is_verified`.

**Our filter scope:** `zone=DOM`. Returns one row per hour (24/day, no
fan-out across load_areas).

**Columns we use:** `datetime_beginning_ept`, `mw` (renamed to
`dom_load_mw` in the analysis panel).

**Disk:** `data/raw/hrl_load_metered/`. 46,871 rows, 2021-01-01 →
2026-05-07. Five+ years on disk — already covers the planned 3.6y
methodology window with substantial buffer.

**Pull:** `surg-pull --feed hrl_load_metered --target-group dom_zonal …`.

**Analysis role:**
- **Threshold variable** — `dom_load_gradient_abs_mw_per_min` (derived in
  Plan 2's `add_load_gradient_columns`) is the TAR threshold variable
- **Growth-projection baseline** — 5y of load data covers the proposal's
  "when does projected growth push the grid past the threshold" framing.
  Pre-2022-10 portion (rule-change era) is available for descriptive
  trend visualization but NOT used in the TAR fit window
- **Verification lag** — recent rows have `is_verified=false`; the
  3-day end-cap gap (2026-05-07 vs LMP's 2026-05-10) reflects
  verification latency, not missing data

**Constraints:** none documented. Not in the archive system; no retention
cap observed. Date-range cap (366 days per request) handled by
acquisition chunking.

---

### `sync_reserve_events` — MAD synchronized reserve events

**PJM:** discrete event records of Synchronized Reserve activations in
the Mid-Atlantic / Dominion (MAD) sub-zone. Field set: `event_start_ept`,
`event_end_ept`, `duration`, `synchronized_reserve_zone`,
`synchronized_sub_zone`, `percent_deployed`.

**Our filter scope:** `synchronized_sub_zone="MidAtlantic-Dominion (MAD)"`.

**Disk:** `data/raw/sync_reserve_events/`. Post-Plan-1.5: 38 events
spanning 2023-01-26 → 2026-03-05 (2 in the 2022-10 → 2024-05 backfill
window, 36 in the existing 2024-05-26 → 2026-03-05 window). MAD sync
reserve activations are rare even at multi-year scale.

Smoke duplicate (`mad_smoke__2026-04-01_to_2026-04-30.parquet`) is
slated for removal before Plan 2's bulk preprocessing (Plan 2 pre-flight).

**Pull:** `surg-pull --feed sync_reserve_events --subzone "MidAtlantic-Dominion (MAD)" …`.

**Analysis role:**
- **ORDC mechanism validation** — direct event records that triggered
  the ORDC penalty stack; the LMP-side response should manifest within
  these event windows
- **Granger causality test** — does `dom_load_gradient_abs_mw_per_min`
  Granger-cause sync-reserve-event occurrence? Methodology spec § Test 1
- **Hours-to/since-event features** — panel columns
  `hours_to_next_sync_event`, `hours_since_last_sync_event` (Plan 2)
- **Event-active flag** — `sync_reserve_event_active` marks hourly
  buckets overlapping any event; conditioning variable for fits

**Constraints:** earliest record back to 2012-11-25 per metadata probe
(2026-05-12). No archive cutoff observed. Total event count across the
entire MAD history is only 65 — events are rare even at multi-year
scale. The 1.6y backfill window (2022-10-02 → 2024-05-25) yielded only
**2 events** (one in Jan 2023, one in Feb 2024) — substantially below
the initial estimate of ~10-15. Event rate appears to have accelerated
sharply post-2025: 28 events in 2025 alone vs 2 in the prior 1.6y.

---

### `reserve_market_results` — MAD reserve market clearing prices

**PJM:** 5-min reserve market clearing prices in the MAD locale, by
service tier. Field set includes `datetime_beginning_utc/ept`, `locale`,
`service`, `mcp` (market clearing price), `mcp_capped`, and various
deployment / capability fields.

**Our filter scope:** `locale=MAD`, `service in {SR, PR}` (Synchronized
Reserve, Primary Reserve).

**Columns we use:** `datetime_beginning_ept`, `service`, `mcp`. Plan 2's
loader aggregates 5-min → hourly mean per service and pivots to two
panel columns:
- `sync_reserve_clearing_price_rt` (SR hourly mean)
- `primary_reserve_clearing_price_rt` (PR hourly mean)

**Disk:** `data/raw/reserve_market_results/`. Post-Plan-1.5: 758,016
rows, 2022-10-02 → 2026-05-10 (288 5-min intervals/day × ~1,318 days ×
2 services). Smoke duplicate (`mad_smoke__2026-04-15_to_2026-04-15.parquet`)
is slated for removal — its rows are subsets of the bulk files but
groupby+mean in the loader self-heals against duplicates (unlike
`sync_reserve_events`).

**Pull:** `surg-pull --feed reserve_market_results --locale MAD …`.

**Analysis role:**
- **Severity quantification** — high SR clearing price corresponds to
  ORDC trigger; magnitude calibrates "how stressed" the regime is
- **Stressed-regime threshold variable** — empirical finding 2026-05-11:
  44% of 5-min intervals have nonzero SR clearing, so "nonzero" is too
  lax a definition of stressed; methodology spec § 4 / § 6 to be revised
  to threshold on *high* clearing prices (target: ≥ $850/MWh, ORDC
  first-step penalty level) before Plan 3 executes
- **Cross-check on event windows** — when `sync_reserve_event_active`
  fires, `sync_reserve_clearing_price_rt` should be elevated; mismatches
  surface either bad event windows or pricing-only stress (PJM dispatched
  short of ORDC trigger)

**Constraints:** earliest record back to 2013-06-14 per metadata probe.
Granularity changed from hourly to 5-min on 2022-10-01; the planned
2022-10-02+ window is uniformly 5-min — no loader branch needed for
mixed granularity. No archive cutoff observed.

---

## 2. Pnode target reference (the 11 nodal targets)

Locked in 2026-05-10 (`docs/decisions.md` § "2026-05-10 — Lock the
11-pnode target set"). All currently have full 2y Standard-tier
coverage on `rt_hrl_lmps`, `da_hrl_lmps`, `rt_fivemin_hrl_lmps`
(post-2025-11 only).

| pnode_id | Name | Subtype | Voltage | Tier | Role | Disk coverage |
|----------|------|---------|---------|------|------|----------------|
| 35010365 | LOUDOUN | EHV | 500 kV | Loudoun cluster | Primary TAR | 3.6y |
| 35010371 | PLEASANT VIEW | EHV | 500 kV | Loudoun cluster | Primary TAR | 3.6y |
| 1356178195 | GOOSECRE (Goose Creek) | EHV | 500 kV | Loudoun cluster | Primary TAR | 3.6y |
| 1356178171 | BRAMBLET (Brambleton) | EHV | 500 kV | Loudoun cluster | Primary TAR | 3.6y |
| 1356178181 | MOSBY | EHV | 500 kV | Loudoun cluster | Primary TAR | 3.6y |
| 1356178201 | SKFFSCRK (Skiffes Creek) | EHV | 500 kV | Loudoun cluster | Primary TAR | 3.6y |
| 35010369 | OX | EHV | 500 kV | Control | Negative control | 3.6y |
| 62871513 | BRISTERS | EHV | 500 kV | Control | Negative control | 3.6y |
| 34964545 | DOM | ZONE | — | Zonal | Zonal-level reference / negative control | 3.6y |
| 34886139 | ASHBURN TX1 | LOAD | 35 kV | Distribution | Distribution-side TAR (separate fit) | **~2y** (2024-05-11 → 2026-05-10; LOAD subtype intractable in Historic — see "Asymmetric LOAD coverage") |
| 34886141 | ASHBURN TX2 | LOAD | 35 kV | Distribution | Distribution-side TAR (separate fit) | **~2y** (2024-05-11 → 2026-05-10) |

Subtype/voltage source: `data/raw/rt_hrl_lmps/` (`type` column in
returned rows) and `data/raw/dom_pnodes_all.parquet` (registry).

### Asymmetric LOAD coverage — why Ashburn TX1/TX2 stay at 2y

PJM has ~10,786 LOAD-subtype pnodes vs ~136 EHV. Historic-tier queries
must filter by subtype (`pnode_id` is rejected), so recovering 2 LOAD
pnodes' history means downloading all 10,786 and discarding 99.98%.
Empirical 2026-05-12: ~94.5M rows/year, ~8.5 hours of API time at 6
calls/min for the 1.6y backfill, to keep ~28,000 useful rows. EHV
historic costs ~6 min for the same proportional sample lift.

The Ashburn distribution-side TAR is a **separate** fit
("complementary, not redundant", decisions.md 2026-05-10). Keeping
Ashburn at 2y while the primary cluster fit gets 3.6y is acceptable
asymmetry. Revisit if reviewer pushback requires it; archive-mode code
in Plan 1.5 will support `type=LOAD` so the overnight pull is one
config change away.

---

## 3. Derived artifacts

### `data/interim/analysis_panel.parquet` (Plan 2 output, not yet built)

Hourly analysis-ready panel joining LMP cluster + per-pnode controls,
DOM load + gradient, sync-reserve events + lead/lag, reserve clearing
prices, and filter columns. Single source of truth for Plan 3
(analysis module).

**Authoritative schema:** `docs/plans/2026-05-11-phase-transition-methodology.md`
§ 3, version-controlled via `src/surg/preprocessing/schema.SCHEMA_VERSION`.

**Expected dimensions** (after Plan 2's window-clipping amendment,
2022-10-02 → 2026-05-10): ~31,632 rows × ~23 columns.

**Producer:** `surg-prep` CLI (Plan 2 Task 11) → calls
`build_analysis_panel(data_root) → DataFrame` then writes atomically
via tmp+rename.

**Consumer:** Plan 3 (TAR + quantile regression analysis).

---

## 4. Reference & exploratory data

### `data/raw/dom_pnodes_all.parquet` — DOM-zone pnode registry

Full DOM-zone pnode registry: 2,328 active pnodes with `pnode_id`,
`pnode_name`, `pnode_type` (AGGREGATE / BUS / LOCALE), `pnode_subtype`
(AGGREGATE / EHV / EXT / GEN / HUB / INTERFACE / LOAD /
RESIDUAL_METERED_EDC / TIE / ZONE), `zone`, `voltage_level`,
`effective_date`, `termination_date`.

Used for resolving pnode names → IDs, identifying subtypes for
acquisition (Plan 1.5 archive-mode filters), and ad-hoc lookups during
methodology work.

Note: zonal aggregate pnodes (e.g., DOM zonal `pnode_id=34964545`) are
**not** tagged with their own zone in the registry (`zone=null`); they
must be queried via `pnode?pnode_subtype=ZONE` instead. See
`docs/pjm-api-constraints.md`.

### `data/raw/spike__*.parquet`, `compare__*.parquet`

Exploratory single-shot pulls from the 2026-05-10 spike phase:
- `spike__hrl_load_metered__2026-04-15__dom.parquet` — one-day DOM load
- `spike__rt_hrl_lmps__2026-04-15__pnode_35010371.parquet` — one-day Pleasant View RT hourly
- `spike__rt_fivemin_hrl_lmps__2026-04-15__pnode_35010371.parquet` — one-day Pleasant View 5-min
- `spike__pnode_lookup_three_substations.parquet` — early pnode resolution work
- `spike__smoke_pnode_dom_1row.parquet` — smallest-possible pnode response
- `compare__2026-04-15__multi_pnode_hourly.parquet` — multi-pnode comparison day

Retained for reproducibility of the methodology-decision evidence.
Not part of the production data pipeline; can be deleted if
`data/raw/` cleanup is desired.

---

## 5. Lifecycle notes

**Adding a new feed:**
1. Update `_FEED_SPECS` in `src/surg/acquisition/pull.py` with a
   FeedSpec entry
2. Add a section to this catalog under § 1
3. If the feed feeds the analysis panel, update `EXPECTED_COLUMNS`
   in `src/surg/preprocessing/schema.py` and bump `SCHEMA_VERSION`
4. Add loader + features in `src/surg/preprocessing/{loaders,features}.py`
5. Record the *why* (analysis role) in
   `docs/plans/2026-05-11-phase-transition-methodology.md` § 2

**Expanding a feed's window:**
1. Check archive tier and constraints in `docs/pjm-api-constraints.md`
2. Update the "Planned window" cell in the snapshot table here
3. Run the appropriate `surg-pull` command (Standard tier) or
   `surg-pull-archive` (Plan 1.5, when added)
4. Update the "Disk window" cell to reflect new state
5. If the methodology window itself changes, append a decision entry
   in `docs/decisions.md`

**Cleanup of exploratory files:**
- `spike__*` and `compare__*` parquets under `data/raw/` are safe to
  delete; not consumed by any pipeline code
- `mad_smoke__*.parquet` under `sync_reserve_events/2026/` and
  `reserve_market_results/2026/` should be removed before Plan 2 runs
  (avoids event_id duplication; see Plan 2 task list)

---

## 6. Cross-ISO Stage-1 feeds

Eight markets running the shared level-vs-volatility Stage-1 diagnostic
(`src/surg/diagnostics/stage1.py`). Each market has a paired driver:
`.venv/bin/python scripts/<market>_fetch.py` then
`scripts/<market>_diagnostic.py`. All are **public archives requiring no
API key** except the PJM 5-min feed (gridstatus.io).

Raw data lands in `data/raw/<market>/`; each driver writes an assembled
panel to `data/interim/<market>_diagnostic_panel*.parquet`.

### Raw holdings on disk (2026-08-11)

| Market | `data/raw/` | Files | Size | Notes |
|---|---|---|---|---|
| MISO | `miso/` | 1,317 | 1.4 GB | `da_expost_lmp`, `df_al` |
| SPP | `spp/` | 914 | 3.7 GB | `load`, `price`; annual zips + daily era |
| NYISO | `nyiso/` | 928 | 393 MB | `damlbmp_zone`, `palIntegrated`, `realtime_zone` |
| ERCOT | `ercot/` | 30 | 179 MB | `Native_Load_*.xlsx/zip` |
| ISO-NE | `isone/` | 10 | 83 MB | SMD hourly workbooks, one per year |
| IESO | `ieso/` | 73 | 28 MB | `Demand`, `DemandZonal`, `PriceHOEPPredispOR` |
| CAISO | `caiso/` | 864 | 24 MB | `da_lmp`, `load` |
| PJM 5-min | `gridstatus/` | 750 | 48 MB | `pjm_lmp_real_time_5_min`, `pjm_load` |

### Assembled panels (`data/interim/`)

| Panel | Rows | Size | Window |
|---|---|---|---|
| `nyiso_diagnostic_panel_merged` | 220,290 | 28.7 MB | 2001-06-21 → 2026-08-09 |
| `ieso_diagnostic_panel` | 204,023 | 7.9 MB | 2003-05-01 → 2026-08-08 |
| `nyiso_diagnostic_panel_split` | 188,648 | 27.8 MB | 2005-01-31 → 2026-08-09 |
| `caiso_diagnostic_panel_full_depth` | 152,135 | 4.2 MB | 2009-03-31 → 2026-08-08 |
| `isone_diagnostic_panel` | 92,015 | 14.0 MB | 2016-01-01 → 2026-06-30 |
| `spp_diagnostic_panel` | 89,609 | 36.3 MB | 2016-01-01 → **2026-03-23** |
| `ercot_diagnostic_panel` | 83,975 | 18.9 MB | 2017-01-01 → 2026-07-31 |
| `caiso_diagnostic_panel_modern` | 68,104 | 2.4 MB | 2018-11-01 → 2026-08-08 |
| `miso_diagnostic_panel` | 31,584 | 3.4 MB | 2023-01-01 → 2026-08-08 |

**Window caveats — do not read these spans as "price depth":**

- **SPP stops at 2026-03-23 by decision, not availability.** The load CSV
  schema flips wide→long on 2026-03-24 and the RTO-West roster jumps;
  the panel is deliberately cut before both. See `scripts/spp_fetch.py`.
- **CAISO ships two panels.** `full_depth` reaches back to 2009 on
  *load*, but CAISO **price** data only starts 2023-04-12 (~2.3 y) —
  the deep window is not deep in price. `modern` is the safer default.
- **NYISO ships two panels** (`merged` vs `split`) reflecting a zone
  roster change; pick deliberately, they are not interchangeable.
- **MISO 36/36 level-beats-volatility is inflated** — LRZ3_5 and LRZ4
  share `ILLINOIS.HUB`, so those cells are not independent.
- **ISO-NE real price depth starts 2016-01**, not 2003, despite what the
  older memo claimed.

Sourcing constraints per market live in
`docs/<market>-data-availability-research.md`, with the cross-market
summary in `docs/cross-iso-data-availability-summary.md` and endpoint
verification in `docs/cross-iso-phase2-recon-verification.md`.

---

## 7. UK Power Networks — data-centre load profiles

**The only facility-level data-centre load data in the project.** UKPN is
a distribution network operator (DNO), not an ISO — this feed answers
*load shape*, never price.

- **Fetch:** `.venv/bin/python scripts/ukpn_fetch.py` (idempotent;
  skips slices already on disk)
- **Raw:** `data/raw/ukpn/` — year-partitioned parquet
- **Key:** `UK_POWER_API_KEY` in `.env`
- **Licence:** CC BY 4.0, UK Power Networks (company no. 3870728)

| Dataset | Records | Grain | Window |
|---|---|---|---|
| `ukpn-data-centre-demand-profiles` | 5,442,348 | half-hourly, 96 sites | 2023-01-01 → 2026-05-13 |
| `ukpn-data-centres-by-local-authority` | 45 | per district | snapshot (mod. 2026-04-24) |
| `ukpn-large-demand-list` | 496 | per project | snapshot (mod. 2025-11-04) |

Fields on the profiles feed: `cleansed_voltage_level`,
`anonymised_data_centre_name`, `dc_type`, `local_timestamp`,
`utc_timestamp`, `hh_utilisation_ratio`.

**Four traps, all documented in `docs/ukpn-api-constraints.md`:**

1. **`hh_utilisation_ratio` is not bounded [0,1]** — range [0, 3.992].
2. **`local_timestamp` is UTC despite its name** — verified across
   116,636 rows and 7 DST boundaries. Convert to `Europe/London`
   yourself for any diurnal work.
3. **13.1 % of rows are exact zeros** across 69 of 96 sites; **4 sites
   are 100 % dead**. Structure is bimodal — a few months-long outages
   *plus* ~1,700 short dropouts (median 2 intervals, 754 singletons).
   The singletons manufacture fake full-scale ramps and will corrupt any
   volatility statistic. Mask before computing anything.
4. **`ukpn-large-demand-list` cannot be filtered to data centres** —
   `demand_technology_type` has only two values (Large Demand,
   Distributed Energy Resource).

**Scope limits:** no MW (ratio is observed ÷ *contracted* capacity, so
levels are not comparable across sites — only shapes), no location, no
price. Covers UKPN's three licence areas only (LPN/EPN/SPN), which
**excludes the Slough and West London cluster** (SSEN territory) and all
transmission-connected hyperscale sites.
