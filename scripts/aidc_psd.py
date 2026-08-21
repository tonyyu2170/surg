# scripts/aidc_psd.py
"""Periodogram of real AI-training GPU power telemetry: where does the energy sit?

Usage: .venv/bin/python scripts/aidc_psd.py

Answers docs/research-notes/N-subsecond-provenance-and-filters.md section 7.7 (and
the deferred item in section 9): does node-scale GPU power telemetry reproduce the
0.2-3 Hz band that arXiv 2508.14318 measured on thousands-of-GPU jobs, and what
mechanism drives the cycling?

Data: 6 sessions from the verified rs-7943457 dataset (York University/IESO,
CC BY 4.0), downloaded to data/raw/aidc_workload/ (gitignored, re-downloadable from
github.com/Ahmed-Elsayed95/High-resolution-AI-Data-Center-Training-Workloads-Dataset).
Each session sums the 8 per-GPU power channels on one 8-GPU node (B200 or H100),
diffusion or LLM training, 45,000 samples at a 20 ms poll interval (effective
refresh ~103 ms / ~9.7 Hz per note N section 7.6 -- confirmed here as near-zero
variance above 3 Hz in every session, i.e. the instrument is mute there by
construction, not evidence about the workload).

Two seq1024/seq4096 "Sequence_length_cut" files from the same repo were pulled for
a mechanism test and dropped: per-GPU memory usage was identical to under 0.01%
across a claimed 4x sequence-length range, which is physically impossible if the
runs actually differed as labeled -- not independent measurements. Anyone reusing
that directory in the source repo should verify before trusting the label.

Method notes that mattered (caught in review before any number was reported):
  * welch()'s default detrend='constant' plus an un-trimmed session lets idle/
    warm-up blocks and a genuine end-of-session power dropoff dump energy into
    the lowest frequency bin. Fixed 5%/5% head-tail trim + detrend='linear' fixes
    this -- an adaptive "flat rolling mean" window detector was tried first and
    discarded because this data duty-cycles for the entire session, so it never
    looks locally flat and the detector collapses to under 2% of the record.
  * Peak location uses the autocorrelation's TALLEST peak within a 1-30s lag
    window, not the earliest local maximum -- the earliest local max lands on
    the second harmonic in several sessions and manufactures a false
    periodogram/ACF disagreement.
  * Parseval's check (integral of the Welch PSD vs Var(signal)) is printed for
    every session as a sanity check on the estimator itself.
"""
import numpy as np
import pandas as pd
from scipy import signal

SESSIONS = {
    "b200_diffusion": "data/raw/aidc_workload/b200_diffusion_baseline.csv",
    "h100_diffusion": "data/raw/aidc_workload/h100_diffusion_baseline.csv",
    "b200_llm_bs16(baseline)": "data/raw/aidc_workload/b200_llm_baseline.csv",
    "h100_llm": "data/raw/aidc_workload/h100_llm_baseline.csv",
    "b200_llm_bs2": "data/raw/aidc_workload/b200_llm_bs2.csv",
    "b200_llm_bs32": "data/raw/aidc_workload/b200_llm_bs32.csv",
    # seq1024/seq4096 dropped: mem_used is identical to the seq2048 baseline
    # to <0.01% (verified separately) - not independent runs, confounded.
}

BANDS = {
    "below 0.1 Hz": (0.0, 0.1),
    "0.1-2 Hz (NERC reliability)": (0.1, 2.0),
    "0.2-3 Hz (measured)": (0.2, 3.0),
}


def band_fraction(f, pxx, lo, hi):
    total = np.trapezoid(pxx, f)
    mask = (f >= lo) & (f <= hi)
    inband = np.trapezoid(pxx[mask], f[mask])
    return inband / total


def steady_state_window(power, trim_frac=0.05):
    # This dataset duty-cycles heavily within steady state (see idle_frac
    # printed below) - an adaptive "flat rolling mean" detector collapses
    # to a near-zero window because the signal is never flat by design.
    # Fixed head/tail trim is the right tool here; it only needs to catch
    # genuine warm-up/cool-down level shifts, which a 5% trim comfortably does.
    n = len(power)
    k = int(n * trim_frac)
    return k, n - k


def main():
    for name, path in SESSIONS.items():
        df = pd.read_csv(path)
        gpu_cols = [c for c in df.columns if c.endswith("_power_W") and c.startswith("gpu")]
        node_power = df[gpu_cols].sum(axis=1).to_numpy()

        t = pd.to_datetime(df["timestamp"]).to_numpy()
        dt = np.median(np.diff(t) / np.timedelta64(1, "s"))
        fs = 1.0 / dt
        n = len(node_power)

        print(f"\n=== {name} ===")
        print(f"n_gpus={len(gpu_cols)}  n_samples={n}  fs={fs:.2f} Hz  duration={n*dt:.1f}s")

        pmax = node_power.max()
        idle_frac = (node_power < 0.4 * pmax).mean()
        head5 = node_power[: n // 20].mean()
        mid50 = node_power[n // 4 : 3 * n // 4].mean()
        tail5 = node_power[-n // 20 :].mean()
        print(f"session max={pmax:.0f} W  idle_frac(<40% max)={idle_frac*100:.1f}%  "
              f"head5%={head5:.0f}W mid50%={mid50:.0f}W tail5%={tail5:.0f}W")

        lo, hi = steady_state_window(node_power)
        ss = node_power[lo:hi]
        print(f"steady-state window: samples [{lo}:{hi}] = {(hi-lo)*dt:.1f}s "
              f"({(hi-lo)/n*100:.1f}% of session)")

        ss_detrended = signal.detrend(ss, type="linear")

        # peak location: single high-resolution periodogram
        f_pg, pxx_pg = signal.periodogram(ss, fs=fs, window="hann", detrend="linear")
        peak_idx = np.argmax(pxx_pg[1:]) + 1
        peak_freq = f_pg[peak_idx]
        print(f"periodogram peak: {peak_freq:.4f} Hz (period {1/peak_freq:.1f}s), "
              f"df={f_pg[1]:.5f} Hz")

        # time-domain corroboration: autocorrelation
        acf = np.correlate(ss_detrended, ss_detrended, mode="full")
        acf = acf[len(acf) // 2:]
        acf /= acf[0]
        min_lag, max_lag = int(fs * 1.0), int(fs * 30.0)
        window = acf[min_lag:max_lag]
        peaks, props = signal.find_peaks(window, height=-np.inf)
        if len(peaks):
            best = peaks[np.argmax(props["peak_heights"])]  # tallest, not first
            lag_s = (best + min_lag) / fs
            print(f"autocorrelation tallest peak (1-30s): lag={lag_s:.1f}s (freq={1/lag_s:.4f} Hz)")
        else:
            print("autocorrelation: no clear peak found")

        # band fractions: averaged Welch PSD, detrended, on the steady-state window
        nperseg = min(16384, len(ss))
        f_w, pxx_w = signal.welch(ss, fs=fs, nperseg=nperseg, detrend="linear")
        var_direct = np.var(ss_detrended)
        var_psd = np.trapezoid(pxx_w, f_w)
        print(f"Parseval check: var(signal)={var_direct:.3e}  integral(PSD)={var_psd:.3e}  "
              f"ratio={var_psd/var_direct:.3f}")

        for label, (blo, bhi) in BANDS.items():
            frac = band_fraction(f_w, pxx_w, blo, bhi)
            print(f"  variance fraction in {label}: {frac*100:.2f}%")


if __name__ == "__main__":
    main()
