# PJM LMP Formation — Primary-Source Reference

**Created:** 2026-07-29. **Workstream C** of the 2026-07-29 advisor meeting
(sub-q1 closure item #5). Design: `docs/specs/2026-07-29-pjm-lmp-formation-research-design.md`.

## Purpose

What the market *mechanically does*. This is the third standing reference,
alongside `pjm-api-constraints.md` ("what the API forces on us") and
`decisions.md` ("what we chose"). Read it before any interpretation or
write-up work.

Written from PJM's own manuals and whitepapers only. The advisor's
instruction was to stop relying on third-party summaries; where PJM's
documents do not answer a question, § 10 says so rather than substituting
an outside source.

### Source inventory

| Tag | Document | Revision / date | Local path |
|---|---|---|---|
| **M11** | PJM Manual 11: Energy & Ancillary Services Market Operations | Rev. 137, eff. 2026-07-28 | `docs/reference/pjm-manuals/m11.pdf` |
| **M12** | PJM Manual 12: Balancing Operations | Rev. 57, eff. 2026-04-22 | `docs/reference/pjm-manuals/m12.pdf` |
| **M03** | PJM Manual 3: Transmission Operations | Rev. 71, eff. 2026-05-20 | `docs/reference/pjm-manuals/m03.pdf` |
| **RSP** | PJM, *Formation of Locational Marginal Pricing and its System Energy Component During Reserve Shortage Events* | 2023-03-07 | `docs/reference/papers/reserve-shortage-pricing-paper.pdf` |

All retrieved 2026-07-29 from `www.pjm.com`. (`api.pjm.com` is the host
that NXDOMAINs on NU DNS; the document server resolves normally.)

**Citation format.** `M11 p.22 § 2.2` — page numbers are **PDF page indices
in the vendored file**. Navigate by PDF page, not by the printed footer
number: the two differ by an offset that is **not constant** (front matter
and unnumbered pages shift it), so no conversion rule is given here. Section
numbers are quoted where the manual supplies them and are the more stable
locator. Verbatim quotes for load-bearing claims are in the Appendix.

---

# Part 1 — Mechanism reference

## §1 The three-component decomposition

M11 § 2.2 defines LMP as the full marginal cost of serving an increment of
load at a bus, decomposed into exactly three components: **System Energy
Price**, **Congestion Price**, **Loss Price** (M11 p.22 § 2.2). The same
decomposition appears at p.13 and, restated for the Day-ahead Market
specifically, at p.154.

The § 2.2 statement is **market-agnostic** — it governs both Real-time and
Day-ahead. § 2.2 says "LMPs are calculated in both the Real-time Energy
Market and Day-ahead Energy Market," and the bullet immediately preceding
the decomposition reads "The Real-time LMP is calculated based on the
approved security constrained economic dispatch solution for the target
dispatch interval." This scoping matters: see § 3.

The decomposition is **exhaustive**. There is no fourth component, and no
separate "scarcity" or "ramp" term. Anything that affects price must enter
through one of the three.

## §2 The system energy component

### What it is

The price of an additional increment of energy from the marginal resource
(M11 p.22 § 2.2). RSP works a full numerical example: the system energy
LMP is built as

```
Energy LMP = Incremental Cost + Congestion Cost + Lost Opportunity Cost
```

where all three terms are evaluated **with respect to the marginal
resource**, scaled by the loss factor needed to deliver one additional MW
to the *distributed load reference bus* (RSP pp. 4–6).

In RSP's 2021-03-17 worked example: `$30 + $1,547.57 + $2,401.16 =
$3,978.73/MWh` before the cap, resolving to a reported `$3,664.51/MWh`.

Two things follow. First, "congestion cost" appears *inside* the system
energy component — but it is the marginal *resource's* congestion impact,
a single scalar, not the pnode-specific congestion component of § 3.
Second, the whole quantity is computed once from the marginal resource, so
it carries no pnode index.

### Is it locationally uniform? — **Yes, across our pnodes (verified empirically)**

M11 does not state uniformity in prose, so this was tested directly on
`data/interim/analysis_panel_5min.parquet` (read-only):

> Across **350,174** rows with all three columns non-null, the maximum
> absolute difference between `system_energy_price_rt_35010365`,
> `system_energy_price_rt_35010371`, and
> `system_energy_price_rt_1356178195` is **9.09 × 10⁻¹³ $/MWh** —
> floating-point representation noise, not price variation.

**The system energy component is identical across Loudoun, Pleasant View,
and Goose Creek at every 5-minute interval in the panel.** For contrast,
`marginal_loss_price_rt_*` differs by up to **$22.60/MWh** between the
same pnodes, so the test is capable of detecting locational variation and
does detect it in the component where it is expected.

This is scoped to these three DOM-zone pnodes; it is not a claim about
RTO-wide uniformity. But that is the scope that matters here — see § 9.

### Scarcity adders

When reserves are short, the cost of converting a MW of a resource's
assigned reserves into energy enters the system energy component as **lost
opportunity cost** (RSP p. 6). M11 § 2.2 states it more generally: the
System Energy Price "may include a portion of the defined reserve penalty
factors should a reserve shortage exist" (M11 p.22).

**The Congestion Price carries the identical qualifier** — see § 3.

### The cap

Post-Reserve-Price-Formation, system energy LMP is **administratively
capped at $3,700/MWh** (RSP p. 8). The pre-RPF regime used $3,750/MWh
built as `$2,000 offer cap + $850 SR Step-1 + $850 PR Step-1 + $50 buffer`,
resolved by an iterative process that disabled sub-zone PR and then
sub-zone SR requirements until the value fell under the cap (RSP p. 6).
**That iterative process is no longer used**: "Post Reserve Price Formation
in the MCE, the system energy LMP is administratively capped at
$3,700/MWh. The iterative process described above ... is no longer
utilized" (RSP p. 8).

This matters for reading history: 5-min data before and after the RPF
change embeds different cap logic. Our panel starts 2023-02-07, after RPF,
so the $3,700 regime applies throughout.

## §3 The congestion component

### Definition

> "Congestion Price – This is the effect on transmission congestion costs
> (whether positive or negative) associated with increasing the output of a
> generation resource or decreasing the consumption by a Demand Resource,
> based on the effect of increased generation from or consumption by the
> resource on transmission line loadings." (M11 p.22 § 2.2)

### Computation

RSP gives PJM's own arithmetic, in the form used inside the system energy
component (RSP p. 5):

```
Cost of impact on constraint control
  = (energy needed from marginal resource) × Σ | Dfax × constraint shadow price |
```

worked as `1.0474 MW × (($2,000 × 0.73254) + ($2,000 × 0.00623)) =
$1,547.57/MWh` for two simultaneously binding constraints.

So the structure is **shadow price × distribution factor, summed over
binding constraints** — confirmed in PJM's notation, with `Dfax`
(distribution factor, also written `dfax`) as PJM's term for the shift
factor. Note the absolute value in that particular formula; it appears
because the marginal resource's *cost of relieving* constraints is being
computed. A pnode's congestion component is signed ("whether positive or
negative", M11 p.22).

### What makes a constraint bind, and what sets the shadow price

M11 § 2.17 is the authoritative section. A constraint violation occurs
when "the flow on the constraint cannot be controlled below the level to
which dispatch is attempting to control the facility" (M11 p.81). Then:

> "The transmission constraint penalty factor is then used to set the
> marginal value of the violated transmission constraint." (M11 p.81 § 2.17)

Default penalty factors (M11 p.81 § 2.17):

| Market / run | Default penalty factor |
|---|---|
| Day-ahead, dispatch run | $30,000/MWh |
| Day-ahead, pricing run | $2,000/MWh |
| **Real-time (both dispatch and pricing runs)** | **$2,000/MWh** |

So **yes, the shadow price is effectively capped** — at the penalty
factor, which is $2,000/MWh by default in Real-time. Below that level the
penalty factor is inert: "The transmission constraint penalty factor does
not directly impact the marginal value of a constraint as long as the
constraint can be solved by resources whose effective costs are lower than
the value of the penalty factor" (M11 p.81).

PJM **discretionarily adjusts** individual penalty factors in real time,
both upward (when available relief costs more than the default) and
downward (to stop an ineffective high-cost resource from setting price),
using a 25% buffer above the effective resource's `$/MW` cost (M11 pp.
81–82 § 2.17). The `$/MW` cost is
`(Resource Offer Price − System Energy Price) / dfax` (M11 p.82).

**This is a discretionary, human-in-the-loop term in the congestion
component.** It is not a fixed function of physical system state. Two
identical physical congestion events can price differently if operators
adjusted the penalty factor in one and not the other.

Constraints themselves are physical limits — thermal, voltage, and
transfer limits (M03 p.13). M03 confirms PJM operates so these are not
exceeded, and that short controlled exceedances happen and are documented
in Manual 3B.

### Is congestion referenced to a slack bus? — **A distributed reference, and M11 never says "reference bus"**

The phrase "reference bus" **does not appear anywhere in M11**. The only
primary-source statement of the reference is in RSP, and it is a
*distributed* one: the marginal resource's impact is computed "in relation
to one additional megawatt of load at the **distributed load reference
bus**" (RSP p. 4). M11's matching language is that LPC applies "a
normalized distribution of system losses to a network location" (M11 p.67
§ 2.7).

So the reference is a load-weighted distributed reference, not a single
slack bus. The practical consequence is narrow: because the reference is
system-wide and shared, a pnode's congestion and loss prices are **not
absolute costs** — they are that pnode's position relative to the
distributed reference, and the system energy component carries the absolute
level (§ 2).

This does **not** undermine analysis of congestion levels or thresholds.
The reference is common to every pnode and stable over time, so both
same-pnode-across-time comparisons (what the GPD and threshold work does)
and across-pnode comparisons at a given interval are well defined. The only
thing ruled out is reading a congestion price as a standalone dollar cost of
congestion.

M11 does not spell out the consequence in those words, so treat the
"relative quantity" reading as a direct implication of the distributed
reference rather than as a quoted PJM statement.

### Does congestion carry reserve penalty factors? — **Yes**

> "The Congestion Price may include a portion of the defined reserve
> penalty factors should a reserve shortage exist." (M11 p.22 § 2.2)

This is the **same sentence** applied to the System Energy Price, repeated
verbatim for the Congestion Price. It is in the market-agnostic § 2.2
definition, so it reaches the Real-time 5-min prices in our panel.

**The allocation rule is not in M11.** M11 states *that* congestion can
carry a portion; it does not say *how much*, or by what formula the
reserve penalty is split between the system energy and congestion
components. Recorded as unanswered in § 10. Do not infer one.

## §4 The marginal loss component

> "Loss Price – This is the effect on transmission loss costs (whether
> positive or negative) associated with increasing the output of a
> generation resource or decreasing the consumption by a Demand Resource,
> based on the effect of increased generation from or consumption by the
> resource on transmission losses." (M11 p.22 § 2.2)

The pnode loss sensitivity factor is `1 − (1 / Loss Penalty Factor)`,
computed by PJM's EMS per pnode and passed to the market clearing engine
(RSP p. 4). Losses are referenced to a **distributed load reference bus**
(RSP p. 4); LPC applies "a normalized distribution of system losses to a
network location" (M11 p.67 § 2.7).

Empirically locational in our panel: up to $22.60/MWh spread across the
three cluster pnodes (§ 2 above).

## §5 Timing and resolution

This section is load-bearing for the § 9 lag analysis.

### Two distinct programs

| Program | Role | M11 term |
|---|---|---|
| **RT SCED** — Real-time Security Constrained Economic Dispatch | Determines the least-cost dispatch | "the **dispatch run**" |
| **LPC** — Locational Pricing Calculator | Determines the prices | "the **pricing run**" |

> "Real-time LMPs and Regulation and Reserve Clearing Prices are calculated
> every five (5) minutes by the Locational Price Calculator (LPC) program,
> in a process referred to as the pricing run, and are based on forecasted
> system conditions and the latest approved RT SCED program solution."
> (M11 p.21 § 2.1.5)

The pricing run runs the same optimization as the dispatch run, plus
Integer Relaxation for Eligible Fast-Start Resources (M11 p.67 § 2.7.1).

### The 5-min price is a spot value at the interval *end*, not an average

> "Real-time LMPs ... are derived from the inputs of the latest approved
> Real-time Security Constrained Economic Dispatch (RT SCED) program
> solution, referred to as the reference case, **for the target time at the
> end of the current five (5) minute interval**." (M11 p.67 § 2.7)

> "The Real-time LMPs and Regulation and Reserve Clearing Prices calculated
> by LPC are **applied to each five (5) minute Real-time Settlement
> Interval ending at the LPC target time**." (M11 p.67 § 2.7)

**Answer to the integrated-vs-spot question: spot.** The 5-min LMP is a
single instantaneous optimization value at one target time, then *applied*
to the interval that ends at that time. It is not an average over
sub-intervals. If no approved RT SCED solution exists for the target time,
LPC falls back to the most recent approved solution prior to it (M11
p.67).

The LPC computes LMPs "for each of the PJM nodes in the state estimator
model" (M11 p.67), jointly optimizing energy and reserves subject to power
balance, the Synchronized / Primary / 30-Minute Reserve Requirements,
generator operating limitations, transaction MW limits, and existing
transmission constraints (M11 p.67 § 2.7).

### Prices are forward-looking — there is a lookahead

This is unambiguous and comes from two independent places.

> "The RT SCED cases use the load forecast and other relevant system
> information **for the look-ahead interval, rather than the time at which
> the case is executing**, to achieve a dispatch solution that will
> adequately control for those forecasted conditions." (M12 p.25)

M11 describes the mechanics: RT SCED works over a **ten-minute look-ahead**
in two five-minute segments, "looking back" to check whether the previous
dispatch basepoint lies inside the unit's achievable output band, then
ramping within the feasible range "over the subsequent five minutes" (M11
pp. 62–63). The achievable band itself comes from the state-estimator MW
value plus bid-in ramp rates — "where the unit can get to in the next five
minutes" (M11 p.61).

**Consequence: RT prices reflect forecast conditions at a future target
time, so they can *lead* realized load rather than lag it.** See § 9 for
what this does to the lag test.

### How this aligns with our panel — resolved 2026-07-29

The alignment is now verified rather than assumed:

- `gridstatus_pull.py:44` requests both `interval_start_utc` and
  `interval_end_utc` from `pjm_lmp_real_time_5_min`, and in the raw chunks
  `interval_end − interval_start` is **exactly 5 minutes** on every row
  (checked across a full pull chunk; single unique value).
- The gridstatus-vs-PJM equivalence check recorded in
  `docs/sources/gridstatus-api-constraints.md` found "**perfect temporal + pnode
  alignment** (0 ours-only, 0 gs-only)" over a 3-day DST-spanning overlap
  against our PJM Data Miner panel, whose time key is
  `datetime_beginning_utc`. Perfect alignment on that key establishes
  **gridstatus `interval_start_utc` ≡ PJM interval-beginning.**

Combined with § 2.7's target-time rule: **a row labeled
`interval_start_utc = t` carries the LMP PJM computed for target time
`t + 5 min`.**

So the panel's contemporaneous (k = 0) pairing puts the load gradient
measured *over* `[t, t+5)` against a price targeting the **end** of that
same window — the price is not lagging the ramp, it sits at the ramp's
close. And because the price is built from a forecast over a ten-minute
look-ahead, the price on row `t` already embeds expectations about load out
to roughly `t+10`–`t+15`. The practical test of anticipation is therefore
price at row `t` against Z on rows `t+1` and `t+2`; see § 10 item 5.

Operators also apply a **load bias** — "entered as a MW value and ...
distributed across the entire RTO" (M12 p.25) — to compensate for load,
wind, solar, and interchange forecast deviations. Dispatch therefore
sometimes prices against a deliberately offset load, adding a wedge
between any measured load series and what the engine actually saw.

### What load does dispatch actually price against? — **State-estimator bus loads, plus a forecast**

Not metered load, and not a zonal aggregate. M11 § 2.6 describes the
State Estimator as taking "the available (metered) Real-time measurements,
the current status of equipment ... and the bus model" and reconciling them
against the power-flow equations, so that it "can correct 'bad data' and
calculate missing data in the model" (M11 p.66 § 2.6). Among the outputs it
supplies to RT SCED, "typically available every minute", are **bus loads**,
actual generator MW output, tie-line flows, MW losses by transmission zone,
and actual MW flow on any constrained facility (M11 p.67 § 2.6). M12
concurs: "SE is used to provide the input to the market systems" (M12
p.13).

So the quantity dispatch optimizes against is a **model-reconciled,
bus-level** load estimate, combined with the **look-ahead load forecast**
described above — not a raw meter reading, and not a zonal total.

**Consequence for our Z.** `dom_load_mw` is a *zonal* feed. Congestion
responds to the spatial pattern of *nodal* injections and withdrawals
against specific constraints (§ 3). A given zonal ramp can be distributed
across buses in ways that load the Loudoun-area constraints heavily or
barely at all, and the zonal aggregate cannot distinguish them. This is a
granularity mismatch between exposure and response that no amount of
statistical power fixes; it is independent of, and additional to, the
missing ramp-rate price channel in § 9. The second half of this question —
what the gridstatus `pjm_load.dom` column reports — is settled in
`docs/sources/gridstatus-api-constraints.md` (line 131) and the 2026-07-17
`dom`-as-DOM disclosure decision, and is not re-litigated here.

## §6 Reserve structure

### Requirements are set by contingency size, not by load

> "PJM models a reserve requirement at the RTO and sub-zonal level in whole
> MW for each hour of the operating day **based on the greatest MW loss of
> all potential Largest Single Contingencies on the system**." (M11 p.120 § 4.3)

In Real-time the Largest Single Contingency is "normally the higher of [max
of (the largest online generator's output or Economic Maximum) or the sum
of the higher of (Economic Maximum values or outputs of an active reserve
group)]" (M11 p.121 § 4.3). An active reserve group is a station over 800
MW with a single outlet or common fault exposure.

The primary driver is therefore **supply-side**: how big the biggest
losable thing is.

### But two channels do link load *level* to the requirement

1. **Indirect and continuous.** Because the RT Largest Single Contingency
   is the largest *online* generator's output or Eco Max, committing more
   and larger units at high load can raise the requirement.
2. **Direct but administratively gated.** M11 p.122 § 4.3:

   > "At times, anticipated heavy load conditions may result in PJM
   > operators carrying additional reserves to cover increased levels of
   > operational uncertainty. PJM may extend the 30-Minute Reserve, Primary
   > Reserve and Synchronized Reserve Requirements in the Market Clearing
   > Engine **during the on-peak period** in order to incorporate these
   > actions in Energy and Reserve Pricing **when a Hot Weather Alert, Cold
   > Weather Alert or an escalating emergency procedure ... has been issued
   > for the Operating Day**."

   The extension flows into Step 2 of every reserve demand curve (§ 7).

Both channels are keyed to **load level**, not to load *ramp rate*.
Channel 2 is additionally gated on a **weather alert** — which is a direct
input to the attribution problem (workstream B); see § 9.

M12 states the general principle: "Reserves are additional capacity above
the expected load. Scheduling excess capacity protects the power system
against the uncertain occurrence of future operating events, including the
loss of capacity or load forecasting errors" (M12 p.33).

### Reserve sub-zones

Sub-zones exist so that deploying 100% of reserves will not overload PJM
transfer interfaces (M11 p.122 § 4.3.1). Critical operational facts:

- **"While PJM can model multiple sub-zones, only one will be active at any
  given time."** (M11 p.122 § 4.3.1)
- The active sub-zone is determined **day-ahead**, with intraday changes
  possible on an exception basis; participants are notified via Markets
  Gateway (M11 p.123 § 4.3.2).
- New sub-zones are defined from reactive transfer interfaces (AP South,
  BED-BLA), 230 kV+ actual overloads, or contingency overloads exceeding
  the load dump limit on a 230 kV+ facility (M11 p.123 § 4.3.2).
- The bus-level membership list is **not in the manual**. It is published
  quarterly at `https://www.pjm.com/markets-and-operations/ancillary-services`
  (M11 p.123 § 4.3.1).

**Is DOM inside the MAD sub-zone? Not established from these sources.** RSP
confirms MAD exists as a reserve sub-zone and had simultaneous SR and PR
shortages with the RTO on 2021-03-17 (RSP p. 6). M11 p.161 refers to "the
RTO, Mid-Atlantic Dominion or Mid-Atlantic regions" — but that is an
*emergency-procedure / weather-alert region*, a different object from a
reserve sub-zone, and it does not establish membership. Recorded in § 10.

## §7 Reserve demand curves, penalty factors, and caps

### The demand curves — and a correction to our figures

M11 p.124 § 4.3.3 defines the curves. Separate curves exist for six
product × location combinations: RTO and Active Sub-Zone, each for
Synchronized Reserve, Primary Reserve, and 30-Minute Reserve.

> "The demand curves for each of these products and locations are similar
> in that they **share the same penalty factors on the Y axis**; however,
> the desired reserve levels on the X axis differ." (M11 p.124 § 4.3.3)

- **Step 1:** Penalty Factor = **$850/MWh**; Desired Reserve MW =
  locational Reliability Requirement.
- **Step 2:** Penalty Factor = **$300/MWh**; Desired Reserve MW =
  requirement **+ 190 MW +** any additional reserves carried in
  anticipation of heavy load conditions (§ 6).

**$850 and $300 are the two steps of every reserve demand curve — they are
not product-specific values.** Our docs describe them as "$850/MWh
Synchronized Reserve, $300/MWh Primary Reserve" (see § 9, Correction 2).
That mis-assignment is understandable — RSP's worked example happens to
have SR clearing at Step 1 ($850) and PR at Step 2 ($300) in that
interval — but it is not the definition.

The penalty factor is both a shortage valuation and a **procurement price
cap**: "the price at which reserves will be valued if the desired reserve
MW cannot be met" and "also acts as a price cap beyond which reserves will
not be procured through market clearing" (M11 p.124 § 4.3.3). Resources
above it can still be committed manually and made whole after the fact.

It also functions as a **scarcity gauge**: "As the price of a reserve
product increases to a value near the penalty factor, it indicates to
market participants that the system is nearing a reserve shortage" (M11
p.125 § 4.3.3).

