from pathlib import Path

import pandas as pd
import pytest


def _seed_minimal_raw(data_root: Path) -> None:
    """Write minimal raw chunks (one hour worth) so build_analysis_panel can run."""
    # rt_hrl_lmps: 11 pnodes x 1 hour
    pnodes = [
        (35010365, "LOUDOUN"), (35010371, "PLEASANT VIEW"),
        (1356178195, "GOOSECRE"), (1356178171, "BRAMBLET"),
        (1356178181, "MOSBY"), (1356178201, "SKFFSCRK"),
        (34886139, "ASHBURN 35 KV TX1"), (34886141, "ASHBURN 35 KV TX2"),
        (35010369, "OX"), (62871513, "BRISTERS"),
        (34964545, "DOM"),
    ]
    rt_dir = data_root / "rt_hrl_lmps" / "2024"
    rt_dir.mkdir(parents=True)
    pd.DataFrame([
        {"datetime_beginning_ept": "2024-07-15T18:00:00",
         "pnode_id": pid, "pnode_name": name,
         "congestion_price_rt": 5.0 + (pid % 10),
         "total_lmp_rt": 50.0 + (pid % 10),
         "system_energy_price_rt": 30.0 + (pid % 10),
         "marginal_loss_price_rt": 1.0 + (pid % 10)}
        for pid, name in pnodes
    ]).to_parquet(rt_dir / "dom_targets__2024-07-15_to_2024-07-15.parquet")

    # hrl_load_metered: 2 hours of DOM load so gradient is computable
    load_dir = data_root / "hrl_load_metered" / "2024"
    load_dir.mkdir(parents=True)
    pd.DataFrame([
        {"datetime_beginning_ept": "2024-07-15T17:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 12000.0, "is_verified": True},
        {"datetime_beginning_ept": "2024-07-15T18:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 12120.0, "is_verified": True},
    ]).to_parquet(load_dir / "dom__2024-07-15_to_2024-07-15.parquet")

    # sync_reserve_events: empty (no events that day)
    ev_dir = data_root / "sync_reserve_events" / "2024"
    ev_dir.mkdir(parents=True)
    pd.DataFrame({
        "event_start_ept": pd.Series(dtype=object),
        "event_end_ept": pd.Series(dtype=object),
        "duration": pd.Series(dtype=object),
        "synchronized_reserve_zone": pd.Series(dtype=object),
        "synchronized_sub_zone": pd.Series(dtype=object),
    }).to_parquet(ev_dir / "mad__2024-07-15_to_2024-07-15.parquet")

    # reserve_market_results: 12 5-min rows x 2 services
    rmr_dir = data_root / "reserve_market_results" / "2024"
    rmr_dir.mkdir(parents=True)
    rmr_rows = []
    for service, base in [("SR", 100.0), ("PR", 30.0)]:
        for i in range(12):
            rmr_rows.append({
                "datetime_beginning_ept": f"2024-07-15T18:{i*5:02d}:00",
                "locale": "MAD", "service": service, "mcp": base + i,
            })
    pd.DataFrame(rmr_rows).to_parquet(rmr_dir / "mad__2024-07-15_to_2024-07-15.parquet")


def test_build_analysis_panel_produces_validated_panel(tmp_path: Path):
    from surg.preprocessing.build import build_analysis_panel
    from surg.preprocessing.schema import validate_panel, EXPECTED_COLUMNS

    _seed_minimal_raw(tmp_path)
    panel = build_analysis_panel(data_root=tmp_path)

    # Schema validation passes
    validate_panel(panel)
    # We seeded two hours of load (17:00 and 18:00); panel rows align to load hours.
    assert len(panel) == 2
    # Gradient at 18:00 is 12120 - 12000 = 120 MW/hr = 2 MW/min
    row18 = panel[panel["datetime_beginning_ept"] == pd.Timestamp("2024-07-15T18:00:00")].iloc[0]
    assert row18["dom_load_gradient_abs_mw_per_min"] == 2.0
    # Cluster mean exists and is reasonable (each of 6 pnodes has price 5+x)
    assert row18["congestion_price_rt_cluster_mean"] > 0
    # Reserve market columns present, hour 18 has aggregated mcps
    assert row18["sync_reserve_clearing_price_rt"] == 105.5  # 100+...+111 / 12
    assert row18["primary_reserve_clearing_price_rt"] == 35.5
    # July is not shoulder season
    assert row18["passes_proposal_filter"] is False or bool(row18["passes_proposal_filter"]) is False


def test_build_analysis_panel_writes_atomic_parquet(tmp_path: Path):
    """write_panel: tmp file + os.replace, no partial file on interruption."""
    from surg.preprocessing.build import build_analysis_panel, write_panel

    _seed_minimal_raw(tmp_path)
    panel = build_analysis_panel(data_root=tmp_path)
    out = tmp_path / "interim" / "analysis_panel.parquet"
    out.parent.mkdir(parents=True)

    write_panel(panel, out)

    assert out.exists()
    # No .tmp file lingers
    assert not (out.parent / "analysis_panel.parquet.tmp").exists()
    # Round-trip
    loaded = pd.read_parquet(out)
    assert len(loaded) == len(panel)


def test_write_panel_stamps_custom_schema_version(tmp_path: Path):
    """build_5min stamps FIVEMIN_SCHEMA_VERSION via write_panel(schema_version=...);
    the default stays the hourly SCHEMA_VERSION."""
    import pyarrow.parquet as pq

    from surg.preprocessing.build import write_panel
    from surg.preprocessing.schema import SCHEMA_VERSION

    df = pd.DataFrame({"x": [1, 2]})

    default_out = tmp_path / "default.parquet"
    write_panel(df, default_out)
    meta = pq.read_schema(default_out).metadata
    assert meta[b"schema_version"] == str(SCHEMA_VERSION).encode()

    custom_out = tmp_path / "custom.parquet"
    write_panel(df, custom_out, schema_version=42)
    meta = pq.read_schema(custom_out).metadata
    assert meta[b"schema_version"] == b"42"


def test_build_renames_system_energy_and_marginal_loss_for_labeled_pnodes(tmp_path: Path):
    from surg.preprocessing.build import build_analysis_panel
    _seed_minimal_raw(tmp_path)
    panel = build_analysis_panel(data_root=tmp_path)
    expected_labeled = ["ashburn_tx1", "ashburn_tx2", "ox", "bristers", "dom_zonal"]
    for lab in expected_labeled:
        assert f"system_energy_price_rt_{lab}" in panel.columns, (
            f"missing system_energy_price_rt_{lab}"
        )
        assert f"marginal_loss_price_rt_{lab}" in panel.columns, (
            f"missing marginal_loss_price_rt_{lab}"
        )
    assert "system_energy_price_rt_cluster_mean" in panel.columns
    assert "marginal_loss_price_rt_cluster_mean" in panel.columns
    # Also verify the new Ashburn total_lmp renames (added in this task for
    # item #4's scatter diagnostic).
    assert "total_lmp_rt_ashburn_tx1" in panel.columns
    assert "total_lmp_rt_ashburn_tx2" in panel.columns


def test_build_analysis_panel_clips_to_analysis_window(tmp_path: Path):
    """Panel excludes hours outside [ANALYSIS_WINDOW_START, ANALYSIS_WINDOW_END)."""
    from surg.preprocessing.build import (
        build_analysis_panel, ANALYSIS_WINDOW_START, ANALYSIS_WINDOW_END,
    )

    _seed_minimal_raw(tmp_path)
    # Append a 2021 load row (before the window starts 2022-10-02)
    load_dir = tmp_path / "hrl_load_metered" / "2021"
    load_dir.mkdir(parents=True)
    pd.DataFrame([
        {"datetime_beginning_ept": "2021-06-15T03:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 11_000.0, "is_verified": True},
    ]).to_parquet(load_dir / "dom__2021-06-15.parquet")

    # Upper-boundary probes: 2026-05-10 23:00 included; 2026-05-11 00:00 excluded.
    load_dir_2026 = tmp_path / "hrl_load_metered" / "2026"
    load_dir_2026.mkdir(parents=True)
    pd.DataFrame([
        {"datetime_beginning_ept": "2026-05-10T23:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 13_000.0, "is_verified": True},
        {"datetime_beginning_ept": "2026-05-11T00:00:00", "zone": "DOM",
         "load_area": "DOM", "mw": 13_010.0, "is_verified": True},
    ]).to_parquet(load_dir_2026 / "dom__2026-05-10_to_2026-05-11.parquet")

    panel = build_analysis_panel(data_root=tmp_path)
    assert (panel["datetime_beginning_ept"] >= ANALYSIS_WINDOW_START).all()
    assert (panel["datetime_beginning_ept"] < ANALYSIS_WINDOW_END).all()
    # The 2021 row is not in the panel
    assert not (panel["datetime_beginning_ept"] == pd.Timestamp("2021-06-15T03:00:00")).any()
    # 2026-05-10 23:00 is the LAST included hour (window end is exclusive at 05-11 00:00)
    assert (panel["datetime_beginning_ept"] == pd.Timestamp("2026-05-10T23:00:00")).any()
    # 2026-05-11 00:00 is excluded
    assert not (panel["datetime_beginning_ept"] == pd.Timestamp("2026-05-11T00:00:00")).any()
