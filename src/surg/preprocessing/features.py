"""Feature engineering: derive volatility, pnode aggregation, event-active.

Each function takes a DataFrame and returns a new DataFrame with the
input columns plus the derived ones. Pure functions, no I/O.
"""
from __future__ import annotations

import pandas as pd

# Value columns that pivot_lmp_long_to_pnode_columns will pivot when present.
# The pivot is best-effort: only columns present in the input long_df are
# included, so legacy callers passing only congestion_price_rt and
# total_lmp_rt still produce a valid (narrower) wide DataFrame.
_VALUE_COLS_PIVOTED = [
    "congestion_price_rt",
    "total_lmp_rt",
    "system_energy_price_rt",
    "marginal_loss_price_rt",
]


def add_load_gradient_columns(
    df: pd.DataFrame,
    freq_minutes: int = 60,
) -> pd.DataFrame:
    """Add period-over-period gradient columns to a DOM-load DataFrame.

    Requires `datetime_beginning_ept` (sorted, evenly spaced at
    `freq_minutes`) and `dom_load_mw`. Default `freq_minutes=60`
    preserves the original hourly behavior; sub-q1 item #8 5-min
    companion uses `freq_minutes=5`.

    Adds (semantics independent of freq_minutes):
    - dom_load_gradient_mw_per_hr: gradient extrapolated to MW/hr
      (= delta * 60 / freq_minutes)
    - dom_load_gradient_signed_mw_per_min: delta / freq_minutes
    - dom_load_gradient_abs_mw_per_min: |delta| / freq_minutes

    First row gets NaN for each (no prior period).
    """
    out = df.copy()
    delta = out["dom_load_mw"].diff(1)
    out["dom_load_gradient_mw_per_hr"] = delta * (60.0 / freq_minutes)
    out["dom_load_gradient_signed_mw_per_min"] = delta / freq_minutes
    out["dom_load_gradient_abs_mw_per_min"] = delta.abs() / freq_minutes
    return out


