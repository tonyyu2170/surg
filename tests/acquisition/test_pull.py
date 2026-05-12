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
    with pytest.raises(ValueError, match="requires a value for pnode_ids"):
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
    with pytest.raises(ValueError, match="uses pnode_ids only"):
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


def test_feed_specs_mark_archive_support_correctly():
    from surg.acquisition.pull import _FEED_SPECS
    # Only the three LMP feeds support archive-tier queries.
    archive_feeds = {f for f, s in _FEED_SPECS.items() if s.supports_archive}
    assert archive_feeds == {"rt_hrl_lmps", "da_hrl_lmps", "rt_fivemin_hrl_lmps"}


def test_feedspec_default_supports_archive_is_false():
    from surg.acquisition.pull import FeedSpec
    spec = FeedSpec("datetime_beginning_ept", "zone", False)
    assert spec.supports_archive is False


def test_pull_feed_rejects_empty_pnode_ids_with_no_zone(tmp_path: Path):
    """Empty list is treated the same as None — no filter would slip through."""
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="requires a value for pnode_ids"):
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
    with pytest.raises(ValueError, match="requires a value for zone"):
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


def test_sync_reserve_events_uses_event_start_ept_date_field(tmp_path: Path):
    """sync_reserve_events filters and sorts on event_start_ept, not datetime_beginning_ept."""
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    pull_feed(
        feed="sync_reserve_events",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=None,
        zone=None,
        subzone="MidAtlantic-Dominion (MAD)",
        group_label="mad",
        client=client,
        data_root=tmp_path,
    )

    args, _ = client.get_feed.call_args
    params = args[1]
    # Date filter on event_start_ept, NOT datetime_beginning_ept
    assert "event_start_ept" in params
    assert "datetime_beginning_ept" not in params
    assert "2026-04-15 00:00 to 2026-04-15 23:59" in params["event_start_ept"]
    # Sort field matches
    assert params["sort"] == "event_start_ept"
    assert params["order"] == "Asc"
    # Geographic filter uses synchronized_sub_zone
    assert params["synchronized_sub_zone"] == "MidAtlantic-Dominion (MAD)"
    # Not an LMP feed
    assert "row_is_current" not in params


def test_reserve_market_results_uses_locale_filter(tmp_path: Path):
    """reserve_market_results uses the `locale` filter (e.g., 'MAD')."""
    rows_per_call = [[{"v": 1}]]
    client, _ = _mock_client(rows_per_call)

    pull_feed(
        feed="reserve_market_results",
        start=date(2026, 4, 15),
        end=date(2026, 4, 15),
        pnode_ids=None,
        zone=None,
        locale="MAD",
        group_label="mad",
        client=client,
        data_root=tmp_path,
    )

    args, _ = client.get_feed.call_args
    params = args[1]
    assert "datetime_beginning_ept" in params
    assert params["locale"] == "MAD"
    assert "pnode_id" not in params
    assert "zone" not in params
    assert "synchronized_sub_zone" not in params
    assert "row_is_current" not in params
    assert params["sort"] == "datetime_beginning_ept"


