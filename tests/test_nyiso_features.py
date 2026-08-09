"""Tests for NYISO pure transforms."""
from __future__ import annotations

import pandas as pd
import pytest

from surg.preprocessing.nyiso_features import ZONES, parse_lbmp, parse_load


def load_frame(rows):
    return pd.DataFrame(
        rows, columns=["Time Stamp", "Time Zone", "Name", "PTID", "Integrated Load"]
    )


def all_zone_rows(stamp, tz, value):
    names = [
        "CAPITL", "CENTRL", "DUNWOD", "GENESE", "HUD VL", "LONGIL",
        "MHK VL", "MILLWD", "N.Y.C.", "NORTH", "WEST",
    ]
    return [[stamp, tz, n, 61750 + i, value] for i, n in enumerate(names)]


def test_parse_load_wide_and_hour_beginning():
    raw = load_frame(
        all_zone_rows("07/01/2026 00:00:00", "EDT", 1000.0)
        + all_zone_rows("07/01/2026 01:00:00", "EDT", 1100.0)
    )
    panel = parse_load(raw)
    assert list(panel["datetime_beginning_ept"]) == [
        pd.Timestamp("2026-07-01 00:00:00"),
        pd.Timestamp("2026-07-01 01:00:00"),
    ]
    assert panel.loc[0, "load_mw_nyc"] == 1000.0
    assert set(f"load_mw_{z}" for z in ZONES) <= set(panel.columns)
    assert not panel["dst_transition_hour"].any()


def test_parse_load_flags_fallback_pair():
    raw = load_frame(
        all_zone_rows("11/02/2025 01:00:00", "EDT", 900.0)
        + all_zone_rows("11/02/2025 01:00:00", "EST", 905.0)
    )
    panel = parse_load(raw)
    assert len(panel) == 2
    assert panel["dst_transition_hour"].all()


def test_parse_load_rejects_missing_zone():
    rows = all_zone_rows("07/01/2026 00:00:00", "EDT", 1000.0)[:-1]
    with pytest.raises(ValueError, match="WEST"):
        parse_load(load_frame(rows))


def test_parse_lbmp_wide():
    raw = pd.DataFrame(
        {
            "Time Stamp": ["07/01/2026 00:00", "07/01/2026 00:00"],
            "Name": ["CAPITL", "N.Y.C."],
            "PTID": [61757, 61761],
            "LBMP ($/MWHr)": [53.6, 60.1],
            "Marginal Cost Losses ($/MWHr)": [1.9, 3.2],
            "Marginal Cost Congestion ($/MWHr)": [0.0, -2.0],
        }
    )
    prices = parse_lbmp(raw, prefix="da_lbmp")
    assert prices.loc[0, "da_lbmp_nyc"] == 60.1
    assert prices.loc[0, "da_lbmp_capitl"] == 53.6
    assert list(prices.columns)[0] == "datetime_beginning_ept"


def test_parse_lbmp_drops_external_proxy_buses():
    raw = pd.DataFrame(
        {
            "Time Stamp": ["07/01/2026 00:00"] * 6,
            "Name": ["CAPITL", "N.Y.C.", "H Q", "NPX", "O H", "PJM"],
            "PTID": [61757, 61761, 61844, 61754, 61753, 61752],
            "LBMP ($/MWHr)": [53.6, 60.1, 20.0, 21.0, 22.0, 23.0],
            "Marginal Cost Losses ($/MWHr)": [1.9, 3.2, 0.0, 0.0, 0.0, 0.0],
            "Marginal Cost Congestion ($/MWHr)": [0.0, -2.0, 0.0, 0.0, 0.0, 0.0],
        }
    )
    prices = parse_lbmp(raw, prefix="da_lbmp")
    assert list(prices.columns) == ["datetime_beginning_ept", "da_lbmp_capitl", "da_lbmp_nyc"]
    assert prices.loc[0, "da_lbmp_nyc"] == 60.1


def test_parse_lbmp_still_raises_on_genuine_drift():
    raw = pd.DataFrame(
        {
            "Time Stamp": ["07/01/2026 00:00"],
            "Name": ["MARS"],
            "PTID": [99999],
            "LBMP ($/MWHr)": [15.0],
            "Marginal Cost Losses ($/MWHr)": [0.0],
            "Marginal Cost Congestion ($/MWHr)": [0.0],
        }
    )
    with pytest.raises(ValueError, match="MARS"):
        parse_lbmp(raw, prefix="da_lbmp")


def test_parse_load_merged_mode_sums_post_2005_pair():
    raw = load_frame(
        [row for row in all_zone_rows("02/01/2005 00:00:00", "EST", 1000.0)
         if row[2] not in ("N.Y.C.", "LONGIL")]
        + [["02/01/2005 00:00:00", "EST", "N.Y.C.", 61761, 700.0]]
        + [["02/01/2005 00:00:00", "EST", "LONGIL", 61762, 300.0]]
    )
    panel = parse_load(raw, merge_nyc_longil=True)
    assert panel.loc[0, "load_mw_nyc_longil"] == 1000.0
    assert "load_mw_nyc" not in panel.columns
    assert "load_mw_longil" not in panel.columns


def test_parse_load_merged_mode_continuous_across_2005_boundary():
    pre = load_frame(
        [row for row in all_zone_rows("01/01/2005 00:00:00", "EST", 1000.0)
         if row[2] not in ("N.Y.C.", "LONGIL")]
        + [["01/01/2005 00:00:00", "EST", "N.Y.C._LONGIL", 61761, 850.0]]
    )
    post = load_frame(
        [row for row in all_zone_rows("02/01/2005 00:00:00", "EST", 1000.0)
         if row[2] not in ("N.Y.C.", "LONGIL")]
        + [["02/01/2005 00:00:00", "EST", "N.Y.C.", 61761, 600.0]]
        + [["02/01/2005 00:00:00", "EST", "LONGIL", 61762, 250.0]]
    )
    raw = pd.concat([pre, post], ignore_index=True)
    panel = parse_load(raw, merge_nyc_longil=True)
    panel = panel.sort_values("datetime_beginning_ept").reset_index(drop=True)
    assert panel.loc[0, "load_mw_nyc_longil"] == 850.0
    assert panel.loc[1, "load_mw_nyc_longil"] == 850.0
    assert not panel["load_mw_nyc_longil"].isna().any()


def test_parse_load_split_mode_rejects_combined_zone_rows():
    raw = load_frame(
        [row for row in all_zone_rows("01/01/2005 00:00:00", "EST", 1000.0)
         if row[2] not in ("N.Y.C.", "LONGIL")]
        + [["01/01/2005 00:00:00", "EST", "N.Y.C._LONGIL", 61761, 850.0]]
    )
    with pytest.raises(ValueError, match="N.Y.C._LONGIL"):
        parse_load(raw)
