# JLARC / LBNL data-center rate-impact claims — source-checked (2026-08-07)

Primary sources pulled and parsed directly (not just secondary summaries):
- `Rpt598-2.pdf` — JLARC Report 598, *Data Centers in Virginia* (Dec 2024), full report, 6991-line text extraction saved as `Rpt598-2.txt` in this folder.
- `E3-2026-drivers.pdf` — E3, *Understanding the Drivers of Rising Electricity Rates and the Role of Data Centers* (May 18, 2026), funded by the Data Center Coalition. Text extraction `E3-2026-drivers.txt`.
- `LBNL-2026.md` — LBNL/Brattle, *Retail Electricity Price Trends and Drivers: Data Update — 2026 Edition* (April 2026), scraped via firecrawl (Cloudflare blocked direct fetch).

---

## 1. JLARC Report 598 (Dec 2024) — what it actually found

### (a) Rate impacts TO DATE (present/historical)

JLARC's finding on the *present* is narrow and specific — it's a **cost-allocation fairness finding**, not a "rates haven't risen" finding:

> "Data centers are currently paying their full cost of service, but growing energy demand is likely to increase other customers' costs. JLARC staff commissioned an independent study of electric utility cost recoveries under current rate structures to see if the data center industry is paying its share of current costs. The study found that current rates appropriately allocate costs to the customers responsible for incurring them, including data center customers." (p.v / Ch.4 summary)

On distribution costs specifically (the clearest "no cost shift so far" finding):

> "Utility rate structures appear to effectively insulate other customers from paying for distribution costs associated with data centers. Dominion recovers data center distribution costs by charging them its standard industrial and large commercial customer class rates, but it also contractually requires data centers to make minimum payments that fully recover the cost of the distribution substations built to serve them." (Ch.4, p.46)

**Important distinction the report itself draws (item you asked about):** JLARC never says data centers *won't* raise rates. It says the current rate-design *mechanism* isn't shifting costs today, then immediately pivots to "will likely increase" for the future. The report explicitly flags that current rate structures are inadequate for the scale of growth coming:

> "Current utility rate structures are not designed to account for sudden, large cost increases from new infrastructure construction to serve a relatively small number of very large customers." (Ch.4, p.48)

### (b) PROJECTED rate/bill impacts by 2040

Headline number (summary, p.v): **$14 to $37/month by 2040**, in constant (real) 2024 dollars, for "generation- and transmission-related costs" only (excludes distribution and some transmission projects).

The full Table 4-2 (Ch.4, p.47) breaks this range out by scenario and year, for a Dominion residential customer using 1,000 kWh/month, baselined against $90/month in current (2023) generation+transmission charges:

| Scenario | 2030 | 2040 |
|---|---|---|
| Scenario 1: Unconstrained demand, w/ VCEA (very difficult to achieve) | +$23 | **+$37** |
| Scenario 1: Unconstrained demand, w/o VCEA (very difficult to achieve) | +$22 | +$33 |
| Scenario 2: Half unconstrained demand, w/ VCEA (difficult to achieve) | +$7 | +$14 |
| Scenario 2: Half unconstrained demand, w/o VCEA (difficult to achieve) | +$6 | +$14 |

Notes JLARC attaches to this table:
- Figures exclude distribution charges and "many intrazonal transmission projects" and generation projects not attributable to data centers — i.e., Dominion's own IRP bill projections are "much larger" than these numbers.
- Held in constant/real dollars specifically so the data-center-attributable growth isn't conflated with inflation.
- Zone-level system cost increase (Dominion transmission zone, all customers, not just residential): **+$16–18 billion by 2040 under unconstrained demand**, **+$8.5–10 billion under half-unconstrained** (Ch.4, p.45). "In both scenarios, most of the projected cost increases are attributable to growing data center demand."

Three mechanisms JLARC identifies for why non-data-center customers bear a share despite data centers paying full cost of service today (Ch.4, p.46):
1. Fixed costs of new generation/transmission that "would not otherwise be built" get amortized across all customers over decades.
2. Energy prices rise for everyone as supply is stretched to keep pace with data center demand.
3. Greater reliance on imported power increases exposure to price spikes.

### (c) Load growth scenarios

JLARC/its consultant (E3, using a Virginia-specific model dubbed "WCC" in the appendix for the demand forecast) modeled three scenarios to 2040/2050 (Ch.3, p.30–32; Appendix, ~p.5220–5230):

