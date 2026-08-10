# scripts/spp_diagnostic.py
"""Stage-1 SPP diagnostic. Usage: .venv/bin/python scripts/spp_diagnostic.py

Locked scope (2026-08-10): 17 zones, one panel, ending 2026-03-24. That end
stops before the wide->long schema break and the RTO-West roster jump, so the
footprint is constant throughout.

Zone price is the unweighted mean of nodal LMPs prefixed by the zone code - an
explicit estimator choice, not a settlement price. SPP publishes no zonal price.
Verified prefix match rate is stable across eras: 64.5% (2016) to 75.1% (2024)
of settlement locations resolve to one of the 17 zones; the unmatched remainder
are utility-prefixed nodes (AEC, AECC_*) that carry no control-zone name.

TWO EXECUTION FINDINGS not in the original plan (2026-08-10):

1. The price zips carry BOTH a `By_Day/` daily family with the same long schema
   as the standalone 2025+ dailies (`Interval, GMTIntervalEnd, Settlement
   Location, Pnode, LMP, MLC, MCC, MEC`) AND 12 monthly rollups
   (`DA-LMP-MONTHLY-SL-YYYYMM.csv`) which are WIDE by hour with different column
   names (`Date, Settlement Location Name, PNODE Name, Price Type, HE01..HE24`).
   Reading both double-counts the year, and the monthly schema is not what the
   parser expects. Only the standard daily family is read.

2. PRICE starts at 2017, not 2016. The 2016 zip holds two naming families and
   only 184 of its 366 days appear as `DA-LMP-SL-YYYYMMDD0100.csv`; the rest are
   `DAMKT-LMP-SL-...-R1-RC4.csv` revision files. Rather than mix families or
   accept a half-covered year in the horse race, 2016 price is excluded. LOAD
   still starts 2016, so the load trend keeps the full span; the 2016 rows simply
   carry no price and are dropped by the regression's own dropna. The locked
   common-overlap headline window (2023-01 -> 2025-05) is unaffected.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.spp_features import (
    TIME, ZONES, gmt_hour_ending_to_local_beginning, monthly_members,
    parse_wide_load, zone_price_from_nodal,
)

RAW = Path("data/raw/spp")
PANEL = Path("data/interim/spp_diagnostic_panel.parquet")
FIGDIR = Path("outputs/spp_diagnostic")
MAX_START = pd.Timestamp("2016-01-01")
PRICE_START_YEAR = 2017  # see finding 2 in the module docstring
MAX_END = pd.Timestamp("2026-03-24")  # exclusive; last full WIDE day is 2026-03-23
PRICE_COLS = [f"da_lmp_{z}" for z in ZONES]

# The standard daily price family. Excludes the wide monthly rollups and the
# 2016 DAMKT revision files, both of which live in the same archives.
_PRICE_DAILY = re.compile(r"By_Day/DA-LMP-SL-\d{8}0100\.csv$")


def _read_csv_bytes(payload: bytes) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(payload.decode("utf-8", "replace")))


def load_panel() -> pd.DataFrame:
    frames = []
    for archive in sorted((RAW / "load" / "zips").glob("*.zip")):
        with zipfile.ZipFile(archive) as zf:
            for member in monthly_members(zf.namelist()):
                frames.append(parse_wide_load(_read_csv_bytes(zf.read(member))))
    for daily in sorted((RAW / "load" / "daily").glob("DAILY_HOURLY_LOAD-*.csv")):
        # The wide->long schema break lands ON 2026-03-24, not after it: that
        # file is the first long/20-zone day, and 2026-03-23 is the last wide
        # one. Files at or past MAX_END are outside the locked 17-zone panel and
        # would fail parse_wide_load, so they are skipped by date here rather
        # than parsed and discarded later.
        day = pd.Timestamp(daily.stem.rsplit("-", 1)[-1])
        if day >= MAX_END:
            continue
        frames.append(parse_wide_load(_read_csv_bytes(daily.read_bytes())))
    if not frames:
        raise RuntimeError(f"no load files under {RAW / 'load'}")
    return pd.concat(frames, ignore_index=True)


def _zone_prices(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    nodal = pd.DataFrame(
        {
            TIME: gmt_hour_ending_to_local_beginning(frame["GMTIntervalEnd"]),
            "location": frame["Settlement Location"],
            "lmp": pd.to_numeric(frame["LMP"], errors="coerce"),
        }
    )
    return zone_price_from_nodal(nodal, ZONES)


def price_panel() -> pd.DataFrame:
    """Aggregate nodal LMP to zone means one file at a time.

    The per-file nodal frames are never retained - only their zone means are.
    """
    frames = []
    for archive in sorted((RAW / "price" / "zips").glob("*.zip")):
        if int(archive.stem) < PRICE_START_YEAR:
            print(f"  skipping {archive.name} (pre-{PRICE_START_YEAR})", flush=True)
            continue
        with zipfile.ZipFile(archive) as zf:
            members = sorted(n for n in zf.namelist() if _PRICE_DAILY.search(n))
            print(f"  {archive.name}: {len(members)} daily members", flush=True)
            for member in members:
                frames.append(_zone_prices(_read_csv_bytes(zf.read(member))))
    dailies = sorted((RAW / "price" / "daily").glob("DA-LMP-SL-*.csv"))
    print(f"  standalone dailies: {len(dailies)}", flush=True)
    for daily in dailies:
        frames.append(_zone_prices(_read_csv_bytes(daily.read_bytes())))
    if not frames:
        raise RuntimeError(f"no price files under {RAW / 'price'}")
    return pd.concat(frames, ignore_index=True)


def build() -> pd.DataFrame:
    panel = load_panel().sort_values(TIME, kind="mergesort")
    panel = panel[(panel[TIME] >= MAX_START) & (panel[TIME] < MAX_END)]
    panel = panel.reset_index(drop=True)

    # SPP's published load has a handful of genuinely missing hours (verified
    # 2026-08-10: 9 rows in 89,618, at 2017-09-27, six hours on 2018-12-12,
    # 2022-12-20 and 2025-01-22; no row is missing every zone, so this is a
    # source gap, not a parse failure). They are DROPPED, never interpolated,
    # per the project rule - and printed so the count stays visible.
    load_cols = [f"load_mw_{z}" for z in ZONES]
    incomplete = panel[load_cols].isna().any(axis=1)
    if incomplete.any():
        print(f"dropping {int(incomplete.sum())} rows with missing zone load:")
        for stamp in panel.loc[incomplete, TIME]:
            print(f"    {stamp}")
        panel = panel[~incomplete].reset_index(drop=True)

    panel["dst_transition_hour"] = panel[TIME].duplicated(keep=False)

    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=1)

    prices = price_panel().drop_duplicates(subset=[TIME])
    before = len(panel)
    panel = panel.merge(prices, on=TIME, how="left", validate="m:1")
    if len(panel) != before:
        raise AssertionError(f"price join changed row count: {before} -> {len(panel)}")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    panel = build()
    data_quality_report(panel, PRICE_COLS, time_col=TIME,
                        window_start=MAX_START, figdir=FIGDIR)
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="SPP")
    for label, start, end in [
        ("max", MAX_START, MAX_END),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, PRICE_COLS, time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="SPP", label=label)
