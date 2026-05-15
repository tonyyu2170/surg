# Design — Direct Z → LMP Tail-Risk Characterization (Sub-Q1 Item #6)

> **Status:** Drafted 2026-05-14 night via the superpowers brainstorming
> skill. Pre-registers the design choices before any code is written.
> This document **IS the pre-reg** for item #6 per the "light pre-reg"
> decision agreed during brainstorming (see [Pre-reg discipline](#pre-reg-discipline)
> below).
>
> Implementation plan will be drafted next via the writing-plans skill
> and committed as `docs/plans/2026-05-14-z-lmp-tail-risk-characterization-implementation.md`.

## Purpose

Produce the **direct empirical answer** to the user's sub-q1 framing —
*"what range of load variance (Z) causes LMP to essentially go crazy"* —
via a binned exceedance-probability characterization of the conditional
Z → LMP distribution.

Items #1–4 in the sub-q1 closure roadmap (Spec B continuous ξ(Z), LMP
components decomposition, τ=0.99 secular sign-flip, Ashburn TX1
anomaly) are **mechanism tests** — they test *why* LMP gets crazy at
high Z. They imply the descriptive answer (e.g., positive z_slope @
τ=0.95 → higher conditional 95th-pct LMP at higher Z) but do not
directly produce a clean *"Z in range [a, b] makes LMP cross $X with
probability P"* artifact. Item #6 fills that gap.

The mechanism work in items #1–4 stays as supporting evidence in any
paper — not replaced. Item #6 adds the descriptive headline figure.

## Sub-q1 closure context

| Roadmap item | What it answers | Status |
|---|---|---|
| #1 Spec B continuous ξ(Z) | Is the median-split rejection robust to a continuous fit? | DONE (`fe2cb94`) |
| #2 LMP-components decomp | Does the cancellation hypothesis hold? | DONE (`01ebbd8`) |
| #3 τ=0.99 secular sign-flip | Is the τ=0.99 sign flip case (a/b/c)? | DONE (`72456bb`) |
| #4 Ashburn TX1 q=0.99 anomaly | Is the q=0.99 sign flip outlier-driven? | DONE (`fd0065c`) |
| **#6 Direct Z → LMP tail-risk** (**this design**) | **What range of Z makes LMP cross $X with what probability?** | **Pending implementation** |
| #5 Advisor meeting | Paper-framing sign-off | Open; gated on #6 |

Item #6 is sequenced **before** item #5 so the advisor sees mechanism
+ descriptive characterization together.

## Pre-registered design choices

This section locks the design before implementation runs. Each choice
was discussed during brainstorming and approved by the user.

### 1. Crazy metric: exceedance probability

For each (Z bin, $-threshold) cell, compute **P(LMP > $threshold | Z
bin)** with a 95% confidence interval. The headline output is a line
chart with one curve per $-threshold, showing how exceedance
probability varies across Z bins.

