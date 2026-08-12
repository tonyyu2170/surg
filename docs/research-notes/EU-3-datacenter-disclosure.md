# EU-3: Data-Centre-Specific Energy Data Disclosure in Europe

Research date: 2026-08-11. Scope: what data-centre-**specific** electricity data is publicly available in Europe, at what granularity, and whether a US undergraduate researcher can actually obtain it.

All legal text below was read directly from EUR-Lex / gesetze-im-internet.de HTML, not from summaries. All statistics were pulled from the publishing agency's own release or API where possible. Anything I could not verify is in the **Not verified** section at the bottom — no regulation number, article number, threshold, or deadline in this note is guessed.

---

## Bottom line

**Yes — Europe gives materially better data-centre-specific resolution than the US, on two counts, and both are obtainable.**

1. **Ireland (CSO)** publishes a genuine official statistical series on data-centre metered electricity consumption: **quarterly, national, 2015Q1–2025Q4, free, no registration, machine-readable API**. This is almost certainly the best *official* data-centre electricity statistic in the world. It is national aggregate only — no geography, no facilities.
2. **UK Power Networks (a UK DNO)** publishes **half-hourly per-site load profiles for ~100 identified data centres** from 2023-01-01 onward, CC BY 4.0, on a free-registration open-data portal. This is the only thing found in Europe that is an actual **hourly/half-hourly data-centre load shape dataset**. Sites are anonymised and values are utilisation *ratios*, not MW.

**And the headline negative:** the EU's own European database on data centres — the thing the project was hoping for — is **explicitly closed at facility level by law**, and the Commission has already refused an academic researcher's formal request for exactly that data. Only Member-State-level and Union-level aggregates are public, and the first reporting round covered only 36% of EU data centres.

### Resolution tiers at a glance

| Tier | What exists in Europe | Where | Obtainable? |
|---|---|---|---|
| **Hourly / sub-hourly load profiles** | ~100 anonymised DC sites, half-hourly utilisation ratio, 2023– | UK Power Networks open data | **Yes** — free registration, CC BY 4.0 |
| **Per-facility records (consumption)** | Germany §13 EnEfG per-facility annual publication duty (incl. postcode, total electricity, PUE) | Operator self-publication; RZReg | **Partly** — duty exists, no verified central public index |
| **Per-facility records (capacity / identity only)** | Norway Nkom registry (names, no MW); Finland DIESL census (capacity, independent); UKPN capacity by local authority | National / academic / DNO | **Yes**, but capacity ≠ consumption |
| **Sub-national / regional aggregates** | UKPN operational + pipeline DC capacity (MVA) by local authority district | UK Power Networks | **Yes** — CC BY 4.0 |
| **National annual/quarterly aggregates** | Ireland CSO (quarterly), Netherlands CBS (annual), EU database (annual, MS-level) | Statistics offices / Commission | **Yes** |
| **Nothing DC-specific** | Denmark, Norway, Sweden, Finland statistics offices; ENTSO-E Transparency | — | n/a |

---

## 1. Ireland — CSO "Data Centres Metered Electricity Consumption"

**This is the strongest official data-centre electricity statistic identified anywhere.** Characterised precisely:

- **Publisher:** Central Statistics Office (CSO), Ireland. Series landing page: https://www.cso.ie/en/statistics/energy/datacentresmeteredelectricityconsumption/
- **Latest release:** *Data Centres Metered Electricity Consumption 2025*, published **07 July 2026**. https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/
- **Underlying data source:** ESB Networks (the Irish DSO) — "consumption data from ESB Networks on data centres connected to the mains electricity network in Ireland."
- **Frequency and coverage:** The *release* is annual, but **the underlying table is quarterly**. Verified directly against the CSO PxStat API: table **MEC02**, dimensions `STATISTIC` × `TLIST(Q1)` × `C03907V04659`, with **44 quarters, 2015Q1 through 2025Q4**, and exactly **three categories**: `All metered electricity consumption`, `Data centres`, `Customers other than data centres`.
- **Geographic breakdown: NONE.** Reference area is "State." The MEC02 cube has no county, region, or NUTS dimension. There is no facility-level breakdown and no facility list.

### Most recent figures (computed from the MEC02 API, not from press coverage)

| Year | Data centres (GWh) | All metered (GWh) | DC share |
|---|---|---|---|
| 2015 | 1,240 | 24,599 | 5.04% |
| 2023 | 6,339 | 30,581 | 20.73% |
| 2024 | 6,974 | 31,904 | 21.86% |
| **2025** | **7,662** | **32,987** | **23.23%** |

Recent quarters (GWh, data centres): 2024Q4 1,830 · 2025Q1 1,821 · 2025Q2 1,894 · 2025Q3 1,956 · **2025Q4 1,991**.

(The CSO release rounds 2024 to 6,973 and 2025 to 7,663; my sums of the quarterly cube give 6,974 and 7,662. Rounding, not a discrepancy.)

### Two precision traps — important for how this can be cited

1. **It is *metered* consumption.** The denominator is total *metered* electricity consumption on the network, not total electricity generated or consumed in Ireland. The "23% of electricity" figure that circulates in press is 23% **of metered network consumption**. Behind-the-meter / on-site generation is not addressed in the background notes either way.
2. **Data centres are not a classification in the source data — CSO identifies them heuristically.** From the background notes, CSO identifies data centres from ~2.6 million meters by: examining the business activity of Large Energy Users; "a search for names and aliases of known data centres with a consumption above a half gigawatt hour"; examining customers in specific business parks above 0.5 GWh; examining all meters above 1 GWh annually; plus the CSO Business Register, third-party reports, and internet searches. **No NACE code or standard classification is used.** CSO explicitly warns of undercoverage: "A new data centre may have a relatively low amount of electricity consumption at first and hence may initially be below the search thresholds."

