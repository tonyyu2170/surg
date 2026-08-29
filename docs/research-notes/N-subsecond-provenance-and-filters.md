# Why Hourly Load Is Flat — Provenance of the Sub-Second Claim and the Four Filters

Research date: 2026-08-20. Answers the five action items in the "Notes from meeting"
section of `docs/plans/advisor/2026-08-19-advisor-meeting-agenda.md` plus the closing question
("hourly load barely fluctuates — but why?").

Primary documents read in full: NERC White Paper 2 (March 2026), NERC Reliability
Guideline (May 2026), arXiv 2508.14318 (Microsoft/OpenAI/NVIDIA), arXiv 2409.11416,
arXiv 2502.01647, arXiv 2608.01250.

All arithmetic here is closed-form and stated inline — boxcar gain
`|sin(pi*f*T)/(pi*f*T)|` with envelope `1/(pi*f*T)`, and coherent-vs-incoherent
summation. Both were also checked numerically against 1 kHz synthetic signals
(periodic and AR(1) broadband); the periodic envelope held as an upper bound in
every case. No production data or pipeline code was involved, so nothing was
added to `scripts/` or `tests/`.

---

## 0. Headline — the working conclusion is TWO findings, and only one of them is real

The agenda's current conclusion is "at least on a large timescale (hourly) not a lot of
fluctuation with load." That statement conflates two independent facts, and the report
needs both, labelled differently:

1. **Sub-second and second-scale volatility CANNOT appear in hourly data. This is
   arithmetic, not evidence.** A boxcar average of width `T` attenuates a fluctuation at
   frequency `f` by at most `1/(pi*f*T)`. At the measured band centre (see §1) a 250 MW
   campus swinging ±112.5 MW leaves **0.05 MW** of ripple in an hourly meter — 0.02% of
   the campus, and roughly 0.00003% of a 150 GW RTO. **Every dataset in this project
   would show a flat hourly load even if the industry claim were true in full.** This is
   a tautology and must be presented as one.

2. **The hourly ENVELOPE separately does not move much either.** EPRI's metered
   facilities run at **94% (hyperscale) and 88% (colocation) of their own realized annual
   peak** (`I-advisor-links-2026-08.md:152`). That is a statement about duty cycle, not
   about filtering, and it survives independently of (1). It is a genuine empirical
   finding and it is what makes the project's null substantive.

**If the report says "hourly load is flat because averaging kills the fluctuation," it has
answered only (1) and deleted (2), and the headline becomes circular.** The defensible
form is: *the fast phenomenon is arithmetically invisible at every resolution this project
holds, AND the slow envelope is independently, measurably flat.*

---

## 1. Q1 — Where the sub-second number comes from: a four-rung provenance ladder

The advisor asked where the LLTF deck's data came from. The answer is that the claim has
four evidentiary tiers of very different quality, and the project should cite them as a
hierarchy rather than as a consensus.

| Rung | Source | What it actually measures | Weight |
|---|---|---|---|
| 1. Vendor anecdote | Musk (Lex Fridman podcast, Aug 2024); Google eng. blog (Feb 2025); Tesla Megapack slides at LLTF | Nothing published. Assertions of "10–20 MW several times per second" and "tens of MW" | Lowest — and Tesla is selling the mitigation |
| 2. Academic, extrapolated | arXiv 2409.11416 (U. Alberta); arXiv 2502.01647 (Li & Li) | **Single desktop GPUs.** 2409.11416 measures an RTX 4090 at 414 W mean / 461 W max and an AMD 7900XTX at 50–250 W; its cluster figure is the MIT Supercloud BERT job at **48.7 kW peak**. 2502.01647 is oscilloscope captures on "a single in-lab workstation," Ryzen 5 5500 + RTX 4090 | Real measurements, but MW-scale claims are **extrapolation** |
| 3. Operator production data | **arXiv 2508.14318**, *Power Stabilization for AI Training Datacenters* (Microsoft + OpenAI + NVIDIA, Aug 2025) | Production traces from jobs spanning tens of thousands of GPUs; swings **10 MW to >100 MW** | Best quantification that exists |
| 4. Independent grid-side measurement | *Understanding the Inception of 14.7 Hz Oscillations Emerging from a Data Center* (Dominion synchrophasor data, several months, Sustainable Energy Grids & Networks 2025) | A real oscillation on a real grid, measured by a third party | Only truly independent rung — **but see the caveat below** |

**Two things to state plainly rather than bury:**

- **NERC's own mitigation guidance rests on rung 3.** The May 2026 Reliability Guideline
  cites arXiv 2508.14318 by name (footnotes 28 and 40) as the technical basis for its
  recommended mitigations. The regulatory framework therefore rests on operator-supplied
  data.
- **Rung 3 is self-reported and unreplicated.** 2508.14318 is authored by the operators
  themselves, releases no raw data, and has not been independently reproduced. The single
  best characterization of the spectrum is a vendor/operator artifact. This is consistent
  with the project's standing lean that **the binding constraint is absence of data.**

### ⚠️ The 14.7 Hz event is NOT workload synchronization — do not blur this
The only independent grid measurement is a **control-interaction instability**: a 10–11 Hz
mode local to the data center goes unstable under changing operating conditions and
emerges at 14.7 Hz. It is a power-electronics control problem, not GPUs stepping in
unison. NERC's own White Paper 2 makes the same distinction, attributing forced
oscillations to "unintended control interactions **or** as part of their processes (e.g.,
AI training)" — control interaction is listed first. **There is no independent grid-side
measurement of training-synchronization oscillation.**

