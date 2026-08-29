# Pecan Street × XFRA Headroom + 1-sec Volatility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Answer the XFRA question with the Pecan Street free-tier bundles: where the pilot is
siting (RQ1), whether homes have idle panel capacity that survives summer peak (RQ2), and how
residential 1-sec volatility compares to a DC-style oscillating node (RQ3).

**Architecture:** One shared library (`scripts/pecanstreet_lib.py`) holds all testable logic;
two thin path-run scripts orchestrate (`pecanstreet_headroom.py`, `pecanstreet_1sec.py`);
results land in `outputs/pecanstreet/` as JSON + PNG; findings become research note M.
Spec: `docs/specs/2026-08-14-pecanstreet-xfra-headroom-design.md`.

**Tech Stack:** Python 3.13 venv (`.venv/bin/python`), pandas, numpy, scipy (welch),
matplotlib (Agg). No new dependencies.

---

## House rules that OVERRIDE the generic task template

- **NEVER `git commit` without asking Tony first — each commit is its own ask.** Commit steps
  below say "ASK, then commit". If permission is not granted, stage and stop.
- **No AI attribution in commits.** Plain human-style messages only.
- **Never `git add .`** — stage the explicit paths listed in each commit step.
- **Never touch `data/` or `outputs/` destructively.**
- `docs/plans/advisor/2026-08-19-advisor-meeting-agenda.md` has uncommitted user edits. Task 8 edits
  ONE section of it and leaves it uncommitted.

## Verified data facts (probed 2026-08-14 — trust these, they override any doc)

- Bundles: `data/raw/pecanstreet/electricity_data/{Austin,New_York,California}/`.
  Austin: 25 homes, calendar 2018, 15-min + 1-min + 1-sec (4 files).
  New_York: 25 homes, 2019-05-01→2019-10-31, all three resolutions (4 × 1-sec files).
  California: 23 homes, 2014-01-01→2018-12-31, 15-min + 1-min only.
- Wide circuit schema. Time col is `local_15min` (15-min) / `localminute` (1-min AND 1-sec).
  Key cols: `dataid`, `grid`, `solar`, `solar2`, `battery1`, `car1`. 1-sec files additionally
  end with `leg1v,leg2v` (leg voltages — out of scope, mention in note as future PQ hook).
  Values are kW, floats; missing = empty string → NaN.
- Timestamps carry UTC offsets: `2018-01-01 01:21:00-06`. **CA files are all San Diego homes
  but stamped -06/-05 (Central)** — parse `utc=True`, convert to the city tz, and run the
  Task 4 diurnal sanity check before believing local-hour claims.
- 1-sec files are **grouped by dataid** (verified: first 400k rows of Austin file1 are one
  home). Streaming must still not rely on grouping — the accumulator design below is
  order-tolerant as long as each home's rows are time-sorted per file.
- `data/raw/pecanstreet/metadata.csv`: 2,037 lines; row 1 header (130 cols), **row 2 is an
  embedded dictionary row — always `skiprows=[1]`**. Columns (1-indexed): 1 `dataid`, 4 `city`,
  5 `state`, 77 `solar`, 78 `solar2`, 98 `house_construction_year`, 99 `total_square_footage`,
  120–127 program flags: `program_579, program_baseline, program_energy_internet_demo,
  program_lg_appliance, program_verizon, program_ccet_group, program_civita_group,
  program_shines`.
- CA bundle dataids (all San Diego): 203, 1450, 1524, 1731, 2606, 3687, 3864, 3938, 4495,
  4934, 5938, 6377, 6547, 7062, 7114, 8061, 8342, 8574, 8733, 9213, 9612, 9775, 9836.
- Austin bundle dataids (probed 2026-08-14): 661, 1642, 2335, 2361, 2818, 3039, 3456, 3538,
  4031, 4373, 4767, 5746, 6139, 7536, 7719, 7800, 7901, 7951, 8156, 8386, 8565, 9019, 9160,
  9278, 9922 — dataid 661 (the sample/pin home) is confirmed present.
- Program-flag columns encode participation as non-null (`yes` or a group label such as
  `CCET - Control`); non-participants are empty, so `notna()` is the correct intervention
  filter. It also sweeps in control-arm homes (`CCET - Control`, `Civita - Control`) — note
  M must say control arms were excluded with the treated. `house_construction_year` and
  `total_square_footage` are float64 with NaN for missing.
- The venv runs **pandas 3.0.5**: `pd.to_datetime` on strings yields `datetime64[us]`, NOT
  ns — `astype("int64") // 10**9` gives garbage epochs (verified: two stamps one second
  apart collapse to the same value). Epoch conversion must go through
  `.dt.as_unit("s").astype("int64")`.
- Ruff here enables only the defaults (E4/E7/E9/F) plus an unused-noqa check: a
  `# noqa: E402` comment is itself flagged (RUF100 — verified on
  `scripts/ercot_diagnostic.py`). Mid-file imports after `matplotlib.use("Agg")` are fine
  as-is; keep the new files noqa-free.
  **CORRECTION 2026-08-14 (during Task 4a):** this is stale. The installed ruff is **0.16.0**
  and its default rule set also includes **isort `I001`**, which the repo's `[tool.ruff]`
  block (line-length + target-version only, no `select`) does not override. Import blocks
  must therefore be isort-clean — notably, no blank line between the third-party imports and
  `import pecanstreet_lib as pslib`, which ruff cannot tell is first-party because it is
  reached via `sys.path[0]` rather than as a package. E402 is still not enabled, so the
  mid-file `matplotlib.use("Agg")` placement remains correct and needs no noqa.

## File map

| File | Responsibility |
|---|---|
| `scripts/pecanstreet_lib.py` | Create. All testable logic: metadata/power loading, use reconstruction, coverage, headroom metrics, run-splitting, streaming delta/PSD accumulators. |
| `scripts/pecanstreet_headroom.py` | Create. RQ2 orchestration: per-city headroom stats, coincidence test, 15-min crosscheck, tz sanity check, robustness cut, JSON + figures. |
| `scripts/pecanstreet_1sec.py` | Create. RQ3 orchestration: streaming pass over 1-sec files, aggregate arrays, 1-min N-curve, node comparison, JSON + figures. |
| `tests/test_pecanstreet_lib.py` | Create. Unit tests on synthetic data (no data/ dependency). |
| `tests/regression/test_pecanstreet_pins.py` | Create (Task 7). Pins headline numbers from the production runs; skips if data/ absent. |
| `outputs/pecanstreet/` | Created by scripts. `siting_research.md`, `headroom_<city>.json`, `onesec_<city>.json`, PNGs. Gitignored. |
| `docs/research-notes/M-pecanstreet-xfra-headroom.md` | Create (Task 8). The deliverable note. |

Import convention: the scripts do `import pecanstreet_lib as pslib` (works when run by path —
the scripts dir is `sys.path[0]`). Tests do `from scripts import pecanstreet_lib as pslib`
(works under pytest — repo root is on `sys.path`, `scripts/__init__.py` exists). Scripts hold
NO logic worth testing; everything testable lives in the lib, so the two import styles never
meet in one process.

---

### Task 1: RQ1 siting desk research

No code. Web research producing `outputs/pecanstreet/siting_research.md`.

- [ ] **Step 1: Create the output dir**

Run: `mkdir -p outputs/pecanstreet`

