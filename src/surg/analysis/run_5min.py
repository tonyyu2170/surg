"""5-min companion analysis orchestrator (design §3).

Three pre-registered replications on the 5-min two-sided panel:
  1. QR-full z_slope at tau in {0.90, 0.95, 0.99} — full panel,
     5 response labels (3 per-pnode congestion, cluster congestion,
     cluster total_lmp). Same iid pair-bootstrap as the hourly prior
     (comparability); year-FE auto-skips on a 1-year panel via
     run_qr_full's existing guard.
  2. Spec A median-split GPD on cluster congestion — twice:
     full-panel (iid bootstrap; comparator to the hourly -0.18 prior)
     and in-filter (island-cluster bootstrap over ~180 night-islands).
  3. Decile tail-risk curves — in-filter (run_tail_risk_curves applies
     the filter itself), 3 pnodes + cluster.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from surg.analysis.gpd import run_gpd
from surg.analysis.panel import load_panel_5min
from surg.analysis.qr_full import run_qr_full
from surg.analysis.tail_risk_curves import run_tail_risk_curves

FIVEMIN_QR_RESPONSES: dict[str, str] = {
    "loudoun":            "congestion_price_rt_35010365",
    "pleasant_view":      "congestion_price_rt_35010371",
    "goosecre":           "congestion_price_rt_1356178195",
    "cluster":            "congestion_price_rt_cluster_mean",
    "cluster_total_lmp":  "total_lmp_rt_cluster_mean",
}

FIVEMIN_TAIL_RISK_MAP: dict[str, dict[str, str]] = {
    "loudoun": {"congestion": "congestion_price_rt_35010365",
                "total_lmp": "total_lmp_rt_35010365"},
    "pleasant_view": {"congestion": "congestion_price_rt_35010371",
                      "total_lmp": "total_lmp_rt_35010371"},
    "goosecre": {"congestion": "congestion_price_rt_1356178195",
                 "total_lmp": "total_lmp_rt_1356178195"},
    "cluster": {"congestion": "congestion_price_rt_cluster_mean",
                "total_lmp": "total_lmp_rt_cluster_mean"},
}

SPEC_A_RESPONSE = "congestion_price_rt_cluster_mean"


def run_all_5min(
    panel: pd.DataFrame,
    *,
    out_root: Path,
    n_boot: int = 200,
    seed: int = 42,
    taus: tuple[float, ...] = (0.90, 0.95, 0.99),
    qr_n_boot: int | None = None,
) -> None:
    """Run all three pre-registered 5-min replications; write JSON/PNG/CSV."""
    out_root = Path(out_root)
    qr_boot = qr_n_boot if qr_n_boot is not None else n_boot

    # 1. QR-full (full panel; run_qr_full skips year-FE on 1-year panels).
    qr_dir = out_root / "qr_full"
    for i, (label, col) in enumerate(FIVEMIN_QR_RESPONSES.items()):
        run_qr_full(
            panel, qr_dir / f"{label}.json",
            response_col=col, pnode_label=label,
            taus=taus, n_boot=qr_boot, seed=seed + 1000 * i,
        )

    # 2. Spec A — full-panel (iid) + in-filter (island cluster bootstrap).
    # Step offsets below use a 10_000-wide stride (vs. the QR-full loop's
    # 1_000-wide seed + 1000 * i above) so this step's own internal offsets
    # (run_gpd's sweep uses seed..seed+3, conditional uses seed+100; see the
    # matching "disjoint bootstrap streams" comment in gpd.py) can't land on
    # a seed already consumed by the QR-full loop's seed + 1000 * i range
    # (i in 0..4, i.e. seed+0..seed+4021) or by each other.
    gpd_dir = out_root / "gpd"
    run_gpd(
        panel, gpd_dir / "cluster_full_panel.json",
        response_col=SPEC_A_RESPONSE, pnode_label="cluster_full_panel",
        sweep_quantiles=(0.90, 0.95, 0.99, 0.995),
        conditional_threshold_quantile=0.95,
        n_boot=n_boot, seed=seed + 10_000,
    )
    in_filter = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)]
    run_gpd(
        in_filter, gpd_dir / "cluster_in_filter.json",
        response_col=SPEC_A_RESPONSE, pnode_label="cluster_in_filter",
        sweep_quantiles=(0.90, 0.95),
        conditional_threshold_quantile=0.95,
        n_boot=n_boot, seed=seed + 20_000,
        cluster_col="night_island_id",
    )

    # 3. Decile tail-risk curves (module applies the proposal filter itself).
    # run_tail_risk_curves fans this same base seed out to all 4 pnodes
    # (its own internal per-decile/per-threshold offsets keep those disjoint
    # from each other within the step); the +30_000 offset here just keeps
    # that whole block clear of steps 1 and 2 above.
    run_tail_risk_curves(
        panel, out_root=out_root, n_boot=n_boot, seed=seed + 30_000,
        pnode_to_response=FIVEMIN_TAIL_RISK_MAP,
        cross_pnode_pnodes=tuple(FIVEMIN_TAIL_RISK_MAP),
        plotted_pnodes=tuple(FIVEMIN_TAIL_RISK_MAP),
        resolution="5-min",
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="surg-run-5min",
        description="Run the pre-registered 5-min companion analyses.",
    )
    p.add_argument("--panel", default="data/interim/analysis_panel_5min.parquet")
    p.add_argument("--out-root", default="outputs/fivemin")
    p.add_argument("--n-boot", type=int, default=1000,
                   help="Bootstrap reps for GPD + tail-risk (pre-reg: 1000).")
    p.add_argument("--qr-n-boot", type=int, default=500,
                   help="Bootstrap reps for QR-full (pre-reg: 500 — each rep refits on ~105K rows).")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args(argv)

    panel = load_panel_5min(Path(args.panel))
    run_all_5min(
        panel, out_root=Path(args.out_root),
        n_boot=args.n_boot, qr_n_boot=args.qr_n_boot, seed=args.seed,
    )
    print(f"5-min analysis outputs written under {args.out_root}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
