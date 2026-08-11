# scripts/necec_price_test.py
"""NECEC price test. Usage: .venv/bin/python scripts/necec_price_test.py

Implements docs/plans/2026-08-11-isone-necec-price-prereg.md exactly. Did the
1,200 MW Canadian HVDC injection at Lewiston, Maine (commercial operation
2026-01-16) move Maine's day-ahead price relative to zones it did not touch?

Reference = CT + RI (no Canadian injection point). Treated = ME. Counter-treated
= the MA zones, which lost ~530 MW of Phase I/II injection at Sandy Pond over the
same window. Inference is by rank against a 45-cell placebo grid, not asymptotic
standard errors, because hourly LMP is heavily autocorrelated.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PANEL = Path("data/interim/isone_diagnostic_panel.parquet")
OUTDIR = Path("outputs/necec_price_test")
TIME = "datetime_beginning_ept"

REFERENCE = ["ct", "ri"]
TREATED = "me"
COUNTER_TREATED = ["nema", "sema", "wcma"]
PLACEBO_ZONES = ["me", "nh", "nema", "sema", "wcma"]  # vt contaminated by Highgate
TREAT_YEAR = 2026
# Feb 1 - Jun 30. January is dropped from every year, symmetrically: NECEC's ramp
# profile is unverified and Jan 2026 is the month most likely to be a
# partial-treatment smear.
MONTHS = (2, 6)


def load_basis() -> pd.DataFrame:
    """Hourly basis of every zone against the mean of the reference zones."""
    df = pd.read_parquet(PANEL)
    df = df[~df["dst_transition_hour"].astype(bool)].copy()
    df[TIME] = pd.to_datetime(df[TIME])

    ref = df[[f"da_lmp_{z}" for z in REFERENCE]].mean(axis=1)
    out = pd.DataFrame({TIME: df[TIME]})
    for col in df.columns:
        if col.startswith("da_lmp_"):
            out[col[len("da_lmp_"):]] = df[col] - ref

    out["year"] = out[TIME].dt.year
    out["hour"] = out[TIME].dt.hour
    month = out[TIME].dt.month
    return out[(month >= MONTHS[0]) & (month <= MONTHS[1])].reset_index(drop=True)


def yearly_stats(basis: pd.DataFrame, zones: list[str]) -> tuple[pd.DataFrame, ...]:
    """Per zone-year: mean basis (primary), median basis, and basis volatility."""
    level, median, vol = {}, {}, {}
    for z in zones:
        by_year = basis.groupby("year")[z]
        level[z] = by_year.mean()
        median[z] = by_year.median()
        # Hour-to-hour |change| within each year, so the Jan->Feb seam never
        # contributes a difference.
        vol[z] = by_year.apply(lambda s: s.diff().abs().mean())
    return pd.DataFrame(level), pd.DataFrame(median), pd.DataFrame(vol)


def standardize(stat: pd.DataFrame) -> pd.DataFrame:
    """s_z(y) = delta_z(y) / SD of that zone's own 2017..2025 year-over-year moves."""
    delta = stat.diff().loc[2017:]
    pre_sd = delta.loc[2017:2025].std()
    return delta / pre_sd


