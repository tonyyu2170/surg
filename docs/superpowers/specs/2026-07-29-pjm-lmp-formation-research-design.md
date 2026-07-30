# PJM LMP Formation — Primary-Source Research Design

**Date:** 2026-07-29
**Status:** Design approved in-session (all five sections).
**Workstream:** C of four (see § 1.2). Advisor-requested; unblocks the
attribution decision (workstream B) and the unfiltered-panel analysis
design (workstream A).
**Predecessors:** advisor meeting (sub-q1 closure item #5, outcome
relayed by user 2026-07-29); the 2026-07-29 filter-drop decision
(`docs/decisions.md`, currently uncommitted); `docs/pjm-api-constraints.md`.

## 1. Scope & framing

### 1.1 What this is

A primary-source reference on how PJM mechanically forms LMP and its
congestion component, written from PJM's own manuals and whitepapers
rather than third-party summaries, **plus** an explicit mapping from
each mechanism to this project's panel columns and existing findings.

The advisor's instruction was to "do further baseline research on how
pricing and congestion pricing and LMP is calculated in PJM, looking
at their specific PDF releases instead of relying on other third party
sources." The mapping half (Part 2) goes beyond that instruction
because the research's value to the project is interpretive: several
sub-q1 findings are currently unexplained, and at least two of them
have candidate mechanical explanations that primary sources can
confirm or kill.

### 1.2 Position in the four-workstream decomposition

The advisor meeting produced four separable pieces. This spec covers
**C only**.

| | Workstream | Type | Status |
|---|---|---|---|
| A | Unfiltered tail-risk analysis (level vs. volatility, plateau mechanism) | Code + analysis | Diagnostic done (§ 1.4); design deferred until C lands |
| B | Attribution — data-center vs. weather load decomposition | Framing, possibly analysis | Deferred until C lands (user decision) |
| **C** | **PJM LMP formation from primary sources** | **Research, docs only** | **This spec** |
| D | Nano-nuclear / SMR co-location with data centers | Research, docs only | Not started; see § 1.3 |

Sequencing rationale (user decision 2026-07-29): ground the mechanism
in primary sources *before* committing to an analysis design, because
the plateau mechanism in § 1.4 is currently inferred from data rather
than derived from how PJM forms prices.

### 1.3 Gating note on D

`CLAUDE.md` files data-center generation trends (the Nvidia residential
mini-DC example) under **sub-q2 narrative scope**, and sub-q2
plan-writing is gated until sub-q1 is paper-ready. Nano-nuclear
research is the same category. Doing it as background reading does not
break the gate; writing it into a projection narrative does. D stays
research-only until sub-q1 closes.

### 1.4 The finding this research is meant to test

A read-only diagnostic on the extended 5-min panel (350,789 rows,
2023-02-07 → 2026-06-24) established, **before** this research began:

- The proposal filter retains 23,000 / 350,789 rows (6.6%) and **71 of
  the 7,680** observations where cluster `total_lmp` exceeds $250 —
  it excludes 99.1% of the tail events it was designed to isolate.
  This independently confirms the advisor's instruction to drop it.
- P(`total_lmp` > $250) by Z decile on the full panel is **flat**:
  0.0226 (d1) → 0.0208 (d10), ratio 0.92. Flatness survives deciles
  within hour × month (0.95), dropping 2026 (0.89), price leads t+1…t+6
  (0.92–1.05), and a rolling max over t…t+3 (1.00). Exceedances
  collapse to 1,199 independent episodes with balanced yearly counts
  (195/238/437/329), so this is not a single-cold-snap artifact.
- Load **level** predicts strongly: 0.0015 → 0.1418 across load
  deciles (~95×).
- On the joint grid, within the top load quintile P(exceed) *falls*
  monotonically as |Z| rises (0.0970 → 0.0670); with the signed
  gradient, risk peaks at **near-zero** gradient (0.0966) and is lower
  at both steep ramp-up (0.0780) and steep ramp-down (0.0618).

**Candidate interpretation (to be tested against primary sources):**
`|dLoad/dt|` conflates *flat overnight* (lowest-risk state) with *flat
at the peak plateau* (highest-risk state), so no Z-threshold analysis
could have worked regardless of statistical power. This would explain
the hourly Spec A "heavier tail at LOW Z" rejection, which has read as
anomalous since May, as well as the Spec B and item #6 nulls.

This interpretation is **inferred from data, not from mechanism.**
Question 9 (§ 3) is its primary-source test. If PJM's dispatch and
pricing logic gives no reason for sustained peak load to price above a
fast ramp, the interpretation is weakened and workstream A's framing
must change.

## 2. Deliverable

One file: **`docs/pjm-lmp-formation.md`**.

It joins `pjm-api-constraints.md` ("what the API forces on us") and
`decisions.md` ("what we chose") as a third standing reference: **"what
the market mechanically does."** Convention: read it at the start of
any interpretation or write-up work, the same way the other two are
read before data-acquisition work.

