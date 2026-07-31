# Plan B — errata from the 2026-07-31 four-agent audit

**Status: Plan B is NOT executable as written.** Apply these before executing
`2026-07-31-surg-recovery-plan-b.md`. Four independent read-only audits
(code-reference, spec-coverage, cold-executor, numbers/research-record) ran
against the live tree; every item below was **independently reproduced** by the
orchestrator before being recorded here. Items the agents raised that did not
survive verification are not listed.

Nothing in the plan's *strategy* changed — the three tracks, the account table,
and corrections C1/C2 hold. What follows is defect repair.

---

## P0 — plan-wide, blocks every command

### E1. Every `python` in the plan is wrong; use `.venv/bin/python`

Verified:

```
bash -c 'command -v python'        -> NO bare python in non-interactive shell
python3 -c "import surg"           -> ModuleNotFoundError: No module named 'surg'
.venv/bin/python -c "import surg"  -> OK
```

Bare `python` is an interactive-shell alias and does not resolve inside
`#!/bin/bash` scripts; ambient `python3` has no `surg` installed. This breaks
every `pytest`, every `python -m surg.*`, every `python -c` snippet, and all
five launches inside `scripts/gridstatus_backfill_launch.sh`.

**Fix:** add to the plan preamble — "every `python`/`python3` in this plan means
`.venv/bin/python`, including inside the launch script." Gate before starting:
`.venv/bin/python -c "import surg; print('ok')"`.

---

## P1 — blockers

### E2. `run_all_5min` has a SECOND blocking gap; C1's "one blocking gap" premise is wrong

`run_5min.py:104-108` passes `cross_pnode_pnodes=`, `plotted_pnodes=` and
`resolution="5-min"` to `run_tail_risk_curves`. The live signature
(`tail_risk_curves.py:419-429`) accepts none of them, and **`resolution` is not
in the recovery chain either** — it exists nowhere in the repo or the archive.

So closing the `gpd.py` `cluster_col` gap does **not** make `surg-run-5min`
runnable. Task 1 Steps 9-11 (unskip `test_run_5min.py`, expect PASS, expect a
green suite) cannot pass until this is also resolved.

**Fix:** add a task between Tasks 2 and 3 that reconciles the
`run_tail_risk_curves` signature against `run_5min.py`'s call site. Decide
deliberately what `resolution` should be named and defaulted (`"hourly"`
default keeps hourly callers unchanged). Move Task 1 Steps 9-12 after it.

### E3. Task 2's source replay does not apply — `applied=1 skipped=1`

