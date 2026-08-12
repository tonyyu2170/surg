# ERCOT as an Alternative Market: Data Availability Research

**Date:** 2026-08-07
**Motivation:** Advisor suggested exploring ERCOT because PJM/DOM data proved too limited.
**Status:** Research memo. No scope decision made.

---

## Headline

**Data-center energy usage in ERCOT is public only as an annual, modeled, subpopulation total
that also includes crypto mining. Facility-level load is not public — in ERCOT any more than in
PJM.** I verified the facility-level negative empirically across two operating days two years
apart, not by inference. Do not pivot to ERCOT expecting to finally see individual data centers.

However, ERCOT is materially better than PJM/DOM on four *other* axes, and one of them
(the West load zone) substantially weakens the single biggest methodological problem in the
original proposal — the Phase 2 "signal isolation" hack.

---

## 1. The decisive negative result (verified empirically)

The most promising candidate was ERCOT's **60-Day SCED Disclosure Reports (NP3-965-ER)**,
specifically the `Load Resource Data in SCED` file. On paper it is close to ideal:

- **Public.** No market-participant credentials, no API key, no quota.
- **Unmasked `Resource Name`** per facility.
- **`Real Power Consumption`** — actual telemetered MW, not a projection.
- **5-minute SCED resolution.**
- It carries **`Ramp Rate Up` / `Ramp Rate Down`** columns — nominally on-topic for a
  load-volatility question. (**See §1a — these turn out to be 97% empty.**)

⚠️ **History caveat — retention policy ≠ accessible files.** ERCOT's product page states retention
back to 2011, but I counted the actual public MIS listing: **866 daily files spanning 2024-03-24
→ 2026-08-07**, a rolling ~2.4-year window. Anything older needs the Data Product Archive
(`data.ercot.com`), which is a separate request path. Third-party aggregators report continuous
coverage from Nov 2021 (~151M rows). Do not assume a 2011 panel is a free download.

I downloaded the 2026-08-07 disclosure (57 MB zip; 33 MB Load Resource CSV; operating day
~2026-06-08) and profiled it:

| Metric | Value |
|---|---|
| Rows (one operating day) | 142,560 |
| Distinct SCED intervals | 288 (full day, 5-min) |
| **Distinct Load Resources** | **495** |
| Resources with peak ≥ 75 MW (ERCOT large-load threshold) | **12** |
| Median resource peak | **2.1 MW** |
| Resources under 10 MW | 376 of 495 |
| Resources reporting zero consumption all day | 160 |
| Sum of peaks, all resources | 5,247 MW |

The 12 resources above 75 MW are recognizably **legacy Gulf Coast petrochemical/industrial**
demand response, not computing:

```
SNDSW_LD9      331.8 MW      FORMOSA_LD3    269.2 MW   (Formosa Plastics)
DOWGEN_LD9     234.6 MW      MBPOD_LD6      183.6 MW   (Dow Chemical)
DIB_LD2        162.5 MW      BCGENWRW_LD1   150.8 MW   (QSE: QOCCID = Occidental)
```

A name/QSE heuristic scan for crypto and hyperscaler operators returned only five weak hits,
the largest being `GEMSCRYP_LD2` at 68.9 MW.

**Why:** this file only contains loads *registered as ERCOT Load Resources* — i.e. entities that
opted into demand response / ancillary services. Crypto miners partly do (QSE `QMP2EN` = MP2
Energy, the Lancium DR partner, has 47 resources). **Hyperscale AI data centers are plain
behind-the-meter load and are structurally invisible here.**

Caveat, stated honestly: this is one operating day and a name-based heuristic. A multi-day
audit of the full resource-name list could surface more crypto participation. It would not
change the structural conclusion about hyperscalers.

---

## 1a. Deeper audit of the 60-Day SCED disclosure

Four further checks, each of which independently reinforces the §1 conclusion.

### The package contents
The daily zip (57 MB compressed, 764 MB expanded) holds ten files. Load-relevant portion is small:

| File | Size | Relevance |
|---|---|---|
| `60d_SCED_Gen_Resource_Data` | 283 MB | generation, not load |
| `60d_SCED_Resource_AS_OFFERS` | 342 MB | ancillary-service offers |
| `60d_ESR_Data_in_SCED` | 95 MB | energy storage |
| **`60d_Load_Resource_Data_in_SCED`** | **34 MB** | **the only load file** |
| `60d_SCED_SMNE_GEN_RES` | 7.8 MB | settlement metered net energy, generation only |
| `60d_HDL_LDL_ManOverride`, `60d_AS_Capability_ManOverride` | 167 B each | empty |

### (i) The population is shrinking, not growing
If this dataset were tracking the data center boom, the registry would be expanding. It is doing
the opposite. Comparing the oldest publicly listed operating day against the newest:

| | 2024-03-24 | 2026-08-07 |
|---|---|---|
| Distinct Load Resources | 680 | **495** |
| Resources ≥ 75 MW | 14 | **12** |
| Sum of peaks | 6,743 MW | **5,247 MW** |
| Median peak | 2.10 MW | 2.10 MW |

315 resources left, 130 joined (1,502 MW total). The largest additions are `MBPOD_LD*`
(QSE `QPRIOR`) and `OB_ALD1` — not recognizable hyperscalers. Over the same window ERCOT's large
load queue grew roughly fourfold. **This registry is decoupled from the data center boom.**

### (ii) Telemetry is continuous — but ~10% of it is static
Good news: `Real Power Consumption` is reported even when a resource is `OUTL` (44.9% of outaged
intervals carry a nonzero value), so you get a continuous 288-interval daily trace, not just
DR-event snapshots.

Bad news: of 281 resources with a full day and peak ≥ 1 MW, **27 (10%) report a perfectly
constant value for all 288 intervals** — including two of the largest, `FORMOSA_LD3` (269.2 MW)
and `DIB_LD2` (162.5 MW). Those are near-certainly registered static values, not live metering.
Any panel built here needs a variance filter to drop them.

### (iii) Within this registry, the big loads are flat and the spiky loads are tiny
Coefficient of variation across the operating day:

- **Median CV = 0.038** — these loads are very flat.
- 81 of 281 resources exceed CV 0.10, but the spikiest are trivially small: `EAG_LD2` CV=11.96 at
  **8.7 MW peak**; `SANTAFE_LD1` CV=7.59 at **1.1 MW**; `CGRSW_LD1` CV=1.99 at **1.8 MW**.
- The genuinely large resources are the flattest: `SNDSW_LD9` (331.8 MW) CV=0.006;
  `GEMSCRYP_LD2`, the largest crypto-looking resource (68.9 MW), CV=0.042 with a maximum 5-minute
  swing of 4.3 MW.

**Is this real, or is it the static-telemetry contamination from (ii)?** I tested it rather than
assuming, by comparing CV for the same resource across both operating days. Of the 40 resources
present on both days with peak ≥ 20 MW, the top 12 by size split:

| Pattern | Count | Reading |
|---|---|---|
| Live telemetry (varies across days and within day) | 9 | genuinely flat load |
| Went flat by 2026 (`FORMOSA_LD3` 0.020→0.000, `DIB_LD2` 0.002→0.000) | 2 | static contamination |
| Flat, level shifted | 1 | ambiguous |

So the flatness is **mostly real, not an artifact** — but two of the largest resources are
demonstrably static-contaminated in 2026, and any panel needs a variance filter.

⚠️ **What this does not license.** This says nothing about data-center volatility, because
none of these resources are data centers — they are petrochemical plants and DR participants.
It is not corroboration of the earlier PJM "volatility flat or falling" finding, and it should
not be cited as a second-market replication of anything. It is a description of who happens to
be in this registry.

### (iv) ⚠️ Correction: the ramp-rate columns are effectively empty
I initially flagged `Ramp Rate Up`/`Ramp Rate Down` as directly on-topic. Measured across all
142,560 rows of the operating day, they are **populated in only 2.8%**. Column population:

