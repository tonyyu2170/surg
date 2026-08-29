# Is Data-Centre Load Actually Spiky? — The UKPN Flatness Cut

Analysis date: 2026-08-11. Answers agenda TODO item 7 of
`docs/plans/advisor/2026-08-19-advisor-meeting-agenda.md`: *"characterize the ~100 site
profiles. Is data-center load actually spiky? Your proposal assumes it and cites two
papers; nobody has checked it against data."*

Script: `scripts/ukpn_flatness.py`. Outputs: `outputs/ukpn_flatness/`
(`results.json`, `site_annual_headline.csv`, `site_year_trend.csv`,
`site_metrics.csv`, `site_screen.csv`, `diurnal_profiles.csv`,
`ukpn_flatness.png`). Corpus and its defects: `docs/sources/ukpn-api-constraints.md`.

---

## 0. Headline — no, and the project now has its own evidence for it

**At the resolutions that form price, these data centres are among the flattest
loads on the system — flatter, per site, than an entire ISO zone's aggregate
load.**

| Quantity (median across 71 sites, annual) | UKPN | Matched comparator |
|---|---|---|
| Diurnal spread (peak hour ÷ trough hour, local civil time) | **1.050** | 1.467 (ISONE, 27 zone-years) |
| Load factor vs own p99 | **0.836** | 0.88 EPRI colo — resolution unstated |
| Load factor vs own realized peak | **0.723** | " (see qualification) |
| CV (σ/μ) | **0.094** | — |
| Normalized ramp, hourly basis (`grad_mean_norm_60m`) | **0.000240** = **1.44 %/hr of own mean** | 0.000574 = 3.44 %/hr (60 ISO zones) |

Three findings carry the answer, and one qualification keeps it honest.

1. **There is almost no daily cycle — the central result.** Median
   peak-hour/trough-hour ratio is **1.050**, a 5 % swing between the busiest and
   quietest hour of the day; 77.5 % of sites sit below 1.10. Computed
   identically on ISONE hourly demand (9 zones × 2023–2025, prevailing local
   time, §3), the same statistic is **1.467** — range 1.396–1.548 across 27
   zone-years. System demand swings roughly **9× more across the day** than
   these facilities do. Whatever they are doing, they are not following human
   activity.
2. **The same flatness, expressed on the project's own cross-ISO measure.** The
   median UKPN site ramps at **0.000240** against **0.000574** for the median of
   60 distinct ISO zones (§3) — about **2.4× flatter**. **59 of 71 UK sites
   (83 %) ramp less than the median ISO zone**, and **21 of 71 (30 %) ramp less
   than the flattest zone in the entire cross-ISO set.**
   ⚠️ **This is not independent corroboration of #1 — it is #1 restated.** An
   ISO zone's `grad_mean_norm` is dominated by its *deterministic daily load
   curve*, which aggregation preserves rather than smooths; a load with no daily
   cycle will mechanically show a smaller mean \|Δ\|. The value of this
   comparison is that it puts UKPN on the same scale as the cross-ISO Stage-1
   panels, not that it is a second finding. Do not argue "aggregation should have
   made the zone smooth, and one facility still beat it" — aggregation does not
   remove the common diurnal signal.
3. **Diversification is real and large — the one genuinely independent result.**
   Both sides are UKPN, same measure, same within-year basis, no diurnal
   confound. The cross-site equal-weighted mean utilization has an annual CV of
   0.034–0.045 against 0.094 for the median individual site, and a ramp ratio
   stable at **0.31 across all three years** — roughly **two-thirds of
   individual-site ramp movement cancels in aggregate.** Site movements are
   largely idiosyncratic, not synchronized. This is the finding most relevant to
   a price question.

