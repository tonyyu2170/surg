"""Tests for gpd_components.py — sub-q1 closure item #2.

Pre-reg: docs/decisions.md § 2026-05-14 — Pre-registration: LMP-components
decomposition (sub-q1 closure item #2).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from surg.analysis.gpd_components import (
    ComponentsHeadlineResult,
    outcome_from_shape_diff_ci,
)


def test_components_headline_result_fields():
    r = ComponentsHeadlineResult(
        component="system_energy",
        pnode_label="primary_cluster",
        threshold_quantile=0.95,
        n_exc=1577,
        shape_diff=-0.18,
        shape_diff_ci_95=(-0.37, -0.04),
        rule_2_outcome="ordc_rejected_broader",
        paper_claim="...",
    )
    assert r.component == "system_energy"
    assert r.rule_2_outcome == "ordc_rejected_broader"


def test_outcome_from_shape_diff_ci_cancellation_supported():
    # shape_diff > 0, CI excludes 0 (positive direction)
    assert outcome_from_shape_diff_ci(0.20, (0.05, 0.40), n_per_half=789) == "cancellation_supported"


def test_outcome_from_shape_diff_ci_ordc_rejected_broader():
    # shape_diff < 0, CI excludes 0 (negative direction)
    assert outcome_from_shape_diff_ci(-0.18, (-0.37, -0.04), n_per_half=789) == "ordc_rejected_broader"


def test_outcome_from_shape_diff_ci_underpowered_neg():
    # shape_diff < 0, CI spans 0
    assert outcome_from_shape_diff_ci(-0.05, (-0.20, 0.05), n_per_half=789) == "underpowered_neg_direction"


def test_outcome_from_shape_diff_ci_underpowered_pos():
    # shape_diff >= 0, CI spans 0
    assert outcome_from_shape_diff_ci(0.05, (-0.05, 0.20), n_per_half=789) == "underpowered_pos_direction"


def test_outcome_from_shape_diff_ci_insufficient_sample():
    # n_per_half below threshold of 50
    assert outcome_from_shape_diff_ci(0.0, (-1.0, 1.0), n_per_half=40) == "insufficient_sample"


def test_fit_single_component_median_split_returns_result():
    from surg.analysis.gpd_components import fit_single_component_median_split

    rng = np.random.default_rng(0)
    n = 8000
    Z = rng.uniform(0, 10, size=n)
    Y = rng.exponential(scale=1.0 + 0.2 * Z, size=n)
    panel = pd.DataFrame({"Y": Y, "Z": Z})

    result = fit_single_component_median_split(
        panel=panel,
        response_col="Y",
        z_col="Z",
        component="system_energy",
        pnode_label="primary_cluster",
        threshold_quantile=0.95,
        n_boot=50,
        seed=0,
    )
    assert isinstance(result, ComponentsHeadlineResult)
    assert result.component == "system_energy"
    assert result.pnode_label == "primary_cluster"
    assert result.threshold_quantile == 0.95
    assert result.n_exc > 0
    assert result.rule_2_outcome in {
        "cancellation_supported",
        "ordc_rejected_broader",
        "underpowered_neg_direction",
        "underpowered_pos_direction",
        "insufficient_sample",
    }


def test_fit_single_component_median_split_low_power_emits_insufficient():
    # 80 obs → ~4 exceedances at 95th-pct → n_per_half < 50.
    # The wrapper should catch this BEFORE calling gpd_quantile_split_on_z
    # (which would otherwise raise on <20 exceedances).
    from surg.analysis.gpd_components import fit_single_component_median_split

    panel = pd.DataFrame({"Y": np.arange(80, dtype=float), "Z": np.arange(80, dtype=float)})
    result = fit_single_component_median_split(
        panel=panel,
        response_col="Y",
        z_col="Z",
        component="system_energy",
        pnode_label="primary_cluster",
        threshold_quantile=0.95,
        n_boot=50,
        seed=0,
    )
    assert result.rule_2_outcome == "insufficient_sample"
