"""Orchestrator: pull a feed for a date range, writing per-chunk parquet files.

Composes `client.PJMClient` + `chunking.date_chunks` + `storage.*`.
Four feed shapes are supported:
  - Nodal LMP feeds (rt_hrl_lmps, rt_fivemin_hrl_lmps, da_hrl_lmps):
    pass `pnode_ids` (semicolon-packed). `row_is_current=true` is forced.
  - Zonal load feeds (hrl_load_metered): pass `zone="DOM"` instead.
  - Sub-zone reserve events (sync_reserve_events): pass `subzone="MidAtlantic-Dominion (MAD)"`.
  - Locale-based reserve results (reserve_market_results): pass `locale="MAD"`.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

from surg.acquisition.chunking import date_chunks
from surg.acquisition.client import PJMClient
from surg.acquisition.storage import chunk_exists, write_chunk
from surg.acquisition.targets import all_pnode_ids, pnode_ids_by_subtype


@dataclass(frozen=True, slots=True)
class FeedSpec:
    """Per-feed metadata for API parameter construction.

    - date_field: column name used for range filter and sort
    - geo_filter_key: name of the geographic filter param (None means
      the feed has no geographic dimension; we don't currently support
      such feeds, but the field is here for future-proofing)
    - is_lmp: True for LMP feeds (adds row_is_current=true to params)
    - supports_archive: True if the feed has a documented archive cutoff
      and Historic-tier queries with `type=<pnode_subtype>` work
    """
    date_field: str
    geo_filter_key: str | None
    is_lmp: bool
    supports_archive: bool = False


_FEED_SPECS: dict[str, FeedSpec] = {
    "rt_hrl_lmps":            FeedSpec("datetime_beginning_ept", "pnode_id", True, supports_archive=True),
    "da_hrl_lmps":            FeedSpec("datetime_beginning_ept", "pnode_id", True, supports_archive=True),
    "rt_fivemin_hrl_lmps":    FeedSpec("datetime_beginning_ept", "pnode_id", True, supports_archive=True),  # CLI rejects archive mode for this feed (type filter rejected on Historic); see pjm-api-constraints.md
    "hrl_load_metered":       FeedSpec("datetime_beginning_ept", "zone", False),
    "sync_reserve_events":    FeedSpec("event_start_ept", "synchronized_sub_zone", False),
    "reserve_market_results": FeedSpec("datetime_beginning_ept", "locale", False),
}



def pull_feed(
    feed: str,
    start: date,
    end: date,
    *,
    pnode_ids: Sequence[int] | None = None,
    zone: str | None = None,
    subzone: str | None = None,
    locale: str | None = None,
    archive_mode: bool = False,
    archive_subtype: str | None = None,
    target_pnode_ids: Sequence[int] | None = None,
    group_label: str,
    client: PJMClient,
    data_root: Path,
    force: bool = False,
    max_days_per_chunk: int = 366,
) -> list[Path]:
    """Pull `feed` for [start, end] in calendar-year chunks.

    Standard mode (archive_mode=False, default): exactly one of
    (pnode_ids, zone, subzone, locale) must be truthy, matching the
    feed's FeedSpec.geo_filter_key.

    Archive mode (archive_mode=True, LMP feeds only): drops the
    pnode_id filter and adds type=<archive_subtype>. After fetch,
    filters rows client-side to `target_pnode_ids` to keep only the
    locked target pnodes (Historic returns all pnodes of that subtype).
    """
    if feed not in _FEED_SPECS:
        raise ValueError(f"unknown feed: {feed!r}")
    spec = _FEED_SPECS[feed]

    if archive_mode:
        # Order: reject standard geo kwargs → require target_pnode_ids → check feed support.
        for name, val in [("pnode_ids", pnode_ids), ("zone", zone),
                          ("subzone", subzone), ("locale", locale)]:
            if val:
                raise ValueError(
                    f"archive_mode=True is incompatible with {name}=...; "
                    f"use target_pnode_ids for client-side filtering"
                )
        if not target_pnode_ids:
            raise ValueError(
                "archive_mode=True requires target_pnode_ids "
                "(client-side filter for the locked target set)"
            )
        if not spec.supports_archive:
            raise ValueError(
                f"feed {feed!r} does not support archive-tier queries"
            )
        target_set = set(target_pnode_ids)

        written: list[Path] = []
        for chunk_start, chunk_end in date_chunks(start, end, max_days=max_days_per_chunk):
            if not force and chunk_exists(data_root, feed, group_label, chunk_start, chunk_end):
                continue
            params = _build_params(
                feed, chunk_start, chunk_end, geo_value=None,
                archive_mode=True, archive_subtype=archive_subtype,
            )
            rows = list(client.get_feed(feed, params))
            df = pd.DataFrame(rows)
            if not df.empty and "pnode_id" in df.columns:
                df = df[df["pnode_id"].isin(target_set)].reset_index(drop=True)
            path = write_chunk(
                data_root=data_root, feed=feed, group_label=group_label,
                chunk_start=chunk_start, chunk_end=chunk_end, df=df,
            )
            written.append(path)
        return written

    # Map kwarg names → values; resolve which one this feed expects.
    kwarg_by_filter_key = {
        "pnode_id": pnode_ids,
        "zone": zone,
        "synchronized_sub_zone": subzone,
        "locale": locale,
    }
    if spec.geo_filter_key is None:
        # No feeds currently have geo_filter_key=None; reserved for future.
        geo_value = None
    else:
        geo_value = kwarg_by_filter_key.get(spec.geo_filter_key)
        if not geo_value:
            raise ValueError(
                f"feed {feed!r} requires a value for "
                f"{_friendly_kwarg_name(spec.geo_filter_key)}"
            )
        # Ensure no *other* geographic kwarg is set.
        for other_key, other_val in kwarg_by_filter_key.items():
            if other_key != spec.geo_filter_key and other_val:
                raise ValueError(
                    f"feed {feed!r} uses {_friendly_kwarg_name(spec.geo_filter_key)} "
                    f"only; got {_friendly_kwarg_name(other_key)}={other_val!r}"
                )

    written: list[Path] = []
    for chunk_start, chunk_end in date_chunks(start, end, max_days=max_days_per_chunk):
        if not force and chunk_exists(data_root, feed, group_label, chunk_start, chunk_end):
            continue
        params = _build_params(feed, chunk_start, chunk_end, geo_value)
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
    geo_value: Sequence[int] | str | None,
    *,
    archive_mode: bool = False,
    archive_subtype: str | None = None,
) -> dict[str, Any]:
    spec = _FEED_SPECS[feed]
    date_range = (
        f"{chunk_start.isoformat()} 00:00 to "
        f"{chunk_end.isoformat()} 23:59"
    )

    if archive_mode:
        if not spec.supports_archive:
            raise ValueError(
                f"feed {feed!r} does not support archive-tier queries"
            )
        if not archive_subtype:
            raise ValueError(
                f"archive_subtype is required for archive-mode pulls "
                f"(feed={feed!r})"
            )
        # Historic queries: no pnode_id filter, no sort/order, type filter only.
        params: dict[str, Any] = {
            spec.date_field: date_range,
            "type": archive_subtype,
        }
        if spec.is_lmp:
            params["row_is_current"] = "true"
        return params

    # Standard-tier path (unchanged from existing implementation).
    params: dict[str, Any] = {
        spec.date_field: date_range,
        "sort": spec.date_field,
        "order": "Asc",
    }
    if spec.geo_filter_key is not None and geo_value is not None:
        if isinstance(geo_value, (list, tuple)):
            params[spec.geo_filter_key] = ";".join(str(p) for p in geo_value)
        else:
            params[spec.geo_filter_key] = geo_value
    if spec.is_lmp:
        params["row_is_current"] = "true"
    return params


def _friendly_kwarg_name(filter_key: str) -> str:
    """Map API filter param → Python kwarg name for error messages."""
    return {
        "pnode_id": "pnode_ids",
        "zone": "zone",
        "synchronized_sub_zone": "subzone",
        "locale": "locale",
    }.get(filter_key, filter_key)


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
                   choices=sorted(_FEED_SPECS.keys()),
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
                   help="For zonal feeds (e.g. hrl_load_metered).")
    p.add_argument("--subzone", default=None,
                   help="For sub-zone feeds (e.g. sync_reserve_events). "
                        "Allowed values include 'MidAtlantic-Dominion (MAD)'.")
    p.add_argument("--locale", default=None,
                   help="For locale-filtered feeds (e.g. reserve_market_results). "
                        "Allowed values include 'MAD', 'PJM_RTO'.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing chunk files.")
    p.add_argument("--archive-tier", action="store_true",
                   help="Use Historic-tier query semantics (drops pnode_id, "
                        "adds type=<archive-subtype>; for LMP feeds with "
                        "data older than the archive cutoff).")
    p.add_argument("--archive-subtype",
                   help="pnode_subtype value for archive queries "
                        "(AGGREGATE / EHV / EXT / GEN / HUB / INTERFACE / "
                        "LOAD / RESIDUAL_METERED_EDC / TIE / ZONE).")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    spec = _FEED_SPECS[args.feed]

    target_pnode_ids: list[int] | None = None

    if args.archive_tier:
        # Validation order matters: subtype-required → feed-level support →
        # 5-min special-case → geo kwargs → target resolution. The 5-min test
        # passes no --zone, so it must trip the 5-min branch before any geo check.
        if not args.archive_subtype:
            print("--archive-subtype is required when --archive-tier is set",
                  file=sys.stderr)
            return 2
        if not spec.supports_archive:
            print(f"feed '{args.feed}' does not support archive-tier queries",
                  file=sys.stderr)
            return 2
        if args.feed == "rt_fivemin_hrl_lmps":
            print("rt_fivemin_hrl_lmps Historic tier rejects the type filter "
                  "(see docs/pjm-api-constraints.md); archive-tier pull is "
                  "not workable for this feed.", file=sys.stderr)
            return 2
        # Standard geo kwargs should be unset.
        for name, val in [("zone", args.zone), ("subzone", args.subzone),
                          ("locale", args.locale)]:
            if val:
                print(f"--{name} is not valid with --archive-tier "
                      f"(archive uses --archive-subtype + client-side "
                      f"filter to locked target set)", file=sys.stderr)
                return 2
        target_pnode_ids = pnode_ids_by_subtype(args.archive_subtype)
        if not target_pnode_ids:
            print(f"No target pnodes have subtype={args.archive_subtype!r}; "
                  f"check src/surg/acquisition/targets.py", file=sys.stderr)
            return 2
    else:
        expected_kwarg = _friendly_kwarg_name(spec.geo_filter_key)

        # Per-feed CLI-arg validation. Each feed expects exactly one geographic arg.
        provided = {
            "zone": args.zone,
            "subzone": args.subzone,
            "locale": args.locale,
        }
        for arg_name, value in provided.items():
            if arg_name == expected_kwarg:
                if value is None:
                    print(f"--{arg_name} is required for feed '{args.feed}'", file=sys.stderr)
                    return 2
            elif value is not None:
                cli_args = {"zone", "subzone", "locale"}
                if expected_kwarg in cli_args:
                    hint = f"(this feed uses --{expected_kwarg})"
                else:
                    hint = "(this feed selects pnode targets automatically; no geographic arg is accepted)"
                print(f"--{arg_name} is not valid for feed '{args.feed}' {hint}",
                      file=sys.stderr)
                return 2
        # For LMP feeds (geo_filter_key='pnode_id'), expected_kwarg='pnode_ids' which
        # is not a CLI arg — we use all_pnode_ids() automatically. Validation above
        # would have ensured zone/subzone/locale are all None.

    load_dotenv()
    api_key = os.environ.get("PJM_API_KEY")
    if not api_key:
        print("PJM_API_KEY is not set. Add it to .env or export it.", file=sys.stderr)
        return 2

    with PJMClient(api_key=api_key) as client:
        if args.archive_tier:
            paths = pull_feed(
                feed=args.feed,
                start=args.start,
                end=args.end,
                archive_mode=True,
                archive_subtype=args.archive_subtype,
                target_pnode_ids=target_pnode_ids,
                group_label=args.group_label,
                client=client,
                data_root=Path(args.data_root),
                force=args.force,
            )
        else:
            # Resolve geographic kwargs to pass to pull_feed.
            pnode_ids = all_pnode_ids() if spec.geo_filter_key == "pnode_id" else None
            paths = pull_feed(
                feed=args.feed,
                start=args.start,
                end=args.end,
                pnode_ids=pnode_ids,
                zone=args.zone,
                subzone=args.subzone,
                locale=args.locale,
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