### Access

Fully open, no registration. PxStat API (JSON-stat 2.0), verified working:

```
https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/MEC02/JSON-stat/2.0/en
```

Also mirrored at data.gov.ie: https://data.gov.ie/dataset/mec02-data-centres-metered-electricity-consumption (CSV, JSON-stat, PX, XLSX).

**Verdict for this project:** best-in-class as a *national aggregate* series, and quarterly is finer than anything the US offers. But it is not a load profile and not geographic, so it does not by itself supply what the project needs.

---

## 2. EU — EED Article 12 and Delegated Regulation (EU) 2024/1364

### 2a. The legal architecture — two distinct channels, frequently conflated

Read from primary text, these are **two separate obligations**, and the distinction is the whole answer to the access question:

**Channel A — operator self-publication, national law.** Directive (EU) 2023/1791 (EED recast), **Article 12(1)**, verbatim:

> "By 15 May 2024 and every year thereafter, Member States shall require owners and operators of data centres in their territory with a power demand of the installed information technology (IT) of at least 500kW, to make the information set out in Annex VII publicly available, except for information subject to Union and national law protecting trade and business secrets and confidentiality."

Article 12(2): does not apply to data centres used exclusively for defence and civil protection.
Article 12(3): the Commission establishes the European database; "The European database shall be publicly available on an aggregated level."
Article 12(4): Member States shall *encourage* DCs ≥1 MW to follow the European Code of Conduct on Data Centre Energy Efficiency (non-binding).

**Annex VII** (verbatim, "MINIMUM REQUIREMENTS FOR MONITORING AND PUBLISHING THE ENERGY PERFORMANCE OF DATA CENTRES") requires monitoring and publication of:
- (a) name of the data centre, name of owner and operators, date operations started, **and the municipality where the data centre is based**;
- (b) floor area, installed power, annual incoming and outgoing data traffic, amount of data stored and processed;
- (c) performance over the last full calendar year on KPIs "about, inter alia, energy consumption, power utilisation, temperature set points, waste heat utilisation, water usage and use of renewable energy," basing on CEN/CENELEC EN 50600-4 where applicable.

So on paper, **EU law requires per-facility publication including municipality and energy consumption**. The catch is the trade-secret carve-out in Art. 12(1) and the fact that *how* and *where* publication happens is left entirely to Member States.

**Channel B — the European database, Delegated Regulation (EU) 2024/1364.** Commission Delegated Regulation (EU) 2024/1364 of **14 March 2024**, on the first phase of the establishment of a common Union rating scheme for data centres; OJ L, 2024/1364, **17 May 2024**. ELI: http://data.europa.eu/eli/reg_del/2024/1364/oj

- **Scope (Article 1):** operators of data centres with "an installed information technology power demand of at least 500 kW."
- **Deadlines (Article 3(1)):** "By 15 September 2024, then by 15 May 2025, and every year thereafter." Data covers "the calendar year immediately preceding the reporting year." Reporting goes via a national reporting scheme where the Member State has one, otherwise direct to the European database.
- **First-round leniency (Art. 3(2)–(3)):** for the first reporting period, operators may omit specified Annex II KPIs "for technical reasons" with an explanation; colocation operators may estimate for the first two periods.
- **What is reported (Annex I + II):** DC name; owner and operator name and contact details; **location as a Eurostat LAU code**; DC type (enterprise / colocation / co-hosting); year and month of entry into operation; electrical and cooling redundancy levels; installed IT power demand (PD_IT, kW); total floor area and computer-room floor area; total energy consumption (E_DC); IT equipment energy consumption (E_IT); water input; waste heat reused and average temperature; IT intake air temperature setpoints; renewable energy consumption incl. Guarantees of Origin; plus data traffic and data stored. Annex III defines the sustainability indicators (PUE, WUE, ERF, REF).

### 2b. WHO CAN SEE WHAT — the decisive provision

**Article 5 of 2024/1364, verbatim:**

> "2. The information, and key performance indicators, communicated to the European database, and the data centre sustainability indicators, in accordance with Annex III, shall be made public in an aggregated manner, at Member State and Union level, in accordance with Annex IV.
>
> 3. Member States shall have access to all information and key performance indicators communicated to the European database by data centres in their territory pursuant to Article 3.
>
> 4. The Commission shall have access to all information and key performance indicators communicated to the European database pursuant to Article 3.
>
> 5. The Commission and Member States concerned shall keep confidential all information and key performance indicators for individual data centres that are communicated to the database pursuant to Article 3. Such information shall be considered confidential information affecting the commercial interests of operators and owners of data centres in accordance with Article 4(2) of Regulation (EC) No 1049/2001 … and Article 4(2)(d) of Directive 2003/4/EC … on public access to environmental information."

**This is the single most important sentence in this note.** Article 5(5) pre-designates facility-level records as commercially confidential under *both* the EU access-to-documents regime (Reg. 1049/2001) *and* the Aarhus environmental-information regime (Dir. 2003/4/EC). It closes the two routes a researcher would normally try.

**What IS public — Annex IV, verbatim scope.** Two levels of aggregation only, Member State and Union. Size categories: very small 100–500 kW; small 500–1,000 kW; medium 1–2 MW; large 2–10 MW; very large >10 MW. Published at Member State level: number of reporting DCs; distribution by size category; total installed IT power demand; total energy consumption; total water consumption; average PUE, WUE, ERF, REF (overall, per DC type, per size category), energy-weighted. Per-type/per-size breakdowns are published "only if the respective category contains data from at least three data centres." Same list at Union level.

### 2c. Has the first round happened, and were results published? Yes — and the coverage is poor

