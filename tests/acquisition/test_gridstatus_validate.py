"""Tests for post-pull validation gates. Synthetic chunk fixtures on tmp_path."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from surg.acquisition.gridstatus_validate import validate_pull
from surg.acquisition.storage import write_chunk

WINDOW_START = datetime(2025, 6, 24, 4, tzinfo=timezone.utc)
WINDOW_END = datetime(2025, 6, 24, 5, tzinfo=timezone.utc)  # 1 hour -> 12 intervals
PNODES = (35010365, 35010371)


def _intervals():
    return pd.date_range(WINDOW_START, WINDOW_END, freq="5min",
                         inclusive="left", tz="UTC")


def _write_load(tmp_path: Path, drop_last: bool = False):
    ts = _intervals()
    if drop_last:
        ts = ts[:-1]
    df = pd.DataFrame({
        "interval_start_utc": ts.astype(str),
        "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
        "dom": 11000.0,
    })
    write_chunk(tmp_path, "pjm_load", "dom",
                WINDOW_START.date(), WINDOW_END.date(), df)


def _write_lmp(tmp_path: Path, pid: int, break_identity: bool = False):
    ts = _intervals()
    energy, congestion, loss = 24.0, 1.0, 0.1
    lmp = energy + congestion + loss + (5.0 if break_identity else 0.0)
    df = pd.DataFrame({
        "interval_start_utc": ts.astype(str),
        "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
        "location": "X", "location_id": pid, "location_short_name": "X",
        "location_type": "AGGREGATE",
        "lmp": lmp, "energy": energy, "congestion": congestion, "loss": loss,
    })
    write_chunk(tmp_path, "pjm_lmp_real_time_5_min", str(pid),
                WINDOW_START.date(), WINDOW_END.date(), df)


def test_validate_passes_on_clean_pull(tmp_path: Path):
    _write_load(tmp_path)
    for pid in PNODES:
        _write_lmp(tmp_path, pid)
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is True
    assert report["expected_intervals"] == 12
    assert all(g["passed"] for g in report["gates"].values())


def test_validate_fails_on_missing_interval(tmp_path: Path):
    _write_load(tmp_path, drop_last=True)
    for pid in PNODES:
        _write_lmp(tmp_path, pid)
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is False
    assert report["gates"]["interval_count"]["passed"] is False


def test_validate_fails_on_lmp_identity_violation(tmp_path: Path):
    _write_load(tmp_path)
    _write_lmp(tmp_path, PNODES[0], break_identity=True)
    _write_lmp(tmp_path, PNODES[1])
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is False
    assert report["gates"]["lmp_identity"]["passed"] is False


def test_validate_fails_on_unexpected_pnode(tmp_path: Path):
    _write_load(tmp_path)
    _write_lmp(tmp_path, PNODES[0])
    _write_lmp(tmp_path, 99999)  # wrong pnode on disk
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is False
    assert report["gates"]["pnode_identity"]["passed"] is False


def test_validate_fails_interval_count_on_calendar_mismatch(tmp_path: Path):
    """Same cardinality (12 unique timestamps) but wrong calendar coverage:
    the last real in-window interval is dropped and replaced with one
    timestamp outside [window_start, window_end). A bare nunique()==12
    check would pass this; the gate must compare timestamp sets instead.
    """
    ts = list(_intervals()[:-1]) + [WINDOW_END + pd.Timedelta(minutes=5)]
    ts = pd.DatetimeIndex(ts)
    df = pd.DataFrame({
        "interval_start_utc": ts.astype(str),
        "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
        "dom": 11000.0,
    })
    write_chunk(tmp_path, "pjm_load", "dom",
                WINDOW_START.date(), WINDOW_END.date(), df)
    for pid in PNODES:
        _write_lmp(tmp_path, pid)

    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    assert report["passed"] is False
    gate = report["gates"]["interval_count"]
    assert gate["passed"] is False
    load_detail = gate["detail"]["pjm_load"]
    assert load_detail["n_present"] == 12
    assert load_detail["n_missing"] == 1
    assert load_detail["n_extra"] == 1


def test_validate_fails_on_lmp_identity_nan(tmp_path: Path):
    """A NaN identity component must fail lmp_identity even when it stays
    under the nullness gate's 1% threshold — resid.isna() must count as a
    violation, not silently pass via `NaN > tol -> False`. Uses a 24h/288
    interval window so a single NaN energy value is well under 1% of the
    combined pnode row count, isolating this from the nullness gate.
    """
    start = datetime(2025, 6, 24, 0, tzinfo=timezone.utc)
    end = datetime(2025, 6, 25, 0, tzinfo=timezone.utc)
    ts = pd.date_range(start, end, freq="5min", inclusive="left", tz="UTC")

    load_df = pd.DataFrame({
        "interval_start_utc": ts.astype(str),
        "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
        "dom": 11000.0,
    })
    write_chunk(tmp_path, "pjm_load", "dom", start.date(), end.date(), load_df)

    energy, congestion, loss = 24.0, 1.0, 0.1
    for i, pid in enumerate(PNODES):
        energy_col = pd.Series(energy, index=range(len(ts)))
        if i == 0:
            energy_col.iloc[0] = float("nan")
        df = pd.DataFrame({
            "interval_start_utc": ts.astype(str),
            "interval_end_utc": (ts + pd.Timedelta(minutes=5)).astype(str),
            "location": "X", "location_id": pid, "location_short_name": "X",
            "location_type": "AGGREGATE",
            "lmp": energy + congestion + loss,  # fixed value, not derived from energy_col
            "energy": energy_col, "congestion": congestion, "loss": loss,
        })
        write_chunk(tmp_path, "pjm_lmp_real_time_5_min", str(pid),
                    start.date(), end.date(), df)

    report = validate_pull(tmp_path, window_start=start, window_end=end,
                           pnode_ids=PNODES)
    assert report["gates"]["nullness"]["passed"] is True
    assert report["gates"]["lmp_identity"]["passed"] is False
    assert report["passed"] is False


def test_validate_fails_nullness_on_missing_lmp_series(tmp_path: Path):
    """No LMP chunks written at all (only load). The nullness gate itself
    must report passed: False with the LMP columns showing as fully null,
    rather than silently omitting them from its own check because `lmp`
    was empty.
    """
    _write_load(tmp_path)
    report = validate_pull(tmp_path, window_start=WINDOW_START,
                           window_end=WINDOW_END, pnode_ids=PNODES)
    gate = report["gates"]["nullness"]
    assert gate["passed"] is False
    assert gate["detail"]["lmp"] == 1.0
    assert gate["detail"]["energy"] == 1.0
    assert gate["detail"]["congestion"] == 1.0
    assert gate["detail"]["loss"] == 1.0
