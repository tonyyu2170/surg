"""Unit tests for scripts/pecanstreet_lib.py. Synthetic data only — no data/ dependency."""
from __future__ import annotations

import gzip
import math

import numpy as np
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


def test_contiguous_runs_splits_on_gaps():
    epoch = np.array([100, 101, 102, 110, 111], dtype=np.int64)
    runs = pslib.contiguous_runs(epoch)
    assert [(s.start, s.stop) for s in runs] == [(0, 3), (3, 5)]


def test_delta_hist_exact_quantile_and_gap_exclusion():
    h = pslib.DeltaHist(lag_s=1)
    epoch = np.array([0, 1, 2, 10, 11], dtype=np.int64)
    use = np.array([1.0, 2.0, 4.0, 100.0, 100.5])
    h.update(epoch, use)
    # Deltas: |2-1|=1, |4-2|=2 within run 1; |100.5-100|=0.5 within run 2.
    # The 4->100 jump across the gap must NOT appear.
    assert h.n == 3
    assert h.max == pytest.approx(2.0)
    # quantile() returns the conservative UPPER edge of the bin holding the
    # true median 1.0: 10**(1/24) = 1.10069 (verified against the bin math —
    # rel=0.1 against 1.0 would fail by a hair, so pin the edge itself).
    assert h.quantile(0.5) == pytest.approx(1.1007, rel=0.01)


def test_delta_hist_split_feed_equals_whole_feed():
    """Chunk-boundary carry: feeding the series in two pieces == feeding it whole."""
    rng = np.random.default_rng(0)
    epoch = np.arange(1000, dtype=np.int64)
    use = rng.normal(2.0, 0.5, size=1000)
    whole = pslib.DeltaHist(lag_s=10)
    whole.update(epoch, use)
    split = pslib.DeltaHist(lag_s=10)
    split.update(epoch[:400], use[:400])
    split.update(epoch[400:], use[400:])
    assert split.n == whole.n
    assert split.counts.tolist() == whole.counts.tolist()


def test_delta_hist_no_valid_deltas_reports_nan_max_not_zero():
    """n == 0 (run shorter than lag) must be distinguishable from a genuinely flat home."""
    h = pslib.DeltaHist(lag_s=10)
    epoch = np.arange(5, dtype=np.int64)
    use = np.full(5, 3.0)
    h.update(epoch, use)
    summary = h.summary()
    assert summary["n"] == 0
    assert math.isnan(summary["max_kw"])

    flat = pslib.DeltaHist(lag_s=1)
    flat_epoch = np.arange(20, dtype=np.int64)
    flat_use = np.full(20, 3.0)
    flat.update(flat_epoch, flat_use)
    flat_summary = flat.summary()
    assert flat_summary["n"] == 19
    assert flat_summary["max_kw"] == 0.0


def test_delta_hist_quantile_saturates_to_inf_above_top_bin_edge():
    """Deltas above the 100 kW top bin edge are dropped from counts but not from n;
    quantile() must signal saturation with inf instead of silently clamping."""
    h = pslib.DeltaHist(lag_s=1)
    n = 10000
    epoch = np.arange(n + 20, dtype=np.int64)
    use = np.zeros(n + 20)
    # Small alternating deltas of 0.01 kW for the bulk of the series.
    use[1::2] = 0.01
    # Append 20 samples that each jump by 500 kW, well above the 100 kW top edge.
    for i in range(20):
        use[n + i] = 500.0 * (i + 1)
    h.update(epoch, use)
    summary = h.summary()
    assert summary["max_kw"] == pytest.approx(500.0)
    assert math.isinf(h.quantile(0.999))
    assert math.isfinite(h.quantile(0.5))


def test_top_events_keeps_largest():
    t = pslib.TopEvents(k=2)
    epoch = np.array([0, 1, 2, 3], dtype=np.int64)
    use = np.array([1.0, 5.0, 1.0, 9.0])  # |d| = 4, 4, 8
    t.update(dataid=42, epoch=epoch, use=use)
    top = t.result()
    assert len(top) == 2
    assert top[0]["delta_kw"] == pytest.approx(8.0)
    assert top[0]["dataid"] == 42


def test_psd_accumulator_finds_injected_frequency():
    fs, n = 1.0, 4096
    tt = np.arange(n) / fs
    x = np.sin(2 * np.pi * 0.1 * tt)  # 0.1 Hz tone
    acc = pslib.PsdAccumulator(nperseg=1024)
    acc.update(np.arange(n, dtype=np.int64), x)
    freqs, psd = acc.result()
    assert freqs[np.argmax(psd)] == pytest.approx(0.1, abs=0.005)


def test_psd_accumulator_nan_is_a_gap():
    """A NaN sample splits the segment (spec: gaps split spectral segments,
    no interpolation) -- it must never be dropped and spliced over."""
    use = np.random.default_rng(1).normal(size=2049)
    use[1024] = np.nan
    acc = pslib.PsdAccumulator(nperseg=1024)
    acc.update(np.arange(2049, dtype=np.int64), use)
    acc.result()
    assert acc.n_segments == 2  # two clean 1024-sample segments, no splice


def test_mask_implausible_nans_out_beyond_threshold():
    use = pd.Series([1.0, 150.0, -200.0, -3.0, np.nan])
    original = use.copy()
    masked = pslib.mask_implausible(use)
    assert masked.iloc[0] == pytest.approx(1.0)
    assert math.isnan(masked.iloc[1])
    assert math.isnan(masked.iloc[2])
    assert masked.iloc[3] == pytest.approx(-3.0)  # legitimate negative (solar export) survives
    assert math.isnan(masked.iloc[4])  # pre-existing NaN stays NaN
    pd.testing.assert_series_equal(use, original)  # input not mutated in place


def test_treated_dataids_excludes_enrolment_and_control():
    meta = pd.DataFrame({
        "dataid": [1, 2, 3, 4, 5],
        "program_energy_internet_demo": ["yes", np.nan, np.nan, np.nan, np.nan],
        "program_ccet_group": [np.nan, "CCET - Control", "CCET - Pricing Trial", np.nan, np.nan],
        "program_shines": [np.nan, np.nan, np.nan, "yes", np.nan],
    })
    assert pslib.treated_dataids(meta) == {3, 4}


def test_program_cols_partitioned_by_enrolment_and_treatment():
    enrolment = set(pslib.ENROLMENT_PROGRAM_COLS)
    treatment = set(pslib.TREATMENT_PROGRAM_COLS)
    assert enrolment | treatment == set(pslib.PROGRAM_COLS)
    assert enrolment & treatment == set()
