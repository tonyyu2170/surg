# Candidate control pnodes outside the DOM zone/LDA

Research date 2026-08-07. Web research only; no gridstatus.io calls; no repo writes.

## 0. Headline finding before the candidate list

Verifying actual bus names against PJM's live Data Miner pnode table (see §3) surfaced a
pattern that changes how this list should be used: **the physical trait that makes a bus a
good electrical control — a large-capacity EHV switching station next to a legacy (often
retired/retiring) power plant, in cheap rural land, far from a metro load center — is
*exactly* the site-selection profile data-center developers are targeting nationally in
2026.** This is structurally the same thing that happened at LOUDOUN/PLEASANTVIEW/GOOSECRE/
SKFFSCRK. Two of the candidates that looked cleanest from zone-level auction data turned out,
on a direct county-level news check, to already have a large project announced at or within
the same county as the specific bus:

- **CONEMAUGH / KEYSTONE (PENELEC, Indiana County, PA)** — Homer City Generating Station,
  the retired coal plant in the *same county*, has a ~4 GW data-center conversion proposal
  (Blackridge Research; Spotlight PA, July 2026; PennFuture). Both are legendary rural
  500 kV coal-plant nodes about 12–20 miles from Homer City. Not disqualifying by itself
  (Homer City is a distinct pnode, not yet a separate EHV entry in the feed), but treat as
  **elevated risk**, not a clean pick.
- **MOUNTAINEER (AEP, Mason County, WV, 765 kV)** — Nscale's Monarch Compute Campus
  (up to 8 GW planned, Microsoft LOI for 1.35 GW) is in the *same county* (Point
  Pleasant/Camp Conley, WV). **Drop this one.** One mitigant worth noting: reporting
  describes Monarch as "gas-powered" with ~984 on-site generators, i.e. possibly
  substantially behind-the-meter/self-supplied rather than a pure grid load — but that
  needs its own verification before trusting it, so don't rely on it as a defense.

Two zone-level confounders also apply broadly and should temper every AEP-zone pick:
AEP's Ohio territory (New Albany/Columbus corridor) and AEP's Indiana-Michigan (I&M)
subsidiary (Fort Wayne, New Carlisle, LaPorte — AWS $11B, Google $2B, Microsoft $1B) are
both in the middle of the same boom. The specific bus-county checks below try to route
around those clusters, not around the zone as a whole.

**Practical implication:** treat every candidate's "clean" status as **clean-through-2026**
(i.e., no realized load at that specific bus in the historical LMP record used for this
panel), not "clean going forward." Announced/pipeline capacity (EKPC's 10 GW of *requests*,
I&M's 2030 projection, Bedington/Berkeley County's 2026 permitting-stage campus) is not yet
in the load or LMP data as of mid-2026, which is what matters for a panel-regression control.
Re-screen this list before extending the study window past ~2027–2028.

---

## 1. PJM LDA structure and where DOM sits

DOM (Dominion, VA + NC) is its own named Locational Deliverability Area (LDA) in PJM's
capacity market — it is not folded into a larger regional LDA like EMAAC or SWMAAC.

**2026/2027 BRA-modeled LDAs:** MAAC, EMAAC, SWMAAC, PSEG, PS-NORTH, DPL-SOUTH, PEPCO, ATSI,
ATSI-Cleveland, COMED, BGE, PL (PPL), DAY, DOM, DEOK, JCPL.
[2026/2027 BRA Report](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-report.pdf)

Zones **not** separately modeled as their own LDA (APS, PENELEC, AEP, EKPC, ComEd's western
neighbors, etc.) are priced at the RTO-wide reference price — PJM's own market design treats
them as *not* independently import-constrained. That is a defensible, sourced proxy for
"different congestion region from DOM":

