# docs/

Grouped by what a document *is*, not by when it was written.

```
decisions.md                 log of record — APPEND-ONLY
Yu_Tony_SURG_Grant_Proposal.md

sources/                     how to get the data, and what it will not give you
  <pjm|gridstatus|ukpn|entsoe>-api-constraints.md
  entsoe-endpoint-reference.md
  data-catalog.md
  availability/              what each market publishes, and how far back
    <caiso|ercot|ieso|isone|miso|nyiso|spp>-data-availability-research.md
    cross-iso-data-availability-summary.md
    cross-iso-phase2-recon-verification.md

research-notes/              findings — see INDEX.md
  A-…  …  L-…                main chronological series
  EU-0-…  …  EU-5-…          European scoping batch
  external-context-research-2026-08.md

plans/                       designs, implementation plans, pre-regs, agendas
                             flat and date-prefixed; the newest
                             *-advisor-meeting-agenda.md is the micro status
specs/                       design docs from the superpowers workflow

reference/                   vendored source material, not written here
  pjm-manuals/               M03/M11/M12, Data Miner 2 guide, pjm-lmp-formation.md
  pecan-street/              Dataport metadata dictionary + metadata.csv
  papers/
```

## Where to look first

| Question | File |
|---|---|
| What has been decided, and why | `decisions.md` — check before re-deriving anything |
| What has been found | `research-notes/INDEX.md` |
| What is being worked on right now | newest `plans/*-advisor-meeting-agenda.md` |
| Can I pull X from market Y | `sources/availability/` |
| Why did that API reject my request | `sources/*-api-constraints.md` |

## Rules

- **`decisions.md` is append-only.** Never edit or delete an entry — write a
  new one that supersedes it, citing the old by date and title.
- **Path citations inside `decisions.md` predate the 2026-08-12 reorganisation**
  and were not rewritten, because rewriting them would have violated the rule
  above. The entry dated 2026-08-12 (*"`docs/` reorganised; path map for
  citations frozen in this log"*) maps every old path to its new home.
- Research notes are provisional until `decisions.md` rules on them.
