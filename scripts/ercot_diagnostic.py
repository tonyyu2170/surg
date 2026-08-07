"""Stage 1 ERCOT load volatility diagnostic.

Answers two questions:
  1. Is ERCOT load volatile, and is its volatility rising?
  2. Does hourly price track load level more than load volatility?

Usage: .venv/bin/python scripts/ercot_diagnostic.py
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from surg.preprocessing.ercot_features import (  # noqa: E402
    ZONES,
    add_zone_gradient_columns,
    hour_ending_to_beginning,
)

RAW = Path("data/raw/ercot")
PANEL = Path("data/interim/ercot_diagnostic_panel.parquet")
FIGDIR = Path("outputs/ercot_diagnostic")

# ERCOT publishes four load schema families. 2017 is the first year whose zone
# names match ZONES: 2016 uses FAR_WEST/NORTH_C/SOUTHERN/SOUTH_C with a
# `Hour_End` Timestamp, 2015 and earlier are .xls, and pre-April-2003 files use
# 11 control areas rather than 8 weather zones.
FIRST_ZONE_YEAR = 2017
# DOM panel starts 2022-10-02; matched window for the price comparison.
DOM_START = pd.Timestamp("2022-10-02")

# Extracted filenames vary in case across years (`native_load_2017.xlsx`,
# `Native_Load_2019.xlsx`). Matching case-insensitively rather than leaning on
# macOS's case-insensitive filesystem.
LOAD_FILE = re.compile(r"native_load_(\d{4})\.xlsx$", re.I)


def load_native_load() -> pd.DataFrame:
    """Read every native_load_<YYYY>.xlsx into one hour-beginning frame."""
    frames = []
    dropped_total = 0
    for path in sorted(RAW.iterdir()):
        match = LOAD_FILE.match(path.name)
        if not match or int(match.group(1)) < FIRST_ZONE_YEAR:
            continue

        raw = pd.read_excel(path)
        raw = raw.rename(columns={c: c.strip().upper() for c in raw.columns})
        # 2018-2020 spell it `HourEnding`; every other year `Hour Ending`.
        raw = raw.rename(
            columns={"HOUR ENDING": "Hour Ending", "HOURENDING": "Hour Ending"}
        )
        missing = [z for z in ZONES if z not in raw.columns]
        if missing:
            raise ValueError(f"{path.name} missing zones: {missing}")

        keep = raw[["Hour Ending", *ZONES]].copy()

        # Native_Load_2026.xlsx republishes all of May 2026 a second time as a
        # contiguous block of 744 rows identical across every column. Dropping
        # exact duplicates here -- while the raw `Hour Ending` label is still
        # present -- is lossless and cannot touch the DST fall-back pair, whose
        # two rows carry *different* labels (`02:00` vs `02:00 DST`).
        # This must happen before hour_ending_to_beginning: otherwise the
        # repeats are flagged `dst_transition_hour`, and assert_panel_quality
        # (which only inspects non-DST rows) passes over them in silence.
        deduped = keep.drop_duplicates()
        if len(deduped) != len(keep):
            dropped_total += len(keep) - len(deduped)
            print(
                f"  {path.name}: dropped {len(keep) - len(deduped)} exact "
                f"duplicate rows (ERCOT republication)"
            )
        frames.append(deduped)

    if not frames:
        raise RuntimeError(f"no load files matched in {RAW}")
    if dropped_total:
        print(f"  total exact-duplicate rows dropped: {dropped_total}")

    combined = pd.concat(frames, ignore_index=True)
    combined = hour_ending_to_beginning(combined)
    combined = combined.rename(columns={z: f"load_mw_{z}" for z in ZONES})
    return combined.sort_values("datetime_beginning_cpt").reset_index(drop=True)


def assert_panel_quality(panel: pd.DataFrame) -> None:
    """Fail loudly on the failure modes that previously bit this project."""
    non_dst = panel.loc[~panel["dst_transition_hour"], "datetime_beginning_cpt"]
    dupes = non_dst.duplicated().sum()
    if dupes:
        raise AssertionError(f"{dupes} duplicate non-DST timestamps")

    # One fall-back pair per completed year; anything beyond that is a
    # republication like the 2026 May block, not a DST artefact. Without this
    # the check above is vacuous, since duplicates hide inside the DST flag.
    flagged = int(panel["dst_transition_hour"].sum())
    span_years = panel["datetime_beginning_cpt"].dt.year.nunique()
    if flagged > 2 * span_years:
        raise AssertionError(
            f"{flagged} rows flagged dst_transition_hour across {span_years} "
            f"years; expected at most {2 * span_years} (one pair per year)"
        )

    for zone in ZONES:
        col = f"load_mw_{zone}"
        if panel[col].isna().any():
            raise AssertionError(f"{col} contains NaN — do not interpolate, investigate")

    span = panel["datetime_beginning_cpt"]
    expected = int((span.max() - span.min()).total_seconds() // 3600) + 1
    actual = len(panel)
    if abs(expected - actual) > 48:
        raise AssertionError(f"gap detected: expected ~{expected} rows, got {actual}")


def load_prices() -> pd.DataFrame:
    """Read RTM settlement point prices, hourly mean per settlement point.

    Files are 15-minute (Delivery Interval 1-4); aggregate to hourly to match
    the load panel. Negative prices are real (ERCOT's floor is -$251/MWh) and
    are NOT clipped -- their prevalence is itself a gate input.

    Known limitation, deliberately not engineered around: on the DST fall-back
    hour ERCOT marks the repeated hour with `Repeated Hour Flag = Y` but gives
    it the *same* Delivery Date and Delivery Hour as the original. Since the
    timestamp is built from date + hour, both hours average into a single
    value -- one hour per year, four years. The load frame keeps two rows for
    that hour, the price frame one, and a left many-to-one merge preserves the
    row count, so this is neither a crash nor a row-count problem.
    """
    frames = []
    for path in sorted(RAW.glob("*RTMLZHBSPP_*.xlsx")):
        year = int(path.stem.split("_")[-1])
        if year < DOM_START.year:
            continue
        print(f"  prices {path.name}", flush=True)
        book = pd.read_excel(path, sheet_name=None)
        for sheet in book.values():
            cols = {c.strip().lower(): c for c in sheet.columns}
            frames.append(
                pd.DataFrame(
                    {
                        "date": sheet[cols["delivery date"]],
                        "hour_str": sheet[cols["delivery hour"]].astype(str),
                        "settlement_point": sheet[cols["settlement point name"]],
                        "price": pd.to_numeric(
                            sheet[cols["settlement point price"]], errors="coerce"
                        ),
                    }
                )
            )

    raw = pd.concat(frames, ignore_index=True)

    # Loud, not silent: the load archives taught us ERCOT mixes datetime cells
    # into text columns, where a bare parse yields NaT without complaint.
    dates = pd.to_datetime(raw["date"].astype(str), format="%m/%d/%Y", errors="coerce")
    if dates.isna().any():
        bad = raw.loc[dates.isna(), "date"].head(3).tolist()
        raise ValueError(f"unparseable Delivery Date values: {bad}")

    # Delivery Hour is 1-24 (hour-ending); subtract 1 for hour-beginning.
    hours = pd.to_numeric(raw["hour_str"], errors="coerce") - 1
    if hours.isna().any():
        raise ValueError("unparseable Delivery Hour values")
    raw["datetime_beginning_cpt"] = dates + pd.to_timedelta(hours, unit="h")

    hourly = (
        raw.groupby(["datetime_beginning_cpt", "settlement_point"])["price"]
        .mean()
        .unstack("settlement_point")
    )
    hourly.columns = [f"total_lmp_rt_{c}" for c in hourly.columns]
    return hourly.reset_index()


def build_panel() -> pd.DataFrame:
    panel = load_native_load()
    panel = add_zone_gradient_columns(panel)
    assert_panel_quality(panel)

    prices = load_prices()
    before = len(panel)
    # `validate` names the invariant the row-count check only detects after the
    # fact: the load side carries two rows for each DST fall-back hour, the
    # price side exactly one, so this must be many-to-one. A duplicated
    # timestamp on the price side would multiply load rows instead of raising.
    panel = panel.merge(
        prices, on="datetime_beginning_cpt", how="left", validate="m:1"
    )
    if len(panel) != before:
        raise AssertionError(f"price join changed row count: {before} -> {len(panel)}")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


def data_quality_report(panel: pd.DataFrame) -> pd.DataFrame:
    """Print rows/year, gaps, and negative-price share. Read before interpreting."""
    print("\n=== ROWS PER YEAR ===")
    per_year = panel.groupby(panel["datetime_beginning_cpt"].dt.year).size()
    print(per_year.to_string())

    price_cols = [c for c in panel.columns if c.startswith("total_lmp_rt_")]
    rows = []
    matched = panel[panel["datetime_beginning_cpt"] >= DOM_START]
    for col in price_cols:
        series = matched[col].dropna()
        if series.empty:
            continue
        rows.append(
            {
                "settlement_point": col.replace("total_lmp_rt_", ""),
                "n": len(series),
                "negative_share": (series < 0).mean(),
                "median": series.median(),
                "p99": series.quantile(0.99),
            }
        )
    report = pd.DataFrame(rows).sort_values("negative_share", ascending=False)
    print("\n=== PRICE QUALITY (DOM-matched window) ===")
    print(report.to_string(index=False))
    print(
        "\nGATE: if negative_share is large for the West points, "
        "their correlations are uninterpretable — see spec gate criterion."
    )
    FIGDIR.mkdir(parents=True, exist_ok=True)
    report.to_csv(FIGDIR / "price_quality.csv", index=False)
    return report


def trend_tables(panel: pd.DataFrame) -> pd.DataFrame:
    """Annual level and volatility per zone, raw and load-normalized.

    Normalization matters: the DOM result was volatility flat/falling while
    load rose, so raw ramps would confound growth with volatility.
    """
    year = panel["datetime_beginning_cpt"].dt.year
    rows = []
    for zone in ZONES:
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
    FIGDIR.mkdir(parents=True, exist_ok=True)
    trends.to_csv(FIGDIR / "trends_by_zone_year.csv", index=False)

    for metric, fname in [
        ("mean_load_mw", "fig2_level_trend.png"),
        ("grad_mean_norm", "fig1_volatility_trend_normalized.png"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 6))
        for zone in ZONES:
            sub = trends[trends["zone"] == zone]
            ax.plot(sub["year"], sub[metric], marker="o", label=zone)
        ax.set_xlabel("year")
        ax.set_ylabel(metric)
        ax.set_title(f"ERCOT {metric} by weather zone")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIGDIR / fname, dpi=150)
        plt.close(fig)

    print(f"\ntrends -> {FIGDIR}")
    return trends


def level_vs_volatility(panel: pd.DataFrame) -> pd.DataFrame:
    """Standardized regression of price on load level vs |gradient|.

    Standardizing puts both predictors on the same scale so their
    coefficients are directly comparable. This is the core Stage 1 question.

    CAVEAT for the write-up: there are no time controls here. Load level and
    price both carry strong diurnal and seasonal structure, so beta_level is
    inflated by both tracking time-of-day. That is acceptable for a
    descriptive horse race, but the DOM finding this gets compared against
    (z_slope sign-flipping under a load-level control) came from a
    specification *with* controls. The two are not directly comparable.
    """
    matched = panel[panel["datetime_beginning_cpt"] >= DOM_START]
    price_cols = [c for c in panel.columns if c.startswith("total_lmp_rt_")]

    rows = []
    for zone in ZONES:
        level_col = f"load_mw_{zone}"
        vol_col = f"load_gradient_abs_mw_per_min_{zone}"
        for col in price_cols:
            data = matched[[level_col, vol_col, col]].dropna()
            if len(data) < 1000:
                continue
            standardized = (data - data.mean()) / data.std()
            exog = sm.add_constant(standardized[[level_col, vol_col]])
            fit = sm.OLS(standardized[col], exog).fit()
            rows.append(
                {
                    "zone": zone,
                    "settlement_point": col.replace("total_lmp_rt_", ""),
                    "beta_level": fit.params[level_col],
                    "beta_volatility": fit.params[vol_col],
                    "r2": fit.rsquared,
                    "n": len(data),
                }
            )

    race = pd.DataFrame(rows)
    race["level_wins"] = race["beta_level"].abs() > race["beta_volatility"].abs()
    FIGDIR.mkdir(parents=True, exist_ok=True)
    race.to_csv(FIGDIR / "fig3_level_vs_volatility.csv", index=False)

    print("\n=== LEVEL vs VOLATILITY (standardized betas) ===")
    print(race.to_string(index=False))
    print(f"\nlevel wins in {race['level_wins'].sum()} of {len(race)} zone-point pairs")
    return race


if __name__ == "__main__":
    panel = build_panel()
    data_quality_report(panel)
    trend_tables(panel)
    level_vs_volatility(panel)
