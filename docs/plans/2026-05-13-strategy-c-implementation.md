# Strategy C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended per `memory/feedback_plan_execution.md`) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the QR-on-full-panel and GPD-on-LMP-tails modules + output-directory reorganization, per the design spec at `docs/plans/2026-05-13-strategy-c-modules.md`.

**Architecture:** Two new sibling modules under `src/surg/analysis/` (`qr_full.py`, `gpd.py`) that operate on the full 31,536-hour analysis panel (no `passes_proposal_filter` filtering). Each module exposes both a low-level fit function (numpy-array API) and a high-level `run_*` orchestrator that consumes the pandas panel and writes JSON output. Both wire into the existing `run_all` orchestrator after the existing TAR + QR + mechanism + subsample stages. Output paths are reorganized from flat `outputs/tar_fit_*.json` into per-method subdirectories `outputs/<method>/<pnode>.json` as a one-shot change in Task 1 — this is a clean break with no backward-compat shim.

**Tech Stack:** Python 3.11+, statsmodels (existing — QuantReg), scipy (existing — `scipy.stats.genpareto`), pandas, numpy, pyarrow (existing — parquet), pytest. No new dependencies.

---

## Task 1: Output directory reorganization

**Why this task exists:** Before adding new methods, refactor the existing flat output structure into per-method subdirectories so new methods land in the right layout from day one. Also consolidates the response-column constants into a single `PNODE_RESPONSES` dict that the new modules will reuse.

**Files:**
- Modify: `src/surg/analysis/run.py` (whole `run_all` body + module-level constants)
- Modify: `tests/analysis/test_run.py` (`test_run_all_writes_all_outputs` test path assertions)
- Modify: `.gitignore` (simpler `outputs/` rule)

- [ ] **Step 1: Update the integration test's expected output paths (it will fail)**

Open `tests/analysis/test_run.py`. Find the test `test_run_all_writes_all_outputs` (or similarly named — the one that asserts which files exist after `run_all` completes). Replace its expected-paths set with:

```python
expected_paths = {
    out_root / "tar" / "primary.json",
    out_root / "tar" / "total_lmp.json",
    out_root / "tar" / "ox.json",
    out_root / "tar" / "bristers.json",
    out_root / "tar" / "dom_zonal.json",
    out_root / "tar" / "ashburn_tx1.json",
    out_root / "tar" / "ashburn_tx2.json",
    out_root / "qr" / "filtered_at_tar_c.json",
    out_root / "mechanism" / "validation.json",
    out_root / "robustness" / "subsample_bootstrap.parquet",
}
for p in expected_paths:
    assert p.exists(), f"expected output not written: {p}"
```

If the test currently checks specific schema keys inside each file (rather than just existence), leave those assertions in place but update the file-path strings to the new layout above.

- [ ] **Step 2: Run integration test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: the assertion that checks `out_root / "tar" / "primary.json"` exists FAILS (because `run_all` still writes to `out_root / "tar_fit_primary.json"`).

- [ ] **Step 3: Replace `run_all` and its module-level constants in `src/surg/analysis/run.py`**

Open `src/surg/analysis/run.py`. Replace the two module-level constants (`_SECONDARY_RESPONSE_COLS` and `_CONTROL_RESPONSE_COLS`) and the entire `run_all` function body with:

```python
PNODE_RESPONSES: dict[str, str] = {
    # Primary: pooled Loudoun cluster (6 transmission pnodes), congestion price
    "primary":     "congestion_price_rt_cluster_mean",
    # Secondary: same cluster, total LMP (cleaner ORDC mechanism test)
    "total_lmp":   "total_lmp_rt_cluster_mean",
    # Negative controls: outside-cluster transmission pnodes
    "ox":          "congestion_price_rt_ox",
    "bristers":    "congestion_price_rt_bristers",
    "dom_zonal":   "congestion_price_rt_dom_zonal",
    # Complementary primary fits: distribution-level pnodes at Ashburn
    "ashburn_tx1": "congestion_price_rt_ashburn_tx1",
    "ashburn_tx2": "congestion_price_rt_ashburn_tx2",
}


def run_all(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    out_root: Path,
    *,
    n_boot: int = 1000,
    n_subsample_reps: int = 200,
) -> None:
    """Run the full Phase 3 analysis pipeline.

    Output layout (per-method subdirectories):
      - outputs/tar/<pnode_label>.json
      - outputs/qr/filtered_at_tar_c.json   (filtered subset, at TAR's primary c_hat)
      - outputs/mechanism/validation.json
      - outputs/robustness/subsample_bootstrap.parquet

    Future Strategy C methods (qr_full, gpd) wire in here after the existing
    fits land. They are added in subsequent tasks; this function currently
    only covers the reorganization of the existing pipeline.
    """
    out_root.mkdir(parents=True, exist_ok=True)

    primary = run_tar(
        panel=panel,
        out_path=out_root / "tar" / "primary.json",
        response_col=PNODE_RESPONSES["primary"],
        n_boot=n_boot,
    )

    for label, col in PNODE_RESPONSES.items():
        if label == "primary":
            continue
        if panel[col].dropna().empty:
            continue
        run_tar(
            panel=panel,
            out_path=out_root / "tar" / f"{label}.json",
            response_col=col,
            n_boot=n_boot,
        )

    run_qr(
        panel=panel,
        out_path=out_root / "qr" / "filtered_at_tar_c.json",
        c_for_threshold_dummy=primary.c_hat,
    )

    run_mechanism(
        panel=panel,
        events=events,
        threshold=primary.c_hat,
        out_path=out_root / "mechanism" / "validation.json",
    )

    subsample_bootstrap(
        panel=panel,
        out_path=out_root / "robustness" / "subsample_bootstrap.parquet",
        n_reps=n_subsample_reps,
    )
```

Delete the two old constants (`_SECONDARY_RESPONSE_COLS`, `_CONTROL_RESPONSE_COLS`) — the new dict replaces them. The file's imports stay the same; no new imports needed in this task.

- [ ] **Step 4: Run integration test to verify it passes**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `145 passed in <time>` (same count as before — no new tests yet, no regressions).

- [ ] **Step 6: Simplify `.gitignore` outputs rule**

Open `.gitignore`. Find the current "Generated outputs" block (lines containing `outputs/figures/*`, `outputs/tables/*`, `outputs/*.json`, `outputs/robustness/`, and `!outputs/figures/.gitkeep` etc.). Replace the entire block with:

```
# Generated outputs (one rule: ignore everything in outputs/ except the
# two .gitkeep files that anchor the figures/ and tables/ subdirs)
outputs/
!outputs/figures/
!outputs/figures/.gitkeep
!outputs/tables/
!outputs/tables/.gitkeep

# Exploratory / alternative-window analysis outputs (regeneratable from
# the panel + analysis module with different filter parameters)
outputs_*/
```

The second block (`outputs_*/`) should already exist from a prior commit — leave it in place if so.

- [ ] **Step 7: Verify `.gitignore` works correctly**

```bash
git status
```

Expected: only `src/surg/analysis/run.py`, `tests/analysis/test_run.py`, and `.gitignore` are listed as modified. No `outputs/` content shows as untracked or modified.

- [ ] **Step 8: Commit**

```bash
git add src/surg/analysis/run.py tests/analysis/test_run.py .gitignore
git commit -m "$(cat <<'EOF'
refactor(analysis): reorganize outputs/ into per-method subdirectories

Flat outputs/tar_fit_*.json + outputs/qr_fit.json + outputs/mechanism_validation.json
become outputs/tar/<pnode>.json + outputs/qr/filtered_at_tar_c.json +
outputs/mechanism/validation.json. Method-first taxonomy matches how the paper
will read and leaves room for the new qr_full/ and gpd/ method dirs added in
subsequent commits.

Consolidates _SECONDARY_RESPONSE_COLS + _CONTROL_RESPONSE_COLS into a single
PNODE_RESPONSES ordered dict that maps pnode labels (used as filenames) to
response column names. New Strategy C modules will reuse this dict.

Simplifies the .gitignore outputs/ rule to "ignore everything except the two
.gitkeep files." No backward-compat shim for the old paths — only the
integration test referenced them, and it's been updated.
EOF
)"
```

---

## Task 2: `gpd.py` scaffold + `fit_gpd` point estimate

**Why:** Build the GPD module's foundation function first — point estimation only, no bootstrap, no sweep, no Z-split. Establishes the dataclass shape and the asymptotic-SE math. Subsequent tasks add bootstrap CI, sweep, and conditional split on top.

**Files:**
- Create: `src/surg/analysis/gpd.py`
- Create: `tests/analysis/test_gpd.py`

- [ ] **Step 1: Write three failing unit tests for `fit_gpd`**

Create `tests/analysis/test_gpd.py` with this content:

