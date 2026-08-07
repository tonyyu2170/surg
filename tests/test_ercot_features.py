from datetime import datetime

import pandas as pd
import pytest

from surg.preprocessing.ercot_features import (
    ZONES,
    add_zone_gradient_columns,
    hour_ending_to_beginning,
)


def test_hour_ending_shifts_back_one_hour():
    df = pd.DataFrame({"Hour Ending": ["01/01/2024 01:00", "01/01/2024 02:00"]})
    out = hour_ending_to_beginning(df)
    assert list(out["datetime_beginning_cpt"]) == [
        pd.Timestamp("2024-01-01 00:00"),
        pd.Timestamp("2024-01-01 01:00"),
    ]


def test_original_column_is_dropped():
    df = pd.DataFrame({"Hour Ending": ["01/01/2024 01:00"]})
    out = hour_ending_to_beginning(df)
    assert "Hour Ending" not in out.columns


def test_hour_ending_24_becomes_23_same_day():
    # ERCOT closes every day with `24:00`, which `%H` (00-23) cannot parse.
    df = pd.DataFrame({"Hour Ending": ["12/31/2024 24:00"]})
    out = hour_ending_to_beginning(df)
    assert out["datetime_beginning_cpt"].iloc[0] == pd.Timestamp("2024-12-31 23:00")


def test_year_seam_has_no_gap_or_overlap():
    # Each annual file runs 01:00 -> 24:00, so the seam is HE24 then HE01.
    # An off-by-one here silently misaligns a whole year against DOM.
    df = pd.DataFrame({"Hour Ending": ["12/31/2024 24:00", "01/01/2025 01:00"]})
    out = hour_ending_to_beginning(df)
    assert list(out["datetime_beginning_cpt"]) == [
        pd.Timestamp("2024-12-31 23:00"),
        pd.Timestamp("2025-01-01 00:00"),
    ]


def test_dst_repeated_hour_is_flagged_not_dropped():
    # Fall-back: ERCOT disambiguates the repeated hour with a ` DST` suffix.
    # It does not emit two identical labels.
    df = pd.DataFrame(
        {
            "Hour Ending": [
                "11/03/2024 02:00",
                "11/03/2024 02:00 DST",
                "11/03/2024 03:00",
            ]
        }
    )
    out = hour_ending_to_beginning(df)
    assert len(out) == 3, "duplicate DST hour must be preserved, not silently dropped"
    assert out["dst_transition_hour"].tolist() == [True, True, False]
    assert out["datetime_beginning_cpt"].iloc[1] == pd.Timestamp("2024-11-03 01:00")


def test_datetime_valued_cell_is_parsed_not_nulled():
    # Native_Load_2022.xlsx stores exactly one cell as a real datetime rather
    # than text (row 8016). A bare `.str` accessor yields NaT there silently.
    # This is that row and its two real neighbours.
    df = pd.DataFrame(
        {
            "Hour Ending": [
                "11/30/2022 24:00",
                datetime(2022, 12, 1, 1, 0),
                "12/01/2022 02:00",
            ]
        }
    )
    out = hour_ending_to_beginning(df)
    assert list(out["datetime_beginning_cpt"]) == [
        pd.Timestamp("2022-11-30 23:00"),
        pd.Timestamp("2022-12-01 00:00"),
        pd.Timestamp("2022-12-01 01:00"),
    ]


def test_non_dst_rows_are_not_flagged():
    df = pd.DataFrame({"Hour Ending": ["01/01/2024 01:00", "01/01/2024 02:00"]})
    out = hour_ending_to_beginning(df)
    assert out["dst_transition_hour"].tolist() == [False, False]


def test_missing_column_raises():
    with pytest.raises(KeyError, match="Hour Ending"):
        hour_ending_to_beginning(pd.DataFrame({"wrong": [1]}))


def test_gradient_matches_dom_formula():
    # 60 MW rise over one hour = 1.0 MW/min.
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [1000.0, 1060.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert out["load_gradient_abs_mw_per_min_COAST"].tolist()[1] == pytest.approx(1.0)


def test_gradient_is_absolute_valued():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [1060.0, 1000.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert out["load_gradient_abs_mw_per_min_COAST"].tolist()[1] == pytest.approx(1.0)


def test_first_row_is_nan():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(["2024-01-01 00:00"]),
            "load_mw_COAST": [1000.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert pd.isna(out["load_gradient_abs_mw_per_min_COAST"].iloc[0])


def test_multiple_zones_are_independent():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [1000.0, 1060.0],
            "load_mw_WEST": [500.0, 500.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST", "WEST"])
    assert out["load_gradient_abs_mw_per_min_COAST"].iloc[1] == pytest.approx(1.0)
    assert out["load_gradient_abs_mw_per_min_WEST"].iloc[1] == pytest.approx(0.0)


def test_source_load_columns_are_preserved():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [1000.0, 1060.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert out["load_mw_COAST"].tolist() == [1000.0, 1060.0]


def test_unsorted_timestamps_raise():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 02:00", "2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            "load_mw_COAST": [900.0, 1000.0, 1060.0],
        }
    )
    with pytest.raises(ValueError, match="sorted"):
        add_zone_gradient_columns(df, zones=["COAST"])


def test_duplicate_dst_timestamps_do_not_raise():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-11-03 01:00", "2024-11-03 01:00", "2024-11-03 02:00"]
            ),
            "load_mw_COAST": [1000.0, 1010.0, 1020.0],
        }
    )
    out = add_zone_gradient_columns(df, zones=["COAST"])
    assert len(out) == 3


def test_default_zones_produces_all_nine_columns():
    df = pd.DataFrame(
        {
            "datetime_beginning_cpt": pd.to_datetime(
                ["2024-01-01 00:00", "2024-01-01 01:00"]
            ),
            **{f"load_mw_{zone}": [1000.0, 1010.0] for zone in ZONES},
        }
    )
    out = add_zone_gradient_columns(df)
    produced = [c for c in out.columns if c.startswith("load_gradient_abs_mw_per_min_")]
    assert len(produced) == 9
    assert set(produced) == {f"load_gradient_abs_mw_per_min_{zone}" for zone in ZONES}
