# UK Power Networks Open Data API — Discovered Constraints

Source: **empirical probing of the live API on 2026-08-11** with the
project account key, plus the Opendatasoft Explore v2.1 surface exposed
at `https://ukpowernetworks.opendatasoft.com/api/explore/v2.1`. Console:
https://ukpowernetworks.opendatasoft.com/api-console/explore/v2.1

This file captures facts the API forces on us, analogous to
`gridstatus-api-constraints.md` and `pjm-api-constraints.md`. Keep
separate from `decisions.md` (what we chose) and from
`docs/research-notes/EU-3-datacenter-disclosure.md` (which surveyed the
portal anonymously and is **corrected in three places** below).

UKPN is a **DNO** (distribution network operator) for London, the East
and the South East. The portal is Opendatasoft-hosted, so the **platform
mechanics** below (ODSQL, pagination caps, export endpoints, rate-limit
headers) carry over to other Opendatasoft energy portals such as
ODRÉ/RTE — see `docs/research-notes/EU-2-grid-data-availability.md`.
**The quota figures do not carry over**; each domain sets its own.

## Transport / auth

- **Base URL:** `https://ukpowernetworks.opendatasoft.com/api/explore/v2.1`
- **Auth — two forms, both verified working:**
  - header `Authorization: Apikey <key>` ← **prefer this**
  - query param `?apikey=<key>` (leaks the key into logs/history; avoid)
- **Unauthenticated access to records is 403** `ForbiddenAccess`, while
  *metadata* (`/catalog/datasets/<id>`) reads fine anonymously. This is
  what made the dataset look empty in the earlier anonymous survey —
  `/exports/csv` returned a header row and zero data rows.
- Key stored in project `.env` as `UK_POWER_API_KEY` (gitignored, same
  convention as `PJM_API_KEY` / `GRIDSTATUS_API_KEY_*`).
- Registration is free. *Per UKPN's own portal text (not independently
  verified):* **accounts inactive for one year are removed** — if this
  thread goes dormant, the key may die with the account.

## Quota — **100,000 calls per DAY, resetting at 00:00 UTC**

Not a lifetime pool. The portal's "your quota will reset in 2 h 08 m
(11 Aug 2026 20:00)" is **midnight UTC rendered in the browser's local
timezone** — 20:00 EDT = 00:00 UTC. In winter (EST) it will read 19:00.

Verified two ways:

1. **Live response headers** (every endpoint returns them):

   ```
   x-ratelimit-limit:     100000
   x-ratelimit-remaining: 99959
   x-ratelimit-reset:     2026-08-12 00:00:00+00:00
   ```

2. **Opendatasoft's own documentation**, verbatim: `X-RateLimit-Limit`
   "indicates the total number of API calls the user can do in a single
   day (**resets at midnight UTC**)"; `X-RateLimit-Remaining` "the
   remaining number of API calls for the user until reset";
   `X-RateLimit-Reset` "the epoch of the next reset time". Authenticated
   users get higher quotas than anonymous ones, per domain configuration.

**Poll the quota** by reading the headers off any cheap request
(`/records?limit=1`); there is no dedicated usage endpoint. Unlike
gridstatus's free `/api_usage`, **the poll itself costs a call** — cheap
at 100 k/day, but not free. Whether `remaining` counts the current call
was not determined (the measurement below gives the same answer either
way); don't build precise delta arithmetic on an assumption about it.

### An export costs exactly **1 call**, regardless of size

Measured: exporting one full site — **58,318 rows, 1.0 MB parquet** —
decremented the counter by 1, the same as a one-row query. The quota
counts *requests*, not rows.

Consequence: **the entire 5.4M-row dataset is one API call.** Even the
fully partitioned fallback (96 sites × 41 months ≈ 3,900 calls) is under
4 % of a single day's quota.

This is the opposite posture from gridstatus, where the binding
constraint is **rows** (500K/month) and requests (250/month) — which is
what forced the six-key rotation and the "no exploratory pulls" rule in
`CLAUDE.md`. **That scarcity discipline does not transfer here.**
Exploratory querying against UKPN is essentially free; budget by calls
per day, and prefer one wide export over many narrow ones.

