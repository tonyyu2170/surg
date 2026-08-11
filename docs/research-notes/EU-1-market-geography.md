# EU-1 — European data-centre market geography and scale

Research note for the SURG energy-economics project (electricity price vs. data-center load
*level* vs. *volatility*). Scoping research for a possible extension of the eight-market
North American diagnostic (PJM/DOM, ERCOT, NYISO, CAISO, IESO, MISO, ISO-NE, SPP) into Europe.

**Compiled:** 11 August 2026. Web research only; no repo or data changes.

**Reading conventions used throughout:**
- **[OFFICIAL]** — national statistics office, TSO, regulator, or government ministry.
- **[RESEARCH]** — research institute or academic body (neither official statistics nor vendor marketing).
- **[INDUSTRY-ESTIMATE]** — CBRE / JLL / DC Byte / Knight Frank / brokerage or market-research output.
- **[DERIVED]** — my own arithmetic from cited inputs, labeled as such, not published by anyone.
- Every figure carries an as-of year. Several official series lag 12–24 months; a "2024 figure"
  is often the newest official one even where 2026 pipeline announcements exist. Do not read
  figures from different rows as simultaneous.

---

## 0. Headline findings — read this first

1. **Ireland is Europe's treatment market, and it is not close.** Data centres consumed
   **23% of Ireland's total *metered* electricity in 2025** (7,663 GWh) — CSO, published
   7 July 2026. The next-highest verified official national share in Europe is the
   **Netherlands at 4.6%** (2024, CBS). Germany is ~4% [RESEARCH], the UK ~2% (2023).
   **A 5x gap is far too large to be a definitional artifact** — see §4.

2. **Ireland is also the only European market that publishes a facility-class load series
   at all — and it is quarterly.** The CSO series runs 2015–2025 with quarterly granularity.
   This directly dissolves the obstacle that blocked all eight North American markets, where
   no data-center-specific load series exists at any frequency. **But read §6 carefully: it
   solves the *existence* problem, not the *identification* problem.** It is national and
   quarterly — not sub-regional, not hourly. Ireland trades one data gap for a different one.

3. **The single most important structural caveat for an Ireland extension is market
   geography, not data.** Irish prices are set in the **all-island Single Electricity Market
   (SEM)**, spanning the Republic *and* Northern Ireland, while the CSO load series covers the
   Republic only. Load and price do not share a footprint. Flagged as a research-design issue
   in §6; not investigated further here.

4. **Europe has nothing geographically comparable to Data Center Alley.** Northern Virginia is
   **~2.1x to ~3.3x Frankfurt** — Europe's largest single market (~1,222 MW, Q1 2026) —
   depending on which Northern Virginia basis is used (2,611 MW CBRE H1 2024 inventory vs
   4,040 MW end-2025 aggregator), and is on the same order as the *entire* FLAP-D group
   combined (~3.8 GW live, mid-2026). Caveats on comparability in §5 — but the *ordering* is
   robust under every basis.

5. **Where Europe does compare is on transmission constraint, and there the evidence is
   official and strong.** Amsterdam (5,116 MW connection queue, 2023), Denmark (60 GW queue
   against ~7 GW peak demand; connections paused Mar–Jun 2026), Dublin (CRU connection
   policy, Dec 2025), West London and central Frankfurt (no substation relief until the
   2030s). For this project's purposes a constrained pocket is the analytically relevant
   object, and Europe has several. See §5.

6. **A structural break is coming in European data availability.** Under EED Article 12 and
   Delegated Regulation (EU) 2024/1364, every EU data centre with ≥500 kW installed IT power
   must report annual energy performance to a **European database**. **However, Annex IV
   specifies publication in *aggregated* form at member-state and EU level** — so this will
   likely produce new official *national* series, not the facility-level data the project has
   been missing. See §6.

---

## 1. Capacity by country and metro

### 1.1 The critical distinction

Operational capacity, under-construction capacity, and announced/queued capacity are three
different things and are conflated constantly in this sector. This note keeps them in three
tiers. **The third tier is the dangerous one:** interconnection-queue and early-planning
figures are non-firm, heavily duplicated (one project appearing in several queues), and
routinely 5–10x what actually gets built. Italy's ">50 GW of requests" against 311 TWh/yr of
national consumption is self-evidently not a build forecast.

There is also a **units problem**: vendors variously report *IT load*, *facility/commissioned
power*, *core-and-shell capacity*, and *total market size*, and rarely say which. Ratios
between them run 1.2–1.5x (PUE) or worse. Where I could not establish the basis, I say so.

### 1.2 FLAP-D aggregate [INDUSTRY-ESTIMATE]

| Tier | FLAP-D total | As-of | Source |
|---|---|---|---|
| Live capacity | **~3.8 GW** | mid-2026 (H1) | JLL |
| To be delivered in-year | +453 MW | rest of 2026 | JLL |
| Under construction | **~1.4 GW** | mid-2026 | JLL |
| Planned | **~2 GW** | mid-2026 | JLL |

FLAP-D live capacity grew from ~1.8 GW (2019) to ~3.8 GW (H1 2026) — slightly more than
doubling in seven years. Note this is a **colocation** measure and **excludes hyperscaler
self-build**, which is material in Dublin, Frankfurt and Amsterdam. CBRE separately expects
European hyperscaler self-build growth to outpace colocation supply growth.

**H1 2026 capacity additions by market** [INDUSTRY-ESTIMATE, JLL]:
Paris 72.5 MW · London 49 MW · Frankfurt 45 MW · Amsterdam 16.3 MW · Dublin 11.4 MW.
(These are *additions in the half-year*, not inventory.)

### 1.3 Per-market inventory [INDUSTRY-ESTIMATE — see conflict note]

