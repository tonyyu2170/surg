# SURG Recovery Plan B — Data Re-Pull and Verification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the one blocking code gap left by Plan A, re-pull both lost data panels, and verify the restoration against the recorded regression targets.

**Architecture:** Three tracks run in parallel. The *code* track (Tasks 1–5) closes the `gpd.py` gap and prepares the acquisition layer for a 4-pnode / 6-account pull; it is not quota-gated and runs today. The *hourly* track (Task 6) re-pulls the 11-pnode PJM Data Miner 2 panel and is also unblocked today. The *5-min* track is quota-gated: a near-zero-cost validation gate fires tonight (Task 7), and the full-window pull launches after the gridstatus free-tier quota resets at **2026-08-01T00:00:00Z** (Task 8). Verification (Task 11) requires all three.

**Tech Stack:** Python 3.11, pandas, numpy, scipy, httpx, pytest. gridstatus.io v1 REST API (6 free-tier accounts). PJM Data Miner 2 API.

---

## Status carried in from Plan A

Verified live at the start of this plan, **2026-07-31**:

| Spec phase | State |
|---|---|
| Phase 1 — unblock data | **DONE.** `.env` holds all 7 keys; all 6 gridstatus keys return HTTP 200 and are **6 distinct accounts**. `.env.example` already lists all 7 names. |
| Phase 2 — acquisition layer | **DONE.** `gridstatus_client.py`, `gridstatus_pull.py`, `gridstatus_validate.py` + 3 test files present. |
| Phase 8 — push | **DONE 2026-07-31.** 39 commits pushed; `origin/main` moved `c6a8a6e → 94cc56e`. |
| Phase 3 — re-pull | This plan, Tasks 6–10. |
| Phase 7 — verify | This plan, Task 11. |

**Live quota reading (2026-07-31, `GET /api_usage`):** all accounts Free tier — 250 requests / 500,000 rows per calendar month.

| Account | July requests used | July rows used |
|---|---|---|
| 1 | 138 | 249,847 |
| 2 | 190 | 431,863 |
| 3 | 139 | 250,135 |
| 4 | 169 | 496,133 |
| 5 | **0** | **0** |
| 6 | **0** | **0** |

`current_usage_period_end` is `2026-08-01T00:00:00Z` for every account. **Decision (user, 2026-07-31): spend July headroom on the validation gate only** — roughly 2 requests on account 6. All real pulls wait for the reset.

---

## Three corrections to the recovery spec, established before this plan was written

These are findings from reading the archive and the live tree. They override the spec where they conflict.

### C1 — The `gpd.py` gap is mutation-test scaffolding, not a statistics problem

The 2026-07-30 memory records that replaying `_worktree-surg-gridstatus-5min__src__surg__analysis__gpd.py.json` gave `applied=9 skipped=2`, that both skips landed in the bootstrap cluster-resampling core, and that the restoration was abandoned as too high-variance.

Reading the chain's 11 ops shows a different picture:

- **op8** inserts `drawn = np.unique(drawn)` carrying the literal comment `# INTENTIONAL BUG for regression-test validation`.
- **op9** applies the same mutation inline, against the *clean* two-line block.
- **op10** reverts op9 exactly. (`op9.new_string == op10.old_string` and `op9.old_string == op10.new_string`.)

Ops 8, 9 and 10 are all mutation-test scaffolding for a regression test. The faithful end state is **ops 0–7 applied, ops 8–10 not applied**.

`applied=9 skipped=2` is exactly what this predicts: op8 applied *and injected the self-labeled intentional bug*; op9's `old_string` then no longer matched, so it skipped; op10's `old_string` never came into existence, so it skipped too. The prior session was right to abandon, but for the wrong reason — the hazard was not unreviewed resampling internals, it was that the replay had silently injected a deliberate bug.

**Target for Task 1: `applied=7 skipped=0`.** If any op in 0–7 skips, that is a genuine base mismatch — stop and diagnose rather than hand-reconcile.

### C2 — `FIVEMIN_PNODE_IDS` is both the pull-set and the cluster-set

`src/surg/preprocessing/build_5min.py:48` calls `add_loudoun_cluster_columns(lmp_wide, FIVEMIN_PNODE_IDS)`. Pre-loss this was safe only by coincidence: `FIVEMIN_PNODE_IDS` was exactly the three Loudoun-cluster nodes, so pull-set and cluster-set were the same tuple.

The spec adds SKFFSCRK as a **fourth** pnode. If SKFFSCRK is appended to `FIVEMIN_PNODE_IDS`, the cluster mean/max columns silently absorb it — and every 5-min regression target in Phase 7 (2024 τ=0.90 z_slope, congestion p95 by load decile, P(cong > $100)) is computed on those cluster columns. The run would diverge from the recorded values and the divergence would look like a restoration failure.

The constant is also **duplicated** — defined identically at `gridstatus_pull.py:31` and `schema_5min.py:13`. Task 3 splits pull-set from cluster-set explicitly.

### C3 — SKFFSCRK is geographically rural but electrically coupled; that gap is a result, not a defect

**Resolved by the user, 2026-07-31.** SKFFSCRK is pulled as the fourth 5-min pnode, and the hourly 6-node cluster pooling stays exactly as pre-registered.

The tension that prompted this: the recovery spec calls SKFFSCRK a "rural 500 kV control", while the project's own locked design treats it as a cluster member —

- `docs/decisions.md:157-167` — the locked n=11 table lists SKFFSCRK under **"Primary nodal — transmission"**, with OX and BRISTERS as the **"Control / outside-cluster"** tier.
- `docs/decisions.md:298` — "Pool the 6-pnode Loudoun transmission cluster (LOUDOUN, PLEASANT VIEW, GOOSECRE, BRAMBLET, MOSBY, **SKFFSCRK**) by mean."
- `docs/decisions.md:151` — LOUDOUN, MOSBY, BRAMBLET and SKFFSCRK "all came back within ~$5/MWh mean LMP and ~$3/MWh mean congestion of each other."
- `src/surg/preprocessing/build.py:34` — `LOUDOUN_CLUSTER_IDS` includes `1356178201`.

**Both descriptions are true.** SKFFSCRK sits in a markedly more rural area geographically, yet prices within ~$3/MWh of the urban cluster because it is on the same 500 kV EHV network inside the same congestion pocket. Electrical distance is not geographic distance. That a geographically-rural node tracks the cluster at +0.870 is **evidence for the system-wide character of the 2026 escalation**, not a failure of the control — and it is consistent with the standing finding that the escalation must never be attributed to data centers.

Two consequences carried into the tasks:

1. **The hourly cluster stays 6-node, as pre-registered.** Amending a pre-registered aggregation mid-project carries a research-integrity cost the ~$3/MWh tightness does not justify. Every recorded Phase 7 hourly target therefore remains reproducible.
2. **The +0.870 correlation is still partly self-correlation**, because SKFFSCRK is inside the cluster it is correlated against. This is **disclosed, not corrected**: Task 12 reports the SKFFSCRK-held-out correlation alongside it as a diagnostic.

