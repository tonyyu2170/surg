import time

import httpx
import pytest

from surg.acquisition.client import PJMClient


def _mock_transport(handler):
    """Wrap a handler function as an httpx.MockTransport."""
    return httpx.MockTransport(handler)


def test_auth_header_attached():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"items": [], "totalRows": 0})

    client = PJMClient(api_key="test-key-123", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("pnode", {"zone": "DOM"}))

    assert captured["headers"].get("ocp-apim-subscription-key") == "test-key-123"
    assert rows == []


def test_paginates_until_total_rows_reached():
    calls = {"n": 0, "starts": []}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        params = dict(request.url.params)
        start = int(params["startRow"])
        rc = int(params["rowCount"])
        calls["starts"].append(start)
        # Simulate 5 total rows; the loop should request startRow=1,3,5
        # with page_size=2 → batches of [2,2,1]
        all_rows = [{"i": i} for i in range(1, 6)]
        page = all_rows[start - 1 : start - 1 + rc]
        return httpx.Response(200, json={"items": page, "totalRows": 5})

    client = PJMClient(api_key="k", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("rt_hrl_lmps", {"foo": "bar"}, page_size=2))

    assert calls["n"] == 3
    assert calls["starts"] == [1, 3, 5]
    assert rows == [{"i": 1}, {"i": 2}, {"i": 3}, {"i": 4}, {"i": 5}]


def test_throttle_sleeps_between_requests(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [{"i": 1}], "totalRows": 1})

    client = PJMClient(api_key="k", min_interval_s=11.0,
                       transport=_mock_transport(handler))
    list(client.get_feed("pnode", {}))
    list(client.get_feed("pnode", {}))

    # First call: no sleep. Second: should sleep ~11s (less the tiny elapsed).
    assert len(sleeps) == 1
    assert 9.5 <= sleeps[0] <= 11.5


def test_max_rows_caps_pagination():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        # API claims 1000 rows total, but max_rows=3 should stop us early
        return httpx.Response(200, json={
            "items": [{"i": calls["n"]}],
            "totalRows": 1000,
        })

    client = PJMClient(api_key="k", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("pnode", {}, page_size=1, max_rows=3))

    assert calls["n"] == 3
    assert rows == [{"i": 1}, {"i": 2}, {"i": 3}]


def test_429_retries_with_backoff(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] <= 2:
            return httpx.Response(429, json={"error": "rate-limited"})
        return httpx.Response(200, json={"items": [{"ok": True}], "totalRows": 1})

    client = PJMClient(api_key="k", min_interval_s=0.0, max_retries=3,
                       backoff_base_s=2.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("pnode", {}))

    assert state["n"] == 3
    assert rows == [{"ok": True}]
    # Two backoff sleeps: 2.0, 4.0 (exponential)
    assert sleeps == [2.0, 4.0]


def test_429_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    client = PJMClient(api_key="k", min_interval_s=0.0, max_retries=2,
                       transport=_mock_transport(handler))
    with pytest.raises(RuntimeError, match="429"):
        list(client.get_feed("pnode", {}))


def test_4xx_other_than_429_raises(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"errors": [{"message": "bad params"}]})

    client = PJMClient(api_key="k", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        list(client.get_feed("pnode", {}))


def test_context_manager_closes_underlying_client():
    closed = {"v": False}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"items": [], "totalRows": 0})

    with PJMClient(api_key="k", min_interval_s=0.0,
                   transport=_mock_transport(handler)) as client:
        list(client.get_feed("pnode", {}))
        # Confirm we have an httpx.Client; close it via context exit
    # No assertion on closed state needed — httpx.Client.is_closed is the truth
    assert client._client.is_closed


def test_empty_batch_mid_pagination_stops_silently():
    """If the API returns items=[] mid-pagination, the loop terminates.

    PJM's API is well-behaved here, but we lock the behavior: a partial
    result is what we get. The orchestrator can detect short results by
    comparing row count to totalRows if needed.
    """
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(200, json={"items": [{"i": 1}, {"i": 2}], "totalRows": 100})
        # Subsequent pages return empty even though totalRows=100
        return httpx.Response(200, json={"items": [], "totalRows": 100})

    client = PJMClient(api_key="k", min_interval_s=0.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("pnode", {}, page_size=2))

    assert state["n"] == 2  # makes one more call to discover empty batch
    assert rows == [{"i": 1}, {"i": 2}]


def test_throttle_and_backoff_compose_additively_under_429(monkeypatch):
    """Verify backoff is ADDITIVE to throttle (not absorbed).

    Under min_interval_s=10.0 and backoff_base_s=2.0:
      - First request fires immediately (no prior request)
      - 429 → backoff sleep 2.0s
      - Next iteration: throttle sleeps full 10.0s on top (since
        _last_request_ts was reset after the backoff)
      - Request succeeds
    Total sleeps: [2.0, 10.0]
    """
    sleeps: list[float] = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        state["n"] += 1
        if state["n"] == 1:
            return httpx.Response(429)
        return httpx.Response(200, json={"items": [{"ok": True}], "totalRows": 1})

    client = PJMClient(api_key="k", min_interval_s=10.0, max_retries=3,
                       backoff_base_s=2.0,
                       transport=_mock_transport(handler))
    rows = list(client.get_feed("pnode", {}))

    # First call: no throttle (no prior). 429. Backoff 2s. Reset ts.
    # Retry: throttle 10s (ts was just reset). Success.
    assert sleeps == pytest.approx([2.0, 10.0], abs=0.01)
    assert rows == [{"ok": True}]
