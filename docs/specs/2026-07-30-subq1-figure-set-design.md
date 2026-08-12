# Sub-q1 figure set — design

**Date:** 2026-07-30
**Status:** design, pending review
**Supersedes:** the figure set currently produced by `scripts/plot_subq1_results.py`

## Why this exists

The existing ten figures were built for a story that no longer holds. They
open on a single illustrative week, foreground the 2–5 AM shoulder filter
that has since been dropped as a default, read the superseded 1-year 5-min
panel, and — most importantly — none of them shows the finding the report
now leads with.

Three results from 2026-07-30 drive the redesign:

1. **The premise is weaker than the project assumed.** DOM load grew
   +21.5% (Feb 2023 → Jun 2026) while ramp volatility did not; normalized
   against contemporaneous load it *fell* every year.
2. **Congestion tracks load level, not load volatility.** Hours with
   congestion > $500 sit at the 99.1st percentile of load but the 45.9th
   of ramp.
3. **The pre-registered coefficient is specification-sensitive to the
   point of sign reversal.** Adding load level as a control flips
   z_slope in all ten subset × τ cells tested.

The figure set must carry (3) honestly rather than picking whichever sign
flatters the narrative.

## Narrative spine

> Load grew but volatility didn't → congestion is driven by load *level*,
> not volatility → the measured volatility effect is small, fragile, and
> sign-flips under a reasonable control → but *location* matters
> enormously.

Every figure below earns its slot by advancing one link of that chain.
Figures that advance no link are cut.

## The figure set

Twelve figures (F1–F11 plus F4b). New = built from scratch; Rebuilt = existing figure
repointed at current data; Retained = keep substantially as-is.

### F1 — The premise (NEW) — *opens the report*
**Three stacked line panels** sharing an x-axis, one point per month
(Feb 2023 → Jun 2026, 41 points each):
- (a) mean DOM load — rising, +21.5%
- (b) ramp p90 in MW/min — flat (21.9–28.5 across all 41 months)
- (c) ramp p90 as % of contemporaneous load — **falling** monotonically
  by year (0.1850% → 0.1596%)

Caption carries the trend test: OLS +0.030 MW/min per month, p=0.153;
Spearman ρ=+0.220, p=0.168. This is the "why the answer is what it is"
figure. Also satisfies the requested plain load-over-time line, in a form
that makes a point.

**Source:** `analysis_panel_5min.parquet`.

### F2 — Load vs volatility, system energy vs congestion (NEW) — *centerpiece*
2×2 small-multiple. Left column: response vs load decile. Right column:
response vs ramp decile *within the top load tercile* (so level is held
roughly fixed). Top row system energy, bottom row congestion (median and
p95).

Carries the mechanism in one image:
- system energy rises smoothly with load ($17.22 → $61.80)
- congestion is a switch, not a slope (median ~$0.30 for nine deciles,
  p95 $8.14 → $254.36 in the tenth)
- neither responds to ramps; congestion p95 *falls* $103.39 → $67.71
  across ramp deciles once load is held fixed

**Source:** `analysis_panel_5min.parquet`. Annotate with the M11 §6/§9
finding that `load volatility → reserve depletion` is UNSUPPORTED.

### F3 — Congestion and system energy over time (NEW)
**Three stacked line panels**, shared x-axis, full 3.4-year panel:
- (a) cluster **total LMP** over time — what a data center actually pays,
  and the accessible entry point
- (b) cluster **congestion** over time
- (c) cluster **system energy price** over time

Panel (a) leads because it is the quantity a non-technical reader cares
about; (b) and (c) then decompose it into the locational and system-wide
parts.

The contrast is the point, and it visually restates F2: system energy is
a smooth, seasonal series tracking load; congestion is spiky and
regime-shifting. Annotate (a) with the regime shift — p90 by year $9.56 /
$8.81 / $13.46 / **$63.56**.

Both panels need a log y-axis or a broken axis: congestion is median
~$1 against a 2026 p90 of $63.56, and system energy is median $28.04
against a max of $3,700 (offer-cap territory). Linear axes would flatten
everything before 2026 into a baseline smear.

Requested figure; it also sets up why pooled statistics over this panel
are not a constant estimand.

**Required caveat (see F11).** Panel (c) must be captioned to note that
system energy price is *locationally uniform across PJM*, so its 2026
rise is not a Northern-Virginia phenomenon. Without that line, panels (a)
and (b) read as a data-center story that the data does not support.

### F4 — Large-congestion events per month (NEW)
Two stacked bar panels, monthly:
- (a) count of intervals with congestion > $100 — **absolute** risk
- (b) count exceeding a trailing-12-month 99th percentile — **relative**
  to its own era

The divergence between the panels *is* the regime-shift finding: (a)
explodes in 2026, (b) does not. Requested figure.

### F4b — Severity escalation by year (NEW, sibling to F4)
Grouped bars, one group per year, one bar per threshold ($100 / $250 /
$500 / $1000):

