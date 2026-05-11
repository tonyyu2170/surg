"""Orchestrator: pull a feed for a date range, writing per-chunk parquet files.

Composes `client.PJMClient` + `chunking.date_chunks` + `storage.*`.
Two feed shapes are supported:
  - Nodal LMP feeds (rt_hrl_lmps, rt_fivemin_hrl_lmps, da_hrl_lmps):
    pass `pnode_ids` (semicolon-packed). `row_is_current=true` is forced.
  - Zonal feeds (hrl_load_metered): pass `zone="DOM"` instead.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from surg.acquisition.chunking import date_chunks
from surg.acquisition.client import PJMClient
from surg.acquisition.storage import chunk_exists, write_chunk

# Feeds that follow LMP versioning semantics.
_LMP_FEEDS = frozenset(
    {"rt_hrl_lmps", "rt_fivemin_hrl_lmps", "da_hrl_lmps"}
)


def pull_feed(
    feed: str,
    start: date,
    end: date,
    *,
    pnode_ids: Sequence[int] | None,
    group_label: str,
    client: PJMClient,
    data_root: Path,
    zone: str | None = None,
    force: bool = False,
    max_days_per_chunk: int = 365,
) -> list[Path]:
    """Pull `feed` for [start, end] in calendar-year chunks.

    Returns the list of parquet paths written this run (skipped chunks
    are excluded from the return value).
    """
    written: list[Path] = []

    for chunk_start, chunk_end in date_chunks(start, end, max_days=max_days_per_chunk):
        if not force and chunk_exists(data_root, feed, group_label, chunk_start, chunk_end):
            continue

        params = _build_params(feed, chunk_start, chunk_end, pnode_ids, zone)
        rows = list(client.get_feed(feed, params))
        df = pd.DataFrame(rows)
        path = write_chunk(
            data_root=data_root,
            feed=feed,
            group_label=group_label,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            df=df,
        )
        written.append(path)

    return written


def _build_params(
    feed: str,
    chunk_start: date,
    chunk_end: date,
    pnode_ids: Sequence[int] | None,
    zone: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "datetime_beginning_ept": (
            f"{chunk_start.isoformat()} 00:00 to "
            f"{chunk_end.isoformat()} 23:59"
        ),
        "sort": "datetime_beginning_ept",
        "order": "Asc",
    }
    if pnode_ids:
        params["pnode_id"] = ";".join(str(p) for p in pnode_ids)
    if zone:
        params["zone"] = zone
    if feed in _LMP_FEEDS:
        params["row_is_current"] = "true"
    return params
