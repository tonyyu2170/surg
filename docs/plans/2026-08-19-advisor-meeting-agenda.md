# Advisor Meeting Agenda — 2026-08-19

## Current Status

## Findings This Week

### UK Data centers

* 

### European energy markets

* 

### Pecan street texas dataset

* 

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

## Future Direction

## Notes from meeting

Links i need to look into

* [A Proposed Framework to Assess Headroom for Integrating Data Centers into Regional Power Systems: An Industry Playbook for Unlocking System Potential with Flexibility](https://www.epri.com/research/products/000000003002034162)  
* [https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/llwg/lltf\_april\_meeting\_\_technical\_workshop\_presentations\_.pdf](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/llwg/lltf_april_meeting__technical_workshop_presentations_.pdf)  
* [Machine Learning Guided Cooling System Optimization for Data Center](https://arxiv.org/pdf/2601.02275)  
* [https://www.ferc.gov/sites/default/files/2024-07/PJM%20FERC%20Technical%20Conference%202024%20-%20Hourly%20Electricity%20Load%20Forecasting%20Using%20Machine%20Learning%20Algorithms.pdf](https://www.ferc.gov/sites/default/files/2024-07/PJM%20FERC%20Technical%20Conference%202024%20-%20Hourly%20Electricity%20Load%20Forecasting%20Using%20Machine%20Learning%20Algorithms.pdf)  
* [https://powering-intelligence.epri.com/annual-peak-use.html](https://powering-intelligence.epri.com/annual-peak-use.html)

## TODO

Today

1. **DONE.** Register UKPN Open Data, confirm the DC profile dataset downloads. Highest value per minute of anything on this list. If it downloads, it's the first facility-level data-center load data the project has found in thirteen weeks.  
2. **DONE, waiting for response.** Email ENTSO-E ([transparency@entsoe.eu](mailto:transparency@entsoe.eu)) for an API token — \~3 working days.  
3. **DONE, waiting for response.** Sign up for Pecan Street University Access (free, needs student ID photo) and email [licensing@pecanstreet.org](mailto:licensing@pecanstreet.org) about whether the 2kHz waveform data is in that tier.

This week

4. Canada new england connection: test on price  
5. Look at advisor suggested links  
6. Look at Pecan street data set. Maybe if we subtract total load from residential we can somewhat isolate data center load?  
7. If UKPN downloads: characterize the \~100 site profiles. Is data-center load actually spiky? Your proposal assumes it and cites two papers; nobody has checked it against data.  
8. Look at european grid data, conduct analysis there similar to pjm/ercot/whatever else based on what data is available
