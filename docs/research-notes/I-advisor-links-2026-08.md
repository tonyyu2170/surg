# Advisor-Suggested Links — Industry Frameworks, Load Shape, and Forecast Error

Research date: 2026-08-11. Primary documents read in full where retrievable; secondary
coverage used only where noted and labelled as such.

Covers the five links parked under "Links i need to look into" in
`docs/plans/2026-08-19-advisor-meeting-agenda.md` (agenda TODO item 5).

**Link/title pairing correction.** The agenda's five bullets pair two titles with the
wrong URLs if read as consecutive pairs. Actual mapping:

| Title | Actual URL | What it really is |
|---|---|---|
| Headroom / Industry Playbook | `epri.com/research/products/000000003002034162` | EPRI product page (**not retrievable**, see §4) |
| *(no title given)* | `nerc.com/.../lltf_april_meeting__technical_workshop_presentations_.pdf` | NERC LLTF workshop deck, 145 pp (§3) |
| ML Guided Cooling System Optimization | `arxiv.org/pdf/2601.02275` | Separate arXiv paper (§5) |
| *(no title given)* | `ferc.gov/.../PJM FERC Technical Conference 2024 - Hourly Electricity Load Forecasting...` | PJM ML load-forecasting deck (§1) |
| *(no title given)* | `powering-intelligence.epri.com/annual-peak-use.html` | EPRI load-shape chapter (§2) |

---

## 0. Headline — the sources converge on one thing, and it is not what the proposal assumed

