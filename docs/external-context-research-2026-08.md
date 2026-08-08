# External context research — BTM, data center pipeline, transmission, emerging tech, policy

**Compiled 2026-08-07** from live web research (firecrawl). Replaces the external-context
notes lost in the 2026-07-30 directory loss. Primary consumer: sub-q2 narrative
(external context requirement per CLAUDE.md) and the eventual report's discussion
sections. Each section ends with a *relevance* note tying it to standing findings.

---

## 1. Behind-the-meter generation and co-location

**FERC's December 2025 co-location order is the watershed — and the docket is
still live.** On 2025-12-18, FERC found PJM's tariff unjust and unreasonable as to
co-located load arrangements (*PJM Interconnection, L.L.C.*, 193 FERC ¶ 61,217;
Docket **EL25-49**, consolidated with AD24-11 and Constellation's EL25-20
complaint) and ordered PJM to establish clear, nondiscriminatory co-location
rules. **Status as of 2026-08-07 (primary-source verified): not settled.** FERC's
2026-04-16 follow-on order partially rejected PJM's compliance filing (PJM's
attempted redefinition of "Co-Located Load" and BTM application requirements),
and a further 2026-06-18 order on rehearing again found parts deficient (BTMG
materiality thresholds, cogeneration exemptions) while extending the
NITS-or-contract-demand logic beyond co-located load to BTM generation
generally. Treat any "settled December rule" framing as out of date. Key
architecture ([K&L Gates summary](https://www.klgates.com/thought-leadership/FERC-Orders-PJM-to-Reform-Tariff-for-Co-Located-Generation-and-Load-1-15-2026)):

- FERC asserted jurisdiction over the wholesale/transmission components of
  co-location even when load sits behind a generator's point of interconnection;
  states keep the retail component.
- Compliance deadlines: revised interconnection procedures by 2026-01-20
  (provisional service, below-nameplate requests, surplus interconnection service);
  co-location terms + two new transmission services by 2026-02-17; revised BTMG
  netting rules by 2026-02-18.
- **New transmission service options for co-located load**: NITS with an
  *interim, non-firm feature* (temporary, curtailable, lets load connect before
  network upgrades finish — pays NITS rate but no capacity charge; trade press
  often mislabels this a standalone "Interim NITS" service), *Firm Contract
  Demand* (firm service capped at a contracted MW, penalty rate for
  over-withdrawal), and *Non-Firm Contract Demand* (1 hour–1 month terms,
  curtailed in emergencies). Rates/terms set for paper hearing beginning Feb 2026.
- **BTMG netting curtailed**: FERC found netting BTMG against load shifts costs to
  other customers and masks transmission usage; PJM must propose a MW materiality
  threshold above which BTMG loads are studied for reliability and take service
  under the new categories, with grandfathering for existing arrangements.

**PJM's 2026-02-23 compliance proposal** ([Utility Dive](https://www.utilitydive.com/news/pjm-ferc-behind-the-meter-data-center-colocation/812939/)):
new loads > 50 MW ineligible for netting (backup generation excluded from the
threshold). Industrial groups (IECA, PJM Industrial Customer Coalition) object that
this destroys the economics of industrial CHP — netting was what made
self-generation worthwhile — and note the tension with DOE's pro-BTM stance.

*Relevance:* co-location + Interim NITS is the mechanism by which very large new
loads may appear in DOM **without** proportional network upgrades first — a
forward-looking channel for exactly the localized congestion the project studies.
The BTMG netting fight also matters for load-data interpretation: netted BTMG load
is invisible in metered zonal load, so any future BTMG buildout at data centers
would decouple observed `dom_load_mw` from true consumption.

## 2. Data center development pipeline (NoVA / DOM)

- **Scale of requests:** Dominion filings show data center customers have requested
  **~70 GW** of new power — nearly 3× the ~25 GW peak of Dominion's entire existing
  Virginia system ([WUSA9/PEC](https://www.wusa9.com/article/news/investigations/data-center-transmission-lines-dominion-energy-state-corporation-commission-rider-t1/65-52f2a48b-5e85-4b3f-8d6a-4802d42fcd80)).
  Virginia hosts **600–700 data centers**, more in the pipeline
  ([Virginia Business, 2026-08-05](https://virginiabusiness.com/scc-orders-dominion-to-develop-policy-shifting-transmission-costs-to-data-centers/)).
- **DOM is the outlier zone of all PJM**
  ([Amperon](https://www.amperon.co/blog/why-virginia-data-centers-matter-to-all-of-pjm)):
  weather-normalized load CAGR 2021–2025 of **+6.50%/yr** vs RTO average +1.63%
  (second place EKPC +2.88%). Baseload growth (+6.60%/yr) outpaced peak growth
  (+5.98%/yr) — the signature of always-on data center load.
- **Prices:** DOM has priced above the RTO average every year 2021–2025; 2025 DOM
  RT averaged $60.65/MWh vs RTO $46.90. **Jan–Apr 2026: DOM DA $95.70, RT $98.47,
  RT premium over RTO = 40.9%.** RT running above DA signals demand the DA market
  did not anticipate.
- **Cooling of the permitting environment:** Loudoun **eliminated by-right
  zoning 2025-03-18** (special-exception review now required; applications filed
  before 2025-02-12 grandfathered). **2026-07-22: the Board voted 6–1 to draft a
  full application moratorium**, pending legality review, with a decision
  expected at the 2026-09-15 meeting. Loudoun inventory ≈ 46M sq ft
  built/permitted + 8–10M under construction, ~61.5M sq ft pipeline (secondary
  source, directional). Suffolk, Front Royal, and Chesapeake are moving on
  similar pauses/bans. PEC reports the development pace has "slowed
  significantly, with many proposals deferred or denied"
  ([PEC](https://www.pecva.org/work/energy-work/push-back-against-more-transmission-lines-for-data-centers/)).

*Relevance:* the Amperon numbers are an independent, zone-level corroboration of
this project's core descriptive facts (load +21.5% over the 3.4-yr 5-min panel;
2026 price escalation), from a commercial forecaster with no stake in our
methodology. The RT>DA "demand surprise" framing is a useful complement to our
finding that the 2026 escalation is system-wide in origin — DOM-wide price levels
can rise while the *locational* congestion component stays network-wide, which is
exactly what the two-price-channels decision records. **The standing rule stands:
do not attribute the 2026 escalation to data centers**; the 70 GW request pipeline
is prospective, not an observed 2026 driver.

## 3. Transmission development

- **PJM 2025 RTEP Window 1 approved 2026-02-12**: $11.84B in new baseline
  projects per PJM's own whitepaper ($12.24B counting scope/cost changes to
  prior projects), of which **Dominion lands ~$4.8B**
  ([Utility Dive](https://www.utilitydive.com/news/pjm-rtep-transmission-expansion-plan-dominion-nextera-exelon/812311/)).
  Centerpiece: a **$2.3B, 185-mile, 525-kV underground HVDC "backbone"** with two
  converter stations (~$1.5B), delivering **3,000 MW into Loudoun County**, online
  June 2032. NextEra–Exelon get a $1.7B Pennsylvania project (June 2031); PPL
  ~$580M; ComEd ~$276M; Pepco ~$292M.
- **Transmission's bill share is rising**: transmission contributed $17.71/MWh to
  PJM wholesale power cost in 2024, up 23% from $14.40 in 2022 (Monitoring
  Analytics). Dominion says **~68% of its $7.59B in transmission projects planned
  through 2031 is driven by data center growth** (own filings, via WUSA9).
- **Contested corridors** (PEC): additional Dominion 500 kV proposals (Lynchburg–
  Appomattox–Fluvanna loop; Gordonsville–Morrisville line), the region's **first
  765 kV line**, and the active multi-state **MARL** 500 kV cases. **Valley
  Link**, a 115-mile 765 kV line feeding NoVA demand, would be the largest ever
  built in Virginia; Buckingham, Goochland and Louisa counties have each budgeted
  $250K to fight it.
- **GOOSECRE is a corridor terminus, not a passive cluster node.** The Goose
  Creek substation east of Leesburg (near-certainly the facility behind our
  GOOSECRE pnode; inferred from name/location/ownership, not yet checked against
  a pnode map) is the confirmed terminus of two concurrent bulk builds:
  (1) **MARL / Gore–Doubs–Goose Creek** (PJM project B3800, ~$5B, NextEra +
  Potomac Edison/FirstEnergy), a ~150-mile 500 kV import corridor PA→WV/MD→
  Loudoun, in-service ~2029–2031; live dockets VA SCC PUR-2026-00018, WV PSC
  26-0075-E-CN (hearing Oct 26–Nov 2, 2026), MD PSC 9870, PA PUC A-2026-3060856;
  and (2) Dominion's Line 514 corridor upgrade (Potomac River → Goose Creek).
  Dominion's **Aspen–Golden** (SCC approved 2025-02-05, VA Supreme Court affirmed
  2026-02-19) and **Golden–Mars** (PUR-2025-00056, final order 2026-06-29) form a
  separate eastern-Loudoun reliability loop serving Ashburn. Forward-looking
  interpretation of GOOSECRE congestion should account for this.
- **Dominion–NextEra merger (~$67B, announced ~May 2026)**: the two MARL
  co-developers are merging; Gov. Spanberger intervened 2026-08-06. Reported as
  not affecting MARL, but worth monitoring.
- **SKFFSCRK rural framing confirmed**: the node is the Surry–Skiffes Creek–
  Whealton 500 kV line's James City County switching station (energized
  2019-02-26; VA SCC PUE-2012-00029). No data center development found at
  Skiffes Creek itself; James City County began regulating data centers
  (Sept/Nov 2025 zoning) but nothing is sited near the station.
- Dominion: residential customers' share of transmission cost allocation fell
  ~27% over five years while data centers' share rose ~148%; the Data Center
  Coalition cites JLARC and LBNL studies that data centers "are not driving up
  residential rates."

*Relevance:* the 3,000 MW HVDC injection into Loudoun (2032) and the 765 kV
proposals are the supply-side response to the congestion pocket our pnodes sit in.
For sub-q2 projections, any exceedance-rate extrapolation must acknowledge that
the binding transmission constraints are scheduled to be materially relaxed on a
2031–2032 horizon. The Goose Creek MARL segment is worth tracking for direct
relevance to the GOOSECRE node.

## 4. Emerging technologies

**Nuclear / SMR co-location** ([SMR Intel deal tracker](https://smrintel.com/nuclear-data-center-deals/)):
committed nuclear capacity for data centers now exceeds **9.8 GW**:

- Microsoft: 20-yr PPA for the full 835 MW of the Three Mile Island Unit 1 restart
  (Crane Clean Energy Center); FERC approved a transmission-rights transfer
  2026-06-01; full power expected **H2 2027** (first nuclear electrons for an AI
  data center).
- Amazon: $700M into X-energy, up to 12 Xe-100 SMRs (first phase 320 MW).
- Google: 500 MW from Kairos Power.
- Meta: up to **6.6 GW** across TerraPower Natrium (2.8 GW + 1.2 GW storage,
  first units 2032), Oklo, Vistra, Constellation.
- Aalo: first commercial Aalo Pod co-located with an AI data center near INL;
  experimental reactor targeting criticality July 2026. 30 microreactors planned
  in Haskell County, TX (ERCOT).
- Pattern: restarts deliver fastest (2027); new-build SMRs deliver scale (2032+).
  Dominion itself is "actively exploring" SMRs (Amperon).

**Nvidia/Span residential mini data centers** ([Realtor.com](https://www.realtor.com/news/trends/nvidia-pultegroup-span-date-center-backyard/)):
Span's **XFRA** program puts liquid-cooled, fanless Nvidia-based server boxes on
new homes, exploiting the ~60% of residential electrical capacity that sits idle;
Span detects headroom via its smart panels. Hosts get bills paid / ~$150 flat fee;
PulteGroup (a top-5 US homebuilder) is trialing it, with a **100-home proof of
concept planned within the year**. Explicit pitch: faster and cheaper than siting
centralized data centers because distribution capacity already exists.

**Flexible / curtailable data center load** (subagent research, 2026-08-07 —
full notes in session scratchpad `research/E-flexible-load.md`):

- **Demonstrated vs announced — the gap is wide.** Emerald AI (Nvidia-backed) has
  real pilot data: 5 live pilots incl. Virginia; up to 40% power reduction in
  <60 s; a 3-hour sustained 25% cut (Phoenix); a 10-hour/5-day test (London).
  Its flagship 96 MW purpose-built-flexible **Aurora facility in Manassas, VA**
  comes online late 2026 (announced, not demonstrated). EPRI DCFlex expanded to
  9 sites (Feb 2026, incl. an Ashburn↔Chicago load-shift test) with no public MW
  results yet. Google has ~1 GW of DR integrated into utility contracts (I&M,
  TVA, Entergy Arkansas, Minnesota Power, DTE) but no evidence of a dispatched
  curtailment event.
- **ERCOT vs PJM contrast**: ERCOT curtailment is economically real (bitcoin
  miners earned $30.6M in curtailment credits in Q3 2025 alone, +147% YoY);
  **PUCT Docket 59220 (decided 2026-07-23)** required a 260 MW Crusoe/Google AI
  campus co-located behind a wind farm to curtail the entire 525.5 MW load
  within 30 minutes in emergencies, without paid-DR revenue — effectively
  forcing full backup capacity for BTM co-location. PJM is still in rulemaking
  (the curtailable interim-NITS product; DOE 202(c) order May 2026; proposed
  IRAS mechanism July 2026), with no confirmed enrollees found.
- **New reference reliability incident:** the July 2024 Fairfax 1,500 MW
  data-center load-loss event is superseded by a **2026-07-22 Ashburn event that
  dropped ~3.1 GW** (≈60 data centers' worth of load, flicker felt Chicago→Miami,
  restored in ~10 min). It triggered a **FERC order (2026-07-16, immediately
  prior) directing NERC to file mandatory computational-load ride-through
  standards by 2026-12-31**, on top of NERC's May 2026 Level 3 Alert.
- **Headroom economics:** Duke/Nitricity "Rethinking Load Growth" (Norris et al.:
  76–126 GW absorbable at 0.25–1% curtailment) has a 2026 follow-up (up to $150B
  savings) and a Jan 2026 critique (the 99.5%-uptime assumption understates real
  SLAs; system-level headroom misapplied to individual projects). Cite the pair
  together.

*Relevance:* both dispersal trends (SMR co-location via BTM supply, XFRA via
distribution-level siting) and demonstrated curtailability push future AI load
**off** the transmission-scale congestion pockets we study, cutting against naive
extrapolation of 2023–2026 locational stress in sub-q2. The CLAUDE.md requirement
to cover the "Nvidia residential mini-DC trend" is satisfiable with the
PulteGroup trial as the concrete anchor. **The 2026-07-22 Ashburn 3.1 GW event
falls three weeks after our 5-min panel ends (2026-06-30)** — it cannot appear in
our data, but it is the natural motivating incident for any follow-on pull and
for the reliability framing of the final report.

## 5. Policy and regulation (Virginia + PJM)

- **GS-5 rate class approved.** SCC's final order in Dominion's biennial review
  (case **PUR-2025-00058**, order 2025-11-25) creates a rate class for customers
  demanding **≥ 25 MW**, effective **2027-01-01** (the WUSA9 piece says minimum demand charges under **14-year
  contracts** with expanded deposits, "takes effect Jan. 1"). Large customers must
  pay minimums of **85% of contracted distribution/transmission demand and 60% of
  generation demand** regardless of usage
  ([SCC release](https://www.scc.virginia.gov/about-the-scc/newsreleases/release/scc-issues-order-on-dev-biennial-review-2025/scc-rules-in-dev-biennial-review-case.html)).
  Same order: Dominion's requested base-rate increases cut to $565.7M (2026) and
  $209.9M (2027); typical residential bill +$11.24/mo in 2026; ROE 9.8%.
- **Rider T-1 order, issued 2026-07-31** (case **PUR-2026-00056**; $2.90→$0.94
  figures corroborated by four outlets, SCC order PDF itself not yet read —
  [Virginia Business](https://virginiabusiness.com/scc-orders-dominion-to-develop-policy-shifting-transmission-costs-to-data-centers/)):
  the SCC cut the residential transmission-rider increase from $2.90 to
  **$0.94/mo** (effective Sept 1) by shifting cost to large-load customers, and
  gave Dominion **90 days to file a "direct connect" policy** — substations and
  lines built to connect large loads get assigned to those customers. PEC, ODEC
  and SCC staff pushed a **"but-for" test** (if a line exists only because of a
  data center, the data center pays 100%, upfront via contribution in aid of
  construction). Gov. Spanberger's administration formally backed assigning
  data-center-driven transmission costs to the facilities.
- **Cooperative model:** Rappahannock Electric Cooperative proposes fully siloing
  ≥25 MW customers — collateral, infrastructure contributions, market-rate
  pass-through supply — described as the "gold standard" for ratepayer insulation
  ([News from the States](https://www.newsfromthestates.com/article/will-special-rate-classes-protect-va-residents-costs-serving-data-centers)).
- **Industry counter-position:** Data Center Coalition cites JLARC + Lawrence
  Berkeley findings that data centers aren't driving residential rates and absorb
  fixed costs; Amazon points to the (voluntary) White House Ratepayer Protection
  Pledge signed March 2026. PEC's rebuttal: voluntary pledges function as queue
  fast-tracks, not cost allocation.

### What the cited studies actually say (subagent literature review, 2026-08-07)

- **JLARC Report 598 (Dec 2024)** makes a rate-*design* fairness finding — data
  centers "are currently paying their full cost of service" — **not** a
  "rates haven't risen" finding, and immediately warns costs "will likely
  increase" for everyone. Its projections: typical Dominion residential
  generation+transmission charges rise **+$14–37/month by 2040** (2024 dollars)
  depending on scenario (+$33–37 unconstrained; +$14 at half-unconstrained);
  systemwide Dominion-zone costs +$16–18B (unconstrained) or +$8.5–10B (half) by
  2040; unconstrained demand needs +54–56 GW of new generation vs. the ~36 GW
  existing system. Eight formal recommendations (delay-not-deny authority, DR
  mandates, stranded-cost plan…); a separate data-center rate class was
  discussed but **not** formally recommended — the SCC's GS-5 class (above) goes
  beyond JLARC.
- **The "LBNL study" is LBNL/Brattle, "Retail Electricity Price Trends and
  Drivers: 2026 Edition" (Apr 2026)**. Nationally it finds high-load-growth
  states saw real retail prices *decline* 2019–2025, data centers not altering
  the conclusion — **but it carves out an explicit exception in a case study
  titled "PJM Capacity Auction demonstrates price increases with load growth,"
  attributing PJM capacity price surges to data-center load growth.** Virginia
  is in PJM; industry citations drop the exception. Even E3's Data Center
  Coalition–funded May 2026 whitepaper concedes "LBNL's recent study found
  similar results, except in the PJM region."
- **Monitoring Analytics attribution numbers** (PJM's independent market
  monitor): 63% (~$9.3–9.4B) of the 2025/26 BRA price increase attributable to
  data centers; $6.3B of $16.4B (38%) in the 2028/29 auction; cumulative across
  the last four auctions **$29.4B of $63.6B (46%)**. E3's own estimate (~50% of
  the auction jump load-growth-driven) is direction-consistent.
- **Harvard Salata Institute (Peskoe & Martin, Mar 2025)**: reviewed 40
  confidential utility–data-center special contracts; found utilities plan to
  recoup discount losses from other ratepayers (e.g. Duke/Fayetteville: $325M
  discount, $100M acknowledged loss), terms shielded from scrutiny.
- **No JLARC follow-up exists as of Aug 2026**; the 2026 "update" circulating is
  the E3 whitepaper funded by the Data Center Coalition, reusing E3's 2024
  JLARC-commissioned analysis plus an Amazon-funded facility study.
- **PJM governance:** stakeholder support is coalescing around strengthening PJM
  board independence and giving states more influence (Utility Dive RTEP piece).

*Relevance:* GS-5's 85%/60% minimum-demand structure and the direct-connect order
change the *forward* incentive landscape — they make speculative capacity requests
expensive, which bears on how much of the 70 GW pipeline materializes. For the
JLARC-based sub-q2 projection, note the JLARC "not driving residential rates"
finding is now actively cited by industry in live rate cases; our projection
framing should cite JLARC's own scope and not overclaim in either direction.

## 6. PJM capacity market and load forecast (subagent research, primary-sourced)

- **BRA clearing prices (RTO, $/MW-day UCAP):** $28.92 (2024/25) → $269.92
  (2025/26, +833%) → $329.17 (2026/27) → **$333.44 (2027/28, record — cleared at
  the FERC-approved cap)** → $325.00 (2028/29). The cap/floor collar comes from
  the Shapiro settlement (ER25-1357, approved 2025-04-22, covers 2026/27–2027/28)
  extended in ER26-1556 (approved 2026-04-28, covers 2028/29–2029/30). Every
  recent auction cleared **short of the reliability requirement** — the shortfall
  grew from 6,623 MW (2027/28) to 6,831 MW (2028/29); PJM plans a September 2026
  "Backstop Procurement."
- **DOM zone nuance (important for us):** DOM was a *constrained* LDA at its own
  zonal cap of **$444.26/MW-day in 2025/26**, but cleared at the flat RTO price
  in 2026/27 and 2027/28. PJM's own no-cap/no-floor simulation for 2027/28 shows
  **DOM would have been the only zone to bind separately, at $542.83/MW-day** —
  DOM's structural import constraint is real but currently masked by the
  RTO-wide cap binding first. PJM's 2028/29 planning materials confirm DOM's
  CETL/CETO remains below 1 and that "the majority" of eastern transmission-
  upgrade delays sit in the DOM LDA.
- **Monitoring Analytics attribution (primary figures):** data-center load added
  **$7.27B (82.1%)** to the 2026/27 BRA and **$6.50B (65.5%)** to 2027/28 —
  **$23.1B combined across the three recent BRAs**. A dedicated "Data Center
  Alley" case study: Dominion data-center growth drove **$1.4B in transmission
  upgrades cost-shifted via Schedule 12 to all PJM zones**, not just DOM —
  precisely the cost-shifting concern behind FERC's 2026 large-load orders.
  (These are the market monitor's own reports; the slightly different splits in
  §5's literature review reflect different auction subsets.)
- **Two distinct FERC proceedings, easy to conflate:** EL25-49 is the
  PJM-specific co-location order (§1). Separately, FERC's **2026-06-18 Section
  206 show-cause orders hit all six RTOs** on large-load interconnection; PJM's
  docket is **EL26-67-000**, with a justify-or-reform tariff deadline of
  **2026-08-17** (ten days from this writing — watch it).
- **Load forecast vetting:** PJM now counts near-term data-center requests at
  full weight only with "firm" (Electric Service Obligation / Construction
  Commitment) status; non-firm requests are derated. DOM is the only zone
  adjusted for both data-center growth and a voltage-optimization program.

*Relevance:* the capacity market is where data-center attribution is
quantitatively strongest — a useful contrast for our energy-market findings,
where the 2026 escalation is system-wide and must not be attributed to data
centers. The DOM $542.83 shadow price and sub-1 CETL/CETO are independent
evidence of the import-constrained pocket our congestion results live in, and
Schedule 12 cost-socialization is the transmission analogue of the
"who pays" policy fight in §5.

## 7. The January 2026 escalation: external evidence (subagent research)

Our panel's biggest unidentified finding — the simultaneous January 2026 step in
congestion p90 ($20.46 → $231.29) and system-energy p90 ($86.32 → $292.19) — now
has a well-evidenced external candidate mechanism (full notes:
`docs/research-notes/F-jan2026-driver.md`):

1. **Winter Storm Fern (2026-01-21 → 01-30) explains both channels.** PJM ran
   130+ GW load for 8 straight days with its **worst forced-outage rate on
   record for a comparable event** (18–19 GW avg vs 12–13 GW in Jan 2025);
   Henry Hub hit an all-time high **$30.72/MMBtu (Jan 23)**. Monitoring
   Analytics' Q1 2026 LMP decomposition ($52.20 → $87.57/MWh, +67.8% YoY)
   attributes **42.2% of the increase to fuel (system-energy channel) and 27.5%
   to the transmission constraint penalty factor (congestion channel)** — a
   structural match to the simultaneous two-component step. January alone was
   ~60% of Q1's ~$2B congestion cost.
2. **DOM's chronic constraint explains the localization**: MMU states DOM had
   the highest zonal congestion of all control zones in Q1 2026 ($356.7M).
   Discrete events continued: a late-May 2026 **Ashburn–Goose Creek 230 kV
   constraint cost ~$150M in 72 hours**. **Cross-checked against our re-pulled
   5-min panel 2026-08-07: confirmed** — daily congestion p95 at GOOSECRE hit
   $550 (May 18), $502 (May 19), then $564 (May 27, cluster $663), with
   intraday peaks to $1,218, against single-digit p95s on surrounding days.
   External record and panel agree.
3. **PJM's operational posture as amplifier (most surprising):** the MMU found
   Q1-2026 real-time SCED ran transmission "control limits" **below physical
   limits in 94% of violated-constraint intervals**, estimating congestion LMP
   would have been ~$0.08/MWh instead of $13.76 without the discretionary
   de-rating. Part of the "driver" is administrative, not physical.
4. **Persistence: level shift, not spike.** Feb 2026 RT averaged ~$85/MWh (2×
   Feb 2025) with outages carrying forward; DOM's premium over RTO *widened*
   Jan→Apr (29% → 40.9%). Ruled out: no ORDC/offer-cap change near Jan 2026
   (cap unchanged at $3,700/MWh); no DOM retirement or large-load energization
   pinned to January.

*Relevance:* this is external evidence, not our own estimation — the advisor
framing for sub-q1 stands — but the write-up can now name Winter Storm Fern +
record forced outages + gas ATH as the leading candidate mechanism, with the MMU
decomposition mapping cleanly onto our two-channel decomposition, and the
94%-control-limit finding as a caveat that some 2026 congestion is
operator-discretionary. Consistent with the standing rule: the January 2026
escalation is a system-wide winter event amplified in an import-constrained
zone — **not** attributable to data centers.

## 8. Non-DOM control pnode candidates (subagent research)

Addresses the standing limitation that every pnode in both panels sits inside
DOM. Candidate names verified live against PJM Data Miner's pnode browser
2026-08-07 (full table: `docs/research-notes/G-control-pnodes.md`):

- **Top 3**: **HARRISON** (APS, 500 kV, Harrison Co. WV — west of the AP South
  seam), **AMOS** (AEP, 765 kV, Putnam Co. WV), **SULLIVAN-AEP** (AEP, 765 kV,
  southern Indiana — far from I&M's northern-Indiana hyperscale cluster).
  **FORTMARTIN** (APS, 500 kV) usable with a caveat (a 1,200 MW gas plant is
  being permitted there for ~2031 — supply-side, likely congestion-dampening).
- **False positives caught by verification**: MOUNTAINEER (same WV county as
  Nscale's 8 GW Monarch campus — drop) and CONEMAUGH/KEYSTONE (county shared
  with the ~4 GW Homer City conversion — backup only). The general lesson: the
  site profile data centers seek (big EHV station, cheap rural land, legacy
  plant) is exactly the profile of good "control" candidates, so clean status
  means **clean-through-2026, not clean going forward**.
- **LDA logic:** DOM is its own LDA; in 2025/26 (the last un-capped auction)
  only DOM ($444.26) and BGE ($466.35) cleared above RTO ($269.92) — APS, AEP,
  PENELEC etc. were empirically unconstrained, making them valid "different
  congestion regime" sources.
- **Hub vs bus:** use a physical EHV bus as primary control (point-decomposable
  into energy/congestion/losses, symmetric with our nodes). Zone aggregates are
  a secondary robustness check. **Financial hubs are disqualified** — hubs are
  low-congestion-sensitivity weighted averages, and Western Hub reportedly
  includes DOM buses (secondary source, unverified).
- Next concrete step when data acquisition resumes: probe HARRISON / AMOS /
  SULLIVAN-AEP as gridstatus 5-min `location_id`s (1 request each on the spare
  account) and pull hourly from PJM Data Miner (free) for a first-pass check.

## 9. Event catalog for sub-q3 (subagent research)

A dated catalog of grid-stress and market events covering our panel window
(2023-02 → 2026-06) now exists at `docs/research-notes/H-event-catalog.md`:
**31 dated rows** (28 in-window, 2 marked outside-window, 1 baseline) plus a
7-row annual census of PJM-declared emergency alerts (2023–2026Q1) built from
Monitoring Analytics primary tables. Anchor events: the 2024-07-10 Fairfax
1,500 MW data-center load loss; Winter Storms Gerri (2024-01, ~134 GW peak) and
Fern (2026-01); the all-time PJM winter peak 143,714 MW (2025-01-22); the
all-time summer peak 168,158 MW (2026-07-02, outside window); the 2025-02-19
DOM_ASHBURN load-management action (the only Ashburn-tagged emergency action
found); the NERC Level 3 data-center alert (2026-05-04).

Corrections made against primary sources during compilation, worth retaining:
- **Winter Storm Fern's actual peak was 139,047 MW (2026-01-29)** — press
  circulated a 147,347 MW *forecast* as a "record"; the 2025 record stood.
- **2023 was not quiet**: it had **more shortage-pricing days (46) than any
  other year in the window**, despite hosting neither record storm.
- **Zero PJM Performance Assessment Intervals triggered 2023 → Q1 2026** —
  confirmed via Monitoring Analytics, not inferred from absence.

Known gaps for a follow-up pass: DOE OE-417 per-year Excel files not
systematically mined; sub-day scarcity-pricing intervals (source PDFs are
downloaded); distribution-level storm outages below NERC thresholds.

*Relevance:* this is the concrete starting artifact for sub-q3's
event-correlation design ("replace the coarse 2-5am × shoulder filter with an
event catalog"). The zero-PAI finding and the 46-day 2023 shortage-pricing count
are both useful priors: scarcity conditions were frequent in-window even before
the 2026 escalation, and PJM's capacity-performance trigger never fired.

---

## Source quality notes

Search + scrape performed 2026-08-07 with firecrawl; five parallel research
subagents then verified primary sources and deepened each thread — their full
notes (page citations, docket links, exact quotes) are in `docs/research-notes/`
(A: primary-source verification, B: Loudoun/pnode geography, C: capacity market
and load forecast, D: JLARC/LBNL literature, E: flexible load). Trade-press items (Utility Dive, Virginia
Business, WUSA9) are dated and quote primary filings; the K&L Gates and SCC pages
are near-primary; smrintel.com and the Amperon blog are commercial secondary
sources — verify any number reused in the final report against the underlying
filing (FERC eLibrary docket for 193 FERC ¶ 61,217; SCC case dockets PUR-2025 for
the biennial review and Rider T-1; PJM RTEP board whitepaper).
