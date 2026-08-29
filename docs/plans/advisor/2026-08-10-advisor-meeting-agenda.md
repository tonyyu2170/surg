# Advisor Meeting Agenda — 2026-08-10

## Current Status

- The parallel cross-market analysis I mentioned last time ("maybe compare against SPP / ERCOT / CAISO") is now an **eight-market comparison, all run**: DOM/PJM, ERCOT, NYISO, CAISO, IESO (Ontario), MISO, ISO-NE, and SPP  
- Spent more time looking at ERCOT in particular  
- More external research on tech/policy  
- Core data limitation is unchanged everywhere: all load series are metered regional aggregates, no node level or facility-level data

## Findings This Week

### Parallel analysis across eight electricity markets

The same diagnostic — does hourly/5-min price track load *level* or load *volatility* — now runs in eight independently governed markets, each with a very different data-center story:

- **PJM / Dominion (Virginia)** — home market. NoVA data center inventory ended 2025 at \~4,040 MW across 600–700 facilities; Dominion has \~70 GW of new interconnection requests on file (\~3× its entire current system peak). DOM's own load is growing at **\+6.5%/yr**, vs. \+1.6%/yr RTO-wide average — by far the fastest-growing zone in PJM. This is the "treatment" market.  
- **ERCOT (\~90% of Texas)** — data centers \+ crypto mining combined ("large flexible load") totaled **54 TWh in 2025, \~11% of ERCOT's system consumption**, and the interconnection queue is exploding on paper (21.7 GW tracked for 2026 growing to 238 GW by 2030\) but *observed, energized* load is flat around 5,768 MW through 2030 — almost all of the queue is speculative. Level still beats volatility in 132/135 zone–price pairs tested.  
- **NYISO (New York state)** — a near-control market. No hyperscale boom; the closest things are a small upstate crypto cluster (Greenidge) and the Micron Clay chip fab, which is semiconductor manufacturing, not a data center, despite being \~6 GW-scale. Load has actually been *falling* over the multi-decade window. Level still wins 97–100% of pairs.  
- **CAISO (most of California; municipal utilities like Silicon Valley Power and LADWP are excluded by construction)** — explicitly "the legacy data-center state, not the growth story": only **\+1.8 GW of new DC load projected by 2030** (system peak forecast 48 GW → \~68 GW by 2040, driven partly by DCs but an order of magnitude below MISO). The existing Silicon Valley cluster in Santa Clara is invisible to this panel because it's served by a municipal utility outside CAISO. Level wins 92–100% of pairs.  
- **IESO (Ontario, Canada)** — an EV-driven growth story, not a data-center one: data centers \+ other new demand combined reach \~8.6% of Ontario demand by 2050, but EVs are more than half of that new growth margin, and IESO's own planning language calls data-center materialization "uncertain." Level wins 100% of pairs.  
- **MISO (Midatlantic: Arkansas, Illinois, Indiana, Iowa, Kentucky, Louisiana, MichiganMinnesota, Mississippi, Missouri, Montana, North Dakota, South Dakota)** — the biggest projected growth story of any market here: its own long-term forecast has data centers going from 9.6 to 266 TWh by 2046, a 28-fold increase, more than every other load-growth driver combined. It even has a pricing node literally named `GRE.REC.DATA`. Load is compounding at **\+1.9%/yr**, the fastest of the three new markets. Level wins **36/36 pairs**.  
- **SPP (Southwest: Kansas, Oklahoma, Nebraska)** — the most aggressively pro-data-center *policy* posture: a dedicated High Impact Large Load program promising interconnection agreements within 90 days, anchored by Google's Pryor, OK campus, and SPP anticipates a near-doubling of peak load within ten years. Load compounding at **\+1.4%/yr**. Level wins **289/289 pairs** — the largest single panel in the project (17 control zones).  
- **ISO-NE (New England)** — added deliberately as the **designated control**. The ISO's own May-2026 words: New England "has not experienced similar growth so far, and only a small amount is expected in the coming decade." There is no hyperscale campus operating in-region in our window. Load is *falling*, −0.6%/yr. **Level wins 64/64 pairs — and with a higher median R² (0.274) than most of the markets that do have data centers.**

Weirdly ISONE was the only zone with somewhat volatile load

* I think due to not as much data center growth, especially in vermont & maine  
* Infrastructure isn’t being heavily invested in

### ERCOT-specific data center data: confirmed there is no public source

Followed up specifically on ERCOT/Texas this week, including the UT Austin lead. Conclusion: **no facility-level or even sub-population data-center data source exists publicly for ERCOT**, verified rather than assumed:

