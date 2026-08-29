# Advisor Meeting Agenda — Post-2026-05-14 State

> **Status:** Drafted overnight 2026-05-14. Consolidates the open
> methodology, framing, and scope questions accumulated across the
> 2026-05-13 and 2026-05-14 decisions.md entries plus the JLARC
> projection-layer design. Some items are flagged `[FILL]` pending
> the conditional-Z robustness battery's verdict — when that lands,
> this doc gets a final pass before the meeting.

## Audience

- Prof Ermin Wei (research advisor, NU EECS — energy markets / optimization)
- Lihui (PhD student, energy market analysis)

## Purpose of the meeting

Get input on three categories of questions that an undergraduate analyst
cannot resolve unilaterally:

1. **Framing the headline result for the paper.** The proposal's
   originally-stated mechanism is empirically rejected; the paper's
   central claim needs to be rewritten before any results can be
   communicated. Multiple framings are defensible.
2. **Methodology details that affect external defensibility** (e.g.,
   whether the bootstrap p-value semantics + Holm correction we've
   applied are appropriate; whether the QR-full linear extrapolation
   is acceptable for the projection layer).
3. **Scope decisions for the remaining work** (e.g., whether to
   pursue Spec B if triggered; whether the Ashburn negative point
   estimate deserves a dedicated diagnostic).

## State of the analysis as of advisor meeting

### Sub-question 1 — "where does the response shift"

The smooth-curve diagnosis (2026-05-13 follow-up entry) established
that there is no single MW/min threshold — the load-volatility →
LMP relationship is smooth, not piecewise. The 2026-05-14 Strategy
C production run produced QR-full and GPD characterizations of that
smooth response. The 2026-05-14 conditional-Z robustness battery
(pre-registered + executed same day) tested whether the headline
median-split rejection of the proposal's heavier-tail-at-high-Z
hypothesis generalizes.

**Headline findings on sub-question 1:**

- QR-full z_slopes at τ=0.90 and 0.95 are robustly positive
  (`[0.325, 0.462]` and `[0.428, 0.761]`).
- τ=0.99 CI crosses zero (`[−0.075, 1.194]`) — bootstrap CI is the
  load-bearing inference, not the asymptotic SE.
- `total_lmp` response is ~4× the congestion response at τ=0.95 —
  direct support for the ORDC mechanism.
- No Loudoun-specific effect on the full panel (Loudoun cluster ≈
  OX ≈ BRISTERS in z_slope at τ=0.95).
- GPD median-split conditional-Z mechanism test at 95th-pct LMP
  threshold: `shape_diff = −0.180`, bootstrap CI
  `[−0.371, −0.044]`. **The proposal's central
  heavier-tail-at-high-Z hypothesis is rejected at this scope.**
- Conditional-Z robustness battery (Spec A quartile-split + Spec C
  99th-pct + Spec F within-filter + Holm correction):
  **[FILL battery verdict from `outputs/gpd/conditional_z_robustness.json`
  when Task 5 finishes.]**

### Sub-question 2 — "when does projected growth push past it"

**Reframed** (after smooth-curve diagnosis): instead of "year when
projected DC growth crosses a single threshold," the new framing is
"year when projected DC growth shifts the load-volatility distribution
such that current rare high-LMP hours become routine."

**Status:** Design spec complete and committed at
`docs/plans/2026-05-14-jlarc-projection-design.md`. Implementation
plan-writing is **GATED on user approval of the design**.

**Design highlights:**
- Primary metric: `exceedance_hours_per_year` above $850/MWh
  (externally-anchored ORDC first-step penalty).
- Secondary metric: quantile-shift year (95th-pct → 50th-pct of
  projected Z distribution).
- Scaling: DC-attributed (primary if `dc_share_of_load` available
  ≈ 0.26 from JLARC Table 4-1), proportional as fallback.
- Linear extrapolation of QR-full slopes is the central
  load-bearing assumption (flagged with `extrapolation_warning` at
  2× historical Z_max).

**Data acquisition:** JLARC Rpt598-2 numbers extracted overnight at
`docs/plans/2026-05-14-jlarc-rpt598-key-figures.md`. Draft
`growth_scenarios.yaml` populated with three scenarios derived from
the JLARC report's Figure 3-3 (1.95× / 2.62× / 2.90× by 2040).

