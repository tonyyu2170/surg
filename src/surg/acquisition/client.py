"""Sync httpx wrapper for PJM Data Miner 2.

Encapsulates: subscription-key auth, JSON envelope unwrapping
(`items` + `totalRows`), pagination, the 6/min rate limit, and
exponential backoff on 429.

`download=true` / gzip handling is intentionally NOT used here for
pulls < ~50K rows — the JSON envelope is more readable for
debugging. A future helper can wrap `download=true` if/when we
ever need it for >50K-row pages.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

import httpx


_BASE_URL = "https://api.pjm.com/api/v1"


class PJMClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _BASE_URL,
        min_interval_s: float = 11.0,
        max_retries: int = 3,
        backoff_base_s: float = 2.0,
        timeout_s: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url
        self._min_interval_s = min_interval_s
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._last_request_ts: float = 0.0
        self._client = httpx.Client(
            headers={
                "Ocp-Apim-Subscription-Key": api_key,
                "Accept": "application/json",
            },
            timeout=timeout_s,
            transport=transport,
        )

    def __enter__(self) -> "PJMClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_feed(
        self,
        feed: str,
        params: dict[str, Any],
        *,
        page_size: int = 50_000,
        max_rows: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield rows for `feed` filtered by `params`, paginating as needed."""
        start = 1
        emitted = 0
        total: int | None = None
        url = f"{self._base_url}/{feed}"

        while True:
            q = {**params, "startRow": start, "rowCount": page_size}
            payload = self._get_with_retry(url, q)
            batch = payload.get("items", [])
            if total is None:
                total = payload.get("totalRows", len(batch))

            for row in batch:
                if max_rows is not None and emitted >= max_rows:
                    return
                yield row
                emitted += 1

            if not batch:
                return
            if max_rows is not None and emitted >= max_rows:
                return
            if emitted >= total:
                return
            start += len(batch)

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < self._min_interval_s:
            time.sleep(self._min_interval_s - elapsed)
        self._last_request_ts = time.time()

    def _get_with_retry(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        attempt = 0
        while True:
            self._throttle()
            r = self._client.get(url, params=params)
            if r.status_code == 429:
                if attempt >= self._max_retries:
                    raise RuntimeError(
                        f"429 from PJM after {attempt} retries: "
                        f"url={url} headers={dict(r.headers)}"
                    )
                wait = self._backoff_base_s * (2 ** attempt)
                time.sleep(wait)
                attempt += 1
                continue
            r.raise_for_status()
            return r.json()
