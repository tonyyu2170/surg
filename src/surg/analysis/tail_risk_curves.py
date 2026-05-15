"""Direct Z -> LMP tail-risk characterization (sub-q1 closure item #6).

Per design spec at
`docs/plans/2026-05-14-z-lmp-tail-risk-characterization-design.md`.

Produces P(LMP > $X | Z bin) curves for the user's stated sub-q1
framing: "what range of Z makes LMP go crazy."

Mechanism evidence (items #1-4) explains WHY; this module produces
the descriptive WHERE.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def compute_z_deciles(panel: pd.DataFrame, z_col: str) -> tuple[np.ndarray, np.ndarray]:
    """Compute 10 equal-count quantile bins of Z.

    Returns
    -------
    edges : np.ndarray of shape (11,)
        Bin edges including endpoints. ``edges[0]`` = Z min, ``edges[10]`` = Z max.
    bin_indices : np.ndarray of shape (n,)
        Integer bin assignment in [0, 9] per row of ``panel``.

    Notes
    -----
    When ``z`` has tied values at quantile boundaries (e.g., many zeros
    from flat-load periods), multiple interior bins may collapse and have
    zero observations. Downstream callers must handle ``decile_n_obs[i] == 0``
    defensively.
    """
    z = panel[z_col].to_numpy()
    edges = np.quantile(z, np.linspace(0.0, 1.0, 11))
    # digitize returns 1..N+1; clip into 0..9 so a value equal to edges[-1] lands in bin 9
    bin_indices = np.clip(np.digitize(z, edges[1:-1], right=True), 0, 9)
    return edges, bin_indices


def compute_threshold_percentiles(
    panel: pd.DataFrame,
    response_col: str,
    thresholds: list[float],
) -> dict[float, float]:
    """Map each $-threshold to its empirical percentile in the panel.

    Returns
    -------
    dict[float, float]
        ``{threshold_$: percentile_in_[0,1]}``. Used for annotating
        chart legends like ``"$500 (p99)"``.
    """
    resp = panel[response_col].dropna().to_numpy()
    return {
        float(t): float(stats.percentileofscore(resp, t, kind="weak") / 100.0)
        for t in thresholds
    }


def compute_exceedance_probability_with_ci(
    panel: pd.DataFrame,
    *,
    response_col: str,
    threshold: float,
    z_bin_mask: np.ndarray,
    n_boot: int = 200,
    seed: int = 0,
) -> tuple[float, int, int, float, float]:
    """Pair-bootstrap CI for P(response > threshold | row in z_bin_mask).

    Returns
    -------
    p_hat : float
        Empirical exceedance probability in the bin.
    n_exc : int
        Number of exceedances.
    n_total : int
        Total rows in the bin.
    ci_low : float
        Bootstrap 95% CI lower bound. ``0.0`` if ``n_exc == 0``.
    ci_high : float
        Bootstrap 95% CI upper bound. Wilson exact upper for ``n_exc == 0``
        (bootstrap is degenerate). ``1.0`` (with Wilson exact lower returned
        in ``ci_low``) for ``n_exc == n_total``.
    """
    bin_resp = panel.loc[z_bin_mask, response_col].dropna().to_numpy()
    n_total = int(bin_resp.size)
    if n_total == 0:
        return 0.0, 0, 0, 0.0, 0.0

    if n_boot <= 0:
        raise ValueError(f"n_boot must be positive, got {n_boot}")

    is_exc = (bin_resp > threshold).astype(np.int64)
    n_exc = int(is_exc.sum())
    p_hat = n_exc / n_total

    if n_exc == 0:
        # Bootstrap is degenerate (all reps yield 0); use Wilson upper bound.
        # Wilson upper for n_exc=0 at alpha=0.05: z = 1.96, p = 0
        # upper = (z^2) / (n + z^2)  =>  3.8416 / (n + 3.8416)
        z2 = 1.96**2
        ci_high = z2 / (n_total + z2)
        return p_hat, n_exc, n_total, 0.0, float(ci_high)

    if n_exc == n_total:
        # Wilson lower for n_exc=n at alpha=0.05: p = 1, sqrt term = z
        # lower = (2*n + z^2 - z*z) / (2*(n + z^2)) = n / (n + z^2)
        z2 = 1.96**2
        ci_low = n_total / (n_total + z2)
        return p_hat, n_exc, n_total, float(ci_low), 1.0

    # Pair-bootstrap: resample (z_bin_mask rows) with replacement.
    rng = np.random.default_rng(seed)
    boot_p = np.empty(n_boot, dtype=np.float64)
    for i in range(n_boot):
        idx = rng.integers(0, n_total, size=n_total)
        boot_p[i] = is_exc[idx].mean()

    ci_low, ci_high = np.quantile(boot_p, [0.025, 0.975])
    return p_hat, n_exc, n_total, float(ci_low), float(ci_high)


def run_pnode_tail_risk_curves(
    panel: pd.DataFrame,
    *,
    pnode_label: str,
    response_cols: dict[str, str],
    z_col: str,
    thresholds: list[float],
    n_deciles: int = 10,
    n_boot: int = 200,
    seed: int = 0,
) -> dict:
    """Per-pnode orchestrator: compute the full P(response > threshold | z decile)
    table for two response variables (typically total_lmp + congestion).

    Returns a JSON-ready dict matching the design spec schema.
    """
    if n_deciles != 10:
        raise NotImplementedError(
            f"n_deciles={n_deciles} not supported; design fixes deciles=10"
        )

    edges, bin_indices = compute_z_deciles(panel, z_col)
    decile_n_obs = [int((bin_indices == d).sum()) for d in range(n_deciles)]

    threshold_pcts: dict[str, dict[float, float]] = {}
    for key, col in response_cols.items():
        threshold_pcts[key] = compute_threshold_percentiles(panel, col, thresholds)

    results: dict[str, list[dict]] = {key: [] for key in response_cols}
    for resp_key, resp_col in response_cols.items():
        for d in range(n_deciles):
            mask = bin_indices == d
            decile_entry: dict = {
                "decile": d + 1,  # 1-indexed for display
                "z_range_mw_per_min": [float(edges[d]), float(edges[d + 1])],
                "n_total": decile_n_obs[d],
                "by_threshold": {},
            }
            for t in thresholds:
                p_hat, n_exc, _, lo, hi = compute_exceedance_probability_with_ci(
                    panel,
                    response_col=resp_col,
                    threshold=t,
                    z_bin_mask=mask,
                    n_boot=n_boot,
                    seed=seed + d * 100_000 + int(t),
                )
                decile_entry["by_threshold"][float(t)] = {
                    "p_hat": p_hat,
                    "n_exc": n_exc,
                    "ci_95": [lo, hi],
                }
            results[resp_key].append(decile_entry)

    return {
        "pnode_label": pnode_label,
        "response_cols": response_cols,
        "z_col": z_col,
        "thresholds": [float(t) for t in thresholds],
        "n_boot": n_boot,
        "n_total_filtered": int(len(panel)),
        "decile_edges_mw_per_min": [float(e) for e in edges],
        "decile_n_obs": decile_n_obs,
        "threshold_percentiles": threshold_pcts,
        "results": results,
    }


def aggregate_cross_pnode_summary(per_pnode_results: list[dict]) -> dict:
    """Extract top-decile-only summary across all per-pnode results.

    Output schema per design spec: ``{n_boot, thresholds, scope, pnodes: [...]}``.
    Each pnode entry has top-decile p_hat + CI per (response, threshold).
    """
    if not per_pnode_results:
        return {"n_boot": None, "scope": "top_decile_only", "thresholds": [], "pnodes": []}

    thresholds = per_pnode_results[0]["thresholds"]
    n_boot = per_pnode_results[0].get("n_boot")

    pnodes_out: list[dict] = []
    for entry in per_pnode_results:
        # Top decile is the last one (decile=10, 0-indexed 9)
        top_decile_by_resp: dict[str, dict[float, dict]] = {}
        for resp_key, deciles in entry["results"].items():
            top = deciles[-1]  # 10th decile
            top_decile_by_resp[resp_key] = {
                t: {
                    "p_hat": top["by_threshold"][t]["p_hat"],
                    "ci_95": top["by_threshold"][t]["ci_95"],
                }
                for t in thresholds
            }

        pnodes_out.append({
            "pnode_label": entry["pnode_label"],
            "z_range_top_decile_mw_per_min": [
                float(entry["decile_edges_mw_per_min"][-2]),
                float(entry["decile_edges_mw_per_min"][-1]),
            ],
            "n_top_decile": int(entry["decile_n_obs"][-1]),
            "results": top_decile_by_resp,
        })

    return {
        "n_boot": n_boot,
        "thresholds": thresholds,
        "scope": "top_decile_only",
        "pnodes": pnodes_out,
    }


def plot_tail_risk_curves(per_pnode: dict, out_path: Path) -> None:
    """2-panel chart: P(LMP > $X | Z decile) for total_lmp + congestion.

    X-axis: decile index 1-10 with MW/min edge labels.
    Y-axis: exceedance probability with bootstrap 95% CI ribbon.
    Lines: one per $-threshold, colored by viridis.
    """
    # Local import to avoid loading matplotlib at module import time.
    # Backend selection (Agg for headless test runs) is handled by
    # conftest.py via MPLBACKEND env var; library code does not call
    # matplotlib.use() to avoid mutating process-level state.
    import matplotlib.pyplot as plt
    from matplotlib.cm import viridis

    pnode_label = per_pnode["pnode_label"]
    thresholds = per_pnode["thresholds"]
    edges = per_pnode["decile_edges_mw_per_min"]
    threshold_pcts = per_pnode["threshold_percentiles"]

    decile_centers = list(range(1, 11))
    xtick_labels = [
        f"{d}\n[{edges[d-1]:.1f},\n{edges[d]:.1f}]"
        for d in decile_centers
    ]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    for ax, resp_key in zip(axes, ("total_lmp", "congestion")):
        deciles = per_pnode["results"][resp_key]
        n_thresh = len(thresholds)
        for i, t in enumerate(thresholds):
            ps = [d["by_threshold"][t]["p_hat"] for d in deciles]
            lo = [d["by_threshold"][t]["ci_95"][0] for d in deciles]
            hi = [d["by_threshold"][t]["ci_95"][1] for d in deciles]
            color = viridis(i / max(1, n_thresh - 1))
            pct = threshold_pcts.get(resp_key, {}).get(t, None)
            label = (
                f"${int(t)} (p{pct*100:.1f})" if pct is not None else f"${int(t)}"
            )
            ax.plot(
                decile_centers, ps,
                color=color, linewidth=1 + i * 0.4, marker="o", label=label,
            )
            ax.fill_between(decile_centers, lo, hi, color=color, alpha=0.15)

        ax.set_title(f"{resp_key}")
        ax.set_xlabel("Z decile (MW/min range)")
        ax.set_xticks(decile_centers)
        ax.set_xticklabels(xtick_labels, fontsize=8)
        ax.set_ylim(bottom=0)
        ax.grid(True, alpha=0.3)
        ax.legend(title="threshold $ (pct)", loc="upper left", fontsize=8)

    axes[0].set_ylabel("P(LMP > $threshold)")
    filter_desc = per_pnode.get("filter", "")
    fig.suptitle(
        f"{pnode_label}: P(LMP > $X) by Z decile "
        f"(filter: {filter_desc}, n_boot={per_pnode['n_boot']}, hourly)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS = [100.0, 250.0, 500.0, 1000.0, 2000.0]
Z_COL = "dom_load_gradient_abs_mw_per_min"
FILTER_COL = "passes_proposal_filter"
FILTER_DESC = "passes_proposal_filter == True"
PNODE_TO_RESPONSE: dict[str, dict[str, str]] = {
    "primary": {
        "total_lmp": "total_lmp_rt_cluster_mean",
        "congestion": "congestion_price_rt_cluster_mean",
    },
    "dom_zonal": {
        "total_lmp": "total_lmp_rt_dom_zonal",
        "congestion": "congestion_price_rt_dom_zonal",
    },
    "ashburn_tx1": {
        "total_lmp": "total_lmp_rt_ashburn_tx1",
        "congestion": "congestion_price_rt_ashburn_tx1",
    },
    "ashburn_tx2": {
        "total_lmp": "total_lmp_rt_ashburn_tx2",
        "congestion": "congestion_price_rt_ashburn_tx2",
    },
    "ox": {
        "total_lmp": "total_lmp_rt_ox",
        "congestion": "congestion_price_rt_ox",
    },
    "bristers": {
        "total_lmp": "total_lmp_rt_bristers",
        "congestion": "congestion_price_rt_bristers",
    },
    "total_lmp": {  # total_lmp pnode alias to cluster_mean total_lmp
        "total_lmp": "total_lmp_rt_cluster_mean",
        "congestion": "congestion_price_rt_cluster_mean",
    },
}
PER_PNODE_PLOTTED = ("primary", "dom_zonal", "ashburn_tx1", "ashburn_tx2")
CROSS_PNODE_PNODES = (
    "primary", "total_lmp", "ox", "bristers",
    "dom_zonal", "ashburn_tx1", "ashburn_tx2",
)


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


def run_tail_risk_curves(
    panel: pd.DataFrame,
    *,
    out_root: Path,
    thresholds: list[float] | None = None,
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """Top-level orchestrator: applies the proposal-filter, runs all
    per-pnode + cross-pnode analyses, writes outputs to disk.

    Writes 5 JSONs + 4 PNGs + 1 CSV under ``out_root/tail_risk_curves/``.
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

    tr_dir = Path(out_root) / "tail_risk_curves"
    tr_dir.mkdir(parents=True, exist_ok=True)

    filtered = panel.loc[panel[FILTER_COL] == True].copy()  # noqa: E712

    all_results: list[dict] = []

    # Per-pnode pass (cross-pnode set includes all 7 pnodes; only 4 get plots)
    for pnode_label in CROSS_PNODE_PNODES:
        response_cols = PNODE_TO_RESPONSE[pnode_label]
        # Drop NA rows in either response column for this pnode
        cols = list(response_cols.values()) + [Z_COL]
        sub = filtered.dropna(subset=cols)

        result = run_pnode_tail_risk_curves(
            panel=sub,
            pnode_label=pnode_label,
            response_cols=response_cols,
            z_col=Z_COL,
            thresholds=thresholds,
            n_deciles=10,
            n_boot=n_boot,
            seed=seed,
        )
        # Inject filter provenance (per-pnode orchestrator can't know this)
        result["filter"] = FILTER_DESC
        all_results.append(result)

        if pnode_label in PER_PNODE_PLOTTED:
            # Write per-pnode JSON
            with open(tr_dir / f"{pnode_label}.json", "w") as f:
                json.dump(_json_serializable(result), f, indent=2)
            # Write per-pnode PNG
            plot_tail_risk_curves(result, tr_dir / f"{pnode_label}.png")

    # Cross-pnode summary
    summary = aggregate_cross_pnode_summary(all_results)
    summary["filter"] = FILTER_DESC   # propagate provenance to cross-pnode summary too
    with open(tr_dir / "cross_pnode_summary.json", "w") as f:
        json.dump(_json_serializable(summary), f, indent=2)

    # Cross-pnode summary CSV
    _write_cross_pnode_csv(summary, tr_dir / "cross_pnode_summary.csv")


def _json_serializable(obj):
    """Convert numeric dict keys to strings (JSON requires) and recurse."""
    if isinstance(obj, dict):
        return {str(k): _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_serializable(v) for v in obj]
    return obj


def _write_cross_pnode_csv(summary: dict, out_path: Path) -> None:
    """Write the top-decile cross-pnode summary as a wide CSV.

    Rows = pnodes; columns = (response_var, threshold) pairs with p_hat.
    """
    thresholds = summary["thresholds"]
    response_vars = ("total_lmp", "congestion")
    header = [
        "pnode_label",
        "z_range_top_decile_low_mw_per_min",
        "z_range_top_decile_high_mw_per_min",
        "n_top_decile",
    ]
    for r in response_vars:
        for t in thresholds:
            header.append(f"{r}_p_hat_at_{int(t)}")

    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for p in summary["pnodes"]:
            row = [
                p["pnode_label"],
                p["z_range_top_decile_mw_per_min"][0],
                p["z_range_top_decile_mw_per_min"][1],
                p["n_top_decile"],
            ]
            for r in response_vars:
                for t in thresholds:
                    row.append(p["results"][r][t]["p_hat"])
            w.writerow(row)