## Agenda items

### Item 1 — Headline framing (HIGH PRIORITY — REVISED 2026-05-14 late-night)

**Update:** The original framing options here were built on the prior
2026-05-14 production-findings entry's reported conditional-Z
rejection (`shape_diff = -0.18, CI [-0.371, -0.044]`). On the **actual
current panel + code**, that rejection does NOT reproduce — the
deterministic re-run produces `shape_diff = -0.09, CI [-0.249, +0.047]`
(CI straddles 0). The conditional-Z robustness battery's verdict is
**not a rejection** but an inconclusive at all three tested scopes
(see the 2026-05-14 application-of-pre-reg entry in decisions.md for
the correction + full battery results).

The framing question changes accordingly. The proposal's tail-shape
prediction is neither confirmed nor rejected; the conditional-Z
mechanism test is **underpowered to discriminate** at α=0.05 on this
window. **Two candidate framings now:**

A'. **Positive findings carry the paper.** QR-full z_slopes at
   moderate τ (z_slope = 0.39, 0.58 at τ=0.90, 0.95 — robust to
   bootstrap) and `total_lmp` ≈ 4× congestion at τ=0.95 (direct
   ORDC mechanism support) are the headline. The conditional-Z
   tail-shape test is reported as a methodologically-honest "we
   tried this specific test and it's underpowered to discriminate
   at the available sample sizes" — not a finding either way.
   Defensible because the positive findings ARE robust and stand
   on their own.

B'. **Reframe the central question.** The proposal's specific
   tail-shape prediction is the wrong question for this data; the
   composite LMP-vs-Z response is smooth, so a tail-shape mechanism
   test is testing the wrong feature of the relationship. The
   paper's central claim shifts to *"moderate-quantile response ×
   ORDC mechanism × distribution shift under projected growth"* —
   which centers QR-full + sub-question 2's JLARC projection layer
   as the paper's contribution. The conditional-Z test result
   becomes a discarded methodology that further evidenced why the
   smooth-curve framing is appropriate.

**What we need from the advisor:** Pick A' or B' (or propose a
hybrid). A' is conservative — keeps the paper close to what we have.
B' is bolder — pivots the paper's contribution toward the projection
layer, which would put sub-question 2's JLARC work in the
critical path for the paper rather than as a follow-up.

### Item 2 — Bootstrap p-value semantics + Holm correction defensibility (METHODOLOGY)

The orchestrator uses an empirical bootstrap "achieved significance
level" p-value: `p_two_sided = 2 × min(P(arr ≤ 0), P(arr ≥ 0))` over
bootstrap replicates. This is a heuristic, not a formal
hypothesis-test p-value. The Holm correction we apply across
A/C/F inherits this heuristic status.

**Questions for advisor:**

- Is this convention acceptable for the paper? Standard in extreme-value
  / GPD literature?
- Should we run a parametric bootstrap (resampling from the fitted GPD)
  alongside the pair-bootstrap for comparison?
- Should we report adjusted CIs (e.g., BCa bootstrap) instead of
  empirical percentile CIs?

### Item 3 — QR-full linear extrapolation for projection layer

The projection layer applies QR-full slopes (fitted on historical
Z range, max ~7.6 MW/min) to projected Z distributions that extend
to 2-3× the historical max. This is linear extrapolation into
never-observed territory.

**Questions for advisor:**

- Is "linear in Z" a defensible local assumption, or should we fit
  a more flexible response curve (splines, GAM)?
- The design's mitigation is a code-level `extrapolation_warning`
  flag when projected Z_max > 2× historical. Is the 2× cutoff
  appropriate?
- Should we cap the projected Z distribution at some plausibility
  ceiling (e.g., DOM peak load capability), or let it extrapolate
  freely with the warning?

### Item 4 — Spec B (continuous ξ(Z) regression) trigger and scope

Per the 2026-05-14 conditional-Z pre-reg, Spec B is gated on Spec
A returning non-monotone or inconclusive primary CI. **[FILL: was
B triggered? If yes, what spec should it follow?]**

Even if B is not triggered tonight, the question of whether to fit
ξ as a continuous function of Z (rather than discrete splits) is
a live methodology question for the paper.

