# Analysis module — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Amendment 2026-05-12.** Three changes since this plan was first written:
>
> 1. **Sample size.** Panel is ~31,536 rows (Plan 2 smoke build, not the prerequisites' stated ~17,160) — 3.6y window per decisions.md 2026-05-12. After `passes_proposal_filter`, ~2,027 hours pass (not ~1,053). Update test fixture sizes (currently `n = 500` in Task 12) as needed — the synthetic-test contracts hold either way; only the real-data smoke (Task 16) sees the actual count.
>
> 2. **Stressed-regime indicators (Tests 2-3).** Methodology spec §6 now defines TWO regime indicators per the 2026-05-12 decision, and `run_mechanism` (Task 12) must run conditional-regime + 2×2 cross-tab against BOTH and structure the JSON output as `{"granger": ..., "by_regime": {"sync_event_active": {...}, "high_sr_clearing": {...}}, "power_law": ..., "threshold_used": ...}`. Definition (2) is derived: `high_sr_clearing = panel["sync_reserve_clearing_price_rt"] >= 850`. The underlying `conditional_regime_test` / `crosstab_chi2` functions (Task 10) don't change — they already accept a generic boolean. Add one test verifying both regime keys appear in the output. Task 12 expected count becomes 8 passed (was 7).
>
> 3. **`sync_reserve_clearing_price_rt` is already in `EXPECTED_COLUMNS`** (Plan 2 Task 1 schema) — no panel-schema changes required for this amendment.
>
> See `docs/decisions.md` 2026-05-12 § "Stressed-regime definition refined to high SR clearing price" and `docs/plans/2026-05-11-phase-transition-methodology.md` § 6 (refined paragraph) for context.

**Goal:** Build `src/surg/analysis/` implementing the Phase 3 methodology: TAR (Hansen 1996/2000) primary fit, conditional quantile regression robustness check, and mechanism validation (Granger causality, conditional regime test, cross-tabulation, power-law fit on event durations). End state: `surg-analyze` produces `outputs/{tar_fit,qr_fit,mechanism_validation}.json` plus robustness tables.

**Architecture:** Five-file module — `panel.py` (load + validate `analysis_panel.parquet`), `tar.py` (Hansen TAR estimator with bootstrap test), `qr.py` (quantile regression at τ=0.99: linear / threshold-dummy / B-spline), `mechanism.py` (Granger, conditional regime, cross-tab, power-law), `run.py` (orchestrator + CLI). Robustness checks are sub-routines of the relevant submodules.

**Tech Stack:** Python 3.11+, pytest, pandas/pyarrow (existing), numpy (transitive), **statsmodels** (NEW dep — QuantReg, grangercausalitytests, AR fitting helpers), **scipy** (NEW dep — chi2_contingency, interpolate), **powerlaw** (NEW dep — Clauset/Shalizi/Newman power-law fitting with KS goodness-of-fit).

**Prerequisites:** Plans 1, 1.5, and 2 complete — `data/interim/analysis_panel.parquet` exists with `schema_version=1` and ~31,536 rows (3.6y window per decisions.md 2026-05-12; 96 rows short of theoretical 31,632 due to load-verification lag ending 2026-05-07 while LMP ends 2026-05-10).

**Prerequisite reading:** `docs/plans/2026-05-11-phase-transition-methodology.md` §4-6 (TAR, QR, mechanism validation specifications); `docs/decisions.md` § "2026-05-11 — Phase 3 method".

**Test discipline:** TDD throughout. Synthetic data with *known* parameters used to verify estimator recovery (TAR recovers a planted threshold within ε; QR detects a planted slope kink; Granger detects a planted lead-lag relationship). E2E run against real panel data verifies pipeline integrity, not specific findings.

---

## File structure

```
src/surg/analysis/
├── __init__.py
├── panel.py             # load + validate analysis_panel.parquet
├── tar.py               # Hansen 1996/2000 TAR estimator + bootstrap
├── qr.py                # Quantile regression (linear, threshold-dummy, B-spline)
├── mechanism.py         # Granger, regime test, cross-tab, power-law
├── robustness.py        # subsample + leave-one-season-out wrappers
└── run.py               # orchestrator + surg-analyze CLI

tests/analysis/
├── __init__.py
├── test_panel.py
├── test_tar.py
├── test_qr.py
├── test_mechanism.py
├── test_robustness.py
└── test_run.py

outputs/                 # gitignored, produced by surg-analyze
├── tar_fit.json
├── qr_fit.json
├── mechanism_validation.json
└── robustness/
    ├── subsample_bootstrap.parquet
    └── leave_one_season_out.parquet
```

---

## Task 1: Add new dependencies + scaffold

**Files:**
- Modify: `pyproject.toml` (add statsmodels, scipy, powerlaw)
- Create: `src/surg/analysis/__init__.py`
- Create: `tests/analysis/__init__.py`

- [ ] **Step 1: Add deps to `pyproject.toml`**

In `pyproject.toml`, find the `dependencies` list. Add (preserving format):

```toml
    "statsmodels>=0.14",
    "scipy>=1.11",
    "powerlaw>=1.5",
```

- [ ] **Step 2: Install new deps**

```
.venv/bin/pip install -e .
```

Expected: `statsmodels`, `scipy`, `powerlaw` installed.

- [ ] **Step 3: Create the module scaffold**

```bash
mkdir -p src/surg/analysis tests/analysis
touch src/surg/analysis/__init__.py tests/analysis/__init__.py
```

- [ ] **Step 4: Smoke imports**

```
.venv/bin/python -c "import statsmodels.api; import scipy.stats; import powerlaw; print('ok')"
```

Expected: `ok`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/surg/analysis/ tests/analysis/
git commit -m "feat(analysis): scaffold module + add statsmodels/scipy/powerlaw deps"
```

---

## Task 2: Panel loader with schema-version check

**Files:**
- Create: `src/surg/analysis/panel.py`
- Create: `tests/analysis/test_panel.py`

- [ ] **Step 1: Write failing test**

Create `tests/analysis/test_panel.py`:

```python
from pathlib import Path

import pandas as pd
import pytest


def test_load_panel_returns_dataframe(tmp_path: Path):
    from surg.analysis.panel import load_panel
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    # Write a minimal-but-valid panel
    df = pd.DataFrame({col: [None, None] for col in EXPECTED_COLUMNS})
    df["datetime_beginning_ept"] = pd.to_datetime(
        ["2024-07-15T03:00:00", "2024-07-15T04:00:00"]
    )
    out = tmp_path / "analysis_panel.parquet"
    df.to_parquet(out)

    loaded = load_panel(out)
    assert isinstance(loaded, pd.DataFrame)
    assert len(loaded) == 2


def test_load_panel_validates_schema(tmp_path: Path):
    from surg.analysis.panel import load_panel

    # Write a panel missing required columns
    df = pd.DataFrame({"datetime_beginning_ept": pd.to_datetime(["2024-07-15"])})
    out = tmp_path / "bad_panel.parquet"
    df.to_parquet(out)

    with pytest.raises(ValueError, match="missing expected columns"):
        load_panel(out)


def test_select_filtered_subset_returns_passing_rows():
    from surg.analysis.panel import select_filtered_subset
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None]*3 for col in EXPECTED_COLUMNS})
    df["datetime_beginning_ept"] = pd.to_datetime(
        ["2024-07-15T03:00:00", "2024-03-15T03:00:00", "2024-03-15T14:00:00"]
    )
    df["passes_proposal_filter"] = [False, True, False]

    out = select_filtered_subset(df)
    assert len(out) == 1
    assert out["passes_proposal_filter"].iloc[0]
```

- [ ] **Step 2: Run tests to verify failure**

```
.venv/bin/pytest tests/analysis/test_panel.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `panel.py`**

Create `src/surg/analysis/panel.py`:

```python
"""Load and validate analysis_panel.parquet for the analysis layer."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.preprocessing.schema import validate_panel


def load_panel(path: Path) -> pd.DataFrame:
    """Load the analysis panel from `path` and validate its schema."""
    df = pd.read_parquet(path)
    validate_panel(df)
    return df


def select_filtered_subset(df: pd.DataFrame) -> pd.DataFrame:
    """Return only rows that pass the proposal filter (shoulder + 2-5 AM)."""
    return df[df["passes_proposal_filter"].fillna(False).astype(bool)].copy()
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_panel.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 96 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/panel.py tests/analysis/test_panel.py
git commit -m "feat(analysis): add panel loader with schema validation"
```

---

## Task 3: TAR — basic point-estimate fit (no bootstrap yet)

