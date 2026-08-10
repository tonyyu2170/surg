"""Stage-1 CAISO diagnostic: level/volatility trends + horse race.

Two panels, per the 2026-08-09 roster-growth fix (docs/decisions.md):
  Panel A (full depth): 4 TAC zones present since the start of the archive
    (caiso_total, pge, sce, sdge), from 2009-04-01.
  Panel B (modern): all 6 TAC zones -- adds vea (first-seen 2013-01-02) and
    mwd (first-seen 2018-03-21) -- from 2018-03-21 onward, the earliest
    point at which every zone in the roster has appeared.
Both panels also run the common-overlap window (2023-01-01 -> 2025-05-01
exclusive). The price side (7 CAISO nodes from NODE_MAP) is identical in
both panels and is read once, not rebuilt per panel -- level_vs_volatility
takes a cross product of zones x price_cols, so no name alignment between
load zones and price zones is required.

Usage: .venv/bin/python scripts/caiso_diagnostic.py
Reads the zips fetched by scripts/caiso_fetch.py; writes panels + figures/
CSVs to outputs/caiso_diagnostic_full_depth/ and outputs/caiso_diagnostic_modern/.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END,
    COMMON_OVERLAP_START,
    FAR_FUTURE,
    add_zone_gradients,
    assert_panel_quality,
    data_quality_report,
    level_vs_volatility,
    trend_tables,
)
from surg.preprocessing.caiso_features import FULL_DEPTH_ZONES, ZONES, parse_dam_lmp, parse_load

RAW = Path("data/raw/caiso")
TIME = "datetime_beginning_ppt"
FULL_DEPTH_START = pd.Timestamp("2009-04-01")  # archive depth; 4 zones present since day one
MODERN_START = pd.Timestamp("2018-03-21")      # all 6 zones present (mwd is the last to appear)


def read_zips(subdir: str) -> pd.DataFrame:
    frames = []
    for zpath in sorted((RAW / subdir).glob("*.zip")):
        with zipfile.ZipFile(zpath) as zf:
            for member in sorted(zf.namelist()):
                frames.append(pd.read_csv(io.BytesIO(zf.read(member))))
    if not frames:
        raise RuntimeError(f"no zips under {RAW / subdir}")
    return pd.concat(frames, ignore_index=True)


def build_panel(
    load_raw: pd.DataFrame,
    prices: pd.DataFrame,
    *,
    zones: list[str],
    panel_path: Path,
) -> pd.DataFrame:
    panel = parse_load(load_raw)
    panel = panel.sort_values(TIME, kind="stable").reset_index(drop=True)
    panel = add_zone_gradients(panel, zones, time_col=TIME)
    assert_panel_quality(panel, zones, time_col=TIME, dst_pairs_per_year=1)

    bad_dtype = [z for z in zones if panel[f"load_mw_{z}"].dtype.kind != "f"]
    if bad_dtype:
        raise AssertionError(f"non-float load columns (schema drift?): {bad_dtype}")

    before = len(panel)
    panel = panel.merge(prices, on=TIME, how="left", validate="m:1")
    if len(panel) != before:
        raise AssertionError(f"price join changed row count: {before} -> {len(panel)}")

    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(panel_path, index=False)
    print(f"panel: {panel.shape} -> {panel_path}")
    return panel


def run_panel(
    panel: pd.DataFrame, zones: list[str], *, market_label: str, figdir: Path, max_start: pd.Timestamp
) -> None:
    price_cols = [c for c in panel.columns if c.startswith("da_lmp_")]
    data_quality_report(panel, price_cols, time_col=TIME, window_start=max_start, figdir=figdir)
    trend_tables(panel, zones, time_col=TIME, figdir=figdir, market=market_label)
    for label, start, end in [
        ("max", max_start, FAR_FUTURE),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, zones, price_cols, time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=figdir, market=market_label, label=label)


if __name__ == "__main__":
    load_raw = read_zips("load")
    prices = parse_dam_lmp(read_zips("da_lmp"))

    print("\n########## PANEL A: full depth (4 zones, from 2009-04-01) ##########")
    panel_a = build_panel(
        load_raw, prices, zones=FULL_DEPTH_ZONES,
        panel_path=Path("data/interim/caiso_diagnostic_panel_full_depth.parquet"),
    )
    run_panel(panel_a, FULL_DEPTH_ZONES, market_label="CAISO-full-depth",
              figdir=Path("outputs/caiso_diagnostic_full_depth"), max_start=FULL_DEPTH_START)

    print("\n########## PANEL B: modern (6 zones, from 2018-03-21) ##########")
    gmt = pd.to_datetime(load_raw["INTERVALSTARTTIME_GMT"], utc=True)
    load_raw_ppt = gmt.dt.tz_convert("America/Los_Angeles").dt.tz_localize(None)
    modern_load_raw = load_raw[load_raw_ppt >= MODERN_START]
    panel_b = build_panel(
        modern_load_raw, prices, zones=ZONES,
        panel_path=Path("data/interim/caiso_diagnostic_panel_modern.parquet"),
    )
    run_panel(panel_b, ZONES, market_label="CAISO-modern",
              figdir=Path("outputs/caiso_diagnostic_modern"), max_start=MODERN_START)
