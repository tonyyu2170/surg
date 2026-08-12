# Cross-ISO Stage-1 Diagnostics — Plan A (Core + NYISO/CAISO/IESO)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the shared Stage-1 diagnostic core and run the full diagnostic (fetch → panel → volatility trend, level trend, level-vs-volatility horse race) for the three zero-blocker markets: NYISO, CAISO, IESO.

**Architecture:** One market-agnostic computation module (`src/surg/diagnostics/stage1.py`) mirrored from the shipped `scripts/ercot_diagnostic.py` (which stays untouched); per-market pure-transform feature modules with tests (the `ercot_features.py` pattern); per-market fetch scripts and thin diagnostic drivers. Every horse race runs at two windows: the market's maximum clean window and the common-overlap window (2023-01-01 → 2025-04-30).

**Tech Stack:** Python 3.12 venv (`.venv`), pandas, statsmodels, matplotlib (Agg), httpx, pytest. Sources: mis.nyiso.com monthly zips; CAISO OASIS SingleZip (https, keyless); reports-public.ieso.ca annual CSVs.

**Scope note (Plan B exclusion):** MISO, ISONE, SPP, and the 8-market capstone are Plan B, written after this trio lands — SPP's fetch cannot be written placeholder-free until its portal naming enumeration runs, and ISONE's SMD URLs need their own enumeration. Checkpoint resolutions recorded in `docs/sources/availability/cross-iso-data-availability-summary.md` govern both plans.

**Execution conventions:** run in a sibling worktree per the standard branch lifecycle (worktree → FF merge → cleanup). Python is always `.venv/bin/python`; pytest is `.venv/bin/python -m pytest`. Commit steps below assume the user's per-session commit authorization has been granted at execution start; if not, batch and ask.

**Facts already verified (2026-08-09, memos):** all endpoint URLs, schemas, and depths cited below were verified against real downloads — do not re-verify during implementation; the memos (`docs/{nyiso,caiso,ieso}-data-availability-research.md`) are the authority.

---

### Task 1: Venv prerequisites (xlrd + restore declared deps)

The main venv is missing `openpyxl` (declared in pyproject) and has no `pip`; `xlrd` is not declared anywhere. Fix both so this plan and the merged ERCOT scripts can run from the main checkout. `uv` is at `~/.local/bin/uv`.

**Files:**
- Modify: `pyproject.toml` (dependencies list, after the `openpyxl` line)

- [ ] **Step 1: Add xlrd to pyproject dependencies**

In `pyproject.toml`, change:

```toml
    "openpyxl>=3.1",
```

to:

```toml
    "openpyxl>=3.1",
    "xlrd>=2.0",
```

(`xlrd` is needed for MISO/legacy `.xls` in Plan B; declaring it now closes the venv gap in one pass.)

- [ ] **Step 2: Sync the venv**

Run: `uv pip install -e ".[dev]" --python .venv/bin/python`
Expected: installs `xlrd`, `openpyxl`, and any other missing declared deps without error.

- [ ] **Step 3: Verify engines import and suite is green**

Run: `.venv/bin/python -c "import openpyxl, xlrd; print('engines ok')"`
Expected: `engines ok`

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -2`
Expected: all tests pass (baseline 447); record the count.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "build: declare xlrd; sync venv (restores openpyxl)"
```

---

### Task 2: Shared Stage-1 core (`stage1.py`)

Market-agnostic versions of the four ERCOT computations plus the gradient shim. Bodies are mirrored from `scripts/ercot_diagnostic.py:95-338` and `src/surg/preprocessing/ercot_features.py:62-97` with market parameters lifted out. `scripts/ercot_diagnostic.py` is NOT modified.

**Files:**
- Create: `src/surg/diagnostics/__init__.py` (empty)
- Create: `src/surg/diagnostics/stage1.py`
- Test: `tests/test_stage1_core.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the market-agnostic Stage-1 diagnostic core."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from surg.diagnostics.stage1 import (
    add_zone_gradients,
    assert_panel_quality,
    level_vs_volatility,
    trend_tables,
)


def make_panel(hours: int = 24 * 400, seed: int = 7) -> pd.DataFrame:
    """Synthetic two-zone hourly panel with a known level/price link."""
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2023-01-01", periods=hours, freq="h")
    load_a = 1000 + 100 * np.sin(np.arange(hours) * 2 * np.pi / 24) + rng.normal(0, 5, hours)
    load_b = 500 + rng.normal(0, 5, hours)
    panel = pd.DataFrame(
        {
            "datetime_beginning_local": ts,
            "load_mw_alpha": load_a,
            "load_mw_beta": load_b,
            "dst_transition_hour": False,
        }
    )
    panel = add_zone_gradients(panel, ["alpha", "beta"], time_col="datetime_beginning_local")
    # price tracks alpha's LEVEL by construction
    panel["px_hub"] = 20 + 0.05 * panel["load_mw_alpha"] + rng.normal(0, 1, hours)
    return panel


def test_add_zone_gradients_matches_manual_diff():
    panel = make_panel(hours=48)
    manual = panel["load_mw_alpha"].diff().abs() / 60.0
    got = panel["load_gradient_abs_mw_per_min_alpha"]
    pd.testing.assert_series_equal(got, manual, check_names=False)


def test_add_zone_gradients_rejects_unsorted():
    panel = make_panel(hours=48).iloc[::-1].reset_index(drop=True)
    with pytest.raises(ValueError, match="sorted"):
        add_zone_gradients(panel, ["alpha"], time_col="datetime_beginning_local")


def test_assert_panel_quality_passes_clean_panel():
    assert_panel_quality(
        make_panel(), ["alpha", "beta"],
        time_col="datetime_beginning_local", dst_pairs_per_year=0,
    )


def test_assert_panel_quality_catches_duplicate_timestamp():
    panel = make_panel()
    panel.loc[10, "datetime_beginning_local"] = panel.loc[9, "datetime_beginning_local"]
    with pytest.raises(AssertionError, match="duplicate"):
        assert_panel_quality(
            panel.sort_values("datetime_beginning_local").reset_index(drop=True),
            ["alpha", "beta"],
            time_col="datetime_beginning_local", dst_pairs_per_year=0,
        )


def test_assert_panel_quality_catches_nan():
    panel = make_panel()
    panel.loc[5, "load_mw_beta"] = np.nan
    with pytest.raises(AssertionError, match="NaN"):
        assert_panel_quality(
            panel, ["alpha", "beta"],
            time_col="datetime_beginning_local", dst_pairs_per_year=0,
        )


def test_trend_tables_shape_and_normalization(tmp_path):
    panel = make_panel()
    trends = trend_tables(
        panel, ["alpha", "beta"],
        time_col="datetime_beginning_local", figdir=tmp_path, market="TEST",
    )
    assert set(trends["zone"]) == {"alpha", "beta"}
    row = trends[trends["zone"] == "alpha"].iloc[0]
    assert row["grad_mean_norm"] == pytest.approx(row["grad_mean"] / row["mean_load_mw"])
    assert (tmp_path / "trends_by_zone_year.csv").exists()
    assert (tmp_path / "fig1_volatility_trend_normalized.png").exists()
    assert (tmp_path / "fig2_level_trend.png").exists()


def test_level_vs_volatility_finds_planted_level_effect(tmp_path):
    panel = make_panel()
    race = level_vs_volatility(
        panel, ["alpha"], ["px_hub"],
        time_col="datetime_beginning_local",
        window_start=pd.Timestamp("2023-01-01"),
        window_end=pd.Timestamp("2026-01-01"),
        figdir=tmp_path, market="TEST", label="max",
    )
    assert len(race) == 1
    row = race.iloc[0]
    assert row["level_wins"]
    assert row["beta_level"] > 0.5  # planted link is strong
    assert (tmp_path / "fig3_level_vs_volatility_max.csv").exists()


def test_level_vs_volatility_window_filters_rows(tmp_path):
    panel = make_panel()
    race = level_vs_volatility(
        panel, ["alpha"], ["px_hub"],
        time_col="datetime_beginning_local",
        window_start=pd.Timestamp("2023-02-01"),
        window_end=pd.Timestamp("2023-03-01"),
        figdir=tmp_path, market="TEST", label="overlap",
        min_rows=1,
    )
    assert race.iloc[0]["n"] == 28 * 24
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_stage1_core.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'surg.diagnostics'`

