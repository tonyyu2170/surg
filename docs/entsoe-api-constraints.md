# ENTSO-E Transparency Platform API — Documented Constraints

Source: **documentation extraction, 2026-08-12**, plus a **live probing
pass the same day** (`scripts/entsoe_probe.py`) that verified three
specific behaviours. Everything not marked **[PROBED]** is still only
"what the vendor says", not "what we measured" — contrast
`ukpn-api-constraints.md`, which was probed throughout.

**Probing changed three answers.** In short:

| Claim | Doc says | Measured |
|---|---|---|
| Parameter name casing | case-**sensitive** | **case-INsensitive** — every spelling worked |
| Parameter *value* casing | (not stated) | **case-SENSITIVE** — `a44` rejected |
| Over-cap behaviour | (not stated) | **HTTP 400 with an exact count**, never a silent truncation |
| Size caps | one figure per data item | **enforced per endpoint, and 12.1.D ignores its own** |
| Unknown parameters | (not stated) | **rejected**, not ignored |

The rate limit was **not** measured — see that section.

> **Correction, same day.** An earlier reading of the 12.1.D result alone
> concluded that omitting `offset` lifts the response cap generally, and
> recommended omitting it for bulk pulls. Probing two further endpoints
> falsified that: 13.1.A and 10.1.A&B both return HTTP 400 when over cap
> with `offset` absent. 12.1.D is the outlier. The corrected guidance —
> chunk by time range, use `offset` only where documented — is in the
> `offset` section below.

Documentation set extracted:

- **Zendesk knowledge base**, `https://transparencyplatform.zendesk.com`
  — the "Sitemap for Restful API Integration"
  ([article 15692855254548](https://transparencyplatform.zendesk.com/hc/en-us/articles/15692855254548-Sitemap-for-Restful-API-Integration),
  updated 2026-08-10) and the 41 articles it indexes, plus the File
  Library, subscription, FAQ and data sections. 272 articles exist in the
  help centre overall; the ~73 in API-relevant sections were read.
- **Postman collection** "Transparency Platform Restful API",
  `https://documenter.getpostman.com/view/7009892/2s93JtP3F6` — 77
  endpoints across 8 folders. Three separate Zendesk articles name this
  as the authority for per-endpoint parameters, so it governs where it
  disagrees with prose.
- **XML examples repo**, `https://gitlab.entsoe.eu/transparency/xml-examples`
  (public, reachable; contents not yet enumerated).

> **Fetching note.** The Zendesk HTML pages sit behind a Cloudflare
> challenge and return **403 to both WebFetch and curl**. The Help Center
> REST API is open and unauthenticated:
> `https://transparencyplatform.zendesk.com/api/v2/help_center/en-us/articles.json?per_page=100`
> (paginate via `next_page`). The Postman docs are likewise a JS SPA, but
> `https://documenter.getpostman.com/api/collections/7009892/2s93JtP3F6`
> returns the full collection JSON (~7.4 MB). Use these routes on any
> re-check.

**Companion file:** `entsoe-endpoint-reference.md` holds the full
per-endpoint parameter matrix for all 77 REST endpoints, extracted from
the Postman collection.

Key stored in project `.env` as `ENTSOE_API_KEY`, same convention as
`PJM_API_KEY` / `GRIDSTATUS_API_KEY_*` / `UK_POWER_API_KEY`.

## Four separate access channels — separate credentials, separate limits

This is the single most important structural fact. ENTSO-E is not one
API. The channels do **not** share a rate-limit counter.

| Channel | Host | Credential | Rate limit |
|---|---|---|---|
| **REST API** (Web API) | `web-api.tp.entsoe.eu/api` | security token from My Account | 400 req/min per token |
| **File Library** (FMS) | `fms.tp.entsoe.eu` | TP **email + password** via Keycloak → bearer | 100 req/min per user login |
| **Subscriptions** | pushed to *your* endpoint | ECP or SOAP 1.2 web-service channel | n/a (push) |
| **Web service submission** | `ws-submission.tp.entsoe.eu` | client cert / machine user | mostly a data-*provider* channel |

The File Library Guide states this explicitly: *"The number of requests
is determined per user login name and distribution channel (FMS has a
separate counter from e.g., Web API)."* So REST and FMS budgets are
additive, not shared.

---

# 1. REST API

## Transport and auth

- **Production endpoint:** `https://web-api.tp.entsoe.eu/api`
- **IOP (test) endpoint:** `https://web-api.tp-iop.entsoe.eu/api` —
  documented as containing *less* data than production.
- **Only HTTPS.** Plain HTTP is not supported.
  ([Request Endpoint](https://transparencyplatform.zendesk.com/hc/en-us/articles/15696677194644-Request-Endpoint), upd. 2026-07-16)
- **GET:** token as query parameter, key `securityToken`.
- **POST:** token in the HTTP header, key `SECURITY_TOKEN`;
  `Content-Type: application/xml`; body is a `StatusRequest_MarketDocument`.
  (Postman also shows a GET variant passing the token in-header.)
- Missing/invalid token, or a suspended account → **HTTP 401**.
- If the token is compromised, **you must reset it yourself** in My Account.
- **Request timeout is 5 minutes (300 s)** per request; normal responses
  are "a few seconds".
  ([Rate Limit Part 2](https://transparencyplatform.zendesk.com/hc/en-us/articles/12783223209876), upd. 2023-06-15)

### Getting a token (already done — recorded for reproducibility)

1. Register at `https://transparency.entsoe.eu/` and verify by email.
2. Email `transparency@entsoe.eu`, subject **"RESTful API access"**, with
   the registered address in the body.
3. Access granted **within 3 working days**.
4. My Account → generate token.

([How to get security token](https://transparencyplatform.zendesk.com/hc/en-us/articles/12845911031188-How-to-get-security-token), upd. 2026-08-07)

## Rate limit — 400 requests/minute **per token** ⚠ two articles disagree

**Authoritative** —
[API Rate Limit Part 1](https://transparencyplatform.zendesk.com/hc/en-us/articles/12783148966036),
**updated 2026-08-12T09:31:59Z** (i.e. the morning this was extracted):

- **400 requests per minute per user account (API token).**
- **Enforcement is per token, not per IP.** Verbatim: *"No IP-Based
  Banning in R3 API: With the transition to the TP R3 API, rate limiting
  and bans are no longer applied based on IP addresses. The system now
  tracks usage and applies restrictions solely per user account (API
  token)."*
- Exceeding 400/min → the system **may temporarily ban the token**.
- Distributed clients (e.g. Kubernetes across many nodes/IPs) sharing one
  token aggregate into the same counter and will trip the ban.
- ENTSO-E reserves the right to **revoke** a compromised or misused token.
- Recommended client-side throttle, verbatim: *"6–7 req/sec on average,
  with burst handling."*
- When reporting a 429 issue, supply: account email, exact 429
  timestamps, and per-minute request counts.

**Stale, do not build against** — the
[Query Response](https://transparencyplatform.zendesk.com/hc/en-us/articles/15727773247124)
article (upd. 2025-12-09) still carries an HTTP-code table reading
*"429 — Too many requests - max allowed 400 per minutes from eash [sic]
unique IP"*. Part 1 is both newer **and** explicitly states the per-IP
model was superseded in R3. **Part 1 governs.** Recorded here because a
reader who hits the 429 table first would build per-IP sharding that buys
nothing.

**Unban duration is soft.** Part 1 says: *"Bans are temporary. The ticket
mentions users are automatically unbanned after approximately 10
minutes."* That is pasted support-ticket phrasing, not a spec — treat
~10 min as an estimate, not a constant to hard-code into a backoff.

### NOT VERIFIED — deliberately

`scripts/entsoe_probe.py` implements a probe for this (threshold index,
fixed-vs-rolling window shape, and the real unban interval) but it is
**dry-run by default and was not armed**. Verifying the limit requires
deliberately exceeding it, and while the vendor documents the resulting
ban as temporary and automatic, the same article states ENTSO-E
*"reserves the right to revoke the token"* for misuse. A burst that trips
abuse detection risks the key — which took 3 working days to obtain and
gates this whole thread — to confirm a number the vendor is unlikely to
be wrong about. Judged not worth it (decision 2026-08-12).

If it ever becomes worth measuring, prefer a **paced** overshoot (~7 req/s
to ~420 requests, matching the docs' own recommended throttle) over the
unthrottled burst the script currently implements.

## Query size limits — per data item

Two prose articles disagree on the document cap: [Rejection of
Request](https://transparencyplatform.zendesk.com/hc/en-us/articles/15854332833300)
(upd. 2025-12-11) says *"More than 100 matching documents"*, while
[Request Rejections](https://transparencyplatform.zendesk.com/hc/en-us/articles/12783463360532)
(upd. 2023-06-15) says *"More than 200"*. **Neither is global.** The
[API Query Size Limit](https://transparencyplatform.zendesk.com/hc/en-us/articles/15854536354964)
table (upd. 2025-10-07) resolves it per data item — outages are 200,
the other capped items are 100. That table is the authority:

| Domain | Data item | Article | Limit |
|---|---|---|---|
| Load | Actual Total Load | 6.1.A | 1-year range |
| Load | Day-Ahead Total Load Forecast | 6.1.B | 1-year range |
| Load | Week/Month/Year-Ahead Load Forecast | 6.1.C/D/E | 1-year range |
| Load | Year-Ahead Forecast Margin | 8.1 | 1-year range |
| Transmission | Expansion and Dismantling Projects | 9.1 | 100 documents |
| Transmission | Forecasted Capacity | 11.1.A | 1-year range |
| Transmission | Offered Capacity | 11.1.A | 100 documents |
| Transmission | Flow-based Parameters | 11.1.B | 100 documents |
| Transmission | Intraday Transfer Limits | 11.3 | 1-year range |
| Transmission | Explicit Allocation (Capacity & Revenue) | 12.1.A | 100 documents |
| Transmission | Total Capacity Nominated | 12.1.B | 1-year range |
| Transmission | Total Capacity Already Allocated | 12.1.C | 100 documents |
| **Transmission** | **Day Ahead Prices** | **12.1.D** | **1-year range** |
| Transmission | Implicit Auction | 12.1.E | 1-year (Net Positions) / 100 docs (Congestion Income) |
| Transmission | Total & Day-ahead Commercial Schedules | 12.1.F | 1-year range |
| Transmission | Physical Flows | 12.1.G | 1-year range |
| Transmission | Capacity Allocated Outside EU | 12.1.H | 100 documents |
| Congestion | Redispatching | 13.1.A | 100 documents |
| Congestion | Countertrading | 13.1.B | 100 documents |
| Congestion | Costs of Congestion Management | 13.1.C | 100 documents |
| Generation | Installed Generation Capacity (aggr. & per unit) | 14.1.A/B | **no limit** |
| Generation | Day-ahead Aggregated Generation | 14.1.C | 1-year range |
| Generation | Generation Forecasts Wind & Solar | 14.1.D | 1-year range |
| **Generation** | **Actual Generation per Generation Unit** | **16.1.A** | **1-DAY range** |
| Generation | Aggregated Generation per Type | 16.1.B/C | 1-year range |
| Generation | Aggregated Filling Rate of Water Reservoirs | 16.1.D | 1-year range |
| Balancing | Current Balancing State | 12.3.A | **100-day range** |
| Balancing | Balancing Energy Bids | 12.3.B/C | 100 documents |
| Balancing | Changes to Bid Availability | IFs mFRR 9.9 etc. | 100 documents |
| Balancing | Aggregated Balancing Energy Bids | 12.3.E | 1-year range |
| Balancing | Procured Balancing Capacity | 12.3.F | 100 documents |
| Balancing | Cross-Zonal Balancing Capacity use | 12.3.H/I | general rules |
| Balancing | Volumes/Prices of Contracted Reserves | 17.1.B/C | general rules |
| Balancing | Accepted Aggregated Offers | 17.1.D | 1-year range |
| Balancing | Activated Balancing Energy | 17.1.E | 1-year range |
| Balancing | Prices of Activated Bal. Energy, aFRR CBMPs | 17.1.F | 1-year range |
| Balancing | Imbalance Prices | 17.1.G | 1-year range |
| Balancing | Total Imbalance Volumes | 17.1.H | 1-year range |
| Balancing | Financial Expenses/Income for Balancing | 17.1.I | 1-year range |
| Balancing | Cross-border Balancing | 17.1.J | 1-year range |
| Balancing | FCR total capacity / shares | SO GL 187.2 | 1-year range |
| Balancing | FRR Actual Capacity | SO GL 188.4 | general rules |
| Balancing | Sharing of RR and FRR | SO GL 190.1 | 1-year range |
| Outages | Unavailability of Consumption Units | 7.1.A/B | 1-year range |
| Outages | Unavailability of Transmission Infrastructure | 10.1.A/B | 1-year **& 200 documents** |
| Outages | Unavailability of Offshore Grid | 10.1.C | 1-year **& 200 documents** |
| Outages | Unavailability of Generation Units | 15.1.A/B | 1-year **& 200 documents** |
| Outages | Unavailability of Production Units | 15.1.C/D | 1-year **& 200 documents** |
| Outages | Fall-backs | IFs IN 7.2 etc. | 100 documents |

Exceeding a limit yields a **negative acknowledgement**, not a truncated
result.

The Postman collection restates these per endpoint and adds granularity
the Zendesk table lacks — e.g. **aFRR** variants of "Netted and Exchanged
Volumes" are capped at **1 day** while other process types get 1 year;
and "IF aFRR 3.16 Cross Border Marginal Prices" is **1 day**.

## [PROBED] `offset` — real, per-endpoint, and the cap rejects rather than truncates

**The single most important measured fact: exceeding a size limit returns
HTTP 400, not a truncated response.** The error is explicit and
quantified, which makes it easy to size a pull:

```
The number of instances (342) exceeds the allowed maximum (200)
for data item UNAVAILABILITY_IN_TRANSMISSION_GRID.
```

So there is no silent data loss — but a naive one-request-per-year pull
will simply fail on dense endpoints.

Measured across three endpoints with different documented caps:

| Endpoint | Doc cap | `offset` omitted | `offset=0` |
|---|---|---|---|
| **12.1.D** Energy Prices, DE-LU, 2024 | 100 TimeSeries | **200 OK — all 732** | 200 OK — 100 |
| **13.1.A** Redispatching Internal, NL, 2024 | 100 TimeSeries | **400** — 140 > 100 | **400** — 140 > 100 |
| **10.1.A&B** Transmission Unavail., FR→BE, 2024 | 200 documents | **400** — 342 > 200 | **200 OK — 200 docs** |

Three distinct behaviours, and the difference is *per endpoint*:

1. **12.1.D does not enforce its documented cap.** 732 TimeSeries came
   back in one response against a documented maximum of 100. The
   published figure is wrong or stale for this data item. Do not
   generalise from it — it was the first endpoint probed and it is the
   exception, not the rule.
2. **13.1.A cannot be rescued by `offset`.** Postman does not list
   `offset` for this endpoint, and supplying it changed nothing — the
   same 400 came back. Over-cap queries here must be **narrowed by time
   range**; pagination is not available.
3. **10.1.A&B is exactly as documented.** Over-cap without `offset`,
   and `offset=0` returns a clean 200-document ZIP page.

**Practical rule: chunk by time range first, and use `offset` only on the
20 endpoints that document it.** Treat the 400 as the signal to halve the
window. Do *not* assume omitting `offset` lifts anything.

When `offset` is supported, pagination is correct and complete
(verified on 12.1.D, 2024, 732 series):

- Pages are **disjoint** by `timeInterval` — no duplication across pages.
- Pages are **contiguous**: page 0 ends `2024-02-18T23:00Z/2024-02-19T23:00Z`,
  page 1 begins `2024-02-19T23:00Z/2024-02-20T23:00Z`.
- The tail closes exactly: `offset=700` returned 32, and 700 + 32 = **732**,
  matching the un-offset total.

**⚠ Trap: `mRID` is not a stable identifier.** Within a
`Publication_MarketDocument`, each `TimeSeries/mRID` is a document-local
counter restarting at 1 on every page — so pages 0, 100 and 200 all carry
mRIDs `1…100`. Deduplicating on `mRID` will silently collapse a paged
pull to 100 rows. **Key on `timeInterval`** (or area + interval) instead.

**⚠ Trap: `offset` is accepted but silently ignored where unsupported.**
On 6.1.A Actual Total Load — where Postman does not document it —
`offset=100` against a 1-TimeSeries response returned that 1 TimeSeries
rather than an empty page or an error. Since unknown parameters *are*
rejected (see casing section), `offset` is globally valid but only
*honoured* on endpoints that paginate. You cannot detect non-support from
the response.

### Where it is documented

**Not listed in the [Available
Parameters](https://transparencyplatform.zendesk.com/hc/en-us/articles/15856744319380)
article** (upd. 2026-07-16), but documented on many Postman endpoints:

> *"The `offset` parameter can be used to retrieve the data in batches of
> up to 100 TimeSeries, where `offset=0` returns the first 100 elements,
> `offset=100` returns the next 100, and so on."*

Outage endpoints use the same mechanism in steps of 200. This turns the
100/200-document ceiling from a hard wall into a pagination stride, which
Documented on **20 of the 77 endpoints**: 12.1.D Energy Prices, 11.1
Continuous Allocations, 12.3.B&C Balancing energy bids (+archives),
Changes to Bid Availability (+archives), Elastic Demands, 17.1.B&C,
12.3.F, SO GL 190.1/190.2/190.3, all six 10.1/15.1 outage endpoints,
Fall-backs, and OMI. Outage endpoints page in steps of 200 rather than
100. It remains absent from the Zendesk parameter reference.

## Response-shape limits (Postman, per endpoint)

Response caps are expressed in three different units depending on the
endpoint, which matters when sizing a pull:

- **TimeSeries elements per XML response** — the common case (100).
- **XML documents inside a ZIP response** — outages, OMI (200).
- **ZIP files inside a ZIP response** — the `…Archives` endpoints (100).
- **Instances** — 11.1.B Flow Based Allocations returns *"a maximum of 1
  instances contained in the ZIP response, split into several files"*;
  12.3.H&I returns max 100 instances, *"one instance can be split into up
  to 8 TimeSeries"*.

Some endpoints count TimeSeries *across* all XML documents in the ZIP
(12.3.B&C, 17.1.B&C, 12.3.F, SO GL 190.3) rather than per document.

## Rejection conditions

A request is rejected when any of these hold
([Rejection of Request](https://transparencyplatform.zendesk.com/hc/en-us/articles/15854332833300), upd. 2025-12-11):

- missing mandatory parameters
- **duplicate parameters** (repeating `documentType` twice fails)
- forbidden characters, or **letter case that does not match** — parameter
  names are case-sensitive; GET requests must URL-escape special characters
  or return HTTP 400
- no data found
- date range exceeds the permitted limit
- too many matching documents

The response is an `Acknowledgement_MarketDocument` carrying a `<Reason>`
with `<code>` and `<text>`.

| HTTP | Reason code | Meaning |
|---|---|---|
| 200 | 999 | No matching data found |
| 400 | 999 | Invalid query attributes or parameters |
| 401 | — | Unauthorized: missing or invalid security token |
| 429 | — | Too many requests |

Note **200 + reason 999**: "no data" arrives as an HTTP *success*
carrying an acknowledgement document. Any client must parse the body to
distinguish data from emptiness — status code alone is not enough.

## Request parameters

- **Parameter names are case-sensitive.** Order is not significant, but
  the docs recommend data-item identifiers first, then filters, then the
  date range, for troubleshooting.
- **Omitting an optional filter returns everything** for that dimension —
  e.g. omitting `businessType` on an outage query returns both planned
  and unplanned.
- **A time interval is always mandatory.** Two mutually exclusive forms:
  - `periodStart` / `periodEnd`, pattern `yyyyMMddHHmm` — **GET only**
  - `timeInterval`, pattern `yyyy-MM-ddTHH:mmZ/yyyy-MM-ddTHH:mmZ` — GET **and** POST
  - They return identical data; the two forms cannot be combined.
- **All times are UTC**, on both request and response.
- `timeIntervalUpdate` (or `periodStartUpdate` + `periodEndUpdate`) —
  **Outages only.** Filters to publications *updated* in a window, which
  is the documented way to avoid re-downloading outages already held. The
  docs cite UK outages exceeding 200 documents in a 2-hour query as the
  motivating case. When these are supplied, the 1-year range limit
  applies to *them* rather than to `periodStart`/`periodEnd`.
- `Update_DateAndOrTime` takes numeric datetime, e.g.
  `20210803113900000` for 03.08.2021 13:39:00.000.

Full parameter list (all valid on both GET and POST unless noted):
`DocumentType`, `DocStatus`, `ProcessType`, `BusinessType`, `PsrType`,
`Type_MarketAgreement.Type`, `Contract_MarketAgreement.Type`,
`Auction.Type`, `Auction.Category`,
`ClassificationSequence_AttributeInstanceComponent.Position`,
`OutBiddingZone_Domain`, `BiddingZone_Domain`, `ControlArea_Domain`,
`In_Domain`, `Out_Domain`, `Acquiring_Domain`, `Connecting_Domain`,
`RegisteredResource`, `Standard_MarketProduct`, `Original_MarketProduct`,
`Direction`, `TimeInterval`, `PeriodStart` (GET), `PeriodEnd` (GET),
`TimeIntervalUpdate`, `PeriodStartUpdate` (GET), `PeriodEndUpdate` (GET),
`Update_DateAndOrTime`.

### Parameters the Zendesk reference omits

The Postman collection uses ten parameters that do **not** appear in the
[Available Parameters](https://transparencyplatform.zendesk.com/hc/en-us/articles/15856744319380)
article. Treat that article as incomplete:

`offset` (pagination, see above), `curveType` (request-side — `A01`
sequential fixed block vs `A03` variable sized blocks, **A03 is the
default**; appears as an `[O]` parameter on most endpoints),
`Area_Domain`, `Domain`, `Asset_RegisteredResource.mRID`,
`pTDF_Domain.mRID`, `Implementation_DateAndOrTime` (Production and
Generation Units — sets the start of the validity window),
`StorageType`, `ExportType`, `mRID`.

That `curveType` is settable per request is worth noting: the response
sections below describe A03 as forced, but the collection presents it as
a client choice with an A03 default.

### [PROBED] Casing: names are case-INsensitive, values are case-SENSITIVE

The docs state plainly that *"Parameter names are case sensitive."*
**That is false for names.** Measured against 12.1.D (DE-LU, 2024-06-01):

| Variant | Result |
|---|---|
| `curveType=A03` vs `curvetype=A03` | both **accepted**, identical output |
| `contract_MarketAgreement.type` vs `.Type` | both **accepted**, identical output |
| `DocumentType=A44` *alone*, no lowercase form | **accepted** |
| `documenttype=A44` *alone* | **accepted** |
| `documentType` omitted entirely (control) | **400** — `The combination of [] is not valid` |
| `documentType=a44` (lowercase **value**) | **400** — `The combination of [DOCUMENT_TYPE=a44] is not valid` |
| `bogusParam=xyz` (control) | **400** — `Input parameter does not exist: bogusParam` |

The discriminator is row 3: `documentType` is mandatory, and omitting it
*does* fail (row 5), so a request carrying only `DocumentType` could not
have succeeded unless the renamed key was actually read. It was.

The error text gives the mechanism away — the API normalises names to an
internal canonical form and echoes *that* back (`DOCUMENT_TYPE`), which is
why surface casing does not matter.

**Consequences:**

- ENTSO-E's inconsistent Postman casing is **harmless**. Either spelling
  works. This is a documentation defect, not a client-side hazard.
- **Values remain case-sensitive** — `A44` ≠ `a44`. Never lower-case a
  code before sending it.
- **Unknown parameters are rejected, not silently dropped** — a typo'd
  parameter name fails loudly with `Input parameter does not exist: <name>`,
  which is genuinely helpful. (One exception below: `offset`.)

## Response semantics — several traps

- **Time is always UTC in the response.**
- **Timezone of the *area*, not the requester, sets day boundaries.**
  A query for CZ day-ahead prices on 2016-04-06 returns
  `2016-04-05T22:00Z` → `2016-04-06T22:00Z` (summer), but
  `2016-12-05T23:00Z` → `2016-12-06T23:00Z` in winter. The docs warn this
  is *"the time zone in which the area or border is physically located.
  However, there can be exceptions … due to regional arrangements for
  capacity allocations"* — and name 12.1.D and 12.1.E as exceptions.
  Also: the response interval follows the area's **configured** timezone,
  which *"may not be the same as the geographical time zone."*
- **You get back more than you asked for.** *"System returns both
  partially and exactly matching data."* A one-day query against a weekly
  allocation returns the whole week; a one-minute query against day-ahead
  forecasted capacity returns one MTU.
- These articles always return whole days (or multiples): 11.1
  Flow-based, 11.1 Offered Transfer Capacities (implicit & explicit),
  **12.1.D Energy Prices**, 12.1.C, 12.1.E (both), 12.1.A (both), 12.1.H.
  Everything else returns the requested MTU/BTU periods.
- **Border queries are one-directional.** With `in_Domain` + `out_Domain`
  set, you get one direction only; swap them and re-request for the other.
  Postman adds, for 12.1.G: *"Unlike Web GUI, API responds not netted
  values as data is requested per direction."*
- **CurveType — the two sources disagree.** [Query
  Response](https://transparencyplatform.zendesk.com/hc/en-us/articles/15727773247124)
  says *"Curve type in response is A03 for all data items."* The
  [Subscription
  guide](https://transparencyplatform.zendesk.com/hc/en-us/articles/15230327975828)
  (upd. 2026-08-12) says A03 for all **except** Flow-based Allocations
  [11.1], Balancing Energy Bids [12.3.B&C], and Netted and Exchanged
  Volumes / per border, *"for which only curveType A01 is available."*
  The subscription statement is more specific and same-day-fresh; assume
  exceptions exist and detect `curveType` per document rather than
  assuming.
- **A03 is variable-sized blocks** — only positions *where the value
  changes* are emitted. A flat series is one point, not N points.
  Expanding A03 to a dense grid is the caller's job, and "value did not
  change" is indistinguishable from "publication missing" without care.
  See [CurveType A01 vs
  A03](https://transparencyplatform.zendesk.com/hc/en-us/articles/30262342482961)
  (upd. 2025-12-18).
- **Decimal values can be returned** post-R3 migration (previously
  integers). Numbers carry max **12 total digits, up to 6 decimal
  places**; leading/trailing zeros trimmed; over-12-digit values rejected.

## Code lists

`Contract_MarketAgreement.Type` / `Type_MarketAgreement.Type`: A01 Daily,
A02 Weekly, A03 Monthly, A04 Yearly, A05 Total, A06 Long term,
A07 Intraday, A13 Hourly (A13 on `Type_MarketAgreement.Type` only).

`Auction.Type`: A01 Implicit, A02 Explicit.
`Auction.Category`: A01 Base, A02 Peak, A03 Off Peak, A04 Hourly.

`ProcessType`: A01 Day ahead, A02 Intra day incremental, A16 Realised,
A18 Intraday total, A31 Week ahead, A32 Month ahead, A33 Year ahead,
A39 Synchronisation, A40 Intraday process, A46 RR, A47 mFRR, A51 aFRR,
A52 FCR, A56 FRR, A60 Scheduled activation mFRR, A61 Direct activation
mFRR, A67 Central Selection aFRR, A68 Local Selection aFRR.

`DocStatus`: A01 Intermediate, A02 Final, A05 Active, A09 Cancelled,
A13 Withdrawn, X01 Estimated.

`PsrType`: A03 Mixed, A04 Generation, A05 Load; B01 Biomass,
B02 Fossil Brown coal/Lignite, B03 Fossil Coal-derived gas, B04 Fossil
Gas, B05 Fossil Hard coal, B06 Fossil Oil, B07 Fossil Oil shale,
B08 Fossil Peat, B09 Geothermal, B10 Hydro Pumped Storage, B11 Hydro
Run-of-river and poundage, B12 Hydro Water Reservoir, B13 Marine,
B14 Nuclear, B15 Other renewable, B16 Solar, B17 Waste, B18 Wind
Offshore, B19 Wind Onshore, B20 Other, B21 AC Link, B22 DC Link,
B23 Substation, B24 Transformer, B25 Energy storage.

`DocumentType` (the key ones for load/price/generation work):
**A65 System total load**, **A44 Price Document**, A75 Actual generation
per type, A73 Actual generation, A74 Wind and solar generation,
A69 Wind and solar forecast, A71 Generation forecast, A68 Installed
generation per type, A70 Load forecast margin, A72 Reservoir filling,
A61 Estimated Net Transfer Capacity, A63 Redispatch notice,
A76 Load unavailability, A77 Production unavailability,
A78 Transmission unavailability, A79 Offshore grid unavailability,
A80 Generation unavailability, A81 Contracted reserves,
A82 Accepted offers, A83 Activated balancing quantities,
A84 Activated balancing prices, A85 Imbalance prices,
A86 Imbalance volume, A87 Financial situation, A88 Cross border
balancing, A89 Contracted reserve prices, A90 Interconnection network
expansion, A91 Counter trade notice, A92 Congestion costs,
A93 DC link capacity, A94 Non EU allocations, A95 Configuration,
A09 Finalized schedule, A11 Aggregated energy data report,
A15 Acquiring system operator reserve schedule, A24 Bid document,
A25 Allocation result document, A26 Capacity document, A31 Agreed
capacity, A37 Reserve bid document, A38 Reserve allocation result,
B11 Flow-based allocations, B17 Aggregated netted external TSO schedule,
B45 Bid Availability Document.

`BusinessType` (selection): A01 Production, A04 Consumption, A19 Balance
energy deviation, A25 General Capacity Information, A29 Already allocated
capacity, A37 Installed generation, A43 Requested capacity, A46 System
Operator re-dispatching, **A53 Planned maintenance**, **A54 Unplanned
outage**, A60 Minimum possible, A61 Maximum possible, A85 Internal
re-dispatch, A91/A92 Positive/Negative forecast margin, A93 Wind
generation, A94 Solar generation, A95 FCR, A96 aFRR, A97 mFRR, A98 RR,
B01/B02 Interconnector evolution/dismantling, B03 Counter trade,
B04 Congestion costs, B05 Capacity allocated, B07 Auction revenue,
B08 Total nominated capacity, B09 Net position, B10 Congestion income,
B11 Production unit, B33 Area Control Error, B74 Offer, B75 Need,
B95 Procured capacity, C22 Shared Balancing Reserve Capacity, C23 Share
of reserve capacity, C24 Actual reserve capacity, C76 Forecasted
capacity, C77 Min, C78 Average, C79 Max.

Small lists: `flowDirection.direction` A01 Up / A02 Down / A03 Symmetric.
`Standard_MarketProduct` = `Original_MarketProduct`: A01 Standard,
A02 Specific, A03 Integrated process, A04 Local, A05 Standard mFRR DA,
A07 Standard mFRR SA+DA. `Imbalance_Price.category`: A04 Excess balance,
A05 Insufficient balance, A06 Average bid price, A07 Single marginal bid
price, A08 Cross border marginal price. `PriceDescriptor.type`:
A01 Scarcity, A02 Incentive, A03 Financial neutrality.
`financial_Price.direction`: A01 Expenditure, A02 Income.

## Areas and EIC codes

Every domain parameter takes a 16-character **EIC** code, and one EIC can
carry several *area type* roles simultaneously. Area types: **BZN**
Bidding Zone, **BZA** Bidding Zone Aggregation, **CTA** Control Area,
**MBA** Market Balance Area, **IBA** Imbalance Area, **IPA** Imbalance
Price Area, **LFA** Load Frequency Control Area, **LFB** Load Frequency
Control Block, **REG** Region, **SCA** Scheduling Area, **SNA**
Synchronous Area.

The parameter names encode which type is expected — `OutBiddingZone_Domain`
and `BiddingZone_Domain` take BZN, `ControlArea_Domain` takes CTA,
`In_Domain`/`Out_Domain` take BCA/BBZ, `Acquiring_Domain`/
`Connecting_Domain` take LFA/SCA. **Passing the right EIC with the wrong
role is a likely source of empty responses.**

Full list: [Area List with
EIC](https://transparencyplatform.zendesk.com/hc/en-us/articles/15885757676308)
(upd. 2024-03-13 — the oldest of the core articles; verify before
trusting). Frequently used: `10YCZ-CEPS-----N` CZ, `10Y1001A1001A82H`
DE-LU, `10YFR-RTE------C` FR, `10YNL----------L` NL,
`10YGB----------A` GB, `10YES-REE------0` ES, `10YIT-GRTN-----B` IT,
`10YBE----------2` BE, `10YPL-AREA-----S` PL, `10YAT-APG------L` AT,
`10YDK-1--------W` DK1, `10YDK-2--------M` DK2, `10YSE-1--------K` SE,
`10YNO-0--------C` NO, `10YFI-1--------U` FI, `10YIE-1001A00010` IE.
Italy and the Nordics are heavily zonal (IT-North, IT-Sicily, …;
SE1–SE4, NO1–NO5). Germany also exposes four TSO control areas
(`10YDE-ENBW-----N` TransnetBW, `10YDE-EON------1` TenneT GER,
`10YDE-RWENET---I` Amprion, `10YDE-VE-------2` 50Hertz).

---

# 2. File Library (FMS) — the bulk route

Separate service, separate credentials, separate quota. This is the
documented answer for large volumes: *"Large data amounts can be
retrieved by using the Transparency Platform File Library."*

**Endpoints**

- FMS PROD: `https://fms.tp.entsoe.eu/` · IOP: `https://fms.tp-iop.entsoe.eu/`
- Keycloak PROD: `https://keycloak.tp.entsoe.eu/realms/tp/protocol/openid-connect/token`
- Methods (all POST, JSON): `/listFileMetadata`, `/listFolder`,
  `/downloadFileContent`

**Auth — not the API token.** OAuth2 password grant against Keycloak with
`client_id=tp-fms-public`, `grant_type=password`, and your **Transparency
Platform email + password**. Returns a bearer token with
`expires_in: 900` (15 min) and `refresh_expires_in: 1800` (30 min).

> Two consequences worth flagging. (a) FMS needs the account *password*
> in the client, not a revocable API token — a different secret-handling
> problem from every other source in this project. (b) **The TP password
> expires every 183 days**, and expiry forces an interactive change at
> next login, which will silently break an automated FMS pull. Note that
> `.env` currently holds only `ENTSOE_API_KEY`; FMS would need credentials
> that are not yet stored.

**Rate limit — 100 requests per minute per user login**, counted
separately from the Web API. Breaching it gives a **10-minute temporary
ban** and HTTP 429 with *"Max allowed requests per minute (100)
exceeded."*

**Volume limit — none stated.** Verbatim: *"there is no limitation on the
download. However, please ensure fair use of the channel as it is a
shared resource for all of our users."* Downloading by file ID fetches
**up to 100 files in one request**, which combined with the 100 req/min
ceiling is a very high effective throughput compared with the REST API.

**Format.** Tab-delimited flat files with a `.csv` extension, UTF-8.
Naming `YYYY_MM_DD_DataItemName_DataItemNo.csv` (e.g.
`2018_08_ActualTotalLoad_6.1.A.csv`); full extracts carry no date
element. Extracts are daily, monthly, yearly or "all" depending on the
item — most of the load/price/generation set is **monthly**. Requests may
ask for ZIP or original format.

**Freshness.** Regenerated **every 60 minutes except the 00:00 and 01:00
CET/CEST slots**, and only for files whose data changed. An inventory of
last-generation times lives at **`/TP_export/Export_log_r3.csv`** — use
it rather than polling modified timestamps.

**Layout.** Active items under `TP_export/`, one folder per data item
(e.g. `ActualTotalLoad_6.1.A_r3/`). Legacy under
`TP_Legacy_Publications/`, including R1 archives (pre-2015-01-05) and R2
items discontinued 2025-12-11. Pre-2015 entsoe.net data (2011→2015-01-05)
is available there as XLSX/XML.

**Error codes:** 400 invalid input / file-or-folder not found,
403 not authorized for that `topLevelFolder`, 500 retrieval failed.

**Access requires login** — the File Library is not anonymous.

## ⚠ Deprecation deadline: r3 → r3.1, **removal 2026-10-01**

The [File Library
Guide](https://transparencyplatform.zendesk.com/hc/en-us/articles/35960137882129)
(upd. 2026-08-05) marks a large fraction of extracts
**`[REMOVED on 01/10/2026]`**, with `r3.1`/`r3.2` replacements already
live (dated 27/05, 30/06, 06/07, 22/07, 04/08 2026). That is **~7 weeks
from this extraction**. Affected items include Energy Prices 12.1.D,
Implicit Allocations Net Positions 12.1.E, Commercial Schedules 12.1.F,
Forecasted Transfer Capacities 11.1, Offered Transfer Capacities
(all variants), Redispatching 13.1.A, Countertrading 13.1.B,
Imbalance Prices 17.1.G, Total Imbalance Volumes 17.1.H,
Installed Capacity per Production Unit 14.1.B, Production and Generation
Units, Transmission Assets, three of the outage extracts
(`UnavailabilityInTheTransmissionGrid_10.1.A_B`,
`UnavailabilityOfOffshoreGrid_10.1.C`,
`UnavailabilityOfProductionAndGenerationUnits_15.1.A_B_C_D`) plus
Fall-backs, and much of balancing. Not every extract is affected — the
`…AffectedAreas` / `…AffectedAssets` variants and
`UnavailabilityOfConsumptionUnits_7.1.A_B_r3` carry no removal marker.
**Any FMS pull must check the guide's per-extract marker and target the
`r3.1`/`r3.2` folder names.**

Two extracts are daily-with-a-window: `BalancingEnergyBids_12.3.B_C_r3.1`
covers **only the past 93 days**, with older data in
`BalancingEnergyBidsArchives_12.3.B_C_r3` as ZIP(XML). Same split for
`ChangesToBidAvailability…`.

Some items are **PDF only** — Ramping Restrictions 11.3, Yearly Report
11.4, Algorithm 12.3.K, Approved Methodologies 12.3.J, Terms and
Conditions 12.3.G, Imbalance Netting 186.2, Operational Agreements
184.2/184.3, Expansion and Dismantling report 9.1.

**SFTP is dead** — decommissioned 2025-11-20; File Library is the
replacement.

---

# 3. Subscriptions and web services (not needed for a historical pull)

Push-based. Requires emailing `transparency@entsoe.eu` with subject
*"Data Consumer subscription rights request"*, then configuring an ECP or
web-service channel that **you** host. **SOAP 1.2, not 1.1.** TLS 1.2/1.3
only. Subscribers must return an IEC 62325-504
`Acknowledgement_MarketDocument`; a channel is disabled after ~100 failed
attempts, and data for an inactive channel is held **2 days** before
archiving. Subscription scope is one of "Only Filtered Data" (default),
"All {Area type} Data", or "All Data".

Web-service submission (`ws-submission.tp.entsoe.eu`) is primarily a
data-*provider* channel: client-certificate auth, machine users, digital
signatures on PUT/GET/QueryData. Messages listable for **30 days** only;
acknowledgements held **30 days**. Pull strategy is discontinued —
push only. Note the platform caps XML processing at **10,000 positions**
per document.

Both channels are heavier to stand up than REST or FMS and neither is
needed for a historical extract.

---

# 4. Licensing and account hygiene

- **Open Data list, CC-BY 4.0.** Since 2022-02-18 the published "list of
  data open for free re-use" carries a Creative Commons Attribution 4.0
  International licence, with no need for prior agreement from the
  Primary Owner of Data. Georgia (GE) was removed from the exceptions
  2023-10-18. Data items under EB GL and SO GL were added 2020-10-30;
  12.1.f, 12.1.h, North Macedonia, Ukraine and BritNed 2019-10-28.
  **The list itself is a separate document and was not retrieved** —
  confirm the specific items before publishing derived figures.
- Use is subject to the Terms of Use (current version 2023-03-29,
  applicable from 2023-11-01).
- **Accounts inactive for one year may be deleted** — same trap noted for
  UKPN. If this thread goes dormant, the token may die with the account.
- The login email cannot be changed; a new address means re-registering.

---

# 5. Migration context (R2 → R3)

Data items were migrated item-by-item from 2023-11-24 through 2025-11-24
([announcement](https://transparencyplatform.zendesk.com/hc/en-us/articles/30195539966865),
upd. 2026-01-16). Consequences that survive into current data:

- Responses use **variable-sized blocks, curveType A03**.
- **Decimal values can now be returned** where integers were returned before.
- Old website data views remain visible but **are no longer updated**.
- Item-specific breaks worth knowing: Implicit Allocations Net Positions
  [12.1.E] was **re-migrated twice** (from 2024-05-06 and 2024-06-21);
  Commercial Schedules [12.1.F] re-migrated from 2025-02-10; Implicit
  Allocations Congestion Income [12.1.E] now always returns a border code
  where it previously sometimes returned area codes; Total Capacity
  Nominated [12.1.B] discontinued contract type "Total (legacy)";
  17.1.B&C switched its API response to ZIP; Balancing Energy Bids
  [12.3.B&C] had **only archives migrated**.

A **series that spans a migration date may change shape mid-series.**
Relevant dates for the load/price items this project would most likely
use: Energy Prices [12.1.D] 2024-10-04, Actual Total Load [6.1.A]
2025-11-10, Day-ahead Total Load Forecast [6.1.B] 2025-11-10, Aggregated
Generation per Type [16.1.B&C] 2025-10-23, Physical Flows [12.1.G]
2025-10-07, Imbalance Prices [17.1.G] 2025-10-14.

---

# 6. Named gaps — not extracted

- **Manual of Procedures (MoP)**, in particular **Ref2 DDD (Detailed Data
  Description)** and **Ref19 (Data Extraction Process)**. The [Reference
  Documentation](https://transparencyplatform.zendesk.com/hc/en-us/articles/12784099471764)
  article calls these *"highly recommended"* for data consumers and they
  define the response download scenarios. The link target is off-Zendesk
  and was not followed.
- **Implementation Guides + XSDs** — the normative response schemas.
- **The Open Data list itself** (which items are CC-BY 4.0).
- `https://gitlab.entsoe.eu/transparency/xml-examples` — public and
  reachable (HTTP 200), contents not enumerated.
- **Per-endpoint mandatory/optional parameter matrices** — extracted in
  full during this pass to the companion file
  **`entsoe-endpoint-reference.md`** (all 77 endpoints, `[M]` / `[O]`
  markers, worked example values, and each endpoint's own request/response
  limits).
- **Publication *depth and coverage* per area** — deliberately not
  claimed. Nothing in this documentation set establishes how far back any
  given area's series runs, and per-market depth claims in this project
  have been falsified twice before. Probe before asserting.
- **Whether the 400/min limit is enforced as claimed** — probe written,
  deliberately not armed (see the rate-limit section for the reasoning).
  `offset` and case-sensitivity **were** checked and are marked [PROBED].
- **Why 12.1.D ignores its documented 100-TimeSeries cap** while 13.1.A
  and 10.1.A&B enforce theirs. The server counts "instances", which may
  not map 1:1 to TimeSeries; ENERGY_PRICES may simply carry a much higher
  instance ceiling. The per-data-item ceilings are not published — the
  400 error is the only way to discover them, and it names the data item
  in server-internal form (`REDISPATCHING_INTERNAL_R3`,
  `UNAVAILABILITY_IN_TRANSMISSION_GRID`).
- **Per-endpoint cap behaviour beyond the three probed.** Three of 77
  were measured and produced three different behaviours, so assume
  nothing about the remaining 74. Probe before designing a pull.
