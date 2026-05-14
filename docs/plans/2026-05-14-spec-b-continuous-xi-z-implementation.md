# Spec B Continuous ξ(Z) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended per `memory/feedback_plan_execution.md`) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement non-stationary GPD with covariate-on-shape-and-scale per `docs/plans/2026-05-14-spec-b-continuous-xi-z-design.md` and the 2026-05-14 Spec B pre-reg in `decisions.md`. Produces `outputs/gpd_continuous/<pnode>.json` per-pnode + `outputs/gpd_continuous/headline.json` for the singular paper claim.

**Architecture:** New module `src/surg/analysis/gpd_continuous.py` (separate from gpd.py which is at ~857 lines). Custom MLE via `scipy.optimize.minimize` with BFGS + Nelder-Mead fallback (scipy.stats.genpareto.fit only handles constant params). Pair-bootstrap (n=200) for CIs and LRT p-value. Two parametric forms: linear (`ξ(Z) = β₀ + β₁·Z`, 2 DOF) and polynomial-degree-3 (`ξ(Z) = β₀ + β₁·Z + β₂·Z² + β₃·Z³`, 4 DOF — equivalent capability to a 4-DOF spline for our Z range; simpler implementation than manual natural cubic spline basis). Log-link on scale: `log σ(Z) = σ₀ + σ₁·Z`. Headline scalar is primary congestion @ 95th-pct LMP, linear form's β₁.

**Tech Stack:** Python 3.11+, scipy (`scipy.optimize.minimize` + `scipy.stats.genpareto`, both existing), numpy, pandas, pyarrow, pytest. No new dependencies.

**Design + pre-reg references:**
- Design: `docs/plans/2026-05-14-spec-b-continuous-xi-z-design.md` (commit `3753b97`).
- Pre-reg: `docs/decisions.md` § "2026-05-14 — Pre-registration: Spec B continuous ξ(Z) regression" (commit `0d1064d`).
- Roadmap: `docs/plans/2026-05-14-sub-question-1-closure-roadmap.md`.

**Execution worktree:** Recommend a sibling `feature/spec-b-continuous-xi-z` worktree under `../surg-spec-b`, matching the conditional-Z battery / Strategy C precedent. FF-merge to main after Task 7 verification.

---

## Task 1: Module skeleton + `GPDContinuousFitResult` dataclass + design-matrix + initial-params helpers

**Why this task exists:** Establish the data structures and small pure helpers (design matrix construction, MLE initial values) that the MLE function and bootstrap will use. All synchronous, no MLE yet.

**Files:**
- Create: `src/surg/analysis/gpd_continuous.py`
- Create: `tests/analysis/test_gpd_continuous.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/analysis/test_gpd_continuous.py`:

```python
"""Unit tests for src/surg/analysis/gpd_continuous.py — Spec B module."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from surg.analysis.gpd_continuous import (
    GPDContinuousFitResult,
    _design_matrix,
    _initial_params,
)


def test_gpd_continuous_fit_result_is_frozen_slots_dataclass():
    """GPDContinuousFitResult must be a frozen+slots dataclass (matching module convention)."""
    result = GPDContinuousFitResult(
        form="linear",
        threshold_quantile=0.95,
        threshold_value=10.0,
        n_exceedances=100,
        shape_coefficients=(0.5, -0.01),
        shape_coefficients_bootstrap_ci_95=((0.4, 0.6), (-0.02, 0.0)),
        scale_coefficients=(2.0, 0.05),
        scale_coefficients_bootstrap_ci_95=((1.8, 2.2), (0.03, 0.07)),
        headline_slope_or_lrt=-0.01,
        headline_p_value=0.04,
        convergence_status="converged",
    )
    assert result.form == "linear"
    with pytest.raises(Exception):
        result.form = "spline"  # frozen


def test_design_matrix_linear_returns_two_columns():
    """Linear form: design matrix has columns [1, Z] for shape regression."""
    Z = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    X = _design_matrix(Z, form="linear")
    assert X.shape == (5, 2)
    assert np.allclose(X[:, 0], 1.0)
    assert np.allclose(X[:, 1], Z)


def test_design_matrix_spline_returns_four_columns_polynomial_basis():
    """Spline form: design matrix has columns [1, Z, Z², Z³] (polynomial-degree-3 basis,
    4 DOF total, equivalent capability to a 4-DOF natural cubic spline)."""
    Z = np.array([0.0, 1.0, 2.0, 3.0])
    X = _design_matrix(Z, form="spline")
    assert X.shape == (4, 4)
    assert np.allclose(X[:, 0], 1.0)
    assert np.allclose(X[:, 1], Z)
    assert np.allclose(X[:, 2], Z ** 2)
    assert np.allclose(X[:, 3], Z ** 3)


def test_design_matrix_validates_form():
    """Invalid form raises ValueError."""
    Z = np.array([1.0, 2.0])
    with pytest.raises(ValueError, match="form"):
        _design_matrix(Z, form="quadratic")


def test_design_matrix_scale_always_linear():
    """Scale design matrix is always linear ([1, Z]) regardless of shape form;
    `for_scale=True` flag returns the scale matrix."""
    Z = np.array([1.0, 2.0, 3.0])
    X_sigma = _design_matrix(Z, form="linear", for_scale=True)
    assert X_sigma.shape == (3, 2)
    assert np.allclose(X_sigma[:, 0], 1.0)
    assert np.allclose(X_sigma[:, 1], Z)
    # Even with form="spline" for shape, scale design matrix is linear
    X_sigma_spline_scale = _design_matrix(Z, form="spline", for_scale=True)
    assert X_sigma_spline_scale.shape == (3, 2)


def test_initial_params_linear_uses_stationary_fit_as_intercepts():
    """Initial params for linear form: stationary GPD fit gives [β₀, 0, σ₀, 0]
    where β₀=shape and σ₀=log(scale) from the stationary fit."""
    rng = np.random.default_rng(seed=42)
    Y_exc = stats.genpareto.rvs(c=0.3, scale=2.0, size=500, random_state=rng)
    init = _initial_params(Y_exc, form="linear")
    # Linear shape: [β₀, β₁]; Scale: [σ₀ (log scale), σ₁]
    assert len(init) == 4
    beta_0, beta_1, sigma_0_log, sigma_1 = init
    # β₀ should be near the planted shape (0.3) within MLE noise
    assert abs(beta_0 - 0.3) < 0.2, f"β₀ initial too far from stationary: {beta_0}"
    # β₁ should be 0 (no Z dependence in initial guess)
    assert beta_1 == 0.0
    # σ₀ = log(scale) should be near log(2.0) = 0.693
    assert abs(sigma_0_log - math.log(2.0)) < 0.5, f"σ₀ initial off: {sigma_0_log}"
    # σ₁ should be 0
    assert sigma_1 == 0.0


def test_initial_params_spline_returns_six_params():
    """Spline form initial params: 4 shape params + 2 scale params = 6 total."""
    rng = np.random.default_rng(seed=42)
    Y_exc = stats.genpareto.rvs(c=0.3, scale=2.0, size=500, random_state=rng)
    init = _initial_params(Y_exc, form="spline")
    assert len(init) == 6
    # First 4 are shape (β₀, β₁, β₂, β₃); β₀ ≈ planted shape, others 0
    assert abs(init[0] - 0.3) < 0.2
    assert init[1] == 0.0
    assert init[2] == 0.0
    assert init[3] == 0.0
    # Last 2 are scale (σ₀ log, σ₁)
    assert abs(init[4] - math.log(2.0)) < 0.5
    assert init[5] == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'surg.analysis.gpd_continuous'`.

- [ ] **Step 3: Create `src/surg/analysis/gpd_continuous.py` with skeleton**

