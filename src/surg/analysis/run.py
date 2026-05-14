"""Orchestrator: load panel, run TAR + QR + mechanism + robustness,
write all output artifacts. CLI entry point `surg-analyze`."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from surg.analysis.panel import load_panel
from surg.analysis.tar import run_tar
from surg.analysis.qr import run_qr
from surg.analysis.mechanism import run_mechanism
from surg.analysis.robustness import subsample_bootstrap
from surg.preprocessing.loaders import load_sync_reserve_events


PNODE_RESPONSES: dict[str, str] = {
    # Primary: pooled Loudoun cluster (6 transmission pnodes), congestion price
    "primary":     "congestion_price_rt_cluster_mean",
    # Secondary: same cluster, total LMP (cleaner ORDC mechanism test)
    "total_lmp":   "total_lmp_rt_cluster_mean",
    # Negative controls: outside-cluster transmission pnodes
    "ox":          "congestion_price_rt_ox",
    "bristers":    "congestion_price_rt_bristers",
    "dom_zonal":   "congestion_price_rt_dom_zonal",
    # Complementary primary fits: distribution-level pnodes at Ashburn
    "ashburn_tx1": "congestion_price_rt_ashburn_tx1",
    "ashburn_tx2": "congestion_price_rt_ashburn_tx2",
}


def run_all(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    out_root: Path,
    *,
    n_boot: int = 1000,
    n_subsample_reps: int = 200,
) -> None:
    """Run the full Phase 3 analysis pipeline.

    Output layout (per-method subdirectories):
      - outputs/tar/<pnode_label>.json
      - outputs/qr/filtered_at_tar_c.json   (filtered subset, at TAR's primary c_hat)
      - outputs/mechanism/validation.json
      - outputs/robustness/subsample_bootstrap.parquet

    Future Strategy C methods (qr_full, gpd) wire in here after the existing
    fits land. They are added in subsequent tasks; this function currently
    only covers the reorganization of the existing pipeline.
    """
    out_root.mkdir(parents=True, exist_ok=True)

    primary = run_tar(
        panel=panel,
        out_path=out_root / "tar" / "primary.json",
        response_col=PNODE_RESPONSES["primary"],
        n_boot=n_boot,
    )

    for label, col in PNODE_RESPONSES.items():
        if label == "primary":
            continue
        if panel[col].dropna().empty:
            continue
        run_tar(
            panel=panel,
            out_path=out_root / "tar" / f"{label}.json",
            response_col=col,
            n_boot=n_boot,
        )

    run_qr(
        panel=panel,
        out_path=out_root / "qr" / "filtered_at_tar_c.json",
        c_for_threshold_dummy=primary.c_hat,
    )

    run_mechanism(
        panel=panel,
        events=events,
        threshold=primary.c_hat,
        out_path=out_root / "mechanism" / "validation.json",
    )

    subsample_bootstrap(
        panel=panel,
        out_path=out_root / "robustness" / "subsample_bootstrap.parquet",
        n_reps=n_subsample_reps,
    )

    # Note: leave_one_season_out (robustness.py) is intentionally NOT called
    # from run_all per the plan's "Out of scope" section — the panel does not
    # yet carry an explicit _season_id column. The function remains importable
    # for ad-hoc use once preprocessing adds that column.


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-analyze",
        description="Run TAR + QR + mechanism analysis on the analysis panel.",
    )
    p.add_argument("--panel", default="data/interim/analysis_panel.parquet",
                   help="Path to the analysis panel parquet.")
    p.add_argument("--data-root", default="data/raw",
                   help="Root directory containing sync_reserve_events chunks.")
    p.add_argument("--out-root", default="outputs",
                   help="Output root directory.")
    p.add_argument("--n-boot", type=int, default=1000,
                   help="Number of bootstrap reps for Hansen test + CI.")
    p.add_argument("--n-subsample-reps", type=int, default=200,
                   help="Subsample bootstrap reps for c_hat CI.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    panel_path = Path(args.panel)
    if not panel_path.exists():
        print(f"panel not found: {panel_path}", file=sys.stderr)
        return 2
    panel = load_panel(panel_path)
    events = load_sync_reserve_events(Path(args.data_root))
    run_all(
        panel=panel, events=events,
        out_root=Path(args.out_root),
        n_boot=args.n_boot,
        n_subsample_reps=args.n_subsample_reps,
    )
    print(f"wrote analysis outputs to {args.out_root}/")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
