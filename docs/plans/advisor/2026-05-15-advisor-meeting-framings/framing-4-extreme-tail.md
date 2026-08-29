# Framing 4: Extreme-Tail Concentration — Proposal Directionally Right, Wrong About Sharpness

**Headline thesis:** The proposal's "phase transition" is empirically a
*concentration* — not a kink at any Z threshold but a smooth super-baseline
clustering of high-LMP events at the extreme tail of Z (top 1%), with lifts
that grow monotonically with the LMP threshold and concentrate in the
system_energy component, exactly as the ORDC reading would predict but at a
finer Z resolution than decile binning can resolve.

## TL;DR
The paper reconciles the SURG proposal with the data: high load volatility
*does* drive crazy LMP, but the dependence is smooth, not stepwise, and the
signal lives in the extreme tail of Z where decile-resolution tests have
no power. Conditional on Z above its 99th percentile (n=316 hours over
3.6 years), P(total_lmp > $250) is 4.4% (Wilson 95% CI [2.7%, 7.2%]) versus
a 1.5% unconditional baseline — a 2.9× lift whose CI lower bound excludes
the baseline. Lifts grow with the LMP threshold ($100: 2.4×; $250: 2.9×;
$500: 3.8×; $1000: 5.9×) and concentrate in the energy component, reading
as ORDC-shaped scarcity pricing under genuinely volatile conditions. The
contribution is a corrected mechanism story plus a methodological lesson
about how decile-resolution analyses can mask extreme-tail effects.