- **Scenario 1 — Unconstrained demand**: meets the full independent demand forecast, under which "unconstrained demand for power in Virginia would double within the next 10 years, with the data center industry being the main driver." Requires **+54,100 to +56,300 MW** of new in-state generation capacity by 2040 (vs. current 36,000 MW system) and **+3,500 MW** interzonal transmission (vs. 8,700 MW current) — data centers account for the large majority of that net increase (+34,300–35,600 MW of the generation growth). Solar would need to be added at ~2x the 2024 annual rate; new wind (8,800 MW) would exceed all secured Virginia offshore wind capacity (7,400 MW); new gas would need ~one 1,500 MW plant/year for 15 straight years; energy imports would need to more than double. JLARC calls this "very difficult" to build regardless of VCEA compliance.
- **Scenario 2 — Half of unconstrained demand**: **+31,200 to +34,700 MW** generation, **+3,100 MW** transmission by 2040. Still "difficult" — e.g., solar at 650–700 MW/yr (vs. 1,000 MW added in 2024), new gas at one 1,500 MW plant every 2 years for 15 years, imports up >50%.
- **Scenario 3 — No new data center demand**: baseline/counterfactual used only for comparison in the modeling appendix; not narratively developed in the body chapters. (Report notes new generation would still be needed even here "because the grid is expected to shift to cheaper [sources]" — i.e., some buildout happens regardless of data centers.)

VCEA (Virginia Clean Economy Act) compliance is modeled as an overlay on both scenarios 1 and 2, not a separate scenario track.

### (d) Recommendations (all 8, verbatim topic lines from the Summary, p.x–xi)

1. VEDP should clarify that data-center sites are eligible for Business Ready Sites Program grants. (Ch.2)
2. General Assembly should consider clarifying that utilities may **delay, but not deny**, service when load additions can't be supported by transmission/generation capacity. (Ch.3)
3. Expand the Accelerated Renewable Buyers program to let large customers claim partial credit for battery storage purchases (PJM ELCC-based), not just solar/wind. (Ch.3)
4. Require utilities to establish a **demand response program for large data center customers** and require those customers to participate. (Ch.3)
5. Direct **Dominion to develop a stranded-infrastructure-cost risk plan** and file it with the SCC (biennial review or separate filing). (Ch.4) — this is the recommendation most directly tied to the rate-impact finding.
6. Authorize local governments to require **water use estimates** from proposed data centers and consider water use in rezoning/permit decisions. (Ch.5)
7. Authorize local governments to require **sound modeling studies** pre-approval. (Ch.6)
8. Authorize local governments to set and enforce **maximum sound levels** (incl. low-frequency noise metrics) via zoning. (Ch.6)

Note: the *narrative* text of Ch.4 (not a numbered Recommendation, but discussed at length, p.48) also floats — without formally recommending — that the General Assembly **could** require Dominion to establish a **separate data center customer class** and that the SCC/utilities are "in the best position" to pursue new cost-allocation methodologies and more frequent rate adjustments. JLARC explicitly declines to recommend this as binding: "historically the legislature has not set such detailed requirements in statute." **This is exactly what the SCC did on its own authority in Nov 2025** — see §4 below.

---

## 2. The LBNL study the industry cites

There are **two distinct LBNL bodies of work** that get conflated in industry talking points — worth keeping separate:

### 2a. LBNL data-center *energy consumption* report (Shehabi et al., Dec 2024)
This is the "2024 United States Data Center Energy Usage Report" (LBNL-2001637). It's a load-forecasting study, not a rate study: data centers consumed ~4.4% of total US electricity in 2023 (or 4.7% per the updated 2025 figure), projected to reach 6.7–12% (or 9.5–15.3% in later restatements) by 2028/2030. It says essentially nothing about residential rate impacts — it's cited by DCC/E3 only for the load-growth-magnitude backdrop, not the "rates aren't rising" claim.

### 2b. LBNL/Brattle *retail price trends* study — **this is the one actually backing the "rates aren't rising" claim**
**"Retail Electricity Price Trends and Drivers: Data Update — 2026 Edition."** Authors: Ryan Wiser, Galen Barbose, Will Gorman, Eric O'Shaughnessy, Sydney Forrester, Paul Donohoo-Vallett, Peter Cappers, Jeffrey Deason (LBNL) + Ryan Hledik, Long Lam (The Brattle Group). Published **April 2026**, funded by DOE. This is an update/successor to an original Oct 2025 "Factors Influencing Recent Trends in Retail Electricity Prices in the United States" study (same LBNL/Brattle team).

**Key claim (the one DCC/E3 lean on):**
> "From 2019 to 2025, states with the highest growth generally saw average retail prices decline in real terms... Over 1 ¢/kWh reduction in all-sector average prices in highest-growth states... Note: Presence of significant data center load does not appear to alter conclusions." (Slide, "All-sector avg. prices vs. total growth")

> "The presence of significant data center and cryptocurrency growth does not appear to alter these conclusions" [re: residential prices vs. load growth]. (Slide, "Residential prices vs. total growth")

