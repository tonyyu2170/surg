# SURG project recovery — design

Date: 2026-07-30
Status: design, approved
Scope: restore the project to its 2026-07-30 pre-loss state

## What happened

The working directory `/Users/turdy/docs/NU/Freshman_Year/Summer_2026/SURG/surg`
was deleted with `rm -rf`. A fresh clone now sits at
`.../Summer_2026/surg` (macOS is case-insensitive, so this path collides
with the old `SURG/` parent).

The clone is **not** a stale snapshot. `main` and `origin/main` are
byte-identical at `c6a8a6e` (2026-05-15 18:04). Nothing was pushed after
that date, so approximately ten weeks of git history existed only inside
the deleted directory.

The loss is an engineering loss, not a research loss. Every substantive
finding survives in the memory directory and in the 2026-07-27 /
2026-08-03 advisor agendas and the figure-set design spec.

## What survived, and where

All recovered material is archived at `~/surg-recovery-2026-07-30/`
(232 MB), which is outside any path scheduled for cleanup.

| Artifact | Location | Contents |
|---|---|---|
| Git bundle | `~/surg-deleted-branches-2026-07-30.bundle` | 2 branches, complete history, verified. Fetched into the repo as `recovered/feature/*` |
| Memory | `<archive>/memory/` + this session's memory dir | 28 files, 2026-05-10 → 2026-07-30 |
| Session transcripts | `<archive>/transcripts/` | 36 main + 62 subagent JSONL, 228 MB |
| Extracted files | `<archive>/extracted/` | 24 files reconstructed from `Write` payloads |
| Edit chains | `<archive>/edit-chains/` | 41 replayable `Write`/`Edit` sequences as JSON |
| Run logs | `<archive>/surg-run-logs/` | Backfill launch script, per-account logs, extended-run log |

### The two recovered branches

Both fork from `07798da`, which is in `origin/main`, so they graft
cleanly. Both are dated **2026-05-15** — they are the May generation of
the work, not the July generation.

`recovered/feature/sub-q1-item-8-5min-companion` — 16 commits.
Valuable, data-source-agnostic parts: `bootstrap_strategies.py` (island
cluster bootstrap), `run.py` CLI extension (+241 lines: `--seed`,
`--bootstrap-method`, skip flags), `features.py` generalized to
arbitrary `freq_minutes`, bootstrap/island-id injection into `gpd`,
`gpd_continuous`, `gpd_components`, `year_fe_diagnostic`,
`tail_risk_curves`, and a 344-line hourly-pair-bootstrap equivalence
test. The July work references all of these.

`recovered/feature/sub-q1-item-6-no-filter` — 4 commits. One code
commit: a 21-line `filter_col: str | None` parameter on
`run_tail_risk_curves`. The 2026-07-30 memory records this as *cleaner
than the workaround in `run_5min_nofilter.py`*, so it supersedes that
script. The other three commits add **382 lines of `decisions.md`** —
the sub-q1 item #9 pre-registration and application for the
filter-lifted analysis, which is the decision the 08/03 agenda leads
with.

### Two generations of 5-min code

This distinction drives several decisions below.

- **May generation** (in the bundle): `loaders_5min.py` reads PJM
  `rt_fivemin_hrl_lmps` parquet.
- **July generation** (transcripts only): reads gridstatus chunks with a
  rename map onto PJM panel conventions.

**Every finding in the 08/03 agenda came from the July generation.** The
May preprocessing layer is superseded and will be dropped (decided
2026-07-30).

## Genuinely lost

- **All data.** The ~350,789-row 5-min panel (Feb 2023 – Jun 2026) and
  the hourly panel. Gitignored, therefore not in the bundle.
- **All analysis outputs** — `outputs/fivemin_extended/`,
  `outputs/fivemin_nofilter/`. Roughly 9–10 hours of compute.
- **`.env`** — `PJM_API_KEY` plus four `GRIDSTATUS_API_KEY*` values.
  Retrievable by logging into the accounts.
- **The 6 unpushed 2026-07-30 commits** on `main`. Reconstructible from
  edit chains plus the pasted agendas.
- **`docs/reference/pjm-manuals/`** — 11 MB of PJM manuals (M11 rev137, M12 rev57,
  M03 rev71). Re-downloadable.

## Approach: tiered restore

Match restoration effort to each artifact's forward value.

