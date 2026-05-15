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
from scipy import stats


def compute_z_deciles(panel: pd.DataFrame, z_col: str) -> tuple[np.ndarray, np.ndarray]:
    """Compute 10 equal-count quantile bins of Z.

    Returns
    -------
    edges : np.ndarray of shape (11,)
        Bin edges including endpoints. ``edges[0]`` = Z min, ``edges[10]`` = Z max.
    bin_indices : np.ndarray of shape (n,)
        Integer bin assignment in [0, 9] per row of ``panel``.

    Notes
    -----
    When ``z`` has tied values at quantile boundaries (e.g., many zeros
    from flat-load periods), multiple interior bins may collapse and have
    zero observations. Downstream callers must handle ``decile_n_obs[i] == 0``
    defensively.
    """
    z = panel[z_col].to_numpy()
    edges = np.quantile(z, np.linspace(0.0, 1.0, 11))
    # digitize returns 1..N+1; clip into 0..9 so a value equal to edges[-1] lands in bin 9
    bin_indices = np.clip(np.digitize(z, edges[1:-1], right=True), 0, 9)
    return edges, bin_indices


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
