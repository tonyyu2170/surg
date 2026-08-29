# **Current Status:** 

Pulled data and applied seasonal/hourly filter.

**Originally:** Data from three main datasets: Hourly Metered Load, Real-Time Hourly LMP, and Real-Time Five Minute LMPs. (2020-2025)

But

* Given the nature of the question is related to volatility, makes more sense to just look at 5 min data  
* Load data at 5 min intervals only available for 30 days on pjm, 6 months if using archived data.   
* Load at individual pnode is not available, only DOM wide aggregate is

**Now:** Using alternative data source, [gridstatus.io](http://gridstatus.io). 

* Also has api limits that are annoying but the data restrictions are lessened  
* 5 min load data goes back to Feb23. Not exactly the 2020-2025 window i originally aimed for but still should work… 2023-2026  
* 5 min lmp data goes back to like 2018 but unnecessary since just using 2023-2026 now  
  * Looking at 10 pnodes spread across data center alley \+ additional areas spread around virginia to get some baseline/constants to compare to  
    * LOUDOUN  
    * PLEASANT VIEW  
    * GOOSECRE (Goose Creek)  
    * BRAMBLET (Brambleton)  
    * MOSBY  
    * SKFFSCRK (Skiffes Creek)  
    * ASHBURN 35 KV LOAD (bus 1\)  
    * ASHBURN 35 KV LOAD (bus 2\)  
    * OX  
    * BRISTERS  
    * DOM zonal (aggregate)

# **Things I need advice on:**

* Since pnode load data not available **should i compare pnodes to aggregate or aggregate to aggregate**  
  * My thought process, pnodes to aggregate  
  * Pnodes to aggregate also lets me see anomalies in different pnodes, even though all being compared to dom anyways  
  * I have pnodes in diff locations, most in data center alley but some spread out in more rural areas  
  * More granularity  
  * Another option is doing both since I already have both on disk  
* After applying seasonal/hourly filter, max LMP is $177/MWh, average during filter is \~$25/MWh. Outside of filter, max LMP is \> $4000/MWh, median about \~$30/MWh. LMP \=  system energy price \+ congestion cost \+ marginal loss cost. **Should I remove the filter to get more of the “high congestion” events?**  
  * My thought process, Yes.  
  * Part 1 of my proposal seeks to answer what load causes a phase transition in pricing  
  * The answer to this question is regardless of data center load or not, data center load just adds into it to create these high MWh events  
  * Part 2 questions when in the future the grid can’t handle pressure anymore and has widespread outages at an often rate.  
  * In the future, things like AC, heating, commercial energy use will still be there. If anything more energy use will be put towards these.  
* What if there is no phase transition  
  * Originally in my report I ask: What is the critical volatility threshold of data center load variance that triggers a non-linear phase transition in Dominion Zone congestion pricing, and at what point in the future will this threshold become the chronic operating state of the NOVA grid?  
  * The idea of non linear phase transition was based on existing literature, might not be the case for pjm

Nano generators