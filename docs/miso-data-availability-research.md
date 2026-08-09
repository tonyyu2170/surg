# MISO as a Comparison Market: Data Availability Research

**Date:** 2026-08-09
**Motivation:** First of six cross-ISO memos per
`docs/superpowers/specs/2026-08-09-cross-iso-data-research-design.md` — extend the DOM + ERCOT
level-vs-volatility result and hunt for data-center visibility, market by market.
**Status:** Research memo. Feeds the Phase-1 checkpoint; no scope decision made here.
**Verification:** Every schema and history-depth claim below was verified by downloading and
reading real files on 2026-08-09 unless flagged ⚠️.

---

## 1. Headline

**MISO cannot see individual data centers any better than PJM or ERCOT — the facility-level
negative is national (CRS R48646) and MISO adds no exception — but it is the best *aggregate*
data environment of the three: free hourly zonal load back to mid-2013, and free hourly *and
5-minute* LMPs with congestion and loss pre-decomposed, all ungated, no key, no quota.**

Two MISO-specific finds stand out:

1. **A pricing node named for a data center.** The CPNode roster contains `GRE.REC.DATA`
   (type Loadzone) — by naming, the data-center load at Rainbow Energy Center, the former
   Coal Creek Station in Underwood, ND (Great River Energy LBA). A North Dakota legislative
   presentation describes the site as "mine, plant, and data center in one place." This is a
   *price* series at a data-center bus, not load telemetry — but it is more locational
   visibility than either PJM or ERCOT price rosters offered, and it makes a
   Loudoun-style locational congestion contrast possible inside MISO. ⚠️ The facility
   interpretation is a naming inference; no MISO document maps the CPNode to the facility.
2. **MISO's own forecast corroborates the flat-profile premise.** The 2026 Long-Term Load
   Forecast projects data centers lifting system load factor from ~63% to ~68% — the system
   gets *tighter without getting peakier*. MISO's forecasting arm, independently, describes
   data-center growth as a load-**level** phenomenon, not a volatility phenomenon. That is
   the DOM/ERCOT finding, stated prospectively by the RTO itself.

## 2. Facility-level / data-center-specific data hunt

**No public facility-level load telemetry exists in MISO.** Checked empirically and
structurally:

- MISO's market-report catalog has **no analog of ERCOT's 60-Day SCED Load Resource file**
  (which at least exposed named DR-registered loads at 5-minute resolution). MISO demand
  response participates as **Load Modifying Resources (LMRs)** registered by load-serving
  entities; public artifacts (LMR whitepaper, FAQ, accreditation reform docs) are
  LSE-level MW capabilities and aggregate totals, never facility traces.
- **Name-heuristic scan of the full pricing-node roster** (2,612 CPNodes in the 2026-08-06
  DA file, mirroring the ERCOT §1 methodology): exactly **one** hit for
  data/crypto/hyperscaler patterns — `GRE.REC.DATA` above. The 437 Loadzone-type nodes are
  otherwise LSE aggregates (`ALTW.CMMPA.MTL`-style), invisible at facility level.
- **The real facility-data channel is state PUC dockets.** Facility-scale MW show up in
  rate cases and CPCN filings — e.g., Indiana URC docket CN 46097 (data-center exhibits,
  partly redacted) and the Entergy Louisiana filings for the Meta Richland Parish
  generation build. Docket mining is possible but is per-utility archaeology, not a dataset.
- National context (shared source packet, CRS R48646): EIA's two collection attempts
  failed (9 of 50 responses in the 2021 pilot; the 2024 crypto survey killed by TRO with
  data destroyed); the Clean Cloud Act is pending. Private proxies: Cushman & Wakefield,
  Baxtel; **EEI's "Large Load Projects and Tariffs" compilation (July 2026)** tracks
  announced projects and tariffs across utilities including MISO members.

**Verdict:** the decisive negative from ERCOT/PJM holds in MISO. What MISO offers instead:
one named DC pricing node, utility announcements with hard MW (see §7), and dockets.

## 3. What MISO does better / worse than PJM + ERCOT

**Better:**

- **Congestion is a free column, at every node, in every product.** Hourly DA and RT files
  carry `LMP / MCC / MLC` rows per node (verified); 5-minute files carry
  `LMP / MEC / MLC / MCC` columns (verified). PJM-grade decomposition without PJM's
  acquisition problem, and no ERCOT-style lossless-SCED derivation dependency.
