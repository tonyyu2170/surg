"""Download IESO annual zonal-demand + HOEP CSVs.

Public open directory, verified 2026-08-09:
  DemandZonal        : PUB_DemandZonal_{YYYY}.csv, 2003 -> present
  Demand (Ontario)   : PUB_Demand_{YYYY}.csv, 2002 -> present
  PriceHOEPPredispOR : PUB_PriceHOEPPredispOR_{YYYY}.csv, 2002 -> (HOEP era
                       ended 2025-04-30 with Market Renewal)

Usage: .venv/bin/python scripts/ieso_fetch.py
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

RAW = Path("data/raw/ieso")
BASE = "https://reports-public.ieso.ca/public"
FAMILIES = {
    "DemandZonal": ("PUB_DemandZonal_{y}.csv", 2003),
    "Demand": ("PUB_Demand_{y}.csv", 2002),
    "PriceHOEPPredispOR": ("PUB_PriceHOEPPredispOR_{y}.csv", 2002),
}
LAST_YEAR = 2026
SLEEP_S = 1.0


def main() -> None:
    with httpx.Client() as client:
        for family, (pattern, first) in FAMILIES.items():
            dest = RAW / family
            dest.mkdir(parents=True, exist_ok=True)
            for year in range(first, LAST_YEAR + 1):
                name = pattern.format(y=year)
                out = dest / name
                if out.exists() and out.stat().st_size > 0:
                    continue
                resp = client.get(f"{BASE}/{family}/{name}", timeout=120.0)
                resp.raise_for_status()
                out.write_bytes(resp.content)
                print(f"  {name} ({len(resp.content)//1024} KB)", flush=True)
                time.sleep(SLEEP_S)


if __name__ == "__main__":
    main()
