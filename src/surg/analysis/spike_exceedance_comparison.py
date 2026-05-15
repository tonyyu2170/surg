"""5-min vs hourly spike-exceedance comparison (sub-q1 item #8 Part B).

Descriptive analysis: for each pnode and each $-threshold, compute
the hidden-fraction = fraction of 5-min exceedances that were NOT
visible in the PJM-published hourly aggregation. Decoupled from
Part A's joint Z+LMP analysis: this only needs LMP and runs over
the full 6-month archive.

Per-pnode metrics:
  - n_5min_exceedances: count of 5-min stamps with LMP > threshold
  - n_hourly_published_exceedances: count of hour buckets where the
    PJM-published hourly LMP exceeded threshold
  - n_hidden_by_hourly: count of hour buckets where ANY 5-min stamp
    in that hour exceeded threshold AND the hourly published value
    did NOT
  - hidden_fraction: n_hidden_by_hourly / (n_hourly buckets that
    contained ≥ 1 5-min exceedance)
                                 → NaN when no 5-min exceedances.
  - threshold_percentile: empirical percentile of `threshold` in the
    pnode's 5-min total_lmp_rt distribution (annotation, not part of
    the metric itself).

No bootstrap CIs (descriptive only — see design § 3.4).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from surg.analysis.tail_risk_curves import compute_threshold_percentiles


def compute_per_pnode_metrics(
    lmp_5min: pd.DataFrame,
    lmp_hourly: pd.DataFrame,
    *,
    pnode_id: int,
    thresholds: list[float],
) -> dict:
    """Compute per-pnode hidden-fraction metrics across thresholds.

    Joins 5-min and hourly on (pnode_id, hour_floor(timestamp)). Hours
    where the hourly panel has no row are dropped from numerator AND
    denominator and recorded in `n_dropped_unmatched_hours`.
    """
    sub_5 = lmp_5min[lmp_5min["pnode_id"] == pnode_id].copy()
    sub_h = lmp_hourly[lmp_hourly["pnode_id"] == pnode_id].copy()
    if sub_5.empty:
        return {
            "pnode_id": int(pnode_id),
            "n_5min_total": 0,
            "n_hourly_total": 0,
            "n_dropped_unmatched_hours": 0,
            "by_threshold": {
                float(t): {
                    "n_5min_exceedances": 0,
                    "n_hourly_buckets_with_5min_exc": 0,
                    "n_hourly_published_exceedances": 0,
                    "n_hidden_by_hourly": 0,
                    "hidden_fraction": float("nan"),
                    "n_below_inference_floor": True,
                    "threshold_percentile": float("nan"),
                }
                for t in thresholds
            },
        }

    sub_5["_hour_floor"] = sub_5["datetime_beginning_ept"].dt.floor("h")

    # Build hourly lookup by hour timestamp
    hourly_by_hour = sub_h.set_index("datetime_beginning_ept")["total_lmp_rt"]

    # Hours present in 5-min that are NOT in hourly (these get dropped)
    hours_in_5min = sub_5["_hour_floor"].unique()
    matched_hours = hourly_by_hour.index.intersection(pd.DatetimeIndex(hours_in_5min))
    n_dropped = int(len(hours_in_5min) - len(matched_hours))

    sub_5_matched = sub_5[sub_5["_hour_floor"].isin(matched_hours)]
    sub_h_matched = hourly_by_hour.loc[matched_hours]

    # Threshold percentiles annotation
    pct = compute_threshold_percentiles(
        sub_5_matched.rename(columns={"total_lmp_rt": "y"}), "y", thresholds
    )

    by_threshold: dict[float, dict] = {}
    for t in thresholds:
        t = float(t)
        # 5-min exceedance count
        is_exc_5 = (sub_5_matched["total_lmp_rt"] > t).to_numpy()
        n_5min_exc = int(is_exc_5.sum())

        # Hour buckets containing >= 1 5-min exceedance
        hours_with_5min_exc = (
            sub_5_matched.loc[is_exc_5, "_hour_floor"].unique()
            if n_5min_exc > 0 else np.array([])
        )
        n_hourly_buckets_with_5exc = int(len(hours_with_5min_exc))

        # Hourly published exceedance count (any hour, not just those with 5-min exc)
        n_hourly_published_exc = int((sub_h_matched > t).sum())

        # Hidden-by-hourly: hours where 5-min spiked but hourly did NOT exceed
        if n_hourly_buckets_with_5exc == 0:
            n_hidden = 0
            hidden_fraction = float("nan")
            below_floor = True
        else:
            hourly_at_those_hours = sub_h_matched.loc[
                pd.DatetimeIndex(hours_with_5min_exc)
            ]
            n_hidden = int((hourly_at_those_hours <= t).sum())
            hidden_fraction = n_hidden / n_hourly_buckets_with_5exc
            below_floor = False

        by_threshold[t] = {
            "n_5min_exceedances": n_5min_exc,
            "n_hourly_buckets_with_5min_exc": n_hourly_buckets_with_5exc,
            "n_hourly_published_exceedances": n_hourly_published_exc,
            "n_hidden_by_hourly": n_hidden,
            "hidden_fraction": hidden_fraction,
            "n_below_inference_floor": below_floor,
            "threshold_percentile": float(pct.get(t, float("nan"))),
        }

    return {
        "pnode_id": int(pnode_id),
        "n_5min_total": int(len(sub_5_matched)),
        "n_hourly_total": int(len(sub_h_matched)),
        "n_dropped_unmatched_hours": n_dropped,
        "by_threshold": by_threshold,
    }


def aggregate_cross_pnode_summary(per_pnode_results: list[dict]) -> dict:
    """Flatten per-pnode results into a cross-pnode summary."""
    if not per_pnode_results:
        return {"thresholds": [], "pnodes": []}
    thresholds = sorted(per_pnode_results[0]["by_threshold"].keys())
    rows: list[dict] = []
    for entry in per_pnode_results:
        row = {
            "pnode_id": entry["pnode_id"],
            "pnode_label": entry.get("pnode_label", str(entry["pnode_id"])),
            "n_5min_total": entry.get("n_5min_total", 0),
            "n_hourly_total": entry.get("n_hourly_total", 0),
        }
        for t in thresholds:
            m = entry["by_threshold"][t]
            row[f"hidden_fraction_at_{int(t)}"] = m["hidden_fraction"]
            row[f"n_5min_exc_at_{int(t)}"] = m["n_5min_exceedances"]
            row[f"n_hidden_at_{int(t)}"] = m["n_hidden_by_hourly"]
        rows.append(row)
    return {"thresholds": [float(t) for t in thresholds], "pnodes": rows}


def plot_hidden_fraction(per_pnode_dict: dict, out_path: Path) -> None:
    """Bar chart: hidden_fraction per threshold for one pnode."""
    import matplotlib.pyplot as plt
    thresholds = sorted(per_pnode_dict["by_threshold"].keys())
    fractions = [per_pnode_dict["by_threshold"][t]["hidden_fraction"]
                 for t in thresholds]
    pcts = [per_pnode_dict["by_threshold"][t]["threshold_percentile"]
            for t in thresholds]
    labels = [
        f"${int(t)} (p{p*100:.1f})" if not math.isnan(p) else f"${int(t)}"
        for t, p in zip(thresholds, pcts)
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    bar_x = list(range(len(thresholds)))
    bar_y = [0.0 if (f is None or math.isnan(f)) else f for f in fractions]
    bars = ax.bar(bar_x, bar_y, color="#2a6ea0")
    for x, f in zip(bar_x, fractions):
        if math.isnan(f):
            ax.text(x, 0.02, "NaN", ha="center", color="gray", fontsize=9)
    ax.set_xticks(bar_x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Hidden-by-hourly fraction")
    ax.set_title(
        f"pnode_id={per_pnode_dict['pnode_id']}: 5-min spikes hidden by hourly aggregation"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)


def _to_jsonable(obj):
    if isinstance(obj, dict):
        return {(str(k) if not isinstance(k, str) else k): _to_jsonable(v)
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(v) for v in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, np.floating):
        v = float(obj)
        return None if math.isnan(v) else v
    if isinstance(obj, (np.integer,)):
        return int(obj)
    return obj


def run_spike_exceedance_comparison(
    panel_5min: pd.DataFrame,
    panel_hourly: pd.DataFrame,
    *,
    out_root: Path,
    thresholds: list[float] | None = None,
) -> None:
    """Top-level orchestrator: per-pnode metrics + cross-pnode summary +
    per-pnode plots. Writes under `out_root/spike_exceedance_comparison/`."""
    if thresholds is None:
        thresholds = [50, 100, 250, 500, 1000]

    out_dir = Path(out_root) / "spike_exceedance_comparison"
    out_dir.mkdir(parents=True, exist_ok=True)

    pnode_ids = sorted(panel_5min["pnode_id"].unique().tolist())
    per_pnode_results: list[dict] = []
    for pid in pnode_ids:
        result = compute_per_pnode_metrics(
            panel_5min, panel_hourly,
            pnode_id=int(pid),
            thresholds=thresholds,
        )
        per_pnode_results.append(result)
        with open(out_dir / f"pnode_{pid}.json", "w") as f:
            json.dump(_to_jsonable(result), f, indent=2)
        try:
            plot_hidden_fraction(result, out_dir / f"pnode_{pid}.png")
        except Exception as e:
            print(f"plot failed for pnode {pid}: {e}")

    summary = aggregate_cross_pnode_summary(per_pnode_results)
    with open(out_dir / "cross_pnode_summary.json", "w") as f:
        json.dump(_to_jsonable(summary), f, indent=2)

    # Cross-pnode summary CSV
    csv_path = out_dir / "cross_pnode_summary.csv"
    if summary["pnodes"]:
        fieldnames = list(summary["pnodes"][0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in summary["pnodes"]:
                # Sanitize NaN to "" for CSV
                clean = {
                    k: ("" if isinstance(v, float) and math.isnan(v) else v)
                    for k, v in row.items()
                }
                writer.writerow(clean)
