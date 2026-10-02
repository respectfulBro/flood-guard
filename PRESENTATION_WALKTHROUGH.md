# FloodGuard: presentation walkthrough

Prepared September 30, 2026. Based on the results currently saved in this project. This guide does not change the application, data, or thresholds.

**Suggested length:** 8–10 minutes, followed by questions.

**The message to remember:** We have built a working, auditable rainfall-screening prototype and a way to test it honestly. The evaluation exposes limitations in both the rainfall inputs and the alert rules. Operational flood-prediction accuracy is not yet established.

## 1. Opening: the problem and our goal — 45 seconds

**Say:**

> Flooding can disrupt travel, damage homes, and put people at risk. FloodGuard explores whether rainfall forecasts can help identify periods when residents should pay closer attention to flood conditions. We are starting with two pilot areas in Lagos: Lekki and Ikosi-Ketu.
>
> Today I will show the prototype, explain how we tested it, and discuss what the results taught us. This is a research pilot, not yet a validated public warning service.

**Show:** The home page and the two pilot areas.

**Keep the scope clear:** The current locations are representative weather points. We have not established flood boundaries for every street or estate.

## 2. How it works — 1 minute

**Say:**

> We obtain hourly ECMWF IFS rainfall forecasts through Open-Meteo. The backend applies explicit rainfall thresholds and presents low, moderate, or high screening tiers for four six-hour windows covering the next 24 hours.
>
> We check rainfall accumulated over one, three, six, and 24 hours. This captures both short bursts and longer periods of rain. We preserve the inputs and rule version so we can reproduce each result later.

The sequence is:

1. Fetch hourly rainfall data.
2. Validate its freshness and completeness.
3. Calculate rolling rainfall accumulations.
4. Apply the versioned rules.
5. Display the screening tiers and retain an audit record.

**Technical explanation, only if asked:** React/Vite provides the interface; a Python/FastAPI backend handles ingestion and screening; SQLite stores the live pilot records. Separate Python CLI tools handle historical research and offline replay.

**Important distinction:** This is currently a rule-based screen, not a machine-learning model trained on flood examples. “Low” means the rainfall thresholds were not crossed; it does not mean flooding is impossible.

## 3. Website demonstration — 1½ minutes

Launch `npm run demo`, sign in as `researcher` at http://127.0.0.1:8000, and start with **Historical replay**. Choose an event and switch original/sensitive rules. Choose the older ERA5 analysis separately. Show the evidence links and strategy, then save a synthetic observation in the isolated demo database. Current-weather areas may be unavailable in this offline mode.

Navigate using the website's menu; labels may differ slightly between views.

### A. Map and area details

- Select Lekki, then Ikosi-Ketu.
- Point out the displayed forecast windows and rainfall information.
- Show timestamps or stale/unknown data notices where present.

**Say:**

> The display makes both the screening result and its data status visible. Missing or outdated data should not be mistaken for a low-risk result. These are rainfall-screening tiers, not calibrated probabilities of flooding.

Do not promise particular colors or current weather conditions: the live forecast can change before the presentation.

### B. Event reporting

Show the report form without submitting a made-up observation.

**Say:**

> We also need observations of what actually happened. Reports record the location, timing, cause, and supporting evidence. They need review before they can influence evaluation results. We want monitored non-flood periods as well as flood reports.

### C. Research performance

Open the research performance page. Start with the original rules, then show the sensitive-rule comparison.

**Say:**

> This page deliberately shows the small sample and the unresolved evidence. An unavailable accuracy metric is more honest than a confident percentage based on a few selected examples.

Presenter note: a label such as “2025 fixed-threshold test” does not make 2025 an untouched test for the sensitive version. Those examples were already inspected during its development. State that distinction aloud.

## 4. How we built the historical evidence — 1 minute

**Say:**

> We use public news and official reports to identify historical floods. Groundsource helps find candidate events, but its dates and polygons do not automatically establish flooding in a particular neighborhood.
>
> We review the article's account of the event, separate the flood date from the publication date, and group duplicate stories about the same storm. Coarse or uncertain records stay pending or provide context rather than becoming precise labels.

The tooling supports:

- Cached source documents and extracted article text, with checksums and provenance.
- Pending observations and recorded review decisions.
- Corrections that preserve review history.
- Offline replay after data collection.
- Separate rainfall observations for diagnosis.

