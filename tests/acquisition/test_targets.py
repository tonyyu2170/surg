import pytest
from dataclasses import FrozenInstanceError

from surg.acquisition.targets import (
    Pnode,
    PNODES,
    all_pnode_ids,
    pnodes_by_tier,
)


def test_eleven_pnodes_locked():
    assert len(PNODES) == 11
    ids = {p.pnode_id for p in PNODES}
    assert len(ids) == 11, "pnode IDs must be unique"


def test_specific_pnodes_present():
    by_id = {p.pnode_id: p for p in PNODES}
    assert by_id[35010365].name == "LOUDOUN"
    assert by_id[34964545].name == "DOM"
    assert by_id[34886139].name == "ASHBURN 35 KV TX1"


def test_tiers_partition():
    tiers = {p.tier for p in PNODES}
    assert tiers == {
        "primary_transmission",
        "primary_distribution",
        "control",
        "zonal",
    }
    counts = {t: len(pnodes_by_tier(t)) for t in tiers}
    assert counts == {
        "primary_transmission": 6,
        "primary_distribution": 2,
        "control": 2,
        "zonal": 1,
    }


def test_all_pnode_ids_returns_int_list():
    ids = all_pnode_ids()
    assert isinstance(ids, list)
    assert len(ids) == 11
    assert all(isinstance(i, int) for i in ids)


def test_pnode_is_immutable():
    with pytest.raises(FrozenInstanceError):
        PNODES[0].pnode_id = 999


def test_pnode_is_hashable():
    p = PNODES[0]
    assert hash(p) == hash(p)
    assert len({p, p}) == 1