| Artifact class | Method | Rationale |
|---|---|---|
| Research record (`decisions.md`, `pjm-lmp-formation.md`) | Faithful edit replay | Pre-registration continuity is what makes the work defensible; a paraphrase is the wrong approximation |
| Analysis code | Graft from bundle | Already exists as real commits |
| Acquisition layer | Replay (few edits each) | Cheap; validated against a surviving CLI oracle |
| Figure pipeline | Rebuild, do not restore | The figure spec already supersedes it and mandates a restructure |
| May preprocessing | Drop | Superseded by the July gridstatus generation |
| Data | Re-pull | No alternative |

Rejected alternatives: full archaeological replay of all six lost
commits (highest cost, concentrated on the least valuable artifact);
clean-slate rebuild from specs alone (discards the actual `decisions.md`
prose).

## Phases

Phases 4–6 do not depend on Phase 3 and proceed while data pulls.

### Phase 0 — Preserve (DONE)

Memory copied to two locations; bundle fetched into the repo as
`recovered/*` refs; 24 files extracted; 41 edit chains dumped;
transcripts, bundle and run logs archived.

Verify: `~/surg-recovery-2026-07-30/` exists and is ~232 MB;
`git branch` lists both `recovered/feature/*` refs.

### Phase 1 — Unblock data (user action, then verification)

User logs into 6 gridstatus.io accounts and the PJM API portal and
rebuilds `.env` with 7 keys (`PJM_API_KEY` plus `GRIDSTATUS_API_KEY_1..6`).
Four were lost with `.env`; accounts 5 and 6 are newly provisioned to
carry the fourth pnode and a dedicated load account — see Phase 3.

Then poll `GET /api_usage` per account to determine whether July quota
headroom remains or the pull starts Aug 1 (free tier resets per calendar
month).

Also fix `.env.example`, which documented only `PJM_API_KEY`. That
omission is why losing the other four keys was silent.

**Key naming.** The pre-loss convention was asymmetric: the acquisition
module read the unsuffixed `GRIDSTATUS_API_KEY`, and the launch script
overrode it per-account from `GRIDSTATUS_API_KEY_2/_3/_4`. Account 1 was
therefore whichever key happened to sit in the bare variable. Adopt
symmetric `GRIDSTATUS_API_KEY_1..6` instead, and have the restored
launch script inject account 1 the same way as the others. The module
keeps reading `GRIDSTATUS_API_KEY`; only the script changes.

Verify: all 7 keys present; `GET /api_usage` returns a usage period and
remaining allowance for each of the 6 accounts.

### Phase 2 — Rebuild the acquisition layer

Reconstruct `gridstatus_client.py`, `gridstatus_pull.py`,
`gridstatus_validate.py` from extracted `Write` payloads plus their edit
chains. Restore the 3 corresponding test files.

Oracle for the CLI contract: `~/surg-run-logs/surg-gridstatus-backfill-launch.sh`
uses `--start --end --pnodes --skip-load --data-root`. Constraints are
already documented in `docs/sources/gridstatus-api-constraints.md`, which is in
`origin/main`.

**Do not "fix" the key lookup.** The module must keep reading the single
`GRIDSTATUS_API_KEY`; the per-account override belongs in the launch
script. Making `gridstatus_pull.py` read `GRIDSTATUS_API_KEY_1` directly
would break the multi-account strategy, which depends on one process per
account each seeing a different value in the same variable.

Verify: acquisition tests pass; a dry-run pull against a 1-day window
returns rows matching the documented schema; the module reads only
`GRIDSTATUS_API_KEY`.

### Phase 3 — Re-pull data (long pole, quota-gated)

**5-min, gridstatus.io:**

- `pjm_lmp_real_time_5_min` — nodal LMP. `lmp/energy/congestion/loss` →
  `total_lmp_rt/system_energy_price_rt/congestion_price_rt/marginal_loss_price_rt`.
- `pjm_load` — 5-min per-zone load, `dom` column. Coverage begins
  **2023-02-07**, which is why the panel does not reach the proposal's
  2020 start.

**Four pnodes** (decided 2026-07-30, up from the pre-loss three):

| pnode | id | Role |
|---|---|---|
| `LOUDOUN` | 35010365 | Loudoun cluster, 500 kV EHV |
| `PLEASANT VIEW` | 35010371 | Loudoun cluster, 500 kV EHV |
| `GOOSECRE` | 1356178195 | Loudoun cluster, 500 kV EHV |
| `SKFFSCRK` | 1356178201 | **New** — rural 500 kV control |

