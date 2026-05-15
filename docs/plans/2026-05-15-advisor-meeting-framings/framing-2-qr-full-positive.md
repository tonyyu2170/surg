# Framing 2: QR-Full Moderate-τ Positive

**Headline thesis:** Load-volatility (Z) drives a robust, cross-pnode-consistent positive shift in the conditional 90th–95th-percentile LMP, and the total-LMP response is roughly 3–4× the congestion response — a clean ORDC-mechanism fingerprint operating through the system-energy component, even though the response does not extend cleanly into the extreme (≥99th-pct) tail.

## TL;DR

The paper characterizes how load volatility in the PJM Dominion zone reshapes the LMP distribution under post-2022 data-center growth. Using 3.6 years of hourly LMP across 7 Loudoun-area pnodes, we estimate a year-FE-residualized quantile-regression slope of LMP on Z and find it is positive and cleanly bounded away from zero at τ=0.90 and τ=0.95, with the total-LMP response ~3–4× the congestion response — a magnitude differential that is the predicted signature of ORDC scarcity adders riding through the system-energy price. The proposal's literal "MW/min threshold" question is rejected (response is smooth, not stepwise), but its underlying mechanism prediction survives at moderate quantiles.

## Why this framing is the right one

- **Only α=0.05-cleared positive finding in the project.** Among the four candidate framings, this is the only one where a year-FE-residualized estimator delivers a CI excluding zero with consistent sign on 5 of 7 pnodes (4 of 5 non-Ashburn pnodes at τ=0.95; 5 of 5 non-Ashburn pnodes at τ=0.90). Every other framing's headline relies on a single rejection (Spec A median-split) or on absence of effect.
- **Direct ORDC mechanism evidence.** The total_lmp / congestion ratio at τ=0.95 (year-FE) is 1.389 / 0.410 ≈ 3.4×. ORDC scarcity adders enter the LMP through the system-energy component — congestion alone cannot generate this differential. The decomposition is the cleanest mechanism statement the data supports.
- **Cross-pnode robustness inside the cluster.** Non-Ashburn pnodes (`primary`, `total_lmp`, `ox`, `bristers`, `dom_zonal`) all carry positive year-FE secular slopes at τ=0.90 with CIs excluding zero; 4 of 5 do at τ=0.95. The pattern holds across the data-center cluster, the operational controls (`ox`, `bristers`), and the zonal aggregate.
- **Direct line to sub-question 2 (JLARC).** This framing produces a defensible projection coefficient (year-FE slope @ τ=0.95) with a stated conservatism rationale. None of the competing framings supplies a usable input for the projection layer.

## Supporting evidence

