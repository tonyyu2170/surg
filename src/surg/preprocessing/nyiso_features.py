"""Pure transforms for the NYISO Stage-1 diagnostic. No I/O."""
from __future__ import annotations

import pandas as pd

# Raw zone name -> column-safe token. 11 zones, stable since 1999.
ZONE_MAP = {
    "CAPITL": "capitl", "CENTRL": "centrl", "DUNWOD": "dunwod",
    "GENESE": "genese", "HUD VL": "hud_vl", "LONGIL": "longil",
    "MHK VL": "mhk_vl", "MILLWD": "millwd", "N.Y.C.": "nyc",
    "NORTH": "north", "WEST": "west",
}
ZONES = list(ZONE_MAP.values())


def _timestamps(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, format="mixed")
    if ts.isna().any():
        bad = series[ts.isna()].head(3).tolist()
        raise ValueError(f"unparseable Time Stamp values: {bad}")
    return ts


def parse_load(raw: pd.DataFrame) -> pd.DataFrame:
    """Long zone rows -> wide hourly `load_mw_<zone>`, hour-beginning EPT.

    NYISO stamps are already hour-beginning prevailing Eastern; the
    `Time Zone` column disambiguates the fall-back hour (01:00 EDT and
    01:00 EST both appear). We keep prevailing wall-clock as the panel key
    (DOM convention) and flag the duplicated pair via dst_transition_hour.
    """
    out = raw.copy()
    out["datetime_beginning_ept"] = _timestamps(out["Time Stamp"])
    unknown = set(out["Name"]) - set(ZONE_MAP)
    if unknown:
        raise ValueError(f"unknown NYISO zone names: {sorted(unknown)}")

    wide = (
        out.pivot_table(
            index=["datetime_beginning_ept", "Time Zone"],
            columns="Name", values="Integrated Load", aggfunc="first",
        )
        .rename(columns=ZONE_MAP)
        .add_prefix("load_mw_")
        .reset_index()
    )
    missing = [z for z in ZONES if f"load_mw_{z}" not in wide.columns]
    if missing:
        missing_raw = [k for k, v in ZONE_MAP.items() if v in [m for m in ZONES if f"load_mw_{m}" not in wide.columns]]
        raise ValueError(f"zones missing from load frame: {missing_raw}")

    wide = wide.sort_values(["datetime_beginning_ept", "Time Zone"], ascending=[True, False])
    wide["dst_transition_hour"] = wide["datetime_beginning_ept"].duplicated(keep=False)
    return wide.drop(columns=["Time Zone"]).reset_index(drop=True)


def parse_lbmp(raw: pd.DataFrame, *, prefix: str) -> pd.DataFrame:
    """Long zone LBMP rows -> wide `{prefix}_<zone>` hourly frame.

    Stage 1 uses TOTAL price only; the loss/congestion columns are ignored
    here (decomposition analysis is out of Stage-1 scope by design).
    Fall-back duplicate stamps average into one value (the ERCOT precedent:
    load keeps two rows, price one, merged many-to-one).
    """
    out = raw.copy()
    out["datetime_beginning_ept"] = _timestamps(out["Time Stamp"])
    unknown = set(out["Name"]) - set(ZONE_MAP)
    if unknown:
        raise ValueError(f"unknown NYISO zone names: {sorted(unknown)}")
    out["zone"] = out["Name"].map(ZONE_MAP)

    hourly = (
        out.groupby(["datetime_beginning_ept", "zone"])["LBMP ($/MWHr)"]
        .mean()
        .unstack("zone")
    )
    hourly.columns = [f"{prefix}_{c}" for c in hourly.columns]
    return hourly.reset_index()
