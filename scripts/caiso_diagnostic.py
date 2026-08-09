"""Stage-1 CAISO diagnostic. Usage: .venv/bin/python scripts/caiso_diagnostic.py"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START, FAR_FUTURE,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.caiso_features import ZONES, parse_dam_lmp, parse_load

RAW = Path("data/raw/caiso")
PANEL = Path("data/interim/caiso_diagnostic_panel.parquet")
FIGDIR = Path("outputs/caiso_diagnostic")
TIME = "datetime_beginning_ppt"
MAX_START = pd.Timestamp("2009-04-01")


def read_zips(subdir: str) -> pd.DataFrame:
    frames = []
    for zpath in sorted((RAW / subdir).glob("*.zip")):
        with zipfile.ZipFile(zpath) as zf:
            for member in sorted(zf.namelist()):
                frames.append(pd.read_csv(io.BytesIO(zf.read(member))))
    if not frames:
        raise RuntimeError(f"no zips under {RAW / subdir}")
    return pd.concat(frames, ignore_index=True)


def build_panel() -> pd.DataFrame:
    panel = parse_load(read_zips("load"))
    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=1)

    prices = parse_dam_lmp(read_zips("da_lmp"))
    before = len(panel)
    panel = panel.merge(prices, on=TIME, how="left", validate="m:1")
    if len(panel) != before:
        raise AssertionError(f"price join changed row count: {before} -> {len(panel)}")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    panel = build_panel()
    price_cols = [c for c in panel.columns if c.startswith("da_lmp_")]
    data_quality_report(panel, price_cols, time_col=TIME,
                        window_start=MAX_START, figdir=FIGDIR)
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="CAISO")
    for label, start, end in [
        ("max", MAX_START, FAR_FUTURE),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, price_cols, time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="CAISO", label=label)
