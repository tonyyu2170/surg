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


def test_dollar_amounts_survive_rendering_verbatim():
    # Literal "$" must not be parsed as mathtext: captions in this set carry
    # amounts like "$9.56 / $8.81" and would otherwise render garbled.
    fig, ax = plt.subplots()
    label = "p90 by year: $9.56 / $8.81 / $13.46"
    t = ax.set_title(label)
    fig.canvas.draw()
    assert t.get_text() == label
    assert not plt.rcParams["text.parse_math"]
    plt.close(fig)


def test_finish_keeps_caption_clear_of_tick_labels(tmp_path):
    # The caption must not collide with the x tick labels, which render BELOW
    # the axes box -- so measuring only the caption's height is insufficient.
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot([0, 1, 2], [1, 3, 2])
    caption = ("Congestion p90 by year: 2023 $9.56 / 2024 $8.81 / "
               "2025 $13.46 / 2026 $63.56")
    out = tmp_path / "f.png"
    _style.finish(fig, out, footer="Source: p.parquet | n=1 | 5-min",
                  caption=caption)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    caption_text = [t for t in fig.texts][-1]
    cap_top = caption_text.get_window_extent(renderer).y1
    ticks = [lbl for lbl in ax.get_xticklabels() if lbl.get_text()]
    assert ticks, "no x tick labels to test against"
    tick_bottom = min(lbl.get_window_extent(renderer).y0 for lbl in ticks)
    assert tick_bottom >= cap_top, (
        f"caption top ({cap_top:.1f}px) overlaps lowest tick label "
        f"({tick_bottom:.1f}px)")
    plt.close(fig)