> **Updated 2026-08-20 (§ 7.1).** There are **four** measured grid events, not one — Meta
> 49/71 Hz (2017), ERCOT 23 Hz (2024), Dominion 14.7 Hz, Dominion 1–11 Hz — and **all four
> are power-electronics control interactions**, one cured by a firmware upgrade. The claim
> above gets stronger, not weaker. But ERCOT *has* field-measured normal LEL workload
> profiles as of Dec 2025; § 7.1 states the precise limit of the claim.

### ⚠️ Correction to the project's stated band: it is 0.2–3 Hz, not 0.1–30 Hz
The agenda repeatedly cites "0.1–30 Hz" as "where industry actually locates the AI-load
problem." That number is Tesla's LLTF slide. The **measured** production spectrum is
narrower and slower:

- **arXiv 2508.14318:** "AI workload power traces ... show **FFT energy concentrated
  between 0.2–3 Hz**."
- Same paper on per-GPU cycling: a dramatic power drop "ranging from **once per second or
  less, to once every tens of seconds**, depending on the scale of the job" (≈0.03–1 Hz).
- **NERC Reliability Guideline** narrows the *reliability-relevant* band further: "If the
  frequency of load cycling is in the electromechanical range (i.e., **0.1–2 Hz** for
  inter-area and local modes), there is a potential for interacting with natural low
  frequencies." The 5–30 Hz end maps to SSCI/SSTI — a rarer risk specific to loads
  co-located with generators.

**Consequence that runs against intuition: bigger jobs are SLOWER, not faster.** Iteration
time grows with job scale, so scaling pushes the fundamental *down* toward 0.1–2 Hz —
which is precisely the inter-area mode band NERC flags as dangerous. The risk does not
recede as clusters grow; it migrates into the worst band.

---

## 2. Q6 mechanism — the four filters between a GPU and a meter

Filter 1 alone is sufficient to explain flat hourly data. The others matter for what a
*facility* meter would show.

### Filter 1 — Averaging (arithmetic, unavoidable, and decisive)
Boxcar gain is `|sin(pi f T)/(pi f T)|`, envelope `1/(pi f T)`. Amplitude surviving:

| Fluctuation | 1-sec | 1-min | 5-min | 30-min | 1-hour |
|---|---|---|---|---|---|
| 0.2 Hz | 0.94 | 1/38 | 1/188 | 1/1131 | 1/2262 |
| 0.5 Hz | 0.64 | 1/94 | 1/471 | 1/2827 | 1/5655 |
| 3 Hz | 1/9.4 | 1/566 | 1/2827 | 1/16965 | 1/33929 |

Worked case, 250 MW campus, ±112.5 MW swing, through an **hourly** meter:
0.2 Hz → **0.050 MW**; 1 Hz → 0.010 MW; 3 Hz → 0.003 MW.

> ⚠️ **This worked case is illustrative, not a cited measurement.** It combines
> Tesla's "90% amplitude" slide with the xAI Colossus ~250 MW scale figure
> (`I-advisor-links-2026-08.md` § 3.1). arXiv 2508.14318 reports swings of
> "10 MW to >100 MW" but does **not** pair an amplitude to a campus size. Do not
> cite the ±112.5 MW figure to that paper.

**Correction to the agenda's "bottom 1%" claim.** The agenda says 1-second sampling sees
"roughly the bottom 1% of the 0.1–30 Hz band." That is wrong twice: wrong band, and it
ignores that 1-second averaging *retains* amplitude at the low end. Against the measured
0.2–3 Hz band, 1-second data covers **10.7% linearly / 33.8% in log-frequency**, and
retains **94% of amplitude at 0.2 Hz** and 64% at 0.5 Hz. The project's finest data sits
*inside* the relevant band for the first time — it just cannot reach the bulk of it.
(Against Tesla's 0.1–30 Hz the figures are 1.3% linear / 28.2% log; the "1%" came from a
linear reading of the wrong band.)

**This converts the null from a data-quality shortfall into physics.** No dataset outside
operator telemetry — not PJM, not ENTSO-E, not UKPN, not Pecan Street — could have shown
this phenomenon at any resolution any of them publish.

### Filter 2 — Coherence (see Q4, §3) — does NOT filter for training; amplifies
### Filter 3 — Physical absorbers on site (see Q2/Q3, §4–5) — dilutes, partially absorbs
### Filter 4 — Duty-cycle envelope — the one real empirical finding (EPRI 94%/88%, §0)

---

## 3. Q4 — Does it aggregate out? Correlation decides, not count

The advisor asked whether the law of large numbers rescues this. **The discriminating
variable is correlation, not N.** For N units each swinging by amplitude `a`, expressed as
a fraction of total load:

- **Coherent (phase-locked):** `N*a / (N*P) = a` — **constant in N. Never cancels.**
- **Incoherent (independent):** `sqrt(N)*a / (N*P) = a/sqrt(N)` — decays as `1/sqrt(N)`.

| N | coherent | incoherent | ratio |
|---|---|---|---|
| 100 | 90% | 9.0% | 10× |
| 10,000 | 90% | 0.90% | 100× |
| 100,000 | 90% | 0.285% | 316× |

> **Updated 2026-08-20 (§ 7.2, § 7.3).** Tier 1 coherence is now **independently measured** —
> a national lab found power-variability sd scaling **linearly** with node count at 0.1 s
> resolution on H100s, which is the ρ = 1 case. And the binary framing below generalizes to
> `Var = N*sigma^2*[1 + (N-1)*rho]`, where correlation dominates once ρ > 1/(N−1) — **provided
> ρ is measured in-band**, a far stricter condition than envelope correlation.

