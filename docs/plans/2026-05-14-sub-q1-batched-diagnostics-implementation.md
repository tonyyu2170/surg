# Sub-Question 1 Batched Diagnostics — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close sub-q1 closure roadmap items #2 (LMP-components decomposition), #3 (τ=0.99 secular sign-flip diagnostic), and #4 (Ashburn TX1 99th-pct anomaly diagnostic) as a single batched plan. Headline test for #2 is pre-registered; #3 and #4 are descriptive characterizations.

**Architecture:** Preprocessing schema bump (SCHEMA_VERSION 1 → 2) adds `system_energy_price_rt` and `marginal_loss_price_rt` columns per labeled pnode + Loudoun cluster means. Three new analysis modules — `gpd_components.py`, `year_fe_diagnostic.py`, `ashburn_diagnostic.py` — each with tests and `run_all` wiring. Production run produces JSON outputs + one PNG figure; three application entries in `docs/decisions.md` apply Rule 2 (for #2) or summarize evidence (for #3, #4); roadmap updated.

**Tech Stack:** Python 3.11+, pandas, numpy, scipy, statsmodels, matplotlib, pyarrow/parquet. Tests via pytest.

**Spec reference:** `docs/plans/2026-05-14-sub-q1-batched-diagnostics-design.md` (commit `a789e75`).

**Working tree:** Plan to be executed in a sibling worktree (`feature/sub-q1-batched-diagnostics`) created via `superpowers:using-git-worktrees`. The executor should create the worktree before Task 1.

---

## Task 1: Extend `pivot_lmp_long_to_pnode_columns` and `add_loudoun_cluster_columns` for 4 components

**Files:**
- Modify: `src/surg/preprocessing/features.py`
- Test: `tests/preprocessing/test_features.py`

- [ ] **Step 1: Write failing tests for 4-component pivot**

Append to `tests/preprocessing/test_features.py`:

```python
def test_pivot_lmp_includes_system_energy_and_marginal_loss():
    long_df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(["2024-01-01 00:00", "2024-01-01 00:00"]),
        "pnode_id": [100, 200],
        "pnode_name": ["A", "B"],
        "congestion_price_rt": [1.0, 2.0],
        "total_lmp_rt": [10.0, 20.0],
        "system_energy_price_rt": [8.0, 17.0],
        "marginal_loss_price_rt": [1.0, 1.0],
    })
    wide = pivot_lmp_long_to_pnode_columns(long_df)
    assert "congestion_price_rt_100" in wide.columns
    assert "total_lmp_rt_100" in wide.columns
    assert "system_energy_price_rt_100" in wide.columns
    assert "marginal_loss_price_rt_100" in wide.columns
    assert float(wide.loc[0, "system_energy_price_rt_200"]) == 17.0
    assert float(wide.loc[0, "marginal_loss_price_rt_200"]) == 1.0


def test_loudoun_cluster_columns_include_system_energy_and_marginal_loss():
    wide_df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(["2024-01-01 00:00"]),
        "congestion_price_rt_1": [1.0],
        "congestion_price_rt_2": [3.0],
        "total_lmp_rt_1": [10.0],
        "total_lmp_rt_2": [12.0],
        "system_energy_price_rt_1": [8.0],
        "system_energy_price_rt_2": [8.0],
        "marginal_loss_price_rt_1": [1.0],
        "marginal_loss_price_rt_2": [1.0],
    })
    out = add_loudoun_cluster_columns(wide_df, cluster_pnode_ids=(1, 2))
    assert out["system_energy_price_rt_cluster_mean"].iloc[0] == 8.0
    assert out["marginal_loss_price_rt_cluster_mean"].iloc[0] == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/preprocessing/test_features.py::test_pivot_lmp_includes_system_energy_and_marginal_loss tests/preprocessing/test_features.py::test_loudoun_cluster_columns_include_system_energy_and_marginal_loss -v`
Expected: both FAIL (KeyError on new columns or AssertionError).

- [ ] **Step 3: Extend `pivot_lmp_long_to_pnode_columns`**

Edit `src/surg/preprocessing/features.py`, change the pivot's `values` list:

```python
pivoted = long_df.pivot_table(
    index="datetime_beginning_ept",
    columns="pnode_id",
    values=[
        "congestion_price_rt",
        "total_lmp_rt",
        "system_energy_price_rt",
        "marginal_loss_price_rt",
    ],
)
```

- [ ] **Step 4: Extend `add_loudoun_cluster_columns`**

Edit `add_loudoun_cluster_columns` to compute cluster means for the two new components. After the existing congestion/total_lmp lines:

```python
sys_cols = [f"system_energy_price_rt_{pid}" for pid in cluster_pnode_ids
            if f"system_energy_price_rt_{pid}" in wide_df.columns]
loss_cols = [f"marginal_loss_price_rt_{pid}" for pid in cluster_pnode_ids
             if f"marginal_loss_price_rt_{pid}" in wide_df.columns]
out["system_energy_price_rt_cluster_mean"] = out[sys_cols].mean(axis=1)
out["marginal_loss_price_rt_cluster_mean"] = out[loss_cols].mean(axis=1)
```

- [ ] **Step 5: Run all preprocessing tests**

Run: `pytest tests/preprocessing/ -v`
Expected: all pass (new tests pass; pre-existing tests still pass).

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/features.py tests/preprocessing/test_features.py
git commit -m "feat(preprocessing): pivot + cluster aggregates for system_energy + marginal_loss"
```

---

## Task 2: Extend `build.py` rename map + `schema.py` version bump + EXPECTED_COLUMNS

**Files:**
- Modify: `src/surg/preprocessing/build.py`
- Modify: `src/surg/preprocessing/schema.py`
- Test: `tests/preprocessing/test_build.py`, `tests/preprocessing/test_schema.py`

- [ ] **Step 1: Write failing test for build.py renames + schema**

Append to `tests/preprocessing/test_build.py`:

```python
def test_build_renames_system_energy_and_marginal_loss_for_labeled_pnodes(tmp_path):
    # Use the existing build_panel fixture pattern. Confirm that after build,
    # the resulting panel has columns:
    #   system_energy_price_rt_{ashburn_tx1, ashburn_tx2, ox, bristers, dom_zonal}
    #   marginal_loss_price_rt_{ashburn_tx1, ashburn_tx2, ox, bristers, dom_zonal}
    # plus the two cluster_mean columns added by features.py.
    panel = _build_minimal_panel(tmp_path)  # reuse existing helper or inline a 2-row fixture
    expected_labeled = ["ashburn_tx1", "ashburn_tx2", "ox", "bristers", "dom_zonal"]
    for lab in expected_labeled:
        assert f"system_energy_price_rt_{lab}" in panel.columns
        assert f"marginal_loss_price_rt_{lab}" in panel.columns
    assert "system_energy_price_rt_cluster_mean" in panel.columns
    assert "marginal_loss_price_rt_cluster_mean" in panel.columns
```

(If `_build_minimal_panel` doesn't exist, copy the fixture inline from another test in `test_build.py`.)

Append to `tests/preprocessing/test_schema.py`:

```python
def test_schema_version_bumped_to_2():
    from surg.preprocessing.schema import SCHEMA_VERSION
    assert SCHEMA_VERSION == 2


def test_expected_columns_include_system_energy_and_marginal_loss():
    from surg.preprocessing.schema import EXPECTED_COLUMNS
    expected_new = {
        "system_energy_price_rt_cluster_mean",
        "marginal_loss_price_rt_cluster_mean",
        "system_energy_price_rt_ashburn_tx1",
        "system_energy_price_rt_ashburn_tx2",
        "system_energy_price_rt_ox",
        "system_energy_price_rt_bristers",
        "system_energy_price_rt_dom_zonal",
        "marginal_loss_price_rt_ashburn_tx1",
        "marginal_loss_price_rt_ashburn_tx2",
        "marginal_loss_price_rt_ox",
        "marginal_loss_price_rt_bristers",
        "marginal_loss_price_rt_dom_zonal",
    }
    assert expected_new.issubset(set(EXPECTED_COLUMNS))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/preprocessing/test_build.py::test_build_renames_system_energy_and_marginal_loss_for_labeled_pnodes tests/preprocessing/test_schema.py::test_schema_version_bumped_to_2 tests/preprocessing/test_schema.py::test_expected_columns_include_system_energy_and_marginal_loss -v`
Expected: all FAIL.

- [ ] **Step 3: Extend `build.py` rename map**

In `src/surg/preprocessing/build.py`, locate the `rename` dict (around line 63-69) and add entries for all 5 labeled pnodes × 2 new components:

```python
rename = {
    # ... existing entries for congestion + total_lmp ...
    f"system_energy_price_rt_{ASHBURN_TX1}": "system_energy_price_rt_ashburn_tx1",
    f"system_energy_price_rt_{ASHBURN_TX2}": "system_energy_price_rt_ashburn_tx2",
    f"system_energy_price_rt_{CONTROL_OX}":  "system_energy_price_rt_ox",
    f"system_energy_price_rt_{CONTROL_BRISTERS}": "system_energy_price_rt_bristers",
    f"system_energy_price_rt_{DOM_ZONAL}":   "system_energy_price_rt_dom_zonal",
    f"marginal_loss_price_rt_{ASHBURN_TX1}": "marginal_loss_price_rt_ashburn_tx1",
    f"marginal_loss_price_rt_{ASHBURN_TX2}": "marginal_loss_price_rt_ashburn_tx2",
    f"marginal_loss_price_rt_{CONTROL_OX}":  "marginal_loss_price_rt_ox",
    f"marginal_loss_price_rt_{CONTROL_BRISTERS}": "marginal_loss_price_rt_bristers",
    f"marginal_loss_price_rt_{DOM_ZONAL}":   "marginal_loss_price_rt_dom_zonal",
}
```

Also check `build.py` for any `total_lmp_rt_<labeled>` rename entries that may need a parallel `total_lmp_rt_<labeled>` for the Ashburn pnodes (used by item #4's scatter). If they're not already present and item #4's scatter requires them, add the rename in this task. Read lines 60-80 of `build.py` and confirm before editing.

- [ ] **Step 4: Bump `SCHEMA_VERSION` and extend `EXPECTED_COLUMNS`**

In `src/surg/preprocessing/schema.py`:

```python
SCHEMA_VERSION = 2  # was 1; bumped for sub-q1 closure item #2 components
```

Extend `EXPECTED_COLUMNS` tuple — under the existing `"# LMP — Loudoun cluster pooled"` section add the two new cluster means; under the existing labeled-pnode sections add the 10 new per-pnode component columns. Group them clearly with section comments matching the existing pattern.

- [ ] **Step 5: Run preprocessing tests**

Run: `pytest tests/preprocessing/ -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/surg/preprocessing/build.py src/surg/preprocessing/schema.py tests/preprocessing/test_build.py tests/preprocessing/test_schema.py
git commit -m "feat(preprocessing): schema v2 — add system_energy + marginal_loss columns"
```

---

## Task 3: Rebuild analysis panel + smoke verify

**Files:**
- Generates: `data/interim/analysis_panel.parquet` (regenerated artifact, gitignored)

- [ ] **Step 1: Rebuild the panel**

Run: `surg-prep`
Expected: completes without error, prints summary line indicating panel written to `data/interim/analysis_panel.parquet`.

- [ ] **Step 2: Verify schema version and new columns**

Run:
```bash
.venv/bin/python -c "
import pyarrow.parquet as pq
pf = pq.ParquetFile('data/interim/analysis_panel.parquet')
meta = pf.schema_arrow.metadata or {}
print('schema_version:', (meta.get(b'schema_version') or b'<missing>').decode())
new_cols = [c for c in pf.schema_arrow.names if 'system_energy' in c or 'marginal_loss' in c]
print('new columns:', new_cols)
"
```
Expected: prints `schema_version: 2` and a list of at least 12 new columns (10 per-pnode + 2 cluster means).

- [ ] **Step 3: Verify `panel.load_panel` round-trips under new schema**

Run:
```bash
.venv/bin/python -c "
from pathlib import Path
from surg.analysis.panel import load_panel
df = load_panel(Path('data/interim/analysis_panel.parquet'))
print('rows:', len(df))
print('system_energy cluster mean nan_frac:', df['system_energy_price_rt_cluster_mean'].isna().mean())
print('marginal_loss cluster mean nan_frac:', df['marginal_loss_price_rt_cluster_mean'].isna().mean())
"
```
Expected: 31536 rows; NaN fractions less than ~0.5 (most rows have valid component data).

- [ ] **Step 4: No commit (rebuild artifact is gitignored)**

The panel is regenerated locally per data pipeline; no git changes from this task. Confirm with `git status` that working tree is clean.

---

## Task 4: Write pre-registration entry for item #2 in `docs/decisions.md`

**Files:**
- Modify: `docs/decisions.md`

- [ ] **Step 1: Append pre-reg section to `docs/decisions.md`**

Append a new section using HEREDOC (do not edit via Edit tool — append at end of file). Section heading and body must contain Rules 1-5 verbatim from the design spec (Phase 2). Use today's date stamp.

Section heading:
```
## 2026-05-XX — Pre-registration: LMP-components decomposition (sub-q1 closure item #2)
```
(replace `XX` with today's day at commit time).

Body should contain all five Rules from `docs/plans/2026-05-14-sub-q1-batched-diagnostics-design.md` § Phase 2 verbatim (Rule 1 singular headline, Rule 2 decision table corrected for ORDC direction, Rule 3 LRT N/A, Rule 4 low-power skip at n_exc/half<50, Rule 5 MT posture).

- [ ] **Step 2: Verify Rule 2's decision table directions match the design spec**

Read back the table content: `shape_diff > 0, CI excludes 0` corresponds to "Cancellation hypothesis supported" — the ORDC-predicted direction. Re-confirm by searching the design spec:

Run: `grep -A 3 "shape_diff > 0" docs/plans/2026-05-14-sub-q1-batched-diagnostics-design.md`
Expected: confirms "Cancellation hypothesis supported" follows `shape_diff > 0`.

- [ ] **Step 3: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): pre-register LMP-components decomposition (sub-q1 item #2)"
```

---

## Task 5: Create `gpd_components.py` skeleton with `ComponentsHeadlineResult` and Rule 2 dispatcher

**Files:**
- Create: `src/surg/analysis/gpd_components.py`
- Test: `tests/analysis/test_gpd_components.py`

- [ ] **Step 1: Write failing tests for `ComponentsHeadlineResult` and `outcome_from_shape_diff_ci`**

Create `tests/analysis/test_gpd_components.py`:

```python
"""Tests for gpd_components.py — sub-q1 closure item #2.

Pre-reg: docs/decisions.md § 2026-05-XX — Pre-registration: LMP-components
decomposition (sub-q1 closure item #2).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from surg.analysis.gpd_components import (
    ComponentsHeadlineResult,
    outcome_from_shape_diff_ci,
)


def test_components_headline_result_fields():
    r = ComponentsHeadlineResult(
        component="system_energy",
        pnode_label="primary_cluster",
        threshold_quantile=0.95,
        n_exc=1577,
        shape_diff=-0.18,
        shape_diff_ci_95=(-0.37, -0.04),
        rule_2_outcome="ordc_rejected_broader",
        paper_claim="...",
    )
    assert r.component == "system_energy"
    assert r.rule_2_outcome == "ordc_rejected_broader"


def test_outcome_from_shape_diff_ci_cancellation_supported():
    # shape_diff > 0, CI excludes 0 (positive direction)
    assert outcome_from_shape_diff_ci(0.20, (0.05, 0.40), n_per_half=789) == "cancellation_supported"


def test_outcome_from_shape_diff_ci_ordc_rejected_broader():
    # shape_diff < 0, CI excludes 0 (negative direction)
    assert outcome_from_shape_diff_ci(-0.18, (-0.37, -0.04), n_per_half=789) == "ordc_rejected_broader"


def test_outcome_from_shape_diff_ci_underpowered_neg():
    # shape_diff < 0, CI spans 0
    assert outcome_from_shape_diff_ci(-0.05, (-0.20, 0.05), n_per_half=789) == "underpowered_neg_direction"


def test_outcome_from_shape_diff_ci_underpowered_pos():
    # shape_diff >= 0, CI spans 0
    assert outcome_from_shape_diff_ci(0.05, (-0.05, 0.20), n_per_half=789) == "underpowered_pos_direction"


def test_outcome_from_shape_diff_ci_insufficient_sample():
    # n_per_half below threshold of 50
    assert outcome_from_shape_diff_ci(0.0, (-1.0, 1.0), n_per_half=40) == "insufficient_sample"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/analysis/test_gpd_components.py -v`
Expected: all FAIL (ImportError on `gpd_components` module not existing).

- [ ] **Step 3: Create `gpd_components.py` skeleton**

Create `src/surg/analysis/gpd_components.py`:

```python
"""LMP-components conditional-Z decomposition (sub-q1 closure item #2).

Median-split conditional-Z test applied to three LMP components separately
(system_energy, congestion, marginal_loss). Singular headline test
pre-registered in docs/decisions.md § 2026-05-XX. Other component / pnode /
threshold combinations are descriptive supplementary.

Reuses gpd.gpd_quantile_split_on_z with split_quantiles=(0.5,) for the
binary median split.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.gpd import gpd_quantile_split_on_z


# Rule 4 in the pre-reg: any test with n_exc/half < 50 reports insufficient.
N_PER_HALF_FLOOR = 50


@dataclass(frozen=True, slots=True)
class ComponentsHeadlineResult:
    """Single median-split conditional-Z result on one LMP component.

    `rule_2_outcome` is one of:
      - "cancellation_supported"      (shape_diff > 0, CI excludes 0)
      - "ordc_rejected_broader"       (shape_diff < 0, CI excludes 0)
      - "underpowered_neg_direction"  (CI spans 0, shape_diff < 0)
      - "underpowered_pos_direction"  (CI spans 0, shape_diff >= 0)
      - "insufficient_sample"         (n_per_half < N_PER_HALF_FLOOR)
    """
    component: str
    pnode_label: str
    threshold_quantile: float
    n_exc: int
    shape_diff: float
    shape_diff_ci_95: tuple[float, float]
    rule_2_outcome: str
    paper_claim: str


def outcome_from_shape_diff_ci(
    shape_diff: float,
    ci_95: tuple[float, float],
    *,
    n_per_half: int,
) -> str:
    """Apply the pre-reg's Rule 2 decision table to a (shape_diff, CI, n) triple."""
    if n_per_half < N_PER_HALF_FLOOR:
        return "insufficient_sample"
    lo, hi = ci_95
    ci_excludes_zero = (lo > 0) or (hi < 0)
    if ci_excludes_zero:
        return "cancellation_supported" if shape_diff > 0 else "ordc_rejected_broader"
    return "underpowered_pos_direction" if shape_diff >= 0 else "underpowered_neg_direction"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_gpd_components.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/gpd_components.py tests/analysis/test_gpd_components.py
git commit -m "feat(analysis): gpd_components skeleton — ComponentsHeadlineResult + Rule 2 dispatcher"
```

---

## Task 6: Add `fit_single_component_median_split` to `gpd_components.py`

**Files:**
- Modify: `src/surg/analysis/gpd_components.py`
- Modify: `tests/analysis/test_gpd_components.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_gpd_components.py`:

```python
def test_fit_single_component_median_split_returns_result():
    from surg.analysis.gpd_components import fit_single_component_median_split

    rng = np.random.default_rng(0)
    n = 8000
    Z = rng.uniform(0, 10, size=n)
    Y = rng.exponential(scale=1.0 + 0.2 * Z, size=n)
    panel = pd.DataFrame({"Y": Y, "Z": Z})

    result = fit_single_component_median_split(
        panel=panel,
        response_col="Y",
        z_col="Z",
        component="system_energy",
        pnode_label="primary_cluster",
        threshold_quantile=0.95,
        n_boot=50,
        seed=0,
    )
    assert isinstance(result, ComponentsHeadlineResult)
    assert result.component == "system_energy"
    assert result.pnode_label == "primary_cluster"
    assert result.threshold_quantile == 0.95
    assert result.n_exc > 0
    assert result.rule_2_outcome in {
        "cancellation_supported",
        "ordc_rejected_broader",
        "underpowered_neg_direction",
        "underpowered_pos_direction",
        "insufficient_sample",
    }


def test_fit_single_component_median_split_low_power_emits_insufficient():
    # 80 obs → ~4 exceedances at 95th-pct → n_per_half < 50.
    # The wrapper should catch this BEFORE calling gpd_quantile_split_on_z
    # (which would otherwise raise on <20 exceedances).
    from surg.analysis.gpd_components import fit_single_component_median_split

    panel = pd.DataFrame({"Y": np.arange(80, dtype=float), "Z": np.arange(80, dtype=float)})
    result = fit_single_component_median_split(
        panel=panel,
        response_col="Y",
        z_col="Z",
        component="system_energy",
        pnode_label="primary_cluster",
        threshold_quantile=0.95,
        n_boot=50,
        seed=0,
    )
    assert result.rule_2_outcome == "insufficient_sample"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/analysis/test_gpd_components.py::test_fit_single_component_median_split_returns_result tests/analysis/test_gpd_components.py::test_fit_single_component_median_split_low_power_emits_insufficient -v`
Expected: both FAIL (ImportError on `fit_single_component_median_split`).

- [ ] **Step 3: Implement `fit_single_component_median_split`**

Append to `src/surg/analysis/gpd_components.py`:

```python
PAPER_CLAIMS = {
    "cancellation_supported": (
        "Cancellation hypothesis supported: {component} carries the ORDC-predicted "
        "direction (heavier tail at HIGH Z); congestion's opposite-direction effect "
        "cancels it in total_lmp. shape_diff={shape_diff:.3f}, CI [{lo:.3f},{hi:.3f}]."
    ),
    "ordc_rejected_broader": (
        "ORDC-predicted direction rejected for {component} too. shape_diff={shape_diff:.3f}, "
        "CI [{lo:.3f},{hi:.3f}] excludes 0 in the negative direction; heavier-tail-at-LOW-Z "
        "effect is broader than congestion. Mechanism is NOT ORDC-specific."
    ),
    "underpowered_neg_direction": (
        "Underpowered on this scope (n_per_half={n_per_half}): {component} direction "
        "consistent with congestion finding (heavier tail at LOW Z), shape_diff={shape_diff:.3f}, "
        "CI [{lo:.3f},{hi:.3f}] spans 0. Not consistent with ORDC's predicted direction."
    ),
    "underpowered_pos_direction": (
        "Underpowered on this scope (n_per_half={n_per_half}): {component} direction "
        "consistent with ORDC's predicted direction (heavier tail at HIGH Z), "
        "shape_diff={shape_diff:.3f}, CI [{lo:.3f},{hi:.3f}] spans 0. Cannot confirm "
        "at α=0.05."
    ),
    "insufficient_sample": (
        "Insufficient sample: n_per_half={n_per_half} below pre-reg floor of "
        f"{N_PER_HALF_FLOOR}. No verdict reported."
    ),
}


def _format_paper_claim(outcome: str, *, component: str, shape_diff: float,
                       ci_95: tuple[float, float], n_per_half: int) -> str:
    template = PAPER_CLAIMS[outcome]
    return template.format(
        component=component, shape_diff=shape_diff,
        lo=ci_95[0], hi=ci_95[1], n_per_half=n_per_half,
    )


def fit_single_component_median_split(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    component: str,
    pnode_label: str,
    threshold_quantile: float = 0.95,
    n_boot: int = 200,
    seed: int = 0,
    filter_col: str | None = None,
) -> ComponentsHeadlineResult:
    """Median-split conditional-Z test on a single (component, pnode, threshold)."""
    sub = panel.dropna(subset=[response_col, z_col]).copy()
    if filter_col is not None:
        sub = sub[sub[filter_col].fillna(False).astype(bool)].copy()

    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()

    if len(Y) == 0:
        return _insufficient(component, pnode_label, threshold_quantile, n_exc=0, n_per_half=0)

    threshold = float(np.quantile(Y, threshold_quantile))
    n_exc = int((Y > threshold).sum())
    n_per_half = n_exc // 2

    if n_per_half < N_PER_HALF_FLOOR:
        return _insufficient(component, pnode_label, threshold_quantile, n_exc=n_exc,
                             n_per_half=n_per_half)

    result = gpd_quantile_split_on_z(
        Y, Z,
        threshold_quantile=threshold_quantile,
        split_quantiles=(0.5,),
        n_boot=n_boot,
        seed=seed,
    )
    shape_diff = float(result.extreme_contrast)
    ci_95 = (
        float(result.extreme_contrast_bootstrap_ci_95[0]),
        float(result.extreme_contrast_bootstrap_ci_95[1]),
    )
    outcome = outcome_from_shape_diff_ci(shape_diff, ci_95, n_per_half=n_per_half)
    claim = _format_paper_claim(outcome, component=component, shape_diff=shape_diff,
                                ci_95=ci_95, n_per_half=n_per_half)
    return ComponentsHeadlineResult(
        component=component,
        pnode_label=pnode_label,
        threshold_quantile=threshold_quantile,
        n_exc=n_exc,
        shape_diff=shape_diff,
        shape_diff_ci_95=ci_95,
        rule_2_outcome=outcome,
        paper_claim=claim,
    )


def _insufficient(
    component: str, pnode_label: str, threshold_quantile: float,
    *, n_exc: int, n_per_half: int,
) -> ComponentsHeadlineResult:
    outcome = "insufficient_sample"
    return ComponentsHeadlineResult(
        component=component,
        pnode_label=pnode_label,
        threshold_quantile=threshold_quantile,
        n_exc=n_exc,
        shape_diff=float("nan"),
        shape_diff_ci_95=(float("nan"), float("nan")),
        rule_2_outcome=outcome,
        paper_claim=_format_paper_claim(outcome, component=component, shape_diff=float("nan"),
                                        ci_95=(float("nan"), float("nan")), n_per_half=n_per_half),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_gpd_components.py -v`
Expected: 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/gpd_components.py tests/analysis/test_gpd_components.py
git commit -m "feat(analysis): gpd_components single-component median-split wrapper"
```

---

## Task 7: Add `run_gpd_components` orchestrator + 4 output JSON files

**Files:**
- Modify: `src/surg/analysis/gpd_components.py`
- Modify: `tests/analysis/test_gpd_components.py`

- [ ] **Step 1: Write failing test for orchestrator**

Append to `tests/analysis/test_gpd_components.py`:

```python
def _make_panel_for_orchestrator(n_rows: int = 8000) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    Z = rng.uniform(0, 10, size=n_rows)
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n_rows, freq="h"),
        "dom_load_gradient_abs_mw_per_min": Z,
        "system_energy_price_rt_cluster_mean": rng.exponential(1.0 + 0.1 * Z),
        "congestion_price_rt_cluster_mean": rng.exponential(1.0 + 0.2 * Z),
        "marginal_loss_price_rt_cluster_mean": rng.exponential(0.5 + 0.05 * Z),
        "passes_proposal_filter": rng.random(n_rows) > 0.7,  # ~30% pass
    })
    return panel


