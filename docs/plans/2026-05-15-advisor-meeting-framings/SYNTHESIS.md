# Sub-q1 Framing Synthesis — Advisor Meeting Prep

**Inputs:** 4 independent champion briefs (one per framing), each
self-contained, working from the same curated evidence sheet.
**Process:** Champions wrote in parallel without seeing each other's
work. This synthesis identifies convergences, divergences, and a
recommended meeting structure.

---

## ⚠ PROVISIONAL FRAMING ARC (pending advisor item #5 — MAY CHANGE)

**Status as of 2026-05-15:** Student (Tony) provisionally leans
toward the following paper arc. **Not locked.** The advisor meeting
(closure item #5) is the gate that confirms or revises this. Treat
as the working assumption for any pre-meeting prep ONLY; do not
build irreversible work on it.

**Provisional arc:**

1. **#3 — why the threshold question was wrong** (intro/motivation:
   no ĉ, smooth response, decile-null triangulation)
2. **#2 — the positive moderate-quantile finding** (headline: Z
   drives conditional 95th-pct LMP, total_lmp ≈ 4× congestion,
   ORDC footprint; closest to the proposal's original intent)
3. **#1 — the boundary that keeps #2 honest** (Spec A α=0.05
   rejection on congestion tail SHAPE; formally orthogonal to #2's
   conditional-LEVEL claim; disciplines the headline)
4. **#4 — post-hoc extreme-tail companion** (top-1% Z concentration,
   abstract-level post-hoc caveat)

**Rationale:** #2 is closest to what the student set out to do; #3
explains why the literal proposal question wasn't answerable as
posed. Internally the most-supported combination (Champion 2
structures itself this way; Champion 3 names #2 as its fallback
with its own content as §5).