**The same math gives opposite answers for homes and for GPUs, and this reconciles the
project's own Pecan Street result.** 73 homes cycling appliances independently are
incoherent → `1/sqrt(73)` ≈ 8.5× reduction; note M's "1-sec volatility cancels as √N" is
correct *for homes*. A synchronous training job is **phase-locked by the all-reduce
barrier** — that is what "synchronized training" means — so it adds coherently and gets no
reduction at all. **Independence is the load-bearing assumption in √N, and synchronized
training is the textbook violation of it.**

Three tiers, with evidence quality flagged:

1. **Within one job — coherent, no cancellation. [Primary evidence]** 2508.14318 considered
   the multiplexing argument explicitly and dismissed it: *"Although a higher hierarchy
   level can theoretically offer more power demand multiplexing from the servers, since we
   are concerned about large synchronous training jobs that have identical power demands
   across all participating servers, **this is not a factor that affects us**."* And it
   goes the wrong way: *"as GPU counts grow, the **aggregate load swing amplitude at these
   critical frequencies increases**, magnifying the potential resonance effects."*
   arXiv 2502.01647 agrees — aggregation *amplifies* when GPUs checkpoint "nearly in
   unison," and it recommends **deliberate phase-shift/staggered scheduling** as the fix,
   which is itself evidence that natural cancellation does not occur.
2. **Across independent inference fleets — genuinely cancels. [Primary evidence]**
   arXiv 2608.01250 finds inference ramp-rate risk converges as **1/√N** by the functional
   CLT, because inference has "heterogeneous request-level dynamics without synchronized
   phases." **But peak power follows the law of large numbers with a non-zero floor that
   does not average out**, and even a small arrival-correlation probability (s=0.10)
   produces near-ceiling coincidence at fleet scale. So: ramps cancel, peaks do not.
3. **Across facilities — fails for exactly the jobs that matter. [Primary evidence]**
   2508.14318 states participating nodes "form a majority of a datacenter, **or even
   multiple datacenters in the same grid**." A single synchronous job spans facilities, so
   cross-facility independence fails precisely for frontier-scale training. Whether
   *different* operators' jobs are mutually independent is **inference, not evidence** —
   no source measures it.

**Does something else aggregate out instead?** HVAC yes (independent chillers, and see
§4), inference fleets yes (tier 2), behind-the-meter storage no — it is a deliberate
control, not a random draw, so it does not average, it *acts*.

---

## 4. Q2 — "Compute fluctuates but overall load is smooth once you add storage and other uses"

**Partly right, but the mechanism is wrong for cooling, and the advisor's phrasing
overstates it.** Cooling *dilutes*; it does not *cancel*. Nothing is destroyed — the
denominator grows.

Cooling has minutes-scale thermal inertia and physically cannot track a 0.2–3 Hz IT swing,
so it contributes a smooth baseline. Using load shares already in the project
(`I-advisor-links-2026-08.md:277` — Entergy: IT ~80% / cooling ~18% / misc ~2%; EPRI: ~90%
electronically driven, cooling 20–40%) plus 2508.14318's "GPUs contribute more than 50% of
the provisioned power" at server level:

| Assumption | GPU swing 90% → facility swing |
|---|---|
| Entergy shares, GPUs = all of IT | **72%** |
| EPRI cooling-heavy (40% cooling), GPUs = all of IT | 54% |
| Entergy shares, GPUs = 50% of server power | 36% |
| EPRI cooling-heavy, GPUs = 50% of server power | 27% |

**A 90% swing on 80% of load is still a 72% facility-level swing.** Even the most generous
assumption leaves ~27%. Dilution alone does not make the facility smooth. The honest
version of the advisor's hypothesis is: **"other data-centre uses" dilute the percentage
but not the megawatts; only storage and software mitigation actually remove the swing.**

---

## 5. Q3 — Would a battery be fast enough? Yes, easily — and speed is not the problem

The answer is band-dependent, and the two apparently contradictory statements in the
literature resolve cleanly once split by mechanism:

- **Passive absorption improves with frequency** (capacitor impedance ∝ 1/ωC). arXiv
  2502.01647's oscilloscope traces confirm it: during GPU load drops the PSU input voltage
  "remains relatively stable, confirming that **local capacitors and PSU control loops
  effectively smooth some of the fastest edges**." 2508.14318 agrees: "**Higher frequencies
  are easier to filter out, compared to the lower frequencies.**"
- **Closed-loop control degrades with frequency** (sense → compute → actuate latency).
  Tesla's LLTF slide says measurement-based control "is ineffective at high frequencies due
  to control delay"; 2508.14318 supplies the number — NVIDIA datacenter GPUs expose power
  telemetry at **100 ms minimum latency** for the reliable counters, "too slow for a
  use-case where we would want to detect power swings at 20 Hz."

**In the measured band this is not close.** 0.2–3 Hz means periods of 0.33–5 seconds.
Grid-scale PCS response is tens of milliseconds, and full grid-forming response ~250 ms
(e.g. Kapolei/Megapack). A battery is one to two orders of magnitude faster than it needs
to be.

**The binding constraint is energy, not speed.** 2508.14318: "ramp-up and ramp-down can
require **very large capacitance** from the energy storage. Such large capacitance would be
very expensive from cost, rack-level space, and embodied carbon perspectives. Given that
these events happen rarely ... designing enough capacity for this does not necessarily pay
off." Their chosen architecture is **rack-level** storage — explicitly *not* facility-level,
because higher placement exposes UPSes and PDUs to the perturbation and the multiplexing
benefit does not exist for synchronous jobs (§3). NERC's guideline names the same trio:
"software mitigations, **GPU power smoothing**, and **rack-level energy storage**."

So the answer to the advisor is: **yes, comfortably fast enough; the reason it isn't simply
solved is capacity sizing and cost, not response time.**

---