def pivot_lmp_long_to_pnode_columns(long_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot long-format LMP (one row per pnode per hour) to wide.

    Output: one row per `datetime_beginning_ept`, with up to four columns
    per pnode: `congestion_price_rt_<pnode_id>`, `total_lmp_rt_<pnode_id>`,
    `system_energy_price_rt_<pnode_id>`, and
    `marginal_loss_price_rt_<pnode_id>`.

    The pivot is best-effort: only columns present in `long_df` are pivoted
    (see module-level `_VALUE_COLS_PIVOTED`), so legacy callers passing only
    `congestion_price_rt` and `total_lmp_rt` still receive a valid narrower
    wide DataFrame.

    pnode_id is used in the column name (not pnode_name) because the LMP
    feed truncates pnode_name (see docs/pjm-api-constraints.md).
    """
    if long_df.empty:
        return pd.DataFrame({"datetime_beginning_ept": pd.Series(dtype="datetime64[ns]")})

    value_cols = [c for c in _VALUE_COLS_PIVOTED if c in long_df.columns]
    if not value_cols:
        return pd.DataFrame({"datetime_beginning_ept": pd.Series(dtype="datetime64[ns]")})

    pivoted = long_df.pivot_table(
        index="datetime_beginning_ept",
        columns="pnode_id",
        values=value_cols,
    )
    # Flatten the (value, pnode_id) MultiIndex columns to `value_pnodeid` strings
    pivoted.columns = [f"{val}_{pid}" for val, pid in pivoted.columns]
    return pivoted.reset_index()


def add_loudoun_cluster_columns(
    wide_df: pd.DataFrame,
    cluster_pnode_ids: tuple[int, ...],
) -> pd.DataFrame:
    """Add Loudoun-cluster aggregate columns from per-pnode wide columns.

    Adds up to five columns (some may be absent — see below):
    - ``congestion_price_rt_cluster_mean``
    - ``congestion_price_rt_cluster_max``
    - ``total_lmp_rt_cluster_mean``
    - ``system_energy_price_rt_cluster_mean``  (only if at least one matching pnode column is present)
    - ``marginal_loss_price_rt_cluster_mean``  (only if at least one matching pnode column is present)

    Only congestion has a ``_max`` column; the other components have
    ``_mean`` only.

    Column presence in ``wide_df`` is checked defensively per component:
    components whose per-pnode columns are all absent from ``wide_df`` are
    **omitted from the output entirely** — the cluster_mean column for that
    component does not appear. Components with at least one matching per-pnode
    column produce a mean over the available ones (matching the behaviour of
    ``pivot_lmp_long_to_pnode_columns``).

    cluster_pnode_ids = the 6 Loudoun-area transmission pnodes (see
    docs/decisions.md 2026-05-10 "Lock the 11-pnode target set").
    """
    cong_cols = [f"congestion_price_rt_{pid}" for pid in cluster_pnode_ids
                 if f"congestion_price_rt_{pid}" in wide_df.columns]
    total_cols = [f"total_lmp_rt_{pid}" for pid in cluster_pnode_ids
                  if f"total_lmp_rt_{pid}" in wide_df.columns]
    sys_cols = [f"system_energy_price_rt_{pid}" for pid in cluster_pnode_ids
                if f"system_energy_price_rt_{pid}" in wide_df.columns]
    loss_cols = [f"marginal_loss_price_rt_{pid}" for pid in cluster_pnode_ids
                 if f"marginal_loss_price_rt_{pid}" in wide_df.columns]

    out = wide_df.copy()
    out["congestion_price_rt_cluster_mean"] = out[cong_cols].mean(axis=1)
    out["congestion_price_rt_cluster_max"] = out[cong_cols].max(axis=1)
    out["total_lmp_rt_cluster_mean"] = out[total_cols].mean(axis=1)
    if sys_cols:
        out["system_energy_price_rt_cluster_mean"] = out[sys_cols].mean(axis=1)
    if loss_cols:
        out["marginal_loss_price_rt_cluster_mean"] = out[loss_cols].mean(axis=1)
    return out


def add_sync_event_columns(
    panel: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """Add sync_reserve_event_active (bool) and sync_reserve_event_id (int|NaN).

    A panel timestamp `t` (hourly) is "active" if any event overlaps the
    hour bucket [t, t+1h): event_start < t+1h AND event_end > t.
    If active, event_id is set to the earliest such event's id.
    """
    out = panel.copy()
    out["sync_reserve_event_active"] = False
    out["sync_reserve_event_id"] = pd.NA

    if events.empty:
        return out

    one_hour = pd.Timedelta(hours=1)
    # Naive O(n*m) loop; acceptable since events are rare (~10s per year).
    for _, ev in events.iterrows():
        start = ev["event_start_ept"]
        end = ev["event_end_ept"]
        mask = (out["datetime_beginning_ept"] + one_hour > start) & \
               (out["datetime_beginning_ept"] < end)
        # Only set event_id where it hasn't been set yet (first event wins)
        first_set = mask & out["sync_reserve_event_id"].isna()
        out.loc[mask, "sync_reserve_event_active"] = True
        out.loc[first_set, "sync_reserve_event_id"] = ev["event_id"]

    return out


def add_event_lead_lag_columns(
    panel: pd.DataFrame,
    events: pd.DataFrame,
) -> pd.DataFrame:
    """Add hours_to_next_sync_event and hours_since_last_sync_event."""
    out = panel.copy()
    out["hours_to_next_sync_event"] = pd.NA
    out["hours_since_last_sync_event"] = pd.NA

    if events.empty:
        return out

    starts = events["event_start_ept"].sort_values().reset_index(drop=True)
    ends = events["event_end_ept"].sort_values().reset_index(drop=True)

    for i, t in enumerate(out["datetime_beginning_ept"]):
        # next event start strictly after t
        next_idx = starts.searchsorted(t, side="right")
        if next_idx < len(starts):
            delta = (starts.iloc[next_idx] - t).total_seconds() / 3600
            out.loc[out.index[i], "hours_to_next_sync_event"] = delta
        # last event end at or before t
        prev_idx = ends.searchsorted(t, side="right") - 1
        if prev_idx >= 0 and ends.iloc[prev_idx] <= t:
            delta = (t - ends.iloc[prev_idx]).total_seconds() / 3600
            out.loc[out.index[i], "hours_since_last_sync_event"] = delta

    return out


def add_filter_columns(panel: pd.DataFrame) -> pd.DataFrame:
    """Add in_shoulder_season, in_2_5am_window, passes_proposal_filter,
    dst_transition_hour."""
    out = panel.copy()
    months = out["datetime_beginning_ept"].dt.month
    hours = out["datetime_beginning_ept"].dt.hour
    out["in_shoulder_season"] = months.isin([3, 4, 5, 9, 10, 11])
    out["in_2_5am_window"] = hours.isin([2, 3, 4])
    out["passes_proposal_filter"] = out["in_shoulder_season"] & out["in_2_5am_window"]
    # DST transition hour: see test docstring for why this is currently always False.
    out["dst_transition_hour"] = False
    return out
