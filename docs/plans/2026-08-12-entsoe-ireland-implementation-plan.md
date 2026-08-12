# ENTSO-E Ireland Load-Shape Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **⚠ PROJECT RULE OVERRIDE — READ BEFORE ANY `git commit`.** `CLAUDE.md`
> forbids committing or pushing without explicit permission **for that specific
> action**. Approval for one commit does not carry to the next. Every `Step:
> Commit` below therefore means **stage the files, then ASK**. Never run
> `git commit` unprompted. No AI attribution in any commit message. Stage
> explicit paths — never `git add .`.

**Goal:** Determine whether the shape of Irish national load changed as data
centres grew to 23.2% of metered electricity (2015→2025), using the Netherlands
as a matched control, from ENTSO-E Transparency Platform data.

**Architecture:** Four layers, each handing files to the next, matching the
existing repo pattern (acquisition → preprocessing → analysis, parquet on disk,
never objects in memory). A pure XML parser and a pure A03 curve expander are
built first and tested in isolation, because every downstream number depends on
their correctness. The fetcher writes *parsed but unexpanded* rows so expansion
can be re-run without re-pulling. Two panels are derived from one source:
native-resolution (NL 15-min, IE 30-min) and hourly.

**Tech Stack:** Python 3.11+, `httpx`, `pandas`, `pyarrow`, `numpy`,
`matplotlib`, `pytest`. No new dependencies. `entsoe-py` is deliberately **not**
used — see design §3.1.

**Design doc:** `docs/plans/2026-08-12-entsoe-ireland-design.md` — read §1
(probe findings) before starting. This plan implements that spec.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/surg/acquisition/entsoe_parse.py` | **Create.** XML → typed result: data rows, or ACK with reason code. Namespace-agnostic. Pure, no I/O. |
| `src/surg/preprocessing/entsoe_expand.py` | **Create.** Sparse A03 positions → dense array + sparsity ratio. Pure, no I/O, timezone-free. |
| `src/surg/preprocessing/entsoe_panel.py` | **Create.** Raw parquet → native and hourly panels, localized, with `dst_transition_hour`. |
| `src/surg/preprocessing/entsoe_zones.py` | **Create.** Zone registry: key → EIC, timezone, which items it serves. Single source of truth. |
| `scripts/entsoe_fetch.py` | **Create.** Driver: paced, idempotent pull → `data/raw/entsoe/`, writes manifest. |
| `scripts/cso_fetch.py` | **Create.** CSO PxStat MEC02 → `data/raw/cso/mec02.parquet`. |
| `scripts/entsoe_ireland.py` | **Create.** Analysis A (shape stats vs dose) + B (diurnal decomposition). |
| `scripts/entsoe_italy_stage1.py` | **Create.** Thin driver into `surg.diagnostics.stage1`, mirroring `scripts/isone_diagnostic.py`. |
| `tests/acquisition/test_entsoe_parse.py` | **Create.** Parser tests, fixtures from real captured responses. |
| `tests/preprocessing/test_entsoe_expand.py` | **Create.** Expander tests — the correctness-critical suite. |
| `tests/preprocessing/test_entsoe_panel.py` | **Create.** Panel localization and DST tests. |
| `docs/research-notes/K-ireland-dc-shape.md` | **Create.** The deliverable note. |
| `docs/plans/2026-08-19-advisor-meeting-agenda.md` | **Modify.** Fill the empty "European energy markets" section. |
| `docs/decisions.md` | **Modify — APPEND ONLY.** New entry at end. Never edit an existing one. |

**Real response schema, captured 2026-08-12** (both document types, so the
parser can be written without guessing):

Load — `GL_MarketDocument`, ns `urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0`:
```xml
<TimeSeries>
  <mRID>1</mRID>
  <outBiddingZone_Domain.mRID codingScheme="A01">10YIE-1001A00010</outBiddingZone_Domain.mRID>
  <curveType>A03</curveType>
  <Period>
    <timeInterval><start>2024-01-08T00:00Z</start><end>2024-01-08T03:00Z</end></timeInterval>
    <resolution>PT30M</resolution>
    <Point><position>1</position><quantity>3635.66</quantity></Point>
    <Point><position>2</position><quantity>3575.42</quantity></Point>
  </Period>
</TimeSeries>
```

Price — `Publication_MarketDocument`, ns `urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3`:
```xml
<TimeSeries>
  <in_Domain.mRID codingScheme="A01">10YNL----------L</in_Domain.mRID>
  <curveType>A03</curveType>
  <Period>
    <timeInterval><start>2024-01-07T23:00Z</start><end>2024-01-08T23:00Z</end></timeInterval>
    <resolution>PT60M</resolution>
    <Point><position>1</position><price.amount>87.02</price.amount></Point>
  </Period>
</TimeSeries>
```

**Three schema facts that drive the parser design:**
1. **Namespaces differ per document type** → strip namespaces, never match on them.
2. **The interval that governs expansion is `TimeSeries/Period/timeInterval`**, *not* the document-level `time_Period.timeInterval`. One TimeSeries may hold several Periods.
3. **Value element differs**: `quantity` (load) vs `price.amount` (price).

---

## Task 1: A03 curve expander

The correctness-critical component. A03 emits a position only where the value
*changes*; a flat stretch collapses to one point. Parsed naively, every
downstream gradient reads spikier than reality — which would corrupt
`mean |Δload|/min`, the statistic this whole project rests on. Confirmed live in
real data (design §1.4).

**Files:**
- Create: `src/surg/preprocessing/entsoe_expand.py`
- Test: `tests/preprocessing/test_entsoe_expand.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/preprocessing/test_entsoe_expand.py`:

```python
import numpy as np
import pandas as pd
import pytest

from surg.preprocessing.entsoe_expand import expand_curve, resolution_minutes


def test_resolution_minutes_parses_the_three_observed_resolutions():
    assert resolution_minutes("PT15M") == 15
    assert resolution_minutes("PT30M") == 30
    assert resolution_minutes("PT60M") == 60


def test_resolution_minutes_rejects_unknown():
    with pytest.raises(ValueError, match="unsupported resolution"):
        resolution_minutes("PT7M")


def test_dense_series_expands_one_to_one():
    # 3 hours at PT60M, every position emitted.
    dense, sparsity = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T03:00Z"),
        resolution="PT60M",
        curve_type="A03",
        points=[(1, 10.0), (2, 20.0), (3, 30.0)],
    )
    assert np.array_equal(dense, np.array([10.0, 20.0, 30.0]))
    assert sparsity == 1.0


def test_flat_day_one_point_becomes_n_identical_values():
    # THE case that silently produces garbage gradients if mishandled.
    dense, sparsity = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-09T00:00Z"),
        resolution="PT60M",
        curve_type="A03",
        points=[(1, 500.0)],
    )
    assert len(dense) == 24
    assert np.all(dense == 500.0)
    assert sparsity == pytest.approx(1 / 24)


def test_gaps_forward_fill_until_the_next_emitted_position():
    # Positions 1,4,6 emitted over N=8: value holds until the next change.
    dense, _ = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T08:00Z"),
        resolution="PT60M",
        curve_type="A03",
        points=[(1, 1.0), (4, 2.0), (6, 3.0)],
    )
    assert np.array_equal(dense, np.array([1.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 3.0]))


def test_last_emitted_value_holds_to_the_end():
    dense, _ = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T04:00Z"),
        resolution="PT60M",
        curve_type="A03",
        points=[(1, 7.0)],
    )
    assert np.array_equal(dense, np.array([7.0, 7.0, 7.0, 7.0]))


def test_a01_passthrough_requires_every_position():
    dense, sparsity = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T02:00Z"),
        resolution="PT60M",
        curve_type="A01",
        points=[(1, 4.0), (2, 5.0)],
    )
    assert np.array_equal(dense, np.array([4.0, 5.0]))
    assert sparsity == 1.0


def test_a01_with_missing_position_raises():
    with pytest.raises(ValueError, match="A01 document is not dense"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T03:00Z"),
            resolution="PT60M",
            curve_type="A01",
            points=[(1, 4.0), (3, 5.0)],
        )


def test_non_integer_span_raises():
    # 90 minutes does not divide into PT60M.
    with pytest.raises(ValueError, match="does not divide"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T01:30Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[(1, 1.0)],
        )


def test_position_beyond_n_raises():
    with pytest.raises(ValueError, match="exceeds dense length"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T02:00Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[(1, 1.0), (5, 2.0)],
        )


def test_missing_position_one_raises():
    # No opening value to forward-fill from -- must not silently backfill.
    with pytest.raises(ValueError, match="position 1"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T03:00Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[(2, 1.0), (3, 2.0)],
        )


