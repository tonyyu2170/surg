"""Load cached gridstatus chunks into canonical DataFrames.

Column renames map gridstatus names onto the repo's PJM-panel
conventions (docs/gridstatus-api-constraints.md, dataset table):
    lmp        -> total_lmp_rt
    energy     -> system_energy_price_rt
    congestion -> congestion_price_rt
    loss       -> marginal_loss_price_rt
    location_id -> pnode_id
Timestamps stay tz-aware UTC here; EPT derivation happens in the
panel builder. Dedupe on the unique key defends against any
inclusive-end boundary rows the API might return.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

_LMP_RENAME = {
    "location_id": "pnode_id",
    "lmp": "total_lmp_rt",
    "energy": "system_energy_price_rt",
    "congestion": "congestion_price_rt",
    "loss": "marginal_loss_price_rt",
}


def _read_all_chunks(data_root: Path, dataset: str) -> pd.DataFrame:
    files = sorted((data_root / dataset).rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no chunks found under {data_root / dataset}")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def load_gridstatus_dom_load(data_root: Path) -> pd.DataFrame:
    """Return [interval_start_utc, dom_load_mw], deduped, sorted."""
    df = _read_all_chunks(data_root, "pjm_load")
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True).dt.as_unit("ns")
    df = df.rename(columns={"dom": "dom_load_mw"})[["interval_start_utc", "dom_load_mw"]]
    df = df.drop_duplicates("interval_start_utc").sort_values("interval_start_utc")
    return df.reset_index(drop=True)


def load_gridstatus_lmp_long(data_root: Path) -> pd.DataFrame:
    """Return long-format LMP with panel-convention column names."""
    df = _read_all_chunks(data_root, "pjm_lmp_real_time_5_min")
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True).dt.as_unit("ns")
    df = df.rename(columns=_LMP_RENAME)
    df["pnode_id"] = df["pnode_id"].astype(int)
    cols = ["interval_start_utc", "pnode_id", "total_lmp_rt",
            "system_energy_price_rt", "congestion_price_rt", "marginal_loss_price_rt"]
    df = df[cols].drop_duplicates(["interval_start_utc", "pnode_id"])
    return df.sort_values(["interval_start_utc", "pnode_id"]).reset_index(drop=True)
