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

PROGRAM_COLS = [
    "program_579", "program_baseline", "program_energy_internet_demo",
    "program_lg_appliance", "program_verizon", "program_ccet_group",
    "program_civita_group", "program_shines",
]


def read_metadata() -> pd.DataFrame:
    return pd.read_csv(META, skiprows=[1], low_memory=False)


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
