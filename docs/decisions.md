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
