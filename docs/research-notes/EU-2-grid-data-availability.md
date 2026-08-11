# EU-2: European electricity load & price data availability

**Date:** 2026-08-11
**Motivation:** Scoping a possible European extension of the load-level vs. load-volatility
price diagnostic currently run on eight North American markets (PJM, ERCOT, NYISO, CAISO,
IESO, MISO, ISO-NE, SPP).
**Status:** Research memo. No scope decision made here.
**Verification convention:** claims below are sourced inline. Anything I could not confirm
from a primary source is flagged ⚠️ and repeated in §9 "Not verified."

---

## 1. Headline — read this first

**The finest spatial unit at which European load AND price are both published is the
bidding zone, and that is a hard floor.** There is no European day-ahead market with
nodal/locational marginal pricing. Single Day-Ahead Coupling (SDAC) is zonal by
construction — one price per bidding zone per market time unit, cleared by the common
EUPHEMIA algorithm. Nothing in Europe is comparable to a PJM pnode or an ERCOT settlement
point.

The binding constraint is not data availability, it is **the join**. Most European TSOs
publish load at a *finer* unit than the price exists at, which is useless for an own-zone
regression:

- **France:** RTE publishes consumption per French metropolitan region — and even per major
  metropolitan *area* — at 15-minute resolution. France is **one** bidding zone. None of
  that regional load has a matching regional price. ⚠️ (region count not verified)
- **Germany:** load is published per each of the four control areas (50Hertz, Amprion,
  TenneT DE, TransnetBW). DE-LU is **one** bidding zone. Same mismatch.
- **Spain:** rich, high-frequency demand data from REE/ESIOS. **One** bidding zone.
- **Ireland:** EirGrid/SONI publish demand for Ireland, Northern Ireland, and All-Island
  separately. SEM is **one** bidding zone spanning both jurisdictions. Same mismatch.

**Only four countries have a within-country zonal price cross-section**, and in all four
the load is published at the matching unit:

| Country | Zones | Zone names |
|---|---|---|
| Italy | 7 | North, Centre-North, Centre-South, South, Calabria, Sicily, Sardinia |
| Norway | 5 | NO1–NO5 |
| Sweden | 4 | SE1–SE4 |
| Denmark | 2 | DK1, DK2 |

**Every other SDAC country is a single bidding zone.** So the entire European within-country
cross-section is 7 + 5 + 4 + 2 = **18 zones, in 4 countries**; everywhere else contributes
exactly one panel unit each, no matter how granular its load data is.

**Italy is the single best European analogue** to a US zonal ISO: 7 zones, load
and price both published per zone, one TSO (Terna) with a documented REST API, plus an
exchange (GME) publishing zonal day-ahead prices.

**Second headline, and it is a real one:** SDAC switched from a 60-minute to a **15-minute
Market Time Unit on trading day 30 September 2025 (delivery day 1 October 2025)** — all
bidding zones and borders simultaneously, **with one exception: Ireland (SEM), which went
to 30-minute rather than 15-minute** (§3.3). European day-ahead prices are now natively
quarter-hourly. This is a structural break dead in the middle of any panel that spans it,
and it is also an opportunity: a 15-minute price series against 15-minute load is a *finer*
temporal resolution than any US day-ahead market offers.

**The tradeoff to put in front of the PI:** Europe trades **spatial** granularity for
**temporal** granularity relative to the US. You lose nodal entirely and get thin
within-country cross-sections; you gain a 15-minute native MTU (post-Oct-2025) and a large
*pooled* cross-section — every SDAC zone clears in one coupled auction under one algorithm
(EUPHEMIA), which is a defensible pooling argument that no US multi-ISO panel can make. But
pooling across countries imports currency, tax, levy, and market-design heterogeneity that
the US panel does not have.

---

## 2. Q1 — ENTSO-E Transparency Platform

The pan-European hub, mandated by **Commission Regulation (EU) No 543/2013**. This is the
only pipeline where load and price share zone definitions, so it is the baseline against
which every national source in §4 should be judged.

### 2.1 What the regulation requires (the legal floor)

This matters more than the platform's marketing, because it defines the guaranteed unit
and resolution:

- **Article 6 (load):** TSOs must submit total load **"per market time unit"** for **each
  bidding zone** — actual total load plus day-ahead/week-ahead/month-ahead/year-ahead
  forecasts. Actual load is due **"no later than one hour after the operating period."**
- **Article 12 (day-ahead prices):** **"for every market time unit the day-ahead prices in
  each bidding zone (Currency/MWh)"**, published **"no later than one hour after gate
  closure."**
- **"Bidding zone"** is defined as *"the largest geographical area within which market
  participants are able to exchange energy without capacity allocation."*
- **"Market time unit"** is *"the period for which the market price is established."*

So load and price are guaranteed to exist at the same unit (bidding zone) at the same
resolution (market time unit). That is the whole reason ENTSO-E is the right starting point.
[Regulation 543/2013, EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013R0543)

### 2.2 Geographic units actually offered

