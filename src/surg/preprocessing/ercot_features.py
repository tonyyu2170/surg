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

    Three properties of the real archives rule out a plain `strptime`:

    * Hour-ending runs **1-24**, so every day ends `24:00`, which `%H`
      (00-23) rejects. The hour is therefore parsed as an integer and
      applied as an offset rather than as a time-of-day field.
    * The fall-back hour carries a trailing ` DST` suffix (one row per
      year), not a duplicated label.
    * `Native_Load_2022.xlsx` stores one cell as a real `datetime` among
      8,759 strings. A bare `.str` accessor returns NaT on it silently, so
      non-text cells are formatted back to the text shape first.

    `date + (hour - 1)` is correct across the whole 0-24 range: `24:00`
    maps to 23:00 the same day, and an Excel-rolled `00:00` maps back to
    23:00 the previous day.
    """
    if "Hour Ending" not in df.columns:
        raise KeyError("Hour Ending column not found in ERCOT load frame")

    out = df.copy()
    raw = out["Hour Ending"]

    is_text = raw.map(lambda value: isinstance(value, str))
    labels = pd.Series(index=raw.index, dtype=object)
    labels[is_text] = raw[is_text].str.strip()
    if (~is_text).any():
        labels[~is_text] = pd.to_datetime(raw[~is_text]).dt.strftime("%m/%d/%Y %H:%M")

    labels = labels.str.replace(r"\s+DST$", "", regex=True)
    parts = labels.str.split(" ", n=1, expand=True)

    dates = pd.to_datetime(parts[0], format="%m/%d/%Y")
    hours_ending = parts[1].str.slice(0, 2).astype(int)

    out["datetime_beginning_cpt"] = dates + pd.to_timedelta(hours_ending - 1, unit="h")
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
