# Phase 3 methodology — threshold autoregression + quantile regression

**Status.** Design spec, 2026-05-11. Input to a subsequent implementation
plan (writing-plans skill).

**Supersedes.** Proposal §Methodology Phase 3, which committed to a
Generalized Pareto Distribution (GPD) fit on LMP exceedances. See
`docs/decisions.md` § "2026-05-11 — Phase 3 method: TAR + quantile
regression (supersedes proposal §Methodology Phase 3 GPD framing)" for
the rationale and supersession record.

**Scope.** This spec covers Phase 3 (statistical analysis) only. Phase 1
(acquisition) is implemented in `src/surg/acquisition/`. Phase 2 (signal
isolation) is folded into the preprocessing stage here. The
forecasting deliverable (year by which projected volatility crosses `ĉ`)
is described in §7 at design level only — a sibling spec will handle its
implementation.

---

## 1. Scientific objective

**Proposal's question.** At what data-center-driven load-volatility
threshold (in MW/min) does the DOM-zone congestion-price response
transition from a roughly linear regime to a heavy-tailed, regime-changing
regime?

**Refined question** (in light of PJM's *Formation of LMP under Reserve
Shortage Events* and the cascading-failures literature):

> At what hourly-averaged DOM load gradient (MW/min equivalent) does the
> marginal probability of a Synchronized Reserve event in the
> MidAtlantic-Dominion (MAD) sub-zone become significant, and what is the
> corresponding regime change in Loudoun-cluster congestion price?

The phase transition is **mechanistic**, not emergent. PJM's Market
Clearing Engine hard-codes a step function: when reserves fall below
requirement, ORDC penalty factors ($850/MWh Synchronized Reserve, $300/MWh
Primary Reserve) are added to system energy LMP. The cascading-failures
literature corroborates this framing — "power grid blackouts follow a
**first-order** phase transition" (discrete jump, not continuous gradient).

This refined framing is what TAR / threshold-regression methods are
designed to estimate, and what GPD / continuous-tail methods are not. The
literature corroboration for first-order (discrete) over continuous is the
deciding factor; see §11.

**Deliverable.** A point estimate `ĉ` (MW/min) with 95% confidence
interval and a Hansen-bootstrap p-value on the existence of the threshold.
Conditional quantile regression provides an independent robustness
estimate of the same value. Mechanism validation via sync-reserve events
confirms the chain `load volatility → reserve depletion → ORDC trigger →
LMP spike`.

---

## 2. Pipeline architecture

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  1. Acquisition     │     │  2. Preprocessing   │     │  3. Analysis        │
│  (existing module   │ ──▶ │  (new module        │ ──▶ │  (new module        │
│  + 3 new feeds)     │     │  src/surg/prep/)    │     │  src/surg/analysis/)│
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
       │                              │                            │
       ▼                              ▼                            ▼
  data/raw/                     data/interim/                 outputs/
  parquet chunks                analysis_panel.parquet        - fitted TAR (ĉ, p, AR coeffs)
  per feed                      (single hourly panel,         - QR curve + slope-kink est
                                joined LMP+load+reserves,     - mechanism-validation tables
                                filtered to shoulder+2-5AM)   - robustness appendix
                                                              - forecast year (downstream)
