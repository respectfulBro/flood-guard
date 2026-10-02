# Why the four daily flood observations were missed

The original screen stayed below all four moderate-alert thresholds in every case. The calculations reproduce from the checksum-verified forecast cache. Four area-days represent three storms.

Moderate thresholds: 10 mm / 1 hour, 20 mm / 3 hours, 30 mm / 6 hours, and 50 mm / 24 hours. The screen uses maximum trailing accumulations, not just the local-day total.

## 2024-07-03 — ikosi-ketu

- Forecast local-day total: **16.2 mm**.
- Peak forecast accumulations: 1h: 3.5 mm, 3h: 8.1 mm, 6h: 10.6 mm, 24h: 16.4 mm.
- Shortfalls below moderate thresholds: 1h: 6.5 mm, 3h: 11.9 mm, 6h: 19.4 mm, 24h: 33.6 mm.
- Archive run: 2024-07-02T12:00:00Z; daily decision: 2024-07-02T23:00:00Z (midnight Lagos).
- Returned forecast grid is 3.4 km from the configured pilot point.
- Ikeja station: 155.96 mm; 24h_report; flag F. Station is 8.0 km from the pilot point.
- First sensitive-rule alert window: 2024-07-03T05:00:00Z to 2024-07-03T11:00:00Z (UTC). Add one hour for Lagos local time; this is the forecast window, not a proven warning lead.

The archive represents a much weaker rain event at the pilot grid than the substantial rainfall reported at Ikeja. Spatial/temporal rainfall mismatch is a plausible contributor; this is not a matched-location forecast-error measurement and does not establish the correct threshold.

Evidence: [source 1](https://punchng.com/10-states-battling-flooding-21-others-at-risk-fg-warns/), [source 2](https://www.pulse.ng/news/metro/sad-day-in-lagos-as-pupil-returning-home-from-school-swept-away-by-flood/fdr71td)

## 2024-07-03 — lekki

- Forecast local-day total: **18.2 mm**.
- Peak forecast accumulations: 1h: 6.8 mm, 3h: 11.8 mm, 6h: 14 mm, 24h: 20.6 mm.
- Shortfalls below moderate thresholds: 1h: 3.2 mm, 3h: 8.2 mm, 6h: 16 mm, 24h: 29.4 mm.
- Archive run: 2024-07-02T12:00:00Z; daily decision: 2024-07-02T23:00:00Z (midnight Lagos).
- Returned forecast grid is 8.7 km from the configured pilot point.
- Ikeja station: 155.96 mm; 24h_report; flag F. Station is 22.1 km from the pilot point.
- First sensitive-rule alert window: 2024-07-02T23:00:00Z to 2024-07-03T05:00:00Z (UTC). Add one hour for Lagos local time; this is the forecast window, not a proven warning lead.

The archive represents a much weaker rain event at the pilot grid than the substantial rainfall reported at Ikeja. Spatial/temporal rainfall mismatch is a plausible contributor; this is not a matched-location forecast-error measurement and does not establish the correct threshold.

Evidence: [source 1](https://punchng.com/10-hour-rainfall-lekki-ikoyi-residents-flee-luxury-mansions-as-flood-ravages-homes-streets/), [source 2](https://www.thecable.ng/photos-commuters-stranded-homes-submerged-as-flood-ravages-lagos/)

## 2025-08-04 — lekki

- Forecast local-day total: **15 mm**.
- Peak forecast accumulations: 1h: 3.1 mm, 3h: 5.6 mm, 6h: 6.6 mm, 24h: 15 mm.
- Shortfalls below moderate thresholds: 1h: 6.9 mm, 3h: 14.4 mm, 6h: 23.4 mm, 24h: 35 mm.
- Archive run: 2025-08-03T12:00:00Z; daily decision: 2025-08-03T23:00:00Z (midnight Lagos).
- Returned forecast grid is 8.7 km from the configured pilot point.
- Ikeja station: 36.07 mm; partial_period; flag E. Station is 22.1 km from the pilot point.
- First sensitive-rule alert window: 2025-08-04T17:00:00Z to 2025-08-04T23:00:00Z (UTC). Add one hour for Lagos local time; this is the forecast window, not a proven warning lead.

The archive predicts modest rain; Ikeja reports a larger amount from one 12-hour report. Different locations and accumulation periods prevent attribution between rainfall error and threshold sensitivity. Sensitive-v2 first alerts in the last six-hour window, so the daily hit does not establish warning before the reported daytime flooding.

Evidence: [source 1](https://guardian.ng/news/nigeria/metro/nimet-prediction-lagos-assures-residents-over-flash-flood-effects/), [source 2](https://www.channelstv.com/2025/08/04/lagos-communities-flooded-vehicles-submerged-after-marathon-rainfall/)

## 2025-09-16 — lekki

- Forecast local-day total: **31.1 mm**.
- Peak forecast accumulations: 1h: 5.2 mm, 3h: 12.1 mm, 6h: 20.6 mm, 24h: 32 mm.
- Shortfalls below moderate thresholds: 1h: 4.8 mm, 3h: 7.9 mm, 6h: 9.4 mm, 24h: 18 mm.
- Archive run: 2025-09-15T12:00:00Z; daily decision: 2025-09-15T23:00:00Z (midnight Lagos).
- Returned forecast grid is 8.7 km from the configured pilot point.
- Ikeja station: no usable record; missing_or_incomplete; flag missing. Station is 22.1 km from the pilot point.
- First sensitive-rule alert window: 2025-09-15T23:00:00Z to 2025-09-16T05:00:00Z (UTC). Add one hour for Lagos local time; this is the forecast window, not a proven warning lead.

The archive predicts appreciable rain but every original threshold remains unmet. No station observation is available for this date. Threshold sensitivity demonstrably changes the classification; whether the rain forecast was accurate remains unresolved.

Evidence: [source 1](https://punchng.com/motorists-residents-lament-as-flood-submerges-lagos-roads/)

## Interpretation and next action

July has the strongest regional rainfall discrepancy. August remains ambiguous, and its sensitive-rule daily hit occurs in the evening window. September has insufficient independent rainfall data to separate forecast error from threshold choice. Lowering thresholds changes all four labels but does not establish skill.

Next, obtain rainfall observations aligned to the pilot locations and accumulation periods for these three storms (local gauge data or quality-controlled satellite estimates). Freeze sensitive-v2, collect new storms alongside explicitly monitored non-flood periods, and evaluate both detection and false alarms before further tuning. No model training or threshold change is justified by this diagnosis alone.

The NOAA 2025 export was re-fetched on 2026-09-30 and matched the existing cached SHA-256 exactly; it still ends on August 24, so September is unavailable from this export, not a verified dry day.

NOAA flag F means two 12-hour amounts; E means one 12-hour amount. Their reporting periods need not match midnight-to-midnight Lagos. No numerical pilot rainfall error is claimed.

[NOAA definitions](https://www.ncei.noaa.gov/data/global-summary-of-the-day/doc/readme.txt)

- Day-level flood presence, not verified onset or street-level rainfall.
- Trailing 24-hour peaks can include modelled antecedent rainfall; they are not daily totals.
- Cycle 49R1 archive is provider-labelled hindcast, not proof of contemporaneous operational forecasts.
- Sensitive-v2 was developed on these examples; no independent accuracy claim or false-alarm estimate.

Reproduce offline: `.venv/bin/python -m backend.diagnose_misses`. Detailed values and provenance: [diagnosis.json](diagnosis.json).
