# tests/test_miso_features.py
from __future__ import annotations

import pandas as pd

from surg.preprocessing.miso_features import (
    TIME, ZONES, parse_da_expost_lmp, parse_df_al,
)


def _df_al_raw() -> pd.DataFrame:
    header = ["Market Day", "HourEnding"]
    for zone in ZONES + ["MISO"]:
        header += [f"{zone} MTLF (MWh)", f"{zone} ActualLoad (MWh)"]
    rows: list[list] = [
        ["FORECASTED AND"] + [None] * 15,
        ["ACTUAL LOAD REPORT"] + [None] * 15,
        ["Published Date:", pd.Timestamp("2023-01-03")] + [None] * 14,
        ["Reporting Period:", pd.Timestamp("2023-01-02")] + [None] * 14,
        header,
        ["January 02, 2023"] + [None] * 15,
    ]
    for hour in range(1, 25):
        row: list = [pd.Timestamp("2023-01-02"), hour]
        for _ in ZONES + ["MISO"]:
            row += [1000.0 + hour, 900.0 + hour]
        rows.append(row)
    for hour in range(1, 25):  # forecast-only day: ActualLoad blank
        row = [pd.Timestamp("2023-01-03"), hour]
        for _ in ZONES + ["MISO"]:
            row += [1000.0 + hour, None]
        rows.append(row)
    return pd.DataFrame(rows)


def test_zone_groups_are_the_six_lrz_groups():
    assert ZONES == ["LRZ1", "LRZ2_7", "LRZ3_5", "LRZ4", "LRZ6", "LRZ8_9_10"]


def test_parse_df_al_keeps_only_actual_load_days():
    out = parse_df_al(_df_al_raw())
    assert len(out) == 24
    assert out[TIME].dt.date.nunique() == 1


def test_parse_df_al_converts_hour_ending_to_hour_beginning():
    out = parse_df_al(_df_al_raw())
    assert out[TIME].iloc[0] == pd.Timestamp("2023-01-02 00:00")
    assert out[TIME].iloc[-1] == pd.Timestamp("2023-01-02 23:00")


def test_parse_df_al_uses_actual_not_forecast():
    out = parse_df_al(_df_al_raw())
    assert out["load_mw_LRZ1"].iloc[0] == 901.0


def test_parse_df_al_flags_no_dst():
    assert not parse_df_al(_df_al_raw())["dst_transition_hour"].any()


def _lmp_raw() -> pd.DataFrame:
    header = ["Node", "Type", "Value"] + [f"HE {h}" for h in range(1, 25)]
    rows: list[list] = [
        ["Day Ahead Market ExPost LMPs"] + [None] * 26,
        ["01/03/2023"] + [None] * 26,
        [None] * 27,
        [None, None, None, "All Hours-Ending are Eastern Standard Time (EST)"] + [None] * 23,
        header,
        ["MINN.HUB", "Hub", "LMP"] + [20.0 + h for h in range(24)],
        ["MINN.HUB", "Hub", "MCC"] + [1.0] * 24,
        ["AECI", "Interface", "LMP"] + [30.0] * 24,
    ]
    return pd.DataFrame(rows)


def test_parse_lmp_keeps_only_total_lmp_rows():
    out = parse_da_expost_lmp(_lmp_raw(), pd.Timestamp("2023-01-03"))
    assert set(out["node"]) == {"MINN.HUB", "AECI"}
    assert len(out) == 48


def test_parse_lmp_is_hour_beginning_est():
    out = parse_da_expost_lmp(_lmp_raw(), pd.Timestamp("2023-01-03"))
    first = out[out["node"] == "MINN.HUB"].sort_values(TIME)
    assert first[TIME].iloc[0] == pd.Timestamp("2023-01-03 00:00")
    assert first["lmp"].iloc[0] == 20.0
