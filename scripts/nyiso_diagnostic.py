"""Stage-1 NYISO diagnostic: level/volatility trends + horse race.

Two panels, per the 2026-08-09 zone-convention fix (docs/decisions.md):
  Panel A (merged): 10 load zones (N.Y.C./LONGIL collapsed into one
    nyc_longil column, summed post-2005-01-31), full archive depth from
    2001-06.
  Panel B (split): 11 load zones, today's convention, from 2005-01-31
    onward. Pre-split rows (the combined N.Y.C._LONGIL name) are excluded
    from the raw load frame *before* parse_load runs, so parse_load's
    "unknown zone name" guard stays a live drift check rather than a
    silenced error.
Both panels also run the common-overlap window (2023-01-01 -> 2025-05-01
exclusive). The price side (11 NY zones, four external interface/proxy
buses dropped) is identical in both panels and is read once, not rebuilt
per panel — level_vs_volatility takes a cross product of zones x
price_cols, so no name alignment between load zones and price zones is
required.

Usage: .venv/bin/python scripts/nyiso_diagnostic.py
Reads the zips fetched by scripts/nyiso_fetch.py; writes panels + figures/
CSVs to outputs/nyiso_diagnostic_merged/ and outputs/nyiso_diagnostic_split/.
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
from surg.preprocessing.nyiso_features import MERGED_ZONES, ZONES, parse_lbmp, parse_load

RAW = Path("data/raw/nyiso")
TIME = "datetime_beginning_ept"
MERGED_START = pd.Timestamp("2001-06-01")  # load-archive depth
SPLIT_START = pd.Timestamp("2005-01-31")   # split-zone convention begins


def read_family(subdir: str) -> pd.DataFrame:
    frames = []
    for zpath in sorted((RAW / subdir).glob("*.zip")):
        with zipfile.ZipFile(zpath) as zf:
            for member in sorted(zf.namelist()):
                frames.append(pd.read_csv(io.BytesIO(zf.read(member))))
    if not frames:
        raise RuntimeError(f"no zips under {RAW / subdir}")
    return pd.concat(frames, ignore_index=True)


def merge_prices(panel: pd.DataFrame, da: pd.DataFrame, rt: pd.DataFrame) -> pd.DataFrame:
    for prices in (da, rt):
        before = len(panel)
        panel = panel.merge(prices, on=TIME, how="left", validate="m:1")
        if len(panel) != before:
            raise AssertionError(f"price join changed row count: {before} -> {len(panel)}")
    return panel


def build_panel(
    load_raw: pd.DataFrame,
    da: pd.DataFrame,
    rt: pd.DataFrame,
    *,
    merge_nyc_longil: bool,
    zones: list[str],
    panel_path: Path,
) -> pd.DataFrame:
    panel = parse_load(load_raw, merge_nyc_longil=merge_nyc_longil)
    panel = panel.sort_values(TIME, kind="stable").reset_index(drop=True)
    panel = add_zone_gradients(panel, zones, time_col=TIME)
    assert_panel_quality(panel, zones, time_col=TIME, dst_pairs_per_year=1)

    bad_dtype = [z for z in zones if panel[f"load_mw_{z}"].dtype.kind != "f"]
    if bad_dtype:
        raise AssertionError(f"non-float load columns (schema drift?): {bad_dtype}")

    panel = merge_prices(panel, da, rt)
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(panel_path, index=False)
    print(f"panel: {panel.shape} -> {panel_path}")
    return panel


def run_panel(
    panel: pd.DataFrame, zones: list[str], *, market_label: str, figdir: Path, max_start: pd.Timestamp
) -> None:
    price_cols = [c for c in panel.columns if c.startswith(("da_lbmp_", "rt_lbmp_"))]
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
    load_raw = read_family("palIntegrated")
    da = parse_lbmp(read_family("damlbmp_zone"), prefix="da_lbmp")
    rt = parse_lbmp(read_family("realtime_zone"), prefix="rt_lbmp")

    print("\n########## PANEL A: merged (10 zones, full depth from 2001-06) ##########")
    panel_a = build_panel(
        load_raw, da, rt, merge_nyc_longil=True, zones=MERGED_ZONES,
        panel_path=Path("data/interim/nyiso_diagnostic_panel_merged.parquet"),
    )
    run_panel(panel_a, MERGED_ZONES, market_label="NYISO-merged",
              figdir=Path("outputs/nyiso_diagnostic_merged"), max_start=MERGED_START)

    print("\n########## PANEL B: split (11 zones, from 2005-01-31) ##########")
    stamps = pd.to_datetime(load_raw["Time Stamp"], format="mixed")
    split_load_raw = load_raw[stamps >= SPLIT_START]
    panel_b = build_panel(
        split_load_raw, da, rt, merge_nyc_longil=False, zones=ZONES,
        panel_path=Path("data/interim/nyiso_diagnostic_panel_split.parquet"),
    )
    run_panel(panel_b, ZONES, market_label="NYISO-split",
              figdir=Path("outputs/nyiso_diagnostic_split"), max_start=SPLIT_START)
