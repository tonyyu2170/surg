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
    assert "ks_distance" in result
    assert 0 <= result["ks_distance"] <= 1  # D is a distance bounded to [0, 1]
    assert "n_tail" in result
    assert 0 < result["n_tail"] <= 2000


def test_power_law_handles_empty_input():
    from surg.analysis.mechanism import fit_power_law
    result = fit_power_law(np.array([]))
    assert result["alpha"] is None
    assert result["n"] == 0


def test_run_mechanism_writes_json(tmp_path):
    from surg.analysis.mechanism import run_mechanism
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    n = 500
    df = pd.DataFrame({col: [None]*n for col in EXPECTED_COLUMNS})
    rng = np.random.default_rng(0)
    df["dom_load_gradient_abs_mw_per_min"] = rng.lognormal(0, 0.7, n)
    df["sync_reserve_event_active"] = rng.random(n) > 0.9
    # Mix of values both above AND below the $850 ORDC step (required so
    # by_regime["high_sr_clearing"] is not degenerate).
    df["sync_reserve_clearing_price_rt"] = rng.uniform(0, 1500, n)
    df["passes_proposal_filter"] = True
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=n, freq="h")

    events_df = pd.DataFrame({
        "event_start_ept": pd.to_datetime(["2024-01-15T03:00:00"] * 15),
        "event_end_ept":   pd.to_datetime(["2024-01-15T04:00:00"] * 15),
        "duration": ["1 hour"] * 15,
    })

    out_path = tmp_path / "mechanism_validation.json"
    run_mechanism(
        panel=df, events=events_df,
        threshold=1.0,
        out_path=out_path,
    )
    assert out_path.exists()
    import json
    payload = json.loads(out_path.read_text())
    assert "granger" in payload
    assert "by_regime" in payload
    assert "power_law" in payload
    assert payload["threshold_used"] == 1.0


def test_run_mechanism_produces_both_regime_blocks(tmp_path):
    """Amendment 2026-05-12: by_regime must contain both sync_event_active
    and high_sr_clearing, each with conditional_regime + crosstab sub-blocks."""
    from surg.analysis.mechanism import run_mechanism
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    n = 500
    df = pd.DataFrame({col: [None]*n for col in EXPECTED_COLUMNS})
    rng = np.random.default_rng(1)
    df["dom_load_gradient_abs_mw_per_min"] = rng.lognormal(0, 0.7, n)
    df["sync_reserve_event_active"] = rng.random(n) > 0.85
    df["sync_reserve_clearing_price_rt"] = rng.uniform(0, 1500, n)
    df["passes_proposal_filter"] = True
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=n, freq="h")
    events_df = pd.DataFrame({
        "event_start_ept": pd.to_datetime(["2024-01-15T03:00:00"] * 10),
        "event_end_ept":   pd.to_datetime(["2024-01-15T04:00:00"] * 10),
        "duration": ["1 hour"] * 10,
    })

    out_path = tmp_path / "mechanism_validation.json"
    run_mechanism(panel=df, events=events_df, threshold=1.0, out_path=out_path)

    import json
    payload = json.loads(out_path.read_text())
    assert set(payload["by_regime"].keys()) == {"sync_event_active", "high_sr_clearing"}
    for regime_key in ["sync_event_active", "high_sr_clearing"]:
        block = payload["by_regime"][regime_key]
        assert "conditional_regime" in block
        assert "crosstab" in block
        # Crosstab table uses semantically named string keys (not bool→"true"/"false")
        assert set(block["crosstab"]["table"].keys()) == {"above", "below"}
        for outer in ["above", "below"]:
            assert set(block["crosstab"]["table"][outer].keys()) == {"active", "inactive"}


def test_power_law_handles_degenerate_fit():
    """When powerlaw can't fit (e.g., all identical durations), the result
    fields should be None — not NaN — so the JSON output is RFC-compliant."""
    from surg.analysis.mechanism import fit_power_law
    # 20 identical durations: powerlaw will fit but alpha/xmin can land on NaN
    durations = np.ones(20)
    result = fit_power_law(durations)
    import json
    # If any value is NaN, json.dumps will emit "NaN" (invalid JSON).
    # Round-trip through a strict-mode dumps and loads.
    serialized = json.dumps(result, allow_nan=False)
    reloaded = json.loads(serialized)
    assert reloaded["n"] == 20
    # alpha may be None or a finite float — never NaN
    assert reloaded["alpha"] is None or isinstance(reloaded["alpha"], (int, float))
