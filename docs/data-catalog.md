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

---

## Snapshot

Joint analysis window: **2022-10-02 → 2026-05-10** (~3.6y, all post-cap;
see decisions.md "2026-05-12 — Window extension to 3.6y post-cap").

| Feed | Disk window | Planned window | Grain | Scope | Role |
|------|-------------|----------------|-------|-------|------|
| `rt_hrl_lmps` | 2024-05-26 → 2026-05-10 | 2022-10-02 → 2026-05-10 (9 pnodes via Plan 1.5; 2 LOAD pnodes stay 2y) | hourly | 11 target pnodes | Primary TAR response; controls; mechanism test |
| `da_hrl_lmps` | 2024-05-26 → 2026-05-10 | — (deferred DA-RT spread analysis) | hourly | 11 target pnodes | Deferred |
| `rt_fivemin_hrl_lmps` | 2025-11-12 → 2026-05-10 | — (Historic intractable, no `type` filter) | 5-min | 11 target pnodes | High-resolution volatility within post-2025-11 portion |
| `hrl_load_metered` | 2021-01-01 → 2026-05-07 | already covers | hourly | DOM zone | TAR threshold variable (load gradient); growth-projection baseline |
| `sync_reserve_events` | 2024-05-26 → 2026-03-05 | 2022-10-02 → 2026-05-10 | event timestamps | MAD sub-zone | ORDC validation; Granger causality (load → event); rare-event corroboration |
| `reserve_market_results` | 2024-05-26 → 2026-05-10 | 2022-10-02 → 2026-05-10 | 5-min → aggregated hourly | MAD locale, services SR + PR | Severity quantification of reserve scarcity; high-clearing-price threshold for stressed regime |
| `dom_pnodes_all` | snapshot | n/a | one row per pnode | DOM zone (2,328 pnodes) | Reference / pnode resolution |

Symbols:
- "Planned window" reflects the post-Plan-1.5 state (`docs/plans/2026-05-11-acquisition-archive-mode.md`, to be written).
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
Currently: 188,760 rows (11 pnodes × 17,160 hours, 2024-05-26 →
2026-05-10).

**Pull:** `surg-pull --feed rt_hrl_lmps --target-group dom_targets …`
(Standard tier, pnode_id filter). For 2022-10-02 → 2024-05-11 backfill
(Historic tier), Plan 1.5 will add archive-mode support using
`type=<subtype>` filters (EHV / ZONE; LOAD intentionally skipped — see
"Asymmetric LOAD coverage" below).

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

**Disk:** `data/raw/sync_reserve_events/`. 36 events, 2025-01-21 →
2026-03-05 (0 in 2024-05-26 → 2025-01-20, 28 in 2025, 8 in 2026-partial).
Smoke duplicate (`mad_smoke__2026-04-01_to_2026-04-30.parquet`) is
slated for removal before Plan 2's bulk preprocessing.

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
scale. The 1.6y backfill window (2022-10-02 → 2024-05-25) is expected to
yield ~10-15 events.

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

**Disk:** `data/raw/reserve_market_results/`. 411,840 rows, 2024-05-26 →
2026-05-10 (288 5-min intervals/day × 715 days × 2 services). Smoke
duplicate (`mad_smoke__2026-04-15_to_2026-04-15.parquet`) is slated for
removal — its rows are subsets of the bulk files but groupby+mean in
the loader self-heals against duplicates (unlike `sync_reserve_events`).

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

| pnode_id | Name | Subtype | Voltage | Tier | Role | Planned window |
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
| 34886139 | ASHBURN TX1 | LOAD | 35 kV | Distribution | Distribution-side TAR (separate fit) | **2y only** (LOAD subtype intractable in Historic — see "Asymmetric LOAD coverage") |
| 34886141 | ASHBURN TX2 | LOAD | 35 kV | Distribution | Distribution-side TAR (separate fit) | **2y only** |

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
