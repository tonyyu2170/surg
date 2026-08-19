# Advisor Meeting Agenda — 2026-08-19

## Current Status

## Findings This Week

### UK Data centers

* UK Power Networks publishes **30 minute interval demand profiles** for **96 anonymous data centers**. Instead of giving traditional **MW**, it instead gives a **utilisation ratio**: observed apparent power ÷ that site's contracted maximum import capacity.  
* This is the first **facility-level** data the project has: 96 individual buildings, metered. The trade is **no MW, no location, no price.** It's a dimensionless ratio from a *distribution* network, not an ISO, so it can't be joined to any nodal geography and cannot speak to price formation at all  
* **Load is flat**. Not super volatile, with expected troughs in morning and hills during the day  
* However,  
  * **These are probably not Hyperscale AI training facilities.** Anonymised UK distribution-connected sites, most likely conventional colocation and enterprise. The synchronized-training workload the whole volatility premise is about may not appear anywhere in this sample.  
  * For the utilisation ratio, **the denominator is *contracted* capacity, not nameplate**, so a flat ratio partly reflects how much headroom a site bought, not how it runs.  
  * **Half-hourly resolution cannot see the 0.1–30 Hz band** where industry actually locates the problem.  
* Seems like whatever we try we can never find an ideal data set. Every set has something we want and misses everything else

### European energy markets

* Pulled about a decade (2015–2026) of demand data from **ENTSO-E**, Europe's official grid-data platform — Ireland, the Netherlands, Italy's six bidding zones, and eventually **12 zones** across Europe for a solar follow-up. Readings every 15–30 minutes.  
* **Ireland** is the only market anywhere in this project where data-centre consumption is actually **metered** (by Ireland's national statistics office) rather than guessed from geography. Data centres grew from **4.4% → 23.7%** of Irish electricity over the decade — and all *other* Irish consumption was flat, so essentially every megawatt of Irish demand growth was data centres. The Netherlands (much smaller data-centre share) served as the comparison country.  
* **Raw minute-to-minute swings in Irish demand barely changed**; what fell was the *ratio* of swings to total demand, because total demand grew 30%. Same denominator trap that already burned us once with ISO-NE, caught a second time.  
* **Ireland's daily load pattern really did flatten dramatically — but data centres don't look like the cause.** The Netherlands flattened in almost exactly the same way, at the same hours, over the same years, despite absorbing only about a fifth as much new data-centre load. If anything the dose-response runs backwards: per unit of data-centre growth, the Dutch pattern changed *more*.  
* **The real fingerprint points at rooftop solar, not data centres.** Ireland's flattening happens almost entirely in **summer at midday** — the winter pattern is unchanged in absolute MW after eleven years. Data centres run flat year-round and physically cannot produce a seasonal signature; solar panels (which erase midday demand from the grid's view in summer) can. Across 12 European zones, the size of this summer-midday effect tracks how much solar each country installed.  
* **Italy served as a robustness check and agreed with everything prior:** in all **36/36** comparisons, price behavior is driven by demand *levels*, not demand *volatility* — consistent with all 11 US market panels.  
* **Volatility that might come from renewables and volatility that might come from data centers is different**  
  * Data centers are sub second, renewables can be acros hours/days/weeks  
  * If we want to see data center volatility we need to see more granular, and the most granular thing we have is pecan 1 minute data

### Pecan Street Texas dataset

