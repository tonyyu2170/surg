# src/surg/preprocessing/isone_features.py
"""Parse ISO-NE SMD hourly annual workbooks into a Stage-1 panel.

One workbook per year carries load, decomposed DA/RT LMP and weather for all
eight load zones. Verified structure (2016, 2023, 2026 all identical) is
recorded in docs/cross-iso-phase2-recon-verification.md section 2.

Time convention: the workbook is a fixed 24-hour-per-day grid - both DST
transition days carry exactly 24 rows, and a full non-leap year is 8760 rows.
There is therefore no fall-back pair to flag, and drivers must call
assert_panel_quality with dst_pairs_per_year=0.

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


def parse_smd_sheet(raw: pd.DataFrame, zone: str) -> pd.DataFrame:
    """One zone sheet -> [TIME, load_mw_<zone>, da_lmp_<zone>], hour-beginning."""
    hours = pd.to_numeric(raw["Hr_End"], errors="coerce")
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
    return out.sort_values(TIME).reset_index(drop=True)


def build_panel(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merge per-zone sheets on the shared time index.

    Every zone must share an identical time index; a mismatch means one sheet
    is short or misaligned and is raised rather than silently outer-joined.
    """
    panel: pd.DataFrame | None = None
    for zone in ZONES:
        parsed = parse_smd_sheet(frames[zone], zone)
        if panel is None:
            panel = parsed
            continue
        if not parsed[TIME].equals(panel[TIME]):
            raise ValueError(f"{zone}: time index differs from the first zone")
        panel = panel.merge(parsed, on=TIME, how="left", validate="1:1")

    assert panel is not None
    panel["dst_transition_hour"] = False
    return panel.sort_values(TIME).reset_index(drop=True)


def read_workbook(path: Path) -> dict[str, pd.DataFrame]:
    """Read the eight zone sheets from one annual workbook."""
    engine = "xlrd" if path.suffix == ".xls" else "openpyxl"
    book = pd.ExcelFile(path, engine=engine)
    return {zone: book.parse(SHEETS[zone]) for zone in ZONES}
