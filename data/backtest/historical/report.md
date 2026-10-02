# Older flood rainfall diagnostic (2015–2023 search)

This is a retrospective rainfall diagnostic, not a forecast backtest. Thresholds are unchanged.

Accepted 5 area-days across 5 storms. Other candidate decisions: {'pending': 3, 'context': 4}. Search gaps are not dry days.

Original rules: {'threshold_not_triggered': 4, 'threshold_triggered': 1}. Sensitive rules: {'threshold_triggered': 5}.

## 2017-07-08 — lekki

Channels contemporary rain/flood reporting corroborated by the July 8 Punch home-flood report. Embedded older tweets in Channels are not used to date this episode.

ERA5 local-day rainfall: **11.6 mm**. Peaks: {'1': 1.7, '3': 4.1, '6': 7.1, '24': 13.0} (keys are accumulation hours; values mm).
Original: **threshold_not_triggered**; sensitive: **threshold_triggered**.
Grid: [6.5, 3.5]; distance from pilot point: 6.6 km.

Ikeja station reported amount: 17.02 mm; 24h_report; flag G. 24-hour-only comparison: {'rainfall-screen-v1': 'threshold_not_triggered', 'rainfall-screen-sensitive-v2': 'threshold_triggered'}. Station distance: 22.1 km.

Evidence: [source 1](https://www.channelstv.com/2017/07/08/lagosians-lament-as-flood-hits-lekki-victoria-island/), [source 2](https://punchng.com/video-flood-lekki-residents-abandon-homes/)

## 2020-06-18 — lekki

BusinessDay describes Thursday flooding on Admiralty Way; TheCable independently dates widespread Lekki flooding to June 18. Flood presence, not exact onset; rain also fell the previous day.

ERA5 local-day rainfall: **22.8 mm**. Peaks: {'1': 5.0, '3': 9.4, '6': 12.9, '24': 23.5} (keys are accumulation hours; values mm).
Original: **threshold_not_triggered**; sensitive: **threshold_triggered**.
Grid: [6.5, 3.5]; distance from pilot point: 6.6 km.

Ikeja station reported amount: 73.91 mm; 24h_report; flag G. 24-hour-only comparison: {'rainfall-screen-v1': 'threshold_triggered', 'rainfall-screen-sensitive-v2': 'threshold_triggered'}. Station distance: 22.1 km.

Evidence: [source 1](https://businessday.ng/news/article/flooding-economic-activities-paralysed-as-nature-empties-its-bowel-in-lagos/), [source 2](https://www.thecable.ng/photos-flood-takes-over-parts-of-lagos/)

## 2021-07-16 — lekki

Nairametrics says it confirmed Friday rainfall flooding and explicitly lists Lekki. Area-day evidence only. Its broader Ketu mention is insufficient to create an Ikosi-Ketu observation.

ERA5 local-day rainfall: **114.2 mm**. Peaks: {'1': 16.5, '3': 47.9, '6': 84.5, '24': 114.2} (keys are accumulation hours; values mm).
Original: **threshold_triggered**; sensitive: **threshold_triggered**.
Grid: [6.5, 3.5]; distance from pilot point: 6.6 km.

Ikeja station reported amount: 50.04 mm; partial_period; flag E. 24-hour-only comparison: {'rainfall-screen-v1': 'unknown', 'rainfall-screen-sensitive-v2': 'unknown'}. Station distance: 22.1 km.

Evidence: [source 1](https://nairametrics.com/2021/07/16/flood-hits-parts-of-lagos-ogun/)

## 2022-06-18 — ikosi-ketu

Punch reporters describe their own observations on Saturday in an article published Sunday June 19. Rainfall cause and named-area flood presence supported; no onset time inferred.

ERA5 local-day rainfall: **15.9 mm**. Peaks: {'1': 2.0, '3': 4.2, '6': 7.4, '24': 17.1} (keys are accumulation hours; values mm).
Original: **threshold_not_triggered**; sensitive: **threshold_triggered**.
Grid: [6.5, 3.5]; distance from pilot point: 16.6 km.

Ikeja station reported amount: 105.92 mm; 24h_report; flag F. 24-hour-only comparison: {'rainfall-screen-v1': 'threshold_triggered', 'rainfall-screen-sensitive-v2': 'threshold_triggered'}. Station distance: 8.0 km.

Evidence: [source 1](https://punchng.com/rain-pounds-lagos-houses-roads-flooded-property-destroyed/)

## 2023-09-16 — lekki

Punch reports Saturday morning rainfall flooding and explicitly names Lekki residents. Article is published Sunday September 17; use September 16. Broad named-area evidence, not a specific weather-grid point.

ERA5 local-day rainfall: **13.8 mm**. Peaks: {'1': 2.8, '3': 6.1, '6': 8.1, '24': 13.8} (keys are accumulation hours; values mm).
Original: **threshold_not_triggered**; sensitive: **threshold_triggered**.
Grid: [6.5, 3.5]; distance from pilot point: 6.6 km.

Ikeja station reported amount: unavailable; missing_or_incomplete; flag missing. 24-hour-only comparison: {'rainfall-screen-v1': 'unknown', 'rainfall-screen-sensitive-v2': 'unknown'}. Station distance: 22.1 km.

Evidence: [source 1](https://punchng.com/residents-groan-as-downpour-leaves-lagos-flooded-properties-destroyed/)

## What this changes

On 2 accepted days, the original rules stay low on ERA5 while the nearby station's reported 24-hour amount crosses the original 50 mm threshold. Different measurement locations and reporting periods prevent calling these exact ERA5 errors. They do show that rainfall source choice can change the conclusion about threshold adequacy.

Do not tune on this selected positive sample. Obtain rainfall aligned to pilot locations and periods, and monitored non-flood intervals, before estimating operational performance. The search included 2015–2023, but this first pass found scoreable days only in 2017, 2020, 2021, 2022 and 2023. Other years remain unresolved, not flood-free.

## Limits and reproducibility

- Public-news review by an assistant, not independent field verification or an exhaustive flood census.
- ERA5 is revised coarse-grid reanalysis, not measured street rainfall or a forecast available before the event.
- Both pilot points can share a grid cell. Do not count them as independent rainfall measurements.
- A day-level threshold coincidence is not proven advance warning. Floodwater may persist from previous days.
- No verified negative sample: no false-alarm ratio, accuracy, or operational detection claim.
- Station daily totals cannot test 1/3/6-hour rules; partial/missing reports remain unknown.

[ERA5 provider documentation](https://open-meteo.com/en/docs/historical-weather-api). [Review register](review.json).

Offline rerun: `.venv/bin/python -m backend.historical_rainfall run`. One-time imports/retries: `.venv/bin/python -m backend.historical_rainfall download`.
