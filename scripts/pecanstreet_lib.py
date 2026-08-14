# scripts/pecanstreet_lib.py
"""Shared logic for the Pecan Street XFRA cut (headroom + 1-sec volatility).

Design doc: docs/specs/2026-08-14-pecanstreet-xfra-headroom-design.md
Facts that shape everything here:
  * Whole-home consumption is NOT a column; it is reconstructed as
    grid + solar + solar2 (gross draw through the panel — the quantity a
    service rating constrains). NaN generation is treated as 0.
  * Timestamps embed UTC offsets, but the CA bundle is San Diego homes
    stamped in Central time. All parsing goes offset -> UTC -> city tz;
    the headroom script's diurnal check validates the CA interpretation.
  * metadata.csv row 2 is an embedded dictionary row (skiprows=[1]).
  * No measured panel size exists anywhere in the free tier, so headroom
    is computed against 100/150/200 A scenario bands, with and without the
    NEC 80% continuous derating.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw/pecanstreet")
ELEC = RAW / "electricity_data"
META = RAW / "metadata.csv"
OUTDIR = Path("outputs/pecanstreet")

CITY_DIR = {"austin": "Austin", "new_york": "New_York", "california": "California"}
CITY_TZ = {
    "austin": "America/Chicago",
    "new_york": "America/New_York",
    "california": "America/Los_Angeles",  # stamps are Central; see diurnal check
}
POWER_COLS = ["grid", "solar", "solar2", "battery1"]

SERVICE_KW = {"100A": 24.0, "150A": 36.0, "200A": 48.0}  # 240 V service
NEC_DERATE = 0.8  # continuous-load rule
PEAK_MONTHS = (6, 7, 8, 9)
PEAK_HOURS = (15, 16, 17, 18)  # 15:00-18:59 local
SUMMER_PEAK_MINUTES = 122 * 240  # Jun-Sep, 15:00-18:59 local: 122 days x 240 min
NODE_AMPLITUDE = 0.9  # LLTF: swings up to 90% of capacity

MAX_PLAUSIBLE_KW = 100.0  # a 400 A / 240 V service tops out at 96 kW

PROGRAM_COLS = [
    "program_579", "program_baseline", "program_energy_internet_demo",
    "program_lg_appliance", "program_verizon", "program_ccet_group",
    "program_civita_group", "program_shines",
]
# PROGRAM_COLS partitioned in two: enrolment markers (participation in Pecan
# Street itself, not load-changing) vs real treatments (see treated_dataids).
ENROLMENT_PROGRAM_COLS = ["program_baseline", "program_energy_internet_demo"]
TREATMENT_PROGRAM_COLS = [
    "program_579", "program_lg_appliance", "program_verizon",
    "program_ccet_group", "program_civita_group", "program_shines",
]


def read_metadata() -> pd.DataFrame:
    return pd.read_csv(META, skiprows=[1], low_memory=False)


def treated_dataids(meta: pd.DataFrame) -> set[int]:
    """dataids in a load-changing treatment arm.

    Enrolment markers do not count, and an explicit '- Control' arm is
    untreated by definition, so both are excluded from the returned set.
    """
    treated: set[int] = set()
    for col in TREATMENT_PROGRAM_COLS:
        if col not in meta.columns:
            continue
        s = meta[col]
        is_control = s.astype(str).str.contains("control", case=False, na=False)
        arm = s.notna() & ~is_control
        treated |= set(meta.loc[arm, "dataid"].astype(int))
    return treated


def read_power_file(path: Path, tz: str, time_col: str | None = None) -> pd.DataFrame:
    """Read one bundle CSV keeping only dataid, timestamp, and power columns."""
    header = pd.read_csv(path, nrows=0).columns
    if time_col is None:
        time_col = "local_15min" if "local_15min" in header else "localminute"
    usecols = ["dataid", time_col] + [c for c in POWER_COLS if c in header]
    df = pd.read_csv(path, usecols=usecols)
    ts = pd.to_datetime(df[time_col], utc=True).dt.tz_convert(tz)
    out = df.drop(columns=[time_col])
    out.insert(1, "ts", ts)
    for c in POWER_COLS:
        if c not in out.columns:
            out[c] = np.nan
    return out[["dataid", "ts"] + POWER_COLS].sort_values(["dataid", "ts"], ignore_index=True)


def read_power(city: str, resolution: str) -> pd.DataFrame:
    """resolution in {'15minute', '1minute'}. 1-sec files go through the streaming path."""
    d = ELEC / CITY_DIR[city]
    name = {"austin": "austin", "new_york": "newyork", "california": "california"}[city]
    path = d / f"{resolution}_data_{name}.csv.gz"
    return read_power_file(path, tz=CITY_TZ[city])


def reconstruct_use(df: pd.DataFrame) -> pd.Series:
    """Whole-home consumption in kW: grid + solar + solar2, NaN generation = 0.

    battery1 is deliberately excluded; battery homes are flagged upstream and
    excluded from headline stats (they are SHINES-intervention homes anyway).
    """
    return df["grid"].astype(float) + df["solar"].fillna(0.0) + df["solar2"].fillna(0.0)


def mask_implausible(use: pd.Series) -> pd.Series:
    """NaN out readings beyond any physically possible residential draw.

    Across all 31,808,722 rows of the three 1-minute bundles, exactly 2 rows
    exceed 48 kW: both belong to Austin dataid 7536 at 2018-02-02 12:26 and
    12:27, where every channel simultaneously flipped sign -- including the
    leg voltages, which read -1,145,948 V and then +1,146,134 V on a nominal
    120 V leg. It is a telemetry fault, not a real draw. With those 2 rows
    removed the corpus maximum is 23.97 kW, and there is an empty gap between
    24 kW and 2,895 kW, so MAX_PLAUSIBLE_KW just needs to sit in that gap --
    the exact value is immaterial. 100 kW comfortably clears it while still
    sitting below any physically wired residential service (400 A / 240 V
    tops out at 96 kW).
    """
    use = use.copy()
    use[use.abs() > MAX_PLAUSIBLE_KW] = np.nan
    return use


def negative_share(use: pd.Series) -> float:
    """Share of rows with negative use. Denominator is all rows, including
    NaN readings, so NaN dilutes the share toward zero."""
    return float((use < 0).mean())


def coverage(df: pd.DataFrame, freq_s: int) -> pd.Series:
    """Per-dataid observed/expected rows inside each home's own [min ts, max ts]."""
    def _one(g: pd.DataFrame) -> float:
        span = (g["ts"].max() - g["ts"].min()).total_seconds()
        expected = span / freq_s + 1
        return len(g) / expected

    return df.groupby("dataid").apply(_one)


