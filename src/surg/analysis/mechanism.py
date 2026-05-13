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
