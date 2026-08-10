# scripts/isone_fetch.py
"""Download ISO-NE SMD hourly annual workbooks.

Usage: .venv/bin/python scripts/isone_fetch.py

One workbook per year carries load, decomposed DA/RT LMP and weather for all
eight load zones, so Stage 1 needs 11 files (~85 MB) rather than the ~1,400
daily WW_DALMP_ISO CSVs the Phase-1 memo budgeted. See
docs/cross-iso-phase2-recon-verification.md section 2.

The numeric document ids for 2024-2026 are verified constants: ISO-NE moved off
dated folders after 2023 and the ids are not reliably derivable.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

BASE = "https://www.iso-ne.com/static-assets/documents"
RAW = Path("data/raw/isone")
SLEEP_S = 2.0

URLS: dict[int, str] = {
    2016: f"{BASE}/2016/02/smd_hourly.xls",
    2017: f"{BASE}/2017/02/2017_smd_hourly.xlsx",
    2018: f"{BASE}/2018/02/2018_smd_hourly.xlsx",
    2019: f"{BASE}/2019/02/2019_smd_hourly.xlsx",
    2020: f"{BASE}/2020/02/2020_smd_hourly.xlsx",
    2021: f"{BASE}/2021/02/2021_smd_hourly.xlsx",
    2022: f"{BASE}/2022/02/2022_smd_hourly.xlsx",
    2023: f"{BASE}/2023/02/2023_smd_hourly.xlsx",
    2024: f"{BASE}/100008/2024_smd_hourly.xlsx",
    2025: f"{BASE}/100020/2025_smd_hourly.xlsx",
    2026: f"{BASE}/100032/2026_smd_hourly.xlsx",
}

FAILED: list[str] = []


def target_path(root: Path, year: int) -> Path:
    suffix = ".xls" if URLS[year].endswith(".xls") else ".xlsx"
    return root / f"{year}_smd_hourly{suffix}"


def is_excel(payload: bytes) -> bool:
    """xlsx is a zip (PK); xls is an OLE2 compound file."""
    return payload[:2] == b"PK" or payload[:4] == b"\xd0\xcf\x11\xe0"


def pull(client: httpx.Client, year: int, out: Path) -> None:
    """Fetch one workbook, retrying transport failures as well as bad responses.

    Never send a Range header to this host: ranged requests return non-Excel
    content (verified 2026-08-10).
    """
    if out.exists() and out.stat().st_size > 0:
        print(f"  {out.name} already present", flush=True)
        return
    for attempt in range(5):
        wait = 15 * (attempt + 1)
        try:
            resp = client.get(URLS[year], timeout=180.0)
        except httpx.HTTPError as exc:
            print(f"  retry {out.name}: {type(exc).__name__}; sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        if resp.status_code == 200 and is_excel(resp.content):
            out.write_bytes(resp.content)
            print(f"  {out.name} ({len(resp.content)//1024} KB)", flush=True)
            time.sleep(SLEEP_S)
            return
        print(
            f"  retry {out.name}: HTTP {resp.status_code}, "
            f"excel={is_excel(resp.content)}; sleeping {wait}s",
            flush=True,
        )
        time.sleep(wait)
    FAILED.append(out.name)
    print(f"  GAVE UP on {out.name} - continuing", flush=True)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "surg-research/1.0 (academic research)"}
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        for year in sorted(URLS):
            pull(client, year, target_path(RAW, year))
    if FAILED:
        print(f"\n=== {len(FAILED)} WORKBOOKS NEVER FETCHED - rerun to retry ===", flush=True)
        for name in FAILED:
            print(f"  {name}", flush=True)
    else:
        print(f"\nall {len(URLS)} workbooks present under {RAW}", flush=True)


if __name__ == "__main__":
    main()
