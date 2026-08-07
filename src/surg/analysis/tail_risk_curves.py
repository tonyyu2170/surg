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
    bootstrap_method: str = "pair",
    island_ids: pd.Series | None = None,
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

    # Bootstrap: pair preserves byte-for-byte equivalence with the
    # pre-refactor implementation (regression test gate); cluster
    # resamples whole islands within the bin's rows for the 5-min
    # companion (sub-q1 item #8).
    rng = np.random.default_rng(seed)
    boot_p = np.empty(n_boot, dtype=np.float64)
    if bootstrap_method == "pair":
        for i in range(n_boot):
            idx = rng.integers(0, n_total, size=n_total)
            boot_p[i] = is_exc[idx].mean()
    elif bootstrap_method == "cluster":
        if island_ids is None:
            raise ValueError(
                "bootstrap_method='cluster' requires island_ids aligned to "
                "the bin's rows"
            )
        # Slice island_ids to the bin's rows, in the same order is_exc was
        # computed (panel.loc[z_bin_mask, response_col].dropna()).
        bin_island_ids = (
            island_ids.loc[z_bin_mask]
            .iloc[: len(bin_resp)]  # align to dropna order
            .reset_index(drop=True)
        )
        unique = bin_island_ids.unique()
        K = len(unique)
        for i in range(n_boot):
            sampled = rng.choice(unique, size=K, replace=True)
            # All bin rows whose island id is in the sampled list,
            # with multiplicity = count of that island id in `sampled`
            picks: list[np.ndarray] = []
            for iid in sampled:
                rows_in_island = (bin_island_ids == iid).to_numpy()
                picks.append(is_exc[rows_in_island])
            if not picks:
                boot_p[i] = 0.0
            else:
                boot_p[i] = np.concatenate(picks).mean()
    else:
        raise ValueError(f"Unknown bootstrap_method: {bootstrap_method!r}")

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
    bootstrap_method: str = "pair",
    island_ids: pd.Series | None = None,
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
                    bootstrap_method=bootstrap_method,
                    island_ids=island_ids,
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


def _plot_suptitle(per_pnode: dict) -> str:
    """Figure caption for a per-pnode result dict.

    `resolution` is read from the result rather than hardcoded: this
    plotter is shared by the hourly and 5-min entrypoints. Result dicts
    written before the key existed were all hourly runs, so that is the
    fallback.
    """
    return (
        f"{per_pnode['pnode_label']}: P(LMP > $X) by Z decile "
        f"(filter: {per_pnode.get('filter', '')}, "
        f"n_boot={per_pnode['n_boot']}, "
        f"{per_pnode.get('resolution', 'hourly')})"
    )


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
    fig.suptitle(_plot_suptitle(per_pnode))
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


def _ensure_total_lmp_columns(panel: pd.DataFrame, pnode_labels: tuple[str, ...]) -> pd.DataFrame:
    """For pnodes missing ``total_lmp_rt_<pnode>``, derive from component sum.

    LMP identity: ``total_lmp = system_energy + congestion + marginal_loss``.
    ``features.py`` only labels ``total_lmp_rt_cluster_mean`` (the cluster average)
    plus Ashburn pnodes; non-cluster labeled pnodes (ox, bristers, dom_zonal)
    have the three components but no labeled total_lmp. This helper materializes
    the missing columns via the additive identity so ``run_pnode_tail_risk_curves``
    can use them uniformly.
    """
    panel = panel.copy()
    for pnode in pnode_labels:
        total_col = f"total_lmp_rt_{pnode}"
        if total_col in panel.columns:
            continue
        se_col = f"system_energy_price_rt_{pnode}"
        co_col = f"congestion_price_rt_{pnode}"
        ml_col = f"marginal_loss_price_rt_{pnode}"
        if all(c in panel.columns for c in (se_col, co_col, ml_col)):
            panel[total_col] = panel[se_col] + panel[co_col] + panel[ml_col]
    return panel


