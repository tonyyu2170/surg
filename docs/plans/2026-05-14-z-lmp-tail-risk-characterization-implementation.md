# Item #6 — Z → LMP Tail-Risk Characterization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a direct empirical answer to *"what range of Z makes LMP go crazy"* via binned exceedance-probability characterization, wired into the `surg-analyze` orchestrator alongside items #1–4.

**Architecture:** New `src/surg/analysis/tail_risk_curves.py` module (~250 lines) following the pattern of `gpd_components.py` / `year_fe_diagnostic.py` / `ashburn_diagnostic.py`. Pair-bootstrap CI (n=200) for project consistency. Outputs: 5 JSONs + 4 PNGs + 1 CSV in `outputs/tail_risk_curves/`. CLI flags `--tail-risk-n-boot` / `--skip-tail-risk-curves` / `--tail-risk-loo-skip`.

**Tech Stack:** Python 3.12, pandas, numpy, scipy.stats (`percentileofscore`), matplotlib, pytest. All deps already in the project.

**Design spec reference:** `docs/plans/2026-05-14-z-lmp-tail-risk-characterization-design.md` (committed at `6c7ebbb`).

---

## Pre-task: Worktree setup

**Why:** Item #6 follows the established feature-branch lifecycle (worktree → FF merge → cleanup). Implementation work happens in a sibling worktree, not on main directly.

- [ ] **Step 1: Verify clean state of main worktree**

Run from main worktree root:
```bash
cd /Users/turdy/docs/NU/Freshman_Year/Summer_2026/SURG/surg
git status
```
Expected: `On branch main` + `nothing to commit, working tree clean` (modulo any unpushed commits from earlier work).

- [ ] **Step 2: Create sibling worktree on a new feature branch**

```bash
git worktree add ../surg-item-6-tail-risk -b feature/sub-q1-item-6-tail-risk-curves
```
Expected: directory `../surg-item-6-tail-risk/` created, on new branch.

- [ ] **Step 3: Set up venv in the new worktree (or symlink existing)**

```bash
cd ../surg-item-6-tail-risk
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```
Expected: `pip install` completes; no errors.

- [ ] **Step 4: Verify baseline tests pass**

```bash
.venv/bin/pytest -q
```
Expected: 240 passed (matches the post-FF-merge baseline). If different, stop and report — something has drifted.

---

## File structure

This plan creates / modifies the following files:

| File | Purpose | Action |
|---|---|---|
| `src/surg/analysis/tail_risk_curves.py` | Item #6 module: decile binning, exceedance-probability with bootstrap CI, per-pnode orchestrator, cross-pnode summary, plotting | **Create** |
| `tests/analysis/test_tail_risk_curves.py` | Unit + integration tests for the new module | **Create** |
| `src/surg/analysis/run.py` | Add `run_tail_risk_curves` step + CLI flags | **Modify** |
| `tests/analysis/test_run.py` | Extend integration test to cover new output paths | **Modify** |
| `docs/decisions.md` | Application entry (post-production run) | **Modify (after Task 8)** |
| `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md` | Mark item #6 DONE (post-Task 9) | **Modify (after Task 9)** |

The module follows the established module pattern: helper functions, per-pnode orchestrator, cross-pnode aggregator, plotting, top-level orchestrator.

---

## Task 1: Module skeleton + Z decile helper

**Files:**
- Create: `src/surg/analysis/tail_risk_curves.py`
- Test: `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Write the failing test for `compute_z_deciles`**

Create `tests/analysis/test_tail_risk_curves.py`:
```python
"""Tests for src/surg/analysis/tail_risk_curves.py — sub-q1 item #6."""

import numpy as np
import pandas as pd
import pytest

from surg.analysis.tail_risk_curves import compute_z_deciles


def test_compute_z_deciles_returns_11_edges_and_correct_bin_indices():
    """Decile binning produces 11 edges + 10 bins; each obs assigned to its decile."""
    rng = np.random.default_rng(seed=0)
    panel = pd.DataFrame({"z": rng.uniform(0, 10, size=1000)})

    edges, bin_indices = compute_z_deciles(panel, "z")

    assert len(edges) == 11, "expected 11 edges (10 bins + upper bound)"
    assert len(bin_indices) == 1000, "one bin index per row"
    assert bin_indices.min() == 0
    assert bin_indices.max() == 9

    # Each bin should have ~100 observations (equal-count quantile bins)
    bin_counts = np.bincount(bin_indices, minlength=10)
    assert bin_counts.min() >= 95, f"bin counts too uneven: {bin_counts}"
    assert bin_counts.max() <= 105, f"bin counts too uneven: {bin_counts}"


