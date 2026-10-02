# Offline evidence workflow

Run from the repository root with `.venv/bin/python -m backend`. The website can be stopped.
Nothing here trains a model or approves an event automatically. Review evidence before inspecting its predictions.

## Collect historical sources

```sh
# Discover candidate links in a publisher's RSS, Atom, or XML sitemap.
# Replace the example address with a real publisher index.
.venv/bin/python -m backend backtest-news-discover --url https://publisher.example/sitemap.xml --terms flood,lekki,ketu,lagos --limit 20 > /tmp/news-links.json
.venv/bin/python -m backend backtest-source-collect /tmp/news-links.json

# Or collect a specific article, including an existing reviewed source.
.venv/bin/python -m backend backtest-source-add --url https://www.thecable.ng/photos-commuters-stranded-homes-submerged-as-flood-ravages-lagos/
# Local saved reports/photos/observations work without internet or a public URL.
.venv/bin/python -m backend backtest-source-add --file /path/to/observation.jpg
# A saved article or report may retain its original URL.
.venv/bin/python -m backend backtest-source-add --url https://publisher.example/report.pdf --file /path/to/report.pdf
```

`source-collect` also accepts `{"urls":["https://..."]}`. Discovery matches any supplied term
in the URL/title; it does not search article bodies. Sitemap indexes follow same-host children,
up to `--limit` documents. `truncated` and `errors` disclose incomplete discovery. Use
publisher archive sitemaps and URLs found through search/Groundsource review for older years:
feeds generally contain only recent stories. This is not an exhaustive web search or flood census.
Sitemap `lastmod`, feed dates, and article publication dates **never** become flood dates.

`data/backtest/sources.json` records source IDs, content versions, URLs, retrieval times,
checksums and local paths. Original bytes and readable HTML/text extracts live in
`cache/sources/`; scripts/styles are excluded, but navigation/boilerplate may remain.
PDFs and photos are cached for manual review; no OCR is performed. Repeated URLs reuse verified
cache entries; `source-add --refresh` explicitly fetches a new version without replacing old ones.
HTML metadata is unverified publisher metadata. Access-denied pages can return HTTP 200, so
check the saved content before reviewing it. Failed bulk fetches are recorded in `collection.json`.
`discovery.json` retains discovery batches. Do not bypass paywalls or access controls.

## Import observations and review

Copy this **synthetic schema example**, replace all values with actual observations, and save
as `/tmp/observations.json`. `source_ids` must contain IDs returned by source collection.
Historical news and prospective resident/gauge-site observations use the same register.

```json
{
  "events": [{
    "id": "replace-with-real-observation-id",
    "area_id": "lekki",
    "storm_id": "replace-with-stable-storm-id",
    "source_ids": ["REPLACE_WITH_SOURCE_ID"],
    "groundsource_ids": [],
    "location": "Verified street or neighborhood",
    "location_precision": "street",
    "location_note": "Explain how the evidence places this location inside the pilot area",
    "description": "Describe the observation, including depth if known",
    "flooded": true,
    "cause": "rainfall",
    "start_at": "2026-09-01T10:00:00+01:00",
    "end_at": "2026-09-01T11:00:00+01:00",
    "timing_precision": "hour",
    "timing_note": "Explain what establishes the onset interval, separately from publication time",
    "observation_kind": "onset"
  }]
}
```

```sh
.venv/bin/python -m backend backtest-events-import /tmp/observations.json
.venv/bin/python -m backend backtest-events-list --status pending
.venv/bin/python -m backend backtest-event-review replace-with-real-observation-id --decision /tmp/decision.json
```

A decision file contains `status` (`approved`, `rejected`, or `context`), `reviewer`, and a
meaningful `review_note`; it may also correct the observation fields above. Example shape:
`{"status":"approved","reviewer":"Reviewer name","review_note":"Explain the independent evidence actually checked"}`.
Only use approval after actually checking the source. Every correction to an already reviewed
entry requires `correction_reason` and appends the previous record to `review_history`.
Repeated identical imports are safe even after review; conflicting IDs fail atomically.
Do not edit the JSON register directly to bypass review. This is a local audit trail, not a
multi-user signed or tamper-proof review system; run one writer at a time.

