"""Non-stationary Generalized Pareto Distribution fits with covariates on shape and scale.

Spec B module (sub-question 1 closure) — fits ξ(Z) = β₀ + β₁·Z (linear) or
ξ(Z) = β₀ + β₁·Z + β₂·Z² + β₃·Z³ (polynomial-degree-3, 4 DOF). Scale is
always log-linear: log σ(Z) = σ₀ + σ₁·Z.

The polynomial-degree-3 basis (4 DOF: intercept + linear + quadratic + cubic)
matches the design's "4-DOF flexible shape" intent. A natural cubic spline
with K=3 interior knots gives only 3 DOF per ESL convention (basis is K
functions including intercept); a 4-DOF natural cubic spline would need K=4
knots + knot placement. Polynomial basis avoids the knot-placement decision
and gives identical capability within the observed Z range.

Implementation reference: Davison & Smith 1990 (JRSS-B), Coles 2001 §6.3.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from scipy import optimize as _optimize
from scipy import stats

from surg.analysis.gpd import fit_gpd


@dataclass(frozen=True, slots=True)
class GPDContinuousFitResult:
    """Non-stationary GPD fit with covariate Z on shape and scale.

    `shape_coefficients`: linear form → (β₀, β₁); spline form → (β₀, β₁, β₂, β₃).
    `scale_coefficients`: always (σ₀ (log-scale intercept), σ₁) since scale form
    is fixed at log-linear regardless of shape form.
    `headline_slope_or_lrt`: β₁ for linear (the headline scalar in the pre-reg);
    LRT statistic (chi² value) for spline.
    `headline_p_value`: two-sided bootstrap p-value for β₁ (linear) or bootstrap
    p-value for LRT (spline).
    `convergence_status`: "converged" | "failed" | "insufficient_bootstrap_reps".
    """

    form: Literal["linear", "spline"]
    threshold_quantile: float
    threshold_value: float
    n_exceedances: int
    shape_coefficients: tuple[float, ...]
    shape_coefficients_bootstrap_ci_95: tuple[tuple[float, float], ...]
    scale_coefficients: tuple[float, float]
    scale_coefficients_bootstrap_ci_95: tuple[tuple[float, float], tuple[float, float]]
    headline_slope_or_lrt: float
    headline_p_value: float
    convergence_status: str


def _design_matrix(
    Z: np.ndarray,
    *,
    form: Literal["linear", "spline"],
    for_scale: bool = False,
) -> np.ndarray:
    """Construct the design matrix X for shape regression (or scale, which is
    always linear).

    Linear shape: X = [1, Z], shape=(n, 2).
    Spline shape: X = [1, Z, Z², Z³], shape=(n, 4) — polynomial-degree-3 basis.
    Scale (always linear): X = [1, Z], shape=(n, 2).
    """
    if form not in ("linear", "spline"):
        raise ValueError(f"form must be 'linear' or 'spline'; got {form!r}")
    Z_arr = np.asarray(Z, dtype=float)
    if for_scale or form == "linear":
        return np.column_stack([np.ones_like(Z_arr), Z_arr])
    # form == "spline" at this point
    return np.column_stack([np.ones_like(Z_arr), Z_arr, Z_arr ** 2, Z_arr ** 3])


def _initial_params(
    Y_exc: np.ndarray,
    *,
    form: Literal["linear", "spline"],
) -> tuple[float, ...]:
    """Compute MLE initial values from a stationary GPD fit on Y_exc.

    Returns:
      Linear: (β₀, β₁=0, σ₀=log(scale), σ₁=0) — 4 params.
      Spline: (β₀, β₁=0, β₂=0, β₃=0, σ₀=log(scale), σ₁=0) — 6 params.

    The stationary fit handles the case where Y_exc is already exceedance over
    a threshold (in this module's context, Y_exc has already been shifted to
    be exceedance values above 0).
    """
    Y_arr = np.asarray(Y_exc, dtype=float)
    # Stationary GPD fit on the exceedances (Y_exc already over threshold=0)
    base_fit = fit_gpd(Y_arr, threshold=0.0)
    shape_init = base_fit.shape
    log_scale_init = math.log(base_fit.scale)
    if form == "linear":
        return (shape_init, 0.0, log_scale_init, 0.0)
    if form == "spline":
        return (shape_init, 0.0, 0.0, 0.0, log_scale_init, 0.0)
    raise ValueError(f"form must be 'linear' or 'spline'; got {form!r}")


def _neg_log_likelihood_nonstationary_gpd(
    params: np.ndarray,
    Y_exc: np.ndarray,
    X_xi: np.ndarray,
    X_sigma: np.ndarray,
) -> float:
    """Negative log-likelihood for non-stationary GPD with covariates Z.

    Y_exc[i] is exceedance over threshold (already shifted), modeled as
    GPD(σ(Z_i), ξ(Z_i)) where:
      log σ(Z) = X_sigma @ params_sigma  (last 2 params)
      ξ(Z)    = X_xi   @ params_xi      (first len(X_xi[0]) params)

    Returns +inf if any of the following invariant violations occurs:
      - σ(Z_i) ≤ 1e-10 for any i (numerical underflow)
      - 1 + ξ(Z_i) * Y_exc[i] / σ(Z_i) ≤ 0 for any i (support violation)
      - Y_exc[i] < 0 for any i (negative exceedance — input invariant violated)

    For ξ(Z_i) near 0 (|ξ| < 1e-8), uses the exponential log-density limit:
      log f(y; σ, ξ→0) = -log σ - y/σ
    """
    n_xi = X_xi.shape[1]
    params_xi = params[:n_xi]
    params_sigma = params[n_xi:]
    if len(params_sigma) != X_sigma.shape[1]:
        return float("inf")

    Y_arr = np.asarray(Y_exc, dtype=float)
    if (Y_arr < 0).any():
        return float("inf")

    log_sigma = X_sigma @ params_sigma
    sigma = np.exp(log_sigma)
    if (sigma <= 1e-10).any() or not np.isfinite(sigma).all():
        return float("inf")

    xi = X_xi @ params_xi
    if not np.isfinite(xi).all():
        return float("inf")

    # Support: 1 + ξ * y / σ > 0 for all observations
    inner = 1.0 + xi * Y_arr / sigma
    if (inner <= 0).any():
        return float("inf")

    # Two branches: |ξ| > 1e-8 (regular GPD log-density) and |ξ| ≤ 1e-8 (exponential limit)
    # For numerical stability, treat each observation by its xi value.
    near_zero = np.abs(xi) < 1e-8
    nll_terms = np.empty_like(Y_arr)
    # Regular branch
    reg_mask = ~near_zero
    nll_terms[reg_mask] = (
        log_sigma[reg_mask]
        + (1.0 + 1.0 / xi[reg_mask]) * np.log(inner[reg_mask])
    )
    # Exponential limit branch
    nll_terms[near_zero] = log_sigma[near_zero] + Y_arr[near_zero] / sigma[near_zero]

    total_nll = float(np.sum(nll_terms))
    if not math.isfinite(total_nll):
        return float("inf")
    return total_nll


def _optimize_mle(
    Y_exc: np.ndarray,
    Z_exc: np.ndarray,
    form: Literal["linear", "spline"],
) -> tuple[np.ndarray, str]:
    """Run MLE optimization with BFGS, falling back to Nelder-Mead.

    Returns (params, status) where status ∈ {"converged", "failed"}.
    The `_initial_params` call is inside the try/except so that fit_gpd
    failures on degenerate data are treated as "failed" rather than crashing.
    """
    X_xi = _design_matrix(Z_exc, form=form)
    X_sigma = _design_matrix(Z_exc, form=form, for_scale=True)

    def objective(params):
        return _neg_log_likelihood_nonstationary_gpd(params, Y_exc, X_xi, X_sigma)

    # BFGS first — includes _initial_params inside the guard
    x0 = None
    try:
        x0 = np.asarray(_initial_params(Y_exc, form=form), dtype=float)
        res = _optimize.minimize(
            objective, x0, method="BFGS", options={"maxiter": 500, "gtol": 1e-6},
        )
        if res.success and np.isfinite(res.fun):
            return (np.asarray(res.x, dtype=float), "converged")
    except (ValueError, FloatingPointError):
        pass

    # Nelder-Mead fallback — reuse x0 if computed; recompute if BFGS path crashed before x0
    try:
        if x0 is None:
            x0 = np.asarray(_initial_params(Y_exc, form=form), dtype=float)
        res = _optimize.minimize(
            objective, x0, method="Nelder-Mead",
            options={"maxiter": 2000, "xatol": 1e-5, "fatol": 1e-5},
        )
        if res.success and np.isfinite(res.fun):
            return (np.asarray(res.x, dtype=float), "converged")
    except (ValueError, FloatingPointError):
        pass

    # x0 may be None if _initial_params failed twice; use zeros as a stub for the NaN return shape
    n_params = X_xi.shape[1] + X_sigma.shape[1]
    return (np.full(n_params, np.nan), "failed")


def fit_gpd_continuous_z(
    Y: np.ndarray | pd.Series,
    Z: np.ndarray | pd.Series,
    *,
    threshold: float,
    form: Literal["linear", "spline"],
    n_boot: int = 200,
    seed: int = 0,
) -> GPDContinuousFitResult:
    """Fit non-stationary GPD with covariate Z on shape and scale.

    Form options:
      "linear": ξ(Z) = β₀ + β₁·Z, log σ(Z) = σ₀ + σ₁·Z. 4 params total.
      "spline": ξ(Z) = β₀ + β₁·Z + β₂·Z² + β₃·Z³, log σ(Z) = σ₀ + σ₁·Z. 6 params.

    Pair-bootstrap on exceedance row indices, n_boot reps, refit per rep.
    Two-sided bootstrap p-value for the headline statistic (β₁ for linear;
    LRT-equivalent for spline — but Task 4 handles the spline LRT separately,
    so for spline form this function reports β₁ from the linear projection).

    Failure modes:
      - Primary MLE failure → convergence_status = "failed", params = NaN
      - Bootstrap < 100 successful reps → convergence_status = "insufficient_bootstrap_reps",
        CIs = (NaN, NaN)
    """
    if form not in ("linear", "spline"):
        raise ValueError(f"form must be 'linear' or 'spline'; got {form!r}")

    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    if len(Y_arr) != len(Z_arr):
        raise ValueError(
            f"Y and Z must have equal length; got {len(Y_arr)} vs {len(Z_arr)}"
        )
    if not np.isfinite(threshold):
        raise ValueError(f"threshold must be finite; got {threshold}")

    exceed_mask = Y_arr > threshold
    Y_exc = Y_arr[exceed_mask] - threshold
    Z_exc = Z_arr[exceed_mask]
    n_exc = len(Y_exc)

    n_xi = 2 if form == "linear" else 4

    if n_exc == 0:
        nan_ci = tuple((float("nan"), float("nan")) for _ in range(n_xi))
        return GPDContinuousFitResult(
            form=form,
            threshold_quantile=float(np.mean(Y_arr <= threshold)),
            threshold_value=float(threshold),
            n_exceedances=0,
            shape_coefficients=tuple(float("nan") for _ in range(n_xi)),
            shape_coefficients_bootstrap_ci_95=nan_ci,
            scale_coefficients=(float("nan"), float("nan")),
            scale_coefficients_bootstrap_ci_95=((float("nan"), float("nan")),) * 2,
            headline_slope_or_lrt=float("nan"),
            headline_p_value=float("nan"),
            convergence_status="failed",
        )

    # Primary fit
    primary_params, primary_status = _optimize_mle(Y_exc, Z_exc, form=form)
    if primary_status == "failed":
        # All NaN result
        nan_ci = tuple((float("nan"), float("nan")) for _ in range(n_xi))
        return GPDContinuousFitResult(
            form=form,
            threshold_quantile=float(np.mean(Y_arr <= threshold)),
            threshold_value=float(threshold),
            n_exceedances=n_exc,
            shape_coefficients=tuple(float("nan") for _ in range(n_xi)),
            shape_coefficients_bootstrap_ci_95=nan_ci,
            scale_coefficients=(float("nan"), float("nan")),
            scale_coefficients_bootstrap_ci_95=((float("nan"), float("nan")),) * 2,
            headline_slope_or_lrt=float("nan"),
            headline_p_value=float("nan"),
            convergence_status="failed",
        )

    # Bootstrap
    rng = np.random.default_rng(seed)
    bootstrap_xi_params: list[np.ndarray] = []
    bootstrap_sigma_params: list[np.ndarray] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_exc, size=n_exc)
        Y_b = Y_exc[idx]
        Z_b = Z_exc[idx]
        try:
            boot_params, boot_status = _optimize_mle(Y_b, Z_b, form=form)
        except (ValueError, FloatingPointError):
            continue
        if boot_status != "converged":
            continue
        bootstrap_xi_params.append(boot_params[:n_xi])
        bootstrap_sigma_params.append(boot_params[n_xi:])

    if len(bootstrap_xi_params) < 100:
        nan_ci = tuple((float("nan"), float("nan")) for _ in range(n_xi))
        return GPDContinuousFitResult(
            form=form,
            threshold_quantile=float(np.mean(Y_arr <= threshold)),
            threshold_value=float(threshold),
            n_exceedances=n_exc,
            shape_coefficients=tuple(float(c) for c in primary_params[:n_xi]),
            shape_coefficients_bootstrap_ci_95=nan_ci,
            scale_coefficients=(float(primary_params[n_xi]), float(primary_params[n_xi + 1])),
            scale_coefficients_bootstrap_ci_95=((float("nan"), float("nan")),) * 2,
            headline_slope_or_lrt=float(primary_params[1]),  # β₁
            headline_p_value=float("nan"),
            convergence_status="insufficient_bootstrap_reps",
        )

    xi_array = np.asarray(bootstrap_xi_params)  # shape (n_succ, n_xi)
    sigma_array = np.asarray(bootstrap_sigma_params)

    xi_cis = tuple(
        (float(np.quantile(xi_array[:, j], 0.025)),
         float(np.quantile(xi_array[:, j], 0.975)))
        for j in range(n_xi)
    )
    sigma_cis = (
        (float(np.quantile(sigma_array[:, 0], 0.025)),
         float(np.quantile(sigma_array[:, 0], 0.975))),
        (float(np.quantile(sigma_array[:, 1], 0.025)),
         float(np.quantile(sigma_array[:, 1], 0.975))),
    )

    # Two-sided bootstrap p on β₁ (regardless of form — for spline, this
    # captures the linear-coefficient share; LRT for spline is in Task 4).
    # Two-sided bootstrap p on β₁. The outer min(1.0, ...) clip handles
    # the degenerate case where all bootstrap β₁ samples are exactly 0
    # (p_left = p_right = 1.0 → 2*1.0 = 2.0 without the clip).
    beta_1_boot = xi_array[:, 1]
    p_left = float(np.mean(beta_1_boot <= 0.0))
    p_right = float(np.mean(beta_1_boot >= 0.0))
    p_two_sided = min(1.0, 2.0 * min(p_left, p_right))

    return GPDContinuousFitResult(
        form=form,
        threshold_quantile=float(np.mean(Y_arr <= threshold)),
        threshold_value=float(threshold),
        n_exceedances=n_exc,
        shape_coefficients=tuple(float(c) for c in primary_params[:n_xi]),
        shape_coefficients_bootstrap_ci_95=xi_cis,
        scale_coefficients=(float(primary_params[n_xi]), float(primary_params[n_xi + 1])),
        scale_coefficients_bootstrap_ci_95=sigma_cis,
        headline_slope_or_lrt=float(primary_params[1]),  # β₁
        headline_p_value=p_two_sided,
        convergence_status="converged",
    )


def _likelihood_ratio_test(
    linear_result: GPDContinuousFitResult,
    spline_result: GPDContinuousFitResult,
    Y: np.ndarray,
    Z: np.ndarray,
    *,
    threshold: float,
) -> dict:
    """Likelihood-ratio test for nested non-stationary GPD models.

    Tests H0: spline-extra-DOF = 0 (i.e., linear is adequate) vs H1: spline.

    LRT statistic: chi² = 2 · (NLL_linear − NLL_spline). Asymptotic χ²
    distribution with df = (spline DOF) − (linear DOF) = 4 − 2 = 2.

    Only the primary fit coefficients are used; bootstrap results are not
    needed. Accepts both "converged" and "insufficient_bootstrap_reps" statuses
    (primary params are finite in both cases). Returns NaN values and df=2 if
    either fit has status "failed" (NaN primary params).
    """
    _VALID_STATUSES = {"converged", "insufficient_bootstrap_reps"}
    out = {"df": 2, "chi2": float("nan"), "asymptotic_p_value": float("nan")}
    if (linear_result.convergence_status not in _VALID_STATUSES
            or spline_result.convergence_status not in _VALID_STATUSES):
        return out

    Y_arr = np.asarray(Y, dtype=float)
    Z_arr = np.asarray(Z, dtype=float)
    exceed_mask = Y_arr > threshold
    Y_exc = Y_arr[exceed_mask] - threshold
    Z_exc = Z_arr[exceed_mask]

    # Reconstruct NLL at the fitted params for both forms
    X_xi_lin = _design_matrix(Z_exc, form="linear")
    X_sigma_lin = _design_matrix(Z_exc, form="linear", for_scale=True)
    params_lin = np.array(
        list(linear_result.shape_coefficients) + list(linear_result.scale_coefficients)
    )
    nll_linear = _neg_log_likelihood_nonstationary_gpd(
        params_lin, Y_exc, X_xi_lin, X_sigma_lin,
    )

    X_xi_spl = _design_matrix(Z_exc, form="spline")
    X_sigma_spl = _design_matrix(Z_exc, form="spline", for_scale=True)
    params_spl = np.array(
        list(spline_result.shape_coefficients) + list(spline_result.scale_coefficients)
    )
    nll_spline = _neg_log_likelihood_nonstationary_gpd(
        params_spl, Y_exc, X_xi_spl, X_sigma_spl,
    )

    if not (math.isfinite(nll_linear) and math.isfinite(nll_spline)):
        return out

    chi2 = max(0.0, 2.0 * (nll_linear - nll_spline))
    asymptotic_p = float(1.0 - stats.chi2.cdf(chi2, df=2))
    out["chi2"] = float(chi2)
    out["asymptotic_p_value"] = asymptotic_p
    return out


def _nan_to_none(obj):
    """Recursively replace float NaN/inf with None for JSON serialization."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (list, tuple)):
        return [_nan_to_none(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _nan_to_none(v) for k, v in obj.items()}
    return obj


def _fit_result_to_dict(fit: GPDContinuousFitResult) -> dict:
    return {
        "convergence_status": fit.convergence_status,
        "shape_coefficients": list(fit.shape_coefficients),
        "shape_coefficients_bootstrap_ci_95": [list(ci) for ci in fit.shape_coefficients_bootstrap_ci_95],
        "scale_coefficients": list(fit.scale_coefficients),
        "scale_coefficients_bootstrap_ci_95": [list(ci) for ci in fit.scale_coefficients_bootstrap_ci_95],
        "beta_1_two_sided_p_value": fit.headline_p_value,
    }


def run_gpd_continuous_z(
    panel: pd.DataFrame,
    out_path: Path,
    *,
    response_col: str,
    pnode_label: str,
    threshold_col: str = "dom_load_gradient_abs_mw_per_min",
    threshold_quantiles: tuple[float, ...] = (0.90, 0.95, 0.99, 0.995),
    n_boot: int = 200,
    seed: int = 0,
) -> None:
    """Per-pnode Spec B orchestrator: threshold sweep × (linear + spline + LRT).

    Drops NaN rows in [response_col, threshold_col]. For each threshold quantile,
    fits both linear and spline forms, runs the LRT. Writes a single JSON
    output file matching the design schema.
    """
    n_total = len(panel)
    subset = panel.dropna(subset=[response_col, threshold_col])
    Y = subset[response_col].to_numpy()
    Z = subset[threshold_col].to_numpy()
    n_after = len(subset)

    sweep_entries: list[dict] = []
    for i, q in enumerate(threshold_quantiles):
        threshold = float(np.quantile(Y, q))
        n_exc = int((Y > threshold).sum())
        linear_result = fit_gpd_continuous_z(
            Y, Z, threshold=threshold, form="linear", n_boot=n_boot, seed=seed + 10 * i,
        )
        spline_result = fit_gpd_continuous_z(
            Y, Z, threshold=threshold, form="spline", n_boot=n_boot, seed=seed + 10 * i + 5,
        )
        lrt = _likelihood_ratio_test(
            linear_result, spline_result, Y, Z, threshold=threshold,
        )
        sweep_entries.append({
            "threshold_quantile": float(q),
            "threshold_value": float(threshold),
            "n_exceedances": n_exc,
            "linear": _fit_result_to_dict(linear_result),
            "spline": _fit_result_to_dict(spline_result),
            "likelihood_ratio_test": {
                "chi2": lrt["chi2"],
                "df": int(lrt["df"]),
                "asymptotic_p_value": lrt["asymptotic_p_value"],
            },
        })

    payload = {
        "pnode_label": pnode_label,
        "response_col": response_col,
        "threshold_col": threshold_col,
        "n_total_panel": int(n_total),
        "n_after_dropna": int(n_after),
        "threshold_sweep": sweep_entries,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(_nan_to_none(payload), indent=2))