def test_empty_points_raises():
    with pytest.raises(ValueError, match="no points"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T03:00Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[],
        )


def test_dst_spring_forward_day_is_a_fixed_utc_span():
    # 2024-03-31 Europe/Dublin loses an hour locally, but the UTC span is
    # unchanged. Expansion is UTC-only; DST belongs to localization.
    dense, _ = expand_curve(
        start=pd.Timestamp("2024-03-31T00:00Z"),
        end=pd.Timestamp("2024-04-01T00:00Z"),
        resolution="PT30M",
        curve_type="A03",
        points=[(1, 100.0)],
    )
    assert len(dense) == 48


def test_real_captured_irish_response_shape():
    # Captured 2026-08-12: IE CTA, 2024-01-08T00:00Z..03:00Z, PT30M, 6 points.
    dense, sparsity = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T03:00Z"),
        resolution="PT30M",
        curve_type="A03",
        points=[
            (1, 3635.66), (2, 3575.42), (3, 3469.86),
            (4, 3396.14), (5, 3336.9), (6, 3345.52),
        ],
    )
    assert len(dense) == 6
    assert dense[0] == 3635.66
    assert dense[-1] == 3345.52
    assert sparsity == 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/preprocessing/test_entsoe_expand.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.preprocessing.entsoe_expand'`

- [ ] **Step 3: Write the implementation**

Create `src/surg/preprocessing/entsoe_expand.py`:

```python
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

    if curve_type == "A01" and len(ordered) != n:
        raise ValueError(
            f"A01 document is not dense: {len(ordered)} points for length {n}"
        )

    dense = np.empty(n, dtype=float)
    for i, (pos, value) in enumerate(ordered):
        stop = ordered[i + 1][0] - 1 if i + 1 < len(ordered) else n
        dense[pos - 1 : stop] = value

    return dense, len(ordered) / n
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/preprocessing/test_entsoe_expand.py -v`
Expected: PASS, 13 passed

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check src/surg/preprocessing/entsoe_expand.py tests/preprocessing/test_entsoe_expand.py`
Expected: `All checks passed!`

- [ ] **Step 6: Stage, then ASK before committing**

```bash
git add src/surg/preprocessing/entsoe_expand.py tests/preprocessing/test_entsoe_expand.py
```
Then ask the user for permission to commit, proposing the message:
`feat(entsoe): A03 variable-block curve expander`

---

## Task 2: XML response parser

**Files:**
- Create: `src/surg/acquisition/entsoe_parse.py`
- Test: `tests/acquisition/test_entsoe_parse.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/acquisition/test_entsoe_parse.py`:

```python
import pytest

from surg.acquisition.entsoe_parse import parse_response

LOAD_XML = """<?xml version="1.0" encoding="utf-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
  <mRID>a8a2c94ba7d64c70b081e99e40a9a750</mRID>
  <type>A65</type>
  <TimeSeries>
    <mRID>1</mRID>
    <outBiddingZone_Domain.mRID codingScheme="A01">10YIE-1001A00010</outBiddingZone_Domain.mRID>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2024-01-08T00:00Z</start><end>2024-01-08T02:00Z</end></timeInterval>
      <resolution>PT30M</resolution>
      <Point><position>1</position><quantity>3635.66</quantity></Point>
      <Point><position>3</position><quantity>3469.86</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""

PRICE_XML = """<?xml version="1.0" encoding="utf-8"?>
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
  <mRID>a1027a4c3c4847488119f1b2ad80263e</mRID>
  <TimeSeries>
    <mRID>1</mRID>
    <in_Domain.mRID codingScheme="A01">10YNL----------L</in_Domain.mRID>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2024-01-07T23:00Z</start><end>2024-01-08T01:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><price.amount>87.02</price.amount></Point>
      <Point><position>2</position><price.amount>81.5</price.amount></Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>
"""

ACK_XML = """<?xml version="1.0" encoding="utf-8"?>
<Acknowledgement_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-1:acknowledgementdocument:8:0">
  <Reason>
    <code>999</code>
    <text>No matching data found for Data item ACTUAL_TOTAL_LOAD_R3 [6.1.A].</text>
  </Reason>
</Acknowledgement_MarketDocument>
"""

MULTI_PERIOD_XML = """<?xml version="1.0" encoding="utf-8"?>
<GL_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationloaddocument:3:0">
  <TimeSeries>
    <curveType>A03</curveType>
    <Period>
      <timeInterval><start>2024-01-08T00:00Z</start><end>2024-01-08T01:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>10.0</quantity></Point>
    </Period>
    <Period>
      <timeInterval><start>2024-01-08T01:00Z</start><end>2024-01-08T02:00Z</end></timeInterval>
      <resolution>PT60M</resolution>
      <Point><position>1</position><quantity>20.0</quantity></Point>
    </Period>
  </TimeSeries>
</GL_MarketDocument>
"""


def test_parses_load_document_into_period_records():
    result = parse_response(LOAD_XML)
    assert result.kind == "data"
    assert len(result.periods) == 1
    p = result.periods[0]
    assert p["doc_start"] == "2024-01-08T00:00Z"
    assert p["doc_end"] == "2024-01-08T02:00Z"
    assert p["resolution"] == "PT30M"
    assert p["curve_type"] == "A03"
    assert p["points"] == [(1, 3635.66), (3, 3469.86)]


def test_parses_price_document_using_price_amount():
    result = parse_response(PRICE_XML)
    assert result.kind == "data"
    assert result.periods[0]["points"] == [(1, 87.02), (2, 81.5)]
    assert result.periods[0]["resolution"] == "PT60M"


def test_acknowledgement_is_no_data_not_success():
    # HTTP 200 + reason 999 is emptiness, not data. Status code alone lies.
    result = parse_response(ACK_XML)
    assert result.kind == "no_data"
    assert result.reason_code == "999"
    assert "No matching data" in result.reason_text
    assert result.periods == []


def test_multiple_periods_in_one_timeseries_are_kept_separate():
    # Expansion is per Period; merging them would corrupt the dense span.
    result = parse_response(MULTI_PERIOD_XML)
    assert len(result.periods) == 2
    assert result.periods[0]["points"] == [(1, 10.0)]
    assert result.periods[1]["points"] == [(1, 20.0)]


def test_unparseable_body_raises():
    with pytest.raises(ValueError, match="could not parse"):
        parse_response("this is not xml")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/acquisition/test_entsoe_parse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.acquisition.entsoe_parse'`

- [ ] **Step 3: Write the implementation**

Create `src/surg/acquisition/entsoe_parse.py`:

```python
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
                        if fname == "position":
                            position = int(field_node.text)
                        elif fname in _VALUE_TAGS:
                            value = float(field_node.text)
                    if position is not None and value is not None:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/acquisition/test_entsoe_parse.py -v`
Expected: PASS, 5 passed

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check src/surg/acquisition/entsoe_parse.py tests/acquisition/test_entsoe_parse.py`
Expected: `All checks passed!`

- [ ] **Step 6: Stage, then ASK before committing**

```bash
git add src/surg/acquisition/entsoe_parse.py tests/acquisition/test_entsoe_parse.py
```
Proposed message: `feat(entsoe): namespace-agnostic market document parser`

---

## Task 3: Zone registry

Single source of truth for EIC codes, timezones, and which items each zone
serves. Kept separate so the fetcher, the panel builder, and the analysis
cannot drift apart on zone definitions.

**Files:**
- Create: `src/surg/preprocessing/entsoe_zones.py`

- [ ] **Step 1: Write the module**

Create `src/surg/preprocessing/entsoe_zones.py`:

```python
"""ENTSO-E zone registry -- EIC codes, timezones, and item availability.

Availability flags are PROBE RESULTS, not assumptions
(docs/plans/2026-08-12-entsoe-ireland-design.md section 1). Two of them are
load-bearing:

  * Irish LOAD comes from the control area (10YIE-1001A00010, Republic-only,
    unbroken 2015->2026 at PT30M). Irish PRICE must come from the SEM bidding
    zone -- the CTA code returns reason 999 on 12.1.D.
  * IE_SEM load stops between 2025-10-15 and 2025-11-01 (the 6.1.A R3
    migration) and is ~1,015 MW higher than IE_CTA because SEM is all-island.
    Do NOT concatenate the two series.

`serves` values: "load", "price". Zones marked probed=False carry EIC codes
that were never queried -- the fetcher records reason 999 as data, and any
write-up must say "not returned for this EIC", never "not published".
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Zone:
    key: str
    eic: str
    timezone: str
    serves: tuple[str, ...]
    group: str
    probed: bool


