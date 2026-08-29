"""F11 (what changed in 2026), F8 (no-filter tail risk), F9 (mechanism tests).

F11 exists to stop the rest of the figure set from being over-read: it is
the honest answer to the question F1 and F4b provoke.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.figures import _style as S

TIME_COL = "datetime_beginning_ept"
LOAD_COL = "dom_load_mw"
CONG_COL = "congestion_price_rt_cluster_mean"
PANEL_5MIN = "analysis_panel_5min.parquet"

BIN_WIDTH = 2000
MIN_SUPPORT = 30  # bins with fewer baseline obs are flagged unsupported


def _rate(cell: dict) -> float:
    """Exceedance as a fraction. An empty bin contributes nothing to a mean.

    Kept apart from the displayed `pct_gt_100`, which is NaN when the bin is
    empty: NaN is right for a line that must break, wrong for a weighted sum
    where the weight is already zero.
    """
    return 0.0 if not cell["n"] else cell["pct_gt_100"] / 100.0


def prepare_f11(panel: pd.DataFrame, *, threshold: float = 100.0) -> dict:
    t = pd.to_datetime(panel[TIME_COL])
    year = t.dt.year
    load = panel[LOAD_COL]

    lo = int(np.floor(load.min() / BIN_WIDTH) * BIN_WIDTH)
    hi = int(np.ceil(load.max() / BIN_WIDTH) * BIN_WIDTH)
    edges = list(range(lo, hi + BIN_WIDTH, BIN_WIDTH))
    labels = [f"{a//1000}-{b//1000} GW" for a, b in zip(edges, edges[1:])]
    binned = pd.cut(load, bins=edges, labels=labels, include_lowest=True)

    years = [str(y) for y in sorted(year.unique())]
    by_year_bin: dict[str, dict[str, dict]] = {}
    for y in years:
        sub = binned[year == int(y)]
        cong = panel.loc[year == int(y), CONG_COL]
        row = {}
        for lab in labels:
            m = (sub == lab).to_numpy()
            # An empty bin is unmeasured, not measured-zero. Reporting 0.0 here
            # would draw 2023 flat along the 24-26 GW bin it never reached,
            # which is the exact misreading this figure exists to prevent.
            row[lab] = {"pct_gt_100": float(100.0 * (cong[m] > threshold).mean())
                                      if m.any() else float("nan"),
                        "n": int(m.sum())}
        by_year_bin[y] = row

    base = years[0]
    base_rate = {lab: _rate(by_year_bin[base][lab]) for lab in labels}
    base_n = {lab: by_year_bin[base][lab]["n"] for lab in labels}
    unsupported = {lab for lab in labels if base_n[lab] < MIN_SUPPORT}

    actual, counterfactual, share = {}, {}, {}
    for y in years:
        row = by_year_bin[y]
        n_tot = sum(c["n"] for c in row.values())
        if not n_tot:
            continue
        act = sum(_rate(c) * c["n"] for c in row.values()) / n_tot
        cf = sum(base_rate[lab] * row[lab]["n"] for lab in labels) / n_tot
        actual[y] = 100.0 * act
        counterfactual[y] = 100.0 * cf
        share[y] = float(100.0 * cf / act) if act > 0 else float("nan")

    return {
        "years": years, "bin_labels": labels, "bin_edges": edges,
        "by_year_bin": by_year_bin,
        "actual_pct": actual, "counterfactual_pct": counterfactual,
        "load_growth_share_pct": share,
        "unsupported_bins": sorted(unsupported),
        "baseline_year": base, "threshold": threshold,
        "n": int(len(panel)),
        "window": f"{t.min():%Y-%m-%d} to {t.max():%Y-%m-%d}",
    }


def plot_f11(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    labels, x = d["bin_labels"], np.arange(len(d["bin_labels"]))
    palette = [S.COLOR["ox"], S.COLOR["bristers"], S.COLOR["dom_zonal"],
               S.COLOR["ashburn_tx1"], S.COLOR["total_lmp"]]
    for i, y in enumerate(d["years"]):
        vals = [d["by_year_bin"][y][lab]["pct_gt_100"] for lab in labels]
        axes[0].plot(x, vals, "o-", color=palette[i % len(palette)], label=y)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    axes[0].set_ylabel(f"P(congestion > ${d['threshold']:.0f}) (%)")
    axes[0].set_title("(a) Same load, different price")
    axes[0].legend(fontsize=8)

    # The baseline year's counterfactual equals its actual by construction
    # (share == 100%), so plotting it invites misreading. Drop it.
    ys = [y for y in d["actual_pct"] if y != d["baseline_year"]]
    xb = np.arange(len(ys), dtype=float)
    axes[1].bar(xb - 0.2, [d["actual_pct"][y] for y in ys], 0.4,
                color=S.COLOR["primary"], label="actual")
    axes[1].bar(xb + 0.2, [d["counterfactual_pct"][y] for y in ys], 0.4,
                color=S.COLOR["system_energy"],
                label=f"counterfactual ({d['baseline_year']} response)")
    for i, y in enumerate(ys):
        axes[1].annotate(f"{d['load_growth_share_pct'][y]:.0f}%",
                         (xb[i], max(d["actual_pct"][y],
                                     d["counterfactual_pct"][y])),
                         ha="center", va="bottom", fontsize=8)
    axes[1].set_xticks(xb)
    axes[1].set_xticklabels(ys)
    axes[1].set_ylabel(f"P(congestion > ${d['threshold']:.0f}) (%)")
    axes[1].set_title("(b) How much does load growth explain?")
    axes[1].legend(fontsize=8)

    fig.suptitle(f"{S.label('F11')} — What actually changed in 2026", y=0.99)
    footer = S.provenance(source=PANEL_5MIN, n=d["n"], window=d["window"],
                          spec=f"{BIN_WIDTH} MW load bins, "
                               f"{d['baseline_year']} baseline response",
                          resolution="5-min")
    caption = (
        "CAVEAT 1 — the counterfactual share is unreliable in magnitude: "
        f"{d['baseline_year']} barely visited the load levels later years "
        f"reach (bins with fewer than {MIN_SUPPORT} baseline observations, "
        f"flagged unsupported: {', '.join(d['unsupported_bins']) or 'none'}), "
        "so it extrapolates where it has no support. The direction is solid; "
        "the number is not. Panel (a) is the defensible version. "
        f"Panel (b) omits {d['baseline_year']}, whose counterfactual equals "
        "its actual by construction. "
        "CAVEAT 2 — the change is NOT local: it is a step change in January "
        "2026 in both congestion and system energy, and system energy is "
        "locationally uniform across PJM, so a substantial part of the 2026 "
        "escalation is system-wide rather than a data-center-alley "
        "congestion story. The driver is UNIDENTIFIED (cold snap, gas "
        "prices, PJM market-rule changes are all untested) and there is no "
        "non-DOM control pnode in this panel.")
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)


def _threshold_key(by_threshold: dict, threshold: str | float) -> str:
    """Match "100" against the run's "100.0" keys without string luck."""
    want = float(threshold)
    for k in by_threshold:
        if float(k) == want:
            return k
    raise KeyError(
        f"threshold {threshold!r} not among {sorted(by_threshold)}")


