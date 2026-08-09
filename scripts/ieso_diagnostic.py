"""Stage-1 IESO diagnostic. Usage: .venv/bin/python scripts/ieso_diagnostic.py

HOEP era only (checkpoint decision 2026-08-09: no MRP-era collector).
Horse-race windows: max = 2003-01 -> 2025-04-30; overlap = 2023-01 -> 2025-04-30.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.ieso_features import ZONES, parse_demand_zonal, parse_hoep

RAW = Path("data/raw/ieso")
PANEL = Path("data/interim/ieso_diagnostic_panel.parquet")
FIGDIR = Path("outputs/ieso_diagnostic")
TIME = "datetime_beginning_est"
MAX_START = pd.Timestamp("2003-01-01")
HOEP_END = pd.Timestamp("2025-05-01")  # exclusive: Market Renewal boundary


def read_family(family: str) -> pd.DataFrame:
    frames = [
        pd.read_csv(path, comment="\\")
        for path in sorted((RAW / family).glob("*.csv"))
    ]
    if not frames:
        raise RuntimeError(f"no files under {RAW / family}")
    return pd.concat(frames, ignore_index=True)


def build_panel() -> pd.DataFrame:
    panel = parse_demand_zonal(read_family("DemandZonal"))
    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=0)

    hoep = parse_hoep(read_family("PriceHOEPPredispOR"))
    before = len(panel)
    panel = panel.merge(hoep, on=TIME, how="left", validate="m:1")
    if len(panel) != before:
        raise AssertionError(f"HOEP join changed row count: {before} -> {len(panel)}")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    panel = build_panel()
    data_quality_report(panel, ["hoep"], time_col=TIME,
                        window_start=MAX_START, figdir=FIGDIR)
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="IESO")
    for label, start, end in [
        ("max", MAX_START, HOEP_END),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, ["hoep"], time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="IESO", label=label)
