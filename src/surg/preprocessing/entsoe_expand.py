"""Expand ENTSO-E A03 variable-block curves to dense arrays.

curveType A03 emits a position only where the value CHANGES; the value then
holds until the next emitted position. A flat series is one point, not N.
Parsed naively -- one row per <Point> -- a flat stretch vanishes and every
gradient computed downstream reads spikier than reality. Since this project's
volatility measure is mean |delta load| per minute, that would corrupt the one
number the work exists to produce.

Confirmed live in real responses (docs/plans/2026-08-12-entsoe-ireland-design.md
section 1.4): NL load 2015-01-08 emitted 95 of 96 positions; IE price
2018-03-10 emitted 32 of 46.

This module is pure and TIMEZONE-FREE. Expansion happens on the UTC span
declared by the document; DST is handled at localization, not here.
"""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

_RESOLUTIONS = {"PT15M": 15, "PT30M": 30, "PT60M": 60}


def resolution_minutes(resolution: str) -> int:
    """Map an ENTSO-E resolution token to minutes."""
    try:
        return _RESOLUTIONS[resolution]
    except KeyError:
        raise ValueError(
            f"unsupported resolution {resolution!r}; expected one of "
            f"{sorted(_RESOLUTIONS)}"
        ) from None


def expand_curve(
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
    resolution: str,
    curve_type: str,
    points: Sequence[tuple[int, float]],
) -> tuple[np.ndarray, float]:
    """Expand sparse (position, value) pairs to a dense array.

    Returns (dense, sparsity) where sparsity = n_emitted / N. A sparsity below
    1.0 is normal for A03 and is recorded so it stays a measured quantity
    rather than an invisible one.

    Raises rather than guessing on every malformed input -- a wrong dense
    length is silent corruption, so there is no permissive path.
    """
    step = resolution_minutes(resolution)
    span_minutes = (end - start).total_seconds() / 60.0
    if span_minutes % step != 0:
        raise ValueError(
            f"span {span_minutes} min does not divide evenly into {resolution}"
        )
    n = int(span_minutes // step)
    if n <= 0:
        raise ValueError(f"non-positive dense length {n} for {start}..{end}")

    if not points:
        raise ValueError(f"no points supplied for {start}..{end}")

    ordered = sorted(points, key=lambda pv: pv[0])
    positions = [p for p, _ in ordered]

    if positions[0] != 1:
        raise ValueError(
            f"position 1 absent (first emitted is {positions[0]}); "
            "no opening value to fill from"
        )
    if positions[-1] > n:
        raise ValueError(f"position {positions[-1]} exceeds dense length {n}")

    if len(set(positions)) != len(positions):
        raise ValueError(
            f"duplicate positions in document: {sorted(positions)}; "
            "a position may be emitted at most once"
        )

    if curve_type == "A01" and len(ordered) != n:
        raise ValueError(
            f"A01 document is not dense: {len(ordered)} points for length {n}"
        )

    dense = np.full(n, np.nan, dtype=float)
    for i, (pos, value) in enumerate(ordered):
        stop = ordered[i + 1][0] - 1 if i + 1 < len(ordered) else n
        dense[pos - 1 : stop] = value

    return dense, len(ordered) / n
