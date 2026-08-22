# SURG Recovery Plan A — Repo Restoration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the SURG repository to its 2026-07-30 pre-loss code and documentation state, with a passing test suite, without requiring any API keys or data.

**Architecture:** Graft the two recovered git branches onto `main` (rebase + fast-forward, preserving individual commits), then reconstruct the transcript-only files by replaying recorded `Write`/`Edit` chains from the recovery archive. A small replay tool lives in the archive, not the repo, because it is recovery scaffolding rather than project code.

**Tech Stack:** Python 3.12, `uv` for the virtualenv, pytest, git.

**Covers spec phases:** 4 (graft), 2 (acquisition layer), 5 (July preprocessing), 6 (research record). Spec phases 1, 3, 7, 8 are Plan B — they need API keys, quota, and compute.

**Source of truth:** `docs/specs/2026-07-30-surg-recovery-design.md`
**Recovery archive:** `~/surg-recovery-2026-07-30/` (referred to below as `$ARCHIVE`)

---

## File Structure

| Path | Responsibility | Origin |
|---|---|---|
| `$ARCHIVE/replay.py` | Replays a recorded edit chain onto a file. Recovery scaffolding — **not** committed to the repo | New (Task 2) |
| `src/surg/acquisition/gridstatus_client.py` | HTTP client for the gridstatus hosted API | Restore (Task 5) |
| `src/surg/acquisition/gridstatus_pull.py` | Chunked pull CLI; reads `GRIDSTATUS_API_KEY` | Restore (Task 6) |
| `src/surg/acquisition/gridstatus_validate.py` | Post-pull validation of cached chunks | Restore (Task 7) |
| `src/surg/preprocessing/schema_5min.py` | Column schema for the 5-min panel | Restore (Task 8) |
| `src/surg/preprocessing/loaders_5min.py` | Loads gridstatus chunks, renames to PJM conventions | Restore (Task 9) |
| `src/surg/preprocessing/build_5min.py` | Builds the 5-min analysis panel | Restore (Task 10) |
| `src/surg/analysis/run_5min.py` | 5-min analysis entrypoint | Restore (Task 11) |
| `docs/decisions.md` | Research record — pre-registrations and results | Extend (Task 13) |
| `docs/reference/pjm-manuals/pjm-lmp-formation.md` | PJM LMP formation reference (workstream C) | Restore (Task 13) |

Note the deliberate absence of `scripts/plot_subq1_results.py`. Per the spec it is superseded by the figure-set design and is rebuilt in a later plan, not restored here.

---

## Task 1: Environment and baseline

The `.venv` died with the directory. Nothing can be verified until it exists.

**Files:**
- Create: `.venv/` (gitignored)

- [ ] **Step 1: Create the virtualenv and install the package**

```bash
cd ~/docs/NU/Freshman_Year/Summer_2026/surg
uv venv --python 3.12
uv pip install -e '.[dev]'
```

- [ ] **Step 2: Run the existing suite to establish a baseline**

Run: `.venv/bin/pytest -q`
Expected: all tests pass. Record the count — it is the baseline every later task compares against.

If anything fails here, **stop**. A failure at this point is a pre-existing problem in `origin/main`, not something this plan introduced, and diagnosing it later will be much harder.

- [ ] **Step 3: Confirm `.venv` is ignored**

Run: `git status --short`
Expected: no `.venv` entry. If it appears, add `.venv/` to `.gitignore` and commit that alone.

---

## Task 2: Build the edit-chain replay tool

41 recorded chains, some with 20+ edits. Replaying by hand is error-prone and unreviewable. This tool makes every later restoration task mechanical and auditable.

It lives in the archive, not the repo — it is scaffolding for this recovery, not project code.

**Files:**
- Create: `$ARCHIVE/replay.py`
- Test: `$ARCHIVE/test_replay.py`

- [ ] **Step 1: Write the failing test**