Why this metric (vs conditional quantile, GPD shape, or tail
expectation): exceedance probability is the most communicable to
non-technical audiences ("at this Z range, $500+ events happen X% of
the time") and most directly answers the user's stated framing. The
existing GPD / Spec B / median-split work already covers the
heavier-tailedness angle.

### 2. Response variables: total_lmp + congestion, side-by-side

Two response variables, presented as side-by-side panels per pnode:

- **`total_lmp_*_cluster_mean`** — primary; the price ratepayers
  actually pay; baseline ~$30–50.
- **`congestion_price_*_cluster_mean`** — secondary; the
  volatility-isolated component (the proposal's stated variable);
  baseline ~$0–5.

`system_energy` and `marginal_loss` decomposition is NOT included —
covered by item #2's components decomposition. The side-by-side total
+ congestion shows both the policy-relevant signal and the
mechanism-isolated signal in one figure.

### 3. $ thresholds: graduated set with percentile annotations

Five thresholds, same for both response variables: **$100, $250,
$500, $1000, $2000**. Each threshold is **annotated with its empirical
percentile** in the filtered panel, e.g., "$500 (p99 total_lmp / p99.5
congestion)". This gives both concrete $ values (communicable) and
statistical interpretability (rigorous).

The asymmetry between variables (e.g., $500 is p99 on total_lmp but
p99.5 on congestion) is itself informative — shows that total_lmp's
$500 events have a system_energy component, not pure congestion.

### 4. Z binning: equal-count deciles with MW/min edge labels

10 equal-count quantile bins of Z (~900 obs per bin after
proposal-filter). Bin edges in MW/min are reported alongside the
decile index (e.g., "decile 9: Z ∈ [4.2, 7.8] MW/min, n=896").

Why deciles (vs equal-width MW/min vs custom): Z is heavily
right-skewed; equal-width bins would put 80% of observations in the
first 2–3 bins and have very few obs at the tail. Quantile bins
distribute evenly. Labeling edges in MW/min preserves the physical
interpretation.

### 5. Pnode scope: primary + DOM zonal + Ashburn + cross-pnode summary

Four pnodes get full per-pnode JSON + PNG output:

- **`primary` (Loudoun cluster mean)** — headline; the DC-adjacent
  cluster.
- **`dom_zonal` (DOM zonal aggregate)** — comparison; "is the
  cluster more sensitive than the zone average?"
- **`ashburn_tx1` (35 kV LOAD subtype)** — bridges to item #4's
  anomaly via the descriptive lens.
- **`ashburn_tx2` (35 kV LOAD subtype)** — same.

All 7 pnodes (`primary`, `total_lmp`, `ox`, `bristers`, `dom_zonal`,
`ashburn_tx1`, `ashburn_tx2`) appear in a **cross-pnode summary
table** (top-decile-only summary; one row per pnode), but only the
four above get full per-pnode plots.

### 6. Filter: proposal-filter only

Apply `passes_proposal_filter == True` (shoulder seasons Mar–May +
Sep–Nov, 2–5 AM window) for all computations. Matches the filter used
in items #1–4. Sample: ~9,000 obs across the 3.6y panel.

Why filtered (vs raw or both): consistency with prior mechanism work.
The filter is designed to isolate the volatility signal from
supply-side spikes. A raw view will eventually be done in sub-q3
(event correlation), which has explicit event flags. Item #6 doesn't
need to duplicate.

### 7. Pre-reg discipline: this design doc

This document is the pre-reg. No separate `decisions.md` entry needed
pre-run; an *application entry* will be written post-run to record the
verdict (matching the items #1–4 pattern). The application entry will
NOT have a Rule-2-style decision table — item #6 is descriptive, not
confirmatory.

The discipline prevents post-hoc "the cliff is at decile X" framing if
we eyeball the chart and find a visually convenient cutoff. Whatever
the chart shows is what gets reported.

## Architecture & integration

**New module:** `src/surg/analysis/tail_risk_curves.py` (~250 lines).
Follows the same pattern as `gpd_components.py`,
`year_fe_diagnostic.py`, `ashburn_diagnostic.py` from items #2–4.

**Orchestrator integration:** wired into `src/surg/analysis/run.py`
as a new step after `run_ashburn_diagnostic`. CLI:

```bash
surg-analyze ... --tail-risk-n-boot 200 [--skip-tail-risk-curves] [--tail-risk-loo-skip]
```

- `--tail-risk-n-boot` (default 200): pair-bootstrap reps for the CI.
- `--skip-tail-risk-curves`: skip the entire orchestrator step.
- `--tail-risk-loo-skip` (soft idempotency): skip per-pnode work
  if the output JSON already exists.

**Library deps:** numpy, pandas, scipy.stats (for
`percentileofscore`), matplotlib (for PNGs). All already in the
project.

**CI method:** pair-bootstrap (n=200), NOT Wilson interval. Rationale:
hourly data has temporal autocorrelation (load patterns persist
hour-to-hour; weather autocorrelates), so Wilson's iid binomial
assumption underestimates true variance. Pair-bootstrap (resample
(Z, response) pairs with replacement within the filtered panel)
matches the discipline used in items #1–4. Cost: <1 min for 200 reps
× ~400 cells × counting operation.

## Outputs

Directory: `outputs/tail_risk_curves/` (gitignored, matches existing
output pattern).

| File | Content |
|---|---|
| `primary.json` | 10 deciles × 5 thresholds × 2 response vars × {p_hat, n_exc, n_total, ci_low, ci_high, threshold_percentile}. Plus decile MW/min edges + decile_n_obs. |
| `dom_zonal.json` | Same structure as primary. |
| `ashburn_tx1.json` | Same structure. |
| `ashburn_tx2.json` | Same structure. |
| `cross_pnode_summary.json` | All 7 pnodes × top-decile-only × 5 thresholds × 2 response vars × {point, CI}. Compact comparison. |
| `cross_pnode_summary.csv` | Tabular view: rows = pnodes, columns = (threshold × response_var) at top decile. Easy paper-table import. |
| `primary.png` | 2-panel chart (total_lmp \| congestion). |
| `dom_zonal.png` | Same layout. |
| `ashburn_tx1.png` | Same layout. |
| `ashburn_tx2.png` | Same layout. |

### Chart specifications (per pnode PNG)

- **Layout:** 1 row × 2 columns. Left panel = total_lmp; right panel =
  congestion. Shared y-axis range across the two panels for the same
  pnode (so reader can visually compare magnitude differences).
- **X-axis:** decile index 1–10 (numeric); MW/min range labels
  underneath each tick (e.g., "1\n[0.0, 0.3]" for decile 1).
- **Y-axis:** P(LMP > $threshold), 0–1 range (probably capped at 0.5
  if no curve exceeds; auto-fit).
- **Lines:** 5 curves per panel, one per $-threshold ($100, $250,
  $500, $1000, $2000). Graduated color (viridis or similar); higher
  $-threshold = darker / heavier line weight.
- **CI bands:** shaded ribbon around each line (pair-bootstrap 95%).
- **Title:** `{pnode_label}: P(LMP > $X) by Z decile (proposal-filter, n_boot=200, hourly)`
- **Legend:** `$500 (p99 total_lmp)` style — both $ and percentile.

### JSON schema (per pnode)

```json
{
  "pnode_label": "primary",
  "response_cols": {
    "total_lmp": "total_lmp_rt_cluster_mean",
    "congestion": "congestion_price_rt_cluster_mean"
  },
  "z_col": "dom_load_gradient_abs_mw_per_min",
  "filter": "passes_proposal_filter == True",
  "n_total_filtered": 8993,
  "n_boot": 200,
  "thresholds": [100, 250, 500, 1000, 2000],
  "threshold_percentiles": {
    "total_lmp": {"100": 0.853, "250": 0.962, "500": 0.989, "1000": 0.997, "2000": 0.999},
    "congestion": {"100": 0.943, "250": 0.984, "500": 0.995, "1000": 0.998, "2000": 0.9995}
  },
  "decile_edges_mw_per_min": [0.0, 0.3, 0.6, 1.1, 1.7, 2.4, 3.2, 4.2, 5.5, 7.8, 21.4],
  "decile_n_obs": [899, 900, 899, 900, 900, 899, 900, 899, 900, 897],
  "results": {
    "total_lmp": [
      {
        "decile": 1,
        "z_range_mw_per_min": [0.0, 0.3],
        "n_total": 899,
        "by_threshold": {
          "100": {"p_hat": 0.012, "n_exc": 11, "ci_95": [0.005, 0.020]},
          "250": {"p_hat": 0.003, "n_exc": 3, "ci_95": [0.000, 0.009]},
          "500": {"p_hat": 0.000, "n_exc": 0, "ci_95": [0.000, 0.004]},
          "1000": {"p_hat": 0.000, "n_exc": 0, "ci_95": [0.000, 0.004]},
          "2000": {"p_hat": 0.000, "n_exc": 0, "ci_95": [0.000, 0.004]}
        }
      },
      ... 9 more deciles
    ],
    "congestion": [ ... 10 deciles ... ]
  }
}
```

### Cross-pnode summary schema

```json
{
  "n_boot": 200,
  "thresholds": [100, 250, 500, 1000, 2000],
  "scope": "top_decile_only",
  "pnodes": [
    {
      "pnode_label": "primary",
      "z_range_top_decile_mw_per_min": [7.8, 21.4],
      "n_top_decile": 897,
      "results": {
        "total_lmp": {
          "100": {"p_hat": 0.45, "ci_95": [0.42, 0.48]},
          ...
        },
        "congestion": { ... }
      }
    },
    ... 6 more pnodes
  ]
}
```

## Implementation components

| Function | Purpose |
|---|---|
| `compute_z_deciles(panel, z_col) → (edges, bin_indices)` | Single source of truth for the 10 decile edges. |
| `compute_threshold_percentiles(panel, response_col, thresholds) → dict[threshold, pct]` | Maps each $ threshold to its empirical percentile (for annotation). |
| `compute_exceedance_probability_with_ci(panel, response_col, threshold, z_bin_mask, n_boot=200) → (p_hat, n_exc, n_total, ci_low, ci_high)` | Core stat with pair-bootstrap CI. |
| `run_pnode_tail_risk_curves(panel, pnode_label, response_cols, thresholds, n_deciles=10, n_boot=200) → dict` | Per-pnode orchestrator. Builds JSON-ready dict. |
| `plot_tail_risk_curves(per_pnode_dict, out_path) → None` | Visualization. matplotlib, 1×2 panel layout, CI shading. |
| `aggregate_cross_pnode_summary(per_pnode_results) → dict` | Cross-pnode top-decile-only summary. |
| `run_tail_risk_curves(panel, data_root, out_root, **kwargs) → None` | Top-level orchestrator called from `run.py`. |

## Error handling

| Edge case | Behavior |
|---|---|
| Empty Z decile (n=0) | Shouldn't happen with quantile binning, but defensive: emit warning, fill cell with `null`, mark `decile_n_obs: 0`. |
| Empty exceedance set in a cell (n_exc=0) | Report `p_hat=0.0`. CI lower bound = 0; upper bound = Wilson exact for n_exc=0 (bootstrap struggles at this boundary). |
| Insufficient bin sample (decile total n < 30) | Flag JSON cell `n_below_inference_floor: True`. Report point estimate anyway; do NOT suppress. |
| Missing data in response or Z | Drop rows pre-binning; log count of dropped rows in the per-pnode JSON `n_dropped_na`. |
| Bootstrap degenerate (zero-variance bin) | Catch + report `convergence_status: "degenerate_bin"`; use empirical (non-bootstrap) point estimate. CI = `[null, null]`. |
| Threshold above max LMP in panel | n_exc=0 everywhere; the chart shows a flat zero line for that threshold. Informative (it tells the reader "this threshold is never reached in our panel"). |

## Testing

`tests/analysis/test_tail_risk_curves.py`:

### Unit tests

- **`compute_z_deciles`:** matches `numpy.percentile([10, 20, ..., 90])` on synthetic data; output has 11 edges (10 bins); bin_indices in [0, 9].
- **`compute_threshold_percentiles`:** matches `scipy.stats.percentileofscore` for known thresholds.
- **`compute_exceedance_probability_with_ci`:** point estimate is `sum(response > threshold) / n_total`; bootstrap CI for high-n bin (n=500) is within 10% relative tolerance of Wilson reference (validates bootstrap implementation).
- **Boundary case — n_exc=0:** function returns `p_hat=0.0`, CI lower bound `0.0`, upper bound matches Wilson exact for `(0, n)`.
- **Boundary case — n_exc=n_total:** function returns `p_hat=1.0`, similar mirror.

### Integration smoke test

- Fixture panel: 100 rows × 5 deciles × 2 response cols (synthetic, deterministic).
- Run `run_pnode_tail_risk_curves` on the fixture.
- Verify output JSON schema matches expected fields (`decile_edges_mw_per_min`, `threshold_percentiles`, `results[*].by_threshold[*].p_hat`, etc.).
- Verify PNG file is created and non-empty.

### End-to-end test

- Fixture panel covering 4 pnodes × 100 rows.
- Run `run_tail_risk_curves` with `n_boot=5` (fast).
- Verify: 4 per-pnode JSONs created, 4 PNGs created, 1 cross-pnode summary JSON + CSV created.
- Verify `cross_pnode_summary.json` contains all 4 pnodes' top-decile results.

## Effort estimate

- **Implementation:** ~250 lines of code (mirrors `gpd_components.py` length).
- **Tests:** ~150 lines.
- **Plot tuning:** ~1 hour (matplotlib layout iteration).
- **Total dev time:** ~4–6 hours, single session.
- **Production run wall time:** <5 minutes (much faster than items #1–4
  which involved expensive GPD MLE bootstraps; item #6 is just
  exceedance counting + percentile lookups).
- **Application entry writing:** ~1 hour after the production run
  produces outputs.

## Sequencing within sub-q1 closure

Item #6 fits between items #4 and #5 (advisor meeting) in the closure
roadmap. Concrete order:

1. **This brainstorm + design doc** (current step; complete after user
   reviews this spec).
2. **Implementation plan** (writing-plans skill next).
3. **Implementation** (subagent-driven-development skill or direct
   coding with TDD).
4. **Production run + application entry**.
5. **FF merge + push** (standard branch lifecycle).
6. **Item #7: 5-min data exploration** (separate scope, brainstorm
   later).
7. **Item #5: Advisor meeting** (agenda updated with #6 + #7 findings).

## Open questions / Revisit when

- **Item #7 scope.** User indicated they want to "look at the 5-min
  data more" pre-advisor. This is a NEW item to brainstorm
  separately; the 5-min path may inform item #6's filter choices in
  retrospect (e.g., if 5-min Z distributions look qualitatively
  different, item #6 may want a 5-min companion run).
- **What if all 4 per-pnode charts look identical?** Then the
  cross-pnode comparison is uninteresting and the headline
  collapses to the primary chart. The cross-pnode summary table
  still gets shipped as supporting evidence.
- **What if no curve crosses 25% probability at any Z decile?** Then
  "LMP goes crazy" doesn't have a clear binary threshold even at
  high Z — the answer is "exceedance probability increases
  monotonically with Z but stays below 25% everywhere." Still a
  valid empirical answer; the chart shows the gradient.
- **Multiple-testing posture.** Item #6 reports many (decile ×
  threshold × pnode × response_var) cells = ~400. None gets an
  α=0.05 verdict; all are descriptive. Matches Rule 5 of item #2
  pre-reg. No family-wise correction.

## Revisit when

- Production output deviates qualitatively from expectations (e.g.,
  pattern is non-monotonic in Z).
- Advisor input materially shifts framing (item #6 may be
  reframed post-meeting).
- Item #7 (5-min) surfaces findings that affect item #6
  interpretation.
- A longer historical window enables finer Z binning (currently 10
  deciles × 9,000 obs = 900/bin; finer binning would dilute n/bin).