def test_run_gpd_components_writes_four_outputs(tmp_path: Path):
    from surg.analysis.gpd_components import run_gpd_components

    panel = _make_panel_for_orchestrator()
    out_dir = tmp_path / "gpd_components"

    run_gpd_components(
        panel=panel,
        out_dir=out_dir,
        n_boot=30,
        seed=0,
    )

    assert (out_dir / "headline.json").exists()
    assert (out_dir / "primary_cluster_supplementary.json").exists()
    assert (out_dir / "cross_pnode.json").exists()
    assert (out_dir / "threshold_sweep.json").exists()

    headline = json.loads((out_dir / "headline.json").read_text())
    assert headline["component"] == "system_energy"
    assert headline["pnode_label"] == "primary_cluster"
    assert headline["threshold_quantile"] == 0.95
    assert "rule_2_outcome" in headline
    assert "paper_claim" in headline
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_gpd_components.py::test_run_gpd_components_writes_four_outputs -v`
Expected: FAIL (ImportError on `run_gpd_components`).

- [ ] **Step 3: Implement `run_gpd_components`**

Append to `src/surg/analysis/gpd_components.py`:

```python
# Per-pnode response-column templates per component. Labeled pnodes only.
LABELED_PNODES = ("ashburn_tx1", "ashburn_tx2", "ox", "bristers", "dom_zonal")
CLUSTER_RESPONSE_COLS = {
    "system_energy": "system_energy_price_rt_cluster_mean",
    "congestion":    "congestion_price_rt_cluster_mean",
    "marginal_loss": "marginal_loss_price_rt_cluster_mean",
}
CROSS_PNODE_RESPONSE_COLS = {
    "system_energy": {p: f"system_energy_price_rt_{p}" for p in LABELED_PNODES},
    "congestion":    {p: f"congestion_price_rt_{p}"    for p in LABELED_PNODES},
    "marginal_loss": {p: f"marginal_loss_price_rt_{p}" for p in LABELED_PNODES},
}