**Be precise about verification:** The current historical observations have undergone assistant review of public sources. They are not independently verified field measurements or a complete inventory of all floods.

## 5. What the 2024–2025 comparison found — 1½ minutes

**Say:**

> Our first daily comparison contains four area-day observations across three storms. The original rules stayed low on all four. After inspecting these cases, a more sensitive rule version flagged all four days. That shows how the thresholds affect the output, but it is not independent validation.

The four observations are:

- **July 3, 2024, Ikosi-Ketu:** archived rainfall for the local day was 16.2 mm.
- **July 3, 2024, Lekki:** archived rainfall was 18.2 mm. These two observations belong to the same storm.
- **August 4, 2025, Lekki:** archived rainfall was 15 mm.
- **September 16, 2025, Lekki:** archived rainfall was 31.1 mm.

These daily totals help describe the weather input. The actual rule decisions use rolling 1/3/6/24-hour peaks; daily total alone does not explain every threshold.

Two findings matter:

1. For July 2024, Ikeja airport reported about 156 mm, much more than the rainfall represented at the pilot forecast grids. The station is at a different location and its reporting period differs, so this is a diagnostic clue, not an exact error calculation.
2. For August 2025, the sensitive version flags the **6 p.m.–midnight forecast window**. A hit somewhere on the same day does not prove useful warning before the reported flood. That window was part of the daily forecast, not necessarily an alert first issued at 6 p.m.

**Explain the archive limitation:** The provider labels the pre-May-2026 model archive as hindcasts. This historical experiment does not reconstruct exactly what a resident could have seen operationally in 2024 or 2025.

**If someone sees hourly results marked inconclusive:** The reports establish flood days, not precise onset times. They can support a daily comparison without supporting an hourly warning-lead claim.

## 6. What looking further back found — 1½ minutes

Open [the older-event report](data/backtest/historical/report.md). These results are separate from the website's original four-case comparison.

**Say:**

> We extended our search to 2015–2023. This first pass accepted five news-supported flood days for comparison and retained seven other candidates as pending or context. We did not assume the unresolved years had no floods.
>
> For these older events, we used hourly ERA5 reanalysis. Reanalysis is a reconstruction of historical weather using information available after the event. It lets us examine threshold behavior, but it does not test advance forecasting skill.

On the five accepted days:

- **July 8, 2017, Lekki:** original rules did not trigger; sensitive rules triggered.
- **June 18, 2020, Lekki:** original rules did not trigger; sensitive rules triggered.
- **July 16, 2021, Lekki:** both versions triggered.
- **June 18, 2022, Ikosi-Ketu:** original rules did not trigger; sensitive rules triggered.
- **September 16, 2023, Lekki:** original rules did not trigger; sensitive rules triggered.

**Summary:** On ERA5 rainfall, the original version triggered on **one of five** selected flood days; the sensitive version triggered on **five of five**. These are threshold-coincidence counts, not accuracy percentages.

The biggest lesson comes from comparing rainfall sources:

- **June 2020:** ERA5 local-day rainfall was 22.8 mm, while Ikeja reported 73.91 mm over its reported 24-hour period.
- **June 2022:** ERA5 local-day rainfall was 15.9 mm, while Ikeja reported 105.92 mm over its reported 24-hour period.

Both station amounts cross the original 50 mm/24-hour threshold, whereas the corresponding ERA5 inputs do not trigger the original rules. Locations and reporting periods differ, so we cannot attribute the discrepancy solely to model error. We can conclude that rainfall-source choice materially changes the diagnosis.

Also disclose that ERA5 places both pilot points in the same roughly 25 km grid cell. It cannot resolve street-level drainage conditions.

## 7. What we learned and what comes next — 1 minute

**Say:**

> The useful result is that the evaluation tells us where to investigate. We cannot improve this responsibly by lowering thresholds until every known flood is detected. A system that alerts every day would also catch every flood day, but could be unusable.
>
> Our next priorities are rainfall observations closer to the pilot locations, new flood events that were not used during development, and explicitly monitored periods when flooding did not occur. We will hold the rules fixed while collecting those observations.

The immediate priorities are:

1. Compare rainfall over aligned locations and time periods using local gauges or suitable satellite estimates.
2. Collect flood and non-flood observations systematically, including rainy days without flooding.
3. Keep all reports from one storm together in evaluation partitions.
4. Evaluate a future period without changing the rules in response to its outcomes.
5. Measure both detection and false alarms before considering training or deployment.

