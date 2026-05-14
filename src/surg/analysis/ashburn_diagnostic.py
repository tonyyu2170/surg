"""Ashburn TX1 99th-pct anomaly diagnostic (sub-q1 closure item #4).

LOO sensitivity at all 4 thresholds (90/95/99/99.5) on TX1 + TX2;
cross-threshold full-sample comparison extracted from existing Spec B
JSON; 4-panel overlay scatter PNG.

Reuses gpd_continuous.fit_gpd_continuous_z (linear form) for the LOO fits.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.gpd_continuous import fit_gpd_continuous_z


@dataclass(frozen=True, slots=True)
class LOOResult:
    pnode_label: str
    threshold_quantile: float
    n_exc: int
    full_sample_beta_1: float
    loo_beta_1_distribution: tuple[float, ...]
    delta_beta_1_per_exceedance: tuple[float, ...]
    top5_influential_indices: tuple[int, ...]
    full_sample_percentile_in_loo: float


def loo_beta_distribution(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    threshold_quantile: float,
    pnode_label: str = "",
) -> LOOResult:
    """Leave-one-out β₁ sensitivity for Spec B linear form fit on a single pnode/threshold.

    Extracts exceedances from the panel, fits the full-sample linear GPD model,
    then performs LOO over the exceedance set — dropping one exceedance at a time
    and re-fitting to measure each observation's influence on β₁.

    The LOO fits pass pre-computed exceedance values (Y_exc, shifted to be > 0)
    with threshold=0.0 so that fit_gpd_continuous_z's internal threshold filter
    is a no-op and no centering shift is applied.
    """
    sub = panel.dropna(subset=[response_col, z_col]).copy()
    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()
    threshold = float(np.quantile(Y, threshold_quantile))
    exc_mask = Y > threshold
    Y_exc = Y[exc_mask] - threshold
    Z_exc = Z[exc_mask]
    n_exc = len(Y_exc)

    # Full-sample fit on exceedances. Pass threshold=0.0 because Y_exc is already
    # shifted (values are exceedances above 0); the internal filter Y > 0.0 keeps all.
    full = fit_gpd_continuous_z(
        Y=Y_exc, Z=Z_exc, threshold=0.0, form="linear", n_boot=0, seed=0,
    )
    full_beta_1 = float(full.shape_coefficients[1]) if full.convergence_status == "converged" else float("nan")

    loo_beta_1: list[float] = []
    delta_beta_1: list[float] = []
    for i in range(n_exc):
        mask = np.ones(n_exc, dtype=bool)
        mask[i] = False
        try:
            r = fit_gpd_continuous_z(
                Y=Y_exc[mask], Z=Z_exc[mask], threshold=0.0,
                form="linear", n_boot=0, seed=0,
            )
            b = float(r.shape_coefficients[1]) if r.convergence_status == "converged" else float("nan")
        except Exception:
            b = float("nan")
        loo_beta_1.append(b)
        delta_beta_1.append(b - full_beta_1 if math.isfinite(b) and math.isfinite(full_beta_1) else float("nan"))

    abs_deltas = [abs(d) if math.isfinite(d) else -1.0 for d in delta_beta_1]
    top5 = tuple(sorted(range(n_exc), key=lambda i: -abs_deltas[i])[:min(5, n_exc)])

    finite_loo = [b for b in loo_beta_1 if math.isfinite(b)]
    if finite_loo and math.isfinite(full_beta_1):
        pct = float((np.asarray(finite_loo) <= full_beta_1).mean())
    else:
        pct = float("nan")

    return LOOResult(
        pnode_label=pnode_label,
        threshold_quantile=threshold_quantile,
        n_exc=n_exc,
        full_sample_beta_1=full_beta_1,
        loo_beta_1_distribution=tuple(loo_beta_1),
        delta_beta_1_per_exceedance=tuple(delta_beta_1),
        top5_influential_indices=top5,
        full_sample_percentile_in_loo=pct,
    )
