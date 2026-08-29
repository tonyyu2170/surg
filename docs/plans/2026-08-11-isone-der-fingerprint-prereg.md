# Pre-registration — ISO-NE rising-volatility diurnal fingerprint test

**Date:** 2026-08-11
**Status:** LOCKED before any result was computed.
**Motivation:** `docs/plans/advisor/2026-08-11-post-meeting-prioritization.md` §1, and the
advisor's 2026-08-10 question "is New England's fluctuation caused by the
Canadian tie?"

## Background

Three ISO-NE zones show rising *raw* |load gradient| 2016→2025 — VT (+38.9%),
ME (+18.9%), RI (+8.6%) — while the other five fall. Post-hoc, these are the
three smallest zones (Spearman ρ = −0.786, p = 0.021, n = 8). Zone size,
rural-ness, and distributed-solar share are collinear across n = 8 and cannot be
separated cross-sectionally.

Three candidate mechanisms:

- **H_canada** — Canadian import variability. Predicts the effect in border
  zones (VT: Highgate/HQ; ME: New Brunswick). Already strained: RI has no
  Canadian tie and rises anyway.
- **H_size** — small zones have less demand diversity, so individual load swings
  average out less. Predicts no particular time-of-day structure.
- **H_solar** — metered zone load is *net* of behind-the-meter PV, so growing
  DER makes the observed series more volatile with no change in demand
  behavior. Predicts a specific diurnal and seasonal fingerprint.

H_solar is the only one making a within-day prediction, which makes the
fingerprint the cheap discriminator. It runs entirely on
`data/interim/isone_diagnostic_panel.parquet`; no new pull.

## Data

`data/interim/isone_diagnostic_panel.parquet` — hourly, 2016-01-01 → 2026-06-30,
8 zones. Fields used: `datetime_beginning_ept`, `load_gradient_abs_mw_per_min_<zone>`,
`dst_transition_hour`. Timestamps are Eastern *Prevailing* Time, so clock hour
tracks local solar position year-round (solar noon ≈ 13:00 under EDT).

Rows with `dst_transition_hour == True` are excluded. NaN gradients (first row of
the series) are excluded. No interpolation anywhere.

## Windows and buckets

**Comparison windows:** early = 2016–2017, late = 2024–2025. Two-year windows,
deviating from the single-year 2016-vs-2025 convention used in the capstone,
because per-hour-bucket cells are ~1/6 the size of the whole-year cells and
single years are too noisy at that resolution. 2026 is excluded (half year).

**Hour buckets (EPT):**

| bucket | hours | solar exposure |
|---|---|---|
| `night` | 00–04 | **none — placebo** |
| `morning_ramp` | 07–10 | PV ramping up |
| `midday` | 11–14 | PV at plateau |
| `evening_ramp` | 16–19 | PV ramping down |

**Season buckets:** `high_solar` = Apr–Jun, `low_solar` = Dec–Feb.

**Statistic:** for each zone × bucket, mean `load_gradient_abs_mw_per_min` over
the window; report % change late vs early. Raw, not normalized by mean load —
the capstone showed normalization inverts wherever load is shrinking, and every
zone here is shrinking.

## Pre-registered decision rule

Evaluated on the three rising zones (VT, ME, RI):

- **H_solar SURVIVES** if, in ≥ 2 of 3 zones, the % increase in *both* ramp
  buckets exceeds the % change in `night`, **and** `night` is flat-to-falling
  (≤ +5%) in ≥ 2 of 3 zones.
- **H_solar REJECTED** if `night` rises by ≥ the mean of the two ramp buckets in
  ≥ 2 of 3 zones. A uniform-across-hours rise is evidence for H_size (or for any
  mechanism acting on total load), not for solar.
- **INCONCLUSIVE** otherwise — report as such, do not reinterpret.

Secondary, not decisive on its own: under H_solar the `high_solar` season should
rise more than `low_solar` in the same zones.

**Falsification asymmetry, stated in advance:** surviving this test does *not*
establish H_solar — a daytime-concentrated rise is also consistent with any
mechanism whose intensity tracks daytime activity. Survival licenses the
external per-zone DER pull; it does not license a claim.

