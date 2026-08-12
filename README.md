# SURG: Data-Center Load and Electricity Prices

Research on how data-center load shows up in wholesale electricity prices.
The core case study is the PJM Dominion (DOM) zone in Northern Virginia,
asking whether high-frequency load *volatility* or plain load *level* is
what moves congestion prices and price tails at data-center-adjacent nodes,
and how the price response scales as load grows. A companion Stage-1
diagnostic runs the same level-vs-volatility comparison across eight North
American markets: PJM, ERCOT, MISO, SPP, ISO-NE, NYISO, CAISO, and IESO.

Full proposal: [`docs/Yu_Tony_SURG_Grant_Proposal.md`](docs/Yu_Tony_SURG_Grant_Proposal.md).
Methodology and findings are logged in [`docs/decisions.md`](docs/decisions.md).

## Setup

Requires Python 3.11+.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

API keys go in `.env` (see `.env.example`): `PJM_API_KEY` for PJM Data
Miner 2, `GRIDSTATUS_API_KEY_1`–`6` for 5-minute data via gridstatus.io,
and `UK_POWER_API_KEY` for the UK Power Networks open-data portal. The
public archives used by the other North American markets need no key.

## Pipelines

**PJM hourly** — pull raw data, build the panel, run the analysis suite:

```bash
surg-pull --feed rt_hrl_lmps --start 2024-01-01 --end 2024-12-31
surg-prep
surg-analyze
```

`surg-pull` writes `data/raw/<feed>/<year>/*.parquet`, skips chunks already
on disk (`--force` to overwrite), and throttles to ~6 requests/min for
PJM's free tier. The 11 target pnodes are a module constant in
`src/surg/acquisition/targets.py`; rationale in `docs/decisions.md`.

**PJM 5-minute** — the same questions at 5-minute resolution on
gridstatus.io data: backfill via `scripts/gridstatus_backfill_launch.sh`,
analyze with `surg-run-5min`.

**Cross-ISO Stage-1** — each market has a paired fetch + diagnostic driver:

```bash
.venv/bin/python scripts/spp_fetch.py
.venv/bin/python scripts/spp_diagnostic.py
```

Same pattern for `ercot`, `miso`, `isone`, `nyiso`, `caiso`, and `ieso`.

**UK Power Networks** — half-hourly metered demand profiles for ~96
distribution-connected data centres in UKPN's London, East and South East
licence areas (fetch only; no diagnostic driver yet):

```bash
.venv/bin/python scripts/ukpn_fetch.py
```

Writes year-partitioned parquets to `data/raw/ukpn/`, skipping slices
already on disk. This is a **load-shape** dataset — no MW, no location,
no price — and it carries real data-quality traps (13% of rows are exact
zeros; the `local_timestamp` column is actually UTC). Read
[`docs/sources/ukpn-api-constraints.md`](docs/sources/ukpn-api-constraints.md) before
using it.

**Figures** — regenerate the report figure set (module, not path):

```bash
.venv/bin/python -m scripts.plot_subq1_results
```

## Tests

```bash
.venv/bin/pytest                     # full suite; bootstrap-heavy, expect 10+ min
.venv/bin/pytest tests/preprocessing # any subset runs fast
```

## Layout

```
data/         # raw/interim/processed parquets (gitignored)
docs/         # decision log, research notes, source constraints, plans
              # (see docs/README.md for the map)
notebooks/    # exploratory analysis
outputs/      # generated figures and tables (gitignored)
scripts/      # per-ISO fetch + diagnostic drivers, figure pipeline
src/surg/
  acquisition/    # PJM Data Miner + gridstatus.io pulls
  preprocessing/  # loaders, per-market features, panel assembly
  analysis/       # quantile regression, EVT/GPD tails, mechanism diagnostics
  diagnostics/    # shared cross-ISO Stage-1 machinery
tests/
```

## Data

Hourly PJM data comes from [PJM Data Miner 2.0](https://dataminer2.pjm.com/list),
5-minute data from [gridstatus.io](https://www.gridstatus.io), and the other
seven markets from their public archives. Facility-level data-centre load
profiles come from the
[UK Power Networks open-data portal](https://ukpowernetworks.opendatasoft.com)
(CC BY 4.0). No raw data is tracked in git; every panel is reproducible
from the acquisition commands above.

Per-source constraints and gotchas live in `docs/sources/*-api-constraints.md`
(PJM, gridstatus, UKPN, ENTSO-E) and
`docs/sources/availability/*-data-availability-research.md` (the cross-ISO
markets). Findings are indexed in `docs/research-notes/INDEX.md`.
