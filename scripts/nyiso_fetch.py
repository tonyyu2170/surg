"""Download NYISO monthly archive zips: load + DA/RT zonal LBMP.

All public, no key, no quota (politeness sleep only). Verified 2026-08-09:
  palIntegrated : 2001-06 -> present  (hourly integrated actual load, 11 zones)
  damlbmp/_zone : 1999-11 -> present  (DA zonal LBMP, decomposed columns)
  realtime/_zone: 2001-06 -> present  (RT zonal LBMP)

Usage: .venv/bin/python scripts/nyiso_fetch.py
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

RAW = Path("data/raw/nyiso")
BASE = "http://mis.nyiso.com/public/csv"
FAMILIES = {
    "palIntegrated": ("palIntegrated", pd.Timestamp("2001-06-01")),
    "damlbmp_zone": ("damlbmp", pd.Timestamp("1999-11-01")),
    "realtime_zone": ("realtime", pd.Timestamp("2001-06-01")),
}
SLEEP_S = 2.0


def month_starts(first: pd.Timestamp) -> list[pd.Timestamp]:
    last = pd.Timestamp.today().normalize().replace(day=1)
    return list(pd.date_range(first, last, freq="MS"))


def fetch_family(client: httpx.Client, key: str, family: str, first: pd.Timestamp) -> None:
    dest = RAW / key
    dest.mkdir(parents=True, exist_ok=True)
    suffix = "_zone" if key.endswith("_zone") else ""
    for month in month_starts(first):
        stamp = month.strftime("%Y%m%d")
        name = f"{stamp}{family}{suffix}_csv.zip"
        out = dest / name
        if out.exists() and out.stat().st_size > 0:
            continue
        url = f"{BASE}/{family}/{name}"
        resp = client.get(url, timeout=120.0, follow_redirects=True)
        if resp.status_code == 404:
            raise RuntimeError(f"unexpected 404 (verified depth says it exists): {url}")
        resp.raise_for_status()
        out.write_bytes(resp.content)
        print(f"  {key} {stamp} ({len(resp.content)//1024} KB)", flush=True)
        time.sleep(SLEEP_S)


def main() -> None:
    with httpx.Client() as client:
        for key, (family, first) in FAMILIES.items():
            print(f"== {key}")
            fetch_family(client, key, family, first)


if __name__ == "__main__":
    main()
