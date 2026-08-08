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