**Deliberate asymmetry to preserve:** SKFFSCRK is *inside* the 6-node hourly cluster and *outside* the 3-node 5-min cluster-set. This is correct. The 5-min cluster was only ever the three pulled nodes, and SKFFSCRK's role at 5-min resolution is explicitly as the comparison node (correction C2). Do not "fix" this to make the two panels match.

**Priority note (user, 2026-07-31):** hourly findings are lower-priority than the 5-min work. Task 6 still runs in parallel because it is cheap and unblocked, but it should not gate anything on the 5-min track.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/surg/analysis/gpd.py` | GPD fitting, conditional-Z, cluster bootstrap | Modify — replay chain ops 0–7 |
| `tests/analysis/test_gpd.py` | GPD unit tests incl. cluster-bootstrap guard | Modify — replay chain, 3 ops |
| `tests/analysis/test_run_5min.py` | 5-min orchestrator smoke test | Modify — remove module-level skip |
| `src/surg/analysis/tail_risk_curves.py` | Decile tail-risk curves | Modify — replay worktree chain, 2 ops |
| `tests/analysis/test_tail_risk_curves.py` | Tail-risk tests | Modify — replay worktree chain, 2 ops |
| `src/surg/preprocessing/schema_5min.py` | 5-min panel schema + pnode constants | Modify — split pull-set / cluster-set, 4-pnode columns |
| `src/surg/preprocessing/build_5min.py` | 5-min panel builder | Modify — use cluster-set for cluster columns |
| `src/surg/acquisition/gridstatus_pull.py` | gridstatus pull CLI | Modify — add SKFFSCRK, add `--skip-lmp` |
| `tests/acquisition/test_gridstatus_pull.py` | Pull CLI tests | Modify — cover `--skip-lmp` and 4-pnode set |
| `scripts/gridstatus_backfill_launch.sh` | 6-account parallel launch | **Create** — rewrite, now version-controlled |
| `scripts/poll_gridstatus_usage.py` | Per-account quota poll | **Create** |

---

## Task 1: Close the `gpd.py` `cluster_col` gap

This is the blocking gap. `run_5min.py:93` calls `run_gpd(..., cluster_col="night_island_id")` and `cluster_col` exists nowhere in the analysis layer.

**Files:**
- Modify: `src/surg/analysis/gpd.py`
- Modify: `tests/analysis/test_gpd.py`
- Replay tool: `~/surg-recovery-2026-07-30/replay.py`
- Chains: `~/surg-recovery-2026-07-30/edit-chains/_worktree-surg-gridstatus-5min__src__surg__analysis__gpd.py.json` (11 ops), `..._tests__analysis__test_gpd.py.json` (3 ops)

- [ ] **Step 1: Confirm the chain still shows the op 8/9/10 pattern**

```bash
python3 -c "
import json
d=json.load(open('/Users/turdy/surg-recovery-2026-07-30/edit-chains/_worktree-surg-gridstatus-5min__src__surg__analysis__gpd.py.json'))
ops=d['ops']
assert len(ops)==11, f'expected 11 ops, got {len(ops)}'
assert 'INTENTIONAL BUG' in ops[8]['new_string'], 'op8 is not the labeled mutation'
assert ops[9]['new_string']==ops[10]['old_string'], 'op9/op10 are not a revert pair'
assert ops[9]['old_string']==ops[10]['new_string'], 'op9/op10 are not a revert pair'
print('CONFIRMED: ops 8,9,10 are mutation scaffolding; replay ops 0-7 only')
"
```

Expected: `CONFIRMED: ops 8,9,10 are mutation scaffolding; replay ops 0-7 only`

- [ ] **Step 2: Replay ops 0–7 only**

`replay.py` cannot do this on its own. Its interface is positional — `replay.py <chain> <dest> [--from-base]` — with **no op-range selector and no dedup flag**; the dedup rule in the Plan A notes is a manual instruction, not a feature. This chain also has **no `Write` baseline** (all 11 ops are `Edit`), so a bare invocation would exit 2.

Use this snippet instead. It mirrors `replay.py`'s exact match/skip semantics (`count == 0` → skip; `count > 1` without `replace_all` → skip) while restricting to ops 0–7 and deduplicating by `(old_string, new_string)` first:

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
python3 - <<'PY'
import json
from pathlib import Path

CHAIN = Path("/Users/turdy/surg-recovery-2026-07-30/edit-chains/"
             "_worktree-surg-gridstatus-5min__src__surg__analysis__gpd.py.json")
DEST = Path("src/surg/analysis/gpd.py")

ops = json.loads(CHAIN.read_text())["ops"][:8]   # ops 0-7 only; 8-10 are scaffolding

seen, deduped = set(), []
for o in ops:
    if o["op"] != "Edit":
        continue
    key = (o["old_string"], o["new_string"])
    if key in seen:            # hook-rejected duplicate; replaying it double-inserts
        print("  DEDUP: dropping repeated edit")
        continue
    seen.add(key)
    deduped.append(o)

text = DEST.read_text()        # from-base: gpd.py already exists in the tree
applied = skipped = 0
for o in deduped:
    old, new = o["old_string"], o["new_string"]
    count = text.count(old)
    if count == 0:
        print(f"  SKIP (no match): {old[:70]!r}")
        skipped += 1
        continue
    if count > 1 and not o.get("replace_all"):
        print(f"  SKIP (ambiguous, {count} matches): {old[:70]!r}")
        skipped += 1
        continue
    text = text.replace(old, new) if o.get("replace_all") else text.replace(old, new, 1)
    applied += 1

DEST.write_text(text)
print(f"{DEST}: applied={applied} skipped={skipped}")
PY
```

Expected: `applied=7 skipped=0`.

**This is empirically established, not hoped for.** The 2026-07-30 run reported `applied=9 skipped=2` against this same base, which means ops 0 through 8 all matched and applied — op8 applying is precisely what injected the bug. Ops 0–7 are therefore known to apply cleanly here.

**If any op skips, stop.** Given the above, a skip means the base has changed since 2026-07-30 — a real anomaly. Report which op and its `old_string` rather than hand-reconciling.

- [ ] **Step 3: Verify no duplicate definitions were introduced**

```bash
grep -c "def run_gpd" src/surg/analysis/gpd.py
grep -c "def gpd_conditional_on_z" src/surg/analysis/gpd.py
grep -n "INTENTIONAL BUG" src/surg/analysis/gpd.py || echo "GOOD: no intentional-bug line present"
grep -n "cluster_col" src/surg/analysis/gpd.py
```

Expected: each `def` count is exactly `1`; `GOOD: no intentional-bug line present`; `cluster_col` now appears in `gpd.py`.

- [ ] **Step 4: Replay the companion test chain**

All 3 ops are `Edit`, so `--from-base` is required (positional args, no `--dedup` flag — dedup is manual):

