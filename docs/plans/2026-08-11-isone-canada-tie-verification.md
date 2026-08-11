# Verification — does the Canadian interconnection explain ISO-NE's rising load volatility?

**Date:** 2026-08-11
**Question:** advisor, 2026-08-10 — "Is [New England's fluctuation] caused by New
England's connection to Canada's grid? One possible hypothesis is that if it is
connected, then Canada's renewable energy generation could be a source of this
fluctuation."
**Verdict: H_canada fails on three independent grounds — mechanism, geography,
and timing.** Every claim below is sourced; claims I could not verify are marked.

---

## 1. The complete set of New England external interfaces (primary source)

From ISO New England's **Available Transfer Capability Implementation Document
(ATCID) v1.0, effective 2011-04-01**, Tables 1–3 and Figure 1. This is an
enumeration, not a sample — the ISO states New England is "interconnected to
three neighboring Balancing Authority Areas."

| Interface (verbatim) | Shortname | Neighbor | Lands in |
|---|---|---|---|
| New England – New Brunswick | NE-NB | New Brunswick SO | **Maine** (east) |
| New England – Hydro Quebec via the Phase I/II HVDC Transmission Facilities | NE-HQ P2 | Hydro-Québec | **Massachusetts** (Sandy Pond, Ayer) |
| New England – Hydro Quebec via the Highgate Transmission Facility | NE-HQ HG | Hydro-Québec | **Vermont** (Highgate) |
| New England – New York-AC | NE-NY AC | NYISO | western MA / CT |
| New England – New York via Northport–Norwalk Harbor Cable | NE-NY NNC | NYISO | Connecticut |
| New England – New York via Cross Sound Cable | NE-NY CSC | NYISO | Connecticut |

**Rhode Island has no external interface of any kind.** That is now a verified
enumeration result, not an inference from absence.

Capacities, each independently sourced:

- **NE-NB:** "upgraded in 2007 from one to two alternating current ('AC')
  transmission facilities and supports a transfer capability of **1,000 MW from
  New Brunswick to New England and 550 MW from New England to New Brunswick**"
  (ATCID §3.1.1). Comprises the Keene Rd–Keswick (3001) and Orrington–Point
  Lepreau (390/3016) 345 kV ties.
- **NE-HQ P2:** ±450 kV HVDC, Radisson–Nicolet–Des Cantons to **Sandy Pond
  substation, Ayer, Massachusetts**; up to **2,000 MW** delivered at Sandy Pond.
  "In service since 1991" (ATCID §3.1.2); Phase I 1986 at 690 MW, Phase II 1992
  at 2,000 MW (Hitachi Energy; Hydro-Québec).
- **NE-HQ HG:** ~24 km, **120 kV**, Bedford substation (Montérégie, QC) to
  Highgate substation, northwest Vermont; **225 MW**; commissioned **1985**
  (Hydro-Québec).
- **NECEC:** **1,200 MW** HVDC, ~150 miles from Beattie Township on the ME–QC
  border to a converter station in **Lewiston, Maine**; commercial operation
  **2026-01-16** (U.S. EIA *Today in Energy* #67105; Avangrid; Maine DEP).
  Post-dates the ATCID, which is why it is absent from the table above.

---

## 2. Mechanism — the decisive objection, independent of any geography

**The dependent variable is metered demand. Interface imports are supply. They
are different quantities.**

`src/surg/preprocessing/isone_features.py` states: "Load is RT_Demand (metered
actual), not DA_Demand (day-ahead cleared)." The ISO-NE panel's
`load_mw_<zone>` is metered zonal demand.

The ATCID describes how imports enter the system (§2): "entities may submit
External Transactions to move energy into the New England Control Area… With
those External Transactions in place, the Real-Time Energy Market dispatches
internal generation in an economic, security constrained manner to meet
Real-Time load within the region."

Imports *serve* load. They do not *constitute* load, and they do not enter the
metered demand series. A fluctuating Canadian import displaces internal
generation; it does not move `RT_Demand` at all.

**This is precisely the contrast with the solar hypothesis.** Behind-the-meter PV
sits on the customer side of the revenue meter, so its output subtracts directly
from metered demand — a BTM mechanism *must* show up in this series, and a
transmission-interface mechanism *cannot*. H_canada is aimed at the wrong
variable.

---

## 3. Geography — three separate contradictions

1. **RI rises with no tie at all.** RI raw |grad| is +8.6% over 2016→2025, and
   §1 establishes it has no external interface. A driver must explain all three
   rising zones.
