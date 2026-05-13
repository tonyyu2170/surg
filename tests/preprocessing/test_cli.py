from pathlib import Path

import pandas as pd
import pytest


def test_help_exits_zero(capsys):
    from surg.preprocessing.build import main
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "surg-prep" in out


def test_main_writes_panel_to_output_path(tmp_path: Path):
    from surg.preprocessing.build import main
    # Seed minimal raw using the helper from test_build.py
    from tests.preprocessing.test_build import _seed_minimal_raw

    _seed_minimal_raw(tmp_path)
    out = tmp_path / "interim" / "analysis_panel.parquet"
    rc = main([
        "--data-root", str(tmp_path),
        "--output", str(out),
    ])
    assert rc == 0
    assert out.exists()
    df = pd.read_parquet(out)
    assert len(df) >= 1


def test_main_refuses_to_overwrite_without_force(tmp_path: Path):
    from surg.preprocessing.build import main
    out = tmp_path / "panel.parquet"
    out.write_text("dummy")  # exists
    rc = main([
        "--data-root", str(tmp_path),
        "--output", str(out),
    ])
    assert rc == 2


def test_main_force_overwrites(tmp_path: Path):
    from surg.preprocessing.build import main
    from tests.preprocessing.test_build import _seed_minimal_raw

    _seed_minimal_raw(tmp_path)
    out = tmp_path / "interim" / "panel.parquet"
    out.parent.mkdir(parents=True)
    out.write_text("dummy")
    rc = main([
        "--data-root", str(tmp_path),
        "--output", str(out),
        "--force",
    ])
    assert rc == 0
    df = pd.read_parquet(out)
    assert len(df) >= 1