**The qualification: the comparison to EPRI's magnitude is unresolved, not
adverse.** EPRI's metered facilities report annual load factors of **0.88
(colocation)** and **0.94 (hyperscale)** against own realized peak. UKPN gives
**0.836 against own p99** and **0.723 against strict half-hourly max** — an
11-point spread that shows the *peak estimator* is doing much of the work, since
`lf_own_peak` divides by the maximum of ~17,520 half-hourly draws. A coarser
metering resolution or shorter window yields a systematically lower denominator
and thus a higher load factor; **EPRI 2025c does not state the resolution of its
load-shape data**, so which of our two figures is methodologically matched to
their 0.88 cannot be determined. Report both, and do not lead with 0.723 as
though the gap were established. What *is* established is direction: EPRI's
qualitative finding replicates on 71 sites instead of 4.

**What this does not test.** The 0.1–30 Hz phenomenon (§3 of
`I-advisor-links-2026-08.md`) is invisible at half-hourly resolution. This note
speaks only to the timescales at which LMP is formed. It is evidence *bearing
on* the "different dependent variable" framing parked as open item 6 of that
note; adopting that framing remains an advisor call, not a result of this work.

---

## 1. What the metrics can and cannot be

`hh_utilisation_ratio` is observed apparent power ÷ **contracted** maximum import
capacity. Contracted capacity is a commercial quantity, not nameplate, so
**levels are not comparable across sites — only shapes.**

Every statistic here is therefore a **within-site ratio**, in which the MIC
denominator cancels. The test applied before admitting any metric: *would this
change if UKPN revised one site's MIC by 2×?* If yes, it is not reportable
cross-site.

| Admitted | Rejected |
|---|---|
| CV = σ/μ | mean of the raw ratio (MIC survives) |
| mean ÷ own realized peak | anything ÷ MIC — **not** comparable to EPRI's 75 %/57 % *nameplate* figures |
| \|Δ\| ÷ own mean | raw \|Δ\| in ratio units |
| peak-hour mean ÷ trough-hour mean | the voltage level gradient (already flagged non-physical in the constraints doc) |

Two consequences worth stating plainly:

- The comparison to EPRI is only valid against their **own-realized-peak**
  figures (94 %/88 %), never their nameplate figures (75 %/57 %).
- No absolute MW exists anywhere in this dataset, and no admissible weighting
  exists either — the large-demand list cannot be filtered to data centres, and
  the local-authority capacity file cannot be joined to anonymised sites.
  §0's aggregate is therefore **"cross-site mean utilization", never "aggregate
  demand"**: the system-seen aggregate is not constructible here.

---

## 2. Screening, and why the headline is within-year

**Cohorts by share of exactly-zero intervals** (96 sites):

| Cohort | Rule | n |
|---|---|---|
| clean | ≤ 1 % zeros | **66** |
| intermittent | 1–50 % | 20 |
| mostly dead | > 50 % | 6 |
| dead | 100 % | 4 (dropped) |

Zeros are **masked, never interpolated**, and differences are taken only across
adjacent unmasked pairs exactly 30 minutes apart. Without the adjacency check,
each of the 754 single-interval zero dropouts fakes a full-scale ramp down and
back up within the hour — the same class of defect as the 5-min gap-mask bug
(`2aab67b`), where a 5 h 50 m hole read as a −4,933 MW excursion. A naive run
would have reported these sites as violently spiky.

**Headline panel: 71 sites** observed in all three complete years (2023, 2024,
2025). 2026 is excluded — the panel ends 2026-05-13 and only 9 of 96 sites reach
that date, so a "latest period" comparison would measure composition, not
behaviour.

### The within-year decision

Statistics are computed **within year, then averaged across years.** A
mid-series contract revision puts a step in the ratio that inflates CV and
depresses load factor; a within-year statistic cannot be contaminated by a
revision that happens between years. Measured on the clean cohort, max/min of
monthly medians is **1.395 pooled against 1.166 within-year** (p95: 6.41 vs
2.82). Annual is also exactly what EPRI reports, so this is the correct basis
for the comparison either way. Pooled whole-span figures are retained in
`results.json` under `pooled_whole_span` as the robustness check.

