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
