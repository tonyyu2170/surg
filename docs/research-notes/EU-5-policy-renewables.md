# EU-5: European Policy, Renewables, and the Volatility Question

Research date: 2026-08-11. Desk research only — no data pulled, no acquisition module written.

Scope: the six questions in the EU-5 brief. Gated item #4 in
`docs/plans/advisor/2026-08-11-post-meeting-prioritization.md`, run after the ISO-NE
diurnal fingerprint test (`docs/plans/2026-08-11-isone-der-fingerprint-prereg.md`)
returned **UNINFORMATIVE**.

Source discipline used here: figures marked **[PRIMARY]** were extracted from the
issuing body's own PDF or page, read directly in this session. Figures marked
**[SECONDARY]** come from trade press or law-firm briefings and were not
confirmed against the underlying document. Anything I could not pin down is in
the **Not verified** section at the bottom rather than being estimated.

---

## 0. Headline assessment — the advisor's hypothesis

The advisor's hypothesis was: *"Since Europeans rely more on renewables, there
will be more fluctuation."*

**Verdict: half right, and the half that is right is not the half this project
measures.**

The hypothesis silently merges two different quantities:

| | Is the hypothesis supported? |
|---|---|
| **Price** volatility | **Yes, strongly** — but the driver is renewables *interacting with a shortage of flexibility*, not renewable share on its own. And the effect is asymmetric, not symmetric "more fluctuation". |
| **Metered load** volatility | **Not established, and renewable share is the wrong regressor.** The only renewable that mechanically enters metered load is *behind-the-meter* generation. Transmission-connected wind and utility-scale solar sit on the far side of the meter and cannot move the load series at all. |

The second row is what this project measures, and it is where the hypothesis
breaks down. Denmark gets 71% of its electricity from wind and solar — the
highest in Europe — but that is overwhelmingly **transmission-connected wind**.
It is on the generation side of the settlement boundary. It changes prices
enormously and changes metered zonal load essentially not at all.

### The finding that actually matters for the research design

This is the payoff of the European extension, and it is worth more than the
Ireland pull that motivated the question.

The ISO-NE panel failed to discriminate because everything was collinear:
`docs/plans/2026-08-11-isone-der-fingerprint-prereg.md` records that zone size,
rural-ness, distributed-solar share and renewable share are mutually collinear
across n = 8, so ρ = −0.786 against zone MW is "equally consistent with every one
of them. Nothing in this panel separates them."

**In Europe, those two variables come apart.** Total VRE share and *solar* share
are not collinear across European countries — and solar is the resource that
carries the behind-the-meter mass:

| Country | wind+solar % of generation, 2025 | **solar %, 2025** | wind-dominated? |
|---|---|---|---|
| Denmark | **71.1** (highest in Europe) | 13.4 | yes |
| **Netherlands** | 46.1 | **21.1** | no — solar-heavy |
| Germany | 45.1 | 17.9 | mixed |
| **Ireland** | **42.8** | **4.7** | **yes, strongly** |
| Spain | 42.3 | 21.8 | no |
| Finland | 28.6 | 1.2 | yes |
| Sweden | 25.4 | 2.6 | yes |
| France | 13.7 | 5.6 | neither (nuclear) |

All figures [PRIMARY — Ember/OWID data files downloaded this session].

**The cleanest matched pair in Europe is Ireland vs the Netherlands.**

| | Ireland | Netherlands |
|---|---|---|
| wind + solar share | 42.8% | 46.1% | 
| **solar share** | **4.7%** | **21.1%** |

Nearly identical total VRE share; solar share differs by a factor of **4.5**. That
is very close to a controlled comparison on exactly the axis H_solar names, and it
is not available anywhere in the North American panel.

So the correct European version of the question is **not** "does Ireland, a
high-renewables market, show more load fluctuation?" It is:

> Does metered load volatility track **distributed solar share**, holding total
> VRE share roughly fixed (NL vs IE), rather than tracking **VRE share**?

If NL shows rising metered-load volatility and IE does not — at the same total VRE
share — H_solar survives a test ISO-NE could not run. If both rise, or neither
does, the metering-artifact mechanism is in trouble. Either way it is informative,
which the diurnal fingerprint test was not.

**This also rescues the Ireland pull the researcher already wanted.** Ireland is
not a treatment case for the volatility question — it is the *control*, and a good
one. It is worth pulling for that reason as much as for the policy material in
§4–§5.

**Two corrections to my own first draft, kept visible because they matter:**

- I initially wrote Denmark as the low-BTM control on the assumption that
  "wind-dominated" implied negligible solar. **That was wrong** — Denmark's solar
  share is 13.4%, roughly Belgium's (14.3%) and well above Ireland's. Denmark is
  fourth-ish in Europe on solar per capita. Do not use Denmark as a low-solar
  control.
- **Solar share of generation is a proxy, not the regressor.** The quantity the
  mechanism actually names is the **rooftop / small-scale share of installed PV
  capacity**, since utility-scale PV sits on the far side of the meter and is as
  irrelevant to metered load as Danish wind is. I did **not** obtain country-level
  rooftop-vs-utility splits — see Not-verified §13. Ireland's 4.7% total solar
  share makes it a safe control regardless of split (there is little solar of any
  kind), but the Netherlands' status as the high-BTM case rests on the per-capita
  and household figures in §3, which are secondary.

### Three honest complications

1. **France breaks the naive correlation.** France has the lowest VRE share of
   the major markets here (13.7%) and still logged ~513 negative-price hours by
   end-October 2025 [SECONDARY] — comparable to Germany's 576 over the same
   window, at a third of the VRE share. Inflexible must-run nuclear plus low
   demand produces negative prices without much wind or solar. Renewable share is
   not sufficient *or* necessary for negative prices.
2. **ACER's own framing is conditional, not direct.** ACER writes: *"Without
   sufficient flexibility, weather variability directly translates into price
   volatility"* [PRIMARY]. The causal object is the interaction term. A
   high-renewables system with deep storage, interconnection and demand response
   is not predicted to be volatile.