def peak_window_mask(ts: pd.DatetimeIndex | pd.Series) -> np.ndarray:
    ts = pd.DatetimeIndex(ts)
    return np.isin(ts.month, PEAK_MONTHS) & np.isin(ts.hour, PEAK_HOURS)


def summer_exposure(ts: pd.DatetimeIndex | pd.Series) -> float:
    """Absolute summer-peak-window exposure: observed peak-window minutes
    (Jun-Sep, 15:00-18:59 local) divided by SUMMER_PEAK_MINUTES, one full
    summer's worth. 1.0 means "one full summer of peak-window minutes";
    a complete multi-year pooled bundle (e.g. 5 years of California data)
    correctly returns ~5.0 rather than being capped at 1.0. Gate rule: a home
    joins a window's statistics only with >=0.90 summer_exposure, measured
    against this fixed absolute denominator rather than the home's own data
    span, so the metric catches both failure modes a self-spanned coverage
    fraction misses: a short data extent (few days of one summer) and a long
    extent riddled with gaps."""
    ts = pd.DatetimeIndex(ts)
    if len(ts) == 0:
        return 0.0
    return float(peak_window_mask(ts).sum() / SUMMER_PEAK_MINUTES)


def headroom_metrics(load: pd.Series) -> dict:
    """Headroom stats for one home over one window. load in kW at 1-min."""
    load = pd.Series(np.asarray(load, dtype=float))
    q = load.quantile
    out = {
        "n_minutes": int(load.notna().sum()),
        "max_kw": float(load.max()),
        "p99_kw": float(q(0.99)),
        "p999_kw": float(q(0.999)),
        "mean_kw": float(load.mean()),
        "hostable_kw": {},           # limit*0.8 - max, floored at 0  (all-minutes)
        "hostable_p999_kw": {},      # limit*0.8 - p99.9, floored at 0 (spike-robust)
        "hostable_kw_noderate": {},  # limit - max, no NEC 0.8 (spec: with AND without)
    }

    def _floor_at_zero(diff: float) -> float:
        return diff if np.isnan(diff) else max(0.0, diff)

    for name, s_kw in SERVICE_KW.items():
        lim = s_kw * NEC_DERATE
        out["hostable_kw"][name] = _floor_at_zero(lim - out["max_kw"])
        out["hostable_p999_kw"][name] = _floor_at_zero(lim - out["p999_kw"])
        out["hostable_kw_noderate"][name] = _floor_at_zero(s_kw - out["max_kw"])
    return out


