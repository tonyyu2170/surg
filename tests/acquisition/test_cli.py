from datetime import date
from unittest.mock import patch

import pytest

from surg.acquisition.pull import _parse_iso_date, main


def test_parse_iso_date_happy():
    assert _parse_iso_date("2026-04-15") == date(2026, 4, 15)


def test_parse_iso_date_invalid_raises():
    with pytest.raises(ValueError):
        _parse_iso_date("2026-13-99")


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "surg-pull" in out


def test_missing_api_key_exits_2(monkeypatch, capsys):
    monkeypatch.delenv("PJM_API_KEY", raising=False)
    # Prevent load_dotenv from re-populating from .env on the host
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "rt_hrl_lmps",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
    ])
    assert rc == 2
    assert "PJM_API_KEY" in capsys.readouterr().err


def test_zone_with_lmp_feed_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "rt_hrl_lmps",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--zone", "DOM",
    ])
    assert rc == 2
    assert "not valid for feed" in capsys.readouterr().err


def test_zone_required_for_load_feed_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "hrl_load_metered",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
    ])
    assert rc == 2
    assert "--zone is required" in capsys.readouterr().err


def test_lmp_feed_dispatches_with_all_pnode_ids(monkeypatch, tmp_path):
    """Happy path: --feed rt_hrl_lmps without --zone passes all 11 pnodes."""
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)

    captured = {}

    def fake_pull_feed(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("surg.acquisition.pull.pull_feed", fake_pull_feed)
    # Avoid making the client actually open an httpx session against real PJM.
    # We never reach the network because fake_pull_feed returns early.
    rc = main([
        "--feed", "rt_hrl_lmps",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--data-root", str(tmp_path),
    ])
    assert rc == 0
    assert captured["pnode_ids"] is not None
    assert len(captured["pnode_ids"]) == 11
    assert captured["zone"] is None


def test_load_feed_dispatches_with_zone(monkeypatch, tmp_path):
    """--feed hrl_load_metered --zone DOM dispatches with pnode_ids=None."""
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)

    captured = {}

    def fake_pull_feed(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("surg.acquisition.pull.pull_feed", fake_pull_feed)
    rc = main([
        "--feed", "hrl_load_metered",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--zone", "DOM",
        "--data-root", str(tmp_path),
    ])
    assert rc == 0
    assert captured["pnode_ids"] is None
    assert captured["zone"] == "DOM"


def test_sync_reserve_events_dispatches_with_subzone(monkeypatch, tmp_path):
    """--feed sync_reserve_events --subzone MAD dispatches with subzone kwarg."""
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)

    captured = {}

    def fake_pull_feed(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("surg.acquisition.pull.pull_feed", fake_pull_feed)
    rc = main([
        "--feed", "sync_reserve_events",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--subzone", "MidAtlantic-Dominion (MAD)",
        "--data-root", str(tmp_path),
    ])
    assert rc == 0
    assert captured["subzone"] == "MidAtlantic-Dominion (MAD)"
    assert captured.get("pnode_ids") is None
    assert captured.get("zone") is None
    assert captured.get("locale") is None


def test_reserve_market_results_dispatches_with_locale(monkeypatch, tmp_path):
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)

    captured = {}

    def fake_pull_feed(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr("surg.acquisition.pull.pull_feed", fake_pull_feed)
    rc = main([
        "--feed", "reserve_market_results",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--locale", "MAD",
        "--data-root", str(tmp_path),
    ])
    assert rc == 0
    assert captured["locale"] == "MAD"
    assert captured.get("pnode_ids") is None


def test_sync_reserve_events_without_subzone_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "sync_reserve_events",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
    ])
    assert rc == 2
    assert "--subzone is required" in capsys.readouterr().err


def test_reserve_market_results_without_locale_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "reserve_market_results",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
    ])
    assert rc == 2
    assert "--locale is required" in capsys.readouterr().err


def test_subzone_with_lmp_feed_exits_2(monkeypatch, capsys):
    """--subzone is not valid for LMP feeds (which use pnode_id)."""
    monkeypatch.setenv("PJM_API_KEY", "fake")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "rt_hrl_lmps",
        "--start", "2026-04-15",
        "--end", "2026-04-15",
        "--subzone", "MAD",
    ])
    assert rc == 2
    assert "--subzone is not valid" in capsys.readouterr().err


def test_cli_archive_tier_requires_subtype(monkeypatch, capsys):
    monkeypatch.setenv("PJM_API_KEY", "test")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "rt_hrl_lmps",
        "--start", "2023-01-01", "--end", "2023-12-31",
        "--archive-tier",
        # missing --archive-subtype
        "--group-label", "dom_targets_archive_ehv",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "--archive-subtype" in err


def test_cli_archive_tier_rejected_for_non_lmp_feed(monkeypatch, capsys):
    monkeypatch.setenv("PJM_API_KEY", "test")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "hrl_load_metered",
        "--start", "2023-01-01", "--end", "2023-12-31",
        "--archive-tier", "--archive-subtype", "LOAD",
        "--zone", "DOM",
        "--group-label", "dom",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "does not support" in err.lower()


def test_cli_archive_tier_rejected_for_5min_lmp(monkeypatch, capsys):
    """5-min LMP rejects the `type` filter on Historic — not workable."""
    monkeypatch.setenv("PJM_API_KEY", "test")
    monkeypatch.setattr("surg.acquisition.pull.load_dotenv", lambda *a, **k: False)
    rc = main([
        "--feed", "rt_fivemin_hrl_lmps",
        "--start", "2023-01-01", "--end", "2023-12-31",
        "--archive-tier", "--archive-subtype", "EHV",
        "--group-label", "dom_targets_archive_ehv",
    ])
    assert rc == 2
    err = capsys.readouterr().err
    assert "5-min" in err.lower() or "fivemin" in err.lower()
