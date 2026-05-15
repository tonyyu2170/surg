# Design — Sub-Q1 Item #8: 5-Min Companion (Two-Part)

> **Status:** Drafted 2026-05-15 (early AM) via the superpowers
> brainstorming skill, then revised after advisor feedback + data
> feasibility check. Pre-registers the design choices for the 5-min
> companion to sub-q1 items #1–4 + #6. This document **IS the pre-reg**
> for item #8 per the light-pre-reg convention established for items
> #2, #3, #4, #6.
>
> Implementation plan will be drafted next via the writing-plans skill
> and committed as
> `docs/plans/2026-05-15-5min-companion-implementation.md`.
> Execution is via the slash command
> `.claude/commands/run-5min-companion.md` (plan-driven launcher,
> ≤4000 chars; user-imposed cap).

## Purpose

Run a 5-minute-resolution companion to the sub-q1 closure work
(items #1–4 mechanism battery + item #6 tail-risk curves), to test
whether the hourly-panel findings hold under finer temporal
granularity and to surface what hourly aggregation washes out.

The companion is **two-part** because PJM API retention forces the
joint Z+LMP analysis into a 30-day window, while LMP-only descriptive
analyses are feasible on the full ~6-month 5-min LMP archive on disk.

| Part | Window | Scope | Statistical posture |
|---|---|---|---|
| **A** Joint Z+LMP | ~30 days (mid-Apr → mid-May 2026, bounded by `inst_load` retention) | Items #1–4 + #6 with block-bootstrap | Pre-registered as **feasibility probe**: every cell expected underpowered |
| **B** LMP-only descriptive | ~6 months (2025-11-12 → 2026-05-10, full 5-min LMP archive on disk) | Single new module: 5-min vs hourly spike-exceedance comparison | Descriptive; no inferential CIs on point statistics |

Item #8 is sequenced **before** item #5 (advisor meeting) so the
advisor sees both mechanism + descriptive characterization at both
temporal resolutions, plus an honest accounting of the data-retention
wall.

## Sub-q1 closure context

| Roadmap item | Resolution | Status |
|---|---|---|
| #1 Spec B continuous ξ(Z) | hourly | DONE (`fe2cb94`) |
| #2 LMP-components decomp | hourly | DONE (`01ebbd8`) |
| #3 τ=0.99 secular sign-flip | hourly | DONE (`72456bb`) |
| #4 Ashburn TX1 q=0.99 anomaly | hourly | DONE (`fd0065c`) |
| #6 Direct Z → LMP tail-risk | hourly | DONE (`b4feb92`) |
| **#8 5-min companion** (**this design**) | **5-min** | **Pending implementation** |
| #5 Advisor meeting | — | Open; gated on #8 |

## Data-retention reality (pre-reg context)

The original brainstorm assumed a 3.6-year 5-min companion (matching
the hourly panel). API verification on 2026-05-15 found this
infeasible:

- **`inst_load` is hard-capped at ~30-day PJM retention**
  (`pjm-api-constraints.md:84`, discovered 2026-05-13). A request
  spanning 6 months returned only the most recent 28 days; PJM
  silently truncates older dates. **No code change can recover older
  data — it does not exist on PJM's servers.**
- **`rt_fivemin_hrl_lmps` Standard tier caps at 186 days**, and
  `pull.py:301-302` explicitly refuses Historic-tier pulls for this
  feed (Historic rejects the `type` filter; bypassing would require a
  full-PJM bulk pull and post-filter, multi-million rows, out of
  scope).
- **`hrl_load_metered`** is hourly-only; cannot substitute as 5-min
  Z source.

So the joint 5-min Z+LMP window is bounded by `inst_load` retention
to ~30 days. The 5-min LMP-only window is bounded by the existing
6-month archive on disk. Both bounds are pre-registered here.

## Pre-registered design choices

This section locks methodology before any code runs. Choices brought
forward from the original (pre-pivot) design that still apply are
noted; new / changed choices are explicit.

### 1. Two-part scope, separated outputs

- **Part A:** Items #1–4 + #6 on the joint 30-day Z+LMP panel.
- **Part B:** Single new module computing the 5-min vs hourly
  spike-exceedance comparison on the 6-month LMP-only panel.

Outputs root at `outputs_5min/` per existing `outputs_*/` gitignore
rule, split into two subtrees:

```
outputs_5min/
  joint_30d/
    gpd_continuous/        (Spec B)
    gpd_components/        (item #2)
    year_fe_diagnostic/    (item #3)
    ashburn_diagnostic/    (item #4)
    tail_risk_curves/      (item #6)
  lmp_descriptive_6mo/
    spike_exceedance_comparison/   (item #8 Part B)
  cross_resolution_summary.json    (Part A only — joint 30d vs hourly)
  cross_resolution_summary.csv
  figures/.gitkeep
  tables/.gitkeep
```

### 2. Part A: Joint Z+LMP, 30-day window

#### 2.1 Time window

Acquisition pulls `inst_load` immediately at slash-command launch (to
maximize freshness). Joint window = the intersection of the freshly
pulled `inst_load` window and the existing `rt_fivemin_hrl_lmps`
on-disk window. Expected: ~30 days, ~mid-Apr → ~mid-May 2026.
Truncation logged in the application entry.

#### 2.2 Filter: same proposal-filter (shoulder + 2–5 AM)

Mar–May + Sep–Nov shoulder months, 2–5 AM EPT. Within the 30-day
window this catches Apr+May (2 shoulder months). In-filter sample:
~30 days × 3 hr × 12 obs ≈ **1,080 obs/pnode**.

#### 2.3 Z (load gradient) at 5-min

```
z_5min[t] = abs(dom_load_mw_5min[t] - dom_load_mw_5min[t-1]) / 5
```

(units: MW/min). Decile binning computed fresh on the 5-min Z
distribution, not inherited from hourly.

#### 2.4 Reserves: forward-fill hourly to 5-min

PJM publishes 5-min reserve clearing, but
`load_reserve_market_results` aggregates to hourly. Rewriting the
loader is out of scope; forward-fill to 5-min within each hour.
Conservative (under-resolves within-hour reserve-price movement).
Items #1–4 use reserves only as covariates, so under-resolution is
documented but not fatal.

#### 2.5 Bootstrap: pure island cluster bootstrap

**Key correction from the original draft, per advisor feedback (two
rounds).** The proposal-filter creates 3-hour islands (2–5 AM = 36
5-min obs) separated by 21-hour gaps. Naive iid pair-bootstrap is
invalid (within-island autocorrelation); naive stationary block
bootstrap is also invalid (blocks can cross gap boundaries, falsely
concatenating different days).

The 5-min run uses **pure island cluster bootstrap**:

1. Index islands 1..K (K ≈ 30 in the 30-day window).
2. Resample K islands with replacement: `idx = np.random.choice(K,
   size=K, replace=True)`.
3. Concatenate the resampled islands into a bootstrap panel.
4. Fit the statistic of interest on the bootstrap panel.
5. Repeat n_boot times; CI is the empirical percentile interval.

For regression-based items (#1 Spec B, #2 components, #3 year-FE)
the bootstrap panel feeds directly into the regression — block
ordering within an island does not enter the likelihood, so an
inner-level stationary-block step adds nothing. For item #6 (binomial
proportion) the same is true: cluster-bootstrap on islands is the
standard reference treatment.

This is the standard cluster-bootstrap approach in the
clustered-data literature (Cameron-Gelbach-Miller). No `arch`
package needed; implementation is `numpy` + existing fitters.

**Effective n = K ≈ 30 islands** (30-day window). This is **below the
conventional 50-cluster floor** for cluster-bootstrap CI reliability —
the bootstrap CIs themselves are noisy, in addition to the underlying
estimator being underpowered. Both effects are pre-registered:

- Wide CIs are expected; not a smoke-gate failure (§4.1).
- CI bounds themselves are imprecise; the application entry frames
  Part A as a feasibility probe, not as inference.

If the K=30 floor concern dominates a specific pnode/threshold cell,
flag it in the per-cell JSON (`n_clusters_below_floor: True`) but
report the estimate anyway — suppression would be more misleading
than reporting with a flag.

#### 2.6 n_boot inheritance

n_boot inherited from hourly: Spec B = 1000, GPD components = 500,
year-FE diagnostic = 500, Ashburn LOO = 175 (its native size), item
#6 tail-risk = 200. Per-task floor of 200; degenerate-block CIs are
flagged in the JSON, not retried.

#### 2.7 Pre-registered acceptance of underpowered findings

Per Rule 2 of the items #1–4 pre-reg, CIs spanning 0 → mark
"underpowered, direction-only." Part A is pre-registered to expect
this on essentially every cell. The application entry will not
relitigate the rule per finding; it will state the data-wall context
upfront, then report the directional pattern alongside hourly for
comparison.

### 3. Part B: LMP-only descriptive, 6-month window

#### 3.1 Window

2025-11-12 → 2026-05-10 (full `rt_fivemin_hrl_lmps` archive on disk).
No new acquisition needed for Part B.

#### 3.2 Filter: NONE

Part B is descriptive characterization of the 5-min LMP distribution
itself. The proposal-filter (volatility-isolation purpose) does not
apply. Use the full 6-month panel.

#### 3.3 Single new module: spike-exceedance comparison

`src/surg/analysis/spike_exceedance_comparison.py`. For each pnode in
the 11-pnode target set, compute:

For each 5-min observation `t`:
- `lmp_5min[t]` = native 5-min LMP at time `t`
- **Headline comparator (per advisor feedback):**
  `lmp_hourly_published[t]` = the published `total_lmp_rt` value
  from `rt_hrl_lmps` for the hour containing `t` (joined on the
  6-month overlap window). This is what our hourly analysis
  actually used; PJM's published hourly LMP may differ from a
  simple mean-of-12 (time-weighted, interval-weighted, or
  settlement-weighted aggregation).
- **Sanity-check comparator (secondary):**
  `lmp_hourly_synthetic[t]` = mean of the 12 5-min obs in the hour
  containing `t`. Used only to characterize how close PJM's
  published hourly is to a naive mean-of-12.
- For each threshold τ ∈ {$50, $100, $250, $500, $1000}:
  - `is_5min_exceedance[t]` = `lmp_5min[t] > τ`
  - `is_hourly_published_exceedance[t]` =
    `lmp_hourly_published[t] > τ`
  - `is_hidden_by_hourly[t]` = `is_5min_exceedance[t] AND NOT
    is_hourly_published_exceedance[t]`
  - (parallel synthetic versions for the sanity-check series)

Headline metrics per (pnode, threshold):

| Metric | Definition |
|---|---|
| `n_5min_exceedances` | count of 5-min obs exceeding τ |
| `n_hourly_published_exceedances` | count of hours whose `total_lmp_rt` exceeded τ (PJM-published) |
| `n_hidden_by_hourly` | 5-min exceedances NOT captured by PJM-published hourly |
| `hidden_fraction` | `n_hidden_by_hourly / n_5min_exceedances` (the headline metric — hidden by PJM hourly aggregation) |
| `n_hourly_synthetic_exceedances` | sanity check — count using mean-of-12 |
| `synthetic_vs_published_agreement` | fraction of hours where synthetic and published exceedance verdicts agree |
| `peak_minus_published_distribution` | within-hour `max(lmp_5min) − lmp_hourly_published` distribution: percentiles {p50, p75, p90, p95, p99, p99.5} |

This directly answers "what does PJM's hourly aggregation hide about
5-min spikes — and how much of that gap is just averaging vs the
specific aggregation method PJM uses?" The headline result is the
**hidden-fraction curve against the published hourly** by threshold,
per pnode; the synthetic comparison is a methodological sidebar.

Joining mechanics: `rt_hrl_lmps` is on disk for the full 6-month
window (verified). Join key: `(pnode_id, hour_floor(datetime_beginning_ept))`.
Misses (5-min obs whose hour has no published hourly row) are
expected to be rare; logged + dropped from the headline numerator
and denominator (recorded as `n_dropped_unmatched_hours`).

#### 3.4 No bootstrap CIs on Part B point estimates

Counts and fractions are computed deterministically on the full
6-month panel. CIs would require a within-day cluster bootstrap that
adds machinery without affecting interpretation (the descriptive
finding is "X% of 5-min spikes are hidden by hourly aggregation,
across this 6-month window"). If Part B's results motivate inferential
follow-up, that's a future item.

#### 3.5 Within-Part-B cross-pnode summary

For comparability, also report the headline hidden-fraction at the
7 sub-q1 target pnodes (subset of the 11) — written to
`outputs_5min/lmp_descriptive_6mo/spike_exceedance_comparison/cross_pnode_summary.csv`.
This is **internal to Part B**; it does NOT land in the top-level
`cross_resolution_summary.{json,csv}` (which are Part A only,
joining 30-day 5-min results to hourly results).

### 4. Smoke gates (NEW; per advisor feedback)

Two gates, both **executional-health only** (verify code runs and
produces well-formed output) — explicitly NOT statistical-quality
gates, because Part A is pre-registered as expected-underpowered and
"wide CI" must not halt the run.

#### 4.1 Production-data smoke gate (Part A)

Run **two** modules on the `primary` pnode only with `n_boot=20`
against the actual joint 30-day panel (not synthetic):

- **Item #6 tail-risk curves** — exercises the cluster-bootstrap
  proportion path.
- **Item #3 year-FE diagnostic** — cheapest of the regression-based
  items; exercises the cluster-bootstrap regression-fit path. Catches
  any cluster-bootstrap integration issue with the MLE / regression
  fitters before the heavy battery launches.

**Pass criteria (executional only, both modules):**

- Each completes in < 5 minutes wall.
- No exceptions raised.
- Output JSON conforms to expected schema (matches keys produced by
  the hourly run on the same module).
- Point estimates finite (not NaN/Inf) for all cells.
- CI fields present (may be `[null, null]` for degenerate clusters —
  this is acceptable; the run notes them and continues).

Explicitly NOT a pass criterion: CI width. Wide CIs are the
pre-registered expected outcome of Part A.

If either smoke module fails, halt + commit current state + report.
Do not launch the heavy battery.

#### 4.2 Hourly-regression smoke gate (NEW; gates any change to shipped modules)

Items #1–4 + #6 are already shipped + merged + cited in
`decisions.md`. This run refactors them to accept an injected
bootstrap strategy. A subtle break in the `--bootstrap-method=pair`
default path could silently re-paint published headlines.

Before *any* shipped module is modified, capture a reference run:
existing hourly fixture (or a representative subset of the
production hourly panel) executed end-to-end through the *current*
items #1–4 + #6 with deterministic seed. Save outputs to
`tests/regression/hourly_reference/`.

After the refactor, re-run the same fixture/seed through the
*modified* items #1–4 + #6 with `--bootstrap-method=pair`. Assert
**numeric equivalence to the reference within bootstrap-seed
tolerance** (point estimates exact; CI bounds within 1e-6 relative
tolerance). Failure halts the run.

This gate runs *between* the refactor task and the Part A production
run. It is the strict prerequisite for trusting the modified hourly
path.

A separate Part B smoke gate is unnecessary — the analysis is a
deterministic count and the panel is on disk.

### 5. Pre-reg discipline: this design + decisions.md item #8 entry

This document is the substantive pre-reg. A short application-style
entry is appended to `docs/decisions.md` **before** the slash command
runs, stating: "Item #8 5-min companion executes per design at
`docs/plans/2026-05-15-5min-companion-design.md`. Two-part: joint
30-day Z+LMP probe (underpowered, pre-registered as feasibility) +
LMP-only 6-month spike-exceedance comparison." The slash command's
first task verifies this entry is committed; if missing or stale, the
run aborts with an instructive error.

## Architecture & integration

### New / modified modules

| Path | Action | Purpose |
|---|---|---|
| `src/surg/preprocessing/build_5min.py` | **Create** | 5-min joint panel builder (Part A). Mirrors `build.py`. ~250 lines. |
| `src/surg/preprocessing/build_5min_lmp_only.py` | **Create** | 5-min LMP-only panel builder (Part B). ~120 lines. |
| `src/surg/preprocessing/loaders_5min.py` | **Create** | 5-min `load_rt_lmp`, `load_dom_load`, `forward_fill_reserves`. ~200 lines. |
| `src/surg/preprocessing/features.py` | **Modify** | Generalize `compute_dom_load_gradient` to accept `freq_minutes`. |
| `src/surg/analysis/spike_exceedance_comparison.py` | **Create** | Part B's single new module. ~180 lines. |
| `src/surg/analysis/bootstrap_strategies.py` | **Create** | Pure island cluster bootstrap implementation (numpy-only). ~80 lines. |
| `src/surg/analysis/run.py` | **Modify** | Add `--panel-path`, `--bootstrap-method {pair,hierarchical}`, `--bootstrap-block-length` flags; route bootstrap strategy into items #1–4 + #6. |
| Items #1–4 + #6 modules | **Modify** | Accept injected bootstrap strategy (currently hardcoded pair-bootstrap). |
| `src/surg/acquisition/pull.py` | **No change** | Existing `inst_load` pull works; Part A explicitly does NOT touch the rejected Historic-5-min path. |
| `tests/preprocessing/test_build_5min*.py` | **Create** | Unit + smoke tests for the two 5-min builders. |
| `tests/preprocessing/test_loaders_5min.py` | **Create** | 5-min loader tests. |
| `tests/analysis/test_spike_exceedance_comparison.py` | **Create** | Part B module tests. |
| `tests/analysis/test_bootstrap_strategies.py` | **Create** | Hierarchical bootstrap tests with synthetic data. |
| `.claude/commands/run-5min-companion.md` | **Create** (gitignored, ≤4000 chars) | Plan-driven slash command. |
| `docs/plans/2026-05-15-5min-companion-implementation.md` | **Create** | Implementation plan. |
| `docs/decisions.md` | **Modify** (pre-launch + post-run) | Pre-reg entry pre-launch; verdict entry post-run. |
| `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md` | **Modify** | Add item #8 row, mark DONE post-run. |
| `pyproject.toml` | **No change** | No new dependency required (cluster bootstrap is numpy-only, per §2.5 simplification). |

### Branch lifecycle

Per the established convention:

1. Sibling worktree `../surg-5min-companion/` on branch
   `feature/sub-q1-item-8-5min-companion`.
2. All work commits to that branch.
3. **No FF-merge, no push.** Stops at "branch ready for user review"
   per locked decision.
4. User reviews + does FF-merge + push manually.

## Slash command structure

`.claude/commands/run-5min-companion.md` — **≤ 4000 characters**
(hard cap, user-imposed). The cap forces it to be a thin wrapper.

What the launcher MUST contain:

- Goal in two sentences.
- Pre-flight checklist (single line each, with which-part-it-gates
  noted):
  1. Pre-reg entry (item #8) committed in `decisions.md` (gates: all)
  2. Design doc path exists (gates: all)
  3. Implementation plan path exists (gates: all)
  4. Main worktree clean (gates: all)
  5. NU DNS workaround active for `api.pjm.com` (gates: **Part A
     only** — Part B uses on-disk data)
  6. (removed — no external bootstrap dependency required)
- One-line invocation: "Execute the plan at
  `docs/plans/2026-05-15-5min-companion-implementation.md` using
  `superpowers:executing-plans`."
- Locked autonomy rules: commit per task; NO FF-merge; NO push;
  run-to-completion regardless of wall time; on any failure not
  handled by the plan, halt + commit current state + report.
- **Visible time-budget warning:** "Estimated 10–15 h wall;
  user-authorized to overflow the 8h target. Re-read this line in
  the morning if surprised by where the run is."
- Final action: write a "ready for review" summary upon completion.

Everything else lives in the implementation plan (no length cap).

## Outputs (full picture)

```
outputs_5min/
  joint_30d/
    gpd_continuous/          # Spec B continuous ξ(Z) per-pnode JSONs + plots
    gpd_components/          # item #2 components decomposition
    year_fe_diagnostic/      # item #3 secular trend
    ashburn_diagnostic/      # item #4 LOO
    tail_risk_curves/        # item #6 exceedance curves
  lmp_descriptive_6mo/
    spike_exceedance_comparison/
      <pnode>.json           # per-pnode hidden-fraction by threshold
      cross_pnode_summary.csv
      hidden_fraction_by_pnode.png
      peak_minus_mean_distribution.png
  cross_resolution_summary.json   # Part A only — 30d vs hourly
  cross_resolution_summary.csv
```

The `cross_resolution_summary` artifacts join Part A's results with
the hourly equivalents at `outputs/<module>/`. Part B has no hourly
counterpart; comparison is intra-Part-B.

## Failure handling

| Failure | Behavior |
|---|---|
| `api.pjm.com` DNS resolution fails | Halt with instructive error citing `pjm-api-constraints.md` § NU DNS workaround. |
| Fresh `inst_load` pull retrieves < 14 days | Halt: 30-day window assumption fails; user must investigate retention. |
| Smoke gate (Task 1) fails | Halt + commit + report. Do NOT launch full battery. |
| API request fails (any) | Retry 3× with exponential backoff (1s, 2s, 4s). |
| 5-min panel build OOM | Halt; log peak RSS. (Unlikely; 30-day panel is ~50 MB.) |
| Block bootstrap returns degenerate CI on a cell | Drop n_boot for that cell to 100; if still degenerate, flag `convergence_status: degenerate_block`; CI = `[null, null]`. |
| Test run fails after a code change | Halt task; commit current state with `WIP:` prefix; report. Do NOT continue. |
| Disk space < 5 GB | Halt with disk-usage report. |

All failures result in a commit reflecting current state and a
written status update; never a silent skip.

## Testing

- `tests/preprocessing/test_build_5min.py` — synthetic 1-day 5-min
  fixture → assert output schema, filter columns, Z computation.
- `tests/preprocessing/test_build_5min_lmp_only.py` — synthetic 1-day
  LMP-only fixture → schema verification.
- `tests/preprocessing/test_loaders_5min.py` — per-loader fixtures.
- `tests/preprocessing/test_features.py` — extend
  `compute_dom_load_gradient` test for `freq_minutes=5`.
- `tests/analysis/test_spike_exceedance_comparison.py` — synthetic
  panel with known peak/mean structure → assert hidden-fraction
  metrics match analytical expectations.
- `tests/analysis/test_bootstrap_strategies.py` — hierarchical
  bootstrap on synthetic data with known autocorrelation; verify
  block lengths respected; verify island boundaries respected.
- `tests/analysis/test_run.py` — `--bootstrap-method hierarchical`
  routes through; smoke-run against fixture.

End-to-end smoke test: synthetic 4-pnode × 1-day panel runs the full
modified analysis surface in < 60s with `n_boot=5`.

Production wall time: see Effort estimate.

## Effort estimate

| Phase | Estimate | Notes |
|---|---|---|
| Fresh `inst_load` pull (~30 days, single feed) | < 30 min | Light API load |
| 5-min panel builds (joint + LMP-only) + tests | 2–3 h | Two new modules + loader |
| Island cluster bootstrap module + tests | ~1 h | numpy-only, ~80 lines |
| Bootstrap-strategy injection into items #1–4 + #6 | 1–2 h | 5 modules; `--bootstrap-method` plumbing |
| Part B `spike_exceedance_comparison` module + tests | 2–3 h | New analytical module |
| **Hourly-regression smoke gate** | 30–60 min | Reference capture + numeric-equivalence assertion |
| **Production-data smoke gate** (item #6 + item #3) | 10 min | n_boot=20, primary pnode, 30-day joint panel |
| Part A production run (items #1–4 + #6 on 30-day joint) | 2–4 h | Cluster bootstrap is faster than the hierarchical alternative |
| Part B production run (spike-exceedance, 6-month) | < 30 min | Deterministic counting, no bootstrap |
| Application entries + cross-resolution summary | 1 h | |
| **Total** | **10–15 h** | Likely overflows 8h. User authorized run-to-completion. |

## Implementation-plan-level details (carry forward to writing-plans)

These are not design choices but execution details the implementation
plan must cover:

- **Part B `hidden_fraction` divide-by-zero:** when
  `n_5min_exceedances = 0` (likely at $1000+ for some pnodes over
  6 months), set `hidden_fraction = NaN` and flag
  `n_below_inference_floor: True`. Do NOT raise an exception; the
  zero-count case is informative ("no 5-min spikes at this
  threshold").
- **Threshold percentile annotations (Part B):** for parity with
  item #6's framing, annotate each Part B threshold with its
  empirical percentile in the 6-month panel (e.g., "$500 (p99.2
  total_lmp)") in the per-pnode JSON and on the headline plot
  legends.
- **Hourly-regression reference capture:** capture a small
  representative subset of the production hourly panel (e.g., 1
  pnode × 90 days) into `tests/regression/hourly_reference/`
  fixtures using deterministic seeds, BEFORE the items #1–4 + #6
  modifications. The post-refactor regression test loads these
  fixtures and asserts numeric equivalence. **Capture must include
  item #6 alongside #1–4** (item #6 is also shipped + cited in
  `decisions.md`, so its hourly path needs the same regression
  guard).
- **Cross-resolution summary — like-for-like comparator:** the
  top-level `cross_resolution_summary.{json,csv}` must NOT compare
  Part A's 30-day 5-min results to the existing 3.6y hourly outputs
  (mixes resolution and window effects). Instead, re-run item #6
  hourly on the same 30-day window before joining (cheap — finishes
  in seconds) and use that as the like-for-like hourly comparator.
  Label the file accordingly: "30-day window, 5-min vs hourly,
  like-for-like."
- **Refresh `rt_fivemin_hrl_lmps` to today before Part A pull:**
  current archive on disk ends 2026-05-10; today is 2026-05-15. A
  small Standard-tier pull (~5 days × 11 pnodes) gets ~5 more days
  of joint window — meaningful at K=30 islands. Add as a parallel
  pre-acquisition step alongside the fresh `inst_load` pull.
- **Refactor task sequencing:** items #1–4 + #6 each have their own
  bootstrap-call sites. Refactor one module at a time, not all five
  simultaneously: (a) capture all reference outputs first, (b)
  refactor one module, (c) run that module's regression test, (d)
  if green, move to the next; if red, halt + commit + report.
  Failing on module 1 saves modules 2–5 from being broken in the
  same way.

## Open questions / Revisit when

- **`inst_load` retention bypass.** If a longer-history 5-min DOM load
  source surfaces (different PJM feed; private dataset from advisor;
  EIA), Part A can be re-run on a real window. Item #8 then becomes
  the v1 record; v2 supersedes.
- **Native 5-min reserves.** Forward-fill is conservative. Future
  revision can rewrite `load_reserve_market_results` for native
  5-min if Part A surfaces a finding sensitive to within-hour
  reserve dynamics.
- **Part B threshold set.** {$50, $100, $250, $500, $1000} matches
  item #6 plus a $50 floor (since LMP medians are $30–50, $50 is the
  "any meaningful spike" threshold for descriptive purposes).
- **Hidden spikes vs hour-of-day.** If Part B surfaces a strong
  hidden-fraction signal, a follow-up could decompose by
  hour-of-day — likely 2–5 AM hidden fractions differ from
  daytime. Out of scope for tonight.
- **Pre-reg amendment.** If implementation forces a methodological
  change, STOP, amend the pre-reg via a new `decisions.md` entry,
  get user sign-off; do not proceed silently.

## Revisit when

- Part B surfaces a hidden-fraction headline that materially changes
  how we interpret the hourly findings (e.g., 50%+ of $500
  exceedances are hidden by hourly mean).
- A longer-history 5-min DOM load source becomes available.
- Advisor (item #5) reframes which resolution is the headline.
- The 30-day Part A window itself changes (e.g., we extend by
  delaying the run a week to grow the inst_load history).