def test_compute_z_deciles_handles_ties_at_boundary():
    """When Z has many ties, deciles still produce 10 valid bins (digitize handles)."""
    panel = pd.DataFrame({"z": np.concatenate([np.zeros(500), np.linspace(1, 10, 500)])})
    edges, bin_indices = compute_z_deciles(panel, "z")
    assert len(edges) == 11
    assert bin_indices.min() == 0
    assert bin_indices.max() == 9
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: FAIL with `ImportError: cannot import name 'compute_z_deciles' from 'surg.analysis.tail_risk_curves'` (module doesn't exist yet).

- [ ] **Step 3: Create the module skeleton with the function**

Create `src/surg/analysis/tail_risk_curves.py`:
```python
"""Direct Z -> LMP tail-risk characterization (sub-q1 closure item #6).

Per design spec at
`docs/plans/2026-05-14-z-lmp-tail-risk-characterization-design.md`.

Produces P(LMP > $X | Z bin) curves for the user's stated sub-q1
framing: "what range of Z makes LMP go crazy."

Mechanism evidence (items #1-4) explains WHY; this module produces
the descriptive WHERE.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def compute_z_deciles(panel: pd.DataFrame, z_col: str) -> tuple[np.ndarray, np.ndarray]:
    """Compute 10 equal-count quantile bins of Z.

    Returns
    -------
    edges : np.ndarray of shape (11,)
        Bin edges including endpoints. ``edges[0]`` = Z min, ``edges[10]`` = Z max.
    bin_indices : np.ndarray of shape (n,)
        Integer bin assignment in [0, 9] per row of ``panel``.
    """
    z = panel[z_col].to_numpy()
    edges = np.quantile(z, np.linspace(0.0, 1.0, 11))
    # digitize returns 1..N+1; clip into 0..9 so a value equal to edges[-1] lands in bin 9
    bin_indices = np.clip(np.digitize(z, edges[1:-1]), 0, 9)
    return edges, bin_indices
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "feat(analysis): tail_risk_curves skeleton + Z decile helper (item #6)"
```

---

## Task 2: Threshold percentile helper

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py`
- Modify: `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/analysis/test_tail_risk_curves.py`:
```python
from surg.analysis.tail_risk_curves import compute_threshold_percentiles


def test_compute_threshold_percentiles_returns_dict_per_threshold():
    """For known thresholds in a uniform [0, 100] distribution, the percentile-of-score should match the threshold itself."""
    panel = pd.DataFrame({"resp": np.linspace(0, 100, 10001)})
    thresholds = [25.0, 50.0, 75.0, 99.0]

    out = compute_threshold_percentiles(panel, "resp", thresholds)

    assert set(out.keys()) == {25.0, 50.0, 75.0, 99.0}
    # P(resp <= threshold) should equal threshold/100 for a uniform [0,100] series
    assert abs(out[25.0] - 0.25) < 0.001
    assert abs(out[50.0] - 0.50) < 0.001
    assert abs(out[75.0] - 0.75) < 0.001
    assert abs(out[99.0] - 0.99) < 0.001


def test_compute_threshold_percentiles_handles_threshold_above_max():
    """A threshold higher than the panel max returns percentile 1.0."""
    panel = pd.DataFrame({"resp": np.linspace(0, 100, 1001)})
    out = compute_threshold_percentiles(panel, "resp", [200.0])
    assert out[200.0] == pytest.approx(1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 2 new FAIL with `cannot import name 'compute_threshold_percentiles'`. Existing 2 tests still pass.

- [ ] **Step 3: Implement the function**

Append to `src/surg/analysis/tail_risk_curves.py`:
```python
from scipy import stats


def compute_threshold_percentiles(
    panel: pd.DataFrame,
    response_col: str,
    thresholds: list[float],
) -> dict[float, float]:
    """Map each $-threshold to its empirical percentile in the panel.

    Returns
    -------
    dict[float, float]
        ``{threshold_$: percentile_in_[0,1]}``. Used for annotating
        chart legends like ``"$500 (p99)"``.
    """
    resp = panel[response_col].dropna().to_numpy()
    return {
        float(t): float(stats.percentileofscore(resp, t, kind="weak") / 100.0)
        for t in thresholds
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 4 passed (2 from Task 1 + 2 new).

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "feat(analysis): tail_risk_curves — threshold percentile helper (item #6)"
```

---

## Task 3: Exceedance probability with pair-bootstrap CI

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py`
- Modify: `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/analysis/test_tail_risk_curves.py`:
```python
from surg.analysis.tail_risk_curves import compute_exceedance_probability_with_ci


def test_exceedance_probability_point_estimate_matches_empirical():
    """Point estimate is sum(resp > threshold) / n; matches naive count for any (Z, resp) panel."""
    rng = np.random.default_rng(seed=42)
    panel = pd.DataFrame({
        "z": rng.uniform(0, 1, size=1000),
        "resp": rng.normal(loc=50, scale=20, size=1000),
    })
    mask = np.ones(1000, dtype=bool)  # all rows
    threshold = 60.0

    p_hat, n_exc, n_total, ci_low, ci_high = compute_exceedance_probability_with_ci(
        panel, response_col="resp", threshold=threshold, z_bin_mask=mask, n_boot=50, seed=0
    )

    expected_p_hat = (panel["resp"] > threshold).sum() / len(panel)
    assert p_hat == pytest.approx(float(expected_p_hat))
    assert n_exc == (panel["resp"] > threshold).sum()
    assert n_total == 1000
    assert ci_low <= p_hat <= ci_high


def test_exceedance_probability_zero_exceedances_returns_p_hat_zero():
    """When no observation exceeds the threshold, p_hat=0; CI lower=0; CI upper is Wilson exact."""
    panel = pd.DataFrame({
        "z": np.arange(100),
        "resp": np.zeros(100),  # nothing exceeds threshold > 0
    })
    mask = np.ones(100, dtype=bool)

    p_hat, n_exc, n_total, ci_low, ci_high = compute_exceedance_probability_with_ci(
        panel, response_col="resp", threshold=100.0, z_bin_mask=mask, n_boot=50, seed=0
    )

    assert p_hat == 0.0
    assert n_exc == 0
    assert n_total == 100
    assert ci_low == 0.0
    # Wilson exact upper bound for (0, 100) at alpha=0.05 is ~0.036
    assert 0.0 < ci_high < 0.10


def test_exceedance_probability_ci_includes_point_estimate():
    """For a normal-power bin, the 95% CI should bracket the point estimate."""
    rng = np.random.default_rng(seed=7)
    panel = pd.DataFrame({
        "z": rng.uniform(0, 1, size=500),
        "resp": rng.exponential(scale=50, size=500),
    })
    mask = np.ones(500, dtype=bool)
    threshold = 50.0

    p_hat, _, _, ci_low, ci_high = compute_exceedance_probability_with_ci(
        panel, response_col="resp", threshold=threshold, z_bin_mask=mask, n_boot=200, seed=11
    )

    assert ci_low <= p_hat <= ci_high
    assert ci_high - ci_low < 0.15  # for n=500, CI width should be reasonable
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 3 new FAIL with `cannot import name 'compute_exceedance_probability_with_ci'`.

- [ ] **Step 3: Implement the function**

Append to `src/surg/analysis/tail_risk_curves.py`:
```python
def compute_exceedance_probability_with_ci(
    panel: pd.DataFrame,
    *,
    response_col: str,
    threshold: float,
    z_bin_mask: np.ndarray,
    n_boot: int = 200,
    seed: int = 0,
) -> tuple[float, int, int, float, float]:
    """Pair-bootstrap CI for P(response > threshold | row in z_bin_mask).

    Returns
    -------
    p_hat : float
        Empirical exceedance probability in the bin.
    n_exc : int
        Number of exceedances.
    n_total : int
        Total rows in the bin.
    ci_low : float
        Bootstrap 95% CI lower bound. ``0.0`` if ``n_exc == 0``.
    ci_high : float
        Bootstrap 95% CI upper bound. Wilson exact upper for ``n_exc == 0``
        case (bootstrap is degenerate when all reps yield 0/n).
    """
    bin_resp = panel.loc[z_bin_mask, response_col].dropna().to_numpy()
    n_total = int(bin_resp.size)
    if n_total == 0:
        return 0.0, 0, 0, 0.0, 0.0

    is_exc = (bin_resp > threshold).astype(np.int64)
    n_exc = int(is_exc.sum())
    p_hat = n_exc / n_total

    if n_exc == 0:
        # Bootstrap is degenerate (all reps yield 0); use Wilson upper bound.
        # Wilson upper for n_exc=0 at alpha=0.05: z = 1.96, p = 0
        # upper = (z^2) / (n + z^2)  =>  3.8416 / (n + 3.8416)
        z2 = 1.96**2
        ci_high = z2 / (n_total + z2)
        return p_hat, n_exc, n_total, 0.0, float(ci_high)

    if n_exc == n_total:
        # Symmetric Wilson treatment for the n_exc = n boundary.
        z2 = 1.96**2
        ci_low = n_total / (n_total + z2)
        return p_hat, n_exc, n_total, float(ci_low), 1.0

    # Pair-bootstrap: resample (z_bin_mask rows) with replacement.
    rng = np.random.default_rng(seed)
    boot_p = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        idx = rng.integers(0, n_total, size=n_total)
        boot_p[i] = is_exc[idx].mean()

    ci_low, ci_high = np.quantile(boot_p, [0.025, 0.975])
    return p_hat, n_exc, n_total, float(ci_low), float(ci_high)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 7 passed (4 from prior tasks + 3 new).

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "feat(analysis): tail_risk_curves — exceedance probability with pair-bootstrap CI (item #6)"
```

---

## Task 4: Per-pnode orchestrator

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py`
- Modify: `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/analysis/test_tail_risk_curves.py`:
```python
from surg.analysis.tail_risk_curves import run_pnode_tail_risk_curves


def test_run_pnode_tail_risk_curves_returns_full_schema():
    """Per-pnode orchestrator returns nested dict with all expected fields."""
    rng = np.random.default_rng(seed=3)
    n = 2000
    panel = pd.DataFrame({
        "z": rng.exponential(scale=2.0, size=n),
        "total_lmp_rt_cluster_mean": rng.lognormal(mean=3.5, sigma=1.0, size=n),
        "congestion_price_rt_cluster_mean": rng.exponential(scale=10.0, size=n),
    })

    result = run_pnode_tail_risk_curves(
        panel=panel,
        pnode_label="primary",
        response_cols={
            "total_lmp": "total_lmp_rt_cluster_mean",
            "congestion": "congestion_price_rt_cluster_mean",
        },
        z_col="z",
        thresholds=[50.0, 100.0],
        n_deciles=10,
        n_boot=20,
        seed=5,
    )

    assert result["pnode_label"] == "primary"
    assert result["z_col"] == "z"
    assert result["thresholds"] == [50.0, 100.0]
    assert result["n_boot"] == 20
    assert len(result["decile_edges_mw_per_min"]) == 11
    assert len(result["decile_n_obs"]) == 10
    assert "threshold_percentiles" in result
    assert "results" in result

    for resp_key in ("total_lmp", "congestion"):
        assert resp_key in result["results"]
        deciles = result["results"][resp_key]
        assert len(deciles) == 10
        for decile_entry in deciles:
            assert "decile" in decile_entry
            assert "z_range_mw_per_min" in decile_entry
            assert "n_total" in decile_entry
            assert "by_threshold" in decile_entry
            for t in (50.0, 100.0):
                cell = decile_entry["by_threshold"][t]
                assert "p_hat" in cell
                assert "n_exc" in cell
                assert "ci_95" in cell
                assert len(cell["ci_95"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v -k "run_pnode"
```
Expected: FAIL with `cannot import name 'run_pnode_tail_risk_curves'`.

- [ ] **Step 3: Implement the per-pnode orchestrator**

Append to `src/surg/analysis/tail_risk_curves.py`:
```python
def run_pnode_tail_risk_curves(
    panel: pd.DataFrame,
    *,
    pnode_label: str,
    response_cols: dict[str, str],
    z_col: str,
    thresholds: list[float],
    n_deciles: int = 10,
    n_boot: int = 200,
    seed: int = 0,
) -> dict:
    """Per-pnode orchestrator: compute the full P(response > threshold | z decile)
    table for two response variables (typically total_lmp + congestion).

    Returns a JSON-ready dict matching the design spec schema.
    """
    if n_deciles != 10:
        raise NotImplementedError(
            f"n_deciles={n_deciles} not supported; design fixes deciles=10"
        )

    edges, bin_indices = compute_z_deciles(panel, z_col)
    decile_n_obs = [int((bin_indices == d).sum()) for d in range(n_deciles)]

    threshold_pcts: dict[str, dict[float, float]] = {}
    for key, col in response_cols.items():
        threshold_pcts[key] = compute_threshold_percentiles(panel, col, thresholds)

    results: dict[str, list[dict]] = {key: [] for key in response_cols}
    for resp_key, resp_col in response_cols.items():
        for d in range(n_deciles):
            mask = bin_indices == d
            decile_entry: dict = {
                "decile": d + 1,  # 1-indexed for display
                "z_range_mw_per_min": [float(edges[d]), float(edges[d + 1])],
                "n_total": decile_n_obs[d],
                "by_threshold": {},
            }
            for t in thresholds:
                p_hat, n_exc, n_total, lo, hi = compute_exceedance_probability_with_ci(
                    panel,
                    response_col=resp_col,
                    threshold=t,
                    z_bin_mask=mask,
                    n_boot=n_boot,
                    seed=seed + d * 1000 + int(t),
                )
                decile_entry["by_threshold"][float(t)] = {
                    "p_hat": p_hat,
                    "n_exc": n_exc,
                    "ci_95": [lo, hi],
                }
                _ = n_total  # already in decile_entry
            results[resp_key].append(decile_entry)

    return {
        "pnode_label": pnode_label,
        "response_cols": response_cols,
        "z_col": z_col,
        "thresholds": [float(t) for t in thresholds],
        "n_boot": n_boot,
        "n_total_filtered": int(len(panel)),
        "decile_edges_mw_per_min": [float(e) for e in edges],
        "decile_n_obs": decile_n_obs,
        "threshold_percentiles": threshold_pcts,
        "results": results,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 8 passed (7 prior + 1 new).

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "feat(analysis): tail_risk_curves — per-pnode orchestrator (item #6)"
```

---

## Task 5: Cross-pnode summary aggregator

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py`
- Modify: `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/analysis/test_tail_risk_curves.py`:
```python
from surg.analysis.tail_risk_curves import aggregate_cross_pnode_summary


def test_aggregate_cross_pnode_summary_extracts_top_decile():
    """Given 2 fake per-pnode results, summary picks top-decile entries per (response, threshold)."""
    per_pnode = [
        {
            "pnode_label": "primary",
            "thresholds": [100.0, 500.0],
            "decile_edges_mw_per_min": [0.0] + [float(i) for i in range(1, 11)],  # 11 edges
            "decile_n_obs": [100] * 10,
            "results": {
                "total_lmp": [
                    {
                        "decile": d + 1,
                        "z_range_mw_per_min": [d * 1.0, (d + 1) * 1.0],
                        "n_total": 100,
                        "by_threshold": {
                            100.0: {"p_hat": 0.01 * d, "n_exc": d, "ci_95": [0.0, 0.02 * d]},
                            500.0: {"p_hat": 0.005 * d, "n_exc": d // 2, "ci_95": [0.0, 0.01 * d]},
                        },
                    }
                    for d in range(10)
                ],
                "congestion": [
                    {
                        "decile": d + 1,
                        "z_range_mw_per_min": [d * 1.0, (d + 1) * 1.0],
                        "n_total": 100,
                        "by_threshold": {
                            100.0: {"p_hat": 0.02 * d, "n_exc": 2 * d, "ci_95": [0.0, 0.04 * d]},
                            500.0: {"p_hat": 0.01 * d, "n_exc": d, "ci_95": [0.0, 0.02 * d]},
                        },
                    }
                    for d in range(10)
                ],
            },
        },
        {
            "pnode_label": "dom_zonal",
            "thresholds": [100.0, 500.0],
            "decile_edges_mw_per_min": [0.0] + [float(i) for i in range(1, 11)],
            "decile_n_obs": [100] * 10,
            "results": {
                "total_lmp": [
                    {
                        "decile": d + 1,
                        "z_range_mw_per_min": [d * 1.0, (d + 1) * 1.0],
                        "n_total": 100,
                        "by_threshold": {
                            100.0: {"p_hat": 0.005 * d, "n_exc": d, "ci_95": [0.0, 0.01 * d]},
                            500.0: {"p_hat": 0.002 * d, "n_exc": d // 3, "ci_95": [0.0, 0.005 * d]},
                        },
                    }
                    for d in range(10)
                ],
                "congestion": [
                    {
                        "decile": d + 1,
                        "z_range_mw_per_min": [d * 1.0, (d + 1) * 1.0],
                        "n_total": 100,
                        "by_threshold": {
                            100.0: {"p_hat": 0.01 * d, "n_exc": d, "ci_95": [0.0, 0.02 * d]},
                            500.0: {"p_hat": 0.005 * d, "n_exc": d // 2, "ci_95": [0.0, 0.01 * d]},
                        },
                    }
                    for d in range(10)
                ],
            },
        },
    ]

    summary = aggregate_cross_pnode_summary(per_pnode)

    assert summary["scope"] == "top_decile_only"
    assert summary["thresholds"] == [100.0, 500.0]
    assert len(summary["pnodes"]) == 2

    primary_entry = next(p for p in summary["pnodes"] if p["pnode_label"] == "primary")
    # Top decile (d=9) values: 0.01 * 9 = 0.09 (total_lmp @ 100)
    assert primary_entry["results"]["total_lmp"][100.0]["p_hat"] == pytest.approx(0.09)
    assert primary_entry["results"]["total_lmp"][500.0]["p_hat"] == pytest.approx(0.045)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v -k "cross_pnode"
```
Expected: FAIL with `cannot import name 'aggregate_cross_pnode_summary'`.

- [ ] **Step 3: Implement the aggregator**

Append to `src/surg/analysis/tail_risk_curves.py`:
```python
def aggregate_cross_pnode_summary(per_pnode_results: list[dict]) -> dict:
    """Extract top-decile-only summary across all per-pnode results.

    Output schema per design spec: ``{n_boot, thresholds, scope, pnodes: [...]}``.
    Each pnode entry has top-decile p_hat + CI per (response, threshold).
    """
    if not per_pnode_results:
        return {"scope": "top_decile_only", "thresholds": [], "pnodes": []}

    thresholds = per_pnode_results[0]["thresholds"]
    n_boot = per_pnode_results[0].get("n_boot")

    pnodes_out: list[dict] = []
    for entry in per_pnode_results:
        # Top decile is the last one (decile=10, 0-indexed 9)
        top_decile_by_resp: dict[str, dict[float, dict]] = {}
        for resp_key, deciles in entry["results"].items():
            top = deciles[-1]  # 10th decile
            top_decile_by_resp[resp_key] = {
                t: {
                    "p_hat": top["by_threshold"][t]["p_hat"],
                    "ci_95": top["by_threshold"][t]["ci_95"],
                }
                for t in thresholds
            }

        pnodes_out.append({
            "pnode_label": entry["pnode_label"],
            "z_range_top_decile_mw_per_min": [
                float(entry["decile_edges_mw_per_min"][-2]),
                float(entry["decile_edges_mw_per_min"][-1]),
            ],
            "n_top_decile": int(entry["decile_n_obs"][-1]),
            "results": top_decile_by_resp,
        })

    return {
        "n_boot": n_boot,
        "thresholds": thresholds,
        "scope": "top_decile_only",
        "pnodes": pnodes_out,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "feat(analysis): tail_risk_curves — cross-pnode summary aggregator (item #6)"
```

---

## Task 6: Plotting (matplotlib visualization)

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py`
- Modify: `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Write the smoke test**

Append to `tests/analysis/test_tail_risk_curves.py`:
```python
from pathlib import Path

from surg.analysis.tail_risk_curves import plot_tail_risk_curves


def test_plot_tail_risk_curves_writes_png(tmp_path):
    """Plot smoke test: given a per-pnode result dict, writes a non-empty PNG."""
    rng = np.random.default_rng(seed=99)
    n = 1000
    panel = pd.DataFrame({
        "z": rng.exponential(scale=1.0, size=n),
        "total_lmp_rt_cluster_mean": rng.lognormal(mean=3.5, sigma=1.0, size=n),
        "congestion_price_rt_cluster_mean": rng.exponential(scale=10.0, size=n),
    })
    per_pnode = run_pnode_tail_risk_curves(
        panel=panel,
        pnode_label="test_pnode",
        response_cols={
            "total_lmp": "total_lmp_rt_cluster_mean",
            "congestion": "congestion_price_rt_cluster_mean",
        },
        z_col="z",
        thresholds=[10.0, 50.0, 100.0],
        n_boot=20,
        seed=11,
    )

    out_path = tmp_path / "test_plot.png"
    plot_tail_risk_curves(per_pnode, out_path)

    assert out_path.exists()
    assert out_path.stat().st_size > 5_000  # non-trivial PNG
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v -k "plot"
```
Expected: FAIL with `cannot import name 'plot_tail_risk_curves'`.

- [ ] **Step 3: Implement the plotting function**

Append to `src/surg/analysis/tail_risk_curves.py`:
```python
from pathlib import Path


def plot_tail_risk_curves(per_pnode: dict, out_path: Path) -> None:
    """2-panel chart: P(LMP > $X | Z decile) for total_lmp + congestion.

    X-axis: decile index 1-10 with MW/min edge labels.
    Y-axis: exceedance probability with bootstrap 95% CI ribbon.
    Lines: one per $-threshold, colored by viridis.
    """
    # Local import to avoid loading matplotlib at module import time
    import matplotlib
    matplotlib.use("Agg")  # non-interactive backend for headless runs
    import matplotlib.pyplot as plt
    from matplotlib.cm import viridis

    pnode_label = per_pnode["pnode_label"]
    thresholds = per_pnode["thresholds"]
    edges = per_pnode["decile_edges_mw_per_min"]
    threshold_pcts = per_pnode["threshold_percentiles"]

    decile_centers = list(range(1, 11))
    xtick_labels = [
        f"{d}\n[{edges[d-1]:.1f},\n{edges[d]:.1f}]"
        for d in decile_centers
    ]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    for ax, resp_key in zip(axes, ("total_lmp", "congestion")):
        deciles = per_pnode["results"][resp_key]
        n_thresh = len(thresholds)
        for i, t in enumerate(thresholds):
            ps = [d["by_threshold"][t]["p_hat"] for d in deciles]
            lo = [d["by_threshold"][t]["ci_95"][0] for d in deciles]
            hi = [d["by_threshold"][t]["ci_95"][1] for d in deciles]
            color = viridis(i / max(1, n_thresh - 1))
            pct = threshold_pcts.get(resp_key, {}).get(t, None)
            label = (
                f"${int(t)} (p{pct*100:.1f})" if pct is not None else f"${int(t)}"
            )
            ax.plot(
                decile_centers, ps,
                color=color, linewidth=1 + i * 0.4, marker="o", label=label,
            )
            ax.fill_between(decile_centers, lo, hi, color=color, alpha=0.15)

        ax.set_title(f"{resp_key}")
        ax.set_xlabel("Z decile (MW/min range)")
        ax.set_xticks(decile_centers)
        ax.set_xticklabels(xtick_labels, fontsize=8)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.legend(title="threshold $ (pct)", loc="upper left", fontsize=8)

    axes[0].set_ylabel("P(LMP > $threshold)")
    fig.suptitle(
        f"{pnode_label}: P(LMP > $X) by Z decile "
        f"(proposal-filter, n_boot={per_pnode['n_boot']}, hourly)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "feat(analysis): tail_risk_curves — matplotlib 2-panel plotting (item #6)"
```

---

## Task 7: Top-level orchestrator (writes outputs/)

**Files:**
- Modify: `src/surg/analysis/tail_risk_curves.py`
- Modify: `tests/analysis/test_tail_risk_curves.py`

- [ ] **Step 1: Write the integration smoke test**

Append to `tests/analysis/test_tail_risk_curves.py`:
```python
import json

from surg.analysis.tail_risk_curves import run_tail_risk_curves


def _make_synthetic_panel(n: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Synthetic panel covering the 7 pnodes + filter column."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"dom_load_gradient_abs_mw_per_min": rng.exponential(scale=2.0, size=n)})
    df["passes_proposal_filter"] = True
    for pnode in ("cluster_mean", "ox", "bristers", "dom_zonal", "ashburn_tx1", "ashburn_tx2"):
        df[f"total_lmp_rt_{pnode}"] = rng.lognormal(mean=3.5, sigma=1.0, size=n)
        df[f"congestion_price_rt_{pnode}"] = rng.exponential(scale=10.0, size=n)
    return df


def test_run_tail_risk_curves_writes_all_expected_outputs(tmp_path):
    """End-to-end: run_tail_risk_curves writes 5 JSONs + 4 PNGs + 1 CSV under out_root."""
    panel = _make_synthetic_panel(n=2000, seed=0)
    out_root = tmp_path / "outputs"
    out_root.mkdir()

    run_tail_risk_curves(
        panel=panel,
        out_root=out_root,
        n_boot=5,
        seed=0,
    )

    tr_dir = out_root / "tail_risk_curves"
    assert tr_dir.exists()

    expected_jsons = [
        "primary.json",
        "dom_zonal.json",
        "ashburn_tx1.json",
        "ashburn_tx2.json",
        "cross_pnode_summary.json",
    ]
    for name in expected_jsons:
        assert (tr_dir / name).exists(), f"missing {name}"

    expected_pngs = [
        "primary.png",
        "dom_zonal.png",
        "ashburn_tx1.png",
        "ashburn_tx2.png",
    ]
    for name in expected_pngs:
        assert (tr_dir / name).exists(), f"missing {name}"
        assert (tr_dir / name).stat().st_size > 5_000

    assert (tr_dir / "cross_pnode_summary.csv").exists()

    # Sanity-check the primary JSON structure
    with open(tr_dir / "primary.json") as f:
        primary = json.load(f)
    assert primary["pnode_label"] == "primary"
    assert "decile_edges_mw_per_min" in primary
    assert "results" in primary
    assert "total_lmp" in primary["results"]
    assert "congestion" in primary["results"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v -k "run_tail_risk_curves_writes"
```
Expected: FAIL with `cannot import name 'run_tail_risk_curves'`.

- [ ] **Step 3: Implement the top-level orchestrator**

Append to `src/surg/analysis/tail_risk_curves.py`:
```python
import json
import csv

# Constants from the design spec
DEFAULT_THRESHOLDS = [100.0, 250.0, 500.0, 1000.0, 2000.0]
Z_COL = "dom_load_gradient_abs_mw_per_min"
FILTER_COL = "passes_proposal_filter"
PNODE_TO_RESPONSE: dict[str, dict[str, str]] = {
    "primary": {
        "total_lmp": "total_lmp_rt_cluster_mean",
        "congestion": "congestion_price_rt_cluster_mean",
    },
    "dom_zonal": {
        "total_lmp": "total_lmp_rt_dom_zonal",
        "congestion": "congestion_price_rt_dom_zonal",
    },
    "ashburn_tx1": {
        "total_lmp": "total_lmp_rt_ashburn_tx1",
        "congestion": "congestion_price_rt_ashburn_tx1",
    },
    "ashburn_tx2": {
        "total_lmp": "total_lmp_rt_ashburn_tx2",
        "congestion": "congestion_price_rt_ashburn_tx2",
    },
    # Cross-pnode summary table includes more pnodes (read-only here)
    "ox": {
        "total_lmp": "total_lmp_rt_ox",
        "congestion": "congestion_price_rt_ox",
    },
    "bristers": {
        "total_lmp": "total_lmp_rt_bristers",
        "congestion": "congestion_price_rt_bristers",
    },
    "total_lmp": {  # total_lmp pnode alias to cluster_mean total_lmp
        "total_lmp": "total_lmp_rt_cluster_mean",
        "congestion": "congestion_price_rt_cluster_mean",
    },
}
PER_PNODE_PLOTTED = ("primary", "dom_zonal", "ashburn_tx1", "ashburn_tx2")
CROSS_PNODE_PNODES = (
    "primary", "total_lmp", "ox", "bristers",
    "dom_zonal", "ashburn_tx1", "ashburn_tx2",
)


def run_tail_risk_curves(
    panel: pd.DataFrame,
    *,
    out_root: Path,
    thresholds: list[float] | None = None,
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """Top-level orchestrator: applies the proposal-filter, runs all
    per-pnode + cross-pnode analyses, writes outputs to disk.

    Writes 5 JSONs + 4 PNGs + 1 CSV under ``out_root/tail_risk_curves/``.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

    tr_dir = Path(out_root) / "tail_risk_curves"
    tr_dir.mkdir(parents=True, exist_ok=True)

    filtered = panel.loc[panel[FILTER_COL] == True].copy()

    all_results: list[dict] = []

    # Per-pnode pass (cross-pnode set includes all 7 pnodes; only 4 get plots)
    for pnode_label in CROSS_PNODE_PNODES:
        response_cols = PNODE_TO_RESPONSE[pnode_label]
        # Drop NA rows in either response column for this pnode
        cols = list(response_cols.values()) + [Z_COL]
        sub = filtered.dropna(subset=cols)

        result = run_pnode_tail_risk_curves(
            panel=sub,
            pnode_label=pnode_label,
            response_cols=response_cols,
            z_col=Z_COL,
            thresholds=thresholds,
            n_deciles=10,
            n_boot=n_boot,
            seed=seed,
        )
        all_results.append(result)

        if pnode_label in PER_PNODE_PLOTTED:
            # Write per-pnode JSON
            with open(tr_dir / f"{pnode_label}.json", "w") as f:
                json.dump(_json_serializable(result), f, indent=2)
            # Write per-pnode PNG
            plot_tail_risk_curves(result, tr_dir / f"{pnode_label}.png")

    # Cross-pnode summary
    summary = aggregate_cross_pnode_summary(all_results)
    with open(tr_dir / "cross_pnode_summary.json", "w") as f:
        json.dump(_json_serializable(summary), f, indent=2)

    # Cross-pnode summary CSV
    _write_cross_pnode_csv(summary, tr_dir / "cross_pnode_summary.csv")


def _json_serializable(obj):
    """Convert numeric dict keys to strings (JSON requires) and recurse."""
    if isinstance(obj, dict):
        return {str(k): _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_serializable(v) for v in obj]
    return obj


def _write_cross_pnode_csv(summary: dict, out_path: Path) -> None:
    """Write the top-decile cross-pnode summary as a wide CSV.

    Rows = pnodes; columns = (response_var, threshold) pairs with p_hat.
    """
    thresholds = summary["thresholds"]
    response_vars = ("total_lmp", "congestion")
    header = ["pnode_label", "z_range_top_decile_low_mw_per_min", "z_range_top_decile_high_mw_per_min", "n_top_decile"]
    for r in response_vars:
        for t in thresholds:
            header.append(f"{r}_p_hat_at_{int(t)}")

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for p in summary["pnodes"]:
            row = [
                p["pnode_label"],
                p["z_range_top_decile_mw_per_min"][0],
                p["z_range_top_decile_mw_per_min"][1],
                p["n_top_decile"],
            ]
            for r in response_vars:
                for t in thresholds:
                    row.append(p["results"][r][t]["p_hat"])
            w.writerow(row)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_tail_risk_curves.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add src/surg/analysis/tail_risk_curves.py tests/analysis/test_tail_risk_curves.py
git commit -m "feat(analysis): tail_risk_curves — top-level orchestrator + CSV writer (item #6)"
```

---

## Task 8: Wire into run.py orchestrator + CLI flags

**Files:**
- Modify: `src/surg/analysis/run.py`
- Modify: `tests/analysis/test_run.py`

- [ ] **Step 1: Read existing run.py to understand integration pattern**

Inspect how `run_ashburn_diagnostic` is wired:
```bash
grep -n "run_ashburn_diagnostic\|--skip-ashburn-diagnostic\|--ashburn-loo-skip" src/surg/analysis/run.py
```
Note the integration pattern (import, argparse flag, skip-check, orchestrator call).

- [ ] **Step 2: Write the failing integration test**

Modify `tests/analysis/test_run.py` (append to existing test or add a new one):
```python
def test_run_all_writes_tail_risk_curves_outputs(tmp_path, sample_panel_with_filter):
    """Smoke test: run_all writes the expected outputs/tail_risk_curves/ files."""
    from surg.analysis.run import run_all

    out_root = tmp_path / "outputs"
    out_root.mkdir()

    run_all(
        panel_path=sample_panel_with_filter,
        data_root=tmp_path / "data_raw",
        out_root=out_root,
        n_boot=5,
        qr_full_n_boot=5,
        gpd_n_boot=5,
        continuous_n_boot=5,
        components_n_boot=5,
        year_fe_n_boot=5,
        tail_risk_n_boot=5,  # NEW
    )

    tr_dir = out_root / "tail_risk_curves"
    assert (tr_dir / "primary.json").exists()
    assert (tr_dir / "cross_pnode_summary.json").exists()
    assert (tr_dir / "primary.png").exists()
```

Note: this test depends on an existing `sample_panel_with_filter` fixture in `tests/analysis/test_run.py`. If the existing fixture is named differently, adapt the call signature accordingly. Use `grep -n "@pytest.fixture" tests/analysis/test_run.py` to identify the actual fixture name first.

- [ ] **Step 3: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v -k "tail_risk_curves"
```
Expected: FAIL with `unexpected keyword argument 'tail_risk_n_boot'`.

- [ ] **Step 4: Add the import + CLI flag + orchestrator call in run.py**

Modify `src/surg/analysis/run.py`. Specifically:

(a) Add import near other analysis-module imports:
```python
from surg.analysis.tail_risk_curves import run_tail_risk_curves
```

(b) Add the argparse flags in the CLI section (next to the other `--*-n-boot` and `--skip-*` flags):
```python
    parser.add_argument(
        "--tail-risk-n-boot",
        type=int,
        default=200,
        help="Bootstrap reps for sub-q1 item #6 (tail_risk_curves) CIs.",
    )
    parser.add_argument(
        "--skip-tail-risk-curves",
        action="store_true",
        help="Skip sub-q1 item #6 (tail_risk_curves) orchestrator.",
    )
    parser.add_argument(
        "--tail-risk-loo-skip",
        action="store_true",
        help="Soft idempotency: skip tail_risk_curves if output already exists.",
    )
```

(c) Add the `tail_risk_n_boot` parameter to `run_all`'s signature and orchestrator call. Find the existing `run_all` signature (it'll have parameters like `n_boot`, `qr_full_n_boot`, etc.); add `tail_risk_n_boot: int = 200` and `skip_tail_risk_curves: bool = False` and `tail_risk_loo_skip: bool = False` to the parameter list.

(d) Inside `run_all`, after the `run_ashburn_diagnostic` call, add:
```python
    if not skip_tail_risk_curves:
        if tail_risk_loo_skip and (out_root / "tail_risk_curves" / "primary.json").exists():
            print("tail_risk_curves outputs exist; skipping (--tail-risk-loo-skip).")
        else:
            print("Running tail_risk_curves (sub-q1 item #6)...")
            run_tail_risk_curves(
                panel=panel,
                out_root=out_root,
                n_boot=tail_risk_n_boot,
                seed=seed if 'seed' in locals() else 0,
            )
```

(e) Wire `args.tail_risk_n_boot` / `args.skip_tail_risk_curves` / `args.tail_risk_loo_skip` into the `run_all(...)` call at the CLI entry point.

- [ ] **Step 5: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v
```
Expected: all tests pass including the new tail_risk_curves smoke.

- [ ] **Step 6: Run the full test suite to confirm no regressions**

```bash
.venv/bin/pytest -q
```
Expected: 251 passed (240 baseline + 11 new from this module).

- [ ] **Step 7: Commit**

```bash
git add src/surg/analysis/run.py tests/analysis/test_run.py
git commit -m "feat(analysis): wire tail_risk_curves into run_all + CLI flags (item #6)"
```

---

## Task 9: Production run

**Files:**
- Generates: `outputs/tail_risk_curves/` contents

- [ ] **Step 1: Verify the panel exists**

From the worktree:
```bash
ls -lh data/interim/analysis_panel.parquet 2>/dev/null || ls -lh ../surg/data/interim/analysis_panel.parquet
```
Expected: file present and ~6 MB. If only present in the main worktree, that's expected — use `--panel ../surg/data/interim/analysis_panel.parquet` in Step 2.

- [ ] **Step 2: Run `surg-analyze` with full coverage**

Run from the item-6 worktree:
```bash
.venv/bin/surg-analyze \
  --panel ../surg/data/interim/analysis_panel.parquet \
  --data-root ../surg/data/raw \
  --out-root outputs \
  --n-boot 1000 \
  --qr-full-n-boot 200 \
  --gpd-n-boot 200 \
  --continuous-n-boot 200 \
  --components-n-boot 200 \
  --year-fe-n-boot 200 \
  --tail-risk-n-boot 200 \
  --skip-gpd-components \
  --skip-year-fe-diagnostic \
  --skip-ashburn-diagnostic
```

Note: items #2-#4 outputs were already produced in the prior production run and are unchanged by this work. The `--skip-*-diagnostic` flags above bypass them to keep this run focused on item #6 only. Wall time estimate: <5 minutes.

Expected: completes without errors. `outputs/tail_risk_curves/` directory created with 10 files (5 JSONs + 4 PNGs + 1 CSV).

- [ ] **Step 3: Verify all expected outputs exist**

```bash
ls -lh outputs/tail_risk_curves/
```
Expected:
- 5 JSONs: `primary.json`, `dom_zonal.json`, `ashburn_tx1.json`, `ashburn_tx2.json`, `cross_pnode_summary.json`
- 4 PNGs: `primary.png`, `dom_zonal.png`, `ashburn_tx1.png`, `ashburn_tx2.png`
- 1 CSV: `cross_pnode_summary.csv`

- [ ] **Step 4: Inspect the primary headline**

```bash
.venv/bin/python -c "
import json
with open('outputs/tail_risk_curves/primary.json') as f:
    d = json.load(f)
print('decile edges (MW/min):', [round(e, 2) for e in d['decile_edges_mw_per_min']])
print('threshold percentiles (total_lmp):', d['threshold_percentiles']['total_lmp'])
print()
print('Top-decile P(total_lmp > thresholds):')
top = d['results']['total_lmp'][-1]
for t, cell in top['by_threshold'].items():
    print(f'  > \${t}: p_hat={cell[\"p_hat\"]:.3f}, CI={cell[\"ci_95\"]}, n_exc={cell[\"n_exc\"]}')
"
```

- [ ] **Step 5: No commit (outputs/ is gitignored)**

```bash
git status
```
Expected: no untracked changes (outputs/ is in `.gitignore`).

---

## Task 10: Application entry in decisions.md

**Files:**
- Modify: `docs/decisions.md`

- [ ] **Step 1: Read the production headline values**

Run from the worktree:
```bash
.venv/bin/python -c "
import json
for name in ['primary', 'dom_zonal', 'ashburn_tx1', 'ashburn_tx2']:
    with open(f'outputs/tail_risk_curves/{name}.json') as f:
        d = json.load(f)
    print(f'=== {name} ===')
    print(f'n_total_filtered: {d[\"n_total_filtered\"]}')
    print(f'decile edges: {[round(e, 2) for e in d[\"decile_edges_mw_per_min\"]]}')
    print(f'threshold percentiles (total_lmp): {d[\"threshold_percentiles\"][\"total_lmp\"]}')
    print('Top-decile total_lmp:')
    for t, cell in d['results']['total_lmp'][-1]['by_threshold'].items():
        print(f'  > \${t}: p_hat={cell[\"p_hat\"]:.3f}, CI=[{cell[\"ci_95\"][0]:.3f}, {cell[\"ci_95\"][1]:.3f}], n_exc={cell[\"n_exc\"]}')
    print()
"
```

- [ ] **Step 2: Read the cross-pnode summary CSV**

```bash
column -t -s, outputs/tail_risk_curves/cross_pnode_summary.csv | head
```

- [ ] **Step 3: Append the application entry to `docs/decisions.md`**

Append a new section after the last existing entry in `docs/decisions.md`. Title:
```markdown
## 2026-05-XX — Sub-q1 item #6: Direct Z → LMP tail-risk characterization (descriptive)
```

Body (template — substitute `<...>` with actual production values):

```markdown
**Context.** Item #6 produces the direct descriptive answer to the
user's sub-q1 framing — *"what range of load variance causes LMP to
essentially go crazy"* — via binned exceedance-probability
characterization. Design spec at
`docs/plans/2026-05-14-z-lmp-tail-risk-characterization-design.md`
(committed `6c7ebbb`).

Items #1-4 (mechanism work) stay as supporting evidence; this entry
adds the descriptive *where*.

**Production-run config.**
- Code: `feature/sub-q1-item-6-tail-risk-curves` worktree
  (FF-merged after this entry). N tests passing.
- Filter: proposal-filter (shoulder-season + 2-5 AM) → n_total_filtered = <n>.
- Pair-bootstrap n_boot=200 for all CIs.
- 4 per-pnode JSONs (primary, dom_zonal, ashburn_tx1, ashburn_tx2)
  with 10 Z deciles × 5 $-thresholds × 2 response vars
  (total_lmp + congestion). Cross-pnode summary covers all 7 pnodes
  at top decile only.

### Z decile structure (primary cluster)

| Decile | Z range (MW/min) | n_obs |
|---|---|---|
| 1 | [<lo>, <hi>] | <n> |
| ... | ... | ... |
| 10 | [<lo>, <hi>] | <n> |

Threshold percentiles in the filtered panel:

| $ threshold | total_lmp pct | congestion pct |
|---|---|---|
| 100 | <pct> | <pct> |
| 250 | <pct> | <pct> |
| 500 | <pct> | <pct> |
| 1000 | <pct> | <pct> |
| 2000 | <pct> | <pct> |

### Top-decile exceedance probabilities (Z ∈ [<lo>, <hi>] MW/min)

| Threshold | total_lmp P [CI] | congestion P [CI] |
|---|---|---|
| $100 | <p> [<ci>] | <p> [<ci>] |
| ... | ... | ... |
| $2000 | <p> [<ci>] | <p> [<ci>] |

### Crazy-region characterization

<Describe the qualitative pattern. E.g.:
- At what decile does P(total_lmp > $500) cross 10%? 25%?
- Is the curve smooth or does it have a visible knee?
- How does congestion compare to total_lmp?>

### Cross-pnode top-decile comparison

See `outputs/tail_risk_curves/cross_pnode_summary.csv`. Notable observations:

<List which pnodes have qualitatively similar vs different top-decile
behavior. Anchor to the items #1-4 findings — e.g., does Ashburn TX1
look different in the descriptive view too?>

### Implication for the paper

<One paragraph. Possible framings:
- The chart IS the headline answer to sub-q1 (if a clear "crazy region"
  emerges).
- The chart shows a smooth gradient with no clean cutoff (consistent
  with smooth-curve diagnosis); item #6 confirms there's no single
  threshold but characterizes the smooth response.>

### Implication for sub-q2 (JLARC projection)

<Specifically: what does the top-decile P(LMP > $X) curve imply about
future projections as data-center growth shifts Z's distribution toward
the right? E.g., "if 2030 growth shifts ~30% of observations from
deciles 5-7 up to deciles 8-10, expected P(LMP > $500) increases from
X% to Y%.">

### Revisit when

- Advisor meeting (item #5) framing decisions.
- Item #7 (5-min data exploration) surfaces qualitatively different
  patterns at sub-hourly resolution.
- Sub-q2 (JLARC projection) implementation needs the top-decile
  curves as projection inputs.
```

- [ ] **Step 4: Commit the application entry**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): apply Z -> LMP tail-risk characterization (sub-q1 item #6)"
```

Note: JSON outputs and PNG remain gitignored per project convention; the application entry quotes the numbers in prose so the entry is self-contained.

---

## Task 11: Update sub-q1 closure roadmap

**Files:**
- Modify: `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`

- [ ] **Step 1: Update the closure-status summary at the top of the roadmap**

Edit `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`. Find the line:
```markdown
> - Item 6 — Direct Z → LMP tail-risk characterization: **added
>   2026-05-14 night** after the user clarified sub-q1 framing
```

Replace with:
```markdown
> - Item 6 — Direct Z → LMP tail-risk characterization: **DONE**
>   (commit `<TASK 10 SHA>`). <One-sentence summary of the verdict:
>   what range of Z makes LMP cross what thresholds with what
>   probability.>
```

- [ ] **Step 2: Update item #6's own section (replace the "Design pending brainstorm" status)**

Find the section `### 6. Direct Z → LMP tail-risk characterization`. Replace the status line and the design-decisions-pending list with the DONE summary:
```markdown
**Status:** Closed by `docs/decisions.md § 2026-05-XX — Sub-q1 item #6:
Direct Z → LMP tail-risk characterization` (commit `<TASK 10 SHA>`).

**Closure outcome.** <Brief summary of the production-run findings:
top-decile exceedance probabilities, qualitative pattern, comparison
across the 4 plotted pnodes.>

**Outputs produced:** 5 JSONs + 4 PNGs + 1 CSV under
`outputs/tail_risk_curves/` (gitignored, locally reproducible via
`surg-analyze --tail-risk-n-boot 200`).
```

- [ ] **Step 3: Update the sequencing diagram**

Find:
```markdown
                                ┌──── 3. τ=0.99 ✓ ────┐
1. Spec B ✓ ─→ 2. Components ✓ ─┤                     │── 6. Z-bin tail-risk ─→ 5. Advisor meeting ─→ paper-ready sub-q1
                                └──── 4. Ashburn ✓ ───┘
```

Replace with:
```markdown
                                ┌──── 3. τ=0.99 ✓ ────┐
1. Spec B ✓ ─→ 2. Components ✓ ─┤                     │── 6. Z-bin tail-risk ✓ ─→ 5. Advisor meeting ─→ paper-ready sub-q1
                                └──── 4. Ashburn ✓ ───┘
```

- [ ] **Step 4: Commit**

```bash
git add docs/plans/2026-05-14-sub-question-1-closure-roadmap.md
git commit -m "docs(plans): mark sub-q1 item #6 DONE with commit SHA"
```

---

## Task 12: FF merge + push + worktree cleanup

**Files:** none (git operations only)

> **Important — per project CLAUDE.md ("each commit/push is its own ask"):**
> the FF merge, the push, the worktree remove, and the branch delete
> are each a separate destructive/shared-state operation. The executor
> MUST request explicit user permission before each, even if the user
> generally approved the lifecycle at plan time. Steps below describe
> the commands; the executor pauses to ask between them.

- [ ] **Step 1: Verify clean working tree**

```bash
git status
```
Expected: `nothing to commit, working tree clean`.

- [ ] **Step 2: Verify final test count from worktree**

```bash
.venv/bin/pytest -q
```
Expected: 251 passed (240 baseline + 11 new).

- [ ] **Step 3: Switch to main worktree and FF merge**

```bash
cd ../surg
git checkout main
git merge --ff-only feature/sub-q1-item-6-tail-risk-curves
```
Expected: fast-forward merge (no merge commit). Main moves forward by the new commits from this work.

- [ ] **Step 4: Verify main worktree tests still pass**

```bash
.venv/bin/pytest -q 2>&1 | tail -3
```
Expected: 251 passed.

- [ ] **Step 5: Push main to origin**

```bash
git push origin main
```
Expected: successful push.

- [ ] **Step 6: Remove the sibling worktree**

```bash
git worktree remove ../surg-item-6-tail-risk
```
Expected: worktree removed cleanly.

- [ ] **Step 7: Delete the feature branch**

```bash
git branch -d feature/sub-q1-item-6-tail-risk-curves
```
Expected: branch deleted (fully merged).

- [ ] **Step 8: Final verification**

```bash
git worktree list
git branch -a
git log --oneline -5
```
Expected: only main worktree; only `main` and `remotes/origin/main` branches; recent commit log shows the item #6 work.