```python
# ~/surg-recovery-2026-07-30/test_replay.py
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent

def _chain(tmp_path, ops):
    p = tmp_path / "chain.json"
    p.write_text(json.dumps({"path": "x.py", "ops": ops}))
    return p

def test_replays_write_then_edit(tmp_path):
    chain = _chain(tmp_path, [
        {"op": "Write", "content": "a = 1\nb = 2\n"},
        {"op": "Edit", "old_string": "b = 2", "new_string": "b = 3", "replace_all": False},
    ])
    dest = tmp_path / "out.py"
    r = subprocess.run([sys.executable, str(HERE / "replay.py"),
                        str(chain), str(dest)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert dest.read_text() == "a = 1\nb = 3\n"

def test_skips_unmatched_edit_and_reports_nonzero(tmp_path):
    chain = _chain(tmp_path, [
        {"op": "Write", "content": "a = 1\n"},
        {"op": "Edit", "old_string": "zzz", "new_string": "qqq", "replace_all": False},
    ])
    dest = tmp_path / "out.py"
    r = subprocess.run([sys.executable, str(HERE / "replay.py"),
                        str(chain), str(dest)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "SKIP" in r.stdout
    assert dest.read_text() == "a = 1\n"

def test_ambiguous_edit_is_skipped_not_guessed(tmp_path):
    chain = _chain(tmp_path, [
        {"op": "Write", "content": "x\nx\n"},
        {"op": "Edit", "old_string": "x", "new_string": "y", "replace_all": False},
    ])
    dest = tmp_path / "out.py"
    r = subprocess.run([sys.executable, str(HERE / "replay.py"),
                        str(chain), str(dest)], capture_output=True, text=True)
    assert r.returncode == 1
    assert "ambiguous" in r.stdout
    assert dest.read_text() == "x\nx\n"

def test_base_mode_starts_from_existing_file(tmp_path):
    chain = _chain(tmp_path, [
        {"op": "Edit", "old_string": "hello", "new_string": "goodbye", "replace_all": False},
    ])
    dest = tmp_path / "out.py"
    dest.write_text("hello world\n")
    r = subprocess.run([sys.executable, str(HERE / "replay.py"),
                        str(chain), str(dest), "--from-base"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert dest.read_text() == "goodbye world\n"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/surg-recovery-2026-07-30 && ~/docs/NU/Freshman_Year/Summer_2026/surg/.venv/bin/pytest test_replay.py -q`
Expected: FAIL — `replay.py` does not exist.

- [ ] **Step 3: Write the implementation**

```python
#!/usr/bin/env python3
"""Replay a recorded Write/Edit chain onto a target file.

Exit code 0 means every Edit applied. Exit code 1 means at least one was
skipped — the output file is still written, but it is NOT a faithful
restoration and the skipped hunks must be reconciled by hand.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def replay(chain_path: Path, dest: Path, from_base: bool) -> int:
    data = json.loads(chain_path.read_text())
    ops = data["ops"]

    if from_base:
        text = dest.read_text()
        start = 0
    else:
        writes = [i for i, o in enumerate(ops) if o["op"] == "Write"]
        if not writes:
            print(f"ERROR: no Write baseline in {chain_path.name}; use --from-base")
            return 2
        last = writes[-1]
        text = ops[last]["content"]
        start = last + 1

    applied = skipped = 0
    for op in ops[start:]:
        if op["op"] != "Edit":
            continue
        old, new = op["old_string"], op["new_string"]
        count = text.count(old)
        if count == 0:
            print(f"  SKIP (no match): {old[:70]!r}")
            skipped += 1
            continue
        if count > 1 and not op.get("replace_all"):
            print(f"  SKIP (ambiguous, {count} matches): {old[:70]!r}")
            skipped += 1
            continue
        text = text.replace(old, new) if op.get("replace_all") else text.replace(old, new, 1)
        applied += 1

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text)
    print(f"{dest}: applied={applied} skipped={skipped}")
    return 1 if skipped else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("chain", type=Path)
    ap.add_argument("dest", type=Path)
    ap.add_argument("--from-base", action="store_true",
                    help="start from dest's current contents instead of the recorded Write")
    args = ap.parse_args()
    return replay(args.chain, args.dest, args.from_base)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/surg-recovery-2026-07-30 && ~/docs/NU/Freshman_Year/Summer_2026/surg/.venv/bin/pytest test_replay.py -q`
Expected: 4 passed.

No commit — this file is outside the repo by design.

---

## Task 3: Graft the item-8 branch (analysis layer)

`recovered/feature/sub-q1-item-8-5min-companion` forks from `07798da`, which is an ancestor of `main`. `main` has since advanced, so a fast-forward is impossible directly. Rebase first, then fast-forward — this preserves all 16 commits individually, matching the project's stated branch convention (never squash).

The only expected conflict surface is `docs/decisions.md`, which `da75a00` also modified.

**Files:**
- Modify: `docs/decisions.md`, `src/surg/analysis/run.py`, `src/surg/analysis/gpd.py`, `src/surg/analysis/gpd_components.py`, `src/surg/analysis/gpd_continuous.py`, `src/surg/analysis/year_fe_diagnostic.py`, `src/surg/analysis/tail_risk_curves.py`, `src/surg/preprocessing/features.py`, `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`
- Create: `src/surg/analysis/bootstrap_strategies.py`, `scripts/build_cross_resolution_summary.py`, and their tests