**Controls:** the same table is computed for all five falling zones. If the
falling zones show the same diurnal *shape* as the rising ones, the shape
carries no information about why VT/ME/RI differ, and the test is uninformative
regardless of which branch of the rule fires. This check is reported alongside.

## Known limitations

- Hourly data. The true PV ramp signature lives at 5-minute resolution; hourly
  differencing smooths it and biases toward finding nothing. This test can
  therefore fail for a reason unrelated to whether H_solar is true.
- Load is *net* of PV by construction — there is no gross-load series in the
  panel to compare against.
- n = 3 rising zones. The decision rule is a 2-of-3 vote, which is weak by
  construction and is the reason the rule is fixed in advance.
- EPT means clock hour shifts one hour against solar time at the DST boundary;
  buckets are wide enough (3–5 h) to absorb this.

## Outcome — run 2026-08-11

### Validity check run first: the 2024 time-convention break is NOT a confound

`isone_features.py` records that the SMD workbook switches convention at 2024
(2016–2023 fixed 24-hour grid; 2024+ real local prevailing clock). Since the test
compares hour buckets across that boundary, a one-hour label shift would have
invalidated it. **Checked and ruled out:** the peak hour of the mean daily load
profile is 17 in July *and* January, in 2016–17, 2022–23 and 2024–25 alike. Hour
labels track local prevailing time in both eras; the buckets are aligned.

### Primary result — % change in mean raw |grad|, 2024-25 vs 2016-17

| zone | group | night | morning_ramp | midday | evening_ramp |
|---|---|---|---|---|---|
| vt | **RISING** | −0.1 | +91.4 | **+125.7** | +98.5 |
| ri | **RISING** | −0.5 | −19.0 | **+65.8** | +20.3 |
| me | **RISING** | −5.7 | −0.2 | **+101.6** | +89.6 |
| nh | falling | −11.1 | −18.5 | +32.0 | +17.6 |
| sema | falling | −10.2 | −7.9 | +49.0 | +17.4 |
| wcma | falling | −9.1 | −11.9 | +41.2 | +20.6 |
| nema | falling | −9.4 | −22.8 | +32.7 | +2.1 |
| ct | falling | −12.2 | −23.7 | +36.6 | +24.4 |

**Decision rule as written → H_solar SURVIVES**, on a technicality: both ramp
buckets exceed `night` in 2 of 3 rising zones (VT, ME; RI's morning ramp is
−19.0 and fails), and `night` is ≤ +5% in 3 of 3.

**But the pre-registered control clause fires, and it overrides.** All five
falling zones show the *same sign pattern* — night down, midday up, evening up.
The spec says: "If the falling zones show the same diurnal shape as the rising
ones, the shape carries no information about why VT/ME/RI differ, and the test is
uninformative regardless of which branch of the rule fires."

**Verdict: UNINFORMATIVE on the question it was built to answer.** The diurnal
fingerprint does not discriminate VT/ME/RI from the rest of ISO-NE. Magnitudes do
differ — rising zones are +66% to +126% at midday against +32% to +49% for
falling zones — but that is a difference of degree, not the shape difference the
test was designed to detect. Do not report H_solar as supported.

### Secondary (seasonal) — FAILED as pre-registered

| zone | Apr–Jun midday | Dec–Feb midday | Apr–Jun night | Dec–Feb night |
|---|---|---|---|---|
| vt | +135.0 | +98.9 | +2.4 | −4.7 |
| ri | +56.4 | **+112.7** | −2.5 | −3.6 |
| me | +77.8 | **+111.9** | −8.6 | −9.2 |
| nh | +39.6 | +26.1 | −8.3 | −15.7 |
| sema | +63.0 | **+78.6** | −6.6 | −15.9 |
| wcma | +47.2 | **+56.3** | −4.4 | −14.6 |
| nema | +43.7 | **+50.9** | −5.8 | −15.3 |
| ct | +43.6 | **+71.4** | −6.9 | −17.7 |

H_solar predicted the high-solar season would rise more. **Winter midday rose as
much or more in 6 of 8 zones.** Recorded as a failure.

