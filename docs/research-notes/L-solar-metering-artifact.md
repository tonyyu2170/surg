# Is the Midday Flattening a Solar Metering Artifact? — 12 European Zones

Analysis date: 2026-08-12. Tests H_solar, which `EU-5` identified as the one
open question the North American panel could not settle, and which the K-note
left live.

Scripts: `scripts/entsoe_fetch.py` (new `capacity` item),
`scripts/entsoe_solar.py`. Module: `src/surg/analysis/entsoe_seasonal.py`
(12 tests). Outputs: `outputs/entsoe/` (`solar_results.json`,
`solar_signature_*.csv`, `solar_step_*.csv`, `solar_cross_section.csv`,
`fig_solar_signature.png`, `fig_solar_diurnal.png`).
Predecessor: `docs/research-notes/K-ireland-dc-shape.md`.

---

## 0. Headline — three findings, in order of how much they cost the project

**1. The Dutch load series changes definition in April 2023, and the K-note's
Dutch control is computed across that break.** The step is
midday-concentrated, which rules out the obvious innocent explanation.

**2. Ireland's flattening is summer-and-midday-specific.** Its winter change is
exactly what flat load growth predicts and nothing more; its summer change is
far beyond it. Data centres cannot produce a seasonal signature. Solar can.

**3. Across 12 zones the seasonal signature tracks installed solar —
suggestively.** Rank correlation between change-in-dose and change-in-signature
is **ρ = +0.714** (n = 7 zones with a dose), and Finland, the lowest-dose zone,
does not move at all. This is the weakest of the three findings: ENTSO-E's
installed-capacity feed turns out to be ~100% complete in the Netherlands and
~3% in Finland (§ 2.1), so the dose is real but unevenly measured, and adjacent
ranks are separated by less than that error. Findings 1 and 2 use load alone and
do not depend on it.

None of this says data centres do nothing. It says a component of what the
K-note measured, and attributed to a period of data-centre growth, has a
fingerprint data centres cannot leave.

---

## 1. Why seasonal, and not a cross-section on solar share

Solar share and calendar year are near-collinear: PV grew monotonically almost
everywhere over this window. A regression of load shape on solar share
therefore cannot separate "solar" from "anything else that drifted across the
same decade" — the same collinearity trap that made the ISONE `vol_norm`
result a denominator artifact.

Irradiance, though, varies enormously **within** a year, while data-centre
share does not move between June and December. That within-year contrast is the
identification:

- a solar-driven midday trough must be concentrated in high-irradiance months
  and near-absent in December;
- a data-centre-driven or secular flattening has **no** seasonal signature.

So the statistic is the **summer-minus-winter midday contrast**
(`signature`), and its trend — not the level of the trough in any one season.

**The confound, stated up front.** Space cooling is also seasonal and also
midday, and it pushes summer midday load *up*. In a hot zone (Spain) that
biases the signature toward zero, making the test conservative there. In the
maritime zones that anchor this project (Ireland, Netherlands, Denmark)
domestic cooling is negligible. Electric heating is seasonal but loads the
winter morning and evening peaks, not midday. Nothing here separates solar from
a hypothetical unmodelled summer-midday process; the claim is that the
signature appears where solar predicts it and is absent where solar is absent.

---

## 2. Two measurement decisions that change the answer

### 2.1 The dose is installed capacity (A68), never metered generation (A75)

Measured 2026-08-12, one June day:

| | A68 installed solar | A75 metered solar, peak | implied |
|---|---|---|---|
| **Netherlands** | **27,980 MW** | **204 MW** | ~1% — TSO-invisible |
| **Germany-Lux** | 77,016 MW | 24,393 MW | ~32% — plainly complete |

The Dutch figure of 27,980 MW matches the national fleet, so **for the
Netherlands** A68 includes behind-the-meter PV while A75 does not. Verified not
to be a `psrType` filter artifact: an unfiltered 16.1.B&C query returns the same
204 MW for B16.

**A68 completeness is NOT uniform across countries, and § 5 is qualified by
this.** Against published national installed PV, ~2024:

| zone | A68 2024 | national ~2024 | coverage |
|---|---|---|---|
| Netherlands | 27,980 MW | ~28,000 MW | **~100%** |
| Denmark (DK1+DK2) | 3,730 MW | ~3,900 MW | ~96% |
| Germany-Lux | 77,016 MW | ~99,000 MW | ~78% |
| France | 17,795 MW | ~24,000 MW | ~74% |
| Spain | 23,867 MW | ~40,000 MW | ~60% |
| **Finland** | **27 MW** | **~1,000 MW** | **~3%** |

