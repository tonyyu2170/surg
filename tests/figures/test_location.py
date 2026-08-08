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


def _fivemin_with_event(n=2000, seed=5):
    rng = np.random.default_rng(seed)
    t = pd.date_range("2024-07-10 00:00", periods=n, freq="5min")
    load = 20000 + rng.normal(0, 50, n)
    energy = np.full(n, 130.0) + rng.normal(0, 1, n)
    load[200:] -= 1500
    energy[200:] -= 80
    return pd.DataFrame({
        "datetime_beginning_ept": t,
        "dom_load_mw": load,
        "dom_load_gradient_abs_mw_per_min": np.abs(np.diff(load, prepend=load[0])) / 5,
        "system_energy_price_rt_cluster_mean": energy,
        "congestion_price_rt_cluster_mean": rng.gamma(1, 2, n),
        "total_lmp_rt_cluster_mean": energy + rng.gamma(1, 2, n),
    })


def _fivemin_with_traps(seed=6):
    # Two traps the plain fixture does not carry, both present in the real
    # panel: (1) a three-hour hole on the event day across which load falls
    # 3,000 MW -- a bare .diff() reads that as the day's largest "five-minute"
    # drop; (2) an excursion that snaps back one interval later, which is the
    # artifact signature decisions.md:4150 screens on.
    rng = np.random.default_rng(seed)
    t = pd.date_range("2024-07-10 00:00", periods=288, freq="5min")
    load = 20000 + rng.normal(0, 5, 288)
    energy = np.full(288, 130.0)
    load[136:] -= 3000.0        # the far side of the hole
    load[200:] -= 1600.0        # the real trip: bigger than the screen's
    energy[200:] -= 80.0        # threshold, and it never comes back
    keep = np.ones(288, bool)
    keep[100:136] = False       # punch the hole

    t2 = pd.date_range("2024-07-11 00:00", periods=288, freq="5min")
    load2 = 17000 + rng.normal(0, 5, 288)
    energy2 = np.full(288, 40.0)
    load2[50] -= 1800.0         # excursion...
    energy2[50] -= 2.0          # ...that reverts at index 51

    return pd.DataFrame({
        "datetime_beginning_ept": list(t[keep]) + list(t2),
        "dom_load_mw": list(load[keep]) + list(load2),
        "system_energy_price_rt_cluster_mean": list(energy[keep]) + list(energy2),
        "congestion_price_rt_cluster_mean": rng.gamma(1, 2, int(keep.sum()) + 288),
    })


def test_f10_locates_the_largest_drop():
    d = L.prepare_f10(_fivemin_with_event(), event_date="2024-07-10")
    assert d["drop_mw"] < -1000
    assert d["energy_before"] > d["energy_after"]


def test_f10_reports_the_price_response():
    d = L.prepare_f10(_fivemin_with_event(), event_date="2024-07-10")
    assert d["energy_drop_dollars"] > 0
    assert len(d["times"]) == len(d["load"]) == len(d["energy"])


def test_f10_ignores_drops_that_span_a_gap():
    # The hole's 3,000 MW step is the largest row-to-row fall on the day, but
    # it spans three hours. Ranking it as a five-minute drop would make panel
    # (a)'s title false.
    d = L.prepare_f10(_fivemin_with_traps(), event_date="2024-07-10")
    assert -1700 < d["drop_mw"] < -1500, d["drop_mw"]
    assert (d["event_time"].hour, d["event_time"].minute) == (16, 40)


def test_f10_screen_holds_only_reverting_excursions():
    d = L.prepare_f10(_fivemin_with_traps(), event_date="2024-07-10")
    assert len(d["screen"]) == 1, d["screen"]
    row = d["screen"][0]
    assert row["time"].date().isoformat() == "2024-07-11"
    assert row["drop_mw"] < -1500 and row["rebound_mw"] > 1500


def test_f10_screen_excludes_the_gap_and_the_event():
    # The gap row falls 3,000 MW and the trip falls 1,600 -- both clear the
    # 1,500 MW threshold, and neither belongs in a screen for artifacts.
    d = L.prepare_f10(_fivemin_with_traps(), event_date="2024-07-10")
    times = [r["time"] for r in d["screen"]]
    assert d["event_time"] not in times
    assert d["event_reverts"] is False
    assert all(t.date().isoformat() != "2024-07-10" for t in times)


def test_f10_annotation_quotes_the_screen_it_computed():
    d = L.prepare_f10(_fivemin_with_traps(), event_date="2024-07-10")
    text = L.prepare_f10_annotation(d)
    assert "$2.00" in text and "$80.00" in text


def test_f10_annotation_survives_an_empty_screen():
    d = L.prepare_f10(_fivemin_with_event(), event_date="2024-07-10")
    assert d["screen"] == []
    assert "no comparator" in L.prepare_f10_annotation(d)


def test_f10_rejects_a_date_outside_the_panel():
    try:
        L.prepare_f10(_fivemin_with_event(), event_date="2019-01-01")
    except ValueError as exc:
        assert "2019-01-01" in str(exc)
    else:
        raise AssertionError("missing date did not raise")


def test_f10_plot_writes_png(tmp_path):
    out = tmp_path / "F10.png"
    L.plot_f10(L.prepare_f10(_fivemin_with_event(), event_date="2024-07-10"), out)
    assert out.exists() and out.stat().st_size > 0
