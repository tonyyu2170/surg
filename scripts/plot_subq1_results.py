"""Thin orchestrator: regenerate the sub-q1 report figure set.

Each module is independently runnable; this runs them all. Expensive
statistics come from outputs/figure_inputs/ (see compute_figure_inputs.py)
and are never recomputed here.

Usage:
    python -m scripts.plot_subq1_results [--only F1,F7]

Run it as a module, not as a path. `scripts` is a package (it has an
__init__.py) and this file imports its siblings, so `python
scripts/plot_subq1_results.py` puts scripts/ rather than the repo root on
sys.path and dies with ModuleNotFoundError: No module named 'scripts'.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from scripts.figures import descriptive as D
from scripts.figures import inference as I
from scripts.figures import location as L
from scripts.figures import mechanism as M

FIGURES = [
    {"name": "F1",  "out": "F1_premise.png",            "resolution": "5-min"},
    {"name": "F2",  "out": "F2_load_vs_volatility.png", "resolution": "5-min"},
    {"name": "F3",  "out": "F3_prices_over_time.png",   "resolution": "5-min"},
    {"name": "F4",  "out": "F4_events_per_month.png",   "resolution": "5-min"},
    # by MONTH, not year: partial 2026 must never be annualised.
    {"name": "F4b", "out": "F4b_severity_by_month.png", "resolution": "5-min"},
    {"name": "F5",  "out": "F5_spec_sensitivity.png",   "resolution": "5-min"},
    {"name": "F6",  "out": "F6_effect_size.png",        "resolution": "5-min"},
    {"name": "F7",  "out": "F7_location.png",           "resolution": "hourly"},
    {"name": "F8",  "out": "F8_tail_risk_nofilter.png", "resolution": "5-min"},
    {"name": "F9",  "out": "F9_mechanism_tests.png",    "resolution": "hourly"},
    {"name": "F10", "out": "F10_nerc_event.png",        "resolution": "5-min"},
    {"name": "F11", "out": "F11_what_changed.png",      "resolution": "5-min"},
]

FIG_DIR = Path("outputs/figures")
INPUTS = Path("outputs/figure_inputs")
NOFILTER = Path("outputs/fivemin_nofilter/pooled/tail_risk_curves/cluster.json")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="plot-subq1-results")
    p.add_argument("--only", default="", help="comma-separated figure names")
    p.add_argument("--panel-5min", default="data/interim/analysis_panel_5min.parquet")
    p.add_argument("--panel-hourly", default="data/interim/analysis_panel.parquet")
    args = p.parse_args(argv)
    known = {f["name"] for f in FIGURES}
    want = {s.strip() for s in args.only.split(",") if s.strip()} or set(known)
    unknown = want - known
    if unknown:
        raise SystemExit(f"unknown figure(s): {sorted(unknown)}; "
                         f"known: {sorted(known)}")

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    # Read a panel only if some requested figure needs it, so --only F5 does
    # not fail on a machine that has the JSON inputs but not the parquet.
    five = hourly = None
    if want & {"F2", "F3", "F4", "F4b", "F10", "F11"}:
        five = pd.read_parquet(args.panel_5min)
    if "F7" in want:
        hourly = pd.read_parquet(args.panel_hourly)

    def out(name: str) -> Path:
        return FIG_DIR / next(f["out"] for f in FIGURES if f["name"] == name)

    if "F1" in want:
        D.plot_f1(D.prepare_f1(INPUTS / "monthly.json"), out("F1"))
    if "F2" in want:
        D.plot_f2(D.prepare_f2(five), out("F2"))
    if "F3" in want:
        D.plot_f3(D.prepare_f3(five), out("F3"))
    if "F4" in want:
        D.plot_f4(D.prepare_f4(five), out("F4"))
    if "F4b" in want:
        D.plot_f4b(D.prepare_f4b(five), out("F4b"))
    if "F5" in want:
        I.plot_f5(I.prepare_f5(INPUTS / "spec_sensitivity.json"), out("F5"))
    if "F6" in want:
        I.plot_f6(I.prepare_f6(INPUTS / "tau_sweep.json"), out("F6"))
    if "F7" in want:
        L.plot_f7(L.prepare_f7(hourly), out("F7"))
    if "F8" in want:
        M.plot_f8(M.prepare_f8(NOFILTER), out("F8"))
    if "F9" in want:
        M.plot_f9(M.prepare_f9(Path("outputs")), out("F9"))
    if "F10" in want:
        L.plot_f10(L.prepare_f10(five), out("F10"))
    if "F11" in want:
        M.plot_f11(M.prepare_f11(five), out("F11"))

    print(f"wrote figures to {FIG_DIR}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
