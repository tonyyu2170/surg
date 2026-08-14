# scripts/pecanstreet_1sec.py
"""RQ3: residential fast volatility vs a DC-style oscillating node.

Usage:
  .venv/bin/python scripts/pecanstreet_1sec.py --city austin --sample        # eyeball first
  .venv/bin/python scripts/pecanstreet_1sec.py --city austin

Streams the 1-sec bundle files (never loads one whole); per home it
accumulates |delta| histograms at 1/10/60-s lags, top step events, and a
Welch PSD (fs=1 Hz -> Nyquist 0.5 Hz, which only grazes the bottom of the
0.1-30 Hz band in the NERC LLTF record -- stated plainly in note M). A city
aggregate is built second-by-second into preallocated arrays; aggregate
deltas are taken only between adjacent seconds with the same reporting
count (composition changes are not volatility); the
synchronization index Var(d_agg)/sum Var(d_i) distinguishes idiosyncratic
(~1, cancels like UKPN DC sites) from synchronized (~N) fast noise, and an
exact N-curve at 1-min resolution complements it. A synthetic XFRA node
(square wave, 90% amplitude, --node-kw sizes) is compared against the
measured natural-swing distributions.
"""
from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pecanstreet_lib as pslib

CHUNK = 2_000_000
# Preallocated aggregate spans (UTC epoch seconds), margins included.
AGG_SPAN = {
    "austin": (1514678400, 1546387200),     # 2017-12-31 .. 2019-01-02
    "new_york": (1556409600, 1572825600),   # 2019-04-28 .. 2019-11-04
}
MIN_HOMES_FOR_AGG = 20


def onesec_files(city: str) -> list:
    d = pslib.ELEC / pslib.CITY_DIR[city]
    return sorted(d.glob("1s_data_*file*.csv.gz"))


def stream_city(city: str, node_kws: list[float], sample: bool, outdir) -> dict:
    t0, t1 = AGG_SPAN[city]
    agg_sum = np.zeros(t1 - t0, dtype=np.float64)
    agg_cnt = np.zeros(t1 - t0, dtype=np.int16)
    homes: dict[int, dict] = {}
    n_implausible_masked = 0

    for path in onesec_files(city):
        header = pd.read_csv(path, nrows=0).columns
        assert "grid" in header, f"no grid column in {path.name}"
        gen_cols = [c for c in ("solar", "solar2") if c in header]
        usecols = ["dataid", "localminute", "grid", *gen_cols]
        print("streaming", path.name, flush=True)
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=CHUNK):
            ts = pd.to_datetime(chunk["localminute"], utc=True)
            # pandas 3 parses strings to datetime64[us]; NEVER astype()//10**9.
            epoch_all = ts.dt.as_unit("s").astype("int64").to_numpy()
            use_s = chunk["grid"].astype(float)
            for c in gen_cols:
                use_s = use_s + chunk[c].fillna(0.0)
            # C2: apply the corruption filter (this script builds `use`
            # inline, so it does not inherit mask_implausible for free).
            masked = pslib.mask_implausible(use_s)
            n_implausible_masked += int((masked.isna() & use_s.notna()).sum())
            use_all = masked.to_numpy()
            for dataid in chunk["dataid"].unique():
                m = (chunk["dataid"] == dataid).to_numpy()
                epoch, use = epoch_all[m], use_all[m]
                st = homes.setdefault(int(dataid), {
                    "hists": {lag: pslib.DeltaHist(lag) for lag in (1, 10, 60)},
                    "top": pslib.TopEvents(k=50),
                    "psd": pslib.PsdAccumulator(),
                    "n": 0,
                })
                st["n"] += len(use)
                for h in st["hists"].values():
                    h.update(epoch, use)
                st["top"].update(int(dataid), epoch, use)
                st["psd"].update(epoch, use)
                ok = (epoch >= t0) & (epoch < t1) & ~np.isnan(use)
                np.add.at(agg_sum, epoch[ok] - t0, use[ok])
                np.add.at(agg_cnt, epoch[ok] - t0, 1)
            if sample:
                break
        if sample:
            break

    # --- aggregate deltas over seconds where >= MIN_HOMES report, taken only
    # between adjacent seconds with the SAME reporting count: a composition
    # change adds a whole-home-sized jump (~1 kW) to a distribution whose real
    # 1-s median is ~0.01 kW. Equal counts kill all of that except the rare
    # exact swap (one home drops the same second another appears). The +2 bump
    # at each count change makes DeltaHist see a gap there; virtual epochs stay
    # strictly increasing, so the existing run-splitting does the rest.
    valid = agg_cnt >= MIN_HOMES_FOR_AGG
    idx = np.where(valid)[0]
    agg_hist = pslib.DeltaHist(lag_s=1)
    if len(idx):
        cnt = agg_cnt[idx]
        bumps = np.zeros(len(idx), dtype=np.int64)
        bumps[1:][(np.diff(idx) == 1) & (np.diff(cnt) != 0)] = 2
        agg_hist.update(idx + np.cumsum(bumps), agg_sum[idx])
    sum_var_i = sum(
        st["hists"][1].summary()["std_kw"] ** 2 for st in homes.values() if st["hists"][1].n
    )
    agg_summary = agg_hist.summary()
    sync_index = (agg_summary["std_kw"] ** 2 / sum_var_i) if sum_var_i else float("nan")

    # City top-50 = merge of the per-home top-50s (exact, and avoids feeding
    # one TopEvents accumulator rows from different homes back to back).
    top_city = sorted(
        (e for st in homes.values() for e in st["top"].result()),
        key=lambda e: -e["delta_kw"],
    )[:50]

    # C1: psd_figure() calls PsdAccumulator.result(), which flushes the
    # buffered final segment and increments n_segments, and is destructive
    # (clears the buffer). Must run BEFORE reading st["psd"].n_segments below,
    # and exactly once per home.
    psd_figure(city, homes, outdir)

    # C4: DeltaHist.quantile returns inf when the true quantile lies above
    # the histogram's 100 kW top bin edge -- a corrupt/saturated home. Flag
    # such homes; their percentiles must not be published.
    saturated_dataids = [
        did for did, st in homes.items()
        if any(np.isinf(h.summary()["p999_kw"]) for h in st["hists"].values() if h.n)
    ]

    result = {
        "city": city, "n_homes": len(homes),
        "per_home": {
            did: {
                "n_seconds": st["n"],
                "delta": {f"lag{lag}s": h.summary() for lag, h in st["hists"].items()},
                "top_events": st["top"].result()[:5],
                "psd_segments": st["psd"].n_segments,
            } for did, st in homes.items()
        },
        "aggregate": {"delta_1s": agg_summary, "sync_index": sync_index,
                      "n_valid_seconds": int(valid.sum()),
                      "min_homes_for_agg": MIN_HOMES_FOR_AGG,
                      "chunk_rows": CHUNK},  # C3: Welch PSD is chunking-dependent
        "top_events_city": top_city,
        "node_comparison": node_comparison(homes, agg_summary, node_kws),
        "n_implausible_masked": n_implausible_masked,  # C2
        "saturated_dataids": saturated_dataids,  # C4
    }
    return result