**The explicit, self-flagged exception — this is the part industry citations drop, and it's the one most relevant to a Virginia/PJM DOM analysis:**
> "Case Study: PJM Capacity Auction demonstrates price increases with load growth... PJM's capacity prices increased due to multiple factors, including load growth [attributed specifically to 'Data Center Load Growth' in the figure]... 23–118% increase in auction revenues [various zones]... Capacity prices are one but not the only contributor to retail price increases." (Slide, "Case Study: PJM Capacity Auction")

E3's own May 2026 whitepaper (funded by DCC) states this caveat plainly when summarizing LBNL: *"Lawrence Berkeley National Lab's (LBNL) recent study found similar results, **except in the PJM region**."* (E3-2026-drivers, Executive Summary, p.2)

**Study's own stated limitations** (from the report's "Objectives and Scope" slide):
> "Is not definitive: analyzes subset of drivers from available data, emphasizes need for continued research. Does not analyze drivers in each individual state; analysis focuses on broader trends."

The methodological logic behind the "load growth → lower prices" finding is that **fixed T&D costs get spread over more billed kWh** — a real mechanism, but the study itself flags it's "bi-directional" (price reductions should also stimulate more load, confounding causal attribution) and that it's a **national/state-panel correlation**, not a Virginia-specific or DOM-zone-specific causal estimate. It also doesn't distinguish "hasn't yet" from "won't" — it's describing 2019–2025 realized data, the same window JLARC's *projections* (2025–2040) build forward from.

**Bottom line for our write-up:** LBNL's own report is Virginia/PJM-adjacent evidence *against* the industry's blanket claim, not for it — PJM is the one region singled out by LBNL as showing rate increases tied to load growth (via the capacity auction channel), which is precisely the DOM-zone mechanism this project studies.

---

## 3. 2025–2026 rebuttals / counter-studies

### 3a. Harvard Electricity Law Initiative (Salata Institute) — special contracts and cost shifting
Paper by Eliza Martin and Ari Peskoe, published ~March 5, 2025 ("How You Subsidize Big Tech With Your Electricity Bill"). Reviewed **40 special contracts** approved by state regulators between utilities and data center customers.

Key claims:
- Utilities can strike confidential "special contracts" offering data centers discounted rates; regulators typically grant confidentiality, "limiting public scrutiny."
- If new infrastructure is needed to serve a discounted customer, the shortfall/loss is recovered from other ratepayers.
- Concrete example: Duke Energy's Fayetteville, NC contract with a data center included a **$325 million discount**, and Duke's own court filings acknowledged it would **lose $100 million** on the deal, planning to recoup losses via rate increases on other customers.
- Central thesis: "nearly impossible" for the public to verify the actual size of cost-shifting because contract terms are sealed.

This directly rebuts the "data centers pay full cost of service" framing (which JLARC's finding is also careful to hedge as applying only to *currently observed* Virginia rate structures, not special contracts nationally).

### 3b. Monitoring Analytics (PJM Independent Market Monitor) — capacity auction attribution
Multiple data points across auction years, all consistent in showing a large, quantified data-center attribution to PJM capacity price increases:

- **2025/2026 BRA** (cleared at $269.92/MW-day, an 833% YoY jump from $28.92): Monitoring Analytics attributed **63% of the price increase to data centers, ≈ $9.3–9.4 billion** in incremental costs recovered from PJM ratepayers (widely reported figure, e.g. Bloomberg "$9.4 Billion," June 2025).
- **2028/2029 BRA** (most recent, cleared ~mid-2026): Monitoring Analytics attributed **$6.3 billion of the $16.4 billion in total capacity charges (38%)** to data centers.
- **Cumulative across the last four BRAs** (i.e., 2025/26 through 2028/29): Monitoring Analytics attributes **$29.4 billion of $63.6 billion total (46%)** to data centers.
- Ratepayer pass-through example: Pepco (DC) residential bills rose ~$21/month starting June 2025, tied to the 2025/26 BRA outcome.

These are independent-market-monitor (quasi-regulatory) figures, not advocacy-group numbers, and directly contradict the "no clear relationship between load growth and rising electric rates" framing E3/DCC apply to PJM specifically — E3's own whitepaper concedes ~50% of the PJM capacity price increase (2024/25→2025/26 auction) is attributable to load growth, "primarily data centers," which is in the same ballpark as Monitoring Analytics' 63%. **Both the industry-funded study and the independent market monitor agree PJM capacity prices are the one channel where data centers are demonstrably raising costs — they only disagree on magnitude (50% vs. 63%), not direction.**

### 3c. Academic / other studies E3 itself cites (from E3-2026-drivers.pdf, Executive Summary and body)
- **Bates White** (economic consulting firm) study: found states with the largest load growth (Texas, Virginia) had the *smallest* rate increases; states with declining load (California, New York) had the *largest* increases. (This is the study underlying the "paradox" framing.)
- **Georgia Tech working paper**: found "a small increase in electricity retail rates on average across a subset of US counties after initial data center entry" — E3 characterizes this as needing "further investigation," i.e., E3's own citation admits a counter-finding exists in the academic literature, even if muted.
- **E3's own Amazon case study** (funded by Amazon; 4 utility territories: Georgia Power, Umatilla Electric Co-op OR, and others): found each Amazon data center site generated an average **$3.4 million in net surplus** (revenue exceeding cost-to-serve), used to argue data centers can *lower* costs for others. Caveat E3 discloses itself: "projections evaluated Amazon data centers in isolation, without modeling underlying system changes to supply and demand" — i.e., this is a per-facility rate-design accounting exercise, not a systemwide causal estimate, and it's funded by the data center operator being evaluated.

---

## 4. Virginia-specific 2026 updates

### 4a. SCC implements JLARC's floated (not formally recommended) data-center rate class
In its **Dominion biennial review order (2025)**, the Virginia SCC approved a **new "GS-5" rate class** for the largest electricity users (data centers >25 MW and other very large loads). Effective **January 1, 2027**:
- Minimum payments of **≥85% of contracted distribution and transmission demand**.
- Minimum payments of **≥60% of contracted generation demand**.
- **14-year minimum contract terms**, so large users pay for committed capacity even if actual usage falls short or a project doesn't fully build out.
- This is explicitly a response to the cost-shift/stranded-cost risk JLARC flagged in Recommendation 5 and the unrecommended-but-discussed "separate data center customer class" idea (Ch.4, p.48) — the SCC acted under its existing rate-design authority rather than waiting for a legislative mandate, which JLARC anticipated ("historically the legislature has not set such detailed requirements in statute").

### 4b. Same biennial review — base rate increase outcome
SCC approved **$565.7 million (2026)** and **$209.9 million (2027)** in Dominion base-rate increases — smaller than Dominion's requested **$822 million (2026)** and **$345 million (2027)**, but still a substantial approved increase. (Note: this is total base-rate revenue, not isolated to data-center cost causation — don't conflate with the JLARC $14–37/month figure, which is generation+transmission only and specifically data-center-attributable.)