def _result_to_dict(r: ComponentsHeadlineResult) -> dict:
    return {
        "component": r.component,
        "pnode_label": r.pnode_label,
        "threshold_quantile": r.threshold_quantile,
        "n_exc": r.n_exc,
        "shape_diff": _nan_to_none(r.shape_diff),
        "shape_diff_ci_95": [_nan_to_none(r.shape_diff_ci_95[0]),
                             _nan_to_none(r.shape_diff_ci_95[1])],
        "rule_2_outcome": r.rule_2_outcome,
        "paper_claim": r.paper_claim,
    }


def _nan_to_none(x: float) -> float | None:
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def run_gpd_components(
    panel: pd.DataFrame,
    out_dir: Path,
    *,
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    filter_col: str = "passes_proposal_filter",
    headline_threshold_q: float = 0.95,
    threshold_sweep_qs: tuple[float, ...] = (0.90, 0.95, 0.99),
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """End-to-end orchestrator for sub-q1 closure item #2.

    Writes four JSON files under `out_dir`:
      - headline.json: system_energy @ headline_threshold_q on primary cluster.
      - primary_cluster_supplementary.json: congestion + marginal_loss on primary cluster.
      - cross_pnode.json: 3 components × 5 labeled pnodes × headline_threshold_q.
      - threshold_sweep.json: 3 components × primary cluster × threshold_sweep_qs.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Headline: system_energy @ p95 on primary cluster.
    headline = fit_single_component_median_split(
        panel=panel,
        response_col=CLUSTER_RESPONSE_COLS["system_energy"],
        z_col=z_col,
        component="system_energy",
        pnode_label="primary_cluster",
        threshold_quantile=headline_threshold_q,
        n_boot=n_boot,
        seed=seed,
        filter_col=filter_col,
    )
    headline_payload = _result_to_dict(headline)
    headline_payload["rule_1_singular_headline"] = (
        f"system_energy_price_rt_cluster_mean median-split @ "
        f"p{int(headline_threshold_q*100)} LMP, Loudoun cluster, filtered subset"
    )
    headline_payload["pre_reg_reference"] = (
        "docs/decisions.md § 2026-05-XX — Pre-registration: LMP-components decomposition"
    )
    (out_dir / "headline.json").write_text(json.dumps(headline_payload, indent=2))

    # Primary cluster supplementary: congestion + marginal_loss @ p95.
    primary_supp = []
    for comp in ("congestion", "marginal_loss"):
        r = fit_single_component_median_split(
            panel=panel,
            response_col=CLUSTER_RESPONSE_COLS[comp],
            z_col=z_col,
            component=comp,
            pnode_label="primary_cluster",
            threshold_quantile=headline_threshold_q,
            n_boot=n_boot,
            seed=seed + 1,
            filter_col=filter_col,
        )
        primary_supp.append(_result_to_dict(r))
    (out_dir / "primary_cluster_supplementary.json").write_text(
        json.dumps({"results": primary_supp, "scope": "descriptive (no MT correction)"}, indent=2)
    )

    # Cross-pnode: 3 components × 5 labeled pnodes @ p95.
    cross_pnode_results = []
    seed_idx = 2
    for comp in ("system_energy", "congestion", "marginal_loss"):
        for label, col in CROSS_PNODE_RESPONSE_COLS[comp].items():
            if col not in panel.columns or panel[col].dropna().empty:
                continue
            r = fit_single_component_median_split(
                panel=panel,
                response_col=col,
                z_col=z_col,
                component=comp,
                pnode_label=label,
                threshold_quantile=headline_threshold_q,
                n_boot=n_boot,
                seed=seed + seed_idx,
                filter_col=filter_col,
            )
            cross_pnode_results.append(_result_to_dict(r))
            seed_idx += 1
    (out_dir / "cross_pnode.json").write_text(
        json.dumps({"results": cross_pnode_results,
                    "scope": "descriptive (no MT correction)"}, indent=2)
    )

    # Threshold sweep: 3 components × primary cluster × multiple thresholds.
    sweep_results = []
    for comp in ("system_energy", "congestion", "marginal_loss"):
        for q in threshold_sweep_qs:
            r = fit_single_component_median_split(
                panel=panel,
                response_col=CLUSTER_RESPONSE_COLS[comp],
                z_col=z_col,
                component=comp,
                pnode_label="primary_cluster",
                threshold_quantile=q,
                n_boot=n_boot,
                seed=seed + seed_idx,
                filter_col=filter_col,
            )
            sweep_results.append(_result_to_dict(r))
            seed_idx += 1
    (out_dir / "threshold_sweep.json").write_text(
        json.dumps({"results": sweep_results,
                    "scope": "descriptive (no MT correction)"}, indent=2)
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_gpd_components.py -v`
Expected: 9 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/gpd_components.py tests/analysis/test_gpd_components.py
git commit -m "feat(analysis): gpd_components orchestrator + 4 output JSON files"
```

---

## Task 8: Wire `run_gpd_components` into `run_all`

**Files:**
- Modify: `src/surg/analysis/run.py`

- [ ] **Step 1: Add `--components-n-boot` and `--skip-gpd-components` CLI flags**

In `src/surg/analysis/run.py:_build_arg_parser`, after `--continuous-n-boot`:

```python
p.add_argument("--components-n-boot", type=int, default=200,
               help="Bootstrap reps for sub-q1 item #2 LMP-components decomposition.")
p.add_argument("--skip-gpd-components", action="store_true",
               help="Skip sub-q1 item #2 (gpd_components) orchestrator.")
```

- [ ] **Step 2: Add `components_n_boot` and `skip_gpd_components` parameters to `run_all`**

Update the `run_all` signature:

```python
def run_all(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    out_root: Path,
    *,
    n_boot: int = 1000,
    n_subsample_reps: int = 200,
    qr_full_n_boot: int = 200,
    gpd_n_boot: int = 200,
    continuous_n_boot: int = 200,
    components_n_boot: int = 200,
    skip_gpd_components: bool = False,
) -> None:
```

- [ ] **Step 3: Call `run_gpd_components` after `_write_spec_b_headline`**

In the body of `run_all`, after the `_write_spec_b_headline(out_root / "gpd_continuous")` call, add:

```python
# Sub-q1 closure item #2: LMP-components decomposition.
# Pre-reg: docs/decisions.md § 2026-05-XX — Pre-registration: LMP-components decomposition.
if not skip_gpd_components:
    from surg.analysis.gpd_components import run_gpd_components
    run_gpd_components(
        panel=panel,
        out_dir=out_root / "gpd_components",
        n_boot=components_n_boot,
    )
```

- [ ] **Step 4: Pass new args from `main` to `run_all`**

Update `main(...)`:

```python
run_all(
    panel=panel, events=events,
    out_root=Path(args.out_root),
    n_boot=args.n_boot,
    n_subsample_reps=args.n_subsample_reps,
    qr_full_n_boot=args.qr_full_n_boot,
    gpd_n_boot=args.gpd_n_boot,
    continuous_n_boot=args.continuous_n_boot,
    components_n_boot=args.components_n_boot,
    skip_gpd_components=args.skip_gpd_components,
)
```

- [ ] **Step 5: Run existing analysis tests to confirm no regression**

Run: `pytest tests/analysis/ -v`
Expected: all pass; no new test failures.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/run.py
git commit -m "feat(analysis): wire run_gpd_components into run_all + CLI flags"
```

---

## Task 9: Create `year_fe_diagnostic.py` skeleton + `compute_raw_per_year_stats`

**Files:**
- Create: `src/surg/analysis/year_fe_diagnostic.py`
- Test: `tests/analysis/test_year_fe_diagnostic.py`

- [ ] **Step 1: Write failing test for `compute_raw_per_year_stats`**

Create `tests/analysis/test_year_fe_diagnostic.py`:

```python
"""Tests for year_fe_diagnostic.py — sub-q1 closure item #3 (descriptive)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _two_year_panel(per_year: int = 1000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    timestamps = (
        list(pd.date_range("2023-01-01", periods=per_year, freq="h")) +
        list(pd.date_range("2024-01-01", periods=per_year, freq="h"))
    )
    return pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(timestamps),
        "Y": np.concatenate([
            rng.exponential(1.0, size=per_year),
            rng.exponential(2.0, size=per_year),   # 2024 is hotter
        ]),
        "Z": rng.uniform(0, 10, size=2 * per_year),
    })


