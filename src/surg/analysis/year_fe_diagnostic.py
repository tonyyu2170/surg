"""τ=0.99 secular sign-flip diagnostic (sub-q1 closure item #3).

Three-layer evidence:
  L1: raw per-year LMP percentile stats (descriptive only).
  L2: pair-bootstrap year-dummy coefficient CIs (per-year LEVEL SHIFTS,
      not a trend test).
  L3: pair-bootstrap secular-component CI = primary_z_slope - year_fe_z_slope
      at each tau (the actual trend test).

Reuses qr_full.fit_qr_full for the year-FE QR.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.qr_full import fit_qr_full


def compute_raw_per_year_stats(
    panel: pd.DataFrame,
    *,
    response_col: str,
    year_col: str,
    pct_list: tuple[float, ...] = (0.90, 0.95, 0.99),
) -> list[dict]:
    """Per-year summary stats of `response_col`. Descriptive only — no model."""
    sub = panel.dropna(subset=[response_col, year_col]).copy()
    sub["__year"] = pd.to_datetime(sub[year_col]).dt.year
    stats: list[dict] = []
    for year, group in sub.groupby("__year"):
        row = {"year": int(year), "n_obs": int(len(group))}
        for p in pct_list:
            row[f"p{int(p*100)}"] = float(np.quantile(group[response_col].to_numpy(), p))
        stats.append(row)
    return sorted(stats, key=lambda r: r["year"])


def _nan_to_none(x: float | None) -> float | None:
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return float(x)


def bootstrap_year_dummy_coefs(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    year_col: str,
    taus: tuple[float, ...],
    n_boot: int = 200,
    seed: int = 0,
    bootstrap_method: str = "pair",
    island_ids: pd.Series | None = None,
) -> dict:
    """Pair-bootstrap CIs for year-dummy coefficients in fit_qr_full's year_fe spec.

    Reports descriptive PER-YEAR LEVEL SHIFTS (from baseline). NOT a trend test.
    """
    sub = panel.dropna(subset=[response_col, z_col, year_col]).copy()
    sub[year_col] = pd.to_datetime(sub[year_col])
    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()
    hour = sub[year_col].dt.hour.to_numpy()
    month = sub[year_col].dt.month.to_numpy()
    year = sub[year_col].dt.year.to_numpy()
    sub_island_ids = (
        island_ids.loc[sub.index].to_numpy()
        if island_ids is not None else None
    )

    distinct_years = sorted(np.unique(year).tolist())
    if len(distinct_years) < 2:
        return {"skip_reason": f"only {len(distinct_years)} distinct year(s)"}

    baseline = distinct_years[0]
    dummy_years = distinct_years[1:]

    out: dict = {}
    n = len(Y)
    for tau_idx, tau in enumerate(taus):
        # Point estimate from a single fit (no bootstrap of point).
        point_fit = fit_qr_full(Y, Z, hour, month, year=year, tau=tau, n_boot=0,
                                seed=seed + tau_idx * 1000)
        point_coefs = point_fit.covariate_coefs

        # Bootstrap each year dummy. Pair preserves byte-for-byte
        # equivalence with the pre-refactor implementation; cluster
        # resamples whole islands for the 5-min companion.
        rng = np.random.default_rng(seed + tau_idx * 1000 + 7)
        boot_coefs: dict[int, list[float]] = {y: [] for y in dummy_years}
        if bootstrap_method == "pair":
            sample_idx_iter = (rng.integers(0, n, size=n) for _ in range(n_boot))
        elif bootstrap_method == "cluster":
            if sub_island_ids is None:
                raise ValueError(
                    "bootstrap_method='cluster' requires island_ids"
                )
            unique_ids = np.unique(sub_island_ids)
            K = len(unique_ids)
            island_to_rows = {
                int(iid): np.where(sub_island_ids == iid)[0]
                for iid in unique_ids
            }
            def _cluster_iter():
                for _ in range(n_boot):
                    sampled = rng.choice(unique_ids, size=K, replace=True)
                    yield np.concatenate([island_to_rows[int(iid)] for iid in sampled])
            sample_idx_iter = _cluster_iter()
        else:
            raise ValueError(f"Unknown bootstrap_method: {bootstrap_method!r}")
        for idx in sample_idx_iter:
            try:
                rep_fit = fit_qr_full(
                    Y[idx], Z[idx], hour[idx], month[idx],
                    year=year[idx], tau=tau, n_boot=0, seed=0,
                )
            except Exception:
                continue
            for y in dummy_years:
                key = f"year_{y}"
                if key in rep_fit.covariate_coefs:
                    val = rep_fit.covariate_coefs[key]
                    if np.isfinite(val):
                        boot_coefs[y].append(val)

        by_year: dict[str, dict] = {}
        for y in dummy_years:
            arr = np.asarray(boot_coefs[y])
            if len(arr) < 20:
                ci = (float("nan"), float("nan"))
            else:
                ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
            by_year[f"year_{y}"] = {
                "point": _nan_to_none(point_coefs.get(f"year_{y}", float("nan"))),
                "ci": [_nan_to_none(ci[0]), _nan_to_none(ci[1])],
                "n_boot_converged": int(len(arr)),
            }
        out[f"tau_{tau:.2f}"] = by_year
        out[f"tau_{tau:.2f}_baseline_year"] = int(baseline)
    return out


def bootstrap_secular_component(
    panel: pd.DataFrame,
    *,
    response_col: str,
    z_col: str,
    year_col: str,
    taus: tuple[float, ...],
    n_boot: int = 200,
    seed: int = 0,
    bootstrap_method: str = "pair",
    island_ids: pd.Series | None = None,
) -> dict:
    """Pair-bootstrap CI on primary_z_slope - year_fe_z_slope per tau.

    This IS the trend test for the τ=0.99 secular sign-flip claim.
    """
    sub = panel.dropna(subset=[response_col, z_col, year_col]).copy()
    sub[year_col] = pd.to_datetime(sub[year_col])
    Y = sub[response_col].to_numpy()
    Z = sub[z_col].to_numpy()
    hour = sub[year_col].dt.hour.to_numpy()
    month = sub[year_col].dt.month.to_numpy()
    year = sub[year_col].dt.year.to_numpy()
    sub_island_ids = (
        island_ids.loc[sub.index].to_numpy()
        if island_ids is not None else None
    )

    distinct_years = sorted(np.unique(year).tolist())
    if len(distinct_years) < 2:
        return {"skip_reason": f"only {len(distinct_years)} distinct year(s)"}

    out: dict = {}
    n = len(Y)
    for tau_idx, tau in enumerate(taus):
        primary_fit = fit_qr_full(Y, Z, hour, month, tau=tau, n_boot=0, seed=seed)
        yfe_fit = fit_qr_full(Y, Z, hour, month, year=year, tau=tau, n_boot=0, seed=seed)
        point_secular = primary_fit.z_slope - yfe_fit.z_slope

        rng = np.random.default_rng(seed + tau_idx * 1000 + 11)
        diffs: list[float] = []
        if bootstrap_method == "pair":
            sample_idx_iter = (rng.integers(0, n, size=n) for _ in range(n_boot))
        elif bootstrap_method == "cluster":
            if sub_island_ids is None:
                raise ValueError(
                    "bootstrap_method='cluster' requires island_ids"
                )
            unique_ids = np.unique(sub_island_ids)
            K = len(unique_ids)
            island_to_rows = {
                int(iid): np.where(sub_island_ids == iid)[0]
                for iid in unique_ids
            }
            def _cluster_iter():
                for _ in range(n_boot):
                    sampled = rng.choice(unique_ids, size=K, replace=True)
                    yield np.concatenate([island_to_rows[int(iid)] for iid in sampled])
            sample_idx_iter = _cluster_iter()
        else:
            raise ValueError(f"Unknown bootstrap_method: {bootstrap_method!r}")
        for idx in sample_idx_iter:
            try:
                pfit = fit_qr_full(Y[idx], Z[idx], hour[idx], month[idx],
                                   tau=tau, n_boot=0, seed=0)
                yfit = fit_qr_full(Y[idx], Z[idx], hour[idx], month[idx],
                                   year=year[idx], tau=tau, n_boot=0, seed=0)
            except Exception:
                continue
            d = pfit.z_slope - yfit.z_slope
            if np.isfinite(d):
                diffs.append(d)
        if len(diffs) < 20:
            ci = (float("nan"), float("nan"))
        else:
            arr = np.asarray(diffs)
            ci = (float(np.quantile(arr, 0.025)), float(np.quantile(arr, 0.975)))
        out[f"tau_{tau:.2f}"] = {
            "primary_z_slope": _nan_to_none(primary_fit.z_slope),
            "year_fe_z_slope": _nan_to_none(yfe_fit.z_slope),
            "secular_component_point": _nan_to_none(point_secular),
            "secular_component_ci": [_nan_to_none(ci[0]), _nan_to_none(ci[1])],
            "n_boot_converged": int(len(diffs)),
        }
    return out


def run_year_fe_diagnostic(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    pnode_label: str,
    response_col: str,
    z_col: str = "dom_load_gradient_abs_mw_per_min",
    taus: tuple[float, ...] = (0.90, 0.95, 0.99),
    pct_list: tuple[float, ...] = (0.90, 0.95, 0.99),
    n_boot: int = 200,
    seed: int = 0,
    bootstrap_method: str = "pair",
    island_ids: pd.Series | None = None,
) -> None:
    """Run three-layer year-FE diagnostic for one pnode. Writes JSON at out_path."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    layer1 = compute_raw_per_year_stats(
        panel, response_col=response_col,
        year_col="datetime_beginning_ept",
        pct_list=pct_list,
    )
    layer2 = bootstrap_year_dummy_coefs(
        panel, response_col=response_col, z_col=z_col,
        year_col="datetime_beginning_ept",
        taus=taus, n_boot=n_boot, seed=seed,
        bootstrap_method=bootstrap_method, island_ids=island_ids,
    )
    layer3 = bootstrap_secular_component(
        panel, response_col=response_col, z_col=z_col,
        year_col="datetime_beginning_ept",
        taus=taus, n_boot=n_boot, seed=seed + 50,
        bootstrap_method=bootstrap_method, island_ids=island_ids,
    )

    payload = {
        "pnode_label": pnode_label,
        "response_col": response_col,
        "z_col": z_col,
        "taus": list(taus),
        "n_total_panel": int(len(panel)),
        "n_after_dropna": int(panel.dropna(subset=[response_col, z_col]).shape[0]),
        "layer1_raw_per_year": layer1,
        "layer2_year_dummy_bootstrap": layer2,
        "layer3_secular_component_bootstrap": layer3,
        "layer2_label": "PER-YEAR LEVEL SHIFTS — descriptive supplementary, not a trend test",
        "layer3_label": "SECULAR-COMPONENT TREND TEST — primary_z_slope - year_fe_z_slope per τ",
    }
    out_path.write_text(json.dumps(payload, indent=2))


def write_cross_pnode_summary(out_dir: Path, pnode_labels: tuple[str, ...]) -> None:
    """Aggregate per-pnode year_fe_diagnostic JSONs into one flat table."""
    rows: list[dict] = []
    for label in pnode_labels:
        path = out_dir / f"{label}.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text())
        for tau_key, l3 in payload.get("layer3_secular_component_bootstrap", {}).items():
            if isinstance(l3, dict) and "secular_component_point" in l3:
                rows.append({
                    "pnode_label": label,
                    "tau_key": tau_key,
                    "primary_z_slope": l3["primary_z_slope"],
                    "year_fe_z_slope": l3["year_fe_z_slope"],
                    "secular_component_point": l3["secular_component_point"],
                    "secular_component_ci": l3["secular_component_ci"],
                })
    (out_dir / "cross_pnode_summary.json").write_text(
        json.dumps({"rows": rows}, indent=2)
    )
