import pandas as pd
import pytest

from surg.preprocessing.entsoe_panel import build_zone_series, to_hourly


def _raw(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "zone", "item", "doc_start", "doc_end",
            "resolution", "curve_type", "position", "value",
        ],
    )


def test_expands_and_localizes_to_naive_local_prevailing():
    raw = _raw([
        ["IE_CTA", "load", "2024-01-08T00:00Z", "2024-01-08T02:00Z",
         "PT30M", "A03", 1, 3635.66],
        ["IE_CTA", "load", "2024-01-08T00:00Z", "2024-01-08T02:00Z",
         "PT30M", "A03", 3, 3469.86],
    ])
    out = build_zone_series(raw, zone_key="IE_CTA", value_name="load_mw")

    # 2 hours at PT30M = 4 slots; positions 1 and 3 emitted, so 1-2 and 3-4.
    assert len(out) == 4
    assert list(out["load_mw"]) == [3635.66, 3635.66, 3469.86, 3469.86]
    # January in Dublin is UTC+0, so naive local == UTC clock time.
    assert out["timestamp_local"].iloc[0] == pd.Timestamp("2024-01-08 00:00:00")
    assert out["timestamp_local"].dt.tz is None


def test_summer_localization_shifts_by_the_utc_offset():
    raw = _raw([
        ["NL", "load", "2024-07-15T00:00Z", "2024-07-15T01:00Z",
         "PT60M", "A03", 1, 12000.0],
    ])
    out = build_zone_series(raw, zone_key="NL", value_name="load_mw")
    # Amsterdam is UTC+2 in July.
    assert out["timestamp_local"].iloc[0] == pd.Timestamp("2024-07-15 02:00:00")


def test_hourly_derivation_averages_within_the_hour():
    raw = _raw([
        ["NL", "load", "2024-01-08T00:00Z", "2024-01-08T01:00Z",
         "PT15M", "A03", 1, 100.0],
        ["NL", "load", "2024-01-08T00:00Z", "2024-01-08T01:00Z",
         "PT15M", "A03", 3, 200.0],
    ])
    native = build_zone_series(raw, zone_key="NL", value_name="load_mw")
    hourly = to_hourly(native, value_name="load_mw")
    assert len(hourly) == 1
    # positions 1,2 = 100; positions 3,4 = 200 -> mean 150
    assert hourly["load_mw"].iloc[0] == 150.0


def test_dst_fall_back_hour_is_flagged():
    # 2024-10-27 Europe/Dublin falls back: local 01:00 occurs twice.
    raw = _raw([
        ["IE_CTA", "load", "2024-10-27T00:00Z", "2024-10-27T03:00Z",
         "PT60M", "A03", 1, 3000.0],
    ])
    native = build_zone_series(raw, zone_key="IE_CTA", value_name="load_mw")
    hourly = to_hourly(native, value_name="load_mw")
    assert hourly["dst_transition_hour"].sum() == 2


def test_ordinary_day_flags_no_dst_hours():
    raw = _raw([
        ["IE_CTA", "load", "2024-01-08T00:00Z", "2024-01-08T03:00Z",
         "PT60M", "A03", 1, 3000.0],
    ])
    hourly = to_hourly(
        build_zone_series(raw, zone_key="IE_CTA", value_name="load_mw"),
        value_name="load_mw",
    )
    assert hourly["dst_transition_hour"].sum() == 0


def test_exact_duplicate_document_rows_are_dropped():
    # 12.1.D returns whole local days, so a year-boundary day arrives from both
    # adjacent year requests and load_raw concatenates two identical copies.
    rows = [
        ["NL", "price", "2024-01-08T00:00Z", "2024-01-08T02:00Z",
         "PT60M", "A03", 1, 87.02],
        ["NL", "price", "2024-01-08T00:00Z", "2024-01-08T02:00Z",
         "PT60M", "A03", 2, 81.5],
    ]
    out = build_zone_series(_raw(rows + rows), zone_key="NL", value_name="price")
    assert list(out["price"]) == [87.02, 81.5]


def test_conflicting_duplicate_positions_still_raise():
    # Same position, DIFFERENT value is a real anomaly, not a re-fetch -- the
    # dedup must not swallow it.
    raw = _raw([
        ["NL", "price", "2024-01-08T00:00Z", "2024-01-08T02:00Z",
         "PT60M", "A03", 1, 87.02],
        ["NL", "price", "2024-01-08T00:00Z", "2024-01-08T02:00Z",
         "PT60M", "A03", 1, 99.99],
    ])
    with pytest.raises(ValueError, match="duplicate positions"):
        build_zone_series(raw, zone_key="NL", value_name="price")


def test_unknown_zone_raises():
    raw = _raw([
        ["NOPE", "load", "2024-01-08T00:00Z", "2024-01-08T01:00Z",
         "PT60M", "A03", 1, 1.0],
    ])
    with pytest.raises(KeyError):
        build_zone_series(raw, zone_key="NOPE", value_name="load_mw")


def test_incomplete_hour_is_counted_not_hidden():
    # Half an hour of PT15M data: 2 of the 4 slots the hour implies. The mean
    # is still 100.0 and looks entirely normal, so n_obs is the only signal.
    raw = _raw([
        ["NL", "load", "2024-01-08T00:00Z", "2024-01-08T00:30Z",
         "PT15M", "A03", 1, 100.0],
    ])
    hourly = to_hourly(
        build_zone_series(raw, zone_key="NL", value_name="load_mw"),
        value_name="load_mw",
    )
    assert hourly["n_obs"].iloc[0] == 2
    assert hourly["load_mw"].iloc[0] == 100.0


def test_complete_hour_reports_full_slot_count():
    raw = _raw([
        ["NL", "load", "2024-01-08T00:00Z", "2024-01-08T01:00Z",
         "PT15M", "A03", 1, 100.0],
    ])
    hourly = to_hourly(
        build_zone_series(raw, zone_key="NL", value_name="load_mw"),
        value_name="load_mw",
    )
    assert hourly["n_obs"].iloc[0] == 4
