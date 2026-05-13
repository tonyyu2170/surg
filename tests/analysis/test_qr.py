import numpy as np
import pandas as pd


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