```bash
python3 /Users/turdy/surg-recovery-2026-07-30/replay.py \
  /Users/turdy/surg-recovery-2026-07-30/edit-chains/_worktree-surg-gridstatus-5min__tests__analysis__test_gpd.py.json \
  tests/analysis/test_gpd.py --from-base
```

Expected: `applied=3 skipped=0`. Then confirm no edit was double-inserted:

```bash
grep -c "def test_gpd_conditional_on_z_cluster_bootstrap_duplicates_rows" tests/analysis/test_gpd.py
```

Expected: `1`.

- [ ] **Step 5: Run the GPD tests**

```bash
python -m pytest tests/analysis/test_gpd.py -v
```

Expected: PASS.

- [ ] **Step 6: Prove the restoration with the author's own mutation test**

A green suite proves little here. The chain restored in Step 4 contains the exact test the original author wrote to catch this mutation — `test_gpd_conditional_on_z_cluster_bootstrap_duplicates_rows`, whose docstring reads: *"Locks in the correct cluster-bootstrap mechanic: a cluster id drawn twice by rng.choice must contribute its exceedance rows twice to the resampled arrays (not deduplicated)."* That is precisely what `np.unique(drawn)` breaks.

Re-inject op8's mutation. Insert this line immediately after the `drawn = rng.choice(unique_clusters, size=len(unique_clusters), replace=True)` line in `gpd.py`:

```python
            drawn = np.unique(drawn)  # TEMPORARY mutation probe — remove after this step
```

Then run that test specifically:

```bash
python -m pytest tests/analysis/test_gpd.py::test_gpd_conditional_on_z_cluster_bootstrap_duplicates_rows -v
```

Expected: **FAIL.** If it passes, the restoration is not faithful — the test is not reaching the resampling path. Report that rather than proceeding.

- [ ] **Step 7: Remove the mutation probe and confirm green again**

```bash
grep -n "TEMPORARY mutation probe" src/surg/analysis/gpd.py && echo "PROBE STILL PRESENT — remove it" || echo "probe removed"
python -m pytest tests/analysis/test_gpd.py -v
```

Expected: `probe removed`; tests PASS.

- [ ] **Step 8: Verify the `< 10` cluster guard will not fire in production**

Chain op7 adds a guard that **raises** when there are fewer than 10 unique clusters among exceedances:

```python
    if unique_clusters is not None and len(unique_clusters) < 10:
        raise ValueError(
            f"too few unique clusters ({len(unique_clusters)}) among exceedances "
            ...
        )
```

`run_5min.py:93` passes `cluster_col="night_island_id"` on the in-filter subset only. Confirm the column is actually produced upstream:

```bash
grep -n "night_island_id" src/surg/preprocessing/*.py src/surg/analysis/*.py
```

Expected: the column is emitted by the preprocessing layer. Record the finding; the live count check happens in Task 11 Step 4, once real data exists.

- [ ] **Step 9: Remove the module-level skip from `test_run_5min.py`**

Delete this block from `tests/analysis/test_run_5min.py:11-17`:

```python
pytest.skip(
    "run_all_5min requires gpd.run_gpd(cluster_col=...), whose worktree edit "
    "chain (_worktree-surg-gridstatus-5min__src__surg__analysis__gpd.py.json, "
    "11 edits) is unassigned in recovery plan A. Unskip after that chain is "
    "restored.",
    allow_module_level=True,
)
```

If `pytest` becomes an unused import after the deletion, remove that import too.

- [ ] **Step 10: Run the previously-skipped smoke test**

```bash
python -m pytest tests/analysis/test_run_5min.py -v
```

Expected: PASS (it was written against a synthetic panel, so it needs no real data).

- [ ] **Step 11: Run the full suite**

```bash
python -m pytest -q 2>&1 | tail -5
```

Expected: at least 313 passed (the Plan A baseline), now with `test_run_5min.py` live rather than skipped.

- [ ] **Step 12: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py tests/analysis/test_run_5min.py
git commit -m "fix(analysis): restore gpd cluster_col chain, excluding mutation scaffolding

Replays ops 0-7 of the worktree gpd.py edit chain. Ops 8-10 are mutation-test
scaffolding: op8 carries a literal 'INTENTIONAL BUG for regression-test
validation' comment, and op9/op10 are an exact revert pair. The prior
applied=9 skipped=2 replay had injected that deliberate bug.

Unskips tests/analysis/test_run_5min.py, which was gated on this chain."
```

---

## Task 2: Restore the `tail_risk_curves` worktree chains

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py`
- Modify: `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Replay both worktree chains**

Both chains are all-`Edit` with no `Write` baseline, so `--from-base` is required. Arguments are positional; there is no `--dedup` flag.

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
R=/Users/turdy/surg-recovery-2026-07-30
python3 $R/replay.py \
  $R/edit-chains/_worktree-surg-gridstatus-5min__src__surg__analysis__tail_risk_curves.py.json \
  src/surg/analysis/tail_risk_curves.py --from-base
python3 $R/replay.py \
  $R/edit-chains/_worktree-surg-gridstatus-5min__tests__analysis__test_tail_risk_curves.py.json \
  tests/analysis/test_tail_risk_curves.py --from-base
```

Expected: `applied=2 skipped=0` for each.

At 2 ops each these chains carry no repeated `(old_string, new_string)` pairs, so no manual dedup is needed — but confirm nothing double-inserted before committing:

```bash
git diff --stat src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
```

- [ ] **Step 2: Check for the known hardcoded-label bug**

A 2026-07-30 observation recorded a hardcoded `"hourly"` label in the `tail_risk_curves` plot title, on a function shared by both the hourly and 5-min entrypoints.

```bash
grep -n "hourly" src/surg/analysis/tail_risk_curves.py
```

If a hardcoded `"hourly"` appears in a plot title or axis label, make it a parameter with `"hourly"` as the default so existing callers are unchanged, and pass `"5-min"` from `run_5min.py`. If it does not appear, the replayed chain already fixed it — record which.

- [ ] **Step 3: Run the tests**

```bash
python -m pytest tests/analysis/test_tail_risk_curves.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "fix(analysis): restore tail_risk_curves worktree edit chains"
```

---

## Task 3: Split the 5-min pull-set from the cluster-set

Prevents correction **C2**: adding SKFFSCRK to the pull must not pull it into the Loudoun cluster average.

**Files:**
- Modify: `src/surg/preprocessing/schema_5min.py:13`
- Modify: `src/surg/preprocessing/build_5min.py:29,48`
- Modify: `src/surg/acquisition/gridstatus_pull.py:31`
- Modify: `tests/preprocessing/test_build_5min.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/preprocessing/test_build_5min.py`:

