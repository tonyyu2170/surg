"""LMP-components conditional-Z decomposition (sub-q1 closure item #2).

Median-split conditional-Z test applied to three LMP components separately
(system_energy, congestion, marginal_loss). Singular headline test
pre-registered in docs/decisions.md § 2026-05-14. Other component / pnode /
threshold combinations are descriptive supplementary.

Reuses gpd.gpd_quantile_split_on_z with split_quantiles=(0.5,) for the
binary median split.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.gpd import gpd_quantile_split_on_z


# Rule 4 in the pre-reg: any test with n_exc/half < 50 reports insufficient.
N_PER_HALF_FLOOR = 50


@dataclass(frozen=True, slots=True)
class ComponentsHeadlineResult:
    """Single median-split conditional-Z result on one LMP component.

    `rule_2_outcome` is one of:
      - "cancellation_supported"      (shape_diff > 0, CI excludes 0)
      - "ordc_rejected_broader"       (shape_diff < 0, CI excludes 0)
      - "underpowered_neg_direction"  (CI spans 0, shape_diff < 0)
      - "underpowered_pos_direction"  (CI spans 0, shape_diff >= 0)
      - "insufficient_sample"         (n_per_half < N_PER_HALF_FLOOR)
    """
    component: str
    pnode_label: str
    threshold_quantile: float
    n_exc: int
    shape_diff: float
    shape_diff_ci_95: tuple[float, float]
    rule_2_outcome: str
    paper_claim: str


def outcome_from_shape_diff_ci(
    shape_diff: float,
    ci_95: tuple[float, float],
    *,
    n_per_half: int,
) -> str:
    """Apply the pre-reg's Rule 2 decision table to a (shape_diff, CI, n) triple."""
    if n_per_half < N_PER_HALF_FLOOR:
        return "insufficient_sample"
    lo, hi = ci_95
    ci_excludes_zero = (lo > 0) or (hi < 0)
    if ci_excludes_zero:
        return "cancellation_supported" if shape_diff > 0 else "ordc_rejected_broader"
    return "underpowered_pos_direction" if shape_diff >= 0 else "underpowered_neg_direction"


PAPER_CLAIMS = {
    "cancellation_supported": (
        "Cancellation hypothesis supported: {component} carries the ORDC-predicted "
        "direction (heavier tail at HIGH Z); congestion's opposite-direction effect "
        "cancels it in total_lmp. shape_diff={shape_diff:.3f}, CI [{lo:.3f},{hi:.3f}]."
    ),
    "ordc_rejected_broader": (
        "ORDC-predicted direction rejected for {component} too. shape_diff={shape_diff:.3f}, "
        "CI [{lo:.3f},{hi:.3f}] excludes 0 in the negative direction; heavier-tail-at-LOW-Z "
        "effect is broader than congestion. Mechanism is NOT ORDC-specific."
    ),
    "underpowered_neg_direction": (
        "Underpowered on this scope (n_per_half={n_per_half}): {component} direction "
        "consistent with congestion finding (heavier tail at LOW Z), shape_diff={shape_diff:.3f}, "
        "CI [{lo:.3f},{hi:.3f}] spans 0. Not consistent with ORDC's predicted direction."
    ),
    "underpowered_pos_direction": (
        "Underpowered on this scope (n_per_half={n_per_half}): {component} direction "
        "consistent with ORDC's predicted direction (heavier tail at HIGH Z), "
        "shape_diff={shape_diff:.3f}, CI [{lo:.3f},{hi:.3f}] spans 0. Cannot confirm "
        "at α=0.05."
    ),
    "insufficient_sample": (
        "Insufficient sample: n_per_half={n_per_half} below pre-reg floor of "
        f"{N_PER_HALF_FLOOR}. No verdict reported."
    ),
}


def _format_paper_claim(outcome: str, *, component: str, shape_diff: float,
                        ci_95: tuple[float, float], n_per_half: int) -> str:
    template = PAPER_CLAIMS[outcome]
    return template.format(
        component=component, shape_diff=shape_diff,
        lo=ci_95[0], hi=ci_95[1], n_per_half=n_per_half,
    )