The TP lets you select by **control area (CTA)**, **bidding zone (BZN)**, or **country**.
[TP intro guide](https://transparencyplatform.zendesk.com/hc/en-us/articles/13772306625428-Introduction-guide-for-new-users)

The EIC area list shows the full area-type taxonomy — the same physical territory can carry
several codes with different roles. Concrete examples straight from the list:

- `10Y1001A1001A82H` = `BZN|DE-LU`, `MBA|DE-LU`, `SCA|DE-LU` — Germany-Luxembourg **as a
  bidding zone**.
- `10YDE-VE-------2` = `CTA|DE(50Hertz)`, `LFA|DE(50Hertz)`, `SCA|DE(50Hertz)` — 50Hertz
  **as a control area only**. There is no `BZN` on it. This is exactly why German
  control-area load cannot be paired with a control-area price: no such price exists.
- `10Y1001A1001A59C` = `BZN|IE(SEM)`, `MBA|IE(SEM)`, `SCA|IE(SEM)`, `SNA|Ireland` — the
  **single all-island bidding zone**, while `10YIE-1001A00010` is `CTA|IE` /
  `MBA|SEM(EirGrid)` and `10Y1001A1001A016` is `CTA|NIE` / `MBA|SEM(SONI)`. One price zone,
  two control areas.
- Italy carries a full set of `BZN|IT-North`, `BZN|IT-Centre-North`, `BZN|IT-Centre-South`,
  `BZN|IT-South`, `BZN|IT-Calabria`, `BZN|IT-Sicily`, `BZN|IT-Sardinia` **each with a
  matching `SCA|` and `MBA|`** — i.e. Italy is the one large country where the zone is
  simultaneously a price unit and a load-reporting unit.
- The list also still contains **retired/legacy zones** (`BZN|IT-Brindisi`, `IT-Foggia`,
  `IT-Priolo`, `IT-Rossano` — the four eliminated production poles; `BZN|DE-AT-LU` — the
  pre-split German-Austrian zone) and **virtual border zones** (`BZN|IT-North-FR`,
  `IT-North-CH`, `IT-GR`, `GB(IFA)`). Do not count these as real load/price zones.

[Area List with EIC](https://transparencyplatform.zendesk.com/hc/en-us/articles/15885757676308-Area-List-with-Energy-Identification-Code-EIC)

### 2.3 API — endpoint, registration, rate limits

- **Production endpoint:** `https://web-api.tp.entsoe.eu/api` (HTTPS only). Test/IOP
  environment: `https://web-api.tp-iop.entsoe.eu/api` (holds less data).
  [Request Endpoint](https://transparencyplatform.zendesk.com/hc/en-us/articles/15696677194644-Request-Endpoint)
- **Registration is required, free, and has a human-in-the-loop step.** The documented
  procedure is: (1) register at `https://transparency.entsoe.eu/` and verify by email;
  (2) **email `transparency@entsoe.eu` with "RESTful API access" in the subject line and
  your registered email address in the body**; (3) *"You will be granted within 3 working
  days and will receive an email"*; (4) log in, go to **My Account**, generate a security
  token.
  [How to get security token](https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token)
  → **Practical note: start this before you need it. Budget 3 working days.**
- **Rate limit: 400 requests per minute per user account (API token).** Enforcement is
  *per token, not per IP* — under the current TP R3 API, IP-based banning was removed.
  Exceeding it *"may temporarily ban the token"*; bans are temporary with automatic
  unbanning *"after approximately 10 minutes."* ENTSO-E's own recommendation is
  client-side throttling at *"6–7 req/sec on average, with burst handling."* A distributed
  job sharing one token aggregates against the same 400/min.
  [API Rate Limit](https://transparencyplatform.zendesk.com/hc/en-us/articles/12783148966036)
- **Per-request limits (verified verbatim in the Postman reference):**
  *"**Request limit:** Each request may cover a period of up to 1 year."* and
  *"**Response limit**: A maximum of 100 TimeSeries elements is returned per XML
  response."* → A multi-year, multi-zone pull is inherently a loop of year-sized requests;
  budget request counts against the 400/min ceiling accordingly.
- **Time interval is mandatory on every request** — it is the primary mechanism limiting
  response size. Parameter names are **case sensitive**. Omitting an optional attribute is
  treated as requesting all options.
  [Request Parameters](https://transparencyplatform.zendesk.com/hc/en-us/articles/15696716612372-Request-Parameters)
- **Document type codes:** `A65` = System total load; `A44` = Price document (day-ahead
  prices use `A44` with `processType=A01`). ⚠️ Confirm against the Postman reference before
  coding — see §9.
- **Reference documentation** now lives in the **Manual of Procedures (MoP)**; ENTSO-E
  specifically recommends **MoP Ref2 (Detailed Data Description)** and **MoP Ref19
  (Transparency Platform Data Extraction Process)** for data consumers.
  [Reference Documentation](https://transparencyplatform.zendesk.com/hc/en-us/articles/12784099471764-Reference-Documentation) ·
  [MoP](https://www.entsoe.eu/data/transparency-platform/mop/)

**Documentation trap (verified 2026-08-11):** the legacy static-content URLs are dead.
`https://transparency.entsoe.eu/content/static_content/Static%20content/web%20api/Guide.html`
returns HTTP 400 with `URI_FORMAT_ERROR`, and the old `RestfulAPI_IG.pdf` download path
returns an HTML shell, not a PDF. Many blog posts and older papers still cite these. **The
live documentation is the Zendesk knowledge base**
(`transparencyplatform.zendesk.com/hc/en-us`) plus the
[Postman collection](https://documenter.getpostman.com/view/7009892/2s93JtP3F6). The
platform was rebuilt ("TP R3") between 2023 and 2025.
[Renewed TP announcement](https://www.entsoe.eu/events/2025/10/29/webinar-invitation-discover-the-new-entso-e-transparency-platform/)

### 2.4 History depth

- The Transparency Platform **launched 5 January 2015**, and platform-native data
  generally starts there.
- Pre-2015 data (2011–2014) that previously lived on `entsoe.net` is reportedly available
  through a **"Data Pre-5.1.15"** section of the TP. ⚠️ I did not verify this section
  still exists on the rebuilt TP R3 — see §9.
- For deeper load history, the separate **ENTSO-E Power Statistics** collection (the old
  Data Portal lineage) is the usual route. ⚠️ Not verified in this pass; §9.

**Practical read: assume ~2015 → present (≈11 years) is the safe, uniform window for
ENTSO-E load+price.** That is shallower than several of the NA panels (IESO zonal load
reaches 2003) but comfortably deep for an hourly panel.

### 2.5 Known data-quality problems

There is a peer-reviewed review of exactly this, and it should be cited rather than forum
complaints:

> Hirth, L., Mühlenpfordt, J., & Bulkeley, M. (2018). "The ENTSO-E Transparency Platform —
> A review of Europe's most ambitious electricity data platform." *Applied Energy*, 225,
> 1054–1067.
> [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0306261918306068) ·
> [open PDF](https://neon.energy/Hirth-Muehlenpfordt-Bulkeley-2018-ENTSO-E-Transparency-Platform.pdf)

The finding most directly relevant to this project: **"Actual Total Load" (6.1.A) values
are inconsistent with other load sources, including ENTSO-E's own Power Statistics, with
deviations often exceeding 10%.** The paper documents a broader range of quality and
usability shortcomings and recommends governance changes.

Additional quality issues to plan for (⚠️ these are standard practitioner cautions, not all
individually source-verified here — see §9):
- **DST handling** — duplicated and missing hours at clock changes; the TP itself supports
  WET/CET/EET display plus UTC, and ENTSO-E's own docs warn that a "day" in CET is
  23:00–23:00 UTC in winter and 22:00–22:00 UTC in summer. **Pull everything in UTC.**
- **Gaps and silent revisions** — values can be republished after the fact.
- **Structural breaks at zone reconfigurations** — two matter for any pre-2021 panel:
  - **The German-Austrian split, effective 1 October 2018.** The combined `DE-AT-LU` zone
    became separate `DE-LU` and `AT` zones, with congestion management introduced on the
    DE-AT border. Announced 28 October 2016 with two years' lead time, following ACER's
    November 2016 decision on Capacity Calculation Regions; driven by unplanned loop flows
    through PL/CZ/SK/HU. **A German price series spanning 2018 changes zone identity
    mid-stream** — `BZN|DE-AT-LU` (`10Y1001A1001A63L`) before, `BZN|DE-LU`
    (`10Y1001A1001A82H`) after.
    [TenneT — go-live of DE-AT congestion management](https://www.tennet.eu/tinyurl-storage/detail/go-live-of-congestion-management-on-the-german-austrian-bidding-zone-border-de-at-bzb-on-1st-of-oc/)
  - **The Italian zone reform, effective 1 January 2021** (§3.2).
- **Mixed resolutions across zones** — different countries report load at different
  resolutions (§6.3), so a naive concatenation produces a ragged panel.

---

## 3. Q2 — Spatial granularity (the make-or-break question)

### 3.1 Is there any nodal/LMP market in Europe? No.

- **SDAC is zonal by construction.** It couples wholesale markets through the common
  **PCR EUPHEMIA** algorithm, producing one price per bidding zone per MTU. The regulation
  itself defines the publication unit as the bidding zone (§2.1).
  [SDAC — ENTSO-E](https://www.entsoe.eu/network_codes/cacm/implementation/sdac/)
- **No European day-ahead market publishes nodal prices.** Nodal pricing is an active
  *policy debate* (ACER's bidding-zone review, academic work on zonal-vs-nodal for
  Germany), not an operating arrangement.
  [Bidding Zone Review — ENTSO-E](https://www.entsoe.eu/network_codes/bzr/) ·
  [ACER on alternative bidding zone configurations](https://www.acer.europa.eu/news-and-events/news/acer-has-decided-alternative-electricity-bidding-zone-configurations)
- **Poland** — the case most often mistaken for nodal. PSE's balancing market reform
  entered into force **14 June 2024**, moving imbalance settlement to **15-minute**
  intervals with single-price settlement, and dispatch uses multi-part unit bids that are
  *locationally specific*. **But Poland remains a single bidding zone and the day-ahead
  price is a single national zonal price.** Locational elements in *unit dispatch /
  balancing* are not LMP and are not a day-ahead price. Do not let this get written up as
  nodal.
  [PSE report — market integration](https://raport.pse.pl/en/economic-and-market-impact/integration-of-the-polish-market-with-european-markets) ·
  [Dexter Energy on the reform](https://dexterenergy.ai/news/polands-balancing-market-reform-what-short-term-power-traders-can-expect/)
  ⚠️ The 14 June 2024 date and the single-price CEN mechanism come from secondary sources;
  confirm against PSE before citing — §9.
- **Italy** — has *multiple day-ahead zones* (below) plus a separate ancillary services
  market (MSD) settled pay-as-bid at unit level. MSD is **not** an LMP and does not give
  you a locational energy price.  ⚠️ MSD detail not verified in this pass — §9.
- ⚠️ **No nodal pilot scheme verified anywhere in Europe.** I found policy discussion of
  "pilot regions" in the academic literature but no operating pilot. Treat "there is no
  nodal pricing in Europe" as the working assumption — §9.

### 3.2 Zone counts by country

**Multi-zone countries (the only within-country cross-sections available):**

- **Italy — 7 zones since 1 January 2021:** North (NORD), Centre-North (CNOR),
  Centre-South (CSUD), South (SUD), **Calabria (CALA)**, Sicily (SICI), Sardinia (SARD).
  The reform ran from 2018 and cut the configuration from 10 zones to 7: the four virtual
  **production poles Priolo, Foggia, Brindisi and Rossano were eliminated** (grid capacity
  expansion) and **Calabria was created** to reflect renewable-driven flows. Umbria moved
  from Centre-North to Centre-South.
  [Terna Lightbox — the new electricity market zones](https://lightbox.terna.it/en/insight/new-electricity-market-zones) ·
  [Terna zonal configuration review (2018)](https://download.terna.it/terna/0000/1033/93.PDF)
  → **This is a structural break on 2021-01-01. A panel starting before 2021 must handle
  the old 10-zone roster.**
- **Norway — 5:** NO1–NO5 (EIC codes `10YNO-1--------2` … `10Y1001A1001A48H`).
- **Sweden — 4:** SE1–SE4 (`10Y1001A1001A44P` … `10Y1001A1001A47J`).
- **Denmark — 2:** DK1, DK2 (`10YDK-1--------W`, `10YDK-2--------M`).

**Single-zone countries** (one price for the whole country): Austria, Belgium, Bulgaria,
Croatia, Czech Republic, Estonia, Finland, France, Germany-Luxembourg, Greece, Hungary,
**Ireland (SEM — the whole island, IE + NI, is one zone)**, Latvia, Lithuania, Netherlands,
Poland, Portugal, Romania, Slovakia, Slovenia, Spain.

**Great Britain** left SDAC in January 2021 and is a separate single-zone market.
[SDAC — ENTSO-E](https://www.entsoe.eu/network_codes/cacm/implementation/sdac/)

**I am deliberately not quoting a total SDAC zone count.** Any number I produce here is my
own arithmetic over a country list, and the decision does not turn on 37 vs 39. The
supportable statement is the one above: **Italy 7, Norway 5, Sweden 4, Denmark 2; every
other SDAC country is single-zone.** If a total is ever needed for a paper, take it from
the ACER/ENTSO-E bidding-zone review (14 configurations studied, report published
28 April 2025), not from this memo.
[ENTSO-E BZR main report (PDF)](https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Network%20codes%20documents/NC%20CACM/BZR/2025/Bidding_Zone_Review_of_the_2025_Target_Year.pdf) ·
[Bidding Zone study released](https://www.entsoe.eu/news/2025/04/28/bidding-zone-study-released/)

### 3.3 Ireland specifically — one zone, two load areas

**SEM is a single bidding zone covering the entire island** (Ireland + Northern Ireland),
`BZN|IE(SEM)` = `10Y1001A1001A59C`. EirGrid is the NEMO for Ireland and SONI for Northern
Ireland, but they sit inside **one** price zone.

Operationally, however, EirGrid/SONI publish **separate** system demand for All-Island,
Ireland, and Northern Ireland on the Smart Grid Dashboard.
[Smart Grid Dashboard](https://www.smartgriddashboard.com/) ·
[I-SEM Industry Guide (SEMO)](https://www.sem-o.com/sites/semo/files/documents/general-publications/I-SEM-Industry-Guide.pdf)

**So Ireland gives you 2 load series and 1 price series.** For the own-zone diagnostic you
get exactly one observation unit (SEM), with all-island load. The IE/NI split is a
*decomposition of the same zone's load*, not a second zone — it cannot support a
cross-sectional comparison. Useful as a robustness check on the load measure, not as a
second panel unit.

**Ireland is also the SDAC MTU exception, and this is easy to get wrong.** The day-ahead
auction runs on **SEMOpx**, at 11:00 each calendar day with results published from 11:45,
covering **48 half-hour Trading Periods** from 23:00 to 23:00. SEMOpx interacts with the
regional Coupling Operator running EUPHEMIA.
[SEMOpx Day-Ahead Market](https://www.semopx.com/markets/day-ahead-market) ·
[SEMOpx market data](https://www.semopx.com/market-data) ·
[market results](https://www.semopx.com/market-data/market-results)

On the same 30 September 2025 go-live date, **SEM moved from 60-minute to 30-minute MTU
while the rest of SDAC moved to 15-minute** — SEMOpx's own market message is titled
*"MCSC Confirms SDAC 15Min MTU/SEM 30Min MTU Go-live on 30 Sept 2025."* So Ireland's
day-ahead price history is: hourly → 30-minute from 2025-10-01, never 15-minute.

**This makes Ireland unexpectedly attractive as a pure time-series case, even though it is
useless as a cross-section.** Irish load is reported at **30-minute** resolution (§6.3),
and from 2025-10-01 the Irish day-ahead price is *also* 30-minute — so **Ireland is the one
European market where load and price sit on the same native sub-hourly grid.** Everywhere
else you are either aggregating a finer load series up to an hourly price, or (post-MTU)
matching 15-min price against a load series on a different grid. If the diagnostic is ever
run as a single-market deep dive rather than a panel, Ireland is the best-resolved candidate
in Europe — with the caveat that the matched-grid period only begins 2025-10-01.
[SEMOpx market message](https://www.semopx.com/market-messages/mcsc-confirms-sdac-15min-mtusem-30min-mtu-go-live-30-sept-2025) ·
[SEMOpx 30-min MTU modification proposal (PDF)](https://www.semopx.com/sites/semopx/files/documents/market-modifications/SPX_01_24/SPX_01_2430MinuteMTUImplementationintheDay-AheadMarket.pdf) ·
[30-Min MTU technical specification (PDF)](https://www.semopx.com/sites/semo/files/documents/general-publications/30-Min-MTU-Technical-Specification-v1.0.pdf)

### 3.4 The answer to "finest resolution where both are available"

**The bidding zone.** Concretely, the finest usable observation units are:

| Rank | Unit | Where it exists | Both load & price? |
|---|---|---|---|
| 1 | Node / pnode (LMP) | **Nowhere in Europe** | — |
| 2 | Bidding zone | All SDAC | **Yes — this is the floor and the ceiling** |
| 3 | Control area / TSO area | DE (4), and others | Load only — no price |
| 4 | Administrative region | FR (12 regions), IT, ES | Load only — no price |

---

## 4. Q3 — National TSO sources

The question to ask of each is not "is it richer than ENTSO-E?" but **"does its extra
granularity buy anything, given the price zone?"** For most, the answer is no.

| TSO / country | Sub-national load published? | Price zones | Does it help? |
|---|---|---|---|
| **Terna (IT)** | **Yes — per bidding zone** | **7** | **Yes — best in Europe** |
| Svenska kraftnät (SE) | Yes — per elområde SE1–SE4 | 4 | Yes |
| Statnett (NO) | ⚠️ per NO1–NO5 expected | 5 | Likely yes |
| Energinet (DK) | Yes — DK1/DK2 | 2 | Yes |
| EirGrid / SONI (IE) | Yes — IE / NI / All-Island | **1 (SEM)** | No — no matching price |
| RTE (FR) | Yes — regions **and metro areas**, 15-min | **1** | No — no matching price |
| TenneT DE, Amprion, 50Hertz, TransnetBW | Yes — 4 control areas (via SMARD) | **1 (DE-LU)** | No — no matching price |
| TenneT NL | national | 1 | No |
| REE / ESIOS (ES) | Yes, plus 10-min national demand | **1** | No — but temporally rich |
| Fingrid (FI) | national (+ metering-point aggregates) | 1 | No |

### 4.1 Terna (Italy) — the one to build on

- **Official REST API**, `Terna Developer` portal. Total Load endpoint:
  **`https://api.terna.it/load/v2.0/total-load`**
- Parameters: `dateFrom`, `dateTo` (both required, `dd/mm/yyyy`), `biddingZone` (optional,
  0..n).
- **Valid `biddingZone` values:** `North`, `Centre-North`, `South`, `Centre-South`,
  `Sardinia`, `Sicily`, `Calabria`, `Italy` — i.e. the 7 zones plus a national total.
- Response fields: `date`, `date_tz` (`Europe/Rome`), `date_offset`, `total_load_MW`,
  `forecast_total_load_MW`, `bidding_zone`.
- **Gotcha documented by Terna:** *"When the value entered does not match one of the
  expected values, an error will not be returned, but an empty body will be returned."*
  A typo'd zone name silently yields an empty series rather than an error. Assert on row
  counts.
- **Auth: OAuth 2.0.** Register an application on the developer portal, get client key +
  secret, exchange for a token. **Tokens are valid for 300 seconds** — the client must
  refresh aggressively.
- Timestamps in the documented examples land on quarter-hours (e.g. `23:45:00`), which is
  consistent with 15-minute data, but ⚠️ **the docs do not state the resolution explicitly
  and do not state the history start date** — §9.

[Total Load API](https://developer.terna.it/docs/read/apis_catalog/load/Total_Load) ·
[Access token](https://developer.terna.it/docs/read/Access_Token) ·
[Developer portal](https://developer.terna.it/) ·
[Download Center (bulk CSV/Excel)](https://dati.terna.it/en/download-center)

The Download Center exposes the same zonal breakdown as browsable datasets — `Total Load`,
`Market Load`, `Peak Valley Load`, `Load Forecast` — each carrying the zone list
*Centre-North, Centre-South, North, South, Sardinia, Sicily, Calabria, Italy*. It is the
sane route for a multi-year bulk pull; the API is the route for incremental updates.

### 4.2 EirGrid / SONI (Ireland + Northern Ireland)

- **Smart Grid Dashboard** — `https://www.smartgriddashboard.com/` — switchable between
  All-Island / Ireland / Northern Ireland; series include system demand, generation, wind,
  interconnection, frequency, **imbalance price and volume**, SNSP, and CO2 intensity.
  Graphs are date-customisable and **downloadable as CSV**.
- **Actual and forecast System Demand are at 15-minute intervals**; **Imbalance Volume is
  per 30-minute Trading Period.** ⚠️ Both figures come from secondary sources (including a
  community scraper) rather than an EirGrid spec page — §9.
- The dashboard has an **undocumented JSON API** behind it, which third-party scrapers use.
  ⚠️ Unofficial; no published contract, no stability guarantee — §9.
- **[EirGrid System and Renewable Data Reports](https://www.eirgrid.ie/grid/system-and-renewable-data-reports)**
  is the official bulk-report page and is the better citation for a paper.
- Market prices (day-ahead) come from **SEMOpx**, not EirGrid. ⚠️ Not investigated in this
  pass — §9.
- Third-party helper: [Daniel-Parke/EirGrid_Data_Download](https://github.com/Daniel-Parke/EirGrid_Data_Download)
  (unofficial; treat as a reference implementation, not a dependency).

### 4.3 Germany — SMARD (Bundesnetzagentur), covering all four TSOs

Rather than hitting 50Hertz / Amprion / TenneT DE / TransnetBW individually, use **SMARD**,
the German regulator's market-data platform, which aggregates all four.

- **Free, no registration**, CSV download; **up to two years of data per exported file**.
  [SMARD download centre](https://www.smard.de/en/downloadcenter/download-market-data)
- SMARD's own statement of provenance: German TSOs supply data to ENTSO-E under the
  transparency Regulation and **SMARD retrieves it automatically** — so SMARD is a
  *convenience layer over ENTSO-E*, not an independent richer source.
  [About SMARD](https://www.smard.de/en/ueber-uns)
- **Undocumented-but-stable JSON API** used by the site itself, reverse-engineered and
  published as an OpenAPI spec by the bundesAPI community:
  `https://www.smard.de/app/chart_data/{filter}/{region}/index_{resolution}.json` for
  available timestamps, then
  `https://www.smard.de/app/chart_data/{filter}/{region}/{filter}_{region}_{resolution}_{timestamp}.json`
  for the series. **Quarter-hour resolution is available** —
  e.g. `.../chart_data/4066/DE/index_quarterhour.json`.
  [bundesAPI/smard-api](https://github.com/bundesAPI/smard-api) ·
  [openapi.yaml](https://github.com/bundesAPI/smard-api/blob/main/openapi.yaml)
  ⚠️ This API is **not officially documented by Bundesnetzagentur**; the spec is
  community-maintained. Fine for research, not for anything that must not break — §9.
- **Still only one price zone (DE-LU).** SMARD's per-control-area load is a decomposition,
  not a cross-section.

### 4.4 France — RTE

France has the **richest sub-national load data in Europe** — and it is completely wasted
on this design, because France is one price zone. Worth documenting anyway in case the
project ever wants a load-only application.

- The real home of the data is **ODRÉ (Open Data Réseaux Énergies)**, an Opendatasoft
  portal, not the éCO2mix marketing pages.
- **`eco2mix-regional-tr`** — real-time regional data, *"refreshed once per hour at
  15-minute intervals"*: actual consumption, production by source, pumped-storage pumping,
  and the balance of physical exchanges with neighbouring regions, **per French region**.
  [ODRÉ regional real-time](https://reseaux-energies-rte.opendatasoft.com/explore/dataset/eco2mix-regional-tr/) ·
  [data.gouv.fr entry](https://www.data.gouv.fr/datasets/donnees-eco2mix-regionales-temps-reel-1)
- **`eco2mix-regional-cons-def`** — the consolidated/definitive archive, at **30-minute**
  resolution (*"au pas demi-heure"*), covering **January 2013 → December 2024** for
  definitive data, with consolidated data from January 2021.
  [ODRÉ consolidated/definitive](https://odre.opendatasoft.com/explore/dataset/eco2mix-regional-cons-def/information/)
  → **Note the resolution mismatch: real-time regional is 15-minute, the definitive archive
  is 30-minute.** Real-time month M is deleted mid-month M+1 and replaced by consolidated,
  then definitive data mid-year A+1. Anything needing 15-minute French regional data must
  be *collected as it is published*.
- **API quota: 50,000 API calls per user per month** on the ODRÉ platform.
- There is also **`eco2mix-metropoles-tr`** — real-time consumption for major French
  *metropolitan areas*, i.e. sub-regional.
  [ODRÉ metropoles](https://odre.opendatasoft.com/explore/dataset/eco2mix-metropoles-tr/)
- The separate **RTE Data Portal** at `https://data.rte-france.com/catalog` is the OAuth
  API catalogue; downloading "certain data published by RTE" requires **creating an
  account**.
  [services-rte download page](https://www.services-rte.com/en/download-data-published-by-rte.html) ·
  [RTE data catalog](https://data.rte-france.com/catalog) ·
  [éCO2mix regional page (RTE)](https://www.rte-france.com/donnees-publications/eco2mix-donnees-temps-reel/donnees-regionales)
- **France is one price zone.** Regional and metropolitan French load cannot be paired with
  a regional or metropolitan French price. This is the single clearest illustration of the
  join problem in §1.

### 4.5 Spain — REE / ESIOS

- **ESIOS API** at `https://api.esios.ree.es/`. **A personal token is required and is
  obtained by emailing `consultasios@ree.es`** (free; no subscription fee documented).
- Real-time demand (*Demanda real*, indicator `1293`) is published **every 10 minutes**.
  That is finer than anything in the US panel.
- ⚠️ Token procedure, indicator number, and 10-minute cadence come from third-party
  clients and blog write-ups, not from a REE page I read directly — §9.
  [ESIOS portal](https://www.esios.ree.es/en) ·
  [resios R client docs](https://ropenspain.github.io/resios/) ·
  [SanPen/ESIOS Python client](https://github.com/SanPen/ESIOS)
- **One price zone (ES).** Temporally rich, spatially useless for this design.

### 4.6 Nordics

- **Fingrid (FI)** — [data.fingrid.fi](https://data.fingrid.fi/en). Open RESTful API,
  machine-readable datasets covering prices, transmission, and consumption. **Free account
  registration required for API calls.** Most datasets update hourly; **some at 15-minute
  and 3-minute intervals**. Since 2024 it also publishes accounting-point-level consumption
  and small-scale production aggregates.
  [Fingrid open data](https://www.fingrid.fi/en/electricity-market-information/fingrid-open-data/) ·
  [2024 accounting-point announcement](https://www.fingrid.fi/en/news/news/2024/fingrids-open-data-service-now-provides-data-on-electricity-consumption-and-small-scale-electricity-production-from-accounting-points-in-finland/)
- **Energinet (DK)** — [Energi Data Service](https://www.energidataservice.dk/). Free and
  open portal for Danish energy-system data with public APIs; reported to need **no
  authentication**. Denmark's DK1/DK2 split makes this genuinely useful.
  [About](https://www.energidataservice.dk/about) ·
  [Energinet data catalog](https://en.energinet.dk/energy-data/data-catalog/)
- **Svenska kraftnät (SE)** — a **new open-data portal at
  [data.svk.se](https://data.svk.se/)**. ⚠️ Reported as launched publicly in June 2026 —
  i.e. very new, and I have not verified its dataset roster, SE1–SE4 breakdown, resolution,
  or history depth — §9. `Mimer` is the separate market-participant settlement system.
  [SVK statistics](https://www.svk.se/en/stakeholders-portal/electricity-market/statistics/)
- **Statnett (NO)** — ⚠️ **not verified in this pass.** Norway's NO1–NO5 load is available
  through ENTSO-E regardless; treat Statnett as an optional cross-check — §9.

**For the Nordics, ENTSO-E is likely sufficient**: SE1–SE4, NO1–NO5 and DK1/DK2 are all
`BZN` codes in the EIC list, so Article 6 load and Article 12 price both exist per zone
through a single API. The national portals are cross-checks, not requirements.

---

## 5. Q4 — Power exchanges: free vs. paywalled

| Exchange | Coverage | Free? | Notes |
|---|---|---|---|
| **OMIE** | ES, PT | **Yes — free file downloads** | Quarter-hourly and hourly |
| **GME** | IT | Website results free; bulk feeds gated | API launched 2025-10-15, authorisation required |
| **Nord Pool** | Nordics, Baltics, CWE, UK | Website display free; **bulk/API paid** | History to 1992 behind a fee |
| **EPEX SPOT** | CWE, and more | Website results free; **datasets paid** | Sold via EEX Group Webshop |

### 5.1 OMIE (Iberia) — the most open exchange

Publishes day-ahead prices for **Spain and Portugal separately** plus Iberian totals, at
**quarter-hourly resolution** (explicitly labelled, e.g. *"period 1 H1Q1, from 00:00 to
00:15 CET"*) with hourly aggregations also available. Monthly / annual / historical scopes
are offered, and there is a public **file-access** section plus an "old format reports"
archive.
[OMIE daily hourly price](https://www.omie.es/en/market-results/daily/daily-market/daily-hourly-price) ·
[OMIE file access](https://www.omie.es/en/file-access-list) ·
[market results history](https://www.omie.es/en/market-results-history)
⚠️ I did not verify the exact file-server URL patterns, retention depth, or whether any
registration is required for the file server — §9.

### 5.2 GME (Italy)

Publishes MGP (day-ahead) results including **PUN** (the national single purchase price)
and zonal prices. GME **launched an API service on 15 October 2025** replacing/augmenting
the previous FTPS channel; **access requires authorisation** — applicants must submit
documents per the API User Manual (contact `SupportoAPI@mercatoelettrico.org`). FTPS
remains available to already-registered users during a transition.
[GME](https://www.mercatoelettrico.org/en/) ·
[Vademecum to the Italian Power Exchange (PDF)](https://www.mercatoelettrico.org/Portals/0/Documents/en-us/20250101VademecumBorsaElettrica_En.pdf)
⚠️ GME does not state on its homepage whether historical downloads carry a fee. **For
Italian zonal prices, ENTSO-E is the cleaner and unambiguously free route** — use GME only
if you need PUN or something ENTSO-E does not carry.

### 5.3 Nord Pool — **flag: paywalled for bulk history**

- Public site `https://data.nordpoolgroup.com/` displays day-ahead prices.
- The **Data Portal** covers day-ahead and other auctions with CSV/Excel export and
  **historical datasets back to 1992** — but Nord Pool Data Services charge a
  **pre-determined annual "Data Fee" per data feed**, with **additional API accounts at
  €350/year**, and **redistribution licences starting at €7,000/year for regional products
  and €3,000/year for country products**.
  [Power Data Services](https://www.nordpoolgroup.com/en/services/power-market-data-services/) ·
  [Day-Ahead market data](https://www.nordpoolgroup.com/en/services/power-market-data-services/day-ahead-market-data/) ·
  [Data Portal registration](https://www.nordpoolgroup.com/en/services/power-market-data-services/dataportalregistration/) ·
  [Historical Market Data PDF](https://www.nordpoolgroup.com/4aabd6/globalassets/download-center/power-data-services/historical-market-data---data-portal.pdf)
- ⚠️ The specific euro figures above come from a search summary of Nord Pool's own pages;
  **confirm current pricing before budgeting** — §9.
- **Recommendation: do not buy Nord Pool.** Nordic day-ahead prices per SE1–SE4 / NO1–NO5 /
  DK1–DK2 are available free through ENTSO-E. Nord Pool's advantage is pre-2015 depth,
  which is a nice-to-have, not a requirement.

### 5.4 EPEX SPOT — **flag: paywalled**

Market results are visible on the public site, but datasets are sold by subscription
through the **EEX Group Webshop**, priced by usage, quoted monthly, **invoiced annually**,
and licensed for internal use within one legal entity only.
[EPEX market data services](https://www.epexspot.com/en/marketdataservices) ·
[EEX Group Webshop](https://webshop.eex-group.com/epex-spot-public-market-data) ·
[public market results](https://www.epexspot.com/en/market-results)
**Same recommendation: use ENTSO-E instead.** An institutional licence here would be an
unnecessary cost for a zonal day-ahead panel.

### 5.5 Intraday and imbalance prices

⚠️ **Under-investigated in this pass.** What is established: Nord Pool sells intraday
continuous data as a separate product; EirGrid publishes imbalance price and volume on the
Smart Grid Dashboard at 30-minute trading periods; Poland's imbalance settlement moved to
15-minute periods in June 2024. ENTSO-E also publishes balancing/imbalance data items under
Regulation 543/2013. **If intraday or imbalance prices matter to the design, this needs its
own pass** — §9.

---

## 6. Q5 — Temporal resolution, and the 15-minute MTU

### 6.1 The 15-minute Market Time Unit — verified, with the exact date

**The go-live was trading day 30 September 2025, for delivery day 1 October 2025.** From
the SDAC press release of 12 September 2025, verbatim:

> "Market Coupling Steering Committee confirms go-live of 15-Minute MTU in SDAC on trading
> day 30 September 2025 for delivery day 1 October 2025 … Go-live is therefore scheduled
> for 30 September 2025 (trading day) for delivery day 1 October 2025."

It had originally been scheduled for 11 June 2025 (delivery 12 June) and was postponed on
14 May 2025 due to non-technical readiness of some parties. It was preceded by a testing
campaign of more than a year covering local, regional and cross-border functionality.
[SDAC press release, 12 Sep 2025 (PDF)](https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Network%20codes%20documents/NC%20CACM/SDAC%202025/SDAC-MCSC%20Confirms%20the%20Go-Live%20of%2015-Minute%20MTU%20in%20SDAC%20on%2030%20September.pdf) ·
[same on NEMO Committee](https://www.nemo-committee.eu/assets/files/market-coupling-steering-committee-confirms-go-live-of-15-minute-mtu-in-sdac-on-trading-day-30-september-2025-for-delivery-day-1-october-2025.pdf) ·
[EPEX SPOT — successful implementation](https://www.epexspot.com/en/news/successful-implementation-15-minute-market-time-unit-mtu-sdac) ·
[EPEX SPOT — revised go-live date](https://www.epexspot.com/en/news/market-coupling-steering-committee-aligns-revised-go-live-date-15-minute-mtu-sdac)

ENTSO-E's SDAC page states plainly that **"SDAC successfully transitioned from hourly to
15-Minute Market Time Units."**
[SDAC — ENTSO-E](https://www.entsoe.eu/network_codes/cacm/implementation/sdac/)

**The one exception: Ireland.** All SDAC bidding zones support 15-minute MTU orders
**except SEM, which went to 30-minute** on the same date. See §3.3 for the SEMOpx sources.
Any statement of the form "all European day-ahead prices are 15-minute from October 2025"
is wrong for Ireland.

**⚠️ Do not conflate two different 15-minute things.** The **imbalance settlement period**
(ISP) moving to 15 minutes under the Electricity Balancing Guideline is a *separate* reform
with *different* national timings — Poland's June 2024 ISP change is an example. The
**day-ahead MTU** change is the one dated above. Keep them distinct in any write-up.

### 6.2 What this means for the panel design

- **Before 2025-10-01:** day-ahead prices are hourly in essentially all SDAC zones.
- **From 2025-10-01:** day-ahead prices are **quarter-hourly** across SDAC.
- **A panel spanning the break has a mid-series resolution change.** Options: (a) end the
  sample 2025-09-30 and keep a clean hourly panel; (b) aggregate post-Oct-2025 quarter-hours
  up to hourly; (c) run the post-break period as a separate, finer-resolution sample. Option
  (b) is probably the default, but (c) is scientifically the more interesting one — a
  15-minute |load gradient| is a much better-resolved volatility measure than an hourly one.

### 6.3 Is 15-minute or finer load data available?

**Yes, and in several places it predates the price change:**

- **Germany (SMARD):** quarter-hour endpoints exist (`index_quarterhour.json`).
- **Ireland (EirGrid):** system demand at 15-minute intervals ⚠️.
- **Italy (Terna):** quarter-hour timestamps in the API examples ⚠️.
- **Spain (ESIOS):** real-time demand every **10 minutes** ⚠️ — the finest cadence found
  anywhere in this survey.
- **Finland (Fingrid):** mostly hourly, some datasets at **15-minute and 3-minute**
  intervals.
- **OMIE:** quarter-hourly *prices* for ES/PT.
- **ENTSO-E:** resolution of Actual Total Load is **country-dependent**, tracking each
  market's MTU. Hirth et al. (2018) document the split as: **15-minute** for Austria,
  Belgium, Czech Republic, Netherlands, Germany and Hungary; **30-minute** for Great
  Britain, Cyprus and Ireland; **hourly** for most other countries. The same paper notes
  Actual Total Load (6.1.A) is published for **three frameworks: countries, bidding zones
  and control areas.**
  [Hirth et al. 2018](https://www.sciencedirect.com/science/article/pii/S0306261918306068)
  ⚠️ **This is 2018-vintage and predates the 15-minute MTU transition** — several countries
  have almost certainly moved since. Treat it as the shape of the problem, not the current
  roster, and **probe resolution per zone empirically once a token exists.**

**Ragged-panel warning:** combining the above, a naive multi-country pull returns series on
at least three different time grids, and the grids change at 2025-10-01 (and, for Ireland,
change to a *fourth* grid). Resample to a common grid explicitly and deliberately; do not
let pandas do it implicitly.

**No 5-minute market data equivalent to US real-time markets exists in Europe**, because
there is no 5-minute European energy market to produce it. ESIOS's 10-minute demand and
Fingrid's 3-minute series are *system telemetry*, not settlement prices.

---

## 7. Q6 — Research datasets and Python packages

### 7.1 entsoe-py — the standard wrapper, and use it

`EnergieID/entsoe-py`, MIT licensed. Two clients:
- `EntsoeRawClient` → raw XML / ZIP
- `EntsoePandasClient` → pandas Series / DataFrame

Relevant methods: **`query_load()`**, **`query_load_forecast()`** (DataFrames) and
**`query_day_ahead_prices()`** (Series). Instantiated as
`EntsoePandasClient(api_key=<YOUR API KEY>)` — **it needs the ENTSO-E security token from
§2.3**. The pandas client automatically splits requests spanning more than one year and
chunks large responses across multiple API calls, which handles the 1-year-per-request
limit for you.
[entsoe-py on GitHub](https://github.com/EnergieID/entsoe-py) ·
[entsoe-py on PyPI](https://pypi.org/project/entsoe-py/)

**Critical version caveat for anyone starting now:** the 15-minute MTU broke
`query_day_ahead_prices()` for zones that switched, because the client passed a default
`resolution='60min'` and got `NoMatchingDataError`. Italian bidding zones were the first
reported casualty. A subsequent release **rewrote day-ahead prices to be 15-min-ready**,
and the `resolution` argument is now **deprecated** — the library forces the correct
resolution and the parameter will be removed.
[Issue #378 — IT zones 15min](https://github.com/EnergieID/entsoe-py/issues/378) ·
[Releases](https://github.com/EnergieID/entsoe-py/releases)
→ **Pin a recent version and test a post-2025-10-01 Italian query as a smoke test.**
Also [Issue #384 — respect API rate limit](https://github.com/EnergieID/entsoe-py/issues/384).

### 7.2 Open Power System Data — **do not build on this**

OPSD's `time_series` package is the obvious first hit for "research dataset wrapping
European load and prices," and it is **stale**. The **latest version is 2020-10-06**; the
version list runs 2016-07-14 → 2020-10-06 and stops. Coverage is described as
**"2015–mid 2020"** from ENTSO-E Transparency sources, 32 countries, with 15/30/60-minute
files, containing electricity prices, load, wind and solar generation and capacities. The
project's funding ran to 2020.
[OPSD time_series data package](https://data.open-power-system-data.org/time_series/) ·
[OPSD homepage](https://open-power-system-data.org/) ·
[GitHub org](https://github.com/Open-Power-System-Data) ·
[Wiese, Hirth et al. (2019), *Energy Strategy Reviews* — OPSD paper (PDF)](https://neon.energy/Wiese-Hirth-etal-2018-Open-Power-System-Data.pdf)

**Verdict: useful as a validation set for 2015–2020 and as a reference for how to clean
ENTSO-E data. Useless for a to-present panel.** Its cleaning notebooks
(`Open-Power-System-Data/time_series/main.ipynb`) are worth reading precisely because they
encode fixes for the ENTSO-E quality problems in §2.5.

### 7.3 Other wrappers noted (not evaluated)

- `Hexagon/entsoe-api-client` (TypeScript/Deno) — [GitHub](https://github.com/Hexagon/entsoe-api-client)
- `entsoe-apy`, `entsoe-client` on PyPI
- `bundesAPI/smard-api` — community OpenAPI spec for SMARD ([GitHub](https://github.com/bundesAPI/smard-api))
- `ropenspain/resios` (R) and `SanPen/ESIOS` (Python) for Spain
- `Daniel-Parke/EirGrid_Data_Download` for Ireland
- RTDIP has an ENTSO-E source connector — [docs](https://www.rtdip.io/sdk/code-reference/pipelines/sources/python/entsoe/)

---

## 8. Recommendation

If the project extends to Europe, the lowest-risk shape is:

1. **Primary source: ENTSO-E Transparency Platform via `entsoe-py`.** One API, one token,
   one zone taxonomy for both load and price. Start the token request immediately (3
   working days).
2. **Primary within-country cross-section: Italy (7 zones).** Cross-check Terna's own API
   against ENTSO-E — a load series that disagrees between the TSO and the TP is exactly the
   Hirth et al. failure mode, and Italy is the one place where finding it matters.
3. **Secondary cross-sections: Norway (5), Sweden (4), Denmark (2)** — free through
   ENTSO-E, no national portal required.
4. **Pool the remaining single-zone countries** for the cross-country dimension, with
   explicit controls for currency/tax/market-design heterogeneity.
5. **Sample window: 2015 → 2025-09-30 for a clean hourly panel**, with the post-2025-10-01
   quarter-hourly period as a separate, higher-resolution extension.
6. **Do not pay Nord Pool or EPEX.** Everything needed is free through ENTSO-E.
7. **Drop Ireland, France, Germany and Spain as *zonal* cases** — they are single-price-zone
   countries and contribute one panel unit each, however rich their load data is. **But do
   not write Ireland off entirely:** it contributes one panel unit with **matching 30-minute
   load and price from 2025-10-01**, the best-resolved single-zone time series in Europe
   (§3.3). If the project ever wants a European single-market deep dive instead of a panel,
   that is the one to pick.
8. **Settle the Italian load question before committing** — see the top item of §9. It is
   the single check that decides whether recommendation #2 holds.

---

## 9. Not verified

Items below are stated somewhere above with a ⚠️, or were out of scope for this pass. **Do
not cite any of these without a primary-source check.**

### 9.0 THE ONE CHECK THAT DECIDES THE RECOMMENDATION — do this first

**Does ENTSO-E publish Actual Total Load (6.1.A) for the Italian bidding zones — concretely,
for `BZN|IT-North` = `10Y1001A1001A73I`?**

Everything in §8 rests on Italy being a 7-zone panel with matching load and price. Two soft
inferences are propping that up, and they should be collapsed into one hard test:

- I inferred zonal Italian load availability from the presence of `SCA|IT-North`,
  `SCA|IT-Centre-North`, … in the EIC list. **`SCA` is a system control area code — its
  existence is not proof that 6.1.A load is published at that granularity.**
- Terna's own API *does* serve per-zone load (§4.1), but **its history start date is
  undocumented and its resolution is inferred from example timestamps.** If Terna's archive
  only reaches, say, 2021, a 2015→2025 Italian panel does not exist through Terna.

**The test is a single API query once a token exists** (§2.3), not more desk research:

```
GET https://web-api.tp.entsoe.eu/api
    ?documentType=A65&processType=A16
    &outBiddingZone_Domain=10Y1001A1001A73I
    &periodStart=201501050000&periodEnd=201501060000
    &securityToken=<TOKEN>
```
(⚠️ `documentType`/`processType` codes themselves unconfirmed — see below. Vary the
`periodStart` year to find the true earliest date.)

- **If it returns data:** the Italian recommendation is safe independent of Terna's archive
  depth, Terna becomes the cross-check described in §8 item 2, and the panel window is
  whatever ENTSO-E supports.
- **If it returns nothing:** Italian *zonal* load exists only via Terna, panel depth is
  capped at Terna's archive, and §8 items 2 and 5 both need revising. In that case run the
  same probe for `BZN|SE1` / `BZN|NO1` / `BZN|DK1` before falling back to the Nordics as the
  primary cross-section.

**Do this before the PI commits to a European extension.**

### 9.1 Everything else

**ENTSO-E API mechanics**
- **`documentType` codes `A65` (system total load) and `A44` (price document), and
  `processType=A01` for day-ahead** — widely used and almost certainly right, but I did not
  see them in a page I read directly. Confirm in the
  [Postman reference](https://documenter.getpostman.com/view/7009892/2s93JtP3F6) or
  MoP Ref2 before writing extraction code. (The 1-year request limit and 100-TimeSeries
  response limit **are** now verified verbatim from that reference — §2.3.)
- Whether the **"Data Pre-5.1.15"** (2011–2014) section still exists on the rebuilt TP R3.
- Whether **ENTSO-E Power Statistics** offers deeper hourly load history, and from when.
- **Current per-country resolution of Actual Total Load.** §6.3 gives the Hirth et al.
  (2018) split, but that is eight years old and predates the MTU transition. **Probe
  empirically per zone.**
- **Empirical history start per zone.** Platform launch date ≠ per-series backfill. Probe
  each zone rather than trusting "since 2015."
- The exact status/behaviour of the **TP File Library** bulk-download feature (the Zendesk
  article is Cloudflare-protected and I could not read it).

**Spatial / market structure**
- **The total number of SDAC bidding zones is deliberately not stated in this memo** (§3.2).
  The multi-zone roster (IT 7 / NO 5 / SE 4 / DK 2) is verified; a grand total would be my
  own arithmetic over a country list. If a paper needs one, take it from the
  [BZR main report](https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Network%20codes%20documents/NC%20CACM/BZR/2025/Bidding_Zone_Review_of_the_2025_Target_Year.pdf).
- **No European nodal pilot was found**, but absence of evidence here is weak evidence of
  absence — I searched, I did not exhaustively check every national regulator.
- **Poland:** the 14 June 2024 balancing-reform date and the single-price CEN mechanism are
  from secondary sources. Confirm with PSE.
- **Italy's MSD (ancillary services market)** — I assert it is pay-as-bid at unit level and
  not an LMP, but did not verify from Terna/GME documentation.

**National TSOs**
- **RTE:** the **number of French regions** in `eco2mix-regional-*` is not verified (12 vs
  13 metropolitan regions, and whether Corsica is included). The 15-min / 30-min split and
  the 2013–2024 definitive range **are** verified from ODRÉ.
- **ESIOS:** the `consultasios@ree.es` token procedure, indicator `1293`, and the 10-minute
  cadence are from third-party clients and blogs, not a REE page.
- **EirGrid:** the 15-minute demand resolution and 30-minute imbalance period are from
  secondary sources; the dashboard's JSON API is **unofficial and undocumented**. History
  depth of the dashboard downloads is unknown. (The SEM 30-minute *day-ahead* MTU **is**
  verified — §3.3.)
- **Terna:** resolution of `total_load_MW` is **inferred** from quarter-hour timestamps in
  the docs; history start date is not stated anywhere I found.
- **Svenska kraftnät's data.svk.se** — reported as launched June 2026; dataset roster,
  SE1–SE4 breakdown, resolution and history depth all unverified.
- **Statnett (Norway)** — not investigated.
- **TenneT NL** — not investigated separately.
- **SMARD's JSON API is community-reverse-engineered**, not officially supported by
  Bundesnetzagentur.

**Exchanges**
- **Nord Pool pricing figures** (€350/year API accounts; €7,000 / €3,000 redistribution
  licences) are from a search summary of Nord Pool pages, not read directly. Confirm before
  quoting a budget number.
- **OMIE** file-server URL patterns, retention depth, and any registration requirement.
- **GME** — whether historical downloads carry a fee, and what the API authorisation
  process actually demands.
- **Intraday and imbalance price availability across Europe** — genuinely
  under-investigated. Needs its own pass if the design requires them.

**Data quality**
- The DST / gaps / silent-revision / structural-break cautions in §2.5 beyond what Hirth et
  al. (2018) explicitly documents are standard practitioner knowledge, not individually
  sourced here.

---

## 10. Sources

**Regulation and market structure**
- [Commission Regulation (EU) No 543/2013 — EUR-Lex](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013R0543)
- [SDAC — ENTSO-E](https://www.entsoe.eu/network_codes/cacm/implementation/sdac/)
- [SDAC 15-min MTU go-live press release, 12 Sep 2025 (PDF)](https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Network%20codes%20documents/NC%20CACM/SDAC%202025/SDAC-MCSC%20Confirms%20the%20Go-Live%20of%2015-Minute%20MTU%20in%20SDAC%20on%2030%20September.pdf)
- [NEMO Committee copy of the same release (PDF)](https://www.nemo-committee.eu/assets/files/market-coupling-steering-committee-confirms-go-live-of-15-minute-mtu-in-sdac-on-trading-day-30-september-2025-for-delivery-day-1-october-2025.pdf)
- [EPEX SPOT — successful implementation of 15-min MTU](https://www.epexspot.com/en/news/successful-implementation-15-minute-market-time-unit-mtu-sdac)
- [EPEX SPOT — revised go-live date](https://www.epexspot.com/en/news/market-coupling-steering-committee-aligns-revised-go-live-date-15-minute-mtu-sdac)
- [Bidding Zone Review — ENTSO-E](https://www.entsoe.eu/network_codes/bzr/)
- [ENTSO-E BZR main report, April 2025 (PDF)](https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/Network%20codes%20documents/NC%20CACM/BZR/2025/Bidding_Zone_Review_of_the_2025_Target_Year.pdf)
- [Bidding Zone study released — ENTSO-E news](https://www.entsoe.eu/news/2025/04/28/bidding-zone-study-released/)
- [ACER — decision on alternative bidding zone configurations](https://www.acer.europa.eu/news-and-events/news/acer-has-decided-alternative-electricity-bidding-zone-configurations)

**ENTSO-E Transparency Platform**
- [Transparency Platform](https://transparency.entsoe.eu/)
- [Electricity Market Transparency — ENTSO-E](https://www.entsoe.eu/data/transparency-platform/)
- [Manual of Procedures (MoP)](https://www.entsoe.eu/data/transparency-platform/mop/)
- [Request Endpoint](https://transparencyplatform.zendesk.com/hc/en-us/articles/15696677194644-Request-Endpoint)
- [How to get security token](https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token)
- [API Rate Limit Part 1](https://transparencyplatform.zendesk.com/hc/en-us/articles/12783148966036)
- [Request Parameters](https://transparencyplatform.zendesk.com/hc/en-us/articles/15696716612372-Request-Parameters)
- [Reference Documentation](https://transparencyplatform.zendesk.com/hc/en-us/articles/12784099471764-Reference-Documentation)
- [Area List with Energy Identification Code (EIC)](https://transparencyplatform.zendesk.com/hc/en-us/articles/15885757676308-Area-List-with-Energy-Identification-Code-EIC)
- [Introduction guide for new users](https://transparencyplatform.zendesk.com/hc/en-us/articles/13772306625428-Introduction-guide-for-new-users)
- [Restful API Postman documentation](https://documenter.getpostman.com/view/7009892/2s93JtP3F6)
- [Webinar: Discover the New ENTSO-E Transparency Platform](https://www.entsoe.eu/events/2025/10/29/webinar-invitation-discover-the-new-entso-e-transparency-platform/)

**Data quality literature**
- [Hirth, Mühlenpfordt & Bulkeley (2018), *Applied Energy* 225:1054–1067 — ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0306261918306068)
- [same, open PDF](https://neon.energy/Hirth-Muehlenpfordt-Bulkeley-2018-ENTSO-E-Transparency-Platform.pdf)

**Italy**
- [Terna Developer — Total Load API](https://developer.terna.it/docs/read/apis_catalog/load/Total_Load)
- [Terna Developer — Access Token](https://developer.terna.it/docs/read/Access_Token)
- [Terna Developer portal](https://developer.terna.it/)
- [Terna Download Center](https://dati.terna.it/en/download-center)
- [Terna Lightbox — the new electricity market zones](https://lightbox.terna.it/en/insight/new-electricity-market-zones)
- [Terna — zonal configuration review, March 2018 (PDF)](https://download.terna.it/terna/0000/1033/93.PDF)
- [GME](https://www.mercatoelettrico.org/en/)
- [Vademecum to the Italian Power Exchange (PDF)](https://www.mercatoelettrico.org/Portals/0/Documents/en-us/20250101VademecumBorsaElettrica_En.pdf)

**Ireland**
- [EirGrid Smart Grid Dashboard](https://www.smartgriddashboard.com/)
- [EirGrid System and Renewable Data Reports](https://www.eirgrid.ie/grid/system-and-renewable-data-reports)
- [SONI Real Time System Information](https://www.soni.ltd.uk/grid/real-time-system-information)
- [I-SEM Industry Guide (SEMO, PDF)](https://www.sem-o.com/sites/semo/files/documents/general-publications/I-SEM-Industry-Guide.pdf)
- [SEMOpx — The Day-Ahead Market](https://www.semopx.com/markets/day-ahead-market)
- [SEMOpx — Market Data](https://www.semopx.com/market-data) · [Market Results](https://www.semopx.com/market-data/market-results)
- [SEMOpx market message — SDAC 15Min MTU / SEM 30Min MTU go-live 30 Sept 2025](https://www.semopx.com/market-messages/mcsc-confirms-sdac-15min-mtusem-30min-mtu-go-live-30-sept-2025)
- [SEMOpx 30-minute MTU modification proposal (PDF)](https://www.semopx.com/sites/semopx/files/documents/market-modifications/SPX_01_24/SPX_01_2430MinuteMTUImplementationintheDay-AheadMarket.pdf)
- [SEMOpx 30-Min MTU technical specification (PDF)](https://www.semopx.com/sites/semo/files/documents/general-publications/30-Min-MTU-Technical-Specification-v1.0.pdf)
- [Chapter 4: Markets — Industry Guide to the I-SEM (PDF)](https://www.sem-o.com/sites/semo/files/documents/training/Industry-Guide-to-the-I-SEM-Markets.pdf)

**Germany**
- [SMARD market data](https://www.smard.de/en)
- [SMARD download centre](https://www.smard.de/en/downloadcenter/download-market-data)
- [About SMARD](https://www.smard.de/en/ueber-uns)
- [bundesAPI/smard-api](https://github.com/bundesAPI/smard-api)
- [TenneT — go-live of DE-AT bidding zone border congestion management, 1 Oct 2018](https://www.tennet.eu/tinyurl-storage/detail/go-live-of-congestion-management-on-the-german-austrian-bidding-zone-border-de-at-bzb-on-1st-of-oc/)

**France**
- [ODRÉ — éCO2mix régionales temps réel (15-min)](https://reseaux-energies-rte.opendatasoft.com/explore/dataset/eco2mix-regional-tr/)
- [ODRÉ — éCO2mix régionales consolidées et définitives (30-min, 2013–2024)](https://odre.opendatasoft.com/explore/dataset/eco2mix-regional-cons-def/information/)
- [ODRÉ — éCO2mix métropoles temps réel](https://odre.opendatasoft.com/explore/dataset/eco2mix-metropoles-tr/)
- [data.gouv.fr — éCO2mix régionales temps réel](https://www.data.gouv.fr/datasets/donnees-eco2mix-regionales-temps-reel-1)
- [RTE — éCO2mix données régionales](https://www.rte-france.com/donnees-publications/eco2mix-donnees-temps-reel/donnees-regionales)
- [RTE download data](https://www.services-rte.com/en/download-data-published-by-rte.html)
- [RTE Data Portal catalog](https://data.rte-france.com/catalog)
- [RTE Analyses et données](https://analysesetdonnees.rte-france.com/en)

**Spain / Iberia**
- [ESIOS](https://www.esios.ree.es/en)
- [OMIE — daily hourly price](https://www.omie.es/en/market-results/daily/daily-market/daily-hourly-price)
- [OMIE — market results history](https://www.omie.es/en/market-results-history)

**Nordics**
- [Fingrid Open Data](https://data.fingrid.fi/en)
- [Fingrid open data overview](https://www.fingrid.fi/en/electricity-market-information/fingrid-open-data/)
- [Energi Data Service (Energinet)](https://www.energidataservice.dk/)
- [Energinet data catalog](https://en.energinet.dk/energy-data/data-catalog/)
- [Svenska kraftnät data portal](https://data.svk.se/)
- [Svenska kraftnät statistics](https://www.svk.se/en/stakeholders-portal/electricity-market/statistics/)
- [Nord Pool Power Data Services](https://www.nordpoolgroup.com/en/services/power-market-data-services/)
- [Nord Pool Day-Ahead market data](https://www.nordpoolgroup.com/en/services/power-market-data-services/day-ahead-market-data/)
- [Nord Pool day-ahead price display](https://data.nordpoolgroup.com/)

**Poland**
- [PSE report — integration with European markets](https://raport.pse.pl/en/economic-and-market-impact/integration-of-the-polish-market-with-european-markets)
- [Dexter Energy — Poland's balancing market reform](https://dexterenergy.ai/news/polands-balancing-market-reform-what-short-term-power-traders-can-expect/)

**Tooling and datasets**
- [entsoe-py](https://github.com/EnergieID/entsoe-py) · [PyPI](https://pypi.org/project/entsoe-py/)
- [entsoe-py issue #378 — 15-min resolution for IT zones](https://github.com/EnergieID/entsoe-py/issues/378)
- [entsoe-py issue #384 — respect API rate limit](https://github.com/EnergieID/entsoe-py/issues/384)
- [OPSD time_series data package](https://data.open-power-system-data.org/time_series/)
- [Open Power System Data](https://open-power-system-data.org/)
- [OPSD GitHub org](https://github.com/Open-Power-System-Data)
- [Wiese, Hirth et al. — Open Power System Data paper (PDF)](https://neon.energy/Wiese-Hirth-etal-2018-Open-Power-System-Data.pdf)
- [RTDIP ENTSO-E connector](https://www.rtdip.io/sdk/code-reference/pipelines/sources/python/entsoe/)
- [Hexagon/entsoe-api-client](https://github.com/Hexagon/entsoe-api-client)
- [Daniel-Parke/EirGrid_Data_Download](https://github.com/Daniel-Parke/EirGrid_Data_Download)
