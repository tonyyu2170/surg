# scripts/ukpn_fetch.py
"""Download UK Power Networks data-centre datasets (Opendatasoft Explore v2.1).

Usage: .venv/bin/python scripts/ukpn_fetch.py

Constraints and gotchas are documented in docs/ukpn-api-constraints.md. The
two that shape this script:

  * /records caps at offset+limit <= 10,000, so the 5.44M-row demand-profiles
    dataset is unreachable by pagination. /exports/parquet is the only bulk
    route, and it honours `where=` filters.
  * An export costs 1 API call regardless of size (quota is 100,000 calls per
    day, resetting 00:00 UTC), so partitioning is essentially free. We
    partition the big dataset by year because a single unfiltered export
    streams at only ~65 KB/s and runs ~30 min -- year slices give resumable
    checkpoints instead of one long all-or-nothing transfer.

Idempotent: re-runs skip any target already on disk, same as the other
per-market fetchers. Partial downloads are written to `.part` and only
renamed on success, so an interrupted run never leaves a truncated parquet
looking complete.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx

BASE = "https://ukpowernetworks.opendatasoft.com/api/explore/v2.1"
RAW = Path("data/raw/ukpn")
TIMEOUT_S = 1800.0
SLEEP_S = 1.0

PROFILES = "ukpn-data-centre-demand-profiles"
# Panel runs 2023-01-01 -> 2026-05-13; 2026 slice is partial by construction.
PROFILE_YEARS = (2023, 2024, 2025, 2026)

# Small enough to take whole; no partitioning needed.
SMALL = ("ukpn-data-centres-by-local-authority", "ukpn-large-demand-list")

FAILED: list[str] = []


def api_key() -> str:
    key = os.environ.get("UK_POWER_API_KEY")
    if not key:
        sys.exit("UK_POWER_API_KEY not set -- source .env first")
    return key


def fetch(client: httpx.Client, dataset: str, dest: Path, where: str | None) -> None:
    """Stream one parquet export to dest, skipping if it already exists."""
    if dest.exists():
        print(f"  skip (exists): {dest.name}")
        return

    params = {"where": where} if where else {}
    part = dest.with_suffix(dest.suffix + ".part")
    url = f"{BASE}/catalog/datasets/{dataset}/exports/parquet"

    try:
        with client.stream("GET", url, params=params) as r:
            r.raise_for_status()
            with part.open("wb") as fh:
                for chunk in r.iter_bytes(chunk_size=1 << 20):
                    fh.write(chunk)
    except Exception as exc:  # noqa: BLE001 -- record and continue to next slice
        part.unlink(missing_ok=True)
        print(f"  FAILED {dest.name}: {type(exc).__name__}: {exc}")
        FAILED.append(dest.name)
        return

    part.rename(dest)
    print(f"  wrote {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Apikey {api_key()}"}

    with httpx.Client(headers=headers, timeout=TIMEOUT_S, follow_redirects=False) as client:
        print(f"{PROFILES} (by year):")
        for year in PROFILE_YEARS:
            where = (
                f"local_timestamp >= date'{year}-01-01' "
                f"AND local_timestamp < date'{year + 1}-01-01'"
            )
            fetch(client, PROFILES, RAW / f"{PROFILES}-{year}.parquet", where)
            time.sleep(SLEEP_S)

        for dataset in SMALL:
            print(f"{dataset}:")
            fetch(client, dataset, RAW / f"{dataset}.parquet", None)
            time.sleep(SLEEP_S)

    if FAILED:
        sys.exit(f"{len(FAILED)} target(s) failed: {', '.join(FAILED)}")
    print("done")


if __name__ == "__main__":
    main()
