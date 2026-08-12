# Did Irish Load Shape Change as Data Centres Reached 23.7% of Consumption?

> **⚠️ QUALIFIED 2026-08-12 by `L-solar-metering-artifact.md` § 8 — read that
> before quoting anything below.** The Dutch series changes definition at
> 2023-04, so every 2015→2025 comparison in this note pairs a pre-break Irish
> endpoint with a post-break Dutch one. On a break-free 2015→2022 window the
> headline matched null on `vol_norm` **does not survive** (×0.814 vs ×0.971,
> not ×0.719 vs ×0.714). What does survive, and is cleaner: the decline is a
> denominator effect, and the raw-numerator null (r = −0.078 IE vs −0.133 NL).
> The numbers in this note are correct as computed and are left unedited; the
> window they are computed over is the problem.

Analysis date: 2026-08-12. Fills the empty "European energy markets" section of
`docs/plans/2026-08-19-advisor-meeting-agenda.md`.

Scripts: `scripts/entsoe_fetch.py`, `scripts/cso_fetch.py`,
`scripts/entsoe_ireland.py`. Outputs: `outputs/entsoe/`
(`ireland_results.json`, `shape_annual_hourly_*.csv`,
`shape_quarterly_with_dose_*.csv`, `fig_diurnal_profiles.png`,
`fig_shape_trends.png`). Design and probe evidence:
`docs/plans/2026-08-12-entsoe-ireland-design.md`. API mechanics:
`docs/entsoe-api-constraints.md`.

---

## 0. Headline — the shape changed, and the control changed identically

**Irish load flattened substantially between 2015 and 2025. So did Dutch load,
by the same amount, over the same years, at the same hours — with a data-centre
share that never moved.** The Irish change is not attributable to data centres
on this evidence.

| 2015 → 2025, hourly panel | Ireland (DC 4.4% → 23.7%, 2015Q1→2025Q4) | Netherlands (DC 1.5% → 4.6%, **2017→2024** — CBS starts 2017) |
|---|---|---|
| mean load | **×1.298** | ×1.196 |
| raw mean \|Δload\| (MW/min) | **×0.933** | **×0.854** |
| `vol_norm` = \|Δload\| ÷ mean load | **×0.719** | **×0.714** |
| `pt_ratio` (daily peak ÷ trough, median) | 1.694 → 1.399 | 1.669 → 1.363 |
| `night_floor` (daily min ÷ daily mean) | 0.722 → 0.823 | 0.715 → 0.840 |

Five findings carry it.

1. **The `vol_norm` decline is mostly a denominator effect, and it replicates in
   the control.** Ireland's normalized volatility fell 28% — but raw absolute
   volatility fell only 6.7% while mean load grew 30%. The control fell 28.6%,
   statistically indistinguishable, and its *raw* volatility fell **more**
   (−14.6% vs −6.7%). This project has already retracted one "normalized
   volatility falls" claim for exactly this reason (ISONE, +9.9%, a shrinking-load
   denominator effect). Ireland is the mirror case — a growing denominator — and
   the same discipline applies: **report the numerator.**
2. **On the raw numerator, the dose correlation is identical in treated and
   control.** `mean_abs_grad` vs Irish DC share gives **r = −0.261 for Ireland
   and r = −0.268 for the Netherlands** (n=44 quarters each). The control,
   correlated against a covariate from a country it has no exposure to, tracks
   it just as well. That is the cleanest null in this note.
3. **The mechanism is real but shared: the day flattened by filling in the
   night.** Ireland's normalized 00–05h floor rose 0.773 → 0.849; the
   Netherlands' rose 0.759 → **0.866**. The single largest hour-of-day change is
   **hour 3 in both countries** (+0.102 IE, +0.116 NL), offset by losses at
   midday (hour 13 IE −0.082, hour 11 NL −0.110). Peak hour is unchanged at 18h.
   Whatever flattened these two systems acted on the same hours in both, and
   harder in the one without data centres.