### 4c. No JLARC follow-up report identified
No evidence found of a JLARC-published follow-up/update report specifically revisiting Report 598's rate findings in 2025–2026. What exists instead is the **E3 whitepaper (May 2026)**, which is *not* a JLARC product — it's **funded directly by the Data Center Coalition**, authored by the same consulting firm (E3) that did JLARC's original 2024 modeling, and it explicitly leans on "E3's prior study for JLARC" as its core evidentiary anchor for the "no historical cost shift" claim. This funding relationship is worth flagging explicitly in our write-up: the industry's 2026 talking points trace back to (a) the original independent JLARC/E3 2024 report, plus (b) a newer, industry-funded E3 report that reuses and extends the same underlying 2024 JLARC-commissioned analysis, plus (c) the LBNL/Brattle national retail-price study reinterpreted through E3's framing (with the PJM exception downplayed).

---

## Precise framing for our write-up (condensed logic chain)

1. **JLARC (Dec 2024, independent, legislative-commission-authored):** Present-day cost allocation is fair (data centers pay full cost of service under current rate design) → but future costs, driven by generation/transmission buildout to serve data-center load growth, will raise a typical Dominion residential customer's generation+transmission charges by **$14–37/month by 2040** depending on scenario, and **$16–18B (or $8.5–10B)** systemwide by 2040 across the Dominion zone. JLARC's own text is explicit that "hasn't shifted costs yet" ≠ "won't."
2. **LBNL/Brattle (Apr 2026, DOE-funded, independent):** Nationally/state-panel, high-load-growth states saw *lower* real retail prices 2019–2025 — but LBNL's own PJM capacity-auction case study is the flagged exception, showing capacity prices (and thus retail prices) rising *because of* data-center load growth. Virginia is in PJM. This exception is the one that matters for our project.
3. **E3 (May 2026, DCC-funded):** Repackages #1 and #2, foregrounding the favorable national LBNL finding and downplaying the PJM exception LBNL itself flags; also cites an Amazon-funded, single-company facility-level accounting study (not systemwide) as evidence data centers can lower costs.
4. **Monitoring Analytics (PJM's independent market monitor, ongoing through 2026) and Harvard's Salata Institute (Mar 2025):** Directly contradict the "no cost impact" framing at the PJM capacity-market level (46–63% of BRA cost increases attributable to data centers, $29–63B cumulative) and at the individual-contract level (opaque special contracts shifting stranded-cost risk to other ratepayers).
5. **SCC (Nov 2025 order, effective Jan 2027):** Regulatory action taken *because* the projected cost-shift risk (JLARC's finding) was judged real enough to warrant a new rate class and 14-year minimum commitments — itself indirect evidence that Virginia's own regulator did not read JLARC's report as "data centers won't raise rates."
