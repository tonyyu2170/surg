"""Robustness checks — subsample bootstrap and leave-one-season-out."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.tar import fit_tar


def subsample_bootstrap(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    n_reps: int = 200,
    sample_frac: float = 0.8,
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    seed: int = 42,
) -> None:
    """Refit TAR on `n_reps` random subsamples (each of `sample_frac` rows).
    Write the resulting c_hat distribution to a parquet file."""
    panel = panel.sort_values("datetime_beginning_ept").reset_index(drop=True)
    # Same gap guard as run_tar — shift(1) walks rows not time; misaligned
    # lags would silently corrupt every c_hat in the bootstrap distribution.
    deltas = panel["datetime_beginning_ept"].diff().dropna()
    if not (deltas == pd.Timedelta(hours=1)).all():
        n_gaps = int((deltas != pd.Timedelta(hours=1)).sum())
        raise ValueError(
            f"panel has {n_gaps} non-hourly gap(s); _Y_lag would be misaligned. "
            f"Rebuild via surg-prep, or pre-fill gaps."
        )
    panel["_Y_lag"] = panel[response_col].shift(1)
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[response_col, "_Y_lag", threshold_col])

    Y_all = subset[response_col].to_numpy()
    Y_lag_all = subset["_Y_lag"].to_numpy()
    Z_all = subset[threshold_col].to_numpy()
    n = len(Y_all)
    k = int(sample_frac * n)

    rng = np.random.default_rng(seed)
    rows = []
    for rep in range(n_reps):
        idx = rng.choice(n, size=k, replace=False)
        result = fit_tar(Y_all[idx], Y_lag_all[idx], Z_all[idx])
        rows.append({"rep": rep, "c_hat": result.c_hat,
                     "n_low": result.n_low, "n_high": result.n_high})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_path, index=False)


def leave_one_season_out(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    season_col: str = "_season_id",
    response_col: str = "congestion_price_rt_cluster_mean",
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
) -> None:
    """For each unique season, fit TAR on all OTHER seasons. Write
    {season_dropped, c_hat} rows to parquet."""
    panel = panel.sort_values("datetime_beginning_ept").reset_index(drop=True)
    # Gap guard — shift(1) walks rows not time; misaligned lags would silently
    # corrupt every c_hat in the leave-one-out distribution.
    deltas = panel["datetime_beginning_ept"].diff().dropna()
    if not (deltas == pd.Timedelta(hours=1)).all():
        n_gaps = int((deltas != pd.Timedelta(hours=1)).sum())
        raise ValueError(
            f"panel has {n_gaps} non-hourly gap(s); _Y_lag would be misaligned. "
            f"Rebuild via surg-prep, or pre-fill gaps."
        )
    panel["_Y_lag"] = panel[response_col].shift(1)
    subset = panel[panel["passes_proposal_filter"].fillna(False).astype(bool)].copy()
    subset = subset.dropna(subset=[response_col, "_Y_lag", threshold_col, season_col])

    seasons = sorted(subset[season_col].unique())
    rows = []
    for s in seasons:
        kept = subset[subset[season_col] != s]
        if len(kept) < 100:
            continue
        result = fit_tar(
            Y=kept[response_col].to_numpy(),
            Y_lag=kept["_Y_lag"].to_numpy(),
            Z=kept[threshold_col].to_numpy(),
        )
        rows.append({"season_dropped": s, "c_hat": result.c_hat,
                     "n_low": result.n_low, "n_high": result.n_high})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_path, index=False)
