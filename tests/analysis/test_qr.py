import numpy as np
import pandas as pd
import pytest


def _make_synthetic_qr(n: int = 2000, c_true: float = 2.0, seed: int = 7):
    """Z is right-skewed; Q_0.99(Y|Z) has a slope kink at c_true."""
    rng = np.random.default_rng(seed)
    Z = rng.lognormal(0, 0.7, size=n)
    # Heteroskedastic: variance increases above c_true → 99th-pct quantile slopes up
    sigma = np.where(Z > c_true, 1.0 + 3.0 * (Z - c_true), 1.0)
    Y = rng.normal(0, sigma)
    return pd.DataFrame({"Z": Z, "Y": Y})


def test_qr_linear_baseline_returns_significant_positive_slope():
    """At τ=0.99, the linear slope should be positive and significant."""
    from surg.analysis.qr import fit_qr_linear

    df = _make_synthetic_qr(n=2000)
    result = fit_qr_linear(Y=df["Y"].to_numpy(), Z=df["Z"].to_numpy(), tau=0.99)
    assert result.slope > 0
    # Statsmodels-style p-value attribute
    assert result.slope_p_value < 0.05


def test_qr_threshold_dummy_detects_kink():
    """With c set to the true threshold, the dummy coefficient should be significant."""
    from surg.analysis.qr import fit_qr_threshold_dummy

    df = _make_synthetic_qr(n=2000, c_true=2.0)
    result = fit_qr_threshold_dummy(
        Y=df["Y"].to_numpy(), Z=df["Z"].to_numpy(), c=2.0, tau=0.99,
    )
    assert result.kink_coef > 0
    assert result.kink_p_value < 0.05


def test_qr_linear_rejects_unequal_lengths():
    from surg.analysis.qr import fit_qr_linear
    with pytest.raises(ValueError, match="equal length"):
        fit_qr_linear(Y=np.array([1.0, 2.0]), Z=np.array([0.5, 1.5, 2.5]))


def test_qr_threshold_dummy_rejects_c_outside_z_range():
    from surg.analysis.qr import fit_qr_threshold_dummy
    rng = np.random.default_rng(0)
    Y = rng.normal(0, 1, 200)
    Z = rng.lognormal(0, 0.5, 200)
    # Z.max() will be well below 100; c=100 is outside the range
    with pytest.raises(ValueError, match="outside Z range"):
        fit_qr_threshold_dummy(Y=Y, Z=Z, c=100.0, tau=0.99)


def test_qr_threshold_dummy_exposes_slope_p_value():
    """New field added in fix commit; verify it's populated and reasonable."""
    from surg.analysis.qr import fit_qr_threshold_dummy
    df = _make_synthetic_qr(n=2000, c_true=2.0)
    result = fit_qr_threshold_dummy(
        Y=df["Y"].to_numpy(), Z=df["Z"].to_numpy(), c=2.0, tau=0.99,
    )
    # slope_p_value should be a finite float; not asserting significance
    # because below-threshold slope is structurally near zero in this DGP.
    assert isinstance(result.slope_p_value, float)
    assert not np.isnan(result.slope_p_value)
    assert 0.0 <= result.slope_p_value <= 1.0


def test_qr_bspline_kink_location_robust_across_seeds():
    """Across 5 seeds the kink localization should be near c_true=2.0.

    Median absolute error across seeds is the stable metric; individual
    seed runs can drift due to QR solver noise and basis allocation.
    """
    from surg.analysis.qr import fit_qr_bspline

    errors = []
    for seed in [7, 11, 17, 23, 29]:
        df = _make_synthetic_qr(n=3000, c_true=2.0, seed=seed)
        result = fit_qr_bspline(
            Y=df["Y"].to_numpy(), Z=df["Z"].to_numpy(),
            tau=0.99, n_knots=5,
        )
        errors.append(abs(result.kink_location - 2.0))
        assert len(result.curve_z) == 200
        assert len(result.curve_q) == 200
    median_err = float(np.median(errors))
    assert median_err < 0.7, f"median |kink - 2.0| = {median_err:.3f} across 5 seeds"


def test_run_qr_writes_json(tmp_path):
    from surg.analysis.qr import run_qr
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None] * 2000 for col in EXPECTED_COLUMNS})
    synth = _make_synthetic_qr(n=2000, c_true=2.0)
    df["dom_load_gradient_abs_mw_per_min"] = synth["Z"].values
    df["congestion_price_rt_cluster_mean"] = synth["Y"].values
    df["passes_proposal_filter"] = True
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=2000, freq="h")

    out_path = tmp_path / "qr_fit.json"
    run_qr(panel=df, out_path=out_path, c_for_threshold_dummy=2.0)
    assert out_path.exists()

    import json
    payload = json.loads(out_path.read_text())
    assert "linear" in payload
    assert payload["linear"]["slope"] > 0
    assert "threshold_dummy" in payload
    assert payload["threshold_dummy"]["c"] == 2.0
    assert "spline" in payload
    assert "kink_location" in payload["spline"]
