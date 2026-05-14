# Strategy C modules — design spec

**Status:** Design only. Implementation plan (writing-plans skill output) is a separate document.

**Date:** 2026-05-13

**Cross-references:**
- `decisions.md` 2026-05-13 § "Application of pre-reg + diagnosis of threshold non-localizability" — the diagnosis motivating this pivot
- `decisions.md` 2026-05-10 § "Lock the 11-pnode target set" — pnode IDs referenced below
- Existing analysis module: `src/surg/analysis/` (`tar.py`, `qr.py`, `mechanism.py`, `robustness.py`, `run.py`)

## Context

The 2026-05-13 follow-up entry in `decisions.md` documented the smooth-curve diagnosis: the proposal's mechanistic chain (DC load → load volatility → reserve scarcity → SR clearing → ORDC step → LMP spike) places the only explicit step function downstream of `Z`, so the composite `Z → LMP` response is a smooth probabilistic curve. TAR's piecewise-constant approximation wanders with the data subset — explaining the filter-, resolution-, and `Z`-variable-sensitivity observed in today's probes.

The recommended pivot ("Strategy C") was: switch primary methodology to **QR-on-full-panel + GPD on LMP tails**, reframe the paper deliverable as a response curve rather than a point estimate. This spec covers the QR + GPD code; JLARC-driven projection is deferred to a separate spec.

## Scope

**In scope (this spec):**

- New module `src/surg/analysis/qr_full.py` — multi-quantile QR on the full 31,536-hour panel with time-of-day + season covariates, plus a year-FE robustness specification.
- New module `src/surg/analysis/gpd.py` — peaks-over-threshold GPD with a fixed-quantile threshold sweep and a `Z`-conditional mechanism test.
- Integration into `run.py` orchestrator; new CLI flags.
- Tests for both modules (~15 new tests; target 165 passing post-implementation, vs current 145).
- Output directory reorganization (`outputs/<method>/<pnode>.json` instead of flat).
- `.gitignore` simplification.

**Out of scope (deferred):**

- JLARC growth-forecast projection layer.
- Paper-ready figure generation.
- Continuous `ξ(Z)` parametric tail-shape model (Approach C from brainstorm; not Approach B).
- Backward-compat shims for the old `outputs/tar_fit_*.json` paths.
- `--methods-only` CLI flag to skip TAR (TAR stays as descriptive evidence per Strategy C).

## Architecture

### File layout

| Path | Status | Purpose |
|---|---|---|
| `src/surg/analysis/qr_full.py` | NEW | Multi-τ QR with covariates + year-FE robustness |
| `src/surg/analysis/gpd.py` | NEW | GPD POT + sweep + Z-conditional split |
| `tests/analysis/test_qr_full.py` | NEW | ~8 unit tests for `qr_full.py` |
| `tests/analysis/test_gpd.py` | NEW | ~7 unit tests for `gpd.py` |
| `src/surg/analysis/run.py` | MODIFIED | Orchestrator extended; output paths reorganized |
| `tests/analysis/test_run.py` | MODIFIED | Integration test paths updated |
| `.gitignore` | MODIFIED | Simpler `outputs/` ignore rule |
| `pyproject.toml` | unchanged | scipy + statsmodels cover all GPD/QR needs |

### Output directory reorganization (one-shot change in this spec)

```
outputs/
├── tar/                      # Method dir — TAR fits
│   ├── primary.json          # was outputs/tar_fit_primary.json
│   ├── total_lmp.json
│   ├── ox.json
│   ├── bristers.json
│   ├── dom_zonal.json
│   ├── ashburn_tx1.json
│   └── ashburn_tx2.json
├── qr/                       # Method dir — existing QR (filtered, at TAR's ĉ)
│   └── filtered_at_tar_c.json    # was outputs/qr_fit.json (renamed)
├── qr_full/                  # NEW method dir — multi-τ QR on full panel
│   └── <7 pnode files>
├── gpd/                      # NEW method dir — GPD POT + sweep + conditional
│   └── <7 pnode files>
├── mechanism/                # Method dir
│   └── validation.json       # was outputs/mechanism_validation.json
├── robustness/               # existing
│   └── subsample_bootstrap.parquet
├── figures/.gitkeep          # existing
└── tables/.gitkeep           # existing
```

