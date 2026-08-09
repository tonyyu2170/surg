"""Pure transforms for the IESO Stage-1 diagnostic. No I/O.

IESO files are fixed EST year-round (24 rows/day, no DST rows — verified),
hour-ending 1-24. `dst_transition_hour` is always False and the quality
gate runs with dst_pairs_per_year=0.
"""
from __future__ import annotations

import pandas as pd

ZONE_MAP = {
    "Ontario Demand": "ontario", "Northwest": "northwest", "Northeast": "northeast",
    "Ottawa": "ottawa", "East": "east", "Toronto": "toronto", "Essa": "essa",
    "Bruce": "bruce", "Southwest": "southwest", "Niagara": "niagara", "West": "west",
}
ZONES = list(ZONE_MAP.values())
# Confirmed against the real 2024 file in Task 9 Step 3; adjust here if the
# real header uses different names.
HOEP_COLS = {"date": "Date", "hour": "Hour", "hoep": "HOEP"}


def _hour_ending_to_beginning(dates: pd.Series, hours: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(dates)
    if parsed.isna().any():
        raise ValueError("unparseable Date values in IESO frame")
    numbers = pd.to_numeric(hours, errors="coerce")
    if numbers.isna().any() or not numbers.between(1, 24).all():
        raise ValueError("Hour values outside 1-24 in IESO frame")
    return parsed + pd.to_timedelta(numbers - 1, unit="h")


def parse_demand_zonal(raw: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in ZONE_MAP if c not in raw.columns]
    if missing:
        raise ValueError(f"zones missing from IESO frame: {missing}")

    out = pd.DataFrame(
        {"datetime_beginning_est": _hour_ending_to_beginning(raw["Date"], raw["Hour"])}
    )
    for src, zone in ZONE_MAP.items():
        out[f"load_mw_{zone}"] = pd.to_numeric(raw[src], errors="coerce").to_numpy()
    out["dst_transition_hour"] = False
    return out.sort_values("datetime_beginning_est").reset_index(drop=True)


def parse_hoep(raw: pd.DataFrame) -> pd.DataFrame:
    for key in HOEP_COLS.values():
        if key not in raw.columns:
            raise ValueError(f"HOEP column {key!r} not found; got {list(raw.columns)}")
    out = pd.DataFrame(
        {
            "datetime_beginning_est": _hour_ending_to_beginning(
                raw[HOEP_COLS["date"]], raw[HOEP_COLS["hour"]]
            ),
            "hoep": pd.to_numeric(raw[HOEP_COLS["hoep"]], errors="coerce"),
        }
    )
    return out.sort_values("datetime_beginning_est").reset_index(drop=True)