# ---------------------------------------------------------------------------
# Streaming pieces for the 1-sec pass. Each accumulator carries its own tail
# across update() calls so chunked feeding gives identical results to whole
# feeding (pinned by test_delta_hist_split_feed_equals_whole_feed).
# ---------------------------------------------------------------------------
from scipy.signal import welch  # mid-file import; E402 off, a noqa would trip RUF100

DELTA_BIN_EDGES = np.concatenate(([0.0], np.logspace(-3, 2, 121)))  # |delta| kW


def contiguous_runs(epoch: np.ndarray) -> list[slice]:
    """Slices of runs where epoch increments by exactly 1 second."""
    if len(epoch) == 0:
        return []
    breaks = np.where(np.diff(epoch) != 1)[0]
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks + 1, [len(epoch)]))
    return [slice(int(a), int(b)) for a, b in zip(starts, ends)]


class DeltaHist:
    """Streaming histogram of |use[t+lag] - use[t]| taken only inside contiguous runs."""

    def __init__(self, lag_s: int):
        self.lag = lag_s
        self.counts = np.zeros(len(DELTA_BIN_EDGES) - 1, dtype=np.int64)
        self.n = 0
        self.sum = 0.0
        self.sumsq = 0.0
        self.max = 0.0
        self._tail_epoch = np.empty(0, dtype=np.int64)
        self._tail_use = np.empty(0, dtype=float)

    def update(self, epoch: np.ndarray, use: np.ndarray) -> None:
        epoch = np.concatenate((self._tail_epoch, epoch))
        use = np.concatenate((self._tail_use, use))
        for s in contiguous_runs(epoch):
            seg = use[s]
            if len(seg) <= self.lag:
                continue
            d = np.abs(seg[self.lag:] - seg[:-self.lag])
            d = d[~np.isnan(d)]
            if len(d) == 0:
                continue
            self.counts += np.histogram(d, bins=DELTA_BIN_EDGES)[0]
            self.n += len(d)
            self.sum += float(d.sum())
            self.sumsq += float((d**2).sum())
            self.max = max(self.max, float(d.max()))
        # Keep the last run's tail (lag samples) so a chunk boundary inside a
        # run doesn't lose the straddling deltas.
        keep = min(self.lag, len(epoch))
        self._tail_epoch = epoch[-keep:]
        self._tail_use = use[-keep:]

    def quantile(self, q: float) -> float:
        if self.n == 0:
            return float("nan")
        cum = np.cumsum(self.counts)
        if q * self.n > cum[-1]:
            # Requested quantile falls above the counted mass: some deltas
            # exceeded the top bin edge and were dropped by np.histogram
            # (self.n still counts them). Signal saturation instead of
            # silently clamping to the top edge.
            return float("inf")
        idx = int(np.searchsorted(cum, q * self.n))
        idx = min(idx, len(self.counts) - 1)
        return float(DELTA_BIN_EDGES[idx + 1])  # upper edge: conservative

    def summary(self) -> dict:
        mean = self.sum / self.n if self.n else float("nan")
        var = self.sumsq / self.n - mean**2 if self.n else float("nan")
        return {
            "n": self.n, "mean_kw": mean, "std_kw": float(np.sqrt(max(var, 0.0))),
            "p50_kw": self.quantile(0.50), "p99_kw": self.quantile(0.99),
            "p999_kw": self.quantile(0.999),
            "max_kw": self.max if self.n else float("nan"),
        }