- [ ] **Step 3: Implement the core**

Create `src/surg/diagnostics/__init__.py` (empty file), then `src/surg/diagnostics/stage1.py`:

```python
"""Market-agnostic Stage-1 diagnostic computations.

Mirrored from scripts/ercot_diagnostic.py (shipped 2026-08-07) with the
market parameters lifted out; that script stays untouched per the design
spec. Pure computation + figure/CSV writes into a caller-supplied figdir.

Conventions every caller must satisfy:
  * `time_col` is naive local prevailing (or fixed-offset) hour-BEGINNING.
  * one `load_mw_<zone>` column per zone; `dst_transition_hour` bool column.
  * gradients are added via `add_zone_gradients` so the volatility measure
    is provably identical to DOM/ERCOT (delegates to
    `add_load_gradient_columns`).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402

from surg.preprocessing.features import add_load_gradient_columns  # noqa: E402


def add_zone_gradients(
    df: pd.DataFrame, zones: list[str], *, time_col: str
) -> pd.DataFrame:
    """Add `load_gradient_abs_mw_per_min_<zone>` for each zone.

    Same shim as ercot_features.add_zone_gradient_columns: rename each zone
    into the DOM column names, delegate, rename out. `features.py` is not
    modified. Requires sorted input because the underlying diff is
    positional.
    """
    if not df[time_col].is_monotonic_increasing:
        raise ValueError(f"add_zone_gradients requires sorted, non-decreasing {time_col}")

    out = df.copy()
    for zone in zones:
        shim = pd.DataFrame(
            {
                "datetime_beginning_ept": out[time_col],
                "dom_load_mw": out[f"load_mw_{zone}"],
            }
        )
        gradients = add_load_gradient_columns(shim, freq_minutes=60)
        out[f"load_gradient_abs_mw_per_min_{zone}"] = gradients[
            "dom_load_gradient_abs_mw_per_min"
        ].to_numpy()
    return out


def assert_panel_quality(
    panel: pd.DataFrame,
    zones: list[str],
    *,
    time_col: str,
    dst_pairs_per_year: int = 1,
) -> None:
    """Fail loudly on the failure modes that previously bit this project.

    dst_pairs_per_year: 1 for prevailing-time markets (one fall-back pair
    per year), 0 for fixed-offset markets (MISO/IESO-style) where any
    duplicate is a republication, never DST.
    """
    non_dst = panel.loc[~panel["dst_transition_hour"], time_col]
    dupes = non_dst.duplicated().sum()
    if dupes:
        raise AssertionError(f"{dupes} duplicate non-DST timestamps")

    flagged = int(panel["dst_transition_hour"].sum())
    span_years = panel[time_col].dt.year.nunique()
    budget = 2 * dst_pairs_per_year * span_years
    if flagged > budget:
        raise AssertionError(
            f"{flagged} rows flagged dst_transition_hour across {span_years} "
            f"years; expected at most {budget}"
        )

    for zone in zones:
        col = f"load_mw_{zone}"
        if panel[col].isna().any():
            raise AssertionError(f"{col} contains NaN — do not interpolate, investigate")

    span = panel[time_col]
    expected = int((span.max() - span.min()).total_seconds() // 3600) + 1
    if abs(expected - len(panel)) > 48:
        raise AssertionError(f"gap detected: expected ~{expected} rows, got {len(panel)}")


def data_quality_report(
    panel: pd.DataFrame,
    price_cols: list[str],
    *,
    time_col: str,
    window_start: pd.Timestamp,
    figdir: Path,
) -> pd.DataFrame:
    """Rows/year + per-price-column negative share. Read before interpreting."""
    print("\n=== ROWS PER YEAR ===")
    print(panel.groupby(panel[time_col].dt.year).size().to_string())

    matched = panel[panel[time_col] >= window_start]
    rows = []
    for col in price_cols:
        series = matched[col].dropna()
        if series.empty:
            continue
        rows.append(
            {
                "price_series": col,
                "n": len(series),
                "negative_share": (series < 0).mean(),
                "median": series.median(),
                "p99": series.quantile(0.99),
            }
        )
    report = pd.DataFrame(rows).sort_values("negative_share", ascending=False)
    print("\n=== PRICE QUALITY (horse-race window) ===")
    print(report.to_string(index=False))
    figdir.mkdir(parents=True, exist_ok=True)
    report.to_csv(figdir / "price_quality.csv", index=False)
    return report


def trend_tables(
    panel: pd.DataFrame,
    zones: list[str],
    *,
    time_col: str,
    figdir: Path,
    market: str,
) -> pd.DataFrame:
    """Annual level and volatility per zone, raw and load-normalized."""
    year = panel[time_col].dt.year
    rows = []
    for zone in zones:
        grouped = panel.groupby(year)
        mean_load = grouped[f"load_mw_{zone}"].mean()
        grad = grouped[f"load_gradient_abs_mw_per_min_{zone}"]
        frame = pd.DataFrame(
            {
                "zone": zone,
                "mean_load_mw": mean_load,
                "peak_load_mw": grouped[f"load_mw_{zone}"].max(),
                "grad_mean": grad.mean(),
                "grad_p95": grad.quantile(0.95),
            }
        )
        frame["grad_mean_norm"] = frame["grad_mean"] / frame["mean_load_mw"]
        frame["grad_p95_norm"] = frame["grad_p95"] / frame["mean_load_mw"]
        rows.append(frame.reset_index(names="year"))

    trends = pd.concat(rows, ignore_index=True)
    figdir.mkdir(parents=True, exist_ok=True)
    trends.to_csv(figdir / "trends_by_zone_year.csv", index=False)

    for metric, fname in [
        ("mean_load_mw", "fig2_level_trend.png"),
        ("grad_mean_norm", "fig1_volatility_trend_normalized.png"),
    ]:
        fig, ax = plt.subplots(figsize=(10, 6))
        for zone in zones:
            sub = trends[trends["zone"] == zone]
            ax.plot(sub["year"], sub[metric], marker="o", label=zone)
        ax.set_xlabel("year")
        ax.set_ylabel(metric)
        ax.set_title(f"{market} {metric} by zone")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(figdir / fname, dpi=150)
        plt.close(fig)

    print(f"\ntrends -> {figdir}")
    return trends


def level_vs_volatility(
    panel: pd.DataFrame,
    zones: list[str],
    price_cols: list[str],
    *,
    time_col: str,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
    figdir: Path,
    market: str,
    label: str,
    min_rows: int = 1000,
) -> pd.DataFrame:
    """Standardized regression of price on load level vs |gradient|.

    Same caveat as the ERCOT run: no time controls, so beta_level carries
    shared diurnal/seasonal structure. Descriptive horse race only; not
    comparable to the DOM controlled z_slope specification.

    `label` distinguishes the two windows ("max" and "overlap") in output
    filenames per the 2026-08-09 checkpoint decision.
    """
    matched = panel[(panel[time_col] >= window_start) & (panel[time_col] < window_end)]

    rows = []
    for zone in zones:
        level_col = f"load_mw_{zone}"
        vol_col = f"load_gradient_abs_mw_per_min_{zone}"
        for col in price_cols:
            data = matched[[level_col, vol_col, col]].dropna()
            if len(data) < min_rows:
                continue
            standardized = (data - data.mean()) / data.std()
            exog = sm.add_constant(standardized[[level_col, vol_col]])
            fit = sm.OLS(standardized[col], exog).fit()
            rows.append(
                {
                    "zone": zone,
                    "price_series": col,
                    "beta_level": fit.params[level_col],
                    "beta_volatility": fit.params[vol_col],
                    "r2": fit.rsquared,
                    "n": len(data),
                }
            )

    race = pd.DataFrame(rows)
    if not race.empty:
        race["level_wins"] = race["beta_level"].abs() > race["beta_volatility"].abs()
    figdir.mkdir(parents=True, exist_ok=True)
    race.to_csv(figdir / f"fig3_level_vs_volatility_{label}.csv", index=False)

    print(f"\n=== LEVEL vs VOLATILITY ({market}, {label} window) ===")
    if race.empty:
        print("no zone×price cell met min_rows — check window and price coverage")
    else:
        print(race.to_string(index=False))
        print(f"level wins in {race['level_wins'].sum()} of {len(race)} cells")
    return race


COMMON_OVERLAP_START = pd.Timestamp("2023-01-01")
COMMON_OVERLAP_END = pd.Timestamp("2025-05-01")  # exclusive; = through 2025-04-30
FAR_FUTURE = pd.Timestamp("2030-01-01")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_stage1_core.py -q`
Expected: 8 passed