- No per-second/per-minute rate limit was hit during probing.
- `access-control-expose-headers` advertises a **per-dataset** tier
  (`X-RateLimit-dataset-Remaining` / `-Limit` / `-Reset`), but these were
  **not returned** on any response observed, and the v1 docs do not
  mention them. Assume domain-level only until seen in the wild.

## The pagination ceiling — *the big constraint*

| Parameter | Ceiling |
|---|---|
| `limit` on `/records` | **≤ 100** |
| `offset + limit` on `/records` | **≤ 10,000** |

Consequence: **only the first 10,000 rows of any result set are
reachable through `/records`.** A 5.4M-row dataset cannot be paginated.
Errors are explicit (`InvalidRESTParameterError`), not silent truncation.

**Therefore bulk acquisition must go through `/exports/<format>`, which
has no such cap.** Two workable routes:

1. **Whole-dataset export** — one call, no filter. *(Not yet exercised;
   see "Not verified" below.)*
2. **Partitioned export** — `where=` on site × month yields ~1,488 rows
   per slice, comfortably under any cap, at ~96 sites × 41 months ≈ 3,900
   calls. Well inside the 100K quota. Use this if route 1 disappoints.

## Export endpoint

`GET /catalog/datasets/<id>/exports/<format>`

- Formats offered: `csv`, `json`, `jsonl`, `parquet`, `geojson`,
  `rdfxml`, `jsonld`, `turtle`, `n3`.
- **`where=` filters ARE honoured on exports** (verified: one site × one
  month returned exactly 1,488 rows = 31 d × 48 half-hours).
- **`parquet` is the right choice** — round-trips through
  `pandas.read_parquet` with correct dtypes (`datetime64[ms, UTC]` for
  `local_timestamp`, `float64` for the ratio) and matches the repo's
  parquet-on-disk pipeline convention.
- **CSV gotchas:** delimiter is **`;`** (not `,`), and the file carries a
  **UTF-8 BOM** on the header. `pd.read_csv(..., sep=';')` is required.
- **Row order is not guaranteed.** A July export began at 2023-07-25.
  Sort explicitly; never assume export order.
- **Costs 1 API call regardless of row count** — see Quota above.
- **Actual size on disk: 49 MB** for the full 5,442,348 rows, as four
  year-partitioned parquets (14.5 / 14.7 / 14.8 / 4.9 MB). That is
  **~9 bytes/row** — far better than the 17.4–24.8 B/row measured on
  single-site exports, because year slices give parquet's dictionary
  encoding much more repetition to exploit in the site-name column.
  *(An earlier 95–135 MB estimate in this file was extrapolated from
  single-site probes and was roughly 2–3× too high.)*
- **Throughput is the real constraint, not quota.** The export streams
  at only **~65 KB/s**; a single unfiltered export of the whole dataset
  runs **~30 minutes** and will blow past most tool/client timeouts.
  This is why `scripts/ukpn_fetch.py` partitions by year — four ~4-minute
  slices with resumable checkpoints instead of one long all-or-nothing
  transfer. Budget wall-clock, not calls.

## ODSQL query gotchas

- **Scalar aggregates broadcast over the result page.** `select=count(*)`
  with no `group_by` returns the same row **ten times** (the default page
  size). Always pass `limit=1` for scalar aggregates.
- **`group_by` results also paginate at 10.** Pass `limit=100` or groups
  will be silently truncated — 96 sites only just fits under the 100 cap.
  A larger portal dataset would need a different strategy.
- Date literals use the `date'YYYY-MM-DD'` form:
  `where=local_timestamp >= date'2023-07-01'`.
- `count(distinct <field>)` is supported. `min()`/`max()` reject **text**
  fields with `StatAggregation only supports numeric or date expression`
  — which is how the `utc_timestamp` typing below was discovered.

### Function surface (probed directly — the v2 docs are not published)

The Opendatasoft docs repo carries only v1, and `help.opendatasoft.com`
truncates. The following was established against the live API.