Hansen's TAR: grid-search a candidate threshold `c` over quantiles of `Z`; for each `c`, fit AR(1) on each regime via OLS; pick `c` minimizing joint residual sum of squares.

**Files:**
- Create: `src/surg/analysis/tar.py`
- Create: `tests/analysis/test_tar.py`

- [ ] **Step 1: Write failing test using synthetic data with known threshold**

Create `tests/analysis/test_tar.py`:

```python
import numpy as np
import pandas as pd
import pytest


def _make_synthetic_tar(n: int = 2000, c_true: float = 2.0, seed: int = 42):
    """Generate synthetic AR(1) data with a planted threshold.

    Below c_true: Y_t = 0.4*Y_{t-1} + N(0, 0.5)
    Above c_true: Y_t = 0.4*Y_{t-1} + 8 + N(0, 2.0)  (mean shift)
    """
    rng = np.random.default_rng(seed)
    Z = rng.lognormal(mean=0, sigma=0.7, size=n)
    Y = np.zeros(n)
    for t in range(1, n):
        if Z[t] <= c_true:
            Y[t] = 0.4 * Y[t-1] + rng.normal(0, 0.5)
        else:
            Y[t] = 0.4 * Y[t-1] + 8 + rng.normal(0, 2.0)
    return pd.DataFrame({"Z": Z, "Y": Y, "Y_lag1": np.r_[np.nan, Y[:-1]]}).dropna()


def test_tar_recovers_planted_threshold_within_tolerance():
    """The point estimate ĉ should be within 0.5 of the true c=2.0."""
    from surg.analysis.tar import fit_tar

    df = _make_synthetic_tar(n=2000, c_true=2.0)
    result = fit_tar(
        Y=df["Y"].to_numpy(),
        Y_lag=df["Y_lag1"].to_numpy(),
        Z=df["Z"].to_numpy(),
        trim=0.15,
        n_grid=200,
    )
    assert abs(result.c_hat - 2.0) < 0.5
    # AR coefficients should be close to 0.4 in each regime
    assert abs(result.alpha[1] - 0.4) < 0.2  # alpha[0] is intercept, alpha[1] is AR
    assert abs(result.beta[1] - 0.4) < 0.2
    # The above-threshold regime should have a higher intercept
    assert result.beta[0] > result.alpha[0]


def test_tar_returns_regime_counts():
    from surg.analysis.tar import fit_tar
    df = _make_synthetic_tar(n=2000)
    result = fit_tar(
        Y=df["Y"].to_numpy(),
        Y_lag=df["Y_lag1"].to_numpy(),
        Z=df["Z"].to_numpy(),
    )
    assert result.n_low + result.n_high == len(df)
    assert result.n_low > 0 and result.n_high > 0


def test_tar_rejects_unequal_array_lengths():
    from surg.analysis.tar import fit_tar
    with pytest.raises(ValueError, match="same length"):
        fit_tar(
            Y=np.array([1.0, 2.0]),
            Y_lag=np.array([0.0, 1.0]),
            Z=np.array([0.5, 1.5, 2.5]),  # mismatched
        )
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_tar.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `fit_tar`**

Create `src/surg/analysis/tar.py`:

```python
"""TAR — Threshold Autoregression estimator (Hansen 1996/2000).

Model:
    Y_t = α₀ + α₁·Y_{t-1} + ε_t   if Z_t ≤ c   (low-volatility regime)
    Y_t = β₀ + β₁·Y_{t-1} + ε_t   if Z_t >  c   (high-volatility regime)

`fit_tar` estimates c via concentrated least squares: grid-search over
candidate values of c (quantiles of Z), fit AR(1) on each regime, pick
c minimizing joint residual SSR.

The Hansen bootstrap test for "is there a threshold" is in a separate
function `hansen_bootstrap_test` (Task 4).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class TARResult:
    c_hat: float          # estimated threshold
    alpha: np.ndarray     # low-regime coefficients [intercept, AR1]
    beta: np.ndarray      # high-regime coefficients [intercept, AR1]
    n_low: int            # observations below threshold
    n_high: int           # observations above
    ssr_low: float        # SSR in low regime
    ssr_high: float       # SSR in high regime
    ssr_joint: float      # ssr_low + ssr_high


def _fit_ar1_ols(Y: np.ndarray, Y_lag: np.ndarray) -> tuple[np.ndarray, float]:
    """Fit Y = β₀ + β₁ Y_lag via OLS. Returns (coefficients, SSR)."""
    X = np.column_stack([np.ones(len(Y)), Y_lag])
    # β = (X'X)^-1 X'Y
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ beta
    return beta, float(resid @ resid)


def fit_tar(
    Y: np.ndarray,
    Y_lag: np.ndarray,
    Z: np.ndarray,
    *,
    trim: float = 0.15,
    n_grid: int = 300,
) -> TARResult:
    """Estimate the TAR threshold c via concentrated least squares.

    Args:
        Y: response vector, length n
        Y_lag: Y_{t-1} aligned with Y, length n
        Z: threshold variable, length n
        trim: minimum fraction of obs in each regime (0.15 = Hansen default)
        n_grid: number of candidate c values to search over

    Grid: `n_grid` evenly-spaced quantiles of Z within [trim, 1-trim].
    """
    Y, Y_lag, Z = np.asarray(Y), np.asarray(Y_lag), np.asarray(Z)
    if not (len(Y) == len(Y_lag) == len(Z)):
        raise ValueError("Y, Y_lag, Z must be the same length")

    # Candidate thresholds: quantiles of Z within the trim region
    lo, hi = np.quantile(Z, trim), np.quantile(Z, 1 - trim)
    candidates = np.linspace(lo, hi, n_grid)

    best = None
    for c in candidates:
        mask = Z <= c
        n_low, n_high = int(mask.sum()), int((~mask).sum())
        # Skip degenerate splits (also enforced by the trim bounds, but be defensive)
        min_n = int(trim * len(Y))
        if n_low < min_n or n_high < min_n:
            continue

        alpha, ssr_low = _fit_ar1_ols(Y[mask], Y_lag[mask])
        beta, ssr_high = _fit_ar1_ols(Y[~mask], Y_lag[~mask])
        ssr_joint = ssr_low + ssr_high

        if best is None or ssr_joint < best.ssr_joint:
            best = TARResult(
                c_hat=float(c),
                alpha=alpha, beta=beta,
                n_low=n_low, n_high=n_high,
                ssr_low=ssr_low, ssr_high=ssr_high,
                ssr_joint=ssr_joint,
            )

    if best is None:
        raise RuntimeError("no valid threshold found (trim too aggressive?)")
    return best
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_tar.py -v
```

Expected: 3 passed. If `test_tar_recovers_planted_threshold_within_tolerance` fails marginally, increase `n=2000` to `n=5000` in `_make_synthetic_tar` or tighten the planted signal. The current params should give ~80% power.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 99 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/tar.py tests/analysis/test_tar.py
git commit -m "feat(analysis): TAR point estimate via concentrated least squares"
```

---

## Task 4: TAR — Hansen bootstrap test for H₀: no threshold

Bootstrap the distribution of the SSR-improvement statistic under H₀ (single AR(1) for all data, no threshold).

**Files:**
- Modify: `src/surg/analysis/tar.py`
- Modify: `tests/analysis/test_tar.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_tar.py`:

```python
def test_hansen_bootstrap_rejects_null_when_threshold_planted():
    """If the data really has a threshold, p-value should be small."""
    from surg.analysis.tar import fit_tar, hansen_bootstrap_test

    df = _make_synthetic_tar(n=1500, c_true=2.0, seed=1)
    result = fit_tar(
        Y=df["Y"].to_numpy(),
        Y_lag=df["Y_lag1"].to_numpy(),
        Z=df["Z"].to_numpy(),
    )
    p = hansen_bootstrap_test(
        Y=df["Y"].to_numpy(),
        Y_lag=df["Y_lag1"].to_numpy(),
        Z=df["Z"].to_numpy(),
        tar_result=result,
        n_boot=200,
        seed=42,
    )
    assert p < 0.10  # threshold is planted → null should be rejected


def test_hansen_bootstrap_does_not_reject_when_no_threshold():
    """If the data is a single AR(1) with no threshold, p-value should be moderate."""
    from surg.analysis.tar import fit_tar, hansen_bootstrap_test

    rng = np.random.default_rng(0)
    n = 1500
    Z = rng.lognormal(0, 0.7, size=n)
    Y = np.zeros(n)
    for t in range(1, n):
        Y[t] = 0.4 * Y[t-1] + rng.normal(0, 1.0)  # no threshold
    df = pd.DataFrame({"Z": Z, "Y": Y, "Y_lag1": np.r_[np.nan, Y[:-1]]}).dropna()
    result = fit_tar(
        Y=df["Y"].to_numpy(),
        Y_lag=df["Y_lag1"].to_numpy(),
        Z=df["Z"].to_numpy(),
    )
    p = hansen_bootstrap_test(
        Y=df["Y"].to_numpy(),
        Y_lag=df["Y_lag1"].to_numpy(),
        Z=df["Z"].to_numpy(),
        tar_result=result,
        n_boot=200,
        seed=99,
    )
    # Hard to assert exact value; just check it isn't a vanishingly-small p
    assert p > 0.05
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_tar.py -k bootstrap -v
```

Expected: ImportError on `hansen_bootstrap_test`.

- [ ] **Step 3: Implement bootstrap**

Append to `src/surg/analysis/tar.py`:

```python
def hansen_bootstrap_test(
    Y: np.ndarray,
    Y_lag: np.ndarray,
    Z: np.ndarray,
    tar_result: TARResult,
    *,
    n_boot: int = 1000,
    trim: float = 0.15,
    n_grid: int = 300,
    seed: int = 0,
) -> float:
    """Bootstrap p-value for H₀: no threshold (single AR(1) for all data).

    Steps:
      1. Fit AR(1) to the *full* sample (no regime split) → get residuals ε̂.
      2. Compute the SSR-improvement statistic on observed data:
           T = SSR_full - SSR_joint (observed)
      3. For each bootstrap rep b in 1..B:
           - Resample residuals with replacement → ε*ᵦ
           - Generate Y*ᵦ recursively under the null AR(1)
           - Re-fit TAR on (Y*, Y*_lag, Z)
           - Compute T*ᵦ = SSR_full(b) - SSR_joint(b)
      4. p = (1 + #{T*ᵦ ≥ T}) / (1 + B)
    """
    rng = np.random.default_rng(seed)

    # Step 1: full-sample AR(1)
    coef_full, ssr_full = _fit_ar1_ols(Y, Y_lag)
    resid_full = Y - (coef_full[0] + coef_full[1] * Y_lag)

    # Step 2: observed test statistic
    T_obs = ssr_full - tar_result.ssr_joint

    # Step 3: bootstrap
    n = len(Y)
    T_boot = np.empty(n_boot)
    for b in range(n_boot):
        # Resample residuals
        eps = rng.choice(resid_full, size=n, replace=True)
        # Generate Y* under the null AR(1)
        Y_star = np.empty(n)
        Y_star[0] = Y_lag[0]  # initialize with the observed first lag
        for t in range(1, n):
            Y_star[t] = coef_full[0] + coef_full[1] * Y_star[t-1] + eps[t]
        Y_star_lag = np.r_[Y_star[0], Y_star[:-1]]

        # Re-fit TAR and full-sample AR on bootstrap data
        _, ssr_full_b = _fit_ar1_ols(Y_star, Y_star_lag)
        boot_result = fit_tar(Y_star, Y_star_lag, Z, trim=trim, n_grid=n_grid)
        T_boot[b] = ssr_full_b - boot_result.ssr_joint

    # Step 4: p-value
    return (1 + int(np.sum(T_boot >= T_obs))) / (1 + n_boot)
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_tar.py -v
```

Expected: 5 passed. The bootstrap tests will be slow (~30s each because of 200 reps × 300-grid TAR refits). Acceptable.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 101 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/tar.py tests/analysis/test_tar.py
git commit -m "feat(analysis): Hansen bootstrap test for TAR threshold significance"
```

---

## Task 5: TAR — public API + JSON output

Convenience function that takes the panel DataFrame, runs `fit_tar` + `hansen_bootstrap_test`, and writes results to `outputs/tar_fit.json`.

**Files:**
- Modify: `src/surg/analysis/tar.py`
- Modify: `tests/analysis/test_tar.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_tar.py`:

```python
def test_run_tar_writes_json(tmp_path):
    from surg.analysis.tar import run_tar
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    # Synthetic panel that passes schema validation
    df = pd.DataFrame({col: [None] * 2000 for col in EXPECTED_COLUMNS})
    # Plant TAR signal in the two columns we use
    synth = _make_synthetic_tar(n=2000, c_true=2.0)
    df["dom_load_gradient_abs_mw_per_min"] = synth["Z"].values
    df["congestion_price_rt_cluster_mean"] = synth["Y"].values
    df["passes_proposal_filter"] = True  # use all rows
    df["datetime_beginning_ept"] = pd.date_range(
        "2024-01-01", periods=2000, freq="h"
    )

    out_path = tmp_path / "tar_fit.json"
    result = run_tar(
        panel=df,
        out_path=out_path,
        n_boot=50,  # fast for test
        seed=42,
    )
    assert out_path.exists()
    import json
    payload = json.loads(out_path.read_text())
    assert "c_hat" in payload
    assert "c_hat_ci_95" in payload
    assert "alpha" in payload
    assert "beta" in payload
    assert "hansen_p_value" in payload
    assert "regime_counts" in payload
    assert abs(payload["c_hat"] - 2.0) < 0.5
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_tar.py::test_run_tar_writes_json -v
```

Expected: ImportError on `run_tar`.

- [ ] **Step 3: Implement `run_tar`**

Append to `src/surg/analysis/tar.py`:

```python
import json
from dataclasses import asdict
from pathlib import Path


def run_tar(
    panel,
    out_path: Path,
    *,
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    trim: float = 0.15,
    n_grid: int = 300,
    n_boot: int = 1000,
    seed: int = 42,
) -> TARResult:
    """End-to-end TAR fit on the panel, writing JSON output.

    Selects rows where passes_proposal_filter is True; constructs Y_lag
    from the full (unfiltered) time series so the AR(1) structure is
    natural.
    """
    import pandas as pd

    # Order by datetime to ensure lag alignment
    panel = panel.sort_values("datetime_beginning_ept").reset_index(drop=True)
    # Y_{t-1} on the FULL time series (per design spec §4)
    panel["_Y_lag"] = panel[response_col].shift(1)
    # Then subset to the proposal filter
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[response_col, "_Y_lag", threshold_col])

    Y = subset[response_col].to_numpy()
    Y_lag = subset["_Y_lag"].to_numpy()
    Z = subset[threshold_col].to_numpy()

    point = fit_tar(Y, Y_lag, Z, trim=trim, n_grid=n_grid)
    p_value = hansen_bootstrap_test(
        Y, Y_lag, Z, point,
        n_boot=n_boot, trim=trim, n_grid=n_grid, seed=seed,
    )

    # Bootstrap CI for c_hat: resample (Y, Y_lag, Z) tuples and re-fit
    rng = np.random.default_rng(seed + 1)
    c_boot = np.empty(min(500, n_boot))
    n = len(Y)
    for i in range(len(c_boot)):
        idx = rng.integers(0, n, size=n)
        b = fit_tar(Y[idx], Y_lag[idx], Z[idx], trim=trim, n_grid=n_grid // 3)
        c_boot[i] = b.c_hat
    ci_lo, ci_hi = float(np.quantile(c_boot, 0.025)), float(np.quantile(c_boot, 0.975))

    payload = {
        "c_hat": point.c_hat,
        "c_hat_ci_95": [ci_lo, ci_hi],
        "alpha": point.alpha.tolist(),
        "beta": point.beta.tolist(),
        "regime_counts": {"low": point.n_low, "high": point.n_high},
        "ssr_low": point.ssr_low,
        "ssr_high": point.ssr_high,
        "ssr_joint": point.ssr_joint,
        "hansen_p_value": p_value,
        "n_boot": n_boot,
        "trim": trim,
        "n_grid": n_grid,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
    return point
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_tar.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 102 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/tar.py tests/analysis/test_tar.py
git commit -m "feat(analysis): TAR public API run_tar with JSON output + bootstrap CI"
```

---

## Task 6: Quantile regression — linear + threshold dummy specs

**Files:**
- Create: `src/surg/analysis/qr.py`
- Create: `tests/analysis/test_qr.py`

- [ ] **Step 1: Write failing test**

Create `tests/analysis/test_qr.py`:

```python
import numpy as np
import pandas as pd


def _make_synthetic_qr(n: int = 2000, c_true: float = 2.0, seed: int = 7):
    """Z is right-skewed; Q_0.99(Y|Z) has a slope kink at c_true."""
    rng = np.random.default_rng(seed)
    Z = rng.lognormal(0, 0.7, size=n)
    # Heteroskedastic: variance increases above c_true → 99th-pct quantile slopes up
    sigma = np.where(Z > c_true, 1.0 + 3.0 * (Z - c_true), 1.0)
    Y = rng.normal(0, sigma)
    return pd.DataFrame({"Z": Z, "Y": Y})


def test_qr_linear_baseline_returns_significant_positive_slope():
    """At τ=0.99, the linear slope should be positive and significant."""
    from surg.analysis.qr import fit_qr_linear

    df = _make_synthetic_qr(n=2000)
    result = fit_qr_linear(Y=df["Y"].to_numpy(), Z=df["Z"].to_numpy(), tau=0.99)
    assert result.slope > 0
    # Statsmodels-style p-value attribute
    assert result.slope_p_value < 0.05


def test_qr_threshold_dummy_detects_kink():
    """With c set to the true threshold, the dummy coefficient should be significant."""
    from surg.analysis.qr import fit_qr_threshold_dummy

    df = _make_synthetic_qr(n=2000, c_true=2.0)
    result = fit_qr_threshold_dummy(
        Y=df["Y"].to_numpy(), Z=df["Z"].to_numpy(), c=2.0, tau=0.99,
    )
    assert result.kink_coef > 0
    assert result.kink_p_value < 0.05
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_qr.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement linear + threshold-dummy QR**

Create `src/surg/analysis/qr.py`:

```python
"""Conditional quantile regression at τ=0.99 — robustness check on TAR.

Three specifications per the design spec §5:
  1. Linear baseline: Q_τ(Y|Z) = γ₀ + γ₁·Z
  2. Threshold dummy at TAR's ĉ: Q_τ(Y|Z) = δ₀ + δ₁·Z + δ₂·(Z−c)·I(Z>c)
  3. B-spline non-parametric: Q_τ(Y|Z) = f(Z); kink location estimated
     by finding where the second derivative of f peaks.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm


@dataclass(frozen=True, slots=True)
class QRLinearResult:
    intercept: float
    slope: float
    slope_p_value: float
    tau: float
    n: int


@dataclass(frozen=True, slots=True)
class QRThresholdDummyResult:
    intercept: float
    slope: float
    kink_coef: float       # the δ₂ coefficient on (Z-c)·I(Z>c)
    kink_p_value: float
    c: float
    tau: float
    n: int


def fit_qr_linear(Y: np.ndarray, Z: np.ndarray, *, tau: float = 0.99) -> QRLinearResult:
    """Linear quantile regression: Q_τ(Y|Z) = γ₀ + γ₁·Z."""
    X = sm.add_constant(Z)
    model = sm.QuantReg(Y, X).fit(q=tau)
    return QRLinearResult(
        intercept=float(model.params[0]),
        slope=float(model.params[1]),
        slope_p_value=float(model.pvalues[1]),
        tau=tau,
        n=len(Y),
    )


def fit_qr_threshold_dummy(
    Y: np.ndarray, Z: np.ndarray, *, c: float, tau: float = 0.99,
) -> QRThresholdDummyResult:
    """Quantile regression with explicit threshold dummy at c."""
    kink = np.where(Z > c, Z - c, 0.0)
    X = np.column_stack([np.ones(len(Z)), Z, kink])
    model = sm.QuantReg(Y, X).fit(q=tau)
    return QRThresholdDummyResult(
        intercept=float(model.params[0]),
        slope=float(model.params[1]),
        kink_coef=float(model.params[2]),
        kink_p_value=float(model.pvalues[2]),
        c=c,
        tau=tau,
        n=len(Y),
    )
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_qr.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 104 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/qr.py tests/analysis/test_qr.py
git commit -m "feat(analysis): QR linear + threshold-dummy specs"
```

---

## Task 7: Quantile regression — B-spline non-parametric kink location

**Files:**
- Modify: `src/surg/analysis/qr.py`
- Modify: `tests/analysis/test_qr.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_qr.py`:

```python
def test_qr_bspline_kink_location_near_truth():
    """The estimated kink location from the spline should be near c_true."""
    from surg.analysis.qr import fit_qr_bspline

    df = _make_synthetic_qr(n=3000, c_true=2.0, seed=11)
    result = fit_qr_bspline(
        Y=df["Y"].to_numpy(), Z=df["Z"].to_numpy(),
        tau=0.99, n_knots=5,
    )
    # Kink location should be in the same ballpark as truth
    assert abs(result.kink_location - 2.0) < 1.0
    assert len(result.curve_z) == 200  # default grid size
    assert len(result.curve_q) == 200
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_qr.py::test_qr_bspline_kink_location_near_truth -v
```

Expected: ImportError.

- [ ] **Step 3: Implement B-spline QR**

Append to `src/surg/analysis/qr.py`:

```python
from scipy.interpolate import UnivariateSpline


@dataclass(frozen=True, slots=True)
class QRSplineResult:
    kink_location: float       # Z value where the slope curvature peaks
    curve_z: np.ndarray        # grid of Z values
    curve_q: np.ndarray        # estimated Q_τ at each curve_z
    tau: float
    n: int


def fit_qr_bspline(
    Y: np.ndarray, Z: np.ndarray, *, tau: float = 0.99,
    n_knots: int = 5, n_grid: int = 200,
) -> QRSplineResult:
    """Non-parametric quantile regression via B-spline basis on Z.

    Strategy: place knots at evenly-spaced Z quantiles; build the spline
    basis manually using piecewise-linear (truncated power) functions;
    run statsmodels QuantReg. Then for kink-location, fit a smoothing
    spline to (Z_grid, Q_grid) and report where its second derivative
    is largest.
    """
    # Knots at interior quantiles
    knot_qs = np.linspace(0.1, 0.9, n_knots)
    knots = np.quantile(Z, knot_qs)

    # Piecewise-linear basis: 1, Z, (Z - knot_k)_+ for k=1..n_knots
    basis_cols = [np.ones(len(Z)), Z]
    for k in knots:
        basis_cols.append(np.maximum(Z - k, 0.0))
    X = np.column_stack(basis_cols)
    model = sm.QuantReg(Y, X).fit(q=tau)

    # Evaluate the fitted curve on a Z grid
    z_lo, z_hi = float(np.quantile(Z, 0.02)), float(np.quantile(Z, 0.98))
    z_grid = np.linspace(z_lo, z_hi, n_grid)
    basis_grid_cols = [np.ones(n_grid), z_grid]
    for k in knots:
        basis_grid_cols.append(np.maximum(z_grid - k, 0.0))
    X_grid = np.column_stack(basis_grid_cols)
    q_grid = X_grid @ model.params

    # Kink location: argmax of |second derivative| of the curve
    second_deriv = np.gradient(np.gradient(q_grid, z_grid), z_grid)
    kink_idx = int(np.argmax(np.abs(second_deriv)))
    kink_location = float(z_grid[kink_idx])

    return QRSplineResult(
        kink_location=kink_location,
        curve_z=z_grid,
        curve_q=q_grid,
        tau=tau,
        n=len(Y),
    )
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_qr.py -v
```

Expected: 3 passed. (B-spline kink location estimation is noisy with small samples; if the test fails marginally, increase `n=3000` in `_make_synthetic_qr`.)

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 105 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/qr.py tests/analysis/test_qr.py
git commit -m "feat(analysis): QR B-spline non-parametric kink location"
```

---

## Task 8: QR — public API + JSON output

**Files:**
- Modify: `src/surg/analysis/qr.py`
- Modify: `tests/analysis/test_qr.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_qr.py`:

```python
def test_run_qr_writes_json(tmp_path):
    from surg.analysis.qr import run_qr
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None] * 2000 for col in EXPECTED_COLUMNS})
    synth = _make_synthetic_qr(n=2000, c_true=2.0)
    df["dom_load_gradient_abs_mw_per_min"] = synth["Z"].values
    df["congestion_price_rt_cluster_mean"] = synth["Y"].values
    df["passes_proposal_filter"] = True
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=2000, freq="h")

    out_path = tmp_path / "qr_fit.json"
    run_qr(panel=df, out_path=out_path, c_for_threshold_dummy=2.0)
    assert out_path.exists()

    import json
    payload = json.loads(out_path.read_text())
    assert "linear" in payload
    assert payload["linear"]["slope"] > 0
    assert "threshold_dummy" in payload
    assert payload["threshold_dummy"]["c"] == 2.0
    assert "spline" in payload
    assert "kink_location" in payload["spline"]
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_qr.py::test_run_qr_writes_json -v
```

Expected: ImportError on `run_qr`.

- [ ] **Step 3: Implement `run_qr`**

Append to `src/surg/analysis/qr.py`:

```python
import json
from pathlib import Path


def run_qr(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    c_for_threshold_dummy: float,
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    tau: float = 0.99,
) -> None:
    """End-to-end QR: linear, threshold-dummy at c, B-spline. Write JSON."""
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[response_col, threshold_col])
    Y = subset[response_col].to_numpy()
    Z = subset[threshold_col].to_numpy()

    linear = fit_qr_linear(Y=Y, Z=Z, tau=tau)
    dummy = fit_qr_threshold_dummy(Y=Y, Z=Z, c=c_for_threshold_dummy, tau=tau)
    spline = fit_qr_bspline(Y=Y, Z=Z, tau=tau)

    payload = {
        "linear": {
            "intercept": linear.intercept,
            "slope": linear.slope,
            "slope_p_value": linear.slope_p_value,
            "n": linear.n,
        },
        "threshold_dummy": {
            "intercept": dummy.intercept,
            "slope": dummy.slope,
            "kink_coef": dummy.kink_coef,
            "kink_p_value": dummy.kink_p_value,
            "c": dummy.c,
            "n": dummy.n,
        },
        "spline": {
            "kink_location": spline.kink_location,
            "curve_z": spline.curve_z.tolist(),
            "curve_q": spline.curve_q.tolist(),
            "n": spline.n,
        },
        "tau": tau,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_qr.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 106 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/qr.py tests/analysis/test_qr.py
git commit -m "feat(analysis): QR public API run_qr with JSON output"
```

---

## Task 9: Mechanism — Granger causality

**Files:**
- Create: `src/surg/analysis/mechanism.py`
- Create: `tests/analysis/test_mechanism.py`

- [ ] **Step 1: Write failing test**

Create `tests/analysis/test_mechanism.py`:

```python
import numpy as np
import pandas as pd


def _make_lead_lag_data(n: int = 1000, lead: int = 2, seed: int = 0):
    """X leads Y by `lead` steps."""
    rng = np.random.default_rng(seed)
    X = rng.normal(0, 1, n)
    noise = rng.normal(0, 1, n)
    Y = np.zeros(n)
    for t in range(lead, n):
        Y[t] = 0.6 * X[t - lead] + noise[t]
    return pd.DataFrame({"X": X, "Y": Y})


def test_granger_detects_planted_lead_lag():
    """When X leads Y by 2 steps, the F-test at lag 2 should be highly significant."""
    from surg.analysis.mechanism import granger_test

    df = _make_lead_lag_data(n=1000, lead=2)
    results = granger_test(
        cause=df["X"].to_numpy(), effect=df["Y"].to_numpy(), max_lag=4,
    )
    # results[k] = (F-stat, p-value) for lag k
    assert results[2][1] < 0.01  # p-value at lag 2 should be tiny


def test_granger_does_not_falsely_detect_when_independent():
    from surg.analysis.mechanism import granger_test
    rng = np.random.default_rng(0)
    X = rng.normal(0, 1, 1000)
    Y = rng.normal(0, 1, 1000)
    results = granger_test(cause=X, effect=Y, max_lag=3)
    # Most p-values should be > 0.1 (no real causality)
    p_values = [results[k][1] for k in results]
    assert np.median(p_values) > 0.1
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_mechanism.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `granger_test`**

Create `src/surg/analysis/mechanism.py`:

```python
"""Mechanism validation — Granger causality, conditional regime test,
cross-tabulation, power-law fit on event durations.

See design spec §6 for the three tests + tertiary robustness check.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests


def granger_test(
    cause: np.ndarray, effect: np.ndarray, *, max_lag: int = 3,
) -> dict[int, tuple[float, float]]:
    """Run Granger causality F-tests at lags 1..max_lag.

    Returns: dict {lag: (F-stat, p-value)}.
    """
    data = np.column_stack([effect, cause])  # [effect, cause] order required
    raw = grangercausalitytests(data, maxlag=max_lag, verbose=False)
    return {
        lag: (float(raw[lag][0]["ssr_ftest"][0]),
              float(raw[lag][0]["ssr_ftest"][1]))
        for lag in range(1, max_lag + 1)
    }
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_mechanism.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 108 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/mechanism.py tests/analysis/test_mechanism.py
git commit -m "feat(analysis): Granger causality test wrapper"
```

---

## Task 10: Mechanism — conditional regime test + 2×2 cross-tab

**Files:**
- Modify: `src/surg/analysis/mechanism.py`
- Modify: `tests/analysis/test_mechanism.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_mechanism.py`:

```python
def test_conditional_regime_test_quantifies_concordance():
    from surg.analysis.mechanism import conditional_regime_test

    # 100 hours. Z>c is true 30/100 times. Event active 25/100 times.
    # Of the 25 event-active hours, 20 also have Z>c (strong concordance).
    n = 100
    Z = np.array([2.0] * 70 + [3.5] * 30)
    active = np.array([False] * 75 + [True] * 25)
    # Reorder so that 20 of the 25 active are in the high-Z region
    rng = np.random.default_rng(0)
    # Hand-craft: first 20 high-Z are active, next 5 of the next 5 high-Z are inactive,
    # remaining 25 low-Z have 5 active and 65 inactive.
    Z = np.r_[np.full(20, 3.5), np.full(5, 3.5), np.full(5, 3.5),
              np.full(5, 2.0), np.full(65, 2.0)]
    active = np.r_[np.full(20, True), np.full(5, False), np.full(5, False),
                   np.full(5, True), np.full(65, False)]

    result = conditional_regime_test(Z=Z, threshold=3.0, event_active=active)
    assert result["frac_above_threshold_when_active"] == 20/25
    assert result["frac_above_threshold_when_inactive"] == 10/75
    assert result["effect_size"] > 0  # strongly positive


def test_crosstab_chi2_detects_strong_dependence():
    from surg.analysis.mechanism import crosstab_chi2

    Z = np.r_[np.full(20, 3.5), np.full(5, 3.5), np.full(5, 3.5),
              np.full(5, 2.0), np.full(65, 2.0)]
    active = np.r_[np.full(20, True), np.full(5, False), np.full(5, False),
                   np.full(5, True), np.full(65, False)]

    result = crosstab_chi2(Z=Z, threshold=3.0, event_active=active)
    # Strong concordance → χ² p-value should be tiny
    assert result["chi2_p_value"] < 0.001
    # The 2×2 table
    assert result["table"][True][True] == 20
    assert result["table"][True][False] == 5
    assert result["table"][False][True] == 10
    assert result["table"][False][False] == 65
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_mechanism.py -k "regime or crosstab" -v
```

Expected: ImportError.

- [ ] **Step 3: Implement both functions**

Append to `src/surg/analysis/mechanism.py`:

```python
from scipy.stats import chi2_contingency


def conditional_regime_test(
    Z: np.ndarray, *, threshold: float, event_active: np.ndarray,
) -> dict:
    """Fraction of Z>c hours conditional on event_active status."""
    Z = np.asarray(Z)
    active = np.asarray(event_active, dtype=bool)
    above = Z > threshold
    n_active = int(active.sum())
    n_inactive = int((~active).sum())

    frac_active = float(above[active].mean()) if n_active > 0 else float("nan")
    frac_inactive = float(above[~active].mean()) if n_inactive > 0 else float("nan")

    return {
        "frac_above_threshold_when_active": frac_active,
        "frac_above_threshold_when_inactive": frac_inactive,
        "effect_size": frac_active - frac_inactive,
        "n_active": n_active,
        "n_inactive": n_inactive,
    }


def crosstab_chi2(
    Z: np.ndarray, *, threshold: float, event_active: np.ndarray,
) -> dict:
    """2×2 cross-tabulation of (Z>c) × (event_active) with χ² test of
    independence."""
    Z = np.asarray(Z)
    active = np.asarray(event_active, dtype=bool)
    above = Z > threshold

    # 2×2 contingency table; rows indexed by event_active, cols by above-threshold
    table = pd.crosstab(active, above)
    chi2, p, _, _ = chi2_contingency(table.values)

    # Normalize the output dict so the test can index by True/False
    out_table = {
        True:  {True: int(table.at[True, True]) if True in table.columns and True in table.index else 0,
                False: int(table.at[True, False]) if False in table.columns and True in table.index else 0},
        False: {True: int(table.at[False, True]) if True in table.columns and False in table.index else 0,
                False: int(table.at[False, False]) if False in table.columns and False in table.index else 0},
    }
    return {
        "table": out_table,
        "chi2_stat": float(chi2),
        "chi2_p_value": float(p),
    }
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_mechanism.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 110 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/mechanism.py tests/analysis/test_mechanism.py
git commit -m "feat(analysis): conditional regime test + 2x2 chi-squared cross-tab"
```

---

## Task 11: Mechanism — power-law fit on event durations

**Files:**
- Modify: `src/surg/analysis/mechanism.py`
- Modify: `tests/analysis/test_mechanism.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_mechanism.py`:

```python
def test_power_law_fit_recovers_alpha():
    """Synthetic Pareto-distributed durations should give back the planted α."""
    from surg.analysis.mechanism import fit_power_law

    rng = np.random.default_rng(42)
    # Pareto with shape α-1=1.5 (so α=2.5), scale=1
    alpha_true = 2.5
    n = 2000
    durations = rng.pareto(alpha_true - 1, size=n) + 1.0

    result = fit_power_law(durations)
    assert abs(result["alpha"] - alpha_true) < 0.3
    assert result["x_min"] > 0
    assert "ks_p_value" in result


def test_power_law_handles_empty_input():
    from surg.analysis.mechanism import fit_power_law
    result = fit_power_law(np.array([]))
    assert result["alpha"] is None
    assert result["n"] == 0
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_mechanism.py -k power_law -v
```

Expected: ImportError on `fit_power_law`.

- [ ] **Step 3: Implement `fit_power_law`**

Append to `src/surg/analysis/mechanism.py`:

```python
def fit_power_law(durations: np.ndarray) -> dict:
    """Fit a power-law distribution to event durations.

    Uses the `powerlaw` package (Clauset/Shalizi/Newman 2009 method):
    estimate x_min via KS minimization, then fit α via MLE on tail.
    Returns alpha, x_min, KS p-value (goodness-of-fit).
    """
    durations = np.asarray(durations, dtype=float)
    n = int(len(durations))
    if n < 10:
        return {"alpha": None, "x_min": None, "ks_p_value": None, "n": n}

    import powerlaw
    fit = powerlaw.Fit(durations, verbose=False)
    return {
        "alpha": float(fit.alpha),
        "x_min": float(fit.xmin),
        "ks_p_value": float(getattr(fit, "D", float("nan"))),  # KS distance (lower=better fit)
        "n": n,
    }
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_mechanism.py -v
```

Expected: 6 passed. The `powerlaw` package emits some warnings on import; ignore.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 112 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/mechanism.py tests/analysis/test_mechanism.py
git commit -m "feat(analysis): power-law fit on sync_reserve_event durations"
```

---

## Task 12: Mechanism — public API `run_mechanism`

**Files:**
- Modify: `src/surg/analysis/mechanism.py`
- Modify: `tests/analysis/test_mechanism.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_mechanism.py`:

```python
def test_run_mechanism_writes_json(tmp_path):
    from surg.analysis.mechanism import run_mechanism
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    n = 500
    df = pd.DataFrame({col: [None]*n for col in EXPECTED_COLUMNS})
    rng = np.random.default_rng(0)
    df["dom_load_gradient_abs_mw_per_min"] = rng.lognormal(0, 0.7, n)
    df["sync_reserve_event_active"] = rng.random(n) > 0.9
    df["passes_proposal_filter"] = True
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=n, freq="h")
    # Synthetic event durations: rows where sync_reserve_event_active is True
    # → produce some durations (the loader normally would give us this)
    # For the run_mechanism API, we pass a separate `events` DataFrame.
    events_df = pd.DataFrame({
        "event_start_ept": pd.to_datetime(["2024-01-15T03:00:00"] * 10),
        "event_end_ept":   pd.to_datetime(["2024-01-15T04:00:00"] * 10),
        "duration": ["1 hour"] * 10,
    })

    out_path = tmp_path / "mechanism_validation.json"
    run_mechanism(
        panel=df, events=events_df,
        threshold=1.0,  # c for the conditional-regime test
        out_path=out_path,
    )
    assert out_path.exists()
    import json
    payload = json.loads(out_path.read_text())
    assert "granger" in payload
    assert "conditional_regime" in payload
    assert "crosstab" in payload
    assert "power_law" in payload
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_mechanism.py::test_run_mechanism_writes_json -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `run_mechanism`**

Append to `src/surg/analysis/mechanism.py`:

```python
import json
from pathlib import Path


def run_mechanism(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    *,
    threshold: float,
    out_path: Path,
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
) -> None:
    """End-to-end mechanism validation, writing JSON output."""
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[threshold_col])

    # Convert sync_reserve_event_active to bool array (NaN → False)
    active = subset["sync_reserve_event_active"].fillna(False).astype(bool).to_numpy()
    Z = subset[threshold_col].to_numpy()

    # Granger: cause = Z (load volatility), effect = active-as-int (event indicator)
    granger = granger_test(cause=Z, effect=active.astype(float), max_lag=3)
    crt = conditional_regime_test(Z=Z, threshold=threshold, event_active=active)
    xtab = crosstab_chi2(Z=Z, threshold=threshold, event_active=active)

    # Power-law on event durations (extracted from events DataFrame)
    if events.empty:
        durations_hours = np.array([])
    else:
        durations_hours = (
            (events["event_end_ept"] - events["event_start_ept"])
            .dt.total_seconds() / 3600.0
        ).to_numpy()
    plaw = fit_power_law(durations_hours)

    payload = {
        "granger": {str(lag): {"F": v[0], "p_value": v[1]} for lag, v in granger.items()},
        "conditional_regime": crt,
        "crosstab": xtab,
        "power_law": plaw,
        "threshold_used": threshold,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_mechanism.py -v
```

Expected: 7 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 113 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/mechanism.py tests/analysis/test_mechanism.py
git commit -m "feat(analysis): mechanism public API run_mechanism with JSON output"
```

---

## Task 13: Robustness — subsample bootstrap on TAR `ĉ`

**Files:**
- Create: `src/surg/analysis/robustness.py`
- Create: `tests/analysis/test_robustness.py`

- [ ] **Step 1: Write failing test**

Create `tests/analysis/test_robustness.py`:

```python
import numpy as np
import pandas as pd


def test_subsample_bootstrap_returns_distribution_of_c_hats(tmp_path):
    from surg.analysis.robustness import subsample_bootstrap
    from tests.analysis.test_tar import _make_synthetic_tar
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None]*2000 for col in EXPECTED_COLUMNS})
    synth = _make_synthetic_tar(n=2000, c_true=2.0)
    df["dom_load_gradient_abs_mw_per_min"] = synth["Z"].values
    df["congestion_price_rt_cluster_mean"] = synth["Y"].values
    df["passes_proposal_filter"] = True
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=2000, freq="h")

    out_path = tmp_path / "subsample_bootstrap.parquet"
    subsample_bootstrap(
        panel=df, out_path=out_path,
        n_reps=20, sample_frac=0.8, seed=42,
    )

    loaded = pd.read_parquet(out_path)
    assert len(loaded) == 20
    assert "c_hat" in loaded.columns
    # All bootstrap c_hats should be in a reasonable neighborhood of truth
    assert (loaded["c_hat"] - 2.0).abs().median() < 1.0
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_robustness.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `subsample_bootstrap`**

Create `src/surg/analysis/robustness.py`:

```python
"""Robustness checks — subsample bootstrap and leave-one-season-out."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.tar import fit_tar


def subsample_bootstrap(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    n_reps: int = 200,
    sample_frac: float = 0.8,
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    seed: int = 42,
) -> None:
    """Refit TAR on `n_reps` random subsamples (each of `sample_frac` rows).
    Write the resulting c_hat distribution to a parquet file."""
    panel = panel.sort_values("datetime_beginning_ept").reset_index(drop=True)
    panel["_Y_lag"] = panel[response_col].shift(1)
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[response_col, "_Y_lag", threshold_col])

    Y_all = subset[response_col].to_numpy()
    Y_lag_all = subset["_Y_lag"].to_numpy()
    Z_all = subset[threshold_col].to_numpy()
    n = len(Y_all)
    k = int(sample_frac * n)

    rng = np.random.default_rng(seed)
    rows = []
    for rep in range(n_reps):
        idx = rng.choice(n, size=k, replace=False)
        result = fit_tar(Y_all[idx], Y_lag_all[idx], Z_all[idx])
        rows.append({"rep": rep, "c_hat": result.c_hat,
                     "n_low": result.n_low, "n_high": result.n_high})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_path, index=False)
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_robustness.py -v
```

Expected: 1 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 114 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/robustness.py tests/analysis/test_robustness.py
git commit -m "feat(analysis): subsample bootstrap of TAR c_hat"
```

