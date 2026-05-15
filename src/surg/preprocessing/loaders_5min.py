"""5-min preprocessing loaders for sub-q1 item #8 companion run.

Mirrors `loaders.py` but at native 5-min granularity. Reserves are
forward-filled from the hourly aggregate (`loaders.load_reserve_market_results`)
because PJM's 5-min reserve loader rewrite is out of scope for item #8.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_rt_lmp_5min(data_root: Path) -> pd.DataFrame:
    """Load all `rt_fivemin_hrl_lmps` parquet files under data_root.

    Returns a DataFrame at native 5-min frequency, sorted +
    deduplicated on (pnode_id, datetime_beginning_ept).
    """
    feed_dir = Path(data_root) / "rt_fivemin_hrl_lmps"
    if not feed_dir.exists():
        return pd.DataFrame()
    files = sorted(feed_dir.rglob("*.parquet"))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df["datetime_beginning_ept"] = pd.to_datetime(
        df["datetime_beginning_ept"], errors="raise"
    )
    df = (
        df.drop_duplicates(subset=["datetime_beginning_ept", "pnode_id"])
          .sort_values(["pnode_id", "datetime_beginning_ept"])
          .reset_index(drop=True)
    )
    return df


def load_dom_load_5min(data_root: Path) -> pd.DataFrame:
    """Load all `inst_load` parquet files; return 5-min PJM SOUTHERN
    REGION instantaneous load (DOM proxy per pjm-api-constraints.md).

    Output columns: `datetime_beginning_ept`, `dom_load_mw`. Sorted,
    deduped on timestamp.
    """
    feed_dir = Path(data_root) / "inst_load"
    if not feed_dir.exists():
        return pd.DataFrame()
    files = sorted(feed_dir.rglob("*.parquet"))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df["datetime_beginning_ept"] = pd.to_datetime(
        df["datetime_beginning_ept"], errors="raise"
    )
    df = df[df["area"] == "PJM SOUTHERN REGION"].copy()
    df = df.rename(columns={"instantaneous_load": "dom_load_mw"})
    df = (
        df[["datetime_beginning_ept", "dom_load_mw"]]
          .drop_duplicates(subset=["datetime_beginning_ept"])
          .sort_values("datetime_beginning_ept")
          .reset_index(drop=True)
    )
    return df


def forward_fill_reserves_to_5min(
    hourly_reserves: pd.DataFrame,
    target_5min_index: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Forward-fill hourly reserve clearing prices to a 5-min target
    index. The hourly value V at hour H applies to all 5-min stamps
    in [H, H+1). Missing hours yield NaN at affected 5-min stamps.
    """
    target_df = pd.DataFrame({"datetime_beginning_ept": target_5min_index})
    target_df["_hour_floor"] = target_df["datetime_beginning_ept"].dt.floor("h")
    hourly_indexed = hourly_reserves.set_index("datetime_beginning_ept")
    target_df["sync_reserve_clearing_price_rt"] = target_df["_hour_floor"].map(
        hourly_indexed["sync_reserve_clearing_price_rt"]
    )
    target_df["primary_reserve_clearing_price_rt"] = target_df["_hour_floor"].map(
        hourly_indexed["primary_reserve_clearing_price_rt"]
    )
    return target_df.drop(columns=["_hour_floor"])
