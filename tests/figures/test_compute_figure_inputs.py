import numpy as np
import pandas as pd
import pytest

from scripts import compute_figure_inputs as cfi


def _panel(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    # 3-hourly, not 5-min: the fixture must span multiple months and more
    # than one calendar year, or the month harmonics are constant columns
    # and the design matrix is rank-deficient.
    t = pd.date_range("2023-02-07", periods=n, freq="3h")
    load = 15000 + 3000 * np.sin(np.arange(n) / 500) + rng.normal(0, 200, n)
    z = np.abs(rng.normal(10, 5, n))
    # congestion driven by LOAD, not by Z -- the finding under test
    cong = np.maximum(0, (load - 17000) / 20 + rng.normal(0, 3, n))
    return pd.DataFrame({
        "datetime_beginning_ept": t,
        "dom_load_mw": load,
        "dom_load_gradient_abs_mw_per_min": z,
        "congestion_price_rt_cluster_mean": cong,
    })


def test_design_matrix_load_controlled_adds_exactly_one_column():
    df = _panel(500)
    pre = cfi.build_design(df, spec="preregistered")
    ctl = cfi.build_design(df, spec="load_controlled")
    assert ctl.shape[1] == pre.shape[1] + 1
    assert "dom_load_mw" in ctl.columns
    assert "dom_load_mw" not in pre.columns


def test_design_matrix_rejects_unknown_spec():
    with pytest.raises(ValueError, match="spec"):
        cfi.build_design(_panel(100), spec="nonsense")


def test_design_matches_the_preregistered_harmonic_basis():
    # Must mirror src/surg/analysis/qr_full.py::_build_periodic_basis exactly.
    df = _panel(200)
    X = cfi.build_design(df, spec="preregistered")
    assert list(X.columns) == [
        "dom_load_gradient_abs_mw_per_min",
        "hour_sin", "hour_cos", "month_sin", "month_cos"]
    t = pd.to_datetime(df["datetime_beginning_ept"])
    # integer hour, and month phase-shifted by -1
    assert np.allclose(X["hour_sin"], np.sin(2 * np.pi * t.dt.hour / 24.0))
    assert np.allclose(X["month_sin"],
                       np.sin(2 * np.pi * (t.dt.month - 1) / 12.0))


def test_day_blocks_group_by_calendar_day():
    df = _panel(3000)
    blocks = cfi.day_blocks(df)
    assert len(blocks) == df["datetime_beginning_ept"].dt.date.nunique()
    assert sum(len(b) for b in blocks) == len(df)


def test_fit_z_slope_recovers_near_zero_when_congestion_is_load_driven():
    # With load controlled, Z should carry essentially no signal here.
    df = _panel(4000)
    slope = cfi.fit_z_slope(df, tau=0.90, spec="load_controlled")
    assert abs(slope) < 0.5


def test_spec_sensitivity_emits_every_period_tau_spec_cell():
    df = _panel(4000)
    out = cfi.spec_sensitivity(df, taus=(0.90,), n_boot=3, seed=1)
    cells = {(r["period"], r["tau"], r["spec"]) for r in out["rows"]}
    assert ("pooled", 0.90, "preregistered") in cells
    assert ("pooled", 0.90, "load_controlled") in cells
    # more than one year must be present, or the per-period split is untested
    assert len({r["period"] for r in out["rows"]}) >= 3  # pooled + >=2 years
    for r in out["rows"]:
        # NOT ci_lo <= z_slope <= ci_hi: at n_boot=3 the interval is the range
        # of three resamples and need not bracket the full-sample estimate.
        assert r["ci_lo"] <= r["ci_hi"]
        assert np.isfinite(r["z_slope"])
        assert r["n"] > 0


def test_design_is_full_rank_on_a_realistic_span():
    df = _panel(4000)
    for spec in ("preregistered", "load_controlled"):
        X = cfi.build_design(df, spec=spec).to_numpy(float)
        X = np.column_stack([np.ones(len(X)), X])  # as fitted, with intercept
        assert np.linalg.matrix_rank(X) == X.shape[1], (
            f"{spec} design is rank-deficient; harmonics may be constant "
            "over the fixture's span")


def test_monthly_aggregates_cover_every_month_once():
    df = _panel(6000)
    out = cfi.monthly_aggregates(df)
    months = [r["month"] for r in out["rows"]]
    assert len(months) == len(set(months))
    assert months == sorted(months)
    for r in out["rows"]:
        assert r["mean_load_mw"] > 0
        assert r["ramp_p90_mw_per_min"] >= 0
        assert r["ramp_p90_pct_of_load"] >= 0