class TopEvents:
    """Largest |1-sec deltas| with context, via a bounded list."""

    def __init__(self, k: int):
        self.k = k
        self._events: list[dict] = []
        self._tail_epoch = np.empty(0, dtype=np.int64)
        self._tail_use = np.empty(0, dtype=float)

    def update(self, dataid: int, epoch: np.ndarray, use: np.ndarray) -> None:
        epoch = np.concatenate((self._tail_epoch, epoch))
        use = np.concatenate((self._tail_use, use))
        for s in contiguous_runs(epoch):
            seg, ep = use[s], epoch[s]
            if len(seg) < 2:
                continue
            d = np.abs(np.diff(seg))
            with np.errstate(invalid="ignore"):
                order = np.argsort(np.nan_to_num(d, nan=-1.0))[::-1][: self.k]
            for i in order:
                if np.isnan(d[i]):
                    continue
                self._events.append({
                    "dataid": int(dataid), "epoch": int(ep[i + 1]),
                    "delta_kw": float(d[i]),
                    "before_kw": float(seg[i]), "after_kw": float(seg[i + 1]),
                })
        self._events = sorted(self._events, key=lambda e: -e["delta_kw"])[: self.k]
        self._tail_epoch = epoch[-1:]
        self._tail_use = use[-1:]

    def result(self) -> list[dict]:
        return self._events


class PsdAccumulator:
    """Welch PSD averaged over contiguous segments of >= nperseg seconds."""

    def __init__(self, nperseg: int = 1024, max_segments: int = 400):
        self.nperseg = nperseg
        self.max_segments = max_segments
        self._psd_sum: np.ndarray | None = None
        self._freqs: np.ndarray | None = None
        self.n_segments = 0
        self._buf_epoch = np.empty(0, dtype=np.int64)
        self._buf_use = np.empty(0, dtype=float)

    def _flush(self, seg: np.ndarray) -> None:
        if self.n_segments >= self.max_segments:
            return
        if len(seg) < self.nperseg:
            return
        freqs, psd = welch(seg, fs=1.0, nperseg=self.nperseg, detrend="linear")
        if self._psd_sum is None:
            self._freqs, self._psd_sum = freqs, psd
        else:
            self._psd_sum = self._psd_sum + psd
        self.n_segments += 1

    def update(self, epoch: np.ndarray, use: np.ndarray) -> None:
        # A NaN sample is a gap (spec: gaps split spectral segments, never
        # interpolate): drop the row BEFORE run-splitting so the epoch hole
        # splits the segment instead of splicing across it.
        keep = ~np.isnan(use)
        epoch, use = epoch[keep], use[keep]
        epoch = np.concatenate((self._buf_epoch, epoch))
        use = np.concatenate((self._buf_use, use))
        runs = contiguous_runs(epoch)
        for s in runs[:-1]:
            self._flush(use[s])
        # Last run may continue into the next chunk: buffer it, capped at 4096.
        last = runs[-1] if runs else slice(0, 0)
        if last.stop - last.start > 4096:
            self._flush(use[last])
            self._buf_epoch = np.empty(0, dtype=np.int64)
            self._buf_use = np.empty(0, dtype=float)
        else:
            self._buf_epoch = epoch[last]
            self._buf_use = use[last]

    def result(self) -> tuple[np.ndarray, np.ndarray]:
        self._flush(self._buf_use)
        self._buf_epoch = np.empty(0, dtype=np.int64)
        self._buf_use = np.empty(0, dtype=float)
        if self._psd_sum is None:
            return np.empty(0), np.empty(0)
        return self._freqs, self._psd_sum / self.n_segments