```python
def test_cluster_columns_exclude_skffscrk():
    """SKFFSCRK is pulled as a comparison node; it must not enter the cluster average.

    Regression guard for the pre-loss coincidence where FIVEMIN_PNODE_IDS was
    simultaneously the pull-set and the cluster-set.
    """
    from surg.preprocessing.schema_5min import (
        FIVEMIN_PNODE_IDS, FIVEMIN_CLUSTER_IDS, SKFFSCRK_PNODE_ID,
    )
    assert SKFFSCRK_PNODE_ID in FIVEMIN_PNODE_IDS
    assert SKFFSCRK_PNODE_ID not in FIVEMIN_CLUSTER_IDS
    assert len(FIVEMIN_PNODE_IDS) == 4
    assert len(FIVEMIN_CLUSTER_IDS) == 3
    assert set(FIVEMIN_CLUSTER_IDS).issubset(set(FIVEMIN_PNODE_IDS))
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
python -m pytest tests/preprocessing/test_build_5min.py::test_cluster_columns_exclude_skffscrk -v
```

Expected: FAIL with `ImportError: cannot import name 'FIVEMIN_CLUSTER_IDS'`.

- [ ] **Step 3: Define the two constants**

Replace `src/surg/preprocessing/schema_5min.py:13` with:

```python
SKFFSCRK_PNODE_ID: int = 1356178201

# Nodes pulled at 5-min resolution. SKFFSCRK was added 2026-07-30 as a
# comparison node; see docs/specs/2026-07-30-surg-recovery-design.md.
FIVEMIN_PNODE_IDS: tuple[int, ...] = (35010365, 35010371, 1356178195, SKFFSCRK_PNODE_ID)

# Nodes averaged into the Loudoun cluster columns. Deliberately NOT the same
# tuple as FIVEMIN_PNODE_IDS: pooling a comparison node into the cluster it is
# compared against would contaminate every cluster-based regression target.
FIVEMIN_CLUSTER_IDS: tuple[int, ...] = (35010365, 35010371, 1356178195)
```

- [ ] **Step 4: Point the builder at the cluster-set**

In `src/surg/preprocessing/build_5min.py`, change the import at line 29 from `FIVEMIN_PNODE_IDS` to `FIVEMIN_CLUSTER_IDS`, and change line 48 to:

```python
    lmp_wide = add_loudoun_cluster_columns(lmp_wide, FIVEMIN_CLUSTER_IDS)
```

If `FIVEMIN_PNODE_IDS` is still needed elsewhere in that file, import both rather than replacing the import.

- [ ] **Step 5: Update the acquisition-side constant**

In `src/surg/acquisition/gridstatus_pull.py:31`:

```python
FIVEMIN_PNODE_IDS: tuple[int, ...] = (35010365, 35010371, 1356178195, 1356178201)
```

- [ ] **Step 6: Regenerate `EXPECTED_COLUMNS_5MIN` for four pnodes**

`EXPECTED_COLUMNS_5MIN` in `schema_5min.py` enumerates per-pnode columns. Extend it so each of the four price components exists for pnode `1356178201`, matching the naming already used for the other three (e.g. `congestion_price_rt_1356178201`). Read the surrounding block and follow its exact ordering convention.

- [ ] **Step 7: Run the preprocessing and acquisition tests**

```bash
python -m pytest tests/preprocessing/ tests/acquisition/ -v 2>&1 | tail -20
```

Expected: PASS, including the new test. Tests asserting `len(FIVEMIN_PNODE_IDS)`-derived counts (`test_gridstatus_pull.py:107,131`) will now see 4 — confirm each change is correct rather than adjusting numbers to whatever makes it green.

- [ ] **Step 8: Commit**

```bash
git add src/surg/preprocessing/schema_5min.py src/surg/preprocessing/build_5min.py \
        src/surg/acquisition/gridstatus_pull.py tests/preprocessing/test_build_5min.py \
        tests/acquisition/test_gridstatus_pull.py
git commit -m "feat(preprocessing): add SKFFSCRK as 4th 5-min pnode, split cluster-set from pull-set

FIVEMIN_PNODE_IDS was both the pull-set and the cluster-set, safe only because
they coincided at 3 nodes. Adding SKFFSCRK would have silently pooled a
comparison node into the Loudoun cluster average, contaminating every
cluster-based regression target."
```

---

## Task 4: Add a load-only path to the pull CLI

Spec account 5 carries `pjm_load` and nothing else. `gridstatus_pull.py` has `--skip-load` but no inverse: line 142 reads `for pid in (pnode_ids or FIVEMIN_PNODE_IDS)`, so an empty `--pnodes` falls back to the full set rather than pulling nothing.

**Files:**
- Modify: `src/surg/acquisition/gridstatus_pull.py:127-180`
- Modify: `tests/acquisition/test_gridstatus_pull.py`

- [ ] **Step 1: Write the failing test**

Read the existing fake-client fixture pattern in `tests/acquisition/test_gridstatus_pull.py` first, then add tests matching its actual fixture and entrypoint names. The shape:

```python
def test_skip_lmp_pulls_load_only(tmp_path, fake_client):
    """--skip-lmp must issue zero LMP requests and still pull load."""
    run_pull(
        start="2023-02-07T00:00:00Z",
        end="2023-02-14T00:00:00Z",
        data_root=tmp_path,
        client=fake_client,
        skip_lmp=True,
    )
    lmp_calls = [c for c in fake_client.calls if c["dataset"] == "pjm_lmp_real_time_5_min"]
    load_calls = [c for c in fake_client.calls if c["dataset"] == "pjm_load"]
    assert lmp_calls == []
    assert len(load_calls) > 0


def test_skip_lmp_and_skip_load_together_is_rejected(tmp_path, fake_client):
    """Pulling neither series is a user error, not a silent no-op."""
    with pytest.raises(ValueError, match="nothing to pull"):
        run_pull(
            start="2023-02-07T00:00:00Z",
            end="2023-02-14T00:00:00Z",
            data_root=tmp_path,
            client=fake_client,
            skip_lmp=True,
            skip_load=True,
        )
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
python -m pytest tests/acquisition/test_gridstatus_pull.py::test_skip_lmp_pulls_load_only -v
```

Expected: FAIL with `TypeError: ... unexpected keyword argument 'skip_lmp'`.

- [ ] **Step 3: Add the parameter**

Add `skip_lmp: bool = False` to the pull function signature beside `skip_load` (near line 127). Guard the pnode loop at line 142:

```python
    if skip_lmp and skip_load:
        raise ValueError(
            "skip_lmp and skip_load are both set — nothing to pull"
        )
    if not skip_lmp:
        for pid in (pnode_ids or FIVEMIN_PNODE_IDS):
            ...  # existing loop body, unchanged
```

Keep the existing `if not skip_load:` load block as-is.

- [ ] **Step 4: Add the CLI flag**

Beside the `--skip-load` argument (line 175):

```python
    p.add_argument("--skip-lmp", action="store_true",
                   help="Pull only the load series, no nodal LMP. Used by the "
                        "dedicated load account, which cannot also carry a "
                        "pnode within the free-tier row cap.")
```

