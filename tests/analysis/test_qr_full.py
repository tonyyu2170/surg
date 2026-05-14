"""Unit tests for src/surg/analysis/qr_full.py — Strategy C QR-on-full-panel module."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from surg.analysis.qr_full import QRFullFitResult, fit_qr_full


def _synth_inputs(
    *,
    n: int = 5000,
    z_slope: float = 2.0,
    hour_amplitude: float = 3.0,
    noise_sd: float = 1.0,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Generate synthetic (Y, Z, hour, month) with a planted Z-slope."""
    rng = np.random.default_rng(seed)
    Z = rng.uniform(0, 10, size=n)
    hour = rng.integers(0, 24, size=n)
    month = rng.integers(1, 13, size=n)
    hour_sin = np.sin(2 * np.pi * hour / 24)
    Y = 5.0 + z_slope * Z + hour_amplitude * hour_sin + rng.normal(0, noise_sd, size=n)
    return Y, Z, hour, month


def test_fit_qr_full_recovers_planted_slope():
    """fit_qr_full at tau=0.5 should recover the planted Z slope."""
    Y, Z, hour, month = _synth_inputs(n=5000, z_slope=2.0, seed=42)
    result = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=0, seed=0)

    assert isinstance(result, QRFullFitResult)
    assert result.spec == "primary"
    assert result.n == 5000
    assert result.tau == 0.5
    assert result.z_slope == pytest.approx(2.0, abs=0.1)
    assert result.z_slope_p_value < 1e-6, f"slope p too high: {result.z_slope_p_value}"
    # Covariate coefs should include the four sin/cos columns
    assert set(result.covariate_coefs.keys()) == {
        "hour_sin", "hour_cos", "month_sin", "month_cos",
    }


def test_fit_qr_full_no_signal_gives_high_p():
    """With Z's slope set to 0, the asymptotic p-value should be > 0.05 most of the time.

    Two seeds to reduce single-draw flakiness; assert at least one is non-significant.
    """
    p_values = []
    for seed in (42, 43):
        Y, Z, hour, month = _synth_inputs(n=3000, z_slope=0.0, seed=seed)
        result = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=0, seed=0)
        p_values.append(result.z_slope_p_value)
    assert max(p_values) > 0.05, f"no seed produced p > 0.05; got {p_values}"


def test_fit_qr_full_validates_length_mismatch():
    """All four input arrays must have equal length."""
    rng = np.random.default_rng(seed=42)
    Y = rng.normal(size=100)
    Z = rng.normal(size=100)
    hour = rng.integers(0, 24, size=100)
    month_short = rng.integers(1, 13, size=50)  # wrong length
    with pytest.raises(ValueError, match="length"):
        fit_qr_full(Y, Z, hour, month_short, tau=0.5)


def test_fit_qr_full_validates_no_nan():
    """NaN in any input array raises ValueError (caller-clean precondition)."""
    rng = np.random.default_rng(seed=42)
    Y = rng.normal(size=100).astype(float)
    Y[3] = float("nan")
    Z = rng.normal(size=100)
    hour = rng.integers(0, 24, size=100)
    month = rng.integers(1, 13, size=100)
    with pytest.raises(ValueError, match="NaN"):
        fit_qr_full(Y, Z, hour, month, tau=0.5)


def test_fit_qr_full_validates_hour_out_of_range():
    """hour values outside [0, 23] should raise ValueError, defending against
    silent NaN-to-zero corruption when np.asarray(..., dtype=int) is applied."""
    rng = np.random.default_rng(seed=42)
    Y = rng.normal(size=100)
    Z = rng.normal(size=100)
    hour = rng.integers(0, 24, size=100).astype(int)
    hour[5] = 24  # out of range
    month = rng.integers(1, 13, size=100)
    with pytest.raises(ValueError, match="hour must be in"):
        fit_qr_full(Y, Z, hour, month, tau=0.5)


def test_fit_qr_full_validates_month_out_of_range():
    """month values outside [1, 12] should raise ValueError."""
    rng = np.random.default_rng(seed=42)
    Y = rng.normal(size=100)
    Z = rng.normal(size=100)
    hour = rng.integers(0, 24, size=100)
    month = rng.integers(1, 13, size=100).astype(int)
    month[5] = 0  # 0-indexed bug
    with pytest.raises(ValueError, match="month in"):
        fit_qr_full(Y, Z, hour, month, tau=0.5)


def test_fit_qr_full_bootstrap_ci_is_non_degenerate():
    """With n_boot > 0, the bootstrap CI is finite, has positive width,
    and brackets the point estimate.

    Full coverage-rate testing would require many simulations and is too slow
    for unit tests; an end-to-end coverage study can be a separate validation
    script if reviewer requests.
    """
    Y, Z, hour, month = _synth_inputs(n=2000, z_slope=2.0, seed=42)
    result = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=100, seed=0)

    lo, hi = result.z_slope_bootstrap_ci_95
    assert math.isfinite(lo) and math.isfinite(hi)
    assert hi > lo
    # The point estimate should sit inside the CI on a well-specified DGP
    assert lo <= result.z_slope <= hi, \
        f"point estimate {result.z_slope:.4f} outside CI [{lo:.4f}, {hi:.4f}]"


def test_fit_qr_full_bootstrap_seed_reproducibility():
    """Same seed gives identical bootstrap CI across runs."""
    Y, Z, hour, month = _synth_inputs(n=2000, z_slope=2.0, seed=42)
    r1 = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=50, seed=123)
    r2 = fit_qr_full(Y, Z, hour, month, tau=0.5, n_boot=50, seed=123)
    assert r1.z_slope_bootstrap_ci_95 == r2.z_slope_bootstrap_ci_95
