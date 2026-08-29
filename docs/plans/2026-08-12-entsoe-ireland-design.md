# ENTSO-E: Irish data-centre growth and the shape of national load — design

**Date:** 2026-08-12
**Status:** design approved in session; implementation plan not yet written
**Supersedes nothing.** Extends `docs/research-notes/EU-0-synthesis.md` §2(b)
and §4, and closes the open check in `EU-2-grid-data-availability.md` §9.0.

---

## 0. What this is

The ENTSO-E API went live for this project on 2026-08-12
(`docs/sources/entsoe-api-constraints.md`). This document specifies what to do with it.

The headline question:

> As data centres grew to 23.2% of Irish metered electricity by 2025, did the
> **shape** of Irish national load change?

The 2015 starting share is **not yet verified** — only the 2025 figure (23.2%,
7,662 GWh) is carried from `EU-0` §3. The starting share is computed from MEC02
in §3.4, not assumed here.

Ireland is worth this attention for one reason that no market in this project
has previously offered: **its data-centre exposure is measured, not proxied.**
The CSO publishes quarterly metered data-centre consumption (table MEC02,
2015Q1–2025Q4, 44 quarters, free, no registration). Every US result in this
project rested on geographic proxies — Loudoun County, the DOM zone, Ashburn
pnodes. This is a dose variable.