| Column | Populated |
|---|---|
| `HDL` / `LDL` | ~65% |
| `Real Power Consumption` | 63.4% |
| `AS Awards ECRS` | 6.8% |
| **`Ramp Rate Up` / `Ramp Rate Down`** | **2.8%** |
| `Base Point` | 2.0% |
| `SCED Bid to Buy Curve-Price1` | 1.9% |
| `SCED Bid to Buy Curve-MW1`, `AS Awards RRSPFR` | 0% |

Ramp rates must be **derived from differencing `Real Power Consumption`**, not read off.

### (v) Price-responsiveness: corroborated qualitatively, not quantified
The bid-to-buy curve nominally gives the price at which a load walks away. Where populated
(**1.9% of intervals**): min $50/MWh, median **$300/MWh**, p75 and max **$5,000/MWh**.

Read this narrowly. `Curve-Price1` is populated in only 1.9% of rows and the paired
`Curve-MW1` is **0% populated** — a price with no quantity is not a usable curtailment trigger,
and 1.9% is not a basis for claiming most of these loads are price-responsive. It corroborates
the §4 mechanism qualitatively and no more. The endogeneity argument in §4 rests on the
Majumder/Xie result, which stands on its own.

### (vi) Cadence changed between 2024 and 2026
The 2024-03-24 file (operating day 2024-01-24) has **96 intervals — 15-minute cadence**. The
2026-08-07 file (operating day 2026-06-08) has **288 intervals — 5-minute**. Any multi-year
panel must handle a resolution change mid-sample; do not assume uniform 5-minute history.

---

### Corroborating evidence from the literature

Majumder, Aravena & **Le Xie**, *"An Econometric Analysis of Large Flexible Cryptocurrency-mining
Consumers in Electricity Markets"* (arXiv:2408.12014) — the best-in-class study of exactly this
question — states plainly of their firm-level hourly data:

> "The crypto-mining firms' electricity consumption dataset represents hourly load data
> aggregated across an ERCOT load zone, **is not publicly available, and can be obtained upon
> request.**"

Even they only got *load-zone-aggregated* data, mixed with unknown other firm load, by request.

**Warm-intro path worth noting:** Le Xie is a co-author of that paper *and* is reference [3] in
the existing SURG proposal. That request path is real and citation-backed.

---

## 2. What ERCOT genuinely does better than PJM/DOM

### (a) Prices: the acquisition blocker disappears
This is the clearest win. PJM forced a gridstatus.io multi-account workaround with a 500K-row /
250-request monthly free quota. ERCOT publishes nodal prices publicly with no membership gate:

- `NP6-905-CD` / `NP6-788-CD` — Settlement Point Prices at Resource Nodes, Hubs, Load Zones
- `NP6-86-CD` — SCED Shadow Prices and Binding Transmission Constraints (named facilities)
- `NP6-322-CD` — SCED System Lambda
- Public REST API at `developer.ercot.com` (free registration), plus the ungated MIS endpoint
  I used above.

### (b) Congestion is not a free column — but reconstruction is probably cheap
PJM publishes LMP pre-decomposed into energy / congestion / loss. **ERCOT does not publish a
congestion component.** The existing analysis codebase assumes a `congestion` column, so
something has to fill it.

The good news: evidence points to **ERCOT SCED being lossless**. Line losses are not explicitly
modeled in the SCED formulation, and ERCOT's own Marginal Losses page describes incorporating
marginal losses as an *assessment* performed at PUCT request — i.e. a proposal, not current
practice. If SCED carries no loss term, then

```
congestion = LMP − system lambda        (NP6-905-CD/NP6-788-CD minus NP6-322-CD)
```

is **exact, not an approximation** — a join of two free public feeds, not a new modeling module.
That materially lowers the cost of Option A below what a first read suggests.

⚠️ **Confirm before relying on it.** Sources conflict: some describe ERCOT LMP as
energy + congestion + loss in the textbook sense. Verify against the ERCOT Nodal Protocols
(Section 4/6, SCED formulation) whether a loss term enters real-time LMP. **This is the single
check most likely to move the Option A vs. B recommendation** — worth 30 minutes before any
scope decision. If losses *do* enter, reconstruction needs shadow prices (`NP6-86-CD`) × shift
factors and becomes a genuine preprocessing module.