def test_sync_reserve_events_requires_subzone(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="requires a value for subzone"):
        pull_feed(
            feed="sync_reserve_events",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=None,
            zone=None,
            subzone=None,
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_sync_reserve_events_rejects_pnode_ids(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="uses subzone only; got pnode_ids"):
        pull_feed(
            feed="sync_reserve_events",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=[35010365],
            subzone="MidAtlantic-Dominion (MAD)",
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_reserve_market_results_requires_locale(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="requires a value for locale"):
        pull_feed(
            feed="reserve_market_results",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=None,
            zone=None,
            locale=None,
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_reserve_market_results_rejects_zone(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="uses locale only; got zone"):
        pull_feed(
            feed="reserve_market_results",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            zone="DOM",
            locale="MAD",
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_unknown_feed_raises(tmp_path: Path):
    client, _ = _mock_client([])
    with pytest.raises(ValueError, match="unknown feed: 'not_a_real_feed'"):
        pull_feed(
            feed="not_a_real_feed",
            start=date(2026, 4, 15),
            end=date(2026, 4, 15),
            pnode_ids=[35010365],
            group_label="mad",
            client=client,
            data_root=tmp_path,
        )


def test_build_params_archive_drops_pnode_id_and_sort():
    from datetime import date
    from surg.acquisition.pull import _build_params

    params = _build_params(
        "rt_hrl_lmps",
        date(2023, 1, 1), date(2023, 12, 31),
        geo_value=None,
        archive_mode=True,
        archive_subtype="EHV",
    )
    assert "pnode_id" not in params
    assert "sort" not in params
    assert "order" not in params
    assert params["type"] == "EHV"
    assert params["datetime_beginning_ept"].startswith("2023-01-01")
    assert params["row_is_current"] == "true"


def test_build_params_archive_requires_subtype_for_lmp():
    from datetime import date
    import pytest
    from surg.acquisition.pull import _build_params

    with pytest.raises(ValueError, match="archive_subtype is required"):
        _build_params(
            "rt_hrl_lmps",
            date(2023, 1, 1), date(2023, 12, 31),
            geo_value=None,
            archive_mode=True,
            archive_subtype=None,
        )


def test_build_params_archive_rejected_on_non_archive_feed():
    from datetime import date
    import pytest
    from surg.acquisition.pull import _build_params

    with pytest.raises(ValueError, match="does not support archive"):
        _build_params(
            "hrl_load_metered",
            date(2023, 1, 1), date(2023, 12, 31),
            geo_value="DOM",
            archive_mode=True,
            archive_subtype="LOAD",
        )


def test_build_params_standard_unchanged_when_archive_mode_false():
    """Regression: existing callers (archive_mode default False) get the
    same params they did before this task."""
    from datetime import date
    from surg.acquisition.pull import _build_params

    params = _build_params(
        "rt_hrl_lmps",
        date(2025, 6, 1), date(2025, 6, 30),
        geo_value=[35010365, 35010371],
    )
    assert params["pnode_id"] == "35010365;35010371"
    assert params["sort"] == "datetime_beginning_ept"
    assert params["order"] == "Asc"
    assert "type" not in params


def test_pull_feed_archive_mode_filters_to_target_pnodes(tmp_path):
    """Archive-mode pull keeps only rows matching the locked target IDs."""
    from datetime import date
    import httpx
    from surg.acquisition.client import PJMClient
    from surg.acquisition.pull import pull_feed

    # Mock returns 4 rows: 2 target EHV pnodes + 2 unrelated EHV pnodes.
    def handler(request: httpx.Request) -> httpx.Response:
        assert "pnode_id" not in request.url.params  # archive: no pnode filter
        assert request.url.params["type"] == "EHV"
        return httpx.Response(200, json={
            "totalRows": 4,
            "items": [
                {"pnode_id": 35010365, "pnode_name": "LOUDOUN",
                 "datetime_beginning_ept": "2023-06-15T03:00:00",
                 "congestion_price_rt": 10.0, "total_lmp_rt": 50.0},
                {"pnode_id": 35010371, "pnode_name": "PLEASANT VIEW",
                 "datetime_beginning_ept": "2023-06-15T03:00:00",
                 "congestion_price_rt": 12.0, "total_lmp_rt": 52.0},
                {"pnode_id": 99999999, "pnode_name": "RANDOM",
                 "datetime_beginning_ept": "2023-06-15T03:00:00",
                 "congestion_price_rt": 1.0, "total_lmp_rt": 41.0},
                {"pnode_id": 88888888, "pnode_name": "OTHER",
                 "datetime_beginning_ept": "2023-06-15T03:00:00",
                 "congestion_price_rt": 2.0, "total_lmp_rt": 42.0},
            ],
        })

    client = PJMClient(
        api_key="test", min_interval_s=0.0,
        transport=httpx.MockTransport(handler),
    )
    paths = pull_feed(
        feed="rt_hrl_lmps",
        start=date(2023, 6, 15), end=date(2023, 6, 15),
        archive_mode=True,
        archive_subtype="EHV",
        target_pnode_ids=[35010365, 35010371],  # filter to these
        group_label="dom_targets_archive_ehv",
        client=client,
        data_root=tmp_path,
    )
    assert len(paths) == 1
    import pandas as pd
    df = pd.read_parquet(paths[0])
    assert len(df) == 2
    assert set(df["pnode_id"]) == {35010365, 35010371}


def test_pull_feed_archive_mode_rejects_standard_geo_kwargs(tmp_path):
    """If archive_mode is set, callers should not pass pnode_ids/zone/etc."""
    from datetime import date
    import httpx
    import pytest
    from surg.acquisition.client import PJMClient
    from surg.acquisition.pull import pull_feed

    client = PJMClient(
        api_key="test", min_interval_s=0.0,
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
            "totalRows": 0, "items": []
        })),
    )
    with pytest.raises(ValueError, match="pnode_ids|zone|subzone|locale"):
        pull_feed(
            feed="rt_hrl_lmps",
            start=date(2023, 6, 15), end=date(2023, 6, 15),
            archive_mode=True,
            archive_subtype="EHV",
            target_pnode_ids=[35010365],
            pnode_ids=[35010365],  # should error: not allowed with archive
            group_label="dom_targets_archive_ehv",
            client=client,
            data_root=tmp_path,
        )


def test_pull_feed_archive_mode_requires_target_pnode_ids(tmp_path):
    """archive_mode=True without target_pnode_ids must raise."""
    from datetime import date
    import httpx
    import pytest
    from surg.acquisition.client import PJMClient
    from surg.acquisition.pull import pull_feed

    client = PJMClient(
        api_key="test", min_interval_s=0.0,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"totalRows": 0, "items": []})
        ),
    )
    with pytest.raises(ValueError, match="target_pnode_ids"):
        pull_feed(
            feed="rt_hrl_lmps",
            start=date(2023, 6, 15), end=date(2023, 6, 15),
            archive_mode=True,
            archive_subtype="EHV",
            target_pnode_ids=None,
            group_label="dom_targets_archive_ehv",
            client=client,
            data_root=tmp_path,
        )


def test_pull_feed_archive_mode_rejects_non_archive_feed(tmp_path):
    """archive_mode=True on a feed where supports_archive=False must raise."""
    from datetime import date
    import httpx
    import pytest
    from surg.acquisition.client import PJMClient
    from surg.acquisition.pull import pull_feed

    client = PJMClient(
        api_key="test", min_interval_s=0.0,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"totalRows": 0, "items": []})
        ),
    )
    with pytest.raises(ValueError, match="does not support archive"):
        pull_feed(
            feed="hrl_load_metered",
            start=date(2023, 6, 15), end=date(2023, 6, 15),
            archive_mode=True,
            archive_subtype="LOAD",
            target_pnode_ids=[34964545],
            group_label="dom_load_archive",
            client=client,
            data_root=tmp_path,
        )
