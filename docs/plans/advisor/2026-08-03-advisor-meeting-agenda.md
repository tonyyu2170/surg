# Current Status

* **I’ve moved the analysis to a full 5-minute panel:** February 2023–June 2026  
* **No more filter**: Now using all months and hours rather than only the original shoulder-season / 2–5 AM filter.  
* **Next step:** researching technologies, current events, policy that could impact load/congestion outlook in dom

**Why the change:** the quiet-hours filter was useful for trying to isolate data-center-like load, but it removed almost all of the genuinely high-price events. It made the original “when does LMP go crazy?” question impossible to answer.

**The key data limitation remains:** PJM does not publish load at each pnode or data center. My “DOM load” series is a broad regional aggregate, so I can measure system-level load and ramps, but not the load swings of individual facilities.

# Findings This Week

**The original idea was:**

> More data centers → more volatile load → a threshold where congestion prices become unstable or heavy-tailed.

The evidence does not support a clean threshold or phase transition.

- **DOM aggregate load has increased substantially since 2023, but its short-term ramp volatility has not meaningfully increased**. Relative to total load, volatility has actually declined.  
  - Load jumps are pretty much the same size from 2023-2026, \~25 MW/min  
  - Across location, ashburn much higher overall congestion prices and more volatile than skiffescreek  
  - But ashburn is also a 35-kV distribution-side load node while SKFFSCRK is a 500-kV EHV node. Also ashburn is more populated so cooking/heating/ac feeds into it too  
- **High congestion is much more associated with high load level than with a rapid load change.** In the highest load decile, congestion becomes much more common; outside that range, it is usually low.  
- The initial model found a small positive relationship between ramp size and higher congestion prices. But after accounting for the overall load level, that relationship reverses: at the same load level, **high-ramp intervals are not the most congested ones.**  
- This helps explain an earlier result that initially looked counterintuitive: **the most extreme congestion tail was somewhat heavier during low-ramp intervals. Those intervals may simply represent sustained high-load conditions, when constraints have time to bind.**  
- The size of the ramp effect is small in practical terms. Across the observed range of load ramps, the estimated movement in the 95th- percentile congestion price is only a few dollars per MWh—far too small to explain $100+ or $500+ congestion events.

There is also an important 2026 complication. **Prices changed sharply in January 2026 even at comparable load levels.** Both congestion and system-energy prices rose, and system energy is system-wide rather than local to Northern Virginia. So I cannot credibly attribute the 2026 escalation to data centers or DOM congestion alone without a non-DOM comparison point and more event-level investigation.

# Current Takeaway

**The current answer to sub-question 1 is becoming:**

> I do not find a load-ramp-volatility threshold that pushes Dominion congestion into a heavy-tailed regime. Aggregate load level matters much more than aggregate load volatility, and the volatility result is small and sensitive to specification.

This does not mean data centers are irrelevant. It means the **available public aggregate-load data cannot support the stronger claim** that short-term data-center-driven load swings are the cause of extreme price events. Individual facilities may have meaningful local effects that are smoothed away in the regional load data.

# Things I Need Advice On

- **What should the paper’s main framing be?** My current preference is to present this as a useful negative/refinement result: the proposed volatility-threshold mechanism does not appear in the public aggregate data; load level and changing grid conditions appear more important.  
    
- **Should I acquire a non-DOM comparison pnode** before finalizing the paper? This would help distinguish a Dominion-specific congestion story from the broader PJM-wide price increase visible in 2026\. It would strengthen the attribution discussion, but expands the scope. **Maybe compare against Southwest Power Pool (SPP)**

**Emailing ppl to get data**

* Directly find hyperscaler on data center side  
* Utility company on transmission side  
* Maybe look at ercot or caiso  
* For ercot utd or uta has ercot data center published data set

[https://baxtel.com/map](https://baxtel.com/map)