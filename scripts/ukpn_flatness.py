# scripts/ukpn_flatness.py
"""Is data-centre load actually spiky? The UKPN flatness cut.

Usage: .venv/bin/python scripts/ukpn_flatness.py

Answers agenda item 7 of docs/plans/advisor/2026-08-19-advisor-meeting-agenda.md
against the 96-site, half-hourly UKPN corpus in data/raw/ukpn/. The
proposal assumes data-centre load is spiky and cites two papers; EPRI's
metered facilities say the opposite (load factor 94% hyperscale / 88%
colocation against each facility's own realized peak). This is the first
independent test of that claim on a real multi-site panel.

Three constraints from docs/sources/ukpn-api-constraints.md shape every metric:

  * `hh_utilisation_ratio` is observed kVA / *contracted* maximum import
    capacity. Contracted capacity is a commercial quantity, so levels are
    NOT comparable across sites -- only shapes. Every statistic here is
    therefore a within-site ratio, in which the MIC denominator cancels.
    Test before adding a metric: would it change if UKPN revised one
    site's MIC by 2x? If yes it is not reportable cross-site.
  * 13.1% of values are exactly 0.0, and the zero structure is bimodal:
    a few enormous runs (site offline) plus ~1,700 short dropouts, 754 of
    them a single half-hour. A lone 0.0 inside live operation fakes a
    full-scale ramp down and back up within the hour, which would swamp
    exactly the statistics this project cares about. Zeros are masked,
    never interpolated, and differences are taken only across adjacent
    unmasked pairs exactly 30 minutes apart.
  * `local_timestamp` is UTC despite its name (verified 0 of 5,442,348
    rows differ from `utc_timestamp`). UK demand shapes follow local
    civil time, so the diurnal cut -- and only the diurnal cut -- converts
    to Europe/London. Ramp and dispersion metrics stay in UTC, which also
    keeps the 46/50-interval DST days out of the difference series.

`grad_mean_norm` is deliberately the same quantity as the cross-ISO
Stage-1 diagnostic (src/surg/diagnostics/stage1.py): mean absolute
period-over-period change per minute, divided by the mean level. It is
dimensionless there and here, so UKPN sites land on the same scale as the
eight ISO load panels instead of being an orphan statistic.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAW = Path("data/raw/ukpn")
OUTDIR = Path("outputs/ukpn_flatness")
PROFILE_YEARS = (2023, 2024, 2025, 2026)
FREQ_MINUTES = 30.0

# Cohort thresholds on each site's share of exactly-zero intervals.
CLEAN_MAX_ZERO_SHARE = 0.01
DEGRADED_MAX_ZERO_SHARE = 0.50

# Minimum unmasked intervals for a site (or site-year) to carry a statistic.
MIN_INTERVALS = 5_000
MIN_INTERVALS_YEAR = 10_000
# Timestamps in the cross-site series need this many reporting sites.
MIN_SITES_PER_INTERVAL = 40

SITE = "anonymised_data_centre_name"
RATIO = "hh_utilisation_ratio"
TS = "local_timestamp"


def load_profiles() -> pd.DataFrame:
    """Concatenate the year-partitioned profile exports, sorted per site.

    Export row order is not guaranteed (a July export began on the 25th),
    so the sort is load-bearing for every difference taken downstream.
    """
    frames = [
        pd.read_parquet(RAW / f"ukpn-data-centre-demand-profiles-{year}.parquet")
        for year in PROFILE_YEARS
    ]
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values([SITE, TS], kind="mergesort").reset_index(drop=True)
    return df


def screen_sites(df: pd.DataFrame) -> pd.DataFrame:
    """Per-site zero contamination, span, and cohort assignment."""
    rows = []
    for site, sub in df.groupby(SITE, sort=True):
        is_zero = sub[RATIO] == 0.0
        n = len(sub)
        zero_share = float(is_zero.mean())
        if zero_share >= 1.0:
            cohort = "dead"
        elif zero_share <= CLEAN_MAX_ZERO_SHARE:
            cohort = "clean"
        elif zero_share <= DEGRADED_MAX_ZERO_SHARE:
            cohort = "intermittent"
        else:
            cohort = "mostly_dead"
        rows.append(
            {
                "site": site,
                "dc_type": sub["dc_type"].iloc[0],
                "voltage": sub["cleansed_voltage_level"].iloc[0],
                "n_raw": n,
                "n_zero": int(is_zero.sum()),
                "zero_share": zero_share,
                "n_unmasked": int((~is_zero).sum()),
                "start": sub[TS].min(),
                "end": sub[TS].max(),
                "n_over_one": int((sub[RATIO] > 1.0).sum()),
                "cohort": cohort,
            }
        )
    return pd.DataFrame(rows)


def mic_step_screen(df: pd.DataFrame, screen: pd.DataFrame) -> list[dict]:
    """Do ratios above 1.0 cluster in time, or scatter through the span?

    Within-site metrics only cancel the MIC denominator if MIC is constant
    over the series. A mid-series contract revision puts a step in the
    ratio that reads as an enormous ramp and inflates CV. A contiguous
    block of >1 rows is the signature of a stale-then-revised MIC; rows
    scattered across the whole span are genuine capacity overshoot with a
    stable denominator. Not decidable from this dataset alone -- the
    output is a flag for interpretation, not a correction.
    """
    flagged = []
    for site in screen.loc[screen["n_over_one"] > 0, "site"]:
        sub = df[df[SITE] == site]
        over = sub.loc[sub[RATIO] > 1.0, TS]
        window = sub[(sub[TS] >= over.min()) & (sub[TS] <= over.max())]
        span_days = (sub[TS].max() - sub[TS].min()).days
        flagged.append(
            {
                "site": site,
                "n_over_one": len(over),
                "first_over": over.min().isoformat(),
                "last_over": over.max().isoformat(),
                # Share of the site's full span bracketed by >1 rows, and
                # how dense >1 is inside that bracket. Dense-and-narrow =
                # step; sparse-and-wide = scattered overshoot.
                "over_window_share_of_span": round(
                    (over.max() - over.min()).days / span_days, 4
                )
                if span_days
                else None,
                "density_within_window": round(len(over) / len(window), 4),
            }
        )
    return flagged


def normalized_ramps(ratio: np.ndarray, ts: np.ndarray, live: np.ndarray, step: float) -> np.ndarray:
    """Absolute per-minute changes over adjacent unmasked pairs `step` apart.

    The adjacency check is the whole point: keep a difference only when
    both endpoints are unmasked AND consecutive samples are exactly one
    interval apart. Masking and then diffing without it silently bridges
    gaps -- the 5-min gap-mask bug (2aab67b), where a 5h50m hole read as a
    -4,933 MW excursion. Here it also disposes of the 754 single-interval
    zero dropouts, each of which would otherwise fake a full-scale ramp
    down and back up within the hour.
    """
    gap_ok = np.diff(ts).astype("timedelta64[m]").astype(float) == step
    pair_ok = live[1:] & live[:-1] & gap_ok
    return np.abs(np.diff(ratio))[pair_ok] / step


def shape_stats(sub: pd.DataFrame, min_intervals: int = MIN_INTERVALS) -> dict | None:
    """Within-site shape statistics on the zero-masked series.

    Shared by the pooled and per-year passes so the two cannot drift.
    Every quantity is invariant to the site's contracted-capacity
    denominator -- MIC cancels in a within-site ratio:

      cv                  std / mean
      lf_own_peak         mean / own realized max   <- EPRI's 94%/88% metric
      lf_p99              mean / own p99            <- outlier-robust variant
      grad_mean_norm      mean(|d ratio| / 30 min) / mean   <- Stage-1 scale
      grad_p95_norm       p95 of the same, / mean
      grad_mean_norm_60m  same, resampled to 60 min <- ISO-comparable

    The 60-minute variant exists because the cross-ISO Stage-1 panels are
    hourly. A per-minute rate taken over a 30-minute difference is not
    strictly comparable to one taken over 60 minutes: on any series with
    high-frequency content the shorter interval reads higher. Sampling
    on the hour puts UKPN on the ISO panels' exact footing.

    Returns None when the site has too few unmasked intervals to carry a
    statistic.
    """
    ratio = sub[RATIO].to_numpy()
    ts = sub[TS].to_numpy()
    live = ratio > 0.0
    vals = ratio[live]
    if len(vals) < min_intervals:
        return None

    mean = float(vals.mean())
    deltas = normalized_ramps(ratio, ts, live, FREQ_MINUTES)
    on_hour = sub[TS].dt.minute.to_numpy() == 0
    hourly = normalized_ramps(ratio[on_hour], ts[on_hour], live[on_hour], 60.0)

    return {
        "n_unmasked": int(live.sum()),
        "n_deltas": len(deltas),
        "mean_ratio": mean,
        "cv": float(vals.std(ddof=1) / mean),
        "lf_own_peak": mean / float(vals.max()),
        "lf_p99": mean / float(np.percentile(vals, 99)),
        "grad_mean_norm": float(deltas.mean()) / mean,
        "grad_p95_norm": float(np.percentile(deltas, 95)) / mean,
        "grad_mean_norm_60m": float(hourly.mean()) / mean,
    }


def site_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Pooled whole-span shape statistics, one row per site.

    Secondary to the per-year pass: pooling across 3.4 years exposes these
    numbers to any mid-series MIC revision, which puts a step in the ratio
    that inflates CV and depresses load factor. Measured on the clean
    cohort, the max/min of monthly medians is 1.40 pooled against 1.17
    within-year, so the annual figures in `year_trend` are the defensible
    headline and these are the robustness check.
    """
    rows = []
    for site, sub in df.groupby(SITE, sort=True):
        stats = shape_stats(sub)
        if stats is None:
            continue
        rows.append(
            {
                "site": site,
                "dc_type": sub["dc_type"].iloc[0],
                "voltage": sub["cleansed_voltage_level"].iloc[0],
                **stats,
            }
        )
    return pd.DataFrame(rows)


