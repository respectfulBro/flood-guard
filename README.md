# FloodGuard Lagos research pilot

Private rainfall screening for the next 24 hours, using the existing React/Vite website and a small FastAPI/SQLite service. **This is not yet a validated flood predictor.** The historical register now contains four public-source-reviewed flood observations across three storms. The original screen missed all four; the new sensitive rules flag all four after development on these known examples. That is not independent validation. There is no trained model or claimed accuracy; monitored non-flood days and more independent storms are still missing.

## Run locally

Requires Python 3.11+ and the Node version supported by the installed Vite.

```sh
npm install
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
npm run build
npm run pilot
```

The pilot command asks for a private password of at least 16 characters, without saving it. Open **http://127.0.0.1:8000**, sign in as **researcher**, and use that password. All pages, assets, and API endpoints require authentication. `PILOT_USER` and `PILOT_PASSWORD` can instead be supplied as environment variables. No mock login, SMS registration, or uploads are exposed in the pilot.

The service fetches weather on startup and hourly while running, including when no browser is open. First load may show unknown risk until the first fetch completes. Run **one worker** to avoid duplicate schedulers. For an external scheduler, set `PILOT_INGEST=0` and run `.venv/bin/python -m backend ingest` hourly instead. The command returns nonzero if either area fails.

For frontend editing, leave the backend running and use `npm run dev`. Vite is bound to loopback and proxies `/api` to port 8000. Authenticate at the backend URL first; the built website on port 8000 is the private end-to-end preview.

## Offline presentation demo

After installing dependencies and collecting the historical caches once, run:

```sh
npm run demo
```

This builds the website, recomputes both historical reports from local caches, asks for a private password (16+ characters), and serves http://127.0.0.1:8000. Sign in as `researcher`. No weather downloads run. Keep the terminal open; Ctrl-C stops the server.

Start at **Historical replay** (`/replay`): choose the archived-run comparison or the older ERA5 diagnostic, select an event, and switch sensitive/original rules. **Strategy and results** (`/performance`) includes detailed evidence, candidate reviews, and background alert counts. The sensitive version already flags all four recent and five older documented days; no additional threshold reduction was needed. These remain separate, development-reviewed experiments, not nine verified advance warnings.

Demo observations are pending records in `data/demo.sqlite3`; the real `data/pilot.sqlite3` is not used. Demo area pages and map markers show the first cached sensitive-rule event for each area, explicitly labelled historical with its date. Current weather is not downloaded. Use historical replay to choose other events. Map tiles and external source links need internet; replay, locally served audit JSON, area lists, and observation submission work without it.

If cached data is absent, first use the import commands below with network access. Do not delete `data/backtest/cache` or `data/backtest/historical/cache` before the demo. Reports and source caches are intentionally not committed; copy them with their manifests when moving the demo to another machine. Missing/stale analysis is explicitly marked in the interface.

Quick journey: replay a Lekki event → compare original and sensitive windows → inspect source evidence → record a synthetic observation → see its pending-review confirmation. Do not treat synthetic demo submissions as research evidence.

## What is implemented

- Two **candidate** representative locations: Lekki and Ikosi-Ketu. These are not verified neighborhood boundaries or flood extents. They returned distinct ECMWF IFS weather grid points in the initial live check; Ikoyi was not added because it shared the Lekki grid point.
- Fixed `ecmwf_ifs` rainfall feed through Open-Meteo, UTC hourly millimetres, three past and three forecast days. Past values are model estimates, not gauge observations. Raw responses, request URLs, source metadata, receipts, algorithm version, thresholds, and generated forecasts are archived.
- Four six-hour windows starting at the next full hour (at most an hour after issuance). Each uses the maximum trailing 1/3/6/24-hour accumulation ending within that window. A value labelled 10:00 by the provider represents rainfall ending at 10:00.
- Original v1 moderate/high thresholds in mm: 1h 10/20, 3h 20/40, 6h 30/60, 24h 50/100. New live forecasts use sensitive v2: 1h 2.5/20, 3h 5/40, 6h 7.5/60, 24h 12.5/100. Any threshold crossing raises the screen. These are engineering defaults to exercise the pipeline, **not locally established flood thresholds**. No soil-moisture, drainage, terrain, tide, river, or ensemble adjustment is represented as implemented.
- Model metadata is checked before and after retrieval; new runs wait at least ten minutes for propagation. Metadata identifies the advertised run, not a guaranteed exact run for every hourly value in the seamless API. Prospective inputs are evaluated exactly as received, not reconstructed from later weather.
- Latest receipt older than two hours, model initialization older than eighteen hours, future timestamps, or expired validity makes a forecast stale. Failed ingestion preserves the previous archive, records an error, and does not refresh its age. Missing data never means low risk. The webpage checks the service every minute.
- Persistent observations, source links, onset/monitoring intervals, flood causes, manual review, stable storm IDs, and evaluation partitions. Pending records cannot affect metrics. Review happens through the local CLI, not a public approval endpoint.

