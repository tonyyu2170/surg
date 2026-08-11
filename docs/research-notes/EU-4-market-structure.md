# EU-4: European Market Structure vs. US ISO/RTO — What Breaks, Changes, or Survives

Research date: 2026-08-11. Desk research only; no data pulled. Scope is deliberately narrow:
European market structure **as it bears on this project's method**, not a general survey.

Primary sources preferred (BMWE, ACER, ENTSO-E, EUR-Lex, BNetzA/SMARD, FfE, peer-reviewed).
Anything I could not pull from a primary document is flagged inline and collected in
**§ Not verified** at the end.

---

## Bottom line up front (this is § 6, stated once at the top)

**The nodal core of the project does not transfer to Europe. The zonal sweep transfers
completely — and that is exactly why it is not worth much.**

- The NOVA mechanism — data-centre load volatility in a constrained pocket driving the
  **congestion component** of a nodal price — has **no European observable**. There is no
  congestion component in a European day-ahead price. Inside a bidding zone the network is
  assumed uncongested *by construction*. There is no European geography at which a
  Loudoun-sized pocket has its own price.
- The Stage-1 horse race (zonal price ~ zonal load level vs. |zonal load gradient|) ports
  **unchanged**, because it is already a zonal specification. ENTSO-E's Transparency
  Platform supplies both series per bidding zone. This would be panels 12, 13, … of the
  existing eleven.
- But the sweep has already returned level-beats-|gradient| in **11/11 panels including
  the low-data-centre control** (ISO-NE, 64/64). Adding European zones is *more of the
  finding already in hand*, not a test of the hypothesis the project started with.
- The one genuinely new thing Europe offers is that **the congestion response is published
  as a physical quantity** — redispatch, per market time unit, naming the constrained
  network element (Reg. (EU) 543/2013 Art. 13). That is a real dependent variable and in
  some respects a better one than PJM's congestion component. **But the question it can
  answer is a German north–south wind-transport question, not a data-centre volatility
  question.**

Full assessment with caveats in § 6.

---

## 1. Zonal vs. nodal pricing

### 1.1 How the European day-ahead market clears

European day-ahead trading runs through **SDAC (Single Day-Ahead Coupling)** — one
pan-European implicit auction operated jointly by the NEMOs (nominated electricity market
operators: EPEX SPOT, Nord Pool, GME, OMIE, EXAA, OTE, etc.), coordinated under the CACM
Regulation. SDAC clears using a single common algorithm, **PCR EUPHEMIA**, which
simultaneously determines:

1. one clearing price per **bidding zone** per market time unit, and
2. the implicit allocation of cross-zonal transmission capacity between zones.

There is no separate transmission-rights auction for day-ahead energy: cross-border capacity
is allocated as a by-product of the energy clearing ("implicit auction"). Cross-zonal
capacity enters EUPHEMIA either as flow-based domains (Core capacity calculation region) or
as NTC limits (most other borders).

