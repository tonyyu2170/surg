# PJM Data Miner 2 API — Discovered Constraints

Source: `docs/data-miner-2-api-guide.pdf` (PJM, Feb 2026 revision) and the
API portal at `https://apiportal.pjm.com`. This file captures facts the
API forces on us, separate from `decisions.md` which records what we
chose to do about them.

## Transport / auth

- **Base URL:** `https://api.pjm.com/api/v1/` (production)
  - Training environment: `https://api-train.pjm.com/api/v1/` — keys are
    NOT interchangeable.
- **Auth:** header `Ocp-Apim-Subscription-Key: <key>` (Azure APIM
  standard). Query-string fallback: `?subscription-key=<key>` (avoid;
  leaks key into logs).
- **TLS 1.2 required.**
- **No GET with body** (rejected by PJM's security appliance since
  Nov 1, 2025).
- **gzip:** when `download=true`, response *may* be gzipped. Always
  inspect `Content-Encoding` before decoding (PJM disabled
  unconditional gzip on Sep 9, 2025).

## Pagination

- `rowCount` per page: **max 50,000**.
- Next page: `startRow = previous_startRow + rowCount`.
- Total row count: `X-TotalRows` HTTP response header (only when
  `download=true`; otherwise embedded in JSON body as `totalRows`).
- **Sort on the same date column you filter on** (use `_ept` with
  `_ept`, `_utc` with `_utc`) for performance.

### JSON envelope (without `download=true`)

Confirmed empirically 2026-05-10 against `/pnode?zone=DOM`:

```
{
  "links": [...],
  "items": [...],          // the actual rows
  "searchSpecification": {...},
  "totalRows": <int>       // total matching across all pages
}
```

### Response headers