def diurnal_spread(df: pd.DataFrame, sites: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Peak-hour / trough-hour ratio per site, in Europe/London civil time.

    The only cut that needs the timezone conversion, because it is the
    only one that asks *when* rather than *how much*. Unequal hour-bin
    counts on the two DST days each year are accepted; they move a
    24-hour mean by far less than the effects being measured.
    """
    sub = df[df[SITE].isin(sites)].copy()
    sub = sub[sub[RATIO] > 0.0]
    sub["hour_london"] = sub[TS].dt.tz_convert("Europe/London").dt.hour

    hourly = sub.groupby([SITE, "hour_london"])[RATIO].mean().unstack("hour_london")
    out = pd.DataFrame(
        {
            "site": hourly.index,
            "peak_hour": hourly.idxmax(axis=1).to_numpy(),
            "trough_hour": hourly.idxmin(axis=1).to_numpy(),
            "diurnal_spread": (hourly.max(axis=1) / hourly.min(axis=1)).to_numpy(),
        }
    )
    return out.reset_index(drop=True), hourly


def cross_site_series(df: pd.DataFrame, sites: list[str]) -> pd.DataFrame:
    """Equal-weighted mean-of-ratios across sites, as a one-column panel.

    This is the cheapest thing in the file that speaks to the price
    question: independent site-level spikes average away, synchronized
    ones do not. If the cross-site series is much flatter than the median
    individual site, the sites are moving independently and no aggregate
    swing reaches the system.

    Returned in the same (timestamp, ratio) shape a single site has, so
    `shape_stats` scores it with the identical definitions -- including
    the same within-year treatment, without which the comparison against
    per-site numbers would be unfair in the aggregate's disfavour: a
    3.4-year span carries cross-year drift that a within-year CV does not.

    Named "cross-site mean utilization", never "aggregate demand". With
    no absolute MW and no admissible weighting (the large-demand list
    cannot be filtered to data centres, and the local-authority capacity
    file cannot be joined to anonymised sites) the system-seen aggregate
    is not constructible from this dataset.
    """
    sub = df[df[SITE].isin(sites)]
    sub = sub[sub[RATIO] > 0.0]
    grouped = sub.groupby(TS)[RATIO]
    series = grouped.mean()[grouped.size() >= MIN_SITES_PER_INTERVAL]
    return pd.DataFrame({TS: series.index, RATIO: series.to_numpy()})


def year_trend(df: pd.DataFrame, sites: list[str]) -> pd.DataFrame:
    """Per-site flatness by complete calendar year -- the headline pass.

    Within-year statistics are the defensible ones. A contract revision
    between years cannot contaminate a within-year CV or load factor, and
    an annual load factor is also exactly what EPRI reports, so this is
    what the 94%/88% figures should be compared against.

    2026 is excluded: the panel ends 2026-05-13 and only 9 of 96 sites
    reach that date, so the tail is ragged and a "latest period"
    comparison against it would measure composition, not behaviour.
    """
    sub = df[df[SITE].isin(sites)].copy()
    sub = sub[sub[TS].dt.year < 2026]
    rows = []
    for (site, year), grp in sub.groupby([SITE, sub[TS].dt.year], sort=True):
        stats = shape_stats(grp, min_intervals=MIN_INTERVALS_YEAR)
        if stats is None:
            continue
        rows.append(
            {
                "site": site,
                "year": int(year),
                "dc_type": grp["dc_type"].iloc[0],
                "voltage": grp["cleansed_voltage_level"].iloc[0],
                **stats,
            }
        )
    return pd.DataFrame(rows)


def balanced(trend: pd.DataFrame) -> pd.DataFrame:
    """Site-years restricted to sites observed in every complete year.

    Without this, a year-over-year move in the median mixes behaviour
    change with entry and exit -- the raw pass covers 76/83/80 sites.
    """
    years = set(trend["year"])
    counts = trend.groupby("site")["year"].nunique()
    keep = counts[counts == len(years)].index
    return trend[trend["site"].isin(keep)]


def describe(frame: pd.DataFrame, cols: list[str]) -> dict:
    """Median / IQR / n for each column -- distributions, never t-tests.

    The Enterprise cell is 18 sites before screening and smaller after,
    so nothing here is powered for significance testing and none is done.
    """
    out = {"n_sites": len(frame)}
    for col in cols:
        # Per-column n, because diurnal_spread is only computed on the
        # clean cohort and is null for the rest.
        out[col] = {
            "n": int(frame[col].notna().sum()),
            "median": round(float(frame[col].median()), 4),
            "p25": round(float(frame[col].quantile(0.25)), 4),
            "p75": round(float(frame[col].quantile(0.75)), 4),
            "min": round(float(frame[col].min()), 4),
            "max": round(float(frame[col].max()), 4),
        }
    return out


def make_figure(metrics: pd.DataFrame, hourly: pd.DataFrame, agg: pd.DataFrame) -> None:
    """Four panels: load factor, ramps, diurnal shape, cross-site series."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    ax = axes[0, 0]
    for dc_type, grp in metrics.groupby("dc_type"):
        ax.hist(grp["lf_own_peak"], bins=20, alpha=0.6, label=f"{dc_type} (n={len(grp)})")
    ax.axvline(0.88, color="k", ls="--", lw=1)
    ax.text(0.88, ax.get_ylim()[1] * 0.95, " EPRI colo 0.88", fontsize=8, va="top")
    ax.set_xlabel("load factor vs own realized peak")
    ax.set_ylabel("sites")
    ax.set_title("Flatness: mean / own peak")
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    for dc_type, grp in metrics.groupby("dc_type"):
        ax.scatter(grp["cv"], grp["grad_mean_norm_60m"] * 60.0, s=18, alpha=0.7, label=dc_type)
    # Median of 60 distinct (market, zone) ISO panels on the same measure,
    # deduplicated across alternate specs of the same zone. See
    # docs/research-notes/J-ukpn-flatness.md §3 -- the gap is largely the
    # diurnal cycle a zone has and these sites do not, not extra volatility.
    iso_median = 0.000574 * 60.0
    ax.axhline(iso_median, color="k", ls="--", lw=1)
    below = int((metrics["grad_mean_norm_60m"] * 60.0 < iso_median).sum())
    ax.annotate(
        f"median ISO zone ({len(metrics) - below}/{len(metrics)} sites above)",
        xy=(0.02, iso_median),
        xycoords=("axes fraction", "data"),
        fontsize=8,
        va="bottom",
    )
    # Log axes: a handful of intermittent-cohort sites are an order of
    # magnitude out and would otherwise flatten the bulk into the corner.
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("CV (sigma / mean), log")
    ax.set_ylabel("mean |change| per hour / own mean, log")
    ax.set_title("Dispersion vs ramp rate (hourly basis)")
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    normed = hourly.div(hourly.mean(axis=1), axis=0)
    ax.plot(normed.columns, normed.median(), color="C0", lw=2, label="median site")
    ax.fill_between(
        normed.columns,
        normed.quantile(0.25),
        normed.quantile(0.75),
        alpha=0.25,
        color="C0",
        label="IQR across sites",
    )
    ax.set_xlabel("hour of day (Europe/London)")
    ax.set_ylabel("utilisation / site's own daily mean")
    # This panel averages normalized profiles across sites, which cancels
    # site-specific peak timing and so reads flatter than any one site.
    # The per-site figure is quoted so the two are not confused.
    ax.set_title(
        "Diurnal shape (median per-site peak/trough = "
        f"{metrics['diurnal_spread'].median():.2f})"
    )
    ax.legend(fontsize=8)

    ax = axes[1, 1]
    ax.plot(agg[TS], agg[RATIO], lw=0.4, color="C3")
    ax.set_xlabel("UTC")
    ax.set_ylabel("cross-site mean utilisation ratio")
    ax.set_title("Cross-site mean (equal-weighted, clean cohort)")
    ax.tick_params(axis="x", labelrotation=30, labelsize=8)
    fig.tight_layout()
    fig.savefig(OUTDIR / "ukpn_flatness.png", dpi=150)
    plt.close(fig)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    df = load_profiles()
    print(f"loaded {len(df):,} rows, {df[SITE].nunique()} sites")

    screen = screen_sites(df)
    cohorts = screen["cohort"].value_counts().to_dict()
    print("cohorts:", cohorts)

    clean_sites = screen.loc[screen["cohort"] == "clean", "site"].tolist()
    # Statistics run on clean + intermittent; the mostly-dead and dead
    # cohorts are reported but never pooled into a headline.
    kept = screen.loc[screen["cohort"].isin(["clean", "intermittent"]), "site"].tolist()

    metrics = site_metrics(df[df[SITE].isin(kept)])
    diurnal, hourly = diurnal_spread(df, clean_sites)
    metrics = metrics.merge(diurnal, on="site", how="left")
    trend = year_trend(df, kept)
    panel = balanced(trend)

    # The aggregate is built on sites that are both balanced and clean, so
    # the diversification ratio compares like with like. Balanced removes
    # entry and exit (the corpus has 5 early exits between 2025-07 and
    # 2026-01, visible as a level drop in the raw cross-site series);
    # clean-only removes the other composition channel, where masking a
    # zero run silently drops a site out of the mean mid-series.
    agg_sites = sorted(set(panel["site"]) & set(clean_sites))
    agg = cross_site_series(df, agg_sites)
    agg_complete = agg[agg[TS].dt.year < 2026]
    cross = shape_stats(agg)
    cross_by_year = {
        str(int(y)): shape_stats(g, min_intervals=MIN_INTERVALS_YEAR)
        for y, g in agg_complete.groupby(agg_complete[TS].dt.year)
    }
    # Headline: one row per site, its statistics averaged over the
    # complete years it is present for. Within-year first, then across
    # years -- so a mid-series contract revision never enters a single
    # CV or load factor.
    annual = (
        panel.groupby(["site", "dc_type", "voltage"], as_index=False)
        .mean(numeric_only=True)
        .merge(diurnal, on="site", how="left")
    )

    metrics.to_csv(OUTDIR / "site_metrics.csv", index=False)
    screen.to_csv(OUTDIR / "site_screen.csv", index=False)
    trend.to_csv(OUTDIR / "site_year_trend.csv", index=False)
    annual.to_csv(OUTDIR / "site_annual_headline.csv", index=False)
    hourly.to_csv(OUTDIR / "diurnal_profiles.csv")

    shape_cols = [
        "cv",
        "lf_own_peak",
        "lf_p99",
        "grad_mean_norm",
        "grad_mean_norm_60m",
        "grad_p95_norm",
        "diurnal_spread",
    ]
    results = {
        "corpus": {
            "rows": len(df),
            "sites": int(df[SITE].nunique()),
            "span": [df[TS].min().isoformat(), df[TS].max().isoformat()],
            "zero_rows": int((df[RATIO] == 0.0).sum()),
            "zero_share": round(float((df[RATIO] == 0.0).mean()), 4),
        },
        "cohorts": cohorts,
        "cohort_definition": {
            "clean": f"zero share <= {CLEAN_MAX_ZERO_SHARE}",
            "intermittent": f"{CLEAN_MAX_ZERO_SHARE} < zero share <= {DEGRADED_MAX_ZERO_SHARE}",
            "mostly_dead": f"zero share > {DEGRADED_MAX_ZERO_SHARE}",
            "dead": "zero share == 1.0 (dropped)",
        },
        "mic_step_screen": mic_step_screen(df, screen),
        "headline_annual": describe(annual, shape_cols),
        "headline_by_dc_type": {
            str(k): describe(g, shape_cols) for k, g in annual.groupby("dc_type")
        },
        "headline_by_voltage": {
            str(k): describe(g, shape_cols) for k, g in annual.groupby("voltage")
        },
        "headline_by_cohort": {
            str(k): describe(g, shape_cols)
            for k, g in annual.merge(screen[["site", "cohort"]], on="site").groupby("cohort")
        },
        "pooled_whole_span": describe(metrics, shape_cols),
        "pooled_by_dc_type": {
            str(k): describe(g, shape_cols) for k, g in metrics.groupby("dc_type")
        },
        "cross_site_n_sites": len(agg_sites),
        "cross_site_mean_pooled": cross,
        "cross_site_mean_by_year": cross_by_year,
        # Diversification: the aggregate's flatness against the median
        # individual site's, both measured within-year so neither side
        # carries cross-year drift the other does not. Below 1 means
        # site-level movement is largely idiosyncratic and cancels.
        "diversification_ratio_by_year": {
            year: {
                "cv_ratio": round(
                    stats["cv"] / float(panel.loc[panel["year"] == int(year), "cv"].median()), 4
                ),
                "grad_mean_norm_ratio": round(
                    stats["grad_mean_norm"]
                    / float(panel.loc[panel["year"] == int(year), "grad_mean_norm"].median()),
                    4,
                ),
            }
            for year, stats in cross_by_year.items()
        },
        "trend_by_year_balanced": {
            str(int(y)): {
                "n_sites": len(g),
                "median_cv": round(float(g["cv"].median()), 4),
                "median_lf_own_peak": round(float(g["lf_own_peak"].median()), 4),
                "median_grad_mean_norm": round(float(g["grad_mean_norm"].median()), 6),
            }
            for y, g in panel.groupby("year")
        },
        "trend_by_year_unbalanced": {
            str(int(y)): {
                "n_sites": len(g),
                "median_cv": round(float(g["cv"].median()), 4),
                "median_lf_own_peak": round(float(g["lf_own_peak"].median()), 4),
                "median_grad_mean_norm": round(float(g["grad_mean_norm"].median()), 6),
            }
            for y, g in trend.groupby("year")
        },
    }

    (OUTDIR / "results.json").write_text(json.dumps(results, indent=2))
    make_figure(annual, hourly, agg)

    print(json.dumps(results["headline_annual"], indent=2))
    print(f"\n-> {OUTDIR}")


if __name__ == "__main__":
    main()
