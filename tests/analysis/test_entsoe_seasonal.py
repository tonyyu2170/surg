import numpy as np
import pandas as pd
import pytest

from surg.analysis.entsoe_seasonal import (
    SUMMER,
    WINTER,
    complete_days,
    implausible_days,
    midday_deviation_mw,
    midday_statistics,
    seasonal_profile,
    signature_by_year,
    solar_signature,
)

FLAT = [1000.0] * 24
# A midday dip of the kind PV carves: hours 10-15 sit ~30% below the rest.
MIDDAY_DIP = [1000.0] * 10 + [700.0] * 6 + [1000.0] * 8


def _panel(days: dict[str, list[float]]) -> pd.DataFrame:
    """Hourly panel from {'2024-06-01': [24 values]}, mirroring to_hourly."""
    rows = []
    for date, shape in days.items():
        assert len(shape) == 24
        start = pd.Timestamp(date)
        for hour, value in enumerate(shape):
            local = start + pd.Timedelta(hours=hour)
            rows.append(
                {
                    "timestamp_utc": local.tz_localize("UTC"),
                    "timestamp_local": local,
                    "load_mw": value,
                }
            )
    return pd.DataFrame(rows)


def _season_days(year: int, months: tuple[int, ...], shape: list[float], n: int = 40) -> dict:
    """`n` days inside each of `months`, all carrying the same shape."""
    out = {}
    for month in months:
        for day in range(1, n + 1):
            try:
                stamp = pd.Timestamp(year=year, month=month, day=day)
            except ValueError:
                continue
            out[str(stamp.date())] = shape
    return out


def test_flat_days_produce_a_flat_profile():
    panel = _panel(_season_days(2024, (6,), FLAT))
    profile = seasonal_profile(panel, year=2024, months=SUMMER)

    assert len(profile) == 24
    assert np.allclose(profile.values, 1.0)


def test_midday_dip_registers_as_positive_depth():
    panel = _panel(_season_days(2024, (6,), MIDDAY_DIP))
    stats = midday_statistics(panel, year=2024, months=SUMMER)

    # Day mean is (18*1000 + 6*700)/24 = 925; midday sits at 700/925.
    assert stats["midday_ratio"] == pytest.approx(700 / 925)
    assert stats["midday_depth"] > 0
    assert stats["trough_hour"] in range(10, 16)


def test_each_day_is_normalized_by_its_own_mean():
    """A high-demand day must not dominate the profile of a low-demand one."""
    small = MIDDAY_DIP
    large = [v * 5 for v in MIDDAY_DIP]
    panel = _panel({"2024-06-01": small, "2024-06-02": large})

    profile = seasonal_profile(panel, year=2024, months=SUMMER)

    # Identical shapes at different levels average to that same shape.
    assert profile.loc[0] == pytest.approx(1000 / 925)
    assert profile.loc[12] == pytest.approx(700 / 925)


def test_incomplete_days_are_dropped_entirely():
    panel = _panel({"2024-06-01": FLAT})
    stub = panel.iloc[:4].assign(
        timestamp_local=lambda d: d["timestamp_local"] + pd.Timedelta(days=1)
    )

    kept = complete_days(pd.concat([panel, stub], ignore_index=True))

    # The 4-hour day contributes nothing; only the complete day survives.
    assert kept["date"].nunique() == 1
    assert len(kept) == 24


def test_january_belongs_to_its_own_calendar_year():
    """Winter spans a year boundary; Jan 2025 must not be counted into 2024."""
    panel = _panel({**_season_days(2024, (11, 12), FLAT), **_season_days(2025, (1, 2), FLAT)})

    winter_2024 = midday_statistics(panel, year=2024, months=WINTER)
    winter_2025 = midday_statistics(panel, year=2025, months=WINTER)

    assert winter_2024["n_days"] > 0
    assert winter_2025["n_days"] > 0
    # No day is counted twice.
    assert winter_2024["n_days"] + winter_2025["n_days"] == len(panel) // 24


def test_summer_dip_with_flat_winter_gives_a_positive_signature():
    """The H_solar prediction: the trough is seasonal."""
    panel = _panel(
        {
            **_season_days(2024, SUMMER, MIDDAY_DIP),
            **_season_days(2024, (11, 12), FLAT),
            **_season_days(2024, (1, 2), FLAT),
        }
    )
    row = solar_signature(panel, year=2024)

    assert row["summer_midday_depth"] > 0
    assert row["winter_midday_depth"] == pytest.approx(0.0)
    assert row["signature"] > 0