### Energy offer caps

- "the applicable marginal Incremental Energy Offer used in the calculation
  of Real-time Prices **shall not exceed $2,000/MWh**" (M11 p.68 § 2.7.1).
- Cost-based offers above $2,000/MWh are "dispatched in economic merit
  order but are capped at $2,000/MWh for the purposes of calculating LMP"
  (M11 p.70 § 2.7.4).
- Composite Energy Offers between $1,000 and $2,000/MWh get reasonableness
  verification (M11 p.69 § 2.7.3); above $2,000/MWh, components are
  adjusted down to the cap (M11 pp. 70–71 § 2.7.5).
- All Fast-Start resources except self-scheduled non-followers are eligible
  to set LMP (M11 p.69). Offer-capped resources remain eligible to set LMP
  (M11 p.49).

### Administrative pricing in emergencies

M11 § 2.15 sets LMP by rule when power balance fails: successively to the
highest online generation offer, the highest cut price-sensitive demand
bid, and finally — under proportional load reduction — "the highest offer
price of all online generation, the price from Step 3, or the bid cap
(presently $2,000/MWh), whichever is higher" (M11 p.80 § 2.15). § 2.16
handles minimum-generation excess, setting LMP to zero or below.

De-energized buses inherit neighbours' LMPs via a Dijkstra least-impedance
search (M11 p.69 § 2.7.2).