### ⚠️ Data quality find: Data Centre #67 has a 5.4× structural break

Mean ratio **1.396 before 2025-11-27, 0.260 after**, with the site pegged above
1.0 for **86 % of its span** (50,386 intervals, 99.6 % density inside that
window). Running above contracted capacity continuously for nearly three years
is not physically plausible; a stale MIC, later revised, is the far more likely
reading. Either way the site has a structural break and its **pooled** 3.4-year
CV and load factor are not interpretable. This is the single clearest case; the
`mic_step_screen` block in `results.json` scores all six sites with ratios above
1.0, and the other five are short episodes (1–517 intervals).

This site is *not* excluded — the within-year basis already handles it, since
the break falls between the 2025 and 2026 slices. Flagged so the next reader
does not quote its pooled numbers.

---

## 3. The ISO comparison — same statistic, same footing

`grad_mean_norm` is deliberately the **same quantity** as the cross-ISO Stage-1
diagnostic (`src/surg/diagnostics/stage1.py`): mean absolute period-over-period
change per minute, divided by the mean level. Dimensionless in both places, so
UKPN sites land on the ISO panels' scale instead of being an orphan statistic.

One correction was needed to make the comparison fair. A per-minute rate taken
over a 30-minute difference is **not** strictly comparable to one taken over 60
minutes: on any series with high-frequency content, the shorter interval reads
higher. UKPN is half-hourly; the ISO panels are hourly. So `grad_mean_norm_60m`
resamples UKPN on the hour before differencing. The correction matters — it
moves the UKPN median from 0.000388 to **0.000240**, i.e. the uncorrected
comparison understates UKPN flatness by ~60 %.

| Panel | `grad_mean_norm` (hourly basis) | as %/hr of own mean |
|---|---|---|
| **UKPN median site** (n=71) | **0.000240** | **1.44 %** |
| **UKPN cross-site mean** | **0.000093–0.000099** | **~0.58 %** |
| ISO zones, median (n=60 distinct) | 0.000574 | 3.44 % |
| ISO zones, range | 0.000168 (CAISO MWD) – 0.001009 (CAISO VEA) | 1.01 – 6.05 % |

**Only 1 of 60 distinct zones (CAISO MWD) is flatter than the median single UK
data centre.** Read from the other side: **59 of 71 UK sites (83 %) are flatter
than the median ISO zone**, and **21 of 71 (30 %) are flatter than CAISO MWD**,
the flattest zone in the whole cross-ISO set.

### ⚠️ Two things this comparison is not

**It is not a second, independent finding.** An ISO zone's `grad_mean_norm` is
driven overwhelmingly by its **deterministic daily load curve** — the sun comes
up, people wake up. Aggregating millions of customers smooths idiosyncratic
movement but *preserves* that common diurnal signal. A load with essentially no
daily cycle (§0.1) therefore has a mechanically smaller mean |Δ|. So the
2.4× gap is largely the same fact as the 1.05-vs-1.467 diurnal gap, measured a
different way. Its value is putting UKPN on the cross-ISO Stage-1 scale, not
corroborating flatness a second time. Correspondingly, **"59 of 71 sites beat
the median ISO zone" is a statement about diurnal amplitude, not about
volatility** — label it that way.

**It is not 73 independent zones.** The 73 `trends_by_zone_year.csv` rows are
zone-panel *specifications*, and several describe the same physical zone under
alternate builds: `caiso_diagnostic_full_depth` and `caiso_diagnostic_modern`
share `caiso_total`/`pge`/`sce`/`sdge`, and `nyiso_diagnostic_merged` and
`nyiso_diagnostic_split` overlap likewise. Collapsing to distinct
(market, zone) pairs gives **60**. The median barely moves (0.000583 → 0.000574)
and all three headline counts survive, but the deduplicated figure is the one to
quote — the same double-counting trap already flagged for MISO's
`LRZ3_5`/`LRZ4` shared `ILLINOIS.HUB`.