Finland's A68 is effectively unreported until it jumps 46.6 MW (2025) to 1,512
MW (2026) — itself a reporting change, not a build-out. So A68 is the *best*
available dose and the only one that captures distributed PV anywhere, but its
LEVELS are not comparable across countries either.

**Consequence: ENTSO-E metered solar generation is not comparable across
countries.** Using it as the dose would score the Netherlands — one of the
densest PV fleets on earth — as a near-zero-solar market, and would have
inverted this entire analysis.

### 2.2 Every ratio is reported beside an absolute MW deviation

`midday_dev_mw` is the mean MW deviation of hours 10–15 from that day's own
mean. Adding **flat** load — data centres, an industrial recovery — leaves it
unchanged and only compresses ratio statistics. Adding **midday-concentrated**
load moves it directly. This is enforced by test
(`test_flat_load_added_does_not_move_the_absolute_midday_deviation`).

The project has now been bitten three times by a normalized statistic moving
because its denominator did: ISONE (shrinking load), Ireland (growing load),
and the Dutch redefinition below.

---

## 3. Finding 1 — the Dutch series breaks in April 2023

### 3.1 The break

The April-vs-March transition, compared against the same transition in every
other year. This is a one-month difference-in-differences on the seasonal
cycle: immune both to a depressed base year (the 2022 gas crisis) and to
secular trend.

| Netherlands | median, other years | **2023** |
|---|---|---|
| April ÷ March mean load | 0.9247 | **1.0493** (×1.1347 excess) |
| April − March **midday** deviation | −123 MW | **+1,395 MW** |

Corrected step size: **+1,548 MW**. All figures on complete local days only,
matching measurement rule 1 — an earlier draft mixed a complete-days step
against all-hours ratios.

### 3.2 It is not the gas crisis, and it is not Europe-wide

Two controls:

- **It is midday-concentrated.** A flat industrial recovery cannot move a
  deviation-from-own-mean. The +1,395 MW is midday-specific.
- **The Netherlands is the only zone where BOTH screens fire.** Every other
  zone's 2023 April/March ratio sits in 0.94–1.02; only the Netherlands exceeds
  1. On the midday-deviation screen there is one other outlier: **DE_LU's 2023
  delta is −934 MW against a +252 MW median** — comparable in magnitude to the
  Dutch figure and **opposite in sign**, with no accompanying level step (its
  ratio is 0.9740, *below* its own 0.9322 median). Cause unexamined; it is not
  a level shift and does not resemble the Dutch step, but "all other zones show
  nothing" would be wrong and is not claimed.

> **An earlier estimate in this session put the step at +1,497 MW and claimed
> it was 68.7% of Dutch 2015→2025 load growth. That was computed against a
> 2022-05→2023-03 base — the gas-crisis trough, when every 2022 month ran
> 0.911–0.980 against a panel median of 1.0042. It conflated the reporting step
> with industrial recovery. The April/March DiD above supersedes it.**

### 3.3 What it costs the K-note

The Dutch 2015→2025 endpoints in `K` straddle this break:
`vol_norm ×0.714`, `night_floor 0.715→0.840`, `pt_ratio 1.669→1.363`.
Pre-break Dutch summer midday deviation runs **+1,521 → −1,343 MW** (2015→2022)
and then jumps back to +655 MW in 2023. That is not a footnote-sized
correction. **The K-note's matched-null comparison should be re-run on
2015→2022 for both countries before it is quoted further.**

Cause **not confirmed with the TSO.** The shape is consistent with distributed
generation being grossed back into reported load; this note deliberately does
not assert that TenneT made a specific methodology change, because five desk
claims were falsified last session for exactly this kind of plausible-mechanism
assertion.

---

## 4. Finding 2 — Ireland's flattening is summer-specific

**The finding is in absolute MW, and it assumes nothing.**

| Ireland, absolute midday deviation | 2015 | 2025 | change |
|---|---|---|---|
| **summer** | +435 MW | **+193 MW** | **−56%** |
| **winter** | +313 MW | **+320 MW** | **+7 MW, i.e. unchanged** |