---

# Part 2 — Mapping to this project

## §8 Panel column → mechanism map

Panel: `data/interim/analysis_panel_5min.parquet`, 350,789 rows,
2023-02-07 → 2026-06-24.

| Column | Mechanism | Notes |
|---|---|---|
| `system_energy_price_rt_*` | § 2 | **Locationally uniform across our 3 pnodes** (max diff 9.09e-13). Carries scarcity via lost opportunity cost. Capped $3,700/MWh. |
| `congestion_price_rt_*` | § 3 | Σ(Dfax × shadow price). Shadow price capped at the penalty factor, $2,000/MWh RT default, **operator-adjustable**. May also carry a portion of reserve penalty factors. |
| `marginal_loss_price_rt_*` | § 4 | Locational; ±$22.60 spread observed. Referenced to distributed load reference bus. |
| `total_lmp_rt_*` | § 1 | Sum of the three. |
| `dom_load_mw` | § 5, § 10 | A **zonal** feed. Dispatch prices against state-estimator **bus** loads plus a forecast for the look-ahead interval, not this series. See § 10. |
| `dom_load_gradient_abs_mw_per_min` (Z) | § 6, § 9 | No mechanism in M11/M12 prices ramp rate directly. See § 9. |
| `interval_start_utc` | § 5 | PJM's price targets the **interval end**. Alignment unverified — § 10. |
| `passes_proposal_filter` | — | Dropped 2026-07-29 (advisor + the 99.1%-exclusion diagnostic). |

