# Sub-Question 1 Batched Diagnostics — Design

> **Status:** Drafted 2026-05-14 from a brainstorming session that
> locked the open items (#2/#3/#4) on
> `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`. Pre-reg
> Section 3 below is locked-rule content; everything else is the
> design for the implementation plan.

## Context

Sub-question 1 closure roadmap (drafted 2026-05-14) carries five items.
Item #1 (Spec B continuous ξ(Z)) closed the same day. Items #2, #3, #4
are three independent diagnostic investigations whose outputs feed the
paper's methods / discussion sections. Item #5 (advisor meeting) is
gated on those three.

This design defines a **single batched plan** covering items #2, #3, and
#4 (Approach C, locked 2026-05-14). Each item:

- Produces a methodology paragraph in `docs/decisions.md` (an
  "application entry" mirroring the Spec B and conditional-Z battery
  application entries on the same date).
- Reuses existing fits where possible; adds new fits / orchestration
  only where the diagnostic requires.
- Lands as a new analysis module under `src/surg/analysis/` with
  tests and `run_all` wiring (matching the Spec B / conditional-Z
  battery pattern).

Item #2 is the only one that pre-registers a hypothesis test (with a
locked decision-rule table). Items #3 and #4 are descriptive in the
strict sense — examining the shape of existing findings, not testing
new claims.

## Scope

**In scope.** The full implementation of items #2, #3, #4 from the
sub-q1 closure roadmap, with full-coverage methodology (decided
2026-05-14):

- **#2 — LMP-components decomposition.** Median-split conditional-Z
  test on three LMP components separately (system_energy, congestion,
  marginal_loss). Headline test pre-registered; cross-pnode +
  threshold sweep descriptive supplementary.
- **#3 — τ=0.99 secular sign-flip diagnostic.** Three-layer evidence
  (raw per-year stats, year-dummy bootstrap, secular-component
  bootstrap). Extended to τ=0.90/0.95/0.99 × 7 pnodes for full
  coverage.
- **#4 — Ashburn TX1 99th-pct anomaly diagnostic.** LOO sensitivity
  at all 4 thresholds (90/95/99/99.5) on TX1 and TX2, with side-by-
  side comparison and a 4-panel overlay scatter figure.

**Out of scope.** Sub-q1 closure item #5 (advisor meeting; separate
work track); JLARC projection (sub-q2; plan-writing gated on
sub-q1 close); paper-figure generation beyond the diagnostic scatter
required by item #4; Ashburn LOAD historic backfill; refactors to
the orchestrator's pnode looping pattern.

## Architecture overview

Six phases, sequenced for the implementation plan:

1. **Preprocessing extension** (Phase 1). Bump `SCHEMA_VERSION`; keep
   `system_energy_price_rt` + `marginal_loss_price_rt` raw columns;
   add wide-pivot per-pnode columns + Loudoun cluster means; rebuild
   `data/interim/analysis_panel.parquet` via `surg-prep`.
2. **Item #2 pre-reg entry** (Phase 2). Commit Rule 1–4 to
   `docs/decisions.md` before any new fit runs.
3. **Three new analysis modules** (Phase 3). `gpd_components.py`,
   `year_fe_diagnostic.py`, `ashburn_diagnostic.py`. Each with tests
   and `run_all` wiring.
4. **Production runs** (Phase 4). Full-coverage runs through `run_all`
   with new flags. Resumable.
5. **Three application entries** (Phase 5). One per item, each
   applying its pre-reg (where applicable) or summarizing its
   descriptive evidence.
6. **Roadmap update** (Phase 6). Mark #2/#3/#4 DONE in
   `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`.

Phase 1 blocks Phase 3 module work for `gpd_components.py` (panel
must exist with new columns). Phase 2 must precede Phase 3 for
`gpd_components.py`. Phases 3-5 within `year_fe_diagnostic.py` and
`ashburn_diagnostic.py` can proceed in parallel with `gpd_components`
once Phase 1 lands.

## Phase 1 — Preprocessing extension

### File-level changes

