"""Compute the expensive statistics the figure set needs, once, to JSON.

Plotting code reads `outputs/figure_inputs/*.json` and never recomputes.

Three products:
  spec_sensitivity.json  -- F5: z_slope under the pre-registered spec and
                            under a load-controlled spec, per period x tau,
                            with day-block bootstrap CIs.
  tau_sweep.json         -- F6: implied congestion shift across the observed
                            Z range vs tau, both specs.
  monthly.json           -- F1: monthly load and ramp aggregates.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

Z_COL = "dom_load_gradient_abs_mw_per_min"
LOAD_COL = "dom_load_mw"
CONG_COL = "congestion_price_rt_cluster_mean"
TIME_COL = "datetime_beginning_ept"

SPECS = ("preregistered", "load_controlled")


def build_design(panel: pd.DataFrame, *, spec: str) -> pd.DataFrame:
    """Design matrix: Z + hour/month harmonics, plus load if load_controlled.

    The harmonic basis MUST match `src/surg/analysis/qr_full.py`
    (`_build_periodic_basis`) exactly, or the "pre-registered" series in F5
    will not reproduce the value already recorded in
    outputs/fivemin_extended/qr_full/cluster.json. Two details verified
    2026-08-08 against that module:
      * hour is the INTEGER hour (`.dt.hour`), not hour + minute/60
      * month harmonics use (month - 1), not month
    """
    if spec not in SPECS:
        raise ValueError(f"unknown spec {spec!r}; expected one of {SPECS}")
    t = pd.to_datetime(panel[TIME_COL])
    hour = t.dt.hour.to_numpy(float)
    month = t.dt.month.to_numpy(float)
    X = pd.DataFrame({
        Z_COL: panel[Z_COL].to_numpy(float),
        "hour_sin": np.sin(2.0 * np.pi * hour / 24.0),
        "hour_cos": np.cos(2.0 * np.pi * hour / 24.0),
        "month_sin": np.sin(2.0 * np.pi * (month - 1) / 12.0),
        "month_cos": np.cos(2.0 * np.pi * (month - 1) / 12.0),
    }, index=panel.index)
    if spec == "load_controlled":
        X[LOAD_COL] = panel[LOAD_COL].to_numpy(float)
    return X


def fit_z_slope(panel: pd.DataFrame, *, tau: float, spec: str) -> float:
    """Quantile-regression coefficient on Z at quantile `tau`."""
    X = build_design(panel, spec=spec)
    y = panel[CONG_COL].to_numpy(float)
    ok = np.isfinite(y) & np.isfinite(X.to_numpy(float)).all(axis=1)
    res = sm.QuantReg(y[ok], sm.add_constant(X[ok], has_constant="add")).fit(q=tau)
    return float(res.params[Z_COL])


def day_blocks(panel: pd.DataFrame) -> list[np.ndarray]:
    """Positional index blocks, one per calendar day (bootstrap unit)."""
    days = pd.to_datetime(panel[TIME_COL]).dt.date.to_numpy()
    order = np.argsort(days, kind="stable")
    _, starts = np.unique(days[order], return_index=True)
    return np.split(order, starts[1:])


def _boot_ci(panel: pd.DataFrame, *, tau: float, spec: str, n_boot: int,
             seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    blocks = day_blocks(panel)
    draws: list[float] = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(blocks), len(blocks))
        idx = np.concatenate([blocks[i] for i in pick])
        try:
            draws.append(fit_z_slope(panel.iloc[idx], tau=tau, spec=spec))
        except Exception:
            continue
    if not draws:
        return (float("nan"), float("nan"))
    return (float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5)))


def _periods(panel: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    year = pd.to_datetime(panel[TIME_COL]).dt.year
    out = [("pooled", panel)]
    out += [(str(y), panel[year == y]) for y in sorted(year.unique())]
    return out


def spec_sensitivity(panel: pd.DataFrame, *, taus=(0.90, 0.95),
                     n_boot: int = 200, seed: int = 42) -> dict:
    rows = []
    for pi, (name, sub) in enumerate(_periods(panel)):
        for ti, tau in enumerate(taus):
            for si, spec in enumerate(SPECS):
                slope = fit_z_slope(sub, tau=tau, spec=spec)
                lo, hi = _boot_ci(sub, tau=tau, spec=spec, n_boot=n_boot,
                                  seed=seed + 1000 * pi + 100 * ti + 10 * si)
                rows.append({"period": name, "tau": float(tau), "spec": spec,
                             "z_slope": slope, "ci_lo": lo, "ci_hi": hi,
                             "n": int(len(sub))})
    return {"rows": rows, "n_boot": n_boot, "bootstrap": "day-block",
            "response": CONG_COL, "z": Z_COL, "resolution": "5-min"}


def tau_sweep(panel: pd.DataFrame, *,
              taus=(0.90, 0.95, 0.97, 0.99, 0.995),
              n_boot: int = 200, seed: int = 7) -> dict:
    """Implied congestion shift across the observed Z range, vs tau."""
    z = panel[Z_COL]
    dec = pd.qcut(z, 10, labels=False, duplicates="drop")
    delta_z = float(z[dec == dec.max()].median() - z[dec == 0].median())
    rows = []
    for pi, (name, sub) in enumerate(_periods(panel)):
        for ti, tau in enumerate(taus):
            for si, spec in enumerate(SPECS):
                slope = fit_z_slope(sub, tau=tau, spec=spec)
                base = float(sub[CONG_COL].quantile(tau))
                shift = slope * delta_z
                rows.append({
                    "period": name, "tau": float(tau), "spec": spec,
                    "z_slope": slope, "delta_z_mw_per_min": delta_z,
                    "shift_dollars": shift,
                    "baseline_quantile_dollars": base,
                    "shift_pct_of_baseline": (100.0 * shift / base) if base else float("nan"),
                    "n": int(len(sub)),
                })
    return {"rows": rows, "delta_z_mw_per_min": delta_z,
            "response": CONG_COL, "resolution": "5-min"}


def monthly_aggregates(panel: pd.DataFrame) -> dict:
    t = pd.to_datetime(panel[TIME_COL])
    g = panel.groupby(t.dt.to_period("M"))
    rows = []
    for period, sub in g:
        load = float(sub[LOAD_COL].mean())
        p90 = float(sub[Z_COL].quantile(0.90))
        rows.append({
            "month": str(period),
            "mean_load_mw": load,
            "ramp_p90_mw_per_min": p90,
            "ramp_p90_pct_of_load": (100.0 * p90 / load) if load else float("nan"),
            "n": int(len(sub)),
        })
    rows.sort(key=lambda r: r["month"])
    return {"rows": rows, "resolution": "5-min"}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="compute-figure-inputs")
    p.add_argument("--panel", default="data/interim/analysis_panel_5min.parquet")
    p.add_argument("--out-root", default="outputs/figure_inputs")
    p.add_argument("--n-boot", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--smoke", action="store_true", help="n_boot=5 wiring check.")
    args = p.parse_args(argv)

    n_boot = 5 if args.smoke else args.n_boot
    out = Path(args.out_root)
    out.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(args.panel)
    print(f"panel: {len(panel):,} rows, n_boot={n_boot}", flush=True)

    print("[1/3] monthly aggregates", flush=True)
    (out / "monthly.json").write_text(json.dumps(monthly_aggregates(panel), indent=2))

    print("[2/3] spec sensitivity (F5)", flush=True)
    (out / "spec_sensitivity.json").write_text(
        json.dumps(spec_sensitivity(panel, n_boot=n_boot, seed=args.seed), indent=2))

    print("[3/3] tau sweep (F6)", flush=True)
    (out / "tau_sweep.json").write_text(
        json.dumps(tau_sweep(panel, n_boot=n_boot, seed=args.seed), indent=2))

    print(f"wrote figure inputs to {out}/", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