4. **Where Ireland genuinely differs is the *path*, not the endpoint.** Ireland's
   correlations with DC share are much stronger than the Netherlands' on the
   normalized statistics (`vol_norm` −0.850 vs −0.340; `pt_ratio` −0.855 vs
   −0.546; `night_floor` +0.898 vs +0.629). But the 2015→2025 *endpoints* are
   near-identical. The gap is explained by NL being noisier year to year — its
   2022 energy-crisis spike is plainly visible (`mean_abs_grad` jumps to 8.11
   from 6.88 in 2021, `pt_ratio` back up to 1.494) — which depresses a linear
   correlation without changing the trend. **Do not report the correlation gap
   as evidence of an Irish-specific effect.** Ireland's monotonicity is the one
   thing that is genuinely different, and monotonicity is not identification.

5. **The dose-response is absent, and if anything inverted** (§1.1). The control
   is **low-dose, not zero-dose** — a design claim that turned out to be wrong
   and was corrected after the first run. The Dutch share *tripled* too
   (×3.09 vs Ireland's ×3.19), but in percentage points Ireland took **4.8×**
   the increment. Per percentage point of dose, **the Netherlands moved 2.5–3.9×
   more** on every dimensionless statistic. Whichever way exposure is scaled —
   relative or absolute — there is no dose-ordering in the response.

**What would have been reported without three measurement corrections.** A naive
run would have shown a 26% `vol_norm` decline with no numerator, correlations of
−0.850 against a *measured* dose, and no control caveat — a publishable-looking
data-centre story. Each correction is in §4.

---

## 1. Why Ireland — the dose is measured, for the first time in this project

Every US result in this project used a **geographic proxy** for data-centre
exposure (Loudoun County, DOM zone, Ashburn pnodes). Ireland's CSO publishes
**metered data-centre consumption** as a national quarterly series (PxStat table
MEC02), which is the reason this market was worth the API access.

| CSO MEC02 | 2015Q1 | 2025Q4 | ratio |
|---|---|---|---|
| Data-centre consumption | 291 GWh | 1,991 GWh | **×6.84** |
| All metered consumption | 6,565 GWh | 8,420 GWh | ×1.28 |
| **Non-data-centre** (derived) | 6,274 GWh | 6,429 GWh | **×1.02** |
| **DC share** | **0.0443** | **0.2365** | **×5.33** |

The design carried "23.2% by 2025" from prior desk research; the measured 2025Q4
figure is **0.2365**, and the 2015 starting share — which the design explicitly
left unverified — is **0.0443**.

**The non-DC row is the striking one: Irish non-data-centre electricity
consumption was flat (×1.02) across eleven years.** Essentially all growth in
Irish metered electricity is data centres. As a treatment variable this is about
as clean as observational exposure gets — which is what makes the null in §0
informative rather than merely underpowered.

**What the covariate is not.** CSO has **no data-centre classification**. Sites
are identified heuristically — name matching, business-park location, meters
above 1 GWh — and CSO warns that new small sites fall below its thresholds.
The identification method therefore *drifts* over exactly the period being
measured. The series fixes the **existence and rough magnitude** of an exposure
trend. It does not identify which load is data-centre load.

### 1.1 ⚠️ The control is LOW-dose, not zero-dose — a design claim, corrected

The design described the Dutch data-centre share as **"flat at ~4.6%"**. That is
**false**, and it was checked only after the analysis was first run. CBS
(Statistics Netherlands) publishes the series, and **4.6% is the 2024 endpoint,
not a constant**:

| NL DC share of national electricity | 2017 | 2019 | 2021 | 2023 | 2024 |
|---|---|---|---|---|---|
| % | 1.48 | 2.42 | 3.29 | 4.19 | 4.58* |

\* provisional. Source: CBS, *"Data centres consume 4.6 percent of the
Netherlands' electricity"* (2025). Definition: connections where the data centre
**is the main activity** — excludes university and hospital data halls. ~200
sites; ~45 large ones are ~90% of consumption. **Not identical to CSO's Irish
heuristic, so cross-country *levels* are only roughly comparable; the
within-country trends are the usable part.**

**This kills the pure-placebo reading and replaces it with a dose-response test,
which is the stronger argument anyway.** Over the matched window CBS covers:

| 2017 → 2024 | Ireland | Netherlands |
|---|---|---|
| DC share | 6.85% → 21.86% | 1.48% → 4.58% |
| dose increment | **+15.01 pp** | **+3.10 pp** |
| dose *ratio* | **×3.19** | **×3.09** |

Two readings, and **both are negative**:

- **Relative dose.** The share **tripled in both countries** (×3.19 vs ×3.09) —
  near-identical growth, near-identical shape response. A pure null.
- **Absolute dose.** Ireland took **4.8× the percentage-point increment**. If
  data centres drove the flattening, Ireland should have moved ~5× as far.
  Instead, **per percentage point of dose the Netherlands moved 2.5–3.9× more**:

| per pp of DC share, 2017→2024 | Ireland | Netherlands | NL ÷ IE |
|---|---|---|---|
| `vol_norm` | −0.000011 | −0.000028 | **2.5×** |
| `pt_ratio` | −0.0145 | −0.0409 | **2.8×** |
| `night_floor` | +0.0049 | +0.0190 | **3.9×** |

That is an **inverted dose-response**. Only the dimensionless statistics are
compared here — raw `mean_abs_grad` is in MW/min and the Dutch system is ~3.4×
larger, so its per-pp figure is not comparable across countries and is excluded.

**What this does and does not license.** It does **not** license "data centres
reduce volatility" — the inversion is far more likely to reflect that both
systems are being flattened by something else (§5.3–5.4) that happens to have
moved further in the Netherlands. It **does** remove the possibility of reading
§0 as a data-centre effect: there is no dose-ordering in the response.

---

## 2. Data and coverage — measured, not assumed

Load: ENTSO-E 6.1.A Actual Total Load, 2015-01-01 → 2026-08-12, pulled 2026-08-12.

| | EIC | resolution | zone-years | native slots | missing |
|---|---|---|---|---|---|
| Ireland (CTA) | `10YIE-1001A00010` | PT30M | 12 | 199,830 | **3,774 (1.85%)** |
| Netherlands | `10YNL----------L` | PT15M | 12 | 407,206 | **0 (0.00%)** |

**Irish load and price come from *different* EIC codes.** Load is the control
area `10YIE-1001A00010` (Republic-only, unbroken 2015→2026 at PT30M); the SEM
bidding zone `10Y1001A1001A59C` returns load too, but it is **all-island** and
runs ~1,015 MW higher. Prior desk research (EU-0 §3) called the
all-island-vs-Republic footprint mismatch one of three disqualifying limits on
Ireland — **that was an artifact of picking the SEM code.** The CTA series is
Republic-only and matches the CSO covariate's footprint. Price is the opposite
asymmetry: the CTA EIC returns reason-999 on 12.1.D, so price must come from SEM.
Observed mean load of 3,832 MW for 2024 (vs ~4,850 expected on SEM) confirms the
right series is in hand.

### ⚠️ Data quality find: the Irish series has 661 gaps; the Dutch has none

3,774 of 203,604 expected Irish slots are absent, in **661 contiguous runs**:

| gap | span | slots |
|---|---|---|
| 2026-02-05 → 02-24 | 19 days | 920 |
| 2025-11-10 → 11-19 | 8.5 days | 412 |
| 2022-12-25 → 12-29 | 4 days | 198 |
| 2021-09-10 → 09-13 | 3 days | 148 |

The second coincides with the documented **6.1.A → R3 migration on 2025-11-10**.
Missing slots per year range from 8 (2019) to 1,104 (2026) — a 138× spread, and
the reason §4.1's correction is not optional.

**The fall-back hour is *omitted* rather than duplicated.** At the October DST
transition the Irish feed jumps from 22:30Z straight to 01:00Z. Consequently
`dst_transition_hour` is **0 for Ireland by construction**, against 22 for the
Netherlands (11 fall-backs × 2 hours). This is a property of the source, not of
the code.

`assert_panel_quality` from `src/surg/diagnostics/stage1.py` **fails** on the
Irish hourly panel (`expected ~101,803 rows, got 99,915`). That is a **true
positive** and was not loosened. Nothing in the Ireland analysis depends on it —
its only load-bearing caller is the (unrun) Italian driver.

**Hour completeness.** The hourly panel records `n_obs`, the number of native
slots behind each hourly mean. Ireland: **0 incomplete hours of 99,915.**
Netherlands: **1 of 101,802.** So gaps in this corpus are whole-hour or larger,
and no hourly value is a partial-hour average.

---

## 3. The statistics, side by side

Hourly panel, annual. Full tables in `outputs/entsoe/shape_annual_hourly_*.csv`.

| | IE 2015 | IE 2025 | Δ | NL 2015 | NL 2025 | Δ |
|---|---|---|---|---|---|---|
| mean load (MW) | 3,031 | 3,933 | +29.8% | 11,159 | 13,345 | +19.6% |
| `mean_abs_grad` (MW/min) | 2.321 | 2.165 | **−6.7%** | 8.130 | 6.940 | **−14.6%** |
| `vol_norm` | 0.000766 | 0.000551 | −28.1% | 0.000729 | 0.000520 | −28.6% |
| `pt_ratio` | 1.694 | 1.399 | −17.4% | 1.669 | 1.363 | −18.3% |
| `load_factor` | 0.652 | 0.661 | +1.5% | 0.579 | 0.682 | +17.8% |
| `night_floor` | 0.722 | 0.823 | +14.0% | 0.715 | 0.840 | +17.5% |

**On every statistic, the Netherlands moved as much as or more than Ireland.**

### Dose correlation with the low-dose control — never quote the Irish row alone

Pearson r against the **Irish** CSO DC share, n=44 quarters. The Dutch row is
correlated against a *foreign* covariate: if it correlates as strongly, the
Irish correlation is picking up a common European time trend rather than an
Irish exposure effect.

⚠️ **This is a weaker instrument than it was originally described as.** The
design assumed the Netherlands had no exposure trend, which would have made this
a true placebo. It has one (§1.1) — smaller in percentage points but of nearly
identical *ratio*. So a strong Dutch correlation here is no longer proof of a
spurious common trend; it is also consistent with a real effect present in both.
**The dose-response comparison in §1.1 is what discriminates, and it is the
result to lead with.** This table remains useful for one thing only: showing
that the raw numerator behaves identically in both countries.

| statistic | Ireland | Netherlands (low-dose control) |
|---|---|---|
| `mean_abs_grad` — the raw numerator | **−0.261** | **−0.268** |
| `vol_norm` | −0.850 | −0.340 |
| `pt_ratio` | −0.855 | −0.546 |
| `load_factor` | +0.331 | +0.157 |
| `night_floor` | +0.898 | +0.629 |

The raw numerator row is the honest one, and it shows **no differential
whatsoever**. The normalized rows carry Ireland's larger load growth in their
denominators, and their apparent gap is a noise artifact (§0.4).

---

## 4. Three measurement corrections, and what each was worth

These are deviations from the approved implementation plan. All were made
because the corpus violated an assumption the plan's formula relied on.

### 4.1 Gradients only across consecutive slots

`load.diff().abs() / freq_minutes` divides a **19-day** jump by 30 and calls the
result a per-minute gradient. With 661 gap runs, this is wrong arithmetic, not a
tolerance question.

Aggregate bias is small (+0.69%), but it **varies by year from +0.07% (2019) to
+2.31% (2022)** — a 33× spread driven entirely by gap frequency, which has
nothing to do with the phenomenon under study. A design that tests a *trend*
cannot carry a year-varying bias. Both zones run the identical code path (it is
a no-op on the gapless Dutch panel) so that a treated-vs-control difference can
never be a code difference — the Hirth et al. failure mode the design chose
single-sourcing to avoid.

### 4.2 Daily statistics use complete days only

`pt_ratio` and `night_floor` are daily max/min statistics. A day holding 4 of 24
hours contributes a garbage max/min to the median. Days are now admitted only at
full slot count; `n_days_used` and `n_days_dropped` are reported per period. The
asymmetry is visible and material — Ireland drops 101 days in 2022 and 62 in
2025; the Netherlands drops **2 per year**, which are the DST days.

### 4.3 The raw numerator is reported next to the ratio

`vol_norm` falls whenever load grows, whatever volatility does. Reporting
`mean_abs_grad` alongside makes the decomposition unavoidable. **This is the
correction that changed the conclusion** — see §0.1.

### Six fail-loud-or-measure fixes in the supporting modules

Found by review during implementation; all are the same bug class — a value that
should exist quietly not existing, leaving a plausible-looking number:

- **A03 expander:** duplicate positions silently dropped a value (last-wins) and
  pushed `sparsity` above 1.0. Now raises.
- **XML parser:** a `<Point>` with a position but no value was silently skipped.
  Under A03 the slot then forward-fills and the resulting sparsity is
  indistinguishable from legitimate compression. Now raises.
- **XML parser:** empty/self-closing value elements raised `TypeError` rather
  than the module's `ValueError` convention. Now consistent.
- **Panel builder:** `to_hourly` averaged incomplete hours silently. Now reports
  `n_obs` (which measured the risk at 1 hour in 201,717 — real but negligible).
- **Panel builder:** `build_zone_series` now drops **exact-duplicate point
  rows**. 12.1.D returns whole days in the *area's* timezone, so a day
  straddling a calendar-year boundary comes back from both adjacent year
  requests and `load_raw` concatenates two identical copies — 622 of 118,263
  Italian price rows, in 311 groups, all agreeing on value. Dedup keys on the
  value as well as the position, so a genuine *conflicting* duplicate still
  raises. **Found because the duplicate-position guard above fired on real
  data**; without it this would have silently produced wrong prices. Irish
  numbers are unaffected — 6.1.A windows are UTC-aligned, only price overlaps.
- **Italy driver:** joins zones on `timestamp_utc`, never `timestamp_local`.
  Local prevailing time repeats at the October fall-back, so it is not a unique
  key: merging six zones on it cross-joined those hours and inflated the panel
  from 101,802 to 146,836 rows. `assert_panel_quality` caught it — 45,056 rows
  flagged against a budget of 24.

---

## 5. Limits — the full list

1. **Not a causal design.** One treated unit, one control, n=44 quarters, and a
   heuristically-constructed covariate. No identification strategy. Nothing here
   supports a causal claim in either direction, including the null.
2. **The null is the informative part, and it is a *matched* null, not an
   absence of change.** Irish load shape changed a great deal. The claim is only
   that the change is not distinguishable from the control's.
3. **COVID (2020) and the 2022 energy crisis** sit inside the window and move
   both series. The 2022 Dutch spike is visible in every statistic.
4. **EV and heat-pump growth confound `night_floor` in the same direction as
   data centres** — all three add flat or overnight load. This confound is not
   separable here, and no attempt is made to explain *why* the control's night
   floor rose more; that would require the penetration data listed in §9.4,
   which was not gathered.
5. **The covariate's identification method drifts** over the measurement period
   (§1).
6. **Ireland is 1.85% incomplete and the Netherlands is not** (§2). Corrections
   in §4.1–4.2 address the arithmetic, not the underlying absence.
7. **The control is LOW-dose, not zero-dose** (§1.1). The design's "flat at
   ~4.6%" was wrong; the Dutch share tripled. This removes the pure-placebo
   reading and replaces it with the dose-response argument in §1.1, which is
   the stronger test anyway — but it must not be described as a placebo.
8. **The Netherlands is a *matched* control, not a randomized one.** It was
   chosen on total VRE share (42.8% vs 46.1%) and flat DC share, and it differs
   from Ireland in solar share (21.1% vs 4.7%), grid size (~3.4×), and
   interconnection. A common European trend is the most likely reading of §0, but
   "both moved together" does not by itself establish *which* common driver.
9. **2026 is a partial year** (to 08-12) and carries the largest gap. It is
   plotted but should not be read as an annual figure.

---

## 6. Comparison discipline — what may and may not be put in one column

- **`vol_norm` levels are NOT comparable to the 11 existing Stage-1 panels.**
  An hourly panel derived by *averaging* sub-hourly data is low-pass filtered and
  reads smoother than a natively-metered hourly series. **Within-zone trends are
  comparable**, and the trend is what this tests. Levels are not.
- **The UKPN 1.05 figure must not appear in the same column as `pt_ratio`.**
  UKPN is half-hourly, per-site, and a *utilisation ratio* against contracted
  capacity, not MW. It is a facility-level contrast for prose only. The
  zonal-to-zonal comparison that *is* licensed: IE 2025 `pt_ratio` **1.399** and
  NL **1.363** against **ISONE hourly 1.467** — same statistic, same basis,
  same units.
- **The 2015→2025 endpoint ratios, not the correlation coefficients, are the
  fair treated-vs-control comparison** (§0.4).

---

## 7. Italy — robustness check, run

`scripts/entsoe_italy_stage1.py`, 168 zone-years pulled. **A ROBUSTNESS CHECK,
NOT A FINDING** — EU-0 §1 argues European zones are panels 12–13 of a result
already 11-for-11 including a near-zero-data-centre control.

**Result: level beats |gradient| in 36 of 36 cells**, in both the max
(2015→2026) and the 2023-01→2025-04 overlap window. 6 zones × 6 price series.
Consistent with all 11 prior panels; nothing here disturbs the Stage-2 gate
ruling.

**Coverage is perfect — 101,802 hourly rows per zone, 0 missing, all six
zones.** Unlike Ireland's 1.85%. `assert_panel_quality` passes.

**IT_CALABRIA is excluded.** It was split out of IT_SOUTH and only becomes a
bidding zone on **2021-01-01**: both 6.1.A and 12.1.D return reason 999 for
2015–2019, and 2020 carries a single stray row. Including it would have forced
the cross-zone inner join down to 2021+, discarding six years from the other
six zones, and would have put a composition break mid-panel. It is reported in
the driver's coverage table, then dropped — visibly, not silently.

**Normalized volatility 2015→2025 falls in 5 of 6 zones** (−7.8% to −14.2%) and
**rises in IT_SARDINIA (+4.7%)**. That lone inversion matters: together with
ISONE's +9.9% it is further evidence that "normalized volatility falls in every
panel" is dead as a general claim.

Terna is **not** cross-checked. Hirth et al. (2018) found >10%
TSO-vs-Transparency-Platform load deviations, and Italy is the one place in this
design where that would matter — still open.

---

## 8. What this changes

1. **A measured-dose test now exists**, and it returns the same answer the
   proxy-based US tests did. The sub-q1 null was previously vulnerable to "your
   exposure variable is a geographic proxy." On a market where exposure is
   metered and grew 5.3× to nearly a quarter of national consumption, the
   shape response is indistinguishable from a matched control.
2. **The ISONE-style denominator trap recurred and was caught.** Two markets, two
   directions (ISONE shrinking, Ireland growing), same artifact. This is now a
   standing hazard of `vol_norm`, and `mean_abs_grad` should be reported beside
   it everywhere in this project, not just here.
3. **A per-market coverage claim was measured rather than asserted** — IE 1.85%
   incomplete in 661 runs, NL 0.00%. Per-market depth claims in this project have
   been falsified three times before; this one is a measurement.
4. **EU-0 §3's footprint objection to Ireland is void** (§2), and should not be
   cited again without the CTA/SEM distinction.
5. **No `docs/decisions.md` entry is written by this note.** The append-only log
   should record the probe findings that overturned EU-0/EU-2, the seven plan
   deviations with their reasons, and the headline — but that is a separate,
   deliberate write.

## 9. Open items

1. **Run the Italian robustness check** (§7), or record a decision not to.
2. **EirGrid validation.** EirGrid publishes Northern Ireland separately, so
   NI demand ≈ 1,015 MW would independently confirm the CTA-vs-SEM gap measured
   here. One number, and it validates the central data choice.
3. **Report `mean_abs_grad` beside `vol_norm` in the existing panels** (§8.2) —
   the ISONE retraction and this note are the same artifact twice.
4. **The `night_floor` confound is the weakest point** (§5.4). Irish and Dutch EV
   and heat-pump penetration by year would not identify the data-centre effect,
   but it would establish whether the control's *larger* night-floor rise has an
   obvious non-data-centre explanation.