**Rationale:** Method-first taxonomy (TAR/QR/GPD/etc. are different *kinds* of analysis; pnodes are dimensions across which each method applies) matches how the paper will read. Renaming `qr_fit.json` → `qr/filtered_at_tar_c.json` makes the distinction with `qr_full/` (full panel, multi-τ, with covariates) obvious. Renaming `mechanism_validation.json` → `mechanism/validation.json` drops a redundant suffix.

### `.gitignore` simplification

Current rule is fragile (many specific patterns). Replace with:

```
outputs/
!outputs/figures/
!outputs/figures/.gitkeep
!outputs/tables/
!outputs/tables/.gitkeep
```

Plus the existing `outputs_*/` rule (alt-window analysis dirs from 2026-05-13 session).

## Module: `qr_full.py`

### Public API

```python
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class QRFullFitResult:
    tau: float
    z_slope: float
    z_slope_se: float                              # asymptotic SE (statsmodels sandwich)
    z_slope_p_value: float
    z_slope_bootstrap_ci_95: tuple[float, float]   # pair-bootstrap, n_boot reps
    intercept: float
    covariate_coefs: dict[str, float]              # hour_sin, hour_cos, month_sin, month_cos[, year_*]
    spec: str                                      # "primary" or "year_fe"
    n: int


def fit_qr_full(
    Y: np.ndarray,
    Z: np.ndarray,
    hour: np.ndarray,    # int array, values in [0, 23]
    month: np.ndarray,   # int array, values in [1, 12]
    *,
    year: np.ndarray | None = None,  # int array; if provided, year dummies are added (year_fe spec)
    tau: float = 0.99,
    n_boot: int = 200,
    seed: int = 0,
) -> QRFullFitResult:
    """Fit Q_τ(Y | Z, sin/cos(hour), sin/cos(month) [, year dummies]).

    All arrays must have equal length; caller drops NaN before passing.
    Bootstrap CI is pair-resample of row indices.

    Returns one fit. Call twice (with/without year) for the primary +
    year-FE pair.
    """


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
    """End-to-end QR on full panel. Writes outputs/qr_full/<pnode_label>.json.

    Fits the primary specification (no year) and the year-FE robustness
    specification at each tau. Drops NaN in [response_col, threshold_col].
    """
```

### Design matrix

```
primary spec:  X = [1, Z, hour_sin, hour_cos, month_sin, month_cos]               # 6 columns
year_fe spec:  X = [1, Z, hour_sin, hour_cos, month_sin, month_cos, year_d1..d_K] # 6 + K columns
```

where the periodic encodings are:

```
hour_sin  = sin(2π · hour / 24)
hour_cos  = cos(2π · hour / 24)
month_sin = sin(2π · (month − 1) / 12)
month_cos = cos(2π · (month − 1) / 12)
```

and `year_d1..d_K` are `K = (number_of_distinct_years - 1)` dummy variables with the earliest year (2022) as the omitted baseline.

### Output JSON schema

