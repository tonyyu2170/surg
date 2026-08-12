# Cross-ISO Data Research + Stage-1 Diagnostics — Design

**Date:** 2026-08-09
**Status:** Design approved in conversation; this file pending user review
**Markets:** MISO, SPP, CAISO, IESO, NYISO, ISONE
**Related:** `docs/sources/availability/ercot-data-availability-research.md` (the pattern being replicated),
`docs/specs/2026-08-07-ercot-load-volatility-diagnostic-design.md` (the diagnostic
being replicated), decisions.md 2026-08-07 ERCOT Stage 1 entry (the result being extended)

---

## Purpose

Extend the DOM + ERCOT two-market result into a continent-scale comparison. Every major
North American ISO/RTO gets the same treatment ERCOT got:

1. **Full data-availability research** — can we see data centers in this market's public
   data at all? What load/price data exists, at what resolution, how deep, behind what gates?
2. **The Stage-1 diagnostic** — is load volatile and rising? Does price track load *level*
   or load *volatility*?

End state: an 8-market comparison (PJM/DOM, ERCOT, plus these six) testing whether
**level-beats-volatility holds everywhere, regardless of data-center concentration**. ISONE,
with minimal data-center activity, serves as the natural low-DC control-market contrast.

## Decisions locked (user, 2026-08-09)