def test_compute_raw_per_year_stats_returns_one_row_per_year():
    from surg.analysis.year_fe_diagnostic import compute_raw_per_year_stats

    panel = _two_year_panel()
    stats = compute_raw_per_year_stats(
        panel, response_col="Y", year_col="datetime_beginning_ept",
        pct_list=(0.90, 0.95, 0.99),
    )
    assert isinstance(stats, list)
    assert len(stats) == 2
    years = {s["year"] for s in stats}
    assert years == {2023, 2024}
    for s in stats:
        assert "p90" in s
        assert "p95" in s
        assert "p99" in s
        assert "n_obs" in s


def test_compute_raw_per_year_stats_p99_higher_in_hotter_year():
    from surg.analysis.year_fe_diagnostic import compute_raw_per_year_stats

    panel = _two_year_panel(per_year=2000, seed=42)
    stats = compute_raw_per_year_stats(
        panel, response_col="Y", year_col="datetime_beginning_ept",
        pct_list=(0.99,),
    )
    by_year = {s["year"]: s for s in stats}
    assert by_year[2024]["p99"] > by_year[2023]["p99"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/analysis/test_year_fe_diagnostic.py -v`
Expected: FAIL (ImportError on `year_fe_diagnostic` module).

- [ ] **Step 3: Create `year_fe_diagnostic.py` skeleton**

Create `src/surg/analysis/year_fe_diagnostic.py`:

```python
"""τ=0.99 secular sign-flip diagnostic (sub-q1 closure item #3).

Three-layer evidence:
  L1: raw per-year LMP percentile stats (descriptive only).
  L2: pair-bootstrap year-dummy coefficient CIs (per-year LEVEL SHIFTS,
      not a trend test).
  L3: pair-bootstrap secular-component CI = primary_z_slope - year_fe_z_slope
      at each tau (the actual trend test).

Reuses qr_full.fit_qr_full for the year-FE QR.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.qr_full import fit_qr_full


def compute_raw_per_year_stats(
    panel: pd.DataFrame,
    *,
    response_col: str,
    year_col: str,
    pct_list: tuple[float, ...] = (0.90, 0.95, 0.99),
) -> list[dict]:
    """Per-year summary stats of `response_col`. Descriptive only — no model."""
    sub = panel.dropna(subset=[response_col, year_col]).copy()
    sub["__year"] = pd.to_datetime(sub[year_col]).dt.year
    stats: list[dict] = []
    for year, group in sub.groupby("__year"):
        row = {"year": int(year), "n_obs": int(len(group))}
        for p in pct_list:
            row[f"p{int(p*100)}"] = float(np.quantile(group[response_col].to_numpy(), p))
        stats.append(row)
    return sorted(stats, key=lambda r: r["year"])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_year_fe_diagnostic.py -v`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/year_fe_diagnostic.py tests/analysis/test_year_fe_diagnostic.py
git commit -m "feat(analysis): year_fe_diagnostic Layer 1 — raw per-year stats"
```

---

## Task 10: Add `bootstrap_year_dummy_coefs` to `year_fe_diagnostic.py`

**Files:**
- Modify: `src/surg/analysis/year_fe_diagnostic.py`
- Modify: `tests/analysis/test_year_fe_diagnostic.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_year_fe_diagnostic.py`:

```python
def test_bootstrap_year_dummy_coefs_returns_ci_per_year():
    from surg.analysis.year_fe_diagnostic import bootstrap_year_dummy_coefs

    panel = _two_year_panel(per_year=1500, seed=1)
    result = bootstrap_year_dummy_coefs(
        panel,
        response_col="Y",
        z_col="Z",
        year_col="datetime_beginning_ept",
        taus=(0.50,),
        n_boot=40,
        seed=0,
    )
    assert "tau_0.50" in result
    by_year = result["tau_0.50"]
    # Baseline (2023) excluded; 2024 dummy present.
    assert "year_2024" in by_year
    entry = by_year["year_2024"]
    assert "point" in entry
    assert "ci" in entry
    assert len(entry["ci"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_year_fe_diagnostic.py::test_bootstrap_year_dummy_coefs_returns_ci_per_year -v`
Expected: FAIL.

- [ ] **Step 3: Implement `bootstrap_year_dummy_coefs`**

Append to `src/surg/analysis/year_fe_diagnostic.py`:

```python
def bootstrap_year_dummy_coefs(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    year_col: str,
    taus: tuple[float, ...],
    n_boot: int = 200,
    seed: int = 0,
) -> dict:
    """Pair-bootstrap CIs for year-dummy coefficients in fit_qr_full's year_fe spec.

    Reports descriptive PER-YEAR LEVEL SHIFTS (from baseline). NOT a trend test.
    """
    sub = panel.dropna(subset=[response_col, z_col, year_col]).copy()
    sub[year_col] = pd.to_datetime(sub[year_col])
    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()
    hour = sub[year_col].dt.hour.to_numpy()
    month = sub[year_col].dt.month.to_numpy()
    year = sub[year_col].dt.year.to_numpy()

    distinct_years = sorted(np.unique(year).tolist())
    if len(distinct_years) < 2:
        return {"skip_reason": f"only {len(distinct_years)} distinct year(s)"}

    baseline = distinct_years[0]
    dummy_years = distinct_years[1:]

    out: dict = {}
    n = len(Y)
    for tau_idx, tau in enumerate(taus):
        # Point estimate from a single fit (no bootstrap of point).
        point_fit = fit_qr_full(Y, Z, hour, month, year=year, tau=tau, n_boot=0,
                                seed=seed + tau_idx * 1000)
        point_coefs = point_fit.covariate_coefs

        # Pair-bootstrap each year dummy.
        rng = np.random.default_rng(seed + tau_idx * 1000 + 7)
        boot_coefs: dict[int, list[float]] = {y: [] for y in dummy_years}
        for rep in range(n_boot):
            idx = rng.integers(0, n, size=n)
            try:
                rep_fit = fit_qr_full(
                    Y[idx], Z[idx], hour[idx], month[idx],
                    year=year[idx], tau=tau, n_boot=0, seed=0,
                )
            except Exception:
                continue
            for y in dummy_years:
                key = f"year_{y}"
                if key in rep_fit.covariate_coefs:
                    val = rep_fit.covariate_coefs[key]
                    if np.isfinite(val):
                        boot_coefs[y].append(val)

        by_year: dict[str, dict] = {}
        for y in dummy_years:
            arr = np.asarray(boot_coefs[y])
            if len(arr) < 20:
                ci = (float("nan"), float("nan"))
            else:
                ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
            by_year[f"year_{y}"] = {
                "point": _nan_to_none(point_coefs.get(f"year_{y}", float("nan"))),
                "ci": [_nan_to_none(ci[0]), _nan_to_none(ci[1])],
                "n_boot_converged": int(len(arr)),
            }
        out[f"tau_{tau:.2f}"] = by_year
        out[f"tau_{tau:.2f}_baseline_year"] = int(baseline)
    return out


def _nan_to_none(x: float | None) -> float | None:
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return float(x)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_year_fe_diagnostic.py -v`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/year_fe_diagnostic.py tests/analysis/test_year_fe_diagnostic.py
git commit -m "feat(analysis): year_fe_diagnostic Layer 2 — year-dummy coef bootstrap (per-year level shifts)"
```

---

## Task 11: Add `bootstrap_secular_component` to `year_fe_diagnostic.py`

**Files:**
- Modify: `src/surg/analysis/year_fe_diagnostic.py`
- Modify: `tests/analysis/test_year_fe_diagnostic.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_year_fe_diagnostic.py`:

```python
def test_bootstrap_secular_component_returns_ci_per_tau():
    from surg.analysis.year_fe_diagnostic import bootstrap_secular_component

    panel = _two_year_panel(per_year=1500, seed=2)
    result = bootstrap_secular_component(
        panel,
        response_col="Y",
        z_col="Z",
        year_col="datetime_beginning_ept",
        taus=(0.50, 0.95),
        n_boot=30,
        seed=0,
    )
    for key in ("tau_0.50", "tau_0.95"):
        assert key in result
        entry = result[key]
        assert "primary_z_slope" in entry
        assert "year_fe_z_slope" in entry
        assert "secular_component_point" in entry
        assert "secular_component_ci" in entry
        assert len(entry["secular_component_ci"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_year_fe_diagnostic.py::test_bootstrap_secular_component_returns_ci_per_tau -v`
Expected: FAIL.

- [ ] **Step 3: Implement `bootstrap_secular_component`**

Append to `src/surg/analysis/year_fe_diagnostic.py`:

```python
def bootstrap_secular_component(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    year_col: str,
    taus: tuple[float, ...],
    n_boot: int = 200,
    seed: int = 0,
) -> dict:
    """Pair-bootstrap CI on primary_z_slope - year_fe_z_slope per tau.

    This IS the trend test for the τ=0.99 secular sign-flip claim.
    """
    sub = panel.dropna(subset=[response_col, z_col, year_col]).copy()
    sub[year_col] = pd.to_datetime(sub[year_col])
    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()
    hour = sub[year_col].dt.hour.to_numpy()
    month = sub[year_col].dt.month.to_numpy()
    year = sub[year_col].dt.year.to_numpy()

    distinct_years = sorted(np.unique(year).tolist())
    if len(distinct_years) < 2:
        return {"skip_reason": f"only {len(distinct_years)} distinct year(s)"}

    out: dict = {}
    n = len(Y)
    for tau_idx, tau in enumerate(taus):
        primary_fit = fit_qr_full(Y, Z, hour, month, tau=tau, n_boot=0, seed=seed)
        yfe_fit = fit_qr_full(Y, Z, hour, month, year=year, tau=tau, n_boot=0, seed=seed)
        point_secular = primary_fit.z_slope - yfe_fit.z_slope

        rng = np.random.default_rng(seed + tau_idx * 1000 + 11)
        diffs: list[float] = []
        for rep in range(n_boot):
            idx = rng.integers(0, n, size=n)
            try:
                pfit = fit_qr_full(Y[idx], Z[idx], hour[idx], month[idx],
                                   tau=tau, n_boot=0, seed=0)
                yfit = fit_qr_full(Y[idx], Z[idx], hour[idx], month[idx],
                                   year=year[idx], tau=tau, n_boot=0, seed=0)
            except Exception:
                continue
            d = pfit.z_slope - yfit.z_slope
            if np.isfinite(d):
                diffs.append(d)
        if len(diffs) < 20:
            ci = (float("nan"), float("nan"))
        else:
            arr = np.asarray(diffs)
            ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
        out[f"tau_{tau:.2f}"] = {
            "primary_z_slope": _nan_to_none(primary_fit.z_slope),
            "year_fe_z_slope": _nan_to_none(yfe_fit.z_slope),
            "secular_component_point": _nan_to_none(point_secular),
            "secular_component_ci": [_nan_to_none(ci[0]), _nan_to_none(ci[1])],
            "n_boot_converged": int(len(diffs)),
        }
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_year_fe_diagnostic.py -v`
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/year_fe_diagnostic.py tests/analysis/test_year_fe_diagnostic.py
git commit -m "feat(analysis): year_fe_diagnostic Layer 3 — secular-component bootstrap (trend test)"
```

---

## Task 12: Add `run_year_fe_diagnostic` orchestrator + wire into `run_all`

**Files:**
- Modify: `src/surg/analysis/year_fe_diagnostic.py`
- Modify: `tests/analysis/test_year_fe_diagnostic.py`
- Modify: `src/surg/analysis/run.py`

- [ ] **Step 1: Write failing test for orchestrator**

Append to `tests/analysis/test_year_fe_diagnostic.py`:

```python
def test_run_year_fe_diagnostic_writes_per_pnode_json(tmp_path: Path):
    from surg.analysis.year_fe_diagnostic import run_year_fe_diagnostic

    panel = _two_year_panel(per_year=1200, seed=3)
    out_path = tmp_path / "year_fe_diagnostic" / "test_pnode.json"
    run_year_fe_diagnostic(
        panel=panel,
        out_path=out_path,
        pnode_label="test_pnode",
        response_col="Y",
        z_col="Z",
        taus=(0.50, 0.95),
        n_boot=20,
        seed=0,
    )
    assert out_path.exists()
    payload = json.loads(out_path.read_text())
    assert payload["pnode_label"] == "test_pnode"
    assert payload["response_col"] == "Y"
    assert "layer1_raw_per_year" in payload
    assert "layer2_year_dummy_bootstrap" in payload
    assert "layer3_secular_component_bootstrap" in payload
    assert len(payload["layer1_raw_per_year"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_year_fe_diagnostic.py::test_run_year_fe_diagnostic_writes_per_pnode_json -v`
Expected: FAIL.

- [ ] **Step 3: Implement `run_year_fe_diagnostic`**

Append to `src/surg/analysis/year_fe_diagnostic.py`:

```python
def run_year_fe_diagnostic(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    pnode_label: str,
    response_col: str,
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    taus: tuple[float, ...] = (0.90, 0.95, 0.99),
    pct_list: tuple[float, ...] = (0.90, 0.95, 0.99),
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """Run three-layer year-FE diagnostic for one pnode. Writes JSON at out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    layer1 = compute_raw_per_year_stats(
        panel, response_col=response_col,
        year_col="datetime_beginning_ept",
        pct_list=pct_list,
    )
    layer2 = bootstrap_year_dummy_coefs(
        panel, response_col=response_col, z_col=z_col,
        year_col="datetime_beginning_ept",
        taus=taus, n_boot=n_boot, seed=seed,
    )
    layer3 = bootstrap_secular_component(
        panel, response_col=response_col, z_col=z_col,
        year_col="datetime_beginning_ept",
        taus=taus, n_boot=n_boot, seed=seed + 50,
    )

    payload = {
        "pnode_label": pnode_label,
        "response_col": response_col,
        "z_col": z_col,
        "taus": list(taus),
        "n_total_panel": int(len(panel)),
        "n_after_dropna": int(panel.dropna(subset=[response_col, z_col]).shape[0]),
        "layer1_raw_per_year": layer1,
        "layer2_year_dummy_bootstrap": layer2,
        "layer3_secular_component_bootstrap": layer3,
        "layer2_label": "PER-YEAR LEVEL SHIFTS — descriptive supplementary, not a trend test",
        "layer3_label": "SECULAR-COMPONENT TREND TEST — primary_z_slope - year_fe_z_slope per τ",
    }
    out_path.write_text(json.dumps(payload, indent=2))
```

- [ ] **Step 4: Wire into `run_all`**

In `src/surg/analysis/run.py`:
- Add CLI flags `--year-fe-n-boot` (default 200) and `--skip-year-fe-diagnostic` (action store_true).
- Add corresponding parameters to `run_all` (matching the pattern in Task 8).
- After the gpd_components call, add:

```python
# Sub-q1 closure item #3: τ=0.99 secular sign-flip diagnostic (descriptive).
if not skip_year_fe_diagnostic:
    from surg.analysis.year_fe_diagnostic import run_year_fe_diagnostic
    for label, col in PNODE_RESPONSES.items():
        if panel[col].dropna().empty:
            continue
        run_year_fe_diagnostic(
            panel=panel,
            out_path=out_root / "year_fe_diagnostic" / f"{label}.json",
            pnode_label=label,
            response_col=col,
            n_boot=year_fe_n_boot,
        )
```

- [ ] **Step 5: Add `write_cross_pnode_summary` helper**

After the per-pnode loop in `run_all`, write a flattened cross-pnode table to
`outputs/year_fe_diagnostic/cross_pnode_summary.json`. Append to
`src/surg/analysis/year_fe_diagnostic.py`:

```python
def write_cross_pnode_summary(out_dir: Path, pnode_labels: tuple[str, ...]) -> None:
    """Aggregate per-pnode year_fe_diagnostic JSONs into one flat table."""
    rows: list[dict] = []
    for label in pnode_labels:
        path = out_dir / f"{label}.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text())
        for tau_key, l3 in payload.get("layer3_secular_component_bootstrap", {}).items():
            if isinstance(l3, dict) and "secular_component_point" in l3:
                rows.append({
                    "pnode_label": label,
                    "tau_key": tau_key,
                    "primary_z_slope": l3["primary_z_slope"],
                    "year_fe_z_slope": l3["year_fe_z_slope"],
                    "secular_component_point": l3["secular_component_point"],
                    "secular_component_ci": l3["secular_component_ci"],
                })
    (out_dir / "cross_pnode_summary.json").write_text(
        json.dumps({"rows": rows}, indent=2)
    )
```

And update the wiring step to call it after the loop:

```python
if not skip_year_fe_diagnostic:
    from surg.analysis.year_fe_diagnostic import run_year_fe_diagnostic, write_cross_pnode_summary
    pnode_labels_processed: list[str] = []
    for label, col in PNODE_RESPONSES.items():
        if panel[col].dropna().empty:
            continue
        run_year_fe_diagnostic(
            panel=panel,
            out_path=out_root / "year_fe_diagnostic" / f"{label}.json",
            pnode_label=label,
            response_col=col,
            n_boot=year_fe_n_boot,
        )
        pnode_labels_processed.append(label)
    write_cross_pnode_summary(out_root / "year_fe_diagnostic", tuple(pnode_labels_processed))
```

Add a test for `write_cross_pnode_summary` in
`tests/analysis/test_year_fe_diagnostic.py`:

```python
def test_write_cross_pnode_summary_aggregates_per_pnode_jsons(tmp_path: Path):
    from surg.analysis.year_fe_diagnostic import write_cross_pnode_summary

    out_dir = tmp_path / "year_fe_diagnostic"
    out_dir.mkdir()
    for label in ("pnode_a", "pnode_b"):
        (out_dir / f"{label}.json").write_text(json.dumps({
            "pnode_label": label,
            "layer3_secular_component_bootstrap": {
                "tau_0.95": {"primary_z_slope": 1.0, "year_fe_z_slope": 0.5,
                              "secular_component_point": 0.5,
                              "secular_component_ci": [0.0, 1.0]},
            },
        }))
    write_cross_pnode_summary(out_dir, ("pnode_a", "pnode_b"))
    summary = json.loads((out_dir / "cross_pnode_summary.json").read_text())
    assert len(summary["rows"]) == 2
    labels = {r["pnode_label"] for r in summary["rows"]}
    assert labels == {"pnode_a", "pnode_b"}
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/analysis/test_year_fe_diagnostic.py tests/analysis/ -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/surg/analysis/year_fe_diagnostic.py tests/analysis/test_year_fe_diagnostic.py src/surg/analysis/run.py
git commit -m "feat(analysis): year_fe_diagnostic orchestrator + run_all wiring + cross-pnode summary"
```

---

## Task 13: Create `ashburn_diagnostic.py` skeleton + `loo_beta_distribution`

**Files:**
- Create: `src/surg/analysis/ashburn_diagnostic.py`
- Test: `tests/analysis/test_ashburn_diagnostic.py`

- [ ] **Step 1: Write failing test for `loo_beta_distribution`**

Create `tests/analysis/test_ashburn_diagnostic.py`:

```python
"""Tests for ashburn_diagnostic.py — sub-q1 closure item #4 (descriptive)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _ashburn_fixture(n_rows: int = 4000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n_rows, freq="h"),
        "dom_load_gradient_abs_mw_per_min": rng.uniform(0, 10, size=n_rows),
        "total_lmp_rt_ashburn_tx1": rng.exponential(2.0, size=n_rows),
        "total_lmp_rt_ashburn_tx2": rng.exponential(1.8, size=n_rows),
    })


def test_loo_beta_distribution_returns_n_exc_betas():
    from surg.analysis.ashburn_diagnostic import loo_beta_distribution

    panel = _ashburn_fixture()
    result = loo_beta_distribution(
        panel=panel,
        response_col="total_lmp_rt_ashburn_tx1",
        z_col="dom_load_gradient_abs_mw_per_min",
        threshold_quantile=0.95,
    )
    assert result.n_exc > 0
    assert len(result.loo_beta_1_distribution) == result.n_exc
    assert len(result.delta_beta_1_per_exceedance) == result.n_exc
    assert len(result.top5_influential_indices) == min(5, result.n_exc)


def test_loo_beta_distribution_top5_sorted_descending_by_delta():
    from surg.analysis.ashburn_diagnostic import loo_beta_distribution

    panel = _ashburn_fixture(n_rows=2000, seed=42)
    result = loo_beta_distribution(
        panel=panel,
        response_col="total_lmp_rt_ashburn_tx1",
        z_col="dom_load_gradient_abs_mw_per_min",
        threshold_quantile=0.95,
    )
    deltas = result.delta_beta_1_per_exceedance
    top5 = result.top5_influential_indices
    sorted_top5 = sorted(top5, key=lambda i: -abs(deltas[i]))
    assert top5 == sorted_top5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/analysis/test_ashburn_diagnostic.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `loo_beta_distribution`**

Create `src/surg/analysis/ashburn_diagnostic.py`:

```python
"""Ashburn TX1 99th-pct anomaly diagnostic (sub-q1 closure item #4).

LOO sensitivity at all 4 thresholds (90/95/99/99.5) on TX1 + TX2;
cross-threshold full-sample comparison extracted from existing Spec B
JSON; 4-panel overlay scatter PNG.

Reuses gpd_continuous.fit_gpd_continuous_z (linear form) for the LOO fits.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.gpd_continuous import fit_gpd_continuous_z


@dataclass(frozen=True, slots=True)
class LOOResult:
    pnode_label: str
    threshold_quantile: float
    n_exc: int
    full_sample_beta_1: float
    loo_beta_1_distribution: tuple[float, ...]
    delta_beta_1_per_exceedance: tuple[float, ...]
    top5_influential_indices: tuple[int, ...]
    full_sample_percentile_in_loo: float


def loo_beta_distribution(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    threshold_quantile: float,
    pnode_label: str = "",
) -> LOOResult:
    """Leave-one-out β₁ sensitivity for Spec B linear form fit on a single pnode/threshold."""
    sub = panel.dropna(subset=[response_col, z_col]).copy()
    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()
    threshold = float(np.quantile(Y, threshold_quantile))
    exc_mask = Y > threshold
    Y_exc = Y[exc_mask]
    Z_exc = Z[exc_mask]
    n_exc = len(Y_exc)

    full = fit_gpd_continuous_z(
        Y=Y_exc, Z=Z_exc, threshold=threshold, form="linear", n_boot=0, seed=0,
    )
    full_beta_1 = float(full.shape_coefficients[1]) if full.convergence_status == "converged" else float("nan")

    loo_beta_1: list[float] = []
    delta_beta_1: list[float] = []
    for i in range(n_exc):
        mask = np.ones(n_exc, dtype=bool)
        mask[i] = False
        try:
            r = fit_gpd_continuous_z(
                Y=Y_exc[mask], Z=Z_exc[mask], threshold=threshold,
                form="linear", n_boot=0, seed=0,
            )
            b = float(r.shape_coefficients[1]) if r.convergence_status == "converged" else float("nan")
        except Exception:
            b = float("nan")
        loo_beta_1.append(b)
        delta_beta_1.append(b - full_beta_1 if math.isfinite(b) and math.isfinite(full_beta_1) else float("nan"))

    abs_deltas = [abs(d) if math.isfinite(d) else -1.0 for d in delta_beta_1]
    top5 = tuple(sorted(range(n_exc), key=lambda i: -abs_deltas[i])[:min(5, n_exc)])

    finite_loo = [b for b in loo_beta_1 if math.isfinite(b)]
    if finite_loo and math.isfinite(full_beta_1):
        pct = float((np.asarray(finite_loo) <= full_beta_1).mean())
    else:
        pct = float("nan")

    return LOOResult(
        pnode_label=pnode_label,
        threshold_quantile=threshold_quantile,
        n_exc=n_exc,
        full_sample_beta_1=full_beta_1,
        loo_beta_1_distribution=tuple(loo_beta_1),
        delta_beta_1_per_exceedance=tuple(delta_beta_1),
        top5_influential_indices=top5,
        full_sample_percentile_in_loo=pct,
    )
```

(If `fit_gpd_continuous_z`'s positional / keyword arg shape differs from this draft, adjust the call site to match; read `src/surg/analysis/gpd_continuous.py` for the actual signature before invoking.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_ashburn_diagnostic.py -v`
Expected: 2 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/ashburn_diagnostic.py tests/analysis/test_ashburn_diagnostic.py
git commit -m "feat(analysis): ashburn_diagnostic LOO β₁ distribution"
```

---

## Task 14: Add `extract_threshold_sweep_summary` to `ashburn_diagnostic.py`

**Files:**
- Modify: `src/surg/analysis/ashburn_diagnostic.py`
- Modify: `tests/analysis/test_ashburn_diagnostic.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_ashburn_diagnostic.py`:

```python
def _make_spec_b_json_fixture(tmp_path: Path, pnode: str) -> Path:
    path = tmp_path / f"{pnode}.json"
    path.write_text(json.dumps({
        "response_col": f"total_lmp_rt_{pnode}",
        "pnode_label": pnode,
        "threshold_sweep": [
            {"threshold_quantile": 0.90, "linear": {"shape_coefficients": [0.5, -0.01],
              "shape_coefficients_bootstrap_ci_95": [[0.3, 0.7], [-0.02, 0.001]],
              "convergence_status": "converged"}},
            {"threshold_quantile": 0.95, "linear": {"shape_coefficients": [0.6, -0.025],
              "shape_coefficients_bootstrap_ci_95": [[0.4, 0.8], [-0.049, -0.004]],
              "convergence_status": "converged"}},
            {"threshold_quantile": 0.99, "linear": {"shape_coefficients": [0.7, 0.09],
              "shape_coefficients_bootstrap_ci_95": [[0.5, 0.9], [0.01, 0.17]],
              "convergence_status": "converged"}},
        ],
    }, indent=2))
    return path


def test_extract_threshold_sweep_summary_parses_spec_b_json(tmp_path: Path):
    from surg.analysis.ashburn_diagnostic import extract_threshold_sweep_summary

    json_path = _make_spec_b_json_fixture(tmp_path, "ashburn_tx1")
    summary = extract_threshold_sweep_summary(
        spec_b_json_path=json_path,
        threshold_qs=(0.90, 0.95, 0.99),
    )
    assert summary["pnode_label"] == "ashburn_tx1"
    assert len(summary["entries"]) == 3
    entry_99 = next(e for e in summary["entries"] if e["threshold_quantile"] == 0.99)
    assert entry_99["beta_1"] == 0.09
    assert entry_99["beta_1_ci_95"] == [0.01, 0.17]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_ashburn_diagnostic.py::test_extract_threshold_sweep_summary_parses_spec_b_json -v`
Expected: FAIL.

- [ ] **Step 3: Implement `extract_threshold_sweep_summary`**

Append to `src/surg/analysis/ashburn_diagnostic.py`:

```python
def extract_threshold_sweep_summary(
    *,
    spec_b_json_path: Path,
    threshold_qs: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
) -> dict:
    """Pull Spec B linear-form β₁ + CI for a pnode at each threshold quantile."""
    payload = json.loads(spec_b_json_path.read_text())
    entries: list[dict] = []
    for q in threshold_qs:
        match = next(
            (e for e in payload.get("threshold_sweep", [])
             if abs(e.get("threshold_quantile", -1) - q) < 1e-6),
            None,
        )
        if match is None or "linear" not in match:
            continue
        lin = match["linear"]
        beta_1 = lin["shape_coefficients"][1] if lin.get("convergence_status") == "converged" else None
        ci_pair = lin.get("shape_coefficients_bootstrap_ci_95")
        beta_1_ci = ci_pair[1] if (ci_pair is not None and len(ci_pair) > 1) else None
        entries.append({
            "threshold_quantile": q,
            "beta_1": beta_1,
            "beta_1_ci_95": beta_1_ci,
            "convergence_status": lin.get("convergence_status"),
        })
    return {
        "pnode_label": payload.get("pnode_label"),
        "response_col": payload.get("response_col"),
        "entries": entries,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_ashburn_diagnostic.py -v`
Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/ashburn_diagnostic.py tests/analysis/test_ashburn_diagnostic.py
git commit -m "feat(analysis): ashburn_diagnostic — Spec B JSON cross-threshold extraction"
```

---

## Task 15: Add `plot_lmp_vs_z_scatter` to `ashburn_diagnostic.py` (4-panel overlay)

**Files:**
- Modify: `src/surg/analysis/ashburn_diagnostic.py`
- Modify: `tests/analysis/test_ashburn_diagnostic.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_ashburn_diagnostic.py`:

```python
def test_plot_lmp_vs_z_scatter_writes_nonempty_png(tmp_path: Path):
    from surg.analysis.ashburn_diagnostic import plot_lmp_vs_z_scatter

    panel = _ashburn_fixture(n_rows=3000, seed=7)
    out_path = tmp_path / "scatter_overlay.png"
    plot_lmp_vs_z_scatter(
        panel=panel,
        pnode_response_cols={"ashburn_tx1": "total_lmp_rt_ashburn_tx1",
                             "ashburn_tx2": "total_lmp_rt_ashburn_tx2"},
        z_col="dom_load_gradient_abs_mw_per_min",
        threshold_qs=(0.90, 0.95, 0.99, 0.995),
        out_path=out_path,
        fitted_slopes={"ashburn_tx1": {0.95: -0.025, 0.99: 0.093},
                       "ashburn_tx2": {0.95: -0.012, 0.99: -0.008}},
    )
    assert out_path.exists()
    assert out_path.stat().st_size > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_ashburn_diagnostic.py::test_plot_lmp_vs_z_scatter_writes_nonempty_png -v`
Expected: FAIL.

- [ ] **Step 3: Implement `plot_lmp_vs_z_scatter`**

Append to `src/surg/analysis/ashburn_diagnostic.py`:

```python
def plot_lmp_vs_z_scatter(
    panel: pd.DataFrame,
    *,
    pnode_response_cols: dict[str, str],   # pnode_label -> response_col
    z_col: str,
    threshold_qs: tuple[float, ...],
    out_path: Path,
    fitted_slopes: dict[str, dict[float, float]] | None = None,
    figsize: tuple[float, float] = (14, 10),
) -> None:
    """4-panel overlay scatter of LMP vs Z at each threshold quantile.

    Marker shape distinguishes pnodes. Color encodes year.
    """
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=False, sharey=False)
    axes_flat = axes.flatten()

    markers = {"ashburn_tx1": "o", "ashburn_tx2": "^"}

    for ax_i, q in enumerate(threshold_qs):
        ax = axes_flat[ax_i]
        for pnode, col in pnode_response_cols.items():
            sub = panel.dropna(subset=[col, z_col]).copy()
            sub["__year"] = pd.to_datetime(sub["datetime_beginning_ept"]).dt.year
            threshold = float(np.quantile(sub[col].to_numpy(), q))
            exc = sub[sub[col] > threshold]
            ax.scatter(
                exc[z_col], exc[col],
                marker=markers.get(pnode, "x"),
                c=exc["__year"], cmap="viridis",
                alpha=0.6, s=20, label=pnode,
            )
            if fitted_slopes and pnode in fitted_slopes and q in fitted_slopes[pnode]:
                slope = fitted_slopes[pnode][q]
                z_line = np.linspace(exc[z_col].min(), exc[z_col].max(), 50)
                # Linear shape parameter visualization, NOT the LMP value — purely indicative.
                ax.plot(z_line, threshold + slope * z_line * (exc[col].max() - threshold),
                        linestyle="--", linewidth=1, alpha=0.7, label=f"{pnode} slope={slope:.3f}")
        ax.set_title(f"Threshold quantile = {q}")
        ax.set_xlabel(z_col)
        ax.set_ylabel("LMP")
        ax.legend(loc="upper right", fontsize=8)
    fig.suptitle("Ashburn TX1 vs TX2 — exceedances at each threshold")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/analysis/test_ashburn_diagnostic.py -v`
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/ashburn_diagnostic.py tests/analysis/test_ashburn_diagnostic.py
git commit -m "feat(analysis): ashburn_diagnostic — 4-panel TX1+TX2 overlay scatter"
```

---

## Task 16: Add `run_ashburn_diagnostic` orchestrator + wire into `run_all`

**Files:**
- Modify: `src/surg/analysis/ashburn_diagnostic.py`
- Modify: `tests/analysis/test_ashburn_diagnostic.py`
- Modify: `src/surg/analysis/run.py`

- [ ] **Step 1: Write failing test for orchestrator**

Append to `tests/analysis/test_ashburn_diagnostic.py`:

```python
def test_run_ashburn_diagnostic_writes_all_outputs(tmp_path: Path):
    from surg.analysis.ashburn_diagnostic import run_ashburn_diagnostic

    panel = _ashburn_fixture(n_rows=2000, seed=5)
    spec_b_dir = tmp_path / "gpd_continuous"
    spec_b_dir.mkdir()
    _make_spec_b_json_fixture(spec_b_dir, "ashburn_tx1")
    _make_spec_b_json_fixture(spec_b_dir, "ashburn_tx2")

    out_dir = tmp_path / "ashburn_diagnostic"
    run_ashburn_diagnostic(
        panel=panel,
        out_dir=out_dir,
        spec_b_results_dir=spec_b_dir,
        threshold_quantiles=(0.90, 0.95),  # smaller for test speed
    )
    assert (out_dir / "tx1_loo.json").exists()
    assert (out_dir / "tx2_loo.json").exists()
    assert (out_dir / "cross_threshold_summary.json").exists()
    assert (out_dir / "scatter_overlay.png").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/analysis/test_ashburn_diagnostic.py::test_run_ashburn_diagnostic_writes_all_outputs -v`
Expected: FAIL.

- [ ] **Step 3: Implement `run_ashburn_diagnostic`**

Append to `src/surg/analysis/ashburn_diagnostic.py`:

```python
def _loo_to_dict(r: LOOResult) -> dict:
    return {
        "pnode_label": r.pnode_label,
        "threshold_quantile": r.threshold_quantile,
        "n_exc": r.n_exc,
        "full_sample_beta_1": _nan_to_none(r.full_sample_beta_1),
        "loo_beta_1_distribution": [_nan_to_none(b) for b in r.loo_beta_1_distribution],
        "delta_beta_1_per_exceedance": [_nan_to_none(d) for d in r.delta_beta_1_per_exceedance],
        "top5_influential_indices": list(r.top5_influential_indices),
        "full_sample_percentile_in_loo": _nan_to_none(r.full_sample_percentile_in_loo),
    }


def _nan_to_none(x: float | None) -> float | None:
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return float(x)


def run_ashburn_diagnostic(
    panel: pd.DataFrame,
    out_dir: Path,
    *,
    pnode_labels: tuple[str, ...] = ("ashburn_tx1", "ashburn_tx2"),
    threshold_quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    spec_b_results_dir: Path | None = None,
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    response_col_template: str = "total_lmp_rt_{pnode}",
    seed: int = 0,
) -> None:
    """Orchestrator for sub-q1 closure item #4 — Ashburn diagnostic."""
    out_dir.mkdir(parents=True, exist_ok=True)
    spec_b_dir = spec_b_results_dir if spec_b_results_dir is not None else Path("outputs/gpd_continuous")

    # Per-pnode LOO across thresholds.
    pnode_response_cols: dict[str, str] = {}
    fitted_slopes: dict[str, dict[float, float]] = {}
    cross_summary: list[dict] = []

    for pnode in pnode_labels:
        col = response_col_template.format(pnode=pnode)
        pnode_response_cols[pnode] = col
        loo_results: list[dict] = []
        for q in threshold_quantiles:
            r = loo_beta_distribution(
                panel=panel, response_col=col, z_col=z_col,
                threshold_quantile=q, pnode_label=pnode,
            )
            loo_results.append(_loo_to_dict(r))
        (out_dir / f"{pnode.replace('ashburn_', '')}_loo.json").write_text(
            json.dumps({"pnode_label": pnode, "results": loo_results}, indent=2)
        )

        # Cross-threshold summary from existing Spec B JSON (if present).
        spec_b_path = spec_b_dir / f"{pnode}.json"
        if spec_b_path.exists():
            summary = extract_threshold_sweep_summary(
                spec_b_json_path=spec_b_path,
                threshold_qs=threshold_quantiles,
            )
            cross_summary.append(summary)
            fitted_slopes[pnode] = {
                e["threshold_quantile"]: e["beta_1"]
                for e in summary["entries"]
                if e["beta_1"] is not None
            }

    (out_dir / "cross_threshold_summary.json").write_text(
        json.dumps({"pnodes": cross_summary}, indent=2)
    )

    plot_lmp_vs_z_scatter(
        panel=panel,
        pnode_response_cols=pnode_response_cols,
        z_col=z_col,
        threshold_qs=threshold_quantiles,
        out_path=out_dir / "scatter_overlay.png",
        fitted_slopes=fitted_slopes,
    )
```

(Note: file naming `tx1_loo.json` / `tx2_loo.json` comes from `pnode.replace('ashburn_', '')`. If the pnode label scheme changes, update both the orchestrator and the integration test in Task 17.)

- [ ] **Step 4: Wire into `run_all`**

In `src/surg/analysis/run.py`:
- Add CLI flag `--skip-ashburn-diagnostic` (action store_true).
- Add `--ashburn-loo-skip` (action store_true; soft idempotency — true reuses existing `outputs/ashburn_diagnostic/`).
- Add `skip_ashburn_diagnostic` and `ashburn_loo_skip` parameters to `run_all`.
- After the year_fe_diagnostic invocation, add:

```python
# Sub-q1 closure item #4: Ashburn TX1 anomaly diagnostic (descriptive).
if not skip_ashburn_diagnostic:
    from surg.analysis.ashburn_diagnostic import run_ashburn_diagnostic
    out_subdir = out_root / "ashburn_diagnostic"
    if ashburn_loo_skip and (out_subdir / "tx1_loo.json").exists():
        pass
    else:
        run_ashburn_diagnostic(
            panel=panel,
            out_dir=out_subdir,
            spec_b_results_dir=out_root / "gpd_continuous",
        )
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/analysis/ -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/ashburn_diagnostic.py tests/analysis/test_ashburn_diagnostic.py src/surg/analysis/run.py
git commit -m "feat(analysis): ashburn_diagnostic orchestrator + run_all wiring"
```

---

## Task 17: Extend `tests/analysis/test_run.py` for new expected paths

**Files:**
- Modify: `tests/analysis/test_run.py`

- [ ] **Step 1: Read existing test to find the expected-paths list**

Run: `grep -n "expected\|outputs/" tests/analysis/test_run.py | head -30`
Identify the variable that holds the expected output relative paths.

- [ ] **Step 2: Add the 16 new expected paths**

Add (in the order they appear during `run_all`):

```python
# Sub-q1 closure item #2 — LMP-components decomposition (4 paths):
"gpd_components/headline.json",
"gpd_components/primary_cluster_supplementary.json",
"gpd_components/cross_pnode.json",
"gpd_components/threshold_sweep.json",
# Sub-q1 closure item #3 — year-FE diagnostic per pnode (7 paths) + summary:
"year_fe_diagnostic/primary.json",
"year_fe_diagnostic/total_lmp.json",
"year_fe_diagnostic/ox.json",
"year_fe_diagnostic/bristers.json",
"year_fe_diagnostic/dom_zonal.json",
"year_fe_diagnostic/ashburn_tx1.json",
"year_fe_diagnostic/ashburn_tx2.json",
"year_fe_diagnostic/cross_pnode_summary.json",
# Sub-q1 closure item #4 — Ashburn diagnostic (4 paths):
"ashburn_diagnostic/tx1_loo.json",
"ashburn_diagnostic/tx2_loo.json",
"ashburn_diagnostic/cross_threshold_summary.json",
"ashburn_diagnostic/scatter_overlay.png",
```

If the existing test passes `n_boot=0` or similar tiny values, the gpd_components / year_fe / ashburn calls in `run_all` may emit `insufficient_sample` or skip rows — adjust the test fixture's n_boot params low but non-zero (e.g., 20) to keep at least the file paths created.

- [ ] **Step 3: Run integration test**

Run: `pytest tests/analysis/test_run.py -v`
Expected: pass with all expected paths present.

- [ ] **Step 4: Commit**

```bash
git add tests/analysis/test_run.py
git commit -m "test(analysis): integration test covers all 16 sub-q1 diagnostic output paths"
```

---

## Task 18: Full-coverage production run

**Files:**
- Generates: contents of `outputs/gpd_components/`, `outputs/year_fe_diagnostic/`, `outputs/ashburn_diagnostic/`

- [ ] **Step 1: Verify the panel is up-to-date**

Run: `surg-prep`
Expected: no errors. (If panel was rebuilt in Task 3, this is a no-op.)

- [ ] **Step 2: Run `surg-analyze` with full coverage**

Run:
```bash
surg-analyze \
  --panel data/interim/analysis_panel.parquet \
  --data-root data/raw \
  --out-root outputs \
  --n-boot 1000 \
  --qr-full-n-boot 200 \
  --gpd-n-boot 200 \
  --continuous-n-boot 200 \
  --components-n-boot 200 \
  --year-fe-n-boot 200
```

Expected: completes (estimated 7-8 hours; resumable). Writes all output files.

- [ ] **Step 3: Verify all expected new outputs exist**

Run:
```bash
ls outputs/gpd_components/
ls outputs/year_fe_diagnostic/
ls outputs/ashburn_diagnostic/
```
Expected: each directory contains its expected files (see Task 17's list).

- [ ] **Step 4: Inspect the gpd_components headline result**

Run: `cat outputs/gpd_components/headline.json`
Read the `rule_2_outcome` and `paper_claim` fields. Note the value — it determines which row of Rule 2 is dispatched into the application entry in Task 19.

- [ ] **Step 5: No commit (outputs/ is gitignored)**

Confirm `git status` shows no changes to track.

---

## Task 19: Apply item #2 pre-reg — write application entry in `docs/decisions.md`

**Files:**
- Modify: `docs/decisions.md`

- [ ] **Step 1: Read the headline numbers**

Read `outputs/gpd_components/headline.json` and capture: `n_exc`, `n_per_half`, `shape_diff`, `shape_diff_ci_95`, `rule_2_outcome`.

- [ ] **Step 2: Read the supplementary results**

Read `outputs/gpd_components/primary_cluster_supplementary.json`, `cross_pnode.json`, `threshold_sweep.json` for the descriptive tables.

- [ ] **Step 3: Append application entry to `docs/decisions.md`**

Append a new section (do NOT edit pre-existing content) titled:

```
## 2026-05-XX — Application of #2 pre-reg: LMP-components decomposition verdict
```

Body should include:

- **Headline (Rule 2 dispatch).** Paste the headline JSON's `paper_claim` verbatim. Below it:
  - `shape_diff = X.XXX`, bootstrap 95% CI `[a, b]`, `n_exc = N, n_per_half = M`.
  - The pre-reg's Rule 2 row dispatched: `cancellation_supported | ordc_rejected_broader | underpowered_neg_direction | underpowered_pos_direction | insufficient_sample`.
  - Pre-reg reference: `docs/decisions.md § 2026-05-XX — Pre-registration: LMP-components decomposition`.

- **Primary cluster supplementary** — small table: congestion + marginal_loss at p95 on primary cluster with `shape_diff`, CI, n. Note no MT correction (descriptive only).

- **Cross-pnode supplementary** — table: 3 components × 5 labeled pnodes at p95. Indicate any unexpected pattern (e.g., a single labeled pnode showing the opposite-direction rejection).

- **Threshold sweep supplementary** — table: 3 components × p90/p95/p99 on primary cluster.

- **Implication for sub-question 1.** One paragraph: how this changes (or doesn't) the conditional-Z verdict from the 2026-05-14 entry. Specifically: if `cancellation_supported`, the ORDC mechanism story is reinforced; if `ordc_rejected_broader`, the LOW-Z effect is broader than congestion alone; if underpowered/insufficient, the original congestion finding remains the headline.

- **Implication for the paper.** One paragraph: which version of the mechanism narrative is now supported.

- [ ] **Step 4: Commit**

```bash
git add docs/decisions.md outputs/gpd_components/headline.json outputs/gpd_components/primary_cluster_supplementary.json outputs/gpd_components/cross_pnode.json outputs/gpd_components/threshold_sweep.json
git commit -m "docs(decisions): apply LMP-components decomposition pre-reg (sub-q1 item #2)"
```

(Note: outputs/ is gitignored by default; this commit adds the JSON files explicitly. Confirm whether project convention is to commit these or leave them local. If gitignored is the convention, drop the JSON paths from `git add`.)

---

## Task 20: Item #3 application entry in `docs/decisions.md`

**Files:**
- Modify: `docs/decisions.md`

- [ ] **Step 1: Read the year-FE diagnostic outputs**

For each pnode label, read `outputs/year_fe_diagnostic/<label>.json` and capture:
- Layer 1 stats — year-by-year p99 LMP and n_exc.
- Layer 2 — year-dummy bootstrap CIs at τ=0.99 (descriptive level shifts).
- Layer 3 — secular-component point + CI at τ=0.99.

- [ ] **Step 2: Append application entry**

Append a new section:

```
## 2026-05-XX — Sub-q1 item #3: τ=0.99 secular sign-flip diagnostic (descriptive)
```

Body:

- **Layer 1 — raw per-year p99 LMP trajectory.** Table per pnode of year × p99 LMP × n_exc.
- **Layer 2 — year-dummy bootstrap (descriptive per-year level shifts, not a trend test).** Table per pnode of year × point × CI at τ=0.99.
- **Layer 3 — secular-component bootstrap (the trend test).** Per pnode at τ=0.99: `primary_z_slope`, `year_fe_z_slope`, `secular_component_point`, `secular_component_ci`. Interpret which case (a) real grid improvement, (b) sparse-tail artifact, (c) window-specific noise the evidence supports.
- **Implication for the paper.** One paragraph.
- **Implication for sub-question 2 (JLARC projection).** Recommendation on which z_slope (primary vs year-FE) to use at τ=0.99 for the projection layer.

- [ ] **Step 3: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): apply τ=0.99 secular sign-flip diagnostic (sub-q1 item #3)"
```

---

## Task 21: Item #4 application entry in `docs/decisions.md`

**Files:**
- Modify: `docs/decisions.md`

- [ ] **Step 1: Read the Ashburn diagnostic outputs**

For TX1 and TX2: read `outputs/ashburn_diagnostic/tx1_loo.json`, `tx2_loo.json`, and `cross_threshold_summary.json`. Capture LOO summary stats (full-sample β₁, LOO mean / median / IQR, top-5 influential exceedance indices) at each threshold.

- [ ] **Step 2: Append application entry**

Append:

```
## 2026-05-XX — Sub-q1 item #4: Ashburn TX1 99th-pct anomaly diagnostic (descriptive)
```

Body:

- **LOO summary at 99th-pct for TX1.** Full-sample β₁ vs LOO distribution; top-5 most influential exceedance indices and their |Δβ₁|. Note whether any single LOO refit changes the sign.
- **LOO summary at other thresholds.** Brief — full-sample β₁ + LOO distribution at p90/p95/p99.5.
- **TX2 cross-check at 99th-pct (and across all thresholds).** Side-by-side numbers. Direction agreement / disagreement at each threshold.
- **Reference to the 4-panel overlay scatter at `outputs/ashburn_diagnostic/scatter_overlay.png`.**
- **Interpretation:** which case (a) real distribution-side physics, (b) power-driven over-fit, (c) data-quality issue the evidence supports.
- **Implication for the paper.** One paragraph: methodology footnote framing for the Ashburn TX1 anomaly.

- [ ] **Step 3: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): apply Ashburn TX1 anomaly diagnostic (sub-q1 item #4)"
```

---

## Task 22: Update sub-q1 closure roadmap

**Files:**
- Modify: `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`

- [ ] **Step 1: Mark items #2/#3/#4 as DONE**

Edit `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`:
- Under "### 2. Response-variable sensitivity diagnostic", change status to **DONE** with commit SHA from Task 19; link to `docs/decisions.md § 2026-05-XX — Application of #2 pre-reg`.
- Under "### 3. τ = 0.99 secular sign-flip investigation", change status to **DONE** with commit SHA from Task 20; link to its application entry.
- Under "### 4. Ashburn TX1 diagnostic", change status to **DONE** with commit SHA from Task 21; link to its application entry.

- [ ] **Step 2: Update top-of-document status line**

In the document header, update the status to reflect: items #2/#3/#4 closed; only item #5 (advisor meeting) remains; sub-q1 substantially closed.

- [ ] **Step 3: Restate JLARC gate state**

In the "Out of scope" or "Sequencing" section, restate explicitly that JLARC implementation plan-writing remains gated on item #5.

- [ ] **Step 4: Commit**

```bash
git add docs/plans/2026-05-14-sub-question-1-closure-roadmap.md
git commit -m "docs(plans): close sub-q1 closure items #2/#3/#4 in roadmap"
```

---

## Final verification

- [ ] **Run the full test suite**

Run: `pytest -v`
Expected: all 213 + ~30 new tests pass (≈243 total).

- [ ] **Verify clean working tree**

Run: `git status`
Expected: clean.

- [ ] **Verify commit ahead-of-origin count**

Run: `git log --oneline origin/main..HEAD`
Expected: 22 task commits + 1 design doc commit = 23 commits ahead of origin/main (or whatever the count is depending on which commits were squashed; the per-task discipline is what matters).

- [ ] **Hand off**

When all tasks are checked off, the sub-q1 batched diagnostics plan is complete. Coordinate with the user on:
- FF merge of the feature branch back to `main`.
- Worktree cleanup.
- Push to origin/main (each push is its own ask).
- Roadmap item #5 (advisor meeting) is the only remaining sub-q1 work.