### (c) ⚠️ The West zone: concentrated, but badly confounded — CORRECTED
**An earlier draft of this memo called West Texas "the strongest single argument for ERCOT."
That was over-claimed. Follow-up research found three confounds serious enough to change the
verdict.** The data availability is real; the identification is not clean.

**What holds up.** The load series is free and current — I verified the range directly on
ERCOT's Hourly Load Data Archives. Annual files cover **1995 through 2026 continuously** (2001
the only gap), split into the **8 weather zones since April 2003**, updated monthly around the
9th. ERCOT's March 2026 large-load report does show real concentration: `LZ_WEST` holds 5,136 MW
approved to energize with 2,253 MW observed peak, versus 3,907 / 1,634 MW for all other zones
combined.

**Confound 1 — load growth is substantially oil & gas, not data centers.** The Far West zone's
peak demand grew **~255% in a decade**, the highest in ERCOT, but the dominant driver is
**Permian Basin oil & gas electrification**. An S&P Global forecast submitted to ERCOT projected
oil-and-gas-related peak demand growth of **11,964 MW by 2030** — versus crypto mining adding
roughly **3.5 GW ERCOT-wide**. Attributing West Texas load growth to data centers would repeat,
in a new market, exactly the error already logged for DOM: *2026 escalation is largely
system-wide — never attribute it to data centers.*

**Confound 2 — West zone congestion is a generation phenomenon.** Congestion and price extremes
there are driven by **wind/solar export constraints**, not load. The zone splits in two: the
Panhandle is *export*-constrained (surplus wind that cannot get out), the Permian is
*import*-constrained (load growth outrunning delivery). Only ~40% of West-zone generation can
be transmitted to consumption hubs. The West load zone posts ERCOT's most frequent negative
prices, reaching **−$244/MWh** against a −$251 floor. A congestion-on-load-volatility regression
here would be dominated by wind, not by computing.

**Confound 3 — I conflated two different geographies.** ERCOT's `LZ_WEST` is a **load zone**;
the 255% growth figure and the free hourly load archive are **weather zones** (`West` and
`FarWest` are separate). They are not the same boundaries. Any West-zone design needs an
explicit load-zone ↔ weather-zone mapping step, which is real work and a source of error.

**Bonus problem for the volatility premise.** West Texas load is documented as **"nearly flat,"
without the peaks and valleys of residential/commercial demand** — because it is industrial.
That is the opposite of the spiky profile the proposal's premise requires.

**Revised verdict:** West Texas is a genuine load-growth hotspot with excellent free data, and it
is a legitimate *descriptive* comparison case against Northern Virginia. It is **not** a clean
treatment/control natural experiment, and it should not be sold to an advisor as one.

### (d) The interconnection queue beats JLARC as a growth forecast
Sub-question 2 currently projects onto JLARC's annual report. ERCOT's Large Load queue is
updated **monthly**, broken out by zone, project type (co-located vs standalone), and a status
funnel. From the March 2026 TAC report:

| Year | Observed energized (MW) | Total tracked incl. queue (MW) |
|---|---|---|
| 2022 | 2,634 | 2,634 |
| 2023 | 4,286 | 4,286 |
| 2024 | 4,845 | 4,845 |
| 2025 | 5,768 | 6,714 |
| 2026 | 5,768 | 21,765 |
| 2028 | 5,768 | 124,785 |
| 2030 | 5,768 | 238,630 |

Note the two columns carefully: **observed energized load is flat at 5,768 MW from 2025 through
2030** — that is realized, operating load. The 238,630 MW is the *queue*, overwhelmingly
"No Studies Submitted." Quoting 238 GW as if it were consumption is the single easiest way to
misread this dataset.

Only ~9.0 GW has Approval to Energize and observed non-simultaneous peak is ~3,883 MW — a
request-to-operating funnel near 1.6%. That funnel ratio is itself a publishable finding and a
much better-grounded projection basis than a queue headline number.

---

### (e) The aggregate that *is* public — and exactly what kind of aggregate it is
This distinction matters and is easy to get wrong, so stated precisely.

EIA's figure is **the summed consumption of large-flexible-load customers as a subpopulation** —
data centers plus crypto mining added together. It is **not** a whole-zone total. Exact wording:

