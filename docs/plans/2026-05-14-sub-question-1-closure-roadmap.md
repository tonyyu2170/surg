# Sub-Question 1 Closure Roadmap

> **Status:** Drafted 2026-05-14 to document the full set of remaining
> work needed to bring sub-question 1 — "what is the critical volatility
> threshold of data center load variance that triggers a non-linear
> phase transition in DOM congestion pricing?" — to **paper-publishable
> confidence**. Brainstormed scope + sequencing with the user in-session.
>
> **Closure status as of 2026-05-14 night:** Items 1, 2, 3, 4 all DONE.
> Items 5 (advisor meeting) and 6 (direct Z → LMP tail-risk
> characterization, added late tonight) remain as open closure steps.
> Item 6 sequenced BEFORE item 5 so the advisor sees the complete
> sub-q1 picture (mechanism + descriptive characterization).
> Commits (chronological):
> - Item 1 — Spec B continuous ξ(Z): `fe2cb94` (FF-merged earlier).
> - Item 2 — LMP-components decomposition (reframed from "response-
>   variable sensitivity"): commit `01ebbd8`.
> - Item 3 — τ=0.99 secular sign-flip: commit `72456bb`. **NEW finding
>   the roadmap did not anticipate:** moderate-τ positive secular
>   component on 5/7 non-Ashburn pnodes; sub-q2 JLARC slope
>   choice = year-FE z_slope @ τ=0.95.
> - Item 4 — Ashburn TX1 q=0.99 anomaly: commit `fd0065c`. Case (b)
>   outlier-driven RULED OUT (LOO 0/175 sign-change); cases (a) and
>   (c) remain candidate. Framed as "robust unexplained anomaly worth
>   investigating" for methods-section subsection.
> - Item 5 — Advisor meeting: agenda needs updating; not yet scheduled.
> - Item 6 — Direct Z → LMP tail-risk characterization: **added
>   2026-05-14 night** after the user clarified the sub-q1 framing
>   (*"what range of load variance causes LMP to essentially go crazy"*
>   is fundamentally a descriptive characterization of the conditional
>   Z → LMP distribution, not a mechanism test). Items #1-4 stay as
>   mechanism supporting evidence; item #6 adds the direct empirical
>   answer. Design pending brainstorm.

## What's already done (as of 2026-05-14)

- **Smooth-curve diagnosis** (2026-05-13 follow-up entry) — established
  there is no single MW/min threshold; the response is smooth across
  the Z distribution. Replaces the proposal's point-estimate framing.
- **QR-full response characterization** (Strategy C ship 2026-05-14):
  z_slopes at τ=0.90/0.95/0.99 across all 7 pnodes; total_lmp slope
  is ~4× the congestion slope at τ=0.95 (direct ORDC mechanism
  support).
- **GPD threshold sweep** (Strategy C): ξ(threshold) for q=0.90–0.995.
- **Conditional-Z mechanism test** (per-pnode `run_gpd` outputs):
  primary congestion median-split at 95th-pct LMP rejects the
  proposal's heavier-tail-at-high-Z hypothesis (shape_diff = −0.180,
  CI [−0.371, −0.044] excludes 0); total_lmp doesn't.
- **Conditional-Z robustness battery** (Spec A/C/F per pre-reg):
  battery's discrete-split extensions are power-limited at the
  available n per group; Spec A's ξ trajectory is non-monotone on
  both batteries → **Spec B triggered per pre-reg**.

## Remaining work to close sub-q1 (in priority order)

### 1. Spec B — Continuous ξ(Z) regression *(DONE 2026-05-14)*

**Status:** Closed by `docs/decisions.md` § "2026-05-14 — Application
of Spec B pre-reg: continuous ξ(Z) verdict". Design at
`docs/plans/2026-05-14-spec-b-continuous-xi-z-design.md` (commit
`3753b97`); implementation plan at
`docs/plans/2026-05-14-spec-b-continuous-xi-z-implementation.md`
(commit `ca05d25`); pre-reg in decisions.md (commit `0d1064d`);
production run on full 31,536-row panel + application entry written
post-execution. **Headline outcome: "underpowered"** per Rule 2 —
β₁ = −0.0080, CI [−0.021, +0.003], spans 0. Direction consistent
across all 7 pnodes (cross-pnode supplementary); magnitude grows at
deeper thresholds (β₁ = −0.028 at 99th-pct, n_exc = 316); LRT detects
non-linearity at 90th-pct (p = 0.007).