**`src/surg/preprocessing/loaders.py`** (`rt_hrl_lmps` loader):
- The raw `rt_hrl_lmps/*.parquet` files contain four price columns:
  `system_energy_price_rt`, `total_lmp_rt`, `congestion_price_rt`,
  `marginal_loss_price_rt`. Currently the loader retains only
  `total_lmp_rt` and `congestion_price_rt`. Extend the column-keep
  list to include `system_energy_price_rt` and
  `marginal_loss_price_rt`. No new I/O.
- Wide-pivot logic: for each pnode in the target set, emit
  `system_energy_price_rt_<pnode>` and `marginal_loss_price_rt_<pnode>`
  columns parallel to the existing `total_lmp_rt_<pnode>` /
  `congestion_price_rt_<pnode>` columns.

**`src/surg/preprocessing/features.py`** (derived columns):
- Add `system_energy_price_rt_cluster_mean` and
  `marginal_loss_price_rt_cluster_mean` parallel to the existing
  `congestion_price_rt_cluster_mean` / `total_lmp_rt_cluster_mean`.
  Use the same Loudoun cluster pnode list.

**`src/surg/preprocessing/schema.py`** (validator):
- Bump `SCHEMA_VERSION` from `1` to `2`.
- Add the new columns (per-pnode + cluster means) to the validator's
  expected schema. New columns must be `double` and may contain NaN
  with the same coverage pattern as the existing component columns
  (i.e., NaN where the source pnode lacks data for that hour).

### Panel rebuild

`surg-prep` regenerates `data/interim/analysis_panel.parquet` end to
end. Estimated rebuild time: sub-minute (current panel is 31,536
rows × ~40 columns; we add ~14 columns).

### Compatibility

`schema_version` is enforced by `panel.load_panel()` via
`_check_schema_version`. After the bump, any existing
`outputs/*.json` results are still valid (they don't reference the
new columns), but re-running `surg-analyze` against an unbuilt panel
will raise. The Phase 1 commit message should call this out so the
operator runs `surg-prep` before re-invoking the analysis layer.

### Tests (Phase 1)

Mirror existing preprocessing test patterns:

- **Loader smoke** — load a single raw `rt_hrl_lmps` parquet file
  (both `dom_targets__*` post-2024-05-26 form and one
  `dom_targets_archive_*` pre-2024-05-26 form) and confirm the new
  component columns survive. Confirms no column-name drift between
  the archive and current raw schemas.
- **Wide-pivot columns** — confirm `system_energy_price_rt_<pnode>`
  and `marginal_loss_price_rt_<pnode>` exist for every pnode in the
  target set.
- **Cluster mean** — confirm `system_energy_price_rt_cluster_mean`
  and `marginal_loss_price_rt_cluster_mean` produce expected values
  on a small fixture (mean of the per-pnode columns over the cluster
  members).
- **Schema-version bump** — confirm a parquet file at the previous
  version raises `ValueError` with the new validator.

## Phase 2 — Item #2 pre-registration

A new `docs/decisions.md` section titled:

> **"2026-05-XX — Pre-registration: LMP-components decomposition (sub-q1 closure item #2)"**

(date stamped at write time; `XX` filled in when committed.)

### Rule 1 — Singular headline test (pre-committed)

The singular paper-level claim from item #2 is the **median-split
conditional-Z test on `system_energy_price_rt_cluster_mean` at
95th-pct LMP**, on the primary Loudoun cluster, with
Z = `dom_load_gradient_abs_mw_per_min`, applied to the filtered
subset (`passes_proposal_filter=True`). This is the same scope as
the 2026-05-14 conditional-Z battery's headline test on congestion
(n=1577 at 95th-pct → 789/half), substituting the response variable.

All other tests run in Phase 4 are descriptive supplementary,
including: (a) the same median-split applied to
`congestion_price_rt_cluster_mean` and
`marginal_loss_price_rt_cluster_mean` on the primary cluster;
(b) cross-pnode supplementary across all 7 pnodes for each component;
(c) threshold sweep at 90/95/99-pct LMP.

