from datetime import datetime

import pandas as pd
import pytest

# Pnode IDs from src/surg/acquisition/targets.py (Loudoun cluster + others)
LOUDOUN_CLUSTER_IDS = (
    35010365,    # LOUDOUN
    35010371,    # PLEASANT VIEW
    1356178195,  # GOOSECRE
    1356178171,  # BRAMBLET
    1356178181,  # MOSBY
    1356178201,  # SKFFSCRK
)


def test_add_load_gradient_columns_computes_diff_per_hour():
    from surg.preprocessing.features import add_load_gradient_columns

    df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime([
            "2024-07-15T00:00:00",
            "2024-07-15T01:00:00",
            "2024-07-15T02:00:00",
        ]),
        "dom_load_mw": [10_000.0, 10_120.0, 10_080.0],
    })

    out = add_load_gradient_columns(df)

    # First row has no prior -> NaN
    assert pd.isna(out["dom_load_gradient_mw_per_hr"].iloc[0])
    # Second row: 10120 - 10000 = +120 MW/hr
    assert out["dom_load_gradient_mw_per_hr"].iloc[1] == 120.0
    assert out["dom_load_gradient_signed_mw_per_min"].iloc[1] == 2.0  # 120 / 60
    assert out["dom_load_gradient_abs_mw_per_min"].iloc[1] == 2.0
    # Third row: 10080 - 10120 = -40 MW/hr
    assert out["dom_load_gradient_mw_per_hr"].iloc[2] == -40.0
    assert out["dom_load_gradient_signed_mw_per_min"].iloc[2] == pytest.approx(-40 / 60)
    assert out["dom_load_gradient_abs_mw_per_min"].iloc[2] == pytest.approx(40 / 60)


def test_add_load_gradient_columns_preserves_existing_columns():
    from surg.preprocessing.features import add_load_gradient_columns
    df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(["2024-01-01T00:00:00"]),
        "dom_load_mw": [12_000.0],
        "extra": ["x"],
    })
    out = add_load_gradient_columns(df)
    assert "extra" in out.columns
    assert out["extra"].iloc[0] == "x"


def test_pivot_lmp_long_to_pnode_columns_creates_one_col_per_pnode():
    from surg.preprocessing.features import pivot_lmp_long_to_pnode_columns

    long_df = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime([
            "2024-07-15T18:00:00", "2024-07-15T18:00:00",
            "2024-07-15T19:00:00", "2024-07-15T19:00:00",
        ]),
        "pnode_id": [35010365, 35010371, 35010365, 35010371],
        "pnode_name": ["LOUDOUN", "PLEASANT VIEW", "LOUDOUN", "PLEASANT VIEW"],
        "congestion_price_rt": [10.0, 12.0, 15.0, 18.0],
        "total_lmp_rt": [50.0, 52.0, 55.0, 58.0],
    })

    out = pivot_lmp_long_to_pnode_columns(long_df)

    assert len(out) == 2  # 2 unique timestamps
    assert "datetime_beginning_ept" in out.columns
    # Per-pnode columns for congestion price
    assert "congestion_price_rt_35010365" in out.columns
    assert "congestion_price_rt_35010371" in out.columns
    # Per-pnode columns for total LMP
    assert "total_lmp_rt_35010365" in out.columns
    assert "total_lmp_rt_35010371" in out.columns
    # Values
    row0 = out.iloc[0]
    assert row0["congestion_price_rt_35010365"] == 10.0
    assert row0["congestion_price_rt_35010371"] == 12.0


def test_add_loudoun_cluster_columns_computes_mean_and_max():
    from surg.preprocessing.features import (
        pivot_lmp_long_to_pnode_columns, add_loudoun_cluster_columns,
    )

    rows = []
    for pid in LOUDOUN_CLUSTER_IDS:
        rows.append({
            "datetime_beginning_ept": pd.Timestamp("2024-07-15T18:00:00"),
            "pnode_id": pid, "pnode_name": str(pid),
            "congestion_price_rt": 10.0 + (pid % 100),  # mild variation
            "total_lmp_rt": 50.0 + (pid % 100),
        })
    long_df = pd.DataFrame(rows)

    wide = pivot_lmp_long_to_pnode_columns(long_df)
    out = add_loudoun_cluster_columns(wide, LOUDOUN_CLUSTER_IDS)

    cluster_cols = [f"congestion_price_rt_{pid}" for pid in LOUDOUN_CLUSTER_IDS]
    expected_mean = wide[cluster_cols].mean(axis=1).iloc[0]
    expected_max = wide[cluster_cols].max(axis=1).iloc[0]

    assert out["congestion_price_rt_cluster_mean"].iloc[0] == expected_mean
    assert out["congestion_price_rt_cluster_max"].iloc[0] == expected_max
    # total_lmp_rt cluster mean is also added
    assert "total_lmp_rt_cluster_mean" in out.columns


def test_add_sync_event_columns_marks_active_hours():
    from surg.preprocessing.features import add_sync_event_columns

    timestamps = pd.to_datetime([
        "2024-07-15T17:00:00",  # before event
        "2024-07-15T18:00:00",  # event covers 18:30-19:15 → 18:00 hour overlaps event
        "2024-07-15T19:00:00",  # 19:00 hour: event ends 19:15, so still active
        "2024-07-15T20:00:00",  # after event
    ])
    panel = pd.DataFrame({"datetime_beginning_ept": timestamps})
    events = pd.DataFrame({
        "event_start_ept": [pd.Timestamp("2024-07-15T18:30:00")],
        "event_end_ept":   [pd.Timestamp("2024-07-15T19:15:00")],
        "event_id":        [0],
    })

    out = add_sync_event_columns(panel, events)
    active = list(out["sync_reserve_event_active"])
    # An event covers timestamp t if event_start <= t+1h AND event_end > t
    # (any overlap with the [t, t+1h) hour bucket).
    assert active == [False, True, True, False]
    # event_id is NaN when inactive, 0 when this event is active
    assert pd.isna(out["sync_reserve_event_id"].iloc[0])
    assert out["sync_reserve_event_id"].iloc[1] == 0
    assert out["sync_reserve_event_id"].iloc[2] == 0
    assert pd.isna(out["sync_reserve_event_id"].iloc[3])


def test_add_sync_event_columns_handles_empty_events():
    from surg.preprocessing.features import add_sync_event_columns
    panel = pd.DataFrame({
        "datetime_beginning_ept": pd.to_datetime(["2024-07-15T18:00:00"])
    })
    events = pd.DataFrame({"event_start_ept": pd.Series(dtype="datetime64[ns]"),
                           "event_end_ept": pd.Series(dtype="datetime64[ns]"),
                           "event_id": pd.Series(dtype="int64")})

    out = add_sync_event_columns(panel, events)
    assert out["sync_reserve_event_active"].iloc[0] is False or \
           bool(out["sync_reserve_event_active"].iloc[0]) is False
    assert pd.isna(out["sync_reserve_event_id"].iloc[0])