- [ ] **Step 1: Create a working branch from the recovered ref**

```bash
cd ~/docs/NU/Freshman_Year/Summer_2026/surg
git switch -c graft/item-8 recovered/feature/sub-q1-item-8-5min-companion
```

- [ ] **Step 2: Rebase onto main**

```bash
git rebase main
```

Expected: conflicts in `docs/decisions.md`. Resolve by **keeping both sides** — these are append-only dated research entries, not competing edits. Order entries by their date heading. Never delete an existing entry to resolve a conflict.

For each conflict: `git add <file>` then `git rebase --continue`.

- [ ] **Step 3: Verify all 16 commits survived**

Run: `git log --oneline main..graft/item-8 | wc -l`
Expected: `16`

If this is not 16, a commit was dropped during rebase. Run `git rebase --abort` and restart rather than proceeding.

- [ ] **Step 4: Run the test suite**

Run: `.venv/bin/pytest -q`
Expected: pass, with a higher test count than the Task 1 baseline (the branch adds 5 test files).

- [ ] **Step 5: Fast-forward main**

```bash
git switch main
git merge --ff-only graft/item-8
git branch -d graft/item-8
```

- [ ] **Step 6: Verify**

Run: `git log --oneline -3 && .venv/bin/pytest -q`
Expected: item-8 commits on `main`; suite green.

---

## Task 4: Drop the superseded May preprocessing

Decided 2026-07-30. These are the May generation, which reads PJM `rt_fivemin_hrl_lmps` parquet. The July generation restored in Tasks 8–10 reads gridstatus chunks. Keeping both would leave two contradictory implementations of the same layer in the tree.

`spike_exceedance_comparison.py` implements Part B, which the July design dropped.

**Files:**
- Delete: `src/surg/preprocessing/build_5min.py`, `src/surg/preprocessing/build_5min_lmp_only.py`, `src/surg/preprocessing/loaders_5min.py`, `src/surg/analysis/spike_exceedance_comparison.py` and their four test files

- [ ] **Step 1: Confirm nothing else imports them**

```bash
grep -rn "build_5min\|loaders_5min\|spike_exceedance" src/ scripts/ tests/ --include='*.py' \
  | grep -v "^src/surg/preprocessing/build_5min\|^src/surg/preprocessing/loaders_5min\|^src/surg/analysis/spike_exceedance\|^tests/"
```

Expected: no output. Any hit is a live caller — **stop** and report it rather than deleting.

- [ ] **Step 2: Delete the files**

```bash
git rm src/surg/preprocessing/build_5min.py \
       src/surg/preprocessing/build_5min_lmp_only.py \
       src/surg/preprocessing/loaders_5min.py \
       src/surg/analysis/spike_exceedance_comparison.py \
       tests/preprocessing/test_build_5min.py \
       tests/preprocessing/test_build_5min_lmp_only.py \
       tests/preprocessing/test_loaders_5min.py \
       tests/analysis/test_spike_exceedance_comparison.py
```

- [ ] **Step 3: Run the suite**

Run: `.venv/bin/pytest -q`
Expected: pass, with a lower count than Task 3.

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor(preprocessing): drop superseded May 5-min generation

The May generation reads PJM rt_fivemin_hrl_lmps parquet; the July
generation reads gridstatus chunks and produced every finding in the
2026-08-03 agenda. Keeping both leaves two contradictory implementations
of the same layer.

spike_exceedance_comparison implemented Part B, which the July design
dropped.

See docs/specs/2026-07-30-surg-recovery-design.md, Phase 4."
```

---

## Task 5: Restore `gridstatus_client.py`

**Files:**
- Create: `src/surg/acquisition/gridstatus_client.py`
- Create: `tests/acquisition/test_gridstatus_client.py`
- Source: `$ARCHIVE/extracted/_worktree-surg-gridstatus-5min/src/surg/acquisition/gridstatus_client.py`
- Chain: `$ARCHIVE/edit-chains/_worktree-surg-gridstatus-5min__src__surg__acquisition__gridstatus_client.py.json`

- [ ] **Step 1: Replay the module**

```bash
cd ~/surg-recovery-2026-07-30
SURG=~/docs/NU/Freshman_Year/Summer_2026/surg
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__src__surg__acquisition__gridstatus_client.py.json" \
  "$SURG/src/surg/acquisition/gridstatus_client.py"
