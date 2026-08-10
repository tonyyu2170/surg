"""Stage-1 CAISO diagnostic: level/volatility trends + horse race.

Two panels, per the 2026-08-09 roster-growth fix (docs/decisions.md):
  Panel A (full depth): 4 TAC zones present since the start of the archive
    (caiso_total, pge, sce, sdge), from 2009-04-01.
  Panel B (modern): all 6 TAC zones -- adds vea (first-seen 2013-01-02) and
    mwd (first-seen 2018-03-21) -- from 2018-11-01 onward, the earliest
    point at which every zone in the roster has NaN-free coverage (later
    than mwd's first appearance: vea has a genuine single-hour raw-archive
    gap at 2018-10-31 14:00 PPT).
Both panels also run the common-overlap window (2023-01-01 -> 2025-05-01
exclusive).

The price side is restricted to ANALYZED_NODES (PGAE, SCE) per the
2026-08-09 retention-window discovery (docs/decisions.md): CAISO OASIS
PRC_LMP DAM v12 has a ~3-year rolling retention window, so real price data
begins 2023-04-12 for every node -- there is no 2010-era price depth,
unlike load. The price side is identical in both panels and is read once,
not rebuilt per panel -- level_vs_volatility takes a cross product of
zones x price_cols, so no name alignment between load zones and price
zones is required.

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
# All 6 zones NaN-free from this point. First-appearance (mwd: 2018-03-21) is
# NOT the same as complete coverage: empirically, vea has a genuine single-hour
# gap in the raw OASIS archive at 2018-10-31 14:00 PPT (confirmed absent from
# both surrounding chunk files, not a chunking artifact) -- later than mwd's
# own last gap (2018-03-29 13:00). Scanned all 6 zones' NaNs across the full
# panel: last NaN of any zone is vea's 2018-10-31 14:00; zero NaNs for any
# zone from 2018-11-01 onward.
MODERN_START = pd.Timestamp("2018-11-01")

# Price-side node scope (2026-08-09 human decision, docs/decisions.md): the
# fetch was stopped before completing the full 7-node NODE_MAP roster (VEA
# and the three TH_* hubs were never fetched). Of the 3 DLAP nodes that were
# fetched, SDGE has only 4 chunks (~1 month) of real data within the OASIS
# retention window -- too little for the horse race -- so the price side of
# this diagnostic is restricted to PGAE and SCE only.
ANALYZED_NODES = ["DLAP_PGAE-APND", "DLAP_SCE-APND"]


def read_zips(subdir: str, node_prefixes: list[str] | None = None) -> pd.DataFrame:
    """Read every CSV member of every zip under RAW/subdir.

    CAISO OASIS PRC_LMP DAM v12 has a ~3-year rolling retention window
    (docs/decisions.md, 2026-08-09): a request outside that window still
    returns a valid zip (starts with PK), but it contains a single XML
    disclaimer file instead of a CSV -- 549 of 637 price archives on disk
    (86%; 82% for SCE specifically, 183 of 224) are this "no data"
    response. Only .csv members are read; an archive
    with no CSV member (a pure XML disclaimer) is skipped entirely rather
    than crashing pd.read_csv on XML content.

    node_prefixes, if given, restricts to zips whose filename starts with
    one of the given node prefixes (used to scope the price side to
    ANALYZED_NODES without touching the load side).
    """
    frames = []
    for zpath in sorted((RAW / subdir).glob("*.zip")):
        if node_prefixes is not None and not zpath.name.startswith(tuple(node_prefixes)):
            continue
        with zipfile.ZipFile(zpath) as zf:
            csv_members = [m for m in sorted(zf.namelist()) if m.endswith(".csv")]
            for member in csv_members:
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

    # kind in "if" (int or float), not strictly float: raw MW is int64 in the
    # OASIS CSVs, and pandas' pivot_table/unstack only upcasts a column to
    # float64 when the *pivot block it shares* has missing cells to fill --
    # e.g. Panel A's full 2009-2026 pivot upcasts every zone (including
    # NaN-free ones) because vea/mwd have historical gaps in that same
    # block. A clean, fully-rectangular window (no zone missing any hour)
    # legitimately stays int64. The real drift signal is non-numeric dtype
    # (e.g. object, from a stray string), which this still catches.
    bad_dtype = [z for z in zones if panel[f"load_mw_{z}"].dtype.kind not in "if"]
    if bad_dtype:
        raise AssertionError(f"non-numeric load columns (schema drift?): {bad_dtype}")

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
    prices = parse_dam_lmp(read_zips("da_lmp", node_prefixes=ANALYZED_NODES))

    print("\n########## PANEL A: full depth (4 zones, from 2009-04-01) ##########")
    panel_a = build_panel(
        load_raw, prices, zones=FULL_DEPTH_ZONES,
        panel_path=Path("data/interim/caiso_diagnostic_panel_full_depth.parquet"),
    )
    run_panel(panel_a, FULL_DEPTH_ZONES, market_label="CAISO-full-depth",
              figdir=Path("outputs/caiso_diagnostic_full_depth"), max_start=FULL_DEPTH_START)

    print("\n########## PANEL B: modern (6 zones, from 2018-11-01) ##########")
    gmt = pd.to_datetime(load_raw["INTERVALSTARTTIME_GMT"], utc=True)
    load_raw_ppt = gmt.dt.tz_convert("America/Los_Angeles").dt.tz_localize(None)
    modern_load_raw = load_raw[load_raw_ppt >= MODERN_START]
    panel_b = build_panel(
        modern_load_raw, prices, zones=ZONES,
        panel_path=Path("data/interim/caiso_diagnostic_panel_modern.parquet"),
    )
    run_panel(panel_b, ZONES, market_label="CAISO-modern",
              figdir=Path("outputs/caiso_diagnostic_modern"), max_start=MODERN_START)