* The dataset is 73 real homes wired with research-grade meters. The free academic tier used here covers **25 homes in Austin, 25 in New York, and 23 in San Diego**. It's the most **granular** demand data this project has ever held; everything else we have tops out at 5-minute market feeds.  
* The question comes from XFRA, a SPAN/NVIDIA venture putting AI compute in houses. The pitch is that homes have unused electrical capacity, so why not fill it with an always-on node of 16 NVIDIA GPUs plus cooling, drawing about 12.5 kW. Leads to 2 questions: **does the headroom exist, and does it survive the hottest summer afternoon?**  
* **It depends lol.** Whether the node fits is decided almost entirely by the home's electrical service rating (the amperage of its panel). Assume every home has **200-amp** service (most homes have this) and all 73 homes can host the node even at their single worst minute of the year. Assume 150 amps: 84 to 91 percent. Assume 100 amps and it collapses to 4% in Austin, 16% in New York, 48% in California.  
* **Homes barely touch their limits, even at their absolute peak.** The typical home's highest single minute of the entire year is about 7 to 12 kW depending on the city, under a third of the \~38 kW a 200-amp panel can safely sustain, and most minutes sit below 5 kW. Summer is when it tightens: about two-thirds of Austin homes and most California homes set their annual peak on a summer afternoon near 5 pm, yet spare capacity never comes close to zero.   
* We had assumed it would throttle whenever the household got busy. The vendor's white paper says the opposite: household spikes are absorbed first by an included home battery, then by pausing the EV charger, while the compute node runs continuously. So XFRA adds a large flat load, not a jittery one, and the question becomes capacity planning (does it fit behind the breaker?) rather than power quality (will it flicker the lights?). Just as well: if a node this size did pulse at full amplitude, each swing would be about seven times a typical home's biggest everyday jolt, and larger than any single step most of these homes recorded in the entire dataset.  
* **Household fast volatility is nearly zero,** and it cancels. The median second-to-second change in a home's power draw is about two watts versus twelve and a half thousand for the node. Also lots of homes cancel each others volatility out  
* **The honest limitations.**  
  * The bundles are 2018-19 vintage, before heat pumps, induction ranges, and Level 2 EV charging spread, so the headroom estimates run optimistic for a modern home.   
  * The data is kind of biased and tilted toward solar and EV owners.   
  * New York covers only six months, with no winter.   
  * Once-per-second sampling physically cannot see oscillations faster than half a hertz, so we observe roughly the bottom 1% of the 0.1-30 Hz band where industry actually locates the AI-load problem  
* **Estimating data-center load by subtracting residential load from system totals fails for four independent reasons**  
  * A thousand-odd volunteer homes can't stand in for millions  
  * The volunteers aren't representative  
  * Whatever remains after subtraction is all commercial and industrial load rather than data centers  
  * This data predates the AI build-out anyway.   
  * Ireland, from the ENTSO-E work, remains the only place in the project where data-center load is actually metered rather than inferred.

### Links you gave me last week

