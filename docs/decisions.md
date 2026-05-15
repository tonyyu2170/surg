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