def run_tail_risk_curves(
    panel: pd.DataFrame,
    *,
    out_root: Path,
    thresholds: list[float] | None = None,
    n_boot: int = 200,
    seed: int = 0,
    bootstrap_method: str = "pair",
    pnode_labels: tuple[str, ...] | None = None,
    filter_col: str | None = "passes_proposal_filter",
    pnode_to_response: dict[str, dict[str, str]] | None = None,
    cross_pnode_pnodes: tuple[str, ...] | None = None,
    plotted_pnodes: tuple[str, ...] | None = None,
    z_col: str = Z_COL,
    resolution: str = "hourly",
) -> None:
    """Top-level orchestrator: applies the proposal-filter (or skips it),
    runs all per-pnode + cross-pnode analyses, writes outputs to disk.

    Writes 5 JSONs + 4 PNGs + 1 CSV under ``out_root/tail_risk_curves/``.

    Sub-q1 item #8: ``bootstrap_method`` is "pair" (default; preserves
    hourly behavior) or "cluster" (5-min companion: resample whole 3-hour
    islands). ``pnode_labels`` selects a subset to process.
    Sub-q1 item #9: ``filter_col=None`` skips the filter and operates on
    the full panel.
    5-min companion: ``pnode_to_response`` / ``cross_pnode_pnodes`` /
    ``plotted_pnodes`` / ``z_col`` retarget the routine at a panel whose
    pnode labels and Z column differ from the hourly ones, and
    ``resolution`` is stamped into each result so the shared plotter can
    label the figure correctly instead of hardcoding "hourly".
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()
    if pnode_to_response is None:
        pnode_to_response = PNODE_TO_RESPONSE
    if plotted_pnodes is None:
        plotted_pnodes = PER_PNODE_PLOTTED

    # `pnode_labels` (item #8) and `cross_pnode_pnodes` (5-min worktree)
    # are two names for the same knob, arrived at independently. Accept
    # either; refuse a conflicting pair rather than silently picking one.
    if (
        cross_pnode_pnodes is not None
        and pnode_labels is not None
        and tuple(cross_pnode_pnodes) != tuple(pnode_labels)
    ):
        raise ValueError(
            "cross_pnode_pnodes and pnode_labels were both given and differ: "
            f"{tuple(cross_pnode_pnodes)!r} vs {tuple(pnode_labels)!r}"
        )
    if cross_pnode_pnodes is not None:
        pnodes_to_process = tuple(cross_pnode_pnodes)
    elif pnode_labels is not None:
        pnodes_to_process = tuple(pnode_labels)
    else:
        pnodes_to_process = tuple(CROSS_PNODE_PNODES)

    tr_dir = Path(out_root) / "tail_risk_curves"
    tr_dir.mkdir(parents=True, exist_ok=True)

    if filter_col is None:
        filtered = panel.copy()
        filter_desc = "no filter (full panel)"
    else:
        filtered = panel.loc[panel[filter_col] == True].copy()  # noqa: E712
        filter_desc = f"{filter_col} == True"

    # Materialize derived total_lmp columns where features.py didn't label
    # them. Scoped to the pnodes actually processed: the hourly full run
    # passes none of the selectors, so this is identical to the previous
    # `CROSS_PNODE_PNODES` behavior there, while the 5-min panel (whose
    # labels are not the hourly ones) no longer KeyErrors.
    filtered = _ensure_total_lmp_columns(filtered, pnodes_to_process)

    # Compute island_ids on the filtered panel (only needed for cluster
    # bootstrap; identify_islands assigns one int per filtered row based
    # on >10-minute timestamp gaps).
    if bootstrap_method == "cluster":
        from surg.analysis.bootstrap_strategies import identify_islands
        island_ids = identify_islands(
            pd.DatetimeIndex(filtered["datetime_beginning_ept"]),
            pd.Series(True, index=filtered.index),
            gap_threshold_minutes=10,
        )
    else:
        island_ids = None

    all_results: list[dict] = []

    for pnode_label in pnodes_to_process:
        response_cols = pnode_to_response[pnode_label]
        # Drop NA rows in either response column for this pnode
        cols = list(response_cols.values()) + [z_col]
        sub = filtered.dropna(subset=cols)
        # Slice island_ids to match `sub`'s row index (dropna preserves
        # index labels)
        sub_island_ids = (
            island_ids.loc[sub.index] if island_ids is not None else None
        )

        result = run_pnode_tail_risk_curves(
            panel=sub,
            pnode_label=pnode_label,
            response_cols=response_cols,
            z_col=z_col,
            thresholds=thresholds,
            n_deciles=10,
            n_boot=n_boot,
            seed=seed,
            bootstrap_method=bootstrap_method,
            island_ids=sub_island_ids,
        )
        # Inject filter + resolution provenance (the per-pnode routine
        # can't know either — both come from how it was invoked).
        result["filter"] = filter_desc
        result["resolution"] = resolution
        all_results.append(result)

        if pnode_label in plotted_pnodes:
            # Write per-pnode JSON
            with open(tr_dir / f"{pnode_label}.json", "w") as f:
                json.dump(_json_serializable(result), f, indent=2)
            # Write per-pnode PNG
            plot_tail_risk_curves(result, tr_dir / f"{pnode_label}.png")

    # Cross-pnode summary
    summary = aggregate_cross_pnode_summary(all_results)
    summary["filter"] = filter_desc   # propagate provenance to cross-pnode summary too
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
