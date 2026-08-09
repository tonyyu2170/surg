"""Tail-risk decile curves on the 5-min panel with NO proposal filter.

The pre-registered 5-min battery ran `tail_risk_curves` in-filter
(shoulder months x 2-5 AM EPT), which left only ~23K of 350K rows and
drove every exceedance probability at $250+ to zero (see the 2026-05-15
item #6 entry: the filter excludes the very events the "crazy LMP"
framing targets). The 2026-07-29 entry dropped that filter as a default
for future analysis. This script is that re-run.

Two passes, because the 2026-07-30 entry established that the extended
panel mixes congestion regimes (p90 by year: $9.56 -> $8.81 -> $13.46
-> $63.56) and that pooled estimates over it are not a constant
estimand:

  1. `pooled/`  - full 3.4-year panel, unfiltered.
  2. `by_year/` - the same curves computed within each calendar year,
     so a pooled result cannot be mistaken for a stationary one.

Z deciles are recomputed within each subset. Absolute dollar thresholds
are held fixed across subsets so the year-over-year comparison is in
the units a reader cares about ("how often does congestion clear $100").

Usage:
    python scripts/run_5min_nofilter.py [--n-boot 1000] [--smoke]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from surg.analysis.panel import load_panel_5min
from surg.analysis.tail_risk_curves import run_tail_risk_curves

# Same 3 pnodes + cluster the pre-registered 5-min battery used.
NOFILTER_TAIL_RISK_MAP: dict[str, dict[str, str]] = {
    "loudoun": {"congestion": "congestion_price_rt_35010365",
                "total_lmp": "total_lmp_rt_35010365"},
    "pleasant_view": {"congestion": "congestion_price_rt_35010371",
                      "total_lmp": "total_lmp_rt_35010371"},
    "goosecre": {"congestion": "congestion_price_rt_1356178195",
                 "total_lmp": "total_lmp_rt_1356178195"},
    "cluster": {"congestion": "congestion_price_rt_cluster_mean",
                "total_lmp": "total_lmp_rt_cluster_mean"},
}

NO_FILTER_COL = "no_filter"


def _unfiltered(panel: pd.DataFrame) -> pd.DataFrame:
    """Add an all-True filter column.

    `run_tail_risk_curves` selects on `panel[filter_col] == True`, so an
    all-True column runs it on the whole panel without touching the
    pre-registered module.
    """
    out = panel.copy()
    out[NO_FILTER_COL] = True
    return out


def _run(panel: pd.DataFrame, out_root: Path, *, n_boot: int, seed: int) -> None:
    run_tail_risk_curves(
        panel, out_root=out_root, n_boot=n_boot, seed=seed,
        pnode_to_response=NOFILTER_TAIL_RISK_MAP,
        cross_pnode_pnodes=tuple(NOFILTER_TAIL_RISK_MAP),
        plotted_pnodes=tuple(NOFILTER_TAIL_RISK_MAP),
        filter_col=NO_FILTER_COL,
        # run_tail_risk_curves defaults resolution to "hourly" and stamps it
        # into every result (tail_risk_curves.py:444, :546). Omitting it here
        # would label this 5-min run as hourly -- the c4a64e7 bug class.
        resolution="5-min",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="run-5min-nofilter")
    p.add_argument("--panel", default="data/interim/analysis_panel_5min.parquet")
    p.add_argument("--out-root", default="outputs/fivemin_nofilter")
    p.add_argument("--n-boot", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--smoke", action="store_true",
                   help="n_boot=30, pooled pass only - wiring check.")
    args = p.parse_args(argv)

    n_boot = 30 if args.smoke else args.n_boot
    out_root = Path(args.out_root)
    panel = _unfiltered(load_panel_5min(Path(args.panel)))
    year = pd.to_datetime(panel["datetime_beginning_ept"]).dt.year

    print(f"panel: {len(panel):,} rows (unfiltered), n_boot={n_boot}", flush=True)

    print("[1/2] pooled, full 3.4-year panel", flush=True)
    _run(panel, out_root / "pooled", n_boot=n_boot, seed=args.seed)

    if args.smoke:
        print("smoke: skipping by_year pass", flush=True)
        return 0

    print("[2/2] by year", flush=True)
    coverage: dict[str, int] = {}
    for yr in sorted(year.unique()):
        sub = panel[year == yr]
        coverage[str(yr)] = int(len(sub))
        print(f"  {yr}: {len(sub):,} rows", flush=True)
        _run(sub, out_root / "by_year" / str(yr),
             n_boot=n_boot, seed=args.seed + 100 * int(yr))

    (out_root / "by_year").mkdir(parents=True, exist_ok=True)
    with open(out_root / "by_year" / "coverage.json", "w") as f:
        json.dump({"rows_per_year": coverage, "n_boot": n_boot,
                   "filter": "none (full panel)"}, f, indent=2)

    print(f"outputs under {out_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