## §9 Findings ledger

### The headline: the mechanism chain's first link has no primary-source support

`docs/plans/2026-05-11-phase-transition-methodology.md` (lines 52, 289)
asserts the chain

```
load volatility → reserve depletion → ORDC trigger → LMP spike
```

Audited link by link:

| Link | Status | Basis |
|---|---|---|
| load volatility → reserve depletion | **UNSUPPORTED** | M11 § 4.3 sets the requirement from the "greatest MW loss of all potential Largest Single Contingencies" — a supply-side contingency quantity. Nothing in M11 or M12 ties the requirement, or reserve depletion, to `dLoad/dt`. |
| reserve depletion → ORDC trigger | **SUPPORTED** | M11 § 4.3.3: deficient MW are valued at the Step-1/Step-2 penalty factor. |
| ORDC trigger → LMP spike | **SUPPORTED** | RSP pp. 4–8 worked example; M11 § 2.2 (both system energy and congestion may carry a portion). |

**Links 2 and 3 are sound. Link 1 is not** — for the scarcity path. The
channels that connect load to reserve *scarcity* (§ 6) run through load
**level** — the largest online unit's size, and the heavy-load requirement
extension — never through the ramp rate. Ramp constraints are also absent
from the price decomposition: § 1's three components are exhaustive, LPC's
objective treats "specific generator and Demand Resource operating
limitations" as constraints on the dispatch rather than as price components
(M11 p.67 § 2.7), and ramping enters only as a feasibility band on where a
unit can get to (M11 pp. 61–63). M11 p.83 corroborates in passing —
"Similar to other operational constraints (e.g. ramp rate limitations) the
shadow price of the generator output constraint will not be included in the
LMP" — though that sentence sits inside a Day-ahead stability-limit passage
and is an analogy, so it is supporting rather than primary evidence.