It is paired with the Netherlands as a control: matched total VRE share (42.8%
vs 46.1%), flat data-centre share (4.6% vs Ireland's 23.2%), and a 4.5× split
on solar share (4.7% vs 21.1%) that simultaneously runs the H_solar test EU-5
identified as the one open question the North American panel could not settle.

**What this design cannot do, stated up front.** One treated unit, one control,
44 quarters. CSO's series is heuristically constructed — name matching,
business parks, meters above 1 GWh — and is national and quarterly. This
establishes the *existence* of an exposure trend, not identification. A result
here is a descriptive fact, consistent with or against the working lean logged
in `decisions.md` § 2026-08-11, and must be written as such.

---

## 1. Probe findings this design rests on

Measured 2026-08-12, ~60 requests, via three scratchpad probe scripts. These
are measurements, not vendor claims, and four of them contradict the desk
research in `EU-0`/`EU-2`.

### 1.1 EU-2 §9.0 resolves POSITIVE — Italy is a real 7-zone panel

All seven Italian bidding zones return **both** 6.1.A Actual Total Load and
12.1.D Day-Ahead Prices for 2024-01-08, and IT-North load runs 2015 → 2026.

The control discriminated correctly: `IT (national CTA)` = `10YIT-GRTN-----B`
returns load but **reason 999 on price**. So a positive on the BZN codes is not
an EIC-role artifact — the concern EU-2 §9.0 raised is answered.

### 1.2 Resolution is native and heterogeneous — the "hourly panel" premise was wrong

| Zone | Load resolution | Window observed |
|---|---|---|
| NL | **PT15M** | 2015 → 2026 |
| IE (CTA) | **PT30M** | 2015 → 2026 |
| IT-North | PT60M → **PT15M** | 2015 → 2026 |
| DE-LU | PT15M | 2024 |

IT-North was PT60M on the 2015, 2018, 2020 and 2021 dates probed and PT15M on
2026-03-10. **The switch date was not bisected** — it lies between 2021-03 and
2026-03, and the 2025-10-01 MTU change is the obvious candidate but is not
established. The panel builder must therefore read resolution per document
rather than assume one per zone.

EU-2 §8 item 5 recommended "2015 → 2025-09-30 for a clean hourly panel", on the
assumption that the 15-minute MTU arrived on 2025-10-01. That is a **market**
time unit change. ENTSO-E has served *load* at native national resolution
throughout — NL at 15 minutes since 2015. The finest multi-year load data in
this project outside the 5-minute PJM panel.

Consequence: `|Δload|` per minute is sensitive to sampling interval, so any
cross-zone comparison must run on a common grid. Hence the two-panel design
in §4.

### 1.3 The Irish load series moves EIC at the R3 migration — and the move fixes a known defect

`IE-SEM BZN` (`10Y1001A1001A59C`) serves load through 2025-10-15 and returns
reason 999 on 2025-11-01 and every date tested through 2026-08-10. 6.1.A
migrated to R3 on 2025-11-10.

`IE CTA` (`10YIE-1001A00010`) serves **2015 → 2026-08 unbroken at PT30M.**

They are **not the same series.** On 2024-01-08, across all 48 shared
positions, `mean(SEM − CTA) = 1015.1 MW` — Northern Ireland.

`EU-0` §3 listed "footprint mismatch" as one of three disqualifying limits on
Ireland: SEM is all-island, the CSO covariate is Republic-only. **That was an
artifact of choosing the SEM code.** The CTA code gives Republic-only load,
matching the covariate. One of the three objections to Ireland is void.

Price has the opposite pattern — `IE CTA` returns reason 999 on 12.1.D, so
**price must come from SEM BZN.** Irish load is Republic-only; Irish price is
all-island. This asymmetry is load-bearing and must be carried in the schema.

### 1.4 A03 sparsity is live and material

`curveType` is A03 on every document observed. A03 emits a position only where
the value *changes*. Observed shortfalls against dense expectation:

| Document | Emitted | Dense |
|---|---|---|
| NL load 2015-01-08 | 95 | 96 |
| IE load 2025-10-15 (23h window) | 44 | 46 |
| IE price 2018-03-10 | 32 | 46 |
| IE price 2018-11-10 | 21 | 24 |
| NL price 2015-03-10 | 23 | 24 |

Parsed naively — one row per `Point` — a flat stretch vanishes and every
gradient computed downstream reads **spikier than reality**. Since the project's
volatility measure is `mean |Δload| per minute`, this would corrupt the single
number the work exists to produce. §3 makes expansion an explicit, tested
component.

### 1.5 Cost is not a constraint

One full year of NL 15-minute load returned **35,134 points in a single
request** (2024: 366 days × 96 = 35,136, less 2 for DST). Against a 400 req/min
limit, the entire corpus is a rounding error.

### 1.6 Incidental findings, recorded but not used

- 6.1.B day-ahead load **forecast** is absent for IE-SEM (reason 999 in both
  2024 and 2026) but present for NL at PT15M. Not needed by this design.
- 16.1.B&C aggregated generation per type (A75) **is** available for IE-SEM in
  both 2024 and 2026 — 16–17 production types at PT30M. A route to Irish wind
  share if the analysis later needs it.
- IE price resolution changed PT30M → PT60M around the I-SEM launch
  (2018-10-01): PT30M on 2018-03-10, PT60M on 2018-11-10.

---

## 2. Corpus

**20 zones × 2 data items × 2015–2026.** One parquet per zone-year-item.

| Group | Zone | EIC | Load | Price |
|---|---|---|---|---|
| **Ireland** | IE (CTA) | `10YIE-1001A00010` | ✅ probed | ✗ reason 999 |
| **Ireland** | IE-SEM (BZN) | `10Y1001A1001A59C` | to 2025-10 only | ✅ probed |
| **Control** | NL | `10YNL----------L` | ✅ probed | ✅ probed |
| Italy | IT-North | `10Y1001A1001A73I` | ✅ | ✅ |
| Italy | IT-Centre-North | `10Y1001A1001A70O` | ✅ | ✅ |
| Italy | IT-Centre-South | `10Y1001A1001A71M` | ✅ | ✅ |
| Italy | IT-South | `10Y1001A1001A788` | ✅ | ✅ |
| Italy | IT-Sicily | `10Y1001A1001A75E` | ✅ | ✅ |
| Italy | IT-Sardinia | `10Y1001A1001A74G` | ✅ | ✅ |
| Italy | IT-Calabria | `10Y1001C--00096J` | ✅ | ✅ |
| VRE | DE-LU | `10Y1001A1001A82H` | ✅ | ✅ |
| VRE | ES | `10YES-REE------0` | ⚠ unverified | ⚠ |
| VRE | FR | `10YFR-RTE------C` | ⚠ unverified | ⚠ |
| VRE | FI | `10YFI-1--------U` | ⚠ unverified | ⚠ |
| VRE | DK1 | `10YDK-1--------W` | ⚠ unverified | ⚠ |
| VRE | DK2 | `10YDK-2--------M` | ⚠ unverified | ⚠ |
| VRE | SE1 | `10Y1001A1001A44P` | ⚠ unverified | ⚠ |
| VRE | SE2 | `10Y1001A1001A45N` | ⚠ unverified | ⚠ |
| VRE | SE3 | `10Y1001A1001A46L` | ⚠ unverified | ⚠ |
| VRE | SE4 | `10Y1001A1001A47J` | ⚠ unverified | ⚠ |

The ⚠ rows carry EIC codes taken from `docs/sources/entsoe-api-constraints.md` and not
probed. **This is not a risk to manage — it is a result to record.** The
fetcher must treat reason 999 as data, not as failure, and write it to the
manifest. A wrong EIC and a genuinely unpublished series look identical from
the client side, so the note must say "not returned for this EIC" rather than
"not published".

Data items: **6.1.A Actual Total Load** (`documentType=A65`, `processType=A16`,
`outBiddingZone_Domain`) and **12.1.D Day-Ahead Prices** (`documentType=A44`,
`in_Domain` = `out_Domain`).

Plus **CSO MEC02** — quarterly Irish data-centre metered consumption via the
PxStat API, one request, no registration.

Request budget: 20 × 12 × 2 = **480 ENTSO-E requests as an upper bound** —
the true count is lower, because IE CTA carries no price and IE-SEM load stops
in 2025. The manifest reports the actual total; do not treat 480 as a target.
Paced ~5/s per the
vendor's own recommended throttle (6–7 req/s). The 400/min limit is not
approached and **must not be probed** — see the constraints doc's deliberate
non-verification decision.

---

## 3. Components

### 3.0 Storage: raw is parsed-but-unexpanded

`data/raw/entsoe/<item>/<zone>/<year>.parquet`, long format:

```
zone, item, doc_start, doc_end, resolution, curve_type, position, quantity
```

Faithful to the response, and it lets §3.2 be re-run and re-tested without
re-pulling. Expansion is a preprocessing step, never a parse-time side effect.

### 3.1 `scripts/entsoe_fetch.py`

Follows `scripts/ukpn_fetch.py`: raw `httpx`, no wrapper, idempotent skip of
targets already on disk, `.part` rename-on-success.

`entsoe-py` is **deliberately not used.** It broke on the 15-minute switch
(EU-0 §5), would need pinning and smoke-testing, and — decisively — it would
hide the A03 expansion, the one step that must be visible and tested.

Behaviour:
- chunk by calendar year (1-year cap on both 6.1.A and 12.1.D)
- **HTTP 200 + reason 999 is "no data", not success** — parse every body
- HTTP 400 carrying an over-cap count → halve the window and retry
- pace ~5 req/s; on HTTP 429, stop rather than retry-storm (the token is
  irreplaceable on a 3-working-day lead time)
- write `data/raw/entsoe/manifest.csv`: zone, item, year, outcome, n_rows,
  resolution, curve_type, `n_emitted/N` sparsity ratio, verbatim reason text

The manifest is a deliverable in its own right: an empirical coverage map of
European load and price data, which is exactly what EU-2 §9 could only infer.

### 3.2 `src/surg/preprocessing/entsoe_expand.py` — the A03 expander

Pure function, no I/O, independently tested. **This component decides whether
any downstream number is real.**

Contract: given `timeInterval` [start, end), `resolution` ∈ {PT15M, PT30M,
PT60M}, `curve_type`, and sparse `(position, quantity)` pairs, return a dense
array of length `N = (end − start) / resolution`.

Rule (A03 = variable-sized blocks): place emitted values at their positions,
forward-fill, last emitted value holds to the end.

Raises rather than guesses when:
- `N` is not an integer
- `max(position) > N`
- position 1 is absent — no opening value to fill from

Also:
- returns `n_emitted / N` so sparsity is measured, not invisible
- **timezone-free** — expansion is in UTC; DST is handled at localization
- A01 documents pass through with an assertion that `n_emitted == N`

### 3.3 `src/surg/preprocessing/entsoe_panel.py`

Builds two panels from the same expanded source:

- **native** — per-zone at its own resolution (NL 15-min, IE 30-min, IT 60/15)
- **hourly-derived** — mean within the hour, for cross-zone and cross-market
  comparison

Both carry naive local prevailing hour-*beginning* timestamps and a
`dst_transition_hour` bool, matching the contract `surg.diagnostics.stage1`
requires. Timezones: IE `Europe/Dublin`, NL `Europe/Amsterdam`, IT
`Europe/Rome`, DE `Europe/Berlin`, ES `Europe/Madrid`, FR `Europe/Paris`, FI
`Europe/Helsinki`, DK `Europe/Copenhagen`, SE `Europe/Stockholm`.

Note the response-side trap from the constraints doc: day boundaries follow the
**area's configured** timezone, which may differ from its geographic one, and
12.1.D is named as an exception. Localization is therefore driven by the
declared `timeInterval`, not by assuming a country's civil timezone.

### 3.4 `scripts/cso_fetch.py`

CSO PxStat table MEC02 → `data/raw/cso/mec02.parquet`. Quarterly Irish
data-centre metered consumption plus total metered consumption, so DC *share*
is computed rather than assumed.

### 3.5 `scripts/entsoe_ireland.py`

The analysis of §4. Writes figures and JSON to `outputs/entsoe/`.

### 3.6 `scripts/entsoe_italy_stage1.py`

Thin driver into `surg.diagnostics.stage1`, same shape as the seven existing
`scripts/<iso>_diagnostic.py` drivers. Marked a robustness check, not a
finding — per EU-0 §1, European zones are panels 12–13 of a result in hand.

---

## 4. Analysis

### 4.1 Approach A — shape statistics against a measured dose

Per zone, per year **and** per quarter, on both panels:

| Statistic | Definition | Provenance |
|---|---|---|
| `vol_norm` | mean \|Δload/min\| ÷ mean load | the existing Stage-1 measure — comparable to all 11 panels |
| `pt_ratio` | median over days of (daily max ÷ daily min) | `J-ukpn-flatness.md`: DC sites 1.05, ISONE 1.467 |
| `load_factor` | mean load ÷ peak load | EPRI's "DCs run at ~90% of own peak" |
| `night_floor` | median over days of (daily min ÷ daily mean) | sharpest predicted signature of an always-on block |

**Which comparisons are licensed — this constrains what the note may print.**

- `pt_ratio`: IE/NL **hourly** vs the ISONE **hourly** figure (1.467) is
  arithmetically comparable. The UKPN 1.05 is **not** — it is half-hourly,
  per-site, and a utilisation *ratio* rather than MW. Quote it only as a
  facility-level contrast in prose, **never in the same column** as a zonal
  number.
- `vol_norm`: an hourly panel *derived by averaging* 15- or 30-minute data is
  low-pass filtered, so it is **smoother than a natively-metered hourly
  series** at the same nominal resolution. Consequence: `vol_norm` **levels**
  are not strictly comparable between IE/NL and the 11 existing panels, even
  after resampling. **Within-zone trends over time remain comparable**, and the
  trend is what this design tests. State this limit in the note; it is the one
  place a reader will over-read.
- Native-resolution gradients call `add_load_gradient_columns` directly with
  the zone's own `freq_minutes` (15/30). They must **not** go through
  `stage1.add_zone_gradients`, which hard-codes `freq_minutes=60`.

Then:
1. IE trend on each statistic, 2015 → 2025
2. NL trend, same window
3. the difference (IE − NL), which absorbs COVID, the 2022 energy crisis, and
   Europe-wide VRE/EV/heat-pump growth
4. correlation of each IE statistic with CSO DC share across 44 quarters
5. **placebo:** the same correlation for NL against its own flat DC share

### 4.2 Approach B — diurnal decomposition (the mechanism plot)

Per year, divide each day's profile by that day's own mean, then average across
days within the year. Plot 2015 / 2020 / 2025, Ireland beside the Netherlands.

Prediction if a flat always-on block is displacing shape: **Ireland's overnight
trough rises relative to its own peak, and the Netherlands' does not move the
same way.** This is where A's signal must appear if A's signal is real.

### 4.3 Confounders — named in the note, not buried

- **COVID 2020.**
- **The 2022 energy crisis.** European demand destruction was large and would
  flatten load shape on its own. This is the most serious threat to a naive
  reading and the strongest argument for the NL difference.
- **EV and heat-pump growth**, which pushes `night_floor` the same direction a
  data centre would.
- **CSO's identification method drifting** across 11 years; CSO itself warns
  new small sites fall below its thresholds.
- **n = 44 quarters, one treated unit.** No causal claim.

### 4.4 One asymmetry that favours Ireland as a measurement site

6.1.A is *metered* load — gross of behind-the-meter generation. Ireland
mandates co-location but **forbids the netting** (generation ≥10 MVA separately
connected and metered, EU-5). So Irish metered load is not eroded by BTM the
way other jurisdictions' can be, and the series should stay honest as DC share
grows. This is the inverse of the US FERC problem and worth stating in the note.

---

## 5. Testing

`tests/preprocessing/test_entsoe_expand.py` carries the weight:

- flat day — one emitted point becomes N identical values (the case that
  silently produces garbage gradients)
- sparse day — gaps forward-fill to the correct positions
- A01 passthrough — asserts `n_emitted == N`
- `N` non-integer → raises
- `max(position) > N` → raises
- missing position 1 → raises
- a DST-span day — fixed UTC span, expansion unaffected

**Panel assertions split by panel, and this is not optional.**
`stage1.assert_panel_quality` computes `expected = (max − min)/3600 + 1` and
tolerates ±48 rows. A 15-minute NL panel has 4× that row count and would fail
by roughly 370,000 rows. So:

- **hourly-derived panel** — reuse `assert_panel_quality` unchanged (IE and NL
  are prevailing-time → `dst_pairs_per_year=1`)
- **native panel** — needs a resolution-aware variant, or no gap assertion at
  all. Do not call the hourly one and fight it.

No regression pins — new thread.

---

## 6. Deliverable

- `docs/research-notes/K-ireland-dc-shape.md`, in the mould of
  `J-ukpn-flatness.md`
- the "European energy markets" section of
  `docs/plans/advisor/2026-08-19-advisor-meeting-agenda.md`, currently empty
- a `docs/decisions.md` entry (append-only)

Six to seven files, so per `CLAUDE.md` this goes through writing-plans →
subagent-driven-development rather than ad-hoc implementation.

---

## 7. What would make this interesting either way

- **If Irish load shape flattened as DC share quadrupled and NL's did not** —
  the first direct evidence in this project that data-centre growth changes
  aggregate load shape, from the only market with a measured dose. It would
  also sit against the working lean, which expects mitigation to have absorbed
  the stress.
- **If neither moved** — a fourth independent null, now from the most
  DC-saturated grid on earth, with measured exposure rather than a proxy. Taken
  with the UKPN flatness result and the eight-market Stage-1 capstone, that is
  a substantive convergence rather than an absence.
- **H_solar, either way** — NL rising while IE does not supports the metering
  artifact; both or neither undercuts it. EU-5 established this is the one open
  question the North American panel could not settle.