```

Expected: `applied=1 skipped=0`, exit 0. If any edit is skipped, reconcile it by hand against `docs/sources/gridstatus-api-constraints.md` before continuing.

- [ ] **Step 2: Replay the test**

```bash
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__tests__acquisition__test_gridstatus_client.py.json" \
  "$SURG/tests/acquisition/test_gridstatus_client.py"
```

Expected: `applied=1 skipped=0`.

- [ ] **Step 3: Run the tests**

Run: `.venv/bin/pytest tests/acquisition/test_gridstatus_client.py -q`
Expected: pass. These tests use a fake client and make no network calls.

- [ ] **Step 4: Verify the two security constraints from the constraints doc**

```bash
grep -n "follow_redirects" src/surg/acquisition/gridstatus_client.py
grep -n "datasets" src/surg/acquisition/gridstatus_client.py
```

Expected: `follow_redirects=False` is present, and no call targets `/datasets/` with a trailing slash. Both matter: the trailing slash 307-redirects to cleartext HTTP and would replay the `x-api-key` header in plaintext.

- [ ] **Step 5: Commit**

```bash
git add src/surg/acquisition/gridstatus_client.py tests/acquisition/test_gridstatus_client.py
git commit -m "feat(acquisition): restore gridstatus_client from recovery archive

Reconstructed from the recorded Write payload plus 1 replayed edit.
Retains follow_redirects=False and the no-trailing-slash /datasets rule
documented in docs/sources/gridstatus-api-constraints.md."
```

---

## Task 6: Restore `gridstatus_pull.py`

This module has edits recorded in **two** places: the worktree chain (2 edits) and the main-path chain (9 edits). Apply the worktree chain first, then the main-path chain in `--from-base` mode, because the main-path edits were made after the worktree was merged.

**Files:**
- Create: `src/surg/acquisition/gridstatus_pull.py`, `tests/acquisition/test_gridstatus_pull.py`

- [ ] **Step 1: Replay the worktree chain (has the Write baseline)**

```bash
cd ~/surg-recovery-2026-07-30
SURG=~/docs/NU/Freshman_Year/Summer_2026/surg
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__src__surg__acquisition__gridstatus_pull.py.json" \
  "$SURG/src/surg/acquisition/gridstatus_pull.py"
```

Expected: `applied=2 skipped=0`.

- [ ] **Step 2: Replay the main-path chain on top**

```bash
python3 replay.py \
  "edit-chains/src__surg__acquisition__gridstatus_pull.py.json" \
  "$SURG/src/surg/acquisition/gridstatus_pull.py" --from-base
```

Expected: `applied=9 skipped=0`. Skips here are plausible if a hunk is already present — inspect each before accepting.

- [ ] **Step 3: Replay both test chains the same way**

```bash
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__tests__acquisition__test_gridstatus_pull.py.json" \
  "$SURG/tests/acquisition/test_gridstatus_pull.py"
python3 replay.py \
  "edit-chains/tests__acquisition__test_gridstatus_pull.py.json" \
  "$SURG/tests/acquisition/test_gridstatus_pull.py" --from-base
```

- [ ] **Step 4: Verify the CLI contract against the surviving oracle**

The backfill script is a working record of the real interface:

```bash
grep -oE '\-\-[a-z-]+' ~/surg-run-logs/surg-gridstatus-backfill-launch.sh | sort -u
grep -oE '"--[a-z-]+"' src/surg/acquisition/gridstatus_pull.py | sort -u
```

Expected: the module accepts at least `--start`, `--end`, `--pnodes`, `--skip-load`, `--data-root`.

- [ ] **Step 5: Verify the key lookup was not "fixed"**

```bash
grep -n "GRIDSTATUS_API_KEY" src/surg/acquisition/gridstatus_pull.py
```

Expected: exactly the bare `GRIDSTATUS_API_KEY`. If it reads `GRIDSTATUS_API_KEY_1`, revert that — the multi-account strategy depends on one process per account seeing a different value in the *same* variable.

- [ ] **Step 6: Run the tests**

Run: `.venv/bin/pytest tests/acquisition/test_gridstatus_pull.py -q`
Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add src/surg/acquisition/gridstatus_pull.py tests/acquisition/test_gridstatus_pull.py
git commit -m "feat(acquisition): restore gridstatus_pull from recovery archive

Reconstructed from the worktree Write baseline plus 2 worktree edits and
9 main-path edits. CLI verified against the surviving backfill launch
script: --start --end --pnodes --skip-load --data-root.

Module reads the bare GRIDSTATUS_API_KEY; per-account override stays in
the launch script."
```

---

## Task 7: Restore `gridstatus_validate.py`

