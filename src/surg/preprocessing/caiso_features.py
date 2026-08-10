"""Pure transforms for the CAISO Stage-1 diagnostic. No I/O."""
from __future__ import annotations

import pandas as pd

# CAISO TAC areas only; every other TAC_AREA_NAME in the ACTUAL report is a
# WEIM member whose rows enter in later years and must not leak into the
# panel (roster-growth trap, memo §4).
TAC_MAP = {
    "CA ISO-TAC": "caiso_total", "PGE-TAC": "pge", "SCE-TAC": "sce",
    "SDGE-TAC": "sdge", "VEA-TAC": "vea", "MWD-TAC": "mwd",
}
TACS = list(TAC_MAP)
ZONES = list(TAC_MAP.values())

# The TAC roster grew over the archive: not every zone above is present
# from day one. Empirically verified by scanning all completed load zips
# on disk (227 files):
#   CA ISO-TAC, PGE-TAC, SCE-TAC, SDGE-TAC -> present from 2009-04-01
#   VEA-TAC -> first appears 2013-01-02
#   MWD-TAC -> first appears 2018-03-21
# FULL_DEPTH_ZONES is the subset that spans the full 2009-04-01 archive
# depth; ZONES (the complete 6-zone roster) is only valid from 2018-03-21
# onward, once the last zone (MWD) has appeared.
FULL_DEPTH_ZONES = ["caiso_total", "pge", "sce", "sdge"]
NODE_MAP = {
    "DLAP_PGAE-APND": "dlap_pgae", "DLAP_SCE-APND": "dlap_sce",
    "DLAP_SDGE-APND": "dlap_sdge", "DLAP_VEA-APND": "dlap_vea",
    "TH_NP15_GEN-APND": "th_np15", "TH_SP15_GEN-APND": "th_sp15",
    "TH_ZP26_GEN-APND": "th_zp26",
}


def _to_ppt(series: pd.Series) -> pd.Series:
    """GMT interval starts -> naive prevailing Pacific wall clock."""
    ts = pd.to_datetime(series, utc=True)
    if ts.isna().any():
        raise ValueError("unparseable INTERVALSTARTTIME_GMT values")
    return ts.dt.tz_convert("America/Los_Angeles").dt.tz_localize(None)


def parse_load(raw: pd.DataFrame) -> pd.DataFrame:
    """OASIS SLD_FCST/ACTUAL rows -> wide hourly `load_mw_<tac>` in PPT."""
    sub = raw[raw["TAC_AREA_NAME"].isin(TACS)].copy()
    if sub.empty:
        raise ValueError("no CAISO TAC rows found — wrong file family?")
    sub["datetime_beginning_ppt"] = _to_ppt(sub["INTERVALSTARTTIME_GMT"])
    sub["_gmt"] = pd.to_datetime(sub["INTERVALSTARTTIME_GMT"], utc=True)

    wide = (
        sub.pivot_table(
            index=["datetime_beginning_ppt", "_gmt"], columns="TAC_AREA_NAME",
            values="MW", aggfunc="first",
        )
        .rename(columns=TAC_MAP)
        .add_prefix("load_mw_")
        .reset_index()
        .sort_values(["datetime_beginning_ppt", "_gmt"])
        .reset_index(drop=True)
    )
    # GMT is unambiguous, so the fall-back pair arrives as two distinct GMT
    # hours mapping to the same PPT wall clock: flag exactly that.
    wide["dst_transition_hour"] = wide["datetime_beginning_ppt"].duplicated(keep=False)
    return wide.drop(columns="_gmt")


def parse_dam_lmp(raw: pd.DataFrame) -> pd.DataFrame:
    """OASIS PRC_LMP rows -> wide hourly `da_lmp_<node>` (total LMP only)."""
    sub = raw[raw["LMP_TYPE"] == "LMP"].copy()
    if sub.empty:
        raise ValueError("no LMP_TYPE == 'LMP' rows — wrong query/version?")
    sub["datetime_beginning_ppt"] = _to_ppt(sub["INTERVALSTARTTIME_GMT"])
    sub["node"] = sub["NODE"].map(NODE_MAP)
    if sub["node"].isna().any():
        unknown = sorted(set(sub.loc[sub["node"].isna(), "NODE"]))
        raise ValueError(f"unexpected CAISO nodes: {unknown}")

    hourly = (
        sub.groupby(["datetime_beginning_ppt", "node"])["MW"].mean().unstack("node")
    )
    hourly.columns = [f"da_lmp_{c}" for c in hourly.columns]
    return hourly.reset_index()
