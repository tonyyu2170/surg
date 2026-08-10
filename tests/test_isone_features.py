# tests/test_isone_features.py
from __future__ import annotations

import pandas as pd
import pytest

from surg.preprocessing.isone_features import SHEETS, ZONES, build_panel, parse_smd_sheet


def _sheet(day: str = "2023-06-15", hours: int = 24) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Date": [pd.Timestamp(day)] * hours,
            "Hr_End": list(range(1, hours + 1)),
            "DA_Demand": [900.0 + h for h in range(hours)],
            "RT_Demand": [1000.0 + h for h in range(hours)],
            "DA_LMP": [30.0 + h for h in range(hours)],
            "DA_CC": [0.0] * hours,
        }
    )


def test_zone_list_and_sheet_names():
    assert ZONES == ["me", "nh", "vt", "ct", "ri", "sema", "wcma", "nema"]
    assert SHEETS["me"] == "ME"
    assert SHEETS["sema"] == "SEMA"


def test_parse_converts_hour_ending_to_hour_beginning():
    out = parse_smd_sheet(_sheet(), "me")
    assert out["datetime_beginning_ept"].iloc[0] == pd.Timestamp("2023-06-15 00:00")
    assert out["datetime_beginning_ept"].iloc[-1] == pd.Timestamp("2023-06-15 23:00")


def test_parse_uses_rt_demand_for_load_and_da_lmp_for_price():
    out = parse_smd_sheet(_sheet(), "me")
    assert out["load_mw_me"].iloc[0] == 1000.0
    assert out["da_lmp_me"].iloc[0] == 30.0


def test_parse_rejects_hour_outside_1_to_24():
    bad = _sheet()
    bad.loc[0, "Hr_End"] = 25
    with pytest.raises(ValueError, match="Hr_End"):
        parse_smd_sheet(bad, "me")


def test_build_panel_merges_zones_and_flags_no_dst():
    panel = build_panel({z: _sheet() for z in ZONES})
    assert len(panel) == 24
    assert not panel["dst_transition_hour"].any()
    for zone in ZONES:
        assert f"load_mw_{zone}" in panel.columns
        assert f"da_lmp_{zone}" in panel.columns


def test_build_panel_rejects_a_zone_with_a_different_time_index():
    frames = {z: _sheet() for z in ZONES}
    frames["nh"] = _sheet(hours=23)
    with pytest.raises(ValueError, match="time index"):
        build_panel(frames)
