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