The `tail_risk_curves.py` worktree chain branched off a base that mainline has
moved past. Live has `bootstrap_method`, `pnode_labels`, and
`filter_col: str | None` (from item #8/#9 work); chain op0's `old_string` is the
older signature and can never match. The **test** chain applies cleanly, so
Task 2 Step 3 fails with `TypeError` against "Expected: PASS".

Two traps: `replay.py` writes the file even when an op skips (`replay.py:50`,
before `return 1`), so the tree is modified regardless — `git checkout` before
retrying. And hand-merging op0 would narrow `filter_col` from `str | None` to
`str`, **silently regressing the sub-q1 item #9 filter-skip mode**.

**Fix:** this is a plan-author decision, not an executor one. Either drop the
source-file replay and re-specify the two new tests against HEAD's actual
signature, or write the merged signature into the plan verbatim. Add the
stop-on-skip instruction Task 2 currently lacks: *"If any op skips, stop and
report — do not hand-reconcile."*

### E4. The launch script never waits; it reports FAILED within a second

`PID1=$(launch ...)` runs `launch` in a command-substitution **subshell**, so
the background python is a grandchild and `wait` cannot reap it. Reproduced:

```
captured=40885
bash: wait: pid 40885 is not a child of this shell
rc=127
```

All five `wait`s return 127 instantly, `RC=127`, the script touches
`...-FAILED` and exits while five pulls run detached — and because the
enclosing `nohup caffeinate -i bash ...` exits with the script, **`caffeinate`
stops holding the machine awake** during a ~5-hour pull. A cold executor reads
`-FAILED`, relaunches, and races duplicate processes against a 250-request cap.

**Fix:** collect PIDs in the parent shell.

```bash
PIDS=()
launch() {
  local idx="$1" label="$2"; shift 2
  local keyvar="GRIDSTATUS_API_KEY_${idx}"
  GRIDSTATUS_API_KEY="${!keyvar}" .venv/bin/python -m surg.acquisition.gridstatus_pull \
    --start "$START" --end "$END" --data-root "$DATA_ROOT" "$@" \
    > "$LOG_DIR/surg-gridstatus-backfill-account${idx}.log" 2>&1 &
  PIDS+=("$!")
  echo "account${idx} pid=${PIDS[-1]} (${label})"
}
launch 1 LOUDOUN --pnodes 35010365 --skip-load
# ... 2-5 ...
RC=0; for pid in "${PIDS[@]}"; do wait "$pid" || RC=$?; done
```

### E5. The launcher is never run before it carries the full quota budget

`bash -n` checks syntax only — which is exactly why E4 survived into the plan.
Between Task 5 and Task 8's irreversible ~890-request launch the script is
never executed once.

**Fix:** add a Task 5 smoke-run against a 1-day window and `/tmp` data root
(~5 requests, one per account). Require: five `pid=` lines, the script
**blocks**, `rc=0`, and a `-DONE` marker. If it returns in under ~10s, the
launcher is broken.

### E6. Every post-pull path, flag and column in Tasks 9-12 is wrong

| Plan | Reality |
|---|---|
| `--out data/processed` | `--output`, a **file** path; `--start`/`--end` are **required** (`build_5min.py:113-116`) |
| `data/processed/panel_5min.parquet` (5 sites) | `data/interim/analysis_panel_5min.parquet` |
| `--out outputs/fivemin_extended` (Task 10) | `--out-root` (`run_5min.py:116`) |
| `df.dropna(subset=['dom'])` | `dom_load_mw` — `loaders_5min.py:40` renames on load |
| `data/processed/panel_hourly.parquet` (Task 12) | `data/interim/analysis_panel.parquet` (`build.py:136`) |

`data/processed` appears nowhere in `src/`, `tests/`, `scripts/` or `docs/`
outside this plan. Write the real invocations in — every flag is knowable today,
and the plan's "read `main()` first" hedges are the deferred-decision pattern
the writing-plans skill bans.

### E7. The hourly panel is never built, and its per-pnode columns do not exist

Two compounding problems.

**(a) No task builds it.** Task 6 pulls raw hourly data; nothing runs
`build.py`. Tasks 11 Step 2 and 12 Step 2 then read a panel that was never
created.

**(b) Per-pnode columns are not retained.** Verified: `schema.py` contains
**zero** `congestion_price_rt_<pnode_id>` columns — only `_cluster_mean`,
`_cluster_max`, `_ashburn_tx1/tx2`, `_ox`, `_bristers`, `_dom_zonal`.
`build.py:62` collapses per-pnode series into cluster aggregates and discards
them. Task 12 Step 2's snippet raises `KeyError` on every name.

**Danger:** an executor told to "correct the column names" will add per-pnode
columns to `EXPECTED_COLUMNS`, bumping `SCHEMA_VERSION` and invalidating
`tests/regression/hourly_reference/`.

**Fix:** add an hourly-build step to Task 6. Compute both correlations from the
pre-aggregation wide frame (`pivot_lmp_long_to_pnode_columns` before
`build.py:62`), not the persisted panel. State explicitly: **do not add
per-pnode columns to `EXPECTED_COLUMNS`.**

---

## P2 — correctness

### E8. `applied=7` is off by one — the correct count is `applied=8`

Ops 0-7 inclusive is **eight** ops, and the plan's own snippet slices `[:8]`.
The plan's own reasoning proves it: `applied=9` covered ops 0-8. Confirmed by
running the plan's snippet against the live file: `applied=8 skipped=0`.

This matters because the wrong number is paired with a hard *"if any op skips,
stop"* gate — a **correct** replay reads as an anomaly. Fix both occurrences
(C1 and Task 1 Step 2).

### E9. Load requests are 42, not 41

`ceil(1239 / 30) = 42`; the window is 1,239 days (verified). `chunking.py:81`
is a strict ceiling. Quota impact nil, but Task 8 Step 4 states 41 as a
verification target, so a correct run reads as an anomaly — same failure mode
as E8. Also wrong in the spec at `:202` and `:216`.

*(177 LMP requests/pnode is exactly right: 1239/7 = 177.0.)*

### E10. The +0.870 pass/fail target does not name its price component

`decisions.md:4030-4033` states all four numbers with **no variable named**.
`total_lmp_rt_*` columns exist for Ashburn, so guessing wrong returns a
plausible number that gets logged as a restoration failure — this fails
*silently*. The project has been bitten by this exact ambiguity twice before
(congestion vs. total_lmp).

Context points to congestion (the companion "4.71% of hours > $100" uses the
standing congestion threshold), but **pin it before Task 11 runs.** Given E7(b),
also downgrade this row from Pass/fail to Diagnostic unless a reproducible
recipe is supplied.

### E11. The republication discriminator is backwards and misapplied

Plan Task 11 says *"gridstatus warehouses as-reported values, and PJM revises."*
`gridstatus-api-constraints.md:130-133` says the opposite: **our** stored series
is `version_nbr=1` (as-first-reported); **gridstatus** carries the
later-republished value — "gridstatus is the cleaner/newer series."

More materially: 99.07% is **cross-source** agreement on a single 3-day window.
It is not a measure of how much gridstatus's own warehoused history drifts
between two pulls — the quantity Task 11 actually needs, which was never
measured. Delete the mechanism claim; keep the raw-vs-derived discriminator,
which is sound and should carry the weight alone.

### E12. Task 1 Step 7 never removes the mutation probe

Step 7 is titled "Remove the mutation probe" but contains **only a grep and a
pytest run** — no removal instruction. An executor who stops here leaves
`np.unique(drawn)` in the tree, and Step 12's `git add` commits **the
deliberate bug C1 exists to prevent**.

**Fix:** add the explicit deletion, and a hard abort at the top of Step 12:
`grep -n "np.unique(drawn)" src/surg/analysis/gpd.py && { echo "ABORT: probe still in tree"; exit 1; }`

### E13. Task 4's test code is written against functions that do not exist

Actual: `pull_gridstatus(client, *, data_root, window_start, window_end,
pnode_ids=None, skip_load=False)` — `client` positional, window params take
**`datetime`** not ISO strings. There is **no fixture**; `test_gridstatus_pull.py:20`
defines a `FakeClient` **class** instantiated inline with `rows_by_dataset`,
plus `_load_rows()` / `_lmp_rows()` helpers and `WINDOW_START`/`WINDOW_END`
constants. So Step 2's expected `TypeError` is really `NameError`.

*(Task 4's line references — 127, 142, 175, 203 — are correct; only the names are wrong.)*

### E14. Task 7 Step 4 loses `.env`; each Bash call is a fresh shell

Step 2 sources `.env`; Step 4 repeats the `GRIDSTATUS_API_KEY_6` prefix without
re-sourcing. It expands empty, and the only live test of the Task 4 code path
fails for an unrelated reason. Prepend `set -a; source .env; set +a`.

Related: neither step passes `--skip-preflight`, so each adds a `/api_usage`
call on top of its data request, and the pollers add more. Restate Step 5 as
"Expected ≤6 requests; above ~10 means chunking is wrong."

### E15. No retry procedure; the preflight blocks resumption

`check_quota` defaults to `min_remaining_rows=430_000` and runs unless
`--skip-preflight`. A full pnode pull is ~350K rows, so the first launch passes
but **any retry on that account aborts** with ~150K remaining. The pull *is*
resumable (`chunk_exists` skips completed chunks) but the plan never says so.

**Fix:** document the retry — re-run the single account with its original
`--pnodes` plus `--skip-preflight`. State: do **not** lower `min_remaining_rows`
in source, and do not burn account 6 unless that account's 250-request budget is
genuinely exhausted.

### E16. Task 8 Step 1's reset check is unsatisfiable if the gate slipped past midnight

Step 1 demands *every* account show `0/250`, but Task 7 explicitly permits the
gate to run on account 6's August allowance. Restate: period end must be
`2026-09-01T00:00:00Z` on all six; accounts **1-5** must be `0/250`; account 6
may show a few requests and does not block (it is the spare and is not launched).

### E17. Neither the spike-filter nor the hourly-window ruling is implemented

The "Decisions closed" section says to log all three via Task 12 Step 3, but
Step 3 describes only the SKFFSCRK write-up. Meanwhile `decisions.md:4128` still
reads **"Status: OPEN. Recommendation is NOT to filter; the user has not
ruled."** Executing Plan B as written leaves the research record contradicting
the plan. Add both closures to Task 12 Step 3 explicitly.

---

## P3 — minor

- **E18.** Task 1 Step 11's "at least 313 passed" is satisfied by doing nothing
  (current state is exactly `313 passed, 6 skipped`). Use **"315 passed, 4
  skipped"** — `test_run_5min.py` holds 2 tests.
- **E19.** Task 3 Step 7 warns about `test_gridstatus_pull.py:107,131`, but those
  assertions derive from `len(FIVEMIN_PNODE_IDS)` and adapt automatically. The
  real coupling is `tests/preprocessing/test_build_5min.py:28,46,96`, whose
  fixture must now emit the four `*_1356178201` columns.
- **E20.** Task 3 leaves `FIVEMIN_PNODE_IDS` duplicated *and* makes the two
  copies textually divergent (one via `SKFFSCRK_PNODE_ID`, one a bare literal),
  though C2 raised duplication as the hazard.
- **E21.** Task 3 Step 6 extends `EXPECTED_COLUMNS_5MIN` without bumping
  `FIVEMIN_SCHEMA_VERSION` (stamped at `build_5min.py:132`, checked at
  `analysis/panel.py:23`).
- **E22.** Serialization the plan does not state: Tasks 3 and 4 both edit
  `gridstatus_pull.py` and its test; Tasks 7, 11, 12 all append to
  `decisions.md`; Task 2 Step 2 also edits `run_5min.py` (absent from its Files
  list and `git add`); 9 ⟵ {3,8}; 10 ⟵ {1,9}; 11 ⟵ {6-build,9,10}; 12 ⟵ 6-build.
- **E23.** Task 10 Steps 1→2 grep a 9-10h job's log immediately; the guard check
  passes trivially at t=0. Gate Step 2 on completion.
- **E24.** `c4a64e7` (cited in Task 11's preamble) is not a valid object in this
  repo — lost in the deletion. Remove or replace.
- **E25.** `decisions.md:157-167` should be **158-170**; the cited range excludes
  the OX/BRISTERS rows the sentence relies on.
- **E26.** Task 12 Step 4's commit message says "contradiction", which Step 3
  explicitly forbids.
- **E27.** Task 6 Step 4's `--end` is **inclusive** (`pull.py:255`), so it pulls
  one day past the exclusive window bound. Harmless (the builder clips) but the
  adjacent prose reasons the other way.
- **E28.** The gate's cost is stated four different ways (~2, ~2, ~3, 2-3).
- **E29.** The plan's own "not auto-fixing ruff findings" guard refers to a lint
  step that does not exist anywhere in the document.

---

## Verified clean — do not re-audit

All 11 pnode IDs against `decisions.md:160-170` and `targets.py:32-45`; all ten
Task 11 regression targets transcribed exactly, with correct hourly/5-min
assignment; 1,239 days; 1,239 × 288 = 356,832; 350,789 rows; 177 LMP
requests/pnode; every account-table cell inside both caps and matching the spec;
both window date pairs; the 12-figure count (F1-F11 + F4b, no F4c); `replay.py`'s
CLI exactly as the plan describes and Task 1 Step 2's snippet faithfully
mirroring its match/skip semantics; C1's op-8/9/10 reasoning (only the count was
wrong); the gpd and test_gpd chains replaying clean; the SKFFSCRK asymmetry
stated consistently in C2/C3/Tasks 3/9/11/12; the bare `GRIDSTATUS_API_KEY` guard
correctly placed and the module genuinely reading only the unsuffixed name; and
**every line-number citation in the plan** — the part most likely to have rotted
after `rm -rf` plus a partial restore, and it did not.

One research note worth carrying: `decisions.md:4030` itself writes
"SKFFSCRK (**rural**)". The rural framing traces to the original analysis, not to
the July recovery spec — C3's write-up should say so.