| Market | Total inventory | YoY growth | As-of | Source |
|---|---|---|---|---|
| Frankfurt | **1,222.5 MW** | +23% | Q1 2026 | CBRE |
| Paris | **666.8 MW** | +15% | Q1 2026 | CBRE |
| Amsterdam | ~649 MW **[DERIVED]** | +11% (+64.3 MW) | Q1 2026 | CBRE (total derived) |
| London | not stated | +21% | Q1 2026 | CBRE |
| Dublin | ~1,150 MW *(disputed)* | — | H1 2025 | secondary; primary unconfirmed |
| London | ~1,189 MW *(disputed)* | — | H1 2025 | secondary; primary unconfirmed |

**Amsterdam derivation:** CBRE reports +64.3 MW = +11% YoY. If 64.3 is the increment on the
prior-year base, base ≈ 585 MW and current ≈ 649 MW. **This is my arithmetic, not a CBRE
published total.** Treat as approximate.

**⚠ Unresolved conflict — do not cite Dublin/London H1 2025 without pinning the primary.**
A secondary claim circulates that Dublin has ~1,150 MW operational, "second largest in
Europe, just short of London's 1,189 MW." This is **irreconcilable with CBRE's Q1 2026
Frankfurt figure of 1,222.5 MW**, which would make Frankfurt the largest, not third. The two
sets almost certainly use different definitions (IT vs facility power; colocation-only vs
including self-build) and different vendors. I could not reach the primary for the
Dublin/London pair. See "Not verified."

### 1.4 Nordics

| Country | Installed capacity | As-of | Source |
|---|---|---|---|
| Denmark | **398 MW** installed; **208 MW** under construction | start of 2026 | [INDUSTRY-ESTIMATE] |
| Norway | **501 MW** installed | ~2024–25 | [INDUSTRY-ESTIMATE] |
| Sweden | **~160.8 MW** third-party core-and-shell | Dec 2024 | [INDUSTRY-ESTIMATE] |
| Finland | not found in MW | — | see "Not verified" |

Denmark projected to reach **~1.2 GW by 2030** [INDUSTRY-ESTIMATE].

Note the Swedish figure is explicitly *third-party* core-and-shell and therefore excludes
hyperscaler self-build — which in Sweden is the larger part of the market. It is not
comparable to the Danish or Norwegian numbers above.

### 1.5 Emerging markets

| Market | Operational | Under development / pipeline | As-of | Tier |
|---|---|---|---|---|
| Madrid | **175 MW IT** | **>1,400 MW IT** pipeline | ~2025–26 | pipeline = announced |
| Lisbon | **58 MW** | **408 MW** under development; **821 MW** early planning | ~2025–26 | mixed |
| Milan | not established | **4.6 GW** "pipeline" | ~2025–26 | **queue/planning — treat as speculative** |
| Warsaw | not found | not found | — | see "Not verified" |

**Italy, national [OFFICIAL, Terna]:** as of **30 June 2025**, data-centre connection
requests exceeded **300 projects totalling >50 GW**, up from ~30 GW at end-2024.
**This is a connection queue, not a build pipeline.** Against Italian national consumption of
311 TWh/yr, 50 GW is not a credible build forecast. It is, however, a genuine signal of
speculative interconnection pressure and is officially sourced.

---

## 2. Data centres as a share of national electricity consumption

### 2.1 Summary table

| Country | Share | Denominator (exact wording) | Absolute | Year | Tier |
|---|---|---|---|---|---|
| **Ireland** | **23%** | "total **metered** electricity consumption" | 7,663 GWh | **2025** | [OFFICIAL] CSO |
| **Ireland** | **21.2%** | "all electricity demand" | 7.0 TWh | 2024 | [OFFICIAL] SEAI — *secondary-sourced, see below* |
| **Netherlands** | **4.6%** | "the Netherlands' total electricity consumption" | 5,100 GWh | 2024 (provisional) | [OFFICIAL] CBS |
| **Germany** | **~4%** | "gross power consumption" | 20 TWh | 2024 | [RESEARCH] Borderstep/Bitkom |
| **UK** | **~2%** | "total UK electricity demand" | 5.0 TWh | 2023 | secondary-sourced |
| **Finland** | **just under 2%** | "Finland's total consumption" | ~1.6 TWh | 2024 | secondary (Nordea) |
| **Denmark** | ~2 TWh (share not stated) | — | 2 TWh | ~2025 | [OFFICIAL] Ministry |
| **Norway** | **~1%** | "national electricity **production**" ⚠ | — | ~2024–25 | [INDUSTRY-ESTIMATE] |
| **Sweden** | **not established** | — | — | — | see "Not verified" |
| **Nordics (region)** | **2%** | "total demand" | 8 TWh | 2024 | [INDUSTRY-ESTIMATE] Argus |
| **EU (whole)** | **~3%** | "the EU's electricity demand" | — | 2024 | European Commission |

⚠ **Norway's denominator is *production*, not consumption.** Norway's electricity production
and consumption differ by roughly 20 TWh (net exporter), so this share is not comparable to
the consumption-based shares above. Reported as given.

### 2.2 Ireland in detail — the two official figures reconcile

This is the load-bearing claim of the whole document, so the definitional work is set out
explicitly.

**Ireland has two different official data-centre electricity figures, and they use different
denominators.** They are *not* in conflict:

- **CSO** (Data Centres Metered Electricity Consumption 2025, published **7 July 2026**):
  data centres = **23% of total *metered* electricity consumption** in 2025, on 7,663 GWh.
  The 2024 figure on the same basis was **22%** on 6,973 GWh.
- **SEAI** (Energy in Ireland 2025, reporting year 2024): data centres = **21.2% of *all
  electricity demand***, on 7.0 TWh, against total Irish electricity demand of 32.9 TWh.

