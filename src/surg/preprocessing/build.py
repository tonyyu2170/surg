"""Orchestrator: build the analysis panel from raw feeds and write atomically.

Compose the loaders + features into a single pipeline:
  raw chunks -> load each feed -> derive features -> join -> filter
              -> atomic write to data/interim/analysis_panel.parquet
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

from surg.preprocessing.loaders import (
    load_rt_hrl_lmps, load_dom_load,
    load_sync_reserve_events, load_reserve_market_results,
)
from surg.preprocessing.features import (
    add_load_gradient_columns,
    pivot_lmp_long_to_pnode_columns,
    add_loudoun_cluster_columns,
    add_sync_event_columns,
    add_event_lead_lag_columns,
    add_filter_columns,
)

# Per-tier pnode IDs from docs/decisions.md (2026-05-10 lock-in).
LOUDOUN_CLUSTER_IDS: tuple[int, ...] = (
    35010365, 35010371, 1356178195, 1356178171, 1356178181, 1356178201,
)
ASHBURN_TX1, ASHBURN_TX2 = 34886139, 34886141
CONTROL_OX, CONTROL_BRISTERS = 35010369, 62871513
DOM_ZONAL = 34964545

# Analysis window (3.6y post-cap). See docs/decisions.md
# "2026-05-12 - Window extension to 3.6y post-cap". Inclusive start,
# exclusive end -> the final included hour is 2026-05-10 23:00 EPT.
ANALYSIS_WINDOW_START = pd.Timestamp("2022-10-02 00:00:00")
ANALYSIS_WINDOW_END = pd.Timestamp("2026-05-11 00:00:00")


def build_analysis_panel(data_root: Path) -> pd.DataFrame:
    """Build the hourly analysis panel from raw feeds under `data_root`.

    Joins LMP (Loudoun cluster + per-pnode controls), DOM zonal load
    (with derived gradient), sync_reserve_events (active flag + lead-lag),
    and reserve_market_results (hourly mean SR/PR clearing prices).
    Applies the shoulder + 2-5 AM filter columns.
    """
    lmp_long = load_rt_hrl_lmps(data_root)
    load_df = load_dom_load(data_root)
    events = load_sync_reserve_events(data_root)
    rmr = load_reserve_market_results(data_root)

    # LMP: long -> wide -> cluster + control columns
    lmp_wide = pivot_lmp_long_to_pnode_columns(lmp_long)
    lmp_wide = add_loudoun_cluster_columns(lmp_wide, LOUDOUN_CLUSTER_IDS)
    rename = {
        f"congestion_price_rt_{ASHBURN_TX1}": "congestion_price_rt_ashburn_tx1",
        f"congestion_price_rt_{ASHBURN_TX2}": "congestion_price_rt_ashburn_tx2",
        f"congestion_price_rt_{CONTROL_OX}":  "congestion_price_rt_ox",
        f"congestion_price_rt_{CONTROL_BRISTERS}": "congestion_price_rt_bristers",
        f"congestion_price_rt_{DOM_ZONAL}":   "congestion_price_rt_dom_zonal",
    }
    lmp_wide = lmp_wide.rename(columns=rename)

    # Load + gradient
    load_df = add_load_gradient_columns(load_df)

    # Left-join from load (the spine): every load hour is kept;
    # any LMP- or RMR-only hours are intentionally dropped.
    panel = load_df.merge(lmp_wide, on="datetime_beginning_ept", how="left")
    panel = panel.merge(rmr, on="datetime_beginning_ept", how="left")

    # Event columns
    panel = add_sync_event_columns(panel, events)
    panel = add_event_lead_lag_columns(panel, events)

    # Filter / metadata columns
    panel = add_filter_columns(panel)

    # Clip to analysis window [ANALYSIS_WINDOW_START, ANALYSIS_WINDOW_END).
    panel = panel[
        (panel["datetime_beginning_ept"] >= ANALYSIS_WINDOW_START)
        & (panel["datetime_beginning_ept"] < ANALYSIS_WINDOW_END)
    ].reset_index(drop=True)

    return panel


def write_panel(panel: pd.DataFrame, out_path: Path) -> None:
    """Atomic write via tmp file + os.replace."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    panel.to_parquet(tmp, index=False)
    os.replace(tmp, out_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-prep",
        description="Build the hourly analysis panel from raw feeds.",
    )
    p.add_argument("--data-root", default="data/raw",
                   help="Root directory of raw parquet chunks.")
    p.add_argument("--output", default="data/interim/analysis_panel.parquet",
                   help="Output path for the analysis panel.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite even if output exists.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    data_root = Path(args.data_root)
    out_path = Path(args.output)

    if out_path.exists() and not args.force:
        print(f"{out_path} exists; pass --force to overwrite.", file=sys.stderr)
        return 2

    panel = build_analysis_panel(data_root=data_root)
    write_panel(panel, out_path)
    print(f"wrote {out_path} ({len(panel):,} rows)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