def prepare_f8(curve_json: Path, *, threshold: str = "100",
               response: str = "congestion") -> dict:
    d = json.loads(Path(curve_json).read_text())
    filt = d.get("filter", "")
    if "passes_proposal_filter" in filt:
        raise ValueError(
            f"F8 requires the no-filter run; this source has filter={filt!r}")
    if d.get("resolution") != "5-min":
        raise ValueError(
            f"F8 expects resolution '5-min'; got {d.get('resolution')!r}")

    # run_tail_risk_curves writes results[response] as a list of decile
    # records, each carrying by_threshold[<t>]{p_hat, n_exc, ci_95}. Read the
    # shape the run actually produces.
    rows = sorted(d["results"][response], key=lambda r: r["decile"])
    key = _threshold_key(rows[0]["by_threshold"], threshold)
    cells = [r["by_threshold"][key] for r in rows]
    prob = [float(c["p_hat"]) for c in cells]
    lo = [float(c["ci_95"][0]) for c in cells]
    hi = [float(c["ci_95"][1]) for c in cells]
    # MDE proxy: half-width of the widest CI, relative to the mean rate.
    mean_rate = float(np.mean(prob)) or float("nan")
    half = max((h - l) / 2.0 for l, h in zip(lo, hi))
    return {
        "deciles": [int(r["decile"]) for r in rows],
        "prob": prob, "ci_lo": lo, "ci_hi": hi,
        "threshold": key, "response": response,
        "mde_pct": float(100.0 * half / mean_rate),
        # The headline read on this curve, computed rather than transcribed.
        "d10_over_d1": (prob[-1] / prob[0]) if prob[0] else float("nan"),
        "n": int(d.get("n_total_filtered") or sum(d.get("decile_n_obs", [0]))),
        "n_boot": d.get("n_boot"),
        "filter": filt or "none (full panel)",
    }