- [ ] **Step 5: Full suite + commit**

Run: `.venv/bin/python -m pytest -q 2>&1 | tail -2`
Expected: baseline + 8 passing.

```bash
git add src/surg/diagnostics/ tests/test_stage1_core.py
git commit -m "feat(diagnostics): market-agnostic Stage-1 core mirrored from ERCOT"
```

---

### Task 3: NYISO fetch script

Monthly zips, three families, resumable. Depths verified: `palIntegrated` 2001-06 →, `damlbmp` zone 1999-11 →, `realtime` zone 2001-06 →.

**Files:**
- Create: `scripts/nyiso_fetch.py`

- [ ] **Step 1: Write the script**

```python
"""Download NYISO monthly archive zips: load + DA/RT zonal LBMP.

All public, no key, no quota (politeness sleep only). Verified 2026-08-09:
  palIntegrated : 2001-06 -> present  (hourly integrated actual load, 11 zones)
  damlbmp/_zone : 1999-11 -> present  (DA zonal LBMP, decomposed columns)
  realtime/_zone: 2001-06 -> present  (RT zonal LBMP)

Usage: .venv/bin/python scripts/nyiso_fetch.py
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

RAW = Path("data/raw/nyiso")
BASE = "http://mis.nyiso.com/public/csv"
FAMILIES = {
    "palIntegrated": ("palIntegrated", pd.Timestamp("2001-06-01")),
    "damlbmp_zone": ("damlbmp", pd.Timestamp("1999-11-01")),
    "realtime_zone": ("realtime", pd.Timestamp("2001-06-01")),
}
SLEEP_S = 2.0


def month_starts(first: pd.Timestamp) -> list[pd.Timestamp]:
    last = pd.Timestamp.today().normalize().replace(day=1)
    return list(pd.date_range(first, last, freq="MS"))


def fetch_family(client: httpx.Client, key: str, family: str, first: pd.Timestamp) -> None:
    dest = RAW / key
    dest.mkdir(parents=True, exist_ok=True)
    suffix = "_zone" if key.endswith("_zone") else ""
    for month in month_starts(first):
        stamp = month.strftime("%Y%m%d")
        name = f"{stamp}{family}{suffix}_csv.zip"
        out = dest / name
        if out.exists() and out.stat().st_size > 0:
            continue
        url = f"{BASE}/{family}/{name}"
        resp = client.get(url, timeout=120.0, follow_redirects=True)
        if resp.status_code == 404:
            raise RuntimeError(f"unexpected 404 (verified depth says it exists): {url}")
        resp.raise_for_status()
        out.write_bytes(resp.content)
        print(f"  {key} {stamp} ({len(resp.content)//1024} KB)", flush=True)
        time.sleep(SLEEP_S)


def main() -> None:
    with httpx.Client() as client:
        for key, (family, first) in FAMILIES.items():
            print(f"== {key}")
            fetch_family(client, key, family, first)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test on two months**

Run a temporary harness that shrinks the window, then execute it:

```bash
.venv/bin/python - <<'EOF'
import importlib.util
import pandas as pd
spec = importlib.util.spec_from_file_location("nf", "scripts/nyiso_fetch.py")
nf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nf)
nf.FAMILIES = {"palIntegrated": ("palIntegrated", pd.Timestamp("2026-06-01"))}
nf.main()
EOF
```

Expected: 2–3 zips land in `data/raw/nyiso/palIntegrated/`; no errors.

- [ ] **Step 3: Commit**

```bash
git add scripts/nyiso_fetch.py
git commit -m "feat(nyiso): monthly-zip fetch for load and zonal LBMP"
```

---

### Task 4: NYISO features module

Pure transforms: zips → wide hourly panel + price frame. Verified schemas:
load `"Time Stamp","Time Zone","Name","PTID","Integrated Load"`; DA LBMP
`Time Stamp,Name,PTID,LBMP ($/MWHr),Marginal Cost Losses ($/MWHr),Marginal Cost Congestion ($/MWHr)`.

**Files:**
- Create: `src/surg/preprocessing/nyiso_features.py`
- Test: `tests/test_nyiso_features.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for NYISO pure transforms."""
from __future__ import annotations

import pandas as pd
import pytest

from surg.preprocessing.nyiso_features import ZONES, parse_lbmp, parse_load


def load_frame(rows):
    return pd.DataFrame(
        rows, columns=["Time Stamp", "Time Zone", "Name", "PTID", "Integrated Load"]
    )


def all_zone_rows(stamp, tz, value):
    names = [
        "CAPITL", "CENTRL", "DUNWOD", "GENESE", "HUD VL", "LONGIL",
        "MHK VL", "MILLWD", "N.Y.C.", "NORTH", "WEST",
    ]
    return [[stamp, tz, n, 61750 + i, value] for i, n in enumerate(names)]


def test_parse_load_wide_and_hour_beginning():
    raw = load_frame(
        all_zone_rows("07/01/2026 00:00:00", "EDT", 1000.0)
        + all_zone_rows("07/01/2026 01:00:00", "EDT", 1100.0)
    )
    panel = parse_load(raw)
    assert list(panel["datetime_beginning_ept"]) == [
        pd.Timestamp("2026-07-01 00:00:00"),
        pd.Timestamp("2026-07-01 01:00:00"),
    ]
    assert panel.loc[0, "load_mw_nyc"] == 1000.0
    assert set(f"load_mw_{z}" for z in ZONES) <= set(panel.columns)
    assert not panel["dst_transition_hour"].any()


def test_parse_load_flags_fallback_pair():
    raw = load_frame(
        all_zone_rows("11/02/2025 01:00:00", "EDT", 900.0)
        + all_zone_rows("11/02/2025 01:00:00", "EST", 905.0)
    )
    panel = parse_load(raw)
    assert len(panel) == 2
    assert panel["dst_transition_hour"].all()


def test_parse_load_rejects_missing_zone():
    rows = all_zone_rows("07/01/2026 00:00:00", "EDT", 1000.0)[:-1]
    with pytest.raises(ValueError, match="WEST"):
        parse_load(load_frame(rows))


def test_parse_lbmp_wide():
    raw = pd.DataFrame(
        {
            "Time Stamp": ["07/01/2026 00:00", "07/01/2026 00:00"],
            "Name": ["CAPITL", "N.Y.C."],
            "PTID": [61757, 61761],
            "LBMP ($/MWHr)": [53.6, 60.1],
            "Marginal Cost Losses ($/MWHr)": [1.9, 3.2],
            "Marginal Cost Congestion ($/MWHr)": [0.0, -2.0],
        }
    )
    prices = parse_lbmp(raw, prefix="da_lbmp")
    assert prices.loc[0, "da_lbmp_nyc"] == 60.1
    assert prices.loc[0, "da_lbmp_capitl"] == 53.6
    assert list(prices.columns)[0] == "datetime_beginning_ept"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_nyiso_features.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Pure transforms for the NYISO Stage-1 diagnostic. No I/O."""