### There are two price channels, and they behave differently

Do **not** read the above as "load volatility has no channel to price." It
does. The two channels must be kept separate:

| | **Scarcity channel** | **Congestion channel** |
|---|---|---|
| Enters | System energy (as lost opportunity cost) | Congestion price |
| Locational? | **No** — identical across our 3 pnodes (§ 2) | **Yes** |
| Driven by | Reserve shortage vs. a contingency-set requirement (§ 6) | Physical flows on binding constraints (§ 3) |
| Ramp-rate channel? | **None found** in M11/M12 | **Yes** — see below |
| Magnitude | Up to the $3,700/MWh cap | Shadow price ≤ penalty factor, $2,000/MWh RT default |

The congestion channel does respond to changing consumption. M11 § 2.2
defines the Congestion Price as the effect on transmission congestion costs
associated with "increasing the output of a generation resource or
decreasing the **consumption** by a Demand Resource, based on the effect of
increased generation from or **consumption by** the resource **on
transmission line loadings**" (M11 p.22). A load ramp is a change in
consumption; changed withdrawals change flows; changed flows change
congestion. There is no mechanical basis for asserting that ramps cannot
move congestion prices.

**So what was actually established:**

1. Ramp rate has **no channel into the scarcity → system energy path**, and
   that path is also locationally uniform — it can carry no
   Loudoun-specific content whatever.
