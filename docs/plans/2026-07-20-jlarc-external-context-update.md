# Sub-Q2 External-Context Research Update (2026-07-20)

> **Status:** Research only — no design or code changes. This updates the
> factual baseline behind `docs/plans/2026-05-14-jlarc-projection-design.md`
> and `docs/plans/2026-05-14-jlarc-rpt598-key-figures.md`, both of which are
> frozen extractions of a December 2024 JLARC report and are now ~19 months
> stale on the fast-moving parts of this story. Per CLAUDE.md, sub-q2
> implementation plan-writing stays gated on the advisor meeting
> (roadmap item #5); this document is exactly the kind of ungated
> reconnaissance that can happen ahead of that gate. Nothing here should be
> read into `data/config/growth_scenarios.yaml` without a separate,
> explicit config-update step once plan-writing unlocks.
>
> Scope: three research tracks requested by the user — (1) data center
> infrastructure growth projections, (2) data center efficiency
> innovations, (3) grid infrastructure growth. All findings below are from
> live web search on 2026-07-20; my training cutoff is January 2026, so
> everything dated Feb–Jul 2026 was previously unknown to me and should be
> read as freshly verified, not recalled.

## 1. DC infrastructure growth projections — the JLARC baseline is badly out of date

**Headline finding: PJM's own forecast for DOM-zone data-center growth by
2037 has nearly quadrupled since the JLARC report was written.**

| Vintage | DOM-zone DC-driven growth by 2037 |
|---|---|
| 2022 PJM forecast (JLARC's implicit baseline) | ~5,700 MW |
| 2025 PJM forecast | **>20,000 MW** |

Source: [PJM Dials Back Near-Term Load Outlook but Maintains Steep
Long-Term Growth Trajectory](https://www.powermag.com/pjm-dials-back-near-term-load-outlook-but-maintains-steep-long-term-growth-trajectory/).

**PJM's January 2026 Load Forecast Report** (posted 2026-01-14, fetched
and read directly —
[source PDF](https://www.pjm.com/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report.pdf))
gives the DOM-zone-specific numbers the 2024 JLARC extraction didn't have
(JLARC's Figure 3-3 was statewide-Virginia only):

- **DOM zone annualized peak-load growth: 5.4%/yr (10-yr), 4.9%/yr
  (15-yr), 4.1%/yr (20-yr) — summer peak.** Winter: 5.1%/4.7%/3.9%.
  This *replaces* the JLARC extraction's single flat "5.5% YoY" figure
  (itself read off 2024-vintage PJM narrative text, not a zone dashboard)
  with a proper term structure — and confirms the near-term rate is
  consistent with JLARC's number, while showing the rate decelerating at
  longer horizons rather than compounding at a constant rate to 2040 as
  the current `growth_scenarios.yaml` draft assumes.
- DOM zone is called out by name as the **largest absolute increase in
  summer peak demand in PJM RTO for 2026–2030**, driven by data centers.
- **Important near-term caveat:** the 2026 report's *RTO-wide* near-term
  forecast is actually *lower* than 2025's — PJM cut projected 2026 summer
  peak by 2,564 MW (−1.6%) — "due to updates to the electric vehicle
  forecast, economics, and large load adjustments." PJM now requires
  "firm" commitments (Electric Service Obligation / Construction
  Commitment) for near-term forecast years and derates longer-term,
  less-certain projects as "non-firm." This is PJM tightening its own
  data-center-request vetting after concerns about speculative/duplicate
  interconnection requests inflating the queue — a real and recent
  methodological shift, not noise.
  Source: [PJM trims near-term load forecast on stricter data center
  vetting](https://www.utilitydive.com/news/pjm-interconnection-load-forecast-data-centers/809717/).

**Contracted vs. built capacity — a conflation risk worth flagging
explicitly.** Multiple sources report Dominion's *contracted* data-center
capacity at **~48.5 GW as of December 2025** (up from ~16.5 GW in July
2023) — nearly 3× in 18 months. This is a large, attention-grabbing
number, but it measures signed interconnection contracts/queue position,
not installed or even under-construction capacity. It should **not** be
substituted for the JLARC extraction's "4,140 MW current NOVA capacity"
figure — they answer different questions (pipeline vs. built). Given
PJM's own recent pushback on queue inflation (previous paragraph), the
48.5 GW figure is likely a substantial overstatement of what will
actually be energized by any given year. Source: [Dominion Energy's data
center growth continues to
accelerate](https://finance.yahoo.com/news/dominion-energy-raises-five-capex-144340092.html).

**Dominion's own capital-plan and connection pace** (corroborating,
narrower numbers): $50.1B capex 2025–2029 (up from $43.2B), 15 new data
centers connected in 2025 (~1 GW), 15 more expected in 2026. Demand
forecast: **5.5%/yr for the next decade, doubling by 2039** — matches the
JLARC-derived "base" scenario almost exactly. Source: [Dominion Energy
Q4 2025 slides: $65B capital plan targets data center
boom](https://www.investing.com/news/company-news/dominion-energy-q4-2025-slides-65b-capital-plan-targets-data-center-boom-93CH-4519537).

**Spatial-concentration complication, directly relevant to the "Loudoun
cluster" framing.** Loudoun County ended by-right data-center approvals
in March 2025 — every new project now needs a public hearing / special
exception. Combined with scarce sites (transmission adjacency, water,
zoning) in Loudoun/Prince William, new campuses are being pushed south
along I-95 to Stafford, Spotsylvania, and the Richmond metro (e.g.
Vantage's $2B VA4 campus in Stafford County, announced Nov 2025). This
means **the analysis's "Loudoun cluster" pnodes may see a *slower* share
of future DC growth than a naive DOM-zone-wide projection would imply**
— growth is diffusing south within the DOM zone, not concentrating
further at Loudoun. This is a genuine complication for any
`dc_share_of_load`-style scaling that assumes the Loudoun cluster
continues capturing its historical share. Source: [Data Center
Development in Northern Virginia, 2026 Market
Brief](https://motioncre.com/resources/data-center-development-northern-virginia).

**Legislative accountability check, new since JLARC.** A Virginia law
passed in the 2026 session (effective 2026-04-30 reporting) now mandates
independent review of **Dominion's own load-forecasting methodology**,
prompted by legislator concern that data-center-driven forecasts may be
overstated or under-scrutinized. Worth citing in the eventual sub-q2
report as evidence that forecast uncertainty here is a live policy
concern, not just an analyst's caveat. Source: [New state law mandates
review of Dominion's load forecasting, as data centers raise
concerns](https://virginiamercury.com/2026/04/30/new-state-law-mandates-review-of-dominions-load-forecasting-as-data-centers-raise-concerns/)
(full text not independently fetchable — site returned 403 to automated
fetch; citation is from the search snippet only and should be verified
by a human read before the report cites it as a settled fact).

**Granular NOVA inventory, confirmed at the aggregate level (CBRE, H2
2025 / full-year 2025, published 2026-03-18, fetched directly).** Total
NOVA data-center inventory: **4,039.6 MW, up 37% YoY**. New capacity
delivered in 2025: **>1 GW**. Under construction (H1 2025 snapshot,
possibly stale by H2): **2,078.2 MW, up 80% YoY**. Vacancy: **0.5%** —
lowest of any major US data-center market. Net absorption 2025: **1,102
MW, up 144% YoY**. Asking rates for 10+ MW requirements: **$155–185/kW**.
No county-level (Loudoun vs. Prince William vs. I-95-corridor) MW
breakdown is available in CBRE's free public content — that granularity
appears to require a paid report. Source: [Northern Virginia Extends
Lead as Largest U.S. Data Center Market in
2025](https://www.cbre.com/press-releases/northern-virginia-extends-lead-as-largest-u-s-data-center-market-in-2025).
*(One other CBRE page, titled as if it were H2-2025 "record-low 0.94%
vacancy" data, actually served stale 2023 content on direct fetch —
CBRE appears to have reused the URL. Its numbers were discarded, not
used above.)*

**The JLARC energy/water reporting recommendation became law — but as
two narrower, separate mechanisms, not the single disclosure regime
JLARC envisioned.** This resolves the "verify by human read" flag from
the paragraph above with much more precise information:

- **Water: HB 496 (2026 session)** requires water utilities serving
  data centers to report, monthly, potable + reclaimed water volumes
  supplied to any data center holding a DEQ air permit. **Effective
  January 1, 2027** — not immediate.
- **Energy: no standalone JLARC-style public-disclosure bill passed.**
  Instead, Virginia's **FY2026 budget** (signed by Gov. Spanberger,
  2026-06-30) imposes a **data-center electricity consumption tax of
  $0.011/kWh, effective 2026-07-01 through 2026-06-30 2028** (a two-year
  sunset), covering both utility-supplied and qualifying self-generated
  electricity, with monthly reporting/remittance to the **SCC** (first
  returns due September 2026). This forces the same underlying
  kWh-consumption data to a regulator on a recurring basis, but as a
  tax-collection mechanism, not JLARC's public-transparency ask.
- A broader **data-center clean-energy-requirement package failed to
  pass** in the 2026 session after months of debate — the accountability
  measures that did pass (water reporting + consumption tax) are a
  narrower subset of what JLARC recommended, not the full package.

Sources: [Virginia Legislature Approves Tax on Data Center Electricity
Consumption |
Greenberg Traurig](https://www.gtlaw.com/en/insights/2026/6/virginia-legislature-approves-tax-on-data-center-electricity-consumption);
[Virginia has a new two-year budget... | Virginia
Mercury](https://virginiamercury.com/2026/06/30/virginia-has-a-new-two-year-budget-heres-what-lawmakers-now-require-of-data-centers/);
[After months of debate, Virginia fails to pass data center clean
energy requirements |
Route Fifty](https://www.route-fifty.com/artificial-intelligence/2026/07/after-months-debate-virginia-fails-pass-data-center-clean-energy-requirements/414848/).

## 2. DC efficiency innovations — treat as ambiguous, not a moderating factor by default

**The naive framing ("more efficient chips → lower power projections") is
not well supported.** The dominant framework analysts are using in 2026
is the **Jevons paradox / rebound effect**: efficiency gains lower the
effective cost per unit of AI compute, which stimulates *more* compute
deployment, not less aggregate power draw. One industry commentator (Wei
Wang, ByteDance) is quoted describing a rebound effect "potentially
exceeding 100%" — i.e., efficiency improvements net *increase* resource
consumption. McKinsey's estimate of 130–240 GW of additional data-center
capacity needed globally by 2030 is framed explicitly as "a power-grid
problem before it is a chip problem." Source: [The Jevons Paradox: Why
Efficiency Alone Won't Solve Our Data Center Carbon
Challenge](https://www.sigarch.org/the-jevons-paradox-why-efficiency-alone-wont-solve-our-data-center-carbon-challenge/);
academic treatment at
[arxiv.org/html/2501.16548v1](https://arxiv.org/html/2501.16548v1).

**Concretely, per-rack power draw is rising, not falling, even as
performance-per-watt improves.** Nvidia's Rubin platform (announced
CES/GTC 2026) delivers ~10× inference throughput per watt over Blackwell
at the chip level, but a full VR200 NVL72 rack draws **190–230 kW**,
up from 120–130 kW for Blackwell and ~40 kW for Hopper just two
generations earlier. Efficiency-per-operation is improving faster than
total facility power draw is falling — consistent with the rebound-effect
framing above. Source: [Nvidia Unleashes Rubin on the AI Data Center
Market](https://www.datacenterknowledge.com/data-center-chips/ces-2026-nvidia-launches-rubin-to-maintain-data-center-stronghold).

**Liquid cooling is an enabler of the rebound pattern, not a moderator of
it.** Adoption is accelerating — liquid-based cooling held **46% of the
data center cooling market by revenue in 2024** (up from ~10% in 2020),
and the AI-datacenter liquid-cooling market specifically is projected at
**$3.70B in 2026, up from $3.20B in 2025**. But fleet-wide PUE (power
usage effectiveness) has barely moved: Uptime Institute's 2025 Global
Data Center Survey puts the **global average PUE at 1.54**, essentially
flat since 2020 (1.55–1.59 band held for six straight years).
Liquid-cooled facilities do run much better individually (PUE 1.02–1.2
vs. 1.4–1.8 air-cooled) — but liquid cooling scopes to the **cooling
subsystem**, not total facility draw (confirmed directly against
Lawrence Berkeley National Lab's own liquid-cooling page, which frames
the benefit exactly this way). The more load-bearing read: liquid
cooling isn't optional at current rack densities (**~27 kW/rack in 2026
production, next-gen Rubin-class racks reportedly projected toward
370 kW** per a Deloitte figure cited via a secondary aggregator, not yet
independently verified) — air cooling physically cannot dissipate that.
So liquid cooling is best understood as **what lets density keep
climbing**, not a technology that caps total power draw. It's a
permissive input to the same Jevons pattern already established above,
not a counterweight to it. Sources: [Tom's Hardware — The data center
cooling state of play
2025](https://www.tomshardware.com/pc-components/cooling/the-data-center-cooling-state-of-play-2025-liquid-cooling-is-on-the-rise-thermal-density-demands-skyrocket-in-ai-data-centers-and-tsmc-leads-with-direct-to-silicon-solutions);
[Uptime Institute 2025 Global Data Center Survey
(PDF)](https://datacenter.uptimeinstitute.com/rs/711-RIA-145/images/2025.Annual.Survey.Report.pdf);
[LBNL — Liquid Cooling](https://datacenters.lbl.gov/liquid-cooling).

**The efficiency-adjacent trend that's actually relevant to sub-q1/q2's
Z–LMP mechanism is demand flexibility, not chip efficiency.** This is a
genuinely new and structurally important 2025–2026 development:

- A 2026 Duke University Nicholas Institute study found a **1–2%
  reduction in data-center peak demand could cut PJM electricity rates
  0.5–2.8%** while protecting reliability — i.e., even small curtailment
  commitments have outsized grid-stability value given how tight PJM's
  capacity margin has become.
- **PJM received DOE emergency approval (2026-05-18) to curtail data
  centers and other large loads during hot-weather emergencies.**
  PJM's January 2026 board-approved framework establishes that data
  centers *without* co-located generation ("Non-Capacity-Backed-Load")
  are curtailed *ahead of* residential/commercial customers during
  emergencies, in exchange for faster grid-connection approval.
- Skeptical counter-framing exists too: PJM's own Independent Market
  Monitor has called data-center flexibility a **"regulatory fiction"**
  and urged FERC to block new large loads unless matched with firm
  generation — flexibility commitments may be weaker in practice than on
  paper, especially since **inference workloads (the dominant AI workload
  today) can't be meaningfully curtailed**, unlike training workloads.

Source: [PJM's emergency data center curtailments signal a new power
calculus for AI
infrastructure](https://startupfortune.com/pjms-emergency-data-center-curtailments-signal-a-new-power-calculus-for-ai-infrastructure/);
[A reality check on flexible data
centers](https://www.latitudemedia.com/news/a-reality-check-on-flexible-data-centers/).

**Why this matters for sub-q1/sub-q2 framing specifically, not just
sub-q2's narrative:** curtailment events are themselves large, sudden,
*negative* load-gradient events — exactly the kind of signal Z is built
to detect. If PJM's curtailment framework matures and gets used more
often (which the 2026-05-18 DOE emergency order suggests is now
institutionally live, not hypothetical), **future high-|Z| events may
increasingly be curtailment-driven rather than demand-ramp-driven** —
a mechanism shift that didn't exist in the historical window (2022–2026)
this project's panel covers. Worth a flag for whoever reviews sub-q2's
design once plan-writing unlocks; it's not actionable in the existing
data (curtailment orders only started in 2026) but should shape how any
2030/2040 projection frames its stationarity assumption.

**On-site/behind-the-meter generation — a load-shape wildcard, not a
demand reducer.** Dominion has a **70 GW interconnection-queue backlog**
in Virginia, pushing data-center developers toward self-supply: on-site
gas turbines, SMRs (e.g. the proposed Surry Green Energy Center),
fuel cells. As of **today (2026-07-20)**, Virginia Mercury reports data
centers are specifically pursuing **owned gas turbines that would not be
grid-interconnected — and therefore fall outside the Virginia Clean
Economy Act's renewable mandates**, since VCEA only binds utility-scale
generation serving grid load. This doesn't reduce a data center's total
power draw; it changes *how much of that draw shows up as DOM-zone grid
load* (self-supplied MW never appears in the panel this project analyzes
at all) — a real, if second-order, complication for translating "DC
capacity growth" into "DOM-zone load growth" one-for-one. Source:
[Data centers want to build their own gas turbines. Would that skirt
state renewable energy
laws?](https://virginiamercury.com/2026/07/20/data-centers-want-to-build-their-own-gas-turbines-would-that-skirt-state-renewable-energy-laws/)
(same 403-to-automated-fetch caveat as above — snippet-sourced, verify
before citing as settled).

**Water is a real, escalating, now-legislated constraint in exactly the
project's geography — and it's already killed a major project.** This
is arguably the single most important new finding from this deeper
research pass, and it wasn't on the radar at all in the first pass:

- **Virginia is in severe drought as of this writing.** As of June 2026,
  ~1/3 of the state was in extreme drought (driest since 2002), with 10
  of 11 drought-monitoring zones under a warning since May 2026. Data
  centers get **no special exemption** — they're bound by the same
  DEQ drought restrictions as every other customer class.
- **Loudoun-specific numbers, directly in the project's geography:**
  Loudoun County data centers used **~899 million gallons of potable
  water in 2023 — a ~250% increase** over earlier years. Loudoun +
  Fairfax together now host **>200 data centers**.
- **ICPRB (Interstate Commission on the Potomac River Basin)** —
  covering exactly the Loudoun/Prince William geography this project's
  pnodes sit in — puts current DC water withdrawal at **<0.1 MGD
  upstream, ~4 MGD across the DC metro area, peaking ~15 MGD regionally
  in summer**. Data centers are only ~1% of total water withdrawal but
  **9% of consumptive use annually (up to 12% in summer)** — a small
  share of raw withdrawal but a disproportionate share of water that
  never returns to the river, concentrated exactly when flows are
  lowest. **By 2050, ICPRB projects ~22 MGD average / >80 MGD peak**
  regional demand. ICPRB's own framing: data center growth "could lead
  to regional water supply reliability challenges especially during
  low-flow periods."
- **The Prince William Digital Gateway — a 23M-sq-ft, 2,100-acre
  campus that would have been the world's largest data center
  complex, sited next to Manassas National Battlefield — was killed by
  the Virginia Court of Appeals in March 2026** after a 2+ year legal
  fight. Water was one of the explicitly cited concerns: the project's
  scale "threatened to pollute drinking water in the Occoquan
  watershed, which serves 800,000 people in Northern Virginia." This is
  concrete, direct evidence that DC growth in this exact region is not
  a smooth exogenous trend — it faces real, sometimes fatal, legal and
  environmental friction.
- **Broader opposition context:** at least **25 planned Virginia data
  centers were canceled in 2025** (~4x the 2024 rate), and a 2026 poll
  found only **35% of Virginia voters comfortable with new data centers
  in their community**.
- **The new HB 496 water-reporting law** (effective 2027, detailed in
  §1 above) is the state's institutional response to this pressure —
  visibility first, before any harder constraint.

Sources: [WHRO — Amid statewide drought conditions, data centers face
same restrictions as all water
customers](https://www.whro.org/environment/2026-06-22/amid-statewide-drought-conditions-data-centers-face-same-restrictions-as-all-water-customers)
(Virginia Mercury original 403'd — mirror used instead); [ICPRB — Data
Centers and Water Use in the Potomac River
Basin](https://www.potomacriver.org/focus-areas/water-resources-and-drinking-water/water-resources/planning/data-centers-and-water-use-in-the-potomac-river-basin/);
[The Cool Down — Community fights
back](https://www.thecooldown.com/green-home/data-center-project-prince-william-county/);
[Virginia Business — PW Digital Gateway officially
dies](https://virginiabusiness.com/prince-william-digital-gateway-data-center-project-officially-dies/);
[Virginia Independent — Data center cancellations pile
up](https://virginiaindependentnews.com/infrastructure/data-center-cancellations-pile-up-as-virginians-voice-opposition/).

**The Nvidia distributed/residential mini-DC trend (already flagged in
CLAUDE.md) is now a real, named program, but not yet Virginia-relevant.**
Nvidia partnered with startup **Span** and homebuilder **PulteGroup** to
launch **"XFRA"** in April 2026: compact 16-GPU (Blackwell) units
installed at new-construction homes, drawing grid power through the
homeowner's existing electrical service, with homeowners compensated for
hosting. Span's pitch: 8,000 XFRA units ≈ same compute as one
traditional 100 MW centralized data center, deployed ~6× faster at ~1/5
the cost. **Initial rollout targets the southwestern US, not Virginia** —
so this doesn't yet threaten the DOM-zone spatial-concentration
assumption directly, but it's the concrete instantiation of the trend
CLAUDE.md flagged as "materially changes the spatial concentration
assumption" if it spreads east. Worth a watch-item, not yet a modeling
input. Source: [Nvidia partners with homebuilders to put AI data centers
in residential
backyards](https://cryptobriefing.com/nvidia-residential-ai-data-centers/).
**Re-checked 2026-07-21, no change to the Virginia-relevance read:**
the pilot's scope is more concrete now — a Q3 2026 proof-of-concept
deploying ~100 nodes, explicitly located in **Nevada or Arizona**, with
>1 GW annual XFRA capacity targeted starting 2027 (still no stated
timeline for eastward/Virginia expansion). Source: [SPAN — Span
Announces XFRA](https://www.span.io/blog/span-announces-xfra-a-distributed-data-center-solution-to-close-the-speed-to-power-gap-for-ai-compute-demand).

**Custom AI silicon (Google TPU, Amazon Trainium, Microsoft Maia) shows
the identical rebound pattern as Nvidia GPUs — it is not a countervailing
force.** Google's **TPU v7 "Ironwood"** (GA late 2025) claims ~2× the
perf/watt of its predecessor and ~30× vs. Google's first 2018 TPU, with
Google claiming ~44% lower TCO than an Nvidia GB200 server. Amazon's
**Trainium3** (launched December 2025, first 3nm AWS chip) offers 2.52
PFLOPS FP8. Microsoft's **Maia 200** (announced January 26, 2026) claims
>10 PFLOPS FP4 within a 750W SoC envelope and "30% cheaper than any
other AI silicon on the market" (a vendor claim, not independently
benchmarked). These efficiency/cost gains are real at the
individual-customer level — Midjourney's reported migration from Nvidia
GPUs to Google TPUs cut its monthly compute bill from $2.1M to $700K
(a 65% reduction). **But the aggregate trajectory shows the same
rebound pattern already established for Nvidia:** custom ASICs are
growing at a reported **44.6% CAGR in 2026**, and global hyperscale
AI-dedicated data-center capacity is projected to grow from **~11.5 GW
in 2026 to ~43.6 GW by 2031** — a ~30.5% CAGR. The cost-per-compute
reductions custom silicon delivers appear to be getting reinvested into
deploying far more aggregate compute, not into flattening total power
draw — structurally identical to the Blackwell→Rubin pattern (10× better
inference-per-watt, but rack power still rising 120kW→230kW) documented
above. Sources: [Google Cloud — Ironwood: the first TPU for the age of
inference](https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/ironwood-tpu-age-of-inference/);
[SemiAnalysis — TPUv7: The 900lb Gorilla In the
Room](https://newsletter.semianalysis.com/p/tpuv7-google-takes-a-swing-at-the);
[Microsoft Blog — Maia 200: The AI accelerator built for
inference](https://blogs.microsoft.com/blog/2026/01/26/maia-200-the-ai-accelerator-built-for-inference/)
(vendor's own claims — flag accordingly). The 44.6% CAGR and 11.5→43.6
GW figures are from secondary aggregator sources, not independently
cross-verified — treat as directional, not precise, if cited in a
paper-bound output.

## 3. Grid infrastructure growth — DOM-zone transmission is under active, funded buildout

**PJM's 2025 RTEP Window 1 (board-approved): $11.8B total, ~$4.8B in
Virginia.** The single largest DOM-zone project: a **525 kV HVDC
underground line, 185 miles from Brunswick County to Loudoun County's
Mosby substation**, including two ~$1.5B converter stations, delivering
**3,000 MW into Northern Virginia**. **Completion slated for June 2032**
— a useful anchor point: this specific capacity addition will not be
online for sub-q2's near-term (2030) projection horizon, only its
2035/2040 horizon. Source: [PJM approves $11.8bn transmission expansion
plan amid data center
boom](https://www.datacenterdynamics.com/en/news/pjm-approves-118bn-transmission-expansion-plan-amid-data-center-boom/).

**Projects specific to the analysis's Loudoun-cluster pnodes:**

- **Golden–Mars project (Ashburn/Dulles):** SCC approved the route in
  2026; 8–9 miles of new 185-ft monopole transmission connecting the
  Golden substation (near Rt. 28) to the Mars substation (near Dulles
  Airport). Framed by Dominion/PJM as critical to avoid damaging existing
  infrastructure and PJM-levied penalties if not completed — i.e. this
  is catch-up capacity for load that's already arrived, not speculative
  buildout. Source: [Dominion Resumes New Connections, But Loudoun Faces
  Lengthy Power
  Constraints](https://www.datacenterfrontier.com/energy/article/11436951/dominion-resumes-new-connections-but-loudoun-faces-lengthy-power-constraints).
- **Goose Creek substation (Line 514):** replacing ~3.1 miles of aging
  lattice structures (500kV + double-circuit 230kV) with monopoles,
  between Goose Creek substation and the Potomac River. SCC case
  PUR-2026-00021; Virginia Supreme Court affirmed the SCC approval
  2026-02-19, clearing the project to proceed. A separate, earlier
  near-term item: a new 500kV–230kV transformer addition at Goose Creek
  itself (distinct from the Line 514 reconductoring). Source: [Line
  514 | Dominion
  Energy](https://www.dominionenergy.com/about/delivering-energy/electric-projects/power-line-projects/line-514).
- Dominion also filed (May 2026, SCC case PUR-2026-00062) for two
  additional 230kV lines connecting a new **Firehouse substation** to the
  existing **BECO substation** — another Loudoun-area addition not
  previously on the project's radar.

**Valley Link and MARL — two much larger, multi-state 765kV/500kV
lines, both explicitly justified by Loudoun/NoVA data-center load, both
arriving earlier than the 3,000 MW HVDC line above.** This is a
significant correction to the first research pass's synthesis, which
treated the 2032 HVDC line as the earliest major relief — it isn't.

- **MARL (Mid-Atlantic Resiliency Link) — 500kV.** Primary developer
  NextEra Energy Transmission (FirstEnergy's role in a southern segment
  is referenced by opposition sources but not independently confirmed).
  Originally routed straight across western Loudoun County; PJM Board
  approved an **"Alternate MARL Re-Route" in August 2024** sending it
  through Frederick/Montgomery counties, MD, then cutting south into
  Ashburn — explicitly to serve Loudoun data-center load while
  addressing the county's routing objections. Selected by PJM December
  2023, rerouted approval August 2024. **Target in-service: end of
  2031.** State certifications (Virginia SCC, Maryland PSC) still
  pending as of this research.
- **Valley Link — 765kV, larger still.** Joint venture of **Dominion
  Energy, AEP/Transource, and FirstEnergy Transmission**, selected by
  PJM's Board of Managers **February 2025**. Two segments: an
  interstate leg (~260 miles, Putnam County WV → Frederick County MD,
  touching Clarke/Frederick/Loudoun counties VA) and a Virginia
  intrastate leg (Campbell County → Fauquier County, plus a new Caroline
  County substation — mileage is genuinely inconsistent across sources,
  115 mi per opposition/VPM reporting vs. ~155 mi per Dominion's own
  press release; likely the same segment measured differently, unresolved
  pending the not-yet-filed SCC application). Capacity cited elsewhere
  at up to **6,600 MW** combined. SCC route-approval filing planned for
  summer 2026 (not yet filed at time of research). **Target energization:
  end of 2029** — three years ahead of the HVDC line.
- **Opposition to both** centers on eminent domain (towers 180–200 ft,
  ~365 acres taken in Loudoun alone for MARL), routing through the
  Monongahela National Forest and near the Appalachian Trail, and a
  specific ask that data centers — not ratepayers — bear the
  underground-vs-overhead cost premium (cited at ~$4.8B underground vs.
  ~$2.6B overhead for one comparison). Tracked jointly at
  [stopmarlvirginia.com](https://stopmarlvirginia.com/), which itself is
  useful primary evidence of the friction discussed in "local pushback"
  below. Louisa County officials have also formally pushed back on the
  Valley Link routing.

Sources: [Dominion Energy Newsroom — PJM selects regional transmission
projects...](https://news.dominionenergy.com/press-releases/press-releases/2025/PJM-selects-regional-transmission-projects-to-be-jointly-developed-by-Dominion-Energy-American-Electric-Power-FirstEnergy/default.aspx);
[Transource — Valley Link
Transmission](https://www.transourceenergy.com/projects/ValleyLink/);
[Waterford Foundation — About the Mid-Atlantic Resiliency
Link](https://www.waterfordfoundation.org/about-marl/); [VPM — Early
Valley Link outreach finds growing opposition in Central
Virginia](https://www.vpm.org/news/2026-03-27/joshua-falls-yeat-valley-link-electric-transmission-pjm-energy-grid);
[Stop MARL Virginia / Stop Valley Link](https://stopmarlvirginia.com/faqs).

**PJM capacity market prices — direct economic evidence of the grid
stress data centers are driving, corroborating the transmission-buildout
narrative above.** Four consecutive Base Residual Auctions ($/MW-day,
UCAP), cross-verified against PJM's own auction report PDFs:

| Delivery Year | RTO-wide price | DOM zone (LDA) price | Note |
|---|---|---|---|
| 2024/2025 | $28.92 | *(not separately constrained)* | |
| 2025/2026 | $269.92 | **$444.26** | DOM constrained as its own LDA for the first time; BGE also spiked to $466.35 |
| 2026/2027 | $329.17 | $329.17 | FERC-approved price cap now binding; DOM no longer separately constrained |
| 2027/2028 | $333.44 | $333.44 | Cap still binding; **first auction where the entire RTO fell short of its reliability requirement** (short by 6,623 MW) |

The RTO-wide "factor of 10" figure checks out for 2024/25→2025/26
specifically (~9.3×); DOM's own price move that same year was closer to
**15×**, before converging back to the RTO-wide (capped) price in
2026/27–2027/28. **Caution:** a widely-repeated $542.83/MW-day figure
for DOM 2027/2028 is a *simulated, uncapped counterfactual* (what DOM
would have cleared absent the FERC cap) — the actual cleared price that
year was $333.44, same as RTO-wide. Don't cite $542.83 as an actual
cleared price. Drivers per PJM/IEEFA (IEEFA article 403'd — snippet only,
verify before citing): data centers were responsible for **63% of the
2025/26 price increase, ≈$9.3B of added cost**; other factors include
generator retirements and Reliability-Must-Run units. Sources: [PJM
Auction Procures 134,479 MW of Generation
Resources](https://insidelines.pjm.com/pjm-auction-procures-134479-mw-of-generation-resources/);
[RTO Insider — PJM Capacity Auction Clears at Max
Price](https://www.rtoinsider.com/121911-pjm-capacity-auction-clears-max-price-falls-short-reliability-requirement/);
[Projected data center growth spurs PJM capacity prices by factor of 10
| IEEFA](https://ieefa.org/resources/projected-data-center-growth-spurs-pjm-capacity-prices-factor-10).

**Regulatory/tariff-side change, not a physical build, but structurally
important for how future DC load connects to the grid.** FERC ordered
PJM (2025-12-18) to reform its tariff for **co-located
generation-and-load** (data centers physically paired with a power
plant, partially bypassing the grid). PJM's compliance filing
(2026-02-23) creates three new transmission service tiers for this
arrangement. This is the regulatory scaffolding for the
"behind-the-meter" trend in §2 above — it's becoming an officially
sanctioned interconnection pathway, not just an ad hoc workaround. Source:
[FERC Orders PJM to Reform Tariff for Co-Located Generation and
Load](https://www.klgates.com/FERC-Orders-PJM-to-Reform-Tariff-for-Co-Located-Generation-and-Load-1-15-2026).

**Generation-side additions in the DOM zone — the buildout isn't only
transmission.** Everything above is wires; here's what's adding supply:

- **Coastal Virginia Offshore Wind (CVOW):** 2.6 GW nameplate (176
  turbines), **began delivering power March 23, 2026**. Full completion
  now expected **early 2027** (slipped from end-2026 after a
  Trump-administration stop-work order in December 2025 that federal
  judges later allowed to lift). **Important constraint: Dominion states
  CVOW can currently deliver only ~50% of its output to the grid without
  transmission upgrades from PJM** — a direct echo of the same
  transmission-bottleneck theme already established for the HVDC line
  and Valley Link/MARL above. Even "complete," CVOW's DOM-zone
  contribution may stay bottlenecked for some time.
- **Cumberland Energy Center** (Cumberland County): **3 GW combined-cycle
  gas**, announced May 2026, built to be hydrogen-capable in future.
  Construction starts 2029, **in operation 2033–2034** — outside even
  the 2032 HVDC horizon.
- **Chesterfield Energy Reliability Center (CERC):** **944 MW gas
  peaker**, sited at the former coal-fired Chesterfield Power Station.
  SCC-approved November 2025; construction starts 2026, completion 2029.
- **North Anna SMR (Louisa County):** Dominion is in **Phase I
  feasibility** (RFP process, ~$17.2M cost recovery Sept 2025–Aug 2026)
  for a grid-serving (not behind-the-meter) small modular reactor.
  Virginia's IRP targets **first SMR online mid-2030s**. Amazon has an
  MOU to help finance/support development — a financing partnership,
  distinct from the on-site/behind-the-meter deals discussed in §2. (A
  specific "5 GW Amazon partnership" figure appears only in a
  secondary-aggregator source and is unverified — don't cite as
  settled.) Separately, Dominion secured a 20-year life-extension for
  the *existing* North Anna units (not new capacity). The older,
  large-format **North Anna Unit 3** (ESBWR design, NRC permit granted
  2017) remains on hold and inactive — not a live pipeline item.
- **Scale context:** Dominion reports **70,000 MW of cumulative
  data-center power requests** in Virginia — roughly triple Dominion's
  current peak load — as the underlying driver of all of the above plus
  the capacity-price spike documented earlier.

Sources: [Utility Dive — Coastal Virginia Offshore Wind begins
delivering
power](https://www.utilitydive.com/news/coastal-virginia-offshore-wind-begins-delivering-power/815874/);
[Virginia Mercury — Dominion announces plans for new 3-gigawatt gas
plant in Cumberland
County](https://virginiamercury.com/2026/05/07/dominion-announces-plans-for-new-3-gigawatt-gas-plant-in-cumberland-county/);
[Virginia Mercury — SCC approves Chesterfield gas plant and Dominion
rate
hike](https://virginiamercury.com/2025/11/25/scc-approves-chesterfield-gas-plant-and-dominion-rate-hike-creates-new-rate-class-for-data-centers/);
[Utility Dive — Dominion Energy requests input on feasibility of
building SMR at North Anna nuclear
site](https://www.utilitydive.com/news/dominion-energy-smr-small-modular-reactor-north-anna-nuclear-site/721240/);
[Virginia Business — Dominion prepares for 70,000 MW in data center
demand](https://virginiabusiness.com/dominion-data-center-power-demand-virginia-scc/).

**Local pushback is a real friction on pace, not just NIMBY noise.** NoVa
legislators are now pushing the SCC to consider requiring buried
transmission lines after a family's legal challenge over 185-ft lines
through their backyard failed (2026). Undergrounding is far more
expensive and slower to permit than overhead — if it gains traction, it
would be a genuine drag on the pace of the transmission buildout the
JLARC/PJM projections assume. Source: [After bills passed, NoVa
lawmakers urge SCC to consider burying transmission
lines](https://virginiamercury.com/2026/03/24/after-bills-passed-nova-lawmakers-urge-scc-to-consider-burying-transmission-lines/).

## 4. Data center grid reliability / voltage ride-through — a new track, not one of the original three, but the single most directly relevant finding in this document

> **Flag before reading further:** the flagship event below (2024-07-10)
> falls **inside this project's own panel window (2022–2026)** and is
> geographically located in the Loudoun cluster (Beaumeade substation).
> This is not just sub-q2 narrative context — it may be a directly
> checkable event in the existing hourly/5-min data. Worth raising at
> the advisor meeting regardless of sub-q2/q3 gating, since it bears on
> sub-q1's own mechanism story.

**The problem, per NERC's own reporting.** Large data-center loads have
been unexpectedly tripping offline (disconnecting) during brief grid
voltage disturbances — sensitive UPS/protection systems disconnect the
load entirely rather than riding through a transient sag, which then
causes a *second* problem: a sudden, massive drop in demand right after
a grid fault, itself capable of destabilizing frequency/voltage
recovery. NERC published an **Incident Review** on this (2025-01-08,
title "Considering Simultaneous Voltage-Sensitive Load Reductions") and
escalated to a **Level 3 "Essential Action" Alert on 2026-05-04** (its
highest-urgency tier), requiring registered entities to model
computational loads, run annual stability-margin studies, install
dynamic fault-recording devices, and improve situational awareness —
with compliance acknowledgment due 2026-05-11 and status reports due
2026-08-03. NERC's review also found the problem isn't AI-DC-specific:
a companion review found **26 large-load ride-through events in ERCOT
(Jan 2023–Sep 2025)**, mostly crypto-mining facilities, losing 17–95% of
pre-disturbance load within milliseconds. (Both core NERC PDFs returned
403 to automated fetch; content below is corroborated across 4+
independent secondary sources — RTO Insider, Utility Dive, Davis Wright
Tremaine, gridstatus.io — not a single primary read.)

**Two concrete incidents, both in DOM zone / this project's exact
geography:**

- **2024-07-10, "Data Center Alley," Ox-Possum 230kV line near
  Fairfax.** A lightning-strike arrestor failure during a thunderstorm
  caused a transmission fault with six successive voltage sags.
  **~1,500 MW of data-center load** — an "extreme outlier" relative to
  typical 5-minute Dominion load swings — disconnected within
  milliseconds via automated protection. **PJM-wide frequency spiked to
  60.047 Hz**, exceeding NERC's ±0.036 Hz target band. Data centers
  stayed offline for hours pending manual reconnection.
- **2026-02, Loudoun and Fairfax Counties** (directly inside the
  project's Loudoun-cluster pnode geography): a single transmission
  fault caused **~1,800 MW of data-center demand** to disconnect
  simultaneously, again within milliseconds. This is the event
  anchoring NERC's May 2026 Level 3 alert. Price-impact data for this
  specific event was not found in this research pass.

**The price-volatility connection — the mirror image of the mechanism
this project studies.** [gridstatus.io](https://blog.gridstatus.io/byte-blackouts-large-data-center-loads-new-issues-pjm/)
— the same data vendor already used for this project's 5-min two-sided
companion analysis — directly analyzed PJM market data around the
2024-07-10 event: **Beaumeade substation** (in the Loudoun cluster)
congestion was **>$200/MWh immediately before** the event. Within **5
minutes** of the load loss, **system-wide energy price collapsed from
~$134/MWh to $56.70/MWh**, and Beaumeade congestion cost declined
**~97%**. This is a **price crash from a sudden load-side drop** — the
mirror image of the "price spike from a load-side surge" mechanism the
project's Z framing has focused on. It falls inside Z's existing
definition (|load gradient|, either direction) but the *causal
direction* is inverted from the demand-growth story: here the large
load itself is the shock's origin (sudden withdrawal), and the price
response is a congestion-relief crash, not a congestion-driven spike.
No source found generalizes this into a "ride-through-driven volatility
regime" claim beyond this one documented, price-verified event.

**What PJM (and Dominion) are doing about it — behind ERCOT's pace.**
PJM's "Large Load Additions" Critical Issue Fast Path process (initiated
August 2025) is the umbrella stakeholder track. PJM's Manual 14H is
being revised to incorporate IEEE 2800-2022 ride-through requirements
(driven by FERC Order 901 and NERC PRC-029, effective 2026-10-01), on a
secondary-sourced target timeline of ~2027 — not independently verified
against PJM's own manual. Dominion's own Facility Interconnection
Requirements document defines a "Power Electronic Interface Large
Loads" (PEILL) category with an Attachment 8 apparently covering
ride-through obligations, but its specific technical thresholds
couldn't be extracted from the PDF and need a direct human read before
citing. **For comparison, ERCOT has already posted a binding rule**
(NOGRR282, 2025-11-14) extending formal ride-through obligations to
"Large Electronic Loads" — PJM has no equivalent binding rule yet.

Sources: [RTO Insider — NERC Incident Review: Data
Center](https://www.rtoinsider.com/95241-nerc-incident-review-data-center/);
[gridstatus.io — Byte Blackouts: Large Data Center Loads, New Issues in
PJM](https://blog.gridstatus.io/byte-blackouts-large-data-center-loads-new-issues-pjm/);
[Data Center Dynamics — Virginia narrowly avoided power cuts when 60
data centers dropped off the grid at
once](https://www.datacenterdynamics.com/en/news/virginia-narrowly-avoided-power-cuts-when-60-data-centers-dropped-off-the-grid-at-once/);
[Davis Wright Tremaine — NERC Level 3 Alert: Large Loads/Data
Centers](https://www.dwt.com/blogs/energy--environmental-law-blog/2026/05/nerc-level-3-alert-large-loads-data-centers);
[White & Case — NERC Tees Up Plan to Assess Grid Risks Associated with
Data
Centers](https://www.whitecase.com/insight-alert/nerc-tees-plan-assess-grid-risks-associated-data-centers);
[techtimes.com — AI Data Centers Triggered 1,800 MW Grid
Drop](https://www.techtimes.com/articles/319695/20260704/ai-data-centers-triggered-1800-mw-grid-drop-nerc-issues-highest-alert.htm).

## 4. Data center grid reliability / voltage ride-through — a new track, not one of the original three, but the single most directly relevant finding in this document

> **Flag before reading further:** the flagship event below (2024-07-10)
> falls **inside this project's own panel window (2022–2026)** and is
> geographically located in the Loudoun cluster (Beaumeade substation).
> This is not just sub-q2 narrative context — it may be a directly
> checkable event in the existing hourly/5-min data. Worth raising at
> the advisor meeting regardless of sub-q2/q3 gating, since it bears on
> sub-q1's own mechanism story.

**The problem, per NERC's own reporting.** Large data-center loads have
been unexpectedly tripping offline (disconnecting) during brief grid
voltage disturbances — sensitive UPS/protection systems disconnect the
load entirely rather than riding through a transient sag, which then
causes a *second* problem: a sudden, massive drop in demand right after
a grid fault, itself capable of destabilizing frequency/voltage
recovery. NERC published an **Incident Review** on this (2025-01-08,
title "Considering Simultaneous Voltage-Sensitive Load Reductions") and
escalated to a **Level 3 "Essential Action" Alert on 2026-05-04** (its
highest-urgency tier), requiring registered entities to model
computational loads, run annual stability-margin studies, install
dynamic fault-recording devices, and improve situational awareness —
with compliance acknowledgment due 2026-05-11 and status reports due
2026-08-03. NERC's review also found the problem isn't AI-DC-specific:
a companion review found **26 large-load ride-through events in ERCOT
(Jan 2023–Sep 2025)**, mostly crypto-mining facilities, losing 17–95% of
pre-disturbance load within milliseconds. (Both core NERC PDFs returned
403 to automated fetch; content below is corroborated across 4+
independent secondary sources — RTO Insider, Utility Dive, Davis Wright
Tremaine, gridstatus.io — not a single primary read.)

**Two concrete incidents, both in DOM zone / this project's exact
geography:**

- **2024-07-10, "Data Center Alley," Ox-Possum 230kV line near
  Fairfax.** A lightning-strike arrestor failure during a thunderstorm
  caused a transmission fault with six successive voltage sags.
  **~1,500 MW of data-center load** — an "extreme outlier" relative to
  typical 5-minute Dominion load swings — disconnected within
  milliseconds via automated protection. **PJM-wide frequency spiked to
  60.047 Hz**, exceeding NERC's ±0.036 Hz target band. Data centers
  stayed offline for hours pending manual reconnection.
- **2026-02, Loudoun and Fairfax Counties** (directly inside the
  project's Loudoun-cluster pnode geography): a single transmission
  fault caused **~1,800 MW of data-center demand** to disconnect
  simultaneously, again within milliseconds. This is the event
  anchoring NERC's May 2026 Level 3 alert. Price-impact data for this
  specific event was not found in this research pass.

**The price-volatility connection — the mirror image of the mechanism
this project studies.** [gridstatus.io](https://blog.gridstatus.io/byte-blackouts-large-data-center-loads-new-issues-pjm/)
— the same data vendor already used for this project's 5-min two-sided
companion analysis — directly analyzed PJM market data around the
2024-07-10 event: **Beaumeade substation** (in the Loudoun cluster)
congestion was **>$200/MWh immediately before** the event. Within **5
minutes** of the load loss, **system-wide energy price collapsed from
~$134/MWh to $56.70/MWh**, and Beaumeade congestion cost declined
**~97%**. This is a **price crash from a sudden load-side drop** — the
mirror image of the "price spike from a load-side surge" mechanism the
project's Z framing has focused on. It falls inside Z's existing
definition (|load gradient|, either direction) but the *causal
direction* is inverted from the demand-growth story: here the large
load itself is the shock's origin (sudden withdrawal), and the price
response is a congestion-relief crash, not a congestion-driven spike.
No source found generalizes this into a "ride-through-driven volatility
regime" claim beyond this one documented, price-verified event.

**What PJM (and Dominion) are doing about it — behind ERCOT's pace.**
PJM's "Large Load Additions" Critical Issue Fast Path process (initiated
August 2025) is the umbrella stakeholder track. PJM's Manual 14H is
being revised to incorporate IEEE 2800-2022 ride-through requirements
(driven by FERC Order 901 and NERC PRC-029, effective 2026-10-01), on a
secondary-sourced target timeline of ~2027 — not independently verified
against PJM's own manual. Dominion's own Facility Interconnection
Requirements document defines a "Power Electronic Interface Large
Loads" (PEILL) category with an Attachment 8 apparently covering
ride-through obligations, but its specific technical thresholds
couldn't be extracted from the PDF and need a direct human read before
citing. **For comparison, ERCOT has already posted a binding rule**
(NOGRR282, 2025-11-14) extending formal ride-through obligations to
"Large Electronic Loads" — PJM has no equivalent binding rule yet.

Sources: [RTO Insider — NERC Incident Review: Data
Center](https://www.rtoinsider.com/95241-nerc-incident-review-data-center/);
[gridstatus.io — Byte Blackouts: Large Data Center Loads, New Issues in
PJM](https://blog.gridstatus.io/byte-blackouts-large-data-center-loads-new-issues-pjm/);
[Data Center Dynamics — Virginia narrowly avoided power cuts when 60
data centers dropped off the grid at
once](https://www.datacenterdynamics.com/en/news/virginia-narrowly-avoided-power-cuts-when-60-data-centers-dropped-off-the-grid-at-once/);
[Davis Wright Tremaine — NERC Level 3 Alert: Large Loads/Data
Centers](https://www.dwt.com/blogs/energy--environmental-law-blog/2026/05/nerc-level-3-alert-large-loads-data-centers);
[White & Case — NERC Tees Up Plan to Assess Grid Risks Associated with
Data
Centers](https://www.whitecase.com/insight-alert/nerc-tees-plan-assess-grid-risks-associated-data-centers);
[techtimes.com — AI Data Centers Triggered 1,800 MW Grid
Drop](https://www.techtimes.com/articles/319695/20260704/ai-data-centers-triggered-1800-mw-grid-drop-nerc-issues-highest-alert.htm).

## 5. Virginia's full 2026 legislative package + PJM interconnection queue reform

**Scale: ~61 data-center bills considered, 15 sent to the governor, 46
carried to 2027.** (The "15" count is inflated by House/Senate companion
pairs counting as two bill numbers for one policy.) Source: [MultiState
— Virginia Lawmakers Pass 15 Data Center Bills as Tax Exemption Fight
Looms](https://www.multistate.us/insider/2026/3/30/virginia-lawmakers-pass-15-data-center-bills-as-tax-exemption-fight-looms).

**Passed and signed, beyond what's already documented above (HB 496
water reporting, the consumption tax):**

- **SB 94 / HB 153 (siting):** new permitting process for "high energy
  use facilities" (≥100 MW) — a site-assessment report covering
  sound/agriculture/historic/forest impacts before rezoning; effective
  **July 1, 2027**, new data centers in zoned localities must site on
  industrial land unless part of a larger shared-connection development.
- **HB 507 (generator emissions):** DEQ must deny air permits for new
  backup generators (filed **after July 1, 2026**) unless they meet
  Tier IV emissions standards. Note: the original bill's battery-storage
  mandate and siting/notification rules were **stripped by amendment** —
  the final law only sets a forward-looking emissions floor for *new*
  permits, no retrofit requirement on the existing fleet.
- **HB 323:** DOE study of data-center/building waste-heat reuse;
  working group; report due September 2026.
- **SB 553 (water, companion to HB 496):** requires facilities to submit
  annual water-consumption estimates as part of permitting.
- **SB 253 (ratepayer cost-shift):** lets the SCC shift
  distribution/generation costs onto data centers/large industrial
  users (≥25 MW) instead of residential ratepayers; extends
  low-income bill assistance.
- **HB 1191 / SB 377:** lets high-energy-use customers invest directly
  in new energy infrastructure while protecting ratepayers from cost
  increases; passed unanimously.
- **HB 284 / SB 371:** requires Dominion/Appalachian Power to establish
  **voluntary** demand-flexibility programs for ≥25 MW customers by
  2029, cost-walled from other ratepayers.
- **HB 1393 (rate class + cost-shift, weakened by amendment):**
  originally created a new "GS-5" rate class with an explicit cost-shift
  mechanism for ≥25 MW users. **Gov. Spanberger amended it in April 2026
  to remove the explicit mechanism**, substituting softer
  SCC-"shall ensure" language — critics say this weakens
  enforceability. (Virginia Mercury 403'd; snippet-sourced, verify
  before citing as settled.)

**Failed or carried to 2027:**

- **SB 339** (subsidy investigation) and **SB 336** (would direct the
  SCC to evaluate *mandating* 20%/year Tier IV retrofits of the
  *existing* generator fleet — going further than HB 507's new-permit-only
  standard) — both carried over.
- The **House's original tax-exemption conditions** (remove co-located
  generation by 2027, Tier IV backup by 2031) and the **Senate's
  alternative** (eliminate the exemption outright by Jan 2027) —
  **neither survived**; the final budget kept the exemption
  unconditional and substituted the temporary consumption tax instead,
  with a phase-out study due November 2026.

**Trajectory: incremental tightening with the sharpest edges sanded
off, not a crackdown.** Every bill that passed adds friction; none
loosens existing rules. But the pattern is consistent: the most
aggressive mechanism in each category was either watered down by
amendment (HB1393), deferred a year (SB339/SB336), or replaced by a
narrower substitute (tax-exemption fight → temporary tax only).

**PJM interconnection queue reform — two distinct processes, both
relevant, neither simply "faster."**

- **(A) Generator interconnection**, reformed in 2022 from "first-come,
  first-served" (avg. ~4-year waits, 74% of studied capacity eventually
  withdrew) to a "first-ready, first-served" cluster model requiring
  upfront site control and financial commitments. Target processing
  under the new model: **1–2 years**. But volume didn't drop —
  **Cycle 1 (opened/closed April 28, 2026) drew 811 projects, 220 GW —
  72× what PJM actually interconnected in the entire prior year.** A
  new **Expedited Interconnection Track (EIT)**, FERC-approved June
  2026, fast-tracks up to 10 generation projects/year (≥250 MW,
  committing to commercial operation within 3 years) explicitly to help
  generators serving large-load additions — $500K study deposit +
  $15K/MW readiness deposit, ~10-month target, **expires end of 2027**.
- **(B) Large-load (data center) interconnection specifically** — PJM's
  Critical Issue Fast Path process (initiated August 2025) hit a
  stakeholder impasse; the **PJM Board issued a Decisional Letter
  2026-01-16** setting the framework unilaterally: revised load
  forecasting, Bring-Your-Own-New-Generation (co-locate with dedicated
  generation, largely bypass the standard queue — FERC compliance order
  2026-04-16, refile due 2026-05-18), and a curtailable "Connect and
  Manage" / Non-Capacity-Backed-Load option (the same DOE-emergency
  curtailment mechanism already documented in §2). "Large load" =
  **≥50 MW at a single point of interconnection**. **RMI's direct
  characterization: this framework "adds scrutiny rather than speeds
  connections."** You can go faster than the standard queue, but only
  by accepting curtailment risk you didn't have before.
- **FERC issued show-cause orders to all six RTOs/ISOs on 2026-06-18**
  requiring each to demonstrate its tariff adequately handles large-load
  interconnection or propose reforms — response due **August 17, 2026**.
  **This means the PJM-specific rules above are likely to change again
  within weeks of this document's writing** — treat as a live, moving
  target, not settled policy.
- **Cost of the current bottleneck, quantified:** GridLab/Aurora Energy
  Research estimate ~$3.5B in avoidable 2026/27 consumer costs if just
  10% of queued renewable/storage projects had completed on time; PJM
  has ~130 GW of capacity-eligible projects queued from before 2024 —
  73% of the entire 2026/27 Base Residual Auction's offered capacity.

Sources: [insidenova.com — Data center bills dominated this year's
General Assembly](https://www.insidenova.com/news/business/data-center-bills-dominated-this-year-s-general-assembly-here-s-what-passed/article_cdfa9be2-61d7-4880-abf1-1511963905db.html);
[Data Center Knowledge — Virginia Sets Tier 4
Baseline](https://www.datacenterknowledge.com/build-design/virginia-deq-revises-data-center-generator-rules-as-community-pushback-builds);
[Route Fifty — Governor amends bills that shift costs onto data
centers](https://www.route-fifty.com/artificial-intelligence/2026/04/virginia-governor-amends-bills-shift-costs-data-centers-critics-say-her-tweaks-weaken-them/412929/);
[DLA Piper — Virginia General Assembly proposes to eliminate sales and
use tax exemption](https://www.dlapiper.com/en-us/insights/publications/2026/03/virginia-general-assembly-proposes-to-eliminate-sales-and-use-tax-exemption-for-data-centers);
[RMI — Unpacking the PJM CIFP
Decision](https://rmi.org/resources/unpacking-the-pjm-cifp-decision-what-pjm-states-can-do-to-ensure-affordable-reliable-electricity-during-the-data-center-boom/);
[White & Case — PJM proposes to carve out new services for co-located
data
centers](https://www.whitecase.com/insight-alert/pjm-proposes-carve-out-new-services-co-located-data-centers);
[GridLab — Interconnection Bottlenecks Cost PJM Customers $3.5
Billion](https://gridlab.org/interconnection-bottlenecks-cost-pjm-customers-3-5-billion/);
[Orrick — FERC Show Cause Orders Signal Broad Reform to Large Load
Interconnection
Policies](https://www.orrick.com/en/Insights/2026/07/FERC-Show-Cause-Orders-Signal-Broad-Reform-to-Large-Load-Interconnection-Policies);
[Ascend Analytics — Can US Interconnection Queues Survive Data
Center-Driven Load
Growth?](https://www.ascendanalytics.com/blog/large-load-interconnection-queues-data-center-grid-access).

## 6. County-level inventory and spillover to neighboring zones

**Prince William County gives usable county-sourced MW figures; Loudoun
does not.** PWC's official annual report (relayed via Prince William
Times, county PDF not directly fetched): **44 operating + 15
under-construction data centers, ~12M sq ft / 275 acres operating,
862 MW consumption (FY2024, +240 MW YoY), projected +660 MW (76%) once
under-construction facilities go live.** Loudoun's live official page
states only "130+ operating data centers, 35M+ sq ft" — no MW, no
sub-county breakdown. A Loudoun county deck (Turner Data Center Brief)
reportedly has richer figures — Dominion service commitments in Loudoun
21 GW (Jul 2024) → 40 GW (Dec 2024); Loudoun's own DC energy demand
1 GW (2018) → 5.33 GW (2025), "nearly a quarter of Dominion's total
Virginia load" — but the PDF didn't parse on fetch, so treat as
moderate-confidence, sourced via Data Center Frontier's relay, not
independently verified. **No sub-county/district-level MW breakdown
exists in free public sources for either county** — confirms the first
pass's finding that this granularity is genuinely unavailable outside a
paid commercial report.

**Growth is spilling well beyond Loudoun/Prince William — this
materially sharpens synthesis point 2's open spatial question.** Three
concrete, independently-sourced directions:

- **AEP-zone (Appalachian Power, southwest/western VA — a *different*
  PJM zone than DOM):** Google/Botetourt County ($3B+, MW under NDA);
  TAC Data Centers/Wythe County (**>1 GW**, 1,000 acres); explicitly
  framed by local press as developers "seeking cheaper land and lower
  taxes" beyond NoVA. Southwest VA localities have set the state's
  lowest data-center property tax rate to compete for this.
- **West Virginia (Eastern Panhandle, electrically adjacent to
  Loudoun):** Penzance's Bedington Campus, Berkeley County — $4B,
  **up to 600 MW**; QTS campus, Jefferson/Berkeley counties (300 acres,
  no MW found).
- **Frederick County, Maryland — the strongest spillover finding, with
  an explicit causal link back to Loudoun.** Quantum Frederick campus:
  2,100 acres, $5B, **target 2,400 MW at completion** — "more than the
  2024 average electricity demand of Montgomery and Prince George's
  counties combined." Aligned Data Centers, Rowan Digital
  Infrastructure, and AWS have broken ground there. **Data Center
  Frontier's direct framing: "Power delays in Eastern Loudoun may cause
  future data center development to shift to nearby sub-markets...
  Quantum Loophole [is] perhaps the biggest beneficiary of the Loudoun
  power delays, having signed contracts with four tenants representing
  240 megawatts of capacity."** Two independent Maryland outlets
  (Maryland Matters, Baltimore Sun — both 403'd, headline-only)
  independently describe Frederick County as "the new data center
  alley," explicitly invoking Loudoun's own nickname.
- **Maryland is not a frictionless release valve either — the same
  water/opposition pattern as Virginia is repeating there.** Frederick
  County's Critical Digital Infrastructure Overlay (Jan 2026) restricts
  new DCs to ~2,600 acres; the County Executive paused new DC
  applications through Dec 31, 2026. **Washington County, MD approved a
  full yearlong moratorium on new DC applications (~July 2026),
  explicitly over water/drought concerns** — the same water-stress theme
  already documented for Virginia in §2, now confirmed as a
  regional pattern, not a Virginia-specific one.
- JLL's 2026 Global Data Center Outlook (relayed secondhand): average
  wait for a 100MW connection in NoVA is **7 years**; this is pushing
  development "20 to 40 miles outside the traditional cluster... into
  western Loudoun County, the Shenandoah Valley corridor, and markets
  in neighboring West Virginia and Pennsylvania."

Sources: [Prince William Times — Report: Prince William County has 44
data centers, 15 more on the
way](https://www.princewilliamtimes.com/news/report-prince-william-county-has-44-data-centers-15-more-on-the-way/article_f0518174-bd23-49ee-ab92-3b04a0936f16.html);
[Data Center Frontier — The future of property values and power in
Virginia's Loudoun
County](https://www.datacenterfrontier.com/site-selection/article/55266317/the-future-of-property-values-and-power-in-virginias-loudoun-county-and-data-center-alley);
[Cardinal News — Gigawatt data center project planned for Wythe
County](https://cardinalnews.org/2026/06/04/gigawatt-data-center-project-planned-for-wythe-county/);
[West Virginia Division of Economic Development — $4 billion data
center campus planned for Berkeley
County](https://westvirginia.gov/4-billion-data-center-campus-planned-for-berkeley-county-positioning-west-virginia-for-the-ai-and-cloud-economy/);
[Data Center Frontier — Circling back: what now for Quantum Loophole
and the Quantum Frederick data center
campus](https://www.datacenterfrontier.com/hyperscale/article/55261511/circling-back-what-now-for-quantum-loophole-and-the-quantum-frederick-data-center-campus);
[Maryland Daily Record — Washington County approves yearlong data
center
moratorium](https://thedailyrecord.com/2026/07/01/washington-county-approves-yearlong-data-center-moratorium/).

## Synthesis — what this changes for sub-q2's eventual design

1. **The JLARC-derived `growth_scenarios.yaml` draft numbers need a
   refresh pass before any implementation, not just a sanity check.**
   The PJM 2025/2026 DOM-zone-specific figures (5.4%/4.9%/4.1% term
   structure) are a better primary source than JLARC's statewide Figure
   3-3 chart-reading, and are now sitting in this document. The 48.5 GW
   "contracted capacity" headline number should **not** enter the config
   at all — it's a queue metric, not a capacity or load metric.
2. **The Loudoun-cluster spatial assumption needs an explicit caveat, not
   silent correction.** Growth is diffusing south along I-95 (Stafford,
   Spotsylvania) partly *because* Loudoun tightened its approval process.
   Whether this means the Loudoun cluster's pnodes see slower relative
   growth than DOM-zone-wide, or roughly tracks it because the underlying
   transmission (Golden-Mars, Goose Creek, the 3,000 MW HVDC line) is
   still being built specifically to serve Loudoun/Dulles, is genuinely
   unresolved from this research pass — flag as an open design question
   for the advisor meeting or sub-q2 design refresh, not something to
   silently pick a side on.
3. **Curtailment is a new, real mechanism with no historical precedent in
   the panel's window.** It complicates any claim that the historical
   Z→LMP relationship will hold unchanged as DC penetration grows — some
   future high-Z events may be curtailment artifacts (grid operator
   response) rather than pure demand-side volatility (the original
   proposal's mechanism). Worth a limitations-section sentence in
   whatever sub-q2 eventually publishes.
4. **Timing matters for the projection horizon — revised from the first
   research pass.** The first pass treated the 3,000 MW HVDC line
   (mid-2032) as the earliest major transmission relief and concluded
   near-term (2028–2032) volatility could run worse than a smooth
   interpolation would suggest. The deeper research pass found that's
   incomplete: **Valley Link (765kV, up to 6,600 MW, target end-2029)
   and MARL (500kV, target end-2031)** are both explicitly justified by
   Loudoun/NoVA load and both arrive *before* the HVDC line. The
   corrected picture is a **staggered relief schedule** — 2029, 2031,
   2032 — rather than a single 2032 cliff. Whether that staggering
   smooths the 2028–2032 window or just moves the "lumpy increment"
   problem earlier (each project is still a discrete step-change, not
   continuous capacity growth) is itself worth a design question, not
   an assumption either way. All of these dates are *targets*; PJM/SCC
   transmission timelines have a documented history of slipping (see
   CVOW's own 2026→2027 slip below), so should be treated as optimistic
   anchors, not commitments.
5. **Political and legal friction is a real, evidenced brake on growth
   — not a hypothetical risk to caveat, but an active force with a body
   count.** The Prince William Digital Gateway (23M sq ft, would have
   been the world's largest DC complex) was killed by the VA Court of
   Appeals in March 2026, partly on water-supply grounds. At least 25
   planned Virginia data centers were canceled in 2025 alone (~4× the
   2024 rate). Only 35% of Virginia voters report comfort with new data
   centers in their community. Any growth scenario that treats JLARC's
   or PJM's forecasts as a smooth, un-opposed trajectory is
   understating a documented source of downside variance. This
   reinforces (rather than duplicates) synthesis point 2's spatial
   concern — Loudoun's own by-right zoning rollback is one instance of
   this same broader friction.
6. **The capacity-price data corroborates the mechanism this project's
   sub-q1 already investigates.** DOM cleared as a separately
   constrained, higher-priced capacity zone in the 2025/2026 auction
   ($444.26 vs. $269.92 RTO-wide) before converging back once new
   transmission/generation commitments came online for later auction
   years. This is real economic evidence that transmission import
   constraints into the DOM zone bind intermittently — the same kind of
   dynamic sub-q1's LMP-volatility mechanism work is built around, just
   observed in the capacity market instead of the energy (LMP) market.
   Worth a cross-reference in whatever ties sub-q1 and sub-q2 together
   narratively.
7. **Generation, not just transmission, has its own bottlenecks.** CVOW
   — the single largest new generation resource specifically serving
   the DOM zone — can currently deliver only ~50% of its 2.6 GW
   nameplate to the grid without further PJM transmission upgrades, even
   once "complete." This is a second, independent instance of the same
   pattern as point 4: big, discrete capacity additions arriving with
   their own attached bottleneck, not smoothly.
8. **The ride-through/price-crash mechanism (§4) deserves attention
   independent of sub-q2's gating — it may already be checkable.** The
   2024-07-10 event is dated, priced, and geographically located inside
   this project's own panel window and Loudoun-cluster pnodes. Whether
   or not it changes sub-q2's design, it's worth flagging at the advisor
   meeting as a candidate for direct verification against the existing
   hourly/5-min data — a real, named, price-documented event is a much
   stronger anchor than a decile-level statistical characterization.
9. **Spillover to neighboring zones (§6) deepens, rather than resolves,
   synthesis point 2's open spatial question.** Growth isn't only
   diffusing south within the DOM zone (Stafford/Spotsylvania, already
   noted) — it's also diffusing into an entirely different PJM zone
   (AEP-Virginia: Botetourt, Wythe) and across state lines (West
   Virginia, Frederick County MD) with an explicit, sourced causal link
   back to Loudoun's own power delays. This makes the "does the Loudoun
   cluster keep its historical growth share" question harder to assume
   either way, not easier — genuinely more reason to treat it as an
   open advisor-level design question rather than a default assumption.
10. **The regulatory/interconnection landscape is a moving target, not
    settled policy — sub-q2 design work should account for this
    explicitly.** FERC's show-cause orders to all six RTOs (response due
    August 17, 2026) mean PJM's current large-load interconnection rules
    are likely to change again soon. Virginia's own 2026 legislative
    session deferred its hardest fights (SB339, SB336, the tax-exemption
    conditions) to 2027. Any sub-q2 design that treats today's rules as
    fixed inputs should say so explicitly and flag the revision risk,
    rather than silently assuming stability.

## Sources (all fetched live, 2026-07-20)

- [PJM Dials Back Near-Term Load Outlook but Maintains Steep Long-Term Growth Trajectory](https://www.powermag.com/pjm-dials-back-near-term-load-outlook-but-maintains-steep-long-term-growth-trajectory/)
- [PJM trims near-term load forecast on stricter data center vetting, economic outlook](https://www.utilitydive.com/news/pjm-interconnection-load-forecast-data-centers/809717/)
- [2026 PJM Load Forecast Report (PDF, posted 2026-01-14)](https://www.pjm.com/-/media/DotCom/library/reports-notices/load-forecast/2026-load-report.pdf)
- [Dominion Energy Q4 2025 slides: $65B capital plan targets data center boom](https://www.investing.com/news/company-news/dominion-energy-q4-2025-slides-65b-capital-plan-targets-data-center-boom-93CH-4519537)
- [Dominion Energy's data center growth continues to accelerate](https://finance.yahoo.com/news/dominion-energy-raises-five-capex-144340092.html)
- [Data Center Development in Northern Virginia, 2026 Market Brief](https://motioncre.com/resources/data-center-development-northern-virginia)
- [New state law mandates review of Dominion's load forecasting, as data centers raise concerns](https://virginiamercury.com/2026/04/30/new-state-law-mandates-review-of-dominions-load-forecasting-as-data-centers-raise-concerns/)
- [The Jevons Paradox: Why Efficiency Alone Won't Solve Our Data Center Carbon Challenge](https://www.sigarch.org/the-jevons-paradox-why-efficiency-alone-wont-solve-our-data-center-carbon-challenge/)
- [From Efficiency Gains to Rebound Effects (arXiv)](https://arxiv.org/html/2501.16548v1)
- [Nvidia Unleashes Rubin on the AI Data Center Market](https://www.datacenterknowledge.com/data-center-chips/ces-2026-nvidia-launches-rubin-to-maintain-data-center-stronghold)
- [PJM's emergency data center curtailments signal a new power calculus for AI infrastructure](https://startupfortune.com/pjms-emergency-data-center-curtailments-signal-a-new-power-calculus-for-ai-infrastructure/)
- [A reality check on flexible data centers](https://www.latitudemedia.com/news/a-reality-check-on-flexible-data-centers/)
- [Data centers want to build their own gas turbines. Would that skirt state renewable energy laws?](https://virginiamercury.com/2026/07/20/data-centers-want-to-build-their-own-gas-turbines-would-that-skirt-state-renewable-energy-laws/)
- [Nvidia partners with homebuilders to put AI data centers in residential backyards](https://cryptobriefing.com/nvidia-residential-ai-data-centers/)
- [SPAN — Span Announces XFRA, a Distributed Data Center Solution to Close the Speed-to-Power Gap for AI Compute Demand](https://www.span.io/blog/span-announces-xfra-a-distributed-data-center-solution-to-close-the-speed-to-power-gap-for-ai-compute-demand)
- [PJM approves $11.8bn transmission expansion plan amid data center boom](https://www.datacenterdynamics.com/en/news/pjm-approves-118bn-transmission-expansion-plan-amid-data-center-boom/)
- [Dominion Resumes New Connections, But Loudoun Faces Lengthy Power Constraints](https://www.datacenterfrontier.com/energy/article/11436951/dominion-resumes-new-connections-but-loudoun-faces-lengthy-power-constraints)
- [Line 514 | Dominion Energy](https://www.dominionenergy.com/about/delivering-energy/electric-projects/power-line-projects/line-514)
- [FERC Orders PJM to Reform Tariff for Co-Located Generation and Load](https://www.klgates.com/FERC-Orders-PJM-to-Reform-Tariff-for-Co-Located-Generation-and-Load-1-15-2026)
- [After bills passed, NoVa lawmakers urge SCC to consider burying transmission lines](https://virginiamercury.com/2026/03/24/after-bills-passed-nova-lawmakers-urge-scc-to-consider-burying-transmission-lines/)

**Added in the deeper research pass (2026-07-20, via three parallel
research agents):**

- [Northern Virginia Extends Lead as Largest U.S. Data Center Market in 2025 | CBRE](https://www.cbre.com/press-releases/northern-virginia-extends-lead-as-largest-u-s-data-center-market-in-2025)
- [Virginia Legislature Approves Tax on Data Center Electricity Consumption | Greenberg Traurig](https://www.gtlaw.com/en/insights/2026/6/virginia-legislature-approves-tax-on-data-center-electricity-consumption)
- [Virginia has a new two-year budget... | Virginia Mercury](https://virginiamercury.com/2026/06/30/virginia-has-a-new-two-year-budget-heres-what-lawmakers-now-require-of-data-centers/)
- [After months of debate, Virginia fails to pass data center clean energy requirements | Route Fifty](https://www.route-fifty.com/artificial-intelligence/2026/07/after-months-debate-virginia-fails-pass-data-center-clean-energy-requirements/414848/)
- [Tom's Hardware — The data center cooling state of play 2025](https://www.tomshardware.com/pc-components/cooling/the-data-center-cooling-state-of-play-2025-liquid-cooling-is-on-the-rise-thermal-density-demands-skyrocket-in-ai-data-centers-and-tsmc-leads-with-direct-to-silicon-solutions)
- [Uptime Institute 2025 Global Data Center Survey (PDF)](https://datacenter.uptimeinstitute.com/rs/711-RIA-145/images/2025.Annual.Survey.Report.pdf)
- [LBNL — Liquid Cooling](https://datacenters.lbl.gov/liquid-cooling)
- [WHRO — Amid statewide drought conditions, data centers face same restrictions as all water customers](https://www.whro.org/environment/2026-06-22/amid-statewide-drought-conditions-data-centers-face-same-restrictions-as-all-water-customers)
- [ICPRB — Data Centers and Water Use in the Potomac River Basin](https://www.potomacriver.org/focus-areas/water-resources-and-drinking-water/water-resources/planning/data-centers-and-water-use-in-the-potomac-river-basin/)
- [The Cool Down — Community fights back (PW Digital Gateway)](https://www.thecooldown.com/green-home/data-center-project-prince-william-county/)
- [Virginia Business — PW Digital Gateway officially dies](https://virginiabusiness.com/prince-william-digital-gateway-data-center-project-officially-dies/)
- [Virginia Independent — Data center cancellations pile up](https://virginiaindependentnews.com/infrastructure/data-center-cancellations-pile-up-as-virginians-voice-opposition/)
- [Google Cloud — Ironwood: the first TPU for the age of inference](https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/ironwood-tpu-age-of-inference/)
- [SemiAnalysis — TPUv7: The 900lb Gorilla In the Room](https://newsletter.semianalysis.com/p/tpuv7-google-takes-a-swing-at-the)
- [Microsoft Blog — Maia 200: The AI accelerator built for inference](https://blogs.microsoft.com/blog/2026/01/26/maia-200-the-ai-accelerator-built-for-inference/)
- [Dominion Energy Newsroom — PJM selects regional transmission projects (Valley Link)](https://news.dominionenergy.com/press-releases/press-releases/2025/PJM-selects-regional-transmission-projects-to-be-jointly-developed-by-Dominion-Energy-American-Electric-Power-FirstEnergy/default.aspx)
- [Transource — Valley Link Transmission](https://www.transourceenergy.com/projects/ValleyLink/)
- [Waterford Foundation — About the Mid-Atlantic Resiliency Link (MARL)](https://www.waterfordfoundation.org/about-marl/)
- [VPM — Early Valley Link outreach finds growing opposition in Central Virginia](https://www.vpm.org/news/2026-03-27/joshua-falls-yeat-valley-link-electric-transmission-pjm-energy-grid)
- [Stop MARL Virginia / Stop Valley Link](https://stopmarlvirginia.com/faqs)
- [PJM Auction Procures 134,479 MW of Generation Resources](https://insidelines.pjm.com/pjm-auction-procures-134479-mw-of-generation-resources/)
- [RTO Insider — PJM Capacity Auction Clears at Max Price](https://www.rtoinsider.com/121911-pjm-capacity-auction-clears-max-price-falls-short-reliability-requirement/)
- [Projected data center growth spurs PJM capacity prices by factor of 10 | IEEFA](https://ieefa.org/resources/projected-data-center-growth-spurs-pjm-capacity-prices-factor-10)
- [Utility Dive — Coastal Virginia Offshore Wind begins delivering power](https://www.utilitydive.com/news/coastal-virginia-offshore-wind-begins-delivering-power/815874/)
- [Virginia Mercury — Dominion announces plans for new 3-gigawatt gas plant in Cumberland County](https://virginiamercury.com/2026/05/07/dominion-announces-plans-for-new-3-gigawatt-gas-plant-in-cumberland-county/)
- [Virginia Mercury — SCC approves Chesterfield gas plant and Dominion rate hike](https://virginiamercury.com/2025/11/25/scc-approves-chesterfield-gas-plant-and-dominion-rate-hike-creates-new-rate-class-for-data-centers/)
- [Utility Dive — Dominion Energy requests input on feasibility of building SMR at North Anna nuclear site](https://www.utilitydive.com/news/dominion-energy-smr-small-modular-reactor-north-anna-nuclear-site/721240/)
- [Virginia Business — Dominion prepares for 70,000 MW in data center demand](https://virginiabusiness.com/dominion-data-center-power-demand-virginia-scc/)

**Added in the second deeper-research round (2026-07-21, three more
background agents — grid reliability, VA legislative package + PJM
queue reform, county inventory + spillover):**

- [RTO Insider — NERC Incident Review: Data Center](https://www.rtoinsider.com/95241-nerc-incident-review-data-center/)
- [gridstatus.io — Byte Blackouts: Large Data Center Loads, New Issues in PJM](https://blog.gridstatus.io/byte-blackouts-large-data-center-loads-new-issues-pjm/)
- [Data Center Dynamics — Virginia narrowly avoided power cuts when 60 data centers dropped off the grid at once](https://www.datacenterdynamics.com/en/news/virginia-narrowly-avoided-power-cuts-when-60-data-centers-dropped-off-the-grid-at-once/)
- [Davis Wright Tremaine — NERC Level 3 Alert: Large Loads/Data Centers](https://www.dwt.com/blogs/energy--environmental-law-blog/2026/05/nerc-level-3-alert-large-loads-data-centers)
- [White & Case — NERC Tees Up Plan to Assess Grid Risks Associated with Data Centers](https://www.whitecase.com/insight-alert/nerc-tees-plan-assess-grid-risks-associated-data-centers)
- [techtimes.com — AI Data Centers Triggered 1,800 MW Grid Drop](https://www.techtimes.com/articles/319695/20260704/ai-data-centers-triggered-1800-mw-grid-drop-nerc-issues-highest-alert.htm)
- [Utility Dive — Sudden data center load losses prompt NERC alert, recommendations](https://www.utilitydive.com/news/data-center-load-disruptions-nerc-alert-recommendations/818036/)
- [DediRock — NERC Highlights AI Data Center Grid Risks in Latest Report](https://dedirock.com/blog/nerc-highlights-ai-data-center-grid-risks-in-latest-report/)
- [insidenova.com — Data center bills dominated this year's General Assembly](https://www.insidenova.com/news/business/data-center-bills-dominated-this-year-s-general-assembly-here-s-what-passed/article_cdfa9be2-61d7-4880-abf1-1511963905db.html)
- [Data Center Knowledge — Virginia Sets Tier 4 Baseline](https://www.datacenterknowledge.com/build-design/virginia-deq-revises-data-center-generator-rules-as-community-pushback-builds)
- [Route Fifty — Governor amends bills that shift costs onto data centers](https://www.route-fifty.com/artificial-intelligence/2026/04/virginia-governor-amends-bills-shift-costs-data-centers-critics-say-her-tweaks-weaken-them/412929/)
- [DLA Piper — Virginia General Assembly proposes to eliminate sales and use tax exemption](https://www.dlapiper.com/en-us/insights/publications/2026/03/virginia-general-assembly-proposes-to-eliminate-sales-and-use-tax-exemption-for-data-centers)
- [RMI — Unpacking the PJM CIFP Decision](https://rmi.org/resources/unpacking-the-pjm-cifp-decision-what-pjm-states-can-do-to-ensure-affordable-reliable-electricity-during-the-data-center-boom/)
- [White & Case — PJM proposes to carve out new services for co-located data centers](https://www.whitecase.com/insight-alert/pjm-proposes-carve-out-new-services-co-located-data-centers)
- [GridLab — Interconnection Bottlenecks Cost PJM Customers $3.5 Billion](https://gridlab.org/interconnection-bottlenecks-cost-pjm-customers-3-5-billion/)
- [Orrick — FERC Show Cause Orders Signal Broad Reform to Large Load Interconnection Policies](https://www.orrick.com/en/Insights/2026/07/FERC-Show-Cause-Orders-Signal-Broad-Reform-to-Large-Load-Interconnection-Policies)
- [Ascend Analytics — Can US Interconnection Queues Survive Data Center-Driven Load Growth?](https://www.ascendanalytics.com/blog/large-load-interconnection-queues-data-center-grid-access)
- [Prince William Times — Report: Prince William County has 44 data centers, 15 more on the way](https://www.princewilliamtimes.com/news/report-prince-william-county-has-44-data-centers-15-more-on-the-way/article_f0518174-bd23-49ee-ab92-3b04a0936f16.html)
- [Data Center Frontier — The future of property values and power in Virginia's Loudoun County](https://www.datacenterfrontier.com/site-selection/article/55266317/the-future-of-property-values-and-power-in-virginias-loudoun-county-and-data-center-alley)
- [Cardinal News — Gigawatt data center project planned for Wythe County](https://cardinalnews.org/2026/06/04/gigawatt-data-center-project-planned-for-wythe-county/)
- [West Virginia Division of Economic Development — $4 billion data center campus planned for Berkeley County](https://westvirginia.gov/4-billion-data-center-campus-planned-for-berkeley-county-positioning-west-virginia-for-the-ai-and-cloud-economy/)
- [Data Center Frontier — Circling back: what now for Quantum Loophole and the Quantum Frederick data center campus](https://www.datacenterfrontier.com/hyperscale/article/55261511/circling-back-what-now-for-quantum-loophole-and-the-quantum-frederick-data-center-campus)
- [Maryland Daily Record — Washington County approves yearlong data center moratorium](https://thedailyrecord.com/2026/07/01/washington-county-approves-yearlong-data-center-moratorium/)

## Caveats for user review

1. Several Virginia Mercury and VPM/vpm.org articles (§1's
   load-forecasting-review law, §2's gas-turbine/VCEA piece and the
   budget article, §3's Louisa County pushback article) returned HTTP
   403 to automated fetch — their content above is from search-result
   snippets or mirror-site republication (e.g. WHRO), not a full
   original-article read. Verify directly before citing any of these as
   a settled fact in paper-bound output.
2. The PJM 2026 Load Forecast Report's DOM-zone numbers (§1) and the
   four Base Residual Auction clearing prices (§3) were both read
   directly from PJM's own primary-source PDFs/pages — high confidence.
3. This document does not resolve the Loudoun-cluster spatial-share
   question (synthesis point 2) — that requires either advisor input or
   a dedicated modeling decision once sub-q2 plan-writing unlocks.
4. **New unresolved items from the deeper pass:**
   - Valley Link's Virginia intrastate-segment mileage is inconsistent
     across sources (115 mi vs. ~155 mi) — likely the same segment
     measured differently, not two different segments, but genuinely
     unresolved pending the not-yet-filed SCC application.
   - The DOM-zone $542.83/MW-day capacity-price figure circulating in
     some coverage is a simulated/uncapped counterfactual for
     2027/2028, not the actual cleared price ($333.44) — don't conflate
     the two.
   - The liquid-cooling "10.2% total facility power reduction" figure
     mentioned in some industry-blog coverage could not be traced to a
     named primary study — treat as unverified, not cited above as a
     settled number.
   - The "5 GW Amazon partnership" framing for the North Anna SMR
     project comes from a single aggregator source, not a primary
     Dominion or Amazon release — unverified.
   - One CBRE web page (title implying H2-2025 "record-low 0.94%
     vacancy" data) actually served stale 2023 content on direct
     fetch — its numbers were not used anywhere in this document.
   - No county-level (Loudoun vs. Prince William vs. I-95-corridor)
     data-center MW breakdown was found in free public sources — that
     granularity likely requires a paid CBRE/JLL/Cushman & Wakefield
     report if it becomes necessary for the eventual sub-q2 report.
5. **New unresolved items from the second deeper-research round
   (§4–6):**
   - The two core NERC PDFs on ride-through risk (Incident Review,
     white paper) both returned 403 to automated fetch — §4's content
     is corroborated across 4+ independent secondary sources, but a
     direct human read of the primary NERC documents is warranted
     before citing specific figures (1,500 MW, 60.047 Hz, etc.) in any
     paper-bound output.
   - The gridstatus.io price-crash figures for the 2024-07-10 event
     (Beaumeade >$200/MWh → system price $134→$56.70/MWh) come from one
     source with direct PJM market-data access, not independently
     cross-verified against a second source reporting the same numbers.
   - Loudoun County's MW-level figures (21→40 GW Dominion commitments,
     5.33 GW 2025 demand) come from a county presentation deck that
     would not parse on automated fetch — relayed via Data Center
     Frontier's secondary reporting, moderate confidence only. Loudoun's
     own reported square footage is inconsistent across sources (35M
     vs. 49M vs. 53M sq ft) — not reconciled in this research pass.
   - The January 2026 PJM Board CIFP Decisional Letter's exact
     enumeration ("six principles" vs. "four-part framework") is
     inconsistent across secondary sources — the primary PDF was not
     independently parsed; read directly before citing a specific
     structure.
   - HB 1393's gubernatorial-amendment story (cost-shift mechanism
     weakened) is Route Fifty/Virginia-Mercury-snippet-sourced
     (Virginia Mercury 403'd again, consistent with every prior attempt
     to fetch that outlet directly in this document) — verify before
     citing as settled.
   - Two Maryland outlets' "Frederick County is the new data center
     alley" framing is headline-only (both 403'd) — real signal, not a
     verified detailed claim.
