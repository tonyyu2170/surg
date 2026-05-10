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
