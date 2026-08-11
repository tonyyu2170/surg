# Dose check — did NECEC actually deliver energy into Maine?

**Date:** 2026-08-11
**Purpose:** Gate on the NECEC price test proposed in
`2026-08-11-isone-canada-tie-verification.md` §5. "Commercial operation
2026-01-16" is a paperwork date. Before pre-registering a price test, establish
that the treatment actually arrived, how big it is, and when it started —
otherwise a price null is a measurement null, not a result.

---

## 1. NECEC is flowing, near-firm, at ~1,060 MW

ISO-NE settles NECEC at external node **`.I.HQMRL_RD345 1`** (Merrill Road
345 kV, Lewiston, Maine). Sampled hourly flows, **2026-03-01 → 2026-03-08**
(168 h), from gridstatus.io `isone_interchange_hourly`:

| ISO-NE external node | interface | mean MW | min | max |
|---|---|---|---|---|
| `.I.HQMRL_RD345 1` | **NECEC (Lewiston, ME)** | **−1059.1** | −1119 | 0 |
| `.I.HQ_P1_P2345 5` | HQ Phase I/II (Sandy Pond, MA) | −171.7 | −1396 | 0 |
| `.I.HQHIGATE120 2` | Highgate (VT) | −49.1 | −225 | 0 |
| `.I.SALBRYNB345 1` | New Brunswick (ME) | −130.5 | −362 | 200 |
| `.I.ROSETON 345 1` | NY AC (Roseton) | −1021.6 | −1600 | 1.8 |
| `.I.SHOREHAM138 99` | Cross Sound Cable (CT) | +100.3 | 0 | 330 |
| `.I.NRTHPORT138 5` | Northport–Norwalk (CT) | 0.0 | 0 | 0 |

Sign: **negative = import into New England** (established in §2). NECEC runs at
89% of its 1,200 MW rating with almost no hour-to-hour variation — a firm block,
which is what an HQ delivery contract looks like and is *not* variable renewable
output.

⚠️ **This is a one-week sample.** The gridstatus.io free-tier row quota (6 keys,
500k rows/key/month) was exhausted mid-pull on 2026-08-11, so the continuous
NECEC series could not be retrieved. Everything below that depends on NECEC's
level uses this week's ~1,060 MW as the estimate. **The switch-on date and the
ramp profile are NOT independently verified** — only EIA's 2026-01-16 commercial
operation date and this March observation.

---

## 2. EIA-930 omits NECEC from ISO-NE's Canadian interchange

This is a data-quality finding that matters beyond this project.

EIA-930 (`EIA930_INTERCHANGE_*.csv`, Hourly Grid Monitor six-month files) reports
ISNE interchange against exactly three neighbors: HQT, NBSO, NYIS. Compared over
the **identical window** 2026-03-01 → 2026-03-08, against the per-interface sums
above:

| neighbor | EIA-930 ISNE | sum of ISO-NE nodes | gap |
|---|---|---|---|
| NBSO | −137.5 | −130.5 | −7.0 ✓ |
| NYIS | −913.8 | −921.3 | +7.5 ✓ |
| **HQT** | **−218.8** | **−1279.9** | **+1061.1** ✗ |

NB and NY agree to within ~1%, which confirms the two sources share a sign
convention and are otherwise consistent. The HQ gap is **1,061 MW against
NECEC's own 1,059 MW** — i.e. the entire discrepancy is NECEC.

**Conclusion: EIA-930's `ISNE → HQT` series excludes the NECEC interface.**
Any analysis using EIA-930 to measure New England's Canadian imports after
January 2026 understates them by ~1,000 MW and will show New England *exporting*
to Québec in months when it is in fact a large net importer. Flagged here because
EIA-930 is the default free source for exactly this question.

---

## 3. Calendar-matched dose, Jan 16 – Jun 30

EIA-930 (legacy HQ interfaces only, NECEC excluded per §2), positive = into
New England:

| year | HQ legacy | NECEC | **HQ total** | NBSO | **Canada total** | NYIS |
|---|---|---|---|---|---|---|
| 2024 | 730.0 | 0 | 730 | 113.9 | **844** | 309.3 |
| 2025 | 558.2 | 0 | 558 | 197.5 | **756** | 608.5 |
| 2026 | 27.5 | ~1060 est. | ~1088 | 109.2 | **~1197** | 840.0 |

Two things happened at once, and the second is larger than the first:

1. **Net Canadian imports rose** ~+440 MW (756 → ~1197) vs. the same calendar
   window in 2025.
2. **The injection point moved to Maine.** Legacy HQ collapsed from +558 to
   +27.5 MW — a −530 MW swing at Sandy Pond (MA) and Highgate (VT) — while
   ~1,060 MW switched on at Lewiston (ME). Roughly a gigawatt of Canadian
   injection *relocated* from Massachusetts and Vermont into Maine.

For a test of *localized* price effects this relocation is the larger and
cleaner shock, and it points the same way: ME should get long, MA/VT shorter.

---

## 4. The confound this surfaces: legacy HQ was already falling pre-NECEC

Monthly HQ legacy imports (MW into New England):

| 2025-07 | 08 | 09 | 10 | 11 | 12 | 2026-01 | 02 | 03 | 04 | 05 | 06 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 500 | 64 | 117 | −41 | −575 | −176 | 87 | 538 | 90 | −380 | −297 | −54 |

Legacy HQ flows went negative in **October and November 2025**, months *before*
NECEC energized. Whatever is driving Hydro-Québec to export less to New England
(reservoir levels, Québec domestic demand, HQ's own export economics) started
before the treatment and is still running during it.

**This is not attributable to NECEC and it contaminates any "Canadian imports"
treatment variable.** It is a reason to define the treatment as NECEC's
*localized injection at Lewiston* — which has a clean on-date and a clean
location — rather than as a change in total Canadian imports, which does not.

---

## 5. Verdict on the gate

**The treatment arrived and it is large.** ~1,060 MW firm at a single Maine node
is roughly 80% of Maine's mean zonal load (1,288 MW). A price test is
well-powered in principle and is worth pre-registering.

Carry forward as known limitations:

- NECEC's level rests on a one-week sample; the switch-on date rests on EIA's
  stated commercial-operation date, not on observed flows.
- Legacy HQ flows have a pre-existing downward trend (§4).
- Hydro-Québec is dispatchable reservoir hydro delivered as a firm block, so the
  advisor's "Canadian renewable variability" premise is weak on mechanism. The
  prediction for *volatility* is if anything downward, not upward.

## Sources

- gridstatus.io `isone_interchange_hourly` (ISO-NE external node actual
  interchange), sampled 2026-03-01 → 2026-03-08.
- U.S. EIA Hourly Electric Grid Monitor, six-month bulk files
  `EIA930_INTERCHANGE_{2024_Jan_Jun, 2025_Jan_Jun, 2025_Jul_Dec, 2026_Jan_Jun}.csv`,
  `https://www.eia.gov/electricity/gridmonitor/sixMonthFiles/`
- NECEC 1,200 MW / Lewiston converter / commercial operation 2026-01-16: EIA
  *Today in Energy* #67105, via `2026-08-11-isone-canada-tie-verification.md`.
