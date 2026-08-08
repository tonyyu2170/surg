import json

import pytest

from scripts.figures import inference as I


def _spec_json(tmp_path):
    rows = []
    for period in ("pooled", "2023", "2024", "2025", "2026"):
        for tau in (0.90, 0.95):
            rows.append({"period": period, "tau": tau, "spec": "preregistered",
                         "z_slope": 0.0367, "ci_lo": 0.0107, "ci_hi": 0.0665,
                         "n": 1000})
            rows.append({"period": period, "tau": tau, "spec": "load_controlled",
                         "z_slope": -0.0266, "ci_lo": -0.0416, "ci_hi": -0.0103,
                         "n": 1000})
    p = tmp_path / "spec_sensitivity.json"
    p.write_text(json.dumps({"rows": rows, "n_boot": 200,
                             "bootstrap": "day-block", "resolution": "5-min"}))
    return p


def _tau_json(tmp_path, descending=False):
    taus = (0.90, 0.95, 0.97, 0.99, 0.995)
    if descending:
        taus = tuple(reversed(taus))
    rows = []
    for period in ("pooled", "2025"):
        for tau in taus:
            for spec in ("preregistered", "load_controlled"):
                rows.append({"period": period, "tau": tau, "spec": spec,
                             "z_slope": 0.04, "delta_z_mw_per_min": 29.3,
                             "shift_dollars": 1.28 * tau,
                             "baseline_quantile_dollars": 8.1,
                             "shift_pct_of_baseline": 15.7 * tau, "n": 1000})
    p = tmp_path / "tau_sweep.json"
    p.write_text(json.dumps({"rows": rows, "delta_z_mw_per_min": 29.3,
                             "resolution": "5-min"}))
    return p


def test_f5_pairs_each_period_tau_with_both_specs(tmp_path):
    d = I.prepare_f5(_spec_json(tmp_path))
    for r in d["rows"]:
        assert r["preregistered"] is not None
        assert r["load_controlled"] is not None


def test_f5_flags_sign_reversals(tmp_path):
    d = I.prepare_f5(_spec_json(tmp_path))
    assert d["n_sign_reversals"] == len(d["rows"])


def test_f5_separates_significant_reversals_from_bare_sign_flips(tmp_path):
    # Two point estimates of opposite sign whose CIs both span zero are two
    # imprecise nulls. On the real inputs 8 of 10 cells flip but only 3 are
    # significant, so conflating them would overstate the finding 2.7x.
    rows = [
        {"period": "sig", "tau": 0.9, "spec": "preregistered",
         "z_slope": 0.04, "ci_lo": 0.02, "ci_hi": 0.07, "n": 10},
        {"period": "sig", "tau": 0.9, "spec": "load_controlled",
         "z_slope": -0.06, "ci_lo": -0.09, "ci_hi": -0.03, "n": 10},
        {"period": "vague", "tau": 0.9, "spec": "preregistered",
         "z_slope": 0.01, "ci_lo": -0.01, "ci_hi": 0.03, "n": 10},
        {"period": "vague", "tau": 0.9, "spec": "load_controlled",
         "z_slope": -0.01, "ci_lo": -0.03, "ci_hi": 0.01, "n": 10},
    ]
    p = tmp_path / "mixed.json"
    p.write_text(json.dumps({"rows": rows, "n_boot": 200}))
    d = I.prepare_f5(p)
    assert d["n_sign_reversals"] == 2
    assert d["n_significant_reversals"] == 1
    by_period = {r["period"]: r for r in d["rows"]}
    assert by_period["sig"]["significant_reversal"] is True
    assert by_period["vague"]["significant_reversal"] is False


def test_f5_refuses_input_missing_a_specification(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"rows": [
        {"period": "pooled", "tau": 0.9, "spec": "preregistered",
         "z_slope": 0.1, "ci_lo": 0.0, "ci_hi": 0.2, "n": 10}]}))
    with pytest.raises(ValueError, match="both specifications"):
        I.prepare_f5(p)


def test_f5_refuses_an_empty_bootstrap(tmp_path):
    # A compute step that died partway writes rows: []. Silently plotting an
    # empty forest would read as "no reversals", the opposite of the finding.
    p = tmp_path / "empty.json"
    p.write_text(json.dumps({"rows": [], "n_boot": 200}))
    with pytest.raises(ValueError, match="no rows"):
        I.prepare_f5(p)


def test_f6_returns_dollar_and_percent_series(tmp_path):
    d = I.prepare_f6(_tau_json(tmp_path))
    s = d["series"][("pooled", "preregistered")]
    assert len(s["tau"]) == len(s["shift_dollars"]) == len(s["shift_pct"])


def test_f6_keeps_the_two_specifications_apart(tmp_path):
    # Cross-cutting rule 8: F6 may not collapse the specs into one line.
    d = I.prepare_f6(_tau_json(tmp_path))
    assert ("pooled", "preregistered") in d["series"]
    assert ("pooled", "load_controlled") in d["series"]
    assert len(d["series"]) == 4


def test_f6_sorts_tau_ascending_whatever_the_file_order(tmp_path):
    # Plotted as a line, unsorted tau draws a zig-zag that invents structure.
    d = I.prepare_f6(_tau_json(tmp_path, descending=True))
    for s in d["series"].values():
        assert s["tau"] == sorted(s["tau"])
        # and the payload must travel with its tau, not stay in file order
        assert s["shift_dollars"] == sorted(s["shift_dollars"])


def test_f6_gives_every_period_a_distinguishable_style():
    # The real sweep holds five periods. Encoding only "pooled vs not" drew
    # eight of ten lines identically, which is a figure that cannot be read.
    styles = [I._period_style(p)
              for p in ("pooled", "2023", "2024", "2025", "2026")]
    assert len(set(styles)) == len(styles), styles
    assert len({m for m, _ in styles}) == len(styles), "markers repeat"


def test_f5_f6_plots_write_pngs(tmp_path):
    I.plot_f5(I.prepare_f5(_spec_json(tmp_path)), tmp_path / "F5.png")
    I.plot_f6(I.prepare_f6(_tau_json(tmp_path)), tmp_path / "F6.png")
    assert (tmp_path / "F5.png").exists()
    assert (tmp_path / "F6.png").exists()
