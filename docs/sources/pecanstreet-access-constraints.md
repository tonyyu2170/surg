# Pecan Street Dataport — Access Routes and Discovered Constraints

Source: **empirical probing on 2026-08-13** — the approval emails, the
logged-in Dataport site, a live JupyterHub session, the Jupyter contents
API, and Pecan Street's public docs/GitHub. Analogous to
`ukpn-api-constraints.md` / `gridstatus-api-constraints.md`: this file
records what the source *forces on us*. What we chose is in
`decisions.md`; reference docs vendored from the vendor live in
`docs/reference/pecan-street/`.

Pecan Street is a research nonprofit instrumenting ~1,000 volunteer
homes with circuit-level eGauge monitors. **This is residential data,
not data-centre data** — its role here is the advisor's XFRA headroom
question and the only power-quality series we hold (see "Research fit").

## Account / tiers

- Account: `tonyyu2029@u.northwestern.edu`, approved 2026-08-13
  ("Dataport Account Approved", dataport@pecanstreet.org). Tier:
  **University Free** (badge on the logged-in dashboard).
- The approval email is generic; tier limits are discoverable only by
  logging in and reading the site.
- **Direct PostgreSQL access is PAID-ONLY.** Dashboard verbatim: "With
  paid Database Access, you can directly connect to Dataport's
  database." The free tier gets **no DB credentials**; the `/access`
  URL redirects to the dashboard. All GitHub examples that open a
  SQLAlchemy `postgresql://` connection (`other_datasets.metadata`,
  `electricity.eg_realpower_1min`) require that paid tier.
- The **2 kHz waveform release** (Oct 2025, 16-bit) is licensed
  separately; it is NOT on the free tier's pages. Whether any of it can
  be had on university terms is an open licensing question
  (shinson@pecanstreet.org / licensing@pecanstreet.org — asked
  2026-08-11, no reply as of 08-13).

## The four access surfaces (free tier)

1. **`dataport.pecanstreet.org/academic`** ("Data → Residential Data")
   — static download links for the curated 25-home bundles (see
   inventory). Plain HTTPS downloads, no tooling. Page footer is
   © 2019; the CA text ("started collecting 1-second data this year")
   dates the page itself to 2019.
2. **JupyterHub, `jupyterhub.pecanstreet.org`** — login = Dataport
   username/password + **email MFA code** each browser session. Runs a
   standard jupyter/user image (user `jovyan`; Python 3, R, C++
   kernels, terminal, git). **The same bundles are pre-staged at
   `/shared/Dataport-Data/` in queryable `.sqlite3` form** — 315 GB
   including the 1-second sets — plus `/shared/tutorials/` (their
   SQLite querying tutorials) and a checkout of `JupyterHub-Examples`.
   The intended free-tier workflow is: compute there, export results.
3. **The Jupyter REST surface** — an API token from
   `jupyterhub.pecanstreet.org/hub/token` authorizes
   `GET /user/<name>/api/contents/<path>` (JSON listings with exact
   byte sizes) and `GET /user/<name>/files/<path>` (raw download,
   supports HTTP `Range` resume). This is the scriptable bulk route and
   what `scripts/pecanstreet_fetch.py` uses. Token lives in `.env` as
   `JUPYTER_API_KEY`. ⚠️ The username in the URL is the email with
   punctuation stripped: `tonyyu2029unorthwesternedu`.
4. **Public docs** (no login): Data Dictionary, Dataport FAQ, and
   Schema Definitions are public Google Docs linked off the dashboard;
   the "Metadata Report" is `dataport.pecanstreet.org/static/metadata.csv`
   (publicly downloadable — which is how we had it pre-approval).

No rate limits or quotas were observed or documented on any of these;
the binding constraints are file sizes and transfer speed (~3 MB/s
observed from JupyterHub `/files/`), not calls. The gridstatus scarcity
discipline does not apply.

## The headline trap: metadata describes 2,072 homes; the tier delivers ~75

`metadata.csv` (both the vendored copy and the fresher one at
`/shared/Dataport-Data/metadata.csv`) inventories the **full research
DB**: 2,072 dataids, 1,198 with 1-min data, 406 current into 2026, 25+
cities. **None of that is reachable on the free tier.** What is
reachable is the static release below: **25 Austin + 25 New York + 23
California homes (2019-era) + a Sept-2023 Puerto Rico set.** Any
analysis plan drafted from metadata.csv counts must be re-based against
the actual bundle contents.

## Inventory (verified via contents API, 2026-08-13)

Staged at `/shared/Dataport-Data/` on JupyterHub; the same regional
bundles are downloadable from `/academic`. Each regional dataset exists
in three formats — `csv.gz`, `.sqlite3`, `.tar.gz` — **the same data
three ways**; the sqlite3 files are pre-indexed for querying in place
and are 13–14× larger than the csv.gz.

| Region (build date) | 15-min | 1-min | 1-sec |
|---|---|---|---|
| Austin, 25 homes (Apr 2021) | 23 MB | 263 MB | 4 files, 13.9 GB total (csv.gz); sqlite3 43–47 GB *each* |
| New York, 25 homes, 6 months (Apr 2021) | 12 MB | 127 MB | 4 files, 6.8 GB (csv.gz) |
| California, 23 homes (Apr 2021) | 14 MB | 172 MB | **none** (never released) |
| Puerto Rico (Oct 2023) | 5 per-metric files, ~4.7 MB | 5 files, ~69 MB | 5 files, ~1.81 GB |

- **Puerto Rico is per-metric, not per-region-bundle**: separate files
  for `realpower`, `apparentpower`, `current`, `thd`, `angle` at each
  resolution, all stamped `09-2023`. It is the only power-quality
  panel we have access to anywhere in the project.
