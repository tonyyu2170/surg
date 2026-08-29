# SURG: Data-Center Load and Electricity Prices

Research on how data-center load shows up in wholesale electricity prices
and on the grid. The core case study is the PJM Dominion (DOM) zone in
Northern Virginia, asking whether high-frequency load *volatility* or plain
load *level* is what moves congestion prices and price tails at
data-center-adjacent nodes. A companion Stage-1 diagnostic runs the same
level-vs-volatility comparison across eight North American markets (PJM,
ERCOT, MISO, SPP, ISO-NE, NYISO, CAISO, IESO) and the seven Italian bidding
zones.

The price question came back null — load *level* prices, volatility does
not, and the near-zero-data-centre control market (ISO-NE) behaves like the
treated ones — so since August 2026 the work has turned to the load itself:
metered facility profiles (UK Power Networks), a national dose–response test
where data centres reached 24% of consumption (Ireland, with the Netherlands
as control), residential panel headroom for behind-the-meter compute (Pecan
Street), and the provenance of the sub-second oscillation claim (NERC LLTF,
arXiv 2508.14318, real GPU telemetry).

Initial proposal: [`docs/Yu_Tony_SURG_Grant_Proposal.md`](docs/Yu_Tony_SURG_Grant_Proposal.md).
Final report: [`docs/final_report.md`](docs/final_report.md) ([PDF](docs/final_report.pdf)),
with its figures in `docs/assets/final_report/`.
Methodology and scope decisions are logged in [`docs/decisions.md`](docs/decisions.md);
findings are indexed in [`docs/research-notes/INDEX.md`](docs/research-notes/INDEX.md).

## Setup

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

API keys go in `.env` (see `.env.example`): `PJM_API_KEY` for PJM Data
Miner 2, `GRIDSTATUS_API_KEY_1`–`6` for 5-minute data via gridstatus.io,
`UK_POWER_API_KEY` for the UK Power Networks open-data portal,
`ENTSOE_API_KEY` for the ENTSO-E Transparency Platform, and
`JUPYTER_API_KEY` + `JUPYTER_USER` for Pecan Street's JupyterHub. The public archives used
by the other North American markets, and the CSO, need no key.

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
licence areas, and the flatness cut that runs on them:

```bash
.venv/bin/python scripts/ukpn_fetch.py
.venv/bin/python scripts/ukpn_flatness.py
```

The fetch writes year-partitioned parquets to `data/raw/ukpn/`, skipping
slices already on disk. This is a **load-shape** dataset — no MW, no
location, no price — and it carries real data-quality traps (13% of rows
are exact zeros; the `local_timestamp` column is actually UTC). Read
[`docs/sources/ukpn-api-constraints.md`](docs/sources/ukpn-api-constraints.md)
before using it.

**ENTSO-E** — load and day-ahead price for 19 European bidding zones
(Ireland, the Netherlands, the Nordics, DE-LU, FR, ES, and the seven
Italian zones), plus Ireland's *measured* data-centre consumption from
the CSO:

```bash
.venv/bin/python scripts/entsoe_fetch.py          # --items load,price --zones IE_CTA,NL
.venv/bin/python scripts/cso_fetch.py             # CSO table MEC02, the dose series
.venv/bin/python scripts/entsoe_ireland.py        # Irish load shape vs dose, NL control
.venv/bin/python scripts/entsoe_solar.py          # is the midday flattening a solar metering artifact?
.venv/bin/python scripts/entsoe_italy_stage1.py   # level-vs-volatility on the Italian zones
```

The API allows 400 requests/min per token and answers a breach with a
ban; the token took three working days to obtain. `entsoe_fetch.py` paces
itself and stops on 429 — do not run `scripts/entsoe_probe.py --hard`.
Constraints and the verified-vs-documented gap are in
[`docs/sources/entsoe-api-constraints.md`](docs/sources/entsoe-api-constraints.md).

**Pecan Street** — residential circuit-level eGauge data (1-sec, 1-min and
15-min) from the Dataport University Free tier, pulled off its JupyterHub:

```bash
.venv/bin/python scripts/pecanstreet_fetch.py
.venv/bin/python scripts/pecanstreet_headroom.py          # idle panel capacity at 100/150/200 A
.venv/bin/python scripts/pecanstreet_1sec.py --city austin # fast volatility vs a synthetic compute node
```

Whole-home use is not a column and has to be reconstructed
(`scripts/pecanstreet_lib.py`); the CA bundle is San Diego homes stamped in
Central time; the Austin 1-second files zero-fill gaps. Read
[`docs/sources/pecanstreet-access-constraints.md`](docs/sources/pecanstreet-access-constraints.md)
first.

**GPU telemetry** — periodogram of real H100/B200 training-node power
traces, testing whether node-scale telemetry reproduces the 0.2–3 Hz band
reported for thousands-of-GPU jobs:

```bash
.venv/bin/python scripts/aidc_psd.py
```

Reads `data/raw/aidc_workload/*.csv`, re-downloadable from the
[rs-7943457 dataset](https://github.com/Ahmed-Elsayed95/High-resolution-AI-Data-Center-Training-Workloads-Dataset)
(York University / IESO, CC BY 4.0).

**Figures** — regenerate the report figure set (module, not path):

```bash
.venv/bin/python -m scripts.plot_subq1_results
```

## Tests

```bash
.venv/bin/pytest                     # full suite; bootstrap-heavy, expect 10+ min
.venv/bin/pytest tests/preprocessing # any subset runs fast
.venv/bin/ruff check .               # lint, line length 100
```

`tests/regression/` pins numbers from production runs; a failure there
after a change is a real behaviour change, not flakiness.

## Layout

```
data/         # raw/interim/processed parquets (gitignored)
docs/         # decision log, research notes, source constraints, plans
              # (see docs/README.md for the map)
notebooks/    # exploratory analysis
outputs/      # generated figures and tables (gitignored)
scripts/      # per-source fetch + analysis drivers, figure pipeline
src/surg/
  acquisition/    # PJM Data Miner, gridstatus.io, ENTSO-E pulls
  preprocessing/  # loaders, per-market features, panel assembly
  analysis/       # quantile regression, EVT/GPD tails, mechanism diagnostics
  diagnostics/    # shared cross-ISO Stage-1 machinery
tests/
```

## Data

Hourly PJM data comes from [PJM Data Miner 2.0](https://dataminer2.pjm.com/list),
5-minute data from [gridstatus.io](https://www.gridstatus.io), and the other
seven North American markets from their public archives. Facility-level
data-centre load profiles come from the
[UK Power Networks open-data portal](https://ukpowernetworks.opendatasoft.com)
(CC BY 4.0); European load and prices from the
[ENTSO-E Transparency Platform](https://transparency.entsoe.eu), with
Ireland's data-centre consumption from CSO table MEC02; residential circuit
data from [Pecan Street Dataport](https://dataport.pecanstreet.org)
(requires an approved account); GPU power traces from the rs-7943457
dataset (CC BY 4.0). No raw data is tracked in git; every panel is
reproducible from the acquisition commands above.

## License

MIT (see `LICENSE`). Vendored third-party material under `docs/reference/`
(PJM manuals, papers, Pecan Street's data dictionary) keeps its own terms.

Per-source constraints and gotchas live in `docs/sources/*-api-constraints.md`
(PJM, gridstatus, UKPN, ENTSO-E), `docs/sources/pecanstreet-access-constraints.md`,
and `docs/sources/availability/*-data-availability-research.md` (the
cross-ISO markets). Findings are indexed in `docs/research-notes/INDEX.md`.
