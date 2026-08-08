"""F5 (specification sensitivity) and F6 (effect size across quantiles).

Both read only from outputs/figure_inputs/*.json. Neither recomputes:
the bootstrap takes minutes and must stay reviewable as data.

Cross-cutting rule 8: no figure states a coefficient's sign without
showing the other specification, so both specs appear in both figures.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from scripts.figures import _style as S

PANEL_5MIN = "analysis_panel_5min.parquet"
SPECS = ("preregistered", "load_controlled")
SPEC_LABEL = {"preregistered": "pre-registered",
              "load_controlled": "load-controlled"}

# Spec is carried by colour, matching F5. Period has to be carried by marker
# and dash pattern: the real sweep holds five periods, and the drafted
# "pooled solid, everything else dashed" rule drew eight of ten lines
# identically.
PERIOD_STYLE = {
    "pooled": ("o", "-"),
    "2023": ("s", (0, (5, 2))),
    "2024": ("^", (0, (1, 1))),
    "2025": ("D", (0, (3, 1, 1, 1))),
    "2026": ("v", (0, (7, 1, 1, 1))),
}


def _period_style(period: str) -> tuple[str, object]:
    return PERIOD_STYLE.get(period, ("x", (0, (2, 2))))


def prepare_f5(spec_json: Path) -> dict:
    d = json.loads(Path(spec_json).read_text())
    if not d.get("rows"):
        raise ValueError(
            f"{Path(spec_json).name} has no rows; a bootstrap that died "
            "partway would otherwise plot as an empty forest, which reads "
            "as 'no sign reversals' -- the opposite of the finding")

    by_cell: dict[tuple[str, float], dict] = {}
    for r in d["rows"]:
        by_cell.setdefault((r["period"], r["tau"]), {})[r["spec"]] = r

    rows, reversals, significant = [], 0, 0
    for (period, tau), specs in by_cell.items():
        if not all(s in specs for s in SPECS):
            raise ValueError(
                f"cell {period} tau={tau} lacks both specifications; F5 may "
                "not state a sign without showing the other specification")
        pre, ctl = specs["preregistered"], specs["load_controlled"]
        flipped = np.sign(pre["z_slope"]) != np.sign(ctl["z_slope"])
        # A flip between two point estimates whose CIs both span zero is two
        # imprecise nulls, not a contradiction. Count the strict case apart,
        # so the caption cannot pass one off as the other.
        strict = bool(flipped
                      and S.excludes_zero(pre["ci_lo"], pre["ci_hi"])
                      and S.excludes_zero(ctl["ci_lo"], ctl["ci_hi"]))
        reversals += int(bool(flipped))
        significant += int(strict)
        rows.append({"period": period, "tau": tau,
                     "preregistered": pre, "load_controlled": ctl,
                     "sign_reversal": bool(flipped),
                     "significant_reversal": strict})
    rows.sort(key=lambda r: (r["period"], r["tau"]))
    return {"rows": rows, "n_sign_reversals": reversals,
            "n_significant_reversals": significant,
            "n_boot": d.get("n_boot"), "bootstrap": d.get("bootstrap"),
            "resolution": d.get("resolution", "5-min")}


def plot_f5(d: dict, out_path: Path) -> None:
    entries = []
    for r in d["rows"]:
        for spec in SPECS:
            e = r[spec]
            color = (S.COLOR["primary"] if spec == "preregistered"
                     else S.COLOR["total_lmp"])
            entries.append((f"{r['period']} τ={r['tau']:.2f} "
                            f"[{SPEC_LABEL[spec]}]",
                            e["z_slope"], e["ci_lo"], e["ci_hi"], color))

    fig, ax = plt.subplots(figsize=(9, max(6, 0.32 * len(entries))))
    S.forest(ax, entries, xlabel="z_slope (congestion $ per MW/min)",
             title="F5 — Same data, same bootstrap, opposite significant signs")
    # Each period has its own n, so quoting rows[0] would advertise 2023's
    # count as the whole figure's. Quote the pooled cell and say so.
    pooled = [r for r in d["rows"] if r["period"] == "pooled"]
    n_row = (pooled or d["rows"])[0]["preregistered"]
    footer = S.provenance(source=PANEL_5MIN, n=n_row["n"],
                          window="per-period (see labels); n is the pooled cell",
                          spec=f"QR, {d['bootstrap']} bootstrap, n_boot={d['n_boot']}",
                          resolution=d["resolution"])
    caption = (
        f"Sign reverses in {d['n_sign_reversals']} of {len(d['rows'])} "
        f"period × τ cells when load level is added as a control; in "
        f"{d['n_significant_reversals']} of those, both confidence intervals "
        f"exclude zero, which is the only subset where the reversal is more "
        f"than two imprecise estimates disagreeing. Filled "
        f"markers = CI excludes zero. APPENDIX FIGURE: the main text must "
        f"still state in plain language that the measured effect is small "
        f"and its sign depends on whether load level is controlled for. "
        + S.ARTIFACT_NOTE)
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)


def prepare_f6(tau_json: Path) -> dict:
    d = json.loads(Path(tau_json).read_text())
    series: dict[tuple[str, str], dict] = {}
    for r in d["rows"]:
        key = (r["period"], r["spec"])
        s = series.setdefault(key, {"tau": [], "shift_dollars": [],
                                    "shift_pct": [], "n": r["n"]})
        s["tau"].append(r["tau"])
        s["shift_dollars"].append(r["shift_dollars"])
        s["shift_pct"].append(r["shift_pct_of_baseline"])
    for s in series.values():
        order = np.argsort(s["tau"])
        for k in ("tau", "shift_dollars", "shift_pct"):
            s[k] = [s[k][i] for i in order]
    return {"series": series, "delta_z": d["delta_z_mw_per_min"],
            "resolution": d.get("resolution", "5-min")}


def plot_f6(d: dict, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
    for (period, spec), s in sorted(d["series"].items()):
        color = (S.COLOR["primary"] if spec == "preregistered"
                 else S.COLOR["total_lmp"])
        marker, dashes = _period_style(period)
        label = f"{period} [{SPEC_LABEL[spec]}]"
        kw = dict(color=color, marker=marker, ls=dashes, ms=4, lw=1.3,
                  label=label, alpha=0.9)
        axes[0].plot(s["tau"], s["shift_dollars"], **kw)
        axes[1].plot(s["tau"], s["shift_pct"], **kw)
    for ax, ylab, title in (
            (axes[0], "Implied shift ($)", "(a) In dollars"),
            (axes[1], "Implied shift (% of baseline)", "(b) Relative")):
        ax.axhline(0, color=S.MUTED, lw=1, ls="--")
        ax.set_xlabel("τ")
        ax.set_ylabel(ylab)
        ax.set_title(title)
    # Panel (b)'s upper right holds the 2024/2025 pre-registered lines; panel
    # (a)'s lower left is empty until the extreme tail.
    axes[0].legend(fontsize=7, ncol=2, loc="lower left", framealpha=0.9)

    fig.suptitle("F6 — Effect size across quantiles, both specifications", y=0.99)
    pooled_n = [s["n"] for (period, _), s in d["series"].items()
                if period == "pooled"]
    footer = S.provenance(source=PANEL_5MIN,
                          n=(pooled_n or [next(iter(d["series"].values()))["n"]])[0],
                          window="per-period (see legend); n is the pooled cell",
                          spec="QR implied shift over observed Z range",
                          resolution=d["resolution"])
    caption = (
        f"Shift implied by moving across the observed Z range "
        f"(Δ={d['delta_z']:.1f} MW/min, d1 median → d10 median). Colour is "
        f"the specification, marker and dash the period. This figure carries "
        f"no confidence intervals, so magnitudes must be read against F5's: "
        f"above τ≈0.97 each estimate rests on a handful of intervals per "
        f"period and the apparent growth is not established. Both "
        f"specifications are plotted because the sign of this effect depends "
        f"on whether load level is controlled for. "
        + S.ZONAL_DISCLOSURE + " " + S.ARTIFACT_NOTE)
    S.finish(fig, Path(out_path), footer=footer, caption=caption)
    plt.close(fig)