## 6. Q5 — LLTF White Paper 2 (March 2026) and Reliability Guideline (May 2026)

Read for what `E-flexible-load.md:147` does not already carry: named bands, limits,
response-time requirements, and whether they cite a measurement source. The regulatory
timeline there is unchanged and is not repeated.

**The single most useful finding for this project — there are no limits.** WP2, Chapter 5:

> **Scope note added 2026-08-20 (§ 7.4).** This concerns **mandatory, continent-wide NERC
> Reliability Standards** and specifically **frequency-domain** limits. It stands. But
> **ERCOT proposed a time-domain criterion on 19 Feb 2026** — load power must not
> "repetitively exceed 10 MW change in a sliding time window of 5 seconds" — filling the gap
> bottom-up at one ISO. NERC is not wrong; the gap is being closed from below, by a
> different instrument than the one WP2 was assessing.

> "Large loads can be a source of significant forced oscillations in the **0.1 Hz to 30 Hz**
> range ... There are significant gaps when it comes to defining allowable limits for forced
> oscillations in terms of BPS reliability ... **there are no guidelines or limits by which a
> system owner/operator can identify that a given forced oscillation is a reliability risk.**"

WP2 further rejects the obvious substitute: "IEEE 519 guidance surrounding interharmonics is
of very limited applicability ... Power quality violations are not sufficient to indicate an
imminent reliability risk." And even when an oscillating load *is* detected, "there is no
established practice for determining whether the oscillation is a risk to reliability."

**Quantitative content actually present:**

| Item | Value | Source |
|---|---|---|
| Forced-oscillation band of concern | 0.1–30 Hz | WP2 Ch.5 |
| Electromechanical (inter-area/local) sub-band | **0.1–2 Hz** | Guideline Ch.5 |
| SSCI/SSTI range | >5 Hz | WP2; Guideline |
| Allowable oscillation limit | **none exists** | WP2 Ch.5 |
| Ramp-rate limit | none specified; guideline only recommends TOs "establish operational load ramp rate limits (e.g., MW/min)" | Guideline fn.29 |
| Overfrequency ceiling for load-loss events | 60.5 Hz (Eastern), 60.6 Hz (others); ERCOT 60.4 Hz transient | Guideline Ch.4 |
| Monitoring requirement | FR/DDR at the HV side of the main transformer, specs "similar to PRC-002 and PRC-028" | Guideline Ch.1 |

**The measurement gap is regulatory, not just ours.** PRC-002-5 requires DDR output
recording at ≥30 samples/sec — Nyquist 15 Hz, meaning the mandated instrument can *barely*
resolve the 14.7 Hz Dominion event and cannot resolve the 5–30 Hz band properly. The
guideline concedes it: "**Accurate characterization of frequency signals above 5 Hz may
require point-on-wave measurements.**" Standard synchrophasor infrastructure is not adequate
for the fast band. Nobody — including NERC — is currently measuring it as a matter of course.

WP2 cites four technical sources for converter-driven stability, all measurement-based:
*Data Center Power System Stability — Part I*, *ERCOT experience with Sub-synchronous Control
Interaction*, *Large Load Oscillation Event* (ERCOT, a crypto-mining facility), and the
14.7 Hz Dominion study.

---

## 7. Follow-up (2026-08-20, second pass) — the three open items

Chasing § 9's open items turned up material that **updates three claims above**. Nothing
here overturns the headline; two items get sharper and one gets properly qualified.

### 7.1 There are now FOUR measured grid events — and every one is a control interaction

§ 1 said the 14.7 Hz Dominion study was the only independent grid-side measurement. It is
not. ERCOT's January 2026 LLWG deck lists four field items:

| Event | Frequency | Attributed cause |
|---|---|---|
| Meta data centers, 2017 | **49 Hz and 71 Hz** | DC-link voltage control in the server PSU |
| ERCOT, Jul–Oct 2024 | **23 Hz** (onset above ~320 MW load) | PSU **power-factor-correction (PFC) control**; **fixed by a firmware upgrade** |
| Dominion Energy, 2024 | **14.7–14.8 Hz**, 4% p-p on 115 kV | data centre **UPS systems**; emerged as four nearby hydro units ramped down |
| Dominion Energy | **1–11 Hz** | EPRI event, details not public |

**The pattern is the finding.** Every measured data-centre oscillation on a real grid is a
**power-electronics control interaction** — PSU DC-link control, PFC control, UPS control —
not GPUs stepping in unison. The ERCOT 23 Hz event was cured by a **firmware upgrade**, with
no change to the workload. This strengthens § 1's caveat considerably: it is not one
ambiguous event, it is four out of four.

⚠️ **But state the limit of that claim precisely.** ERCOT's deck also lists "**LEL normal
load profile (Dec. 2025)**" as a field item, noting that LEL load profiles "**may** lead to
continuous torque perturbations on synchronous generator shafts." So:

- **Workload-driven oscillation has never been observed to cause a grid event.** ✅ survives.
- **"Nobody has field-measured workload load profiles" does NOT survive** — ERCOT has them,
  as of December 2025. The torque consequence is *analytical and prospective*, not an
  observed generator failure. ERCOT's own framing is "repeated, low-amplitude excitation of
  torsional modes," with the open question being long-term mechanical fatigue.

Source: `Replicating Real-World 23-Hz Oscillations Caused by Large Electronic Loads`
(arXiv 2605.17190, IEEE PES IBR/IBL SSO Task Force, incl. ERCOT authors). It also records a
data-availability finding worth keeping: **no dynamic model for the oscillating load was
ever submitted by the load entity or its TSP**, "due to limited operational experience and
lack of industry accepted dynamic model for LELs."