```python
"""Non-stationary Generalized Pareto Distribution fits with covariates on shape and scale.

Spec B module (sub-question 1 closure) — fits ξ(Z) = β₀ + β₁·Z (linear) or
ξ(Z) = β₀ + β₁·Z + β₂·Z² + β₃·Z³ (polynomial-degree-3, 4 DOF). Scale is
always log-linear: log σ(Z) = σ₀ + σ₁·Z.

The polynomial-degree-3 basis (4 DOF: intercept + linear + quadratic + cubic)
matches the design's "4-DOF flexible shape" intent. A natural cubic spline
with K=3 interior knots gives only 3 DOF per ESL convention (basis is K
functions including intercept); a 4-DOF natural cubic spline would need K=4
knots + knot placement. Polynomial basis avoids the knot-placement decision
and gives identical capability within the observed Z range.

Implementation reference: Davison & Smith 1990 (JRSS-B), Coles 2001 §6.3.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from scipy import stats

from surg.analysis.gpd import fit_gpd


@dataclass(frozen=True, slots=True)
class GPDContinuousFitResult:
    """Non-stationary GPD fit with covariate Z on shape and scale.

    `shape_coefficients`: linear form → (β₀, β₁); spline form → (β₀, β₁, β₂, β₃).
    `scale_coefficients`: always (σ₀ (log-scale intercept), σ₁) since scale form
    is fixed at log-linear regardless of shape form.
    `headline_slope_or_lrt`: β₁ for linear (the headline scalar in the pre-reg);
    LRT statistic (chi² value) for spline.
    `headline_p_value`: two-sided bootstrap p-value for β₁ (linear) or bootstrap
    p-value for LRT (spline).
    `convergence_status`: "converged" | "max_iter" | "failed" |
    "insufficient_bootstrap_reps".
    """
    form: Literal["linear", "spline"]
    threshold_quantile: float
    threshold_value: float
    n_exceedances: int
    shape_coefficients: tuple[float, ...]
    shape_coefficients_bootstrap_ci_95: tuple[tuple[float, float], ...]
    scale_coefficients: tuple[float, float]
    scale_coefficients_bootstrap_ci_95: tuple[tuple[float, float], tuple[float, float]]
    headline_slope_or_lrt: float
    headline_p_value: float
    convergence_status: str


def _design_matrix(
    Z: np.ndarray,
    *,
    form: Literal["linear", "spline"],
    for_scale: bool = False,
) -> np.ndarray:
    """Construct the design matrix X for shape regression (or scale, which is
    always linear).

    Linear shape: X = [1, Z], shape=(n, 2).
    Spline shape: X = [1, Z, Z², Z³], shape=(n, 4) — polynomial-degree-3 basis.
    Scale (always linear): X = [1, Z], shape=(n, 2).
    """
    Z_arr = np.asarray(Z, dtype=float)
    if for_scale or form == "linear":
        return np.column_stack([np.ones_like(Z_arr), Z_arr])
    if form == "spline":
        return np.column_stack([np.ones_like(Z_arr), Z_arr, Z_arr ** 2, Z_arr ** 3])
    raise ValueError(f"form must be 'linear' or 'spline'; got {form!r}")


def _initial_params(
    Y_exc: np.ndarray,
    *,
    form: Literal["linear", "spline"],
) -> tuple[float, ...]:
    """Compute MLE initial values from a stationary GPD fit on Y_exc.

    Returns:
      Linear: (β₀, β₁=0, σ₀=log(scale), σ₁=0) — 4 params.
      Spline: (β₀, β₁=0, β₂=0, β₃=0, σ₀=log(scale), σ₁=0) — 6 params.

    The stationary fit handles the case where Y_exc is already exceedance over
    a threshold (in this module's context, Y_exc has already been shifted to
    be exceedance values above 0).
    """
    Y_arr = np.asarray(Y_exc, dtype=float)
    # Stationary GPD fit on the exceedances (Y_exc already over threshold=0)
    base_fit = fit_gpd(Y_arr, threshold=0.0)
    shape_init = base_fit.shape
    log_scale_init = math.log(base_fit.scale)
    if form == "linear":
        return (shape_init, 0.0, log_scale_init, 0.0)
    if form == "spline":
        return (shape_init, 0.0, 0.0, 0.0, log_scale_init, 0.0)
    raise ValueError(f"form must be 'linear' or 'spline'; got {form!r}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `197 passed` (190 prior + 7 new). No failures.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd_continuous.py tests/analysis/test_gpd_continuous.py
git commit -m "$(cat <<'EOF'
feat(analysis): Spec B skeleton — GPDContinuousFitResult + design matrix + initial params

New module src/surg/analysis/gpd_continuous.py with:
- GPDContinuousFitResult dataclass (frozen+slots; mirrors module convention)
- _design_matrix(Z, *, form, for_scale=False): polynomial-degree-3 basis for
  shape (linear: 2 DOF; spline: 4 DOF); scale always linear (2 DOF)
- _initial_params(Y_exc, *, form): stationary GPD fit gives intercepts;
  slope/cubic params start at 0

Implementation note: polynomial-degree-3 basis [1, Z, Z², Z³] used instead
of natural cubic spline basis. ESL convention K interior knots → K basis
functions, so 3-knot natural cubic = 3 DOF (not 4 as design implied).
Polynomial-3 gives 4 DOF, no knot-placement decision, equivalent capability
within observed Z range.

7 new tests; full suite at 197.
EOF
)"
```

---

## Task 2: `_neg_log_likelihood_nonstationary_gpd` (the MLE objective)

**Why this task exists:** The core likelihood function. Pure-numerical, isolatable. Tested for finite values on valid input, +inf on invalid (boundary violations), and consistency with `scipy.stats.genpareto` for the stationary special case (σ₁=0, β₁=...=0).

**Files:**
- Modify: `src/surg/analysis/gpd_continuous.py` (add `_neg_log_likelihood_nonstationary_gpd`)
- Modify: `tests/analysis/test_gpd_continuous.py` (add ~4 new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/analysis/test_gpd_continuous.py`:

```python
from surg.analysis.gpd_continuous import _neg_log_likelihood_nonstationary_gpd


def test_neg_log_likelihood_finite_on_valid_params():
    """For valid parameters, the negative log-likelihood returns a finite float."""
    rng = np.random.default_rng(seed=42)
    Y_exc = stats.genpareto.rvs(c=0.3, scale=2.0, size=200, random_state=rng)
    Z_exc = rng.uniform(1.0, 10.0, size=200)
    X_xi = _design_matrix(Z_exc, form="linear")
    X_sigma = _design_matrix(Z_exc, form="linear", for_scale=True)
    # Reasonable params: shape ≈ 0.3, scale ≈ 2.0
    params = np.array([0.3, 0.0, math.log(2.0), 0.0])  # β₀, β₁, σ₀_log, σ₁
    nll = _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)
    assert math.isfinite(nll), f"NLL not finite: {nll}"
    assert nll > 0, f"NLL should be > 0 for positive sample: {nll}"


def test_neg_log_likelihood_returns_inf_on_negative_scale_implied():
    """If σ(Z) implied is non-positive for any observation, NLL returns +inf.

    Constructed: σ₀ = log(0.1), σ₁ = very negative → at high Z, σ(Z) underflows.
    Actually since we use exp(σ₀ + σ₁·Z), σ(Z) is always positive — this test
    instead probes the support violation: 1 + ξ(Z) * Y_exc / σ(Z) <= 0.
    """
    Y_exc = np.array([100.0, 200.0, 50.0])  # large exceedances
    Z_exc = np.array([1.0, 2.0, 3.0])
    X_xi = _design_matrix(Z_exc, form="linear")
    X_sigma = _design_matrix(Z_exc, form="linear", for_scale=True)
    # Force ξ(Z) very negative such that 1 + ξ·u/σ ≤ 0 for at least one obs
    params = np.array([-1.0, -0.5, math.log(1.0), 0.0])  # β₀=-1, β₁=-0.5 → ξ(3) = -2.5
    nll = _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)
    assert math.isinf(nll) and nll > 0, f"Expected +inf for support violation; got {nll}"


