"""Pure transforms for the ERCOT Stage 1 diagnostic panel.

No I/O. Each function takes a DataFrame and returns a new one.
"""
from __future__ import annotations

import pandas as pd

from surg.preprocessing.features import add_load_gradient_columns

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


def add_zone_gradient_columns(
    df: pd.DataFrame,
    zones: list[str] | None = None,
) -> pd.DataFrame:
    """Add `load_gradient_abs_mw_per_min_<zone>` for each ERCOT zone.

    Delegates to the DOM `add_load_gradient_columns` so the volatility
    measure is provably identical across markets. That function is
    hardcoded to `dom_load_mw` / `datetime_beginning_ept`, so each zone is
    renamed in, computed, and renamed out. `features.py` is not modified.

    `add_load_gradient_columns` computes `.diff()` positionally and assumes
    sorted, evenly-spaced input without enforcing it; an unsorted frame
    would silently produce wrong gradients. That is checked here instead.
    """
    if not df["datetime_beginning_cpt"].is_monotonic_increasing:
        raise ValueError(
            "add_zone_gradient_columns requires sorted, non-decreasing datetime_beginning_cpt"
        )

    zones = list(ZONES) if zones is None else zones
    out = df.copy()

    for zone in zones:
        shim = pd.DataFrame(
            {
                "datetime_beginning_ept": out["datetime_beginning_cpt"],
                "dom_load_mw": out[f"load_mw_{zone}"],
            }
        )
        gradients = add_load_gradient_columns(shim, freq_minutes=60)
        out[f"load_gradient_abs_mw_per_min_{zone}"] = gradients[
            "dom_load_gradient_abs_mw_per_min"
        ].to_numpy()

    return out