Published output: **"Assessment of the energy performance and sustainability of data centres in EU — First technical report," DG ENER, July 2025** (manuscript completed June 2025). https://op.europa.eu/en/publication-detail/-/publication/83be4c3e-5c79-11f0-a9d0-01aa75ed71a1/language-en

Key findings read directly from the PDF:

- **770 data centres reported, out of an estimated 2,161 expected EU-wide = 36% coverage.**
- **Six Member States had zero reporting data centres: Cyprus, Czechia, Estonia, Romania, Slovakia, Slovenia.** Fewer than three data centres reported in five further Member States (so those states get no per-type/per-size figures under the Annex IV ≥3 rule).
- **EU totals (Table 22):** total installed IT power demand **3,738.86 MW**; total energy consumption **14,088 GWh**; total water consumption **6,223,391 m³**.
- **Member State totals (Table 24)**, IT power (MW) / energy (GWh) / water (m³), selected: DE 946.87 / 4,608.53 / 1,841,262 · FR 1,311.43 / 2,416.90 / 399,147 · **IE 315.92 / 1,411.76 / 626,594** · NL 102.76 / 574.87 / 1,356,210 · DK 193.74 / 731.28 / 330,801 · FI 219.67 / 1,091.18 / 8,599 · BE 236.13 / 1,070.95 / 1,240,048 · ES 101.03 / 603.63 / 214,501 · IT 92.02 / 350.24 / 78,351 · SE (from the coverage table) 7 of 103 DCs reported = 7%.
- Estonia submitted KPIs for three DCs but they were excluded because they were data *ranges*, not absolute numbers.

**The coverage problem, quantified.** Ireland reports **1,411.76 GWh** in the EU database. Ireland's own CSO puts Irish data-centre metered consumption at **6,339 GWh in 2023** and **6,974 GWh in 2024**. Even allowing for reference-year ambiguity, **the EU database captures roughly a fifth to a quarter of actual Irish data-centre consumption** (exact ratio depends on reference-year alignment — see Not verified, item 2). Sweden's 7% response rate points the same way. **The European database, in its current state, is not a usable measure of national data-centre load.** It is a compliance artefact with severe self-selection.

There is also an **online dashboard** presenting the Annex IV aggregates: https://link.europa.eu/q7x39t → resolves to https://dashboard.tech.ec.europa.eu/qs_digit_dashboard_mt/public/sense/app/940a61c3-bcfe-47d6-a786-25d93aa63b85/sheet/ZLWpJa/state/analysis/bookmark/381456a5-1044-4047-92f5-671be7ad92c4 (Qlik Sense; I could not render its contents — see Not verified).

Reporting/registration portal (for obligated operators, not researchers): https://policy-reporting-platform.ec.europa.eu/Reporting/web/registration
Commission topic page: https://energy.ec.europa.eu/topics/energy-efficiency/energy-efficiency-targets-directive-and-rules/energy-efficiency-directive/energy-performance-data-centres_en

### 2d. Proof that a researcher cannot get facility-level EU data — a refusal letter

This is not inference. **Charis Papaevangelou, a postdoctoral researcher at the Institute for Information Law (IViR), University of Amsterdam, formally requested exactly this data under Regulation 1049/2001 on 4 July 2025 (case 2025/3469), and was refused on 29 August 2025** by the Director-General for Energy.

Request: the European database for 2023 and 2024 reporting periods; failing that, Greek data; failing that, "the disaggregated and facility-level data … for all data centres in Greece with an installed IT power of at least 500 kW."

Commission's reasoning, verbatim from the refusal letter:

> "Accordingly, the data you requested — namely the disaggregated and facility-level data, where available, for all data centres in Greece with an installed IT power of at least 500 kW — constitutes confidential information as defined in Article 5(5) of the Delegated Regulation."
>
> "Granting public access to this information would pose a real and non-hypothetical risk of seriously undermining the commercial interests of the third parties concerned."
>
> "Therefore, the exception provided for in Article 4(2), first indent of Regulation (EC) No 1049/2001 and in Article 4(2)(d) of Directive 2003/4/EC applies. … In this instance, no compelling arguments have been presented that would demonstrate such an overriding public interest sufficient to outweigh the protection of commercial interests."

Two further findings in the same letter that save time:

- **The Commission holds no pre-2023 data-centre consumption data at all**: "the Commission does not hold any such data."
- **The Commission pushes public availability back to Member States**: Article 12(1) EED "requires Member States to ensure the public availability of the relevant data… **It is therefore the responsibility of each Member State to determine which information can be made publicly accessible** under applicable EU and national laws."

Request record: https://www.asktheeu.org/request/access_to_data_centres_consumpti
Refusal letter (PDF): https://www.asktheeu.org/request/access_to_data_centres_consumpti/response/60793/attach/2/2025%203469%20reply%20EN%20final.pdf

**Operational implication:** do not spend time on an EU-level access request. The refusal is on the record, the legal basis is explicit in the delegated act, and an overriding-public-interest argument was already tried and rejected. **If facility-level EU data is obtainable at all, the route is national, not Brussels.**

---

## 3. Germany — Energieeffizienzgesetz (EnEfG) and the RZReg

Germany has, on paper, **the strongest facility-level disclosure obligation in Europe** — and no verified central public access point. Both halves matter.

Law: Gesetz zur Steigerung der Energieeffizienz in Deutschland (Energieeffizienzgesetz – EnEfG), in force 18 November 2023. https://www.gesetze-im-internet.de/enefg/

### The obligation

**§ 13(1) EnEfG**, verbatim:

> "Betreiber von Rechenzentren sind verpflichtet, bis zum Ablauf des 31. März eines jeden Jahres Informationen über ihr Rechenzentrum nach Maßgabe der Anlage 3 für das vorangegangene Kalenderjahr **zu veröffentlichen und an den Bund zu übermitteln**."

