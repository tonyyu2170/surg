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


def test_conditional_regime_test_quantifies_concordance():
    from surg.analysis.mechanism import conditional_regime_test

    # 100 hours. Z>c is true 30/100 times. Event active 25/100 times.
    # Of the 25 event-active hours, 20 also have Z>c (strong concordance).
    n = 100
    Z = np.array([2.0] * 70 + [3.5] * 30)
    active = np.array([False] * 75 + [True] * 25)
    # Reorder so that 20 of the 25 active are in the high-Z region
    rng = np.random.default_rng(0)
    Z = np.r_[np.full(20, 3.5), np.full(5, 3.5), np.full(5, 3.5),
              np.full(5, 2.0), np.full(65, 2.0)]
    active = np.r_[np.full(20, True), np.full(5, False), np.full(5, False),
                   np.full(5, True), np.full(65, False)]

    result = conditional_regime_test(Z=Z, threshold=3.0, event_active=active)
    assert result["frac_above_threshold_when_active"] == 20/25
    assert result["frac_above_threshold_when_inactive"] == 10/75
    assert result["effect_size"] > 0


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
