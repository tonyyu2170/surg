"""Feature engineering: derive volatility, pnode aggregation, event-active.

Each function takes a DataFrame and returns a new DataFrame with the
input columns plus the derived ones. Pure functions, no I/O.
"""
from __future__ import annotations

import pandas as pd


def add_load_gradient_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Add hour-over-hour gradient columns to a DOM-load DataFrame.

    Requires `datetime_beginning_ept` (sorted, hourly) and `dom_load_mw`.
    Adds:
    - dom_load_gradient_mw_per_hr: dom_load_mw.diff(1)
    - dom_load_gradient_signed_mw_per_min: gradient / 60
    - dom_load_gradient_abs_mw_per_min: abs(gradient) / 60

    First row gets NaN for each (no prior hour).
    """
    out = df.copy()
    gradient = out["dom_load_mw"].diff(1)
    out["dom_load_gradient_mw_per_hr"] = gradient
    out["dom_load_gradient_signed_mw_per_min"] = gradient / 60.0
    out["dom_load_gradient_abs_mw_per_min"] = gradient.abs() / 60.0
    return out
