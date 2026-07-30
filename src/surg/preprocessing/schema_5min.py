"""Versioned schema for the 5-min analysis panel artifact.

Separate from the hourly schema (schema.py): the two panels evolve
independently. Z-column names deliberately match the hourly panel so
analysis-module defaults (threshold_col, Z_COL) work unchanged.
"""
from __future__ import annotations

import pandas as pd

FIVEMIN_SCHEMA_VERSION = 1

FIVEMIN_PNODE_IDS: tuple[int, ...] = (35010365, 35010371, 1356178195)

EXPECTED_COLUMNS_5MIN: tuple[str, ...] = (
    # Keys & metadata
    "interval_start_utc",           # unique key (tz-aware UTC)
    "datetime_beginning_ept",       # derived; DST fall-back rows share stamps
    "in_shoulder_season",
    "in_2_5am_window",
    "passes_proposal_filter",
    "night_island_id",              # days-since-epoch of EPT date; cluster id for island bootstrap
    # Load + Z (names match hourly panel)
    "dom_load_mw",
    "dom_load_gradient_mw_per_hr",
    "dom_load_gradient_abs_mw_per_min",
    "dom_load_gradient_signed_mw_per_min",
    # Per-pnode LMP (4 components x 3 pnodes)
    "congestion_price_rt_35010365",
    "congestion_price_rt_35010371",
    "congestion_price_rt_1356178195",
    "total_lmp_rt_35010365",
    "total_lmp_rt_35010371",
    "total_lmp_rt_1356178195",
    "system_energy_price_rt_35010365",
    "system_energy_price_rt_35010371",
    "system_energy_price_rt_1356178195",
    "marginal_loss_price_rt_35010365",
    "marginal_loss_price_rt_35010371",
    "marginal_loss_price_rt_1356178195",
    # Cluster aggregates (3-pnode cluster — narrower than the hourly 6-pnode cluster)
    "congestion_price_rt_cluster_mean",
    "congestion_price_rt_cluster_max",
    "total_lmp_rt_cluster_mean",
    "system_energy_price_rt_cluster_mean",
    "marginal_loss_price_rt_cluster_mean",
)


def validate_panel_5min(df: pd.DataFrame) -> None:
    """Raise ValueError if df is missing any expected 5-min panel column."""
    missing = set(EXPECTED_COLUMNS_5MIN) - set(df.columns)
    if missing:
        raise ValueError(f"missing expected 5-min panel columns: {sorted(missing)}")
