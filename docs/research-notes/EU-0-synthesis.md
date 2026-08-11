# Europe — synthesis across EU-1 … EU-5

**Date:** 2026-08-11. Five parallel research threads; detail and sources live in
the numbered notes. This file records only what the five together imply.

## Headline

**The project's original question cannot be ported to Europe, and Europe should
not be added as market #9. But two genuinely new things were found, and one of
them addresses the obstacle that has blocked this project since May.**

---

## 1. What is dead

**The nodal congestion mechanism.** (EU-4, confirmed independently by EU-2.)
SDAC/EUPHEMIA solves a *zonal* welfare problem subject to inter-zonal limits and
never models the grid inside a zone. Intra-zonal congestion is therefore priced
at **exactly zero, everywhere, always, by construction.** Germany — the largest
load, the largest redispatch bill, much of the DC growth — is a **single bidding
zone**. No European geography gives a Loudoun-sized constrained pocket its own
price. There is nothing to decompose.

Also dead: ORDC-style scarcity pricing (no European analogue) and the
upper-tail/GPD framing. Europe's fat tail is **negative** — German negative-price
hours 301 → 457 → 573 across three record years — and ACER finds countries with
more negative hours have *fewer* spikes above 150 EUR/MWh. Both tails move, in
opposite directions.

**Europe as market #9 is near-worthless.** The Stage-1 horse race ports fine,
because it is already zonal. That is the argument against it: the sweep returned
level-beats-|gradient| in 11/11 panels including the low-DC control. European
zones would be panels 12–13 of a result already in hand.

**The EU database is legally closed — spend no time on it.** (EU-3.) Art. 5(5) of
Delegated Reg. (EU) 2024/1364 pre-designates facility-level records confidential
under *both* Reg. 1049/2001 and Aarhus 2003/4/EC. A University of Amsterdam
postdoc requested exactly this and was refused by DG ENER on 2025-08-29 (case
2025/3469). Coverage would disqualify it anyway: 770 of ~2,161 EU data centres
reported (36%), six Member States zero. Ireland shows 1,411.76 GWh there against
CSO's 6,339 GWh for 2023 — roughly a fifth of actual load.

---

## 2. What is new and worth doing

### (a) UK Power Networks half-hourly per-site data-centre load profiles

**This is the find.** (EU-3.) `ukpn-data-centre-demand-profiles`: **5.44M
records, ~100 identified DC sites, half-hourly, 2023-01-01 onward, updated
2026-08-01, CC BY 4.0.**

Since May the project's blocking constraint has been that no facility-level
data-centre load data exists publicly — verified across all eight North American
markets, and confirmed again for ERCOT. This is the first direct measurement of
data-centre load shape found anywhere.

**Why the "shapes, not magnitudes" caveat does not bite.** Values are observed
apparent power ÷ contractual max import capacity. That is a *normalized* series —
and the project's question is about **volatility**, which is a property of shape.
Measuring how spiky a data centre's load is does not require knowing its MW. The
normalization is nearly irrelevant to the question actually being asked.

**What it could settle.** The proposal's premise — that AI/hyperscale load is
"spiky," citing Li & Li and Chen et al. — has been assumed throughout and never
tested on data. ~100 real sites at half-hourly resolution tests it directly. It
can confirm the premise, or falsify it, and either is a result.

**Gating uncertainty:** the records/export API returns 403 unauthenticated;
registration is free but the researching agent did not create an account, so
**nobody has yet confirmed the data actually downloads.** Five-minute test,
decides the whole thread.

**Scope caveat:** UK, not EU. A DNO open-data decision, unrelated to EED — do not
expect an EU equivalent.

### (b) Ireland vs the Netherlands breaks the ISO-NE collinearity

(EU-5.) The 2026-08-11 ISO-NE diurnal test came back **uninformative** because
zone size, rural-ness and solar share were fully collinear at n=8.

In Europe they come apart. **Ireland 42.8% vs Netherlands 46.1% total wind+solar
— near-identical — but 4.7% vs 21.1% solar.** A 4.5× split on precisely the axis
H_solar names, at matched total VRE. **Ireland is the control, not the
treatment.**

This is a **load-side** question. It needs no nodal pricing, so it survives §1
intact, and it advances the one genuinely open question in the project.

---

## 3. Ireland — the market everyone will ask about

- **Most DC-saturated grid on earth: 23.2% of metered electricity, 2025**
  (7,662 GWh), CSO. Next country is the Netherlands at 4.6%. A 5× gap cannot be
  a definitional artifact.
- **CSO series verified against the PxStat API (table MEC02): quarterly,
  2015Q1–2025Q4, 44 quarters, free, no registration.**
