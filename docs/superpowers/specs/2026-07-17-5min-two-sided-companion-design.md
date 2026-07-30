# 5-Min Two-Sided Companion — Design

**Date:** 2026-07-17
**Status:** Design approved in-session (all four sections); supersedes
the paused 2026-05-15 soft-restart brainstorm and the scope fork it
left open.
**Predecessors:** item #8 pre-reg (`docs/decisions.md` § 2026-05-15 —
Sub-q1 item #8), the 2026-05-15 gridstatus blocker pass
(`docs/gridstatus-api-constraints.md`), and the 2026-06-25 pull plan
(`docs/gridstatus-5min-pull-plan.md`).

## 1. Scope & framing

A pre-registered, **two-sided** replication of the sub-q1 mechanism
tests at 5-minute resolution:

- **Z:** gridstatus `pjm_load.dom` (5-min), treated as DOM-zone 5-min
  load. Disclosure: exactly **one line** in methods/limitations noting
  `dom` is empirically identical to PJM's Southern-Region aggregate
  load (user decision 2026-07-17; no further audit, no repeated
  hedging).
- **Response:** gridstatus `pjm_lmp_real_time_5_min` nodal LMP for
  LOUDOUN (35010365), PLEASANT VIEW (35010371), GOOSECRE (1356178195).