PJM does **not** surface rate-limit information per response.
Empirical inspection of `X-*` headers shows only `x-powered-by: ASP.NET`.
There is no `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
`X-RateLimit-Reset`, or `Retry-After`. Clients must track their own
request count.

## Date filtering

- Format: `datetime_beginning_ept=MM-DD-YYYY HH:MM to MM-DD-YYYY HH:MM`
  (also accepts `YYYY-MM-DD`).
- **Range cap: 366 days per request.**
- Open-ended ranges (`to MM-DD-YYYY` or `MM-DD-YYYY to`) are allowed.
- Append ` exact` to a date for exact-timestamp match.
- Special tokens for short windows: `Today`, `Yesterday`, `LastWeek`,
  `CurrentMonth`, `15SecondsAgo`, `5MinutesAgo`, etc. The two seconds-
  /minutes-ago tokens only work on `_ept` columns and only on dispatch
  rates / unverified LMP feeds.

## Archived ("Historic") data — *the big constraint*

PJM splits each archived feed into "Standard" (recent) and "Historic"
(older) tiers based on a feed-specific cutoff. Historic queries have
heavy restrictions.

| Feed | Archive cutoff | Notes |
|------|----------------|-------|
| `rt_fivemin_hrl_lmps` | **186 days** (~6 months) | Highest-volume feed |
| `rt_hrl_lmps`         | **731 days** (~2 years)  | Hourly RT LMP |
| `da_hrl_lmps`         | **731 days** (~2 years)  | Hourly DA LMP |

**Real-time-monitoring feeds with hard retention caps** (separate
constraint from the archive/Standard split above — these feeds delete
old data outright):

| Feed | Retention | Posting frequency | Notes |
|------|-----------|-------------------|-------|
| `operational_reserves` | **15 days** | every 15 seconds | Designed for live monitoring, not historical analysis. Cannot retrospectively pull windows > 15 days old. Discovered 2026-05-11 via live metadata API. |

**Restrictions on Historic queries:**
- Date range must be **within a single calendar year** (UTC).
- **No custom sort/order** — results are always sorted by
  `datetime_beginning_utc` ascending.
- Allowed filter attributes: `dates`, `type`, `row_is_current`,
  `version_nbr` only.
  - `pnode_id` filter is **rejected** on Historic data.
  - `type` filter is **rejected** on Historic 5-min LMP specifically.
- A request that spans the cutoff boundary is rejected outright with
  "Date range in the API request spans over archived and standard
  data".
- Metadata response gains: `enableArchiving`, `archiveCutoffDays`,
  `enableArchiveFiltering`.

**Implication for this project:** to retrieve nodal LMP for specific
substations across multi-year history, we cannot simply filter by
`pnode_id` against Historic data. We must either (a) pull the entire
feed for each calendar year and filter client-side, or (b) restrict
nodal analysis to the Standard window. See `decisions.md` for the
chosen approach.

## LMP versioning

- LMP rows are versioned. Use `row_is_current=true` to retrieve only
  the latest version (recommended default).
- `row_is_current=false` returns superseded versions; `=all` returns
  every version.
- Each row carries a `version_nbr`.

## Feeds we'll use

### `pnode` — pnode reference / metadata

Filterable fields: `pnode_id`, `pnode_name` (partial, case-insensitive),
`pnode_type` (`AGGREGATE`, `BUS`, `LOCALE`), `pnode_subtype`
(`AGGREGATE`, `EHV`, `EXT`, `GEN`, `HUB`, `INTERFACE`, `LOAD`,
`RESIDUAL_METERED_EDC`, `TIE`, `ZONE`), `zone` (DOM, AECO, AEP, etc.),
`voltage_level`.

Active-only: `terminate_date_ept=12/31/9999 exact`.

### `rt_fivemin_hrl_lmps` — 5-min real-time nodal LMP

Returned fields: `datetime_beginning_utc`, `datetime_beginning_ept`,
`pnode_id`, `pnode_name`, `voltage`, `equipment`, `type`, `zone`,
`system_energy_price_rt`, `total_lmp_rt`, `congestion_price_rt`,
`marginal_loss_price_rt`, `row_is_current`, `version_nbr`.

**Zone filter is disabled** on this feed due to data volume — the docs
explicitly say to first hit `pnode` to resolve zone→pnode_ids, then
query LMP by `pnode_id` (Standard data only; see archive constraint).

### `rt_hrl_lmps`, `da_hrl_lmps` — hourly RT / DA nodal LMP

Same field set as above (DA uses `_da` price suffixes).
Zone filter *is* available on these (allowed values include DOM).

### `hrl_load_metered`, `hrl_load_estimated` — hourly zonal load

`hrl_load_metered` filters: `nerc_region`, `mkt_region`, `zone`,
`load_area`, `is_verified`. Zone allowed values include DOM. Field:
`mw`, `is_verified`.

`hrl_load_estimated` filters: `load_area` (DOM available). Field:
`estimated_load_hourly`.

### `inst_load` — 5-min instantaneous load

**Region-only:** `area` allowed values are `PJM MID ATLANTIC REGION`,
`PJM RTO`, `PJM SOUTHERN REGION`, `PJM WESTERN REGION`. **No DOM-zone
filter.** DOM is bundled into `PJM SOUTHERN REGION`.

## Empirical findings from 2026-05-10 spike

- **Default sort order is NOT by date.** The `hrl_load_metered`
  response came back in apparently random order. Pass
  `sort=datetime_beginning_ept&order=Asc` explicitly when ordering
  matters (which is almost always for time-series work).
- **Timestamps come back as ISO-8601 strings** (e.g.
  `"2026-04-15T04:00:00"`), not native datetimes. Pandas reads them
  as `object` dtype — coerce with `pd.to_datetime` before analysis.
- **EPT vs UTC offset** is consistent with normal Eastern conversion
  (-4 in DST, -5 in standard time). For 2026-04-15: 00:00 EPT =
  04:00 UTC.
- **`hrl_load_metered` with `zone=DOM`** returns one row per hour
  (24/day), with both `zone` and `load_area` columns = `DOM`. No
  fan-out across multiple `load_area`s. Recent rows have
  `is_verified=False` — verification lags by some days/weeks.
- **`rt_hrl_lmps` and `rt_fivemin_hrl_lmps` have identical field
  shapes** as the API guide promises. 24 and 288 rows per day per
  pnode respectively (non-DST day).
- **Pnode aggregates exist at substation granularity.** Querying
  `pnode?zone=DOM&pnode_name=Pleasant View` returned a single
  `AGGREGATE / EHV / 500 KV` pnode (`pnode_id=35010371`) — i.e. the
  substation as a single 500 KV aggregate, not its constituent
  buses. This is a useful unit of analysis, possibly preferable to
  picking a single bus.
- **Substation name resolution is fragile.** "Ashburn" and "Goose
  Creek" returned zero matches via partial-name search, despite
  being known DOM constraint elements. PJM's registry uses
  abbreviated names. Always verify by pulling the full DOM pnode
  list and grepping client-side rather than trusting a single
  partial-name query.
- **`pnode_name` is truncated in LMP feed responses.** The
  `pnode` registry stores the full name (e.g.
  `"ASHBURN 35 KV   TX1"`), but `rt_hrl_lmps` /
  `rt_fivemin_hrl_lmps` return only the short substation name
  (e.g. `"ASHBURN"`) for both TX1 and TX2. **Always identify
  pnodes by `pnode_id` (numeric) in any join, group-by, or
  aggregation — never by `pnode_name`.**
- **Zonal-aggregate pnodes are NOT tagged with their own zone.**
  The DOM zonal pnode (`pnode_id=34964545`, `pnode_name="DOM"`,
  `pnode_type=AGGREGATE`, `pnode_subtype=ZONE`) has `zone=null`
  in the registry. To find zonal pnodes, query
  `pnode?pnode_subtype=ZONE` without a zone filter (returns
  ~20–25 rows, one per PJM zone).
- **Multi-pnode pulls work via semicolon-packed `pnode_id`.**
  Confirmed: `pnode_id=A;B;C;...` returns rows for all listed
  pnodes in a single API call. Major efficiency under the 6/min
  rate limit — pack as many pnodes per call as the result fits
  under the 50K row page cap.

## Performance / ops notes

- Filter on `pnode_id` (numeric exact) instead of `pnode_name`
  (substring) for query performance.
- **Pack multiple pnodes per call** with `pnode_id=X;Y;Z`
  (semicolon-separated). Per API guide §VI example 2 — this is
  a major efficiency for nodal pulls under the 6/min rate limit.
- Per-fetch export limit: 50K rows.
- **Rate limit: 6 calls/minute** on the free tier (empirical,
  confirmed from the API portal subscription details on 2026-05-10).
  Not documented in the API guide PDF.
  - Implies a minimum spacing of ~11 seconds between requests to
    stay safely under the limit (one slot of safety margin).
  - All clients (notebook fetcher, future acquisition module) must
    throttle. Burst-then-pause is risky because 6/min appears to be
    a rolling-window count, not a per-second token bucket.
  - Plan for 429 responses with an exponential-backoff retry; do
    not retry-storm.
  - Bulk-pull runtime is dominated by this limit. Examples assuming
    one page per call:
    - Nodal 5-min × 6 months × 10 pnodes (~11 pages) ≈ 2 min
    - Nodal hourly × 2 years × 10 pnodes (~4 pages) ≈ 45 s
    - DOM zonal hourly × 5 years (chunked into 5 yearly calls
      due to the 366-day range cap) ≈ 55 s