from __future__ import annotations

import pandas as pd

# Raw zone name -> column-safe token. 11 zones as reported 2005-01-31
# onward (NOT stable since 1999: pre-split load reports a single combined
# N.Y.C._LONGIL zone instead of this N.Y.C./LONGIL pair — see the
# 2026-08-09 zone-convention fix landed after this task, which also drops
# four external interface/proxy buses from the price side).
ZONE_MAP = {
    "CAPITL": "capitl", "CENTRL": "centrl", "DUNWOD": "dunwod",
    "GENESE": "genese", "HUD VL": "hud_vl", "LONGIL": "longil",
    "MHK VL": "mhk_vl", "MILLWD": "millwd", "N.Y.C.": "nyc",
    "NORTH": "north", "WEST": "west",
}
ZONES = list(ZONE_MAP.values())


def _timestamps(series: pd.Series) -> pd.Series:
    ts = pd.to_datetime(series, format="mixed")
    if ts.isna().any():
        bad = series[ts.isna()].head(3).tolist()
        raise ValueError(f"unparseable Time Stamp values: {bad}")
    return ts


def parse_load(raw: pd.DataFrame) -> pd.DataFrame:
    """Long zone rows -> wide hourly `load_mw_<zone>`, hour-beginning EPT.

    NYISO stamps are already hour-beginning prevailing Eastern; the
    `Time Zone` column disambiguates the fall-back hour (01:00 EDT and
    01:00 EST both appear). We keep prevailing wall-clock as the panel key
    (DOM convention) and flag the duplicated pair via dst_transition_hour.
    """
    out = raw.copy()
    out["datetime_beginning_ept"] = _timestamps(out["Time Stamp"])
    unknown = set(out["Name"]) - set(ZONE_MAP)
    if unknown:
        raise ValueError(f"unknown NYISO zone names: {sorted(unknown)}")

    wide = (
        out.pivot_table(
            index=["datetime_beginning_ept", "Time Zone"],
            columns="Name", values="Integrated Load", aggfunc="first",
        )
        .rename(columns=ZONE_MAP)
        .add_prefix("load_mw_")
        .reset_index()
    )
    missing = [z for z in ZONES if f"load_mw_{z}" not in wide.columns]
    if missing:
        missing_raw = [k for k, v in ZONE_MAP.items() if v in [m for m in ZONES if f"load_mw_{m}" not in wide.columns]]
        raise ValueError(f"zones missing from load frame: {missing_raw}")

    wide = wide.sort_values(["datetime_beginning_ept", "Time Zone"], ascending=[True, False])
    wide["dst_transition_hour"] = wide["datetime_beginning_ept"].duplicated(keep=False)
    return wide.drop(columns=["Time Zone"]).reset_index(drop=True)


def parse_lbmp(raw: pd.DataFrame, *, prefix: str) -> pd.DataFrame:
    """Long zone LBMP rows -> wide `{prefix}_<zone>` hourly frame.

    Stage 1 uses TOTAL price only; the loss/congestion columns are ignored
    here (decomposition analysis is out of Stage-1 scope by design).
    Fall-back duplicate stamps average into one value (the ERCOT precedent:
    load keeps two rows, price one, merged many-to-one).
    """
    out = raw.copy()
    out["datetime_beginning_ept"] = _timestamps(out["Time Stamp"])
    unknown = set(out["Name"]) - set(ZONE_MAP)
    if unknown:
        raise ValueError(f"unknown NYISO zone names: {sorted(unknown)}")
    out["zone"] = out["Name"].map(ZONE_MAP)

    hourly = (
        out.groupby(["datetime_beginning_ept", "zone"])["LBMP ($/MWHr)"]
        .mean()
        .unstack("zone")
    )
    hourly.columns = [f"{prefix}_{c}" for c in hourly.columns]
    return hourly.reset_index()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_nyiso_features.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/nyiso_features.py tests/test_nyiso_features.py