### 7.2 Coherent scaling is now INDEPENDENTLY MEASURED, not just operator-asserted

§ 3 rested on Microsoft/OpenAI/NVIDIA asserting that synchronous jobs do not multiplex. That
claim is now corroborated by an independent measurement:

> **arXiv 2604.07345** (National Laboratory of the Rockies), H100 nodes, **0.1-second
> resolution**, public dataset. For both Llama-2 70B fine-tuning and Stable Diffusion
> training, **power variability (standard deviation) increased LINEARLY with node count.**

Linear sd growth is the ρ = 1 coherent case. Independent sd growth would be `sqrt(N)`. **This
is a measured scaling exponent from a national lab, not a vendor assertion** — the single
strongest new item in this pass, and it upgrades § 3 tier 1 from assertion to measurement.

⚠️ **Scope discipline:** this is measured *within one job*, across node counts up to 16. It
confirms **tier 1 only**. It says nothing about tier 3 (cross-facility).

### 7.3 Cross-facility independence — progress, but still no field measurement

§ 9's item 1 was "completely unmeasured." That is now too strong, but the gap survives.

**arXiv 2606.13853** (Michigan State) derives the general result that supersedes § 3's binary
framing:

```
Var(L_agg) = N*sigma^2 * [1 + (N-1)*rho]
```

ρ = 0 recovers the incoherent `sqrt(N)` case; ρ = 1 recovers the coherent `N` case;
everything between interpolates. **Correlation dominates once (N−1)ρ > 1, i.e. ρ > 1/(N−1).**

| Facilities in a region | ρ below which independence still holds |
|---|---|
| 10 | ρ < 0.11 |
| 50 | ρ < 0.020 |
| 100 | ρ < 0.010 |

⚠️ **The ρ in this formula must be computed on BAND-LIMITED fluctuation, and this matters
enormously.** Two facilities can have hourly load correlated at 0.9 — same weather, same
workday — and have *exactly zero* phase coherence in their all-reduce cycles at 0.2–3 Hz.
Conflating envelope correlation with in-band phase coherence is the same timescale error
this note exists to correct, just running the other way. Sorting the candidate drivers:

| Driver | Acts in-band (0.2–3 Hz)? |
|---|---|
| Shared orchestration platform / synchronized job launch | **Plausibly yes** |
| Same model architecture → similar iteration period | **Plausibly yes** |
| Thermal constraints | Ambiguous — needs thought, not assumption |
| Weather, workday, market prices, model release cycles | **No** — envelope only |

2606.13853's own list is "shared orchestration platforms, thermal constraints, or workload
scheduling," and it names **Northern Virginia** as the archetype where dense hyperscale
concentration shares transmission corridors.

**⚠️ Its ρ ≈ 0.4 is IMPOSED, not measured** — an RTDS sensitivity study on the IEEE 39-bus
test system, not field data. So the honest status of item 1 is: *characterized by simulation
under an assumed ρ, plus a conservative regulatory design assumption (§ 7.4). There is still
no field measurement of cross-facility phase coherence.* The gap is narrower, not closed.

### 7.4 ERCOT has proposed an actual numeric limit — but this does NOT contradict § 6

§ 6's central finding was that **no allowable-limit standard exists**. That stands, correctly
scoped. WP2 concerns **mandatory, continent-wide NERC Reliability Standards** and specifically
**frequency-domain** limits (allowable spectral magnitude at a given frequency). That gap is
real and unfilled. What has changed is that **a single ISO is filling it bottom-up with a
time-domain criterion**:

> **ERCOT proposed requirement (LLWG, 19 Feb 2026):** *"Load power shall not repetitively
> exceed **10 MW change in a sliding time window of 5 seconds**."* Revision request to be
> submitted **Q2 2026**. Not yet in force.

Supporting framework, developed with Electranix:
- **Endurance Limit (EL)** — max continuous cyclic shaft torque a generator tolerates.
- **Load Shape Ratio (LSR)** — amplification from terminal power variation to shaft torque.
- **MCTV = EL / LSR** — e.g. EL 0.1 pu, LSR 10 → MCTV 0.01 pu → **1 MW allowable oscillatory
  power at a 100 MW generator's terminals**.
- **IFBL** — max load variation such that no nearby generator exceeds its MCTV; **the most
  limiting generator sets the limit for that location.**

**What the 10 MW / 5 s rule actually means, converted.** A 5-second window contains at least
a half-period of anything at or above 0.1 Hz, so the full peak-to-peak swing is reachable
inside the window. **For the entire measured 0.2–3 Hz band the rule is therefore a flat 10 MW
peak-to-peak amplitude cap** — ERCOT's "Option 3," uniform rather than frequency-dependent.
(Verified numerically; below ~0.1 Hz it begins to relax — 14.1 MW at 0.05 Hz, 32.4 MW at
0.02 Hz.)

Against reported magnitudes — 2508.14318's "10 MW to >100 MW," Musk's 10–20 MW, Google's
"tens of MW" — **a frontier-scale cluster is non-compliant by up to an order of magnitude as
proposed.** Mitigation stops being optional and becomes an interconnection precondition.

The 10 MW figure is **deliberate, not arbitrary**: ERCOT's screening across all ERCOT buses
≥100 kV found few affected generator stations at 5 MW of injected variation rising to roughly
50 by 25 MW, and they picked the knee of that curve.

**And the allocation consequence is the most interesting thing in this pass.** ERCOT states
that if one large load operates at its IFBL, *"any additional LEL connected at the same
location must maintain minimal or flat power variation, as the first LEL already consumes the
allowable variation margin."* **Oscillation headroom is being defined as a scarce, exhaustible,
first-come-first-served locational resource** — structurally the same shape as transmission
congestion, which is the project's one surviving live price finding. Note this is a
*conservative design assumption* that variations add at a location; it is not a measurement
of whether they actually do (§ 7.3).