| | 2023 | 2024 | 2025 | 2026 (½ yr) |
|---|---|---|---|---|
| >$100 | 479 | 804 | 1,505 | 3,737 |
| >$250 | 59 | 206 | 399 | 1,612 |
| >$500 | 0 | 73 | 128 | 681 |
| >$1000 | 0 | 7 | 13 | 62 |

**Annual, not monthly, and this is deliberate.** At $500, 28 of 41 months
are empty; at $1000, 33 of 41. Monthly bars at those thresholds would be
mostly zero and would read as noise rather than escalation. Annual
buckets are dense enough to be honest.

2026 covers Jan–Jun only, so its bars are **annualised and hatched** to
mark the extrapolation. $2000 is dropped — zero events in the entire
panel.

The headline this figure carries: $500+ congestion intervals did not
occur at all in 2023, and the escalation is monotone at every threshold.

**Required caveat (see F11).** This figure is the most likely in the set
to be misread. Shown bare, 0 → 681 invites the inference that Loudoun
congestion exploded because of data centers. A large share of the 2026
rise is system-wide — PJM-wide system energy price roughly tripled in the
same month — and the driver is unidentified. The caption must say so.

### F5 — Specification sensitivity (NEW) — *appendix; see note*
Forest plot. For each period (pooled, 2023, 2024, 2025, 2026) and each
τ ∈ {0.90, 0.95}, two point-and-CI rows: pre-registered spec and
load-controlled spec, all with day-block bootstrap CIs.

Anchor annotation on **2024 at τ=0.90**: +0.0367 [+0.0107, +0.0665]
pre-registered versus −0.0266 [−0.0416, −0.0103] load-controlled. Same
data, same bootstrap, opposite significant signs.

**Placement decided at review (2026-07-30): appendix, not headline** —
the forest plot is too methodological to lead a grant report. **F2 leads
instead.**

This demotion carries an obligation. The main text must still state the
fragility in plain language and point here — something to the effect of
*"the measured effect is small and its sign depends on whether load level
is controlled for; both specifications are reported in Appendix X."*
Demoting the figure must not quietly become suppressing the finding.

### F6 — Effect size across quantiles (NEW)
Two panels: implied congestion shift across the full observed Z range
(d1 median → d10 median, ΔZ ≈ 29.3 MW/min) versus τ ∈ {0.90 … 0.995};
left in dollars, right as % of the baseline quantile.

Pooled: +$1.28 / +$1.91 / +$0.69 / +$0.08 / −$0.31. 2025: +$2.02 /
+$4.44 / +$4.34 / +$2.79 / +$3.28, with the relative version collapsing
15.7% → 1.5%.

Must be plotted from the **pre-registered** spec with the load-controlled
values shown as a second series, and captioned that above τ≈0.97 nothing
is measurable — σ falls to +0.5/+0.3 *before* the 2.4–4.9× deflation.

### F7 — Location (NEW)
Ashburn TX1 vs Loudoun cluster vs OX vs BRISTERS vs SKFFSCRK vs DOM
zonal. Panel (a) exceedance frequency and p99 by pnode; panel (b) a small
correlation matrix.

Headline numbers: Ashburn p99 $611.37 and 4.71% of hours > $100 versus
SKFFSCRK $96.13 and 0.96%; SKFFSCRK–cluster correlation +0.870 while
Ashburn–cluster is only +0.209.

Supports the proposal's *locational* intuition even as the volatility
premise fails. **Check first:** Ashburn has n=17,448 vs 31,536 for the
others — confirm the coverage gap is benign before this ships.

**Source:** hourly `analysis_panel.parquet` (the 5-min panel has only 3
pnodes).

### F8 — Tail-risk decile curves, no filter (REBUILT)
Repoint the existing fig-5 at `outputs/fivemin_nofilter/`. Add the MDE
annotation: the $100 test resolves ±19% against a predicted 2–5% lift, so
the flat curve is a non-result there, not a refutation.

### F9 — Mechanism tests, condensed (RETAINED, condensed — confirmed at review)
Compress current figs 1–4 (conditional-Z, QR-full, Spec B, τ=0.99
secular) into a single multi-panel "supporting tests" figure. These are
hourly results and remain valid; they belong in the report as the defense
behind the headline, not as headline figures. Re-caption Spec A with the
mechanism this session found: heavier tail at low Z is what a
level-driven constraint story predicts, since low-Z intervals are the
sustained-load ones.

### F11 — What actually changed in 2026 (NEW)
Two panels answering the question F1 and F4b provoke — *if volatility is
flat, what drove the escalation?*

- (a) **Same load, different price.** P(congestion > $100) within fixed
  2,000-MW load bins, one line per year. The clean row is 20–22 GW, well
  sampled every year (n = 846 / 2,095 / 5,110 / 3,339): 1.89% → 5.58% →
  5.03% → **37.80%**. The same load level now produces $100+ congestion
  seven times as often as it did a year earlier.
