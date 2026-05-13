# Decision Log

Append-only log of methodology, scope, and architectural decisions for
this project. One H2 per decision, newest at the bottom (chronological
order makes it easier to follow how thinking evolved).

Each entry should answer:
- **Context** — what triggered the decision; what was unclear or
  contested.
- **Decision** — what we chose, in one or two sentences.
- **Rationale** — why this option over alternatives we considered.
- **Revisit when** — what new evidence would re-open the question.

If a later decision overrides an earlier one, *don't* edit the old
entry — write a new one and reference the prior by date and title.

Pure API facts and platform constraints belong in
`pjm-api-constraints.md`, not here.

---

## 2026-05-10 — Adopt decision-log + superpowers conventions

**Context.** Project is just starting. Methodology decisions are
already accumulating (data scope, pivots from the proposal) and
they'll be invisible to future sessions unless captured.

**Decision.** Two conventions:
1. Record every methodology, scope, or architectural decision in this
   file at the moment it's made.
2. Use Claude superpowers skills as the default workflow:
   `brainstorming` before any creative/feature work, `writing-plans`
   for multi-step implementation, `test-driven-development` for code,
   `systematic-debugging` for bugs, `verification-before-completion`
   before claiming work done.

**Rationale.** Research projects accumulate undocumented "we decided
X because Y" choices that quietly drive later code. Writing them down
once is much cheaper than re-deriving them mid-analysis. The
superpowers skills exist to enforce planning discipline that this
project's CLAUDE.md already asks for.

**Revisit when.** If the decision log gets noisy with low-stakes
entries (e.g. library choices that nobody contests), tighten the
threshold for what warrants an entry.

---

## 2026-05-10 — Cap nodal 5-min LMP scope to the Standard window

**Context.** PJM Data Miner 2 archives the 5-min RT LMP feed after
186 days. Archived queries cannot filter by `pnode_id` and must stay
within a single calendar year. Pulling the full feed for our 3
target substations across 2020–2025 would require downloading every
PJM pnode's 5-min LMP for each calendar year — likely terabytes —
purely to filter client-side. See `pjm-api-constraints.md` §
"Archived (Historic) data".

**Decision.** Three-tier scope:
- **5-min nodal LMP:** restricted to the Standard window (last
  ~6 months from the date of pull). Used for the high-resolution
  phase-transition analysis.
- **Hourly nodal LMP** (`rt_hrl_lmps`, `da_hrl_lmps`): pulled for the
  Standard window (last ~2 years, currently mid-2024 onward) for
  long-window nodal congestion trends.
- **Older periods (pre-2024):** zonal aggregates only (DOM zone),
  losing nodal granularity. Used as historical context, not as the
  primary signal.

**Rationale.** The proposal's 2020–2025 nodal 5-min ambition is not
operationally feasible through Data Miner 2 without a bulk research
extract. Rather than block on that, ship analysis on what's queryable
and treat older nodal data as an open follow-up (option (c) below).

**Open follow-up.** Email PJM Data Miner support to ask whether a
research-grade bulk historical extract for `rt_fivemin_hrl_lmps`
exists outside the Data Miner 2 API.

**Revisit when.** A bulk extract becomes available, OR we get a
clean-enough signal in the 6-month/2-year windows that historical
nodal data isn't needed.

---

## 2026-05-10 — Use hourly DOM-zone load for the volatility metric

**Context.** The proposal's mechanism is "data-center-driven minute-
scale load swings push the LMP into a heavy-tailed regime." The 5-min
load feed (`inst_load`) only exposes load at the *region* level (PJM
SOUTHERN REGION etc.), bundling DOM with DAY/EKPC/etc. DOM-specific
load is hourly only.

**Decision.** Compute the load-volatility metric on **hourly
`hrl_load_metered` for the DOM zone**, accepting the resolution
mismatch with the 5-min LMP feed.

**Rationale.** Region-level 5-min load dilutes the data-center
signal across a much wider geographic and economic footprint than
DOM alone, which arguably hurts the analysis more than coarser
resolution does. Hourly DOM is also more directly interpretable as
"DOM-zone aggregate behavior" and aligns with the hourly LMP feed
used for the long-window analysis.

**Revisit when.** If the hourly load → LMP-regime relationship is too
weak to detect, consider augmenting with `inst_load` regional 5-min
as a secondary signal (variance ratio between region and DOM, etc.).

---

## 2026-05-10 — Pull all matching pnodes for the three target substations

