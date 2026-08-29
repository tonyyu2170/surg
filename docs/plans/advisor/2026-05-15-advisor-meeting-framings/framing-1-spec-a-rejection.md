# Framing 1: Spec A Median-Split Rejection

**Headline thesis:** A pre-registered median-split GPD test on the proposal's
own variable (DOM-zone congestion price, p95 exceedances) rejects the
ORDC-motivated "high load-variance produces a heavier-tailed congestion
regime" hypothesis at α=0.05, and rejects it in the *opposite* direction
the proposal predicted — establishing that the conjectured volatility-driven
phase transition is not the mechanism generating DOM-zone congestion tails.

## TL;DR
The paper pre-registers and executes a clean test of the SURG proposal's
central conjecture and reports the rejection. The contribution is not a
new finding *for* the ORDC mechanism — it is a credible falsification *of*
a widely-assumed mechanism, supported by (i) a single α=0.05 rejection on
the proposal's own response variable and (ii) direction-consistent
triangulation across an independent continuous specification and across
all seven target pnodes. The reframing implication: data-center volatility
is not a phase-transition driver of congestion-tail behavior on the post-
cap DOM zone; mechanism work should pivot to mid-quantile conditional
response and to the broader system-energy component, not to tail shape.

## Why this framing is the right one
- It tests the proposal's *literal* hypothesis (heavier congestion tail at
  high Z) on the proposal's *literal* response (DOM-zone congestion LMP)
  with a method (split-sample GPD shape comparison) whose null directly
  encodes "tail behavior is invariant to Z." Every other framing tests a
  proxy of the proposal, not the proposal itself.
- It is the only finding in the project that crosses the conventional
  α=0.05 bar on a pre-registered hypothesis. Items #2 and #3 are
  underpowered or directionally noisy; items #6/#9 are descriptive.
- The rejection is corroborated, not isolated: Spec B's continuous ξ(Z)
  fit is direction-consistent (β₁ < 0 at p95 on every one of 7 pnodes;
  shape_diff < 0 on every pnode under median-split), and the LRT detects
  significant non-linearity at p90 (p=0.007). Triangulation across
  independent specifications on the same direction is the strongest
  evidentiary structure available without a second dataset.
- The "wrong direction" is *informative*, not embarrassing: it has a
  clean mechanistic reading (ORDC adders are saturating in the high-Z
  regime, not producing a new heavy-tailed branch), which generates
  testable implications for downstream work.

