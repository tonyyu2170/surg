# Loudoun/Skiffes Creek geography research — Aug 7, 2026

Research thread for PJM/Dominion pricing-node study (GOOSECRE, LOUDOUN, PLEASANTVIEW, SKFFSCRK).
Web research only, no repo changes.

---

## 0. Headline finding — read this first

**The "Goose Creek Substation" (east of Leesburg, Loudoun County) — almost certainly the
transmission facility behind the GOOSECRE pricing node — is not a generic node inside the
Data Center Alley cluster. It is the confirmed southern/eastern terminus of two separate,
concurrent bulk-transmission builds designed specifically to relieve NoVA data-center
congestion:**

1. **MARL / Gore-Doubs-Goose Creek** (PJM B3800 baseline reliability project, ~$5B,
   approved by the PJM Board Dec 11, 2023): a ~500-kV import corridor running from
   Greene County, PA, through WV, to Gore, VA (NextEra's "MARL" segment), then continuing
   as the "Gore-Doubs-Goose Creek Improvements Project" (Potomac Edison/FirstEnergy) through
   Frederick County VA, Jefferson County WV, and Loudoun County VA, **terminating at
   Dominion's Goose Creek Substation**. Target in-service ~2029–2031 (dates vary by source;
   see §2).
2. **Line 514 Corridor Upgrade** (separate, older Dominion project): upgrades the existing
   3.5-mile 500kV + double-circuit 230kV corridor running from the Potomac River south to
   the Goose Creek substation — i.e., Goose Creek is already the terminus of Dominion's
   existing northern import path, independent of MARL.

Practically: within our study horizon, the substation feeding GOOSECRE is the designated
landing point for a multi-billion-dollar new import corridor that will materially change
its transmission topology (2027–2031 construction window). If the paper frames GOOSECRE as
a passive/comparison node relative to LOUDOUN/PLEASANTVIEW, that framing should be revisited —
it is arguably the most transmission-strategic of the four nodes going forward, not a lesser
one. This is separate and distinct from Dominion's local "reliability loop"
(Aspen–Golden–Mars–Twin Creeks/Apollo) in eastern Loudoun/Ashburn — different substations,
same underlying driver (data center load).

No comparable finding for SKFFSCRK: it remains a transmission-pass-through node (nuclear
generation injection + Hampton Roads Peninsula reliability), with no data-center-specific
development identified at the switching station itself. See §3.

---

## 1. Loudoun County zoning/permitting, 2025–2026

