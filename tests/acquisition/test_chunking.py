from datetime import date

import pytest

from surg.acquisition.chunking import date_chunks, pnode_batches


# ---------- date_chunks ----------

def test_single_chunk_within_calendar_year():
    chunks = list(date_chunks(date(2024, 3, 1), date(2024, 6, 30)))
    assert chunks == [(date(2024, 3, 1), date(2024, 6, 30))]


def test_splits_at_calendar_year_boundary():
    chunks = list(date_chunks(date(2024, 12, 1), date(2025, 2, 28)))
    assert chunks == [
        (date(2024, 12, 1),  date(2024, 12, 31)),
        (date(2025, 1, 1),   date(2025, 2, 28)),
    ]


def test_full_year_is_one_chunk():
    chunks = list(date_chunks(date(2024, 1, 1), date(2024, 12, 31), max_days=366))
    assert chunks == [(date(2024, 1, 1), date(2024, 12, 31))]


def test_multi_year_splits_per_calendar_year():
    chunks = list(date_chunks(date(2022, 1, 1), date(2024, 12, 31), max_days=366))
    assert chunks == [
        (date(2022, 1, 1), date(2022, 12, 31)),
        (date(2023, 1, 1), date(2023, 12, 31)),
        (date(2024, 1, 1), date(2024, 12, 31)),
    ]


def test_max_days_subdivides_within_year():
    # max_days=30: a 101-day inclusive window in one calendar year splits into 4
    chunks = list(date_chunks(date(2024, 1, 1), date(2024, 4, 10), max_days=30))
    # 30 + 30 + 30 + 11 = 101 days
    assert len(chunks) == 4
    assert chunks[0] == (date(2024, 1, 1),  date(2024, 1, 30))
    assert chunks[-1][1] == date(2024, 4, 10)
    # No chunk exceeds 30 days inclusive
    for s, e in chunks:
        assert (e - s).days + 1 <= 30


def test_single_day():
    chunks = list(date_chunks(date(2024, 5, 15), date(2024, 5, 15)))
    assert chunks == [(date(2024, 5, 15), date(2024, 5, 15))]


def test_end_before_start_raises():
    with pytest.raises(ValueError):
        list(date_chunks(date(2024, 5, 2), date(2024, 5, 1)))


# ---------- pnode_batches ----------

def test_pnode_batches_simple():
    assert list(pnode_batches([1, 2, 3, 4, 5], batch_size=2)) == [[1, 2], [3, 4], [5]]


def test_pnode_batches_exact_fit():
    assert list(pnode_batches([1, 2, 3, 4], batch_size=2)) == [[1, 2], [3, 4]]


def test_pnode_batches_single_batch_when_under_size():
    assert list(pnode_batches([1, 2, 3], batch_size=50)) == [[1, 2, 3]]


def test_pnode_batches_empty_input():
    assert list(pnode_batches([], batch_size=10)) == []


def test_pnode_batches_invalid_size():
    with pytest.raises(ValueError):
        list(pnode_batches([1, 2, 3], batch_size=0))


from datetime import datetime, timezone

from surg.acquisition.chunking import utc_datetime_chunks


def test_utc_datetime_chunks_half_open_contiguous():
    start = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
    end = datetime(2025, 8, 24, 4, tzinfo=timezone.utc)
    chunks = list(utc_datetime_chunks(start, end, days=30))
    assert chunks[0][0] == start
    assert chunks[-1][1] == end
    for (s1, e1), (s2, e2) in zip(chunks, chunks[1:]):
        assert e1 == s2  # contiguous, non-overlapping
    for s, e in chunks:
        assert (e - s).days <= 30


def test_utc_datetime_chunks_single_short_window():
    start = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
    end = datetime(2025, 6, 25, 4, tzinfo=timezone.utc)
    assert list(utc_datetime_chunks(start, end, days=30)) == [(start, end)]


def test_utc_datetime_chunks_rejects_reversed():
    start = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        list(utc_datetime_chunks(start, start, days=30))
