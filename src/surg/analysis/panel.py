"""Load and validate analysis_panel.parquet for the analysis layer."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.preprocessing.schema import validate_panel


def load_panel(path: Path) -> pd.DataFrame:
    """Load the analysis panel from `path` and validate its schema."""
    df = pd.read_parquet(path)
    validate_panel(df)
    return df


def select_filtered_subset(df: pd.DataFrame) -> pd.DataFrame:
    """Return only rows that pass the proposal filter (shoulder + 2-5 AM)."""
    return df[df["passes_proposal_filter"].fillna(False).astype(bool)].copy()