2. Ramp rate **does** have a channel into congestion, the locational
   component. That is precisely where a local data-center effect could live.

**Reading sub-q1's results through this split.** The tail-risk nulls were
computed on `total_lmp > $250` — a threshold that the scarcity channel
dominates, since congestion is capped far below the levels the scarcity
adder reaches. Those nulls are therefore the correct answer *for the
scarcity channel*, and they close the ORDC-threshold framing the proposal
was built on. They do **not** speak against the congestion channel. The
QR-full positive z_slope on congestion at τ=0.90/0.95 is the surviving
positive finding, and it is the one most likely to reflect a genuine local
effect. Workstream A should treat it as the live thread, not as noise left
over from a failed test.

### Per-finding ledger

| Finding | Mechanism verdict |
|---|---|
| **Spec A median-split rejection** (heavier tail at LOW Z, hourly congestion, shape_diff −0.18, CI excludes 0) | **Still unexplained — and the scarcity story does not explain it.** Spec A's response was `congestion_price_rt_cluster_mean`, so this is a congestion-channel result. Scarcity cannot produce it: scarcity lands mostly in system energy, which is uniform across our pnodes (§ 2) and so cannot generate a Z-dependent *congestion* tail in either direction. A congestion-channel explanation would have to say why low-Z intervals produce heavier-tailed congestion. The plausible candidate is that congestion magnitude tracks flow *level* on binding constraints, and low Z pools sustained high-load plateaus (high flows) with flat overnight periods (low flows) — but that is a hypothesis, not established, and the supporting load × Z evidence we have is on `total_lmp`, not congestion. Mark unexplained; do not carry forward any "scarcity at low Z" reading. |
| **Spec B continuous ξ(Z) underpowered** | **Response variable is defensible but not sufficient.** Congestion is one of only two locational components (§ 2), so it was the right primary spec for a *local* effect. But it is not where scarcity mainly lands, and its shadow price is capped at $2,000/MWh and operator-adjustable (§ 3) — a compressed, partly discretionary signal. Underpowered is the expected outcome. |
| **QR-full moderate-τ positive z_slope** (5/7 pnodes, τ=0.95, year-FE) | **Not a scarcity signal.** Scarcity enters via lost opportunity cost in the system energy component, which is *identical* across our pnodes (§ 2) — so it cannot produce a pnode-varying congestion slope. What remains is genuine transmission congestion: ramps redistribute injections and shift flows across the Loudoun-area constraints. This is the finding most likely to be about real congestion rather than scarcity. |
| **Item #6 / decile null** | **Scope failure, now doubly explained.** The filter retained 71 of 7,680 tail events (99.1% excluded). *And* the exposure variable had no price channel. Both defects point the same way. |
| **Level-vs-volatility + plateau** (P(exceed) 0.0015→0.1418 across load deciles, ~95×; falls with \|Z\| inside the top load quintile) | **Level channel SUPPORTED; plateau channel PARTIALLY supported.** § 6 gives two mechanisms by which load level raises scarcity risk. It does *not* give a mechanism by which a sustained plateau prices above a fast ramp *per se* — the plateau result follows from ramp rate having no channel *into scarcity* while level has two, rather than from anything privileging flatness. Reframe as "on the scarcity channel, level prices and volatility does not" — the response was `total_lmp > $250`, which the scarcity channel dominates. This says nothing about the congestion channel, where volatility does have a mechanism. |

### Input to workstream B (attribution)

The direct load→requirement channel is gated on a **Hot Weather Alert,
Cold Weather Alert, or escalating emergency procedure**, and applies only
during the **on-peak period** (M11 p.122 § 4.3). PJM has written the
weather dependence into the mechanism itself. Any claim that data-center
load growth drives scarcity pricing has to contend with the fact that the
requirement extension is triggered by *weather*, not by load composition.
This sharpens rather than resolves the attribution problem the advisor
raised, and it is a citable constraint for that discussion.