def plot_f8(d: dict, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = d["deciles"]
    ax.plot(x, [100 * v for v in d["prob"]], "o-", color=S.COLOR["primary"])
    ax.fill_between(x, [100 * v for v in d["ci_lo"]],
                    [100 * v for v in d["ci_hi"]],
                    color=S.COLOR["primary"], alpha=0.18)
    ax.set_xlabel("Ramp (Z) decile")
    ax.set_ylabel(f"P({d['response']} > ${float(d['threshold']):,.0f}) (%)")
    ax.set_title(f"{S.label('F8')} — Tail-risk by volatility decile, no proposal filter")

    footer = S.provenance(source="outputs/fivemin_nofilter/pooled",
                          n=d["n"], window="full 3.4-year panel",
                          spec=f"tail-risk deciles, filter: {d['filter']}",
                          resolution="5-min")
    caption = (
        f"Top decile over bottom decile is {d['d10_over_d1']:.2f}. Each "
        f"decile's rate carries a 95% interval up to ±{d['mde_pct']:.1f}% of "
        f"the mean rate, wider than the 2–5% lift the volatility hypothesis "
        f"predicts, so a flat curve here is a NON-RESULT rather than a "
        f"refutation. (This is the per-decile precision; the recorded ±19% "
        f"figure is the resolution on the d10/d1 contrast, a different "
        f"quantity.) " + S.ARTIFACT_NOTE)
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)


SPEC_A_CAPTION = (
    "Spec A re-read: a heavier tail at LOW Z is what a level-driven "
    "constraint story predicts, because low-Z intervals are the "
    "sustained-load ones. This is not evidence for a volatility channel.")