| Function | Works? | Note |
|---|---|---|
| `hour(dt)` / `year(dt)` / `month(dt)` | ✅ | valid in `select` **and** `group_by` |
| `date_format(dt,'yyyy-MM')` | ✅ | best route to monthly buckets |
| `day_of_week(dt)` | ❌ | `unexpected (` — derive client-side |
| `median(x)` | ✅ | |
| `percentile(x, N)` | ⚠️ | **N is 0–100, not 0–1** |
| `stddev(x)` / `variance(x)` | ❌ | `unexpected (` — **not supported** |

Two traps here:

- **`percentile()` silently returns a wrong answer on the wrong scale.**
  `percentile(x, 0.95)` returns **0.0**; `percentile(x, 95)` returns
  0.554. No error either way. Always pass 0–100. This is worse than it
  looks in *this* dataset: **0.0 is a perfectly plausible result** given
  13 % exact zeros, so the bad value is indistinguishable from a real one
  and could be quoted without anyone noticing.
- **There is no server-side standard deviation or variance.** Since
  dispersion is this project's core quantity, **volatility must be
  computed client-side from exported rows** — which reinforces
  export-then-analyse over server-side aggregation.

Alias gotcha: in a `group_by`, the grouped expression is returned under
its **full expression text**, not the alias. `select=hour(local_timestamp)
as k ... group_by=hour(local_timestamp)` yields
`{"hour(local_timestamp)": 0, "k": null, ...}` — read the key, not `k`.

---

# Dataset: `ukpn-data-centre-demand-profiles`

Half-hourly demand profiles for identified data centres in UKPN's
licence areas. **CC BY 4.0.** Publisher: UK Power Networks (company no.
3870728). Last modified 2026-08-01.

## Shape (verified)

| Property | Value |
|---|---|
| Records | **5,442,348** |
| Distinct sites | **96** |
| Span | **2023-01-01 → 2026-05-13** |
| Resolution | half-hourly (48/day) |
| `dc_type` | 78 Co-located / 18 Enterprise |
| `cleansed_voltage_level` | 60 High / 24 Low / 12 Extra-High Voltage Import |

Schema — 6 fields:

| Field | API type | Note |
|---|---|---|
| `cleansed_voltage_level` | text | |
| `anonymised_data_centre_name` | text | `Data Centre #NN`, the site key |
| `dc_type` | text | **inferred** by UKPN, not declared |
| `local_timestamp` | datetime | see DST defect below |
| `utc_timestamp` | **text** | **not queryable as a date** |
| `hh_utilisation_ratio` | double | see range correction below |

Panel is **near-balanced**: 91 of 96 sites span the full window. Five
late entrants (2023-03, 2023-04, 2024-05, 2024-10, 2024-11) and five
early exits (2025-07, 2025-08, 2025-12 ×2, 2026-01). Median 58,174 rows
per site against a theoretical 58,980 → ~98.6 % interval completeness.
The final month is **ragged**: 91 sites reach May 2026 but only 9 reach
2026-05-13 itself. Trim the tail before any "latest period" comparison.

## Corrections to `EU-3-datacenter-disclosure.md`

That note was written **without an account**, from metadata alone. Four
of its claims are wrong — three about this dataset (below) and one about
`ukpn-large-demand-list` (see Companion datasets). Its survey of *which*
datasets exist held up; its claims about *what is in them* did not.

### 1. The ratio is NOT bounded in [0,1]

Observed range is **[0.0, 3.992]**. **51,078 records (0.94 %) exceed
1.0, across 6 sites.** Ratios above 1 mean observed import exceeded
contracted maximum import capacity — plausible physically, but a 4×
overshoot more likely indicates a stale or wrong MIC denominator for
those sites. **Do not clip to 1.0**; treat >1 as a site-level flag.

### 2. `local_timestamp` does not encode British local time

Both fields carry **identical wall-clock values**, and `local_timestamp`
has a fixed `+00:00` offset that never changes.