`midday_dev_mw` is provably invariant to flat load additions — enforced by
test, not argued. So no amount of data-centre growth, of any size, can produce
either row. Ireland's winter midday hump is **the same size in MW as it was
eleven years ago**, while its summer hump has more than halved. That is a
summer-and-midday-specific removal of metered load, which is what PV does and
what a flat aseasonal load cannot do in either direction.

This is on a series with **no definitional break**: Ireland's 2023 April/March
excess is 0.9853 and its midday-dev delta −9 MW against a median of +33 MW.

**The ratio decomposition illustrates the same thing** and is reported because
the K-note is written in ratios. Irish mean load grew ×1.298, so dilution alone
predicts normalized depths shrink ×(1/1.298) = ×0.770:

| Ireland, 2015 → 2025 | predicted by flat-load dilution | observed | excess |
|---|---|---|---|
| **winter** midday depth | −0.0733 | **−0.0740** | ~0 |
| **summer** midday depth | −0.1190 | **−0.0526** | **+0.066** |

Winter matching the dilution prediction to 0.0007 is not a coincidence of two
offsetting trends: it is the direct consequence of the absolute winter
deviation being unchanged while the denominator grew 30%. The two tables are
the same fact in two units.

Ireland has no A68 dose (both `IE_CTA` and `IE_SEM` return reason 999), so
Ireland enters the seasonal test but not the dose cross-section.

---

## 5. Finding 3 — the signature tracks the dose, suggestively, across 12 zones

Dose = A68 installed solar MW per MW of mean load. Netherlands truncated at
2022 (pre-break only); Germany starts 2019; Finland starts 2019.

> **Read this table with § 2.1's coverage caveat in hand.** A68 completeness
> runs from ~100% (Netherlands) to ~3% (Finland), so a zone with a partial feed
> understates its true dose. The rank correlation below is therefore
> **suggestive, not a measured dose-response**, and the coverage differences
> have not been corrected for.

| zone | dose first → last | signature first → last | Δdose | Δsignature |
|---|---|---|---|---|
| Netherlands (→2022) | 0.090 → **1.301** | +0.0005 → **+0.1708** | +1.212 | **+0.170** |
| Spain | 0.230 → 1.066 | −0.0208 → +0.0141 | +0.836 | +0.035 |
| Germany-Lux (2019→) | 0.792 → 1.618 | −0.0401 → −0.0005 | +0.826 | +0.040 |
| France | 0.115 → 0.461 | −0.0611 → −0.0429 | +0.345 | +0.018 |
| **Finland** (2019→) | **0.0003 → 0.005** | **−0.0295 → −0.0291** | +0.005 | **+0.0004** |
| Denmark W | 0.187 → 0.923 | −0.0207 → −0.0799 | +0.736 | −0.059 |
| Denmark E | 0.121 → 0.435 | −0.0380 → −0.0773 | +0.314 | −0.039 |

**Spearman ρ(Δdose, Δsignature) = +0.714**, n = 7 zones. Reported as a rank
correlation over a table, not a fitted regression: n = 7 does not support
standard errors, and the underlying dose has 3%–100% coverage variation.

**The margins between adjacent ranks are smaller than the known measurement
error, so treat the ordering as provisional.** Germany and Spain are separated
by 0.010 in Δdose and France and Denmark-East by 0.031; a coverage correction of
the size measured in § 2.1 (Spain ~60%, Germany ~78%) would plausibly reorder
both pairs. ρ survived the capacity-year correction of § 9 unchanged, but that
is *not* evidence of robustness — the correction moved dose values without
moving any rank, so ρ was structurally incapable of detecting it.

- **Finland does not move — but its dose is the least trustworthy in the
  table.** Its signature is flat (−0.0295 → −0.0291 over the dose window;
  −0.0289 → −0.0291 over the full 2015→2025 load record), which is a real,
  load-based fact. Its *dose*, though, is ~3% complete, so "0.005" is not
  Finland's solar penetration. Using the national ~1 GW against ~9 GW of mean
  load puts Finland nearer 0.11 — still the **lowest-dose zone in the panel by
  a wide margin**, so its placebo role survives, but the number in the table
  does not.
- **Spain moves the H_solar way against its own confound.** Cooling should push
  Spanish summer midday *up* and mask the signature; instead Spanish summer
  midday deviation falls +3,196 → +1,228 MW (−62%) against a winter fall of
  −38%. A confounded zone moving in the predicted direction anyway is stronger
  evidence than an unconfounded one.