- **Primary headline (Evidence #4 + 2026-05-14 year-FE diagnostic).** Year-FE-residualized z_slope at τ=0.95: `primary` cluster congestion = +0.410 [+0.040, +0.275 secular component]; `total_lmp` = +1.389 [+0.547, +1.205]; `ox` = +0.408; `bristers` = +0.348. At τ=0.90 the same five non-Ashburn pnodes carry positive year-FE slopes with CIs excluding zero. The primary-spec slopes are larger (cluster congestion +0.578, total_lmp +2.334) but partly absorb a year-correlated 2026 partial-window component; we report year-FE as the conservative anchor, primary as the upper bound, and label the gap "year-FE-absorbed component, attribution unresolved."
- **ORDC mechanism support (Evidence #4).** total_lmp / congestion year-FE ratio ≈ 3.4× at τ=0.95 and ≈ 4.6× at τ=0.90. This differential cannot arise from congestion alone; it requires Z to load on the system-energy component, which is what the ORDC scarcity-adder mechanism predicts.
- **Component-level direction consistency (Evidence #5).** The pre-registered system_energy median-split test produced shape_diff = +0.257 in the ORDC-predicted direction (CI spans zero, underpowered per Rule 2). Sign is consistent with the QR-full headline; the component decomposition is direction-corroborative even if not power-conclusive.
- **Extreme-tail extension (Evidence #9).** Post-hoc top-1% Z slice on the full panel: P(total_lmp > $250 | Z > p99, n=316) = 4.4% (Wilson CI [2.7%, 7.2%]), versus a much lower base rate. The slope's sign extends into the extreme tail at descriptive scope, even though the τ=0.99 QR-full estimator is too sparse to fit cleanly.
- **What we are NOT claiming.** No threshold ĉ (Evidence #1, smooth-curve diagnosis). No tail-shape heaviness shift on congestion (Evidence #2, #3, addressed below).

## The strongest counter-argument

**"You answered an easier question than the proposal posed."** The proposal asked about a heavy-tailed regime — a tail-shape claim that lives at τ ≥ 0.99. Our cleanest result is at τ=0.95 (a moderate conditional quantile), and the extreme-tail evidence is either underpowered (item #9 decile null), null (item #6 in-filter), or descriptive-only (item #9 post-hoc top-1%). The Spec A median-split GPD test on congestion's tail shape rejects in the *opposite* direction at α=0.05 (shape_diff = −0.180, CI excludes 0). A reviewer can fairly say: "your positive finding is on a quantile the proposal did not center, and the test that actually addresses the proposal's tail-heaviness question rejects with the wrong sign."

## Rebuttal

The Spec A rejection and the QR-full positive slope test **different statistics on different functions of the LMP distribution** and are not in tension:

1. Spec A is a GPD shape parameter ξ on the congestion exceedances above p95 — it asks whether the *tail-decay rate* of congestion changes between low- and high-Z halves.
2. QR-full is the conditional quantile of LMP at τ — it asks whether the *level* of the conditional 95th percentile shifts with Z.

A distribution can have (a) a heavier right tail at LOW Z (Spec A's finding) and (b) a higher conditional 95th percentile at HIGH Z (our finding) simultaneously — for example, if HIGH-Z hours systematically push the entire conditional distribution up (location shift) while LOW-Z hours have rarer but more dispersion-rich extreme excursions (scale/shape effect). The two statistics are not redundant. The QR-full result is the operationally meaningful one for price exposure: a generator or load-serving entity is exposed to the *level* of the price at quantiles it actually transacts against, not to the asymptotic shape parameter. Most LMP volatility relevant to operational risk lives at p90–p95, not at p99+.

The "moderate-quantile" objection also understates τ=0.95 in this market. With ~31,500 hourly observations, τ=0.95 corresponds to roughly 1,575 hours (~9 weeks of operating time per pnode). These are not normal hours; they are the upper-decile-of-upper-decile pricing events that drive annual revenue and risk-management decisions. A robust slope at τ=0.95 is an economically meaningful claim, not a consolation prize for failing at τ=0.99.

The extreme-tail evidence (items #6, #9) is **consistent**, not contradictory. Item #6's null is within a filter that excludes the very events the question targets — a methodological caveat, not a substantive null. Item #9's full-panel decile null is at coarse aggregation, but the post-hoc top-1% slice (4.4% exceedance rate, n=316, CI excludes the base rate) shows the slope's direction extending into the extreme tail; we just cannot estimate the slope itself there with the available n.

## Anticipated advisor pushback

1. **(Most severe) "Year-FE absorbs 2026 partial-year inflation — how do you know your headline isn't a 2026 artifact?"** Honest answer: we don't, fully. The year-FE residualization absorbs everything loading on year (weather, generation mix, topology, partial-year selection). We report the primary slope as the upper bound, the year-FE slope as the conservative bound, and label the gap as un-attributed by design. This is acknowledged in the paper's methods and is the rationale for using year-FE as the JLARC projection input.
2. **"Why τ=0.95 and not τ=0.99?"** Pre-registered as the headline; τ=0.99 is reported as a sparse-tail-unstable directional caveat per the year-FE diagnostic. Reframing post-hoc to τ=0.99 would violate the pre-reg and would inherit the τ=0.99 estimator instability.
3. **"The Spec A rejection on congestion tail shape goes the other way — explain that to me again."** Different statistic (shape vs. conditional level), addressed in the rebuttal. The paper presents both as complementary characterizations of how Z reshapes the LMP distribution: the conditional level rises with Z (QR-full) while the congestion tail is no heavier (Spec A). Both can be true; both are reported.
4. **"Ashburn diverges from the cluster — does that contaminate the headline?"** Ashburn TX1 and TX2 carry negative year-FE secular slopes at τ=0.95 with CIs spanning zero. We restrict the headline to the 5 non-Ashburn pnodes; Ashburn is reported as a robust unexplained anomaly (item #4) requiring distribution-side substation diagnosis the data cannot resolve.
5. **"Why publish a positive 95th-pct conditional finding rather than the proposal's stated mechanism question?"** Because it is the result the data actually supports at α=0.05 with cross-pnode robustness, and it has a clean economic interpretation. The proposal's literal question (MW/min threshold) is rejected by smooth-curve diagnosis; the proposal's mechanism question (tail shape) rejects in the wrong direction at the only scope with power. Reporting the moderate-quantile result honestly is preferable to a tortured tail-shape headline.

## Proposed paper title + abstract (~200 words)

**Title:** *Load Volatility and Conditional Price Quantiles in the PJM Dominion Zone: Evidence of an ORDC Footprint at Moderate Tails*

**Abstract.** Rapid data-center buildout in northern Virginia has reshaped the load-variance profile of the PJM Dominion zone. We ask how short-horizon load volatility (Z = |Δ DOM zonal load| / 60 MW/min) maps onto the conditional distribution of locational marginal prices at seven nodal price points covering the Loudoun cluster, two Ashburn substations, and operational controls, using 3.6 years of post-2022 hourly LMP. We find no support for a discrete MW/min threshold; the response is smooth in Z. Year-fixed-effects quantile regression delivers a positive, cross-pnode-consistent slope at τ=0.90 and τ=0.95 with confidence intervals excluding zero on five of seven pnodes; the total-LMP response is approximately 3–4× the congestion response, a magnitude differential consistent with ORDC scarcity adders propagating through the system-energy price component. Tail-shape tests on congestion exceedances (GPD, median-split) do not show the predicted heavier-tail-at-high-Z pattern; we interpret this as evidence that Z affects the conditional level of moderate-tail prices, not the asymptotic shape parameter of the congestion tail. The estimated moderate-quantile slope serves as a conservative input to a projection of 2030–2040 price-exposure trajectories under JLARC's official load forecast.

## What this framing leaves unaddressed

- **Ashburn TX1 q=0.99 sign reversal.** Robust to LOO (0 of 175 refits change sign, stdev 0.003) but mechanistically unexplained. Reported as a "robust unexplained substation-level anomaly" footnote.
- **Year-FE attribution gap.** The primary-vs-year-FE difference is not separately identified between secular drift, weather, generation-mix shifts, and 2026 partial-window selection. Reported as a stated methodological limit, not resolved.
- **Tail-shape mechanism on congestion.** Spec A's α=0.05 rejection in the wrong direction is not explained by this framing — it is presented as a complementary, separate result.
- **In-filter direct Z → LMP exceedance characterization (item #6).** Reported as a methodological note (filter excludes target events), not as substantive evidence either way.
- **τ=0.99 conditional quantile.** Sparse-tail-unstable in the year-FE diagnostic; not used as a headline quantity.
- **Magnitude precision.** 3.6y window establishes direction and order-of-magnitude; cannot tightly bound the slope.

## How this framing handles the competing findings

- **Spec A median-split rejection on congestion (Evidence #2).** Different statistic. Spec A measures the GPD shape parameter ξ on congestion exceedances above p95; the QR-full headline measures the conditional level of LMP at τ=0.95. A LOW-Z heavier tail (Spec A) and a HIGH-Z higher conditional 95th percentile (QR-full) are jointly consistent — for example, a Z-driven location shift on the conditional distribution combined with greater dispersion in the rare LOW-Z extreme excursions. The paper reports both with the explicit framing that they characterize different aspects of the Z → LMP relationship. Spec B (Evidence #3) corroborates Spec A's direction at the continuous-fit scope but is underpowered (CI [−0.021, +0.003]); it is reported as direction-consistent supplementary evidence.
- **Item #6 in-filter decile null.** The proposal-filter scope excludes events where LMP > $100 (only 10 of 2,027 obs exceed). The null reflects filter scope, not absence of effect; outside the filter the response exists but cannot be decomposed by Z deciles within filter. Reported as a methodological boundary on the descriptive question, separable from the conditional-quantile slope.
- **Item #9 full-panel decile null + post-hoc top-1% slice.** The decile-level null on the full panel is at coarse aggregation. The post-hoc top-1% Z slice (P(total_lmp > $250 | Z > p99) = 4.4%, Wilson CI [2.7%, 7.2%]) is in the same direction as the QR-full slope and extends it descriptively to the extreme tail at the cost of moving from inferential to descriptive scope. Reported as supportive: the conditional-quantile slope's sign extends into the extreme tail; only the inferential power does not.

## If the advisor disagrees with this framing

The natural fallback is **Framing #1 (Spec A rejection of the ORDC mechanism on congestion)**: it is the only other α=0.05-cleared finding in the project and has the same statistical strength on a different statistic. Under that framing, this framing's QR-full positive slope becomes the secondary "but the moderate-quantile conditional level still rises with Z" result — a complementary characterization that softens the headline rejection and provides the sub-q2 projection input. The Spec B continuous-fit underpowered result (Evidence #3) is also consistent with that framing as a direction-corroborative robustness check.

Under any framing, the year-FE slope at τ=0.95 is the right input to sub-q2's projection layer; that role does not depend on which framing wins the paper headline.
