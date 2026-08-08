import numpy as np
import pandas as pd

from scripts.figures import location as L


def _hourly(n=20000, seed=3):
    # n must carry the fixture past 2024-08-06, where Ashburn switches on --
    # 2022-10-02 plus 9,000 hours only reaches Oct 2023, leaving the column
    # all-NaN and the "common window" NaT.
    rng = np.random.default_rng(seed)
    t = pd.date_range("2022-10-02", periods=n, freq="h")
    base = rng.gamma(1.2, 8, n)
    df = pd.DataFrame({"datetime_beginning_ept": t})
    for p in ("ox", "bristers", "dom_zonal"):
        df[f"congestion_price_rt_{p}"] = base * rng.uniform(0.8, 1.2, n)
    # The six pnodes that actually compose cluster_mean on the real panel.
    for p in L.CLUSTER_6:
        df[f"congestion_price_rt_{p}"] = base * rng.uniform(0.8, 1.2, n)
    df["congestion_price_rt_cluster_mean"] = df[
        [f"congestion_price_rt_{p}" for p in L.CLUSTER_6]].mean(axis=1)
    hot = base * 3 + rng.gamma(2, 20, n)
    df["congestion_price_rt_ashburn_tx1"] = np.where(
        t >= pd.Timestamp("2024-08-06"), hot, np.nan)
    return df


def test_f7_common_window_starts_where_ashburn_starts():
    d = L.prepare_f7(_hourly())
    assert d["common_window_start"] == "2024-08-06"
    assert d["n_common"] < d["n_full"]


def test_f7_reports_both_windows_for_always_on_pnodes():
    d = L.prepare_f7(_hourly())
    row = d["rows"][L.SKFFSCRK]
    assert row["p99_common"] is not None
    assert row["p99_full"] is not None


def test_f7_ashburn_has_no_full_panel_value():
    d = L.prepare_f7(_hourly())
    assert d["rows"]["ashburn_tx1"]["p99_full"] is None


def test_f7_correlations_computed_on_common_window():
    d = L.prepare_f7(_hourly())
    m = d["correlation"]
    assert set(m["labels"]) <= set(d["rows"])
    arr = np.array(m["matrix"], float)
    assert np.allclose(np.diag(arr), 1.0, atol=1e-6)


def test_f7_carries_a_held_out_cluster():
    # decisions.md:4281 -- SKFFSCRK sits inside the 6-node cluster it is
    # correlated against, so part of that correlation is self-correlation.
    # The ruling requires the held-out 5-node figure beside the primary one.
    d = L.prepare_f7(_hourly())
    assert L.HELD_OUT_KEY in d["rows"], "no held-out cluster series"
    sc = d["self_correlation"]
    assert sc["primary"] > sc["held_out"], (
        "held-out correlation must be lower than the self-correlated one")
    assert sc["inflation"] > 0


def test_f7_held_out_cluster_actually_excludes_skffscrk():
    # A held-out series that still contained SKFFSCRK would silently defeat
    # the disclosure while passing every other test here.
    d = L.prepare_f7(_hourly())
    assert d["rows"][L.HELD_OUT_KEY]["p99_common"] != \
        d["rows"]["cluster_mean"]["p99_common"], \
        "held-out cluster is identical to the 6-node cluster"
    assert len(L.HELD_OUT_IDS) == 5
    assert L.SKFFSCRK not in L.HELD_OUT_IDS


def test_f7_does_not_call_skffscrk_a_control():
    # It is inside the cluster. Labelling it a control misstates the design.
    label = L.F7_PNODES[L.SKFFSCRK]
    assert "control" not in label.lower(), f"SKFFSCRK mislabelled: {label}"


def test_f7_plot_writes_png(tmp_path):
    out = tmp_path / "F7.png"
    L.plot_f7(L.prepare_f7(_hourly()), out)
    assert out.exists() and out.stat().st_size > 0
