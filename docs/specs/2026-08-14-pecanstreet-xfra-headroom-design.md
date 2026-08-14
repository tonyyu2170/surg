# Pecan Street × XFRA: panel headroom and fast residential volatility — design

**Date:** 2026-08-14
**Status:** approved in discussion; awaiting spec review
**Data:** `data/raw/pecanstreet/` (22 GiB, committed `6855b83`) — free-tier static
bundles: Austin 25 homes (15-min/1-min/1-sec, calendar 2018), New York 25 homes
(15-min/1-min/1-sec, May–Oct 2019), California 23 homes (15-min/1-min only,
2014–2018). No analysis exists yet; this is the first cut.

## Motivation

Prioritization doc (`docs/plans/2026-08-11-post-meeting-prioritization.md` §3)
assigns Pecan Street one job: the advisor's XFRA question. XFRA/SPAN propose
hosting AI compute nodes in homes on the theory that residential panels have
idle "electrical headroom." The obvious tension, already written down there: a
house's spare capacity is largest exactly when the grid is least stressed and
smallest at summer peak. Separately, the NERC LLTF record shows AI training
loads oscillating at 0.1–30 Hz with swings up to 90% of capacity — and an XFRA
node puts that behavior *behind a residential panel*. Pecan Street is
residential circuit-level data; it cannot see data centers, but it is the right
instrument for both host-side questions, and its 1-sec view is the fastest data
the project holds anywhere.

## Research questions (note reads in this order)

- **RQ1 — siting (brief desk research).** Where is the XFRA/PulteGroup
  100-home pilot actually siting — which metros, which utility territory? Is
  Austin the right climate analog? Also: any published node wattage/spec (feeds
  RQ3's node-size assumption).
- **RQ2 — headroom.** Do the bundle homes have genuinely idle panel capacity,
  and does it shrink or vanish exactly during summer peak? Headline number: the
  largest continuous node draw X such that home load + X stays within the
  service rating — year-round vs. in the summer-peak window.
- **RQ3 — fast volatility.** How large is residential fluctuation at
  1-second-to-1-minute timescales, per home and in 25-home aggregate, relative
  to a DC-style oscillating node?

The note also gets a short closure subsection: **why subtracting residential
load from total load cannot isolate data-center load** (agenda item 7).
Reasons, in four sentences: sample-not-census scaling error dwarfs the signal;
the volunteer sample is solar/EV-biased; the remainder is all non-residential
load, not DCs; 2018–19 vintage predates the DC boom. Closes the item citably;
the shape-based variant is strictly dominated by the ENTSO-E/CSO measured-dose
work already shipped.

## Approach

Lean script pair + research note (UKPN-flatness pattern). No preprocessing
module, no schema-validation ceremony — this is a descriptive/distributional
analysis, not a market joining the cross-ISO pipeline. Each script has a
`--sample` mode (one home, one day/month) that gets run and eyeballed before
any full run.

## RQ2 — headroom design

- **Input:** 1-minute bundles, all three cities (primary — a breaker responds
  to sustained draw and 15-min averaging shaves real peaks); 15-min files as a
  cross-check.
- **Load reconstruction:** whole-home consumption `use = grid + solar +
  solar2` — gross draw through the panel, which is what the service rating
  constrains (not net grid import). Identity sanity-checked on solar homes;
  the ≤8 battery homes flagged and handled explicitly.
- **Denominator:** no measured panel size exists anywhere in the data (audits,
  surveys, and the 130-col metadata all checked 2026-08-14). Headroom runs as
  scenario bands — 100 A / 150 A / 200 A service (24 / 36 / 48 kW at 240 V),
  each with and without the NEC 80% continuous-load derating. 200 A is the
  headline scenario (XFRA's own framing); construction year + square footage
  from metadata are reported per home as descriptive context for which band a
  home plausibly sits in — they do not reweight any statistic.
- **Per home:** load-duration curve; annual max, p99, p99.9; headroom
  `S − load_t` per scenario.
- **Coincidence test (headline):** seasonal curve of daily minimum headroom;
  headroom in the system-peak window (Jun–Sep, 15:00–19:00 local, inclusive of
  the 15:00 hour) vs. rest of year; fraction of homes that could host a continuous 1 / 3 / 5 / 10 kW node
  year-round vs. only off-peak, per scenario.
- **Cross-city:** Austin full-2018 (cooling-dominated analog), NY May–Oct 2019
  (includes summer, milder), CA 2014–2018 (five years — also a year-to-year
  stability check; headroom half only, no 1-sec).

## RQ3 — fast-volatility design

- **Input:** eight 1-sec files (Austin ~12.9 GB gz + NY ~6.3 GB gz), processed
  as streams, never loaded whole. Same reconstruction, after verifying
  grid/solar columns exist at 1-sec.
- **Per home:** distributions of load changes over 1 s / 10 s / 60 s lags;
  catalog of largest natural fast events (AC compressor starts, EV charger
  steps — what a panel already survives daily); Welch spectral density on
  continuous segments, band-limited 0–0.5 Hz. Stated honestly: 1-sec sampling
  (Nyquist 0.5 Hz) only grazes the bottom of the 0.1–30 Hz DC band; the 2 kHz
  waveform release would cover it and its licensing question is still open.
- **Aggregate:** sum homes present per second; re-run delta metrics; the
  cancellation test — does σ of aggregate changes grow like √N (idiosyncratic,
  cancels; the UKPN result for DC sites) or like N (synchronized)? Relevant to
  a subdivision of XFRA nodes on one feeder.
- **Node comparison:** synthetic oscillating node — square wave at a frequency
  in the 0.1–0.5 Hz overlap band, amplitude 90% of node draw, node draw ∈
  {1, 5, 10 kW} unless RQ1 finds a published spec. Headline metric: where a
  node's second-to-second swing sits in the distribution of each home's
  natural swings. Magnitude comparison only — no detection theory.

## Data handling — verified and reported, not assumed

- Timestamps carry embedded UTC offsets; parse them as such. **CA files show
  `-06` (Central, not Pacific)** — resolve before any local-time peak-window
  claim; document the resolution either way.
- Per-home coverage computed first; a home joins a window's statistics only
  with ≥90% coverage in that window. Gaps split spectral segments; no
  interpolation.
- Join the 73 bundle homes to metadata intervention flags (CCET, SHINES,
  Verizon, …); report overlap; re-run headline stats without contaminated
  homes as a robustness line.
- Sign conventions checked on solar homes (reconstructed use should
  essentially never be negative); violations counted and reported.

## Implementation shape

- `scripts/pecanstreet_lib.py` — shared loading/reconstruction/coverage logic
  (same-directory import works for path-run scripts).
- `scripts/pecanstreet_headroom.py`, `scripts/pecanstreet_1sec.py` — argparse:
  `--city`, `--sample`, `--outdir` (default `outputs/pecanstreet/`). Outputs
  JSON + figures.
- Tests: a handful of pytest cases pinning reconstruction sign handling, gap
  handling, and the coverage rule, under `tests/`.
- Runtime: 1-sec streaming pass is the only heavy step (tens of minutes); all
  local — corpus already on disk, no JupyterHub needed.
- **Execution order:** RQ1 siting research first (can adjust the node-size
  assumption) → RQ2 headroom → RQ3 1-sec → research note
  `docs/research-notes/M-pecanstreet-xfra-headroom.md` + INDEX line + catalog
  update.

## Out of scope

- Puerto Rico power-quality set (THD/angle/apparent power) — future work.
- 2 kHz waveform tier — blocked on licensing reply.
- Any facility-level data-center inference from this dataset (see closure
  subsection).