**Files:**
- Create: `src/surg/acquisition/gridstatus_validate.py`, `tests/acquisition/test_gridstatus_validate.py`

- [ ] **Step 1: Replay module and test**

```bash
cd ~/surg-recovery-2026-07-30
SURG=~/docs/NU/Freshman_Year/Summer_2026/surg
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__src__surg__acquisition__gridstatus_validate.py.json" \
  "$SURG/src/surg/acquisition/gridstatus_validate.py"
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__tests__acquisition__test_gridstatus_validate.py.json" \
  "$SURG/tests/acquisition/test_gridstatus_validate.py"
```

Expected: `applied=4 skipped=0` and `applied=1 skipped=0`.

- [ ] **Step 2: Run the tests**

Run: `.venv/bin/pytest tests/acquisition/test_gridstatus_validate.py -q`
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add src/surg/acquisition/gridstatus_validate.py tests/acquisition/test_gridstatus_validate.py
git commit -m "feat(acquisition): restore gridstatus_validate from recovery archive

Reconstructed from the recorded Write payload plus 4 replayed edits."
```

---

## Task 8: Restore `schema_5min.py`

The cleanest of the set — one recorded `Write`, zero edits.

**Files:**
- Create: `src/surg/preprocessing/schema_5min.py`

- [ ] **Step 1: Copy the extracted file**

```bash
cp ~/surg-recovery-2026-07-30/extracted/_worktree-surg-gridstatus-5min/src/surg/preprocessing/schema_5min.py \
   src/surg/preprocessing/schema_5min.py
```

- [ ] **Step 2: Verify it imports**

Run: `.venv/bin/python -c "from surg.preprocessing import schema_5min; print(sorted(n for n in dir(schema_5min) if not n.startswith('_')))"`
Expected: prints the module's public names without error.

- [ ] **Step 3: Commit**

```bash
git add src/surg/preprocessing/schema_5min.py
git commit -m "feat(preprocessing): restore schema_5min from recovery archive

Recorded Write payload with no subsequent edits — byte-faithful."
```

---

## Task 9: Restore `loaders_5min.py` (July generation)

Task 4 deleted the May file of the same name. This restores the July one, which reads gridstatus chunks and renames columns onto PJM panel conventions.

**Files:**
- Create: `src/surg/preprocessing/loaders_5min.py`, `tests/preprocessing/test_loaders_5min.py`

- [ ] **Step 1: Replay module, copy test**

```bash
cd ~/surg-recovery-2026-07-30
SURG=~/docs/NU/Freshman_Year/Summer_2026/surg
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__src__surg__preprocessing__loaders_5min.py.json" \
  "$SURG/src/surg/preprocessing/loaders_5min.py"
cp extracted/_worktree-surg-gridstatus-5min/tests/preprocessing/test_loaders_5min.py \
   "$SURG/tests/preprocessing/test_loaders_5min.py"
```

Expected: `applied=2 skipped=0`.

- [ ] **Step 2: Verify it is the July generation, not the May one**

```bash
grep -c "rt_fivemin_hrl_lmps" src/surg/preprocessing/loaders_5min.py || true
grep -n "location_id\|total_lmp_rt" src/surg/preprocessing/loaders_5min.py | head -5
```

Expected: **zero** matches for `rt_fivemin_hrl_lmps` (that is the May signature), and the gridstatus rename map present — `location_id -> pnode_id`, `lmp -> total_lmp_rt`.

- [ ] **Step 3: Run the tests**

Run: `.venv/bin/pytest tests/preprocessing/test_loaders_5min.py -q`
Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add src/surg/preprocessing/loaders_5min.py tests/preprocessing/test_loaders_5min.py
git commit -m "feat(preprocessing): restore July loaders_5min from recovery archive

Reads gridstatus chunks and renames onto PJM panel conventions. Replaces
the May generation removed in the earlier drop commit."
```

---

## Task 10: Restore `build_5min.py` (July generation)

Edits recorded in two places: worktree (5 edits) and main path (4 edits).

**Files:**
- Create: `src/surg/preprocessing/build_5min.py`, `tests/preprocessing/test_build_5min.py`

- [ ] **Step 1: Replay worktree chain, then main-path chain**

```bash
cd ~/surg-recovery-2026-07-30
SURG=~/docs/NU/Freshman_Year/Summer_2026/surg
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__src__surg__preprocessing__build_5min.py.json" \
  "$SURG/src/surg/preprocessing/build_5min.py"
python3 replay.py \
  "edit-chains/src__surg__preprocessing__build_5min.py.json" \
  "$SURG/src/surg/preprocessing/build_5min.py" --from-base
```