def node_comparison(homes: dict, agg_summary: dict, node_kws: list[float]) -> dict:
    """A square-wave node at 0.2 Hz swings NODE_AMPLITUDE*P twice per 5-s period."""
    p999 = [st["hists"][1].summary()["p999_kw"] for st in homes.values() if st["hists"][1].n]
    # C5: guard the empty-sample case (small --sample chunk can leave every
    # home with too few contiguous seconds for a lag-1 delta).
    if p999:
        median_p999 = float(np.median(p999))
        max_p999 = float(np.max(p999))
    else:
        median_p999 = float("nan")
        max_p999 = float("nan")
    out = {"home_natural_1s_p999_median_kw": median_p999,
           "home_natural_1s_p999_max_kw": max_p999,
           "aggregate_1s_std_kw": agg_summary["std_kw"], "nodes": {}}
    for p in node_kws:
        step = pslib.NODE_AMPLITUDE * p
        out["nodes"][f"{p:g}kW"] = {
            "step_kw": step,
            "vs_median_home_p999": step / median_p999,
            "n_homes_whose_max_natural_step_exceeds_it": int(
                sum(st["hists"][1].max >= step for st in homes.values())),
        }
    return out


def psd_figure(city: str, homes: dict, outdir) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for st in homes.values():
        freqs, psd = st["psd"].result()
        if len(freqs):
            ax.loglog(freqs[1:], psd[1:], lw=0.5, alpha=0.5)
    ax.axvspan(0.1, 0.5, alpha=0.15, color="red",
               label="overlap with DC 0.1-30 Hz band")
    ax.set(xlabel="Hz", ylabel="PSD (kW²/Hz)", title=f"{city}: per-home whole-home PSD")
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / f"onesec_psd_{city}.png", dpi=150)
    plt.close(fig)


def ncurve_1min(city: str, outdir, n_draws: int = 10, seed: int = 0) -> dict:
    """Exact sigma(delta) vs N at 1-min resolution (complement to sync_index)."""
    df = pslib.read_power(city, "1minute")
    df["use"] = pslib.mask_implausible(pslib.reconstruct_use(df))  # C2
    wide = df.pivot_table(index="ts", columns="dataid", values="use")
    deltas = wide.diff().dropna(how="all")
    rng = np.random.default_rng(seed)
    cols = list(deltas.columns)
    curve = {}
    for n in range(1, len(cols) + 1):
        sigmas = []
        for _ in range(n_draws):
            pick = rng.choice(cols, size=n, replace=False)
            sigmas.append(float(deltas[pick].sum(axis=1, min_count=n).std()))
        curve[n] = float(np.median(sigmas))
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ns = np.array(list(curve))
    ax.plot(ns, list(curve.values()), "o-", label="measured")
    ax.plot(ns, curve[1] * np.sqrt(ns), "--", label="sqrt(N) (independent)")
    ax.plot(ns, curve[1] * ns, ":", label="N (synchronized)")
    ax.set(xlabel="N homes", ylabel="sigma of aggregate 1-min delta (kW)", title=city)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / f"ncurve_1min_{city}.png", dpi=150)
    plt.close(fig)
    return curve


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", choices=list(AGG_SPAN), action="append")
    ap.add_argument("--sample", action="store_true", help="first chunk only: eyeball mode")
    ap.add_argument("--node-kw", default="1,5,6.25,12.5,19.2")
    ap.add_argument("--outdir", default=str(pslib.OUTDIR))
    args = ap.parse_args()
    outdir = pslib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    node_kws = [float(x) for x in args.node_kw.split(",")]

    for city in (args.city or list(AGG_SPAN)):
        result = stream_city(city, node_kws, args.sample, outdir)
        result["ncurve_1min"] = ncurve_1min(city, outdir) if not args.sample else None
        suffix = "_sample" if args.sample else ""
        (outdir / f"onesec_{city}{suffix}.json").write_text(json.dumps(result, indent=2))
        print(city, "sync_index:", result["aggregate"]["sync_index"],
              "| node table:", json.dumps(result["node_comparison"]["nodes"]))


if __name__ == "__main__":
    main()
