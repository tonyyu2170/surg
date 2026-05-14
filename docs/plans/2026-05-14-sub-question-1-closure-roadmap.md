# Sub-Question 1 Closure Roadmap

> **Status:** Drafted 2026-05-14 to document the full set of remaining
> work needed to bring sub-question 1 — "what is the critical volatility
> threshold of data center load variance that triggers a non-linear
> phase transition in DOM congestion pricing?" — to **paper-publishable
> confidence**. Brainstormed scope + sequencing with the user in-session.

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

### 1. Spec B — Continuous ξ(Z) regression *(IN PROGRESS)*

**Status:** Design spec at
`docs/plans/2026-05-14-spec-b-continuous-xi-z-design.md` (commit
`3753b97`). Pre-reg entry pending in this commit. Implementation
plan + execution next.

**Why first:** The conditional-Z battery's pre-reg explicitly triggers
Spec B on Spec A's non-monotone outcome. Without B, the battery's
verdict is "extensions inconclusive due to power" — not a clean
answer for the paper.

**What it produces:** Non-stationary GPD fit with both σ(Z) and ξ(Z)
varying as functions of Z. Linear form gives the headline β₁ slope
(+ bootstrap CI + two-sided p); 3-knot natural cubic spline form
characterizes any smooth non-monotonicity. Full threshold sweep
(90/95/99/99.5) × 7 pnodes × 2 forms.

**Headline claim for paper:** primary congestion @ 95th-pct, linear
β₁. Decision rules locked in pre-reg entry.

**Effort estimate:** 2-3 focused sessions matching conditional-Z
battery cadence (brainstorm + pre-reg + plan + subagent-driven
execution + application-of-pre-reg entry + FF-merge).

**Closes:** the central pre-reg-required follow-up. Without this,
sub-q1's conditional-Z verdict reads "underpowered at extension
scopes."

### 2. Response-variable sensitivity diagnostic

**Status:** Not started. Naturally follows Spec B (B's output
informs which response shows the cleanest signal).

**Why:** The 2026-05-14 application-of-pre-reg entry surfaced an
asymmetry: median-split conditional-Z rejects on **congestion**
(proposal's stated variable) but is inconclusive on **total_lmp**
(Strategy C secondary). Both are on the same Loudoun cluster, same
Z. Why does the test discriminate one but not the other? Either:

- (a) The total_lmp's larger mean-quantile response (4× the
  congestion slope) "saturates" the tail's Z-dependence — the
  vertical-shift effect dominates the shape effect.
- (b) The conditional-Z test's sensitivity to scale-vs-shape
  confounding differs between the two responses.
- (c) Random noise — the discrepancy is sample-size-specific.

**What it produces:** A focused empirical investigation (not a new
fit method). Outputs: a methodology paragraph for the paper
explaining the asymmetry, with supporting decomposition of
tail-shape vs. tail-rate Z-effects.

**Effort estimate:** 1 session brainstorm + small implementation
(2-3 hours).

**Closes:** the "response-variable sensitivity" item flagged in the
2026-05-14 application entry. Required for paper to honestly report
which response carries the mechanism finding.

### 3. τ = 0.99 secular sign-flip investigation

**Status:** Open since 2026-05-14 production-findings entry. Not
addressed by any in-flight work.

**Why:** The QR-full year-FE decomposition at τ=0.99 shows the
**secular** trend component goes the OPPOSITE direction from the
contemporaneous Z response. 99th-pct LMP is trending *downward*
over 2022-2026 even though DC growth and contemporaneous z_slope
are both positive. Three plausible interpretations:

- (a) **Real grid improvement.** PJM ORDC reform + transmission
  investments are genuinely dampening extreme-tail LMP over time.
  This matters for the projection layer (sub-q2): if real, the
  projection should apply the *contemporaneous* z_slope rather
  than the primary (full) z_slope at τ=0.99, since the secular
  trend would otherwise offset the DC-driven volatility effect.
- (b) **Sparse-tail artifact.** At τ=0.99 the year-FE decomposition
  has very few observations per year × quantile cell; the
  sign-flip could be noise from a small effective sample.
- (c) **Window-specific.** 2022-2026 is a 4-year window; secular
  trends inside it are not stable estimates.

**What it produces:** Diagnostic analysis — split the panel by year,
examine year-FE residuals, possibly bootstrap the year-FE
decomposition. Output: a paragraph in the paper interpreting the
sign-flip (or rejecting it as artifact).

**Effort estimate:** 1 session (~2-3 hours).

**Closes:** the τ=0.99 question in the 2026-05-14 production-findings
entry's open list. Important for the JLARC projection layer's choice
of z_slope (primary vs year-FE).

### 4. Ashburn TX1 diagnostic

**Status:** Open since 2026-05-14 production-findings entry.

**Why:** The QR-full z_slope at τ=0.95 for Ashburn TX1 is −0.604
(CI [−1.22, +0.52], spans 0). The wide CI means the bootstrap can't
reject zero, but the median sign is the *wrong* direction for a
DC-adjacent distribution-side pnode. Either:

- (a) **Real distribution-side physics** — at 35 kV, the load-LMP
  response may differ from the 500 kV transmission cluster's.
- (b) **Noise** — wide CI consistent with no effect.

**What it produces:** Focused diagnostic — examine Ashburn TX1's
LMP-vs-Z scatter, check for outlier influence, possibly compare
with Ashburn TX2 (the second distribution-side pnode).

**Effort estimate:** 1 session (~2 hours). Could be done in parallel
with item 3.

**Closes:** the Ashburn TX1 question. Methodology footnote for paper;
if distribution-side physics is real, may inform future work on
distribution-side pnodes.

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
                          ┌──── 3. τ=0.99 ────┐
1. Spec B ─→ 2. Resp-var ─┤                   │── 5. Advisor meeting ─→ paper-ready sub-q1
                          └──── 4. Ashburn ───┘
```

- Items 3 and 4 are independent of 1 and 2 — can be done in parallel.
- Item 5 (advisor meeting) is best after 1 completes; items 2, 3, 4
  can happen before or after the meeting.
- Total wall time estimate: **3-5 weeks** for paper-publishable
  confidence, depending on advisor meeting scheduling.

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