**Context.** The proposal names three substations: Pleasant View,
Ashburn, Goose Creek. PJM's pnode reference (`pnode` feed) typically
returns multiple buses per substation — different voltages, EHV vs.
LOAD subtypes, generator vs. load-side metering points.

**Decision.** Initial pull: every `pnode` row in `zone=DOM` whose
`pnode_name` partial-matches one of the three substation names,
regardless of `pnode_subtype` or `voltage_level`. Filter / narrow
later based on what the actual congestion signal looks like.

**Rationale.** Cheaper to pull broad and prune than to pull narrow
and re-pull. Voltage/subtype distinctions matter for interpretation
but not for initial signal detection. The `pnode` feed is small and
this metadata pull is one-time.

**Revisit when.** After the first pass of LMP analysis, decide
whether to keep all matching buses, restrict to EHV (transmission-
level), or pick a single representative pnode per substation.

---

## 2026-05-10 — Lock the 11-pnode target set (supersedes 2026-05-10 §4)

**Context.** Spike notebook (`notebooks/01_data_miner_spike.ipynb`)
resolved the actual pnode IDs and ran a one-day hourly LMP comparison
across 11 candidate pnodes. Two surprises forced a revision of the
prior "all matching buses" plan:

1. **Ashburn ≠ LOUDOUN.** The proposal's "Ashburn" substation has no
   500 KV transmission aggregate in PJM's registry. We initially
   proposed using LOUDOUN 500 KV as the proxy, on the theory that
   distribution-side LOAD pnodes typically track their upstream
   feeder. The 2026-04-15 spike disproved this: ASHBURN 35 KV LOAD
   showed *consistently higher* congestion than LOUDOUN 500 KV
   (mean $47 vs $28), and during a 15:00–17:00 window LOUDOUN went
   sharply negative (~−$35) while ASHBURN stayed slightly positive.
   The two signals are complementary, not redundant.

2. **Loudoun-area transmission pnodes cluster very tightly.**
   LOUDOUN, MOSBY, BRAMBLET, and SKFFSCRK all came back within
   ~$5/MWh mean LMP and ~$3/MWh mean congestion of each other.
   Useful for spatial-covariance work but largely interchangeable
   for the central regime-detection question.

**Decision.** Final pnode set (locked, n=11):

| Tier | pnode_id | pnode_name | type/subtype | voltage |
|---|---|---|---|---|
| Primary nodal — transmission | 35010365 | LOUDOUN | AGGREGATE/EHV | 500 KV |
| Primary nodal — transmission | 35010371 | PLEASANT VIEW | AGGREGATE/EHV | 500 KV |
| Primary nodal — transmission | 1356178195 | GOOSECRE | AGGREGATE/EHV | 500 KV |
| Primary nodal — transmission | 1356178171 | BRAMBLET | AGGREGATE/EHV | 500 KV |
| Primary nodal — transmission | 1356178181 | MOSBY | AGGREGATE/EHV | 500 KV |
| Primary nodal — transmission | 1356178201 | SKFFSCRK | AGGREGATE/EHV | 500 KV |
| Primary nodal — distribution | 34886139 | ASHBURN 35 KV TX1 | BUS/LOAD | 35 KV |
| Primary nodal — distribution | 34886141 | ASHBURN 35 KV TX2 | BUS/LOAD | 35 KV |
| Control / outside-cluster | 35010369 | OX | AGGREGATE/EHV | 500 KV |
| Control / outside-cluster | 62871513 | BRISTERS | AGGREGATE/EHV | 500 KV |
| Zonal baseline | 34964545 | DOM | AGGREGATE/ZONE | n/a |

**Rationale.**
- Both ASHBURN 35 KV and LOUDOUN 500 KV stay in the *primary* set,
  not as proxy + sanity. The spike showed they capture different
  physics (distribution-level local load vs transmission-level
  import constraints) and should both be present in the regime
  analysis.
- The 6-pnode Loudoun-area transmission cluster gives spatial
  redundancy — useful for confirming whether a regime change is a
  cluster-wide phenomenon or a single-pnode artifact.
- OX and BRISTERS as control pnodes (same DOM zone, same voltage
  class, demonstrably *uncongested* on the spike day — OX mean
  congestion $0.86) enable a difference-in-differences treatment
  if needed: regime change at primary pnodes *while* controls stay
  flat is much stronger evidence than either signal alone.
- DOM zonal as baseline answers "how unusual is the nodal
  congestion vs the zone-wide signal everyone else looks at?"
