from datetime import date
from pathlib import Path

import pandas as pd

from surg.acquisition.storage import (
    chunk_exists,
    chunk_path,
    write_chunk,
)


def test_chunk_path_layout(tmp_path: Path):
    p = chunk_path(
        data_root=tmp_path,
        feed="rt_hrl_lmps",
        group_label="dom_targets",
        chunk_start=date(2026, 4, 1),
        chunk_end=date(2026, 4, 30),
    )
    assert p == tmp_path / "rt_hrl_lmps" / "2026" / "dom_targets__2026-04-01_to_2026-04-30.parquet"


def test_chunk_path_uses_chunk_start_year(tmp_path: Path):
    # Chunks never cross calendar years (per chunking.py invariant), so the
    # year in the path is the chunk_start year.
    p = chunk_path(tmp_path, "rt_hrl_lmps", "dom", date(2024, 12, 31), date(2024, 12, 31))
    assert "2024" in p.parts


def test_chunk_exists_false_then_true(tmp_path: Path):
    args = dict(
        data_root=tmp_path,
        feed="rt_hrl_lmps",
        group_label="dom",
        chunk_start=date(2026, 4, 15),
        chunk_end=date(2026, 4, 15),
    )
    assert chunk_exists(**args) is False

    df = pd.DataFrame({"a": [1, 2, 3]})
    written = write_chunk(df=df, **args)
    assert written.exists()
    assert chunk_exists(**args) is True


def test_write_chunk_creates_parent_dirs(tmp_path: Path):
    df = pd.DataFrame({"x": [1.0]})
    out = write_chunk(
        data_root=tmp_path,
        feed="hrl_load_metered",
        group_label="dom",
        chunk_start=date(2024, 1, 1),
        chunk_end=date(2024, 12, 31),
        df=df,
    )
    assert out.parent.is_dir()
    # Round-trip the data
    loaded = pd.read_parquet(out)
    assert list(loaded["x"]) == [1.0]


def test_write_chunk_overwrites_existing(tmp_path: Path):
    args = dict(
        data_root=tmp_path,
        feed="rt_hrl_lmps",
        group_label="dom",
        chunk_start=date(2026, 1, 1),
        chunk_end=date(2026, 1, 1),
    )
    write_chunk(df=pd.DataFrame({"v": [1]}), **args)
    write_chunk(df=pd.DataFrame({"v": [2]}), **args)
    loaded = pd.read_parquet(chunk_path(**args))
    assert list(loaded["v"]) == [2]