### Corrections to existing docs

**Correction 1 — congestion is not blind to reserve penalties.**
`docs/plans/2026-05-11-phase-transition-methodology.md:145` states the
penalty "lands in system energy LMP rather than in the congestion
component." M11 p.22 § 2.2 applies the same qualifier to both: the
Congestion Price "may include a portion of the defined reserve penalty
factors should a reserve shortage exist." The stated reason for preferring
`total_lmp` as the ORDC-mechanism target is therefore wrong. The *choice*
survives on a different basis (`total_lmp` includes the component where
scarcity mainly lands), but the reasoning must be restated. The allocation
rule between components is unknown — § 10.

**Correction 2 — the $850/$300 characterization.**
Line 38 describes "ORDC penalty factors ($850/MWh Synchronized Reserve,
$300/MWh Primary Reserve)". The figures are right; the assignment is not.
M11 § 4.3.3: $850 is **Step 1** and $300 is **Step 2** of *every* reserve
demand curve, and all six product × location curves "share the same
penalty factors on the Y axis." Neither number belongs to a product.

**Correction 3 — $850 is not a meaningful LMP threshold.**
`docs/plans/2026-05-14-jlarc-napkin-projection.md` and
`docs/plans/2026-05-14-jlarc-rpt598-key-figures.md:161` use $850 as an LMP
exceedance benchmark ("hours/year above $850 LMP benchmark"). $850 is a
penalty factor on a *reserve* demand curve, denominated in reserve
$/MWh. It reaches LMP only after being multiplied by the marginal
resource's loss factor and summed across shorted products and zones — RSP's
example turns Step-1 and Step-2 penalties into $2,401.16/MWh of lost
opportunity cost (RSP p. 6). There is no mechanical reason for LMP = $850
to mark "ORDC is biting." The napkin math already found the $850 benchmark
empirically uninformative; this supplies the reason, and it is a stronger
one. Any ORDC-anchored LMP benchmark should be derived from the penalty
stack the way RSP derives it, or abandoned for a quantile anchor.

**Not a correction — the uniformity premise.** The design spec flagged
"system energy is uniform across pnodes" as an unverified premise that had
been overstated as established. It is now **verified empirically** for our
three pnodes (§ 2), scoped to those pnodes rather than RTO-wide. Its
consequence stands: within our cluster, a local effect can appear only in
congestion or marginal loss.

## §10 What primary sources do not answer

1. **The reserve-penalty allocation rule between components.** M11 says
   both System Energy Price and Congestion Price "may include a portion" of
   the reserve penalty factors. Neither M11 nor RSP gives the split. *Would
   settle it:* the Operating Agreement Schedule 1 pricing formulation, or
   PJM's market-clearing engine formulation documents.
2. **MAD sub-zone membership — is DOM in it?** § 6. Still open, but the
   path is now exact. The ancillary-services page M11 § 4.3.1 points to does
   **not** list sub-zones inline; it links two Data Miner 2 feeds that carry
   the mapping (checked 2026-07-29):
   - `sync_pri_reserves_buses_list` — "Reserve Subzone Bus Mapping"
   - `sync_pri_reserves_resources_list` — "Reserve Subzone Resource Mapping"

   Neither is fetchable from this machine as-is: Data Miner 2's browser is a
   JS app that returns an empty shell to a plain fetch, and its API host
   `api.pjm.com` NXDOMAINs on NU DNS (the documented `/etc/hosts` workaround
   applies — `www.pjm.com` and `dataminer2.pjm.com` resolve fine). *Would
   settle it:* one authenticated `sync_pri_reserves_buses_list` pull with
   that workaround in place, filtered for DOM-zone buses.

   Note this is a **sub-zone bus mapping**, so it also answers a sharper
   question than "is DOM in MAD": which *specific* buses are, and whether
   our three cluster pnodes are among them.
3. **Which sub-zone was active on a given day.** Only one is active at a
   time, set day-ahead (M11 § 4.3.1). Our panel has no such column, so
   sub-zonal scarcity episodes cannot currently be identified. *Would
   settle it:* Markets Gateway postings, or a Data Miner 2 feed if one
   exists.
4. ~~**Timestamp alignment between the gridstatus feed and PJM's target
   time.**~~ **RESOLVED 2026-07-29 — see § 5, "How this aligns with our
   panel."** gridstatus `interval_start_utc` ≡ PJM interval-beginning
   (established by the perfect-temporal-alignment equivalence check), and
   PJM's price targets the interval end, so a row labeled `t` carries the
   price computed for `t + 5 min`.
5. **The untested lag direction.** The 2026-07-29 diagnostic tested
   *price-lags-Z* (`Y_lead{k}`, k = 0…6), which — given item 4's
   resolution — pushed the price progressively *past* the end of the ramp
   window. The mechanically plausible direction is the opposite:
   forecast-based dispatch over a ten-minute look-ahead (§ 5) means price on
   row `t` embeds expected load out to roughly `t+10`–`t+15`. **Workstream A
   should pair price at row `t` against Z on rows `t+1` and `t+2`** —
   i.e. `Z_lead{k}`, not `Y_lead{k}`. This is untested in either the hourly
   or 5-min work.
6. **Operator penalty-factor adjustments and load bias.** Both are
   discretionary and real-time (§ 3, § 5). Neither is recoverable from our
   panel, and both inject non-physical variation into congestion prices.