- **5-minute *final* real-time LMPs are free and deep.** Weekly `5MIN_LMP.zip` archives
  (with price corrections) run Jan 2023 → present, ungated (verified probes). The PJM
  equivalent required the gridstatus.io quota workaround and six accounts.
- **No gates anywhere touched in this research**: no API key, no registration, no quota on
  `docs.misoenergy.org`, `cdn.misoenergy.org`, or `public-api.misoenergy.org`.
- **Fixed-EST timestamps** (files state "All Hours-Ending are Eastern Standard Time");
  FERC-approved EST market operation means no DST duplicate/missing-hour handling at parse
  time — the cleanest hour-labeling regime of any market in this project.

**Worse:**

- **Zonal load granularity is coarse: six zone-groups + total** (LRZ1, LRZ2_7, LRZ3_5,
  LRZ4, LRZ6, LRZ8_9_10, MISO). ERCOT gives 8 weather zones; PJM gives zones and below.
  The groups do cover the DC-relevant geographies separately (LRZ4 = IL, LRZ6 = IN/KY,
  LRZ8_9_10 = MISO South/Louisiana), but Wisconsin+Michigan and Iowa+Missouri arrive
  pre-mixed.
- **No public large-load interconnection queue.** ERCOT publishes a monthly large-load
  status funnel by zone; MISO's large-load requests surface only through utility
  announcements, the aggregate Long-Term Load Forecast, and a Large Load Working Group
  (see §7). A load-side growth funnel cannot be assembled from MISO publications today.
- **Legacy file plumbing.** Load files are `.xls` (needs `xlrd`), 5-minute daily files are
  `.xlsx` (needs `openpyxl`); ⚠️ **neither engine is installed in the main-checkout venv**
  (the ERCOT scripts ran from the worktree venv — the main venv cannot run them today
  either). Both engines are Phase-2 prerequisites, the ERCOT-openpyxl lesson repeated.

## 4. Zonal load archive (verified)

**Series: hourly forecast (MTLF) + actual load by Local Resource Zone group,
2013-06-01 → present, in two format eras plus a boundary quirk.**

| Era | Source | Format | Coverage |
|---|---|---|---|
| Archive | `https://docs.misoenergy.org/marketreports/{YYYY}12_dfal_HIST_xls.zip` | one cumulative `.xls` per year, **long** (`MarketDay, HourEnding, LoadResource Zone, MTLF (MWh), ActualLoad (MWh)`) | 2013 (from Jun 1) → 2022; `201212_dfal_HIST` 404s (a 2012 zip exists only for the regional rfal variant) |
| Daily | `https://docs.misoenergy.org/marketreports/{YYYYMMDD}_df_al.xls` | **wide** (16 cols: `Market Day, HourEnding`, then MTLF/Actual pairs per group + MISO) | 2023-01-01 → present (verified: 20230101 = 200, 20221231 = 404 — retention is current + 3 calendar years) |

Verified parsing facts:

- Daily files carry a 7-day reporting window but **only day 1 has actuals** (rest is
  forecast) → a backfill is one file per market day (~1,315 files, ~44 KB each).
- The wide schema is **identical at both ends of the daily window** (2023-01 vs 2026-08
  headers compared).
- **Zone-label change:** the 2013 archive uses `LRZ8_9` — the label later becomes
  `LRZ8_9_10`. Parsers must normalize. ⚠️ Which year the label flips is unverified;
  check each archive year during the pull.
- **MISO South enters the data exactly 2013-12-19** (first `LRZ8_9` rows; 312 rows in
  2013) — the footprint change is *inside* the load window and observable to the day.
- Archive files contain **repeated interior header rows** ("LoadResource Zone" appears as
  a data value) — drop-rule needed, the MISO cousin of ERCOT's republished-May-2026 block.
- Hour convention: `HourEnding` 1–24 in **fixed EST** (no DST rows; 24 hours every day).
  DOM comparisons must convert explicitly (EST → EPT is +0/+1 by season, asserted — the
  reverse of the naive-join trap logged for ERCOT).