git commit -m "feat(nyiso): pure transforms for load and zonal LBMP"
```

---

### Task 5: NYISO diagnostic driver + production run

**Files:**
- Create: `scripts/nyiso_diagnostic.py`

- [ ] **Step 1: Write the driver**

**Superseded 2026-08-09.** The driver originally printed here was a
single-panel design that could not run against the real archive: `parse_load`
raises on the pre-2005-01-31 combined `N.Y.C._LONGIL` zone (present from the
start of the load archive, 2001-06, through 2005-01-30) and `parse_lbmp`
raises on four external interface/proxy buses (`H Q`, `NPX`, `O H`, `PJM`)
present in every price file across the whole archive. Both defects and their
fixes are recorded in `docs/decisions.md`. The fixed `nyiso_features.py`
supports two zone conventions via `parse_load(..., merge_nyc_longil=...)`,
so the driver now builds **two panels** rather than one:

  * Panel A (merged, `nyc_longil` combined, 10 zones): full load-archive
    depth from 2001-06-01. Writes
    `data/interim/nyiso_diagnostic_panel_merged.parquet` and
    `outputs/nyiso_diagnostic_merged/`.
  * Panel B (split, today's 11-zone convention): from 2005-01-31 onward —
    the raw load frame is filtered to that window *before* `parse_load`
    runs, so its unknown-zone-name guard stays live rather than being
    silenced. Writes `data/interim/nyiso_diagnostic_panel_split.parquet`
    and `outputs/nyiso_diagnostic_split/`.

Both panels also run the common-overlap window. The price side (11 NY
zones, four external buses dropped) is identical in both panels and is
read once, not rebuilt per panel. The actual shipped driver is
`scripts/nyiso_diagnostic.py`; its content is not reproduced here to avoid
a second copy that can drift from the real file.

- [ ] **Step 2: Smoke run on the two already-fetched months**

Run: `.venv/bin/python scripts/nyiso_diagnostic.py`
Expected on partial data: it fails loudly at `read_family("damlbmp_zone")` (no zips yet) — confirming the guard works. Then smoke-fetch one month of each family (same harness pattern as Task 3 Step 2 with all three families at `2026-06-01`) and re-run.
Expected after: small panel builds; quality gate passes for the contiguous span; overlap-window race prints the empty-cell message (fine at smoke scale).

- [ ] **Step 3: Full fetch (background)**

Run: `nohup .venv/bin/python scripts/nyiso_fetch.py > ~/nyiso-fetch.log 2>&1 &`
Expected: ~926 zips (~300/family), ~2–3 h at the 2 s sleep. Monitor: `tail -f ~/nyiso-fetch.log`.

- [ ] **Step 4: Production run**

Run: `.venv/bin/python scripts/nyiso_diagnostic.py 2>&1 | tee ~/nyiso-diagnostic-run.log`
Expected (actual, 2026-08-09): Panel A (merged) `(220290, 44)`; Panel B (split) `(188648, 46)`; both quality gates pass; each panel's figures + CSVs land in its own `outputs/nyiso_diagnostic_{merged,split}/` directory. **Read the data-quality report before interpreting** (gate criterion: data-quality gate, not results gate). ⚠️ If early-era RT files change cadence (pre-2005 eras), `parse_lbmp`'s hourly `groupby(...).mean()` already normalizes them — but check the rows/year table for anomalies and note any in the entry.

- [ ] **Step 5: Record results**

Append a decisions.md entry (dated section, repo convention): rows/year anomalies if any; trend headline (system + per-zone load growth % and normalized-volatility % change, earliest→latest full year); both horse-race tables (max + overlap) with the no-time-controls caveat and the NYISO memo §6 caveats (ICAP/SCR, BTM solar, Zone J weather, 2022 crypto moratorium).

- [ ] **Step 6: Commit**

```bash
git add scripts/nyiso_diagnostic.py docs/decisions.md
git commit -m "feat(nyiso): Stage-1 diagnostic driver + production results"
```

---

### Task 6: CAISO fetch script (OASIS)

Chunked keyless pulls. Verified: `SLD_FCST` v1 ACTUAL (hourly TAC rows), `PRC_LMP` v12 DAM per node, https required, GMT interval columns, 2010 depth confirmed.

**Files:**
- Create: `scripts/caiso_fetch.py`

- [ ] **Step 1: Write the script**

```python
"""Download CAISO OASIS actual load + DAM LMPs as CSV-in-zip chunks.

Keyless; informal rate limits -> 6 s sleep, 28-day chunks, retry on
non-zip responses. Verified 2026-08-09: SLD_FCST/ACTUAL v1 returns data
back to 2010 (MRTU era starts 2009-04). https required (http is empty).

Usage: .venv/bin/python scripts/caiso_fetch.py
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx
import pandas as pd

RAW = Path("data/raw/caiso")
BASE = "https://oasis.caiso.com/oasisapi/SingleZip"
LOAD_START = pd.Timestamp("2009-04-01")
PRICE_START = pd.Timestamp("2009-04-01")
CHUNK_DAYS = 28
SLEEP_S = 6.0
NODES = [
    "DLAP_PGAE-APND", "DLAP_SCE-APND", "DLAP_SDGE-APND", "DLAP_VEA-APND",
    "TH_NP15_GEN-APND", "TH_SP15_GEN-APND", "TH_ZP26_GEN-APND",
]


def stamp(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y%m%dT%H:%M-0000")


def pull(client: httpx.Client, params: dict, out: Path) -> None:
    if out.exists() and out.stat().st_size > 0:
        return
    for attempt in range(5):
        resp = client.get(BASE, params=params, timeout=180.0)
        if resp.status_code == 200 and resp.content[:2] == b"PK":
            out.write_bytes(resp.content)
            print(f"  {out.name} ({len(resp.content)//1024} KB)", flush=True)
            time.sleep(SLEEP_S)
            return
        wait = 30 * (attempt + 1)
        print(f"  retry {out.name}: HTTP {resp.status_code}; sleeping {wait}s", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"gave up on {out.name}")


def chunks(start: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    today = pd.Timestamp.today().normalize()
    edges = list(pd.date_range(start, today, freq=f"{CHUNK_DAYS}D"))
    if edges[-1] < today:
        edges.append(today)
    return [(a, b) for a, b in zip(edges, edges[1:]) if a < b]


def main() -> None:
    (RAW / "load").mkdir(parents=True, exist_ok=True)
    (RAW / "da_lmp").mkdir(parents=True, exist_ok=True)
    with httpx.Client() as client:
        for a, b in chunks(LOAD_START):
            pull(client, {
                "queryname": "SLD_FCST", "market_run_id": "ACTUAL", "version": "1",
                "startdatetime": stamp(a), "enddatetime": stamp(b), "resultformat": "6",
            }, RAW / "load" / f"load_{a:%Y%m%d}_{b:%Y%m%d}.zip")
        for node in NODES:
            for a, b in chunks(PRICE_START):
                pull(client, {
                    "queryname": "PRC_LMP", "market_run_id": "DAM", "version": "12",
                    "node": node,
                    "startdatetime": stamp(a), "enddatetime": stamp(b), "resultformat": "6",
                }, RAW / "da_lmp" / f"{node}_{a:%Y%m%d}_{b:%Y%m%d}.zip")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test three recent chunks**

```bash
.venv/bin/python - <<'EOF'
import importlib.util
import pandas as pd
spec = importlib.util.spec_from_file_location("cf", "scripts/caiso_fetch.py")
cf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cf)
cf.LOAD_START = pd.Timestamp.today().normalize() - pd.Timedelta(days=60)
cf.PRICE_START = cf.LOAD_START
cf.NODES = cf.NODES[:1]
cf.main()
EOF
```

Expected: ~3 load zips + ~3 price zips; unzip one of each and confirm the verified headers (`INTERVALSTARTTIME_GMT`, `TAC_AREA_NAME`, `MW`; `NODE`, `LMP_TYPE`).

- [ ] **Step 3: Commit**

```bash
git add scripts/caiso_fetch.py
git commit -m "feat(caiso): chunked OASIS fetch for TAC load + DAM LMPs"
```

---

### Task 7: CAISO features module

**Files:**
- Create: `src/surg/preprocessing/caiso_features.py`
- Test: `tests/test_caiso_features.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for CAISO pure transforms."""
from __future__ import annotations

import pandas as pd
import pytest

from surg.preprocessing.caiso_features import TACS, parse_dam_lmp, parse_load


def load_row(start_gmt: str, tac: str, mw: float) -> dict:
    return {
        "INTERVALSTARTTIME_GMT": start_gmt,
        "TAC_AREA_NAME": tac,
        "MW": mw,
    }


def test_parse_load_converts_gmt_to_prevailing_pacific():
    raw = pd.DataFrame([load_row("2026-01-15T08:00:00-00:00", t, 100.0) for t in TACS])
    panel = parse_load(raw)
    # 08:00 GMT in January = 00:00 PST
    assert panel.loc[0, "datetime_beginning_ppt"] == pd.Timestamp("2026-01-15 00:00:00")
    assert panel.loc[0, "load_mw_caiso_total"] == 100.0


def test_parse_load_ignores_weim_areas():
    raw = pd.DataFrame(
        [load_row("2026-01-15T08:00:00-00:00", t, 100.0) for t in TACS]
        + [load_row("2026-01-15T08:00:00-00:00", "AZPS", 55.0)]
    )
    panel = parse_load(raw)
    assert not any("azps" in c for c in panel.columns)


def test_parse_load_flags_fallback_duplicate():
    # 2025-11-02: 01:00 PDT = 08:00 GMT and 01:00 PST = 09:00 GMT
    raw = pd.DataFrame(
        [load_row("2025-11-02T08:00:00-00:00", t, 100.0) for t in TACS]
        + [load_row("2025-11-02T09:00:00-00:00", t, 100.0) for t in TACS]
    )
    panel = parse_load(raw)
    assert len(panel) == 2
    assert panel["dst_transition_hour"].all()