7. **Which physical constraints bind near Loudoun.** Deliberately out of
   scope for this workstream. M03 gives the limit *types*; constraint
   identification would need Data Miner 2 binding-constraint feeds.

---

# Appendix — verbatim quotes for load-bearing claims

**A1. Three-component decomposition, and both components carrying reserve
penalties** (M11 p.22 § 2.2):

> "The LMP calculation determines the full marginal cost of serving an
> increment of load at each bus from each resource associated with an
> eligible energy offer as the sum of three (3) separate components of LMP.
> ... ◦ System Energy Price – This is the price at which the Market Seller
> has offered to supply an additional increment of energy from a generation
> resource or decrease an increment of energy being consumed by a Demand
> Resource. The System Energy Price may include a portion of the defined
> reserve penalty factors should a reserve shortage exist. ◦ Congestion
> Price – This is the effect on transmission congestion costs (whether
> positive or negative) ... The Congestion Price may include a portion of
> the defined reserve penalty factors should a reserve shortage exist."

Scope note, same page, immediately above: "The Real-time LMP is calculated
based on the approved security constrained economic dispatch solution for
the target dispatch interval as described in Section 2.7 of this Manual."

**A2. 5-min price is a spot value at the interval end** (M11 p.67 § 2.7):

> "Real-time LMPs and Regulation and Reserve Clearing Prices are derived
> from the inputs of the latest approved Real-time Security Constrained
> Economic Dispatch (RT SCED) program solution, referred to as the
> reference case, for the target time at the end of the current five (5)
> minute interval. ... The Real-time LMPs and Regulation and Reserve
> Clearing Prices calculated by LPC are applied to each five (5) minute
> Real-time Settlement Interval ending at the LPC target time."

**A3. Dispatch runs on forecast, not current conditions** (M12 p.25):

> "The RT SCED cases use the load forecast and other relevant system
> information for the look-ahead interval, rather than the time at which
> the case is executing, to achieve a dispatch solution that will
> adequately control for those forecasted conditions."

**A4. Reserve requirement set by largest contingency** (M11 p.120 § 4.3):

> "PJM models a reserve requirement at the RTO and sub-zonal level in whole
> MW for each hour of the operating day based on the greatest MW loss of
> all potential Largest Single Contingencies on the system."

**A5. Heavy-load requirement extension, weather-gated** (M11 p.122 § 4.3):

> "At times, anticipated heavy load conditions may result in PJM operators
> carrying additional reserves to cover increased levels of operational
> uncertainty. PJM may extend the 30-Minute Reserve, Primary Reserve and
> Synchronized Reserve Requirements in the Market Clearing Engine during
> the on-peak period in order to incorporate these actions in Energy and
> Reserve Pricing when a Hot Weather Alert, Cold Weather Alert or an
> escalating emergency procedure (as defined in PJM Manual 13: Emergency
> Operations) has been issued for the Operating Day."

**A6. $850 / $300 are curve steps shared across all products** (M11 p.124
§ 4.3.3):

> "The demand curves for each of these products and locations are similar
> in that they share the same penalty factors on the Y axis; however, the
> desired reserve levels on the X axis differ to reflect the Reserve
> Requirement differences amongst the reserve products and locations. These
> demand curves are defined as follows: • Step 1: ◦ Penalty Factor =
> $850/MWh ◦ Desired Reserve MW = locational Reliability Requirement for
> the specified reserve product ... • Step 2: ◦ Penalty Factor = $300/MWh
> ◦ Desired Reserve MW = locational Reliability Requirement ... plus 190 MW
> plus any additional reserves that are being carried in anticipation of
> heavy load conditions."

**A7. Shadow price is set by, and capped at, the penalty factor** (M11
p.81 § 2.17):

> "If the flow on the constraint cannot be controlled below the level to
> which dispatch is attempting to control the facility it results in a
> constraint violation in the MCE optimization. The transmission constraint
> penalty factor is then used to set the marginal value of the violated
> transmission constraint. ... All PJM internal constraints, regardless of
> voltage level, are defaulted to a $2,000/MWh transmission penalty factor
> in the Real-time Energy Market."

**A8. Congestion arithmetic** (RSP p. 5):

> "Cost of impact on constraint control = Additional energy needed from
> marginal resource * sum (ABS (Σ Dfax * constraint shadow price)) =
> 1.0474 MW * (($2,000/MWh * 0.73254) + ($2,000/MWh * 0.00623)) =
> $1547.57/MWh"

**A9. Scarcity enters system energy as lost opportunity cost, and the cap**
(RSP pp. 6, 8):

> "Finally, the impact of converting a megawatt of assigned reserves on the
> marginal resource to energy to serve the next megawatt of load is
> reflected in the system energy LMP. This is referred to as the lost
> opportunity cost."

> "Post Reserve Price Formation in the MCE, the system energy LMP is
> administratively capped at $3,700/MWh. The iterative process described
> above in the Pre-Reserve Price Formation section is no longer utilized."

**A10. Real-time energy offer cap** (M11 p.68 § 2.7.1):

> "For purposes of calculating Real-time Prices, the applicable marginal
> Incremental Energy Offer used in the calculation of Real-time Prices
> shall not exceed $2,000/MWh."

**A11. Only one reserve sub-zone active at a time** (M11 p.122 § 4.3.1):

> "While PJM can model multiple sub-zones, only one will be active at any
> given time."
