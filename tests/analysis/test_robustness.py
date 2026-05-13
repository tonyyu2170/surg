import numpy as np
import pandas as pd


def test_subsample_bootstrap_returns_distribution_of_c_hats(tmp_path):
    from surg.analysis.robustness import subsample_bootstrap
    from tests.analysis.test_tar import _make_synthetic_tar
    from surg.preprocessing.schema import EXPECTED_COLUMNS

    df = pd.DataFrame({col: [None]*2000 for col in EXPECTED_COLUMNS})
    synth = _make_synthetic_tar(n=2001, c_true=2.0)
    df["dom_load_gradient_abs_mw_per_min"] = synth["Z"].values
    df["congestion_price_rt_cluster_mean"] = synth["Y"].values
    df["passes_proposal_filter"] = True
    df["datetime_beginning_ept"] = pd.date_range("2024-01-01", periods=2000, freq="h")

    out_path = tmp_path / "subsample_bootstrap.parquet"
    subsample_bootstrap(
        panel=df, out_path=out_path,
        n_reps=20, sample_frac=0.8, seed=42,
    )

    loaded = pd.read_parquet(out_path)
    assert len(loaded) == 20
    assert "c_hat" in loaded.columns
    # All bootstrap c_hats should be in a reasonable neighborhood of truth
    assert (loaded["c_hat"] - 2.0).abs().median() < 1.0
