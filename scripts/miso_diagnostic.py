# scripts/miso_diagnostic.py
"""Stage-1 MISO diagnostic. Usage: .venv/bin/python scripts/miso_diagnostic.py

Window: 2023-01 -> present, bounded by the current+3-calendar-year retention on
docs.misoenergy.org. Fixed EST throughout, so dst_pairs_per_year=0.

ZONE_PRICE_NODES is filled in by Task 9 Step 1 - MISO node names carry no LRZ
code, so the mapping is resolved empirically rather than by prefix. The probe
found no LRZ token or zone digit in any of the 432 Loadzone node names (they
are utility/LSE-prefixed, e.g. AECI.ALTW, ALTW.MRES) and no documented
utility->LRZ crosswalk was available in-scope, so this uses the documented
eight-hub geographic fallback from the plan. Under that fallback, LRZ3_5 and
LRZ4 both map to ILLINOIS.HUB (nearest available hub, not in-zone for either) -
those two cells are therefore not independent.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.miso_features import (
    TIME, ZONES, parse_da_expost_lmp, parse_df_al,
)

RAW = Path("data/raw/miso")
PANEL = Path("data/interim/miso_diagnostic_panel.parquet")
FIGDIR = Path("outputs/miso_diagnostic")
MAX_START = pd.Timestamp("2023-01-01")
MAX_END = pd.Timestamp("2030-01-01")  # open-ended; panel ends at last fetched day
PRICE_COLS = [f"da_lmp_{z}" for z in ZONES]

# Filled in by Task 9 Step 1 - hub fallback (see module docstring for why).
ZONE_PRICE_NODES: dict[str, list[str]] = {
    "LRZ1": ["MINN.HUB"],
    "LRZ2_7": ["MICHIGAN.HUB"],
    "LRZ3_5": ["ILLINOIS.HUB"],
    "LRZ4": ["ILLINOIS.HUB"],
    "LRZ6": ["INDIANA.HUB"],
    "LRZ8_9_10": ["ARKANSAS.HUB", "LOUISIANA.HUB", "MS.HUB", "TEXAS.HUB"],
}


def load_panel() -> pd.DataFrame:
    frames = []
    for path in sorted((RAW / "df_al").glob("*_df_al.xls")):
        raw = pd.ExcelFile(path, engine="xlrd").parse("Sheet1", header=None)
        frames.append(parse_df_al(raw))
    if not frames:
        raise RuntimeError(f"no df_al files under {RAW / 'df_al'}")
    panel = pd.concat(frames, ignore_index=True).sort_values(TIME)
    return panel.drop_duplicates(subset=[TIME], keep="last").reset_index(drop=True)


def price_panel() -> pd.DataFrame:
    if set(ZONE_PRICE_NODES) != set(ZONES):
        raise RuntimeError("ZONE_PRICE_NODES not filled in - see Task 9 Step 1")

    wanted = sorted({node for nodes in ZONE_PRICE_NODES.values() for node in nodes})
    frames = []
    for path in sorted((RAW / "da_expost_lmp").glob("*_da_expost_lmp.csv")):
        day = pd.Timestamp(path.name[:8])
        # header=None + skip_blank_lines=False on the real file needs an explicit
        # column count: the file's preamble rows are jagged (1, 1, 0, 4 fields)
        # before the 27-column header/data rows begin, and pandas' C/python
        # tokenizers both error ("Expected 1 fields ... saw 4") without it. The
        # plan's fixture-based unit tests build `raw` as a rectangular
        # pd.DataFrame directly, so they never exercised this real-file path.
        # 27 is the verified max field count across all 1317 files in the window.
        raw = pd.read_csv(path, header=None, skip_blank_lines=False, names=range(27))
        parsed = parse_da_expost_lmp(raw, day)
        frames.append(parsed[parsed["node"].isin(wanted)])
    if not frames:
        raise RuntimeError(f"no LMP files under {RAW / 'da_expost_lmp'}")

    nodal = pd.concat(frames, ignore_index=True)
    out: pd.DataFrame | None = None
    for zone, nodes in ZONE_PRICE_NODES.items():
        member = nodal[nodal["node"].isin(nodes)]
        mean = member.groupby(TIME)["lmp"].mean().rename(f"da_lmp_{zone}").reset_index()
        out = mean if out is None else out.merge(mean, on=TIME, how="outer")
    assert out is not None
    return out.sort_values(TIME).reset_index(drop=True)


def build() -> pd.DataFrame:
    panel = load_panel()
    panel = panel[panel[TIME] >= MAX_START].reset_index(drop=True)
    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=0)

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
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="MISO")
    for label, start, end in [
        ("max", MAX_START, MAX_END),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, PRICE_COLS, time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="MISO", label=label)