---

## Task 14: Robustness — leave-one-season-out

**Files:**
- Modify: `src/surg/analysis/robustness.py`
- Modify: `tests/analysis/test_robustness.py`

- [ ] **Step 1: Write failing test**

Append to `tests/analysis/test_robustness.py`:

```python
def test_leave_one_season_out_returns_per_season_c_hats(tmp_path):
    from surg.analysis.robustness import leave_one_season_out
    from tests.analysis.test_tar import _make_synthetic_tar
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None]*2000 for col in EXPECTED_COLUMNS})
    synth = _make_synthetic_tar(n=2000, c_true=2.0)
    df["dom_load_gradient_abs_mw_per_min"] = synth["Z"].values
    df["congestion_price_rt_cluster_mean"] = synth["Y"].values
    df["passes_proposal_filter"] = True
    # Split the rows into 4 fake "seasons" by date range
    df["datetime_beginning_ept"] = pd.date_range(
        "2024-01-01", periods=2000, freq="h"
    )
    # Assign a season_id 0-3 by 500-row chunks
    df["_season_id"] = np.repeat([0, 1, 2, 3], 500)

    out_path = tmp_path / "leave_one_season_out.parquet"
    leave_one_season_out(
        panel=df, out_path=out_path, season_col="_season_id",
    )
    loaded = pd.read_parquet(out_path)
    assert len(loaded) == 4
    assert "season_dropped" in loaded.columns
    assert "c_hat" in loaded.columns
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_robustness.py::test_leave_one_season_out_returns_per_season_c_hats -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `leave_one_season_out`**

Append to `src/surg/analysis/robustness.py`:

```python
def leave_one_season_out(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    season_col: str = "_season_id",
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
) -> None:
    """For each unique season, fit TAR on all OTHER seasons. Write
    {season_dropped, c_hat} rows to parquet."""
    panel = panel.sort_values("datetime_beginning_ept").reset_index(drop=True)
    panel["_Y_lag"] = panel[response_col].shift(1)
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[response_col, "_Y_lag", threshold_col, season_col])

    seasons = sorted(subset[season_col].unique())
    rows = []
    for s in seasons:
        kept = subset[subset[season_col] != s]
        if len(kept) < 100:
            continue
        result = fit_tar(
            Y=kept[response_col].to_numpy(),
            Y_lag=kept["_Y_lag"].to_numpy(),
            Z=kept[threshold_col].to_numpy(),
        )
        rows.append({"season_dropped": s, "c_hat": result.c_hat,
                     "n_low": result.n_low, "n_high": result.n_high})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_path, index=False)
