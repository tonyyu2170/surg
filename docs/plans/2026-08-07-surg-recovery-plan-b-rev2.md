# SURG Recovery Plan B rev2 — Data Re-Pull and Verification

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining code gaps left by Plan A, re-pull both lost data panels, and verify the restoration against the recorded regression targets.

**Architecture:** Three tracks. The *code* track (Tasks 1–7) closes the `gpd.py` and `tail_risk_curves.py` gaps and prepares the acquisition layer for a 4-pnode / 6-account pull; it is not quota-gated and runs immediately. The *hourly* track (Task 8) re-pulls the 11-pnode PJM Data Miner 2 panel **and builds it**; also unblocked. The *5-min* track runs a cheap pre-launch validation gate (Task 9) and then the full-window pull (Task 10). Verification (Task 13) requires all three.

**Tech Stack:** Python 3.11, pandas, numpy, scipy, httpx, pytest. gridstatus.io v1 REST API (6 free-tier accounts). PJM Data Miner 2 API.

---

## This document supersedes `2026-07-31-surg-recovery-plan-b.md`

Plan B rev1 was audited by four read-only agents on 2026-07-31; the audit produced `2026-07-31-plan-b-ERRATA.md` (29 defects, E1–E29) and the verdict **"not executable as written."** This rev2 applies every errata item, plus four defects found on 2026-08-07 that the errata itself missed, plus corrections to two errata claims that turned out to be wrong.

Read this file. Rev1 and the ERRATA are retained as the audit trail only — **do not execute either.**

### Errata items whose resolution changed on re-examination

| Item | ERRATA said | Actual, verified 2026-08-07 |
|---|---|---|
| **E2** | "`resolution` is not in the recovery chain either — it exists nowhere in the repo or the archive." Told the plan author to invent a name and default. | **Wrong.** `resolution: str = "hourly"` is in `src__surg__analysis__tail_risk_curves.py.json` op3. The archive already made that decision; adopt it verbatim. The errata inventoried only the 2 `_worktree-` chains and missed the 2 non-worktree ones. |
| **E8** | `applied=8`, not 7. | **Correct** — confirmed by measured dry-run. Rev1's `applied=7` was wrong. |

### Defects found 2026-08-07, absent from both rev1 and the ERRATA

- **D1 — There are four `tail_risk_curves` chains, not two.** Rev1 Task 2 replays only `_worktree-…__src__…` and `_worktree-…__tests__…`. Also present: `src__surg__analysis__tail_risk_curves.py.json` (6 ops) and `tests__analysis__test_tail_risk_curves.py.json` (5 ops). The non-worktree pair carries `resolution` **and** the `_plot_suptitle` helper that fixes the hardcoded `"hourly"` plot label. This makes rev1 Task 2 Step 2's manual hunt for that bug redundant — the chain *is* the fix.

- **D2 — `pnode_to_response` is a fourth unaccepted kwarg.** E2 lists three (`cross_pnode_pnodes`, `plotted_pnodes`, `resolution`). `run_5min.py:103` also passes `pnode_to_response=FIVEMIN_TAIL_RISK_MAP`, equally absent from the live signature. Verified: all four return `0 hits` against `tail_risk_curves.py`.

- **D3 — The tail-risk regression test is vacuous and has never guarded anything.** `REF_DIR = tests/regression/hourly_reference` and the test globs `REF_DIR / "tail_risk_curves" / "*.json"`, but the fixtures live one level deeper at `hourly_reference/tail_risk_curves/tail_risk_curves/*.json` (the capture wrote `out_root/tail_risk_curves/` into a directory already named `tail_risk_curves`). The glob returns empty, the comparison loop never executes, and `test_tail_risk_curves_pair_bootstrap_equivalence` passes trivially. Every sibling fixture dir (`gpd_components/`, `gpd_continuous/`, …) stores JSONs at the correct depth — this one is the outlier.

- **D4 — Adding `result["resolution"]` breaks that regression test the moment D3 is fixed.** `_assert_numeric_equivalence` does a strict key-set comparison and raises on `extra=`. The five captured reference JSONs have no `resolution` key. D3 currently masks this; fixing D3 unmasks it. Handled deliberately in Task 3.

### Calendar items that expired

Rev1's Task 7 was scheduled "before 8pm EDT 2026-07-31" and Task 8 was gated on the 2026-08-01 quota reset. Both dates have passed. The gate is now undated and runs on August quota; the reset check is restated per E16.

---

## P0 preamble — read before running any command

**Every `python` and `python3` in this plan means `.venv/bin/python`**, including inside `scripts/gridstatus_backfill_launch.sh`. Bare `python` is an interactive-shell alias that does not resolve in `#!/bin/bash` scripts, and ambient `python3` has no `surg` installed (ERRATA E1).

Gate before starting anything:

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
.venv/bin/python -c "import surg; print('ok')"
```

Expected: `ok`. If this fails, stop — nothing below will work.

**Replay hazard (applies to every chain step):** `replay.py` writes the destination file even when an op skips (`replay.py:50`, before `return 1`). If a replay reports any skip, `git checkout -- <file>` before retrying. Never hand-reconcile a skipped op; report it.

**Commit policy:** every commit and every push is a separate explicit ask to the user. Do not batch them.

---

## Status carried in from Plan A

| Spec phase | State |
|---|---|
| Phase 1 — unblock data | **DONE.** `.env` holds all 7 keys (`PJM_API_KEY` + `GRIDSTATUS_API_KEY_1..6`), 6 distinct accounts. |
| Phase 2 — acquisition layer | **DONE.** `gridstatus_client.py`, `gridstatus_pull.py`, `gridstatus_validate.py` + 3 test files present. |
| Phase 8 — push | **DONE 2026-07-31.** `origin/main` at `94cc56e`. |
| Phase 3 — re-pull | This plan, Tasks 8–12. |
| Phase 7 — verify | This plan, Task 13. |

**Live tree, verified 2026-08-07:** working tree clean, 5 commits ahead of `origin/main` (all docs). `318 tests collected`; `313 passed, 6 skipped` is the standing baseline. `data/raw`, `data/interim`, `data/processed` contain only `.gitkeep` — **both panels are still absent.** No mutation probe in `gpd.py`.

**Quota:** as of 2026-07-31 every account showed `current_usage_period_end = 2026-08-01T00:00:00Z`, Free tier, 250 requests / 500,000 rows per calendar month. That period has rolled over. Re-read live usage in Task 9 Step 1 rather than trusting this table.

---

## Corrections carried forward from rev1

### C1 — The `gpd.py` gap is mutation-test scaffolding, not a statistics problem

Chain `_worktree-surg-gridstatus-5min__src__surg__analysis__gpd.py.json` has 11 ops. **op8** inserts `drawn = np.unique(drawn)` carrying the literal comment `# INTENTIONAL BUG for regression-test validation`; **op9** applies the same mutation inline against the clean block; **op10** reverts op9 exactly (`op9.new_string == op10.old_string` and `op9.old_string == op10.new_string`).

The faithful end state is **ops 0–7 applied, ops 8–10 not applied**. The 2026-07-30 `applied=9 skipped=2` result is exactly what this predicts: op8 applied and injected the self-labeled deliberate bug, after which op9 and op10 could no longer match.

**Measured target: `applied=8 skipped=0`** (ops 0–7 inclusive is eight ops; ERRATA E8). This is not derived — it was produced by a report-only dry-run against live HEAD on 2026-08-07.

### C2 — `FIVEMIN_PNODE_IDS` is both the pull-set and the cluster-set

`build_5min.py:48` calls `add_loudoun_cluster_columns(lmp_wide, FIVEMIN_PNODE_IDS)`. Pre-loss this was safe only by coincidence: the tuple was exactly the three Loudoun-cluster nodes. Adding SKFFSCRK as a fourth pnode would silently pool a comparison node into the cluster average, and every 5-min regression target is computed on those cluster columns — the divergence would look like a restoration failure. The constant is also duplicated at `gridstatus_pull.py:31` and `schema_5min.py:13`. Task 5 splits the two roles.

### C3 — SKFFSCRK is geographically rural but electrically coupled

**Resolved by the user, 2026-07-31.** SKFFSCRK is pulled as the fourth 5-min pnode; the hourly 6-node cluster pooling stays exactly as pre-registered.

Both descriptions are true: SKFFSCRK sits in a markedly more rural area yet prices within ~$3/MWh of the urban cluster because it is on the same 500 kV EHV network inside the same congestion pocket. Electrical distance is not geographic distance. A geographically-rural node tracking the cluster at +0.870 is **evidence for the system-wide character of the 2026 escalation**, consistent with the standing finding that the escalation must never be attributed to data centers.

**Deliberate asymmetry to preserve:** SKFFSCRK is *inside* the 6-node hourly cluster and *outside* the 3-node 5-min cluster-set. Do not "fix" this to make the panels match.

**Priority note (user, 2026-07-31):** hourly findings are lower-priority than the 5-min work. Task 8 runs in parallel because it is cheap, but must not gate the 5-min track.