def test_parse_dam_lmp_filters_lmp_rows_and_pivots():
    raw = pd.DataFrame(
        {
            "INTERVALSTARTTIME_GMT": ["2026-01-15T08:00:00-00:00"] * 2,
            "NODE": ["DLAP_PGAE-APND"] * 2,
            "LMP_TYPE": ["LMP", "MCC"],
            "MW": [51.7, -0.5],
        }
    )
    prices = parse_dam_lmp(raw)
    assert prices.loc[0, "da_lmp_dlap_pgae"] == 51.7
    assert prices.shape[1] == 2  # time + one node
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_caiso_features.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Pure transforms for the CAISO Stage-1 diagnostic. No I/O."""
from __future__ import annotations

import pandas as pd

# CAISO TAC areas only; every other TAC_AREA_NAME in the ACTUAL report is a
# WEIM member whose rows enter in later years and must not leak into the
# panel (roster-growth trap, memo §4).
TAC_MAP = {
    "CA ISO-TAC": "caiso_total", "PGE-TAC": "pge", "SCE-TAC": "sce",
    "SDGE-TAC": "sdge", "VEA-TAC": "vea", "MWD-TAC": "mwd",
}
TACS = list(TAC_MAP)
ZONES = list(TAC_MAP.values())
NODE_MAP = {
    "DLAP_PGAE-APND": "dlap_pgae", "DLAP_SCE-APND": "dlap_sce",
    "DLAP_SDGE-APND": "dlap_sdge", "DLAP_VEA-APND": "dlap_vea",
    "TH_NP15_GEN-APND": "th_np15", "TH_SP15_GEN-APND": "th_sp15",
    "TH_ZP26_GEN-APND": "th_zp26",
}


def _to_ppt(series: pd.Series) -> pd.Series:
    """GMT interval starts -> naive prevailing Pacific wall clock."""
    ts = pd.to_datetime(series, utc=True)
    if ts.isna().any():
        raise ValueError("unparseable INTERVALSTARTTIME_GMT values")
    return ts.dt.tz_convert("America/Los_Angeles").dt.tz_localize(None)


def parse_load(raw: pd.DataFrame) -> pd.DataFrame:
    """OASIS SLD_FCST/ACTUAL rows -> wide hourly `load_mw_<tac>` in PPT."""
    sub = raw[raw["TAC_AREA_NAME"].isin(TACS)].copy()
    if sub.empty:
        raise ValueError("no CAISO TAC rows found — wrong file family?")
    sub["datetime_beginning_ppt"] = _to_ppt(sub["INTERVALSTARTTIME_GMT"])
    sub["_gmt"] = pd.to_datetime(sub["INTERVALSTARTTIME_GMT"], utc=True)

    wide = (
        sub.pivot_table(
            index=["datetime_beginning_ppt", "_gmt"], columns="TAC_AREA_NAME",
            values="MW", aggfunc="first",
        )
        .rename(columns=TAC_MAP)
        .add_prefix("load_mw_")
        .reset_index()
        .sort_values(["datetime_beginning_ppt", "_gmt"])
        .reset_index(drop=True)
    )
    # GMT is unambiguous, so the fall-back pair arrives as two distinct GMT
    # hours mapping to the same PPT wall clock: flag exactly that.
    wide["dst_transition_hour"] = wide["datetime_beginning_ppt"].duplicated(keep=False)
    return wide.drop(columns="_gmt")


def parse_dam_lmp(raw: pd.DataFrame) -> pd.DataFrame:
    """OASIS PRC_LMP rows -> wide hourly `da_lmp_<node>` (total LMP only)."""
    sub = raw[raw["LMP_TYPE"] == "LMP"].copy()
    if sub.empty:
        raise ValueError("no LMP_TYPE == 'LMP' rows — wrong query/version?")
    sub["datetime_beginning_ppt"] = _to_ppt(sub["INTERVALSTARTTIME_GMT"])
    sub["node"] = sub["NODE"].map(NODE_MAP)
    if sub["node"].isna().any():
        unknown = sorted(set(sub.loc[sub["node"].isna(), "NODE"]))
        raise ValueError(f"unexpected CAISO nodes: {unknown}")

    hourly = (
        sub.groupby(["datetime_beginning_ppt", "node"])["MW"].mean().unstack("node")
    )
    hourly.columns = [f"da_lmp_{c}" for c in hourly.columns]
    return hourly.reset_index()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_caiso_features.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/caiso_features.py tests/test_caiso_features.py
git commit -m "feat(caiso): pure transforms for TAC load and DAM LMPs"
```

---

### Task 8: CAISO driver + production run

**Files:**
- Create: `scripts/caiso_diagnostic.py`

- [ ] **Step 1: Write the driver**

**Superseded 2026-08-09.** The driver originally printed here used the full
6-zone `TAC_MAP` roster from `MAX_START = 2009-04-01`, but the CAISO TAC
roster grew over the archive: scanning all 227 completed load zips on disk
found that only 4 of the 6 zones (`CA ISO-TAC`, `PGE-TAC`, `SCE-TAC`,
`SDGE-TAC`) are present from the start of the archive (2009-04-01); `VEA-TAC`
first appears 2013-01-02 and `MWD-TAC` first appears 2018-03-21.
`assert_panel_quality` raises on any NaN in `load_mw_<zone>` across the
whole unwindowed panel, so the 6-zone/2009 combination fails immediately.
The fix (same pattern as the NYISO driver's Task 5 supersession) is a
**two-panel** design rather than one:

  * Panel A (full depth, 4 zones — `caiso_total`, `pge`, `sce`, `sdge`):
    full load-archive depth from 2009-04-01. Writes
    `data/interim/caiso_diagnostic_panel_full_depth.parquet` and
    `outputs/caiso_diagnostic_full_depth/`.
  * Panel B (modern, all 6 zones): from 2018-03-21 onward — the point at
    which the last zone to appear, `MWD-TAC`, has entered the roster. The
    raw load frame is filtered to that window *before* `parse_load` runs.
    Writes `data/interim/caiso_diagnostic_panel_modern.parquet` and
    `outputs/caiso_diagnostic_modern/`.

Both panels also run the common-overlap window. The price side (7
`NODE_MAP` nodes) is identical in both panels and is read once, not rebuilt
per panel. `caiso_features.py` gained a new `FULL_DEPTH_ZONES` constant (the
4-zone list) alongside the existing `ZONES` (the complete 6-zone roster),
with the empirical first-seen dates above recorded in a comment. The actual
shipped driver is `scripts/caiso_diagnostic.py`; its content is not
reproduced here to avoid a second copy that can drift from the real file.

- [ ] **Step 2: Smoke run on the smoke-fetched chunks**

Run: `.venv/bin/python scripts/caiso_diagnostic.py`
Expected: Panel A builds a small panel from the smoke-fetched days and its
quality gate passes; overlap window prints the empty-cell message (fine).
⚠️ Panel B needs load rows from 2018-03-21 onward — if the smoke-fetched
chunks don't reach that date, `parse_load` raises `no CAISO TAC rows found`
for Panel B. That's expected at smoke scale, not a regression; re-check
once the full fetch (Step 3) has run.

⚠️ If `assert_panel_quality` fails on a fall-back pair where OASIS delivered only one of the two GMT hours (possible at chunk edges), check the rows/year print and the chunk boundary before touching tolerance — re-fetch the boundary chunk first.

- [ ] **Step 3: Full fetch (background, ~4–5 h)**

Run: `nohup .venv/bin/python scripts/caiso_fetch.py > ~/caiso-fetch.log 2>&1 &`
~230 load chunks + 7 × ~230 price chunks ≈ 1,840 requests at 6 s ≈ 3.5–5 h. If OASIS returns non-zip beyond the retry budget, double SLEEP_S and rerun — the script resumes past existing files.

- [ ] **Step 4: Production run + record**

Run: `.venv/bin/python scripts/caiso_diagnostic.py 2>&1 | tee ~/caiso-diagnostic-run.log`
Expected: Panel A (full depth) and Panel B (modern) both build; both quality gates pass; each panel's figures + CSVs land in its own `outputs/caiso_diagnostic_{full_depth,modern}/` directory. **Read the data-quality report before interpreting** (gate criterion: data-quality gate, not results gate).

Append the decisions.md entry with the **BTM-solar caveat stapled to the level/volatility trends** (pre-committed framing per checkpoint): metered load ≠ consumption; duck→canyon structural change; WEIM exclusion; Santa Clara invisibility. Note the roster-growth split (full depth vs. modern panels) alongside it.

- [ ] **Step 5: Commit**

```bash
git add scripts/caiso_diagnostic.py docs/decisions.md
git commit -m "feat(caiso): Stage-1 diagnostic driver + production results"
```

---

### Task 9: IESO fetch script

Annual CSVs, three families, trivial volume (~73 files, ~10 MB).

**Files:**
- Create: `scripts/ieso_fetch.py`

- [ ] **Step 1: Write the script**

```python
"""Download IESO annual zonal-demand + HOEP CSVs.

