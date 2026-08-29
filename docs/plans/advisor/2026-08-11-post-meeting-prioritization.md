# Post-Meeting Prioritization — week of 2026-08-11

Source: `docs/plans/advisor/2026-08-10-advisor-meeting-agenda.md`, "Notes from meeting"
plus "Things I Need Advice On" and "Future Direction".

All six items are due this week. What follows is an ordering, and the ordering
principle is **which item changes what you write**, not which is most
interesting.

---

## The ordering

| # | Item | When | Why here |
|---|---|---|---|
| 0 | UT Austin email + Pecan Street access request | **Today, ~30 min** | Multi-week reply latency, near-zero cost. Must not consume the week. |
| 1 | New England fluctuation (VT/ME/RI) | **Mon–Tue** | Only item touching Finding 3, the result that threatens the premise. Data already on disk. Pre-decides #4. |
| 2 | FERC 50 MW + the cost-shift logic | **Wed** | Reading, not analysis. Resolves agenda worry #2, which is a framing threat. |
| 3 | XFRA + Pecan Street (one task, not two) | **Thu** | Pecan Street is the evidence base for the XFRA question. |
| 4 | Europe / Ireland | **Fri, gated on #1** | Expensive expansion. Its hypothesis is #1's hypothesis. |
| — | Reverse-engineer DC load from pricing | **Don't** | See "The one to drop". |

---

## 0. Outreach first, because it isn't work

Both of these are emails with multi-week reply times and no analysis cost. Send
them before starting anything else so the latency runs in parallel with the
week.

- **UT Austin (BEG TRAIL Map).** The agenda already concluded it's a policy
  white paper, not a data release. That is the correct reason to email rather
  than to keep searching: ask whether the data behind the narrative can be
  shared with an academic under an agreement. Worst case is a no, which closes
  the ERCOT question permanently and is itself a citable result.
- **Pecan Street.** The waveform release is a request/registration flow, not an
  open download. Start it now; it feeds item #3.

---

## 1. New England — and the agenda's own framing is slightly off

The agenda says (line 25) "ISONE was the only zone with somewhat volatile load."
The capstone entry disagrees with that, and the capstone is right: the
system-level +9.9% is **mostly a denominator effect**. ISO-NE load *fell* 5.2%,
so normalizing by mean load inflates the number even in zones where raw
volatility fell (CT: raw −7.8%; SEMA: raw −3.2%). Line 27 — Vermont and Maine —
is the accurate version of the observation. Lead with that in the write-up, and
drop the aggregate framing.

### What the data on disk already says

Recomputed this morning from `outputs/isone_diagnostic/trends_by_zone_year.csv`
(2016 → 2025, raw `grad_mean`, no new pulls):

| zone | mean MW | raw \|grad\| change | load change | normalized change |
|---|---|---|---|---|
| **vt** | **578** | **+38.9%** | −11.9% | +57.7% |
| **ri** | **887** | **+8.6%** | −4.5% | +13.7% |
| **me** | **1288** | **+18.9%** | −3.8% | +23.5% |
| nh | 1301 | −8.2% | −0.3% | −8.0% |
| sema | 1591 | −3.2% | −3.4% | +0.2% |
| wcma | 1829 | −4.8% | −4.3% | −0.5% |
| nema | 2700 | −12.7% | −3.6% | −9.5% |
| ct | 3197 | −7.8% | −9.6% | +2.1% |

**The three zones with rising raw volatility are the three smallest zones.**
Spearman(mean MW, raw |grad| change) = **−0.786, p = 0.021, n = 8**.

⚠️ **This is post-hoc and not pre-registered.** It was computed from an existing
production output to size the question, and by the project's own convention it
cannot be quoted as a blessed result without a pre-registration entry first.
Treat it as a lead, not a finding.

### What this does to the advisor's hypothesis

The advisor proposed the Canadian interconnection as the driver. **RI rules that
out as the leading explanation:** RI is rising (+8.6%) and has no Canadian
interconnection at all, while the tie zones VT (Highgate → Hydro-Québec) and ME
(New Brunswick) are only two of the three. A hypothesis that misses one of three
positives isn't the driver, though it may still be part of the VT/ME story.

**What the three rising zones actually share is that they are the small, rural,
high-DER-share zones** — and that is one description, not three hypotheses. Zone
size, rural-ness, distributed-solar share per unit of load, and renewable share
are all collinear across n = 8: the small zones *are* VT/ME/RI, the large ones
*are* the CT / Boston / Providence load centers. ρ = −0.786 against zone MW is
equally consistent with every one of them. Nothing in this panel separates them.

That determines the discriminating test: **regress raw |grad| trend on per-zone
DER penetration, not on zone MW.** If DER share predicts the trend where size
does not, the mechanism is net-load measurement — metered zone load is *net* of
behind-the-meter solar, so rising DER makes the series more volatile with no
change in demand behavior at all. That is the version of the hypothesis worth
putting to your advisor, and it is the reason to pull per-zone DER data rather
than more load data.

Two caveats to carry:

- The size boundary is razor-thin — ME (1288 MW, rising) against NH (1301 MW,
  falling) is a 13 MW gap. With n = 8, the clean split could still be
  coincidence. Do not treat ρ = −0.786 as settling anything.
