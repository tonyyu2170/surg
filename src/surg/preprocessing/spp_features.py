# src/surg/preprocessing/spp_features.py
"""Parse SPP hourly load and nodal DA LMP into a Stage-1 panel.

Every structure here was verified against real files on 2026-08-10; see
docs/sources/availability/cross-iso-phase2-recon-verification.md section 3 for the era table and the
evidence behind each guard.

Four traps this module exists to defuse:
  1. Annual zips carry BOTH daily files and 12 monthly rollups covering the same
     hours. `monthly_members` keeps only the monthlies, which are the one family
     present in every archived year.
  2. Header whitespace drift: 2011-2014 have no space after commas, 2015+ do.
  3. Datetime format drift: early monthlies use '1/1/11 7:00', dailies use
     '11/22/2023 07:00:00'. Formats are inferred, never hard-coded.
  4. `MarketHour` is GMT hour-ENDING while one file spans one LOCAL Central day
     (23/24/25 rows). Converting to local prevailing time leaves one fall-back
     duplicate pair per year, so drivers pass dst_pairs_per_year=1.
"""
from __future__ import annotations

import re

import pandas as pd

TIME = "datetime_beginning_cpt"
LOCAL_TZ = "America/Chicago"

# Locked 17-zone roster: the stable footprint from the Oct-2015 Integrated
# System join through the 2026-03-24 schema break. The RTO-West additions
# (PRPA, WACM, WAUW, PSCO) are deliberately excluded.
ZONES: list[str] = [
    "CSWS", "EDE", "GRDA", "INDN", "KACY", "KCPL", "LES", "MPS", "NPPD",
    "OKGE", "OPPD", "SECI", "SPRM", "SPS", "WAUE", "WFEC", "WR",
]

_MONTHLY = re.compile(r"/HOURLY_LOAD-\d{6}\.csv$")


def monthly_members(names: list[str]) -> list[str]:
    """Monthly rollups only - never the dailies that share the same zip."""
    return sorted(n for n in names if _MONTHLY.search(n))


def gmt_hour_ending_to_local_beginning(stamps: pd.Series) -> pd.Series:
    """GMT hour-ending -> naive local Central hour-beginning.

    Subtracting one hour turns hour-ending into hour-beginning; converting to
    America/Chicago and dropping the offset yields the naive local clock the
    Stage-1 panel contract requires.
    """
    parsed = pd.to_datetime(stamps, format="mixed", utc=True)
    beginning = parsed - pd.Timedelta(hours=1)
    return beginning.dt.tz_convert(LOCAL_TZ).dt.tz_localize(None)


def parse_wide_load(raw: pd.DataFrame) -> pd.DataFrame:
    """Wide-era load file -> [TIME, load_mw_<zone>..., dst_transition_hour]."""
    frame = raw.copy()
    frame.columns = [str(c).strip() for c in frame.columns]

    missing = [z for z in ZONES if z not in frame.columns]
    if missing:
        raise ValueError(f"wide load file missing zones: {missing}")

    out = pd.DataFrame({TIME: gmt_hour_ending_to_local_beginning(frame["MarketHour"])})
    for zone in ZONES:
        out[f"load_mw_{zone}"] = pd.to_numeric(frame[zone], errors="coerce")

    out = out.sort_values(TIME).reset_index(drop=True)
    out["dst_transition_hour"] = out[TIME].duplicated(keep=False)
    return out


def parse_long_load(raw: pd.DataFrame) -> pd.DataFrame:
    """Long-era load file (2026-03-25 ->). Sums CF + NC per (hour, zone).

    Seven zones carry both a CF and an NC row; the wide era's single column
    equals their sum, so summing is what keeps the two eras on one level.
    Retained for completeness - the locked 17-zone panel stops before this era.
    """
    frame = raw.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    for col in ("Control Zone Name", "Forecast Area Type"):
        frame[col] = frame[col].astype(str).str.strip()

    frame[TIME] = gmt_hour_ending_to_local_beginning(frame["Market Hour"])
    summed = frame.groupby([TIME, "Control Zone Name"])["Load MW"].sum().unstack()
    summed = summed.reindex(columns=ZONES)
    summed.columns = [f"load_mw_{z}" for z in summed.columns]

    out = summed.reset_index().sort_values(TIME).reset_index(drop=True)
    out["dst_transition_hour"] = out[TIME].duplicated(keep=False)
    return out


def zone_price_from_nodal(nodal: pd.DataFrame, zones: list[str]) -> pd.DataFrame:
    """Zone price = unweighted mean of nodal LMPs whose name starts with the code.

    This is an explicit estimator choice (locked 2026-08-10): SPP publishes no
    zonal price, only ~1,222 settlement locations, and only 11 of 17 zones have
    any hub - those being vintage-tagged commercial hubs, not clean proxies.
    It is NOT a load-weighted settlement price and must be disclosed as such.
    """
    frame = nodal.copy()
    frame["location"] = frame["location"].astype(str).str.strip()

    out: pd.DataFrame | None = None
    for zone in zones:
        member = frame[frame["location"].str.upper().str.startswith(zone.upper())]
        if member.empty:
            continue
        mean = member.groupby(TIME)["lmp"].mean().rename(f"da_lmp_{zone}").reset_index()
        out = mean if out is None else out.merge(mean, on=TIME, how="outer")

    if out is None:
        raise ValueError("no nodal locations matched any zone prefix")
    return out.sort_values(TIME).reset_index(drop=True)
