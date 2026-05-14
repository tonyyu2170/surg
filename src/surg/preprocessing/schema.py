"""Versioned schema for the analysis panel artifact.

Bump SCHEMA_VERSION any time EXPECTED_COLUMNS changes. Downstream
analysis modules check the version and refuse to operate on a panel
written under an earlier schema.
"""
from __future__ import annotations

import pandas as pd

SCHEMA_VERSION = 2  # bumped for sub-q1 closure item #2: system_energy + marginal_loss components

EXPECTED_COLUMNS: tuple[str, ...] = (
    # Identifiers & metadata
    "datetime_beginning_ept",
    "in_shoulder_season",
    "in_2_5am_window",
    "passes_proposal_filter",
    "dst_transition_hour",
    # Load + volatility
    "dom_load_mw",
    "dom_load_gradient_mw_per_hr",
    "dom_load_gradient_abs_mw_per_min",
    "dom_load_gradient_signed_mw_per_min",
    # LMP — Loudoun cluster pooled
    "congestion_price_rt_cluster_mean",
    "congestion_price_rt_cluster_max",
    "total_lmp_rt_cluster_mean",
    "system_energy_price_rt_cluster_mean",
    "marginal_loss_price_rt_cluster_mean",
    # LMP — Ashburn distribution (separate fit; total_lmp for item #4 scatter)
    "congestion_price_rt_ashburn_tx1",
    "congestion_price_rt_ashburn_tx2",
    "total_lmp_rt_ashburn_tx1",
    "total_lmp_rt_ashburn_tx2",
    "system_energy_price_rt_ashburn_tx1",
    "system_energy_price_rt_ashburn_tx2",
    "marginal_loss_price_rt_ashburn_tx1",
    "marginal_loss_price_rt_ashburn_tx2",
    # LMP — negative controls
    "congestion_price_rt_ox",
    "congestion_price_rt_bristers",
    "congestion_price_rt_dom_zonal",
    "system_energy_price_rt_ox",
    "system_energy_price_rt_bristers",
    "system_energy_price_rt_dom_zonal",
    "marginal_loss_price_rt_ox",
    "marginal_loss_price_rt_bristers",
    "marginal_loss_price_rt_dom_zonal",
    # Reserves & events
    "sync_reserve_event_active",
    "sync_reserve_event_id",
    "hours_to_next_sync_event",
    "hours_since_last_sync_event",
    "sync_reserve_clearing_price_rt",
    "primary_reserve_clearing_price_rt",
)


def validate_panel(df: pd.DataFrame) -> None:
    """Raise ValueError if df is missing any expected column."""
    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(
            f"missing expected columns: {sorted(missing)}"
        )