Public open directory, verified 2026-08-09:
  DemandZonal        : PUB_DemandZonal_{YYYY}.csv, 2003 -> present
  Demand (Ontario)   : PUB_Demand_{YYYY}.csv, 2002 -> present
  PriceHOEPPredispOR : PUB_PriceHOEPPredispOR_{YYYY}.csv, 2002 -> (HOEP era
                       ended 2025-04-30 with Market Renewal)

Usage: .venv/bin/python scripts/ieso_fetch.py
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

RAW = Path("data/raw/ieso")
BASE = "https://reports-public.ieso.ca/public"
FAMILIES = {
    "DemandZonal": ("PUB_DemandZonal_{y}.csv", 2003),
    "Demand": ("PUB_Demand_{y}.csv", 2002),
    "PriceHOEPPredispOR": ("PUB_PriceHOEPPredispOR_{y}.csv", 2002),
}
LAST_YEAR = 2026
SLEEP_S = 1.0


def main() -> None:
    with httpx.Client() as client:
        for family, (pattern, first) in FAMILIES.items():
            dest = RAW / family
            dest.mkdir(parents=True, exist_ok=True)
            for year in range(first, LAST_YEAR + 1):
                name = pattern.format(y=year)
                out = dest / name
                if out.exists() and out.stat().st_size > 0:
                    continue
                resp = client.get(f"{BASE}/{family}/{name}", timeout=120.0)
                resp.raise_for_status()
                out.write_bytes(resp.content)
                print(f"  {name} ({len(resp.content)//1024} KB)", flush=True)
                time.sleep(SLEEP_S)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the full fetch (small enough to run inline)**

Run: `.venv/bin/python scripts/ieso_fetch.py`
Expected: ~73 files in a few minutes.

- [ ] **Step 3: Verify the HOEP header assumption**

Run: `head -8 data/raw/ieso/PriceHOEPPredispOR/PUB_PriceHOEPPredispOR_2024.csv`
The memo verified this file's existence but NOT its header. Confirm the columns include `Date`, `Hour`, and `HOEP` — if the real names differ (e.g. `Delivery Date`), update `HOEP_COLS` in Task 10's module accordingly (it is the single named constant wired for this).

- [ ] **Step 4: Commit**

```bash
git add scripts/ieso_fetch.py
git commit -m "feat(ieso): annual-file fetch for zonal demand and HOEP"
```

---

### Task 10: IESO features module

**Files:**
- Create: `src/surg/preprocessing/ieso_features.py`
- Test: `tests/test_ieso_features.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for IESO pure transforms."""
from __future__ import annotations

import pandas as pd
import pytest

from surg.preprocessing.ieso_features import ZONES, parse_demand_zonal, parse_hoep


def demand_frame():
    cols = ["Date", "Hour", "Ontario Demand", "Northwest", "Northeast", "Ottawa",
            "East", "Toronto", "Essa", "Bruce", "Southwest", "Niagara", "West",
            "Zone Total", "Diff"]
    rows = [
        ["2026-01-01", 1, 16526, 688, 1474, 1049, 1085, 5568, 1219, 96, 3000, 569, 1949, 16697, 171],
        ["2026-01-01", 2, 16000, 680, 1450, 1000, 1050, 5400, 1200, 95, 2950, 560, 1900, 16285, 285],
    ]
    return pd.DataFrame(rows, columns=cols)


def test_parse_demand_zonal_hour_beginning_and_wide():
    panel = parse_demand_zonal(demand_frame())
    assert panel.loc[0, "datetime_beginning_est"] == pd.Timestamp("2026-01-01 00:00:00")
    assert panel.loc[1, "datetime_beginning_est"] == pd.Timestamp("2026-01-01 01:00:00")
    assert panel.loc[0, "load_mw_toronto"] == 5568
    assert panel.loc[0, "load_mw_ontario"] == 16526
    assert set(f"load_mw_{z}" for z in ZONES) <= set(panel.columns)
    assert not panel["dst_transition_hour"].any()  # fixed EST: never flagged


def test_parse_demand_zonal_rejects_missing_zone():
    with pytest.raises(ValueError, match="Toronto"):
        parse_demand_zonal(demand_frame().drop(columns=["Toronto"]))


def test_parse_demand_zonal_rejects_bad_hour():
    frame = demand_frame()
    frame.loc[0, "Hour"] = 25
    with pytest.raises(ValueError, match="1-24"):
        parse_demand_zonal(frame)


def test_parse_hoep():
    raw = pd.DataFrame(
        {"Date": ["2024-06-01", "2024-06-01"], "Hour": [1, 2], "HOEP": [25.1, 27.9]}
    )
    prices = parse_hoep(raw)
    assert prices.loc[0, "hoep"] == 25.1
    assert prices.loc[0, "datetime_beginning_est"] == pd.Timestamp("2024-06-01 00:00:00")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ieso_features.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Pure transforms for the IESO Stage-1 diagnostic. No I/O.

IESO files are fixed EST year-round (24 rows/day, no DST rows — verified),
hour-ending 1-24. `dst_transition_hour` is always False and the quality
gate runs with dst_pairs_per_year=0.
"""
from __future__ import annotations

import pandas as pd

ZONE_MAP = {
    "Ontario Demand": "ontario", "Northwest": "northwest", "Northeast": "northeast",
    "Ottawa": "ottawa", "East": "east", "Toronto": "toronto", "Essa": "essa",
    "Bruce": "bruce", "Southwest": "southwest", "Niagara": "niagara", "West": "west",
}
ZONES = list(ZONE_MAP.values())
# Confirmed against the real 2024 file in Task 9 Step 3; adjust here if the
# real header uses different names.
HOEP_COLS = {"date": "Date", "hour": "Hour", "hoep": "HOEP"}


def _hour_ending_to_beginning(dates: pd.Series, hours: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(dates)
    if parsed.isna().any():
        raise ValueError("unparseable Date values in IESO frame")
    numbers = pd.to_numeric(hours, errors="coerce")
    if numbers.isna().any() or not numbers.between(1, 24).all():
        raise ValueError("Hour values outside 1-24 in IESO frame")
    return parsed + pd.to_timedelta(numbers - 1, unit="h")


def parse_demand_zonal(raw: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in ZONE_MAP if c not in raw.columns]
    if missing:
        raise ValueError(f"zones missing from IESO frame: {missing}")

    out = pd.DataFrame(
        {"datetime_beginning_est": _hour_ending_to_beginning(raw["Date"], raw["Hour"])}
    )
    for src, zone in ZONE_MAP.items():
        out[f"load_mw_{zone}"] = pd.to_numeric(raw[src], errors="coerce").to_numpy()
    out["dst_transition_hour"] = False
    return out.sort_values("datetime_beginning_est").reset_index(drop=True)


def parse_hoep(raw: pd.DataFrame) -> pd.DataFrame:
    for key in HOEP_COLS.values():
        if key not in raw.columns:
            raise ValueError(f"HOEP column {key!r} not found; got {list(raw.columns)}")
    out = pd.DataFrame(
        {
            "datetime_beginning_est": _hour_ending_to_beginning(
                raw[HOEP_COLS["date"]], raw[HOEP_COLS["hour"]]
            ),
            "hoep": pd.to_numeric(raw[HOEP_COLS["hoep"]], errors="coerce"),
        }
    )
    return out.sort_values("datetime_beginning_est").reset_index(drop=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ieso_features.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/surg/preprocessing/ieso_features.py tests/test_ieso_features.py
git commit -m "feat(ieso): pure transforms for zonal demand and HOEP"
```