**Closed:** the central pre-reg-required follow-up. Sub-q1's
conditional-Z verdict now reads "median-split rejection on congestion
holds at α = 0.05; continuous fit is underpowered to sharpen at
α = 0.05 but direction is consistent across all 7 pnodes and across
the threshold sweep." Truthful and defensible.

### 2. LMP-components decomposition *(DONE 2026-05-14)*

> **Reframing note.** Original item was "response-variable sensitivity
> diagnostic" (why median-split rejects on congestion but not total_lmp).
> During design (2026-05-14, plan commits `a789e75` + `02e40e9`) this
> was sharpened into a principled 4-component decomposition: instead
> of comparing total_lmp vs congestion as black boxes, decompose
> total_lmp = system_energy + congestion + marginal_loss and test the
> conditional-Z mechanism on each component separately. The
> "cancellation hypothesis" — system_energy carries the ORDC-direction,
> congestion carries the opposite — explains the total_lmp null result
> as components-canceling. Pre-reg at `docs/decisions.md § 2026-05-14
> — Pre-registration: LMP-components decomposition (sub-q1 closure
> item #2)`.

**Status:** Closed by `docs/decisions.md § 2026-05-14 — Application of
#2 pre-reg: LMP-components decomposition verdict` (commit `01ebbd8`).

**Closure outcome.** Rule 2 dispatch: **`underpowered_pos_direction`**
on the headline `system_energy` test. shape_diff = +0.257, CI
[−0.543, +0.617]. Direction is consistent with ORDC's predicted
heavier-tail-at-HIGH-Z; magnitude does not clear α=0.05 at the
available n_per_half=51 (one above the Rule 4 convergence floor).

Supplementary descriptive evidence:
- Primary cluster: `congestion` −0.133, `marginal_loss` −0.156 (both
  CIs span 0; direction OPPOSITE to system_energy → the
  cancellation-hypothesis pattern descriptively).
- Cross-pnode `system_energy` is structurally invariant across DOM
  pnodes (zone-wide LMP-decomposition property), NOT independent
  replication. Cross-pnode `congestion` is uniformly negative across
  4 labeled pnodes — direction-consistent, magnitude-unsupported.
- Threshold sweep p90→p95 on `system_energy`: 50× magnitude jump
  flagged as **sample-fragile near GPD MLE convergence floor**, not a
  clean threshold-effect curve.

**Paper-level implication:** direction-level support for the
cancellation hypothesis without magnitude confirmation. Paper headline
framing for sub-q1 deferred to advisor meeting (item #5 below).

### 3. τ = 0.99 secular sign-flip investigation *(DONE 2026-05-14)*

**Status:** Closed by `docs/decisions.md § 2026-05-14 — Sub-q1 item
#3: τ=0.99 secular sign-flip diagnostic (descriptive)` (commit
`72456bb`).

**Closure outcome — case (b) sparse-tail bootstrap artifact at τ=0.99.**

The three-layer year-FE diagnostic (Layer 1 raw per-year p99, Layer 2
year-dummy bootstrap, Layer 3 secular-component bootstrap as
`primary_z_slope − year_fe_z_slope`) gave:

- **Layer 1 directly contradicts case (a) "grid improvement."** 2026
  partial-year p99 is **4–10× any prior year** across all DOM pnodes
  (e.g., primary 2026 p99 = 480 vs 2023 p99 = 43). The trajectory is
  upward, not downward.
- **Layer 3 at τ=0.99: all 7 pnodes have secular component CIs
  spanning 0.** The diagnostic cannot distinguish real secular trend
  from noise at the tail. Combined with Layer 1, the evidence supports
  case (b) "sparse-tail bootstrap artifact" — the τ=0.99 QR-full sign
  flip reported in Spec B is a sparse-tail estimator instability, not
  an interpretable trend.

**New finding the closure roadmap did not anticipate.** At
τ=0.90/0.95 the secular component is **positive** with CIs **excluding
0 on 5/7 non-Ashburn pnodes** (e.g., primary @ τ=0.95: secular
component +0.168, CI [+0.04, +0.28]). `primary_z_slope >
year_fe_z_slope` means the primary spec reports a larger response than
year-FE; year-FE has absorbed something correlated with year. The
honest framing: year-FE absorbs everything year-correlated (weather,
generation mix, topology, AND 2026 partial-year selection) without
separately identifying secular drift vs the 2026 event. **Magnitude
attribution is unresolved by this diagnostic.**

**Sub-q2 (JLARC projection) implication.** Use **year-FE-residualized
slope at τ=0.95** as conservative bound for projection. Defer τ=0.99
projection until a longer historical window stabilizes the tail.

### 4. Ashburn TX1 q=0.99 anomaly diagnostic *(DONE 2026-05-14)*

> **Sharpening note.** The original framing was about TX1's τ=0.95
> QR-full z_slope. After Spec B (2026-05-14) the focus shifted to TX1's
> **q=0.99 sign flip on the Spec B continuous-fit β₁** (positive +0.093
> at q=0.99 vs negative at q=0.90/0.95/0.995). The LOO + TX2
> cross-check tests case (b) "outlier-driven over-fit" directly.

**Status:** Closed by `docs/decisions.md § 2026-05-14 — Sub-q1 item #4:
Ashburn TX1 99th-pct anomaly diagnostic (descriptive)` (commit
`fd0065c`).

**Closure outcome — case (b) RULED OUT; cases (a) and (c) remain
candidate explanations.**

- **TX1 q=0.99 LOO is rock-solid.** Full β₁ = +0.0932; LOO mean
  +0.0931, stdev 0.0028, range [+0.083, +0.101]; **0 of 175 LOO refits
  change sign.** Dropping any single exceedance does not flip the
  positive direction. Case (b) "outlier-driven over-fit" RULED OUT.
- **TX2 q=0.995 shows 30% sign-change refits**, validating the LOO
  methodology can detect fragility. The TX1 q=0.99 0-sign-change
  result is meaningful as fit-stability evidence, not noise floor.
- **TX2 q=0.99 cross-check is directional, NOT independent.** TX2
  β₁ = +0.0232 (same positive direction as TX1), LOO 0/175
  sign-change. But TX1 and TX2 are co-located substation pnodes with
  the same ~2y coverage window — directional confirmation only.
- **Caveats beyond LOO** documented in the entry: temporal clustering
  of q=0.99 exceedances (LOO cannot detect), selection effects from
  the proposal-filter, generative-model misspecification (Spec B LRT
  p=0.000 at TX1 q=0.99 suggests strong non-linearity).

**Paper-level implication.** Framed as **"a robust unexplained Ashburn
q=0.99 anomaly worth investigating,"** NOT a paper-headline mechanism
finding. Methods-section subsection with explicit open-questions
framing (temporal clustering check, spline-form re-fit, mechanism
investigation). Do not lead the paper with this finding.

**Open follow-ups** (out of scope for sub-q1 closure, but flagged for
advisor + paper-writing):
- Temporal-clustering check on TX1's q=0.99 exceedances (load panel,
  inspect exceedance-set timestamps).
