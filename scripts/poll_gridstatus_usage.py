"""Poll GET /api_usage for each GRIDSTATUS_API_KEY_1..6.

Read-only. Prints plan limits, the current usage period, and consumption per
account. Never prints a key value — only a short fingerprint, so output is
safe to paste into logs or notes.
"""
from __future__ import annotations

import hashlib
import os

import httpx
from dotenv import load_dotenv

BASE_URL = "https://api.gridstatus.io/v1/api_usage"
N_ACCOUNTS = 6


def main() -> int:
    load_dotenv()
    seen: dict[str, list[str]] = {}
    for i in range(1, N_ACCOUNTS + 1):
        name = f"GRIDSTATUS_API_KEY_{i}"
        key = os.getenv(name)
        if not key:
            print(f"{name}: MISSING")
            continue
        fp = hashlib.sha256(key.encode()).hexdigest()[:8]
        seen.setdefault(fp, []).append(name)
        r = httpx.get(BASE_URL, params={"api_key": key}, timeout=30)
        if r.status_code != 200:
            print(f"{name} (fp={fp}): HTTP {r.status_code} {r.text[:200]}")
            continue
        d = r.json()
        used = d["current_period_usage"]
        lim = d["limits"]
        print(
            f"{name} (fp={fp}): {used['total_requests']}/{lim['api_requests_limit']} req, "
            f"{used['total_api_rows_returned']}/{lim['api_rows_returned_limit']} rows, "
            f"period ends {d['current_usage_period_end']}"
        )
    dupes = {fp: n for fp, n in seen.items() if len(n) > 1}
    if dupes:
        print(f"\nWARNING: duplicate keys — the account-per-pnode plan is invalid: {dupes}")
    else:
        print(f"\n{len(seen)} distinct accounts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
