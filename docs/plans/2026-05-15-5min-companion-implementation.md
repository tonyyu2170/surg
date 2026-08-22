# Sub-Q1 Item #8 — 5-Min Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` (inline batch execution is the
> appropriate pattern for unattended overnight runs — subagent-driven
> review-per-task is optimized for human-in-the-loop). Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute Sub-Q1 Item #8 — the 5-min companion to the hourly
sub-q1 closure work (items #1–4 + #6) — as an unattended overnight
run, in two parts: Part A (joint Z+LMP, 30-day window, items #1–4 +
#6 with island cluster bootstrap) and Part B (LMP-only descriptive,
6-month window, single new spike-exceedance-comparison module).

**Architecture:** New 5-min preprocessing modules (`build_5min.py`,
`build_5min_lmp_only.py`, `loaders_5min.py`); new island cluster
bootstrap module (`bootstrap_strategies.py`); refactor of items
#1–4 + #6 to accept injected bootstrap strategy (preserving
hourly-pair-bootstrap default, regression-tested for numeric
equivalence); new Part B module
(`spike_exceedance_comparison.py`); CLI extension to `run.py`. All
work in sibling worktree `../surg-5min-companion/` on branch
`feature/sub-q1-item-8-5min-companion`. Commit per task; no FF-merge,
no push.

**Tech Stack:** Python 3.12, pandas, numpy, scipy.stats, matplotlib,
pytest. **No new dependencies.** Cluster bootstrap is numpy-only.

