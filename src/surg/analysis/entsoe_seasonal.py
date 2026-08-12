"""Seasonal decomposition of daily load shape -- the H_solar test.

H_solar (design section 4, EU-5) says behind-the-meter PV deepens the *metered*
midday trough, which can masquerade as a data-centre-driven change in load
shape. The Irish/Dutch result already hints at it: NL (dense rooftop PV) lost
-0.110 at hour 11 while Ireland (little PV) lost -0.082 at hour 13.

WHY SEASONAL, AND NOT A CROSS-SECTION ON SOLAR SHARE. Solar share and calendar
year are near-collinear -- PV grew monotonically almost everywhere -- so a
regression of shape on solar share cannot separate "solar" from "whatever else
drifted over the same decade". Irradiance, by contrast, varies enormously
WITHIN a year while data-centre share does not move between June and December.
That within-year contrast is the identification:

  * a solar-driven midday trough must be concentrated in high-irradiance months
    and near-absent in December;
  * a data-centre-driven or secular flattening has NO seasonal signature.

So the statistic that carries the test is the SUMMER-MINUS-WINTER midday gap,
and its trend over time -- not the level of the trough in any one season.

THE CONFOUND, STATED UP FRONT: space cooling is also seasonal and also midday,
and it pushes summer midday load UP. In a hot zone (ES) that biases the
seasonal signature toward zero, making the test conservative there. In the
maritime zones that anchor this project (IE, NL, DK) domestic cooling is
negligible, so summer midday is close to a clean solar read. Electric heating
is seasonal too but loads the winter morning and evening peaks, not midday.
Nothing here can separate solar from a hypothetical unmodelled summer-midday
process; the claim is only that the signature is where solar predicts it.

MEASUREMENT RULES, inherited from scripts/entsoe_ireland.py because the raw
corpus violates the naive assumptions:

  1. COMPLETE DAYS ONLY. A day holding 4 of 24 hours contributes a garbage
     mean, and normalizing by that mean corrupts every hour of it. IE_CTA is
     missing 1.85% of its native slots in 661 runs.
  2. EACH DAY IS NORMALIZED BY ITS OWN MEAN before averaging across days, so a
     year's profile is not dominated by its highest-demand days.
  3. n_days is returned, never assumed. A season-year with few complete days
     produces a plausible-looking profile from nothing.
"""
from __future__ import annotations

import pandas as pd

# Seasons chosen for irradiance contrast, not meteorological convention:
# May-Aug brackets the solstice, Nov-Feb the winter minimum. March/April and
# September/October are deliberately excluded -- they are the shoulder months
# where the two regimes overlap and would blur the contrast the test rests on.
SUMMER = (5, 6, 7, 8)
WINTER = (11, 12, 1, 2)

# Hour blocks, local prevailing time. MIDDAY brackets solar noon across the
# longitudes in this panel; NIGHT is the floor, and is the block the Irish
# result found moving most (hour 3, in both countries).
MIDDAY = (10, 11, 12, 13, 14, 15)
NIGHT = (0, 1, 2, 3, 4)
EVENING = (18, 19, 20, 21)

HOURS_PER_DAY = 24


def complete_days(panel: pd.DataFrame, *, value_name: str = "load_mw") -> pd.DataFrame:
    """Rows belonging to local days that carry all 24 hourly slots.

    Returns the panel with a `date` column added and incomplete days removed.
    """
    work = panel.dropna(subset=[value_name]).copy()
    if work.empty:
        return work.assign(date=pd.Series(dtype="object"))
    work["date"] = work["timestamp_local"].dt.date
    sizes = work.groupby("date")[value_name].transform("size")
    return work[sizes == HOURS_PER_DAY].copy()


