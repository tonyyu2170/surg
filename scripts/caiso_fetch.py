"""Download CAISO OASIS actual load + DAM LMPs as CSV-in-zip chunks.

Keyless; informal rate limits -> 6 s sleep, 28-day chunks, retry on
non-zip responses. Verified 2026-08-09: SLD_FCST/ACTUAL v1 returns data
back to 2010 (MRTU era starts 2009-04). https required (http is empty).

Usage: .venv/bin/python scripts/caiso_fetch.py
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

RAW = Path("data/raw/caiso")
BASE = "https://oasis.caiso.com/oasisapi/SingleZip"
LOAD_START = pd.Timestamp("2009-04-01")
PRICE_START = pd.Timestamp("2009-04-01")
CHUNK_DAYS = 28
SLEEP_S = 6.0
NODES = [
    "DLAP_PGAE-APND", "DLAP_SCE-APND", "DLAP_SDGE-APND", "DLAP_VEA-APND",
    "TH_NP15_GEN-APND", "TH_SP15_GEN-APND", "TH_ZP26_GEN-APND",
]


def stamp(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y%m%dT%H:%M-0000")


FAILED: list[str] = []


def pull(client: httpx.Client, params: dict, out: Path) -> None:
    """Fetch one chunk, retrying transport failures as well as bad responses.

    OASIS is intermittently slow: the same request can time out and then
    succeed seconds later (verified 2026-08-09 - one 28-day chunk timed out
    at 40 s twice, then returned 200 in 25 s). `client.get` therefore raises
    `httpx.ReadTimeout` straight out of the retry loop unless it is caught
    here, which previously killed the whole multi-hour run on the first slow
    request.

    After the retry budget is spent the chunk is recorded in `FAILED` and the
    run continues, so one bad chunk cannot cost the other ~1,500. Failures are
    reported loudly at the end, and would also surface downstream as a panel
    gap - they are never silently skipped.
    """
    if out.exists() and out.stat().st_size > 0:
        return
    for attempt in range(5):
        wait = 30 * (attempt + 1)
        try:
            resp = client.get(BASE, params=params, timeout=180.0)
        except httpx.HTTPError as exc:
            print(f"  retry {out.name}: {type(exc).__name__}; sleeping {wait}s", flush=True)
            time.sleep(wait)
            continue
        if resp.status_code == 200 and resp.content[:2] == b"PK":
            out.write_bytes(resp.content)
            print(f"  {out.name} ({len(resp.content)//1024} KB)", flush=True)
            time.sleep(SLEEP_S)
            return
        print(f"  retry {out.name}: HTTP {resp.status_code}; sleeping {wait}s", flush=True)
        time.sleep(wait)
    FAILED.append(out.name)
    print(f"  GAVE UP on {out.name} - continuing", flush=True)


def chunks(start: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    today = pd.Timestamp.today().normalize()
    edges = list(pd.date_range(start, today, freq=f"{CHUNK_DAYS}D"))
    if edges[-1] < today:
        edges.append(today)
    return [(a, b) for a, b in zip(edges, edges[1:]) if a < b]


def main() -> None:
    (RAW / "load").mkdir(parents=True, exist_ok=True)
    (RAW / "da_lmp").mkdir(parents=True, exist_ok=True)
    with httpx.Client() as client:
        for a, b in chunks(LOAD_START):
            pull(client, {
                "queryname": "SLD_FCST", "market_run_id": "ACTUAL", "version": "1",
                "startdatetime": stamp(a), "enddatetime": stamp(b), "resultformat": "6",
            }, RAW / "load" / f"load_{a:%Y%m%d}_{b:%Y%m%d}.zip")
        for node in NODES:
            for a, b in chunks(PRICE_START):
                pull(client, {
                    "queryname": "PRC_LMP", "market_run_id": "DAM", "version": "12",
                    "node": node,
                    "startdatetime": stamp(a), "enddatetime": stamp(b), "resultformat": "6",
                }, RAW / "da_lmp" / f"{node}_{a:%Y%m%d}_{b:%Y%m%d}.zip")

    if FAILED:
        print(f"\n=== {len(FAILED)} CHUNKS NEVER FETCHED - rerun to retry ===", flush=True)
        for name in FAILED:
            print(f"  {name}", flush=True)
    else:
        print("\n=== all chunks present ===", flush=True)


if __name__ == "__main__":
    main()