ZONES: tuple[Zone, ...] = (
    # --- Ireland: load and price come from DIFFERENT EICs. See module docstring.
    Zone("IE_CTA", "10YIE-1001A00010", "Europe/Dublin", ("load",), "ireland", True),
    Zone("IE_SEM", "10Y1001A1001A59C", "Europe/Dublin", ("price",), "ireland", True),
    # --- Matched control
    Zone("NL", "10YNL----------L", "Europe/Amsterdam", ("load", "price"), "control", True),
    # --- Italy: 7 bidding zones, load AND price, 2015->2026 (design section 1.1)
    Zone("IT_NORTH", "10Y1001A1001A73I", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_CNORTH", "10Y1001A1001A70O", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_CSOUTH", "10Y1001A1001A71M", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_SOUTH", "10Y1001A1001A788", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_SICILY", "10Y1001A1001A75E", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_SARDINIA", "10Y1001A1001A74G", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_CALABRIA", "10Y1001C--00096J", "Europe/Rome", ("load", "price"), "italy", True),
    # --- VRE cross-section (EU-5 solar table). EIC codes below are UNPROBED.
    Zone("DE_LU", "10Y1001A1001A82H", "Europe/Berlin", ("load", "price"), "vre", True),
    Zone("ES", "10YES-REE------0", "Europe/Madrid", ("load", "price"), "vre", False),
    Zone("FR", "10YFR-RTE------C", "Europe/Paris", ("load", "price"), "vre", False),
    Zone("FI", "10YFI-1--------U", "Europe/Helsinki", ("load", "price"), "vre", False),
    Zone("DK1", "10YDK-1--------W", "Europe/Copenhagen", ("load", "price"), "vre", False),
    Zone("DK2", "10YDK-2--------M", "Europe/Copenhagen", ("load", "price"), "vre", False),
    Zone("SE1", "10Y1001A1001A44P", "Europe/Stockholm", ("load", "price"), "vre", False),
    Zone("SE2", "10Y1001A1001A45N", "Europe/Stockholm", ("load", "price"), "vre", False),
    Zone("SE3", "10Y1001A1001A46L", "Europe/Stockholm", ("load", "price"), "vre", False),
    Zone("SE4", "10Y1001A1001A47J", "Europe/Stockholm", ("load", "price"), "vre", False),
)

BY_KEY = {z.key: z for z in ZONES}

YEARS = tuple(range(2015, 2027))


def zones_for(item: str) -> list[Zone]:
    """Zones that are expected to serve `item`."""
    return [z for z in ZONES if item in z.serves]