Expected: `applied=5` then `applied=4`.

- [ ] **Step 2: Replay the test chains**

```bash
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__tests__preprocessing__test_build_5min.py.json" \
  "$SURG/tests/preprocessing/test_build_5min.py"
python3 replay.py \
  "edit-chains/tests__preprocessing__test_build_5min.py.json" \
  "$SURG/tests/preprocessing/test_build_5min.py" --from-base
```

- [ ] **Step 3: Run the tests**

Run: `.venv/bin/pytest tests/preprocessing/test_build_5min.py -q`
Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add src/surg/preprocessing/build_5min.py tests/preprocessing/test_build_5min.py
git commit -m "feat(preprocessing): restore July build_5min from recovery archive

Reconstructed from the worktree Write baseline plus 5 worktree edits and
4 main-path edits. Includes the gap-masking fix."
```

---

## Task 11: Restore `run_5min.py`

**Files:**
- Create: `src/surg/analysis/run_5min.py`, `tests/analysis/test_run_5min.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Replay module, copy test**

```bash
cd ~/surg-recovery-2026-07-30
SURG=~/docs/NU/Freshman_Year/Summer_2026/surg
python3 replay.py \
  "edit-chains/_worktree-surg-gridstatus-5min__src__surg__analysis__run_5min.py.json" \
  "$SURG/src/surg/analysis/run_5min.py"
python3 replay.py \
  "edit-chains/src__surg__analysis__run_5min.py.json" \
  "$SURG/src/surg/analysis/run_5min.py" --from-base
cp extracted/_worktree-surg-gridstatus-5min/tests/analysis/test_run_5min.py \
   "$SURG/tests/analysis/test_run_5min.py"
```

- [ ] **Step 2: Run the tests**

Run: `.venv/bin/pytest tests/analysis/test_run_5min.py -q`
Expected: pass.

- [ ] **Step 3: Register the console script**

The pre-loss entrypoint was `surg-run-5min`. Add it to `pyproject.toml` alongside the existing three:

```toml
[project.scripts]
surg-pull = "surg.acquisition.pull:main"
surg-prep = "surg.preprocessing.build:main"
surg-analyze = "surg.analysis.run:main"
surg-run-5min = "surg.analysis.run_5min:main"
```

- [ ] **Step 4: Reinstall and verify the entrypoint resolves**

```bash
uv pip install -e '.[dev]'
.venv/bin/surg-run-5min --help
```

Expected: help text, exit 0.

- [ ] **Step 5: Full suite**

Run: `.venv/bin/pytest -q`
Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/run_5min.py tests/analysis/test_run_5min.py pyproject.toml
git commit -m "feat(analysis): restore run_5min entrypoint from recovery archive

Re-registers the surg-run-5min console script."
```

---

## Task 12: Graft the item-6 branch (filter-skip + item #9 record)

Done after the acquisition and preprocessing work because its `tail_risk_curves.py` and `run.py` changes must land on top of item-8's changes to the same files.

This branch also makes `scripts/run_5min_nofilter.py` unnecessary — the spec records `filter_col=None` as the cleaner replacement for that workaround, so the script is deliberately not restored.

**Files:**
- Modify: `docs/decisions.md` (+382 lines), `src/surg/analysis/run.py`, `src/surg/analysis/tail_risk_curves.py`, `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Rebase onto main**

```bash
git switch -c graft/item-6 recovered/feature/sub-q1-item-6-no-filter
git rebase main
```

Expected: conflicts in `docs/decisions.md`, `src/surg/analysis/run.py`, `src/surg/analysis/tail_risk_curves.py`.

Resolution rules:
- `decisions.md` — keep both sides, ordered by date heading. Never drop an entry.
- `tail_risk_curves.py` — keep **both** item-8's `bootstrap_method`/`pnode_labels` parameters and item-6's `filter_col`. They are independent additions to the same signature.
- `run.py` — same principle; both sets of CLI flags survive.

- [ ] **Step 2: Verify all 4 commits survived**

Run: `git log --oneline main..graft/item-6 | wc -l`
Expected: `4`

- [ ] **Step 3: Verify the merged signature has both features**

```bash
grep -n "def run_tail_risk_curves" -A 12 src/surg/analysis/tail_risk_curves.py
```

Expected: the signature contains `filter_col`, `bootstrap_method`, and `pnode_labels`. If any is missing, the conflict resolution dropped a feature — fix before continuing.

- [ ] **Step 4: Run the suite**

Run: `.venv/bin/pytest -q`
Expected: pass.

- [ ] **Step 5: Fast-forward main**

