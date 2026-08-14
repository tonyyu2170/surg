# scripts/pecanstreet_headroom.py
"""RQ2: do the bundle homes have idle panel capacity, and does it survive summer peak?

Usage:
  .venv/bin/python scripts/pecanstreet_headroom.py --sample 661 --month 2018-07  # eyeball first
  .venv/bin/python scripts/pecanstreet_headroom.py                               # full, 3 cities

Design doc: docs/specs/2026-08-14-pecanstreet-xfra-headroom-design.md.
Reads the 1-min bundles (primary; a breaker responds to sustained draw and
15-min averaging shaves peaks — the 15-min files serve only as a crosscheck),
reconstructs whole-home use, and reports headroom against 100/150/200 A
service scenarios, with and without the NEC 80% continuous derating. Homes flagged in any
intervention program are excluded from a robustness re-run. CA timestamps are
Central-stamped San Diego data; the diurnal check below prints the evidence
for the chosen interpretation before any local-hour claim is used.
"""
from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pecanstreet_lib as pslib

MIN_COVERAGE = 0.90


def clean_use(df: pd.DataFrame) -> pd.Series:
    """Whole-home use with physically impossible meter readings masked out."""
    return pslib.mask_implausible(pslib.reconstruct_use(df))


def home_records(city: str, df: pd.DataFrame, meta: pd.DataFrame) -> list[dict]:
    cov = pslib.coverage(df, freq_s=60)
    flagged = pslib.treated_dataids(meta)
    # Descriptive context only (spec): never reweights any statistic. Both
    # columns are float64-with-NaN in metadata.csv (verified 2026-08-14).
    context = {}
    for _, mrow in meta.iterrows():
        yr, sqft = mrow["house_construction_year"], mrow["total_square_footage"]
        context[int(mrow["dataid"])] = {
            "construction_year": None if pd.isna(yr) else int(yr),
            "square_footage": None if pd.isna(sqft) else float(sqft),
        }
    battery_homes = set(df.loc[df["battery1"].notna(), "dataid"].unique().tolist())
    records = []
    for dataid, g in df.groupby("dataid"):
        use = clean_use(g)
        rec = {"dataid": int(dataid), "city": city,
               "coverage": float(cov.loc[dataid]),
               "valid_share": float(use.notna().mean()),
               "negative_share": pslib.negative_share(use),
               "intervention": int(dataid) in flagged,
               "battery": int(dataid) in battery_homes,
               "meta": context.get(int(dataid)),
               # Full bundle span: NY = 6 months, CA = 5 pooled years — note M
               # must not call these "annual" outside Austin.
               "year": pslib.headroom_metrics(use)}
        mask = pslib.peak_window_mask(g["ts"])
        if mask.any():
            rec["summer_exposure"] = pslib.summer_exposure(g["ts"])
            rec["off_window"] = pslib.headroom_metrics(use[~mask])
            if rec["summer_exposure"] >= MIN_COVERAGE:
                rec["peak_window"] = pslib.headroom_metrics(use[mask])
        records.append(rec)
    return records


def diurnal_check(city: str, df: pd.DataFrame) -> dict:
    """Mean use by local hour; the evening residential peak must land ~16-21."""
    use = clean_use(df)
    hours = pd.DatetimeIndex(df["ts"]).hour
    prof = pd.Series(use.values).groupby(np.asarray(hours)).mean()
    return {"peak_hour_local": int(prof.idxmax()),
            "profile_kw": {int(h): float(v) for h, v in prof.items()}}


def crosscheck_15min(city: str, records: list[dict]) -> dict:
    df15 = pslib.read_power(city, "15minute")
    out = {}
    by_id = {r["dataid"]: r for r in records}
    for dataid, g in df15.groupby("dataid"):
        if int(dataid) not in by_id:
            continue
        max15 = float(clean_use(g).max())
        max1 = by_id[int(dataid)]["year"]["max_kw"]
        out[int(dataid)] = {"max_15min_kw": max15, "max_1min_kw": max1,
                            "peak_shaving_ratio": max15 / max1 if max1 else float("nan")}
    return out