* [A Proposed Framework to Assess Headroom for Integrating Data Centers into Regional Power Systems: An Industry Playbook for Unlocking System Potential with Flexibility](https://www.epri.com/research/products/000000003002034162) (compared to xfra.ai)  
  * Both EPRI and XFRA aim to solve the primary bottleneck of the AI boom: the **5-to-10-year wait times required to connect massive new loads to the grid**, avoiding the need for multi-billion-dollar transmission and generation upgrades.  
  * EPRI's framework provides a **standardized, four-step methodology** for grid operators to safely connect massive, centralized data centers to the existing transmission grid by **calculating the system's unused "headroom"** across different scenarios.  
    * Step 1: Wide range operating conditions  
      * Uses probabilistic modeling to analyze the grid hourly, accounting for macro variables like weather, economic conditions, availability of renewables  
      * Identifies the theoretical max excess power before any physical constraints of power lines are considered  
    * Step 2: Nodal transmission limits  
      * Overlays physical map of nodes and transmission lines to the hourly data from step 1  
      * Prove that delivering excess power to a data center won’t cause congestion or make lines explode  
    * Step 3: sub hourly limits  
      * Looks at sub hourly intervals to look at sudden spikes in demand or drops in supply  
      * Prove that flexible data centers can actively ramp power up or down within those small windows to respond to changes  
    * Step 4: zoom in more to local equipment  
      * Looks at local voltage stability, frequency regulation, health of local transformers  
      * Proves that when a data center cuts its power, sudden voltage spike won’t fry local infrastructure  
  * EPRI relies on data centers proving they can **quickly ramp down usage** during regional grid congestion, while XFRA relies on SPAN smart panels to **instantly throttle the AI node's power** if a homeowner turns on major appliances (like an oven or dryer).  
  * EPRI's framework aims to **protect everyday utility ratepayers from the costs of infrastructure upgrades** caused by hyperscalers  
* [Large Loads Task Force Meeting and Workshop](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/llwg/lltf_april_meeting__technical_workshop_presentations_.pdf)  
  * Tesla and Google provided hard data proving that AI training workloads are not static. Tesla showed **AI loads oscillating at 0.1–1 Hz and 5–30 Hz**, with amplitude swings reaching up to 90% of peak capacity (framed by Elon Musk as "**10–20 MW** shifts several times per second," with Google corroborating swings in the tens of megawatts).  
  * Utility presentations detailed exactly why data centers exacerbate grid faults. Their **power electronics employ aggressive undervoltage protection**; if local voltage dips below \~65% during a transient event, the facility **instantly disconnects** to protect its servers. They then take roughly 8 seconds to automatically reconnect. Entergy demonstrated that when this massive load slams back onto the grid simultaneously, the sudden localized demand spike can cause nearby conventional generators to lose transient stability and slip out of synchronism.   
    * This is kinda **outdated** by now   
    * Mandated **Voltage Ride-Through (VRT)** and **Fast Frequency Reserve (FFR)** capabilities try to mitigate disconnection issues  
    * Even in case of disconnection, facilities can **soft start** to not put a done of stress at once  
  * This 145-page deck serves as historical context. Its proposed frameworks have since been codified into binding industry documents. For current regulatory analysis, cite LLTF White Paper 2 (March 2026\) and the NERC Reliability Guideline (May 2026).  
* [Machine Learning Guided Cooling System Optimization for Data Center](https://arxiv.org/pdf/2601.02275)  
  * A test on a top-tier supercomputer, the Frontier exascale system.  
  * Because the system's average IT load is 12 MW, s**mall percentage inefficiencies in cooling pumps and fans still translate to hundreds of kilowatts** of continuous, wasted power.  
  * Developed and trained a ML model to predict how much cooling power should be used at a given time to see when the facility’s cooling system is overworking  
  * In the context of our project, not super useful. They measured **10 minute resolution data** which isn’t as granular as article 5 suggests we need  
* [Hourly Electricity Load Forecasting Using Machine Learning Algorithms](https://www.ferc.gov/sites/default/files/2024-07/PJM%20FERC%20Technical%20Conference%202024%20-%20Hourly%20Electricity%20Load%20Forecasting%20Using%20Machine%20Learning%20Algorithms.pdf)  
  * PJM tested 4 modern ML models against their production forecast. XGBoost won across the system, but **it ws better than the production forecast for every large zone except Dominion**. That's PJM naming your zone as the one place their methods break.  
  * The closing slide says it outright: "**Dominion data center load is challenging and will be more so in next few years.**"  
  * Crucially, the problem they describe is **unpredictability, not jumpiness.** The load is **hard to forecast, not wildly swinging**. That's a different defect than the proposal assumed, and it points the same direction your results do.  
* [Annual and Peak Electricity Use: History and Future Projections](https://powering-intelligence.epri.com/annual-peak-use.html)  
  * Someone finally metered actual data centers. The answer: they **run at \~90% of their own peak essentially all year** — 94% for a large single-tenant site, 88% for multi-tenant. That is about as flat as any load on the grid gets.  
  * Data centers do not hit their advertised capacity. Real peaks land at 62–80% of nameplate. When a developer announces "500 MW," the grid sees appreciably less — EPRI flags this as a planning trap.  
  * Buried in a footnote is the whole story: **load is steady "across minutes and hours," but swings hard at second and sub-second timescales.** And the consequence they name is grid reliability.  
    * After this note they kindly included a link “as an example” for an article that costs $25,000 to access ([https://www.epri.com/research/products/3002033303](https://www.epri.com/research/products/3002033303))

### New England/Canada Connection

* Last week, **Vermont, maine, rhode island** showed more **volatility** in aggregate load data than expected  
* However, this is unlikely since **imports are supply, load is demand.** They're different quantities.  
* When more Canadian power flows in, **load wouldn’t change.** Maybe price would?  
* **Rhode Island has no connection to Canada at all** — and it's one of the three zones that got more volatile.  
* Also massachusetts (48.2%) and vermont (33.7%) are also very heavy on solar not just cananda  
* The **largest Canadian line** —Phase I/II, 2,000 MW, nine times bigger than Vermont's — lands at **Sandy Pond in Massachusetts, where volatility fell in all three zones** (−3.2%, −4.8%, −12.7%).

### PJM, FERC, and the 50 MW Limit

* The 50 MW number is just an arbitrary number that PJM came up with to describe a **“large load”**  
* Chose this number to c**apture hyperscale AI data centers** while exempting standard commercial or industrial facilities.  
* **The Transmission Cost Illusion:** It seems logical that a behind-the-meter data center wouldn't incur transmission costs since it taps directly into the generator. However, these facilities **still rely on the broader grid for frequency regulation, stability, and emergency backup**. If the co-located power plant trips offline, the data center will instantly pull massive amounts of power from the grid to stay online.  
* **Cost Shifting to Homeowners:** The **transmission grid must build and maintain the physical infrastructure** to handle these sudden, fast-ramping backup draws. If data centers use retail behind-the-meter netting rules to report a "net zero" usage, they **avoid paying the transmission tariffs that fund this exact infrastructure**. Because total grid maintenance costs are fixed, those unpaid costs are **shifted to other transmission customers,** ultimately trickling down to residential homeowners' utility bills.

### NVIDIA & SPAN's XFRA Mini Data Centers

* **Homeowners don't generate extra energy;** instead, XFRA is utilizing hidden "electrical headroom". When a home is built, its electrical panel (e.g., 200-amp service) is permitted for a **theoretical maximum load**—assuming the HVAC, electric stove, EV charger, and dryer all run simultaneously on the hottest day of the year. In reality, a home's average continuous power draw is a fraction of that limit.  
* Since its early in development, SPAN has indicated that it will likely take on **paying the host's electricity and broadband internet bills directly.** The homeowner would then **pay a predictable, flat monthly fee** that is significantly lower than what they would normally pay their electric utility.  
* Homeowners who host a node receive **significant infrastructure upgrades.** For the initial 100-home proof-of-concept, the home comes equipped with the **XFRA compute node, a SPAN smart panel, and a 15 kWh whole-home battery backup system** that provides reliable power to the home during grid outages  
* Current stage: executing a **100-home "proof of concept" pilot program**. Instead of retrofitting older houses, they have partnered directly with the homebuilder PulteGroup to install these first units exclusively in new residential construction projects in the southwestern United States.

## Notes from meeting

* Dig more into [Large Loads Task Force Meeting and Workshop](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/llwg/lltf_april_meeting__technical_workshop_presentations_.pdf)  
  * Where they got their data from, where does the subsecond number come from  
  * Maybe can say compute fluctuates but overall load is smooth when adding in storage other data center usages  
  * Would a battery be fast enough to respond to this sub second fluctuation  
  * Does compute aggreagate out with enough clusters being used (law of large numbers) or does something else like hvac could also aggregate out, maybe battery, maybe behind the meter, etc.  
  * For current regulatory analysis, look more into LLTF White Paper 2 (March 2026\) and the NERC Reliability Guideline (May 2026).  
* Current conclusion  
  * At least on large timescale (hourly) not a lot of fluctuation with load (this looks like most likely report outcome as of now)  
  * but why?