SKFFSCRK is added because it is the direct counterpart in the
Ashburn-vs-rural contrast and previously existed only at hourly
resolution, which is why that comparison could not be made at 5-min. The
account capacity to carry it did not exist before; six accounts are now
provisioned.

The other two candidates considered — Ashburn TX1 and a non-DOM control
pnode — were **not** added. The non-DOM control remains deferred, and is
still the item that would settle the 2026 attribution question.

### Quota arithmetic

**Requests, not rows, are the binding constraint** (250/month/account).
Measured from `~/surg-run-logs/surg-gridstatus-backfill-account2.log`:
125 chunk-requests covered `2023-02-07 → 2025-06-24` for one pnode. LMP
is chunked at 7 days (~2,013 rows per pnode-week), load at 30 days
(~8,600 rows).

Extrapolating to the full `2023-02-07 → 2026-06-30` window (1,239 days):
**177 requests and ~356K rows per pnode**; load is 41 requests and ~353K
rows.

**Load cannot share an account with a pnode.** Account 2's backfill
finished at 251K LMP + 249K load = **exactly the 500K cap**. Over the
full window the same pairing would be 356K + 353K = 709K, well over. So
load gets a dedicated account:

| Account | Carries | Requests | Rows |
|---|---|---|---|
| 1 | LOUDOUN | 177 | ~356K |
| 2 | PLEASANT VIEW | 177 | ~356K |
| 3 | GOOSECRE | 177 | ~356K |
| 4 | SKFFSCRK | 177 | ~356K |
| 5 | `pjm_load` only | 41 | ~353K |
| 6 | spare / retry budget | — | — |

Every cell is inside both caps. This is a single-pass full-window pull
and supersedes the pre-loss two-pass structure (accounts 2/3/4 covering
`2023-02-07 → 2025-06-24` with `--skip-load`, account 1 covering the
complement), which existed only because fewer accounts were available.

**Quota resets per calendar month.** Accounts 1–4 were spent on
2026-07-29, so the earliest clean launch is **2026-08-01 00:00 UTC**.
Poll `GET /api_usage` per account before launching rather than assuming
either a full allowance or an exhausted one — accounts 5 and 6 are newly
provisioned and may have July headroom.

**Hourly, PJM Data Miner 2:** the locked 11-pnode set (6 EHV
Loudoun-cluster nodes, both Ashburn 35 kV buses, OX and BRISTERS as
controls, DOM zonal). Required for F7, which cannot be built from the
5-min panel.

Known environment issue: NU DNS NXDOMAINs `api.pjm.com`; the `/etc/hosts`
workaround is recorded in the memory directory.

Verify: 5-min panel row count near 350,789; `pjm_load` `dom` column
present from 2023-02-07; four pnode column groups rather than three.

**The row-count target is unchanged by the fourth pnode.** The panel is
wide — one row per 5-min timestamp, one column group per pnode. 1,239
days × 288 intervals = 356,832 upper bound against 350,789 recorded, the
difference being gaps and DST. SKFFSCRK adds columns, not rows. A row
count that scales toward ~470K would mean the builder emitted long
format and something is wrong.

### Phase 4 — Graft the bundle, selectively

Merge `recovered/feature/sub-q1-item-8-5min-companion` for the analysis
layer, then `recovered/feature/sub-q1-item-6-no-filter` for `filter_col`
and the item #9 record.

Drop, per decision 2026-07-30: `build_5min.py`, `loaders_5min.py`,
`build_5min_lmp_only.py` (superseded by the July generation) and
`spike_exceedance_comparison.py` (Part B was dropped in the July design).

Known conflict: both branches modify `docs/decisions.md`,
`src/surg/analysis/run.py`, and `src/surg/analysis/tail_risk_curves.py`.
Merge in the order above and resolve deliberately.

Verify: test suite passes; `run_tail_risk_curves` accepts
`filter_col=None`.

### Phase 5 — Rebuild the July preprocessing/analysis layer

`build_5min.py`, `loaders_5min.py`, `schema_5min.py`, `run_5min.py` plus
tests, from extracted payloads and edit chains.

Verify: preprocessing tests pass; the panel builder produces the
documented schema against re-pulled data.

### Phase 6 — Restore the research record

Replay the `decisions.md` edit chain (20 edits) to recover the July
entries: workstream C, extended-panel interpretation, load-control
amendment, 2026-escalation investigation.

**Constraint:** `decisions.md` has 20 `Edit` diffs but **no `Write`
baseline**. Replay must run against a base assembled first from
`origin/main` plus the Phase 4 merges. Edits originating in different
worktrees must be applied against the matching base. If a hunk fails to
apply, reconstruct that entry from the memory directory and the pasted
agendas rather than forcing the patch, and mark it as reconstructed.