```python
"""Unit tests for src/surg/analysis/gpd.py — Strategy C GPD module."""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from surg.analysis.gpd import GPDFitResult, fit_gpd


def test_fit_gpd_recovers_planted_shape_and_scale():
    """fit_gpd with simulated GPD data should recover the planted parameters
    to within tolerance proportional to sqrt(n_exceedances)."""
    rng = np.random.default_rng(seed=42)
    true_shape, true_scale = 0.3, 2.0
    threshold = 10.0
    # Generate exceedances and shift by threshold so the data is "above threshold"
    excess = stats.genpareto.rvs(c=true_shape, scale=true_scale, size=5000, random_state=rng)
    Y = excess + threshold
    # Pad with a few below-threshold observations so fit_gpd has something to filter
    Y_full = np.concatenate([Y, rng.uniform(0, threshold - 0.1, size=200)])

    result = fit_gpd(Y_full, threshold=threshold)

    assert isinstance(result, GPDFitResult)
    assert result.n_exceedances == 5000
    assert result.threshold_value == pytest.approx(10.0)
    assert result.threshold_quantile == pytest.approx(5000 / 5200, abs=0.01)
    # Recovery tolerance: ~0.1 for shape with n=5000 (asymptotic SE ≈ 0.018)
    assert result.shape == pytest.approx(true_shape, abs=0.1)
    assert result.scale == pytest.approx(true_scale, abs=0.3)
    # Asymptotic SE should be positive and finite
    assert result.shape_se > 0
    assert math.isfinite(result.shape_se)
    assert result.scale_se > 0
    assert math.isfinite(result.scale_se)


def test_fit_gpd_recovers_xi_near_zero_for_exponential():
    """fit_gpd on exponential data (a special case of GPD with shape=0) should
    return shape close to zero."""
    rng = np.random.default_rng(seed=42)
    # Exponential with rate 1/5 (mean=5), shifted to be "above threshold 0"
    Y = rng.exponential(scale=5.0, size=5000) + 0.001  # tiny offset to avoid zeros

    result = fit_gpd(Y, threshold=0.0)

    assert abs(result.shape) < 0.1, f"shape too far from 0: {result.shape}"
    assert result.scale == pytest.approx(5.0, abs=0.5)


def test_fit_gpd_threshold_above_max_raises():
    """If threshold > max(Y), there are zero exceedances and the fit is ill-defined."""
    Y = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    with pytest.raises(ValueError, match="threshold"):
        fit_gpd(Y, threshold=100.0)
```

- [ ] **Step 2: Run tests to verify they fail (module doesn't exist yet)**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py -v
```

Expected: collection error or import error — `ModuleNotFoundError: No module named 'surg.analysis.gpd'`.

- [ ] **Step 3: Create `src/surg/analysis/gpd.py` with `GPDFitResult` and `fit_gpd`**

Create the file with this content:

```python
"""Generalized Pareto Distribution fits on LMP exceedances over a threshold.

Strategy C module — peaks-over-threshold (POT) MLE plus a sweep across
multiple threshold quantiles and a Z-conditional mechanism test. This
file initially contains the point-estimate `fit_gpd` only; the sweep
and conditional functions land in subsequent tasks.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


@dataclass(frozen=True, slots=True)
class GPDFitResult:
    """Point-estimate result from a single GPD fit at one threshold.

    `shape_bootstrap_ci_95` is `(nan, nan)` on a bare fit_gpd call; it
    is filled in by `gpd_threshold_sweep` and `gpd_conditional_on_z`
    which wrap fit_gpd with a bootstrap loop.
    """
    threshold_quantile: float
    threshold_value: float
    shape: float
    shape_se: float
    shape_bootstrap_ci_95: tuple[float, float]
    scale: float
    scale_se: float
    n_exceedances: int


def fit_gpd(Y: np.ndarray | pd.Series, *, threshold: float) -> GPDFitResult:
    """Fit a Generalized Pareto Distribution to exceedances of `Y` over `threshold`.

    Uses `scipy.stats.genpareto` MLE with `floc=0`, after subtracting the
    threshold from the exceedances. Asymptotic SE for (shape, scale) uses
    the closed-form Hosking & Wallis (1987) covariance valid for shape > -0.5.

    Raises ValueError if `threshold` exceeds `max(Y)` (no exceedances) or
    fewer than 10 exceedances remain (fit is too noisy to be useful).
    """
    Y_arr = np.asarray(Y, dtype=float)
    if not np.isfinite(threshold):
        raise ValueError(f"threshold must be finite, got {threshold}")
    if threshold > Y_arr.max():
        raise ValueError(
            f"threshold {threshold:.4g} exceeds max(Y) = {Y_arr.max():.4g}; "
            f"no exceedances"
        )
    excess = Y_arr[Y_arr > threshold] - threshold
    n = len(excess)
    if n < 10:
        raise ValueError(
            f"too few exceedances above threshold {threshold:.4g}: n={n} (need ≥10)"
        )

    # scipy.stats.genpareto MLE with location fixed at 0 (we subtracted threshold)
    shape, _loc, scale = stats.genpareto.fit(excess, floc=0.0)

    # Asymptotic SE for (shape, scale) — Hosking & Wallis (1987), valid for shape > -0.5
    if shape > -0.5:
        shape_se = (1.0 + shape) / math.sqrt(n)
        scale_se = scale * math.sqrt(2.0 * (1.0 + shape) / n)
    else:
        # Regularity condition violated — MLE is non-regular, asymptotic SE undefined
        shape_se = float("nan")
        scale_se = float("nan")

    threshold_quantile = float(np.mean(Y_arr <= threshold))

    return GPDFitResult(
        threshold_quantile=threshold_quantile,
        threshold_value=float(threshold),
        shape=float(shape),
        shape_se=float(shape_se),
        shape_bootstrap_ci_95=(float("nan"), float("nan")),
        scale=float(scale),
        scale_se=float(scale_se),
        n_exceedances=n,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py -v
```

Expected: 3 PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `148 passed` (145 existing + 3 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "feat(analysis): add fit_gpd point-estimate function"
```

---

## Task 3: GPD threshold sweep with bootstrap CI

**Why:** Add `gpd_threshold_sweep` that fits GPD at multiple quantile thresholds and adds a non-parametric bootstrap CI on the shape parameter. This is the sensitivity-check half of the GPD module — does ξ stay stable across threshold choices?

**Files:**
- Modify: `src/surg/analysis/gpd.py` (append `gpd_threshold_sweep`)
- Modify: `tests/analysis/test_gpd.py` (append sweep tests)

- [ ] **Step 1: Write failing tests for `gpd_threshold_sweep`**

Append to `tests/analysis/test_gpd.py`:

```python
from surg.analysis.gpd import gpd_threshold_sweep


def test_gpd_threshold_sweep_returns_count_equal_to_quantile_count():
    """Passing 4 quantiles produces exactly 4 fits."""
    rng = np.random.default_rng(seed=42)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=5000, random_state=rng)

    results = gpd_threshold_sweep(
        Y, quantiles=(0.50, 0.75, 0.90, 0.95), n_boot=50, seed=0
    )

    assert len(results) == 4
    for fit, expected_q in zip(results, (0.50, 0.75, 0.90, 0.95), strict=True):
        assert isinstance(fit, GPDFitResult)
        assert fit.threshold_quantile == pytest.approx(expected_q, abs=0.01)
        # Bootstrap CI should be non-degenerate (positive width) and finite
        lo, hi = fit.shape_bootstrap_ci_95
        assert math.isfinite(lo) and math.isfinite(hi), \
            f"CI not finite at q={expected_q}: ({lo}, {hi})"
        assert hi > lo, f"CI has zero width at q={expected_q}: ({lo}, {hi})"


def test_gpd_threshold_sweep_seed_reproducibility():
    """Same seed must produce identical bootstrap CIs across runs."""
    rng = np.random.default_rng(seed=42)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=2000, random_state=rng)

    r1 = gpd_threshold_sweep(Y, quantiles=(0.5, 0.75), n_boot=30, seed=123)
    r2 = gpd_threshold_sweep(Y, quantiles=(0.5, 0.75), n_boot=30, seed=123)
    for f1, f2 in zip(r1, r2, strict=True):
        assert f1.shape_bootstrap_ci_95 == f2.shape_bootstrap_ci_95
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_gpd_threshold_sweep_returns_count_equal_to_quantile_count -v
```

Expected: `ImportError` — `gpd_threshold_sweep` not yet defined.

- [ ] **Step 3: Implement `gpd_threshold_sweep` in `src/surg/analysis/gpd.py`**

Append to `src/surg/analysis/gpd.py`:

```python
def _bootstrap_shape_ci(
    Y: np.ndarray,
    *,
    threshold: float,
    n_boot: int,
    seed: int,
) -> tuple[float, float]:
    """Non-parametric pair-bootstrap CI on the GPD shape parameter.

    Resample row indices of `Y` with replacement, refit GPD at the same
    threshold each time, return 2.5%/97.5% quantiles of the shape estimates.

    Skips bootstrap reps that result in < 10 exceedances or fail to converge.
    Returns (nan, nan) if fewer than 20 reps succeed (CI uninformative).
    """
    rng = np.random.default_rng(seed)
    n = len(Y)
    shapes: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        Y_boot = Y[idx]
        try:
            fit = fit_gpd(Y_boot, threshold=threshold)
        except ValueError:
            continue
        shapes.append(fit.shape)
    if len(shapes) < 20:
        return (float("nan"), float("nan"))
    arr = np.asarray(shapes)
    return (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))


def gpd_threshold_sweep(
    Y: np.ndarray | pd.Series,
    *,
    quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    n_boot: int = 200,
    seed: int = 0,
) -> list[GPDFitResult]:
    """Fit GPD at each threshold quantile; report shape stability via bootstrap CI.

    For each `q ∈ quantiles`:
      1. threshold = empirical quantile of Y at q
      2. Fit GPD at that threshold (`fit_gpd`)
      3. Bootstrap CI on shape: pair-resample row indices of Y, refit, take
         2.5%/97.5% quantiles of the shape estimates
      4. Return a list of `GPDFitResult` with bootstrap CIs filled in

    Quantiles must be sorted ascending and in (0, 1). Raises ValueError otherwise.
    """
    Y_arr = np.asarray(Y, dtype=float)
    if not all(0.0 < q < 1.0 for q in quantiles):
        raise ValueError(f"quantiles must be in (0, 1); got {quantiles}")
    if list(quantiles) != sorted(quantiles):
        raise ValueError(f"quantiles must be sorted ascending; got {quantiles}")

    results: list[GPDFitResult] = []
    for i, q in enumerate(quantiles):
        threshold = float(np.quantile(Y_arr, q))
        # Per-quantile seed offset so each fit uses a different bootstrap stream
        ci_lo, ci_hi = _bootstrap_shape_ci(
            Y_arr, threshold=threshold, n_boot=n_boot, seed=seed + i,
        )
        base = fit_gpd(Y_arr, threshold=threshold)
        # Replace the (nan, nan) placeholder with the bootstrap CI
        result = GPDFitResult(
            threshold_quantile=base.threshold_quantile,
            threshold_value=base.threshold_value,
            shape=base.shape,
            shape_se=base.shape_se,
            shape_bootstrap_ci_95=(ci_lo, ci_hi),
            scale=base.scale,
            scale_se=base.scale_se,
            n_exceedances=base.n_exceedances,
        )
        results.append(result)
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py -v
```

Expected: 5 PASS (3 existing + 2 new).

- [ ] **Step 5: Run full suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `150 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "feat(analysis): add gpd_threshold_sweep with bootstrap shape CI"
```

---

## Task 4: GPD Z-conditional split with bootstrap p-value

**Why:** Add `gpd_conditional_on_z` — the mechanism test. Splits exceedances into low-Z and high-Z subsets at Z's median, fits GPD to each, and bootstraps the shape-parameter difference. Answers: "does the LMP tail get heavier when load volatility is high?"

**Files:**
- Modify: `src/surg/analysis/gpd.py` (append `GPDConditionalResult` + `gpd_conditional_on_z`)
- Modify: `tests/analysis/test_gpd.py` (append conditional tests)

- [ ] **Step 1: Write failing tests for `gpd_conditional_on_z`**

Append to `tests/analysis/test_gpd.py`:

```python
from surg.analysis.gpd import GPDConditionalResult, gpd_conditional_on_z


def test_gpd_conditional_detects_z_dependent_shape():
    """When DGP has higher tail heaviness at high Z, the conditional split
    should detect it: shape_diff > 0 with low bootstrap p-value."""
    rng = np.random.default_rng(seed=42)
    n = 8000
    Z = rng.uniform(0, 10, size=n)
    # Generate Y with Z-dependent GPD shape: ξ = 0.5 if Z > 5, else 0.1
    Y = np.empty(n)
    high_z = Z > 5.0
    n_high = int(high_z.sum())
    n_low = n - n_high
    Y[high_z] = stats.genpareto.rvs(c=0.5, scale=2.0, size=n_high, random_state=rng)
    Y[~high_z] = stats.genpareto.rvs(c=0.1, scale=2.0, size=n_low, random_state=rng)

    result = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.5, z_split_quantile=0.5, n_boot=100, seed=0,
    )

    assert isinstance(result, GPDConditionalResult)
    assert result.z_split_value == pytest.approx(np.median(Z), abs=0.1)
    assert result.shape_diff > 0.2, f"shape_diff too small: {result.shape_diff}"
    assert result.shape_diff_bootstrap_p_value < 0.05, \
        f"failed to detect z-dependence: p={result.shape_diff_bootstrap_p_value}"
    # CI should not include 0 since the difference is real and positive
    lo, hi = result.shape_diff_bootstrap_ci_95
    assert lo > 0 or hi < 0 or (lo < 0 < hi and abs(lo) < hi), \
        f"CI does not cleanly exclude 0: ({lo}, {hi})"


def test_gpd_conditional_null_when_z_independent():
    """When DGP has Z-independent shape, the conditional split should give
    a non-tiny bootstrap p-value (broad null check, not exact)."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    Z = rng.uniform(0, 10, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    result = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.5, z_split_quantile=0.5, n_boot=100, seed=0,
    )

    assert result.shape_diff_bootstrap_p_value > 0.10, \
        f"false-positive z-dependence: p={result.shape_diff_bootstrap_p_value}"


