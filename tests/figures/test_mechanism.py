import json

import numpy as np
import pandas as pd
import pytest

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


def _nofilter_json(tmp_path, *, shuffled=False):
    # Mirrors what run_tail_risk_curves actually writes: results[response] is
    # a LIST of decile records carrying by_threshold[<t>]{p_hat, n_exc,
    # ci_95}, and the threshold keys are "100.0", not "100".
    deciles = list(range(1, 11))
    if shuffled:
        deciles = deciles[5:] + deciles[:5]
    d = {
        "pnode_label": "cluster",
        "thresholds": [100.0, 250.0],
        "decile_n_obs": [3500] * 10,
        "n_total_filtered": 35000,
        "n_boot": 1000,
        "filter": "no_filter == True",
        "resolution": "5-min",
        "results": {
            "congestion": [
                {"decile": i, "z_range_mw_per_min": [0.0, 1.0], "n_total": 3500,
                 "by_threshold": {
                     "100.0": {"p_hat": 0.011 + 0.0001 * (i - 1), "n_exc": 40,
                               "ci_95": [0.008, 0.015]},
                     "250.0": {"p_hat": 0.004, "n_exc": 14,
                               "ci_95": [0.003, 0.005]}}}
                for i in deciles
            ]
        },
    }
    p = tmp_path / "cluster.json"
    p.write_text(json.dumps(d))
    return p


def test_f8_reads_the_schema_the_run_actually_writes(tmp_path):
    # The drafted fixture invented results[response][threshold] as a dict of
    # parallel arrays. Production writes a list of decile records, so the
    # drafted prepare_f8 would have raised TypeError on the first real file.
    d = M.prepare_f8(_nofilter_json(tmp_path), threshold="100")
    assert d["deciles"] == list(range(1, 11))
    assert d["threshold"] == "100.0"
    assert d["n"] == 35000 and d["n_boot"] == 1000


def test_f8_orders_deciles_regardless_of_file_order(tmp_path):
    d = M.prepare_f8(_nofilter_json(tmp_path, shuffled=True), threshold="100")
    assert d["deciles"] == list(range(1, 11))
    assert d["prob"] == sorted(d["prob"])


def test_f8_rejects_a_filtered_source(tmp_path):
    p = tmp_path / "filtered.json"
    p.write_text(json.dumps({"filter": "passes_proposal_filter == True",
                             "resolution": "5-min", "results": {}}))
    with pytest.raises(ValueError, match="no-filter"):
        M.prepare_f8(p)


def test_f8_rejects_a_source_labelled_hourly(tmp_path):
    p = tmp_path / "hourly.json"
    p.write_text(json.dumps({"filter": "none (full panel)",
                             "resolution": "hourly", "results": {}}))
    with pytest.raises(ValueError, match="resolution"):
        M.prepare_f8(p)


def test_f8_returns_decile_curve_with_cis(tmp_path):
    d = M.prepare_f8(_nofilter_json(tmp_path), threshold="100")
    assert len(d["deciles"]) == 10
    assert len(d["prob"]) == len(d["ci_lo"]) == len(d["ci_hi"]) == 10


def test_f8_computes_an_mde_annotation(tmp_path):
    d = M.prepare_f8(_nofilter_json(tmp_path), threshold="100")
    assert d["mde_pct"] > 0


def test_f8_reports_the_decile_ratio_it_plots(tmp_path):
    # The headline read on this curve is d10/d1. Computing it here keeps the
    # caption from quoting a ratio nobody derived from the plotted series.
    d = M.prepare_f8(_nofilter_json(tmp_path), threshold="100")
    assert d["d10_over_d1"] == pytest.approx(
        d["prob"][-1] / d["prob"][0], rel=1e-9)


def test_f8_plot_writes_png(tmp_path):
    out = tmp_path / "F8.png"
    M.plot_f8(M.prepare_f8(_nofilter_json(tmp_path), threshold="100"), out)
    assert out.exists() and out.stat().st_size > 0