3. **The direction is asymmetric.** ACER finds *"countries with more
   negative-price hours generally experienced fewer extreme price spikes above
   150 EUR/MWh"* [PRIMARY]. High-VRE countries get more *downside* excursions and
   *fewer* upside ones. "More fluctuation" as a symmetric statement is wrong; the
   distribution is being reshaped, not simply widened. This matters for a project
   whose method is EVT/GPD tail characterisation — the two tails are moving in
   opposite directions.

---

## 1. Renewable penetration by country

Source: Ember, via the Our World in Data mirror, downloaded as CSV this session
(`share-of-electricity-production-from-solar-and-wind`, `share-electricity-solar`).
Most recent full year = **2025**. Figures are **wind + solar as a share of
domestic electricity generation**. [PRIMARY — Ember data file]

### European ranking, 2025 (wind + solar % of generation)

| Rank | Country | wind+solar % | solar % |
|---|---|---|---|
| 1 | Denmark | **71.05** | 13.36 |
| 2 | Lithuania | 63.67 | 18.79 |
| 3 | Luxembourg | 61.04 | 30.52 |
| 4 | Netherlands | 46.09 | 21.12 |
| 5 | Germany | 45.09 | 17.91 |
| 6 | Portugal | 44.06 | 17.33 |
| 7 | Ireland | 42.75 | **4.75** |
| 8 | Greece | 42.61 | 22.17 |
| 9 | Spain | 42.26 | 21.85 |
| 10 | Estonia | 37.32 | 18.49 |
| 11 | United Kingdom | 35.98 | — |
| 12 | Belgium | 33.16 | 14.34 |
| — | **EU-27** | **30.25** | 13 (Ember) |
| 13 | Croatia | 30.20 | — |
| 14 | Hungary | 28.78 | 27.29 |
| 15 | Finland | 28.63 | 1.19 |
| 16 | Cyprus | 26.73 | 23.18 |
| 17 | Poland | 25.49 | — |
| 18 | Austria | 25.43 | — |
| 19 | Sweden | 25.38 | 2.60 |
| 20 | Italy | 24.98 | 16.86 |
| — | France | 13.74 | 5.58 |
| — | Switzerland | 12.35 | — |
| — | Norway | 8.76 | — |
| — | Czechia | 6.57 | — |
| — | Slovakia | 2.41 | — |

**Two caveats that matter before quoting these.**

- These are shares of **domestic generation**, not of consumption. Luxembourg
  (61%) and Lithuania (63.7%) are inflated by this: both have small domestic
  generation fleets and import a large share of what they consume. Do not put
  Luxembourg second in Europe in a write-up without saying this. Denmark's 71% is
  not an artifact of the same kind — Denmark genuinely generates that much — but
  Denmark is also a heavy net trader with Norway/Sweden/Germany.
- Solar share and wind+solar share are from different Ember series; where I show
  a dash, I did not extract the country from the solar file and have not
  estimated it.

### EU-level context, 2025 [SECONDARY — Ember European Electricity Review 2026]

- Wind and solar reached **30% of EU electricity**, exceeding fossil (**29%**)
  for the first time on record; up from 20% five years earlier.
- Solar: **369 TWh, 13% of EU electricity**, fourth consecutive year of >20%
  growth; solar exceeded both coal and hydro.
- Wind: **17%** of EU power, second-largest source, above gas.
- Wind and solar out-generated fossil fuels in **14 of 27** EU countries.
- Wind and solar supplied **more than half of generation in at least a third of
  all hours** in Denmark, Estonia, Germany, Greece, Lithuania, Luxembourg,
  Netherlands, Portugal and Spain.

### Comparison with US markets

| Market | wind + solar share | Basis |
|---|---|---|
| **United States (national)** | **17%** utility-scale, **19%** including small-scale solar, 2025 | EIA [SECONDARY] |
| US national (Ember series) | 18.88%, 2025 | Ember/OWID [PRIMARY] |
| **ERCOT** | **36%** of demand, **first nine months of 2025** | EIA [SECONDARY] |
| SPP | **not verified** — see Not-verified §1 | |
| CAISO | **not verified** — see Not-verified §1 | |

**The comparison that should go in the write-up:** the EU-27 average (30.3%) is
already above the US national figure (~19%) and roughly at ERCOT's level. But the
*top* of the European distribution is far above anything in the US — Denmark at
71% has no US analogue at ISO scale. Meanwhile France, Czechia, Slovakia and
Norway sit far below the US average. **European VRE penetration is much more
dispersed across countries than US VRE penetration is across ISOs**, which is
precisely what makes Europe a better cross-sectional panel than the eight North
American markets already completed — more spread in the regressor.

---

## 2. Does high renewable share produce more PRICE volatility?

**Short answer: yes, and this part of the advisor's hypothesis is well
supported by regulator-grade evidence — with the three qualifications in §0.**

### The strongest single citation [PRIMARY — ACER 2026 Monitoring Report]

ACER, *Key developments in EU electricity and gas markets — 2026 Monitoring
Report*. Read directly from the ACER PDF this session.

