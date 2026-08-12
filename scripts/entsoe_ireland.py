# scripts/entsoe_ireland.py
"""Did Irish load shape change as data centres grew to 23.7% of consumption?

Approach A -- level-normalized shape statistics per period, for Ireland and the
Netherlands, joined to the CSO dose series.
Approach B -- normalized diurnal profiles per year, the mechanism plot.

WHICH COMPARISONS ARE LICENSED (design section 4.1) -- this constrains what
the note may print:

  * pt_ratio: IE/NL HOURLY vs the ISONE HOURLY figure (1.467) is comparable.
    The UKPN 1.05 is NOT -- half-hourly, per-site, a utilisation ratio rather
    than MW. Quote it only as a facility-level contrast in prose, never in the
    same column as a zonal number.
  * vol_norm: an hourly panel derived by AVERAGING sub-hourly data is low-pass
    filtered, so it reads smoother than natively-metered hourly. LEVELS are
    not comparable to the 11 existing panels; WITHIN-ZONE TRENDS are, and the
    trend is what this tests.

THREE MEASUREMENT RULES, each added because the raw corpus violates the
assumption the plan's original formula made:

  1. Gradients are computed only across CONSECUTIVE slots. IE_CTA is missing
     3,774 of 203,604 native slots (1.85%) in 661 runs, the largest a 19-day
     outage in Feb 2026. Dividing a multi-day jump by freq_minutes invents
     volatility. The bias is small in aggregate (+0.69%) but varies by year
     from +0.07% to +2.31% -- and a trend is exactly what this design tests,
     so a year-varying bias is disqualifying. NL has zero gaps, so the mask is
     a no-op there; both zones run the identical code path deliberately, so a
     treated-vs-control difference can never be a code difference.
  2. Daily statistics (pt_ratio, night_floor) use only COMPLETE days. A day
     holding 4 of 24 hours contributes a garbage max/min to the median.
  3. mean_abs_grad -- the RAW numerator -- is reported next to vol_norm.
     vol_norm = mean|dLoad| / mean_load falls whenever load grows, whatever
     volatility does. This project has already retracted one "normalized
     volatility falls" claim that turned out to be a denominator effect
     (ISONE, shrinking load). Ireland is the mirror case: load GREW 30%.
     Reporting both makes the decomposition unavoidable rather than optional.

This is not a causal design: one treated unit, one control, n=44 quarters, and
a heuristically-constructed covariate.

Usage: .venv/bin/python scripts/entsoe_ireland.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from surg.preprocessing.entsoe_panel import zone_panel

OUT = Path("outputs/entsoe")
ZONES = {"IE_CTA": "Ireland", "NL": "Netherlands"}
NATIVE_STEP = {"IE_CTA": 30, "NL": 15}
STATISTICS = ["vol_norm", "mean_abs_grad", "pt_ratio", "load_factor", "night_floor"]

# Dutch data-centre share of national electricity, percent, by year.
# Source: CBS (Statistics Netherlands), "Data centres consume 4.6 percent of
# the Netherlands' electricity" (2025); 2024 is provisional. Definition:
# electricity connections where the data centre IS the main activity, which
# excludes university and hospital data halls. ~200 sites, of which ~45 large
# ones are ~90% of the total.
#
# This series exists because the design's desk claim that the Dutch DC share
# was "flat at ~4.6%" is FALSE -- 4.6% is the 2024 endpoint, and the share
# TRIPLED from 1.48% in 2017. The Netherlands is a LOW-DOSE control, not a
# zero-dose placebo, and every write-up must say so. Note the definitions are
# not identical to CSO's Irish heuristic, so cross-country LEVELS are only
# roughly comparable; the within-country trends are the usable part.
NL_DC_SHARE_PCT = {
    2017: 1.48, 2018: 2.09, 2019: 2.42, 2020: 2.82,
    2021: 3.29, 2022: 3.98, 2023: 4.19, 2024: 4.58,
}
DOSE_WINDOW = (2017, 2024)  # the years CBS covers on both sides

# THE DUTCH SERIES BREAKS AT 2023-04, so every window ending after 2022 compares
# a pre-break Irish endpoint against a post-break Dutch one.
#
# Measured in scripts/entsoe_solar.py: the Dutch April/March mean-load ratio is
# 1.0493 against a 0.9247 median in every other year (+1,548 MW), and the
# April-minus-March MIDDAY deviation jumps +1,395 MW against a -123 MW median.
# The step being midday-concentrated is what rules out a flat industrial
# recovery from the 2022 gas crisis, since a flat addition cannot move a
# deviation from a day's own mean. Ireland shows no such step (2023 excess
# 0.9853). See docs/research-notes/L-solar-metering-artifact.md.
#
# Both windows are reported rather than one replacing the other: the published
# window reproduces the K-note exactly, and the break-free window is what any
# treated-vs-control claim must now rest on.
SHAPE_WINDOWS = {
    "published_2015_2025": ("2015", "2025"),
    "break_free_2015_2022": ("2015", "2022"),
}
DOSE_WINDOWS = {
    "published_2017_2024": (2017, 2024),
    "break_free_2017_2022": (2017, 2022),
}
LAST_CLEAN_QUARTER = "2022Q4"


def shape_statistics(panel: pd.DataFrame, *, freq_minutes: int) -> pd.Series:
    """Level-normalized shape statistics for one block of a load panel.

    Gradients skip non-consecutive pairs and daily statistics skip incomplete
    days; both counts are returned so the exclusions stay visible.
    """
    load = panel["load_mw"]
    mean_load = load.mean()

    step = pd.Timedelta(minutes=freq_minutes)
    deltas = panel["timestamp_utc"].diff()
    contiguous = deltas == step
    # The first row's diff is NaT by construction, not a gap.
    n_spurious = int((~contiguous).sum() - deltas.isna().sum())
    grad = (load.diff().abs() / freq_minutes)[contiguous]

    slots_per_day = 24 * 60 // freq_minutes
    day = panel["timestamp_local"].dt.date
    per_day = panel.groupby(day)["load_mw"]
    complete = per_day.size() == slots_per_day
    day_max = per_day.max()[complete]
    day_min = per_day.min()[complete]
    day_mean = per_day.mean()[complete]
    valid = day_min > 0

    return pd.Series(
        {
            "n_obs": len(panel),
            "n_days_used": int(valid.sum()),
            "n_days_dropped": int(len(per_day.size()) - valid.sum()),
            "n_spurious_diffs": n_spurious,
            "mean_load_mw": mean_load,
            "mean_abs_grad": grad.mean(),
            "vol_norm": grad.mean() / mean_load,
            "pt_ratio": (day_max[valid] / day_min[valid]).median(),
            "load_factor": mean_load / load.max(),
            "night_floor": (day_min[valid] / day_mean[valid]).median(),
        }
    )


def by_period(panel: pd.DataFrame, *, freq_minutes: int, freq: str) -> pd.DataFrame:
    """Shape statistics grouped by year ('Y') or quarter ('Q')."""
    work = panel.dropna(subset=["load_mw"]).copy()
    key = work["timestamp_local"].dt.to_period(freq)
    rows = []
    for period, block in work.groupby(key):
        if len(block) < 100:
            continue
        stats = shape_statistics(block, freq_minutes=freq_minutes)
        stats["period"] = str(period)
        rows.append(stats)
    return pd.DataFrame(rows).set_index("period")


def diurnal_profile(panel: pd.DataFrame, year: int) -> pd.Series:
    """Mean daily profile for one year, each day normalized by its own mean."""
    work = panel[panel["timestamp_local"].dt.year == year].dropna(subset=["load_mw"])
    if work.empty:
        return pd.Series(dtype=float)
    work = work.copy()
    work["date"] = work["timestamp_local"].dt.date
    work["slot"] = (
        work["timestamp_local"].dt.hour * 60 + work["timestamp_local"].dt.minute
    )
    day_mean = work.groupby("date")["load_mw"].transform("mean")
    work["normalized"] = work["load_mw"] / day_mean
    return work.groupby("slot")["normalized"].mean()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {}

    native_panels, hourly_panels = {}, {}
    for key in ZONES:
        native, hourly = zone_panel("load", key, value_name="load_mw")
        native_panels[key], hourly_panels[key] = native, hourly

    # --- Approach A -------------------------------------------------------
    for key, label in ZONES.items():
        annual = by_period(hourly_panels[key], freq_minutes=60, freq="Y")
        quarterly = by_period(hourly_panels[key], freq_minutes=60, freq="Q")
        annual_native = by_period(
            native_panels[key], freq_minutes=NATIVE_STEP[key], freq="Y"
        )

        annual.to_csv(OUT / f"shape_annual_hourly_{key}.csv")
        quarterly.to_csv(OUT / f"shape_quarterly_hourly_{key}.csv")
        annual_native.to_csv(OUT / f"shape_annual_native_{key}.csv")
        results[key] = {
            "label": label,
            "annual_hourly": annual.to_dict(orient="index"),
            "annual_native": annual_native.to_dict(orient="index"),
        }
        print(f"\n=== {label} ({key}) annual, hourly panel ===")
        print(annual.round(4).to_string())

    # --- Numerator vs denominator ----------------------------------------
    # vol_norm falls whenever mean_load grows. Print the decomposition so the
    # write-up cannot quote a ratio without the two terms behind it.
    decomposition_by_window = {}
    for window_name, (start, end) in SHAPE_WINDOWS.items():
        banner = (
            "  [DUTCH ENDPOINT IS POST-BREAK -- not a valid control comparison]"
            if end > "2022"
            else "  [break-free for BOTH zones]"
        )
        print(f"\n=== vol_norm decomposition, {start} -> {end} ==={banner}")
        decomposition = {}
        for key, label in ZONES.items():
            annual = pd.read_csv(OUT / f"shape_annual_hourly_{key}.csv", index_col=0)
            # A CSV round-trip turns the annual period label "2015" back into an
            # int64 index; force it to string so the lookups below match.
            annual.index = annual.index.astype(str)
            if start not in annual.index or end not in annual.index:
                continue
            first, last = annual.loc[start], annual.loc[end]
            ratios = {
                "mean_load_ratio": last.mean_load_mw / first.mean_load_mw,
                "raw_grad_ratio": last.mean_abs_grad / first.mean_abs_grad,
                "vol_norm_ratio": last.vol_norm / first.vol_norm,
                "pt_ratio_first": first.pt_ratio, "pt_ratio_last": last.pt_ratio,
                "night_floor_first": first.night_floor,
                "night_floor_last": last.night_floor,
                "load_factor_first": first.load_factor,
                "load_factor_last": last.load_factor,
            }
            decomposition[key] = ratios
            print(
                f"  {label:<12} mean_load x{ratios['mean_load_ratio']:.3f}  "
                f"raw |dLoad| x{ratios['raw_grad_ratio']:.3f}  "
                f"vol_norm x{ratios['vol_norm_ratio']:.3f}   "
                f"pt_ratio {first.pt_ratio:.3f}->{last.pt_ratio:.3f}  "
                f"night_floor {first.night_floor:.3f}->{last.night_floor:.3f}  "
                f"load_factor {first.load_factor:.3f}->{last.load_factor:.3f}"
            )
        decomposition_by_window[window_name] = decomposition
    results["decomposition_by_window"] = decomposition_by_window
    # Preserved under its original key so the K-note's numbers stay addressable.
    results["decomposition_2015_2025"] = decomposition_by_window["published_2015_2025"]

    # --- Dose join --------------------------------------------------------
    cso = pd.read_parquet("data/raw/cso/mec02.parquet")
    dose = cso.set_index(cso["quarter"].astype(str))["dc_share"]

    correlations = {}
    for key in ZONES:
        quarterly = pd.read_csv(OUT / f"shape_quarterly_hourly_{key}.csv", index_col=0)
        joined = quarterly.join(dose, how="inner")
        if joined.empty:
            raise ValueError(
                "dose join produced zero rows -- period labels do not match. "
                f"shape index sample: {list(quarterly.index[:3])}; "
                f"dose index sample: {list(dose.index[:3])}"
            )
        # The quarterly correlation pools quarters on both sides of the Dutch
        # 2023-04 break, so it is computed twice: on everything (as published)
        # and on the break-free window only.
        clean = joined[joined.index <= LAST_CLEAN_QUARTER]
        stats = {}
        for column in STATISTICS:
            sub = joined[[column, "dc_share"]].dropna()
            sub_clean = clean[[column, "dc_share"]].dropna()
            stats[column] = {
                "n": len(sub),
                "pearson_r": float(sub[column].corr(sub["dc_share"])),
                "first": float(sub[column].iloc[0]) if len(sub) else None,
                "last": float(sub[column].iloc[-1]) if len(sub) else None,
                "n_break_free": len(sub_clean),
                "pearson_r_break_free": float(
                    sub_clean[column].corr(sub_clean["dc_share"])
                )
                if len(sub_clean) > 2
                else None,
            }
        correlations[key] = stats
        joined.to_csv(OUT / f"shape_quarterly_with_dose_{key}.csv")

    print("\n=== correlation with Irish DC share (NL row is the PLACEBO) ===")
    for key, stats in correlations.items():
        print(f"\n{ZONES[key]}:")
        for column, values in stats.items():
            clean_r = values["pearson_r_break_free"]
            clean_txt = f"  |  break-free r={clean_r:+.3f} (n={values['n_break_free']})" if clean_r is not None else ""
            print(
                f"  {column:<14} r={values['pearson_r']:+.3f}  n={values['n']}  "
                f"{values['first']:.6f} -> {values['last']:.6f}{clean_txt}"
            )
    results["correlations"] = correlations

    # --- Dose-response ----------------------------------------------------
    # The control is LOW-dose, not zero-dose (see NL_DC_SHARE_PCT). So the
    # placebo argument is replaced by a stronger one: if data centres drove the
    # shape change, the response should scale with the dose. Only the
    # DIMENSIONLESS statistics are compared across countries here -- raw
    # mean_abs_grad is in MW/min and the Dutch system is ~3.4x larger, so its
    # per-pp figure is not comparable to Ireland's and is excluded.
    cso_annual = cso.copy()
    cso_annual["year"] = cso_annual["period"].dt.year
    ie_share = cso_annual.groupby("year").apply(
        lambda d: 100 * d["dc_gwh"].sum() / d["total_gwh"].sum(), include_groups=False
    )

    dose_by_window = {}
    for window_name, (first_year, last_year) in DOSE_WINDOWS.items():
        dose = {
            "IE_CTA": ie_share[last_year] - ie_share[first_year],
            "NL": NL_DC_SHARE_PCT[last_year] - NL_DC_SHARE_PCT[first_year],
        }
        ratio = {
            "IE_CTA": ie_share[last_year] / ie_share[first_year],
            "NL": NL_DC_SHARE_PCT[last_year] / NL_DC_SHARE_PCT[first_year],
        }
        banner = (
            "  [DUTCH ENDPOINT IS POST-BREAK]" if last_year > 2022
            else "  [break-free for BOTH zones]"
        )
        print(f"\n=== dose-response, {first_year} -> {last_year} ==={banner}")
        print(
            f"  dose increment: Ireland {dose['IE_CTA']:+.2f} pp (x{ratio['IE_CTA']:.2f})  "
            f"Netherlands {dose['NL']:+.2f} pp (x{ratio['NL']:.2f})"
        )
        dose_response = {"dose_pp": dose, "dose_ratio": ratio, "per_pp": {}}
        for key, label in ZONES.items():
            annual = pd.read_csv(OUT / f"shape_annual_hourly_{key}.csv", index_col=0)
            annual.index = annual.index.astype(str)
            f_row, l_row = annual.loc[str(first_year)], annual.loc[str(last_year)]
            per_pp = {
                column: float((l_row[column] - f_row[column]) / dose[key])
                for column in ("vol_norm", "pt_ratio", "night_floor")
            }
            dose_response["per_pp"][key] = per_pp
            print(f"  {label:<12} " + "  ".join(f"{c}={v:+.6f}/pp" for c, v in per_pp.items()))
        dose_by_window[window_name] = dose_response
    results["dose_response_by_window"] = dose_by_window
    results["dose_response"] = dose_by_window["published_2017_2024"]

    # --- Approach B: diurnal decomposition --------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, (key, label) in zip(axes, ZONES.items(), strict=True):
        for year in (2015, 2020, 2025):
            profile = diurnal_profile(native_panels[key], year)
            if profile.empty:
                continue
            ax.plot(profile.index / 60.0, profile.values, label=str(year))
        ax.axhline(1.0, color="grey", linewidth=0.6, linestyle=":")
        ax.set_title(f"{label} — normalized daily profile")
        ax.set_xlabel("hour of local day")
        ax.legend()
    axes[0].set_ylabel("load ÷ that day's mean")
    fig.tight_layout()
    fig.savefig(OUT / "fig_diurnal_profiles.png", dpi=150)
    plt.close(fig)

    # --- Trend figure -----------------------------------------------------
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))
    flat = axes.ravel()
    for ax, column in zip(flat, STATISTICS, strict=False):
        for key, label in ZONES.items():
            annual = pd.read_csv(OUT / f"shape_annual_hourly_{key}.csv", index_col=0)
            ax.plot(annual.index.astype(str), annual[column], marker="o", label=label)
        ax.set_title(column)
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=8)
    flat[len(STATISTICS)].axis("off")
    fig.tight_layout()
    fig.savefig(OUT / "fig_shape_trends.png", dpi=150)
    plt.close(fig)

    (OUT / "ireland_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nwrote {OUT}/ireland_results.json, fig_diurnal_profiles.png, fig_shape_trends.png")


if __name__ == "__main__":
    main()