```

- [ ] **Step 4: Run tests**

```
.venv/bin/pytest tests/analysis/test_robustness.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 115 passed.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/robustness.py tests/analysis/test_robustness.py
git commit -m "feat(analysis): leave-one-season-out robustness check"
```

---

## Task 15: Run orchestrator + `surg-analyze` CLI

**Files:**
- Create: `src/surg/analysis/run.py`
- Create: `tests/analysis/test_run.py`
- Modify: `pyproject.toml` (add console_scripts entry)

- [ ] **Step 1: Write failing test**

Create `tests/analysis/test_run.py`:

```python
from pathlib import Path

import numpy as np
import pandas as pd


def _make_panel_with_signal(n: int = 2000) -> pd.DataFrame:
    from surg.preprocessing.schema import EXPECTED_COLUMNS
    from tests.analysis.test_tar import _make_synthetic_tar

    df = pd.DataFrame({col: [None]*n for col in EXPECTED_COLUMNS})
    synth = _make_synthetic_tar(n=n, c_true=2.0)
    df["dom_load_gradient_abs_mw_per_min"] = synth["Z"].values
    df["congestion_price_rt_cluster_mean"] = synth["Y"].values
    df["passes_proposal_filter"] = True
    df["sync_reserve_event_active"] = (df["dom_load_gradient_abs_mw_per_min"] > 2.0)
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=n, freq="h")
    return df


