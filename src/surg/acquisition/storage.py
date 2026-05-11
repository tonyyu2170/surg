"""Filesystem layout for raw acquisition output.

Layout:
    <data_root>/<feed>/<year>/<group_label>__<start>_to_<end>.parquet

Skip-if-exists is the resumability mechanism. A chunk that has been
written is treated as complete; pass `force=True` to the orchestrator
to override.
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import pandas as pd


def chunk_path(
    data_root: Path,
    feed: str,
    group_label: str,
    chunk_start: date,
    chunk_end: date,
) -> Path:
    """Return the deterministic path for a chunk's parquet file."""
    fname = f"{group_label}__{chunk_start.isoformat()}_to_{chunk_end.isoformat()}.parquet"
    return data_root / feed / str(chunk_start.year) / fname


def chunk_exists(
    data_root: Path,
    feed: str,
    group_label: str,
    chunk_start: date,
    chunk_end: date,
) -> bool:
    """Return True if a chunk parquet already exists at its canonical path."""
    return chunk_path(data_root, feed, group_label, chunk_start, chunk_end).exists()


def write_chunk(
    data_root: Path,
    feed: str,
    group_label: str,
    chunk_start: date,
    chunk_end: date,
    df: pd.DataFrame,
) -> Path:
    """Write `df` to the chunk's path, creating parent dirs.

    Atomic via temp-file + `os.replace` so an interrupted write
    never leaves a partial parquet at the canonical path.
    Overwrites any existing file.
    """
    out = chunk_path(data_root, feed, group_label, chunk_start, chunk_end)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, out)
    return out