### 7.5 EPRI 3002033303 — dead end, closing it

The product page is JavaScript-rendered and returns only the site shell to any fetch; the
report remains paywalled at $25,000. **Stop spending time here.** Sibling product
**3002033424, *Data Center Load Shape Library: 2025 Edition***, is a possible substitute lead
if facility load shapes are ever needed.

### 7.6 rs-7943457 verified against primary sources (2026-08-20, third pass) — real, but two claims below needed correcting

The § 9 lead below was checked against the actual PDF (WebFetch 403'd on Research Square;
a UA'd `curl` got through) and the underlying GitHub repo, not just search snippets.

- **Confirmed real and usable.** Ahmed Abd Elaziz Elsayed, Abdullah Azhar Al-Obaidi, Hany E.Z.
  Farag (**York University / IESO**), *Characterization of high-resolution AI data center
  training workloads on single and multiple GPU nodes*, Research Square `rs-7943457`, posted
  2025-10-29, **CC BY 4.0**. 32 sessions on H100/B200 8-GPU nodes + 40 on RTX 3060, 1.8M+
  samples, per-GPU power/utilization/memory/temperature. Data and code are genuinely open —
  not paywalled, not vaporware — at
  `github.com/Ahmed-Elsayed95/High-resolution-AI-Data-Center-Training-Workloads-Dataset`.

- ⚠️ **Correction: NOT a companion to arXiv 2604.07345.** Different institution and authors
  entirely — York/IESO, not the National Laboratory of the Rockies. They are independent,
  unrelated efforts that happen to converge on the same conclusion. That is *better* evidence
  than a companion dataset would be: a second, independent measurement rather than one paper's
  own supplementary data.

- ⚠️ **Correction: "sampled at 50 Hz (20 ms)" is the polling interval, not the true update
  rate, for the node-scale (H100/B200) power channel.** Downloaded one real session (B200,
  45,000 rows) and checked directly: 80.7% of consecutive `gpu0_power_W` samples are identical
  to the previous sample. Average run-length of repeated values ≈ 5.17 → implied true refresh
  interval ≈ **103 ms (~9.7 Hz)**, not 20 ms. This lands almost exactly on Microsoft's own
  number in 2508.14318 ("100 ms minimum latency for the reliable counters," § 5) — an
  independent replication of that spec, on different hardware, by an unrelated group, two years
  later. **This is the same shape of trap as the Pecan Street Austin 1-second zero-fill**
  (note M): a monitor polling faster than the sensor actually updates. It does not kill the
  dataset's value — Nyquist ≈ 5 Hz still comfortably covers the entire measured 0.2–3 Hz band
  and NERC's 0.1–2 Hz reliability sub-band — but any future claim of resolving up to 25 Hz, or
  reaching into the 5–30 Hz SSCI/SSTI range, does not survive and must not be made.

- ✅ **New, independent evidence for § 3's coherence claim.** Same downloaded session:
  cross-GPU power correlation within the 8-GPU node, full 15-minute session — ρ(gpu0,gpu1) =
  0.994, ρ(gpu0,gpu4) = 0.995. A third, independent line of evidence for tier-1 coherence
  (after Microsoft's self-report in § 3 and the NLR node-count linear-scaling result in § 7.2)
  — and the first one this project computed itself rather than read off someone else's paper.

- **Net effect.** Still the first dataset the project could hold that sits inside the measured
  0.2–3 Hz band and would let the project compute a spectrum rather than cite one. Still
  node-scale only — does not touch the cross-facility gap (§ 7.3). Cite the effective rate as
  **~10 Hz for GPU power**, not 50 Hz, in any future write-up.

- **Deferred, deliberately.** The actual spectral analysis (periodogram/PSD of node-aggregate
  power across several sessions, checking where energy concentrates against the claimed
  0.2–3 Hz band) has **not** been done. This pass verified the dataset is real, corrected two
  claims about it, and got one coherence number essentially for free — nothing more. Analysis
  is scoped for a fresh session.

### 7.7 The deferred spectral analysis, done (2026-08-20, fourth pass)

Six node-scale sessions were downloaded from the verified rs-7943457 GitHub repo: B200 and
H100 diffusion baselines, B200 and H100 LLM baselines, and a B200 LLM batch-size arm (bs2,
bs32, seq length fixed at 2048) to test mechanism. Two of the six — a "Sequence_length_cut"
seq1024/seq4096 pair pulled for a second mechanism test — turned out not to be independent
measurements (trap below) and were dropped, leaving **4 independent sessions** for the band
analysis (2 diffusion + 2 LLM baselines) plus the **bs2/bs16/bs32** triple for the mechanism
question.

Method: sum the 8 per-GPU power channels to node-aggregate power, trim 5% head/tail (this
data duty-cycles for the entire session, so an adaptive "flat-region" detector collapses to
under 2% of the session and is the wrong tool here), linearly detrend, then compute both a
Welch PSD (`nperseg=16384`, for stable band-fraction integrals) and a single high-resolution
periodogram (for peak location). Peak location is cross-checked against the time-domain
autocorrelation's **tallest** peak within a 1–30 s lag window — the earliest local maximum
lands on the ACF's second harmonic and manufactures a false disagreement. Parseval's check
(`∫PSD df` vs `Var(signal)`) held to within 0.3–6.3% (ratio 0.94–1.01) on the 4 analyzed
sessions — the bs2 mechanism session is a separate case, noted in Finding 4.

**Finding 1 — nothing above ~3 Hz, as designed, not as evidence.** ≤0.04% of variance sits
above 3 Hz in every session. This is the ~103 ms / ~9.7 Hz effective refresh from §7.6 doing
exactly what it should: **the instrument is mute above ~5 Hz by construction.** This is not
evidence the workload lacks fast content — it cannot be cited that way.

**Finding 2 — none of the 4 sessions reproduce the 0.2–3 Hz "measured" band, and none can
adjudicate the scale→frequency question.** Dominant periods run 8.5–15.9 s (periodogram and
autocorrelation agree to within 1–2% on all 4). This 8-GPU/ZeRO-3 node runs slower than the
spectrum arXiv 2508.14318 measured on jobs spanning thousands of GPUs. One node, one scale,
one parallelism strategy cannot tell us whether frequency rises or falls with job size — it
only says this node, this way, cycles slower than the frontier-scale operator band. This
supersedes the §1 "bigger jobs are slower" extrapolation as something this dataset could
confirm — it can't, in either direction. **But it does not weaken the §1/§2 point about
1-second data:** this node's content sits at 0.06–0.12 Hz, *below* 0.2 Hz, which is exactly
where a 1-second average retains the most amplitude (94% at 0.2 Hz, per §2's boxcar table).
Whether the true operator band is 0.2–3 Hz (thousands of GPUs) or slower still (this one
node), 1-second sampling remains inside or above the content, not below it.

**Finding 3 — workload type is the strongest driver of how much energy reaches the
regulator-relevant bands, on this one harness.**

| Session | Dominant period | Var < 0.1 Hz | Var in 0.1–2 Hz (NERC) | Var in 0.2–3 Hz (measured) |
|---|---|---|---|---|
| B200 diffusion | 11.4 s | 72.9% | 26.3% | 5.4% |
| H100 diffusion | 15.9 s | 75.6% | 24.3% | 7.3% |
| B200 LLM (bs16) | 8.5 s | 0.4% | 99.5% | 36.8% |
| H100 LLM (bs16) | 13.5 s | 45.7% | 54.2% | 31.2% |

Diffusion puts only 5–7% of its variance in the measured band and 73–76% below even the wide
NERC band. LLM training puts 31–37% in the measured band and 54–99% in the NERC band. This
describes two workload types on **one 8-GPU harness** — not a general claim about diffusion
or LLM training.

**Finding 4 — the cycle is a duty-cycle effect that requires idle time, and it can vanish
entirely.** B200 LLM batch-size arm, sequence length fixed at 2048: at **bs2**, GPU memory is
210,488 MB and **idle_frac (samples below 40% of session peak) = 0.0%** — the workload never
idles. (Its spectral estimate is not trustworthy enough to lean on separately: Parseval is off
by 17% there, consistent with slow wander a linear detrend didn't remove, and the
periodogram's "peak" at 0.0025 Hz is a period close to the record length — not a resolved
periodicity. The claim rests on `idle_frac`, not on the spectrum.) At **bs16**, memory
339,466 MB, idle_frac 18.1%, period 8.5 s. At **bs32**, memory 481,584 MB, idle_frac 12.1%,
period 9.1 s (agrees with autocorrelation to within 1%, Parseval ratio 1.000). Memory scales
correctly with batch size across all three, confirming they are genuinely distinct runs. The
bs16→bs32 shift (8.5→9.1 s, same direction as the 2× batch increase) is **n=1 per cell and
suggestive only** — it is not a measured scaling law. The load-bearing result is bs2's
`idle_frac`: **the workload that never idles is also the one with no resolvable cycle**,
which rules out a fixed logging/checkpoint cadence as the mechanism.

**Trap — two of the six downloaded files were not independent measurements.** The repo's
"Sequence_length_cut" sweep (seq1024, seq2048-baseline, seq4096) was pulled to extend the
mechanism test, but per-GPU memory usage is identical to under 0.01% across all three
(339,444–339,466 MB) despite a claimed 4× change in sequence length — activation memory
should scale materially with sequence length and does not; power mean/std/max are likewise
identical to under 0.1%. These three files are not independent training runs, or the label
does not match what executed. seq1024 and seq4096 were dropped. Anyone reusing this repo's
`Sequence_length_cut` directory should verify before trusting the label.


## 8. What this changes for the report

1. **The headline must be two-part** (§0). One half is arithmetic and must be labelled as
   such; the other half (EPRI 94%/88%) is the real finding.
2. **The null is now stronger and better founded.** "We measured at the wrong resolution"
   becomes "no public dataset at any resolution could have measured this, and here is the
   closed-form reason." The phenomenon is real, well-characterized by its operators, and
   structurally invisible to every market and grid feed the project holds.
3. **The stated band should be corrected to 0.2–3 Hz measured / 0.1–2 Hz reliability-relevant**,
   with 0.1–30 Hz cited as the vendor/regulatory envelope rather than the measured spectrum.
4. **The "bottom 1%" limitation was wrong** — restated as ~11% linear / ~34% log against
   the measured band. ✅ Done: correction block added to note M § 3.4 and carried into the
   08-24 agenda. The committed 08-19 agenda was deliberately **not** retro-edited.
5. **Note M's √N cancellation claim is correct for homes and must not be generalized.**
   Add the coherence caveat explicitly — it is the single sharpest sentence available and
   it pre-empts the obvious reviewer objection.
6. **"Lack of data" is now evidenced, not asserted.** The best spectrum measurement is
   operator self-reported and unreplicated; NERC's own guidance depends on it; and NERC
   admits no allowable-limit exists and that standard instrumentation cannot characterize
   the fast band.
7. **rs-7943457 is verified, real, and usable (§ 7.6)** — but cite it at ~10 Hz effective
   for GPU power, not the nominal 50 Hz, and as an independent dataset, not a companion to
   2604.07345.
8. **The project's first self-computed spectrum (§ 7.7) says the operator band is not
   universal.** 4 independent node sessions all cycle slower (8.5–15.9 s dominant period)
   than the 0.2–3 Hz band 2508.14318 measured on thousands-of-GPU jobs — one small node
   cannot confirm or deny how frequency scales with job size, only that it doesn't reproduce
   the frontier-scale spectrum on its own. Workload type is the strongest driver of how much
   variance reaches the regulator-relevant bands on this harness (diffusion 5–7% in the
   measured band vs. LLM 31–37%). The cycle is a genuine duty-cycle effect requiring idle
   time — it vanishes entirely at batch size 2, where the GPU never idles.

## 9. Open items

*Updated 2026-08-20 after the second pass (§ 7).*

- **Cross-facility phase coherence — narrowed, NOT closed.** Now characterized by simulation
  under an **imposed** ρ ≈ 0.4 (arXiv 2606.13853, RTDS on IEEE 39-bus), plus ERCOT's
  conservative regulatory assumption that variations add at a location (§ 7.4). **There is
  still no field measurement of in-band ρ between facilities**, and the in-band/envelope
  distinction (§ 7.3) rules out most intuitive arguments for correlation.
- ✅ **RESOLVED — the two unread sources.** *Data Center Power System Stability — Part I*
  (CSEE JPES 2022, 8(2):403–419) is PSU impedance modelling, and its lineage runs directly
  into the ERCOT/Dominion event analyses in § 7.1. ERCOT's LEL-SSO material is read and
  written up in § 7.4; it over-delivered — it contained a proposed numeric limit.
- ❌ **CLOSED AS DEAD END — EPRI 3002033303.** JS-rendered page, $25,000 paywall (§ 7.5).
  Substitute lead: EPRI 3002033424, *Data Center Load Shape Library: 2025 Edition*.
- ✅ **VERIFIED AND ANALYSED — see §§ 7.6–7.7.** Research Square `rs-7943457` (York
  University/IESO, CC BY 4.0, GitHub-hosted): **32 AI training sessions on H100 and B200
  8-GPU nodes** plus 40 on RTX 3060, **>1.8M samples**, per-GPU power/utilisation/memory/
  temperature. **Independent of arXiv 2604.07345** (different institution), not a companion.
  GPU power's *effective* rate is **~10 Hz, not the nominal 50 Hz** — the polling interval is
  20 ms but the true telemetry refresh is ~103 ms, matching Microsoft's own 100 ms figure. A
  quick check found ρ ≈ 0.994–0.995 cross-GPU power correlation within one node — independent
  confirmation of the § 3 coherence claim. The project's own periodogram of 4 independent
  node sessions (§ 7.7) found none reproduce the 0.2–3 Hz operator-measured band (all cycle
  slower, 8.5–15.9 s dominant period), workload type drives how much variance reaches the
  NERC 0.1–2 Hz band (diffusion 5–7% vs. LLM 31–37%), and the cycling is a duty-cycle effect
  tied to idle time that vanishes at batch size 2. Still **node-scale, not facility-scale** —
  does not close the facility gap (§ 7.3).
- **Long-term torsional fatigue** is the open engineering question ERCOT itself names: the
  consequence of repeated low-amplitude torque excitation is prospective, not observed.
- **Diffusion's duty-cycle mechanism is untested.** §7.7 Finding 4's mechanism test (does the
  cycle require idle time?) only ran on the LLM batch-size arm. Diffusion's own 11.4/15.9 s
  dominant periods have no equivalent sweep behind them — unknown whether the same
  idle-time-dependent mechanism applies, or something else drives the (much larger) fraction
  of diffusion's variance sitting below 0.1 Hz.

## 10. Follow-up (2026-08-28) — the cycle is slow, its edges are not

The §7.7 spectrum says the node cycles every 8.5–15.9 s. What that number hides is the
speed of each transition inside the cycle: `scripts/aidc_edges.py` (10%→90% of the
swing, middle 80% of each baseline session) finds falls of 0.70–1.79 s and rises of
0.68–1.56 s across steps of 2.2–4.5 kW, i.e. 2–5 kW/s for one 8-GPU node, well above the
sensor's ~103 ms floor. So the telemetry does reproduce the *abruptness* the operators and
EPRI's footnote describe (repeated slowly, not oscillating at 0.2–3 Hz); the in-band
variance shares in §7.7 are those edges. Numbers, method and the report wording changes
are in `decisions.md` § 2026-08-28.

## 11. Follow-up (2026-08-28) — the node's step at training-job scale

`scripts/aidc_scale.py` divides the §10 step by the node's eight GPUs (0.28–0.56 kW per
GPU, 61–69% of the high level; ramp 0.19–0.61 kW/s per GPU) and multiplies by the GPU
count of real jobs under perfect coherence: 16,384 GPUs (Llama 3 405B) → 4.5–9.2 MW,
24,576 (a Meta 2024 cluster) → 6.8–13.8 MW, 100,000 (Colossus phase 1) → 28–56 MW. A
10 MW step takes ~18k–36k synchronized GPUs and a 20 MW step ~36k–72k — the "tens of
thousands of GPUs" jobs of arXiv 2508.14318 — so the operators' 10–20 MW is consistent in
magnitude with the node telemetry (their >100 MW needs ~180k–360k). Caveats: the sessions
run below rated power (0.4–0.86 kW/GPU at the high level vs. 0.7 kW H100 / 1 kW B200),
cross-node coherence is assumed, and the figure is pre-mitigation load. Numbers and report
placement in `decisions.md` § 2026-08-28 (second entry).
