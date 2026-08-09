"""Tests for IESO pure transforms."""
from __future__ import annotations

import pandas as pd
import pytest

from surg.preprocessing.ieso_features import ZONES, parse_demand_zonal, parse_hoep


def demand_frame():
    cols = ["Date", "Hour", "Ontario Demand", "Northwest", "Northeast", "Ottawa",
            "East", "Toronto", "Essa", "Bruce", "Southwest", "Niagara", "West",
            "Zone Total", "Diff"]
    rows = [
        ["2026-01-01", 1, 16526, 688, 1474, 1049, 1085, 5568, 1219, 96, 3000, 569, 1949, 16697, 171],
        ["2026-01-01", 2, 16000, 680, 1450, 1000, 1050, 5400, 1200, 95, 2950, 560, 1900, 16285, 285],
    ]
    return pd.DataFrame(rows, columns=cols)


def test_parse_demand_zonal_hour_beginning_and_wide():
    panel = parse_demand_zonal(demand_frame())
    assert panel.loc[0, "datetime_beginning_est"] == pd.Timestamp("2026-01-01 00:00:00")
    assert panel.loc[1, "datetime_beginning_est"] == pd.Timestamp("2026-01-01 01:00:00")
    assert panel.loc[0, "load_mw_toronto"] == 5568
    assert panel.loc[0, "load_mw_ontario"] == 16526
    assert set(f"load_mw_{z}" for z in ZONES) <= set(panel.columns)
    assert not panel["dst_transition_hour"].any()  # fixed EST: never flagged


def test_parse_demand_zonal_rejects_missing_zone():
    with pytest.raises(ValueError, match="Toronto"):
        parse_demand_zonal(demand_frame().drop(columns=["Toronto"]))


def test_parse_demand_zonal_rejects_bad_hour():
    frame = demand_frame()
    frame.loc[0, "Hour"] = 25
    with pytest.raises(ValueError, match="1-24"):
        parse_demand_zonal(frame)


def test_parse_hoep():
    raw = pd.DataFrame(
        {"Date": ["2024-06-01", "2024-06-01"], "Hour": [1, 2], "HOEP": [25.1, 27.9]}
    )
    prices = parse_hoep(raw)
    assert prices.loc[0, "hoep"] == 25.1
    assert prices.loc[0, "datetime_beginning_est"] == pd.Timestamp("2024-06-01 00:00:00")
