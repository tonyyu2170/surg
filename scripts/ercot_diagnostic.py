"""Stage 1 ERCOT load volatility diagnostic.

Answers two questions:
  1. Is ERCOT load volatile, and is its volatility rising?
  2. Does hourly price track load level more than load volatility?

Usage: .venv/bin/python scripts/ercot_diagnostic.py
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from surg.preprocessing.ercot_features import (
    ZONES,
    add_zone_gradient_columns,
    hour_ending_to_beginning,
)

RAW = Path("data/raw/ercot")
PANEL = Path("data/interim/ercot_diagnostic_panel.parquet")
FIGDIR = Path("outputs/ercot_diagnostic")

# ERCOT publishes four load schema families. 2017 is the first year whose zone
# names match ZONES: 2016 uses FAR_WEST/NORTH_C/SOUTHERN/SOUTH_C with a
# `Hour_End` Timestamp, 2015 and earlier are .xls, and pre-April-2003 files use
# 11 control areas rather than 8 weather zones.
FIRST_ZONE_YEAR = 2017
# DOM panel starts 2022-10-02; matched window for the price comparison.
DOM_START = pd.Timestamp("2022-10-02")

# Extracted filenames vary in case across years (`native_load_2017.xlsx`,
# `Native_Load_2019.xlsx`). Matching case-insensitively rather than leaning on
# macOS's case-insensitive filesystem.
LOAD_FILE = re.compile(r"native_load_(\d{4})\.xlsx$", re.I)


def load_native_load() -> pd.DataFrame:
    """Read every native_load_<YYYY>.xlsx into one hour-beginning frame."""
    frames = []
    dropped_total = 0
    for path in sorted(RAW.iterdir()):
        match = LOAD_FILE.match(path.name)
        if not match or int(match.group(1)) < FIRST_ZONE_YEAR:
            continue

        raw = pd.read_excel(path)
        raw = raw.rename(columns={c: c.strip().upper() for c in raw.columns})
        # 2018-2020 spell it `HourEnding`; every other year `Hour Ending`.
        raw = raw.rename(
            columns={"HOUR ENDING": "Hour Ending", "HOURENDING": "Hour Ending"}
        )
        missing = [z for z in ZONES if z not in raw.columns]
        if missing:
            raise ValueError(f"{path.name} missing zones: {missing}")

        keep = raw[["Hour Ending", *ZONES]].copy()

        # Native_Load_2026.xlsx republishes all of May 2026 a second time as a
        # contiguous block of 744 rows identical across every column. Dropping
        # exact duplicates here -- while the raw `Hour Ending` label is still
        # present -- is lossless and cannot touch the DST fall-back pair, whose
        # two rows carry *different* labels (`02:00` vs `02:00 DST`).
        # This must happen before hour_ending_to_beginning: otherwise the
        # repeats are flagged `dst_transition_hour`, and assert_panel_quality
        # (which only inspects non-DST rows) passes over them in silence.
        deduped = keep.drop_duplicates()
        if len(deduped) != len(keep):
            dropped_total += len(keep) - len(deduped)
            print(
                f"  {path.name}: dropped {len(keep) - len(deduped)} exact "
                f"duplicate rows (ERCOT republication)"
            )
        frames.append(deduped)

    if not frames:
        raise RuntimeError(f"no load files matched in {RAW}")
    if dropped_total:
        print(f"  total exact-duplicate rows dropped: {dropped_total}")

    combined = pd.concat(frames, ignore_index=True)
    combined = hour_ending_to_beginning(combined)
    combined = combined.rename(columns={z: f"load_mw_{z}" for z in ZONES})
    return combined.sort_values("datetime_beginning_cpt").reset_index(drop=True)


def assert_panel_quality(panel: pd.DataFrame) -> None:
    """Fail loudly on the failure modes that previously bit this project."""
    non_dst = panel.loc[~panel["dst_transition_hour"], "datetime_beginning_cpt"]
    dupes = non_dst.duplicated().sum()
    if dupes:
        raise AssertionError(f"{dupes} duplicate non-DST timestamps")

    # One fall-back pair per completed year; anything beyond that is a
    # republication like the 2026 May block, not a DST artefact. Without this
    # the check above is vacuous, since duplicates hide inside the DST flag.
    flagged = int(panel["dst_transition_hour"].sum())
    span_years = panel["datetime_beginning_cpt"].dt.year.nunique()
    if flagged > 2 * span_years:
        raise AssertionError(
            f"{flagged} rows flagged dst_transition_hour across {span_years} "
            f"years; expected at most {2 * span_years} (one pair per year)"
        )

    for zone in ZONES:
        col = f"load_mw_{zone}"
        if panel[col].isna().any():
            raise AssertionError(f"{col} contains NaN — do not interpolate, investigate")

    span = panel["datetime_beginning_cpt"]
    expected = int((span.max() - span.min()).total_seconds() // 3600) + 1
    actual = len(panel)
    if abs(expected - actual) > 48:
        raise AssertionError(f"gap detected: expected ~{expected} rows, got {actual}")


def build_panel() -> pd.DataFrame:
    panel = load_native_load()
    panel = add_zone_gradient_columns(panel)
    assert_panel_quality(panel)
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    build_panel()