def yearly_breakdown(df: pd.DataFrame) -> dict:
    """Per calendar year: per-home max and the 12.5kW hostable fraction.

    The spec uses CA (2014-2018) as a year-to-year stability check; for
    Austin/NY this is a harmless single-entry table.
    """
    df = df.copy()
    df["use"] = clean_use(df)
    df["yr"] = pd.DatetimeIndex(df["ts"]).year
    lim = pslib.SERVICE_KW["200A"] * pslib.NEC_DERATE
    out = {}
    for yr, g in df.groupby("yr"):
        # dropna: a home with no valid readings has a NaN max, and NaN >= 12.5
        # is False — without this it would count as "cannot host" rather than
        # being excluded, understating the fraction (same hazard AM-1/AM-2
        # removed from hostable_fractions).
        mx = g.groupby("dataid")["use"].max().dropna()
        out[int(yr)] = {"n_homes": int(mx.size),
                        "median_max_kw": float(mx.median()),
                        "hostable_12.5kw_frac": float(((lim - mx) >= 12.5).mean())}
    return out


def seasonal_min_headroom(df: pd.DataFrame) -> pd.Series:
    """Median across homes of each day's minimum 200A-derated headroom."""
    df = df.copy()
    df["use"] = clean_use(df)
    lim = pslib.SERVICE_KW["200A"] * pslib.NEC_DERATE
    df["date"] = pd.DatetimeIndex(df["ts"]).date
    daily_max = df.groupby(["dataid", "date"])["use"].max()
    return (lim - daily_max).groupby("date").median()


def make_figures(city: str, df: pd.DataFrame, records: list[dict], outdir) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    # (a) load-duration curves
    for dataid, g in df.groupby("dataid"):
        use = clean_use(g).dropna().sort_values(ascending=False)
        axes[0].plot(np.linspace(0, 100, len(use)), use, lw=0.6, alpha=0.6)
    for name, s_kw in pslib.SERVICE_KW.items():
        axes[0].axhline(s_kw * pslib.NEC_DERATE, ls="--", lw=0.8, color="k")
        axes[0].annotate(f"{name}×0.8", (60, s_kw * pslib.NEC_DERATE), fontsize=7)
    axes[0].set(xlabel="% of minutes", ylabel="kW", title=f"{city}: load duration (1-min)")
    # (b) seasonal daily-min headroom
    smh = seasonal_min_headroom(df)
    axes[1].plot(pd.to_datetime(smh.index), smh.values, lw=0.9)
    axes[1].axhline(0, color="r", lw=0.8)
    axes[1].set(ylabel="kW", title="median daily min headroom (200A×0.8)")
    # (c) hostable node, year vs peak window
    ids = [r["dataid"] for r in records]
    year_x = [r["year"]["hostable_kw"]["200A"] for r in records]
    peak_x = [r.get("peak_window", {}).get("hostable_kw", {}).get("200A", np.nan)
              for r in records]
    pos = np.arange(len(ids))
    axes[2].bar(pos - 0.2, year_x, 0.4, label="year")
    axes[2].bar(pos + 0.2, peak_x, 0.4, label="peak window")
    axes[2].set(xticks=pos, title="hostable node kW (200A×0.8)")
    axes[2].set_xticklabels(ids, rotation=90, fontsize=6)
    axes[2].legend()
    fig.tight_layout()
    fig.savefig(outdir / f"headroom_{city}.png", dpi=150)
    plt.close(fig)


def hostable_fractions(records: list[dict], node_kws=(1.0, 5.0, 6.25, 12.5, 19.2)) -> dict:
    """Fraction of homes that can host a continuous X kW node, year vs peak window.

    NaN hostable_kw values (a home with no valid readings in the window) are
    excluded from the mean rather than counted as "cannot host" — a
    home-count is recorded alongside each fraction so an empty/near-empty
    denominator is visible instead of silently producing 0.0 or NaN.
    """
    out = {}
    for sc in pslib.SERVICE_KW:
        out[sc] = {}
        for x in node_kws:
            year_vals = [r["year"]["hostable_kw"][sc] >= x for r in records
                         if not np.isnan(r["year"]["hostable_kw"][sc])]
            peak_vals = [r["peak_window"]["hostable_kw"][sc] >= x for r in records
                         if "peak_window" in r
                         and not np.isnan(r["peak_window"]["hostable_kw"][sc])]
            year = float(np.mean(year_vals)) if year_vals else float("nan")
            peak = float(np.mean(peak_vals)) if peak_vals else float("nan")
            out[sc][f"{x:g}kW"] = {"year": year, "peak_window": peak,
                                    "n_year": len(year_vals), "n_peak": len(peak_vals)}
    return out


