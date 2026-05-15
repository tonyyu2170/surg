# Sub-q1 Application-Entry Scaffolds (Tasks 19-21)

**Prep timestamp:** 2026-05-14 ~19:30 CDT (during Task 18 production run).

**Purpose.** Drafted while Task 18 runs (~7-8 hr ETA). Once production
outputs land, fill in `{{PLACEHOLDER}}` references and commit three
separate doc-only changes into `docs/decisions.md` per the plan at
`docs/plans/2026-05-14-sub-q1-batched-diagnostics-implementation.md`
(Tasks 19, 20, 21).

**How to use each scaffold.**
1. Read the source JSON listed in each scaffold's "Inputs" block.
2. Copy the scaffold body (everything between the `===BEGIN ENTRY===`
   and `===END ENTRY===` markers) and append it to `docs/decisions.md`.
3. Replace `{{...}}` placeholders. The `{{path.field}}` syntax names
   the JSON field; the `{{IF outcome=X: prose}}` blocks select the
   correct branch based on a rule outcome.
4. Delete remaining unused conditional branches.
5. Commit doc-only per the Task 19/20/21 step "Commit" instructions.

**Do NOT** commit this scaffold file alongside the application
entries (it'd be redundant with the entries themselves). Either delete
the file post-Task 21 or move it to a session-notes location. Decision
deferred.

**Style anchors.** All three scaffolds mirror the structure of the
existing 2026-05-14 Spec B application entry (lines 1876-2036 of
`docs/decisions.md`): Context → Production-run config → Headline result
→ Supplementary tables → Interpretation/Implication paragraphs →
Revisit-when. Tone is descriptive-first, prose where the Rule dispatch
is mechanical, conditional branches where the Rule 2 outcome varies.

---

## SCAFFOLD FOR TASK 19 — Item #2 (LMP-components Rule 2 dispatch)

**Inputs (read into context before filling):**
- `outputs/gpd_components/headline.json` — single object. Fields:
  `component`, `pnode_label`, `threshold_quantile`, `n_exc`,
  `shape_diff`, `shape_diff_ci_95`, `rule_2_outcome`, `paper_claim`,
  `rule_1_singular_headline`, `pre_reg_reference`.
- `outputs/gpd_components/primary_cluster_supplementary.json` —
  `{results: [...], scope}` with 2 entries (congestion, marginal_loss)
  at p95 on the primary cluster.
- `outputs/gpd_components/cross_pnode.json` — 3 components × all
  labeled pnodes at p95 (`ox`, `bristers`, `dom_zonal`, `ashburn_tx1`,
  `ashburn_tx2`).
- `outputs/gpd_components/threshold_sweep.json` — 3 components ×
  3 thresholds (0.90, 0.95, 0.99) on the primary cluster.

**Pre-flight sanity checks before writing the entry:**
- Confirm `HEADLINE.rule_1_singular_headline` matches the pre-reg's
  Rule 1 wording (cluster_mean + 95th-pct + Loudoun + filtered subset).
- Confirm `HEADLINE.pre_reg_reference` points to the actual
  pre-reg entry (line 2038 of `decisions.md`).
- Confirm `HEADLINE.n_exc` >= 100 (n_per_half >= 50, above Rule 4 floor).
- Note which Rule 2 row applies: `cancellation_supported`,
  `ordc_rejected_broader`, `underpowered_pos_direction`,
  `underpowered_neg_direction`, or `insufficient_sample`.

===BEGIN ENTRY===

## 2026-05-XX — Application of #2 pre-reg: LMP-components decomposition verdict

**Context.** The 2026-05-14 LMP-components decomposition
pre-registration ("sub-q1 closure item #2", `docs/decisions.md`
line 2038) locked decision rules before any GPD fit on the
4-component-decomposed LMP ran. This entry applies Rule 2 mechanically
to the production outputs in `outputs/gpd_components/`, records the
supplementary descriptive evidence across pnodes and thresholds, and
captures the implication for the paper's mechanism narrative.

The headline outcome is **"{{HEADLINE.rule_2_outcome}}"** per Rule 2.

{{IF rule_2_outcome=cancellation_supported:
The proposal's strongest mechanism-affirming outcome. `system_energy`
carries the ORDC-predicted direction (heavier tail at HIGH Z), confirming
the "cancellation hypothesis" that explains why the same median-split
on `total_lmp` was inconclusive: congestion and system_energy carry
opposite-direction tail-shape effects that partially cancel in the
aggregated total. The conditional-Z LOW-Z rejection on congestion
(2026-05-14 entry) and the system_energy HIGH-Z confirmation (this
entry) together support a clean ORDC mechanism story.}}

{{IF rule_2_outcome=ordc_rejected_broader:
ORDC-direction is rejected for `system_energy` too. The heavier-tail-at-
LOW-Z effect detected in congestion is broader than congestion alone —
it also affects the system_energy component. This sharpens the prior
conditional-Z rejection: the mechanism is NOT ORDC-specific; the
effect is system-wide. The paper's mechanism section reframes from
"ORDC scarcity adders heavy-tail HIGH-Z load" to "load-volatility
correlates with low-LMP regimes broadly, mechanism remains to be
identified."}}

{{IF rule_2_outcome=underpowered_pos_direction:
Direction matches the ORDC prediction (`system_energy shape_diff > 0`)
but the bootstrap CI spans 0 at the available headline n. Magnitude is
power-bounded; direction is informative as evidence the "cancellation
hypothesis" is plausible without confirming it at α=0.05. The original
congestion conditional-Z rejection remains the strongest single
empirical anchor; the LMP-components decomposition adds direction
evidence for ORDC.}}

{{IF rule_2_outcome=underpowered_neg_direction:
Direction is consistent with the congestion finding (heavier tail at
LOW Z) rather than ORDC's predicted direction. Underpowered at the
available headline n. The components decomposition does not provide
the cancellation evidence the proposal hoped for; the paper's mechanism
section must acknowledge the system-wide LOW-Z effect rather than
positing the ORDC-specific HIGH-Z effect on system_energy.}}

{{IF rule_2_outcome=insufficient_sample:
The headline test triggers Rule 4 (insufficient sample;
n_per_half < 50). The components decomposition cannot contribute a
verdict at this scope. Sub-q1's tail-shape verdict is unchanged from
the 2026-05-14 conditional-Z application entry.}}

**Production-run config.**
- Code: `feature/sub-q1-batched-diagnostics` worktree (FF-merged into
  main after this entry's commit). 240 tests passing.
- 4-component decomposition (`total_lmp`, `system_energy`, `congestion`,
  `marginal_loss`) at the cluster level (`*_price_rt_cluster_mean`) per
  the Task 1-2 `features.py` pivot (commit `a5bc16e` + `1767a07`).
- Headline median-split applied at 95th-pct LMP on the filtered subset
  (`passes_proposal_filter=True`) using
  Z = `dom_load_gradient_abs_mw_per_min`, with pair-bootstrap n_boot=200
  for the shape_diff CI.

### Headline result — Rule 2 application

`{{HEADLINE.component}}_price_rt_cluster_mean` median-split @
{{int(HEADLINE.threshold_quantile*100)}}th-pct LMP on the primary
Loudoun cluster, filtered subset:

- n_exc = {{HEADLINE.n_exc}}, n_per_half = {{HEADLINE.n_exc // 2}}
- **shape_diff = {{HEADLINE.shape_diff}}**
- bootstrap 95% CI: **[{{HEADLINE.shape_diff_ci_95.0}},
  {{HEADLINE.shape_diff_ci_95.1}}]**
- **Rule 2 outcome:** `{{HEADLINE.rule_2_outcome}}`
- Paper claim (Rule 2): *"{{HEADLINE.paper_claim}}"*
- Pre-reg reference: `docs/decisions.md § 2026-05-14 — Pre-registration:
  LMP-components decomposition (sub-q1 closure item #2)`.

### Primary cluster supplementary at 95th-pct (descriptive, no MT correction)

From `outputs/gpd_components/primary_cluster_supplementary.json`. The
two non-headline components on the same primary cluster + threshold +
filter scope:

| Component | shape_diff | Bootstrap CI 95% | n_exc | Rule 2 outcome |
|---|---|---|---|---|
| congestion | {{PCS.congestion.shape_diff}} | [{{PCS.congestion.shape_diff_ci_95.0}}, {{PCS.congestion.shape_diff_ci_95.1}}] | {{PCS.congestion.n_exc}} | {{PCS.congestion.rule_2_outcome}} |
| marginal_loss | {{PCS.marginal_loss.shape_diff}} | [{{PCS.marginal_loss.shape_diff_ci_95.0}}, {{PCS.marginal_loss.shape_diff_ci_95.1}}] | {{PCS.marginal_loss.n_exc}} | {{PCS.marginal_loss.rule_2_outcome}} |

(The `system_energy` headline row is the same as the headline section
above. Included here for completeness only conceptually.)

**Observations.**

{{Compare congestion's shape_diff to the prior median-split on
congestion at the conditional-Z scope (n=789/half; shape_diff = −0.18,
CI [−0.37, −0.04]). At the components scope (n_per_half=51),
congestion's direction should be consistent in sign but with a wider
CI. Whether marginal_loss aligns with congestion (negative) or with
system_energy (positive) is descriptive evidence about which side of
the LMP decomposition dominates at the cluster level.}}

### Cross-pnode supplementary at 95th-pct (descriptive, no MT correction)

From `outputs/gpd_components/cross_pnode.json`. Three components × five
non-primary labeled pnodes at p95 on the filtered subset:

| Pnode | `system_energy` shape_diff [CI] | `congestion` shape_diff [CI] | `marginal_loss` shape_diff [CI] |
|---|---|---|---|
| ox | {{CP.system_energy.ox.shape_diff}} [{{ci}}] | {{CP.congestion.ox.shape_diff}} [{{ci}}] | {{CP.marginal_loss.ox.shape_diff}} [{{ci}}] |
| bristers | {{CP.system_energy.bristers.shape_diff}} [...] | {{CP.congestion.bristers.shape_diff}} [...] | {{CP.marginal_loss.bristers.shape_diff}} [...] |
| dom_zonal | {{CP.system_energy.dom_zonal.shape_diff}} [...] | {{CP.congestion.dom_zonal.shape_diff}} [...] | {{CP.marginal_loss.dom_zonal.shape_diff}} [...] |
| ashburn_tx1 | {{CP.system_energy.ashburn_tx1.shape_diff or "insufficient_sample"}} | {{CP.congestion.ashburn_tx1.shape_diff or "insufficient_sample"}} | {{CP.marginal_loss.ashburn_tx1.shape_diff or "insufficient_sample"}} |
| ashburn_tx2 | {{CP.system_energy.ashburn_tx2.shape_diff or "insufficient_sample"}} | {{CP.congestion.ashburn_tx2.shape_diff or "insufficient_sample"}} | {{CP.marginal_loss.ashburn_tx2.shape_diff or "insufficient_sample"}} |

Pnodes flagged `insufficient_sample` triggered Rule 4 (n_per_half < 50)
and are reported without a verdict. Smoke run showed both Ashburn
pnodes triggering this at 95th-pct on all three components — production
likely reproduces this pattern.

**Observations.**

{{Flag any single labeled pnode with shape_diff direction OPPOSITE to
the primary cluster's verdict at α (descriptive only). Cross-pnode
direction agreement is evidence the mechanism is cluster-wide; a
single opposite-direction labeled pnode would be a focused diagnostic
hook.}}

### Threshold sweep on primary cluster (descriptive)

From `outputs/gpd_components/threshold_sweep.json`. Three components ×
three thresholds on the primary cluster, filtered subset:

| Quantile | n_exc | `system_energy` shape_diff [CI] | `congestion` shape_diff [CI] | `marginal_loss` shape_diff [CI] |
|---|---|---|---|---|
| 0.90 | {{TS.system_energy.0.90.n_exc}} | {{TS.system_energy.0.90.shape_diff}} [...] | {{TS.congestion.0.90.shape_diff}} [...] | {{TS.marginal_loss.0.90.shape_diff}} [...] |
| 0.95 (headline) | {{TS.system_energy.0.95.n_exc}} | {{TS.system_energy.0.95.shape_diff}} [...] | {{TS.congestion.0.95.shape_diff}} [...] | {{TS.marginal_loss.0.95.shape_diff}} [...] |
| 0.99 | {{TS.system_energy.0.99.n_exc or "insufficient_sample"}} | ... | ... | ... |

(Production may keep 99th-pct in `insufficient_sample` per smoke
preview: n_exc=21, n_per_half=10 well below the Rule 4 floor of 50.)

**Observations.**

{{Direction stability across thresholds — does `system_energy`'s sign
stay consistent at p90 vs p95? Does magnitude grow with threshold?
This is the closest the components decomposition gets to the "deeper
threshold sharpens the verdict" pattern Spec B documented for
congestion alone.}}

### Implication for sub-question 1

{{One paragraph. Specifically address how this changes the conditional-Z
verdict from the 2026-05-14 entry. Reference the Spec B verdict
(2026-05-14 line 1971): "Spec B confirmed total_lmp's continuous β₁ is
much smaller in magnitude than congestion's" — system_energy's
direction provides the complementary evidence (or doesn't) about
whether the system-wide effect on total_lmp is dominated by congestion's
LOW-Z effect, masked by system_energy's HIGH-Z effect (cancellation),
or absent (ordc_rejected_broader).}}

### Implication for the paper

{{One paragraph. Update the paper's mechanism story:
- IF `cancellation_supported`: paper has a clean three-component
  ORDC story (system_energy HIGH-Z, congestion LOW-Z, total_lmp null
  because they cancel). Lead with this in the mechanism section.
- IF `ordc_rejected_broader`: paper acknowledges the system-wide
  LOW-Z effect. Mechanism story shifts from "ORDC scarcity adders" to
  "system-wide load-volatility correlation, mechanism unidentified."
- IF underpowered (either direction): paper acknowledges the power
  ceiling. Mechanism story rests on the conditional-Z congestion
  rejection plus the directionally-consistent components evidence.
- IF `insufficient_sample`: components decomposition is a methods-
  section footnote, not a paper-level claim.}}

### Revisit when

- Advisor input materially shifts framing for the mechanism narrative.
- A longer historical window enables higher-resolution components
  tests at deeper thresholds (currently 99th-pct on system_energy
  is sample-limited).
- The Ashburn TX1 distribution-side anomaly (sub-q1 item #4) lands —
  if (a) "real distribution-side physics," the components decomposition
  at the Ashburn pnodes may matter despite the headline scope being
  cluster-level.

===END ENTRY===

---

## SCAFFOLD FOR TASK 20 — Item #3 (τ=0.99 secular sign-flip)

**Inputs:**
- `outputs/year_fe_diagnostic/<pnode>.json` for each of the 7 pnodes:
  `primary`, `total_lmp`, `ox`, `bristers`, `dom_zonal`, `ashburn_tx1`,
  `ashburn_tx2`. Fields:
  - `layer1_raw_per_year[]` — per-year `{year, n_obs, p90, p95, p99}`.
  - `layer2_year_dummy_bootstrap.tau_0.99` — per-year
    `{point, ci, n_boot_converged}` relative to baseline year 2022.
  - `layer3_secular_component_bootstrap.tau_0.X` —
    `{primary_z_slope, year_fe_z_slope, secular_component_point,
    secular_component_ci, n_boot_converged}` for the 3 taus.
- `outputs/year_fe_diagnostic/cross_pnode_summary.json` —
  `{rows: [...]}` with per-pnode per-tau secular component summary.

**Pre-flight sanity checks:**
- Confirm `n_boot_converged` ≈ 200 across pnodes/taus. Any pnode/tau
  where convergence is well below 200 → bootstrap is failing on small
  tail samples; flag in Interpretation as case (b) for that pnode.
- Confirm `n_total_panel` matches the analysis panel row count
  (~31,536 in smoke; production should be similar).
- Note the 2026 year's `n_obs` — it's a partial-year window cut off
  at the panel build date; large 2026 dummies are partly composition
  effects (high-load months over-represented) rather than pure secular
  trend.

===BEGIN ENTRY===

## 2026-05-XX — Sub-q1 item #3: τ=0.99 secular sign-flip diagnostic (descriptive)

**Context.** The 2026-05-14 Spec B application entry (line 1876) left
open: at τ=0.99 the QR-full `z_slope` flips negative across most
pnodes, contrasting the positive `z_slope` at τ=0.90/0.95. Three
possible causes:
- (a) **Real grid improvement** — the 99th-pct LMP has trended
  downward across the 3.6y window (e.g., PJM market design changes,
  generation mix shift), and the τ=0.99 QR is picking up a secular
  component rather than a contemporaneous load-volatility response.
- (b) **Sparse-tail bootstrap artifact** — at τ=0.99 the QR estimator
  fits with ~316 observations on the proposal-filtered subset; small-n
  instability could explain the sign flip.
- (c) **Window-specific noise** — the 3.6y post-2022-10 window happens
  to span a regime change (e.g., 2025-2026 spike), and the τ=0.99 fit
  is over-weighted by atypical years.

The three-layer diagnostic decomposes the τ=0.99 `z_slope` into a
**primary specification** (no year-FE; the spec used in Spec B) and a
**year-FE-augmented specification** (year dummies absorb level shifts),
then pair-bootstraps the difference (primary − year_fe) as the
**"secular component."** If the secular component CI excludes 0 → there
IS a real downward trend in 99th-pct LMP across years, and the τ=0.99
sign flip is a year-FE-detectable secular trend rather than a tail
artifact.

**Production-run config.**
- 7 pnodes (`primary`, `total_lmp`, `ox`, `bristers`, `dom_zonal`,
  `ashburn_tx1`, `ashburn_tx2`) × 3 taus (0.90, 0.95, 0.99).
- Pair-bootstrap n_boot=200 for both Layer 2 (year-dummy CIs) and
  Layer 3 (secular component CI).
- Code: `feature/sub-q1-batched-diagnostics`. Tests cover all 3 layers.

### Layer 1 — Raw per-year p99 LMP trajectory (descriptive)

From `outputs/year_fe_diagnostic/<pnode>.json` (`layer1_raw_per_year[]`).
Each cell is the year's empirical p99 of the response column (Z is not
involved):

| Pnode | 2022 p99 | 2023 p99 | 2024 p99 | 2025 p99 | 2026 p99 (partial) |
|---|---|---|---|---|---|
| primary | {{Y.primary.2022.p99}} | {{Y.primary.2023.p99}} | {{Y.primary.2024.p99}} | {{Y.primary.2025.p99}} | {{Y.primary.2026.p99}} |
| total_lmp | ... | ... | ... | ... | ... |
| ox | ... | ... | ... | ... | ... |
| bristers | ... | ... | ... | ... | ... |
| dom_zonal | ... | ... | ... | ... | ... |
| ashburn_tx1 | ... | ... | ... | ... | ... |
| ashburn_tx2 | ... | ... | ... | ... | ... |

(2022 is a partial year — post-2022-10 only — so the 2022 p99 is
based on `n_obs ≈ 2185`; 2026 is also partial through the panel build
date.)

**Observations.**

{{Trend direction per pnode at p99. Smoke shows primary p99 stepping
up across years (11→9→9→15→59), not down. If production reproduces a
generally UPWARD p99 trajectory, the τ=0.99 sign flip's "real grid
improvement" explanation (case a) is contradicted — secular component
should be NON-negative at year-FE level.}}

### Layer 2 — Year-dummy bootstrap at τ=0.99 (descriptive level shifts, not a trend test)

From `outputs/year_fe_diagnostic/<pnode>.json`
(`layer2_year_dummy_bootstrap.tau_0.99`). Each cell is the year-dummy
point estimate relative to baseline year 2022, with pair-bootstrap CI:

| Pnode | year_2023 | year_2024 | year_2025 | year_2026 |
|---|---|---|---|---|
| primary | {{L2.primary.tau_0.99.year_2023.point}} [{{ci}}] | {{...}} | {{...}} | {{...}} |
| total_lmp | ... | ... | ... | ... |
| ox | ... | ... | ... | ... |
| bristers | ... | ... | ... | ... |
| dom_zonal | ... | ... | ... | ... |
| ashburn_tx1 | ... | ... | ... | ... |
| ashburn_tx2 | ... | ... | ... | ... |

(`n_boot_converged` annotated in footnotes where below 200.)

**Observations.**

{{Per-year level shifts at τ=0.99 are descriptive, NOT the trend test
itself (Layer 3 is). Note whether 2026 dummies dominate (smoke shows
~+355 for primary at τ=0.99 in 2026). Large 2026 dummies + small
n_obs in 2026 → year-FE absorbs the late-window spike. The trend test
in Layer 3 nets this out.}}

### Layer 3 — Secular-component bootstrap (the trend test)

From `outputs/year_fe_diagnostic/<pnode>.json`
(`layer3_secular_component_bootstrap.tau_X`) — pair-bootstrap CI on
`primary_z_slope − year_fe_z_slope`:

#### τ=0.99 (the sign-flip threshold)

| Pnode | primary_z_slope | year_fe_z_slope | secular component (point) | secular component CI 95% |
|---|---|---|---|---|
| primary | {{L3.primary.tau_0.99.primary_z_slope}} | {{L3.primary.tau_0.99.year_fe_z_slope}} | {{L3.primary.tau_0.99.secular_component_point}} | [{{L3.primary.tau_0.99.secular_component_ci.0}}, {{.1}}] |
| total_lmp | ... | ... | ... | [...] |
| ox | ... | ... | ... | [...] |
| bristers | ... | ... | ... | [...] |
| dom_zonal | ... | ... | ... | [...] |
| ashburn_tx1 | ... | ... | ... | [...] |
| ashburn_tx2 | ... | ... | ... | [...] |

#### τ=0.95 and τ=0.90 (reference, no sign-flip)

(Brief table — same fields — to confirm the diagnostic agrees at taus
where Spec B's z_slope is robustly positive. If the secular component
at τ=0.95 is near 0 with CI containing 0 across pnodes → diagnostic
is well-behaved; the τ=0.99 secular component is the only meaningful
result.)

| Pnode | τ=0.95 secular [CI] | τ=0.90 secular [CI] |
|---|---|---|
| primary | {{L3.primary.tau_0.95.secular_component_point}} [...] | {{L3.primary.tau_0.90...}} [...] |
| ... | ... | ... |

**Interpretation — which case does the data support at τ=0.99?**

- (a) **Real grid improvement / downward trend in 99th-pct.** Evidence:
  - `secular_component_ci` excludes 0 on the NEGATIVE side at τ=0.99
    on most pnodes (i.e., `primary_z_slope < year_fe_z_slope`).
  - Layer 1 raw p99 trajectory shows a downward trend per pnode.
  - `n_boot_converged` ≈ 200 (diagnostic is well-powered at τ=0.99).
  - In this case: the τ=0.99 QR-full sign flip in Spec B is a real
    secular trend artifact; sub-q2 JLARC projection should use the
    year-FE slope (contemporaneous response, secular-trend-removed)
    rather than the primary slope.

- (b) **Sparse-tail bootstrap artifact.** Evidence:
  - `n_boot_converged` is well below 200 at τ=0.99 across most pnodes.
  - Layer 2 year-dummy CIs are very wide.
  - In this case: the τ=0.99 point estimate is unreliable. Sub-q2
    JLARC projection at the 99th-pct should be flagged as
    power-limited and given less weight in the headline finding.

- (c) **Window-specific noise.** Evidence:
  - Pnodes disagree on sign of the secular component at τ=0.99 but
    agree at τ=0.90/0.95.
  - Year 2025 or 2026 dummies dominate Layer 2 (very large relative
    to other years); year-FE absorbs window-specific composition
    effects rather than a true secular trend.
  - In this case: the τ=0.99 sign flip is window-noise. Sub-q2 JLARC
    projection at the 99th-pct extrapolates from a non-stationary
    sample — flag explicitly.

{{Pick the case the production numbers support. Smoke preview:
primary_z_slope = +0.36, year_fe_z_slope = +0.62, secular component
point = −0.26 with CI [−0.79, +0.31] spans 0 — at smoke resolution,
underpowered. Production tightening to a reject-negative would confirm
case (a).}}

### Implication for the paper

{{One paragraph. Either:
- If case (a): paper's τ=0.99 result needs a caveat about the secular
  trend, and the year-FE slope becomes the headline at the 99th-pct.
- If case (b): paper acknowledges the τ=0.99 result is power-limited
  and treats the τ=0.95 finding as the primary headline.
- If case (c): paper reports both slopes (primary and year-FE) at
  τ=0.99 and lets readers see the window-specific divergence.}}

### Implication for sub-question 2 (JLARC projection)

{{One paragraph on which `z_slope` to use at τ=0.99 in the projection
layer. The JLARC napkin-math used the primary slope; the production
projection should reconcile this entry's recommendation:
- Case (a): switch τ=0.99 projection to the year-FE slope.
- Case (b): defer the τ=0.99 projection or skip it; emphasize τ=0.95.
- Case (c): present both projections with the methodological caveat.}}

### Revisit when

- Sub-q2 JLARC plan-writing — this entry feeds directly into the
  projection slope choice (currently locked behind the sub-q1 closure
  gate).
- Advisor input on whether year-FE is the right secular-trend
  decomposition.
- Additional historical data (pre-2022-10) materially changes the
  year-FE coefficients; currently no path without re-introducing the
  pre-cap regime break.

===END ENTRY===

---

## SCAFFOLD FOR TASK 21 — Item #4 (Ashburn TX1 99th-pct anomaly)

**Inputs:**
- `outputs/ashburn_diagnostic/tx1_loo.json` —
  `{pnode_label, results: [...]}` where each result has
  `{pnode_label, threshold_quantile, n_exc, full_sample_beta_1,
  loo_beta_1_distribution[]}`. `loo_beta_1_distribution` is a list of
  `n_exc` floats — the i-th entry is β₁ refit after dropping the i-th
  exceedance.
- `outputs/ashburn_diagnostic/tx2_loo.json` — same structure for TX2.
- `outputs/ashburn_diagnostic/cross_threshold_summary.json` —
  `{pnodes: [{pnode_label, response_col, entries:
  [{threshold_quantile, beta_1, beta_1_ci_95, convergence_status}]}]}` —
  Spec B β₁ + CI cross-thresholds, both TX1 and TX2.
- `outputs/ashburn_diagnostic/scatter_overlay.png` — 4-panel scatter
  with both pnodes overlaid at p95 and p99 thresholds.

**Pre-flight sanity checks:**
- Confirm `cross_threshold_summary.json` TX1 q=0.99 entry shows
  `beta_1 ≈ +0.093` and `convergence_status="converged"` (this is the
  Spec B anomaly being diagnosed). Smoke run was at n_boot=30 and
  showed `insufficient_bootstrap_reps`; production with n_boot=200
  should converge.
- Confirm `tx1_loo.json` q=0.99 `full_sample_beta_1 ≈ +0.0932` matches
  the Spec B cross-pnode entry exactly (sanity-check pipeline).
- Per the 2026-05-14 LOO/response-col fix commit `6b93af9`:
  `response_col` should be `congestion_price_rt_ashburn_tx1` (NOT
  total_lmp). Smoke fix verified this.

**Derived stats to compute from the JSON:**
For each `(pnode, threshold)`:
- `loo_mean = mean(loo_beta_1_distribution)`
- `loo_median = median(loo_beta_1_distribution)`
- `loo_stdev = stdev(loo_beta_1_distribution)`
- `loo_iqr = (q25, q75)`
- `loo_range = (min, max)`
- `signed_delta = full_sample_beta_1 - loo_beta_1_distribution[i]` per i
- Top-5 influential exceedances: indices with largest `|signed_delta|`
- Sign-change refits: count of i where `loo_beta_1_distribution[i]`
  has opposite sign to `full_sample_beta_1`

===BEGIN ENTRY===

## 2026-05-XX — Sub-q1 item #4: Ashburn TX1 99th-pct anomaly diagnostic (descriptive)

**Context.** The 2026-05-14 Spec B application entry's cross-pnode
table (`docs/decisions.md` line 1922) flagged Ashburn TX1's β₁ flipping
sign at q=0.99: at thresholds q ∈ {0.90, 0.95, 0.995} β₁ is negative
(consistent with cross-pnode pattern), but at q=0.99
**β₁ = +0.0932** with CI [+0.010, +0.167], p = 0.030, and LRT p = 0.000
(strong non-linearity). Three competing interpretations from that
entry:
- (a) **Real distribution-side physics** at the extreme tail —
  Ashburn (35 kV LOAD subtype) may have qualitatively different
  tail-shape behavior at ORDC-relevant levels vs the 500 kV
  transmission pnodes. Signal detectable at q=0.99 because that's
  where ORDC events concentrate.
- (b) **Power-driven over-fit** — n_exc ≈ 175 at q=0.99 with a 4-DOF
  linear + 6-DOF spline fit is fragile. One or two outlier exceedances
  could drive the sign flip.
- (c) **Data quality issue** — Ashburn pnodes have asymmetric coverage
  (~2y vs 3.6y per the 2026-05-12 archive-mode decision); the q=0.99
  exceedance set may be concentrated in atypical months.

This entry runs a leave-one-out (LOO) re-estimation across all 4
thresholds, with TX2 as a sibling cross-check, to discriminate (b)
from (a)/(c).

**Production-run config.**
- TX1 and TX2 LOO at 4 thresholds (0.90, 0.95, 0.99, 0.995). Each LOO
  refit is a deterministic GPD MLE (n_boot=0) on the exceedance set
  minus one observation; response column is `congestion_price_rt_<tx>`
  per the 2026-05-14 fix commit `6b93af9` (Spec B's anomaly is on
  congestion, not total_lmp).
- n_exc ≈ {1745, 873, 175, 87} for TX1 across the four thresholds.
  Total LOO fits per pnode ≈ 2,880.
- 4-panel scatter overlay PNG generated by `ashburn_diagnostic`'s
  visualization step (TX1 + TX2 at p95 and p99).

### LOO summary at 99th-pct — Ashburn TX1 (the anomaly threshold)

From `outputs/ashburn_diagnostic/tx1_loo.json` (results[2] —
`threshold_quantile=0.99`):

- **Full-sample β₁ = {{TX1.q99.full_sample_beta_1}}** (matches Spec B's
  cross-pnode entry at q=0.99 — pipeline sanity check passes).
- n_exc = {{TX1.q99.n_exc}} LOO refits.
- LOO distribution summary:
  - mean = {{computed.loo_mean}}, median = {{computed.loo_median}}
  - stdev = {{computed.loo_stdev}}
  - IQR = [{{computed.q25}}, {{computed.q75}}]
  - range = [{{computed.loo_min}}, {{computed.loo_max}}]
- **Sign-change refits:** {{computed.n_sign_change}} out of
  {{TX1.q99.n_exc}} ({{computed.pct_sign_change}}%). 
  {{IF n_sign_change > 5%: significant fraction of single observations
  flip the sign — strong evidence for case (b).}}
  {{IF n_sign_change ≈ 0: the +0.0932 is NOT outlier-driven — strong
  evidence against case (b).}}

#### Top-5 most influential exceedances at q=0.99

| Rank | Index in exceedance set | β₁_loo | Δβ₁ = full − loo |
|---|---|---|---|
| 1 | {{idx_1}} | {{loo_dist[idx_1]}} | {{computed.delta_1}} |
| 2 | {{idx_2}} | {{loo_dist[idx_2]}} | {{computed.delta_2}} |
| 3 | {{idx_3}} | {{loo_dist[idx_3]}} | {{computed.delta_3}} |
| 4 | {{idx_4}} | {{loo_dist[idx_4]}} | {{computed.delta_4}} |
| 5 | {{idx_5}} | {{loo_dist[idx_5]}} | {{computed.delta_5}} |

(Indices sorted by |Δβ₁| descending; index numbers are positions in
the threshold-filtered exceedance set, not panel row indices.)

### LOO summary at other thresholds — Ashburn TX1

From `outputs/ashburn_diagnostic/tx1_loo.json` (results[0], [1], [3]):

| Threshold | n_exc | full β₁ | LOO mean | LOO stdev | n_sign_change |
|---|---|---|---|---|---|
| 0.90 | {{TX1.q90.n_exc}} | {{TX1.q90.full_sample_beta_1}} | {{loo_mean}} | {{loo_stdev}} | {{n_sign_change}} |
| 0.95 | {{TX1.q95.n_exc}} | {{TX1.q95.full_sample_beta_1}} | ... | ... | ... |
| 0.99 (anomaly) | {{TX1.q99.n_exc}} | {{TX1.q99.full_sample_beta_1}} | (see above) | (above) | (above) |
| 0.995 | {{TX1.q995.n_exc}} | {{TX1.q995.full_sample_beta_1}} | ... | ... | ... |

**Observations.**

{{Smoke preview (n_boot=30 but LOO is deterministic and complete at
smoke scale): LOO stdev at q=0.99 = 0.0028, range [0.0830, 0.1007].
The +0.0932 is robust to dropping any single exceedance — direct
evidence against case (b) for the q=0.99 threshold. Compare to other
thresholds in production: a similarly tight LOO at q=0.99 + wider LOO
at q=0.995 would isolate the anomaly to q=0.99 specifically.}}

### TX2 cross-check across all thresholds

From `outputs/ashburn_diagnostic/tx2_loo.json`:

| Threshold | n_exc | full β₁ | LOO mean | LOO stdev | Direction agreement with TX1? |
|---|---|---|---|---|---|
| 0.90 | {{TX2.q90.n_exc}} | {{TX2.q90.full_sample_beta_1}} | ... | ... | {{compare signs}} |
| 0.95 | ... | ... | ... | ... | {{compare}} |
| 0.99 (key) | ... | ... | ... | ... | {{compare — KEY QUESTION: does TX2 also show q=0.99 anomaly?}} |
| 0.995 | ... | ... | ... | ... | {{compare}} |

**Key observation.**

{{If TX2's q=0.99 β₁ is ALSO positive with robust LOO → strong
evidence for case (a) "real distribution-side physics" — both Ashburn
substations share the q=0.99 anomaly. If TX2's q=0.99 β₁ is negative
or wildly different in magnitude → the anomaly is TX1-specific, more
suggestive of (b)/(c) for TX1 in isolation. Spec B's prior cross-pnode
table at q=0.99 has TX1 = +0.0932 (CI excludes 0) and TX2 ≈ -0.011
(CI spans 0) — that disagreement, if reproduced and tightened at LOO
scale, is evidence the q=0.99 anomaly is TX1-specific.}}

### 4-panel scatter overlay

See `outputs/ashburn_diagnostic/scatter_overlay.png`. The four panels
show:
1. TX1 exceedances at q=0.95, congestion vs Z.
2. TX1 exceedances at q=0.99, congestion vs Z.
3. TX2 exceedances at q=0.95, congestion vs Z.
4. TX2 exceedances at q=0.99, congestion vs Z.

**Visual notes.**

{{Brief description after viewing the PNG. Key things to note:
- Does TX1 at q=0.99 visually show a positive-trending fan vs the
  negative trends at q=0.95?
- Does the exceedance set at q=0.99 cluster around specific Z values
  (suggesting temporal concentration / data quality)?
- Are there obvious outlier exceedances that would dominate the fit?}}

### Interpretation — which case does the evidence support?

- (a) **Real distribution-side physics.** Supported if:
  - LOO stdev at q=0.99 is small relative to full-sample β₁ → not
    outlier-driven.
  - TX2 q=0.99 β₁ direction agrees with TX1 → both substations share
    the effect.
  - Scatter overlay shows a visually distinct shape at the high tail.
- (b) **Power-driven over-fit.** Supported if:
  - LOO stdev is large or sign-change refits non-zero → fragile fit.
  - TX2 q=0.99 β₁ direction disagrees with TX1 → anomaly is
    TX1-specific.
  - Scatter overlay shows 1-3 obvious outliers dominating the q=0.99
    exceedance set.
- (c) **Data quality issue.** Supported if:
  - TX1's q=0.99 exceedances cluster in specific months or years
    (e.g., concentrated in the partial-window 2026 months).
  - The asymmetric coverage gap (2y vs 3.6y, per 2026-05-12) puts
    the q=0.99 exceedance count below the substantive Rule 4 floor
    when properly accounted for.

{{Final pick: smoke preview is consistent with (a) at TX1 (LOO stdev
0.003 << |full β₁| = 0.093), but case (a) requires the TX2 cross-check
to ALSO show positive q=0.99 β₁. If TX2 q=0.99 is negative → revised
to TX1-specific, mixed (a)+(b)/(c). The strongest interpretation the
data supports lands here.}}

### Implication for the paper

{{One paragraph methodology footnote framing. If (a) → the q=0.99
Ashburn TX1 anomaly is a paper-worthy finding (distribution-side
physics at ORDC-relevant tail levels). Suggests a sub-section in the
mechanism chapter. If (b) → methodological footnote: "TX1's q=0.99
β₁ point estimate is sample-fragile; we report it for transparency but
do not interpret the sign at this scope." If (c) → caveat in the data
section: "Ashburn pnodes' asymmetric coverage limits inference at
deep thresholds."}}

### Revisit when

- Advisor input on whether the anomaly is worth a sub-section vs
  footnote in the paper.
- Additional Ashburn-specific data (longer history at higher
  resolution) becomes available — would re-test (b) at larger n_exc.
- The components decomposition at the Ashburn pnodes (sub-q1 item #2
  cross-pnode supplementary) materially shifts the interpretation —
  if `system_energy` shows a positive shape_diff at Ashburn q=0.99,
  the components decomposition supports case (a).

===END ENTRY===

---

## After Tasks 19-21 — Task 22 closure roadmap update

The plan's Task 22 updates
`docs/plans/2026-05-14-sub-question-1-closure-roadmap.md` to mark
items #2/#3/#4 DONE with commit SHAs from Tasks 19/20/21. The
roadmap entry table currently shows items 2-5 as "Open" per the
2026-05-14 Spec B application entry (line 2017-2027 of `decisions.md`).
After Tasks 19-21 ship:
- Item #2 → DONE (commit SHA from Task 19) with Rule 2 verdict.
- Item #3 → DONE (commit SHA from Task 20) with case (a/b/c) verdict.
- Item #4 → DONE (commit SHA from Task 21) with case (a/b/c) verdict.
- Item #5 (advisor meeting) → still Open, but now ready: items 2-4
  evidence is all available for discussion.
