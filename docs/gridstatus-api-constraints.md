# gridstatus.io Hosted API — Discovered Constraints

Source: the `gridstatusio` client source (`gs_client.py`, raw GitHub —
the docs site at `docs.gridstatus.io` / `opensource.gridstatus.io` is
Cloudflare-403 to programmatic fetch) plus **empirical probing of the
live API on 2026-05-15** with the project account. This file captures
facts the hosted API forces on us, analogous to `pjm-api-constraints.md`
for PJM Data Miner 2. Keep separate from `decisions.md` (what we chose)
and from `pjm-api-constraints.md` (a different API).

This is the **hosted warehouse** (`gridstatusio` client / API key), NOT
the open-source `gridstatus` library. The OSS library scrapes PJM Data
Miner 2 directly and inherits PJM's ceilings (186-day 5-min / 731-day
hourly); only the hosted warehouse retains deep history.

## Transport / auth

- **Base URL:** `https://api.gridstatus.io/v1` (no version negotiation).
- **Auth:** header `x-api-key: <key>`. The official client also sends
  `x-client: gridstatusio-python` and `x-client-version`.
- **API key ≠ account password.** Key is provisioned in the dashboard;
  stored in project `.env` as `GRIDSTATUS_API_KEY` (gitignored, same
  convention as `PJM_API_KEY`).
- **`GET /datasets/` (trailing slash) 307-redirects to
  `http://api.gridstatus.io/v1/datasets` — a cleartext downgrade.**
  Always call `/datasets` (no trailing slash). Run clients with
  `follow_redirects=False` so a redirect can never replay the
  `x-api-key` header over plaintext HTTP.

## Quota / tier — *the big constraint* (empirical, `GET /api_usage`)

Project account is **Free** tier. Limits (per usage period = calendar
month, e.g. `2026-05-01T00:00:00Z → 2026-06-01T00:00:00Z`):

| Limit | Value |
|---|---|
| `api_rows_returned_limit` | **500,000 rows / month** |
| `api_requests_limit` | **250 requests / month** |
| `api_rows_per_response_limit` | 50,000 rows / response |
| `per_second_api_rate_limit` | 1 req/s |
| `per_minute_api_rate_limit` | 30 req/min |
| `per_hour_api_rate_limit` | 600 req/hour |

`GET /api_usage` returns `plan_name`, `limits`, `current_usage_period_*`,
and `current_period_usage{total_requests,total_api_rows_returned}` — poll
it to track budget.

**Implication for the 5-min soft-restart:** 5-min = 288 intervals/day.
Post-cap window (2022-10-02 → present, ~1,321 days) ≈ **380K rows/pnode**.
- 1 pnode full window ≈ 380K (just under the 500K/mo cap).
- 2 pnodes ≈ 760K → **over the monthly cap**.
- 11-pnode locked set ≈ **4.2M rows ≈ 8.4× the monthly free cap**, ~84
  responses (within the 250-req cap, but the row cap binds first).

A maximalist 5-min re-pull is **infeasible on Free tier in one month**.
Options: (a) paid tier; (b) **academic/research access request** (clean,
reproducible — preferred for a published pipeline); (c) scope reduction
(fewer pnodes / shorter window); (d) spread across months. Multi-account
evasion is a ToS + reproducibility liability for a published project —
avoid.

## Rate limiting / retry (client `gs_client.py`)

- Retriable: HTTP `{429,500,502,503,504}` and `(ConnectionError,
  Timeout)`. Exponential backoff `base_delay=2.0 * 2.0**retries`,
  `max_retries=5`. Optional `sleep_time` between paginated requests.
- Server enforces the hard **1 req/s**; a hand-rolled client must
  self-pace ≥ ~1.3 s/call (free-tier returns
  `429 {"detail":"Too Many Requests. Limit: 1 per 1 second."}`).
- **Read timeouts observed** on multi-day windowed queries at 60 s —
  use a ≥180 s read timeout for range pulls.

## Query API

`GET /datasets/{id}/query` parameters (from client source):

- `start_time`, `end_time` — ISO-8601 (UTC `...Z` accepted).
- `limit`, `page`, `page_size`.
- `columns` — comma-separated projection.
- `filter_column`, `filter_value`, `filter_operator`.
  - **Supported operators: `= != > < >= <= in` only.** `contains` is
    **not** supported.
  - **Empirical: `filter_operator=in` with a comma-joined
    `filter_value` did not return 200 in a raw-HTTP probe.** Prefer
    repeated `=` calls or client-side filtering until the correct `in`
    value encoding is confirmed. `filter_column=location_short_name` +
    `filter_operator="="` is the confirmed-good nodal filter (e.g.
    `LOUDOUN`; `ASHBURN` returns both TX1 34886139 + TX2 34886141 —
    disambiguate client-side on `location_id`).
