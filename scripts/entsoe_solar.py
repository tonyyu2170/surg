# scripts/entsoe_solar.py
"""H_solar: is the midday flattening a solar metering artifact?

EU-5 called this the one open question the North American panel could not
settle, and the Irish/Dutch result made it live: the K-note attributed a
flattening of Irish load shape to a period in which data centres grew from 4.4%
to 23.7% of consumption, but the Dutch control -- 28 GW of mostly rooftop PV --
flattened identically. If behind-the-meter PV is carving the *metered* midday,
part of what the K-note measured is a metering artifact rather than a change in
anyone's load behaviour.

THE IDENTIFICATION (see surg.analysis.entsoe_seasonal for the full argument).
Solar share and calendar year are near-collinear, so a cross-section on solar
share cannot separate solar from any other decade-long drift. Irradiance,
though, varies within the year while data-centre share does not move between
June and December. So the test is the SUMMER-MINUS-WINTER midday contrast and
its trend -- a signature data centres cannot produce.

TWO MEASUREMENT DECISIONS THAT CHANGE THE ANSWER:

  1. The DOSE is A68 installed capacity, never A75 actual generation. Measured
     2026-08-12: the Dutch A75 solar feed peaks at 204 MW on a June day against
     27,980 MW installed, because Dutch PV is overwhelmingly distributed and
     invisible to the TSO, while German A75 peaks at 24,393 MW against 77,016
     MW installed and plainly does include it. A75 is not comparable across
     countries and would score the Netherlands as a near-zero-solar market.
  2. Every ratio is reported beside an ABSOLUTE MW deviation. This project has
     now been bitten three times by a normalized statistic moving because its
     denominator did (ISONE's shrinking load, Ireland's growing load, and the
     Dutch redefinition this script measures). A flat load addition cannot move
     `midday_dev_mw`; only a midday-concentrated one can.

THE DUTCH BREAK, measured here rather than assumed. The NL series steps at
2023-04: the April/March mean-load ratio is 1.049 against a median of 0.925 in
every other year, and the midday deviation jumps +1,395 MW against a median of
-123 MW. Because that step is MIDDAY-CONCENTRATED, a flat industrial recovery
from the 2022 gas crisis cannot explain it -- a flat addition leaves a
deviation-from-own-mean untouched. The shape is consistent with distributed
generation being grossed back into reported load; the cause is NOT confirmed
with the TSO and must not be written as if it were. Consequence: NL endpoints
spanning 2015->2025 straddle a definitional break, so this script reports NL
pre-break and post-break separately and never across.

Usage: .venv/bin/python scripts/entsoe_solar.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

from surg.analysis.entsoe_seasonal import (
    SUMMER,
    WINTER,
    complete_days,
    implausible_days,
    seasonal_profile,
    signature_by_year,
)
from surg.preprocessing.entsoe_panel import zone_panel
from surg.preprocessing.entsoe_zones import FIRST_LOAD_YEAR

OUT = Path("outputs/entsoe")
RAW = Path("data/raw/entsoe")

# 2026 is excluded everywhere. The Dutch feed's 2026 tail carries days whose
# mean is a fraction of the system floor (a July minimum of 1,272 MW and an
# August one of 187 MW on a ~12,000 MW system); those days hold 24 slots each,
# so they pass the completeness gate and would otherwise produce confident
# numbers from corrupt values. The exclusion is reported, not silent.
YEARS = list(range(2015, 2026))

# The Dutch definitional break, measured in this script's own diagnostics.
NL_BREAK_YEAR = 2023

ZONES = {
    "IE_CTA": "Ireland",
    "NL": "Netherlands",
    "DE_LU": "Germany-Lux",
    "ES": "Spain",
    "FR": "France",
    "FI": "Finland",
    "DK1": "Denmark W",
    "DK2": "Denmark E",
    "SE1": "Sweden N",
    "SE2": "Sweden N-C",
    "SE3": "Sweden S-C",
    "SE4": "Sweden S",
}


def load_capacity(zone_key: str) -> pd.Series:
    """Installed solar capacity (MW) by year, from the raw A68 parquet.

    Read directly rather than through `zone_panel`: A68 carries resolution P1Y,
    which the point expander is not built for and would raise on.
    """
    directory = RAW / "capacity" / zone_key
    if not directory.exists():
        return pd.Series(dtype=float)
    rows = {}
    for path in sorted(directory.glob("*.parquet")):
        frame = pd.read_parquet(path)
        if frame.empty:
            continue
        # doc_start is LOCAL MIDNIGHT OF 1 JANUARY expressed in UTC, so it lands
        # on 31 December of the PREVIOUS year (FI 2019 -> 2018-12-31T22:00Z).
        # Taking .year off it shifts every dose back a year and silently joins
        # each zone-year to the following year's capacity. The filename is the
        # requested year by construction of the fetcher; doc_end is the
        # independent witness, and a disagreement is a fail-loud error rather
        # than a quiet off-by-one.
        year = int(path.stem)
        from_doc = (pd.Timestamp(frame["doc_end"].iloc[0]) - pd.Timedelta(days=1)).year
        if year != from_doc:
            raise ValueError(
                f"capacity year mismatch for {path}: filename says {year}, "
                f"doc_end {frame['doc_end'].iloc[0]} implies {from_doc}"
            )
        rows[year] = float(frame["value"].iloc[0])
    return pd.Series(rows, name="solar_mw").sort_index()


def mean_load_by_year(hourly: pd.DataFrame) -> pd.Series:
    work = hourly.dropna(subset=["load_mw"])
    return work.groupby(work["timestamp_local"].dt.year)["load_mw"].mean()


def monthly_mean_march(hourly: pd.DataFrame, year: int) -> float:
    """March mean load, the base the implied step size is expressed against."""
    work = complete_days(hourly)
    work = work[work["timestamp_local"].dt.to_period("M") == pd.Period(f"{year}-03")]
    return float(work["load_mw"].mean()) if not work.empty else float("nan")


def april_march_step(hourly: pd.DataFrame) -> pd.DataFrame:
    """April-vs-March transition per year -- the break detector.

    A one-month difference-in-differences on the seasonal cycle. It is immune
    both to a depressed base year (the 2022 gas crisis) and to secular trend,
    because it compares a transition against the same transition in every other
    year. A step that appears here and nowhere else is a level shift, and if it
    also appears in the MIDDAY deviation it is a midday-concentrated one.
    """
    # COMPLETE DAYS ONLY, matching measurement rule 1 in entsoe_seasonal. A
    # partial day at the edge of a pull window drags the monthly mean and the
    # per-day deviation in opposite directions, and mixing the two conventions
    # inside one table is how a +1,548 MW step ends up quoted beside a ratio
    # computed over a different sample.
    work = complete_days(hourly).copy()
    work["ym"] = work["timestamp_local"].dt.to_period("M")
    work["day_mean"] = work.groupby("date")["load_mw"].transform("mean")
    work["dev"] = work["load_mw"] - work["day_mean"]
    midday = work[work["timestamp_local"].dt.hour.isin(range(10, 16))]

    monthly = pd.DataFrame(
        {
            "mean_mw": work.groupby("ym")["load_mw"].mean(),
            "midday_dev_mw": midday.groupby("ym")["dev"].mean(),
        }
    )
    rows = []
    for year in YEARS:
        try:
            march, april = monthly.loc[f"{year}-03"], monthly.loc[f"{year}-04"]
        except KeyError:
            continue
        rows.append(
            {
                "year": year,
                "apr_over_mar": april["mean_mw"] / march["mean_mw"],
                "midday_dev_delta_mw": april["midday_dev_mw"] - march["midday_dev_mw"],
            }
        )
    return pd.DataFrame(rows).set_index("year")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {"years": YEARS, "excluded": "2026 (see module docstring)"}

    panels, signatures, coverage = {}, {}, []
    for key, label in ZONES.items():
        try:
            _, hourly = zone_panel("load", key, value_name="load_mw")
        except FileNotFoundError:
            print(f"  no load on disk for {key} -- skipped")
            continue
        panels[key] = hourly

        bad = implausible_days(hourly)
        in_window = hourly[hourly["timestamp_local"].dt.year.isin(YEARS)]
        signatures[key] = signature_by_year(in_window, years=YEARS)
        first_year = int(hourly["timestamp_local"].dt.year.min())
        coverage.append(
            {
                "zone": key,
                "label": label,
                "first_year": first_year,
                "declared_first_load_year": FIRST_LOAD_YEAR.get(key, YEARS[0]),
                "n_hours": len(hourly),
                "n_implausible_days_all_time": len(bad),
                "implausible_dates": ";".join(str(d) for d in bad["date"][:5]),
            }
        )

    cov = pd.DataFrame(coverage).set_index("zone")
    print("=== coverage (measured, not asserted) ===")
    print(cov.to_string())
    results["coverage"] = cov.to_dict(orient="index")

    # --- the Dutch break, and whether anyone else shares it -----------------
    print("\n=== April-vs-March step detector (break month = the outlier year) ===")
    steps = {}
    for key, panel in panels.items():
        table = april_march_step(panel)
        if table.empty or NL_BREAK_YEAR not in table.index:
            continue
        others = table.drop(index=NL_BREAK_YEAR)
        median_ratio = others["apr_over_mar"].median()
        excess = table.loc[NL_BREAK_YEAR, "apr_over_mar"] / median_ratio
        steps[key] = {
            "median_apr_over_mar_excl_break_year": float(median_ratio),
            "break_year_apr_over_mar": float(table.loc[NL_BREAK_YEAR, "apr_over_mar"]),
            "excess_ratio": float(excess),
            "median_midday_dev_delta_mw": float(others["midday_dev_delta_mw"].median()),
            "break_year_midday_dev_delta_mw": float(
                table.loc[NL_BREAK_YEAR, "midday_dev_delta_mw"]
            ),
            "implied_step_mw": float(
                monthly_mean_march(panel, NL_BREAK_YEAR) * (excess - 1)
            ),
        }
        table.to_csv(OUT / f"solar_step_{key}.csv")
        print(
            f"  {key:<8} median Apr/Mar={median_ratio:.4f}  "
            f"{NL_BREAK_YEAR}={steps[key]['break_year_apr_over_mar']:.4f}  "
            f"(x{excess:.4f})   midday-dev delta: median="
            f"{steps[key]['median_midday_dev_delta_mw']:+,.0f} MW  "
            f"{NL_BREAK_YEAR}={steps[key]['break_year_midday_dev_delta_mw']:+,.0f} MW"
        )
    results["april_march_step"] = steps

    # --- the seasonal signature, per zone ----------------------------------
    print("\n=== seasonal signature: summer minus winter midday depth ===")
    print("    (positive = midday sits lower in summer than winter, as PV predicts)")
    for key, table in signatures.items():
        if table.empty:
            continue
        table.to_csv(OUT / f"solar_signature_{key}.csv")
        first, last = table.index.min(), table.index.max()
        note = "  [SPANS THE 2023-04 BREAK -- see pre/post split below]" if key == "NL" else ""
        print(
            f"  {ZONES[key]:<12} {first}->{last}  signature "
            f"{table.loc[first, 'signature']:+.4f} -> {table.loc[last, 'signature']:+.4f}   "
            f"summer midday dev {table.loc[first, 'summer_midday_dev_mw']:+,.0f} -> "
            f"{table.loc[last, 'summer_midday_dev_mw']:+,.0f} MW{note}"
        )

    # --- NL pre-break vs post-break ----------------------------------------
    if "NL" in signatures and not signatures["NL"].empty:
        nl = signatures["NL"]
        pre, post = nl[nl.index < NL_BREAK_YEAR], nl[nl.index >= NL_BREAK_YEAR]
        if not pre.empty and not post.empty:
            results["nl_break"] = {
                "break_year": NL_BREAK_YEAR,
                "pre_window": [int(pre.index.min()), int(pre.index.max())],
                "pre_summer_midday_dev_mw": [
                    float(pre["summer_midday_dev_mw"].iloc[0]),
                    float(pre["summer_midday_dev_mw"].iloc[-1]),
                ],
                "post_window": [int(post.index.min()), int(post.index.max())],
                "post_summer_midday_dev_mw": [
                    float(post["summer_midday_dev_mw"].iloc[0]),
                    float(post["summer_midday_dev_mw"].iloc[-1]),
                ],
            }
            print(
                f"\n=== NL split at the break ===\n"
                f"  pre-break  {pre.index.min()}->{pre.index.max()}: summer midday dev "
                f"{pre['summer_midday_dev_mw'].iloc[0]:+,.0f} -> "
                f"{pre['summer_midday_dev_mw'].iloc[-1]:+,.0f} MW\n"
                f"  post-break {post.index.min()}->{post.index.max()}: summer midday dev "
                f"{post['summer_midday_dev_mw'].iloc[0]:+,.0f} -> "
                f"{post['summer_midday_dev_mw'].iloc[-1]:+,.0f} MW"
            )

    # --- dose cross-section -------------------------------------------------
    # n is small (7 zones carry A68), so this is a table and a rank correlation,
    # never a fitted regression with standard errors.
    rows = []
    for key, panel in panels.items():
        capacity = load_capacity(key)
        if capacity.empty:
            continue
        mean_load = mean_load_by_year(panel)
        table = signatures[key]
        for year in table.index:
            if year not in capacity.index or year not in mean_load.index:
                continue
            if key == "NL" and year >= NL_BREAK_YEAR:
                continue  # post-break NL is a different series
            load_mw = mean_load.loc[year]
            rows.append(
                {
                    "zone": key,
                    "label": ZONES[key],
                    "year": int(year),
                    "solar_mw": float(capacity.loc[year]),
                    "mean_load_mw": float(load_mw),
                    "dose": float(capacity.loc[year] / load_mw),
                    "signature": float(table.loc[year, "signature"]),
                    "summer_midday_dev_mw": float(table.loc[year, "summer_midday_dev_mw"]),
                    "summer_midday_dev_norm": float(
                        table.loc[year, "summer_midday_dev_mw"] / load_mw
                    ),
                }
            )
    cross = pd.DataFrame(rows)
    if not cross.empty:
        cross.to_csv(OUT / "solar_cross_section.csv", index=False)
        spearman = cross[["dose", "signature", "summer_midday_dev_norm"]].corr(method="spearman")
        print("\n=== dose cross-section (A68 installed solar / mean load) ===")
        print(f"  {len(cross)} zone-years, {cross['zone'].nunique()} zones "
              f"(NL truncated at the break; SE1-4 and IE carry no A68)")
        print("  Spearman rank correlations:")
        print(f"    dose vs seasonal signature        rho = "
              f"{spearman.loc['dose', 'signature']:+.3f}")
        print(f"    dose vs normalized summer midday  rho = "
              f"{spearman.loc['dose', 'summer_midday_dev_norm']:+.3f}")
        results["cross_section"] = {
            "n_zone_years": len(cross),
            "n_zones": int(cross["zone"].nunique()),
            "spearman_dose_signature": float(spearman.loc["dose", "signature"]),
            "spearman_dose_summer_dev_norm": float(
                spearman.loc["dose", "summer_midday_dev_norm"]
            ),
        }

        endpoints = []
        for key, block in cross.groupby("zone"):
            block = block.sort_values("year")
            endpoints.append({
                "zone": key, "label": ZONES[key],
                "first_year": int(block["year"].iloc[0]), "last_year": int(block["year"].iloc[-1]),
                "dose_first": block["dose"].iloc[0], "dose_last": block["dose"].iloc[-1],
                "signature_first": block["signature"].iloc[0],
                "signature_last": block["signature"].iloc[-1],
                "d_dose": block["dose"].iloc[-1] - block["dose"].iloc[0],
                "d_signature": block["signature"].iloc[-1] - block["signature"].iloc[0],
            })
        ends = pd.DataFrame(endpoints).set_index("zone")
        print("\n  per-zone endpoints (dose = installed solar MW per MW of mean load):")
        print(ends.round(4).to_string())
        results["cross_section_endpoints"] = ends.to_dict(orient="index")
        rho = ends["d_dose"].corr(ends["d_signature"], method="spearman")
        print(f"\n  Spearman, change-in-dose vs change-in-signature, n={len(ends)}: rho={rho:+.3f}")
        results["spearman_change_in_dose_vs_change_in_signature"] = float(rho)

    # --- figures ------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for key, table in signatures.items():
        if table.empty:
            continue
        style = {"linewidth": 2.4} if key in ("IE_CTA", "NL") else {"linewidth": 1.0, "alpha": 0.75}
        axes[0].plot(table.index, table["signature"], marker="o", ms=3, label=ZONES[key], **style)
        axes[1].plot(table.index, table["summer_midday_dev_mw"], marker="o", ms=3,
                     label=ZONES[key], **style)
    axes[0].axhline(0, color="grey", lw=0.6, ls=":")
    axes[0].set_title("Seasonal signature (summer − winter midday depth)")
    axes[0].set_ylabel("signature")
    axes[1].axhline(0, color="grey", lw=0.6, ls=":")
    axes[1].axvline(NL_BREAK_YEAR - 0.5, color="crimson", lw=0.8, ls="--")
    axes[1].set_title("Summer midday deviation (MW) — absolute, dilution-proof")
    axes[1].set_ylabel("MW above/below the day's own mean")
    for ax in axes:
        ax.set_xlabel("year")
        ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "fig_solar_signature.png", dpi=150)
    plt.close(fig)

    # Diurnal profiles, summer vs winter, first and last clean year.
    keys = [k for k in ("IE_CTA", "NL", "DE_LU", "ES") if k in panels]
    fig, axes = plt.subplots(1, len(keys), figsize=(4.2 * len(keys), 4.2), sharey=True)
    for ax, key in zip(axes, keys, strict=True):
        last = NL_BREAK_YEAR - 1 if key == "NL" else 2025
        first = 2018 if key == "DE_LU" else 2015
        for year, colour in ((first, "tab:blue"), (last, "tab:red")):
            for months, style in ((SUMMER, "-"), (WINTER, ":")):
                profile = seasonal_profile(panels[key], year=year, months=months)
                if profile.empty:
                    continue
                ax.plot(profile.index, profile.values, style, color=colour,
                        label=f"{year} {'summer' if months == SUMMER else 'winter'}")
        ax.axhline(1.0, color="grey", lw=0.6, ls=":")
        ax.set_title(ZONES[key])
        ax.set_xlabel("hour, local")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("load ÷ that day's mean")
    fig.tight_layout()
    fig.savefig(OUT / "fig_solar_diurnal.png", dpi=150)
    plt.close(fig)

    (OUT / "solar_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nwrote {OUT}/solar_results.json, fig_solar_signature.png, fig_solar_diurnal.png")


if __name__ == "__main__":
    main()
