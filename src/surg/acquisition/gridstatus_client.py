"""Sync httpx wrapper for the gridstatus.io hosted API.

Mirrors `client.PJMClient` in shape. Facts encoded here come from
`docs/gridstatus-api-constraints.md`:
  - auth header `x-api-key`; base https://api.gridstatus.io/v1
  - NEVER follow redirects (the /datasets/ trailing-slash 307 downgrades
    to cleartext HTTP and would replay the api key)
  - server enforces 1 req/s -> self-pace >= 1.3 s
  - cursor pagination: loop while meta.hasNextPage, pass meta.cursor back
  - retriable statuses {429, 500, 502, 503, 504}, exponential backoff
  - >= 180 s read timeout for range pulls
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx

_BASE_URL = "https://api.gridstatus.io/v1"
_RETRIABLE = {429, 500, 502, 503, 504}


class GridStatusClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _BASE_URL,
        min_interval_s: float = 1.3,
        max_retries: int = 5,
        backoff_base_s: float = 2.0,
        timeout_s: float = 180.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._min_interval_s = min_interval_s
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._last_request_ts: float = 0.0
        self._client = httpx.Client(
            headers={"x-api-key": api_key, "Accept": "application/json"},
            timeout=timeout_s,
            transport=transport,
            follow_redirects=False,
        )

    def __enter__(self) -> "GridStatusClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def query(
        self,
        dataset: str,
        *,
        start_time: str,
        end_time: str,
        columns: str | None = None,
        filter_column: str | None = None,
        filter_value: str | None = None,
        page_size: int = 50_000,
    ) -> Iterator[dict[str, Any]]:
        """Yield rows of `dataset` for [start_time, end_time), cursor-paginating."""
        url = f"{self._base_url}/datasets/{dataset}/query"
        params: dict[str, Any] = {
            "start_time": start_time,
            "end_time": end_time,
            "page_size": page_size,
        }
        if columns is not None:
            params["columns"] = columns
        if filter_column is not None:
            params["filter_column"] = filter_column
            params["filter_value"] = filter_value
            params["filter_operator"] = "="

        cursor: str | None = None
        while True:
            q = dict(params)
            if cursor is not None:
                q["cursor"] = cursor
            payload = self._get_with_retry(url, q)
            yield from payload.get("data", [])
            meta = payload.get("meta", {})
            if not meta.get("hasNextPage"):
                return
            cursor = meta.get("cursor")

    def get_api_usage(self) -> dict[str, Any]:
        return self._get_with_retry(f"{self._base_url}/api_usage", {})

    def get_datasets(self) -> list[dict[str, Any]]:
        """List all dataset metadata. ~500 rows in one call — cache the result."""
        payload = self._get_with_retry(f"{self._base_url}/datasets", {})
        return payload.get("data", payload) if isinstance(payload, dict) else payload

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_request_ts = time.time()

    def _get_with_retry(self, url: str, params: dict[str, Any]) -> Any:
        attempt = 0
        while True:
            self._throttle()
            try:
                r = self._client.get(url, params=params)
            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt >= self._max_retries:
                    raise RuntimeError(
                        f"{exc!r} from gridstatus after {attempt} retries: "
                        f"url={url} params={params}"
                    ) from exc
                time.sleep(self._backoff_base_s * (2 ** attempt))
                self._last_request_ts = time.time()
                attempt += 1
                continue
            if r.status_code in _RETRIABLE:
                if attempt >= self._max_retries:
                    raise RuntimeError(
                        f"{r.status_code} from gridstatus after {attempt} retries: "
                        f"url={url} params={params}"
                    )
                time.sleep(self._backoff_base_s * (2 ** attempt))
                self._last_request_ts = time.time()
                attempt += 1
                continue
            r.raise_for_status()
            return r.json()