- `resample_frequency` (e.g. `"1 hour"`, `"7 days"`), `resample_by`,
  `resample_function ∈ {mean,sum,min,max,stddev,count,variance}` —
  server-side aggregation. (Not for the restart response series — that
  needs raw 5-min — but usable for cheap Z/variance or QA.)
- `timezone`, `publish_time` / `publish_time_start` / `publish_time_end`
  (`"latest_report"`, `"latest"`, timestamp, or `None`), `cursor`.

### Response shape / pagination

- Body: JSON with `data` (list of row objects) + `meta`
  (`hasNextPage`, `cursor`). Client also supports an
  `array-of-arrays` mode (row 0 = column names) and CSV
  (`request_format`).
- **Cursor pagination is the default** (`use_cursor_pagination=True`):
  loop while `meta.hasNextPage`, pass `meta.cursor` back as `cursor`.
- Dataset metadata fields (from `GET /datasets`):
  `earliest_available_time_utc`, `latest_available_time_utc`,
  `num_rows`, `all_columns` (list of `{name,...}`), `data_timezone`.
  `GET /datasets` returns **all ~500 datasets in one call** — cache it;
  do not re-list (request budget).

## PJM datasets — relevant facts (empirical 2026-05-15)

| Dataset | Cadence | History | Notes |
|---|---|---|---|
| `pjm_lmp_real_time_5_min` | 5-min | **2018-04-01 → present** | **As-reported** feed = our `rt_fivemin_hrl_lmps`. Nodal: `location, location_id, location_short_name, location_type`. `location_id` == our `pnode_id` (verified 35010365 LOUDOUN, 34886139 ASHBURN TX1). Cols `lmp/energy/congestion/loss` ↔ our `total_lmp_rt/system_energy_price_rt/congestion_price_rt/marginal_loss_price_rt`. |
| `pjm_settlements_verified_lmp_5_min` | 5-min | 2018-04-01 → present | Settlement-verified counterpart (different series — parallel, not drop-in). |
| `pjm_lmp_real_time_hourly` | hourly | 2010-01-01 → present | Nodal; far exceeds PJM DM2 731-day ceiling. |
| `pjm_lmp_day_ahead_hourly` | hourly | 2010-01-01 → present | Nodal. |
| `pjm_load` | **5-min** | 2023-02-07 → present | Per-zone columns incl. `dom` — **but `dom` ≡ `pjm_southern_region` verbatim** (DOM bundled into Southern Region; NOT true DOM 5-min). Same constraint as `pjm-api-constraints.md` § `inst_load` / `decisions.md` §85. |
| `pjm_load_metered_hourly` | hourly | **1993-01-01 → present** | `zone`/`load_area` (DOM available), `mw`, `is_verified`. gridstatus equivalent of our `hrl_load_metered`; far deeper baseline. |

### `pjm_lmp_real_time_5_min` vs our PJM panel — equivalence (empirical)

3-day DST-spanning overlap (2026-03-07 → 03-10, pnodes 35010365 /
34886139 / 34886141, 2,592 rows): **perfect temporal + pnode alignment**
(0 ours-only, 0 gs-only; 864 rows on the 03-08 DST day). **2,568 / 2,592
(99.07%) identical to the cent.** 24 rows (8 timestamps × all 3 pnodes,
bidirectional, max Δ $7.28 on total_lmp) differ. Both series internally
consistent (`energy+congestion+loss − lmp` max 0.0000). Diagnosis: **PJM
real-time LMP republication corrections** — our stored series is
`version_nbr=1` (as-first-reported); gridstatus carries the
later-republished value. gridstatus is the *cleaner/newer* series, not
wrong. ⇒ gridstatus `pjm_lmp_real_time_5_min` is **not byte-identical**
to our pre-registered panel; it is the same as-reported feed with ~0.9%
of 5-min intervals carrying PJM republication updates. Must be disclosed
in any fresh pre-reg; not disqualifying.

## Ops notes

- **Request budget is the binding free-tier constraint** (250/mo). Be
  surgical: cache `GET /datasets` and every pull to disk; never
  shotgun-probe; combine questions into single scripts.
- Probe scripts for this project live in `/tmp` (throwaway, zero repo
  footprint); production acquisition would add a `gridstatusio`-backed
  module under `src/surg/acquisition/` only after a tier/access decision.
- All probing 2026-05-15 used GET only, bounded, paced; the deep-history
  + equivalence claims above are empirically grounded, not doc-scraped.
