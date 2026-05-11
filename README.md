# SURG: Data Center Load Volatility and Congestion Pricing in PJM DOM

Research on the relationship between high-frequency data-center load volatility
in Northern Virginia and Locational Marginal Pricing (LMP) in the PJM Dominion
zone. The goal is to identify the load-variance threshold (MW/min) at which the
DOM-zone pricing response transitions from a linear to a heavy-tailed regime,
then project when forecasted growth pushes the grid permanently past that point.

Full proposal: [`docs/Yu_Tony_SURG_Grant_Proposal.md`](docs/Yu_Tony_SURG_Grant_Proposal.md).

## Setup

Requires Python 3.11+.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Data acquisition

All raw PJM Data Miner 2 pulls go through `surg-pull`, the CLI registered by
`src/surg/acquisition/pull.py`. Output goes to
`data/raw/<feed>/<year>/<group_label>__<start>_to_<end>.parquet` and re-runs
skip chunks that already exist on disk (`--force` to overwrite).

The 11 target pnodes (LOUDOUN, PLEASANT VIEW, GOOSECRE, BRAMBLET, MOSBY,
SKFFSCRK, two ASHBURN 35 KV LOAD buses, OX, BRISTERS, DOM zonal) are baked
in as a module constant; see `docs/decisions.md` for the rationale.

### Examples

```bash
# Hourly nodal LMP, the 11-pnode target set, one calendar year
surg-pull --feed rt_hrl_lmps --start 2024-01-01 --end 2024-12-31

# 5-minute nodal LMP within PJM's 186-day Standard window
surg-pull --feed rt_fivemin_hrl_lmps --start 2025-11-15 --end 2026-05-10

# Day-ahead hourly LMP
surg-pull --feed da_hrl_lmps --start 2024-01-01 --end 2024-12-31

# DOM-zone hourly load (zonal feed — --zone replaces the pnode set)
surg-pull --feed hrl_load_metered --zone DOM --start 2024-01-01 --end 2024-12-31 --group-label dom_load
```

Requires `PJM_API_KEY` in `.env` (see `.env.example`) or the environment.
The CLI throttles requests to ~6/min to respect PJM's free-tier rate limit;
expect roughly 11s of wall time per API call.

## Layout

```
data/         # PJM data
docs/         # proposal and supporting writing
notebooks/    # exploratory analysis
outputs/      # generated figures and tables (gitignored)
src/surg/
  acquisition/    # PJM Data Miner pulls
  preprocessing/  # filtering, signal isolation
  analysis/       # Granger causality, EVT/GPD, regime detection
tests/
```

## Data

Raw data is sourced from [PJM Data Miner 2.0](https://dataminer2.pjm.com/list)
and is not tracked in git. All pulls should be reproducible by running scripts
in `src/surg/acquisition/`.