- Checked the **UT Austin** lead (Bureau of Economic Geology's "TRAIL Map" data-center program).  
  - It's real, but it's a narrative policy white paper, not a data release.   
  - They partner with data centers to “research and facilitate the sustainable growth of data centers in Texas.”  
  - Not sure if they have specific data but maybe could email  
- Couldn’t find any other thing related to “UT data center energy load dataset”

### External research this week: technology and grid context

- **Behind-the-meter co-location is a live, unsettled FERC (federal energy regulatory commission) fight.** FERC's Dec. 2025 order told PJM its co-location tariff was unlawful; PJM's compliance filings have been rejected twice since (April and June 2026\) for issues including how much behind-the-meter generation gets "netted" against load. This matters for us directly: netted BTM generation is invisible in the metered load data we use, so future co-located data centers could decouple observed load from true consumption.  
  - Opposing utilities argued that tapping power directly behind-the-meter lets large tech loads avoid fair transmission costs, potentially forcing standard consumers to absorb up to $140 million a year in grid upkeep  
  - FERC declared PJM Interconnection's old rules unjust, ordering grid operators to craft specific new transmission service categories and rewrite outdated behind-the-meter generation netting standard  
  - Right now rule is max 50MW without paying for transmission charges  
  - Developers like Talen Energy took legal action,  
- **Nuclear/SMR co-location has crossed 9.8 GW of committed capacity** for data centers nationally: Microsoft's restart of Three Mile Island Unit 1 (first power expected H2 2027), Amazon's $700M into X-energy SMRs, Google's 500 MW deal with Kairos, Meta's 6.6 GW across several developers. The genuinely "nano" end of this is **microreactors** — Aalo is targeting criticality for its first reactor in July 2026 and has 30 microreactors planned for a site in Haskell County, TX (inside ERCOT). Dominion itself is "actively exploring" SMRs.  
- **Nvidia/Span's residential mini-data-center program (XFRA: [https://www.xfra.ai/](https://www.xfra.ai/))** puts small liquid-cooled server boxes in new houses, using idle residential electrical capacity that homebuilder PulteGroup is piloting at \~100 homes this year. Interesting as a dispersal trend — pulls some future AI load *away* from the transmission-scale congestion pockets we study.

### CRS (congress research service) report — "Data Centers and Their Energy Consumption: Frequently Asked Questions" (R48646)

The Congressional Research Service report you sent (updated May 2026):

- **The most useful finding for us is a genuine surprise: CRS's own analysis did not find data centers to be a major driver of electricity prices in most of the country between 2019 and 2025 — states with the largest data-center demand growth generally saw prices *decrease* over that period**, plausibly because the added demand let utilities spread fixed costs over more sales. This is the opposite of the "data centers raise your bill" framing the proposal started from.  
- The report immediately qualifies that finding in exactly the direction our project's data points: **"areas of the country with grid constraints due to insufficient infrastructure are more likely to experience rate increases from new data center demand."** That's a national-level statement of precisely the DOM story — it's not data centers per se, it's data centers landing in an already-congested, import-constrained zone.  
- Data collection is weak and contested: A 2021 EIA (Energy Information Administration) pilot survey got only 9 responses from 50 facilities; a 2024 EIA attempt to survey cryptomining data centers was halted after a lawsuit forced EIA to destroy collected data.  
- Policy landscape: no binding federal energy standards for data centers today. A pending bill (Clean Cloud Act of 2025, S. 1475\) would give EPA (Environment protection agency) /EIA authority to collect data-center energy data — notable because facility-level data unavailability is the recurring obstacle across every market I've checked (DOM, ERCOT, and implicitly the rest). At the state/utility level, CRS notes a rising trend of utilities creating separate rate classes for large data-center customers — which matches Virginia's own GS-5 rate class already in our research notes.

## Things I Need Advice On

1. **What do i do now lol the data quite literally is hidden even from the US government**  
2. **If behind the meter really takes off energy volatility, the whole point of my report, is flattened. Infrastructure will keep up and consumers wont face outages**  
3. **Is the ERCOT dead-end worth a UT Austin research-access request?** 

## Future Direction

- Optional UT Austin outreach  
- Try reverse engineering data center load from the pricing?

## Notes from meeting

* One possible conclusion for this project is that data centers are effectively mitigating the fluctuation, but baseline energy usage is still extremely high?
* Texas data set: [https://www.pecanstreet.org/2025/10/waveform-release/](https://www.pecanstreet.org/2025/10/waveform-release/)  
* Look into new england fluctuation
  * Is it caused by new england's connection to Canada's grid?
  * One possible hypothesis is that if it is connected, then Canada's renewable energy generation could be a source of this fluctuation. Otherwise it also wouldn't surprise me if this was weather driven.
* Look into FERC
  * Where does this 50 MW limit come from? Why this number speciically?
  * Why would transmission costs fall onto the burden of homeowners if behind the meter takes off? Wouldn't the cost of transmission for these data centers just not exist since they are directly tapped into these energy sources?
* Look into Nvidia xfra mini data center program
  * Where are they looking to build these?
  * Do homeowners even have the "extra energy" xfra claims they have? Why would they even have extra in the first place?
* Expand outside of US to looking at european datacenters
  * Specifically in locations like ireland
  * One possible hypothesis is similar to the new england hypothesis. Since Europeans rely more on renewables, there will be more fluctuation.
  * It would also be very nice if European data centers released data, or if European data from energy RTOs gives more granular information
  * See if European data centers are also looking into behind the meter technology