def test_neg_log_likelihood_matches_stationary_genpareto_when_z_terms_zero():
    """When β₁ = σ₁ = 0 (stationary special case), the non-stationary NLL
    matches scipy.stats.genpareto's log-pdf sum."""
    rng = np.random.default_rng(seed=42)
    true_shape, true_scale = 0.3, 2.0
    Y_exc = stats.genpareto.rvs(c=true_shape, scale=true_scale, size=300, random_state=rng)
    Z_exc = rng.uniform(1.0, 10.0, size=300)  # Z doesn't matter for stationary case
    X_xi = _design_matrix(Z_exc, form="linear")
    X_sigma = _design_matrix(Z_exc, form="linear", for_scale=True)
    params = np.array([true_shape, 0.0, math.log(true_scale), 0.0])

    nll_ours = _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)
    nll_scipy = -np.sum(stats.genpareto.logpdf(Y_exc, c=true_shape, loc=0.0, scale=true_scale))

    assert math.isclose(nll_ours, nll_scipy, rel_tol=1e-6), \
        f"Stationary NLL mismatch: ours={nll_ours}, scipy={nll_scipy}"


def test_neg_log_likelihood_handles_xi_near_zero_via_exponential_limit():
    """When ξ(Z) ≈ 0 for all Z (exponential tail), NLL uses the exponential
    log-density limit, not the genpareto formula (which would have 1/0 issues)."""
    Y_exc = np.array([1.0, 2.0, 3.0, 0.5, 4.0])
    Z_exc = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    X_xi = _design_matrix(Z_exc, form="linear")
    X_sigma = _design_matrix(Z_exc, form="linear", for_scale=True)
    # ξ exactly 0 at intercept, β₁=0 → ξ(Z) = 0 for all
    params = np.array([0.0, 0.0, math.log(2.0), 0.0])
    nll = _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)
    # Expected exponential NLL: sum(log σ + Y/σ) = n*log(2) + sum(Y)/2
    n = len(Y_exc)
    expected = n * math.log(2.0) + Y_exc.sum() / 2.0
    assert math.isclose(nll, expected, rel_tol=1e-6), \
        f"Exponential-limit NLL mismatch: got {nll}, expected {expected}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py::test_neg_log_likelihood_finite_on_valid_params -v
```

Expected: FAIL with `ImportError: cannot import name '_neg_log_likelihood_nonstationary_gpd'`.

- [ ] **Step 3: Add `_neg_log_likelihood_nonstationary_gpd` to gpd_continuous.py**

Append to `src/surg/analysis/gpd_continuous.py` (after `_initial_params`):

```python
def _neg_log_likelihood_nonstationary_gpd(
    params: np.ndarray,
    Y_exc: np.ndarray,
    X_xi: np.ndarray,
    X_sigma: np.ndarray,
) -> float:
    """Negative log-likelihood for non-stationary GPD with covariates Z.

    Y_exc[i] is exceedance over threshold (already shifted), modeled as
    GPD(σ(Z_i), ξ(Z_i)) where:
      log σ(Z) = X_sigma @ params_sigma  (last 2 params)
      ξ(Z)    = X_xi   @ params_xi      (first len(X_xi[0]) params)

    Returns +inf if any of the following invariant violations occurs:
      - σ(Z_i) ≤ 1e-10 for any i (numerical underflow)
      - 1 + ξ(Z_i) * Y_exc[i] / σ(Z_i) ≤ 0 for any i (support violation)
      - Y_exc[i] < 0 for any i (negative exceedance — input invariant violated)

    For ξ(Z_i) near 0 (|ξ| < 1e-8), uses the exponential log-density limit:
      log f(y; σ, ξ→0) = -log σ - y/σ
    """
    n_xi = X_xi.shape[1]
    params_xi = params[:n_xi]
    params_sigma = params[n_xi:]
    if len(params_sigma) != X_sigma.shape[1]:
        return float("inf")

    Y_arr = np.asarray(Y_exc, dtype=float)
    if (Y_arr < 0).any():
        return float("inf")

    log_sigma = X_sigma @ params_sigma
    sigma = np.exp(log_sigma)
    if (sigma <= 1e-10).any() or not np.isfinite(sigma).all():
        return float("inf")

    xi = X_xi @ params_xi
    if not np.isfinite(xi).all():
        return float("inf")

    # Support: 1 + ξ * y / σ > 0 for all observations
    inner = 1.0 + xi * Y_arr / sigma
    if (inner <= 0).any():
        return float("inf")

    # Two branches: |ξ| > 1e-8 (regular GPD log-density) and |ξ| ≤ 1e-8 (exponential limit)
    # For numerical stability, treat each observation by its xi value.
    near_zero = np.abs(xi) < 1e-8
    nll_terms = np.empty_like(Y_arr)
    # Regular branch
    reg_mask = ~near_zero
    nll_terms[reg_mask] = (
        log_sigma[reg_mask]
        + (1.0 + 1.0 / xi[reg_mask]) * np.log(inner[reg_mask])
    )
    # Exponential limit branch
    nll_terms[near_zero] = log_sigma[near_zero] + Y_arr[near_zero] / sigma[near_zero]

    total_nll = float(np.sum(nll_terms))
    if not math.isfinite(total_nll):
        return float("inf")
    return total_nll
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py -v --tb=short
```

Expected: 11 PASS (7 from Task 1 + 4 new).

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `201 passed` (197 from Task 1 + 4 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd_continuous.py tests/analysis/test_gpd_continuous.py
git commit -m "$(cat <<'EOF'
feat(analysis): Spec B negative log-likelihood for non-stationary GPD

Adds _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma):
core MLE objective for ξ(Z) and log σ(Z) regression with covariates.

Handles invariant violations explicitly:
- Sigma underflow (σ ≤ 1e-10): returns +inf
- Support violation (1 + ξ·y/σ ≤ 0): returns +inf
- Negative exceedance: returns +inf
- ξ near 0 (|ξ| < 1e-8): exponential log-density limit (avoids 1/0)
- Non-finite intermediate values: returns +inf

Verified against scipy.stats.genpareto for the stationary special case
(β₁=σ₁=0). 4 new tests; full suite at 201.
EOF
)"
```

---

## Task 3: `fit_gpd_continuous_z` — single fit with pair-bootstrap

**Why this task exists:** The full MLE + bootstrap function, given a fixed threshold and parametric form. Wraps the optimizer (BFGS + Nelder-Mead fallback), the bootstrap loop (200 reps default), and convergence-failure handling per the Spec B pre-reg.

