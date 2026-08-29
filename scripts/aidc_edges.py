"""Edge speed of the training-loop cycle in the rs-7943457 GPU telemetry.

Question it answers: the node's power cycle repeats only every 8 to 16
seconds (scripts/aidc_psd.py), but how fast is each transition inside the
cycle? Commissioned by the final-report review of 2026-08-28 (section 3.12
of docs/final_report.md, Table 11): the drop and the recovery in Figure 39
are much faster than the cycle that contains them.

For each baseline session: node power = the sum of the eight gpuN_power_W
channels; the middle 80% of the session (drops warm-up and the
end-of-session dropoff); high and low levels = the 90th and 10th
percentiles of node power; a fall is the time from the last sample above
90% of the swing to the first sample below 10% of it, a rise the reverse;
ramp rate = 80% of the swing divided by the edge time. The sensor refreshes
every ~103 ms, so an edge of about 0.1 s is "within one sensor refresh".

Usage: .venv/bin/python scripts/aidc_edges.py            (markdown table + outputs/aidc_edges.json)
       .venv/bin/python scripts/aidc_edges.py --selftest
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "aidc_workload"
OUT = ROOT / "outputs" / "aidc_edges.json"
SESSIONS = [
    ("B200 diffusion", "b200_diffusion_baseline.csv"),
    ("H100 diffusion", "h100_diffusion_baseline.csv"),
    ("B200 LLM (batch 16)", "b200_llm_baseline.csv"),
    ("H100 LLM (batch 16)", "h100_llm_baseline.csv"),
]


def edges(t, x):
    """10-to-90% fall and rise times (s) of a two-level signal.

    Returns (falls, rises, low, high). A partial dip that never reaches the
    low band is not an edge.
    """
    lo, hi = np.percentile(x, [10, 90])
    t10, t90 = lo + 0.1 * (hi - lo), lo + 0.9 * (hi - lo)
    falls, rises = [], []
    state, last_h, last_l = None, None, None
    for i, xi in enumerate(x):
        if xi > t90:
            if state == "L":
                rises.append(t[i] - t[last_l])
            state, last_h = "H", i
        elif xi < t10:
            if state == "H":
                falls.append(t[i] - t[last_h])
            state, last_l = "L", i
    return np.array(falls), np.array(rises), lo, hi


def load(path):
    df = pd.read_csv(path)
    ts = pd.to_datetime(df["timestamp"])
    cols = [c for c in df.columns if c.startswith("gpu") and c.endswith("_power_W")]
    x = df[cols].sum(axis=1).to_numpy()
    t = (ts - ts.iloc[0]).dt.total_seconds().to_numpy()
    n = len(x)
    sl = slice(n // 10, 9 * n // 10)  # middle 80%
    return t[sl], x[sl]


def summarize(name, t, x):
    falls, rises, lo, hi = edges(t, x)
    swing = hi - lo
    return {
        "session": name, "n_falls": len(falls), "n_rises": len(rises),
        "low_kW": lo / 1000, "high_kW": hi / 1000, "swing_kW": swing / 1000,
        "fall_median_s": float(np.median(falls)), "fall_p90_s": float(np.percentile(falls, 90)),
        "rise_median_s": float(np.median(rises)), "rise_p90_s": float(np.percentile(rises, 90)),
        "fall_rate_median_kW_per_s": 0.8 * swing / 1000 / float(np.median(falls)),
        "rise_rate_median_kW_per_s": 0.8 * swing / 1000 / float(np.median(rises)),
    }


def selftest():
    dt = 0.02
    t = np.arange(0, 120, dt)
    period, fall_dur, rise_dur, hi, lo = 12.0, 0.6, 1.4, 5000.0, 1000.0
    ph = t % period
    x = np.where(ph < 6.0, hi, lo).astype(float)
    m = (ph >= 6.0) & (ph < 6.0 + fall_dur)
    x[m] = hi - (hi - lo) * (ph[m] - 6.0) / fall_dur
    m = (ph >= 11.0 - rise_dur) & (ph < 11.0)
    x[m] = lo + (hi - lo) * (ph[m] - (11.0 - rise_dur)) / rise_dur
    x[ph >= 11.0] = hi
    falls, rises, _, _ = edges(t, x)
    assert len(falls) == len(rises) == 10, (len(falls), len(rises))
    assert abs(np.median(falls) - 0.8 * fall_dur) < 0.05, np.median(falls)
    assert abs(np.median(rises) - 0.8 * rise_dur) < 0.05, np.median(rises)
    print("selftest ok")


def main():
    if "--selftest" in sys.argv:
        return selftest()
    rows = [summarize(name, *load(RAW / fname)) for name, fname in SESSIONS]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, indent=2))
    print("| Session | cycles | swing (kW) | fall median / p90 (s) | rise median / p90 (s) | fall kW/s | rise kW/s |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['session']} | {r['n_falls']} | {r['low_kW']:.1f} to {r['high_kW']:.1f} ({r['swing_kW']:.1f}) "
              f"| {r['fall_median_s']:.2f} / {r['fall_p90_s']:.2f} | {r['rise_median_s']:.2f} / {r['rise_p90_s']:.2f} "
              f"| {r['fall_rate_median_kW_per_s']:.1f} | {r['rise_rate_median_kW_per_s']:.1f} |")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