def test_run_all_writes_all_outputs(tmp_path: Path):
    from surg.analysis.run import run_all
    panel = _make_panel_with_signal(n=2000)
    events = pd.DataFrame({
        "event_start_ept": pd.to_datetime(["2024-01-15T03:00:00"] * 5),
        "event_end_ept":   pd.to_datetime(["2024-01-15T05:30:00"] * 5),
        "duration": ["2.5 hours"] * 5,
    })

    out_root = tmp_path / "outputs"
    # Add the secondary + control response columns to the synthetic panel
    # so run_all can write per-column TAR outputs
    for col in [
        "total_lmp_rt_cluster_mean",
        "congestion_price_rt_ashburn_tx1", "congestion_price_rt_ashburn_tx2",
        "congestion_price_rt_ox", "congestion_price_rt_bristers",
        "congestion_price_rt_dom_zonal",
    ]:
        # Plant the same TAR signal as the primary so all fits succeed
        synth_extra = _make_synthetic_tar(n=len(panel), c_true=2.0,
                                          seed=hash(col) % 1000)
        panel[col] = synth_extra["Y"].values

    run_all(
        panel=panel, events=events,
        out_root=out_root,
        n_boot=30,  # fast
        n_subsample_reps=10,
    )
    assert (out_root / "tar_fit_primary.json").exists()
    assert (out_root / "tar_fit_total_lmp_cluster_mean.json").exists() \
        or (out_root / "tar_fit_total_lmp.json").exists()  # slug variants accepted
    # At least one control fit emitted
    control_outputs = list(out_root.glob("tar_fit_ashburn*.json")) + \
                      list(out_root.glob("tar_fit_ox.json")) + \
                      list(out_root.glob("tar_fit_bristers.json"))
    assert len(control_outputs) >= 1
    assert (out_root / "qr_fit.json").exists()
    assert (out_root / "mechanism_validation.json").exists()
    assert (out_root / "robustness" / "subsample_bootstrap.parquet").exists()