- Verbatim: *"The average electricity price difference has grown five times
  compared to the 2020 value."* The metric is the **yearly average of the daily
  minimum-to-maximum day-ahead price spread, averaged across EU-27/EEA(Norway)
  bidding zones**, from the chart *"Yearly average difference of minimum and
  maximum day-ahead prices across bidding zones, EU-27/EEA (Norway), 2020–2025
  (EUR/MWh)"*.

  **Quote the sentence, not a computed 2025 level.** The bar labels I recovered
  from the PDF text layer are 28.3 / 68.3 / 167.6 / 85.9 / 96.8 / 109 against an
  x-axis of 2020–2025 (the chart note says *"2022 is excluded due to extreme price
  levels"*, so 167.6 is the annotated 2022 outlier). On the natural mapping,
  2020 = 28.3 and 2025 = 109 — a ratio of **3.9×, which does not reconcile with
  ACER's own "five times"**. Either the sentence refers to a different series
  (there is a second, similar chart later in the report) or my bar-to-year mapping
  is wrong; pdftotext does not preserve x-position. **Cite ACER's sentence and the
  2020 base of 28.3 EUR/MWh; do not assert a 2025 value.** See Not-verified §12.
- *"Rising solar penetration intensified the 'duck curve': more low and negative
  price hours during midday and sharper evening price peaks. The higher incidence
  of high-price hours reflects increased sensitivity to the evening decline in
  solar output and constraints in available system flexibility."*
- *"Average prices stabilised, but volatility increased: daily peak-valley
  spreads rose above 2023 levels, reflecting a system increasingly driven by
  variable resources and by insufficient flexibility during tight hours."*
- *"Europe cannot rely on intermittent renewables alone. Without sufficient
  flexibility, weather variability directly translates into price volatility."*
- Renewable generation share overall reached **around 50%** in 2025.
- ACER's worked example — **Germany, 1 May 2025**: day-ahead price fell to about
  **−130 EUR/MWh** at midday at peak solar, then rose to roughly **+164 EUR/MWh**
  in the evening — *"an exceptional swing of about 294 EUR/MWh during the day."*

This is the cleanest available demonstration of the duck-curve mechanism in
Europe and it is a regulator's own figure, not press.

### Negative prices — the numbers, with their vintages kept straight

Press reporting garbles year-to-date and full-year figures badly. Both circulate
as "2025".

**Germany, full calendar year, from the national regulator [PRIMARY —
Bundesnetzagentur, published 5 Jan 2026]:**

| Year | Negative-price hours | Total hours |
|---|---|---|
| 2023 | 301 | — |
| 2024 | 457 | 8,784 |
| **2025** | **573** | 8,760 |

Three consecutive record years. 2025 = 6.5% of all hours. Same release: 2025
German average day-ahead price **89.32 EUR/MWh**, up 13.8% on 2024's 78.51;
renewables **257.5 TWh / 58.8% of generation** (58.5% in 2024); solar **74.1 TWh**
(63.2 in 2024), the jump attributed to above-average sunshine; onshore wind
**106.5 TWh** (112.6 in 2024, i.e. *down*); offshore wind 26.1 TWh.

> Note the internal tension worth flagging: German wind generation **fell** in
> 2025 while negative hours hit a record. The record was driven by solar, which
> is the diurnally-concentrated resource — consistent with the duck-curve
> mechanism rather than with generic "renewables".

**Cross-country, year-to-date through end-October 2025 [SECONDARY — pv magazine,
3 Nov 2025, citing the Strommarkt-App tool]:**

| Zone | Negative hours (to end-Oct 2025) |
|---|---|
| Sweden SE2 | 593 |
| Netherlands | 584 |
| Germany | 576 |
| Spain | 569 |
| Belgium | 519 |
| France | 513 |
| Finland | >400 |
| Denmark (each of two zones) | >400 |
| CZ, PL, HU, CH, SI, SK, HR | ~300 each |

Italy is excluded — negative prices are prohibited there by market rule, which is
itself a caution about naive cross-country comparison. The same article
attributes October's negative hours mainly to **autumn storms (wind)**, not solar.

**Warning:** Germany's 576 in this table is a *ten-month* figure and the
Bundesnetzagentur full-year figure is 573. These are not reconcilable as stated
and at least one is measured on a different basis (likely bidding-zone or
product definition). Do not present the 593/584/576 table as full-year 2025. See
Not-verified §2.

### Where the hypothesis gets complicated

- **France.** 13.7% VRE, ~513 negative hours. Inflexible nuclear must-run and
  weak demand generate negative prices without high VRE. A cross-country
  regression of negative hours on VRE share would be badly specified without a
  flexibility/must-run control.
- **Italy.** Zero negative hours by regulation, at 25% VRE. Market design, not
  physics.
- **The 2021–2023 volatility episode was gas-driven.** European price volatility
  peaked during the gas crisis, when VRE shares were *lower* than today. ACER's
  2026 report notes gas price volatility in H2 2025 fell to its lowest since
  2021 even as electricity volatility rose. Any long time series that includes
  2022 will attribute variance to the wrong cause unless gas is controlled for.
- **Direction asymmetry.** Restating the ACER finding because it is easy to miss:
  more negative hours ↔ *fewer* spikes above 150 EUR/MWh. Both tails are moving,
  in opposite directions.

---

## 3. Does high renewable share produce more LOAD volatility in metered data?

**Short answer: this is not established for Europe, the mechanism is real and
well-documented in the engineering literature, and — critically — renewable share
is the wrong variable. The right one is behind-the-meter share.**

### The mechanism is not in dispute

The BTM-netting mechanism the researcher proposes is standard in the power-systems
literature, though it is usually framed as a *forecasting* problem rather than a
*measurement-artifact* problem:

- BTM PV is invisible to the system operator; it *"adds an unknown varying
  negative demand to the system"*, causing net-load volatility and forecast error.
- One quantified result from that literature: adding residential PV increased net
  load forecast error by **30% at household level and 250% at aggregate level**
  [SECONDARY — see Sources; I did not read the underlying paper].

Note what this literature is *not*: it is almost entirely US/Chinese, methods-
focused (disaggregation via ML), and aimed at improving forecasts. **I did not
find a published European study measuring the trend in metered net-load
volatility attributable to BTM PV growth.** That is a genuine gap and is
plausibly where this project's contribution lies. See Not-verified §3 — I am
flagging absence-of-evidence, not evidence-of-absence, since my search was
English-language and not exhaustive of German/Dutch-language TSO literature.

### Rooftop / BTM penetration in Europe — the Netherlands is the case

[SECONDARY throughout this subsection unless marked]

- **Netherlands ranks first in Europe for solar capacity per capita**, passing
  1,000 W/inhabitant in 2022 and reaching **~1,353 W/capita in 2024**. It
  overtook Germany in 2021.
- **~31.5% of Dutch homes — about 2.58 million installations — had rooftop solar
  by end-2023**, average system ~4.69 kW.
- 2023 additions: 4.82 GW total, of which **residential 2.55 GW** — i.e. rooftop
  was the majority of new capacity.
- Dutch solar share of generation **21.1% in 2025** [PRIMARY — Ember/OWID].

**Why the Netherlands is such an extreme case: net metering.** The Dutch
*salderingsregeling* let households offset consumption against export at full
retail value — one of Europe's most generous rooftop incentives, and the direct
cause of the per-capita lead. **It is scheduled to be abolished on 1 January
2027.** From that date suppliers set the export compensation.

This has a specific consequence for the research design: **the Netherlands has a
scheduled, dated, exogenous policy change to the economics of BTM solar.** If BTM
behaviour drives metered net-load volatility, 1 Jan 2027 changes the incentive to
self-consume and to install storage without changing underlying demand.

⚠️ **But it cannot be run now, and should be pitched as a follow-on, not as this
summer's analysis.** Today is 2026-08-11. **The post-treatment period does not yet
exist.** Any 2027 net-metering study is at minimum a 2027–28 project, and would
want a full post-year. Present it to the advisor as "here is a clean
identification strategy this project is positioned to run later," not as an
available design — otherwise it reads as something deliverable this term and it
is not.

The NL-vs-IE cross-section in §0, by contrast, **is** runnable on historical data
today.

### Ranking candidates for a BTM-intensity regressor

Best candidates, highest BTM intensity first: **Netherlands** (clear first), then
**Germany** and **Belgium**. **Ireland is the low-solar control** (4.75% solar
share). **Denmark is not a low-solar control** — 13.4%, see the correction in §0.
Hungary is interesting — 27.3% solar share, above Germany's 17.9% — and worth
checking for rooftop share, which I did not verify.

Caveat carried from §0: all of these are ranked on *solar share of generation*,
which is a proxy. The correct regressor is **rooftop / small-scale share of
installed PV capacity**, which I did not obtain per country (Not-verified §13).
EU-wide context only: rooftop was **66% of the 209 GW installed across the EU at
end-2022**, projected to fall to ~59% by 2026, and **utility-scale exceeded 50% of
annual EU installations for the first time in 2025** [SECONDARY — SolarPower
Europe]. So the rooftop share of the *stock* is still the majority but the *flow*
has tipped utility-scale, which means the proxy will degrade over time and the
country splits genuinely matter.

### Honest statement of the limitation

The researcher's ISO-NE work already demonstrates how hard this is to pin down.
The pre-registered diurnal test came back **UNINFORMATIVE** — all eight zones,
rising and falling alike, showed the same diurnal *shape* (night down, midday up,
evening up), so the shape carried no information about why VT/ME/RI differ.
Magnitudes differed (+66% to +126% midday in rising zones vs +32% to +49% in
falling ones) but that is a difference of degree.

Nothing in the European material I found resolves that. What Europe offers is not
a better test of the same design — it is a *different* design (the NL-vs-IE
cross-section in §0, matched on total VRE share and split 4.5× on solar share;
and later, the 2027 net-metering discontinuity) in which the confound that
defeated ISO-NE is not present.

---

## 4. Data-centre policy and moratoria

This is the section where press reporting is most wrong, and the brief was right
to warn about it.

### 4.1 Ireland — **there was never a CRU moratorium.** [PRIMARY]

Read directly from the CRU decision paper PDF this session.

**Document:** *Large Energy Users Connection Policy — Decision Paper*, Reference
**CRU/2025236**, published **12 December 2025**, Commission for Regulation of
Utilities.

**The single most-repeated error in the press.** Very widely reported — including
in a commercial energy newsletter I retrieved during this research — is that
"CRU imposed a de facto moratorium on new data centre connections to Dublin's
grid beginning in 2021" and that the December 2025 decision "formally ended the
moratorium." **The CRU's own document says the opposite, twice, explicitly:**

> "In November 2021 the CRU published a decision paper (CRU/21/124) setting out
> that a connection measures approach would be taken. **The CRU was of the view
> that imposing a moratorium on data centre connections would have been
> disproportionate.** … Consistent with the approach taken in decision CRU/21/124
> the CRU is of the view that **imposing a moratorium on data centre connections
> at this time is not an appropriate or proportionate approach** and proposes to
> take an approach based on 'connection measures'."

The June 2021 consultation (CRU/21/060) considered exactly three options: (1) do
nothing, (2) **moratorium on data centre connections**, (3) connection measures.
**Option 3 was chosen in November 2021 and option 3 was chosen again in December
2025.** Option 2 was rejected both times. There has never been a CRU moratorium
in Ireland, and the December 2025 decision did not end one.

**What CRU/21/124 (Nov 2021) actually did** — a Section 34 direction to EirGrid
(TSO) and ESB Networks (DSO) to assess data centre connection applications against
four criteria: location (constrained vs unconstrained region); ability to bring
on-site dispatchable generation and/or storage ≥ demand; ability to provide
demand flexibility via that on-site generation; and ability to provide demand
flexibility on operator request.

**What CRU/2025236 (12 Dec 2025) decides** — a new Section 34 direction that
**supersedes CRU/21/124**. Applications received before publication continue
under the old direction. The policy **applies exclusively to data centres**.

| Tier | Requirement |
|---|---|
| Below **1 MVA** de-minimis | Location assessment by the System Operators only. No other requirements. |
| ≥ 1 MVA and < **10 MVA** | Must provide an **autoproducer unit** meeting **100% of the site's MIC** on a de-rated basis, **participating in the wholesale electricity market**. Compliance removes any separate Mandatory Demand Curtailment obligation. |
| ≥ **10 MVA** | Must provide **dispatchable on-site or proximate generation and/or storage matching MIC** (de-rated), **separately connected and metered**, and **participating in the wholesale market**. **The connection cannot be operational or ramp to full MIC without the associated generation delivered.** |
| All ≥ de-minimis | **≥ 80% of annual demand met by additional renewable electricity generated in the Republic of Ireland**, with a **6-year glide path** from energisation. |

Also decided: System Operators must publish locational capacity/constraint
information, provide initial proposals to CRU on that by **31 March 2026**, and
publish an engagement and connection process for applicants by **31 March 2026**.
Where an SO is not satisfied the connection is consistent with system needs, *"the
application will not be processed by the SO, accordingly, the application will
terminate."*

**Status: in force.** It applies to connection applications from 12 December 2025.

**Supporting figures from the same document [PRIMARY]:**
- Irish total electricity demand grew **30% over the past 10 years**.
- Data centres used **21% of Irish electricity in 2022**.
- **~50% of metered electricity consumption in the Dublin/Meath region in 2024
  was attributable to data centre load** (CRU analysis using CSO June 2025 data
  centre metered consumption data).
- **97% of Ireland's data centres are located in Dublin** — the highest such
  concentration of any European city. *"The next highest concentration after
  Dublin is Amsterdam, where 44% of the data centres in the Netherlands are
  located."* (ICIS 2025 data, cited in the CRU paper.)
- SO market-intelligence exercise suggests potential for **~5.8 GW additional
  data centre demand capacity** in Ireland in the medium term.
- Ireland's target: **80% renewable electricity by 2030**.
- On Dublin specifically, EirGrid's position as recorded by CRU: it is a safety
  and system-security issue relating to the amount of generation connected in
  Dublin and network topology — Dublin has a high concentration of synchronous
  generators, the network is highly meshed, and the existing Dublin fleet is
  connected at 220 kV, which itself makes connecting further generation difficult.

**The EirGrid "no new Dublin connections until 2028" line** is a separate thing
from the CRU policy and is **[SECONDARY]** — reported from 2022 as EirGrid
stating it would not connect new data centres in Dublin "for the foreseeable
future" and possibly until 2028, with pipeline applications still progressing and
non-Dublin applications considered case-by-case. This is a **system operator's
commercial/operational position under the CRU criteria**, not a regulatory
moratorium. Describing it as a moratorium is the error above. See Not-verified §4
— I did not retrieve an EirGrid primary document stating this.

### 4.2 Netherlands — a real, national, currently-in-force restriction

Three distinct things, routinely conflated:

**(a) Amsterdam / Haarlemmermeer municipal stop, July 2019 — expired.**
[SECONDARY] The municipalities of Amsterdam and Haarlemmermeer announced an
immediate halt to new data centre development in July 2019, on land-use and
energy grounds. Lifted after roughly a year: on **1 July 2020** Amsterdam's
municipal executive proposed the successor policy.

**(b) Successor: *Vestigingsbeleid Datacenters*, from 2020.** [SECONDARY] Permits
a limited number of new data centres subject to conditions on spatial embedding,
energy use, water use and circular construction, and confines them to designated
clusters — reported as Amstel III (South-East), Port/Port City (North-West),
Schinkelkwartier (South) and Science Park (East). This is a *zoning-and-conditions*
regime, not a ban.

**(c) National hyperscale restriction — this is the one that is currently in
force.** [SECONDARY]
- **16 February 2022:** the Ministry of the Interior issued a *voorbereidingsbesluit*
  (preparatory decision), a **nine-month** national prohibition on changing land or
  building use to establish a hyperscale data centre, pending permanent national
  rules. Nationwide except the municipalities of **Hollands Kroon** and **Het
  Hogeland**.
- **1 January 2024:** an amendment to the ***Besluit kwaliteit leefomgeving*
  (Bkl)** entered into force making the restriction **permanent**: no hyperscale
  data centres in the Netherlands except at designated locations in **Het
  Hogeland** and **Hollands Kroon**, which the National Environmental Vision
  designates as preferred areas.
- **Definition of "hyperscale" used:** more than **10 hectares** *and* an
  electrical connected load of **70 MW**.

**Status: in force since 1 January 2024, permanent, national.** Unlike Ireland,
this genuinely is a prohibition — but only for the hyperscale size class, and it
is a *spatial-planning* instrument, not a grid-connection instrument.

**Note the contrast worth drawing in the write-up:** the Netherlands restricts
*where you may build*; Ireland restricts *what you must bring with you*. They are
different regulatory technologies aimed at the same problem.

### 4.3 Frankfurt — zoning, not a moratorium [SECONDARY]

Frankfurt's *"Data Centre Concept — Update of the Commercial Land Development
Program"* was passed by the city council on **9 June 2022**. It divides the city
into **suitable areas (Eignungsgebiete)**, **restricted suitable areas
(eingeschränkte Eignungsgebiete)** and **exclusion areas (Ausschlussgebiete)** for
company-independent (cloud/colocation) data centres. Suitable areas are reported
as Sossenheim, Rödelheim, Griesheim, Gallus, Ostend, Fechenheim and Seckbach. The
plan is sized to meet a projected land requirement of **75 hectares through 2030**.
Accompanying measures include a city-wide district heating plan for waste-heat
reuse and an expectation of "Blue Angel" efficiency certification.

No moratorium. Land-use steering.

### 4.4 Nordics and elsewhere

**Not verified.** I did not establish any Singapore-style capacity cap in Europe.
Singapore's own moratorium (2019–2022) and its successor capacity-allocation
regime are frequently cited as the model, but I found no European jurisdiction
that adopted a numerical MW cap of that kind. The Nordics broadly compete *for*
data centre investment rather than restricting it, and Sweden is the most active
SMR market in Europe (§6). See Not-verified §5.

### 4.5 Grid-connection queue dynamics

Weakest-sourced part of this section. What is solid:

- **Ireland [PRIMARY]:** the binding constraint is explicitly stated as a race
  condition — *"The pace at which new electricity demand is being sought by data
  centres is faster than the pace of network infrastructure delivery and the
  development of new generation capacity."* The CRU's answer is to make the
  applicant internalise it: no energisation, and no ramp to full MIC, until the
  matching generation is delivered. Applications that fail assessment
  **terminate** rather than queue. That is a queue-management design choice with
  real consequences — it converts a queue into a filter.
- **Generally [SECONDARY]:** connection waits in major European markets are
  reported to stretch to years, with escalating and unpredictable costs, which is
  the principal driver of BTM interest (§5).

I did not obtain quantitative queue statistics (MW in queue, average wait) for any
European TSO. See Not-verified §6.

---

## 5. Behind-the-meter and co-location in Europe

**The key analytical point, and it inverts the US picture.**

In the US, the FERC co-location fight (docket EL25-49 et al., order 193 FERC
¶ 61,217 of 18 Dec 2025 — already documented in
`docs/research-notes/A-primary-verify.md`) is about data centres netting
generation against load *behind* the meter, making consumption invisible in
metered data and shifting transmission cost recovery onto other ratepayers.

**Ireland has arrived at close to the opposite arrangement, and did it by
regulatory mandate rather than by private initiative.** CRU/2025236 does not
merely permit co-location — it **requires** it for any data centre ≥ 10 MVA. But
it attaches two conditions that specifically prevent the US pathology [PRIMARY]:

1. the generation must be **"separately connected and metered"**; and
2. it must **participate in the wholesale electricity market**.

Separately metered, market-participating co-located generation is **not** invisible
BTM netting. The load remains visible as load and the generation remains visible as
generation. Ireland has mandated physical co-location while explicitly refusing the
netting that makes US co-location a measurement and cost-allocation problem.

**For this project specifically, this is the most important sentence in the
section:** Ireland's design means Irish data-centre load should stay *observable*
in metered data even as co-location becomes universal there — whereas the US
trajectory points the other way. The "shelf life of the data" limitation that
`docs/plans/advisor/2026-08-11-post-meeting-prioritization.md` §2 identifies for the US is
**not** symmetric across jurisdictions, and Ireland is a live example of a
regulator choosing to preserve observability. That is a genuinely publishable
observation and it costs nothing further to make.

### Corporate PPAs vs physical co-location — keep these separate

The brief is right that these get conflated. They are different objects:

- **Corporate PPA:** a *financial/contractual* instrument. The generator connects
  to the grid normally; the data centre draws from the grid normally; the contract
  settles the price difference and transfers certificates. **Metered load is
  completely unaffected.** A 100%-PPA-covered data centre is fully visible in load
  data.
- **Physical co-location:** the generator is electrically adjacent and its output
  is consumed on site. **This is what can change metered load** — and only if the
  arrangement nets, i.e. only if the generation is *not* separately metered.

Ireland's 80%-renewable obligation is satisfiable by contracting ("Data centres
will be able to develop these generation projects directly or contract with other
parties to develop them" [PRIMARY]) — so the 80% obligation is PPA-like and does
not affect metered load. The 10 MVA dispatchable-generation obligation is physical
co-location — but separately metered, so it also does not corrupt the load series.
**Both Irish obligations preserve load observability.** That is not an accident of
drafting; the market-participation requirement is there to make the generation
dispatchable by the system operator, and separate metering follows from that.

### European market context [SECONDARY]

- European corporate PPA momentum **cooled in 2025**: disclosed contracted
  capacity fell to **13.1 GW across 247 deals**, down from **15.3 GW in 2024**, as
  the market adjusted to lower capture-price expectations. **Data centres are one
  of the few buyer categories with structurally growing demand.**
- The principle that BTM generation benefiting from grid backup should contribute
  more to network costs is reported to be gaining traction with European
  regulators — the same cost-shift logic as the US fight.

### Is there a European equivalent of the FERC co-location docket?

**Not one that I could identify, and I am flagging this as a genuine negative
finding rather than a gap I ran out of time on** — though the search was not
exhaustive. There is no single European proceeding of comparable prominence. The
structural reason is visible in the material above: the EU handles this through
**connection policy** (Ireland) and **spatial planning** (Netherlands, Frankfurt)
rather than through **transmission cost allocation**, because European
transmission charging is set nationally by regulators rather than litigated in a
federal tariff proceeding. The US fight is FERC-shaped because US transmission
rates are FERC-shaped. See Not-verified §7.

---

## 6. Nuclear / SMR and data centres in Europe

All **[SECONDARY]** — announcements and MoUs, none of them operating plant. Treat
every one of these as *announced intent*, not committed capacity. None of these
projects is generating.

- **Equinix / ULC-Energy (Netherlands).** Letter of intent for a PPA of up to
  **250 MWe** to power Dutch data centres, announced **14 August 2025** per
  Equinix's own newsroom. ULC-Energy is an Amsterdam-based developer founded 2021
  and has an exclusive agreement (Aug 2022) with **Rolls-Royce SMR** for
  deployment in the Netherlands. **This is a letter of intent, not a construction
  decision.**
- **Equinix, broader programme.** Reported to have signed three deals with
  advanced-nuclear firms totalling **more than 750 MW**.
- **Blykalla / evroc / Studsvik (Sweden).** MoU to explore **Sweden's first
  nuclear-powered data centres** at Studsvik's licensed nuclear site in
  **Nyköping**. Blykalla develops lead-cooled reactors; evroc is building European
  hyperscale AI infrastructure. **An MoU to explore — the weakest possible
  commitment level.**
- **Sweden / Rolls-Royce SMR.** Rolls-Royce SMR selected by Vattenfall — reported
  as three SMRs on the **Värö peninsula near Varberg**, announced **June 2026**.
  This is Sweden's first new nuclear in over 40 years but is **not** a data-centre
  project; it is grid supply. (Note: one source names the counterparty as
  "Videberg Kraft"; I could not confirm the entity name — see Not-verified §8.)
- **Poland.** Ministry of Climate and Environment issued a *Decision in Principle*
  endorsing Rolls-Royce SMR technology. Not data-centre-specific.
- **European SMR market context.** Europe reported as the second most active SMR
  market after the US, with **52 projects** tracked and **~US$156 bn** in potential
  investment; **Sweden leads with 10 proposed projects**, then **Czech Republic (9)**
  and **Poland (6)**.

**Assessment:** the European nuclear-for-data-centres story is at an earlier and
softer stage than the US equivalent — letters of intent and MoUs rather than
signed PPAs against restarting plant. Nothing here affects load or price data
within this project's horizon.

---

## Sources

**Primary — read directly this session**

- CRU, *Large Energy Users Connection Policy — Decision Paper*, CRU/2025236,
  12 Dec 2025 (PDF, read in full via pdftotext):
  https://cruie-live-96ca64acab2247eca8a850a7e54b-5b34f62.divio-media.com/documents/CRU2025236_Large_Energy_User_connection_policy_decision_paper.pdf
- CRU news page for the above decision:
  https://www.cru.ie/about-us/news/the-cru-publishes-its-decision-on-new-electricity-connection-policy-for-data-centres/
- ACER, *Key developments in EU electricity and gas markets — 2026 Monitoring
  Report* (PDF, read via pdftotext):
  https://www.acer.europa.eu/sites/default/files/documents/Publications/2026-ACER-Gas-Electricity-Key-Developments.pdf
- ACER landing page: https://acer.europa.eu/monitoring/electricity-gas-key-developments-2026
- Bundesnetzagentur, *Bundesnetzagentur publishes 2025 electricity market data*,
  press release 5 Jan 2026:
  https://www.bundesnetzagentur.de/SharedDocs/Pressemitteilungen/EN/2026/20260104_SMARD.html
- Ember via Our World in Data, `share-of-electricity-production-from-solar-and-wind`
  (CSV downloaded): https://ourworldindata.org/grapher/share-of-electricity-production-from-solar-and-wind
- Ember via Our World in Data, `share-electricity-solar` (CSV downloaded):
  https://ourworldindata.org/grapher/share-electricity-solar

**Secondary**

- Ember, *European Electricity Review 2026*:
  https://ember-energy.org/latest-insights/european-electricity-review-2026/
  (blocks automated fetch; figures taken from search summaries and the Ember
  update page below — see Not-verified §9)
- Ember, *Wind and solar generated more power than fossil fuels in the EU for the
  first time in 2025*:
  https://ember-energy.org/latest-updates/wind-and-solar-generated-more-power-than-fossil-fuels-in-the-eu-for-the-first-time-in-2025/
- pv magazine, *Europe faces surge in negative power prices as solar output
  grows*, 3 Nov 2025:
  https://www.pv-magazine.com/2025/11/03/europe-faces-surge-in-negative-power-prices-as-solar-output-grows/
- EIA, *Wind and solar generated a record 17% of U.S. electricity in 2025*:
  https://www.eia.gov/todayinenergy/detail.php?id=67367
- EIA, *ERCOT increasingly meets rising demand with solar, wind, and batteries*:
  https://www.eia.gov/todayinenergy/detail.php?id=66464
- DCD, *EirGrid says no new applications for data centers in Dublin until 2028*:
  https://www.datacenterdynamics.com/en/news/eirgrid-says-no-new-applications-for-data-centers-in-dublin-till-2028/
- RTE, *Data centres get to grips with EirGrid's Dublin pause*, 16 Jan 2022:
  https://www.rte.ie/news/business/2022/0116/1273819-data-centres-eirgrid/
- CMS Law-Now, *Netherlands prohibits creating hyperscale data centres until
  national guidelines are passed*, Nov 2022:
  https://cms-lawnow.com/en/ealerts/2022/11/netherlands-prohibits-creating-hyperscale-data-centres-until-national-guidelines-are-passed
- Greenberg Traurig, *Challenges in the Dutch Data Center Market*, Mar 2024
  (source for the 1 Jan 2024 Bkl amendment):
  https://www.gtlaw.com/en/insights/2024/3/challenges-in-the-dutch-data-center-market
- DLA Piper, *Data centers in the Netherlands: a shifting landscape*:
  https://www.dlapiper.com/en/insights/publications/real-estate-gazette/real-estate-gazette-data-centers/data-centers-in-the-netherlands-a-shifting-landscape
- DCD, *The ongoing impact of Amsterdam's data center moratorium*:
  https://www.datacenterdynamics.com/en/analysis/the-ongoing-impact-of-amsterdams-data-center-moratorium/
- Stadtplanungsamt Frankfurt, *Steuerung von Rechenzentren*:
  https://www.stadtplanungsamt-frankfurt.de/steuerung_von_rechenzentren_22137.html
- DCD, *Frankfurt updates its plans for environmental data center zoning*:
  https://www.datacenterdynamics.com/en/news/frankfurt-updates-its-plans-for-environmental-data-center-zoning/
- Equinix newsroom, *Equinix and ULC-Energy Collaborate…*, 14 Aug 2025:
  https://newsroom.equinix.com/2025-08-14-Equinix-and-ULC-Energy-Collaborate-to-Support-Sustainable-AI-Data-Center-Growth-in-the-Netherlands-with-Clean-Nuclear-Power
- World Nuclear News, *Equinix signs further agreements with SMR developers*:
  https://www.world-nuclear-news.org/articles/equinix-signs-further-agreements-with-smr-developers
- Blykalla, *Blykalla, evroc, and Studsvik partner…*:
  https://www.blykalla.com/post/blykalla-evroc-and-studsvik-partner-to-explore-the-development-of-swedens-first-nuclear-powered-data-centers
- Rolls-Royce SMR, Sweden selection:
  https://www.rolls-royce-smr.com/press/sweden-selects-rolls-royce-smr-for-its-nuclear-future
- pv magazine, *Netherlands to phase out net-metering scheme in 2027*, 16 May 2024:
  https://www.pv-magazine.com/2024/05/16/netherlands-to-phase-out-net-metering-scheme-in-2027/
- Wikipedia, *Solar power in the Netherlands* (per-capita and household figures):
  https://en.wikipedia.org/wiki/Solar_power_in_the_Netherlands
- OSTI, *Net Load Forecasting with Disaggregated Behind-the-Meter PV Generation*:
  https://www.osti.gov/biblio/2375798
- A&O Shearman, *Powering data centers: the rise and challenges of the
  behind-the-meter model*:
  https://www.aoshearman.com/en/insights/data-center-insights/powering-data-centers-the-rise-and-challenges-of-the-behind-the-meter-model
- Pexapark, *A Data Center Tale: The Hunger for PPAs* (2025 PPA volumes):
  https://pexapark.com/blog/a-data-center-tale-the-hunger-for-ppas/
- SolarPower Europe, *Annual rooftop and utility scale installations in the EU*:
  https://www.solarpowereurope.org/advocacy/solar-saves/fact-figures/annual-rooftop-and-utility-scale-installations-in-the-eu
- SolarPower Europe, *EU hits 2025 solar target but market contraction puts 2030
  goal at risk*:
  https://www.solarpowereurope.org/press-releases/new-report-eu-hits-2025-solar-target-but-market-contraction-puts-2030-goal-at-risk

---

## Not verified

Explicitly flagged. **Do not quote any of these as established.**

1. **SPP and CAISO 2025 wind+solar shares.** Not obtained. The brief asked for
   them; I declined to estimate. ERCOT (36%, EIA) is a nine-month 2025 figure, not
   full-year — do not present it as annual. US national 2025 (17% utility-scale /
   19% incl. small-scale, EIA) is solid. **Fix:** EIA Electric Power Monthly, or
   each ISO's own annual markets report.
2. **Full-year 2025 negative-price hours outside Germany.** The
   593 / 584 / 576 / 569 / 519 / 513 table is **through end-October 2025** only.
   Germany's figure in that table (576) does not reconcile with the
   Bundesnetzagentur full-year figure (573); at least one uses a different
   product or zone definition. Only the Bundesnetzagentur German series
   (301 / 457 / 573 for 2023 / 2024 / 2025) is verified.
3. **Published European net-load-volatility work.** I found **no** European study
   measuring trends in metered net-load volatility attributable to BTM PV. This is
   absence of evidence from an English-language search, not evidence of absence.
   German- and Dutch-language TSO/regulator literature (TenneT, Bundesnetzagentur,
   PBL, TNO) was not searched and is the most likely place for it.
4. **EirGrid's Dublin position.** The "no new Dublin data centre connections until
   2028" line is press-reported from 2022 and I did **not** retrieve an EirGrid
   primary document stating it. Its current status in 2026 is unknown to me and
   may well have been overtaken by CRU/2025236. Verify before citing.
5. **Singapore-style capacity caps in Europe / Nordic restrictions.** I found none
   and could not confirm that none exist. Treat §4.4 as unresearched rather than
   as a negative finding.
6. **European grid-connection queue statistics.** No quantitative figures (MW in
   queue, average wait) obtained for any European TSO.
7. **A European equivalent to the FERC co-location docket.** I identified none and
   offer a structural explanation for why, but the search was not exhaustive of
   national regulator proceedings (Ofgem, Bundesnetzagentur, ACM, CRE).
8. **Rolls-Royce SMR Sweden counterparty.** One source names "Videberg Kraft";
   I could not confirm this entity and suspect a garbled name. Confirm from the
   Rolls-Royce SMR press release before citing. The June 2026 date is also from a
   single source.
9. **Ember European Electricity Review 2026 country detail.** ember-energy.org
   returns HTTP 403 to automated fetches, so the EU-level figures attributed to it
   (30% wind+solar vs 29% fossil; 369 TWh solar; 13% / 17% shares; 14 of 27
   countries) come from search-engine summaries, **not** from the report read
   directly. The country-level table in §1 does **not** depend on this — it comes
   from the Ember data files downloaded via OWID, which I did read.
10. **Netherlands rooftop figures.** The 1,353 W/capita (2024), 31.5% of homes /
    2.58 m installations (end-2023), and 2.55 GW residential (2023) figures are
    secondary and should be re-sourced to SolarPower Europe or CBS (Statistics
    Netherlands) before use in a write-up.
11. **The BTM forecast-error figures** (30% household / 250% aggregate increase in
    net load forecast error) are quoted from a search summary of the OSTI paper;
    I did not read the paper.
12. **ACER's "five times" vs its own chart.** ACER's text says the average daily
    price difference *"has grown five times compared to the 2020 value"*, and the
    2020 base is 28.3 EUR/MWh. My reading of the bar labels gives 2025 ≈ 109
    EUR/MWh, i.e. **3.9×, not 5×**. Unresolved — the text may refer to a second,
    similar chart later in the report, or my bar-to-year mapping may be wrong
    (pdftotext discards x-position). **Quote ACER's sentence; do not state a 2025
    level.** Resolving this needs the chart read visually, not via text extraction.
13. **Country-level rooftop-vs-utility PV splits.** Not obtained for any country.
    This is the *correct* regressor for H_solar and §0/§3 currently substitute
    solar share of generation as a proxy. EU-wide splits (66% rooftop of stock at
    end-2022; utility-scale >50% of 2025 annual installs) are secondary. **Fix:**
    SolarPower Europe *EU Market Outlook* country chapters, or IEA-PVPS *National
    Survey Reports*, both of which publish the segmentation.
14. **Amsterdam cluster names** (Amstel III, Port/Port City, Schinkelkwartier,
    Science Park) and **Frankfurt suitable-area names** are secondary and
    unconfirmed against the municipal documents.
