# src/surg/preprocessing/isone_features.py
"""Parse ISO-NE SMD hourly annual workbooks into a Stage-1 panel.

One workbook per year carries load, decomposed DA/RT LMP and weather for all
eight load zones. Verified against all 11 workbooks on 2026-08-10.

Time convention CHANGES AT 2024:
  * 2016-2023: a fixed 24-hour-per-day grid. Both DST transition days carry 24
    rows, `Hr_End` is int64, and a full non-leap year is 8760 rows.
  * 2024 onward: real local prevailing clock. `Hr_End` is a STRING; the
    fall-back day carries 25 rows with the repeated hour marked `'02X'`
    (2024-11-03, 2025-11-02), and the spring-forward day carries 23 rows with
    hour 2 absent (2024-03-10, 2025-03-09, 2026-03-08).

`'02X'` maps to hour 2, which makes the fall-back pair a genuine duplicate
timestamp; both rows are flagged via `dst_transition_hour`. Drivers therefore
pass dst_pairs_per_year=1 - an upper bound the zero-pair years 2016-2023 also
satisfy.

The Phase-1 recon sampled 2016, 2023 and 2026 only, and the 2026 workbook stops
at 2026-06-30 so it never reached a November fall-back. That sampling gap is why
the first version of this module asserted a uniform fixed grid and crashed on
the 2024 workbook.

Load is RT_Demand (metered actual), not DA_Demand (day-ahead cleared).
Stage 1 uses the total DA_LMP only; the decomposition columns are left in the
workbook for any later work.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

TIME = "datetime_beginning_ept"

SHEETS: dict[str, str] = {
    "me": "ME",
    "nh": "NH",
    "vt": "VT",
    "ct": "CT",
    "ri": "RI",
    "sema": "SEMA",
    "wcma": "WCMA",
    "nema": "NEMA",
}
ZONES: list[str] = list(SHEETS)


def parse_hour_ending(values: pd.Series) -> pd.Series:
    """`Hr_End` -> int 1..24, mapping the post-2024 repeated-hour marker.

    From 2024 the column is a string and the second occurrence of the
    fall-back hour is written `'02X'`. Stripping the suffix maps it to hour 2,
    which is what makes the pair a duplicate timestamp downstream.
    """
    text = values.astype(str).str.strip().str.upper()
    return pd.to_numeric(text.str.removesuffix("X"), errors="coerce")


def parse_smd_sheet(raw: pd.DataFrame, zone: str) -> pd.DataFrame:
    """One zone sheet -> [TIME, load_mw_<zone>, da_lmp_<zone>], hour-beginning."""
    hours = parse_hour_ending(raw["Hr_End"])
    if not hours.between(1, 24).all():
        raise ValueError(f"{zone}: Hr_End outside 1..24")

    dates = pd.to_datetime(raw["Date"])
    out = pd.DataFrame(
        {
            TIME: dates + pd.to_timedelta(hours - 1, unit="h"),
            f"load_mw_{zone}": pd.to_numeric(raw["RT_Demand"], errors="coerce"),
            f"da_lmp_{zone}": pd.to_numeric(raw["DA_LMP"], errors="coerce"),
        }
    )
    # mergesort is stable, so the 02 / 02X pair keeps its published order.
    return out.sort_values(TIME, kind="mergesort").reset_index(drop=True)


def build_panel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Assemble per-zone sheets positionally onto one shared time index.

    Assembly is positional rather than a merge on TIME: from 2024 the fall-back
    hour is a genuine duplicate timestamp, and a key-based merge would fan those
    rows out combinatorially. Every zone must present an identical time index;
    a mismatch means a sheet is short or misaligned and is raised rather than
    silently aligned.
    """
    parsed = {zone: parse_smd_sheet(frames[zone], zone) for zone in ZONES}
    base = parsed[ZONES[0]][TIME]

    panel = pd.DataFrame({TIME: base})
    for zone in ZONES:
        frame = parsed[zone]
        if not frame[TIME].equals(base):
            raise ValueError(f"{zone}: time index differs from the first zone")
        panel[f"load_mw_{zone}"] = frame[f"load_mw_{zone}"].to_numpy()
        panel[f"da_lmp_{zone}"] = frame[f"da_lmp_{zone}"].to_numpy()

    panel["dst_transition_hour"] = panel[TIME].duplicated(keep=False)
    return panel


def read_workbook(path: Path) -> dict[str, pd.DataFrame]:
    """Read the eight zone sheets from one annual workbook."""
    engine = "xlrd" if path.suffix == ".xls" else "openpyxl"
    book = pd.ExcelFile(path, engine=engine)
    return {zone: book.parse(SHEETS[zone]) for zone in ZONES}
