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
from surg.analysis.qr_full import run_qr_full
from surg.analysis.gpd import run_gpd, run_conditional_z_robustness
from surg.analysis.gpd_continuous import run_gpd_continuous_z
from surg.analysis.gpd_components import run_gpd_components
from surg.analysis.year_fe_diagnostic import run_year_fe_diagnostic, write_cross_pnode_summary
from surg.analysis.ashburn_diagnostic import run_ashburn_diagnostic
from surg.analysis.tail_risk_curves import run_tail_risk_curves
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
    qr_full_n_boot: int = 200,
    gpd_n_boot: int = 200,
    continuous_n_boot: int = 200,
    components_n_boot: int = 200,
    skip_gpd_components: bool = False,
    year_fe_n_boot: int = 200,
    skip_year_fe_diagnostic: bool = False,
    skip_ashburn_diagnostic: bool = False,
    ashburn_loo_skip: bool = False,
    tail_risk_n_boot: int = 200,
    skip_tail_risk_curves: bool = False,
    tail_risk_loo_skip: bool = False,
) -> None:
    """Run the full Phase 3 analysis pipeline.

    Output layout (per-method subdirectories):
      - outputs/tar/<pnode_label>.json                          (Hansen TAR)
      - outputs/qr/filtered_at_tar_c.json                       (QR at TAR's ĉ, filtered)
      - outputs/qr_full/<pnode_label>.json                      (Strategy C QR-full)
      - outputs/gpd/<pnode_label>.json                          (Strategy C GPD)
      - outputs/mechanism/validation.json
      - outputs/robustness/subsample_bootstrap.parquet
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

    # Strategy C methods: QR-full + GPD per pnode, full panel (no filter)
    for label, col in PNODE_RESPONSES.items():
        if panel[col].dropna().empty:
            continue
        run_qr_full(
            panel=panel,
            out_path=out_root / "qr_full" / f"{label}.json",
            response_col=col,
            pnode_label=label,
            n_boot=qr_full_n_boot,
        )
        run_gpd(
            panel=panel,
            out_path=out_root / "gpd" / f"{label}.json",
            response_col=col,
            pnode_label=label,
            n_boot=gpd_n_boot,
        )

    # 2026-05-14 conditional-Z robustness battery (A/C/F + Holm-Bonferroni).
    # Single battery run on the primary response (cluster total_lmp) where
    # the original median-split rejection was found. Pre-reg:
    # docs/decisions.md § "2026-05-14 — Pre-registration: conditional-Z
    # robustness battery (A/C/F + gated B)".
    run_conditional_z_robustness(
        panel=panel,
        out_path=out_root / "gpd" / "conditional_z_robustness.json",
        response_col=PNODE_RESPONSES["total_lmp"],
        pnode_label="total_lmp",
        n_boot=gpd_n_boot,
    )

    # 2026-05-14 Spec B continuous ξ(Z) regression battery — sub-q1 closure.
    # Per pre-reg: docs/decisions.md § "2026-05-14 — Pre-registration: Spec B".
    for label, col in PNODE_RESPONSES.items():
        if panel[col].dropna().empty:
            continue
        run_gpd_continuous_z(
            panel=panel,
            out_path=out_root / "gpd_continuous" / f"{label}.json",
            response_col=col,
            pnode_label=label,
            n_boot=continuous_n_boot,
        )

    # Headline JSON: primary congestion @ 95th-pct linear β₁ per pre-reg
    _write_spec_b_headline(out_root / "gpd_continuous")

    # Sub-q1 closure item #2: LMP-components decomposition.
    # Pre-reg: docs/decisions.md § 2026-05-14 — Pre-registration: LMP-components decomposition.
    if not skip_gpd_components:
        run_gpd_components(
            panel=panel,
            out_dir=out_root / "gpd_components",
            n_boot=components_n_boot,
        )

    # Sub-q1 closure item #3: τ=0.99 secular sign-flip diagnostic (descriptive).
    if not skip_year_fe_diagnostic:
        pnode_labels_processed: list[str] = []
        for label, col in PNODE_RESPONSES.items():
            if panel[col].dropna().empty:
                continue
            run_year_fe_diagnostic(
                panel=panel,
                out_path=out_root / "year_fe_diagnostic" / f"{label}.json",
                pnode_label=label,
                response_col=col,
                n_boot=year_fe_n_boot,
            )
            pnode_labels_processed.append(label)
        write_cross_pnode_summary(out_root / "year_fe_diagnostic", tuple(pnode_labels_processed))

    # Sub-q1 closure item #4: Ashburn TX1 anomaly diagnostic (descriptive).
    if not skip_ashburn_diagnostic:
        out_subdir = out_root / "ashburn_diagnostic"
        if ashburn_loo_skip and (out_subdir / "tx1_loo.json").exists():
            pass
        else:
            run_ashburn_diagnostic(
                panel=panel,
                out_dir=out_subdir,
                spec_b_results_dir=out_root / "gpd_continuous",
            )

    # Sub-q1 closure item #6: direct Z → LMP tail-risk characterization.
    if not skip_tail_risk_curves:
        if tail_risk_loo_skip and (out_root / "tail_risk_curves" / "primary.json").exists():
            print("tail_risk_curves outputs exist; skipping (--tail-risk-loo-skip).")
        else:
            print("Running tail_risk_curves (sub-q1 item #6)...")
            run_tail_risk_curves(
                panel=panel,
                out_root=out_root,
                n_boot=tail_risk_n_boot,
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
    p.add_argument("--qr-full-n-boot", type=int, default=200,
                   help="Bootstrap reps for QR-full slope CI.")
    p.add_argument("--gpd-n-boot", type=int, default=200,
                   help="Bootstrap reps for GPD shape CI and conditional p-value.")
    p.add_argument("--continuous-n-boot", type=int, default=200,
                   help="Bootstrap reps for Spec B continuous ξ(Z) regression.")
    p.add_argument("--components-n-boot", type=int, default=200,
                   help="Bootstrap reps for sub-q1 item #2 LMP-components decomposition.")
    p.add_argument("--skip-gpd-components", action="store_true",
                   help="Skip sub-q1 item #2 (gpd_components) orchestrator.")
    p.add_argument("--year-fe-n-boot", type=int, default=200,
                   help="Bootstrap reps for sub-q1 item #3 year-FE secular diagnostic.")
    p.add_argument("--skip-year-fe-diagnostic", action="store_true",
                   help="Skip sub-q1 item #3 (year_fe_diagnostic) orchestrator.")
    p.add_argument("--skip-ashburn-diagnostic", action="store_true",
                   help="Skip sub-q1 item #4 (ashburn_diagnostic) orchestrator.")
    p.add_argument("--ashburn-loo-skip", action="store_true",
                   help="Soft idempotency: skip ashburn LOO if outputs already exist.")
    p.add_argument("--tail-risk-n-boot", type=int, default=200,
                   help="Bootstrap reps for sub-q1 item #6 (tail_risk_curves) CIs.")
    p.add_argument("--skip-tail-risk-curves", action="store_true",
                   help="Skip sub-q1 item #6 (tail_risk_curves) orchestrator.")
    p.add_argument("--tail-risk-loo-skip", action="store_true",
                   help="Soft idempotency: skip tail_risk_curves if output already exists.")
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
        qr_full_n_boot=args.qr_full_n_boot,
        gpd_n_boot=args.gpd_n_boot,
        continuous_n_boot=args.continuous_n_boot,
        components_n_boot=args.components_n_boot,
        skip_gpd_components=args.skip_gpd_components,
        year_fe_n_boot=args.year_fe_n_boot,
        skip_year_fe_diagnostic=args.skip_year_fe_diagnostic,
        skip_ashburn_diagnostic=args.skip_ashburn_diagnostic,
        ashburn_loo_skip=args.ashburn_loo_skip,
        tail_risk_n_boot=args.tail_risk_n_boot,
        skip_tail_risk_curves=args.skip_tail_risk_curves,
        tail_risk_loo_skip=args.tail_risk_loo_skip,
    )
    print(f"wrote analysis outputs to {args.out_root}/")
    return 0


def _write_spec_b_headline(gpd_continuous_dir: Path) -> None:
    """Emit the Spec B headline JSON consolidating primary congestion @ 95th-pct
    linear β₁ per the 2026-05-14 Spec B pre-reg."""
    import json
    primary_path = gpd_continuous_dir / "primary.json"
    if not primary_path.exists():
        return
    payload = json.loads(primary_path.read_text())
    # Find the 95th-pct entry
    entry_95 = next(
        (e for e in payload["threshold_sweep"]
         if abs(e["threshold_quantile"] - 0.95) < 1e-6),
        None,
    )
    if entry_95 is None or entry_95["linear"]["convergence_status"] != "converged":
        # Headline cannot be computed; write a minimal record
        headline = {
            "test": "spec_b_primary_95th_linear",
            "convergence_status":
                entry_95["linear"]["convergence_status"] if entry_95 else "missing",
            "decision_rule_outcome": "could_not_compute_headline",
        }
    else:
        lin = entry_95["linear"]
        beta_1 = lin["shape_coefficients"][1]
        ci_beta_1 = lin["shape_coefficients_bootstrap_ci_95"][1]
        p = lin["beta_1_two_sided_p_value"]
        if p is None or ci_beta_1 is None or ci_beta_1[0] is None:
            outcome = "underpowered"
        elif ci_beta_1[1] < 0 and beta_1 < 0:
            outcome = "rejection_confirmed_linear"
        elif ci_beta_1[0] > 0 and beta_1 > 0:
            outcome = "contradicts_median_split"
        else:
            outcome = "underpowered"
        headline = {
            "test": "spec_b_primary_95th_linear",
            "response_col": payload["response_col"],
            "pnode_label": "primary",
            "threshold_quantile": 0.95,
            "form": "linear",
            "beta_1": beta_1,
            "beta_1_bootstrap_ci_95": ci_beta_1,
            "beta_1_two_sided_p_value": p,
            "decision_rule_outcome": outcome,
            "pre_reg_reference": (
                "docs/decisions.md § 2026-05-14 — Pre-registration: "
                "Spec B continuous ξ(Z) regression"
            ),
        }
    out = gpd_continuous_dir / "headline.json"
    out.write_text(json.dumps(headline, indent=2))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
