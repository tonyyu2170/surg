"""Scale the 8-GPU node's step to a synchronized training job.

Question it answers: if the per-GPU step measured in the rs-7943457 node
telemetry (scripts/aidc_edges.py) repeated in perfect synchrony across a
training job of N GPUs, how large would the step be, and how many GPUs
would it take to reach the 10 to 20 MW the operators claim? Commissioned
by the final-report review of 2026-08-28 (docs/final_report.md section
3.12, Table 12).

Per-GPU step = node swing / 8 and per-GPU ramp rate = node ramp rate / 8,
over the four baseline sessions (the range is the min and max across
sessions and, for the ramp, across fall and rise). Step at N GPUs =
N x per-GPU step, assuming perfect coherence: measured 0.994 to 0.995
within the node, assumed (not measured) across nodes. It is the load
before any UPS or battery absorbs it.

Usage: .venv/bin/python scripts/aidc_scale.py   (markdown table + outputs/aidc_scale.json)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDGES = ROOT / "outputs" / "aidc_edges.json"
OUT = ROOT / "outputs" / "aidc_scale.json"
GPUS_PER_NODE = 8
JOBS = [  # public descriptions of real training jobs and clusters (report refs [108] to [110])
    (16_384, "Llama 3 405B pre-training [108]"),
    (24_576, "one of Meta's two 2024 H100 clusters [109]"),
    (50_000, "a round number"),
    (100_000, "xAI's Colossus, first phase [110]"),
]
CLAIM_MW = (10, 20)


def main():
    rows = json.loads(EDGES.read_text())
    step = [r["swing_kW"] / GPUS_PER_NODE for r in rows]
    rate = [r[k] / GPUS_PER_NODE for r in rows
            for k in ("fall_rate_median_kW_per_s", "rise_rate_median_kW_per_s")]
    frac = [r["swing_kW"] / r["high_kW"] for r in rows]
    lo, hi, rlo, rhi = min(step), max(step), min(rate), max(rate)
    assert 0 < lo < hi and 0 < rlo < rhi
    out = {
        "per_gpu_step_kW": [lo, hi], "per_gpu_ramp_kW_per_s": [rlo, rhi],
        "step_over_high_level": [min(frac), max(frac)],
        "jobs": [{"gpus": n, "what": w, "step_MW": [n * lo / 1000, n * hi / 1000],
                  "ramp_MW_per_s": [n * rlo / 1000, n * rhi / 1000]} for n, w in JOBS],
        "gpus_for_claim": {str(mw): [mw * 1000 / hi, mw * 1000 / lo] for mw in CLAIM_MW},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"per-GPU step {lo:.2f} to {hi:.2f} kW ({min(frac):.0%} to {max(frac):.0%} of the node's "
          f"high level); per-GPU ramp {rlo:.2f} to {rhi:.2f} kW/s")
    print("| GPUs in the job | What that is | Step | Ramp rate |")
    print("|---|---|---|---|")
    for j in out["jobs"]:
        print(f"| {j['gpus']:,} | {j['what']} | {j['step_MW'][0]:.1f} to {j['step_MW'][1]:.1f} MW "
              f"| {j['ramp_MW_per_s'][0]:.1f} to {j['ramp_MW_per_s'][1]:.1f} MW/s |")
    for mw, (a, b) in out["gpus_for_claim"].items():
        print(f"| {a:,.0f} to {b:,.0f} | GPUs needed for a {mw} MW step | {mw} MW | |")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
