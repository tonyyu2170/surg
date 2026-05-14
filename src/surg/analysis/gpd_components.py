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