---

### Task 11: IESO driver + production run

**Files:**
- Create: `scripts/ieso_diagnostic.py`

- [ ] **Step 1: Write the driver**

```python
"""Stage-1 IESO diagnostic. Usage: .venv/bin/python scripts/ieso_diagnostic.py

HOEP era only (checkpoint decision 2026-08-09: no MRP-era collector).
Horse-race windows: max = 2003-01 -> 2025-04-30; overlap = 2023-01 -> 2025-04-30.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from surg.diagnostics.stage1 import (
    COMMON_OVERLAP_END, COMMON_OVERLAP_START,
    add_zone_gradients, assert_panel_quality, data_quality_report,
    level_vs_volatility, trend_tables,
)
from surg.preprocessing.ieso_features import ZONES, parse_demand_zonal, parse_hoep

RAW = Path("data/raw/ieso")
PANEL = Path("data/interim/ieso_diagnostic_panel.parquet")
FIGDIR = Path("outputs/ieso_diagnostic")
TIME = "datetime_beginning_est"
MAX_START = pd.Timestamp("2003-01-01")
HOEP_END = pd.Timestamp("2025-05-01")  # exclusive: Market Renewal boundary


def read_family(family: str) -> pd.DataFrame:
    frames = [
        pd.read_csv(path, comment="\\")
        for path in sorted((RAW / family).glob("*.csv"))
    ]
    if not frames:
        raise RuntimeError(f"no files under {RAW / family}")
    return pd.concat(frames, ignore_index=True)


def build_panel() -> pd.DataFrame:
    panel = parse_demand_zonal(read_family("DemandZonal"))
    panel = add_zone_gradients(panel, ZONES, time_col=TIME)
    assert_panel_quality(panel, ZONES, time_col=TIME, dst_pairs_per_year=0)

    hoep = parse_hoep(read_family("PriceHOEPPredispOR"))
    before = len(panel)
    panel = panel.merge(hoep, on=TIME, how="left", validate="m:1")
    if len(panel) != before:
        raise AssertionError(f"HOEP join changed row count: {before} -> {len(panel)}")

    PANEL.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(PANEL, index=False)
    print(f"panel: {panel.shape} -> {PANEL}")
    return panel


if __name__ == "__main__":
    panel = build_panel()
    data_quality_report(panel, ["hoep"], time_col=TIME,
                        window_start=MAX_START, figdir=FIGDIR)
    trend_tables(panel, ZONES, time_col=TIME, figdir=FIGDIR, market="IESO")
    for label, start, end in [
        ("max", MAX_START, HOEP_END),
        ("overlap", COMMON_OVERLAP_START, COMMON_OVERLAP_END),
    ]:
        level_vs_volatility(panel, ZONES, ["hoep"], time_col=TIME,
                            window_start=start, window_end=end,
                            figdir=FIGDIR, market="IESO", label=label)
```

- [ ] **Step 2: Run (data already fetched in Task 9)**

Run: `.venv/bin/python scripts/ieso_diagnostic.py 2>&1 | tee ~/ieso-diagnostic-run.log`
Expected: panel ≈ 207K rows; fixed-EST quality gate passes (a DST flag would fail loudly — that is the gate working); horse race = 11 load series × HOEP.

⚠️ The HOEP annual file may include predispatch/OR columns beyond the three used; `parse_hoep` selects by name and ignores the rest. If the 2002-era files use different headers than 2024 (checked in Task 9 Step 3), extend `HOEP_COLS` handling per era and note it in the entry.

- [ ] **Step 3: Record results**

Append the decisions.md entry with the IESO memo §6 caveats front-of-caption: ICI/Global-Adjustment peak-shaving endogeneity, HOEP = wholesale-energy-only signal, CAD prices, embedded-generation netting, HOEP era ends 2025-04-30.

- [ ] **Step 4: Commit**

```bash
git add scripts/ieso_diagnostic.py docs/decisions.md
git commit -m "feat(ieso): Stage-1 diagnostic driver + production results"
```

---

### Task 12: Trio interim synthesis

**Files:**
- Modify: `docs/decisions.md` (new dated entry)

- [ ] **Step 1: Build the interim comparison table**

From the three `fig3_level_vs_volatility_overlap.csv` files plus the recorded DOM and ERCOT results (decisions.md 2026-08-07 ERCOT entry: level wins 132/135, load +36.7%, normalized volatility −20.7%; DOM figures per the figure-set entries), assemble one table: market | load growth % (earliest→latest full year, system series) | normalized-volatility change % | level-wins fraction (overlap window) | median R². Compute trio numbers from each `trends_by_zone_year.csv` and race CSV with a short throwaway script; the entry shows the numbers, not the script.

- [ ] **Step 2: Write the decisions.md entry**

Dated section: what ran (three markets, both windows), the table, and explicitly what it does NOT support yet (no MISO/ISONE/SPP, no capstone claim, descriptive only, per-market caveats by reference to the memos). Flag anything anomalous for Plan B's design — e.g. a market with *rising* normalized volatility changes the capstone framing.

- [ ] **Step 3: Update the session-state memory file** (`project_state_2026-08-09-cross-iso-phase1.md`): trio shipped, headline numbers, Plan B next (MISO → ISONE SMD hunt → SPP enumeration → capstone).

- [ ] **Step 4: Commit**

```bash
git add docs/decisions.md
git commit -m "docs(decisions): cross-ISO Stage-1 trio results (NYISO/CAISO/IESO)"
```

---

## Self-review (done at write time)

- **Spec coverage:** three outputs ✓ (Tasks 2/5/8/11); shared gradient lineage ✓ (`add_zone_gradients` delegates to `add_load_gradient_columns`); ERCOT script untouched ✓; correctness requirements — explicit hour conventions per market, duplicate/gap/NaN assertions, negative prices unclipped, no interpolation ✓; two-window policy ✓; data-quality gate before interpretation ✓; decisions.md entries ✓. MISO/ISONE/SPP + capstone deferred to Plan B by the scope note, per checkpoint staging.
- **Placeholder scan:** none. The one deliberately deferred fact (exact HOEP header) has a concrete verify-and-adjust step (Task 9 Step 3) wired to a named constant (`HOEP_COLS` in Task 10).
- **Type consistency:** `add_zone_gradients(df, zones, *, time_col)`, `assert_panel_quality(panel, zones, *, time_col, dst_pairs_per_year)`, `level_vs_volatility(..., window_start, window_end, figdir, market, label)` used identically across Tasks 2/5/8/11; `ZONES` / `parse_*` names consistent within each module; drivers all follow the same read → parse → gradients → quality → merge(m:1) → report/trends/race shape.