Use the same storm ID for duplicate stories and observations from both areas. Syndicated
stories are not independent corroboration; explain attribution in the review note/evidence.
Precise timing alone is insufficient: `location_precision` must be `point`, `street`, or
`named_area` with a location explanation. Broad LGA and month/year observations belong in
`context`, with conservative timestamp bounds. Local times normalize to UTC.

A day-only observation uses `timing_precision: "day"`, `observation_kind: "flood_present_on_day"`,
`event_date: "YYYY-MM-DD"`, and the local day's bounds. It stays unknown for hourly scoring.
Hourly positive labels require `observation_kind: "onset"`; presence at a time does not prove onset.
For observed non-flood intervals, use `flooded: false`, `observation_kind: "monitored_interval"`,
nonzero start/end bounds, and `monitoring_method`. Record the street actually monitored;
one dry street does not prove the entire pilot area was dry. Approval is the reviewer's
explicit judgment of relevance to the evaluated area, not automatic spatial verification.
Hourly negatives must cover entire matched forecast windows; daily negatives need full-day
monitoring. No report, missing observations, and cloudy/inconclusive imagery remain unknown.

Collect prospective observations on a defined schedule, including rainy days without flooding.
Cache observation notes, images, or operational logs locally as sources. Keep private source
files local; no upload or public publication occurs. Existing event records retain legacy
provenance until explicitly revised through this workflow; legacy review records are preserved.

## Independent rainfall diagnosis

Keep using `backtest-rainfall-audit FILE...` for NOAA GSOD station CSVs. For local gauges or
satellite estimates, cache the original export as a source, then prepare a canonical CSV:

```csv
start_at,end_at,latitude,longitude,station_or_grid,kind,product_version,rainfall_mm,quality
2026-09-01T09:00:00Z,2026-09-01T10:00:00Z,6.45,3.47,local-gauge-1,gauge,logger-export-v1,12.5,valid
2026-09-01T10:00:00Z,2026-09-01T11:00:00Z,6.45,3.47,local-gauge-1,gauge,logger-export-v1,,missing
```

`kind` is `gauge` or `satellite`; `quality` is `valid`, `missing`, or `suspect`. Values are
**interval totals in millimetres**, not mm/hour rates. Record the actual station/grid coordinates
and source product version. IMERG half-hour estimates are supported for storage; convert rates
to totals using the product documentation before import. To compare with hourly forecasts,
explicitly aggregate complete consecutive half-hours into hourly totals. Never fill a missing
half-hour with zero. No automatic NASA authentication, HDF/NetCDF conversion, or interpolation
is performed; use a provider CSV export or a documented local conversion.

```sh
.venv/bin/python -m backend backtest-source-add --file /path/to/original-rainfall-export.csv
.venv/bin/python -m backend backtest-rainfall-import /path/to/normalized-rainfall.csv --source-id REPLACE_WITH_SOURCE_ID
.venv/bin/python -m backend backtest-rainfall-check
.venv/bin/python -m backend backtest-run
.venv/bin/python -m backend backtest-run --resolution daily
```

Rainfall imports are checksum-cached; missing amounts remain null. The offline diagnostic
writes `results/rainfall-comparison.json`: observed and forecast interval totals, signed
forecast-minus-observed errors, station/grid distance, matched run/cycle, and exclusion reasons.
It uses the latest run simulated available before interval start, at most 18 hours old, with
complete hourly coverage over `(start,end]`. Distances are disclosed, not treated as proof of
spatial equivalence. Comparisons are not pooled into an accuracy claim. Observations never
replace archived forecast inputs or establish flood/non-flood labels.

Replays verify managed evidence checksums and include source/review provenance in audit outputs.
Same cached inputs and code produce the same results. Keep `sources.json`, `events.json`, their
referenced caches, and code together when archiving a reproducible evaluation.

2025 examples have already informed sensitive-v2 development. They are not an untouched test
set for that version. Preserve original v1 thresholds and reserve future storms before any
further tuning; group all observations from a storm in the same partition.

Checks: `.venv/bin/python -m unittest backend.test_evidence backend.test_backtest backend.test_daily_backtest backend.test_pilot -q`.