**By-right elimination (locked in, not prospective):**
- March 18, 2025: Loudoun Board of Supervisors approved a Comprehensive Plan Amendment
  (CPAM) + Zoning Ordinance Amendment (ZOAM) eliminating **by-right** data center
  development. Data centers now require a **special exception**: legislative review + public
  hearings before the Planning Commission and Board of Supervisors.
  [Holland & Knight](https://www.hklaw.com/en/insights/publications/2025/04/loudoun-county-virginia-eliminates-by-right-data-center-development) ·
  [LoudounNow](https://www.loudounnow.com/news/by-right-data-centers-eliminated-in-loudoun-existing-applications-grandfathered/article_130515be-0478-11f0-ab4f-7771b6b47f71.html)
- Grandfathering: applications already under review as of **Feb 12, 2025** are exempt from
  the new special-exception requirement.
- **Phase 2** (in progress): county staff researching/drafting standards for data centers,
  substations, microgrids, generators — research/drafting Oct 2025–Apr 2026, public
  engagement Apr–Jun 2026.
  [Loudoun County Phase 2 page](https://www.loudoun.gov/6222/Phase-2-Data-Center-Standards-Locations)

**Moratorium push (new, as of late July 2026 — not yet enacted):**
- July 22, 2026: Board voted 6-1 (motion by Supervisor Juli Briskman) to direct staff to
  draft a plan for pausing **all** new data center applications, site plans, and substation
  permits until Phase 2 concludes.
- Legal uncertainty flagged: county attorney to research whether VA law permits a blanket
  moratorium, since state law requires each rezoning/special-exception application be
  considered on its merits.
- Staff to bring the pause item to the **Sept 15, 2026** board meeting.
- Framing from Briskman: county has become "fiscally over reliant" on data centers; residents
  cite grid strain, noise, diesel generator emissions, neighborhood transformation.
- Loudoun now has **over 250** operating data centers per this reporting.
- Other VA localities moving in parallel: **Suffolk** (temporary pause on new applications,
  reviewing regs), **Front Royal** (drafting a full ban across all zoning districts),
  **Chesapeake** (voted to delay application review 8 months).
  [Virginia Mercury, Jul 30, 2026](https://virginiamercury.com/2026/07/30/loudoun-county-other-virginia-localities-consider-hitting-the-brakes-on-data-center-development/) ·
  [WTOP](https://wtop.com/loudoun-county/2026/07/loudoun-county-other-virginia-localities-consider-hitting-the-brakes-on-data-center-development/) ·
  [DCD on a rejected 3.25M sq ft campus](https://www.datacenterdynamics.com/en/news/loudoun-county-considering-moratorium-on-new-data-center-applications-rejects-325-million-sq-ft-campus/) ·
  [MLQ News on a rejected 780MW campus](https://mlq.ai/news/loudoun-county-moves-toward-data-center-moratorium-rejects-780mw-active-infrastructure-campus/)

**Inventory / pipeline (2026):**
- Current: ~**46 million sq ft** constructed or permitted, plus another **8–10 million sq ft**
  under active construction.
- Pipeline: **61.5 million sq ft** of potential future development — a large share of that
  is grandfathered under the pre-ZOAM by-right rules even though construction hasn't started.
- 2026-specific projects cited: AWS building 3 new Loudoun facilities (~1.2M sq ft,
  ~180MW at full buildout, construction through 2028); Google expanding with 2 new buildings
  (~600,000 sq ft, ~90MW).
- Regional context: Northern Virginia ended 2025 with **4,039.6 MW** of data center inventory.
  [MotionCRE 2026 Market Brief](https://motioncre.com/resources/data-center-development-northern-virginia)
  (secondary/aggregator source — treat MW/sq-ft figures as directional, not authoritative;
  cross-check against CBRE/JLL primary reports if these numbers get used quantitatively).
- Older baseline for comparison: as of Nov 2024, Loudoun had ~30M sq ft built + 5M sq ft in
  development (DCD, citing CBRE H1 2024 data: NoVA at 2,611.1 MW inventory,
  1,157 MW under construction).
  [DCD, "The future of Virginia post-Loudoun," Nov 4 2024](https://www.datacenterdynamics.com/en/analysis/the-future-of-virginia-post-loudoun/)

---

## 2. MARL / Gore-Doubs-Goose Creek (PJM B3800)

**Structure:** One continuous ~500-kV transmission corridor split into two utility-owned
segments under PJM project series **B3800** (~$5B combined, ~220 projects, approved by PJM
Board Dec 11, 2023) to import bulk power into NoVA for data center load:

| Segment | Developer | Route | Length |
|---|---|---|---|
| MARL (Mid-Atlantic Resiliency Link) | NextEra Energy Transmission MidAtlantic | Greene County, PA → WV (Monongalia, Preston, Mineral, Hampshire counties) → handoff at Gore, Frederick County, VA | ~107.5 mi |
| Gore-Doubs-Goose Creek Improvements | Potomac Edison (FirstEnergy) | Gore, VA → Frederick Co VA (17.9 mi) → Clarke Co MD (0.2 mi — likely a data/labeling artifact, see caveat) → Jefferson Co WV (15.4 mi) → Loudoun Co VA (10.5 mi) → **Goose Creek Substation, Eastern Loudoun County** | ~44 mi (upgrading existing 138kV ROW to double-circuit 500kV/138kV) |

Caveat: source county/mileage breakdowns for Gore-Doubs-Goose Creek were inconsistent across
outlets (a Dominion Post summary lists "Clarke County, Maryland" which is very likely a
transcription error — Clarke County is in VA; Frederick and Montgomery counties are the MD
segment per the MD PSC filing, see below). Use the MD PSC case filing as the authoritative
route source if this matters for the paper.

**Endpoint confirmation:** Multiple independent sources (FirstEnergy project fact sheet,
stopmarlvirginia.com FAQ, Loudoun Wildlife Conservancy) confirm the line terminates at
**Dominion's Goose Creek Substation**, located on the east side of Leesburg, Loudoun County —
an existing 500kV/230kV facility that is also the terminus of Dominion's separate Line 514
corridor upgrade (Potomac River → Goose Creek, 3.5 mi).
[FirstEnergy fact sheet](https://www.firstenergycorp.com/content/dam/corporate/transmission/gore-doubs-goose-creek-va-wv-fact-sheet.pdf) ·
[stopmarlvirginia.com FAQs](https://stopmarlvirginia.com/faqs) ·
[Loudoun Wildlife Conservancy](https://loudounwildlife.org/2024/08/energy-infrastructure-goose-creek/) ·
[Dominion Line 514 project page](https://www.dominionenergy.com/about/delivering-energy/electric-projects/power-line-projects/line-514)

**State case status (as of Aug 2026):**

- **Virginia SCC** — MARL (NextEra's VA-adjacent filing): docket **PUR-2026-00018**.
  Hearing-examiner procedural schedule set; intervention deadline June 8, 2026.
  [nvdaily coverage](https://www.nvdaily.com/nvdaily/application-filed-in-virginia-for-marl-transmission-line/article_d800080a-73e7-5aa9-8bff-47b00c63246c.html)
  — I did not find a separately confirmed VA SCC docket number specifically for Potomac
  Edison/Dominion's Gore-Doubs-Goose Creek VA leg; it may be filed under the same or an
  adjacent case. Worth a direct SCC docket search if the case number matters.
- **West Virginia PSC** — MARL: **Case No. 26-0075-E-CN**. Evidentiary hearing scheduled
  **Oct 26–30 and Nov 2, 2026**, Charleston. ~180 petitions to intervene as of July 2026.
  PSC decision due **March 9, 2027** (one Dominion Post piece says March 6, 2027 — treat as
  ~early March 2027). Estimated project cost ~$960M for the WV/MARL portion.
  [WV MetroNews](https://wvmetronews.com/2026/06/15/evidentiary-hearing-next-up-for-marl-project/) ·
  [Dominion Post](https://www.dominionpost.com/2026/07/08/psc-staff-makes-recommendations-for-upcoming-marl-hearing-in-charleston/)
- **Maryland PSC** — Gore-Doubs-Goose Creek: **Case No. 9870**. Covers ~18 miles of upgrades
  in Frederick and Montgomery counties, MD, using existing corridors. Potomac Edison
  requested a schedule allowing a final CPCN order by **Dec 20, 2027**.
  [MD PSC CPCN case filing](https://img1.wsimg.com/blobby/go/bae620d5-257a-40da-a168-d7df3fda5122/MD_9870_Gore-Doubs-Goose_CPCN_Application.pdf)
- **Pennsylvania PUC** — **Case # A-2026-3060856**. Order issued setting protest/intervention
  procedure per 52 Pa. Code (covers the PA portion of MARL, Greene/Fayette counties).

**In-service dates:** Estimates vary by source and haven't fully converged:
- Dominion Post (Sept 2025): Gore-Doubs-Goose Creek "estimated completion 2029–2030."
- Another aggregator figure: construction starting 2027/2028, completion 2031.
- stopmarlvirginia.com states "PJM has already moved the in-service date for MARL by three
  years" (i.e., slipped from an earlier target) without giving the current number.
- **Working range to use: construction ~2027–2029, in-service ~2029–2031.** Treat any single
  precise date in secondary sources with caution; the WV PSC decision (March 2027) and VA SCC
  case (still in intervention phase) haven't even concluded siting yet.

**New context — Dominion/NextEra merger:** NextEra Energy and Dominion Energy announced a
merger (~$67B, per most consistent reporting — one search result implied a much larger
headline "$600B" figure that looks like it conflated combined enterprise value/customer
scale rather than deal price; treat $67B as the more reliable figure) around **May 2026**.
Reporting explicitly states the **MARL project is not expected to be affected** by the merger.
Sen. Angus King has urged FERC to reject the merger; **Sen./Gov.-elect Abigail Spanberger
intervened in the merger review as of Aug 6, 2026** (Virginia Mercury). Since NextEra and
Dominion are the two utilities co-developing MARL/Gore-Doubs-Goose Creek, this merger is
worth monitoring as a source of schedule/ownership risk even though current reporting says
"no impact."
[WAJR, May 19 2026](https://wajr.com/2026/05/19/nextera-energy-to-merge-with-dominion-energy-marl-project-not-affected/) ·
[Virginia Mercury, Aug 6 2026](https://virginiamercury.com/2026/08/06/spanberger-takes-unprecedented-step-to-intervene-in-67b-dominion-nextera-merger/)

---

## 3. Skiffes Creek

**What's physically there:** The **Surry–Skiffes Creek–Whealton** transmission project —
energized **Feb 26, 2019**. Consists of:
- 7.76-mile 500kV overhead line from Surry (nuclear) Power Station across the **James River**
  to a new **Skiffes Creek switching station** (500kV/230kV/115kV, 51 acres) in eastern
  James City County.
- 20.2-mile 230kV line from the switching station to the existing Whealton substation in
  Hampton.
- VA SCC docket: **PUE-2012-00029**.
- Purpose: replace generation lost from the retirement of Yorktown coal/oil units and shore
  up reliability for the Hampton Roads Peninsula (600,000+ people); this was also a highly
  contested project (James River crossing near Jamestown/Captain John Smith Historic Trail —
  litigation went to the VA Supreme Court, upheld April 2015).
  [Dominion Energy project page](https://www.dominionenergy.com/skiffescreek) ·
  [Permitting Dashboard](https://www.permits.performance.gov/permitting-project/other-projects/surry-skiffes-creek-whealton-aerial-transmission-line)

**Data center activity near Skiffes Creek, 2024–2026:** I found **no evidence of any data
center sited at or immediately around the Skiffes Creek switching station itself**. What I
did find, at the broader James City County level (not Skiffes Creek specifically):
- Sept 2025: JCC Board of Supervisors approved zoning ordinance updates restricting data
  centers to industrial districts, with permits required.
- Nov 2025: JCC adopted a data center policy requiring **≥1,000 ft from residences** and
  **≥250 ft from historic/recreational/environmentally sensitive areas**, and limiting
  water/energy consumption.
- The county is further amending ordinances in response to 2026 Virginia legislation on
  data center sound assessments, among other topics.
  [WHRO, Sept 10 2025](https://www.whro.org/local-government/2025-09-10/james-city-county-is-the-latest-virginia-county-to-regulate-data-centers) ·
  [WHRO, Nov 13 2025](https://www.whro.org/local-government/2025-11-13/james-city-county-data-center-policy-limits-water-and-energy-consumption-proximity-to-homes)
- Tangential: an Irish data-center **power-infrastructure manufacturer** (not a data center
  operator) is opening its first U.S. plant in James City County (~$5.2M investment, 250
  jobs) — a supply-chain investment, not a data center campus, and not tied to a Skiffes
  Creek location specifically.
  [Virginia Business](https://virginiabusiness.com/irish-data-center-power-manufacturer-virginia/)

**Read for the study:** James City County as a whole is now writing data-center zoning
rules, which signals some developer interest in the county — but there's no evidence that
interest is concentrated at or near the Skiffes Creek switching station, which remains
functionally a nuclear-generation injection point + Peninsula reliability node, not a
load-growth node. This is consistent with (does not overturn) treating SKFFSCRK as a
geographically/functionally rural comparison node, though it's not a "no development
anywhere nearby" claim — just no development *at Skiffes Creek*.

---

## 4. Dominion transmission projects in/near Loudoun, 2025–2026

All of these sit within Dominion's "eastern Loudoun reliability loop," distinct from the
MARL/Goose Creek bulk-import corridor in §2 — different substations, same underlying driver
(NoVA data center demand).

**Aspen to Golden** — SCC-approved, litigation resolved:
- 9.4 miles of 230kV/500kV double-circuit line on monopole towers along Rt. 7, eastern
  Loudoun. Connects two new substations: **Aspen** (near Philip A. Bolen Memorial Park,
  south of Leesburg) and **Golden** (west of Sterling).
- VA SCC issued its Final Order approving the project **Feb 5, 2025**.
- Loudoun County + Lansdowne Conservancy appealed to the VA Supreme Court.
- **Feb 19, 2026: VA Supreme Court affirmed the SCC's approval** — project proceeds.
  [LoudounNow](https://www.loudounnow.com/news/supreme-court-upholds-overhead-aspen-to-golden-power-lines/article_075e7437-6fee-4e7c-a4de-c053d878e73d.html) ·
  [SCC environmental review doc](https://www.scc.virginia.gov/media/sccvirginiagov-home/consumer-home/public-utilities/electricity/transmission-line-projects/dev-240032-aspengolden.pdf)

**Golden to Mars** — SCC-approved, route contested/litigated in 2026:
- ~9-mile 500kV/230kV line connecting the new Golden substation to a new **Mars** substation
  in eastern Loudoun. Part of the same 3-pronged "reliability loop" as Twin Creeks–Apollo and
  Aspen–Golden, funneling power to the Ashburn data-center cluster.
- VA SCC docket: **PUR-2025-00056**. Final Order issued **June 29, 2026**, selecting Route 3A
  (through/near residential subdivisions — heavily contested; SCC denied Loudoun County's
  request to delay and denied undergrounding).
  [Virginia Mercury, Apr 10 2026](https://virginiamercury.com/2026/04/10/scc-approves-loudoun-transmission-line-nixes-undergrounding-final-route-to-be-determined/) ·
  [WTOP, Jul 2026](https://wtop.com/loudoun-county/2026/07/whats-the-fate-of-loudouns-controversial-golden-to-mars-transmission-line/) ·
  [wjla](https://wjla.com/news/local/loudoun-county-homeowners-appear-to-lose-battle-with-dominion-energy-data-center-transmission-lines-state-corporation-commission-july-2026)

**Twin Creeks to Apollo** — bundled with Aspen–Golden in Dominion's filing:
- SCC application submitted **March 7, 2024**; public hearing **Sept 5, 2024**. I did not
  dig up a separate final-order date for this specific segment in this pass — flag for
  follow-up if Twin Creeks–Apollo timing specifically matters.
  [Loudoun Wildlife Conservancy summary](https://loudounwildlife.org/2024/08/energy-infrastructure-goose-creek/)

**Line 514 Corridor Upgrade** — separate from the reliability loop, feeds Goose Creek:
- Upgrades an existing corridor from the Potomac River south ~3.5 miles to the **Goose Creek
  substation**, replacing lattice/monopole structures to support existing 500kV + 230kV lines
  plus additional capacity. This is the corridor MARL will eventually tie into at Goose Creek
  (see §0/§2).
  [Dominion Line 514 project page](https://www.dominionenergy.com/about/delivering-energy/electric-projects/power-line-projects/line-514)

---

## Sources index (all URLs cited above, deduplicated)

- https://www.hklaw.com/en/insights/publications/2025/04/loudoun-county-virginia-eliminates-by-right-data-center-development
- https://www.loudounnow.com/news/by-right-data-centers-eliminated-in-loudoun-existing-applications-grandfathered/article_130515be-0478-11f0-ab4f-7771b6b47f71.html
- https://www.loudoun.gov/6222/Phase-2-Data-Center-Standards-Locations
- https://virginiamercury.com/2026/07/30/loudoun-county-other-virginia-localities-consider-hitting-the-brakes-on-data-center-development/
- https://wtop.com/loudoun-county/2026/07/loudoun-county-other-virginia-localities-consider-hitting-the-brakes-on-data-center-development/
- https://www.datacenterdynamics.com/en/news/loudoun-county-considering-moratorium-on-new-data-center-applications-rejects-325-million-sq-ft-campus/
- https://mlq.ai/news/loudoun-county-moves-toward-data-center-moratorium-rejects-780mw-active-infrastructure-campus/
- https://motioncre.com/resources/data-center-development-northern-virginia
- https://www.datacenterdynamics.com/en/analysis/the-future-of-virginia-post-loudoun/
- https://www.firstenergycorp.com/content/dam/corporate/transmission/gore-doubs-goose-creek-va-wv-fact-sheet.pdf
- https://stopmarlvirginia.com/faqs
- https://loudounwildlife.org/2024/08/energy-infrastructure-goose-creek/
- https://www.dominionenergy.com/about/delivering-energy/electric-projects/power-line-projects/line-514
- https://www.nvdaily.com/nvdaily/application-filed-in-virginia-for-marl-transmission-line/article_d800080a-73e7-5aa9-8bff-47b00c63246c.html
- https://wvmetronews.com/2026/06/15/evidentiary-hearing-next-up-for-marl-project/
- https://www.dominionpost.com/2026/07/08/psc-staff-makes-recommendations-for-upcoming-marl-hearing-in-charleston/
- https://img1.wsimg.com/blobby/go/bae620d5-257a-40da-a168-d7df3fda5122/MD_9870_Gore-Doubs-Goose_CPCN_Application.pdf
- https://www.dominionpost.com/2025/09/13/a-look-at-marl-and-pjms-b3800-project-series/
- https://wajr.com/2026/05/19/nextera-energy-to-merge-with-dominion-energy-marl-project-not-affected/
- https://virginiamercury.com/2026/08/06/spanberger-takes-unprecedented-step-to-intervene-in-67b-dominion-nextera-merger/
- https://www.dominionenergy.com/skiffescreek
- https://www.permits.performance.gov/permitting-project/other-projects/surry-skiffes-creek-whealton-aerial-transmission-line
- https://www.whro.org/local-government/2025-09-10/james-city-county-is-the-latest-virginia-county-to-regulate-data-centers
- https://www.whro.org/local-government/2025-11-13/james-city-county-data-center-policy-limits-water-and-energy-consumption-proximity-to-homes
- https://virginiabusiness.com/irish-data-center-power-manufacturer-virginia/
- https://www.loudounnow.com/news/supreme-court-upholds-overhead-aspen-to-golden-power-lines/article_075e7437-6fee-4e7c-a4de-c053d878e73d.html
- https://www.scc.virginia.gov/media/sccvirginiagov-home/consumer-home/public-utilities/electricity/transmission-line-projects/dev-240032-aspengolden.pdf
- https://virginiamercury.com/2026/04/10/scc-approves-loudoun-transmission-line-nixes-undergrounding-final-route-to-be-determined/
- https://wtop.com/loudoun-county/2026/07/whats-the-fate-of-loudouns-controversial-golden-to-mars-transmission-line/
- https://wjla.com/news/local/loudoun-county-homeowners-appear-to-lose-battle-with-dominion-energy-data-center-transmission-lines-state-corporation-commission-july-2026

---

## Gaps / things I did not confirm

- No confirmed distinct VA SCC docket number for the Gore-Doubs-Goose Creek VA-side filing
  (separate from NextEra's PUR-2026-00018); worth a direct SCC docket-search pass if the
  case number is needed.
- Twin Creeks–Apollo final-order date not found in this pass.
- Precise MARL/Gore-Doubs-Goose Creek in-service date not fully converged across sources
  (range given: 2029–2031); if the paper needs a single number, go to the PJM RTEP/B3800
  project tracker directly rather than secondary press.
- Did not independently verify that "Goose Creek Substation" is the exact PJM pricing-node
  location for GOOSECRE (inferred from name match + Loudoun County location + Dominion
  ownership; the substation is real, well-documented, and geographically consistent with
  the study's GOOSECRE description, but I did not cross-reference a PJM pnode map).
