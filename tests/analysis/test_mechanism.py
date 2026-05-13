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
    p_values = [results[k][1] for k in results]
    assert np.median(p_values) > 0.1
