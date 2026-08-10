# scripts/miso_fetch.py
"""Download MISO daily load and DA ex-post LMP reports.

Usage: .venv/bin/python scripts/miso_fetch.py

Retention on docs.misoenergy.org/marketreports is current + 3 calendar years,
so the Stage-1 window (2023-01 ->) is inside it. Each df_al.xls covers a 7-day
reporting period but carries ActualLoad for only the single day before
publication, so every market day needs its own file.

NEVER POST to misoenergy.org/api/find/... - it is an Elasticsearch write
endpoint. This script only issues GETs.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

BASE = "https://docs.misoenergy.org/marketreports"
RAW = Path("data/raw/miso")
SLEEP_S = 0.5

MAX_START = pd.Timestamp("2023-01-01")
SUFFIX = {"df_al": "xls", "da_expost_lmp": "csv"}

FAILED: list[str] = []


def family_url(family: str, day: pd.Timestamp) -> str:
    return f"{BASE}/{day:%Y%m%d}_{family}.{SUFFIX[family]}"


def market_days() -> list[pd.Timestamp]:
    """Every day from the Stage-1 start through yesterday."""
    end = pd.Timestamp.today().normalize() - pd.Timedelta(days=1)
    return list(pd.date_range(MAX_START, end, freq="D"))


def pull(client: httpx.Client, family: str, day: pd.Timestamp) -> None:
    out = RAW / family / f"{day:%Y%m%d}_{family}.{SUFFIX[family]}"
    if out.exists() and out.stat().st_size > 0:
        return
    url = family_url(family, day)
    for attempt in range(4):
        wait = 15 * (attempt + 1)
        try:
            resp = client.get(url, timeout=120.0)
        except httpx.HTTPError as exc:
            print(f"  retry {out.name}: {type(exc).__name__}; sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        if resp.status_code == 200 and len(resp.content) > 1000:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(resp.content)
            time.sleep(SLEEP_S)
            return
        if resp.status_code == 404:
            FAILED.append(f"{out.name} (404)")
            return
        print(f"  retry {out.name}: HTTP {resp.status_code}; sleeping {wait}s", flush=True)
        time.sleep(wait)
    FAILED.append(out.name)
    print(f"  GAVE UP on {out.name} - continuing", flush=True)


def main() -> None:
    headers = {"User-Agent": "surg-research/1.0 (academic research)"}
    days = market_days()
    print(f"fetching {len(days)} market days x 2 families", flush=True)
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for family in SUFFIX:
            for i, day in enumerate(days, 1):
                pull(client, family, day)
                if i % 100 == 0:
                    print(f"  {family}: {i}/{len(days)}", flush=True)

    if FAILED:
        print(f"\n=== {len(FAILED)} MISO FILES NEVER FETCHED ===", flush=True)
        for name in FAILED:
            print(f"  {name}", flush=True)
    else:
        print(f"\nMISO fetch complete under {RAW}", flush=True)


if __name__ == "__main__":
    main()