And thread it into the call at line 203: `skip_lmp=args.skip_lmp,`.

- [ ] **Step 5: Run the tests**

```bash
python -m pytest tests/acquisition/test_gridstatus_pull.py -v 2>&1 | tail -15
```

Expected: PASS.

- [ ] **Step 6: Confirm the key lookup was not "fixed"**

The module must keep reading the bare `GRIDSTATUS_API_KEY`; per-account override belongs in the launch script. This is load-bearing for the multi-account strategy — one process per account, each seeing a different value in the same variable.

```bash
grep -n "GRIDSTATUS_API_KEY" src/surg/acquisition/*.py
```

Expected: only the unsuffixed `GRIDSTATUS_API_KEY`. **No `_1`..`_6` suffix may appear in the module.**

- [ ] **Step 7: Commit**

```bash
git add src/surg/acquisition/gridstatus_pull.py tests/acquisition/test_gridstatus_pull.py
git commit -m "feat(acquisition): add --skip-lmp for the dedicated load account"
```

---

## Task 5: Rewrite the backfill launch script into the repo

The surviving script at `~/surg-run-logs/surg-gridstatus-backfill-launch.sh` is the pre-loss 3-account version and **cannot run**: it `cd`s to `/Users/turdy/docs/NU/Freshman_Year/Summer_2026/SURG/surg`, the deleted path, under `set -euo pipefail`. Treat this as a rewrite against the spec's account table, not a restoration. It also moves **into the repo**, so it cannot be lost again.

**Files:**
- Create: `scripts/gridstatus_backfill_launch.sh`
- Create: `scripts/poll_gridstatus_usage.py`

- [ ] **Step 1: Write the usage poller**

Create `scripts/poll_gridstatus_usage.py`:

```python
"""Poll GET /api_usage for each GRIDSTATUS_API_KEY_1..6.

Read-only. Prints plan limits, the current usage period, and consumption per
account. Never prints a key value — only a short fingerprint, so output is
safe to paste into logs or notes.
"""
from __future__ import annotations

import hashlib
import os

import httpx
from dotenv import load_dotenv

BASE_URL = "https://api.gridstatus.io/v1/api_usage"
N_ACCOUNTS = 6


def main() -> int:
    load_dotenv()
    seen: dict[str, list[str]] = {}
    for i in range(1, N_ACCOUNTS + 1):
        name = f"GRIDSTATUS_API_KEY_{i}"
        key = os.getenv(name)
        if not key:
            print(f"{name}: MISSING")
            continue
        fp = hashlib.sha256(key.encode()).hexdigest()[:8]
        seen.setdefault(fp, []).append(name)
        r = httpx.get(BASE_URL, params={"api_key": key}, timeout=30)
        if r.status_code != 200:
            print(f"{name} (fp={fp}): HTTP {r.status_code} {r.text[:200]}")
            continue
        d = r.json()
        used = d["current_period_usage"]
        lim = d["limits"]
        print(
            f"{name} (fp={fp}): {used['total_requests']}/{lim['api_requests_limit']} req, "
            f"{used['total_api_rows_returned']}/{lim['api_rows_returned_limit']} rows, "
            f"period ends {d['current_usage_period_end']}"
        )
    dupes = {fp: n for fp, n in seen.items() if len(n) > 1}
    if dupes:
        print(f"\nWARNING: duplicate keys — the account-per-pnode plan is invalid: {dupes}")
    else:
        print(f"\n{len(seen)} distinct accounts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it**

```bash
python scripts/poll_gridstatus_usage.py
```

Expected: 6 lines, each showing a request/row count, ending `6 distinct accounts.`

Note: `load_dotenv()` searches upward from the *calling file*, so run it from the repo root.

- [ ] **Step 3: Write the launch script**

Create `scripts/gridstatus_backfill_launch.sh`:

```bash
#!/bin/bash
# 5-min full-window backfill: 2023-02-07 -> 2026-06-30, 5 gridstatus.io accounts.
#
# Single-pass, one account per pnode plus a dedicated load account. Supersedes
# the pre-loss two-pass split, which existed only because fewer accounts were
# available. Account 6 is held as spare/retry budget and is NOT launched here.
#
# Free tier is 250 requests and 500K rows per account per calendar month, and
# requests are the binding constraint: 177 per pnode, 41 for load.
# See docs/specs/2026-07-30-surg-recovery-design.md § "Quota arithmetic".
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
set -a; source .env; set +a

START=2023-02-07T00:00:00Z
END=2026-06-30T00:00:00Z
DATA_ROOT="data/raw/gridstatus"
LOG_DIR="$HOME/surg-run-logs"
mkdir -p "$LOG_DIR"

echo "=== backfill launched $(date) ==="
echo "repo=$REPO_ROOT window=$START -> $END"

launch() {  # $1=account index  $2=label  $3...=extra args
  local idx="$1" label="$2"; shift 2
  local keyvar="GRIDSTATUS_API_KEY_${idx}"
  GRIDSTATUS_API_KEY="${!keyvar}" python -m surg.acquisition.gridstatus_pull \
    --start "$START" --end "$END" \
    --data-root "$DATA_ROOT" "$@" \
    > "$LOG_DIR/surg-gridstatus-backfill-account${idx}.log" 2>&1 &
  echo "$!"
}

PID1=$(launch 1 LOUDOUN       --pnodes 35010365   --skip-load)
PID2=$(launch 2 PLEASANTVIEW  --pnodes 35010371   --skip-load)
PID3=$(launch 3 GOOSECRE      --pnodes 1356178195 --skip-load)
PID4=$(launch 4 SKFFSCRK      --pnodes 1356178201 --skip-load)
PID5=$(launch 5 LOAD          --skip-lmp)

echo "account1 pid=$PID1 (LOUDOUN)"
echo "account2 pid=$PID2 (PLEASANT VIEW)"
echo "account3 pid=$PID3 (GOOSECRE)"
echo "account4 pid=$PID4 (SKFFSCRK)"
echo "account5 pid=$PID5 (pjm_load only)"

RC=0
for pid in "$PID1" "$PID2" "$PID3" "$PID4" "$PID5"; do
  wait "$pid" || RC=$?
done

echo "=== backfill finished $(date): rc=$RC ==="
if [ "$RC" -eq 0 ]; then
  touch "$LOG_DIR/surg-gridstatus-backfill-DONE"
else
  touch "$LOG_DIR/surg-gridstatus-backfill-FAILED"
fi
```

Differences from the pre-loss script, all deliberate: repo root is derived rather than hardcoded to the deleted path; account 1 is injected the same way as the others rather than relying on whatever sat in the bare variable; `--skip-load` now applies to **all four** pnode accounts because load has its own; `END` extends to 2026-06-30; SKFFSCRK is added; logs go to `$LOG_DIR` rather than `$HOME` directly.

- [ ] **Step 4: Make it executable and syntax-check it**

```bash
chmod +x scripts/gridstatus_backfill_launch.sh
bash -n scripts/gridstatus_backfill_launch.sh && echo "SYNTAX OK"
```

Expected: `SYNTAX OK`.

- [ ] **Step 5: Commit**

```bash
git add scripts/gridstatus_backfill_launch.sh scripts/poll_gridstatus_usage.py
git commit -m "feat(scripts): version-control the backfill launcher and usage poller

