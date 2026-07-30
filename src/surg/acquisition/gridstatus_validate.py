"""Post-pull validation gates for the gridstatus 5-min pull (design §2).

All gates must pass before the panel build; `main` exits non-zero on
any failure so the execution runbook can gate on it.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

LMP_IDENTITY_TOL = 0.011  # dollars; components are published to the cent
_SAMPLE_LIMIT = 5  # max example timestamps to surface per calendar mismatch


def _read_series(data_root: Path, dataset: str) -> pd.DataFrame:
    files = sorted((data_root / dataset).rglob("*.parquet"))
    if not files:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    df["interval_start_utc"] = pd.to_datetime(df["interval_start_utc"], utc=True)
    return df


def _calendar_check(present_ts, expected_set: set) -> dict:
    """Compare a series' actual timestamps against the expected calendar.

    Catches what a bare count comparison misses: right cardinality, wrong
    coverage (e.g. a chunk-boundary bug swaps an out-of-window timestamp
    in for a missing in-window one — nunique() alone wouldn't notice).
    """
    present = set(present_ts)
    missing = sorted(expected_set - present)
    extra = sorted(present - expected_set)
    return {
        "n_present": len(present),
        "n_missing": len(missing),
        "n_extra": len(extra),
        "missing_sample": [t.isoformat() for t in missing[:_SAMPLE_LIMIT]],
        "extra_sample": [t.isoformat() for t in extra[:_SAMPLE_LIMIT]],
    }


def validate_pull(
    data_root: Path,
    *,
    window_start: datetime,
    window_end: datetime,
    pnode_ids: tuple[int, ...],
) -> dict:
    """Run all gates; returns a report dict with per-gate pass/fail."""
    expected = pd.date_range(window_start, window_end, freq="5min",
                             inclusive="left", tz="UTC")
    n_expected = len(expected)
    expected_set = set(expected)

    load = _read_series(data_root, "pjm_load")
    lmp = _read_series(data_root, "pjm_lmp_real_time_5_min")

    gates: dict[str, dict] = {}

    # Gate 1: interval calendar coverage — load series and each pnode's LMP
    # series. Compares actual timestamp sets, not just counts: a series can
    # have the right cardinality but wrong coverage (e.g. an out-of-window
    # timestamp substituted for a missing in-window one), which a bare
    # nunique()==n_expected check would silently pass.
    interval_detail = {
        "pjm_load": _calendar_check(
            load["interval_start_utc"] if len(load) else [], expected_set),
    }
    for pid in pnode_ids:
        sub = lmp[lmp["location_id"] == pid] if len(lmp) else pd.DataFrame()
        interval_detail[f"lmp_{pid}"] = _calendar_check(
            sub["interval_start_utc"] if len(sub) else [], expected_set)
    gates["interval_count"] = {
        "passed": all(d["n_missing"] == 0 and d["n_extra"] == 0
                      for d in interval_detail.values()),
        "detail": {**interval_detail, "expected": n_expected},
    }

    # Gate 2: unique keys.
    load_dup = int(load.duplicated("interval_start_utc").sum()) if len(load) else 0
    lmp_dup = int(lmp.duplicated(["interval_start_utc", "location_id"]).sum()) if len(lmp) else 0
    gates["unique_keys"] = {
        "passed": load_dup == 0 and lmp_dup == 0,
        "detail": {"load_duplicates": load_dup, "lmp_duplicates": lmp_dup},
    }

    # Gate 3: LMP identity energy + congestion + loss == lmp (within tolerance).
    # A NaN in any component makes the identity unverifiable for that row —
    # treat it as a violation rather than letting `NaN > tol -> False` pass
    # it through silently.
    if len(lmp):
        resid = (lmp["energy"] + lmp["congestion"] + lmp["loss"] - lmp["lmp"]).abs()
        bad = resid.isna() | (resid > LMP_IDENTITY_TOL)
        n_bad = int(bad.sum())
        max_resid = float(resid.max())
    else:
        n_bad, max_resid = -1, float("nan")
    gates["lmp_identity"] = {
        "passed": n_bad == 0,
        "detail": {"n_violations": n_bad, "max_abs_residual": max_resid,
                   "tolerance": LMP_IDENTITY_TOL},
    }

    # Gate 4: pnode identity — exactly the requested location_ids, nothing else.
    found = set(int(x) for x in lmp["location_id"].unique()) if len(lmp) else set()
    gates["pnode_identity"] = {
        "passed": found == set(pnode_ids),
        "detail": {"found": sorted(found), "expected": sorted(pnode_ids)},
    }

    # Gate 5: nullness — dom and LMP components >= 99% non-null. Always
    # populate every expected key, even when a whole series is missing:
    # "no data to check" is a failure (100% null), not an omission that
    # would let `all(...)` vacuously pass over an incomplete dict.
    null_fracs: dict[str, float] = {
        "dom": float(load["dom"].isna().mean()) if len(load) else 1.0,
    }
    for col in ("lmp", "energy", "congestion", "loss"):
        null_fracs[col] = float(lmp[col].isna().mean()) if len(lmp) else 1.0
    gates["nullness"] = {
        "passed": all(v <= 0.01 for v in null_fracs.values()),
        "detail": null_fracs,
    }

    return {
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "expected_intervals": n_expected,
        "gates": gates,
        "passed": all(g["passed"] for g in gates.values()),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="surg-gridstatus-validate")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--data-root", default="data/raw/gridstatus")
    p.add_argument("--pnodes", default="35010365,35010371,1356178195")
    p.add_argument("--report-out", default="outputs/gridstatus_pull_validation.json")
    args = p.parse_args(argv)

    ws = datetime.fromisoformat(args.start.replace("Z", "+00:00")).astimezone(timezone.utc)
    we = datetime.fromisoformat(args.end.replace("Z", "+00:00")).astimezone(timezone.utc)
    pnodes = tuple(int(x) for x in args.pnodes.split(","))

    report = validate_pull(Path(args.data_root), window_start=ws, window_end=we,
                           pnode_ids=pnodes)
    out = Path(args.report_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    for name, gate in report["gates"].items():
        print(f"  [{'PASS' if gate['passed'] else 'FAIL'}] {name}: {gate['detail']}")
    if not report["passed"]:
        print("VALIDATION FAILED", file=sys.stderr)
        return 1
    print("validation passed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