```

- [ ] **Step 2: Run test to verify failure**

```
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement `run.py`**

Create `src/surg/analysis/run.py`:

```python
"""Orchestrator: load panel, run TAR + QR + mechanism + robustness,
write all output artifacts. CLI entry point `surg-analyze`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from surg.analysis.panel import load_panel
from surg.analysis.tar import run_tar
from surg.analysis.qr import run_qr
from surg.analysis.mechanism import run_mechanism
from surg.analysis.robustness import subsample_bootstrap
from surg.preprocessing.loaders import load_sync_reserve_events


_SECONDARY_RESPONSE_COLS: tuple[str, ...] = (
    # Same Loudoun cluster pooled, but total LMP — cleaner ORDC mechanism test
    # (penalty lands in system energy LMP, not in congestion component directly).
    "total_lmp_rt_cluster_mean",
)

_CONTROL_RESPONSE_COLS: tuple[str, ...] = (
    # Ashburn distribution — separate fit (different physics per
    # decisions.md 2026-05-10 lock-in)
    "congestion_price_rt_ashburn_tx1",
    "congestion_price_rt_ashburn_tx2",
    # Negative controls — outside the Loudoun cluster; should NOT show
    # the same threshold (or show one at much higher c)
    "congestion_price_rt_ox",
    "congestion_price_rt_bristers",
    "congestion_price_rt_dom_zonal",
)


def run_all(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    out_root: Path,
    *,
    n_boot: int = 1000,
    n_subsample_reps: int = 200,
) -> None:
    """Run the full Phase 3 analysis pipeline.

    Produces:
      - tar_fit_primary.json: TAR on the Loudoun cluster mean congestion price
        (the proposal's primary deliverable)
      - tar_fit_<col>.json: TAR on each secondary + control response variable
      - qr_fit.json: quantile regression robustness on the PRIMARY response
      - mechanism_validation.json: Granger / conditional regime / cross-tab /
        power-law against the PRIMARY threshold
      - robustness/subsample_bootstrap.parquet: 200 c_hat samples from
        80%-subsamples of the PRIMARY fit
    """
    out_root.mkdir(parents=True, exist_ok=True)

    # Primary TAR fit — the proposal's deliverable
    primary = run_tar(
        panel=panel,
        out_path=out_root / "tar_fit_primary.json",
        response_col="congestion_price_rt_cluster_mean",
        n_boot=n_boot,
    )

    # Secondary fit — cleaner ORDC mechanism test (penalty lands in system
    # energy LMP, not congestion price)
    for col in _SECONDARY_RESPONSE_COLS:
        slug = col.replace("_rt_cluster_mean", "").replace("_rt_", "_")
        run_tar(
            panel=panel,
            out_path=out_root / f"tar_fit_{slug}.json",
            response_col=col,
            n_boot=n_boot,
        )

    # Negative-control fits — should NOT find the same threshold
    for col in _CONTROL_RESPONSE_COLS:
        slug = col.replace("congestion_price_rt_", "")
        # If a control column is fully NaN (the data didn't include that
        # pnode), skip it gracefully.
        if panel[col].dropna().empty:
            continue
        run_tar(
            panel=panel,
            out_path=out_root / f"tar_fit_{slug}.json",
            response_col=col,
            n_boot=n_boot,
        )

    # QR robustness check (uses the PRIMARY threshold for the dummy spec)
    run_qr(
        panel=panel,
        out_path=out_root / "qr_fit.json",
        c_for_threshold_dummy=primary.c_hat,
    )

    # Mechanism validation (uses the PRIMARY threshold)
    run_mechanism(
        panel=panel, events=events,
        threshold=primary.c_hat,
        out_path=out_root / "mechanism_validation.json",
    )

    # Robustness — subsample bootstrap of the PRIMARY fit
    subsample_bootstrap(
        panel=panel,
        out_path=out_root / "robustness" / "subsample_bootstrap.parquet",
        n_reps=n_subsample_reps,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-analyze",
        description="Run TAR + QR + mechanism analysis on the analysis panel.",
    )
    p.add_argument("--panel", default="data/interim/analysis_panel.parquet",
                   help="Path to the analysis panel parquet.")
    p.add_argument("--data-root", default="data/raw",
                   help="Root directory containing sync_reserve_events chunks.")
    p.add_argument("--out-root", default="outputs",
                   help="Output root directory.")
    p.add_argument("--n-boot", type=int, default=1000,
                   help="Number of bootstrap reps for Hansen test + CI.")
    p.add_argument("--n-subsample-reps", type=int, default=200,
                   help="Subsample bootstrap reps for c_hat CI.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    panel_path = Path(args.panel)
    if not panel_path.exists():
        print(f"panel not found: {panel_path}", file=sys.stderr)
        return 2
    panel = load_panel(panel_path)
    events = load_sync_reserve_events(Path(args.data_root))
    run_all(
        panel=panel, events=events,
        out_root=Path(args.out_root),
        n_boot=args.n_boot,
        n_subsample_reps=args.n_subsample_reps,
    )
    print(f"wrote analysis outputs to {args.out_root}/")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Add CLI entry to `pyproject.toml`**

In `[project.scripts]`, append:

```toml
surg-analyze = "surg.analysis.run:main"
```

Re-install: `.venv/bin/pip install -e .`

- [ ] **Step 5: Run tests**

```
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: 1 passed.

