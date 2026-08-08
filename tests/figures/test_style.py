from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from scripts.figures import _style


def test_palette_has_a_distinct_color_per_named_series():
    colors = list(_style.COLOR.values())
    assert len(colors) == len(set(colors)), "palette colors must be distinct"
    assert all(c.startswith("#") and len(c) == 7 for c in colors)


def test_provenance_returns_all_four_required_fields():
    line = _style.provenance(
        source="analysis_panel_5min.parquet",
        n=352467,
        window="2023-02-07 to 2026-06-29",
        spec="descriptive",
        resolution="5-min",
    )
    assert "analysis_panel_5min.parquet" in line
    assert "352,467" in line
    assert "2023-02-07 to 2026-06-29" in line
    assert "descriptive" in line
    assert "5-min" in line


def test_provenance_requires_resolution_label():
    # Resolution must be explicit on every figure (the c4a64e7 bug class).
    with pytest.raises(ValueError, match="resolution"):
        _style.provenance(
            source="p.parquet", n=1, window="w", spec="s", resolution=""
        )


def test_finish_writes_a_png(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    out = tmp_path / "fig.png"
    _style.finish(fig, out, footer="src=x | n=1 | 5-min")
    plt.close(fig)
    assert out.exists() and out.stat().st_size > 0