- Spline-form re-fit at TX1 q=0.99 (LRT p=0.000 motivates).
- Independent Ashburn-like 35 kV pnode at a different substation —
  not available in current dataset.

### 6. Direct Z → LMP tail-risk characterization *(added 2026-05-14 night)*

> **Why this item exists.** Items #1-4 are **mechanism tests** — they
> ask *why* LMP gets crazy at high Z (ORDC scarcity, cancellation
> hypothesis, components decomposition). The user's stated sub-q1
> framing — *"what range of load variance causes LMP to essentially
> go crazy"* — is a **descriptive characterization** of where in
> Z-space LMP's tail behavior lights up. The mechanism tests imply
> the answer (positive z_slope at τ=0.95 means higher Z → higher
> conditional 95th-pct LMP) but don't directly produce the artifact
> the framing wants.

**Status:** Added 2026-05-14 night. Design pending brainstorm; not yet
executed.

**What it produces (target):** A binned or smooth characterization of
the conditional Z → LMP distribution, specifically focused on the
upper tail. Final form to be determined in brainstorm; candidate
outputs include:

- Z-bin × P(LMP > $threshold) table, for several thresholds (e.g.,
  $200, $500, $1000) — answers "in which Z range does P(crazy LMP)
  exceed N%?"
- Z-bin × conditional quantile of LMP (50th, 95th, 99th) — answers
  "at what Z does the 99th-pct LMP cross $X?"
- Tail expectation E[LMP | LMP > cutoff, Z bin] — answers "given
  that LMP is already in the tail, how much worse is it at high Z?"

