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


def test_symlog_axis_tick_labels_are_not_raw_mathtext():
    # rcParams sets text.parse_math=False so literal "$" in captions renders
    # correctly. The cost is that matplotlib's symlog/log tick formatter
    # emits mathtext ("$\\mathdefault{10^{2}}$"), which then renders as that
    # literal string on the axis. symlog_axis must install a plain formatter.
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [0.5, 50, 500])
    _style.symlog_axis(ax, linthresh=1.0, label="Price ($)")
    fig.canvas.draw()
    labels = [t.get_text() for t in ax.get_yaxis().get_ticklabels()]
    assert labels, "no tick labels rendered"
    for text in labels:
        assert "mathdefault" not in text, f"raw mathtext leaked: {text!r}"
        assert "^" not in text, f"unrendered exponent markup: {text!r}"
    plt.close(fig)


def test_finish_keeps_long_caption_inside_the_figure_width(tmp_path):
    # matplotlib's wrap=True overshoots: an F3-length caption rendered ~32px
    # past the right edge of an 11in figure, clipping the last word of a
    # line. finish() must wrap to the figure box, however long the caption.
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.plot([0, 1], [0, 1])
    caption = (
        "Congestion p90 by year: 2023 $9.56 / 2024 $8.81 / 2025 $13.46 / "
        "2026 $60.76. Panel (c): system energy price is locationally uniform "
        "across PJM, so its 2026 rise is NOT a Northern-Virginia phenomenon. "
        "Daily medians on a symlog axis; linear axes would flatten everything "
        "before 2026 into a baseline smear.")
    out = tmp_path / "wrapped.png"
    _style.finish(fig, out, footer="Source: p.parquet | n=1 | 5-min",
                  caption=caption)
    renderer = fig.canvas.get_renderer()
    texts = [t for t in fig.texts if "Congestion p90" in t.get_text()]
    assert texts, "caption artist not found"
    right = texts[0].get_window_extent(renderer).x1
    width = fig.get_window_extent().width
    assert right <= width, (
        f"caption overflows the figure by {right - width:.1f}px")
    plt.close(fig)


def test_finish_fits_an_inference_scale_caption():
    # F5/F6/F8 captions carry ARTIFACT_NOTE plus ZONAL_DISCLOSURE plus their
    # own inference prose -- materially longer than F3's. The wrap loop must
    # still land inside the figure.
    import matplotlib.pyplot as plt
    import tempfile
    fig, ax = plt.subplots(figsize=(11, 8.5))
    ax.plot([0, 1], [0, 1])
    caption = (
        "Pre-registered vs load-controlled z_slope at tau=0.90 and tau=0.95. "
        "Under a load-level control the estimate is negative in all 10 cells; "
        "in the 8 cells where the pre-registered estimate was positive the "
        "sign reverses; the negative estimate excludes zero in 5. "
        + _style.ARTIFACT_NOTE + " " + _style.ZONAL_DISCLOSURE)
    with tempfile.TemporaryDirectory() as td:
        _style.finish(fig, Path(td) / "f.png",
                      footer="Source: p.parquet | n=352,467 | 5-min",
                      caption=caption)
    renderer = fig.canvas.get_renderer()
    t = [x for x in fig.texts if "Pre-registered" in x.get_text()][0]
    assert t.get_window_extent(renderer).x1 <= fig.get_window_extent().width
    plt.close(fig)


def test_wrap_to_figure_raises_rather_than_clipping():
    # An impossible target must fail loudly. Returning a still-overflowing
    # caption is the exact failure this helper exists to prevent.
    import matplotlib.pyplot as plt
    import pytest
    fig = plt.figure(figsize=(11, 8.5))
    t = fig.text(0.01, 0.005, "x", fontsize=7)
    fig.canvas.draw()
    with pytest.raises(RuntimeError, match="could not wrap caption"):
        _style._wrap_to_figure(fig, t, "word " * 400, limit_px=5.0)
    plt.close(fig)