- [ ] **Step 2: Research.** Run web searches (WebSearch / Exa), at minimum these queries, and
  follow primary sources (company pages, homebuilder press releases, local-utility news):
  - `XFRA SPAN PulteGroup 100 home pilot data center`
  - `xfra.ai NVIDIA home compute node specifications kW`
  - `SPAN smart panel XFRA pilot location utility`
  - `PulteGroup XFRA new construction southwest which city`

  Questions to answer (write "not disclosed as of 2026-08" where that is the finding — that
  is itself a result):
  1. Which metro(s)/state(s) is the pilot siting in? Which utility territory?
  2. Is the climate cooling-dominated like Austin? (One sentence judgment.)
  3. **Node electrical spec: continuous draw in kW**, and any published duty-cycle/oscillation
     behavior. This feeds Task 5's `--node-kw`; fallback bracket is `1,5,10` kW.
  4. Anything on how the SPAN panel throttles the node (confirms the "node yields to
     appliances" mechanic from the agenda).

- [ ] **Step 3: Write `outputs/pecanstreet/siting_research.md`** — a dated markdown file with
  the four answers, each with source URL + access date, and an explicit "node-kw decision:
  `<values>`" line at the end.

- [ ] **Step 4: Report the node-kw decision to Tony** in the session (one line). No commit —
  `outputs/` is gitignored; the content gets folded into note M in Task 8.

---

### Task 2: `scripts/pecanstreet_lib.py` — loading, reconstruction, coverage (TDD)

**Files:**
- Create: `scripts/pecanstreet_lib.py`
- Create: `tests/test_pecanstreet_lib.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pecanstreet_lib.py`:

```python
"""Unit tests for scripts/pecanstreet_lib.py. Synthetic data only — no data/ dependency."""
from __future__ import annotations

import gzip

import numpy as np
import pandas as pd
import pytest

from scripts import pecanstreet_lib as pslib


def _write_gz_csv(path, text):
    with gzip.open(path, "wt") as f:
        f.write(text)


@pytest.fixture
def minute_csv(tmp_path):
    # Two homes: 100 has solar (one negative-use minute), 200 has no solar cols populated.
    text = (
        "dataid,localminute,air1,grid,solar,solar2,battery1\n"
        "100,2018-06-01 17:00:00-05,1.0,-0.5,2.0,,\n"
        "100,2018-06-01 17:01:00-05,1.0,-3.0,2.0,,\n"      # use = -1.0 -> negative
        "100,2018-06-01 17:02:00-05,1.0,0.5,2.0,,\n"
        "200,2018-06-01 17:00:00-05,,4.0,,,\n"
        "200,2018-06-01 17:02:00-05,,6.0,,,\n"              # 17:01 missing -> coverage 2/3
    )
    p = tmp_path / "1minute_data_austin.csv.gz"
    _write_gz_csv(p, text)
    return p


def test_read_power_parses_local_time(minute_csv):
    df = pslib.read_power_file(minute_csv, tz="America/Chicago")
    assert list(df.columns) == ["dataid", "ts", "grid", "solar", "solar2", "battery1"]
    assert str(df["ts"].dt.tz) == "America/Chicago"
    assert df["ts"].iloc[0].hour == 17  # -05 stamp in June == CDT == already local


def test_reconstruct_use_sums_grid_and_solar(minute_csv):
    df = pslib.read_power_file(minute_csv, tz="America/Chicago")
    use = pslib.reconstruct_use(df)
    assert use.iloc[0] == pytest.approx(1.5)   # -0.5 + 2.0
    assert use.iloc[3] == pytest.approx(4.0)   # grid only, NaN solar treated as 0


def test_negative_share_counts_negatives(minute_csv):
    df = pslib.read_power_file(minute_csv, tz="America/Chicago")
    use = pslib.reconstruct_use(df)
    assert pslib.negative_share(use) == pytest.approx(1 / 5)


def test_coverage_within_window(minute_csv):
    df = pslib.read_power_file(minute_csv, tz="America/Chicago")
    df["use"] = pslib.reconstruct_use(df)
    cov = pslib.coverage(df, freq_s=60)
    # Window = each home's own [min ts, max ts]; 100 has 3/3, 200 has 2/3.
    assert cov.loc[100] == pytest.approx(1.0)
    assert cov.loc[200] == pytest.approx(2 / 3)


def test_headroom_metrics_shape():
    load = pd.Series([1.0, 2.0, 3.0, 9.0, 2.0, 1.0, 1.0, 30.0, 2.0, 1.0])
    m = pslib.headroom_metrics(load)
    assert m["max_kw"] == 30.0
    # 200A scenario: 48 kW * 0.8 - 30 = 8.4 kW hostable (all-minutes definition)
    assert m["hostable_kw"]["200A"] == pytest.approx(8.4)
    # 100A scenario: 24 * 0.8 - 30 < 0 -> floored at 0
    assert m["hostable_kw"]["100A"] == 0.0
    # Un-derated variant (spec: with AND without the NEC 0.8): 48 - 30 = 18
    assert m["hostable_kw_noderate"]["200A"] == pytest.approx(18.0)


def test_peak_window_mask_june_afternoon():
    ts = pd.DatetimeIndex(
        [
            "2018-06-15 15:00:00",  # in: Jun, 15h
            "2018-06-15 19:00:00",  # out: 19h is exclusive
            "2018-12-15 16:00:00",  # out: December
            "2018-09-01 18:59:00",  # in
        ]
    ).tz_localize("America/Chicago")
    mask = pslib.peak_window_mask(ts)
    assert mask.tolist() == [True, False, False, True]


def test_window_coverage_counts_only_peak_minutes():
    ts = pd.DatetimeIndex(
        ["2018-06-15 15:00:00", "2018-06-15 15:01:00", "2018-06-15 15:03:00"]
    ).tz_localize("America/Chicago")
    # Span 15:00-15:03 -> 4 expected peak-window minutes, 3 observed.
    assert pslib.window_coverage(ts) == pytest.approx(3 / 4)
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `.venv/bin/pytest tests/test_pecanstreet_lib.py -x -q`
Expected: FAIL — `ImportError` / `AttributeError` (module doesn't exist yet).

- [ ] **Step 3: Implement the lib**

Create `scripts/pecanstreet_lib.py`:

```python
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
    return float((use < 0).mean())


def coverage(df: pd.DataFrame, freq_s: int) -> pd.Series:
    """Per-dataid observed/expected rows inside each home's own [min ts, max ts]."""
    def _one(g: pd.DataFrame) -> float:
        span = (g["ts"].max() - g["ts"].min()).total_seconds()
        expected = span / freq_s + 1
        return len(g) / expected

    return df.groupby("dataid").apply(_one, include_groups=False)


def peak_window_mask(ts: pd.DatetimeIndex | pd.Series) -> np.ndarray:
    ts = pd.DatetimeIndex(ts)
    return np.isin(ts.month, PEAK_MONTHS) & np.isin(ts.hour, PEAK_HOURS)


def window_coverage(ts: pd.DatetimeIndex | pd.Series) -> float:
    """Coverage inside the peak window: observed peak-window minutes over the
    expected count within [min ts, max ts] at 1-min cadence. Spec rule: a home
    joins a window's statistics only with >=90% coverage in that window."""
    ts = pd.DatetimeIndex(ts)
    if len(ts) == 0:
        return float("nan")
    full = pd.date_range(ts.min(), ts.max(), freq="min")
    expected = int(peak_window_mask(full).sum())
    if expected == 0:
        return float("nan")
    return float(peak_window_mask(ts).sum() / expected)


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
    for name, s_kw in SERVICE_KW.items():
        lim = s_kw * NEC_DERATE
        out["hostable_kw"][name] = float(max(0.0, lim - out["max_kw"]))
        out["hostable_p999_kw"][name] = float(max(0.0, lim - out["p999_kw"]))
        out["hostable_kw_noderate"][name] = float(max(0.0, s_kw - out["max_kw"]))
    return out
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `.venv/bin/pytest tests/test_pecanstreet_lib.py -x -q`
Expected: 10 passed (7 in the original plan; amendment A3 added three).

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check scripts/pecanstreet_lib.py tests/test_pecanstreet_lib.py`
Expected: clean (repo has ~173 pre-existing findings elsewhere; your two files must be clean).

- [ ] **Step 6: ASK Tony for permission to commit.** If granted:

```bash
git add scripts/pecanstreet_lib.py tests/test_pecanstreet_lib.py
git commit -m "feat(pecanstreet): shared lib for XFRA headroom cut - loading, use reconstruction, headroom metrics"
```

---

### Task 3: streaming accumulators for the 1-sec pass (TDD, still in the lib)

**Files:**
- Modify: `scripts/pecanstreet_lib.py` (append)
- Modify: `tests/test_pecanstreet_lib.py` (append)

- [ ] **Step 1: Append the failing tests**

Append to `tests/test_pecanstreet_lib.py`:

```python
def test_contiguous_runs_splits_on_gaps():
    epoch = np.array([100, 101, 102, 110, 111], dtype=np.int64)
    runs = pslib.contiguous_runs(epoch)
    assert [(s.start, s.stop) for s in runs] == [(0, 3), (3, 5)]


def test_delta_hist_exact_quantile_and_gap_exclusion():
    h = pslib.DeltaHist(lag_s=1)
    epoch = np.array([0, 1, 2, 10, 11], dtype=np.int64)
    use = np.array([1.0, 2.0, 4.0, 100.0, 100.5])
    h.update(epoch, use)
    # Deltas: |2-1|=1, |4-2|=2 within run 1; |100.5-100|=0.5 within run 2.
    # The 4->100 jump across the gap must NOT appear.
    assert h.n == 3
    assert h.max == pytest.approx(2.0)
    # quantile() returns the conservative UPPER edge of the bin holding the
    # true median 1.0: 10**(1/24) = 1.10069 (verified against the bin math —
    # rel=0.1 against 1.0 would fail by a hair, so pin the edge itself).
    assert h.quantile(0.5) == pytest.approx(1.1007, rel=0.01)


def test_delta_hist_split_feed_equals_whole_feed():
    """Chunk-boundary carry: feeding the series in two pieces == feeding it whole."""
    rng = np.random.default_rng(0)
    epoch = np.arange(1000, dtype=np.int64)
    use = rng.normal(2.0, 0.5, size=1000)
    whole = pslib.DeltaHist(lag_s=10)
    whole.update(epoch, use)
    split = pslib.DeltaHist(lag_s=10)
    split.update(epoch[:400], use[:400])
    split.update(epoch[400:], use[400:])
    assert split.n == whole.n
    assert split.counts.tolist() == whole.counts.tolist()


def test_top_events_keeps_largest():
    t = pslib.TopEvents(k=2)
    epoch = np.array([0, 1, 2, 3], dtype=np.int64)
    use = np.array([1.0, 5.0, 1.0, 9.0])  # |d| = 4, 4, 8
    t.update(dataid=42, epoch=epoch, use=use)
    top = t.result()
    assert len(top) == 2
    assert top[0]["delta_kw"] == pytest.approx(8.0)
    assert top[0]["dataid"] == 42


def test_psd_accumulator_finds_injected_frequency():
    fs, n = 1.0, 4096
    tt = np.arange(n) / fs
    x = np.sin(2 * np.pi * 0.1 * tt)  # 0.1 Hz tone
    acc = pslib.PsdAccumulator(nperseg=1024)
    acc.update(np.arange(n, dtype=np.int64), x)
    freqs, psd = acc.result()
    assert freqs[np.argmax(psd)] == pytest.approx(0.1, abs=0.005)


def test_psd_accumulator_nan_is_a_gap():
    """A NaN sample splits the segment (spec: gaps split spectral segments,
    no interpolation) -- it must never be dropped and spliced over."""
    use = np.random.default_rng(1).normal(size=2049)
    use[1024] = np.nan
    acc = pslib.PsdAccumulator(nperseg=1024)
    acc.update(np.arange(2049, dtype=np.int64), use)
    acc.result()
    assert acc.n_segments == 2  # two clean 1024-sample segments, no splice
```

- [ ] **Step 2: Run, verify the new tests fail**

Run: `.venv/bin/pytest tests/test_pecanstreet_lib.py -x -q`
Expected: first 7 pass, then FAIL at `test_contiguous_runs_splits_on_gaps` (AttributeError).

- [ ] **Step 3: Append the implementation**

Append to `scripts/pecanstreet_lib.py`:

```python
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
        idx = int(np.searchsorted(cum, q * self.n))
        idx = min(idx, len(self.counts) - 1)
        return float(DELTA_BIN_EDGES[idx + 1])  # upper edge: conservative

    def summary(self) -> dict:
        mean = self.sum / self.n if self.n else float("nan")
        var = self.sumsq / self.n - mean**2 if self.n else float("nan")
        return {
            "n": self.n, "mean_kw": mean, "std_kw": float(np.sqrt(max(var, 0.0))),
            "p50_kw": self.quantile(0.50), "p99_kw": self.quantile(0.99),
            "p999_kw": self.quantile(0.999), "max_kw": self.max,
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
```

- [ ] **Step 4: Run all lib tests, verify they pass**

Run: `.venv/bin/pytest tests/test_pecanstreet_lib.py -q`
Expected: 18 passed (13 in the original plan; amendments A3/A6 added five more).

- [ ] **Step 5: Lint**

Run: `.venv/bin/ruff check scripts/pecanstreet_lib.py tests/test_pecanstreet_lib.py`
Expected: clean.

- [ ] **Step 6: ASK Tony for permission to commit.** If granted:

```bash
git add scripts/pecanstreet_lib.py tests/test_pecanstreet_lib.py
git commit -m "feat(pecanstreet): streaming delta/PSD accumulators for the 1-sec pass"
```

---

### Task 4: `scripts/pecanstreet_headroom.py`

**Files:**
- Create: `scripts/pecanstreet_headroom.py`

The script is orchestration only — every computation beyond gluing already lives in the lib.
It is not unit-tested; Task 7 pins its production numbers.

- [ ] **Step 1: Write the script**

```python
# scripts/pecanstreet_headroom.py
"""RQ2: do the bundle homes have idle panel capacity, and does it survive summer peak?

Usage:
  .venv/bin/python scripts/pecanstreet_headroom.py --sample 661 --month 2018-07  # eyeball first
  .venv/bin/python scripts/pecanstreet_headroom.py                               # full, 3 cities

Design doc: docs/specs/2026-08-14-pecanstreet-xfra-headroom-design.md.
Reads the 1-min bundles (primary; a breaker responds to sustained draw and
15-min averaging shaves peaks — the 15-min files serve only as a crosscheck),
reconstructs whole-home use, and reports headroom against 100/150/200 A
service scenarios, with and without the NEC 80% continuous derating. Homes flagged in any
intervention program are excluded from a robustness re-run. CA timestamps are
Central-stamped San Diego data; the diurnal check below prints the evidence
for the chosen interpretation before any local-hour claim is used.
"""
from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import pecanstreet_lib as pslib

MIN_COVERAGE = 0.90


def home_records(city: str, df: pd.DataFrame, meta: pd.DataFrame) -> list[dict]:
    cov = pslib.coverage(df, freq_s=60)
    flagged = set(
        meta.loc[meta[pslib.PROGRAM_COLS].notna().any(axis=1), "dataid"].astype(int)
    )
    # Descriptive context only (spec): never reweights any statistic. Both
    # columns are float64-with-NaN in metadata.csv (verified 2026-08-14).
    context = {}
    for _, mrow in meta.iterrows():
        yr, sqft = mrow["house_construction_year"], mrow["total_square_footage"]
        context[int(mrow["dataid"])] = {
            "construction_year": None if pd.isna(yr) else int(yr),
            "square_footage": None if pd.isna(sqft) else float(sqft),
        }
    battery_homes = set(df.loc[df["battery1"].notna(), "dataid"].unique().tolist())
    records = []
    for dataid, g in df.groupby("dataid"):
        use = pslib.reconstruct_use(g)
        rec = {"dataid": int(dataid), "city": city,
               "coverage": float(cov.loc[dataid]),
               "negative_share": pslib.negative_share(use),
               "intervention": int(dataid) in flagged,
               "battery": int(dataid) in battery_homes,
               "meta": context.get(int(dataid)),
               # Full bundle span: NY = 6 months, CA = 5 pooled years — note M
               # must not call these "annual" outside Austin.
               "year": pslib.headroom_metrics(use)}
        mask = pslib.peak_window_mask(g["ts"])
        if mask.any():
            # Spec: a home joins a window's stats only with >=90% coverage IN
            # that window, measured as ABSOLUTE summer exposure (amendment A2).
            # off_window is ~92% of all minutes, so the overall coverage gate
            # in run_city stands in for it (documented simplification).
            rec["summer_exposure"] = pslib.summer_exposure(g["ts"])
            rec["off_window"] = pslib.headroom_metrics(use[~mask])
            if rec["summer_exposure"] >= MIN_COVERAGE:
                rec["peak_window"] = pslib.headroom_metrics(use[mask])
        records.append(rec)
    return records


def diurnal_check(city: str, df: pd.DataFrame) -> dict:
    """Mean use by local hour; the evening residential peak must land ~16-21."""
    use = pslib.reconstruct_use(df)
    hours = pd.DatetimeIndex(df["ts"]).hour
    prof = pd.Series(use.values).groupby(np.asarray(hours)).mean()
    return {"peak_hour_local": int(prof.idxmax()),
            "profile_kw": {int(h): float(v) for h, v in prof.items()}}


def crosscheck_15min(city: str, records: list[dict]) -> dict:
    df15 = pslib.read_power(city, "15minute")
    out = {}
    by_id = {r["dataid"]: r for r in records}
    for dataid, g in df15.groupby("dataid"):
        if int(dataid) not in by_id:
            continue
        max15 = float(pslib.reconstruct_use(g).max())
        max1 = by_id[int(dataid)]["year"]["max_kw"]
        out[int(dataid)] = {"max_15min_kw": max15, "max_1min_kw": max1,
                            "peak_shaving_ratio": max15 / max1 if max1 else float("nan")}
    return out


def yearly_breakdown(df: pd.DataFrame) -> dict:
    """Per calendar year: per-home max and the 200A hostable fraction.

    The spec uses CA (2014-2018) as a year-to-year stability check; for
    Austin/NY this is a harmless single-entry table.
    """
    df = df.copy()
    df["use"] = pslib.reconstruct_use(df)
    df["yr"] = pd.DatetimeIndex(df["ts"]).year
    lim = pslib.SERVICE_KW["200A"] * pslib.NEC_DERATE
    out = {}
    for yr, g in df.groupby("yr"):
        mx = g.groupby("dataid")["use"].max()
        out[int(yr)] = {"n_homes": int(mx.size),
                        "median_max_kw": float(mx.median()),
                        "hostable_5kw_frac": float(((lim - mx) >= 5.0).mean())}
    return out


def seasonal_min_headroom(df: pd.DataFrame) -> pd.Series:
    """Median across homes of each day's minimum 200A-derated headroom."""
    df = df.copy()
    df["use"] = pslib.reconstruct_use(df)
    lim = pslib.SERVICE_KW["200A"] * pslib.NEC_DERATE
    df["date"] = pd.DatetimeIndex(df["ts"]).date
    daily_max = df.groupby(["dataid", "date"])["use"].max()
    return (lim - daily_max).groupby("date").median()


def make_figures(city: str, df: pd.DataFrame, records: list[dict], outdir) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    # (a) load-duration curves
    for dataid, g in df.groupby("dataid"):
        use = pslib.reconstruct_use(g).dropna().sort_values(ascending=False)
        axes[0].plot(np.linspace(0, 100, len(use)), use, lw=0.6, alpha=0.6)
    for name, s_kw in pslib.SERVICE_KW.items():
        axes[0].axhline(s_kw * pslib.NEC_DERATE, ls="--", lw=0.8, color="k")
        axes[0].annotate(f"{name}×0.8", (60, s_kw * pslib.NEC_DERATE), fontsize=7)
    axes[0].set(xlabel="% of minutes", ylabel="kW", title=f"{city}: load duration (1-min)")
    # (b) seasonal daily-min headroom
    smh = seasonal_min_headroom(df)
    axes[1].plot(pd.to_datetime(smh.index), smh.values, lw=0.9)
    axes[1].axhline(0, color="r", lw=0.8)
    axes[1].set(ylabel="kW", title="median daily min headroom (200A×0.8)")
    # (c) hostable node, year vs peak window
    ids = [r["dataid"] for r in records]
    year_x = [r["year"]["hostable_kw"]["200A"] for r in records]
    peak_x = [r.get("peak_window", {}).get("hostable_kw", {}).get("200A", np.nan)
              for r in records]
    pos = np.arange(len(ids))
    axes[2].bar(pos - 0.2, year_x, 0.4, label="year")
    axes[2].bar(pos + 0.2, peak_x, 0.4, label="peak window")
    axes[2].set(xticks=pos, title="hostable node kW (200A×0.8)")
    axes[2].set_xticklabels(ids, rotation=90, fontsize=6)
    axes[2].legend()
    fig.tight_layout()
    fig.savefig(outdir / f"headroom_{city}.png", dpi=150)
    plt.close(fig)


def hostable_fractions(records: list[dict], node_kws=(1.0, 5.0, 6.25, 12.5, 19.2)) -> dict:
    """Fraction of homes that can host a continuous X kW node, year vs peak window."""
    out = {}
    for sc in pslib.SERVICE_KW:
        out[sc] = {}
        for x in node_kws:
            year = np.mean([r["year"]["hostable_kw"][sc] >= x for r in records])
            peak_records = [r for r in records if "peak_window" in r]
            peak = np.mean([r["peak_window"]["hostable_kw"][sc] >= x
                            for r in peak_records]) if peak_records else float("nan")
            out[sc][f"{x:g}kW"] = {"year": float(year), "peak_window": float(peak)}
    return out


def run_city(city: str, meta: pd.DataFrame, outdir) -> dict:
    print(f"=== {city}")
    df = pslib.read_power(city, "1minute")
    records = home_records(city, df, meta)
    kept = [r for r in records if r["coverage"] >= MIN_COVERAGE]
    clean = [r for r in kept if not r["intervention"] and not r["battery"]]
    result = {
        "city": city, "n_homes": len(records), "n_kept": len(kept), "n_clean": len(clean),
        "diurnal_check": diurnal_check(city, df),
        "records": kept,
        "hostable_fractions_all": hostable_fractions(kept),
        "hostable_fractions_clean": hostable_fractions(clean) if clean else None,
        "crosscheck_15min": crosscheck_15min(city, kept),
        "yearly": yearly_breakdown(df),
        "negative_share_worst": max(r["negative_share"] for r in records),
    }
    make_figures(city, df, kept, outdir)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", choices=list(pslib.CITY_DIR), action="append")
    ap.add_argument("--sample", type=int, help="single dataid: quick eyeball mode")
    ap.add_argument("--month", help="YYYY-MM restriction for --sample")
    ap.add_argument("--outdir", default=str(pslib.OUTDIR))
    args = ap.parse_args()
    outdir = pslib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    meta = pslib.read_metadata()

    if args.sample is not None:
        city = (args.city or ["austin"])[0]
        df = pslib.read_power(city, "1minute")
        df = df[df["dataid"] == args.sample]
        if args.month:
            per = pd.Period(args.month)
            ts = pd.DatetimeIndex(df["ts"])
            df = df[(ts.year == per.year) & (ts.month == per.month)]
        use = pslib.reconstruct_use(df)
        print(json.dumps(pslib.headroom_metrics(use), indent=2))
        fig, ax = plt.subplots(figsize=(12, 4))
        ax.plot(df["ts"], use, lw=0.4)
        ax.set(ylabel="kW", title=f"{city} dataid={args.sample} {args.month or ''}")
        fig.savefig(outdir / f"sample_{city}_{args.sample}.png", dpi=150)
        return

    results = {c: run_city(c, meta, outdir) for c in (args.city or list(pslib.CITY_DIR))}
    for c, r in results.items():
        (outdir / f"headroom_{c}.json").write_text(json.dumps(r, indent=2))
        print(c, "peak_hour_local:", r["diurnal_check"]["peak_hour_local"],
              "| hostable 200A/5kW year vs peak:",
              r["hostable_fractions_all"]["200A"]["5kW"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lint**

Run: `.venv/bin/ruff check scripts/pecanstreet_headroom.py`
Expected: clean.

- [ ] **Step 3: Sample-mode run (the eyeball gate)**

Run: `.venv/bin/python scripts/pecanstreet_headroom.py --sample 661 --month 2018-07`
Expected: JSON block with plausible numbers — `max_kw` in single-digit-to-low-teens kW for a
July Austin home, `mean_kw` around 1–3 kW, `hostable_kw["200A"]` positive. Figure
`outputs/pecanstreet/sample_austin_661.png` shows a daily AC-cycling sawtooth.
(dataid 661 is confirmed present in the Austin bundle — probed 2026-08-14.)

**If `max_kw` > 48 or mean > 10 or the figure looks like noise: STOP — the reconstruction is
wrong. Debug before proceeding (check solar sign by comparing a solar home's grid vs use at
noon).**

- [ ] **Step 4: Send the sample figure + JSON to Tony and WAIT for his OK before the full run.**

- [ ] **Step 5: Full run (after Tony's OK)**

Run: `.venv/bin/python scripts/pecanstreet_headroom.py` (expect ~2–10 min; the 1-min files
are 127–263 MB gz each).
Expected: three `headroom_<city>.json` + three `headroom_<city>.png` in `outputs/pecanstreet/`;
stdout prints each city's local peak hour (sanity: all in 16–21) and the year-vs-peak hostable
fractions.

- [ ] **Step 6: Record the CA timezone verdict.** Read `headroom_california.json` →
  `diurnal_check.peak_hour_local`. If it lands 16–21, the "stamps are Central instants,
  convert to LA" interpretation is validated — write one sentence confirming this into
  `outputs/pecanstreet/siting_research.md` under a "## CA timezone verdict" heading (it gets
  folded into note M). If it lands elsewhere (e.g., 13–15), the stamps were local-PT clock
  readings mislabeled with Central offsets: change `CITY_TZ["california"]` to
  `"America/Chicago"` in the lib (making ts read back the as-recorded clock), re-run CA, and
  document.

- [ ] **Step 7: ASK Tony for permission to commit.** If granted:

```bash
git add scripts/pecanstreet_headroom.py
git commit -m "feat(pecanstreet): XFRA headroom analysis across Austin/NY/CA bundles"
```

---

### Task 5: `scripts/pecanstreet_1sec.py`

**Files:**
- Create: `scripts/pecanstreet_1sec.py`

- [ ] **Step 1: Write the script**

```python
# scripts/pecanstreet_1sec.py
"""RQ3: residential fast volatility vs a DC-style oscillating node.

Usage:
  .venv/bin/python scripts/pecanstreet_1sec.py --city austin --sample        # eyeball first
  .venv/bin/python scripts/pecanstreet_1sec.py --city austin --node-kw 1,5,10

Streams the 1-sec bundle files (never loads one whole); per home it
accumulates |delta| histograms at 1/10/60-s lags, top step events, and a
Welch PSD (fs=1 Hz -> Nyquist 0.5 Hz, which only grazes the bottom of the
0.1-30 Hz band in the NERC LLTF record — stated plainly in note M). A city
aggregate is built second-by-second into preallocated arrays; aggregate
deltas are taken only between adjacent seconds with the same reporting
count (composition changes are not volatility); the
synchronization index Var(d_agg)/sum Var(d_i) distinguishes idiosyncratic
(~1, cancels like UKPN DC sites) from synchronized (~N) fast noise, and an
exact N-curve at 1-min resolution complements it. A synthetic XFRA node
(square wave, 90% amplitude, --node-kw sizes) is compared against the
measured natural-swing distributions.
"""
from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import pecanstreet_lib as pslib

CHUNK = 2_000_000
# Preallocated aggregate spans (UTC epoch seconds), margins included.
AGG_SPAN = {
    "austin": (1514678400, 1546387200),     # 2017-12-31 .. 2019-01-02
    "new_york": (1556409600, 1572825600),   # 2019-04-28 .. 2019-11-04
}
MIN_HOMES_FOR_AGG = 20


def onesec_files(city: str) -> list:
    d = pslib.ELEC / pslib.CITY_DIR[city]
    return sorted(d.glob("1s_data_*file*.csv.gz"))


def stream_city(city: str, node_kws: list[float], sample: bool, outdir) -> dict:
    t0, t1 = AGG_SPAN[city]
    agg_sum = np.zeros(t1 - t0, dtype=np.float64)
    agg_cnt = np.zeros(t1 - t0, dtype=np.int16)
    homes: dict[int, dict] = {}

    for path in onesec_files(city):
        header = pd.read_csv(path, nrows=0).columns
        assert "grid" in header, f"no grid column in {path.name}"
        gen_cols = [c for c in ("solar", "solar2") if c in header]
        usecols = ["dataid", "localminute", "grid", *gen_cols]
        print("streaming", path.name, flush=True)
        for chunk in pd.read_csv(path, usecols=usecols, chunksize=CHUNK):
            ts = pd.to_datetime(chunk["localminute"], utc=True)
            # pandas 3 parses strings to datetime64[us]; NEVER astype()//10**9.
            epoch_all = ts.dt.as_unit("s").astype("int64").to_numpy()
            use_s = chunk["grid"].astype(float)
            for c in gen_cols:
                use_s = use_s + chunk[c].fillna(0.0)
            use_all = use_s.to_numpy()
            for dataid in chunk["dataid"].unique():
                m = (chunk["dataid"] == dataid).to_numpy()
                epoch, use = epoch_all[m], use_all[m]
                st = homes.setdefault(int(dataid), {
                    "hists": {lag: pslib.DeltaHist(lag) for lag in (1, 10, 60)},
                    "top": pslib.TopEvents(k=50),
                    "psd": pslib.PsdAccumulator(),
                    "n": 0,
                })
                st["n"] += len(use)
                for h in st["hists"].values():
                    h.update(epoch, use)
                st["top"].update(int(dataid), epoch, use)
                st["psd"].update(epoch, use)
                ok = (epoch >= t0) & (epoch < t1) & ~np.isnan(use)
                np.add.at(agg_sum, epoch[ok] - t0, use[ok])
                np.add.at(agg_cnt, epoch[ok] - t0, 1)
            if sample:
                break
        if sample:
            break

    # --- aggregate deltas over seconds where >= MIN_HOMES report, taken only
    # between adjacent seconds with the SAME reporting count: a composition
    # change adds a whole-home-sized jump (~1 kW) to a distribution whose real
    # 1-s median is ~0.01 kW. Equal counts kill all of that except the rare
    # exact swap (one home drops the same second another appears). The +2 bump
    # at each count change makes DeltaHist see a gap there; virtual epochs stay
    # strictly increasing, so the existing run-splitting does the rest.
    valid = agg_cnt >= MIN_HOMES_FOR_AGG
    idx = np.where(valid)[0]
    agg_hist = pslib.DeltaHist(lag_s=1)
    if len(idx):
        cnt = agg_cnt[idx]
        bumps = np.zeros(len(idx), dtype=np.int64)
        bumps[1:][(np.diff(idx) == 1) & (np.diff(cnt) != 0)] = 2
        agg_hist.update(idx + np.cumsum(bumps), agg_sum[idx])
    sum_var_i = sum(
        st["hists"][1].summary()["std_kw"] ** 2 for st in homes.values() if st["hists"][1].n
    )
    agg_summary = agg_hist.summary()
    sync_index = (agg_summary["std_kw"] ** 2 / sum_var_i) if sum_var_i else float("nan")

    # City top-50 = merge of the per-home top-50s (exact, and avoids feeding
    # one TopEvents accumulator rows from different homes back to back).
    top_city = sorted(
        (e for st in homes.values() for e in st["top"].result()),
        key=lambda e: -e["delta_kw"],
    )[:50]

    result = {
        "city": city, "n_homes": len(homes),
        "per_home": {
            did: {
                "n_seconds": st["n"],
                "delta": {f"lag{lag}s": h.summary() for lag, h in st["hists"].items()},
                "top_events": st["top"].result()[:5],
                "psd_segments": st["psd"].n_segments,
            } for did, st in homes.items()
        },
        "aggregate": {"delta_1s": agg_summary, "sync_index": sync_index,
                      "n_valid_seconds": int(valid.sum()),
                      "min_homes_for_agg": MIN_HOMES_FOR_AGG},
        "top_events_city": top_city,
        "node_comparison": node_comparison(homes, agg_summary, node_kws),
    }
    psd_figure(city, homes, outdir)
    return result


def node_comparison(homes: dict, agg_summary: dict, node_kws: list[float]) -> dict:
    """A square-wave node at 0.2 Hz swings NODE_AMPLITUDE*P twice per 5-s period."""
    p999 = [st["hists"][1].summary()["p999_kw"] for st in homes.values() if st["hists"][1].n]
    out = {"home_natural_1s_p999_median_kw": float(np.median(p999)),
           "home_natural_1s_p999_max_kw": float(np.max(p999)),
           "aggregate_1s_std_kw": agg_summary["std_kw"], "nodes": {}}
    for p in node_kws:
        step = pslib.NODE_AMPLITUDE * p
        out["nodes"][f"{p:g}kW"] = {
            "step_kw": step,
            "vs_median_home_p999": step / out["home_natural_1s_p999_median_kw"],
            "n_homes_whose_max_natural_step_exceeds_it": int(
                sum(st["hists"][1].max >= step for st in homes.values())),
        }
    return out


def psd_figure(city: str, homes: dict, outdir) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    for _did, st in homes.items():
        freqs, psd = st["psd"].result()
        if len(freqs):
            ax.loglog(freqs[1:], psd[1:], lw=0.5, alpha=0.5)
    ax.axvspan(0.1, 0.5, alpha=0.15, color="red",
               label="overlap with DC 0.1-30 Hz band")
    ax.set(xlabel="Hz", ylabel="PSD (kW²/Hz)", title=f"{city}: per-home whole-home PSD")
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / f"onesec_psd_{city}.png", dpi=150)
    plt.close(fig)


def ncurve_1min(city: str, outdir, n_draws: int = 10, seed: int = 0) -> dict:
    """Exact sigma(delta) vs N at 1-min resolution (complement to sync_index)."""
    df = pslib.read_power(city, "1minute")
    df["use"] = pslib.reconstruct_use(df)
    wide = df.pivot_table(index="ts", columns="dataid", values="use")
    deltas = wide.diff().dropna(how="all")
    rng = np.random.default_rng(seed)
    cols = list(deltas.columns)
    curve = {}
    for n in range(1, len(cols) + 1):
        sigmas = []
        for _ in range(n_draws):
            pick = rng.choice(cols, size=n, replace=False)
            sigmas.append(float(deltas[pick].sum(axis=1, min_count=n).std()))
        curve[n] = float(np.median(sigmas))
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ns = np.array(list(curve))
    ax.plot(ns, list(curve.values()), "o-", label="measured")
    ax.plot(ns, curve[1] * np.sqrt(ns), "--", label="sqrt(N) (independent)")
    ax.plot(ns, curve[1] * ns, ":", label="N (synchronized)")
    ax.set(xlabel="N homes", ylabel="sigma of aggregate 1-min delta (kW)", title=city)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outdir / f"ncurve_1min_{city}.png", dpi=150)
    plt.close(fig)
    return curve


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", choices=list(AGG_SPAN), action="append")
    ap.add_argument("--sample", action="store_true", help="first chunk only: eyeball mode")
    ap.add_argument("--node-kw", default="1,5,6.25,12.5,19.2")
    ap.add_argument("--outdir", default=str(pslib.OUTDIR))
    args = ap.parse_args()
    outdir = pslib.Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    node_kws = [float(x) for x in args.node_kw.split(",")]

    for city in (args.city or list(AGG_SPAN)):
        result = stream_city(city, node_kws, args.sample, outdir)
        result["ncurve_1min"] = ncurve_1min(city, outdir) if not args.sample else None
        suffix = "_sample" if args.sample else ""
        (outdir / f"onesec_{city}{suffix}.json").write_text(json.dumps(result, indent=2))
        print(city, "sync_index:", result["aggregate"]["sync_index"],
              "| node table:", json.dumps(result["node_comparison"]["nodes"]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lint**

Run: `.venv/bin/ruff check scripts/pecanstreet_1sec.py`
Expected: clean.

- [ ] **Step 3: Sample run (eyeball gate)**

Run: `.venv/bin/python scripts/pecanstreet_1sec.py --city austin --sample`
Expected (first 2M rows ≈ one home): per-home `delta.lag1s.p50_kw` in the 0.001–0.05 kW
range (most seconds are quiet), `max_kw` in the 1–10 kW range (compressor/oven steps),
`psd_segments` > 0. **If p50 ≈ max, or everything is NaN: STOP and debug the run-splitting.**

- [ ] **Step 4: Send the sample JSON summary + PSD figure to Tony; WAIT for OK.**

- [ ] **Step 5: Full runs (after OK), in the background**

Run: `.venv/bin/python scripts/pecanstreet_1sec.py --city austin` then
`--city new_york` (Bash `run_in_background=true`; expect 0.5–1.5 h each — the Austin files
are ~13 GB gz. The harness notifies on completion; don't poll.)
Expected: `onesec_austin.json`, `onesec_new_york.json`, PSD + N-curve PNGs.

- [ ] **Step 6: Plausibility checks on the full outputs** (each violation = investigate
  before writing the note):
  - `n_homes` == 25 per city (or document the shortfall);
  - `sync_index` between ~0.5 and ~25 (outside → bug);
  - `n_valid_seconds` is several million (a tiny value means the ≥20-home mask or the
    equal-count composition guard collapsed — investigate before trusting `sync_index`);
  - N-curve rises with N and sits at-or-near the sqrt(N) reference if idiosyncratic;
  - city top events ≤ ~50 kW (a 100 kW household step is a data error, not an appliance).

- [ ] **Step 7: ASK Tony for permission to commit.** If granted:

```bash
git add scripts/pecanstreet_1sec.py
git commit -m "feat(pecanstreet): 1-sec volatility pass - delta histograms, PSD, aggregate cancellation, node comparison"
```

---

### Task 6: interpretation checkpoint

- [ ] **Step 1: Write a 10-line summary** of what RQ2 + RQ3 found (hostable fractions year vs
  peak per city; sync index + N-curve verdict; node table) and post it in the session.
- [ ] **Step 2: Discuss with Tony** — the note's framing depends on which result is the
  headline. WAIT for his read before Task 7+.

---

### Task 7: regression pins

**Files:**
- Create: `tests/regression/test_pecanstreet_pins.py`

- [ ] **Step 1: Write the pin test.** Copy the actual production numbers from
`outputs/pecanstreet/headroom_austin.json` into the literals below. `FILL_FROM_RUN` is the
single intentional fill-in in this plan — a pin cannot know production numbers before the
production run exists; the executor replaces each with the number from the JSON:

```python
"""Pins production numbers from the 2026-08 pecanstreet runs.

A failure here after a code change is a real behavior change, not flakiness.
Recomputes ONE home-month through the lib (fast path) and checks it against
the values produced by the full production run.
"""
from __future__ import annotations

import pandas as pd
import pytest

from scripts import pecanstreet_lib as pslib

pytestmark = pytest.mark.skipif(not pslib.RAW.exists(), reason="pecanstreet data not on disk")


def test_austin_661_july_2018_pins():
    df = pslib.read_power("austin", "1minute")
    df = df[df["dataid"] == 661]
    ts = pd.DatetimeIndex(df["ts"])
    df = df[(ts.year == 2018) & (ts.month == 7)]
    m = pslib.headroom_metrics(pslib.reconstruct_use(df))
    assert m["max_kw"] == pytest.approx(FILL_FROM_RUN, rel=1e-6)
    assert m["p999_kw"] == pytest.approx(FILL_FROM_RUN, rel=1e-6)
    assert m["hostable_kw"]["200A"] == pytest.approx(FILL_FROM_RUN, rel=1e-6)
```

- [ ] **Step 2: Run it**

Run: `.venv/bin/pytest tests/regression/test_pecanstreet_pins.py -q`
Expected: 1 passed (in ~1–2 min; it reads the real 1-min file).

- [ ] **Step 3: ASK Tony for permission to commit.** If granted:

```bash
git add tests/regression/test_pecanstreet_pins.py
git commit -m "test(pecanstreet): pin headroom numbers from the production run"
```

---

### Task 8: research note M + index/catalog updates

**Files:**
- Create: `docs/research-notes/M-pecanstreet-xfra-headroom.md`
- Modify: `docs/research-notes/INDEX.md` (add one line, following the existing letter rows)
- Modify: `docs/sources/data-catalog.md` (mark the pecanstreet analysis as existing, one line)
- Modify: `docs/plans/advisor/2026-08-19-advisor-meeting-agenda.md` — fill the empty
  `### Pecan street texas dataset` section with 3–5 result bullets. **Leave this file
  uncommitted** (it carries Tony's own uncommitted edits).

- [ ] **Step 1: Write note M** with this exact section order (content from the run outputs;
  every number cited to its JSON file):
  1. **What XFRA is and where it is siting** (RQ1, from `siting_research.md`, incl. the CA
     timezone verdict footnote and node-kw decision).
  2. **Does the headroom exist — and does it survive summer peak?** (RQ2: hostable-fraction
     table year vs peak window per city per scenario; seasonal figure; the CA 2014–2018
     year-to-year stability line from the `yearly` key; the coincidence verdict in one bold
     sentence.)
  3. **Can a panel absorb the volatility?** (RQ3: node table vs natural-swing distributions;
     sync index + N-curve; PSD figure. State the Nyquist honesty caveat: 1-sec grazes only
     the bottom of the 0.1–30 Hz band; the 2 kHz waveform tier would cover it — licensing
     still unanswered.)
  4. **Why subtracting residential from total load cannot isolate DC load** (the four
     reasons from the design doc; closes agenda item 7).
  5. **Caveats:** 2018–19 vintage (pre-boom appliances/EVs), 25-home volunteer sample,
     intervention overlap count (from the JSONs; the `notna()` filter also excludes
     control-arm homes — `CCET - Control`, `Civita - Control` — say so), scenario-band
     denominator (no measured panel sizes), one summer per city except CA, and NY "year"
     stats span May–Oct only — never label NY or pooled-CA numbers "annual".
  6. **Future hooks:** `leg1v/leg2v` 1-sec voltages (power-quality), PR THD set, 2 kHz tier.

- [ ] **Step 2: Add the INDEX.md line** (match the existing table format):
`| \`M-pecanstreet-xfra-headroom.md\` | Whether homes have idle panel capacity for XFRA nodes — and whether it survives summer peak. |`

- [ ] **Step 3: Add the data-catalog line** and fill the agenda section (bullets = the bold
  verdicts from note sections 2–4).

- [ ] **Step 4: Re-read note M start to finish** — every number must trace to a JSON in
  `outputs/pecanstreet/`; every claim beyond the data must carry a source URL from
  `siting_research.md`.

- [ ] **Step 5: ASK Tony for permission to commit** (agenda file stays out). If granted:

```bash
git add docs/research-notes/M-pecanstreet-xfra-headroom.md docs/research-notes/INDEX.md docs/sources/data-catalog.md
git commit -m "docs(pecanstreet): note M - XFRA headroom and 1-sec volatility findings"
```

---

## Self-review (done at write time)

- **Spec coverage:** RQ1 → Task 1; RQ2 (1-min primary, 15-min crosscheck, scenario bands
  with AND without the NEC 0.8 via `hostable_kw_noderate`, coincidence test, cross-city,
  CA year-to-year stability via `yearly_breakdown`, per-home construction-year/sq-footage
  context via the `meta` key, intervention robustness via `hostable_fractions_clean`,
  negative-share reporting) → Task 4; RQ3 (streaming, deltas at 1/10/60 s, PSD with
  NaN-as-gap segmentation, aggregate with the equal-count composition guard, cancellation,
  node comparison) → Tasks 3+5; CA tz resolution → Task 4 Step 6; per-window coverage gate
  (`summer_exposure` ≥ 0.90 for peak-window stats — see amendment A2) → Tasks 2+4;
  sample/eyeball gates →
  Task 4 Steps 3–4 and Task 5 Steps 3–4; subtraction-closure, caveats, out-of-scope →
  Task 8; tests → Tasks 2, 3, 7.
- **Known simplifications vs spec:** (a) the seasonal figure uses the 200A×0.8 scenario
  only — the other scenarios are constant vertical offsets of the same curve, no
  information lost; (b) `off_window` stats are gated on overall coverage rather than their
  own window coverage — the off window is ~92% of all minutes, so the two gates are nearly
  identical; (c) the equal-count aggregate guard cannot exclude the rare exact swap where
  one home drops out in the same second another appears.
- **Type consistency:** `headroom_metrics(load)`, `DeltaHist.update(epoch, use)`,
  `read_power(city, resolution)`, `TopEvents.update(dataid, epoch, use)`,
  `summer_exposure(ts)` — signatures match all call sites shown.
- **`FILL_FROM_RUN` (Task 7) is the single intentional fill-in**, justified above.
- **Review pass 2026-08-14:** three defects fixed after empirical verification against this
  environment (pandas-3 microsecond epochs, the quantile test tolerance, the RUF100 noqa
  trap), four spec gaps closed (CA yearly stability, un-derated headroom, metadata context,
  per-window coverage), and two methodological guards added (aggregate composition guard,
  PSD NaN-as-gap).

---

## Amendments during execution (2026-08-14)

These supersede the task text above where they conflict. Recorded here rather than by
rewriting history, so the reasoning stays auditable.

**A1 — node-kW bracket (supersedes the `1,5,10` fallback).** Task 1 surfaced a real node
spec, so the fallback no longer applies. ~12.5 kW/node is triangulated three ways from a
SPAN CEO interview: 1.25 MW ÷ 100 nodes, 100 MW ÷ 8,000 nodes, and 1,600 GPUs ÷ 100 nodes =
16 GPUs/node matching the white paper's two-module architecture (p.24). Physically
plausible: 16 × RTX PRO 6000 Blackwell at ~600 W ≈ 9.6 kW of GPU plus CPUs and a 35,000 BTU
cooling heat pump. Tony's ruling: evaluate **1, 5, 6.25, 12.5, 19.2 kW** in both
`hostable_fractions` (Task 4) and `--node-kw` (Task 5). The 19.2 figure is retained as an
upper stress case only — it appears to be pv magazine applying the white paper's *used*
40%-of-peak fraction to a "headroom" label, inverting the source's own framing.

**A2 — coverage gate is absolute summer exposure, not self-spanned.** `window_coverage`
built its denominator from the passed timestamps' own extent, so a home holding 11 complete
days of August scored 1.00 while covering ~9% of the real Jun–Sep window (reproduced
2026-08-14). Replaced by `summer_exposure(ts)` = peak-window minutes ÷ `SUMMER_PEAK_MINUTES`
(122 days × 240 min). The ≥0.90 gate now means "at least ~90% of one full summer's
peak-window minutes", which catches both failure modes — a short data extent and a long
extent riddled with gaps. A five-year pooled bundle (CA) returns ~5.0; that is intended.
Rationale for absolute-over-fractional: what makes a per-home summer-peak estimate valid is
absolute exposure to summer afternoons, not what share of the bundle's calendar the home
happens to span. `coverage()` keeps its self-spanned denominator — documented and deliberate
there.

**A3 — `headroom_metrics` must not report 0.0 kW hostable for a home with no data.**
`max(0.0, lim - NaN)` returns `0.0` because NaN comparisons are always False, so a home with
no valid readings was indistinguishable from a completely maxed-out panel — a silent wrong
answer headed for the research note (136/1198 homes lack `grid` per prior corpus work). Now
returns NaN when there are no valid readings; the zero floor still applies to real numbers.

**A4 — `include_groups=False` dropped from `coverage()`.** Verified on pandas 3.0.5: the
kwarg is *accepted*; it is `include_groups=True` that now raises `ValueError`. The
implementer's claimed `TypeError` was false. Code kept as built anyway — the kwarg is
vestigial in pandas 3 and `_one` never touches the grouping column, so output is identical.

**A5 — RQ1 findings that change the framing (feeds Task 8).** The XFRA node is a **firm,
always-on load**, not a passive gap-filler: white paper p.15 says household peaks are
absorbed first by the whole-home battery and then by curtailing EV charging, while "Node
power is maintained continuously," interrupted only for grid outages, utility DR events, or
safety shutdowns. Consequences: (a) `hostable_kw = limit×0.8 − household_max` is the correct
headline metric and the summer-peak coincidence test is the *primary* result rather than a
robustness check; (b) note M section 3 must drop the "node yields to appliances" mechanic
the agenda assumed. Also: siting is **not disclosed** (one hedged secondary source says
"likely Nevada or Arizona"), and the white paper names the 100-node pilot partner only as an
unnamed **build-to-rent** company — a comparability caveat against Pecan Street's
owner-occupied Austin homes that belongs in the caveats section.

**A6 — `DeltaHist` reporting fixes, and four constraints this puts on Task 5.** Review of the
streaming accumulators confirmed `DeltaHist` and `TopEvents` chunk-equivalence survives
adversarial splitting (chunk size 1, zero-length chunks, chunks shorter than the lag, splits
landing exactly on gap boundaries), and that the `sumsq/n - mean²` variance form is fine at
production scale (1e-16 relative error at n=10⁷ — `|delta|` data clusters near zero, so there
is nothing to cancel). Two reporting defects were fixed, and three findings became Task 5
constraints rather than code changes:

- *Fixed:* `summary()["max_kw"]` returned `0.0` when `n == 0`, indistinguishable from a
  genuinely flat load. Now NaN when `n == 0`. Note the trap: the initializer must stay
  `self.max = 0.0`, because `max(nan, x)` returns `nan` in Python and a NaN initializer would
  poison the value permanently.
- *Fixed:* `quantile()` silently returned the 100 kW top bin edge when the true value was
  above it (`np.histogram` drops out-of-range deltas from `counts` while `n` still counts
  them). Now returns `inf` when the quantile falls above the counted mass — visibly distinct
  from the `nan` that means "no data". Real household 1-sec deltas live in 0.001–10 kW and
  100 kW is ~2× the largest swing a 200 A panel can physically produce, so saturation means
  corrupt readings, not load.
- *Task 5 constraint:* the Welch PSD is **chunk-size dependent** — where the >4096 buffer
  flush lands is set by the caller's chunking, not by the data. Measured: whole-feed vs
  1000-sample chunks moved PSD values by up to 48%, and irregular chunking by up to 94%.
  Peak *frequency* was stable in every case; peak *power* was not. So `CHUNK` must stay
  pinned at its constant and be **recorded in note M** as part of what determines the
  reported PSD.
- *Task 5 constraint:* `PsdAccumulator.result()` is destructive (it flushes and clears the
  buffer). Call it exactly once per home, at the end. The Task 5 code as drafted reads
  `st["psd"].n_segments` into the result dict *before* `psd_figure()` calls `result()`, which
  undercounts by up to one segment per home — read it after.
- *Task 5 read-out rule:* any home whose `delta.lag1s.max_kw` exceeds 100 has corrupt
  readings; its `p99_kw`/`p999_kw` are saturated (now `inf`) and must not be published.

**A7 — physically impossible meter readings are filtered (`MAX_PLAUSIBLE_KW = 100.0`).** The
first full run produced an Austin home (`dataid` 7536) with an annual max of 5,308.7 kW
against a p99.9 of 8.45 kW and a mean of 1.31 kW. Investigation, at Tony's instruction to
establish impossibility rather than assume it, found a two-minute telemetry fault on
2018-02-02: at 12:26 every channel flipped sign at once — `grid` +2894.977, `solar`
−8199.953, `oven1` −351.559 — and the **leg voltages read −1,145,948 V and −1,145,406 V on a
nominal 120 V leg**, mirroring to +1,146,134 V at 12:27 before returning to normal at 12:28.
The meter recorded its own failure in a column the analysis was not otherwise using.

Corpus-wide scan: **exactly 2 rows of 31,808,722 exceed 48 kW**, both of them this event.
Excluding them, the corpus maximum is 23.97 kW. There is an empty gap between 24 kW and
2,895 kW, so the threshold is not a tuning knob — any value in that range is identical.
Those two rows were the *sole* reason Austin's 200 A / 12.5 kW headline read 0.96 instead of
1.00. Note M must report the drop count, the affected dataid, and the voltage evidence.
`mask_implausible` is deliberately separate from `reconstruct_use` so the dropped count stays
observable. **Task 5 must apply the same guard** — the 1-sec script builds `use` inline from
`grid`/`solar` rather than calling `reconstruct_use`.

**A8 — intervention redefined: enrolment markers are not treatments.** The strict
`notna().any()` filter excluded every Austin home (all 25 carry
`program_energy_internet_demo='yes'`) and every California home (all 23 carry
`program_civita_group`), so `n_clean` was 0 for two of three cities and the robustness cut
was vacuous. Tony's ruling: `program_baseline` and `program_energy_internet_demo` are
enrolment markers for Pecan Street participation, not load-changing treatments, and do not
disqualify a home. The six real treatments are `program_579`, `program_lg_appliance`,
`program_verizon`, `program_ccet_group`, `program_civita_group`, `program_shines` — but an
explicit **control arm is untreated by definition and is kept** (`'CCET - Control'`,
`'Civita - Control'`, matched case-insensitively on `control`), which also supersedes the
original plan's instruction that note M should say control arms were excluded with the
treated. They are no longer excluded.

**A9 — a SECOND, different data defect: the Austin 1-second bundle zero-fills dropouts.**
Found during the Task 8 write-up review, not by any threshold. Austin's median per-home
maximum 1-second step was 18.09 kW against New York's 5.82 kW — implausible when the same
homes show a median annual *level* max of 12.1 kW at 1-minute resolution. Inspecting
`TopEvents`' recorded `before_kw`/`after_kw` pairs showed **18 of 25 Austin homes have their
largest step touching exactly `0.000` kW, versus 0 of 25 in New York**. A live house never
draws exactly zero, so these are gaps written as `0.000` instead of missing, and the
resumption reads as a ~23 kW instantaneous step. Excluding those homes, Austin's median
per-home max falls to **8.91 kW**, consistent with New York.

Critically, this is **not** the A7 fault family and A7's filter cannot catch it: there is no
sign flip, no impossible voltage, and ~23 kW is a perfectly possible household draw, so it
passes `MAX_PLAUSIBLE_KW` legitimately. The empty 24–2,895 kW gap that justified A7's
threshold was measured on **1-minute levels only**; nothing established an equivalent gap in
the 1-second data, and this defect lives well below it.

Scope of contamination: **maximum-based statistics only.** p99.9 swings are 1.47 (Austin) vs
1.62 kW (New York) — comparable, which is itself evidence the corruption sits in the extreme
tail — and `sync_index`, the N-curve and the PSD are computed from standard deviations and
spectra over tens of millions of seconds, so a few spurious steps per home do not move them.
Note M § 3.5's right-hand column is therefore restricted to the 7 clean Austin homes; on the
full 25 it would read 17/25 at 12.5 kW rather than 2/7, and that apparent Austin/New York
asymmetry (17/25 vs 3/25) is the artifact rather than a real difference between the cities.
Recorded in `docs/sources/data-catalog.md` § 8 so the next reuse of this bundle starts
forewarned.
