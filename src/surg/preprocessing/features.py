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


def pivot_lmp_long_to_pnode_columns(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot long-format LMP (one row per pnode per hour) to wide.

    Output: one row per `datetime_beginning_ept`, with two columns per
    pnode: `congestion_price_rt_<pnode_id>` and `total_lmp_rt_<pnode_id>`.
    pnode_id is used in the column name (not pnode_name) because the LMP
    feed truncates pnode_name (see docs/pjm-api-constraints.md).
    """
    if long_df.empty:
        return pd.DataFrame({"datetime_beginning_ept": pd.Series(dtype="datetime64[ns]")})

    pivoted = long_df.pivot_table(
        index="datetime_beginning_ept",
        columns="pnode_id",
        values=["congestion_price_rt", "total_lmp_rt"],
    )
    # Flatten the (value, pnode_id) MultiIndex columns to `value_pnodeid` strings
    pivoted.columns = [f"{val}_{pid}" for val, pid in pivoted.columns]
    return pivoted.reset_index()


def add_loudoun_cluster_columns(
    wide_df: pd.DataFrame,
    cluster_pnode_ids: tuple[int, ...],
) -> pd.DataFrame:
    """Add congestion_price_rt_cluster_{mean,max} and total_lmp_rt_cluster_mean.

    cluster_pnode_ids = the 6 Loudoun-area transmission pnodes (see
    docs/decisions.md 2026-05-10 "Lock the 11-pnode target set").
    """
    cong_cols = [f"congestion_price_rt_{pid}" for pid in cluster_pnode_ids
                 if f"congestion_price_rt_{pid}" in wide_df.columns]
    total_cols = [f"total_lmp_rt_{pid}" for pid in cluster_pnode_ids
                  if f"total_lmp_rt_{pid}" in wide_df.columns]

    out = wide_df.copy()
    out["congestion_price_rt_cluster_mean"] = out[cong_cols].mean(axis=1)
    out["congestion_price_rt_cluster_max"] = out[cong_cols].max(axis=1)
    out["total_lmp_rt_cluster_mean"] = out[total_cols].mean(axis=1)
    return out