def seasonal_profile(
    panel: pd.DataFrame,
    *,
    year: int,
    months: tuple[int, ...],
    value_name: str = "load_mw",
) -> pd.Series:
    """Mean normalized daily profile for one year and set of months.

    Each complete day is divided by its own mean, then the days are averaged.
    Index is local hour 0-23; a flat day would return all ones.

    Winter spans a year boundary (Nov-Feb), so `year` selects days by the year
    of the LOCAL DATE -- January 2025 belongs to 2025, not to the 2024 winter.
    This keeps every season-year an intersection of a calendar year and a month
    set, which is what the dose join expects.
    """
    work = complete_days(panel, value_name=value_name)
    if work.empty:
        return pd.Series(dtype=float)

    local = work["timestamp_local"]
    work = work[(local.dt.year == year) & (local.dt.month.isin(months))]
    if work.empty:
        return pd.Series(dtype=float)

    day_mean = work.groupby("date")[value_name].transform("mean")
    normalized = work[value_name] / day_mean
    return normalized.groupby(work["timestamp_local"].dt.hour).mean()


def midday_statistics(
    panel: pd.DataFrame,
    *,
    year: int,
    months: tuple[int, ...],
    value_name: str = "load_mw",
) -> pd.Series:
    """Hour-block summaries of one season-year's normalized profile.

    `midday_ratio` below 1 means the midday block sits below that day's own
    mean -- a depressed midday. `midday_depth` is 1 - midday_ratio, so it rises
    as the trough deepens, which is the direction H_solar predicts.
    """
    profile = seasonal_profile(panel, year=year, months=months, value_name=value_name)
    work = complete_days(panel, value_name=value_name)
    if not work.empty:
        local = work["timestamp_local"]
        work = work[(local.dt.year == year) & (local.dt.month.isin(months))]
    n_days = 0 if work.empty else work["date"].nunique()

    if profile.empty:
        return pd.Series(
            {
                "n_days": 0,
                "midday_ratio": float("nan"),
                "midday_depth": float("nan"),
                "night_ratio": float("nan"),
                "evening_ratio": float("nan"),
                "peak_hour": float("nan"),
                "trough_hour": float("nan"),
            }
        )

    def block(hours: tuple[int, ...]) -> float:
        present = [h for h in hours if h in profile.index]
        return float(profile.loc[present].mean()) if present else float("nan")

    midday = block(MIDDAY)
    return pd.Series(
        {
            "n_days": int(n_days),
            "midday_ratio": midday,
            "midday_depth": 1.0 - midday,
            "night_ratio": block(NIGHT),
            "evening_ratio": block(EVENING),
            "peak_hour": float(profile.idxmax()),
            "trough_hour": float(profile.idxmin()),
        }
    )


def midday_deviation_mw(
    panel: pd.DataFrame,
    *,
    year: int,
    months: tuple[int, ...],
    value_name: str = "load_mw",
) -> float:
    """Mean ABSOLUTE deviation (MW) of the midday block from its own day's mean.

    This is the statistic that discriminates between the two explanations, and
    it exists because every normalized statistic in this project has at some
    point been undone by its denominator (ISONE's shrinking load, Ireland's
    growing load, the Dutch series' 2023 redefinition).

      * Adding FLAT load -- data centres, an industrial recovery -- leaves this
        quantity unchanged. It only compresses the ratio-based statistics.
      * Adding MIDDAY-CONCENTRATED load, or removing it, moves this quantity
        directly.

    So a change here cannot be manufactured by load growth of any size, as long
    as the added load is flat. Positive means midday sits above the daily mean
    (the historic shape); it falls toward zero and then negative as PV carves
    the midday trough.
    """
    work = complete_days(panel, value_name=value_name)
    if work.empty:
        return float("nan")

    local = work["timestamp_local"]
    work = work[(local.dt.year == year) & (local.dt.month.isin(months))]
    if work.empty:
        return float("nan")

    day_mean = work.groupby("date")[value_name].transform("mean")
    deviation = work[value_name] - day_mean
    midday = deviation[work["timestamp_local"].dt.hour.isin(MIDDAY)]
    return float(midday.mean()) if len(midday) else float("nan")


