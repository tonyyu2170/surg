"""LMP-only 5-min panel builder for sub-q1 item #8 Part B.

Decoupled from the joint Z+LMP builder: Part B is descriptive (5-min
vs hourly spike-exceedance comparison) and does not need DOM-load,
reserves, or filter columns. Used over the full 6-month 5-min LMP
archive on disk.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.preprocessing.loaders_5min import load_rt_lmp_5min


def build_lmp_only_5min_panel(data_root: Path) -> pd.DataFrame:
    """Return the long-format 5-min nodal LMP panel under data_root.

    Output is the loader's output unchanged (sorted by pnode_id, then
    timestamp; deduped on (pnode_id, timestamp)). One row per
    (pnode, 5-min stamp) — all 11 locked target pnodes preserved.
    """
    return load_rt_lmp_5min(data_root)
