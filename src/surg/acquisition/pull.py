"""Orchestrator: pull a feed for a date range, writing per-chunk parquet files.

Composes `client.PJMClient` + `chunking.date_chunks` + `storage.*`.
Two feed shapes are supported:
  - Nodal LMP feeds (rt_hrl_lmps, rt_fivemin_hrl_lmps, da_hrl_lmps):
    pass `pnode_ids` (semicolon-packed). `row_is_current=true` is forced.
  - Zonal feeds (hrl_load_metered): pass `zone="DOM"` instead.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from surg.acquisition.chunking import date_chunks
from surg.acquisition.client import PJMClient
from surg.acquisition.storage import chunk_exists, write_chunk
from surg.acquisition.targets import all_pnode_ids

# Feeds that follow LMP versioning semantics.
_LMP_FEEDS = frozenset(
    {"rt_hrl_lmps", "rt_fivemin_hrl_lmps", "da_hrl_lmps"}
)


def pull_feed(
    feed: str,
    start: date,
    end: date,
    *,
    pnode_ids: Sequence[int] | None,
    group_label: str,
    client: PJMClient,
    data_root: Path,
    zone: str | None = None,
    force: bool = False,
    max_days_per_chunk: int = 366,
) -> list[Path]:
    """Pull `feed` for [start, end] in calendar-year chunks.

    Returns the list of parquet paths written this run (skipped chunks
    are excluded from the return value).
    """
    if (pnode_ids is None) == (zone is None):
        raise ValueError(
            "pull_feed requires exactly one of pnode_ids or zone, not both/neither"
        )

    written: list[Path] = []

    for chunk_start, chunk_end in date_chunks(start, end, max_days=max_days_per_chunk):
        if not force and chunk_exists(data_root, feed, group_label, chunk_start, chunk_end):
            continue

        params = _build_params(feed, chunk_start, chunk_end, pnode_ids, zone)
        rows = list(client.get_feed(feed, params))
        df = pd.DataFrame(rows)
        path = write_chunk(
            data_root=data_root,
            feed=feed,
            group_label=group_label,
            chunk_start=chunk_start,
            chunk_end=chunk_end,
            df=df,
        )
        written.append(path)

    return written


def _build_params(
    feed: str,
    chunk_start: date,
    chunk_end: date,
    pnode_ids: Sequence[int] | None,
    zone: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "datetime_beginning_ept": (
            f"{chunk_start.isoformat()} 00:00 to "
            f"{chunk_end.isoformat()} 23:59"
        ),
        "sort": "datetime_beginning_ept",
        "order": "Asc",
    }
    if pnode_ids:
        params["pnode_id"] = ";".join(str(p) for p in pnode_ids)
    if zone:
        params["zone"] = zone
    if feed in _LMP_FEEDS:
        params["row_is_current"] = "true"
    return params


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_iso_date(s: str) -> date:
    return date.fromisoformat(s)


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="surg-pull",
        description="Pull a PJM Data Miner 2 feed for a date range to data/raw/.",
    )
    p.add_argument("--feed", required=True,
                   choices=sorted(_LMP_FEEDS | {"hrl_load_metered"}),
                   help="API feed name.")
    p.add_argument("--start", required=True, type=_parse_iso_date,
                   help="Inclusive start date (YYYY-MM-DD).")
    p.add_argument("--end",   required=True, type=_parse_iso_date,
                   help="Inclusive end date (YYYY-MM-DD).")
    p.add_argument("--group-label", default="dom_targets",
                   help="Slug used in output filenames.")
    p.add_argument("--data-root", default="data/raw",
                   help="Root directory under which feed/year subdirs are created.")
    p.add_argument("--zone", default=None,
                   help="For zonal feeds (e.g. hrl_load_metered). Mutually "
                        "exclusive with the implicit pnode set.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing chunk files.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)

    if args.feed in _LMP_FEEDS and args.zone is not None:
        print(f"--zone is not valid for LMP feed '{args.feed}'", file=sys.stderr)
        return 2
    if args.feed == "hrl_load_metered" and args.zone is None:
        print("--zone is required for feed 'hrl_load_metered'", file=sys.stderr)
        return 2

    load_dotenv()
    api_key = os.environ.get("PJM_API_KEY")
    if not api_key:
        print("PJM_API_KEY is not set. Add it to .env or export it.", file=sys.stderr)
        return 2

    pnode_ids = None if args.zone else all_pnode_ids()

    with PJMClient(api_key=api_key) as client:
        paths = pull_feed(
            feed=args.feed,
            start=args.start,
            end=args.end,
            pnode_ids=pnode_ids,
            zone=args.zone,
            group_label=args.group_label,
            client=client,
            data_root=Path(args.data_root),
            force=args.force,
        )

    if not paths:
        print("No chunks pulled (all already exist; use --force to overwrite).")
    else:
        for p in paths:
            print(f"wrote {p}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