**Relationship to hourly findings:** the hourly analysis (items #1–4,
#6, #9) remains the primary, disclosed *discovery* stage. The 5-min
run is a **confirmatory replication at finer resolution** on a
different (1-year, more recent) window, feeding the advisor meeting
(item #5) as an additional data point. Item #8's original pre-reg is
cited as independent prior motivation.

**Discipline:** a fresh pre-registration of every 5-min spec is
written and committed to `docs/decisions.md` **before any 5-min
result is computed**. No peeking.

**Advisor gate (user decision 2026-07-17):** the previously recorded
"advisor() before fresh pre-reg" rule is **deferred** — the advisor
consult moves to when sub-q1 is completely answered (hourly + 5-min
companion both done), right before sub-q2 unlocks. It folds into the
existing item #5 meeting. The pre-reg commit proceeds without it.

## 2. Data pull

Per `docs/gridstatus-5min-pull-plan.md` (Free tier, as drafted):

- **Window:** `2025-06-24T04:00:00Z → 2026-06-24T04:00:00Z` (latest
  complete EPT-aligned year per the 2026-06-25 metadata check).
  Re-verify `latest_available_time_utc` at pull time; if the boundary
  moved, keep 1-year length, slide forward, and record the final
  window in the pre-reg **before** pulling.
- **Datasets:**
  - `pjm_load`: `interval_start_utc`, `interval_end_utc`, `dom` —
    one pull for the full window.
  - `pjm_lmp_real_time_5_min`: interval bounds + location identity +
    `lmp`, `energy`, `congestion`, `loss` — one pull **per pnode**
    via `filter_column=location_id`, `filter_operator="="` (the
    confirmed-good filter form).
- **Budget:** ~420,480 rows ≈ 84% of the 500K rows/month Free cap;
  ~12–15 of 250 requests. Preflight `GET /api_usage`; **abort if
  remaining monthly rows < 430,000**.
- **Mechanics:** `page_size=50000`, cursor pagination, ≥1.3 s pacing,
  ≥180 s read timeout, every page cached to disk immediately under
  `data/raw/gridstatus/pjm_load/` and
  `data/raw/gridstatus/pjm_lmp_real_time_5_min/`.
- **Validation gates (all must pass before any analysis):**
  - exactly 105,120 intervals per series for the window;
  - unique keys (`interval_start_utc`; `interval_start_utc +
    location_id`);
  - LMP identity `energy + congestion + loss == lmp` within rounding;
  - pnode identity matched by `location_id` exactly;
  - `dom`/`lmp` component columns present, mostly non-null;
  - no overwrites of existing PJM Data Miner files.
- **Ordering:** the pull happens **after** the pre-reg is committed;
  raw data stays untouched on disk until the spec is locked.

Starter-trial expansion (6 pnodes) is **out of scope** (user chose
Free tier 2026-07-17); the pull plan's expansion section remains a
documented option only.

## 3. Analysis spec

**Z definition (new, to be locked in the pre-reg):** Z computed
natively from 5-min `dom` — load gradient over 5-min first
differences (MW/min), analogous in construction to the hourly
gradient. **Default formula: Z_t = (dom_t − dom_{t−1}) / 5 in
MW/min, no smoothing.** The pre-reg either confirms this default or
records a deviation with rationale; either way it is locked before
the pull.

**Tests that replicate** (each pre-registered with its hourly result
as the prior and an explicit confirms / contradicts / underpowered
rule):

1. **QR-full z_slope at τ = 0.90 / 0.95 / 0.99**, full panel — the
   framing-#2 headline candidate. Hourly prior: positive slope, CIs
   excluding 0 at τ=0.90/0.95 on 5/7 pnodes. Expectation: same sign
   on 3/3 or 2/3 pnodes.
2. **Spec A median-split GPD on congestion**, in-filter — the
   pre-registered rejection. Hourly prior: shape_diff = −0.18
   (heavier tail at LOW Z), CI excludes 0.
3. **Tail-risk decile curves** (item #6/#9 style) — descriptive,
   both in-filter and full-window.

**Power context (vs the dead 30-day Part A):** proposal filter
(shoulder months × 2–5 AM) yields ~6,500 in-filter 5-min obs across
two full shoulder seasons and ~180 night-islands for the island
cluster bootstrap — above the 50-cluster floor that made the 30-day
version a feasibility probe only.

**Cannot replicate (disclosed up front in the pre-reg):**

- **No year-FE / secular component** — single-year window; item #3's
  τ=0.99 sign-flip diagnostics do not carry over.
- **No Ashburn TX1** — not in the 3-pnode set; item #4's anomaly
  cannot be probed (distribution-level pnode; this pull covers the
  transmission cluster).
- **Spec B continuous ξ(Z) skipped** — underpowered at hourly with
  7 pnodes × 3.6 y; no reason to expect better here.

**Dropped (user decision 2026-07-17):** old item #8 Part B (5-min vs
PJM-hourly hidden-fraction comparison) is not part of this work.

## 4. Implementation shape & execution order

**New code (existing repo patterns, TDD):**

- `src/surg/acquisition/gridstatus_client.py` + pull entry point —
  mirrors the PJM client (retry/backoff per
  `docs/gridstatus-api-constraints.md`, cache-per-page, quota
  preflight, `follow_redirects=False`).
- Preprocessing extension building a validated 5-min analysis panel
  (schema-versioned parquet, same conventions as the hourly panel
  builder).
- **Analysis reuse, not rewrite:** QR-full, Spec A GPD, and
  decile-curve modules are parameterized for the 5-min run (new Z
  column, filter mask, island-cluster bootstrap config). Hard-coded
  hourly assumptions get parameters; the existing 255-test suite
  stays green.

**Execution order:**

1. Write + commit the pre-registration (`docs/decisions.md` entry:
   final window, Z formula, tests, confirmation rules, the one-line
   dom disclosure). Also commits the two currently-uncommitted
   gridstatus doc files as part of the paper trail. (Each commit
   asks explicit permission per the git rule.)
2. Quota preflight → pull → validation gates (§2).
3. Panel build → run the three pre-registered tests → single results
   entry in `docs/decisions.md`.
4. Advisor meeting (item #5) with hourly + 5-min picture together;
   then sub-q2 unlocks.

**Testing:** TDD for all new acquisition/preprocessing code;
regression fixtures for analysis runs (n_boot=50, seed=42 repo
convention).

## Decisions log (this design session, 2026-07-17)

| Decision | Choice |
|---|---|
| Scope fork (A/B/C from paused brainstorm) | **Two-sided** per the 2026-06-25 pull plan (supersedes A/B/C) |
| `dom` column identity | Treat as DOM-zone 5-min load, as-is; **one-line** Southern-Region disclosure in methods/limitations; no audit |
| Tier / pnodes | Free tier, 3 pnodes, 1 year |
| Old Part B (hidden fraction) | Dropped |
| Advisor gate | Deferred to post-5-min, pre-sub-q2 (folds into item #5) |