- **Denmark is the exception and is reported as such**, not dropped. Both Danish
  zones move *against* the dose. Denmark is wind-dominated with heavy electric
  heating and district-heating interaction; the seasonal contrast there is
  plausibly driven by a heating trend the design does not model. Two of seven
  zones contradicting the pattern is the honest headline number, and it is why
  ρ is +0.714 and not higher.

Sweden's four bidding zones and Ireland carry load but no A68 (Swedish capacity
is published only on the country EIC, 3,200 MW in 2024, and cannot be
apportioned across zones). They contribute to the seasonal test, which needs no
dose, and not to this table.

---

## 6. Coverage, measured not asserted

All 10 VRE EICs probed before pulling; every one returns 6.1.A load.

- **DE_LU returns nothing before 2018.** The zone split from DE_AT_LU
  (`10Y1001A1001A63L`) on 2018-10-01; the predecessor returns data in 2016 and
  none in 2024. Footprints differ (Austria), so the two are **not
  concatenable** — the Calabria precedent. Germany enters at 2019.
- **SE1–SE4 and Ireland return no A68.**
- **2026 is excluded everywhere.** The Dutch feed's 2026 tail carries days with
  minima of 187–1,822 MW against a 10,320 MW median day minimum. Those days hold
  24 slots each and **pass the completeness gate** — the same bug class as the
  six found last session: a value that should not exist quietly does, leaving a
  plausible number.
- **The guard written for this initially could not see it.** `implausible_days()`
  first tested only each day's MEAN against the median day, and the Dutch
  corruption is intra-day: a handful of collapsed slots inside a day whose mean
  (6,150–7,789 MW) clears any sane floor. It flagged **zero** days. It now runs a
  second test on the day MINIMUM and flags 12 Dutch days, all in the 2026 tail.
  Isolated single days also surface in Spain (2), Denmark-West (1), Sweden (13
  across SE1/SE2/SE4) — immaterial against ~120 days per season-year, but now
  visible rather than assumed absent. The exclusion of 2026 is by year cap, not
  by this guard, so no result here ever depended on it.

---

## 7. What this does and does not license

**Licensed.** That a solar metering artifact is present in these series, is
large in the Netherlands, is visible in Ireland, and scales with installed
capacity across most of the panel. That the Dutch control in `K` is
contaminated by a definitional break. That any future load-shape claim in this
project must report an absolute MW statistic beside every ratio, and must check
for a mid-panel definitional break before comparing endpoints.

**Not licensed.** Any statement that data centres do not change load shape —
this note does not test that. Any attribution of the Dutch break to a named
TSO decision. Any causal reading of ρ = +0.714 from n = 7 with two zones moving
the wrong way and a known cooling confound.

**Open.** Find the methodology notice behind the Dutch step. An Irish dose from
national statistics (SEAI microgeneration), since ENTSO-E carries none.

---

## 8. The K-note re-run on the break-free window — mixed, not overturned

`scripts/entsoe_ireland.py` now reports both windows; the published one still
reproduces exactly (Ireland `vol_norm ×0.719`, Netherlands `×0.714`), so this is
a comparison, not a replacement.

| 2015 → 2022, both zones break-free | Ireland | Netherlands |
|---|---|---|
| mean load | ×1.189 | ×1.027 |
| raw mean \|Δload\| | **×0.968** | **×0.997** |
| `vol_norm` | **×0.814** | **×0.971** |
| `pt_ratio` | 1.694 → 1.538 (−9.2%) | 1.669 → 1.494 (**−10.5%**) |
| `night_floor` | 0.721 → 0.760 (+5.4%) | 0.715 → 0.806 (**+12.7%**) |
| `load_factor` | 0.652 → 0.654 (+0.3%) | 0.579 → 0.647 (**+11.7%**) |

### What dies

**The headline matched null on `vol_norm`.** `×0.719` vs `×0.714` becomes
**`×0.814` vs `×0.971`** — Ireland down 18.6%, the control down 2.9%. That match
existed because the break inflated Dutch load growth from ×1.027 to ×1.196; the
Dutch denominator was doing the work. The K-note's single most quotable number
should not be quoted again.

### What survives, and is now cleaner

**The denominator finding.** On the clean window Irish raw volatility fell
**3.2%** while Irish load grew **18.9%** — so `0.968 / 1.189 = 0.814`, and the
entire `vol_norm` decline is arithmetic. This was the K-note's real point and
it is stronger here than in the published window.

