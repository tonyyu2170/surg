"""Locked target pnode set for the SURG analysis.

See `docs/decisions.md` 2026-05-10 §5 for the rationale behind
this set. Identifying by pnode_id is required (the LMP feed
truncates pnode_name; see `docs/pjm-api-constraints.md`).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tier = Literal[
    "primary_transmission",
    "primary_distribution",
    "control",
    "zonal",
]


@dataclass(frozen=True, slots=True)
class Pnode:
    pnode_id: int
    name: str
    tier: Tier


PNODES: tuple[Pnode, ...] = (
    # Primary nodal — Loudoun-area transmission cluster (500 KV AGGREGATE/EHV)
    Pnode(35010365,   "LOUDOUN",            "primary_transmission"),
    Pnode(35010371,   "PLEASANT VIEW",      "primary_transmission"),
    Pnode(1356178195, "GOOSECRE",           "primary_transmission"),
    Pnode(1356178171, "BRAMBLET",           "primary_transmission"),
    Pnode(1356178181, "MOSBY",              "primary_transmission"),
    Pnode(1356178201, "SKFFSCRK",           "primary_transmission"),
    # Primary nodal — Ashburn distribution (35 KV BUS/LOAD)
    Pnode(34886139,   "ASHBURN 35 KV TX1",  "primary_distribution"),
    Pnode(34886141,   "ASHBURN 35 KV TX2",  "primary_distribution"),
    # Control / outside the Loudoun cluster
    Pnode(35010369,   "OX",                 "control"),
    Pnode(62871513,   "BRISTERS",           "control"),
    # DOM zonal baseline
    Pnode(34964545,   "DOM",                "zonal"),
)


def all_pnode_ids() -> list[int]:
    return [p.pnode_id for p in PNODES]


def pnodes_by_tier(tier: Tier) -> list[Pnode]:
    return [p for p in PNODES if p.tier == tier]