def implausible_days(
    panel: pd.DataFrame, *, value_name: str = "load_mw", floor_fraction: float = 0.25
) -> pd.DataFrame:
    """Complete days that are absurd against the panel's own median day.

    `complete_days` counts slots and validates no magnitude, so a day of 24
    corrupt values passes the completeness gate and produces a plausible-looking
    profile.

    TWO tests, because corruption comes in two shapes and a mean-only test is
    blind to the one that actually occurs:

      * the day's MEAN collapses -- a wholly bad day;
      * the day's MINIMUM collapses while the mean survives -- a few corrupt
        slots inside an otherwise ordinary day.

    The Dutch 2026 tail is the second kind, and it is why the second test
    exists: eight days carry minima of 187-1,822 MW against a median day
    minimum of 10,320 MW, yet their means (6,150-7,789 MW) clear any sane
    mean-based floor. A mean-only guard flags none of them.

    Returned rather than raised, because which years to exclude is the caller's
    decision and a silent drop would be the same class of bug -- but the caller
    is expected to print this, not ignore it.
    """
    work = complete_days(panel, value_name=value_name)
    if work.empty:
        return pd.DataFrame(
            columns=["date", "day_mean_mw", "day_min_mw", "reason"]
        )

    per_day = work.groupby("date")[value_name].agg(["mean", "min"])
    mean_floor = per_day["mean"].median() * floor_fraction
    min_floor = per_day["min"].median() * floor_fraction

    low_mean = per_day["mean"] < mean_floor
    low_min = per_day["min"] < min_floor
    bad = per_day[low_mean | low_min].copy()
    bad["reason"] = [
        "mean+min" if m and n else "mean" if m else "min"
        for m, n in zip(low_mean[low_mean | low_min], low_min[low_mean | low_min], strict=True)
    ]
    return bad.reset_index().rename(
        columns={"mean": "day_mean_mw", "min": "day_min_mw"}
    )


def solar_signature(
    panel: pd.DataFrame, *, year: int, value_name: str = "load_mw"
) -> pd.Series:
    """Summer-minus-winter contrast for one zone-year -- the H_solar statistic.

    `signature` is summer midday depth minus winter midday depth. Positive means
    the midday trough is deeper in summer than in winter, which is what PV does
    and what a data-centre or secular explanation does not do.

    Returning the two seasons' pieces alongside the contrast is deliberate: a
    signature can move because summer deepened or because winter filled in, and
    those are different stories.
    """
    summer = midday_statistics(panel, year=year, months=SUMMER, value_name=value_name)
    winter = midday_statistics(panel, year=year, months=WINTER, value_name=value_name)
    return pd.Series(
        {
            "year": year,
            "n_days_summer": summer["n_days"],
            "n_days_winter": winter["n_days"],
            "summer_midday_depth": summer["midday_depth"],
            "winter_midday_depth": winter["midday_depth"],
            "signature": summer["midday_depth"] - winter["midday_depth"],
            "summer_night_ratio": summer["night_ratio"],
            "winter_night_ratio": winter["night_ratio"],
            # Absolute MW, reported beside every ratio for the reason given in
            # midday_deviation_mw: a ratio can move because its denominator did.
            "summer_midday_dev_mw": midday_deviation_mw(
                panel, year=year, months=SUMMER, value_name=value_name
            ),
            "winter_midday_dev_mw": midday_deviation_mw(
                panel, year=year, months=WINTER, value_name=value_name
            ),
        }
    )


def signature_by_year(
    panel: pd.DataFrame,
    *,
    years: list[int] | tuple[int, ...],
    value_name: str = "load_mw",
    min_days: int = 30,
) -> pd.DataFrame:
    """`solar_signature` for each year, dropping season-years that are too thin.

    A season spans roughly 120 days. `min_days` guards against a year whose
    summer or winter is a stub -- the edges of the pull window, or an outage
    like the 19-day Irish gap in February 2026 -- producing a confident-looking
    number from a handful of days.
    """
    rows = []
    for year in years:
        row = solar_signature(panel, year=year, value_name=value_name)
        if row["n_days_summer"] < min_days or row["n_days_winter"] < min_days:
            continue
        rows.append(row)
    if not rows:
        return pd.DataFrame(
            columns=[
                "year", "n_days_summer", "n_days_winter", "summer_midday_depth",
                "winter_midday_depth", "signature", "summer_night_ratio",
                "winter_night_ratio", "summer_midday_dev_mw", "winter_midday_dev_mw",
            ]
        ).set_index("year")
    return pd.DataFrame(rows).astype({"year": int}).set_index("year")