⚠️ **Scope of the ISO side.** These 60 zones cover **six** markets — CAISO,
IESO, ISONE, MISO, NYISO, SPP — being the `trends_by_zone_year.csv` files
present on disk. ERCOT and PJM/DOM diagnostic outputs are gitignored and were
not on disk at analysis time, so they are **not** in this comparison. Re-run
those two drivers before describing it as the full eight-market set.

### The matched diurnal comparator

The §0.1 comparator is computed, not quoted. ISONE `RT_Demand` from
`data/raw/isone/{2023,2024,2025}_smd_hourly.xlsx`, 9 zones, using the
**identical statistic** applied to UKPN: mean demand in each hour-of-day bin
over the year, then peak-hour mean ÷ trough-hour mean. ISONE `Hr_End` is
prevailing local time, matching the Europe/London conversion on the UKPN side;
the `02X` fall-back marker (one row per zone-year) is dropped rather than
allowed to collide with hour 2.

| | 2023 | 2024 | 2025 |
|---|---|---|---|
| ISO NE CA (system) | 1.462 | 1.454 | 1.440 |
| Zone range | 1.415–1.525 | 1.413–1.533 | 1.396–1.548 |

Median across all 27 zone-years: **1.467**. UKPN median site: **1.050**; the
UKPN cross-site mean series: **1.055**.

This replaces an earlier draft's unsourced "GB national demand moves roughly
1.5–1.8× across a day." That figure was not the same statistic — a winter-evening
peak over an overnight minimum is much larger than a three-year average of
hour-of-day means — and it overstated the comparator. The computed matched
figure is smaller, and the finding survives it comfortably.

---

## 4. Results in detail

### Diversification (cross-site mean vs median individual site, within-year)

| Year | Aggregate CV | Aggregate LF vs own peak | CV ratio | Ramp ratio |
|---|---|---|---|---|
| 2023 | 0.0435 | 0.849 | 0.535 | 0.320 |
| 2024 | 0.0336 | 0.840 | 0.439 | 0.314 |
| 2025 | 0.0448 | 0.839 | 0.498 | 0.305 |

The ramp ratio is remarkably stable at ~0.31. Read directly: **about two-thirds
of the half-hourly movement of an individual site is idiosyncratic and cancels
against other sites.** This is the result most relevant to a price question —
synchronized swings would survive aggregation and reach the system; these
largely do not. It is also the only comparison here free of the diurnal
confound in §3: both sides are UKPN, the same measure, the same within-year
basis.

**Composition check.** The aggregate is built on sites that are both in the
balanced panel and in the clean cohort, so neither entry/exit nor
zero-masking can change its membership mid-series. This turned out to bind on
nothing: **all 66 clean sites are already present in all three complete years**,
so restricting to the intersection left every number unchanged. The level drop
visible in the raw cross-site series (~0.28 → ~0.25) falls in **2026**, outside
the complete-years window the annual statistics use. The constraint is kept in
the code because it will bind if the corpus is refreshed.

### No trend toward spikier (balanced 71-site panel)

| Year | median CV | median LF vs own peak | median `grad_mean_norm` |
|---|---|---|---|
| 2023 | 0.0813 | 0.750 | 0.000378 |
| 2024 | 0.0765 | 0.752 | 0.000392 |
| 2025 | 0.0900 | 0.740 | 0.000391 |

Essentially flat across three years, with a slight CV uptick in 2025. Nothing
here supports "data centres are becoming spikier."

### By `dc_type` — report as distributions, run no tests

| | n | LF vs own peak | LF vs p99 | CV | ramp (60 m) | diurnal |
|---|---|---|---|---|---|---|
| Co-located | 59 | 0.723 | 0.839 | 0.083 | 0.00020 | 1.046 |
| Enterprise | 12 | 0.698 | 0.803 | 0.118 | 0.00030 | 1.066 |

