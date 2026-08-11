# Pre-registration — did NECEC move Maine's day-ahead price?

**Date:** 2026-08-11
**Status:** LOCKED before any result was computed.
**Motivation:** `2026-08-11-isone-canada-tie-verification.md` §5. That document
rules out the Canadian interconnection as a driver of ISO-NE *load* volatility on
three independent grounds, and redirects the advisor's 2026-08-10 question to the
one place it is still live: **price**. Imports are supply; supply variability
moves LMP directly. This is that test.
**Gate:** `2026-08-11-necec-dose-check.md` — passed. Treatment verified present
and large (~1,060 MW firm at Lewiston, ME).

---

## Background

NECEC — 1,200 MW HVDC, Québec border to a converter station in **Lewiston,
Maine**, commercial operation **2026-01-16**. ISO-NE settles it at external node
`.I.HQMRL_RD345 1` (Merrill Road 345 kV).

The dose check established two facts that shape this design:

1. **NECEC runs as a firm, near-flat block** — 1,059 MW mean, 1,119 MW max, over
   the sampled week, with almost no hour-to-hour variation. Hydro-Québec is
   dispatchable reservoir hydro under delivery contract. It is *not* variable
   renewable generation.
2. **The dominant shock is relocation, not net addition.** Legacy HQ interfaces
   fell from +558 MW (2025 window) to +27.5 MW (2026 window) while ~1,060 MW
   switched on in Maine. Roughly a gigawatt of Canadian injection **moved from
   Sandy Pond, Massachusetts and Highgate, Vermont into Lewiston, Maine.**

Fact 2 is what makes this a two-sided test rather than a one-sided one, and it
disqualifies the Massachusetts zones as controls.

## Data

`data/interim/isone_diagnostic_panel.parquet` — hourly, 2016-01-01 → 2026-06-30,
8 zones, no missing LMPs. Fields used: `datetime_beginning_ept`, `da_lmp_<zone>`,
`dst_transition_hour`. Prices are **day-ahead** hourly zonal LMP, $/MWh.

Rows with `dst_transition_hour == True` are excluded. No interpolation anywhere.
No new data pull is required.

## Units

| role | zones | rationale |
|---|---|---|
| **Reference** | **CT, RI** | ~4.1 GW combined. RI has no external interface of any kind; CT's ties are all NYISO. Neither hosts a Canadian injection point, so neither is treated in either direction. |
| **Treated** (predict basis **falls**) | **ME** | NECEC injects ~1,060 MW at Lewiston. |
| **Counter-treated** (predict basis **rises**) | **NEMA, SEMA, WCMA** | Sandy Pond (Ayer, MA) lost ~530 MW of Phase I/II injection over the same window. |
| **Contaminated — excluded from both** | **VT** | Highgate is a Canadian interface (−49 MW in the sample week). Small but nonzero; cannot serve as reference or placebo. |
| **Spillover diagnostic only** | **NH** | Interface-clean but electrically adjacent to ME. Reported, not decisive. |

**Basis** for zone *z* at hour *t*:

```
B_z(t) = da_lmp_z(t) − mean( da_lmp_ct(t), da_lmp_ri(t) )
```

Simple mean of the two reference zones, pre-committed as primary. A
load-weighted reference is reported as robustness only.

## Windows

**Post period starts 2026-02-01, not 2026-01-16.** January 2026 is excluded from
the treated year, and the exclusion is applied **symmetrically** to every
comparison year. Stated in advance, before results: NECEC's ramp profile is not
independently verified (the dose rests on a one-week March sample plus EIA's
stated commercial-operation date), EIA's paperwork date may lead sustained flow,
and January 2026 legacy HQ (+87 MW) looks unlike February (+538 MW). January is
the month most likely to be a partial-treatment smear. Two weeks is cheap
insurance against a diluted treatment.

**Comparison window: February 1 – June 30**, in each year **2016 … 2026** (11
years). The panel ends 2026-06-30, so this is the longest calendar-matched window
available and season-of-year is held fixed by construction.

## Statistics

For each zone *z* and year *y*, over the Feb 1 – Jun 30 window:

