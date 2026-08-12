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
    Zone("NL", "10YNL----------L", "Europe/Amsterdam",
         ("load", "price", "capacity"), "control", True),
    # --- Italy: 7 bidding zones, load AND price, 2015->2026 (design section 1.1)
    Zone("IT_NORTH", "10Y1001A1001A73I", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_CNORTH", "10Y1001A1001A70O", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_CSOUTH", "10Y1001A1001A71M", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_SOUTH", "10Y1001A1001A788", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_SICILY", "10Y1001A1001A75E", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_SARDINIA", "10Y1001A1001A74G", "Europe/Rome", ("load", "price"), "italy", True),
    Zone("IT_CALABRIA", "10Y1001C--00096J", "Europe/Rome", ("load", "price"), "italy", True),
    # --- VRE cross-section (EU-5 solar table). All ten EICs PROBED 2026-08-12:
    # every one returns 6.1.A load. Two probe results constrain their use:
    #
    #   * DE_LU returns NOTHING before 2018 -- the zone split from DE_AT_LU
    #     (10Y1001A1001A63L) on 2018-10-01, and that predecessor returns data in
    #     2016 and none in 2024. Its footprint included Austria, so the two are
    #     NOT concatenable. This is the Calabria precedent: a late entrant whose
    #     inclusion in an inner join would truncate the whole panel.
    #   * SE1-SE4 return NO A68 installed capacity -- it is published on the
    #     Swedish country EIC (10YSE-1--------K, 3,200 MW in 2024) and cannot be
    #     apportioned across the four bidding zones. They carry load only, so
    #     they contribute to the seasonal test, which needs no dose, and not to
    #     the dose cross-section.
    #
    # "capacity" is absent from IE_CTA and IE_SEM too: both return reason 999.
    Zone("DE_LU", "10Y1001A1001A82H", "Europe/Berlin",
         ("load", "price", "capacity"), "vre", True),
    Zone("ES", "10YES-REE------0", "Europe/Madrid",
         ("load", "price", "capacity"), "vre", True),
    Zone("FR", "10YFR-RTE------C", "Europe/Paris",
         ("load", "price", "capacity"), "vre", True),
    Zone("FI", "10YFI-1--------U", "Europe/Helsinki",
         ("load", "price", "capacity"), "vre", True),
    Zone("DK1", "10YDK-1--------W", "Europe/Copenhagen",
         ("load", "price", "capacity"), "vre", True),
    Zone("DK2", "10YDK-2--------M", "Europe/Copenhagen",
         ("load", "price", "capacity"), "vre", True),
    Zone("SE1", "10Y1001A1001A44P", "Europe/Stockholm", ("load", "price"), "vre", True),
    Zone("SE2", "10Y1001A1001A45N", "Europe/Stockholm", ("load", "price"), "vre", True),
    Zone("SE3", "10Y1001A1001A46L", "Europe/Stockholm", ("load", "price"), "vre", True),
    Zone("SE4", "10Y1001A1001A47J", "Europe/Stockholm", ("load", "price"), "vre", True),
)

# First year each zone returns 6.1.A load, where it is NOT the panel start.
# Recorded so a driver drops a late entrant explicitly instead of letting an
# inner join silently truncate every other zone to its start date.
FIRST_LOAD_YEAR = {"DE_LU": 2018}

BY_KEY = {z.key: z for z in ZONES}

YEARS = tuple(range(2015, 2027))


def zones_for(item: str) -> list[Zone]:
    """Zones that are expected to serve `item`."""
    return [z for z in ZONES if item in z.serves]