Also restore `docs/reference/pjm-manuals/pjm-lmp-formation.md` (37 KB + 10 edits), the July
plans and specs, and re-download `docs/reference/pjm-manuals/`.

Note: the pasted figure-set spec is the **post-review** version (13
figures, including the review-decisions section) and supersedes the
9,787-byte extracted copy.

Verify: `decisions.md` contains entries for items #8 and #9 and all four
July topics; every entry is either byte-identical to its replay or
explicitly marked reconstructed.

### Phase 7 — Verify the restoration

Re-run the analysis and check against recorded values. These come from
the memory directory and the agendas, and function as a regression
suite:

The two panels are separate targets and must not be checked against each
other. Every row states its resolution — the same implicitness caused the
figure-label bug fixed in `c4a64e7`.

**5-min panel (gridstatus, 4 pnodes, Feb 2023 – Jun 2026):**

Recorded values below come from the pre-loss **3-pnode** panel. The three
original pnodes must reproduce them exactly; SKFFSCRK is new and has no
recorded baseline, so it is characterised rather than verified.

| Quantity | Expected |
|---|---|
| Panel rows | 350,789 |
| DOM load growth, Feb 2023 → Jun 2026 | +21.5% |
| Ramp p90 | 24.22 → 25.28 MW/min |
| Ramp p90 as % of load, by year | 0.1850% → 0.1596% |
| 2024 τ=0.90 z_slope, pre-registered | +0.0367 [+0.0107, +0.0665] |
| 2024 τ=0.90 z_slope, load-controlled | −0.0266 [−0.0416, −0.0103] |
| P(cong > $100) at 20–22 GW, by year | 1.89 / 5.58 / 5.03 / 37.80% |
| Congestion p95, load decile 1 → 10 | $8.14 → $254.36 |

**Hourly panel (PJM Data Miner 2, 11 pnodes):**

| Quantity | Expected | Status |
|---|---|---|
| Ashburn TX1 p99 vs SKFFSCRK p99 | $611.37 vs $96.13 | Diagnostic, not pass/fail |
| SKFFSCRK–cluster vs Ashburn–cluster corr | +0.870 vs +0.209 | Pass/fail |

**Ashburn TX1 is not in the 5-min pull**, so the Ashburn-vs-SKFFSCRK
comparison cannot be evaluated until the hourly re-pull completes. Its
absence after a gridstatus-only pull is expected, not a restoration
failure. SKFFSCRK itself is now in both panels (added 2026-07-30), which
means the contrast can additionally be characterised at 5-min resolution
once Ashburn is available at that resolution — it is not yet.

The Ashburn rows are diagnostic rather than pass/fail because they carry
an unresolved coverage question (`n=17,448` vs `31,536` for the other
pnodes), flagged in the 2026-07-30 memory as "verify before it ships in
F7". A quantity with an open coverage question is a weak regression
target.

Reproducing these proves the restoration. Divergence localises the gap.

### Phase 8 — Push

Pushing is what makes this loss unrepeatable. Per the standing rule in
the memory directory, every commit and push is a separate explicit ask,
so this is requested on its own rather than bundled into an earlier
phase.

## Constraints carried from the memory directory

- No Claude attribution in commit messages; `.gitignore` covers
  `CLAUDE.md` and `.claude/`.
- Every commit and push requires explicit permission.
- Feature work uses a sibling worktree, fast-forward merge preserving
  commits (never squash), then worktree removal and branch deletion.

## Research questions this recovery does not settle

Carried forward unchanged; they are advisor calls, not recovery work.

- Which QR specification is primary: pre-registered or load-controlled.
- Whether identifying the January 2026 driver belongs in sub-q1.
- Whether to acquire a non-DOM control pnode. Every pnode in both panels
  sits inside DOM, so the system-wide component of the 2026 escalation
  cannot currently be separated from a Dominion-specific one.
- Whether to filter the ~3,193-spike class. Heavily leaning on no. Keep them in.

Standing sub-q2 warning: projecting 2026 exceedance rates forward would
extrapolate an unidentified, possibly transient, possibly system-wide
shift as though it were data-center load growth.

## Immediate next step after recovery

Per the 2026-07-30 memory entry: invoke `superpowers:writing-plans` for
the 13-figure build specified in the figure-set design spec. That design
is done and user-reviewed; it should not be re-brainstormed.