("Operators of data centres are obliged, by the end of 31 March each year, to **publish** information about their data centre in accordance with Annex 3 for the preceding calendar year **and to transmit it to the federal government**.")

Note this is a **duty to publish**, not merely to report — distinct from and stronger than the EU database channel.

**Threshold.** § 3 Nr. 24(a) EnEfG defines *Rechenzentrum* as a structure or group of structures for central housing/operation of IT and network telecom equipment for data storage, processing and transport **"mit einer nicht redundanten elektrischen Nennanschlussleistung ab 300 Kilowatt"** — i.e. **≥300 kW non-redundant rated connected load**, lower than the EU's 500 kW. Phasing (BMWE FAQ): ≥500 kW first due 15 August 2024; 300 kW to <500 kW first due 1 July 2025; annually by 31 March thereafter.

**Anlage 3 (Annex 3), what must be published — per facility:**

1. General: (a) name of the data centre; (b) **name of the owner and operator**; (c) size class by IT connected load (<500 kW, <1 MW, <5 MW, <10 MW, <50 MW, <100 MW, ≥100 MW); (d) **Postleitzahl (postal code) of the data centre**; (e) total building floor area; (f) rated IT connected load and non-redundant rated connected load of the data centre.
2. Operating data for the last full calendar year: (a) **total electricity consumption including own generation, total electricity purchased, and electricity fed back into the supply grid**; (b) renewable share per DIN EN 50600-4-3; (c) quantity and average temperature of measurable/estimable waste heat released to air, water or ground; (d) waste heat delivered to heat offtakers (kWh/yr) and average temperature (°C); (e) quantity of data stored and processed; (f) **PUE** per DIN EN 50600-4-2; (g) energy reuse factor per DIN EN 50600-4-6; (h) cooling system efficiency per DIN EN 50600-4-7; (i) water usage effectiveness per DIN EN 50600-9.

**No aggregation permitted.** The BMWE FAQ: "Können die Informationen mehrerer Rechenzentren eines Betreibers zusammengefasst (aggregiert) berichtet werden? **Nein, jedes Rechenzentrum eines Betreibers ist einzeln zu erfassen.**" ("No, each data centre of an operator must be recorded individually.")

So the *content* mandated for German public disclosure is: **annual total electricity consumption, per facility, with owner name, size class, and postal code.** That is finer than anything in US public data by a wide margin.

### The access problem

**§ 14 EnEfG**, verbatim in full:

> "Die Bundesregierung errichtet ein Energieeffizienzregister für Rechenzentren, in dem die von den Rechenzentren nach § 13 Absatz 1 in Verbindung mit Anlage 3 übermittelten Informationen gespeichert und in eine europäische Datenbank über Rechenzentren übertragen werden."

§ 14 says the register **stores** the data and **transfers it to the European database**. It says **nothing** about the register being publicly viewable or searchable.

Where operators actually publish is left open. The BMWE FAQ states the publication duty *can* be discharged through the register: "**Die Veröffentlichungspflicht kann dabei durch Erteilung der Freigabe zur Publikation der geforderten Daten im Effizienzregister für Rechenzentren erfüllt werden.**" ("The publication obligation can be fulfilled by granting release for publication of the required data in the Efficiency Register for Data Centres.") — note **"kann"**, permissive, and conditioned on the operator granting release.

