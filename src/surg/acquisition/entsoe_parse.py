"""Parse ENTSO-E market documents into flat period records.

Three schema facts drive this module, all verified against real responses
captured 2026-08-12:

  1. Namespaces differ per document type -- GL_MarketDocument (load) uses
     ...451-6:generationloaddocument, Publication_MarketDocument (price) uses
     ...451-3:publicationdocument. So we strip namespaces and never match on
     them.
  2. The interval governing expansion is TimeSeries/Period/timeInterval, NOT
     the document-level time_Period.timeInterval. One TimeSeries may carry
     several Periods, and merging them would corrupt the dense span.
  3. The value element differs: <quantity> for load, <price.amount> for price.

"No data" arrives as HTTP 200 carrying an Acknowledgement_MarketDocument with
reason code 999. Status code alone cannot distinguish data from emptiness --
every body must be parsed.

A Point that carries no parseable position and value RAISES rather than being
skipped. A silently dropped point is invisible downstream: for A03 the missing
slot is forward-filled and the resulting sparsity is indistinguishable from
legitimate compression, which would corrupt mean |delta load| per minute.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

_VALUE_TAGS = ("quantity", "price.amount")


def _tag(element: ET.Element) -> str:
    """Local tag name with any namespace stripped."""
    return element.tag.split("}")[-1]


def _find_text(parent: ET.Element, name: str) -> str | None:
    for child in parent.iter():
        if _tag(child) == name:
            return child.text
    return None


@dataclass
class ParseResult:
    """Outcome of parsing one response body."""

    kind: str  # "data" | "no_data"
    periods: list[dict[str, Any]] = field(default_factory=list)
    reason_code: str | None = None
    reason_text: str | None = None


def parse_response(xml_text: str) -> ParseResult:
    """Parse a market document into period records.

    Each period record carries: doc_start, doc_end, resolution, curve_type,
    and points as a list of (position, value) tuples.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"could not parse response body as XML: {exc}") from exc

    if _tag(root) == "Acknowledgement_MarketDocument":
        return ParseResult(
            kind="no_data",
            reason_code=_find_text(root, "code"),
            reason_text=_find_text(root, "text"),
        )

    periods: list[dict[str, Any]] = []
    for series in root.iter():
        if _tag(series) != "TimeSeries":
            continue
        curve_type = _find_text(series, "curveType")
        for period in series.iter():
            if _tag(period) != "Period":
                continue
            start = end = resolution = None
            points: list[tuple[int, float]] = []
            for node in period:
                name = _tag(node)
                if name == "timeInterval":
                    for bound in node:
                        if _tag(bound) == "start":
                            start = bound.text
                        elif _tag(bound) == "end":
                            end = bound.text
                elif name == "resolution":
                    resolution = node.text
                elif name == "Point":
                    position = value = None
                    for field_node in node:
                        fname = _tag(field_node)
                        if fname == "position" and field_node.text is not None:
                            position = int(field_node.text)
                        elif fname in _VALUE_TAGS and field_node.text is not None:
                            value = float(field_node.text)
                    if position is None or value is None:
                        raise ValueError(
                            f"Point missing position or value in period "
                            f"{start}..{end}: position={position}, value={value}"
                        )
                    points.append((position, value))
            periods.append(
                {
                    "doc_start": start,
                    "doc_end": end,
                    "resolution": resolution,
                    "curve_type": curve_type,
                    "points": points,
                }
            )

    return ParseResult(kind="data", periods=periods)
