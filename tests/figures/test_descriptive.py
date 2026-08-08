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