## Event register and evaluation

Record events at `/report`. Use Lagos local time (UTC+1). For a flood record the earliest/latest plausible **onset**, not the duration of standing water. For a non-flood observation record the period that was actually monitored. Name the street/location in the description and cite evidence; a general city bulletin does not establish a neighborhood outcome.

```sh
.venv/bin/python -m backend reports
.venv/bin/python -m backend review 1 --status approved --storm lagos-2026-example --reviewer researcher --note 'Describe the independently checked location, timing, cause and evidence here'
.venv/bin/python -m backend evaluate
.venv/bin/python -m backend replay
```

The example review command is a template, not a seeded event. Confirm the record and replace its identifiers/evidence before running. Review decisions are preserved; already reviewed records cannot be silently overwritten. Use the same storm ID across duplicate observations and affected areas. A storm cannot be approved into multiple partitions. Conflicting labels for the same area/storm are excluded from scoring and must be resolved in the evidence register before a formal evaluation.

Evaluation matches one archived forecast per area/storm at 6, 12, and 18 hours before the earliest possible onset, allowing up to two hours of receipt age. Moderate/high screens count as alerts. It records hits, misses (including low-risk forecasts with no alert), false alarms on confirmed non-events, correct negatives, and exclusions. Lead time is calculated only for hits. No forecast coverage is an exclusion, not an invented miss. Unreviewed events, non-rainfall floods, intervals over six hours, and timing ranges spanning conflicting classifications cannot establish timing skill.

The dashboard has no fabricated results. It shows sample counts, results by area/lead, and descriptive Wilson intervals. Because reports are selective and areas can share storms, these intervals are not evidence of independent samples or operational reliability. Unverified alert outcomes remain unknown; consequently the reported false-alarm ratio applies only to the reviewed sample.

**Research protocol before fitting anything:** collect systematic non-event observations alongside events. Freeze chronological train/validation/test cutoffs in a versioned dataset manifest after assessing coverage; assign entire storms to one partition. Use earlier records to fit a rainfall baseline, select thresholds on validation data prioritizing ≥80% detection with a desired ≤40% false-alarm ratio, then freeze code, thresholds, inputs, and event register before evaluating the later test period. Preserve a seasonal-frequency benchmark and rainfall-only baseline for comparison. Only introduce calibrated logistic regression if data support independent training/calibration/testing and it improves held-out performance. The current four positive observations and zero monitored non-flood days are insufficient for those fitting and validation steps.

Use `evaluate --split train|validation|test|prospective` to inspect the selected partition. Do not call the current fixed defaults a trained or calibrated model. Prospective monitoring needs at least a wet season and sufficient verified storms; sample adequacy and independent review are required before any public warning rollout. No historical prediction is backfilled from revised observations or reanalysis.

## Source audit and remaining data work

Audit date: 2026-09-25. Live requests succeeded for both candidate points and produced complete hourly mm series. Local raw responses and metadata are in `inputs`; use `replay` to reproduce outputs. Source documentation and blockers are recorded in [data/sources.json](data/sources.json).

