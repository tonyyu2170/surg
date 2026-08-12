# scripts/entsoe_italy_stage1.py
"""Stage-1 level-vs-volatility horse race on the 7 Italian bidding zones.

ROBUSTNESS CHECK, NOT A FINDING. EU-0 section 1 argues European zones are
panels 12-13 of a result already in hand: level beat |gradient| in 11 of 11
panels including the near-zero-data-centre control. This exists because Italy
is the only European within-country price cross-section and the panel is a
near-free by-product of a corpus pulled for other reasons.

Italy is also the one place where a TSO-vs-Transparency-Platform load
disagreement would matter (Hirth et al. 2018 found >10% deviations). Terna is
NOT cross-checked here -- flagged as future work.

A COVERAGE REPORT runs before assert_panel_quality, because the Irish series
turned out to be 1.85% incomplete in 661 separate runs and the assertion alone
reports only a row-count mismatch. If the assertion fires, read the coverage
table first -- do NOT loosen the assertion, which exists because these exact
failure modes have bitten this project before.

Usage: .venv/bin/python scripts/entsoe_italy_stage1.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END,
    COMMON_OVERLAP_START,
    FAR_FUTURE,
    add_zone_gradients,
    assert_panel_quality,
    data_quality_report,
    level_vs_volatility,
    trend_tables,
)
from surg.preprocessing.entsoe_panel import zone_panel

FIGDIR = Path("outputs/entsoe/italy_stage1")

# IT_CALABRIA is EXCLUDED from the panel. It was split out of IT_SOUTH and
# only becomes a bidding zone on 2021-01-01: 6.1.A and 12.1.D both return
# reason 999 for 2015-2019, and 2020 carries a single stray row. Including it
# would force the cross-zone inner join down to 2021+, discarding six years
# from the other six zones, and would put a composition break mid-panel -- the
# same trap already documented elsewhere in this project. It is reported in
# the coverage table and then dropped, deliberately and visibly.
ZONES = [
    "IT_NORTH", "IT_CNORTH", "IT_CSOUTH", "IT_SOUTH",
    "IT_SICILY", "IT_SARDINIA",
]
LATE_ENTRANT = "IT_CALABRIA"
TIME_COL = "timestamp_local"


def coverage_report(hourly: dict[str, pd.DataFrame]) -> None:
    """Per-zone hourly completeness, before anything is merged or asserted."""
    print("\n=== ITALIAN COVERAGE (hourly, per zone) ===")
    rows = []
    for key, frame in hourly.items():
        stamps = frame["timestamp_utc"]
        expected = pd.date_range(stamps.min(), stamps.max(), freq="h", tz="UTC")
        missing = expected.difference(pd.DatetimeIndex(stamps))
        rows.append(
            {
                "zone": key,
                "rows": len(frame),
                "expected": len(expected),
                "missing": len(missing),
                "pct_missing": round(100 * len(missing) / len(expected), 3),
                "start": stamps.min(),
                "end": stamps.max(),
            }
        )
    print(pd.DataFrame(rows).to_string(index=False))


def build_panel() -> tuple[pd.DataFrame, list[str], list[str]]:
    """Join hourly load and price for every Italian zone on local time."""
    load_hourly, panel, price_cols = {}, None, []
    # Reported so the exclusion is visible in the log, then not merged.
    _, late = zone_panel("load", LATE_ENTRANT, value_name=f"load_mw_{LATE_ENTRANT}")
    load_hourly[f"{LATE_ENTRANT} (EXCLUDED)"] = late
    for key in ZONES:
        _, hourly = zone_panel("load", key, value_name=f"load_mw_{key}")
        load_hourly[key] = hourly
        # Join on timestamp_utc, NEVER on timestamp_local. Local prevailing
        # time repeats at the October fall-back, so it is not a unique key --
        # merging six zones on it cross-joins those hours (2^6 rows each) and
        # inflated the panel from 101,802 to 146,836 rows. UTC is unambiguous.
        block = hourly[["timestamp_utc", TIME_COL, f"load_mw_{key}", "dst_transition_hour"]]
        if panel is None:
            panel = block
        else:
            panel = panel.merge(
                block[["timestamp_utc", f"load_mw_{key}"]],
                on="timestamp_utc",
                how="inner",
            )

        _, price_hourly = zone_panel("price", key, value_name=f"price_{key}")
        panel = panel.merge(
            price_hourly[["timestamp_utc", f"price_{key}"]],
            on="timestamp_utc",
            how="left",
        )
        price_cols.append(f"price_{key}")

    coverage_report(load_hourly)
    panel = panel.sort_values("timestamp_utc").reset_index(drop=True)
    return panel, ZONES, price_cols


def main() -> None:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    panel, zones, price_cols = build_panel()
    panel = panel.dropna(subset=[f"load_mw_{z}" for z in zones]).reset_index(drop=True)
    print(f"\nmerged panel: {panel.shape}, {panel[TIME_COL].min()} -> {panel[TIME_COL].max()}")

    assert_panel_quality(panel, zones, time_col=TIME_COL, dst_pairs_per_year=1)
    panel = add_zone_gradients(panel, zones, time_col=TIME_COL)

    data_quality_report(
        panel, price_cols, time_col=TIME_COL,
        window_start=COMMON_OVERLAP_START, figdir=FIGDIR,
    )
    trend_tables(panel, zones, time_col=TIME_COL, figdir=FIGDIR, market="ITALY")
    for label, start, end in [
        ("max", panel[TIME_COL].min(), FAR_FUTURE),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(
            panel, zones, price_cols, time_col=TIME_COL,
            window_start=start, window_end=end,
            figdir=FIGDIR, market="ITALY", label=label,
        )


if __name__ == "__main__":
    main()
