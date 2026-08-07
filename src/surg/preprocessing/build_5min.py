"""Orchestrator: build the 5-min analysis panel from gridstatus chunks.

Pipeline: gridstatus chunks -> loaders -> pivot -> cluster aggregates
-> Z (diff/5, NaN-masked at spine gaps) -> EPT derivation -> filter +
island columns -> window-slice -> validate -> atomic write
(schema-stamped parquet).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from surg.preprocessing.build import write_panel
from surg.preprocessing.features import (
    add_filter_columns,
    add_load_gradient_columns,
    add_loudoun_cluster_columns,
    pivot_lmp_long_to_pnode_columns,
)
from surg.preprocessing.loaders_5min import (
    load_gridstatus_dom_load,
    load_gridstatus_lmp_long,
)
from surg.preprocessing.schema_5min import (
    EXPECTED_COLUMNS_5MIN,
    FIVEMIN_CLUSTER_IDS,
    FIVEMIN_SCHEMA_VERSION,
    validate_panel_5min,
)

_EPT_TZ = "America/New_York"


def build_analysis_panel_5min(
    data_root: Path,
    *,
    window_start_utc: pd.Timestamp,
    window_end_utc: pd.Timestamp,
) -> pd.DataFrame:
    """Build the validated 5-min panel for [window_start_utc, window_end_utc)."""
    load_df = load_gridstatus_dom_load(data_root)
    lmp_long = load_gridstatus_lmp_long(data_root)

    lmp_wide = pivot_lmp_long_to_pnode_columns(lmp_long, index_col="interval_start_utc")
    lmp_wide = add_loudoun_cluster_columns(lmp_wide, FIVEMIN_CLUSTER_IDS)

    # Left-join from load (the spine), keyed on the unique UTC interval.
    panel = load_df.merge(lmp_wide, on="interval_start_utc", how="left")
    panel = panel.sort_values("interval_start_utc").reset_index(drop=True)

    # add_load_gradient_columns computes Z via diff(1) against row
    # adjacency, not elapsed wall-clock time — a missing interval would
    # silently produce a spurious extreme Z at the row after the gap.
    # Real-world gaps are confirmed genuine upstream feed gaps, not
    # recoverable via re-pull (docs/gridstatus-api-constraints.md), so
    # gap-adjacent rows are NaN-masked rather than failing the build.
    gap_mask = _gap_adjacent_mask(panel["interval_start_utc"])

    # Z at native 5-min cadence: Z_t = (dom_t - dom_{t-1}) / 5 (design §3).
    panel = add_load_gradient_columns(panel, freq_minutes=5)
    panel.loc[gap_mask, list(_GRADIENT_COLUMNS_5MIN)] = float("nan")

    # EPT derivation for filter/hour/month features. tz-naive like the
    # hourly panel; fall-back duplicates are tolerated because
    # interval_start_utc stays the unique key.
    ept = panel["interval_start_utc"].dt.tz_convert(_EPT_TZ).dt.tz_localize(None)
    panel["datetime_beginning_ept"] = ept

    panel = add_filter_columns(panel)

    # Island id = EPT calendar date as days-since-epoch (the 2-5 AM window
    # never crosses midnight, so one night == one date == one island).
    panel["night_island_id"] = (
        panel["datetime_beginning_ept"].dt.normalize()
        - pd.Timestamp("1970-01-01")
    ).dt.days.astype("int32")

    panel = panel[
        (panel["interval_start_utc"] >= window_start_utc)
        & (panel["interval_start_utc"] < window_end_utc)
    ].reset_index(drop=True)

    validate_panel_5min(panel)
    # Column-select also drops dst_transition_hour (from add_filter_columns):
    # it's not part of EXPECTED_COLUMNS_5MIN.
    return panel[list(EXPECTED_COLUMNS_5MIN)]


_GRADIENT_COLUMNS_5MIN = (
    "dom_load_gradient_mw_per_hr",
    "dom_load_gradient_signed_mw_per_min",
    "dom_load_gradient_abs_mw_per_min",
)


def _gap_adjacent_mask(interval_start_utc: pd.Series) -> pd.Series:
    """True for rows preceded by a spine gap (delta != 5min), where Z would
    otherwise be computed across missing interval(s) rather than one true
    5-min step. The row's own gradient is NaN-masked; other columns (dom,
    LMP) are unaffected."""
    deltas = interval_start_utc.diff()
    return deltas.notna() & deltas.ne(pd.Timedelta(minutes=5))


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-prep-5min",
        description="Build the 5-min analysis panel from gridstatus chunks.",
    )
    p.add_argument("--start", required=True, help="Window start, ISO UTC")
    p.add_argument("--end", required=True, help="Window end (exclusive), ISO UTC")
    p.add_argument("--data-root", default="data/raw/gridstatus")
    p.add_argument("--output", default="data/interim/analysis_panel_5min.parquet")
    p.add_argument("--force", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    out_path = Path(args.output)
    if out_path.exists() and not args.force:
        print(f"{out_path} exists; pass --force to overwrite.", file=sys.stderr)
        return 2
    panel = build_analysis_panel_5min(
        Path(args.data_root),
        window_start_utc=pd.Timestamp(args.start),
        window_end_utc=pd.Timestamp(args.end),
    )
    write_panel(panel, out_path, schema_version=FIVEMIN_SCHEMA_VERSION)
    print(f"wrote {out_path} ({len(panel):,} rows)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
