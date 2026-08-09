"""Tests for the market-agnostic Stage-1 diagnostic core."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from surg.diagnostics.stage1 import (
    add_zone_gradients,
    assert_panel_quality,
    level_vs_volatility,
    trend_tables,
)


def make_panel(hours: int = 24 * 400, seed: int = 7) -> pd.DataFrame:
    """Synthetic two-zone hourly panel with a known level/price link."""
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2023-01-01", periods=hours, freq="h")
    load_a = 1000 + 100 * np.sin(np.arange(hours) * 2 * np.pi / 24) + rng.normal(0, 5, hours)
    load_b = 500 + rng.normal(0, 5, hours)
    panel = pd.DataFrame(
        {
            "datetime_beginning_local": ts,
            "load_mw_alpha": load_a,
            "load_mw_beta": load_b,
            "dst_transition_hour": False,
        }
    )
    panel = add_zone_gradients(panel, ["alpha", "beta"], time_col="datetime_beginning_local")
    # price tracks alpha's LEVEL by construction
    panel["px_hub"] = 20 + 0.05 * panel["load_mw_alpha"] + rng.normal(0, 1, hours)
    return panel


def test_add_zone_gradients_matches_manual_diff():
    panel = make_panel(hours=48)
    manual = panel["load_mw_alpha"].diff().abs() / 60.0
    got = panel["load_gradient_abs_mw_per_min_alpha"]
    pd.testing.assert_series_equal(got, manual, check_names=False)


def test_add_zone_gradients_rejects_unsorted():
    panel = make_panel(hours=48).iloc[::-1].reset_index(drop=True)
    with pytest.raises(ValueError, match="sorted"):
        add_zone_gradients(panel, ["alpha"], time_col="datetime_beginning_local")


def test_assert_panel_quality_passes_clean_panel():
    assert_panel_quality(
        make_panel(), ["alpha", "beta"],
        time_col="datetime_beginning_local", dst_pairs_per_year=0,
    )


def test_assert_panel_quality_catches_duplicate_timestamp():
    panel = make_panel()
    panel.loc[10, "datetime_beginning_local"] = panel.loc[9, "datetime_beginning_local"]
    with pytest.raises(AssertionError, match="duplicate"):
        assert_panel_quality(
            panel.sort_values("datetime_beginning_local").reset_index(drop=True),
            ["alpha", "beta"],
            time_col="datetime_beginning_local", dst_pairs_per_year=0,
        )


def test_assert_panel_quality_catches_nan():
    panel = make_panel()
    panel.loc[5, "load_mw_beta"] = np.nan
    with pytest.raises(AssertionError, match="NaN"):
        assert_panel_quality(
            panel, ["alpha", "beta"],
            time_col="datetime_beginning_local", dst_pairs_per_year=0,
        )


def test_trend_tables_shape_and_normalization(tmp_path):
    panel = make_panel()
    trends = trend_tables(
        panel, ["alpha", "beta"],
        time_col="datetime_beginning_local", figdir=tmp_path, market="TEST",
    )
    assert set(trends["zone"]) == {"alpha", "beta"}
    row = trends[trends["zone"] == "alpha"].iloc[0]
    assert row["grad_mean_norm"] == pytest.approx(row["grad_mean"] / row["mean_load_mw"])
    assert (tmp_path / "trends_by_zone_year.csv").exists()
    assert (tmp_path / "fig1_volatility_trend_normalized.png").exists()
    assert (tmp_path / "fig2_level_trend.png").exists()


def test_level_vs_volatility_finds_planted_level_effect(tmp_path):
    panel = make_panel()
    race = level_vs_volatility(
        panel, ["alpha"], ["px_hub"],
        time_col="datetime_beginning_local",
        window_start=pd.Timestamp("2023-01-01"),
        window_end=pd.Timestamp("2026-01-01"),
        figdir=tmp_path, market="TEST", label="max",
    )
    assert len(race) == 1
    row = race.iloc[0]
    assert row["level_wins"]
    assert row["beta_level"] > 0.5  # planted link is strong
    assert (tmp_path / "fig3_level_vs_volatility_max.csv").exists()


def test_level_vs_volatility_window_filters_rows(tmp_path):
    panel = make_panel()
    race = level_vs_volatility(
        panel, ["alpha"], ["px_hub"],
        time_col="datetime_beginning_local",
        window_start=pd.Timestamp("2023-02-01"),
        window_end=pd.Timestamp("2023-03-01"),
        figdir=tmp_path, market="TEST", label="overlap",
        min_rows=1,
    )
    assert race.iloc[0]["n"] == 28 * 24
