import pandas as pd
import pytest

from surg.preprocessing.ercot_features import hour_ending_to_beginning


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


def test_dst_duplicate_hour_is_flagged_not_dropped():
    # Fall-back: the 02:00 hour-ending value appears twice.
    df = pd.DataFrame(
        {"Hour Ending": ["11/03/2024 02:00", "11/03/2024 02:00", "11/03/2024 03:00"]}
    )
    out = hour_ending_to_beginning(df)
    assert len(out) == 3, "duplicate DST hour must be preserved, not silently dropped"
    assert out["dst_transition_hour"].tolist() == [True, True, False]


def test_non_dst_rows_are_not_flagged():
    df = pd.DataFrame({"Hour Ending": ["01/01/2024 01:00", "01/01/2024 02:00"]})
    out = hour_ending_to_beginning(df)
    assert out["dst_transition_hour"].tolist() == [False, False]


def test_missing_column_raises():
    with pytest.raises(KeyError, match="Hour Ending"):
        hour_ending_to_beginning(pd.DataFrame({"wrong": [1]}))


from surg.preprocessing.ercot_features import add_zone_gradient_columns


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
