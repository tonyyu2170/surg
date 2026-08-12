# scripts/cso_fetch.py
"""Fetch CSO table MEC02 -- Irish data-centre metered electricity consumption.

This is the DOSE variable, and it is why Ireland is worth the attention: every
US result in this project used a geographic proxy (Loudoun, DOM, Ashburn),
whereas this is measured consumption.

Verified 2026-08-12: JSON-stat 2.0, 44 quarters (2015Q1-2025Q4), 3 categories
(all metered / data centres / customers other than data centres), unit GWh.
Free, no registration.

Caveats that must reach the write-up: CSO has no data-centre classification --
sites are identified heuristically (name matching, business parks, meters above
1 GWh) -- and CSO warns new small sites fall below its thresholds. The series
is national and quarterly. It fixes EXISTENCE of an exposure trend, not
identification.

Usage: .venv/bin/python scripts/cso_fetch.py
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pandas as pd

URL = (
    "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/"
    "MEC02/JSON-stat/2.0/en"
)
DEST = Path("data/raw/cso/mec02.parquet")


def _labels(dim_spec: dict) -> list[str]:
    """Category labels in index order."""
    category = dim_spec["category"]
    index = category["index"]
    label = category.get("label", {})
    codes = (
        index
        if isinstance(index, list)
        else [c for c, _ in sorted(index.items(), key=lambda kv: kv[1])]
    )
    return [label.get(c, c) for c in codes]


def main() -> None:
    resp = httpx.get(URL, timeout=120.0)
    resp.raise_for_status()
    payload = json.loads(resp.text)
    ds = payload.get("dataset", payload)

    ids = ds["id"]
    sizes = ds["size"]
    values = ds["value"]
    labels = {d: _labels(ds["dimension"][d]) for d in ids}

    rows = []
    for flat, value in enumerate(values):
        coords, rest = [], flat
        for size in reversed(sizes):
            coords.append(rest % size)
            rest //= size
        coords.reverse()
        record = {d: labels[d][c] for d, c in zip(ids, coords, strict=True)}
        record["value_gwh"] = value
        rows.append(record)

    df = pd.DataFrame(rows)
    quarter_col = next(c for c in df.columns if c.startswith("TLIST"))
    category_col = next(
        c for c in df.columns if c not in ("STATISTIC", quarter_col, "value_gwh")
    )
    df = df.rename(columns={quarter_col: "quarter", category_col: "category"})

    wide = df.pivot_table(
        index="quarter", columns="category", values="value_gwh", aggfunc="first"
    ).reset_index()
    wide.columns.name = None

    dc_col = next(c for c in wide.columns if "Data centres" in c)
    total_col = next(c for c in wide.columns if "All metered" in c)
    wide["dc_gwh"] = wide[dc_col]
    wide["total_gwh"] = wide[total_col]
    wide["dc_share"] = wide["dc_gwh"] / wide["total_gwh"]
    wide["period"] = pd.PeriodIndex(wide["quarter"], freq="Q")
    wide = wide.sort_values("period").reset_index(drop=True)

    DEST.parent.mkdir(parents=True, exist_ok=True)
    wide.to_parquet(DEST, index=False)

    print(f"wrote {DEST} ({len(wide)} quarters)")
    print(wide[["quarter", "dc_gwh", "total_gwh", "dc_share"]].head(3).to_string(index=False))
    print("...")
    print(wide[["quarter", "dc_gwh", "total_gwh", "dc_share"]].tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
