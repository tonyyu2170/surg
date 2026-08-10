# tests/test_spp_features.py
from __future__ import annotations

import pandas as pd

from surg.preprocessing.spp_features import (
    TIME, ZONES, gmt_hour_ending_to_local_beginning, monthly_members,
    parse_wide_load, zone_price_from_nodal,
)


def _wide(stamps: list[str]) -> pd.DataFrame:
    data: dict[str, list] = {"MarketHour": stamps}
    for zone in ZONES:
        data[f" {zone}"] = [100.0 + i for i in range(len(stamps))]
    return pd.DataFrame(data)


def test_zone_roster_is_the_locked_seventeen():
    assert len(ZONES) == 17
    assert "WAUE" in ZONES
    for absent in ("PRPA", "WACM", "WAUW", "PSCO"):
        assert absent not in ZONES


def test_gmt_hour_ending_converts_to_local_hour_beginning():
    # 06:00Z hour-ending == hour beginning 00:00 CDT on an ordinary summer day
    got = gmt_hour_ending_to_local_beginning(pd.Series(["08/06/2025 06:00:00"]))
    assert got.iloc[0] == pd.Timestamp("2025-08-06 00:00")


def test_fall_back_day_yields_twenty_five_rows_with_a_duplicate_pair():
    stamps = [f"11/02/2025 {h:02d}:00:00" for h in range(6, 24)]
    stamps += [f"11/03/2025 {h:02d}:00:00" for h in range(0, 7)]
    out = parse_wide_load(_wide(stamps))
    assert len(out) == 25
    assert out["dst_transition_hour"].sum() == 2


def test_parse_strips_header_whitespace():
    out = parse_wide_load(_wide(["08/06/2025 06:00:00"]))
    assert f"load_mw_{ZONES[0]}" in out.columns


def test_parse_handles_the_two_digit_year_format():
    out = parse_wide_load(_wide(["1/1/11 7:00"]))
    assert out[TIME].iloc[0] == pd.Timestamp("2011-01-01 00:00")


def test_zone_price_averages_nodes_by_prefix():
    nodal = pd.DataFrame(
        {
            TIME: [pd.Timestamp("2025-08-06 00:00")] * 3,
            "location": ["CSWS.A", "CSWS.B", "EDE.A"],
            "lmp": [10.0, 20.0, 99.0],
        }
    )
    out = zone_price_from_nodal(nodal, ["CSWS", "EDE"])
    assert out["da_lmp_CSWS"].iloc[0] == 15.0
    assert out["da_lmp_EDE"].iloc[0] == 99.0


def test_monthly_members_excludes_dailies():
    names = [
        "2023/HOURLY_LOAD-202301.csv",
        "2023/DAILY_HOURLY_LOAD-20230101.csv",
        "2023/",
    ]
    assert monthly_members(names) == ["2023/HOURLY_LOAD-202301.csv"]
