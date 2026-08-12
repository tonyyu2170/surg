import numpy as np
import pandas as pd
import pytest

from surg.preprocessing.entsoe_expand import expand_curve, resolution_minutes


def test_resolution_minutes_parses_the_three_observed_resolutions():
    assert resolution_minutes("PT15M") == 15
    assert resolution_minutes("PT30M") == 30
    assert resolution_minutes("PT60M") == 60


def test_resolution_minutes_rejects_unknown():
    with pytest.raises(ValueError, match="unsupported resolution"):
        resolution_minutes("PT7M")


def test_dense_series_expands_one_to_one():
    # 3 hours at PT60M, every position emitted.
    dense, sparsity = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T03:00Z"),
        resolution="PT60M",
        curve_type="A03",
        points=[(1, 10.0), (2, 20.0), (3, 30.0)],
    )
    assert np.array_equal(dense, np.array([10.0, 20.0, 30.0]))
    assert sparsity == 1.0


def test_flat_day_one_point_becomes_n_identical_values():
    # THE case that silently produces garbage gradients if mishandled.
    dense, sparsity = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-09T00:00Z"),
        resolution="PT60M",
        curve_type="A03",
        points=[(1, 500.0)],
    )
    assert len(dense) == 24
    assert np.all(dense == 500.0)
    assert sparsity == pytest.approx(1 / 24)


def test_gaps_forward_fill_until_the_next_emitted_position():
    # Positions 1,4,6 emitted over N=8: value holds until the next change.
    dense, _ = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T08:00Z"),
        resolution="PT60M",
        curve_type="A03",
        points=[(1, 1.0), (4, 2.0), (6, 3.0)],
    )
    assert np.array_equal(dense, np.array([1.0, 1.0, 1.0, 2.0, 2.0, 3.0, 3.0, 3.0]))


def test_last_emitted_value_holds_to_the_end():
    dense, _ = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T04:00Z"),
        resolution="PT60M",
        curve_type="A03",
        points=[(1, 7.0)],
    )
    assert np.array_equal(dense, np.array([7.0, 7.0, 7.0, 7.0]))


def test_a01_passthrough_requires_every_position():
    dense, sparsity = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T02:00Z"),
        resolution="PT60M",
        curve_type="A01",
        points=[(1, 4.0), (2, 5.0)],
    )
    assert np.array_equal(dense, np.array([4.0, 5.0]))
    assert sparsity == 1.0


def test_a01_with_missing_position_raises():
    with pytest.raises(ValueError, match="A01 document is not dense"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T03:00Z"),
            resolution="PT60M",
            curve_type="A01",
            points=[(1, 4.0), (3, 5.0)],
        )


def test_non_integer_span_raises():
    # 90 minutes does not divide into PT60M.
    with pytest.raises(ValueError, match="does not divide"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T01:30Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[(1, 1.0)],
        )


def test_position_beyond_n_raises():
    with pytest.raises(ValueError, match="exceeds dense length"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T02:00Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[(1, 1.0), (5, 2.0)],
        )


def test_missing_position_one_raises():
    # No opening value to forward-fill from -- must not silently backfill.
    with pytest.raises(ValueError, match="position 1"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T03:00Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[(2, 1.0), (3, 2.0)],
        )


def test_duplicate_positions_raise():
    # Stable sort puts duplicates adjacent, making the earlier one's fill an
    # empty slice -- its value would vanish silently. Must not be permissive.
    with pytest.raises(ValueError, match="duplicate positions"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T03:00Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[(1, 5.0), (1, 9.0), (3, 2.0)],
        )


def test_empty_points_raises():
    with pytest.raises(ValueError, match="no points"):
        expand_curve(
            start=pd.Timestamp("2024-01-08T00:00Z"),
            end=pd.Timestamp("2024-01-08T03:00Z"),
            resolution="PT60M",
            curve_type="A03",
            points=[],
        )


def test_dst_spring_forward_day_is_a_fixed_utc_span():
    # 2024-03-31 Europe/Dublin loses an hour locally, but the UTC span is
    # unchanged. Expansion is UTC-only; DST belongs to localization.
    dense, _ = expand_curve(
        start=pd.Timestamp("2024-03-31T00:00Z"),
        end=pd.Timestamp("2024-04-01T00:00Z"),
        resolution="PT30M",
        curve_type="A03",
        points=[(1, 100.0)],
    )
    assert len(dense) == 48


def test_real_captured_irish_response_shape():
    # Captured 2026-08-12: IE CTA, 2024-01-08T00:00Z..03:00Z, PT30M, 6 points.
    dense, sparsity = expand_curve(
        start=pd.Timestamp("2024-01-08T00:00Z"),
        end=pd.Timestamp("2024-01-08T03:00Z"),
        resolution="PT30M",
        curve_type="A03",
        points=[
            (1, 3635.66), (2, 3575.42), (3, 3469.86),
            (4, 3396.14), (5, 3336.9), (6, 3345.52),
        ],
    )
    assert len(dense) == 6
    assert dense[0] == 3635.66
    assert dense[-1] == 3345.52
    assert sparsity == 1.0