The pre-loss launcher lived only at ~/surg-run-logs/ and hardcoded the
now-deleted SURG/surg path, so it could not run. Rewritten for the 6-account
single-pass table: 4 pnode accounts, 1 dedicated load account, 1 spare."
```

---

## Task 6: Re-pull the hourly PJM Data Miner 2 panel (parallel track, starts now)

Not gridstatus-quota-gated, so this runs today alongside the code work. Phase 7's only hourly pass/fail row and figure F7 both depend on it.

**Files:**
- Uses: `src/surg/acquisition/pull.py` (CLI: `--feed --start --end --group-label --data-root`)
- Uses: `src/surg/acquisition/targets.py` (the locked 11-pnode set)

- [ ] **Step 1: Apply the DNS workaround before anything else**

NU DNS NXDOMAINs `api.pjm.com` while sibling PJM hosts still resolve. Symptom if skipped: `httpx.ConnectError`.

```bash
dig +short api.pjm.com || true
```

If it returns nothing, resolve a sibling host and add an `/etc/hosts` entry. This needs `sudo`, so **ask the user to run it** rather than attempting it:

```bash
dig +short www.pjm.com
# then the user runs:  sudo sh -c 'echo "<ip>  api.pjm.com" >> /etc/hosts'
```

Re-check with `dig +short api.pjm.com` before proceeding.

- [ ] **Step 2: Confirm the 11-pnode target set**

```bash
grep -n "Pnode(" src/surg/acquisition/targets.py
```

Expected: 11 entries — 6 EHV Loudoun-cluster nodes, both Ashburn 35 kV buses, OX and BRISTERS as controls, and DOM zonal.

- [ ] **Step 3: Verify the PJM key works with a 1-day pull**

```bash
python -m surg.acquisition.pull --feed rt_hrl_lmps \
  --start 2026-06-01 --end 2026-06-02 \
  --group-label dom_targets --data-root data/raw
```

Expected: exits 0 and writes a file under `data/raw/`. If it 401s, the `PJM_API_KEY` in `.env` needs re-checking with the user.

- [ ] **Step 4: Launch the full hourly backfill in the background**

The analysis window is locked at `src/surg/preprocessing/build.py:43-44` — `ANALYSIS_WINDOW_START = 2022-10-02`, `ANALYSIS_WINDOW_END = 2026-05-11` (inclusive start, exclusive end, so the final included hour is 2026-05-10 23:00 EPT).

```bash
nohup caffeinate -i python -m surg.acquisition.pull --feed rt_hrl_lmps \
  --start 2022-10-02 --end 2026-05-11 \
  --group-label dom_targets --data-root data/raw \
  > ~/surg-run-logs/surg-pjm-hourly-repull.log 2>&1 &
echo "pid=$!"
```

Note this window **ends 2026-05-11**, while the 5-min pull runs to 2026-06-30. That asymmetry is pre-existing and deliberate — the hourly panel's window was locked on 2026-05-12. Do not silently extend it to match the 5-min window; if the 2026 escalation work needs hourly data past May, that is a separate decision.

`caffeinate -i` prevents sleep from killing a long pull mid-flight.

- [ ] **Step 5: Record the Ashburn coverage question as an open item**

The 2026-07-30 memory flagged `n=17,448` for Ashburn against `31,536` for the other pnodes, marked "verify before it ships in F7". Once the pull lands, count rows per pnode and report the ratio. Do **not** treat a short Ashburn series as a pull failure without checking first — it may be genuine partial coverage of that bus.

---

## Task 7: The validation gate (tonight, before 2026-08-01T00:00:00Z)

177 requests against a 250/month cap means one botched launch costs a calendar month, with only account 6 as spare for four pnodes. This gate spends **~2 requests** of account 6's expiring July headroom to prove the pipeline end-to-end before the real launch.

**Critical path: this task depends only on Task 4 (`--skip-lmp`) and Task 5 (the poller).** It does *not* depend on Tasks 1, 2, 3 or 6. An executor working strictly in numeric order will spend the afternoon on Task 1's twelve steps and reach this too late. Do Tasks 4 and 5 first if the 8pm boundary is close.

**Target: before 8pm EDT today (2026-07-31)** — but this is a soft deadline, not a hard one. Missing it costs nothing of consequence: the gate then runs on account 6's fresh *August* allowance, spending ~3 of 250 requests on the spare account. The gate's value is being before the **launch**, not before the **reset**. Do not rush Task 4 to beat the clock — a hurried `--skip-lmp` is exactly the defect this gate exists to catch.

- [ ] **Step 1: Record account 6's pre-gate usage**

```bash
python scripts/poll_gridstatus_usage.py | grep KEY_6
```

Expected: `0/250 req`.

- [ ] **Step 2: Pull one short LMP window on account 6**

One pnode, one 7-day chunk — a single request.

```bash
set -a; source .env; set +a
GRIDSTATUS_API_KEY="$GRIDSTATUS_API_KEY_6" python -m surg.acquisition.gridstatus_pull \
  --start 2026-06-01T00:00:00Z --end 2026-06-08T00:00:00Z \
  --pnodes 1356178201 --skip-load \
  --data-root /tmp/surg-validation-gate
```

Expected: exits 0, writes one chunk file. **This is the first live proof that SKFFSCRK (1356178201) is a valid `location_id` for this dataset** — the spec asserts it, but SKFFSCRK has never been pulled at 5-min resolution.

- [ ] **Step 3: Verify the schema and rename map against the pulled chunk**

```bash
python -c "
import glob, pandas as pd
f = sorted(glob.glob('/tmp/surg-validation-gate/**/*.parquet', recursive=True))
assert f, 'no chunk written'
df = pd.read_parquet(f[0])
print('rows:', len(df))
print('columns:', sorted(df.columns))
for c in ['lmp','energy','congestion','loss']:
    print(c, 'present' if c in df.columns else 'MISSING')
"
```

Expected: roughly 2,013 rows for one pnode-week, and the four source columns `lmp/energy/congestion/loss` that the rename map maps onto `total_lmp_rt / system_energy_price_rt / congestion_price_rt / marginal_loss_price_rt`. A missing source column means the rename map is stale and **must** be fixed before the Aug 1 launch.

- [ ] **Step 4: Prove the load-only path with one request**

```bash
GRIDSTATUS_API_KEY="$GRIDSTATUS_API_KEY_6" python -m surg.acquisition.gridstatus_pull \
  --start 2026-06-01T00:00:00Z --end 2026-06-08T00:00:00Z \
  --skip-lmp \
  --data-root /tmp/surg-validation-gate
