# scripts/isone_diagnostic.py
"""Stage-1 ISO-NE diagnostic. Usage: .venv/bin/python scripts/isone_diagnostic.py

ISO-NE is the designated low-data-center CONTROL market. Windows:
max = 2016-01 -> 2026-06-30 (the workbook series ends there);
overlap = the shared 2023-01 -> 2025-04-30 capstone window.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.isone_features import TIME, ZONES, build_panel, read_workbook

RAW = Path("data/raw/isone")
PANEL = Path("data/interim/isone_diagnostic_panel.parquet")
FIGDIR = Path("outputs/isone_diagnostic")
MAX_START = pd.Timestamp("2016-01-01")
MAX_END = pd.Timestamp("2026-07-01")  # exclusive; series ends 2026-06-30
PRICE_COLS = [f"da_lmp_{z}" for z in ZONES]


def build() -> pd.DataFrame:
    books = sorted(RAW.glob("*_smd_hourly.xls*"))
    if not books:
        raise RuntimeError(f"no workbooks under {RAW} - run scripts/isone_fetch.py")

    frames = [build_panel(read_workbook(path)) for path in books]
    # One workbook per year, so the years never overlap and there is nothing to
    # de-duplicate. Dropping duplicate timestamps here would silently delete the
    # second half of each post-2024 fall-back pair.
    panel = pd.concat(frames, ignore_index=True)
    panel = panel.sort_values(TIME, kind="mergesort").reset_index(drop=True)

    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    # 1, not 0: from 2024 the workbook uses real local clock time and carries a
    # genuine fall-back pair. This is an upper bound, satisfied by the
    # zero-pair years 2016-2023 as well.
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=1)

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    panel = build()
    data_quality_report(panel, PRICE_COLS, time_col=TIME,
                        window_start=MAX_START, figdir=FIGDIR)
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="ISONE")
    for label, start, end in [
        ("max", MAX_START, MAX_END),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, PRICE_COLS, time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="ISONE", label=label)