**The raw-numerator null.** Quarterly correlation against the Irish
data-centre dose, break-free (n=32): `mean_abs_grad` **r = −0.078 for Ireland,
−0.133 for the Netherlands**. Both ≈ 0, and the control is *more* negative than
the treated unit against a covariate from a country it has no exposure to.
Cleaner than the published −0.261 / −0.268.

**No dose-ordering on `night_floor` or `load_factor`.** Ireland took **+10.83
pp** of dose to the Netherlands' **+2.50 pp** (4.3×), yet the control moved
2.3× further on `night_floor` and 39× further on `load_factor`.

### What reverses

**`pt_ratio` now orders the other way.** Per point of dose, Ireland moves
**−0.011450** against the Netherlands' **−0.006203** — Ireland 1.85× *more*,
where the published window had the control ahead. On `vol_norm` per pp the two
now carry **opposite signs** (IE −0.000010, NL +0.000041).

### Verdict

The K-note's conclusion is **weakened but not overturned, and it is no longer
uniform.** "The control moved as much or more on every statistic" was true only
across the break. Break-free, the control moves more on three statistics
(`pt_ratio` endpoints, `night_floor`, `load_factor`), Ireland moves more on
`pt_ratio` per unit dose, and neither moves on raw volatility. The defensible
statement is now: **no consistent dose-ordering in either direction, and no
detectable movement in raw volatility in either country** — which still does not
license attributing Irish load-shape change to data centres, and no longer
licenses the tidy "identical control" framing either.

---

## 9. Double-check pass — what an independent re-derivation found

Every headline number was recomputed from the raw parquet with plain pandas,
deliberately **not** importing `surg.analysis.entsoe_seasonal`, so a bug in the
module could not validate itself.

### Confirmed exactly

- Ireland summer midday deviation **+435 → +193 MW**; winter **+313 → +320 MW**.
- Netherlands pre-break summer **+1,521 → −1,343 MW**; 2023 **+655**, 2025 **+472**.
- The Netherlands is the only zone of twelve whose 2023 April/March ratio
  exceeds 1.
- Section 5's cross-section table, and **ρ = +0.714** reproduced with
  `scipy.stats.spearmanr`.
- Section 8's break-free re-run, including r = −0.078 / −0.133 and the
  +10.83 / +2.50 pp dose increments.

### Two defects found and fixed

**1. Capacity years were shifted by one.** `load_capacity` derived the year from
`doc_start`, which for an A68 annual document is **local midnight of 1 January
expressed in UTC** — so it lands on 31 December of the *previous* year
(Finland 2019 → `2018-12-31T22:00Z`). Every zone-year was therefore joined to
the **following** year's installed capacity. Fixed by keying on the filename
with `doc_end` as an independent witness and a **fail-loud** mismatch check.
All dose figures in § 5 are the corrected ones. **ρ = +0.714 is unchanged —
which is a fact about ρ, not a reassurance:** the correction moved dose values
without changing any of the seven ranks, so a rank correlation could not have
registered it either way.

**2. `implausible_days` could not see the corruption it was written for.** It
tested only each day's mean, and the Dutch 2026 tail is intra-day: collapsed
slots inside days whose means clear any floor. It flagged zero days on every
zone. A second test on the day minimum was added; it now flags 12 Dutch days.
No result depended on it — 2026 is excluded by year cap — but § 6 had claimed
the guard reported them when it did not.

**3. The break detector used a different sample from every other statistic.**
`april_march_step` did not filter to complete days, so a +1,548 MW step computed
on complete days was quoted beside ratios computed on all hours. Now complete
days throughout, which is why the Dutch figures read 1.0493 / 0.9247 / +1,395 /
−123 rather than the 1.0526 / 0.9295 / +1,385 / −86 of the first draft. The
conclusion is unaffected — the excess is ×1.1347 either way.

### One claim materially weakened

The A68 coverage table in § 2.1 was produced by this pass. Discovering that the
dose runs from ~100% complete (Netherlands) to ~3% (Finland) is what forced
§ 5 from "dose-response" down to "suggestive". **This is the fourth time in this
project that a measurement has turned out to be about the instrument rather
than the system** — after ISONE's denominator, Ireland's denominator, and the
Dutch redefinition. It is becoming the project's most reliable finding.
