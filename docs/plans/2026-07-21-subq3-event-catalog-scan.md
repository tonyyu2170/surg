# Sub-Q3 Event Catalog Scan (2026-07-21)

> **Status:** Ungated reconnaissance, same category as
> `docs/plans/2026-07-20-jlarc-external-context-update.md`. Sub-q3
> plan-writing is gated until sub-q1 is paper-ready (advisor meeting,
> item #5, still pending) — see `CLAUDE.md`. This document is
> background data exploration + external cross-referencing only: it
> scans the existing hourly panel for candidate real-world-event days
> and checks a handful of the strongest candidates against outside
> reporting. It does not propose or lock a sub-q3 methodology.
>
> Confirmed scope with the user 2026-07-21 (AskUserQuestion): "ungated
> reconnaissance only," explicitly the event-catalog scan idea
> proposed earlier the same session, following the precedent already
> shipped for sub-q2 (design doc, napkin-math, external-context doc).
>
> **Extended same day, per explicit user instruction** ("go through
> all of them extensively and autonomously, dont worry about
> time/quota"): the original pass (§1-§3 below, two confirmed events)
> is superseded by a much wider day-level scan and exhaustive
> cross-referencing of every candidate it surfaced — see §3 (expanded)
> and §4 (renamed from "not yet examined" to "investigated, no
> corroboration found").

## 1. A ground-truth event signal already exists in the panel

`data/interim/analysis_panel.parquet` has `sync_reserve_event_active`
(bool) and `sync_reserve_event_id` — PJM's own record of when a
synchronized-reserve event was in effect. This wasn't built for this
project; it came along with whatever PJM feed populated the panel, and
nobody had looked at it as an event-correlation signal until now.

- **37 unique events, 39 event-hours, 2023-01-26 → 2026-03-05.**
- **Distinct from the 2024-07-10 NERC ride-through event already
  verified** (`docs/decisions.md`, 2026-07-21 entry): the 2024-07-10
  event does not appear in this flag at all — checked directly, no
  `sync_reserve_event_active=True` row within ±1 day of 2024-07-10.
  This makes sense mechanistically: synchronized-reserve events are
  PJM deploying reserves in response to a generation shortfall
  (typically a generator trip), while the verified 2024-07-10 event
  was a demand-side voltage ride-through disturbance (data centers
  tripping off, not a generator). Sub-q3's "outages, weather,
  generator trips" framing spans both categories, but they are
  genuinely different mechanisms and this panel column only
  covers one of them.
- **Cross-tab against the proposal filter** (shoulder season × 2-5am
  window): of the 39 event-hours, 15 fall in shoulder season, 4 fall
  in the 2-5am window, and only **2 pass both** (2025-04-05 04:00,
  2026-03-05 02:00). Neither of those two shows an extreme price or
  gradient signature (total_lmp $30-44, congestion near 0, gradient
  ~1.4 MW/min) — consistent with item #6's finding that the proposal
  filter's scope excludes the price extremes even when a real PJM
  event coincides with it.
- **Implication for eventual sub-q3 design (not decided here):** if
  the goal is correlating LMP behavior with real PJM-recorded events,
  the current 2-5am × shoulder-season filter overlaps with only ~5%
  of PJM's own recorded reserve-deployment events. A sub-q3
  methodology built strictly inside that filter would have very few
  real events to correlate against; one built on the full panel (or a
  widened window) would have much more to work with. This is exactly
  the kind of framing tradeoff the roadmap already flagged sub-q3
  needs to make — noted here so it isn't rediscovered from scratch
  later.

## 2. Naive top-N-by-gradient scan mostly finds a diurnal artifact, not events

Ranking all hours (excluding the two already-verified event dates) by
`dom_load_gradient_abs_mw_per_min` returns almost entirely **09:00
EPT** rows across many different dates (2026-01-21, 2024-01-22,
2026-02-09, 2025-01-24, 2024-02-05, 2023-03-21, 2025-01-25,
2024-02-20, 2024-02-01, 2022-12-02, 2025-12-16 all appear in the top
15, all at 09:00). None of these show elevated prices. This is the
ordinary morning load ramp, not a stress event — a reminder (already
implicit in why the project's filter uses 2-5am, away from ramp hours)
that raw-gradient ranking isn't a usable event-finding method on its
own; it needs to be paired with a price-based or PJM-event-based
signal to avoid just re-finding the daily ramp over and over.

**Confirmed rigorously** (extended pass): of the top 50 rows
panel-wide by `dom_load_gradient_abs_mw_per_min`, 31/50 fall at hour
09:00 EPT. Hour 9's gradient distribution is systematically shifted
above the panel overall (mean 8.59 vs. 6.40 MW/min; 95th-pct 21.2 vs.
16.0 MW/min) — a real, structural diurnal effect, not a coincidence of
which dates happened to rank highest. Gradient-based ranking is not a
usable event-finding signal without excluding or de-weighting the
ramp hours first.

The one gradient-scan hit that *isn't* the diurnal ramp is
**2022-12-23 17:00 EPT** (gradient 26.2 MW/min, total_lmp cluster mean
≈ $4,130) — see §3.

## 3. Externally-corroborated candidate events

**Expanded methodology.** The original top-15-by-hour congestion scan
was widened to a **day-level scan**: group by calendar date, take each
day's max `congestion_price_rt_cluster_max` / `total_lmp_rt_cluster_mean`
/ `dom_load_gradient_abs_mw_per_min`, exclude the (by now nine)
already-known event dates, and rank the top 30 days. This avoids the
original method's blind spot where one multi-hour event could occupy
several rows of a top-15 hourly list and crowd out separate events —
the day-level version surfaced several genuine new events the
hour-level pass missed entirely (2022-12-24, 2025-01-22/23,
2024-01-20, 2024-05-26). Every day in the resulting top-30 list was
then checked against external reporting.

Seven candidate events (some multi-day) came back with solid external
corroboration. The rest of the top-30 (§4) were searched with equal
effort and came back empty.

### 2022-12-23, ~17:00 EPT — Winter Storm Elliott

**Panel signature:** total_lmp_rt_cluster_mean ≈ $4,130 (mean across
the 7-pnode cluster, i.e. every node was pinned near/at the price
cap), congestion_price_rt_cluster_mean ≈ $357, gradient ≈ 26.2 MW/min.
By far the largest total_lmp value anywhere in the panel outside the
two already-known events.

**External corroboration — sourced via WebSearch (AI-synthesized
summary of multiple results, not a page I fetched and read directly
this session):** PJM's own after-action report and RTO Insider both
describe Dec 23, 2022 as a PJM-wide emergency event — ~46,000 MW of
forced generation outages (~25% of PJM's installed capacity, gas
units responsible for ~70% of it), PJM invoked multiple emergency
procedures and a public conservation appeal, and PJM's report
attributes prices in excess of the $3,700/MWh cap "primarily to the
impacts of congestion." This is Winter Storm Elliott, one of the
most extensively documented PJM emergency events in the RTO's
history — high confidence despite the sourcing tier being
search-summary rather than direct-fetch.

**Assessment:** strong match. A famous, well-documented systemic
emergency landing exactly on the panel's largest non-verified price
spike is about as clean a correlation as this kind of scan can
produce.

**Extension found in the day-level rescan: 2022-12-24 04:00 EPT.** The
day-level scan turned up total_lmp_rt_cluster_mean ≈ $4,125.52 at
2022-12-24 04:00 — nearly identical magnitude to the 12-23 peak, and
missed entirely by the original hour-level top-15 (which only had room
for one Elliott hour before other dates crowded it out). PJM's Elliott
after-action report covers emergency conditions through Dec 23-24;
this is the same storm's second day, not a separate event. Folding it
into the Elliott entry rather than treating it as new.

### 2025-01-22 (21:00) / 2025-01-23 (07:00) — PJM record winter peak, Arctic Outbreak

**Panel signature:** congestion_price_rt_cluster_max $385.81
(2025-01-22 21:00) and $449.12 (2025-01-23 07:00); total_lmp cluster
mean up to $824.92 (01-23 07:00). Two separate peak hours a day apart,
not a single spike — consistent with a multi-day cold event rather
than a discrete short-lived incident.

**External corroboration — WebSearch summary of PJM Inside Lines and
RTO Insider coverage, not directly fetched:** PJM set a new all-time
hourly winter demand record of ~143,714 MW between 8-9am on Jan 22,
2025, surpassing the prior record (~143,700 MW, Feb 2015). This
capped an "Arctic Outbreak" that began Jan 18, 2025 with sustained
sub-zero wind chills across the western part of PJM's footprint. PJM
maintained reliability (and kept exporting ~8,000 MW to neighboring
grids) throughout.

**Note on the "previous record" this event set:** this is the same
143,700 MW figure the January 2026 cold wave (below) was benchmarked
against and slightly exceeded — i.e. this project's panel now directly
covers *both* of PJM's two most recent winter-peak record-setting
events, back to back in consecutive years.

**Assessment:** strong match — a specifically-named, precisely-dated
PJM operational record with a two-peak signature in the panel that
matches a two-day cold event, not a single-hour coincidence.

### 2024-01-20, 17:00 EPT — PJM Cold Weather Alert (second January 2024 wave)

**Panel signature:** congestion_price_rt_cluster_max $324.11, total_lmp
cluster mean $681.28, gradient 20.0 MW/min.

**External corroboration — WebSearch summary, not directly fetched:**
January 2024 saw two distinct PJM cold weather alerts: a polar-vortex-
driven alert Jan 14-17, and a second "Cold Weather Alert Issued for
Jan. 20-22" (PJM Inside Lines article title). The panel's spike lands
inside the second window, not the first.

**Assessment:** moderate-strong match. The alert window (Jan 20-22) is
a 3-day window rather than a pinned hour, so this is closer to "the
spike happened during a documented alert period" than "the spike
matches a documented peak hour" — still a real correlation, just a
looser one than the Jan 2025/2026 record-peak matches.

### 2024-05-26, 15:00 EPT — May 25-27, 2024 severe weather / tornado outbreak

**Panel signature:** congestion_price_rt_cluster_max $526.16, total_lmp
cluster mean $562.85, gradient 4.2 MW/min (a price-driven event, not a
load-gradient-driven one — the only confirmed event in this catalog
where the panel's price signature isn't accompanied by an elevated
gradient).

**External corroboration — WebSearch summary referencing NOAA/NWS
reporting, not directly fetched:** May 26, 2024 saw 60 unique severe
weather reports (mostly damaging winds) across the Mid-Atlantic — the
most in a single day since June 21, 2011 — including an EF1 tornado in
Salem, VA. This was part of a broader multi-state severe weather
outbreak spanning May 25-27, 2024 (also documented on Wikipedia as
"Tornado outbreak of May 25-27, 2024"), with the initial storm line
moving through West Virginia, Virginia, and North Carolina.

**Assessment:** moderate match. Severe convective weather damaging
transmission/distribution infrastructure is mechanistically the kind
of "incident" sub-q3 is asking about (parallel to 2024-07-10's
lightning-strike-on-arrestor mechanism), but this wasn't confirmed to
be *specifically* a Dominion-zone transmission event the way Elliott
and the winter-peak events were — the outbreak was regional and VA-wide,
not confirmed as landing directly on PJM's monitored transmission
elements in Data Center Alley specifically.

### 2026-01-24 → 2026-02-09 (multi-week) — January-February 2026 North American cold wave

**Panel signature:** an extended cluster of elevated-congestion days
across the day-level top-30: 2026-01-24 ($349.37), 01-25 ($813.82),
01-26 ($502.56), 01-27 ($857.02), 01-28 ($629.49), 01-29 ($312.63),
02-02 ($398.89), 02-09 ($586.16) — in addition to the already-confirmed
01-31/02-01 multi-hour spike. This is not a single event but a
multi-week elevated-congestion regime.

**External corroboration — mixed tiers, see below:** this is the same
"January 2026 extreme cold event" already documented below as a
separate subsection for the 01-31/02-01 peak; the wider dates confirm
it wasn't an isolated spike but the tail ends of a longer cold wave.
Per Wikipedia (fetched directly): the **"January-February 2026 North
American cold wave"** ran **January 17 - February 11, 2026**, with a
"reinforcing winter storm" January 23-27, 2026 — which lines up almost
exactly with the 01-24 through 01-29 cluster above. PJM's own Cold
Weather Alert (RTO-wide, effective Jan 24-27) and Cold Weather Advisory
(effective Jan 24-30) — confirmed via WebSearch summary of PJM Inside
Lines coverage — match the same window. A DOE §202(c) order was issued
Jan 25 in response to PJM's Jan 24 application, and PJM activated
Demand Response in the Mid-Atlantic on Jan 25.

One naming note: several independent sources (an American Public Power
Association article title, and the WebFetch synthesis of a PJM Inside
Lines article) refer to this event in passing as **"Winter Storm
Fern"** — but the Wikipedia article on the cold wave itself does not
use that name, describing it only by the generic "January-February
2026 North American cold wave" title. Both likely refer to the same
underlying weather system (Weather Channel-style storm names and
NWS/meteorological cold-wave framing often coexist for the same event,
as with "Winter Storm Elliott" above), but this wasn't independently
confirmed by finding both names in a single authoritative source —
treat "Fern" as probable, not certain.

**Assessment:** strong match, and the widest/longest-duration
confirmed event in this catalog — effectively the panel shows
elevated congestion for most of a 3-week window that maps onto a
single named cold wave with multiple PJM emergency actions, capped by
the already-documented data-center backup-generation order.

### 2026-01-31 (evening) → 2026-02-01 (early morning) — DOE data-center backup-generation order (peak of the cold wave above)

**Panel signature:** a multi-hour congestion spike, 2026-01-31 18:00
through 22:00 EPT (congestion_price_rt_cluster_mean ranging ~$700-975,
total_lmp up to ~$2,035), continuing into 2026-02-01 02:00-06:00
(~$830-945 congestion). Several of the 2026-01-31 evening hours
(18:00, 19:00, 20:00, 21:00) carry `sync_reserve_event_active=True` —
i.e. this is one of the 37 PJM-recorded events from §1, not just a
price anomaly. The 2026-02-01 early-morning hours do *not* carry the
flag on those specific hours, so treat that continuation as
price-correlated-but-not-independently-flagged.

**External corroboration — sourced via WebFetch of the primary PJM
Inside Lines article directly (higher-confidence tier than a search
summary, though the fetch tool itself summarizes long pages through a
smaller model rather than returning raw text):**
[PJM Reviews January Cold Weather Operations](https://insidelines.pjm.com/pjm-reviews-january-cold-weather-operations/)
confirms hourly winter peak loads of 130 GW+ for eight consecutive
days, Jan 26 - Feb 2, 2026 — "two of the top 10 hourly winter peaks in
PJM history." Generator outages averaged 18-19 GW over the period.
PJM obtained two separate DOE emergency orders under Federal Power Act
§202(c): one authorizing 15 generators to run outside normal
environmental permits (1,035 total run-hours, 5.2 GW), and — the
directly relevant one for this project — **a second order permitting
PJM to direct data centers and other large loads onto their own
backup generation "if needed in an emergency,"** effective through
February 2, 2026. A companion PDF notice
([pjm-notice-re-behind-the-meter-emergency-procedure.pdf](https://www.pjm.com/-/media/DotCom/committees-groups/committees/oc/postings/pjm-notice-re-behind-the-meter-emergency-procedure.pdf))
exists but did not extract cleanly (compressed PDF text streams);
it corroborates that data centers are named in the procedure but
didn't yield extractable MW figures or activation thresholds beyond
what the Inside Lines article already gave.

One caveat on a specific detail: the WebFetch synthesis referred to
this event in passing as "Winter Storm Fern." That name was not seen
directly in quoted text, only in the fetch tool's own summarization —
treat the storm name as unconfirmed; the dates, MW figures, and DOE
order details above came from the same fetch and are better-supported
since they're specific figures rather than a name.

**Assessment:** the strongest possible kind of hit for this project's
actual research question — not just "a grid event happened," but "PJM
formally invoked data centers as part of the emergency-response
mechanism during the same event this panel shows a real-time price
spike for." Worth flagging to the advisor as a concrete illustration
candidate, separate from whatever the eventual sub-q3 methodology
looks like.

## 4. Investigated, no external corroboration found

Every one of these was searched with the same effort as the confirmed
events above — general PJM/NERC alert search, weather/storm-database
search (including NOAA NCEI's Storm Events Database by name), and
Dominion/Virginia-specific news search, often 2-3 query angles each.
None returned anything connecting the date to a documented incident.
Listed with their day-level peak values for reference:

- **2025-05-01 to 05-03** (congestion up to $1,020.29 on 05-02 —
  the single largest unexplained congestion value in the entire
  panel outside the confirmed events). Checked general event search,
  PJM transmission-outage search (Ashburn/Pleasant View specifically),
  PJM Market Monitor / State-of-the-Market search, and Dominion-
  specific news search. The closest anything came was a structural
  fact, not an incident: PJM's 2025 Market Monitor reports the
  Dominion zone had the *highest real-time congestion component of
  any zone* for the first nine months of 2025 ($13.09/MWh average).
  That supports a "chronically congested zone" reading rather than a
  discrete incident on these specific days — see assessment below.
- **2024-05-08, 05-18, 05-22** (congestion $421-808; note 2024-05-26,
  four days after 05-22, *is* confirmed above as part of the tornado
  outbreak — these three siblings are not, despite being close in
  time and in the same general severe-weather-season pattern).
- **2023-10-26** (congestion $574.42).
- **2023-11-29** (congestion $348.17).
- **2025-04-14** (congestion $549.87).
- **2025-11-18** (congestion $661.05).
- **2025-12-15** (congestion $338.01).
- **2026-04-04, 04-15, 04-16** (congestion $327-377).

**Assessment of this whole group.** The absence of a documented
external incident doesn't mean nothing happened — it more likely means
these are routine transmission congestion events in a zone that is
*structurally* congested (per the Market Monitor stat above), not
individually newsworthy or NERC-reportable. This is itself a relevant
finding for sub-q3: the panel's congestion spikes split into at least
two populations — a minority tied to documented, externally-verifiable
incidents (storms, cold-wave records, generator-shortfall reserve
events), and a majority that aren't discretely explainable and are
more consistent with ordinary (if elevated) market congestion
dynamics. A sub-q3 methodology that assumes every price spike has a
findable external cause would be checking the wrong premise.

## What this does and doesn't establish

This scan shows the panel + open web can jointly reproduce plausible
event correlations, and surfaces a real analytical resource
(`sync_reserve_event_active`) nobody had used yet. Across the full
day-level top-30 (excluding the two pre-existing verified events),
**7 of ~17 distinct candidate dates/clusters** came back with solid
external corroboration (Elliott + its Dec-24 extension, the Jan 2025
winter-peak record, the Jan 2024 cold alert, the May 2024 tornado
outbreak, and the multi-week Jan-Feb 2026 cold wave culminating in the
DOE data-center order) — the rest did not, despite equally thorough
search effort. That roughly 40-45% hit rate is itself informative: a
sub-q3 methodology should expect a substantial share of statistically
extreme congestion days to have no findable external correlate, not
treat non-confirmation as a search failure.

This does **not** decide sub-q3's methodology — how broad the
correlation window should be, what counts as a "hit," how to handle
the ride-through vs. sync-reserve event-category split found in §1,
or how to treat the "no external cause found" majority. Those are
framing decisions for when sub-q3 plan-writing actually unlocks.