```

**Stage 1 — Acquisition extension.** Add three feeds to
`src/surg/acquisition/`:

- `sync_reserve_events` — event log with `event_start_ept`,
  `event_end_ept`, `duration`, `synchronized_sub_zone` (filter to
  `MidAtlantic-Dominion (MAD)`). The directly-observable manifestation of
  the ORDC trigger.
- `reserve_market_results` — RT reserve clearing prices; corroborates the
  shortage events and quantifies severity.
- `operational_reserves` — reserve quantity time series for descriptive
  context on reserve margin trajectory.

The orchestrator may need minor extension to handle zone/sub-zone
aggregates (vs the nodal feeds it currently supports).

**Stage 2 — Preprocessing.** New module `src/surg/preprocessing/`. Single
responsibility: produce `data/interim/analysis_panel.parquet` — a clean
hourly panel with all features needed downstream. Filters applied at this
stage (not at analysis time). Schema in §3.

**Stage 3 — Analysis.** New module `src/surg/analysis/`. Submodules:

- `tar.py` — Hansen TAR estimator with bootstrap test (§4).
- `qr.py` — conditional quantile regression at τ=0.99 (§5).
- `mechanism.py` — Granger causality, cross-tabulation, and power-law fit
  on event durations (§6).

Each submodule consumes `analysis_panel.parquet` and produces independent
output artifacts in `outputs/`. Forecasting (§7) sits downstream; a sibling
spec covers its implementation.

---

## 3. Preprocessing layer — `data/interim/analysis_panel.parquet` schema

**Identifiers & metadata**

- `datetime_beginning_ept` — primary key, hourly, EPT
- `in_shoulder_season` — bool, month ∈ {3,4,5,9,10,11}
- `in_2_5am_window` — bool, hour ∈ {2,3,4}
- `passes_proposal_filter` — `in_shoulder_season AND in_2_5am_window`
- `dst_transition_hour` — bool; spring-forward gives one missing
  row/year naturally (no explicit drop)

**Load + volatility (TAR threshold variable)**

- `dom_load_mw` — from `hrl_load_metered`, zone=DOM
- `dom_load_gradient_mw_per_hr` = `dom_load_mw.diff(1)`
- `dom_load_gradient_abs_mw_per_min` = `abs(dom_load_gradient_mw_per_hr) / 60`
  — **the TAR threshold variable**
- `dom_load_gradient_signed_mw_per_min` — for asymmetry sensitivity

**LMP — response & controls**

Pooled (primary):
- `congestion_price_rt_cluster_mean` — Loudoun pooled (LOUDOUN,
  PLEASANT VIEW, GOOSECRE, BRAMBLET, MOSBY, SKFFSCRK), mean across pnodes
- `congestion_price_rt_cluster_max`
- `total_lmp_rt_cluster_mean` — secondary TAR fit target (cleaner test of
  the ORDC mechanism, since the penalty lands in system energy LMP rather
  than in the congestion component) and for ORDC-mechanism visualization

Per-pnode (separate fits + controls):
- `congestion_price_rt_ashburn_tx1`, `_tx2` — distinct fit (35 KV
  distribution-side, different physics per decisions.md 2026-05-10)
- `congestion_price_rt_ox`, `_bristers` — outside-cluster controls
- `congestion_price_rt_dom_zonal` — zonal baseline

**Reserves & events (mechanism observables)**

- `sync_reserve_event_active` — bool, joined from `sync_reserve_events`:
  `event_start ≤ t < event_end AND sub_zone = MAD`
- `sync_reserve_event_id` — non-null when active, groups consecutive
  event hours
- `hours_to_next_sync_event`, `hours_since_last_sync_event` — lead-lag
- `sync_reserve_clearing_price_rt`, `primary_reserve_clearing_price_rt`
  — from `reserve_market_results`, aggregated to hourly mean

**Time alignment**

- All EPT. `rt_hrl_lmps` is hourly natively; aligns to load directly.
- DA LMP from `da_hrl_lmps` is forecast for the same hour; sibling
  `da_panel.parquet` exists but is not joined into the primary panel.
- 5-min `rt_fivemin_hrl_lmps` excluded from the primary panel; if used
  for the secondary 5-min analysis, a separate
  `analysis_panel_5min.parquet` would broadcast hourly load down 12-fold.
- DST: spring-forward skips one 2-3 AM EPT hour per year — naturally
  absent from data. Fall-back affects 1 AM EPT, outside the filter.
- NaN handling: drop rows missing `dom_load_mw` OR `congestion_price_rt`
  for any primary pnode. Surface drop rate; investigate if > 1%.

**Output is versioned.** `schema_version` constant in the module; bump
on schema changes; analysis loaders refuse to operate on stale schemas.

**Joint analysis window** (after acquisition windows are joined and
filtered): 2024-05-26 → 2026-05-10, hourly grain, shoulder + 2-5 AM
filter. Expected count ~1,053 hours (see §4 sample-size concern).

---

## 4. TAR (primary fit) — Hansen 1996/2000

**Model:**

```
Y_t = α₀ + α₁·Y_{t-1} + ε_t   if  Z_t ≤ c     (low-volatility regime)
Y_t = β₀ + β₁·Y_{t-1} + ε_t   if  Z_t >  c     (high-volatility regime)
```

- **Y_t** = `congestion_price_rt_cluster_mean` at hour t (after filter)
- **Z_t** = `dom_load_gradient_abs_mw_per_min` (threshold variable)
- **c** = threshold (estimated; the proposal's MW/min deliverable)
- **Y_{t-1}** = lag-1 hour congestion price from the *unfiltered* time
  series (preserves natural autoregressive structure even though we only
  model 2-5 AM observations)

**Specification choices:**

| Choice | Default | Reasoning |
|---|---|---|
| AR order p | 1, bump to 2 if Ljung-Box residual autocorr is significant | Parsimony; hourly LMP at 2-5 AM has limited within-night persistence |
| Threshold grid | 15th–85th percentile of Z, ~300 evenly-spaced quantiles | Hansen canonical |
| Trim parameter (min fraction in each regime) | 0.15 | Protects against degenerate "one obs above threshold" fits |
| Bootstrap reps for Hansen test | 1,000 | Stable p-values |
| Standard error method | Hansen bootstrap (not asymptotic Wald) | Threshold parameter has non-standard distribution under H₀ |

**Outputs (`outputs/tar_fit.json`):**

- `c_hat` — point estimate, MW/min
- `c_hat_ci_95` — 95% CI via Hansen bootstrap
- `alpha`, `beta` — regime AR coefficients
- `hansen_p_value` — p-value for H₀: "no threshold"
- `regime_counts` — n_low, n_high observations
- `ljung_box_p_low`, `_high` — residual autocorr diagnostic; if < 0.05 in
  either regime, bump p to 2 and re-fit

**Secondary fit on `total_lmp_rt_cluster_mean`.** Run the identical TAR
specification in parallel with total LMP as response. The ORDC penalty
mechanism lands in system energy LMP (not directly in congestion price),
so this fit is the *cleaner test of the mechanism itself*; the primary
congestion-price fit answers the *proposal's specific framing*. Both
results are reported. Strong agreement between the two (both reject H₀,
similar `ĉ` values) is the cleanest version of the result. Divergence
(e.g., total LMP shows a threshold but congestion does not) tells us the
mechanism fires but doesn't transmit cleanly to the congestion
component — still a valid finding, but a different story than the
proposal expects.

**Sample-size concern.** Joint window × shoulder × 2-5 AM filter gives
~1,053 hours. If the "above threshold" regime contains < 50 hours,
Hansen's bootstrap power is marginal. Mitigation: pre-decided to verify
first; if regime count is < 50, expand night window to 11 PM – 6 AM
(triples sample) and document as a deliberate departure from the
proposal's strict 2-5 AM filter.

---

## 5. Quantile regression (robustness) — `Q_0.99(Y | Z)`

Three parallel specifications, each at τ = 0.99:

1. **Linear baseline:** `Q_0.99(Y|Z) = γ₀ + γ₁·Z`. Captures monotonic
   conditional-quantile slope. Should be statistically significant in
   the direction of TAR.
2. **Threshold dummy at TAR's `ĉ`:**
   `Q_0.99(Y|Z) = δ₀ + δ₁·Z + δ₂·(Z − ĉ)·I(Z > ĉ)`.
   Tests whether the slope changes specifically at the TAR-estimated
   threshold.
3. **B-spline basis (3-5 knots at Z quintiles):** `Q_0.99(Y|Z) = f(Z)`,
   non-parametric. The slope-change location estimated from this curve
   is *independent* of TAR. Compare against `ĉ`.

**Inference.** Quantile coefficients use rank-score inversion for CIs.
Bootstrap-the-residuals for the spline curve (B = 500).

**Outputs (`outputs/qr_fit.json`):**

- `linear_slope` (spec 1) with CI
- `kink_dummy_coef` (spec 2) δ₂ with CI and p-value
- `spline_kink_location` (spec 3) point estimate with bootstrap CI
- Comparison block: `|c_hat_TAR − kink_location_QR|` and a
  pre-registered agreement criterion (see below)

**Agreement criterion** (what counts as "robust"):

- `|c_hat_TAR − kink_location_QR| < 0.5 · SD(Z)` (loose) or `< 0.2 · SD(Z)`
  (strict).
- Spec 2 `δ₂` significant at α = 0.05.
- Both methods reject the null of "no nonlinearity" (Hansen bootstrap
  p < 0.05; spec 1 vs spec 3 likelihood-ratio test p < 0.05).

If TAR rejects and QR does not → suspect spurious piecewise-AR shape.
If QR rejects and TAR does not → suspect nonlinearity is in the
conditional quantile shape only; QR's result stands as primary.

---

## 6. Mechanism validation

Three tests on the chain `load volatility → reserve depletion →
sync_reserve_event → ORDC penalty → LMP spike`.

**Test 1: Granger causality** (proposal Phase 3 commits to this). Does
`dom_load_gradient_abs_mw_per_min` Granger-cause sync-reserve-event
occurrence in the MAD sub-zone, at lags 1, 2, 3 hours? Standard F-test.

**Test 2: Conditional regime test.** Among hours where `sync_reserve_event_active`,
what fraction have `Z > ĉ`? Compare to the unconditional fraction.
Effect size = `P(Z > ĉ | event active) − P(Z > ĉ | event inactive)`.
Strongly positive = mechanism confirmed.

**Test 3: Cross-tabulation.** 2×2 of (Z > ĉ) × (event active), with χ²
test of independence. Discordance type matters for interpretation:

- Many (Z > ĉ AND event inactive): "volatility above threshold but
  reserves held" — threshold too low or volatility doesn't transmit to
  reserves cleanly.
- Many (Z ≤ ĉ AND event active): "reserve events fire without high load
  volatility" — other drivers (gen outages, transmission contingencies)
  are dominant.

**Tertiary robustness — power-law fit on sync_reserve_event durations.**
Following the Texas SOC paper (arXiv 2504.10675), fit a power-law
distribution to event durations: `P(duration > x) ~ x^(−α)`. If the
system is near criticality, α should be near or below 1 (the Zipf
threshold). This is an *independent* check on whether observed event
durations exhibit the heavy-tailed signature of self-organized criticality
— our TAR threshold being statistically valid doesn't require this, but
agreement strengthens the broader narrative.

**Outputs (`outputs/mechanism_validation.json`):** Granger F-stats and
p-values per lag; conditional-regime fractions and effect size; 2×2
table with χ² result; power-law α with bootstrap CI.

---

## 7. Forecasting layer (downstream, separate spec)

Given `ĉ` (MW/min) and a projected load-volatility trajectory
`{V(year): year ∈ [2026, 2040]}`, find `y*` = the earliest year such that
`V(y) > ĉ` "permanently" (definition: P(Z > ĉ in year y) ≥ 50% for all
y ≥ y*; sensitivity on the probability threshold).

**Projection model — two paths:**

- *Scaling.* Compute current volatility-per-data-center-MW; multiply by
  JLARC's projected data-center MW trajectory. Assumes load-volatility
  profile is invariant per MW.
- *Distributional shift.* Assume current Z distribution shifts in
  location or scale by JLARC's growth factor (factor of ~2.9× by 2040
  per the unconstrained scenario; 2.0× by 2034).

Both are speculative extrapolations and will be presented in the paper
as conditional projections, not predictions.

**JLARC baseline:** the unconstrained-demand scenario shows DOM total
energy going from ~10,500 GWh/month (2024) to ~30,500 GWh/month (2040).
PJM's adjusted forecast tracks JLARC closely. Half-of-unconstrained
gives ~21,500 GWh/month at 2040.

**Defer to sibling spec.** Implementation comes after the TAR/QR analysis
stabilizes. JLARC data is not yet pulled or processed.

---

## 8. Failure modes

| Failure | Diagnostic | Response |
|---|---|---|
| Hansen test fails to reject "no threshold" | p > 0.10 | Report null result; quantify power given n; suggest Historic-data extension to widen window |
| TAR `ĉ` lands at boundary (≥ 95th pct of Z) | `ĉ` in trim region | Trim 0.15 should prevent; if not, report as boundary degenerate |
| TAR and QR disagree on kink location | \|ĉ_TAR − ĉ_QR\| > 0.5 SD(Z) | TAR may be over-fitting piecewise-AR shape; trust QR; report both |
| Controls (OX, BRISTERS, DOM zonal) also show same threshold | Bootstrap p < 0.05 with similar `ĉ` | Phenomenon is DOM-wide, not Loudoun-specific; reframe — still a finding |
| sync_reserve_events fires zero times in window | Zero count of `sync_reserve_event_active = True` | Mechanism unfalsifiable; fall back to `reserve_market_results` clearing prices; discuss in paper |
| High-volatility regime has < 50 hours after filter | Regime occupancy count | Pre-decided mitigation: widen window to 11 PM – 6 AM; document as deliberate departure |
| Power-law fit on event durations rejected | KS test rejects power-law | SOC framing may be wrong for our window; TAR result stands on its own; report negative result for the tertiary check |

---

## 9. Testing strategy

**Unit tests on TAR / QR estimators against synthetic data.** Generate
Y given Z and a hand-coded threshold; verify recovery within ε under
multiple noise levels. Test edge cases: threshold at quantile boundary,
degenerate regimes, low signal-to-noise.

**End-to-end smoke** — pipeline runs against a tiny analysis panel
(e.g., one shoulder season's worth, ~200 hours) and produces non-NaN
outputs of expected shape. Catches schema/pipeline bugs without long
fit times.

**Robustness on the actual fit:**

- Subsample 80% bootstrap × 200 reps — `ĉ` distribution should be tight.
- Drop one shoulder season (e.g., Sep-Nov 2025) — leave-one-out stability.
- cluster_max vs cluster_mean — same `ĉ` neighborhood, different
  magnitude of regime difference.
- Per-pnode separate fits vs pooled — pooled `ĉ` should be a
  weighted average of per-pnode `ĉ_i`'s.

---

## 10. Limitations (to acknowledge in the paper)

**Time-scale gap.** AI workload dynamics happen on millisecond-to-second
timescales (per Li & Li 2025: training checkpoints cause "wide swings
within a fraction of a second"; "large-scale GPU clusters can produce
power fluctuations of hundreds of megawatts within only seconds" per
Chen et al. 2025). Our hourly DOM load gradient is a 4-order-of-magnitude
smoothed proxy. The threshold we estimate is "effective hourly-averaged
ramp rate at which the integrated reserve depletion fires ORDC,"
*not* "instantaneous physical ramp rate." This is a known limitation
of the data we can access (DOM-specific load is hourly only; PJM's 5-min
`inst_load` is region-only, mixing DOM with DAY/EKPC/etc.). The estimated
threshold is still a valid scientific quantity and a valid grid-stability
indicator — but it is the *macro effective* threshold, not the *micro
physical* one.

**Identification.** Even after the shoulder + 2-5 AM filter and the
sync-event mechanism conditioning, residual confounding exists. The TAR
threshold is the load-volatility level at which DOM-cluster congestion
response *changes regime in our filtered subset*. Generalizing to "this
will happen in the future given JLARC's load trajectory" requires
extrapolation that compounds these caveats.

**Response variable choice.** The primary fit uses congestion price to
match the proposal's "DOM-zone congestion pricing" framing. The ORDC
penalty mechanism technically lands in *system energy* LMP, not in
congestion LMP. During shortage events the two are highly correlated
(reserve-shortage dispatch also stresses transmission, raising the
congestion component), so the congestion-price fit picks up the shock
indirectly — but it is not the cleanest test of the mechanism. The
parallel total-LMP fit (§4 *Secondary fit*) provides that cleaner test.
Where the two fits diverge, the paper will report both.

**Window size.** ~2 years of nodal data (2024-05-26 → 2026-05-10) is the
limit of what PJM Data Miner 2's Standard window allows. Pre-2024 nodal
data is in PJM's Historic tier and not retrievable by `pnode_id`, only
by pulling the entire feed for each calendar year. A future extension
of acquisition could open this.

**Post-Oct-2022 LMP rule regime only.** PJM's reserve price formation
rules changed on 2022-10-01 (system energy LMP cap at $3,700/MWh,
elimination of iterative-cap logic). Our entire analysis window is
post-rule-change, so we don't span the structural break — but it limits
direct comparability to studies that use pre-2022 nodal data.

---

## 11. Literature support

**For first-order discrete phase-transition framing** (vs continuous):

- Hines, Balasubramaniam, Sanchez (2009), *Cascading failures in power
  grids* — proposal reference [8]. Foundational SOC framing.
- Cascading-failures lit consensus: "power grid blackouts follow a
  first-order phase transition" (multiple peer-reviewed sources).
- "Predicting Power Grid Failures Using Self-Organized Criticality: A
  Case Study of the Texas Grid 2014-2022" (arXiv 2504.10675) —
  methodologically close. Power-law exponent α on outage sizes; α < 1
  defines criticality. Inspires our tertiary power-law check on event
  durations.

**For LMP mechanism (the ORDC step function):**

- PJM (March 2023), *Formation of Locational Marginal Pricing and its
  System Energy Component During Reserve Shortage Events* — proposal
  reference [10]. Walks through the March 17, 2021 example.
- Hogan & Harvey (2022), *Locational Marginal Prices and Electricity
  Markets* — proposal reference [11]. Theoretical foundation;
  conceptually subsumed by the PJM ORDC paper for our purposes.
- PJM Manual 11, *Energy & Ancillary Services Market Operations* —
  proposal reference [4]. Operational details.

**For AI workload volatility (the proposal's premise):**

- Li & Li (2025), *AI load dynamics — a power electronics perspective*
  — proposal reference [2]. Documents training/inference power swings
  on millisecond timescales (LLaMA-3.1 8B: 25 A swings in <200 ms;
  GPT-2 training: "wide swings within a fraction of a second").
- Chen, Wang, Colacelli, Lee, Xie (2025), *Electricity demand and grid
  impacts of AI data centers* — proposal reference [3]. "Large-scale
  GPU clusters can produce power fluctuations of hundreds of megawatts
  within only seconds." US data center load: 25 GW (2024) → 80+ GW
  (2030). PJM capacity prices 2026-2027: $329.17/MW vs $28.92/MW for
  2024-2025 (>10× increase).

**For DOM-zone load growth and forecast layer:**

- JLARC (December 2024), *Data Centers in Virginia* — proposal reference
  [1]. Unconstrained Virginia data center load: ~10,500 GWh/month
  (2024) → ~30,500 GWh/month (2040). PJM's forecast tracks JLARC
  closely.
- Monitoring Analytics (2024-2025), *State of the Market Reports* —
  proposal references [6][7]. Recent DOM-zone congestion specifics.
  Gridstatus blog summarizes: "Nodal volatility within Dominion can
  stand out against the rest of PJM."

**On TAR methodology specifically:**

- Hansen, B.E. (1996), *Inference when a nuisance parameter is not
  identified under the null hypothesis*. The bootstrap test for
  threshold significance.
- Hansen, B.E. (2000), *Sample splitting and threshold estimation*.
  Inference framework for the threshold parameter.

---

## 12. Deliverables

The pipeline produces these durable artifacts:

```
outputs/
├── tar_fit.json              # point estimate ĉ ± 95% CI, regime coeffs, Hansen p-value
├── qr_fit.json               # linear slope, kink-dummy coef at ĉ, spline-kink location
├── mechanism_validation.json # Granger F, conditional regime, 2×2 cross-tab, power-law α
├── robustness/
│   ├── subsample_bootstrap.parquet
│   ├── leave_one_season_out.parquet
│   ├── cluster_max_vs_mean.parquet
│   └── per_pnode_vs_pooled.parquet
└── figures/
    ├── scatter_Z_Y_overlays.png      # main: scatter with TAR breakpoints, QR spline, events highlighted
    ├── qr_spline_curve.png
    ├── mechanism_crosstab_heatmap.png
    ├── event_duration_power_law.png  # log-log with fitted α
    └── robustness_fan.png            # bootstrap CI fan around ĉ
