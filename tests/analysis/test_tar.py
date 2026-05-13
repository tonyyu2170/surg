import numpy as np
import pandas as pd
import pytest


def _make_synthetic_tar(n: int = 2000, c_true: float = 2.0, seed: int = 42):
    """Generate synthetic AR(1) data with a planted threshold.

    Below c_true: Y_t = 0.4*Y_{t-1} + N(0, 0.5)
    Above c_true: Y_t = 0.4*Y_{t-1} + 8 + N(0, 2.0)  (mean shift)
    """
    rng = np.random.default_rng(seed)
    Z = rng.lognormal(mean=0, sigma=0.7, size=n)
    Y = np.zeros(n)
    for t in range(1, n):
        if Z[t] <= c_true:
            Y[t] = 0.4 * Y[t-1] + rng.normal(0, 0.5)
        else:
            Y[t] = 0.4 * Y[t-1] + 8 + rng.normal(0, 2.0)
    return pd.DataFrame({"Z": Z, "Y": Y, "Y_lag1": np.r_[np.nan, Y[:-1]]}).dropna()


def test_tar_recovers_planted_threshold_within_tolerance():
    """The point estimate ĉ should be within 0.5 of the true c=2.0."""
    from surg.analysis.tar import fit_tar

    df = _make_synthetic_tar(n=2000, c_true=2.0)
    result = fit_tar(
        Y=df["Y"].to_numpy(),
        Y_lag=df["Y_lag1"].to_numpy(),
        Z=df["Z"].to_numpy(),
        trim=0.15,
        n_grid=200,
    )
    assert abs(result.c_hat - 2.0) < 0.5
    # AR coefficients should be close to 0.4 in each regime
    assert abs(result.alpha[1] - 0.4) < 0.2  # alpha[0] is intercept, alpha[1] is AR
    assert abs(result.beta[1] - 0.4) < 0.2
    # The above-threshold regime should have a higher intercept
    assert result.beta[0] > result.alpha[0]


def test_tar_returns_regime_counts():
    from surg.analysis.tar import fit_tar
    df = _make_synthetic_tar(n=2000)
    result = fit_tar(
        Y=df["Y"].to_numpy(),
        Y_lag=df["Y_lag1"].to_numpy(),
        Z=df["Z"].to_numpy(),
    )
    assert result.n_low + result.n_high == len(df)
    assert result.n_low > 0 and result.n_high > 0


def test_tar_rejects_unequal_array_lengths():
    from surg.analysis.tar import fit_tar
    with pytest.raises(ValueError, match="same length"):
        fit_tar(
            Y=np.array([1.0, 2.0]),
            Y_lag=np.array([0.0, 1.0]),
            Z=np.array([0.5, 1.5, 2.5]),  # mismatched
        )