def fit_single_component_median_split(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    component: str,
    pnode_label: str,
    threshold_quantile: float = 0.95,
    n_boot: int = 200,
    seed: int = 0,
    filter_col: str | None = None,
) -> ComponentsHeadlineResult:
    """Median-split conditional-Z test on a single (component, pnode, threshold)."""
    sub = panel.dropna(subset=[response_col, z_col]).copy()
    if filter_col is not None:
        sub = sub[sub[filter_col].fillna(False).astype(bool)].copy()

    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()

    if len(Y) == 0:
        return _insufficient(component, pnode_label, threshold_quantile, n_exc=0, n_per_half=0)

    threshold = float(np.quantile(Y, threshold_quantile))
    n_exc = int((Y > threshold).sum())
    n_per_half = n_exc // 2

    if n_per_half < N_PER_HALF_FLOOR:
        return _insufficient(component, pnode_label, threshold_quantile, n_exc=n_exc,
                             n_per_half=n_per_half)

    result = gpd_quantile_split_on_z(
        Y, Z,
        threshold_quantile=threshold_quantile,
        split_quantiles=(0.5,),
        n_boot=n_boot,
        seed=seed,
    )
    shape_diff = float(result.extreme_contrast)
    ci_95 = (
        float(result.extreme_contrast_bootstrap_ci_95[0]),
        float(result.extreme_contrast_bootstrap_ci_95[1]),
    )
    outcome = outcome_from_shape_diff_ci(shape_diff, ci_95, n_per_half=n_per_half)
    claim = _format_paper_claim(outcome, component=component, shape_diff=shape_diff,
                                ci_95=ci_95, n_per_half=n_per_half)
    return ComponentsHeadlineResult(
        component=component,
        pnode_label=pnode_label,
        threshold_quantile=threshold_quantile,
        n_exc=n_exc,
        shape_diff=shape_diff,
        shape_diff_ci_95=ci_95,
        rule_2_outcome=outcome,
        paper_claim=claim,
    )


