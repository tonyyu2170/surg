# src/surg/preprocessing/miso_features.py
"""Parse MISO daily load and DA ex-post LMP reports into a Stage-1 panel.

Verified layouts (2023-01-03 and 2025-08-06) are recorded in
docs/cross-iso-phase2-recon-verification.md section 4 and in this plan's Task 6.

Time: MISO publishes fixed EST hour-ending with no DST rows, so drivers pass
dst_pairs_per_year=0 and no fall-back pair is ever flagged.

df_al.xls spans a 7-day reporting period but carries ActualLoad for exactly one
market day; the forecast-only days are dropped rather than interpolated.
"""
from __future__ import annotations

import pandas as pd

TIME = "datetime_beginning_est"
HEADER_ROW = 4

ZONES: list[str] = ["LRZ1", "LRZ2_7", "LRZ3_5", "LRZ4", "LRZ6", "LRZ8_9_10"]


def parse_df_al(raw: pd.DataFrame) -> pd.DataFrame:
    """Header-less read of one df_al workbook -> hour-beginning actual load."""
    header = [str(x).strip() for x in raw.iloc[HEADER_ROW].tolist()]
    frame = raw.iloc[HEADER_ROW + 1:].copy()
    frame.columns = header

    hours = pd.to_numeric(frame["HourEnding"], errors="coerce")
    frame = frame[hours.notna()].copy()
    hours = hours[hours.notna()]
    if not hours.between(1, 24).all():
        raise ValueError("HourEnding outside 1..24")

    days = pd.to_datetime(frame["Market Day"], errors="coerce")
    out = pd.DataFrame({TIME: days + pd.to_timedelta(hours - 1, unit="h")})
    for zone in ZONES:
        col = f"{zone} ActualLoad (MWh)"
        if col not in frame.columns:
            raise ValueError(f"df_al missing column {col!r}")
        out[f"load_mw_{zone}"] = pd.to_numeric(frame[col], errors="coerce")

    load_cols = [f"load_mw_{z}" for z in ZONES]
    out = out[out[load_cols].notna().all(axis=1)]
    out = out.dropna(subset=[TIME]).sort_values(TIME).reset_index(drop=True)
    out["dst_transition_hour"] = False
    return out


def parse_da_expost_lmp(raw: pd.DataFrame, day: pd.Timestamp) -> pd.DataFrame:
    """Header-less read of one da_expost_lmp file -> long [TIME, node, lmp].

    Only `Value == 'LMP'` rows are kept: Stage 1 uses total price, and the MCC
    and MLC rows would otherwise triple every node.
    """
    header = [str(x).strip() for x in raw.iloc[HEADER_ROW].tolist()]
    frame = raw.iloc[HEADER_ROW + 1:].copy()
    frame.columns = header

    for col in ("Node", "Type", "Value"):
        frame[col] = frame[col].astype(str).str.strip()
    frame = frame[frame["Value"] == "LMP"]

    hour_cols = [f"HE {h}" for h in range(1, 25)]
    melted = frame.melt(
        id_vars=["Node", "Type"], value_vars=hour_cols,
        var_name="hour_ending", value_name="lmp",
    )
    hours = melted["hour_ending"].str.removeprefix("HE ").astype(int)
    out = pd.DataFrame(
        {
            TIME: day + pd.to_timedelta(hours - 1, unit="h"),
            "node": melted["Node"],
            "node_type": melted["Type"],
            "lmp": pd.to_numeric(melted["lmp"], errors="coerce"),
        }
    )
    return out.sort_values([TIME, "node"]).reset_index(drop=True)
