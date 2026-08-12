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
