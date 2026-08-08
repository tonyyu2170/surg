import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.figures import descriptive as D


def _monthly_json(tmp_path):
    rows = []
    for i, m in enumerate(pd.period_range("2023-02", "2026-06", freq="M")):
        load = 14000 + 60 * i
        p90 = 25.0
        rows.append({"month": str(m), "mean_load_mw": load,
                     "ramp_p90_mw_per_min": p90,
                     "ramp_p90_pct_of_load": 100 * p90 / load,
                     "n": 8000})
    p = tmp_path / "monthly.json"
    p.write_text(json.dumps({"rows": rows, "resolution": "5-min"}))
    return p


def test_f1_reports_growth_and_flat_ramp(tmp_path):
    d = D.prepare_f1(_monthly_json(tmp_path))
    assert d["n_months"] == 41
    assert d["load_growth_pct"] > 0
    # ramp held flat in the fixture, so normalised ramp must fall
    assert d["ramp_pct_first_year"] > d["ramp_pct_last_year"]


def test_f1_growth_is_like_for_like_not_first_to_last_month(tmp_path):
    # A panel with ZERO real growth but a strong seasonal cycle must report
    # ~0% growth. A naive first-month-to-last-month difference would report
    # a large spurious number.
    rows = []
    for m in pd.period_range("2023-02", "2026-06", freq="M"):
        seasonal = 3000 * np.cos(2 * np.pi * (m.month - 7) / 12.0)
        load = 14000 + seasonal          # no trend at all
        rows.append({"month": str(m), "mean_load_mw": load,
                     "ramp_p90_mw_per_min": 25.0,
                     "ramp_p90_pct_of_load": 100 * 25.0 / load, "n": 8000})
    p = tmp_path / "seasonal.json"
    p.write_text(json.dumps({"rows": rows, "resolution": "5-min"}))
    d = D.prepare_f1(p)
    assert abs(d["load_growth_pct"]) < 1.0, (
        f"seasonal-only panel reported {d['load_growth_pct']:.1f}% growth; "
        "growth is not being computed like-for-like")
    assert d["growth_basis_months"], "no common-month basis recorded"


def test_f1_carries_a_trend_test(tmp_path):
    d = D.prepare_f1(_monthly_json(tmp_path))
    for k in ("ols_slope_per_month", "ols_p_value",
              "spearman_rho", "spearman_p_value"):
        assert k in d and np.isfinite(d[k])


def test_f1_plot_writes_png(tmp_path):
    out = tmp_path / "F1.png"
    D.plot_f1(D.prepare_f1(_monthly_json(tmp_path)), out)
    assert out.exists() and out.stat().st_size > 0


def _panel_5min(n=20000, seed=1):
    rng = np.random.default_rng(seed)
    t = pd.date_range("2023-02-07", periods=n, freq="5min")
    load = 14000 + 6000 * rng.random(n)
    z = np.abs(rng.normal(10, 5, n))
    energy = 20 + (load - 14000) / 200 + rng.normal(0, 2, n)
    # Congestion switches on in the top load decile only. Derive the
    # threshold from the data rather than hardcoding it: a fixed 19000 MW
    # sits at the 83rd percentile of this uniform load, straddling deciles 9
    # and 10, so decile 9 inherits the high-congestion draw and the switch
    # reads as a slope.
    cong = np.where(load > np.quantile(load, 0.9),
                    rng.gamma(2, 40, n), rng.gamma(1, 0.4, n))
    return pd.DataFrame({
        "datetime_beginning_ept": t,
        "dom_load_mw": load,
        "dom_load_gradient_abs_mw_per_min": z,
        "congestion_price_rt_cluster_mean": cong,
        "system_energy_price_rt_cluster_mean": energy,
        "total_lmp_rt_cluster_mean": energy + cong,
    })


def test_f2_decile_labels_match_the_aggregated_rows():
    # qcut(duplicates="drop") can yield <10 bins on a variable with a point
    # mass; the labels must track the actual rows rather than assume ten.
    d = D.prepare_f2(_panel_5min())
    for col in ("by_load", "by_ramp_top_tercile"):
        s = d[col]
        assert 2 <= len(s["decile"]) <= 10
        assert len(s["decile"]) == len(s["energy_median"]) == len(s["cong_p95"])


def test_f2_system_energy_rises_with_load():
    d = D.prepare_f2(_panel_5min())
    e = d["by_load"]["energy_median"]
    assert e[-1] > e[0]