## Supporting evidence
- **Primary (evidence #2):** Spec A median-split GPD on congestion @ p95,
  n=789/half. shape_diff = −0.180, 95% CI [−0.371, −0.044]. Sign of CI
  excludes zero; direction is opposite to proposal.
- **Triangulation #1 (evidence #3):** Spec B continuous ξ(Z) at p95
  congestion, β₁ = −0.008, CI [−0.021, +0.003]. Underpowered for α=0.05
  but same sign on every one of 7 pnodes. LRT p=0.007 at p90.
- **Triangulation #2 (evidence #1):** Smooth-curve diagnosis (2026-05-13)
  rules out a literal step-function transition at any threshold ĉ. Spec A
  rejection is consistent with a smooth response whose tail *thins* with Z.
- **Scope discipline (evidence #7):** In-filter direct Z → LMP shows
  P(LMP > $250 | top Z decile) = 0 across all 7 pnodes (n=2,027). The
  high-Z regime within the proposal-filter scope simply does not generate
  the "crazy LMP" events the ORDC mechanism would predict.

## The strongest counter-argument
A naive read of the result is "you falsified your own hypothesis — what
is the contribution?" Specifically, an advisor will note that (i) the
direction is opposite to what motivated the grant, (ii) Spec B is
underpowered at α=0.05 so the headline rests on a single split-sample
test with n=789/half, and (iii) the QR-full year-FE finding (5/7 pnodes,
positive z_slope at τ=0.95 with CIs excluding 0; total_lmp ≈ 4× congestion)
appears to *support* the ORDC mechanism at the conditional-quantile level,
which contradicts the headline.

## Rebuttal
The contribution is the credibility of the rejection, not the direction
of the prior. (i) A clean α=0.05 rejection of a pre-registered hypothesis
on a pre-specified response is a stronger empirical claim than any
direction-confirming positive finding the project produced — none of the
positive findings clear the same evidentiary bar. (ii) The single-test
worry is mitigated by triangulation: Spec B is direction-consistent on
*all 7* pnodes for both β₁ and shape_diff; the joint probability that 7
independent pnodes line up against a true null is small even before any
formal pooling, and the LRT independently flags non-linearity at p90.
(iii) The QR-full positive finding is not a contradiction — it is a
distinct claim about a different statistical object (see next section).

## Anticipated advisor pushback
1. **(Wei, most severe) "Single rejection at α=0.05 with n=789/half on
   one threshold is fragile — what's the threshold-sensitivity?"** Answer:
   the result holds on the same direction across thresholds (Spec B
   continuous fit at p95, LRT non-linearity at p90, all-pnodes sign
   consistency). The α=0.05 rejection is anchored, not stress-tested at
   adjacent quantiles in the headline; pre-registration constrains how
   far we can push this without inviting forking-paths concerns. Defensible
   move: report the p90/p95/p99 trajectory in supplementary results.
2. **(Lihui) "QR-full positive at τ=0.95 contradicts the headline."**
   Answer: it doesn't — the conditional-quantile slope and the tail-shape
   parameter measure different things (location of the 95th percentile vs.
   curvature of the exceedance distribution above it). See "competing
   findings" section. The clean way to write this is "Z shifts the
   conditional 95th percentile up but does not heavy-tail the distribution
   above it."
3. **(Wei) "Why is direction opposite to the proposal? Mechanism story?"**
   Answer: the saturation reading — at high Z, ORDC adders are already
   active and the marginal additional MW/min of volatility no longer
   produces a discontinuous reserve-shortage event because reserves are
   already binding. The thin-tail-at-high-Z direction is exactly what a
   saturation regime would produce.
4. **(Lihui) "Is the median-split arbitrary?"** Answer: yes by design —
   pre-registered split is the only way to get a clean α=0.05 test
   without forking. The continuous Spec B fit is the supplementary check
   that the split isn't gaming the cut.
5. **(Wei) "Ashburn TX1 q=0.99 anomaly? Item #6 null?"** These don't
   touch the headline directly; address briefly under "leaves unaddressed."

## Proposed paper title + abstract (~200 words)

**Title:** Load Volatility Does Not Heavy-Tail DOM-Zone Congestion: A
Pre-Registered Falsification of the ORDC Phase-Transition Hypothesis

**Abstract:** Rapid data-center buildout in the PJM Dominion zone has
motivated concern that load-side volatility (Z = |ΔL|/Δt, MW/min) drives
the zone past a heavy-tailed congestion-pricing regime via the ORDC
reserve-shortage mechanism. We test this hypothesis directly. Using 3.6
years of post-cap hourly DM2 data (2022-10 → 2026-05; 31,536 obs across
seven nodal injection points) and a pre-registered median-split GPD
specification on p95 congestion exceedances, we find shape_diff =
−0.180 (95% CI [−0.371, −0.044]) — a rejection of the volatility-driven
heavy-tail hypothesis at α=0.05, in the *opposite* direction predicted by
the ORDC mechanism. A continuous ξ(Z) regression triangulates the
direction across all seven pnodes (β₁ < 0 in every case) with a likelihood-
ratio test for non-linearity at p90 (p=0.007). The result is consistent
with ORDC-adder saturation, not with phase-transition behavior, and shifts
the empirical question from tail shape to conditional location, where a
positive Z → 95th-percentile-LMP relationship persists. Implications for
JLARC-projected 2030 load growth and DOM-zone reliability investment are
that congestion-tail risk is unlikely to scale super-linearly with
volatility within the post-cap operating regime studied.

## What this framing leaves unaddressed
- **Ashburn TX1 q=0.99 sign-flip (evidence #6).** Survives LOO
  (0/175 sign-changes). Real, isolated, mechanism unknown. Footnoted
  rather than headlined; sets up future work.
- **Item #2 system_energy +0.257 shape_diff (CI spans 0).** The component
  decomposition hints that *energy*, not congestion, may carry whatever
  ORDC-direction signal exists. Out of scope for the headline test (which
  is on congestion); footnoted as motivation for follow-on work.
- **Item #9 post-hoc top-1% Z lift (4.4%, Wilson [2.7%, 7.2%]).** Post-hoc
  and at the panel level, not at the pre-registered scope. Cannot be
  promoted to a headline finding without inviting forking-paths critique.
- **Power for Spec B at α=0.05.** β₁ CI grazes zero; we cannot claim
  the continuous spec independently rejects.
- **Item #8 5-min companion / publication-hiding.** Real measurement
  concern but tangential to the tail-shape claim; either appendix or
  separate paper.

## How this framing handles the competing findings
- **QR-full positive at τ=0.95 (evidence #4):** Reframed as the *second*
  result, not a contradiction. The narrative is "Z shifts the conditional
  95th percentile of LMP upward (consistent with a higher-pressure operating
  regime) but does not produce a heavier-tailed distribution above that
  percentile (rejecting the ORDC phase-transition mechanism)." The two
  statistical objects — quantile location vs. tail-shape parameter — are
  formally orthogonal; positive on one is not evidence for or against the
  other. total_lmp ≈ 4× congestion at the conditional-quantile level fits
  the same story: most of the location effect is in energy, not congestion,
  reinforcing the decomposition logic.
- **Item #6 in-filter null (evidence #7):** Strong corroboration, not
  competition. Inside the proposal-filter scope, P(LMP > $250 | top Z
  decile) = 0 — the high-Z regime simply does not generate the tail
  events the proposal targeted. Reads as direct empirical support for the
  rejection.
- **Item #9 decile-level null + top-1% lift (evidence #9):** Decile
  monotonicity failure on 4/4 plotted pnodes corroborates the rejection
  of the smooth-monotone Z → tail mapping. Top-1% lift (4.4%) is small,
  panel-level, post-hoc, and within shouting distance of the unconditional
  base rate; it does not undermine the headline.
- **Smooth-curve diagnosis (evidence #1):** Pre-headline framing context;
  ruled out the proposal's literal phase-transition reading already, and
  the median-split rejection is the formal nail.

## If the advisor disagrees with this framing
The most likely alternative they will favor is **Framing #2** (QR-full
positive moderate-quantile slope), because positive findings are easier
to publish and align with the ORDC narrative the advisor likely brought
to the project. If Framing #2 becomes the headline, this Framing #1
content should be repositioned as the paper's *discipline section*: the
rigorous tail-shape test that establishes the *boundary* of the QR-full
claim. The narrative becomes "Z shifts conditional location (headline)
but not tail shape (boundary), so projections should scale location-based
risk metrics with Z but not tail-based reserve-margin metrics." This
preserves the methodological contribution of the rejection without
requiring the paper to lead with a negative result. Framing #4 is the
weaker fallback (post-hoc and concentration-only); Framing #3 collapses
into a less informative version of #1 and should not be the headline.