---

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/surg/analysis/gpd.py` | GPD fitting, conditional-Z, cluster bootstrap | Modify — replay chain ops 0–7 |
| `tests/analysis/test_gpd.py` | GPD unit tests incl. cluster-bootstrap guard | Modify — replay chain, 3 ops |
| `src/surg/analysis/tail_risk_curves.py` | Decile tail-risk curves | Modify — **hand-written merge** (chains cannot replay) |
| `tests/analysis/test_tail_risk_curves.py` | Tail-risk tests | Modify — replay 2 chains (2 + 4 ops after dedup) |
| `tests/regression/test_hourly_pair_bootstrap_equivalence.py` | Hourly byte-equivalence guards | Verify — the D3 fix is a fixture move, not a source edit |
| `tests/regression/hourly_reference/tail_risk_curves/**` | Captured hourly fixtures | Modify — re-nest, stamp `resolution` |
| `tests/analysis/test_run_5min.py` | 5-min orchestrator smoke test | Modify — remove module-level skip |
| `src/surg/preprocessing/schema_5min.py` | 5-min panel schema + pnode constants | Modify — split pull-set / cluster-set, 4-pnode columns, bump schema version |
| `src/surg/preprocessing/build_5min.py` | 5-min panel builder | Modify — use cluster-set for cluster columns |
| `src/surg/acquisition/gridstatus_pull.py` | gridstatus pull CLI | Modify — import shared pnode tuple, add `--skip-lmp` |
| `tests/acquisition/test_gridstatus_pull.py` | Pull CLI tests | Modify — cover `--skip-lmp` |
| `tests/preprocessing/test_build_5min.py` | Builder tests | Modify — 4-pnode fixture, cluster-exclusion guard |
| `scripts/gridstatus_backfill_launch.sh` | 6-account parallel launch | **Create** |
| `scripts/poll_gridstatus_usage.py` | Per-account quota poll | **Create** |

---

## Task 1: Close the `gpd.py` `cluster_col` gap

`run_5min.py:93` calls `run_gpd(..., cluster_col="night_island_id")` and `cluster_col` exists nowhere in the analysis layer.

**Files:**
- Modify: `src/surg/analysis/gpd.py`
- Modify: `tests/analysis/test_gpd.py`
- Chains: `~/surg-recovery-2026-07-30/edit-chains/_worktree-surg-gridstatus-5min__src__surg__analysis__gpd.py.json` (11 ops), `..._tests__analysis__test_gpd.py.json` (3 ops)

- [x] **Step 0: Capture the test baseline verbatim**

Every later count in this plan is a **delta** from this line, not an absolute. Record the output exactly.

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
.venv/bin/python -m pytest -q 2>&1 | tail -2
```

Expected as of 2026-08-07: `313 passed, 6 skipped`. If your baseline differs, use **your** number — the deltas below still hold, the absolutes do not.

- [x] **Step 1: Confirm the chain still shows the op 8/9/10 pattern**

```bash
.venv/bin/python -c "
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

- [x] **Step 2: Replay ops 0–7 only**

`replay.py` cannot do this itself: its interface is positional (`replay.py <chain> <dest> [--from-base]`), with no op-range selector and no dedup flag. This chain has no `Write` baseline (all 11 ops are `Edit`), so a bare invocation exits 2.

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
.venv/bin/python - <<'PY'
import json
from pathlib import Path

CHAIN = Path("/Users/turdy/surg-recovery-2026-07-30/edit-chains/"
             "_worktree-surg-gridstatus-5min__src__surg__analysis__gpd.py.json")
DEST = Path("src/surg/analysis/gpd.py")

ops = json.loads(CHAIN.read_text())["ops"][:8]   # ops 0-7; 8-10 are scaffolding

seen, deduped = set(), []
for o in ops:
    if o["op"] != "Edit":
        continue
    key = (o["old_string"], o["new_string"])
    if key in seen:
        print("  DEDUP: dropping repeated edit")
        continue
    seen.add(key)
    deduped.append(o)

text = DEST.read_text()
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

Expected: **`applied=8 skipped=0`** — measured by dry-run against live HEAD on 2026-08-07, not derived.

**If any op skips, stop.** `git checkout -- src/surg/analysis/gpd.py` and report which op and its `old_string`. Do not hand-reconcile.

- [x] **Step 3: Verify no duplicate definitions and no injected bug**

```bash
grep -c "def run_gpd" src/surg/analysis/gpd.py
grep -c "def gpd_conditional_on_z" src/surg/analysis/gpd.py
grep -n "INTENTIONAL BUG" src/surg/analysis/gpd.py || echo "GOOD: no intentional-bug line present"
grep -n "cluster_col" src/surg/analysis/gpd.py | head -5
```

Expected: each `def` count is exactly `1`; `GOOD: no intentional-bug line present`; `cluster_col` now appears.

- [x] **Step 4: Replay the companion test chain**

```bash
.venv/bin/python /Users/turdy/surg-recovery-2026-07-30/replay.py \
  /Users/turdy/surg-recovery-2026-07-30/edit-chains/_worktree-surg-gridstatus-5min__tests__analysis__test_gpd.py.json \
  tests/analysis/test_gpd.py --from-base
grep -c "def test_gpd_conditional_on_z_cluster_bootstrap_duplicates_rows" tests/analysis/test_gpd.py
```

Expected: `applied=3 skipped=0` (measured), then `1`.

- [x] **Step 5: Run the GPD tests**

```bash
.venv/bin/python -m pytest tests/analysis/test_gpd.py -q
```

Expected: PASS.

- [x] **Step 6: Prove the restoration with the author's own mutation test**

A green suite proves little. The chain restored in Step 4 contains the test the original author wrote to catch this exact mutation — `test_gpd_conditional_on_z_cluster_bootstrap_duplicates_rows`, whose docstring reads: *"Locks in the correct cluster-bootstrap mechanic: a cluster id drawn twice by rng.choice must contribute its exceedance rows twice to the resampled arrays (not deduplicated)."*

Insert this line immediately after the `drawn = rng.choice(unique_clusters, size=len(unique_clusters), replace=True)` line in `gpd.py`:

```python
            drawn = np.unique(drawn)  # TEMPORARY mutation probe — remove in Step 7
```

```bash
.venv/bin/python -m pytest tests/analysis/test_gpd.py::test_gpd_conditional_on_z_cluster_bootstrap_duplicates_rows -q
```

Expected: **FAIL.** If it passes, the restoration is not faithful — the test is not reaching the resampling path. Report that instead of proceeding.

- [x] **Step 7: Delete the mutation probe**

Delete the line added in Step 6. This is an explicit deletion instruction — rev1's Step 7 contained only a grep and was satisfiable without removing anything (ERRATA E12).

```bash
grep -n "TEMPORARY mutation probe\|np.unique(drawn)" src/surg/analysis/gpd.py \
  && echo "PROBE STILL PRESENT — delete it before continuing" \
  || echo "probe removed"
.venv/bin/python -m pytest tests/analysis/test_gpd.py -q
```

Expected: `probe removed`; tests PASS.

- [x] **Step 8: Record the `< 10` cluster guard's production dependency**

Chain op7 adds a guard that **raises** when there are fewer than 10 unique clusters among exceedances. `run_5min.py:93` passes `cluster_col="night_island_id"` on the in-filter subset only.

```bash
grep -rn "night_island_id" src/surg/preprocessing/ src/surg/analysis/ | head
```

Expected: the column is emitted by the preprocessing layer. Record the finding; the live count check happens in Task 13 Step 4, once real data exists.

- [x] **Step 9: Commit (ask the user first)**

Hard abort if the probe survived:

```bash
grep -n "np.unique(drawn)" src/surg/analysis/gpd.py && { echo "ABORT: probe still in tree"; exit 1; }
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "fix(analysis): restore gpd cluster_col chain, excluding mutation scaffolding

Replays ops 0-7 of the worktree gpd.py edit chain. Ops 8-10 are mutation-test
scaffolding: op8 carries a literal 'INTENTIONAL BUG for regression-test
validation' comment, and op9/op10 are an exact revert pair. The prior
applied=9 skipped=2 replay had injected that deliberate bug."
```

---

## Task 2: Merge `run_tail_risk_curves` by hand

**The source chains cannot be replayed.** Measured dry-run against live HEAD, 2026-08-07:

| Chain | Ops | Result |
|---|---|---|
| `_worktree-…__src__…__tail_risk_curves.py.json` | 2 | **`applied=1 skipped=1`** — op0 cannot match |
| `src__surg__analysis__tail_risk_curves.py.json` | 6 (5 after dedup) | **`applied=3 skipped=2`** — depends on the worktree chain's op0 |
| `_worktree-…__tests__…__test_tail_risk_curves.py.json` | 2 | `applied=2 skipped=0` ✅ |
| `tests__analysis__test_tail_risk_curves.py.json` | 5 (4 after dedup) | `applied=4 skipped=0` ✅ |

Both **test** chains apply cleanly. Only the **source** file must be hand-merged, because HEAD moved past the chains' base: item #8 added `bootstrap_method` and `pnode_labels`, item #9 widened `filter_col` to `str | None`, and the cluster-bootstrap island logic landed after the chains were captured.

Replaying the source chains would narrow `filter_col: str | None → str` and **silently regress the sub-q1 item #9 filter-skip mode** (ERRATA E3).

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py`
- Modify: `tests/analysis/test_tail_risk_curves.py`

- [x] **Step 1: Replay the two test chains first**

They define the behavior the merged function must satisfy, so they come first and must fail before the merge.

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
R=/Users/turdy/surg-recovery-2026-07-30
.venv/bin/python $R/replay.py \
  $R/edit-chains/_worktree-surg-gridstatus-5min__tests__analysis__test_tail_risk_curves.py.json \
  tests/analysis/test_tail_risk_curves.py --from-base
```

Expected: `applied=2 skipped=0`.

The second chain contains **two identical `(old_string, new_string)` ops** (op0 and op1 — the hook-rejected double-insert pattern). `replay.py` has no dedup flag, so replaying it directly would double-insert the `_plot_suptitle` import. Use the deduplicating snippet:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path

CHAIN = Path("/Users/turdy/surg-recovery-2026-07-30/edit-chains/"
             "tests__analysis__test_tail_risk_curves.py.json")
DEST = Path("tests/analysis/test_tail_risk_curves.py")

seen, deduped = set(), []
for o in json.loads(CHAIN.read_text())["ops"]:
    if o["op"] != "Edit":
        continue
    key = (o["old_string"], o["new_string"])
    if key in seen:
        print("  DEDUP: dropping repeated edit")
        continue
    seen.add(key)
    deduped.append(o)

text = DEST.read_text()
applied = skipped = 0
for o in deduped:
    old, new = o["old_string"], o["new_string"]
    count = text.count(old)
    if count == 0:
        print(f"  SKIP (no match): {old[:70]!r}"); skipped += 1; continue
    if count > 1 and not o.get("replace_all"):
        print(f"  SKIP (ambiguous, {count}): {old[:70]!r}"); skipped += 1; continue
    text = text.replace(old, new, 1)
    applied += 1

DEST.write_text(text)
print(f"{DEST}: applied={applied} skipped={skipped}")
PY
```

Expected: `DEDUP: dropping repeated edit` once, then **`applied=4 skipped=0`**.

Confirm no double-insert:

```bash
grep -c "_plot_suptitle," tests/analysis/test_tail_risk_curves.py
```

Expected: `1`.

- [x] **Step 2: Run the tests to confirm they fail**

```bash
.venv/bin/python -m pytest tests/analysis/test_tail_risk_curves.py -q 2>&1 | tail -15
```

Expected: FAIL — `ImportError: cannot import name '_plot_suptitle'`, plus `TypeError: run_tail_risk_curves() got an unexpected keyword argument 'pnode_to_response'`.

- [x] **Step 3: Add the `_plot_suptitle` helper**

From `src__surg__analysis__tail_risk_curves.py.json` op0. Insert immediately **above** `def plot_tail_risk_curves(`:

```python
def _plot_suptitle(per_pnode: dict) -> str:
    """Figure caption for a per-pnode result dict.

    `resolution` is read from the result rather than hardcoded: this
    plotter is shared by the hourly and 5-min entrypoints. Result dicts
    written before the key existed were all hourly runs, so that is the
    fallback.
    """
    return (
        f"{per_pnode['pnode_label']}: P(LMP > $X) by Z decile "
        f"(filter: {per_pnode.get('filter', '')}, "
        f"n_boot={per_pnode['n_boot']}, "
        f"{per_pnode.get('resolution', 'hourly')})"
    )
```

- [x] **Step 4: Use it in the plotter**

In `plot_tail_risk_curves`, replace this block:

```python
    axes[0].set_ylabel("P(LMP > $threshold)")
    filter_desc = per_pnode.get("filter", "")
    fig.suptitle(
        f"{pnode_label}: P(LMP > $X) by Z decile "
        f"(filter: {filter_desc}, n_boot={per_pnode['n_boot']}, hourly)"
    )
```

with:

```python
    axes[0].set_ylabel("P(LMP > $threshold)")
    fig.suptitle(_plot_suptitle(per_pnode))
```

Then check for a now-unused local (chain op5 removes it):

```bash
grep -n "pnode_label" src/surg/analysis/tail_risk_curves.py | sed -n '1,40p'
```

Read the whole `plot_tail_risk_curves` function before deleting. Remove the `pnode_label = per_pnode["pnode_label"]` assignment **only** if no other line in that function uses it. This is the one place a faithful chain replay would have left dead code.

- [x] **Step 5: Write the merged `run_tail_risk_curves`**

Replace the entire existing `def run_tail_risk_curves(...)` through the end of its body (up to but not including `def _json_serializable`) with the following. This is the union of live HEAD (items #8/#9) and both source chains — written out in full because no replay can produce it.

```python
def run_tail_risk_curves(
    panel: pd.DataFrame,
    *,
    out_root: Path,
    thresholds: list[float] | None = None,
    n_boot: int = 200,
    seed: int = 0,
    bootstrap_method: str = "pair",
    pnode_labels: tuple[str, ...] | None = None,
    filter_col: str | None = "passes_proposal_filter",
    pnode_to_response: dict[str, dict[str, str]] | None = None,
    cross_pnode_pnodes: tuple[str, ...] | None = None,
    plotted_pnodes: tuple[str, ...] | None = None,
    z_col: str = Z_COL,
    resolution: str = "hourly",
) -> None:
    """Top-level orchestrator: applies the proposal-filter (or skips it),
    runs all per-pnode + cross-pnode analyses, writes outputs to disk.

    Writes 5 JSONs + 4 PNGs + 1 CSV under ``out_root/tail_risk_curves/``.

    Sub-q1 item #8: ``bootstrap_method`` is "pair" (default; preserves
    hourly behavior) or "cluster" (5-min companion: resample whole 3-hour
    islands). ``pnode_labels`` selects a subset to process.
    Sub-q1 item #9: ``filter_col=None`` skips the filter and operates on
    the full panel.
    5-min companion: ``pnode_to_response`` / ``cross_pnode_pnodes`` /
    ``plotted_pnodes`` / ``z_col`` retarget the routine at a panel whose
    pnode labels and Z column differ from the hourly ones, and
    ``resolution`` is stamped into each result so the shared plotter can
    label the figure correctly instead of hardcoding "hourly".
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()
    if pnode_to_response is None:
        pnode_to_response = PNODE_TO_RESPONSE
    if plotted_pnodes is None:
        plotted_pnodes = PER_PNODE_PLOTTED

    # `pnode_labels` (item #8) and `cross_pnode_pnodes` (5-min worktree)
    # are two names for the same knob, arrived at independently. Accept
    # either; refuse a conflicting pair rather than silently picking one.
    if (
        cross_pnode_pnodes is not None
        and pnode_labels is not None
        and tuple(cross_pnode_pnodes) != tuple(pnode_labels)
    ):
        raise ValueError(
            "cross_pnode_pnodes and pnode_labels were both given and differ: "
            f"{tuple(cross_pnode_pnodes)!r} vs {tuple(pnode_labels)!r}"
        )
    if cross_pnode_pnodes is not None:
        pnodes_to_process = tuple(cross_pnode_pnodes)
    elif pnode_labels is not None:
        pnodes_to_process = tuple(pnode_labels)
    else:
        pnodes_to_process = tuple(CROSS_PNODE_PNODES)

    tr_dir = Path(out_root) / "tail_risk_curves"
    tr_dir.mkdir(parents=True, exist_ok=True)

    if filter_col is None:
        filtered = panel.copy()
        filter_desc = "no filter (full panel)"
    else:
        filtered = panel.loc[panel[filter_col] == True].copy()  # noqa: E712
        filter_desc = f"{filter_col} == True"

    # Materialize derived total_lmp columns where features.py didn't label
    # them. Scoped to the pnodes actually processed: the hourly full run
    # passes none of the selectors, so this is identical to the previous
    # `CROSS_PNODE_PNODES` behavior there, while the 5-min panel (whose
    # labels are not the hourly ones) no longer KeyErrors.
    filtered = _ensure_total_lmp_columns(filtered, pnodes_to_process)

    # Compute island_ids on the filtered panel (only needed for cluster
    # bootstrap; identify_islands assigns one int per filtered row based
    # on >10-minute timestamp gaps).
    if bootstrap_method == "cluster":
        from surg.analysis.bootstrap_strategies import identify_islands
        island_ids = identify_islands(
            pd.DatetimeIndex(filtered["datetime_beginning_ept"]),
            pd.Series(True, index=filtered.index),
            gap_threshold_minutes=10,
        )
    else:
        island_ids = None

    all_results: list[dict] = []

    for pnode_label in pnodes_to_process:
        response_cols = pnode_to_response[pnode_label]
        # Drop NA rows in either response column for this pnode
        cols = list(response_cols.values()) + [z_col]
        sub = filtered.dropna(subset=cols)
        # Slice island_ids to match `sub`'s row index (dropna preserves
        # index labels)
        sub_island_ids = (
            island_ids.loc[sub.index] if island_ids is not None else None
        )

        result = run_pnode_tail_risk_curves(
            panel=sub,
            pnode_label=pnode_label,
            response_cols=response_cols,
            z_col=z_col,
            thresholds=thresholds,
            n_deciles=10,
            n_boot=n_boot,
            seed=seed,
            bootstrap_method=bootstrap_method,
            island_ids=sub_island_ids,
        )
        # Inject filter + resolution provenance (the per-pnode routine
        # can't know either — both come from how it was invoked).
        result["filter"] = filter_desc
        result["resolution"] = resolution
        all_results.append(result)

        if pnode_label in plotted_pnodes:
            # Write per-pnode JSON
            with open(tr_dir / f"{pnode_label}.json", "w") as f:
                json.dump(_json_serializable(result), f, indent=2)
            # Write per-pnode PNG
            plot_tail_risk_curves(result, tr_dir / f"{pnode_label}.png")

    # Cross-pnode summary
    summary = aggregate_cross_pnode_summary(all_results)
    summary["filter"] = filter_desc   # propagate provenance to cross-pnode summary too
    with open(tr_dir / "cross_pnode_summary.json", "w") as f:
        json.dump(_json_serializable(summary), f, indent=2)

    # Cross-pnode summary CSV
    _write_cross_pnode_csv(summary, tr_dir / "cross_pnode_summary.csv")
```

**Three deliberate choices, each preserving something a literal replay would have destroyed:**

1. `result["filter"] = filter_desc` — **not** the chain's `f"{filter_col} == True"`. Item #9's `filter_col=None` path needs the string `"no filter (full panel)"`; the chain's version predates that mode and would emit `"None == True"`.
2. `filter_col: str | None` is retained at its live width. The chain would narrow it to `str`.
3. `summary["resolution"]` is **not** set. The chain stamps `resolution` on per-pnode results only; the cross-pnode summary keeps its original key set. Do not add it — Task 3 depends on that key set being exactly as captured.

- [x] **Step 6: Run the tests**

```bash
.venv/bin/python -m pytest tests/analysis/test_tail_risk_curves.py -q 2>&1 | tail -10
```

Expected: PASS, including `test_plot_suptitle_reports_the_panel_resolution`, `test_run_tail_risk_curves_records_resolution_in_result`, `test_run_tail_risk_curves_accepts_custom_pnode_map`, and `test_run_tail_risk_curves_accepts_custom_z_and_filter_col`.

- [x] **Step 7: Prove both callers still bind**

```bash
.venv/bin/python -c "
import inspect
from surg.analysis.tail_risk_curves import run_tail_risk_curves as f
s = inspect.signature(f)
for p in ('bootstrap_method','pnode_labels','filter_col','pnode_to_response',
          'cross_pnode_pnodes','plotted_pnodes','z_col','resolution'):
    assert p in s.parameters, p
assert s.parameters['resolution'].default == 'hourly'
print('OK: merged signature satisfies run.py (pnode_labels) and run_5min.py (cross_pnode_pnodes)')
"
```

Expected: `OK: ...`.

- [x] **Step 8: Commit (ask the user first)**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "fix(analysis): merge 5-min tail_risk_curves params into the post-item-9 signature

The four archived tail_risk_curves chains cannot replay: HEAD moved past
their base when items #8/#9 added bootstrap_method, pnode_labels and
filter_col: str | None. Replaying would have narrowed filter_col back to
str, regressing the item #9 filter-skip mode.

Adds pnode_to_response / cross_pnode_pnodes / plotted_pnodes / z_col /
resolution and the _plot_suptitle helper, so the shared plotter labels
5-min figures correctly instead of hardcoding 'hourly'. Both test chains
replayed cleanly and pin the merged behavior."
```

---

## Task 3: Arm the vacuous tail-risk regression test (D3/D4)

`test_tail_risk_curves_pair_bootstrap_equivalence` has never compared anything. `REF_DIR / "tail_risk_curves"` globs `*.json` at a level that holds only a directory; the fixtures are one level deeper. The loop body never executes.

This must run **after** Task 2, because arming it unmasks D4 — the `resolution` key Task 2 adds is `extra=` against the captured key set.

**Files:**
- Modify: `tests/regression/hourly_reference/tail_risk_curves/**`

- [x] **Step 1: Confirm the defect**

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
echo "globbed by the test (expect 0):"
ls tests/regression/hourly_reference/tail_risk_curves/*.json 2>/dev/null | wc -l
echo "actually present (expect 5):"
ls tests/regression/hourly_reference/tail_risk_curves/tail_risk_curves/*.json | wc -l
echo "sibling dir for comparison (expect >0):"
ls tests/regression/hourly_reference/gpd_components/*.json | wc -l
```

Expected: `0`, `5`, then a non-zero count — confirming this directory is the outlier.

- [x] **Step 2: Flatten the fixture directory**

The fix is a fixture move, not a source edit: the test already looks in the right place.

```bash
git mv tests/regression/hourly_reference/tail_risk_curves/tail_risk_curves/* \
       tests/regression/hourly_reference/tail_risk_curves/
rmdir tests/regression/hourly_reference/tail_risk_curves/tail_risk_curves
ls tests/regression/hourly_reference/tail_risk_curves/
```

Expected: the 5 JSONs, 4 PNGs and 1 CSV now sit directly under `tail_risk_curves/`.

- [x] **Step 3: Stamp `resolution` into the per-pnode fixtures**

Every captured reference was an hourly run — the chain author states exactly this in `_plot_suptitle`'s own docstring ("Result dicts written before the key existed were all hourly runs"). Recording that known-true provenance fact is **not** re-blessing numbers: no numeric value is touched, and `cross_pnode_summary.json` is deliberately left alone because Task 2 does not stamp the summary.

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path

REF = Path("tests/regression/hourly_reference/tail_risk_curves")
for f in sorted(REF.glob("*.json")):
    if f.name == "cross_pnode_summary.json":
        print(f"  skip (summary is not stamped): {f.name}")
        continue
    d = json.loads(f.read_text())
    assert "pnode_label" in d, f"{f.name} is not a per-pnode result"
    if d.get("resolution") == "hourly":
        print(f"  already stamped, leaving alone: {f.name}")
        continue
    assert "resolution" not in d, f"{f.name} has an unexpected resolution: {d['resolution']!r}"
    d["resolution"] = "hourly"
    f.write_text(json.dumps(d, indent=2))
    print(f"  stamped resolution=hourly: {f.name}")
PY
```

Expected: 4 files stamped, `cross_pnode_summary.json` skipped.

**This step is idempotent by design.** Task 8 Step 6 instructs a re-run if the regression test reports `extra={'resolution'}`, and a bare `assert "resolution" not in d` would abort on the second pass — leaving a partial stamp permanently un-completable if the first pass died midway. Re-running is always safe.

- [x] **Step 4: Verify the glob now resolves**

```bash
.venv/bin/python -c "
from pathlib import Path
d = Path('tests/regression/hourly_reference/tail_risk_curves')
n = len(sorted(d.glob('*.json')))
assert n == 5, f'expected 5 reference JSONs, got {n}'
print(f'OK: test glob now finds {n} reference files (was 0)')
"
```

Expected: `OK: test glob now finds 5 reference files (was 0)`.

- [x] **Step 5: Confirm the test still skips without a panel**

```bash
.venv/bin/python -m pytest tests/regression/ -q -rs 2>&1 | tail -5
```

Expected: `5 skipped` — the hourly panel does not exist yet, so `_hourly_panel_or_skip` still short-circuits. **The real check runs in Task 8 Step 6, once the panel is rebuilt.** Record here that this test was previously green-but-vacuous and is now armed.

- [x] **Step 6: Commit (ask the user first)**

```bash
git add tests/regression/
git commit -m "fix(regression): arm the tail-risk equivalence test, which never compared anything

REF_DIR/tail_risk_curves globbed *.json one level above the fixtures --
the capture wrote out_root/tail_risk_curves/ into a directory already
named tail_risk_curves. The comparison loop iterated zero times, so
test_tail_risk_curves_pair_bootstrap_equivalence passed trivially for its
whole life. Every sibling fixture dir stores JSONs at the correct depth.

Flattens the directory and stamps resolution=hourly into the four
per-pnode fixtures, which the merged run_tail_risk_curves now emits. All
captured runs were hourly, so this records provenance without altering a
single numeric value."
```

---

## Task 4: Unskip the 5-min smoke test and green the suite

**Files:**
- Modify: `tests/analysis/test_run_5min.py`

- [x] **Step 1: Remove the module-level skip**

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

If `pytest` becomes an unused import afterwards, remove that import too.

- [x] **Step 2: Run the previously-skipped smoke test**

```bash
.venv/bin/python -m pytest tests/analysis/test_run_5min.py -v
```

Expected: PASS — 2 tests. It runs on a synthetic panel and needs no real data. This is the first end-to-end proof that Tasks 1 and 2 together make `run_all_5min` callable.

- [x] **Step 3: Run the full suite**

```bash
.venv/bin/python -m pytest -q 2>&1 | tail -5
```

**Check this as a delta from Task 1 Step 0's captured baseline, not against an absolute.** Rev1's "at least 313 passed" was satisfiable by doing nothing (ERRATA E18), but E18's proposed replacement — `315 passed, 4 skipped` — is also wrong: it was derived from a tree where Tasks 2 and 5 had not yet added tests.

Accounting, relative to baseline:

| Source | Passed | Skipped |
|---|---|---|
| Task 1 — gpd test chain (3 ops, no new test functions) | +0 | 0 |
| Task 2 Step 1 — two test chains add 4 test functions | +4 | 0 |
| Task 4 — module-level skip removed, `test_run_5min.py` holds 2 tests | +2 | **−1** |
| Task 5 Step 1 — `test_cluster_columns_exclude_skffscrk` (only if Task 5 ran first) | +1 | 0 |

From a `313 passed, 6 skipped` baseline with Tasks 1, 2, 4 done and Task 5 **not** yet done, expect **`319 passed, 5 skipped`**.

The 5 remaining skips are the `tests/regression/` suite, which stays skipped until the hourly panel exists (Task 8). Only **one** skip is removed here — the `test_run_5min.py` module-level one.

Report the actual line, then confirm the arithmetic against which tasks have run. **A mismatch is not a failure until you have accounted for which task added what** — an unexplained mismatch is.

- [x] **Step 3b: Confirm no test was lost**

A delta check passes if one test is added and another silently disappears. Pin the names:

```bash
.venv/bin/python -m pytest --collect-only -q 2>&1 | tail -1
.venv/bin/python -m pytest tests/analysis/test_tail_risk_curves.py --collect-only -q 2>&1 | tail -1
```

Expected: total collected is baseline `318` + 6 (4 from Task 2, 2 from `test_run_5min.py` becoming collectable) = **324**, and the tail-risk module collects 4 more than it did at baseline.

- [x] **Step 4: Commit (ask the user first)**

```bash
git add tests/analysis/test_run_5min.py
git commit -m "test(analysis): unskip the 5-min orchestrator smoke test

Gated on the gpd cluster_col chain (Task 1) and the tail_risk_curves
signature merge (Task 2); both are now in."
```

---

## Task 5: Split the 5-min pull-set from the cluster-set

Prevents correction **C2**: adding SKFFSCRK to the pull must not pull it into the Loudoun cluster average.

**Files:**
- Modify: `src/surg/preprocessing/schema_5min.py`
- Modify: `src/surg/preprocessing/build_5min.py`
- Modify: `src/surg/acquisition/gridstatus_pull.py`
- Modify: `tests/preprocessing/test_build_5min.py`

- [x] **Step 1: Write the failing test**

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

- [x] **Step 2: Run it to confirm it fails**

```bash
.venv/bin/python -m pytest tests/preprocessing/test_build_5min.py::test_cluster_columns_exclude_skffscrk -q
```

Expected: FAIL with `ImportError: cannot import name 'FIVEMIN_CLUSTER_IDS'`.

- [x] **Step 3: Define the two constants**

Replace the `FIVEMIN_PNODE_IDS` definition at `src/surg/preprocessing/schema_5min.py:13` with:

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

- [x] **Step 4: Point the builder at the cluster-set**

In `src/surg/preprocessing/build_5min.py`, change the import at line 29 to bring in **both** names, and change line 48 to:

```python
    lmp_wide = add_loudoun_cluster_columns(lmp_wide, FIVEMIN_CLUSTER_IDS)
```

- [x] **Step 5: De-duplicate the acquisition-side constant**

`src/surg/acquisition/gridstatus_pull.py:31` re-declares the tuple. Import it instead, so the two copies cannot drift (ERRATA E20 — rev1 left them duplicated *and* textually divergent):

```python
from surg.preprocessing.schema_5min import FIVEMIN_PNODE_IDS
```

Delete the local `FIVEMIN_PNODE_IDS = (...)` assignment, then verify there is no import cycle:

```bash
.venv/bin/python -c "
from surg.acquisition.gridstatus_pull import FIVEMIN_PNODE_IDS as a
from surg.preprocessing.schema_5min import FIVEMIN_PNODE_IDS as b
assert a is b
print('OK: single definition,', a)
"
```

Expected: `OK: single definition, (35010365, 35010371, 1356178195, 1356178201)`.

If this raises `ImportError` from a cycle, keep the literal in `gridstatus_pull.py` and instead add a test asserting the two tuples are equal. Report which path you took.

- [x] **Step 6: Extend `EXPECTED_COLUMNS_5MIN` and bump the schema version**

`EXPECTED_COLUMNS_5MIN` in `schema_5min.py` enumerates per-pnode columns. Add the four price components for pnode `1356178201`, matching the existing naming and ordering exactly:

```
congestion_price_rt_1356178201
marginal_loss_price_rt_1356178201
system_energy_price_rt_1356178201
total_lmp_rt_1356178201
```

Read the surrounding block and follow its ordering convention rather than appending blindly.

Then bump `FIVEMIN_SCHEMA_VERSION` (stamped at `build_5min.py:132`, checked at `analysis/panel.py:23`). Extending the expected column set without bumping it leaves the checker unable to distinguish a 3-pnode panel from a 4-pnode one (ERRATA E21).

```bash
grep -n "FIVEMIN_SCHEMA_VERSION" src/surg/preprocessing/schema_5min.py \
  src/surg/preprocessing/build_5min.py src/surg/analysis/panel.py
```

- [x] **Step 7: Update the builder-test fixture to emit four pnodes**

`tests/preprocessing/test_build_5min.py:28,46,96` construct fixtures over the pnode set; they must now emit the four `*_1356178201` columns. This is the real coupling — **not** `test_gridstatus_pull.py:107,131`, whose assertions derive from `len(FIVEMIN_PNODE_IDS)` and adapt on their own (ERRATA E19).

- [x] **Step 8: Run the preprocessing and acquisition tests**

```bash
.venv/bin/python -m pytest tests/preprocessing/ tests/acquisition/ -q 2>&1 | tail -20
```

Expected: PASS, including the new test. Where a count changes from 3 to 4, confirm each change is *correct* rather than adjusting numbers until it goes green.

- [x] **Step 9: Commit (ask the user first)**

```bash
git add src/surg/preprocessing/schema_5min.py src/surg/preprocessing/build_5min.py \
        src/surg/acquisition/gridstatus_pull.py tests/preprocessing/test_build_5min.py \
        tests/acquisition/test_gridstatus_pull.py
git commit -m "feat(preprocessing): add SKFFSCRK as 4th 5-min pnode, split cluster-set from pull-set

FIVEMIN_PNODE_IDS was both the pull-set and the cluster-set, safe only
because they coincided at 3 nodes. Adding SKFFSCRK would have silently
pooled a comparison node into the Loudoun cluster average, contaminating
every cluster-based regression target."
```

---

## Task 6: Add a load-only path to the pull CLI

Account 5 carries `pjm_load` and nothing else. `gridstatus_pull.py` has `--skip-load` but no inverse: line 142 reads `for pid in (pnode_ids or FIVEMIN_PNODE_IDS)`, so an empty `--pnodes` falls back to the full set rather than pulling nothing.

**Files:**
- Modify: `src/surg/acquisition/gridstatus_pull.py`
- Modify: `tests/acquisition/test_gridstatus_pull.py`

**Real interface** (ERRATA E13 — rev1's test code was written against functions that do not exist):

```
pull_gridstatus(client, *, data_root, window_start, window_end,
                pnode_ids=None, skip_load=False)
```

`client` is **positional**. `window_start` / `window_end` take **`datetime`**, not ISO strings. There is **no pytest fixture**: `test_gridstatus_pull.py:20` defines a `FakeClient` **class**, instantiated inline with `rows_by_dataset`, alongside `_load_rows()` / `_lmp_rows()` helpers and `WINDOW_START` / `WINDOW_END` constants. Rev1's expected `TypeError` was really a `NameError`.

- [x] **Step 1: Read the existing test scaffolding**

```bash
sed -n '1,60p' tests/acquisition/test_gridstatus_pull.py
```

Note the exact `FakeClient` constructor signature, the helper names, and how `WINDOW_START`/`WINDOW_END` are built. The tests below use them.

- [x] **Step 2: Write the failing tests**

Add to `tests/acquisition/test_gridstatus_pull.py`, adjusting only the `FakeClient(...)` construction to match what Step 1 showed:

```python
def test_skip_lmp_pulls_load_only(tmp_path):
    """--skip-lmp must issue zero LMP requests and still pull load."""
    client = FakeClient(rows_by_dataset={"pjm_load": _load_rows()})
    pull_gridstatus(
        client,
        data_root=tmp_path,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        skip_lmp=True,
    )
    datasets = [c["dataset"] for c in client.calls]
    assert "pjm_lmp_real_time_5_min" not in datasets
    assert "pjm_load" in datasets


def test_skip_lmp_and_skip_load_together_is_rejected(tmp_path):
    """Pulling neither series is a user error, not a silent no-op."""
    client = FakeClient(rows_by_dataset={})
    with pytest.raises(ValueError, match="nothing to pull"):
        pull_gridstatus(
            client,
            data_root=tmp_path,
            window_start=WINDOW_START,
            window_end=WINDOW_END,
            skip_lmp=True,
            skip_load=True,
        )
```

- [x] **Step 3: Run them to confirm they fail**

```bash
.venv/bin/python -m pytest tests/acquisition/test_gridstatus_pull.py::test_skip_lmp_pulls_load_only -q
```

Expected: FAIL with `TypeError: pull_gridstatus() got an unexpected keyword argument 'skip_lmp'`.

- [x] **Step 4: Add the parameter**

Add `skip_lmp: bool = False` to the signature beside `skip_load` (near line 127), then guard the pnode loop at line 142:

```python
    if skip_lmp and skip_load:
        raise ValueError(
            "skip_lmp and skip_load are both set — nothing to pull"
        )
    if not skip_lmp:
        for pid in (pnode_ids or FIVEMIN_PNODE_IDS):
            ...  # existing loop body, unchanged
```

Keep the existing `if not skip_load:` block as-is.

- [x] **Step 5: Add the CLI flag**

Beside the `--skip-load` argument (line 175):

```python
    p.add_argument("--skip-lmp", action="store_true",
                   help="Pull only the load series, no nodal LMP. Used by the "
                        "dedicated load account, which cannot also carry a "
                        "pnode within the free-tier row cap.")
```

Thread it into the call at line 203: `skip_lmp=args.skip_lmp,`.

- [x] **Step 6: Run the tests**

```bash
.venv/bin/python -m pytest tests/acquisition/test_gridstatus_pull.py -q 2>&1 | tail -10
```

Expected: PASS.

- [x] **Step 7: Confirm the key lookup was not "fixed"**

The module must keep reading the bare `GRIDSTATUS_API_KEY`; per-account override belongs in the launch script. This is load-bearing: one process per account, each seeing a different value in the same variable.

```bash
grep -n "GRIDSTATUS_API_KEY" src/surg/acquisition/*.py
```

Expected: only the unsuffixed name. **No `_1`..`_6` suffix may appear in the module.**

- [x] **Step 8: Commit (ask the user first)**

```bash
git add src/surg/acquisition/gridstatus_pull.py tests/acquisition/test_gridstatus_pull.py
git commit -m "feat(acquisition): add --skip-lmp for the dedicated load account"
```

---

## Task 7: Write the launcher and the usage poller, then smoke-run them

The surviving script at `~/surg-run-logs/surg-gridstatus-backfill-launch.sh` is the pre-loss 3-account version and **cannot run** — it `cd`s to the deleted `.../SURG/surg` path under `set -euo pipefail`. This is a rewrite, and it moves into the repo so it cannot be lost again.

**Files:**
- Create: `scripts/poll_gridstatus_usage.py`
- Create: `scripts/gridstatus_backfill_launch.sh`

- [x] **Step 1: Write the usage poller**

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

- [x] **Step 2: Run it**

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
.venv/bin/python scripts/poll_gridstatus_usage.py
```

Expected: 6 lines with request/row counts, ending `6 distinct accounts.`

This costs **6 requests** (one `/api_usage` call per account). Record the numbers — Task 9 compares against them.

`load_dotenv()` searches upward from the calling file, so run from the repo root.

- [x] **Step 3: Write the launch script**

Create `scripts/gridstatus_backfill_launch.sh`. **The PID collection below is the ERRATA E4 fix** — rev1 ran `launch` inside a command substitution, making each background python a *grandchild* that `wait` could not reap. Every `wait` returned 127 instantly, the script touched `-FAILED` within a second, and because the enclosing `nohup caffeinate -i bash ...` exits with the script, `caffeinate` stopped holding the machine awake during a ~5-hour pull.

```bash
#!/bin/bash
# 5-min full-window backfill: 2023-02-07 -> 2026-06-30, 5 gridstatus.io accounts.
#
# Single-pass, one account per pnode plus a dedicated load account. Account 6
# is held as spare/retry budget and is NOT launched here.
#
# Free tier is 250 requests and 500K rows per account per calendar month, and
# requests are the binding constraint: 177 per pnode, 42 for load.
# See docs/specs/2026-07-30-surg-recovery-design.md § "Quota arithmetic".
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
set -a; source .env; set +a

PY="$REPO_ROOT/.venv/bin/python"
START="${START:-2023-02-07T00:00:00Z}"
END="${END:-2026-06-30T00:00:00Z}"
DATA_ROOT="${DATA_ROOT:-data/raw/gridstatus}"
LOG_DIR="${LOG_DIR:-$HOME/surg-run-logs}"
mkdir -p "$LOG_DIR"

echo "=== backfill launched $(date) ==="
echo "repo=$REPO_ROOT window=$START -> $END data_root=$DATA_ROOT"

PIDS=()
LABELS=()
launch() {  # $1=account index  $2=label  $3...=extra args
  local idx="$1" label="$2"; shift 2
  local keyvar="GRIDSTATUS_API_KEY_${idx}"
  GRIDSTATUS_API_KEY="${!keyvar}" "$PY" -m surg.acquisition.gridstatus_pull \
    --start "$START" --end "$END" \
    --data-root "$DATA_ROOT" "$@" \
    > "$LOG_DIR/surg-gridstatus-backfill-account${idx}.log" 2>&1 &
  PIDS+=("$!")
  LABELS+=("account${idx} (${label})")
  echo "account${idx} pid=${PIDS[-1]} (${label})"
}

launch 1 LOUDOUN      --pnodes 35010365   --skip-load
launch 2 PLEASANTVIEW --pnodes 35010371   --skip-load
launch 3 GOOSECRE     --pnodes 1356178195 --skip-load
launch 4 SKFFSCRK     --pnodes 1356178201 --skip-load
launch 5 LOAD         --skip-lmp

RC=0
for i in "${!PIDS[@]}"; do
  if ! wait "${PIDS[$i]}"; then
    echo "FAILED: ${LABELS[$i]} (pid ${PIDS[$i]})"
    RC=1
  fi
done

echo "=== backfill finished $(date): rc=$RC ==="
if [ "$RC" -eq 0 ]; then
  touch "$LOG_DIR/surg-gridstatus-backfill-DONE"
else
  touch "$LOG_DIR/surg-gridstatus-backfill-FAILED"
fi
```

Deliberate differences from the pre-loss script: repo root derived rather than hardcoded; `.venv/bin/python` explicitly; account 1 injected the same way as the others; `--skip-load` on all four pnode accounts because load has its own; `END` extends to 2026-06-30; SKFFSCRK added; `START`/`END`/`DATA_ROOT`/`LOG_DIR` overridable from the environment so Step 5 can smoke-test without touching real data.

- [x] **Step 4: Make it executable and syntax-check**

```bash
chmod +x scripts/gridstatus_backfill_launch.sh
bash -n scripts/gridstatus_backfill_launch.sh && echo "SYNTAX OK"
```

Expected: `SYNTAX OK`. **`bash -n` checks syntax only — which is exactly how E4 survived into rev1. Step 5 is not optional.**

- [x] **Step 5: Smoke-run the launcher against a 1-day window (ERRATA E5)**

Between here and Task 10's irreversible ~890-request launch, this is the only time the script is actually executed. Cost: ~5 requests, one per account. The env-var overrides added in Step 3 make this a real run of the real script — no edited copy.

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
time env START=2026-06-01T00:00:00Z END=2026-06-02T00:00:00Z \
         DATA_ROOT=/tmp/surg-launch-smoke \
         LOG_DIR=/tmp/surg-launch-smoke-logs \
     bash scripts/gridstatus_backfill_launch.sh
ls -la /tmp/surg-launch-smoke-logs/
```

Required outcome, all four:
1. Five `pid=` lines print.
2. The script **blocks** — wall time is tens of seconds, not under 10s.
3. `rc=0`.
4. `/tmp/surg-launch-smoke-logs/surg-gridstatus-backfill-DONE` exists.

**If it returns in under ~10 seconds, the launcher is broken — that is E4 recurring. Do not proceed to Task 10.**

- [x] **Step 6: Commit (ask the user first)**

```bash
rm -rf /tmp/surg-launch-smoke /tmp/surg-launch-smoke-logs
git add scripts/gridstatus_backfill_launch.sh scripts/poll_gridstatus_usage.py
git commit -m "feat(scripts): version-control the backfill launcher and usage poller

The pre-loss launcher lived only at ~/surg-run-logs/ and hardcoded the
now-deleted SURG/surg path, so it could not run. Rewritten for the
6-account single-pass table: 4 pnode accounts, 1 dedicated load account,
1 spare.

PIDs are collected in the parent shell. The obvious phrasing --
PID=\$(launch ...) -- puts the background process in a subshell, where it
becomes a grandchild that wait cannot reap; every wait returns 127
instantly and the caller reports FAILED within a second while five pulls
run on detached."
```

---

## Execution record — Tasks 1–7 completed 2026-08-07

Code track executed on `main` (not a worktree: `data/` is gitignored, so a
worktree teardown would discard the panels this plan exists to restore).
Commits `e9a6e06 → 74dc229`. Suite went `313 passed, 6 skipped` →
**`328 passed, 5 skipped`, 330 collected**.

**Three defects in this plan, found during execution. Later tasks still
contain the uncorrected text — read these first.**

### X1 — `${PIDS[-1]}` in Task 7 Step 3 is fatal on macOS

Negative array subscripts require bash ≥ 4.2; macOS ships `/bin/bash` 3.2,
where `${PIDS[-1]}` is a hard `bad array subscript` error — fatal under
`set -u`. As written, the launcher would have aborted on the **first**
`launch` call, which is the E4 failure mode this plan was written to fix,
reintroduced by the fix itself. `bash -n` cannot catch it (it is a runtime
expansion), so Task 7 Step 5's smoke-run is what caught it.

The committed script echoes a `local pid=$!` captured before the array
append. This preserves the actual E4 fix — a shell *function* does not
fork, so `$!` and the append still land in the parent shell where `wait`
can reap them.

### X2 — Task 4 Step 3's accounting table under-counts Task 1

The table credits the gpd test chain with "+0 (3 ops, no new test
functions)". It actually adds **6 test functions** — including
`test_gpd_conditional_on_z_cluster_bootstrap_duplicates_rows`, the very
mutation guard Task 1 Step 6 depends on. The plan therefore contradicts
itself: Step 6 requires that test to be newly restored by a chain the
accounting says adds nothing.

Corrected arithmetic from a `313 passed, 6 skipped` baseline:

| Source | Passed | Skipped |
|---|---|---|
| Task 1 — gpd test chain | **+6** | 0 |
| Task 2 — two test chains | +4 | 0 |
| Task 4 — module-level skip removed | +2 | −1 |
| Task 5 — cluster-exclusion guard | +1 | 0 |
| Task 6 — two `--skip-lmp` tests | +2 | 0 |

After Tasks 1–4: **325 passed, 5 skipped, 330 collected** (not the plan's
319 / 324). After Tasks 1–7: **328 passed, 5 skipped**.

### X3 — `/api_usage` polls are free; Task 9's cost table is wrong

Measured 2026-08-07 against live accounts. After the Task 7 Step 5
smoke-run, accounts 1–5 each read exactly `1/250 req, 288/500000 rows`
having pulled one chunk apiece, and **account 6 read `0/250` after being
polled twice**.

So `GET /api_usage` does not count against quota, and the per-chunk
multiplier — the single number Task 9 exists to produce — is exactly
**1.0**. Task 9's table (4 requests on account 6, 14 across all accounts)
overstates cost; the true figures are 2 and 2. A 177-chunk pnode pull
costs 177 requests against the 250 cap, and 356,832 rows against the
500,000 cap (1,239 days × 288 rows/day), both with margin.

**Consequence for Task 9:** its substance is already satisfied by the
Task 7 smoke-run — Step 2 (SKFFSCRK is a valid 5-min `location_id`: 288
rows, `location=SKFFSCRK`), Step 3 (rename map carries all four source
columns `lmp/energy/congestion/loss`), Step 4 (`--skip-lmp` exercised
live on account 5) and Step 5 (multiplier). Only **Step 6**, the
`docs/decisions.md` entry, is outstanding. Do not re-spend requests
re-running a gate that is already green.

### Other execution notes

- **Task 8 Step 1 needs no `sudo`.** `api.pjm.com` already resolves — the
  `/etc/hosts` entry added 2026-05-11 survived the directory loss.
- **Task 3 is armed, not verified.** `5 skipped` proves only that the glob
  now resolves. The first real comparison is Task 8 Step 6.
- **Task 12 Step 2's `while kill -0 <PID>; do sleep 300; done`** exceeds an
  agent Bash call's 600s ceiling; run it detached or poll instead.
- **`test_cluster_columns_exclude_skffscrk` guards the constants, not the
  wiring.** If `build_5min.py:48` ever reverted to `FIVEMIN_PNODE_IDS` the
  test would still pass; only Task 11 Step 3 catches that, ~890 requests
  downstream.

---

## Task 8: Re-pull **and build** the hourly PJM Data Miner 2 panel

Not gridstatus-quota-gated, so this runs in parallel with the code track. Rev1 pulled raw hourly data but **never built the panel**, so its Tasks 11–12 read a file that was never created (ERRATA E7a).

**Files:**
- Uses: `src/surg/acquisition/pull.py` (CLI: `--feed --start --end --group-label --data-root`)
- Uses: `src/surg/acquisition/targets.py` (the locked 11-pnode set)
- Uses: `src/surg/preprocessing/build.py` → writes `data/interim/analysis_panel.parquet`

- [ ] **Step 1: Apply the DNS workaround before anything else**

NU DNS NXDOMAINs `api.pjm.com` while sibling PJM hosts still resolve. Symptom if skipped: `httpx.ConnectError`.

```bash
dig +short api.pjm.com || true
```

If it returns nothing, resolve a sibling host and add an `/etc/hosts` entry. This needs `sudo`, so **ask the user to run it**:

```bash
dig +short www.pjm.com
# then the user runs:  sudo sh -c 'echo "<ip>  api.pjm.com" >> /etc/hosts'
```

Re-check with `dig +short api.pjm.com` before proceeding.

- [ ] **Step 2: Confirm the 11-pnode target set**

```bash
grep -c "Pnode(" src/surg/acquisition/targets.py
```

Expected: `11` — 6 EHV Loudoun-cluster nodes, both Ashburn 35 kV buses, OX and BRISTERS as controls, and DOM zonal.

- [ ] **Step 3: Verify the PJM key with a 1-day pull**

```bash
.venv/bin/python -m surg.acquisition.pull --feed rt_hrl_lmps \
  --start 2026-06-01 --end 2026-06-02 \
  --group-label dom_targets --data-root data/raw
```

Expected: exits 0 and writes a file under `data/raw/`. If it 401s, the `PJM_API_KEY` in `.env` needs re-checking with the user.

- [ ] **Step 4: Launch the full hourly backfill in the background**

The analysis window is locked at `build.py:43-44` — `ANALYSIS_WINDOW_START = 2022-10-02`, `ANALYSIS_WINDOW_END = 2026-05-11` (inclusive start, exclusive end; final included hour is 2026-05-10 23:00 EPT).

```bash
mkdir -p ~/surg-run-logs
nohup caffeinate -i .venv/bin/python -m surg.acquisition.pull --feed rt_hrl_lmps \
  --start 2022-10-02 --end 2026-05-11 \
  --group-label dom_targets --data-root data/raw \
  > ~/surg-run-logs/surg-pjm-hourly-repull.log 2>&1 &
echo "pid=$!"
```

This window **ends 2026-05-11** while the 5-min pull runs to 2026-06-30. That asymmetry is pre-existing and deliberate — the hourly window was locked on 2026-05-12. Do not silently extend it.

Note `pull.py:255` treats `--end` as **inclusive**, so this pulls one day past the exclusive window bound. Harmless — the builder clips — but do not "correct" it (ERRATA E27).

- [ ] **Step 5: Build the hourly panel**

Wait for Step 4 to finish, then read the real flag names:

```bash
.venv/bin/python -m surg.preprocessing.build --help
```

Run the build, then confirm it landed. It writes `data/interim/analysis_panel.parquet` (`build.py:136`) — **not** `data/processed/panel_hourly.parquet`, which appears nowhere in `src/`, `tests/`, `scripts/` or `docs/` outside rev1 (ERRATA E6/E7a).

```bash
ls -la data/interim/analysis_panel.parquet
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/interim/analysis_panel.parquet')
print('rows:', len(df), 'cols:', len(df.columns))
"
```

- [ ] **Step 6: Run the now-armed regression suite**

This is the payoff from Task 3. With the panel on disk, the five previously-skipped regression tests execute for the first time — and `test_tail_risk_curves_pair_bootstrap_equivalence` compares real output against the captured fixtures for the first time ever.

```bash
.venv/bin/python -m pytest tests/regression/ -q -rs 2>&1 | tail -20
```

Expected: PASS. Two failure modes, to be **reported rather than fixed**:
- `Key mismatch ... extra={'resolution'}` → Task 3 Step 3 did not stamp the fixtures. Re-run it.
- Numeric divergence → the re-pulled hourly data differs from the pre-loss pull. That is a **data** finding, feeding Task 13's republication-vs-code discriminator. Do not touch the fixtures to make it green.

- [ ] **Step 7: Record the Ashburn coverage question**

The 2026-07-30 record flagged `n=17,448` for Ashburn against `31,536` for the other pnodes, marked "verify before it ships in F7".

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/interim/analysis_panel.parquet')
for c in sorted(c for c in df.columns if 'ashburn' in c or 'cluster_mean' in c):
    print(f'{c}: {df[c].notna().sum()} non-null of {len(df)}')
"
```

Do **not** treat a short Ashburn series as a pull failure without checking — it may be genuine partial coverage of that bus.

---

## Task 9: Pre-launch validation gate

177 requests against a 250/month cap means one botched launch costs a calendar month, with only account 6 as spare for four pnodes. This gate proves the pipeline end-to-end before the real launch.

**Exact cost — 4 requests on account 6, 10 across all accounts.** Rev1 stated this four different ways (~2, ~2, ~3, 2–3), which made the Step 5 verification unfalsifiable (ERRATA E28). The breakdown:

| Step | Account 6 | All accounts |
|---|---|---|
| 1 — poll usage | 1 | 6 (one `/api_usage` per account) |
| 2 — one LMP pnode-week, `--skip-preflight` | 1 | 1 |
| 4 — one load week, `--skip-preflight` | 1 | 1 |
| 5 — poll usage again | 1 | 6 |
| **Total** | **4** | **14** |

Only account 6 is touched by data requests; the polls are read-only metadata calls that nonetheless count against each account's own quota. Accounts 1–5 therefore each spend 2 requests (two polls) and remain effectively at full budget for Task 10.

**This task is undated.** Rev1 tied it to "before 8pm EDT 2026-07-31"; that deadline passed unused. The gate's value is being before the **launch**, not before any reset.

**Depends only on Tasks 6 and 7.** It does not depend on Tasks 1–5 or 8.

- [ ] **Step 1: Read live quota**

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
.venv/bin/python scripts/poll_gridstatus_usage.py
```

Record all six lines. Expected: `current_usage_period_end` of `2026-09-01T00:00:00Z` on every account (ERRATA E16). Accounts 1–5 should be at or near `0/250`; **account 6 may show usage from this gate and does not block anything** — it is the spare and is never launched in Task 10.

- [ ] **Step 2: Pull one short LMP window on account 6**

One pnode, one 7-day chunk — a single request. `--skip-preflight` avoids an extra `/api_usage` call on top of the data request (ERRATA E14).

```bash
set -a; source .env; set +a
GRIDSTATUS_API_KEY="$GRIDSTATUS_API_KEY_6" .venv/bin/python -m surg.acquisition.gridstatus_pull \
  --start 2026-06-01T00:00:00Z --end 2026-06-08T00:00:00Z \
  --pnodes 1356178201 --skip-load --skip-preflight \
  --data-root /tmp/surg-validation-gate
```

Expected: exits 0, writes one chunk file. **This is the first live proof that SKFFSCRK (1356178201) is a valid `location_id` for this dataset** — the spec asserts it, but SKFFSCRK has never been pulled at 5-min resolution.

- [ ] **Step 3: Verify the schema and rename map against the pulled chunk**

```bash
.venv/bin/python -c "
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

Expected: roughly 2,013 rows for one pnode-week, and the four source columns `lmp/energy/congestion/loss` that the rename map maps onto `total_lmp_rt / system_energy_price_rt / congestion_price_rt / marginal_loss_price_rt`. **A missing source column means the rename map is stale and must be fixed before Task 10.**

- [ ] **Step 4: Prove the load-only path**

Each Bash call is a fresh shell, so `.env` must be re-sourced (ERRATA E14 — rev1 repeated the key prefix without it, so it expanded empty and the only live test of the Task 6 code path failed for an unrelated reason).

```bash
set -a; source .env; set +a
GRIDSTATUS_API_KEY="$GRIDSTATUS_API_KEY_6" .venv/bin/python -m surg.acquisition.gridstatus_pull \
  --start 2026-06-01T00:00:00Z --end 2026-06-08T00:00:00Z \
  --skip-lmp --skip-preflight \
  --data-root /tmp/surg-validation-gate
```

Expected: exits 0, writes a `pjm_load` chunk containing a `dom` column, and issues **zero** LMP requests. This is the only live test of the Task 6 code path before it carries account 5.

- [ ] **Step 5: Confirm the gate's true cost**

```bash
.venv/bin/python scripts/poll_gridstatus_usage.py | grep KEY_6
```

Expected: **exactly 4 requests above the Step 1 reading** (Step 1's own poll, the two data pulls, and this poll — see the cost table above). 5 or 6 is tolerable slack.

**Anything above ~8 means chunking is wrong and each logical request is costing more than one API call.** That same multiplier applied to a 177-request pnode pull would blow the 250 cap. Stop and diagnose before Task 10 — this is the single number the gate exists to produce.

- [ ] **Step 6: Record the result in `docs/decisions.md`**

Append a dated entry noting: the gate ran; whether SKFFSCRK is a valid 5-min `location_id`; the rename map verified against live columns; `--skip-lmp` verified; and the measured request cost. Follow the file's existing entry conventions.

- [ ] **Step 7: Commit (ask the user first)**

```bash
rm -rf /tmp/surg-validation-gate
git add docs/decisions.md
git commit -m "docs(decisions): pre-launch validation gate result"
```

---

## Task 10: Launch the 5-min full-window pull

**Prerequisites, all four:** Task 5 (4-pnode constants), Task 6 (`--skip-lmp`), Task 7 Step 5 (launcher smoke-run passed **and blocked**), Task 9 (gate green).

- [ ] **Step 1: Confirm quota**

```bash
.venv/bin/python scripts/poll_gridstatus_usage.py
```

Required, all three:

1. `current_usage_period_end` is `2026-09-01T00:00:00Z` on **all six** accounts.
2. Accounts **1–5** each show **≤ 10 requests used** and **≥ 230 remaining**.
3. Account 6 is **unconstrained** — it is the spare and is never launched.

**Do not require accounts 1–5 to read `0/250`.** By this point each has legitimately spent ~4–5 requests: the Task 7 Step 2 poll, its own pull in the Task 7 Step 5 smoke-run, and the Task 9 Step 1 and Step 5 polls. Rev1 demanded `0/250` because it had no launcher smoke-run to spend them; demanding it here would make a correct run read as an anomaly — the same failure mode as E8/E9, and E16 recurring on the other half of the account table.

Headroom is not in question: 177 + ~5 is far below 250.

Budget: 177 LMP requests per pnode (1,239 days ÷ 7 = 177.0 exactly) and **42** load requests (`ceil(1239/30) = 42`; `chunking.py:81` is a strict ceiling). Rev1 stated 41, so a correct run would have read as an anomaly (ERRATA E9).

- [ ] **Step 2: Launch**

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
nohup caffeinate -i bash scripts/gridstatus_backfill_launch.sh \
  > ~/surg-run-logs/surg-gridstatus-backfill.log 2>&1 &
echo "launcher pid=$!"
```

The pre-loss equivalent ran roughly 5 hours.

- [ ] **Step 3: Check progress after ~15 minutes**

```bash
tail -3 ~/surg-run-logs/surg-gridstatus-backfill-account*.log
.venv/bin/python scripts/poll_gridstatus_usage.py
```

Expected: all five logs advancing, request counts climbing at similar rates. An account stalled at 0 while others climb means that process died — read its log rather than waiting.

- [ ] **Step 4: If an account fails, retry it individually**

The pull **is** resumable — `chunk_exists` skips completed chunks. But `check_quota` defaults to `min_remaining_rows=430_000` and a full pnode pull is ~350K rows, so the first launch passes preflight and **any retry on that account aborts** with ~150K remaining (ERRATA E15).

Re-run the single failed account with its original `--pnodes` plus `--skip-preflight`:

```bash
set -a; source .env; set +a
GRIDSTATUS_API_KEY="$GRIDSTATUS_API_KEY_<N>" .venv/bin/python -m surg.acquisition.gridstatus_pull \
  --start 2023-02-07T00:00:00Z --end 2026-06-30T00:00:00Z \
  --pnodes <THAT_ACCOUNTS_PNODE> --skip-load --skip-preflight \
  --data-root data/raw/gridstatus
```

Do **not** lower `min_remaining_rows` in source. Do **not** burn account 6 unless that account's own 250-request budget is genuinely exhausted.

- [ ] **Step 5: Confirm completion**

```bash
ls ~/surg-run-logs/surg-gridstatus-backfill-{DONE,FAILED} 2>/dev/null
.venv/bin/python scripts/poll_gridstatus_usage.py
```

Expected: `...-DONE` exists. Per-account usage near 177 requests for pnode accounts and 42 for load, all under 250.

---

## Task 11: Rebuild the 5-min panel

Every path and flag below is the real one. Rev1's were wrong throughout (ERRATA E6).

- [ ] **Step 1: Build**

`build_5min.py:113-116` requires `--start` and `--end`, and `--output` is a **file** path. Rev1 wrote `--out data/processed`, a directory, with neither window flag.

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
.venv/bin/python -m surg.preprocessing.build_5min --help
.venv/bin/python -m surg.preprocessing.build_5min \
  --data-root data/raw/gridstatus \
  --start 2023-02-07 --end 2026-06-30 \
  --output data/interim/analysis_panel_5min.parquet
```

If `--help` shows different flag names, use what it prints and record the discrepancy.

- [ ] **Step 2: Verify shape — the row count must NOT scale with the fourth pnode**

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/interim/analysis_panel_5min.parquet')
print('rows:', len(df), 'cols:', len(df.columns))
for pid in (35010365, 35010371, 1356178195, 1356178201):
    print(pid, '->', len([c for c in df.columns if str(pid) in c]), 'columns')
"
```

Expected: rows near **350,789** — the panel is wide, one row per 5-min timestamp, one column *group* per pnode. SKFFSCRK adds columns, not rows. A count scaling toward ~470K means the builder emitted long format. Each pnode should show the same column count.

- [ ] **Step 3: Verify the cluster columns exclude SKFFSCRK**

This is the live check on correction **C2**. Read what `add_loudoun_cluster_columns` actually names its outputs first and correct the column name below if it differs.

```bash
.venv/bin/python -c "
import pandas as pd, numpy as np
df = pd.read_parquet('data/interim/analysis_panel_5min.parquet')
cl = [f'congestion_price_rt_{p}' for p in (35010365, 35010371, 1356178195)]
rec = df[cl].mean(axis=1).dropna()
got = df.loc[rec.index, 'congestion_price_rt_cluster_mean']
assert np.allclose(rec, got), 'cluster mean does not match the 3-node set'
four = df[cl + ['congestion_price_rt_1356178201']].mean(axis=1).dropna()
assert not np.allclose(four, df.loc[four.index, 'congestion_price_rt_cluster_mean']), \
    'cluster mean matches the 4-node average — SKFFSCRK leaked in'
print('OK: cluster mean is over the 3 Loudoun nodes, SKFFSCRK excluded')
"
```

Expected: `OK: cluster mean is over the 3 Loudoun nodes, SKFFSCRK excluded`.

- [ ] **Step 4: Verify load coverage**

The column is `dom_load_mw`, not `dom` — `loaders_5min.py:40` renames on load (ERRATA E6).

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/interim/analysis_panel_5min.parquet')
d = df.dropna(subset=['dom_load_mw'])
print('load coverage:', d['interval_start_utc'].min(), '->', d['interval_start_utc'].max())
"
```

Expected: begins **2023-02-07** (the documented `pjm_load` start) and runs to 2026-06-30.

- [ ] **Step 5: Commit any builder fixes (ask the user first)**

```bash
git add -A src/ tests/
git commit -m "fix(preprocessing): 5-min panel builder corrections found against re-pulled data"
```

Skip if the builder needed no changes. The panel itself is gitignored and is not committed.

---

## Task 12: Re-run the 5-min analysis

- [ ] **Step 1: Launch**

The flag is `--out-root`, not `--out` (`run_5min.py:116`), and the panel default is `data/interim/analysis_panel_5min.parquet`.

```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/surg
nohup caffeinate -i .venv/bin/python -m surg.analysis.run_5min \
  --panel data/interim/analysis_panel_5min.parquet \
  --out-root outputs/fivemin_extended \
  > ~/surg-run-logs/surg-run5min-extended.log 2>&1 &
echo "pid=$!"
```

The pre-loss run took **9–10 hours** at the pre-registered `--n-boot 1000` / `--qr-n-boot 500`.

- [ ] **Step 2: Wait for completion, then check the cluster guard**

Gate this on the job actually finishing — rev1 grepped the log immediately, where the check passes trivially at t=0 (ERRATA E23). Substitute the pid printed in Step 1.

```bash
while kill -0 <PID> 2>/dev/null; do sleep 300; done
echo "run finished"
grep -n "too few unique clusters" ~/surg-run-logs/surg-run5min-extended.log \
  && echo "GUARD FIRED — see Task 13 Step 4" || echo "OK: guard did not fire"
tail -20 ~/surg-run-logs/surg-run5min-extended.log
```

Chain op7's guard raises below 10 unique clusters among exceedances. If it fires, the run dies rather than producing numbers.

- [ ] **Step 3: Confirm outputs exist, and that figures are labelled 5-min**

```bash
find outputs/fivemin_extended -name '*.json' | head -20
.venv/bin/python -c "
import json, glob
for f in sorted(glob.glob('outputs/fivemin_extended/tail_risk_curves/*.json')):
    d = json.load(open(f))
    if 'pnode_label' in d:
        print(f.split('/')[-1], '-> resolution =', d.get('resolution', 'MISSING'))
"
```

Expected: every per-pnode result carries `resolution = 5-min`. This is the live confirmation that the Task 2 merge fixed the hardcoded `"hourly"` figure label — the defect that made every pre-loss 5-min PNG say "hourly".

---

## Task 13: Verify the restoration against recorded targets

The two panels are separate targets and **must not be checked against each other**. Every row states its resolution.

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

**Do not assume a divergence is a code defect.** Use this discriminator before hunting through code:

- Compare the **raw** per-pnode series (mean, p50, p95, row count) for the three original pnodes against their recorded aggregates. If the raw series shifted in the same direction and rough magnitude as the derived statistics, suspect **data revision**.
- If the raw series match but only derived statistics move, suspect **code**.

State which the evidence supports for every divergence.

**On republication, state only what was measured.** The 99.07% figure is **cross-source** agreement between gridstatus and PJM on a single 3-day window. It is *not* a measure of how much gridstatus's own warehoused history drifts between two pulls — the quantity this step actually needs, which was never measured. Note also the direction: `gridstatus-api-constraints.md:130-133` records that **our** stored series is `version_nbr=1` (as-first-reported) and **gridstatus** carries the later-republished value. Rev1 stated this backwards (ERRATA E11). Drop the mechanism claim; the raw-vs-derived discriminator carries this step on its own.

- [ ] **Step 2: Identify the price variable behind the hourly correlation targets, then check them**

`decisions.md:4030-4032` records four numbers with **no variable named**: Ashburn TX1 p99 `$611.37` / 4.71% of hours > $100, SKFFSCRK `$96.13` / 0.96%, SKFFSCRK–cluster corr `+0.870`, Ashburn–cluster corr `+0.209`. `total_lmp_rt_*` columns exist alongside `congestion_price_rt_*`, so guessing returns a plausible number that gets logged as a restoration failure — this fails *silently*, and the project has been bitten by exactly this congestion/total_lmp ambiguity twice before (ERRATA E10).

**Do not guess. Compute both and let the match identify the variable.**

Two constraints on how (ERRATA E7b): the persisted hourly panel contains **zero** `congestion_price_rt_<pnode_id>` columns — `build.py:62` collapses per-pnode series into cluster aggregates and discards them. So compute from the **pre-aggregation wide frame** (`pivot_lmp_long_to_pnode_columns` output), not `analysis_panel.parquet`. And: **do not add per-pnode columns to `EXPECTED_COLUMNS`.** Doing so bumps `SCHEMA_VERSION` and invalidates every fixture in `tests/regression/hourly_reference/`.

This is `build.py:60-61` verbatim — the wide frame as it exists one line before `add_loudoun_cluster_columns` and the rename map collapse it.

```bash
.venv/bin/python - <<'PY'
from pathlib import Path

from surg.preprocessing.loaders import load_rt_hrl_lmps
from surg.preprocessing.features import pivot_lmp_long_to_pnode_columns

SKF = 1356178201
CLUSTER = (35010365, 35010371, 1356178195, 1356178171, 1356178181, SKF)

# build.py:60-61 — long -> wide, before any aggregation or renaming.
lmp_long = load_rt_hrl_lmps(Path("data/raw"))
wide = pivot_lmp_long_to_pnode_columns(lmp_long)

for var in ("congestion_price_rt", "total_lmp_rt"):
    cols = [f"{var}_{p}" for p in CLUSTER]
    missing = [c for c in cols if c not in wide.columns]
    if missing:
        print(f"{var}: MISSING {missing}")
        continue
    skf = wide[f"{var}_{SKF}"]
    holdout = [c for c in cols if str(SKF) not in c]
    print(f"--- {var} ---")
    print(f"  SKFFSCRK p99            : {skf.quantile(0.99):.2f}")
    print(f"  SKFFSCRK pct > $100     : {(skf > 100).mean() * 100:.2f}%")
    print(f"  corr vs 6-node cluster  : {skf.corr(wide[cols].mean(axis=1)):.3f}")
    print(f"  corr vs 5-node held out : {skf.corr(wide[holdout].mean(axis=1)):.3f}")
PY
```

Read the result as follows:

- Whichever variable returns SKFFSCRK p99 ≈ **$96.13** with ≈ **0.96%** above $100 **is** the variable behind the recorded targets. The two are internally consistent (p99 = $96.13 implies just under 1% above $100), so the pair identifies the variable on its own.
- The `+0.870` row is then pass/fail against the **6-node** cluster figure for that variable; the 6-node pooling is retained, so it is reproducible.
- The held-out figure is a **disclosure diagnostic** — SKFFSCRK is inside the cluster it is correlated against, so part of +0.870 is self-correlation. The 6-node figure stays primary.
- Repeat for Ashburn TX1 to check `$611.37` / 4.71% / `+0.209`.

Record the identified variable explicitly in the Step 5 write-up so this ambiguity never recurs.

- [ ] **Step 3: Hourly rows, with status**

| Quantity | Expected | Status |
|---|---|---|
| Ashburn TX1 p99 vs SKFFSCRK p99 | $611.37 vs $96.13 | **Diagnostic** — the `n=17,448` vs `31,536` coverage question is open, and a quantity with an open coverage question is a weak regression target |
| SKFFSCRK–cluster vs Ashburn–cluster corr | +0.870 vs +0.209 | **Pass/fail** once Step 2 identifies the variable |

Also note what **cannot** be checked: Ashburn TX1 is not in the 5-min pull, so the Ashburn-vs-SKFFSCRK comparison cannot be evaluated at 5-min resolution. Its absence after a gridstatus-only pull is **expected, not a restoration failure**.

- [ ] **Step 4: Report the live cluster count for the op7 guard**

```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/interim/analysis_panel_5min.parquet')
f = df[df['passes_proposal_filter'].fillna(False).astype(bool)]
print('unique night_island_id in filter:', f['night_island_id'].nunique())
"
```

Expected: comfortably ≥10. Below 10 and the guard fires, so `run_gpd(cluster_col=...)` cannot run on that subset — report it as a finding.

- [ ] **Step 5: Write the verification entry**

Append a dated entry to `docs/decisions.md` recording every row above as reproduced or diverged with observed values, the price variable identified in Step 2, the SKFFSCRK characterisation, and — for each divergence — whether the evidence points to data revision or code. Follow the file's existing conventions.

- [ ] **Step 6: Commit (ask the user first)**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): Plan B restoration verification against recorded targets"
```

---

## Task 14: Document the SKFFSCRK split and close the three open rulings

Correction **C3**, resolved by the user 2026-07-31. This documents the interpretation and discloses the self-correlation — it changes no aggregation.

- [ ] **Step 1: Assemble the evidence**

```bash
grep -n "SKFFSCRK\|1356178201" docs/decisions.md src/surg/preprocessing/build.py \
  src/surg/acquisition/targets.py | head -30
```

Expected: the locked n=11 table at `decisions.md:158-170` (cluster tier — this range, not rev1's `157-167`, which excluded the OX/BRISTERS rows the argument relies on; ERRATA E25), the 6-node pooling decision at `:298`, and the ~$3/MWh tightness note at `:151`.

- [ ] **Step 2: Write the interpretation into `docs/decisions.md`**

Record, as a dated entry: SKFFSCRK is **geographically rural but electrically coupled** — same 500 kV EHV network, same congestion pocket, within ~$3/MWh mean congestion of the cluster. Include both correlations from Task 13 Step 2, with the 6-node figure primary and the held-out figure disclosed beside it. State that the 6-node pre-registered pooling is **retained unchanged**, and that SKFFSCRK sits inside the hourly cluster and outside the 3-node 5-min cluster-set by design.

Note that `decisions.md:4030` itself writes "SKFFSCRK (**rural**)" — the rural framing traces to the original analysis, not to the July recovery spec.

Frame the substantive point plainly: a geographically-rural node tracking the urban cluster this closely is **evidence that congestion in this pocket is network-wide rather than localized to where the data centers physically sit**, reinforcing the standing finding that the 2026 escalation must not be attributed to data centers.

Do **not** describe this as a contradiction or an unresolved question — it is a documented interpretation.

- [ ] **Step 3: Close all three rulings in the research record**

Rev1 said to log all three here but its step described only the SKFFSCRK write-up, leaving `decisions.md:4137` still reading **"Status: OPEN. Recommendation is NOT to filter; the user has not ruled."** — the research record contradicting the plan (ERRATA E17). Verified still OPEN on 2026-08-07.

Append all three closures, and **edit `decisions.md:4137` itself** so the OPEN status is resolved rather than merely superseded further down the file:

- **SKFFSCRK role — CLOSED.** Pulled as the 4th 5-min pnode; hourly 6-node cluster pooling retained as pre-registered. Geographically rural, electrically coupled.
- **Spike filtering — CLOSED: do not filter.** The ~3,193-spike class stays in. These are the scarcity events the research question targets; removing them would remove the signal. This also keeps every recorded Phase 7 target reproducible, since all were computed unfiltered. Open since May, ruled by the user 2026-07-31.
- **Hourly window — CLOSED: unchanged at 2022-10-02 → 2026-05-11.** Not extended to match the 5-min window. It is pre-registered, hourly findings are lower-priority, and the 5-min panel already covers 2026 at higher resolution.

```bash
grep -n "Status: OPEN" docs/decisions.md || echo "GOOD: no OPEN rulings remain"
```

- [ ] **Step 4: Commit (ask the user first)**

The message must not say "contradiction" — Step 2 forbids that framing, and rev1's own commit message used it (ERRATA E26).

```bash
git add docs/decisions.md
git commit -m "docs(decisions): SKFFSCRK geographic/electrical split, held-out correlation, three closures

SKFFSCRK is geographically rural and electrically coupled; both
descriptions hold and the 6-node pre-registered pooling is retained.
Discloses the held-out correlation beside the primary figure, since
SKFFSCRK sits inside the cluster it is correlated against.

Closes the SKFFSCRK-role, spike-filtering and hourly-window rulings."
```

---

## Task 15: Push

- [ ] **Step 1: Confirm no Claude attribution**

```bash
git log origin/main..main --format='%an|%ae|%(trailers)' | grep -iE "claude|anthropic|co-authored" || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 2: Ask the user for permission, then push**

Per the standing rule, every push is a separate explicit ask.

```bash
git push origin main
git rev-list --count origin/main..main   # expect 0
```

---

## Task dependencies

Rev1 left these unstated, and several tasks touch the same files (ERRATA E22).

```
1 ──┐
2 ──┼─→ 3 ─→ 4               (4 needs both 1 and 2; 3 must follow 2)
5 ──┐
6 ──┴─→ 7 ─→ 9 ─→ 10 ─→ 11 ─→ 12 ─┐
                                   ├─→ 13 ─→ 14 ─→ 15
8 ─────────────────────────────────┘
```

- **Tasks 5 and 6** both edit `gridstatus_pull.py` and `test_gridstatus_pull.py` — serialize them.
- **Tasks 9, 13 and 14** all append to `docs/decisions.md` — serialize them.
- **Task 8** (hourly) runs in parallel with everything and joins only at Task 13. It must not gate the 5-min track.
- **Task 3** must follow Task 2: it is what unmasks the `resolution` key mismatch.
- **Task 10** must follow Task 7 Step 5 — an unexecuted launcher is the E4/E5 failure mode.

---

## Verified clean — do not re-audit

Confirmed by the 2026-07-31 four-agent audit against live files, and re-confirmed where it mattered on 2026-08-07: all 11 pnode IDs against `decisions.md:158-170` and `targets.py:32-45`; every Task 13 regression target transcribed exactly with correct hourly/5-min assignment; 1,239 days; 1,239 × 288 = 356,832; 350,789 rows; 177 LMP requests/pnode; every account-table cell inside both caps; both window date pairs; the 12-figure count (F1–F11 + F4b; F4c never existed); `replay.py`'s CLI and match/skip semantics; and every line-number citation in rev1.

Two things the audit banked that this revision **did** re-check, because its chain inventory proved incomplete: the gpd and test_gpd chains (dry-run: `applied=8` and `applied=3`, both clean) and the full chain inventory (four tail_risk_curves chains, not two).

`c4a64e7`, cited in rev1's Task 11 preamble, is not a valid object in this repo — lost in the deletion. Removed here (ERRATA E24).

---

## Open items carried forward, not settled by this plan

Advisor calls, not recovery work:

- **Which QR specification is primary** — pre-registered or load-controlled. The two disagree in sign on the headline 2024 τ=0.90 row. Largest open research question; it gates interpretation, not execution.
- Whether identifying the January 2026 driver belongs in sub-q1.
- **Whether to acquire a non-DOM control pnode.** Every pnode in both panels sits inside DOM, so the system-wide component of the 2026 escalation cannot be separated from a Dominion-specific one. C3 sharpens this: a geographically-rural node tracking the cluster is suggestive of a system-wide component but cannot settle it from inside DOM alone.

**Standing sub-q2 warning:** projecting 2026 exceedance rates forward would extrapolate an unidentified, possibly transient, possibly system-wide shift as though it were data-center load growth.

**After Plan B:** `superpowers:writing-plans` for the **12-figure** build (F1–F11 plus F4b). That design is done and user-reviewed — do not re-brainstorm it.

---

## Execution record — Tasks 8–15, completed 2026-08-07/08

- **Task 8** done 2026-08-07 morning: hourly re-pull (rc=1 on a final
  ReadTimeout after all files wrote; aux feeds "ALL THREE DONE"), panel built
  (31,608 rows), regression suite armed and run — five fixtures re-blessed at
  the corrected window (`ed24770`; pre-loss panel had silently started
  2022-10-05). See the 2026-08-07 decisions entries.
- **Task 9** done (substance via Task 7 smoke-run per X3; decisions entry
  `64b363f`).
- **Task 10** done: launched 11:10:16 EDT, finished 17:43:55 EDT (6h33m),
  rc=0, zero error/retry lines, 708 LMP + 42 load parquets, full window
  verified on disk.
- **Task 11** done: panel 352,467 rows × 31 cols (was 350,789 — data
  revision, see Task 13). Two plan corrections: the Step 1 build command
  needs Z-suffixed ISO-UTC dates (bare dates crash tz-naive vs tz-aware),
  and `write_panel` lacked the `schema_version` kwarg `build_5min.py:132`
  passes — fixed test-first in `eafcf1b`. Cluster-exclusion (C2) live check
  passed.
- **Task 12** done: 19:12 → 05:58 EDT (**10h46m**, over the 9–10h estimate;
  first QR label alone took 2h22m). Guard silent (641 islands). All outputs
  present; every tail-risk JSON stamped `resolution: "5-min"`.
- **Task 13** done: full verification table + discriminator verdict (data
  revision, not code) in the 2026-08-08 decisions entry. Both 2024 τ=0.90
  z_slopes reproduce to four decimals. Steps 2–3's hourly variable
  identification had already closed via `67b9f08`.
- **Task 14** done earlier via `67b9f08` (before this record's tasks — the
  hourly wide-frame data needed for its correlations was available from the
  morning re-pull).
- **Task 15**: pending user permission at time of writing.
