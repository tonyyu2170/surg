# Conditional-Z Robustness Battery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended per `memory/feedback_plan_execution.md`) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the A/C/F conditional-Z robustness battery + Holm–Bonferroni roll-up specified in `docs/decisions.md` § "2026-05-14 — Pre-registration: conditional-Z robustness battery". Produces `outputs/gpd/conditional_z_robustness.json` after a `surg-analyze` run, with per-spec results, two-sided bootstrap p-values, and a family-wise inferential verdict.

**Architecture:** One new public function (`gpd_quantile_split_on_z`) generalizing the existing `gpd_conditional_on_z` to N-way splits; one new public utility (`holm_bonferroni_two_sided`); one new orchestrator (`run_conditional_z_robustness`) that runs Spec A (quartile-split at 95th-pct, full panel), Spec C (median-split at 99th-pct, full panel), Spec F (median-split at within-filter 95th-pct, filtered subset), converts each spec's bootstrap diffs to two-sided p-values, and applies Holm–Bonferroni. All three functions land in `src/surg/analysis/gpd.py` alongside the existing module. The orchestrator wires into `run_all` after the existing per-pnode `run_gpd` loop.

**Tech Stack:** Python 3.11+, scipy (`scipy.stats.genpareto` — existing), numpy, pandas, pyarrow (parquet — existing), pytest. No new dependencies.

