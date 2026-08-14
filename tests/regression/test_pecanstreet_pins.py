"""Pins production numbers from the 2026-08 pecanstreet runs.

A failure here after a code change is a real behavior change, not flakiness.

The pinned values come from the production run that produced
`outputs/pecanstreet/headroom_austin.json` (2026-08-14) and are the numbers
quoted in research note M. Two slices are pinned:

  * one home-month (dataid 661, July 2018) recomputed through the lib, which
    is the fast path and catches most arithmetic regressions;
  * the same home's full-bundle (calendar 2018) figures, which are what the
    note actually cites.

Both go through `mask_implausible(reconstruct_use(...))` rather than the raw
reconstruction, because that is what `scripts/pecanstreet_headroom.py` does
(its `clean_use` helper). dataid 661 carries no implausible readings, so the
mask is a no-op here -- but pinning the production path means a change to the
filter shows up as a failure rather than passing silently.
"""
from __future__ import annotations

import pandas as pd
import pytest

from scripts import pecanstreet_lib as pslib

pytestmark = pytest.mark.skipif(not pslib.RAW.exists(), reason="pecanstreet data not on disk")


@pytest.fixture(scope="module")
def austin_661() -> pd.DataFrame:
    """The Austin 1-min bundle restricted to dataid 661 (read once per module)."""
    df = pslib.read_power("austin", "1minute")
    return df[df["dataid"] == 661]


def _clean_use(df: pd.DataFrame) -> pd.Series:
    return pslib.mask_implausible(pslib.reconstruct_use(df))


def test_austin_661_july_2018_pins(austin_661: pd.DataFrame) -> None:
    ts = pd.DatetimeIndex(austin_661["ts"])
    july = austin_661[(ts.year == 2018) & (ts.month == 7)]
    m = pslib.headroom_metrics(_clean_use(july))
    assert m["n_minutes"] == 44640  # 31 days x 1440 min, no gaps
    assert m["max_kw"] == pytest.approx(10.209999999999999, rel=1e-6)
    assert m["p999_kw"] == pytest.approx(9.579, rel=1e-6)
    assert m["mean_kw"] == pytest.approx(2.6308815188172043, rel=1e-6)
    assert m["hostable_kw"]["200A"] == pytest.approx(28.190000000000005, rel=1e-6)


def test_austin_661_full_bundle_pins(austin_661: pd.DataFrame) -> None:
    """The full calendar-2018 figures, as cited in note M."""
    m = pslib.headroom_metrics(_clean_use(austin_661))
    assert m["n_minutes"] == 520550
    assert m["max_kw"] == pytest.approx(10.867, rel=1e-6)
    assert m["p99_kw"] == pytest.approx(6.216, rel=1e-6)
    assert m["p999_kw"] == pytest.approx(8.665902, rel=1e-6)
    assert m["mean_kw"] == pytest.approx(1.4921581308231677, rel=1e-6)
    assert m["hostable_kw"]["200A"] == pytest.approx(27.533000000000005, rel=1e-6)
    assert m["hostable_kw_noderate"]["200A"] == pytest.approx(37.132999999999996, rel=1e-6)


def test_implausible_filter_still_catches_the_known_meter_fault() -> None:
    """dataid 7536 emitted a 5308.7 kW reading on 2018-02-02 (leg voltages
    read -1.15 MV in the same rows). Exactly 2 rows corpus-wide exceed 48 kW,
    both from this home. If this stops holding, the filter or the data moved.
    """
    df = pslib.read_power("austin", "1minute")
    raw = pslib.reconstruct_use(df)
    masked = pslib.mask_implausible(raw)
    dropped = raw.notna() & masked.isna()
    assert int(dropped.sum()) == 2
    assert sorted(df.loc[dropped, "dataid"].unique().tolist()) == [7536]
    assert float(masked.max()) == pytest.approx(23.97, abs=0.01)
