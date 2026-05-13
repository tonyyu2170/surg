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


_SECONDARY_RESPONSE_COLS: tuple[str, ...] = (
    # Same Loudoun cluster pooled, but total LMP — cleaner ORDC mechanism test
    # (penalty lands in system energy LMP, not in congestion component directly).
    "total_lmp_rt_cluster_mean",
)

_CONTROL_RESPONSE_COLS: tuple[str, ...] = (
    # Ashburn distribution — separate fit (different physics per
    # decisions.md 2026-05-10 lock-in)
    "congestion_price_rt_ashburn_tx1",
    "congestion_price_rt_ashburn_tx2",
    # Negative controls — outside the Loudoun cluster
    "congestion_price_rt_ox",
    "congestion_price_rt_bristers",
    "congestion_price_rt_dom_zonal",
)


def run_all(
    panel: pd.DataFrame,
    events: pd.DataFrame,
    out_root: Path,
    *,
    n_boot: int = 1000,
    n_subsample_reps: int = 200,
) -> None:
    """Run the full Phase 3 analysis pipeline.

    Produces:
      - tar_fit_primary.json: TAR on the Loudoun cluster mean congestion price
      - tar_fit_<col>.json: TAR on each secondary + control response variable
      - qr_fit.json: quantile regression robustness on the PRIMARY response
      - mechanism_validation.json: dual-regime mechanism JSON
      - robustness/subsample_bootstrap.parquet: subsample c_hat samples
    """
    out_root.mkdir(parents=True, exist_ok=True)

    primary = run_tar(
        panel=panel,
        out_path=out_root / "tar_fit_primary.json",
        response_col="congestion_price_rt_cluster_mean",
        n_boot=n_boot,
    )

    for col in _SECONDARY_RESPONSE_COLS:
        slug = col.replace("_rt_cluster_mean", "").replace("_rt_", "_")
        run_tar(
            panel=panel,
            out_path=out_root / f"tar_fit_{slug}.json",
            response_col=col,
            n_boot=n_boot,
        )

    for col in _CONTROL_RESPONSE_COLS:
        slug = col.replace("congestion_price_rt_", "")
        if panel[col].dropna().empty:
            continue
        run_tar(
            panel=panel,
            out_path=out_root / f"tar_fit_{slug}.json",
            response_col=col,
            n_boot=n_boot,
        )

    run_qr(
        panel=panel,
        out_path=out_root / "qr_fit.json",
        c_for_threshold_dummy=primary.c_hat,
    )

    run_mechanism(
        panel=panel, events=events,
        threshold=primary.c_hat,
        out_path=out_root / "mechanism_validation.json",
    )

    subsample_bootstrap(
        panel=panel,
        out_path=out_root / "robustness" / "subsample_bootstrap.parquet",
        n_reps=n_subsample_reps,
    )


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
