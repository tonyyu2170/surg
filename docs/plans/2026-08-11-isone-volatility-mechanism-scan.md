# EXPLORATORY — what else could explain the VT/ME/RI volatility rise?

**Date:** 2026-08-11
**Status:** ⚠️ **EXPLORATORY. Not pre-registered. No claim here may be quoted as
a result.** Hypothesis-generating only; the discriminating test is the DER panel
regression described in §5.
**Context:** H_canada is dead (`2026-08-11-isone-canada-tie-verification.md`).
H_solar was neither supported nor rejected by the diurnal fingerprint
(`2026-08-11-isone-der-fingerprint-prereg.md`) because all eight zones share the
same diurnal shape. This scan asks what else is on the table.

## 1. Candidate mechanisms

| hypothesis | mechanism | acts on metered demand? |
|---|---|---|
| **H_solar** | metered load is *net* of behind-the-meter PV; more DER = noisier series with no change in demand behaviour | yes |
| **H_size** | small zones aggregate fewer customers, so individual swings average out less | yes |
| **H_baseload** | loss of flat always-on industrial load leaves a smaller stable core (ME paper mills, VT GlobalFoundries; no data centers to replace it) | yes |
| **H_weather** | more temperature extremes → larger swings | yes |
| **H_grid** | weaker transmission infrastructure | **no** — fails for the same reason H_canada did: transmission affects price and congestion, never how much customers consume |

## 2. Test — duck-curve migration (a *level* signature, independent of the gradient series)

Share of days whose **minimum** load falls in hours 10–16. Behind-the-meter PV
is the only mechanism that moves a daily minimum from pre-dawn to midday.

| zone | group | 2016 | 2025 | change |
|---|---|---|---|---|
| **vt** | RISING | 1.4% | **68.2%** | **+66.9 pp** |
| **me** | RISING | 0.0% | **36.7%** | **+36.7 pp** |
| sema | falling | 0.0% | 13.2% | +13.2 pp |
| wcma | falling | 0.0% | 8.5% | +8.5 pp |
| ct | falling | 0.0% | 8.5% | +8.5 pp |
| nema | falling | 0.0% | 0.8% | +0.8 pp |
| **ri** | **RISING** | 0.0% | **0.5%** | **+0.5 pp** |
| nh | falling | 0.0% | 0.3% | +0.3 pp |

Spearman against the volatility trend: **ρ = +0.707, p = 0.050, n = 8.**

Vermont's median minimum-load hour moved from **03:00 to 11:00**; 68% of its days
now bottom out at midday. Maine is a third of the way there. **Rhode Island has
not moved at all** — 98% → 88% of its minima still occur in hours 00–05.

## 3. Test — baseload erosion (Tony's composition hypothesis)

Floor ratio = annual minimum load / annual mean load. Falls when the flat
always-on core of demand shrinks relative to the swinging part.

| zone | volatility trend | duck migration | **floor erosion** |
|---|---|---|---|
| vt | +38.9% | +66.9 pp | **−91.7%** |
| me | +18.9% | +36.7 pp | **−20.1%** |
| ri | +8.6% | +0.5 pp | **−38.5%** |
| sema | −3.2% | +13.2 pp | −16.2% |
| wcma | −4.8% | +8.5 pp | −12.4% |
| ct | −7.8% | +8.5 pp | −7.6% |
| nh | −8.2% | +0.3 pp | +3.5% |
| nema | −12.7% | +0.8 pp | +2.1% |

Spearman against the volatility trend: **ρ = −0.952, p = 0.0003, n = 8** — and
the three rising zones separate cleanly from the five falling ones with **no
overlap** (rising −20.1 to −91.7; falling +3.5 to −16.2).

This is a stronger cross-sectional correlate than zone size (ρ = −0.786,
p = 0.021), which is what the prioritization doc had.

⚠️ **Partial circularity, stated up front.** Floor ratio and |gradient| are both
dispersion measures on the same series, so some of this correlation is
definitional rather than causal. They are not identical — a series can have a low
floor with slow smooth transitions, or a high floor with fast oscillation — but
this correlation must not be read as "baseload loss causes volatility." It is a
description, not a mechanism test.

## 4. What this changes — the rising trio is NOT one phenomenon

The prioritization doc framed VT/ME/RI as "one description, not three
hypotheses": small, rural, high-DER. **The duck-curve test contradicts that.**

- **Vermont — solar, overwhelmingly.** Minimum-load hour migrated 03:00 → 11:00.
  Annual minimum fell from 420 MW to 31 MW (5.5% of mean; five hours below
  50 MW in 2025, none before). Metered demand at midday is approaching zero
  because the meter has stopped seeing the load, not because the load left.
- **Maine — solar, partially.** Same signature at roughly half Vermont's
  magnitude.
- **Rhode Island — NOT solar.** Zero duck migration, yet a 38.5% floor erosion,
  and its minimum is still at 3 a.m. Solar does not operate at 3 a.m. **Rhode
  Island's stable overnight core shrank**, which is Tony's composition
  hypothesis, not H_solar.

**At least two distinct mechanisms are producing the same headline.** RI is the
zone that killed H_canada (rising with no tie) and it is now also the zone that
breaks H_solar. Any single-mechanism story for the trio is wrong.

Note this also rehabilitates something the fingerprint prereg discarded. That run
found a *magnitude* gradient (rising zones +66% to +126% at midday vs +32% to
+49% for falling zones) and rejected it as "degree, not shape." A continuous
driver like DER penetration predicts exactly a magnitude gradient and no shape
break — so the shape test may have been uninformative *because the shape is
universal and the magnitude carries the signal.*

## 5. The discriminating test, still outstanding

Pre-identified in two prior documents and still not run: **regress zone
volatility on per-zone DER penetration.**

Now feasible at zero cost — **EIA-861 annual net-metering capacity by state is a
free bulk download**, and 5 of 8 ISO-NE zones map 1:1 to states (ME, NH, VT, RI,
CT); the three MA zones sum to the state.

**Design note that must be settled first:** if DER-per-MW is strongly collinear
with zone size across n = 8, a cross-sectional regression cannot separate H_solar
from H_size. The fix is a **zone-year panel with zone fixed effects** — zone FE
absorbs size entirely (size does not change over ten years), so identification
comes from *within-zone growth* in DER, which H_solar predicts and H_size says
nothing about. Compute `Spearman(zone mean MW, DER per MW)` first; it decides
which design is admissible.

**This deserves its own locked pre-registration.** It has been named as the
discriminating test twice; running it exploratorily would waste the project's one
clean shot at it.

## 6. Not tested, and why

- **H_weather** — requires temperature data not on disk. Proxying weather with
  peak load is unsound because the competing hypotheses themselves move load.
  Needs free NOAA station data for a few New England airports.
- **Seasonal (winter vs summer)** — deliberately skipped. The fingerprint
  prereg's own post-mortem established that New England's compressed winter solar
  day makes hours 11–14 ramp-shoulder in December and plateau in June, so the
  seasonal comparison is a known-bad design.
- **Maine state ≠ ME zone** — Aroostook and parts of Penobscot/Washington are
  outside ISO-NE. EIA-861 Maine will include load and PV that the ME series does
  not. Magnitude must be checked before the regression.