```jsonc
{
  "pnode_label": "primary",
  "response_col": "congestion_price_rt_cluster_mean",
  "threshold_col": "dom_load_gradient_abs_mw_per_min",
  "covariate_encoding": "sin_cos_hour_24_month_12",
  "n_total_panel": 31536,
  "n_after_dropna": 31536,
  "fits": [
    {
      "tau": 0.90,
      "spec": "primary",
      "z_slope": 0.123,
      "z_slope_se": 0.045,
      "z_slope_p_value": 0.006,
      "z_slope_bootstrap_ci_95": [0.034, 0.212],
      "intercept": 12.4,
      "covariate_coefs": {
        "hour_sin": 0.52, "hour_cos": 1.23,
        "month_sin": -0.34, "month_cos": 0.87
      }
    },
    { "tau": 0.95, "spec": "primary", "...": "..." },
    { "tau": 0.99, "spec": "primary", "...": "..." }
  ],
  "fits_year_fe": [
    {
      "tau": 0.90,
      "spec": "year_fe",
      "z_slope": 0.078,
      "z_slope_se": 0.041,
      "z_slope_p_value": 0.057,
      "z_slope_bootstrap_ci_95": [-0.003, 0.159],
      "intercept": 14.2,
      "covariate_coefs": {
        "hour_sin": 0.51, "hour_cos": 1.22,
        "month_sin": -0.33, "month_cos": 0.86,
        "year_2023": 0.34, "year_2024": 1.08,
        "year_2025": 1.67, "year_2026": 2.10
      }
    },
    { "tau": 0.95, "spec": "year_fe", "...": "..." },
    { "tau": 0.99, "spec": "year_fe", "...": "..." }
  ]
}
```

### Design choices (rationale)

1. **Sin/cos vs hour-dummies for time-of-day:** 4 covariate parameters total vs ~22 (23 hour dummies + 11 month dummies, minus baselines). Sin/cos is naturally periodic (hour 23 ≈ hour 0). Limitation: assumes a sinusoidal time-of-day shape — roughly accurate for load/LMP (single peak per day, single peak per year). If the advisor pushes for full flexibility, an `--encoding=dummies` flag is a follow-up addition.

2. **Year-FE as a separate robustness spec, not the primary:** Year is a *mediator* of the DC-growth treatment effect, not a confound — conditioning on it would partial out part of the secular signal the proposal cares about. The primary fit omits year so the Z coefficient captures both contemporaneous and secular response. The year-FE fit isolates the contemporaneous response. The *difference* between the two estimates quantifies the secular component — itself a substantive finding.

3. **Bootstrap CI alongside asymptotic SE:** Asymptotic SE from statsmodels' sandwich estimator is known to underperform on quantile regression at high `τ` with autocorrelated data. Pair-bootstrap CI is the more honest interval. We report both so the paper can cite whichever the advisor prefers and discuss the gap.

4. **No `passes_proposal_filter` check:** Full-panel methodology. Drop NaN in `[response_col, threshold_col]` only.

## Module: `gpd.py`

### Public API

```python
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class GPDFitResult:
    threshold_quantile: float
    threshold_value: float
    shape: float                                # ξ
    shape_se: float                             # asymptotic, from observed Fisher information
    shape_bootstrap_ci_95: tuple[float, float]  # bootstrap of exceedances, n_boot reps
    scale: float                                # σ
    scale_se: float
    n_exceedances: int


@dataclass(frozen=True, slots=True)
class GPDConditionalResult:
    threshold_quantile: float
    threshold_value: float
    z_split_quantile: float
    z_split_value: float
    low_z: GPDFitResult
    high_z: GPDFitResult
    shape_diff: float                                 # ξ_high − ξ_low
    shape_diff_bootstrap_ci_95: tuple[float, float]
    shape_diff_bootstrap_p_value: float               # one-sided: P(ξ_high − ξ_low ≤ 0)


def fit_gpd(Y: np.ndarray, *, threshold: float) -> GPDFitResult:
    """MLE fit of GPD to exceedances over threshold u.

    Excess = Y[Y > u] - u, fit via scipy.stats.genpareto with floc=0.
    Asymptotic SE from observed Fisher information at MLE.
    """


def gpd_threshold_sweep(
    Y: np.ndarray,
    *,
    quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    n_boot: int = 200,
    seed: int = 0,
) -> list[GPDFitResult]:
    """Fit GPD at each threshold quantile. Bootstrap CI on shape per fit."""


def gpd_conditional_on_z(
    Y: np.ndarray,
    Z: np.ndarray,
    *,
    threshold_quantile: float = 0.95,
    z_split_quantile: float = 0.5,
    n_boot: int = 200,
    seed: int = 0,
) -> GPDConditionalResult:
    """Mechanism test: split exceedances by Z median, fit GPD on each subset,
    bootstrap the shape-parameter difference.

    Bootstrap procedure: resample exceedance row indices (with their paired Z
    values) with replacement; recompute the Z-split on each resample; refit
    GPD to each subset; record ξ_high − ξ_low. P-value is the fraction of
    bootstrap reps with ξ_high − ξ_low ≤ 0.
    """


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
    """End-to-end GPD: sweep + conditional split. Writes outputs/gpd/<pnode_label>.json."""
```

