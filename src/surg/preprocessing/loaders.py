"""Loaders: parquet chunks → tidy DataFrames per feed.

Each loader takes a `data_root` path (default `data/raw`), globs the
feed's chunks, and returns a single DataFrame keyed on its date column
with the data types expected by downstream code.

Empty feed dirs return an empty DataFrame with the expected columns
(not None) so downstream code can chain without null-checking.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_rt_hrl_lmps(data_root: Path) -> pd.DataFrame:
    """Load all rt_hrl_lmps chunks into a long-format DataFrame.

    Columns: datetime_beginning_ept (datetime64), pnode_id (int),
    pnode_name (str), congestion_price_rt (float),
    total_lmp_rt (float), and any extra columns present in the chunks.
    """
    feed_dir = data_root / "rt_hrl_lmps"
    expected_cols = [
        "datetime_beginning_ept", "pnode_id", "pnode_name",
        "congestion_price_rt", "total_lmp_rt",
    ]
    if not feed_dir.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in expected_cols})

    chunks = sorted(feed_dir.rglob("*.parquet"))
    if not chunks:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in expected_cols})

    dfs = [pd.read_parquet(p) for p in chunks]
    df = pd.concat(dfs, ignore_index=True)

    # Parse the EPT timestamp string to pandas datetime
    df["datetime_beginning_ept"] = pd.to_datetime(
        df["datetime_beginning_ept"], errors="raise"
    )
    # Cast pnode_id to int (it should already be, but be defensive)
    df["pnode_id"] = df["pnode_id"].astype("int64")

    return df.sort_values("datetime_beginning_ept").reset_index(drop=True)


def load_dom_load(data_root: Path) -> pd.DataFrame:
    """Load DOM-zone metered hourly load.

    Returns: DataFrame with columns datetime_beginning_ept (datetime64),
    dom_load_mw (float). Sorted ascending by timestamp.
    Defensively filters to zone == 'DOM' even though acquisition
    already filters at the API level.
    """
    feed_dir = data_root / "hrl_load_metered"
    out_cols = ["datetime_beginning_ept", "dom_load_mw"]
    if not feed_dir.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    chunks = sorted(feed_dir.rglob("*.parquet"))
    if not chunks:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    dfs = [pd.read_parquet(p) for p in chunks]
    df = pd.concat(dfs, ignore_index=True)

    # Defensive filter to DOM zone
    df = df[df["zone"] == "DOM"].copy()

    df["datetime_beginning_ept"] = pd.to_datetime(
        df["datetime_beginning_ept"], errors="raise"
    )
    df = df.rename(columns={"mw": "dom_load_mw"})

    return df[out_cols].sort_values("datetime_beginning_ept").reset_index(drop=True)


def load_sync_reserve_events(data_root: Path) -> pd.DataFrame:
    """Load sync_reserve_events for the MAD sub-zone.

    Returns: DataFrame with columns event_start_ept, event_end_ept
    (both datetime64), duration (str), synchronized_sub_zone (str),
    event_id (int, zero-indexed by sort order). Sorted by event_start_ept.
    """
    feed_dir = data_root / "sync_reserve_events"
    out_cols = ["event_start_ept", "event_end_ept", "duration",
                "synchronized_sub_zone", "event_id"]
    if not feed_dir.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    chunks = sorted(feed_dir.rglob("*.parquet"))
    if not chunks:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    dfs = [pd.read_parquet(p) for p in chunks]
    df = pd.concat(dfs, ignore_index=True)

    df["event_start_ept"] = pd.to_datetime(df["event_start_ept"], errors="raise")
    df["event_end_ept"] = pd.to_datetime(df["event_end_ept"], errors="raise")
    df = df.sort_values("event_start_ept").reset_index(drop=True)
    df["event_id"] = df.index.astype("int64")

    keep = [c for c in out_cols if c in df.columns]
    return df[keep]


def load_reserve_market_results(data_root: Path) -> pd.DataFrame:
    """Load reserve_market_results for locale=MAD, services SR + PR.

    Aggregates 5-min granularity to hourly mean per service. Returns:
    DataFrame with columns datetime_beginning_ept (datetime64, hourly),
    sync_reserve_clearing_price_rt (float, NaN if no SR rows that hour),
    primary_reserve_clearing_price_rt (float, NaN if no PR rows that hour).
    """
    feed_dir = data_root / "reserve_market_results"
    out_cols = [
        "datetime_beginning_ept",
        "sync_reserve_clearing_price_rt",
        "primary_reserve_clearing_price_rt",
    ]
    if not feed_dir.exists():
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    chunks = sorted(feed_dir.rglob("*.parquet"))
    if not chunks:
        return pd.DataFrame({c: pd.Series(dtype=object) for c in out_cols})

    dfs = [pd.read_parquet(p) for p in chunks]
    df = pd.concat(dfs, ignore_index=True)

    df["datetime_beginning_ept"] = pd.to_datetime(
        df["datetime_beginning_ept"], errors="raise"
    )

    # Filter to MAD locale and SR/PR services
    df = df[(df["locale"] == "MAD") & (df["service"].isin(["SR", "PR"]))]

    # Floor the 5-min timestamps to the hour
    df = df.assign(_hour=df["datetime_beginning_ept"].dt.floor("h"))

    # Mean mcp per (hour, service); then pivot to two columns
    agg = (
        df.groupby(["_hour", "service"], as_index=False)["mcp"]
        .mean()
        .pivot(index="_hour", columns="service", values="mcp")
        .reset_index()
        .rename(columns={
            "_hour": "datetime_beginning_ept",
            "SR": "sync_reserve_clearing_price_rt",
            "PR": "primary_reserve_clearing_price_rt",
        })
    )
    agg.columns.name = None

    # Ensure both columns exist even if one service had no data
    for col in ("sync_reserve_clearing_price_rt",
                "primary_reserve_clearing_price_rt"):
        if col not in agg.columns:
            agg[col] = pd.NA

    return agg[out_cols].sort_values("datetime_beginning_ept").reset_index(drop=True)