**THE key decision for the advisor:** Is Spec A (#1) a *boundary
section* under the #2 headline, or does Wei want it *elevated to
co-headline*? That single call sets the paper's tone:
"positive finding with a disciplined boundary" vs
"rejection-and-refinement." Both are publishable.

**Supersede when:** advisor meeting (item #5) locks the final
framing. Update this section + write a locked decisions.md entry
at that point.

---

## TL;DR

Four candidate framings, **all four self-rated medium confidence,
none high**. None is clearly best from the data alone — the choice
is a narrative call, not an analysis call.

**Convergence point: Framing #2 (QR-full moderate-τ positive) is
named as the fallback by 3 of 4 champions, including the champions
who argued against it as headline.** This is the natural Schelling
point for the paper.

**Recommendation:** lead the advisor meeting with the framing
landscape (don't anchor on one), surface that #2 is the consensus
fallback, and let Wei/Lihui make the call. Have specific
decision-point questions ready.

## The four framings at a glance

| | **#1 Spec A rejection** | **#2 QR-full positive** | **#3 Decile null** | **#4 Extreme-tail** |
|---|---|---|---|---|
| **Headline** | "ORDC mechanism on congestion rejected at α=0.05, opposite direction" | "Z drives conditional 95th-pct LMP, total_lmp ≈ 4× congestion" | "Proposal's framing was the wrong question — Z doesn't separate crazy hours" | "Proposal directionally right, wrong about sharpness — top-1% concentration" |
| **Statistical strength** | Single α=0.05 rejection on n=789/half | α=0.05-cleared on 5/7 pnodes | Multi-test triangulated null | Post-hoc Wilson CI excludes baseline (n=316) |
| **Direction vs proposal** | Opposite | Same (at moderate τ) | N/A — rejects the framing itself | Same (at extreme tail) |
| **Pre-registered?** | Yes | Yes | Yes | **No (post-hoc)** |
| **Publication tier guess** | Negative-result paper, mid-tier | Positive standard, mid-tier | Methodological journal | Descriptive characterization |
| **Sub-q2 (JLARC) input?** | Bounds the projection | **Provides the slope coefficient** | Bounds the policy strength | Provides extreme-tail factor |
| **Self-rated confidence** | Medium | Medium | Medium | Medium |
| **Champion's own fallback** | → #2 | → #1 (paired) | → #2 | → #2 |

## Where the champions converged

### 1. Framing #2 is the natural Schelling point

Three of four champions (1, 3, 4) explicitly name #2 as their
fallback. Champion 2 names #1 as the natural complement. So
**every brief independently reasons that #2 either anchors the
paper or is the fallback that survives if the headline argument
fails**.

Why #2 wins by elimination:
- Only α=0.05-cleared **positive** finding in the project (5/7
  pnodes, CIs exclude 0)
- Only framing that produces a usable sub-q2 (JLARC) projection
  input (year-FE z_slope @ τ=0.95)
- Compatible with all other findings as supporting/complementary
  results (Spec A rejection = different statistic; decile null =
  different scope; extreme-tail = same direction at finer resolution)

### 2. Spec A rejection (#1) is too important to omit, regardless of headline

All four champions agree the Spec A α=0.05 rejection on congestion
must appear in the paper. Champion 1 wants it as headline; champions
2-4 want it as the "discipline section" / boundary on whatever
positive claim is made. Either way, **the rejection must be
prominently presented and cleanly explained** (different statistic
than the QR-full level test).

### 3. Decile null (#3) is the most intellectually honest framing but the hardest to publish

Champion 3 explicitly acknowledges this: "strongest on internal
evidence and intellectual honesty; weakest on first-author
publishability for an undergraduate at top-tier energy venues."
The triangulated null IS a paper-worthy finding, but it requires a
methodological journal (Energy Economics, Energy Policy, The Energy
Journal) and the advisor's commitment to that path.

### 4. Extreme-tail (#4) handles the post-hoc concern carefully but cannot escape it

Champion 4 is honest: "without a held-out validation window it is
hard to defend as *the* contribution against a senior PhD pushing
on forking paths." The extreme-tail finding is the most
narratively defensible interpretation of the proposal but cannot
be the formal headline without a pre-registered follow-up.

## Cross-framing tensions to resolve at the meeting

### Tension A — How to present the Spec A vs QR-full direction conflict

- Spec A rejects on **tail SHAPE** of **congestion** in the OPPOSITE
  direction
- QR-full positive on **conditional LEVEL at τ=0.95** of **total_lmp**
  in the SAME direction

These test different things on different variables. Champion 2's
rebuttal (formal orthogonality of conditional location vs tail
shape) is technically correct but reads as ex-post sophistication.
**The advisor needs to lock how the paper reconciles these two
findings narratively.**

### Tension B — Is the post-hoc top-1% finding paper-presentable?

Champion 4 says yes (with abstract-level caveats). Champion 3 folds
it in as "refinement of the smooth-low-discrimination
characterization." Champions 1 and 2 are skeptical: champion 1
calls it "panel-level, post-hoc, and within shouting distance of the
unconditional base rate." **Wei/Lihui need to call this — it
materially changes which framing is anchorable.**

### Tension C — Year-FE attribution gap

Champion 2 (the only one whose headline depends on this) flags it
honestly: primary-spec slope = 0.578 vs year-FE slope = 0.410 on
cluster congestion at τ=0.95. The gap is "year-correlated 2026
partial-window component, attribution unresolved." **Advisor has to
decide whether this is publishable as-is with caveats or requires
further attribution work** (which the data probably can't support).

### Tension D — Ashburn TX1 anomaly placement

All four framings push it to a "robust unexplained finding"
footnote/section. **Advisor decides:** paper subsection? Methods
footnote? "Future work" deferral?

## Recommended meeting structure (60 min agenda)

**Pre-read for advisor (send 24h ahead):** the 4 brief files +
this synthesis. They're self-contained.

### 0–10 min: Frame the meeting

- Sub-q1 is analytically closed; closure roadmap items 1-4, 6, 8, 9
  all DONE (only item #5, this meeting, remains).
- The data does not pick a paper headline for us. Four candidate
  framings exist; all four self-rate medium; the champions
  converge on #2 as the natural fallback / Schelling point.
- The meeting's purpose is to LOCK the headline framing so paper
  drafting can begin. Secondary purpose: resolve four specific
  tensions (above).

### 10–25 min: Walk through the framing landscape

For each framing, 3 minutes:
- Headline thesis (1 sentence)
- Strongest evidence (1 number + cross-pnode pattern)
- Strongest weakness (the brief's own honest acknowledgment)

Don't over-defend any single framing. Let the advisor see all four.

### 25–40 min: Resolve the four tensions

In order:
1. **Tension A:** narrative reconciliation of Spec A vs QR-full
2. **Tension C:** year-FE attribution publishable as-is?
3. **Tension B:** post-hoc top-1% paper-presentable?
4. **Tension D:** Ashburn TX1 placement?

For each, present the evidence, note the trade-off, and ask the
advisor to call it.

### 40–55 min: Lock the headline framing

After the tensions are resolved, the framing space narrows
significantly. Walk the advisor through the implied framing(s)
and ask for the lock.

Likely outcomes:
- **Most likely:** #2 as headline, #1 as boundary section, #4 as
  descriptive characterization, #3's null content as §1's framing
  rejection
- **Possible:** #1 as headline, #2 as the "but level still rises"
  secondary, #3 / #4 as supporting
- **Unlikely:** #3 or #4 as headline standalone

### 55–60 min: Lock follow-up actions

- Sub-q1 paper outline due date
- Sub-q2 plan-writing unlock conditions
- Open methodology questions parked for sub-q3 design (e.g.,
  pre-registered top-1% follow-up; Ashburn data acquisition)
- Items the paper explicitly does NOT address (out-of-zone
  generalization, mechanism replacement story, etc.)

## Decision points the advisor must lock (consolidated)

1. **Headline framing** (one of the four, or a hybrid — most likely
   #2 with #1 as boundary)
2. **Spec A vs QR-full reconciliation language** for the paper
3. **Post-hoc top-1% finding placement** (paper section, footnote,
   future work)
4. **Year-FE attribution gap** (publish as-is with caveat, or
   require additional work)
5. **Ashburn TX1 anomaly** (subsection, footnote, deferred)
6. **Publication target** (top-tier energy economics vs methodological
   journal — affects framing #3's viability)
7. **Sub-q2 projection coefficient** (year-FE @ τ=0.95 is the
   default; advisor confirms or revises)

## What I (the synthesizer) think

**I'd lead with #2 + #1 paired, structured as:**

- **Headline (#2):** "Z drives conditional 95th-pct LMP" — positive,
  α=0.05 cleared, cross-pnode, sub-q2-ready
- **Boundary section (#1):** "But Z does NOT heavy-tail congestion
  at p95" — pre-registered rejection on the proposal's own variable,
  formally orthogonal to the headline (different statistic)
- **Supporting characterization (#4):** "The slope's direction
  extends to extreme tail (top 1% Z) at descriptive scope" —
  post-hoc, abstract-level caveat
- **Methodological context (#3):** "The proposal's literal threshold
  framing is rejected (smooth response + decile-null
  triangulation)" — frames §1 of the paper

This pairing maximizes the publishable surface area without
overclaiming any single result. It also leaves sub-q2 with a
defensible projection input.

**The risk:** Wei may push for #1 as headline because it is the
cleanest pre-registered α=0.05 result. That works too — the
argument is more conservative but still publishable, and #2 simply
moves to "but the moderate-quantile slope still rises with Z."

**The risk I'd resist:** anchoring on #4 alone. The post-hoc
concern is real and a single Wilson CI on n=316 is too thin to
carry the headline.

**The risk I'd reluctantly accept:** if Wei wants #3 (null-led)
because intellectual honesty demands it, the path is longer (need
methodological-journal commitment) but defensible.

## File pointers

- `framing-1-spec-a-rejection.md`
- `framing-2-qr-full-positive.md`
- `framing-3-decile-null.md`
- `framing-4-extreme-tail.md`
- Closure roadmap: `../2026-05-14-sub-question-1-closure-roadmap.md`
- Existing meeting agenda: `../2026-05-14-advisor-meeting-agenda.md` (pre-dates items #6/#8/#9; supplement with this synthesis)
- Authoritative findings record: `docs/decisions.md` (sub-q1 entries through 2026-05-15 item #9 + post-hoc audit)

## What this synthesis is NOT

- Not a final paper outline (post-meeting deliverable)
- Not a recommendation that bypasses Wei/Lihui's judgment — they
  pick the headline; this surfaces the choice for them
- Not exhaustive — Ashburn TX1 anomaly, JLARC projection
  attribution, and the Part B 5-min hidden-fraction finding all
  need their own meeting time
- Not a guarantee #2 wins. The meeting could lock differently and
  any of the four framings is publishable with sufficient framing
  discipline.