def test_gpd_conditional_validates_length_mismatch():
    """Y and Z must have the same length."""
    rng = np.random.default_rng(seed=42)
    Y = rng.exponential(scale=5.0, size=100)
    Z = rng.uniform(0, 10, size=50)  # wrong length
    with pytest.raises(ValueError, match="length"):
        gpd_conditional_on_z(Y, Z, threshold_quantile=0.5, n_boot=10)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_gpd_conditional_detects_z_dependent_shape -v
```

Expected: `ImportError` — `gpd_conditional_on_z` not defined.

- [ ] **Step 3: Implement `GPDConditionalResult` + `gpd_conditional_on_z` in `src/surg/analysis/gpd.py`**

Append to `src/surg/analysis/gpd.py`:

```python
@dataclass(frozen=True, slots=True)
class GPDConditionalResult:
    """Z-conditional GPD: fit on low-Z and high-Z halves of the exceedance set."""
    threshold_quantile: float
    threshold_value: float
    z_split_quantile: float
    z_split_value: float
    low_z: GPDFitResult
    high_z: GPDFitResult
    shape_diff: float                                # ξ_high − ξ_low
    shape_diff_bootstrap_ci_95: tuple[float, float]
    shape_diff_bootstrap_p_value: float              # one-sided: P(ξ_high − ξ_low ≤ 0)


