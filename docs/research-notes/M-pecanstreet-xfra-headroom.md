# M — Pecan Street × XFRA: is there panel headroom for a home compute node?

Analysis note, 2026-08-14. Commissioned by
`docs/plans/2026-08-14-pecanstreet-xfra-implementation-plan.md`; design in
`docs/specs/2026-08-14-pecanstreet-xfra-headroom-design.md`.
Code: `scripts/pecanstreet_lib.py`, `scripts/pecanstreet_headroom.py`,
`scripts/pecanstreet_1sec.py`. Outputs: `outputs/pecanstreet/` (gitignored).
Every number below cites the JSON it came from.

---

## 0. The answer in one paragraph

**Whether a 12.5 kW XFRA node fits in a house is decided almost entirely by
the electrical service size — and the Pecan Street free tier never records
it.** At a 200 A service, every one of the 73 homes across Austin, New York
and California can host a firm 12.5 kW node at its single worst minute of the
year. At 150 A, 84–91% can. At 100 A, **4–48%** can. The load data is
excellent and the analysis is decisive; the one variable that determines the
answer is the one nobody measured. That is the finding, and it rhymes with
the standing lean logged in `decisions.md` § 2026-08-11: the binding
constraint on this whole research programme is missing data, not missing
method.

Two secondary results are firmer than expected and worth carrying forward:
residential second-by-second volatility is **tiny and self-cancelling**
(§ 3), and the XFRA node is a **firm always-on load, not an oscillating
one** (§ 1.4) — which means it poses a capacity question, not a reliability
one.

---

## 1. What XFRA is, and where it is siting (RQ1)

Source file: `outputs/pecanstreet/siting_research.md`, all access dates
2026-08-14. Primary source is the SPAN/NVIDIA "XFRA White Paper" (Arch Rao &
Chris Lander, ©2026 SPAN.IO, `ap.span.io/XFRA_White_Paper.pdf`), cited by
printed page.