```

Plus a methodology section + figures for the eventual paper.

---

## 13. Outstanding decisions

- **Advisor input.** Prof Wei / Lihui have not yet reviewed this design.
  Their input may push toward keeping GPD in parallel (for proposal-
  fidelity reasons) or specific operational refinements. If so, run GPD
  in parallel and present both with a comparison.
- **Aggregation function for the Loudoun cluster: mean vs max.** Default
  is mean (preserves more signal). Switch to max if mean over-smooths
  the shortage events. Decide empirically after the first fit.
- **Sample-size mitigation.** Pre-decided: verify first, mitigate only
  if the high-volatility regime has < 50 hours. Mitigation = widen night
  window to 11 PM – 6 AM (triples sample, departs from proposal's strict
  2-5 AM filter).
- **`reserve_market_results` granularity.** RT clearing prices are
  available at 5-min — do we aggregate to hourly mean, max, or any-
  nonzero indicator? Mean is the safe default; the indicator (any
  shortage in this hour) may be more interpretable. Decide during
  preprocessing implementation.
- **Power-law fit window.** All sync_reserve_events in the joint
  analysis window, or just shoulder-season subset? The former is more
  data; the latter aligns with the rest of the analysis. Default: use
  the full analysis window for the power-law fit (it's a robustness
  check, not part of the primary identification).