| Tier | Zones | Basis |
|---|---|---|
| **Tier 1 — not separately modeled as an LDA** | APS, PENELEC, AEP, EKPC | Absent from the BRA LDA list entirely; PJM doesn't think these need their own capacity price |
| **Tier 2 — modeled but cleared at RTO price in 2025/26** | PL (PPL), DAY, DEOK, ATSI, ATSI-Cleveland, ComEd | Separately monitored by PJM (so an interface/constraint exists on paper) but not binding in the last clean auction |
| **Excluded — cleared above RTO (2025/2026)** | DOM ($444.26/MW-day), BGE ($466.35/MW-day) vs. RTO $269.92/MW-day | Confirms DOM (and BGE) are the ones with realized locational scarcity |

Sources: [Utility Dive, PJM capacity prices set another record](https://www.utilitydive.com/news/pjm-interconnection-capacity-auction-prices/753798/);
[PJM 2025/2026 BRA Report](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/2025-2026-base-residual-auction-report.pdf)

**Caveat:** the 2026/2027 auction cleared *every* LDA at the FERC price cap ($329.17/MW-day,
a system-wide reserve-shortfall event), so it is uninformative for telling constrained zones
apart from unconstrained ones. Use 2025/2026 as the clean read; treat 2026/2027 as a "the cap
bound everywhere" data point, not a ranking.

**Geographic/electrical boundary west of DOM:** the AP South interface (the Bedington–Black
Oak / Meadow Brook–Doubs 500 kV corridor in the WV Eastern Panhandle) is PJM's long-standing
name for the transfer limit separating western, generation-rich APS/AEP territory from the
eastern Mid-Atlantic load pocket (DOM, EMAAC, SWMAAC, MAAC). A separate, specifically named
**AEP-Dominion interface** also appears in PJM's historical top-5 congestion-driver lists —
meaning AEP-zone buses close to that seam (southwest/south-central Virginia AEP nodes) can
still co-move with DOM congestion. Prefer AEP candidates on the WV/OH/IN side of that seam
over AEP's Virginia buses.
[PJM/Monitoring Analytics congestion history](http://www.monitoringanalytics.com/reports/pjm_state_of_the_market/2011/2011q2-som-pjm-sec7.pdf)

---

## 2. Candidate table

All pnode names below were pulled live from PJM Data Miner 2's public pricing-node browser
(`https://dataminer2.pjm.com/feed/pnode`, filtered by Transmission Zone + Pricing Node
SubType = EHV) on 2026-08-07 — these are real, current `pnode_name` values, not names from
memory. Voltage is as tagged in that feed.

| Candidate (`pnode_name`) | Zone | Tier | Voltage | Geography | Why electrically distant from NoVA | Known confounders |
|---|---|---|---|---|---|---|
| **HARRISON** | APS | 1 | 500 kV | Harrison County, WV (near Clarksburg) | West of the AP South seam, deep in APS's WV backbone | No data-center or major-load announcement found in this pass. Best-checked APS candidate. |
| **FORTMARTIN** | APS | 1 | 500 kV | Monongalia County, WV (Maidsville, near Morgantown) | West of AP South, adjacent to Fort Martin coal plant | FirstEnergy/Mon Power is permitting a 1,200 MW **gas-fired plant** at this site ("Maidsville Energy Center," in service ~2031) to serve data-center load *elsewhere* in FirstEnergy's territory — this is a **supply-side** addition at the bus, not a local load addition, so it plausibly *dampens* rather than inflates local congestion. Still worth flagging and re-checking once online. [Dominion Post, June 2026](https://www.dominionpost.com/2026/06/03/a-look-at-firstenergys-planned-gas-fired-plant-and-fort-martin/) |
| **CONEMAUGH** | PENELEC | 1 | 500 kV | Indiana County, PA | West-central PA, outside any EMAAC/MAAC congestion pocket | **Elevated risk**: Homer City Generating Station (same county, ~4 GW data-center conversion proposal) is in active permitting as of July 2026. Not the same bus, but same county/local grid pocket. |
| **KEYSTONE** | PENELEC | 1 | 500 kV | Indiana County, PA | Same corridor as Conemaugh | Same Homer City caveat as above. |
| **VINCO** | PENELEC | 1 | 500 kV | Cambria County, PA area (Johnstown vicinity) | West-central PA | No confounder found in this pass; less exposed to the Homer City county than Conemaugh/Keystone, but unverified — check before use. |
| **AMOS** | AEP | 1 | 765 kV | Putnam County, WV (St. Albans/Winfield area) | Deep in AEP's WV 765 kV backbone, west of AP South and away from the AEP–Dominion seam | No county-level data-center news found in this pass. Zone-wide caution: AEP overall is mid-boom (Ohio + I&M), but this specific county wasn't named. |
| **SULLIVAN-AEP** | AEP | 1 | 765 kV | Sullivan County, southern Indiana | Far southern Indiana, hundreds of miles from I&M's Fort Wayne/New Carlisle/LaPorte growth cluster (all northern Indiana) | No confounder found in this pass; general I&M zone-wide growth (peak demand doubling to ~8,000 MW by 2030) is a distant-future risk, not yet in the historical record. |
| **JACKSONS FERRY** | AEP | 1 | 765 kV | Wythe County, VA (near Wytheville) | Different LDA (AEP, not DOM) despite being geographically in Virginia | **Caveat**: this is an AEP-zone bus in Virginia, closer to the historically-named AEP–Dominion interface than the WV/IN picks above — treat as a weaker "different congestion region" candidate than Harrison/Amos/Sullivan. |
| ~~MOUNTAINEER~~ | AEP | — | 765 kV | Mason County, WV (New Haven) | — | **Drop.** Same county as Nscale's Monarch Compute Campus (up to 8 GW planned, Microsoft 1.35 GW LOI, first phase targeted 2027–2028). |
| EKPC / DAY / DEOK — **no EHV-tagged bus exists** | EKPC, DAY, DEOK | 2 | n/a | Kentucky co-op; Dayton, OH; Cincinnati, OH | — | The live pnode feed returned **zero rows** for these three zones when filtered to SubType = EHV. These zones don't carry their own 500/345 kV switching-station nodes in PJM's node taxonomy (their EHV ties are presumably tagged under a parent transmission owner). If you want these zones, you'd have to use a zone aggregate (e.g. "DAY", "DEOK", "EKPC") or drop to their highest-available bus voltage — not a clean bus-level congestion-component comparison. |

**Recommended shortlist to actually pull LMP for first:** HARRISON, AMOS, SULLIVAN-AEP —
these three cleared every check run in this pass (Tier 1, verified EHV bus, no county-level
project found). FORTMARTIN is a reasonable fourth if you're comfortable with a supply-side
(not load-side) future confounder. Treat CONEMAUGH/KEYSTONE as backups only, and drop
MOUNTAINEER outright.

---

## 3. Pnode/zone discoverability — how this was actually done

PJM Data Miner 2's **Pricing Nodes** reference feed
(`https://dataminer2.pjm.com/feed/pnode`, definition at
`https://dataminer2.pjm.com/feed/pnode/definition`) is a public, no-API-key browsable table
(confirmed by direct interaction, 2026-08-07) covering **~14,450 total pnodes**. Its
filterable columns are exactly what's needed:

- **Transmission Zone**: dropdown includes AECO, AEP, APS, ATSI, BGE, COMED, CPL, DAY, DEOK,
  DOM, DPL, DUKE, DUQ, EKPC, EXTERNAL, JCPL, METED, PECO, PENELEC, PEPCO, PPL, PSEG, RECO,
  OVEC.
- **Pricing Node SubType**: dropdown includes AGGREGATE, EHV, EXT, GEN, HUB, INTERFACE, LOAD,
  RESIDUAL_METERED_EDC, TIE, ZONE. **"EHV" is a literal, first-class tag** — filtering
  SubType=EHV + Zone=<X> returns exactly the 500/765 kV backbone buses for that zone, which
  is how the candidate table above was built.
- **Pricing Node Type**: AGGREGATE, BUS, LOCALE.
- Voltage Level is a plain column (e.g. "500 KV", "765 KV").

A programmatic pull (for later hourly LMP work) goes through the same feed IDs via the
subscription-keyed PJM API (`apiportal.pjm.com`) — not used here per the task's
web-research-only constraint; the browser-based table above is sufficient to name and locate
candidates without touching any metered API.

**Zone aggregate nodes** also exist as first-class pnodes — e.g. the very first rows of the
unfiltered pnode table include `PJM-RTO` (id 1) and `MID-ATL/APS` (id 3), both tagged
Type=AGGREGATE, SubType=ZONE. So a pure APS-zone-average control is directly queryable by
name if you want the zone-aggregate route (see §4).

Monitoring Analytics' quarterly State of the Market reports (e.g.
[2011 Q2](http://www.monitoringanalytics.com/reports/pjm_state_of_the_market/2011/2011q2-som-pjm-sec7.pdf))
are the standing source for which interfaces/constraints bind most often — useful for a
periodic re-check of whether AP South, the AEP–Dominion interface, or a new WV/PA/OH
interface has started coupling any of these candidate buses to DOM.

---

## 4. Hub vs. zone-aggregate vs. physical bus

**Physical EHV bus (recommended primary choice for this use case).** A single named
500/765 kV bus's LMP decomposes cleanly into system energy + congestion + losses at *that
specific point* — directly comparable in kind to how LOUDOUN/PLEASANTVIEW/GOOSECRE/SKFFSCRK
are used in the existing panels. This is the only option that isolates a genuine congestion
component rather than an average of many.

**Zone aggregate (e.g. "MID-ATL/APS", "DAY", "AEP").** These are Type=AGGREGATE,
SubType=ZONE pnodes — a load-weighted average across all buses in the zone. Reasonable as a
**secondary/robustness check**, not a primary instrument: averaging smears together buses
that are near a new data-center interconnection with buses that aren't, diluting exactly the
congestion signal you're trying to isolate. Useful mainly to sanity-check that a chosen
physical bus isn't a weird outlier relative to its own zone.

**Financial hub (e.g. WESTERN HUB, AEP-DAYTON HUB) — not recommended.** PJM's `agg_definitions`
feed (`https://dataminer2.pjm.com/feed/agg_definitions/definition`) confirms the mechanism:
hubs are Fixed Weighted Average Aggregates — an "Aggregate Pnode" defined as a weighted sum
of dozens of individual "BUS Pnode" rows, each with its own factor. That structure is
consistent with (though I could not pull the live WESTERN HUB row list within this session's
tool budget — the UI's default sort didn't surface it and further form automation was out of
scope) a secondary-sourced claim that **Western Hub's 89 constituent buses sit in only five
zones — PENELEC (49), PEPCO (33), BGE, METED, and DOM** — with zero AEP or DAY
representation.
[Kyber Energy, "The Western Hub Illusion"](https://kyberenergy.substack.com/p/the-western-hub-illusion)
**Treat this as moderate-confidence, single-source, structurally plausible — not
independently verified against the authoritative feed. If Western Hub really does contain
DOM buses, it is disqualified outright as a "distant from DOM" control by construction.**
Regardless of that specific composition question, hubs are designed by PJM to be
*price-stable and low-congestion-sensitivity by selection criteria* — the opposite of what
you want when the comparison object is the congestion component itself. AEP-DAYTON HUB's
exact composition was not pulled this session (would need the same live-filtered query
against `agg_definitions` for Aggregate Pnode Name = "AEP-DAYTON HUB"); recommend doing that
before using it, for the same reason.

**Bottom line: physical EHV bus as primary control, zone aggregate as an optional robustness
cross-check, hub nodes disqualified/deprioritized for this comparison.**

---

## 5. Sources

- [PJM 2026/2027 BRA Report (PDF)](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-report.pdf)
- [PJM 2025/2026 BRA Report (PDF)](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/2025-2026-base-residual-auction-report.pdf)
- [Utility Dive — PJM capacity prices set another record with 22% jump](https://www.utilitydive.com/news/pjm-interconnection-capacity-auction-prices/753798/)
- [Utility Dive — PJM capacity prices hit price cap, reserve shortfall grows](https://www.utilitydive.com/news/pjm-capacity-auction-price-cap-reserve-shortfall/825282/)
- [PJM Data Miner 2 — Pricing Nodes feed](https://dataminer2.pjm.com/feed/pnode) / [definition](https://dataminer2.pjm.com/feed/pnode/definition)
- [PJM Data Miner 2 — Fixed Weighted Average Aggregate Definitions](https://dataminer2.pjm.com/feed/agg_definitions/definition)
- [Kyber Energy — The Western Hub Illusion](https://kyberenergy.substack.com/p/the-western-hub-illusion)
- [Monitoring Analytics — 2011 Q2 State of the Market, PJM (interfaces/constraints)](http://www.monitoringanalytics.com/reports/pjm_state_of_the_market/2011/2011q2-som-pjm-sec7.pdf)
- [PJM White Paper — Transource/Independence Energy Connection (AP South context)](https://www.pjm.com/-/media/DotCom/committees-groups/committees/teac/20181108/20181108-transource-white-paper.ashx)
- [Dominion Post — FirstEnergy's planned gas-fired plant and Fort Martin, June 2026](https://www.dominionpost.com/2026/06/03/a-look-at-firstenergys-planned-gas-fired-plant-and-fort-martin/)
- [Utility Dive — FirstEnergy data center contracts surge 50% in Q2 (Maidsville, WV)](https://www.utilitydive.com/news/firstenergy-data-center-west-virginia-maidsville-earnings/826558/)
- [West Virginia Watch — $4B Berkeley County (Bedington) data center campus, Feb 2026](https://westvirginiawatch.com/2026/02/26/d-c-based-real-estate-firm-investing-4b-for-new-data-center-development-in-berkeley-county-wv/)
- [WV Gazette-Mail — Mason County Monarch data center operational 2027](https://www.wvgazettemail.com/business/construction-weeks-away-mason-county-data-center-operational-in-early-2027-builder/article_0edb4165-114e-4b92-ba1c-9acbdd240893.html)
- [DataCenterDynamics — Nscale acquires 8GW Monarch Compute Campus, Microsoft 1.35GW](https://www.datacenterdynamics.com/en/news/nscale-acquires-8gw-monarch-compute-campus-microsoft-signs-on-for-135gw-of-compute/)
- [Blackridge Research — Upcoming Data Centers in Pennsylvania 2026 (Homer City)](https://www.blackridgeresearch.com/blog/latest-list-of-upcoming-data-centers-in-pennsylvania-pa-united-states-us)
- [Spotlight PA — New power plants for data centers would worsen pollution, July 2026](https://www.spotlightpa.org/news/2026/07/pennsylvania-data-centers-emissions-gas-plants-climate-environment/)
- [Data Center Frontier — Data Centers Are Booming In Ohio's Digital Heartland](https://www.datacenterfrontier.com/site-selection/article/33035576/data-centers-are-booming-in-ohios-digital-heartland)
- [Utility Dive — Indiana Michigan Power / AEP / Amazon / Google / Microsoft large-load interconnection rules](https://www.utilitydive.com/news/indiana-michigan-power-aep-amazon-google-microsoft-data-center-interconnect/733850/)
- [Kentucky Living — Data centers will come to Kentucky; EKPC is prepared](https://www.kentuckyliving.com/news/data-centers-will-come-to-kentucky-ekpc-is-prepared)