- 11 pnodes × 288 5-min × 186 days = ~590K rows = ~12 paginated
  calls = ~2 min wall-time. Fits comfortably under the 6/min
  limit. (See `pjm-api-constraints.md` for sizing model.)

**Revisit when.**
- If the analysis proves stable, consider collapsing the
  Loudoun-area cluster (LOUDOUN/MOSBY/BRAMBLET/SKFFSCRK) into one
  representative pnode for narrative clarity.
- If ASHBURN TX1/TX2 prove indistinguishable in the bulk pull
  (max diff <$5/MWh consistently), drop one.
- If we need finer resolution on the data center driver, query
  the `gen` feed for Loudoun-area generator pnodes that may
  reflect data-center-adjacent generation response.

---

## 2026-05-11 — Acquisition module: sync httpx, filesystem-skip, hardcoded pnode constants

**Context.** Spike (`notebooks/01_data_miner_spike.ipynb`) validated the
end-to-end API shape. Before bulk pulls we needed a reusable, idempotent
acquisition layer that respects the 6/min rate limit, archive cutoffs,
366-day range cap, and PJM's quirks (envelope keys, pnode_name truncation).

**Decision.** Three architectural choices, all favoring the simpler option:

1. **Sync httpx (not async).** The 6/min rate limit makes us bound by
   wall time, not concurrency. A single API key cannot benefit from
   async multiplexing.
2. **Filesystem-based skip-if-exists** (not a SQLite ledger). Each
   chunk's parquet path is deterministic; presence on disk = pulled.
   `--force` overrides for re-pulls. `write_chunk` is atomic
   (`.tmp` + `os.replace`) so interrupted writes never pollute the
   skip-if-exists contract.
3. **Pnode IDs as a Python module constant** (`surg.acquisition.targets.PNODES`),
   not config. They are locked in this file (`decisions.md`) and treating
   them as code-level constants matches their stability.

**Rationale.** Each picks the simpler option in its trade-off, given a
single-developer research project with locked targets and a hard rate
ceiling that limits parallelism's value.

**Revisit when.** If we ever obtain a higher-rate API key, async
becomes worth it. If we add multi-target pulls (different pnode
sets per call), targets should move to config.

---

## 2026-05-11 — Phase 3 method: TAR + quantile regression (supersedes proposal §Methodology Phase 3 GPD framing)

**Context.** The proposal commits Phase 3 to a Generalized Pareto
Distribution (GPD) fit on LMP exceedances to "determine the specific
load variance value where the grid's pricing response shifts from
linear to exponential." Re-reading PJM's *Formation of Locational
Marginal Pricing and its System Energy Component During Reserve
Shortage Events* (March 2023, proposal reference [10]) reshaped the
conceptual basis for that fit:

- LMP has a hard step function via the Operational Reserve Demand
  Curve (ORDC). When reserves fall below requirement, PJM's Market
  Clearing Engine adds fixed penalty factors to the system energy LMP:
  $850/MWh for a Synchronized Reserves shortage (first ORDC step),
  $300/MWh for Primary Reserves (second step). These can stack.
- The March 17, 2021 walkthrough (paper p.3): marginal cost $30/MWh +
  $1,547.57 congestion + $2,401.16 ORDC lost-opportunity + small
  adders → $3,664.51/MWh system energy LMP. A >100× discontinuity
  for an infinitesimal reserve depletion.
- Post Oct 1, 2022 the system energy LMP is administratively capped
  at $3,700/MWh (paper p.6). Our pulled nodal LMP windows (hourly
  from 2024-05-26, 5-min from 2025-11-12) are entirely post-cap, so
  no rule-change break inside the analysis window.

The phase transition is therefore **mechanistic** (a structural break
hard-coded in the price formula) rather than **emergent** (a heavy
tail arising from self-organized criticality). GPD models tail
heaviness but doesn't naturally produce a threshold value as a
function of load volatility — it tells us the tail is heavy, not
where the break is.

**Decision.** Replace GPD-as-primary with a method that mirrors the
mechanism. Four sub-decisions:

1. **Primary method — Threshold Autoregression (TAR / SETAR),
   Hansen (1996, 2000) framework.** Threshold variable = load
   volatility; regime-switching response. Hansen's bootstrap test
   gives a *p*-value on whether the threshold is real. The estimated
   threshold `c` *is* the deliverable required by the proposal (a
   specific MW/min load-variance value).