def run_city(city: str, meta: pd.DataFrame, outdir) -> dict:
    df = pslib.read_power(city, "1minute")
    # Raw vs masked comparison to report how many readings mask_implausible
    # dropped for this city; deliberately bypasses clean_use to get the
    # pre-mask values needed for the comparison.
    raw_use = pslib.reconstruct_use(df)
    masked_use = pslib.mask_implausible(raw_use)
    implausible_rows = raw_use.notna() & masked_use.isna()
    n_implausible_dropped = int(implausible_rows.sum())
    implausible_dataids = sorted(
        df.loc[implausible_rows, "dataid"].astype(int).unique().tolist()
    )
    print(f"=== {city} (masked {n_implausible_dropped} implausible reading(s), "
          f"dataids {implausible_dataids})")
    records = home_records(city, df, meta)
    kept = [r for r in records
            if r["coverage"] >= MIN_COVERAGE and r["valid_share"] >= MIN_COVERAGE]
    clean = [r for r in kept if not r["intervention"] and not r["battery"]]
    result = {
        "city": city, "n_homes": len(records), "n_kept": len(kept), "n_clean": len(clean),
        "n_dropped_no_data": sum(1 for r in records if r["valid_share"] < MIN_COVERAGE),
        "n_implausible_dropped": n_implausible_dropped,
        "implausible_dataids": implausible_dataids,
        "diurnal_check": diurnal_check(city, df),
        "records": kept,
        "hostable_fractions_all": hostable_fractions(kept),
        "hostable_fractions_clean": hostable_fractions(clean) if clean else None,
        "crosscheck_15min": crosscheck_15min(city, kept),
        "yearly": yearly_breakdown(df),
        "n_minutes_by_home": {r["dataid"]: r["year"]["n_minutes"] for r in kept},
        "negative_share_worst": max(r["negative_share"] for r in records),
    }
    make_figures(city, df, kept, outdir)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", choices=list(pslib.CITY_DIR), action="append")
    ap.add_argument("--sample", type=int, help="single dataid: quick eyeball mode")
    ap.add_argument("--month", help="YYYY-MM restriction for --sample")
    ap.add_argument("--outdir", default=str(pslib.OUTDIR))
    args = ap.parse_args()
    outdir = pslib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    meta = pslib.read_metadata()

    if args.sample is not None:
        city = (args.city or ["austin"])[0]
        df = pslib.read_power(city, "1minute")
        df = df[df["dataid"] == args.sample]
        if args.month:
            per = pd.Period(args.month)
            ts = pd.DatetimeIndex(df["ts"])
            df = df[(ts.year == per.year) & (ts.month == per.month)]
        use = clean_use(df)
        print(json.dumps(pslib.headroom_metrics(use), indent=2))
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df["ts"], use, lw=0.4)
        ax.set(ylabel="kW", title=f"{city} dataid={args.sample} {args.month or ''}")
        fig.savefig(outdir / f"sample_{city}_{args.sample}.png", dpi=150)
        return

    results = {c: run_city(c, meta, outdir) for c in (args.city or list(pslib.CITY_DIR))}
    for c, r in results.items():
        (outdir / f"headroom_{c}.json").write_text(json.dumps(r, indent=2))
        print(c, "peak_hour_local:", r["diurnal_check"]["peak_hour_local"],
              "| hostable 200A/12.5kW year vs peak:",
              r["hostable_fractions_all"]["200A"]["12.5kW"])


if __name__ == "__main__":
    main()