```
Header — purpose, source inventory (title, revision, retrieval date), citation format
Part 1 — Mechanism reference
  §1 Three-component decomposition
  §2 System energy component (incl. scarcity adders, 2x penalty-factor cap)
  §3 Congestion component (shadow prices, shift factors, reference bus)
  §4 Marginal loss component
  §5 Timing & resolution (RTSCED, LPC, 5-min pricing, lookahead horizon)
  §6 Reserve structure (MAD sub-zone, requirements)
  §7 Caps and administrative pricing
Part 2 — Mapping to this project
  §8 Panel column -> mechanism map
  §9 Findings ledger (§ 4 of this spec)
  §10 Open questions primary sources do not answer
Appendix — verbatim quotes for load-bearing claims
```

The appendix is load-bearing infrastructure, not padding: it lets a
future session verify a claim without re-downloading and re-reading a
200-page manual.

## 3. Question list

Fixed before reading begins. Grouped by what each group settles.

**Congestion formation — the actual gap in our sourcing**

1. How is the congestion component computed? (Constraint shadow price ×
   shift factor summed over binding constraints — need PJM's own
   statement and notation.)
2. What makes a constraint bind, and what sets shadow price magnitude?
   Is it capped?
3. Is congestion referenced to a system-wide slack/reference bus, and
   does that make it a *relative* rather than absolute quantity?

**Why our congestion tests were the weak ones**

4. Confirm from primary source that reserve-scarcity adders land in
   **system energy**, not congestion. (`reserve-shortage-pricing-paper.pdf`
   says so; get Manual 11's statement too.) **Load-bearing.**
5. Is the system energy component uniform across all pnodes, or does it
   vary by location? **Load-bearing — highest-stakes question in the
   list; see § 4.**

**Resolution and timing — bears on the lag analysis in § 1.4**

6. How does RTSCED/LPC produce 5-min prices, and are they timestamped
   interval-beginning or interval-ending?
7. Is the 5-min price a spot dispatch price or an integrated/averaged
   quantity? **Load-bearing** — if PJM's 5-min LMP embeds a dispatch
   lookahead, the "flat at all lags" result tests something different
   from what was assumed.
8. Does RTSCED use a lookahead horizon that would make prices *lead*
   rather than lag a load ramp?

**Load and dispatch mechanics — bears on the plateau interpretation**

9. **Load-bearing — primary-source test of § 1.4.** Deliberately *not*
   phrased as "is there a mechanism by which sustained peak load prices
   higher than a fast ramp?" — no manual answers a comparative question
   like that, and searching for a sentence that does not exist would
   burn effort. Split into three documented lookups whose conjunction
   supports or kills the plateau interpretation:
   - 9a. How do unit ramp constraints enter the dispatch objective /
     constraint set?
   - 9b. Can a ramp-limited unit set the marginal price, and under what
     conditions?
   - 9c. Do reserve requirements scale with load level, so that being at
     peak raises the requirement independently of the ramp?
10. What does "DOM zone load" measure — metered load or a state-estimator
    value — and is it the same quantity dispatch prices against?

**Structural / caveat-bearing**

11. MAD reserve sub-zone definition; is DOM inside it?
12. Offer caps, price caps, and the post-Oct-2022 2× penalty-factor cap
    logic.

## 4. The mapping half (§9 findings ledger)

For each existing finding, state what the mechanism implies — explains,
limits, or invalidates.

| Finding | Question it tests |
|---|---|
| Spec A median-split rejection (heavier tail at LOW Z) | Does the plateau story hold mechanically, or is it a pricing artifact? |
| Spec B continuous ξ(Z) underpowered | Is congestion structurally the wrong response variable (Q4/Q5)? |
| QR-full moderate-τ positive z_slope | What is it detecting, if scarcity lands in system energy? |
| Item #6 / decile null | Scope failure vs. genuine mechanism absence |
| New: level-vs-volatility + plateau (§ 1.4) | Q9 — does dispatch price sustained peak above fast ramp? |

**Why Q5 is the highest-stakes question.** If the system energy
component is uniform across pnodes, then congestion is the *only*
component in which a **local** data-center effect could ever appear.
That would mean the congestion-based tests were right to be the primary
spec despite being the weak ones, and that `total_lmp`'s larger response
is mostly a system-wide scarcity signal with no Loudoun-specific
content. Sub-q1's framing would need substantial revision. If instead
system energy varies locationally, the reverse holds and `total_lmp` is
defensible as a primary response.

**Do not assume the answer.** "The system energy component is uniform
across pnodes" is a *premise under test*, not an established fact, and
it was verbally overstated as established during the 2026-07-29 design
session. `reserve-shortage-pricing-paper.pdf` p. 1 establishes only
that (a) total LMP = system energy + congestion + marginal loss, and
(b) a pnode's total LMP may be greater or less than the system energy
component. Neither statement settles locational uniformity of the
system energy term, particularly given the MAD reserve **sub-zone**
structure (Q11) — a sub-zonal reserve shortage is the obvious candidate
mechanism for a locationally varying scarcity adder. Any downstream doc
that relies on uniformity must cite Q5's resolution, not this spec.

## 5. Sources

Vendored to a new `docs/pjm-sources/` directory. Reachability and sizes
verified 2026-07-29 (`www.pjm.com` resolves normally; the DNS failure
recorded in memory is specific to `api.pjm.com`).

| Source | Size | Answers |
|---|---|---|
| Manual 11 — Energy & Ancillary Services Market Operations | 6 MB | Q1–5, 7, 8, 12 |
| Manual 12 — Balancing Operations | 1 MB | Q6, 9, 10, 11 |
| Manual 3 — Transmission Operations | 1 MB | Q2 (constraint definition) |
| *(already in repo)* `docs/reserve-shortage-pricing-paper.pdf` — PJM, 2023-03-07 | — | Q4, 12 |

Q10 has two halves and only the first belongs to this workstream: what
quantity PJM's dispatch prices against (Manual 12, state estimation /
load accounting) versus what the gridstatus `pjm_load.dom` feed
actually reports. The second half is already settled in
`docs/gridstatus-api-constraints.md` and the 2026-07-17 `dom`-as-DOM
disclosure decision; this doc cross-references that rather than
re-litigating it.