2. **Robustness method — conditional quantile regression at
   τ = 0.99.** Estimate `Q_0.99(response | volatility)`
   non-parametrically; verify the slope kink appears at the same `c`
   as TAR. Guards against TAR's piecewise-AR functional form being
   the source of the kink rather than the data.
3. **Drop GPD as primary.** GPD was a reasonable starting point in
   hindsight (we didn't yet know the ORDC mechanism was so explicit),
   but the mechanistic evidence walks back the case for
   tail-heaviness as the *primary* detection tool. May retain GPD as
   a tertiary descriptive figure (the tail *is* heavy, post-mechanism)
   if reviewer pushback warrants.
4. **Skip Markov regime-switching entirely.** Reserve clearing prices
   are observable through PJM's `reserve_market_results` feed, so the
   regime is directly identifiable — no need to infer it via
   Hamilton-style latent-state models. Avoids EM stability and
   label-switching issues.

**Operational choices for the TAR primary fit.**

| Item | Choice | Notes |
|---|---|---|
| Threshold variable | Hour-over-hour gradient of DOM zonal load: \|Δload_t\| in MW/hr (divide by 60 for MW/min framing) | Proposal says MW/min but DOM-specific load is hourly only on PJM. |
| Response variable | `congestion_price_rt`, hourly | Matches proposal's "congestion pricing" framing. ORDC penalty actually lands in system energy LMP, but congestion is the stated target. |
| Pnode aggregation | Pool the 6-pnode Loudoun transmission cluster (LOUDOUN, PLEASANT VIEW, GOOSECRE, BRAMBLET, MOSBY, SKFFSCRK) by mean. Single regression. | Justified by the 2026-05-10 spike: cluster pnodes within ~$5/MWh of each other. Pooling preserves spatial signal without losing power. May switch to max if mean over-smooths the shortage events. |
| Negative controls | Separate TAR fits on OX, BRISTERS, DOM zonal pnode | Should NOT show the same threshold, or show one at much higher `c`. Negative controls for the cluster claim. |
| Ashburn distribution | Separate TAR fit (35 KV vs 500 KV — different physics, per 2026-05-10 lock-in) | Complementary, not redundant. |
| Time window | Joint LMP+load overlap: 2024-05-26 → 2026-05-10, ~715 days | Hourly grain. |
| Signal isolation | Shoulder season (Mar–May, Sep–Nov) + 2-5 AM window, outage-log cross-check | Per proposal Phase 2. Applied at preprocessing stage. |

**Open follow-up.** Extend acquisition module to pull two additional
PJM Data Miner 2 feeds:

- `sync_reserve_events` — event log with `event_start_ept`,
  `event_end_ept`, `duration`, `synchronized_sub_zone` (filterable to
  "MidAtlantic-Dominion (MAD)" — the DOM-relevant sub-zone).
  *Discrete-event log of when synchronized-reserve dispatch fired*,
  which is the directly-observable mechanism trigger for the ORDC
  first-step penalty. This is the cleanest validation signal for the
  load-volatility → reserves → ORDC → LMP causal chain — better than
  literal outage logs because it captures the *manifestation* of
  reserve stress regardless of cause. Indefinite retention back to
  2002-12-02.
- `reserve_market_results` — RT reserve clearing prices; nonzero
  clearing prices corroborate ORDC trigger and quantify severity.
  Available from 2013-06-14; switched from hourly to 5-min granularity
  on 2022-10-01 (our analysis window is entirely post-change, so
  uniformly 5-min — preprocessing aggregates to hourly).

A third feed (`operational_reserves`) was considered for descriptive
context on reserve margin trajectory, but live-metadata investigation on
2026-05-11 revealed a **15-day retention** policy (the feed posts every
15 seconds for real-time monitoring, not historical analysis).
Retrospective access to the 2024-2026 window is therefore impossible.
The feed is dropped from scope; see `pjm-api-constraints.md` for the
constraint. The core analysis remains intact — the two retained feeds
are sufficient for mechanism validation.

The acquisition module may need minor extension to handle
zone/sub-zone aggregates (vs the nodal feeds it currently supports
cleanly). All three feeds are documented in
`data-miner-2-api-guide.pdf`.

**Outage cross-check (proposal Phase 2) — strategy revision.** The
proposal commits to "checking PJM's publicly available outage logs"
to rule out supply-side LMP spikes. Investigation 2026-05-11 showed
PJM Data Miner 2 has no event-level outage log feed; the closest
public source is the eDART Transmission Facilities Outage List
(member-walled for filtering). Rather than invest in manual TFOL
collection, we use `sync_reserve_events` as the observable mechanism
trigger: an LMP spike not coinciding with a sync reserve event (±3h
window) is excluded from the test of our hypothesis without needing
to identify *which* non-load-volatility cause drove it. This is a
methodological refinement that's *stronger* than the proposal's
explicit outage cross-check, because it conditions on the actual
ORDC mechanism rather than on a proxy upstream of it.

**Revisit when.**
- Advisor input (Prof Wei, Lihui) may push for keeping GPD for
  proposal-fidelity reasons. If so, run GPD in parallel and present
  both with a comparison.
- If TAR's Hansen bootstrap test fails to reject "no threshold" on
  the Loudoun cluster, the mechanistic story lacks statistical
  support for *this* zone in *this* window. We then either (a) widen
  the time window once 2023 nodal LMP becomes available (would need
  Historic-data fetch infrastructure), (b) refine the signal-isolation
  filter, or (c) test whether the threshold is conditional on reserve
  margin rather than load volatility directly.
- If `operational_reserves` shows reserve margin is a sharper
  threshold variable than load volatility, the primary TAR fit may
  shift to reserve margin (closer to the mechanism). The proposal's
  MW/min framing then becomes the *derived* number, not the *fit*
  number.

---

## 2026-05-12 — Window extension to 3.6y post-cap (2022-10-02 → 2026-05-10)

**Context.** The 2026-05-11 decision anchored the joint analysis window
at 2024-05-26 → 2026-05-10 (~2y, 715 days) — bounded by the
`rt_hrl_lmps` 731-day archive cutoff *and* the methodological
requirement to stay entirely post-cap on the 2022-10-01 ORDC rule
change. The window was a soft pick within that post-cap era; older
data exists but we hadn't tested the access path.

Research 2026-05-12 confirmed Historic-tier API access works for
hourly LMP feeds with documented restrictions (`pjm-api-constraints.md`
§ "Archived data" — single calendar year per request, no `pnode_id`
filter, `type=<pnode_subtype>` workaround). Reserves and load feeds
have no archive cutoff and reach back to 2012-2013 (empirical probes).
Pre-2022-10 LMP is in a different rule regime (iterative-cap logic,
no $3,700/MWh cap) and crossing that break would confound the TAR
fit.

**Decision.** Extend the joint analysis window to **2022-10-02 →
2026-05-10** (~3.6y, 1,318 days, ~31,632 hourly observations). This is
the maximal window staying entirely post-cap; the start date is
chosen as one day after the rule change to maximize sample without
straddling the break.

**Rationale.** ~1.8× sample-size lift for the TAR primary fit at zero
methodological cost — all data is in the same ORDC regime. The
longer load baseline also strengthens the proposal's projection
question ("when does projected growth push the grid past the
threshold?"). The structural-break worry that motivated the 2y
anchor doesn't apply here.

**Coverage choice (1a) — asymmetric LOAD-subtype coverage.** Of the
11 nodal targets, 9 receive 3.6y coverage via Plan 1.5 Historic-tier
pulls (8 EHV-subtype: Loudoun cluster + OX + BRISTERS; 1 ZONE-subtype:
DOM zonal). The 2 LOAD-subtype pnodes (ASHBURN TX1/TX2) stay at the
existing 2y coverage. Driver: PJM Historic stores ~10,786
LOAD-subtype pnodes (vs ~136 EHV, ~23 ZONE); recovering 2 of them
requires downloading the entire LOAD-subtype feed (~150M rows, ~8.5h
wall-clock at the 6/min rate limit). The Ashburn-distribution TAR is
a separate, complementary fit per the 2026-05-10 lock-in ("35 KV vs
500 KV — different physics"), so asymmetric window for that single
fit is acceptable. Plan 1.5's archive-mode code supports `type=LOAD`
so the overnight backfill is one config change away if reviewer
pushback requires symmetry.

**Cost summary** (1.6y historic backfill acquisition wall-clock):

| Feed / scope | New coverage | API time |
|---|---|---|
| `rt_hrl_lmps` 9 pnodes (EHV + ZONE) | full 1.6y backfill | ~7 min |
| `sync_reserve_events` MAD | ~10-15 events expected | <1 min |
| `reserve_market_results` MAD SR + PR | ~170K rows | ~2 min |
| `hrl_load_metered` DOM | already on disk back to 2021-01-01 | 0 |
| `da_hrl_lmps` 9 pnodes | deferred (DA-RT spread off the critical path) | 0 |
| `rt_fivemin_hrl_lmps` | not feasible (Historic 5-min rejects `type` filter; full-feed pull ~10B rows/yr) | 0 |

**Revisit when.**
- Reviewer (Prof Wei / Lihui) pushes back on the asymmetric Ashburn
  window — schedule the ~8.5-hour LOAD backfill as an overnight job.
- TAR fit under the 3.6y window indicates insufficient power in the
  high-volatility regime — widen the 2-5 AM filter, or revisit the
  pre-2022-10 portion with a regime-break dummy.
- A new PJM market rule change is announced inside the 2022-10 →
  2026-05 window — re-check the post-cap assumption.

---

## 2026-05-12 — Stressed-regime definition refined to high SR clearing price

**Context.** Mechanism validation tests (§6 of the methodology spec)
originally conditioned the "stressed regime" indicator on
`sync_reserve_event_active` (binary, derived from the
sync_reserve_events feed). Two empirical findings from this session
forced a refinement:

1. **44% of 5-min `reserve_market_results` intervals have nonzero SR
   clearing price** (Plan 1 bulk pull, 2026-05-11). Earlier framing
   considered "nonzero SR clearing" as a stressed-regime proxy; this
   is too lax — it captures normal scarcity pricing, not the discrete
   ORDC-trigger events the mechanism predicts.
2. **Sync reserve events in MAD are sparse**: only 38 events across
   the 3.6y window after Plan 1.5 backfill (Plan 2 smoke build,
   2026-05-12). The original binary regime indicator may have low
   statistical power if it's the only signal.

**Decision.** Run mechanism tests 2 + 3 against **two** stressed-regime
definitions and report both:

1. **Sync event active** (`sync_reserve_event_active = True`) —
   binary, rare. Hits when the full ORDC penalty stack fires.
2. **High SR clearing price** — `sync_reserve_clearing_price_rt ≥ 850
   $/MWh` (the ORDC first-step penalty level). Hits when reserve
   scarcity pricing reached or exceeded the ORDC first-step penalty
   even if no discrete event row was recorded.

**Rationale.** The two definitions are complementary signals of the
same mechanism. Strong agreement = clean confirmation. Disagreement
is informative on its own: if (2) captures more hours than (1), the
binary event log under-counts scarcity; if (1) catches hours that (2)
doesn't, the mechanism fires via the discrete event log without the
clearing price reaching $850. Either result strengthens the paper.

The $850 cutoff is the documented ORDC first-step penalty level
(decisions.md 2026-05-11 § Phase 3 method, citing PJM's *Formation of
LMP under Reserve Shortage Events* paper). Pre-register that
disagreement between the two definitions triggers a sensitivity
analysis sweeping the cutoff from $300 (PR penalty level) up to $3,700
(post-2022-10 LMP cap).

**Implementation.** Plan 3 mechanism tasks (T9-T12) thread both
regime definitions through Tests 2-3 and the 2×2 cross-tab. No
changes to TAR (T3-T5) or QR (T6-T8). No changes to the panel schema
— `sync_reserve_clearing_price_rt` is already in EXPECTED_COLUMNS.

**Revisit when.**
- Reviewer (Prof Wei / Lihui) prefers a single primary regime
  definition for parsimony — either is defensible; switch to (1) if
  the sparse-event sample is large enough, or (2) if reviewers want
  a continuous signal.
- The two definitions diverge meaningfully (>20% of regime-active
  hours in one but not the other) — sensitivity sweep on the $850
  cutoff becomes load-bearing for the paper's narrative.

---

## 2026-05-12 — Methodology caveats noted on `run_tar` (Plan 3 Task 5)

`run_tar` writes a `c_hat_ci_95` block computed via pair bootstrap
(iid resampling of (Y, Y_lag, Z) rows). This is a simplification that
ignores AR serial correlation and is expected to be tighter than the
true sampling distribution. T13's subsample bootstrap is the canonical
CI for write-up purposes.

Separately, after the proposal's signal-isolation filter (shoulder
months + 2-5 AM), consecutive subset rows are ~21 hours apart in real
time. The Hansen bootstrap's recursive Y* generation treats the
filtered subset as a single AR(1) path; we accept this as an
approximation rather than redesigning the bootstrap to respect the
non-contiguous structure. The alternative — bootstrapping at the
night-block level — would shrink the sample further and is not
warranted given the threshold question's locality.

Both points should appear in the methodology section of the writeup.