- **Level:** `L_z(y)` = mean of `B_z(t)`. Primary. Median reported as robustness.
- **Volatility:** `V_z(y)` = mean of `|B_z(t) − B_z(t−1)|`, hour-to-hour absolute
  change in the basis.

Year-over-year change `Δ_z(y) = L_z(y) − L_z(y−1)`, giving transitions
2017 … 2026. Standardized within zone against that zone's own pre-treatment
variability:

```
s_z(y) = Δ_z(y) / SD{ Δ_z(y') : y' = 2017 … 2025 }
```

## Inference — randomization, not asymptotics

Hourly LMP is heavily autocorrelated, so asymptotic standard errors on ~3,600
hourly observations would be badly overstated. Inference is by **rank against a
placebo grid**.

**Placebo grid:** `{ s_z(y) : z ∈ {ME, NH, NEMA, SEMA, WCMA}, y ∈ 2017 … 2025 }`
= **45 cells**, every one of them untreated. (VT excluded as contaminated; CT and
RI excluded because their own basis against a reference containing themselves is
degenerate.)

**Test statistic:** `s_ME(2026)`, compared against those 45 cells.
One-sided p = (# placebo cells ≤ s_ME(2026) + 1) / 46.

**Power limit, stated in advance:** the smallest attainable one-sided p is
1/46 ≈ 0.022. This design cannot produce a smaller number no matter how large the
effect. It is not capable of a conventional "highly significant" result and will
not be described as producing one.

## Pre-registered decision rule

**Primary (level, ME):**

- **SUPPORTED** if `s_ME(2026)` is negative **and** its one-sided rank p ≤ 0.05
  (i.e. ME 2026 is among the two most negative of the 46 values).
- **REJECTED** if `s_ME(2026)` is positive, or if its rank p > 0.20.
- **INCONCLUSIVE** otherwise (negative, 0.05 < p ≤ 0.20). Report as such; do not
  reinterpret.

**Counter-treatment check (Massachusetts):** under the relocation mechanism, the
mean of `s_z(2026)` across NEMA, SEMA, WCMA should be **positive**. This is a
signed prediction fixed in advance and is the strongest single feature of the
design — a generic "Maine got cheaper in 2026" story does not predict that
Massachusetts simultaneously got more expensive against CT/RI. If ME falls and MA
does *not* rise, the relocation mechanism is not what moved the price, and the
result is downgraded to INCONCLUSIVE regardless of ME's rank.

**Hour-uniformity discriminator (the answer to the pre-trend threat, below):**
NECEC is a firm near-flat block, so its effect on ME basis should be
approximately **uniform across hours of the day**. Pre-registered as: the
hour-specific `Δ_ME(2026)` has the **same sign in ≥ 20 of 24 hours**. A change
concentrated in a few hours is the signature of something that follows a dispatch
or demand pattern — i.e. of the HQ-economics confound, not of NECEC.

**Secondary (volatility, ME):** predicted sign is **negative or null**. A firm
1,060 MW block flattens the supply stack and should, if anything, *reduce* price
volatility. Fixed in advance: a *positive* volatility result contradicts the
firm-block mechanism and **will be reported as a contradiction**, not
reinterpreted as support for the advisor's "Canadian renewable variability"
hypothesis. That hypothesis is already weak on mechanism — reservoir hydro under
contract is dispatchable and scheduled, not variable.

## Named threats

**1. The pre-trend in legacy HQ flows.** `necec-dose-check.md` §4: legacy HQ
imports went negative in **October–November 2025**, months before treatment, and
stayed weak through the post window. Hydro-Québec's export behavior is trending
for its own reasons (reservoir levels, Québec domestic demand, export economics).
"ME basis fell in 2026" therefore has a live competing explanation with nothing to
do with Lewiston.

Two things address it, both fixed in advance: the calendar-matched multi-year
design (2025's same window had legacy HQ at +558 MW, so the comparison year is not
itself a trough), and the **hour-uniformity discriminator** above, which is the
only within-2026 feature that separates a firm block from a dispatch-following
flow. This threat is not fully eliminated and the write-up must say so.

**2. Basis blindness — stated before the result exists.** The basis design
differences out anything that moves all eight zones equally. NECEC's *system-wide*
level effect — 1,060 MW displacing the marginal unit lowers LMP across all of
ISO-NE — is invisible to this test by construction.

**A null therefore licenses exactly one claim: "no detectable *localized* price
effect at Lewiston." It does NOT license "NECEC had no price effect."** The
system-wide component is not identified here, and cannot be identified without an
external control market. NYISO is unsuitable — it has its own Hydro-Québec ties
and shares gas basis and weather with ISO-NE — so it is not attempted.

**3. Correlated placebo cells.** The 45 placebo cells are not independent: zonal
bases co-move within a year, so cells sharing a year are correlated. This makes
the effective number of independent placebos smaller than 45 and the rank p
somewhat optimistic. Direction of the bias is stated here; it is not corrected.

**4. Heavy tails.** ISO-NE LMP has large positive spikes (ME 2026 max $922/MWh).
The mean is the pre-committed primary because average price difference is the
economically meaningful quantity; the median is reported alongside as robustness.
Disagreement between them is itself reportable.

**5. Northern Maine is not in the data.** Per the ATCID, the Aroostook /
Penobscot / Washington County system radially connected to New Brunswick is
outside the ISO-NE control area. The treated zone is not the whole state.

## Outcome — run 2026-08-11

Run by `scripts/necec_price_test.py`; CSVs in `outputs/necec_price_test/`.
Window sizes are balanced: 3,599–3,624 hours per year, including 3,599 in both
2025 and 2026.

### Primary — SUPPORTED at the design's floor

Mean ME basis against the CT/RI reference, Feb–Jun, $/MWh:

| year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | **2026** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ME | −0.60 | −1.14 | −1.62 | −0.31 | +0.03 | −0.12 | −0.35 | +0.01 | −0.20 | −1.88 | **−4.82** |

- `Δ_ME(2026)` = **−2.94 $/MWh**; `s_ME(2026)` = **−3.62**
- **0 of 45** placebo cells fall below it (placebo range −2.07 to +1.95)
- one-sided rank **p = 0.0217** — the minimum the design can produce
- **Median robustness agrees exactly:** `s_ME(2026)` = −2.20, again 0 of 45,
  p = 0.0217. The result is not an artifact of price spikes.

In levels: in 2026 Maine's day-ahead price averaged **$56.41/MWh against
$60–63 everywhere else** in ISO-NE, while in 2025 the same gap was ~$1.50–2.50.
Maine's discount roughly tripled in the year NECEC energized.

**Pre-registered rule → SUPPORTED.**

### Counter-treatment (Massachusetts) — correct sign, weak magnitude

Predicted positive, and positive: NEMA +0.11, SEMA +0.70, WCMA +0.20,
**mean +0.34**. The sign prediction that a generic "Maine got cheap" story does
not make is confirmed, so the result is not downgraded. But +0.34 is an ordinary
value inside the placebo distribution — this clause passes, it does not
corroborate strongly.

**NH (spillover diagnostic) = −2.76**, swinging from +1.95 in 2025. New
Hampshire moved with Maine, not with the reference, which is what electrical
adjacency to a newly-long zone predicts. Pre-registered as non-decisive; it is
reported because it is consistent and because it means the effect is regional
rather than ME-idiosyncratic.

### Hour uniformity — passes, 24/24

`Δ_ME(2026)` by hour is **negative in all 24 hours** (threshold was ≥ 20),
ranging −5.59 to −1.01 $/MWh. No hour-of-day concentration, consistent with a
firm round-the-clock block rather than a dispatch- or demand-following flow.

Reported honestly: a large level shift will tend to move every hour, so the sign
test is a weak instrument. It rules out the specific alternative it was built to
rule out — an effect concentrated in peak hours — and no more. The 5× spread in
magnitude across hours is not itself uniform.

### Secondary (volatility) — CONTRADICTS the pre-registered prediction

| | 2025 | 2026 |
|---|---|---|
| ME basis volatility (mean hourly \|Δ\|, $/MWh) | 0.87 | **1.96** |

`s_ME_vol(2026)` = **+3.41**, above **all 45** placebo cells. Volatility more
than doubled. Every other zone rose only slightly (NH 0.30 → 0.52; the MA zones
0.11–0.29 → 0.24–0.38), so this is Maine-specific.

The prereg predicted **negative or null** on the reasoning that a firm block
flattens the supply stack. **That prediction failed, and is recorded as failed.**

*Post-hoc, and flagged as post-hoc — this does not rescue the prediction:* a
large firm injection into a zone that is already export-limited should make the
Maine export interface bind **intermittently** rather than continuously. Basis
then switches between a congested state and an uncongested one, and switching
raises hour-to-hour basis variance even though the injection itself is perfectly
flat. If that is right, the pre-registered reasoning confused a system-wide
effect (flatter stack) with a local one (more frequent congestion). It is a
plausible mechanism, not a tested one, and it needs a binding-constraint or
shadow-price series to check.

**It does not support the advisor's original hypothesis.** That hypothesis was
that *Canadian renewable variability* drives fluctuation. The dose check shows
the Canadian injection is a near-constant 1,059 MW block. Volatility rose
*because* a constant was added to a congested network, not because anything
variable arrived.

### The pre-trend threat survives — this is the main caveat

Threat 1 was not eliminated, and the data make it sharper than anticipated:

**The single most extreme cell in the entire placebo grid is Maine's own 2025**
(`s_ME(2025)` = −2.07, against a next-most-extreme of −1.44). Maine's basis was
already falling hard in the year *before* treatment.

Monthly detail shows why:

| month | 2025 | 2026 |
|---|---|---|
| Feb | −0.13 | **−10.63** |
| Mar | +0.36 | −2.11 |
| Apr | **−4.52** | −0.98 |
| May | **−3.81** | −6.79 |
| Jun | −1.19 | −3.99 |

April–May 2025 reached −4.52 and −3.81 with no NECEC in service, and comparable
shoulder-season episodes appear in 2018 (Apr −3.97) and 2022 (Apr −3.09,
May −2.13). **Deeply negative Maine basis is a recurring pre-NECEC phenomenon**,
almost certainly shoulder-season export congestion — low regional load plus
Maine wind saturating the Maine export interface.

What can be said, and what cannot:

- **Can:** 2026 is the most extreme year in the eleven-year record by a wide
  margin, it is outside the placebo distribution on both mean and median, the
  shift is uniform across all hours, and it coincides with a verified ~1,060 MW
  firm injection at Lewiston. Two points in favour of the timing: Nov–Dec 2025
  basis was *positive* (+1.36, +1.75) immediately before the break, and 2026 is
  negative in every single month.
- **Cannot:** rule out that NECEC intensified a trend already underway rather
  than starting one. The mechanism that produced −4.52 in April 2025 was
  available in 2026 too. Distinguishing "NECEC caused it" from "NECEC added
  ~1 GW to an export constraint that was already binding" is not possible with
  this design.

The honest formulation for the write-up: **NECEC did not create Maine's negative
basis — it roughly tripled it.**

### POST-HOC ADDENDUM (2026-08-11) — not pre-registered, added after the result

Two follow-ups. Neither touches the pre-registered result, which stands as
recorded above. Both are labeled post-hoc and must be described as such.

#### A. The January discontinuity — this substantially weakens the pre-trend objection

January was excluded from the test by design (partial-treatment smear). That
also parked the most diagnostic two weeks available. Splitting it at the
energization date, mean ME basis, $/MWh:

| year | Jan 1–15 | Jan 16–31 | shift |
|---|---|---|---|
| 2024 | −0.84 | −3.01 | −2.17 |
| 2025 | −1.69 | −0.73 | +0.97 |
| **2026** | **+1.45** | **−14.54** | **−15.99** |

Daily means across the boundary in 2026:

| Jan 10 | 11 | 12 | 13 | 14 | 15 | **16** | 17 | 18 | 19 | 20 | 21 | 22 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| +4.65 | +4.93 | +1.29 | +3.20 | +2.06 | +2.16 | **−2.85** | −1.93 | −1.47 | −3.92 | −8.87 | −6.48 | −2.14 |

**Maine's basis is positive on every one of the six days before energization and
negative on every one of the days after.** The sign flips on 2026-01-16, the
stated commercial-operation date, and does not flip back.

The two control years show ordinary within-January drift of −2.17 and +0.97
against 2026's −15.99, so this is not a calendar artifact of splitting January.

**Why this matters for Threat 1.** The competing explanation was shoulder-season
export congestion — a seasonal mechanism that produced −4.52 in April 2025. A
seasonal mechanism cannot produce a step change on a *specific mid-January day*
and hold it. This does not eliminate the pre-trend (Maine's basis was genuinely
drifting down through 2025), but it makes "NECEC merely coincided with an
existing trend" much harder to sustain. The *timing* is now tied to the
treatment date, not just to the treatment year.

Caveat on the caveat: this is a two-week comparison on ~700 hours, it is
post-hoc, and January 2026 was unusually cold across the region. It should be
presented as corroborating evidence, not as the primary result.

#### B. The volatility result is a TAIL effect, not a broad increase — headline corrected

`V_ME` was defined as `mean |ΔB|`, which is exposed to a handful of extreme
hours. Re-run three ways, Feb–Jun as pre-registered:

| definition | V(2025) | V(2026) | s_ME(2026) | cells ≤ |
|---|---|---|---|---|
| **mean \|ΔB\|** (pre-registered primary) | 0.872 | 1.960 | **+3.41** | 45/45 |
| mean \|ΔB\|, dropping top 1% of hours by system price | 0.868 | 1.874 | **+3.12** | 45/45 |
| **median \|ΔB\|** | 0.345 | **0.310** | **−0.30** | 10/45 |

Two things follow, and they point in different directions:

1. **It is not a system-price-spike artifact.** Removing the top 1% of hours by
   ISO-NE system price barely moves it (+3.41 → +3.12, still beyond all 45
   placebo cells). The scarcity-pricing explanation is ruled out.
2. **But the typical hour got slightly *calmer*, not noisier.** Median hourly
   basis movement fell from 0.345 to 0.310. The entire increase lives in the
   tail of the basis distribution.

**The statement "Maine's price volatility more than doubled" is therefore
misleading and is withdrawn.** The correct statement: *the median hour is
unchanged-to-calmer, while a minority of hours now show very large basis
swings.*

This refines rather than rescues the post-hoc congestion-switching story, and
the refinement is in its favour: intermittent binding of an export constraint
predicts exactly this shape — most hours uncongested and normal, a tail of hours
where the constraint binds hard and basis gaps open. A mechanism that made the
market broadly noisier would have moved the median. It still is not a tested
claim, and confirming it needs the binding-constraint / shadow-price series,
which is not in this panel.

The pre-registered prediction (negative or null) still **failed** on the primary
mean-based definition. That failure stands as recorded.

### Blindness clause, as pre-committed

This test measured a **localized** price effect at Lewiston. NECEC's system-wide
level effect is differenced out by construction and is **not** measured here.
Nothing above licenses any claim about NECEC's effect on ISO-NE's overall price
level.

### Status of the advisor's question

The advisor asked whether New England's fluctuation comes from its Canadian
connection. Complete answer after both runs:

- **Load volatility — no.** Fails on mechanism, geography and timing
  (`isone-canada-tie-verification.md`). Interface imports are supply and never
  enter metered demand.
- **Price level — yes, locally and substantially.** Maine's discount to the rest
  of ISO-NE roughly tripled, to −$4.82/MWh, in the year NECEC energized, outside
  the placebo distribution and uniform across hours. Caveated by a real
  pre-trend.
- **Price volatility — yes, but not for the reason proposed.** Maine's basis
  volatility more than doubled. The driver is a *constant* injection interacting
  with a congested export interface, not variable renewable output. Hydro-Québec
  delivers a firm scheduled block.
