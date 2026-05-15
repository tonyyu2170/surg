"""Tests for src/surg/analysis/bootstrap_strategies.py — sub-q1 item #8."""
import numpy as np
import pandas as pd
import pytest

from surg.analysis.bootstrap_strategies import (
    identify_islands,
    island_cluster_bootstrap,
    bootstrap_dispatch,
)


def test_identify_islands_consecutive_5min_obs_form_one_island():
    ts = pd.DatetimeIndex(pd.date_range("2026-04-15 02:00", periods=36, freq="5min"))
    mask = pd.Series([True] * 36, index=range(36))
    island_ids = identify_islands(ts, mask, gap_threshold_minutes=10)
    assert island_ids.nunique() == 1


def test_identify_islands_gap_creates_new_island():
    ts1 = pd.date_range("2026-04-15 02:00", periods=36, freq="5min")
    ts2 = pd.date_range("2026-04-16 02:00", periods=36, freq="5min")
    ts = pd.DatetimeIndex(list(ts1) + list(ts2))
    mask = pd.Series([True] * 72, index=range(72))
    island_ids = identify_islands(ts, mask, gap_threshold_minutes=10)
    assert island_ids.nunique() == 2
    assert (island_ids.iloc[:36] == island_ids.iloc[0]).all()
    assert (island_ids.iloc[36:] == island_ids.iloc[36]).all()
    assert island_ids.iloc[0] != island_ids.iloc[36]


def test_identify_islands_three_consecutive_proposal_islands():
    """Realistic case: 3 days of 2-5 AM windows separated by 21h gaps."""
    parts = []
    for day in range(3):
        parts.append(pd.date_range(
            f"2026-04-{15+day:02d} 02:00", periods=36, freq="5min"
        ))
    ts = pd.DatetimeIndex(np.concatenate(parts))
    mask = pd.Series([True] * len(ts), index=range(len(ts)))
    island_ids = identify_islands(ts, mask, gap_threshold_minutes=10)
    assert island_ids.nunique() == 3


def test_island_cluster_bootstrap_single_island_returns_same_size():
    ts = pd.date_range("2026-04-15 02:00", periods=36, freq="5min")
    df = pd.DataFrame({
        "datetime_beginning_ept": ts,
        "value": np.arange(36).astype(float),
    })
    island_ids = pd.Series([0] * 36)
    rng = np.random.default_rng(42)
    boot_df = island_cluster_bootstrap(df, island_ids, rng)
    assert len(boot_df) == 36


def test_island_cluster_bootstrap_resamples_islands_with_replacement():
    df = pd.DataFrame({
        "datetime_beginning_ept": pd.date_range("2026-04-15", periods=72, freq="5min"),
        "value": np.arange(72).astype(float),
    })
    island_ids = pd.Series([0] * 36 + [1] * 36)
    rng = np.random.default_rng(42)
    # Each rep resamples K=2 islands with replacement → output size = sum
    # of resampled island sizes (each island has 36 rows here so always 72)
    boot_df = island_cluster_bootstrap(df, island_ids, rng)
    assert len(boot_df) == 72


def test_island_cluster_bootstrap_can_repeat_island():
    """Across many bootstrap reps, both islands are sometimes repeated."""
    df = pd.DataFrame({
        "value": np.arange(20).astype(float),
    })
    island_ids = pd.Series([0] * 10 + [1] * 10)
    rng = np.random.default_rng(0)
    saw_all_zero_island = False
    for _ in range(50):
        boot_df = island_cluster_bootstrap(df, island_ids, rng)
        # If both sampled islands == 0, all values come from rows 0..9
        if (boot_df["value"] < 10).all():
            saw_all_zero_island = True
            break
    assert saw_all_zero_island, "K=2 with replacement should sometimes draw (0,0)"


def test_bootstrap_dispatch_pair_returns_n_boot_x_n_stats():
    df = pd.DataFrame({"x": np.arange(100).astype(float)})

    def stat_fn(d):
        return np.array([d["x"].mean(), d["x"].std()])

    rng = np.random.default_rng(42)
    reps = bootstrap_dispatch("pair", df, stat_fn, n_boot=20, rng=rng)
    assert reps.shape == (20, 2)
    # Bootstrap distribution should hover near the true mean (49.5)
    assert abs(reps[:, 0].mean() - 49.5) < 5.0


def test_bootstrap_dispatch_cluster_requires_island_ids():
    df = pd.DataFrame({"x": np.arange(10).astype(float)})

    def stat_fn(d):
        return np.array([d["x"].mean()])

    rng = np.random.default_rng(42)
    with pytest.raises(ValueError, match="island_ids"):
        bootstrap_dispatch("cluster", df, stat_fn, n_boot=5, rng=rng)


def test_bootstrap_dispatch_cluster_uses_island_resampling():
    df = pd.DataFrame({"x": np.arange(20).astype(float)})
    island_ids = pd.Series([0] * 10 + [1] * 10)

    def stat_fn(d):
        return np.array([d["x"].mean()])

    rng = np.random.default_rng(42)
    reps = bootstrap_dispatch(
        "cluster", df, stat_fn, n_boot=30, rng=rng, island_ids=island_ids,
    )
    assert reps.shape == (30, 1)
    # When both islands == 0 are drawn → mean = 4.5; both 1 → 14.5; mixed → 9.5
    means = reps[:, 0]
    assert set(np.round(means, 1)) <= {4.5, 9.5, 14.5}


def test_bootstrap_dispatch_unknown_method_raises():
    df = pd.DataFrame({"x": [1.0]})
    with pytest.raises(ValueError, match="Unknown bootstrap method"):
        bootstrap_dispatch("unknown", df, lambda d: np.array([1.0]),
                           n_boot=1, rng=np.random.default_rng(0))


def test_bootstrap_dispatch_validates_stat_fn_consistent_length():
    df = pd.DataFrame({"x": np.arange(10).astype(float)})
    call_count = {"n": 0}

    def stat_fn(d):
        call_count["n"] += 1
        # First call → length 2; subsequent → length 1 (regression trigger)
        if call_count["n"] == 1:
            return np.array([d["x"].mean(), d["x"].std()])
        return np.array([d["x"].mean()])

    rng = np.random.default_rng(0)
    with pytest.raises(ValueError, match="length"):
        bootstrap_dispatch("pair", df, stat_fn, n_boot=3, rng=rng)
