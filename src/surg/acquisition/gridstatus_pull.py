"""Orchestrator: pull the 5-min two-sided panel inputs from gridstatus.io.

Design: docs/specs/2026-07-17-5min-two-sided-companion-design.md
Datasets and constraints: docs/sources/gridstatus-api-constraints.md
Pull plan: docs/gridstatus-5min-pull-plan.md

Chunks are half-open UTC windows cached via storage.write_chunk (30-day for
the load series, 7-day for the location_id-filtered LMP series — see
LMP_CHUNK_DAYS):
    <data_root>/pjm_load/<year>/dom__<start>_to_<end>.parquet
    <data_root>/pjm_lmp_real_time_5_min/<year>/<pnode_id>__<start>_to_<end>.parquet
Skip-if-exists gives resumability; a partial run never re-spends quota
on chunks already on disk.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from surg.acquisition.chunking import utc_datetime_chunks
from surg.acquisition.gridstatus_client import GridStatusClient
from surg.acquisition.storage import chunk_exists, write_chunk

# Free-tier pnode set (design §2; pull plan table). Single definition lives in
# the schema module so the pull-set and the panel schema cannot drift apart.
from surg.preprocessing.schema_5min import FIVEMIN_PNODE_IDS

# The location_id-filtered LMP query hits a ~180s server-side query budget at
# 30-day chunk width (empirically observed 2026-07-18: a 30-day chunk returns
# 422 at exactly ~180s regardless of client timeout, while a 7-day chunk for
# the same pnode/filter succeeds in ~114s — docs/sources/gridstatus-api-constraints.md).
# The unfiltered load series has no such ceiling and keeps the 30-day default.
LMP_CHUNK_DAYS = 7

LOAD_DATASET = "pjm_load"
LMP_DATASET = "pjm_lmp_real_time_5_min"
LOAD_COLUMNS = "interval_start_utc,interval_end_utc,dom"
LMP_COLUMNS = (
    "interval_start_utc,interval_end_utc,location,location_id,"
    "location_short_name,location_type,lmp,energy,congestion,loss"
)


def check_quota(
    client,
    *,
    min_remaining_rows: int = 430_000,
    min_remaining_requests: int = 150,
) -> dict:
    """Abort (RuntimeError) if the remaining monthly row or request quota is too low.

    The Free tier caps both `api_rows_returned_limit` (rows/mo) and
    `api_requests_limit` (requests/mo) independently; either one can bind
    (docs/sources/gridstatus-api-constraints.md calls the request budget "the
    binding free-tier constraint" as a general rule, even though for this
    3-pnode/1-year pull the row cap binds first by a comfortable margin).
    """
    usage = client.get_api_usage()
    limit_rows = usage["limits"]["api_rows_returned_limit"]
    used_rows = usage["current_period_usage"]["total_api_rows_returned"]
    remaining_rows = limit_rows - used_rows
    if remaining_rows < min_remaining_rows:
        raise RuntimeError(
            f"insufficient gridstatus quota (rows): {remaining_rows:,} remaining "
            f"< {min_remaining_rows:,} required (plan={usage.get('plan_name')})"
        )

    limit_requests = usage["limits"]["api_requests_limit"]
    used_requests = usage["current_period_usage"]["total_requests"]
    remaining_requests = limit_requests - used_requests
    if remaining_requests < min_remaining_requests:
        raise RuntimeError(
            f"insufficient gridstatus quota (requests): {remaining_requests:,} remaining "
            f"< {min_remaining_requests:,} required (plan={usage.get('plan_name')})"
        )

    return usage


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pull_series(
    client,
    data_root: Path,
    *,
    dataset: str,
    group_label: str,
    columns: str,
    window_start: datetime,
    window_end: datetime,
    filter_column: str | None = None,
    filter_value: str | None = None,
    chunk_days: int = 30,
) -> int:
    """Pull one series in `chunk_days`-day chunks; returns number fetched."""
    fetched = 0
    for cs, ce in utc_datetime_chunks(window_start, window_end, days=chunk_days):
        if chunk_exists(data_root, dataset, group_label, cs.date(), ce.date()):
            continue
        rows = list(client.query(
            dataset,
            start_time=_iso_z(cs), end_time=_iso_z(ce),
            columns=columns,
            filter_column=filter_column, filter_value=filter_value,
        ))
        df = pd.DataFrame(rows, columns=columns.split(","))
        write_chunk(data_root, dataset, group_label, cs.date(), ce.date(), df)
        fetched += 1
        print(f"  wrote {dataset}/{group_label} {cs.date()} -> {ce.date()} ({len(df):,} rows)")
    return fetched


def pull_gridstatus(
    client,
    *,
    data_root: Path,
    window_start: datetime,
    window_end: datetime,
    pnode_ids: tuple[int, ...] | None = None,
    skip_load: bool = False,
    skip_lmp: bool = False,
) -> None:
    """Pull DOM 5-min load once + 5-min LMP per pnode for the window.

    `pnode_ids`, `skip_load` and `skip_lmp` support splitting a pull across
    multiple gridstatus.io accounts by pnode (docs/gridstatus-5min-pull-plan.md
    § "Backfill Pull") — default behavior (all pnodes, load included) is
    unchanged. `skip_lmp` is the inverse of `skip_load`: it serves the
    dedicated load account, which cannot also carry a pnode within the
    free-tier row cap.
    """
    if skip_lmp and skip_load:
        raise ValueError(
            "skip_lmp and skip_load are both set — nothing to pull"
        )
    if not skip_load:
        _pull_series(
            client, data_root,
            dataset=LOAD_DATASET, group_label="dom", columns=LOAD_COLUMNS,
            window_start=window_start, window_end=window_end,
        )
    if not skip_lmp:
        for pid in (pnode_ids or FIVEMIN_PNODE_IDS):
            _pull_series(
                client, data_root,
                dataset=LMP_DATASET, group_label=str(pid), columns=LMP_COLUMNS,
                window_start=window_start, window_end=window_end,
                filter_column="location_id", filter_value=str(pid),
                chunk_days=LMP_CHUNK_DAYS,
            )


def _parse_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"window datetimes must be timezone-aware UTC, got {s!r}")
    return dt.astimezone(timezone.utc)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-gridstatus-pull",
        description="Pull the 5-min two-sided panel inputs from gridstatus.io.",
    )
    # No defaults on the window: the pre-registered window must be passed
    # explicitly (design §2 — the pre-reg records the final window first).
    p.add_argument("--start", required=True, help="Window start, ISO-8601 UTC (e.g. 2025-06-24T04:00:00Z)")
    p.add_argument("--end", required=True, help="Window end (exclusive), ISO-8601 UTC")
    p.add_argument("--data-root", default="data/raw/gridstatus")
    p.add_argument("--skip-preflight", action="store_true",
                   help="Skip the /api_usage quota check (resume of a mostly-done pull).")
    p.add_argument("--pnodes", default=None,
                   help="Comma-separated pnode IDs to pull (default: all of "
                        "FIVEMIN_PNODE_IDS). Use to split a pull by pnode across "
                        "multiple gridstatus.io accounts.")
    p.add_argument("--skip-load", action="store_true",
                   help="Skip the pjm_load pull (for a split-account pull that "
                        "only fetches LMP).")
    p.add_argument("--skip-lmp", action="store_true",
                   help="Pull only the load series, no nodal LMP. Used by the "
                        "dedicated load account, which cannot also carry a "
                        "pnode within the free-tier row cap.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    load_dotenv()
    api_key = os.environ.get("GRIDSTATUS_API_KEY")
    if not api_key:
        print("GRIDSTATUS_API_KEY is not set. Add it to .env or export it.", file=sys.stderr)
        return 2

    window_start = _parse_utc(args.start)
    window_end = _parse_utc(args.end)
    pnode_ids = (
        tuple(int(p) for p in args.pnodes.split(",")) if args.pnodes else None
    )

    with GridStatusClient(api_key) as client:
        if not args.skip_preflight:
            usage = check_quota(client)
            used = usage["current_period_usage"]["total_api_rows_returned"]
            print(f"preflight OK: plan={usage.get('plan_name')}, rows used this period={used:,}")
        pull_gridstatus(
            client, data_root=Path(args.data_root),
            window_start=window_start, window_end=window_end,
            pnode_ids=pnode_ids, skip_load=args.skip_load,
            skip_lmp=args.skip_lmp,
        )
    print("pull complete")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