**[DERIVED] Reconciliation.** The numerators agree (CSO 6,973 GWh ≈ SEAI 7.0 TWh for 2024).
Back out the CSO denominator: 6,973 / 0.22 ≈ **31.7 TWh of metered consumption**. Against
SEAI's **32.9 TWh of total demand**, the gap is **~1.2 TWh (~3.6%)** — the right order of
magnitude for transmission/distribution losses plus unmetered supply. **The two official
series are consistent; the percentage difference is entirely a denominator effect.**

**Practical guidance for the paper:** cite **23% of metered consumption (2025, CSO)** as the
official headline, and state the denominator explicitly every time. If a total-consumption
basis is needed, derive it from the CSO GWh numerator against a named SEAI/Eurostat total and
**label it as your own derivation** — neither office publishes that ratio. On a
total-demand basis 2025 is likely **~22–23%** [DERIVED, approximate: 7,663 GWh against an
estimated ~33.6–33.9 TWh total demand assuming 2–3% growth from SEAI's 2024 figure].

**CSO series construction (matters for interpretation).** Source is ESB Networks meter data.
There is **"no agreed definition of a data centre"** — the CSO identified data-centre MPRNs
out of ~2.5–2.6 million meters via: name/alias search for known data centres consuming
>0.5 GWh; examination of customers in specific business parks >0.5 GWh; and examination of
all meters with annual consumption >1 GWh; supplemented by the Business Register and other
sources. Selection targets MPRNs with high consumption **not** associated with high
employment or other identifiable activity (e.g. cement manufacture).
**Stated caveat:** "A new data centre may have a relatively low amount of electricity
consumption at first and hence may initially be below the search thresholds." The series
therefore likely **under-counts new/ramping facilities**.

**Quarterly detail, 2025** [OFFICIAL, CSO]: Q1 1,821 GWh · Q2 1,894 GWh · Q3 1,956 GWh ·
Q4 1,991 GWh. (Sums to 7,662 GWh, consistent with the 7,663 GWh annual.) Series runs
2015–2025. Note the profile is **near-monotonic and remarkably smooth** — quarterly variation
is dominated by trend growth, not by seasonal or operational swing. That is itself a
substantive observation for a level-vs-volatility study.

**Trajectory:** 1,240 GWh (2015, 5% share) → 2,490 GWh (2019) → 6,973 GWh (2024, 22%) →
7,663 GWh (2025, 23%). **Data centre consumption has risen every single year without
exception.** For comparison, in 2025 residential consumption was 28% of metered total
(urban dwellings 18%, rural 9%) — urban dwellings' share *fell* from 22% in 2015 and rural
from 12%, while data centres rose from 5%. Non-data-centre metered consumption grew just
**2%** in 2025 against the data centres' **10%**.

**The demand-growth attribution is the most striking Irish statistic:** SEAI attributes
**88.2% of the entire increase in Irish electricity demand since 2015** to data centres.

### 2.3 Netherlands in detail [OFFICIAL, CBS]

Published **15 December 2025**, reference year **2024** (provisional): data centres consumed
**5,100 GWh = 4.6% (4.58%) of total Dutch electricity consumption**, up from **1.48% in
2017** and 3.3% in 2021. Growth is **decelerating**: +37% over 2021–2024 versus +58% over
2018–2021.

Structure: **~200 data centres**, of which **~45 large facilities (>10 GWh each) account for
~90%** of all data-centre electricity. Most are **located around Amsterdam**.

**Explicit CBS caveat:** figures "only relate to electricity connections where the data centre
itself is the main activity" — in-house facilities run by universities, hospitals and similar
are **excluded**. The Dutch figure is therefore, if anything, an under-count on a
like-for-like basis with Ireland's.

### 2.4 Germany [RESEARCH — label carefully]

Borderstep Institute (for the Bitkom study *Data Centres in Germany: Current Market
Developments – Update 2025*): **20 TWh in 2024**, rising to **21.3 TWh expected in 2025**.
Data centres plus smaller IT installations ≈ **4% of German gross power consumption (2024)**.
Roughly two-thirds of that consumption is IT infrastructure; one third is cooling, building
infrastructure and UPS.

**Borderstep is a research institute and Bitkom an industry association — this is neither
official statistics nor vendor marketing.** The German federal statistics office does not
publish an equivalent series.

The **Bundesnetzagentur** (federal network regulator, [OFFICIAL]) demand assessment projects
this could reach **10% by 2037**.

### 2.5 United Kingdom

**~5.0 TWh in 2023 ≈ 2% of total UK electricity demand** (and ~7% of commercial-sector
consumption). *Secondary-sourced — I did not reach a DESNZ primary; the NESO PDF would not
render as text.*

Forward projections in §3.

---

## 3. Growth rates and forecasts to 2030

### 3.1 Ireland [OFFICIAL]

- **9.4 TWh (2025) → 14.6 TWh (2034)** for data-centre electricity demand.
- Share of national electricity demand: **22% (2024) → 31% (2034)**.
- Both figures as cited by the **CRU** in its December 2025 connection-policy decision,
  drawing on EirGrid analysis.
- Observed growth: **+10% year-on-year 2024→2025** (CSO), against +2% for all other metered
  customers.

> ⚠ **Unreconciled gap — do not splice these into one series.** The EirGrid/CRU forecast of
> 9.4 TWh for 2025 exceeds the CSO's *measured* 7.663 TWh for the same year by ~1.7 TWh
> (~23%). The two are clearly on different bases, but **which** difference accounts for the
> gap is **not established**. Candidate explanations — an all-island rather than
> Republic-only footprint; a wider "large energy user" definition than the CSO's data-centre
> class; or a forecast vintage predating 2025 actuals — were **not** verified, and the
> all-island explanation is not obviously sufficient on its own, since Northern Ireland's
> *entire* electricity consumption is only ~8 TWh. Because the 22%→31% trajectory rests on
> this base, resolving the gap should precede any use of that trajectory. See §8.1.

### 3.2 United Kingdom

- **NESO Clean Power 2030**: ~**22 TWh** data-centre demand by 2030; ~**5.2 GW** connected
  capacity; **just under 6%** of total UK electricity consumption by 2030. [OFFICIAL]
- **NESO, July 2025, 2050 scenarios**: **30 TWh/yr** ("falling behind", lowest growth) to
  **71 TWh/yr** ("electric engagement", highest growth). [OFFICIAL]
- **Oxford Economics**: **26.2 TWh by 2030 = 8.8%** of UK electricity demand (30.4% of
  commercial consumption) — more aggressive than NESO. [RESEARCH/consultancy]

### 3.3 Denmark [OFFICIAL — supersedes older forecasts]

**Klimastatus og -fremskrivning 2025 (KF25)**, Danish Ministry of Climate, Energy and
Utilities / Danish Energy Agency:
- Current data-centre consumption **~2 TWh/yr**.
- **8 TWh by 2030.**
- **26 TWh by 2050** — described as roughly **one third of Denmark's entire electricity
  consumption** within ~25 years.

⚠ **Older Danish forecasts are still widely quoted and should not be used.** The Danish
Energy Agency's 2019 projection (15% of consumption by 2030), a 2021 Ea Energianalyse/DEA
figure (~17% by 2030), and a "one-fifth by 2030" 2024 reading all predate KF25. Some were
stated against an *energy* rather than *electricity* budget. **Cite KF25 (2025) only.**

### 3.4 Nordics [INDUSTRY-ESTIMATE, Argus]

Regional: **8 TWh (2024, 2% of total demand) → 28 TWh/yr by 2030 (5% of total demand)**.
By country to 2030: Sweden ~**9 TWh**, Norway ~**7 TWh**, Finland ~**4 TWh** (roughly double
2024). These are broker/press estimates, not TSO forecasts.

### 3.5 Europe-wide and global [OFFICIAL, IEA]

*Energy and AI* (IEA):
- **Global** data-centre electricity consumption roughly **doubles to ~945 TWh by 2030**,
  just under **3% of global electricity consumption**.
- **Europe**: data-centre electricity consumption **grows by more than 45 TWh, up ~70%**, by
  2030. This is materially slower growth than the US or China.
- Renewables and nuclear supply most of Europe's additional requirement, their combined share
  reaching **85% by 2030**.
- Accelerated (AI) servers grow ~**30% annually** in the Base Case; AI rises from ~5–15% of
  data-centre power use recently to a possible **35–50% by 2030**.

**Germany**: Bundesnetzagentur — data centres could roughly **double to ~10% of consumption
by 2037**. [OFFICIAL]

---

## 4. Which European market has the highest data-centre share of national demand?

**Ireland — 23% of total metered electricity consumption (2025, CSO).** No other European
country is within a factor of four.

### 4.1 Is this real, or is it a measurement artifact?

This is the right question to ask, because Ireland is also the country that *measures* this
best, and "highest measured" can be an artifact of who bothers to measure. **The answer is
that Ireland's lead is real.**

The decisive evidence is the **Netherlands**. CBS publishes a directly comparable official
national series — same kind of institution, same kind of metered-supply basis, an explicitly
*conservative* scope (excludes in-house university/hospital facilities). It reports **4.6%**
(2024). Ireland on the nearest-comparable year reports **22%** (2024).

**A ~5x gap cannot be produced by definitional differences.** Denominator effects between
metered consumption and total demand are worth ~1 percentage point in Ireland (§2.2).
Scope effects of the CBS in-house exclusion would move the Dutch figure by tenths of a point,
not by 17 points. Germany (~4%) and the UK (~2%), from independent institutions on
independent methods, corroborate the low European baseline.

**Conclusion: Ireland genuinely is an outlier, by roughly a factor of five, on the metric
that matters most to this project.** It is the closest thing Europe has to a treatment market.

### 4.2 Which markets could plausibly rival it, and when?

None currently. On *forecast* trajectories, the plausible challengers are:

| Candidate | Forecast share | By | Basis |
|---|---|---|---|
| **Denmark** | ~8 TWh/yr; ~⅓ of consumption by ~2050 | 2030 / 2050 | [OFFICIAL] KF25 |
| **Ireland** | **31%** of national demand | 2034 | [OFFICIAL] CRU/EirGrid |
| UK | just under 6% | 2030 | [OFFICIAL] NESO |
| Germany | ~10% | 2037 | [OFFICIAL] BNetzA |

**Denmark is the market to watch**, and is the only European country with an official
projection implying an Ireland-like share — but on a **2050**, not 2030, horizon, and from a
small installed base (398 MW at start-2026). Denmark also has no published historical
data-centre load series comparable to the CSO's, so it currently fails on data availability
even though it may eventually qualify on exposure.

### 4.3 What would have to be published for others to become comparable

For any other European market to serve as a treatment case, it would need a
**data-centre-specific metered load series with history and sub-annual frequency**. Today:

- **Netherlands** — has the annual official series (CBS); would need sub-annual frequency and
  regional breakdown.
- **Denmark, Sweden, Finland, Norway, Spain, Italy, Poland** — no official national
  data-centre load series identified. Sweden's new reporting law (§6) may change this.
- **Germany, UK** — figures come from research institutes and system-operator scenarios, not
  from a measured statistical series.

---

## 5. Concentration: does Europe have a Data Center Alley?

### 5.1 The MW comparison — and why it must be handled carefully

**Reference point:** Northern Virginia ended 2025 with **~4,039.6 MW of data-center
inventory** across Loudoun/Fairfax (~600–700 facilities). *Source: this project's own
`B-loudoun-geography.md`, which flags it as a secondary/aggregator figure to be treated as
directional. The same note records DCD citing CBRE H1 2024 at 2,611.1 MW inventory plus
1,157 MW under construction.*

**⚠ Comparability warning.** Comparing that 4,040 MW to Europe's 3.8 GW FLAP-D figure is
tempting and partly misleading:
- The **JLL 3.8 GW is colocation live capacity and excludes hyperscaler self-build**, which is
  material in Dublin, Frankfurt and Amsterdam.
- The NoVA figure is a **CBRE-basis inventory** number whose treatment of self-build and of
  IT-vs-facility power I have not confirmed.
- IT load vs facility power differs by PUE (~1.2–1.4x) and vendors rarely state which.

**State the ratio as a range across bases, rather than claiming a matched-vendor comparison.**
The end-2025 figure of 4,039.6 MW is labeled in `B-loudoun-geography.md` as a
**secondary/aggregator** number of unconfirmed basis; the *confirmed* CBRE-sourced figure in
that note is **2,611.1 MW inventory + 1,157 MW under construction (H1 2024)**. Against
Frankfurt's 1,222.5 MW (CBRE, Q1 2026):

> **Northern Virginia is ~2.1x Frankfurt on the confirmed CBRE H1 2024 inventory figure, and
> ~3.3x on the end-2025 aggregator figure.**

**The ordering holds under every basis available.** No single European metro approaches
Northern Virginia's concentration. Northern Virginia alone is on the same order as all five
FLAP-D markets combined — but state that as a *rough order-of-magnitude* observation with the
caveats above, not as a precise 4,040-vs-3,800 comparison.

### 5.2 The better question: is any European cluster in one transmission-constrained pocket?

For this project, a constrained pocket is the analytically relevant object — that is what
makes Loudoun's load bind on price. **On this dimension Europe has several genuine analogues,
and the evidence is official.**

**Amsterdam / Haarlemmermeer — the strongest European analogue on constraint.**
- ~200 Dutch data centres, **most located around Amsterdam**; ~45 large sites = ~90% of
  data-centre load [OFFICIAL, CBS].
- **Netbeheer Nederland: in 2023 Amsterdam had 9,396 customers waiting for a grid connection,
  equivalent to 5,116 MW.** Realised wholesale connections fell from 4,267 (2020) to 2,929
  (2023), attributed to Amsterdam-region congestion. [OFFICIAL]
- Grid operator **Liander warns shortages persist until at least 2030**.
- **April 2026: a court ruled the Haarlemmermeer grid is full**, delaying a data-centre
  connection — a judicial confirmation of the constraint.
- Policy history: Amsterdam and Haarlemmermeer imposed a **one-year moratorium in June 2019**;
  restrictions persist, including a reported cap on new projects above 70 MW. Developers are
  displacing to Rotterdam.

**Dublin — highest exposure, explicit regulatory response.**
- **CRU decision, 12 December 2025** (current governing policy). Requires new data centres to:
  (i) provide generation and/or storage capacity, onsite or local, matching their maximum
  import demand; (ii) meet **at least 80% of annual demand with additional renewable
  electricity projects built in Ireland** (6-year development window); (iii) have associated
  generation participate in the wholesale market. System operators must assess **whether each
  requested connection is in a constrained or unconstrained location**, case by case.
  Applies to applications submitted after 12 Dec 2025. SOs to publish engagement processes by
  31 March 2026.
- The CRU explicitly declined a blanket moratorium, calling it "not an appropriate or
  proportionate approach."
- ⚠ **Vintage trap:** the widely repeated "no new Dublin connections until 2028" is a **2022
  EirGrid** statement and is **superseded** by the Dec 2025 CRU policy. Reporting indicates
  Dublin returned to active growth in 2026 under the Large Energy User framework. Use the CRU
  decision as current state; the 2028 line as historical context only.

**Denmark — largest queue-to-system ratio in Europe.**
- **Energinet paused all new large-load grid connection agreements in March 2026** when
  pending requests reached **~60 GW** — against Danish peak demand of roughly **7 GW**, a
  queue nearly **nine times peak load**. Data centres ≈ **15 GW (about a quarter)** of it.
- Pause **lifted 3 June 2026**; first-come-first-served abolished from **1 February 2026**,
  replaced by pooled assessment on maturity, development progress and grid-friendliness.
- ⚠ The 60 GW is a **queue**, not a build pipeline. Its analytical value is as evidence of
  constraint severity, not of future load.

**Frankfurt.** Grid capacity in the central data-centre area "remains constrained, with
upgrades unlikely until the 2030s"; municipal rezoning is pushing developers 40+ km out.
[INDUSTRY-ESTIMATE, CBRE]

**London.** "Power availability in the London area remains a key constraint. The West London
corridor is unlikely to receive a key substation upgrade until the early 2030s." Expansion is
shifting to north London. [INDUSTRY-ESTIMATE, CBRE]

**Paris.** Constraint is **permitting/environmental**, not primarily transmission — lengthy
environmental assessments and multi-level approvals. Development concentrated south of Paris.
[INDUSTRY-ESTIMATE, CBRE]

### 5.3 Verdict on Q5

**No European cluster matches Northern Virginia's absolute concentration**, and the largest
single European market is roughly a third its size. **But several European clusters are
comparably or more severely transmission-constrained**, and — unlike Northern Virginia —
their constraints are documented in official regulator/TSO/court artifacts.

Ranked as candidate analogues for this project:
1. **Dublin** — highest national exposure, explicit regulator decision, official quarterly load series.
2. **Amsterdam/Haarlemmermeer** — tightest documented pocket (5,116 MW queue, court ruling, named DSO).
3. **Denmark (Jutland)** — most extreme queue-to-peak ratio; small installed base today.
4. **West London / central Frankfurt** — real constraints, but low national data-centre share.

---

## 6. Implications for the project

**What Ireland solves.** Every North American market failed on the same obstacle: no
facility-level or sub-regional data-center load data, only metered regional aggregates.
Ireland is the **only** market examined here where an official statistics office publishes a
**data-centre-specific electricity series** — 2015–2025, **quarterly**, with methodology and
caveats documented. That is strictly more than PJM, ERCOT, NYISO, CAISO, IESO, MISO, ISO-NE or
SPP offer.

**What Ireland does not solve.** The series is **national and quarterly**. The
level-vs-volatility diagnostic needs sub-regional and high-frequency identification.
Quarterly national data supports a *level* story but is far too coarse to say anything about
*volatility* at the frequency the North American work operates on. **Ireland trades the
"no data at all" problem for a "wrong granularity" problem.** It is a real improvement, but
it is not the identification the diagnostic requires. Do not over-read it.

Relatedly, the Irish quarterly profile (§2.2) is **near-monotonic and smooth** — quarterly
variation is dominated by trend growth. Any volatility signal at that frequency will be
mechanically weak.

**The market-geography problem — flag before committing.** Irish wholesale prices are set in
the **all-island Single Electricity Market (SEM)**, covering the Republic and Northern
Ireland. The CSO load series covers the **Republic only**. Load and price therefore do not
share a geographic footprint — a mismatch with no analogue in the North American work, where
load and LMP come from the same balancing authority. This should be resolved before an
Ireland extension is committed to. *Not researched here.*

**The structural break worth watching.** Under **EED Article 12** ((EU) 2023/1791) and
**Delegated Regulation (EU) 2024/1364**, every EU data centre with **≥500 kW installed IT
power** must report annual energy performance (consumption, PUE, WUE, ERF, REF) to a
**European database**. First reports covered CY2023 (due 15 Sep 2024); thereafter due
**15 May** for the preceding year.

⚠ **Critical caveat: Annex IV specifies publication to the public in *aggregated* form at
member-state and EU level.** So the likely output is **new official national series for every
EU member state** — valuable, and it would let the Ireland-vs-rest comparison be made on
consistent definitions — but **not** the facility-level data this project has been missing.
Whether any member state publishes at finer granularity is worth one targeted follow-up.

**Sweden** has gone further domestically: a law in force **1 July 2025** requires data-centre
operators with ≥500 kW installed IT power to disclose energy performance annually, with the
**first report due 15 May 2026 covering calendar 2025**. That data may now exist. Worth a
follow-up check.

---

## 7. Sources

**Ireland — official**
- [CSO, Data Centres Metered Electricity Consumption 2025 (pub. 7 Jul 2026)](https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/)
- [CSO, Key Findings 2025](https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/keyfindings/)
- [CSO, Background Notes 2025](https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/backgroundnotes/)
- [CSO, methodology page](https://www.cso.ie/en/methods/energy/datacentresmeteredelectricityconsumption/)
- [CSO, 2024 release](https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2024/)
- [CRU, Decision on New Electricity Connection Policy for Data Centres (12 Dec 2025)](https://www.cru.ie/about-us/news/the-cru-publishes-its-decision-on-new-electricity-connection-policy-for-data-centres/)
- [CRU, Large Energy Users Connection Policy decision paper (PDF)](https://cruie-live-96ca64acab2247eca8a850a7e54b-5b34f62.divio-media.com/documents/CRU2025236_Large_Energy_User_connection_policy_decision_paper.pdf)
- [SEAI, Energy in Ireland (landing page)](https://www.seai.ie/data-and-insights/seai-statistics/key-publications/energy-in-ireland) · [Energy in Ireland 2025 (PDF — 403/image-only on fetch)](https://www.seai.ie/sites/default/files/publications/Energy-in-Ireland-2025.pdf)
- [EirGrid, All-Island Resource Adequacy Assessment](https://www.eirgrid.ie/airaa) · [AIRAA 2026–2035 (PDF — did not render as text)](https://cms.eirgrid.ie/sites/default/files/publications/AIRAA-2026-2035_Ireland.pdf)
- [Gov.ie, Data Centre Energy and Sustainability Performance Reporting Obligations](https://www.gov.ie/en/department-of-climate-energy-and-the-environment/publications/data-centre-energy-and-sustainability-performance-reporting-obligations/)

**Netherlands — official**
- [CBS, "Data centres consume 4.6 percent of the Netherlands' electricity" (15 Dec 2025)](https://www.cbs.nl/en-gb/news/2025/51/data-centres-consume-4-6-percent-of-the-netherlands-electricity)
- [CBS, Elektriciteit geleverd aan datacenters, 2017–2024](https://www.cbs.nl/nl-nl/maatwerk/2025/51/elektriciteit-geleverd-aan-datacenters-2017-2024)

**Denmark — official**
- [Klimastatus og -fremskrivning 2025 (KF25), Ministry of Climate, Energy and Utilities (PDF)](https://www.kefm.dk/Media/638917081009383884/KEFM_KF25_200825_DEL%201.pdf)
- [Danish Energy Agency, Klimastatus og -fremskrivning](https://ens.dk/analyser-og-statistik/klimastatus-og-fremskrivning)
- [Plesner, "Energinet's grid connection pause and its impact"](https://plesner.com/en/news/energinets-grid-connection-pause-and-its-impact-what-do-project-owner)

**UK — official**
- [NESO, Data Centres (document)](https://www.neso.energy/document/246446/download)
- [Energy Demand Research Centre, on NESO's Clean Power 2030 demand advice](https://www.edrc.ac.uk/news-blog/clean-power-2030-a-reflection-on-energy-demand-following-nesos-advice-to-government/)
- [UK Parliament, written evidence DCU0081](https://committees.parliament.uk/writtenevidence/166090/html/)

**Germany**
- [Borderstep Institute, Data centres in the EU — Facts & Figures](https://www.borderstep.org/data-centres-in-the-eu-facts-figures/) [RESEARCH]
- [BMWK, Status and development of the German data centre landscape — Executive Summary (PDF)](https://www.bundeswirtschaftsministerium.de/Redaktion/EN/Publikationen/Digitale-Welt/status-and-development-of-the-german-data-centre-landscape-executive-summary.pdf?__blob=publicationFile&v=2) [OFFICIAL]
- [heise, "Government: Power consumption of data centers likely to double by 2037" (BNetzA)](https://www.heise.de/en/news/Government-Power-consumption-of-data-centers-likely-to-double-by-2037-10194679.html)

**Italy / Spain — official**
- [Terna, Lightbox: "Data centres and the future: the energy challenge facing Italy"](https://lightbox.terna.it/en/insight/data-center-trasmission-grid)
- [Terna, Electricity demand of 311.3 TWh in 2025](https://www.terna.it/en/media/press-releases/detail/electricity-consumption-2025)

**EU-level regulation and forecasts**
- [European Commission, EU-wide scheme for rating sustainability of data centres (15 Mar 2024)](https://energy.ec.europa.eu/news/commission-adopts-eu-wide-scheme-rating-sustainability-data-centres-2024-03-15_en)
- [Finnish Energy Authority, "Reporting from data centres to the European database has started"](https://energiavirasto.fi/en/-/reporting-from-data-centres-to-the-european-database-has-started)
- [Swedish Energy Agency, Data centre energy performance reporting](https://www.energimyndigheten.se/en/climate/climate/data-centre-energy-performance-reporting/)
- [White & Case, Data centres and energy consumption: evolving EU regulatory landscape, outlook 2026](https://www.whitecase.com/insight-alert/data-centres-and-energy-consumption-evolving-eu-regulatory-landscape-and-outlook-2026)
- [IEA, Energy and AI — Energy demand from AI](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai)
- [IEA, Energy and AI — Executive summary](https://www.iea.org/reports/energy-and-ai/executive-summary)
- [IEA, Data centres and energy — from global headlines to local headaches?](https://www.iea.org/commentaries/data-centres-and-energy-from-global-headlines-to-local-headaches)

**Netherlands grid constraint**
- [NL Times, "Judge rules electricity grid in Haarlemmermeer is full, data centre connection delayed" (29 Apr 2026)](https://nltimes.nl/2026/04/29/judge-rules-electricity-grid-haarlemmermeer-full-data-centre-connection-delayed)
- [DCD, The ongoing impact of Amsterdam's data center moratorium](https://www.datacenterdynamics.com/en/analysis/the-ongoing-impact-of-amsterdams-data-center-moratorium/)
- [Worldstream, Power grid congestion in Amsterdam (cites Netbeheer Nederland)](https://www.worldstream.com/en/power-grid-congestion-in-amsterdam-rotterdam-emerges-as-colocation-hub/)
- [Monstadt et al., IJURR (2025), "How Data Centers Have Come to Matter"](https://onlinelibrary.wiley.com/doi/10.1111/1468-2427.13316) [RESEARCH]

**Industry-estimate capacity sources**
- [CBRE, Global Data Center Trends 2026](https://www.cbre.com/insights/reports/global-data-center-trends-2026)
- [CBRE, European Data Centres Figures Q3 2025 (PDF)](https://mediaassets.cbre.com/-/media/project/cbre/shared-site/insights/figures/European-Data-Centres-Figures-Q3-2025/European-Data-Centres-Figures-Q3-2025)
- [CBRE, European Data Centres Outlook 2026](https://www.cbre.com/insights/books/european-real-estate-market-outlook-2026/data-centres)
- [w.media, FLAP-D markets plagued by grid constraints and moratoriums (CBRE)](https://w.media/special-feature-flap-d-markets-plagued-by-grid-constraints-and-moratoriums-cbre/)
- [JLL, EMEA data centre mid-year 2026 report](https://www.jll.com/en-uk/insights/emea-data-centre-report)
- [Data Centre Review, FLAP-D capacity pricing set to rise 12% in 2026 (CBRE, 21 May 2026)](https://datacentrereview.com/2026/05/flap-d-data-centre-capacity-pricing-set-to-rise-12-in-2026/)
- [Knight Frank, Data Centre Atlas 2026 (PDF)](https://www.knightfrank.co.uk/site-assets/research/report-pdfs/data-centres/data-centre-atlas-2026.pdf)
- [Argus, Nordic data centres to support power demand growth](https://www.argusmedia.com/en/news-and-insights/latest-market-news/2806298-nordic-data-centres-to-support-power-demand-growth)
- [Colliers, Data Center Snapshot, Iberian Region (Oct 2025 – Mar 2026)](https://www.colliers.com/en-es/research/data-center-snapshot-iberian-region-oct-2025-mar-2026)
- [MLQ News, Denmark's Energinet halts new large-load grid connections as queue hits 60 GW](https://mlq.ai/news/v2/denmarks-energinet-halts-new-large-load-grid-connections-as-queue-hits-60-gw/)
- [Nordea, Finland: Data Centers — Midas Touch or Achilles' Heel](https://corporate.nordea.com/article/101924/finland-data-centers-midas-touch-or-achilles-heel)
- [Ember, Grids for data centres in Europe (PDF)](https://ember-energy.org/app/uploads/2025/06/Grids-for-data-centres-in-Europe.pdf) [RESEARCH]
- [Bisnow, New rules power back up Ireland's data centre market](https://www.bisnow.com/dublin/news/data-center/new-rules-power-up-irelands-data-centre-market-at-last-135550)

**Internal**
- `docs/research-notes/B-loudoun-geography.md` — source of the ~4,039.6 MW Northern Virginia figure.

---

## 8. Not verified

Explicitly listed rather than guessed. **Nothing in this section should be treated as a
finding.**

### 8.1 Figures I could not reach a primary for

1. **SEAI's 21.2% / 7.0 TWh / 32.9 TWh (2024).** The *Energy in Ireland 2025* PDF returned
   HTTP 403 on the SEAI host and rendered as image-only via a mirror; the SEAI HTML landing
   page also 403'd. These figures come from a **search-result synthesis of SEAI content**, not
   from my own read of the primary. They are internally consistent with the CSO series (§2.2),
   which raises confidence, but **verify against the PDF before publishing.** Same status for
   the "88.2% of demand growth since 2015" attribution.
2. **UK 5.0 TWh / ~2% of demand (2023).** Secondary-sourced. The NESO PDF would not render as
   text. No DESNZ primary reached.
3. **EirGrid AIRAA figures.** The AIRAA 2026–2035 PDF did not render as text. The 9.4 TWh →
   14.6 TWh and 22% → 31% figures are taken from **the CRU's own citation** of them, which is
   an official secondary use but not the EirGrid primary.
3a. **The ~1.7 TWh gap between EirGrid/CRU's 9.4 TWh (2025) and the CSO's measured 7.663 TWh
   (2025) is unexplained.** Whether it reflects an all-island footprint, a wider large-energy-user
   definition, or a stale forecast vintage was **not** determined. The all-island explanation
   alone looks insufficient (Northern Ireland's total consumption is only ~8 TWh). **The
   22%→31% trajectory rests on this base and should not be used until the gap is resolved.**
   Resolving it requires the EirGrid AIRAA primary (item 3).
4. **Finland ~1.6 TWh / just under 2% (2024).** Sourced to Nordea (bank research), not
   Statistics Finland or Fingrid.
5. **Norway 501 MW ≈ 1% of national production.** Industry estimate; denominator is
   *production* not consumption; no SSB or NVE primary reached.

### 8.2 Things I could not find at all

6. **Sweden — no national data-centre electricity consumption figure, in TWh or as a share.**
   Neither Energimyndigheten nor SCB appears to publish one. The only Swedish quantity found
   was ~160.8 MW of *third-party core-and-shell* capacity (Dec 2024), which excludes
   hyperscaler self-build and is not comparable to other countries' figures. **Sweden's first
   mandatory reports (due 15 May 2026, covering 2025) may now exist — worth a follow-up.**
7. **Warsaw / Poland — no MW capacity figure and no national share found.** Warsaw is
   repeatedly described as the CEE leader, but I found no quantity. No PSE figure reached.
8. **Spain and Italy — no national data-centre share of electricity consumption.** Only
   national totals (Spain 255,759 GWh in 2025, REE; Italy 311 TWh in 2025, Terna) and Italy's
   connection-request queue. Neither REE nor Terna appears to publish a data-centre share.
9. **Portugal — no national share.** Only Lisbon metro capacity figures.
10. **Per-market under-construction MW for individual FLAP-D markets.** Only the FLAP-D
    aggregate (~1.4 GW UC) was obtainable. The CBRE quarterly Figures PDFs would not render as
    text; the underlying market-by-market table was not reached.
11. **London total inventory MW (Q1 2026).** CBRE reports +21% YoY growth but no absolute
    total was extractable.
12. **Whether the EU data-centre database publishes anything below member-state aggregate.**
    Annex IV specifies aggregated publication; I did not establish whether any member state
    publishes finer granularity, nor whether researcher access to unaggregated records exists.
    **This is the single highest-value follow-up in this note.**

### 8.3 Active conflicts left unresolved

13. **Dublin/London ~1,150 / ~1,189 MW (H1 2025) vs CBRE's Frankfurt 1,222.5 MW (Q1 2026).**
    Mutually inconsistent on market ordering. Reached only via secondary aggregators
    (sentisight / Gardiner / Bisnow); original attribution unconfirmed. Almost certainly
    different definitions and different vendors. **Do not cite either without pinning the
    primary.**
14. **Ireland "2.88 thousand MW in 2025 → 3.21 thousand MW in 2026"** (Mordor Intelligence).
    Irreconcilable with a Dublin operational figure of ~1,150 MW and with "upcoming capacity
    ~1,300 MW, over 3x current existing" (which implies existing ≈ 400 MW IT) from the same
    search. Three mutually incompatible magnitudes for Irish capacity. **Excluded from the
    body.** Listed here because the PI may encounter it.
15. **Amsterdam total inventory ~649 MW is my own derivation** from CBRE's "+64.3 MW = +11%",
    not a published figure. One extraction pass misread that 64.3 MW *increment* as the
    *total* — a reminder that this specific number is a known trap.

### 8.4 Figures deliberately excluded as unreliable

16. **"Data Centres Use 32% of Ireland's Electricity"** (wattcharger.com, vendor blog). Not
    supported by any official source; CSO reports 23% of metered consumption for 2025 and
    SEAI 21.2% of total demand for 2024. **Excluded.** Noted because it ranks in search
    results and directly contradicts the official figures.
17. **Older Danish forecasts** (DEA 2019 "15% by 2030"; Ea Energianalyse/DEA 2021 "~17% by
    2030"; a 2024 "one-fifth by 2030" reading). Superseded by KF25 (2025); at least one was
    stated against an *energy* rather than *electricity* budget. **Excluded from the body**;
    listed in §3.3 as a vintage trap because they remain widely quoted.
18. **Milan's "4.6 GW pipeline" and Italy's ">50 GW of requests"** are retained in §1.5 but
    explicitly tiered as queue/planning figures. They are **not** capacity forecasts and
    should never be compared against operational MW.
