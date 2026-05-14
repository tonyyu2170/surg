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