def _insufficient(
    component: str, pnode_label: str, threshold_quantile: float,
    *, n_exc: int, n_per_half: int,
) -> ComponentsHeadlineResult:
    outcome = "insufficient_sample"
    return ComponentsHeadlineResult(
        component=component,
        pnode_label=pnode_label,
        threshold_quantile=threshold_quantile,
        n_exc=n_exc,
        shape_diff=float("nan"),
        shape_diff_ci_95=(float("nan"), float("nan")),
        rule_2_outcome=outcome,
        paper_claim=_format_paper_claim(
            outcome, component=component, shape_diff=float("nan"),
            ci_95=(float("nan"), float("nan")), n_per_half=n_per_half,
        ),
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

# Per-pnode response-column templates per component. Labeled pnodes only.
LABELED_PNODES = ("ashburn_tx1", "ashburn_tx2", "ox", "bristers", "dom_zonal")
CLUSTER_RESPONSE_COLS = {
    "system_energy": "system_energy_price_rt_cluster_mean",
    "congestion":    "congestion_price_rt_cluster_mean",
    "marginal_loss": "marginal_loss_price_rt_cluster_mean",
}
CROSS_PNODE_RESPONSE_COLS = {
    "system_energy": {p: f"system_energy_price_rt_{p}" for p in LABELED_PNODES},
    "congestion":    {p: f"congestion_price_rt_{p}"    for p in LABELED_PNODES},
    "marginal_loss": {p: f"marginal_loss_price_rt_{p}" for p in LABELED_PNODES},
}


def _result_to_dict(r: ComponentsHeadlineResult) -> dict:
    return {
        "component": r.component,
        "pnode_label": r.pnode_label,
        "threshold_quantile": r.threshold_quantile,
        "n_exc": r.n_exc,
        "shape_diff": _nan_to_none(r.shape_diff),
        "shape_diff_ci_95": [_nan_to_none(r.shape_diff_ci_95[0]),
                             _nan_to_none(r.shape_diff_ci_95[1])],
        "rule_2_outcome": r.rule_2_outcome,
        "paper_claim": r.paper_claim,
    }


def _nan_to_none(x: float) -> float | None:
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return x


def run_gpd_components(
    panel: pd.DataFrame,
    out_dir: Path,
    *,
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    filter_col: str = "passes_proposal_filter",
    headline_threshold_q: float = 0.95,
    threshold_sweep_qs: tuple[float, ...] = (0.90, 0.95, 0.99),
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """End-to-end orchestrator for sub-q1 closure item #2.

    Writes four JSON files under `out_dir`:
      - headline.json: system_energy @ headline_threshold_q on primary cluster.
      - primary_cluster_supplementary.json: congestion + marginal_loss on primary cluster.
      - cross_pnode.json: 3 components × 5 labeled pnodes × headline_threshold_q.
      - threshold_sweep.json: 3 components × primary cluster × threshold_sweep_qs.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Headline: system_energy @ p95 on primary cluster.
    headline = fit_single_component_median_split(
        panel=panel,
        response_col=CLUSTER_RESPONSE_COLS["system_energy"],
        z_col=z_col,
        component="system_energy",
        pnode_label="primary_cluster",
        threshold_quantile=headline_threshold_q,
        n_boot=n_boot,
        seed=seed,
        filter_col=filter_col,
    )
    headline_payload = _result_to_dict(headline)
    headline_payload["rule_1_singular_headline"] = (
        f"system_energy_price_rt_cluster_mean median-split @ "
        f"p{int(headline_threshold_q*100)} LMP, Loudoun cluster, filtered subset"
    )
    headline_payload["pre_reg_reference"] = (
        "docs/decisions.md § 2026-05-14 — Pre-registration: LMP-components decomposition"
    )
    (out_dir / "headline.json").write_text(json.dumps(headline_payload, indent=2))

    # Primary cluster supplementary: congestion + marginal_loss @ p95.
    primary_supp = []
    for comp in ("congestion", "marginal_loss"):
        r = fit_single_component_median_split(
            panel=panel,
            response_col=CLUSTER_RESPONSE_COLS[comp],
            z_col=z_col,
            component=comp,
            pnode_label="primary_cluster",
            threshold_quantile=headline_threshold_q,
            n_boot=n_boot,
            seed=seed + 1,
            filter_col=filter_col,
        )
        primary_supp.append(_result_to_dict(r))
    (out_dir / "primary_cluster_supplementary.json").write_text(
        json.dumps({"results": primary_supp, "scope": "descriptive (no MT correction)"}, indent=2)
    )

    # Cross-pnode: 3 components × 5 labeled pnodes @ p95.
    cross_pnode_results = []
    seed_idx = 2
    for comp in ("system_energy", "congestion", "marginal_loss"):
        for label, col in CROSS_PNODE_RESPONSE_COLS[comp].items():
            if col not in panel.columns or panel[col].dropna().empty:
                continue
            r = fit_single_component_median_split(
                panel=panel,
                response_col=col,
                z_col=z_col,
                component=comp,
                pnode_label=label,
                threshold_quantile=headline_threshold_q,
                n_boot=n_boot,
                seed=seed + seed_idx,
                filter_col=filter_col,
            )
            cross_pnode_results.append(_result_to_dict(r))
            seed_idx += 1
    (out_dir / "cross_pnode.json").write_text(
        json.dumps({"results": cross_pnode_results,
                    "scope": "descriptive (no MT correction)"}, indent=2)
    )

    # Threshold sweep: 3 components × primary cluster × multiple thresholds.
    sweep_results = []
    for comp in ("system_energy", "congestion", "marginal_loss"):
        for q in threshold_sweep_qs:
            r = fit_single_component_median_split(
                panel=panel,
                response_col=CLUSTER_RESPONSE_COLS[comp],
                z_col=z_col,
                component=comp,
                pnode_label="primary_cluster",
                threshold_quantile=q,
                n_boot=n_boot,
                seed=seed + seed_idx,
                filter_col=filter_col,
            )
            sweep_results.append(_result_to_dict(r))
            seed_idx += 1
    (out_dir / "threshold_sweep.json").write_text(
        json.dumps({"results": sweep_results,
                    "scope": "descriptive (no MT correction)"}, indent=2)
    )
