"""Unit tests for scripts/pecanstreet_lib.py. Synthetic data only — no data/ dependency."""
from __future__ import annotations

import gzip
import math

import pandas as pd
import pytest

from scripts import pecanstreet_lib as pslib


def _write_gz_csv(path, text):
    with gzip.open(path, "wt") as f:
        f.write(text)


@pytest.fixture
def minute_csv(tmp_path):
    # Two homes: 100 has solar (one negative-use minute), 200 has no solar cols populated.
    text = (
        "dataid,localminute,air1,grid,solar,solar2,battery1\n"
        "100,2018-06-01 17:00:00-05,1.0,-0.5,2.0,,\n"
        "100,2018-06-01 17:01:00-05,1.0,-3.0,2.0,,\n"      # use = -1.0 -> negative
        "100,2018-06-01 17:02:00-05,1.0,0.5,2.0,,\n"
        "200,2018-06-01 17:00:00-05,,4.0,,,\n"
        "200,2018-06-01 17:02:00-05,,6.0,,,\n"              # 17:01 missing -> coverage 2/3
    )
    p = tmp_path / "1minute_data_austin.csv.gz"
    _write_gz_csv(p, text)
    return p


def test_read_power_parses_local_time(minute_csv):
    df = pslib.read_power_file(minute_csv, tz="America/Chicago")
    assert list(df.columns) == ["dataid", "ts", "grid", "solar", "solar2", "battery1"]
    assert str(df["ts"].dt.tz) == "America/Chicago"
    assert df["ts"].iloc[0].hour == 17  # -05 stamp in June == CDT == already local


def test_reconstruct_use_sums_grid_and_solar(minute_csv):
    df = pslib.read_power_file(minute_csv, tz="America/Chicago")
    use = pslib.reconstruct_use(df)
    assert use.iloc[0] == pytest.approx(1.5)   # -0.5 + 2.0
    assert use.iloc[3] == pytest.approx(4.0)   # grid only, NaN solar treated as 0


def test_negative_share_counts_negatives(minute_csv):
    df = pslib.read_power_file(minute_csv, tz="America/Chicago")
    use = pslib.reconstruct_use(df)
    assert pslib.negative_share(use) == pytest.approx(1 / 5)


def test_coverage_within_window(minute_csv):
    df = pslib.read_power_file(minute_csv, tz="America/Chicago")
    df["use"] = pslib.reconstruct_use(df)
    cov = pslib.coverage(df, freq_s=60)
    # Window = each home's own [min ts, max ts]; 100 has 3/3, 200 has 2/3.
    assert cov.loc[100] == pytest.approx(1.0)
    assert cov.loc[200] == pytest.approx(2 / 3)


def test_headroom_metrics_shape():
    load = pd.Series([1.0, 2.0, 3.0, 9.0, 2.0, 1.0, 1.0, 30.0, 2.0, 1.0])
    m = pslib.headroom_metrics(load)
    assert m["max_kw"] == 30.0
    # 200A scenario: 48 kW * 0.8 - 30 = 8.4 kW hostable (all-minutes definition)
    assert m["hostable_kw"]["200A"] == pytest.approx(8.4)
    # 100A scenario: 24 * 0.8 - 30 < 0 -> floored at 0
    assert m["hostable_kw"]["100A"] == 0.0
    # Un-derated variant (spec: with AND without the NEC 0.8): 48 - 30 = 18
    assert m["hostable_kw_noderate"]["200A"] == pytest.approx(18.0)


def test_headroom_metrics_all_nan_input():
    load = pd.Series([float("nan")] * 5)
    m = pslib.headroom_metrics(load)
    assert m["n_minutes"] == 0
    for key in ("hostable_kw", "hostable_p999_kw", "hostable_kw_noderate"):
        for scenario, value in m[key].items():
            assert math.isnan(value), f"{key}[{scenario}] should be NaN, got {value}"


def test_peak_window_mask_june_afternoon():
    ts = pd.DatetimeIndex(
        [
            "2018-06-15 15:00:00",  # in: Jun, 15h
            "2018-06-15 19:00:00",  # out: 19h is exclusive
            "2018-12-15 16:00:00",  # out: December
            "2018-09-01 18:59:00",  # in
        ]
    ).tz_localize("America/Chicago")
    mask = pslib.peak_window_mask(ts)
    assert mask.tolist() == [True, False, False, True]


def test_summer_exposure_complete_summer_is_one():
    full = pd.date_range(
        "2018-06-01", "2018-09-30 23:59:00", freq="min", tz="America/Chicago"
    )
    ts = full[pslib.peak_window_mask(full)]
    assert pslib.summer_exposure(ts) == pytest.approx(1.0)


def test_summer_exposure_eleven_august_days_is_small():
    full = pd.date_range(
        "2018-08-01", "2018-08-11 23:59:00", freq="min", tz="America/Chicago"
    )
    ts = full[pslib.peak_window_mask(full)]
    exposure = pslib.summer_exposure(ts)
    assert exposure == pytest.approx(11 / 122, abs=0.01)
    assert exposure < 0.90  # well below the gate; the exact regression case


def test_summer_exposure_empty_input_is_zero():
    assert pslib.summer_exposure(pd.DatetimeIndex([])) == 0.0
