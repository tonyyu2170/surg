"""Pure transforms for the ERCOT Stage 1 diagnostic panel.

No I/O. Each function takes a DataFrame and returns a new one.
"""
from __future__ import annotations

import pandas as pd

ZONES = ["COAST", "EAST", "FWEST", "NORTH", "NCENT", "SOUTH", "SCENT", "WEST", "ERCOT"]


def hour_ending_to_beginning(df: pd.DataFrame) -> pd.DataFrame:
    """Convert ERCOT's `Hour Ending` column to hour-beginning `datetime_beginning_cpt`.

    ERCOT labels the hour 00:00-01:00 as "01:00". The DOM panel is
    hour-beginning, so conversion subtracts one hour. Getting this wrong
    produces a silent one-hour misalignment against DOM.

    Duplicate timestamps (DST fall-back) are preserved and flagged in
    `dst_transition_hour` rather than dropped.
    """
    if "Hour Ending" not in df.columns:
        raise KeyError("Hour Ending column not found in ERCOT load frame")

    out = df.copy()
    ending = pd.to_datetime(out["Hour Ending"], format="%m/%d/%Y %H:%M")
    out["datetime_beginning_cpt"] = ending - pd.Timedelta(hours=1)
    out["dst_transition_hour"] = out["datetime_beginning_cpt"].duplicated(keep=False)
    return out.drop(columns=["Hour Ending"])
