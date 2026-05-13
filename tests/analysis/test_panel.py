from pathlib import Path

import pandas as pd
import pytest


def test_load_panel_returns_dataframe(tmp_path: Path):
    from surg.analysis.panel import load_panel
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    # Write a minimal-but-valid panel
    df = pd.DataFrame({col: [None, None] for col in EXPECTED_COLUMNS})
    df["datetime_beginning_ept"] = pd.to_datetime(
        ["2024-07-15T03:00:00", "2024-07-15T04:00:00"]
    )
    out = tmp_path / "analysis_panel.parquet"
    df.to_parquet(out)

    loaded = load_panel(out)
    assert isinstance(loaded, pd.DataFrame)
    assert len(loaded) == 2


def test_load_panel_validates_schema(tmp_path: Path):
    from surg.analysis.panel import load_panel

    # Write a panel missing required columns
    df = pd.DataFrame({"datetime_beginning_ept": pd.to_datetime(["2024-07-15"])})
    out = tmp_path / "bad_panel.parquet"
    df.to_parquet(out)

    with pytest.raises(ValueError, match="missing expected columns"):
        load_panel(out)


def test_select_filtered_subset_returns_passing_rows():
    from surg.analysis.panel import select_filtered_subset
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None]*3 for col in EXPECTED_COLUMNS})
    df["datetime_beginning_ept"] = pd.to_datetime(
        ["2024-07-15T03:00:00", "2024-03-15T03:00:00", "2024-03-15T14:00:00"]
    )
    df["passes_proposal_filter"] = [False, True, False]

    out = select_filtered_subset(df)
    assert len(out) == 1
    assert out["passes_proposal_filter"].iloc[0]
