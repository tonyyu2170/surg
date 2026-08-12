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

* **Ireland is the first market where the data-centre dose is *measured*, not proxied.** Ireland's CSO publishes metered data-centre consumption quarterly (table MEC02): **4.4% of national metered electricity in 2015Q1 → 23.7% in 2025Q4**, a 5.3× rise. Every US result so far leaned on a geographic proxy (Loudoun, DOM, Ashburn). Even better, **non-data-centre consumption was flat over the whole eleven years (×1.02)** — essentially all Irish load growth is data centres.
* **Load shape: I paired Ireland against the Netherlands as a control**, both from ENTSO-E so a treated-vs-control difference can't be a data-source difference. Irish load at 30-minute resolution, Dutch at 15-minute, 2015→2026.
* **⚠️ I had to correct my own design here.** I'd written down that the Dutch data-centre share was "flat at ~4.6%" — that came from desk research and it's **wrong**. CBS publishes the series: 4.6% is the **2024 endpoint**, and the Dutch share **tripled** from 1.48% in 2017. So the Netherlands is a **low-dose control, not a placebo**. I only caught this because I went back to verify it after the analysis had already run.
* **Result — Irish load shape changed a lot, and the control changed identically.** Peak/trough fell 1.69→1.40 in Ireland and 1.67→1.36 in the Netherlands; the night floor rose 0.72→0.82 in Ireland and 0.72→**0.84** in the Netherlands. The day flattened by filling in the overnight hours, **peaking at hour 3 in both countries**. On every statistic the control moved as much as or more than Ireland.
* **That correction actually made the result stronger, by turning a placebo test into a dose-response test.** 2017→2024, Ireland's share went 6.9%→21.9% (**+15.0 points**) and the Netherlands' 1.5%→4.6% (**+3.1 points**) — so Ireland took **4.8× the dose increment**. If data centres were flattening load, Ireland should have moved ~5× as far. **Per percentage point of dose, the Netherlands moved 2.5–3.9× *more*** on every statistic. And read as a *ratio* instead, both shares simply tripled (×3.19 vs ×3.09) with the same response. Either way there's no dose-ordering.
* **The headline number nearly fooled me, and it's the same trap as ISONE.** Normalized volatility fell 28% in Ireland — but raw absolute volatility fell only 6.7% while mean load grew 30%, so the "decline" is mostly the denominator. The Netherlands fell 28.6%, statistically indistinguishable. **On the raw numerator the dose correlation is r = −0.26 for Ireland and r = −0.27 for the Netherlands** — a control correlated against a covariate from a country it has no exposure to tracks it just as well.
* **What it can't say:** one treated unit, one control, n=44 quarters, no identification strategy — not causal in either direction. COVID and the 2022 energy crisis sit inside the window. EV and heat-pump growth push `night_floor` the same way data centres would, and I have no way to separate them here.
* **Two data findings worth knowing:** Irish load and price come from **different EIC codes** — using the SEM code gets you an all-island series ~1,015 MW too big, which is what earlier desk research mistook for a disqualifying footprint mismatch. And the Irish feed is **1.85% incomplete** (661 gaps, largest 19 days) where the Dutch is 100% complete; gaps had to be masked before differencing or they invent volatility, with a bias that varies 33× across years.
* **Italy, as a robustness check (not a finding): level beats volatility in 36 of 36 cells**, both windows. That's panels 12–13 of the cross-ISO result, now 6 Italian bidding zones over 2015→2026 with *perfect* coverage (0 missing hours, unlike Ireland). One detail worth having: **normalized volatility fell in 5 of 6 zones but ROSE in Sardinia (+4.7%)** — which, with ISONE's +9.9%, is another nail in "normalized volatility falls in every panel."
* I dropped **Calabria** from the Italian panel: it only became a bidding zone on 2021-01-01 (split from South), so including it would have cut six years off the other zones and put a composition break mid-panel.
* Full write-up: `docs/research-notes/K-ireland-dc-shape.md`.

#### Then I extended it to 12 European zones to test the solar explanation — and it changed two things above