### Item 5 — τ=0.99 secular sign flip — is it real?

QR-full year-FE decomposition at τ=0.99 shows the secular trend
component is −74% of the primary trend (i.e., the 99th-pct LMP is
trending *downward* over 2022-2026 even as DC growth continues).

**Hypotheses:**

1. **Real grid improvement.** PJM ORDC reform + investment in
   transmission is genuinely dampening extreme tails. Implication
   for projection: future LMP_τ=0.99 may continue to fall even
   under aggressive DC growth, partially offsetting the
   contemporaneous volatility response.
2. **Sparse-tail artifact.** At τ=0.99, the year-FE decomposition
   has very few observations per year × quantile cell; the sign
   flip could be noise.
3. **Window-specific artifact.** 2022-2026 is a 4-year window;
   secular trends within it are not stable estimates.

**Questions for advisor:** which hypothesis is most plausible
given the prior literature on PJM grid trends? Should we test
further (e.g., split sample, examine the year-FE residuals
directly)? Implication for the projection layer: should the
projection apply *contemporaneous* z_slopes (which would project
LMP_τ=0.99 to keep rising under DC growth) or *primary* (full)
z_slopes (which include the secular dampening — but at τ=0.99 the
sign flip makes the primary slope smaller)?

### Item 6 — Ashburn TX1 negative point estimate

QR-full z_slope at τ=0.95 for Ashburn TX1 (one of two
distribution-side pnodes) is −0.604 (CI [−1.22, 0.52]). The wide
CI crosses zero, but the median sign is wrong for a DC-influenced
distribution-side pnode.

**Question for advisor:** worth a focused diagnostic (e.g., examine
Ashburn TX1's response curve directly), or is the wide CI sufficient
to set aside? Implications for paper: if Ashburn TX1 is genuinely
behaving differently from other DC-adjacent pnodes, that's a
methodologically interesting finding worth investigating; if it's
noise, the distribution-side pnodes become a side-note in the paper.

### Item 7 — JLARC projection layer design approval

The JLARC projection layer design is at
`docs/plans/2026-05-14-jlarc-projection-design.md`. It has 8 open
questions for user review (listed in the design's "Open questions
for user review" section). The most consequential ones:

- Primary metric framing: `exceedance_hours_per_year` above $850 (chosen
  default) vs. quantile-shift framing (originally proposed).
- Whether to use DC-attributed scaling (primary if dc_share=0.26 is
  acceptable) or proportional scaling (strong-claim fallback).
- Growth-curve shape between 2025/2040 anchors: linear (default) vs.
  exponential CAGR.
- Reference year: 2025 (default, uses full panel) vs. 2026 (panel end).

**What we need from the advisor:** sign-off on the design's primary
methodological choices before the implementation plan is written.
(This is the gate that's currently blocking the plan-writing step.)

### Item 8 — Paper section structure + claim sequencing

Mid-priority unless the advisor wants to start narrative work
early. The paper has three "natural" sections after introduction:

1. **Method:** Strategy C + conditional-Z battery + projection
   layer methodology.
2. **Results:** QR-full slopes, GPD threshold sweep, conditional-Z
   rejection, projection trajectories.
3. **Implications:** What the rejected-mechanism finding means for
   policy + future research.

The "results" section's narrative depends heavily on the framing
chosen in Item 1. Worth deferring until that decision is made.

## Carryover items (not for this meeting, just status)

- Ashburn LOAD historic backfill (~8.5h overnight pull) — still
  deferred; advisor can re-decide whether the symmetry argument
  warrants it.
- Continuous ξ(Z) parametric model — see Item 4.
- Paper-ready figure generation — separate notebook task, will
  start after framing decisions in Items 1, 3, 5.

## Suggested decisions to bring out of the meeting

1. **One sentence on framing** — Item 1. Either A, B, C, or a
   crystallized fourth option.
2. **Yes/no on bootstrap p-value semantics** — Item 2.
3. **Methodology for response curve extrapolation** — Item 3.
4. **JLARC design approval (or changes)** — Item 7. Unblocks
   plan-writing.
5. **Priority ordering of remaining methodological investigations**
   — Items 4, 5, 6. Some are paper-blocking, some are nice-to-have.