*Post-hoc note, which does NOT rescue the hypothesis and is flagged as such:* the
prediction was poorly reasoned at lock time. New England's winter solar day is
compressed, so hours 11–14 sit near the ramp shoulders in December but on a flat
plateau in June — midday |Δsolar/Δt| need not be larger in summer. The seasonal
test as specified was not a good test of H_solar. This is a criticism of the
design, not evidence for the hypothesis.

### What the run did establish — a system-wide result, larger than the question asked

Across **all eight zones**, without exception: daytime volatility rose sharply
(midday +32% to +126%) while overnight and shoulder-hour volatility fell. ISO-NE
has undergone a region-wide redistribution of *when* load volatility occurs.

**Decomposition of the annual change (added after an initial mis-statement — see
below).** Contribution of each hour bucket to the annual mean change, in
percentage points of the early-window annual mean:

| zone | ANNUAL % | 0–4 | 5–6 | 7–10 | 11–14 | 15 | 16–19 | 20–23 |
|---|---|---|---|---|---|---|---|---|
| vt | **+35.3** | −0.0 | −4.4 | +14.7 | +9.7 | +4.8 | +16.8 | −6.3 |
| ri | **+5.3** | −0.1 | −0.0 | −4.2 | +4.9 | +2.5 | +2.4 | −0.3 |
| me | **+12.8** | −0.8 | −3.7 | −0.0 | +5.4 | +3.6 | +10.8 | −2.5 |
| nh | −6.6 | −1.6 | −3.1 | −3.4 | +1.9 | +1.4 | +2.1 | −3.9 |
| sema | −1.5 | −1.5 | −2.6 | −1.3 | +3.8 | +2.1 | +2.5 | −4.4 |
| wcma | −2.7 | −1.4 | −3.2 | −2.0 | +3.1 | +2.2 | +2.8 | −4.2 |
| nema | −10.8 | −1.5 | −3.8 | −4.5 | +2.2 | +1.3 | +0.2 | −4.6 |
| ct | −5.8 | −1.9 | −3.4 | −4.5 | +2.9 | +2.4 | +3.0 | −4.4 |

Contributions sum to the annual figure in every row. The annual figures also
reconcile with the capstone's single-year 2016-vs-2025 numbers (VT +38.9%, ME
+18.9%, RI +8.6%) given the different windows.

**Correction to an earlier draft of this section.** It claimed "in the five large
zones the overnight decline dominates the annual mean." That is wrong. Hours 0–4
contribute only −0.0 to −1.9 pp in *every* zone — almost nothing happens there,
which is exactly why it is a good placebo. The decline is carried by **hours
20–23** (−0.3 to −4.6 pp, the largest single negative in four of five falling
zones) together with **5–6 and 7–10**.

**The corrected statement:** every zone gains volatility in the solar-day hours
(11–19) and loses it in the late-evening and morning-shoulder hours (20–23, 5–10).
A zone's annual sign is decided by which side wins. VT/ME/RI are not a different
phenomenon — they are the zones where the daytime gain is large enough to
outweigh the shoulder-hour loss. Note also that VT's and ME's gains are
concentrated in the **ramp** hours (VT: +14.7 morning, +16.8 evening) more than at
midday, which is a stronger PV signature than the primary table alone suggested.

### Known defect in the gradient series (found 2026-08-11, bounded)

On post-2024 spring-forward days the workbook omits hour 1, but the gradient at
hour 2 is still divided by 60 minutes despite spanning two real hours — e.g.
2024-03-10 VT: `|499.841 − 520.055| / 60 = 0.3369`, roughly 2× inflated. This
affects **1 hour/year in 2024 and 2025 and zero hours in 2016–2017**, i.e. 2 of
~3,650 night-bucket observations per zone in the late window. It biases the
`night` placebo *upward*, which is the conservative direction for every claim
made here — night still came out flat-to-falling. Left uncorrected; flagged for
the module owner.

### Status of the three hypotheses after this run

- **H_canada** — see `2026-08-11-isone-canada-tie-verification.md`. Fails on
  mechanism, geography and timing independently.
- **H_size** — not tested here; predicts no diurnal structure, and strong diurnal
  structure exists in every zone, so size cannot be the whole story.
- **H_solar** — neither supported nor rejected. The mechanism remains the only
  one of the three that acts on metered demand. The external per-zone DER pull is
  still the discriminating test; this run does not license skipping it.