def test_a_year_round_dip_gives_a_zero_signature():
    """A non-seasonal flattening -- what data centres would produce -- cancels."""
    panel = _panel(
        {
            **_season_days(2024, SUMMER, MIDDAY_DIP),
            **_season_days(2024, (11, 12), MIDDAY_DIP),
            **_season_days(2024, (1, 2), MIDDAY_DIP),
        }
    )
    row = solar_signature(panel, year=2024)

    assert row["summer_midday_depth"] > 0
    assert row["signature"] == pytest.approx(0.0)


def test_thin_season_years_are_dropped_not_reported():
    """A stub season must not produce a confident-looking number."""
    full = {
        **_season_days(2024, SUMMER, MIDDAY_DIP),
        **_season_days(2024, (11, 12), FLAT),
        **_season_days(2024, (1, 2), FLAT),
    }
    # 2025 gets a full summer but only three winter days.
    thin = {
        **_season_days(2025, SUMMER, MIDDAY_DIP),
        **_season_days(2025, (1,), FLAT, n=3),
    }
    panel = _panel({**full, **thin})

    out = signature_by_year(panel, years=[2024, 2025], min_days=30)

    assert list(out.index) == [2024]


def test_flat_load_added_does_not_move_the_absolute_midday_deviation():
    """The property the whole H_solar test rests on.

    Data centres, or an industrial recovery, add roughly flat load. That must
    leave the absolute midday deviation untouched -- otherwise this statistic
    is as vulnerable to its denominator as vol_norm was.
    """
    base = _panel(_season_days(2024, (6,), MIDDAY_DIP))
    # +5,000 MW of perfectly flat load, five times the original mean.
    inflated = base.assign(load_mw=base["load_mw"] + 5000.0)

    before = midday_deviation_mw(base, year=2024, months=SUMMER)
    after = midday_deviation_mw(inflated, year=2024, months=SUMMER)

    assert before == pytest.approx(after)
    # ...while the ratio-based statistic IS diluted by exactly that load.
    ratio_before = midday_statistics(base, year=2024, months=SUMMER)["midday_depth"]
    ratio_after = midday_statistics(inflated, year=2024, months=SUMMER)["midday_depth"]
    assert abs(ratio_after) < abs(ratio_before)


def test_midday_specific_load_does_move_the_absolute_deviation():
    base = _panel(_season_days(2024, (6,), FLAT))
    grossed_up = [1000.0] * 10 + [2000.0] * 6 + [1000.0] * 8
    changed = _panel(_season_days(2024, (6,), grossed_up))

    assert midday_deviation_mw(base, year=2024, months=SUMMER) == pytest.approx(0.0)
    assert midday_deviation_mw(changed, year=2024, months=SUMMER) > 0


def test_implausible_days_are_reported_not_silently_kept():
    """A day of 24 corrupt values passes the completeness gate (NL 2026)."""
    days = _season_days(2024, (6,), FLAT)
    days["2024-06-15"] = [10.0] * 24

    bad = implausible_days(_panel(days))

    assert list(bad["date"].astype(str)) == ["2024-06-15"]
    assert bad["day_mean_mw"].iloc[0] == pytest.approx(10.0)


def test_a_few_corrupt_slots_inside_an_ordinary_day_are_caught():
    """The shape the Dutch 2026 tail actually takes.

    A mean-only guard is blind to this: the day's mean stays well within range
    while a handful of slots collapse. Measured on the real NL panel, eight days
    carry minima of 187-1,822 MW against a 10,320 MW median day minimum, and
    their means clear any sane mean-based floor.
    """
    days = _season_days(2024, (6,), FLAT)
    # 21 ordinary hours plus 3 corrupt ones: mean 876 MW against a 1,000 MW
    # median day, so the mean test cannot fire -- but the minimum is 10 MW.
    days["2024-06-15"] = [1000.0] * 21 + [10.0] * 3

    bad = implausible_days(_panel(days))

    assert list(bad["date"].astype(str)) == ["2024-06-15"]
    assert bad["reason"].iloc[0] == "min"
    assert bad["day_mean_mw"].iloc[0] > 800  # the mean test would have missed it


def test_empty_panel_returns_empty_rather_than_raising():
    empty = pd.DataFrame(columns=["timestamp_utc", "timestamp_local", "load_mw"])

    assert seasonal_profile(empty, year=2024, months=SUMMER).empty
    assert midday_statistics(empty, year=2024, months=SUMMER)["n_days"] == 0
    assert signature_by_year(empty, years=[2024]).empty