2. **The largest Canadian path lands in a falling zone.** Phase I/II at 2,000 MW
   dwarfs Highgate's 225 MW, and it terminates at Sandy Pond in Ayer,
   Massachusetts. All three Massachusetts zones *fall*: SEMA −3.2%, WCMA −4.8%,
   NEMA −12.7%. (I did not resolve which ISO-NE zone contains Ayer; it does not
   matter, because every MA zone falls.)
3. **The most NB-coupled Maine load isn't in the data.** ATCID §1: the New
   England Control Area "does not include the transmission system in northern
   Maine (i.e., Aroostook and parts of Penobscot and Washington Counties) that is
   radially connected to New Brunswick and administered by the Northern Maine
   Independent System Administrator." The part of Maine most directly tied to
   Canada is outside ISO-NE and therefore outside our ME series entirely.

---

## 4. Timing — no step change inside the measurement window

Highgate has been in service since **1985** and Phase I/II since **1991**, and
the ATCID states of both that "their nominal facility ratings have not changed
since they were placed in service." NE-NB last changed in **2007**.

The measurement window is **2016–2025**. No Canadian interconnection capacity
changed inside it. The one addition — NECEC, 1,200 MW — reached commercial
operation **2026-01-16**, after the window closes.

A hypothesis about Canadian interconnection therefore has no event to point to
that could produce a 2016→2025 trend.

---

## 5. Where the advisor's instinct *is* live — redirect, not discard

One genuinely useful thing survives, and it is a **price**-side test, not a
load-side one.

**Canada is a plausible driver of price volatility, which is the project's actual
outcome variable.** Imports are supply, and supply variability moves LMP
directly. Everything above rules Canada out for *load* volatility; none of it
rules Canada out for *price*. Test it on `da_lmp_<zone>`, not `load_mw_<zone>`.

**NECEC supplies the identification.** A 1,200 MW Canadian import path switched on
in Lewiston, Maine on 2026-01-16, and
`data/interim/isone_diagnostic_panel.parquet` runs through 2026-06-30 — about 5.5
months of post-energization data, ME treated, the other seven zones as controls.

**This must be run on price, not load.** §2 argues interface imports cannot enter
`RT_Demand` at all; if that argument is right, NECEC has no predicted effect on
the load series, so a load-side null would test nothing and a load-side effect
would mean §2 is wrong. Only the price-side version is a real test.

Caveats to design around: 5.5 months is a single season, so season-of-year is
fully confounded with treatment unless matched against the same calendar months
in prior years; and Maine's non-ISO-NE northern system means the treated zone is
not the whole state.

---

## Sources

- ISO New England, *Available Transfer Capability Implementation Document (ATCID)
  v1.0*, effective 2011-04-01 — §1 (control-area definition, Table 1, Figure 1),
  §1.2 (Table 3 interface names), §2 (External Transactions), §3.1.1 (NE-NB
  capability), §3.1.2 (NE-HQ interfaces). Retrieved via National Grid OASIS:
  `https://www.nationalgridus.com/media/oasis/atc/isne_atcid_v1.pdf`
- U.S. EIA, *Today in Energy* #67105 — NECEC 1,200 MW, commercial operation
  2026-01-16. `https://www.eia.gov/todayinenergy/detail.php?id=67105`
- Hydro-Québec, "New England" market page — Highgate 225 MW / 120 kV / Bedford→
  Highgate / commissioned 1985; Radisson–Nicolet–Des Cantons 450 kV DC to Sandy
  Pond. `https://www.hydroquebec.com/clean-energy-provider/markets/new-england.html`
- Hitachi Energy, "Québec – New England" — Phase 1 1986 (690 MW), Phase 2 1992
  (2,000 MW), Sandy Pond Station in Ayer, MA.
- Avangrid / Maine DEP / NECEC project site — Beattie Township to Lewiston
  converter station, ~150 miles HVDC.
- ISO-NE PAC materials — NE-NB comprises Keene Rd–Keswick (3001) and
  Orrington–Point Lepreau (390/3016) 345 kV ties.

### Not verified

- Which ISO-NE load zone contains Ayer, MA (WCMA vs NEMA). Immaterial here — all
  three MA zones fall.
- Whether the ATCID's interface list has changed between 2011 and 2026 other than
  by the addition of NECEC. The 2011 document is the most complete enumeration I
  located; a current-vintage ISO-NE source would be worth confirming against
  before this goes in a write-up.
