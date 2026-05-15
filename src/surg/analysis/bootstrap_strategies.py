"""Pure island cluster bootstrap (sub-q1 item #8).

The proposal-filter creates 3-hour islands (2-5 AM) separated by
21-hour gaps. Pair-bootstrap is invalid for the joint 5-min panel
(within-island autocorrelation in 5-min Z and LMP); naive block
bootstrap is invalid (blocks would cross the 21-hour gap boundaries).
Pure island cluster bootstrap (Cameron-Gelbach-Miller-style) is the
standard treatment: resample whole 3-hour islands with replacement.

bootstrap_dispatch(...) is the injection point used by items #1-4 +
#6 modules: each module's existing pair-bootstrap call site is
replaced with a dispatch call so the existing hourly behavior is
preserved (method='pair') while the 5-min companion can opt into
cluster bootstrap (method='cluster').
"""
from __future__ import annotations

from typing import Callable, Optional

import numpy as np
import pandas as pd


def identify_islands(
    timestamps: pd.DatetimeIndex,
    filter_mask: pd.Series,
    gap_threshold_minutes: int = 10,
) -> pd.Series:
    """Assign each in-filter row an integer island id.

    Rows separated by a gap > `gap_threshold_minutes` are in different
    islands. The first row always starts island 0.

    Returns a Series of int island ids, indexed like `filter_mask`.
    Caller pre-filters: this function does not handle out-of-filter
    rows (it expects the filter_mask of the already-filtered rows).
    """
    if len(timestamps) != len(filter_mask):
        raise ValueError("timestamps and filter_mask length mismatch")
    ts = pd.Series(timestamps)
    diffs_min = ts.diff().dt.total_seconds() / 60.0
    island_break = diffs_min > gap_threshold_minutes
    island_break.iloc[0] = True
    island_ids = island_break.cumsum() - 1
    island_ids.index = filter_mask.index
    return island_ids.astype(int)


def island_cluster_bootstrap(
    df: pd.DataFrame,
    island_ids: pd.Series,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Resample whole islands with replacement; return resampled DataFrame.

    K = number of unique island ids. We draw K islands with replacement
    and concat their rows in the sampled order.
    """
    if len(df) != len(island_ids):
        raise ValueError("df and island_ids length mismatch")
    unique_islands = island_ids.unique()
    K = len(unique_islands)
    sampled = rng.choice(unique_islands, size=K, replace=True)
    groups = {iid: df[island_ids == iid] for iid in unique_islands}
    pieces = [groups[iid] for iid in sampled]
    return pd.concat(pieces, ignore_index=True)


def bootstrap_dispatch(
    method: str,
    df: pd.DataFrame,
    stat_fn: Callable[[pd.DataFrame], np.ndarray],
    n_boot: int,
    rng: np.random.Generator,
    island_ids: Optional[pd.Series] = None,
) -> np.ndarray:
    """Run `n_boot` bootstrap replicates and return their statistics.

    `stat_fn` must take a DataFrame and return a 1-D np.ndarray. Items
    #1-4 fit regressions producing vector-valued statistics
    (intercept + slope, etc.); item #6 produces a scalar via
    `np.array([p_hat])`. Returns array of shape (n_boot, n_stats),
    where n_stats is the length of stat_fn's return value on the
    unbootstrapped sample.

    method:
        "pair"    — resample row indices with replacement (for IID)
        "cluster" — resample whole islands with replacement (requires
                    `island_ids` aligned with `df`)
    """
    first = np.atleast_1d(np.asarray(stat_fn(df)))
    n_stats = len(first)
    replicates = np.empty((n_boot, n_stats))

    for b in range(n_boot):
        if method == "pair":
            idx = rng.choice(len(df), size=len(df), replace=True)
            boot_df = df.iloc[idx].reset_index(drop=True)
        elif method == "cluster":
            if island_ids is None:
                raise ValueError("cluster method requires island_ids")
            boot_df = island_cluster_bootstrap(df, island_ids, rng)
        else:
            raise ValueError(f"Unknown bootstrap method: {method!r}")
        out = np.atleast_1d(np.asarray(stat_fn(boot_df)))
        if len(out) != n_stats:
            raise ValueError(
                f"stat_fn returned length {len(out)} on bootstrap rep {b}, "
                f"expected {n_stats} from the unbootstrapped sample"
            )
        replicates[b] = out

    return replicates