def test_f2_congestion_is_a_switch_not_a_slope():
    d = D.prepare_f2(_panel_5min())
    p95 = d["by_load"]["cong_p95"]
    # top decile dominates: last decile p95 far exceeds the 9th
    assert p95[-1] > 3 * p95[-2]


def test_f2_ramp_column_holds_load_roughly_fixed():
    d = D.prepare_f2(_panel_5min())
    loads = d["by_ramp_top_tercile"]["mean_load_mw"]
    assert (max(loads) - min(loads)) / np.mean(loads) < 0.15


def test_f2_plot_writes_png(tmp_path):
    out = tmp_path / "F2.png"
    D.plot_f2(D.prepare_f2(_panel_5min()), out)
    assert out.exists() and out.stat().st_size > 0


def test_f3_returns_daily_series_for_three_components():
    d = D.prepare_f3(_panel_5min())
    for k in ("total_lmp", "congestion", "system_energy"):
        assert len(d[k]) == len(d["dates"])


def test_f3_dates_align_with_the_aggregated_series():
    # The date axis and the plotted values must come from the same
    # aggregation, not from two separately-ordered views of the groupby.
    p = _panel_5min()
    d = D.prepare_f3(p)
    day = pd.to_datetime(p["datetime_beginning_ept"]).dt.floor("D")
    expected = p.groupby(day)["congestion_price_rt_cluster_mean"].median()
    assert [pd.Timestamp(x) for x in d["dates"]] == list(expected.index)
    assert d["congestion"] == expected.tolist()


def test_f3_reports_congestion_p90_by_year():
    d = D.prepare_f3(_panel_5min())
    assert d["cong_p90_by_year"]
    for y, v in d["cong_p90_by_year"].items():
        assert int(y) >= 2023 and v >= 0


def test_f3_plot_writes_png(tmp_path):
    out = tmp_path / "F3.png"
    D.plot_f3(D.prepare_f3(_panel_5min()), out)
    assert out.exists() and out.stat().st_size > 0


def test_f2_energy_panels_share_a_scale(monkeypatch):
    # (a) and (b) plot the same quantity. If (b) autoscales to its own ~$4
    # range, a 10% decline renders as a collapse comparable to (a)'s real
    # $17->$62 climb -- overstating the ramp effect in the direction that
    # flatters the thesis. Guard the shared scale.
    import matplotlib.pyplot as plt
    captured = {}

    def _record(fig, out_path, **kw):
        captured["axes"] = fig.get_axes()

    monkeypatch.setattr(D.S, "finish", _record)
    D.plot_f2(D.prepare_f2(_panel_5min()), Path("unused.png"))
    a, b = captured["axes"][0], captured["axes"][1]
    assert a.get_ylim() == b.get_ylim(), (
        "F2 panels (a) and (b) must share a y-scale")
    plt.close("all")


def test_f4_absolute_and_relative_counts_align_on_months():
    d = D.prepare_f4(_panel_5min())
    assert len(d["months"]) == len(d["count_gt_100"]) == len(
        d["count_gt_trailing_p99"])


def test_f4_trailing_threshold_is_undefined_early():
    # No trailing 12 months available at the start of the panel.
    d = D.prepare_f4(_panel_5min())
    assert d["count_gt_trailing_p99"][0] == 0
    assert not np.isfinite(d["trailing_p99"][0])


def test_f4_records_how_many_months_are_undefined():
    # The plot shades this region so a zero bar there cannot be misread as
    # "no events". The count belongs in the data, not a magic 12 at draw time.
    # A panel shorter than the trailing window is undefined end to end.
    short = D.prepare_f4(_panel_5min())
    assert short["n_undefined_months"] == len(short["months"])
    # A longer one is undefined for exactly the trailing window, and the
    # count must agree with the thresholds it claims to describe.
    long = D.prepare_f4(_panel_5min(n=180000))
    assert long["n_undefined_months"] == 12
    assert long["n_undefined_months"] == sum(
        1 for v in long["trailing_p99"] if not np.isfinite(v))


def test_f4_trailing_window_actually_engages_later():
    # Guards against panel (b) being silently all-zero, which would pass the
    # "undefined early" test while destroying the figure's whole point.
    d = D.prepare_f4(_panel_5min(n=180000))
    assert any(np.isfinite(v) for v in d["trailing_p99"]), \
        "no month ever got a trailing-12-month threshold"
    assert sum(d["count_gt_trailing_p99"]) > 0, \
        "era-relative panel is entirely zero"