Read together, three independent sources (PJM's forecasters, EPRI's metered facility
data, and NERC/Tesla's disturbance records) say the same thing about the timescale
structure of data-center load:

- **At hourly and 5-minute resolution, data-center load is unusually FLAT**, not spiky.
  EPRI's metered facilities show annual load factors of 75% (hyperscale) and 57% (colo)
  against nameplate, and 94%/88% against their own realized peak — i.e. these facilities
  sit near their own peak nearly all the time. EPRI states plainly that "aggregate DC
  load tends to be relatively constant through the year."
- **The volatility that industry actually worries about lives at 0.1–30 Hz** — seconds
  and sub-seconds. Tesla's slides quantify it: "slow" 0.1–1 Hz, "fast" 5–30 Hz, swings
  up to 90% of peak.
- **Every stated consequence of that sub-second behavior is a reliability or
  power-quality consequence** — voltage flicker, nearby-generator interaction, frequency
  regulation, inter-area oscillation, ride-through, UFLS. Across all five sources, **not
  one claims an energy-price (LMP) effect from load volatility.**

  (The single price claim anywhere in this batch — EPRI/GridCARE, §4 — runs the *other*
  way and concerns load **growth** lowering **average** prices via better utilization,
  not volatility raising tail prices. It does not weaken this point, but the advisor will
  probably raise it, so it is flagged rather than buried.)

This matters directly for sub-question 1. The natural temptation is to read the EPRI
sub-second footnote as "we measured at the wrong resolution, so the effect is hidden
below our data." That reading is wrong and would be vulnerable on review. LMP is
computed on 5-minute dispatch intervals; 0.1–30 Hz jitter is absorbed by AGC/regulation
and by on-site UPS/inverter response, and **never enters the energy price stack at all.**

The defensible framing is stronger:

> The data-center volatility phenomenon the industry documents is a **different
> dependent variable**. It lives in reliability and power quality, not in energy price
> formation. The project's null result on hourly/5-min volatility → price is therefore
> **substantive, not instrumental** — and these sources independently explain *why* load
> level, not load volatility, is the channel that reaches price.

This converts three existing findings from awkward nulls into a corroborated result:
level beats volatility in 100% of panels; normalized volatility is flat-to-falling;
5-minute tests came out *weaker* than hourly rather than stronger.

If a genuine price channel for sub-second behavior is wanted, it is **regulation and
frequency-response procurement cost**, not LMP. That should be named as a distinct open
extension, not blurred into the volatility finding.

**Corroborating detail — NERC's own risk register never mentions price.** In White Paper
1's prioritization (§3.5), *every* High-priority risk is reliability or adequacy. Demand
forecasting sits at Medium. "Voltage Fluctuations" is explicitly **Low**. A body whose
entire remit is large-load risk, surveying industry, did not rank price formation as a
large-load risk at all.

---

## 1. PJM — "Hourly Electricity Load Forecasting Using Machine Learning Algorithms"

**Highest-value source of the five.** Primary, from PJM's own load-forecasting group, and
it is about the project's exact zone.

FERC Technical Conference, July 9, 2024. Yinghua Wu, Laura Walter, Anthony Giacomoni
(PJM); acknowledges Kexin Xie, PhD candidate, Virginia Tech Statistics. 17 slides.

### Setup
- Two operational forecasts: **short-term hourly** (7 days ahead; feeds the 11:00
  Day-Ahead close and the 18:00 Reliability Assessment & Commitment run) and **very
  short-term 5-minute** (6 hours ahead; feeds SCED).
- Models tested: **XGBoost, neural network, LSTM, Transformer.** Test period April 2023 →
  May 2024, progressing monthly; training on the past seven years.
- Features: calendar (year/month/weekday/hour/holiday), weather (temperature, dew point,
  wind speed, cloud cover), temperature differences ±3 hours, and lagged MW/temperature
  at current hour, same hour yesterday, and same hour last weekday.
- PJM scale as of 2/2024: peak load 165,563 MW; 180,785 MW capacity; 65M+ people; 13
  states + DC; annual energy 770 (the stat box labels this "Gigawatt hours"; against a
  165 GW peak the numeral is right and the **unit label** should read TWh).

### The finding that matters
> **"XGBoost improves all large zones except Dominion."**

And in the conclusion:
> **"Dominion data center load is challenging and will be more so in next few years."**

RTO-level improvement is large — RMSE 1,909 → 1,523 MW on the economic-benefit metric,
1,835 → 1,267 MW on the reliability metric. **Dominion is the single zone where the
machine-learning approach fails to beat the production forecast.** PJM's fix is a second
"bias learner" (Forecast Error ~ MW(Forecast) + Hour, XGBoost again) stacked on the MW
learner. Their reported result: bias correction **"significantly improved forecast in
Dominion,"** **"did not impact forecast in other zones,"** and is **"robust."**

⚠️ *Caveat on the bias-correction numbers.* The slide is titled "Bias Correction in RTO"
and lists Hour 10 Day 0: Prod 371 / XGB 393 / BC 326; Hour 10 Day 1: 407 / 398 / 356;
Hour 18 Day 0: 256 / 313 / 243; Hour 18 Day 1: 390 / 351 / 312. These magnitudes are an
order of magnitude below the RTO RMSEs on slide 8 (1,267–1,909 MW), so they are probably
zonal (Dominion) or a different error metric. The plots are images, so this cannot be
resolved from extracted text. **Do not cite these four triples as RTO-level RMSE without
checking the slide visually.**

### Why this is useful to the project
1. **It is a predictability problem, not a volatility problem.** PJM's difficulty in DOM
   is forecast *error and bias* — a conditional-mean problem — not excess high-frequency
   variance. This is a third independent line of support for the level-not-volatility
   framing in §0, from the system operator itself.
2. **It is an operator-side admission of DOM exceptionalism**, which the project has so
   far had to establish statistically. PJM saying "all large zones except Dominion" is a
   citable, non-statistical corroboration that DOM is the anomalous zone.
3. **Direction-of-trend contrast:** the deck's slide 10 shows RTO load trending *down*
   while Dominion trends *up*. Consistent with the project's load-growth findings.
4. Dominion data-center figures given: **67 connected data centers** (stated as 35%
   worldwide), 15 connected in 2023 and 15 more in 2024; hourly-average data-center load
   **2.7 GW (2022) → 3.2 GW (2023)**; "Dominion expects 10 GW data center load by 2035";
   "70% of the world's internet traffic flows through Virginia data centers." The last
   two are sourced by PJM to Data Center Frontier and VEDP, i.e. **PJM is repeating
   industry marketing figures, not publishing its own measurement** — cross-check the
   10 GW/2035 and 70%-of-traffic claims against `C-capacity-forecast.md` and
   `B-loudoun-geography.md` before reuse.

**Novelty check:** nothing on XGBoost, bias correction, Giacomoni, or PJM ML forecasting
appears anywhere in the existing corpus. **Entirely new to the project.**

Source: [PJM / FERC Technical Conference 2024 (PDF)](https://www.ferc.gov/sites/default/files/2024-07/PJM%20FERC%20Technical%20Conference%202024%20-%20Hourly%20Electricity%20Load%20Forecasting%20Using%20Machine%20Learning%20Algorithms.pdf)

---

## 2. EPRI *Powering Intelligence 2026* — "Annual and Peak Electricity Use"

Primary, retrieved in full. Page last updated **February 24, 2026**.

This is the **empirical load-shape evidence** the project has been missing, and it speaks
directly to agenda TODO item 7 ("Is data-center load actually spiky? Your proposal
assumes it and cites two papers; nobody has checked it against data").

### Metered facility load shapes — the core numbers
EPRI collected facility-level load-shape data from several anonymous facilities
(EPRI 2025c):

| Metric | Hyperscale (>75 MW, single tenant) | Colocation (<75 MW, multi-tenant, avg of 3) |
|---|---|---|
| Peak utilization vs nameplate | 0.80 | 0.64 |
| Annual load factor vs nameplate | **75%** | **57%** |
| Annual load factor vs own realized peak | **94%** | **88%** |

Peak utilization across the sample runs **62–80% of nameplate**. EPRI's own reading:
"observed profiles ... show high, relatively flat utilization"; "aggregate DC load tends
to be relatively constant through the year."

The 94%/88% figures are the striking ones for this project: measured against their own
realized peak, these facilities are at ~90% of peak essentially all year. **That is close
to the flattest load shape on any grid.**

### The sub-second footnote (footnote 1) — quoted in full because the framing turns on it
> "Despite relatively constant levels of output across minutes and hours, abrupt and
> large changes in load at second and sub-second timescales (that result from coordinated
> computing tasks stopping and starting) can have significant implications for
> **operational reliability of the grid**."

Note what the consequence clause says and does not say: operational reliability. Not
price. See §0.

### Methodology (useful as a modelling template)
- **PUE:** US capacity-weighted average **1.32 in 2024**; older enterprise 1.5+;
  hyperscale liquid-cooled builds could reach **1.1** (LBNL 2024).
- **Ramp assumption:** a new facility runs at **20% of nominal capacity in year 1,
  +20%/yr** to full deployment. This is why nominal capacity and energy use diverge.
- **Validation approach worth stealing:** EPRI cross-checks modelled DC demand against
  EIA State Energy Data System C&I retail sales for VA, TX, OR, IA, and concludes the
  estimates "could not be significantly higher and still be consistent with observed
  total electricity sales." A bounding argument from public aggregates.
- ⚠️ **Data caveat with direct relevance to this project's panels:** DC load "is sometimes
  reported by EIA as commercial demand and sometimes as industrial demand," with
  reclassification over time visible in Oregon and Virginia, driven by tariff class or
  interconnection terms.

### Magnitudes
- **2024 US DC electricity use: 177–192 TWh**, ≈2× 2021 — while nominal capacity grew
  ≈3–4× over the same period. (Energy has grown *slower* than capacity.)
- **2030 projections: 383 (Low) / 596 (Medium) / 793 (High) TWh** — 2–4× 2024, and
  **~60% above EPRI's own 2024-vintage scenarios.**
- Nominal capacity ~10 GW (2021) → 55–135 GW (2030).
- **Non-coincident aggregate US DC peak: 21–22 GW (2024) → 45 / 71 / 94 GW (2030)**,
  explicitly *before* any flexible demand response.
- Fleet-average utilization fell ~0.7 → ~0.4 historically (a ramp artifact, not a
  behavior change), recovering to 0.55–0.65 by 2030; always below 100%.

### Planner-facing implication EPRI states directly
"Realized peak demand is lower than maximum/nameplate capacity" — "a key consideration
for power system planners translating announced MW into near-term peak impacts."

**Novelty check:** PUE appears in `external-context-research-2026-08.md` and
`B-loudoun-geography.md`; load factor appears only in ISO data-availability docs in an
unrelated sense. **The metered load-shape numbers and the TWh/GW projections are new.**
Cross-check the 2030 figures against `C-capacity-forecast.md` before citing both.

Source: [EPRI Powering Intelligence 2026 — Annual and Peak Electricity Use](https://powering-intelligence.epri.com/annual-peak-use.html)

---

## 3. NERC LLTF April 2025 Workshop Deck — mostly superseded, but three things survive

Primary, 145 pages, read in full. NERC Large Loads Task Force meeting and workshop,
**April 10, 2025, Austin TX.**

### ⚠️ Status: this deck is 16 months old and its forward-looking content has landed
The deck presents White Paper 2 and the Reliability Guideline as *upcoming*. Both have
since published, and `E-flexible-load.md:148` already tracks the sequel events (Level 3
Alert, Reliability Guideline, FERC-ordered mandatory standards for Board adoption
December 2026). **Cite the published documents, not these slides:**
- White Paper 1 — [Characteristics and Risks of Emerging Large Loads](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/3_doc_white-paper-characteristics-and-risks-of-emerging-large-loads.pdf)
- White Paper 2 — [Assessment of Gaps in Existing Practices, Requirements, and Reliability Standards](https://www.nerc.com/globalassets/our-work/guidelines/reliability/white-paper---assessment-of-gaps.pdf) (published **March 2026**; finds existing NERC standards "inadequate for the reliable integration of emerging large loads")
- [Reliability Guideline: Risk Mitigation for Emerging Large Loads](https://www.nerc.com/globalassets/our-work/guidelines/reliability/RG_Risk-Mitigation-For-Emerging-Large-Loads.pdf) (published **May 2026**; voluntary, non-binding)

### 3.1 The Tesla slides — best available quantification of the sub-second phenomenon
This is the part of the deck worth keeping. Presented by Tesla (Megapack team):

- **Fluctuation spectrum of AI training load:** "slow" seconds-scale variation
  **0.1–1 Hz**; "fast" millisecond-scale variation **5–30 Hz**; **up to 90% power demand
  fluctuation (100% → 10%)**.
- Musk, August 2024 (Lex Fridman interview, on xAI Memphis): *"when you do synchronized
  training it's like having an orchestra and it can go loud to quiet very quickly, at the
  sub-second level. The electrical system freak out about that — with **10-20 MW shifts
  several times per second**."*
- Google Technical Lead Manager & VP Engineering, February 2025 blog: *"In our latest
  batch-synchronous ML workloads running on dedicated ML clusters, we observed power
  fluctuations in the **tens of megawatts**."*
- Stated impacts — **all reliability/power-quality**: on-grid, voltage flicker, nearby
  generator interactions, frequency regulation challenges, inter-area oscillation
  excitation; off-grid, generator oscillations beyond specification.
- Mitigation: parallel Megapack with grid-forming controls reduces **70%+ of
  variability**; measurement-based control alone is ineffective at high frequencies due
  to control delay. Tested beyond 25 MW.
- Scale references: **xAI Colossus — 200k GPU, ~250 MW**; Tesla Gigafactory Texas — 130 MW
  data center, 130 MW/260 MWh behind-the-meter Megapack plus 125 MW/250 MWh
  front-of-meter ERCOT-participating system.

**Use:** cite these as the *characterization* of a phenomenon the project's data cannot
see and, per §0, does not need to see for a price question.

### 3.2 Ride-through field records — independent corroboration, no new numbers for DOM
AEP (Robert O'Keefe) presented relay oscillography from two 2025 138 kV faults: Data
Center A (90 MW) rode through the initial fault and all three reclose attempts; Data
Center B (68 MW) tripped after the 2nd reclose; Data Center C (80 MW) tripped after the
2nd reclose. One owner's logic trips after 3 voltage dips within <1 minute. Both data
centers and crypto mines present a **"mostly constant power characteristic"** during
voltage dips. Fault-clearing context: normal clearing 3–6 cycles; high-speed reclose
20–30 cycles; 1–3 timed recloses at 5–20 s.

The Tesla deck also cites **"Dominion: 1.5 GWs across 60 data centers, July 2024 — due to
reclosing attempts on faulted 230 kV system."** This **agrees with**
`H-event-catalog.md:19` (2024-07-10, Fairfax County, ~1,500 MW across ~60 facilities,
lightning-arrestor failure + reclose logic) — the catalog entry is already more detailed.
Logged here as second-source corroboration only; **no update to the catalog needed.**

Worth noting for the reconciliation flagged in memory (worst response $13.30, two
excursions moved *up*, versus the trip's $80.06): 1.5 GW of load **dropping off** is an
over-frequency event, so falling or mixed prices are the physically expected response,
not a scarcity spike.

### 3.3 Load-composition parameters — useful if load modelling is ever needed
- EPRI (Parag Mitra): **~90% of data-center load is electronically driven** (SMPS +
  electronic drives); lighting and cooling 20–40% of total; each building ~40 MW,
  campuses >1 GW; cryptomining 800–900 MW and mostly without UPS.
- Entergy (Maryclaire Peterson): **IT ~80% / cooling ~18% / misc ~2%**; undervoltage
  disconnect at **V < 0.65 pu instantaneous**; reconnect at **V > 0.65 pu with an
  8-second ramp**. Their N-1-1 study found nearby generators **lose synchronism within
  the first 2 seconds** — well before load returns at 8 s. 70% increase in load
  interconnection studies in the past 1–2 years.

### 3.4 ERCOT context numbers (Woody Rickerson, COO)
Large-load interconnection queue as of March 2025, by year: 2,634 (2022) / 4,680 (2023) /
5,239 (2024) / 17,050 (2025) / 34,356 (2026) / 70,889 (2027) / 97,161 (2028) / 103,128
(2029) / **108,281 MW (2030)** — with the explicit caveat that it is "difficult to
determine what should be included in planning forecasts." Lead-time asymmetry: load 6–18
months, generation 9–24 months, **transmission 3–6 years**. Supply side: 2009–2024 saw
only **1,700 MW net new dispatchable thermal** (23,083 added / 21,354 retired) against
**61,027 MW net new solar and wind**; 400 GW of active generation interconnection
requests, 42.3% battery and 39% solar.

### 3.5 White Paper 1 risk prioritization — see §0
- **High:** Resource Adequacy; Balancing and Reserves; Dynamic Modeling; Ride-through;
  Frequency Stability; Voltage Stability; Oscillations; Automatic UFLS Programs.
- **Medium:** Short-Term Demand Forecasting; Lack of Real-Time Coordination; Demand
  Forecasting; Transmission Adequacy; Resilience.
- **Low:** Harmonics; **Voltage Fluctuations**; Cyber Security; System Restoration.

Nine load characteristics were identified: peak demand, fast interconnection timeline,
demand profile, load predictability, ramp rate, load type (PEL/motors), voltage
sensitivity, inaccurate dynamic models, internal segmentation. Note that **"load
predictability" is a named characteristic distinct from "ramp rate"** — the same
distinction PJM's forecasting results make empirically (§1).

Source: [NERC LLTF April 2025 workshop presentations (PDF, 145 pp)](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/llwg/lltf_april_meeting__technical_workshop_presentations_.pdf)

---

## 4. EPRI Headroom Framework / Flex MOSAIC™

**Retrieval note:** `epri.com/research/products/000000003002034162` and
`headroom.epri.com` are JavaScript-only shells (raw HTML ~1.6–10 KB, "You need to enable
JavaScript to run this app"). Direct fetch, WebFetch, Exa, and Firecrawl all failed;
`sitemap.xml`/`robots.txt` 404. **Retrieved via browser session.** The report is a
web-published discussion paper at `headroom.epri.com/*.html`, last updated
**12 June 2026**. Executive Summary and Introduction read in full; deeper chapters
("Drivers of Power System Headroom" onward) not read. Flex MOSAIC™ detail below remains
**secondary**.

### Definition
> "Headroom, as presented in this framework, is **the amount of new load (MW) a system
> can integrate across all time periods before violating reliability requirements**" —
> elsewhere: "without expansion of central power generation, energy storage, or
> transmission capacity before system limits are breached."

Note the definition is **entirely reliability-constrained**. Not a cost or price
constraint. Consistent with §0.

### The four-step analytical ladder
Each step is repeated for **both inflexible and flexible** DC load, so the framework
outputs headroom *as a function of* flexibility:

1. **Probabilistic resource adequacy** — how much DC load fits across a wide range of
   uncertain operating conditions.
2. **Hourly nodal grid operations simulation** — realistic generation constraints,
   transmission limits, strategic siting; "energy supply limitations and network
   congestion can materially shape headroom."
3. **Sub-hourly nodal operations simulation** — "higher resolution temporal system
   changes, such as **rapid DC load swings and ramping requirements**."
4. **Power flow simulation** — transmission reliability and locational risks.

⚠️ **Nuance worth carrying into the advisor meeting.** Step 3 shows EPRI *does* treat
sub-hourly DC load swings as headroom-relevant. This does not undercut §0 — the output
variable is still MW of integrable load under reliability limits, not price — but it
means "industry ignores sub-hourly swings" would be an overstatement. The accurate
statement is that industry models sub-hourly swings **as a reliability/ramping
constraint**, never as a price-formation channel.

### ⚡ A direct price claim — the one place any of these five sources touches price
Summarizing GridCARE (2025), the Introduction states:

> "Results from the analysis are echoed in a recent EPRI report investigating DC and
> other load growth, showing that **under the right conditions growing loads can lower
> average electricity prices** and improve utilization of the existing system, among
> providing other societal benefits."

This is the **opposite sign** from the proposal's implicit premise. It is a modelled,
conditional, average-price claim (better utilization of fixed infrastructure spreads
costs), not a wholesale-LMP-tail claim, so it does not contradict the project's findings
directly — but it is a live, citable, industry-side counter-narrative and the advisor
will likely raise it. The underlying EPRI report is cited as reference 6 and was **not
retrieved**; run it down before relying on this.

### Literature the framework positions itself against — three new leads
- **Norris et al. (2025)** — the Duke "Rethinking Load Growth" study already in
  `E-flexible-load.md`: 76–126 GW of new load at 0.25%–1.0% annual curtailment. EPRI's
  own assessment is a **polite critique**: a "first-order assessment, using demand curves
  and focusing on ensuring that total load stayed below system peaks," with the authors
  acknowledging that realistic network, inter-temporal, and uncertainty constraints are
  needed for planning decision support. **This is a second authoritative critique of the
  Duke study alongside the Handshy critique** already logged at `E-flexible-load.md:126`.
- **Brancucci, Culter, and Jenkins (2025)** — ⚠️ **most relevant new lead in this note.**
  A **multi-site data center interconnection study within PJM territory**, quantifying
  the expected curtailment profile of flexible large loads **at specific locations**,
  considering generation and transmission constraints, across all hours of the year.
  Tiered modelling: systems model → coordinated production-cost and power-flow planning
  models → site planning model. Finding: flexible DCs could connect **3–5 years sooner**
  than inflexible ones while improving utilization and lowering costs. A locational,
  all-hours, PJM-specific study is the closest thing in this batch to the project's own
  unit of analysis. **Track this down.**
- **GridCARE (2025)** — stylized economic analysis of a 1 GW DC in a representative
  mid-sized service territory, modelling how tariff revenue from the DC might offset
  costs and lower customer rates; assumes substantial DC flexibility (50% annual capacity
  factor).
- **EPRI (2025) Texas study** — synthetic grid model (Texas A&M *Texas Combined Electric
  Gas Test Case*, 7k electric-gas), hourly operations simulation with zonal transmission
  constraints, showing strategic siting plus flexibility enhances both speed and scale of
  DC integration.

### Status and framing
Explicitly **a proposal / discussion paper**, not a finished method: EPRI plans case
studies in active planning settings plus industry workshops, then a refined version for
implementation at scale, and is soliciting comment. Positioned as complementary to Flex
MOSAIC™ — Flex MOSAIC defines flexibility classes, Headroom quantifies what those classes
unlock. Framing quote: *"As data centers reshape load growth patterns, the planning
question shifts from whether new demand can be served to how intelligently it can be
integrated."*

### Flex MOSAIC™ (secondary sources only)
A voluntary classification system translating a facility's operational flexibility into
defined performance attributes — **notification time, duration, ramp rate, and depth of
load adjustment** — each mapped to grid needs such as peak reduction, congestion relief,
and emergency response. Launched **23 April 2026** with 65+ utilities, operators,
regulators, hyperscalers and vendors (Google, Meta, NVIDIA, Siemens, Constellation,
Southern, Exelon, MISO, CAISO, APS). EPRI CEO Arshad Mansoor: flexibility is "the third
leg of the speed-to-power stool, alongside generation and transmission."

**Fit to the current question:** still the weakest of the five for the econometrics — it
is planning/interconnection methodology. But it is **more relevant than it first
appeared**, for three reasons: the GridCARE price claim, the Brancucci/PJM locational
study, and EPRI's critique of the Duke headroom result the project already cites.

⚠️ **Terminology collision to avoid.** `E-flexible-load.md:126-127` already discusses
"headroom" in the **Duke "Rethinking Load Growth"** sense (curtailment-enabled headroom;
76–126 GW; the Handshy critique that system-level headroom is being misapplied to
individual interconnection requests). **EPRI Headroom ≠ Duke headroom** — different
method, different actor, different claim. The NERC deck's Tesla slides cite the Duke
version (22 balancing authorities, 95% of US peak, 10% of US peak unlockable with 0.25%
curtailment of new load, 2–5 hr shifts via on-site BESS), which is already covered.
Whichever is cited, name which one.

Sources (all secondary): [Energy Central — EPRI's Headroom Framework](https://www.energycentral.com/energy-management/post/epri-s-headroom-framework-advances-grid-planning-as-data-centers-become-RJakjOlDggf0Hnc), [DCD — EPRI launches flexibility framework](https://www.datacenterdynamics.com/en/news/epri-launches-data-center-flexibility-framework-to-speed-up-grid-connections/), [DCFlex homepage](https://dcflex.epri.com/)

---

## 5. "Machine Learning Guided Cooling System Optimization for Data Center" (arXiv 2601.02275)

Primary, read in full. Shrenik Jadhav and Zheng Liu, University of Michigan-Dearborn.
v3, 6 August 2026. Won the Avram Bar-Cohen Best Paper Award, Data Centers Thermal
Management track, IEEE ITherm 2026.

### What the paper does
A three-stage physics-guided ML framework on the **Frontier exascale supercomputer**
(Oak Ridge, warm-water liquid cooled): (1) a monotonicity-constrained gradient-boosting
surrogate predicting facility accessory power from coolant flows, temperatures and server
power; (2) that surrogate as a physics-consistent baseline to quantify excess cooling
energy; (3) guardrail-constrained counterfactual setpoint adjustments.

Results: surrogate MAE **0.026 MW**, predicting PUE within ±0.01 for **98.7%** of test
samples; **~85 MWh of annual cooling inefficiency** identified, concentrated in specific
months/hours/regimes; **up to 96% recoverable** through small, safe setpoint changes.
Code at [github.com/m-iml/ML-Optimization-Data-Centers](https://github.com/m-iml/ML-Optimization-Data-Centers).

### Direct relevance to this project: essentially none
This is facility thermal engineering — cooling-plant micro-optimization behind the meter.
It says nothing about price formation, market structure, or grid-side load behavior. On
the project's actual question it is the least relevant of the five.

### But it contains one genuinely valuable lead
The paper's data source is a **public, facility-level, full-year, 10-minute-resolution
telemetry dataset for a ~20 MW compute load** — the kind of data the project has been
hunting for thirteen weeks (agenda TODO item 7).

**Frontier HPC & Facility Data**, 2023-01-01 → 2023-12-31, **49,869 records** after
cleaning (vs 52,560 in a complete year; gaps are scheduled downtime and telemetry drops).
The paper describes it as "the publicly released Frontier HPC & facility dataset."

| Variable | Description | Typical range |
|---|---|---|
| P_IT | IT/compute power | **8–29 MW** |
| P_acc | Facility accessory power | 0.5–1.1 MW |
| T_sup | Coolant supply temperature | 18–25 °C |
| T_r,i | Subloop return temperatures | 25–40 °C |
| Q_heat | Total waste heat | 5–25 MW |
| PUE | Power usage effectiveness | 1.03–1.10 |

Each record carries synchronized per-loop coolant temperatures and flows, compute power,
facility accessory power, total power, and PUE, plus derived calendar fields.

Dataset citations: J. Sun, Z. Gao, D. Grant et al., "Energy dataset of Frontier
supercomputer for waste heat recovery," ***Scientific Data*** vol. 11, p. 1077, 2024; and
D. Grant et al., "Frontier HPC & facility data," 2024, dataset. *Scientific Data* is
open-access with a mandatory data-availability statement, so the repository location
should be directly recoverable from the article.

**A fourth independent data point on flatness:** the paper's own exploratory analysis
reports waste heat "dominated by the 5 to 15 MW range with only **modest daily and weekly
seasonality**, indicating a **relatively steady** but unevenly distributed source." A
year of 10-minute metered data from a ~20 MW compute load, characterized by its own
authors as steady.

### ⚠️ Limits before treating Frontier as a data-center proxy
1. **Frontier is an HPC/scientific supercomputer, not a commercial AI data center.**
   Batch-scheduled scientific jobs have a different power signature from
   batch-synchronous AI training — and synchronized AI training is precisely the workload
   the Tesla/Google/Musk sub-second observations describe.
2. **10-minute resolution still cannot see the 0.1–30 Hz band.** It confirms flatness at
   the resolution the project already studies; it cannot test the sub-second claim.
3. **PUE 1.05 is exceptional** and not representative of the 1.32 fleet average (§2).
4. Single site, single year (2023), single cooling architecture.

**Verdict:** low value as a citation, potentially high value as a **dataset lead**. Worth
one hour to locate the *Scientific Data* deposit and check whether IT power is released
at 10-minute granularity in a usable form.

Source: [arXiv 2601.02275](https://arxiv.org/pdf/2601.02275)

---

## 6. What this changes, and what it does not

**Changes:**
1. **Framing of the sub-q1 null (§0).** Strengthens it from "we found nothing" to "the
   phenomenon is a different dependent variable, and here is independent evidence."
   This is a methodology-level implication — per the append-only rule, if adopted it
   belongs in a **new** `docs/decisions.md` entry citing the prior one, never an edit.
2. **DOM exceptionalism now has operator-side corroboration** (§1) independent of the
   project's own statistics.
3. **Agenda TODO item 7 is partly answered before the UKPN data arrives** (§2): metered
   facility load shapes say data-center load is flat at hourly resolution. The proposal's
   spikiness assumption is contradicted at the resolutions this project can observe, and
   supported only at 0.1–30 Hz.
4. **A new candidate dataset** (§5) for facility-level compute load.
5. **A counter-narrative to prepare for** (§4): EPRI/GridCARE's claim that load growth
   can *lower* average prices. Different variable from the project's, but the advisor is
   likely to raise it.
6. **A second authoritative critique of the Duke headroom study** (§4), from EPRI itself,
   to sit alongside the Handshy critique in `E-flexible-load.md:126`.

**Does not change:**
- No source tests a volatility → price hypothesis; that remains the project's own
  contribution.
- No update needed to `H-event-catalog.md` (§3.2 corroborates the existing entry).
- Nothing here bears on the cross-ISO Stage-1 results or the MISO LRZ3_5/LRZ4 hub-sharing
  caveat.

## 7. Open items

1. **Chase Brancucci, Culter & Jenkins (2025)** (§4) — a multi-site, all-hours,
   locational DC interconnection study *inside PJM*. Closest external work to this
   project's unit of analysis; highest-value follow-up in this note.
2. **Locate the Frontier dataset deposit** via the *Scientific Data* article (§5) and
   check granularity/licensing.
3. **Run down the EPRI report behind the "growing loads can lower average electricity
   prices" claim** (§4, cited there as reference 6) before it gets cited or rebutted.
4. **Visually check PJM slide 16** (§1) to resolve whether the bias-correction RMSEs are
   RTO-level or Dominion-level.
5. **Cross-check before joint citation:** EPRI 2030 TWh/GW projections (§2) against
   `C-capacity-forecast.md`; PJM's repeated "10 GW by 2035" and "70% of internet traffic"
   marketing figures (§1) against `B-loudoun-geography.md`.
6. **Decide whether the §0 framing is adopted** — a user/advisor call, not an
   implementation detail. If adopted, it wants a new `decisions.md` entry.
7. *(Optional)* Read the unread Headroom chapters ("Drivers of Power System Headroom"
   onward) if the framework becomes relevant beyond context.
