from pathlib import Path

import numpy as np
import pandas as pd


def _make_panel_with_signal(n: int = 2000) -> pd.DataFrame:
    from surg.preprocessing.schema import EXPECTED_COLUMNS
    from tests.analysis.test_tar import _make_synthetic_tar

    df = pd.DataFrame({col: [None]*n for col in EXPECTED_COLUMNS})
    # synth has n-1 rows after dropna; n+1 input → exactly n rows of synth
    synth = _make_synthetic_tar(n=n+1, c_true=2.0)
    df["dom_load_gradient_abs_mw_per_min"] = synth["Z"].values
    df["congestion_price_rt_cluster_mean"] = synth["Y"].values
    df["passes_proposal_filter"] = True
    df["sync_reserve_event_active"] = (df["dom_load_gradient_abs_mw_per_min"] > 2.0)
    df["sync_reserve_clearing_price_rt"] = np.random.default_rng(7).uniform(0, 1500, n)
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=n, freq="h")
    return df


def test_run_all_writes_all_outputs(tmp_path: Path):
    from surg.analysis.run import run_all
    panel = _make_panel_with_signal(n=2000)
    events = pd.DataFrame({
        "event_start_ept": pd.to_datetime(["2024-01-15T03:00:00"] * 5),
        "event_end_ept":   pd.to_datetime(["2024-01-15T05:30:00"] * 5),
        "duration": ["2.5 hours"] * 5,
    })

    out_root = tmp_path / "outputs"
    # Plant the same TAR signal in the secondary + control response columns
    # so all fits succeed
    for col in [
        "total_lmp_rt_cluster_mean",
        "congestion_price_rt_ashburn_tx1", "congestion_price_rt_ashburn_tx2",
        "congestion_price_rt_ox", "congestion_price_rt_bristers",
        "congestion_price_rt_dom_zonal",
    ]:
        from tests.analysis.test_tar import _make_synthetic_tar
        synth_extra = _make_synthetic_tar(n=len(panel)+1, c_true=2.0,
                                          seed=abs(hash(col)) % 1000)
        panel[col] = synth_extra["Y"].values

    run_all(
        panel=panel,
        events=events,
        out_root=out_root,
        n_boot=30,  # fast
        n_subsample_reps=10,
        qr_full_n_boot=5,
        gpd_n_boot=5,
        continuous_n_boot=5,
    )
    expected_paths = {
        # Existing TAR (one per pnode)
        out_root / "tar" / "primary.json",
        out_root / "tar" / "total_lmp.json",
        out_root / "tar" / "ox.json",
        out_root / "tar" / "bristers.json",
        out_root / "tar" / "dom_zonal.json",
        out_root / "tar" / "ashburn_tx1.json",
        out_root / "tar" / "ashburn_tx2.json",
        # Existing QR / mechanism / robustness
        out_root / "qr" / "filtered_at_tar_c.json",
        out_root / "mechanism" / "validation.json",
        out_root / "robustness" / "subsample_bootstrap.parquet",
        # NEW: QR-full (one per pnode)
        out_root / "qr_full" / "primary.json",
        out_root / "qr_full" / "total_lmp.json",
        out_root / "qr_full" / "ox.json",
        out_root / "qr_full" / "bristers.json",
        out_root / "qr_full" / "dom_zonal.json",
        out_root / "qr_full" / "ashburn_tx1.json",
        out_root / "qr_full" / "ashburn_tx2.json",
        # NEW: GPD (one per pnode)
        out_root / "gpd" / "primary.json",
        out_root / "gpd" / "total_lmp.json",
        out_root / "gpd" / "ox.json",
        out_root / "gpd" / "bristers.json",
        out_root / "gpd" / "dom_zonal.json",
        out_root / "gpd" / "ashburn_tx1.json",
        out_root / "gpd" / "ashburn_tx2.json",
        # NEW: conditional-Z robustness battery
        out_root / "gpd" / "conditional_z_robustness.json",
        # NEW: Spec B continuous ξ(Z) regression (one per pnode + headline)
        out_root / "gpd_continuous" / "primary.json",
        out_root / "gpd_continuous" / "total_lmp.json",
        out_root / "gpd_continuous" / "ox.json",
        out_root / "gpd_continuous" / "bristers.json",
        out_root / "gpd_continuous" / "dom_zonal.json",
        out_root / "gpd_continuous" / "ashburn_tx1.json",
        out_root / "gpd_continuous" / "ashburn_tx2.json",
        out_root / "gpd_continuous" / "headline.json",
    }
    for p in expected_paths:
        assert p.exists(), f"expected output not written: {p}"