- [Open-Meteo forecast documentation](https://open-meteo.com/en/docs) and [ECMWF feed](https://open-meteo.com/en/docs/ecmwf-api): live feed usable, but global grid resolution cannot establish street-level flood skill. [Metadata documentation](https://open-meteo.com/en/docs/model-updates) explains update propagation and timestamp meanings.
- [Open-Meteo terms](https://open-meteo.com/en/terms): the free service is for non-commercial use, subject to limits and CC BY 4.0 attribution. This private research setup assumes non-commercial use. Recheck licensing before commercialization. Attribution is displayed in the footer.
- [Single Runs API](https://open-meteo.com/en/docs/single-runs-api): historical importer and offline replay are available; see Offline historical backtest below for measured coverage and hindcast limitations.
- [NASA IMERG](https://gpm.nasa.gov/data/imerg): candidate observed-rainfall context, with Early Run latency around four hours. No IMERG feed is connected yet; no immediate nowcasting claim is made.
- [NiMet State of the Climate 2024](https://nimet.gov.ng/downloader?file=admin%2Fuploads%2Fpublications%2F67a3837604c26_2024+State+of+the+Climate.pdf): candidate historical event evidence. Direct download returned a JavaScript browser check during this audit. Search snippets were not converted into labels; precise onset, location, causes, and source content still need verification.
- [NEMA Lagos assessment](https://nema.gov.ng/nema-collaborates-with-lagos-state-on-2022-2023-flood-assessment-and-preparedness/): supports investigating Lagos flood hotspots, but lacks the precise event times/non-event monitoring needed here. A hazard assessment or forecast bulletin is not an observed event register.

Terrain, built-up land, drainage condition, lagoon/tide effects, gauges, and ensemble skill are not yet audited sufficiently to add as model features. Candidate point locations remain provisional: the historical reports establish flooding in named areas, not at the exact weather points. The live register is separate from the four historical daily observations.

The map uses standard OpenStreetMap tiles for interactive pilot viewing, with visible attribution and browser caching. Follow the [tile policy](https://operations.osmfoundation.org/policies/tiles/); no offline download or prefetching is implemented. The original CARTO tile URL returned an API-key-required watermark during the browser check and has been replaced.

## Checks and operation

```sh
npm run test:backend
npm run build
npm run lint
.venv/bin/python -m backend replay
```

Backend tests cover units/hour boundaries, missing/invalid input, archive persistence, duplicate ingestion, staleness/failures, event matching, uncertain timing, authentication, report validation, and exclusion of pending evidence. Synthetic test observations use temporary databases and never enter the live register.

`npm run typecheck` currently has a pre-existing unsupported `ignoreDeprecations: "6.0"` setting. Overriding it to `5.0` also reveals existing missing Leaflet typings and untyped shared UI component props. Build/lint and the backend checks are the passing gates; a repository-wide JavaScript typing cleanup has not been folded into this pilot.

`GET /api/health` reports per-area freshness and ingestion failures. It is authenticated and returns `status: degraded` when coverage is missing/stale. Monitor that status and process logs when hosting. The database defaults to `data/pilot.sqlite3` (ignored by Git); set `FLOODGUARD_DB` to persistent storage. Back it up with SQLite's backup API or stop the service before copying the database and its WAL files. Never use an ephemeral filesystem for a long-running pilot.

No hosted deployment is configured. To host privately, run one worker behind an HTTPS reverse proxy with the same authentication enforced by this service, a strong environment-provided password, persistent storage, process restart supervision, and an authenticated health monitor. The local `serve` command deliberately binds only to loopback. Evaluation and wet-season validation require ongoing collection; installing the app does not complete that research.

## Offline historical backtest

The historical backtest is separate from the live SQLite pilot. It reuses `core.predict`
with unchanged thresholds. You do **not** need the website or server running.

```sh
# Small real-data smoke run; include at least a day before the period you want to score.
.venv/bin/python -m backend backtest-download --start 2024-07-01 --end 2024-07-03
# Download the public Groundsource parquet once and extract candidate records (~667 MB).
.venv/bin/python -m backend backtest-groundsource
# After reviewing evidence in data/backtest/events.json, replay locally with no network.
.venv/bin/python -m backend backtest-run
```

The importer requests four initialization times daily. A missing run is recorded in
`data/backtest/cache/gaps.json`; the download command exits nonzero if any requested
run fails. Successfully cached runs remain usable, and rerunning skips their verified
checksums. The July 1–3, 2024 smoke check found 00/12 UTC runs but the 06/18 UTC requests
returned HTTP 400. Availability must be measured rather than assumed from the nominal
model schedule. Download in short date ranges before attempting entire years.

Single Runs currently returns rainfall starting at initialization, with no antecedent
hours despite `past_hours`. Replay combines the newest cached run's forecast with
rainfall from earlier cached runs where antecedents are required. Only runs initialized
at or before the selected run are used. Each prediction records all contributing run
checksums. This is **modelled antecedent rain**, not measured rainfall. Runs without
complete inputs are excluded with reasons; download at least one preceding day for
warmup. The simulated issue time is initialization plus six hours.

[Open-Meteo's documentation](https://open-meteo.com/en/docs/single-runs-api) labels the
March 2024 onward Cycle 49R1 archive as **hindcasts**, followed by Cycle 50R1 from May 12,
2026 at 06 UTC. Thus the 2024/2025 results test these archived model outputs, not the
weather forecasts actually available to users in those years. Keep 2024 exploratory and partial
2026 separately reported by cycle. The original 2025 holdout has since been inspected during
sensitive-v2 development; it is not an untouched test for that version. Reserve future storms
before further tuning.
No threshold fitting is performed by these commands.

Groundsource outputs `data/backtest/cache/groundsource/candidates.json`. This is a spatial
search for polygons intersecting a broad Lagos box (2.7–4.4°E, 6.3–6.8°N), not an official
boundary. It can include nearby places or very broad polygons. The published file contains
UUIDs, dates and geometries, **no article URLs or place names**. Independently find supporting
articles before assigning a pilot area. Candidate GeoJSON geometry, day precision and
intersected pilot points are retained; intersection alone does not establish local flooding. Dataset metadata and a verified checksum are retained. Candidates are
never automatically approved. The Lagos history report and satellite dataset links are
in the event register; their often coarse timing is supporting context.

Copy the pending template in `data/backtest/events.json` into a new record, giving it a
unique ID. For floods, `start_at`/`end_at` bound the earliest/latest plausible **onset**, not
standing-water duration. For non-flood evidence, they bound an actually monitored period.
Use timezone-aware timestamps, a pilot area ID, evidence links, a stable `storm_id`, cause,
reviewer, review date and a meaningful verification note. `timing_precision` is `exact`,
`hour`, `day`, `month` or `unknown`; only the first two can support hourly onset scores, and
intervals wider than six hours remain unknown. Use `context` for coarse historical evidence.
Approve only after checking location, timing and cause independently of predictions.
No news report does not establish a non-flood event. The template itself cannot be approved.

Results are written to `data/backtest/results/`:

- `predictions.jsonl`: every replayed area forecast, risk windows and input-run provenance.
- `episodes.csv` and `episodes.jsonl`: one row per area/storm/lead with evidence, matched
  run, actual lead time, outcome and exclusion reason.
- `scores.json`: counts, descriptive intervals, results by year and model cycle, no-alert
  baseline, missing data, replay errors and code/input checksums.

At each target lead (6, 12, 18, 24 hours), matching selects the nearest issue within
three hours, always before onset. Actual lead is recorded, so nominal and actual lead
must not be confused. Moderate/high is an alert. A verified flood with an alert is a
hit; with low risk it is a miss. An alert over a verified non-flood interval is a false
alarm; low risk is a correct negative. Partial coverage, ambiguous timing, conflicting
labels and missing inputs stay unknown. Duplicate area/storm records become one episode;
all areas in the same storm share the earliest episode's calendar split.

Rates require at least five distinct scoreable flood storms in the relevant group.
This is a display floor, **not a claim of sufficient statistical power**. False-alarm
ratios also require verified non-flood evidence and describe only the reviewed sample.
Wilson intervals remain descriptive because areas within a storm are correlated. The
never-alert baseline has an undefined false-alarm ratio because it issues no alerts.
The hourly replay remains `inconclusive` because the current evidence establishes days, not precise flood onset times. Use the daily comparison below to inspect the documented outcomes.


## Real-data daily results and team demo

The completed first-pass review checked **87 pilot-overlapping candidates in 47 date groups**.
The audit in [review.json](data/backtest/review.json) records every group, unresolved dates,
duplicate stories, source links and the reasons for accepting or excluding evidence.
This was an assistant review of public reports, not human field verification or an exhaustive flood census.

[events.json](data/backtest/events.json) contains four accepted area-day observations:
Lekki and Ikosi-Ketu on July 3, 2024; Lekki on August 4 and September 16, 2025.
The daily run scored **0 detected, 4 missed, 0 excluded**, covering **3 distinct storms**.
There are no verified full-day non-flood observations, so false alarms are **not measured**.
These examples expose failures of the current rules; they do not establish overall accuracy.

Run using the already downloaded cache:

```sh
.venv/bin/python -m backend backtest-run --resolution daily
npm run build
PILOT_INGEST=0 npm run pilot
```

Open **http://127.0.0.1:8000/performance**, sign in as `researcher` with the password
chosen at startup, and inspect the historical daily section. It shows missed/detected
cases, forecast windows, original evidence links, review notes and the full candidate audit.
The server is needed to display the site; the backtest itself finishes offline and does
not need to keep running. Live hourly evaluation is shown separately below it.

To reproduce on a fresh checkout, download these small ranges first:

```sh
.venv/bin/python -m backend backtest-download --start 2024-07-01 --end 2024-07-03
.venv/bin/python -m backend backtest-download --start 2025-08-02 --end 2025-08-04
.venv/bin/python -m backend backtest-download --start 2025-09-14 --end 2025-09-16
```

The first four-case comparison used 28 valid runs; the subsequent sensitivity experiment expands the cache to a complete requested August plus warmup, with gaps retained. Some requested runs were missing/invalid;
commands record those gaps and can exit nonzero while retaining usable downloads.
All four evaluated cases had complete inputs. Raw caches and generated results are Git-ignored;
the reviewed evidence and code are versionable. Groundsource need not be downloaded again
just to replay these accepted cases.

For each observed day, daily replay issues at **00:00 Lagos time**, selecting the latest
cached run whose simulated availability (initialization + 6h) is no later than issuance.
Any moderate/high six-hour window counts as a daily alert. It reuses the unchanged rainfall
rules and never substitutes later observations. Evidence dates were selected before scoring.
A day label establishes flood presence, not exact onset: even a daily hit would not prove
advance warning. The 2024/2025 weather archive is model hindcast data, not the operational
forecasts delivered then. 2024 remains exploratory. The original unchanged v1 used 2025 as a fixed-threshold test sample; after inspecting those failures, v2 results on 2025 are development results, not held-out validation.

Outputs are `data/backtest/results/daily/report.json`, `predictions.jsonl` and `episodes.csv`.
The authenticated read-only `/api/backtest` serves the report and flags changes to its
code, register, candidate audit or cache manifest as stale until replayed. Daily results
never overwrite the separate hourly outputs. Percentages remain withheld below five
distinct storms; this display floor is not a sufficient sample-size claim.


## Sensitive rules and rainfall investigation

New ingestion uses **rainfall-screen-sensitive-v2**, lowering the moderate thresholds to
one quarter of v1 while preserving the high thresholds. This prioritizes detection as
requested. It is an explicit experimental policy, not an optimized or trained model.
Original forecasts are immutable; `replay` selects their stored version. Prospective
evaluation selects v2 only, so results from different rules are not pooled.

Measured development result: v1 misses all four accepted cases; v2 flags all four.
An always-alert rule also flags all four. These known positives alone do not establish
skill. Do not retune v2 using future evaluation storms; make a new version for further
changes. Because 2025 outcomes have now informed development, collect an untouched later
sample before claiming validation. No confidence percentage is emitted: API
`probability` remains null, and `confidence.status` is `unvalidated`. Fresh/stale input
status and rainfall intensity must not be interpreted as flood probability.

To reproduce the additional whole-month alert-frequency comparison:

```sh
.venv/bin/python -m backend backtest-download --start 2025-07-30 --end 2025-08-31
.venv/bin/python -m backend backtest-run --resolution daily
npm run build
npm run pilot
```

August has 58 usable area-days out of 62 requested. V1 alerts on 0; v2 alerts on 10
(17.2%). Nine v2 alerts have no reviewed outcome; they are **not confirmed false alarms**.
The month contains a known storm and is a diagnostic sample, not representative seasonal
performance. Missing coverage is shown explicitly. Comparisons and case outcomes are in
`report.json` under `sensitivity`, and on the Performance page. The original four misses
remain visible below the new comparison. New live forecasts appear after a successful
`ingest` or hourly fetch; restarting a server does not relabel archived forecasts.

The rainfall investigation imported NOAA GSOD station **65201099999 (Lagos/Ikeja)**:
[2024 CSV](https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/2024/65201099999.csv),
[2025 CSV](https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/2025/65201099999.csv),
[quality definitions](https://www.ncei.noaa.gov/data/global-summary-of-the-day/doc/readme.txt).
Raw files are cached with SHA-256 checksums. The compact auditable findings are in
[data/backtest/rainfall-audit.json](data/backtest/rainfall-audit.json).

- July 3, 2024: 155.96 mm, flag F (two 12-hour reports).
- August 4, 2025: 36.07 mm, flag E (one 12-hour report, not a full daily total).
- September 16, 2025: no station record in the retrieved file; it ends August 24.

This shows substantial rain at a nearby station for two storms, but does not quantify
forecast error at the pilot points: the station is 8 km from Ikosi-Ketu's representative
point and 22.1 km from Lekki's, and the reporting intervals differ from Lagos calendar
days. NOAA H/I flags and missing values are never interpreted as zero rainfall or no
flooding. The audit uses observations only after the event; they never enter a forecast.
NASA IMERG remains unconnected; its documented scientific download paths require account
registration. No satellite values or local gauge readings have been fabricated.

After downloading NOAA CSVs, regenerate the audit with:

```sh
.venv/bin/python -m backend backtest-rainfall-audit /path/to/2024.csv /path/to/2025.csv
.venv/bin/python -m backend backtest-run --resolution daily
```

### Outcome collection needed to measure confidence

Use the existing `/report` form at fixed, explicitly named locations in each pilot area.
Record floods and actively observed non-flood periods regardless of the forecast. Include
observer, street/coordinates, check times, gaps, onset bounds and evidence in the description.
Do not expand occasional checks into an uninterrupted dry day. Keep monitoring records
pending until reviewed through the existing CLI. Use one storm ID across affected areas.
Six-hour observed intervals can support the live evaluator; historical daily negatives
require a full monitored day. Missing observation periods stay unknown.

Request records from your local partners/NiMet/Lagos emergency services using this checklist:
date and timezone; named location or coordinates; flood onset/end uncertainty; cause;
observed rainfall amount, units, accumulation start/end and gauge location; quality flags;
method of observation; monitored non-flood intervals; source provenance and reuse permission.
These requests have **not** been sent. Continuous observations and permissioned institutional
records require cooperation from people on the ground. The app is ready to collect them,
but confidence cannot be calibrated until those outcomes exist.

## Collect sources and observations offline

See [the evidence CLI workflow](backend/EVIDENCE.md) for historical news discovery and caching,
pending event imports, auditable review corrections, prospective flood/non-flood observations,
and independent gauge/satellite rainfall imports and diagnostics. No website process is needed.

## Older flood rainfall diagnostic (2015–2023)

The [historical review and results](data/backtest/historical/report.md) are separate from
forecast validation. This initial news search accepted five area-days (2017, 2020–2023)
and retained seven uncertain/coarse candidates without scoring them. Fixed ERA5 hourly
reanalysis tests all four rainfall accumulation thresholds; nearby NOAA daily station
records provide a separate 24-hour-only check. Neither dataset establishes street-level
rainfall or advance-warning accuracy. No negative labels or threshold tuning are inferred.

```sh
# Download once or retry source failures; checksum-verified copies are reused.
.venv/bin/python -m backend.historical_rainfall download
# Subsequent runs are offline, with the website stopped.
.venv/bin/python -m backend.historical_rainfall run
```

The separate review register, versioned source metadata, raw caches, code hashes and
`historical/results/report.json` preserve provenance. Keep the referenced cache when
archiving this investigation. Missing sources/rainfall remain unknown; results are not
merged into live or archived-forecast performance metrics.
# flood-guard