Plus PJM Learning Center / training material on LMP components if a
citable PDF exists. If none does, that is recorded as unavailable —
**no third-party substitute**, which is the specific failure the
advisor asked us to fix.

The two PDFs already at `docs/` top level stay where they are. Moving
them into `pjm-sources/` is unrelated cleanup; flagged, not done.

## 6. Method and verification standard

**Read order — cheapest load-bearing source first.** Before downloading
any manual, read pp. 4–6 of `docs/reserve-shortage-pricing-paper.pdf`
(8 pages, already in repo). Page 1 already names the **Locational
Pricing Calculator (LPC)** as a stage distinct from the **RTSCED**
dispatch engine, and states an interval as a range ("LPC pricing
interval (10:10–10:15)"). That is direct evidence on Q6–Q8 — including
Q7, the question most likely to invalidate the lag conclusion in § 1.4.
Settling Q7 from a source already on disk changes what Manual 11 needs
to supply, so it happens first.

Per question: locate the passage, **read its surrounding section** (not
the matching paragraph alone), record the answer with manual + revision
+ section + page.

Three rules make the output trustworthy:

- **Load-bearing claims get verbatim quotes.** Load-bearing = a claim
  some existing project doc already asserts, or one that changes how a
  finding reads. Q4, Q5, Q7, Q9 qualify.
- **Contradictions are flagged, not smoothed.** A manual contradicting
  our docs goes in an explicit corrections list *and* gets a
  `decisions.md` entry, since prior sessions built on those claims.
- **Unanswered stays unanswered.** Questions the manuals don't settle go
  in §10 with a note on what would settle them. No inference presented
  as a citation.

## 7. Success criteria

1. All 12 questions answered with page-level citation, or explicitly
   listed in §10 as unanswered.
2. Each **finding-gating** LMP-formation claim is confirmed-with-citation,
   corrected, or marked unsupported. Scoped to a named list rather than
   "everything in `docs/`" (~20 files mention ORDC / shadow price /
   marginal loss in passing; auditing all of them is not the goal):
   - `docs/plans/2026-05-11-phase-transition-methodology.md:145` — "the
     penalty lands in system energy LMP rather than in the congestion
     component" (gates the choice of response variable).
   - The same file's `load volatility → reserve depletion → ORDC trigger
     → LMP spike` chain (lines 52, 289) — gates the entire mechanism
     narrative.
   - The `$850`/`$300` per-MWh ORDC penalty-factor figures (line 38) —
     gate the JLARC napkin-math benchmarks.
   - The implicit "system energy is uniform across pnodes" premise (§ 4)
     — gates whether a local effect can appear anywhere but congestion.
3. §9 filled in for all five findings in § 4.
4. Docs only — no `src/` changes, no analysis re-runs, no new tests.

## 8. Out of scope

- Workstreams A, B, D (§ 1.2).
- DOM-specific transmission-constraint identification — considered and
  explicitly not chosen (user decision 2026-07-29); the most
  open-ended option in effort.
- Any re-run of the analysis pipeline. The 5-min re-run in flight
  (`outputs/fivemin_extended/`, reported 3/5 complete as of ~18:30 EDT
  2026-07-29; PID 71958, detached and not tied to any session) is left
  untouched. This workstream is docs-only so there is no collision.
- Committing `docs/decisions.md` and `docs/gridstatus-api-constraints.md`,
  which the prior session left uncommitted (user instruction 2026-07-29:
  leave them).