I found **no public search, list, or download interface** for the RZReg. The register operator is the Bundesstelle für Energieeffizienz (BfEE) at BAFA; its page and the BMWE RZReg landing page link only to the reporting portal (https://rzreg.bmwk.de), FAQs, and data-point guidance — no public data view, no aggregate statistics.

**Honest characterisation:** Germany mandates per-facility public disclosure of annual electricity consumption with postcode, but there is **no verified central index**. In practice the data would have to be collected operator-by-operator from company websites and sustainability reports, with no register of who has published what, and with compliance quality unknown. This is a plausible but labour-intensive route to a German facility-level panel — and a genuinely novel one, since nobody appears to have assembled it.

Sources: § 13 https://www.gesetze-im-internet.de/enefg/__13.html · § 14 https://www.gesetze-im-internet.de/enefg/__14.html · Anlage 3 https://www.gesetze-im-internet.de/enefg/anlage_3.html · BMWE RZReg https://www.bundeswirtschaftsministerium.de/RZReg/rechenzentrums-register.html · BMWE FAQ PDF https://www.bundeswirtschaftsministerium.de/RZReg/Downloads/faq-anforderungen-rechenzentren-im-enefg.pdf · BfEE https://www.bfee-online.de/BfEE/DE/Effizienzpolitik/Energieeffizienzregister_Rechenzentren/energieeffizienzregister_rechenzentren_node.html

---

## 4. Netherlands, Denmark, Norway, Sweden, Finland

Checked for a **separate** data-centre electricity series at each national statistics office / TSO. Summary: **only the Netherlands has one, and it is an occasional custom table, not a standing series.** Nobody in the Nordics has an Irish-style official statistic.

### Netherlands — CBS: yes, but as a "maatwerk" custom table
- *Elektriciteit geleverd aan datacenters, 2017–2024*, CBS, published week 51 of 2025. https://www.cbs.nl/nl-nl/maatwerk/2025/51/elektriciteit-geleverd-aan-datacenters-2017-2024
- **5.1 billion kWh (5.1 TWh) in 2024 = 4.6% of national electricity consumption**; up 37% from 3.73 TWh in 2021. News release: https://www.cbs.nl/nl-nl/nieuws/2025/51/datacenters-verbruiken-4-6-procent-van-de-elektriciteit
- Sourced from network operators (netbeheerders). Roughly 200 data centres in NL; **about 45 of them account for ~90% of the electricity delivered to data centres**.
- **Annual, national only. No provincial/regional breakdown, no size classes, no facility list.** Downloadable Excel. It is *maatwerk* (commissioned custom work), **not a standing StatLine series** — so continuity is not guaranteed. An earlier edition covered 2017–2021 (https://www.cbs.nl/nl-nl/maatwerk/2022/49/elektriciteit-geleverd-aan-datacenters-2017-2021).

### Denmark — no separate official series; hourly industry data exists but buries data centres
- **Statistics Denmark: no data-centre-specific electricity series found.** Danish figures in circulation come from **Energistyrelsen** (Danish Energy Agency) analyses and projections, e.g. *Analyse af datacentrenes elforbrug* (Jan 2022, https://ens.dk/media/4630/download) and *Udviklingen af datacentre og deres indvirkning på…* (Jan 2021, https://ens.dk/media/4312/download). These are **projections and studies, not a measured statistical series**.
- **Energinet's Energi Data Service does publish hourly consumption by industry** — dataset `ConsumptionDK3619IndustryHour`, free open API, no key. **I queried it directly and enumerated all 33 categories.** The finest relevant category is **`JB_JC` = "Telekommunikation & It- og informationstjenester"** (within DK19 "Information og kommunikation"). **Data centres are not separable** — they are pooled with all telecom and IT services. There is no data-centre code.
  - API: `https://api.energidataservice.dk/dataset/ConsumptionDK3619IndustryHour` (note: rate-limited, HTTP 429 on repeated calls).
  - *Possible angle, not a finding:* because Danish hyperscale sites (Apple, Meta, Google) are large relative to the rest of the sector, movements in `JB_JC` may be DC-dominated, so it could support an **indirect/inferential** hourly proxy. That is an inference to be tested, not a DC-specific dataset.

### Norway — a public facility *registry*, but with no energy data
- **Registration duty in force since January 2025** under the Forskrift om datasenter (Regulation on data centres) of 18 December 2024, administered by **Nkom** (Nasjonal kommunikasjonsmyndighet), not the energy regulator. All commercial data centres must register; internal enterprise data centres must register if they subscribe to more than **0.5 MW** electrical power. https://nkom.no/datasenter/registreringsplikt · Regulation text: https://lovdata.no/dokument/SF/forskrift/2024-12-18-3313
- **Public register: https://nkom.no/datasenter/oversikt** — 61 commercial operators listed, **115 registered data centres** including internal ones. **Downloadable CSV.**
- **Published fields: company name, organisation number, and cryptocurrency-mining status (with % of consumption where applicable). That is all.** **No MW capacity, no energy consumption, no per-facility address.** Nkom notes that information about which actors have internal data centres can be security-sensitive.
- **SSB (Statistics Norway): no data-centre-specific electricity statistic found.** SSB's monthly electricity statistics derive from Elhub metering-point data and break out power-intensive manufacturing, not data centres. The circulating figure of **3.7 TWh for "digital infrastructure" in 2024 (2.6% of Norway's ~140 TWh)** comes from a government white paper, not an SSB statistical release. https://www.regjeringen.no/en/documents/the-data-centre-industry-a-sustainable-industry-of-the-future-for-the-digital-norway/id3112356/

### Sweden — none found
SCB publishes electricity consumption by area of use (industry) but **no data-centre category** was found. Separately — and this is evidence about EU-database coverage, **not** an SCB statistic — the DG ENER first-round report's coverage table shows only **7 of 103 expected Swedish data centres reported (7%)**, the worst coverage rate among larger Member States. SCB energy statistics: https://www.scb.se/en/finding-statistics/statistics-by-subject-area/energy/

### Finland — no official series; a strong independent facility census exists
- **Statistics Finland: no separate data-centre electricity series found.**
- The figure in circulation — **~1.6 TWh in 2024, just under 2% of Finnish consumption, projected 5–6 TWh by 2030** — comes from the **Finnish Data Center Association (FDCA)**, an industry body: https://www.fdca.fi/data-centers-are-posing-a-challenge-to-the-electricity-market-but-the-challenge-can-be-overcome/
- **Finnish Data Centre Census 2025** — independent academic work (Kaarlo Liukkonen, Otto Kässi, Vili Lehdonvirta; DIESL / Aalto University and University of Oxford). **40 operational data centre sites identified with locations, operators, and specialisations; verified peak load capacity for 22 facilities totalling 379.5 MW; downloadable Excel.** Built by cross-referencing S&P Capital IQ, Business Finland's data centre list, the Confederation of Finnish Industries' green-investment list, and Data Center Map, then verifying against operator websites and press. https://diesl.eu/finnish-data-centre-census-2025/
  - **This is capacity, not consumption, and it is not official statistics** — but it is a good template for what a facility-level European panel built from open sources looks like, and it is directly citable prior art.

---

## 5. Routes to facility-level data, and whether an academic can actually obtain them

Ranked by realism for this project.

1. **Germany, § 13 EnEfG operator self-publication.** Legally the richest — annual total electricity consumption per facility with postcode. **Obtainable only by manual collection from operator websites**; no central index verified. Highest effort, highest novelty.
2. **UK Power Networks (see §6).** Actually downloadable, actually per-site, actually half-hourly — but anonymised and dimensionless. **Best effort-to-value ratio by a wide margin.**
3. **Open-source facility censuses.** The DIESL Finnish census demonstrates that a credible facility-level list (location, operator, capacity) can be assembled from commercial databases + press + operator disclosures. Data Center Map, S&P Capital IQ, and national investment-promotion lists are the ingredients. **Capacity, not consumption.**
4. **National registers.** Norway's Nkom register gives identity but no energy data. **Not useful for load.**
5. **EU Regulation 1049/2001 request to the Commission. Do not attempt** — already refused on the record for exactly this ask, with the legal basis pre-written into Art. 5(5) of the delegated act.
6. **National access-to-environmental-information requests to Member State authorities.** Art. 5(5) binds "the Commission and Member States concerned" to confidentiality for database records, so this is likely blocked too for the *database* copy. Whether any national authority holds and would release equivalent data outside the database is **not verified** — this is the one untested legal avenue.
7. **Grid-connection / permit records (IED permits, EIA files, connection-offer registers).** Not investigated in depth here. **Critical caution: connection or contracted capacity in MW/MVA is not metered consumption.** Conflating the two would be a real methodological error. Ireland's CRU published a new Large Energy User connection policy (CRU/2025236, decision paper: https://cruie-live-96ca64acab2247eca8a850a7e54b-5b34f62.divio-media.com/documents/CRU2025236_Large_Energy_User_connection_policy_decision_paper.pdf) requiring System Operators to publish an engagement and connection process for data-centre applicants by 31 March 2026 — a possible future transparency source, not a current dataset.

---

## 6. Load profiles (hourly shapes) — the thing the project actually needs

**One real find, and it is not in the EU.**

### UK Power Networks — "Data Centre Demand Profiles"

> **⚠️ SUPERSEDED IN PART — see `docs/sources/ukpn-api-constraints.md` (2026-08-11).**
> An account was created and the API probed directly. **The access
> question below is CLOSED: the data does download.** But four claims in
> this section are **wrong**, having been written from metadata alone:
> (1) the ratio is *not* bounded in [0,1] — it reaches 3.99; (2)
> `local_timestamp` does *not* carry British local time — it is UTC;
> (3) all-zero sites were *not* excluded — 13.1 % of rows are zero and
> four sites are entirely dead; (4) `ukpn-large-demand-list` *cannot* be
> filtered to data-centre demand types. Trust the constraints doc over
> this section wherever they disagree.

- Portal: https://ukpowernetworks.opendatasoft.com — dataset id `ukpn-data-centre-demand-profiles`
- **5,442,348 records**, last modified **2026-08-01** (actively maintained). Licence **CC BY 4.0** (https://creativecommons.org/licenses/by/4.0/).
- **Half-hourly load profiles of identified data centres within UK Power Networks' licence areas** (London, East and South East England), using actual demand data from connected sites, **from 1 January 2023 onwards**.
- **Fields:** `cleansed_voltage_level`, `anonymised_data_centre_name`, `dc_type`, `local_timestamp`, `utc_timestamp`, `hh_utilisation_ratio`.

**Methodology, from the dataset description:** "Nearly 100 operational data centre sites (and at least 10 per voltage level) were identified through internal desktop exercises and corroboration with external sources." Their addresses, connection points and MPANs were identified via internal systems; half-hourly smart-meter import data (active and reactive power) were retrieved and apparent power computed via the power triangle. Where a site has multiple meter points, observed imports are summed and compared against summed maximum import capacity:

> % Utilisation = SUM(S_MPAN half-hourly observed import) / SUM(S_MPAN Maximum Import Capacity), where S = apparent power in kVA

Sites with utilisation consistently 0% across the year were excluded. `dc_type` (enterprise vs colocated) is **inferred** by UKPN from address and customer name — an estimate, not a declaration.

**What this gives you, precisely:**
- ✅ **Per-site** (each anonymised site is a separate identifier), **half-hourly**, **multi-year (2023–2026)**, **~100 data centres**, **openly licensed**.
- ❌ **No absolute MW.** Values are a dimensionless ratio in [0,1].
- ❌ **No location.** Anonymised: only voltage level and inferred DC type survive.
- ⚠️ **The denominator is contractual maximum import capacity, not nameplate IT load.** Consequence: **ratios are comparable across sites as *shapes*, not as *levels*.** A site at 0.4 is not necessarily "less loaded" than one at 0.7 in any physical sense; it may simply have contracted more headroom. Any cross-site level comparison needs an explicit assumption about capacity-contracting behaviour.
- ⚠️ **Distribution-connected only.** Transmission-connected hyperscale sites are outside a DNO's metering, so the largest facilities may be systematically absent.

**Jurisdiction note:** this is **UK, not EU**. It exists because of a DNO open-data decision under the GB regulatory framework, **not** because of EED Art. 12 or 2024/1364. It has no relationship to the EU scheme, and there is no reason to expect an EU equivalent to appear.

**Access — the one open item.** Dataset *metadata* and schema are readable anonymously via the API. **Records are not**: I verified that `/api/explore/v2.1/catalog/datasets/ukpn-data-centre-demand-profiles/records` returns HTTP 403 `ForbiddenAccess` unauthenticated, and `/exports/csv` returns a header row with zero data rows. The portal displays "PLEASE LOGIN TO VIEW DATASETS." Per UKPN, **registration is free** — "registration is recommended and absolutely free"; the catalogue is browsable without registering but "access to data tables requires registration." Accounts inactive for a year are removed. **I did not create an account, so I have not confirmed the data actually downloads post-registration.** This should be the very first thing tested — it is a 5-minute check that determines whether this whole thread is live.
  - Terms: https://ukpowernetworks.opendatasoft.com/terms/terms-and-conditions/ · Portal overview: https://www.ukpowernetworks.co.uk/our-company/open-data-portal

### Related UKPN datasets (same portal, all CC BY 4.0)

- **`ukpn-data-centres-by-local-authority`** — 45 records, modified 2026-04-24. **Operational and pipeline data-centre capacity in MVA, aggregated to local authority district**, using UKPN's internal committed-projects system plus ONS geography. Fields: `local_authority_district_name`, `county_and_unitary_authority_name`, `operational_data_centre_capacity_mva`, `pipeline_data_centre_capacity_mva`. **This is a genuine sub-national geographic breakdown of data-centre capacity** — the only one found in Europe. Capacity, not consumption.
- **`ukpn-large-demand-list`** — 496 records, modified 2025-11-04. Anonymised list of live, committed import projects ≥5,000 kVA including BESS. Fields: `licence_area`, `grid_supply_point`, `anonymised_name`, `demand_technology_type`, `required_import_capacity_kva`, `application_date`. **Grid supply point is retained** — so this has locational information at GSP level, and can be filtered to data-centre demand types. Useful for pipeline/interconnection-queue analysis.
- **`ukpn-data-centre-utilisation`** — **archived, 0 records.** Superseded by the demand-profiles dataset. Noted so it isn't chased.

### Everything else on load profiles — negative

- **Other GB DNOs:** I searched Northern Powergrid's open-data portal via the same API and found **no data-centre dataset** (only an unrelated gas-pipelines match). SSEN's data API returned HTTP 403 to automated access. **UKPN appears to be unique among GB DNOs** in publishing data-centre-specific profiles. This is worth a manual re-check on SSEN, NGED, SP Energy Networks and ENWL portals before concluding.
- **Ireland:** no half-hourly or hourly data-centre demand dataset from EirGrid, SEAI, or CSO. **CSO's quarterly MEC02 is the finest DC-specific time resolution available in Ireland**, and quarterly is far too coarse for load-shape work.
- **Denmark:** hourly by industry exists but data centres are not separable (see §4).
- **EU database:** annual only, by design. Annex II collects annual totals; there is no time-series or sub-annual element anywhere in 2024/1364.
- **ENTSO-E Transparency Platform:** publishes national/bidding-zone total load at hourly or finer resolution. **This is not data-centre-specific in any way** and should not be listed as a data-centre data source. It is only useful as a denominator.
- **Adjacent but not data-centre-specific:** ELMAS, a one-year open dataset of hourly load profiles for 424 French industrial and tertiary sectors from 55,730 customers (https://www.nature.com/articles/s41597-023-02542-z). Worth a look for method and for whether any sector maps near-cleanly to data centres, but it is sector-level and not a data-centre dataset.

---

## Sources

**Ireland**
- CSO series landing page — https://www.cso.ie/en/statistics/energy/datacentresmeteredelectricityconsumption/
- CSO, *Data Centres Metered Electricity Consumption 2025*, published 07 July 2026 — https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/
- Key findings — https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/keyfindings/
- Background notes (identification method) — https://www.cso.ie/en/releasesandpublications/ep/p-dcmec/datacentresmeteredelectricityconsumption2025/backgroundnotes/
- Methodology / metadata — https://www.cso.ie/en/methods/energy/datacentresmeteredelectricityconsumption
- PxStat MEC02 API (JSON-stat 2.0) — https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/MEC02/JSON-stat/2.0/en
- data.gov.ie mirror — https://data.gov.ie/dataset/mec02-data-centres-metered-electricity-consumption
- CRU Large Energy User connection policy decision (CRU/2025236) — https://cruie-live-96ca64acab2247eca8a850a7e54b-5b34f62.divio-media.com/documents/CRU2025236_Large_Energy_User_connection_policy_decision_paper.pdf

**EU legal texts and outputs**
- Directive (EU) 2023/1791 (EED recast), Art. 12 and Annex VII — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32023L1791 (OJ L 231, 20.9.2023, p. 1)
- Commission Delegated Regulation (EU) 2024/1364, 14 March 2024 — https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=OJ:L_202401364 · ELI http://data.europa.eu/eli/reg_del/2024/1364/oj
- DG ENER, *Assessment of the energy performance and sustainability of data centres in EU — First technical report*, July 2025 — https://op.europa.eu/en/publication-detail/-/publication/83be4c3e-5c79-11f0-a9d0-01aa75ed71a1/language-en
- Commission topic page, energy performance of data centres — https://energy.ec.europa.eu/topics/energy-efficiency/energy-efficiency-targets-directive-and-rules/energy-efficiency-directive/energy-performance-data-centres_en
- Aggregated dashboard (short link) — https://link.europa.eu/q7x39t
- Reporting platform registration (operators) — https://policy-reporting-platform.ec.europa.eu/Reporting/web/registration
- FOI request 2025/3469 record — https://www.asktheeu.org/request/access_to_data_centres_consumpti
- Commission refusal letter, Ref. Ares(2025)7003195, 29 Aug 2025 — https://www.asktheeu.org/request/access_to_data_centres_consumpti/response/60793/attach/2/2025%203469%20reply%20EN%20final.pdf

**Germany**
- EnEfG full text — https://www.gesetze-im-internet.de/enefg/
- § 3 (definitions, 300 kW) — https://www.gesetze-im-internet.de/enefg/__3.html
- § 11 (PUE targets) — https://www.gesetze-im-internet.de/enefg/__11.html
- § 12 (energy management systems) — https://www.gesetze-im-internet.de/enefg/__12.html
- § 13 (publication duty) — https://www.gesetze-im-internet.de/enefg/__13.html
- § 14 (RZReg) — https://www.gesetze-im-internet.de/enefg/__14.html
- Anlage 3 (what must be published) — https://www.gesetze-im-internet.de/enefg/anlage_3.html
- BMWE RZReg landing page — https://www.bundeswirtschaftsministerium.de/RZReg/rechenzentrums-register.html
- BMWE FAQ (publication route, phasing) — https://www.bundeswirtschaftsministerium.de/RZReg/Downloads/faq-anforderungen-rechenzentren-im-enefg.pdf
- BfEE register page — https://www.bfee-online.de/BfEE/DE/Effizienzpolitik/Energieeffizienzregister_Rechenzentren/energieeffizienzregister_rechenzentren_node.html
- BAFA notice on register start — https://www.bafa.de/SharedDocs/Kurzmeldungen/DE/Energie/20240319_bfee_enefg.html

**Netherlands / Nordics**
- CBS, *Elektriciteit geleverd aan datacenters 2017–2024* — https://www.cbs.nl/nl-nl/maatwerk/2025/51/elektriciteit-geleverd-aan-datacenters-2017-2024
- CBS news release — https://www.cbs.nl/nl-nl/nieuws/2025/51/datacenters-verbruiken-4-6-procent-van-de-elektriciteit
- CBS earlier edition 2017–2021 — https://www.cbs.nl/nl-nl/maatwerk/2022/49/elektriciteit-geleverd-aan-datacenters-2017-2021
- Energinet Energi Data Service, `ConsumptionDK3619IndustryHour` — https://api.energidataservice.dk/dataset/ConsumptionDK3619IndustryHour
- Energistyrelsen, *Analyse af datacentrenes elforbrug* (Jan 2022) — https://ens.dk/media/4630/download
- Energistyrelsen, data-centre development analysis (Jan 2021) — https://ens.dk/media/4312/download
- Nkom, registration duty — https://nkom.no/datasenter/registreringsplikt
- Nkom, public register of registered operators and data centres — https://nkom.no/datasenter/oversikt
- Forskrift om datasenter, 18 Dec 2024 — https://lovdata.no/dokument/SF/forskrift/2024-12-18-3313
- Norwegian government white paper on the data-centre industry — https://www.regjeringen.no/en/documents/the-data-centre-industry-a-sustainable-industry-of-the-future-for-the-digital-norway/id3112356/
- SSB electricity statistics — https://www.ssb.no/en/energi-og-industri/energi/statistikk/elektrisitet
- SCB energy statistics — https://www.scb.se/en/finding-statistics/statistics-by-subject-area/energy/
- FDCA on Finnish data-centre consumption — https://www.fdca.fi/data-centers-are-posing-a-challenge-to-the-electricity-market-but-the-challenge-can-be-overcome/
- DIESL, *Finnish Data Centre Census 2025* — https://diesl.eu/finnish-data-centre-census-2025/

**United Kingdom**
- UKPN open data portal — https://ukpowernetworks.opendatasoft.com
- `ukpn-data-centre-demand-profiles` metadata API — https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-data-centre-demand-profiles
- `ukpn-data-centres-by-local-authority` metadata API — https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-data-centres-by-local-authority
- `ukpn-large-demand-list` metadata API — https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-large-demand-list
- UKPN portal terms and conditions — https://ukpowernetworks.opendatasoft.com/terms/terms-and-conditions/
- UKPN open data overview — https://www.ukpowernetworks.co.uk/our-company/open-data-portal

**Other**
- ELMAS French sectoral hourly load profiles — https://www.nature.com/articles/s41597-023-02542-z

---

## Not verified

Explicitly flagged. None of these should be treated as established.

1. **UKPN post-registration access.** I confirmed the records and export endpoints return 403 / empty without authentication, and that UKPN states registration is free. **I did not create an account and have not confirmed the data downloads.** Also unconfirmed: the exact number of distinct anonymised sites, the true end date of the series, and whether registration imposes any nationality, institutional, or use restriction beyond CC BY 4.0 attribution. **Test this first.**
2. **Reference year of the EU report's Table 22/24 figures.** Article 3 says data covers "the calendar year immediately preceding the reporting year," which makes the first period calendar 2023. The report describes it as "the first reporting period of 2024" and pools May and September 2024 submissions. I could not pin the reference year unambiguously in the document. **The Ireland comparison (1,411.76 GWh in the EU database vs. CSO's 6,339 GWh for 2023 / 6,974 GWh for 2024) is directionally solid but the exact ratio depends on this alignment.**
3. **Contents of the Commission's aggregated dashboard.** The Qlik Sense app did not render to text for me. I could not confirm which years and countries it displays, or whether it offers CSV export. The Annex IV list defines its *maximum* scope; actual contents unverified.
4. **Whether any Member State has built a national public register under EED Art. 12(1).** The Commission's refusal letter puts the public-availability decision squarely on Member States, but I checked only Germany in depth. **Ireland, the Netherlands, Denmark, Sweden and Finland were not checked for a national Art. 12(1) publication portal.** This is the highest-value unexplored thread in the note — if any Member State built a public national register, it would be facility-level and public.
5. **Whether German operators are actually complying with the § 13 publication duty, and where.** No central index found; I did not sample operator websites. Compliance rate, publication format, and findability are all unknown. It is also unverified whether BfEE/BAFA publishes any aggregate statistics from the RZReg.
6. **Whether the RZReg has any public-facing view.** § 14 does not provide for one and I found none, but I did not access https://rzreg.bmwk.de itself (it is a login portal).
7. **Other GB DNOs.** I checked Northern Powergrid via API (nothing) and SSEN returned 403 to automated access. **NGED, SP Energy Networks and ENWL were not checked at all.** If another DNO publishes comparable profiles, coverage would improve substantially.
8. **Whether an access-to-environmental-information request to a national authority could succeed** where the EU-level one failed. Art. 5(5) binds Member States too for database records, but the position on nationally-held equivalents is untested.
9. **Danish `JB_JC` as a data-centre proxy.** The suggestion that Danish hyperscale load may dominate that category is my inference from sector structure, not something I measured. Untested.
10. **Grid-connection and permit routes** (IED permits, EIA files, connection registers) were not investigated. Note again that connection/contracted MW is not metered consumption.
11. **CSO denominator treatment of behind-the-meter generation.** The background notes do not state whether on-site generation is excluded from either numerator or denominator. Treated here as "metered network consumption only," which follows from the ESB Networks source, but is not explicitly confirmed in the methodology text.