```bash
git switch main
git merge --ff-only graft/item-6
git branch -d graft/item-6
```

- [ ] **Step 6: Verify `filter_col=None` works end to end**

Run: `.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -q -k "filter"`
Expected: pass, including the filter-skip cases.

---

## Task 13: Restore the research record

The highest-fidelity requirement in the plan. `docs/decisions.md` has 20 recorded `Edit` diffs and **no `Write` baseline**, so replay must run in `--from-base` mode against the tree as it now stands — after Tasks 3 and 12 have added the item-8 and item-9 entries.

**Files:**
- Modify: `docs/decisions.md`
- Create: `docs/reference/pjm-manuals/pjm-lmp-formation.md`, plus the July plans and specs

- [ ] **Step 1: Snapshot decisions.md before replay**

```bash
cp docs/decisions.md /tmp/decisions-before-replay.md
wc -l docs/decisions.md
```

- [ ] **Step 2: Replay the decisions.md chain in base mode**

```bash
cd ~/surg-recovery-2026-07-30
SURG=~/docs/NU/Freshman_Year/Summer_2026/surg
python3 replay.py "edit-chains/docs__decisions.md.json" "$SURG/docs/decisions.md" --from-base
```

Skips are **expected** here — the chain spans several worktrees with different bases. For each skipped hunk, reconstruct that entry by hand from the memory directory (`$ARCHIVE/memory/`) and the 2026-07-27 / 2026-08-03 agendas, and mark it in the document as reconstructed rather than replayed. Do not force a patch.

- [ ] **Step 3: Verify the four July topics are present**

```bash
grep -n "^## 2026-07" docs/decisions.md
```

Expected: entries covering workstream C (two price channels), the extended-panel interpretation, the load-control amendment, and the 2026-escalation investigation.

- [ ] **Step 4: Verify nothing was lost**

```bash
diff <(grep '^## ' /tmp/decisions-before-replay.md) <(grep '^## ' docs/decisions.md)
```

Expected: only additions. Any deletion is a replay bug — restore from the snapshot and redo.

- [ ] **Step 5: Restore `pjm-lmp-formation.md`**

```bash
python3 replay.py "edit-chains/docs__pjm-lmp-formation.md.json" "$SURG/docs/reference/pjm-manuals/pjm-lmp-formation.md"
```

Expected: `applied=10`. Verify it contains the §6/§9 finding that load-volatility → reserve depletion is UNSUPPORTED, and the M11 §2.2 congestion mechanism:

```bash
grep -n "UNSUPPORTED" docs/reference/pjm-manuals/pjm-lmp-formation.md | head
grep -n "4.3\|2.2" docs/reference/pjm-manuals/pjm-lmp-formation.md | head
```

- [ ] **Step 6: Restore the July plans and specs**

```bash
cd ~/surg-recovery-2026-07-30
cp extracted/docs/plans/2026-07-17-5min-two-sided-companion-implementation.md "$SURG/docs/plans/"
cp extracted/docs/plans/2026-07-20-jlarc-external-context-update.md "$SURG/docs/plans/"
cp extracted/docs/plans/2026-07-21-subq3-event-catalog-scan.md "$SURG/docs/plans/"
cp extracted/docs/specs/2026-07-17-5min-two-sided-companion-design.md "$SURG/docs/specs/"
cp extracted/docs/specs/2026-07-29-pjm-lmp-formation-research-design.md "$SURG/docs/specs/"
```

Then replay their edit chains in `--from-base` mode:

```bash
python3 replay.py "edit-chains/docs__plans__2026-07-20-jlarc-external-context-update.md.json" \
  "$SURG/docs/plans/2026-07-20-jlarc-external-context-update.md" --from-base
python3 replay.py "edit-chains/docs__plans__2026-07-21-subq3-event-catalog-scan.md.json" \
  "$SURG/docs/plans/2026-07-21-subq3-event-catalog-scan.md" --from-base
python3 replay.py "edit-chains/docs__superpowers__specs__2026-07-29-pjm-lmp-formation-research-design.md.json" \
  "$SURG/docs/specs/2026-07-29-pjm-lmp-formation-research-design.md" --from-base
python3 replay.py "edit-chains/docs__superpowers__specs__2026-07-17-5min-two-sided-companion-design.md.json" \
  "$SURG/docs/specs/2026-07-17-5min-two-sided-companion-design.md" --from-base
```

- [ ] **Step 7: Restore the figure-set design spec**

Use the **post-review** version — the one pasted into the recovery session, containing 13 figures (F1–F11 plus F4b, F4c) and the "Review decisions (2026-07-30)" section. The extracted 9,787-byte copy predates that review and must not be used.

