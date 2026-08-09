"""Pure transforms for the NYISO Stage-1 diagnostic. No I/O."""
from __future__ import annotations

import pandas as pd

# Raw zone name -> column-safe token. 11 zones in the split convention, in
# effect 2005-01-31 onward. Before that, load reports a single combined
# N.Y.C._LONGIL zone instead of the N.Y.C./LONGIL pair (see MERGED_ZONE_MAP).
ZONE_MAP = {
    "CAPITL": "capitl", "CENTRL": "centrl", "DUNWOD": "dunwod",
    "GENESE": "genese", "HUD VL": "hud_vl", "LONGIL": "longil",
    "MHK VL": "mhk_vl", "MILLWD": "millwd", "N.Y.C.": "nyc",
    "NORTH": "north", "WEST": "west",
}
ZONES = list(ZONE_MAP.values())

# Merged-zone convention: N.Y.C. and LONGIL (post-2005-01-31) and the
# pre-split combined N.Y.C._LONGIL name all collapse into one zone,
# nyc_longil, giving 10 zones that span the full load archive (2001-06-).
MERGED_ZONE_MAP = {
    **ZONE_MAP,
    "N.Y.C.": "nyc_longil", "LONGIL": "nyc_longil", "N.Y.C._LONGIL": "nyc_longil",
}
MERGED_ZONES = list(dict.fromkeys(MERGED_ZONE_MAP.values()))

# External interface/proxy buses that appear in every damlbmp_zone/
# realtime_zone file across the archive alongside the 11 NY load zones:
# Hydro-Quebec, Neptune (NY-NE tie), Ontario-Hydro tie, PJM. Not NY load
# zones, so they are dropped rather than mapped.
EXTERNAL_PRICE_ZONES = {"H Q", "NPX", "O H", "PJM"}


def _timestamps(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, format="mixed")
    if ts.isna().any():
        bad = series[ts.isna()].head(3).tolist()
        raise ValueError(f"unparseable Time Stamp values: {bad}")
    return ts


def parse_load(raw: pd.DataFrame, *, merge_nyc_longil: bool = False) -> pd.DataFrame:
    """Long zone rows -> wide hourly `load_mw_<zone>`, hour-beginning EPT.

    NYISO stamps are already hour-beginning prevailing Eastern; the
    `Time Zone` column disambiguates the fall-back hour (01:00 EDT and
    01:00 EST both appear). We keep prevailing wall-clock as the panel key
    (DOM convention) and flag the duplicated pair via dst_transition_hour.

    `merge_nyc_longil` selects the zone convention:
      * False (default, today's behavior): 11 split zones. NYISO reported
        a single combined N.Y.C._LONGIL zone before 2005-01-31; any row
        with that name is unrecognized under this convention and raises
        (the caller is responsible for restricting the window to
        2005-01-31 onward before calling in this mode).
      * True: 10 zones. N.Y.C._LONGIL (pre-2005) and the N.Y.C./LONGIL
        pair (post-2005) all collapse into one `nyc_longil` column; the
        post-2005 pair is SUMMED (load is additive in MW) so the series
        is continuous across the 2005-01-31 boundary.
    """
    out = raw.copy()
    out["datetime_beginning_ept"] = _timestamps(out["Time Stamp"])

    zone_map = MERGED_ZONE_MAP if merge_nyc_longil else ZONE_MAP
    zones = MERGED_ZONES if merge_nyc_longil else ZONES
    unknown = set(out["Name"]) - set(zone_map)
    if unknown:
        raise ValueError(f"unknown NYISO zone names: {sorted(unknown)}")

    pivot = out.pivot_table(
        index=["datetime_beginning_ept", "Time Zone"],
        columns="Name", values="Integrated Load", aggfunc="first",
    )
    load_cols = {}
    for zone in zones:
        raw_names = [n for n in pivot.columns if zone_map[n] == zone]
        load_cols[f"load_mw_{zone}"] = pivot[raw_names].sum(axis=1, min_count=1)
    wide = pd.DataFrame(load_cols, index=pivot.index).reset_index()

    missing = [z for z in zones if wide[f"load_mw_{z}"].isna().all()]
    if missing:
        missing_raw = sorted(k for k, v in zone_map.items() if v in missing)
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

    Every price file also carries four external interface/proxy buses
    (EXTERNAL_PRICE_ZONES) alongside the 11 NY load zones. Those are
    deliberately excluded, not a schema error, so they are dropped before
    the unknown-name check; anything else unrecognized still raises, to
    catch genuine schema drift.
    """
    out = raw.copy()
    out["datetime_beginning_ept"] = _timestamps(out["Time Stamp"])
    unknown = set(out["Name"]) - set(ZONE_MAP) - EXTERNAL_PRICE_ZONES
    if unknown:
        raise ValueError(f"unknown NYISO zone names: {sorted(unknown)}")
    out = out[out["Name"].isin(ZONE_MAP)]
    out["zone"] = out["Name"].map(ZONE_MAP)

    hourly = (
        out.groupby(["datetime_beginning_ept", "zone"])["LBMP ($/MWHr)"]
        .mean()
        .unstack("zone")
    )
    hourly.columns = [f"{prefix}_{c}" for c in hourly.columns]
    return hourly.reset_index()
