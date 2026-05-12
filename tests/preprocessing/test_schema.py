def test_schema_version_is_an_int():
    from surg.preprocessing.schema import SCHEMA_VERSION
    assert isinstance(SCHEMA_VERSION, int)
    assert SCHEMA_VERSION >= 1


def test_expected_columns_covers_all_design_columns():
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    # Identifiers & metadata
    must_have = {
        "datetime_beginning_ept",
        "in_shoulder_season",
        "in_2_5am_window",
        "passes_proposal_filter",
        "dst_transition_hour",
        # Load + volatility
        "dom_load_mw",
        "dom_load_gradient_mw_per_hr",
        "dom_load_gradient_abs_mw_per_min",
        "dom_load_gradient_signed_mw_per_min",
        # LMP — pooled and per-pnode controls
        "congestion_price_rt_cluster_mean",
        "congestion_price_rt_cluster_max",
        "total_lmp_rt_cluster_mean",
        "congestion_price_rt_ashburn_tx1",
        "congestion_price_rt_ashburn_tx2",
        "congestion_price_rt_ox",
        "congestion_price_rt_bristers",
        "congestion_price_rt_dom_zonal",
        # Reserves & events
        "sync_reserve_event_active",
        "sync_reserve_event_id",
        "hours_to_next_sync_event",
        "hours_since_last_sync_event",
        "sync_reserve_clearing_price_rt",
        "primary_reserve_clearing_price_rt",
    }
    assert must_have.issubset(set(EXPECTED_COLUMNS))


def test_validate_panel_accepts_dataframe_with_expected_columns():
    import pandas as pd
    from surg.preprocessing.schema import EXPECTED_COLUMNS, validate_panel

    df = pd.DataFrame({col: [None] for col in EXPECTED_COLUMNS})
    # Should not raise
    validate_panel(df)


def test_validate_panel_rejects_missing_columns():
    import pandas as pd
    import pytest
    from surg.preprocessing.schema import validate_panel

    df = pd.DataFrame({"datetime_beginning_ept": [None]})
    with pytest.raises(ValueError, match="missing expected columns"):
        validate_panel(df)