- **Quantization was checked and ruled out** (2026-08-11): a rising `grad_mean`
  on a 578 MW zone could have been reporting precision rather than physics, and
  precision artifacts scale inversely with zone size, which would reproduce this
  ρ exactly. `data/interim/isone_diagnostic_panel.parquet` reports load
  continuously to 3 decimals in every zone and every year — the share of exact
  integer values is 0.001, i.e. chance level, with no era break. The absolute
  precision floor is identical for VT and CT, so the correlation is not an
  artifact of the small denominator.

### Why this is the week's most important item

Finding 3 in the capstone is the load-bearing problem: the low-data-center
control market shows the level-over-volatility result at 64/64, with a *higher*
median R² (0.274) than most treated markets. On that evidence the project's
central pattern is a property of how power systems price load, not a data-center
signature.

If the VT/ME/RI rise turns out to be supply-side — Canadian imports, wind, or
distributed solar — then the project has a genuine and publishable inversion of
its own premise: **in the absence of data centers, load volatility is driven by
generation, not by demand.** That is a finding, not a null result, and it is the
strongest thing to come out of the eight-market sweep. It is worth the two days.

---

## 2. FERC — search the repo before searching the web

`docs/research-notes/E-flexible-load.md` and `docs/research-notes/A-primary-verify.md`
already carry the FERC order, the compliance-filing schedule, and the co-location
material. Start there; only go to the order text for what's missing.

On **"why would transmission costs fall on homeowners if the data center is
tapped in directly?"** — the shape of the answer, to be confirmed against the
order rather than asserted:

1. Co-located load still leans on the network for backup when its host generator
   trips, and for reliability services generally, so it is not truly off-grid.
2. That generator was already counted as a network resource in transmission
   planning; netting it against on-site load removes it from the pool.
3. Transmission fixed costs are recovered per-MWh of *billed* sales. Remove
   large sales from the denominator without removing the costs, and the rate on
   everyone else rises.

That is the mechanism behind the $140M/yr figure in the agenda. The 50 MW
threshold is worth pinning to its source paragraph — it may be a PJM tariff
convention rather than something FERC derived, which would itself be the answer.

**On agenda worry #2 ("if BTM takes off, my whole premise is flattened").**
It doesn't flatten it, and the reason is in your own capstone: you already found
volatility is *not* what prices track — level is, in 11 of 11 panels. The premise
that BTM would threaten is the volatility premise you have already moved off.
What BTM actually threatens is *measurement*: netted BTM generation is invisible
in metered load, so future observed load decouples from true consumption. That is
a limitations-section point about the shelf life of your data, not a refutation.
Write it as such.

---

## 3. XFRA and Pecan Street are one question

**Pecan Street is residential waveform data from Austin. It is not
data-center data.** Do not file it as the ERCOT source you were missing — it
cannot answer the facility-level question, and the ERCOT gap stays open
regardless.

What it *can* answer is the advisor's XFRA question: *do homeowners actually
have the spare capacity XFRA claims?* Residential waveform data at appliance
resolution is close to the ideal instrument for that. Run the two items as one:

- Where is XFRA siting? (PulteGroup's ~100-home pilot — which metros, which
  utility territories.)
- What headroom does a typical new-build panel actually have, and what does
  Pecan Street's Austin data say about how much of it is genuinely idle?

Note the tension worth writing down: a house's spare capacity is largest exactly
when the grid is least stressed, and smallest during the summer peak when it
matters. If that holds in the Pecan Street data, XFRA's dispersal claim gets much
weaker, and you have a real result from a cheap analysis.

---

## 4. Europe — gated on #1

Ireland is a good instinct and the hypothesis is right there in the agenda: more
renewables → more fluctuation. But that is the *same* hypothesis as the VT/ME/RI
question, tested on a market whose data you have never pulled, whose price
product differs, and where a new acquisition module would be needed.

Run it after #1 reports. If #1 comes back supply-side, Ireland becomes a targeted
confirmation of a hypothesis you already hold — much more valuable, and a much
narrower pull. If #1 comes back some other way, you may not want Ireland at all.
Do the desk research this week (does EirGrid publish zone-level load and price at
useful granularity, and at what depth); defer the pull.

---

## The one to drop

**"Try reverse engineering data center load from the pricing."**

This cannot work, and the reason is your own results. Median R² across the eleven
panels runs 0.108–0.332 — the price series explains at most a third of load
variance in the best panel. And the headline finding is that price tracks load
*level*, not volatility. Inverting a relationship that weak to recover a
component of load, where you have no facility-level ground truth to validate
against, would produce a number with no defensible error bar.

Say this to your advisor explicitly rather than letting it sit on the list. A
clean "here is why that direction is closed" is worth more than a failed attempt,
and it is the kind of judgment the meeting is for.

---

## One process note

Sub-q1 has been "analytically closed, only the advisor meeting remaining" since
2026-05-15. The deliverable-structure decision of that same date requires a
standalone hybrid technical/accessible report per sub-q, with supporting graphs.
The twelve-figure set was built 2026-08-08. No report exists in the repo.

This doesn't change the ordering above, but it should change where the week's
output lands: whatever comes out of items #1–#3 belongs in **sub-q1 report
prose**, not in a twelfth `decisions.md` entry. The analysis is done; the writing
is the deliverable that's actually outstanding.