- **Three disqualifying limits for the volatility question:**
  1. **Quarterly and national.** Zero geography, zero facilities. The profile is
     near-monotonic (2025: Q1 1,821 → Q4 1,991 GWh), so variation is dominated by
     trend growth. It fixes *existence*, not identification.
  2. **CSO has no data-centre classification.** Sites are identified
     heuristically — name matching, business parks, meters above 1 GWh — and CSO
     warns new small sites fall below its thresholds. This is a constructed
     series, not a register.
  3. **Footprint mismatch.** SEM is one price zone spanning Republic + Northern
     Ireland; the CSO series is Republic-only. EirGrid/SONI publish IE / NI /
     All-Island load separately, so *load and price* can be matched at all-island
     level — the mismatch is specifically the **DC covariate**.
- **Unresolved, flagged by EU-1:** a 1.7 TWh gap between EirGrid/CRU's 9.4 TWh
  forecast for 2025 and CSO's measured 7.662 TWh. All-island does not obviously
  explain it (Northern Ireland's *entire* consumption is ~8 TWh). **The
  widely-quoted 22%→31%-by-2034 trajectory rests on that base — do not use it
  until resolved.**
- **Two press narratives corrected against primary sources (EU-5):** Ireland
  never had a moratorium — CRU/2025236 says twice that one "would have been
  disproportionate." And Ireland **mandates co-location but forbids the netting**
  (generation ≥10 MVA separately connected and metered). That is the inverse of
  the US FERC problem, and it means "BTM erodes the shelf life of metered load
  data" is **not symmetric across jurisdictions**.

---

## 4. If a European price cross-section is ever wanted

(EU-2.) Only four countries have a within-country price cross-section: **Italy 7
zones** (since 2021-01-01), **Norway 5, Sweden 4, Denmark 2** — 18 total.
Everything else in SDAC is single-zone. **Italy is the closest European analogue
to a US zonal ISO.** Poland is a trap: locational unit dispatch and 15-min
imbalance settlement since 2024, but still one zone and one national day-ahead
price.

Open question that decides Italy, resting on two soft inferences EU-2 could not
close: does ENTSO-E return Actual Total Load for `BZN|IT-North`
(`10Y1001A1001A73I`)? The EIC codes found are *control area* codes, which is not
proof. One query settles it; EU-2 §9.0 has the query and both branches.

---

## 5. Immediate actions, in order

1. **Five minutes — register for UKPN Open Data and confirm the DC profile
   dataset downloads.** This single test decides whether §2(a) is live.
2. **Today — start ENTSO-E API registration.** Requires a *human* step (email
   `transparency@entsoe.eu`, ~3 working days). Free; Nord Pool and EPEX are
   paywalled and unnecessary.
3. Then, and only then, decide between §2(a) and §2(b). They are independent.

**Known traps, each worth a day (EU-2):** the legacy ENTSO-E `Guide.html` /
`RestfulAPI_IG.pdf` URLs cited in most papers are dead — use the Zendesk KB and
Postman collection. Limits are 400 req/min per token, 1 year per request, 100
TimeSeries per response. 15-min MTU landed on delivery day 2025-10-01, **but
Ireland went to 30-min, not 15**. `entsoe-py`'s `query_day_ahead_prices()` broke
on that switch (Italian zones first) — pin recent and smoke-test. OPSD is dead
(last version 2020-10-06). Hirth et al. 2018 found ENTSO-E Actual Total Load
deviating >10% from other sources; structural breaks at the DE-AT split
(2018-10-01) and the Italian zone reform (2021-01-01).

---

## 6. Carried forward — unverified or unexplored

- **UKPN download unconfirmed** (403 unauthenticated; no account created).
- **Germany's EnEfG § 13(1)** obliges per-facility *publication* at ≥300 kW
  including postcode and total consumption, with aggregation across sites
  forbidden — but there is **no public search index**, and BMWE says the register
  route requires operator release. Real but labour-intensive; a project in
  itself.
- **The one unexplored thread that could change the picture:** DG ENER's refusal
  makes public availability a **Member State** responsibility under Art. 12(1).
  Only Germany was checked in depth. A national public register in any other
  Member State would be facility-level and public.
- **Nordics/NL are negatives.** Denmark's Energinet publishes hourly by industry,
  but all 33 categories were enumerated and data centres are **not separable**
  (buried in "Telecom & IT services"). Norway's Nkom register is public but
  carries only name, org number and a crypto flag — no MW, no consumption.
  Sweden and Finland have no official series.
- ACER's "five times" price-spread growth **does not reconcile with ACER's own
  chart** (bar labels imply ~3.9×). Quote the sentence and the 2020 base of 28.3
  EUR/MWh; do not state a 2025 level.
- EU-4 asserted a day-ahead timing defect that "lands backwards on the existing
  US panels." **Unverified against this repo — do not act on it until checked
  directly.**
