# tests/test_isone_fetch.py
from __future__ import annotations

from scripts.isone_fetch import URLS, target_path


def test_urls_cover_2016_through_2026():
    assert sorted(URLS) == list(range(2016, 2027))


def test_2016_is_xls_and_others_are_xlsx():
    assert URLS[2016].endswith(".xls")
    for year in range(2017, 2027):
        assert URLS[year].endswith(".xlsx")


def test_numeric_document_ids_are_verified_constants():
    assert "/100008/" in URLS[2024]
    assert "/100020/" in URLS[2025]
    assert "/100032/" in URLS[2026]


def test_target_path_keeps_the_source_extension(tmp_path):
    assert target_path(tmp_path, 2016).name == "2016_smd_hourly.xls"
    assert target_path(tmp_path, 2023).name == "2023_smd_hourly.xlsx"
