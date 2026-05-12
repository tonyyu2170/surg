"""Empirical verification before launching Plan 1.5.

Checks:
1. Earliest available row for sync_reserve_events (MAD sub-zone).
2. Earliest available row for reserve_market_results (MAD locale, SR service).
3. Historic-tier access on rt_hrl_lmps with type=AGGREGATE — sample
   2023 calendar year, totalRows tells us pull volume per year.
4. Historic-tier access on rt_hrl_lmps with type=BUS — sample 2023.

Reads PJM_API_KEY from environment (or .env file alongside this dir).
Prints a one-line summary per check.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Load .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from surg.acquisition.client import PJMClient  # noqa: E402


def first_row(client: PJMClient, feed: str, params: dict) -> tuple[int | None, dict | None]:
    """One paginated page, return (totalRows, first_row)."""
    q = {**params, "startRow": 1, "rowCount": 1}
    payload = client._get_with_retry(f"{client._base_url}/{feed}", q)
    total = payload.get("totalRows")
    items = payload.get("items", [])
    return total, items[0] if items else None


def main() -> None:
    key = os.environ.get("PJM_API_KEY")
    if not key:
        print("PJM_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    with PJMClient(api_key=key, min_interval_s=11.0) as client:
        # 1. sync_reserve_events: earliest MAD record
        print("--- sync_reserve_events (MAD) earliest record ---")
        total, row = first_row(
            client,
            "sync_reserve_events",
            {
                "sort": "event_start_ept",
                "order": "Asc",
                "synchronized_sub_zone": "MidAtlantic-Dominion (MAD)",
            },
        )
        print(f"  totalRows: {total}")
        print(f"  earliest:  {row.get('event_start_ept') if row else 'no row'}")

        # 2. reserve_market_results: earliest MAD SR record
        print("--- reserve_market_results (MAD, SR) earliest record ---")
        total, row = first_row(
            client,
            "reserve_market_results",
            {
                "sort": "datetime_beginning_ept",
                "order": "Asc",
                "locale": "MAD",
                "service": "SR",
            },
        )
        print(f"  totalRows: {total}")
        print(f"  earliest:  {row.get('datetime_beginning_ept') if row else 'no row'}")

        # 3-5. Historic rt_hrl_lmps volumes for the three subtypes
        # covering our 11 targets: EHV (8 pnodes), LOAD (Ashburn TX1/TX2),
        # ZONE (DOM zonal).
        for subtype, n_targets in [("EHV", 8), ("LOAD", 2), ("ZONE", 1)]:
            print(f"--- rt_hrl_lmps Historic type={subtype} 2023 (1-row probe) ---")
            total, row = first_row(
                client,
                "rt_hrl_lmps",
                {
                    "datetime_beginning_ept": "01-01-2023 00:00 to 12-31-2023 23:59",
                    "type": subtype,
                    "row_is_current": "true",
                },
            )
            total_str = f"{total:,}" if isinstance(total, int) else f"{total}"
            n_pnodes = total // 8760 if isinstance(total, int) and total else "n/a"
            print(f"  totalRows {subtype} 2023: {total_str}  (~{n_pnodes} pnodes)")
            print(f"  sample pnode: {row.get('pnode_id') if row else 'no row'} "
                  f"({row.get('pnode_name') if row else ''}) "
                  f"type={row.get('type') if row else ''}  "
                  f"(targets in this subtype: {n_targets})")


if __name__ == "__main__":
    main()
