"""Locked target pnode set for the SURG analysis.

See `docs/decisions.md` entry "2026-05-10 — Lock the 11-pnode target set"
for the rationale behind this set. Identifying by pnode_id is required
(the LMP feed truncates pnode_name; see `docs/pjm-api-constraints.md`).
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

Subtype = Literal["EHV", "LOAD", "ZONE"]


@dataclass(frozen=True, slots=True)
class Pnode:
    pnode_id: int
    name: str
    tier: Tier
    subtype: Subtype


PNODES: tuple[Pnode, ...] = (
    # Primary nodal — Loudoun-area transmission cluster (500 KV EHV)
    Pnode(35010365,   "LOUDOUN",            "primary_transmission", "EHV"),
    Pnode(35010371,   "PLEASANT VIEW",      "primary_transmission", "EHV"),
    Pnode(1356178195, "GOOSECRE",           "primary_transmission", "EHV"),
    Pnode(1356178171, "BRAMBLET",           "primary_transmission", "EHV"),
    Pnode(1356178181, "MOSBY",              "primary_transmission", "EHV"),
    Pnode(1356178201, "SKFFSCRK",           "primary_transmission", "EHV"),
    # Primary nodal — Ashburn distribution (35 KV LOAD)
    Pnode(34886139,   "ASHBURN 35 KV TX1",  "primary_distribution", "LOAD"),
    Pnode(34886141,   "ASHBURN 35 KV TX2",  "primary_distribution", "LOAD"),
    # Control / outside the Loudoun cluster
    Pnode(35010369,   "OX",                 "control", "EHV"),
    Pnode(62871513,   "BRISTERS",           "control", "EHV"),
    # DOM zonal baseline
    Pnode(34964545,   "DOM",                "zonal", "ZONE"),
)


def all_pnode_ids() -> list[int]:
    return [p.pnode_id for p in PNODES]


def pnodes_by_tier(tier: Tier) -> list[Pnode]:
    return [p for p in PNODES if p.tier == tier]


def pnode_ids_by_subtype(subtype: str) -> list[int]:
    """Return pnode IDs for all targets matching the LMP-feed `type` value.

    Subtype is the `pnode_subtype` value as it appears in the
    rt_hrl_lmps response's `type` column. Used by Plan 1.5's
    archive-mode pull to client-side filter Historic-tier results.
    """
    return [p.pnode_id for p in PNODES if p.subtype == subtype]