> "we expect electricity demand from customers identified by ERCOT as large flexible load (LFL)
> will total 54 billion kilowatthours (kWh) in 2025"

For scale, ERCOT total 2025 consumption is ~487 billion kWh, so LFL is roughly **11%** of the
system. ERCOT defines LFL as any facility with expected peak demand ≥ 75 MW.

**This is categorically better than what DOM offers.** In PJM/DOM you get total zonal load and
must *infer* the data-center share — which is precisely what the Phase 2 filter was trying and
failing to do. Here the subpopulation is already separated for you.

⚠️ **Three limits that keep it from solving the problem:**
1. **It is a projection, not a metered sum.** Derived as ~9,500 MW approved capacity × ~65%
   historical utilization. It is an estimate built from a capacity factor.
2. **Annual, not a time series.** No hourly or 5-minute shape — so it cannot support a
   volatility question at all, only a levels/growth narrative.
3. **Data centers and crypto are not separated.** EIA treats them collectively as "large-scale
   computing facilities."

So the honest one-line answer: **yes, ERCOT data-center energy usage is public as an
annual, modeled, subpopulation total that lumps in crypto — and nothing finer.**

---

## 3. The UT dataset

The advisor's recollection is real but the dataset is **not currently public**.

**TRAIL Map** — *Texas Resilient and Advanced Industrial Load* — Center for Energy Economics,
Bureau of Economic Geology, UT Austin. Described as a data-driven platform for industrial load
growth, load forecasting, infrastructure alignment, water use, land use, and emissions hotspots.
Funded by the UT Austin Energy Institute, **project period May 2025 – August 2026**.

**White paper authorship** (verified from the PDF): Dr. **Ning Lin**, Dr. **Mariam Arzumanyan**,
**Edna Rodriguez Calzado**, Dr. **Dean Foreman**, Dr. **Nur Schuba**. Six chapters covering the
energy–data nexus, economic/infrastructure impacts, water and land sustainability, policy, and
strategic recommendations. **It is a narrative policy document, not a data publication** — no
facility tables, no load series, no appendix dataset.

⚠️ **The access risk is structural.** TRAIL sits under an **industrial affiliates program**,
launched with TXOGA, Treaty Oak Clean Energy, and Infrastructure Masons among its engaged
parties. Affiliates programs typically gate deliverables to paying members. That materially
lowers the odds TRAIL is ever released openly, and it means an access request is better framed
as an academic collaboration than as a download request.

- Program contact: **`dcws@beg.utexas.edu`** (dedicated program address — better first stop than
  a personal address)
- Lead researcher: **Ning Lin** — `ning.lin@beg.utexas.edu`
- Program page: https://www.beg.utexas.edu/energyecon/advancing-sustainable-data-center-development-in-texas
- White paper (PDF, public): https://www.beg.utexas.edu/files/cee/Data_Center_White_Paper_BEG.pdf
- Repository record: https://repositories.lib.utexas.edu/items/7e457f70-9f42-4177-af28-c51ba92608fb
- Related geospatial siting paper: https://ssrn.com/abstract=5160237

No download link or data portal is published. Given the project ends August 2026, an email now
is well timed — and an undergraduate research request costs nothing to send.

**Other UT threads checked and ruled out:**
- **TEX-DEL** (UT-wide Texas Initiative for Datacenter Energy and Large Loads, dirs. Brian Korgel
  / Alex Hanson) — a convening initiative. No datasets published.
- **Pecan Street Dataport** (Austin, UT-founded) — genuinely excellent and partly free to
  university researchers, but it is *residential* consumption. Wrong domain entirely.
- **arXiv:2509.21312** (Texas data center air quality/GHG) — single author, no UT affiliation
  listed, no released dataset.

**Adjacent, non-UT, possibly more useful:** the *Texas Tribune* compiled **248 planned Texas data
centers** from Cleanview + Data Center Map plus its own reporting. It's a facility inventory
(location, some capacity), not time-resolved load, and is not published as a downloadable
dataset — but it is the most complete public siting picture, and the Tribune's data team has a
track record of sharing on request.