Enterprise is slightly less flat on every measure, consistently. But **n=12**,
and `dc_type` is **inferred by UKPN, not declared** — so this is a direction,
not a finding, and nothing is significance-tested.

**Mapping to EPRI, stated explicitly so it is not misread:**

- UKPN **Co-located** (59) ↔ EPRI **colocation** (0.88, avg of 3 facilities).
  This is a genuine independent test of an EPRI number, at ~20× the sample.
- UKPN **Enterprise** (12) ↔ EPRI measured **no** enterprise counterpart. New
  evidence, not a comparison.
- EPRI **hyperscale** (0.94) ↔ **absent from UKPN by construction.**
  Transmission-connected sites sit outside a DNO's metering, so the largest
  facilities — the class EPRI found flattest — are structurally excluded here.
  The flatness result must not be described as covering hyperscale.

### By voltage level — the harder-edged cut, but small cells

| | n | LF vs own peak | CV | ramp (60 m) | diurnal |
|---|---|---|---|---|---|
| High Voltage Import | 48 | 0.733 | 0.084 | 0.00020 | 1.047 |
| Low Voltage Import | 15 | 0.667 | 0.094 | 0.00030 | 1.049 |
| Extra-High Voltage Import | 8 | 0.651 | 0.110 | 0.00020 | 1.058 |

Voltage is declared rather than inferred, so it is the harder-edged cut, but the
EHV cell is 8 sites. Note this is a *shape* comparison and therefore admissible,
unlike the level gradient the constraints doc rules out.

### Cohort contrast — why screening was load-bearing

| Cohort | n | LF vs own peak | CV | ramp (60 m) |
|---|---|---|---|---|
| clean | 66 | 0.733 | 0.082 | 0.00020 |
| intermittent | 5 | 0.294 | 1.026 | 0.00180 |

The intermittent cohort looks like a completely different population — CV **12×**
the clean cohort. Pooling them would have produced a "data centres are spiky"
headline built entirely on metering dropouts. Never pool these.

---

## 5. What this changes

1. **The proposal's spikiness premise is contradicted at the resolutions this
   project can observe** — and now by the project's own data, not by borrowed
   citations. Previously this rested on EPRI's 4 facilities (§2 of
   `I-advisor-links-2026-08.md`); it now rests on 71 metered sites over three
   years, against a matched system comparator computed from the project's own
   ISONE panel.
2. **Diversification is quantified**: ~⅔ of site-level ramp cancels in
   aggregate, stable across three years. This is the genuinely new result and
   the one that bears on price.
3. **EPRI's magnitude is unresolved rather than contradicted** — 0.836 vs 0.88
   on the p99 denominator, 0.723 on the strict max, with EPRI's own metering
   resolution unstated. Worth raising in the meeting as an open comparability
   question, not as a discrepancy. If it is a real gap, the likeliest
   explanations are sample composition (4 US facilities vs 71 UK
   distribution-connected sites) and the structural exclusion of hyperscale.
4. **No decisions.md entry is written by this note.** The append-only log should
   record the methodology choice (within-year basis, zero-masking discipline,
   the 60-minute resampling correction) and the finding — but adopting the §0
   "different dependent variable" framing is an advisor call, and the two should
   not be bundled into one entry.

## 6. Open items

1. **Re-run the ERCOT and PJM/DOM Stage-1 drivers** so the ISO comparison covers
   all eight markets rather than the six with outputs on disk.
2. **Decide the decisions.md entry** (see §5.4) after the 2026-08-19 meeting.
3. **Establish EPRI 2025c's metering resolution**, which decides whether 0.836
   or 0.723 is the figure comparable to their 0.88 — and therefore whether there
   is a gap to explain at all. Highest-value item here: it is one fact, and it
   settles the only number in this note that reads unfavourably.
4. **Other GB DNOs remain unchecked** (SSEN, NGED, SP Energy Networks, ENWL).
   SSEN covers Slough and West London — the cluster this dataset structurally
   excludes. Still the highest-value extension of this corpus.