**Resolution changed recently and this matters for panel construction.** SDAC moved from a
60-minute to a **15-minute market time unit on trading day 30 September 2025 / delivery day
1 October 2025**, simultaneously on all borders and in all bidding zones
([EPEX SPOT](https://www.epexspot.com/en/news/successful-implementation-15-minute-market-time-unit-mtu-sdac)).
Any European day-ahead price panel spanning that date has a **resolution break in the middle
of the series**, not at an endpoint.

### 1.2 What a bidding zone is

A bidding zone is the largest geographical area within which market participants can trade
energy **without** capacity allocation. The defining modelling assumption is that the network
*inside* the zone is unconstrained — a copper plate. Congestion is represented only at zone
*borders*.

Current multi-zone arrangements:

| Country | Zones | Notes |
|---|---|---|
| Norway | 5 (NO1–NO5) | [Nord Pool](https://www.nordpoolgroup.com/en/the-power-market/Bidding-areas/) |
| Sweden | 4 (SE1–SE4) | Same |
| Denmark | 2 (DK1 west, DK2 east) | Same |
| Italy | 7 geographical (NORD, CNOR, CSUD, SUD, CALA, SICI, SARD) | CALA added from 1 Jan 2021 per ARERA Decision 103/2019/R/eel; plus virtual zones for foreign/limited-production poles |
| Germany–Luxembourg | **1** | Single zone; the country with by far the most redispatch |
| Most others | 1 per country | — |

The **total** number of European bidding zones is not a figure I could pin to a primary
source — secondary sources I saw disagree (≈30 vs. ≈41 depending on whether non-EU/ENTSO-E
observer areas are counted). Flagged in § Not verified. The number that actually matters for
this project is the *order of magnitude*: **tens, not thousands**.

### 1.3 Why there is no per-node congestion component

PJM computes LMP = system energy + marginal congestion + marginal loss **per pricing node**,
by taking shadow prices on binding transmission constraints out of the security-constrained
dispatch. EUPHEMIA does not solve a security-constrained network dispatch of the internal
grid at all. It solves a welfare-maximisation over zonal order books subject to *inter-zonal*
capacity limits. There is no internal network model from which an intra-zonal shadow price
could be extracted, so there is nothing to decompose.

Consequently:

- **Congestion appears in price only as a spread between adjacent zone prices.** A DE-LU/DK1
  spread is a statement about that border, not about anywhere inside Germany.
- **Intra-zonal congestion is priced at exactly zero** for every participant in the zone,
  everywhere in the zone, at all times, by assumption.
- Intra-zonal congestion is real, and is resolved **after** the market clears, by the TSO,
  outside the price (§ 2).

### 1.4 Practical consequence for a congestion-via-price researcher

Blunt version: **you cannot study intra-zonal transmission congestion through European
day-ahead prices, because the market design has removed it from the price on purpose.**

The specific failure for this project: Germany — where the congestion is, where the
redispatch bill is, and where a large share of European data-centre growth is going — is
**one price**. If Loudoun County were inside a European bidding zone, its "LMP" would be the
same number as Munich's and Hamburg's, in every hour, forever. The entire spatial identifying
variation the NOVA design rests on is definitionally absent.

A second, subtler problem: **aggregation dilution.** The Transparency Platform reports actual
total load *per bidding zone*. The DOM zone is a relatively small load area; the German zone
is several times larger. The same MW ramp is a much smaller share of the reported aggregate,
so a |gradient| regressor built from zonal load is a noisier proxy for any localised load
event than the DOM equivalent was. (Zone size ratio not verified — see § Not verified.)

---

## 2. Where congestion cost actually shows up

### 2.1 The four instruments

Because the market clears as if the zone were a copper plate, the TSO must fix the resulting
infeasibility physically, after the fact:

1. **Redispatch** — the TSO instructs generators *upstream* of the constraint to reduce
   output and generators *downstream* to increase it, holding net balance. This is the direct
   analogue of what a nodal market would have priced ex ante.
2. **Countertrading** — the TSO buys/sells energy across a zone border to change the
   cross-zonal exchange, relieving the constraint by trade rather than by dispatch order.
3. **Curtailment of renewables** (in Germany, folded into the redispatch regime) — reducing
   RES infeed, with compensation.
4. **Reserve/grid reserve** (Germany: *Netzreserve*) — contracted-out-of-market capacity held
   specifically for congestion, incurring both availability and deployment costs.

Countertrading and redispatch are the two the EU legal framework names explicitly; the German
reporting adds curtailment compensation and *Netzreserve* as separate cost lines.

### 2.2 What is published, by whom, and at what granularity

**This is the finding that most changes the answer to § 6, so it is worth stating precisely.**

**Regulation (EU) No 543/2013, Article 13** (congestion management measures) requires
publication on the ENTSO-E Transparency Platform of, **per market time unit**:

- *Redispatching*: "the action taken (that is to say production increase or decrease, load
  increase or decrease), **the identification, location and type of network elements
  concerned by the action**, the reason for the action, capacity affected by the action taken
  (MW)"
- *Countertrading*: "the action taken (that is to say cross-zonal exchange increase or
  decrease), the bidding zones concerned, the reason for the action, change in cross-zonal
  exchange (MW)"

Deadline: "as soon as possible but **no later than one hour after the operating period**,
except for the reasons which shall be published as soon as possible but not later than one
day after the operating period."
([EUR-Lex CELEX:32013R0543](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013R0543))

So the European redispatch record is, on paper, **per-MTU, near-real-time, and
element-identified** — it names the constrained network element, which a PJM congestion
component only implies. That is a stronger congestion observable than the project has been
assuming Europe lacks.

**Congestion income / rents** are published under the same regulation, Article 12:
Art. 12(1)(a) "the auction revenue (in Currency) per border between bidding zones" (explicit
allocation) and Art. 12(1)(e) "the congestion income (in Currency) per border between bidding
zones" (implicit allocation), both "no later than one hour after each capacity allocation"
(Art. 12(2)(a)). Note the granularity: **per border**, not per element and not per node.
Congestion rent is therefore an inter-zonal quantity and is *not* a measure of intra-zonal
congestion.

**Germany's national platform.** The four German TSOs (50Hertz, Amprion, TenneT, TransnetBW)
publish redispatch measures jointly on **netztransparenz.de**, an obligation created by
BNetzA ruling **BK6-11-098** (30 Oct 2012) requiring publication of all adjustments to active
power infeed on a common website. BNetzA/SMARD additionally publish quarterly and annual
*Netzengpassmanagement* volume and cost reporting. I did **not** download the netztransparenz
files or verify their field schema — flagged in § Not verified.

### 2.3 The numbers

**EU-wide (ACER, 2025 monitoring report on cross-zonal electricity trade, published
5 September 2025):**

- EU TSOs spent **€4.3 billion on 60 TWh** of remedial actions to manage grid congestion in
  **2024**.
- Core-region TSOs made available on average **54%** of physical capacity on the most
  congested lines, against the **70%** requirement.
- ACER estimates **~€580 million** of foregone welfare in 2024 from incomplete 70%
  implementation in Core; only ~40% of the potential gain was realised.
- **147 severe price spikes** in South-East Europe in summer 2024 could potentially have been
  avoided had 70% been offered.

**Germany (BNetzA / SMARD):**

| Period | Total *Netzengpassmanagement* cost | Note |
|---|---|---|
| 2023 | €3.335 bn | |
| 2024 | €2.776 bn (preliminary) / €2.954 bn (as restated in the 2025 comparison) | **The preliminary and restated 2024 figures differ — use the restated one for a 2024/2025 comparison and say which you used.** |
| 2025 (full year) | **€3.071 bn**, +≈4% vs. 2024 | |

Q3/2025 breakdown, as an illustration of the reported line items
([SMARD](https://www.smard.de/page/home/topic-article/444/219200/volumen-und-kosten-gestiegen)):

- Total cost **€667 m** (Q3/2024: €608 m, +≈10%)
- Total measure volume **5,650 GWh** (Q3/2024: 5,266 GWh, +≈7%)
- Redispatch with conventional plant: **€207 m** deployment cost
- RES curtailment compensation: **€127 m**
- *Netzreserve*: **€317 m** total (€239 m availability + €78 m deployment)
- Countertrading: **€17 m** net

Germany alone is therefore running roughly **€3 bn/yr** against an EU-wide remedial-action
bill of **€4.3 bn** in 2024. Germany is not "a" case study of European congestion cost; it is
most of it. That is precisely because it is one enormous bidding zone with its wind in the
north and its load in the south.

---

## 3. The bidding-zone review and the splitting debate

### 3.1 The legal machinery

- **Reg. (EU) 2019/943 Art. 14** requires ENTSO-E to carry out a periodic bidding zone review
  (BZR).
- **Art. 14(7)**: where structural congestion is identified, the affected Member State must
  decide, within **six months** of receiving the report, either to **amend its bidding zone
  configuration** or to **establish an action plan under Art. 15**.
- **Art. 15** governs those action plans (measures to reduce structural congestion, with a
  linear trajectory of cross-zonal capacity).
- **Art. 16(8)** sets the **70% minimum** of the transmission capacity of critical network
  elements to be released for cross-zonal trade, to be met by **31 December 2025**.
- **Art. 10(1)**: "There shall be neither a maximum nor a minimum limit to the wholesale
  electricity price." Art. 10(2) nevertheless permits NEMOs to set harmonised *technical*
  bidding limits with an automatic adjustment mechanism (see § 5).

### 3.2 What the 2025 review found

- **ACER Decision 11/2022** (August 2022) set which alternative configurations must be
  studied — Germany drew by far the most scrutiny (multiple split options; other named
  countries one each).
- **ENTSO-E published the BZR for the 2025 target year on 28 April 2025**, assessing
  **14 alternative configurations** against **22 criteria** in four categories (network
  security, market efficiency, stability/robustness of zones, energy transition). Output data
  released 28 May 2025.
  ([ENTSO-E](https://www.entsoe.eu/network_codes/bzr/))
- **Central Europe result:** every German–Luxembourg split studied (2, 3, 4 and 5 zones)
  showed higher economic efficiency than the status quo, ranging **€251 m to €339 m** for
  target year 2025, with the **five-zone split (DE5) highest at €339 m**.
- **Nordic result:** *no* configuration showed improved economic efficiency versus the
  current arrangement. Sweden's SE1–SE4 and Norway's NO1–NO5 are, on this evidence, already
  about right.
- **ACER Opinion, 18 September 2025:** the TSOs **understated** the benefits. ACER puts the
  benefit of splitting DE-LU plus reconfiguring the Netherlands at **€450–540 m per year**,
  **~70% higher** than the TSOs' assessment, finding that the TSOs overestimated the
  effectiveness of coordination in Central Europe and underestimated reconfiguration costs on
  the basis of limited stakeholder consultation.
  ([ACER](https://www.acer.europa.eu/news/electricity-system-operators-bidding-zone-study-significantly-underestimates-benefits-reshaping-europes-bidding-zones))

### 3.3 Germany said no

The decisive document is Germany's own: **"Bidding Zone Action Plan – pursuant to Art. 15 of
Regulation (EU) 2019/943," Federal Ministry for Economic Affairs and Energy (BMWE)**, PDF
created December 2025. Read directly. Verbatim:

> "The Federal Republic of Germany remains committed to the existing single German-Luxembourg
> bidding zone."

> "The BZR does not explicitly identify any structural congestion in the German-Luxembourg
> bidding zone. It nevertheless comes to the conclusion that pan-European economic efficiency
> could be increased if Germany amended its bidding zone configuration in 2025. In the BZR,
> however, ENTSO-E draws attention to methodological flaws in the review. The German TSOs
> also agree with the assessment of the methodological flaws referred to. **The validity of
> the BZR is therefore disputed.**"

> "This means there is no legal basis for splitting the German-Luxembourg bidding zone
> against Germany's will."

Germany's stated reasons: the BZR is a single-year (2025) snapshot; the simulated prosperity
gains are "far lower than the estimated adjustment costs," so new zones "would have to remain
in place for many years in order to be profitable"; the intra-German HVDC lines (SuedLink,
SuedOstLink, A-Nord, Ultranet) will materially raise internal transport capacity and reduce
bottlenecks; and splitting would raise investment uncertainty and regional consumer-cost
differences. The commitment is also written into the CDU/CSU–SPD coalition agreement.

Supporting facts from the same document:

- Germany's 2019 action plan committed to a **linear trajectory to 70%** cross-zonal capacity
  by end-2025. Reported trajectory (%):

  | Border | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | from 31.12.2025 |
  |---|---|---|---|---|---|---|---|
  | CWE/Core | 11.5 | 21.3 | 31.0 | 40.8 | 50.5 | 60.3 | 70.0 |
  | DE–SE4 | 41.4 | 46.2 | 50.9 | 55.7 | 60.5 | 65.2 | 70.0 |
  | DE–DK1 | 23.9 | 31.6 | 39.4 | 47.0 | 54.6 | 62.3 | 70.0 |
  | DE–NO2 | 0 | 11.7 | 23.3 | 35.0 | 46.7 | 58.3 | 70.0 |
  | DE–DK2 (Kontek) | 70.0 | 70.0 | 70.0 | 70.0 | 70.0 | 70.0 | 70.0 |
  | DE–DK2 (KFCGS) | 0.0 | 11.7 | 23.3 | 35.0 | 46.7 | 58.3 | 70.0 |

- BNetzA approved the latest report on available cross-zonal capacity for 2024 in **August
  2025** under Art. 15(4).
- Grid build-out: **128 projects, 16,600 km** of transmission lines planned/approved/under
  EnLAG and BBPlG; as of Q1/2025 ~**5,500 km under construction** and ~**2,500 km
  operational**, versus ~1,800 km approved and ~1,200 km implemented in 2019.
- The updated action plan explicitly **will not** set a new linear trajectory: the Art. 15(2)
  exception "was a one-off case," and the Art. 16(8) 70% requirement binds regardless.

### 3.4 Is Europe moving toward finer locational granularity?

**No — not in any sense relevant to this project.**

- The direction of travel is a fight over whether the largest market should go from **1 zone
  to somewhere between 2 and 5**. The maximal proposal on the table, DE5, would give ~80
  million people five prices. PJM has thousands of pricing nodes.
- Even that maximal proposal has been **refused by the Member State**, which has instead
  exercised its Art. 14(7)/Art. 15 right to submit an action plan.
- The Nordic review found the *existing* multi-zone configurations already efficient — i.e.
  no case for further splitting there either.
- The regulator (ACER) and the Member State are in open disagreement, with the Member State
  disputing the study's validity and asserting there is no legal basis to split it against
  its will.

**Status as of this research date:** Germany's December 2025 Art. 15 action plan is the most
recent *primary* document I could retrieve. Whether the European Commission has since acted —
Art. 14 provides for Commission involvement where Member States cannot agree — I could **not
verify**. See § Not verified. Do not assert a 2026 outcome.

---

## 4. Balancing and imbalance markets

### 4.1 Structure and resolution

Governed by the **Electricity Balancing Guideline, Reg. (EU) 2017/2195 (EBGL)**:

- **Art. 53(1): a 15-minute imbalance settlement period (ISP)**, to be applied by all TSOs in
  all scheduling areas by **18 December 2021**.
- **Art. 52(2)(c): a single imbalance price** (as opposed to dual pricing).
- Reg. (EU) 2019/943 requires imbalance price information to be published **as close to real
  time as possible**; some TSOs publish **minute-by-minute** updates of imbalance price and
  system imbalance.

European platforms for cross-border balancing energy:

- **PICASSO** (aFRR activation) and **MARI** (mFRR activation), both operational since 2022,
  with **staggered national accession** through 2025–2026 (e.g. Nordic mFRR platform go-live
  4 March 2025 before European accession; TenneT NL targeting MARI Dec 2025; PSE ~Sept 2026;
  RTE delayed by at least a further year).
- **IGCC** (imbalance netting), covering 24 countries / 30 TSOs.

**Ireland (SEM)** is a useful special case: the imbalance price is computed over a
**5-minute imbalance pricing period**, averaged over a **30-minute settlement period**.
Ireland's constraint/congestion cost analogue is *Dispatch Balancing Costs*, recovered
through the **Imperfections Charge**, forecast and reported through EirGrid/SONI and overseen
by CRU/the SEM Committee.

### 4.2 Is this a better place to look than day-ahead? Yes — and the point applies backwards

**Yes, and this is a genuine methodological criticism that also lands on the existing US
work.** A day-ahead price is set in an auction cleared roughly 12–36 hours before delivery.
It **cannot** respond to a same-hour load ramp, because the ramp has not happened yet when
the price is formed. Regressing a day-ahead price on a contemporaneous |load gradient| is
close to a timing error dressed up as a specification: at best it picks up the *forecast* of
the ramp, at worst nothing.

The genuinely real-time European price signals are:

1. **Imbalance prices** — 15-min ISP EU-wide (5-min pricing period in SEM), often published
   at sub-minute update frequency. These are the closest European object to a US real-time
   price.
2. **Balancing energy prices** from PICASSO/MARI.
3. **Intraday** (SIDC continuous trading), which does respond within the day.

**But the locational problem does not go away.** An imbalance price is a **scheduling-area /
LFC-area** price. It answers "was the *system* short," not "was *this pocket* congested." So
moving to imbalance prices buys back the *temporal* resolution the project needs and buys
back **none** of the *spatial* resolution. For a scarcity/volatility signal it is the right
series; for a congestion signal it is still the wrong object.

---

## 5. Scarcity pricing and tail behaviour

### 5.1 There is no general European ORDC

PJM's and ERCOT's ORDC/reserve-shortage adders mechanically inject a large price adder into
the energy price when reserves fall below thresholds, producing the sharp spikes the
proposal's phase-transition story leans on (proposal ref. [10], PJM reserve-shortage pricing
paper). Europe has no equivalent as a general feature.

What actually exists:

- **Reg. (EU) 2019/943 Art. 20(3)** contemplates a **"shortage pricing function"** as
  something individual TSOs **may** implement. It is permissive, not mandatory, and the
  all-TSO balancing-energy pricing methodology under EBGL Art. 30(1) is explicitly stated to
  be "without prejudice to the introduction of a shortage pricing function ... referred [to]
  in Article 20(3) of Regulation (EU) 2019/943."
- **Belgium is the notable adopter**: Elia has computed ORDC scarcity prices since **October
  2019**, with dynamic reserve dimensioning launched **February 2020**.
- The academic assessment (Papavasiliou, Smeers, de Maere d'Aertrycke and related work) is
  that a **real-time market for reserve capacity — the thing ORDC prices — does not currently
  exist in Europe**, which is why scarcity pricing has not generalised.

Do **not** describe a European ORDC as though it were a market-wide institution. It is a
Belgian computation plus an optional legal hook.

### 5.2 What bounds the upper tail instead: administrative caps

- **ACER Decision 01/2023** sets the harmonised maximum clearing price (HMMCP) methodology
  for SDAC, with a reference **maximum of +4,000 EUR/MWh**.
- Adjustment mechanism: the maximum rises by **+1,000 EUR/MWh** if the clearing price exceeds
  **60%** of the current maximum in at least one market time unit in a day in one or more
  bidding zones.
- History worth knowing: 4,000 EUR/MWh was reached on **16 August 2022** (delivery 17 August)
  in Lithuania, Latvia and Estonia; the automatic escalation to 5,000 EUR/MWh announced for
  20 September 2022 was **suspended** following the extraordinary TTE Energy Council of
  9 September 2022, and the cap remained at 4,000.

So the European upper tail is **administratively truncated**, and the escalator has been
politically overridden at least once.

### 5.3 Do European prices have comparable heavy tails? No — the fat tail is on the other side

German day-ahead, 2025 ([FfE](https://www.ffe.de/en/publications/german-electricity-prices-on-the-epex-spot-exchange-in-2025/)):

- Base **€89.3/MWh** (up ~16% on 2024); peak €92.3; off-peak €87.7
- **Annual maximum ≈ €583/MWh** (20 January 2025) — i.e. **~15% of the 4,000 cap**
- **Annual minimum ≈ −€250/MWh** (11 May 2025)
- **≈575 hours of negative prices** in 2025, versus 459 in 2024, 301 in 2023, 69 in 2022

Negative-price shares: **0.8% (2022) → 3% (2023) → 5% (2024) → ~6.6% (2025)** of hours in
Germany, and this is now a *continent-wide* phenomenon. By end-October 2025, negative-price
hour counts ran approximately: **SE2 593, NL 584, DE 576, ES 569, BE 519, FR 513** (secondary
source — see § Not verified; the DE figure is quoted variously as 573/575/576 across
trackers, consistent to within a few hours).

**Implication for the project's tail machinery.** The GPD/extreme-value apparatus will run
mechanically on European prices, but what it is fitting is different:

- The **upper** tail is **right-censored** at an administrative cap that is not a scarcity
  price — fitting a GPD to it estimates a truncation artefact as much as a physical regime.
- The interesting European tail is the **negative** one, and it is a **renewable-surplus**
  phenomenon (must-run/subsidised infeed against inelastic demand), not a
  scarcity-or-congestion phenomenon.
- The "self-organised criticality / phase transition into a chaotic heavy-tailed pricing
  regime" framing (proposal ref. [8]) has no European empirical footing at the top of the
  distribution. A German maximum of €583/MWh is not the same object as a PJM or ERCOT
  scarcity print.

---

## 6. What survives the translation — full assessment

The project has three separable layers. They fare very differently.

### 6.1 Does NOT transfer

**(a) The nodal congestion-component decomposition. Terminal.**
LMP = energy + congestion + loss has no European counterpart. There is no intra-zonal shadow
price because EUPHEMIA solves no intra-zonal network. Do **not** attempt to synthesise a
congestion component from zone-price spreads: a DE-LU/DK1 spread describes that border, not a
pocket inside Germany. Any such construction would be a different quantity wearing the same
name, and a referee who knows European market design will say so.

**(b) The constrained-pocket research design. Terminal.**
The finest locational granularity in the EU day-ahead market is Italy's 7 zones and Norway's
5 — regions of millions of people. Germany, which is where the congestion and much of the
data-centre growth are, is **one zone**, and its government has just formally refused to split
it (§ 3.3). There is nowhere in Europe to run the NOVA design.

**(c) The ORDC/reserve-shortage scarcity mechanism.**
No general European analogue (§ 5.1). The proposal's threshold story is anchored to a PJM
institution that Europe does not have.

**(d) Any claim about US-comparable heavy upper tails.**
€583/MWh annual max under a 4,000 cap (§ 5.3). Different distribution, different generating
mechanism, capped.

### 6.2 Transfers essentially unchanged

**(a) The Stage-1 horse race.** This is *already* a zonal specification — the same regression
already run eight times. Sources: ENTSO-E Transparency Platform Art. 6.1.A actual total load
per bidding zone, and day-ahead prices per bidding zone. Load resolution is **15-minute for
AT, BE, CZ, DE, HU, NL**, 30-minute for GB/CY/IE, hourly for most others. API access needs a
token (request via transparency@entsoe.eu) and is rate-limited (~60 requests/60 s).

**Read "transfers unchanged" narrowly: it transfers the specification, including the
specification's defects.** In particular, the day-ahead timing problem in § 4.2 applies in
full — a European day-ahead price is set 12–36 h before delivery and cannot respond to a
contemporaneous load ramp. And because European day-ahead is the liquid, well-populated
series while the real-time signal sits in imbalance/balancing data, the temptation to use it
is stronger here than it was in the US panels. **This criticism also lands backwards, on any
existing panel in the eight-market sweep built from day-ahead rather than real-time prices** —
it is not a Europe-specific objection.

Three further caveats before treating this as a drop-in:
1. **Mid-panel resolution break**: day-ahead MTU changed 60-min → 15-min at delivery day
   1 Oct 2025 (§ 1.1). Not an endpoint effect.
2. **Data quality is materially worse than PJM/EIA-grade.** Hirth, Mühlenpfordt & Bulkeley
   (2018, *Applied Energy* 225: 1054–1067) find "deviations in the double-digit percentage
   range are not uncommon" between Transparency Platform series and other sources, varying by
   country — Austrian load on the TP is reported ~20% *smaller* than other sources. Any
   European panel needs a cross-source reconciliation step the US panels did not.
3. **Aggregation dilution** (§ 1.4): zonal load aggregates are larger, so |gradient| is a
   noisier proxy for localised events.

**(b) The GPD/tail code runs**, but see § 5.3 for why the estimand changes.

### 6.3 The strategic point, which matters more than either list

**Adding European zones to the sweep is more of the finding you already have, not a test of
the hypothesis you started with.**

The sweep has returned **level beats |gradient| in 11 of 11 panels**, range 91.7–100%,
*including ISO-NE at 64/64* — the market deliberately chosen as a low-data-centre control.
The project's own conclusion from that was that this looks like "a property of how power
systems price load, not a signature of data-centre growth." A twelfth and thirteenth zonal
panel from Europe will, on that evidence, return the same result. Marginal value ≈ 0.

If European zones are added anyway, **choose them adversarially, not conveniently** — pick
zones that could plausibly break the regularity:

- **Zones where load is growing.** Most existing panels have flat or falling load (NYISO
  −0.20%/yr, IESO −0.44%/yr, ISO-NE −0.59%/yr). A growing zone is a different regime.
- **Zones with high renewable share and rising *raw* |gradient|** — the VT/ME analogue that
  produced the only genuine volatility increase in the existing panel. Candidates: SE1/SE2,
  DK1, IE.
- **Zones with a real data-centre concentration**: Ireland (SEM) and DE-LU.

**Ireland is the best single candidate** — a small, wind-dominated system with a genuine
data-centre load concentration, a 5-minute imbalance pricing period, and published
constraint/Dispatch Balancing Costs. But note the irony: SEM is a **single bidding zone for
the whole island**, which is precisely why it cannot answer the locational question either.

### 6.4 The closest valid European research question

**Swap the dependent variable, not the market.**

The European object that corresponds to PJM's congestion component is **redispatch**, and it
*is* published — per market time unit, identifying "the location and type of network elements
concerned," within one hour of the operating period (Reg. 543/2013 Art. 13, § 2.2), plus
Germany's national netztransparenz.de platform and BNetzA/SMARD cost reporting. In one
respect this is a **better** congestion instrument than a nodal price: it names the
constrained element directly instead of implying it through a shadow price.

**Data feasibility — verified.** netztransparenz.de publishes a per-measure redispatch CSV
("Format 5") with these columns:

`BEGINN_DATUM, BEGINN_UHRZEIT, ZEITZONE_VON, ENDE_DATUM, ENDE_UHRZEIT, ZEITZONE_BIS,
GRUND_DER_MASSNAHME, RICHTUNG, MITTLERE_LEISTUNG_MW, MAXIMALE_LEISTUNG_MW,
GESAMTE_ARBEIT_MWH, ANWEISENDER_UENB, ANFORDERNDER_UENB, BETROFFENE_ANLAGE,
PRIMAERENERGIEART`

That is: start and end timestamps with time zone, reason for the measure, direction, mean and
maximum MW, total energy (MWh), instructing TSO, requesting TSO, affected facility, and
primary energy type. Available as CSV download with a date-range picker, a **2013–2020
archive ZIP**, and a documented **WebAPI** (documentation v1.14, 7 Feb 2025). So the design
in this section is **buildable**, with roughly a decade of depth.

Three data-engineering facts that follow, and that change the specification:

- **It is an event log, not a fixed-resolution time series.** Measures have arbitrary start
  and end times. Converting to a 15-minute MTU grid (overlap-weighting each measure onto the
  grid) is a required preprocessing step, not a resample.
- **`BETROFFENE_ANLAGE` is the affected *generating facility*, not the constrained network
  element.** The named-network-element field is the Art. 13 Transparency Platform obligation,
  not this file. If the constrained element is wanted, it has to come from the TP feed, and TP
  data quality caveats (§ 6.2) apply. Do not conflate the two sources.
- **Cross-border measures are only partially published**: for cross-border redispatch and
  countertrading, only the portion relating to facilities or exchange trading inside Germany
  appears. Any cross-border measure is therefore left-censored in volume.

So the defensible European question is:

> **Does zonal load level, or zonal load volatility, predict redispatch volume and cost in
> the German–Luxembourg bidding zone at market-time-unit resolution, conditional on wind and
> solar infeed?**

Four caveats, all of which must be stated up front rather than discovered later:

1. **The shock is on the wrong side.** German redispatch is dominated by a **north-to-south
   renewable transport** problem: too much wind in the north, load and retired nuclear in the
   south, insufficient internal transfer capacity until the HVDC corridors land (§ 3.3). The
   first-order driver is *where the wind is blowing*, not how fast load is ramping. A
   load-volatility regressor will be swamped by wind unless wind is controlled for — and even
   then the residual load-attributable variation may be small. This is the **opposite
   orientation** to the NOVA hypothesis, where the shock is demand-side.
2. **Redispatch cost is an administrative number, not a market-clearing price.** Germany uses
   cost-based redispatch remuneration. The series responds to TSO procedure and regulatory
   change, so **structural breaks in it are regulatory, not physical** — a hazard the project
   has already been bitten by elsewhere. (The Redispatch 2.0 regime change, which brought
   DSO-connected and renewable units into the redispatch framework, is the obvious break to
   check; its exact effective date is **not verified** here.)
3. **It answers a different question.** "Did the grid have to intervene, and how much did it
   cost?" is not "did prices spike." The GPD/phase-transition framing does **not** carry
   over. The natural specification is a volume/cost model with a mass at zero (hurdle or
   Tobit), not extreme-value theory on prices.
4. **It is a different paper.** It shares a regressor with the NOVA work and essentially
   nothing else — different market, different mechanism, different dependent variable,
   different causal story. Framing it as "extending the NOVA result to Europe" would be
   overclaiming.

### 6.5 Recommendation, stated plainly

- If the goal is **more panels for the existing cross-market regularity**: Europe is cheap
  and adds close to nothing, because the regularity already held in the control market. Do it
  only as a robustness appendix, and only with adversarially chosen zones (§ 6.3).
- If the goal is **to rescue the original congestion hypothesis**: Europe is the only place in
  the developed world where the congestion *response* is published as a physical quantity
  tied to a named network element. That is genuinely attractive. But the question that data
  can actually answer is a German wind-transport question, not a data-centre-volatility
  question, and it is a new project rather than an extension.
- Given that the project's own control market already argues against a data-centre-specific
  reading of the result, and that the sub-question-1 report does not yet exist in the repo,
  the honest ordering is: **write the report, then decide about Europe.** Europe is not a
  rescue for the volatility premise; it is a second paper competing for the same weeks.

---

## Sources

**EU law / regulation**
- Regulation (EU) No 543/2013 (transparency), Art. 12 (congestion income) and Art. 13
  (congestion management measures) — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013R0543
- Regulation (EU) 2019/943 (internal electricity market), Art. 10 (technical bidding limits),
  Art. 14 (bidding zone review), Art. 15 (action plans), Art. 16(8) (70% MACZT), Art. 20(3)
  (shortage pricing function) — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32019R0943
- Commission Regulation (EU) 2017/2195 (EBGL), Art. 52(2)(c) single imbalance price, Art.
  53(1) 15-min ISP — https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32017R2195

**Regulators / TSOs**
- BMWE, *Bidding Zone Action Plan – pursuant to Art. 15 of Regulation (EU) 2019/943* (PDF
  created Dec 2025) — read directly, pp. 1–8 —
  https://www.bundeswirtschaftsministerium.de/Redaktion/EN/Publikationen/Energie/action-plan-germanys-bidding-zone-2025.pdf
- ACER, *Transmission capacities for cross-zonal electricity trade and grid congestion
  management* (2025 monitoring report, published 5 Sept 2025) —
  https://www.acer.europa.eu/monitoring/cross-zonal-electricity-trade-2025
- ACER news, "Electricity system operators' bidding zone study significantly underestimates
  the benefits of reshaping Europe's bidding zones" (Opinion, 18 Sept 2025) —
  https://www.acer.europa.eu/news/electricity-system-operators-bidding-zone-study-significantly-underestimates-benefits-reshaping-europes-bidding-zones
- ACER, Congestion Revenues — https://www.acer.europa.eu/electricity/infrastructure/congestion-revenues
- ACER Decision 11/2022 on alternative bidding zone configurations, Annex I —
  https://www.acer.europa.eu/Individual%20Decisions_annex/ACER%20Decision%2011-2022%20on%20alternative%20BZ%20configurations%20-%20Annex%20I.pdf
  *(could not parse the PDF; cited for the decision's existence and subject only)*
- ACER Decision 01/2023 on HMMCP for SDAC —
  https://www.acer.europa.eu/sites/default/files/documents/Individual%20Decisions/ACER%20Decision%2001-2023%20on%20HMMCP%20SDAC.pdf
- ENTSO-E, Bidding Zone Review landing page — https://www.entsoe.eu/network_codes/bzr/
- ENTSO-E, *Bidding Zone Review of the 2025 Target Year* (28 Apr 2025) —
  https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Network%20codes%20documents/NC%20CACM/BZR/2025/Bidding_Zone_Review_of_the_2025_Target_Year.pdf
- ENTSO-E, SDAC implementation — https://www.entsoe.eu/network_codes/cacm/implementation/sdac/
- ENTSO-E, PICASSO — https://www.entsoe.eu/network_codes/eb/picasso/ ; Imbalance Netting —
  https://www.entsoe.eu/network_codes/eb/imbalance-netting/
- ENTSO-E Transparency Platform, Redispatching data view —
  https://transparency.entsoe.eu/content/static_content/Static%20content/knowledge%20base/data-views/congestion-management/Data-view%20Redispatching.html
  *(page returned HTTP 400 to my fetch tooling; Art. 13 content cited from EUR-Lex instead)*
- ENTSO-E Transparency Platform, Actual Total Load & Day-ahead per Bidding Zone [6.1.A]/[6.1.B] —
  https://transparencyplatform.zendesk.com/hc/en-us/articles/16647979768084-Actual-Total-Load-Day-ahead-Per-Bidding-Zone-6-1-A-6-1-B
- SMARD (BNetzA), "Netzengpassmanagement in Q3/2025 – Volumen und Kosten gestiegen" —
  https://www.smard.de/page/home/topic-article/444/219200/volumen-und-kosten-gestiegen
- SMARD (BNetzA), "Volumen und Kosten gesunken" —
  https://www.smard.de/page/home/topic-article/444/216636/volumen-und-kosten-gestiegen
- netztransparenz.de (joint German TSO redispatch publication platform; obligation per BNetzA
  ruling BK6-11-098, 30 Oct 2012) —
  https://www.netztransparenz.de/de-de/Systemdienstleistungen/Betriebsfuehrung/Redispatch
  (English: https://www.netztransparenz.de/en/Ancillary-Services/System-operations/Redispatch)
- netztransparenz.de WebAPI documentation v1.14 (7 Feb 2025) — redispatch "Format 5" column
  schema —
  https://www.netztransparenz.de/xspproxy/api/staticfiles/ntp-relaunch/dokumente/web-api/dokumentation-webserviceapi-netztransparenz_v1.14.pdf
- Redispatch dataset listing, EU Open Data Portal —
  https://data.europa.eu/data/datasets/b7f14d52-222b-4105-98a8-c79c1442bfdc
- EirGrid/SONI, *Balancing Market Principles Statement* —
  https://cms.eirgrid.ie/sites/default/files/publications/EirGrid-and-SONI-Balancing-Market-Principles-Statement-V8.0.pdf
- SEM Committee, *Imperfections Charges Decision Paper* SEM-25-053 —
  https://www.semcommittee.com/files/semcommittee/2025-09/SEM-25-053_2025_26%20Imperfections%20Charges%20Decision%20Paper.pdf

**Exchanges / market operators**
- EPEX SPOT, "Successful Implementation of 15-Minute Market Time Unit (MTU) in SDAC" —
  https://www.epexspot.com/en/news/successful-implementation-15-minute-market-time-unit-mtu-sdac
- EPEX SPOT, MCSC confirmation of 15-min MTU go-live (30 Sept 2025 trading / 1 Oct 2025
  delivery) —
  https://www.epexspot.com/en/news/market-coupling-steering-committee-confirms-go-live-15-minute-mtu-sdac-trading-day-30
- NEMO Committee, SDAC 15-min MTU information paper —
  https://www.nemo-committee.eu/assets/files/sdac-15-minute-mtu-information-paper.pdf
- Nord Pool, Bidding areas — https://www.nordpoolgroup.com/en/the-power-market/Bidding-areas/
- GME, *Vademecum to the Italian Power Exchange* —
  https://www.mercatoelettrico.org/portals/0/Documents/en-US/20260131VademecumBorsaElettrica_En.pdf
- EXAA / Nord Pool operational messages on the 4,000 EUR/MWh HMMCP (Sept 2022) —
  https://www.exaa.at/en/about-exaa/exaa-news/no-changes-in-harmonised-maximum-clearing-price-for-sdac-from-20-september-it-remains-at-4-000-eur-mwh/

**Academic / analytical**
- L. Hirth, J. Mühlenpfordt, M. Bulkeley, "The ENTSO-E Transparency Platform – A review of
  Europe's most ambitious electricity data platform," *Applied Energy* 225 (2018) 1054–1067 —
  https://www.sciencedirect.com/science/article/pii/S0306261918306068
  (open copy: https://neon.energy/Hirth-Muehlenpfordt-Bulkeley-2018-ENTSO-E-Transparency-Platform.pdf)
- A. Papavasiliou, Y. Smeers, G. de Maere d'Aertrycke, "Market Design Considerations for
  Scarcity Pricing: A Stochastic Equilibrium Framework," *The Energy Journal* 42(5), 2021 —
  https://journals.sagepub.com/doi/abs/10.5547/01956574.42.5.apap
- A. Papavasiliou, Y. Smeers, "Scarcity pricing and the missing European market for real-time
  reserve capacity," *The Electricity Journal* (2020) —
  https://www.sciencedirect.com/science/article/pii/S104061902030155X
- Elia, *Preliminary report on Elia's findings regarding the design of a scarcity pricing
  mechanism* (2020) —
  https://www.elia.be/-/media/project/elia/elia-site/public-consultations/2020/20200930_elia_preliminary-report-scarcity-pricing_en.pdf
- JRC, *Future-proofing the European power market: redispatch and congestion management*,
  JRC137685 — https://publications.jrc.ec.europa.eu/repository/bitstream/JRC137685/JRC137685_01.pdf
  *(PDF would not parse for me; listed as a lead, no figure cited from it)*
- "Real-Time Imbalance Pricing in I-SEM – Ireland's Balancing Market," NPSC 2018 —
  https://www.iitk.ac.in/npsc/Papers/NPSC2018/1570475323.pdf

**Market data / trade analysis (secondary, used only where flagged)**
- FfE, "German electricity prices on the EPEX Spot exchange in 2025" —
  https://www.ffe.de/en/publications/german-electricity-prices-on-the-epex-spot-exchange-in-2025/
- FfE, "German electricity prices on EPEX Spot 2024" —
  https://www.ffe.de/en/publications/german-electricity-prices-on-epex-spot-2024/
- pv magazine, "Europe faces surge in negative power prices as solar output grows"
  (3 Nov 2025) — https://www.pv-magazine.com/2025/11/03/europe-faces-surge-in-negative-power-prices-as-solar-output-grows/
- IWR, "Netzengpassmanagement 2025: Stromnetz stabil, Kosten leicht gestiegen…" —
  https://www.iwr.de/news/netzengpassmanagement-2025-stromnetz-stabil-kosten-leicht-gestiegen-bei-hohem-ausbau-erneuerbarer-energien-news39599

---

## Not verified

Items below are **not** primary-source-confirmed. Do not put any of them in a paper without a
second pass.

1. **Total number of European bidding zones.** Secondary sources disagree (≈30 vs. ≈41),
   likely differing on whether non-EU / ENTSO-E observer areas count. The per-country counts
   in § 1.2 (NO 5, SE 4, DK 2, IT 7 geographical, DE-LU 1) are well corroborated; the grand
   total is not. Pull it from the ENTSO-E bidding zone configuration technical report if the
   number is needed.
2. **Italy's 7 geographical zones from a primary source.** GME's own zone document would not
   parse for my tooling. The 7-zone list (NORD, CNOR, CSUD, SUD, CALA, SICI, SARD) and the
   1 Jan 2021 addition of CALA under ARERA Decision 103/2019/R/eel are cross-corroborated
   across several secondary sources but not read out of the GME/Terna/ARERA original.
3. **ACER Decision 11/2022 contents.** The Annex I PDF would not parse. Cited only for the
   decision's existence, date (August 2022) and subject matter. Decision numbering appears in
   ACER's own file path; a secondary source dates it 8 August 2022. Verify before citing a
   decision number and date together.
4. **Any bidding-zone-review development after December 2025.** Germany's Art. 15 action plan
   (Dec 2025) is the latest primary document retrieved. Whether the European Commission has
   since acted under Art. 14, and what the current formal status is as of August 2026, is
   **unknown to this note**. Do not assert a 2026 outcome.
5. **German 2024 congestion-management cost.** Two figures circulate: **€2.776 bn**
   (preliminary) and **€2.954 bn** (the 2024 baseline used in the 2025 comparison). The 2025
   figure of **€3.071 bn** and the "+4%" are consistent with the €2.954 bn baseline. Pull
   BNetzA's own final annual figure and state which vintage is used.
6. **netztransparenz.de redispatch file schema — RESOLVED, see § 6.4.** The per-measure CSV
   schema (start/end timestamps, direction, mean/max MW, total MWh, requesting and
   instructing TSO, affected facility, primary energy type), the 2013–2020 archive, and the
   WebAPI are confirmed. Residual: I read the schema from the platform's own page and API
   documentation rather than by downloading and parsing an actual file, so **column names and
   the exact history depth of the live (post-2020) feed should be confirmed against a real
   download** before building on them.
7. **Redispatch 2.0 effective date** and its exact scope change (DSO-connected units,
   renewables entering the redispatch regime). Named in § 6.4 as the structural break to
   check; the date is from background knowledge, not a source read here.
8. **Country-by-country negative-price hour counts for 2025** (SE2 593, NL 584, DE 576,
   ES 569, BE 519, FR 513, "by end of October"). Secondary/trade-press aggregation. The
   German full-year figure (~575, FfE) and the 2022–2024 series (69/301/459) are from FfE and
   are stronger. The DE 2025 count varies 573–576 across trackers.
9. **German bidding-zone load magnitude vs. DOM zone load magnitude** (the "aggregation
   dilution" point in § 1.4 and § 6.2). The direction is certain — the German zone is much
   larger — but no ratio is asserted because neither figure was pulled.
10. **Ireland's imbalance settlement period** is stated as a 5-minute pricing period over a
    30-minute settlement period, from a 2018 conference paper on I-SEM. Whether SEM now
    operates a 15-minute ISP under EBGL Art. 53(1), or holds a derogation, is **not
    verified**. Check SEMO/SEM Committee before relying on the resolution.
11. **Ireland data-centre share of demand.** Frequently quoted, but I did not retrieve a CSO
    or CRU primary figure in this pass. Get it from CSO/CRU directly if Ireland becomes the
    target.
12. **PICASSO/MARI accession dates** for individual TSOs (TenneT NL Dec 2025, PSE Sept 2026,
    RTE delayed, Nordic mFRR 4 Mar 2025) come from ENTSO-E accession-roadmap documents via
    search summaries, not from a roadmap PDF read directly. Roadmap dates slip routinely.
13. **JRC137685** redispatch report — listed as a lead only; the PDF would not parse and no
    figure from it is used here.