**1.1 Siting: not disclosed as of 2026-08.** No primary source names a metro,
state, or utility. The white paper (p.31) says only that a "100-Node
residential proof of concept" would roll out "in early Q3 in partnership with
a leading build-to-rent company." Early Q3 has arrived with nothing publicly
named. The only geography anywhere is a hedged secondary quote — pv magazine
USA reporting SPAN CRO Ryan Harris saying the programme will be in "a
southwestern state — likely Nevada or Arizona"
(<https://pv-magazine-usa.com/2026/04/15/span-and-nvidia-to-develop-ai-data-centers-in-your-backyard-lowering-electric-bills/>).
PulteGroup's own newsroom carries no XFRA release — checked, confirmed empty,
not merely unsearched.

**1.2 Climate.** If Nevada/Arizona holds, it is hotter and more
cooling-dominated than Austin, so the Austin-derived coincidence numbers in
§ 2 should be read as an *understatement* of real summer peak risk, not a
like-for-like proxy. This rests on one hedged quote and nothing more.

**1.3 Node size: ~12.5 kW continuous.** No primary source states a per-node
kW figure; it triangulates three independent ways from a Latitude Media
interview with SPAN CEO Arch Rao
(<https://www.latitudemedia.com/news/span-to-launch-mini-ai-data-centers-for-distributed-at-home-compute/>):
1.25 MW ÷ 100 nodes = 12.5 kW; the 2027 target of 100 MW ÷ 8,000 nodes =
12.5 kW; and 1,600 GPUs ÷ 100 nodes = 16 GPUs/node, matching the white
paper's two-module architecture (p.24, two 4U 8-GPU modules per node). It is
physically coherent: 16 × RTX PRO 6000 Blackwell at ~600 W ≈ 9.6 kW of GPU,
plus 4 EPYC CPUs and a 35,000 BTU cooling heat pump.

A competing **19.2 kW** figure circulates widely in secondary coverage. It
appears to be an inversion: pv magazine computed 40% of a 200 A service
(80 A ≈ 19.2 kW at 240 V) and labelled it headroom, but the white paper (p.5)
says residential infrastructure "operates at roughly 40% of peak capacity,
leaving substantial headroom untapped" — 40% is the *used* fraction, so
headroom is the other ~60% (~28.8 kW). 19.2 kW is carried below as an upper
stress case only, not as a trusted spec.

**1.4 The node does not yield to appliances — this falsifies the agenda's
assumption.** White paper p.15 (§4.2): "XFRA Nodes are provisioned to operate
as always-on loads within verified residential capacity. In normal operation,
Node power is maintained continuously. If rare residential peaks occur, XFRA
preserves Node operation by **first drawing on the whole home battery**, and
in extreme cases by **temporarily reducing non-critical flexible loads like
EV charging via PowerUp**. Node interruption will only occur during defined
power events (such as a grid outage, a utility demand response event, or a
safety-triggered shutdown)." The node is the thing kept running; the EV is
the thing curtailed.

Two consequences run through the rest of this note. First, the correct
headroom metric is `limit − household maximum` — the node must fit at the
worst minute, not on average — which is what § 2 reports. Second, the
volatility comparison in § 3.5 describes a scenario the vendor says will not
occur, so it is a bound, not a forecast.

---

## 2. Does the headroom exist, and does it survive summer peak? (RQ2)

Sources: `outputs/pecanstreet/headroom_{austin,new_york,california}.json`
and `headroom_<city>.png`. 1-minute bundles are primary (a breaker responds
to sustained draw, and 15-minute averaging shaves real peaks — measured
peak-shaving ratio median **0.796 / 0.781 / 0.781** for Austin / New York /
California, i.e. the 15-minute files understate true maxima by ~20%).
Whole-home consumption is
reconstructed as `grid + solar + solar2` — gross draw through the panel,
which is the quantity a service rating constrains.

**2.1 The headline table.** Fraction of homes that could host a *firm* node
of the given size at their single worst minute of the record, against three
service scenarios with the NEC 80% continuous-load derating applied:

| Node | 100 A | 150 A | 200 A |
|---|---|---|---|
| 1 kW | 0.92 / 0.88 / 0.91 | 1.00 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| 5 kW | 0.72 / 0.80 / 0.91 | 0.96 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| 6.25 kW | 0.68 / 0.76 / 0.91 | 0.96 / 1.00 / 1.00 | 1.00 / 1.00 / 1.00 |
| **12.5 kW** | **0.04 / 0.16 / 0.48** | **0.84 / 0.84 / 0.91** | **1.00 / 1.00 / 1.00** |
| 19.2 kW | 0.00 / 0.00 / 0.00 | 0.16 / 0.40 / 0.91 | 0.96 / 0.92 / 0.96 |

Austin / New York / California. n = 25 / 25 / 23 homes.

**The 12.5 kW row is the result.** The same node, the same homes, the same
minutes — and the answer swings from *every home* to *one home in
twenty-five* purely on an assumption about panel size. No measured service
rating exists anywhere in the Pecan Street free tier, so this band cannot be
collapsed to a single number from this data.

**2.2 Summer coincidence is real but shallow.** Median daily-minimum headroom
(the worst minute of each day, median across homes, 200 A × 0.8) runs ~33 kW
in winter and dips to ~30 kW across June–September — visible in the middle
panel of `headroom_austin.png`, and never approaching zero. The coincidence
is genuine: for **16 of 25** Austin homes and **18 of 23** California homes
the annual maximum falls inside the June–September 15:00–18:59 window, with a
median hour-of-maximum of **17:00**.

A framing warning for anyone re-reading the JSON: the `peak_window` fractions
are mechanically ≥ the annual ones, because the peak window is a *subset* of
minutes and a maximum over a subset cannot exceed the maximum over the whole.
That comparison is **not** a stress test and must not be reported as
"headroom survives summer." The annual figure is the binding constraint and
already contains the summer peak; the month-of-maximum count above is the
honest coincidence evidence.

**2.3 The load shape behind the numbers.** Median home annual maximum is
12.1 kW (Austin), 10.0 kW (New York), 6.8 kW (California), against a 200 A
derated ceiling of 38.4 kW. Load-duration curves
(`headroom_<city>.png`, left panel) show homes spending the overwhelming
majority of minutes below 5 kW; the 100 A × 0.8 line at 19.2 kW is crossed
only by brief spikes. Diurnal peak hour is 18:00 (Austin), 20:00 (New York),
18:00 (California) — all inside the expected residential evening band.

**2.4 Robustness to programme participation.** Excluding homes in a
load-changing treatment arm leaves n = 9 (Austin), 25 (New York), 12
(California). The 200 A / 12.5 kW result is **unchanged at 1.00 in all three
cities**; the 150 A figure softens slightly (Austin 0.84 → 0.78). The
headline is not an artifact of intervention homes.

Note this differs from the plan's original instruction. The first pass
treated any programme flag as disqualifying, which excluded *every* Austin
home (all 25 carry `program_energy_internet_demo`) and *every* California
home (all 23 carry `program_civita_group`), making the robustness cut
vacuous. Those two are enrolment markers for Pecan Street participation, not
treatments. The six real treatments are `program_579`, `program_lg_appliance`,
`program_verizon`, `program_ccet_group`, `program_civita_group`,
`program_shines` — and explicit control arms (`CCET - Control`,
`Civita - Control`) are untreated by definition and are **kept**, superseding
the plan's original note that control arms would be excluded alongside the
treated.

**2.5 One meter fault, removed and reported.** Austin `dataid` 7536 recorded
5,308.7 kW at 2018-02-02 12:27, against its own p99.9 of 8.45 kW and mean of
1.31 kW. Inspecting the full row settled it: every channel flipped sign
simultaneously (`grid` +2894.977, `solar` −8199.953, `oven1` −351.559) and
the leg voltages read **−1,145,948 V and −1,145,406 V on a nominal 120 V
leg**, mirroring to +1,146,134 V the following minute and returning to normal
the minute after. The meter recorded its own failure in a column the analysis
was not otherwise using.

Corpus-wide, **exactly 2 rows of 31,808,722 exceed 48 kW**, both from this
event. Excluding them the corpus maximum is 23.97 kW, leaving an empty gap
between 24 kW and 2,895 kW — so the 100 kW filter threshold is not a tuning
knob; any value in that range is identical. Those two rows were the sole
reason Austin's 200 A / 12.5 kW figure initially read 0.96 rather than 1.00.
The 1-second pass masked a further **76** readings in Austin by the same rule
and 0 in New York.

---

## 3. Can a panel absorb the volatility? (RQ3)

Sources: `outputs/pecanstreet/onesec_{austin,new_york}.json`,
`onesec_psd_<city>.png`, `ncurve_1min_<city>.png`. 25 homes per city; the
Austin pass streamed 12.95 GB and New York 6.31 GB of gzipped 1-second data.

**3.1 Residential second-to-second load barely moves.** Median 1-second
change across homes is **0.0022 kW — about two watts.** The median home's
99.9th-percentile 1-second swing is 1.47 kW (Austin) / 1.62 kW (New York),
and the worst home's is 2.87 / 3.48 kW. Large steps exist but are rare, and
in Austin most of the largest ones are an artifact — see § 3.1a.

**3.1a A zero-fill defect in the Austin 1-second bundle inflates per-home
maxima.** Austin's median per-home maximum 1-second step is 18.09 kW against
New York's 5.82 kW — implausible, given the same homes show a median annual
*level* maximum of 12.1 kW at 1-minute resolution. The cause is visible in
the recorded step events: **18 of 25 Austin homes have their largest step
touching exactly 0.000 kW**, versus **0 of 25** in New York. A live house
never draws exactly zero — there is always standby load — so these are
dropouts written as `0.000` rather than as missing, and the resumption
registers as a ~23 kW instantaneous step. Restricting to the 7 Austin homes
whose largest step lies between two real levels, the median per-home maximum
falls to **8.91 kW**, in line with New York.

This is confined to the extreme tail. The p99.9 swings (1.47 vs 1.62 kW) are
comparable across cities, and `sync_index`, the N-curve, and the PSD are
computed from standard deviations and spectra over tens of millions of
seconds, so a handful of spurious steps per home does not move them. Only
maximum-based statistics are affected — which is why § 3.5's right-hand
column is restricted to the clean subset. This defect is distinct from the
§ 2.5 meter fault: no sign flip, no impossible voltage, and it passes the
`MAX_PLAUSIBLE_KW` filter because ~23 kW is a perfectly possible household
draw. It was found by inspecting `before_kw`/`after_kw` pairs, not by any
threshold.

**3.2 That volatility is idiosyncratic and cancels.** The synchronisation
index Var(aggregate Δ) ÷ Σ Var(home Δ) is **0.902** (Austin) and **0.668**
(New York) over 31.5M and 15.9M valid aggregate seconds. A value near 1 means
homes move independently and their fast noise cancels in aggregate; a value
near N (25) would mean synchronised swings that add. This is the same
cancellation the UKPN facility data-centre sites showed in note `J`, arrived
at from the opposite end of the size distribution.

**3.3 The N-curve confirms it exactly.** Aggregate 1-minute volatility grows
as √N, not N (`ncurve_1min_austin.png`): σ(1) = 0.396 kW rising to σ(25) =
2.400 kW, a ratio of **6.06** against a √N reference of 5.00 and a
synchronised reference of 25. New York: ratio 5.45. The measured curve sits
just above the independent reference across the whole range and nowhere near
the synchronised one.

**3.4 At data-centre frequencies there is almost nothing there.** Per-home
power spectral density (`onesec_psd_austin.png`) is dominated by
sub-0.01 Hz content, with a clear spectral peak near 9 mHz (~110-second
period, consistent with appliance duty cycling). By 0.1–0.5 Hz — the shaded
band — PSD has fallen **4–5 orders of magnitude** below the low-frequency
content.

**The Nyquist caveat, stated plainly.** 1-second sampling gives a Nyquist
limit of 0.5 Hz. The NERC LLTF band of concern is 0.1–30 Hz. So this analysis
sees the bottom **~1.3%** of that band and can say nothing whatsoever about
0.5–30 Hz. Dataport's 2 kHz waveform tier would cover it; licensing for that
tier remains unanswered (see § 6). Any claim here about "data-centre
frequencies" means the 0.1–0.5 Hz sliver only.

**3.5 The oscillating-node comparison is a bound, not a forecast.** Modelling
a hypothetical node as a square wave swinging 90% of its rated power:

| Node | step | × median home's natural p99.9 swing | homes whose largest natural step already exceeds it |
|---|---|---|---|
| 1 kW | 0.90 kW | 0.61× / 0.56× | 7/7 / 25/25 |
| 6.25 kW | 5.62 kW | 3.83× / 3.48× | 6/7 / 17/25 |
| **12.5 kW** | **11.25 kW** | **7.66× / 6.96×** | **2/7 / 3/25** |
| 19.2 kW | 17.28 kW | 11.77× / 10.70× | 2/7 / 1/25 |

Austin / New York. The ratio column uses all 25 homes per city (p99.9 is
unaffected by the § 3.1a defect); the right-hand column is restricted to
homes whose largest step lies between two real levels — 7 of 25 in Austin,
all 25 in New York — because a maximum-based count is exactly what the
zero-fill artifact corrupts. Using all 25 Austin homes would report 17/25
rather than 2/7 at 12.5 kW, and that apparent Austin/New York asymmetry is
the artifact, not a real difference between the cities.

So *if* a 12.5 kW node oscillated at 90% amplitude, each transition would be
~7× the median home's 99.9th-percentile natural swing, and would exceed the
largest step that 22 of 25 New York homes and 5 of 7 clean Austin homes ever
produced.

**But § 1.4 says it does not oscillate.** The white paper describes a flat,
continuous draw interrupted only by grid outages, utility demand-response
events, or safety shutdowns. So this table bounds a counterfactual: it says
what *would* happen under a duty-cycling design the vendor has not built. The
operative finding is the opposite one — **XFRA adds level, not volatility**,
which makes it a capacity-planning question and not a power-quality one.

---

## 4. Why subtracting residential load from total load cannot isolate data-centre load

Closes agenda item 7. The idea was to estimate data-centre load as
(total system load − residential load). It does not work, for four
independent reasons, any one of which is fatal:

1. **Sample-not-census scaling error dwarfs the signal.** Pecan Street is
   ~1,200 volunteer homes; scaling to a service territory of millions
   multiplies every sampling error by ~10³–10⁴. A 1% error in the residential
   estimate swamps a data-centre signal that is itself only a few percent of
   system load.
2. **The volunteer sample is biased in exactly the wrong direction.** These
   homes are disproportionately solar- and EV-equipped (of 2,035 metadata
   rows: 427 with solar, 163 with an EV, 8 with a battery), so their net
   shape is unrepresentative of the residential class being subtracted.
3. **The remainder is not data centres.** Total minus residential leaves
   *all* non-residential load — commercial, industrial, agricultural,
   municipal — of which data centres are a minority almost everywhere. The
   subtraction identifies a residual, not a sector.
4. **The vintage is wrong.** These bundles are 2018–19 (California 2014–18);
   the data-centre build-out being studied is 2023 onward. The residential
   baseline predates the phenomenon.

The shape-based variant of the same idea is strictly dominated by the
ENTSO-E/CSO measured-dose work already shipped in notes `K` and `L`, where
the data-centre share is *measured* rather than inferred by subtraction.

---

## 5. Caveats

- **No measured panel sizes.** The scenario band in § 2.1 is the deliverable,
  not a step toward a single number. Collapsing it needs a data source the
  free tier does not have.
- **2018–19 vintage.** Pre-dates the current appliance and EV mix. Modern
  homes with heat pumps, induction ranges and Level-2 EV charging will show
  higher maxima, pushing the hostable fractions down. This biases the note
  *optimistic*.
- **25-home volunteer samples.** Not a random sample of housing stock;
  solar/EV-skewed as noted above.
- **New York and California spans are not annual.** New York covers
  2019-05-01→10-31 (six months, no winter); California pools 2014–2018 across
  homes with very uneven coverage (`yearly` shows 3–15 homes per year).
  **Never label New York or pooled-California figures "annual."** Only Austin
  is a clean calendar year. California's `yearly` table also carries a small
  2013 entry — a boundary artifact of converting Central-stamped instants to
  Pacific, not extra data.
- **California timezone.** CA files are San Diego homes stamped with Central
  offsets. Parsing offset → UTC → `America/Los_Angeles` is validated by the
  diurnal check: peak hour lands at 18:00, inside the 16–21 evening band. Had
  the stamps been mislabelled Pacific clock readings, the peak would have
  landed ~13–15. It did not.
- **The PSD is chunk-size dependent.** Where `PsdAccumulator`'s internal
  4096-sample flush lands is set by the reader's chunking, not by the data;
  different chunkings moved PSD magnitudes by up to 94% in testing, though
  peak *frequency* was stable throughout. All results here were produced with
  `chunk_rows = 2,000,000`, recorded in every output JSON. Read the PSD for
  spectral *shape*, not for absolute magnitude.
- **Austin 1-second zero-fill (§ 3.1a).** 18 of 25 Austin homes write `0.000`
  during dropouts rather than a missing value, inflating maximum-based
  1-second statistics. Any future reuse of the Austin 1-second bundle must
  treat an exact `0.000` as suspect. Quantile- and σ-based statistics are
  unaffected; maximum-based ones are not, and the note restricts them to the
  clean subset accordingly.
- **Aggregate composition guard.** Aggregate 1-second deltas are taken only
  between adjacent seconds reporting the same number of homes, so a home
  joining or leaving does not register as volatility. The one case it cannot
  catch is an exact swap — one home dropping in the same second another
  appears. Both cities show a handful of extreme aggregate outliers
  (New York's aggregate 1-second maximum is 52.21 kW against a standard
  deviation of 0.507 kW) that are most likely this residue; they do not
  affect the standard-deviation-based `sync_index`.
- **Build-to-rent vs owner-occupied.** The white paper's pilot partner is a
  build-to-rent company; Pecan Street's homes are owner-occupied. Occupancy
  model plausibly affects both load shape and appliance stock.

---

## 6. Future hooks

- **`leg1v` / `leg2v`.** The 1-second Austin files carry per-leg voltages,
  unused here except forensically in § 2.5. They are a direct power-quality
  channel — voltage sag under load step is exactly what a 12.5 kW node
  switching on would produce, and it is measurable in data already on disk.
- **The Pecan Street THD set.** 2018+ files add apparent power, current,
  angle and THD, which would extend § 3 from real-power volatility into
  genuine power quality.
- **The 2 kHz waveform tier.** The only route to the 0.5–30 Hz band this note
  cannot see. Licensing terms remain unanswered — see
  `docs/sources/pecanstreet-access-constraints.md`.
- **Panel-size data.** The single highest-value addition. Utility service
  records or AHJ permit data would collapse § 2.1's band to an answer.

---

## Related

- `docs/decisions.md` — the log of record; findings here are provisional
  until an entry there rules on them.
- `J-ukpn-flatness.md` — facility data-centre flatness; § 3.2 here is the
  residential-scale counterpart.
- `I-advisor-links-2026-08.md` — the NERC LLTF 0.1–30 Hz band and the
  timescale framing that § 3.4 is measured against.
- `docs/sources/pecanstreet-access-constraints.md` — corpus limits and traps.
