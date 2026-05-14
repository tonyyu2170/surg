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
    # Accept either "converged" or "insufficient_bootstrap_reps" — both mean the
    # MLE converged; only bootstrap (which we don't run with n_boot=0) didn't.
    full_beta_1 = (
        float(full.shape_coefficients[1])
        if math.isfinite(full.shape_coefficients[1])
        else float("nan")
    )

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
            b = (
                float(r.shape_coefficients[1])
                if math.isfinite(r.shape_coefficients[1])
                else float("nan")
            )
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


def extract_threshold_sweep_summary(
    *,
    spec_b_json_path: Path,
    threshold_qs: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
) -> dict:
    """Pull Spec B linear-form β₁ + CI for a pnode at each threshold quantile."""
    payload = json.loads(spec_b_json_path.read_text())
    entries: list[dict] = []
    for q in threshold_qs:
        match = next(
            (e for e in payload.get("threshold_sweep", [])
             if abs(e.get("threshold_quantile", -1) - q) < 1e-6),
            None,
        )
        if match is None or "linear" not in match:
            continue
        lin = match["linear"]
        beta_1 = lin["shape_coefficients"][1] if lin.get("convergence_status") == "converged" else None
        ci_pair = lin.get("shape_coefficients_bootstrap_ci_95")
        beta_1_ci = ci_pair[1] if (ci_pair is not None and len(ci_pair) > 1) else None
        entries.append({
            "threshold_quantile": q,
            "beta_1": beta_1,
            "beta_1_ci_95": beta_1_ci,
            "convergence_status": lin.get("convergence_status"),
        })
    return {
        "pnode_label": payload.get("pnode_label"),
        "response_col": payload.get("response_col"),
        "entries": entries,
    }


def _nan_to_none(x: float | None) -> float | None:
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return float(x)


def _loo_to_dict(r: LOOResult) -> dict:
    return {
        "pnode_label": r.pnode_label,
        "threshold_quantile": r.threshold_quantile,
        "n_exc": r.n_exc,
        "full_sample_beta_1": _nan_to_none(r.full_sample_beta_1),
        "loo_beta_1_distribution": [_nan_to_none(b) for b in r.loo_beta_1_distribution],
        "delta_beta_1_per_exceedance": [_nan_to_none(d) for d in r.delta_beta_1_per_exceedance],
        "top5_influential_indices": list(r.top5_influential_indices),
        "full_sample_percentile_in_loo": _nan_to_none(r.full_sample_percentile_in_loo),
    }


def run_ashburn_diagnostic(
    panel: pd.DataFrame,
    out_dir: Path,
    *,
    pnode_labels: tuple[str, ...] = ("ashburn_tx1", "ashburn_tx2"),
    threshold_quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    spec_b_results_dir: Path | None = None,
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    response_col_template: str = "congestion_price_rt_{pnode}",
    seed: int = 0,
) -> None:
    """Orchestrator for sub-q1 closure item #4 — Ashburn diagnostic."""
    out_dir.mkdir(parents=True, exist_ok=True)
    spec_b_dir = spec_b_results_dir if spec_b_results_dir is not None else Path("outputs/gpd_continuous")

    # Per-pnode LOO across thresholds.
    pnode_response_cols: dict[str, str] = {}
    fitted_slopes: dict[str, dict[float, float]] = {}
    cross_summary: list[dict] = []

    for pnode in pnode_labels:
        col = response_col_template.format(pnode=pnode)
        if col not in panel.columns or panel[col].dropna().empty:
            continue
        pnode_response_cols[pnode] = col
        loo_results: list[dict] = []
        for q in threshold_quantiles:
            r = loo_beta_distribution(
                panel=panel, response_col=col, z_col=z_col,
                threshold_quantile=q, pnode_label=pnode,
            )
            loo_results.append(_loo_to_dict(r))
        (out_dir / f"{pnode.replace('ashburn_', '')}_loo.json").write_text(
            json.dumps({"pnode_label": pnode, "results": loo_results}, indent=2)
        )

        # Cross-threshold summary from existing Spec B JSON (if present).
        spec_b_path = spec_b_dir / f"{pnode}.json"
        if spec_b_path.exists():
            summary = extract_threshold_sweep_summary(
                spec_b_json_path=spec_b_path,
                threshold_qs=threshold_quantiles,
            )
            cross_summary.append(summary)
            fitted_slopes[pnode] = {
                e["threshold_quantile"]: e["beta_1"]
                for e in summary["entries"]
                if e["beta_1"] is not None
            }

    (out_dir / "cross_threshold_summary.json").write_text(
        json.dumps({"pnodes": cross_summary}, indent=2)
    )

    plot_lmp_vs_z_scatter(
        panel=panel,
        pnode_response_cols=pnode_response_cols,
        z_col=z_col,
        threshold_qs=threshold_quantiles,
        out_path=out_dir / "scatter_overlay.png",
        fitted_slopes=fitted_slopes,
    )


def plot_lmp_vs_z_scatter(
    panel: pd.DataFrame,
    *,
    pnode_response_cols: dict[str, str],   # pnode_label -> response_col
    z_col: str,
    threshold_qs: tuple[float, ...],
    out_path: Path,
    fitted_slopes: dict[str, dict[float, float]] | None = None,
    figsize: tuple[float, float] = (14, 10),
) -> None:
    """4-panel overlay scatter of LMP vs Z at each threshold quantile.

    Marker shape distinguishes pnodes. Color encodes year.
    """
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=figsize, sharex=False, sharey=False)
    axes_flat = axes.flatten()

    markers = {"ashburn_tx1": "o", "ashburn_tx2": "^"}

    for ax_i, q in enumerate(threshold_qs):
        ax = axes_flat[ax_i]
        for pnode, col in pnode_response_cols.items():
            sub = panel.dropna(subset=[col, z_col]).copy()
            sub["__year"] = pd.to_datetime(sub["datetime_beginning_ept"]).dt.year
            threshold = float(np.quantile(sub[col].to_numpy(), q))
            exc = sub[sub[col] > threshold]
            ax.scatter(
                exc[z_col], exc[col],
                marker=markers.get(pnode, "x"),
                c=exc["__year"], cmap="viridis",
                alpha=0.6, s=20, label=pnode,
            )
            if fitted_slopes and pnode in fitted_slopes and q in fitted_slopes[pnode]:
                slope = fitted_slopes[pnode][q]
                z_line = np.linspace(exc[z_col].min(), exc[z_col].max(), 50)
                # Linear shape parameter visualization, NOT the LMP value — purely indicative.
                ax.plot(z_line, threshold + slope * z_line * (exc[col].max() - threshold),
                        linestyle="--", linewidth=1, alpha=0.7, label=f"{pnode} slope={slope:.3f}")
        ax.set_title(f"Threshold quantile = {q}")
        ax.set_xlabel(z_col)
        ax.set_ylabel("LMP")
        ax.legend(loc="upper right", fontsize=8)
    fig.suptitle("Ashburn TX1 vs TX2 — exceedances at each threshold")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
