# scripts/spp_fetch.py
"""Download SPP hourly load and DA LMP archives.

Usage: .venv/bin/python scripts/spp_fetch.py

Two eras per series (docs/cross-iso-phase2-recon-verification.md section 3):
  * 2016-2024: one annual zip per year at ?path=/{YYYY}/{YYYY}.zip
  * 2025 ->  : daily CSVs; no annual zip exists (404 verified)

The panel stops at 2026-03-24, the last day before the wide->long schema break
and the RTO-West roster jump, per the locked 17-zone single-panel decision.

Disk: DA LMP annual zips 2016-2024 total ~2.53 GB; the daily era adds ~1.6 GB.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

BASE = "https://portal.spp.org/file-browser-api/download"
RAW = Path("data/raw/spp")
SLEEP_S = 1.0

MAX_START = pd.Timestamp("2016-01-01")
DAILY_ERA_START = pd.Timestamp("2025-01-01")
PANEL_END = pd.Timestamp("2026-03-24")  # inclusive last day, pre-schema-break

LOAD = "hourly-load"
PRICE = "da-lmp-by-settlement-location"

FAILED: list[str] = []


def zip_url(fileset: str, year: int) -> str:
    return f"{BASE}/{fileset}?path=/{year}/{year}.zip"


def daily_url(fileset: str, day: pd.Timestamp) -> str:
    if fileset == LOAD:
        path = f"/{day:%Y}/DAILY_HOURLY_LOAD-{day:%Y%m%d}.csv"
    else:
        path = f"/{day:%Y}/{day:%m}/By_Day/DA-LMP-SL-{day:%Y%m%d}0100.csv"
    return f"{BASE}/{fileset}?path={path}"


def daily_dates() -> list[pd.Timestamp]:
    return list(pd.date_range(DAILY_ERA_START, PANEL_END, freq="D"))


def pull(client: httpx.Client, url: str, out: Path, *, expect_zip: bool) -> None:
    """Fetch one artifact, retrying transport failures as well as bad responses."""
    if out.exists() and out.stat().st_size > 0:
        return
    for attempt in range(5):
        wait = 20 * (attempt + 1)
        try:
            resp = client.get(url, timeout=600.0)
        except httpx.HTTPError as exc:
            print(f"  retry {out.name}: {type(exc).__name__}; sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        ok = resp.status_code == 200 and len(resp.content) > 0
        if ok and expect_zip:
            ok = resp.content[:2] == b"PK"
        if ok:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(resp.content)
            print(f"  {out.name} ({len(resp.content)//1024} KB)", flush=True)
            time.sleep(SLEEP_S)
            return
        print(f"  retry {out.name}: HTTP {resp.status_code}; sleeping {wait}s", flush=True)
        time.sleep(wait)
    FAILED.append(out.name)
    print(f"  GAVE UP on {out.name} - continuing", flush=True)


def main() -> None:
    headers = {"User-Agent": "surg-research/1.0 (academic research)"}
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for fileset, tag in [(LOAD, "load"), (PRICE, "price")]:
            for year in range(MAX_START.year, DAILY_ERA_START.year):
                out = RAW / tag / "zips" / f"{year}.zip"
                pull(client, zip_url(fileset, year), out, expect_zip=True)
            for day in daily_dates():
                name = (
                    f"DAILY_HOURLY_LOAD-{day:%Y%m%d}.csv"
                    if fileset == LOAD
                    else f"DA-LMP-SL-{day:%Y%m%d}0100.csv"
                )
                out = RAW / tag / "daily" / name
                pull(client, daily_url(fileset, day), out, expect_zip=False)

    if FAILED:
        print(f"\n=== {len(FAILED)} SPP FILES NEVER FETCHED - rerun to retry ===", flush=True)
        for name in FAILED:
            print(f"  {name}", flush=True)
    else:
        print(f"\nSPP fetch complete under {RAW}", flush=True)


if __name__ == "__main__":
    main()