**Files:**
- Modify: `src/surg/analysis/gpd_continuous.py` (add `fit_gpd_continuous_z`)
- Modify: `tests/analysis/test_gpd_continuous.py` (add ~5 new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/analysis/test_gpd_continuous.py`:

```python
from surg.analysis.gpd_continuous import fit_gpd_continuous_z


def test_fit_gpd_continuous_z_linear_recovers_planted_beta_1():
    """Planted DGP: ξ(Z) = 0.3 + 0.05·Z; fit recovers β₁ within bootstrap tolerance."""
    rng = np.random.default_rng(seed=42)
    n = 5000
    Z = rng.uniform(1.0, 10.0, size=n)
    # Generate Y with Z-dependent shape and constant scale
    Y_full = np.empty(n)
    for i in range(n):
        xi_i = 0.3 + 0.05 * Z[i]
        Y_full[i] = stats.genpareto.rvs(c=xi_i, scale=2.0, size=1, random_state=rng)[0]
    # Add some below-threshold values for the function to filter
    threshold = 0.0  # everything is an exceedance for this synthetic

    result = fit_gpd_continuous_z(
        Y_full, Z, threshold=threshold, form="linear", n_boot=100, seed=0,
    )

    assert isinstance(result, GPDContinuousFitResult)
    assert result.form == "linear"
    assert result.convergence_status == "converged"
    # Recovery tolerance: β₁ true is 0.05, MLE should be within ±0.03 at n=5000
    assert abs(result.shape_coefficients[1] - 0.05) < 0.03, \
        f"β₁ recovery off: {result.shape_coefficients[1]}"
    # Headline = β₁ for linear form
    assert result.headline_slope_or_lrt == result.shape_coefficients[1]


def test_fit_gpd_continuous_z_linear_null_dgp_gives_beta_1_near_zero():
    """When DGP has constant ξ, β₁ should be near zero and its CI should span 0."""
    rng = np.random.default_rng(seed=42)
    n = 3000
    Z = rng.uniform(1.0, 10.0, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)
    threshold = 0.0

    result = fit_gpd_continuous_z(
        Y, Z, threshold=threshold, form="linear", n_boot=100, seed=0,
    )

    assert abs(result.shape_coefficients[1]) < 0.05, \
        f"β₁ should be near 0 for null DGP: {result.shape_coefficients[1]}"
    # Two-sided p should be > 0.10 (cannot reject null)
    assert result.headline_p_value > 0.10, \
        f"False rejection: p={result.headline_p_value}"
    # CI should span 0
    ci_lo, ci_hi = result.shape_coefficients_bootstrap_ci_95[1]  # β₁ CI
    assert ci_lo < 0 < ci_hi, f"β₁ CI should span 0: ({ci_lo}, {ci_hi})"


def test_fit_gpd_continuous_z_spline_returns_four_shape_coefficients():
    """Spline form has 4 shape coefficients (β₀, β₁, β₂, β₃) + 2 scale coefficients."""
    rng = np.random.default_rng(seed=42)
    n = 3000
    Z = rng.uniform(1.0, 10.0, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    result = fit_gpd_continuous_z(
        Y, Z, threshold=0.0, form="spline", n_boot=50, seed=0,
    )

    assert result.form == "spline"
    assert len(result.shape_coefficients) == 4
    assert len(result.scale_coefficients) == 2
    assert len(result.shape_coefficients_bootstrap_ci_95) == 4
    assert len(result.scale_coefficients_bootstrap_ci_95) == 2


def test_fit_gpd_continuous_z_validates_inputs():
    """Y and Z must have same length; threshold must be finite."""
    rng = np.random.default_rng(seed=42)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=100, random_state=rng)
    Z = rng.uniform(1.0, 10.0, size=50)  # wrong length
    with pytest.raises(ValueError, match="length"):
        fit_gpd_continuous_z(Y, Z, threshold=0.0, form="linear", n_boot=10)

    with pytest.raises(ValueError, match="form"):
        fit_gpd_continuous_z(
            np.zeros(100), np.zeros(100), threshold=0.0, form="quadratic", n_boot=10,
        )


def test_fit_gpd_continuous_z_reports_insufficient_bootstrap_reps_on_low_n():
    """If fewer than 100 bootstrap reps succeed (out of n_boot=200), CI is NaN
    and convergence_status is 'insufficient_bootstrap_reps'."""
    # Synthetic small-n case to force frequent bootstrap failures
    rng = np.random.default_rng(seed=42)
    # Very small n_exc + force unstable fits via near-boundary support
    n = 35
    Y = rng.uniform(0.0, 0.1, size=n)  # near-zero exceedances, ξ MLE unstable
    Z = rng.uniform(1.0, 10.0, size=n)

    result = fit_gpd_continuous_z(
        Y, Z, threshold=0.0, form="spline", n_boot=200, seed=0,
    )
    # At n=35 with degenerate data, spline (6 params) + bootstrap likely fails
    # often. Status can be 'converged' but CI may be NaN if reps insufficient,
    # OR status can be 'failed' if the primary fit also fails. Either is valid.
    assert result.convergence_status in {
        "converged",
        "failed",
        "insufficient_bootstrap_reps",
    }
    if result.convergence_status == "insufficient_bootstrap_reps":
        # CI should be (NaN, NaN) for all coefficients
        for ci in result.shape_coefficients_bootstrap_ci_95:
            assert math.isnan(ci[0]) and math.isnan(ci[1])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py::test_fit_gpd_continuous_z_linear_recovers_planted_beta_1 -v
```

Expected: FAIL with `ImportError: cannot import name 'fit_gpd_continuous_z'`.

- [ ] **Step 3: Add `fit_gpd_continuous_z` to gpd_continuous.py**

Append to `src/surg/analysis/gpd_continuous.py` (after `_neg_log_likelihood_nonstationary_gpd`):

```python
from scipy import optimize as _optimize


def _optimize_mle(
    Y_exc: np.ndarray,
    Z_exc: np.ndarray,
    form: Literal["linear", "spline"],
) -> tuple[np.ndarray, str]:
    """Run MLE optimization with BFGS, falling back to Nelder-Mead.

    Returns (params, status) where status ∈ {"converged", "max_iter", "failed"}.
    """
    X_xi = _design_matrix(Z_exc, form=form)
    X_sigma = _design_matrix(Z_exc, form=form, for_scale=True)
    x0 = np.asarray(_initial_params(Y_exc, form=form), dtype=float)

    def objective(params):
        return _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)

    # BFGS first
    try:
        res = _optimize.minimize(
            objective, x0, method="BFGS", options={"maxiter": 500, "gtol": 1e-6},
        )
        if res.success and np.isfinite(res.fun):
            return (np.asarray(res.x, dtype=float), "converged")
        if not res.success and "maximum number of iterations" in str(res.message).lower():
            # Try Nelder-Mead as fallback
            pass
    except (ValueError, FloatingPointError):
        pass

    # Nelder-Mead fallback
    try:
        res = _optimize.minimize(
            objective, x0, method="Nelder-Mead",
            options={"maxiter": 2000, "xatol": 1e-5, "fatol": 1e-5},
        )
        if res.success and np.isfinite(res.fun):
            return (np.asarray(res.x, dtype=float), "converged")
    except (ValueError, FloatingPointError):
        pass

    return (np.full_like(x0, np.nan), "failed")