**Pre-reg reference:** `docs/decisions.md` § "2026-05-14 — Pre-registration: conditional-Z robustness battery (A/C/F + gated B)". Decision rules and roll-up tables in that entry are normative — this plan only implements the code that produces the numbers; the application-of-pre-reg entry (a separate decisions.md entry written after this plan's numbers run) interprets them.

**Execution worktree:** Recommended to execute on a sibling `feature/conditional-z-robustness` worktree under `../surg-conditional-z`, matching the Strategy C implementation pattern (see `memory/feedback_branch_lifecycle.md`). FF-merge back to main after Task 5 verification passes.

---

## Task 1: `gpd_quantile_split_on_z` (Spec A engine)

**Why this task exists:** Spec A in the pre-reg requires a 4-way quartile-split on Z within exceedances, with bootstrap CI on the (Q4 − Q1) extreme-shape contrast. The existing `gpd_conditional_on_z` only supports 2-way median split. This task generalizes to N-way without modifying the existing 2-way function (which is used by `run_gpd` and must not change behavior).

**Files:**
- Modify: `src/surg/analysis/gpd.py` (add `GPDQuantileSplitResult` dataclass + `gpd_quantile_split_on_z` function)
- Modify: `tests/analysis/test_gpd.py` (add ~5 new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/analysis/test_gpd.py`:

```python
# ─── gpd_quantile_split_on_z (Spec A engine) ──────────────────────────────────

from surg.analysis.gpd import GPDQuantileSplitResult, gpd_quantile_split_on_z


def test_gpd_quantile_split_detects_monotone_shape():
    """When DGP has monotonically increasing GPD shape across Z quartiles,
    gpd_quantile_split_on_z should detect a positive extreme_contrast
    (ξ_Q4 − ξ_Q1) and a two-sided bootstrap p < 0.05."""
    rng = np.random.default_rng(seed=42)
    n = 12000
    Z = rng.uniform(0, 10, size=n)
    # Z-dependent GPD shape: Q1 → 0.1, Q2 → 0.3, Q3 → 0.5, Q4 → 0.7
    Y = np.empty(n)
    z_quartile_edges = np.quantile(Z, [0.25, 0.5, 0.75])
    shape_by_q = [0.1, 0.3, 0.5, 0.7]
    for i in range(4):
        if i == 0:
            mask = Z <= z_quartile_edges[0]
        elif i == 3:
            mask = Z > z_quartile_edges[2]
        else:
            mask = (Z > z_quartile_edges[i - 1]) & (Z <= z_quartile_edges[i])
        n_i = int(mask.sum())
        Y[mask] = stats.genpareto.rvs(
            c=shape_by_q[i], scale=2.0, size=n_i, random_state=rng
        )

    result = gpd_quantile_split_on_z(
        Y, Z,
        threshold_quantile=0.5,
        split_quantiles=(0.25, 0.5, 0.75),
        n_boot=100,
        seed=0,
    )

    assert isinstance(result, GPDQuantileSplitResult)
    assert len(result.quantile_fits) == 4
    assert len(result.quantile_edges) == 3
    assert tuple(result.split_quantiles) == (0.25, 0.5, 0.75)

    # ξ trajectory should be roughly monotonically increasing
    shapes = [fit.shape for fit in result.quantile_fits]
    assert shapes[3] > shapes[0], f"Q4 ξ not > Q1 ξ: {shapes}"
    # extreme_contrast (Q4 − Q1) should be clearly positive
    assert result.extreme_contrast > 0.3, \
        f"extreme_contrast too small: {result.extreme_contrast}"
    # Two-sided p-value should reject H0
    assert result.extreme_contrast_bootstrap_p_value < 0.05, \
        f"failed to detect quartile-monotone shape: p={result.extreme_contrast_bootstrap_p_value}"


def test_gpd_quantile_split_n2_matches_median_split_shape_diff():
    """gpd_quantile_split_on_z with split_quantiles=(0.5,) should reproduce
    the same per-subset shape estimates as gpd_conditional_on_z with
    z_split_quantile=0.5. The bootstrap CI on extreme_contrast may differ
    slightly because of independent RNG streams, but the point estimates
    must match exactly."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    Z = rng.uniform(0, 10, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    n_way = gpd_quantile_split_on_z(
        Y, Z, threshold_quantile=0.5, split_quantiles=(0.5,),
        n_boot=50, seed=0,
    )
    two_way = gpd_conditional_on_z(
        Y, Z, threshold_quantile=0.5, z_split_quantile=0.5,
        n_boot=50, seed=0,
    )

    assert len(n_way.quantile_fits) == 2
    # First quantile fit corresponds to low-Z; second to high-Z
    assert n_way.quantile_fits[0].shape == pytest.approx(two_way.low_z.shape)
    assert n_way.quantile_fits[1].shape == pytest.approx(two_way.high_z.shape)
    # extreme_contrast (last - first) == shape_diff (high - low) for N=2
    assert n_way.extreme_contrast == pytest.approx(two_way.shape_diff)


def test_gpd_quantile_split_validates_split_quantiles_sorted_in_range():
    """split_quantiles must be strictly ascending and in (0, 1)."""
    rng = np.random.default_rng(seed=42)
    n = 1000
    Y = rng.exponential(scale=5.0, size=n)
    Z = rng.uniform(0, 10, size=n)

    with pytest.raises(ValueError, match="split_quantiles"):
        gpd_quantile_split_on_z(Y, Z, split_quantiles=(0.5, 0.25), n_boot=10)
    with pytest.raises(ValueError, match="split_quantiles"):
        gpd_quantile_split_on_z(Y, Z, split_quantiles=(0.0, 0.5), n_boot=10)
    with pytest.raises(ValueError, match="split_quantiles"):
        gpd_quantile_split_on_z(Y, Z, split_quantiles=(0.5, 1.0), n_boot=10)


def test_gpd_quantile_split_raises_on_small_quartile():
    """If a quartile subset has fewer than 10 exceedances, the fit cannot
    proceed and the function raises ValueError (no silent partial result).

    Constructed deterministically: 25 large values + 475 small values, with
    threshold_quantile=0.95 capturing exactly the 25 large ones. Quartile
    split → ~6 per quartile, failing the per-subset n≥10 check while
    comfortably passing the overall n_exc≥20 check.
    """
    rng = np.random.default_rng(seed=42)
    large = rng.uniform(100, 200, size=25)
    small = rng.uniform(1, 10, size=475)
    Y = np.concatenate([large, small])
    Z = rng.uniform(0, 10, size=500)  # uniform Z so quartiles are balanced

    with pytest.raises(ValueError, match="too few exceedances per subset"):
        gpd_quantile_split_on_z(
            Y, Z, threshold_quantile=0.95, split_quantiles=(0.25, 0.5, 0.75),
            n_boot=10, seed=0,
        )


def test_gpd_quantile_split_validates_length_mismatch():
    """Y and Z must have the same length."""
    rng = np.random.default_rng(seed=42)
    Y = rng.exponential(scale=5.0, size=100)
    Z = rng.uniform(0, 10, size=50)
    with pytest.raises(ValueError, match="length"):
        gpd_quantile_split_on_z(Y, Z, split_quantiles=(0.5,), n_boot=10)


def test_gpd_quantile_split_two_sided_p_value_for_null_dgp():
    """When DGP is Z-independent, the two-sided p-value should be non-tiny
    (broad null check, not exact)."""
    rng = np.random.default_rng(seed=42)
    n = 4000
    Z = rng.uniform(0, 10, size=n)
    Y = stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng)

    result = gpd_quantile_split_on_z(
        Y, Z, threshold_quantile=0.5, split_quantiles=(0.25, 0.5, 0.75),
        n_boot=100, seed=0,
    )

    assert result.extreme_contrast_bootstrap_p_value > 0.10, \
        f"false-positive quartile-dependence: p={result.extreme_contrast_bootstrap_p_value}"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_gpd_quantile_split_detects_monotone_shape -v
```

Expected: FAIL with `ImportError: cannot import name 'GPDQuantileSplitResult'` (and likewise for `gpd_quantile_split_on_z`).

- [ ] **Step 3: Add `GPDQuantileSplitResult` dataclass and `gpd_quantile_split_on_z` to `src/surg/analysis/gpd.py`**

Open `src/surg/analysis/gpd.py`. Append after the existing `gpd_conditional_on_z` function and before `_nan_to_none`:

```python
@dataclass(frozen=True, slots=True)
class GPDQuantileSplitResult:
    """N-way Z-quantile split of GPD fits on exceedances of a fixed threshold.

    `quantile_fits` has length `len(split_quantiles) + 1` (N+1 groups for N
    split points). `quantile_edges` are the empirical Z values at each
    `split_quantile` computed within the exceedance set. `extreme_contrast`
    is the (last − first) shape contrast — for quartile split this is the
    headline Q4 − Q1.

    The two-sided bootstrap p-value tests H0: extreme_contrast = 0 against
    a two-sided alternative; the sign of the CI determines the direction
    of any rejection. Bootstrap protocol: resample exceedance row indices
    (paired Y,Z), recompute quantile edges inside each rep, refit all N+1
    GPDs per rep.
    """
    threshold_quantile: float
    threshold_value: float
    split_quantiles: tuple[float, ...]
    quantile_edges: tuple[float, ...]
    quantile_fits: tuple[GPDFitResult, ...]
    extreme_contrast: float                                    # ξ_last − ξ_first
    extreme_contrast_bootstrap_ci_95: tuple[float, float]
    extreme_contrast_bootstrap_p_value: float                  # two-sided


def gpd_quantile_split_on_z(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    *,
    threshold_quantile: float = 0.95,
    split_quantiles: tuple[float, ...] = (0.25, 0.5, 0.75),
    n_boot: int = 200,
    seed: int = 0,
) -> GPDQuantileSplitResult:
    """N-way GPD fit conditional on Z-quantile groups within exceedances of Y.

    Generalizes `gpd_conditional_on_z` (which is fixed at N=2). Procedure:
      1. threshold = empirical quantile of Y at `threshold_quantile`
      2. exceedances = rows where Y > threshold
      3. quantile_edges = empirical quantile of Z[exceedances] at each
         `split_quantile` — yields N edges for N+1 groups
      4. Fit GPD on each of the N+1 groups independently (each carries the
         parent `threshold_quantile`, same convention as `gpd_conditional_on_z`)
      5. Bootstrap: resample exceedance row indices, recompute edges per rep,
         refit all groups, record extreme_contrast = ξ_last − ξ_first. Report
         empirical 2.5%/97.5% quantiles of resampled contrasts as the 95% CI,
         and two-sided bootstrap p-value = 2 * min(P(contrast ≤ 0), P(contrast ≥ 0)).

    Note on p-value semantics: the returned two-sided p-value is an empirical
    bootstrap "achieved significance level" (2 * min(P(arr ≤ 0), P(arr ≥ 0))),
    matching the heuristic convention used by `gpd_conditional_on_z`. It is
    not a formal hypothesis-test p-value; Holm–Bonferroni corrections applied
    downstream inherit this heuristic status.

    Raises:
      ValueError if length(Y) ≠ length(Z), if `split_quantiles` is unsorted /
      out-of-range, if too few exceedances overall (< 20), or if any quantile
      group ends up with < 10 exceedances (fit too noisy).
    """
    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    if len(Y_arr) != len(Z_arr):
        raise ValueError(f"Y and Z must have equal length; got {len(Y_arr)} vs {len(Z_arr)}")
    if not 0.0 < threshold_quantile < 1.0:
        raise ValueError(f"threshold_quantile must be in (0,1); got {threshold_quantile}")
    if len(split_quantiles) == 0:
        raise ValueError("split_quantiles must have at least one entry")
    if not all(0.0 < q < 1.0 for q in split_quantiles):
        raise ValueError(f"split_quantiles must be in (0,1); got {split_quantiles}")
    if list(split_quantiles) != sorted(set(split_quantiles)):
        raise ValueError(
            f"split_quantiles must be strictly ascending and unique; got {split_quantiles}"
        )

    threshold = float(np.quantile(Y_arr, threshold_quantile))
    exceed_mask = Y_arr > threshold
    Y_exc = Y_arr[exceed_mask]
    Z_exc = Z_arr[exceed_mask]
    if len(Y_exc) < 20:
        raise ValueError(
            f"too few exceedances ({len(Y_exc)}) above threshold_quantile={threshold_quantile} "
            f"for an N-way Z-split test (need ≥20)"
        )

    # N edges → N+1 groups indexed 0..N
    edges = tuple(float(np.quantile(Z_exc, q)) for q in split_quantiles)
    group_masks = _assign_groups(Z_exc, edges)
    counts = tuple(int(m.sum()) for m in group_masks)
    if any(c < 10 for c in counts):
        raise ValueError(
            f"too few exceedances per subset at split_quantiles={split_quantiles}: "
            f"counts={counts} (each needs ≥10)"
        )

    fits: list[GPDFitResult] = []
    for mask in group_masks:
        _base = fit_gpd(Y_exc[mask], threshold=threshold)
        fits.append(GPDFitResult(
            threshold_quantile=float(threshold_quantile),
            threshold_value=_base.threshold_value,
            shape=_base.shape,
            shape_se=_base.shape_se,
            shape_bootstrap_ci_95=_base.shape_bootstrap_ci_95,
            scale=_base.scale,
            scale_se=_base.scale_se,
            n_exceedances=_base.n_exceedances,
        ))
    extreme_contrast = fits[-1].shape - fits[0].shape

    # Bootstrap: pair-resample exceedance indices, recompute edges per rep,
    # refit all groups. Skip reps where any group ends up with < 10 obs.
    rng = np.random.default_rng(seed)
    n_exc = len(Y_exc)
    contrasts: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_exc, size=n_exc)
        Y_b = Y_exc[idx]
        Z_b = Z_exc[idx]
        edges_b = tuple(float(np.quantile(Z_b, q)) for q in split_quantiles)
        masks_b = _assign_groups(Z_b, edges_b)
        if any(m.sum() < 10 for m in masks_b):
            continue
        try:
            shapes_b = [fit_gpd(Y_b[m], threshold=threshold).shape for m in masks_b]
        except ValueError:
            continue
        contrasts.append(shapes_b[-1] - shapes_b[0])

    if len(contrasts) < 20:
        ci: tuple[float, float] = (float("nan"), float("nan"))
        p_two_sided = float("nan")
    else:
        arr = np.asarray(contrasts)
        ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
        p_left = float(np.mean(arr <= 0.0))
        p_right = float(np.mean(arr >= 0.0))
        p_two_sided = min(1.0, 2.0 * min(p_left, p_right))

    return GPDQuantileSplitResult(
        threshold_quantile=float(threshold_quantile),
        threshold_value=threshold,
        split_quantiles=tuple(float(q) for q in split_quantiles),
        quantile_edges=edges,
        quantile_fits=tuple(fits),
        extreme_contrast=float(extreme_contrast),
        extreme_contrast_bootstrap_ci_95=ci,
        extreme_contrast_bootstrap_p_value=p_two_sided,
    )


def _assign_groups(Z: np.ndarray, edges: tuple[float, ...]) -> list[np.ndarray]:
    """Return a list of boolean masks partitioning Z into len(edges)+1 groups.

    Group i contains rows where edges[i-1] < Z <= edges[i], with edges[-1] = -inf
    for the first group and edges[len(edges)] = +inf for the last. Edges should
    be sorted ascending; behavior on unsorted edges is undefined.
    """
    masks: list[np.ndarray] = []
    prev = -np.inf
    for edge in edges:
        masks.append((Z > prev) & (Z <= edge))
        prev = edge
    masks.append(Z > prev)
    return masks
```

Note: the helper `_assign_groups` is added once and reused by both the main fit and the bootstrap loop.

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_gpd_quantile_split_detects_monotone_shape \
                 tests/analysis/test_gpd.py::test_gpd_quantile_split_n2_matches_median_split_shape_diff \
                 tests/analysis/test_gpd.py::test_gpd_quantile_split_validates_split_quantiles_sorted_in_range \
                 tests/analysis/test_gpd.py::test_gpd_quantile_split_raises_on_small_quartile \
                 tests/analysis/test_gpd.py::test_gpd_quantile_split_validates_length_mismatch \
                 tests/analysis/test_gpd.py::test_gpd_quantile_split_two_sided_p_value_for_null_dgp \
                 -v
```

Expected: 6 PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `178 passed` (172 prior + 6 new). No failures.

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "$(cat <<'EOF'
feat(analysis): add gpd_quantile_split_on_z for Spec A of conditional-Z battery

N-way Z-quantile generalization of gpd_conditional_on_z. Used by Spec A of
the 2026-05-14 conditional-Z robustness pre-reg: quartile-split at the 95th-pct
LMP threshold on the full panel, with bootstrap CI on the (Q4 - Q1) extreme
shape contrast and a two-sided bootstrap p-value.

The existing gpd_conditional_on_z (2-way median split) is unchanged; the new
function returns a GPDQuantileSplitResult dataclass that carries the full
ξ trajectory across groups. A private _assign_groups helper handles the
N+1 partitioning consistently between the main fit and the bootstrap loop.

6 new tests bring tests/analysis/test_gpd.py to 18 GPD-module tests; full
suite passes at 178 tests.
EOF
)"
```

---

## Task 2: `holm_bonferroni_two_sided` utility

**Why this task exists:** The pre-reg specifies two-sided Holm–Bonferroni across the three battery specs at α = 0.05 for the family-wise inferential claim. This task adds the small utility function so the orchestrator (Task 3) can apply the correction consistently.

**Files:**
- Modify: `src/surg/analysis/gpd.py` (add `holm_bonferroni_two_sided` function)
- Modify: `tests/analysis/test_gpd.py` (add ~5 new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/analysis/test_gpd.py`:

```python
# ─── holm_bonferroni_two_sided (family-wise correction utility) ───────────────

from surg.analysis.gpd import holm_bonferroni_two_sided


def test_holm_all_significant():
    """All p-values below α/k threshold → all rejected, family-wise rejection."""
    result = holm_bonferroni_two_sided(
        labeled_p_values={"a": 0.001, "b": 0.005, "c": 0.012},
        alpha=0.05,
    )
    assert result["rejections"] == {"a": True, "b": True, "c": True}
    assert result["family_wise_rejection"] is True
    assert result["alpha"] == 0.05
    # sorted_order: ascending p-values; first rank gets α/3, next α/2, last α/1
    assert result["sorted_order"] == ["a", "b", "c"]
    # Adjusted thresholds returned for downstream reporting
    assert result["adjusted_thresholds"]["a"] == pytest.approx(0.05 / 3, rel=1e-9)
    assert result["adjusted_thresholds"]["b"] == pytest.approx(0.05 / 2, rel=1e-9)
    assert result["adjusted_thresholds"]["c"] == pytest.approx(0.05 / 1, rel=1e-9)


def test_holm_stops_at_first_non_rejection():
    """Holm is sequential: the first failure halts the procedure for all
    higher-ranked p-values, even if those would individually pass at their
    own adjusted thresholds (a=0.05 won't be considered if b at α/2 failed)."""
    result = holm_bonferroni_two_sided(
        labeled_p_values={"a": 0.001, "b": 0.030, "c": 0.045},
        alpha=0.05,
    )
    # a: 0.001 < 0.05/3=0.0167 → reject
    # b: 0.030 > 0.05/2=0.025 → stop, do not reject b OR c
    assert result["rejections"] == {"a": True, "b": False, "c": False}
    assert result["family_wise_rejection"] is False


def test_holm_first_p_above_alpha_over_k_rejects_nothing():
    """If the smallest p-value already fails its α/k threshold, nothing is
    rejected and family-wise rejection is False."""
    result = holm_bonferroni_two_sided(
        labeled_p_values={"a": 0.02, "b": 0.03, "c": 0.04},
        alpha=0.05,
    )
    # smallest = 0.02 > 0.05/3 = 0.0167 → reject nothing
    assert result["rejections"] == {"a": False, "b": False, "c": False}
    assert result["family_wise_rejection"] is False


def test_holm_handles_nan_p_value_as_non_rejection():
    """An inconclusive spec (NaN p-value) is treated as 'cannot reject' —
    it is sorted to the end (with p=+inf) and is never rejected, but does
    not affect whether earlier specs in the order can be rejected at their
    own adjusted thresholds."""
    result = holm_bonferroni_two_sided(
        labeled_p_values={"a": 0.005, "b": float("nan"), "c": 0.020},
        alpha=0.05,
    )
    # a: 0.005 < 0.05/3 = 0.0167 → reject
    # c: 0.020 < 0.05/2 = 0.025 → reject (c is now rank 2)
    # b: NaN → never rejected
    assert result["rejections"] == {"a": True, "b": False, "c": True}
    # b cannot be rejected → family-wise is False (not all rejected)
    assert result["family_wise_rejection"] is False
    assert result["sorted_order"] == ["a", "c", "b"]


def test_holm_validates_alpha_in_open_unit_interval():
    """α must be in (0, 1)."""
    with pytest.raises(ValueError, match="alpha"):
        holm_bonferroni_two_sided({"a": 0.01}, alpha=0.0)
    with pytest.raises(ValueError, match="alpha"):
        holm_bonferroni_two_sided({"a": 0.01}, alpha=1.0)


def test_holm_validates_p_value_range():
    """p-values must be in [0, 1] or NaN; values outside this range raise."""
    with pytest.raises(ValueError, match="p-value"):
        holm_bonferroni_two_sided({"a": -0.01}, alpha=0.05)
    with pytest.raises(ValueError, match="p-value"):
        holm_bonferroni_two_sided({"a": 1.01}, alpha=0.05)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_holm_all_significant -v
```

Expected: FAIL with `ImportError: cannot import name 'holm_bonferroni_two_sided'`.

- [ ] **Step 3: Add `holm_bonferroni_two_sided` to `src/surg/analysis/gpd.py`**

Open `src/surg/analysis/gpd.py`. Append after `_assign_groups` (added in Task 1) and before `_nan_to_none`:

```python
def holm_bonferroni_two_sided(
    labeled_p_values: dict[str, float],
    *,
    alpha: float = 0.05,
) -> dict:
    """Apply Holm–Bonferroni step-down correction to a family of two-sided p-values.

    Procedure (Holm 1979):
      1. Sort p-values ascending. NaN p-values (inconclusive specs) sort to
         the end (treated as p = +inf for ranking; never rejected).
      2. Test the smallest at α/k where k is the family size, the next at
         α/(k-1), … , the largest at α/1.
      3. Stop at the first non-rejection: all p-values not yet considered
         remain non-rejected, regardless of their value.

    Returns a dict with:
      - "alpha": the input α
      - "sorted_order": list of input labels in ascending-p order (NaNs last)
      - "adjusted_thresholds": dict mapping each label to its α/(k-rank) threshold
      - "rejections": dict mapping each label to a bool
      - "family_wise_rejection": True iff every input was rejected (i.e., the
        family-wise inferential statement is supported)

    Raises:
      ValueError if α ∉ (0, 1) or any p-value falls outside [0, 1] (NaN is allowed).
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1); got {alpha}")
    for label, p in labeled_p_values.items():
        if math.isnan(p):
            continue
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p-value for {label!r} must be in [0, 1] or NaN; got {p}")

    k = len(labeled_p_values)
    # Sort ascending; NaN goes last
    def _sort_key(item: tuple[str, float]) -> tuple[int, float]:
        label, p = item
        if math.isnan(p):
            return (1, 0.0)  # NaN bucket — order within doesn't matter for the alg
        return (0, p)

    sorted_items = sorted(labeled_p_values.items(), key=_sort_key)
    sorted_order = [label for label, _ in sorted_items]
    adjusted_thresholds: dict[str, float] = {}
    rejections: dict[str, bool] = {}
    stopped = False
    for rank, (label, p) in enumerate(sorted_items):
        threshold = alpha / (k - rank)
        adjusted_thresholds[label] = threshold
        if stopped or math.isnan(p) or p > threshold:
            rejections[label] = False
            stopped = True
        else:
            rejections[label] = True

    return {
        "alpha": alpha,
        "sorted_order": sorted_order,
        "adjusted_thresholds": adjusted_thresholds,
        "rejections": rejections,
        "family_wise_rejection": all(rejections.values()),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_holm_all_significant \
                 tests/analysis/test_gpd.py::test_holm_stops_at_first_non_rejection \
                 tests/analysis/test_gpd.py::test_holm_first_p_above_alpha_over_k_rejects_nothing \
                 tests/analysis/test_gpd.py::test_holm_handles_nan_p_value_as_non_rejection \
                 tests/analysis/test_gpd.py::test_holm_validates_alpha_in_open_unit_interval \
                 tests/analysis/test_gpd.py::test_holm_validates_p_value_range \
                 -v
```

Expected: 6 PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `184 passed` (178 from Task 1 + 6 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "$(cat <<'EOF'
feat(analysis): add holm_bonferroni_two_sided for the conditional-Z battery

Step-down Holm-Bonferroni correction at alpha=0.05 across the three pre-reg
battery specs (A: quartile-split 95th, C: median-split 99th, F: within-filter
median-split 95th). Two-sided per the pre-reg's decision tables, which admit
both sign directions as substantively meaningful.

NaN p-values (inconclusive spec outcomes — fit failure due to power) sort
to the end and are treated as cannot-reject without halting evaluation of
better-ranked specs. Family-wise rejection requires every spec to clear its
adjusted threshold in order.

6 new tests; full suite at 184.
EOF
)"
```

---

## Task 3: `run_conditional_z_robustness` orchestrator

**Why this task exists:** The pre-reg locks three specs (A/C/F) plus a Holm–Bonferroni roll-up. This task is the orchestrator that runs all three, converts each spec's bootstrap diffs into a two-sided p-value, applies the family-wise correction, and writes a single JSON output file containing all per-spec results + the family-wise verdict.

**Files:**
- Modify: `src/surg/analysis/gpd.py` (add `run_conditional_z_robustness` function + supporting JSON helpers)
- Modify: `tests/analysis/test_gpd.py` (add ~4 new tests)

- [ ] **Step 1: Write the failing tests**

Append to `tests/analysis/test_gpd.py`:

```python
# ─── run_conditional_z_robustness (orchestrator) ──────────────────────────────

from surg.analysis.gpd import run_conditional_z_robustness


def _synthetic_battery_panel(n: int, seed: int) -> pd.DataFrame:
    """Build a synthetic panel matching the columns run_conditional_z_robustness
    consumes: response (Y), threshold variable (Z), filter mask.

    Generates a Z-dependent GPD where high-Z exceedances have lighter tails
    than low-Z (matching the actual 2026-05-14 production finding's
    direction). The filter mask retains a fraction of rows.
    """
    rng = np.random.default_rng(seed=seed)
    Z = rng.uniform(0, 10, size=n)
    Y = np.empty(n)
    # Median-split: shape=0.5 below, shape=0.2 above (matches production finding)
    high_z = Z > 5.0
    Y[~high_z] = stats.genpareto.rvs(c=0.5, scale=2.0, size=int((~high_z).sum()), random_state=rng)
    Y[high_z] = stats.genpareto.rvs(c=0.2, scale=2.0, size=int(high_z.sum()), random_state=rng)

    # Filter: keep ~6% of rows (matches the proposal's 2-5 AM × shoulder share)
    filter_mask = rng.random(size=n) < 0.064
    return pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": Y,
        "Z_target": Z,
        "passes_proposal_filter": filter_mask,
    })


def test_run_conditional_z_robustness_writes_expected_json(tmp_path: Path):
    """End-to-end: run_conditional_z_robustness writes a JSON file with the
    expected schema (per-spec blocks for A/C/F + a holm_bonferroni block)."""
    panel = _synthetic_battery_panel(n=12000, seed=42)
    out = tmp_path / "gpd" / "conditional_z_robustness.json"

    run_conditional_z_robustness(
        panel,
        out_path=out,
        response_col="Y_target",
        pnode_label="test",
        threshold_col="Z_target",
        filter_col="passes_proposal_filter",
        n_boot=50,
        seed=0,
    )

    assert out.exists(), f"orchestrator did not write {out}"
    payload = json.loads(out.read_text())

    # Top-level shape
    assert payload["pnode_label"] == "test"
    assert payload["response_col"] == "Y_target"
    assert payload["threshold_col"] == "Z_target"
    assert payload["filter_col"] == "passes_proposal_filter"
    assert payload["n_total_panel"] == 12000

    # Spec A: quartile split, full panel
    spec_a = payload["spec_a_quartile_split"]
    assert spec_a["status"] == "fit"
    assert spec_a["scope"] == "full_panel"
    assert spec_a["threshold_quantile"] == pytest.approx(0.95)
    a_result = spec_a["result"]
    assert tuple(a_result["split_quantiles"]) == (0.25, 0.5, 0.75)
    assert len(a_result["quantile_fits"]) == 4
    assert "extreme_contrast" in a_result
    assert "extreme_contrast_bootstrap_ci_95" in a_result
    assert "extreme_contrast_bootstrap_p_value" in a_result

    # Spec C: median-split at 99th-pct, full panel
    spec_c = payload["spec_c_99th_pct"]
    assert spec_c["scope"] == "full_panel"
    assert spec_c["threshold_quantile"] == pytest.approx(0.99)
    # Status may be "fit" or "inconclusive" depending on synthetic n;
    # both are valid outcomes for this test (we only check the schema).
    assert spec_c["status"] in {"fit", "inconclusive"}
    if spec_c["status"] == "fit":
        assert "shape_diff" in spec_c["result"]
        assert "two_sided_p_value" in spec_c["result"]

    # Spec F: within-filter median-split at 95th
    spec_f = payload["spec_f_within_filter"]
    assert spec_f["scope"] == "filtered_subset"
    assert spec_f["filter_col"] == "passes_proposal_filter"
    assert spec_f["threshold_quantile"] == pytest.approx(0.95)
    assert spec_f["status"] in {"fit", "inconclusive"}

    # Holm-Bonferroni roll-up
    holm = payload["holm_bonferroni"]
    assert holm["alpha"] == pytest.approx(0.05)
    assert set(holm["two_sided_p_values"].keys()) == {"spec_a", "spec_c", "spec_f"}
    assert set(holm["rejections"].keys()) == {"spec_a", "spec_c", "spec_f"}
    assert isinstance(holm["family_wise_rejection"], bool)


def test_run_conditional_z_robustness_handles_spec_c_fit_failure(tmp_path: Path):
    """When the 99th-pct threshold leaves too few exceedances per Z-half,
    Spec C must be reported as 'inconclusive' (status string), not crash
    the orchestrator. The other specs still run; Holm sees NaN for C."""
    rng = np.random.default_rng(seed=42)
    n = 800  # at 99th-pct: ~8 exceedances total, far below the n=20 floor
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng),
        "Z_target": rng.uniform(0, 10, size=n),
        "passes_proposal_filter": np.zeros(n, dtype=bool),
    })

    out = tmp_path / "gpd" / "small_n.json"
    run_conditional_z_robustness(
        panel, out_path=out,
        response_col="Y_target", pnode_label="small",
        threshold_col="Z_target", filter_col="passes_proposal_filter",
        n_boot=30, seed=0,
    )

    payload = json.loads(out.read_text())
    assert payload["spec_c_99th_pct"]["status"] == "inconclusive"
    assert payload["spec_c_99th_pct"]["reason"] is not None  # human-readable explanation
    assert payload["spec_c_99th_pct"]["result"] is None
    # Holm should record NaN for spec_c (which serializes to null)
    assert payload["holm_bonferroni"]["two_sided_p_values"]["spec_c"] is None
    # Spec C cannot be rejected
    assert payload["holm_bonferroni"]["rejections"]["spec_c"] is False


def test_run_conditional_z_robustness_handles_spec_f_filter_empty(tmp_path: Path):
    """When the filter mask is all-False, Spec F has no data → inconclusive."""
    rng = np.random.default_rng(seed=42)
    n = 8000
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2024-01-01", periods=n, freq="h"),
        "Y_target": stats.genpareto.rvs(c=0.3, scale=2.0, size=n, random_state=rng),
        "Z_target": rng.uniform(0, 10, size=n),
        "passes_proposal_filter": np.zeros(n, dtype=bool),
    })

    out = tmp_path / "gpd" / "empty_filter.json"
    run_conditional_z_robustness(
        panel, out_path=out,
        response_col="Y_target", pnode_label="empty",
        threshold_col="Z_target", filter_col="passes_proposal_filter",
        n_boot=30, seed=0,
    )

    payload = json.loads(out.read_text())
    assert payload["spec_f_within_filter"]["status"] == "inconclusive"
    assert payload["spec_f_within_filter"]["reason"] is not None
    assert payload["spec_f_within_filter"]["n_after_filter"] == 0


def test_run_conditional_z_robustness_serializes_nan_as_null(tmp_path: Path):
    """If any bootstrap CI or p-value is NaN, JSON output uses null, not NaN."""
    panel = _synthetic_battery_panel(n=4000, seed=0)
    out = tmp_path / "gpd" / "nan_check.json"
    run_conditional_z_robustness(
        panel, out_path=out,
        response_col="Y_target", pnode_label="nan_test",
        threshold_col="Z_target", filter_col="passes_proposal_filter",
        n_boot=20, seed=0,
    )
    text = out.read_text()
    assert "NaN" not in text, "JSON output contains literal NaN token"
    # strict json.loads validates RFC-compliance
    payload = json.loads(text)
    # If any p-value field is null, it must be None on parse (not NaN)
    for spec_key in ("spec_a", "spec_c", "spec_f"):
        p = payload["holm_bonferroni"]["two_sided_p_values"][spec_key]
        assert p is None or (isinstance(p, (int, float)) and math.isfinite(p))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_run_conditional_z_robustness_writes_expected_json -v
```

Expected: FAIL with `ImportError: cannot import name 'run_conditional_z_robustness'`.

- [ ] **Step 3: Add `run_conditional_z_robustness` and supporting helpers to `src/surg/analysis/gpd.py`**

Open `src/surg/analysis/gpd.py`. Append after `holm_bonferroni_two_sided` (added in Task 2) and before `_nan_to_none`:

```python
def _gpd_quantile_split_result_to_dict(result: GPDQuantileSplitResult) -> dict:
    return {
        "threshold_quantile": result.threshold_quantile,
        "threshold_value": result.threshold_value,
        "split_quantiles": list(result.split_quantiles),
        "quantile_edges": list(result.quantile_edges),
        "quantile_fits": [_gpd_fit_result_to_dict(f) for f in result.quantile_fits],
        "extreme_contrast": result.extreme_contrast,
        "extreme_contrast_bootstrap_ci_95": list(result.extreme_contrast_bootstrap_ci_95),
        "extreme_contrast_bootstrap_p_value": result.extreme_contrast_bootstrap_p_value,
    }


def _gpd_conditional_result_to_dict_with_two_sided(result: GPDConditionalResult) -> dict:
    """Serialize a GPDConditionalResult and add a two-sided p-value derived from
    the existing one-sided field. Two-sided = 2 * min(p_one, 1 - p_one), clipped
    to [0, 1]. NaN propagates."""
    p_one = result.shape_diff_bootstrap_p_value
    if math.isnan(p_one):
        p_two = float("nan")
    else:
        p_two = min(1.0, 2.0 * min(p_one, 1.0 - p_one))
    return {
        "threshold_quantile": result.threshold_quantile,
        "threshold_value": result.threshold_value,
        "z_split_quantile": result.z_split_quantile,
        "z_split_value": result.z_split_value,
        "low_z": _gpd_fit_result_to_dict(result.low_z),
        "high_z": _gpd_fit_result_to_dict(result.high_z),
        "shape_diff": result.shape_diff,
        "shape_diff_bootstrap_ci_95": list(result.shape_diff_bootstrap_ci_95),
        "one_sided_p_value": p_one,
        "two_sided_p_value": p_two,
    }


def run_conditional_z_robustness(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    response_col: str,
    pnode_label: str,
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    filter_col: str = "passes_proposal_filter",
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """Run the 2026-05-14 pre-registered conditional-Z robustness battery (A/C/F).

    Spec A — quartile-split at 95th-pct LMP threshold, full panel.
    Spec C — median-split at 99th-pct LMP threshold, full panel.
    Spec F — median-split at within-filter 95th-pct LMP threshold, on the
             subset where `panel[filter_col]` is True.

    For each spec, computes a two-sided bootstrap p-value (Spec A uses the
    GPDQuantileSplitResult's native two-sided p; Specs C and F convert
    `gpd_conditional_on_z`'s one-sided field via 2*min(p, 1-p)). Each spec's
    fit-failure due to power (ValueError from underlying functions) is caught
    and marked `status="inconclusive"` with a human-readable `reason`.

    Applies Holm-Bonferroni at alpha=0.05 across the three two-sided p-values
    (NaN counts as "cannot reject" and sorts to the end of the family).

    Writes a JSON file at `out_path` with per-spec result blocks plus a
    `holm_bonferroni` block. Schema documented inline below. NaN values
    serialize to JSON `null` (RFC-compliant).
    """
    n_total = len(panel)
    base_subset = panel.dropna(subset=[response_col, threshold_col])
    Y_full = base_subset[response_col].to_numpy()
    Z_full = base_subset[threshold_col].to_numpy()

    # --- Spec A: quartile-split at 95th-pct, full panel ---
    spec_a: dict
    try:
        a_result = gpd_quantile_split_on_z(
            Y_full, Z_full,
            threshold_quantile=0.95,
            split_quantiles=(0.25, 0.5, 0.75),
            n_boot=n_boot,
            seed=seed,
        )
        spec_a = {
            "status": "fit",
            "scope": "full_panel",
            "threshold_quantile": 0.95,
            "n_panel_after_dropna": int(len(Y_full)),
            "reason": None,
            "result": _gpd_quantile_split_result_to_dict(a_result),
        }
        p_a = a_result.extreme_contrast_bootstrap_p_value
    except ValueError as exc:
        spec_a = {
            "status": "inconclusive",
            "scope": "full_panel",
            "threshold_quantile": 0.95,
            "n_panel_after_dropna": int(len(Y_full)),
            "reason": str(exc),
            "result": None,
        }
        p_a = float("nan")

    # --- Spec C: median-split at 99th-pct, full panel ---
    spec_c: dict
    try:
        c_result = gpd_conditional_on_z(
            Y_full, Z_full,
            threshold_quantile=0.99,
            z_split_quantile=0.5,
            n_boot=n_boot,
            seed=seed + 100,
        )
        c_dict = _gpd_conditional_result_to_dict_with_two_sided(c_result)
        spec_c = {
            "status": "fit",
            "scope": "full_panel",
            "threshold_quantile": 0.99,
            "n_panel_after_dropna": int(len(Y_full)),
            "reason": None,
            "result": c_dict,
        }
        p_c = c_dict["two_sided_p_value"]
    except ValueError as exc:
        spec_c = {
            "status": "inconclusive",
            "scope": "full_panel",
            "threshold_quantile": 0.99,
            "n_panel_after_dropna": int(len(Y_full)),
            "reason": str(exc),
            "result": None,
        }
        p_c = float("nan")

    # --- Spec F: median-split at within-filter 95th-pct, filtered subset ---
    if filter_col not in panel.columns:
        raise KeyError(
            f"filter_col {filter_col!r} not in panel columns; cannot run Spec F"
        )
    filter_mask = panel[filter_col].fillna(False).astype(bool)
    # Boolean numpy array aligned with base_subset's row order — avoids
    # pandas .loc-with-boolean-Series alignment subtleties.
    keep_in_filter = filter_mask.reindex(base_subset.index, fill_value=False).to_numpy()
    f_subset = base_subset[keep_in_filter]
    Y_filt = f_subset[response_col].to_numpy()
    Z_filt = f_subset[threshold_col].to_numpy()
    n_after_filter = int(len(Y_filt))

    spec_f: dict
    if n_after_filter < 20:
        spec_f = {
            "status": "inconclusive",
            "scope": "filtered_subset",
            "filter_col": filter_col,
            "threshold_quantile": 0.95,
            "n_after_filter": n_after_filter,
            "reason": f"too few rows after filter (n={n_after_filter}; need ≥20 for exceedance set)",
            "result": None,
        }
        p_f = float("nan")
    else:
        try:
            f_result = gpd_conditional_on_z(
                Y_filt, Z_filt,
                threshold_quantile=0.95,
                z_split_quantile=0.5,
                n_boot=n_boot,
                seed=seed + 200,
            )
            f_dict = _gpd_conditional_result_to_dict_with_two_sided(f_result)
            spec_f = {
                "status": "fit",
                "scope": "filtered_subset",
                "filter_col": filter_col,
                "threshold_quantile": 0.95,
                "n_after_filter": n_after_filter,
                "reason": None,
                "result": f_dict,
            }
            p_f = f_dict["two_sided_p_value"]
        except ValueError as exc:
            spec_f = {
                "status": "inconclusive",
                "scope": "filtered_subset",
                "filter_col": filter_col,
                "threshold_quantile": 0.95,
                "n_after_filter": n_after_filter,
                "reason": str(exc),
                "result": None,
            }
            p_f = float("nan")

    # --- Holm-Bonferroni across the three two-sided p-values ---
    holm = holm_bonferroni_two_sided(
        {"spec_a": p_a, "spec_c": p_c, "spec_f": p_f},
        alpha=0.05,
    )

    payload = {
        "pnode_label": pnode_label,
        "response_col": response_col,
        "threshold_col": threshold_col,
        "filter_col": filter_col,
        "n_total_panel": int(n_total),
        "spec_a_quartile_split": spec_a,
        "spec_c_99th_pct": spec_c,
        "spec_f_within_filter": spec_f,
        "holm_bonferroni": {
            "alpha": holm["alpha"],
            "sorted_order": holm["sorted_order"],
            "adjusted_thresholds": holm["adjusted_thresholds"],
            "two_sided_p_values": {"spec_a": p_a, "spec_c": p_c, "spec_f": p_f},
            "rejections": holm["rejections"],
            "family_wise_rejection": holm["family_wise_rejection"],
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_nan_to_none(payload), indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/pytest tests/analysis/test_gpd.py::test_run_conditional_z_robustness_writes_expected_json \
                 tests/analysis/test_gpd.py::test_run_conditional_z_robustness_handles_spec_c_fit_failure \
                 tests/analysis/test_gpd.py::test_run_conditional_z_robustness_handles_spec_f_filter_empty \
                 tests/analysis/test_gpd.py::test_run_conditional_z_robustness_serializes_nan_as_null \
                 -v
```

Expected: 4 PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `188 passed` (184 from Task 2 + 4 new).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/gpd.py tests/analysis/test_gpd.py
git commit -m "$(cat <<'EOF'
feat(analysis): add run_conditional_z_robustness orchestrator

Implements the 2026-05-14 pre-registered A/C/F battery in one call:
  A: quartile-split conditional-Z at 95th-pct LMP, full panel
  C: median-split conditional-Z at 99th-pct LMP, full panel
  F: median-split conditional-Z at within-filter 95th-pct, filtered subset

Catches ValueError from underlying gpd functions and marks the offending
spec as status="inconclusive" with a human-readable reason; other specs
still run. Converts gpd_conditional_on_z's one-sided p-value to two-sided
via 2*min(p, 1-p) for the Holm family-wise correction.

Writes a single JSON file at outputs/gpd/conditional_z_robustness.json
(when wired into run_all in Task 4) carrying per-spec results, two-sided
p-values, Holm rejections, and the family-wise verdict. NaN -> null via
the existing _nan_to_none helper.

4 new tests; full suite at 188.
EOF
)"
```

---

## Task 4: Wire `run_conditional_z_robustness` into `run_all`

**Why this task exists:** The orchestrator from Task 3 must run inside `surg-analyze` so the battery produces an output JSON on every production run. This is the smallest change that completes the pipeline: a single call after the per-pnode GPD loop, on the primary response (`total_lmp_rt_cluster_mean`) where the original conditional-Z rejection was found.

**Files:**
- Modify: `src/surg/analysis/run.py` (one import + one function call in `run_all`)
- Modify: `tests/analysis/test_run.py` (add `outputs/gpd/conditional_z_robustness.json` to the expected-paths set)

- [ ] **Step 1: Update the integration test's expected paths**

Open `tests/analysis/test_run.py`. Find the integration test that asserts which files `run_all` writes (the one updated in the Strategy C plan's Task 1). Locate the `expected_paths` set and add the new entry:

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
    out_root / "qr_full" / "primary.json",
    out_root / "qr_full" / "total_lmp.json",
    out_root / "qr_full" / "ox.json",
    out_root / "qr_full" / "bristers.json",
    out_root / "qr_full" / "dom_zonal.json",
    out_root / "qr_full" / "ashburn_tx1.json",
    out_root / "qr_full" / "ashburn_tx2.json",
    out_root / "gpd" / "primary.json",
    out_root / "gpd" / "total_lmp.json",
    out_root / "gpd" / "ox.json",
    out_root / "gpd" / "bristers.json",
    out_root / "gpd" / "dom_zonal.json",
    out_root / "gpd" / "ashburn_tx1.json",
    out_root / "gpd" / "ashburn_tx2.json",
    out_root / "gpd" / "conditional_z_robustness.json",   # NEW
    out_root / "mechanism" / "validation.json",
    out_root / "robustness" / "subsample_bootstrap.parquet",
}
```

If the current test's `expected_paths` doesn't list all of the above (e.g., the Strategy C `qr_full/` and `gpd/` per-pnode entries), preserve what's there and add only `out_root / "gpd" / "conditional_z_robustness.json"`. The point is to assert the new file exists; do not unilaterally restructure the rest.

- [ ] **Step 2: Run integration test to verify it fails**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: FAIL with assertion that `out_root / "gpd" / "conditional_z_robustness.json"` does not exist.

- [ ] **Step 3: Add the import and the call in `src/surg/analysis/run.py`**

Open `src/surg/analysis/run.py`. Update the existing GPD import line:

```python
from surg.analysis.gpd import run_gpd
```

to:

```python
from surg.analysis.gpd import run_gpd, run_conditional_z_robustness
```

Then, inside `run_all`, append after the existing `for label, col in PNODE_RESPONSES.items(): … run_qr_full(…); run_gpd(…)` loop and before the trailing comment about `leave_one_season_out`:

```python
    # 2026-05-14 conditional-Z robustness battery (A/C/F + Holm-Bonferroni).
    # Single battery run on the primary response (cluster total_lmp) where
    # the original median-split rejection was found. Pre-reg:
    # docs/decisions.md § "2026-05-14 — Pre-registration: conditional-Z
    # robustness battery (A/C/F + gated B)".
    run_conditional_z_robustness(
        panel=panel,
        out_path=out_root / "gpd" / "conditional_z_robustness.json",
        response_col=PNODE_RESPONSES["total_lmp"],
        pnode_label="total_lmp",
        n_boot=gpd_n_boot,
    )
```

No new CLI flag — the orchestrator reuses the existing `--gpd-n-boot` argument routed through `gpd_n_boot=gpd_n_boot`.

- [ ] **Step 4: Run integration test to verify it passes**

```bash
.venv/bin/pytest tests/analysis/test_run.py -v
```

Expected: PASS.

- [ ] **Step 5: Run full test suite to verify no regressions**

```bash
.venv/bin/pytest tests/ --tb=no -q
```

Expected: `188 passed` (no new tests in this task; integration test updated in place).

- [ ] **Step 6: Commit**

```bash
git add src/surg/analysis/run.py tests/analysis/test_run.py
git commit -m "$(cat <<'EOF'
feat(analysis): wire run_conditional_z_robustness into run_all

Runs the 2026-05-14 pre-registered conditional-Z battery once per surg-analyze
invocation, on the primary response (total_lmp_rt_cluster_mean) where the
original median-split rejection was found. Output lands at
outputs/gpd/conditional_z_robustness.json alongside the per-pnode GPD JSONs.

Reuses the existing --gpd-n-boot CLI flag; no new arguments.
EOF
)"
```

---

## Task 5: Verification on real panel

**Why this task exists:** Final check that the new battery runs end-to-end on the actual 31,632-row panel and produces an interpretable JSON. No code changes; just exercise the pipeline at production resolution, confirm the output schema is sensible, and snapshot the result for the application-of-pre-reg decisions.md entry that follows in a separate session.

**Files:**
- Read-only: `data/interim/analysis_panel.parquet`, `outputs/gpd/conditional_z_robustness.json` (after run)

- [ ] **Step 1: Confirm the analysis panel is current**

```bash
ls -la data/interim/analysis_panel.parquet
```

Expected: file exists and is the panel artifact from the most recent `surg-prep` build. If missing, run `.venv/bin/surg-prep` first.

- [ ] **Step 2: Run the full analysis at production bootstrap resolution**

```bash
.venv/bin/surg-analyze
```

Expected: completes in ~40 min (matches the prior Strategy C production run). The new battery adds ~2-4 min on top (three more GPD calls at n_boot=200). Final stdout: `wrote analysis outputs to outputs/`.

- [ ] **Step 3: Confirm the new output file exists and is well-formed**

```bash
ls -la outputs/gpd/conditional_z_robustness.json
.venv/bin/python -c "import json; p=json.load(open('outputs/gpd/conditional_z_robustness.json')); print(list(p.keys()))"
```

Expected output (last command):
```
['pnode_label', 'response_col', 'threshold_col', 'filter_col', 'n_total_panel', 'spec_a_quartile_split', 'spec_c_99th_pct', 'spec_f_within_filter', 'holm_bonferroni']
```

- [ ] **Step 4: Snapshot the headline numbers for the application-of-pre-reg entry**

```bash
.venv/bin/python <<'EOF'
import json
p = json.load(open("outputs/gpd/conditional_z_robustness.json"))

print("=== Spec A (quartile-split at 95th-pct, full panel) ===")
a = p["spec_a_quartile_split"]
print(f"  status: {a['status']}")
if a["status"] == "fit":
    r = a["result"]
    print(f"  ξ trajectory across quartiles: {[round(f['shape'], 3) for f in r['quantile_fits']]}")
    print(f"  Q4 − Q1 contrast: {r['extreme_contrast']:.3f}")
    print(f"  bootstrap CI 95%: {r['extreme_contrast_bootstrap_ci_95']}")
    print(f"  two-sided p:     {r['extreme_contrast_bootstrap_p_value']}")

print("\n=== Spec C (median-split at 99th-pct, full panel) ===")
c = p["spec_c_99th_pct"]
print(f"  status: {c['status']}")
if c["status"] == "fit":
    r = c["result"]
    print(f"  ξ_low: {r['low_z']['shape']:.3f}  (n={r['low_z']['n_exceedances']})")
    print(f"  ξ_high: {r['high_z']['shape']:.3f}  (n={r['high_z']['n_exceedances']})")
    print(f"  shape_diff (high−low): {r['shape_diff']:.3f}")
    print(f"  bootstrap CI 95%: {r['shape_diff_bootstrap_ci_95']}")
    print(f"  two-sided p:     {r['two_sided_p_value']}")
else:
    print(f"  reason: {c['reason']}")

print("\n=== Spec F (median-split at within-filter 95th-pct, filtered subset) ===")
f = p["spec_f_within_filter"]
print(f"  status: {f['status']}")
print(f"  n_after_filter: {f['n_after_filter']}")
if f["status"] == "fit":
    r = f["result"]
    print(f"  ξ_low: {r['low_z']['shape']:.3f}  (n={r['low_z']['n_exceedances']})")
    print(f"  ξ_high: {r['high_z']['shape']:.3f}  (n={r['high_z']['n_exceedances']})")
    print(f"  shape_diff (high−low): {r['shape_diff']:.3f}")
    print(f"  bootstrap CI 95%: {r['shape_diff_bootstrap_ci_95']}")
    print(f"  two-sided p:     {r['two_sided_p_value']}")
else:
    print(f"  reason: {f['reason']}")

print("\n=== Holm–Bonferroni roll-up ===")
h = p["holm_bonferroni"]
print(f"  two-sided p-values: {h['two_sided_p_values']}")
print(f"  sorted order:      {h['sorted_order']}")
print(f"  adjusted thresholds: {h['adjusted_thresholds']}")
print(f"  rejections:        {h['rejections']}")
print(f"  family-wise rejection: {h['family_wise_rejection']}")
EOF
```

Expected: human-readable summary of all three specs + the Holm verdict. Save the output (copy to clipboard or terminal scrollback) — it is the input to the application-of-pre-reg decisions.md entry written in a follow-up session.

- [ ] **Step 5: No commit in this task**

Task 5 is verification only. No source files changed. The next step (writing the application-of-pre-reg decisions.md entry) happens in a follow-up session after interpreting the numbers.

---

## Out of scope (for follow-up plans)

- **Spec B (continuous ξ(Z) regression).** Per the pre-reg, B is gated on Spec A returning a non-monotone trajectory or inconclusive primary CI. A separate plan will land if and when B is triggered.
- **Application-of-pre-reg decisions.md entry.** Written in a follow-up session after Task 5 produces the headline numbers. Format follows the 2026-05-13 application entry — mechanical rule application against the pre-reg's decision tables.
- **Cross-pnode robustness sweep.** The battery runs on `total_lmp` only because that is where the original rejection was found. If the advisor meeting requests cross-pnode replication, a follow-up plan adds a loop over `PNODE_RESPONSES`.
- **JLARC projection layer.** Separate work track, separate plan, scheduled after this battery resolves the conditional-Z question.