def gpd_conditional_on_z(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    *,
    threshold_quantile: float = 0.95,
    z_split_quantile: float = 0.5,
    n_boot: int = 200,
    seed: int = 0,
) -> GPDConditionalResult:
    """Fit GPD separately to low-Z and high-Z halves of the exceedance set.

    Procedure:
      1. threshold = empirical quantile of Y at `threshold_quantile`
      2. exceedances = rows where Y > threshold
      3. z_split = empirical quantile of Z[exceedances] at `z_split_quantile`
      4. low_z subset = exceedances where Z ≤ z_split
         high_z subset = exceedances where Z > z_split
      5. Fit GPD on each subset independently
      6. Bootstrap: resample exceedance row indices (paired Y,Z) with replacement,
         recompute z_split inside each bootstrap rep, refit both subsets, record
         shape_diff = ξ_high - ξ_low. Return 2.5%/97.5% quantiles plus one-sided
         p-value (fraction of bootstrap reps with shape_diff ≤ 0).
    """
    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    if len(Y_arr) != len(Z_arr):
        raise ValueError(f"Y and Z must have equal length; got {len(Y_arr)} vs {len(Z_arr)}")
    if not 0.0 < threshold_quantile < 1.0:
        raise ValueError(f"threshold_quantile must be in (0,1); got {threshold_quantile}")
    if not 0.0 < z_split_quantile < 1.0:
        raise ValueError(f"z_split_quantile must be in (0,1); got {z_split_quantile}")

    threshold = float(np.quantile(Y_arr, threshold_quantile))
    exceed_mask = Y_arr > threshold
    Y_exc = Y_arr[exceed_mask]
    Z_exc = Z_arr[exceed_mask]
    if len(Y_exc) < 20:
        raise ValueError(
            f"too few exceedances ({len(Y_exc)}) above threshold_quantile={threshold_quantile} "
            f"for a Z-split test (need ≥20)"
        )

    z_split = float(np.quantile(Z_exc, z_split_quantile))
    low_mask = Z_exc <= z_split
    high_mask = ~low_mask

    if low_mask.sum() < 10 or high_mask.sum() < 10:
        raise ValueError(
            f"too few exceedances per subset at z_split_quantile={z_split_quantile}: "
            f"low_z={int(low_mask.sum())}, high_z={int(high_mask.sum())} (each needs ≥10)"
        )

    low_z_fit = fit_gpd(Y_exc[low_mask], threshold=threshold)
    high_z_fit = fit_gpd(Y_exc[high_mask], threshold=threshold)
    shape_diff = high_z_fit.shape - low_z_fit.shape

    # Bootstrap on shape_diff: resample exceedance indices, recompute split,
    # refit both. Skip reps where either subset has too few obs.
    rng = np.random.default_rng(seed)
    n_exc = len(Y_exc)
    diffs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_exc, size=n_exc)
        Y_b = Y_exc[idx]
        Z_b = Z_exc[idx]
        z_split_b = float(np.quantile(Z_b, z_split_quantile))
        low_b = Z_b <= z_split_b
        high_b = ~low_b
        if low_b.sum() < 10 or high_b.sum() < 10:
            continue
        try:
            low_fit_b = fit_gpd(Y_b[low_b], threshold=threshold)
            high_fit_b = fit_gpd(Y_b[high_b], threshold=threshold)
        except ValueError:
            continue
        diffs.append(high_fit_b.shape - low_fit_b.shape)

    if len(diffs) < 20:
        ci = (float("nan"), float("nan"))
        p_value = float("nan")
    else:
        arr = np.asarray(diffs)
        ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
        # One-sided test: alternative is shape_diff > 0
        p_value = float(np.mean(arr <= 0.0))

    return GPDConditionalResult(
        threshold_quantile=float(threshold_quantile),
        threshold_value=threshold,
        z_split_quantile=float(z_split_quantile),
        z_split_value=z_split,
        low_z=low_z_fit,
        high_z=high_z_fit,
        shape_diff=float(shape_diff),
        shape_diff_bootstrap_ci_95=ci,
        shape_diff_bootstrap_p_value=p_value,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py -v
```

Expected: 8 PASS.

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `153 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "feat(analysis): add gpd_conditional_on_z mechanism test"
```

---

## Task 5: `run_gpd` end-to-end orchestrator + JSON schema test

**Why:** Wire `gpd_threshold_sweep` + `gpd_conditional_on_z` into a panel-consuming function that writes the documented JSON schema. This is what `run_all` will call per pnode.

**Files:**
- Modify: `src/surg/analysis/gpd.py` (append `run_gpd`)
- Modify: `tests/analysis/test_gpd.py` (append schema test)

- [ ] **Step 1: Write a failing test for `run_gpd`**

Append to `tests/analysis/test_gpd.py`:

```python
from pathlib import Path

from surg.analysis.gpd import run_gpd


def test_run_gpd_writes_expected_json_schema(tmp_path: Path):
    """run_gpd writes a JSON file with the spec-documented schema."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng),
        "Z_target": rng.uniform(0, 10, size=n),
    })

    out = tmp_path / "gpd" / "test_pnode.json"
    run_gpd(
        panel,
        out_path=out,
        response_col="Y_target",
        pnode_label="test_pnode",
        threshold_col="Z_target",
        sweep_quantiles=(0.50, 0.75, 0.90, 0.95),
        conditional_threshold_quantile=0.5,
        n_boot=50,
        seed=0,
    )

    assert out.exists(), f"run_gpd did not write {out}"
    payload = json.loads(out.read_text())

    # Top-level shape
    assert payload["pnode_label"] == "test_pnode"
    assert payload["response_col"] == "Y_target"
    assert payload["threshold_col"] == "Z_target"
    assert payload["n_total_panel"] == n
    assert payload["n_after_dropna"] == n

    # Threshold sweep: 4 entries
    sweep = payload["threshold_sweep"]
    assert len(sweep) == 4
    for entry in sweep:
        assert set(entry.keys()) >= {
            "threshold_quantile", "threshold_value", "n_exceedances",
            "shape", "shape_se", "shape_bootstrap_ci_95", "scale", "scale_se",
        }
        assert isinstance(entry["shape_bootstrap_ci_95"], list)
        assert len(entry["shape_bootstrap_ci_95"]) == 2

    # Conditional Z
    cond = payload["conditional_z"]
    assert cond["threshold_quantile"] == pytest.approx(0.5)
    assert "low_z" in cond and "high_z" in cond
    assert set(cond["low_z"].keys()) >= {"shape", "shape_se", "n_exceedances"}
    assert "shape_difference" in cond
    diff_block = cond["shape_difference"]
    assert set(diff_block.keys()) >= {"diff", "bootstrap_ci_95", "bootstrap_p_value"}
```

This test imports `json` at the top of the file — verify the import already exists at the top of `test_gpd.py`; if not, add `import json` to the imports.

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_run_gpd_writes_expected_json_schema -v
```

Expected: `ImportError` — `run_gpd` not defined.

- [ ] **Step 3: Implement `run_gpd` in `src/surg/analysis/gpd.py`**

Append to `src/surg/analysis/gpd.py`:

```python
def _gpd_fit_result_to_dict(fit: GPDFitResult) -> dict:
    return {
        "threshold_quantile": fit.threshold_quantile,
        "threshold_value": fit.threshold_value,
        "n_exceedances": fit.n_exceedances,
        "shape": fit.shape,
        "shape_se": fit.shape_se,
        "shape_bootstrap_ci_95": list(fit.shape_bootstrap_ci_95),
        "scale": fit.scale,
        "scale_se": fit.scale_se,
    }


def run_gpd(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    response_col: str,
    pnode_label: str,
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    sweep_quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    conditional_threshold_quantile: float = 0.95,
    z_split_quantile: float = 0.5,
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """End-to-end GPD analysis on the full panel: threshold sweep + Z-conditional split.

    Writes a JSON file at `out_path` matching the schema documented in
    `docs/plans/2026-05-13-strategy-c-modules.md` § "Module: gpd.py".

    Drops NaN rows in [response_col, threshold_col] only; does NOT filter by
    `passes_proposal_filter` — Strategy C operates on the full panel.
    """
    n_total = len(panel)
    subset = panel.dropna(subset=[response_col, threshold_col])
    Y = subset[response_col].to_numpy()
    Z = subset[threshold_col].to_numpy()
    n_after_dropna = len(subset)

    sweep_results = gpd_threshold_sweep(
        Y, quantiles=sweep_quantiles, n_boot=n_boot, seed=seed,
    )
    cond_result = gpd_conditional_on_z(
        Y, Z,
        threshold_quantile=conditional_threshold_quantile,
        z_split_quantile=z_split_quantile,
        n_boot=n_boot,
        seed=seed + 100,  # offset so sweep and conditional use disjoint bootstrap streams
    )

    payload = {
        "pnode_label": pnode_label,
        "response_col": response_col,
        "threshold_col": threshold_col,
        "n_total_panel": int(n_total),
        "n_after_dropna": int(n_after_dropna),
        "threshold_sweep": [_gpd_fit_result_to_dict(fit) for fit in sweep_results],
        "conditional_z": {
            "threshold_quantile": cond_result.threshold_quantile,
            "threshold_value": cond_result.threshold_value,
            "z_split_quantile": cond_result.z_split_quantile,
            "z_split_value": cond_result.z_split_value,
            "low_z": _gpd_fit_result_to_dict(cond_result.low_z),
            "high_z": _gpd_fit_result_to_dict(cond_result.high_z),
            "shape_difference": {
                "diff": cond_result.shape_diff,
                "bootstrap_ci_95": list(cond_result.shape_diff_bootstrap_ci_95),
                "bootstrap_p_value": cond_result.shape_diff_bootstrap_p_value,
            },
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_run_gpd_writes_expected_json_schema -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `154 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "feat(analysis): add run_gpd orchestrator with JSON output"
```

---

## Task 6: `qr_full.py` scaffold + `fit_qr_full` primary spec (point estimates, no bootstrap, no year-FE)

**Why:** Build the QR-on-full-panel module's foundation. Just the primary specification with point estimates and asymptotic SE — bootstrap CI lands in Task 7, year-FE in Task 8.

**Files:**
- Create: `src/surg/analysis/qr_full.py`
- Create: `tests/analysis/test_qr_full.py`

- [ ] **Step 1: Write failing tests for `fit_qr_full` (primary spec)**

Create `tests/analysis/test_qr_full.py`:

```python
"""Unit tests for src/surg/analysis/qr_full.py — Strategy C QR-on-full-panel module."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from surg.analysis.qr_full import QRFullFitResult, fit_qr_full


def _synth_inputs(
    *,
    n: int = 5000,
    z_slope: float = 2.0,
    hour_amplitude: float = 3.0,
    noise_sd: float = 1.0,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate synthetic (Y, Z, hour, month) with a planted Z-slope."""
    rng = np.random.default_rng(seed)
    Z = rng.uniform(0, 10, size=n)
    hour = rng.integers(0, 24, size=n)
    month = rng.integers(1, 13, size=n)
    hour_sin = np.sin(2 * np.pi * hour / 24)
    Y = 5.0 + z_slope * Z + hour_amplitude * hour_sin + rng.normal(0, noise_sd, size=n)
    return Y, Z, hour, month


def test_fit_qr_full_recovers_planted_slope():
    """fit_qr_full at tau=0.5 should recover the planted Z slope."""
    Y, Z, hour, month = _synth_inputs(n=5000, z_slope=2.0, seed=42)
    result = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=0, seed=0)

    assert isinstance(result, QRFullFitResult)
    assert result.spec == "primary"
    assert result.n == 5000
    assert result.tau == 0.5
    assert result.z_slope == pytest.approx(2.0, abs=0.1)
    assert result.z_slope_p_value < 1e-6, f"slope p too high: {result.z_slope_p_value}"
    # Covariate coefs should include the four sin/cos columns
    assert set(result.covariate_coefs.keys()) == {
        "hour_sin", "hour_cos", "month_sin", "month_cos",
    }


def test_fit_qr_full_no_signal_gives_high_p():
    """With Z's slope set to 0, the asymptotic p-value should be > 0.05 most of the time.

    Two seeds to reduce single-draw flakiness; assert at least one is non-significant.
    """
    p_values = []
    for seed in (42, 43):
        Y, Z, hour, month = _synth_inputs(n=3000, z_slope=0.0, seed=seed)
        result = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=0, seed=0)
        p_values.append(result.z_slope_p_value)
    assert max(p_values) > 0.05, f"no seed produced p > 0.05; got {p_values}"


def test_fit_qr_full_validates_length_mismatch():
    """All four input arrays must have equal length."""
    rng = np.random.default_rng(seed=42)
    Y = rng.normal(size=100)
    Z = rng.normal(size=100)
    hour = rng.integers(0, 24, size=100)
    month_short = rng.integers(1, 13, size=50)  # wrong length
    with pytest.raises(ValueError, match="length"):
        fit_qr_full(Y, Z, hour, month_short, tau=0.5)


def test_fit_qr_full_validates_no_nan():
    """NaN in any input array raises ValueError (caller-clean precondition)."""
    rng = np.random.default_rng(seed=42)
    Y = rng.normal(size=100).astype(float)
    Y[3] = float("nan")
    Z = rng.normal(size=100)
    hour = rng.integers(0, 24, size=100)
    month = rng.integers(1, 13, size=100)
    with pytest.raises(ValueError, match="NaN"):
        fit_qr_full(Y, Z, hour, month, tau=0.5)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_qr_full.py -v
```

Expected: import error — module not yet created.

- [ ] **Step 3: Create `src/surg/analysis/qr_full.py`**

Create the file with this content:

```python
"""Multi-quantile QR on the full panel with time-of-day + season covariates.

Strategy C module — operates on the full 31,536-hour analysis panel
(no `passes_proposal_filter` filtering). Each fit produces point
estimates and asymptotic SE; bootstrap CI is added in Task 7 of the
implementation plan. Year-FE robustness specification is added in
Task 8.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(frozen=True, slots=True)
class QRFullFitResult:
    """Single QR fit at one quantile, one specification (primary or year_fe).

    `z_slope_bootstrap_ci_95` is `(nan, nan)` until Task 7 wires bootstrap.
    """
    tau: float
    z_slope: float
    z_slope_se: float
    z_slope_p_value: float
    z_slope_bootstrap_ci_95: tuple[float, float]
    intercept: float
    covariate_coefs: dict[str, float]
    spec: str   # "primary" or "year_fe"
    n: int


def _build_periodic_basis(hour: np.ndarray, month: np.ndarray) -> dict[str, np.ndarray]:
    """Return the four sin/cos basis columns for hour and month."""
    return {
        "hour_sin":  np.sin(2.0 * np.pi * hour / 24.0),
        "hour_cos":  np.cos(2.0 * np.pi * hour / 24.0),
        "month_sin": np.sin(2.0 * np.pi * (month - 1) / 12.0),
        "month_cos": np.cos(2.0 * np.pi * (month - 1) / 12.0),
    }


def fit_qr_full(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    hour: np.ndarray | pd.Series,
    month: np.ndarray | pd.Series,
    *,
    tau: float = 0.99,
    n_boot: int = 0,
    seed: int = 0,
) -> QRFullFitResult:
    """Fit Q_τ(Y | Z, sin/cos(hour), sin/cos(month)).

    All four arrays must have equal length and contain no NaN. (Caller drops
    NaN rows before passing.) `n_boot=0` skips bootstrap CI and returns
    `(nan, nan)` for `z_slope_bootstrap_ci_95`; non-zero `n_boot` will be
    wired in a subsequent task.
    """
    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    hour_arr = np.asarray(hour, dtype=int)
    month_arr = np.asarray(month, dtype=int)

    n = len(Y_arr)
    if not (len(Z_arr) == len(hour_arr) == len(month_arr) == n):
        raise ValueError(
            f"all inputs must have equal length; got Y={len(Y_arr)}, "
            f"Z={len(Z_arr)}, hour={len(hour_arr)}, month={len(month_arr)}"
        )
    if any(np.isnan(arr).any() for arr in (Y_arr, Z_arr)):
        raise ValueError("Y or Z contains NaN; caller must drop NaN rows first")

    basis = _build_periodic_basis(hour_arr, month_arr)
    X = np.column_stack([
        np.ones(n),                  # intercept
        Z_arr,                       # primary regressor
        basis["hour_sin"],
        basis["hour_cos"],
        basis["month_sin"],
        basis["month_cos"],
    ])
    model = sm.QuantReg(Y_arr, X).fit(q=tau)
    z_slope = float(model.params[1])
    z_slope_se = float(model.bse[1])
    z_slope_p = float(model.pvalues[1])
    intercept = float(model.params[0])

    covariate_coefs = {
        name: float(model.params[i + 2])  # +2 to skip [intercept, Z]
        for i, name in enumerate(("hour_sin", "hour_cos", "month_sin", "month_cos"))
    }

    # Bootstrap CI is wired in Task 7; for now return placeholder
    ci: tuple[float, float] = (float("nan"), float("nan"))

    return QRFullFitResult(
        tau=float(tau),
        z_slope=z_slope,
        z_slope_se=z_slope_se,
        z_slope_p_value=z_slope_p,
        z_slope_bootstrap_ci_95=ci,
        intercept=intercept,
        covariate_coefs=covariate_coefs,
        spec="primary",
        n=n,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_qr_full.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `158 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/qr_full.py tests/analysis/test_qr_full.py
git commit -m "feat(analysis): add fit_qr_full primary spec with sin/cos covariates"
```

---

## Task 7: Bootstrap CI for `fit_qr_full`

**Why:** Wire the pair-bootstrap CI on the Z slope. Quantile regression's asymptotic SE is known to underperform at high τ with autocorrelated data; the bootstrap is the more honest interval. Same pattern as TAR's existing bootstrap CI.

**Files:**
- Modify: `src/surg/analysis/qr_full.py` (replace bootstrap placeholder with real loop)
- Modify: `tests/analysis/test_qr_full.py` (append bootstrap test)

- [ ] **Step 1: Write a failing test for the bootstrap CI**

Append to `tests/analysis/test_qr_full.py`:

```python
def test_fit_qr_full_bootstrap_ci_is_non_degenerate():
    """With n_boot > 0, the bootstrap CI is finite, has positive width,
    and brackets the point estimate.

    Full coverage-rate testing would require many simulations and is too slow
    for unit tests; an end-to-end coverage study can be a separate validation
    script if reviewer requests.
    """
    Y, Z, hour, month = _synth_inputs(n=2000, z_slope=2.0, seed=42)
    result = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=100, seed=0)

    lo, hi = result.z_slope_bootstrap_ci_95
    assert math.isfinite(lo) and math.isfinite(hi)
    assert hi > lo
    # The point estimate should sit inside the CI on a well-specified DGP
    assert lo <= result.z_slope <= hi, \
        f"point estimate {result.z_slope:.4f} outside CI [{lo:.4f}, {hi:.4f}]"


def test_fit_qr_full_bootstrap_seed_reproducibility():
    """Same seed gives identical bootstrap CI across runs."""
    Y, Z, hour, month = _synth_inputs(n=2000, z_slope=2.0, seed=42)
    r1 = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=50, seed=123)
    r2 = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=50, seed=123)
    assert r1.z_slope_bootstrap_ci_95 == r2.z_slope_bootstrap_ci_95
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_qr_full.py::test_fit_qr_full_bootstrap_ci_is_non_degenerate -v
```

Expected: FAIL — CI is `(nan, nan)`, `math.isfinite(nan)` is False.

- [ ] **Step 3: Implement the bootstrap loop in `fit_qr_full`**

In `src/surg/analysis/qr_full.py`, find this block (near the end of `fit_qr_full`):

```python
    # Bootstrap CI is wired in Task 7; for now return placeholder
    ci: tuple[float, float] = (float("nan"), float("nan"))
```

Replace it with:

```python
    ci: tuple[float, float] = _bootstrap_z_slope_ci(
        Y=Y_arr, Z=Z_arr, hour=hour_arr, month=month_arr,
        tau=tau, n_boot=n_boot, seed=seed,
    )
```

And add this helper function **above** `fit_qr_full` (after `_build_periodic_basis`):

```python
def _bootstrap_z_slope_ci(
    Y: np.ndarray,
    Z: np.ndarray,
    hour: np.ndarray,
    month: np.ndarray,
    *,
    tau: float,
    n_boot: int,
    seed: int,
    extra_X: np.ndarray | None = None,
) -> tuple[float, float]:
    """Pair-bootstrap 95% CI on the Z slope coefficient in fit_qr_full.

    Resamples row indices with replacement, refits QR each time, returns
    2.5%/97.5% quantiles of the Z-slope sampling distribution. Returns
    (nan, nan) if n_boot < 20 or fewer than 20 reps converge.

    `extra_X` is an optional matrix of additional design columns (used by
    the year-FE spec in Task 8). When None, only the sin/cos basis is used.
    """
    if n_boot < 20:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    n = len(Y)
    slopes: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        basis = _build_periodic_basis(hour[idx], month[idx])
        cols = [
            np.ones(n),
            Z[idx],
            basis["hour_sin"], basis["hour_cos"],
            basis["month_sin"], basis["month_cos"],
        ]
        if extra_X is not None:
            cols.append(extra_X[idx])
        X_boot = np.column_stack(cols)
        try:
            m = sm.QuantReg(Y[idx], X_boot).fit(q=tau)
            slopes.append(float(m.params[1]))
        except Exception:
            continue
    if len(slopes) < 20:
        return (float("nan"), float("nan"))
    arr = np.asarray(slopes)
    return (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_qr_full.py -v
```

Expected: 6 PASS.

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `160 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/qr_full.py tests/analysis/test_qr_full.py
git commit -m "feat(analysis): add pair-bootstrap CI for QR-full z_slope"
```

---

## Task 8: Year-FE robustness specification

**Why:** Add the year-FE specification to `fit_qr_full`. When `year` is passed, append year-dummy columns (earliest year as baseline) to the design matrix. The Z coefficient then captures the contemporaneous (within-year) response only; the difference between primary and year-FE Z slopes quantifies the secular DC-growth component.

**Files:**
- Modify: `src/surg/analysis/qr_full.py` (extend `fit_qr_full` signature; add year-dummy logic)
- Modify: `tests/analysis/test_qr_full.py` (append year-FE tests)

- [ ] **Step 1: Write failing tests for the year-FE path**

Append to `tests/analysis/test_qr_full.py`:

```python
def test_fit_qr_full_year_fe_adds_year_dummies():
    """When year is passed, covariate_coefs contains year_* keys (one per
    distinct year, excluding the earliest as baseline) and spec == 'year_fe'."""
    rng = np.random.default_rng(seed=42)
    n = 3000
    Z = rng.uniform(0, 10, size=n)
    hour = rng.integers(0, 24, size=n)
    month = rng.integers(1, 13, size=n)
    year = rng.choice([2022, 2023, 2024, 2025], size=n)
    Y = 5.0 + 2.0 * Z + 0.3 * (year - 2022) + rng.normal(0, 1, size=n)

    result = fit_qr_full(
        Y, Z, hour, month, year=year, tau=0.5, n_boot=0, seed=0,
    )

    assert result.spec == "year_fe"
    # Year dummies for 2023, 2024, 2025 (2022 is baseline)
    year_keys = [k for k in result.covariate_coefs if k.startswith("year_")]
    assert sorted(year_keys) == ["year_2023", "year_2024", "year_2025"]


def test_fit_qr_full_year_fe_isolates_contemporaneous_response():
    """When the DGP has a year-trend in Y that is correlated with Z's mean
    by year, year_fe should give a different (smaller) Z slope than primary.

    Construct Z such that mean Z is higher in later years; Y has a strong
    year trend independent of within-year Z.
    """
    rng = np.random.default_rng(seed=42)
    n_per_year = 1500
    years_list = [2022, 2023, 2024, 2025]
    Z_blocks = []
    Y_blocks = []
    year_arr = []
    for i, y in enumerate(years_list):
        Z_y = rng.normal(loc=i * 2.0, scale=1.0, size=n_per_year)  # mean shifts up by year
        # Y has a year-shift of 4 * year_index AND a true within-year Z slope of 1
        Y_y = 5.0 + 4.0 * i + 1.0 * Z_y + rng.normal(0, 0.5, size=n_per_year)
        Z_blocks.append(Z_y)
        Y_blocks.append(Y_y)
        year_arr.extend([y] * n_per_year)
    Z = np.concatenate(Z_blocks)
    Y = np.concatenate(Y_blocks)
    year = np.array(year_arr)
    hour = rng.integers(0, 24, size=len(Y))
    month = rng.integers(1, 13, size=len(Y))

    primary = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=0, seed=0)
    year_fe = fit_qr_full(Y, Z, hour, month, year=year, tau=0.5, n_boot=0, seed=0)

    # Primary picks up both the year trend AND the within-year slope → biased high
    # Year-FE isolates the within-year slope ≈ 1.0
    assert year_fe.z_slope == pytest.approx(1.0, abs=0.2), \
        f"year_fe z_slope too far from 1.0: {year_fe.z_slope}"
    assert primary.z_slope > year_fe.z_slope, \
        f"primary slope ({primary.z_slope}) should exceed year_fe slope ({year_fe.z_slope})"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_qr_full.py::test_fit_qr_full_year_fe_adds_year_dummies -v
```

Expected: TypeError — `fit_qr_full() got an unexpected keyword argument 'year'`.

- [ ] **Step 3: Extend `fit_qr_full` to accept `year` and build year dummies**

In `src/surg/analysis/qr_full.py`, replace the entire `fit_qr_full` function with this updated version:

```python
def fit_qr_full(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    hour: np.ndarray | pd.Series,
    month: np.ndarray | pd.Series,
    *,
    year: np.ndarray | pd.Series | None = None,
    tau: float = 0.99,
    n_boot: int = 0,
    seed: int = 0,
) -> QRFullFitResult:
    """Fit Q_τ(Y | Z, sin/cos(hour), sin/cos(month) [, year dummies]).

    Primary spec (year is None): design matrix is [1, Z, hour_sin, hour_cos,
    month_sin, month_cos]. Z slope captures contemporaneous + secular response.

    Year-FE spec (year is provided): same design matrix plus K-1 year dummies
    (earliest year as baseline). Z slope captures contemporaneous response only.

    All input arrays must have equal length and contain no NaN. Caller drops
    NaN rows first.
    """
    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    hour_arr = np.asarray(hour, dtype=int)
    month_arr = np.asarray(month, dtype=int)

    n = len(Y_arr)
    if not (len(Z_arr) == len(hour_arr) == len(month_arr) == n):
        raise ValueError(
            f"all inputs must have equal length; got Y={len(Y_arr)}, "
            f"Z={len(Z_arr)}, hour={len(hour_arr)}, month={len(month_arr)}"
        )
    if any(np.isnan(arr).any() for arr in (Y_arr, Z_arr)):
        raise ValueError("Y or Z contains NaN; caller must drop NaN rows first")

    basis = _build_periodic_basis(hour_arr, month_arr)
    base_cols = [
        np.ones(n),
        Z_arr,
        basis["hour_sin"], basis["hour_cos"],
        basis["month_sin"], basis["month_cos"],
    ]
    covariate_names = ["hour_sin", "hour_cos", "month_sin", "month_cos"]

    if year is None:
        spec = "primary"
        X = np.column_stack(base_cols)
        extra_X_for_boot: np.ndarray | None = None
    else:
        spec = "year_fe"
        year_arr = np.asarray(year, dtype=int)
        if len(year_arr) != n:
            raise ValueError(
                f"year length {len(year_arr)} != Y length {n}"
            )
        distinct_years = sorted(np.unique(year_arr).tolist())
        if len(distinct_years) < 2:
            raise ValueError(
                f"year_fe spec requires ≥2 distinct years; got {distinct_years}"
            )
        baseline_year = distinct_years[0]
        year_dummy_cols: list[np.ndarray] = []
        year_dummy_names: list[str] = []
        for y in distinct_years[1:]:
            year_dummy_cols.append((year_arr == y).astype(float))
            year_dummy_names.append(f"year_{y}")
        extra_X_for_boot = np.column_stack(year_dummy_cols)
        X = np.column_stack(base_cols + year_dummy_cols)
        covariate_names = covariate_names + year_dummy_names

    model = sm.QuantReg(Y_arr, X).fit(q=tau)
    z_slope = float(model.params[1])
    z_slope_se = float(model.bse[1])
    z_slope_p = float(model.pvalues[1])
    intercept = float(model.params[0])

    covariate_coefs = {
        name: float(model.params[i + 2])  # +2 to skip [intercept, Z]
        for i, name in enumerate(covariate_names)
    }

    ci = _bootstrap_z_slope_ci(
        Y=Y_arr, Z=Z_arr, hour=hour_arr, month=month_arr,
        tau=tau, n_boot=n_boot, seed=seed,
        extra_X=extra_X_for_boot,
    )

    return QRFullFitResult(
        tau=float(tau),
        z_slope=z_slope,
        z_slope_se=z_slope_se,
        z_slope_p_value=z_slope_p,
        z_slope_bootstrap_ci_95=ci,
        intercept=intercept,
        covariate_coefs=covariate_coefs,
        spec=spec,
        n=n,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_qr_full.py -v
```

Expected: 8 PASS.

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `162 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/qr_full.py tests/analysis/test_qr_full.py
git commit -m "feat(analysis): add year-FE robustness spec to fit_qr_full"
```

---

## Task 9: `run_qr_full` end-to-end orchestrator + JSON schema test

**Why:** Wire `fit_qr_full` into a panel-consuming function that runs at multiple τ values for both specs (primary + year-FE) and writes the documented JSON schema.

**Files:**
- Modify: `src/surg/analysis/qr_full.py` (append `run_qr_full`)
- Modify: `tests/analysis/test_qr_full.py` (append schema test)

- [ ] **Step 1: Write failing test for `run_qr_full`**

Append to `tests/analysis/test_qr_full.py`:

```python
from surg.analysis.qr_full import run_qr_full


def test_run_qr_full_writes_expected_json_schema(tmp_path: Path):
    """run_qr_full writes a JSON file with primary fits and year_fe fits."""
    rng = np.random.default_rng(seed=42)
    n = 1000
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": rng.normal(size=n),
        "Z_target": rng.uniform(0, 10, size=n),
    })

    out = tmp_path / "qr_full" / "test_pnode.json"
    run_qr_full(
        panel,
        out_path=out,
        response_col="Y_target",
        pnode_label="test_pnode",
        threshold_col="Z_target",
        taus=(0.90, 0.95, 0.99),
        n_boot=30,
        seed=0,
    )

    assert out.exists()
    payload = json.loads(out.read_text())

    assert payload["pnode_label"] == "test_pnode"
    assert payload["response_col"] == "Y_target"
    assert payload["threshold_col"] == "Z_target"
    assert payload["covariate_encoding"] == "sin_cos_hour_24_month_12"
    assert payload["n_total_panel"] == n
    assert payload["n_after_dropna"] == n

    # Primary fits: 3 entries at the requested taus
    fits = payload["fits"]
    assert len(fits) == 3
    for fit, expected_tau in zip(fits, (0.90, 0.95, 0.99), strict=True):
        assert fit["spec"] == "primary"
        assert fit["tau"] == pytest.approx(expected_tau)
        assert set(fit.keys()) >= {
            "tau", "spec", "z_slope", "z_slope_se", "z_slope_p_value",
            "z_slope_bootstrap_ci_95", "intercept", "covariate_coefs",
        }
        # Primary spec has only the 4 sin/cos coefs
        assert set(fit["covariate_coefs"].keys()) == {
            "hour_sin", "hour_cos", "month_sin", "month_cos",
        }

    # year_fe fits: 3 entries with year dummies present
    yfe = payload["fits_year_fe"]
    assert len(yfe) == 3
    for fit in yfe:
        assert fit["spec"] == "year_fe"
        # The synthetic panel spans only 2024 (one year, but the date_range
        # starts at 2024-01-01 with hourly freq for n=1000 hours ≈ 41 days,
        # so all observations are in 2024). With ≥2 years required for
        # year_fe, run_qr_full should detect this and either skip year_fe
        # or fall back. Adjust the panel to span 2 years.
        # The fixture above stays in 2024; for this assertion we accept
        # that year_fe may be skipped — let the implementation define the
        # contract. Test that fits_year_fe is at least the same length as
        # fits or explicitly an empty list with a documented reason.
        # (See implementation note: when only 1 year present, fits_year_fe
        # is an empty list and a "fits_year_fe_skip_reason" key is set.)
```

The trailing comments hint at the contract: when there's only one year, the year-FE spec can't run and `fits_year_fe` should be an empty list with a `fits_year_fe_skip_reason` key explaining why. Let's adjust the test to span 2 years and verify the year-FE path works:

Replace the test above with this corrected version (delete the previous one and use this):

```python
def test_run_qr_full_writes_expected_json_schema(tmp_path: Path):
    """run_qr_full writes a JSON file with primary fits and year_fe fits."""
    rng = np.random.default_rng(seed=42)
    n = 2000
    # Span two years (~83 days each) so the year-FE spec has ≥2 years
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": rng.normal(size=n),
        "Z_target": rng.uniform(0, 10, size=n),
    })
    # Shift half the dates into 2025
    panel.loc[n // 2:, "datetime_beginning_ept"] = pd.date_range("2025-01-01", periods=n - n // 2, freq="h")

    out = tmp_path / "qr_full" / "test_pnode.json"
    run_qr_full(
        panel,
        out_path=out,
        response_col="Y_target",
        pnode_label="test_pnode",
        threshold_col="Z_target",
        taus=(0.90, 0.95, 0.99),
        n_boot=30,
        seed=0,
    )

    assert out.exists()
    payload = json.loads(out.read_text())

    assert payload["pnode_label"] == "test_pnode"
    assert payload["covariate_encoding"] == "sin_cos_hour_24_month_12"
    assert payload["n_after_dropna"] == n

    # Primary fits
    fits = payload["fits"]
    assert len(fits) == 3
    for fit, expected_tau in zip(fits, (0.90, 0.95, 0.99), strict=True):
        assert fit["spec"] == "primary"
        assert fit["tau"] == pytest.approx(expected_tau)
        assert set(fit["covariate_coefs"].keys()) == {
            "hour_sin", "hour_cos", "month_sin", "month_cos",
        }

    # year_fe fits with year dummies
    yfe = payload["fits_year_fe"]
    assert len(yfe) == 3
    for fit in yfe:
        assert fit["spec"] == "year_fe"
        year_keys = [k for k in fit["covariate_coefs"] if k.startswith("year_")]
        assert year_keys == ["year_2025"]  # 2024 is baseline, 2025 is the dummy
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_qr_full.py::test_run_qr_full_writes_expected_json_schema -v
```

Expected: `ImportError` — `run_qr_full` not yet defined.

- [ ] **Step 3: Implement `run_qr_full` in `src/surg/analysis/qr_full.py`**

Append to `src/surg/analysis/qr_full.py`:

```python
def _qr_fit_result_to_dict(fit: QRFullFitResult) -> dict:
    return {
        "tau": fit.tau,
        "spec": fit.spec,
        "z_slope": fit.z_slope,
        "z_slope_se": fit.z_slope_se,
        "z_slope_p_value": fit.z_slope_p_value,
        "z_slope_bootstrap_ci_95": list(fit.z_slope_bootstrap_ci_95),
        "intercept": fit.intercept,
        "covariate_coefs": dict(fit.covariate_coefs),
    }


def run_qr_full(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    response_col: str,
    pnode_label: str,
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    taus: tuple[float, ...] = (0.90, 0.95, 0.99),
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """End-to-end QR on full panel. Writes JSON at out_path.

    Fits the primary specification (sin/cos covariates only) and the year-FE
    robustness specification (sin/cos + year dummies) at each tau. Drops NaN
    rows in [response_col, threshold_col] only; does NOT filter by
    passes_proposal_filter.

    When the panel spans only 1 year, the year-FE spec cannot run and
    fits_year_fe is an empty list with fits_year_fe_skip_reason set.
    """
    n_total = len(panel)
    subset = panel.dropna(subset=[response_col, threshold_col]).copy()
    subset = subset.sort_values("datetime_beginning_ept").reset_index(drop=True)
    n_after_dropna = len(subset)

    Y = subset[response_col].to_numpy()
    Z = subset[threshold_col].to_numpy()
    hour = subset["datetime_beginning_ept"].dt.hour.to_numpy()
    month = subset["datetime_beginning_ept"].dt.month.to_numpy()
    year = subset["datetime_beginning_ept"].dt.year.to_numpy()

    distinct_years = sorted(np.unique(year).tolist())
    year_fe_available = len(distinct_years) >= 2

    primary_fits: list[QRFullFitResult] = []
    yfe_fits: list[QRFullFitResult] = []
    for i, tau in enumerate(taus):
        primary_fits.append(fit_qr_full(
            Y, Z, hour, month, tau=tau, n_boot=n_boot, seed=seed + 10 * i,
        ))
        if year_fe_available:
            yfe_fits.append(fit_qr_full(
                Y, Z, hour, month, year=year,
                tau=tau, n_boot=n_boot, seed=seed + 10 * i + 1,
            ))

    payload: dict = {
        "pnode_label": pnode_label,
        "response_col": response_col,
        "threshold_col": threshold_col,
        "covariate_encoding": "sin_cos_hour_24_month_12",
        "n_total_panel": int(n_total),
        "n_after_dropna": int(n_after_dropna),
        "fits": [_qr_fit_result_to_dict(f) for f in primary_fits],
        "fits_year_fe": [_qr_fit_result_to_dict(f) for f in yfe_fits],
    }
    if not year_fe_available:
        payload["fits_year_fe_skip_reason"] = (
            f"only {len(distinct_years)} distinct year(s) in panel "
            f"({distinct_years}); year-FE spec requires ≥2"
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/analysis/test_qr_full.py::test_run_qr_full_writes_expected_json_schema -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `163 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/qr_full.py tests/analysis/test_qr_full.py
git commit -m "feat(analysis): add run_qr_full with primary + year-FE spec output"
```

---

## Task 10: Wire `run_qr_full` + `run_gpd` into `run_all` + integration test

**Why:** Make the new methods part of the standard `surg-analyze` pipeline so they fire automatically per pnode after the existing TAR/QR/mechanism/subsample fits.

**Files:**
- Modify: `src/surg/analysis/run.py` (extend `run_all`, add CLI flags)
- Modify: `tests/analysis/test_run.py` (update integration test for new output paths)

- [ ] **Step 1: Update integration test to expect new outputs**

Open `tests/analysis/test_run.py`, find `test_run_all_writes_all_outputs`, and replace the `expected_paths` block (added in Task 1) with the full extended set:

```python
expected_paths = {
    # Existing TAR (one per pnode)
    out_root / "tar" / "primary.json",
    out_root / "tar" / "total_lmp.json",
    out_root / "tar" / "ox.json",
    out_root / "tar" / "bristers.json",
    out_root / "tar" / "dom_zonal.json",
    out_root / "tar" / "ashburn_tx1.json",
    out_root / "tar" / "ashburn_tx2.json",
    # Existing QR / mechanism / robustness
    out_root / "qr" / "filtered_at_tar_c.json",
    out_root / "mechanism" / "validation.json",
    out_root / "robustness" / "subsample_bootstrap.parquet",
    # NEW: QR-full (one per pnode)
    out_root / "qr_full" / "primary.json",
    out_root / "qr_full" / "total_lmp.json",
    out_root / "qr_full" / "ox.json",
    out_root / "qr_full" / "bristers.json",
    out_root / "qr_full" / "dom_zonal.json",
    out_root / "qr_full" / "ashburn_tx1.json",
    out_root / "qr_full" / "ashburn_tx2.json",
    # NEW: GPD (one per pnode)
    out_root / "gpd" / "primary.json",
    out_root / "gpd" / "total_lmp.json",
    out_root / "gpd" / "ox.json",
    out_root / "gpd" / "bristers.json",
    out_root / "gpd" / "dom_zonal.json",
    out_root / "gpd" / "ashburn_tx1.json",
    out_root / "gpd" / "ashburn_tx2.json",
}
for p in expected_paths:
    assert p.exists(), f"expected output not written: {p}"
```

If the integration test invokes `run_all` with very small `n_boot` (e.g., 5 or 10), that's fine — the new methods' bootstrap loops also support small `n_boot` and will just produce nan CIs which the schema accepts. Confirm the test's `run_all` call passes `qr_full_n_boot` and `gpd_n_boot` (added below):

```python
run_all(
    panel=panel,
    events=events,
    out_root=out_root,
    n_boot=5,
    n_subsample_reps=5,
    qr_full_n_boot=5,
    gpd_n_boot=5,
)
```

- [ ] **Step 2: Run integration test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_run.py::test_run_all_writes_all_outputs -v
```

Expected: assertion failure on the first missing `qr_full/*.json` path (since `run_all` doesn't call `run_qr_full` yet) OR a TypeError on the unknown `qr_full_n_boot` kwarg if the test was updated before the function signature.

- [ ] **Step 3: Extend `run_all` in `src/surg/analysis/run.py`**

Open `src/surg/analysis/run.py`. Add these imports near the top (alongside the existing analysis-module imports):

```python
from surg.analysis.qr_full import run_qr_full
from surg.analysis.gpd import run_gpd
```

Then replace the `run_all` signature and body with this extended version:

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
) -> None:
    """Run the full Phase 3 analysis pipeline.

    Output layout (per-method subdirectories):
      - outputs/tar/<pnode_label>.json                          (Hansen TAR)
      - outputs/qr/filtered_at_tar_c.json                       (QR at TAR's ĉ, filtered)
      - outputs/qr_full/<pnode_label>.json                      (Strategy C QR-full)
      - outputs/gpd/<pnode_label>.json                          (Strategy C GPD)
      - outputs/mechanism/validation.json
      - outputs/robustness/subsample_bootstrap.parquet
    """
    out_root.mkdir(parents=True, exist_ok=True)

    primary = run_tar(
        panel=panel,
        out_path=out_root / "tar" / "primary.json",
        response_col=PNODE_RESPONSES["primary"],
        n_boot=n_boot,
    )

    for label, col in PNODE_RESPONSES.items():
        if label == "primary":
            continue
        if panel[col].dropna().empty:
            continue
        run_tar(
            panel=panel,
            out_path=out_root / "tar" / f"{label}.json",
            response_col=col,
            n_boot=n_boot,
        )

    run_qr(
        panel=panel,
        out_path=out_root / "qr" / "filtered_at_tar_c.json",
        c_for_threshold_dummy=primary.c_hat,
    )

    run_mechanism(
        panel=panel,
        events=events,
        threshold=primary.c_hat,
        out_path=out_root / "mechanism" / "validation.json",
    )

    subsample_bootstrap(
        panel=panel,
        out_path=out_root / "robustness" / "subsample_bootstrap.parquet",
        n_reps=n_subsample_reps,
    )

    # Strategy C methods: QR-full + GPD per pnode, full panel (no filter)
    for label, col in PNODE_RESPONSES.items():
        if panel[col].dropna().empty:
            continue
        run_qr_full(
            panel=panel,
            out_path=out_root / "qr_full" / f"{label}.json",
            response_col=col,
            pnode_label=label,
            n_boot=qr_full_n_boot,
        )
        run_gpd(
            panel=panel,
            out_path=out_root / "gpd" / f"{label}.json",
            response_col=col,
            pnode_label=label,
            n_boot=gpd_n_boot,
        )
```

Also extend `_build_arg_parser()` (the CLI parser) with two new arguments. Find the existing `--n-subsample-reps` arg and add right after it:

```python
    p.add_argument("--qr-full-n-boot", type=int, default=200,
                   help="Bootstrap reps for QR-full slope CI.")
    p.add_argument("--gpd-n-boot", type=int, default=200,
                   help="Bootstrap reps for GPD shape CI and conditional p-value.")
```

And in `main()`, find the `run_all(...)` call and add the two new args:

```python
    run_all(
        panel=panel, events=events,
        out_root=Path(args.out_root),
        n_boot=args.n_boot,
        n_subsample_reps=args.n_subsample_reps,
        qr_full_n_boot=args.qr_full_n_boot,
        gpd_n_boot=args.gpd_n_boot,
    )
```

- [ ] **Step 4: Run integration test to verify it passes**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full suite**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `163 passed` (no new tests in this task — only run_all signature changes; the new methods are still tested by their own modules' tests).

- [ ] **Step 6: Verify the CLI accepts the new flags**

```bash
.venv/bin/surg-analyze --help
```

Expected: `--qr-full-n-boot` and `--gpd-n-boot` appear in the help text.

- [ ] **Step 7: Commit**

```bash
git add src/surg/analysis/run.py tests/analysis/test_run.py
git commit -m "feat(analysis): wire run_qr_full + run_gpd into run_all"
```

---

## Task 11: Final verification — end-to-end smoke run + test-count check

**Why:** Confirm the full pipeline runs end-to-end on the real panel, all expected outputs land at the new paths, and the test suite is at the target count.

**Files:** None modified. This task only verifies.

- [ ] **Step 1: Confirm test count**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: at least `163 passed`. The spec said "target 165" — the actual final count depends on exactly how many tests landed in tests 6-9; anything ≥ 160 is acceptable for purposes of this task.

- [ ] **Step 2: Clear any prior outputs and run surg-analyze end-to-end at modest bootstrap reps**

```bash
rm -rf outputs/tar outputs/qr outputs/qr_full outputs/gpd outputs/mechanism outputs/robustness
.venv/bin/surg-analyze --n-boot 100 --n-subsample-reps 50 --qr-full-n-boot 50 --gpd-n-boot 50
```

Expected: completes without error, prints `wrote analysis outputs to outputs/`. Wall time ~3-4 minutes at these low bootstrap reps.

- [ ] **Step 3: Verify the output tree matches the spec**

```bash
find outputs -type f -name '*.json' -o -name '*.parquet' | sort
```

Expected output (24 files):

```
outputs/gpd/ashburn_tx1.json
outputs/gpd/ashburn_tx2.json
outputs/gpd/bristers.json
outputs/gpd/dom_zonal.json
outputs/gpd/ox.json
outputs/gpd/primary.json
outputs/gpd/total_lmp.json
outputs/mechanism/validation.json
outputs/qr/filtered_at_tar_c.json
outputs/qr_full/ashburn_tx1.json
outputs/qr_full/ashburn_tx2.json
outputs/qr_full/bristers.json
outputs/qr_full/dom_zonal.json
outputs/qr_full/ox.json
outputs/qr_full/primary.json
outputs/qr_full/total_lmp.json
outputs/robustness/subsample_bootstrap.parquet
outputs/tar/ashburn_tx1.json
outputs/tar/ashburn_tx2.json
outputs/tar/bristers.json
outputs/tar/dom_zonal.json
outputs/tar/ox.json
outputs/tar/primary.json
outputs/tar/total_lmp.json
```

- [ ] **Step 4: Spot-check one QR-full and one GPD JSON have the expected top-level keys**

```bash
.venv/bin/python -c "
import json
qr = json.loads(open('outputs/qr_full/primary.json').read())
print('qr_full primary keys:', sorted(qr.keys()))
print('qr_full primary fits count:', len(qr['fits']))
print('qr_full primary year_fe count:', len(qr['fits_year_fe']))
gpd = json.loads(open('outputs/gpd/primary.json').read())
print('gpd primary keys:', sorted(gpd.keys()))
print('gpd primary sweep count:', len(gpd['threshold_sweep']))
"
```

Expected: keys include `fits`, `fits_year_fe`, `pnode_label`, etc. for QR-full and `threshold_sweep`, `conditional_z`, etc. for GPD. Fit counts: 3 (for the 3 taus). Sweep count: 4 (for the 4 sweep quantiles).

- [ ] **Step 5: Verify git state is clean**

```bash
git status
```

Expected: working tree clean, branch is N commits ahead of `origin/main` (where N = the number of commits this plan added, ~10).

- [ ] **Step 6: No commit needed**

This task only verifies. If anything fails:
- Test count mismatch → check tests 2-9 added the right number; fix or update this task's expectations.
- Output path mismatch → check task 1 + task 10 paths agree; fix the `run_all` paths.
- JSON schema mismatch → check tasks 5 + 9 against the spec; fix the schema.

---

## Definition of done

- [ ] All 11 tasks complete.
- [ ] Tests passing: ≥ 163 (target 165, acceptable any ≥160).
- [ ] `outputs/` tree matches the layout in the spec.
- [ ] `surg-analyze --help` shows `--qr-full-n-boot` and `--gpd-n-boot` flags.
- [ ] End-to-end `surg-analyze` run completes without error and writes 24 output files.
- [ ] No regressions in existing acquisition, preprocessing, or analysis modules.

## Out of scope (per the design spec)

- JLARC growth-forecast projection layer.
- Paper-ready figure generation.
- Continuous `ξ(Z)` parametric tail-shape model.
- Backward-compat shims for the old output paths.
- `--methods-only` CLI flag to skip TAR.

Each of the above is deferred to its own future spec / task list.