- Top-level extras: `metadata.csv` (616 KB, newer than the 2019-era
  vendored copy), `metadata.sqlite3`, `audits_and_surveys.zip` (513 KB),
  `ev_and_weather.zip` (6.1 MB), `indoor_temp_data.zip` (359 MB),
  `project_specific_datasets.zip` (3.7 KB), `soils_data/` (empty-ish),
  `pr_homes/` (per-home repackaging of the PR series: 15min 4.8 MB /
  1min 69 MB / 1sec 1.79 GB tarballs — presumed redundant with the
  per-metric files, **not independently verified**).

### Server-side defects found

- **`pr_angle_09-2023_1sec.csv.gz` is 20 bytes** — a broken upload.
  The PR 1-second panel is effectively **four** metrics; phase angle
  exists only at 15-min and 1-min.
- `1s_data_newyork_file2.sqlite4` — zero-byte stray file.
- NY 1-sec files 2–4 are ~⅓ the size of file 1; whether that is
  compression or coverage is undetermined.

## Data semantics (from vendored docs + official examples)

- **`dataid` = home × resident pair.** A move spawns a new dataid.
- Circuit-level columns per home (`grid`, `solar`, `air1`, `car1`,
  `office1`, …), average real power in kW per interval; timestamps
  are interval starts.
- **Schema drift:** the older Metadata Dictionary describes `use` and
  `gen`; current data uses `grid` + `solar` (+`solar2`, `battery1`,
  `energy_storage_system_*`). Whole-home use must be reconstructed
  (`use = grid + solar`), and not every home has a `grid` circuit —
  in the full-DB metadata, 136 of 1,198 1-min homes lack it. Check
  per-bundle before assuming.
- **Time columns (`localminute`, `local_15min`) are LOCAL time** —
  metadata min/max timestamps land on 05:00/06:00 UTC = Austin
  midnight. Handle DST explicitly; never treat as UTC.
- 2012–2017 data is real power only; **2018+ adds apparent power,
  current, phase angle, THD** — but on the free tier that richness is
  only realized in the PR set.
- **Intervention contamination:** many homes were experiment subjects
  (CCET pricing trial, Baseline behavioral, Verizon low-income
  apartments, LG appliance swap, SHINES solar+storage, Civita texts).
  Program membership is in metadata; screen before treating any home
  as untouched observation.
- Oddities: `building_type` includes "Sales" (2 rows) and 3 mobile
  homes in the full metadata.

## Acquisition status — PULLED AND VERIFIED 2026-08-13 (two passes)

`.venv/bin/python scripts/pecanstreet_fetch.py` → `data/raw/pecanstreet/`,
mirroring the server layout. **37/37 files, 22 GiB, 0 failures, every
file byte-size-identical to the server manifest** (the script verifies
each transfer and resumes partials via `Range`; the big pass survived
two mid-run kills with zero loss).

Pass 1 (~2.9 GB): all regional 15-min + 1-min csv.gz; the full PR
per-metric set (including the 20-byte broken angle file, kept
deliberately as evidence); all top-level extras listed above.
Pass 2 (~19.4 GB): **Austin 1-sec (4 files) + NY 1-sec (4 files)** and
`pr_homes/pr_15min/metadata.csv` — a **full-DB metadata snapshot
(1,927 rows incl. 49 Puerto Rico homes**, Culebra/Bayamon/Vega Baja/
Humacao/San Juan…), the join key for the PR per-metric files. ⚠️ Its
first data row is an embedded data-dictionary row (cells = column
descriptions) — drop on load; and its PR rows have blank 1-sec
time-range fields even though PR 1-sec data exists.

**Still deliberately skipped** (re-runnable by extending `MANIFEST`):

- `.sqlite3` / `.tar.gz` duplicates of data we took as csv.gz;
- `pr_homes/` tarballs and per-metric files (~1.9 GB) — **confirmed
  redundant**: byte-identical sizes to the per-metric files pulled,
  including the same 20-byte broken 1-sec angle file.

## Research fit and scope limits

- **Not data-centre data.** Do not file it as the missing ERCOT
  facility source, and the "subtract residential from total load"
  agenda idea cannot work — this is a ~25-home-per-region sample.
- Its real jobs: (a) the **XFRA headroom question** — does household
  spare panel capacity vanish exactly at summer peak? Austin 1-min
  circuit-level data is the right instrument; (b) **power quality** —
  the PR THD/current/apparent-power series is our only foothold in
  that territory; (c) residential contrast to the UKPN facility-DC
  flatness finding (J-note).
- Vintage limits: Austin/NY/CA bundles are 2019-era (built Apr 2021);
  nothing recent. NY is only 6 months. PR is a Sept-2023 snapshot.
- 1-second sampling = 1 Hz → Nyquist 0.5 Hz: even the 1-sec sets barely
  graze the 0.1–30 Hz band where industry locates DC-induced
  volatility (I-note framing). Only the paid 2 kHz waveform release
  covers that band.

## Not verified

- Whether JupyterHub home directories persist / are quota'd; whether
  long-running notebooks are culled. Treat the hub as scratch compute.
- The exact PR *panel* membership: the pr_homes metadata snapshot lists
  **49 Puerto Rico homes**, but which dataids actually appear in the
  per-metric files (and their coverage) has not been counted from the
  data itself.
- Whether the fresher `/shared` `metadata.csv` (616 KB vs 604 KB local)
  adds homes/columns — **diff it before reusing the old orientation
  numbers.**
- Whether the `/academic` PR links serve the same files as `/shared`
  (sizes were unlabeled on the page).
- Jupyter API token lifetime/expiry policy.
- NY 1-sec files 2–4 being ~⅓ the size of file 1 — compression vs
  coverage, undetermined until the files are opened.