- (b) **Decomposition.** Actual P(>$100) per year against a
  counterfactual applying 2023's conditional-response-given-load to each
  later year's load distribution. Load growth explains 85.2% of 2024's
  level, 59.1% of 2025's, and **12.2% of 2026's**.

**Two caveats that must appear in the caption, not a footnote.**

1. The 12.2% figure is unreliable in magnitude. 2023 barely visited the
   load levels 2026 reaches (n=10 in the 22–24 GW bin, zero above), so
   the counterfactual extrapolates where it has no support. The
   direction is solid; the number is not. Panel (a)'s 20–22 GW row is the
   defensible version of the same claim.
2. **The change is not local.** It is a step change in January 2026 in
   *both* components — congestion p90 $20.46 → $231.29, system energy p90
   $86.32 → $292.19 — and system energy is locationally uniform across
   PJM. So a substantial part of the 2026 escalation is system-wide, not
   a data-center-alley congestion story. The driver is **unidentified**;
   candidates (January cold snap, gas prices, PJM market-rule or capacity
   changes effective 2026) are untested, and we have **no non-DOM control
   pnode** because every pnode in the panel sits in DOM.

This figure exists to stop the rest of the set from being over-read. It
is the honest answer to the question the report otherwise raises and
declines to answer.

### Cut
- Current **fig 0a** (illustrative week) — superseded by F1/F3 and its
  2–5 AM shading now frames a deprecated default.
- Current **fig 6** (hourly vs 5-min companion) — the resolution
  comparison is not established (neither fit was block-bootstrapped;
  deflated they are ~+1σ and −0.7σ). Cutting rather than shipping a
  divergence claim that inference does not support.
- **fig 0b** (erratic week) — cut; F1 and F3 cover the same ground with
  the full panel rather than one hand-picked week.

### F10 — The 2024-07-10 NERC event (RETAINED as its own figure)
Decided at review: the documented data-center trip keeps a standalone
figure rather than being folded into F1. It is the one place in 3.4 years
where a large, *verified* load loss and a large price response coincide —
1,479 MW in five minutes, system energy $134.25 → $53.17 — and it
doubles as the positive control that validates the artifact screen used
elsewhere (the three larger apparent excursions moved price $0–4).

Source: the existing fig-0c supplemental 5-min pull. Re-caption to carry
the positive-control role, which is new.

## Cross-cutting requirements

**Every figure carries provenance** in a footnote: source parquet, n,
window, and specification. The current script does this well; keep it.

**Resolution labelling.** All figures state hourly vs 5-min explicitly —
the bug fixed in `c4a64e7` existed because this was implicit.

**Zonal-aggregate disclosure.** F1, F2 and F6 rest on a zonal load
aggregate (and a Southern-Region proxy for DOM). Each carries a one-line
caption noting that individual facilities may swing while the aggregate
smooths, and that this is structural — DOM resolves to a single
`load_area`, per-customer load is confidential, and dispatch prices
against unpublished State-Estimator bus loads.

**Artifact handling.** The extreme reversion excursions (>1,500 MW, ~4
cases) are almost certainly artifacts — they move system energy price
$0–4 where a confirmed-real 1,479 MW trip moved it $81. Figures touching
the Z tail (F5, F6, F8) get an exclusion-robustness annotation. The
broader ~3,193-spike class is **not** established as artifactual and is
not filtered.

**No figure may state a coefficient's sign without showing the other
specification.** This is the central lesson of 2026-07-30 and applies to
F5 and F6 specifically.

## Implementation shape

`scripts/plot_subq1_results.py` is 713 lines and would roughly double.
Split it:

- `scripts/figures/_style.py` — shared palette, fonts, provenance-footer
  helper (currently duplicated per figure)
- `scripts/figures/descriptive.py` — F1–F4
- `scripts/figures/inference.py` — F5–F7
- `scripts/figures/mechanism.py` — F8–F9
- `scripts/plot_subq1_results.py` — thin orchestrator

Each module is independently runnable so a single figure can be
regenerated without recomputing the set. F5 and F6 need bootstrap results
that take ~15 minutes; those must read from a cached JSON produced by a
separate compute step, never recomputed inside plotting code.

**New compute step:** `scripts/compute_figure_inputs.py` writes
`outputs/figure_inputs/*.json` (spec-sensitivity CIs, τ-sweep CIs,
monthly aggregates). Plotting reads only from that. This keeps figures
reproducible in seconds and makes the expensive statistics reviewable as
data.

## Review decisions (2026-07-30)

1. **F9 condensation** — *resolved:* compress the four mechanism figures
   into one.
2. **Figs 0b/0c** — *resolved:* 0b cut; the NERC event gets its own
   figure (now F10).
3. **F5 framing** — *resolved:* too methodological to headline. F2 leads;
   F5 moves to an appendix, with a mandatory plain-language statement of
   the fragility in the main text.
4. **Report deliverable** — *resolved at review:* these are **report
   figures** for the single hybrid technical/accessible document, not a
   separate advisor deck.
