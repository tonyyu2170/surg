"""Tests for CAISO pure transforms."""
from __future__ import annotations

import pandas as pd
import pytest

from surg.preprocessing.caiso_features import TACS, parse_dam_lmp, parse_load


def load_row(start_gmt: str, tac: str, mw: float) -> dict:
    return {
        "INTERVALSTARTTIME_GMT": start_gmt,
        "TAC_AREA_NAME": tac,
        "MW": mw,
    }


def test_parse_load_converts_gmt_to_prevailing_pacific():
    raw = pd.DataFrame([load_row("2026-01-15T08:00:00-00:00", t, 100.0) for t in TACS])
    panel = parse_load(raw)
    # 08:00 GMT in January = 00:00 PST
    assert panel.loc[0, "datetime_beginning_ppt"] == pd.Timestamp("2026-01-15 00:00:00")
    assert panel.loc[0, "load_mw_caiso_total"] == 100.0


def test_parse_load_ignores_weim_areas():
    raw = pd.DataFrame(
        [load_row("2026-01-15T08:00:00-00:00", t, 100.0) for t in TACS]
        + [load_row("2026-01-15T08:00:00-00:00", "AZPS", 55.0)]
    )
    panel = parse_load(raw)
    assert not any("azps" in c for c in panel.columns)


def test_parse_load_flags_fallback_duplicate():
    # 2025-11-02: 01:00 PDT = 08:00 GMT and 01:00 PST = 09:00 GMT
    raw = pd.DataFrame(
        [load_row("2025-11-02T08:00:00-00:00", t, 100.0) for t in TACS]
        + [load_row("2025-11-02T09:00:00-00:00", t, 100.0) for t in TACS]
    )
    panel = parse_load(raw)
    assert len(panel) == 2
    assert panel["dst_transition_hour"].all()


def test_parse_dam_lmp_filters_lmp_rows_and_pivots():
    raw = pd.DataFrame(
        {
            "INTERVALSTARTTIME_GMT": ["2026-01-15T08:00:00-00:00"] * 2,
            "NODE": ["DLAP_PGAE-APND"] * 2,
            "LMP_TYPE": ["LMP", "MCC"],
            "MW": [51.7, -0.5],
        }
    )
    prices = parse_dam_lmp(raw)
    assert prices.loc[0, "da_lmp_dlap_pgae"] == 51.7
    assert prices.shape[1] == 2  # time + one node
