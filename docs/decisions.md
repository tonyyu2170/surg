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

---

## 2026-05-13 — Pre-registration: interpretation rules for n_boot=1000 TAR re-run

**Context.** The 2026-05-12 real-data run of `surg-analyze` at
`n_boot=300, n_subsample_reps=50` produced a working pipeline but
five unsettled findings that the n=1000 re-run will either resolve
or sharpen:

1. **Boundary degeneracy.** Hansen TAR estimated `ĉ ≈ 4.4` MW/min
   for the primary Loudoun-cluster congestion fit and 4 of 5
   controls; `ĉ` sits at the 85th percentile of the threshold
   variable `Z` (DOM load gradient), at the upper edge of the
   estimator's 0.15-trim search window. Methodology spec §8 flags
   this configuration as "boundary degenerate."
2. **Hansen p = 0.0033 for every fit.** Exactly the bootstrap floor
   `1/(1+n_boot)` at `n=300`. The test cannot discriminate primary
   from controls at this resolution.
3. **High-SR-clearing regime empty.** The 2026-05-12 dual-regime
   amendment's second indicator (`sync_reserve_clearing_price_rt ≥
   $850`) captures **0** active hours inside the 2,027-hour
   `passes_proposal_filter` subset.
4. **`total_lmp` basin at `ĉ ≈ 1.45`, congestion basin at
   `ĉ ≈ 4.4`.** Same Loudoun cluster, but the total-LMP response
   localizes ~3 MW/min lower than the congestion-only response.
5. **Granger non-significant at all lags (p > 0.5).** Only 2 active
   sync-reserve-event hours inside the filter; the test is
   underpowered by sample size, not by `n_boot`.

The re-run at `n_boot=1000` increases bootstrap resolution by 3.3×
at the floor and directly addresses findings 1, 2, and 4. Findings
3 and 5 are filter-occupancy / power problems that `n_boot` cannot
fix — they need parameter sweeps and/or filter widening.

This pre-registration locks interpretation rules before the n=1000
numbers are visible. Five inconvenient findings + a fresh result
set is exactly the configuration where post-hoc rationalization
inflates apparent results.

**Decision.** The rules below apply to the next
`surg-analyze --n-boot 1000 --n-subsample-reps 200` run. Any
deviation requires a new dated entry in this file explicitly
overriding this one; we do not edit this entry post-hoc.

### Rule 1 — Boundary degeneracy

Compute `q_ĉ` = empirical quantile of `ĉ` in `Z`. The TAR
estimator's search window is `[0.15, 0.85]` of `Z` (trim parameter
0.15), so `q_ĉ` at or close to these boundaries indicates the
algorithm hit the search wall.

| `q_ĉ` | Classification | Action |
|---|---|---|
| `(0.20, 0.80)` | Not degenerate | `ĉ` is the headline threshold; no further mitigation |
| `≥ 0.80` | **Boundary-degenerate** (high-`Z`) | Widen filter to **1–6 AM** (deliberate departure from the proposal's 2–5 AM, per §8); re-run; report both pre- and post-widening fits |
| `≤ 0.20` | Low-`Z` degenerate | Flag as "no meaningful threshold detected"; do not report `ĉ` as a headline |

The 0.20 / 0.80 cutoffs are deliberately tighter than the trim
boundaries (0.15 / 0.85) — a 5-percentage-point buffer protects
against estimates that aren't literally at the wall but are close
enough to be wall-driven. Widening is pre-committed over trim
tightening or `Z` rescaling because it matches the §8 default and
preserves the algorithm's working assumptions about the search
window.

### Rule 2 — Primary-vs-controls Hansen p separation

Negative controls are **OX, BRISTERS, DOM zonal** only (per the
2026-05-10 locked target set § "Lock the 11-pnode target set").
Ashburn TX1/TX2 are complementary primary fits on different
physics, not controls. Let `p_loudoun` = Hansen p-value of the
primary Loudoun-cluster congestion fit, and
`p_min = min(p_OX, p_BRISTERS, p_DOM_zonal)`.

| Pattern | Classification | Implication |
|---|---|---|
| `p_loudoun ≤ 0.01` AND `p_min ≥ 0.05` | **Loudoun-specific** | Headline claim supported as in proposal |
| `p_loudoun ≤ 0.01` AND `p_min ≤ 0.01` | **DOM-wide** | Reframe paper: "DOM-zone threshold detected; not localized to Loudoun." Still a positive result, different scope |
| `p_loudoun ≤ 0.01` AND `p_min ∈ (0.01, 0.05)` | **Ambiguous** | Report all 4 p-values; do not claim cluster-specificity; discuss in limitations |
| `p_loudoun ∈ (0.01, 0.05]` | **Marginal cluster significance** | Report as "suggestive evidence for cluster threshold pending power analysis"; do not claim a confirmed threshold regardless of controls |
| `p_loudoun > 0.05` | **Null for cluster** | Lean on QR + `total_lmp` to salvage interpretation |

The asymmetric `≥ 0.05` / `≤ 0.01` bands within the strong-primary
rows are intentional. The gray zone is a permitted outcome ("we
don't know"), not a binary forcing.

### Rule 3 — Choice of primary response variable (congestion vs total LMP)

Compute `Δĉ = |ĉ_total_lmp − ĉ_congestion| / sd(Z)`.

| Condition | Action |
|---|---|
| `Δĉ ≤ 0.5` AND both Hansen tests pass (`p < 0.01`) | Congestion stays primary (proposal-aligned); `total_lmp` reported as a robustness check |
| `Δĉ > 0.5` AND both Hansen tests pass | **`total_lmp` becomes the primary outcome**; congestion demoted to "robustness: congestion component only, same cluster." Methods section cites the methodology-spec rationale that total LMP is the cleaner ORDC test (penalty enters via system-energy LMP, not congestion component) |
| Exactly one Hansen test fails | Report the passing fit; demote the failing one |
| Both fail | See Rule 2's null-result branch |

The `0.5 · sd(Z)` threshold is a stipulation, no theoretical
anchor. Picked as "meaningfully different on the scale of the
data."

### Rule 4 — High-SR-clearing regime sensitivity sweep

Pre-authorized in `decisions.md` 2026-05-12 § "Stressed-regime
definition refined to high SR clearing price"; this rule fixes the
sweep parameters.

Sweep `sync_reserve_clearing_price_rt ≥ cutoff` at:
**$300, $500, $850, $1000, $2000, $3700**. Report active hour
count inside `passes_proposal_filter` at each. Hour count is
monotonically decreasing in cutoff, so each condition below has a
well-defined solution.

The objective is the **highest** cutoff that captures ≥ 30 active
hours, because higher cutoffs better isolate ORDC-level stress (vs
baseline scarcity pricing). Lowering the cutoff is a sensitivity-
driven substitution, not a free choice.

| Outcome | Action |
|---|---|
| `$850` (methodology-spec cutoff) captures ≥ 30 active hours | Use `$850` as originally specified; no substitution |
| `$850` captures < 30 hours but `$500` captures ≥ 30 | Use `$500`; document as a sensitivity-driven downward substitution from the spec value |
| `$500` captures < 30 hours but `$300` captures ≥ 30 | Use `$300` with explicit caveat: "cutoff at PR penalty level, not SR — weak supplementary signal only" |
| `$300` captures 10–29 active hours | Use `$300` with the same supplementary-signal caveat |
| `$300` captures < 10 hours | **Drop the dual-regime amendment** from mechanism validation; report only `sync_reserve_event_active` |

### Rule 5 — Granger causality power

- If Rule 1 widens the filter to 1–6 AM, Granger automatically
  reruns on the widened filter — no separate action.
- If Granger's final p-value is `> 0.10` (whether or not widening
  occurred): report null result honestly with explicit power
  discussion (`n_active_events` reported alongside). Do not drop
  Granger from the mechanism section; reframe as "underpowered in
  our window."

**Open question — multiple-testing correction.** Rule 2 involves 4
Hansen tests at the cluster + control level (1 primary + 3
controls). Family-wise error rate at α = 0.05 with 4 tests inflates
to ~0.19; Bonferroni would suggest α ≈ 0.0125 per test. This
pre-registration **does not** apply a correction because (a) the
controls are pre-specified at the methodology-spec level as part of
the test of the central hypothesis, not as bonus tests, and (b) we
want advisor (Prof Wei / Lihui) input before committing. Flagged
for the advisor meeting; a follow-up dated entry may tighten
Rule 2.

**Rationale.** Pre-registration is the cheapest defense against
post-hoc rationalization. Drafting these rules before seeing n=1000
numbers means we cannot retrofit a decision boundary to make the
result tell whichever story we prefer. The rules are deliberately
not all-numerical (Rule 1 mixes a quantile cutoff with a qualitative
classification; Rule 5 is procedural) because not every finding has
a meaningful single-number boundary.

**Revisit when.**
- After the n=1000 run lands, the rules are applied as-is.
  Disagreement with the rules in light of actual numbers triggers a
  new dated entry, not an edit here.
- Advisor input on multiple-testing correction may produce a
  follow-up entry tightening Rule 2.
- If Rule 1's widening (1–6 AM) itself produces boundary-degenerate
  results, escalate to the next §8 option (trim tightening, then
  `Z` rescaling).

---

## 2026-05-13 — Application of pre-reg + diagnosis of threshold non-localizability (follow-up)

**Context.** The same-date pre-registration entry locked five
interpretation rules before any new bootstrap output was visible.
This entry records (a) mechanical application of those rules to
the pre-reg-mandated runs, and (b) the substantive diagnosis that
emerged from follow-up exploratory probes spanning multiple filter
widths, time resolutions, and threshold-variable choices. The
diagnosis reshapes the project's analytical strategy and
supersedes the simpler "find threshold c" framing the proposal
and the methodology spec committed to. The pivot recommendation
below is the analyst's read pending advisor (Prof Wei / Lihui)
sign-off, not a fait accompli.

Pre-reg-mandated runs:

- `outputs/` — original 2-5 AM filter, `n_boot=1000`.
- `outputs_n300/` — original filter, `n_boot=300` (sanity check;
  identical verdicts to `n=1000` on this data).
- `outputs_widened/` — Rule 1 widening to 1-6 AM, `n_boot=1000`.

Post-pre-reg exploratory probes (outside original pre-reg scope):

- `outputs_widened_12_7am/` — symmetric 7-hour widening.
- `outputs_sweep_*/` — four additional hourly filter widths
  (1-5 AM, 2-6 AM, 11pm-6am [methodology spec §8 default], 11pm-7am)
  at `n_boot=300`.
- 5-min approach (a) — regional load gradient `Z` from
  `inst_load` (PJM SOUTHERN REGION), one-off in-memory analysis;
  raw data at `data/raw/inst_load/2025_2026_southern_region.parquet`.
- 5-min approach (c) — `Z` = SR clearing price from native 5-min
  `reserve_market_results` (MAD, service=SR), one-off in-memory
  analysis on the existing on-disk parquets.

### Pre-registered rule application — headline numbers

`sd(Z)` differs between filters because each filter samples a
different load-gradient distribution; quantiles of `ĉ` in `Z` are
computed against the filter's own `Z`.

|  | Original (2-5 AM, n=2027) | Widened (1-6 AM, n=3385) |
|---|---|---|
| `Z` mean / sd / 80th pct | 2.79 / 2.15 / 4.39 | 4.25 / 3.44 / 7.10 |
| **primary** — Loudoun cluster congestion `ĉ` (q) | **4.39** (q=0.80) | **4.42** (q=0.62) |
| **total_lmp** — Loudoun cluster total LMP `ĉ` (q) | **1.45** (q=0.31) | **4.93** (q=0.66) |
| OX (control) `ĉ` | 4.39 | **7.83** |
| BRISTERS (control) `ĉ` | 4.39 | **7.83** |
| DOM zonal (control) `ĉ` | 3.74 | 4.42 |
| Ashburn TX1 / TX2 (complementary) `ĉ` | 4.18 | 6.30 |
| QR spline kink | 1.68 | 12.37 |
| QR threshold-dummy kink coef @ TAR's `ĉ` (p) | −3.62 (p=0.049) | **+3.55 (p=0.032)** |
| Granger lag-1 / lag-2 / lag-3 p | 0.54 / 0.82 / 0.94 | 0.59 / 0.13 / 0.25 |
| Subsample bootstrap median `ĉ` (95% CI) | 4.40 ([3.20, 4.60]) | 5.89 ([4.36, 7.85]) |

All Hansen p-values at or one tick off the n=1000 bootstrap floor
(0.0010 to 0.0020). The test statistic exceeds essentially every
bootstrap null on every fit.

### Rule-by-rule verdicts

| Rule | Verdict | Action per pre-reg |
|---|---|---|
| 1 — Boundary degeneracy | Original q=0.80 (degenerate); widened q=0.62 (clean) | Use widened-filter result |
| 2 — Primary vs controls | `p_loudoun ≤ 0.01` AND `p_min(controls) ≤ 0.01` | **DOM-wide** classification |
| 3 — Congestion vs total_lmp | `Δĉ/sd(Z) = 0.15 < 0.5` on widened (both pass at `p < 0.01`) | **Congestion stays primary** (reversal from original-filter verdict; the 1.45 total_lmp basin was a 2-5 AM artifact) |
| 4 — SR-clearing sweep | At `$300`: 1 hour inside either filter | **Drop dual-regime amendment** |
| 5 — Granger | `p > 0.10` even after widening (best lag-2 p=0.13) | **Null result with power discussion** |

The rules were honored mechanically. But the rule-2 verdict
collapsed to "all p-values at the bootstrap floor" — methodologically
true, interpretively thin. The richer dimensions of the data are
treated in the subsequent sections.

### Post-pre-reg exploration 1 — 12-7 AM widening

User-initiated curiosity about whether wider-still windows further
clarified the picture. Result: ĉ jumped from 4.42 (1-6 AM) to
**10.92** (12-7 AM) for the primary fit, with q=0.85 — back to the
boundary. Five of the seven fits pinned to the identical ĉ=10.92.
Granger lag-2 worsened to 0.97 (from 0.13 in 1-6 AM). The 1-6 AM
result does not generalize to wider windows.

### Post-pre-reg exploration 2 — 7-window hourly sweep

Asymmetric and symmetric widenings around the 1-6 AM point.
Cluster/control ratio (Loudoun ĉ / OX ĉ) across windows — the
quantity that the original follow-up draft treated as a substantive
"Loudoun stresses first" finding:

| Window | width | Loudoun ĉ | OX ĉ | L/OX |
|---|---|---|---|---|
| 2-5 AM (orig) | 3 hrs | 4.39 | 4.39 | **1.00** |
| 1-5 AM | 4 hrs | 4.41 | 4.41 | **1.00** |
| 2-6 AM | 4 hrs | 7.81 | 6.29 | **1.24** (reversed) |
| 1-6 AM (rule1) | 5 hrs | 4.42 | 7.83 | **0.56** |
| 11pm-6am (§8) | 7 hrs | 7.83 | 7.83 | **1.00** |
| 11pm-7am | 8 hrs | 8.62 | 11.39 | **0.76** |
| 12-7 AM | 7 hrs | 10.92 | 10.92 | **1.00** |

**The 1-6 AM L/OX = 0.56 result is a singularity** in the filter
family, not a robust empirical phenomenon. Small perturbations
(adding hour 5 instead of hour 1, using the methodology spec's
recommended §8 widening 11pm-6am, etc.) reset L/OX to 1.0 or flip
it to > 1.0.

### Post-pre-reg exploration 3 — 5-min approach (a): regional load gradient `Z`

A 27-day joint window of 5-min PJM SOUTHERN REGION load and 5-min
nodal LMP (2026-04-13 → 2026-05-10) — `inst_load` has ~27-day
rolling retention (see `pjm-api-constraints.md` update for this
constraint).

Headline finding: ĉ is **more** unstable across filters at 5-min
than at hourly. Primary congestion ĉ varies 1.89 → 6.82 → 12.83
across 1-6 AM / 2-5 AM / 11pm-7am. Hansen p separates from the
bootstrap floor — primary cong at 2-5 AM gives p = 0.053
(borderline non-significant); total_lmp at 2-5 AM and 1-6 AM
gives p = 0.103 (not significant at α = 0.05). The 5-min evidence
for a threshold is actually weaker than hourly suggested. L/OX
ratio is 3.56 on 2-5 AM at 5-min — Loudoun ĉ *higher* than OX,
the opposite direction from the 1-6 AM hourly singularity.

### Post-pre-reg exploration 4 — 5-min approach (c): SR clearing as `Z`

Joint window 2025-11-12 → 2026-05-10 (~6 months, 51,541 5-min
intervals). Z distribution wildly skewed: median = $0.010, 95th
pct = $21.40, 99th pct = $141.67, max = $4156.

| Cutoff | Joint window | Full 3.6y panel |
|---|---|---|
| ≥ $300 | 117 intervals (0.23%) | 550 (0.15%) |
| **≥ $850 (ORDC 1st step)** | **26 (0.050%)** | **289 (0.076%)** |
| ≥ $1000 | 19 | 213 |
| ≥ $3000 | 2 | 58 |

At `trim=0.15`, ĉ lands in [0.00, 0.12] — essentially "above
median noise level," not at any mechanistically meaningful value.
At `trim=0.05`, ĉ jumps to ~13-21 (the new 95th-percentile
boundary). All five pnode fits give the same ĉ in each filter —
no spatial differentiation when `Z` is a system-level variable
(SR clearing is one number for all of MAD), as mechanistically
expected.

**The pre-known $850 ORDC threshold is invisible to TAR.** Only
26 of 51,541 intervals in the 6-month joint window have SR
clearing ≥ $850 (0.050%). To make $850 a candidate threshold,
trim would need to be ≤ 0.0005, which violates the algorithm's
regime-occupancy assumption.

### Diagnosis: why TAR is filter-sensitive on this data

The proposal hypothesizes a "phase transition" at a critical load
volatility level. The methodology spec (citing PJM's *Formation of
LMP Under Reserve Shortage Events*, 2023) identifies the mechanism
as a chain:

```
DC load  →  load volatility  →  reserve scarcity
         →  SR clearing  →  ORDC step  →  LMP spike
```

The proposal's threshold question targets the **first** link
(load volatility → downstream). The explicit step function lives
at the **last** link (SR clearing → ORDC at $850). The link from
load volatility to reserve scarcity is **probabilistic, not
deterministic**: high load volatility makes scarcity events more
likely but does not guarantee them.

The composite function (LMP as a function of load volatility) is
therefore the convolution of:

- **P(reserves scarce | load volatility)** — smooth probabilistic
  curve, no hard threshold.
- **LMP boost | reserves scarce** — sharp step at $850
  (guaranteed by PJM market rule).

A smooth probabilistic curve convolved with a sharp step yields
**another smooth curve**, not a sharp threshold. TAR's piecewise-
constant model is approximating this smooth curve with a jump,
and the approximation point drifts with whatever data subset is
fed in. This is the mechanism behind every filter-, resolution-,
and Z-variable-sensitivity we observed today.

This diagnosis is consistent with every probe result:

| Observation | Explanation under the smooth-curve diagnosis |
|---|---|
| `ĉ` shifts with filter widening | Different filter → different `Z` distribution → different "where the smooth curve looks most jump-like" |
| `ĉ` shifts with time resolution | Same — finer resolution samples the smooth curve differently |
| `ĉ` shifts with `Z` variable | Each `Z` has its own smooth response curve; `ĉ` lands at the steepest local slope |
| QR spline kink also unstable | Same — there isn't a kink, there's a smooth curve |
| Hansen always rejects null | True — the response really is non-constant; just not piecewise |
| QR threshold-dummy slope sign positive | True — the smooth curve is monotonically increasing in `Z` |
| Negative controls reject too | True — the smooth curve exists for all pnodes; ORDC is system-mediated |
| $850 threshold invisible to TAR | The mechanistic step is so rare that it falls outside the trim domain |

### Robust signals across all probes

- **A regime change exists.** Hansen rejects "no threshold" in
  every fit across hourly, 5-min approach (a), and 5-min approach
  (c), spanning multiple `Z` choices and filter widths.
- **Response direction is correct.** QR threshold-dummy slope
  positive in 6 of 7 hourly windows and most 5-min fits — slope
  increases with `Z`, as the proposal predicted.
- **The ORDC mechanism is real and rare.** SR-clearing ≥ $850
  events occur in our window (289 5-min intervals over 3.6 years,
  ~24 hours total).

### Not-robust signals (caveats)

- A specific MW/min or $/MWh value for the threshold.
- Spatial differentiation between Loudoun cluster and outside-
  cluster controls (L/OX ratio collapses to 1.0 outside the
  singular 1-6 AM window).
- QR spline kink location (1.57 to 15.54 across hourly windows).
- The "Loudoun stresses first" reading at 1-6 AM.

### Implications for the research question

The proposal's first sub-question — "what is the critical MW/min
threshold of data-center load variance" — is **not the right
question for this data.** There is no single threshold value; there
is a smooth probabilistic relationship between load volatility and
LMP response. The proposal's second sub-question — "when does this
become the chronic operating state" — is still answerable, but
requires reframing as a question about the *shifting distribution*
of load volatility under projected DC growth, not about crossing a
fixed point.

### Strategy C — recommended analytical pivot (pending advisor sign-off)

1. **Switch the primary analytical tool** from TAR-as-headline to
   **QR-on-full-panel + GPD on LMP tails.** Both methods naturally
   model the smooth probabilistic relationship; both are
   filter-robust because they don't search for a single jump point.
2. **Reframe the deliverable** from "the critical threshold is
   X MW/min" to "the upper quantiles of LMP shift meaningfully as
   load volatility crosses the Yth percentile of its historical
   distribution; the response curve has slope Z near that crossing."
3. **Answer the projection question via JLARC growth forecasts
   applied to the load-volatility distribution.** When does the
   historical 95th percentile of `Z` become the new 50th percentile?
   When do ORDC-triggering load excursions become routine instead
   of rare? These questions do not require a threshold point
   estimate.
4. **Keep TAR and the filter-sweep results as descriptive evidence,
   not primary headline.** The sweep itself is a methodological
   contribution: it documents that the response is smooth, not
   piecewise.

### Open questions for advisor meeting (Prof Wei / Lihui)

1. **Validate the smooth-curve diagnosis.** This is the central
   methodological claim of this session. Prof Wei is well-equipped
   to evaluate whether the convolution-of-smooth-and-step framing
   is sound and whether Strategy C is the right pivot.
2. **Specific QR / GPD specifications.** For QR: which quantiles
   (τ=0.95, 0.99, both)? Which covariates (time-of-day, season,
   load level)? For GPD: what tail cutoff (90th, 95th, 99th
   percentile of LMP)? Peaks-over-threshold or block maxima?
3. **Mechanism-validation framing.** Without discrete-event Granger
   and without the dual-regime amendment, the ORDC mechanism is
   supported theoretically (proposal §10 citing the PJM 2023 paper)
   but not empirically validated in our window. Is the theoretical
   citation adequate?
4. **Multiple-testing correction.** Flagged as open in pre-reg.
   Less load-bearing now that we're pivoting away from TAR-as-
   primary, but still relevant for the descriptive sensitivity
   sweep.
5. **Filter primacy.** With QR on full panel as primary, the
   shoulder × 2-5 AM filter becomes a robustness check, not a
   primary analytical decision. Keep it as such or drop?
6. **Handling the proposal's MW/min deliverable.** The proposal
   commits to "determine the specific load variance value." If we
   cannot deliver that as a point estimate, the paper needs either
   a reframed deliverable or a quantified-uncertainty version
   ("between the 80th and 95th percentile of historical load
   volatility, with response slope Y").

### Revisit when

- After advisor meeting produces guidance on the diagnosis, the
  pivot, and the open questions above.
- If a substantially new data source becomes available — 5-min
  DOM-specific load (not currently exposed by PJM), longer 5-min
  LMP history (currently capped at ~6 months by archive
  constraint), etc. None expected within the SURG project timeline.
- If we discover the smooth-curve diagnosis is wrong (e.g., a
  threshold appears via a method we have not yet tried).

---

## 2026-05-14 — Build Strategy C tools before advisor sign-off

**Context.** The 2026-05-13 follow-up entry recommended Strategy C
(QR-on-full-panel as primary + GPD on LMP tails) *pending advisor
sign-off*. The advisor meeting (Prof Wei / Lihui) has not yet been
scheduled. Continuing analysis requires either (a) waiting for the
meeting and accepting the opportunity cost while six open methodology
questions remain abstract, or (b) building the Strategy C modules
ahead of the meeting on the bet they are mechanically appropriate
regardless of which final framing the advisor endorses.

**Decision.** Build and run the Strategy C modules — `fit_qr_full`,
year-FE robustness, GPD threshold sweep, GPD conditional-on-Z
mechanism test — and execute a production-resolution run before the
advisor meeting. Treat the modules as analytical instruments useful
under any final framing, not as a commitment to the Strategy C
narrative itself.

**Rationale — naming the bet.** QR-on-full-panel and GPD do not
search for a single threshold point and are therefore filter-, time-
resolution-, and Z-variable-robust in ways TAR is not. Per the
2026-05-13 smooth-curve diagnosis, that robustness is mechanically
appropriate for this data regardless of how the paper's headline
deliverable is ultimately framed. Worst case (advisor pushes back on
Strategy C as the *narrative pivot*): we still have concrete numbers
characterizing the data's volatility-LMP response, which any
revised plan will need to evaluate. Best case: the numbers make the
advisor meeting evidence-based rather than speculative on six open
questions. Build cost was bounded (~1 day, implemented via
subagent-driven-development from a `feature/strategy-c-modules`
worktree).

**Implementation record.** 11-task plan at
`docs/plans/2026-05-13-strategy-c-implementation.md`; 18 commits
(11 feat + 7 fix) on a sibling worktree, FF-merged to main at
`40bbfd2`, branch deleted. New modules:
`src/surg/analysis/qr_full.py`, `src/surg/analysis/gpd.py`. Existing
`run.py` extended with `PNODE_RESPONSES` dict and new CLI flags
(`--qr-full-n-boot`, `--gpd-n-boot`). Output layout reorganized to
`outputs/{tar,qr,qr_full,gpd,mechanism,robustness}/`. 172 tests
passing (up from 145). Production-run findings recorded in the
next entry.

**Revisit when.**
- Advisor input proposes a framing that the implemented modules
  cannot serve (e.g., a fit method we have not yet built —
  continuous ξ(Z) parametric model, copula-based dependence, etc.).
  In that case, a follow-up entry records the addition.
- Advisor input contradicts a specific implementation choice (e.g.,
  bootstrap CI method, threshold quantile, conditioning-variable
  granularity). Implementation is changed in code, no further
  decisions.md entry needed unless the methodology spec itself
  shifts.

---

## 2026-05-14 — Strategy C production findings: moderate-τ volatility response confirmed; conditional-Z mechanism test (median-split, 95th-pct threshold) rejects heavier-tail-at-high-volatility

**Context.** Production-resolution run of the freshly-shipped
Strategy C tools plus full-pipeline re-execution of TAR / QR /
mechanism for cross-method consistency. Run config: `n_boot=1000`
(TAR), `n_subsample_reps=200` (TAR subsample bootstrap),
`qr_full_n_boot=200`, `gpd_n_boot=200`. ~40 min wall-clock on the
full 2022-10-02 → 2026-05-10 panel.

**Provenance note.** Numbers below come from the session's
worktree-local `outputs/` directory, which was removed when the
`feature/strategy-c-modules` worktree was cleaned up post-merge.
Reproduce via `.venv/bin/surg-analyze` from main (default flags);
outputs land at `outputs/{tar,qr,qr_full,gpd,mechanism,robustness}/`.
This entry is the durable record of the run.

### Finding 1 — TAR consistency check

`ĉ` byte-identical to the prior n=1000 run on main (pre-Strategy-C):
primary Loudoun cluster congestion = 4.3927, OX = 4.3927, BRISTERS =
4.3927, DOM zonal = 3.7382. Hansen *p* at the n=1000 bootstrap floor
(0.000999) on every fit. The smooth-curve-diagnosis prediction (TAR
returns the same boundary value regardless of intervening
implementation work, because it locates the smooth curve's steepest
slope, not a threshold) is confirmed.

### Finding 2 — QR-full primary spec: Loudoun cluster congestion

Pair-bootstrap CIs at τ ∈ {0.90, 0.95, 0.99} on the full panel
(31,632 hourly rows, no filter):

| τ | z_slope | bootstrap 95% CI | asymptotic *p* |
|---|---|---|---|
| 0.90 | 0.393 | [0.325, 0.462] | < 1e-6 |
| 0.95 | 0.578 | [0.428, 0.761] | < 1e-6 |
| 0.99 | 0.358 | [−0.075, 1.194] | ~1e-6 |

The τ = 0.99 row empirically confirms the Strategy C pivot's premise:
asymptotic SE understates uncertainty at high τ on autocorrelated
data; the bootstrap CI is the load-bearing inference. Both moderate
quantiles show robust positive volatility-to-LMP response on the
full panel.

### Finding 3 — Year-FE robustness: secular vs contemporaneous decomposition

`fit_qr_full` with year fixed effects (`baseline_year=2022`) absorbs
secular trends; the residual is the contemporaneous z_slope.

| τ | primary z_slope | year-FE z_slope | secular share |
|---|---|---|---|
| 0.90 | 0.393 | 0.252 | 36% |
| 0.95 | 0.578 | 0.410 | 29% |
| 0.99 | 0.358 | 0.622 | **−74% (sign flip)** |

At τ = 0.99 the secular trend goes the *opposite* direction from
contemporaneous volatility response — the 99th-pct LMP has been
trending **down** over 2022–2026 even as the contemporaneous
relationship to volatility stays positive. Plausible explanation:
PJM grid investments and post-2022 ORDC reform are dampening
extreme-tail LMP over time, offsetting (and at τ = 0.99,
over-correcting) the DC-driven volatility effect. **This is
methodologically real but mechanistically open** — could be a true
structural improvement, could be a 4-year window picking up a
cyclical trough, could be an artifact of the sparse tail at τ = 0.99
× 31,632 obs. Flagged for advisor.

### Finding 4 — QR-full cross-pnode at τ = 0.95 (primary spec)

| Pnode | Tier | z_slope | bootstrap CI |
|---|---|---|---|
| Loudoun cluster (cong) | Primary | 0.578 | [0.43, 0.76] |
| Loudoun cluster (total_lmp) | Primary | **2.334** | **[1.85, 2.73]** |
| OX | Control | 0.612 | [0.40, 0.85] |
| BRISTERS | Control | 0.570 | [0.38, 0.79] |
| DOM zonal | Zonal | 0.195 | [−0.05, 0.47] |
| Ashburn TX1 | Distribution | −0.604 | [−1.22, 0.52] |
| Ashburn TX2 | Distribution | 0.119 | [−0.35, 0.47] |

Three patterns:

1. **`total_lmp` z_slope is ~4× the congestion z_slope on the same
   Loudoun cluster.** The ORDC penalty stack lands in system-energy
   LMP, not in the congestion component — this is the methodology
   spec's prior mechanistic prediction operationalized as a number.
   Direct support for the ORDC mechanism on the full panel.
2. **No Loudoun-specific effect.** Loudoun ≈ OX ≈ BRISTERS at
   τ = 0.95 (all in [0.57, 0.61]). The L/OX = 0.56 finding from the
   2026-05-13 1-6 AM widened filter does not generalize to the full
   panel. This is consistent with the 2026-05-13 Rule 2 verdict
   ("DOM-wide" on the widened filter) — that verdict now generalizes
   from the widened-filter subset to the full panel.
3. **Ashburn TX1 has a negative point estimate.** Wide CI crosses 0,
   so the bootstrap can't reject zero, but the median sign is the
   wrong direction for a DC-influenced distribution-side pnode.
   Either real (different physics at 35 kV) or noise. Flagged for
   advisor.

**Reconciliation with the 2026-05-13 Rule 3 verdict.** That rule
classified "congestion stays primary" under TAR using the
`Δĉ / sd(Z)` criterion. The QR-full total_lmp result above is a
finding under a *different method* and detects a differential the
TAR-Δĉ rule was not designed to surface. Rule 3 stands within TAR;
the QR-full 4× differential is complementary additional evidence
that `total_lmp` is the cleaner ORDC-mechanism response in the
high-quantile regime.

### Finding 5 — GPD threshold sweep

Peaks-over-threshold GPD fit on the Loudoun-cluster mean
`total_lmp_rt` at progressively higher LMP threshold quantiles.
Bootstrap CI on ξ via residual resampling.

| Threshold quantile of LMP | Exceedance count | ξ | tail regime |
|---|---|---|---|
| q = 0.90 | 3,154 | 0.851 | very heavy |
| q = 0.95 | 1,577 | 0.706 | heavy |
| q = 0.99 | 316 | 0.275 | moderate |
| q = 0.995 | 158 | 0.024 | essentially exponential |

Bootstrap CIs on ξ at each threshold are in
`outputs/gpd/gpd_threshold_sweep.json` (regenerated by re-run; not
recorded in session memory).

**ξ decreases sharply with threshold.** No single GPD describes the
full LMP tail; the tail is "heaviest" in the upper 10th percentile,
moderate in the upper 1st percentile, and essentially exponential at
the 0.5% extreme. This matters for paper framing: a single
GPD-shape headline (e.g., "the LMP tail has shape ξ = X") is
ill-defined on this data.

### Finding 6 — GPD conditional Z-split mechanism test

The proposal's central mechanism test, operationalized as: at a
fixed LMP threshold, does the high-load-volatility subset of
exceedances have a heavier GPD tail than the low-load-volatility
subset?

Test specification: threshold = 95th percentile of cluster
`total_lmp_rt`; split exceedances by median Z (`dom_load_gradient
_abs_mw_per_min`); fit GPD separately to each subset; report
`shape_diff = ξ_high − ξ_low` with paired bootstrap CI.

| Subset | n | ξ |
|---|---|---|
| low-Z (Z < median) | 789 | 0.788 |
| high-Z (Z ≥ median) | 788 | 0.609 |
| **`shape_diff` (high − low)** | — | **−0.180** |
| bootstrap 95% CI | — | **[−0.371, −0.044]** |
| bootstrap *p* (one-sided, H₁: high > low) | — | 0.99 |

**The hypothesis "high load volatility produces a heavier LMP tail
than low load volatility" is rejected at this scope.** 99% of
bootstrap replicates produced a *lighter* tail in the high-Z
subset.

**Scope of the rejection — what this result does NOT say.** This is
the precision point most likely to be misread in a six-month-old
session. The result rejects exactly one specific hypothesis:
*median-split, 95th-pct LMP threshold, full panel*. It does NOT
reject:

- **The ORDC mechanism.** The `total_lmp` 4× congestion finding
  (Finding 4) is direct support.
- **A volatility-LMP relationship.** Positive z_slopes at τ = 0.90
  and τ = 0.95 (Finding 2) directly support that.
- **Non-monotonic Z dependence.** A quartile split or continuous
  ξ(Z) parametric model could find a non-monotonic structure
  invisible to a median split. Not yet tested.
- **Tail-heaviness at higher LMP thresholds.** Finding 5 swept the
  threshold but did not run conditional-Z at each level. The
  rejection is anchored to the 95th-pct threshold.
- **A different conditioning variable.** Z = DOM load gradient was
  pre-registered as the threshold variable, but the 2026-05-13
  5-min SR-clearing probe (`§ Post-pre-reg exploration 4`)
  established that Z = SR clearing price gives a different
  mechanistic story. The rejection here is for the DOM load
  gradient conditioning, not any other Z.

The next question is whether the rejection holds *outside* this
narrow scope. If it does, the proposal's central mechanistic story
needs reframing; if it doesn't, the median-split was the wrong
test specification. Flagged for advisor.

### What this means for the proposal — net read

**Supported** (full panel, robust at production bootstrap reps):

- Positive volatility-to-LMP response at moderate quantiles (τ =
  0.90, 0.95).
- ORDC penalty stack lands in system-energy LMP, not congestion
  (`total_lmp` z_slope ≈ 4× `congestion_price_rt` z_slope at
  τ = 0.95).
- Hansen TAR rejects "no threshold" at the bootstrap floor on every
  fit — a regime change in the response *does* exist (carryover
  from prior sessions; not new today).

**Open at the rejection's specific scope** (per the precision
points above):

- Median-split, 95th-pct LMP threshold, full panel: high-Z subset
  has *lighter* tail. The narrowly-scoped hypothesis is rejected;
  the broader hypothesis is not testable from this one specification
  alone.

**Not robust** (from 2026-05-13, still not robust on full panel):

- A specific MW/min threshold (TAR ĉ filter-, resolution-, Z-variable
  sensitive; the 4.39 production result is the smooth-curve diagnosis's
  predicted artifact).
- Spatial differentiation between Loudoun cluster and DOM-zone
  controls (full-panel cross-pnode shows Loudoun ≈ OX ≈ BRISTERS).
- "Loudoun stresses first" framing — the 1-6 AM hourly singularity
  did not survive the full-panel run.

### Open questions carried into the advisor meeting

1. **Conditional-Z rejection — true negative or median-split
   artifact?** Quartile split or continuous ξ(Z) parametric model
   may reveal non-monotonic structure. Pre-commit to a robustness
   spec before re-running, to avoid post-hoc rationalization.
2. **τ = 0.99 secular sign flip.** Real grid improvement absorbing
   DC-volatility effect at the extreme tail, or sparse-tail
   artifact? The implication for the projection question is large
   — if real, projected DC growth must overpower a *declining*
   extreme-LMP trend.
3. **Ashburn TX1 negative point estimate.** Real distribution-side
   inversion (different physics) or noise (CI crosses 0)? Worth a
   focused diagnostic if any paper-relevant claim rides on
   distribution-side pnodes.
4. **GPD threshold choice for conditional-Z test.** 95th-pct was
   chosen as the methodology default; ξ at the 95th-pct threshold
   is 0.706 (heavy) and there are enough exceedances to split
   (n = 1,577). 99th-pct gives ξ = 0.275 (moderate) and n = 316 —
   splittable but less power. Pre-commit threshold for the
   robustness spec.
5. **Multiple-testing correction.** Carried from the 2026-05-13
   pre-reg. Less load-bearing now that the headline is on QR-full
   z_slopes (univariate per pnode), but still relevant for the
   conditional-Z robustness sweep above.
6. **Mechanism-validation framing for the paper.** With the
   median-split rejection on Z and the discrete-event Granger null
   carried over, the ORDC mechanism is supported by `total_lmp`
   ≫ congestion but not by any direct event-conditional test on
   load volatility. Is the cite-the-PJM-2023-paper + show-the-4×
   evidence adequate, or does the paper need a stronger
   load-volatility-to-mechanism link?

**Revisit when.**
- After advisor meeting on the 6 open questions; each may produce
  a follow-up dated entry.
- After a quartile-split or continuous-ξ(Z) robustness run on the
  conditional-Z test produces a verdict on whether the median-split
  rejection generalizes. Pre-commit the spec before running, per
  the pre-registration discipline established 2026-05-13.
- If the τ = 0.99 secular sign flip resolves via a longer historical
  load-volatility window (would require widening the analysis window
  past 2022-10-02, which would re-introduce the ORDC pre-cap rule
  change — likely not pursued).

---

## 2026-05-14 — Pre-registration: conditional-Z robustness battery (A/C/F + gated B)

**Context.** The same-date production-findings entry above reported a
median-split conditional-Z GPD test with `shape_diff (high − low) =
−0.180`, bootstrap CI `[−0.371, −0.044]` (99% of replicates produced a
lighter tail in the high-Z subset) at the 95th-pct LMP threshold on
the full panel. That result rejects the specific hypothesis
*median-split, 95th-pct LMP threshold, full panel, Z = DOM load
gradient* — but the rejection's generalizability across split
granularity, threshold quantile, and signal-isolation filter is
open (open question 1 in that entry).

The 2026-05-14 build-decision entry's "Revisit when" section
contemplates a follow-up entry to govern QR/GPD code changes
addressing the open questions. The post-session memory carries a
"do not start QR/GPD code changes until advisor input" rule. This
entry is the principled relaxation of that rule: we lock decision
rules before any new specifications run, and the rules are committed
in writing before the implementation work begins. This is the same
discipline the 2026-05-13 pre-reg entry exemplified — written *before*
the n=1000 numbers were visible, applied mechanically after.

The robustness battery below is the minimum sufficient set to
distinguish the three competing readings of today's median-split
rejection:

1. **The rejection generalizes.** Tail-heaviness systematically
   decreases with load volatility across the Z distribution.
2. **The rejection is artifactual at the median.** Tail-heaviness has
   non-monotonic Z structure that a 2-way split mis-summarizes.
3. **The rejection is artifactual at the threshold or fails to
   replicate within the signal-isolation regime.** The 95th-pct LMP
   threshold pools moderate exceedances with ORDC-level ones (3a),
   or the conditional-Z relationship within the proposal's filtered
   regime (shoulder × 2–5 AM) does not match the full-panel result
   (3b).

Each spec below tests exactly one of these readings.

**Decision.** Run the **A/C/F battery** below before any further
substantive analysis on this sub-question. Decision rules apply
mechanically to the produced numbers. Spec B (continuous ξ(Z)
regression) is **gated** — it runs only on outcomes that demand a
smooth characterization the discrete specs cannot deliver.

### Spec A — Quartile-split conditional-Z at 95th-pct LMP, full panel

**What it tests.** Hypothesis (2): the median split is too coarse.
Partition exceedance Z values into quartiles Q1 (lowest Z) through Q4
(highest Z); fit GPD to each subset; report ξ trajectory across
quartiles plus bootstrap CI on the Q4 − Q1 contrast.

**Sample sizes** (forecast from production-findings entry):
n_exceedances ≈ 1,577 → ~394 per quartile. Adequate for stable GPD
fits.

**Primary decision criterion** — bootstrap 95% CI on `ξ_Q4 − ξ_Q1`:

| CI on (ξ_Q4 − ξ_Q1) | Verdict |
|---|---|
| Excludes 0, sign negative | Rejection generalizes at the extreme contrast (lowest vs highest Z quartile). |
| Excludes 0, sign positive | Proposal's hypothesis supported despite median-split rejection. The median-split was anti-conservative. |
| Spans 0 | Inconclusive on the extreme contrast; consult secondary monotonicity criterion. |

**Secondary criterion — monotonicity of ξ across quartiles:**

| Pattern | Combined verdict |
|---|---|
| Monotone (decreasing or increasing) — sign matches primary CI | Clean answer; primary verdict stands |
| Non-monotone (e.g., U-shape, inverse-U, single-quartile spike) | **Trigger Spec B** to characterize the smooth shape that discrete quartiles cannot capture |
| Approximately flat (max − min < 0.05) | No Z-dependence of tail shape; median rejection was sample-specific noise |

**Bootstrap protocol.** Pair-bootstrap (same protocol as the existing
median-split test): resample exceedance rows with replacement, refit
all four GPDs per replicate, compute the four ξ values, report the
empirical 95% CI on (ξ_Q4 − ξ_Q1) across replicates.

### Spec C — Median-split conditional-Z at 99th-pct LMP, full panel

**What it tests.** Hypothesis (3a): the 95th-pct threshold pools too
many moderate exceedances. At the 99th-pct threshold, only ORDC-stress-
relevant exceedances are included.

**Sample sizes** (forecast): n_exceedances ≈ 316 → ~158 per Z-half.
Tight; bootstrap CIs will be substantially wider than at the 95th-pct.
GPD fits at n = 158 with `fit_gpd`'s regularity assumptions: tractable
based on the existing module's tested ranges, but a `fit_gpd` failure
on either subset is a possible outcome (singular Hessian, ξ →
boundary). Pre-commit: failure is reported as **inconclusive due to
power**, not refit at a lower threshold ad hoc.

**Primary decision criterion** — bootstrap 95% CI on `shape_diff =
ξ_high − ξ_low`:

| CI on shape_diff | Verdict |
|---|---|
| Excludes 0, sign negative | Rejection persists at the deeper-tail threshold. Combined with A confirming, gives the strongest possible negative claim. |
| Excludes 0, sign positive | Threshold-dependent rejection: at 95th-pct rejection holds, at 99th-pct the proposal is supported. Important nuance; paper claim shifts to "the test variant matters." |
| Spans 0 | Underpowered at this threshold; no claim on this spec, do not generalize. |

### Spec F — Median-split conditional-Z within signal-isolation filter

**What it tests.** Hypothesis (3b): the conditional-Z tail-shape
relationship within the proposal's signal-isolation regime (shoulder
months Mar–May, Sep–Nov × 2–5 AM hours) — does it match the full-panel
rejection or differ from it? This is *not* a strict dilution test
(same LMP threshold value across full panel and filter); it is a
within-regime replication test (same nominal *quantile* threshold of
each regime's own LMP distribution).

**Sample sizes** (forecast): filtered n ≈ 2,027 hours; at within-subset
95th-pct LMP threshold, n_exceedances ≈ 101; median split gives ~50
per Z-half. **Substantially underpowered for GPD inference.** This is
acknowledged up front: the most likely outcome is a wide CI spanning
0, which is itself informative — it would mean the signal-isolation
filter does not deliver enough exceedances to discriminate the
hypothesis under the existing test framework, regardless of which
direction the truth lies.

**Threshold construction.** The 95th-pct LMP is computed **within the
filtered subset**, not inherited from the full panel. This ensures
the test operates on the filtered LMP distribution rather than
catching tail rows that happen to fall inside the filter.

**Primary decision criterion** — bootstrap 95% CI on `shape_diff =
ξ_high − ξ_low`:

| CI on shape_diff | Verdict |
|---|---|
| Excludes 0, sign negative | Rejection replicates within signal-isolated regime. Strong: the full-panel finding holds even after the proposal's own filter is applied. |
| Excludes 0, sign positive | Within-regime relationship reverses. The filter sees a different signal than the full panel — the paper's mechanism narrative must distinguish full-panel and signal-isolated regimes. |
| Spans 0 | **Most-likely outcome.** Filter is underpowered for tail-shape inference at within-regime 95th-pct; no claim. Failure to detect is not evidence of equivalence to the full-panel result. |

**Implementation failure mode.** If either subset's GPD fit fails
(n < 30 after the median split, singular fit, ξ → boundary): report
as fit-failure-due-to-power, do not lower the threshold ad hoc.

### Multiple-testing correction

Family-wise error rate at α = 0.05 across the three battery specs.
Apply **Holm–Bonferroni** ordering on the three bootstrap p-values
(**two-sided**, against H₀: shape_diff = 0). The sign of each spec's
shape_diff CI determines the direction of any rejection:

- Sort p-values ascending: p_(1) ≤ p_(2) ≤ p_(3).
- Reject H₀ at level (1) if p_(1) ≤ α/3 = 0.0167.
- Reject H₀ at level (2) if p_(2) ≤ α/2 = 0.025 *and* level (1)
  rejected.
- Reject H₀ at level (3) if p_(3) ≤ α = 0.05 *and* level (2)
  rejected.

Two-sided is used deliberately because the per-spec decision tables
above admit both sign directions as substantively meaningful — a
one-sided correction would suppress significant sign-positive
outcomes (e.g., Spec C reversing the rejection at the 99th-pct
threshold) that the entry already commits to reporting as
paper-reshaping findings.

The family-wise correction governs only the **headline family-wise
inferential statement**. Each individual spec's shape_diff and CI
are still reported verbatim alongside its unadjusted bootstrap
two-sided p-value. The correction is the threshold for making a
family-wise claim, not a filter on what gets reported.

### Roll-up verdict on "where does the response shift"

The post-battery overall verdict for the paper's central claim,
mapped from the battery outcomes:

| A | C | F | Overall verdict |
|---|---|---|---|
| Confirms (CI excludes 0, sign neg, monotone) | Confirms | Confirms | **Strong rejection.** Proposal's heavier-tail-at-high-Z hypothesis rejected at all three test variants. Paper headline. |
| Confirms | Confirms | Inconclusive | **Rejection holds** with explicit power caveat on the filtered subset. |
| Confirms | Inconclusive | Inconclusive | **Rejection holds** at the original threshold and split granularity, both power-caveat'd extensions inconclusive. |
| Confirms | Reverses (CI excludes 0, sign pos) | Inconclusive | **Threshold-dependent rejection.** The 95th-pct rejection is real, but at ORDC-relevant LMP levels (99th-pct) the proposal is supported. Major nuance. |
| Non-monotone | any | any | **Spec B triggered.** No paper-level verdict until continuous fit completes. |
| Flat | any | any | **Median-split was noise.** No Z-dependence of tail shape at this scope; the today's rejection was sample-specific. Paper claim updates to "no detectable Z-dependence." |
| Reverses (Q4 > Q1) | Reverses | Confirms (rejection) | **Pathological.** Methodology section gets a dedicated subsection. Investigate before drawing any conclusion. |

The "Confirms / Inconclusive / Inconclusive" row is the
power-realistic central scenario. Pre-committing that it counts as
"rejection holds" (rather than requiring all three to fire) prevents
post-hoc demands for unattainable Spec C / Spec F precision.

### Gated follow-up: Spec B — continuous ξ(Z) regression

**Trigger:** Spec A returns non-monotone ξ trajectory **or** Spec A
returns inconclusive primary CI **and** monotonicity is unclear.

**What it would test.** Fit GPD with shape parameter as a function of
Z: ξ(Z) = β₀ + β₁ · Z (linear) or a low-order spline. Maximum-
likelihood with Z as a covariate on the shape parameter.

**Why gated.** B is the methodologically richest spec but
substantially more involved to implement and validate. Building it
before A/C/F have run is overkill if A returns a clean monotone
verdict; building it conditionally on outcomes that genuinely demand
a smooth fit respects implementation budget. The trigger condition
above is the principled "no monotone discrete summary is adequate"
signal.

**If B runs:** decision rules for β₁'s CI will be written in a
follow-up dated entry. Pre-committing rules for an unspecified
parametric form is premature.

### Open questions explicitly *not* in scope of this pre-reg

The following are real methodology questions but they are not what
this battery tests; they get their own pre-reg if and when they're
pursued:

- **Different conditioning variable (Z = SR clearing).** The
  2026-05-13 5-min SR-clearing probe established this is a separate
  mechanism question, not a robustness check on the existing one.
- **τ = 0.99 secular sign flip.** Investigative refinement on a
  different result (QR-full year-FE decomposition), not on the
  conditional-Z test.
- **Ashburn TX1 negative point estimate.** Side-pnode question.
- **Discrete-event Granger.** Power-limited by sync_reserve_event
  sparsity; needs a different remedy.

### Rationale

Pre-registration's value rises sharply when the result space is
small and the temptation to retrofit is correspondingly high. Three
specs × three CI outcomes apiece = 27 result cells, of which several
have low-stakes interpretations and several would substantially
reshape the paper. Without pre-registered decision rules, the
combinatorics of "which subset of the results to feature" become a
post-hoc choice. With rules locked in writing, the choice is
mechanical.

The decision-rule tables above include the "spans 0" / inconclusive
outcomes as first-class results, not as defaults to be re-run with
modified specifications. A pre-reg that only governs significant
outcomes is an asymmetric pre-reg.

### Revisit when

- After the battery runs, a follow-up dated entry records mechanical
  rule application (paralleling 2026-05-13's "Application of pre-reg"
  entry).
- If A's outcome triggers Spec B, the B decision rules are written
  in their own dated entry before B runs.
- If the advisor meeting subsequently produces guidance that changes
  the battery's spec list (e.g., recommends running C at the 97.5th-pct
  instead of 99th-pct, or suggests an entirely different Z variable),
  a new dated entry overrides this one. We do not edit this entry
  post-hoc.
- If the implementation of any spec hits a regularity issue not
  anticipated above (e.g., `fit_gpd` fails on the full quartile-split
  battery, not just on a sparse subset), an implementation-note entry
  documents what changed, but the decision rules above stand unless
  the spec itself becomes uncomputable.

---

## 2026-05-14 — Application of pre-reg: conditional-Z robustness battery verdict + correction to prior production-findings entry's pnode labeling

**Context.** The same-date pre-registration entry locked decision rules for an A/C/F conditional-Z robustness battery before any new GPD fits ran. This entry records (a) a correction to the prior 2026-05-14 production-findings entry's pnode labeling, (b) mechanical application of the pre-reg's decision rules to the battery's production output on two responses (`total_lmp_rt_cluster_mean` via the orchestrator default; `congestion_price_rt_cluster_mean` via a manual one-shot), and (c) the verdict on sub-question 1.

**Production-run config.**
- Analysis panel: `data/interim/analysis_panel.parquet` (mtime 2026-05-12 23:09). 31,536 hourly rows, 2022-10-02 → 2026-05-07.
- Z (threshold variable): `dom_load_gradient_abs_mw_per_min`.
- Filter for Spec F: `passes_proposal_filter` (shoulder × 2–5 AM), n = 2,027 rows (6.43% of panel).
- Bootstrap: 200 reps per spec. Seeds: 0 (Spec A + per-pnode `run_gpd`), +100 (Spec C in orchestrator), +200 (Spec F in orchestrator).
- Code: `feature/conditional-z-robustness` branch — FF-merged into main after this entry.

### Correction to prior 2026-05-14 production-findings entry — pnode labeling

The prior 2026-05-14 production-findings entry's "Finding 6 — GPD conditional Z-split mechanism test" section prose specified `threshold = 95th percentile of cluster total_lmp_rt`, and reported `low-Z 789 / 0.788; high-Z 788 / 0.609; shape_diff = −0.180; CI [−0.371, −0.044]; one-sided p = 0.99`.

Re-running the deterministic per-pnode `run_gpd` calls tonight shows those numbers are an exact match for **primary (`congestion_price_rt_cluster_mean`)**, not for total_lmp. Cross-pnode evidence from `outputs/gpd/*.json`:

| pnode | response_col | shape_diff (high − low) | bootstrap CI 95% | one-sided p | CI excludes 0? |
|---|---|---|---|---|---|
| **primary** | congestion_price_rt_cluster_mean | **−0.1796** | **[−0.371, −0.044]** | 0.99 | **yes** |
| total_lmp | total_lmp_rt_cluster_mean | −0.0934 | [−0.236, +0.071] | 0.86 | no |
| ox | congestion_price_rt_ox | −0.1565 | [−0.309, +0.008] | 0.96 | no (barely) |
| bristers | congestion_price_rt_bristers | −0.1184 | [−0.269, +0.016] | 0.94 | no |
| dom_zonal | congestion_price_rt_dom_zonal | −0.0470 | [−0.161, +0.080] | 0.76 | no |

Per the decisions.md "don't edit the old entry — write a new one and reference the prior by date and title" convention, the prior entry remains in git history unchanged. This entry corrects the pnode labeling: the prior entry's numerical verdict (rejection at CI [−0.371, −0.044]) is **right for congestion (primary), the proposal's stated response**, not for total_lmp.

This correction is consequential: my Task 4 orchestrator wiring targets total_lmp per the prior entry's prose, so the default battery (`outputs/gpd/conditional_z_robustness.json`) tests the **inconclusive** variant (total_lmp), not the **rejected** variant (primary). A manual one-shot call ran the orchestrator on primary too, producing `outputs/gpd/conditional_z_robustness_primary.json`. Both batteries' numbers are below.

### Per-spec battery results

**Battery A/C/F on `total_lmp_rt_cluster_mean` (orchestrator default).**

Spec A (quartile-split at 95th-pct LMP, full panel, n_exceedances = 1,577):

| Quartile | Z edge | n | ξ |
|---|---|---|---|
| Q1 (lowest Z) | Z ≤ 2.72 | 395 | 0.6559 |
| Q2 | 2.72 < Z ≤ 5.70 | 394 | 0.6971 |
| Q3 | 5.70 < Z ≤ 10.17 | 394 | 0.5589 |
| Q4 (highest Z) | Z > 10.17 | 394 | 0.6025 |

Extreme contrast (Q4 − Q1) = **−0.0534**, bootstrap 95% CI **[−0.236, +0.127]**, two-sided p = **0.49**. CI spans 0. **ξ trajectory is non-monotone** (Q1 < Q2 > Q3 < Q4 — single Q2 spike).

Spec C (median-split at 99th-pct LMP, full panel, n_exceedances = 316):
- ξ_low = 0.4184 (n = 158), ξ_high = 0.3699 (n = 158).
- shape_diff = **−0.0485**, CI **[−0.339, +0.247]**, two-sided p = **0.83**. CI spans 0.

Spec F (median-split within filter, n_after_filter = 2,027, within-filter 95th-pct):
- ξ_low = 0.0444 (n = 51), ξ_high = 0.0829 (n = 51).
- shape_diff = **+0.0386** (**sign reversal direction**), CI **[−0.608, +0.601]** (very wide), two-sided p = **0.66**.

Holm-Bonferroni (sorted: spec_a 0.49, spec_f 0.66, spec_c 0.83):
- All p-values exceed their adjusted thresholds (α/3 = 0.0167, α/2 = 0.025, α = 0.05).
- **Family-wise rejection: False.**

**Battery A/C/F on `congestion_price_rt_cluster_mean` (manual one-shot — the proposal's stated response).**

Spec A (quartile-split at 95th-pct LMP, full panel, n_exceedances = 1,577):

| Quartile | n | ξ |
|---|---|---|
| Q1 (lowest Z) | 395 | 0.7377 |
| Q2 | 394 | **0.8396** (Q2 spike) |
| Q3 | 394 | 0.6071 |
| Q4 (highest Z) | 394 | 0.6035 |

Extreme contrast (Q4 − Q1) = **−0.1341**, bootstrap 95% CI **[−0.324, +0.064]**, two-sided p = **0.24**. CI spans 0. **ξ trajectory is non-monotone** (same Q2 spike pattern as total_lmp).

Spec C (median-split at 99th-pct LMP, full panel):
- ξ_low = 0.3462 (n = 158), ξ_high = 0.1434 (n = 158).
- shape_diff = **−0.2028** (negative direction, larger magnitude than median-split's −0.18), CI **[−0.458, +0.053]**, two-sided p = **0.21**. CI just barely spans 0.

Spec F (median-split within filter):
- ξ_low = 0.1088 (n = 51), ξ_high = −0.0246 (n = 51).
- shape_diff = **−0.1334** (negative direction), CI **[−0.639, +0.261]** (wide), two-sided p = **0.54**.

Holm-Bonferroni (sorted: spec_c 0.21, spec_a 0.24, spec_f 0.54):
- All p-values exceed their adjusted thresholds.
- **Family-wise rejection: False.**

### Per-spec verdicts and pre-reg roll-up

**Both batteries:** Spec A returns **non-monotone** ξ trajectories with primary CI spanning 0. Per pre-reg's Spec A secondary criterion ("Non-monotone → trigger Spec B to characterize the smooth shape"), **Spec B is triggered**. Spec C and Spec F are independently inconclusive on both batteries (CIs span 0 at family-wise α).

**For total_lmp:** the battery's verdict is consistent with the median-split's inconclusiveness on this response (median-split shape_diff = −0.093, CI [−0.236, +0.071]). The proposal's tail-shape prediction is **not testable at α = 0.05** on total_lmp at any of the four scopes (median + A/C/F).

**For primary (congestion, proposal's stated response):** the battery is **power-limited at the extension scopes** (Spec A's quartile split halves n per group; Spec C's 99th-pct halves it further; Spec F's filter cuts to ~50/half). The **median-split rejection from `outputs/gpd/primary.json` stands** at its own scope (n = 789/half, shape_diff = −0.180, CI excludes 0). The battery's extensions cannot sharpen or generalize this rejection because of power loss; they cannot reverse it either.

**Pre-reg roll-up verdict.** The pre-reg's roll-up table maps clean A/C/F triples to verdicts; tonight's outcome (A: spans 0 + non-monotone; C: spans 0; F: spans 0) is closest to the "Non-monotone → Spec B triggered" row, which **defers paper-level verdict** to Spec B for the smooth characterization. The "extreme contrast spans 0" outcome on both batteries also matches the pre-reg's "spans 0 → inconclusive on the extreme contrast" branch — power-limited at this resolution.

### Verdict on sub-question 1 — "where does the response shift"

The proposal's first sub-question asked: *"What is the critical volatility threshold of data center load variance that triggers a non-linear phase transition in Dominion Zone congestion pricing?"*

The answer, after the cumulative analysis:

1. **There is no single MW/min threshold.** Smooth-curve diagnosis (2026-05-13) established that the load-volatility → reserve-scarcity step is probabilistic, and the composite LMP-vs-Z relationship is smooth and monotonic, not piecewise. TAR's `ĉ` is filter-/resolution-/Z-variable-sensitive.

2. **The conditional mean-quantile response is positive and robust at moderate quantiles** (QR-full slopes z_slope = 0.39 / 0.58 / 0.36 at τ = 0.90 / 0.95 / 0.99 on the Loudoun-cluster congestion response, with the τ = 0.99 CI crossing 0). `total_lmp` z_slope is ~4× the congestion z_slope — direct support for the ORDC mechanism in the system-energy LMP component.

3. **On the proposal's stated response (Loudoun-cluster congestion), the conditional-Z mechanism test rejects the heavier-tail-at-high-Z hypothesis** at median-split, 95th-pct LMP threshold: shape_diff = −0.180, CI [−0.371, −0.044] (excludes 0). The high-load-volatility subset of LMP exceedances has a *lighter* GPD tail than the low-load-volatility subset — opposite to what the proposal predicted. The cross-pnode pattern is consistent: OX, BRISTERS, DOM_zonal all trend negative (lighter tail at high Z) but with CIs spanning 0 at their per-pnode n's.

4. **The robustness battery's higher-granularity extensions are underpowered** to either confirm or generalize the rejection. Spec A's quartile split halves n per group → CI [−0.324, +0.064] spans 0. Spec C at 99th-pct (n = 158/half) → CI [−0.458, +0.053]. Spec F within the filter (n = 51/half) → CI [−0.639, +0.261]. **The ξ trajectory across quartiles is non-monotone** on both batteries (single Q2 spike, then drop in Q3, flat to Q4) — per pre-reg, this **triggers Spec B (continuous ξ(Z) regression)** as a follow-up plan.

5. **The mechanism test is response-variable-sensitive.** On the same Loudoun cluster but total_lmp (not congestion), the median-split test is inconclusive (CI spans 0). The proposal's tail-shape prediction is rejected for congestion (the proposal's variable) and not testable-at-this-power for total_lmp. Methodologically, the choice of response variable is a load-bearing decision for this test — the paper should report both and discuss.

**Implication for the paper's headline.** Sub-question 1 has a real answer combining positive and negative findings:
- POSITIVE: moderate-quantile response is robust; ORDC mechanism is supported via `total_lmp` ≈ 4× congestion at τ = 0.95.
- NEGATIVE: the proposal's specific tail-shape mechanism prediction (on its own stated congestion response) is rejected at the median-split scope.
- METHODOLOGICAL: the tail-shape rejection is response-variable-specific; the higher-granularity robustness extensions are underpowered; Spec B (continuous ξ(Z)) is the natural next characterization step.

The paper's narrative: "the proposal's specific MW/min threshold framing is the wrong question for this data (smooth-curve diagnosis), but the proposal's mechanism prediction on its stated response is empirically rejected at median granularity, with the tail-heaviness *decreasing* with load volatility rather than increasing. Strategy C's QR-full slopes characterize the positive moderate-quantile response and the strong `total_lmp` differential supports the ORDC mechanism."

### Open methodology questions — status after this entry

From the 2026-05-14 production-findings entry's six open questions:

1. **"Conditional-Z rejection — true negative or median-split artifact?"** → **PARTIALLY RESOLVED.** On congestion, the median-split rejection is real (CI excludes 0); the quartile-split (Spec A) is underpowered to sharpen it but trends in the same direction. On total_lmp, the "rejection" was a pnode-labeling error; the actual median-split is inconclusive there.
2. **"τ = 0.99 secular sign flip."** → **STILL OPEN.** Independent investigation.
3. **"Ashburn TX1 negative point estimate."** → **STILL OPEN.** Side-pnode question.
4. **"GPD threshold choice for conditional-Z test."** → **PARTIALLY RESOLVED.** Spec C at 99th-pct on primary gives shape_diff = −0.20, CI [−0.46, +0.05] (just barely spans 0) — the negative direction generalizes to deeper threshold, but n = 158/half is power-limited. On total_lmp, Spec C is uninformative (CI [−0.34, +0.25]).
5. **"Multiple-testing correction."** → **RESOLVED** for both responses (Holm–Bonferroni two-sided at α = 0.05).
6. **"Mechanism-validation framing for paper."** → **REFRAMED.** With the corrected pnode labeling, the mechanism story is bifurcated: congestion shows the rejected tail-shape mechanism; total_lmp doesn't. Paper section should present both and treat the response-variable sensitivity as a methodologically interesting finding.

### Revisit when

- **Advisor input (Prof Wei / Lihui)** materially shifts the framing. Agenda at `docs/plans/2026-05-14-advisor-meeting-agenda.md`. Item 1's original framing options (clean negative / refinement / mechanism-substitution) are **back on the table** for the *congestion* result; the 2026-05-14 late-night reframe (commit `0a7239d`) is partially reversed by this entry.
- **Spec B (continuous ξ(Z))** triggered by both batteries' non-monotone Spec A trajectory. Spec B follow-up needs its own pre-reg + design + plan + execution. Until B runs, sub-question 1's verdict is "median-split rejection on congestion is real; higher-granularity behavior requires Spec B to characterize."
- **The orchestrator's wiring decision** — should `run_conditional_z_robustness` run on every pnode in `PNODE_RESPONSES`, or stay at total_lmp default? This Task 4-amendment question is for advisor / user input, not unilateral implementation. For tonight, the manual one-shot on congestion is the surgical workaround.
- **Longer historical window** to shrink CIs at higher-granularity scopes. Currently no path to extend without re-introducing the 2022-10 pre-cap break.

---

## 2026-05-14 — Pre-registration: Spec B continuous ξ(Z) regression (follow-up from conditional-Z battery)

**Context.** The same-date conditional-Z robustness battery pre-reg
("Pre-registration: conditional-Z robustness battery (A/C/F + gated B)")
specified that **Spec B is triggered if Spec A returns non-monotone ξ
trajectory or inconclusive primary CI**. The 2026-05-14
application-of-pre-reg entry recorded that both batteries (total_lmp
default + manual primary one-shot) produce non-monotone Spec A
trajectories with the single Q2 spike pattern. **Spec B is therefore
triggered.**

The original conditional-Z pre-reg deferred Spec B's decision rules to
"a follow-up dated entry before B runs." This is that entry. The Spec
B design spec is at
`docs/plans/2026-05-14-spec-b-continuous-xi-z-design.md`
(commit `3753b97`). Decision rules below are locked **before any
Spec B MLE fit runs**.

This entry exists for the same reason the conditional-Z pre-reg did:
to prevent post-hoc rationalization of decision boundaries after
results land. Spec B is more flexible than the discrete A/C/F battery
(continuous Z covariate on both σ and ξ), so the temptation to
retrofit a paper claim to whichever subset of the cross-pnode × cross-
threshold × cross-form results "tells the cleanest story" is real and
must be pre-committed away.

**Decision.** Apply the decision rules below mechanically to the
production output once `run_gpd_continuous_z` lands and runs on the
full panel. Any deviation requires a new dated entry explicitly
overriding this one; the rules below are not edited post-hoc.

### Rule 1 — Singular paper headline

The singular paper claim from Spec B is:

- **Pnode:** `primary` (Loudoun cluster congestion — `congestion_price_rt_cluster_mean`).
- **Threshold quantile:** 0.95 (matches the conditional-Z battery's Spec A scope).
- **Parametric form:** linear (ξ(Z) = β₀ + β₁·Z; σ(Z) = exp(σ₀ + σ₁·Z)).
- **Statistic:** β₁ point estimate + pair-bootstrap 95% CI + two-sided
  bootstrap p-value (= 2 × min(P(β₁ ≤ 0), P(β₁ ≥ 0)) clipped to [0,1]).
- **Significance threshold:** two-sided p < 0.05.

**All other Spec B output** (other pnodes, other thresholds, the
spline form, the LRT statistic) is **descriptive supplementary** and
is *not* subject to family-wise correction. The supplementary results
inform the paper's discussion but are not interpreted as
hypothesis-test rejections.

This singular-headline framing is itself the multiple-testing
mitigation: by pre-committing one test as the inferential claim, we
avoid the dimensionality (7 pnodes × 4 thresholds × 2 forms = 56
candidate tests) that would otherwise drive any α correction to be
either uninterpretable or so conservative as to be unrejectable.

### Rule 2 — Paper claim table

The decision-rule table maps the headline statistic to paper language:

| β₁ point estimate | β₁ bootstrap CI 95% | LRT spline-vs-linear (bootstrap p) | Paper claim |
|---|---|---|---|
| < 0 | upper bound < 0 (excludes 0) | not significant (p ≥ 0.10) | "Continuous fit confirms the median-split direction at α = 0.05: ξ decreases linearly with Z at rate β₁ = [value], bootstrap CI [...]. Median-split rejection (95th-pct, congestion) is sharpened." |
| < 0 | upper bound < 0 (excludes 0) | significant (p < 0.10) | "Continuous fit confirms direction (β₁ < 0) but the smooth ξ(Z) is non-linear (LRT p = [value]). Spline characterization shows [paragraph describing the shape]." |
| > 0 | lower bound > 0 (excludes 0) | n/a | "Continuous fit **CONTRADICTS** the median-split direction: β₁ > 0 implies heavier tail at higher Z, consistent with the proposal's original hypothesis. Headline reframes — median-split's negative shape_diff was scope- or sample-specific. This is the most paper-shaking outcome and requires careful additional sensitivity analysis before any narrative shift." |
| spans 0 | CI includes 0 | n/a | "Continuous fit is **underpowered** on this 3.6y window: β₁ = [value], bootstrap CI [...] (spans 0). The median-split rejection at 95th-pct is the strongest evidence the data supports; Spec B does not sharpen the conclusion. Paper acknowledges the power ceiling explicitly." |

The "contradicts" row is the paper-shaking outcome and is
pre-committed to require additional sensitivity analysis (re-running
with different MLE initial values, alternative bootstrap protocols,
profile-likelihood CI) before any narrative shift. The pre-reg locks
that any contradiction triggers extra scrutiny rather than an
immediate paper-narrative pivot.

### Rule 3 — Spline form interpretation

The 3-knot natural cubic spline fit produces a per-Z-grid evaluation
of ξ̂(Z) with bootstrap CI bands. This is reported descriptively even
when it does not enter the headline:

- If linear β₁ excludes 0 AND LRT not significant → "the linear
  approximation is adequate; the spline is reported for transparency
  but does not change the paper's claim."
- If linear β₁ excludes 0 AND LRT significant → "the headline
  direction holds but the smooth shape is informative; the spline
  visualization is the natural figure for the paper."
- If LRT significant AND linear β₁ spans 0 → "the headline test is
  underpowered, but the spline reveals non-monotonicity worth
  reporting. Headline reads 'inconclusive at the linear scope; spline
  characterization suggests [pattern]'."

### Rule 4 — Cross-pnode supplementary

All 7 pnodes' Spec B linear β₁ + CIs are reported descriptively. **No
family-wise correction across pnodes.** The cross-pnode comparison
informs paper narrative (does the rejection direction hold across
controls? distribution-side?) without itself being a hypothesis test.

The conditional-Z battery's per-pnode `shape_diff` already established
the cross-pnode pattern (primary rejects; controls trend negative but
spans 0; total_lmp inconclusive). Spec B's per-pnode linear β₁
supplements that with the smooth-fit version of the same comparison.

### Rule 5 — Threshold sweep supplementary

For each pnode, the 4 thresholds (90/95/99/99.5) are reported
descriptively. **No family-wise correction across thresholds.** The
threshold sweep tests whether the headline finding (at 95th-pct) is
artifactual at that threshold.

Pre-commit: convergence failures (MLE doesn't converge under BFGS +
Nelder-Mead fallback, or fewer than 100 successful bootstrap reps
remain) are reported as `convergence_status: "failed"` /
`"insufficient_bootstrap_reps"`. Not retried with different
initialization, not dropped from output. The honest reporting of
failures at small n is itself a paper-worthy methodological point.

### Convergence failure handling — pre-commit

| Failure mode | Pre-committed behavior |
|---|---|
| MLE doesn't converge (both BFGS and Nelder-Mead fail) | Mark `convergence_status: "failed"`, report fit parameters as NaN. No retry with different initial values. |
| Convergence succeeds but bootstrap has < 100 successful reps (out of 200) | Mark `convergence_status: "insufficient_bootstrap_reps"`, report CIs as (NaN, NaN). |
| `σ(Z) < 1e-6` or `(1 + ξ(Z) · u/σ(Z)) ≤ 0` for any exceedance during MLE | Log-likelihood returns +inf (MLE rejects). No ad-hoc clipping or transformation. |
| LRT statistic is negative (numerical issue) | Mark as NaN, do not interpret. |

The honest reporting of "failed" cells is preferable to opaque
retries. If 99.5th-pct headline fits fail across multiple pnodes,
that's a methodologically interesting finding (high-tail Spec B is
not estimable at our n).

### Open questions explicitly *not* in scope of this pre-reg

The Spec B design's "Open implementation questions to resolve in the
plan" section lists tactical decisions deferred to plan-writing
(initial value strategy, knot placement, Z-grid for spline curve
evaluation, numerical safeguards). These are tactical defaults and do
not affect the pre-reg's decision rules. They are documented in the
implementation plan, not here.

The following sub-q1 closure questions are *not* what Spec B tests;
they get their own work tracks (see
`docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`):

- **Response-variable sensitivity** (why congestion rejects, total_lmp
  doesn't) — separate diagnostic after Spec B's results.
- **τ=0.99 secular sign flip** — independent year-FE investigation.
- **Ashburn TX1 negative point estimate** — separate diagnostic.
- **Multiple-testing correction across the conditional-Z battery +
  Spec B family** — the singular-headline framing is the
  pre-committed answer; if a reviewer pushes back, a separate entry
  documents the rationale.
- **Profile-likelihood CIs as a robustness check** — deferred unless
  reviewers request.

### Rationale

The conditional-Z battery's pre-reg established the value of locking
decision rules before fits run: it prevents the combinatorics of
"which subset to feature" from becoming a post-hoc choice. Spec B's
result space (56 cross-pnode × cross-threshold × cross-form cells) is
larger than the conditional-Z battery's (3 cells in A/C/F), making
the post-hoc selection risk proportionally larger.

The singular-headline framing (Rule 1) is the principled response:
one test pre-committed as inferential; all other tests descriptive.
This is defensible to peer review because the headline is locked
before fit and is on the proposal's stated response at the
methodology-spec-default scope.

The decision table (Rule 2) covers all four mutually exclusive paper
claims, including the paper-shaking "contradicts" outcome.
Pre-committing the *response* to a contradicting result (extra
sensitivity analysis, not immediate narrative pivot) is the locking
move — without it, a positive β₁ could be retrofit to support the
proposal's original hypothesis without due diligence.

### Revisit when

- After Spec B runs on the production panel, a follow-up dated
  application-of-pre-reg entry records mechanical rule application
  (paralleling the 2026-05-14 conditional-Z application entry's
  pattern).
- If any "contradicts" outcome emerges, the pre-committed
  extra-sensitivity analyses get their own pre-reg in a separate
  dated entry.
- If the advisor meeting (Prof Wei / Lihui) produces guidance that
  changes Spec B's spec list (e.g., recommends profile-likelihood
  CIs as primary, or a different parametric form), a new dated
  entry overrides this one. The rules above are not edited post-hoc.
- If the implementation hits a regularity issue not anticipated above
  (e.g., MLE fails on all 7 pnodes at 99.5th-pct), an
  implementation-note entry documents what changed; the decision
  rules stand unless the spec itself becomes uncomputable.

---

## 2026-05-14 — Application of Spec B pre-reg: continuous ξ(Z) verdict

**Context.** The same-date Spec B pre-registration locked decision
rules before any non-stationary GPD fit ran. This entry records (a)
mechanical application of the Rule 2 paper-claim table to the
production-run outputs in `outputs/gpd_continuous/`, (b) supplementary
descriptive findings across pnodes and thresholds, and (c) the
resulting verdict on sub-question 1 with Spec B included.

The headline outcome is **"underpowered"** per Rule 2 (β₁ point
estimate negative direction but CI spans 0). Median-split rejection
on congestion at 95th-pct (recorded in the 2026-05-14
conditional-Z application entry) remains the strongest empirical
evidence the data supports.

**Production-run config.**
- Code: `feature/spec-b-continuous-xi-z` worktree (FF-merged into
  main after this entry). 213 tests passing.
- Implementation matches design + pre-reg with one tactical deviation
  documented in Task 1: polynomial-degree-3 basis [1, Z, Z², Z³]
  instead of natural cubic spline (matches 4-DOF intent without
  knot-placement decision; equivalent capability within observed Z
  range). Documented in Spec B implementation plan commit and the
  module's docstring.
- 7 pnodes × 4 threshold quantiles × 2 forms (linear + polynomial-3)
  × pair-bootstrap n_boot=200. ~50 min wall on the full 31,536-row
  panel; all fits converged with no `"failed"` or
  `"insufficient_bootstrap_reps"` statuses at production resolution.

### Headline result — Rule 1 application

Primary congestion (Loudoun cluster) @ 95th-pct LMP, linear form:

- **β₁ = −0.0080**
- bootstrap 95% CI: **[−0.0208, +0.0034]**
- two-sided bootstrap p-value: **0.230**
- LRT (spline-vs-linear) chi² = 5.34, asymptotic p = **0.068**

Per Rule 2's table, the row that applies is:

> **β₁ point estimate < 0 BUT CI spans 0 → "underpowered"**
>
> Paper claim: *"Continuous fit is underpowered on this 3.6y window: β₁ = −0.0080, bootstrap CI [−0.021, +0.003] (spans 0). The median-split rejection at 95th-pct is the strongest evidence the data supports; Spec B does not sharpen the conclusion. Paper acknowledges the power ceiling explicitly."*

The LRT borderline p (0.068, just under the "not significant" 0.10 cutoff in Rule 3) tilts the spline interpretation toward "the linear approximation is adequate; spline reported for transparency." No paper-shaking outcome.

### Cross-pnode summary at 95th-pct (linear form, descriptive)

All 7 pnodes converged. Direction is **consistently negative** (ξ decreases with Z) across every pnode. Magnitudes are small.

| Pnode | β₁ | Bootstrap CI 95% | Two-sided p | LRT p |
|---|---|---|---|---|
| primary (congestion) | −0.0080 | [−0.021, +0.003] | 0.230 | 0.068 |
| total_lmp | −0.0013 | [−0.012, +0.010] | 0.720 | 0.067 |
| ox (control) | −0.0081 | [−0.023, +0.003] | 0.190 | 0.085 |
| bristers (control) | −0.0079 | [−0.021, +0.007] | 0.260 | 0.122 |
| dom_zonal | −0.0035 | [−0.015, +0.007] | 0.540 | **0.033** |
| **ashburn_tx1** | **−0.0252** | **[−0.049, −0.004]** | **0.030** | NaN (degenerate LRT) |
| ashburn_tx2 | −0.0114 | [−0.033, +0.013] | 0.320 | 0.735 |

**Observations:**

1. **Sign consistency.** All 7 pnodes show β₁ negative direction — across primary, controls, zonal, and distribution-side. This is consistent with the conditional-Z median-split's cross-pnode pattern (all `shape_diff` negative, with primary the only one whose CI excluded 0).

2. **Ashburn TX1 is the only single-pnode rejection at α = 0.05.** β₁ = −0.0252, CI excludes 0, p = 0.030. **Per Rule 4** (cross-pnode supplementary, no family-wise correction), this is reported descriptively, not as a paper-level claim. Magnitude is ~3× the primary's |β₁| — consistent with the QR-full finding that Ashburn TX1 has wider response variance at distribution-level voltage. See "notable findings" below.

3. **DOM zonal LRT p = 0.033 (significant at α = 0.05).** This is the only single-pnode LRT rejection. The cubic non-linearity is detectable on the zonal aggregate. Per Rule 3, this would normally trigger a "non-linear shape is informative" footnote — but only the *headline* test's LRT (primary @ 95th) is interpreted at α = 0.05 by Rule 3; the cross-pnode descriptive LRT values are flagged here without family-wise correction.

### Threshold sweep — primary congestion (descriptive)

| q | n_exc | β₁ | CI 95% | Two-sided p | LRT p |
|---|---|---|---|---|---|
| 0.90 | 3,154 | −0.0075 | [−0.019, +0.002] | 0.090 | **0.007** |
| 0.95 (headline) | 1,577 | −0.0080 | [−0.021, +0.003] | 0.230 | 0.068 |
| 0.99 | 316 | −0.0280 | [−0.063, +0.002] | 0.070 | 0.259 |
| 0.995 | 158 | +0.0143 | [−0.070, +0.128] | 0.646 | 1.000 |

**Observations:**

1. **LRT p = 0.007 at 90th-pct** indicates the cubic non-linearity in ξ(Z) IS detectable at the larger n_exc. As threshold deepens (n_exc shrinks), LRT loses power: p = 0.068 at 95th, 0.259 at 99th, 1.000 at 99.5th. This suggests there IS a smooth non-monotonicity in ξ(Z) that median-split granularity (Spec A's 4-quartile pattern, where Q2 spiked) plausibly reflected.

2. **β₁ magnitude grows with threshold (0.90 → 0.99: −0.0075 → −0.028).** A 3.7× larger magnitude at the deeper threshold. This is consistent with the conditional-Z battery's 99th-pct sweep (Spec C in conditional-Z showed shape_diff = −0.20, more negative than median-split's −0.18). The Spec B continuous fit confirms the *direction* sharpens at deeper thresholds, but power loss prevents the rejection.

3. **99.5th-pct sign reversal at n_exc = 158.** Power-driven; CI very wide. Not interpreted.

### Notable cross-pnode findings (descriptive)

**Ashburn TX1's 99th-pct sign reversal.** At threshold quantile 0.99 (n_exc = 175), Ashburn TX1's β₁ flips sign to **+0.0932** (CI [+0.010, +0.167], p = 0.030) with LRT p = 0.000 — strong non-linearity. At 90/95/99.5 thresholds, β₁ stays negative. This is the most unusual single-pnode finding from Spec B. Three interpretations:

- (a) **Real distribution-side physics at extreme tail.** Ashburn (35 kV LOAD subtype) may have qualitatively different tail-shape behavior at ORDC-relevant levels vs. 500 kV transmission pnodes. The signal is detectable at the 99th-pct because that's where ORDC events concentrate.
- (b) **Power-driven artifact.** n_exc = 175 split into 4-parameter (linear) or 6-parameter (spline) MLE + bootstrap is fragile. The single-threshold anomaly with strong sign-flip + LRT = 0.000 looks like an over-fit on a small sample with one or two outlier exceedances.
- (c) **Data quality issue.** Ashburn pnodes have asymmetric coverage (only ~2y vs 3.6y for other pnodes per 2026-05-12 archive-mode decision); the 99th-pct exceedances are concentrated in fewer total hours.

Resolving this between (a)/(b)/(c) is the **"Ashburn TX1 diagnostic"** sub-q1 closure item (#4 in the roadmap). Spec B's evidence is descriptive; the paper's mechanism section should acknowledge Ashburn TX1 as a methodology footnote — not a headline finding.

### Verdict on sub-question 1 — final consolidated answer

After Spec B's results land, sub-question 1 has the following four-component answer:

1. **No single MW/min threshold.** Smooth-curve diagnosis stands.

2. **Moderate-quantile QR-full response is robust and positive.** z_slopes at τ = 0.90 / 0.95 are robust to bootstrap; τ = 0.99 underpowered. `total_lmp` ≈ 4× congestion at τ = 0.95 — direct ORDC mechanism support.

3. **GPD conditional-Z mechanism test on congestion (proposal's variable):**
   - Median-split (2026-05-14 conditional-Z entry, n=789/half): **rejects** at α = 0.05. shape_diff = −0.180, CI [−0.371, −0.044]. Direction: heavier tail at LOW load volatility (opposite of proposal's prediction).
   - **Spec B continuous fit (this entry, all panel data):** **underpowered at headline scope.** β₁ = −0.0080, CI [−0.021, +0.003] spans 0. Direction consistent with median-split (ξ decreases with Z), magnitude small.
   - **Deeper-threshold continuous fits** (99th-pct, n=316): β₁ = −0.028, CI just barely spans 0 (p = 0.07). Direction sharpens at deeper threshold; magnitude grows 3.5×; power-limited.
   - **LRT detects significant non-linearity at 90th-pct** (p = 0.007). The smooth ξ(Z) curve is not perfectly linear; some non-monotonicity exists in the smooth fit at the larger n_exc.

4. **Cross-pnode pattern:** all 7 pnodes have β₁ < 0 (continuous fit) and shape_diff < 0 (median-split). Direction is consistent across the cluster, controls, zonal aggregate, and distribution-side. Magnitudes are small for most; Ashburn TX1 is the only pnode whose continuous β₁ CI excludes 0 individually (with a 99th-pct anomaly that needs separate diagnosis).

**Implication for the paper's headline.** Sub-q1 has a defensible mixed answer:

- **POSITIVE finding (carries the paper):** moderate-quantile volatility-LMP response is robust; ORDC mechanism is supported via `total_lmp` ≈ 4× congestion.
- **NEGATIVE finding at median-split scope:** the proposal's heavier-tail-at-high-Z hypothesis on congestion is rejected at α = 0.05 (n=789/half). Direction is *opposite* to proposal's prediction.
- **CONTINUOUS-FIT honest acknowledgment:** Spec B is underpowered to sharpen the rejection at higher granularity. The direction is consistent across all 7 pnodes and across the threshold sweep, but only the binary median-split at headline n excludes 0. The paper acknowledges this power ceiling explicitly per the pre-reg.
- **METHODOLOGICAL contribution:** The cross-method consistency (median-split rejects, continuous fit underpowered but same direction, cross-pnode all same sign) is the strongest evidentiary triangulation the data supports.

The paper's narrative for sub-q1 reads as: "the proposal's MW/min threshold framing is the wrong question for this data; the smooth-response characterization shows positive moderate-quantile sensitivity with strong total_lmp / congestion differential consistent with ORDC; the mechanism test on the proposal's specific variable detects a direction opposite to the prediction at sufficient granularity but is power-limited at higher granularity. The 3.6y post-2022-10 window establishes the direction but cannot bound the magnitude precisely."

### Open methodology questions — status after this entry

From the 2026-05-14 conditional-Z application entry + this entry:

1. **Conditional-Z rejection — true negative or median-split artifact?** → **PARTIALLY RESOLVED.** Spec B's continuous fit on congestion is consistent with the rejection direction but underpowered to confirm at α = 0.05. Cross-pnode + cross-threshold sign consistency is evidence the direction is real; magnitude is bounded by the available n.

2. **τ = 0.99 secular sign flip.** → **STILL OPEN.** Independent investigation, not addressed by Spec B.

3. **Ashburn TX1 negative point estimate (QR-full) + 99th-pct sign reversal (Spec B).** → **NEWLY MORE OPEN.** Spec B sharpens Ashburn TX1 as a methodological anomaly: at 90/95 the β₁ is significantly negative; at 99th it strongly reverses (β₁ = +0.093, CI excludes 0 in positive direction, LRT p = 0.000). Worth a focused diagnostic before paper.

4. **GPD threshold choice for conditional-Z test.** → **RESOLVED.** Threshold sweep on primary (Spec B) shows β₁ magnitude grows with threshold (-0.008 → -0.028), confirming the direction generalizes to deeper tails; LRT p decreases with threshold (0.007 → 1.000), showing power loss at higher quantiles.

5. **Multiple-testing correction.** → **RESOLVED.** Singular headline (primary @ 95th-pct linear) was pre-committed; all other Spec B tests are descriptive per Rule 1. No family-wise correction applied to the larger family.

6. **Mechanism-validation framing for paper.** → **FURTHER REFRAMED.** With Spec B's underpowered headline, the paper's mechanism story now includes:
   - Mean-quantile mechanism: supported via `total_lmp` ≈ 4× congestion (positive at α = 0.05).
   - Tail-shape mechanism: rejected at median-split scope on congestion; underpowered at continuous-fit scope; consistent direction across all robustness tests.
   - The "direction is robust, magnitude is power-bounded" framing is the truthful position.

7. **Spec B (continuous ξ(Z)) triggered by both batteries' non-monotone Spec A** → **RESOLVED**. This entry.

### Sub-q1 closure status

Per `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`:

| Item | Status after this entry |
|---|---|
| #1 Spec B | **DONE** — this entry. |
| #2 Response-variable sensitivity diagnostic | Open. Spec B confirmed total_lmp's continuous β₁ is much smaller in magnitude (−0.0013) than congestion's (−0.0080), but the diagnostic is still useful for the paper's methods section. |
| #3 τ = 0.99 secular sign flip | Open. |
| #4 Ashburn TX1 diagnostic | **Newly sharpened** by Spec B's 99th-pct anomaly. |
| #5 Advisor meeting | Open. Now ready: Spec B verdict, cross-pnode evidence, threshold sweep, Ashburn anomaly are all available for discussion. |

The closure roadmap is updated accordingly: items 2-5 remain; #1 closed.

### Revisit when

- **Advisor input** materially shifts the framing. The "underpowered but direction-consistent" framing is the truthful position the data supports; an advisor may push toward emphasizing either the positive findings (QR-full) or the negative ones (median-split rejection on congestion).
- **Items 2-5** in the sub-q1 closure roadmap complete. The Ashburn TX1 diagnostic (#4) is now more interesting given the Spec B 99th-pct sign reversal — could be a paper-worthy finding if real, or a footnote if noise.
- **A longer historical window** that shrinks Spec B's CIs at higher granularity. Currently no path without re-introducing the 2022-10 pre-cap break.
- **A different conditioning variable Z'** (e.g., SR clearing price as Z). Separate scientific question.

## 2026-05-14 — Pre-registration: LMP-components decomposition (sub-q1 closure item #2)

**Pre-registration applies to sub-question 1 closure roadmap item #2.** Locks decision rules before the LMP-components decomposition fits run, per the discipline used for Spec B and the conditional-Z robustness battery.

### Rule 1 — Singular headline test (pre-committed)

The singular paper-level claim from item #2 is the **median-split conditional-Z test on `system_energy_price_rt_cluster_mean` at 95th-pct LMP**, on the primary Loudoun cluster, with Z = `dom_load_gradient_abs_mw_per_min`, applied to the filtered subset (`passes_proposal_filter=True`). This is the same scope as the 2026-05-14 conditional-Z battery's headline test on congestion (n=1577 at 95th-pct → 789/half), substituting the response variable.

All other tests run in the production phase are descriptive supplementary, including: (a) the same median-split applied to `congestion_price_rt_cluster_mean` and `marginal_loss_price_rt_cluster_mean` on the primary cluster; (b) cross-pnode supplementary across all 7 pnodes for each component; (c) threshold sweep at 90/95/99-pct LMP.

### Rule 2 — Decision-rule table for the headline

The test produces `shape_diff = ξ_high − ξ_low` with a pair-bootstrap 95% CI. Outcome interpretation (locked before any fit runs):

| Outcome | Paper claim |
|---|---|
| `shape_diff > 0`, CI excludes 0 | **Cancellation hypothesis supported.** system_energy carries the ORDC-predicted direction (heavier tail at HIGH Z); congestion's opposite-direction effect cancels it in total_lmp. This is the proposal's strongest mechanism-affirming outcome. |
| `shape_diff < 0`, CI excludes 0 | **ORDC-predicted direction rejected for system_energy too.** Heavier-tail-at-LOW-Z effect is broader than congestion; mechanism is NOT ORDC-specific. Sharpens the conditional-Z rejection rather than redirecting it. |
| CI spans 0, `shape_diff < 0` | **Underpowered;** direction consistent with congestion finding (heavier tail at LOW Z), not consistent with ORDC's predicted direction. Magnitude bounded only by the available n; paper acknowledges the power ceiling. |
| CI spans 0, `shape_diff ≥ 0` | **Underpowered;** direction consistent with ORDC's predicted direction (heavier tail at HIGH Z) but cannot confirm at this scope. Same power-ceiling language. |

**Mechanistic basis.** The PJM ORDC adds scarcity adders to the system marginal price when synchronized reserves drop below the demand curve threshold. Reserve drawdown is concentrated during high-load / high-volatility events → ORDC scarcity events concentrate at HIGH Z → system_energy_price spikes at HIGH Z → heavier tail at HIGH Z → `shape_diff > 0`. The 2026-05-14 conditional-Z battery's rejection on congestion produced `shape_diff < 0` (heavier tail at LOW Z, OPPOSITE direction to ORDC's prediction). The "cancellation hypothesis" predicts these opposite-direction effects partially offset when aggregated into total_lmp, explaining why the same median-split test on total_lmp was inconclusive in prior runs.

### Rule 3 — Spline/LRT layer

Not applicable to item #2 (median-split is binary, not continuous). Reference only.

### Rule 4 — Low-power skip rule

Any individual median-split test for which `n_exc / 2 < 50` reports status `insufficient_sample` and does NOT contribute a verdict line. The threshold of 50 matches the typical GPD MLE convergence floor on a 2-parameter (ξ, σ) fit, below which the asymptotic likelihood geometry becomes unreliable. Cross-pnode supplementary tests on Ashburn TX1 / TX2 at deep thresholds (99th-pct, 99.5th-pct) may trigger this rule.

### Rule 5 — Multiple-testing posture

Singular headline only at α=0.05. All other tests in the production phase are descriptive supplementary; reported with point estimates + bootstrap CIs but no family-wise correction. Matches Spec B's Rule 1 posture exactly.

### Revisit when

- Production fit results come in (write the application entry per Rule 2).
- Advisor input materially shifts framing.
- A different conditioning variable Z' becomes available (separate scientific question).

## 2026-05-14 — Application of #2 pre-reg: LMP-components decomposition verdict

**Context.** The same-date LMP-components pre-registration (above) locked decision rules before any GPD fit on the 4-component-decomposed LMP ran. This entry applies Rule 2 mechanically to the production outputs in `outputs/gpd_components/`, records the supplementary descriptive evidence, and notes implications for the paper's mechanism narrative.

The headline outcome is **`underpowered_pos_direction`** per Rule 2. Direction is consistent with ORDC's predicted heavier-tail-at-HIGH-Z effect on `system_energy`, but the bootstrap CI spans 0 at the available headline n. **No claim cleared α=0.05.** Paper-level headline framing for sub-q1 is deferred to the advisor meeting (sub-q1 closure item #5); this entry records what the production phase produced, not the paper narrative.

**Production-run config.**
- Code: `feature/sub-q1-batched-diagnostics` worktree. 240 tests passing pre-run. Production wall time 2h 8m (19:10–21:18 May 14 CDT).
- 4-component decomposition (`total_lmp`, `system_energy`, `congestion`, `marginal_loss`) at the cluster level (`*_price_rt_cluster_mean`) per `features.py` Task 1-2 pivot.
- Headline: median-split at 95th-pct LMP on the filtered subset (`passes_proposal_filter=True`), Z = `dom_load_gradient_abs_mw_per_min`, pair-bootstrap n_boot=200 for the shape_diff CI.
- Pre-reg reference: `docs/decisions.md § 2026-05-14 — Pre-registration: LMP-components decomposition (sub-q1 closure item #2)` (above).
- CIs reported across `headline.json`, `primary_cluster_supplementary.json`, `cross_pnode.json`, `threshold_sweep.json` come from separately-seeded pair-bootstrap runs of the same underlying test; minor CI differences (a few hundredths) across reporting locations reflect bootstrap variance, not data differences.

### Headline result — Rule 2 application

`system_energy_price_rt_cluster_mean` median-split @ 95th-pct LMP, primary Loudoun cluster, filtered subset:

- n_exc = 102, n_per_half = 51
- **shape_diff = +0.257**, bootstrap 95% CI: **[−0.543, +0.617]**
- **Rule 2 outcome:** `underpowered_pos_direction`
- Paper claim (verbatim from `headline.json`): *"Underpowered on this scope (n_per_half=51): system_energy direction consistent with ORDC's predicted direction (heavier tail at HIGH Z), shape_diff=0.257, CI [−0.543, +0.617] spans 0. Cannot confirm at α=0.05."*

n_per_half = 51 sits one above the Rule 4 floor (50), so the test reports a verdict but the GPD MLE asymptotic geometry is near its convergence boundary. The "underpowered" language is the truthful description; direction is informative as evidence-direction but not as a magnitude confirmation.

### Primary cluster supplementary at 95th-pct (descriptive, no MT correction)

From `outputs/gpd_components/primary_cluster_supplementary.json` — the two non-headline components on the same primary cluster + threshold + filter scope:

| Component | shape_diff | Bootstrap CI 95% | n_exc | Rule 2 outcome |
|---|---|---|---|---|
| congestion | −0.133 | [−0.690, +0.297] | 102 | underpowered_neg_direction |
| marginal_loss | −0.156 | [−0.949, +0.388] | 102 | underpowered_neg_direction |

Both non-headline components point in the OPPOSITE direction from `system_energy` (negative shape_diff = heavier tail at LOW Z, the direction the 2026-05-14 conditional-Z congestion entry rejected at the larger n=789/half scope). At the components scope (n_per_half=51), neither CI clears α=0.05, but the **direction divergence between `system_energy` (+0.257) and `congestion` (−0.133) is the empirical pattern the pre-registered "cancellation hypothesis" Rule 2 row 1 named.** Direction-level support exists; magnitude confirmation at α=0.05 does not.

### Cross-pnode supplementary at 95th-pct (descriptive, no MT correction)

From `outputs/gpd_components/cross_pnode.json`. Three components × five labeled non-primary pnodes (ashburn_tx1/tx2 trigger Rule 4 insufficient_sample on all three components due to n_per_half ≈ 27):

| Pnode | `system_energy` shape_diff [CI] | `congestion` shape_diff [CI] | `marginal_loss` shape_diff [CI] |
|---|---|---|---|
| ox | +0.257 [−0.587, +0.603] | −0.096 [−0.767, +0.332] | insufficient_sample |
| bristers | +0.257 [−0.544, +0.652] | −0.053 [−0.537, +0.390] | insufficient_sample |
| dom_zonal | +0.257 [−0.533, +0.533] | −0.075 [−0.527, +0.423] | +0.023 [−1.042, +0.323] |
| ashburn_tx1 | insufficient_sample | insufficient_sample | insufficient_sample |
| ashburn_tx2 | insufficient_sample | insufficient_sample | insufficient_sample |

**Two structural observations.**

1. **`system_energy` is identical to 13 decimals across all 4 DOM pnodes (primary cluster + ox + bristers + dom_zonal).** This is forced by PJM LMP decomposition: `system_energy_price_rt_<pnode>` is the slack-bus marginal energy price, identical at every node in a balancing area. The `_cluster_mean` aggregation over the Loudoun pnodes also collapses to the same series. **The cross-pnode supplementary test on `system_energy` is therefore one estimate replicated four times — NOT four independent observations.** The small CI differences across pnodes (CIs vary by ~0.1) reflect bootstrap reseeding alone. This is expected behavior, not a bug; it does mean cross-pnode "consistency" on system_energy carries no inferential weight beyond the headline.

2. **`congestion` is the only component with genuine nodal variation across the 4 labeled pnodes.** shape_diff ranges [−0.13, −0.05] — all NEGATIVE. None of the four CIs clear α=0.05 at this n_per_half=51 scope, but the **direction is uniformly consistent across the four pnodes**. This is the genuine cross-pnode evidence (vs system_energy's structural replication) and reinforces the 2026-05-14 conditional-Z congestion rejection (at n_per_half=789, shape_diff = −0.18, CI [−0.37, −0.04]) directionally at higher granularity.

3. **Ashburn pnodes are insufficient_sample on all three components at p95** (n_per_half ≈ 27 from n_exc ≈ 55 due to ~half the panel coverage from the 2026-05-12 archive-mode decision). Cannot contribute components-level evidence at this scope.

### Threshold sweep on primary cluster (descriptive)

From `outputs/gpd_components/threshold_sweep.json`:

| Quantile | n_exc | `system_energy` shape_diff [CI] | `congestion` shape_diff [CI] | `marginal_loss` shape_diff [CI] |
|---|---|---|---|---|
| 0.90 | 201–203 | +0.005 [−0.460, +0.316] | −0.140 [−0.463, +0.123] | −0.065 [−0.468, +0.321] |
| 0.95 (headline) | 102 | +0.257 [−0.444, +0.651] | −0.133 [−0.808, +0.334] | −0.156 [−0.853, +0.291] |
| 0.99 | 21 | insufficient_sample | insufficient_sample | insufficient_sample |

**Caveat on the p90→p95 magnitude jump on `system_energy`.** The point estimate moves from +0.005 (at n_per_half=100) to +0.257 (at n_per_half=51) — a 50× magnitude increase. The naive read is "direction sharpens at deeper threshold" (consistent with ORDC mechanism kicking in at tighter tail). The more conservative read is that **the GPD ξ MLE near the n_per_half=50 convergence floor is sample-fragile, and the +0.257 estimate sits in that unstable region.** The pre-reg's Rule 4 sets the floor at exactly 50, so n_per_half=51 satisfies the rule formally but the asymptotic likelihood geometry is on the edge. CI widening from [−0.46, +0.32] at p90 to [−0.44, +0.65] at p95 is consistent with both readings; **neither interpretation is supportable at α=0.05.** The honest framing is "direction is suggestive but magnitude is sample-fragile near the convergence floor."

`congestion`'s shape_diff is stable across p90/p95 (−0.13 to −0.14) — that direction-stability is NOT artifact-driven.

### Implication for sub-question 1

The components decomposition adds to sub-q1's mixed answer at the **direction** level without changing the **magnitude / α=0.05** verdict:

- **The opposite-direction pattern across components** (system_energy +0.26, congestion −0.13 on the primary cluster) is the empirical pattern the pre-registered "cancellation hypothesis" (Rule 2 row 1) named. This is direction-level support for the cancellation mechanism story.
- **No claim cleared α=0.05.** The headline CI on system_energy spans 0; both supplementary tables also span 0. The 2026-05-14 conditional-Z congestion rejection (at scope n=789/half, CI excluding 0) remains the only tail-shape α=0.05 result in sub-q1.
- **Cross-pnode `system_energy` "consistency" is structural** (zone-wide invariance), NOT independent replication. The genuine nodal-variation evidence is on `congestion` (4 pnodes, all negative, all CIs span 0 at this scope) — direction-consistent but magnitude-unsupported at n_per_half=51.
- **The threshold-sweep p90→p95 magnitude jump on `system_energy` is sample-fragile** at the GPD MLE convergence boundary, not a clean threshold-effect curve. The direction-sharpens-at-tail reading is suggestive but not supportable.

### Implication for the paper

**Paper-level headline framing for sub-q1 is deferred to the advisor meeting (item #5).** This entry records the mechanical Rule 2 dispatch and the supplementary descriptive evidence; the choice of which finding anchors the paper's abstract is a narrative decision that benefits from advisor input. The candidates with substantive evidence:

- Mean-quantile mechanism (QR-full positive z_slope at moderate τ; total_lmp ≈ 4× congestion) — α=0.05 cleared at τ=0.90/0.95.
- Median-split congestion conditional-Z rejection (anti-ORDC direction at scope n=789/half) — α=0.05 cleared.
- Opposite-direction-by-component decomposition (this entry) — directionally suggestive of the cancellation hypothesis, NOT cleared at α=0.05.

What this entry contributes is **direction-level evidence for the cancellation hypothesis without the magnitude confirmation the proposal sought.** Whether the paper leads with this, with the moderate-τ z_slope, or with the median-split rejection — the advisor meeting is the right venue.

### Revisit when

- Advisor input materially shifts framing for the paper's mechanism narrative.
- A longer historical window enables components-level fits at deeper thresholds (currently n_per_half=10 at p99; n_per_half=51 at p95 is one above the convergence floor).
- A different conditioning variable Z' becomes available (separate scientific question).

## 2026-05-14 — Sub-q1 item #3: τ=0.99 secular sign-flip diagnostic (descriptive)

**Context.** The 2026-05-14 Spec B application entry (above, line 1876) left open: at τ=0.99 the QR-full `z_slope` flips negative across most pnodes (e.g., ashburn_tx1: −5.57), contrasting positive `z_slope` at τ=0.90/0.95. The pre-registered case taxonomy was: (a) real grid improvement / downward p99 trend, (b) sparse-tail bootstrap artifact, (c) window-specific noise. The three-layer year-FE diagnostic decomposes each τ's `z_slope` into a primary specification and a year-FE-augmented specification, then pair-bootstraps the difference (`primary_z_slope − year_fe_z_slope`) as the **secular component**.

The headline τ=0.99 result is **case (b) sparse-tail bootstrap artifact**. All 7 pnodes' secular component CIs span 0 at τ=0.99; Layer 1 raw p99 trajectory directly contradicts case (a). The diagnostic also surfaces a **new moderate-τ finding the closure roadmap did not anticipate**: at τ=0.90/0.95 the secular component is POSITIVE and CIs EXCLUDE 0 on five of seven pnodes. This has implications for sub-q2 JLARC projection that warrant their own subsection.

**Production-run config.**
- Code: `feature/sub-q1-batched-diagnostics` worktree. Pair-bootstrap n_boot=200 for Layer 2 (year dummies) and Layer 3 (secular component).
- 7 pnodes (`primary`, `total_lmp`, `ox`, `bristers`, `dom_zonal`, `ashburn_tx1`, `ashburn_tx2`) × 3 taus (0.90, 0.95, 0.99).
- Response columns: `congestion_price_rt_cluster_mean` for `primary`; `total_lmp_rt_cluster_mean` for `total_lmp`; `congestion_price_rt_<pnode>` for the others.

### Layer 1 — Raw per-year p99 trajectory (descriptive)

From `outputs/year_fe_diagnostic/<pnode>.json` (`layer1_raw_per_year`). Empirical p99 of the response column per year, no Z involved:

| Pnode | 2022 (partial) | 2023 | 2024 | 2025 | 2026 (partial) |
|---|---|---|---|---|---|
| primary | 119.3 | 42.7 | 60.6 | 95.8 | **480.4** |
| total_lmp | 571.0 | 129.8 | 180.0 | 289.9 | **996.9** |
| ox | 122.8 | 53.5 | 66.2 | 108.4 | **483.6** |
| bristers | 123.3 | 52.3 | 59.0 | 92.0 | **488.8** |
| dom_zonal | 221.0 | 85.1 | 70.8 | 230.2 | 439.1 |
| ashburn_tx1 | — | — | 319.8 | 674.7 | 586.4 |
| ashburn_tx2 | — | — | 238.7 | 481.5 | 585.8 |

n_obs per year: 2022 has 2,185 obs (post-2022-10 cutoff); 2023–2025 have ~8,760 obs each (full year); 2026 has 3,047 obs (Jan–Apr partial). Ashburn pnodes have 0 obs in 2022/2023, ~5,641 in 2024, full year 2025, partial 2026.

**Observation.** The 2026 partial-year p99 is **4–10× any other year** across all pnodes. This is a **wide-pattern observation across pnodes**, not a single-pnode artifact. Case (a) "real grid improvement / downward p99 trend" is **directly contradicted** — 2026 is exceptionally bad, not improving. The 2025 → 2026 step on partial-year data is the dominant trajectory feature.

### Layer 2 — Year-dummy bootstrap @ τ=0.99, focus on the year_2026 dummy (descriptive, baseline=2022)

From `layer2_year_dummy_bootstrap.tau_0.99.year_2026` (the level shift relative to 2022 baseline). Pair-bootstrap CIs:

| Pnode | year_2026 dummy (point) | CI 95% | n_boot_conv |
|---|---|---|---|
| primary | +355.0 | [+236.6, +486.6] | 200 |
| total_lmp | +388.1 | [−338.2, +740.6] | 200 |
| ox | +340.1 | [+234.1, +464.1] | 200 |
| bristers | +341.7 | [+225.4, +470.5] | 200 |
| dom_zonal | +232.6 | [+132.2, +356.9] | 200 |
| ashburn_tx1 | +20.4 | [−94.3, +196.3] | 200 |
| ashburn_tx2 | +368.3 | [+284.3, +449.4] | 200 |

(Layer 2 is descriptive level shifts, NOT a trend test; the trend test is Layer 3.)

**Observation.** 2026 year-dummy excludes 0 on 5 of 7 pnodes (all except total_lmp and ashburn_tx1) with massive point estimates. Ashburn_tx1's year_2026 dummy is unique — small (+20) and CI spans 0. The 2026 spike at TX1 is concentrated where Z is concentrated, not at all τ=0.99 events.

### Layer 3 — Secular-component bootstrap (the trend test)

#### τ=0.99 — the sign-flip threshold

From `layer3_secular_component_bootstrap.tau_0.99` per pnode:

| Pnode | primary_z_slope | year_fe_z_slope | secular component (point) | secular CI 95% |
|---|---|---|---|---|
| primary | +0.357 | +0.622 | **−0.265** | [−0.890, +0.256] |
| total_lmp | +2.598 | +2.129 | **+0.468** | [−1.511, +1.861] |
| ox | +0.655 | +0.770 | **−0.115** | [−0.942, +0.788] |
| bristers | +0.636 | +1.116 | **−0.480** | [−1.021, +0.510] |
| dom_zonal | −0.395 | −0.006 | **−0.389** | [−1.225, +0.962] |
| ashburn_tx1 | −5.571 | −5.430 | **−0.141** | [−1.720, +0.927] |
| ashburn_tx2 | −2.272 | −1.539 | **−0.733** | [−3.740, +3.148] |

**All 7 pnodes have secular component CIs spanning 0 at τ=0.99.** The diagnostic cannot distinguish a real secular trend from noise at the tail. Combined with the Layer 1 evidence that 2026 p99 is 4–10× higher than prior years (not lower), this matches **case (b) "sparse-tail bootstrap artifact"** unambiguously:

- Case (a) ruled out by Layer 1 (no downward p99 trend; opposite trajectory).
- Case (c) "window-specific noise" is subsumed into (b) here — the sparse-tail GPD-like instability dominates over any meaningful window-specific signal.
- The τ=0.99 QR-full sign flip reported in Spec B is a sparse-tail estimator instability, not an interpretable trend.

For Ashburn pnodes specifically: `primary_z_slope` and `year_fe_z_slope` are both large negative (TX1: −5.6 / −5.4; TX2: −2.3 / −1.5), but the **difference** (secular component) is small (TX1: −0.14, TX2: −0.73). The τ=0.99 sign flip at Ashburn is NOT a year-FE-distinguishable secular effect — it survives both specifications and is consistent with the LOO-stable q=0.99 anomaly diagnosed separately in sub-q1 item #4.

#### τ=0.95 and τ=0.90 — the NEW moderate-τ finding (closure roadmap did not anticipate)

From `layer3_secular_component_bootstrap.tau_0.95` and `tau_0.90` per pnode:

**τ=0.95:**

| Pnode | primary_z_slope | year_fe_z_slope | secular component (point) | secular CI 95% |
|---|---|---|---|---|
| primary | +0.578 | +0.410 | **+0.168** | [+0.040, +0.275] ✓ |
| total_lmp | +2.334 | +1.389 | **+0.945** | [+0.547, +1.205] ✓ |
| ox | +0.612 | +0.408 | **+0.203** | [+0.051, +0.330] ✓ |
| bristers | +0.570 | +0.348 | **+0.223** | [+0.060, +0.347] ✓ |
| dom_zonal | +0.195 | +0.080 | +0.115 | [−0.055, +0.340] |
| ashburn_tx1 | −0.604 | −0.255 | −0.349 | [−0.646, +0.281] |
| ashburn_tx2 | +0.119 | +0.282 | −0.163 | [−0.505, +0.101] |

**τ=0.90:**

| Pnode | primary_z_slope | year_fe_z_slope | secular component (point) | secular CI 95% |
|---|---|---|---|---|
| primary | +0.393 | +0.251 | **+0.141** | [+0.090, +0.205] ✓ |
| total_lmp | +1.527 | +1.146 | **+0.381** | [+0.194, +0.566] ✓ |
| ox | +0.433 | +0.306 | **+0.128** | [+0.073, +0.196] ✓ |
| bristers | +0.403 | +0.283 | **+0.120** | [+0.071, +0.179] ✓ |
| dom_zonal | +0.354 | +0.175 | **+0.179** | [+0.108, +0.260] ✓ |
| ashburn_tx1 | +0.377 | +0.261 | +0.116 | [−0.075, +0.296] |
| ashburn_tx2 | +0.371 | +0.357 | +0.013 | [−0.075, +0.141] |

(✓ marks CIs that exclude 0.)

**Observation — the new finding.** At τ=0.90 and τ=0.95 the secular component is **positive** on 5/7 non-Ashburn pnodes with CIs **excluding 0**. This means `primary_z_slope > year_fe_z_slope` — the primary specification reports a larger response of LMP to Z than the year-FE-augmented specification does. Year-FE has absorbed something correlated with year that the primary spec was attributing to Z.

The most natural reading is that **year-2026's extreme partial-year (and to a lesser extent 2025's elevated p95) inflates the primary spec's z_slope unconditionally**; year-FE conditions out year-mean shifts and recovers a smaller within-year slope. But year-FE absorbs *everything* loading on year — weather, generation mix, topology, and 2026 partial-year selection — so the magnitude attribution between "secular drift" and "2026-specific event" is **not separately identified** by this diagnostic. The pre-registered interpretation taxonomy did not include this τ=0.95-positive case; it is reported here as descriptive evidence.

Ashburn pnodes diverge from the DOM-cluster pattern: at τ=0.95, both Ashburn secular components are NEGATIVE (TX1 −0.35; TX2 −0.16) with CIs spanning 0; at τ=0.90 both are positive but CIs span 0. The DOM-cluster's moderate-τ pattern does not extend to Ashburn — consistent with Ashburn's smaller window (2024–2026) absorbing year-FE differently.

### Implication for the paper

**Spec B's β₁ on the primary spec at moderate τ is partly attributable to year-correlated effects that year-FE absorbs.** The honest framing is: the proposal's central response coefficient is **the year-FE-residualized slope at τ=0.95** as a conservative bound, with **magnitude attribution between secular drift and the 2026 partial-year event unresolved by the diagnostic available here**.

Concretely for the paper:
- Spec B's headline β₁ = −0.008 at τ=0.95 on congestion is unchanged (different fit, different variable; not directly comparable to this entry's z_slope numbers, which are on the QR-full spec used by sub-q2 JLARC projection).
- The QR-full z_slope used in Spec C-strategy framing at moderate τ should be reported as **a range bounded below by the year-FE slope and above by the primary slope**, with the difference labeled "year-FE-absorbed component, attribution unresolved."
- The τ=0.99 QR-full numbers reported in Spec B should be flagged as **sparse-tail unstable** rather than interpreted as direction-reversal evidence.

### Implication for sub-question 2 (JLARC projection)

The JLARC projection layer at τ=0.95 should use **the year-FE-residualized slope** as the conservative, rigorous choice:

| Spec | primary z_slope @ τ=0.95 | year_fe z_slope @ τ=0.95 |
|---|---|---|
| congestion (primary cluster) | +0.578 | +0.410 |
| total_lmp (cluster) | +2.334 | +1.389 |

For sub-q2's "2030/2040 projection" framing: using year-FE @ τ=0.95 gives a more conservative price-trajectory estimate than using primary @ τ=0.95. The 2026 partial-window inflation would otherwise extrapolate non-conservatively.

At τ=0.99: **defer JLARC projection at τ=0.99** until a longer historical window stabilizes the tail. The current 3.6y window's τ=0.99 secular component CIs span 0 on all 7 pnodes; projecting from an unstable tail risks reporting a number more confident than the data supports. Sub-q2's headline projection table should anchor at τ=0.95 with τ=0.99 as a "directional caveat" sub-table.

### Revisit when

- Advisor input on the moderate-τ positive secular finding (it is descriptive new evidence; whether it warrants paper-level treatment is a narrative decision).
- A longer historical window pre-2022-10 enables clean year-FE without the 2022 partial-year + post-cap regime issues.
- Sub-q2 JLARC plan-writing — this entry feeds the projection-layer slope choice (year-FE > primary at τ=0.95).

## 2026-05-14 — Sub-q1 item #4: Ashburn TX1 99th-pct anomaly diagnostic (descriptive)

**Context.** The 2026-05-14 Spec B application entry (above, line 1876, "Notable cross-pnode findings") flagged Ashburn TX1's β₁ flipping sign at the 99th-pct threshold: at q ∈ {0.90, 0.95, 0.995} β₁ is negative (consistent with cross-pnode pattern); at q=0.99 β₁ = +0.0932 (CI [+0.010, +0.167], p = 0.030; LRT p = 0.000). The pre-registered case taxonomy was: (a) real distribution-side physics at extreme tail, (b) power-driven over-fit / outlier-driven sign flip, (c) data-quality issue from Ashburn's asymmetric coverage.

The diagnostic ran leave-one-out (LOO) re-estimation across all 4 thresholds for both TX1 and TX2, plus a 4-panel scatter overlay PNG. The headline outcome is **case (b) "power-driven over-fit" is ruled out**: the q=0.99 sign at TX1 is robust to dropping any single exceedance (0 of 175 LOO refits change sign; LOO stdev = 0.003 on a point estimate of +0.093). Cases (a) and (c) remain candidate explanations. **The TX2 cross-check is NOT independent evidence** (see rigor caveat below); it provides directional confirmation that the sign flip is not a TX1-specific artifact but cannot independently rule out case (c).

The honest framing this entry adopts: **a robust unexplained q=0.99 anomaly at the Ashburn substation worth flagging for the advisor meeting and for follow-up investigation**, not a paper-headline mechanism finding. The mechanism is undetermined; the robustness is what the diagnostic established.

**Production-run config.**
- Code: `feature/sub-q1-batched-diagnostics` worktree (commits `66528a4` + `6b93af9` for LOO + response-col fix).
- TX1 and TX2 LOO at 4 thresholds (0.90, 0.95, 0.99, 0.995). Each LOO refit is a deterministic GPD MLE (n_boot=0) on the exceedance set minus one observation; response column is `congestion_price_rt_<tx>` per the 2026-05-14 fix commit `6b93af9` (Spec B's anomaly is on congestion, not total_lmp).
- Cross-threshold β₁ + CI table (`cross_threshold_summary.json`) uses pair-bootstrap n_boot=200 for the full-sample β₁ CI at each threshold.
- 4-panel scatter overlay PNG at `outputs/ashburn_diagnostic/scatter_overlay.png` (TX1 + TX2 at p95 and p99).

### Cross-threshold β₁ (Spec B redux, n_boot=200, both Ashburn pnodes)

From `outputs/ashburn_diagnostic/cross_threshold_summary.json`. β₁ on the linear form, pair-bootstrap CIs:

| Threshold | TX1 β₁ [CI] | TX2 β₁ [CI] |
|---|---|---|
| q=0.90 | −0.0261 [−0.045, −0.010] ✓ | −0.0090 [−0.024, +0.008] |
| q=0.95 | −0.0252 [−0.049, −0.004] ✓ | −0.0114 [−0.033, +0.013] |
| **q=0.99** | **+0.0932 [+0.010, +0.167] ✓** | **+0.0232 [−0.012, +0.075]** |
| q=0.995 | −0.0262 [−0.110, +0.084] | −0.0009 [−0.144, +0.190] |

(✓ marks CIs excluding 0.) TX1 has CIs excluding 0 at q=0.90, q=0.95, and q=0.99 — significance at the q=0.99 threshold is in the OPPOSITE direction. TX2 has a point-direction agreement with TX1 at q=0.99 (both positive) but its CI spans 0.

### LOO summary at the q=0.99 anomaly threshold (TX1)

Derived from `tx1_loo.json` `loo_beta_1_distribution[]` at q=0.99 (n_exc = 175 LOO refits):

- **Full-sample β₁ = +0.09317** (matches Spec B cross-pnode entry exactly; pipeline sanity check passes).
- LOO mean = +0.09314, median = +0.09337.
- **LOO stdev = 0.00278** (3.0% of |full β₁|).
- LOO IQR = [+0.09187, +0.09494]; range = [+0.08304, +0.10070].
- **Sign-change LOO refits: 0 of 175 (0.00%).** Every single LOO refit remains positive.
- Top-5 most influential exceedances (sorted by |Δβ₁| = |full − loo|):

| Rank | exc-set idx | β₁_loo | Δβ₁ |
|---|---|---|---|
| 1 | 154 | +0.08304 | +0.01013 |
| 2 | 113 | +0.08436 | +0.00881 |
| 3 | 112 | +0.08475 | +0.00842 |
| 4 | 98 | +0.10070 | −0.00753 |
| 5 | 130 | +0.08641 | +0.00676 |

(Indices are positions in the threshold-filtered exceedance set, NOT panel row indices.) The most influential single exceedance shifts β₁ by ~0.010, leaving the LOO refit at +0.083 — still well above zero. Dropping the top influential exceedance does not change the sign.

### LOO summary at other thresholds (TX1 + TX2)

From `tx1_loo.json` and `tx2_loo.json`:

| Pnode | Threshold | n_exc | Full β₁ | LOO mean | LOO stdev | Sign-change refits |
|---|---|---|---|---|---|---|
| TX1 | 0.90 | 1,745 | −0.0261 | −0.0261 | 0.00024 | 0 / 1,745 |
| TX1 | 0.95 | 873 | −0.0252 | −0.0252 | 0.00038 | 0 / 873 |
| TX1 | **0.99** | **175** | **+0.0932** | **+0.0931** | **0.00278** | **0 / 175** |
| TX1 | 0.995 | 88 | −0.0262 | −0.0263 | 0.00529 | 0 / 88 |
| TX2 | 0.90 | 1,745 | −0.0090 | −0.0090 | 0.00020 | 0 / 1,745 |
| TX2 | 0.95 | 873 | −0.0114 | −0.0114 | 0.00038 | 0 / 873 |
| TX2 | **0.99** | **175** | **+0.0232** | **+0.0232** | **0.00164** | **0 / 175** |
| TX2 | 0.995 | 88 | −0.0009 | −0.0008 | 0.00570 | **26 / 88 (29.5%)** |

**Two methodologically relevant observations.**

1. **TX1 q=0.99 LOO is rock-solid.** Stdev 0.003 on point +0.093; every refit stays positive. Direct evidence the q=0.99 sign flip is **not driven by 1–2 outlier exceedances** — case (b) "outlier-driven over-fit" is ruled out for TX1 q=0.99. The same robustness holds at TX1 q=0.90 and q=0.95 (negative direction).

2. **TX2 q=0.995 shows 30% sign-change refits**, validating that the LOO methodology CAN detect fragile fits. This makes the TX1 q=0.99 0-sign-change result more meaningful as fit-stability evidence — the LOO isn't merely smooth across the board; it's smooth at TX1 q=0.99 specifically and fragile at TX2 q=0.995 specifically. The contrast is informative.

### TX2 cross-check — directional, not independent

TX2 q=0.99 β₁ = +0.0232 (same direction as TX1's +0.0932), LOO stdev 0.0016, 0 of 175 sign-change refits. Every TX2 q=0.99 LOO refit stays in the positive range [+0.010, +0.030].

**Rigor caveat: TX2 is NOT independent evidence of "real physics."** Both Ashburn TX1 and TX2 are pnodes at the same Loudoun substation, sharing the same local load environment, the same DOM-zone congestion signal, and overlapping data-coverage windows. The TX2 result is best interpreted as **directional confirmation that the q=0.99 sign flip is not a TX1-specific artifact within this substation** — useful, but it does NOT rule out case (c) "data-quality issue from Ashburn's asymmetric coverage" because TX2 shares the same asymmetric coverage window (~2y of data, 2024-04 onward).

What would constitute **independent** evidence of case (a) "real distribution-side physics":
- A second Ashburn-like 35 kV LOAD-subtype pnode in a DIFFERENT substation, also showing the q=0.99 sign flip — not in this data set.
- A pre-2024 historical replication of the q=0.99 sign flip at Ashburn — not available (Ashburn coverage starts 2024-04).
- Mechanism evidence connecting the Ashburn LOAD-subtype voltage class to a specific ORDC-relevant physical effect — outside the scope of the diagnostic.

### Caveats beyond LOO

LOO measures the **fit's robustness to single-observation exclusion**. It does NOT measure:
- **Temporal clustering of exceedances.** If TX1's 175 q=0.99 exceedances are concentrated in a specific window (e.g., specific months in 2025-2026), the sign flip could reflect window-specific physics rather than tail-shape physics. Diagnosing temporal clustering requires the timestamps of the exceedance set, which are not in this entry's input JSONs; this is a **follow-up check** worth running before the paper.
- **Selection effects from the proposal-filter.** The filter (`passes_proposal_filter`) selects shoulder-season + 2-5 AM observations to isolate the signal from supply-side spikes. If Ashburn's q=0.99 exceedances pass the filter at different rates than its q=0.95 exceedances (e.g., 0.99 exceedances disproportionately survive the filter from a different time-of-day pattern), the threshold-conditional fit is fitting different sub-populations of events.
- **Generative-model misspecification.** LOO confirms the fitted linear form is stable; it doesn't confirm the linear form is correct. The LRT p=0.000 at TX1 q=0.99 (Spec B cross-pnode table, line 1933) is evidence of strong non-linearity — a spline form at q=0.99 might capture a different qualitative shape than the linear β₁ suggests.

### 4-panel scatter overlay

`outputs/ashburn_diagnostic/scatter_overlay.png` shows TX1 + TX2 exceedances at q=0.95 and q=0.99, congestion-price vs Z. Pre-paper, this overlay is the natural place to check whether the q=0.99 exceedance cloud has a visually distinct shape vs the q=0.95 cloud and whether outlier influence would have been visually obvious. (PNG not embedded in this entry; reference path only.)

### Interpretation — which case does the evidence support?

- **Case (b) "outlier-driven over-fit" — RULED OUT.** LOO at TX1 q=0.99 has 0/175 sign-change refits and stdev 0.003. The q=0.99 sign is not contingent on any single exceedance.
- **Case (a) "real distribution-side physics" — POSSIBLE, NOT CONFIRMED.** TX2 directional agreement is consistent with case (a) but is not independent (co-located substation). The mechanism for why q=0.99 (and only q=0.99) would carry the opposite-direction effect is undetermined.
- **Case (c) "data-quality / asymmetric coverage issue" — POSSIBLE.** Ashburn pnodes have ~2y coverage vs ~3.6y for other pnodes; q=0.99 exceedance set may be temporally clustered in ways the LOO cannot detect.
- **Generative-model misspecification at TX1 q=0.99 (NEW open question)** — the Spec B LRT at TX1 q=0.99 was p=0.000 (strong non-linearity); the linear β₁ may not characterize the response shape correctly even given case (a). A spline-form re-fit at TX1 q=0.99 specifically is the next diagnostic.

### Implication for the paper

**Report as "a robust unexplained Ashburn-substation q=0.99 anomaly worth investigating," NOT as a paper-headline mechanism finding.** Specifically:

- **Methods-section subsection (not headline).** The LOO + cross-threshold β₁ table establish that the sign flip is stable and not outlier-driven; the mechanism is undetermined.
- **Caveat the TX2 cross-check** as directional, not independent.
- **Open questions for follow-up** (temporal clustering check, spline-form re-fit at q=0.99, mechanism investigation): list these explicitly so the paper section reads as "robust observation + open questions" rather than "explained finding."
- **Do not lead the paper with this finding.** The mean-quantile mechanism (QR-full positive z_slope) and the median-split congestion rejection (anti-ORDC direction) are stronger anchor candidates with α=0.05-cleared evidence.

### Revisit when

- Advisor input on whether the Ashburn anomaly warrants its own paper sub-section or remains a methods-section footnote.
- Temporal-clustering check on TX1's q=0.99 exceedances completes (requires loading the panel and inspecting the exceedance-set timestamps; not done in this entry).
- Spline-form re-fit at TX1 q=0.99 specifically (the LRT p=0.000 suggests non-linearity; a spline may characterize the q=0.99 shape qualitatively).
- A pre-2024 Ashburn data source or a second Ashburn-like 35 kV LOAD pnode at a different substation becomes available — would provide independent evidence for case (a).

## 2026-05-14 — Post-sub-q1 research agenda + sub-q1 framing clarification (item #6 added)

**Context.** A status-update conversation tonight surfaced that the
sub-q1 framing the user has been holding is **descriptive**, not
mechanistic: *"what range of load variance causes LMP to essentially
go crazy."* The work to date (items #1-4 in the sub-q1 closure
roadmap, plus the Strategy C / Spec B foundation) has been
**mechanism-focused** — testing whether ORDC's predicted direction
holds, whether components cancel, whether Ashburn TX1's q=0.99 sign
is robust. These tests imply the descriptive answer (positive z_slope
at τ=0.95 → higher Z drives higher conditional 95th-pct LMP) but do
not directly produce a clean *"Z in range [a, b] makes LMP cross
$X with probability P"* artifact.

This entry records two decisions made tonight in light of that
clarification:

### Decision 1 — Sub-q1 closure now includes item #6

Item #6 (direct Z → LMP tail-risk characterization) added to
`docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`. Items
#1-4 stay as **mechanism supporting evidence**, not replaced.
Sequenced **before item #5 (advisor meeting)** so the advisor sees
the complete sub-q1 picture (mechanism + descriptive
characterization) together. Design pending brainstorm; effort
estimate ~half a day implementation + ~1 hour design.

The descriptive question item #6 answers is closer to the
**proposal's original sub-q1 framing** (*"at what load-variance
threshold ... does LMP transition to heavy-tailed"*) than the
mechanism-first reframing used in items #1-4 was. The proposal's
threshold framing was already ruled out by the smooth-curve
diagnosis (2026-05-13); item #6 replaces "threshold" with "range"
and characterizes the smooth response empirically.

### Decision 2 — Post-sub-q1 research agenda (event correlation + time trends)

The user identified two follow-up directions explicitly **post**
sub-q1:

1. **Real-world event correlation.** Cross-referencing LMP-volatility
   events with PJM outage logs, weather incidents, named generation
   events — confirming volatility-driven extremes are NOT
   supply-side noise. This is **Phase 1/2 of the original SURG
   proposal**; mostly not done yet. The 2-5 AM + shoulder-season
   filter currently in use is a *coarse* version (excludes most
   supply-side spikes by construction); the follow-up sharpens it
   with specific event matching.

2. **Time-trend characterization.** "Do crazy events occur more
   often as more data centers come online?" This is **sub-q2
   (JLARC projection)**. The design + JLARC Rpt598-2 extraction +
   napkin-math are already shipped to `docs/plans/2026-05-14-jlarc-
   projection-*.md`; implementation plan-writing is gated on
   sub-q1 closure.

#### Mapping table

| User's framing | Project sub-q | Status |
|---|---|---|
| "What range of Z makes LMP crazy?" | sub-q1 item #6 (NEW, added tonight) | Design pending brainstorm |
| "Why does it happen?" | sub-q1 items #1-4 (mechanism work) | All DONE (`fe2cb94` / `01ebbd8` / `72456bb` / `fd0065c`) |
| "Are events related to real-world incidents?" | **sub-q3** (event correlation, NEW addition tonight) | Gated by sub-q1 closure |
| "Are events more frequent as more DCs come online?" | sub-q2 (JLARC projection) | Plan-writing gated by sub-q1 closure |

#### Gating order (locked tonight)

1. Sub-q1 item #6 — direct Z → LMP tail-risk characterization.
2. Sub-q1 item #5 — advisor meeting.
3. Sub-q1 paper-ready.
4. Sub-q2 (JLARC projection) plan-writing unlocks; design + execute.
5. Sub-q3 (event correlation) plan-writing unlocks; design + execute.

The unlocks are sequential because:
- Sub-q2's slope-choice depends on sub-q1's framing decisions
  (e.g., year-FE z_slope @ τ=0.95 was set tonight by item #3).
- Sub-q3's "what counts as an event" definition depends on
  sub-q1 item #6's output (e.g., if item #6 defines crazy LMP =
  P(LMP > $500 | Z > 5 MW/min) > 30%, sub-q3 looks at the
  timestamps in that intersection).

### Revisit when

- Sub-q1 closes fully (items #5 + #6 both done) — re-evaluate
  whether sub-q2 should start before sub-q3 or in parallel.
- A NEW finding from sub-q1 closure work (advisor meeting or item
  #6) materially changes the sub-q2 / sub-q3 framing.
- The user pivots priorities (e.g., decides event correlation
  should happen before JLARC projection).

## 2026-05-15 — Sub-q1 item #6: Direct Z → LMP tail-risk characterization (descriptive)

**Context.** Item #6 produces the direct descriptive answer to the user's
sub-q1 framing — *"what range of load variance causes LMP to essentially
go crazy"* — via binned exceedance-probability characterization. Design
spec at `docs/plans/2026-05-14-z-lmp-tail-risk-characterization-design.md`
(commit `6c7ebbb`); implementation plan at
`docs/plans/2026-05-14-z-lmp-tail-risk-characterization-implementation.md`
(commit `53a26b6`); module + tests on feature branch
`feature/sub-q1-item-6-tail-risk-curves` (10 commits through `0106294`).

Items #1-4 (mechanism work) stay as supporting evidence; this entry
records what the descriptive analysis found — including a substantive
methodological observation that affects how the user's stated question
can be answered.

**Headline.** Within the proposal-filter scope (shoulder seasons +
2-5 AM, n_total_filtered = 2,027 hourly observations), **exceedance
probability is 0.000 for $250 / $500 / $1000 / $2000 thresholds across
all 10 Z deciles and all 4 plotted pnodes**, and is bounded between
0.000 and 0.015 at the $100 threshold. The filter scope's LMP
distribution does not reach the chosen $-thresholds at any Z range.
The "crazy LMP region" question, as the user framed it, **is not
answerable within this filter scope at these threshold choices** — the
filter excludes the extreme-price events by design.

This is descriptive evidence in its own right, but it is not the
"high-Z makes LMP cross $500 with probability P" curve the design
spec targeted. See "Implication" sections below for what this means
for the paper + follow-up work.

**Production-run config.**
- Code: `feature/sub-q1-item-6-tail-risk-curves` worktree (FF-merged
  into main after this entry's commit). 15 module tests + 1 integration
  test passing pre-run.
- Filter: `passes_proposal_filter == True` (Mar-May + Sep-Nov shoulder
  seasons, 02:00-05:00 EPT). n_total_filtered = 2,027.
- 10 equal-count Z deciles on `dom_load_gradient_abs_mw_per_min`.
- 5 $-thresholds: $100, $250, $500, $1000, $2000.
- 2 response variables: `total_lmp_rt_*` + `congestion_price_rt_*`.
- 4 plotted pnodes (primary cluster, dom_zonal, ashburn_tx1, ashburn_tx2)
  + 3 additional in cross-pnode summary (total_lmp, ox, bristers) =
  7 pnodes total.
- Pair-bootstrap n_boot=200 for the CIs.
- Production wall time: ~47 min (legacy modules) + <1 min (tail_risk_curves itself).

### Z decile structure (primary Loudoun cluster)

From `outputs/tail_risk_curves/primary.json`. 10 equal-count quantile
bins of Z on the filtered subset:

| Decile | Z range (MW/min) | n_obs |
|---|---|---|
| 1 | [0.003, 0.504] | 203 |
| 2 | [0.504, 0.947] | 203 |
| 3 | [0.947, 1.409] | 202 |
| 4 | [1.409, 1.805] | 203 |
| 5 | [1.805, 2.291] | 203 |
| 6 | [2.291, 2.852] | 202 |
| 7 | [2.852, 3.507] | 203 |
| 8 | [3.507, 4.387] | 202 |
| 9 | [4.387, 5.653] | 203 |
| 10 | [5.653, 16.170] | 203 |

Decile 10's top range ([5.65, 16.17] MW/min) corresponds to the
high-volatility regime the proposal's mode-of-failure framing
invoked. The data-center growth scenarios in sub-q2 (JLARC) projection
would shift the right tail of this distribution upward.

### Threshold percentiles in the filtered panel

From `outputs/tail_risk_curves/primary.json` (`threshold_percentiles`):

| $ threshold | total_lmp pct | congestion pct |
|---|---|---|
| $100 | 0.9951 | 1.0000 |
| $250 | 1.0000 | 1.0000 |
| $500 | 1.0000 | 1.0000 |
| $1000 | 1.0000 | 1.0000 |
| $2000 | 1.0000 | 1.0000 |

(Percentile = P(LMP ≤ threshold) in the filtered subset.)

**Reading.** $100 sits at the 99.5th percentile of `total_lmp_rt_cluster_mean`
within the filtered subset; only ~10 of the 2,027 observations exceed
it. $250 and above are above the maximum observed LMP — the filtered
subset literally never reaches those values. Congestion is even
tighter: $100 already sits above the maximum filtered congestion
value.

### Top-decile exceedance probabilities (primary Loudoun cluster, decile 10: Z ∈ [5.65, 16.17] MW/min)

| Threshold | total_lmp P(LMP > $X) [CI] | congestion P(LMP > $X) [CI] |
|---|---|---|
| $100 | 0.0000 [0.000, 0.019] | 0.0000 [0.000, 0.019] |
| $250 | 0.0000 [0.000, 0.019] | 0.0000 [0.000, 0.019] |
| $500 | 0.0000 [0.000, 0.019] | 0.0000 [0.000, 0.019] |
| $1000 | 0.0000 [0.000, 0.019] | 0.0000 [0.000, 0.019] |
| $2000 | 0.0000 [0.000, 0.019] | 0.0000 [0.000, 0.019] |

(CIs from Wilson exact upper bound for the n_exc=0 case;
n_top_decile=203.)

### Per-decile $100 exceedance pattern on total_lmp (the only threshold with any signal)

| Decile | Z range (MW/min) | n_exc at $100 | P($100) |
|---|---|---|---|
| 1 | [0.003, 0.504] | 0 | 0.000 |
| 2 | [0.504, 0.947] | 1 | 0.005 |
| 3 | [0.947, 1.409] | 0 | 0.000 |
| 4 | [1.409, 1.805] | 0 | 0.000 |
| 5 | [1.805, 2.291] | 3 | 0.015 |
| 6 | [2.291, 2.852] | 2 | 0.010 |
| 7 | [2.852, 3.507] | 0 | 0.000 |
| 8 | [3.507, 4.387] | 2 | 0.010 |
| 9 | [4.387, 5.653] | 2 | 0.010 |
| 10 | [5.653, 16.170] | 0 | 0.000 |

Total exceedances at $100 across the full filtered panel: 10 of 2,027
observations (0.49%). Distribution is roughly uniform across moderate
deciles (5, 6, 8, 9) — no monotonic trend with Z. **The top decile (10)
has zero exceedances**, against the design spec's prediction that
high Z would push toward higher exceedance probability.

### Cross-pnode top-decile comparison

From `outputs/tail_risk_curves/cross_pnode_summary.csv`. All 7 pnodes
at decile 10:

| Pnode | Z top decile (MW/min) | n_top | total_lmp P($100) | congestion P($100) |
|---|---|---|---|---|
| primary (cluster_mean) | [5.65, 16.17] | 203 | 0.000 | 0.000 |
| total_lmp (alias) | [5.65, 16.17] | 203 | 0.000 | 0.000 |
| ox | [5.65, 16.17] | 203 | 0.000 | 0.000 |
| bristers | [5.65, 16.17] | 203 | 0.000 | 0.000 |
| dom_zonal | [5.65, 16.17] | 203 | 0.000 | 0.000 |
| ashburn_tx1 | [5.79, 16.17] | 109 | 0.000 | 0.000 |
| ashburn_tx2 | [5.79, 16.17] | 109 | 0.000 | 0.000 |

(Higher thresholds — $250 to $2000 — also all 0.000. See CSV for
full table.)

**Observation.** Ashburn pnodes have ~half the top-decile sample size
(n=109 vs n=203) because their data coverage starts in 2024 rather
than 2022-10. CIs are correspondingly wider (~3.4% vs 1.9% Wilson
upper). Direction-wise, no cross-pnode contrast emerges at this
threshold set — all pnodes uniformly produce 0% at $100+.

### The "crazy region" question — what the data actually shows

**Naive reading: no crazy region exists within the proposal-filter
scope.** Every (decile × threshold × pnode) cell except for ~10
isolated $100 exceedances on total_lmp has p_hat = 0.

**Why this happens.** The proposal-filter selects shoulder seasons +
2-5 AM specifically to exclude high-load summer afternoons + named
supply-side events. By construction, the filter removes the conditions
under which "crazy LMP" most commonly occurs. The filtered subset's
LMP distribution is concentrated in the $0-$100 range, with a
99.5th-percentile total_lmp value of approximately $100.

**This is not a null finding about "Z → LMP" — it is a finding about
the filter scope:** the filter does its job (isolates the volatility
signal from supply-side spikes), but it does so by removing the very
events the user's "crazy LMP" framing targets. The mechanism work in
items #1-4 was conducted on this filtered scope's tail (top percentiles
within the filter, not absolute $ levels), which is why the
conditional-Z congestion shape_diff = -0.18 result is meaningful even
though the absolute LMP values are mostly $0-$100.

**To answer the user's "crazy region" framing more directly, two paths
exist (neither was executed in this run):**

1. **Re-run item #6 with smaller thresholds calibrated to the filtered
   panel** — e.g., $25, $50, $75, $100, $150. Stays within the
   proposal-filter scope; characterizes Z → tail-shape at the magnitudes
   the filter actually produces. Pre-reg discipline-wise this would be
   post-hoc threshold selection, so any finding from this re-run should
   be flagged as exploratory.

2. **Re-run on the raw panel** (no filter) with the original
   $100/$250/$500/$1000/$2000 thresholds. Answers "where do crazy
   events occur in the full panel?" but mixes data-center-driven
   volatility events with supply-side spikes (the very thing the
   filter was designed to separate). This is closer to the user's
   stated question but methodologically less clean — sub-q3 (event
   correlation, NEW per 2026-05-14 entry) is the principled venue for
   this characterization.

The current production output is the honest answer to the
question-as-asked-with-the-design-as-specified. Path (1) or path (2)
would extend the answer with specific tradeoffs.

### Implication for the paper

The descriptive figure item #6 produces (4 per-pnode chart pairs +
1 cross-pnode summary) is **not the headline figure** the user's
stated framing imagined. The charts show flat-zero lines across most
panels, with the only visible signal being a sparse $100 exceedance
band in the moderate Z deciles (5-9) on total_lmp.

For the paper:
- The mechanism work in items #1-4 (conditional-Z congestion shape_diff
  rejection, opposite-direction-by-component pattern, Ashburn TX1
  q=0.99 anomaly) remains the empirical anchor. Those tests do NOT
  require LMP to reach absolute $-thresholds — they measure tail-shape
  changes within the filter's effective LMP range.
- Item #6's figure is best framed as a **methodology contribution**:
  "the proposal-filter scope, by isolating the volatility signal from
  supply-side spikes, also removes the absolute-magnitude extreme
  events; tail-shape mechanism testing within the filter is meaningful
  but absolute-magnitude characterization of 'crazy LMP' requires a
  different scope."
- Paper-headline framing is still deferred to advisor (item #5);
  item #6's contribution informs but does not anchor that decision.

### Implication for sub-q2 JLARC projection

The top-decile P(LMP > $X) curve is the natural input to a
"growth-shifts-Z-distribution → P(LMP > $X) increases" projection. But
since item #6's headline P_hat is 0 across the board, **there is no
useful empirical anchor for sub-q2's projection within this filter
scope.**

Sub-q2's projection design (per
`docs/plans/2026-05-14-jlarc-projection-design.md`) should anchor at
the **moderate-quantile z_slope** evidence (which items #3 and Spec B
established at τ=0.95) rather than at absolute $-threshold exceedance
probabilities. This is consistent with the 2026-05-14 item #3 entry's
recommendation to use the year-FE-residualized slope at τ=0.95 as the
conservative bound.

### Revisit when

- Advisor input (item #5) on whether to re-run with calibrated
  thresholds or accept the methodology-contribution framing.
- Sub-q3 (event correlation, new addition tonight) — would produce
  the raw-panel "crazy region" characterization with explicit
  supply-side event flags.
- The proposal-filter is re-evaluated (e.g., expanded to include
  high-load summer hours) — the descriptive results would change
  qualitatively.
- A longer historical window (pre-2022-10) is added to the panel —
  the filtered scope might capture different LMP magnitudes.

---

## 2026-05-15 — Sub-q1 item #8: 5-min companion run (pre-reg)

**Context.** Sub-q1 closure (items #1–4 + #6) shipped at hourly
resolution. The advisor meeting (item #5) is stronger if mechanism +
descriptive findings come with a 5-min companion + an honest
accounting of what 5-min granularity adds. Initial brainstorm
assumed a 3.6y 5-min companion; API verification on 2026-05-15
revealed `inst_load` is hard-capped at ~30-day PJM retention
(`pjm-api-constraints.md:84`), making the joint Z+LMP analysis
feasible only on a ~30-day window. 5-min LMP-only data is
available for ~6 months on disk.

**Decision.** Execute item #8 in two parts per the design at
`docs/plans/2026-05-15-5min-companion-design.md`:

- **Part A.** Items #1–4 + #6 on a joint 30-day Z+LMP panel
  (mid-Apr → mid-May 2026). Pre-registered as a feasibility probe —
  every CI is expected to span 0; the run documents the data wall
  in concrete numbers. Bootstrap: pure island cluster bootstrap
  (proposal-filter creates 3-hour islands separated by 21-hour gaps;
  ~30 islands in window; below the 50-cluster floor for
  cluster-bootstrap CI reliability — also pre-registered).
- **Part B.** Single new module computing 5-min vs hourly
  spike-exceedance comparison on the full 6-month LMP panel.
  Headline comparator: PJM-published `total_lmp_rt` from
  `rt_hrl_lmps`. Output: hidden-fraction by threshold per pnode.
  Descriptive only; no inferential CIs.

Implementation per
`docs/plans/2026-05-15-5min-companion-implementation.md`. Execution
via slash command `/run-5min-companion` (plan-driven launcher,
≤ 4000 chars). Sibling worktree `../surg-5min-companion/`, commit
per task, NO FF-merge, NO push.

**Rationale.** The data-retention wall is a hard constraint, not a
framing choice. Pre-registering the underpowered expectation
prevents post-hoc "5-min looks the same" disappointment from being
reframed as a finding; pre-registering the sub-50-cluster floor
flag prevents post-hoc CI-noise from being read as substantive
uncertainty. Part B is decoupled from Part A's Z constraint, giving
an independently useful descriptive deliverable ("what does PJM
hourly aggregation hide about 5-min spikes").

**Revisit when.** Either (a) a longer-history 5-min DOM-load
source surfaces (different PJM feed, advisor's private dataset,
EIA), in which case Part A re-runs on a real window, or (b)
advisor (item #5) reframes which resolution is the headline.

---

## 2026-05-15 (late) — Deliverable structure for sub-q reports

**Context.** With sub-q1 analytically closed (only advisor meeting
remaining) and sub-q2 / sub-q3 plan-writing about to unlock, this
entry codifies the deliverable expectation so all three sub-q
write-ups follow a consistent structure.

**Decision.** Each sub-q produces:

1. **A standalone report** (markdown) explaining: the question, the
   approach, what we found, what's still open, what the limitations
   are.
2. **Supporting graphs** that visualize the headline findings.
3. **Hybrid technical + accessible prose**: a technical reader gets
   precise method + statistics; a non-technical reader gets the
   intuition, the framing, and the takeaway. Write ONE document
   that does both — technical detail in subsections or appendices,
   intuition in the main flow. Do not write two separate reports
   for the same sub-q.

**Rationale.** The SURG audience includes both research-savvy
faculty advisors and policy-oriented stakeholders (JLARC,
Northwestern admin reviewing the grant). A report that's only
technical loses the policy audience; one that's only accessible
loses methodological credibility. Hybrid prose with clear
segmentation (technical-detail vs intuition-flow) serves both.

**Sub-q2 narrative addition** (per same-date conversation):
Sub-q2's report must connect the projection math to physical-grid
+ policy realities. Explicitly include external context:

- Data center construction pace in NOVA (JLARC Rpt598-2 + newer
  announcements as they emerge)
- Transmission line expansion in DOM zone (Pleasant View - Ashburn,
  Goose Creek transformer upgrades)
- Distributed compute trends (e.g., Nvidia's late-2025/early-2026
  proposal for residential-co-located mini data centers — changes
  the spatial concentration assumption)
- Other policy-relevant news/events as they emerge

**Sub-q1 stays focused** on analytical findings without external-
event context (its scope is mechanism + characterization on existing
data, not policy projection).

**Sub-q3** scope is event-correlation; external news incorporation
TBD when plan-writing unlocks.

**Implementation.** CLAUDE.md updated this date with:
- Sub-q1/2/3 split + gating order
- Per-sub-q deliverable expectation
- Sub-q2 specific narrative scope
- Refreshed Phase 3 methodology section (replacing stale 2026-05-11
  TAR-as-primary reference with current Spec A/B + QR-full + item
  #6/9 picture)

**Revisit when.**
- Sub-q1 paper is drafted — verify the report structure works for
  the audience as designed.
- Sub-q2 plan-writing begins — re-evaluate which external-event
  sources are most material; commission a brief literature/news
  scan as part of the design phase.
- A new sub-q is added or the existing scope shifts.

## 2026-07-18 — Sub-q1 5-min two-sided companion: pre-registration

**Design:** `docs/superpowers/specs/2026-07-17-5min-two-sided-companion-design.md`
(commit `6492184`). This entry locks every spec BEFORE any 5-min pull
or result computation. Data limitation, disclosed once here and once in
the eventual methods/limitations section: Z is measured via gridstatus's
`pjm_load.dom` column, which is empirically identical to PJM's
Southern-Region aggregate 5-min load.

**Window (locked):** `2025-06-24T04:00Z -> 2026-06-24T04:00Z` (1 year,
verified against `latest_available_time_utc` on 2026-07-18 — both
`pjm_load` and `pjm_lmp_real_time_5_min` report availability through
2026-07-18, well past the window's end, so the design's default window
is kept unchanged).

**Panel:** Z = `(dom_t − dom_{t−1}) / 5` MW/min, no smoothing, native
5-min cadence. LMP = `pjm_lmp_real_time_5_min` for pnodes 35010365
(LOUDOUN), 35010371 (PLEASANT VIEW), 1356178195 (GOOSECRE); cluster =
mean over these 3 (narrower than the hourly 6-pnode cluster —
disclosed). Filter = shoulder months × 2–5 AM EPT, unchanged.

**Pnode filter validation (pre-pull check, 2026-07-18):** the pull
design filters `pjm_lmp_real_time_5_min` by `location_id` (not
`location_short_name`, the only form previously empirically validated
per `docs/gridstatus-api-constraints.md`'s 2026-05-15 probe). Before
committing quota to the full pull, a 1-day/1-pnode probe (LOUDOUN,
35010365, 2026-03-02) confirmed `location_id` filtering returns exactly
the requested pnode (283/283 rows, zero cross-contamination) with the
LMP identity (`energy+congestion+loss == lmp`) holding exactly (0
violations). `location_id` filtering is confirmed safe to use for the
full pull.

**Test 1 — QR-full z_slope** (τ = 0.90/0.95/0.99; primary read at 0.95;
responses: 3 per-pnode congestion + cluster congestion + cluster
total_lmp; iid pair-bootstrap, qr_n_boot=500, seed=42, matching the
hourly method for comparability; year-FE auto-skipped, 1-year window):
- Hourly prior: positive slope, CI excluding 0, on 5/7 response labels
  at τ=0.90/0.95.
- CONFIRMS: ≥2 of the 3 per-pnode congestion fits at τ=0.95 have
  positive z_slope with bootstrap CI excluding 0.
- CONTRADICTS: ≥2 of 3 have negative z_slope with CI excluding 0.
- UNDERPOWERED/MIXED: anything else.

**Test 2 — Spec A median-split GPD on cluster congestion**
(threshold_quantile=0.95, z_split=median, n_boot=1000, seed=42):
- (a) Full-panel, iid exceedance bootstrap — direct comparator to the
  hourly prior shape_diff = −0.180, CI [−0.371, −0.044].
  CONFIRMS the hourly rejection: shape_diff < 0 with 95% CI excluding 0.
  CONTRADICTS: shape_diff > 0 with CI excluding 0. Else UNDERPOWERED.
- (b) In-filter, island-cluster bootstrap (night-islands ≈ 180;
  above the 10-cluster floor enforced in code). Same rules; secondary
  read.

**Test 3 — Decile tail-risk curves** (in-filter; thresholds
$100/$250/$500/$1000/$2000; n_boot=1000, seed=42): descriptive only.
Report decile monotonicity and d10/d1 exceedance ratios next to the
hourly item #6/#9 values; no confirm/contradict rule.

**Quota discipline:** preflight `GET /api_usage`; abort if remaining
monthly rows < 430,000 OR remaining monthly requests < 150 (both
independently guarded in `check_quota()`). ~420,480 rows, ~54 requests
expected for the full pull. As of this entry, 2/250 requests and
812/500,000 rows have been used this billing period (metadata check +
pnode-filter probe above) — comfortable headroom remains.

**Revisit when:** the results entry lands (same title, "results"
suffix), or the advisor meeting (item #5, deferred to post-run/pre-sub-q2)
reframes which resolution is the headline.

## 2026-07-19 — Sub-q1 5-min two-sided companion: results

**Data limitation, disclosed per the pre-reg:** Z is measured via
gridstatus's `pjm_load.dom` column, empirically identical to PJM's
Southern-Region aggregate 5-min load. Additionally, the pull found
~0.1-0.4% sparse interval gaps in both `pjm_load` and
`pjm_lmp_real_time_5_min` (identical missing timestamps across all 3
pnodes, scattered across the year) — a genuine upstream feed gap, not
recoverable via re-pull (`docs/gridstatus-api-constraints.md`). Panel:
105,019 rows; the 52 gap-adjacent rows have their gradient NaN-masked
rather than computed across a missing interval.

**Correction to the pre-reg's Test 1 framing:** the pre-reg stated
"year-FE auto-skipped, 1-year window." This is incorrect — the window
runs 2025-06-24 → 2026-06-24, crossing a calendar-year boundary, so the
panel contains 2 distinct years and `run_qr_full`'s year-FE spec ran
normally (it only skips when < 2 distinct years are present, per its own
guard). Both specs are reported below for transparency; they agree
qualitatively.

**Test 1 — QR-full z_slope @ τ=0.95.** Verdict per Task 13's
pre-registered rule: **UNDERPOWERED/MIXED**. All 5 responses have
bootstrap CI spanning 0 in both the primary and year-FE specifications:

| Response | Primary z_slope | Primary 95% CI | Year-FE z_slope | Year-FE 95% CI |
|---|---|---|---|---|
| loudoun (congestion) | −0.0013 | [−0.0275, +0.0034] | −0.0119 | [−0.0561, +0.0181] |
| pleasant_view (congestion) | −0.0029 | [−0.0271, +0.0014] | −0.0057 | [−0.0293, +0.0033] |
| goosecre (congestion) | −0.0028 | [−0.0282, +0.0016] | −0.0058 | [−0.0299, +0.0022] |
| cluster (congestion) | −0.0031 | [−0.0295, +0.0007] | −0.0055 | [−0.0330, +0.0024] |
| cluster (total_lmp) | +0.0040 | [−0.0870, +0.1060] | +0.0399 | [−0.1018, +0.1655] |

0/3 per-pnode congestion fits reach the pre-reg's ≥2/3-with-CI-excluding-0
bar in either specification. Materially weaker than the hourly companion
(positive + significant on 5/7 labels at the same τ).

**Test 2 — Spec A median-split GPD on cluster congestion.** Verdict per
Task 13: **UNDERPOWERED** on both variants.

| Variant | shape_diff | 95% CI | one-sided p (H1: diff > 0) |
|---|---|---|---|
| (a) Full-panel, iid bootstrap | −0.034 | [−0.100, +0.033] | 0.834 |
| (b) In-filter, island-cluster bootstrap | −0.022 | [−0.346, +0.250] | 0.576 |

Both point estimates run the same direction as the hourly Spec A
rejection (shape_diff = −0.180, CI [−0.371, −0.044]) — heavier tail at
*low* Z, not high — but neither CI excludes 0 at 5-min resolution. (The
listed p-value tests only the original proposal's hypothesized direction,
shape_diff > 0; the verdict above is based on the CI, per the pre-reg's
actual rule, not this p-value.)

**Test 3 — Decile tail-risk curves** (in-filter, descriptive, no
confirm/contradict rule). At the $100 threshold: no monotonic increase
toward decile 10. Congestion is flat (d10/d1 = 1.0: decile 1 p̂=0.0046,
decile 10 p̂=0.0046, n_exc=3 both); total_lmp *decreases* at the top
decile (d10/d1 = 0.5: decile 1 p̂=0.0213, decile 10 p̂=0.0107). Identical
across all 3 pnodes and the cluster mean — this is partly by construction
(Z is a shared, system-wide covariate, so decile bins are identical
across pnode-analyses by design) and partly a genuine empirical finding
(the specific 5-min intervals where congestion crosses $100 coincide
across all 3 nodes, consistent with a shared, corridor-wide transmission
constraint rather than node-specific events). At $250, exceedances are
near-zero across all deciles for congestion. Does not replicate the
hourly item #9 post-hoc finding of a ~3× exceedance lift (different
calibration — top decile here vs. top 1% there — so not a direct
contradiction, but the pattern doesn't extend cleanly to this
resolution).

**Overall read.** All three pre-registered tests come back weaker at
5-min resolution than their hourly counterparts. Where a direction
exists (Test 2), it's consistent with the hourly Spec A rejection, not
the original proposal's hypothesis. No new confirmatory evidence for a
load-volatility → LMP-tail-risk mechanism at native 5-min granularity in
this 1-year, 3-pnode window.

**Post-hoc notes (not part of the pre-registered verdicts):** QR-full fit
runtimes varied substantially by pnode (21-39 min each at qr_n_boot=500)
— a data characteristic, not a code issue, useful for future 5-min run
time-budgeting.

**Verification note:** before writing this entry, the underlying
computations were independently spot-checked — a manual `QuantReg` refit
reproduced loudoun's primary-spec z_slope exactly, and a manual
decile/exceedance-rate computation on the raw panel reproduced the
Test 3 cluster/congestion numbers exactly. Source code for `qr_full.py`,
`gpd.py`, `tail_risk_curves.py`, and the `run_5min.py` orchestrator wiring
was read and confirmed to match the pre-reg's design (response-column
mapping, bootstrap modes, shape_diff direction).

**Pointers:** `outputs/fivemin/{qr_full,gpd,tail_risk_curves}/`. Panel:
`data/interim/analysis_panel_5min.parquet` (105,019 rows).

**Revisit when:** the advisor meeting (item #5) reframes which
resolution is the headline for the sub-q1 paper.

---

## 2026-07-20 — Sweep output directories relocated under `outputs/sweeps/`

**Context.** The 2026-05-13 entry above ("Application of pre-reg +
diagnosis of threshold non-localizability") references seven
directories at the repo top level: `outputs_n300/`, `outputs_widened/`,
`outputs_widened_12_7am/`, and four `outputs_sweep_*/` variants.
These were cluttering the project root as loose top-level directories.

**Decision.** Moved all seven into `outputs/sweeps/`, dropping the
`outputs_` prefix: `outputs_n300/` → `outputs/sweeps/n300/`,
`outputs_widened/` → `outputs/sweeps/widened/`,
`outputs_widened_12_7am/` → `outputs/sweeps/widened_12_7am/`,
`outputs_sweep_1_5am/` → `outputs/sweeps/sweep_1_5am/`,
`outputs_sweep_2_6am/` → `outputs/sweeps/sweep_2_6am/`,
`outputs_sweep_11pm_6am/` → `outputs/sweeps/sweep_11pm_6am/`,
`outputs_sweep_11pm_7am/` → `outputs/sweeps/sweep_11pm_7am/`.
Contents unchanged, only the location moved. Still covered by the
`outputs_*/` / `outputs/` `.gitignore` rules either way.

**Rationale.** Pure filesystem housekeeping, not a methodology change;
no code or script references the old paths. Per this log's append-only
convention, the 2026-05-13 entry's directory names were left as-is
rather than edited — this entry is the pointer to their current
location.

**Revisit when:** never expected to; noted here only so the 2026-05-13
entry's directory references remain resolvable.

## 2026-07-21 — 2024-07-10 NERC ride-through event verified against a supplemental targeted pull

**Context.** `docs/plans/2026-07-20-jlarc-external-context-update.md`
§4 flagged a NERC-reported incident — 2024-07-10, ~19:05 EPT, a
transmission fault near Fairfax caused ~1,500 MW of data-center load
to trip offline within milliseconds, with a documented price crash at
the Beaumeade substation (external source: gridstatus.io blog,
system-wide energy price ~$134→$56.70/MWh within 5 minutes) — as
"possibly directly checkable" against this project's own data, since
the date falls inside the hourly panel's coverage (2022-10-02 →
2026-05-07) and the geography is the Loudoun cluster this project
already tracks.

Neither production panel can check it directly: the hourly panel
covers the date but averages over 60 minutes, which erases a 5-minute
step change (the afternoon's congestion swings on 2024-07-10 are not
visually distinguishable from the same-magnitude swings on the
unremarkable day before, 2024-07-09 — both are heat-wave/ORDC
dynamics). The production 5-min panel (`analysis_panel_5min.parquet`)
only spans 2025-06-24 → 2026-06-23 and doesn't reach back to mid-2024.

**Finding.** A small supplemental pull was made (same 3 locked
Loudoun-cluster pnodes — LOUDOUN/PLEASANT VIEW/GOOSECRE — one week,
2024-07-07 → 2024-07-14, ~8K rows / 4 requests against the gridstatus.io
Free tier) and written to
`data/interim/analysis_panel_5min_event_week.parquet` (gitignored,
NOT the production panel). Independently re-verified directly against
that parquet (not just the plotting script's docstring claims):

- `dom_load_mw` drops from 21,718.18 (19:00 EPT) to 20,239.56 (19:05
  EPT) — **−1,478.6 MW in 5 minutes**, matching NERC's ~1,500 MW figure
  almost exactly.
- `dom_load_gradient_abs_mw_per_min` = **295.72 MW/min** at that
  interval — the maximum value anywhere in the pulled week, and far
  above the 90th-percentile Z threshold used throughout the hourly
  analysis (13.4 MW/min).
- `system_energy_price_rt_cluster_mean` = **$56.70** at 19:05 EPT,
  down from $136.76 at 19:00 — the endpoint matches gridstatus.io's
  externally-reported system-wide figure ($56.70) to the penny. This
  is expected, not coincidental: system_energy is a zone-wide invariant
  (established in the 2026-05-15 item #2 entry above — identical across
  every pnode in a balancing area), so this project's own pull and the
  external source are measuring the same underlying series.
- `total_lmp_rt_cluster_mean` (this project's Loudoun-cluster mean, a
  different series from the externally-reported Beaumeade-specific
  number) peaks near $186 at 18:55 and falls to a ~$50–70 plateau
  within ~10 minutes — same direction and rough magnitude as the
  external report, not an exact match since it's a different node.

Figure `outputs/figures/00c_event_week_grid_reliability.png` (built by
`scripts/plot_subq1_results.py::fig0c_event_week`) visualizes this.

**A second reported event was checked and NOT located.** The same
JLARC external-context doc also cites a ~1,800 MW Loudoun/Fairfax
event in "2026-02" (no exact date given in the secondary sources).
Scanning the production 5-min panel's full February 2026 window found
no comparable signature — the largest `|Z|` anywhere that month is
~124 MW/min (2026-02-04 02:35), an order of magnitude below the
~360 MW/min a discrete 1,800 MW/5-min step would imply. Either the
event's exact date/time is wrong as reported, it didn't register as a
DOM-zone-wide load step of that scale, or it needs a targeted pull
outside Feb 2026 — not pursued further; flag as unconfirmed rather
than force a match.

**Rationale for logging this now.** This is a real, priced,
geographically-in-scope event that lands inside the project's own
panel window and pnode set — a much stronger anchor than the decile-
level tail-risk null (item #6) for the "crazy LMP" framing, and
directly relevant to the advisor-meeting agenda's Item 5 (filter-scope
limitation) and to sub-q3's eventual "real-world incident correlation"
framing once it unlocks. Recording it here rather than leaving it as
an undocumented script diff, per this log's standing convention.

**Revisit when:** the advisor meeting decides whether this event
belongs in the sub-q1 paper as a supporting illustration (Item 5) or
is better saved for sub-q3; or if the second (Feb 2026) event's exact
timestamp is later pinned down and can be similarly pulled.

## 2026-07-21 — Second NERC event's date corrected: February 2025, not February 2026

**Context.** The entry immediately above (this same date) scanned the
production 5-min panel's full February 2026 window for a ~1,800 MW
Loudoun/Fairfax load-loss event cited in
`docs/plans/2026-07-20-jlarc-external-context-update.md` §4, found
nothing, and logged it as "unconfirmed." Continuing that thread as
ungated sub-q2 background research, the date itself was re-checked
against additional sources.

**Finding.** The "2026-02" date in the external-context doc was wrong.
Provenance, stated honestly: only one source was both directly read
and explicit about the date — DediRock (a secondary hosting-provider
blog) states "February 2025." Utility Dive's article was also directly
read but does *not* state a specific date (only "incidents... in 2024
and 2025"); techtimes.com 403'd to fetch and was never actually read,
despite appearing in search summaries; RTO Insider was seen only via a
WebSearch result summary, not a direct fetch. So this is not "four
sources confirm" — it's one direct-read confirmation plus a stronger
**constraint argument**: multiple outlets independently describe this
as the *second* such Northern Virginia data-center load-loss incident,
occurring less than a year after 2024-07-10. February 2026 would be 19
months later, violating that constraint; February 2025 (7 months
later) satisfies it. A government PDF that might have offered primary
confirmation (`ferc.gov/.../2025-04/...Large Load
Integration_1.pdf`) was fetched but returned unreadable binary
content, not usable text.

Treat **February 2025** as well-supported, not primary-source-
confirmed. This means the prior entry's February 2026 scan was
checking the wrong month entirely; its "no comparable signature"
conclusion doesn't bear on whether the real event happened, just that
it didn't happen when we thought it did.

February 2025 falls inside this project's **hourly panel**'s coverage
(2022-10-02 → 2026-05-07), so it was checked directly:
`data/interim/analysis_panel.parquet` filtered to 2025-02-01 →
2025-02-28 shows no hour with an anomalous load or price signature
that month — max `dom_load_gradient_abs_mw_per_min` is ~26.3 (2025-02-24
09:00 EPT), an order of magnitude below the 295.7 MW/min seen for the
verified 2024-07-10 event, and no single-hour system-energy-price step
exceeds -$262 (2025-02-05 11:00, not obviously event-shaped). This is
consistent with, not contrary to, the finding already logged for
2024-07-10: hourly averaging erases a discrete 5-minute step of this
kind (the July 2024 event was invisible in the hourly panel too — see
the entry above, "Neither production panel can check it directly").
February 2025 also falls outside the 5-min panel's coverage
(2025-06-24 → 2026-06-23), so no direct 5-min check is possible with
data already on hand.

**Exact day within February 2025 not found.** Six-plus secondary
sources were checked (Utility Dive, DediRock, RTO Insider, techtimes,
American Public Power Association, EnerKnol, gridstatus.io's own
blog); none give a day-level date. NERC's primary PDFs return 403 to
automated fetch, same limitation already noted for the 2024-07-10
research pass.

**Rationale for logging this now.** A wrong date sitting uncorrected
in the external-context doc would misdirect anyone (including the
advisor) trying to cross-check it against this project's data, and
already caused one wasted scan (the entry above). Correcting it here,
with a strikethrough-and-correction inline in the source doc too, so
neither copy is silently wrong going forward.

**Not pursued:** a wide-window supplemental 5-min pull across all of
February 2025 to localize the exact day/hour, the same technique used
for 2024-07-10. That earlier pull was one week (~8K rows / 4 requests)
because the date was already known; a full-month blind scan would cost
substantially more of the gridstatus.io Free-tier monthly quota (500K
rows / 250 requests) for a date this project doesn't currently need
pinned to the hour — the month-level correction is enough to keep the
external-context doc accurate. Worth reconsidering if the advisor
meeting decides this second event should anchor a paper illustration
alongside 2024-07-10 (Item 5).

**Revisit when:** a primary NERC source surfaces with the exact date,
or the advisor meeting decides this event needs day-level pinning for
the paper.

## 2026-07-21 — Sub-q3 event-catalog scan: `sync_reserve_event_active` discovered as an existing ground-truth signal

**Context.** With sub-q1 closed pending only the advisor meeting, and
sub-q2 plan-writing gated on that meeting, the user asked to start
ungated reconnaissance for sub-q3 ("are crazy LMP events tied to
real-world incidents?") — confirmed via AskUserQuestion as background
scanning only, not sub-q3 methodology/plan-writing. Full writeup:
`docs/plans/2026-07-21-subq3-event-catalog-scan.md`.

**Finding.** `data/interim/analysis_panel.parquet` already contains
`sync_reserve_event_active` / `sync_reserve_event_id` — PJM's own
record of synchronized-reserve deployment events, 37 unique events
(39 event-hours) spanning 2023-01-26 to 2026-03-05. This is a
distinct signal from the verified 2024-07-10 NERC ride-through event
(demand-side voltage disturbance): the 2024-07-10 event does not
appear in this flag at all, confirming the two are different event
mechanisms (generation-shortfall reserve deployment vs. data-center
voltage ride-through). Cross-tabbed against the proposal filter
(shoulder season × 2-5am window): only 2 of 39 event-hours pass both
conditions, and neither shows an elevated price/gradient signature —
consistent with item #6's finding that the filter's scope excludes
price extremes even when a real PJM event coincides with it.

A naive top-N-by-`dom_load_gradient_abs_mw_per_min` scan (excluding
known event dates) mostly just re-finds the 09:00 EPT daily load ramp
across many dates — a diurnal artifact, not real anomalies. Ranking
by congestion price instead surfaced two new, externally-corroborated
candidate events: **2022-12-23 ~17:00 EPT (Winter Storm Elliott** —
total_lmp cluster mean ≈$4,130, matches PJM's own after-action report
of ~46,000 MW forced outages and prices exceeding the $3,700/MWh cap)
and **2026-01-31 evening → 2026-02-01 early morning** (multi-hour
congestion spike, several hours flagged `sync_reserve_event_active`,
matching a PJM-confirmed extreme-cold event where PJM obtained a DOE
§202(c) order authorizing it to direct data centers specifically onto
backup generation — see the plan doc for full sourcing and provenance
caveats on each claim).

**Rationale for logging now.** The `sync_reserve_event_active` column
is a real analytical resource for sub-q3 that nobody had used before
this scan, and its near-total non-overlap with the current proposal
filter (2/39 event-hours) is a load-bearing fact for whatever
correlation window sub-q3 eventually adopts — worth having on record
before that design conversation happens, not rediscovered from
scratch.

**Extended same session, per explicit user instruction** ("go through
all of them extensively and autonomously, dont worry about
time/quota"). Widened from an hour-level top-15 scan to a day-level
top-30 scan (avoids one multi-hour event crowding out separate events
in an hourly ranking) and searched every resulting candidate date
against external reporting. Five more events confirmed, bringing the
total to seven distinct corroborated events/clusters:

- **2022-12-24** — Winter Storm Elliott's second day (total_lmp
  ≈$4,125, nearly matching 12-23); the hour-level scan had missed it.
- **2025-01-22/23** — PJM's all-time hourly winter demand record
  (~143,714 MW), capping an Arctic Outbreak that began Jan 18, 2025.
- **2024-01-20** — a second, distinct January 2024 PJM Cold Weather
  Alert (Jan 20-22), separate from an earlier Jan 14-17 polar-vortex
  alert.
- **2024-05-26** — a documented severe-weather/tornado outbreak
  (60 wind-damage reports region-wide, EF1 tornado in Salem, VA;
  Wikipedia: "Tornado outbreak of May 25-27, 2024"). The only
  confirmed event where the panel signature is price-driven without
  an elevated load gradient.
- **2026-01-24 → 02-09** — the Jan 2025 event's twin: the broader
  "January-February 2026 North American cold wave" (Jan 17-Feb 11,
  Wikipedia, directly fetched), confirming the already-logged
  01-31/02-01 DOE-order spike was the peak of a 3-week elevated-
  congestion regime, not an isolated event. A storm name ("Winter
  Storm Fern") surfaced in two independent sources but not the
  Wikipedia article itself — treated as probable, not certain.

**Also confirmed rigorously (not just asserted):** the earlier "naive
gradient-ranking mostly finds the diurnal ramp" observation — 31/50
panel-wide top-gradient rows fall at hour 09:00 EPT, with hour-9
gradient systematically elevated (mean 8.59 vs. 6.40 MW/min panel-
wide).

**Equally important negative result.** Eight more candidate dates/
clusters (2025-05-01→03 — the single largest unexplained congestion
value in the panel outside confirmed events at $1,020; three more May
2024 dates besides the confirmed 05-26; 2023-10-26; 2023-11-29;
2025-04-14; 2025-11-18; 2025-12-15; 2026-04-04/15/16) were searched
with equal effort (general event search, NOAA storm-events-database
search by name, PJM transmission-outage and Market Monitor search,
Dominion-specific news) and came back with **no** external
corroboration. The closest finding was structural, not incident-
specific: PJM's own 2025 Market Monitor report places Dominion zone's
real-time congestion component highest of any PJM zone for the first
three quarters of 2025. Read together with the confirmed-event list,
this splits the panel's congestion spikes into two populations: a
minority traceable to documented external incidents, and a majority
consistent with routine (if elevated) congestion in a structurally
constrained zone rather than discrete newsworthy events. Roughly
40-45% of the ~17 investigated candidates confirmed — a sub-q3
methodology should expect this hit rate, not treat the unconfirmed
majority as a search failure.

**Revisit when:** sub-q3 plan-writing unlocks and the correlation-
window / event-category-scope decision (ride-through vs. sync-reserve,
filter-scoped vs. full-panel, how to treat the "no external cause
found" majority) needs to be made formally.

## 2026-07-21 — Sub-q1 item #6 follow-up path (a): calibrated-threshold tail-risk recompute (exploratory)

**Context.** Item #6's original run (`docs/decisions.md`, 2026-05-15
entry) tested exceedance thresholds $100-$2000, all above the
proposal-filter's actual data range (99.5th-pct total_lmp ≈ $100),
producing an all-zero curve — a methodological finding about filter
scope, not the descriptive Z→LMP curve the design intended. The
roadmap (`docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`,
item #6) flagged two follow-up paths for advisor input: (a) recompute
at calibrated smaller thresholds, (b) raw-panel analysis via sub-q3.
Path (b) was pursued today as ungated sub-q3 reconnaissance (entry
above); on reflection (advisor-tool consult), path (a) is the same
kind of ungated reconnaissance — a mechanical rerun of an existing,
already-DONE module with different threshold inputs, not new sub-q1
methodology. Run via a one-off script calling
`run_tail_risk_curves()` directly (no CLI flag exists for custom
thresholds) with `thresholds=[25, 50, 75, 100, 150]`, `n_boot=200`,
same panel/filter/seed as the original. Output written to
`outputs/tail_risk_curves_calibrated/` (gitignored), kept separate
from the original item #6 outputs.

**Finding.** Real (non-degenerate) curves this time. For the primary
pnode's total_lmp response at **$50**: P(exceed | Z decile) rises
through the top deciles — decile 8: 8.9%, decile 9: 9.9%, decile 10:
15.3% (CI [10.3%, 19.7%], n_exc=31/203) — and decile 10's CI does not
overlap deciles 1/3/4/6/7 (upper bounds 0.064-0.094). At **$75 and
$100**, the pattern does not hold: decile 10 drops to 0.025 (@ $75)
and 0.0 (@ $100), while several middle deciles (5, 8, 9) retain small
positive exceedance probabilities at $100 that decile 10 does not.
Congestion's curve is far sparser (only visible at $25, p_hat ≤ 0.03
everywhere, ~6 exceedances per decile) and doesn't show a clean
decile-10 pattern at all. Full per-decile tables with CIs for all 7
pnodes are in `outputs/tail_risk_curves_calibrated/tail_risk_curves/`.

**Rationale for treating this as exploratory, not a result.** No
pre-registration, no multiple-testing correction across the 5
thresholds × 2 response variables × 7 pnodes, small per-decile n
(~200), and the pattern doesn't replicate across adjacent thresholds
($50 vs $75/$100) — textbook conditions for a post-hoc finding that
wouldn't survive a stricter test. It does NOT confirm the proposal's
"heavier tail at high Z" hypothesis (that question was already
formally tested and rejected by Spec A/B on congestion); it's a
different, complementary descriptive object — the actual shape of
$-exceedance-probability-by-decile that item #6 was designed to
produce and the original thresholds prevented. Not used to revise any
existing framing.

**Not decided here:** whether this curve becomes paper content, gets
re-run pre-registered with a chosen headline threshold, or is
superseded by the advisor's input on item #6's original (a) vs (b)
choice. Producing the curve is reconnaissance; using it is the
advisor's call, per the same line already applied to sub-q2's
napkin-math and today's sub-q3 scan.

**Revisit when:** the advisor meeting (item #5) addresses item #6's
follow-up-path question directly.

---

## 2026-05-15 (late) — Sub-q1 item #8: 5-min companion run (application)

**Context.** Pre-registration locked the methodology in 2026-05-15
§ Item #8. Production run executed autonomously per
`docs/plans/2026-05-15-5min-companion-implementation.md` via the
`/run-5min-companion` slash command. Sibling worktree
`../surg-5min-companion/` on `feature/sub-q1-item-8-5min-companion`.

**Joint window achieved (Part A).** 2026-04-13 20:00 → 2026-05-10
23:55 EPT (27.2 days). 6,855 5-min stamps total; 845 in
proposal-filter window (shoulder × 2-5 AM). The `inst_load` 30-day
retention wall capped the upper edge as expected. 5-min LMP delta
pull through 2026-05-14 succeeded but added no joint-window days
(bottlenecked by `inst_load` end at 2026-05-10). `inst_load`
refresh skipped — `surg-pull` CLI does not support the `inst_load`
feed; existing 27-day archive used.

**Part A findings (per pre-reg expectation: underpowered).** All
five modules ran end-to-end with `--bootstrap-method=cluster`.
Cluster count K is data-contiguity-dependent (>10-min gaps =
boundaries) and was small for full-panel modules — pre-registered
as below the 50-cluster floor.

- **Item #1 — Spec B (continuous ξ(Z) regression), congestion @
  cluster_mean, p95 threshold (headline):** β₁ = +0.024,
  bootstrap 95% CI [−0.013, +0.073], p = 0.16 → **`underpowered`
  decision-rule outcome**, matching pre-reg. Direction (positive
  β₁) consistent across the threshold sweep at p90/p95/p99 (point
  estimates +0.011/+0.024/+0.040, all CIs span 0); p99.5 fit failed
  (insufficient exceedances — n = 35).
- **Item #2 — gpd_components decomposition:** **`insufficient_sample`**
  outcome on the headline (system_energy @ p95 on primary cluster):
  n_exc = 43, below the n ≥ 50 per-half floor needed for the
  median-split test. Pre-registered as expected at this n.
- **Item #3 — year_fe_diagnostic (τ-trend secular component):**
  **`skip_reason: only 1 distinct year (2026)`**. The 27-day
  single-month joint window cannot support year-FE estimation by
  construction. Pre-registered as the single-month-window failure
  mode; documents the data wall in the most explicit way available.
- **Item #4 — ashburn_diagnostic (LOO scatter):** LOO finished
  (deterministic — no bootstrap dependency). Cross-threshold
  summary CI columns are all `null` because Spec B fits at p95
  failed for the Ashburn pnodes on this thin window — the LOO
  beta_1 sweep itself is reported (q=0.9: −0.019, q=0.99: +0.066,
  q=0.995: +0.159 for tx1) but is not a statistical claim at this
  sample size.
- **Item #6 — tail_risk_curves (direct Z → LMP):** computed P(LMP
  > $X | Z decile) tables for 5 thresholds × 10 deciles × 7 pnodes.
  Top-Z-decile (z ∈ [19, 79] MW/min, n = 85): P(congestion > $100)
  = 0.000 (CI [0, 0.043]); P(total_lmp > $100) = 0.012 (1 of 85,
  CI [0, 0.042]); $250+ thresholds all return p_hat = 0. The
  hourly item #6 finding ("filter excludes the very events the
  'crazy LMP' framing targets") replicates at 5-min cadence on the
  shorter window.

**Cross-resolution summary.** Like-for-like comparator built on the
24.1-day overlap window (2026-04-13 → 2026-05-07, bounded by the
on-disk hourly panel's end). Hourly comparator: 580 rows, n_filtered
= 72 (8 obs/decile, very thin). 4 pnodes × 100 (decile×threshold)
cells = 400 comparison rows in
`outputs_5min/cross_resolution_summary.{json,csv}`. The matched
hourly comparator is itself underpowered at this window length,
limiting the inferential weight of any 5-min vs hourly delta.

**Part B findings (descriptive, 6-month LMP-only,
spike-exceedance).** Joined 5-min nodal LMP (2025-11-12 →
2026-05-14, 582,780 rows × 11 pnodes) with hourly published total
LMP on (pnode, hour_floor). Headline pnode = PLEASANT VIEW
(35010371, primary anchor, 50,964 5-min rows × 4,247 matched
hours):

| Threshold | Pct (5-min) | n 5-min exc | n hourly buckets w/ 5-min exc | n hidden | hidden_fraction |
|---|---|---|---|---|---|
| $50 | 66.07 | 17,293 | 2,448 | 839 | **0.343** |
| $100 | 84.40 | 7,950 | 1,329 | 604 | **0.454** |
| $250 | 92.28 | 3,932 | 739 | 428 | **0.579** |
| $500 | 96.98 | 1,539 | 279 | 162 | **0.581** |
| $1000 | 99.19 | 413 | 81 | 48 | **0.593** |

Hourly aggregation hides ~34–60 % of hour-buckets with 5-min spikes
across the threshold range. The hidden fraction grows
monotonically with threshold: rarer events are MORE likely to be
hidden, because a single 5-min spike is averaged with 11 normal
prices and the published hourly value does not exceed the
threshold. Cross-pnode CSV at
`outputs_5min/lmp_descriptive_6mo/spike_exceedance_comparison/cross_pnode_summary.csv`.

**Limitations.**
1. **Data-retention wall.** `inst_load` ~30-day retention caps Part
   A at one month — pre-reg expected this; documented in concrete
   numbers (27.2 days, 6,855 stamps, 845 in-filter).
2. **Sub-50 cluster floor** for Part A's cluster bootstrap. K was
   well below 50 (precise count not measured but small given panel
   contiguity); CI widths reported are noisier than face value.
3. **Single-month window** breaks year-FE estimation entirely (item
   #3 skip_reason).
4. **Part B is descriptive only** — no inferential CIs (design
   § 3.4); the hidden-fraction headline is a count-based ratio with
   no uncertainty interval.
5. **Cross-resolution comparator window** (24.1 days, 72 in-filter
   rows) is itself thin. Useful as a like-for-like sanity check,
   not as an authoritative resolution-effect estimate.
6. **`inst_load` refresh skipped** because `surg-pull` CLI lacks
   the `inst_load` feed (it was originally pulled via a one-off
   script). Existing 27-day archive met the planned window
   (mid-Apr → mid-May); the missed 5-day refresh would have shifted
   the upper bound to 2026-05-15 but only Part A's joint window
   is bottlenecked by `inst_load`, so this is non-load-bearing.

**Headline interpretation.**
- Part A confirms what pre-reg expected: a 27-day joint window
  cannot deliver any statistical claim about Z → LMP tail risk; it
  documents the data wall.
- Part B delivers an **independently useful descriptive finding
  about resolution loss**: PJM's hourly publication hides 34 % of
  the time the price spiked above $50 and 59 % of the time it
  spiked above $1000, at the primary anchor pnode. This belongs in
  the SURG report as a 5-min-cadence value-add even when the
  upstream Z → LMP tail-risk question is unanswerable from the
  monthly 5-min joint panel.

**Revisit when.** Same conditions as the pre-reg: a longer-history
5-min DOM-load source surfaces (different PJM feed, advisor's
private dataset, EIA), or advisor reframes which resolution is the
headline.
---

## 2026-05-15 (late) — Sub-q1 item #9: Full-panel direct Z → LMP characterization (pre-reg)

**Context.** Sub-q1 item #6 (direct Z → LMP tail-risk) finding within
the proposal-filter scope (shoulder × 2-5 AM) was: P(LMP > $250 |
top Z decile) = 0.000 across all 10 deciles × 7 pnodes; only 10 of
2027 in-filter observations even exceed $100. The natural critique
of this result is that the filter excludes by construction the
periods (summer afternoons, peak hours) where DOM-zone "crazy LMP"
events actually occur. To resolve this critique before the advisor
meeting (item #5), this entry pre-registers a single full-panel
re-run of item #6 with the proposal-filter lifted.

This is added as **sub-q1 closure item #9** (item #7 was renumbered;
item #8 is the 5-min companion shipped earlier today). Decision to
add pre-meeting per user direction tonight.

**Decision rule (pre-registered before any code runs).** Three
mutually-exclusive verdicts on whether item #6's null was driven by
the proposal-filter or is structural:

- **Verdict A — "filter-driven":** Full-panel
  `P(total_lmp_rt > $250 | top Z decile) > 0.05` on **≥4 of 7
  pnodes**. The filter was the binding constraint; lifting it
  reveals high-Z → crazy-LMP at material rates. Item #6's in-filter
  null is a scope artifact, not a substantive answer. Major
  reframing implication: sub-q1's negative answer becomes scope-
  limited; the descriptive question has a positive answer outside
  the filter.

- **Verdict B — "structural":** Full-panel
  `P(total_lmp_rt > $250 | top Z decile) ≤ 0.01` on **≥4 of 7
  pnodes** AND the monotonic-increase check below also fails. Even
  on the full panel, top-Z deciles do not produce crazy LMP at
  material rates. Item #6's in-filter null hardens into a real
  finding. The proposal's hypothesis is wrong on the merits, not on
  the scope.

- **Verdict C — "partial / mixed":** Anything between A and B.
  Examples: only 1-3 pnodes show full-panel exceedance >0.05;
  monotonic increase emerges on the full panel but at moderate
  thresholds ($100 not $250); cross-pnode pattern is heterogeneous.
  Headline framing depends on which subset of pnodes shows the
  effect — to be decided in the advisor meeting.

**Secondary diagnostic (descriptive, not gating verdict A/B/C):**
For each pnode, on the full panel, check whether
`P(total_lmp_rt > $100 | Z decile)` increases monotonically from
decile 1 → decile 10. Monotonicity on **≥4 of 7 pnodes** indicates
a smooth Z → tail relationship exists outside the filter scope, even
if the $250+ exceedance criterion fails. This sharpens verdict B vs
C interpretation but does not change the verdict assignment itself.

**Scope.**
- Panel: `data/interim/analysis_panel.parquet` (3.6y post-cap
  hourly, ~31k rows).
- Module: `surg.analysis.tail_risk_curves.run_tail_risk_curves`
  with new `filter_col=None` mode (filter step skipped).
- Pnodes: all 7 in `CROSS_PNODE_PNODES` (primary cluster, total_lmp,
  ox, bristers, dom_zonal, ashburn_tx1, ashburn_tx2).
- Thresholds: default `[100, 250, 500, 1000, 2000]`.
- Bootstrap: `bootstrap_method=pair`, `n_boot=200`, `seed=42`.
- Headline response: `total_lmp_rt` (the proposal's "crazy LMP"
  variable) at the $250 threshold. Decision rule uses total_lmp_rt
  exclusively because the proposal's framing was about absolute
  pricing, not the congestion component.

**Why total_lmp_rt $250 specifically (cross-checked with PJM data):**
$250 is roughly the 99th percentile of total_lmp_rt across the full
DOM-zone hourly panel and corresponds informally to the "crazy LMP"
threshold in PJM operator parlance (well above the typical $30-50
nominal range, close to the ORDC reserve-shortage trigger). Lower
thresholds ($100) capture moderately elevated prices that are not
"crazy" by the proposal's framing.

**Why 0.05 specifically:** A 5% top-decile exceedance rate at $250
would correspond to roughly 1 hour per 20 high-Z hours. At the panel
scale (~3,000 top-decile observations on the unfiltered full
panel), 0.05 = ~150 events — large enough to support follow-up
characterization (sub-q3 territory). Below 0.05, the events are too
rare to ground a positive answer.

**Implementation.**
- New worktree: `../surg-item-6-no-filter/` on branch
  `feature/sub-q1-item-6-no-filter`.
- Modify `run_tail_risk_curves` to accept `filter_col: str | None
  = "passes_proposal_filter"`. When `None`, skip the filter step
  and use the full panel.
- Add CLI flag `--no-filter` to `surg-analyze`.
- Test: assert behavior when filter_col=None matches a manually
  unfiltered call.
- Run on the full panel; write outputs to `outputs_no_filter/`.

**Rationale for pre-registering.** Even though this is a single
descriptive run with no inferential claim, pre-registering the
verdict mapping prevents post-hoc "the data really shows X"
rationalization when the result is mixed. The advisor meeting
benefits from a mechanical verdict assignment we can't talk
ourselves out of.

**No FF-merge, no push policy continues** for this closure item per
the same conventions as items #1-#8.

**Revisit when.** Verdict applied in the application entry
following this run. If verdict C (mixed), the advisor meeting locks
the sub-q1 narrative; if verdict A or B, the pre-reg forces a
specific paper headline before the meeting.

---

## 2026-05-15 (late) — Sub-q1 item #9: Full-panel direct Z → LMP characterization (application)

**Context.** Pre-reg at this date § Item #9 (above) locked the
verdict mapping before any code ran. This entry mechanically applies
that decision rule to the full-panel `run_tail_risk_curves` output
(filter lifted, n_boot=200, seed=42, all 7 pnodes).

**Run details.**
- Panel: `data/interim/analysis_panel.parquet` (rebuilt with schema
  v2 metadata; 31,536 hourly rows, 2022-10-02 → 2026-05-07).
- In-filter rows (for comparison context): 2,027.
- Full-panel n_total per pnode: 31,540 (cluster pnodes), 17,448
  (Ashburn pnodes; fewer because the Ashburn columns have NA on
  pre-availability dates).
- Top-Z-decile range: z ∈ [13.38, 36.39] MW/min.
- Wall: ~30 s.

### Decision rule application

Headline: P(`total_lmp_rt` > $250 | top Z decile), per the pre-reg.

| Pnode | n_top_decile | P(total_lmp > $250) | CI 95% |
|---|---:|---:|---:|
| primary | 3,154 | 0.0190 | [0.0146, 0.0247] |
| total_lmp | 3,154 | 0.0190 | [0.0146, 0.0247] |
| ox | 3,154 | 0.0200 | [0.0152, 0.0251] |
| bristers | 3,154 | 0.0190 | [0.0146, 0.0244] |
| dom_zonal | 3,154 | 0.0206 | [0.0158, 0.0260] |
| ashburn_tx1 | 1,745 | **0.0470** | [0.0384, 0.0562] |
| ashburn_tx2 | 1,745 | **0.0395** | [0.0309, 0.0481] |

- **Pnodes with P > 0.05:** 0/7. *Verdict A threshold (≥4) NOT met.*
- **Pnodes with P ≤ 0.01:** 0/7. *Verdict B threshold (≥4) NOT met.*
- **Pnodes between 0.01 and 0.05:** 7/7.

**Verdict: C — partial / mixed**, by the literal pre-reg rule.

### Secondary diagnostic — STRONG structural twist

The pre-reg's secondary check was: "monotonic increase of P(total_lmp
> $100) across deciles 1 → 10 on ≥4 of 7 pnodes indicates a smooth Z →
tail relationship exists outside the filter scope." Result:

| Pnode | d1 | d2 | d3 | d4 | d5 | d6 | d7 | d8 | d9 | d10 | Monotonic? |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| primary | 0.061 | 0.056 | 0.059 | 0.062 | 0.054 | 0.054 | 0.053 | 0.063 | 0.061 | **0.078** | No |
| dom_zonal | 0.081 | 0.078 | 0.080 | 0.081 | 0.073 | 0.068 | 0.069 | 0.081 | 0.084 | **0.091** | No |
| ashburn_tx1 | 0.111 | 0.111 | 0.105 | 0.107 | 0.111 | 0.094 | 0.104 | 0.123 | 0.120 | **0.139** | No |
| ashburn_tx2 | 0.105 | 0.108 | 0.098 | 0.103 | 0.101 | 0.086 | 0.093 | 0.112 | 0.104 | **0.127** | No |

**Monotonicity fails on 4/4 plotted pnodes.** P(LMP > $100) is
essentially flat across Z deciles, with only a small bump at the
highest decile (~25-28% relative increase d1 → d10, well within the
descriptive noise of the lower deciles).

For congestion (the proposal's specific mechanism variable),
Z-decile binning provides essentially zero discrimination:

| Pnode | d1 | d10 | d10/d1 ratio |
|---|---:|---:|---:|
| primary | 0.010 | 0.013 | 1.3× |
| dom_zonal | 0.022 | 0.016 | 0.7× (DECREASES) |
| ashburn_tx1 | 0.038 | 0.048 | 1.3× |
| ashburn_tx2 | 0.029 | 0.037 | 1.3× |

**Congestion-exceedance rates are flat or non-monotonic across Z deciles.**

### Headline interpretation — verdict C with structural-leaning content

Verdict C by the literal pre-reg rule, but the secondary diagnostic
provides a **strong structural-leaning interpretation** that needs to
be on the table for the advisor meeting:

1. **Lifting the filter does NOT reveal a Z → LMP relationship.** The
   in-filter null was not a filter artifact; the relationship is
   weak-to-absent at the decile level on the full panel as well.

2. **Crazy LMP events occur at a low-but-nonzero rate at EVERY Z decile.**
   1.9–4.7% top-decile $250+ exceedance is not zero, but it's not
   uniquely concentrated in high-Z bins either. The events appear
   roughly Z-uniform across the support.

3. **At the decile level, the proposal's "phase transition" framing
   finds no support.** No decile (low or high) where LMP behavior
   qualitatively shifts in the decile aggregates. The smooth-curve
   diagnosis from 2026-05-13 is reinforced by the full-panel
   per-decile evidence. **See post-hoc exploration below for the
   extreme-tail (top 1% of Z) caveat that decile binning is too
   coarse to detect.**

4. **Ashburn pnodes show consistent ~2× elevation across all deciles.**
   This is a pnode-level effect, not a Z-driven effect. Independent
   of the Z question; consistent with item #4's TX1 anomaly findings.

### Implication for sub-q1's overall verdict

The mechanism-test mixed answer (positive QR-full moderate-τ,
negative Spec A median-split) now has an additional **descriptive
finding at the decile level**: Z provides little discrimination for
predicting crazy LMP across deciles 1-10 on the full panel. This
**does not contradict** the positive QR-full moderate-τ slope (which
operates on conditional quantiles, not decile exceedance rates), but
it does **constrain the paper's framing**: any decile-aggregate "Z
drives LMP" claim has to be carefully qualified as a *moderate-
quantile slope* phenomenon, not a *crazy-event-rate* phenomenon at
the decile level. **The post-hoc top-1% exploration below identifies
a real concentration at the extreme Z tail that the decile binning
is too coarse to detect — see that subsection for the refined
picture.**

The pre-reg's purpose was to prevent post-hoc "the data really shows
X" rationalization on a likely-mixed result. Mechanical Verdict C
applies; the secondary diagnostic is mechanically reported. The
choice of how to weight verdict C vs the secondary structural-leaning
interpretation in the paper headline is now explicitly an advisor-
meeting decision.

### Four options for the advisor meeting (item #5)

1. **Anchor on Spec A median-split rejection** ("ORDC mechanism on
   congestion is rejected at α=0.05"). Item #9's result becomes a
   descriptive companion: "The decile-level rejection holds on the
   full panel too — top-Z decile only marginally elevates exceedance
   rates over low-Z decile, well within the small range of overall
   variation."

2. **Anchor on QR-full moderate-τ positive finding** ("higher Z drives
   higher conditional 95th-pct LMP"). Item #9's result becomes a
   limit: "The Z → LMP slope at moderate quantiles does not extend
   to a decile-level concentration of crazy events; the effect is in
   the conditional distribution shape, not in the decile-aggregate
   exceedance rate."

3. **Anchor on the unified decile-level finding** ("Z provides little
   discrimination for crazy LMP events at the decile level — the
   proposal's threshold framing is wrong, the mechanism evidence is
   mixed, the decile-aggregate evidence on the full panel finds Z
   roughly uniform for high-LMP events"). Treats most sub-q1 work as
   triangulation pointing toward "the proposal's framing was the
   wrong question." Acknowledges the post-hoc top-1% caveat as a
   methodological footnote.

4. **Anchor on the extreme-tail concentration** (post-hoc):
   "Z drives crazy LMP only at the extreme tail (top 1% of Z, n=316
   on the full hourly panel), with the effect concentrated in the
   system_energy component (ORDC mechanism). The proposal's
   threshold framing was directionally right about *where* the
   effect lives but wrong about the *smoothness/sharpness* of the
   transition — there is no kink, only a heavy-tail concentration
   visible at percentile-99+ resolution that decile binning is too
   coarse to detect." Reconciles the proposal with the data; cost
   is post-hoc analysis with n=316 (modest CIs) and n=32 at top
   0.1% (uselessly wide CIs).

### Sub-q1 closure status (revised after item #9)

| Item | Status |
|---|---|
| #1 Spec B continuous ξ(Z) | DONE |
| #2 LMP-components decomposition | DONE |
| #3 year_fe_diagnostic | DONE |
| #4 Ashburn TX1 anomaly | DONE |
| #5 Advisor meeting | **PENDING (now ready with full evidence)** |
| #6 Direct Z → LMP tail-risk (in-filter) | DONE |
| #8 5-min companion (Part A + Part B) | DONE |
| #9 Full-panel direct Z → LMP (filter lifted) | **DONE — this entry** |

**Only item #5 remains.** All analysis paths sub-q1 was designed to
support are exhausted. The advisor meeting is now positioned to make
narrative + framing decisions with the complete evidentiary picture
available.

### Revisit when

- Advisor meeting locks the headline framing (item #5).
- A NEW data source (private dataset, EIA load curves, etc.)
  enables a different scope test that addresses Z → LMP at sub-decile
  granularity. Currently no path within the SURG dataset.

### Post-hoc exploration — extreme-tail Z (NOT pre-registered)

Triggered by a sanity-check audit of this entry's pre-reg verdict.
The pre-registered decile-level rule averages z ∈ [13.38, 36.39] in
the top-decile bin (n=3,154 for cluster, n=1,745 for Ashburn) — wide
enough that an extreme-tail concentration could be diluted away.
**This subsection is post-hoc and exploratory; the pre-reg verdict C
above stands unchanged.** The findings here are reported for the
advisor meeting's framing decision, not used to revise the verdict.

**Method.** Recompute `P(LMP > $X | Z > pct)` for percentiles 50, 75,
90, 95, 99, 99.5, 99.9 using the same full hourly panel. No
bootstrap; raw counts. CIs in this section are normal-approximation
or Wilson — sufficient for descriptive characterization, not
inferential claims.

**Results — `total_lmp_rt_cluster_mean` (cluster pnode, n=31,536):**

| pct | Z cutoff | n above | P>$100 | P>$250 | P>$500 | P>$1000 |
|---:|---:|---:|---:|---:|---:|---:|
| 50.0 | 5.47 | 15,768 | 0.062 | 0.015 | 0.005 | 0.001 |
| 90.0 | 13.38 | 3,154 | 0.078 | 0.019 | 0.007 | 0.002 |
| 95.0 | 15.95 | 1,577 | 0.098 | 0.024 | 0.009 | 0.003 |
| **99.0** | **19.87** | **316** | **0.146** | **0.044** | **0.019** | **0.010** |
| 99.5 | 21.04 | 158 | 0.196 | 0.051 | 0.019 | 0.013 |
| 99.9 | 24.29 | 32 | 0.156 | 0.094 | 0.063 | 0.063 |
| **(unconditional)** | — | 31,536 | **0.060** | **0.015** | **0.005** | **0.002** |

**Lift at top 1% Z vs unconditional baseline:**
- P > $100: 0.146 / 0.060 = **2.4×**
- P > $250: 0.044 / 0.015 = **2.9×** (Wilson 95% CI ≈ [0.027, 0.072], lower bound excludes the 0.015 unconditional)
- P > $500: 0.019 / 0.005 = **3.8×**
- P > $1000: 0.010 / 0.002 = **5.9×**

**Lift at top 0.1% Z (n=32, very wide CIs):**
- P > $1000: 0.063 / 0.002 = **37×** — n=32 means just 2 events; not statistically reliable

**Results — congestion** (proposal's mechanism variable, cluster):

| pct | Z cutoff | n | P>$50 | P>$100 | P>$250 |
|---:|---:|---:|---:|---:|---:|
| 50 | 5.47 | 15,768 | 0.025 | 0.012 | 0.003 |
| 99 | 19.87 | 316 | 0.063 | 0.029 | 0.013 |
| 99.5 | 21.04 | 158 | 0.076 | 0.032 | 0.006 |
| **(unconditional)** | — | 31,536 | **0.025** | **0.012** | **0.004** |

Congestion top-1% lift: ~2.3-3× (smaller than total_lmp's, consistent
with the LMP-components decomposition's `total_lmp ≈ 4× congestion`
finding). The lift at top 0.5% for $250 (0.006 vs 0.004 unconditional)
is small enough to be within sampling noise at n=158.

### Refined honest interpretation

Combining the pre-registered verdict C with the post-hoc top-1%
finding:

1. **At the decile level (pre-registered):** Z provides little
   discrimination for crazy LMP. The "filter excludes the events"
   critique is dead. The proposal's *smooth-curve* hypothesis is
   reinforced.

2. **At the extreme-tail level (post-hoc):** Z DOES concentrate crazy
   LMP at top 1% (lifts of 2-6×, modest CIs supporting the lower-bound
   above unconditional baseline for cluster pnodes). The effect lives
   in the system_energy component (ORDC mechanism), with congestion
   showing a smaller secondary lift consistent with the components
   decomposition.

3. **The two findings together support a refined characterization:**
   "There is no Z threshold, but there IS an extreme-tail Z
   concentration of crazy LMP — visible only at percentile-99+ Z
   resolution." This is a paper-publishable refinement of the
   proposal's framing: the proposal was directionally right about
   where the effect lives but wrong about the sharpness of the
   transition.

### Caveat on the post-hoc

The post-hoc top-1% finding was triggered by an audit that explicitly
checked whether decile binning could mask an extreme-tail effect. It
was NOT specified before the run, so it inherits the usual post-hoc
caveats: no MT correction, no formal CI on the lift ratio, sample
sizes (n=316 at p99, n=32 at p99.9) are too small to support a
strong statistical claim. **A pre-registered top-1% analysis would
require advisor sign-off post-meeting**; this subsection's purpose is
only to surface the finding for that conversation.

The implementation has been audited (5/5 sanity checks pass: filter-
skip plumbing, in-filter byte-equivalent reproduction, total_lmp
derivation, Z range expectations, full-panel coverage). The
extreme-tail finding is a real feature of the data, not a bug.

---

---

## 2026-07-29 — Backfill executed; 2-5am/shoulder-season filter dropped for future analysis

**Context.** The Feb 2023 → Jun 2025 backfill (previous entry) executed
same day via accounts 2/3/4 (account `GRIDSTATUS_API_KEY` was found
nearly depleted — 68,137 rows / 60 requests remaining — and excluded).
`surg-gridstatus-validate` initially failed on duplicate keys (1,943
load rows, 6,048 LMP rows); root cause: a leftover `2024-07-07_to_2024-07-14`
probe-week chunk (pre-dating this session) didn't align with the
backfill's regular 7-day/30-day grid, so skip-if-exists didn't
recognize the overlap. The 4 stale files were deleted (data/ is
gitignored and reproducible) and validation passed on `unique_keys`
(0/0). One remaining validation finding, not fixed: 631 missing LMP
intervals per pnode (identical window across all 3 independent
pnodes, starting 2023-11-27T15:45, ~2.2 days) and 4,398 missing +
35 extra load intervals — consistent with the already-documented
sparse-interval-gap behavior of the gridstatus real-time feed, not a
pull defect; `build_5min.py` already NaN-masks gradient rows adjacent
to spine gaps. `analysis_panel_5min.parquet` rebuilt over the full
window: 350,789 rows (was 105,019 — ~3.3x).

**Decision.** For future analysis (not retroactive to the already-
pre-registered 5-min companion re-run on this extended panel, which
ran unchanged), drop the coarse `passes_proposal_filter` (shoulder-
season months × 2-5am window) as a default restriction. New analysis
work should default to the full panel unless a specific test has its
own pre-registered reason to subset.

**Rationale.** The coarse filter was designed as a signal-isolation
heuristic (CLAUDE.md "Signal-isolation strategy"), but sub-q1 item #6
already found it excludes the very events the "crazy LMP" framing
targets (0/2027 filtered observations exceed $250 across all deciles
and pnodes). Sub-q3's mandate is explicitly to "sharpen the coarse
2-5am × shoulder filter" against real-world event correlation — a
full, unfiltered panel is the natural starting point for that work.
The current 5-min companion re-run's own design already runs QR-full
and one Spec A branch on the full panel (only Spec A's `in_filter`
variant and tail-risk-curves are filter-gated), so this decision
mainly formalizes a direction the pre-registered design was already
moving toward.

**Revisit when:** sub-q3 design work begins in earnest and needs a
concrete replacement targeting criterion (event catalog windows,
`sync_reserve_event_active`, etc.) rather than "no filter."
---

## 2026-07-29 — Workstream C: two price channels, do not conflate

> **RECONSTRUCTED, not replayed.** The original entry was committed in
> `2179bbc` (lost with the working directory) and no `Edit` for it survives
> in the recovery transcripts. Rebuilt 2026-07-30 from
> `project_state_2026-07-29-workstream-c-shipped` in the recovery archive's
> memory directory. Figures are as recorded there; the surrounding prose is
> new. Treat quantities as attested-by-memory, not re-derived.

**Context.** The advisor meeting (sub-q1 item #5) happened; its outcome
split the remaining work into four workstreams: **A** unfiltered
tail-risk analysis, **B** attribution (data-center vs. weather, deferred
by the user until after C), **C** PJM primary-source LMP research, and
**D** nano-nuclear / SMR co-location (research-only, gated by sub-q2).
This entry records C. Deliverable: `docs/pjm-lmp-formation.md`, now a
third standing reference alongside `gridstatus-api-constraints.md` and
this file. PJM manuals vendored to `docs/pjm-sources/` (M11 rev137,
M12 rev57, M03 rev71) because the reference cites section numbers that
move between revisions.

**The finding that reframes sub-q1 — there are two price channels.**

- **Scarcity channel → system energy.** Verified empirically
  **locationally uniform** across our 3 pnodes (max difference
  9.09e-13 over 350,174 rows; for contrast, marginal loss differs by up
  to $22.60). Load *volatility* has **no** route into it: M11 §4.3 sets
  the reserve requirement from the largest single *contingency*, and the
  only load→requirement channel is gated on a Hot/Cold Weather Alert
  during on-peak hours.
- **Congestion channel → locational**, and load ramps **do** have a
  mechanism: M11 §2.2 prices the effect of "consumption by the resource
  on transmission line loadings".

**Consequence.** The `total_lmp > $250` tail-risk nulls were correct
**for the scarcity channel**, and they close the proposal's
ORDC-threshold framing. But the **QR-full positive z_slope on congestion
at τ=0.90/0.95 is the surviving positive finding and the live thread** —
not leftover noise. Spec A's low-Z rejection reverts to **unexplained**:
it is a congestion result that the scarcity story cannot explain in
either direction. An earlier draft overreached to "volatility doesn't
price"; that was corrected in both files before commit.

**Three corrections logged.**
1. The ORDC penalty is *not* confined to system energy — M11 §2.2
   qualifies both components; the allocation rule remains unknown.
2. $850 / $300 are Step 1 / Step 2 of *every* reserve demand curve, not
   SR / PR values.
3. $850 is not a meaningful LMP threshold — which is why the JLARC
   napkin math found it uninformative.

**Two items handed to workstream A.** PJM's 5-min price targets the
interval **end**, and RT SCED dispatches against a *forecast* over a
ten-minute look-ahead, so prices can **lead** load — the 2026-07-29
diagnostic only tested price-lags-Z. Separately, `dom_load_mw` is zonal
while congestion responds to nodal injection patterns.

**Revisit when.** Workstream A completes, or the ORDC allocation rule
between congestion and system energy is located in PJM source material.

---

## 2026-07-30 — Extended-panel interpretation: the premise is weak and congestion is level-driven

> **RECONSTRUCTED, not replayed.** Original committed in `0e39d51`
> (lost). Rebuilt from `project_state_2026-07-30-extended-panel-interpreted`
> in the recovery archive's memory directory.

**Context.** Interpretation of the extended ~3.4-year 5-min panel
(Feb 2023 → Jun 2026) plus the no-filter tail-risk run.

**1. The proposal's premise is weak.** DOM load grew **+21.5%** over the
panel, but ramp volatility did not: p90 moved 24.22 → 25.28 MW/min, and
**normalized by contemporaneous load it FELL every year**
(0.1850% → 0.1596%). Trend tests are null (OLS p=0.153, Spearman
p=0.168). A typical 5-min ramp moves **0.32%** of zonal load. The
project was premised on load growth bringing volatility growth; on this
panel it did not.

**2. Congestion is level-driven, not volatility-driven.** Hours with
congestion > $500 sit at the **99.1st percentile of load but only the
45.9th of ramp**. corr(load, congestion) = **+0.188**;
corr(|ramp|, congestion) = **+0.008**. By load decile, system energy
rises smoothly $17 → $62, while congestion behaves as a *switch*:
median ~$0.30 across nine deciles, then p95 $8.14 → **$254.36** in the
tenth. This matches `pjm-lmp-formation.md` §6/§9: the
load-volatility → reserve-depletion chain is **UNSUPPORTED**, and the
ramp channel exists only into congestion.

**3. Location matters.** Ashburn TX1 p99 **$611.37**, with 4.71% of
hours > $100, against SKFFSCRK (rural) $96.13 / 0.96%. SKFFSCRK–cluster
correlation is **+0.870** but Ashburn–cluster only **+0.209** — Ashburn
is decoupled from the rest of the cluster. Hourly panel only; the 5-min
panel has just 3 pnodes. **Caveat:** Ashburn n=17,448 vs 31,536 — the
coverage gap must be verified before this ships in F7.

**4. Effect size is small.** Across the whole observed Z span
(ΔZ ≈ 29.3 MW/min) the τ=0.95 slopes imply a q95 shift of only
**$1.91 pooled / $4.44 in 2025**, against **$71.20** needed to reach
$100. The implied shift decays with τ; at τ=0.99 congestion is already
$170 pooled.

**5. No-filter tail-risk is a non-result, not a refutation.** Flat at
$100 (d10/d1 = 0.98), with a small real lift at $5–$25. The $100 test
resolves ±19% against a predicted 2–5% lift, so it lacks the power to
refute anything at that threshold.

**Load-data artifacts.** Roughly 4 extreme reversion excursions
(> 1,500 MW) are artifacts — they move system energy $0–4, where the
confirmed-real 2024-07-10 NERC trip (1,479 MW) moved it **$81**. The
broader ~3,193-spike class is **NOT** established as artifactual. Of the
three evidence lines originally offered, two (forward-fill signature,
minute clustering) collapsed under testing; only the price-response test
held. See the separate 2026-07-30 ruling below.

**Structural limitation.** Per-facility / sub-zonal load is
unobtainable: DOM resolves to a single `load_area`, per-customer load is
confidential, and PJM dispatches against unpublished State-Estimator
*bus* loads (§5). This is a structural limit, not an acquisition gap.

**Revisit when.** The advisor rules on which QR specification is
primary, or a non-DOM control pnode becomes available.

---

## 2026-07-30 — Amendment: the pre-registered z_slope sign-flips under a load-level control

> **RECONSTRUCTED, not replayed.** Original committed in `857a758`
> (lost). Rebuilt from
> `project_state_2026-07-30-extended-panel-interpreted`.

**Finding.** Adding a contemporaneous load-*level* control flips the sign
of the pre-registered `z_slope` in **all 10 subset × τ cells**.

Day-block bootstrap results: pooled **−0.0605 [−0.0904, −0.0331]** and
**−0.1215 [−0.1920, −0.0672]**; 2026 negative at both τ; 2024 negative
at τ=0.90; **2023 and 2025 null**.

The sharpest case is **2024 at τ=0.90**: pre-registered
**+0.0367 [+0.0107, +0.0665]** against load-controlled
**−0.0266 [−0.0416, −0.0103]** — the same data producing opposite,
individually significant signs.

**Caveat, and why this is not simply a correction.** Z is dLoad/dt, the
derivative of the very control being added, so load level is a
confounder-or-mediator depending on the causal question. The two
specifications answer **different questions**, and neither is declared
primary here. Which one is primary is an **advisor call** and is added to
the sub-q1 item #5 agenda.

**Revisit when.** The advisor meeting rules on primary specification.

---

## 2026-07-30 — The 2026 escalation is largely system-wide; do not attribute it to data centers

> **RECONSTRUCTED, not replayed.** Original committed in `d77c96a`
> (lost). Rebuilt from
> `project_state_2026-07-30-extended-panel-interpreted`.

**Finding.** Holding load fixed at 20–22 GW — a band well sampled in all
four years — P(congestion > $100) runs
**1.89% / 5.58% / 5.03% / 37.80%** across 2023 / 2024 / 2025 / 2026.
The escalation is therefore not a simple consequence of more load.

But it is a step change in **both** components at once, dated to
January 2026: congestion p90 **$20.46 → $231.29** *and* system energy p90
**$86.32 → $292.19**. System energy is locationally uniform across PJM
(established in the workstream C entry above), so its tripling **cannot**
be a NOVA phenomenon.

**Ruling.** The driver is **unidentified**, and no non-DOM control pnode
exists in either panel to isolate it. **Do not attribute the 2026
escalation to data centers** in any write-up. Any such attribution would
be unsupported by this panel.

**Warning carried into sub-q2.** Projecting 2026 exceedance rates forward
would extrapolate an unidentified, possibly system-wide, possibly
transient shift as though it were data-center load growth. Sub-q2 must
not do this without first identifying the driver.

**Revisit when.** A non-DOM control pnode is acquired (deferred, not
rejected), or the January 2026 driver is identified from PJM
market-operations sources.

---

## 2026-07-30 — Reversion-spike class: standing recommendation NOT to filter (RULED 2026-07-31: do not filter)

> **RECONSTRUCTED during recovery.** This records the *status* of an open
> question so the research record is the single source of truth. It is
> deliberately NOT written as a settled decision.

**Question.** Whether to filter the ~3,193-spike class in `dom_load_mw`
before analysis.

**Status: CLOSED 2026-07-31 by the user — do NOT filter.** The
recommendation below was accepted in full; see the 2026-08-07 closure
entry at the end of this file. The text below is preserved as the
reasoning that led to the ruling.

*Superseded status line, kept for the audit trail:* "OPEN. Recommendation
is NOT to filter; the user has not ruled."
`docs/superpowers/specs/2026-07-30-surg-recovery-design.md` lists this
under "Research questions this recovery does not settle" as "heavily
leaning on no. Keep them in", and the 2026-07-30 memory entry records
"recommended NOT to filter; user never ruled."

**Evidence behind the recommendation.**
- Roughly **4** extreme reversion excursions (> 1,500 MW) *are* artifacts:
  they move system energy only $0–4, whereas the confirmed-real
  2024-07-10 NERC trip (1,479 MW) moved it **$81**.
- The broader **~3,193-spike class is NOT established as artifactual**.
  Of the three evidence lines originally advanced, two — the forward-fill
  signature and the minute-clustering pattern — **collapsed under
  testing**. Only the price-response test held.

Filtering on evidence this weak would remove real events, so the burden
of proof sits with filtering, not with keeping.

**Revisit when.** The user rules, or a decisive test separates the spike
class from real load excursions.

---

## 2026-08-07 — Pre-launch validation gate: green, and cheaper than the plan assumed

**Context.** Plan B rev2 Task 9 gates the ~890-request 5-min backfill behind a
cheap end-to-end proof, because 177 requests against a 250/month Free-tier cap
means one botched launch costs a calendar month.

**What ran.** The gate's substance was satisfied by the Task 7 Step 5 launcher
smoke-run (1-day window, 2026-06-01 → 2026-06-02, all five accounts), not by a
separate spend.

**Findings.**
- **SKFFSCRK (1356178201) is a valid 5-min `location_id`.** First live proof —
  the node had never been pulled at 5-min resolution. Returned 288 rows for one
  day (= 24 h × 12), `location=SKFFSCRK`.
- **The rename map is not stale.** The pulled chunk carries all four source
  columns `lmp` / `energy` / `congestion` / `loss`, which map onto
  `total_lmp_rt` / `system_energy_price_rt` / `congestion_price_rt` /
  `marginal_loss_price_rt`.
- **`--skip-lmp` works live.** Account 5 pulled `pjm_load` only, issuing zero
  LMP requests.
- **The launcher blocks.** 21.2 s wall, `rc=0`, `-DONE` marker written. A
  sub-10 s return would have meant the ERRATA E4 subshell/`wait` defect had
  recurred.

**Measured request cost — the number the gate exists to produce.**
`GET /api_usage` does **not** count against quota: account 6 read `0/250`
after being polled twice, and accounts 1–5 each read exactly `1/250 req,
288/500000 rows` after one data chunk apiece. **The per-chunk multiplier is
exactly 1.0.** Plan B rev2's Task 9 cost table (4 requests on account 6, 14
across all accounts) therefore overstates cost; the true figures are 2 and 2.

**Consequence.** A 177-chunk pnode pull costs 177 requests against the 250 cap
and 356,832 rows against the 500,000 cap (1,239 days × 288 rows/day) — both
with margin. All six accounts are distinct and the usage period ends
2026-09-01.

---

## 2026-08-07 — `rt_hrl_lmps` archive cutoff has rolled; hourly re-pull needs Historic tier

**Context.** Plan B rev2 Task 8 Step 4 prescribes a single
`surg.acquisition.pull --start 2022-10-02 --end 2026-05-11` command. It fails
with **400 Bad Request** on the first chunk.

**Diagnosis.** Not transient, and not a range-width problem: a *one-day* pull in
2022 fails identically while a one-day pull in 2026 succeeds, isolating the
cause to the **age** of the data. `rt_hrl_lmps` carries a **rolling 731-day
archive cutoff** (`docs/pjm-api-constraints.md` § "Archived data"). As of
2026-08-07 the Historic/Standard boundary sits at **2024-08-06**, so
**2022-10-02 → 2024-08-05 — roughly half the analysis window — is now Historic
tier**, where the `pnode_id` filter is rejected and a request spanning the
boundary is rejected outright. The plan's command does both forbidden things.

**Decision.** Re-pull in three parts, reproducing the 2026-05-12 coverage
choice (1a) rather than inventing a new one:
1. Historic, `--archive-tier --archive-subtype EHV`, one calendar year per
   request → the 8 EHV pnodes (Loudoun cluster + OX + BRISTERS).
2. Historic, `--archive-subtype ZONE` → DOM zonal.
3. Standard, normal `pnode_id` mode, 2024-08-06 → 2026-05-11 → all 11 targets.

Validated before launch: a 2-day archive-mode probe returned 384 rows = 8 EHV
pnodes × 48 h, all 8 present, client-side filter working.

**Ashburn coverage — ruled by the user 2026-08-07: Standard tier only.**
This also *resolves* the open `n=17,448` vs `31,536` question the plan flagged
as "verify before it ships in F7". It was never a pull failure:
**17,448 h = 727 days ≈ the 731-day cutoff.** ASHBURN TX1/TX2 are the only
LOAD-subtype targets, and PJM Historic stores ~10,786 LOAD-subtype pnodes, so
recovering 2 of them means downloading ~150M rows (~8.5 h). The asymmetry is
by design.

**Consequence to expect in verification.** Because the cutoff *rolls*, Ashburn's
Standard window is now 2024-08-06 → 2026-05-11 ≈ **15,432 hours**, about
**2,016 hours shorter** than the recorded 17,448. That shortfall is
rolling-cutoff drift from the ~3 months elapsed since the original pull — **not**
a restoration defect. Do not chase it as a code or data-revision divergence.

**Revisit when.** The reviewer pushback on the asymmetric Ashburn window
(Prof Wei / Lihui, recorded 2026-05-12) is taken up, at which point the ~8.5 h
Historic LOAD backfill becomes an overnight job.

---

## 2026-08-07 — SKFFSCRK geographic/electrical split, and three rulings closed

**Context.** Plan B rev2 Task 14. Three questions had been carried as open in
this file while the plan treated them as settled — the research record
contradicting the plan (ERRATA E17). This entry closes all three and records
the SKFFSCRK interpretation.

### SKFFSCRK is geographically rural *and* electrically coupled

Both descriptions are true and there is no contradiction between them.
SKFFSCRK sits in a markedly more rural area than the rest of the Loudoun
cluster, yet prices within ~$3/MWh of it (`:151`) because it sits on the same
500 kV EHV network inside the same congestion pocket. **Electrical distance is
not geographic distance.**

The rural framing traces to the original analysis, not to the July recovery
spec — `:4031` itself writes "SKFFSCRK (**rural**)".

**Substantive reading.** A geographically-rural node tracking the urban cluster
this closely is **evidence that congestion in this pocket is network-wide
rather than localized to where the data centers physically sit.** That
reinforces the standing finding that the 2026 escalation must not be attributed
to data centers. It does not settle it: every pnode in both panels sits inside
DOM, so a system-wide component still cannot be separated from a
Dominion-specific one from inside DOM alone.

**Deliberate asymmetry, do not "fix" it.** SKFFSCRK is *inside* the 6-node
hourly cluster (pre-registered pooling at `:298`, retained unchanged) and
*outside* the 3-node 5-min cluster-set (`FIVEMIN_CLUSTER_IDS`, added
2026-08-07). Pooling a comparison node into the cluster it is compared against
would contaminate every cluster-based regression target.

**Disclosure.** Because SKFFSCRK sits inside the 6-node cluster it is
correlated against, part of the recorded `+0.870` correlation is
self-correlation. The 6-node figure remains primary; a held-out (5-node)
figure will be reported beside it. *Both figures are pending the hourly panel
rebuild — see Task 13 Step 2, which must also identify whether the recorded
`:4031` numbers are `congestion_price_rt` or `total_lmp_rt`. That variable is
unnamed in the record and must not be guessed.*

### Three rulings, now closed

- **SKFFSCRK role — CLOSED.** Pulled as the 4th 5-min pnode; the hourly 6-node
  cluster pooling stays exactly as pre-registered. Geographically rural,
  electrically coupled.
- **Spike filtering — CLOSED 2026-07-31 by the user: do not filter.** The
  ~3,193-spike class stays in. These are the scarcity events the research
  question targets; removing them would remove the signal. This also keeps
  every recorded Phase 7 target reproducible, since all were computed
  unfiltered. Open since May. The 2026-07-30 entry's status line is updated in
  place.
- **Hourly window — CLOSED: unchanged at 2022-10-02 → 2026-05-11.** Not
  extended to match the 5-min window (which runs to 2026-06-30). It is
  pre-registered, hourly findings are lower-priority than the 5-min work, and
  the 5-min panel already covers 2026 at higher resolution. The asymmetry
  between the two windows is deliberate.

---

## 2026-08-07 — Hourly panel re-pulled; regression fixtures re-blessed at the corrected window

**Context.** Plan B rev2 Task 8. The re-pulled hourly panel failed all five
regression tests on a single field, `n_total_panel: ref=31536, cur=31608`.

### Root cause: the pre-loss panel violated the pre-registered window

Clipping the rebuilt panel to `>= 2022-10-05` reproduces **exactly 31,536**.
The pre-loss `hrl_load_metered` pull began 3 days late, and because the load
series is the panel's join spine (`build.py`: `load_df.merge(lmp_wide,
how="left")`), the pre-loss panel silently started at **2022-10-05** rather
than the pre-registered `ANALYSIS_WINDOW_START = 2022-10-02`.

The rebuilt panel is therefore **more correct, not merely different**. It is
verified complete: 31,608 rows against 31,608 expected hourly slots, whose
only irregularities are 4 duplicate stamps and 4 gaps — the signatures of the
4 DST fall-backs and 4 spring-forwards in the window.

**Decision: re-bless the fixtures at 31,608 rather than clip to 31,536.**
Matching the old numbers byte-for-byte was available (and was verified to
work) but would have encoded a pre-registration violation into the analysis to
keep a stale test green. These fixtures guard **code invariance** — the test is
`test_hourly_pair_bootstrap_equivalence`, protecting item #8's
`bootstrap_method` refactor — not data vintage.

### Measured delta

Data: panel **31,536 → 31,608** (+0.23%); filtered analysis base
**2,027 → 2,036** (+9 rows, +0.44%). The 3 recovered days are shoulder-season,
contributing exactly 3 days x 3 hours of filter-passing rows.

Derived statistics move **much more** than 0.44%, for reasons that are
mechanical rather than substantive:
- Thresholds are **quantile-based**, so a larger sample shifts the threshold
  and changes which points exceed: `n_exc` moved **55 → 52** (down, despite
  more data).
- Several flipped coefficients are **near-zero** (1e-5..1e-3) fit on
  n_exc ≈ 52, where sign is not identified.
- The Ashburn LOO arrays (1,745 → 1,544) are **not** from these 3 days at all;
  that is the 11.6% Ashburn window shrink from the rolling archive cutoff.
- Bootstrap CIs shift because resampling differs once inputs change at all.

Point estimates are stable where identified (e.g. `shape_diff = 0.257`
unchanged; its CI moved ~1%).

### Finding: these fixtures are weak guards

Their deep-threshold fields encode bootstrap-resampling noise and unidentified
near-zero coefficients that move under any perturbation. Re-blessing restores
a meaningful code-invariance guard only for the stable fields. **A future
failure in a deep-threshold coefficient should not be read as a code
regression without this context.**

### bristers q=0.995 spline is knife-edge unstable (not a code regression)

`gpd_continuous/bristers.json` `threshold_sweep[3].spline` changed from
`insufficient_bootstrap_reps` (with coefficients) to `failed` (coefficients
null). Sample size does not explain it: ashburn_tx1/tx2 converge at
**n_exc = 78**, while bristers fails at **159**, and four other pnodes
converge at that same 159.

Discriminator run — identical code, two panels:

| Panel | n_exc | spline | shape_coef[0] |
|---|---|---|---|
| full (31,608) | 159 | `failed` | None |
| clipped (31,536) | 158 | `insufficient_bootstrap_reps` | 0.1996 |

**One additional exceedance flips the optimizer.** This is data-driven, not a
regression in the restored `gpd_continuous` chain, so the `failed` state is
the true output of correct code on correct data and is re-blessed as such.
Independently of this recovery, **any conclusion resting on the bristers
q=0.995 spline fit is fragile** and should not be reported without this caveat.

---

## 2026-08-07 — ERCOT Stage 1: volatility falls once normalized; level beats volatility 132/135

**Context.** Stage 1 of the ERCOT diagnostic asks two descriptive questions —
is ERCOT load volatile and rising, and does hourly price track load *level*
more than load *volatility* — as an out-of-market check on the DOM findings.
Panel: **83,975 rows × 35 cols, 2017-01-01 00:00 → 2026-07-31 23:00 CPT**, nine
weather zones from 10 annual load archives, 15 settlement points from 5 annual
RTM price archives.

**Two data defects were found and handled. Both were invisible to the plan.**

- **The committed hour parser could not read a single real ERCOT day.** It used
  `strptime("%m/%d/%Y %H:%M")`, but hour-ending runs **1–24**, so every day
  closes `24:00` (3,650 rows) and `%H` accepts 00–23 only. The fall-back hour
  additionally carries a trailing ` DST` suffix. Its test passed because it
  asserted a *duplicate label* ERCOT never emits. Now parsed as
  `date + (hour − 1)`, verified against all ten files: 0 NaT, 0 NaN, and the
  only absent hours are the 10 spring-forward hours, one per year.
- **`Native_Load_2026.xlsx` republishes all of May 2026** — a contiguous
  744-row block, identical across all ten columns. This is a **publisher-side
  defect; anyone re-pulling that file will hit it.** Exact duplicates are
  dropped before the hour conversion, which is lossless and cannot touch the
  DST pair (whose rows carry *different* labels). **The ordering is the whole
  point:** deduplicating afterwards would have flagged all 744 as
  `dst_transition_hour`, and `assert_panel_quality` inspects only non-DST rows,
  so the bad data would have passed the gate in silence. A bound on the DST
  flag count was added for the same reason — without it that check is vacuous.

**Finding 1 — normalized volatility is FALLING, in all nine zones.**
2017 → 2025 (2026 excluded, partial through 07/31):

| zone | mean load | raw ramp | **normalized ramp** | p95 normalized |
|---|---|---|---|---|
| ERCOT | +36.7% | +8.4% | **−20.7%** | −23.3% |
| FWEST | +211.0% | +156.0% | **−17.7%** | −1.0% |
| NORTH | +106.5% | +93.4% | **−6.3%** | −10.7% |
| SOUTH | +27.9% | +3.4% | **−19.2%** | −18.4% |
| EAST | +29.9% | +29.6% | **−0.3%** | −2.6% |

All nine zones fall on the mean-normalized measure (−0.3% to −20.7%) and all
nine on p95-normalized (−1.0% to −23.3%). Raw ramps *do* grow — Far West by
156% — but slower than load. **Growth is being mistaken for volatility.**

**Finding 2 — load level beats load volatility in 132 of 135 zone-point pairs.**
Standardized betas, so magnitudes are comparable. Sanity anchor
ERCOT × HB_HUBAVG: `beta_level` **+0.185** vs `beta_volatility` **−0.036**.
Volatility's coefficient is *negative* in 8 of 9 zones — higher ramps go with
slightly *lower* prices, not higher.

**Far West is the sole exception and it inverts.** All 15 FWEST pairs show
`beta_level` **negative** (−0.071 to −0.101) and `beta_volatility` **positive**
(+0.068 to +0.086); in 3 of them (LZ_AEN, LZ_LCRA, LZ_SOUTH) volatility wins on
magnitude. Do not read this as a data-center signal. It is the confound the
research memo §2c already flagged: Far West load is Permian electrification and
its price is set by wind, so high load coincides with high wind and low prices.

**R² is 0.004–0.056 everywhere.** Load level and volatility together explain
almost none of hourly price variance. Whatever moves ERCOT prices, it is
mostly not either of these.

**Finding 3 — negative prices concentrate in the West, as the gate anticipated.**
`HB_PAN` **20.4%** of hours negative, `HB_WEST` 10.1%, `LZ_WEST` 8.5%; the other
twelve points sit at 1.6–2.5%. Per the spec gate criterion, **correlations on
HB_PAN and HB_WEST are uninterpretable** and the FWEST inversion above rests
partly on them. Medians are $18.51–$23.69, p99 $189–$290.

**This corroborates the DOM result in a second, unrelated market.** DOM
(this file, 2026-07-30): load **+21.5%**, p90 ramp 24.22 → 25.28 MW/min but
normalized volatility falling every year (0.1850% → 0.1596%), trend tests null,
congestion level-driven. ERCOT: load +36.7%, normalized volatility −20.7%,
level dominant 132/135. Two independently governed markets, same qualitative
answer.

**The two panels are not the same object, and the corroboration is only as
strong as that allows.** DOM is **5-minute resolution over ~3.4 years**
(Feb 2023 → Jun 2026); ERCOT here is **hourly over ~9.6 years** (2017 → Jul
2026). Hourly differencing cannot see the sub-hourly ramps the DOM measure is
built from, and the two windows overlap only partially. That the normalized
trend points the same way in both is meaningful precisely because the
measurements are so different — but it is agreement in *direction*, across
different instruments, not a matched comparison.

**Do not claim the two are directly comparable.** `level_vs_volatility` has
**no time controls**. Load level and price both carry strong diurnal and
seasonal structure, so `beta_level` is inflated by both tracking time-of-day.
The DOM finding it echoes — `z_slope` sign-flipping under a load-level control —
came from a specification *with* controls. The agreement is qualitative and
directional; it is not an effect-size replication, and nothing here should be
written up as one.

**Two artefacts noted, neither worth fixing.** (1) The gradient differences
positionally, so at each spring-forward seam a two-hour wall-clock jump reads as
one step (overstated) and at fall-back the duplicate hour reads as near-zero —
about 180 of 83,975 rows, changing no conclusion. (2) ERCOT gives the repeated
fall-back hour the same Delivery Date and Hour, so its two prices average into
one value: one hour per year, four years.

**Gate recommendation — RULED 2026-08-08.** Stage 1 succeeded on its own
terms: the answer is trustworthy, the two data defects are found and handled,
and the QA gates now fail loudly on the modes that actually occur. But the
answer it produced **undercuts the volatility premise a second time**. The
recommendation is therefore *not* to proceed to a Stage 2 built on load
volatility as the driver, and instead to redirect toward load *level* and
locational structure, which is where both markets point.

**Ruling (user, 2026-08-08): accepted — Stage 2 will not be built on load
volatility.** Any future ERCOT work proceeds from load level and locational
structure. No Stage 2 is scheduled; the DOM thread (figure build → sub-q2 →
sub-q3) takes priority, and an ERCOT continuation would need its own
brainstorm/design pass starting from the level-and-location framing.

**Scope.** 2017–2026 only. ERCOT publishes four load schema families; 2016
renames four zones and stores a Timestamp, 2015 and earlier are `.xls`, and
pre-April-2003 files use 11 control areas. Extending earlier is a parser
project, not a config change.

---

## 2026-08-08 — Plan B restoration verification: recorded targets reproduce; divergences are data revision

**Context.** Final step of Recovery Plan B rev2 (Task 13). The 5-min panel was
rebuilt 2026-08-07 from the re-pulled gridstatus data (352,467 rows ×
31 cols, 4 pnodes) and the full pre-registered analysis re-ran overnight
(19:12 → 05:58 EDT, ~10h46m; n_boot=1000, qr_n_boot=500; the op7 cluster
guard never fired — 641 unique night islands against the 10 minimum). Every
recorded 5-min target from the pre-loss panel was checked against the
restoration. Hourly-side checks were closed earlier (see the two 2026-08-07
entries above).

**Verification table.** Recorded targets vs. the rebuilt panel:

| Target | Recorded | Observed | Verdict |
|---|---|---|---|
| Panel rows | 350,789 | 352,467 (+1,678, +0.48%) | diverged — data revision |
| DOM load growth (2023 annual mean → 2026 annual mean) | +21.5% | +21.8% | ≈reproduced |
| Ramp p90 by year (MW/min) | 24.22 → 25.28 | 24.22 → 25.38 | 2023 exact; 2026 drift |
| Ramp p90 as % of load (p90 of per-row ramp/load) | 0.1850% → 0.1596% | 0.1850% → 0.1598% | 2023 exact; 2026 drift |
| P(cong > $100) at 20–22 GW, 2023/24/25/26 | 1.89 / 5.58 / 5.03 / 37.80% | 1.89 / 5.58 / 5.03 / 36.05% | 2023–25 exact; 2026 drift |
| Congestion p95, load decile 1 → 10 | $8.14 → $254.36 | $8.14 → $254.19 | d1 exact; d10 drift |
| 2024 τ=0.90 z_slope, pre-registered | +0.0367 | **+0.0367** | **exact** |
| 2024 τ=0.90 z_slope, load-controlled | −0.0266 | **−0.0266** | **exact** |

Recipe notes recovered during verification (the computing scripts were lost
with the directory): "load growth" is annual-mean 2023 vs 2026 (the
first-month/last-month recipe gives +37.4% and is not what was recorded);
"ramp p90 %" is the p90 of per-row ramp/load, not p90(ramp)/mean(load). The
z_slope rows were reproduced as point estimates with the qr_full periodic
basis on the 2024 subset (n=105,105); both reproduce to all four recorded
decimals, so the 2024 sign-flip finding (pre-registered positive,
load-controlled negative) stands unchanged on the restored panel.

**Discriminator verdict: data revision, not code.** Every pre-2026 statistic
reproduces exactly at recorded precision; only 2026-touching quantities move,
and the raw-series changes localize to (a) the documented 631-interval
2023-11-27 LMP gap, now backfilled by gridstatus (863/864 rows present in
that window), and (b) load-spine gaps backfilled between the 2026-07-29 pull
and the 2026-08-07 re-pull (+1,678 rows; remaining missing-vs-theoretical is
4,305 intervals, dominated by the known Feb-2023 early-history sparseness).
This is the expected behavior of a warehouse that carries republished values
(`gridstatus-api-constraints.md`) — no code defect is indicated, and nothing
was tuned to match.

**Run-output confirmations.** All five QR-full labels wrote both primary and
year-FE fits; both GPD variants and all four tail-risk pnodes wrote; every
per-pnode tail-risk result carries `resolution: "5-min"` — live confirmation
that the merged `run_tail_risk_curves` fixed the pre-loss hardcoded "hourly"
figure label. Pooled QR-full congestion cluster at τ=0.90: z_slope +0.043
(primary), +0.0257 (year-FE) with a year_2026 fixed effect of +$49.9 — the
2026 escalation surfacing as a level shift, consistent with the standing
system-wide interpretation. One incidental external cross-check: the market
monitor's late-May 2026 Ashburn–Goose Creek constraint event (~$150M/72h)
appears in the rebuilt panel exactly where reported (GOOSECRE daily
congestion p95 $550/$502 on May 18–19 and $564 on May 27 against
single-digit neighbors; see `docs/external-context-research-2026-08.md` §7).

**Decision.** Restoration is verified; the pre-loss findings carry forward to
the restored panels without reinterpretation. SKFFSCRK (new, no baseline) is
characterised rather than verified, per plan. Plan B is complete pending the
push.

## 2026-08-08 — Sub-q1 figure set built: twelve figures, every caption number recomputed

**Context.** `docs/superpowers/specs/2026-07-30-subq1-figure-set-design.md`
specifies twelve figures for the sub-question 1 report. They were built over
Tasks 0–13 of
`docs/superpowers/plans/2026-08-08-subq1-figure-set-build.md`, on branch
`feature/subq1-figure-set`. **No caption number was transcribed from the
design spec.** Every one is computed at plot time from the current panels or
from `outputs/figure_inputs/*.json`, because three drafted captions turned
out to assert values the data contradicts (F4, F8, and the shared
`ARTIFACT_NOTE`). 97 tests cover the set; `python -m
scripts.plot_subq1_results` regenerates all twelve PNGs from a clean slate
under `-W error::UserWarning`.

**Spec value vs recomputed value.**

| quantity | spec | recomputed | note |
|---|---|---|---|
| F1 load growth | +21.5% | **+28.0%** | spec compared a half-year to a full one |
| F1 ramp p90 range | — | 21.91 → 28.38 MW/min | OLS trend p=0.158, not significant |
| F3 congestion p90 by year | — | 9.56 / 8.81 / 13.46 / **60.76** | 2026 is 6.4× 2023 |
| F4b `>$100` per year | 479 / 804 / 1,505 / 3,737 | 479 / 804 / 1,505 / **3,768** | 2023–25 exact |
| F4b `>$250` per year | 59 / 206 / 399 / 1,612 | 59 / 206 / 399 / **1,620** | 2023–25 exact |
| F4b `>$500` per year | — | **0** / 73 / 128 / 681 | 2023 still zero |
| F4b `>$1000` per year | — | 0 / 7 / 13 / 62 | worst month is 2026-06, not 2026-01 |
| F5 2024 τ=0.90 pre-registered | +0.0367 [+0.0107, +0.0665] | +0.0367 [**+0.0095, +0.0631**] | point exact, CI drifts |
| F5 2024 τ=0.90 load-controlled | −0.0266 [−0.0416, −0.0103] | −0.0266 [**−0.0420, −0.0115**] | point exact, CI drifts |
| F11 20–22 GW row | 1.89 / 5.58 / 5.03 / 37.80 % | 1.89 / 5.58 / 5.02 / **35.84** % | |
| F11 load-growth share | 85.2 / 59.1 / 12.2 % | 85.1 / 59.2 / **12.7** % | |

2026 values drift where 2023–2025 match exactly. That is the data-revision
signature already established in the 2026-08-08 Plan B entry above, not a
computational disagreement.

**1. F5 — two reversal counts, not one.** Adding load level as a control
reverses the sign of the ramp coefficient in **8 of 10** period × τ cells.
But only **3** of those (2024 τ=0.90, pooled τ=0.90, pooled τ=0.95) have
*both* confidence intervals excluding zero. The other five are two imprecise
estimates disagreeing, which is not the same claim. Quoting "8 of 10" alone
overstates the finding 2.7×; the figure states both, and prose about the
specification conflict must do the same.

**2. F7 — the locational contrast was measured across mismatched windows.**
Ashburn TX1 enters the hourly panel only on 2024-08-06. Comparing its late
window against other pnodes' full-panel statistics inflates the gap, since
congestion escalated sharply in 2026. On the **common window**
(2024-08-06 → 2026-05-10, n=15,432) the Ashburn-vs-SKFFSCRK gap is **~3×**
(4.78% vs 1.60% above $100), not the ~4.9× the spec implies. **The
locational finding stands; its magnitude was overstated.** A second result
strengthens it: Ashburn correlates only 0.25–0.48 with every other series,
while the cluster, both controls and SKFFSCRK intercorrelate at 0.83–0.94 —
Ashburn is doing its own thing, not riding a common DOM signal.

**3. The unnamed variable at `:4286` is closed.** That entry records the
`:4031` numbers as resting on a variable "unnamed in the record" that "must
not be guessed." It is **`congestion_price_rt`**: it reproduces $610.03 /
4.78% and $95.92 / 0.96% exactly, whereas `total_lmp_rt` gives $803.97 /
11.54% and $301.29 / 5.38% — nowhere close.

**4. The held-out correlation the `:4281` ruling requires is now computed.**
SKFFSCRK sits inside the 6-node `cluster_mean` it is compared against
(verified equal to the 6-pnode mean to 2.3e-13), so part of the recorded
+0.870 is self-correlation. On the common window: **0.8703 primary vs 0.8283
held out** (inflation +0.042); on the full window 0.8526 vs 0.8049 (+0.048).
**The contamination is modest and the qualitative finding survives** at
r≈0.83 — which reinforces the standing reading that congestion in this
pocket is network-wide rather than data-center-localised. F7 reports both
series and labels the node "SKFFSCRK (inside cluster)", never "control".

**5. The load-artifact screen needs a revision note.** Entries `:4048` and
`:4150` record "roughly **4** extreme reversion excursions (> 1,500 MW) …
they move system energy **$0–4**, where the confirmed-real 2024-07-10 NERC
trip (1,479 MW) moved it **$81**." Recomputed on the current panel with a
**gap-aware** delta, the criterion and the class both reproduce, but two
numbers move:

| time | drop MW | rebound MW | system-energy response |
|---|---|---|---|
| 2023-12-06 11:10 | −1,709.7 | +1,529.2 | +$2.35 |
| 2025-08-13 10:30 | −1,630.4 | +1,730.5 | **−$13.30** (price rose) |
| 2026-06-11 07:40 | −1,575.0 | +1,683.7 | **−$1.05** (price rose) |
| **2024-07-10 19:05 (real trip)** | −1,478.6 | +24.8 | **+$80.06** |

There are **3**, not 4, and the worst response is **$13.30**, not $0–4. Two
of the three moved price *upward*, which strengthens the positive control
rather than weakening it: drop magnitude alone predicts no price response,
and only the non-reverting trip moved price. The ruling itself is unchanged —
the spike class stays unfiltered. `_style.ARTIFACT_NOTE`, which every
tail-touching figure appends, was corrected to these values.

**Gap-awareness matters here.** A bare `.diff()` on the 5-min panel reads the
5h50m hole between 2024-07-10 21:45 and 2024-07-11 03:35 as a single
**−4,933 MW** step — larger than anything real in 3.4 years, and it would
have ranked first in any unguarded screen.

**6. F8 — the restored no-filter script would have mislabelled its output.**
The archived `run_5min_nofilter.py` called `run_tail_risk_curves(...)`
without `resolution=`, whose default is `"hourly"` and which is stamped into
every result (`tail_risk_curves.py:444`, `:546`). That is the `c4a64e7` bug
class. Fixed and verified on the smoke pass before the production run. At
**n_boot=1000** over 351,371 rows the curve is flat across all ten deciles
(1.78–1.95%) with **d10/d1 = 0.9797** at $100 — reproducing the recorded 0.98.
Note the figure's stated precision (±8.1% of the mean rate, per-decile) is a
*different quantity* from the ±19% recorded at `:4045`, which is the
resolution on the d10/d1 contrast.

**7. F9 — Spec B's trajectory, and the secular component.** The continuous
ξ(Z) slope is β₁ = **−0.0074 / −0.0073 / −0.0260 / +0.0104** at threshold
quantiles 0.90 / 0.95 / 0.99 / 0.995. Every interval spans zero, so
"underpowered per pre-reg Rule 2" stands; the magnitude deepens to q=0.99
and then **flips sign at q=0.995 on a CI four times as wide**, which a single
quoted number hides. The secular component (primary − year-FE) excludes zero
at τ=0.90 (+0.138 [+0.100, +0.193]) and τ=0.95 (+0.158 [+0.022, +0.282]) and
spans it at τ=0.99 (−0.258 [−0.947, +0.352]).

**8. F11 — what the 2026 escalation is, and is not.** Within fixed 2,000 MW
load bins, 2026 exceeds $100 far more often than 2023 at the *same* load:
1.89% → 35.84% in the 20–22 GW bin. Applying 2023's conditional response to
each later year's load distribution, load growth explains 85.1% of 2024,
59.2% of 2025, and only **12.7%** of 2026. **Two caveats travel in the
caption and must travel with any prose use.** The counterfactual's magnitude
is unreliable — 2023 barely visited the load levels later years reach
(22–24 GW has 10 baseline observations, 24–26 GW has none), so it
extrapolates without support; the direction is solid, the number is not.
And **the change is not local**: it is a January-2026 step in both congestion
and system energy, system energy is locationally uniform across PJM, and
there is no non-DOM control pnode in this panel. **A substantial part of the
2026 escalation is system-wide and its driver is unidentified. It must not be
attributed to data centers.**

**Presentation rulings carried into the code.** Bars encode magnitude by
length, which is meaningless on a log axis, so symlog series are drawn as
markers and lines (F4b, F3). F4b buckets by **month, not year**, so the
partial 2026 is never annualised — the finding survives the conservative
presentation, since 3,768 intervals above $100 in six months already exceeds
1,505 in twelve. Unvisited load bins are NaN rather than 0.0% (F11), so a
line breaks instead of drawing a measured zero where there is no
measurement. F5's and F6's provenance quote the **pooled** cell's n, since
per-period n ranges 51,746 → 352,467.

**Decision.** The figure set is complete and its numbers are the ones above.
Where a recomputed value disagrees with the design spec or with an earlier
entry, **the recomputed value governs** and the divergence is recorded here
rather than by editing the earlier entry, per this log's append-only
convention. The `:4048` / `:4150` artifact-screen numbers are superseded by
item 5; the `:4286` open question is closed by item 3; the `:4281`
disclosure requirement is satisfied by item 4.

**Revisit when.** The panels are re-pulled again (2026 values drift with
revision), or the advisor rules on framing, at which point F5's two reversal
counts and F11's two caveats are the constraints any narrative has to
respect.

## 2026-08-09 — NYISO Stage-1 production run: BLOCKED by two zone-name defects in the committed features module

Task 5's driver (`scripts/nyiso_diagnostic.py`) was written verbatim from the
plan and run against the full 928-zip real archive. It failed. Two
independent, real-data defects live in the already-committed
`src/surg/preprocessing/nyiso_features.py`, which is out of scope for Task 5
to fix (per the session's explicit "do not modify anything NYISO/CAISO
outside what Task 5 creates" instruction). Neither is a one-line driver fix.

**Defect 1 — `parse_load`'s `ZONE_MAP` does not cover NYISO's pre-2005 combined zone.**
From the start of the load archive (2001-06-01) through 2005-01-30, NYISO
reports a single combined `"N.Y.C._LONGIL"` zone instead of the split
`"N.Y.C."` / `"LONGIL"` pair the 11-entry `ZONE_MAP` (nyiso_features.py:7-12)
expects. The split takes effect exactly on 2005-01-31 (verified day-by-day
across the `20050101` zip). 1,320 of the archive's daily `palIntegrated`
files carry the combined name. `parse_load`'s strict
`unknown = set(out["Name"]) - set(ZONE_MAP)` check
(nyiso_features.py:34-36) raises `ValueError: unknown NYISO zone names:
['N.Y.C._LONGIL']` on any read that includes this era — which every read
does, since `scripts/nyiso_diagnostic.py`'s `read_family` concatenates the
entire archive before `parse_load` ever runs, and `MAX_START` (driver line
29, `2001-06-01`) is never used to truncate the raw files read — only to
filter reporting windows after the fact.

**Defect 2 — `parse_lbmp`'s `ZONE_MAP` never covers NYISO's external interface/proxy zones.**
Independent of any date range: every `damlbmp_zone` and `realtime_zone` file
across the full 1999-2026 archive (checked at the earliest zip, the
2004/2005 boundary, and the most recent zip) reports LBMPs for four
zones beyond the 11 internal load zones — `H Q`, `NPX`, `O H`, `PJM`
(external interface/proxy points: Hydro-Québec, Neptune, Ontario-Hydro tie,
PJM). `parse_lbmp`'s identical strict check (nyiso_features.py:67-69) raises
`ValueError: unknown NYISO zone names: ['H Q', 'NPX', 'O H', 'PJM']` on
literally every price file in the archive, at every date. This means the
price side of the driver cannot succeed against real data at *any* window,
not just the pre-2005 era — a change to `MAX_START` alone would not have
unblocked the run even if defect 1 didn't exist.

**Why this isn't a driver-only fix.** Both defects are inside the
already-committed `nyiso_features.py` (Task 4), not
`scripts/nyiso_diagnostic.py` (Task 5's own file). The driver's `read_family`
has no date-filtering or zone-filtering hook before handing frames to
`parse_load`/`parse_lbmp`. Fixing either defect changes `ZONE_MAP` and/or the
strict-unknown-name check in a file this task was told not to touch.

**Recommended lowest-blast-radius fix (not implemented — human call).**
For defect 1: either (a) restrict the driver's effective load-read window to
start 2005-01-31 (accepting the loss of the 2001-06 -> 2005-01 pre-split
era), or (b) extend `ZONE_MAP` to accept `"N.Y.C._LONGIL"` as its own
combined-zone column and decide how a 10-zone early era reconciles with the
11-zone `ZONES` list used everywhere downstream (`add_zone_gradients`,
`assert_panel_quality`'s per-zone NaN check, `trend_tables`). For defect 2:
extend the "known but ignored" set in `parse_lbmp` to drop `H Q`/`NPX`/`O
H`/`PJM` before the unknown-name check, mirroring how loss/congestion
columns are already dropped by column selection rather than raising. Option
(b)-for-defect-1 plus the defect-2 drop together would be the smallest
change; both require touching `nyiso_features.py`, so a human should decide
whether that reopens Task 4 or gets folded into a new task.

**Status.** Not committed. `scripts/nyiso_diagnostic.py` is untracked in the
worktree (transcribed verbatim from the plan, unmodified) for reference. No
panel, no figures, no results. Per the session's explicit contingency for
this scenario, IESO (Tasks 9-11) proceeded independently and is reported
separately below.

## 2026-08-09 — IESO Stage-1 production run: fetch, features, and results

**Task 9 (fetch) — plan-text contradiction, not a blocker.** `scripts/ieso_fetch.py`
was transcribed verbatim and run inline. It exited 1: the docstring
(lines 1268-1269 of the plan) states the HOEP era ended 2025-04-30, but
`LAST_YEAR = 2026` (line 1287) applies uniformly to all three families with
no per-family override (loop at lines 1296-1305), so the script 404s
fetching `PriceHOEPPredispOR/PUB_PriceHOEPPredispOR_2026.csv` — a file that
does not exist because the era it would belong to ended in April 2025. This
is the last file of the last family processed, so every file the fetch
needed to have landed by then already had: 24 `DemandZonal` (2003-2026), 25
`Demand` (2002-2026, unused by the Task 11 driver), 24 `PriceHOEPPredispOR`
(2002-2025) — 73 files total, matching the plan's own "~73 files" estimate.
Verified by directory listing before proceeding. Committed as printed
(`b3a5cdd`) per the transcribe-verbatim path (constraint 1), not stopped,
since the underlying data goal was met and the defect is a fetch-loop range
bound, not a data-correctness bug.

**Task 9 Step 3 — real HOEP header confirmed, no `HOEP_COLS` change needed.**
`head -8 data/raw/ieso/PriceHOEPPredispOR/PUB_PriceHOEPPredispOR_2024.csv`:
three `\`-prefixed preamble lines, then header row
`Date,Hour,HOEP,Hour 1 Predispatch,Hour 2 Predispatch,Hour 3 Predispatch,OR 10 Min Sync,OR 10 Min non-sync,OR 30 Min`.
`Date`, `Hour`, `HOEP` are exactly as `HOEP_COLS` (Task 10) assumed —
verified against the real file both by inspecting bytes and by loading it
through the exact `pd.read_csv(path, comment="\\")` path Task 11 uses. The
real `DemandZonal` header was checked the same way and also matches
Task 10's `ZONE_MAP` source names exactly. Neither constant needed
adjustment.

**Task 10/11 — a defect the printed test suite couldn't see: mixed date formats.**
`ieso_features.py`'s `_hour_ending_to_beginning` called
`pd.to_datetime(dates)` with no explicit format (as printed). Task 10's
tests passed (4/4) because the synthetic fixture uses one date string per
test. Running Task 11 against the real, full `DemandZonal` archive (all 24
years concatenated) crashed: `PUB_DemandZonal_2017.csv` uses `"2017/01/01"`
while every other year (2003-2016, 2018-2026) uses `"2017-01-01"`-style
dashes — a one-year formatting quirk in IESO's own publication, confirmed by
scanning the first row of every year's file in both `DemandZonal` and
`PriceHOEPPredispOR` (the latter is dash-consistent across all 24 years, so
only `DemandZonal` needed the fix). Unlike the NYISO defects above, this
file is Task 10's own output from this session, not on the
do-not-modify list, so it was fixed directly:
`pd.to_datetime(dates)` -> `pd.to_datetime(dates, format="mixed")`
(`ieso_features.py:23`), matching the sibling NYISO module's existing
`format="mixed"` precedent (`nyiso_features.py:17`). Year-first in both
formats, so no dayfirst ambiguity. A regression test
(`test_parse_demand_zonal_mixed_date_format`) was added. Committed
separately (`2c6393d`): `fix(ieso): parse mixed date formats - 2017
DemandZonal uses slashes`.

**Production run.** Panel: `(204023, 25)` rows. `assert_panel_quality`
passed with `dst_pairs_per_year=0` (IESO is fixed-EST; zero duplicate
timestamps, zero `dst_transition_hour` flags, as expected). Rows/year is
8760 (8784 in leap years 2004/2008/2012/2016/2020/2024) for every full year;
the three exceptions are explained by data coverage, not gaps: 2003 = 5,880
rows (`PUB_DemandZonal_2003.csv` starts 2003-05-01, not January — `MAX_START
= 2003-01-01` in the driver precedes the data by four months, harmless for
windowing but noted here so it doesn't read as a hole); 2025 = 8,759 rows
(one hour short of a full non-leap year; not investigated further — flagged
for anyone extending this panel); 2026 = 5,280 rows (partial year, archive
current through roughly August 2026).

Price quality (HOEP, from `MAX_START = 2003-01-01`): n = 192,857,
negative_share = 3.74%, median = $29.33/MWh, p99 = $135.36/MWh.

Level-vs-volatility horse race, **max window** (2003-01-01 -> 2025-05-01
exclusive, i.e. through 2025-04-30, the Market Renewal boundary):

```
     zone price_series  beta_level  beta_volatility       r2      n  level_wins
  ontario         hoep    0.539397         0.008923 0.291318 192856        True
northwest         hoep    0.377407         0.052088 0.148660 192856        True
northeast         hoep    0.341326         0.027285 0.117989 192856        True
   ottawa         hoep    0.505896        -0.029211 0.252172 192856        True
     east         hoep    0.375105        -0.015324 0.140706 192856        True
  toronto         hoep    0.429030         0.026708 0.183973 192856        True
     essa         hoep    0.419530        -0.029999 0.174648 192856        True
    bruce         hoep    0.049892         0.002020 0.002496 192856        True
southwest         hoep    0.494489         0.000300 0.244527 192856        True
  niagara         hoep    0.535674         0.029667 0.287853 192856        True
     west         hoep    0.566242        -0.013350 0.319209 192856        True
level wins in 11 of 11 cells
```

**overlap window** (2023-01-01 -> 2025-05-01 exclusive):

```
     zone price_series  beta_level  beta_volatility       r2     n  level_wins
  ontario         hoep    0.408710         0.012621 0.167707 20424        True
northwest         hoep    0.176111         0.067407 0.036543 20424        True
northeast         hoep    0.266063         0.028168 0.072128 20424        True
   ottawa         hoep    0.356920         0.004746 0.127823 20424        True
     east         hoep    0.323087         0.066899 0.110652 20424        True
  toronto         hoep    0.344009         0.020778 0.118214 20424        True
     essa         hoep    0.391174         0.003844 0.153396 20424        True
    bruce         hoep    0.229340        -0.024013 0.051602 20424        True
southwest         hoep    0.367493         0.012962 0.135449 20424        True
  niagara         hoep    0.344866         0.011371 0.119196 20424        True
     west         hoep    0.397985         0.000528 0.158425 20424        True
level wins in 11 of 11 cells
```

Level wins in all 11 of 11 cells at both windows — no time controls, so
`beta_level` carries shared diurnal/seasonal structure (same descriptive-only
caveat as ERCOT and NYISO).

**Trend headline, 2004 -> 2024 (earliest -> latest full calendar year; 2003
and 2026 are partial, see above).** System (Ontario) mean load fell -8.5%
(17,468 -> 15,986 MW); normalized volatility (`grad_mean_norm`) was
essentially flat (-1.1%). Per zone, load and normalized-volatility change
both vary in sign and magnitude across the 11 zones (bruce +174.9% load /
-66.2% norm-vol; northwest -43.9% load / +33.6% norm-vol; toronto +0.9% load
/ -9.4% norm-vol; full table in `outputs/ieso_diagnostic/trends_by_zone_year.csv`).
These are raw numbers only — no cross-zone driver analysis was performed
here.

**Caveats (IESO memo §6, front-of-caption for any use of these numbers):**
- **ICI / Global Adjustment peak-shaving endogeneity** — the strongest
  peak-response endogeneity effect in this project. Class A consumers pay
  Global Adjustment pro-rata to their share of Ontario's top five annual
  demand peaks; IESO itself publishes a "Peak Tracker." Observed zonal load
  at system peaks is behaviorally suppressed by design, and any data center
  on Class A billing inherits this incentive. Ontario's top-hour load shape
  is partly a policy artifact, not a physical one.
- **HOEP is a wholesale-energy-only signal.** Global Adjustment means HOEP
  alone understates the all-in price large consumers actually face. Fine
  for cross-market comparability; must travel as one caption line wherever
  HOEP is used as "the price."
- **Prices are CAD**, not USD — no FX adjustment was applied here.
- **Embedded generation nets out of "Ontario Demand"** before it ever
  reaches this panel (CAISO-style metered-load caveat, milder scale here).
- **HOEP era ends 2025-04-30** (Market Renewal, 2025-05-01): dispatch,
  price formation, and settlement all changed at that boundary. Both
  horse-race windows in this run stop at that boundary by construction
  (`HOEP_END = 2025-05-01` exclusive); the load series itself is unaffected
  by the regime change and continues past it in the panel.

Committed: `scripts/ieso_diagnostic.py` + this entry.

## 2026-08-09 — NYISO Stage-1 zone-convention fixes + two-panel production run

Resolves the blocker recorded above ("NYISO Stage-1 production run: BLOCKED
by two zone-name defects"). Both defects lived in the already-committed
`src/surg/preprocessing/nyiso_features.py` (Task 4); fixed there, not in
the driver, per the human decision to reopen Task 4 rather than work around
it in `scripts/nyiso_diagnostic.py`.

**Fix 1 (`parse_lbmp`, external proxy buses).** Added a module-level
`EXTERNAL_PRICE_ZONES = {"H Q", "NPX", "O H", "PJM"}` (Hydro-Quebec,
Neptune, Ontario-Hydro tie, PJM). Rows with these names are dropped before
the unknown-name check; anything else unrecognized still raises
`ValueError`, so the drift guard is unchanged for genuine schema drift —
mirrors the roster-filter pattern already used in `caiso_features.py`'s
`TAC_MAP`/WEIM exclusion.

**Fix 2 (`parse_load`, pre/post-2005 zone convention).** Added a
keyword-only `merge_nyc_longil: bool = False` parameter. Default (`False`,
today's split behavior, unchanged): 11 zones; the pre-2005-01-31 combined
`N.Y.C._LONGIL` name is not in `ZONE_MAP`, so it still hits the existing
"unknown zone name" raise — pre-split rows are rejected, not silently
dropped, exactly as required. `merge_nyc_longil=True`: a new
`MERGED_ZONE_MAP`/`MERGED_ZONES` (10 zones) collapses `N.Y.C._LONGIL`
(pre-split), `N.Y.C.`, and `LONGIL` (post-split) into one `nyc_longil`
column; post-split the pair is summed via
`pivot[raw_names].sum(axis=1, min_count=1)` (`min_count=1` so a
genuinely-all-missing row still surfaces as NaN and trips
`assert_panel_quality`, rather than silently reading as 0 MW).

**Boundary verified clean, not assumed.** Queried the raw
`palIntegrated` archive day-by-day from 2005-01-25 to 2005-02-05:
`N.Y.C._LONGIL` reports on every day through 2005-01-30 and never again;
`N.Y.C.`/`LONGIL` report from 2005-01-31 onward and never before. No
overlap day, so the merged-mode summation cannot double-count and
`SPLIT_START = 2005-01-31` is the correct split-mode window boundary (not
2005-02-01).

**Tests.** 5 new tests added to `tests/test_nyiso_features.py`: external-bus
dropping, still-raises on a genuinely unrecognized name, merged-mode
summation of the post-2005 pair, merged-mode continuity across the
boundary (single combined value pre-split, summed pair post-split, no
NaNs), and split-mode rejection of combined-zone rows. `pytest
tests/test_nyiso_features.py -q`: 9 passed (4 baseline + 5 new). Full
suite: 468 passed, 5 skipped (baseline 463 passed + 5 new; skip count
unchanged).

**Driver (Task 5) ships two panels**, both against the full real archive
(928 zips): Panel A (merged, 10 zones, full depth) and Panel B (split, 11
zones, from 2005-01-31). Panel B's raw load frame is filtered to
`Time Stamp >= 2005-01-31` *before* `parse_load` runs, so the split-mode
"reject combined rows" guard stays live rather than being bypassed. The
price side (11 NY zones, four external buses dropped) is read once and
merged into both panels unchanged — `level_vs_volatility` takes a cross
product of load zones x price columns, so no name alignment between the
merged/split load zones and the price zones is required or attempted; no
merged price series was invented. Both panels also run the common-overlap
window (2023-01-01 → 2025-05-01 exclusive). Total wall time: ~97s for both
panels combined.

Non-float `load_mw_*` dtype check (added defensively for this run) did not
fire on either panel — the "sum instead of rename" restructure did not
silently pass a non-numeric column through.

**Panel A (merged) — rows/year.** 2001 = 4,656 (partial, archive starts
2001-06); 2002 = 8,758; 2003 = 8,726; 2004 = 8,782; 2005 = 8,756; 2006 =
8,759; 2007 = 8,759; 2008 = 8,783; 2009–2011 = 8,760; 2012 = 8,784 (leap);
2013–2015 = 8,760; 2016 = 8,783; 2017–2019 = 8,760; 2020 = 8,784 (leap);
2021–2023 = 8,760; 2024 = 8,784 (leap); 2025 = 8,760; 2026 = 5,296
(partial, archive current). Mechanically re-derived deficits from expected
(8,760 non-leap / 8,784 leap), excluding the partial 2001/2026 edges:
2002 −2h, 2003 −34h, 2004 −2h, 2005 −4h, 2006 −1h, 2007 −1h, 2008 −1h,
2016 −1h. Not investigated further, flagged here per the plan's
anomaly-noting instruction. `assert_panel_quality`
passed: 42 `dst_transition_hour` rows flagged across 26 distinct years
(budget `2*26=52`), zero duplicate non-DST timestamps, no gap exceeding
tolerance, `panel.shape == (220290, 44)`.

**Panel B (split) — rows/year.** 2005 = 8,036 (partial, window starts
2005-01-31); 2006–2026 checked against Panel A's per-year counts and
confirmed identical (zero absolute difference summed across every year
2006–2026), despite being a separate parse (11 zones, pre-filtered raw
frame) rather than assumed from Panel A. `assert_panel_quality` passed:
34 `dst_transition_hour`
rows flagged across 22 distinct years (budget `2*22=44`), `panel.shape ==
(188648, 46)`.

**Price quality (horse-race window, both panels — RT and DA, all 11 NY
zones).** RT negative_share ranges 0.77%–4.5%–5.1% (north highest in both
panels — 4.55% Panel A, 5.14% Panel B); RT median $29.72–$42.01/MWh, RT p99
$203.80–$426.47/MWh (longil highest in both). DA negative_share is much
smaller, ≤0.09% in every zone, several zones exactly 0.0% in the
horse-race window; DA median $31.57–$47.84/MWh, DA p99 $129.08–$221.23/MWh.
Full per-zone tables (11 RT + 11 DA rows each) written to
`outputs/nyiso_diagnostic_{merged,split}/price_quality.csv`.

**Level-vs-volatility horse race — summary.** Full zone x price-column
tables (no time controls; standardized OLS; same descriptive-only caveat
as ERCOT/CAISO/IESO) written to
`outputs/nyiso_diagnostic_{merged,split}/fig3_level_vs_volatility_{max,overlap}.csv`.
Win counts (level beats |gradient| beta):
- Panel A, max window (2001-06 → present): level wins in **220 of 220**
  cells (100%).
- Panel A, overlap window (2023-01 → 2025-05 excl.): level wins in
  **213 of 220** cells (96.8%); all 7 non-wins are the `north` zone.
- Panel B, max window (2005-01-31 → present): level wins in **242 of 242**
  cells (100%).
- Panel B, overlap window: level wins in **235 of 242** cells (97.1%);
  all 7 non-wins are again the `north` zone (same 7 price columns as
  Panel A's non-wins).

No substantive interpretation attempted here per this task's scope —
numbers and anomalies only; conclusions are a later step with a human.

**Memo cross-check.** `docs/nyiso-data-availability-research.md` §6 states
"Footprint: stable since 1999 — no joins, no boundary changes, uniquely
among the six markets researched." That claim is the apparent source of
the plan's now-corrected Task 4 comment and is itself empirically false
for load (the 2005-01-31 N.Y.C./LONGIL split documented above). The memo
itself was left unedited — out of this task's scope — but is flagged here
for whoever next touches it.

**NYISO memo §6 caveats (apply to both panels, no time controls in
either):** Zone J (nyc/nyc_longil) weather dominance can swamp zone-level
variance; the DC/crypto question lives upstate (C/D zones). BTM solar is
growing statewide, strongest in Long Island/Hudson Valley. ICAP tag/SCR
peak-response programs give large consumers a peak-shaving incentive.
The 2022 PoW crypto moratorium is a policy break inside the load class of
interest — any upstate trend crossing 2022 carries it.

Committed: `src/surg/preprocessing/nyiso_features.py`,
`tests/test_nyiso_features.py`, `scripts/nyiso_diagnostic.py`, this entry.

## 2026-08-09 — CAISO Stage-1: OASIS `PRC_LMP` retention window falsifies the project's own memo; two-node scope; two-panel production run

**⚠️ Second research-memo claim falsified by real data in this project.**
The first was the NYISO §6 "footprint stable since 1999" claim corrected in
the entry directly above (false: the 2005-01-31 N.Y.C./LONGIL split). This
entry documents the second: `docs/caiso-data-availability-research.md`
(referenced by name in the Phase-1 memo set) claimed roughly 2010-era price
depth for CAISO OASIS. **That claim is false for `PRC_LMP` (the DAM LMP
endpoint this diagnostic uses).** It appears to have verified the *load*
endpoint (`SLD_FCST`), which genuinely does span 2009-2026 (227/227 load
chunks complete, confirmed below), and conflated that with the price
endpoint, which does not. **Recommendation: verify the remaining ISO
memos' depth and footprint claims against real downloaded files before
relying on them for Plan B (MISO, ISONE, SPP) — two claims have now failed
empirical checks out of two checked closely.**

**The discovery, empirically verified.** `PRC_LMP` DAM v12 has a ~3-year
rolling retention window. Of 637 price zips fetched across the three DLAP
nodes that got fetched before the run was stopped (PGAE, SCE, SDGE — VEA
and the three `TH_*` trading hubs were never fetched at all), 549 (86%;
82% for SCE specifically, 183 of 224) are ~649-byte zips that are valid
archives (start with `PK`) but contain a single **XML** file
(`..._PRC_LMP_DAM_..._v12.xml`) holding only an OASIS "no data" disclaimer,
not a CSV. Real price data begins **2023-04-12** for every node checked.
Per-node real-data chunk counts: PGAE 43/226, SCE 41/224, SDGE 4/187. The
download stalls that plagued the original fetch clustered in the oldest
retained window (2023-05-10 to 2023-08-30) — consistent with that being
cold storage server-side, not a client-side issue. Load is unaffected:
all 227 load zips are 100% CSV, no XML disclaimers, genuine 2009-2026
depth.

**`read_zips` fix (Task 1).** The function did `pd.read_csv` on every
member of every zip, so it crashed or silently ingested XML bytes as a
malformed one-column CSV on the 549 disclaimer archives. Fixed to read
only members ending in `.csv`; an archive with no CSV member (a pure XML
disclaimer) is skipped entirely rather than read. The "no zips found"
`RuntimeError` behavior is unchanged. `scripts/nyiso_diagnostic.py`'s
`read_family` has the structurally identical defect (reads every zip
member regardless of extension) — checked all 928 NYISO zips (`palIntegrated`,
`damlbmp_zone`, `realtime_zone`): 100% CSV members, zero non-CSV archives,
so the bug is latent there, not live. Left unchanged per scope (NYISO's
run already succeeded and is not being re-run). The IESO reader
(`scripts/ieso_diagnostic.py`'s `read_family`) reads raw `.csv` files
directly off disk, never unzips anything, so this bug class does not
apply to it.

**Two-node scope decision (Task 2, human decision).** The price side is
restricted to **PGAE and SCE only** via a new `ANALYZED_NODES` module
constant in `scripts/caiso_diagnostic.py`. SDGE has only 4 chunks (~1
month) of real data within the retention window and would produce a
ragged series; the fetch was stopped deliberately rather than spend
another 1-2 hours completing it. VEA and the three `TH_*` hubs were never
fetched. `NODE_MAP` in `src/surg/preprocessing/caiso_features.py` is
**unchanged** — it stays the 7-node allowlist of recognized nodes, not a
scope filter, so a future fetch of the remaining nodes would still parse
correctly.

**Two unplanned driver-level fixes found while running Panel B, both
confined to `scripts/caiso_diagnostic.py` (not the shared `stage1.py`
core, not `caiso_features.py`).** Panel B had never been run against real
data before this entry (`dbb3d66`, "code only, NOT run").
1. `MODERN_START` was `2018-03-21` (mwd's first-appearance date), but
   first-appearance is not the same as complete coverage. `vea` has a
   genuine single-hour gap in the raw OASIS archive at **2018-10-31
   14:00 PPT** — confirmed present in neither of the two adjacent chunk
   files (not a chunking artifact; it is absent from the source). That
   gap is later than `mwd`'s own last gap (2018-03-29 13:00) and tripped
   `assert_panel_quality`'s deliberate "do not interpolate, investigate"
   guard. Scanned all 6 zones' full NaN history: the latest NaN of any
   zone is `vea`'s 2018-10-31 14:00; zero NaNs for any zone from
   **2018-11-01** onward. `MODERN_START` moved to `2018-11-01` (cost:
   ~1 month off a ~7.8-year panel; 2018 was already a partial year).
2. The `bad_dtype` check (`dtype.kind != "f"`) then raised on **all six**
   Panel B zones. Root cause: raw `MW` is `int64` in the OASIS CSVs, and
   `pivot_table`/`unstack` only upcasts a column to `float64` when the
   pivot block it shares has missing cells to fill. Panel A's full
   2009-2026 pivot upcasts every zone (even NaN-free ones) because
   `vea`/`mwd`'s historical gaps live in the same shared block; Panel B's
   now-clean, fully-rectangular 2018-11-01-onward window has no missing
   cells anywhere, so pandas correctly keeps it `int64`. Non-float was
   never a valid proxy for schema drift here. Fixed to accept `kind in
   "if"` (int or float), rejecting only genuinely non-numeric dtypes
   (e.g. `object`, from a stray string) — the actual drift signal the
   check intended to catch.

**Tests.** No new tests: `read_zips`/`ANALYZED_NODES`/`MODERN_START` live
in `scripts/caiso_diagnostic.py`, a driver script, not a `src/` module —
matches the precedent set by the NYISO and IESO driver commits (both
script-only, zero new tests; NYISO's 5 new tests went into the separate
`src/` module commit `52d941e`). Full suite: **474 passed, 5 skipped**,
unchanged from baseline.

**Production run.**

Panel A (full depth, 4 zones — `caiso_total`, `pge`, `sce`, `sdge` — from
2009-04-01): `panel.shape == (152135, 14)`, `assert_panel_quality` passed.
Rows/year: 2009 = 6,608 (partial, archive starts 2009-04-01) through 2025
= 8,760, 2026 = 5,272 (partial, current). No anomalies beyond the expected
partial edge years.

Panel B (modern, 6 zones — adds `vea`, `mwd` — from 2018-11-01):
`panel.shape == (68104, 16)`, `assert_panel_quality` passed. Rows/year:
2018 = 1,465 (partial, window starts 2018-11-01) through 2025 = 8,760,
2026 = 5,272 (partial).

**Price quality (horse-race window, both panels — identical, because the
retention window binds regardless of the load window's start date):**

```
    price_series     n  negative_share   median        p99
 da_lmp_dlap_sce 26776        0.111817 37.13587 107.598675
da_lmp_dlap_pgae 28120        0.028343 40.30052 113.626843
```

SCE's 11.2% negative-price share is notably higher than PGAE's 2.8%; not
investigated further here. Both panels' `data_quality_report` windows
start well before 2023-04-12 (2009-04-01 for Panel A, 2018-11-01 for
Panel B), so `n ≈ 27-28k` against panel sizes of 152,135 and 68,104 rows
*is the retention window visibly showing up in the output* — prices exist
for about 18% of Panel A's rows and about 41% of Panel B's, all
concentrated in the last ~2.3 years. **No horse-race cell was dropped**:
`min_rows=1000` never bound — every cell had n between 15,623 and 28,120,
one to two orders of magnitude above the floor.

**Level vs volatility, Panel A (full depth), max window** (2009-04-01 →
present):

```
       zone     price_series  beta_level  beta_volatility       r2     n  level_wins
caiso_total da_lmp_dlap_pgae    0.339523         0.012682 0.117877 28120        True
caiso_total  da_lmp_dlap_sce    0.301722         0.052977 0.102677 26776        True
        pge da_lmp_dlap_pgae    0.507948        -0.075814 0.242599 28120        True
        pge  da_lmp_dlap_sce    0.487939        -0.074476 0.224129 26776        True
        sce da_lmp_dlap_pgae    0.185908        -0.067036 0.032409 28120        True
        sce  da_lmp_dlap_sce    0.141697        -0.067812 0.019649 26776        True
       sdge da_lmp_dlap_pgae    0.428275        -0.131178 0.189686 28120        True
       sdge  da_lmp_dlap_sce    0.497410        -0.183260 0.262629 26776        True
level wins in 8 of 8 cells
```

**Panel A, overlap window** (2023-01-01 → 2025-05-01 exclusive):

```
       zone     price_series  beta_level  beta_volatility       r2     n  level_wins
caiso_total da_lmp_dlap_pgae    0.404146        -0.012137 0.160193 16967        True
caiso_total  da_lmp_dlap_sce    0.372796         0.037084 0.149402 15623        True
        pge da_lmp_dlap_pgae    0.516257        -0.074471 0.249920 16967        True
        pge  da_lmp_dlap_sce    0.507637        -0.080400 0.241403 15623        True
        sce da_lmp_dlap_pgae    0.263629        -0.027197 0.065982 16967        True
        sce  da_lmp_dlap_sce    0.223107        -0.016549 0.047941 15623        True
       sdge da_lmp_dlap_pgae    0.475935        -0.065714 0.228715 16967        True
       sdge  da_lmp_dlap_sce    0.554181        -0.126030 0.317836 15623        True
level wins in 8 of 8 cells
```

**Level vs volatility, Panel B (modern), max window** (2018-11-01 →
present):

```
       zone     price_series  beta_level  beta_volatility       r2     n  level_wins
caiso_total da_lmp_dlap_pgae    0.339523         0.012682 0.117877 28120        True
caiso_total  da_lmp_dlap_sce    0.301722         0.052977 0.102677 26776        True
        pge da_lmp_dlap_pgae    0.507948        -0.075814 0.242599 28120        True
        pge  da_lmp_dlap_sce    0.487939        -0.074476 0.224129 26776        True
        sce da_lmp_dlap_pgae    0.185908        -0.067036 0.032409 28120        True
        sce  da_lmp_dlap_sce    0.141697        -0.067812 0.019649 26776        True
       sdge da_lmp_dlap_pgae    0.428275        -0.131178 0.189686 28120        True
       sdge  da_lmp_dlap_sce    0.497410        -0.183260 0.262629 26776        True
        vea da_lmp_dlap_pgae    0.244663        -0.045091 0.052762 28120        True
        vea  da_lmp_dlap_sce    0.253862        -0.064582 0.054590 26776        True
        mwd da_lmp_dlap_pgae   -0.035175        -0.012672 0.001384 28120        True
        mwd  da_lmp_dlap_sce   -0.020184        -0.009964 0.000501 26776        True
level wins in 12 of 12 cells
```

**Panel B, overlap window** (2023-01-01 → 2025-05-01 exclusive):

```
       zone     price_series  beta_level  beta_volatility       r2     n  level_wins
caiso_total da_lmp_dlap_pgae    0.404146        -0.012137 0.160193 16967        True
caiso_total  da_lmp_dlap_sce    0.372796         0.037084 0.149402 15623        True
        pge da_lmp_dlap_pgae    0.516257        -0.074471 0.249920 16967        True
        pge  da_lmp_dlap_sce    0.507637        -0.080400 0.241403 15623        True
        sce da_lmp_dlap_pgae    0.263629        -0.027197 0.065982 16967        True
        sce  da_lmp_dlap_sce    0.223107        -0.016549 0.047941 15623        True
       sdge da_lmp_dlap_pgae    0.475935        -0.065714 0.228715 16967        True
       sdge  da_lmp_dlap_sce    0.554181        -0.126030 0.317836 15623        True
        vea da_lmp_dlap_pgae    0.243444        -0.053748 0.051079 16967        True
        vea  da_lmp_dlap_sce    0.252967        -0.070977 0.053173 15623        True
        mwd da_lmp_dlap_pgae   -0.040904        -0.001816 0.001692 16967        True
        mwd  da_lmp_dlap_sce   -0.015569        -0.029240 0.001192 15623       False
level wins in 11 of 12 cells
```

The one non-win is `mwd` × `da_lmp_dlap_sce` in Panel B's overlap window
(`beta_level = -0.0156`, `beta_volatility = -0.0292`): `mwd` (Metropolitan
Water District) has the smallest R² of any zone in either panel
(0.0005-0.0017), consistent with it being a small, likely
weather/agriculture-driven load pocket rather than one where wholesale
price tracks either load measure well. Not investigated further.

**What these results can and cannot support, given a 2.3-year price
window.** The load-based trend outputs (`fig1_volatility_trend_normalized.png`,
`fig2_level_trend.png`, `trends_by_zone_year.csv`) genuinely span the full
load-archive depth of each panel (2009-2025 for Panel A, 2018-2025 for
Panel B) — that part of the memo's depth claim, for load, holds. But
**every horse-race result (level vs. volatility, both panels, both
windows) is confined to 2023-04-12 onward**, because that is all the price
data that exists, not a windowing choice. CAISO's horse race cannot speak
to whether load level has "always" dominated volatility in the way the
16-year ERCOT and 24-year NYISO panels can; it is a 2.3-year snapshot,
coincident with the overlap window used for the trio comparison in the
entry below. Treat the CAISO price-side numbers as descriptive of the
current regime only.

**BTM-solar caveat, pre-committed framing (stapled to the level/volatility
trends per the 2026-08-09 checkpoint).** Metered load is not consumption:
CAISO's TAC-area load is net of behind-the-meter (BTM) solar, which has
grown enormously in California since 2009 — the well-known
"duck-to-canyon" structural change in the net-load shape is a visibility
artifact of this panel, not a change in underlying demand. The 6-zone
`ZONES` roster is CAISO TAC areas only (WEIM member entities excluded by
construction, per `caiso_features.py`'s `TAC_MAP` filter, memo §4); a
large embedded municipal load such as Santa Clara (Silicon Valley Power,
not a CAISO TAC area) is invisible to this panel entirely. Any load-growth
or volatility reading from these panels inherits both caveats.

**No substantive interpretation attempted beyond what is stated above** —
numbers and anomalies only; conclusions are a later step with a human.

Committed: `scripts/caiso_diagnostic.py`, this entry.

## 2026-08-09 — Cross-ISO Stage-1 trio interim synthesis: NYISO, CAISO, IESO, alongside the earlier DOM/ERCOT results

**What ran.** Three markets against real, fully-fetched archives, each at
both the "max" (full available) and "overlap" (2023-01-01 → 2025-05-01
exclusive, common to all three) windows: NYISO (two zone-convention
panels: merged/10-zone and split/11-zone), CAISO (two roster-growth
panels: full-depth/4-zone and modern/6-zone, this entry's companion
above), IESO (one panel, HOEP era only). Numbers below are recomputed
from each panel's own `trends_by_zone_year.csv` and
`fig3_level_vs_volatility_overlap.csv` with a short throwaway script (not
reproduced here); DOM and ERCOT rows are the already-recorded figures
from the 2026-07-30 and 2026-08-07 entries, included as reference, not
recomputed.

**⚠️ Price-history depth used for the horse race varies by roughly an
order of magnitude across the trio, and that gap is now empirically
grounded, not assumed:** NYISO ≈25 years (2001/2005 → 2026), IESO ≈22
years (2003 → 2025-04, HOEP era), **CAISO ≈2.3 years (2023-04-12 →
present) regardless of which load window is used** — the retention-window
discovery documented above. Load-side depth is not the constraint for any
of the three; the price side is, and CAISO's is dramatically shorter than
the other two.

| market / panel | price depth used | load growth % (earliest→latest full year) | normalized volatility change % | level-wins, overlap window | level-wins, max window | median R², overlap |
|---|---|---|---|---|---|---|
| DOM (5-min, reference) | ~3.4 yr | +28.0% (2023→2026 annual mean) | 0.1850%→0.1596% (falling) | not computed in this OLS framework — see quantile-regression findings instead | — | — |
| ERCOT (hourly, reference) | ~9 yr (2017-2025) | +36.7% | −20.7% | 132/135 (97.8%) | (single window reported) | not recorded (R² range 0.004–0.056) |
| NYISO — merged (10 zone) | ~25 yr | −4.5% (2002→2025) | −12.6% | 213/220 (96.8%) | 220/220 (100%) | 0.175 |
| NYISO — split (11 zone) | ~21 yr | −6.5% (2006→2025) | −8.7% | 235/242 (97.1%) | 242/242 (100%) | 0.163 |
| CAISO — full-depth (4 zone) | ~2.3 yr | +31.4% (2010→2025) | −9.8% | 8/8 (100%) | 8/8 (100%) | 0.194 |
| CAISO — modern (6 zone) | ~2.3 yr | +2.4% (2019→2025) | −3.5% | 11/12 (91.7%) | 12/12 (100%) | 0.108 |
| IESO (Ontario) | ~22 yr (HOEP era) | −8.5% (2004→2024; 17,468→15,986 MW) | −1.1% (flat) | 11/11 (100%) | 11/11 (100%) | 0.119 |

Load growth/normalized-volatility columns use each panel's own full
load-archive depth (system-wide series: summed zone means for NYISO,
`caiso_total` for CAISO, `ontario` for IESO), not the price-truncated
overlap window; level-wins and median R² are always the overlap window,
the one common across every market including DOM/ERCOT.

**Two findings worth flagging for Plan B's capstone framing.**

1. **Normalized volatility falls (or is flat) in every single panel
   examined across the whole project so far — DOM, ERCOT, both NYISO
   panels, both CAISO panels, IESO. Zero exceptions, eight panels.** This
   is the single most consistent result in the project. The plan
   explicitly asked to flag a market with *rising* normalized volatility
   as a capstone-framing risk; none was found. If MISO/ISONE/SPP also
   fall in line, "volatility is not what's growing" becomes a genuinely
   strong, well-replicated cross-market claim.
2. **Load growth diverges sharply by market, and the direction itself is
   informative.** DOM, ERCOT, and both CAISO panels show *rising* system
   load (+2.4% to +36.7%) over their respective full-year windows; NYISO
   (both panels) and IESO show system load *falling* (−4.5% to −8.5%)
   over multi-decade windows. This is not a data defect — it is
   consistent with each market's own memo caveats (NYISO: BTM solar,
   ICAP/SCR peak-shaving; IESO: ICI/Global Adjustment peak-shaving,
   embedded-generation netting) already documented as reasons metered
   load can decouple from underlying consumption. It means "data centers
   are driving load growth" cannot be asserted as a shared, market-wide
   phenomenon from these numbers alone — the sign of the trend itself
   splits the six panels roughly down the middle.
3. **Level beats volatility almost everywhere.** The weakest showing is
   CAISO-modern's overlap window at 11/12 (91.7%); every other
   market/panel/window combination is at or above 96.8%, several at
   100%. This replicates the ERCOT and DOM qualitative finding
   (congestion/price tracks load *level*, not load *ramp rate*) in four
   more independently governed markets.

**What this does NOT support.** No MISO, ISONE, or SPP data has been
touched (Plan B scope, not yet started). No capstone claim is being made
here — three markets is not six, and this synthesis is descriptive
inventory, not a conclusion. Every number above comes from a **Stage-1
descriptive horse race with no time controls**: `beta_level` and
`beta_volatility` are standardized OLS coefficients on load level and
|load gradient| against price, with no hour-of-day, day-of-week, or
seasonal fixed effects — `beta_level` in particular carries shared
diurnal and seasonal structure that a controlled specification (like the
DOM z_slope work) would strip out. Treat "level wins" as "level is a
better *raw* correlate than ramp rate," not as a causal or even a
fully-adjusted descriptive claim. Per-market caveats apply on top of this
by reference to each market's own research memo (NYISO §6, IESO §6,
CAISO memo — noting the CAISO memo's depth claim is now known-wrong per
the entry above) and are not repeated here. No policy or data-center
conclusion is drawn in this entry; that is explicitly a later step with a
human, per the project's standing convention.

Committed: this entry (`docs/decisions.md` only, per the plan's own Task
12 commit step — no `outputs/` files staged, matching the NYISO/IESO
precedent).

---

## 2026-08-10 — Cross-ISO Stage-1 CAPSTONE: eight markets, eleven panels

Plan B (`docs/superpowers/plans/2026-08-10-cross-iso-stage1-plan-b.md`) added
MISO, ISO-NE and SPP to the five markets already run, completing the cross-ISO
Stage-1 sweep. Same descriptive horse race as Plan A: standardized OLS of price
on own-zone load **level** vs own-zone **|load gradient|**, **no time controls**,
run at each market's max window and at the locked common-overlap window
(2023-01-01 → 2025-05-01 excl.).

### The eight-market table

| market / panel | price depth used | load growth % (span) | **annualized %/yr** | normalized volatility change % | level-wins, overlap | level-wins, max | median R², overlap |
|---|---|---|---|---|---|---|---|
| DOM (5-min, reference) | ~3.4 yr | +28.0% (2023→2026, 3 yr) | **+8.58** | 0.1850%→0.1596% (falling) | see quantile-regression findings | — | — |
| ERCOT (hourly, reference) | ~9 yr (2017-2025) | +36.7% (2017→2025, 8 yr) | **+3.99** | −20.7% | 132/135 (97.8%) | (single window) | R² 0.004–0.056 |
| NYISO — merged (10 zone) | ~25 yr | −4.5% (2002→2025, 23 yr) | **−0.20** | −12.6% | 213/220 (96.8%) | 220/220 (100%) | 0.175 |
| NYISO — split (11 zone) | ~21 yr | −6.5% (2006→2025, 19 yr) | **−0.35** | −8.7% | 235/242 (97.1%) | 242/242 (100%) | 0.163 |
| CAISO — full-depth (4 zone) | ~2.3 yr | +31.4% (2010→2025, 15 yr) | **+1.84** | −9.8% | 8/8 (100%) | 8/8 (100%) | 0.194 |
| CAISO — modern (6 zone) | ~2.3 yr | +2.4% (2019→2025, 6 yr) | **+0.40** | −3.5% | 11/12 (91.7%) | 12/12 (100%) | 0.108 |
| IESO (Ontario) | ~22 yr (HOEP era) | −8.5% (2004→2024, 20 yr) | **−0.44** | −1.1% (flat) | 11/11 (100%) | 11/11 (100%) | 0.119 |
| **MISO (6 LRZ groups)** | 2023-01 → 2026-08 | **+3.8%** (2023→2025, **2 yr**) | **+1.88** | **−5.6%** | **36/36 (100%)** | 36/36 (100%) | **0.332** |
| **ISO-NE (8 zones, CONTROL)** | 2016-01 → 2026-06 | **−5.2%** (2016→2025, 9 yr) | **−0.59** | **+9.9%** ⚠️ | **64/64 (100%)** | 64/64 (100%) | **0.274** |
| **SPP (17 zones)** | 2017-01 → 2026-03 | **+13.2%** (2016→2025, 9 yr) | **+1.39** | **−14.2%** | **289/289 (100%)** | 289/289 (100%) | **0.245** |

⚠️ **Read the annualized column, not the total-growth column, for any cross-market
comparison.** The spans differ by an order of magnitude (2 years for MISO, 23 for
NYISO), so the raw totals are not comparable and invert the ranking in at least
one place: MISO's **+3.8%** looks like the weakest growth of the three new
markets next to SPP's **+13.2%**, but MISO is compounding at **1.88%/yr against
SPP's 1.39%/yr** — MISO's load is growing *faster*. This is the same defect class
as the F1 figure correction recorded at `decisions.md` 2026-08-08 (a half-year
compared against a full one, +21.5% → +28.0%); the totals are kept only because
each is the honest figure for its own window.

Annualized figures are compound rates, `(1 + total)^(1/years) − 1`, computed from
the same first/last full-year zone means as the total column.

### Finding 1 — level beats volatility, now essentially without exception

All three new markets return **100% level-wins at both windows**. Across all
eleven panels the range is 91.7%–100%. Whatever explains price levels in these
markets, it tracks how much load there is far better than how fast load is
moving. This is the most robust cross-market regularity in the project.

### Finding 2 — the "normalized volatility always falls" regularity BREAKS, and it breaks in the control market

Plan A recorded normalized volatility falling or flat in **all eight panels,
zero exceptions**. That claim no longer holds. **ISO-NE is the first exception:
+9.9%, with 5 of 8 zones rising** (ct, me, ri, sema, vt; range −9.5% to +57.7%).

The decomposition matters and must not be skipped:

| market | raw \|gradient\| change | mean load change | normalized change |
|---|---|---|---|
| ISO-NE | **+3.7%** (rising in only 3/8 zones) | −5.2% | +9.9% |
| MISO | −2.2% | +3.8% | −5.6% |
| SPP | −4.6% | +13.2% | −14.2% |

**ISO-NE's exception is mostly a denominator effect, not a volatility story.**
Normalization divides by mean load, and ISO-NE's load *fell* 5.2%, so normalized
volatility rises even in zones where raw volatility fell — CT is raw −7.8%, load
−9.6%, normalized +2.1%; SEMA is raw −3.2%, load −3.4%, normalized +0.2%. Only
**VT (raw +38.9%) and ME (raw +18.9%)** show genuinely rising absolute
volatility; both are small, rural, high-renewable-share zones.

The honest statement is therefore: *raw* load volatility is flat-to-falling in
every market measured, including ISO-NE at the system level; the normalized
measure inverts wherever load is shrinking. Any future use of `grad_mean_norm`
as a headline number needs this caveat attached.

### Finding 3 — the control market behaves exactly like the treated markets

ISO-NE was chosen as the **low-data-center control**: the ISO's own May-2026
statement is that New England "has not experienced similar growth so far, and
only a small amount is expected in the coming decade." It nonetheless shows the
level-over-volatility result at **64/64 — the same 100% as SPP and MISO** — and
a *higher* median R² (0.274) than most treated markets.

**This cuts against a data-center-specific reading of the project's premise.**
If the pattern held only where data centers are concentrated, it would be
evidence about data centers. It holds just as strongly where they are absent, so
on this evidence it is a property of how power systems price load, not a
signature of data-center growth. That belongs in the framing of any write-up,
not in a footnote.

### Per-market caveats (these bound the numbers above)

- **MISO's 36/36 is inflated.** MISO publishes no zonal price and its node names
  carry no LRZ code — the probe found no LRZ token in any of 432 `Loadzone`
  names and no utility→LRZ crosswalk in scope. The documented eight-hub
  geographic fallback was used, under which **LRZ3_5 and LRZ4 both map to
  `ILLINOIS.HUB` and are byte-identical series**. Those cells are not
  independent, so the effective cell count is below 36.
- **SPP's zone price is an estimator, not a settlement price** — the unweighted
  mean of nodal LMPs matching the zone prefix (64.5%–75.1% of locations match,
  stable across eras). SPP's west is the most wind-penetrated in North America
  and the negative-price share is large (SECI 17.9%, WR 11.3%, NPPD 8.8%); any
  SPP price statistic is partly a wind story.
- **SPP price starts 2017, load starts 2016.** The 2016 price zip mixes two
  naming families with only 184 of 366 days in the standard one. SPP's panel
  ends 2026-03-23, the last day before the wide→long schema break.
- **ISO-NE 2026 is a half year** (ends 2026-06-30) and is excluded from the
  growth columns, which use 2016→2025.
- Nine SPP rows with missing zone load were **dropped, never interpolated**, and
  are listed by timestamp in the run log.

### What this does NOT support

No causal claim of any kind. No attribution of any price behaviour to data
centers — the control-market result actively argues against that. These are
uncontrolled OLS horse races: `beta_level` absorbs shared diurnal and seasonal
structure that the DOM `z_slope` specification strips out, so "level wins" means
"level is the better single predictor here", not "load level causes price". The
eleven panels are not directly comparable in magnitude — depths, zone
definitions, price products and price-construction methods all differ.

Interpretation with a human is a later step, per standing convention.

Committed: this entry (`docs/decisions.md` only; `outputs/` stays untracked,
matching the NYISO/IESO/CAISO precedent).

## 2026-08-11 — Macro pivot: sub-q2 and sub-q3 shut down; paper framing deferred; exploratory mode

Stated directly by the user in session, 2026-08-11. This entry supersedes
the "Gating order (locked tonight)" subsection of **2026-05-14 —
Post-sub-q1 research agenda + sub-q1 framing clarification (item #6
added)**, and stands down the paper-arc step contemplated in **2026-05-15
(late) — Deliverable structure for sub-q reports** and in the provisional
framing briefs (`docs/plans/2026-05-15-advisor-meeting-framings/`).

### What changed

1. **Sub-q2 (JLARC projection) and sub-q3 (event correlation) are shut
   down.** Both presumed sub-q1 would produce a real positive answer — a
   volatility mechanism to project forward (sub-q2), crazy-LMP events to
   correlate with incidents (sub-q3). Sub-q1 instead resolved to a robust
   null (premise undercut on the extended DOM panel; eight-market Stage-1
   capstone with the near-zero-data-centre control matching treated
   markets; item #6 finding zero qualifying events inside the proposal's
   own filter). With nothing to build on, both downstream questions are
   closed. The 2026-07-21 sub-q3 event-catalog scan stands as a discovery
   record; its application closes with the thread.

2. **Paper framing is deferred.** The provisional #3→#2→#1→#4 arc is
   dormant — the lack of data does not currently give a good, compelling
   direction to write toward. The deliverable-format expectation from
   2026-05-15 (standalone report + graphs + hybrid technical/accessible
   prose in one document) carries forward to whatever deliverable
   eventually emerges.

3. **Operating mode is exploratory.** The project is looking for data,
   policy, or anything else that could yield insight, and digging into
   whatever it finds. Work is organized week-to-week around the standing
   advisor meetings: suggestions land in the "Notes from meeting" section
   of each week's agenda doc, get worked during the week, and the notes
   accumulate in the next week's agenda doc
   (`docs/plans/2026-08-19-advisor-meeting-agenda.md` is current).
   Advisor meetings are weekly working check-ins; no single meeting is a
   gate that other work waits on.

### Working lean (a hypothesis to test, not a finding)

As of today the user leans toward: **modern solutions are effectively
mitigating AI data-centre stresses on the transmission grid** — VRT/FFR
mandates and soft-start (NERC LLTF), headroom/flexibility frameworks
(EPRI), behind-the-meter designs, and dispersal trends (Nvidia/SPAN
XFRA). This echoes the advisor's 2026-08-10 note ("data centers are
effectively mitigating the fluctuation, but baseline energy usage is
still extremely high?") and sits consistently with the timescale framing
in `docs/research-notes/I-advisor-links-2026-08.md` and the UKPN
flatness result in `docs/research-notes/J-ukpn-flatness.md`.

### The binding constraint

The recurring obstacle, named in the 2026-08-10 agenda and confirmed by
CRS R48646, is that facility-level data-centre load data is essentially
unavailable — even to the US government (EIA's 2021 pilot survey drew 9
responses from 50 facilities; its 2024 cryptomining survey was halted by
lawsuit and the collected data destroyed). The main villain of this
project is the lack of data.

### In flight

Two access requests pending; when either lands, dig in:

- **Pecan Street** — University Access signup + licensing question on
  whether the 2 kHz waveform release is included (agenda TODO #7).
- **ENTSO-E** — API token for European grid data (agenda TODO #8;
  Ireland-first hypothesis per the 2026-08-10 meeting notes).

### Revisit when

- A dataset or policy thread yields a compelling direction — then choose
  deliverable and framing fresh (the dormant arc is an input, not a
  default).
- Either pending access request lands with usable data.

## 2026-08-12 — ENTSO-E: Irish data-centre dose vs load shape

Supersedes nothing. Resolves the ENTSO-E half of the "In flight" item in
the 2026-08-11 macro pivot entry above (Pecan Street still pending).
Full write-up: `docs/research-notes/K-ireland-dc-shape.md`.

### Four probe findings that overturned prior desk research

Scope probes (~60 requests) before any implementation falsified four
EU-0/EU-2 desk claims. All four changed the design:

1. **Italy is a real 7-zone panel.** All 7 Italian bidding zones serve
   both 6.1.A load and 12.1.D price, 2015→2026. The control worked: the
   IT national CTA gives load but reason-999s on price, so this is not
   an EIC-role artifact.
2. **Resolution is native and heterogeneous — the "hourly panel" premise
   was wrong.** NL load is PT15M back to 2015; IE is PT30M back to 2015.
   Resolution must be read PER DOCUMENT, never assumed per zone.
3. **⭐ Irish load lives on the CTA EIC, not SEM, and that voids EU-0
   §3's footprint objection.** `IE CTA 10YIE-1001A00010` serves
   2015→2026 unbroken at PT30M and is Republic-only, matching the CSO
   covariate. `IE-SEM BZN` is all-island and runs ~1,015 MW higher
   (= Northern Ireland). EU-0 §3 called the all-island-vs-Republic
   mismatch one of three disqualifying limits on Ireland; that was an
   artifact of picking the SEM code. **Price is the opposite asymmetry:**
   the CTA EIC reason-999s on 12.1.D, so load comes from CTA and price
   from SEM. Carry that asymmetry in any future schema.
4. **A03 sparsity is live and material**, not theoretical. Naive
   one-row-per-`Point` parsing makes flat stretches vanish and reads
   spikier than reality, which would corrupt `mean |Δload|/min`.

### Design: Ireland treated, Netherlands control, both from ENTSO-E

**Why Ireland:** its data-centre exposure is *measured* (CSO PxStat
MEC02, 44 quarters), the first time in this project — every US result
used a geographic proxy. Measured: **DC share 0.0443 (2015Q1) → 0.2365
(2025Q4), ×5.33**; DC consumption ×6.84 while **non-DC consumption was
flat at ×1.02**. Essentially all Irish load growth is data centres.

**Why the Netherlands:** matched on total VRE share. Drawn from ENTSO-E
like Ireland *deliberately* — mixing EirGrid
for the treated unit with ENTSO-E for the control would contaminate a
treated-vs-control difference with a source difference (the Hirth et al.
2018 >10% deviation failure mode). EirGrid and Terna were asked about
and rejected for that reason; EirGrid survives as *validation* only.

### ⚠️ A FIFTH desk claim falsified — the control is low-dose, not flat

The design stated the Dutch DC share was **"flat at ~4.6%"**. **False.**
CBS (Statistics Netherlands) publishes the series and 4.6% is the **2024
endpoint**: 1.48% (2017) → 2.42 → 3.29 → 4.19 → 4.58% (2024, prov.).
**The Dutch share TRIPLED.** Checked only after the analysis had already
been run, which is the process lesson — the design's per-market claims
should be probed before, not after.

This removes the pure-placebo reading and replaces it with a
**dose-response test, which is the stronger argument**. Matched window
2017→2024:

| | Ireland | Netherlands |
|---|---|---|
| DC share | 6.85% → 21.86% | 1.48% → 4.58% |
| dose increment | **+15.01 pp** | **+3.10 pp** |
| dose ratio | ×3.19 | ×3.09 |

Per percentage point of dose, on the dimensionless statistics, the
**Netherlands moved 2.5–3.9× MORE** (`vol_norm` −0.000028 vs −0.000011;
`pt_ratio` −0.0409 vs −0.0145; `night_floor` +0.0190 vs +0.0049). Raw
`mean_abs_grad` is excluded from that comparison — MW/min across systems
of different size is not comparable.

**Both readings are negative.** As a ratio, both shares tripled with the
same response. In percentage points, Ireland took 4.8× the dose and moved
less per unit. **No dose-ordering either way.** This does NOT license
"data centres reduce volatility"; the likeliest reading is that both
systems are being flattened by something else that moved further in NL.

CBS definition (connections where the data centre IS the main activity)
is not identical to CSO's Irish heuristic, so cross-country *levels* are
only roughly comparable; within-country trends are the usable part.

### Headline: a matched null

Irish load shape changed substantially 2015→2025 — and the control
changed identically, at the same hours.

| 2015→2025, hourly | Ireland | Netherlands |
|---|---|---|
| mean load | ×1.298 | ×1.196 |
| raw mean \|Δload\| | ×0.933 | **×0.854** |
| `vol_norm` | ×0.719 | ×0.714 |
| `pt_ratio` | 1.694 → 1.399 | 1.669 → 1.363 |
| `night_floor` | 0.722 → 0.823 | 0.715 → **0.840** |

**The `vol_norm` decline is mostly a denominator effect and it recurs in
the control.** Raw volatility fell 6.7% in Ireland while mean load grew
30%; the Netherlands' raw volatility fell *more* (14.6%). On the raw
numerator the dose correlation is **r = −0.261 (IE) vs −0.268 (NL)** —
no differential at all. The mechanism (day flattens by filling in the
night, largest change at hour 3) is present in both, larger in the
control.

**This is the ISONE denominator artifact a second time, in the opposite
direction** (ISONE shrinking load, Ireland growing). Standing conclusion:
`mean_abs_grad` should be reported beside `vol_norm` everywhere in this
project, not just here.

**Explicitly non-causal.** One treated unit, one control, n=44 quarters,
heuristic covariate, no identification strategy. COVID and the 2022
energy crisis sit inside the window; EV and heat-pump growth confound
`night_floor` in the same direction as data centres. The null is a
*matched* null — shape changed a lot — not an absence of change.

### Seven deviations from the approved implementation plan

Recorded so a future reader diffing plan against code does not conclude
someone went off-script. All are the same character — fail loud or
measure, rather than silently absorb:

1. `expand_curve` allocates with `np.full(n, np.nan)` not `np.empty`, so
   any future hole is visible rather than garbage.
2. `expand_curve` **raises on duplicate positions**. Stable sort made the
   earlier duplicate's fill an empty slice, silently dropping its value
   and pushing `sparsity` above 1.0.
3. `parse_response` **raises on a `<Point>` with no parseable value**
   instead of skipping it. Under A03 a dropped point forward-fills and
   the resulting sparsity is indistinguishable from legitimate
   compression. Also makes empty/self-closing elements raise `ValueError`
   rather than `TypeError`.
4. `to_hourly` reports **`n_obs`**, the native slots behind each hourly
   mean. Measured the risk at 1 incomplete hour in 201,717 — real but
   negligible, and now a number rather than an assumption.
5. `shape_statistics` **masks non-contiguous diffs** and uses
   **complete days only**, and reports `mean_abs_grad` beside
   `vol_norm`. Deviation 5 is the one that changed the conclusion.
6. `build_zone_series` **drops exact-duplicate point rows**. 12.1.D
   returns whole days in the AREA's timezone, so a day straddling a
   calendar-year boundary comes back from both adjacent year requests and
   `load_raw` concatenates two identical copies. Measured on Italian
   price: 622 of 118,263 rows in 311 groups, **all agreeing on value**.
   Dedup keys on the value as well as the position, so an exact re-fetch
   is dropped while a genuine *conflicting* duplicate still reaches
   deviation 2's guard and raises. **Found because deviation 2's guard
   fired on real data** — without it this would have silently produced
   wrong prices. Irish numbers are unchanged by it (load is UTC-aligned;
   only price overlaps).
7. `entsoe_italy_stage1.build_panel` **joins zones on `timestamp_utc`,
   never on `timestamp_local`.** The plan specified the local column, but
   local prevailing time repeats at the October fall-back, so it is not a
   unique key: merging six zones on it cross-joined those hours (2^6 rows
   each) and inflated the panel from 101,802 to 146,836 rows.
   `assert_panel_quality` caught it (45,056 rows flagged against a budget
   of 24) — another true positive for that assertion.

### Measured coverage, not asserted

IE_CTA: **3,774 of 203,604 native slots absent (1.85%) in 661 runs**,
largest 2026-02-05→02-24 (19 days) and 2025-11-10→11-19 (coinciding with
the documented 6.1.A→R3 migration). NL: **0 missing**. The Irish feed
*omits* the DST fall-back hour rather than duplicating it, so
`dst_transition_hour` is 0 for Ireland by construction.
`assert_panel_quality` **fails** on the Irish hourly panel — a true
positive, deliberately not loosened; nothing in the Ireland analysis
depends on it.

### Scope decisions

- **Italy WAS run** (168 zone-years pulled). **ROBUSTNESS CHECK, NOT A
  FINDING.** Level beats |gradient| **36 of 36 cells** in both the max and
  overlap windows — consistent with all 11 prior panels, and it does not
  disturb the Stage-2 gate ruling. Coverage is perfect: 101,802 hourly
  rows per zone, **0 missing**, unlike Ireland's 1.85%.
  **IT_CALABRIA excluded** — split out of IT_SOUTH and only a bidding zone
  from 2021-01-01 (reason 999 for 2015-2019, one stray row in 2020).
  Including it would have forced the inner join down to 2021+, discarding
  six years from the other six zones and putting a composition break
  mid-panel. Normalized volatility 2015→2025 falls in 5 of 6 zones
  (−7.8% to −14.2%) and **RISES in IT_SARDINIA (+4.7%)** — with ISONE's
  +9.9%, more evidence that "normalized volatility falls in every panel"
  is dead. Terna still not cross-checked (Hirth et al. 2018).
- **The unprobed VRE zones (ES/FR/FI/DK1-2/SE1-4) were not pulled** —
  nothing in the executed tasks consumes them. The fetcher is idempotent,
  so pulling them later costs nothing already spent.
- **Rate limit still deliberately unverified.** Confirming it means
  tripping abuse protection on a token ENTSO-E reserves the right to
  revoke.

### Committed

Code and docs only; `data/` and `outputs/` stay untracked, matching the
NYISO/IESO/CAISO precedent.

---

## 2026-08-12 — H_solar tested: the midday flattening is partly a metering
## artifact, and the Dutch control series breaks mid-panel

Supersedes nothing outright, but **materially qualifies the entry of earlier
today** ("2026-08-12 — Irish DC dose vs load shape, with NL control"). That
entry stands as written; this one records what the VRE cut found about the
evidence it rests on. Note: `docs/research-notes/L-solar-metering-artifact.md`.

### Scope executed

Probed all 10 VRE-zone EICs before pulling (the process lesson from this
morning). Pulled 6.1.A load for DE_LU, ES, FR, FI, DK1, DK2, SE1-4 (12 years)
and 14.1.A installed solar capacity for the 7 zones that publish it. New module
`src/surg/analysis/entsoe_seasonal.py` (12 tests), driver
`scripts/entsoe_solar.py`, `capacity` item added to `scripts/entsoe_fetch.py`.

### Decision 1 — the solar dose is A68 installed capacity, never A75 generation

Measured, one June day: Dutch A75 metered solar peaks at **204 MW** against
**27,980 MW** of A68 installed capacity, because Dutch PV is overwhelmingly
distributed and invisible to the TSO. German A75 peaks at 24,393 MW against
77,016 MW installed and plainly does include distributed PV. Confirmed not to
be a psrType filter artifact via an unfiltered 16.1.B&C query.

**ENTSO-E metered solar generation is therefore NOT comparable across
countries.** Using it as the dose would have scored the Netherlands as a
near-zero-solar market and inverted the analysis. A68 matches the national
fleet figure and is the only ENTSO-E series here that includes behind-the-meter.

### Decision 2 — identification is seasonal, not cross-sectional

Solar share and calendar year are near-collinear, so a cross-section on solar
share cannot separate solar from any other decade-long drift. Irradiance varies
within the year; data-centre share does not move between June and December.
The test statistic is the summer-minus-winter midday contrast and its trend.
Confound recorded: space cooling is also seasonal and midday, biasing the test
conservative in Spain and near-harmless in the maritime zones.

### Finding 1 — the NL series steps at 2023-04, midday-concentrated

April-vs-March DiD against the same transition in all other years:
NL April/March mean-load ratio **1.0526 vs a 0.9295 median** (×1.1325 excess,
**+1,548 MW**); April−March **midday** deviation **+1,385 MW vs a −86 MW
median**. Two controls: the step is midday-concentrated, so a flat industrial
recovery from the 2022 gas crisis cannot produce it; and **all 11 other zones
show no such step** (2023 excess 0.94-1.02).

**Consequence: the NL control endpoints in this morning's entry
(`vol_norm ×0.714`, `night_floor 0.715→0.840`, `pt_ratio 1.669→1.363`) are
computed ACROSS a definitional break.** Pre-break Dutch summer midday deviation
runs +1,521 → −1,343 MW (2015→2022), then jumps back to +655 MW in 2023. The
matched-null comparison should be re-run on a break-free 2015→2022 window for
both countries before it is quoted further.

Cause NOT confirmed with the TSO. Shape is consistent with distributed
generation being grossed back into reported load; deliberately not asserted as
a named TenneT methodology change (five desk claims were falsified this
morning for exactly that kind of assertion).

**A superseded number from within this session:** an earlier estimate put the
step at +1,497 MW and "68.7% of NL 2015→2025 load growth". It used a
2022-05→2023-03 base — the gas-crisis trough, every 2022 month running
0.911–0.980 against a 1.0042 panel median — and so conflated the reporting step
with industrial recovery. The April/March DiD supersedes it.

### Finding 2 — Ireland's flattening is summer-specific

Irish mean load grew ×1.298, so flat-load dilution predicts normalized depths
shrink ×0.770. Winter midday depth: predicted −0.0733, observed **−0.0740**
(pure dilution). Summer: predicted −0.1190, observed **−0.0526** — an excess of
**+0.066**. Absolute summer midday deviation falls +435 → +193 MW. Irish series
has **no** definitional break (2023 April/March excess 0.9874).

**Data centres cannot produce a seasonal signature.** A component of the
flattening the K-note measured has a fingerprint data centres cannot leave.
This does NOT show data centres change nothing — that is not tested here.

### Finding 3 — dose-response across the panel, with an honest exception

Spearman ρ(Δdose, Δsignature) = **+0.714**, n=7 zones. Finland is a near-perfect
placebo (dose 0.0003→0.157, signature −0.0293→−0.0291, Δ=+0.0002). **Both
Danish zones move AGAINST the dose** and are reported, not dropped — Denmark is
wind-dominated with heavy electric heating. Reported as a rank correlation over
a table; n=7 does not support standard errors.

### Standing rules added

1. **Report an absolute MW statistic beside every ratio.** Third denominator
   artifact in this project (ISONE shrinking load, Ireland growing load, NL
   redefinition). `midday_dev_mw` is provably immune to flat load additions,
   enforced by test.
2. **Check for a mid-panel definitional break before comparing endpoints.**
   The April/March DiD is the cheap detector.
3. **2026 excluded from all ENTSO-E analysis.** The NL 2026 tail carries days
   averaging a fraction of the system floor (July min 1,272 MW, August 187 MW)
   that hold 24 slots each and pass the completeness gate. `implausible_days()`
   reports them rather than silently dropping them.
4. **DE_LU enters at 2019** — the zone split from DE_AT_LU on 2018-10-01 and the
   footprints differ (Austria). The Calabria precedent, second occurrence.

### Not committed

Nothing pushed. Working tree carries this entry, the L-note, the new module and
tests, and the fetcher/registry changes. Tony has not authorised a commit.

### Correction to the entry immediately above (same session, before commit)

Two claims in the entry above are corrected here rather than edited, because
this file is append-only.

1. **"all 11 other zones show no step" is too strong.** The Netherlands is the
   only zone where BOTH screens fire. On the midday-deviation screen there is a
   second outlier: **DE_LU 2023 = −848 MW against a +300 MW median** —
   comparable in magnitude to the Dutch +1,385 MW and **opposite in sign**,
   with no accompanying level step (April/March ratio 0.9731). Cause
   unexamined. The Dutch break finding is unaffected; the control claim is now
   "only NL fires on both screens", which is what the data supports.

2. **Finding 2 should lead with absolute MW, not the dilution ratio.** The
   ratio version imports an assumption (that added Irish load is flat) from
   another market. The direct statement needs no assumption, because
   `midday_dev_mw` is provably flat-load-invariant: **Irish winter midday
   deviation is +313 → +320 MW, unchanged across eleven years, while summer
   falls +435 → +193 MW (−56%).** No quantity of flat data-centre load can move
   either number. Winter's tight match to the dilution prediction (0.0007) is
   then a consequence of an unchanged numerator over a grown denominator, not a
   coincidence of offsetting trends.

Also worth recording: **Spain moves the H_solar way against its own confound.**
Cooling should push Spanish summer midday up and mask the signature; instead
Spanish summer midday deviation falls +3,196 → +1,228 MW (−62%) against a
winter fall of −38%.

`docs/research-notes/L-solar-metering-artifact.md` carries the corrected
versions and is the authoritative write-up.

---

## 2026-08-12 — K-note re-run on the break-free window: the matched null on
## `vol_norm` does not survive; the denominator finding does

Executes the "open" item from the entry above. `scripts/entsoe_ireland.py` now
reports BOTH windows; the published one still reproduces exactly (Ireland
`vol_norm ×0.719`, NL `×0.714`), so nothing is replaced. Write-up:
`docs/research-notes/L-solar-metering-artifact.md` § 8. A warning banner was
added to the top of the K-note; its body is left unedited.

### The break-free comparison, 2015 → 2022

| | Ireland | Netherlands |
|---|---|---|
| mean load | ×1.189 | ×1.027 |
| raw mean \|Δload\| | ×0.968 | ×0.997 |
| `vol_norm` | **×0.814** | **×0.971** |
| `pt_ratio` | −9.2% | −10.5% |
| `night_floor` | +5.4% | +12.7% |
| `load_factor` | +0.3% | +11.7% |

### Dies

**The headline matched null on `vol_norm`.** ×0.719 vs ×0.714 becomes ×0.814
vs ×0.971. The match existed because the 2023-04 break inflated Dutch load
growth from ×1.027 to ×1.196 — the Dutch denominator was doing the work.
**That number must not be quoted again.**

### Survives, and is cleaner

- **The denominator finding.** Irish raw volatility fell 3.2% while Irish load
  grew 18.9%: 0.968/1.189 = 0.814, so the whole `vol_norm` decline is
  arithmetic. This was the K-note's real point.
- **The raw-numerator null.** Break-free quarterly correlation against the
  Irish dose (n=32): `mean_abs_grad` **r = −0.078 (IE) vs −0.133 (NL)** — both
  ≈0, control MORE negative. Cleaner than the published −0.261 / −0.268.
- **No dose-ordering on `night_floor`/`load_factor`.** Ireland took +10.83 pp
  of dose vs the Netherlands' +2.50 pp (4.3×), yet the control moved 2.3×
  further on `night_floor` and 39× further on `load_factor`.

### Reverses

**`pt_ratio` orders the other way per unit dose**: Ireland −0.011450/pp vs the
Netherlands −0.006203/pp (Ireland 1.85× MORE), where the published window had
the control ahead. On `vol_norm` per pp the two now carry opposite signs.

### Ruling

The K-note conclusion is **weakened but not overturned, and no longer uniform.**
"The control moved as much or more on every statistic" was true only across the
break. The defensible statement is now: **no consistent dose-ordering in either
direction, and no detectable movement in raw volatility in either country.**
That still does not license attributing Irish load-shape change to data
centres, and no longer licenses the "identical control" framing either.

### Not committed

Nothing pushed or committed. Tony has not authorised either.

---

## 2026-08-12 — double-check pass: two defects fixed, one claim weakened

Independent re-derivation of every headline number from raw parquet with plain
pandas, not importing the analysis module. Recorded in
`docs/research-notes/L-solar-metering-artifact.md` § 9.

### Confirmed exactly

Ireland +435→+193 MW summer / +313→+320 MW winter; NL pre-break +1,521→−1,343
MW; NL the only zone of twelve with a 2023 April/March ratio above 1; the § 5
cross-section and ρ = +0.714 (reproduced with `scipy.stats.spearmanr`); the
break-free K-note re-run including r = −0.078 / −0.133.

### Defect 1 — capacity years shifted by one (FIXED)

`load_capacity` took the year from `doc_start`, which for an A68 annual document
is local midnight of 1 January expressed in UTC and therefore falls on 31
December of the PREVIOUS year (Finland 2019 -> 2018-12-31T22:00Z). Every
zone-year was joined to the FOLLOWING year's capacity. Now keyed on the filename
with `doc_end` as an independent witness and a fail-loud mismatch check. Dose
figures in the note are the corrected ones; **ρ = +0.714 is unchanged.**

Caught because the manifest showed Finnish capacity as no_data for 2015-2018
while the cross-section reported Finland starting in 2018 — a contradiction
between two artifacts that only a cross-check surfaces.

### Defect 2 — break detector used a different sample (FIXED)

`april_march_step` did not filter to complete days, so a +1,548 MW step computed
on complete days was quoted beside ratios computed on all hours. Now complete
days throughout: the Dutch figures are **1.0493 / 0.9247 / +1,395 MW / −123 MW**
(excess ×1.1347), superseding the 1.0526 / 0.9295 / +1,385 / −86 in the two
entries above. Conclusion unaffected.

### Weakened — A68 coverage varies 3% to 100% across countries

Against published national installed PV, ~2024: Netherlands ~100%, Denmark
~96%, Germany ~78%, France ~74%, Spain ~60%, **Finland ~3%** (27 MW against a
~1,000 MW national fleet, jumping to 1,512 MW in 2026 — itself a reporting
change). So A68 captures distributed PV in some countries and not others, and
its LEVELS are not cross-country comparable.

**Consequence: Finding 3 is downgraded from "dose-response" to "suggestive".**
ρ = +0.714 stands as computed but rests on a dose of uneven completeness, not
corrected for. Finland's flat signature is a real load-based fact and it remains
the lowest-dose zone under any source, so its placebo role survives — but the
0.005 dose figure does not mean Finland has no solar.

Findings 1 (the Dutch break) and 2 (Ireland's summer-specific flattening) are
**untouched** by all of this: both are computed from load alone and use no dose.

### Standing rule added

**A cross-market "dose" from a platform feed must be validated against national
statistics per country before it is used, not once.** Fourth instance in this
project of a measurement turning out to be about the instrument rather than the
system, after ISONE's denominator, Ireland's denominator and the Dutch
redefinition.

### Not committed

Nothing committed or pushed. Tony has not authorised either.

### Addendum to the double-check entry above — two further corrections

**1. `implausible_days` could not detect the corruption it was written for.**
It tested only each day's MEAN against the median day. The Dutch 2026 tail is
INTRA-day: a few collapsed slots inside days whose means (6,150-7,789 MW) clear
any sane floor, against a 10,320 MW median day minimum. It flagged **zero** days
on all twelve zones. A second test on the day MINIMUM now flags 12 Dutch days
(all 2026), plus isolated single days in ES (2), DK1 (1) and Sweden (13 across
SE1/SE2/SE4) — immaterial against ~120 days per season-year but now visible.
No result ever depended on the guard: 2026 is excluded by year cap. The L-note
had claimed the guard reported these days when it did not; § 6 is corrected.

**2. "ρ = +0.714 unchanged by the capacity-year correction" was being used as
reassurance, and it is not.** With n=7 a Spearman is a rank correlation over
seven pairs; the year correction moved dose VALUES without moving any rank, so
ρ was structurally incapable of registering it. Worse, adjacent ranks are now
separated by less than the known coverage error — Germany and Spain by 0.010 in
Δdose, France and Denmark-East by 0.031, against coverage of 78% and 60%. The
ordering is provisional and both § 5 and § 9 now say so.

Findings 1 (the Dutch break) and 2 (Ireland's summer-specific flattening) remain
untouched — load only, no dose, no dependence on the guard.

### Verification state at end of session

Full suite **560 passed** (548 baseline + 12 new), including `tests/regression/`
which pins production numbers. `ruff` clean on all six touched files. Both
drivers re-run end to end. `data/` intact: 376 ENTSO-E parquets, CSO, UKPN, 27
`outputs/` directories, nothing deleted. `docs/decisions.md` verified
append-only throughout (0 deletions). Nothing committed; nothing pushed; the
three earlier commits remain unpushed.
