"""Tests for the gridstatus.io hosted-API client (mock transport, no network)."""
from __future__ import annotations

import httpx
import pytest

from surg.acquisition.gridstatus_client import GridStatusClient


def _client(handler, **kw):
    kw.setdefault("min_interval_s", 0.0)  # no throttling in tests
    return GridStatusClient(
        api_key="k", transport=httpx.MockTransport(handler), **kw
    )


def test_query_sends_api_key_and_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["headers"] = dict(request.headers)
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={"data": [], "meta": {"hasNextPage": False}})

    with _client(handler) as c:
        rows = list(c.query(
            "pjm_load",
            start_time="2025-06-24T04:00:00Z",
            end_time="2025-07-24T04:00:00Z",
            columns="interval_start_utc,interval_end_utc,dom",
        ))
    assert rows == []
    assert seen["headers"]["x-api-key"] == "k"
    assert seen["params"]["start_time"] == "2025-06-24T04:00:00Z"
    assert seen["params"]["columns"] == "interval_start_utc,interval_end_utc,dom"
    assert seen["params"]["page_size"] == "50000"


def test_query_follows_cursor_pagination():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(dict(request.url.params))
        if "cursor" not in request.url.params:
            return httpx.Response(200, json={
                "data": [{"a": 1}, {"a": 2}],
                "meta": {"hasNextPage": True, "cursor": "C1"},
            })
        return httpx.Response(200, json={
            "data": [{"a": 3}],
            "meta": {"hasNextPage": False},
        })

    with _client(handler) as c:
        rows = list(c.query("pjm_load", start_time="s", end_time="e"))
    assert [r["a"] for r in rows] == [1, 2, 3]
    assert len(calls) == 2 and calls[1]["cursor"] == "C1"


def test_query_passes_filter_params():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"data": [], "meta": {"hasNextPage": False}})

    with _client(handler) as c:
        list(c.query(
            "pjm_lmp_real_time_5_min", start_time="s", end_time="e",
            filter_column="location_id", filter_value="35010365",
        ))
    assert seen["filter_column"] == "location_id"
    assert seen["filter_value"] == "35010365"
    assert seen["filter_operator"] == "="


def test_retry_on_429_then_success():
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(429, json={"detail": "Too Many Requests"})
        return httpx.Response(200, json={"data": [{"a": 1}], "meta": {"hasNextPage": False}})

    with _client(handler, backoff_base_s=0.0) as c:
        rows = list(c.query("pjm_load", start_time="s", end_time="e"))
    assert rows == [{"a": 1}] and attempts["n"] == 2


def test_retry_exhaustion_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with _client(handler, backoff_base_s=0.0, max_retries=2) as c:
        with pytest.raises(RuntimeError, match="after 2 retries"):
            list(c.query("pjm_load", start_time="s", end_time="e"))


def test_retry_on_transport_exception_then_success():
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.ReadTimeout("boom", request=request)
        return httpx.Response(200, json={"data": [{"a": 1}], "meta": {"hasNextPage": False}})

    with _client(handler, backoff_base_s=0.0) as c:
        rows = list(c.query("pjm_load", start_time="s", end_time="e"))
    assert rows == [{"a": 1}] and attempts["n"] == 2


def test_retry_exhaustion_on_transport_exception_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("boom", request=request)

    with _client(handler, backoff_base_s=0.0, max_retries=2) as c:
        with pytest.raises(RuntimeError, match="after 2 retries"):
            list(c.query("pjm_load", start_time="s", end_time="e"))


def test_redirects_not_followed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(307, headers={"location": "http://api.gridstatus.io/v1/x"})

    with _client(handler, backoff_base_s=0.0, max_retries=0) as c:
        with pytest.raises(httpx.HTTPStatusError):
            list(c.query("pjm_load", start_time="s", end_time="e"))


def test_get_api_usage_returns_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/api_usage"
        return httpx.Response(200, json={
            "plan_name": "Free",
            "limits": {"api_rows_returned_limit": 500_000},
            "current_period_usage": {"total_api_rows_returned": 10},
        })

    with _client(handler) as c:
        usage = c.get_api_usage()
    assert usage["plan_name"] == "Free"


def test_get_datasets_no_trailing_slash():
    def handler(request: httpx.Request) -> httpx.Response:
        # Trailing slash triggers a cleartext 307 on the real API; assert we never send it.
        assert request.url.path == "/v1/datasets"
        return httpx.Response(200, json={"data": [{"id": "pjm_load"}]})

    with _client(handler) as c:
        ds = c.get_datasets()
    assert ds[0]["id"] == "pjm_load"