**Design spec reference:**
`docs/plans/2026-05-15-5min-companion-design.md`. The design doc IS
the pre-reg per the project's light-pre-reg convention; a short
application-style entry in `docs/decisions.md` (item #8) is the
written confirmation.

**Time budget:** 10–15 h estimated wall, user-authorized to overflow
the nominal 8h target. Run-to-completion is the locked policy.

**Failure handling locked policy:** any failure not handled by a
specific task → halt + commit current state with `WIP:` prefix +
write status update; do NOT continue downstream tasks.

---

## Pre-launch setup (done by me tonight on `main`, before slash command invoked)

These tasks happen **outside** the autonomous overnight run, on
`main`, before the user invokes the slash command. They must complete
before the slash command launches.

### Setup-1: Verify clean main worktree state

- [ ] Verify `git status` shows clean working tree on `main`.
- [ ] Verify head is `b4feb92` or later (item #6 application entry shipped).

### Setup-2: Capture hourly regression reference fixtures

**Why:** Items #1–4 + #6 are shipped + cited in `decisions.md`. The
overnight run refactors them. Without a captured pre-refactor
reference, the regression smoke gate has nothing to compare against.

**CLI gap (verified 2026-05-15):** `surg-analyze` does NOT have a
`--seed` flag (seeds are hardcoded constants in `run_all()`); it
also lacks per-module skip flags for TAR/QR/QR-full/GPD-median/
mechanism/robustness/conditional_z/gpd_continuous. Adding these to
the CLI is part of Task 8. To AVOID needing those CLI changes during
reference capture, this setup task **bypasses the CLI entirely** and
calls each module's `run_*` function directly via a Python script
with explicit `seed=42`. This is sufficient because every module
already accepts a `seed` kwarg and uses
`np.random.default_rng(seed)` internally (verified by inspection
2026-05-15).

**Per advisor (blocker fix):** capture against the **full 3.6y
hourly panel** with reduced `n_boot=50`, not a single-year slice.
Single-year slices make item #3 (year_fe_diagnostic) degenerate (the
year FE absorbs everything with no within-year contrast) and weaken
items #1, #2 similarly. Full-panel reference is methodologically
correct and the wall time at n_boot=50 is acceptable (~10–20 min
total).

- [ ] **Step 1:** Create directory:
  ```bash
  mkdir -p tests/regression/hourly_reference
  ```

- [ ] **Step 2:** Capture references via direct Python invocation
  (NOT CLI), using the full 3.6y panel with n_boot=50 and explicit
  seed=42:
  ```bash
  python <<'EOF'
  from pathlib import Path
  import pandas as pd
  from surg.preprocessing.loaders import load_sync_reserve_events
  from surg.analysis.gpd_continuous import run_gpd_continuous_z
  from surg.analysis.gpd_components import run_gpd_components
  from surg.analysis.year_fe_diagnostic import run_year_fe_diagnostic, write_cross_pnode_summary
  from surg.analysis.ashburn_diagnostic import run_ashburn_diagnostic
  from surg.analysis.tail_risk_curves import run_tail_risk_curves
  from surg.analysis.run import PNODE_RESPONSES

  panel = pd.read_parquet('data/interim/analysis_panel.parquet')
  out_root = Path('tests/regression/hourly_reference')
  out_root.mkdir(parents=True, exist_ok=True)

  # Item #1: gpd_continuous (Spec B), all pnodes, n_boot=50, seed=42
  for label, col in PNODE_RESPONSES.items():
      if panel[col].dropna().empty:
          continue
      run_gpd_continuous_z(
          panel=panel,
          out_path=out_root / "gpd_continuous" / f"{label}.json",
          response_col=col, pnode_label=label,
          n_boot=50, seed=42,
      )

  # Item #2: gpd_components, n_boot=50, seed=42
  run_gpd_components(
      panel=panel, out_dir=out_root / "gpd_components",
      n_boot=50, seed=42,
  )

  # Item #3: year_fe_diagnostic, all pnodes, n_boot=50, seed=42
  pnode_labels = []
  for label, col in PNODE_RESPONSES.items():
      if panel[col].dropna().empty:
          continue
      run_year_fe_diagnostic(
          panel=panel,
          out_path=out_root / "year_fe_diagnostic" / f"{label}.json",
          pnode_label=label, response_col=col,
          n_boot=50, seed=42,
      )
      pnode_labels.append(label)
  write_cross_pnode_summary(out_root / "year_fe_diagnostic", tuple(pnode_labels))

  # Item #4: ashburn_diagnostic (uses Spec B outputs from above)
  # Verified signature 2026-05-15: accepts seed kwarg (no n_boot param)
  run_ashburn_diagnostic(
      panel=panel,
      out_dir=out_root / "ashburn_diagnostic",
      spec_b_results_dir=out_root / "gpd_continuous",
      seed=42,
  )

  # Item #6: tail_risk_curves, n_boot=50, seed=42
  run_tail_risk_curves(
      panel=panel,
      out_root=out_root / "tail_risk_curves",
      n_boot=50, seed=42,
  )

  print('Reference capture complete')
  EOF
  ```

  **If any module's `run_*` signature does not match the calls above
  (e.g., positional args, missing `seed` param, different kwarg
  names):** inspect the actual signature with
  `python -c "import inspect; from surg.analysis.<module> import run_<X>; print(inspect.signature(run_<X>))"`
  and adjust the script. Do NOT proceed to Step 3 until reference
  capture succeeds.

- [ ] **Step 3:** Verify all reference outputs exist:
  ```bash
  find tests/regression/hourly_reference -name "*.json" -o -name "*.csv" | sort
  ```
  Expected: per-pnode JSON for each of the 5 modules + summary CSVs.

- [ ] **Step 4:** Capture the seed values, n_boot, and tolerance
  policy used (for the regression test to replay).

  **NOTE on panel rebuild (2026-05-15):** The on-disk panel was schema
  v1 (mtime 2026-05-12 23:09); preprocessing HEAD is schema v2
  (commits `1767a07` + `a5bc16e` on 2026-05-14 added system_energy +
  marginal_loss columns). Item #2 and item #6 reference capture both
  required the v2 columns. **Rebuild before capture:**
  ```bash
  .venv/bin/python -c "
  from pathlib import Path
  from surg.preprocessing.build import build_analysis_panel
  panel = build_analysis_panel(data_root=Path('data/raw'))
  panel.to_parquet('data/interim/analysis_panel.parquet')
  "
  ```
  Takes ~5 seconds. After rebuild, all 5 modules capture cleanly
  (verified 2026-05-15: 33 reference files written in 15 min).

  Write `CAPTURE_PARAMS.json` with the actual capture parameters and
  detection rules (see the committed file at
  `tests/regression/hourly_reference/CAPTURE_PARAMS.json` for the
  authoritative content; key fields are panel_schema_version,
  per-module n_boot+seed, tolerance_policy, ci_field_detection_rule).

- [ ] **Step 5:** Commit:
  ```bash
  git add tests/regression/hourly_reference/
  git commit -m "test(regression): capture hourly reference fixtures (full 3.6y panel, n_boot=50, seed=42) pre-refactor"
  ```

### Setup-3: Append item #8 pre-reg entry to decisions.md

- [ ] Append the following to `docs/decisions.md`:
  ```markdown
  ---

  ## 2026-05-15 — Sub-q1 item #8: 5-min companion run (pre-reg)

  **Context.** Sub-q1 closure (items #1–4 + #6) shipped at hourly
  resolution. The advisor meeting (item #5) is stronger if mechanism
  + descriptive findings come with a 5-min companion + an honest
  accounting of what 5-min granularity adds. Initial brainstorm
  assumed a 3.6y 5-min companion; API verification revealed
  `inst_load` is hard-capped at ~30-day PJM retention
  (`pjm-api-constraints.md:84`), making the joint Z+LMP analysis
  feasible only on a ~30-day window. 5-min LMP-only data is
  available for ~6 months on disk.

  **Decision.** Execute item #8 in two parts per the design at
  `docs/plans/2026-05-15-5min-companion-design.md`:
  - **Part A:** Items #1–4 + #6 on a joint 30-day Z+LMP panel
    (mid-Apr → mid-May 2026). Pre-registered as a feasibility
    probe — every CI is expected to span 0; the run documents the
    data wall in concrete numbers. Bootstrap: pure island cluster
    bootstrap (proposal-filter creates 3-hour islands separated by
    21-hour gaps; ~30 islands in window; below the 50-cluster floor
    for cluster-bootstrap CI reliability — also pre-registered).
  - **Part B:** Single new module computing 5-min vs hourly
    spike-exceedance comparison on the full 6-month LMP panel.
    Headline comparator: PJM-published `total_lmp_rt` from
    `rt_hrl_lmps`. Output: hidden-fraction by threshold per pnode.
    Descriptive only; no inferential CIs.

  Implementation per
  `docs/plans/2026-05-15-5min-companion-implementation.md`.
  Execution via slash command `/run-5min-companion` (plan-driven
  launcher, ≤4000 chars). Sibling worktree
  `../surg-5min-companion/`, commit per task, NO FF-merge, NO push.

  **Rationale.** The data-retention wall is a hard constraint, not a
  framing choice. Pre-registering the underpowered expectation
  prevents post-hoc "5-min looks the same" disappointment from being
  reframed as a finding; pre-registering the ≥50-cluster floor flag
  prevents post-hoc CI-noise from being read as substantive
  uncertainty. Part B is decoupled from Part A's Z constraint,
  giving an independently useful descriptive deliverable
  ("what does PJM hourly aggregation hide about 5-min spikes").

  **Revisit when.** Either (a) a longer-history 5-min DOM-load
  source surfaces (different PJM feed, advisor's private dataset,
  EIA), in which case Part A re-runs on a real window, or (b)
  advisor (item #5) reframes which resolution is the headline.
  ```
- [ ] Commit:
  ```bash
  git add docs/decisions.md
  git commit -m "docs(decisions): pre-reg sub-q1 item #8 (5-min companion, two-part)"
  ```

### Setup-4: Create slash command file

See "Slash command file" section at the end of this plan for the
exact content. Setup task only — file lives at
`.claude/commands/run-5min-companion.md` (gitignored, not committed).

- [ ] Create the file with the content specified in the §"Slash
  command file" section.
- [ ] Verify byte count ≤ 4000:
  ```bash
  wc -c .claude/commands/run-5min-companion.md
  ```
  Expected: a single number ≤ 4000.

### Setup-5: Commit pre-launch artifacts (design + plan)

- [ ] Commit the design + plan + roadmap update:
  ```bash
  git add docs/plans/2026-05-15-5min-companion-design.md \
          docs/plans/2026-05-15-5min-companion-implementation.md
  git commit -m "docs(plans): design + implementation plan for sub-q1 item #8 (5-min companion)"
  ```
- [ ] Update `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`
  to add an item #8 row marked "pending implementation"; commit:
  ```bash
  git add docs/plans/2026-05-14-sub-question-1-closure-roadmap.md
  git commit -m "docs(plans): add sub-q1 item #8 to closure roadmap"
  ```
- [ ] Do **NOT** push. User reviews + pushes manually.

After Setup-5 completes, the slash command is ready for the user to
invoke when they choose to launch the overnight run.

---

## File structure (created/modified by the autonomous run)

| Path | Action | Responsibility |
|---|---|---|
| `src/surg/preprocessing/loaders_5min.py` | Create | 5-min variants of `load_rt_lmp`, `load_dom_load`, `forward_fill_reserves`. ~200 lines. |
| `src/surg/preprocessing/build_5min.py` | Create | Joint 5-min panel builder (LMP + Z + reserves + filter). ~250 lines. |
| `src/surg/preprocessing/build_5min_lmp_only.py` | Create | LMP-only 5-min panel builder (Part B). ~120 lines. |
| `src/surg/preprocessing/features.py` | Modify | Generalize `compute_dom_load_gradient` to accept `freq_minutes` parameter. |
| `src/surg/analysis/bootstrap_strategies.py` | Create | Pure island cluster bootstrap implementation (numpy). ~80 lines. |
| `src/surg/analysis/tail_risk_curves.py` | Modify | Inject bootstrap strategy parameter; preserve pair-bootstrap default. |
| `src/surg/analysis/gpd_continuous.py` | Modify | Same. |
| `src/surg/analysis/gpd_components.py` | Modify | Same. |
| `src/surg/analysis/year_fe_diagnostic.py` | Modify | Same. |
| `src/surg/analysis/ashburn_diagnostic.py` | Modify | Same. |
| `src/surg/analysis/spike_exceedance_comparison.py` | Create | Part B's single new analytical module. ~180 lines. |
| `src/surg/analysis/run.py` | Modify | Add `--panel-path`, `--bootstrap-method`, related CLI flags. |
| `tests/preprocessing/test_loaders_5min.py` | Create | 5-min loader unit tests. |
| `tests/preprocessing/test_build_5min.py` | Create | Joint builder tests. |
| `tests/preprocessing/test_build_5min_lmp_only.py` | Create | LMP-only builder tests. |
| `tests/preprocessing/test_features.py` | Modify | Extend `compute_dom_load_gradient` test for `freq_minutes=5`. |
| `tests/analysis/test_bootstrap_strategies.py` | Create | Cluster bootstrap unit tests. |
| `tests/analysis/test_spike_exceedance_comparison.py` | Create | Part B module tests. |
| `tests/regression/test_hourly_pair_bootstrap_equivalence.py` | Create | Regression test asserting numeric equivalence post-refactor (per shipped module). |
| `scripts/build_cross_resolution_summary.py` | Create | Post-run cross-resolution summary builder. ~80 lines. |
| `data/raw/inst_load/2026_*.parquet` | Pull | Fresh `inst_load` Standard-tier pull. |
| `data/raw/rt_fivemin_hrl_lmps/2026/dom_targets__2026-05-11_to_2026-05-15.parquet` | Pull | 5-day refresh of 5-min LMP. |
| `data/interim/analysis_panel_5min_joint.parquet` | Build | Joint 5-min panel (Part A). |
| `data/interim/analysis_panel_5min_lmp_only.parquet` | Build | LMP-only 5-min panel (Part B). |
| `outputs_5min/...` | Produce | All Part A + Part B output JSON / CSV / PNG. |
| `outputs_5min/cross_resolution_summary.{json,csv}` | Produce | Like-for-like 30-day 5-min vs 30-day hourly comparison (item #6 only). |
| `docs/decisions.md` | Modify | Application entry post-run. |
| `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md` | Modify | Mark item #8 DONE post-run. |

---

## Task 1: Worktree setup + pre-flight verification

**Why:** All work happens in `../surg-5min-companion/`. Slash command
verifies pre-conditions before doing any other work.

**Files (read-only verification):**
- Verify: `docs/plans/2026-05-15-5min-companion-design.md`
- Verify: `docs/plans/2026-05-15-5min-companion-implementation.md`
- Verify: `docs/decisions.md` contains the item #8 pre-reg

- [ ] **Step 1:** Verify clean main + on main:
  ```bash
  cd ~/docs/NU/Freshman_Year/Summer_2026/SURG/surg
  git status
  ```
  Expected: `On branch main` + `nothing to commit, working tree clean`.

- [ ] **Step 2:** Verify pre-reg entry exists in `decisions.md`:
  ```bash
  grep -q "Sub-q1 item #8: 5-min companion run (pre-reg)" docs/decisions.md \
      && echo "PRE-REG OK" || echo "PRE-REG MISSING — HALT"
  ```
  Expected: `PRE-REG OK`. If `PRE-REG MISSING` → halt + report.

- [ ] **Step 3:** Verify NU DNS workaround for `api.pjm.com`:
  ```bash
  python -c "import socket; print(socket.gethostbyname('api.pjm.com'))"
  ```
  Expected: an IPv4 address (not `NXDOMAIN`). If `NXDOMAIN` → halt
  with instruction to user: "Add the `/etc/hosts` entry per
  `docs/sources/pjm-api-constraints.md`'s NU DNS workaround section, then
  re-run."

- [ ] **Step 4:** Create sibling worktree:
  ```bash
  git worktree add ../surg-5min-companion -b feature/sub-q1-item-8-5min-companion
  cd ../surg-5min-companion
  ```
  Expected: directory created, on new branch.

- [ ] **Step 5:** Set up venv:
  ```bash
  python3.12 -m venv .venv
  .venv/bin/pip install -e ".[dev]"
  ```
  Expected: install succeeds.

- [ ] **Step 6:** Verify baseline tests pass:
  ```bash
  .venv/bin/pytest -q
  ```
  Expected: `253 passed` (baseline post-item #6; verify count
  matches what's currently on main HEAD; if different, note + continue
  unless tests fail).

- [ ] **Step 7:** Commit (no-op if no changes; this task creates the
  branch but no code):
  ```bash
  # No commit; worktree creation does not need a commit on its own.
  ```

---

## Task 2: Refresh `inst_load` + `rt_fivemin_hrl_lmps`

**Why:** `inst_load` retention is rolling ~30 days; pulling fresh
maximizes the joint window. `rt_fivemin_hrl_lmps` archive on disk
ends 2026-05-10; today (or whenever this runs) is later, so a small
delta pull adds a few days of joint window.

**Files:**
- Add: `data/raw/inst_load/2026_<latest>_southern_region.parquet`
- Add: `data/raw/rt_fivemin_hrl_lmps/2026/dom_targets__2026-05-11_to_<today>.parquet`

- [ ] **Step 1:** Determine today's date:
  ```bash
  TODAY=$(date +%Y-%m-%d)
  echo "Pulling through $TODAY"
  ```

- [ ] **Step 2:** Refresh `inst_load`:
  ```bash
  .venv/bin/surg-pull \
      --feed inst_load \
      --area "PJM SOUTHERN REGION" \
      --start-date "$(date -v-32d +%Y-%m-%d)" \
      --end-date "$TODAY" \
      --output "data/raw/inst_load/2026_${TODAY}_southern_region.parquet"
  ```
  Expected: 7,000–9,000 rows (rolling 30-day window). On failure
  (3× retries with exp-backoff) → halt + commit + report.

- [ ] **Step 3:** Verify `inst_load` window:
  ```bash
  python -c "
  import pandas as pd, glob
  files = sorted(glob.glob('data/raw/inst_load/*.parquet'))
  df = pd.concat([pd.read_parquet(f) for f in files])
  df = df.drop_duplicates(subset=['datetime_beginning_ept'])
  print('rows:', len(df))
  print('min:', df['datetime_beginning_ept'].min())
  print('max:', df['datetime_beginning_ept'].max())
  "
  ```
  Expected: window covers at least 14 days. If < 14 days → halt
  (retention assumption broken; user must investigate).

- [ ] **Step 4:** Refresh 5-min LMP delta (only if last archive
  end-date < today):
  ```bash
  LAST=$(ls data/raw/rt_fivemin_hrl_lmps/2026/ | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | sort -u | tail -1)
  echo "Existing archive ends at: $LAST; today: $TODAY"
  if [ "$LAST" \< "$TODAY" ]; then
      .venv/bin/surg-pull \
          --feed rt_fivemin_hrl_lmps \
          --type EHV \
          --start-date "$(date -j -v+1d -f %Y-%m-%d "$LAST" +%Y-%m-%d 2>/dev/null || date -d "$LAST + 1 day" +%Y-%m-%d)" \
          --end-date "$TODAY" \
          --output "data/raw/rt_fivemin_hrl_lmps/2026/dom_targets__delta_to_${TODAY}.parquet"
  fi
  ```
  (Uses Standard tier; the 6-month-cap is well outside this delta
  window.) Expected: pull succeeds or no-op.

- [ ] **Step 5:** Commit (data files are gitignored; this commit
  records the operation only via the application entry later — no
  files to add):
  ```bash
  echo "Acquisition phase complete. Data files gitignored; no commit needed for this task."
  ```

---

## Task 3: Generalize `compute_dom_load_gradient` for 5-min support

**Files:**
- Modify: `src/surg/preprocessing/features.py` (function
  `compute_dom_load_gradient`)
- Test: `tests/preprocessing/test_features.py`

- [ ] **Step 1:** Read existing `compute_dom_load_gradient`:
  ```bash
  grep -n "compute_dom_load_gradient" src/surg/preprocessing/features.py
  ```

- [ ] **Step 2:** Write failing test for `freq_minutes=5` parameter
  in `tests/preprocessing/test_features.py`:
  ```python
  def test_compute_dom_load_gradient_5min():
      from surg.preprocessing.features import compute_dom_load_gradient
      import pandas as pd
      df = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range(
              "2026-04-15", periods=24, freq="5min"
          ),
          "dom_load_mw": [100, 105, 102, 108, 100, 95,
                          100, 110, 120, 115, 105, 100,
                          110, 115, 120, 130, 140, 135,
                          130, 125, 120, 115, 110, 105],
      })
      result = compute_dom_load_gradient(df, freq_minutes=5)
      assert "dom_load_gradient_abs_mw_per_min" in result.columns
      # second row gradient = abs(105-100)/5 = 1.0
      assert abs(result["dom_load_gradient_abs_mw_per_min"].iloc[1] - 1.0) < 1e-9
      # first row should be NaN
      assert pd.isna(result["dom_load_gradient_abs_mw_per_min"].iloc[0])
  ```
- [ ] **Step 3:** Run test, verify FAIL:
  ```bash
  .venv/bin/pytest tests/preprocessing/test_features.py::test_compute_dom_load_gradient_5min -v
  ```
  Expected: FAIL (function doesn't accept `freq_minutes` kwarg).

- [ ] **Step 4:** Modify `compute_dom_load_gradient` to accept
  `freq_minutes` kwarg defaulting to 60 (preserves hourly behavior):
  ```python
  def compute_dom_load_gradient(df: pd.DataFrame,
                                 freq_minutes: int = 60) -> pd.DataFrame:
      """Compute |Δ load| / freq_minutes. Default freq_minutes=60 (hourly)."""
      out = df.copy()
      out["dom_load_gradient_abs_mw_per_min"] = (
          out["dom_load_mw"].diff().abs() / freq_minutes
      )
      return out
  ```
  Preserve existing default behavior (verified by existing hourly
  tests).

- [ ] **Step 5:** Run all `features` tests, verify PASS:
  ```bash
  .venv/bin/pytest tests/preprocessing/test_features.py -v
  ```
  Expected: all PASS, including pre-existing tests + the new one.

- [ ] **Step 6:** Commit:
  ```bash
  git add src/surg/preprocessing/features.py tests/preprocessing/test_features.py
  git commit -m "feat(preprocessing): generalize compute_dom_load_gradient for arbitrary freq_minutes"
  ```

---

## Task 4: 5-min loaders module

**Files:**
- Create: `src/surg/preprocessing/loaders_5min.py`
- Test: `tests/preprocessing/test_loaders_5min.py`

- [ ] **Step 1:** Write failing tests for three functions in
  `tests/preprocessing/test_loaders_5min.py`:
  ```python
  """Tests for src/surg/preprocessing/loaders_5min.py — sub-q1 item #8."""
  from pathlib import Path
  import pandas as pd
  import pytest
  from surg.preprocessing.loaders_5min import (
      load_rt_lmp_5min, load_dom_load_5min, forward_fill_reserves_to_5min,
  )


  def test_load_rt_lmp_5min_returns_5min_frequency(tmp_path):
      # Synthetic raw 5-min LMP file
      raw_dir = tmp_path / "rt_fivemin_hrl_lmps" / "2026"
      raw_dir.mkdir(parents=True)
      df = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range(
              "2026-04-15", periods=12, freq="5min"
          ),
          "pnode_id": [35010371] * 12,
          "pnode_name": ["LOUDOUN"] * 12,
          "voltage": [500] * 12,
          "type": ["EHV"] * 12,
          "zone": ["DOM"] * 12,
          "system_energy_price_rt": list(range(12)),
          "total_lmp_rt": list(range(20, 32)),
          "congestion_price_rt": [0.0] * 12,
          "marginal_loss_price_rt": [1.0] * 12,
      })
      df.to_parquet(raw_dir / "test.parquet")
      result = load_rt_lmp_5min(tmp_path)
      assert len(result) == 12
      assert "datetime_beginning_ept" in result.columns
      assert "total_lmp_rt" in result.columns
      # frequency check
      diffs = result["datetime_beginning_ept"].diff().dropna()
      assert (diffs == pd.Timedelta(minutes=5)).all()


  def test_load_dom_load_5min_dedupes_overlap(tmp_path):
      raw_dir = tmp_path / "inst_load"
      raw_dir.mkdir(parents=True)
      df1 = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range(
              "2026-04-15", periods=8, freq="5min"
          ),
          "area": ["PJM SOUTHERN REGION"] * 8,
          "instantaneous_load": [10000.0 + i * 50 for i in range(8)],
      })
      df2 = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range(
              "2026-04-15 00:25", periods=8, freq="5min"
          ),
          "area": ["PJM SOUTHERN REGION"] * 8,
          "instantaneous_load": [10000.0 + i * 50 for i in range(5, 13)],
      })
      df1.to_parquet(raw_dir / "f1.parquet")
      df2.to_parquet(raw_dir / "f2.parquet")
      result = load_dom_load_5min(tmp_path)
      # 8 + 8 - 3 overlap = 13 unique timestamps
      assert len(result) == 13
      assert result["datetime_beginning_ept"].is_monotonic_increasing
      assert result["datetime_beginning_ept"].is_unique


  def test_forward_fill_reserves_to_5min_preserves_hourly_value():
      hourly = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range(
              "2026-04-15", periods=2, freq="h"
          ),
          "sync_reserve_clearing_price_rt": [5.0, 7.0],
          "primary_reserve_clearing_price_rt": [3.0, 4.0],
      })
      target_5min = pd.date_range("2026-04-15", periods=24, freq="5min")
      result = forward_fill_reserves_to_5min(hourly, target_5min)
      assert len(result) == 24
      # First 12 obs (hour 0): SR = 5.0
      assert (result["sync_reserve_clearing_price_rt"].iloc[:12] == 5.0).all()
      # Next 12 obs (hour 1): SR = 7.0
      assert (result["sync_reserve_clearing_price_rt"].iloc[12:] == 7.0).all()
  ```
- [ ] **Step 2:** Run tests, verify all FAIL (module doesn't exist):
  ```bash
  .venv/bin/pytest tests/preprocessing/test_loaders_5min.py -v
  ```
  Expected: ImportError or 3× FAIL.

- [ ] **Step 3:** Implement `src/surg/preprocessing/loaders_5min.py`:
  ```python
  """5-min preprocessing loaders for sub-q1 item #8 companion run.

  Mirrors `loaders.py` but at native 5-min granularity. Reserves are
  forward-filled from hourly because PJM's 5-min reserve loader
  rewrite is out of scope for item #8.
  """
  from pathlib import Path
  import pandas as pd


  def load_rt_lmp_5min(data_root: Path) -> pd.DataFrame:
      """Load all `rt_fivemin_hrl_lmps` parquet files under data_root.

      Returns a DataFrame at native 5-min frequency, sorted +
      deduplicated.
      """
      feed_dir = Path(data_root) / "rt_fivemin_hrl_lmps"
      if not feed_dir.exists():
          return pd.DataFrame()
      files = sorted(feed_dir.rglob("*.parquet"))
      if not files:
          return pd.DataFrame()
      df = pd.concat(
          [pd.read_parquet(f) for f in files], ignore_index=True
      )
      df["datetime_beginning_ept"] = pd.to_datetime(
          df["datetime_beginning_ept"], errors="raise"
      )
      df = (df.drop_duplicates(
                subset=["datetime_beginning_ept", "pnode_id"])
              .sort_values(["pnode_id", "datetime_beginning_ept"])
              .reset_index(drop=True))
      return df


  def load_dom_load_5min(data_root: Path) -> pd.DataFrame:
      """Load all `inst_load` parquet files; return 5-min DOM-zone
      load filtered to PJM SOUTHERN REGION (DOM proxy per
      pjm-api-constraints.md), deduped by timestamp."""
      feed_dir = Path(data_root) / "inst_load"
      if not feed_dir.exists():
          return pd.DataFrame()
      files = sorted(feed_dir.rglob("*.parquet"))
      if not files:
          return pd.DataFrame()
      df = pd.concat(
          [pd.read_parquet(f) for f in files], ignore_index=True
      )
      df["datetime_beginning_ept"] = pd.to_datetime(
          df["datetime_beginning_ept"], errors="raise"
      )
      df = df[df["area"] == "PJM SOUTHERN REGION"].copy()
      df = df.rename(columns={"instantaneous_load": "dom_load_mw"})
      df = (df[["datetime_beginning_ept", "dom_load_mw"]]
              .drop_duplicates(subset=["datetime_beginning_ept"])
              .sort_values("datetime_beginning_ept")
              .reset_index(drop=True))
      return df


  def forward_fill_reserves_to_5min(
      hourly_reserves: pd.DataFrame,
      target_5min_index: pd.DatetimeIndex,
  ) -> pd.DataFrame:
      """Forward-fill hourly reserve clearing prices to 5-min
      frequency. The hourly value V at hour H applies to all 5-min
      stamps in [H, H+1)."""
      target_df = pd.DataFrame({"datetime_beginning_ept": target_5min_index})
      target_df["_hour_floor"] = target_df["datetime_beginning_ept"].dt.floor("h")
      hourly_indexed = hourly_reserves.set_index("datetime_beginning_ept")
      target_df["sync_reserve_clearing_price_rt"] = target_df["_hour_floor"].map(
          hourly_indexed["sync_reserve_clearing_price_rt"]
      )
      target_df["primary_reserve_clearing_price_rt"] = target_df["_hour_floor"].map(
          hourly_indexed["primary_reserve_clearing_price_rt"]
      )
      return target_df.drop(columns=["_hour_floor"])
  ```

- [ ] **Step 4:** Run tests, verify PASS:
  ```bash
  .venv/bin/pytest tests/preprocessing/test_loaders_5min.py -v
  ```
  Expected: 3 PASS.

- [ ] **Step 5:** Commit:
  ```bash
  git add src/surg/preprocessing/loaders_5min.py tests/preprocessing/test_loaders_5min.py
  git commit -m "feat(preprocessing): 5-min loaders for LMP, DOM load, forward-fill reserves (item #8)"
  ```

---

## Task 5: Joint 5-min panel builder (`build_5min.py`)

**Files:**
- Create: `src/surg/preprocessing/build_5min.py`
- Test: `tests/preprocessing/test_build_5min.py`

- [ ] **Step 1:** Write failing test in
  `tests/preprocessing/test_build_5min.py`. Test verifies: output
  has 5-min frequency, joint Z+LMP+reserves columns, filter columns
  (`passes_proposal_filter`, `is_shoulder`, `is_2_to_5_am`), sorted
  + unique timestamps per pnode.
  ```python
  """Tests for src/surg/preprocessing/build_5min.py — sub-q1 item #8."""
  from pathlib import Path
  import pandas as pd
  import pytest
  from surg.preprocessing.build_5min import build_joint_5min_panel


  def _make_synthetic_data_root(tmp_path: Path) -> Path:
      """Build a minimal data_root with 1 day of synthetic 5-min data."""
      lmp_dir = tmp_path / "rt_fivemin_hrl_lmps" / "2026"
      lmp_dir.mkdir(parents=True)
      lmp_df = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range("2026-04-15", periods=288, freq="5min"),
          "pnode_id": [35010371] * 288,
          "pnode_name": ["LOUDOUN"] * 288,
          "voltage": [500] * 288,
          "type": ["EHV"] * 288,
          "zone": ["DOM"] * 288,
          "system_energy_price_rt": [25.0] * 288,
          "total_lmp_rt": [30.0 + i * 0.1 for i in range(288)],
          "congestion_price_rt": [0.0] * 288,
          "marginal_loss_price_rt": [1.0] * 288,
      })
      lmp_df.to_parquet(lmp_dir / "test.parquet")

      load_dir = tmp_path / "inst_load"
      load_dir.mkdir(parents=True)
      load_df = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range("2026-04-15", periods=288, freq="5min"),
          "area": ["PJM SOUTHERN REGION"] * 288,
          "instantaneous_load": [10000.0 + i * 5 for i in range(288)],
      })
      load_df.to_parquet(load_dir / "test.parquet")

      reserves_dir = tmp_path / "reserve_market_results"
      reserves_dir.mkdir(parents=True)
      reserves_df = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range("2026-04-15", periods=24 * 12, freq="5min"),
          "locale": ["MAD"] * (24 * 12),
          "service": (["SR"] * 12 + ["PR"] * 12) * 12,
          "mcp": [5.0] * (24 * 12),
      })
      reserves_df.to_parquet(reserves_dir / "test.parquet")
      return tmp_path


  def test_build_joint_5min_panel_basic(tmp_path):
      data_root = _make_synthetic_data_root(tmp_path)
      panel = build_joint_5min_panel(data_root=data_root)
      assert len(panel) > 0
      # 5-min frequency check (per pnode)
      first_pnode = panel.iloc[0]["pnode_id"]
      one_pnode = panel[panel["pnode_id"] == first_pnode].sort_values("datetime_beginning_ept")
      diffs = one_pnode["datetime_beginning_ept"].diff().dropna()
      assert (diffs == pd.Timedelta(minutes=5)).all()
      # Required columns
      required = [
          "datetime_beginning_ept", "pnode_id", "total_lmp_rt",
          "congestion_price_rt", "dom_load_mw",
          "dom_load_gradient_abs_mw_per_min",
          "sync_reserve_clearing_price_rt",
          "passes_proposal_filter", "is_shoulder", "is_2_to_5_am",
      ]
      for col in required:
          assert col in panel.columns, f"Missing column: {col}"
      # Filter logic spot check: 2:30 AM in April (shoulder) = in filter
      assert panel[
          (panel["datetime_beginning_ept"] == pd.Timestamp("2026-04-15 02:30"))
      ]["passes_proposal_filter"].iloc[0] == True
      # 12 noon = NOT in filter
      assert panel[
          (panel["datetime_beginning_ept"] == pd.Timestamp("2026-04-15 12:00"))
      ]["passes_proposal_filter"].iloc[0] == False
  ```
- [ ] **Step 2:** Run test, verify FAIL.

- [ ] **Step 3:** Implement `src/surg/preprocessing/build_5min.py`.
  Mirror the structure of existing `build.py`. Key steps in the
  function `build_joint_5min_panel(data_root)`:
  1. Load 5-min LMP via `loaders_5min.load_rt_lmp_5min`.
  2. Load 5-min DOM load via `loaders_5min.load_dom_load_5min`.
  3. Load hourly reserves via existing `loaders.load_reserve_market_results`.
  4. Compute Z (5-min DOM load gradient) via the modified
     `compute_dom_load_gradient(df, freq_minutes=5)`.
  5. Per-pnode merge: LMP + Z (on `datetime_beginning_ept`).
  6. Forward-fill reserves to 5-min via
     `forward_fill_reserves_to_5min`.
  7. Restrict to the joint window = intersection of LMP and DOM-load
     timestamp coverage.
  8. Add filter columns (`is_shoulder`, `is_2_to_5_am`,
     `passes_proposal_filter` = `is_shoulder & is_2_to_5_am`)
     using the same logic as hourly `build.py`.

  ```python
  """Joint 5-min analysis panel builder for sub-q1 item #8."""
  from pathlib import Path
  import pandas as pd
  from surg.preprocessing.loaders import load_reserve_market_results
  from surg.preprocessing.loaders_5min import (
      load_rt_lmp_5min, load_dom_load_5min, forward_fill_reserves_to_5min,
  )
  from surg.preprocessing.features import compute_dom_load_gradient

  SHOULDER_MONTHS = {3, 4, 5, 9, 10, 11}
  FILTER_HOURS = {2, 3, 4}  # 2-5 AM = hours 2,3,4 inclusive of 4:55


  def build_joint_5min_panel(data_root: Path) -> pd.DataFrame:
      lmp = load_rt_lmp_5min(data_root)
      dom_load = load_dom_load_5min(data_root)
      hourly_reserves = load_reserve_market_results(data_root)
      if lmp.empty or dom_load.empty:
          return pd.DataFrame()
      # Compute Z on dom_load
      dom_load = compute_dom_load_gradient(dom_load, freq_minutes=5)
      # Joint window
      tmin = max(lmp["datetime_beginning_ept"].min(),
                 dom_load["datetime_beginning_ept"].min())
      tmax = min(lmp["datetime_beginning_ept"].max(),
                 dom_load["datetime_beginning_ept"].max())
      lmp = lmp[(lmp["datetime_beginning_ept"] >= tmin) &
                (lmp["datetime_beginning_ept"] <= tmax)].copy()
      dom_load = dom_load[(dom_load["datetime_beginning_ept"] >= tmin) &
                          (dom_load["datetime_beginning_ept"] <= tmax)].copy()
      # Per-pnode merge: LMP + Z
      panel = lmp.merge(
          dom_load[["datetime_beginning_ept", "dom_load_mw",
                    "dom_load_gradient_abs_mw_per_min"]],
          on="datetime_beginning_ept", how="inner",
      )
      # Reserves forward-fill
      target_index = panel["datetime_beginning_ept"].sort_values().unique()
      reserves_5min = forward_fill_reserves_to_5min(
          hourly_reserves, pd.DatetimeIndex(target_index)
      )
      panel = panel.merge(reserves_5min, on="datetime_beginning_ept", how="left")
      # Filter columns
      ts = panel["datetime_beginning_ept"]
      panel["is_shoulder"] = ts.dt.month.isin(SHOULDER_MONTHS)
      panel["is_2_to_5_am"] = ts.dt.hour.isin(FILTER_HOURS)
      panel["passes_proposal_filter"] = panel["is_shoulder"] & panel["is_2_to_5_am"]
      panel = (panel.sort_values(["pnode_id", "datetime_beginning_ept"])
                    .reset_index(drop=True))
      return panel
  ```

- [ ] **Step 4:** Run test, verify PASS.

- [ ] **Step 5:** Run full panel build against on-disk data + write
  parquet:
  ```bash
  .venv/bin/python -c "
  from pathlib import Path
  from surg.preprocessing.build_5min import build_joint_5min_panel
  panel = build_joint_5min_panel(data_root=Path('data/raw'))
  panel.to_parquet('data/interim/analysis_panel_5min_joint.parquet')
  print('rows:', len(panel))
  print('window:', panel['datetime_beginning_ept'].min(), '→',
        panel['datetime_beginning_ept'].max())
  print('in-filter rows:', panel['passes_proposal_filter'].sum())
  print('pnodes:', panel['pnode_id'].nunique())
  "
  ```
  Expected: rows on the order of 30,000–80,000 (depends on freshness
  of pulls); window starts mid-April, ends today; in-filter rows ~1,000
  per pnode.

- [ ] **Step 6:** Commit:
  ```bash
  git add src/surg/preprocessing/build_5min.py tests/preprocessing/test_build_5min.py
  git commit -m "feat(preprocessing): joint 5-min panel builder (item #8 Part A)"
  ```

---

## Task 6: LMP-only 5-min panel builder

**Files:**
- Create: `src/surg/preprocessing/build_5min_lmp_only.py`
- Test: `tests/preprocessing/test_build_5min_lmp_only.py`

Same TDD pattern as Task 5 but simpler: panel = `load_rt_lmp_5min`
output only (no Z, no reserves, no filter). Used for Part B which
needs the full 6-month archive without proposal-filter constraints.

- [ ] **Step 1:** Write failing test that builds an LMP-only panel
  from a synthetic data root and asserts: 5-min frequency,
  `total_lmp_rt` column, no filter columns, all pnodes preserved.
- [ ] **Step 2:** Run test, verify FAIL.
- [ ] **Step 3:** Implement (~50 lines). Function
  `build_lmp_only_5min_panel(data_root)` calls
  `load_rt_lmp_5min` and returns the result with sorted +
  per-pnode-deduped index, no other transformation.
- [ ] **Step 4:** Run test, verify PASS.
- [ ] **Step 5:** Build the production LMP-only panel against
  on-disk data:
  ```bash
  .venv/bin/python -c "
  from pathlib import Path
  from surg.preprocessing.build_5min_lmp_only import build_lmp_only_5min_panel
  panel = build_lmp_only_5min_panel(data_root=Path('data/raw'))
  panel.to_parquet('data/interim/analysis_panel_5min_lmp_only.parquet')
  print('rows:', len(panel), 'pnodes:', panel['pnode_id'].nunique())
  "
  ```
  Expected: ~411,708 rows (matches the 6-month 11-pnode archive on
  disk).
- [ ] **Step 6:** Commit:
  ```bash
  git add src/surg/preprocessing/build_5min_lmp_only.py tests/preprocessing/test_build_5min_lmp_only.py
  git commit -m "feat(preprocessing): LMP-only 5-min panel builder (item #8 Part B)"
  ```

---

## Task 7: Island cluster bootstrap module

**Files:**
- Create: `src/surg/analysis/bootstrap_strategies.py`
- Test: `tests/analysis/test_bootstrap_strategies.py`

- [ ] **Step 1:** Write failing tests in
  `tests/analysis/test_bootstrap_strategies.py`:
  ```python
  """Tests for island cluster bootstrap (sub-q1 item #8)."""
  import numpy as np
  import pandas as pd
  import pytest
  from surg.analysis.bootstrap_strategies import (
      identify_islands, island_cluster_bootstrap,
  )


  def test_identify_islands_consecutive_5min_obs_form_one_island():
      ts = pd.DatetimeIndex(pd.date_range("2026-04-15 02:00", periods=36, freq="5min"))
      mask = pd.Series([True] * 36, index=range(36))
      island_ids = identify_islands(ts, mask, gap_threshold_minutes=10)
      assert island_ids.nunique() == 1
      assert (island_ids == island_ids.iloc[0]).all()


  def test_identify_islands_gap_creates_new_island():
      # Two 36-obs windows separated by a 21-hour gap
      ts1 = pd.date_range("2026-04-15 02:00", periods=36, freq="5min")
      ts2 = pd.date_range("2026-04-16 02:00", periods=36, freq="5min")
      ts = pd.DatetimeIndex(list(ts1) + list(ts2))
      mask = pd.Series([True] * 72, index=range(72))
      island_ids = identify_islands(ts, mask, gap_threshold_minutes=10)
      assert island_ids.nunique() == 2
      assert (island_ids.iloc[:36] == island_ids.iloc[0]).all()
      assert (island_ids.iloc[36:] == island_ids.iloc[36]).all()
      assert island_ids.iloc[0] != island_ids.iloc[36]


  def test_island_cluster_bootstrap_preserves_island_size():
      ts = pd.date_range("2026-04-15 02:00", periods=36, freq="5min")
      df = pd.DataFrame({
          "datetime_beginning_ept": ts,
          "value": np.arange(36).astype(float),
      })
      island_ids = pd.Series([0] * 36)
      rng = np.random.default_rng(42)
      boot_df = island_cluster_bootstrap(df, island_ids, rng)
      # Single island; resampling 1 island with replacement n times = identity (or repeat)
      assert len(boot_df) == 36


  def test_island_cluster_bootstrap_resamples_from_multiple_islands():
      df = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range("2026-04-15", periods=72, freq="5min"),
          "value": np.arange(72).astype(float),
      })
      island_ids = pd.Series([0] * 36 + [1] * 36)
      rng = np.random.default_rng(42)
      boot_df = island_cluster_bootstrap(df, island_ids, rng)
      assert len(boot_df) == 72  # K=2 islands resampled with replacement → K islands of size 36 each
  ```

- [ ] **Step 2:** Run tests, verify all FAIL.

- [ ] **Step 3:** Implement
  `src/surg/analysis/bootstrap_strategies.py`:
  ```python
  """Pure island cluster bootstrap (sub-q1 item #8).

  The proposal-filter creates 3-hour islands (2-5 AM) separated by
  21-hour gaps. Pair-bootstrap is invalid (within-island
  autocorrelation); naive block bootstrap is invalid (blocks cross
  gap boundaries). Pure island cluster bootstrap (Cameron-Gelbach-
  Miller-style) is the standard treatment.
  """
  from typing import Callable, Optional
  import numpy as np
  import pandas as pd


  def identify_islands(
      timestamps: pd.DatetimeIndex,
      filter_mask: pd.Series,
      gap_threshold_minutes: int = 10,
  ) -> pd.Series:
      """Assign each in-filter row an island id. Rows separated by a
      gap > gap_threshold_minutes are in different islands.

      Returns a Series of integer island ids, indexed like
      filter_mask. NaN for out-of-filter rows is NOT supported here;
      callers must pre-filter.
      """
      if len(timestamps) != len(filter_mask):
          raise ValueError("timestamps and filter_mask length mismatch")
      ts = pd.Series(timestamps)
      diffs_min = ts.diff().dt.total_seconds() / 60.0
      island_break = diffs_min > gap_threshold_minutes
      island_break.iloc[0] = True  # first row starts island 0
      island_ids = island_break.cumsum() - 1
      island_ids.index = filter_mask.index
      return island_ids.astype(int)


  def island_cluster_bootstrap(
      df: pd.DataFrame,
      island_ids: pd.Series,
      rng: np.random.Generator,
  ) -> pd.DataFrame:
      """Resample whole islands with replacement; return the
      resampled DataFrame."""
      if len(df) != len(island_ids):
          raise ValueError("df and island_ids length mismatch")
      unique_islands = island_ids.unique()
      K = len(unique_islands)
      sampled = rng.choice(unique_islands, size=K, replace=True)
      groups = {iid: df[island_ids == iid].copy() for iid in unique_islands}
      pieces = [groups[iid] for iid in sampled]
      return pd.concat(pieces, ignore_index=True)


  def bootstrap_dispatch(
      method: str,
      df: pd.DataFrame,
      stat_fn: Callable[[pd.DataFrame], np.ndarray],
      n_boot: int,
      rng: np.random.Generator,
      island_ids: Optional[pd.Series] = None,
  ) -> np.ndarray:
      """Dispatch to pair or cluster bootstrap. Returns array of
      shape (n_boot, n_stats) where n_stats is the length of
      stat_fn's return vector. Items #1-4 fit regressions producing
      vector-valued statistics (intercept + slope + per-year FE
      coefficients); item #6 produces a scalar (proportion). Both
      fit the (n_boot, n_stats) shape with n_stats=1 for scalars.

      stat_fn MUST return a 1-D np.ndarray (use np.array([x]) for
      scalars). Caller is responsible for naming the n_stats columns
      and computing percentile CIs / point estimates from the
      returned array.
      """
      first = np.atleast_1d(np.asarray(stat_fn(df.iloc[:0]) if False else stat_fn(df)))
      n_stats = len(first)
      replicates = np.empty((n_boot, n_stats))
      replicates[0] = first  # shouldn't reuse the un-bootstrapped sample as a bootstrap rep
      # Recompute properly: replicates[0..n_boot] all from bootstrap samples
      for b in range(n_boot):
          if method == "pair":
              idx = rng.choice(len(df), size=len(df), replace=True)
              boot_df = df.iloc[idx].reset_index(drop=True)
          elif method == "cluster":
              if island_ids is None:
                  raise ValueError("cluster method requires island_ids")
              boot_df = island_cluster_bootstrap(df, island_ids, rng)
          else:
              raise ValueError(f"Unknown bootstrap method: {method}")
          out = np.atleast_1d(np.asarray(stat_fn(boot_df)))
          if len(out) != n_stats:
              raise ValueError(
                  f"stat_fn returned length {len(out)} on bootstrap rep {b}, "
                  f"expected {n_stats} from the unbootstrapped sample"
              )
          replicates[b] = out
      return replicates
  ```

  **Rationale (per advisor blocker fix):** items #1–4 fit
  regressions producing vector statistics — Spec B continuous ξ(Z)
  yields intercept + slope; components decomposition produces 3
  coefficients per response var; year-FE diagnostic produces a slope
  coefficient PLUS one FE coefficient per year. A scalar
  `Callable → float` cannot represent these. The vector signature
  also accommodates item #6's scalar via `np.array([p_hat])`.

- [ ] **Step 4:** Run tests, verify all PASS.

- [ ] **Step 5:** Commit:
  ```bash
  git add src/surg/analysis/bootstrap_strategies.py tests/analysis/test_bootstrap_strategies.py
  git commit -m "feat(analysis): island cluster bootstrap module (sub-q1 item #8)"
  ```

---

## Task 8: Extend `run.py` CLI — skip flags + `--seed` + `--bootstrap-method`

**Why:** Verified 2026-05-15 — the existing `surg-analyze` CLI is
missing many flags that this plan needs. To run only items #1–4 + #6
(skipping TAR/QR/QR-full/GPD-median/mechanism/robustness/conditional_z),
to get deterministic output for the regression smoke gate, and to
toggle bootstrap method, the CLI must be extended.

**Files:**
- Modify: `src/surg/analysis/run.py`
- Test: `tests/analysis/test_run.py`

**New CLI flags to add:**

| Flag | Default | Purpose |
|---|---|---|
| `--seed` | `42` | Top-level seed; threaded into all module `run_*` calls. Replaces hardcoded constants in `run_all()`. |
| `--bootstrap-method` | `pair` | `{pair, cluster}`. Threaded into items #1–4 + #6 modules. |
| `--skip-tar` | `False` | Skip TAR (`tar.py`). |
| `--skip-qr` | `False` | Skip QR (`qr.py`). |
| `--skip-qr-full` | `False` | Skip QR-full (`qr_full.py`). |
| `--skip-gpd` | `False` | Skip GPD median-split (`gpd.py`, the `run_gpd` calls). |
| `--skip-mechanism` | `False` | Skip mechanism validation. |
| `--skip-robustness` | `False` | Skip subsample bootstrap. |
| `--skip-conditional-z` | `False` | Skip conditional-Z robustness battery (the 2026-05-14 A/C/F + Holm work). |
| `--skip-gpd-continuous` | `False` | Skip Spec B continuous ξ(Z) (item #1) — needed when running only item #6 in smoke mode. |
| `--tail-risk-pnodes` | `None` (= all) | Comma-separated subset of pnode labels to process for item #6 only. Used by smoke gate (`--tail-risk-pnodes primary`). |

- [ ] **Step 1:** Add the 11 new `add_argument` calls to
  `_build_arg_parser` in `run.py`. Each `--skip-*` is
  `action="store_true"`. `--seed` is `type=int, default=42`.
  `--bootstrap-method` uses `choices=["pair", "cluster"]`.
  `--tail-risk-pnodes` is a comma-separated string parsed downstream
  into a tuple.

- [ ] **Step 2:** Add corresponding kwargs to `run_all()` signature
  (one per new CLI flag) and thread them through:
  - Wrap the always-on calls (TAR loop, QR, mechanism, subsample,
    QR-full loop, GPD loop, conditional_z, gpd_continuous loop) in
    `if not skip_X:` blocks.
  - Replace any hardcoded `seed=...` constants in `run_all()` with
    `seed=seed` (thread the parameter through).
  - For items #1–4 + #6 only: pass `bootstrap_method=bootstrap_method`
    to each module's `run_*` call.
  - For item #6 only: filter `PNODE_RESPONSES` by
    `tail_risk_pnodes` if provided.

- [ ] **Step 3:** Update `main()` to pass the new args:
  ```python
  run_all(
      panel=panel, events=events,
      out_root=Path(args.out_root),
      seed=args.seed,
      bootstrap_method=args.bootstrap_method,
      tail_risk_pnodes=args.tail_risk_pnodes,
      skip_tar=args.skip_tar,
      skip_qr=args.skip_qr,
      skip_qr_full=args.skip_qr_full,
      skip_gpd=args.skip_gpd,
      skip_mechanism=args.skip_mechanism,
      skip_robustness=args.skip_robustness,
      skip_conditional_z=args.skip_conditional_z,
      skip_gpd_continuous=args.skip_gpd_continuous,
      # ... existing kwargs unchanged ...
  )
  ```

- [ ] **Step 4:** Write tests in `tests/analysis/test_run.py`:
  - Existing tests must still pass (defaults preserve current
    behavior).
  - New test: `--seed` plumbing — mock `run_year_fe_diagnostic` and
    assert that running `surg-analyze --seed 99 ...` calls it with
    `seed=99` (not the default). This is a plumbing check, not a
    statistical check (degenerate data could yield identical
    outputs by coincidence under different seeds).
  - New test: `--skip-tar` causes no `tar/` output dir.
  - New test: `--bootstrap-method cluster` is accepted by the CLI
    parser and threaded into `run_all()`.

- [ ] **Step 5:** Run all tests:
  ```bash
  .venv/bin/pytest tests/analysis/ -v
  ```
  Expected: all PASS.

- [ ] **Step 6:** Commit:
  ```bash
  git add src/surg/analysis/run.py tests/analysis/test_run.py
  git commit -m "feat(analysis): CLI extension — skip flags + --seed + --bootstrap-method (item #8)"
  ```

---

## Tasks 9–13: Refactor items #6, #1, #2, #3, #4 (one per task)

**Why one-per-task (per advisor):** failing on module 1 saves modules
2–5 from being broken in the same way. Each refactor is followed
immediately by its regression test.

**Per-task pattern (repeat for each module):**

- **Step 1:** Identify all bootstrap-call sites in the module
  (currently hardcoded pair-bootstrap). For each, replace with a
  call to `bootstrap_strategies.bootstrap_dispatch(method=cfg.bootstrap_method, ...)`.
  Pass `island_ids` when method is `cluster`; pass None when `pair`.
- **Step 2:** Verify the module's existing unit tests still pass:
  ```bash
  .venv/bin/pytest tests/analysis/test_<module>.py -v
  ```
  Expected: all PASS.
- **Step 3:** Run the regression test (must equal pre-refactor
  reference within bootstrap-seed tolerance):
  ```bash
  .venv/bin/pytest tests/regression/test_hourly_pair_bootstrap_equivalence.py::test_<module> -v
  ```
  Expected: PASS. If FAIL, halt + commit + report.
- **Step 4:** Commit:
  ```bash
  git add src/surg/analysis/<module>.py tests/regression/test_hourly_pair_bootstrap_equivalence.py
  git commit -m "refactor(analysis): inject bootstrap strategy into <module> (item #8)"
  ```

### Task 9: Refactor `tail_risk_curves.py` (item #6) + create regression test file

**Step 0 (NEW — done once before any module is refactored):** Create
the regression test file skeleton:

- [ ] Create `tests/regression/test_hourly_pair_bootstrap_equivalence.py`
  with the skeleton shown in an inline regression-test skeleton
  (preserved here):
  ```python
  """Regression tests for items #1-4 + #6 post-cluster-bootstrap-refactor.

  Asserts: with --bootstrap-method=pair (default), modified modules
  produce numerically equivalent output to the captured pre-refactor
  reference fixtures.

  Tolerance policy (per CAPTURE_PARAMS.json):
  - Point estimates: exact match (rel diff < 1e-9). These do NOT
    depend on RNG and must be identical pre/post refactor.
  - CI bounds + bootstrap-derived stats: 2% relative tolerance. The
    refactor changes the order in which rng.choice() is called (the
    same seed produces a different consumption sequence), so CI bounds
    drift slightly even though the bootstrap method is unchanged.
  """
  import json
  from pathlib import Path
  import pytest

  REF_DIR = Path("tests/regression/hourly_reference")
  POINT_TOLERANCE_REL = 1e-9
  CI_TOLERANCE_REL = 0.02


  def _load_json(p: Path) -> dict:
      with open(p) as f:
          return json.load(f)


  def _is_ci_field(key_path: str) -> bool:
      """A leaf key is CI/bootstrap-derived if ANY:
        (a) exact 'ci', (b) ends '_ci', (c) contains '_ci_',
        (d) contains 'p_value', (e) contains 'bootstrap',
        (f) contains 'boot_se' or 'boot_std'.
      Per CAPTURE_PARAMS.json ci_field_detection_rule."""
      last = key_path.split(".")[-1].split("[")[0]
      if last == "ci": return True
      if last.endswith("_ci"): return True
      if "_ci_" in last: return True
      if "p_value" in last: return True
      if "bootstrap" in last: return True
      if "boot_se" in last or "boot_std" in last: return True
      return False


  def _assert_numeric_equivalence(reference, current, path=""):
      """Recursive numeric comparison with CI-aware tolerance."""
      assert type(reference) == type(current), f"Type mismatch at {path}"
      if isinstance(reference, dict):
          assert set(reference.keys()) == set(current.keys()), \
              f"Key mismatch at {path}: ref={set(reference.keys())} cur={set(current.keys())}"
          for k in reference:
              _assert_numeric_equivalence(reference[k], current[k], f"{path}.{k}")
      elif isinstance(reference, list):
          assert len(reference) == len(current), f"Length mismatch at {path}"
          for i, (r, c) in enumerate(zip(reference, current)):
              _assert_numeric_equivalence(r, c, f"{path}[{i}]")
      elif isinstance(reference, float):
          tol = CI_TOLERANCE_REL if _is_ci_field(path) else POINT_TOLERANCE_REL
          if reference == 0:
              # Absolute tolerance for zero references
              abs_tol = tol if tol < 1e-3 else 1e-3
              assert abs(current) < abs_tol, \
                  f"Numeric mismatch at {path}: ref=0, cur={current}, abs_tol={abs_tol}"
          else:
              rel = abs(reference - current) / abs(reference)
              assert rel < tol, \
                  f"Numeric mismatch at {path}: ref={reference}, cur={current}, " \
                  f"rel_diff={rel:.2e}, tol={tol:.2e}"
      else:
          # Strings, bools, None, ints — exact match
          assert reference == current, f"Mismatch at {path}: ref={reference}, cur={current}"
  ```

**Step 1+ (the per-task refactor pattern):** Apply the pattern from
the section header above. Bootstrap call sites in
`tail_risk_curves.py` are in
`compute_exceedance_probability_with_ci`, currently using
`np.random.choice` directly for pair-bootstrap. Refactor to call
`bootstrap_strategies.bootstrap_dispatch(method=...)`.

After refactor, add the per-module test function to the regression
test file:
```python
def test_tail_risk_curves_pair_bootstrap_equivalence():
    """Regenerate item #6 outputs with --bootstrap-method=pair (default)
    and seed=42 against the panel slice; assert numeric equivalence
    to the captured reference."""
    from surg.analysis.tail_risk_curves import run_tail_risk_curves
    import pandas as pd
    from tempfile import TemporaryDirectory

    panel = pd.read_parquet("data/interim/analysis_panel.parquet")
    with TemporaryDirectory() as tmp:
        run_tail_risk_curves(
            panel=panel, out_root=Path(tmp),
            n_boot=50, seed=42,
            bootstrap_method="pair",
        )
        for ref_file in (REF_DIR / "tail_risk_curves").glob("*.json"):
            cur = _load_json(Path(tmp) / ref_file.name)
            ref = _load_json(ref_file)
            _assert_numeric_equivalence(ref, cur, ref_file.name)
```

### Task 10: Refactor `gpd_continuous.py` (item #1, Spec B)

(Bootstrap is in the `boot_continuous_xi_z` function. Resample
within each pnode group; preserve the existing per-pnode bootstrap
loop.)

### Task 11: Refactor `gpd_components.py` (item #2)

Apply the per-task pattern from the section header. Item #2's
reference fixture WAS captured (after the schema v2 panel rebuild
during Setup-2), so the regression test applies normally.

### Task 12: Refactor `year_fe_diagnostic.py` (item #3)

### Task 13: Refactor `ashburn_diagnostic.py` (item #4)

---

## Task 14: Production-data smoke gate (item #6 + item #3)

**Why (per advisor):** before launching the full battery, exercise
both proportion (item #6) and regression (item #3) bootstrap paths
on real data. Catches integration issues at low cost.

- [ ] **Step 1:** Run item #6 on `primary` only with `n_boot=20`
  using the new CLI flags from Task 8:
  ```bash
  .venv/bin/surg-analyze \
      --panel data/interim/analysis_panel_5min_joint.parquet \
      --out-root outputs_5min/joint_30d/ \
      --bootstrap-method cluster \
      --tail-risk-n-boot 20 \
      --tail-risk-pnodes primary \
      --seed 42 \
      --skip-tar --skip-qr --skip-qr-full --skip-gpd \
      --skip-mechanism --skip-robustness --skip-conditional-z \
      --skip-gpd-continuous --skip-gpd-components \
      --skip-year-fe-diagnostic --skip-ashburn-diagnostic
  ```
  Expected: completes in < 5 minutes; produces non-empty JSON.

- [ ] **Step 2:** Verify executional health (NOT statistical
  quality): JSON exists, point estimates are finite, schema matches.
  ```bash
  .venv/bin/python -c "
  import json
  with open('outputs_5min/joint_30d/tail_risk_curves/primary.json') as f:
      d = json.load(f)
  for decile in d['results']['total_lmp']:
      for thr in decile['by_threshold'].values():
          assert isinstance(thr['p_hat'], (int, float))
          assert thr['p_hat'] >= 0 and thr['p_hat'] <= 1
  print('Smoke gate item #6: PASS')
  "
  ```

- [ ] **Step 3:** Run item #3 (year_fe_diagnostic) on `primary` only
  with `n_boot=20`:
  ```bash
  .venv/bin/surg-analyze \
      --panel data/interim/analysis_panel_5min_joint.parquet \
      --out-root outputs_5min/joint_30d/ \
      --bootstrap-method cluster \
      --year-fe-n-boot 20 \
      --seed 42 \
      --skip-tar --skip-qr --skip-qr-full --skip-gpd \
      --skip-mechanism --skip-robustness --skip-conditional-z \
      --skip-gpd-continuous --skip-gpd-components \
      --skip-ashburn-diagnostic --skip-tail-risk-curves
  ```
  (Note: there's no `--year-fe-pnodes primary` flag, so
  year_fe_diagnostic runs all pnodes; `n_boot=20` keeps wall low.)
  Expected: completes in < 5 min, finite point estimates.

- [ ] **Step 4:** Verify item #3 health:
  ```bash
  .venv/bin/python -c "
  import json
  from pathlib import Path
  for p in Path('outputs_5min/joint_30d/year_fe_diagnostic').glob('*.json'):
      d = json.load(open(p))
      print(p.name, 'OK' if 'pnode_label' in d else 'BAD')
  "
  ```
  Expected: each pnode JSON valid.

- [ ] **Step 5:** If both pass, proceed to Task 15. If either fails:
  ```bash
  git add -A
  git commit -m "WIP: smoke gate failure on item <X>; halting per plan"
  ```
  Halt the autonomous run and write a status update.

---

## Task 15: Re-run hourly item #6 on the actual overlap window (like-for-like comparator)

**Why (per advisor):** the cross-resolution summary must use a
matched-window hourly comparator, NOT the 3.6y hourly. Per advisor's
window-overlap blocker fix: explicitly compute the overlap window
(it may be < 30 days if the on-disk hourly panel ends before the
freshly-pulled 5-min panel) and document the actual window in the
summary metadata.

- [ ] **Step 1:** Compute the actual overlap window + write a
  matched-window hourly slice. This explicitly handles the case
  where the hourly panel on disk ends before today (per advisor:
  the on-disk hourly panel may end ~2026-05-07 while the fresh 5-min
  panel ends today):
  ```bash
  .venv/bin/python <<'EOF'
  import pandas as pd
  import json
  from pathlib import Path

  panel_hourly = pd.read_parquet('data/interim/analysis_panel.parquet')
  panel_5min   = pd.read_parquet('data/interim/analysis_panel_5min_joint.parquet')

  tmin = max(panel_5min['datetime_beginning_ept'].min(),
             panel_hourly['datetime_beginning_ept'].min())
  tmax = min(panel_5min['datetime_beginning_ept'].max(),
             panel_hourly['datetime_beginning_ept'].max())
  overlap_days = (tmax - tmin).total_seconds() / 86400

  # Slice BOTH panels to the overlap (write the hourly slice; the 5-min
  # panel for cross-resolution summary will also be sliced in Task 19)
  hourly_overlap = panel_hourly[
      (panel_hourly['datetime_beginning_ept'] >= tmin.floor('h')) &
      (panel_hourly['datetime_beginning_ept'] <= tmax.floor('h'))
  ]
  hourly_overlap.to_parquet('data/interim/analysis_panel_hourly_overlap.parquet')

  meta = {
      'overlap_window_start': tmin.isoformat(),
      'overlap_window_end': tmax.isoformat(),
      'overlap_days': round(overlap_days, 1),
      'panel_hourly_max': panel_hourly['datetime_beginning_ept'].max().isoformat(),
      'panel_5min_max': panel_5min['datetime_beginning_ept'].max().isoformat(),
      'note': 'Overlap window is the intersection. If panel_hourly_max < panel_5min_max, the hourly panel was not refreshed to today.',
  }
  outdir = Path('outputs_5min/hourly_overlap_for_comparison')
  outdir.mkdir(parents=True, exist_ok=True)
  with open(outdir / 'overlap_window.json', 'w') as f:
      json.dump(meta, f, indent=2)
  print('Overlap window:', tmin, '→', tmax, f'({overlap_days:.1f} days)')
  EOF
  ```

  **Decision point:** if `overlap_days < 14`, the like-for-like
  comparison is too thin to be useful. In that case, ALSO refresh
  the hourly panel via the existing `build_analysis_panel` against
  fresh `rt_hrl_lmps` data (added by an extra `surg-pull` of the
  delta window). Adds ~5 min. Trigger: read `overlap_days` from the
  printed line above; if < 14, run:
  ```bash
  .venv/bin/surg-pull --feed rt_hrl_lmps --type EHV \
      --start-date "$(date -v-7d +%Y-%m-%d)" \
      --end-date "$(date +%Y-%m-%d)" \
      --output "data/raw/rt_hrl_lmps/2026/dom_targets__delta_to_$(date +%Y-%m-%d).parquet"
  .venv/bin/python -c "
  from pathlib import Path
  from surg.preprocessing.build import build_analysis_panel
  panel = build_analysis_panel(data_root=Path('data/raw'))
  panel.to_parquet('data/interim/analysis_panel.parquet')
  "
  # Re-compute overlap window after refresh; re-slice
  ```

- [ ] **Step 2:** Run item #6 hourly with full n_boot on the
  matched-window slice:
  ```bash
  .venv/bin/surg-analyze \
      --panel data/interim/analysis_panel_hourly_overlap.parquet \
      --out-root outputs_5min/hourly_overlap_for_comparison/ \
      --bootstrap-method pair \
      --tail-risk-n-boot 200 \
      --seed 42 \
      --skip-tar --skip-qr --skip-qr-full --skip-gpd \
      --skip-mechanism --skip-robustness --skip-conditional-z \
      --skip-gpd-continuous --skip-gpd-components \
      --skip-year-fe-diagnostic --skip-ashburn-diagnostic
  ```
  Expected: < 1 minute wall. Outputs land in
  `outputs_5min/hourly_overlap_for_comparison/tail_risk_curves/`.

- [ ] **Step 3:** Commit metadata:
  ```bash
  echo "Like-for-like hourly comparator built at outputs_5min/hourly_overlap_for_comparison/. Window metadata at outputs_5min/hourly_overlap_for_comparison/overlap_window.json."
  ```
  (Output JSON files are gitignored; metadata file lives alongside.)

---

## Task 16: Part A production run (full battery, full n_boot)

**Why:** the headline. All five modules at production n_boot on the
joint 30-day panel with cluster bootstrap.

- [ ] **Step 1:** Run all five modules in one orchestrator
  invocation (using corrected flag names from Task 8 CLI extension):
  ```bash
  .venv/bin/surg-analyze \
      --panel data/interim/analysis_panel_5min_joint.parquet \
      --out-root outputs_5min/joint_30d/ \
      --bootstrap-method cluster \
      --continuous-n-boot 1000 \
      --components-n-boot 500 \
      --year-fe-n-boot 500 \
      --tail-risk-n-boot 200 \
      --seed 42 \
      --skip-tar --skip-qr --skip-qr-full --skip-gpd \
      --skip-mechanism --skip-robustness --skip-conditional-z \
      2>&1 | tee outputs_5min/joint_30d/production_run.log
  ```
  Expected wall: 2–4 hours. On any failure: halt + commit current
  state with `WIP:` prefix + report.

- [ ] **Step 2:** Verify all 5 module output directories exist + are
  non-empty:
  ```bash
  for m in tail_risk_curves gpd_continuous gpd_components year_fe_diagnostic ashburn_diagnostic; do
      n=$(find outputs_5min/joint_30d/$m -name "*.json" | wc -l)
      echo "$m: $n JSON files"
  done
  ```

- [ ] **Step 3:** Commit log:
  ```bash
  git add outputs_5min/joint_30d/production_run.log 2>/dev/null || true
  echo "Part A production run complete. Outputs at outputs_5min/joint_30d/"
  ```
  (Output JSONs/PNGs are gitignored.)

---

## Task 17: Build Part B `spike_exceedance_comparison` module

**Files:**
- Create: `src/surg/analysis/spike_exceedance_comparison.py`
- Test: `tests/analysis/test_spike_exceedance_comparison.py`

- [ ] **Step 1:** Write failing tests with synthetic input + known
  hidden-fraction expectations:
  ```python
  """Tests for spike_exceedance_comparison.py — sub-q1 item #8 Part B."""
  import json
  from pathlib import Path
  import pandas as pd
  import pytest
  from surg.analysis.spike_exceedance_comparison import (
      compute_per_pnode_metrics, run_spike_exceedance_comparison,
  )


  def test_hidden_fraction_basic():
      # Hour with 12 5-min obs: one spike of $600, rest at $25
      # Mean = (600 + 11*25) / 12 = 72.9 < $100, so hourly hides the $100+ spike
      lmp_5min = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range("2026-04-15", periods=12, freq="5min"),
          "pnode_id": [35010371] * 12,
          "total_lmp_rt_5min": [600.0] + [25.0] * 11,
      })
      lmp_hourly = pd.DataFrame({
          "datetime_beginning_ept": [pd.Timestamp("2026-04-15 00:00")],
          "pnode_id": [35010371],
          "total_lmp_rt": [72.92],  # PJM-published hourly aggregation, close to mean-of-12
      })
      result = compute_per_pnode_metrics(
          lmp_5min, lmp_hourly, pnode_id=35010371,
          thresholds=[100, 250, 500, 1000],
      )
      m100 = result["by_threshold"]["100"]
      assert m100["n_5min_exceedances"] == 1
      assert m100["n_hourly_published_exceedances"] == 0
      assert m100["n_hidden_by_hourly"] == 1
      assert m100["hidden_fraction"] == 1.0


  def test_hidden_fraction_zero_5min_exceedances_returns_nan():
      lmp_5min = pd.DataFrame({
          "datetime_beginning_ept": pd.date_range("2026-04-15", periods=12, freq="5min"),
          "pnode_id": [35010371] * 12,
          "total_lmp_rt_5min": [25.0] * 12,
      })
      lmp_hourly = pd.DataFrame({
          "datetime_beginning_ept": [pd.Timestamp("2026-04-15 00:00")],
          "pnode_id": [35010371],
          "total_lmp_rt": [25.0],
      })
      result = compute_per_pnode_metrics(
          lmp_5min, lmp_hourly, pnode_id=35010371,
          thresholds=[100, 250],
      )
      m100 = result["by_threshold"]["100"]
      assert m100["n_5min_exceedances"] == 0
      import math
      assert math.isnan(m100["hidden_fraction"])
      assert m100["n_below_inference_floor"] == True
  ```

- [ ] **Step 2:** Run tests, verify FAIL.

- [ ] **Step 3:** Implement
  `src/surg/analysis/spike_exceedance_comparison.py`. Key functions:
  - `compute_per_pnode_metrics(lmp_5min, lmp_hourly, pnode_id, thresholds) → dict`
  - `aggregate_cross_pnode_summary(per_pnode_results) → dict`
  - `plot_hidden_fraction(per_pnode_dict, out_path)`
  - `run_spike_exceedance_comparison(panel_5min, panel_hourly, out_root, thresholds=[50, 100, 250, 500, 1000])`

  **Implementation requirements (per advisor carry-forwards):**
  - Import `compute_threshold_percentiles` from
    `surg.analysis.tail_risk_curves` (do not duplicate). The
    function is the de-facto authority for the percentile
    annotation pattern; coupling the modules is justified.
  - Annotate each threshold with its empirical percentile in the
    6-month panel (e.g., `"$500 (p99.2 total_lmp)"`) using the
    imported helper. Annotation goes in the per-pnode JSON +
    headline plot legends.
  - Handle divide-by-zero explicitly: when
    `n_5min_exceedances == 0`, set `hidden_fraction = float('nan')`
    and `n_below_inference_floor = True`. Do NOT raise.
  - Join 5-min ↔ hourly on `(pnode_id, hour_floor(timestamp))`.
    Hours where the hourly panel has no row → log + drop from both
    numerator and denominator; record count in
    `n_dropped_unmatched_hours`.

- [ ] **Step 4:** Run tests, verify PASS.

- [ ] **Step 5:** Commit:
  ```bash
  git add src/surg/analysis/spike_exceedance_comparison.py tests/analysis/test_spike_exceedance_comparison.py
  git commit -m "feat(analysis): spike_exceedance_comparison module (sub-q1 item #8 Part B)"
  ```

---

## Task 18: Part B production run

- [ ] **Step 1:** Load both panels + run:
  ```bash
  .venv/bin/python -c "
  from pathlib import Path
  import pandas as pd
  from surg.analysis.spike_exceedance_comparison import run_spike_exceedance_comparison

  panel_5min = pd.read_parquet('data/interim/analysis_panel_5min_lmp_only.parquet')
  panel_hourly = pd.read_parquet('data/interim/analysis_panel.parquet')
  # Restrict hourly to the 6-month overlap window
  tmin = panel_5min['datetime_beginning_ept'].min()
  tmax = panel_5min['datetime_beginning_ept'].max()
  panel_hourly = panel_hourly[
      (panel_hourly['datetime_beginning_ept'] >= tmin.floor('h')) &
      (panel_hourly['datetime_beginning_ept'] <= tmax.ceil('h'))
  ]
  run_spike_exceedance_comparison(
      panel_5min=panel_5min,
      panel_hourly=panel_hourly,
      out_root=Path('outputs_5min/lmp_descriptive_6mo/'),
      thresholds=[50, 100, 250, 500, 1000],
  )
  print('Part B run complete')
  "
  ```
  Expected wall: < 30 min.

- [ ] **Step 2:** Verify outputs:
  ```bash
  ls outputs_5min/lmp_descriptive_6mo/spike_exceedance_comparison/
  ```
  Expected: per-pnode JSON + cross_pnode_summary.csv + plots.

---

## Task 19: Cross-resolution summary builder

**Files:**
- Create: `scripts/build_cross_resolution_summary.py`

- [ ] **Step 1:** Implement script that joins `outputs_5min/joint_30d/tail_risk_curves/`
  with `outputs_5min/hourly_30d_for_comparison/tail_risk_curves/`
  on (pnode, decile, threshold) and writes
  `outputs_5min/cross_resolution_summary.{json,csv}`.
- [ ] **Step 2:** Run it:
  ```bash
  .venv/bin/python scripts/build_cross_resolution_summary.py
  ```
- [ ] **Step 3:** Commit script:
  ```bash
  git add scripts/build_cross_resolution_summary.py
  git commit -m "feat(scripts): cross-resolution summary builder (sub-q1 item #8)"
  ```

---

## Task 20: Application entry to decisions.md

- [ ] **Step 1:** Append a 2026-05-15-late application entry to
  `docs/decisions.md` with structure:
  - **Context.** "Pre-reg at 2026-05-15 § Item #8 5-min companion
    pre-reg locked the methodology. Production run executed
    autonomously per `docs/plans/2026-05-15-5min-companion-implementation.md`."
  - **Findings — Part A (joint Z+LMP, ~30-day window, K islands):**
    summarize each module's verdict with hourly-comparison.
  - **Findings — Part B (LMP-only, 6-month, spike-exceedance):**
    summarize hidden-fraction headline by pnode.
  - **Limitations:** restate `inst_load` retention wall;
    cluster-count below 50-floor (Part A); descriptive-only (no CI)
    (Part B).
  - **Revisit when:** as in pre-reg.

- [ ] **Step 2:** Commit:
  ```bash
  git add docs/decisions.md
  git commit -m "docs(decisions): apply sub-q1 item #8 5-min companion findings"
  ```

---

## Task 21: Mark item #8 DONE in roadmap + final summary

- [ ] **Step 1:** Update
  `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`: change
  item #8 status from "pending implementation" to "DONE" with the
  commit SHA of the application entry.
- [ ] **Step 2:** Commit:
  ```bash
  git add docs/plans/2026-05-14-sub-question-1-closure-roadmap.md
  git commit -m "docs(plans): mark sub-q1 item #8 DONE"
  ```
- [ ] **Step 3:** Write the final "ready for review" summary
  message to the user. Include:
  - Branch name + commit count + last commit SHA.
  - Total wall time.
  - Headline findings (Part A: as expected, all underpowered with
    direction X; Part B: hidden-fraction = Y at $500 threshold for
    `primary`).
  - Reminder: NO FF-merge done, NO push done. User reviews +
    merges.

---

## Slash command file

Create `.claude/commands/run-5min-companion.md` with the following
content (must be ≤ 4000 characters; verify with `wc -c`):

```markdown
# /run-5min-companion

Execute Sub-Q1 Item #8 — the 5-min companion overnight run — per the
plan-driven launcher convention.

**Goal:** Run items #1-4 + #6 on a joint 30-day 5-min Z+LMP panel
(Part A) and a single new spike-exceedance-comparison module on a
6-month LMP-only panel (Part B), per the locked design.

**Estimated wall: 10-15 h. User-authorized to overflow the 8h target.
Re-read this line in the morning if surprised by where the run is.**

## Pre-flight checks (HALT if any fail)

1. Pre-reg entry committed: `grep -q "Sub-q1 item #8" docs/decisions.md` (gates: all)
2. Design exists: `test -f docs/plans/2026-05-15-5min-companion-design.md` (gates: all)
3. Plan exists: `test -f docs/plans/2026-05-15-5min-companion-implementation.md` (gates: all)
4. Main worktree clean: `git status` shows nothing to commit (gates: all)
5. NU DNS workaround active: `python -c "import socket; socket.gethostbyname('api.pjm.com')"` succeeds (gates: Part A only — Part B uses on-disk data)

If any pre-flight fails, halt with the specific failed check + the
fix instruction (DNS: see `docs/sources/pjm-api-constraints.md` § NU DNS).

## Execute

Use `superpowers:executing-plans` against
`docs/plans/2026-05-15-5min-companion-implementation.md`. Begin from
Task 1 (worktree setup); pre-launch tasks (Setup-1 through Setup-5)
are completed by the user before invocation and verified by
pre-flight check #1.

## Locked autonomy rules

- Commit per task to the feature branch in the sibling worktree.
- NO FF-merge. NO push to origin. Stops at "branch ready for user
  review."
- Run-to-completion regardless of wall time (8h target is informational).
- On any failure not handled by a specific task: halt + commit current
  state with `WIP:` prefix + write status update. Do NOT continue
  downstream tasks.
- After Task 21 completes, write a "ready for review" summary to the
  user (branch name, commit count, last SHA, total wall time, headline
  findings, reminder that NO push has happened).
```

(Verify byte count with `wc -c .claude/commands/run-5min-companion.md`
— must be ≤ 4000 bytes.)

---

## Self-review checklist (run after writing this plan)

- [x] **Spec coverage:** Every section of the design doc has a
  corresponding task or pre-launch setup item.
- [x] **No placeholders:** All code blocks contain actual code, not
  TBD/TODO. Every CLI invocation is concrete.
- [x] **Type consistency:** Function names match across tasks
  (`bootstrap_dispatch`, `island_cluster_bootstrap`,
  `compute_per_pnode_metrics` consistent throughout).
- [x] **Carry-forwards from advisor:** divide-by-zero handled in
  Task 17 spec; threshold percentiles called out in Task 17
  Step 3; like-for-like comparator addressed in Task 15; refresh
  pull addressed in Task 2 Step 4; refactor sequencing enforced by
  one-module-per-task structure (Tasks 9-13).
- [x] **Failure paths:** Each substantive task has an explicit halt
  protocol (commit `WIP:` + report; do not continue).
- [x] **Pre-launch vs slash-command-driven separation:** Setup-1
  through Setup-5 happen on `main` before invocation; Tasks 1-21
  happen autonomously in the worktree.
