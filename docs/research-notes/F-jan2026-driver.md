# January 2026 PJM/DOM price escalation — candidate drivers

Research date: 2026-08-07. Web research only (no repo changes).

Context restated: 5-min panel (Feb 2023–Jun 2026, Loudoun County VA pnodes) shows a
step change dated January 2026 — congestion p90 $20.46 → $231.29 and system-energy
p90 $86.32 → $292.19, simultaneously. P(congestion > $100) at fixed 20–22 GW load
jumped from ~5% (2024/2025) to ~37% (2026).

---

## 1. Weather: Winter Storm Fern / the January–February 2026 North American cold wave

- **Event window:** Jan 21–30, 2026 (part of the broader "January–February 2026 North
  American cold wave"), with the most severe stretch Jan 23–27 and extreme cold lingering
  through Feb 1–2. PJM named this event **Winter Storm Fern**.
  [Wikipedia: January–February 2026 North American cold wave](https://en.wikipedia.org/wiki/January%E2%80%93February_2026_North_American_cold_wave)
- **Alerts/emergency actions (PJM Inside Lines, "Jan. 25 Update on PJM Cold Weather
  Operations"):**
  - Cold Weather Alert issued in advance, extended through Feb 1.
  - **Conservative Operations** declared Jan 24–Feb 1 (maintenance-outage recalls,
    increased reserve requirements — operationally relevant to the congestion story, see §3).
  - **Pre-Emergency Demand Response** activated Jan 25 in **BGE, Dominion, and Pepco**
    service areas specifically to address **localized transmission constraints** — direct
    DOM-zone evidence during the event itself.
  - **DOE Section 202(c) emergency order** issued Jan 25 (effective through Jan 31,
    extended via order 202-26-02A through Feb 2) authorizing PJM generators to run at
    max output, waiving air-quality/fuel-shortage permit limits. 15 generators used this
    authority for 1,035 total hours, providing 5.2 GW.
  [Jan. 25 Update](https://insidelines.pjm.com/pjm-issues-precautionary-alerts-ahead-of-expected-cold-spell/) ·
  [DOE order 202-26-02](https://www.energy.gov/ceser/federal-power-act-section-202c-pjm-interconnection-pjm-order-no-202-26-02) ·
  [PJM 202(c) application](https://www.energy.gov/documents/pjm-202c-application-2026-01-24)
- **Load:** Forecast peak for Jan 27 was 147,200 MW (a potential all-time winter record).
  Actual outturn did **not** break PJM's all-time winter peak (143,700 MW, set Jan 22,
  2025), but PJM ran hourly loads of 130 GW+ for **8 consecutive days** (Jan 26–Feb 2) —
  "a first for the winter season" — with a highest single value of 139.05 GW.
  [PJM Reviews January Cold Weather Operations](https://insidelines.pjm.com/pjm-reviews-january-cold-weather-operations/)
- **Generator outages — the key severity marker:** PJM's fleet averaged **18–19 GW of
  outages** during the event (peaking 19.7 GW on Jan 26), versus only **12–13 GW**
  during the comparable January 2025 cold snap, and versus a **15.9 GW** seasonal
  forecast. "Plant equipment failures were by far the most commonly cited cause." This
  is the single best evidence that Jan 2026 was mechanically more severe for the supply
  stack than the Jan 2025 event, despite similar or lower peak loads.
- **Gas-electric coordination failure:** "Gas-electric market misalignment" produced
  **~$798 million** in out-of-market uplift costs Jan 24–Feb 1 (PJM Inside Lines).
- **Realized prices during the event:** Day-ahead prices rose to a peak **>$1,800/MWh**
  the morning of Jan 26; PJM spot wholesale spiked **above $3,000/MWh** the morning of
  Jan 25; **real-time wholesale in Dominion's Virginia market shot past $1,800/MWh**
  specifically. Forced outages peaked at 19.7 GW on Jan 26 (~16% of average storm load).
  [ts2.tech: Winter Storm Fern jolts prices above $1,800](https://ts2.tech/en/winter-storm-fern-jolts-u-s-power-prices-above-1800-as-pjm-outages-jump/)

**Channel:** (a) system-energy — via extreme gas-price pass-through (§2) and record
outage-driven scarcity; (c) congestion — via the explicit DOM/BGE/Pepco pre-emergency
DR activation for localized transmission constraints, and via operator-conservative
transmission control limits during Conservative Operations (§3). **Both.**

---

## 2. Natural gas: Henry Hub and the mid-Atlantic

- **Henry Hub all-time high: $30.72/MMBtu on January 23, 2026** (EIA data). Other price
  services logged similar extremes: Argus Media $28.00/MMBtu Jan 26 peak, retreating to
  $12.00 Jan 27; a separate industry recap cites an all-time daily record of
  **$30.565/MMBtu on Jan 26**. January 2026 averaged **$7.72/MMBtu** at Henry Hub, then
  collapsed to **$3.62/MMBtu in February** — confirming this was a sharp, short-lived
  spike, not a sustained gas-price plateau.
  [EIA Today in Energy #67046](https://www.eia.gov/todayinenergy/detail.php?id=67046) ·
  [IE News Q1 2026 Energy Market Recap PDF](https://www.integrityenergy.com/wp-content/uploads/2026/05/IE-News-Q1-2026-Energy-Market-Recap.pdf)
- **Storage drawdown:** Record **360 Bcf withdrawal** for the week ending Jan 30, 2026,
  part of ~2,020 Bcf withdrawn over the winter season — evidence of genuine physical
  tightness, not just financial/basis noise.
- **EIA revised its 2026 Henry Hub forecast up ~23–40%** in the February STEO in direct
  response to the storm (Feb $4.60, March $4.12 vs. January STEO's much lower figures).
  [EIA STEO Feb 2026](https://www.eia.gov/outlooks/steo/archives/Feb26.pdf) ·
  [PA Environment Digest recap](http://paenvironmentdaily.blogspot.com/2026/02/us-eia-increases-natural-gas-price.html)
- **Mid-Atlantic-specific basis (TETCO M3 / Transco Zone 5):** Could not find a clean,
  dated TETCO M3 or Transco Zone 5 basis series for the Jan 22–27 window in this search
  session — this is a **gap**, not a null result. One tangential item: AEGIS Hedging
  references a **TETCO M2** basis extreme around Jan 26, 2026, but the source page
  content did not resolve into readable specifics under WebFetch, and a related
  "Feds Force TETCO to Reduce Flow" AEGIS article that looked promising turned out to
  be a **2021** event (PHMSA permit denial, unrelated to 2026) — flagging this so it is
  not mistaken for a 2026 finding. Recommend a follow-up pull directly from Natural Gas
  Intelligence's TETCO M3 / Transco Zone 5 daily snapshot pages if basis-specific
  confirmation is needed.
  [NGI Transco Zone 5 daily](https://naturalgasintel.com/data-snapshot/daily/NEATRANZ5/)

**Channel:** (a) system-energy — this is the primary mechanism. Because gas sets the
marginal price for most PJM hours and Henry Hub is a national reference price, an
$8–30/MMBtu gas spike raises the RTO-wide marginal energy price roughly uniformly
(before congestion/losses), which is exactly the mechanism needed to explain a
PJM-wide, locationally-uniform system-energy tripling. **Primarily (a).**

---

## 3. PJM market events — Monitoring Analytics IMM reports (PRIMARY EVIDENCE)

Pulled directly from the **2026 Q1 (Jan–Mar) Quarterly State of the Market Report for
PJM**, published by Monitoring Analytics (the PJM Independent Market Monitor) on
May 14, 2026 — the single most load-bearing source in this research. Full text scraped
to `research/q1-2026-som-sec1.md` in this scratchpad.
[Report PDF](https://www.monitoringanalytics.com/reports/PJM_State_of_the_Market/2026/2026q1-som-pjm-sec1.pdf)

### Headline price move
- RT load-weighted average LMP, Q1 2026 vs Q1 2025: **$52.20 → $87.57/MWh (+$35.37,
  +67.8%)**.
- **Decomposition of the $35.37/MWh increase:**
  - **$14.92/MWh (42.2%) — fuel & consumables cost component** → system-energy channel.
  - **$9.73/MWh (27.5%) — transmission constraint penalty factor component** →
    congestion channel.
  - $3.56/MWh (10.1%) — markup/maintenance/10% adder (market power) components.
  - $1.26/MWh (3.6%) — emissions cost components.
  - $0.85/MWh (2.4%) — scarcity component.
  - +$0.18/MWh — pre-emergency DR strike prices called during Winter Storm Fern.
  - −$0.03/MWh — effect of the $3,700/MWh administrative offer cap (a pre-existing,
    unchanged parameter — no evidence of an ORDC or offer-cap rule change effective
    around Jan 2026).

This decomposition is a near-exact structural match to the panel's finding: **both**
components moved together, fuel cost (system-energy) contributing the larger absolute
share and transmission congestion the second-largest.

### Timing: January was the spike month
- Monthly total PJM congestion costs in Q1 2026 ranged from **$171.4M in March** to
  **$1,205.7M in January** — January alone was ~60% of the entire quarter's $2,015.2M
  congestion total. Total congestion costs rose **+300.4% YoY** ($503.3M → $2,015.2M).
- Marginal loss costs followed the same January-heavy pattern ($517.4M in January vs.
  $94.3M in March).
- Of 86 five-minute shortage-pricing intervals in Q1 2026, **40 occurred during cold
  weather from late January into early February, including Winter Storm Fern.**

### DOM zone specifically flagged as the congestion epicenter
> "**Zonal Congestion.** DOM had the highest zonal congestion costs among all control
> zones in the first three months of 2026. DOM had $356.7 million in zonal congestion
> costs, comprised of $407.7 million in day-ahead congestion costs and -$51.0 million
> in balancing congestion costs."

This directly corroborates that the congestion channel's step was **concentrated in
DOM**, not spread evenly across PJM — consistent with the panel being built on Loudoun
County (DOM) pnodes.

### Why congestion jumped so much: an operational/administrative mechanism, not (only) a physical grid event
This is the most important — and most actionable — finding in this research. The MMU
attributes the bulk of the transmission-constraint-penalty-factor spike to **PJM
operators' discretionary reduction of "control limits"** (the line ratings actually
used in real-time SCED dispatch) below the physical line limits:

> "In the first three months of 2026, the control limit used in RT SCED for 94 percent
> of violated transmission constraint intervals was less than 100 percent of the actual
> line limit, with an average reduction of 5.5 percent. If the control limits had not
> been artificially reduced for PJM transmission constraints and everything else
> remained unchanged, the transmission constraint penalty factor's contribution to the
> load-weighted average LMP in the first three months of 2026 would have decreased by
> 99.4 percent from $13.76 to $0.08 per MWh."

Key nuance: this MMU criticism of "manual and automated discretionary reductions in
control limits" is a **longstanding complaint, first reported in 2015** — it is not a
brand-new January 2026 rule change. What appears to have changed is the *intensity/
frequency of use* of this discretion, plausibly a defensive operator response to the
record-severe outage environment (18–19 GW average outages, see §1) and to the
post-Winter-Storm-Elliott institutional posture of leaning conservative during extreme
cold. The MMU explicitly recommends PJM "end the practice" and calls transmission
constraint penalty factors "the second largest determinant of LMP after the marginal
cost of gas."

### Root-cause framing offered by the IMM itself
The MMU's own summary op-ed frames the quarter as: fuel costs (Winter Storm Fern →
gas price spike) plus PJM's own administrative transmission-constraint-penalty
practices, compounding on top of a structurally tight system driven by data-center
load growth (pivotal-supplier frequency up from 87.8% of days in Q1 2025 to 90.0% of
days in Q1 2026; capacity auctions clearing at the FERC price cap for three consecutive
delivery years). The energy market itself was still assessed as "competitive"; the
capacity market was not.

### Annual 2025 report (context, published Mar 12, 2026)
2025 RT load-weighted average LMP: **$33.74 → $50.73/MWh (+50.4% YoY)** — shows the
elevation trend was already underway pre-2026, but the magnitude of the 2026 Q1 jump
(+67.8% YoY on top of that) is distinctly larger, consistent with a discrete step in
January rather than pure trend continuation.
[2025 Annual SOM Vol. 1](https://www.monitoringanalytics.com/reports/PJM_State_of_the_Market/2025/2025-som-pjm-vol1.pdf)

**Channel: both**, with a clean, source-attributed split (fuel = system-energy;
transmission constraint penalty factor = congestion, concentrated in DOM).

---

## 4. DOM-specific: transmission, load growth, generation

- **No specific DOM transmission-line outage or generator-retirement event was found
  dated precisely to January 2026.** This is a genuine gap in available public
  reporting, not a ruled-out hypothesis.
- **Chronic, pre-existing NoVA transmission constraint (background condition, not a
  Jan-2026 trigger):** Loudoun/"Data Center Alley" has had a known transmission
  "pinch point" limiting new data-center interconnections since well before 2026.
  Near-term Dominion mitigation projects (reconductoring three 230 kV lines, a new
  500/230 kV transformer at Goose Creek, series reactors) were targeted at this
  constraint. DOM's 2025/26 capacity price cleared at **$444.26/MW-day** vs. PJM RTO's
  **$269.92/MW-day** — a direct locational-scarcity signal.
  [Data Center Frontier](https://www.datacenterfrontier.com/energy/article/11436951/dominion-resumes-new-connections-but-loudoun-faces-lengthy-power-constraints)
- **Load growth scale:** Loudoun County alone reported 5.33 GW of AI data-center
  electricity consumption in 2025, +166% from 2.0 GW in 2021. Virginia data-center
  power *requests* to Dominion total ~70,000 MW (3x Dominion's peak load) — but these
  are interconnection-queue requests, not evidence of a discrete January 2026
  energization event.
- **New DOM-area gas generation (Chesterfield 944 MW; proposed Mt. Storm/Grant County,
  WV additions) are all 2026–2027-and-later projects, not yet online in January 2026** —
  ruled out as an explanation for a January 2026 step (these would, if anything, relieve
  congestion once built, not cause it).
- **Persistence corroboration, DOM-specific, into Q2 2026:** A May 2026 congestion
  study by Gridraven's "Congestion Tracker" found PJM-wide grid congestion cost
  **~$1 billion in May 2026 alone**, with a binding constraint on the
  **Ashburn–Goose Creek 230 kV line** (May 26–29, 2026) generating **~$150 million in
  congestion costs in 72 hours** — Ashburn is inside the same Loudoun County study
  footprint as this project's pnodes. Dynamic line rating was estimated to have been
  able to save ~$100M of that in the same window, again pointing at *operational/rating
  conservatism* rather than a hard physical capacity shortfall as a contributing factor.
  [RenewableEnergyWorld](https://www.renewableenergyworld.com/power-grid/transmission/grid-congestion-cost-pjm-1-billion-in-one-month/)
- A June 2026 source also notes new RT constraints (MORRISVL-SPOTSLV 500 kV,
  AQUAHAR-CRANESCR 230 kV) with DOM-zone shift factors affecting the Western Hub from
  June 1–July 2, 2026 — further evidence the DOM congestion regime was still active
  into summer 2026.

**Channel:** (b) congestion, concentrated in and around the Loudoun/Ashburn corridor —
both as a chronic background condition that the January storm interacted with, and as
a channel that kept resurfacing (Ashburn–Goose Creek) months later.

---

## 5. Did it persist, or was January a spike?

**Verdict: level shift, with partial but incomplete mean-reversion.**

| Period | Evidence | Source |
|---|---|---|
| **January 2026** | RT price spikes to $1,800–3,000+/MWh during Fern; congestion $1,205.7M for the month (60% of Q1 total) | Monitoring Analytics Q1 2026 SOM |
| **February 2026** | RT prices averaged **$85/MWh, ~2x February 2025**; outliers $500–800/MWh; maintenance outages *tripled* to 7.8 GW; forced outages "remained elevated throughout, carrying forward from January's storm-driven peak" | [Modo Energy](https://modoenergy.com/research/en/pjm-bess-february-2026-regulation-revenues) |
| **March 2026** | Partial moderation: PJM peak load −11% MoM; East Hub DA on-peak avg $43.34/MWh, −19% MoM; Q1 quarterly monthly congestion low of $171.4M | Monitoring Analytics Q1 2026 SOM |
| **Jan–Apr 2026 (DOM specific)** | DOM RT averaged **$98.47/MWh**, a **40.9%** premium over RTO real-time average — up sharply from 2025's DOM RT $60.65/MWh vs. RTO $46.90/MWh (a ~29% premium) | [Amperon](https://www.amperon.co/blog/why-virginia-data-centers-matter-to-all-of-pjm) |
| **May 2026** | PJM-wide congestion ~$1B for the month; Ashburn–Goose Creek 230 kV binding constraint, $150M/72hrs | Gridraven Congestion Tracker |
| **June 2026** | PJM West Hub RT on-peak avg $112.15/MWh (+36% MoM, +212% vs. June 2021); new DOM-zone RT constraints active June 1–Jul 2 | S&P Global / gridstatus.io |

The February carryover is explicitly attributed (by the source, not by inference) to
outages "carrying forward" from January — i.e., the physical fleet did not fully
recover for weeks. March showed real moderation on load and DA price. But the DOM-zone
premium over RTO *widened* rather than reverting across Jan–Apr (29% → 40.9%), and
DOM-specific congestion events kept recurring at Ashburn–Goose Creek through May and
June. This is consistent with January acting as a **trigger that exposed and then
sustained a locational (DOM) supply-demand/transmission imbalance** that pre-existed
the storm, layered on top of a **transient** national gas-price shock that itself did
revert quickly (Henry Hub $7.72 → $3.62/MMBtu, Jan→Feb).

---

## Ranked assessment: what best explains a SIMULTANEOUS step in both components

**1. Winter Storm Fern (Jan 21–30, 2026) as the proximate trigger — explains (c) both.**
Record-adjacent PJM loads (130+ GW for 8 straight days) combined with the
**most severe forced-outage rate on record for a comparable event** (18–19 GW avg,
vs. 12–13 GW in Jan 2025) simultaneously (a) spiked the marginal cost of gas-fired
generation RTO-wide as Henry Hub hit an all-time $30.72/MMBtu, and (b) pushed PJM
operators into "Conservative Operations" with tighter, discretionary transmission
control limits, per the MMU's own decomposition ($14.92/MWh fuel + $9.73/MWh
transmission-constraint-penalty = ~70% of the entire quarterly LMP increase). This is
the best-evidenced, most proximate, and most temporally precise driver — it explains
*why January*, and Monitoring Analytics' own numbers show January contributed ~60% of
the entire quarter's congestion cost.

**2. DOM-zone-specific chronic transmission constraint (Loudoun/Ashburn "Data Center
Alley") as the reason the congestion channel localized so heavily in DOM — explains
(b) congestion, and explains why the step didn't fully revert.**
Monitoring Analytics independently confirms DOM had the *highest* zonal congestion
costs of any PJM control zone in Q1 2026. This is layered on a background condition
(NoVA data-center load growth outpacing transmission buildout, DOM capacity clearing
64% above RTO) that predates January 2026 and continued generating discrete congestion
events (Ashburn–Goose Creek, May 2026) for months afterward — explaining the observed
persistence/level-shift rather than a pure one-month spike.

**3. PJM's own operational posture (discretionary transmission control-limit
reductions) as an amplifier that turned a real physical stress event into an outsized
price event — explains (b) congestion specifically, and is the most actionable/
surprising finding.**
The MMU's own arithmetic (control limits below actual line limits for 94% of violated
constraint-intervals; congestion component would fall 99.4% if this practice stopped)
suggests a meaningful share of the congestion step was administrative/operational
choice rather than a hard physical capacity shortfall — this is a mechanism, not
independent of #1 and #2, but worth flagging separately since it means part of the
"unidentified driver" is a PJM market-operations practice, potentially even a policy
target rather than a structural grid fact.

**4. Natural gas price shock (Henry Hub $30.72/MMBtu, Jan 23) as the dominant explainer
of the system-energy channel specifically — explains (a) system-energy.**
This is well evidenced nationally (EIA) but the mid-Atlantic-specific basis data
(TETCO M3, Transco Zone 5) that would pin the mechanism down at the PJM/DOM level more
precisely was **not successfully retrieved** in this session — flagged as an open gap,
not a negative finding.

**Not supported / ruled out by available evidence:**
- No energy-offer-cap or ORDC/scarcity-pricing rule change effective around January
  2026 was found — the $3,700/MWh admin cap is unchanged and long-standing.
- No specific DOM generation retirement or new large-load energization dated to
  January 2026 was found; the DOM-area new-gas-plant pipeline (Chesterfield, Mt. Storm/
  Grant County WV) is all 2026–2027+ construction, not yet operational in Jan 2026.
- PJM's capacity-market price collar (FERC, extended April 2026) is a capacity-market
  mechanism and does not mechanically flow into RT energy or congestion pricing.

---

## Gaps / suggested follow-ups if more precision is needed
1. TETCO M3 / Transco Zone 5 daily basis series for Jan 20–30, 2026 specifically
   (NGI data-snapshot pages found but not scraped with dated values).
2. A DOM-zone-specific (not PJM-wide) LMP component decomposition from Monitoring
   Analytics — the Q1 2026 report gives PJM-wide and DOM total-congestion-cost figures
   but not a DOM-only fuel-vs-congestion LMP breakdown at the granularity of §3's
   PJM-wide table.
3. Confirmation of exactly which transmission facilities bound in DOM/Loudoun during
   Jan 21–30 specifically (the report's "Bedington Transformer / Pruntytown /
   Conastone-Northwest" list is the Q1-wide top-facility list, not confirmed as the
   January-specific binding set).