Also public and free: **ERCOT/Texas A&M jointly developed PSCAD dynamic models** of AI data
center load and crypto-miner load (`ercot.com/about/grit/large-load-modeling`). These are
*simulation models of load behavior*, not observations — but they encode ERCOT's own assumptions
about what data-center load volatility looks like, which is directly relevant to a volatility
premise.

---

## 4. The endogeneity problem ERCOT introduces

Worth flagging before anyone treats ERCOT as strictly cleaner. The Majumder/Xie paper found that
large flexible loads in ERCOT **curtail in response to expected prices** — specifically to avoid
4CP transmission charges, and responding to day-ahead prices with a measurable lag structure.

For a "does load volatility drive price spikes" question, that is reverse causality sitting in the
core relationship, and it is **worse than anything in the PJM setup**. ERCOT large load is not an
exogenous forcing function; it is a price-responsive agent. Any ERCOT design needs an
identification strategy for this, not just a filter.

---

## 5. Two options, with honest costs

**Option A — Full pivot to ERCOT.**
Rebuild acquisition + preprocessing from zero, including a genuine congestion-reconstruction
module (§2b). Buys the West-zone natural experiment and an ungated price feed. Given the project
already lost a working directory once and is running on a recovery plan, this is a large bet on a
market where the headline dataset still doesn't exist.

**Option B — ERCOT as a replication market (recommended for discussion).**
Keep the existing analysis code and run ERCOT as a second market to test the *surviving* finding:
congestion is level-driven, not volatility-driven, and the pre-registered `z_slope` sign-flips
under a load-level control. This needs only prices + zonal load — no facility-level data, no
new signal-isolation scheme. It converts a null result into a **two-market result**, which is a
stronger deliverable than a half-built second pipeline.

**⚠️ Note the West-zone downgrade (§2c).** An earlier version of this memo treated the West-zone
natural experiment as the anchor for Option A. After the confound review it is no longer that.
West Texas remains a good *descriptive* counterpart to Northern Virginia — two load-growth
hotspots with opposite drivers — but it will not carry a causal identification claim. With that
support removed, **Option B is the stronger recommendation, not merely the cheaper one.**

**Zero-cost actions worth taking regardless:**
1. Email Ning Lin about TRAIL Map data access.
2. Ask Prof. Wei about a request path to the Le Xie group's load-zone crypto data (citation-level
   warm intro already exists via proposal ref [3]).

---

## 6. Concrete pull spec for Option B (ERCOT as DOM's replication partner)

### ⚠️ Binding constraint: the replication must be HOURLY — but the reason is RETENTION, not resolution

**Correction to an earlier draft.** I first wrote that ERCOT publishes actual load only hourly
and that all 5-minute load products are forecasts. **That is wrong.** ERCOT does publish
5-minute *actual* system load in real time (`real_time_system_conditions`,
`loadForecastVsActual`), and `gridstatus.get_load()` returns ERCOT load in 5-minute intervals.

The real constraint is **how long ERCOT keeps it**:

| Product | Resolution | Free history |
|---|---|---|
| Real-time system conditions / `loadForecastVsActual` | **5-min actual** | ~31-day rolling window |
| `NP6-345-CD` / `NP6-346-CD` Actual System Load | hourly | 31-day display; ~1 month back |
| Hourly Load Data Archives (annual zips) | **hourly** | **1995 → 2026, continuous** |
| Backcasted (Actual) Load Profiles | 15-min | annual, settlement-lagged |
| Third-party 15-min "System-Wide Demand" / 5-min feeds | 15-min / 5-min | **2026 onward only** |

So: multi-year *history* at sub-hourly resolution does not exist for free. Only the hourly
archive goes back far enough to match the Feb 2023 → present DOM window.

**Three consequences worth noting:**
1. The hourly panel is the right replication target regardless — the primary DOM findings
   (QR-full congestion, Spec A/B, GPD) are hourly.
2. A 5-minute ERCOT panel **can be built prospectively** by scraping the 31-day rolling window
   on a schedule. That is a real option for future work, just not for a backfill.