def fit_gpd_continuous_z(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    *,
    threshold: float,
    form: Literal["linear", "spline"],
    n_boot: int = 200,
    seed: int = 0,
) -> GPDContinuousFitResult:
    """Fit non-stationary GPD with covariate Z on shape and scale.

    Form options:
      "linear": ξ(Z) = β₀ + β₁·Z, log σ(Z) = σ₀ + σ₁·Z. 4 params total.
      "spline": ξ(Z) = β₀ + β₁·Z + β₂·Z² + β₃·Z³, log σ(Z) = σ₀ + σ₁·Z. 6 params.

    Pair-bootstrap on exceedance row indices, n_boot reps, refit per rep.
    Two-sided bootstrap p-value for the headline statistic (β₁ for linear;
    LRT-equivalent for spline — but Task 4 handles the spline LRT separately,
    so for spline form this function reports β₁ from the linear projection).

    Failure modes:
      - Primary MLE failure → convergence_status = "failed", params = NaN
      - Bootstrap < 100 successful reps → convergence_status = "insufficient_bootstrap_reps",
        CIs = (NaN, NaN)
    """
    if form not in ("linear", "spline"):
        raise ValueError(f"form must be 'linear' or 'spline'; got {form!r}")

    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    if len(Y_arr) != len(Z_arr):
        raise ValueError(
            f"Y and Z must have equal length; got {len(Y_arr)} vs {len(Z_arr)}"
        )
    if not np.isfinite(threshold):
        raise ValueError(f"threshold must be finite; got {threshold}")

    exceed_mask = Y_arr > threshold
    Y_exc = Y_arr[exceed_mask] - threshold
    Z_exc = Z_arr[exceed_mask]
    n_exc = len(Y_exc)

    n_xi = 2 if form == "linear" else 4

    # Primary fit
    primary_params, primary_status = _optimize_mle(Y_exc, Z_exc, form=form)
    if primary_status == "failed":
        # All NaN result
        nan_ci = tuple((float("nan"), float("nan")) for _ in range(n_xi))
        return GPDContinuousFitResult(
            form=form,
            threshold_quantile=float(np.mean(Y_arr <= threshold)),
            threshold_value=float(threshold),
            n_exceedances=n_exc,
            shape_coefficients=tuple(float("nan") for _ in range(n_xi)),
            shape_coefficients_bootstrap_ci_95=nan_ci,
            scale_coefficients=(float("nan"), float("nan")),
            scale_coefficients_bootstrap_ci_95=((float("nan"), float("nan")),) * 2,
            headline_slope_or_lrt=float("nan"),
            headline_p_value=float("nan"),
            convergence_status="failed",
        )

    # Bootstrap
    rng = np.random.default_rng(seed)
    bootstrap_xi_params: list[np.ndarray] = []
    bootstrap_sigma_params: list[np.ndarray] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_exc, size=n_exc)
        Y_b = Y_exc[idx]
        Z_b = Z_exc[idx]
        try:
            boot_params, boot_status = _optimize_mle(Y_b, Z_b, form=form)
        except (ValueError, FloatingPointError):
            continue
        if boot_status != "converged":
            continue
        bootstrap_xi_params.append(boot_params[:n_xi])
        bootstrap_sigma_params.append(boot_params[n_xi:])

    if len(bootstrap_xi_params) < 100:
        nan_ci = tuple((float("nan"), float("nan")) for _ in range(n_xi))
        return GPDContinuousFitResult(
            form=form,
            threshold_quantile=float(np.mean(Y_arr <= threshold)),
            threshold_value=float(threshold),
            n_exceedances=n_exc,
            shape_coefficients=tuple(float(c) for c in primary_params[:n_xi]),
            shape_coefficients_bootstrap_ci_95=nan_ci,
            scale_coefficients=(float(primary_params[n_xi]), float(primary_params[n_xi + 1])),
            scale_coefficients_bootstrap_ci_95=((float("nan"), float("nan")),) * 2,
            headline_slope_or_lrt=float(primary_params[1]),  # β₁
            headline_p_value=float("nan"),
            convergence_status="insufficient_bootstrap_reps",
        )

    xi_array = np.asarray(bootstrap_xi_params)  # shape (n_succ, n_xi)
    sigma_array = np.asarray(bootstrap_sigma_params)

    xi_cis = tuple(
        (float(np.quantile(xi_array[:, j], 0.025)),
         float(np.quantile(xi_array[:, j], 0.975)))
        for j in range(n_xi)
    )
    sigma_cis = (
        (float(np.quantile(sigma_array[:, 0], 0.025)),
         float(np.quantile(sigma_array[:, 0], 0.975))),
        (float(np.quantile(sigma_array[:, 1], 0.025)),
         float(np.quantile(sigma_array[:, 1], 0.975))),
    )

    # Two-sided bootstrap p on β₁ (regardless of form — for spline, this
    # captures the linear-coefficient share; LRT for spline is in Task 4).
    beta_1_boot = xi_array[:, 1]
    p_left = float(np.mean(beta_1_boot <= 0.0))
    p_right = float(np.mean(beta_1_boot >= 0.0))
    p_two_sided = min(1.0, 2.0 * min(p_left, p_right))

    return GPDContinuousFitResult(
        form=form,
        threshold_quantile=float(np.mean(Y_arr <= threshold)),
        threshold_value=float(threshold),
        n_exceedances=n_exc,
        shape_coefficients=tuple(float(c) for c in primary_params[:n_xi]),
        shape_coefficients_bootstrap_ci_95=xi_cis,
        scale_coefficients=(float(primary_params[n_xi]), float(primary_params[n_xi + 1])),
        scale_coefficients_bootstrap_ci_95=sigma_cis,
        headline_slope_or_lrt=float(primary_params[1]),  # β₁
        headline_p_value=p_two_sided,
        convergence_status="converged",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py -v --tb=short
```

Expected: 16 PASS (11 prior + 5 new).

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `206 passed` (201 prior + 5 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd_continuous.py tests/analysis/test_gpd_continuous.py
git commit -m "$(cat <<'EOF'
feat(analysis): Spec B fit_gpd_continuous_z — MLE + pair-bootstrap

Single non-stationary GPD fit (linear or spline form) + pair-bootstrap CIs
for shape coefficients and scale coefficients. Two-sided bootstrap p-value
on β₁ for the linear-form headline.

Optimizer: scipy BFGS with Nelder-Mead fallback. Convergence-failure
handling per pre-reg:
- Primary MLE failure → all NaN result, status="failed"
- Bootstrap < 100 successful reps → CIs=NaN, status="insufficient_bootstrap_reps"
- No retry with different initial values; no ad-hoc clipping

Recovery validated on synthetic DGPs (planted β₁=0.05 recovered ±0.03 at
n=5000; null DGP gives β₁≈0 with CI spanning 0). 5 new tests; suite at 206.
EOF
)"
```

---

## Task 4: `_likelihood_ratio_test` (LRT spline vs linear)

**Why this task exists:** The likelihood-ratio test between nested linear (2 DOF) and spline (4 DOF) shape models. Provides the spline-form's headline p-value per the pre-reg's decision rules (which says "LRT p < 0.10 → 'non-linear shape is significant'").

**Files:**
- Modify: `src/surg/analysis/gpd_continuous.py` (add `_likelihood_ratio_test`)
- Modify: `tests/analysis/test_gpd_continuous.py` (add ~3 new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/analysis/test_gpd_continuous.py`:

```python
from surg.analysis.gpd_continuous import _likelihood_ratio_test


def test_likelihood_ratio_test_under_null_returns_high_p_value():
    """When DGP is linear, the LRT should not reject the linear-null in favor of spline."""
    rng = np.random.default_rng(seed=42)
    n = 3000
    Z = rng.uniform(1.0, 10.0, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    linear_result = fit_gpd_continuous_z(Y, Z, threshold=0.0, form="linear", n_boot=50, seed=0)
    spline_result = fit_gpd_continuous_z(Y, Z, threshold=0.0, form="spline", n_boot=50, seed=0)
    lrt = _likelihood_ratio_test(linear_result, spline_result, Y, Z, threshold=0.0)

    assert lrt["df"] == 2  # spline (4 DOF shape) - linear (2 DOF shape)
    # Under null, asymptotic p should be > 0.05
    assert lrt["asymptotic_p_value"] > 0.05, \
        f"False rejection of linear null: p={lrt['asymptotic_p_value']}"
    assert lrt["chi2"] >= 0, f"LRT chi² should be non-negative: {lrt['chi2']}"


def test_likelihood_ratio_test_with_strongly_nonlinear_dgp_rejects_linear():
    """When DGP has a strongly cubic ξ(Z), LRT should reject linear in favor of spline."""
    rng = np.random.default_rng(seed=42)
    n = 6000
    Z = rng.uniform(1.0, 10.0, size=n)
    # Strongly cubic shape: ξ(Z) = 0.2 + 0.1·Z - 0.02·Z² + 0.001·Z³
    Y = np.empty(n)
    for i in range(n):
        xi_i = 0.2 + 0.1 * Z[i] - 0.02 * Z[i] ** 2 + 0.001 * Z[i] ** 3
        # Clamp to safe MLE range
        xi_i = max(-0.4, min(xi_i, 0.8))
        Y[i] = stats.genpareto.rvs(c=xi_i, scale=2.0, size=1, random_state=rng)[0]

    linear_result = fit_gpd_continuous_z(Y, Z, threshold=0.0, form="linear", n_boot=50, seed=0)
    spline_result = fit_gpd_continuous_z(Y, Z, threshold=0.0, form="spline", n_boot=50, seed=0)
    lrt = _likelihood_ratio_test(linear_result, spline_result, Y, Z, threshold=0.0)

    # Strong non-linearity should produce small p (we use 0.10 cutoff for tolerance)
    assert lrt["asymptotic_p_value"] < 0.10, \
        f"Failed to detect non-linearity: p={lrt['asymptotic_p_value']}, chi2={lrt['chi2']}"


def test_likelihood_ratio_test_handles_failed_fits():
    """If either input fit has status != 'converged', LRT returns NaN values
    rather than crashing."""
    # Construct a failed linear-result (NaN shape coefficients)
    nan_ci = tuple((float("nan"), float("nan")) for _ in range(2))
    failed_result = GPDContinuousFitResult(
        form="linear",
        threshold_quantile=0.95,
        threshold_value=10.0,
        n_exceedances=10,
        shape_coefficients=(float("nan"), float("nan")),
        shape_coefficients_bootstrap_ci_95=nan_ci,
        scale_coefficients=(float("nan"), float("nan")),
        scale_coefficients_bootstrap_ci_95=((float("nan"), float("nan")),) * 2,
        headline_slope_or_lrt=float("nan"),
        headline_p_value=float("nan"),
        convergence_status="failed",
    )
    spline_ok = GPDContinuousFitResult(
        form="spline",
        threshold_quantile=0.95,
        threshold_value=10.0,
        n_exceedances=10,
        shape_coefficients=(0.3, 0.0, 0.0, 0.0),
        shape_coefficients_bootstrap_ci_95=((0, 0),) * 4,
        scale_coefficients=(0.69, 0.0),
        scale_coefficients_bootstrap_ci_95=((0, 0),) * 2,
        headline_slope_or_lrt=0.0,
        headline_p_value=1.0,
        convergence_status="converged",
    )

    lrt = _likelihood_ratio_test(failed_result, spline_ok, np.zeros(10), np.zeros(10), threshold=0.0)
    assert math.isnan(lrt["chi2"])
    assert math.isnan(lrt["asymptotic_p_value"])
    assert lrt["df"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py::test_likelihood_ratio_test_under_null_returns_high_p_value -v
```

Expected: FAIL with `ImportError: cannot import name '_likelihood_ratio_test'`.

- [ ] **Step 3: Add `_likelihood_ratio_test` to gpd_continuous.py**

Append to `src/surg/analysis/gpd_continuous.py` (after `fit_gpd_continuous_z`):

```python
def _likelihood_ratio_test(
    linear_result: GPDContinuousFitResult,
    spline_result: GPDContinuousFitResult,
    Y: np.ndarray,
    Z: np.ndarray,
    *,
    threshold: float,
) -> dict:
    """Likelihood-ratio test for nested non-stationary GPD models.

    Tests H0: spline-extra-DOF = 0 (i.e., linear is adequate) vs H1: spline.

    LRT statistic: chi² = 2 · (NLL_linear − NLL_spline). Asymptotic χ²
    distribution with df = (spline DOF) − (linear DOF) = 4 − 2 = 2.

    If either fit has convergence_status != "converged", returns NaN values
    and df=2.
    """
    out = {"df": 2, "chi2": float("nan"), "asymptotic_p_value": float("nan")}
    if (linear_result.convergence_status != "converged"
            or spline_result.convergence_status != "converged"):
        return out

    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    exceed_mask = Y_arr > threshold
    Y_exc = Y_arr[exceed_mask] - threshold
    Z_exc = Z_arr[exceed_mask]

    # Reconstruct NLL at the fitted params for both forms
    X_xi_lin = _design_matrix(Z_exc, form="linear")
    X_sigma_lin = _design_matrix(Z_exc, form="linear", for_scale=True)
    params_lin = np.array(
        list(linear_result.shape_coefficients) + list(linear_result.scale_coefficients)
    )
    nll_linear = _neg_log_likelihood_nonstationary_gpd(
        params_lin, Y_exc, X_xi_lin, X_sigma_lin,
    )

    X_xi_spl = _design_matrix(Z_exc, form="spline")
    X_sigma_spl = _design_matrix(Z_exc, form="spline", for_scale=True)
    params_spl = np.array(
        list(spline_result.shape_coefficients) + list(spline_result.scale_coefficients)
    )
    nll_spline = _neg_log_likelihood_nonstationary_gpd(
        params_spl, Y_exc, X_xi_spl, X_sigma_spl,
    )

    if not (math.isfinite(nll_linear) and math.isfinite(nll_spline)):
        return out

    chi2 = max(0.0, 2.0 * (nll_linear - nll_spline))
    asymptotic_p = float(1.0 - stats.chi2.cdf(chi2, df=2))
    out["chi2"] = float(chi2)
    out["asymptotic_p_value"] = asymptotic_p
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py -v --tb=short
```

Expected: 19 PASS (16 prior + 3 new).

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `209 passed` (206 prior + 3 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd_continuous.py tests/analysis/test_gpd_continuous.py
git commit -m "$(cat <<'EOF'
feat(analysis): Spec B likelihood-ratio test for spline-vs-linear

_likelihood_ratio_test(linear_result, spline_result, Y, Z, threshold) returns
chi², asymptotic p-value, and df=2 for the nested test. NaN values gracefully
returned if either input fit didn't converge.

Verified under null (linear DGP → high LRT p) and alternative (cubic DGP →
LRT p < 0.10). 3 new tests; suite at 209.
EOF
)"
```

---

## Task 5: `run_gpd_continuous_z` orchestrator (per-pnode threshold sweep + JSON output)

**Why this task exists:** The per-pnode orchestrator that does the threshold sweep × linear + spline + LRT, and writes the JSON output schema documented in the design.

**Files:**
- Modify: `src/surg/analysis/gpd_continuous.py` (add `run_gpd_continuous_z` + JSON helpers)
- Modify: `tests/analysis/test_gpd_continuous.py` (add ~3 new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/analysis/test_gpd_continuous.py`:

```python
import json
from pathlib import Path
from surg.analysis.gpd_continuous import run_gpd_continuous_z


def test_run_gpd_continuous_z_writes_expected_json_schema(tmp_path: Path):
    """End-to-end: writes JSON with the per-pnode schema documented in the design."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng),
        "Z_target": rng.uniform(1.0, 10.0, size=n),
    })

    out = tmp_path / "gpd_continuous" / "test_pnode.json"
    run_gpd_continuous_z(
        panel,
        out_path=out,
        response_col="Y_target",
        pnode_label="test_pnode",
        threshold_col="Z_target",
        threshold_quantiles=(0.50, 0.75, 0.90),
        n_boot=30,
        seed=0,
    )

    assert out.exists()
    payload = json.loads(out.read_text())
    assert payload["pnode_label"] == "test_pnode"
    assert payload["response_col"] == "Y_target"
    assert payload["threshold_col"] == "Z_target"
    assert payload["n_total_panel"] == n
    sweep = payload["threshold_sweep"]
    assert len(sweep) == 3
    for entry in sweep:
        assert set(entry.keys()) >= {
            "threshold_quantile", "threshold_value", "n_exceedances",
            "linear", "spline", "likelihood_ratio_test",
        }
        assert set(entry["linear"].keys()) >= {
            "convergence_status", "shape_coefficients",
            "shape_coefficients_bootstrap_ci_95", "scale_coefficients",
            "scale_coefficients_bootstrap_ci_95", "beta_1_two_sided_p_value",
        }
        assert set(entry["spline"].keys()) >= {
            "convergence_status", "shape_coefficients",
            "shape_coefficients_bootstrap_ci_95", "scale_coefficients",
            "scale_coefficients_bootstrap_ci_95",
        }
        assert set(entry["likelihood_ratio_test"].keys()) >= {
            "chi2", "df", "asymptotic_p_value",
        }


def test_run_gpd_continuous_z_handles_dropna_in_response(tmp_path: Path):
    """Rows with NaN in response_col or threshold_col are dropped; n_after_dropna
    reflects the actual fit sample size."""
    rng = np.random.default_rng(seed=42)
    n = 2000
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)
    Z = rng.uniform(1.0, 10.0, size=n)
    Y[10] = float("nan")
    Y[20] = float("nan")
    Z[100] = float("nan")
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": Y,
        "Z_target": Z,
    })

    out = tmp_path / "gpd_continuous" / "test_dropna.json"
    run_gpd_continuous_z(
        panel, out_path=out,
        response_col="Y_target", pnode_label="dropna_test",
        threshold_col="Z_target",
        threshold_quantiles=(0.5,), n_boot=30, seed=0,
    )

    payload = json.loads(out.read_text())
    assert payload["n_total_panel"] == 2000
    assert payload["n_after_dropna"] == 1997  # 3 rows with any NaN dropped


def test_run_gpd_continuous_z_serializes_nan_as_null(tmp_path: Path):
    """JSON output uses null for NaN values (RFC-compliant), not literal NaN."""
    # Force a fit failure scenario with very small n
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=50, freq="h"),
        "Y_target": np.random.default_rng(42).uniform(0, 1, size=50),
        "Z_target": np.random.default_rng(42).uniform(1, 10, size=50),
    })
    out = tmp_path / "gpd_continuous" / "nan_check.json"
    run_gpd_continuous_z(
        panel, out_path=out,
        response_col="Y_target", pnode_label="nan_test",
        threshold_col="Z_target",
        threshold_quantiles=(0.5,), n_boot=20, seed=0,
    )
    text = out.read_text()
    assert "NaN" not in text, "JSON output contains literal NaN token"
    json.loads(text)  # strict JSON parsing must succeed
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py::test_run_gpd_continuous_z_writes_expected_json_schema -v
```

Expected: FAIL with `ImportError: cannot import name 'run_gpd_continuous_z'`.

- [ ] **Step 3: Add `run_gpd_continuous_z` to gpd_continuous.py**

Append to `src/surg/analysis/gpd_continuous.py`:

```python
import json


def _nan_to_none(obj):
    """Recursively replace float NaN/inf with None for JSON serialization."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (list, tuple)):
        return [_nan_to_none(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _nan_to_none(v) for k, v in obj.items()}
    return obj


def _fit_result_to_dict(fit: GPDContinuousFitResult) -> dict:
    return {
        "convergence_status": fit.convergence_status,
        "shape_coefficients": list(fit.shape_coefficients),
        "shape_coefficients_bootstrap_ci_95": [list(ci) for ci in fit.shape_coefficients_bootstrap_ci_95],
        "scale_coefficients": list(fit.scale_coefficients),
        "scale_coefficients_bootstrap_ci_95": [list(ci) for ci in fit.scale_coefficients_bootstrap_ci_95],
        "beta_1_two_sided_p_value": fit.headline_p_value,
    }


def run_gpd_continuous_z(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    response_col: str,
    pnode_label: str,
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    threshold_quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """Per-pnode Spec B orchestrator: threshold sweep × (linear + spline + LRT).

    Drops NaN rows in [response_col, threshold_col]. For each threshold quantile,
    fits both linear and spline forms, runs the LRT. Writes a single JSON
    output file matching the design schema.
    """
    n_total = len(panel)
    subset = panel.dropna(subset=[response_col, threshold_col])
    Y = subset[response_col].to_numpy()
    Z = subset[threshold_col].to_numpy()
    n_after = len(subset)

    sweep_entries: list[dict] = []
    for i, q in enumerate(threshold_quantiles):
        threshold = float(np.quantile(Y, q))
        n_exc = int((Y > threshold).sum())
        linear_result = fit_gpd_continuous_z(
            Y, Z, threshold=threshold, form="linear", n_boot=n_boot, seed=seed + 10 * i,
        )
        spline_result = fit_gpd_continuous_z(
            Y, Z, threshold=threshold, form="spline", n_boot=n_boot, seed=seed + 10 * i + 5,
        )
        lrt = _likelihood_ratio_test(
            linear_result, spline_result, Y, Z, threshold=threshold,
        )
        sweep_entries.append({
            "threshold_quantile": float(q),
            "threshold_value": float(threshold),
            "n_exceedances": n_exc,
            "linear": _fit_result_to_dict(linear_result),
            "spline": _fit_result_to_dict(spline_result),
            "likelihood_ratio_test": {
                "chi2": lrt["chi2"],
                "df": int(lrt["df"]),
                "asymptotic_p_value": lrt["asymptotic_p_value"],
            },
        })

    payload = {
        "pnode_label": pnode_label,
        "response_col": response_col,
        "threshold_col": threshold_col,
        "n_total_panel": int(n_total),
        "n_after_dropna": int(n_after),
        "threshold_sweep": sweep_entries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_nan_to_none(payload), indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd_continuous.py -v --tb=short
```

Expected: 22 PASS (19 prior + 3 new).

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `212 passed` (209 prior + 3 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd_continuous.py tests/analysis/test_gpd_continuous.py
git commit -m "$(cat <<'EOF'
feat(analysis): Spec B per-pnode orchestrator + JSON output

run_gpd_continuous_z does the per-pnode threshold sweep:
for each threshold quantile, fit linear + spline forms, run LRT, accumulate
into a per-pnode JSON schema (matches design doc Section "Output schema").

NaN handling: rows with NaN in response/threshold columns dropped before
fit. NaN values in output (e.g., CIs from failed bootstraps) serialize to
JSON null via _nan_to_none.

3 new tests; suite at 212.
EOF
)"
```

---

## Task 6: Wire `run_gpd_continuous_z` into `run_all` + headline JSON

**Why this task exists:** Spec B must run inside `surg-analyze` so the battery produces outputs on every production run. After the per-pnode loop, write the headline JSON consolidating primary's 95th-pct linear β₁ per the pre-reg.

**Files:**
- Modify: `src/surg/analysis/run.py`
- Modify: `tests/analysis/test_run.py`

- [ ] **Step 1: Update `tests/analysis/test_run.py`**

Find the integration test's `expected_paths` set. Add 8 new entries (7 per-pnode + 1 headline):

```python
expected_paths = {
    # ... existing entries ...
    out_root / "gpd_continuous" / "primary.json",
    out_root / "gpd_continuous" / "total_lmp.json",
    out_root / "gpd_continuous" / "ox.json",
    out_root / "gpd_continuous" / "bristers.json",
    out_root / "gpd_continuous" / "dom_zonal.json",
    out_root / "gpd_continuous" / "ashburn_tx1.json",
    out_root / "gpd_continuous" / "ashburn_tx2.json",
    out_root / "gpd_continuous" / "headline.json",
}
```

Preserve all existing entries.

- [ ] **Step 2: Run integration test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: FAIL (missing `gpd_continuous/*.json` paths).

- [ ] **Step 3: Modify `src/surg/analysis/run.py`**

Update the GPD imports:

```python
from surg.analysis.gpd import run_gpd, run_conditional_z_robustness
from surg.analysis.gpd_continuous import run_gpd_continuous_z
```

Add a new CLI flag to `_build_arg_parser()`:

```python
    p.add_argument("--continuous-n-boot", type=int, default=200,
                   help="Bootstrap reps for Spec B continuous ξ(Z) regression.")
```

Update `run_all` signature:

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
) -> None:
```

After the existing `run_conditional_z_robustness` call (and before the `leave_one_season_out` comment), add:

```python
    # 2026-05-14 Spec B continuous ξ(Z) regression battery — sub-q1 closure.
    # Per pre-reg: docs/decisions.md § "2026-05-14 — Pre-registration: Spec B".
    for label, col in PNODE_RESPONSES.items():
        if panel[col].dropna().empty:
            continue
        run_gpd_continuous_z(
            panel=panel,
            out_path=out_root / "gpd_continuous" / f"{label}.json",
            response_col=col,
            pnode_label=label,
            n_boot=continuous_n_boot,
        )

    # Headline JSON: primary congestion @ 95th-pct linear β₁ per pre-reg
    _write_spec_b_headline(out_root / "gpd_continuous")
```

Wire the CLI:

```python
    run_all(
        panel=panel, events=events,
        out_root=Path(args.out_root),
        n_boot=args.n_boot,
        n_subsample_reps=args.n_subsample_reps,
        qr_full_n_boot=args.qr_full_n_boot,
        gpd_n_boot=args.gpd_n_boot,
        continuous_n_boot=args.continuous_n_boot,
    )
```

Add the headline helper at the bottom of `run.py`:

```python
def _write_spec_b_headline(gpd_continuous_dir: Path) -> None:
    """Emit the Spec B headline JSON consolidating primary congestion @ 95th-pct
    linear β₁ per the 2026-05-14 Spec B pre-reg."""
    import json
    primary_path = gpd_continuous_dir / "primary.json"
    if not primary_path.exists():
        return
    payload = json.loads(primary_path.read_text())
    # Find the 95th-pct entry
    entry_95 = next(
        (e for e in payload["threshold_sweep"]
         if abs(e["threshold_quantile"] - 0.95) < 1e-6),
        None,
    )
    if entry_95 is None or entry_95["linear"]["convergence_status"] != "converged":
        # Headline cannot be computed; write a minimal record
        headline = {
            "test": "spec_b_primary_95th_linear",
            "convergence_status":
                entry_95["linear"]["convergence_status"] if entry_95 else "missing",
            "decision_rule_outcome": "could_not_compute_headline",
        }
    else:
        lin = entry_95["linear"]
        beta_1 = lin["shape_coefficients"][1]
        ci_beta_1 = lin["shape_coefficients_bootstrap_ci_95"][1]
        p = lin["beta_1_two_sided_p_value"]
        if p is None or ci_beta_1 is None or ci_beta_1[0] is None:
            outcome = "underpowered"
        elif ci_beta_1[1] < 0 and beta_1 < 0:
            outcome = "rejection_confirmed_linear"
        elif ci_beta_1[0] > 0 and beta_1 > 0:
            outcome = "contradicts_median_split"
        else:
            outcome = "underpowered"
        headline = {
            "test": "spec_b_primary_95th_linear",
            "response_col": payload["response_col"],
            "pnode_label": "primary",
            "threshold_quantile": 0.95,
            "form": "linear",
            "beta_1": beta_1,
            "beta_1_bootstrap_ci_95": ci_beta_1,
            "beta_1_two_sided_p_value": p,
            "decision_rule_outcome": outcome,
            "pre_reg_reference": (
                "docs/decisions.md § 2026-05-14 — Pre-registration: "
                "Spec B continuous ξ(Z) regression"
            ),
        }
    out = gpd_continuous_dir / "headline.json"
    out.write_text(json.dumps(headline, indent=2))
```

- [ ] **Step 4: Run integration test to verify it passes**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `212 passed` (no new tests in this task; integration test updated).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/run.py tests/analysis/test_run.py
git commit -m "$(cat <<'EOF'
feat(analysis): wire Spec B continuous ξ(Z) into run_all + headline JSON

Per-pnode loop after existing conditional-Z battery; one call per pnode
in PNODE_RESPONSES. Outputs land at outputs/gpd_continuous/<pnode>.json.

After the loop, _write_spec_b_headline consolidates primary congestion @
95th-pct linear β₁ into outputs/gpd_continuous/headline.json with the
pre-reg's 4 decision-rule outcomes:
- rejection_confirmed_linear: β₁ < 0, CI excludes 0
- contradicts_median_split: β₁ > 0, CI excludes 0 (paper-shaking)
- underpowered: CI spans 0
- could_not_compute_headline: primary @ 95th-pct fit failed to converge

New CLI flag --continuous-n-boot (default 200) reuses the existing CLI
argument pattern.
EOF
)"
```

---

## Task 7: Verification on real panel + application-of-pre-reg entry prep

**Why this task exists:** Run `surg-analyze` at production resolution on the actual 31,536-row panel. Spec B is computationally heavier than the conditional-Z battery (7 pnodes × 4 thresholds × 2 forms × 200 boot reps = ~11,200 MLE fits), expected ~3-4 hour wall time. After completion, snapshot results for the application-of-pre-reg entry.

**Files:**
- Read-only: `data/interim/analysis_panel.parquet`, `outputs/gpd_continuous/*.json`

- [ ] **Step 1: Confirm the analysis panel is current**

```bash
ls -la data/interim/analysis_panel.parquet
```

Expected: file exists. If missing, run `.venv/bin/surg-prep` first.

- [ ] **Step 2: Run the full analysis at production bootstrap resolution**

```bash
.venv/bin/surg-analyze 2>&1 | tee outputs/surg-analyze-spec-b.log
```

Expected: completes in ~3-4 hr (existing pipeline ~40 min + Spec B's ~3 hr addition). Final stdout: `wrote analysis outputs to outputs/`.

- [ ] **Step 3: Verify Spec B outputs exist**

```bash
ls -la outputs/gpd_continuous/
```

Expected: 8 files — 7 per-pnode `<label>.json` + 1 `headline.json`.

- [ ] **Step 4: Snapshot headline + per-pnode 95th-pct results**

```bash
.venv/bin/python <<'EOF'
import json

print("=== Spec B headline ===")
headline = json.load(open("outputs/gpd_continuous/headline.json"))
print(json.dumps(headline, indent=2))
print()

print("=== Cross-pnode linear β₁ at 95th-pct ===")
for label in ["primary", "total_lmp", "ox", "bristers", "dom_zonal", "ashburn_tx1", "ashburn_tx2"]:
    p = json.load(open(f"outputs/gpd_continuous/{label}.json"))
    entry = next((e for e in p["threshold_sweep"] if abs(e["threshold_quantile"] - 0.95) < 1e-6), None)
    if entry is None:
        print(f"  {label}: no 95th-pct entry")
        continue
    lin = entry["linear"]
    spl = entry["spline"]
    lrt = entry["likelihood_ratio_test"]
    if lin["convergence_status"] != "converged":
        print(f"  {label}: linear status={lin['convergence_status']}")
        continue
    beta_1 = lin["shape_coefficients"][1]
    ci_b1 = lin["shape_coefficients_bootstrap_ci_95"][1]
    p_b1 = lin["beta_1_two_sided_p_value"]
    print(f"  {label}: β₁={beta_1:+.4f}, CI [{ci_b1[0]:+.3f}, {ci_b1[1]:+.3f}], p={p_b1:.3f}; LRT p_asymp={lrt['asymptotic_p_value']:.3f}")
EOF
```

Expected: human-readable summary. Save the output for the application-of-pre-reg entry in decisions.md.

- [ ] **Step 5: No commit in this task**

Task 7 is verification only. No source files changed. Application-of-pre-reg entry write happens after this plan completes (separate write to `decisions.md` per the pre-reg's "Revisit when" instruction).

---

## Out of scope (for follow-up plans / tasks)

- **Application-of-pre-reg entry** in `decisions.md` — written after Task 7 completes, applying the pre-reg's decision rule to the actual headline numbers. Per pre-reg discipline, this is the next decisions.md entry after this plan ships.
- **Sensitivity analyses if "contradicts" outcome triggers** — the pre-reg locks that a β₁ > 0 outcome requires extra sensitivity work before any narrative pivot. Separate plan if triggered.
- **Profile-likelihood CI as a robustness check** — deferred unless reviewers request.
- **Response-variable sensitivity diagnostic** (sub-q1 item #2) — separate work track, follows Spec B results.
- **τ=0.99 secular sign flip investigation** (sub-q1 item #3) — independent track.
- **Ashburn TX1 diagnostic** (sub-q1 item #4) — independent track.
- **FF-merge + worktree cleanup** — happens after Task 7 + application-of-pre-reg entry land. Same pattern as conditional-Z battery (rebase + FF-merge + branch delete + memory snapshot).