**Closing line:**

> FloodGuard currently demonstrates a working screening and evidence pipeline. Our contribution is making its decisions reproducible and its limitations visible, so the next improvements can be driven by evidence rather than a misleading accuracy claim.

## Quick answers to likely questions

### “What is the accuracy?”

We cannot responsibly estimate operational accuracy yet. We have a small, selectively reported set of flood observations and no sufficient monitored non-flood sample. The application therefore withholds unsupported rates.

### “Does five out of five mean 100% accuracy?”

No. It means the sensitive rules crossed a threshold on five selected older flood days when given reanalysis rainfall. It does not measure false alarms, advance warning, or generalization to future storms.

### “Why did the original rules miss floods?”

The supplied rainfall never crossed their thresholds in those cases. Nearby station comparisons show that rainfall representation may contribute, while local drainage and other flood mechanisms are not modelled. We cannot isolate one universal cause from the current evidence.

### “Why not just keep lowering the thresholds?”

That increases alert frequency. Without verified negative observations, we do not know how many extra alerts would be false alarms. Both detection and alert burden matter.

### “Are there zero false alarms?”

We have not established that. A count of zero verified false alarms is not evidence of a zero false-alarm rate. Many alert outcomes are unknown.

### “Why use news?”

News can document historical flood presence, locations, and dates where structured incident records are unavailable. It is selective and sometimes ambiguous, so every accepted label needs a review note and source links. News silence cannot establish a dry day.

### “Why not train an AI model now?”

The current labelled dataset is too limited to justify a reliable training-and-test exercise. We first need representative observations, including negatives, and independent storms reserved for evaluation.

### “Can this predict exactly which street floods?”

Not yet. The pilot uses representative weather points and coarse weather grids. It does not include a validated street-level drainage, terrain, tide, or river model.

### “Can I combine the old and new results into one detection rate?”

No. The earlier-period analysis uses ERA5 reanalysis; the later comparison replays archived model outputs. Their inputs and interpretation differ. Keep them separate.

### “Is it ready for public emergency warnings?”

No. It is a private research pilot that still needs prospective validation and stronger local observations.

## Before presenting: practical checklist

These are instructions for you; preparing this document has not run these commands or changed the app.

### Launch the local website

In a terminal:

```sh
cd /Users/amansingh/Desktop/floodguard-africa
npm run pilot
```

If needed, the service prompts for a private password of at least 16 characters. Open **http://127.0.0.1:8000**, sign in as **researcher**, and enter the password you chose. Keep the password off the projected screen.

If the built frontend is missing or you need the latest frontend build, run `npm run build` before starting the pilot. Existing dependencies and the Python virtual environment are already present in this workspace; do not reinstall them just for the presentation.

The live weather fetch needs network access. An unknown/stale state can occur if the fetch fails. Explain it honestly and move to the saved historical reports.

### Optional reproducibility demonstration

Only run these if the main project work has finished and you want to regenerate the corresponding outputs. They write report files, but do not require the website process or network downloads when their inputs are cached.

```sh
# Original 2024–2025 daily comparison
.venv/bin/python -m backend backtest-run --resolution daily

# Older-event ERA5 rainfall diagnostic
.venv/bin/python -m backend.historical_rainfall run
```

Avoid collecting new sources or changing thresholds during the presentation.

### Offline fallback

Open these files in the editor's Markdown preview if the website or network is unavailable:

- [Four-case diagnosis](data/backtest/diagnosis.md).
- [Older-event rainfall diagnostic](data/backtest/historical/report.md).
- [Older candidate review decisions](data/backtest/historical/review.json).
- [Source-review CLI instructions](backend/EVIDENCE.md).

Do not claim the older five-case analysis is displayed in the website unless you have verified that integration. Its separate Markdown report is sufficient for this walkthrough.

## Thirty-second version

> FloodGuard is a rainfall-screening research prototype for Lekki and Ikosi-Ketu. It converts hourly weather data into versioned risk tiers and preserves the evidence needed to test those decisions. Our first historical comparison found four missed area-day observations under the original rules. A separate older-event rainfall diagnostic found that the original rules triggered on one of five selected flood days, while the sensitive version triggered on all five. These are not accuracy claims: rainfall sources differ, precise onset times are often missing, and false alarms remain unmeasured. The next step is better local rainfall data and prospective flood and non-flood monitoring with the rules held fixed.
