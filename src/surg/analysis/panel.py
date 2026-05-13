"""Load and validate analysis_panel.parquet for the analysis layer."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from surg.preprocessing.schema import SCHEMA_VERSION, validate_panel


def load_panel(path: Path) -> pd.DataFrame:
    """Load the analysis panel from `path` and validate its schema."""
    _check_schema_version(path)
    df = pd.read_parquet(path)
    validate_panel(df)
    return df


def _check_schema_version(path: Path) -> None:
    """Raise ValueError if the parquet file's schema_version doesn't match SCHEMA_VERSION."""
    meta = pq.read_schema(path).metadata or {}
    raw = meta.get(b"schema_version")
    if raw is None:
        raise ValueError(
            f"schema_version metadata missing from {path}; "
            f"expected {SCHEMA_VERSION}. Rebuild the panel with surg-prep."
        )
    file_version = raw.decode()
    if file_version != str(SCHEMA_VERSION):
        raise ValueError(
            f"schema_version mismatch in {path}: file has {file_version!r}, "
            f"code expects {SCHEMA_VERSION}. Rebuild the panel with surg-prep."
        )


def select_filtered_subset(df: pd.DataFrame) -> pd.DataFrame:
    """Return only rows that pass the proposal filter (shoulder + 2-5 AM).

    NaN values in `passes_proposal_filter` are treated as False.
    """
    return df[df["passes_proposal_filter"].fillna(False).astype(bool)].copy()
