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
    # so all fits succeed (includes total_lmp_rt_* for tail_risk_curves)
    for col in [
        "total_lmp_rt_cluster_mean",
        "system_energy_price_rt_cluster_mean",
        "marginal_loss_price_rt_cluster_mean",
        "congestion_price_rt_ashburn_tx1", "congestion_price_rt_ashburn_tx2",
        "total_lmp_rt_ashburn_tx1", "total_lmp_rt_ashburn_tx2",
        "congestion_price_rt_ox", "congestion_price_rt_bristers",
        "congestion_price_rt_dom_zonal",
        # Required by tail_risk_curves (total_lmp per negative-control pnode)
        "total_lmp_rt_ox", "total_lmp_rt_bristers", "total_lmp_rt_dom_zonal",
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
        components_n_boot=5,
        year_fe_n_boot=5,
        tail_risk_n_boot=5,
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
        # Sub-q1 closure item #2 — LMP-components decomposition
        out_root / "gpd_components" / "headline.json",
        out_root / "gpd_components" / "primary_cluster_supplementary.json",
        out_root / "gpd_components" / "cross_pnode.json",
        out_root / "gpd_components" / "threshold_sweep.json",
        # Sub-q1 closure item #3 — year-FE diagnostic per pnode + cross-pnode summary
        out_root / "year_fe_diagnostic" / "primary.json",
        out_root / "year_fe_diagnostic" / "total_lmp.json",
        out_root / "year_fe_diagnostic" / "ox.json",
        out_root / "year_fe_diagnostic" / "bristers.json",
        out_root / "year_fe_diagnostic" / "dom_zonal.json",
        out_root / "year_fe_diagnostic" / "ashburn_tx1.json",
        out_root / "year_fe_diagnostic" / "ashburn_tx2.json",
        out_root / "year_fe_diagnostic" / "cross_pnode_summary.json",
        # Sub-q1 closure item #4 — Ashburn diagnostic
        out_root / "ashburn_diagnostic" / "tx1_loo.json",
        out_root / "ashburn_diagnostic" / "tx2_loo.json",
        out_root / "ashburn_diagnostic" / "cross_threshold_summary.json",
        out_root / "ashburn_diagnostic" / "scatter_overlay.png",
        # Sub-q1 closure item #6 — direct Z → LMP tail-risk curves
        out_root / "tail_risk_curves" / "primary.json",
        out_root / "tail_risk_curves" / "cross_pnode_summary.json",
        out_root / "tail_risk_curves" / "primary.png",
    }
    for p in expected_paths:
        assert p.exists(), f"expected output not written: {p}"


# NOTE: A standalone test_run_all_writes_tail_risk_curves_outputs was removed
# 2026-05-15 after Task 8 review — its coverage is a strict subset of
# test_run_all_writes_all_outputs (above), which now plants the tail_risk_curves
# columns and asserts the tail_risk outputs as part of the same end-to-end run.


# ---------------------------------------------------------------------------
# Sub-q1 item #8 CLI extension tests
# ---------------------------------------------------------------------------


def test_arg_parser_accepts_seed_and_bootstrap_method():
    from surg.analysis.run import _build_arg_parser
    p = _build_arg_parser()
    args = p.parse_args(["--seed", "99", "--bootstrap-method", "cluster"])
    assert args.seed == 99
    assert args.bootstrap_method == "cluster"


def test_arg_parser_rejects_invalid_bootstrap_method():
    import pytest
    from surg.analysis.run import _build_arg_parser
    p = _build_arg_parser()
    with pytest.raises(SystemExit):
        p.parse_args(["--bootstrap-method", "garbage"])


def test_arg_parser_default_seed_and_bootstrap_method():
    from surg.analysis.run import _build_arg_parser
    args = _build_arg_parser().parse_args([])
    assert args.seed == 42
    assert args.bootstrap_method == "pair"


def test_arg_parser_accepts_all_new_skip_flags():
    from surg.analysis.run import _build_arg_parser
    p = _build_arg_parser()
    args = p.parse_args([
        "--skip-tar", "--skip-qr", "--skip-qr-full", "--skip-gpd",
        "--skip-mechanism", "--skip-robustness", "--skip-conditional-z",
        "--skip-gpd-continuous",
    ])
    assert args.skip_tar
    assert args.skip_qr
    assert args.skip_qr_full
    assert args.skip_gpd
    assert args.skip_mechanism
    assert args.skip_robustness
    assert args.skip_conditional_z
    assert args.skip_gpd_continuous


