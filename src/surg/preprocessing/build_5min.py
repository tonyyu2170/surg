"""Joint 5-min analysis panel builder for sub-q1 item #8 (Part A).

Mirrors build.py's structure but at 5-min cadence. The output panel
is consumed unchanged by items #1-4 + #6 analysis modules — column
names match build.py exactly so PNODE_RESPONSES (cluster_mean,
ox, bristers, ashburn_tx1/2, dom_zonal) lookups work without
modification.

Reserves are forward-filled from hourly to 5-min (the
`load_reserve_market_results` loader aggregates 5-min source to
hourly mean; refactoring that loader to expose 5-min granularity is
out of scope for item #8).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.preprocessing.build import (
    LOUDOUN_CLUSTER_IDS,
    ASHBURN_TX1, ASHBURN_TX2,
    CONTROL_OX, CONTROL_BRISTERS,
    DOM_ZONAL,
)
from surg.preprocessing.features import (
    add_load_gradient_columns,
    pivot_lmp_long_to_pnode_columns,
    add_loudoun_cluster_columns,
    add_filter_columns,
)
from surg.preprocessing.loaders import load_reserve_market_results
from surg.preprocessing.loaders_5min import (
    load_rt_lmp_5min,
    load_dom_load_5min,
    forward_fill_reserves_to_5min,
)


_PNODE_FRIENDLY_RENAME: dict[str, str] = {
    f"congestion_price_rt_{ASHBURN_TX1}": "congestion_price_rt_ashburn_tx1",
    f"congestion_price_rt_{ASHBURN_TX2}": "congestion_price_rt_ashburn_tx2",
    f"congestion_price_rt_{CONTROL_OX}":  "congestion_price_rt_ox",
    f"congestion_price_rt_{CONTROL_BRISTERS}": "congestion_price_rt_bristers",
    f"congestion_price_rt_{DOM_ZONAL}":   "congestion_price_rt_dom_zonal",
    f"total_lmp_rt_{ASHBURN_TX1}":        "total_lmp_rt_ashburn_tx1",
    f"total_lmp_rt_{ASHBURN_TX2}":        "total_lmp_rt_ashburn_tx2",
    f"system_energy_price_rt_{ASHBURN_TX1}": "system_energy_price_rt_ashburn_tx1",
    f"system_energy_price_rt_{ASHBURN_TX2}": "system_energy_price_rt_ashburn_tx2",
    f"system_energy_price_rt_{CONTROL_OX}":  "system_energy_price_rt_ox",
    f"system_energy_price_rt_{CONTROL_BRISTERS}": "system_energy_price_rt_bristers",
    f"system_energy_price_rt_{DOM_ZONAL}":   "system_energy_price_rt_dom_zonal",
    f"marginal_loss_price_rt_{ASHBURN_TX1}": "marginal_loss_price_rt_ashburn_tx1",
    f"marginal_loss_price_rt_{ASHBURN_TX2}": "marginal_loss_price_rt_ashburn_tx2",
    f"marginal_loss_price_rt_{CONTROL_OX}":  "marginal_loss_price_rt_ox",
    f"marginal_loss_price_rt_{CONTROL_BRISTERS}": "marginal_loss_price_rt_bristers",
    f"marginal_loss_price_rt_{DOM_ZONAL}":   "marginal_loss_price_rt_dom_zonal",
}


def build_joint_5min_panel(data_root: Path) -> pd.DataFrame:
    """Build the joint 5-min Z+LMP+reserves analysis panel.

    Returns one row per 5-min stamp in the joint window (intersection
    of LMP and DOM-load timestamp coverage), wide-format LMP per
    pnode + cluster aggregates + DOM-load gradient + forward-filled
    reserves + filter columns.
    """
    lmp_long = load_rt_lmp_5min(data_root)
    dom_load = load_dom_load_5min(data_root)
    hourly_reserves = load_reserve_market_results(data_root)
    if lmp_long.empty or dom_load.empty:
        return pd.DataFrame()

    # LMP: long → wide → cluster + control columns; rename to friendly names
    lmp_wide = pivot_lmp_long_to_pnode_columns(lmp_long)
    lmp_wide = add_loudoun_cluster_columns(lmp_wide, LOUDOUN_CLUSTER_IDS)
    lmp_wide = lmp_wide.rename(columns=_PNODE_FRIENDLY_RENAME)

    # DOM load: compute Z at 5-min cadence
    dom_load = add_load_gradient_columns(dom_load, freq_minutes=5)

    # Joint window = intersection of LMP and DOM-load timestamp coverage
    tmin = max(lmp_wide["datetime_beginning_ept"].min(),
               dom_load["datetime_beginning_ept"].min())
    tmax = min(lmp_wide["datetime_beginning_ept"].max(),
               dom_load["datetime_beginning_ept"].max())
    lmp_wide = lmp_wide[
        (lmp_wide["datetime_beginning_ept"] >= tmin)
        & (lmp_wide["datetime_beginning_ept"] <= tmax)
    ].copy()
    dom_load = dom_load[
        (dom_load["datetime_beginning_ept"] >= tmin)
        & (dom_load["datetime_beginning_ept"] <= tmax)
    ].copy()

    # Spine: dom_load (every 5-min stamp with a Z value); inner-merge
    # LMP so we keep only stamps where both sides are present.
    panel = dom_load.merge(
        lmp_wide, on="datetime_beginning_ept", how="inner"
    )

    # Forward-fill reserves to 5-min on the panel's timestamp index
    target_index = pd.DatetimeIndex(
        panel["datetime_beginning_ept"].drop_duplicates().sort_values()
    )
    reserves_5min = forward_fill_reserves_to_5min(
        hourly_reserves, target_index
    )
    panel = panel.merge(reserves_5min, on="datetime_beginning_ept", how="left")

    # Filter columns (cadence-independent: depends on month/hour only)
    panel = add_filter_columns(panel)

    # Schema-required event columns. The 5-min joint window is too short
    # for sync_reserve_events analysis to be meaningful, but the schema
    # validator and downstream code expect the columns. Stub them with
    # event-inactive defaults; if a future Part A run wants real event
    # data, plumb load_sync_reserve_events + add_sync_event_columns in.
    panel["sync_reserve_event_active"] = False
    panel["sync_reserve_event_id"] = pd.NA
    panel["hours_to_next_sync_event"] = pd.NA
    panel["hours_since_last_sync_event"] = pd.NA

    return panel.sort_values("datetime_beginning_ept").reset_index(drop=True)