```

- [ ] **Step 2: Verify it imports and the registry is self-consistent**

Run:
```bash
.venv/bin/python -c "
from surg.preprocessing.entsoe_zones import ZONES, zones_for, BY_KEY
assert len(BY_KEY) == len(ZONES), 'duplicate zone key'
print('zones:', len(ZONES))
print('load zones:', len(zones_for('load')))
print('price zones:', len(zones_for('price')))
assert [z.key for z in zones_for('load')].count('IE_SEM') == 0, 'IE_SEM must not serve load'
assert [z.key for z in zones_for('price')].count('IE_CTA') == 0, 'IE_CTA must not serve price'
print('ok')
"
```
Expected:
```
zones: 20
load zones: 19
price zones: 19
ok
```

- [ ] **Step 3: Lint**

Run: `.venv/bin/ruff check src/surg/preprocessing/entsoe_zones.py`
Expected: `All checks passed!`

- [ ] **Step 4: Stage, then ASK before committing**

```bash
git add src/surg/preprocessing/entsoe_zones.py
```
Proposed message: `feat(entsoe): zone registry with probed availability flags`

---

## Task 4: Fetcher script

**Files:**
- Create: `scripts/entsoe_fetch.py`

- [ ] **Step 1: Write the script**

Create `scripts/entsoe_fetch.py`:

```python
# scripts/entsoe_fetch.py
"""Pull ENTSO-E 6.1.A load and 12.1.D day-ahead price into data/raw/entsoe/.

Constraints that shape this script live in docs/entsoe-api-constraints.md and
docs/plans/2026-08-12-entsoe-ireland-design.md. The four that matter:

  * "No data" is HTTP 200 + reason 999. Every body must be parsed; the status
    code alone cannot distinguish data from emptiness.
  * Over-cap is HTTP 400 carrying an exact count, never a silent truncation.
    The response to a 400 is to halve the window, not to paginate -- offset is
    honoured on only 20 of 77 endpoints and is silently ignored elsewhere.
  * The rate limit is 400 req/min PER TOKEN and tripping it earns a temporary
    ban; the vendor also reserves the right to revoke. We pace at ~5 req/s
    (the docs' own recommendation is 6-7) and STOP on 429 rather than retry.
    The token took 3 working days to obtain and gates this whole thread.
  * Raw storage is parsed-but-UNEXPANDED, so A03 expansion can be re-run and
    re-tested without re-pulling.

Idempotent: re-runs skip any target already on disk. Partial writes go to
.part and are renamed only on success.

Usage: .venv/bin/python scripts/entsoe_fetch.py [--items load,price] [--zones IE_CTA,NL]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import httpx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from surg.acquisition.entsoe_parse import parse_response  # noqa: E402
from surg.preprocessing.entsoe_zones import YEARS, zones_for  # noqa: E402

API = "https://web-api.tp.entsoe.eu/api"
RAW = Path("data/raw/entsoe")
MANIFEST = RAW / "manifest.csv"
SLEEP_S = 0.2  # ~5 req/s, under the documented 6-7 rec.
TIMEOUT_S = 300.0  # vendor request timeout is 5 minutes

ITEM_PARAMS = {
    "load": {"documentType": "A65", "processType": "A16"},
    "price": {"documentType": "A44"},
}


def api_key() -> str:
    for line in Path(".env").read_text().splitlines():
        if line.startswith("ENTSOE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("ENTSOE_API_KEY not found in .env")


def domain_params(item: str, eic: str) -> dict[str, str]:
    if item == "load":
        return {"outBiddingZone_Domain": eic}
    return {"in_Domain": eic, "out_Domain": eic}


def fetch_window(
    client: httpx.Client, item: str, eic: str, start: str, end: str
) -> tuple[str, list[dict], str]:
    """Fetch one window. Returns (outcome, period_records, note).

    outcome is one of: "data", "no_data", "over_cap", "error".
    """
    params = {
        **ITEM_PARAMS[item],
        **domain_params(item, eic),
        "periodStart": start,
        "periodEnd": end,
    }
    resp = client.get(API, params=params, timeout=TIMEOUT_S)
    time.sleep(SLEEP_S)

    if resp.status_code == 429:
        sys.exit(
            "HTTP 429 -- rate limited. STOPPING rather than retrying: the "
            "vendor reserves the right to revoke a misused token. Wait ~10 "
            "minutes and re-run; the pull is idempotent."
        )
    if resp.status_code == 400:
        return "over_cap", [], resp.text[:300].replace("\n", " ")
    if resp.status_code != 200:
        return "error", [], f"HTTP {resp.status_code}: {resp.text[:200]}"

    result = parse_response(resp.text)
    if result.kind == "no_data":
        return "no_data", [], f"reason {result.reason_code}: {result.reason_text}"
    return "data", result.periods, ""


def fetch_year(
    client: httpx.Client, item: str, eic: str, year: int
) -> tuple[str, list[dict], str]:
    """Fetch one calendar year, halving the window if the API rejects on size."""
    windows = [(f"{year}01010000", f"{year + 1}01010000")]
    collected: list[dict] = []
    note = ""
    while windows:
        start, end = windows.pop(0)
        outcome, periods, detail = fetch_window(client, item, eic, start, end)
        if outcome == "over_cap":
            mid = (
                pd.Timestamp(start, tz="UTC")
                + (pd.Timestamp(end, tz="UTC") - pd.Timestamp(start, tz="UTC")) / 2
            ).floor("D")
            mid_s = mid.strftime("%Y%m%d%H%M")
            if mid_s in (start, end):
                return "error", collected, f"cannot split further: {detail}"
            windows[:0] = [(start, mid_s), (mid_s, end)]
            note = "split on over-cap"
            continue
        if outcome == "error":
            return "error", collected, detail
        if outcome == "no_data":
            note = note or detail
            continue
        collected.extend(periods)
    if not collected:
        return "no_data", [], note
    return "data", collected, note


def to_frame(periods: list[dict], zone_key: str, item: str) -> pd.DataFrame:
    rows = []
    for p in periods:
        for position, value in p["points"]:
            rows.append(
                {
                    "zone": zone_key,
                    "item": item,
                    "doc_start": p["doc_start"],
                    "doc_end": p["doc_end"],
                    "resolution": p["resolution"],
                    "curve_type": p["curve_type"],
                    "position": position,
                    "value": value,
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", default="load,price")
    ap.add_argument("--zones", default="", help="comma-separated zone keys; default all")
    ap.add_argument("--years", default="", help="comma-separated years; default all")
    args = ap.parse_args()

    items = args.items.split(",")
    year_list = [int(y) for y in args.years.split(",")] if args.years else list(YEARS)
    manifest_rows = []

    client = httpx.Client(params={"securityToken": api_key()}, follow_redirects=True)
    for item in items:
        candidates = zones_for(item)
        if args.zones:
            wanted = set(args.zones.split(","))
            candidates = [z for z in candidates if z.key in wanted]
        for zone in candidates:
            dest_dir = RAW / item / zone.key
            dest_dir.mkdir(parents=True, exist_ok=True)
            for year in year_list:
                dest = dest_dir / f"{year}.parquet"
                if dest.exists():
                    print(f"  skip (exists): {item}/{zone.key}/{year}")
                    continue
                outcome, periods, note = fetch_year(client, item, zone.eic, year)
                frame = to_frame(periods, zone.key, item)
                if outcome == "data" and not frame.empty:
                    part = dest.with_suffix(".parquet.part")
                    frame.to_parquet(part, index=False)
                    part.rename(dest)
                resolutions = sorted(frame["resolution"].unique()) if not frame.empty else []
                print(f"  {item}/{zone.key}/{year}: {outcome} rows={len(frame)} {resolutions}")
                manifest_rows.append(
                    {
                        "item": item,
                        "zone": zone.key,
                        "eic": zone.eic,
                        "year": year,
                        "outcome": outcome,
                        "n_rows": len(frame),
                        "resolutions": ";".join(resolutions),
                        "note": note,
                    }
                )
    client.close()

    if manifest_rows:
        new = pd.DataFrame(manifest_rows)
        if MANIFEST.exists():
            new = pd.concat([pd.read_csv(MANIFEST), new], ignore_index=True)
            new = new.drop_duplicates(subset=["item", "zone", "year"], keep="last")
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        new.to_csv(MANIFEST, index=False)
        print(f"\nmanifest -> {MANIFEST} ({len(new)} rows)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test on one zone-year before pulling the corpus**

Run:
```bash
.venv/bin/python scripts/entsoe_fetch.py --items load --zones IE_CTA --years 2024
```
Expected: `load/IE_CTA/2024: data rows=17568 ['PT30M']` (17,568 = 366 × 48;
a slightly lower count is normal and means A03 collapsed flat stretches).
Then a manifest line.

- [ ] **Step 3: Verify the raw file round-trips**

Run:
```bash
.venv/bin/python -c "
import pandas as pd
df = pd.read_parquet('data/raw/entsoe/load/IE_CTA/2024.parquet')
print(df.dtypes)
print(df.head(3).to_string())
print('rows:', len(df), 'resolutions:', df.resolution.unique())
assert df.position.min() == 1
assert df.value.notna().all()
print('ok')
"
```
Expected: 8 columns, `position` starting at 1, no NaN values, `ok`.

- [ ] **Step 4: Verify idempotency**

Run the same command from Step 2 again.
Expected: `skip (exists): load/IE_CTA/2024` and no HTTP traffic.

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check scripts/entsoe_fetch.py`
Expected: `All checks passed!`

- [ ] **Step 6: Stage, then ASK before committing**

```bash
git add scripts/entsoe_fetch.py
```
Proposed message: `feat(entsoe): paced idempotent fetcher with coverage manifest`

Note: `data/` is gitignored — the parquet files are not committed and **must
never be deleted** (`CLAUDE.md`).

---

## Task 5: Pull the corpus

Not a code task — an execution task. Kept separate because it is long-running
and its output is the coverage map that the note reports.

- [ ] **Step 1: Pull load for every zone and year**

Run:
```bash
.venv/bin/python scripts/entsoe_fetch.py --items load 2>&1 | tee /tmp/entsoe_load_pull.log
```
Expected: ~19 zones × 12 years. Ireland, NL, Italy and DE-LU should return
`data`. The unprobed zones (ES, FR, FI, DK1/2, SE1–4) may return `no_data` —
**that is a result to record, not a failure to fix.**

- [ ] **Step 2: Pull price for every zone and year**

Run:
```bash
.venv/bin/python scripts/entsoe_fetch.py --items price 2>&1 | tee /tmp/entsoe_price_pull.log
```

- [ ] **Step 3: Summarise the manifest**

Run:
```bash
.venv/bin/python -c "
import pandas as pd
m = pd.read_csv('data/raw/entsoe/manifest.csv')
print(m.groupby(['item','outcome']).size().to_string())
print()
print('zones with zero data rows, by item:')
bad = m[m.n_rows == 0].groupby('item')['zone'].unique()
print(bad.to_string())
print()
print('total requests recorded:', len(m))
"
```
Expected: a coverage table. Record the actual numbers — the design predicted
480 as an *upper bound* and the true count will be lower.

- [ ] **Step 4: Confirm the Irish and Dutch series are complete**

Run:
```bash
.venv/bin/python -c "
import pandas as pd
m = pd.read_csv('data/raw/entsoe/manifest.csv')
for z in ['IE_CTA','NL']:
    sub = m[(m.zone==z) & (m.item=='load')].sort_values('year')
    print(z); print(sub[['year','outcome','n_rows','resolutions']].to_string(index=False))
"
```
Expected: `IE_CTA` data for 2015–2026 at PT30M; `NL` data for 2015–2026 at
PT15M. 2026 is a partial year by construction. **If IE_CTA shows a gap in any
year 2015–2025, stop and investigate before building the panel** — the whole
design rests on that series being continuous.

---

## Task 6: Panel builder

**Files:**
- Create: `src/surg/preprocessing/entsoe_panel.py`
- Test: `tests/preprocessing/test_entsoe_panel.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/preprocessing/test_entsoe_panel.py`:

```python
import pandas as pd
import pytest

from surg.preprocessing.entsoe_panel import build_zone_series, to_hourly


def _raw(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "zone", "item", "doc_start", "doc_end",
            "resolution", "curve_type", "position", "value",
        ],
    )


def test_expands_and_localizes_to_naive_local_prevailing():
    raw = _raw([
        ["IE_CTA", "load", "2024-01-08T00:00Z", "2024-01-08T02:00Z",
         "PT30M", "A03", 1, 3635.66],
        ["IE_CTA", "load", "2024-01-08T00:00Z", "2024-01-08T02:00Z",
         "PT30M", "A03", 3, 3469.86],
    ])
    out = build_zone_series(raw, zone_key="IE_CTA", value_name="load_mw")

    # 2 hours at PT30M = 4 slots; positions 1 and 3 emitted, so 1-2 and 3-4.
    assert len(out) == 4
    assert list(out["load_mw"]) == [3635.66, 3635.66, 3469.86, 3469.86]
    # January in Dublin is UTC+0, so naive local == UTC clock time.
    assert out["timestamp_local"].iloc[0] == pd.Timestamp("2024-01-08 00:00:00")
    assert out["timestamp_local"].dt.tz is None


def test_summer_localization_shifts_by_the_utc_offset():
    raw = _raw([
        ["NL", "load", "2024-07-15T00:00Z", "2024-07-15T01:00Z",
         "PT60M", "A03", 1, 12000.0],
    ])
    out = build_zone_series(raw, zone_key="NL", value_name="load_mw")
    # Amsterdam is UTC+2 in July.
    assert out["timestamp_local"].iloc[0] == pd.Timestamp("2024-07-15 02:00:00")


def test_hourly_derivation_averages_within_the_hour():
    raw = _raw([
        ["NL", "load", "2024-01-08T00:00Z", "2024-01-08T01:00Z",
         "PT15M", "A03", 1, 100.0],
        ["NL", "load", "2024-01-08T00:00Z", "2024-01-08T01:00Z",
         "PT15M", "A03", 3, 200.0],
    ])
    native = build_zone_series(raw, zone_key="NL", value_name="load_mw")
    hourly = to_hourly(native, value_name="load_mw")
    assert len(hourly) == 1
    # positions 1,2 = 100; positions 3,4 = 200 -> mean 150
    assert hourly["load_mw"].iloc[0] == 150.0


def test_dst_fall_back_hour_is_flagged():
    # 2024-10-27 Europe/Dublin falls back: local 01:00 occurs twice.
    raw = _raw([
        ["IE_CTA", "load", "2024-10-27T00:00Z", "2024-10-27T03:00Z",
         "PT60M", "A03", 1, 3000.0],
    ])
    native = build_zone_series(raw, zone_key="IE_CTA", value_name="load_mw")
    hourly = to_hourly(native, value_name="load_mw")
    assert hourly["dst_transition_hour"].sum() == 2


def test_ordinary_day_flags_no_dst_hours():
    raw = _raw([
        ["IE_CTA", "load", "2024-01-08T00:00Z", "2024-01-08T03:00Z",
         "PT60M", "A03", 1, 3000.0],
    ])
    hourly = to_hourly(
        build_zone_series(raw, zone_key="IE_CTA", value_name="load_mw"),
        value_name="load_mw",
    )
    assert hourly["dst_transition_hour"].sum() == 0


def test_unknown_zone_raises():
    raw = _raw([
        ["NOPE", "load", "2024-01-08T00:00Z", "2024-01-08T01:00Z",
         "PT60M", "A03", 1, 1.0],
    ])
    with pytest.raises(KeyError):
        build_zone_series(raw, zone_key="NOPE", value_name="load_mw")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/preprocessing/test_entsoe_panel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.preprocessing.entsoe_panel'`

- [ ] **Step 3: Write the implementation**

Create `src/surg/preprocessing/entsoe_panel.py`:

```python
"""Build native-resolution and hourly panels from raw ENTSO-E rows.