### Rule 2 — Decision-rule table for the headline

The test produces `shape_diff = ξ_high − ξ_low` with a pair-bootstrap
95% CI. Outcome interpretation (locked before any fit runs):

| Outcome | Paper claim |
|---|---|
| `shape_diff > 0`, CI excludes 0 | **Cancellation hypothesis supported.** system_energy carries the ORDC-predicted direction (heavier tail at HIGH Z); congestion's opposite-direction effect cancels it in total_lmp. This is the proposal's strongest mechanism-affirming outcome. |
| `shape_diff < 0`, CI excludes 0 | **ORDC-predicted direction rejected for system_energy too.** Heavier-tail-at-LOW-Z effect is broader than congestion; mechanism is NOT ORDC-specific. Sharpens the conditional-Z rejection rather than redirecting it. |
| CI spans 0, `shape_diff < 0` | **Underpowered;** direction consistent with congestion finding (heavier tail at LOW Z), not consistent with ORDC's predicted direction. Magnitude bounded only by the available n; paper acknowledges the power ceiling. |
| CI spans 0, `shape_diff ≥ 0` | **Underpowered;** direction consistent with ORDC's predicted direction (heavier tail at HIGH Z) but cannot confirm at this scope. Same power-ceiling language. |

**Mechanistic basis.** The PJM ORDC adds scarcity adders to the
system marginal price when synchronized reserves drop below the
demand curve threshold. Reserve drawdown is concentrated during
high-load / high-volatility events → ORDC scarcity events
concentrate at HIGH Z → system_energy_price spikes at HIGH Z →
heavier tail at HIGH Z → `shape_diff > 0`. The 2026-05-14
conditional-Z battery's rejection on congestion produced
`shape_diff < 0` (heavier tail at LOW Z, OPPOSITE direction to
ORDC's prediction). The "cancellation hypothesis" predicts these
opposite-direction effects partially offset when aggregated into
total_lmp, explaining why the same median-split test on total_lmp
was inconclusive in prior runs.

### Rule 3 — Spline/LRT layer

Not applicable to item #2 (median-split is binary, not continuous).
Reference only.

### Rule 4 — Low-power skip rule

Any individual median-split test for which `n_exc / 2 < 50` reports
status `insufficient_sample` and does NOT contribute a verdict line.
The threshold of 50 matches the typical GPD MLE convergence floor
on a 2-parameter (ξ, σ) fit, below which the asymptotic likelihood
geometry becomes unreliable. Cross-pnode supplementary tests on
Ashburn TX1 / TX2 at deep thresholds (99th-pct, 99.5th-pct) may
trigger this rule.

### Rule 5 — Multiple-testing posture

Singular headline only at α=0.05. All other tests in Phase 4 are
descriptive supplementary; reported with point estimates + bootstrap
CIs but no family-wise correction. Matches Spec B's Rule 1 posture
exactly.

## Phase 3 — Three new analysis modules

### 3.1 — `src/surg/analysis/gpd_components.py`

**Purpose.** Implement item #2 — median-split conditional-Z on the
three LMP components, both at the singular headline scope and as
descriptive supplementary across pnodes and thresholds.

**Reuses.** `gpd.py:gpd_quantile_split_on_z` (existing primitive: GPD
median-split on Z, returns `shape_diff` with bootstrap CI). The new
module is orchestration + output structure, not new statistical
method.

**Public API:**

```python
@dataclass(frozen=True, slots=True)
class ComponentsHeadlineResult:
    component: str          # "system_energy", "congestion", "marginal_loss"
    pnode_label: str
    threshold_quantile: float
    n_exc: int
    shape_diff: float
    shape_diff_ci_95: tuple[float, float]
    rule_2_outcome: str     # "cancellation_supported" |
                            # "ordc_rejected_broader" |
                            # "underpowered_neg_direction" |
                            # "underpowered_pos_direction" |
                            # "insufficient_sample"
    paper_claim: str        # Filled per Rule 2 table.

def run_gpd_components(
    panel: pd.DataFrame,
    out_dir: Path,
    *,
    cluster_response_cols: dict[str, str],   # component -> col name
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    filter_col: str = "passes_proposal_filter",
    threshold_q: float = 0.95,
    n_boot: int = 200,
    seed: int = 0,
    components_for_supplementary_threshold_sweep: tuple[float, ...] = (0.90, 0.95, 0.99),
    cross_pnode_response_cols: dict[str, dict[str, str]] | None = None,
) -> None: ...
```

**Outputs** (under `outputs/gpd_components/`):

- `headline.json` — singular headline result (Rule 1 + Rule 2 outcome).
- `primary_cluster_supplementary.json` — congestion + marginal_loss at
  95th-pct on primary cluster (descriptive, no Rule 2 outcome).
- `cross_pnode.json` — 3 components × 7 pnodes × 1 threshold (95th).
- `threshold_sweep.json` — 3 components × primary cluster × 3
  thresholds.

**Headline JSON shape:**

```json
{
  "rule_1_singular_headline": "system_energy_price_rt_cluster_mean median-split @ p95 LMP, Loudoun cluster, filtered subset",
  "component": "system_energy",
  "pnode_label": "primary_cluster",
  "threshold_quantile": 0.95,
  "filter_col": "passes_proposal_filter",
  "z_col": "dom_load_gradient_abs_mw_per_min",
  "n_exc": 1577,
  "n_per_half": 789,
  "shape_diff": -0.XXX,
  "shape_diff_ci_95": [..., ...],
  "rule_2_outcome": "...",
  "paper_claim": "..."
}
```

**Tests** (`tests/analysis/test_gpd_components.py`, ~10-12 tests):

- Orchestrator emits all four expected output paths.
- Headline JSON keys match schema.
- Rule 2 outcome dispatches correctly for fixture inputs covering
  all four (and the `insufficient_sample`) cases.
- Reduces to identical numbers as `gpd_quantile_split_on_z` called
  directly when applied to the same column (regression).
- Low-power skip behavior (`n_exc/2 < 50` → `insufficient_sample`)
  fires on a fixture.
- NaN-to-None serialization preserved.

### 3.2 — `src/surg/analysis/year_fe_diagnostic.py`

**Purpose.** Implement item #3 — three-layer diagnostic on the
τ=0.99 secular sign-flip, generalized to τ=0.90/0.95/0.99 × 7
pnodes.

**Reuses.** `qr_full.py:fit_qr_full` (existing QR fitter with year-FE
spec). The new module wraps it in bootstraps and adds a raw
per-year stats layer.

**Layer 1 — Raw per-year percentile stats** (`compute_raw_per_year_stats`).
Pure pandas: per (pnode, year), compute the year-level 90/95/99-pct
of `response_col` plus `n_exc` at each panel-overall threshold.
No model, no bootstrap. Surfaces whether the "downward trend" is
visible in the raw distribution or is solely an artifact of the
year-FE decomposition.

**Layer 2 — Year-dummy coefficient bootstrap** (`bootstrap_year_dummy_coefs`).
Pair-bootstrap n_boot=200 of `fit_qr_full` with `year_fe` spec;
record each year-dummy coefficient across reps; return 2.5/97.5
quantiles per (pnode, τ, year). **Reported as descriptive per-year
level-shift CIs, not a trend test.** Reviewers reading this layer
should not infer a slope from the year-dummy pattern; the trend
test lives in Layer 3.

**Layer 3 — Secular-component bootstrap** (`bootstrap_secular_component`).
The secular component is `primary_z_slope − year_fe_z_slope` (the
variance attributed to year FE). Per rep: resample rows with
replacement; fit both `primary` and `year_fe` specs on the same
resampled rows; compute the difference; aggregate 2.5/97.5
quantiles. Produces an explicit CI on "is the secular component
statistically non-zero?" This is the trend test for the
"downward at τ=0.99" claim.

**Public API:**

```python
@dataclass(frozen=True, slots=True)
class YearFEDiagnosticResult:
    pnode_label: str
    response_col: str
    layer1_raw_per_year: list[dict]          # per-year stats
    layer2_year_dummy_bootstrap: dict        # by tau -> by year -> {point, ci}
    layer3_secular_component_bootstrap: dict # by tau -> {point, ci, primary, year_fe}
    n_total_panel: int
    n_after_dropna: int

def run_year_fe_diagnostic(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    pnode_label: str,
    response_col: str,
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    taus: tuple[float, ...] = (0.90, 0.95, 0.99),
    pct_list: tuple[float, ...] = (0.90, 0.95, 0.99),
    n_boot: int = 200,
    seed: int = 0,
) -> None: ...
```

**Outputs** (under `outputs/year_fe_diagnostic/`):

- `<pnode_label>.json` — one per pnode (7 files), full three-layer
  payload.
- `cross_pnode_summary.json` — flattened table across pnodes for
  paper inclusion (one row per pnode × τ).

**Per-pnode JSON shape:**

```json
{
  "pnode_label": "primary_cluster",
  "response_col": "congestion_price_rt_cluster_mean",
  "z_col": "dom_load_gradient_abs_mw_per_min",
  "n_total_panel": 31536,
  "n_after_dropna": ...,
  "taus": [0.90, 0.95, 0.99],
  "layer1_raw_per_year": [
    {"year": 2022, "n_obs": 2208, "p90": ..., "p95": ..., "p99": ..., "n_exc_p99": ...},
    ...
  ],
  "layer2_year_dummy_bootstrap": {
    "tau_0.99": {
      "year_2023": {"point": ..., "ci": [..., ...]},
      ...
    },
    ...
  },
  "layer3_secular_component_bootstrap": {
    "tau_0.99": {
      "primary_z_slope": ...,
      "year_fe_z_slope": ...,
      "secular_component_point": ...,
      "secular_component_ci": [..., ...]
    },
    ...
  }
}
```

**Tests** (`tests/analysis/test_year_fe_diagnostic.py`, ~8-10 tests):

- Layer 1 matches direct pandas-quantile computation on a fixture.
- Layer 2 bootstrap CI brackets the point estimate on a fixture where
  ground truth is known (e.g., a panel with a known year-level shift).
- Layer 3 secular bootstrap matches manual `primary − year_fe` on a
  small deterministic case (n_boot=2, seed fixed).
- Skip-reason emitted when panel spans only 1 year (matches `qr_full`).
- Orchestrator schema integration test (all expected keys present).
- NaN-to-None preserved.

### 3.3 — `src/surg/analysis/ashburn_diagnostic.py`

**Purpose.** Implement item #4 — leave-one-out sensitivity, TX2
comparison, and a 4-panel overlay scatter for the Spec B 99th-pct
Ashburn TX1 sign-flip anomaly. Full coverage: LOO at all 4
thresholds (90/95/99/99.5) on both TX1 and TX2.

**Reuses.** `gpd_continuous.py:fit_gpd_continuous_z` (Spec B's linear
form fitter). LOO refits the linear form (no bootstrap inside LOO;
LOO IS the resampling).

**LOO procedure (per pnode × threshold):**

1. Identify the `n_exc` exceedances at the threshold quantile.
2. For each exceedance index `i` in 0..n_exc-1:
   - Drop that single (LMP, Z) pair from the exceedance set.
   - Refit `fit_gpd_continuous_z` (linear form only; spline not in
     LOO scope) on the remaining `n_exc - 1` pairs.
   - Record `β₁`, `scale_β₁`, log-likelihood.
3. Compute the distribution of `β₁` across the n_exc LOO refits;
   compute `|Δβ₁| = |β₁_LOO − β₁_full|` for each dropped exceedance;
   sort and identify the top-5 most-influential exceedances
   (largest `|Δβ₁|`).
4. Summary: full-sample `β₁`, LOO distribution mean / median / IQR /
   2.5-97.5 quantile range; percentile rank of full-sample `β₁`
   within the LOO distribution.

**TX2 cross-check.** For each threshold, side-by-side TX1 vs TX2:
- Full-sample β₁ + bootstrap CI (from existing
  `outputs/gpd_continuous/ashburn_tx{1,2}.json`).
- LOO summary (this module's new output).
- Direction agreement / disagreement flag.

**Visual scatter.** Single 4-panel matplotlib figure (one panel per
threshold quantile):
- X-axis: Z = `dom_load_gradient_abs_mw_per_min` (log scale if
  data justifies; linear otherwise — decided at implementation).
- Y-axis: LMP value (`total_lmp_rt_ashburn_tx1` or `tx2`).
- Points: ~`n_exc` exceedances at the panel threshold.
- Color: by year (2024/2025/2026 — Ashburn pnodes span ~2y).
- Marker shape: by pnode (circle = TX1, triangle = TX2).
- Overlay: fitted linear ξ(Z) curve from Spec B's full-sample fit
  (separate curves for TX1 and TX2).
- Annotation: top-5 most-influential LOO exceedances (per pnode)
  labeled with their |Δβ₁| value.
- No hour-of-day encoding (the LOO ranking identifies influential
  points; adding a fourth visual dimension is clutter).

**Public API:**

```python
@dataclass(frozen=True, slots=True)
class LOOResult:
    pnode_label: str
    threshold_quantile: float
    n_exc: int
    full_sample_beta_1: float
    loo_beta_1_distribution: list[float]     # length n_exc
    delta_beta_1_per_exceedance: list[float]
    top5_influential_indices: list[int]
    full_sample_percentile_in_loo: float

def run_ashburn_diagnostic(
    panel: pd.DataFrame,
    out_dir: Path,
    *,
    pnode_labels: tuple[str, ...] = ("ashburn_tx1", "ashburn_tx2"),
    threshold_quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    spec_b_results_dir: Path | None = None,   # default Path("outputs/gpd_continuous"); source for TX1/TX2 4-threshold sweep extraction
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    response_col_template: str = "total_lmp_rt_{pnode}",
    seed: int = 0,
) -> None: ...
```

**Outputs** (under `outputs/ashburn_diagnostic/`):

- `tx1_loo.json` — LOO summary across 4 thresholds.
- `tx2_loo.json` — same for TX2.
- `cross_threshold_summary.json` — TX1 + TX2 side-by-side across 4
  thresholds (full-sample + LOO summary stats).
- `scatter_overlay.png` — 4-panel TX1+TX2 overlay figure.

**Tests** (`tests/analysis/test_ashburn_diagnostic.py`, ~7-9 tests):

- LOO on a fixture with `n_exc=10` produces 10 leave-one-out β₁
  values; full-sample β₁ differs from each LOO β₁ (sanity).
- Top-5 influential exceedances are sorted by descending `|Δβ₁|`.
- `extract_threshold_sweep_summary` parses an existing Spec B JSON
  fixture correctly (test against a committed fixture path).
- Scatter PNG file written + non-zero size (no image-content
  asserting; visual review).
- Orchestrator integration test producing all expected output paths.

### 3.4 — `run_all` wiring

In `src/surg/analysis/run.py`, after the existing Spec B and
conditional-Z robustness invocations, add three new orchestrator
calls:

```python
# Sub-q1 closure items #2/#3/#4 (batched diagnostics):
if not args.skip_gpd_components:
    run_gpd_components(panel, out_dir=Path("outputs/gpd_components"), ...)

if not args.skip_year_fe_diagnostic:
    for pnode_label, response_col in PNODE_TO_RESPONSE_COL.items():
        run_year_fe_diagnostic(panel, out_path=..., pnode_label=..., response_col=..., ...)

if not args.skip_ashburn_diagnostic:
    run_ashburn_diagnostic(panel, out_dir=Path("outputs/ashburn_diagnostic"), ...)
```

New CLI flags (mirroring existing patterns):

- `--components-n-boot` (default 200) — bootstrap reps for
  `gpd_components`.
- `--year-fe-n-boot` (default 200) — bootstrap reps for
  `year_fe_diagnostic`.
- `--ashburn-loo-skip` (default false; true reuses existing
  `outputs/ashburn_diagnostic/*` if present) — LOO is the longest
  compute step in this plan.
- `--skip-gpd-components` / `--skip-year-fe-diagnostic` /
  `--skip-ashburn-diagnostic` — per-step skip flags.

`--ashburn-loo-skip` is a soft idempotency tool (operator re-runs
`run_all` without rerunning LOO if `outputs/ashburn_diagnostic/*`
already exists). The per-step `--skip-*` flags are hard skips that
bypass the orchestrator call entirely.

### 3.5 — Integration test (`tests/analysis/test_run.py`)

Extend the existing run_all integration test to cover the new
expected output paths:

- `outputs/gpd_components/{headline,primary_cluster_supplementary,cross_pnode,threshold_sweep}.json`
- `outputs/year_fe_diagnostic/{<pnode_label>.json × 7, cross_pnode_summary.json}`
- `outputs/ashburn_diagnostic/{tx1_loo,tx2_loo,cross_threshold_summary}.json` + `scatter_overlay.png`

Total new expected paths: 4 + 8 + 4 = 16.

## Phase 4 — Production runs

Single end-to-end `surg-analyze` invocation with production resolution
(`n_boot=200` for all bootstraps; LOO at full `n_exc` per threshold).

### Compute cost estimate

Rough bounds based on Spec B's ~50 min wall on full panel:

- **`gpd_components`** — 3 components × 7 pnodes × 3 thresholds × 200
  bootstrap reps × 2 half-fits each ≈ 25,000 GPD MLE fits at <0.5s
  each → **~3 hours**.
- **`year_fe_diagnostic`** — 7 pnodes × 3 taus × 200 bootstrap reps ×
  2 specs (primary + year_fe) per Layer 3 rep ≈ 8,400 QR fits at <1s
  each → **~2.5 hours**.
- **`ashburn_diagnostic` LOO** — 2 pnodes × 4 thresholds with n_exc
  varying:
  - p99.5 (n_exc ≈ 80): 160 LOO fits → ~3 min.
  - p99 (n_exc ≈ 175): 350 LOO fits → ~6 min.
  - p95 (n_exc ≈ 800): 1600 LOO fits → ~30 min.
  - p90 (n_exc ≈ 1700): 3400 LOO fits → ~1 hour.
  Total: **~1.5-2 hours**.
- Scatter figure render: <1 min.

**Total estimate: 7-8 hours of compute.** Resumable per output file
(each module writes its own output dir, skip flags allow per-step
re-invocation).

### Runs to perform

One full-coverage run with seed=0, n_boot=200. If any module emits
an `insufficient_sample` (Rule 4) or `failed` status, debug and
re-run that module only.

## Phase 5 — Application entries (`docs/decisions.md`)

Three entries, written after Phase 4 outputs are complete:

### 5.1 — Item #2 application entry

> **"2026-05-XX — Application of #2 pre-reg: LMP-components decomposition verdict"**

Contains:

- Headline result (numeric values from
  `outputs/gpd_components/headline.json`).
- Rule 2 outcome dispatch (one of the four / fifth-case rows).
- Paper-claim sentence per the locked table.
- Supplementary section: primary-cluster congestion + marginal_loss;
  cross-pnode summary; threshold sweep summary.
- Implication for sub-question 1: how this changes (or doesn't) the
  conditional-Z verdict's mechanism interpretation.
- Implication for the paper: which version of the mechanism story is
  now supported.

### 5.2 — Item #3 application entry

> **"2026-05-XX — Sub-q1 item #3: τ=0.99 secular sign-flip diagnostic (descriptive)"**

Contains:

- Layer 1 summary: raw per-year p99 LMP trajectory across pnodes
  (table or compact prose).
- Layer 2 summary: year-dummy CIs (explicitly labeled as per-year
  level shifts, not a trend test).
- Layer 3 summary: secular-component bootstrap at τ=0.99 — point +
  CI; explicitly framed as the trend test for the "downward at
  τ=0.99" claim.
- Interpretation: which of (a) real grid improvement, (b) sparse-
  tail artifact, (c) window-specific noise the evidence supports.
- Implication for sub-question 2 (JLARC projection): which z_slope
  to use at τ=0.99 (primary vs year-FE).

### 5.3 — Item #4 application entry

> **"2026-05-XX — Sub-q1 item #4: Ashburn TX1 99th-pct anomaly diagnostic (descriptive)"**

Contains:

- LOO summary at 99th-pct for TX1: full-sample β₁ vs LOO distribution;
  top-5 most-influential exceedances; whether dropping any single
  exceedance flips the sign.
- TX2 cross-check at 99th-pct (and across all 4 thresholds).
- Direction agreement / disagreement between TX1 and TX2 at each
  threshold.
- Reference to the 4-panel scatter figure
  (`outputs/ashburn_diagnostic/scatter_overlay.png`).
- Interpretation: which of (a) real distribution-side physics, (b)
  power-driven over-fit, (c) data-quality issue the evidence
  supports.
- Implication for the paper: methodology footnote framing for
  Ashburn TX1's anomaly.

## Phase 6 — Sub-q1 closure roadmap update

Edit `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`:

- Items #2/#3/#4 marked **DONE** with commit SHAs + links to the
  three application entries.
- Item #5 (advisor meeting) becomes the only open item.
- Top-of-document status line updated to reflect "items 2-4 closed;
  sub-q1 substantially closed pending advisor #5."
- JLARC plan-writing gate state restated (gated on item #5).

## Sub-q1 closure semantics after this plan

After Phase 6: sub-q1 is **substantially closed**. All four
empirical / methodological items (#1-#4) have committed decisions.md
entries. The remaining item #5 (advisor meeting) requires no further
code; it produces framing sign-off and triggers JLARC plan-writing
activation per the 2026-05-14 locked decisions.

"Substantially closed" mirrors the language used after Spec B
(2026-05-14) and is the bar the roadmap defined as
"paper-publishable confidence" pending advisor sign-off.

## Git workflow

Matches recent practice (Spec B and conditional-Z battery):

- Sibling worktree at
  `~/docs/NU/Freshman_Year/Summer_2026/SURG/surg-sub-q1-diag/`
  (or similar) created via `using-git-worktrees`.
- Feature branch named `feature/sub-q1-batched-diagnostics`.
- Each commit is its own ask per CLAUDE.md.
- No push to origin until explicitly authorized.
- FF merge back to `main` when the plan completes; branch deleted;
  worktree removed.
- Commit messages follow existing conventions; no AI / Claude
  attribution.

## Compute cost estimate (summary)

- Phase 1 (preprocessing rebuild): sub-minute.
- Phase 4 (production runs): 7-8 hours total compute.
- All other phases: development time, not compute.

## Out of scope (restated)

- Sub-q1 closure item #5 (advisor meeting) — separate work track.
- JLARC projection (sub-q2) — plan-writing gated on item #5.
- Paper-figure generation beyond the diagnostic scatter required by
  item #4.
- Ashburn LOAD historic backfill.
- Refactors to the orchestrator's pnode looping pattern (single-
  pass-per-pnode vs. batch-on-component).
- Additional Z variables (SR clearing price as Z, etc.) — separate
  question.

## Open implementation choices (deferred to writing-plans)

- **Resumability granularity.** Per-output-file caching (current
  design) vs. per-pnode caching vs. per-test caching. Per-output-
  file is simplest and matches the existing pattern; the writing-
  plans task can decide on per-test granularity if needed for LOO
  re-runs.
- **Bootstrap seed scheme.** Spec B uses `seed + 10*i` per index;
  consistency suggests we follow that, but any deterministic scheme
  is acceptable.
- **PNODE_TO_RESPONSE_COL mapping** for `year_fe_diagnostic` — where
  does this dictionary live? Could be a `constants.py` module or
  inlined in `run.py`. Writing-plans decides.