Evidence — two full-site exports (Data Centre #11 and #14, **116,636
rows**, both spanning 2023-01-01 → May 2026 and therefore **7 UK DST
transitions**): `local_timestamp` differs from parsed `utc_timestamp` in
**0 rows**. Spring-forward days carry a full **48** intervals where a
genuine local clock has 46 (01:00–02:00 local does not exist), and
autumn-back days carry 48 where a local clock has 50.

*Caveat for the next reader:* Data Centre #14 shows 46 intervals on
2026-03-29. That is **not** a DST signature — it is a 2-interval data
gap. Every other spring-forward day at both sites has 48, and the
direct field comparison is what carries the claim.

**Treat both fields as UTC.** Any diurnal-shape or time-of-day analysis
that trusts the `local_` prefix inherits a one-hour summer error — the
same class of defect as the ERCOT `24:00`/` DST` parser bug. Note the
practical consequence: **UK demand shapes are driven by local civil
time**, so shape work needs an explicit UTC→Europe/London conversion
done by us; the dataset will not do it.

### 3. "Sites consistently 0 % were excluded" — they were not

UKPN's stated methodology says such sites were dropped. They remain.

**711,794 records (13.1 %) are exactly 0.0, spread across 69 of 96 sites.**

| Zero share | Sites |
|---|---|
| 100 % (entirely dead) | **4** — Data Centre #24, #65, #75, #91 |
| > 50 % | 10 |
| < 1 % | 66 |

**The zero structure is bimodal, and this matters more than the share.**
Run-length encoding of Data Centre #14's full 58,318-row span (46.7 %
zeros) gives **1,739 distinct zero runs**:

| Run structure | Count |
|---|---|
| Longest run | **7,947 intervals (~166 days)** |
| Next four | 2,276 / 1,717 / 1,621 / 667 |
| **Median run length** | **2 intervals** |
| **Singleton runs (one 30-min zero)** | **754** |
| Runs that are whole-day multiples of 48 | 3 / 1,739 |

So there are **two different defects wearing the same value**, and they
need opposite treatments:

1. **A handful of enormous runs** (weeks to months) — site offline or not
   reporting. Drop the period, or drop the site.
2. **~1,700 short scattered dropouts, median 2 intervals, 754 of them a
   single half-hour** — these sit *inside* otherwise-live operation and
   are almost certainly metering dropouts.

**Category 2 is the first-order trap for this project specifically.** A
lone 0.0 dropped into a live series creates a fake full-scale ramp down
and back up within one hour. Any volatility, ramp-rate, or Δ-based
statistic — the exact quantities this project cares about — will read
those artefacts as real demand swings. **Interpolating them and
computing volatility on the raw series are both wrong; they must be
masked and the gap excluded from the difference.** Same discipline as
the existing 5-min gap-mask work (`2aab67b`), where a 5 h 50 m hole read
as a −4,933 MW excursion.

Zero contamination is also **highly site-specific** — 66 of 96 sites are
under 1 % zeros, and Data Centre #11 has *none* across its full span.
Screen per site; do not apply one global rule.

The naive `avg(hh_utilisation_ratio)` ≈ 0.216 is biased downward by the
four entirely-dead sites and ten mostly-dead ones, and should not be
quoted.

## Interpretation limits (unchanged from EU-3, still binding)

- **No absolute MW.** The value is dimensionless: observed apparent
  power ÷ contracted maximum import capacity, both in kVA.
- **No location.** Anonymised; only voltage level and inferred type
  survive. Cannot be joined to any nodal or GSP geography.
- **No price.** This dataset cannot speak to price formation at all.
- **Levels are not comparable across sites — only shapes.** The
  denominator is *contracted* capacity, so a site at 0.4 is not
  physically "less loaded" than one at 0.7; it may simply have contracted
  more headroom. The observed voltage gradient (EHV 0.121 < LV 0.178 <
  HV 0.245) is **not** evidence that big sites run cooler; larger
  connections plausibly contract proportionally more headroom. Do not
  report that gradient as physical without an explicit contracting
  assumption.
- **Distribution-connected only.** Transmission-connected hyperscale
  sites sit outside a DNO's metering, so the largest facilities are
  likely absent by construction.

## Companion datasets on the same portal