def rank_p(stat_value: float, placebo: np.ndarray) -> tuple[int, float]:
    """One-sided (lower-tail) rank p. Minimum attainable is 1/(len+1)."""
    n_below = int((placebo <= stat_value).sum())
    return n_below, (n_below + 1) / (len(placebo) + 1)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    basis = load_basis()
    zones = [c for c in basis.columns if c not in (TIME, "year", "hour")]
    print("hours per year (Feb-Jun, DST-transition rows dropped):")
    print(basis.groupby("year").size().to_string())

    level, median, vol = yearly_stats(basis, zones)
    s_level = standardize(level)
    s_vol = standardize(vol)

    level.to_csv(OUTDIR / "basis_level_by_zone_year.csv")
    vol.to_csv(OUTDIR / "basis_volatility_by_zone_year.csv")
    s_level.to_csv(OUTDIR / "standardized_level_change.csv")

    print("\n=== Mean ME basis vs CT/RI reference, $/MWh, Feb-Jun ===")
    print(level[[TREATED] + COUNTER_TREATED + ["nh", "vt"]].round(2).to_string())

    # ---- Primary: level, ME ----
    placebo = s_level.loc[2017:2025, PLACEBO_ZONES].to_numpy().ravel()
    placebo = placebo[~np.isnan(placebo)]
    s_me = s_level.loc[TREAT_YEAR, TREATED]
    n_below, p = rank_p(s_me, placebo)

    print("\n=== PRIMARY: ME standardized level change, 2026 vs placebo grid ===")
    delta_me = level.loc[TREAT_YEAR, TREATED] - level.loc[TREAT_YEAR - 1, TREATED]
    print(f"delta_ME(2026)   = {delta_me:+.3f} $/MWh")
    print(f"s_ME(2026)       = {s_me:+.3f}")
    print(f"placebo cells    = {len(placebo)} (min {placebo.min():+.2f}, max {placebo.max():+.2f})")
    print(f"cells <= s_ME    = {n_below}")
    print(f"one-sided rank p = {p:.4f}")

    if s_me < 0 and p <= 0.05:
        verdict = "SUPPORTED"
    elif s_me > 0 or p > 0.20:
        verdict = "REJECTED"
    else:
        verdict = "INCONCLUSIVE"
    print(f"pre-registered rule -> {verdict}")

    # ---- Counter-treatment: MA should RISE ----
    s_ma = s_level.loc[TREAT_YEAR, COUNTER_TREATED]
    print("\n=== COUNTER-TREATMENT: MA zones, predicted POSITIVE ===")
    for z in COUNTER_TREATED:
        print(f"  s_{z}(2026) = {s_ma[z]:+.3f}")
    print(f"  mean        = {s_ma.mean():+.3f}  -> "
          f"{'as predicted (positive)' if s_ma.mean() > 0 else 'CONTRADICTS prediction (negative)'}")
    print(f"  s_nh(2026)  = {s_level.loc[TREAT_YEAR, 'nh']:+.3f} (spillover diagnostic)")
    print(f"  s_vt(2026)  = {s_level.loc[TREAT_YEAR, 'vt']:+.3f} (contaminated, not decisive)")

    # ---- Hour uniformity: >= 20 of 24 hours share a sign ----
    hourly = basis[basis["year"].isin([TREAT_YEAR - 1, TREAT_YEAR])]
    by_hour = hourly.groupby(["year", "hour"])[TREATED].mean().unstack(0)
    d_hour = by_hour[TREAT_YEAR] - by_hour[TREAT_YEAR - 1]
    n_neg, n_pos = int((d_hour < 0).sum()), int((d_hour > 0).sum())
    dominant = max(n_neg, n_pos)
    d_hour.to_csv(OUTDIR / "me_hourly_delta_2026.csv")

    print("\n=== HOUR UNIFORMITY: delta ME basis by hour, 2026 vs 2025 ===")
    print(f"  hours negative {n_neg}, positive {n_pos}, dominant sign in {dominant}/24")
    print(f"  pre-registered threshold >= 20/24 -> "
          f"{'UNIFORM (consistent with a firm block)' if dominant >= 20 else 'NOT uniform (dispatch-following)'}")
    print(f"  range {d_hour.min():+.2f} to {d_hour.max():+.2f} $/MWh")

    # ---- Secondary: volatility, predicted negative or null ----
    placebo_v = s_vol.loc[2017:2025, PLACEBO_ZONES].to_numpy().ravel()
    placebo_v = placebo_v[~np.isnan(placebo_v)]
    s_me_v = s_vol.loc[TREAT_YEAR, TREATED]
    n_below_v, p_v = rank_p(s_me_v, placebo_v)
    print("\n=== SECONDARY: ME basis volatility (predicted negative or null) ===")
    print(f"  V_ME(2025) = {vol.loc[TREAT_YEAR - 1, TREATED]:.3f}, "
          f"V_ME(2026) = {vol.loc[TREAT_YEAR, TREATED]:.3f} $/MWh per hour")
    print(f"  s_ME_vol(2026)   = {s_me_v:+.3f}  (cells <= : {n_below_v})")
    print(f"  one-sided rank p = {p_v:.4f}")
    print(f"  -> {'as predicted (down or flat)' if s_me_v <= 0 else 'CONTRADICTS the firm-block mechanism (volatility UP)'}")

    # ---- Robustness: median basis ----
    s_med = standardize(median)
    print("\n=== ROBUSTNESS ===")
    print(f"  median-basis s_ME(2026) = {s_med.loc[TREAT_YEAR, TREATED]:+.3f} "
          f"(primary used the mean: {s_me:+.3f})")
    print(f"\nwrote CSVs to {OUTDIR}/")


if __name__ == "__main__":
    main()
