# Research notes — index

Two independent series share this directory. Filenames are stable and cited
from `docs/decisions.md`, so they are not renamed; use this index instead.

- **`A`–`L`** — the main chronological series. `A`–`H` were compiled together
  in the 2026-08-07 external-context sweep (parent doc:
  `external-context-research-2026-08.md`); `I`–`L` are later one-off cuts,
  each answering a specific question.
- **`EU-0`–`EU-5`** — a single parallel batch, 2026-08-11, scoping whether the
  eight-market study could extend to Europe. `EU-0` is the synthesis; read it
  first and the numbered notes only for detail.

Desk research and data analysis are mixed together. The **Kind** column says
which: *desk* notes cite public documents and pull no data; *analysis* notes
compute from files in `data/`.

## Main series

| Note | Kind | What it answers |
|---|---|---|
| `A-primary-verify.md` | desk | FERC co-location order, Virginia SCC cases, PJM RTEP Window 1 — checked against the primary PDFs, not trade press. |
| `B-loudoun-geography.md` | desk | Physical and electrical geography behind the GOOSECRE / LOUDOUN / PLEASANTVIEW / SKFFSCRK pnodes. |
| `C-capacity-forecast.md` | desk | PJM resource adequacy and load forecast context, 2025–2026. |
| `D-jlarc-lbnl.md` | desk | JLARC Report 598 and LBNL rate-impact claims, source-checked against the full reports. |
| `E-flexible-load.md` | desk | Flexible / curtailable data-centre load — state of play. |
| `F-jan2026-driver.md` | desk | What drove the January 2026 PJM/DOM price escalation. Answer: Winter Storm Fern. |
| `G-control-pnodes.md` | desk | Candidate control pnodes outside the DOM zone/LDA. |
| `H-event-catalog.md` | desk | Dated PJM/DOM grid-stress and market events, 2023-02 → 2026-06, to replace a coarse time-of-day filter. |
| `I-advisor-links-2026-08.md` | desk | The five advisor-suggested links read in full — EPRI headroom, NERC LLTF, PJM forecasting, EPRI peak-use. Source of the timescale framing. |
| `J-ukpn-flatness.md` | analysis | Is data-centre load actually spiky? 96 metered UK sites, half-hourly. Median daily peak/trough 1.05. |
| `K-ireland-dc-shape.md` | analysis | Did Irish load shape change as data centres reached 23.7% of consumption? ⚠️ Qualified by `L` — read `L` § 8 first. |
| `L-solar-metering-artifact.md` | analysis | Is the midday flattening a solar metering artifact? 12 European zones. Also finds the Dutch control's 2023-04 definitional break. |
| `M-pecanstreet-xfra-headroom.md` | analysis | Do homes have idle panel capacity for a 12.5 kW XFRA compute node? 73 homes, 1-min and 1-sec. The answer hinges entirely on service size — 100% at 200 A, 4% at 100 A — which the data never records. |
| `external-context-research-2026-08.md` | desk | Umbrella doc for `A`–`H`: BTM, data-centre pipeline, transmission, emerging tech, policy. |

## European scoping batch (2026-08-11)

| Note | What it answers |
|---|---|
| `EU-0-synthesis.md` | What the five below jointly imply. **Start here.** |
| `EU-1-market-geography.md` | European data-centre market geography and scale. |
| `EU-2-grid-data-availability.md` | What load and price data is obtainable, at what granularity. |
| `EU-3-datacenter-disclosure.md` | Data-centre-*specific* disclosure — what exists and whether it is reachable. |
| `EU-4-market-structure.md` | What breaks, changes, or survives when the method moves off US ISO/RTOs. |
| `EU-5-policy-renewables.md` | Policy and renewables, including the H_solar question that `L` went on to test. |

## Related

- `docs/decisions.md` — the log of record. Findings here are provisional until
  an entry there rules on them.
- `docs/sources/` — where each feed comes from and what it will not give you.
- `docs/plans/` — the plan or agenda that commissioned a given note.
