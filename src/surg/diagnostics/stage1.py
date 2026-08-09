"""Market-agnostic Stage-1 diagnostic computations.

Mirrored from scripts/ercot_diagnostic.py (shipped 2026-08-07) with the
market parameters lifted out; that script stays untouched per the design
spec. Pure computation + figure/CSV writes into a caller-supplied figdir.

Conventions every caller must satisfy:
  * `time_col` is naive local prevailing (or fixed-offset) hour-BEGINNING.
  * one `load_mw_<zone>` column per zone; `dst_transition_hour` bool column.
  * gradients are added via `add_zone_gradients` so the volatility measure
    is provably identical to DOM/ERCOT (delegates to
    `add_load_gradient_columns`).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from surg.preprocessing.features import add_load_gradient_columns  # noqa: E402


def add_zone_gradients(
    df: pd.DataFrame, zones: list[str], *, time_col: str
) -> pd.DataFrame:
    """Add `load_gradient_abs_mw_per_min_<zone>` for each zone.

    Same shim as ercot_features.add_zone_gradient_columns: rename each zone
    into the DOM column names, delegate, rename out. `features.py` is not
    modified. Requires sorted input because the underlying diff is
    positional.
    """
    if not df[time_col].is_monotonic_increasing:
        raise ValueError(f"add_zone_gradients requires sorted, non-decreasing {time_col}")

    out = df.copy()
    for zone in zones:
        shim = pd.DataFrame(
            {
                "datetime_beginning_ept": out[time_col],
                "dom_load_mw": out[f"load_mw_{zone}"],
            }
        )
        gradients = add_load_gradient_columns(shim, freq_minutes=60)
        out[f"load_gradient_abs_mw_per_min_{zone}"] = gradients[
            "dom_load_gradient_abs_mw_per_min"
        ].to_numpy()
    return out


def assert_panel_quality(
    panel: pd.DataFrame,
    zones: list[str],
    *,
    time_col: str,
    dst_pairs_per_year: int = 1,
) -> None:
    """Fail loudly on the failure modes that previously bit this project.

    dst_pairs_per_year: 1 for prevailing-time markets (one fall-back pair
    per year), 0 for fixed-offset markets (MISO/IESO-style) where any
    duplicate is a republication, never DST.
    """
    non_dst = panel.loc[~panel["dst_transition_hour"], time_col]
    dupes = non_dst.duplicated().sum()
    if dupes:
        raise AssertionError(f"{dupes} duplicate non-DST timestamps")

    flagged = int(panel["dst_transition_hour"].sum())
    span_years = panel[time_col].dt.year.nunique()
    budget = 2 * dst_pairs_per_year * span_years
    if flagged > budget:
        raise AssertionError(
            f"{flagged} rows flagged dst_transition_hour across {span_years} "
            f"years; expected at most {budget}"
        )

    for zone in zones:
        col = f"load_mw_{zone}"
        if panel[col].isna().any():
            raise AssertionError(f"{col} contains NaN — do not interpolate, investigate")

    span = panel[time_col]
    expected = int((span.max() - span.min()).total_seconds() // 3600) + 1
    if abs(expected - len(panel)) > 48:
        raise AssertionError(f"gap detected: expected ~{expected} rows, got {len(panel)}")


def data_quality_report(
    panel: pd.DataFrame,
    price_cols: list[str],
    *,
    time_col: str,
    window_start: pd.Timestamp,
    figdir: Path,
) -> pd.DataFrame:
    """Rows/year + per-price-column negative share. Read before interpreting."""
    print("\n=== ROWS PER YEAR ===")
    print(panel.groupby(panel[time_col].dt.year).size().to_string())

    matched = panel[panel[time_col] >= window_start]
    rows = []
    for col in price_cols:
        series = matched[col].dropna()
        if series.empty:
            continue
        rows.append(
            {
                "price_series": col,
                "n": len(series),
                "negative_share": (series < 0).mean(),
                "median": series.median(),
                "p99": series.quantile(0.99),
            }
        )
    report = pd.DataFrame(rows).sort_values("negative_share", ascending=False)
    print("\n=== PRICE QUALITY (horse-race window) ===")
    print(report.to_string(index=False))
    figdir.mkdir(parents=True, exist_ok=True)
    report.to_csv(figdir / "price_quality.csv", index=False)
    return report


def trend_tables(
    panel: pd.DataFrame,
    zones: list[str],
    *,
    time_col: str,
    figdir: Path,
    market: str,
) -> pd.DataFrame:
    """Annual level and volatility per zone, raw and load-normalized."""
    year = panel[time_col].dt.year
    rows = []
    for zone in zones:
        grouped = panel.groupby(year)
        mean_load = grouped[f"load_mw_{zone}"].mean()
        grad = grouped[f"load_gradient_abs_mw_per_min_{zone}"]
        frame = pd.DataFrame(
            {
                "zone": zone,
                "mean_load_mw": mean_load,
                "peak_load_mw": grouped[f"load_mw_{zone}"].max(),
                "grad_mean": grad.mean(),
                "grad_p95": grad.quantile(0.95),
            }
        )
        frame["grad_mean_norm"] = frame["grad_mean"] / frame["mean_load_mw"]
        frame["grad_p95_norm"] = frame["grad_p95"] / frame["mean_load_mw"]
        rows.append(frame.reset_index(names="year"))

    trends = pd.concat(rows, ignore_index=True)
    figdir.mkdir(parents=True, exist_ok=True)
    trends.to_csv(figdir / "trends_by_zone_year.csv", index=False)

    for metric, fname in [
        ("mean_load_mw", "fig2_level_trend.png"),
        ("grad_mean_norm", "fig1_volatility_trend_normalized.png"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 6))
        for zone in zones:
            sub = trends[trends["zone"] == zone]
            ax.plot(sub["year"], sub[metric], marker="o", label=zone)
        ax.set_xlabel("year")
        ax.set_ylabel(metric)
        ax.set_title(f"{market} {metric} by zone")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(figdir / fname, dpi=150)
        plt.close(fig)

    print(f"\ntrends -> {figdir}")
    return trends


def level_vs_volatility(
    panel: pd.DataFrame,
    zones: list[str],
    price_cols: list[str],
    *,
    time_col: str,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    figdir: Path,
    market: str,
    label: str,
    min_rows: int = 1000,
) -> pd.DataFrame:
    """Standardized regression of price on load level vs |gradient|.

    Same caveat as the ERCOT run: no time controls, so beta_level carries
    shared diurnal/seasonal structure. Descriptive horse race only; not
    comparable to the DOM controlled z_slope specification.

    `label` distinguishes the two windows ("max" and "overlap") in output
    filenames per the 2026-08-09 checkpoint decision.
    """
    matched = panel[(panel[time_col] >= window_start) & (panel[time_col] < window_end)]

    rows = []
    for zone in zones:
        level_col = f"load_mw_{zone}"
        vol_col = f"load_gradient_abs_mw_per_min_{zone}"
        for col in price_cols:
            data = matched[[level_col, vol_col, col]].dropna()
            if len(data) < min_rows:
                continue
            standardized = (data - data.mean()) / data.std()
            exog = sm.add_constant(standardized[[level_col, vol_col]])
            fit = sm.OLS(standardized[col], exog).fit()
            rows.append(
                {
                    "zone": zone,
                    "price_series": col,
                    "beta_level": fit.params[level_col],
                    "beta_volatility": fit.params[vol_col],
                    "r2": fit.rsquared,
                    "n": len(data),
                }
            )

    race = pd.DataFrame(rows)
    if not race.empty:
        race["level_wins"] = race["beta_level"].abs() > race["beta_volatility"].abs()
    figdir.mkdir(parents=True, exist_ok=True)
    race.to_csv(figdir / f"fig3_level_vs_volatility_{label}.csv", index=False)

    print(f"\n=== LEVEL vs VOLATILITY ({market}, {label} window) ===")
    if race.empty:
        print("no zone×price cell met min_rows — check window and price coverage")
    else:
        print(race.to_string(index=False))
        print(f"level wins in {race['level_wins'].sum()} of {len(race)} cells")
    return race


COMMON_OVERLAP_START = pd.Timestamp("2023-01-01")
COMMON_OVERLAP_END = pd.Timestamp("2025-05-01")  # exclusive; = through 2025-04-30
FAR_FUTURE = pd.Timestamp("2030-01-01")