```

Expected: exits 0, writes a `pjm_load` chunk containing a `dom` column, and issues **zero** LMP requests. This is the only live test of the Task 4 code path before it carries account 5.

- [ ] **Step 5: Confirm the gate's true cost**

```bash
python scripts/poll_gridstatus_usage.py | grep KEY_6
```

Expected: 2–3 requests used. **If it is materially higher, stop and find out why before Aug 1** — that same multiplier applied to a 177-request pull would blow the cap.

- [ ] **Step 6: Record the result in `docs/decisions.md`**

Append a dated entry noting: the gate ran; whether SKFFSCRK is a valid 5-min `location_id`; the rename map verified against live columns; `--skip-lmp` verified; and the measured request cost. Follow the file's existing entry conventions.

- [ ] **Step 7: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): pre-launch validation gate result (2026-07-31)"
```

---

## Task 8: Launch the 5-min full-window pull (after 2026-08-01T00:00:00Z)

**Do not start before the reset.** Accounts 1–4 have 60–112 requests left in July, far short of the 177 each needs.

- [ ] **Step 1: Confirm the reset actually happened**

```bash
python scripts/poll_gridstatus_usage.py
```

Expected: every account shows `0/250 req` and a `current_usage_period_end` of `2026-09-01T00:00:00Z`. **If any account still shows July usage, wait — do not launch.**

- [ ] **Step 2: Launch**

```bash
nohup caffeinate -i bash scripts/gridstatus_backfill_launch.sh \
  > ~/surg-run-logs/surg-gridstatus-backfill.log 2>&1 &
echo "launcher pid=$!"
```

The pre-loss equivalent ran roughly 5 hours. `caffeinate -i` keeps the machine awake.

- [ ] **Step 3: Check progress after ~15 minutes**

```bash
tail -5 ~/surg-run-logs/surg-gridstatus-backfill-account*.log
python scripts/poll_gridstatus_usage.py
```

Expected: all five logs advancing, request counts climbing at similar rates. An account stalled at 0 while others climb means that process died — check its log rather than waiting.

- [ ] **Step 4: Confirm completion**

```bash
ls ~/surg-run-logs/surg-gridstatus-backfill-{DONE,FAILED} 2>/dev/null
python scripts/poll_gridstatus_usage.py
```

Expected: `...-DONE` exists. Per-account usage should land near 177 requests for pnode accounts and 41 for load, all under 250.

---

## Task 9: Rebuild the 5-min panel

- [ ] **Step 1: Build**

Read `build_5min.py`'s `main()` for the exact flag names first, then run the equivalent of:

```bash
python -m surg.preprocessing.build_5min --data-root data/raw/gridstatus --out data/processed
```

- [ ] **Step 2: Verify shape — the row count must NOT scale with the fourth pnode**

```bash
python -c "
import pandas as pd
df = pd.read_parquet('data/processed/panel_5min.parquet')
print('rows:', len(df))
print('cols:', len(df.columns))
for pid in (35010365, 35010371, 1356178195, 1356178201):
    n = [c for c in df.columns if str(pid) in c]
    print(pid, '->', len(n), 'columns')
"
```

Expected: rows near **350,789** — the panel is wide, one row per 5-min timestamp, one column *group* per pnode. SKFFSCRK adds columns, not rows. A count scaling toward ~470K means the builder emitted long format and something is wrong. Each pnode should show the same number of columns.

- [ ] **Step 3: Verify the cluster columns exclude SKFFSCRK**

Read what `add_loudoun_cluster_columns` actually names its output columns, then:

```bash
python -c "
import pandas as pd, numpy as np
df = pd.read_parquet('data/processed/panel_5min.parquet')
cl = [f'congestion_price_rt_{p}' for p in (35010365, 35010371, 1356178195)]
rec = df[cl].mean(axis=1).dropna()
got = df.loc[rec.index, 'congestion_price_rt_cluster_mean']
assert np.allclose(rec, got), 'cluster mean does not match the 3-node set'
print('OK: cluster mean is over the 3 Loudoun nodes, SKFFSCRK excluded')
"
```

Expected: `OK: cluster mean is over the 3 Loudoun nodes, SKFFSCRK excluded`. This is the live check on correction **C2**.

- [ ] **Step 4: Verify load coverage**

```bash
python -c "
import pandas as pd
df = pd.read_parquet('data/processed/panel_5min.parquet')
d = df.dropna(subset=['dom'])
print('dom first:', d['interval_start_utc'].min(), 'last:', d['interval_start_utc'].max())
"
```

Expected: coverage begins **2023-02-07** (the documented `pjm_load` start) and runs to 2026-06-30.

- [ ] **Step 5: Commit any builder fixes**

```bash
git add -A src/ tests/
git commit -m "fix(preprocessing): 5-min panel builder corrections found against re-pulled data"
```

Skip if the builder needed no changes. The panel itself is gitignored and is not committed.

---

## Task 10: Re-run the 5-min analysis

- [ ] **Step 1: Launch**

Read `run_5min.py`'s `main()` for exact flag names first, then run the equivalent of:

```bash
nohup caffeinate -i python -m surg.analysis.run_5min \
  --panel data/processed/panel_5min.parquet \
  --out outputs/fivemin_extended \
  > ~/surg-run-logs/surg-run5min-extended.log 2>&1 &
echo "pid=$!"
```

The pre-loss run took **9–10 hours**.

- [ ] **Step 2: Confirm the cluster guard did not fire**

```bash
grep -n "too few unique clusters" ~/surg-run-logs/surg-run5min-extended.log && echo "GUARD FIRED — see Task 11 Step 4" || echo "OK: guard did not fire"
```

The chain op7 guard raises below 10 unique clusters among exceedances. If it fires, the run dies rather than producing numbers.

- [ ] **Step 3: Confirm outputs exist**

```bash
find outputs/fivemin_extended -name '*.json' | head -20
```

---

## Task 11: Verify the restoration against recorded targets

The two panels are separate targets and **must not be checked against each other**. Every row below states its resolution — the same implicitness caused the figure-label bug fixed in `c4a64e7`.

Recorded 5-min values come from the pre-loss **3-pnode** panel. The three original pnodes must reproduce them; SKFFSCRK is new, has no baseline, and is **characterised, not verified**.

- [ ] **Step 1: Check the 5-min panel targets**

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

Record each as reproduced / diverged with the observed value. **Divergence localises the gap — it is diagnostic information, not a failure to hide.** Report divergences rather than tuning anything to match.

**Do not assume a divergence is a code defect.** The gridstatus evaluation measured **99.07% equivalence with PJM, i.e. ~0.9% republication**: gridstatus warehouses as-reported values, and PJM revises. Re-pulling the same historical window today can legitimately return slightly different numbers than the pre-loss pull. A target coming back +0.031 against a recorded +0.0367 may be data revision rather than a restoration failure.