- Archives are **regenerated** (the 2013 zip's member is file-dated 2022) — treat as
  as-reported-latest, not point-in-time.

Fallbacks / extensions, both verified reachable: regional (`rf_al`, North/Central/South)
daily files exist with an archive at least back to `201212_rfal_HIST_xls.zip`; EIA-930
gives MISO **BA-total** hourly demand 2015 → present as an ungated cross-check
(`EIA930_BALANCE_2023_Jan_Jun.csv` HEAD = 200). Real-time-only JSON exists at
`public-api.misoenergy.org` (`RealTimeTotalLoad`) — no history, not needed.

## 5. Price archive (verified)

**Hourly, daily files, 2023-01-01 → present (same retention rule as load):**

- `{YYYYMMDD}_da_expost_lmp.csv` — DA ex-post, wide (`Node, Type, Value, HE 1..24`),
  3 rows per node (`LMP`, `MCC`, `MLC`), 2,612 nodes: 1,715 Gennode, 437 Loadzone,
  414 Hub-type, 46 Interface. Named hubs: `ARKANSAS.HUB, ILLINOIS.HUB, INDIANA.HUB,
  LOUISIANA.HUB, MICHIGAN.HUB, MINN.HUB, MS.HUB, TEXAS.HUB` (8, verified).
- `{YYYYMMDD}_rt_lmp_final.csv` — RT ex-post hourly, same schema; **final lags ~4–5 days**
  (prelim exists in between; use final). `da_exante_lmp.csv` also exists (not needed).

**5-minute:**

- Daily `{YYYYMMDD}_5min_exante_lmp.xlsx` — long format
  (`Time (EST), CP Node, RT Ex-Ante LMP, MEC, MLC, MCC`), 2023 → present (verified at
  2023-02-06). Ex-ante = indicative.
- Weekly `{YYYYMMDD}_5MIN_LMP.zip` — RT **final** 5-min with corrections; URL date = the
  covered week's Monday **+ 2 weeks** (a 2026-08-04 Tuesday probe 404s; Mondays 200).
  Coverage 2023-01-02 → present (2022 Mondays 404). This is the free MISO counterpart of
  the PJM 5-minute panel this project paid quota for.

**Pre-2023 history exists but is bundled differently:** the market-reports page's
"Archives" tab (client-rendered; enumerated via a JS-rendered scrape) exposes cumulative
CSV bundles on `cdn.misoenergy.org` — e.g. `RT_LMP_HOURLY631315.zip` (a Sep–Oct 2023
chunk, wide CSV with `LMP/MCC/MLC` rows), `RT LMP Hourly771348.csv` (rolling recent, long
schema `PNODENAME, MKTHOUR_EST, LMP, CONGESTIONLMP, LOSSLMP, PRICINGTYPE, ENERGYLMP`),
`Post_RTHOURLY_LMP620988.zip` (25 MB, older era), plus reserve-zone MCP bundles
(ancillary prices — not needed). ⚠️ **Chunk inventory and full era coverage are not yet
enumerated** — the listing is paginated; enumeration is a Phase-2 mechanical task, not a
feasibility risk. LMP history nominally reaches the 2005 market start.
(Side note for the record: the site's `/api/find/...` endpoint is a tracking *write*
endpoint, not a query API — do not POST to it; the paginated page scrape is the listing
route.)

**Window fit:** daily hourly files miss Oct–Dec 2022 of the DOM-matched window
(2022-10-02 →). Options: run the horse race on 2023-01-01 → (≈3.6 yr, comparable to
DOM's 3.7), or recover Q4-2022 from the archive bundles. Recommended: the former, with
the latter as a stretch goal.

## 6. Market-specific confounds

- **Footprint change inside the load window.** MISO South (Entergy: AR/LA/MS/E-TX) joined
  2013-12-19 — verified in-data. MISO-total level trends must start 2014-01-01 (or split
  at the join); zone-group series are unaffected except `LRZ8_9(_10)` starting then.
- **Wind (the FWEST analog).** MISO carries a double-digit wind energy share concentrated
  in LRZ1 and LRZ3_5 (MN/IA/Dakotas); wind-export congestion and negative LMPs
  around `MINN.HUB` are generation-driven, not load-driven. Any LRZ1 congestion-on-load
  regression inherits the exact caution logged for ERCOT's West zones. ⚠️ share figure to
  be pinned from MISO's Historical Generation Fuel Mix report during Phase 2.
- **Storm events.** Winter Storm Uri (Feb 2021, MISO South load shed) and Elliott
  (Dec 2022) sit **inside the load-trend window but outside the 2023+ horse-race
  window** — the price regression dodges both; the load series carries shed hours to flag.
- **Peak-response endogeneity — weaker than 4CP/ICI.** MISO has no single sharp
  coincident-peak charge like ERCOT 4CP or Ontario's Global Adjustment; demand response
  is emergency-oriented (LMRs) and transmission allocation runs through LSE demand
  charges. Large flexible loads still self-curtail against price forecasts
  (the Majumder/Xie mechanism travels), but the scheduled, calendar-predictable
  peak-shaving that plagues ERCOT/IESO load traces is structurally weaker here.
- **BTM solar** is minor in MISO relative to CAISO/ISONE — the load series is close to
  consumption; note and move on.
- **Revisions:** RT final prices correct the prelim series (~4–5-day lag); load archives
  are regenerated after the fact. Pull final/latest; do not mix prelim and final eras.

## 7. Interconnection queue / large-load tracking

- **MISO 2026 Long-Term Load Forecast** (public; summarized by Modo Energy): system
  energy 678 TWh (2026) → 1,104 TWh (2046), +63%; coincident peak 124 → 184 GW
  (scenarios 149–232). **Data centers: 9.6 → 266 TWh (28-fold; 24% of 2046 energy) and
  +32 GW of the +60 GW peak growth — more than every other driver combined.** MISO
  Central absorbs ~58% of DC energy growth (WI, MI, MO, IN). **Load factor rises
  63% → 68%** — the RTO's own statement that this growth is flat-profile, level-not-spiky.
- **Resource adequacy pressure:** OMS-MISO survey coverage reports a potential **14 GW
  capacity deficit by 2029** (RTO Insider headline; as reported).
- **Process churn is live:** FERC directed all RTOs to update large-load tariff provisions
  on 2026-06-18 (195 FERC ¶ 61,212) with rulemaking RM26-4 open; MISO's response stack is
  ERAS (expedited generation additions), MTEP Expedited Project Review, co-location
  agreements, and a Large Load Working Group. Requests reportedly seek 18–36-month
  connections. **No public large-load queue exists** — the ERCOT monthly funnel has no
  MISO counterpart; the Working Group is the thing to monitor.
- **Hard announced-MW anchors (utility-verified):** Entergy Louisiana × **Meta Richland
  Parish** (LRZ8_9_10): $10B, >4M sq ft, Meta's largest DC; Entergy building three CCGTs
  totaling **2,260 MW** (two in Richland Parish, online 2028–29) plus 1,500 MW
  solar/storage funded by Meta. **Duke Energy**: 7.6 GW of executed DC agreements
  (+2.7 GW in Q1-2026 alone), ~two-thirds under construction, +7.8 GW late-stage
  pipeline — ⚠️ Duke spans six states and *only Duke Indiana is MISO*; never attribute
  the full 7.6 GW to MISO. (Adjacent trap, verified: AEP Indiana Michigan and AWS
  New Carlisle are **PJM**, not MISO — Indiana splits between RTOs.)

## 8. Academic / institutional dataset leads

- **Purdue State Utility Forecasting Group (SUFG)** — Indiana's statutory load-forecast
  body; MISO-relevant, publishes Indiana forecasts. ⚠️ Unverified lead; check whether DC
  scenarios are broken out.
- **MISO Long-Term Load Forecast committee materials** (public page) — workshop decks and
  possibly by-LRZ data-center forecast tables; one click in Phase 2 could yield the
  zone-level DC growth series this project would otherwise estimate.
- From the shared packet, applicable here: LBNL/Brattle retail-price study (MISO-state
  rows), Frick & Lam large-load tariff survey + SEPA/NCCETC DELTa (Entergy and Indiana
  tariffs), EEI large-load project list (July 2026).
- Modo Energy and Grid Strategies national load-growth reports as secondary syntheses.

## 9. Concrete Stage-1 pull spec

| Need | Source | Est. volume |
|---|---|---|
| Zonal load 2013-06 → 2022 | 10 annual `dfal_HIST` zips (~0.8 MB each) | ~590K long rows |
| Zonal load 2023 → present | ~1,315 daily `df_al.xls` (~44 KB each) | ~58 MB → ~31K hourly wide rows |
| Hourly DA LMP 2023 → present | ~1,315 daily `da_expost_lmp.csv` (~1.2 MB) | ~1.6 GB raw; extract 8 hubs → ~252K node-hours |
| Hourly RT LMP 2023 → present | ~1,315 daily `rt_lmp_final.csv` | same again |
| (Optional) RT 5-min final | ~187 weekly `5MIN_LMP.zip` | several GB; out of Stage-1 scope |

All ungated, no quota; politeness throttling only. **Prerequisites:** add `xlrd` +
`openpyxl` to the venv. **Panel:** hour-beginning EST → converted/flagged panel mirroring
`ercot_diagnostic_panel.parquet`, zone-groups wide, gradient via the shared
`add_load_gradient_columns` lineage.

**Horse race design (checkpoint decision):** 7 load series (6 groups + MISO) × 8 named
hubs, full cross (~56 cells), DA and RT ex-post — the ERCOT 132/135 pattern. Alternative
price granularity: 437 Loadzone CPNodes (LSE-level). Window 2023-01-01 → present.
**Open dependencies:** (a) pre-2023 archive-bundle enumeration if the Q4-2022 gap or
longer price history is wanted; (b) LRZ8_9 → LRZ8_9_10 label-flip year; (c) hub↔zone-group
mapping is imperfect by construction (no Iowa/Wisconsin hub) — the full cross sidesteps it.
**Future-work hook (not Stage 1):** `GRE.REC.DATA` congestion vs. a rural MN/ND control
node — a within-MISO Loudoun-style locational contrast; plus the free 5-min final panel.

## 10. Source index

- Market reports host (daily files): `https://docs.misoenergy.org/marketreports/` —
  patterns verified in §4/§5
- Market reports listing (JS): https://www.misoenergy.org/markets-and-operations/real-time--market-data/market-reports/
- Archive bundles (CDN): `https://cdn.misoenergy.org/` — e.g. `RT_LMP_HOURLY631315.zip`
- Real-time JSON: `https://public-api.misoenergy.org/api/` (FuelMix, RealTimeTotalLoad,
  MarketPricing 5-min rolling)
- Large Load page: https://www.misoenergy.org/planning/large-loads---container-page/large-load-additions/
- Large Load Working Group: https://www.misoenergy.org/engage/committees/large-load-working-group/
- Long-Term Load Forecast committee: https://www.misoenergy.org/engage/committees/long-term-load-forecast/
- Modo Energy LTLF analysis: https://modoenergy.com/research/en/miso-2046-demand-outlook-data-centers-20-gw-2030
- FERC large-load action: https://www.ferc.gov/news-events/news/ferc-launches-aggressive-targeted-action-speed-large-load-integration ; rulemaking https://www.ferc.gov/rm26-4
- Entergy × Meta Richland Parish: https://www.entergy.com/news/entergy-louisiana-power-meta-s-data-center-in-richland-parish
- Duke DC contracts (Q1-2026): https://www.utilitydive.com/news/duke-energy-earnings-anderson-gas-plant/819428/
- OMS-MISO survey deficit: https://www.rtoinsider.com/81668-oms-miso-ra-survey-results-capacity-deficit/
- LMR whitepaper: https://cdn.misoenergy.org/LMR%20Whitepaper652580.pdf ; LMR FAQ: https://help.misoenergy.org/knowledgebase/article/KA-01560/en-us
- Rainbow Energy Center: https://rainbowenergycenter.com/ ; ND legislature deck: https://ndlegis.gov/sites/default/files/pdf/committees/69-2025/27.5070.02000presentation0910.pdf
- EEI Large Load Projects and Tariffs (July 2026): https://www.eei.org/-/media/Project/EEI/Documents/Issues%20and%20Policy/List%20of%20Large%20Customer%20Projects%20and%20Tariffs
- IURC docket example (facility MW in dockets): CN 46097 exhibits via iurc.portal.in.gov
- gridstatus MISO module (endpoint corroboration): https://github.com/gridstatus/gridstatus/blob/master/gridstatus/miso.py
- Shared packet: CRS R48646 (see design spec for full packet citations)