### Output JSON schema

```jsonc
{
  "pnode_label": "primary",
  "response_col": "congestion_price_rt_cluster_mean",
  "threshold_col": "dom_load_gradient_abs_mw_per_min",
  "n_total_panel": 31536,
  "n_after_dropna": 31536,
  "threshold_sweep": [
    {
      "threshold_quantile": 0.90,
      "threshold_value": 8.4,
      "n_exceedances": 3154,
      "shape": 0.34,
      "shape_se": 0.04,
      "shape_bootstrap_ci_95": [0.26, 0.42],
      "scale": 12.1,
      "scale_se": 0.5
    },
    { "threshold_quantile": 0.95, "...": "..." },
    { "threshold_quantile": 0.99, "...": "..." },
    { "threshold_quantile": 0.995, "...": "..." }
  ],
  "conditional_z": {
    "threshold_quantile": 0.95,
    "threshold_value": 23.7,
    "z_split_quantile": 0.5,
    "z_split_value": 2.291,
    "low_z":  {
      "shape": 0.21, "shape_se": 0.05,
      "shape_bootstrap_ci_95": [0.11, 0.31],
      "n_exceedances": 580
    },
    "high_z": {
      "shape": 0.48, "shape_se": 0.06,
      "shape_bootstrap_ci_95": [0.36, 0.60],
      "n_exceedances": 1297
    },
    "shape_difference": {
      "diff": 0.27,
      "bootstrap_ci_95": [0.10, 0.44],
      "bootstrap_p_value": 0.001
    }
  }
}
```

### Design choices (rationale)

1. **Fixed-quantile threshold sweep (not data-driven MRL plot selection):** The textbook approach picks `u` where the mean-residual-life plot becomes approximately linear — qualitative, per-pnode, requires human inspection. We sweep 4 fixed quantiles instead: reproducible, cross-pnode comparable, no per-pnode tuning. The sweep itself IS the robustness check — if `ξ` is stable across thresholds, the tail-heaviness conclusion is robust; if it shifts substantially, we have a threshold-selection finding to discuss.

2. **95th-percentile threshold for the conditional-Z test:** The sweep covers all 4; the Z-split test picks one threshold for parsimony.
   - 95th pct: ~1577 exceedances per pnode, split by Z median → ~788 per subset. Plenty of power.
   - 99th: ~315 / ~158 per subset — workable but power-limited.
   - 90th: ~3154 / ~1577 — most power but the "tail" claim is weaker.

3. **Z-split at median (not quartiles):** Median split keeps the full exceedance sample. Quartile split (top 25% vs bottom 25%, drop middle) gives sharper contrast but throws away half the data. Median first; revisit if results are noisy.

4. **Bootstrap on shape parameter only:** 200 reps per shape estimate × 4 sweep thresholds × 1 conditional split × 7 pnodes = ~5,600 GPD MLE fits per `run_all`. scipy's `genpareto.fit` is ~10-50ms each → ~30-150 sec wall for GPD alone.