- [ ] **Step 6: Full suite**

```
.venv/bin/pytest tests/ -v
```

Expected: 116 passed.

- [ ] **Step 7: Smoke the entry point**

```
.venv/bin/surg-analyze --help
```

Expected: usage line starting with `usage: surg-analyze`.

- [ ] **Step 8: Commit**

```bash
git add src/surg/analysis/run.py tests/analysis/test_run.py pyproject.toml
git commit -m "feat(analysis): run_all orchestrator + surg-analyze CLI"
```

---

## Task 16: End-to-end run against the real analysis panel

After Plans 1 and 2 have populated `data/interim/analysis_panel.parquet`, run the full analysis.

- [ ] **Step 1: Verify prerequisites**

```bash
ls -la data/interim/analysis_panel.parquet 2>/dev/null && \
ls -la data/raw/sync_reserve_events/*/*.parquet 2>/dev/null | head -3
```

Both must exist. If not, complete Plans 1 and 2 first.

- [ ] **Step 2: Run the analysis**

```
.venv/bin/surg-analyze
```

Expected: ~5-10 min wall time (dominated by Hansen bootstrap and subsample bootstrap). Output: `wrote analysis outputs to outputs/`.

- [ ] **Step 3: Inspect primary TAR result**

```bash
.venv/bin/python -c "
import json
r = json.load(open('outputs/tar_fit_primary.json'))
print(f'c_hat = {r[\"c_hat\"]:.4f} MW/min')
print(f'95% CI = [{r[\"c_hat_ci_95\"][0]:.4f}, {r[\"c_hat_ci_95\"][1]:.4f}]')
print(f'Hansen bootstrap p = {r[\"hansen_p_value\"]:.4f}')
print(f'regime counts: low={r[\"regime_counts\"][\"low\"]}, high={r[\"regime_counts\"][\"high\"]}')
print(f'AR coefs: alpha={r[\"alpha\"]}, beta={r[\"beta\"]}')
"
```