3. `gridstatus.io` warehouses `ercot_load` and `ercot_standardized_5_min`. Coverage depth is
   unconfirmed — but going that route **reintroduces exactly the quota problem the ERCOT-native
   path avoids**, which was a main reason to consider ERCOT at all.

### What to pull

| Need | ERCOT product | Resolution | Maps to DOM column |
|---|---|---|---|
| Total price | `NP6-905-CD` Settlement Point Prices at Resource Nodes/Hubs/Load Zones | 15-min → agg hourly | `total_lmp` |
| Energy component | `NP6-322-CD` SCED System Lambda | 5-min → agg hourly | `system_energy` |
| **Congestion** | **derived: SPP − system lambda** | hourly | `congestion` |
| Load level + Z | `NP6-345-CD` Actual System Load by Weather Zone (or annual zips at `gridinfo/load/load_hist`) | hourly, 8 zones | load control + volatility |
| Constraint attribution (optional) | `NP6-86-CD` SCED Shadow Prices & Binding Constraints | 5-min | — |

`NP6-787-CD` (LMPs by Electrical Bus, true 5-min) exists but is bus-level and far larger than
needed for an hourly panel. Skip it.

**The congestion derivation is the one open dependency** — it is exact only if ERCOT SCED is
lossless (§2b). Verify that before building.

### Where from
- **ERCOT MIS public listing** — `https://www.ercot.com/misapp/GetReports.do?reportTypeId=<id>`,
  no API key, no quota. This is what I used to pull the 57 MB SCED file in §1.
- **ERCOT Public API** — `developer.ercot.com`, free registration, better for programmatic bulk.
- **Hourly Load Archives** — annual zips, simplest path for the load backfill.

### Volume — this is the good news
Matching the existing DOM window (Feb 2023 → present, ~3.4 yr ≈ 30,000 hours):

- 8 weather zones × 30,000 h ≈ **240K load rows**
- ~10 settlement points × 30,000 h ≈ **300K price rows**

**Roughly 500K rows total — smaller than the 350,789-row DOM 5-minute panel already built, and
with no quota, no multi-account workaround, and no membership gate.** The acquisition burden is
the lightest part of this project, which is the opposite of the PJM experience.

### Open design decision (not a data question)
Which settlement points play the role of the 7 DOM pnodes. Load zones (`LZ_WEST`, `LZ_NORTH`,
`LZ_SOUTH`, `LZ_HOUSTON`) plus hubs give clean coverage; resource nodes near large-load
concentrations plus a rural control would mirror the DOM design more literally. Given the §2c
confounds, do not assume `LZ_WEST` is a treatment zone — pick nodes deliberately and justify them.

---

## Source index

- ERCOT 60-Day SCED Disclosure (NP3-965-ER): https://www.ercot.com/mp/data-products/data-product-details?id=NP3-965-ER
- ERCOT MIS public listing (ungated): `https://www.ercot.com/misapp/GetReports.do?reportTypeId=13052`
- ERCOT Large Load Integration: https://www.ercot.com/services/rq/large-load-integration
- March 2026 Large Load Interconnection Status Update: https://www.ercot.com/files/docs/2026/03/12/March-TAC-Report.pdf
- ERCOT Large Load Modeling (PSCAD): https://www.ercot.com/about/grit/large-load-modeling
- ERCOT Hourly Load Data Archives: https://www.ercot.com/gridinfo/load/load_hist
- ERCOT Public API: https://developer.ercot.com/applications/pubapi/relnotes/
- ERCOT Marginal Losses (assessment status): https://www.ercot.com/mktinfo/rtm/marginallosses
- EIA — Texas data centers & crypto drive demand growth: https://www.eia.gov/todayinenergy/detail.php?id=63344
- Majumder, Aravena & Xie (arXiv:2408.12014): https://arxiv.org/abs/2408.12014
- UT BEG data center program: https://www.beg.utexas.edu/energyecon/advancing-sustainable-data-center-development-in-texas
- UT TEX-DEL: https://energy.utexas.edu/ut-tex-del
- Texas Tribune data center map: https://www.texastribune.org/2026/06/08/texas-regulation-data-centers-electricity-power-water/