Both fit entirely under the 10,000-row cap, so `/records` works normally
— no export needed. **Schemas below are verified, not inherited.**

### `ukpn-data-centres-by-local-authority` — 45 records, mod. 2026-04-24

Fields: `local_authority_district_name` (text),
`county_and_unitary_authority_name` (text),
`operational_data_centre_capacity_mva` (double),
`pipeline_data_centre_capacity_mva` (double).

Totals across all 45 districts: **1,184 MVA operational vs 7,386 MVA
pipeline — a 6.2× pipeline-to-operational ratio.** This is the only
sub-national geographic breakdown of data-centre capacity found in
Europe, and it is *capacity, not consumption*.

⚠️ **Nulls are present** in the capacity columns (e.g. Basildon has
`operational = None`, `pipeline = 120.0`). A null is not a zero — do not
`fillna(0)` without deciding what an absent operational figure means.

### `ukpn-large-demand-list` — 496 records, mod. 2025-11-04

Fields: `licence_area` (text), `grid_supply_point` (text),
`anonymised_name` (text), `demand_technology_type` (text),
`required_import_capacity_kva` (double), `application_date` (**date** —
genuinely typed, unlike the profiles dataset).

**Correction to EU-3, #4.** That note says this list "can be filtered to
data-centre demand types." **It cannot.** `demand_technology_type` takes
exactly **two** values, neither data-centre-specific:

| `demand_technology_type` | n | Σ capacity |
|---|---|---|
| Large Demand | 252 | 7,250 MVA |
| Distributed Energy Resource | 244 | 9,267 MVA |

So this dataset gives GSP-level location and connection-queue timing for
*large demand in general* — data centres are **not separable** within it.
Any data-centre reading of it would be an assumption, not a filter.

### `ukpn-data-centre-utilisation`

Archived, 0 records, superseded by the demand-profiles dataset. Noted so
it isn't chased.

## Acquisition status — PULLED AND VERIFIED 2026-08-11

Full corpus is on disk at `data/raw/ukpn/` (49 MB, 6 files) via
`.venv/bin/python scripts/ukpn_fetch.py`. Verified against the API's own
reported values:

| Check | Result |
|---|---|
| Total rows | **5,442,348** — exact match |
| Distinct sites | **96** — exact match |
| Span | 2023-01-01 00:00 → 2026-05-13 22:30 |
| Duplicate `(site, timestamp)` | **0** — year partitioning is clean, no boundary overlap |
| Nulls in `hh_utilisation_ratio` | 0 |
| Ratio range | [0.000, **3.992**] — matches |
| Exact zeros | 711,794 (13.1 %) across 69 sites — matches |
| Ratio > 1 | 51,078 across 6 sites — matches |
| 100 % dead sites | #24, #65, #75, #91 — confirmed by name |
| `local_timestamp` vs `utc_timestamp` | **0 of 5,442,348 rows differ** |

That last row upgrades the DST finding from a two-site sample to a
**whole-corpus universal**: the two timestamp columns are value-identical
everywhere. `local_timestamp` carries no local time at all.

## Not verified

- **The per-dataset rate-limit tier** (`X-RateLimit-dataset-*`) is
  advertised in CORS headers but was never observed on any response.
  Assume domain-level only until seen in the wild.
- **Whether zero-runs correspond to meter changes, site closure, or
  reporting gaps** — undetermined, and not answerable from this dataset
  alone.
- **Other GB DNOs** (SSEN, NGED, SP Energy Networks, ENWL) have not been
  re-checked. EU-3 found no DC-specific dataset at Northern Powergrid and
  a 403 at SSEN. Still open — and material, since **SSEN covers Slough
  and West London**, the cluster this dataset structurally excludes.
- Whether zero-runs correlate with meter changes, site closure, or
  reporting gaps — undetermined, and not answerable from this dataset
  alone.
- Other GB DNOs (SSEN, NGED, SP Energy Networks, ENWL) were **not**
  re-checked this session. The EU-3 note found no DC-specific dataset at
  Northern Powergrid and a 403 at SSEN; it flags a manual re-check of the
  remaining four as an open item. Still open.
