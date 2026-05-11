"""Pure-function helpers for splitting work into API-compatible chunks.

Two constraints from PJM Data Miner 2 (see `docs/pjm-api-constraints.md`):
  - A single date-filtered query may not span more than 366 days.
  - For archived feeds, a query must stay within a single calendar year.

`date_chunks` enforces both: chunks are always within one calendar year
and never longer than `max_days`.

`pnode_batches` packs pnode IDs for semicolon-joined `pnode_id=A;B;C`
queries — the major efficiency under the 6/min rate limit.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import date, timedelta


def date_chunks(
    start: date,
    end: date,
    max_days: int = 365,
) -> Iterator[tuple[date, date]]:
    """Yield (chunk_start, chunk_end) inclusive windows.

    Windows never cross a calendar year boundary and never exceed
    `max_days` days inclusive.

    `max_days` defaults to 365 (one day under PJM's 366-day range cap)
    to leave margin for edge cases. Pass `max_days=366` to use the
    full cap — required when pulling a full leap year as a single chunk.
    """
    if end < start:
        raise ValueError(f"end ({end}) must be >= start ({start})")
    if max_days < 1:
        raise ValueError(f"max_days must be >= 1, got {max_days}")

    cur = start
    while cur <= end:
        year_end = date(cur.year, 12, 31)
        max_end = cur + timedelta(days=max_days - 1)
        chunk_end = min(year_end, max_end, end)
        yield (cur, chunk_end)
        cur = chunk_end + timedelta(days=1)


def pnode_batches(
    pnode_ids: Sequence[int],
    batch_size: int = 50,
) -> Iterator[list[int]]:
    """Yield successive batches of pnode IDs of length up to `batch_size`.

    NOTE: Currently unused by the orchestrator (Task 5 packs all 11 locked
    pnodes into a single `pnode_id=A;B;C;...` query, which fits comfortably
    in one URL). Retained for the case where the target set grows past
    `batch_size` and per-call packing becomes necessary.
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1, got {batch_size}")
    for i in range(0, len(pnode_ids), batch_size):
        yield list(pnode_ids[i : i + batch_size])
