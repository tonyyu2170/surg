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