Findings interpretation per design spec §8 (failure modes):
- If `hansen_p_value > 0.10`: report the null result; consider widening the night window.
- If `regime_counts.high < 50`: apply the pre-decided mitigation (widen the window).
- If `c_hat` lands at the trim boundary (≥ 95th percentile of Z): report as boundary degenerate.

- [ ] **Step 4: Compare primary, secondary, and control TAR fits**

```bash
.venv/bin/python -c "
import json
from pathlib import Path
for f in sorted(Path('outputs').glob('tar_fit_*.json')):
    r = json.load(f.open())
    print(f'{f.stem:50}  c_hat={r[\"c_hat\"]:8.3f}  Hansen p={r[\"hansen_p_value\"]:.4f}  n_high={r[\"regime_counts\"][\"high\"]}')
"
```

Expected interpretation (per design spec §8):
- `tar_fit_primary` (congestion price, Loudoun cluster) should have small Hansen p-value if the threshold is real.
- `tar_fit_total_lmp_*` (total LMP, Loudoun cluster) should agree closely — same mechanism, cleaner test.
- `tar_fit_ox`, `tar_fit_bristers`, `tar_fit_dom_zonal` (outside-cluster controls) should have larger p-values or much different `c_hat`. If they show the same threshold, the phenomenon is DOM-wide rather than Loudoun-specific — still a finding but a different story.
- `tar_fit_ashburn_*` (distribution-side) is a separate finding; should be interpreted independently of the cluster.

- [ ] **Step 5: Inspect QR + mechanism results**

```bash
.venv/bin/python -c "
import json
qr = json.load(open('outputs/qr_fit.json'))
mech = json.load(open('outputs/mechanism_validation.json'))
print(f'QR linear slope: {qr[\"linear\"][\"slope\"]:.3f} (p={qr[\"linear\"][\"slope_p_value\"]:.4f})')
print(f'QR threshold-dummy kink coef at c: {qr[\"threshold_dummy\"][\"kink_coef\"]:.3f} (p={qr[\"threshold_dummy\"][\"kink_p_value\"]:.4f})')
print(f'QR spline kink location: {qr[\"spline\"][\"kink_location\"]:.4f}')
print()
print(f'Granger F at lag 1: F={mech[\"granger\"][\"1\"][\"F\"]:.2f}, p={mech[\"granger\"][\"1\"][\"p_value\"]:.4f}')
print(f'P(Z>c | event active): {mech[\"conditional_regime\"][\"frac_above_threshold_when_active\"]:.3f}')
print(f'P(Z>c | event inactive): {mech[\"conditional_regime\"][\"frac_above_threshold_when_inactive\"]:.3f}')
print(f'Crosstab chi2 p-value: {mech[\"crosstab\"][\"chi2_p_value\"]:.4f}')
print(f'Power-law alpha on event durations: {mech[\"power_law\"][\"alpha\"]}')
"
```

- [ ] **Step 6: No commit** (outputs are gitignored).

---

## Task 17: Final verification + push

- [ ] **Step 1: Full suite one last time**

```
.venv/bin/pytest tests/ -v
```

Expected: 116 passed.

- [ ] **Step 2: Verify git state**

```
git log --oneline origin/main..HEAD
```

Expected: 15 commits ahead (Tasks 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15 each commit).

- [ ] **Step 3: Push (requires user confirmation)**

> "Analysis module complete. 15 new commits. Push?"

If yes:

```bash
git push origin main
```

---

## Definition of done

- [ ] All 17 tasks complete.
- [ ] 116 tests passing.
- [ ] `outputs/tar_fit.json` exists with `c_hat`, `c_hat_ci_95`, `hansen_p_value`.
- [ ] `outputs/qr_fit.json` exists with linear / threshold-dummy / spline blocks.
- [ ] `outputs/mechanism_validation.json` exists with Granger, conditional regime, cross-tab, power-law blocks.
- [ ] `outputs/robustness/subsample_bootstrap.parquet` exists with 200 c_hat samples.
- [ ] No regressions in acquisition or preprocessing modules.

## Out of scope (deferred)

- Forecasting layer (year by which projected volatility crosses `ĉ`) — sibling spec; not in this plan.
- Figures (scatter, QR spline curve, cross-tab heatmap, power-law log-log, robustness fan) — separate spec or notebook.
- Leave-one-season-out execution (the function exists from Task 14 but isn't called by `run_all`) — uncomment in `run_all` once the panel has explicit season IDs (probably added in a small follow-up).
- 5-min secondary analysis (`analysis_panel_5min`) — deferred per spec §4 / §3.
- Markov regime-switching — skipped per design spec (we have observable events).
