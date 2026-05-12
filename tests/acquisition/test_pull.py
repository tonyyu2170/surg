from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from surg.acquisition.pull import pull_feed


def _mock_client(rows_per_call: list[list[dict]]):
    """Return a mock client whose get_feed yields the next list each call."""
    mc = MagicMock()
    queue = list(rows_per_call)

    def _get_feed(*args, **kwargs):
        return iter(queue.pop(0))

    mc.get_feed.side_effect = _get_feed
    return mc, queue


def test_writes_one_chunk_per_calendar_year(tmp_path: Path):
    rows_per_call = [
        [{"datetime_beginning_ept": "2024-12-15", "v": 1}],
        [{"datetime_beginning_ept": "2025-01-15", "v": 2}],
    ]
    client, _ = _mock_client(rows_per_call)

    written = pull_feed(
        feed="rt_hrl_lmps",
        start=date(2024, 12, 1),
        end=date(2025, 1, 31),
        pnode_ids=[35010365],
        group_label="dom_targets",
        client=client,
        data_root=tmp_path,
    )

    assert client.get_feed.call_count == 2
    assert len(written) == 2
    assert (tmp_path / "rt_hrl_lmps" / "2024").is_dir()
    assert (tmp_path / "rt_hrl_lmps" / "2025").is_dir()


def test_skips_existing_chunks_by_default(tmp_path: Path):
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    # Pre-create the chunk file
    feed_dir = tmp_path / "rt_hrl_lmps" / "2026"
    feed_dir.mkdir(parents=True)
    pd.DataFrame({"v": [99]}).to_parquet(
        feed_dir / "dom__2026-04-15_to_2026-04-15.parquet"
    )

    written = pull_feed(
        feed="rt_hrl_lmps",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=[35010365],
        group_label="dom",
        client=client,
        data_root=tmp_path,
    )

    assert client.get_feed.call_count == 0
    assert written == []


def test_force_overrides_skip(tmp_path: Path):
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    feed_dir = tmp_path / "rt_hrl_lmps" / "2026"
    feed_dir.mkdir(parents=True)
    pd.DataFrame({"v": [99]}).to_parquet(
        feed_dir / "dom__2026-04-15_to_2026-04-15.parquet"
    )

    pull_feed(
        feed="rt_hrl_lmps",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=[35010365],
        group_label="dom",
        client=client,
        data_root=tmp_path,
        force=True,
    )

    assert client.get_feed.call_count == 1
    # Overwritten with the new value
    df = pd.read_parquet(feed_dir / "dom__2026-04-15_to_2026-04-15.parquet")
    assert list(df["v"]) == [1]


def test_passes_correct_params_to_client(tmp_path: Path):
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    pull_feed(
        feed="rt_hrl_lmps",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=[35010365, 1356178195],
        group_label="dom",
        client=client,
        data_root=tmp_path,
    )

    args, kwargs = client.get_feed.call_args
    assert args[0] == "rt_hrl_lmps"
    params = args[1]
    # Date filter is the inclusive range with the API's required ` to ` separator
    assert "2026-04-15 00:00 to 2026-04-15 23:59" in params["datetime_beginning_ept"]
    # Multiple pnodes are semicolon-packed
    assert params["pnode_id"] == "35010365;1356178195"
    # row_is_current=true for LMP feeds
    assert params.get("row_is_current") == "true"
    # Sort by date ascending
    assert params.get("sort") == "datetime_beginning_ept"
    assert params.get("order") == "Asc"


def test_zonal_feed_omits_pnode_id(tmp_path: Path):
    """For hrl_load_metered we filter by zone instead of pnode_id."""
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    pull_feed(
        feed="hrl_load_metered",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=None,  # signal: not a nodal pull
        zone="DOM",
        group_label="dom",
        client=client,
        data_root=tmp_path,
    )

    args, _ = client.get_feed.call_args
    params = args[1]
    assert "pnode_id" not in params
    assert params["zone"] == "DOM"
    assert params.get("row_is_current") is None  # not an LMP feed


def test_empty_chunk_still_writes_an_empty_parquet(tmp_path: Path):
    """A chunk that returns zero rows is treated as 'pulled' so we don't re-pull."""
    rows_per_call = [[]]
    client, _ = _mock_client(rows_per_call)

    written = pull_feed(
        feed="rt_hrl_lmps",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=[35010365],
        group_label="dom",
        client=client,
        data_root=tmp_path,
    )

    assert len(written) == 1
    df = pd.read_parquet(written[0])
    assert df.empty


def test_pull_feed_rejects_missing_filter(tmp_path: Path):
    """Both pnode_ids=None AND zone=None should raise — would otherwise
    issue an unfiltered query that returns millions of rows."""
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="exactly one of pnode_ids or zone"):
        pull_feed(
            feed="rt_hrl_lmps",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=None,
            zone=None,
            group_label="dom",
            client=client,
            data_root=tmp_path,
        )


def test_pull_feed_rejects_both_filters(tmp_path: Path):
    """Both pnode_ids AND zone is ambiguous — raise."""
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="exactly one of pnode_ids or zone"):
        pull_feed(
            feed="rt_hrl_lmps",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=[35010365],
            zone="DOM",
            group_label="dom",
            client=client,
            data_root=tmp_path,
        )


def test_feed_specs_registry_has_all_supported_feeds():
    from surg.acquisition.pull import _FEED_SPECS, FeedSpec

    expected_feeds = {
        "rt_hrl_lmps", "da_hrl_lmps", "rt_fivemin_hrl_lmps",
        "hrl_load_metered",
        "sync_reserve_events", "reserve_market_results",
    }
    assert set(_FEED_SPECS.keys()) == expected_feeds

    # LMP feeds get row_is_current=true added
    for f in ["rt_hrl_lmps", "da_hrl_lmps", "rt_fivemin_hrl_lmps"]:
        assert _FEED_SPECS[f].is_lmp is True
        assert _FEED_SPECS[f].date_field == "datetime_beginning_ept"
        assert _FEED_SPECS[f].geo_filter_key == "pnode_id"

    # Load feed uses zone filter
    assert _FEED_SPECS["hrl_load_metered"].geo_filter_key == "zone"
    assert _FEED_SPECS["hrl_load_metered"].is_lmp is False

    # New: sync_reserve_events uses event_start_ept and synchronized_sub_zone
    sre = _FEED_SPECS["sync_reserve_events"]
    assert sre.date_field == "event_start_ept"
    assert sre.geo_filter_key == "synchronized_sub_zone"
    assert sre.is_lmp is False

    # New: reserve_market_results uses datetime_beginning_ept and locale
    rmr = _FEED_SPECS["reserve_market_results"]
    assert rmr.date_field == "datetime_beginning_ept"
    assert rmr.geo_filter_key == "locale"
    assert rmr.is_lmp is False


def test_pull_feed_rejects_empty_pnode_ids_with_no_zone(tmp_path: Path):
    """Empty list is treated the same as None — no filter would slip through."""
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="exactly one of pnode_ids or zone"):
        pull_feed(
            feed="rt_hrl_lmps",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=[],
            zone=None,
            group_label="dom",
            client=client,
            data_root=tmp_path,
        )


def test_pull_feed_rejects_empty_zone_with_no_pnodes(tmp_path: Path):
    """Empty string zone is treated the same as None."""
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="exactly one of pnode_ids or zone"):
        pull_feed(
            feed="hrl_load_metered",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=None,
            zone="",
            group_label="dom",
            client=client,
            data_root=tmp_path,
        )
