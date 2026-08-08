# Flexible / Curtailable Data Center Load — State of Play, 2025-2026

Research date: 2026-08-07. Web research only.

---

## 1. Curtailable AI load pilots and products — demonstrated vs. announced

### Emerald AI (NVIDIA-backed startup)
**What has been DEMONSTRATED** (per NVIDIA case study and press coverage):
- 5 live demonstrations at commercial data center facilities: **Phoenix (Arizona), Chicago, Virginia, Portland, and London (UK)**.
- Power reduction: up to **40% power demand reduction achieved in under 60 seconds**; ~30% load shed within 30 seconds for "emergency curtailment."
- Phoenix event (May 3, [year not specified in source, likely 2025 or early 2026]): **25% energy consumption reduction sustained for 3 consecutive hours**, orchestrated with Oracle/Nvidia infrastructure ([Latitude Media](https://www.latitudemedia.com/news/nvidia-and-oracle-tapped-this-startup-to-flex-a-phoenix-data-center/)).
- London trial: **96-GPU NVIDIA Blackwell Ultra AI cluster**, sustained load-reduction support for **up to 10 hours**, over a **5-day demonstration**.
- **200+ simulated grid events** tested successfully with all requested power-reduction targets met; claims "100% alignment" with National Grid and EPRI power targets in testing.
- CEO Varun Sivaram's framing: "The power grid is like a large-scale freeway that only faces rush hour two times a month" — claims up to 100 GW of existing U.S. grid capacity could be unlocked if load is flexible.

**What is ANNOUNCED but not yet operating at scale:**
- NVIDIA's under-construction **96 MW "Aurora" AI Factory Research Center in Manassas, Virginia** — described as the first commercial-scale facility designed for DSX Flex / power-flexible operation, targeted to come online **late 2026**. This is a design-stage/construction-stage commitment, not a demonstrated large-scale flex event.
- Silicon Valley Power (Santa Clara, CA) announced a pilot partnership with Emerald AI to "demonstrate flexible data centers" and unlock power capacity — announcement stage; could not retrieve MW/duration specifics (site blocked scraping).
- At COMPUTEX 2026 / GTC Taipei, Emerald AI announced a NVIDIA DSX OS collaboration to scale "from demonstration to commercial deployment" in Silicon Valley — explicitly framed as a transition point, confirming prior work was demonstration-scale.

Sources: [NVIDIA case study](https://www.nvidia.com/en-us/case-studies/emerald-ai/), [Latitude Media — Nvidia/Oracle Phoenix](https://www.latitudemedia.com/news/nvidia-and-oracle-tapped-this-startup-to-flex-a-phoenix-data-center/), [Latitude Media — DSX Flex 100GW](https://www.latitudemedia.com/industry-news/emerald-ai-integrates-with-nvidia-dsx-flex-to-unlock-up-to-100-gw-of-grid-capacity-for-next-generation-ai-factories/), [DCD — SVP pilot](https://www.datacenterdynamics.com/en/news/emerald-ai-to-conduct-pilot-program-with-silicon-valley-power-in-santa-clara-california/), [Emerald AI newsroom](https://www.emeraldai.co/news)

### EPRI DCFlex initiative
- Launched October 2024. Expanded (announced February 2026 at DTECH) from 3 to **9 demonstration sites** across the U.S. and Europe.
- Sites/tests span: **Chicago** (compute load flexibility with AI focus, real-time power control in a simulated production environment), **Dallas, TX** (HVO renewable diesel vs. conventional diesel for backup generation — emissions/performance/runtime comparison), **Ashburn, VA ↔ Chicago, IL** (geospatial load-shifting of compute during grid congestion), plus sites in **Northern Virginia, London, and Texas** more broadly.
- Framing: flexibility is "not a single, uniform capability" — three pillars identified: (1) managed/shiftable compute workloads, (2) reduced AI-plant energy consumption (e.g., cooling/power draw throttling), (3) backup power substitution.
- **No quantified MW or event-count results were found in public sources** for the Chicago/Ashburn geospatial-shift or Chicago compute-flex demos as of this research — coverage is at the "testing methodology / site announcement" stage, not results-reporting stage.
- EPRI/NVIDIA/Emerald AI partnership: plan to bring the 96 MW Aurora AI Factory (Manassas, VA) online in late 2026 specifically to "validate workload flexibility at scale" — i.e., the flagship at-scale validation is still forward-looking, not yet demonstrated.

Sources: [PR Newswire — DCFlex nine sites](https://www.prnewswire.com/news-releases/epris-dcflex-initiative-expands-to-nine-demonstration-sites-across-us-europe-302676241.html), [Utility Dive — data centers negotiate flexibility](https://www.utilitydive.com/news/data-centers-flexibility-utilities-speed-to-power/822588/), [DCFlex demonstrations page](https://dcflex.epri.com/demonstrations), [Renewable Energy World — automation and load flexibility](https://www.renewableenergyworld.com/power-grid/how-automation-and-load-flexibility-are-helping-manage-data-center-growth/)

### Google demand-response agreements
**DEMONSTRATED (contracted / integrated) — but no evidence found of an actual dispatched curtailment event yet:**
- August 2025: first agreements with **Indiana Michigan Power (I&M)** and **Tennessee Valley Authority (TVA)** — first time Google will target machine-learning workloads specifically for demand response. I&M deal tied to the **$2B "Project Zodiac" Fort Wayne, Indiana campus**, structured as a Clean Capacity Arrangement (CCA) + custom AI-workload DR program.
- By 2026: Google announced it has now integrated **1 GW of demand response capacity** into long-term energy contracts with U.S. utilities, adding **Entergy Arkansas, Minnesota Power, and DTE Energy (Michigan)** to the roster.
- Mechanism: Google curtails/shifts ML training workloads (not necessarily inference) during utility-declared stress periods in exchange for faster grid interconnection and reduced capacity/transmission buildout obligations for the utility.
- **No public reporting found of an actual invoked/dispatched DR event** (i.e., a utility calling on Google to curtail and Google complying) — all sourcing describes contractual capacity commitments, not operational track record.

Sources: [Google blog — 1 GW milestone](https://blog.google/innovation-and-ai/infrastructure-and-cloud/global-network/demand-response-data-center-milestone/), [Google blog — making DCs flexible](https://blog.google/innovation-and-ai/infrastructure-and-cloud/global-network/how-were-making-data-centers-more-flexible-to-benefit-power-grids/), [RTO Insider — Google/I&M/TVA](https://www.rtoinsider.com/111767-google-strikes-demand-response-deals-im-tva/), [DCD](https://www.datacenterdynamics.com/en/news/google-partners-with-im-and-tva-to-expand-use-of-demand-response-at-its-ai-data-centers/), [PowerMag — I&M deal](https://www.powermag.com/google-im-strike-landmark-deal-to-share-clean-capacity-and-flex-ai-load/), [Latitude Media](https://www.latitudemedia.com/news/google-expands-demand-response-to-target-machine-learning-workloads/)

### Microsoft / OpenAI
- **Not primarily a flexibility/curtailment story** — the major 2025-2026 commitments are about **cost-shifting protection**, not load flexibility per se:
  - January 2026: Microsoft's "Community-First AI Infrastructure" initiative — commits that data centers will not raise residential ratepayer bills (full electricity cost recovery / dedicated rate classes); OpenAI made a parallel pledge.
  - March 2026: Amazon, Google, Meta, Microsoft, OpenAI, Oracle, and xAI signed a White House-facilitated **"Ratepayer Protection Pledge"** to fund grid infrastructure improvements directly.
  - OpenAI's Stargate initiative (10 GW target) references locally-tailored "community plans" but no specific curtailable-load commitment was found.
- Texas SB 6 (state law, not a Microsoft/OpenAI-specific commitment) requires any new load >75 MW to participate in demand response programs — this indirectly compels flexibility for any Microsoft/OpenAI-affiliated Texas campuses.
- **Conclusion: no evidence found of Microsoft or OpenAI operating a demonstrated MW-scale curtailment program analogous to Google's**, as of this research pass.

Sources: [TheMinerMag](https://www.theminermag.com/news/2026-01-21/openai-power-ai-data-center), [PowerMag — Microsoft cost recovery](https://www.powermag.com/microsoft-commits-to-full-electricity-cost-recovery-in-data-center-communities/)

---

## 2. PJM-specific: co-location, curtailable interconnection, who has signed up

### FERC's December 2025 show-cause order and the co-location tariff overhaul
- **December 19, 2025**: FERC ruled PJM's tariff "unjust and unreasonable" for co-located generation + load (e.g., data centers sited behind a power plant's meter) because it lacked clarity on rates/terms and lacked transmission products suited to loads willing to accept curtailment.
- FERC directed PJM to create **three new transmission service categories** for co-located load:
  1. **Interim (non-firm) Network Integration Transmission Service (Interim NITS)** — temporary service available before required network upgrades are complete; in exchange, the co-located load **agrees in advance to curtailment ahead of system emergency conditions**. Converts to full NITS once upgrades are energized.
  2. **Firm Contract Demand transmission service**
  3. **Non-Firm Contract Demand transmission service**
- **Compliance filing deadline: February 17, 2026** — PJM required to file specific terms/conditions for co-location arrangements and the interim curtailable transmission product.
- Context: this directly follows the **Talen Energy / Amazon Web Services (AWS)** dispute — AWS's ~960 MW–1.9 GW data center campus directly connected to the **Susquehanna nuclear plant** — where FERC earlier **rejected/blocked** the original interconnection service agreement for the co-located arrangement, forcing the broader tariff reform. As of this search, no confirmation was found of which specific companies (beyond Talen/AWS as the precipitating case) have formally signed up for the new Interim NITS curtailable product post-February 2026 filing — the filing itself sets the framework; enrollment data was not found in public sources at this research pass.

Sources: [K&L Gates](https://www.klgates.com/FERC-Orders-PJM-to-Reform-Tariff-for-Co-Located-Generation-and-Load-1-15-2026), [Mayer Brown](https://www.mayerbrown.com/en/insights/publications/2026/01/ferc-directs-pjm-to-facilitate-co-location-arrangements), [Baker Botts](https://www.bakerbotts.com/thought-leadership/publications/2025/december/ferc-issues-order-providing-guidance-for-co-locating-power-plants-with-data-centers-within-pjm), [Gibson Dunn](https://www.gibsondunn.com/ferc-orders-pjm-largest-u-s-grid-operator-to-revise-tariff-to-permit-new-transmission-services-for-co-located-loads-such-as-data-centers/), [PowerMag — FERC blocks Amazon/Susquehanna expansion](https://www.powermag.com/ferc-blocks-pjm-proposal-to-expand-amazon-data-center-load-at-susquehanna-nuclear-plant/)

### PJM's own emergency curtailment authority (separate track, faster-moving)
- **May 17-18, 2026**: PJM requested and received a **DOE Federal Power Act §202(c) emergency order (Order No. 202-26-23)** during a heat wave with <5,800 MW of reserve margin expected. The order authorized PJM to direct transmission owners to **curtail data centers and other large loads ≥50 MW of peak load**, forcing them onto **on-site backup generators within 15 minutes** of an emergency signal. Exempted: hospitals, 911 centers, water treatment, air traffic control, defense installations. Framed explicitly as a **last-resort measure**, ahead of voltage reduction / rolling blackouts.
- **July 27, 2026**: PJM board proposed a **backstop capacity auction** (to cover a ~6.8 GW shortfall) paired with a formal, permanent **"Interim Resource Adequacy Service" (IRAS)**: new large loads that don't bring their own generation by **June 1, 2027** and haven't otherwise secured firm supply will be **curtailed ahead of Pre-Emergency Load Management** during capacity shortages. This is PJM's structural (not just emergency-order) mechanism to make new large load inherently curtailable by default unless self-supplied.
- No public list of specific data centers enrolled in IRAS was found — the mechanism was still in board-proposal/rulemaking stage as of late July 2026, not yet an operating enrollment program.

Sources: [DOE — Order 202-26-23](https://www.energy.gov/ceser/federal-power-act-section-202c-pjm-interconnection-llc-pjm-order-no-202-26-23), [Utility Dive — DOE emergency order](https://www.utilitydive.com/news/pjm-doe-emergency-order-curtail-data-centers/820571/), [TechCrunch](https://techcrunch.com/2026/07/28/data-centers-may-face-temporary-power-cuts-to-prevent-blackouts-on-largest-us-grid/), [Utility Dive — backstop auction/curtailment plans](https://www.utilitydive.com/news/pjm-board-backstop-capacity-auction-data-center-curtailment/826347/), [Network World](https://www.networkworld.com/article/4202800/ai-data-centers-in-the-us-may-face-power-cuts-under-pjm-reliability-proposal.html)

---

## 3. ERCOT precedent: Controllable Load Resources, interim large-load process, 4CP, crypto curtailment

### Legal/regulatory framework (Texas Senate Bill 6, signed June 2025)
- Gave ERCOT authority to disconnect data centers during grid emergencies; gave PUCT mandatory review authority over any **new behind-the-meter (BTM) co-location arrangement ≥75 MW**.
- **Batch Zero** large-load interconnection process approved by PUCT **June 2026** — subjects all new large-load applicants to simultaneous batch study with MW allocations over a six-year horizon. First batch qualification deadlines **July 10-24, 2026**; financial security ~**$50,000/MW**.
- Loads interconnecting **after December 31, 2025** must accept a protocol allowing curtailment during firm load-shed events (exemptions for critical-load industrial/critical natural gas facilities).
- **Provisional Controllable Load Resource (PCLR)**: lets a large load consume above its firm allocation (up to its full request) in Batch Zero study, in exchange for accepting ERCOT real-time dispatch instructions to reduce load when transmission is constrained.
- PUCT finalized **ride-through rules for data centers** in July 2026 (behavior requirements during grid-stress events short of full emergency curtailment).
- CLR/BYOG ("Bring Your Own Generation")/WLPUN rules being codified via Batch Zero revision requests filed **April 8, 2026**; target effective date **August 1, 2026**.

### Landmark contested curtailment ruling — Docket 59220 (Goodnight campus, July 23, 2026)
- First fully-contested PUCT proceeding under SB 6. **260 MW AI campus (Crusoe/Google "Crusoe Load 2")** co-located behind the **265.5 MW Goodnight 1 wind farm** (Armstrong County, TX), alongside an already-approved 265.5 MW "Crusoe Load 1."
- PUCT sided with **ERCOT's "broad reading"** of PURA §39.169: the **entire combined 525.5 MW** of co-located AI load (not just load proportional to the wind farm's nameplate) must be curtailable within **30 minutes** whenever ERCOT declares a grid emergency — a **~2:1 curtailment-to-generator-nameplate ratio**.
- Order also **bars this arrangement from participating in paid demand-response programs** — mandatory emergency curtailment is deemed a reliability obligation, not a compensated grid service.
- Practical effect flagged by industry (GridTracker's Chris Talley): BTM wind-paired co-location now effectively **requires full off-grid backup capacity** (gas turbines/batteries) capable of carrying the entire campus load for the duration of an emergency — not just short-interruption ride-through.
- Context: campus is part of Google's $40B Texas investment (announced with Crusoe); a separate 933 MW off-grid gas-turbine segment at the same site sits outside ERCOT's curtailment authority entirely (used to preserve Google's "renewable-only" accounting for the wind-paired portion).
- **Next test case**: Docket 59399 — Amazon/Vistra co-location proposal next to the **Comanche Peak nuclear plant** (2.4 GW, licensed through 2050/2053) — will determine whether the same broad curtailment logic applies to dispatchable nuclear pairings, not just intermittent wind.

Source: [Tech Times — Texas curtailment precedent](https://www.techtimes.com/articles/322366/20260730/texas-sets-curtailment-precedent-co-located-ai-campuses-must-run-off-grid.htm) (scraped in full via Firecrawl), cross-referenced against [Utility Dive coverage of the same ruling](https://www.utilitydive.com/news/texas-approves-ai-data-center-co-location-next-to-wind-farm-with-curtailme/826617/)

### 4CP and crypto-miner curtailment economics (the mature precedent)
- ERCOT's 4-Coincident-Peak (4CP) mechanism: transmission cost allocation set by the 4 highest 15-minute intervals June-September; full-load exposure can run **~$50,000/MW/year**. Recent 4CP intervals cluster **16:00-18:00 CT**.
- **Q3 2025**: major Bitcoin miners generated **$30.6 million in power curtailment credits** — a **147% increase** over Q3 2024 — from strategic participation in demand-response/4CP-avoidance curtailment.
- Observable grid-level effect: in June 2025, mining difficulty saw two negative adjustments (-0.45%, -7.48%) and average block times ran **~51 seconds slower during likely-4CP hours** as sites curtailed — i.e., real, measurable, economically-driven curtailment behavior at gigawatt scale, well established over multiple years.
- **Large Flexible Load (LFL) capacity**: ERCOT approved **~9,500 MW of LFL demand capacity by end of 2025** (up 73% from ~5,479 MW), with 1,570 MW newly approved in the prior 12 months — this figure spans miners and other flexible industrial load, not exclusively AI data centers.
- PUCT must finish reviewing/revise the 4CP coincident-peak cost-allocation methodology by **December 31, 2026**.
- **AI data centers specifically actually curtailing**: no evidence found (in this research pass) of a dispatched, ERCOT-called curtailment event where an AI data center (as opposed to crypto miners) actually reduced load in response to a real grid emergency in 2025-2026. NERC's 2026 summer assessment did **reduce its ERCOT peak-demand forecast by 1.9 GW and net-demand forecast by 3.7 GW** specifically citing improved modeling of "large computational load" curtailability — i.e., regulators are now underwriting the *expectation* of curtailment in planning forecasts, even where a hard operational track record for AI (vs. crypto) loads is not yet publicly documented.

Sources: [Hashrate Index — 4CP mechanics](https://hashrateindex.com/blog/4cp-for-bitcoin-miners-how-one-hour-sets-a-year-of-ercot-transmission-costs/), [Energy By 5](https://www.energyby5.com/blogs/the-new-challenges-of-managing-4cp/), [CryptoSlate](https://cryptoslate.com/bitcoin-miners-saved-the-texas-power-grid-from-collapse-but-their-lucrative-pivot-to-ai-is-stripping-away-the-emergency-brake/), [Utility Dive — 438 GW queue](https://www.utilitydive.com/news/texas-facing-438-gw-queue-approves-initial-large-load-interconnection-pro/823367/), [Utility Dive — NERC reduced ERCOT forecast](https://www.utilitydive.com/news/demand-management-data-center-flexibility-boost-regional-reliability/821225/), [Keentel — BYOG/CLR/WLPUN](https://keentelengineering.com/byog-clr-and-wlpun-explained-how-ercot-is-rewiring-the-grid-for-ai-data-centers)

---

## 4. Economics: Duke "Rethinking Load Growth" (Norris et al.) and 2026 follow-on

### Original study (February 2025)
- Authors: **Tyler H. Norris, Tim Profeta, Dalia Patiño-Echeverri, Adam Cowie-Haskell** (Duke Nicholas Institute).
- Headline finding: U.S. balancing authorities could accommodate **76-126 GW of new large flexible load** if that load can be curtailed for **0.25%-1% of hours annually** (i.e., roughly 22-88 hours/year at the low end), without triggering costly new grid capacity buildout.
- Lead author Tyler Norris testified before the **U.S. House Energy and Commerce Committee's Subcommittee on Energy** in March 2025.

### 2026 follow-on work (same Duke team, NOT a walk-back)
- New modeling extends the original study **through 2035**, quantifying long-term system impacts of flexible data-center demand:
  - Up to **$150 billion in cumulative customer savings**.
  - At **minimal flexibility (1-2% peak disconnection)**: ~15% reduction in new gas-plant construction (~12 GW avoided).
  - At **moderate flexibility (20% of demand flexible)**: ~20% gas-capacity reduction.
  - At **high flexibility (50% of demand flexible)**: ~50% of new gas capacity avoided.
  - Framing: "flexibility is fairly unequivocally going to be good for lowering emissions... shift in generation mix away from gas and into renewables."
  - Authors explicitly acknowledge limits: doesn't resolve tariff design specifics, actual AI-workload flexing constraints, cloud-customer SLA availability requirements, or enforcement mechanisms. Notably, this follow-up does **not** rebut or walk back the original study.

### Criticism (January 2026)
- A critique (Brian Handshy, Medium, widely enough discussed to be picked up in industry coverage) argues the original Duke study is being **misused in the interconnection-policy debate**: advocates cite the system-level "curtailment-enabled headroom" finding to argue **individual** data centers should get reduced network-upgrade obligations, or that virtual power plants can substitute for firm interconnection capacity — claims the critique says are **not supported by Duke's own methodology, data-center operating economics, or existing FERC/NERC standards**.
- Specific numeric objection: Duke's headline assumption of curtailment 0.25%-1% of hours/year (~44 hours/year at the 0.5% figure often cited) implies **99.50% uptime** for the flexible portion — which the critique says falls **far below the SLA (service-level-agreement) uptime requirements** that commercial/cloud data-center contracts actually demand, meaning system-level "headroom" doesn't cleanly translate into an individual project's contractual flexibility tolerance.

Sources: [Duke Climate Commitment — Rethinking Load Growth](https://climate.duke.edu/annual-report/items/rethinking-load-growth/), [PowerMag — Duke researchers](https://www.powermag.com/duke-researchers-grid-flexibility-key-to-accommodate-load-growth/), [Utility Dive — original 76-126 GW finding](https://www.utilitydive.com/news/us-grid-headroom-flexible-load-data-center-ai-ev-duke-report/739767/), [Latitude Media — 2026 long-term follow-up](https://www.latitudemedia.com/news/the-long-term-grid-impacts-of-data-center-flexibility/) (fetched in full), [Medium — Handshy critique](https://medium.com/@brianwhandshy/dukes-rethinking-load-growth-study-is-being-misused-in-the-interconnection-debate-b7d3d981e8ca)

---

## 5. Grid reliability: NERC/PJM large-load voltage-sensitivity events and ride-through standards

### The original event — July 10, 2024 (Fairfax County / "Data Center Alley")
- A **lightning strike** hit a 230 kV transmission line in Fairfax, VA; a lightning arrestor failed, causing a sustained fault; **six successive system faults over an 82-second period** eventually locked out the line.
- Result: **60 data centers simultaneously disconnected**, dropping **~1,500 MW of demand in under two minutes** — an unanticipated, correlated customer-side (load) response to a transmission disturbance, not a generation-side failure.
- Underlying mechanism flagged by NERC: many data center uninterruptible-power-supply (UPS) and protection systems are **voltage-sensitive** and trip/transfer to backup power on transient voltage sags that would not normally be considered a "fault" for conventional load.

### The repeat, larger event — July 22, 2026
- A transmission-line equipment failure in **Ashburn, VA** (Dominion Energy) caused **>3.1 GW of Northern Virginia data-center load** to disconnect and transfer to backup power — roughly **double** the 2024 event's magnitude, and ~3% of PJM's total demand at the time.
- Grid-wide effect: brief voltage/power flicker reported across a wide swath of the eastern interconnection ("Chicago to Boston and down to Miami"); PJM reported **no overall reliability impact**; normal conditions restored within **~10 minutes**.
- This is officially the **second event of its class** on PJM, and its scale (roughly doubling in two years) is the proximate trigger for the escalated 2026 regulatory response below.

### NERC/FERC regulatory response, 2025-2026
- **NERC Level 3 Essential Action Alert** issued **May 4, 2026** — warns large computational loads (AI data centers explicitly included) pose "immediate risks" to bulk power system reliability; specifies **7 required actions** for registered entities; **mandatory response deadline August 3, 2026**.
- **NERC Reliability Guideline: "Risk Mitigation for Emerging Large Loads"** — finalized **May 2026**, a 47-page document establishing engagement norms between large industrial/computational loads and the bulk power system; addresses **low-/high-voltage ride-through** requirements coordinated per-interconnection, referencing existing standards **PRC-019, PRC-024, PRC-029** as the technical basis (a specific new "PRC-029-style" mandatory computational-load standard was not confirmed by name in this research pass — see below).
- **Large Loads Action Plan (LLAP) Q2 2026 update** (published July 2026): confirms NERC has (a) issued the Level 3 alert, (b) published the Reliability Guideline, (c) opened registration of data centers as NERC-regulated entities, and (d) put **new mandatory Reliability Standards on track for Board adoption in December 2026**.
- **FERC Order, July 16, 2026, Docket No. RD26-7-000**: directly triggered by the July 22, 2026 event context (issued shortly after) — FERC **directs NERC to file one or more new/modified MANDATORY reliability standards** governing "computational loads" (defined broadly enough to cover generative-AI data centers, crypto mines, and other IT facilities) **by December 31, 2026**. NERC must also propose Rules of Procedure changes (registry criteria bringing computational-load entities directly under the mandatory framework) and file a **Phase II work plan for additional standards by March 1, 2027**.
- Technical detail flagged by NERC: sub-second/second-timescale behavior — "customer-initiated large-load reductions and significant oscillations occurring in seconds" — is driving a push for more detailed, validated **electromagnetic transient (EMT) models** of data center UPS/protection behavior, since conventional steady-state planning models don't capture it.

Sources: [NERC — Incident Review large load loss (PDF)](https://www.nerc.com/globalassets/our-work/reports/event-reports/incident_review_large_load_loss.pdf), [Modern Power Systems](https://www.modernpowersystems.com/analysis/nerc-review-of-major-load-loss-and-data-centre-impact/), [Renewable Energy World — NERC Level 3 alert](https://www.renewableenergyworld.com/power-grid/nerc-issues-level-3-alert-to-address-immediate-risks-data-center-loads-pose-to-the-grid/), [NERC Reliability Guideline PDF](https://www.nerc.com/globalassets/our-work/guidelines/reliability/RG_Risk-Mitigation-For-Emerging-Large-Loads.pdf), [electroneconomics Substack — July 22 event](https://electroneconomics.substack.com/p/on-july-22-31-gw-of-northern-virginia), [MLQ News](https://mlq.ai/news/northern-virginia-data-center-disconnect-dumps-3-gw-off-pjm-grid-takes-10-minutes-to-stabilize/), [RTO Insider — line fault 3 GW](https://www.rtoinsider.com/137301-line-fault-causes-3-gw-in-data-center-load-to-drop-in-virginia/), [Datacenter Knowledge](https://www.datacenterknowledge.com/outages/fault-in-data-center-alley-triggered-3-gw-load-drop-on-pjm), [PowerMag — FERC mandatory standards order](https://www.powermag.com/ferc-orders-mandatory-nerc-reliability-standards-for-data-center-and-other-computational-loads/), [natlawreview](https://natlawreview.com/article/ferc-directs-nerc-file-reliability-standards-apply-data-centers), [Prometheus Institute](https://prometheus.org/2026/07/18/ferc-orders-mandatory-nerc-reliability-standards-for-data-center-and-other-computational-loads/)

---

## Cross-cutting observations for the PJM/Dominion (Virginia) research thread

- The July 2026 Ashburn event is the single most important new data point since your last session state entries — it directly supersedes the July 2024 Fairfax event as the reference incident, is **2x** the magnitude, and is the proximate cause of the FERC-mandated NERC standards process now running (due Dec 31, 2026). This sits squarely in your existing PJM/Dominion/Loudoun analysis geography.
- PJM is running **two parallel curtailment tracks simultaneously**: (1) the FERC-driven **co-location/Interim-NITS tariff reform** (voluntary-ish, tied to new interconnection requests, compliance filed Feb 17 2026) and (2) PJM's own **emergency-authority + IRAS** track (DOE 202(c) order May 2026; backstop-auction/IRAS proposal July 2026) — these are different legal mechanisms with different enrollment populations and should not be conflated.
- ERCOT is meaningfully ahead of PJM operationally: it has a **contested, decided case** (Docket 59220, July 2026) establishing a hard curtailment ratio and a mature multi-year track record of **actual dispatched, economically-measurable curtailment** (4CP/crypto), whereas PJM's mechanisms are still mostly in rulemaking/filing stage with no confirmed large-scale dispatched AI-load curtailment event found in this research.
- Caution flag for any headline use of the Duke 76-126 GW / 0.5%-of-hours figure: as of January 2026 there is an active, credentialed critique arguing this system-level figure is being misapplied to justify reduced obligations for individual projects — worth citing both the number and the critique together if it appears in your report.
