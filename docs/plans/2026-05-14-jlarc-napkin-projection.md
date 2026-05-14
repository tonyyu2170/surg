# Napkin-Math Projection — Early Sub-Question 2 Read (2026-05-14)

> **Status:** Analytic sketch run overnight to give the user an early
> concrete read of sub-question 2's answer. NOT the formal projection
> layer — that's gated on user approval of the design at
> `docs/plans/2026-05-14-jlarc-projection-design.md`. This document is
> for review-context; the formal layer (when built) supersedes it.

## Inputs

- **Current Z distribution:** `dom_load_gradient_abs_mw_per_min` on the
  analysis panel. E[Z(2025)] = 6.404 MW/min. Z_max(historical) = 36.4
  MW/min.
- **Baseline LMP percentiles:**
  - Cluster total_lmp: 95th-pct = $111.07; 99th-pct = $332.55.
  - Cluster congestion: 95th-pct = $24.75; 99th-pct = $124.63.
- **QR-full z_slopes** (from `outputs/qr_full/{primary,total_lmp}.json`):
  - Cluster congestion: τ=0.90 → 0.393; τ=0.95 → 0.578; τ=0.99 → 0.358
    (CI crosses 0).
  - Cluster total_lmp: τ=0.90 → 1.527; τ=0.95 → 2.334; τ=0.99 → 2.598.
- **JLARC growth scenarios** (from `docs/plans/2026-05-14-jlarc-rpt598-key-figures.md`):
  - Low (Half unconstrained): 1.95× by 2040.
  - Base (PJM 5.5% YoY): 2.23× by 2040.
  - High (Unconstrained): 2.90× by 2040.

## Method (napkin-grade)

1. Proportional scaling: E[Z(2040)] = scenario_multiplier × E[Z(2025)].
2. Linear extrapolation of QR-full slope: LMP_τ shift = slope_τ × (E[Z(2040)] - E[Z(2025)]).
3. Effective-threshold approximation for exceedance counting: under a
   shifted distribution, "hours above $X in 2040" ≈ "hours above
   (X - slope_τ × ΔE[Z]) in 2025 distribution units." This is
   defensible at first order but treats slope as constant across τ.

## Result table — total_lmp (the ORDC-mechanism response)

Projected hours/year above each LMP benchmark in 2040 under three JLARC scenarios:

| Benchmark | Slope-τ used | 2025 baseline | Low (1.95×) | Base (2.23×) | High (2.90×) |
|---|---|---|---|---|---|
| $50 | τ=0.90 | 2,064 hr/yr | 3,012 | 3,404 | 4,650 |
| $100 | τ=0.95 | 526 hr/yr | 698 | 768 | 993 |
| $200 | τ=0.99 | 179 hr/yr | 203 | 212 | 234 |
| $300 | τ=0.99 | 104 hr/yr | 112 | 114 | 122 |
| $500 | τ=0.99 | 48 hr/yr | 51 | 51 | 54 |
| **$850 (ORDC 1st-step)** | τ=0.99 | **19 hr/yr** | **19** | **19** | **21** |

## Result table — cluster congestion (the proposal's stated response)

| Benchmark | Slope-τ used | 2025 baseline | Low (1.95×) | Base (2.23×) | High (2.90×) |
|---|---|---|---|---|---|
| $10 | τ=0.90 | 1,096 hr/yr | 1,433 | 1,568 | 1,996 |
| $25 | τ=0.95 | 433 hr/yr | 504 | 528 | 605 |
| $50 | τ=0.99 | 221 hr/yr | 230 | 234 | 241 |
| $100 | τ=0.99 | 108 hr/yr | 112 | 113 | 115 |
| $200 | τ=0.99 | 46 hr/yr | 46 | 47 | 47 |

## Key takeaways for the design

1. **$850 benchmark (current design default) is uninformative.** Even
   under the aggressive "high" scenario (2.9× growth), hours/yr above
   $850 only goes from 19.2 to 20.6 — essentially flat. The tail above
   $850 is already so rare that a doubling of Z barely shifts the count.
2. **Moderate-quantile benchmarks ($50-$100 total_lmp) show dramatic
   shifts.** Under the base PJM scenario by 2040: hours above $50
   grow by ~65% (2,064 → 3,404); hours above $100 grow by ~46%
   (526 → 768).
3. **$300 (PR penalty level) is in the middle.** ~10-15% growth in
   hours/yr under base/high — interpretable but not dramatic.
4. **Sub-question 2's framing depends critically on benchmark choice.**
   The same projection produces very different paper narratives at
   different benchmarks. The design's open question (Item 2 in the
   8-question list) becomes load-bearing.

## Implications for the JLARC projection-layer design (open questions)

- **Open Q2 (benchmark LMP value):** Recommend revising the design's
  default from $850 (uninformative) to $300 or to a quantile-anchored
  benchmark (e.g., current 99th-pct → projected 99th-pct as a "the
  rare event today is more common in 2040" framing). The user's choice
  here determines whether sub-question 2's headline reads as
  "modest tail growth" or "moderate-tail-frequency doubling."
- **Open Q1 (primary metric):** The exceedance-hours framing remains
  useful, but the *level* of the benchmark drives interpretability
  more than the *concept* of the metric.

## Caveats — these are the same load-bearing assumptions as the design

1. **Proportional scaling** assumes Z is fully DC-attributable. The
   JLARC extraction's "no-new-DC" baseline (1.19× by 2040) suggests
   ~19% of growth is non-DC. The DC-attributed scaling would shave
   ~10-20% off the projected shifts above.
2. **Linear extrapolation of QR-full slopes** is the central
   load-bearing assumption. Under high scenario (2.9×), E[Z(2040)] =
   18.6 MW/min — about half of Z_max historical (36.4), so within the
   fitted range. The extrapolation_factor (max projected Z / max
   historical Z) is well below 2 → no extrapolation_warning would
   fire under the design's spec.
3. **τ=0.99 CI crosses 0** on congestion (slope CI [-0.075, +1.194]).
   The point estimates above use the central value (0.358); the true
   uncertainty on congestion at the deepest tail is wide. For
   total_lmp, τ=0.99 slope is more solid (CI [1.32, 4.33]).
4. **Single point estimate, no scenario CIs.** The formal projection
   layer (when built) would propagate slope CIs and scenario
   uncertainty through to interval estimates on projected hours/yr.

## What would the formal projection layer add over this napkin-math?

- DC-attributed scaling (per-`dc_share_of_load` adjustment).
- Bootstrap propagation of slope CIs → CIs on projected hours.
- Multi-scenario × multi-metric × multi-year trajectory output JSON.
- `extrapolation_warning` flag at threshold-configurable Z_max ratio.
- Year-by-year trajectory between 2025/2040 anchors (linear or
  exponential growth curve per scenario).
- Distribution-shape projection (not just mean shift).

The napkin-math gives the central-estimate direction. The formal layer
gives interval-precise paper-ready output. Both will land at similar
qualitative conclusions if the design's assumptions hold.
