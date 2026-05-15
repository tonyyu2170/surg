"""Cross-resolution summary builder for sub-q1 item #8.

Joins the 5-min joint-30d item-#6 (tail_risk_curves) outputs with the
matched-window hourly comparator outputs on (pnode, decile,
threshold). Writes outputs_5min/cross_resolution_summary.{json,csv}.

Like-for-like comparison: both sides use bootstrap_method=pair on the
same overlap window. The 5-min side adds cluster bootstrap (item
#8 design) but the resolution comparison only needs point estimates
(p_hat per decile per threshold) plus CIs.

Usage:
    python scripts/build_cross_resolution_summary.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIVEMIN_DIR = ROOT / "outputs_5min" / "joint_30d" / "tail_risk_curves"
HOURLY_DIR = ROOT / "outputs_5min" / "hourly_overlap_for_comparison" / "tail_risk_curves"
OUT_JSON = ROOT / "outputs_5min" / "cross_resolution_summary.json"
OUT_CSV = ROOT / "outputs_5min" / "cross_resolution_summary.csv"
OVERLAP_META = ROOT / "outputs_5min" / "hourly_overlap_for_comparison" / "overlap_window.json"


def _load_pnode_table(per_pnode_dir: Path, pnode_label: str) -> dict | None:
    """Return the per-pnode JSON or None if missing."""
    p = per_pnode_dir / f"{pnode_label}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _index_by_decile_threshold(pnode_json: dict) -> dict:
    """Flatten {results: {response_key: [{decile, by_threshold: {t: {...}}}]}}
    to {(response_key, decile, threshold) → metric_dict}."""
    out: dict[tuple[str, int, float], dict] = {}
    for resp_key, deciles in pnode_json["results"].items():
        for entry in deciles:
            decile = int(entry["decile"])
            for thr_str, metrics in entry["by_threshold"].items():
                thr = float(thr_str)
                out[(resp_key, decile, thr)] = metrics
    return out


def _build_summary() -> dict:
    overlap_meta = (
        json.loads(OVERLAP_META.read_text()) if OVERLAP_META.exists() else {}
    )
    summary = {
        "scope": "sub-q1 item #8 cross-resolution comparison",
        "overlap_window": overlap_meta,
        "pnodes": [],
    }

    fivemin_files = sorted(FIVEMIN_DIR.glob("*.json")) if FIVEMIN_DIR.exists() else []
    hourly_files = sorted(HOURLY_DIR.glob("*.json")) if HOURLY_DIR.exists() else []
    fivemin_labels = {p.stem for p in fivemin_files} - {"cross_pnode_summary"}
    hourly_labels = {p.stem for p in hourly_files} - {"cross_pnode_summary"}
    common = sorted(fivemin_labels & hourly_labels)

    for label in common:
        five = _load_pnode_table(FIVEMIN_DIR, label)
        hour = _load_pnode_table(HOURLY_DIR, label)
        if not (five and hour):
            continue
        five_idx = _index_by_decile_threshold(five)
        hour_idx = _index_by_decile_threshold(hour)
        common_keys = sorted(set(five_idx.keys()) & set(hour_idx.keys()))
        per_pnode_rows: list[dict] = []
        for k in common_keys:
            resp, decile, thr = k
            f = five_idx[k]
            h = hour_idx[k]
            per_pnode_rows.append({
                "response": resp,
                "decile": decile,
                "threshold": thr,
                "p_hat_5min": f["p_hat"],
                "p_hat_hourly": h["p_hat"],
                "delta_p_hat_5min_minus_hourly":
                    (f["p_hat"] - h["p_hat"])
                    if (f["p_hat"] is not None and h["p_hat"] is not None)
                    else None,
                "ci_5min": f.get("ci_95"),
                "ci_hourly": h.get("ci_95"),
            })
        summary["pnodes"].append({
            "pnode_label": label,
            "rows": per_pnode_rows,
        })

    return summary


def _write_csv(summary: dict, csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "pnode_label", "response", "decile", "threshold",
            "p_hat_5min", "p_hat_hourly", "delta_p_hat_5min_minus_hourly",
            "ci_5min_low", "ci_5min_high", "ci_hourly_low", "ci_hourly_high",
        ])
        for p in summary["pnodes"]:
            for row in p["rows"]:
                ci_5 = row["ci_5min"] or [None, None]
                ci_h = row["ci_hourly"] or [None, None]
                writer.writerow([
                    p["pnode_label"], row["response"], row["decile"], row["threshold"],
                    row["p_hat_5min"], row["p_hat_hourly"],
                    row["delta_p_hat_5min_minus_hourly"],
                    ci_5[0], ci_5[1], ci_h[0], ci_h[1],
                ])


def main() -> int:
    summary = _build_summary()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    _write_csv(summary, OUT_CSV)
    n_pnodes = len(summary["pnodes"])
    n_rows = sum(len(p["rows"]) for p in summary["pnodes"])
    print(f"wrote {OUT_JSON.name} ({n_pnodes} pnodes, {n_rows} (decile×threshold) rows)")
    print(f"wrote {OUT_CSV.name}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