## Why this framing is the right one
- **It is the only framing that reconciles the proposal with the data
  rather than overturning or sidestepping it.** The proposal got the
  direction right (high Z → tail-LMP risk) and got the *shape* wrong
  (smooth concentration, not a kink). That is a much more defensible
  empirical posture than "we falsified the grant" (Framing #1) or "we
  found something different from what the grant asked" (Framing #2/#3).
- **The triangulation across statistical objects is unusually clean.**
  The QR-full year-FE positive z_slope at τ=0.95 (5/7 pnodes, CIs exclude
  0; total_lmp ≈ 4× congestion) is the *moderate-quantile companion* to
  the extreme-tail concentration. Two independent estimators on different
  parts of the conditional distribution point the same way; that is rare
  enough in this project to be worth headlining.
- **The component story lines up with theory.** The lift concentrates in
  system_energy (the ORDC-bearing component), with congestion showing a
  smaller ~2.3× lift at the same Z bin. This matches the LMP decomposition
  expectation: ORDC adders enter via the energy clearing price, not via
  the binding-constraint shadow prices.
- **It downgrades the pre-registered failures cleanly.** The decile-level
  null becomes a *resolution* result (decile binning is too coarse for an
  extreme-tail signal). The Spec A rejection becomes a *statistic* result
  (a tail-shape test on congestion does not detect a tail-exceedance-rate
  effect on total_lmp). Neither is reframed away — both are explained.

## Supporting evidence
- **Headline (evidence #9, post-hoc):** Full-panel pooled hourly data
  (post-cap, n=31,536). Conditional on Z above its 99th percentile
  (n=316), P(total_lmp > $250) = 4.4%, Wilson 95% CI [2.7%, 7.2%]; the
  lower bound excludes the 1.5% unconditional baseline. Lifts at higher
  thresholds: $500 → 3.8×, $1000 → 5.9×; lifts at $100 → 2.4×. The
  monotone growth in lift with threshold is the concentration signature.
- **Component decomposition (evidence #9):** At the same top-1% Z bin,
  congestion lift is ~2.3× ($100 threshold), substantially smaller than
  the total_lmp lift, and the residual is in system_energy. Reads as
  ORDC adders in the energy component, consistent with evidence #5
  (item #2 system_energy headline `underpowered_pos_direction`,
  shape_diff = +0.257).
- **Triangulation (evidence #4):** QR-full year-FE @ τ=0.95 finds positive
  z_slope on 5/7 pnodes, CIs exclude 0, total_lmp ≈ 4× congestion. The
  conditional 95th-percentile slope and the top-1% extreme-tail
  concentration are independent statistical objects on the same
  underlying joint distribution, both pointing positive.
- **Smoothness (evidence #1):** No threshold ĉ exists in the TAR sense.
  This is *consistent with* concentration (a smooth response curve whose
  upper tail steepens) and inconsistent with the proposal's literal kink
  reading. Pre-headline framing context.
- **Non-linearity (evidence #3):** Spec B LRT detects significant
  non-linearity at p90 (p=0.007). Curvature in ξ(Z) at moderate quantiles
  is exactly what a concentration framing predicts.
- **Pre-reg vs post-hoc:** Decile-level pre-registered test on item #9
  returned Verdict C (partial/mixed). The top-1% finding is post-hoc, was
  triggered by an audit asking whether decile binning could mask an
  extreme-tail effect, and is labeled as such in the application entry.
  The pre-reg verdict stands unchanged; the headline is presented as
  descriptive characterization, not as a hypothesis test.

## The strongest counter-argument
"This is post-hoc fishing dressed up as a finding. The pre-registered
decile rule failed (Verdict C); you then went looking at finer Z bins and
found a top-1% lift with a Wilson CI lower bound at 2.7% — a thin signal
on n=316 — and now you want to make it the headline. That is exactly the
forking-paths pattern pre-registration exists to prevent. Worse, you are
asking a faculty audience to accept a post-hoc number as the paper's
contribution while the *pre-registered* test on the same variable rejected
the proposal in the opposite direction (Spec A, Framing #1). A reviewer
will notice and the paper will be hard to defend."

## Rebuttal
The objection is fair on its surface and the post-hoc nature is real, but
three points constrain how damaging it actually is. First, the audit was a
*diagnostic*, not a search: it asked a single, sharply specified
methodological question — does decile binning have power to detect an
extreme-tail effect? — and was logged as post-hoc in the same application
entry that recorded Verdict C. There is no garden of forking paths here
because there were no alternative analyses run and discarded; the audit
was the only follow-up, and its result was reported regardless of sign.
Second, the headline is *not* a hypothesis test and is not framed as one.
The Wilson CI is a descriptive uncertainty bound on a conditional
exceedance rate; the contribution is "high-Z hours concentrate high-LMP
events at rates whose Wilson lower bound excludes the unconditional
baseline." That claim is publishable as descriptive empirical
characterization with the post-hoc nature stated in the abstract. Third,
the QR-full year-FE positive at τ=0.95 (evidence #4) is *independently
pre-registered* and points the same direction. The headline does not stand
alone — it sits inside a triangulation. The honest framing is "the
pre-registered conditional-quantile test confirms a positive Z → moderate-
quantile-LMP slope; a post-hoc extreme-tail audit shows the slope steepens
into a 2.9–5.9× lift in the top 1% of Z." Both pieces are necessary and
neither is presented as something it is not.

What the rebuttal *cannot* do is convert the top-1% number into a
pre-registered finding. Hardening it requires either a held-out window
(prospective pre-registration on data acquired after lock-in) or a
sub-question 3 follow-up that pre-registers extreme-tail thresholds in
advance. Both are flagged as future work; the paper does not claim
otherwise.

## Anticipated advisor pushback
1. **(Wei, most severe) "Post-hoc is post-hoc — why should I accept this
   as a headline?"** Answer: the headline is descriptive characterization
   triangulated against an independent pre-registered positive result
   (QR-full @ τ=0.95). The post-hoc audit was scoped, single-shot, and
   logged before the result was known to be positive. The paper's
   contribution is the *reconciliation* — proposal directionally right,
   wrong about sharpness — which neither pure rejection (#1) nor pure
   null (#3) supports. The post-hoc nature is named in the abstract.
2. **(Lihui) "n=316 with Wilson lower bound at 2.7% vs 1.5% baseline is
   thin. Why not p99.5 or report the full quantile sweep?"** Answer:
   the lift is reported at multiple LMP thresholds ($100, $250, $500,
   $1000), and the *monotone growth* in lift across thresholds (2.4× →
   2.9× → 3.8× → 5.9×) is the concentration signature, not the single
   p99 number. n=32 at top-0.1% Z is reported as a sensitivity but not
   load-bearing because Wilson CIs are too wide to interpret.
3. **(Wei) "How does this reconcile with the Spec A rejection at α=0.05
   on congestion?"** Answer: different statistic on a different variable.
   Spec A measures *tail-shape parameter* (GPD ξ) on *congestion*; the
   headline measures *exceedance-rate concentration* on *total_lmp*. A
   thinner-tailed congestion exceedance distribution is fully compatible
   with a higher exceedance *rate* of total_lmp at extreme Z if the
   rate-shift sits in the energy component (which the decomposition
   confirms). The two findings address orthogonal questions.
4. **(Lihui) "Decile null undermines this. Verdict C means the
   pre-registered rule said 'mixed' on the same variable."** Answer:
   yes — that is the methodological lesson the paper draws explicitly.
   Decile resolution is too coarse for an extreme-tail signal; a top-1%
   bin (10× finer at the right end) recovers a clean concentration. The
   decile null is presented as motivation for the audit, not as a
   contradiction.
5. **(Wei) "The LRT non-linearity at p90 (p=0.007) — is that consistent
   with your story?"** Answer: yes. Concentration at the extreme tail of
   Z implies the conditional response curve is non-linear at high
   quantiles; the LRT result is independent corroboration of that
   curvature.
6. **(Lihui) "Item #4 Ashburn TX1 q=0.99 anomaly?"** Footnoted, isolated,
   does not touch the headline.
7. **(Wei) "Item #6 in-filter null — high Z within the proposal-filter
   scope produces zero $250+ events on n=2,027. How does that square?"**
   Answer: the filter excludes shoulder-season night-time hours
   precisely the hours where ORDC scarcity is least likely, by design.
   The full-panel headline is the unfiltered version of the same question
   and is the more inclusive characterization. The filter result is a
   scope discipline finding (the filter is too aggressive for this
   question), not a contradiction.

## Proposed paper title + abstract (~200 words)

**Title:** Load Volatility Concentrates High-LMP Events at the Extreme Tail
of Z: A Reconciliation of the ORDC Phase-Transition Hypothesis on the PJM
Dominion Zone

**Abstract:** Rapid data-center buildout in PJM's Dominion zone has
motivated concern that load-side volatility (Z = |ΔL|/Δt, MW/min) drives
the zone past a heavy-tailed congestion-pricing regime via the ORDC
reserve-shortage mechanism. We test the conjecture using 3.6 years of
post-cap hourly DM2 data (2022-10 → 2026-05; 31,536 obs across seven
nodal injection points). A pre-registered decile-binned test on
P(LMP > $250 | Z) returns mixed verdicts; a pre-registered conditional
quantile regression at τ=0.95 finds a positive z_slope on five of seven
pnodes (CIs exclude zero; total_lmp ≈ 4× congestion). A post-hoc
extreme-tail audit, scoped and labeled as such, finds that conditional on
Z above its 99th percentile (n=316), P(total_lmp > $250) is 4.4% (Wilson
95% CI [2.7%, 7.2%]) versus a 1.5% unconditional baseline, with lifts
growing monotonically across LMP thresholds (2.4× at $100, 2.9× at $250,
3.8× at $500, 5.9× at $1000) and concentrating in the system_energy
component. The empirical phase transition is a smooth tail concentration
rather than a kink; decile resolution lacks power to detect it. We
present the result as descriptive characterization triangulated against
the pre-registered conditional-quantile finding, flag a pre-registered
follow-up on extreme-tail thresholds as future work, and discuss
implications for JLARC-projected 2030 load growth.

## What this framing leaves unaddressed
- **Spec A median-split rejection (evidence #2).** A pre-registered
  α=0.05 rejection of opposite-sign tail-SHAPE behavior on congestion.
  Reframed (correctly) as a different statistic on a different variable,
  but the paper has to *carry* this finding rather than dismiss it.
  Treated as the paper's discipline section: tail shape on congestion is
  flat-to-thinning; tail concentration on total_lmp is real. Both are
  true.
- **Decile-level Verdict C (evidence #9 pre-reg).** Acknowledged as the
  motivating result, not buried. Sets up the resolution-lesson framing.
- **Item #6 in-filter null.** Filter-scope discipline finding; reads as
  "the proposal's literal filter excludes the events of interest," which
  is itself a contribution and is footnoted.
- **n=32 at top-0.1% Z.** Reported as a sensitivity; not load-bearing
  because CIs are uninterpretable.
- **Ashburn TX1 q=0.99 anomaly (evidence #6).** Footnoted; future work.
- **Item #8 5-min companion / publication-hiding.** Either appendix or a
  separate paper; tangential to the concentration claim.
- **Lack of held-out validation.** The post-hoc finding cannot be
  hardened within this paper. Pre-registered sub-q3 follow-up is the
  honest path; flagged in discussion, not promised in results.

## How this framing handles the competing findings
- **Framing #1 (Spec A rejection):** Reframed as the paper's *boundary*
  statement on a different statistic. "Z does not heavy-tail the
  *congestion* exceedance distribution at p95 (Spec A); Z does
  concentrate *total_lmp* exceedance events at the extreme tail of Z
  (this paper)." Two compatible claims about two different things. The
  Spec A result remains a clean pre-registered α=0.05 finding and earns
  its own section.
- **Framing #2 (QR-full positive at τ=0.95):** *Strongest support* for
  this headline, not competition. The QR-full result is the
  pre-registered moderate-quantile companion to the extreme-tail
  concentration. The paper presents them as a triangulation: positive
  z_slope at τ=0.95 (pre-registered, n large) → 2.9× exceedance lift at
  top-1% Z for $250+ events (post-hoc, n=316). Same direction, different
  parts of the distribution.
- **Framing #3 (decile-level null):** Demoted from "the proposal was
  wrong" to "the proposal's *test resolution* was wrong." The decile
  null is the motivating result that triggered the audit; the audit
  recovers the signal at finer Z resolution. Decile-resolution failure
  becomes a methodological contribution rather than a substantive null.
- **Smooth-curve diagnosis (evidence #1):** Pre-headline framing context.
  Rules out the literal kink and supports the smooth-concentration
  reading directly.

## If the advisor disagrees with this framing
The most likely disagreement is "you cannot lead a paper with a post-hoc
number." If Wei or Lihui pushes hard on this, the fallback is **Framing #2
(QR-full positive)** as headline and this Framing #4 content repositioned
as the paper's *characterization section*: the QR-full result establishes
the pre-registered conditional-quantile finding; the extreme-tail
concentration is presented as a descriptive companion that *characterizes
where the slope concentrates* rather than as the headline contribution.
The paper's structure becomes "Z shifts the conditional 95th percentile
of LMP upward (headline, pre-registered) and the shift is driven
disproportionately by the top 1% of Z (descriptive characterization,
post-hoc, with appropriate caveats)." This preserves the substantive
finding without asking the post-hoc result to carry the title.

Framing #4 should not be the fallback for #1 or #3 — those framings
exclude this content entirely (or carry it only as a footnote), and the
substantive contribution is lost.

## Pre-registration note (REQUIRED — handle the post-hoc question explicitly)
The top-1% extreme-tail finding is post-hoc. It was generated by a
sanity-audit triggered after the pre-registered decile-binned test
returned Verdict C, asking the single methodological question "does
decile binning have power to detect an extreme-tail effect?" The audit
was scoped to one specification (top-1% and top-0.1% Z bins, four LMP
thresholds, Wilson exact CIs, full panel) and the result was logged
*before* it was characterized as positive. The application entry for
item #9 records the pre-registered Verdict C and the post-hoc audit
result side-by-side; the pre-reg verdict is not edited.

This finding is publishable as **descriptive empirical characterization**
under three conditions, all met by the paper as drafted: (i) the
post-hoc nature is stated in the abstract, not buried in the methods;
(ii) the headline is presented as a Wilson-CI exceedance-rate
concentration, not as a hypothesis test or a tail-shape claim; (iii)
the result is triangulated against an independent *pre-registered*
positive finding (QR-full @ τ=0.95) and a theoretically motivated
component decomposition (system_energy carries the lift), so it does
not stand alone as the sole evidentiary basis for the contribution.

The honest hardening path is a pre-registered sub-q3 follow-up that
locks in extreme-tail thresholds (top-1% Z, $250+ LMP threshold,
Wilson CI rule) on a held-out window before the test is run. That
follow-up is flagged in the discussion as the natural next step; the
paper does not claim it has already been done. Without it, the
strongest available framing is "post-hoc characterization of a
pre-registered triangulating positive," which is what this paper
defends.
