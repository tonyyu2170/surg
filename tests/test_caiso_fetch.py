"""Regression tests for the CAISO OASIS fetch script's retry/resilience logic.

No network: uses httpx.MockTransport to drive a real httpx.Client, matching
the pattern in tests/acquisition/test_client.py.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest

from scripts import caiso_fetch


@pytest.fixture(autouse=True)
def _reset_failed():
    """FAILED is a module-level list; don't let tests leak state into each other."""
    caiso_fetch.FAILED.clear()
    yield
    caiso_fetch.FAILED.clear()


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_pull_retries_read_timeout_then_succeeds(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, content=b"PK\x03\x04fake-zip-bytes")

    out = tmp_path / "chunk.zip"
    caiso_fetch.pull(_client(handler), {"a": 1}, out)

    assert calls["n"] == 2
    assert out.read_bytes() == b"PK\x03\x04fake-zip-bytes"
    assert caiso_fetch.FAILED == []


def test_pull_records_failure_and_does_not_raise_when_always_timing_out(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    out = tmp_path / "chunk.zip"
    caiso_fetch.pull(_client(handler), {"a": 1}, out)  # must not raise

    assert caiso_fetch.FAILED == [out.name]
    assert not out.exists()


def test_pull_skips_existing_nonempty_file_without_http_call(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, content=b"PK\x03\x04should-not-be-fetched")

    out = tmp_path / "chunk.zip"
    out.write_bytes(b"already here")

    caiso_fetch.pull(_client(handler), {"a": 1}, out)

    assert calls["n"] == 0
    assert out.read_bytes() == b"already here"
