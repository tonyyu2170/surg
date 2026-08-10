# tests/test_miso_fetch.py
from __future__ import annotations

import pandas as pd

from scripts.miso_fetch import MAX_START, family_url, market_days


def test_load_url_shape():
    assert family_url("df_al", pd.Timestamp("2023-01-03")) == (
        "https://docs.misoenergy.org/marketreports/20230103_df_al.xls"
    )


def test_price_url_shape():
    assert family_url("da_expost_lmp", pd.Timestamp("2025-08-06")) == (
        "https://docs.misoenergy.org/marketreports/20250806_da_expost_lmp.csv"
    )


def test_market_days_start_at_the_stage1_window():
    assert market_days()[0] == MAX_START
    assert MAX_START == pd.Timestamp("2023-01-01")


def test_market_days_are_contiguous_daily():
    days = pd.Series(market_days())
    assert (days.diff().dropna() == pd.Timedelta(days=1)).all()
