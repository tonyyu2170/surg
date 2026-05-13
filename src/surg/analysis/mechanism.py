"""Mechanism validation — Granger causality, conditional regime test,
cross-tabulation, power-law fit on event durations.

See design spec §6 for the three tests + tertiary robustness check.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
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


def fit_power_law(durations: np.ndarray) -> dict:
    """Fit a power-law distribution to event durations.

    Uses the `powerlaw` package (Clauset/Shalizi/Newman 2009 method):
    estimate x_min via KS minimization, then fit α via MLE on tail.
    Returns alpha, x_min, KS distance (goodness-of-fit), n, and n_tail.
    """
    durations = np.asarray(durations, dtype=float)
    n = int(len(durations))
    if n < 10:
        return {"alpha": None, "x_min": None, "ks_distance": None, "n": n, "n_tail": 0}

    import powerlaw
    fit = powerlaw.Fit(durations, verbose=False)
    return {
        "alpha": float(fit.alpha),
        "x_min": float(fit.xmin),
        "ks_distance": float(fit.D),  # KS distance D (lower = better fit; not a p-value)
        "n": n,
        "n_tail": int(fit.n_tail),  # observations above x_min, used in the MLE
    }
