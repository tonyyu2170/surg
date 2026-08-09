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


def pull(client: httpx.Client, params: dict, out: Path) -> None:
    if out.exists() and out.stat().st_size > 0:
        return
    for attempt in range(5):
        resp = client.get(BASE, params=params, timeout=180.0)
        if resp.status_code == 200 and resp.content[:2] == b"PK":
            out.write_bytes(resp.content)
            print(f"  {out.name} ({len(resp.content)//1024} KB)", flush=True)
            time.sleep(SLEEP_S)
            return
        wait = 30 * (attempt + 1)
        print(f"  retry {out.name}: HTTP {resp.status_code}; sleeping {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"gave up on {out.name}")


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


if __name__ == "__main__":
    main()