| Decision | Choice | Rationale |
|---|---|---|
| Research depth | **Full ERCOT-depth memos, ×6** | Includes facility-level/DC data hunt, queue analogs, confound analysis, academic leads — not just diagnostic-feasibility recon. |
| Sequencing | **Research-first** | All six memos, then a user checkpoint, then one consolidated diagnostic build for the survivors. Memos determine diagnostic feasibility (IESO had no LMP before 2025; SPP's market only exists since 2014). |
| Execution | **Inline sequential** | One researcher, one market at a time. The ERCOT memo's value was empirically verified claims (downloaded the real 57 MB SCED file, profiled 142K rows); that discipline is easier to hold inline, and each memo benefits from patterns the previous ones surfaced. |

## Phase 1 — Six research memos

One memo per market at `docs/<iso>-data-availability-research.md` (lowercase iso name),
mirroring the ERCOT memo's structure:

1. **Headline** — one-paragraph verdict on data-center-load visibility in this market.
2. **Facility-level / DC-specific data hunt** — the decisive positive-or-negative, verified
   empirically, not inferred from product pages.
3. **What this ISO does better/worse than PJM + ERCOT** — price access, congestion
   decomposition availability, gates/quotas/registration walls.
4. **Zonal load archive** — zone structure, resolution, history depth, access path, schema
   quirks, hour-ending vs hour-beginning convention, timezone regime.
5. **Price archive** — same treatment; which series could play the horse-race price role.
6. **Market-specific confounds** — including this market's analog of ERCOT's two named
   confounds (wind on the price side, 4CP price-responsiveness on the load side).
7. **Interconnection queue / large-load tracking** — the growth-forecast angle.
8. **Academic / institutional dataset leads** — the TRAIL-map analog hunt.
9. **Concrete Stage-1 pull spec** — sources, volume estimate, open dependencies.
10. **Source index.**

Sections may be short where the market is thin — "no large-load program exists" is a
finding, not a gap. Every memo ends analysis-ready: section 9 must be concrete enough that
the Phase-2 plan can cite it without re-research.

### Verification bar

- Every **schema claim** backed by downloading and reading at least one real file with the
  project venv.
- Every **history-depth claim** backed by listing the actual archive (counting files, reading
  the earliest one), not quoting a documentation page.
- Claims that resist verification get flagged ⚠️ as unverified, the way the ERCOT memo
  flagged its congestion-derivation dependency.

### Order and rationale

**MISO → SPP → CAISO → IESO → NYISO → ISONE.** Data-center-relevance order (MISO's
Louisiana/Indiana buildout and SPP's Oklahoma corridor are the hottest stories), with the
control market last so its framing benefits from all five before it.

### Starting leads per market (to verify, not inherit)

Everything below is prior knowledge that seeds the research. **Each item must be verified
before it appears in a memo as fact.**

**MISO** — Public market reports at misoenergy.org (`rf_al` regional forecast/actual load;
`da_expost`/`rt_lmp` files by CPNode incl. named hubs); LMP history back to the 2005 market
start. Key risk: public *actual load* may exist only at 3-region granularity
(North/Central/South + total), not the 10 local resource zones — LRZ-level load may sit
behind the registration-gated Data Exchange API or not exist publicly. Publishes in fixed
EST year-round (no DST). Footprint change: MISO South (Entergy) joined Dec 2013 — any
long-window level trend must handle it. DC context: Louisiana (Meta Richland Parish),
Indiana, Illinois; new large-load interconnection process circa 2025–26.

**SPP** — Marketplace portal (portal.spp.org) public files: hourly load by reporting area,
DA/RT LMPs by settlement location, hubs SPPNORTH/SPPSOUTH — since Integrated Marketplace
start March 2014; before that only the EIS market (2007–14, imbalance prices only).
Central time. Footprint change: Integrated System (WAPA/Basin/Heartland) joined Oct 2015.
Confound: severe wind penetration (negative-price territory in the west). DC context:
Google Pryor OK and the Oklahoma corridor.

**CAISO** — OASIS API (oasis.caiso.com), no key: `PRC_LMP` (DAM hourly), `PRC_INTVL_LMP`
(RTM 5-min), demand via `SLD_FCST` family; history back to the April 2009 MRTU start.
Zone structure: TAC areas (PGE, SCE, SDGE, VEA) with DLAP prices per area plus TH hubs
(NP15/SP15/ZP26). OASIS timestamps are GMT. Confounds: behind-the-meter rooftop solar
makes metered load ≠ consumption, and the duck curve is a structural volatility change
unrelated to data centers. Key question: whether Santa Clara (Silicon Valley Power — the
legacy DC cluster, a muni inside the CAISO BA) is inside "CAISO demand" and which TAC/DLAP
covers it. LADWP/SMUD/BANC are separate BAs, excluded.

**IESO** — Public reports directory: hourly zonal demand (10 zones) back to ~2003; HOEP
uniform hourly price back to 2002; **Market Renewal launched May 1 2025 — the LMP era is
~15 months old**, so the horse race pre-2025 runs zonal load against a uniform price (no
locational variation — fine, ERCOT ran hub prices against zone loads). Fixed EST
year-round, hour-ending. Endogeneity analog: the Industrial Conservation Initiative —
Class A loads shave predicted top-5 peaks to cut Global Adjustment charges — is the 4CP
analog, possibly stronger. "Ontario Demand" excludes embedded generation (much Ontario
solar is embedded in LDCs). Prices in CAD — standardized coefficients absorb this; raw
levels don't compare. DC context: Toronto is the largest Canadian DC market.

**NYISO** — mis.nyiso.com public CSVs, no key, the cleanest archive of the six: `pal`
actual load (5-min real-time and integrated hourly) by 11 zones (A–K) back to ~2001;
zonal LBMP DA/RT back to ~1999. Eastern prevailing with an explicit time-zone column
(EST/EDT flags). DC context: modest — upstate crypto (Massena, Greenidge) more than
hyperscale. Confounds: growing BTM solar; zone J (NYC) weather-dominated.

**ISONE** — "SMD hourly" zonal files: 8 load zones with DA/RT LMP + load back to the
March 2003 SMD start; real-time 5-min demand by zone exists. Key access question: which
files are open downloads vs behind the free-registration web-services API. Eastern,
hour-ending, with DST-hour label conventions to verify. Confounds: substantial BTM solar
(mid-day load suppression); winter gas-constraint price spikes unrelated to data centers.
DC context: minimal — the designated control market.

**Cross-cutting checks (every memo):** the peak-response endogeneity analog (4CP ↔ ICI ↔
PJM 5CP ↔ NYISO ICAP tags ↔ ISONE capacity tags ↔ MISO/SPP CP allocations); a
footprint-change audit (which years the system boundary moved); whether the open-source
`gridstatus` library covers this ISO deep enough to serve as probe or fallback fetcher.

### Shared source packet (user-supplied 2026-08-09)

**CRS R48646, "Data Centers and Their Energy Consumption: FAQ" (updated 2026-05-12).**
Federally corroborates the project's core data-availability finding and seeds every memo:

- **No federal dataset of actual DC energy use exists.** EIA's 2021 CBECS pilot surveyed 50
  facilities and got 9 responses; EIA's 2024 mandatory crypto-miner survey was halted by a
  TRO in *Tex. Blockchain Council v. DOE* (W.D. Tex.) and the collected data destroyed.
  S. 1475 (Clean Cloud Act), H.R. 6984, and H.R. 7858 would create collection authority but
  are pending. This is the memo-section-2 framing citation for all six markets: the
  facility-level negative is national, not market-specific — what varies by ISO is proxies.
- **LBNL/Brattle retail-price analysis** (Wiser et al., *Retail Electricity Price Trends and
  Drivers: Data Update — 2026 Edition*, April 2026): 2019–2025 retail price increases were
  driven mainly by grid-infrastructure investment; **states with the largest DC demand
  growth generally saw retail price *decreases***. A system-level retail contrast to this
  project's wholesale congestion findings — synthesis framing must reconcile with it, and it
  reinforces the standing rule against attributing broad price escalation to data centers.
- **Large-load tariff tracking:** Frick & Lam, *Large Loads: Interconnection, Tariff
  Designs, and State Actions* (LBNL/Brattle, Sept 2025) and the SEPA/NCCETC **DELTa**
  database of emerging large-load tariffs — per-state/per-utility material for each memo's
  section 7.
- **Private facility inventories** as proxies: Cushman & Wakefield and Baxtel (the
  Texas-Tribune-map analog, nationally).
- **Estimate-reliability anchors:** Mytton & Ashtine (Joule 2022) on the unreliability of
  DC energy estimates; Koomey & Masanet (Joule 2021) on systematic overestimation. Baseline
  national figure: LBNL 2024 — 176 TWh ≈ 4.4% of US consumption in 2023, excluding crypto.
- Sibling CRS report **R48762** (*Data Center Energy Infrastructure: Federal Permit
  Requirements*) as a permitting-context lead.

### Phase-1 closing deliverable

`docs/sources/availability/cross-iso-data-availability-summary.md` — one comparative table across all six plus
PJM and ERCOT: zone count, load resolution × history, price history, access gates,
DC-load visibility, dominant confound, diagnostic feasibility verdict. This is the
checkpoint's reading packet.

## Checkpoint (hard gate)

User reviews the six memos + summary and decides:

- which markets proceed to the Phase-2 diagnostic;
- which source wins where alternatives exist;
- whether any registration-gated path (ISONE web services, MISO Data Exchange) is worth
  registering for — **registration is always a user decision, never made unilaterally**;
- anything surfaced by research that changes the Phase-2 shape.

Until then the working policy is: prefer ungated, no-registration, no-quota paths — the
ERCOT principle. The gridstatus.io hosted API (quota) is out of scope entirely.

## Phase 2 — Diagnostics (structural spec; finalized at the checkpoint)

Same three outputs per market, same definitions as ERCOT:

1. **Volatility trend** — monthly + annual mean and p95 of |gradient|, per zone, raw AND
   normalized by mean load.
2. **Level trend** — annual mean and peak load per zone.
3. **Horse race** — hourly price regressed on load level vs |gradient|, per zone × price
   series, standardized coefficients, on the DOM-matched window (2022-10-02 →).

**Comparability requirements:**

- The gradient is computed through the same shared machinery DOM and ERCOT used
  (`add_load_gradient_columns` lineage) — never re-implemented per market.
- Load window: full clean-schema zonal history per market (per-market start year chosen by
  the memo, the way ERCOT's memo picked 2017). Price window: DOM-matched.
- Same regression form and reporting as `ercot_diagnostic.py`.

**Architecture:** one shared diagnostic core (panel in → the three outputs + data-quality
summary out), with thin per-market adapters:

- `scripts/<iso>_fetch.py` — download raw archives to `data/raw/<iso>/`
- `src/surg/preprocessing/<iso>_features.py` — parse, convert conventions, wrap the shared
  gradient; tested like `ercot_features.py`
- `scripts/<iso>_diagnostic.py` — thin driver → `data/interim/<iso>_diagnostic_panel.parquet`,
  figures to `outputs/<iso>_diagnostic/`

The shipped `ercot_diagnostic.py` **stays untouched** — its thread is closed and its outputs
are recorded. The shared core is extracted or mirrored from it without retrofitting it;
whether ERCOT is later re-run through the core is a separate decision, not part of this scope.

**Correctness requirements carried over from ERCOT, applied per market:**

- Hour-convention (ending vs beginning) and timezone conversion explicit and asserted —
  including the fixed-EST regimes (MISO, IESO) and DST-labeled regimes (NYISO, ISONE).
- Timestamp uniqueness asserted after every join; duplicate republication blocks dropped
  only while raw labels are still present (the ERCOT May-2026 lesson).
- Gaps surface as failures, never as interpolation.
- Negative prices reported, never clipped.
- Footprint changes (MISO 2013, SPP 2015) flagged in the panel, and level trends reported
  in a way that does not read a boundary change as organic growth.

**Gate criterion per market — unchanged from ERCOT:** a data-quality gate, not a results
gate. Reproducing DOM/ERCOT strengthens the multi-market null; diverging from them is a
genuine contrast; the only failure is a price or load series too confounded to interpret.

## Phase 3 — Synthesis

- One decisions.md entry per market as its diagnostic lands (repo convention).
- Capstone: a cross-market table + figure — load growth %, normalized volatility trend %,
  horse-race verdict (level-vs-volatility win count), R² — across all 8 markets, ordered
  by data-center exposure. PJM/DOM and ERCOT rows reuse recorded numbers where the metric
  definitions match; recompute through the shared core only if they don't.
- A closing decisions.md entry stating what the 8-market comparison does and does not
  support.

## Non-goals

- No Stage-2 ports (QR-full, GPD, tail-risk curves) for any market — separate
  post-checkpoint decisions.
- No causal claims anywhere; this is descriptive.
- No facility-level load reconstruction attempts.
- No gridstatus.io hosted-API usage. The open-source `gridstatus` *library* hitting native
  ISO endpoints is permitted as probe or fallback fetcher.
- No retrofit of the ERCOT script or re-litigation of its closed Stage-2 gate.

## Testing

- Phase 1: no code tests — memos, held to the verification bar above.
- Phase 2: per-market features modules get test modules (the `test_ercot_features.py`
  pattern); the shared diagnostic core gets its own tests; diagnostic drivers rely on
  inline assertions + the printed data-quality summary, per the ERCOT precedent.

## Open items deferred to the checkpoint

- Price series per market for the horse race (zonal/DLAP vs hub) — default zonal where it
  exists; IESO pre-2025 uses HOEP by necessity.
- Which markets actually proceed — including whether any memo's findings justify skipping
  a market entirely.
- Commit cadence for memos (per-memo vs batch) — each commit remains its own ask per
  standing git policy.