def test_arg_parser_tail_risk_pnodes_comma_split():
    from surg.analysis.run import _build_arg_parser
    args = _build_arg_parser().parse_args([
        "--tail-risk-pnodes", "primary,total_lmp,ox",
    ])
    assert args.tail_risk_pnodes == "primary,total_lmp,ox"


def test_run_all_skip_tar_does_not_create_tar_dir(tmp_path: Path):
    """skip_tar prevents the tar/ output dir from being created."""
    from surg.analysis.run import run_all

    panel = _make_panel_with_signal(n=2000)
    events = pd.DataFrame({
        "event_start_ept": pd.to_datetime(["2024-01-15T03:00:00"] * 2),
        "event_end_ept":   pd.to_datetime(["2024-01-15T05:30:00"] * 2),
        "duration": ["2.5 hours"] * 2,
    })
    out_root = tmp_path / "outputs"
    run_all(
        panel=panel, events=events, out_root=out_root,
        n_boot=5, n_subsample_reps=5, qr_full_n_boot=5,
        gpd_n_boot=5, continuous_n_boot=5, components_n_boot=5,
        year_fe_n_boot=5, tail_risk_n_boot=5,
        skip_tar=True, skip_qr=True, skip_qr_full=True, skip_gpd=True,
        skip_mechanism=True, skip_robustness=True,
        skip_conditional_z=True, skip_gpd_continuous=True,
        skip_gpd_components=True, skip_year_fe_diagnostic=True,
        skip_ashburn_diagnostic=True, skip_tail_risk_curves=True,
    )
    # All major output dirs should be absent
    for d in ("tar", "qr", "qr_full", "gpd", "mechanism", "robustness",
              "gpd_continuous", "gpd_components",
              "year_fe_diagnostic", "ashburn_diagnostic",
              "tail_risk_curves"):
        assert not (out_root / d).exists(), f"{d}/ should not exist"


def test_run_all_seed_threaded_to_modules(tmp_path: Path, monkeypatch):
    """Verify seed is plumbed through to module run_* calls (via spy)."""
    from surg.analysis import run as runmod

    captured: dict[str, int] = {}

    def _spy_year_fe(*args, **kwargs):
        captured["year_fe_seed"] = kwargs["seed"]

    def _spy_tail_risk(*args, **kwargs):
        captured["tail_risk_seed"] = kwargs["seed"]

    def _spy_continuous(*args, **kwargs):
        captured["continuous_seed"] = kwargs["seed"]

    def _spy_components(*args, **kwargs):
        captured["components_seed"] = kwargs["seed"]

    monkeypatch.setattr(runmod, "run_year_fe_diagnostic", _spy_year_fe)
    monkeypatch.setattr(runmod, "run_tail_risk_curves", _spy_tail_risk)
    monkeypatch.setattr(runmod, "run_gpd_continuous_z", _spy_continuous)
    monkeypatch.setattr(runmod, "run_gpd_components", _spy_components)
    # Stub out write_cross_pnode_summary so we can monkeypatch run_year_fe
    monkeypatch.setattr(runmod, "write_cross_pnode_summary", lambda *a, **k: None)

    panel = _make_panel_with_signal(n=200)
    for col in (
        "total_lmp_rt_cluster_mean", "system_energy_price_rt_cluster_mean",
        "marginal_loss_price_rt_cluster_mean",
        "congestion_price_rt_ashburn_tx1", "congestion_price_rt_ashburn_tx2",
        "total_lmp_rt_ashburn_tx1", "total_lmp_rt_ashburn_tx2",
        "congestion_price_rt_ox", "congestion_price_rt_bristers",
        "congestion_price_rt_dom_zonal",
    ):
        panel[col] = panel["congestion_price_rt_cluster_mean"].values

    runmod.run_all(
        panel=panel, events=pd.DataFrame(columns=["event_start_ept", "event_end_ept"]),
        out_root=tmp_path / "outputs",
        seed=99,
        # Skip everything we don't care about for seed plumbing
        skip_tar=True, skip_qr=True, skip_qr_full=True, skip_gpd=True,
        skip_mechanism=True, skip_robustness=True,
        skip_conditional_z=True,
        skip_ashburn_diagnostic=True,
    )
    assert captured.get("year_fe_seed") == 99
    assert captured.get("tail_risk_seed") == 99
    assert captured.get("continuous_seed") == 99
    assert captured.get("components_seed") == 99
# Keeping both doubled CI wall time for zero added coverage.