**Why before item #5 (advisor meeting):** The advisor sees the
complete sub-q1 picture (mechanism + descriptive characterization)
before weighing in on paper framing. Calendar latency on advisor
scheduling absorbs the implementation time. If item #6 surfaces an
unexpected pattern (e.g., the "crazy region" is at LOW Z, opposite
the proposal's prediction), advisor framing shifts.

**Design decisions pending brainstorm:**
- Z binning strategy (quantile vs equally-spaced MW/min vs
  physically-meaningful breakpoints from ORDC-curve documentation)
- "Crazy" cutoff(s) — $200 / $500 / $1000 thresholds; conditional
  quantile-based; tail expectation
- Response variable(s) — total_lmp, congestion, components-decomposed
- Pnode scope — primary cluster only, all 7, voltage-stratified
- Filter — proposal-filter (consistency with prior mechanism work)
  vs raw panel (a separate descriptive view)
- Pre-reg discipline — descriptive only, or pre-committed binning
  + thresholds to avoid post-hoc cherry-picking (per the discipline
  used in items #2-4)
- Output artifact — table, plot, both; static, interactive

**Effort estimate:** Half-day implementation; brainstorm + plan add
~1 hour.

**Closes:** the direct empirical answer to the user's stated sub-q1
framing. Items #1-4 stay as mechanism supporting evidence in the
paper. Without item #6, the paper would have substantial *why*
evidence but no clean *where* artifact answering the user's
own question.

### 5. Advisor meeting (Prof Wei / Lihui)

**Status:** Agenda at
`docs/plans/2026-05-14-advisor-meeting-agenda.md`. 8 items;
critical for sub-q1 closure are items 1 (framing), 2 (bootstrap
p-value semantics), 5 (τ=0.99 sign flip), 6 (Ashburn TX1).

**Why:** Paper-publishable confidence requires advisor sign-off on:
- Framing of the rejected-mechanism finding (item 1 in agenda — back
  on the table after pnode-labeling correction).
- Bootstrap p-value heuristic ASL semantics (item 2 — methodological
  defensibility for peer review).
- Item 1's framing choice influences items 3 (QR-full extrapolation
  for projection), 7 (JLARC design approval).

**Best timing:** After Spec B completes (so the meeting has the full
empirical picture). In parallel with items 3 and 4 (the diagnostics
don't block).

**Effort estimate:** 1-2 hours meeting prep + ~1-hour meeting + 2-3
hours post-meeting integration. Plus calendar latency for scheduling.

**Closes:** items 1, 2, 5, 6 from the advisor agenda; framing
decisions that any of items 1-4 above might need re-doing.

## Sequencing

```
                                ┌──── 3. τ=0.99 ✓ ────┐
1. Spec B ✓ ─→ 2. Components ✓ ─┤                     │── 6. Z-bin tail-risk ─→ 5. Advisor meeting ─→ paper-ready sub-q1
                                └──── 4. Ashburn ✓ ───┘
```

- Items 1–4 completed in a single sub-q1 batched-diagnostics push
  (2026-05-14). Original "3-5 weeks" estimate compressed by batching
  items 2, 3, 4 into one production run + one round of application
  entries (commits `01ebbd8` / `72456bb` / `fd0065c`).
- Items 6 and 5 remain. Item 6 (added 2026-05-14 night) is the
  direct descriptive answer to the user's stated sub-q1 framing —
  sequenced before item 5 so the advisor sees mechanism +
  description together. Agenda for item 5 needs updating to reflect
  the moderate-τ secular finding (new from item
  3) and the Ashburn q=0.99 anomaly framing (sharpened from item 4).

## What "paper-publishable" means here

The bar is "the methodology section + results section can survive
peer review." Concretely:

- Each finding has either a clean rejection (CI excludes 0, bootstrap
  p < 0.05 family-wise where applicable) or a clear "test was
  underpowered" acknowledgment with reported bounds.
- Multiple-testing correction is either applied where it matters or
  the singular-headline framing is pre-committed (not post-hoc
  selected).
- Open methodology questions are documented with stated limitations,
  not silently elided.
- Advisor has reviewed and sign-off-ed on the framing.

If Spec B comes back inconclusive (β₁ CI spans 0), the truthful
finding is "the data does not support a continuous shape-Z
dependence at our window size" — still publishable, just a different
paper than if β₁ is significant.

## How this roadmap is maintained

Updated when:

- Any of items 1-4 completes — mark "DONE" with link to the closing
  decisions.md entry + commit SHA.
- Advisor meeting produces sign-off — mark item 5 DONE + link the
  resulting decisions.md entry.
- A new sub-q1 gap is discovered — add as item 6+ with rationale.
- A planned item is descoped — note the reason and the implications
  for the closure bar.

## Out of scope of this roadmap

- **Sub-question 2 (JLARC projection layer).** Independent track.
  See `docs/plans/2026-05-14-jlarc-projection-design.md` for that
  status.
- **Paper-figure generation.** Deferred until sub-q1 closure
  (decision recorded 2026-05-14 in-session: "Let's drop the slide
  deck entirely until we fully answer problem 1").
- **Code-side improvements to the orchestrator** (running
  conditional-Z battery across all pnodes by default, etc.) — these
  are quality-of-life refactors, not sub-q1 closure work.
