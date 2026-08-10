# tests/test_spp_fetch.py
from __future__ import annotations

import pandas as pd

from scripts.spp_fetch import (
    DAILY_ERA_START, MAX_START, PANEL_END, daily_dates, daily_url, zip_url,
)


def test_zip_url_shape():
    assert zip_url("hourly-load", 2019) == (
        "https://portal.spp.org/file-browser-api/download/hourly-load"
        "?path=/2019/2019.zip"
    )


def test_daily_load_url_shape():
    url = daily_url("hourly-load", pd.Timestamp("2025-08-06"))
    assert url.endswith("?path=/2025/DAILY_HOURLY_LOAD-20250806.csv")


def test_daily_price_url_shape():
    url = daily_url("da-lmp-by-settlement-location", pd.Timestamp("2025-08-06"))
    assert url.endswith("?path=/2025/08/By_Day/DA-LMP-SL-202508060100.csv")


def test_daily_dates_span_the_daily_era_only():
    dates = daily_dates()
    assert dates[0] == DAILY_ERA_START
    assert dates[-1] <= PANEL_END


def test_window_constants_match_the_locked_decision():
    assert MAX_START == pd.Timestamp("2016-01-01")
    assert PANEL_END == pd.Timestamp("2026-03-24")
