from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest


def test_load_panel_returns_dataframe(tmp_path: Path):
    from surg.analysis.panel import load_panel
    from surg.preprocessing.build import write_panel
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None, None] for col in EXPECTED_COLUMNS})
    df["datetime_beginning_ept"] = pd.to_datetime(
        ["2024-07-15T03:00:00", "2024-07-15T04:00:00"]
    )
    out = tmp_path / "analysis_panel.parquet"
    write_panel(df, out)

    loaded = load_panel(out)
    assert isinstance(loaded, pd.DataFrame)
    assert len(loaded) == 2


def test_load_panel_validates_schema(tmp_path: Path):
    from surg.analysis.panel import load_panel
    from surg.preprocessing.build import write_panel

    df = pd.DataFrame({"datetime_beginning_ept": pd.to_datetime(["2024-07-15"])})
    out = tmp_path / "bad_panel.parquet"
    write_panel(df, out)

    with pytest.raises(ValueError, match="missing expected columns"):
        load_panel(out)


def test_load_panel_rejects_mismatched_schema_version(tmp_path: Path):
    from surg.analysis.panel import load_panel
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None, None] for col in EXPECTED_COLUMNS})
    df["datetime_beginning_ept"] = pd.to_datetime(
        ["2024-07-15T03:00:00", "2024-07-15T04:00:00"]
    )
    table = pa.Table.from_pandas(df, preserve_index=False)
    # Wholesale replace drops the pandas key intentionally — the file fails the
    # version check before pd.read_parquet runs, so pandas metadata is irrelevant.
    table = table.replace_schema_metadata({b"schema_version": b"99"})
    out = tmp_path / "wrong_version.parquet"
    pq.write_table(table, out)

    with pytest.raises(ValueError, match="schema_version mismatch"):
        load_panel(out)


def test_load_panel_rejects_missing_schema_version(tmp_path: Path):
    from surg.analysis.panel import load_panel
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None, None] for col in EXPECTED_COLUMNS})
    df["datetime_beginning_ept"] = pd.to_datetime(
        ["2024-07-15T03:00:00", "2024-07-15T04:00:00"]
    )
    out = tmp_path / "no_metadata.parquet"
    df.to_parquet(out)  # raw pandas write — no schema_version stamped

    with pytest.raises(ValueError, match="schema_version metadata missing"):
        load_panel(out)


def test_select_filtered_subset_returns_passing_rows():
    from surg.analysis.panel import select_filtered_subset
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None]*4 for col in EXPECTED_COLUMNS})
    df["datetime_beginning_ept"] = pd.to_datetime(
        ["2024-07-15T03:00:00", "2024-03-15T03:00:00",
         "2024-03-15T14:00:00", "2024-03-15T04:00:00"]
    )
    # Index 1: True (kept). Index 3: NaN (treated as False; excluded — exercises the fillna defense).
    df["passes_proposal_filter"] = [False, True, False, None]

    out = select_filtered_subset(df)
    assert len(out) == 1
    assert bool(out["passes_proposal_filter"].iloc[0]) is True
