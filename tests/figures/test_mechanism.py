import json

import numpy as np
import pandas as pd

from scripts.figures import mechanism as M


def _panel(n=360000, seed=11):
    # n must span 2023 -> 2026: at 5-minute steps 40,000 rows reach only June
    # 2023, and every per-year assertion below would KeyError. 360,000 rows is
    # ~3.4 years, the real panel's span.
    rng = np.random.default_rng(seed)
    t = pd.date_range("2023-02-07", periods=n, freq="5min")
    year = t.year
    load = 14000 + 4000 * rng.random(n) + 800 * (year - 2023)
    # Response given load worsens sharply in 2026. The 17,000 MW knee matters:
    # put it above 2023's ceiling and the baseline rate is identically zero,
    # which makes the counterfactual degenerate rather than merely weak.
    p = np.where(year == 2026, 0.4, 0.03) * (load > 17000)
    cong = np.where(rng.random(n) < p, 200.0, 1.0)
    return pd.DataFrame({
        "datetime_beginning_ept": t,
        "dom_load_mw": load,
        "congestion_price_rt_cluster_mean": cong,
        "system_energy_price_rt_cluster_mean": 30 + rng.normal(0, 2, n),
    })


def test_f11_fixture_spans_every_year_the_assertions_use():
    d = M.prepare_f11(_panel())
    assert d["years"] == ["2023", "2024", "2025", "2026"]


def test_f11_bins_are_two_thousand_mw_wide():
    d = M.prepare_f11(_panel())
    edges = d["bin_edges"]
    assert all(round(b - a) == 2000 for a, b in zip(edges, edges[1:]))


def test_f11_reports_exceedance_per_year_per_bin():
    d = M.prepare_f11(_panel())
    for year, row in d["by_year_bin"].items():
        for label, cell in row.items():
            assert cell["n"] >= 0
            if cell["n"]:
                assert 0.0 <= cell["pct_gt_100"] <= 100.0


def test_f11_leaves_unvisited_bins_undefined_not_zero():
    # 2023 never reaches 2026's top bins. Reporting 0.0% there would draw the
    # 2023 line flat along load levels it never saw.
    d = M.prepare_f11(_panel())
    empty = [(y, lab) for y, row in d["by_year_bin"].items()
             for lab, cell in row.items() if cell["n"] == 0]
    assert empty, "fixture no longer has an unvisited bin to check"
    for y, lab in empty:
        assert np.isnan(d["by_year_bin"][y][lab]["pct_gt_100"])
    # ...and an undefined bin must not poison the weighted means
    for v in d["actual_pct"].values():
        assert np.isfinite(v)


def test_f11_counterfactual_share_is_reported_per_year():
    d = M.prepare_f11(_panel())
    assert set(d["load_growth_share_pct"]) <= set(d["years"])
    # 2026's escalation is response-driven in the fixture, so load explains little
    assert d["load_growth_share_pct"]["2026"] < 60


def test_f11_baseline_year_explains_itself_entirely():
    # The baseline's counterfactual is its own actual by construction. If that
    # ever drifts from 100%, the counterfactual is not doing what it claims.
    d = M.prepare_f11(_panel())
    assert round(d["load_growth_share_pct"][d["baseline_year"]]) == 100


def test_f11_flags_unsupported_counterfactual_bins():
    d = M.prepare_f11(_panel())
    assert "unsupported_bins" in d
    # 2023 never reaches the load levels 2026 lives in, which is precisely why
    # the caption calls the magnitude unreliable.
    assert d["unsupported_bins"], "no bin flagged despite a baseline that stops low"


def test_f11_plot_writes_png(tmp_path):
    out = tmp_path / "F11.png"
    M.plot_f11(M.prepare_f11(_panel()), out)
    assert out.exists() and out.stat().st_size > 0