def prepare_f9(out_root: Path) -> dict:
    root = Path(out_root)

    def _load(rel):
        return json.loads((root / rel).read_text())

    # Spec B publishes no `beta1`: the continuous xi(Z) slope is the SECOND
    # entry of `linear.shape_coefficients`, with its CI in the matching slot
    # of shape_coefficients_bootstrap_ci_95. Reading [0] would plot the
    # intercept (~0.9) where the slope (~-0.007) belongs.
    spec_b = []
    for e in _load("gpd_continuous/primary.json")["threshold_sweep"]:
        lin = e["linear"]
        spec_b.append({
            "quantile": float(e["threshold_quantile"]),
            "beta1": float(lin["shape_coefficients"][1]),
            "ci": [float(v) for v in
                   lin["shape_coefficients_bootstrap_ci_95"][1]],
            "converged": lin.get("convergence_status") == "converged",
            "n_exceedances": e.get("n_exceedances"),
        })
    spec_b.sort(key=lambda r: r["quantile"])

    # Likewise there is no `raw_by_year`/`year_fe_z_slope` pair. Layer 3 is
    # the trend test: secular component = primary_z_slope - year_fe_z_slope.
    yfe = _load("year_fe_diagnostic/primary.json")
    secular = []
    for key, v in yfe["layer3_secular_component_bootstrap"].items():
        secular.append({
            "tau": float(key.removeprefix("tau_")),
            "primary": float(v["primary_z_slope"]),
            "year_fe": float(v["year_fe_z_slope"]),
            "point": float(v["secular_component_point"]),
            "ci": [float(x) for x in v["secular_component_ci"]],
        })
    secular.sort(key=lambda r: r["tau"])

    return {
        # unwrap the nested block so callers see the statistics directly
        "conditional_z": _load("gpd/primary.json")["conditional_z"],
        "qr_full": _load("qr_full/primary.json"),
        "spec_b": spec_b,
        "secular": secular,
        "spec_a_caption": SPEC_A_CAPTION,
    }


def plot_f9(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    sd = d["conditional_z"]["shape_difference"]
    lo, hi = sd["bootstrap_ci_95"]
    S.forest(axes[0][0],
             [("ξ(high Z) − ξ(low Z)", sd["diff"], lo, hi, S.COLOR["primary"])],
             xlabel="GPD shape difference")
    axes[0][0].set_title("(a) Conditional-Z GPD (Spec A)")

    fits = sorted(d["qr_full"]["fits"], key=lambda f: f["tau"])
    taus = [f["tau"] for f in fits]
    slopes = [f["z_slope"] for f in fits]
    cis = [f["z_slope_bootstrap_ci_95"] for f in fits]
    axes[0][1].errorbar(
        taus, slopes,
        yerr=[[s - c[0] for s, c in zip(slopes, cis)],
              [c[1] - s for s, c in zip(slopes, cis)]],
        fmt="o-", color=S.COLOR["primary"], capsize=3)
    axes[0][1].axhline(0, color=S.MUTED, lw=1, ls="--")
    axes[0][1].set_xlabel("τ")
    axes[0][1].set_ylabel("z_slope")
    axes[0][1].set_title("(b) QR-full τ sweep")

    # The whole threshold sweep, not one row: the slope deepens to q=0.99 and
    # then flips at q=0.995 on a CI four times as wide -- a trajectory a
    # single quoted number hides.
    S.forest(axes[1][0],
             [(f"q={r['quantile']:g}" + ("" if r["converged"] else " (no conv.)"),
               r["beta1"], r["ci"][0], r["ci"][1], S.COLOR["total_lmp"])
              for r in d["spec_b"]],
             xlabel="β₁ of continuous ξ(Z)")
    axes[1][0].set_title("(c) Spec B — continuous ξ(Z) by threshold")
    # β₁ is O(0.01), so the default locator packs enough ticks that adjacent
    # labels ("-0.050", "-0.025") run together.
    axes[1][0].locator_params(axis="x", nbins=5)

    S.forest(axes[1][1],
             [(f"τ={r['tau']:g}  (primary {r['primary']:+.2f}, "
               f"year-FE {r['year_fe']:+.2f})",
               r["point"], r["ci"][0], r["ci"][1], S.COLOR["dom_zonal"])
              for r in d["secular"]],
             xlabel="secular component (primary − year-FE)")
    axes[1][1].set_title("(d) Secular component vs year fixed effects")

    fig.suptitle("F9 — Supporting mechanism tests (hourly)", y=0.99)
    footer = S.provenance(source="analysis_panel.parquet",
                          n=31608, window="2022-10-02 to 2026-05-10",
                          spec="conditional-Z / QR-full / Spec B / year-FE",
                          resolution="hourly")
    caption = (
        d["spec_a_caption"] + " Panels (c) and (d) are read the same way: "
        "a filled marker means the interval excludes zero.")
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)