Cheap discriminator — run it before hunting through code:

- Compare the **raw** per-pnode series (mean, p50, p95, row count) for the three original pnodes against their recorded aggregates. If the raw series have shifted in the same direction and rough magnitude as the derived statistics, suspect **republication**.
- If the raw series match but only derived statistics move, suspect **code**.

State which of the two the evidence supports for every divergence recorded.

- [ ] **Step 2: Check the hourly panel targets**

| Quantity | Expected | Status |
|---|---|---|
| Ashburn TX1 p99 vs SKFFSCRK p99 | $611.37 vs $96.13 | Diagnostic, not pass/fail |
| SKFFSCRK–cluster vs Ashburn–cluster corr | +0.870 vs +0.209 | Pass/fail — the 6-node cluster is retained, so this is reproducible |

The Ashburn rows are diagnostic because of the unresolved coverage question (`n=17,448` vs `31,536`). A quantity with an open coverage question is a weak regression target.

- [ ] **Step 3: Note what cannot be checked yet**

Ashburn TX1 is **not** in the 5-min pull, so the Ashburn-vs-SKFFSCRK comparison cannot be evaluated at 5-min resolution. Its absence after a gridstatus-only pull is **expected, not a restoration failure**.

- [ ] **Step 4: Report the live cluster count for the op7 guard**

```bash
python -c "
import pandas as pd
df = pd.read_parquet('data/processed/panel_5min.parquet')
f = df[df['passes_proposal_filter'].fillna(False).astype(bool)]
print('unique night_island_id in filter:', f['night_island_id'].nunique())
"
```

Expected: comfortably ≥10. If it is below 10, the guard fires and `run_gpd(cluster_col=...)` cannot run on that subset — report it as a finding.

- [ ] **Step 5: Write the verification entry**

Append a dated entry to `docs/decisions.md` recording every row above as reproduced or diverged, with observed values, plus the SKFFSCRK characterisation. Follow the file's existing conventions.

- [ ] **Step 6: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): Plan B restoration verification against recorded targets"
```

---

## Task 12: Document the SKFFSCRK geographic/electrical split and disclose the self-correlation

Correction **C3**, now **resolved** (user, 2026-07-31): SKFFSCRK is pulled as the fourth 5-min pnode; the hourly 6-node cluster pooling stays as pre-registered. This task documents the interpretation and discloses the self-correlation — it does **not** change any aggregation.

- [ ] **Step 1: Assemble the evidence for the write-up**

```bash
grep -n "SKFFSCRK\|1356178201" docs/decisions.md src/surg/preprocessing/build.py src/surg/acquisition/targets.py
```

Expected: the locked n=11 table (cluster tier), the 6-node pooling decision, and the ~$3/MWh tightness note at `decisions.md:151`.

- [ ] **Step 2: Quantify how much of +0.870 is self-correlation**

SKFFSCRK is one of the six nodes averaged into the hourly cluster, so recompute the correlation with SKFFSCRK **held out** of the cluster mean. This is a **disclosure diagnostic — the reported 6-node figure stays primary.** Correct the panel path and column names to what the hourly builder actually emits:

```python
import pandas as pd
df = pd.read_parquet("data/processed/panel_hourly.parquet")
cluster_all = [f"congestion_price_rt_{p}" for p in
               (35010365, 35010371, 1356178195, 1356178171, 1356178181, 1356178201)]
cluster_holdout = [c for c in cluster_all if "1356178201" not in c]
skf = df["congestion_price_rt_1356178201"]
print("with SKFFSCRK in cluster:  ", skf.corr(df[cluster_all].mean(axis=1)))
print("with SKFFSCRK held out:    ", skf.corr(df[cluster_holdout].mean(axis=1)))
```

- [ ] **Step 3: Write the interpretation into `docs/decisions.md`**

Record, as a dated entry: SKFFSCRK is **geographically rural but electrically coupled** — same 500 kV EHV network, same congestion pocket, within ~$3/MWh mean congestion of the cluster. Both correlations from Step 2, with the 6-node figure primary and the held-out figure disclosed beside it. State that the 6-node pre-registered pooling is **retained unchanged**, and that SKFFSCRK sits inside the hourly cluster and outside the 3-node 5-min cluster-set by design.

Frame the substantive point plainly: a geographically-rural node tracking the urban cluster this closely is **evidence that congestion in this pocket is network-wide rather than localized to where the data centers physically sit**. That is consistent with, and reinforces, the standing finding that the 2026 escalation must not be attributed to data centers.

Do **not** describe this as a contradiction or an unresolved question — it is a documented interpretation.

- [ ] **Step 4: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): SKFFSCRK cluster-membership contradiction, held-out correlation"
```

---

## Task 13: Push

Per the standing rule, every push is a separate explicit ask.

- [ ] **Step 1: Confirm no Claude attribution**

```bash
git log origin/main..main --format='%an|%ae|%(trailers)' | grep -iE "claude|anthropic|co-authored" || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 2: Ask the user for permission, then push**

```bash
git push origin main
git rev-list --count origin/main..main   # expect 0
```

---

## Decisions closed on 2026-07-31

Previously open; ruled by the user during planning. Log each in `docs/decisions.md` as part of Task 12 Step 3.

- **SKFFSCRK role — CLOSED.** Pulled as the 4th 5-min pnode; hourly 6-node cluster pooling retained as pre-registered. Geographically rural, electrically coupled. See correction C3.
- **Spike filtering — CLOSED: do not filter.** The ~3,193-spike class stays in. These are the scarcity events the research question targets; removing them would remove the signal. This also keeps every recorded Phase 7 target reproducible, since all were computed unfiltered. Open since May, now formally ruled.
- **Hourly window — CLOSED: unchanged at 2022-10-02 → 2026-05-11.** Not extended to match the 5-min window. It is pre-registered, hourly findings are lower-priority, and the 5-min panel already covers 2026 at higher resolution, so the escalation work does not depend on extending it.

## Open items carried forward, not settled by this plan

Advisor calls, not recovery work:

- Which QR specification is primary — pre-registered or load-controlled. The two disagree in sign on the headline 2024 τ=0.90 row. This is the largest open research question and it gates interpretation, not execution.
- Whether identifying the January 2026 driver belongs in sub-q1.
- Whether to acquire a non-DOM control pnode. Every pnode in both panels sits inside DOM, so the system-wide component of the 2026 escalation cannot currently be separated from a Dominion-specific one. Correction C3 sharpens this: a geographically-rural node tracking the cluster is suggestive of a system-wide component, but cannot settle it from inside DOM alone.

**Standing sub-q2 warning:** projecting 2026 exceedance rates forward would extrapolate an unidentified, possibly transient, possibly system-wide shift as though it were data-center load growth.

**After Plan B:** `superpowers:writing-plans` for the **12-figure** build (F1–F11 plus F4b; F4c does not exist). That design is done and user-reviewed — do not re-brainstorm it.