* **The question:** if rooftop solar is carving the *metered* midday, then part of the "flattening" above isn't a change in anyone's behaviour, it's a metering artifact. You flagged this as the one thing the North American data couldn't settle.
* **⚠️ The Dutch control series changes definition in April 2023 — and the comparison above is computed across that break.** The April/March load ratio is **1.0493 against a 0.9247 median in every other year** (+1,548 MW), and the jump is **midday-specific: +1,395 MW vs a −123 MW median**. Two things rule out the innocent explanation: a flat industrial recovery from the 2022 gas crisis *cannot* move a deviation-from-its-own-mean, and **the Netherlands is the only zone where both screens fire** (one other zone, Germany, has a midday-deviation outlier that year — −934 MW, opposite sign, no level step — so I'm not claiming the other eleven are all silent). Pre-break, Dutch summer midday runs +1,521 → **−1,343 MW**, then snaps back to +655 MW. I'd like to re-run the Ireland-vs-Netherlands comparison on a clean 2015→2022 window before we lean on it. I have not confirmed the cause with TenneT and am not asserting one.
* **Ireland's flattening is summer-specific — and this one needs no modelling assumption at all.** In raw MW, Ireland's **winter** midday hump is *the same size it was eleven years ago* (**+313 → +320 MW**) while its **summer** hump has **more than halved (+435 → +193 MW)**. That statistic is provably immune to flat load being added, so no quantity of data-centre growth can move either number. **Data centres can't produce a seasonal signature; solar can.** (In the ratio units of last week's table: winter −0.0740 against a −0.0733 dilution prediction, summer −0.0526 against −0.1190 — an excess of +0.066. Same fact, two units.) Ireland's series has no break (2023 excess 0.9853), so this one is clean.
* **Across the panel the signature tracks installed solar: Spearman ρ = +0.714** (n=7 zones) — but I'm calling this **suggestive, not a measured dose-response**, and here's why. When I checked ENTSO-E's installed-capacity feed against published national PV figures it runs **~100% complete for the Netherlands and ~3% for Finland** (27 MW reported against a ~1,000 MW national fleet), with Germany 78%, France 74%, Spain 60%. So the dose is real but its completeness varies wildly by country, and I haven't corrected for that. **Finland still doesn't move** (signature −0.0295 → −0.0291, and −0.0289 → −0.0291 over the full load record) and it remains the lowest-dose zone under any source, so the placebo logic holds — but its 0.005 dose figure doesn't mean Finland has no solar. **Both Danish zones move the *wrong* way** and I've kept them in rather than dropping them; Denmark is wind-dominated with heavy electric heating.
* **Findings 1 and 2 above don't depend on any of this** — the Dutch break and Ireland's summer-specific flattening are computed from load alone and use no dose at all.
* **I re-derived every headline number from the raw files with independent code and found two bugs in my own work**, both now fixed: installed-capacity years were shifted by one (the annual document's start timestamp is local midnight of 1 Jan, which lands on 31 Dec of the prior year), and the break detector was using a different day-sample from every other statistic. ρ = +0.714 survived both; the Dutch break figures moved to 1.0493 / 0.9247 / +1,395 / −123.
* **A data trap worth your time:** I nearly used ENTSO-E's *metered solar generation* as the dose. Dutch metered solar peaks at **204 MW** against **27,980 MW installed** — Dutch PV is distributed and the TSO simply can't see it — while Germany's peaks at 24,393 MW against 77,016 MW installed. **ENTSO-E metered solar is not comparable across countries**, and using it would have scored the Netherlands as a near-zero-solar market and inverted the whole result. I switched the dose to installed capacity, which matches the national fleet figure.
* **What I'm *not* claiming:** none of this shows data centres don't change load shape — I didn't test that. It shows one component of what I measured last week has a fingerprint data centres can't leave.
* Full write-up: `docs/research-notes/L-solar-metering-artifact.md`.

### Pecan street texas dataset

* 

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

## Things I Need Advice On

* 

## Future Direction

* 

## Notes from meeting

* 

## TODO

Today

1. **DONE.** Register UKPN Open Data, confirm the DC profile dataset downloads. Highest value per minute of anything on this list. If it downloads, it's the first facility-level data-center load data the project has found in thirteen weeks.  
2. **DONE, waiting for response.** Email ENTSO-E ([transparency@entsoe.eu](mailto:transparency@entsoe.eu)) for an API token — \~3 working days.  
3. **DONE, waiting for response.** Sign up for Pecan Street University Access (free, needs student ID photo) and email [licensing@pecanstreet.org](mailto:licensing@pecanstreet.org) about whether the 2kHz waveform data is in that tier.

This week

4. **DONE.** Canada new england connection  
5. **DONE.** Look at advisor suggested links  
6. **DONE.** Look at UKPN data set for UK data center load. Is data-center load actually spiky?  
7. Look at Pecan street data set. Maybe if we subtract total load from residential we can somewhat isolate data center load?  
8. Look at european grid data, conduct analysis there similar to pjm/ercot/whatever else based on what data is available