# Spec B — Continuous ξ(Z) Regression Design Spec

> **Status:** Drafted 2026-05-14 via brainstorming skill, all design
> decisions confirmed with the user in-session. User to review the
> written spec before plan-writing begins.

## Goal

Close the central remaining gap in sub-question 1 ("where does the
response shift") by fitting a **non-stationary Generalized Pareto
Distribution** with the load-volatility variable Z as a covariate on
both the scale and shape parameters. This is the explicit follow-up
triggered by the 2026-05-14 conditional-Z robustness battery's pre-reg
(Spec A returned non-monotone ξ trajectory on both batteries).

The spec produces:
- A **headline scalar** (β₁ slope of ξ on Z under a linear form) with
  bootstrap CI and two-sided p-value, on the primary response
  (congestion, the proposal's stated variable) at the 95th-pct LMP
  threshold. This is the *single paper claim* answering sub-q1's
  conditional-Z mechanism question.
- A **shape characterization** (3-knot natural cubic spline fit of
  ξ(Z)) with per-Z-grid bootstrap bands, allowing the paper to
  distinguish "linear-in-Z" from "non-monotone smooth structure."
- **Cross-pnode descriptive supplementary** (all 7 pnodes) and
  **threshold sweep** (90/95/99/99.5) to support the headline.

## Non-goals (explicit out-of-scope)

- **Multiple-testing correction across pnodes/thresholds.** Headline
  is singular (primary × 95th-pct × linear); all other tests are
  descriptive. No Bonferroni / Holm correction is applied to the
  larger family. Pre-committed in the headline-only design choice.
- **Stationary GPD re-fit.** The existing `gpd_threshold_sweep` and
  `gpd_conditional_on_z` cover stationary fits; Spec B is strictly
  the non-stationary extension.
- **Block-bootstrap or temporal-autocorrelation correction.** Pair-
  bootstrap on exceedance row indices, matching existing convention.
  If reviewers push back, a follow-up plan adds a block-bootstrap
  variant.
- **Profile-likelihood CIs.** Bootstrap-only; profile-likelihood is
  a deferred robustness check.
- **GAM / penalized smoothing splines.** The natural cubic spline at
  3 knots (4 DOF total) is the chosen flexibility level. A smoother
  GAM would auto-select the smoothing parameter — not done here.
- **Spec A re-execution at different quantiles.** Spec B replaces
  Spec A's discrete-split with a continuous fit; the discrete output
  remains the existing `outputs/gpd/conditional_z_robustness*.json`.
- **Implementation of the JLARC projection layer or any sub-q2 work.**
  Sub-q2 is on its own track per the existing JLARC design doc.

## Statistical model

The non-stationary GPD per Davison & Smith (1990, *JRSS-B*), Coles
(2001) §6.3 conventions:

For exceedances Y_i > threshold T (with i indexing exceedance row),
let Z_i be the corresponding load-gradient observation. The
exceedance Y_i - T is modeled as:

```
(Y_i - T) | Z_i ~ GPD(σ(Z_i), ξ(Z_i))
```

with:

```
log σ(Z) = σ₀ + σ₁ · Z           (log-link, ensures σ > 0)
ξ(Z)     = β₀ + β₁ · Z           (linear form — primary)
ξ(Z)     = β₀ + Σⱼ βⱼ · Bⱼ(Z)   (spline form — characterization)
```

where Bⱼ are basis functions for a natural cubic spline with 3
internal knots placed at empirical Z quantiles (33rd / 50th / 67th
of Z within exceedance set). The spline has 4 DOF for the ξ curve
(intercept + 3 knot effects via natural cubic spline boundary
constraints).

**Log-likelihood (negative, for minimization):**

```
ℓ(σ₀, σ₁, β...) = Σᵢ [ log σ(Zᵢ) + (1 + 1/ξ(Zᵢ)) · log(1 + ξ(Zᵢ) · (Yᵢ-T)/σ(Zᵢ)) ]
```

(with the edge case ξ(Zᵢ) → 0 handled via the exponential limit.)

**MLE via** `scipy.optimize.minimize` with BFGS, gradient-free fallback
(Nelder-Mead) for failed convergence. Initial values:
- σ₀ = log(σ_const) from stationary `fit_gpd` on the same exceedance set
- σ₁ = 0
- β₀ = ξ_const from stationary `fit_gpd`
- β₁ = 0 (or spline coefficients = 0 for spline form)

**Likelihood ratio test** (spline vs linear nested test): LRT
statistic = 2·(ℓ_linear - ℓ_spline) ~ χ²_3 asymptotically (DOF =
spline_DOF − linear_DOF = 4 − 2 = 2; note: there's a subtle issue
with non-stationarity at the boundary of regularity that may make the
asymptotic χ² approximation imprecise — the bootstrap p-value is the
load-bearing inference).

## Pnode + threshold scope

**Pnodes (all 7, matches PNODE_RESPONSES):**
- `primary` (Loudoun cluster congestion) — **headline pnode**
- `total_lmp` (Loudoun cluster total LMP)
- `ox`, `bristers`, `dom_zonal` (negative controls)
- `ashburn_tx1`, `ashburn_tx2` (distribution-side)

**Thresholds (full sweep, 4 quantiles):**
- 0.90 (≈n=3,154 exceedances per pnode at full panel)
- 0.95 (≈n=1,577) — **headline threshold**
- 0.99 (≈n=316)
- 0.995 (≈n=158)

**Headline:** primary @ 95th-pct, linear form, β₁ + bootstrap CI.
**Supplementary:** everything else descriptively, without family-wise
inferential correction.

**Known limitation:** at 99.5th-pct (n≈158), fitting a 4-DOF spline
plus 200 bootstrap reps is power-limited. Convergence failures
expected; pre-commit to reporting `convergence_status` per fit. Do
not retry or drop reps post-hoc.

## Bootstrap protocol

Pair-bootstrap, n_boot = 200, seed = 0 (matches existing battery).

For each rep:
1. Resample exceedance row indices with replacement (size = original n).
2. Refit the non-stationary GPD MLE on the resampled (Y, Z) pairs.
3. Record the headline statistic (β₁ for linear; per-Z-grid evaluation
   of ξ̂(Z) for spline; LRT statistic for spline-vs-linear).

Failed-convergence reps (BFGS + Nelder-Mead both fail) are recorded
and excluded from the CI calculation. If fewer than 100 successful
reps remain, the CI is reported as `(NaN, NaN)` and
`convergence_status: "insufficient_bootstrap_reps"`.

Two-sided p-value: `p = 2 × min(P(β₁ ≤ 0), P(β₁ ≥ 0))`, clipped to
[0, 1]. Matches the existing battery's "achieved significance level"
convention. Documented in the per-pnode output JSON.

## Decision rules — paper claim table

For the headline (primary @ 95th-pct, linear form):

| β₁ point estimate | β₁ bootstrap CI | LRT spline-vs-linear | Paper claim |
|---|---|---|---|
| < 0 | excludes 0 (upper bound < 0) | not significant | "Continuous fit confirms median-split direction. ξ decreases with Z at rate β₁ = [value], bootstrap CI [...]." |
| < 0 | excludes 0 | significant (p < 0.05) | "Continuous fit confirms direction (β₁ < 0) but shape is non-linear. Spline characterization shows [pattern]." |
| > 0 | excludes 0 | n/a | "Continuous fit CONTRADICTS median-split direction. Median-split rejection was scope-specific; paper headline reframes." |
| spans 0 | n/a | n/a | "Continuous fit is underpowered on this window. Median-split's rejection at 95th-pct is the strongest evidence the data supports; Spec B does not sharpen the conclusion." |

These rules are **pre-committed in a decisions.md entry BEFORE Spec B
fits run** (matches the conditional-Z battery's pre-reg discipline).

## Output schema

### Per-pnode file: `outputs/gpd_continuous/<pnode>.json`

```json
{
  "pnode_label": "primary",
  "response_col": "congestion_price_rt_cluster_mean",
  "threshold_col": "dom_load_gradient_abs_mw_per_min",
  "n_total_panel": 31536,
  "n_after_dropna": 31536,
  "threshold_sweep": [
    {
      "threshold_quantile": 0.90,
      "threshold_value": 12.35,
      "n_exceedances": 3154,
      "linear": {
        "convergence_status": "converged",
        "shape_coefficients": [0.95, -0.012],
        "shape_coefficients_bootstrap_ci_95": [[0.84, 1.04], [-0.024, -0.001]],
        "scale_coefficients": [2.1, 0.08],
        "scale_coefficients_bootstrap_ci_95": [[2.0, 2.2], [0.05, 0.11]],
        "beta_1_two_sided_p_value": 0.04
      },
      "spline": {
        "convergence_status": "converged",
        "shape_coefficients": [0.95, -0.005, -0.030, 0.020],
        "shape_coefficients_bootstrap_ci_95": [[...], [...], [...], [...]],
        "scale_coefficients": [2.1, 0.08],
        "scale_coefficients_bootstrap_ci_95": [...],
        "xi_curve_z_grid": [1.0, 2.0, ..., 30.0],
        "xi_curve_central": [...],
        "xi_curve_ci_lower": [...],
        "xi_curve_ci_upper": [...]
      },
      "likelihood_ratio_test": {
        "chi2": 4.7,
        "df": 2,
        "asymptotic_p_value": 0.095,
        "bootstrap_p_value": 0.12
      }
    },
    {"threshold_quantile": 0.95, ...},
    {"threshold_quantile": 0.99, ...},
    {"threshold_quantile": 0.995, ...}
  ]
}
```

### Headline file: `outputs/gpd_continuous/headline.json`

```json
{
  "test": "spec_b_primary_95th_linear",
  "response_col": "congestion_price_rt_cluster_mean",
  "pnode_label": "primary",
  "threshold_quantile": 0.95,
  "form": "linear",
  "beta_1": -0.012,
  "beta_1_bootstrap_ci_95": [-0.024, -0.001],
  "beta_1_two_sided_p_value": 0.04,
  "decision_rule_outcome": "rejection_confirmed_linear",
  "pre_reg_reference": "docs/decisions.md § 2026-05-14 Spec B pre-registration"
}
```

## Architecture — module structure

New module `src/surg/analysis/gpd_continuous.py` (separate from
`gpd.py` which is at ~857 lines):

```
src/surg/analysis/gpd_continuous.py:
  - GPDContinuousFitResult         (frozen+slots dataclass)
  - _basis_for_spline(Z, n_knots)  (natural cubic spline basis matrix)
  - _neg_log_likelihood(params, Y_exc, Z_exc, X_sigma, X_xi)
  - _initial_params(Y_exc, form, n_knots)
  - fit_gpd_continuous_z(Y, Z, *, threshold, form, n_boot, seed)
  - _likelihood_ratio_test(linear_result, spline_result)
  - run_gpd_continuous_z(panel, out_path, *, response_col, pnode_label, ...)
```

Wiring into `src/surg/analysis/run.py`:
- New CLI flag: `--continuous-n-boot` (default 200)
- New loop after existing per-pnode GPD loop:
  ```python
  for label, col in PNODE_RESPONSES.items():
      if panel[col].dropna().empty:
          continue
      run_gpd_continuous_z(
          panel=panel,
          out_path=out_root / "gpd_continuous" / f"{label}.json",
          response_col=col,
          pnode_label=label,
          n_boot=continuous_n_boot,
      )
  ```
- Final orchestrator call emits the headline JSON.

## Test design

`tests/analysis/test_gpd_continuous.py` mirrors the conditional-Z
battery's pattern:

1. **Recovery test (linear form).** Plant a known DGP with `ξ(Z) = β₀
   + β₁·Z`, simulate, fit, recover β₀ and β₁ within tolerance
   `±2/√n_boot`.
2. **Null test (β₁ = 0 DGP).** Plant constant-ξ DGP, fit, confirm β₁
   bootstrap CI spans 0 and two-sided p > 0.10.
3. **Spline recovery test.** Plant a non-monotone ξ(Z) curve (e.g.,
   inverse-U), fit spline form, confirm the spline's per-Z-grid
   evaluation matches the planted curve at coarse grid.
4. **LRT power test.** With planted non-monotone DGP, confirm LRT
   bootstrap p < 0.10 against linear null model.
5. **Convergence failure handling.** Construct an exceedance set
   small enough to force MLE failure; confirm
   `convergence_status: "failed"` is reported without crashing.
6. **Output JSON schema test.** End-to-end run on synthetic panel
   produces a JSON file with the expected schema (matching the
   per-pnode output above).
7. **Integration test.** `run_all` with `continuous_n_boot=30` on
   synthetic panel produces both per-pnode files and the headline
   file at the expected paths.

Existing 190 test count → 197 (7 new tests). All passing required.

## Pre-reg discipline

Spec B follows the same pre-reg → implement → apply pattern as the
conditional-Z battery:

1. **Pre-reg entry** in `docs/decisions.md` BEFORE any Spec B fits
   run — locks the headline decision rule and the paper-claim table
   above. Title: `2026-05-14 — Pre-registration: Spec B continuous
   ξ(Z) regression (follow-up from conditional-Z battery)`.
2. **Implementation plan** at
   `docs/plans/2026-05-14-spec-b-continuous-xi-z-implementation.md`
   — verbatim test + impl tasks for subagent-driven-development.
3. **Application-of-pre-reg entry** in `decisions.md` AFTER fits run
   — applies the decision rule to actual β₁ and writes the paper
   verdict.

## Implementation effort estimate

- This brainstorm doc → spec commit: 30 min ✓
- Pre-reg decisions.md entry: 30 min
- Implementation plan: 1-2 hr
- Subagent execution: ~6-9 hr wall (4-5 implementer tasks + reviews,
  matches Strategy C / conditional-Z cadence)
- Production run on full panel: ~3 hr wall (sweep × pnodes × bootstrap)
- Application entry write + commit + FF-merge: 1 hr
- **Total: 2-3 focused sessions** (similar to conditional-Z battery's
  cadence)

## Open implementation questions to resolve in the plan

These are tactical decisions deferred to plan-writing, not
load-bearing for the design:

1. **MLE initial value strategy** — if BFGS fails, fallback to
   Nelder-Mead; if both fail, mark `convergence_status: "failed"`
   and continue. Pre-commit no parameter restart loop.
2. **Knot placement for spline** — empirical quantiles (33/50/67) of
   Z within exceedance set, recomputed inside each bootstrap rep.
3. **Z-grid for spline curve evaluation** — 50-point linspace over
   [Z_min, Z_max] of the full panel, fixed across pnodes and reps.
4. **Numerical safeguards** — if `σ(Z) < 1e-6` or `(1 + ξ(Z) · u/σ(Z)) ≤ 0`
   for any exceedance, log-likelihood returns inf (MLE rejects). No
   adhoc clipping or transformation.

## Implementation plan reference

Implementation plan to be written at
`docs/plans/2026-05-14-spec-b-continuous-xi-z-implementation.md`
AFTER user approval of this spec.