Two panels come from one source (design section 3.3):

  * native  -- each zone at its own resolution (NL PT15M, IE PT30M, IT PT60M
               or PT15M depending on the year)
  * hourly  -- mean within the hour, for cross-zone comparison

A caution that must survive into the write-up: an hourly panel DERIVED BY
AVERAGING sub-hourly data is low-pass filtered, so it is smoother than a
natively-metered hourly series. vol_norm LEVELS are therefore not strictly
comparable between these zones and the 11 existing panels. Within-zone TRENDS
are, and the trend is what this design tests.

Resolution is read PER DOCUMENT, never assumed per zone -- IT-North switches
from PT60M to PT15M somewhere between 2021 and 2026 (design section 1.2).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.preprocessing.entsoe_expand import expand_curve, resolution_minutes
from surg.preprocessing.entsoe_zones import BY_KEY

_DOC_KEYS = ["doc_start", "doc_end", "resolution", "curve_type"]


def build_zone_series(
    raw: pd.DataFrame, *, zone_key: str, value_name: str
) -> pd.DataFrame:
    """Expand every document in `raw` and localize to naive local prevailing.

    Returns columns: timestamp_utc, timestamp_local, <value_name>.
    """
    zone = BY_KEY[zone_key]

    frames = []
    for (start, end, resolution, curve_type), group in raw.groupby(
        _DOC_KEYS, sort=True
    ):
        points = list(zip(group["position"], group["value"], strict=True))
        dense, _ = expand_curve(
            start=pd.Timestamp(start),
            end=pd.Timestamp(end),
            resolution=resolution,
            curve_type=curve_type,
            points=points,
        )
        index = pd.date_range(
            start=pd.Timestamp(start),
            periods=len(dense),
            freq=f"{resolution_minutes(resolution)}min",
            tz="UTC",
        )
        frames.append(pd.DataFrame({"timestamp_utc": index, value_name: dense}))

    if not frames:
        return pd.DataFrame(columns=["timestamp_utc", "timestamp_local", value_name])

    out = pd.concat(frames, ignore_index=True)
    # Documents can overlap (12.1.D returns whole days regardless of the
    # window asked for), so de-duplicate on the UTC instant.
    out = out.drop_duplicates(subset="timestamp_utc").sort_values("timestamp_utc")
    out["timestamp_local"] = (
        out["timestamp_utc"].dt.tz_convert(zone.timezone).dt.tz_localize(None)
    )
    out.attrs["timezone"] = zone.timezone
    out.attrs["zone_key"] = zone_key
    return out.reset_index(drop=True)[["timestamp_utc", "timestamp_local", value_name]]


def to_hourly(native: pd.DataFrame, *, value_name: str, timezone: str | None = None) -> pd.DataFrame:
    """Mean within the hour, plus the dst_transition_hour flag stage1 needs.

    The timezone comes from `native.attrs` (set by build_zone_series) unless
    passed explicitly. It cannot be recovered by offset arithmetic, because the
    offset changes across DST -- which is the whole point of the flag.
    """
    columns = ["timestamp_utc", "timestamp_local", value_name, "dst_transition_hour"]
    if native.empty:
        return pd.DataFrame(columns=columns)

    tz = timezone or native.attrs.get("timezone")
    if tz is None:
        raise ValueError(
            "timezone unknown: pass timezone= explicitly, or build the frame "
            "with build_zone_series so attrs['timezone'] is set"
        )

    work = native.copy()
    work["hour_utc"] = work["timestamp_utc"].dt.floor("h")
    grouped = (
        work.groupby("hour_utc", as_index=False)[value_name]
        .mean()
        .rename(columns={"hour_utc": "timestamp_utc"})
    )
    grouped["timestamp_local"] = (
        grouped["timestamp_utc"].dt.tz_convert(tz).dt.tz_localize(None)
    )
    grouped["dst_transition_hour"] = grouped["timestamp_local"].duplicated(keep=False)
    grouped.attrs["timezone"] = tz
    return grouped[columns].reset_index(drop=True)


