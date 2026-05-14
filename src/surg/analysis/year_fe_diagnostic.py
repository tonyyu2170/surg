"""τ=0.99 secular sign-flip diagnostic (sub-q1 closure item #3).

Three-layer evidence:
  L1: raw per-year LMP percentile stats (descriptive only).
  L2: pair-bootstrap year-dummy coefficient CIs (per-year LEVEL SHIFTS,
      not a trend test).
  L3: pair-bootstrap secular-component CI = primary_z_slope - year_fe_z_slope
      at each tau (the actual trend test).

Reuses qr_full.fit_qr_full for the year-FE QR.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.qr_full import fit_qr_full


def compute_raw_per_year_stats(
    panel: pd.DataFrame,
    *,
    response_col: str,
    year_col: str,
    pct_list: tuple[float, ...] = (0.90, 0.95, 0.99),
) -> list[dict]:
    """Per-year summary stats of `response_col`. Descriptive only — no model."""
    sub = panel.dropna(subset=[response_col, year_col]).copy()
    sub["__year"] = pd.to_datetime(sub[year_col]).dt.year
    stats: list[dict] = []
    for year, group in sub.groupby("__year"):
        row = {"year": int(year), "n_obs": int(len(group))}
        for p in pct_list:
            row[f"p{int(p*100)}"] = float(np.quantile(group[response_col].to_numpy(), p))
        stats.append(row)
    return sorted(stats, key=lambda r: r["year"])