5. **`scipy.stats.genpareto` quirk:** the default 3-parameter fit includes a free location parameter. We fix `floc=0` after shifting the data: `excess = Y[Y > u] - u`; `shape, _, scale = scipy.stats.genpareto.fit(excess, floc=0)`. Asymptotic SE from the Hessian at MLE via manual computation (`numpy.linalg.inv` of `-∂²ℓ/∂θ²`).

## Integration

### Orchestrator

`run_all` in `src/surg/analysis/run.py` extends as follows. The existing `_SECONDARY_RESPONSE_COLS` and `_CONTROL_RESPONSE_COLS` tuples consolidate into a single ordered dict:

```python
PNODE_RESPONSES: dict[str, str] = {
    "primary":     "congestion_price_rt_cluster_mean",
    "total_lmp":   "total_lmp_rt_cluster_mean",
    "ox":          "congestion_price_rt_ox",
    "bristers":    "congestion_price_rt_bristers",
    "dom_zonal":   "congestion_price_rt_dom_zonal",
    "ashburn_tx1": "congestion_price_rt_ashburn_tx1",
    "ashburn_tx2": "congestion_price_rt_ashburn_tx2",
}
```

`run_all` flow (in order):

1. **TAR** — fit for each pnode in `PNODE_RESPONSES`; write to `outputs/tar/<label>.json`. Skip if response column is empty.
2. **QR (existing, filtered, at TAR's ĉ)** — single fit on primary cluster; write to `outputs/qr/filtered_at_tar_c.json`.
3. **Mechanism** — write to `outputs/mechanism/validation.json`.
4. **Subsample bootstrap** — write to `outputs/robustness/subsample_bootstrap.parquet`.
5. **NEW: QR-full** — fit per pnode; write to `outputs/qr_full/<label>.json`. Skip if response column is empty.
6. **NEW: GPD** — fit per pnode; write to `outputs/gpd/<label>.json`. Skip if response column is empty.

Each method's `run_*` function creates its parent dir via `out_path.parent.mkdir(parents=True, exist_ok=True)`.

### CLI flags

Extend `_build_arg_parser` with:

```python
p.add_argument("--qr-full-n-boot", type=int, default=200,
               help="Bootstrap reps for QR-full slope CI.")
p.add_argument("--gpd-n-boot", type=int, default=200,
               help="Bootstrap reps for GPD shape CI and conditional p-value.")
```

Existing flags preserved: `--panel`, `--data-root`, `--out-root`, `--n-boot`, `--n-subsample-reps`.

## Testing strategy

Per the project's TDD + multi-file-module convention (see `memory/feedback_plan_execution.md`). All synthetic-DGP unit tests use fixed seeds for determinism.

### `tests/analysis/test_qr_full.py` (~8 tests)

1. `test_fit_qr_full_recovers_planted_slope` — `Y = 5 + 2·Z + 3·hour_sin + ε`; fit at `τ=0.5`; assert `|z_slope − 2| < 0.1`.
2. `test_fit_qr_full_no_signal_gives_high_p` — `Y = pure noise, no Z dependence`; assert `z_slope_p_value > 0.05`.
3. `test_fit_qr_full_bootstrap_ci_is_non_degenerate` — bootstrap CI is finite, has positive width, and brackets the point estimate. (Full coverage-rate testing would require many simulations and is too slow for unit tests; an end-to-end coverage study can be a separate validation script if reviewer requests.)
4. `test_fit_qr_full_validates_length_mismatch` — `Y`/`Z`/`hour`/`month` length mismatch raises `ValueError`.
5. `test_fit_qr_full_validates_no_nan` — arrays with NaN raise `ValueError` (caller-clean precondition).
6. `test_fit_qr_full_year_fe_adds_year_dummies` — when `year` is passed, `covariate_coefs` contains `year_*` keys.
7. `test_run_qr_full_writes_expected_json_schema` — write to `tmp_path`; parse; assert top-level keys (`fits`, `fits_year_fe`, etc.) present.
8. `test_run_qr_full_writes_three_taus_per_spec` — `len(payload["fits"]) == 3 and len(payload["fits_year_fe"]) == 3`.

### `tests/analysis/test_gpd.py` (~7 tests)

1. `test_fit_gpd_recovers_planted_shape_and_scale` — simulate GPD(`ξ=0.3, σ=2`) above threshold 10; fit; assert `|ξ − 0.3| < 0.1` and `|σ − 2| < 0.3`.
2. `test_fit_gpd_recovers_xi_near_zero_for_exponential` — simulate exponential (mean=5); assert `|ξ| < 0.1`.
3. `test_gpd_threshold_sweep_returns_count_equal_to_quantile_count` — pass 4 quantiles; assert `len(results) == 4`.
4. `test_gpd_conditional_detects_z_dependent_shape` — DGP: `ξ = 0.5 if Z > median else 0.1`; assert `shape_diff > 0.2` and `bootstrap_p_value < 0.05`.
5. `test_gpd_conditional_null_when_z_independent` — DGP: `ξ = 0.3` regardless of `Z`; assert `bootstrap_p_value > 0.20` (broad check, not exact).
6. `test_run_gpd_writes_expected_json_schema` — top-level keys (`threshold_sweep`, `conditional_z`); inner shape correct.
7. `test_fit_gpd_threshold_above_max_raises` — `threshold > Y.max()` raises `ValueError`.

### `tests/analysis/test_run.py` (modified)

Update `test_run_all_writes_all_outputs` to check the new paths:

```
outputs/tar/{primary,total_lmp,ox,bristers,dom_zonal,ashburn_tx1,ashburn_tx2}.json
outputs/qr/filtered_at_tar_c.json
outputs/qr_full/{primary,total_lmp,ox,bristers,dom_zonal,ashburn_tx1,ashburn_tx2}.json
outputs/gpd/{primary,total_lmp,ox,bristers,dom_zonal,ashburn_tx1,ashburn_tx2}.json
outputs/mechanism/validation.json
outputs/robustness/subsample_bootstrap.parquet
```

Target: **165 tests passing** after this work (current 145 + 8 QR-full + 7 GPD + integration updates).

## Wall time

| Phase | Cost (n_boot=200, full panel) |
|---|---|
| Existing pipeline (TAR + QR + mechanism + subsample) | ~5 min |
| QR-full: 3 τ × 2 specs × 200 boot × 7 pnodes | ~7 min |
| GPD: (4 sweep + 1 conditional × 2 subsets) × 200 boot × 7 pnodes | ~4 min |
| **Total `surg-analyze` after extension** | **~16 min** |

For faster exploratory runs: `--qr-full-n-boot 50 --gpd-n-boot 50` drops total to ~7 min.

## Implementation guidance

When the writing-plans skill produces the task-by-task implementation plan from this spec, suggested task sequencing:

1. Reorganize output paths in `run.py` + update `test_run.py` integration test. Keep all existing fits working under new paths before adding new modules. Verify 145 tests still pass.
2. Implement `fit_gpd` (no bootstrap, no sweep). Unit tests for MLE recovery + edge cases.
3. Implement `gpd_threshold_sweep` and `gpd_conditional_on_z` (adds bootstrap). Unit tests for the conditional mechanism test.
4. Implement `run_gpd`. JSON schema test.
5. Implement `fit_qr_full` (primary spec only, no bootstrap). Unit tests for slope recovery + edge cases.
6. Add bootstrap CI to `fit_qr_full`. Unit tests for CI containing truth.
7. Add year-FE specification path. Unit tests for year-dummy presence in coef dict.
8. Implement `run_qr_full`. JSON schema test.
9. Wire `run_qr_full` + `run_gpd` into `run_all`. Update integration test for all new paths.
10. Final verification: `pytest tests/ -v` shows 165 passed; `surg-analyze` end-to-end on the real panel writes the expected output tree.

Use `superpowers:subagent-driven-development` per the validated workflow in `memory/feedback_plan_execution.md`.
