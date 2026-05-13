"""Mechanism validation — Granger causality, conditional regime test,
cross-tabulation, power-law fit on event durations.

See design spec §6 for the three tests + tertiary robustness check.
"""
from __future__ import annotations

import json
from pathlib import Path

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


# Reserve-shortage pricing step (ORDC first-step penalty level). See
# docs/decisions.md "Stressed-regime definition refined to high SR clearing price".
HIGH_SR_CLEARING_THRESHOLD = 850.0


def _crosstab_table_to_semantic(table: dict) -> dict:
    """Re-key crosstab_chi2's bool-keyed table to string keys that survive
    json.dumps roundtrip. Maps (Z-above-threshold, event-active) → ("above"/"below", "active"/"inactive")."""
    return {
        "above": {
            "active":   int(table.get(True, {}).get(True, 0)),
            "inactive": int(table.get(False, {}).get(True, 0)),
        },
        "below": {
            "active":   int(table.get(True, {}).get(False, 0)),
            "inactive": int(table.get(False, {}).get(False, 0)),
        },
    }


def run_mechanism(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    *,
    threshold: float,
    out_path: Path,
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
) -> None:
    """End-to-end mechanism validation, writing JSON output.

    Threads BOTH stressed-regime indicators per the 2026-05-12 amendment:
    - sync_event_active: panel["sync_reserve_event_active"] (binary)
    - high_sr_clearing:  panel["sync_reserve_clearing_price_rt"] >= 850

    See docs/decisions.md 2026-05-12 § "Stressed-regime definition
    refined to high SR clearing price" for the rationale.
    """
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[threshold_col])

    Z = subset[threshold_col].to_numpy()
    sync_active = subset["sync_reserve_event_active"].fillna(False).astype(bool).to_numpy()
    # Continuous-derived second indicator. NaN treated as False (no event).
    high_sr = (subset["sync_reserve_clearing_price_rt"].fillna(0.0) >= HIGH_SR_CLEARING_THRESHOLD).to_numpy()

    # Granger uses the binary sync_event_active as the effect series (cause = Z).
    granger = granger_test(cause=Z, effect=sync_active.astype(float), max_lag=3)

    # Per-regime conditional + crosstab
    by_regime = {}
    for regime_key, regime_indicator in [
        ("sync_event_active", sync_active),
        ("high_sr_clearing", high_sr),
    ]:
        crt = conditional_regime_test(Z=Z, threshold=threshold, event_active=regime_indicator)
        xtab = crosstab_chi2(Z=Z, threshold=threshold, event_active=regime_indicator)
        # Convert bool-keyed table to string-keyed before JSON serialization
        xtab_serializable = {
            "table": _crosstab_table_to_semantic(xtab["table"]),
            "chi2_stat": xtab["chi2_stat"],
            "chi2_p_value": xtab["chi2_p_value"],
        }
        by_regime[regime_key] = {
            "conditional_regime": crt,
            "crosstab": xtab_serializable,
        }

    # Power-law on event durations
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
        "by_regime": by_regime,
        "power_law": plaw,
        "threshold_used": threshold,
        "high_sr_clearing_cutoff": HIGH_SR_CLEARING_THRESHOLD,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