def test_f4_annotation_quotes_defined_thresholds_only():
    # The first 12 months carry NaN thresholds. An annotation that reached
    # for months[0] would print "$nan" into the caption of every F4.
    d = D.prepare_f4(_panel_5min(n=180000))
    s = D.prepare_f4_annotation(d)
    assert "nan" not in s.lower(), f"annotation quoted an undefined month: {s}"
    assert s.count("$") == 2, f"expected two dollar figures, got: {s}"


def test_f4_annotation_survives_a_panel_with_no_trailing_window():
    # A panel shorter than the trailing window has no defined threshold at
    # all. Reaching for the first one crashes the whole figure.
    s = D.prepare_f4_annotation(D.prepare_f4(_panel_5min()))
    assert "undefined throughout" in s
    assert "$" not in s


def test_f4b_covers_four_thresholds_on_monthly_buckets():
    d = D.prepare_f4b(_panel_5min())
    assert d["thresholds"] == [100, 250, 500, 1000]
    for thr in d["thresholds"]:
        assert len(d["counts"][thr]) == len(d["months"])


def test_f4b_counts_are_nested_by_threshold():
    # An interval above $500 is necessarily above $250. Checking elementwise
    # catches a mis-keyed or mis-ordered threshold that totals would hide.
    d = D.prepare_f4b(_panel_5min())
    for lo, hi in zip(d["thresholds"], d["thresholds"][1:]):
        for a, b in zip(d["counts"][lo], d["counts"][hi]):
            assert b <= a, f"count above ${hi} exceeds count above ${lo}"


def test_f4b_totals_are_observed_counts_not_rescaled():
    # Monthly buckets exist so that nothing needs annualising. If a scaling
    # factor ever creeps back in, the per-month counts stop summing to the
    # panel's own exceedance total.
    p = _panel_5min()
    d = D.prepare_f4b(p)
    for thr in d["thresholds"]:
        assert sum(d["counts"][thr]) == int((p[D.CONG_COL] > thr).sum())


def test_f4b_shares_the_month_axis_with_f4():
    p = _panel_5min()
    assert D.prepare_f4(p)["months"] == D.prepare_f4b(p)["months"]


def test_f4_plots_write_pngs(tmp_path):
    D.plot_f4(D.prepare_f4(_panel_5min()), tmp_path / "F4.png")
    D.plot_f4b(D.prepare_f4b(_panel_5min()), tmp_path / "F4b.png")
    assert (tmp_path / "F4.png").exists()
    assert (tmp_path / "F4b.png").exists()


def test_f4b_panels_share_a_scale(monkeypatch):
    # All four panels count the same thing at different severities. On
    # independent scales, 25 events above $1000 would draw the same height
    # as 1,632 above $100 -- overstating rare-event escalation, which is the
    # direction that flatters the thesis. Same guard as F2's.
    import matplotlib.pyplot as plt
    captured = {}

    def _record(fig, out_path, **kw):
        captured["axes"] = fig.get_axes()

    monkeypatch.setattr(D.S, "finish", _record)
    D.plot_f4b(D.prepare_f4b(_panel_5min()), Path("unused.png"))
    lims = {ax.get_ylim() for ax in captured["axes"]}
    assert len(lims) == 1, f"F4b panels drew on {len(lims)} different scales"
    plt.close("all")


def test_f4b_tick_labels_are_plain_decimals(monkeypatch):
    # text.parse_math is off module-wide so a literal "$100" survives in
    # captions; a log/symlog formatter would then render ticks as the raw
    # string "$\\mathdefault{10^{2}}$". Same defect S.symlog_axis exists to
    # fix -- assert it here so F4b cannot regress to a bare set_yscale.
    import matplotlib.pyplot as plt
    captured = {}

    def _record(fig, out_path, **kw):
        captured["axes"] = fig.get_axes()

    monkeypatch.setattr(D.S, "finish", _record)
    D.plot_f4b(D.prepare_f4b(_panel_5min()), Path("unused.png"))
    for ax in captured["axes"]:
        ax.figure.canvas.draw()
        for lab in ax.get_yticklabels():
            assert "mathdefault" not in lab.get_text(), \
                f"mathtext leaked into a tick label: {lab.get_text()!r}"
    plt.close("all")