Save to `docs/specs/2026-07-30-subq1-figure-set-design.md`.

- [ ] **Step 8: Log the spike-filtering ruling**

The 2026-07-30 decision — the ~3,193-spike class stays in, unfiltered — was ruled during recovery and currently lives only in the recovery spec. Add it to `docs/decisions.md` as a dated entry so the research record is the single source of truth.

- [ ] **Step 9: Commit**

```bash
git add docs/
git commit -m "docs: restore July research record from recovery archive

decisions.md July entries (workstream C, extended-panel interpretation,
load-control amendment, 2026-escalation), pjm-lmp-formation.md, and the
July plans and specs. Entries that could not be replayed cleanly are
marked as reconstructed from the memory directory and advisor agendas.

Figure-set spec is the post-review 13-figure version.

Logs the reversion-spike ruling: not filtered."
```

---

## Task 14: Re-download the PJM manuals

**Files:**
- Create: `docs/reference/pjm-manuals/` — M11 rev137, M12 rev57, M03 rev71 (~11 MB)

- [ ] **Step 1: Download the three manuals**

Source: `https://www.pjm.com/library/manuals`. The project tracks them in git deliberately (decided pre-loss) because `pjm-lmp-formation.md` cites specific section numbers that move between revisions.

Match the recorded revisions exactly — M11 rev137, M12 rev57, M03 rev71. If a revision is no longer downloadable, record the substituted revision in `decisions.md` and re-verify every section citation in `pjm-lmp-formation.md` against it.

- [ ] **Step 2: Verify the cited sections resolve**

Confirm M11 §2.2 (congestion / transmission line loadings), §4.3 (reserve requirement from largest single contingency), §6 and §9 exist in the downloaded revision.

- [ ] **Step 3: Commit**

```bash
git add docs/reference/pjm-manuals/
git commit -m "docs(sources): re-vendor PJM manuals M11 r137, M12 r57, M03 r71

Tracked in git because pjm-lmp-formation.md cites section numbers that
move between revisions."
```

---

## Task 15: Final verification

- [ ] **Step 1: Full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass.

- [ ] **Step 2: Lint**

Run: `.venv/bin/ruff check src/ tests/ scripts/`
Expected: clean, or only pre-existing findings also present at the Task 1 baseline.

- [ ] **Step 3: Confirm the restored surface**

```bash
ls src/surg/acquisition/gridstatus_client.py \
   src/surg/acquisition/gridstatus_pull.py \
   src/surg/acquisition/gridstatus_validate.py \
   src/surg/preprocessing/schema_5min.py \
   src/surg/preprocessing/loaders_5min.py \
   src/surg/preprocessing/build_5min.py \
   src/surg/analysis/run_5min.py \
   src/surg/analysis/bootstrap_strategies.py
```

Expected: all present.

- [ ] **Step 4: Confirm the intentional absences**

```bash
ls src/surg/analysis/spike_exceedance_comparison.py \
   src/surg/preprocessing/build_5min_lmp_only.py \
   scripts/plot_subq1_results.py 2>&1
```

Expected: all three "No such file". Each is a deliberate decision — Part B dropped, May generation dropped, figure pipeline superseded by the figure-set spec.

- [ ] **Step 5: Report status**

Summarise for the user: tests passing vs the Task 1 baseline, any hunks marked reconstructed rather than replayed, and confirmation that Plan B (data re-pull, verification, push) is the remaining work.

**Do not push.** Pushing is Plan B / spec Phase 8 and is a separate explicit ask.

---

## Self-Review Notes

**Spec coverage.** Phase 4 → Tasks 3, 4, 12. Phase 2 → Tasks 5, 6, 7. Phase 5 → Tasks 8, 9, 10, 11. Phase 6 → Tasks 13, 14. Phases 1, 3, 7, 8 are explicitly Plan B. Task 1 (environment) and Task 2 (replay tool) are plan infrastructure the spec assumed but did not enumerate — the `.venv` died with the directory, and 41 chains cannot be replayed by hand reliably.

**Known risk.** Task 13 is the only task expected to produce skipped hunks, because `decisions.md` has no `Write` baseline. The mitigation is explicit: reconstruct from the memory directory and mark as reconstructed rather than forcing patches. This is the one place where "restore" may honestly mean "rewrite from records", and the document says so rather than hiding it.

**Ordering constraint.** Task 12 must follow Tasks 3–11: its `tail_risk_curves.py` and `run.py` edits land on top of item-8's changes to the same functions, and resolving those conflicts requires item-8 already present.