def load_raw(item: str, zone_key: str, root: str = "data/raw/entsoe") -> pd.DataFrame:
    """Concatenate every year file on disk for one zone and item."""
    files = sorted(Path(root, item, zone_key).glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"no raw files for {item}/{zone_key} under {root}")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def zone_panel(
    item: str, zone_key: str, *, value_name: str, root: str = "data/raw/entsoe"
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Convenience: disk -> (native, hourly)."""
    raw = load_raw(item, zone_key, root)
    native = build_zone_series(raw, zone_key=zone_key, value_name=value_name)
    return native, to_hourly(native, value_name=value_name)
```

> **Implementer note on `attrs`:** pandas does not preserve `.attrs` through
> every operation, so `to_hourly` also accepts an explicit `timezone=`. If any
> caller loses the attribute, pass `BY_KEY[zone_key].timezone` directly rather
> than reconstructing it from timestamps — per-row offsets vary across DST, so
> offset arithmetic is wrong by construction.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/preprocessing/test_entsoe_panel.py -v`
Expected: PASS, 6 passed

- [ ] **Step 5: Build the real Irish and Dutch panels and sanity-check them**

Run:
```bash
.venv/bin/python -c "
from surg.preprocessing.entsoe_panel import zone_panel
for z in ['IE_CTA', 'NL']:
    native, hourly = zone_panel('load', z, value_name='load_mw')
    print(z, 'native rows:', len(native), 'hourly rows:', len(hourly))
    print('  span:', native.timestamp_local.min(), '->', native.timestamp_local.max())
    print('  mean load MW:', round(native.load_mw.mean(), 1))
    print('  dst hours flagged:', int(hourly.dst_transition_hour.sum()))
"
```
Expected: IE_CTA mean load in the 3,000–5,000 MW range (a country of Ireland's
size); NL an order of magnitude higher, ~12,000–14,000 MW. DST hours flagged
should be roughly 2 per year of span. **If IE mean load looks ~1,000 MW higher
than expected, the SEM EIC was used instead of the CTA one — stop and check the
registry.**

- [ ] **Step 6: Verify the hourly panel satisfies the stage1 contract**

Run:
```bash
.venv/bin/python -c "
from surg.preprocessing.entsoe_panel import zone_panel
from surg.diagnostics.stage1 import assert_panel_quality
_, hourly = zone_panel('load', 'IE_CTA', value_name='load_mw')
p = hourly.rename(columns={'load_mw':'load_mw_IE'})[
    ['timestamp_local','load_mw_IE','dst_transition_hour']].dropna()
assert_panel_quality(p, ['IE'], time_col='timestamp_local', dst_pairs_per_year=1)
print('stage1 contract satisfied, rows:', len(p))
"
```
Expected: `stage1 contract satisfied, rows: ~100000`.
**Do not run `assert_panel_quality` on the native panel** — it computes
`expected = (max−min)/3600 + 1` with a ±48-row tolerance, so a 30-minute panel
fails by ~50,000 rows and a 15-minute one by ~370,000. That assertion is for
the hourly panel only (design §5).

- [ ] **Step 7: Lint**

Run: `.venv/bin/ruff check src/surg/preprocessing/entsoe_panel.py tests/preprocessing/test_entsoe_panel.py`
Expected: `All checks passed!`

- [ ] **Step 8: Stage, then ASK before committing**

```bash
git add src/surg/preprocessing/entsoe_panel.py tests/preprocessing/test_entsoe_panel.py
```
Proposed message: `feat(entsoe): native and hourly panel builders`

---

## Task 7: CSO data-centre dose series

**Files:**
- Create: `scripts/cso_fetch.py`

Endpoint verified live 2026-08-12: 44 quarters (2015Q1–2025Q4) × 3 categories
× 1 statistic = 132 values in GWh.

- [ ] **Step 1: Write the script**

Create `scripts/cso_fetch.py`:

```python
# scripts/cso_fetch.py
"""Fetch CSO table MEC02 -- Irish data-centre metered electricity consumption.

This is the DOSE variable, and it is why Ireland is worth the attention: every
US result in this project used a geographic proxy (Loudoun, DOM, Ashburn),
whereas this is measured consumption.

Verified 2026-08-12: JSON-stat 2.0, 44 quarters (2015Q1-2025Q4), 3 categories
(all metered / data centres / customers other than data centres), unit GWh.
Free, no registration.

Caveats that must reach the write-up: CSO has no data-centre classification --
sites are identified heuristically (name matching, business parks, meters above
1 GWh) -- and CSO warns new small sites fall below its thresholds. The series
is national and quarterly. It fixes EXISTENCE of an exposure trend, not
identification.

Usage: .venv/bin/python scripts/cso_fetch.py
"""
from __future__ import annotations

import json
from pathlib import Path

import httpx
import pandas as pd

URL = (
    "https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/"
    "MEC02/JSON-stat/2.0/en"
)
DEST = Path("data/raw/cso/mec02.parquet")


def _labels(dim_spec: dict) -> list[str]:
    """Category labels in index order."""
    category = dim_spec["category"]
    index = category["index"]
    label = category.get("label", {})
    codes = (
        index
        if isinstance(index, list)
        else [c for c, _ in sorted(index.items(), key=lambda kv: kv[1])]
    )
    return [label.get(c, c) for c in codes]


def main() -> None:
    resp = httpx.get(URL, timeout=120.0)
    resp.raise_for_status()
    payload = json.loads(resp.text)
    ds = payload.get("dataset", payload)

    ids = ds["id"]
    sizes = ds["size"]
    values = ds["value"]
    labels = {d: _labels(ds["dimension"][d]) for d in ids}

    rows = []
    for flat, value in enumerate(values):
        coords, rest = [], flat
        for size in reversed(sizes):
            coords.append(rest % size)
            rest //= size
        coords.reverse()
        record = {d: labels[d][c] for d, c in zip(ids, coords, strict=True)}
        record["value_gwh"] = value
        rows.append(record)

    df = pd.DataFrame(rows)
    quarter_col = next(c for c in df.columns if c.startswith("TLIST"))
    category_col = next(
        c for c in df.columns if c not in ("STATISTIC", quarter_col, "value_gwh")
    )
    df = df.rename(columns={quarter_col: "quarter", category_col: "category"})

    wide = df.pivot_table(
        index="quarter", columns="category", values="value_gwh", aggfunc="first"
    ).reset_index()
    wide.columns.name = None

    dc_col = next(c for c in wide.columns if "Data centres" in c)
    total_col = next(c for c in wide.columns if "All metered" in c)
    wide["dc_gwh"] = wide[dc_col]
    wide["total_gwh"] = wide[total_col]
    wide["dc_share"] = wide["dc_gwh"] / wide["total_gwh"]
    wide["period"] = pd.PeriodIndex(wide["quarter"], freq="Q")
    wide = wide.sort_values("period").reset_index(drop=True)

    DEST.parent.mkdir(parents=True, exist_ok=True)
    wide.to_parquet(DEST, index=False)

    print(f"wrote {DEST} ({len(wide)} quarters)")
    print(wide[["quarter", "dc_gwh", "total_gwh", "dc_share"]].head(3).to_string(index=False))
    print("...")
    print(wide[["quarter", "dc_gwh", "total_gwh", "dc_share"]].tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python scripts/cso_fetch.py`
Expected: `wrote data/raw/cso/mec02.parquet (44 quarters)`, and the tail rows
showing 2025Q4 with `dc_share` near **0.232** — the 23.2% figure the design
carries from EU-0 §3. **If the final share is not close to 0.23, stop** —
either the category mapping is wrong or the EU-0 figure needs revisiting.

- [ ] **Step 3: Record the 2015 baseline, which the design deliberately left unverified**

Run:
```bash
.venv/bin/python -c "
import pandas as pd
d = pd.read_parquet('data/raw/cso/mec02.parquet')
first, last = d.iloc[0], d.iloc[-1]
print(f'{first.quarter}: {first.dc_share:.4f}')
print(f'{last.quarter}: {last.dc_share:.4f}')
print(f'growth factor: {last.dc_share / first.dc_share:.2f}x')
"
```
Expected: a 2015Q1 share and a growth factor. **Write these numbers into the
note** — design §0 states the 2015 starting share was never verified and is
computed here, not assumed.

- [ ] **Step 4: Lint**

Run: `.venv/bin/ruff check scripts/cso_fetch.py`
Expected: `All checks passed!`

- [ ] **Step 5: Stage, then ASK before committing**

```bash
git add scripts/cso_fetch.py
```
Proposed message: `feat(cso): fetch MEC02 data-centre consumption dose series`

---

## Task 8: Ireland analysis — shape statistics and diurnal decomposition

**Files:**
- Create: `scripts/entsoe_ireland.py`

- [ ] **Step 1: Write the script**

Create `scripts/entsoe_ireland.py`:

```python
# scripts/entsoe_ireland.py
"""Did Irish load shape change as data centres grew to 23.2% of consumption?

Approach A -- four level-normalized shape statistics per period, for Ireland
and the Netherlands, joined to the CSO dose series.
Approach B -- normalized diurnal profiles per year, the mechanism plot.

WHICH COMPARISONS ARE LICENSED (design section 4.1) -- this constrains what
the note may print:

  * pt_ratio: IE/NL HOURLY vs the ISONE HOURLY figure (1.467) is comparable.
    The UKPN 1.05 is NOT -- half-hourly, per-site, a utilisation ratio rather
    than MW. Quote it only as a facility-level contrast in prose, never in the
    same column as a zonal number.
  * vol_norm: an hourly panel derived by AVERAGING sub-hourly data is low-pass
    filtered, so it reads smoother than natively-metered hourly. LEVELS are
    not comparable to the 11 existing panels; WITHIN-ZONE TRENDS are, and the
    trend is what this tests.

This is not a causal design: one treated unit, one control, n=44 quarters,
and a heuristically-constructed covariate.

Usage: .venv/bin/python scripts/entsoe_ireland.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from surg.preprocessing.entsoe_panel import zone_panel  # noqa: E402

OUT = Path("outputs/entsoe")
ZONES = {"IE_CTA": "Ireland", "NL": "Netherlands"}
NATIVE_STEP = {"IE_CTA": 30, "NL": 15}
STATISTICS = ["vol_norm", "pt_ratio", "load_factor", "night_floor"]


def shape_statistics(panel: pd.DataFrame, *, freq_minutes: int) -> pd.Series:
    """Four level-normalized shape statistics for one block of a load panel."""
    load = panel["load_mw"]
    mean_load = load.mean()

    grad = load.diff().abs() / freq_minutes
    vol_norm = grad.mean() / mean_load

    daily = panel.groupby(panel["timestamp_local"].dt.date)["load_mw"]
    day_max, day_min, day_mean = daily.max(), daily.min(), daily.mean()
    valid = day_min > 0

    return pd.Series(
        {
            "n_obs": len(panel),
            "mean_load_mw": mean_load,
            "vol_norm": vol_norm,
            "pt_ratio": (day_max[valid] / day_min[valid]).median(),
            "load_factor": mean_load / load.max(),
            "night_floor": (day_min[valid] / day_mean[valid]).median(),
        }
    )


def by_period(panel: pd.DataFrame, *, freq_minutes: int, freq: str) -> pd.DataFrame:
    """Shape statistics grouped by year ('Y') or quarter ('Q')."""
    work = panel.dropna(subset=["load_mw"]).copy()
    key = work["timestamp_local"].dt.to_period(freq)
    rows = []
    for period, block in work.groupby(key):
        if len(block) < 100:
            continue
        stats = shape_statistics(block, freq_minutes=freq_minutes)
        stats["period"] = str(period)
        rows.append(stats)
    return pd.DataFrame(rows).set_index("period")


def diurnal_profile(panel: pd.DataFrame, year: int) -> pd.Series:
    """Mean daily profile for one year, each day normalized by its own mean."""
    work = panel[panel["timestamp_local"].dt.year == year].dropna(subset=["load_mw"])
    if work.empty:
        return pd.Series(dtype=float)
    work = work.copy()
    work["date"] = work["timestamp_local"].dt.date
    work["slot"] = (
        work["timestamp_local"].dt.hour * 60 + work["timestamp_local"].dt.minute
    )
    day_mean = work.groupby("date")["load_mw"].transform("mean")
    work["normalized"] = work["load_mw"] / day_mean
    return work.groupby("slot")["normalized"].mean()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, object] = {}

    native_panels, hourly_panels = {}, {}
    for key in ZONES:
        native, hourly = zone_panel("load", key, value_name="load_mw")
        native_panels[key], hourly_panels[key] = native, hourly

    # --- Approach A -------------------------------------------------------
    for key, label in ZONES.items():
        annual = by_period(hourly_panels[key], freq_minutes=60, freq="Y")
        quarterly = by_period(hourly_panels[key], freq_minutes=60, freq="Q")
        annual_native = by_period(
            native_panels[key], freq_minutes=NATIVE_STEP[key], freq="Y"
        )

        annual.to_csv(OUT / f"shape_annual_hourly_{key}.csv")
        quarterly.to_csv(OUT / f"shape_quarterly_hourly_{key}.csv")
        annual_native.to_csv(OUT / f"shape_annual_native_{key}.csv")
        results[key] = {
            "label": label,
            "annual_hourly": annual.to_dict(orient="index"),
            "annual_native": annual_native.to_dict(orient="index"),
        }
        print(f"\n=== {label} ({key}) annual, hourly panel ===")
        print(annual.round(4).to_string())

    # --- Dose join --------------------------------------------------------
    cso = pd.read_parquet("data/raw/cso/mec02.parquet")
    dose = cso.set_index(cso["quarter"].astype(str))["dc_share"]

    correlations = {}
    for key in ZONES:
        quarterly = pd.read_csv(OUT / f"shape_quarterly_hourly_{key}.csv", index_col=0)
        joined = quarterly.join(dose, how="inner")
        stats = {}
        for column in STATISTICS:
            sub = joined[[column, "dc_share"]].dropna()
            stats[column] = {
                "n": int(len(sub)),
                "pearson_r": float(sub[column].corr(sub["dc_share"])),
                "first": float(sub[column].iloc[0]) if len(sub) else None,
                "last": float(sub[column].iloc[-1]) if len(sub) else None,
            }
        correlations[key] = stats
        joined.to_csv(OUT / f"shape_quarterly_with_dose_{key}.csv")

    print("\n=== correlation with Irish DC share (NL row is the PLACEBO) ===")
    for key, stats in correlations.items():
        print(f"\n{ZONES[key]}:")
        for column, values in stats.items():
            print(
                f"  {column:<13} r={values['pearson_r']:+.3f}  n={values['n']}  "
                f"{values['first']:.4f} -> {values['last']:.4f}"
            )
    results["correlations"] = correlations

    # --- Approach B: diurnal decomposition --------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, (key, label) in zip(axes, ZONES.items(), strict=True):
        for year in (2015, 2020, 2025):
            profile = diurnal_profile(native_panels[key], year)
            if profile.empty:
                continue
            ax.plot(profile.index / 60.0, profile.values, label=str(year))
        ax.axhline(1.0, color="grey", linewidth=0.6, linestyle=":")
        ax.set_title(f"{label} — normalized daily profile")
        ax.set_xlabel("hour of local day")
        ax.legend()
    axes[0].set_ylabel("load ÷ that day's mean")
    fig.tight_layout()
    fig.savefig(OUT / "fig_diurnal_profiles.png", dpi=150)
    plt.close(fig)

    # --- Trend figure -----------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, column in zip(axes.ravel(), STATISTICS, strict=True):
        for key, label in ZONES.items():
            annual = pd.read_csv(OUT / f"shape_annual_hourly_{key}.csv", index_col=0)
            ax.plot(annual.index.astype(str), annual[column], marker="o", label=label)
        ax.set_title(column)
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "fig_shape_trends.png", dpi=150)
    plt.close(fig)

    (OUT / "ireland_results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nwrote {OUT}/ireland_results.json, fig_diurnal_profiles.png, fig_shape_trends.png")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/python scripts/entsoe_ireland.py 2>&1 | tee /tmp/entsoe_ireland.log`
Expected: annual tables for both zones, a correlation block, and three output
files. Sanity checks before believing anything:
- `load_factor` between 0.6 and 0.9 for both (a national grid, not a flat block)
- `pt_ratio` between 1.2 and 2.0 (ISONE hourly is 1.467)
- `night_floor` between 0.6 and 0.9

- [ ] **Step 3: Check the placebo before interpreting**

The Netherlands is correlated against **Irish** DC share on purpose. If NL
shows correlations as strong as Ireland's, the Irish correlation is picking up
a common European time trend — COVID, the 2022 energy crisis, EV and heat-pump
growth — and **not** data centres. Record that comparison explicitly; it is the
main defence against over-reading.

- [ ] **Step 4: Lint**

Run: `.venv/bin/ruff check scripts/entsoe_ireland.py`
Expected: `All checks passed!`

- [ ] **Step 5: Stage, then ASK before committing**

```bash
git add scripts/entsoe_ireland.py
```
Proposed message: `feat(entsoe): Irish load-shape analysis with NL control`

---

## Task 9: Italy Stage-1 robustness driver

Marked a robustness check, **not a finding** — per EU-0 §1, European zones are
panels 12–13 of a result already in hand (level beat |gradient| in 11/11 panels
including the low-DC control).

**Files:**
- Create: `scripts/entsoe_italy_stage1.py`

- [ ] **Step 1: Read the existing driver to match its shape**

Run: `sed -n '1,60p' scripts/isone_diagnostic.py`
Follow whatever conventions it establishes for figdir, argument handling and
printing.

- [ ] **Step 2: Write the script**

Create `scripts/entsoe_italy_stage1.py`:

```python
# scripts/entsoe_italy_stage1.py
"""Stage-1 level-vs-volatility horse race on the 7 Italian bidding zones.

ROBUSTNESS CHECK, NOT A FINDING. EU-0 section 1 argues European zones are
panels 12-13 of a result already in hand: level beat |gradient| in 11 of 11
panels including the near-zero-data-centre control. This exists because Italy
is the only European within-country price cross-section and the panel is a
near-free by-product of a corpus pulled for other reasons.

Italy is also the one place where a TSO-vs-Transparency-Platform load
disagreement would matter (Hirth et al. 2018 found >10% deviations). Terna is
NOT cross-checked here -- flagged as future work.

Usage: .venv/bin/python scripts/entsoe_italy_stage1.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END,
    COMMON_OVERLAP_START,
    FAR_FUTURE,
    add_zone_gradients,
    assert_panel_quality,
    data_quality_report,
    level_vs_volatility,
    trend_tables,
)
from surg.preprocessing.entsoe_panel import zone_panel

FIGDIR = Path("outputs/entsoe/italy_stage1")
ZONES = [
    "IT_NORTH", "IT_CNORTH", "IT_CSOUTH", "IT_SOUTH",
    "IT_SICILY", "IT_SARDINIA", "IT_CALABRIA",
]
TIME_COL = "timestamp_local"


def build_panel() -> tuple[pd.DataFrame, list[str], list[str]]:
    """Join hourly load and price for every Italian zone on local time."""
    panel = None
    price_cols = []
    for key in ZONES:
        _, load_hourly = zone_panel("load", key, value_name=f"load_mw_{key}")
        block = load_hourly[[TIME_COL, f"load_mw_{key}", "dst_transition_hour"]]
        if panel is None:
            panel = block
        else:
            panel = panel.merge(
                block.drop(columns="dst_transition_hour"), on=TIME_COL, how="inner"
            )

        _, price_hourly = zone_panel("price", key, value_name=f"price_{key}")
        panel = panel.merge(
            price_hourly[[TIME_COL, f"price_{key}"]], on=TIME_COL, how="left"
        )
        price_cols.append(f"price_{key}")

    panel = panel.sort_values(TIME_COL).reset_index(drop=True)
    return panel, ZONES, price_cols


def main() -> None:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    panel, zones, price_cols = build_panel()
    panel = panel.dropna(subset=[f"load_mw_{z}" for z in zones]).reset_index(drop=True)

    assert_panel_quality(panel, zones, time_col=TIME_COL, dst_pairs_per_year=1)
    panel = add_zone_gradients(panel, zones, time_col=TIME_COL)

    data_quality_report(
        panel, price_cols, time_col=TIME_COL,
        window_start=COMMON_OVERLAP_START, figdir=FIGDIR,
    )
    trend_tables(panel, zones, time_col=TIME_COL, figdir=FIGDIR, market="ITALY")
    for label, start, end in [
        ("max", panel[TIME_COL].min(), FAR_FUTURE),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(
            panel, zones, price_cols, time_col=TIME_COL,
            window_start=start, window_end=end,
            figdir=FIGDIR, market="ITALY", label=label,
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run it**

Run: `.venv/bin/python scripts/entsoe_italy_stage1.py 2>&1 | tee /tmp/entsoe_italy.log`
Expected: rows-per-year, price quality, trend tables, and two horse-race tables
ending in `level wins in N of M cells`. If `assert_panel_quality` raises,
**read the message rather than loosening the assertion** — it exists because
these exact failure modes have bitten this project before.

- [ ] **Step 4: Lint**

Run: `.venv/bin/ruff check scripts/entsoe_italy_stage1.py`
Expected: `All checks passed!`

- [ ] **Step 5: Stage, then ASK before committing**

```bash
git add scripts/entsoe_italy_stage1.py
```
Proposed message: `feat(entsoe): Italy 7-zone Stage-1 robustness driver`

---

## Task 10: Full test suite and regression check

- [ ] **Step 1: Run the new tests together**

Run:
```bash
.venv/bin/pytest tests/preprocessing/test_entsoe_expand.py \
                 tests/preprocessing/test_entsoe_panel.py \
                 tests/acquisition/test_entsoe_parse.py -v
```
Expected: 24 passed.

- [ ] **Step 2: Run the fast preprocessing subset to check nothing regressed**

Run: `.venv/bin/pytest tests/preprocessing -q`
Expected: all pass. Nothing in this plan modifies existing modules, so a
failure here is a real regression — investigate rather than proceeding.

- [ ] **Step 3: Run the full suite**

Run: `.venv/bin/pytest -q`
Expected: all pass. **Budget 10+ minutes** — the full suite is bootstrap-heavy
(`CLAUDE.md`). `tests/regression/` pins numbers from production runs; a failure
there is a real behaviour change, not flakiness.

- [ ] **Step 4: Lint everything new**

Run: `.venv/bin/ruff check .`
Expected: `All checks passed!`

---

## Task 11: Write the research note and update the logs

**Files:**
- Create: `docs/research-notes/K-ireland-dc-shape.md`
- Modify: `docs/plans/2026-08-19-advisor-meeting-agenda.md` — the empty
  "European energy markets" section (currently line ~20)
- Modify: `docs/decisions.md` — **APPEND ONLY**, new entry at the end

- [ ] **Step 1: Read the model note for structure and tone**

Run: `cat docs/research-notes/J-ukpn-flatness.md`
Match its structure: headline finding first, method, numbers, then limits.

- [ ] **Step 2: Write `docs/research-notes/K-ireland-dc-shape.md`**

Required content, in this order:

1. **Headline** — one sentence: did Irish load shape change as DC share grew?
2. **Why Ireland** — the dose is *measured* (CSO MEC02), the first time in this
   project. Report the actual 2015Q1 → 2025Q4 shares and growth factor from
   Task 7 Step 3.
3. **Data** — IE CTA load, PT30M, 2015→2026, and the fact that Irish load and
   price come from *different EICs*. Report the manifest coverage numbers.
4. **The four statistics**, with IE and NL side by side, annual.
5. **The dose correlation and the NL placebo**, together. Never the Irish
   correlation alone.
6. **The diurnal figure** and what it shows about *where* in the day shape moved.
7. **Limits, in full:** n=44 quarters, one treated unit, no causal claim;
   COVID; the 2022 energy crisis; EV and heat-pump growth confounding
   `night_floor` in the same direction as data centres; CSO's heuristic and
   drifting identification method.
8. **Comparison discipline** — state that the UKPN 1.05 is a facility-level
   figure and is not in the same units as a zonal `pt_ratio`, and that
   `vol_norm` levels are not comparable to the 11 existing panels because
   hourly-from-sub-hourly is low-pass filtered. Trends are.
9. **Italy**, one short section, explicitly labelled a robustness check.

- [ ] **Step 3: Fill the agenda's "European energy markets" section**

Edit `docs/plans/2026-08-19-advisor-meeting-agenda.md`, replacing the empty
bullet under `### European energy markets` with 4–6 bullets in the style of the
existing "UK Data centers" section: what the data is, what was found, and what
it cannot say.

- [ ] **Step 4: Append a `docs/decisions.md` entry**

**Append only — never edit or delete an existing entry** (`CLAUDE.md`). New
section at the end of the file:

```markdown
## 2026-08-12 — ENTSO-E: Irish data-centre dose vs load shape
```

Cover: the four probe findings that overturned EU-0/EU-2 desk research
(Italy is a real 7-zone panel; native sub-hourly resolution; the Irish CTA-vs-SEM
EIC discovery and that it voids EU-0 §3's footprint objection; A03 sparsity
being material), the design choice of Ireland-with-NL-control, the headline
result, and the explicit non-causal framing.

- [ ] **Step 5: Stage, then ASK before committing**

```bash
git add docs/research-notes/K-ireland-dc-shape.md \
        docs/plans/2026-08-19-advisor-meeting-agenda.md \
        docs/decisions.md
```
Proposed message: `docs(entsoe): Irish DC dose vs load shape findings`

---

## Self-Review

**Spec coverage — every design section maps to a task:**

| Design section | Task |
|---|---|
| §1 probe findings (recorded, not re-run) | context for Tasks 1–4 |
| §2 corpus, 20 zones, EIC table | Task 3 (registry), Task 5 (pull) |
| §3.0 raw storage schema | Task 4 |
| §3.1 fetcher, no entsoe-py | Task 4 |
| §3.2 A03 expander | Task 1 |
| §3.3 native + hourly panels, localization | Task 6 |
| §3.4 CSO MEC02 | Task 7 |
| §3.5 Ireland analysis | Task 8 |
| §3.6 Italy Stage-1 driver | Task 9 |
| §4.1 four statistics, dose join, placebo | Task 8 |
| §4.1 licensed comparisons | Task 8 docstring, Task 11 Step 2 item 8 |
| §4.2 diurnal decomposition | Task 8 |
| §4.3 confounders | Task 11 Step 2 item 7 |
| §4.4 BTM asymmetry | Task 11 Step 2 (note prose) |
| §5 testing, assertion split | Tasks 1, 2, 6 (Step 6), 10 |
| §6 deliverables | Task 11 |

XML parsing was not a named component in the design but is required by §3.0/§3.1
— added as Task 2. The zone registry is likewise implied by §2 rather than
named — added as Task 3.

**Type consistency:** `expand_curve(start, end, resolution, curve_type, points)
-> (ndarray, float)` is used identically in Task 1 tests and Task 6.
`parse_response(xml) -> ParseResult(kind, periods, reason_code, reason_text)` is
consistent between Tasks 2 and 4. `build_zone_series(raw, zone_key=, value_name=)`
and `to_hourly(native, value_name=, timezone=)` match between Tasks 6, 8 and 9.
Raw column names (`zone, item, doc_start, doc_end, resolution, curve_type,
position, value`) are identical in Tasks 4, 6 and their tests. `STATISTICS` and
`NATIVE_STEP` are module constants in Task 8, so the statistic list cannot drift
between the correlation loop and the trend figure.

---

## Open question for the user before execution

`CLAUDE.md` says feature work goes in a **sibling worktree**
(`git worktree add -b <name> ../surg-<name> main`, own venv, fast-forward-only
merge, then remove worktree and delete branch). This plan creates 8 new files
and modifies 2, which qualifies.

But the approved design doc is currently **staged and uncommitted on `main`**,
and `3b65008` / `bac1b77` are unpushed. So the worktree decision has to be made
before Task 1: either commit the design on `main` first and branch from it, or
run the whole thing on `main`.

**If a worktree is used:** `data/` and `outputs/` are gitignored, so the corpus
pulled in Task 5 lives only in the worktree. Before any `git worktree remove`,
`rsync -a --ignore-existing` both directories back into the main checkout and
verify file counts match. This has bitten the project before.