def _mechanism_dir(tmp_path):
    # Every shape below was read off the real outputs on 2026-08-08. The plan
    # guessed `beta1` for gpd_continuous and `raw_by_year` for the year-FE
    # diagnostic; neither key exists.
    for sub in ("gpd", "qr_full", "gpd_continuous", "year_fe_diagnostic"):
        (tmp_path / sub).mkdir()
    (tmp_path / "gpd" / "primary.json").write_text(json.dumps({
        "conditional_z": {
            "low_z": {"shape": 0.778, "shape_bootstrap_ci_95": [0.65, 0.90]},
            "high_z": {"shape": 0.609, "shape_bootstrap_ci_95": [0.50, 0.72]},
            "shape_difference": {"diff": -0.1695,
                                 "bootstrap_ci_95": [-0.3340, -0.0217],
                                 "bootstrap_p_value": 0.985}}}))
    (tmp_path / "qr_full" / "primary.json").write_text(json.dumps({
        "fits": [{"tau": t, "spec": "primary", "z_slope": 0.03 * i,
                  "z_slope_bootstrap_ci_95": [0.01 * i, 0.05 * i]}
                 for i, t in enumerate((0.90, 0.95, 0.99), start=1)]}))
    (tmp_path / "gpd_continuous" / "primary.json").write_text(json.dumps({
        "threshold_sweep": [
            {"threshold_quantile": q, "n_exceedances": 3000,
             "linear": {"convergence_status": "converged",
                        "shape_coefficients": [0.9, b1],
                        "shape_coefficients_bootstrap_ci_95": [
                            [0.80, 1.00], [b1 - 0.01, b1 + 0.01]]}}
            for q, b1 in ((0.90, -0.0074), (0.95, -0.0073),
                          (0.99, -0.0260), (0.995, 0.0104))]}))
    (tmp_path / "year_fe_diagnostic" / "primary.json").write_text(json.dumps({
        "taus": [0.9, 0.95, 0.99],
        "layer3_secular_component_bootstrap": {
            "tau_0.90": {"primary_z_slope": 0.391, "year_fe_z_slope": 0.253,
                         "secular_component_point": 0.138,
                         "secular_component_ci": [0.100, 0.193]},
            "tau_0.95": {"primary_z_slope": 0.573, "year_fe_z_slope": 0.415,
                         "secular_component_point": 0.158,
                         "secular_component_ci": [0.110, 0.220]},
            "tau_0.99": {"primary_z_slope": 0.357, "year_fe_z_slope": 0.622,
                         "secular_component_point": -0.265,
                         "secular_component_ci": [-0.700, 0.100]}}}))
    return tmp_path


def test_f9_reads_all_four_mechanism_sources(tmp_path):
    d = M.prepare_f9(_mechanism_dir(tmp_path))
    for k in ("conditional_z", "qr_full", "spec_b", "secular"):
        assert k in d and d[k]


def test_f9_carries_the_spec_a_reinterpretation(tmp_path):
    d = M.prepare_f9(_mechanism_dir(tmp_path))
    assert "level-driven" in d["spec_a_caption"]


def test_f9_reads_spec_b_beta1_out_of_shape_coefficients(tmp_path):
    # There is no `beta1` key. beta1 is the SECOND shape coefficient; taking
    # the first would silently plot the intercept (~0.9) as the slope.
    d = M.prepare_f9(_mechanism_dir(tmp_path))
    assert [round(r["beta1"], 4) for r in d["spec_b"]] == [
        -0.0074, -0.0073, -0.0260, 0.0104]
    assert all(r["ci"][0] < r["beta1"] < r["ci"][1] for r in d["spec_b"])


def test_f9_secular_rows_are_ordered_by_tau(tmp_path):
    d = M.prepare_f9(_mechanism_dir(tmp_path))
    assert [r["tau"] for r in d["secular"]] == [0.90, 0.95, 0.99]
    # secular component is primary minus year-FE, by definition
    for r in d["secular"]:
        assert abs((r["primary"] - r["year_fe"]) - r["point"]) < 5e-3


def test_f9_plot_writes_png(tmp_path):
    out = tmp_path / "F9.png"
    M.plot_f9(M.prepare_f9(_mechanism_dir(tmp_path)), out)
    assert out.exists() and out.stat().st_size > 0
