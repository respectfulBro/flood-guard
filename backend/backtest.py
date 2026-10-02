"""One-time offline backtest: replay the unchanged rainfall screen over archived single runs.

Network is used only by `download` (Open-Meteo Single Runs) and `groundsource` (Zenodo);
replay and scoring read the local cache and the reviewed event register. All timestamps
are UTC. Unknown outcomes are never treated as dry. The live pilot database is not touched.
"""
import hashlib
import csv
import math
import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError

from .core import AREAS, HOUR, ROOT, THRESHOLDS, UTC, VERSION, dt, iso, now_utc, predict
from .evaluation import wilson

BACKTEST = ROOT / "data" / "backtest"
RUNS_URL = "https://single-runs-api.open-meteo.com/v1/forecast"
ZENODO_API = "https://zenodo.org/api/records/18647054"
MODEL = "ecmwf_ifs"
# Request forecast hours; the provider currently ignores past_hours for single runs.
# Earlier cached runs supply the antecedent period required by predict().
PAST_HOURS, FORECAST_HOURS = 24, 48
LEADS = (6, 12, 18, 24)
LEAD_TOLERANCE = timedelta(hours=3)  # runs are issued on a 6h grid, so the nearest issue is within 3h
ISSUE_DELAY = 6 * HOUR  # conservative simulated availability: initialization time plus six hours
ARCHIVE_START = datetime(2024, 3, 14, tzinfo=UTC)
CYCLES = ((ARCHIVE_START, "ifs-49r1"), (datetime(2026, 5, 12, 6, tzinfo=UTC), "ifs-50r1"))
SPLITS = (("exploration-2024", 2024), ("test-2025", 2025), ("partial-2026", 2026))
MIN_VERIFIED_FLOODS = 5  # fewer scoreable flood episodes => rates are withheld as inconclusive
STATUS_VALUES = ("pending", "approved", "rejected", "context")
LAGOS_SEARCH_BOUNDS = (2.7, 6.3, 4.4, 6.8)  # broad search box, not an administrative boundary


def paths(root=None):
    base = Path(root) if root else BACKTEST
    return {"base": base, "runs": base / "cache" / "runs", "cache": base / "cache",
            "groundsource": base / "cache" / "groundsource", "results": base / "results",
            "manifest": base / "cache" / "manifest.json", "gaps": base / "cache" / "gaps.json",
            "events": base / "events.json"}


def fetch_bytes(url, timeout=60):
    try:
        with urlopen(url, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", errors="replace")
        raise ValueError(f"HTTP {exc.code}: {detail}") from exc


def fetch_stream(url, target, timeout=60):
    digest, size = hashlib.md5(), 0
    with urlopen(url, timeout=timeout) as response, open(target, "wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def file_digest(path, algorithm):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, algorithm).hexdigest()


def sha256_file(path):
    return file_digest(path, "sha256")


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)


def run_key(init):
    return init.strftime("%Y%m%dT%HZ")


def parse_key(key):
    return datetime.strptime(key, "%Y%m%dT%HZ").replace(tzinfo=UTC)


def cycle_of(init):
    label = CYCLES[0][1]
    for cutoff, name in CYCLES[1:]:
        if init >= cutoff:
            label = name
    return label


def split_of(time):
    for name, year in SPLITS:
        if time.year == year:
            return name
    return "out-of-archive"


def run_url(init):
    return RUNS_URL + "?" + urlencode({
        "latitude": ",".join(str(a["lat"]) for a in AREAS),
        "longitude": ",".join(str(a["lng"]) for a in AREAS),
        "hourly": "precipitation", "models": MODEL, "run": init.strftime("%Y-%m-%dT%H:%M"),
        "timezone": "UTC", "past_hours": PAST_HOURS, "forecast_hours": FORECAST_HOURS})


def init_times(start, end):
    time = datetime(start.year, start.month, start.day, tzinfo=UTC)
    finish = datetime(end.year, end.month, end.day, 23, 59, tzinfo=UTC)
    while time <= finish:
        yield time
        time += 6 * HOUR


def validate_run(raw, init):
    """Validate forecast coverage; preceding cached runs provide antecedent rainfall."""
    payloads = json.loads(raw)
    if not isinstance(payloads, list) or len(payloads) != len(AREAS):
        raise ValueError(f"expected {len(AREAS)} area payloads, got {type(payloads).__name__}")
    for area, payload in zip(AREAS, payloads):
        hourly = payload.get("hourly", {})
        times, values = hourly.get("time", []), hourly.get("precipitation", [])
        if payload.get("utc_offset_seconds") != 0 or payload.get("hourly_units", {}).get("precipitation") != "mm":
            raise ValueError("expected UTC hourly precipitation in mm")
        if not times or len(times) != len(values):
            raise ValueError("precipitation values do not match the hourly time axis")
        stamps = [dt(t if t.endswith("Z") else t + "Z") for t in times]
        if any(b - a != HOUR for a, b in zip(stamps, stamps[1:])):
            raise ValueError("expected consecutive hourly timestamps")
        if stamps[0] > init + HOUR or stamps[-1] < init + 30 * HOUR:
            raise ValueError("run does not cover the required forecast horizon")
        if abs(payload["latitude"] - area["lat"]) > .25 or abs(payload["longitude"] - area["lng"]) > .25:
            raise ValueError("response grid does not match requested pilot area")
        for stamp, value in zip(stamps, values):
            if init < stamp <= init + 30 * HOUR and (
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ValueError("missing or invalid forecast rainfall")


def download(start, end, root=None, fetch=fetch_bytes):
    """Import archived runs once; cached runs are checksum-verified and never redownloaded."""
    start = start.date() if isinstance(start, datetime) else start
    end = end.date() if isinstance(end, datetime) else end
    if start > end or start < ARCHIVE_START.date() or end >= now_utc().date():
        raise ValueError("Download dates must be ordered, historical dates")
    place = paths(root)
    place["runs"].mkdir(parents=True, exist_ok=True)
    manifest = read_json(place["manifest"]) if place["manifest"].exists() else {}
    gaps = read_json(place["gaps"])["failed_runs"] if place["gaps"].exists() else {}
    imported, skipped, failed = 0, 0, 0
    for init in init_times(start, end):
        key = run_key(init)
        path = place["runs"] / f"{key}.json"
        entry = manifest.get(key)
        if entry and path.exists() and sha256_file(path) == entry["sha256"]:
            skipped += 1
            gaps.pop(key, None)
            continue
        try:
            raw = fetch(run_url(init))
            validate_run(raw, init)
            path.write_bytes(raw)
            manifest[key] = {"url": run_url(init), "sha256": hashlib.sha256(raw).hexdigest(),
                             "bytes": len(raw), "fetched_at": iso(now_utc()),
                             "model": MODEL, "cycle": cycle_of(init)}
            imported += 1
            gaps.pop(key, None)
        except Exception as exc:  # recorded as an auditable gap, never silently dropped
            gaps[key] = str(exc)[:300]
            failed += 1
        write_json(place["manifest"], manifest)
        write_json(place["gaps"], {"failed_runs": gaps, "checked_at": iso(now_utc())})
    write_json(place["manifest"], manifest)
    write_json(place["gaps"], {"failed_runs": gaps, "checked_at": iso(now_utc())})
    return {"imported": imported, "skipped_cached": skipped, "failed": failed,
            "total_run_slots": imported + skipped + failed, "failures": gaps,
            "note": "Rerun to retry gaps; verified cache entries are not redownloaded"}


def replay(root=None, daily_dates=None):
    """Replay the unchanged screen (core.predict) over every cached run, offline."""
    place = paths(root)
    manifest = read_json(place["manifest"]) if place["manifest"].exists() else {}
    if not manifest:
        raise ValueError("No cached runs; run `backtest-download` first")
    scheduled = {}
    if daily_dates is not None:
        for day in sorted(set(daily_dates)):
            issue = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC) - HOUR
            eligible = [k for k in manifest if issue - 18 * HOUR <= parse_key(k) + ISSUE_DELAY <= issue]
            if eligible:
                scheduled.setdefault(max(eligible), []).append(issue)
    rows, errors, history = [], [], {a["id"]: {} for a in AREAS}
    for key in sorted(manifest):
        init = parse_key(key)
        path = place["runs"] / f"{key}.json"
        try:
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != manifest[key]["sha256"]:
                raise ValueError("cached run no longer matches its recorded checksum")
            validate_run(raw, init)
            payloads = json.loads(raw)
            for area, payload in zip(AREAS, payloads):
                series = history[area["id"]]
                # Earlier archived forecasts supply modelled antecedents, never later runs/reanalysis.
                for stamp, value in zip(payload["hourly"]["time"], payload["hourly"]["precipitation"]):
                    time = dt(stamp if stamp.endswith("Z") else stamp + "Z")
                    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
                        series[time] = (value, key)
                issues = [init + ISSUE_DELAY] if daily_dates is None else scheduled.get(key, [])
                for issue in issues:
                    needed = [issue + i * HOUR for i in range(-22, 25)]
                    if any(t not in series for t in needed):
                        errors.append({"run": key, "area_id": area["id"], "error": "Missing rainfall coverage: download at least one preceding day and a complete forecast horizon"})
                        continue
                    combined = {**payload, "hourly": {"time": [iso(t) for t in needed],
                                "precipitation": [series[t][0] for t in needed]}}
                    forecast = predict(combined, issue)
                    sources = sorted({series[t][1] for t in needed})
                    rows.append({"run_at": iso(init), "cycle": cycle_of(init), "area_id": area["id"],
                                 "issued_at": iso(issue), "available_at": iso(init + ISSUE_DELAY),
                                 "issue_rule": "run initialisation plus six hours" if daily_dates is None else "midnight Lagos; latest cached run available under the six-hour delay assumption",
                                 "version": forecast["version"], "grid": [payload["latitude"], payload["longitude"]],
                                 "valid_from": forecast["valid_from"], "valid_until": forecast["valid_until"],
                                 "windows": forecast["windows"], "source_url": manifest[key]["url"],
                                 "source_sha256": manifest[key]["sha256"],
                                 "input_runs": {k: manifest[k]["sha256"] for k in sources}})
        except Exception as exc:
            errors.append({"run": key, "error": str(exc)[:300]})
    rows.sort(key=lambda r: (r["run_at"], r["area_id"]))
    return rows, errors


def load_events(root=None):
    """Validate evidence and retain reviewer identity; approval is not a claim of field verification."""
    path = paths(root)["events"]
    if not path.exists():
        raise ValueError(f"Missing event register: {path}")
    data = read_json(path)
    problems, events, ids = [], [], set()
    areas = {a["id"] for a in AREAS}

    def text(event, field, minimum=1):
        value = event.get(field)
        return value.strip() if isinstance(value, str) and len(value.strip()) >= minimum else None

    def stamp(event, field):
        try:
            return dt(event[field])
        except (KeyError, TypeError, ValueError, AttributeError):
            return None

    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
        raise ValueError("Event register must contain an events list")
    for event in data["events"]:
        if not isinstance(event, dict):
            problems.append("Each event must be an object")
            continue
        label = text(event, "id") or "<missing id>"
        if not text(event, "id"):
            problems.append(f"{label}: missing id")
        elif label in ids:
            problems.append(f"{label}: duplicate id")
        ids.add(label)
        status = event.get("status")
        if status not in STATUS_VALUES:
            problems.append(f"{label}: status must be one of {STATUS_VALUES}")
            continue
        if event.get("area_id") not in areas:
            problems.append(f"{label}: area_id must be one of {sorted(areas)}")
        start, end = stamp(event, "start_at"), stamp(event, "end_at")
        if status in ("approved", "context") and (start is None or end is None):
            problems.append(f"{label}: {status} events need timezone-aware UTC start_at/end_at")
        elif start and end and start > end:
            problems.append(f"{label}: start_at is after end_at")
        if status == "approved":
            if event.get("event_date") is not None:
                try:
                    datetime.strptime(event["event_date"], "%Y-%m-%d")
                except (ValueError, TypeError):
                    problems.append(f"{label}: event_date must be YYYY-MM-DD")
            if label == "template-never-approve":
                problems.append("The template cannot be approved")
            if event.get("timing_precision") not in ("exact", "hour", "day", "month", "unknown"):
                problems.append(f"{label}: invalid timing_precision")
            if end and end > now_utc():
                problems.append(f"{label}: observed events cannot be in the future")
            for name, minimum in [("storm_id", 1), ("location", 1), ("description", 1), ("cause", 1),
                                  ("timing_precision", 1), ("reviewer", 1), ("review_note", 10)]:
                if not text(event, name, minimum):
                    problems.append(f"{label}: approved event needs a meaningful {name}")
            if not isinstance(event.get("flooded"), bool):
                problems.append(f"{label}: approved event needs flooded true/false")
            if stamp(event, "reviewed_at") is None:
                problems.append(f"{label}: approved event needs a timezone-aware reviewed_at")
            urls = event.get("source_urls")
            if not isinstance(urls, list) or not urls or not all(
                    isinstance(u, str) and (u.startswith(("http://", "https://")) or
                    (event.get("evidence_workflow") and u.startswith("local:"))) for u in urls):
                problems.append(f"{label}: approved event needs at least one source link (HTTP(S) or a managed local observation)")
        events.append(event)
    if problems:
        raise ValueError("Event register problems:\n" + "\n".join(problems))
    from .evidence import verify_events
    verify_events(events, root)
    return data, events


def overlapping_windows(forecast, start, end):
    return [w for w in forecast["windows"] if dt(w["start_at"]) <= end and (dt(w["end_at"]) > start
            or start == end == dt(forecast["valid_until"]) == dt(w["end_at"]))
            and (start == end or dt(w["start_at"]) < end)]


def match_forecast(forecasts, target, start):
    """The archived run issued nearest the target lead: within three hours, never after onset."""
    if not forecasts:
        return None
    best = min(forecasts, key=lambda f: (abs(dt(f["issued_at"]) - target), dt(f["issued_at"])))
    if abs(dt(best["issued_at"]) - target) > LEAD_TOLERANCE or dt(best["issued_at"]) >= start:
        return None
    return best


def score_episode(reports, forecasts_by_area):
    """One reviewed episode per area/storm: per-lead outcomes plus an event-level rollup."""
    area = reports[0]["area_id"]
    start = min(dt(r["start_at"]) for r in reports)
    end = max(dt(r["end_at"]) for r in reports)
    labels = {bool(r["flooded"]) for r in reports}
    episode = {"area_id": area, "storm_id": reports[0]["storm_id"], "split": split_of(start),
               "start_at": iso(start), "end_at": iso(end), "reports": len(reports),
               "flooded": labels.pop() if len(labels) == 1 else None,
               "timing_precision": reports[0].get("timing_precision", ""), "cause": reports[0].get("cause", ""),
               "location": reports[0].get("location", ""), "description": reports[0].get("description", ""),
               "report_ids": sorted(r["id"] for r in reports),
               "evidence_records": [{k: r.get(k) for k in ("id", "source_ids", "source_checksums", "review_history",
                                      "evidence", "location_precision", "timing_note", "monitoring_method")}
                                    for r in reports],
               "source_urls": sorted({url for r in reports for url in r.get("source_urls", [])}), "reviewer": reports[0].get("reviewer", ""),
               "review_note": reports[0].get("review_note", ""), "leads": []}
    coarse = end - start > 6 * HOUR or any(r.get("timing_precision") not in ("exact", "hour") for r in reports)
    for lead in LEADS:
        row = {"storm_id": episode["storm_id"], "lead_target_hours": lead, "outcome": "unknown", "reason": None,
               "matched_run_at": None, "matched_issued_at": None, "actual_lead_hours": None,
               "cycle": None, "risk_tiers": []}
        if episode["flooded"] is None:
            row["reason"] = "Duplicate storm reports carry conflicting flooded labels"
        elif coarse:
            row["reason"] = "Timing precision too coarse for hourly scoring (coarse label or interval wider than six hours)"
        else:
            forecast = match_forecast(forecasts_by_area.get(area, []), start - lead * HOUR, start)
            if forecast is None:
                row["reason"] = "No archived run issued within three hours of the target lead"
            else:
                windows = overlapping_windows(forecast, start, end)
                alarms = {w["risk_tier"] in ("moderate", "high") for w in windows}
                row.update(matched_run_at=forecast["run_at"], matched_issued_at=forecast["issued_at"],
                           cycle=forecast["cycle"], risk_tiers=[w["risk_tier"] for w in windows],
                           actual_lead_hours=round((start - dt(forecast["issued_at"])).total_seconds() / 3600, 2))
                if not windows or dt(forecast["valid_from"]) > start or dt(forecast["valid_until"]) < end:
                    row["reason"] = "Matched run does not cover the episode window"
                elif episode["flooded"] is False and any(r.get("evidence_workflow") for r in reports) and any(
                        not any(dt(r["start_at"]) <= dt(w["start_at"]) and dt(r["end_at"]) >= dt(w["end_at"])
                                for r in reports) for w in windows):
                    row["reason"] = "Monitoring does not cover the full matched forecast windows"
                elif len(alarms) != 1:
                    row["reason"] = "Episode straddles forecast windows with different risk tiers"
                else:
                    alarm = alarms.pop()
                    row["outcome"] = ("hit" if alarm else "miss") if episode["flooded"] \
                        else ("false_alarm" if alarm else "correct_negative")
        episode["leads"].append(row)
    known = [l["outcome"] for l in episode["leads"] if l["outcome"] != "unknown"]
    outcome = "unknown"
    if episode["flooded"] is not None and known:
        # Event-level: any alert decides; every scored lead said low => a miss. Per-lead
        # rows in the audit file keep coverage gaps and their reasons visible.
        if "hit" in known or "false_alarm" in known:
            outcome = "detected" if episode["flooded"] else "false_alarm"
        else:
            outcome = "missed" if episode["flooded"] else "correct_negative"
    episode["event_outcome"] = outcome
    return episode


def lead_summary(leads, gate):
    counts = Counter(lead["outcome"] for lead in leads)
    floods = counts["hit"] + counts["miss"]
    alerts_known = counts["hit"] + counts["false_alarm"]
    summary = {"hits": counts["hit"], "misses": counts["miss"], "false_alarms": counts["false_alarm"],
               "correct_negatives": counts["correct_negative"], "unknowns": counts["unknown"],
               "pairs": len(leads)}
    gate = gate and len({l["storm_id"] for l in leads if l["outcome"] in ("hit", "miss")}) >= MIN_VERIFIED_FLOODS
    negatives = counts["false_alarm"] + counts["correct_negative"]
    rates = {"detection_rate": counts["hit"] / floods if floods else None,
             "detection_interval": wilson(counts["hit"], floods),
             "false_alarm_ratio": counts["false_alarm"] / alerts_known if alerts_known and negatives else None,
             "false_alarm_interval": wilson(counts["false_alarm"], alerts_known) if negatives else None}
    return {**summary, **(rates if gate else dict.fromkeys(rates, None))}


def score(events, rows, gaps=0, replay_errors=0):
    forecasts_by_area = {}
    for row in rows:
        forecasts_by_area.setdefault(row["area_id"], []).append(row)
    for forecasts in forecasts_by_area.values():
        forecasts.sort(key=lambda f: dt(f["issued_at"]))

    groups, unscored = {}, Counter()
    for event in events:
        if event["status"] == "approved":
            if event["flooded"] and event.get("cause") != "rainfall":
                unscored["non_rainfall_floods"] += 1
                continue
            groups.setdefault((event["area_id"], event["storm_id"]), []).append(event)
        else:
            unscored[event["status"]] += 1
    episodes = [score_episode(reports, forecasts_by_area) for reports in groups.values()]
    storm_starts = {}
    for episode in episodes:
        storm = episode["storm_id"]
        storm_starts[storm] = min(dt(episode["start_at"]), storm_starts.get(storm, dt(episode["start_at"])))
    for episode in episodes:
        episode["split"] = split_of(storm_starts[episode["storm_id"]])
    floods = [e for e in episodes if e["flooded"]]
    gate = len({e["storm_id"] for e in floods if e["event_outcome"] != "unknown"}) >= MIN_VERIFIED_FLOODS  # rates are withheld below this evidence floor
    all_leads = [lead for episode in episodes for lead in episode["leads"]]

    by_split = {}
    for name, _ in SPLITS + (("out-of-archive", 0),):
        chosen = [e for e in episodes if e["split"] == name]
        if not chosen:
            continue
        by_split[name] = {"flood_episodes": sum(e["flooded"] is True for e in chosen),
                          "non_flood_episodes": sum(e["flooded"] is False for e in chosen),
                          "event_outcomes": dict(Counter(e["event_outcome"] for e in chosen)),
                          "by_lead": {lead: lead_summary([l for e in chosen for l in e["leads"]
                                                           if l["lead_target_hours"] == lead], gate)
                                      for lead in LEADS}}
    detected = sum(e["event_outcome"] == "detected" for e in floods)
    missed = sum(e["event_outcome"] == "missed" for e in floods)
    false_alarms = sum(e["event_outcome"] == "false_alarm" for e in episodes if e["flooded"] is False)
    known_floods = detected + missed
    alerts_known = false_alarms + detected
    lead_hits = sorted(l["actual_lead_hours"] for l in all_leads if l["outcome"] == "hit")
    known_negatives = sum(e["flooded"] is False and e["event_outcome"] != "unknown" for e in episodes)
    rates = {"detection_rate": detected / known_floods if known_floods else None,
             "detection_interval": wilson(detected, known_floods),
             "false_alarm_ratio": false_alarms / alerts_known if alerts_known and known_negatives else None,
             "false_alarm_interval": wilson(false_alarms, alerts_known) if known_negatives else None}
    scores = {
        "screen": {"version": VERSION, "thresholds_mm": THRESHOLDS, "replayed_unchanged": True,
                   "model": MODEL, "simulated_issue_rule": "run initialisation plus six hours",
                   "cycle_change": {"at": iso(CYCLES[1][0]), "from": CYCLES[0][1], "to": CYCLES[1][1],
                                    "source": "Open-Meteo Single Runs documentation"}},
        "status": "inconclusive" if not gate else "early_evaluation",
        "evidence_floor": {"min_independent_scoreable_flood_storms_for_rates": MIN_VERIFIED_FLOODS,
                           "message": None if gate else
                           f"Fewer than {MIN_VERIFIED_FLOODS} independent scoreable flood storms; counts are reported "
                           "but rates are withheld because they would be a misleading accuracy claim"},
        "episodes": {"flood_episodes": len(floods), "scored_floods": known_floods,
                     "non_flood_episodes": sum(e["flooded"] is False for e in episodes),
                     "event_outcomes": dict(Counter(e["event_outcome"] for e in episodes)),
                     "unscored_register_entries": dict(unscored)},
        "overall": {**(rates if gate else dict.fromkeys(rates, None)),
                    "by_lead": {lead: lead_summary([l for l in all_leads
                                                    if l["lead_target_hours"] == lead], gate) for lead in LEADS}},
        "lead_time_hours": {"hit_count": len(lead_hits), "values": lead_hits,
                            "min": min(lead_hits) if lead_hits else None,
                            "median": median(lead_hits) if lead_hits else None,
                            "mean": round(mean(lead_hits), 2) if lead_hits else None},
        "no_alert_baseline": {"strategy": "never alert", "detected": 0, "missed": known_floods,
                               "detection_rate": 0.0 if known_floods else None, "false_alarm_ratio": None,
                               "note": "Compared over the same scored episodes as the screen: never "
                                       "alerting detects nothing and produces no false alarms"},
        "by_split": by_split,
        "by_cycle": {cycle: {lead: lead_summary([l for l in all_leads if l["cycle"] == cycle
                          and l["lead_target_hours"] == lead], gate) for lead in LEADS}
                     for _, cycle in CYCLES},
        "checks": {"missing_run_slots": gaps, "replay_errors": replay_errors,
                   "duplicate_report_storms": sorted(e["storm_id"] for e in episodes if e["reports"] > 1),
                   "coarse_timing_episodes": sum(any("coarse" in (l["reason"] or "") for l in e["leads"])
                                                 for e in episodes),
                   "conflicting_label_episodes": sum(e["flooded"] is None for e in episodes),
                   "unknown_reasons": dict(Counter(l["reason"] for l in all_leads
                                                     if l["outcome"] == "unknown" and l["reason"])),
                   "episodes_without_any_matched_run": sum(
                       all(l["matched_run_at"] is None for l in e["leads"]) for e in episodes)},
        "limitations": "The pre-May-2026 archive is labelled Cycle 49R1 hindcasts by the provider; it is not evidence of operational skill in 2024/2025. Archived replay is a standardized historical simulation, not proof of the exact "
                       "forecast a user could have seen. The 2025 test split must not be used for threshold "
                       "tuning. Unknown is not dry: unverified dates, coarse timing, cloudy satellite imagery "
                       "and missing reports never count as correct negatives. Wilson intervals are descriptive; "
                       "areas within one storm are correlated. 2026 is an incomplete year spanning two model cycles. False-alarm ratios describe only the reviewed sample, not all issued alerts."}
    return scores, episodes


def run(root=None):
    """Offline replay, scoring and export; byte-identical when rerun on the same cache."""
    place = paths(root)
    place["results"].mkdir(parents=True, exist_ok=True)
    rows, errors = replay(root)
    _, events = load_events(root)
    gaps = read_json(place["gaps"])["failed_runs"] if place["gaps"].exists() else {}
    scores, episodes = score(events, rows, gaps=len(gaps), replay_errors=len(errors))
    manifest = read_json(place["manifest"])
    from .evidence import verify_events
    scores["evidence_sources"] = verify_events(events, root)
    scores["evaluation_history"] = "2025 examples were inspected during sensitive-v2 development; not an untouched test for that version. Reserve future storms before further tuning."
    scores["reproducible"] = True
    scores["replay_errors"] = errors
    scores["code_sha256"] = {p.name: sha256_file(p) for p in (Path(__file__), Path(__file__).with_name("core.py"), Path(__file__).with_name("evidence.py"))}
    scores["inputs"] = {"runs_imported": len(manifest),
                        "runs_by_cycle": dict(Counter(entry["cycle"] for entry in manifest.values())),
                        "predictions_exported": len(rows), "event_register": str(place["events"]),
                        "inputs_digest": hashlib.sha256(
                            json.dumps([[k, manifest[k]["sha256"]] for k in sorted(manifest)],
                                       sort_keys=True).encode() + Path(place["events"]).read_bytes()
                            + json.dumps(scores["evidence_sources"], sort_keys=True).encode()).hexdigest()}
    (place["results"] / "predictions.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in rows) + ("\n" if rows else ""))
    write_json(place["results"] / "scores.json", scores)
    # ponytail: file-scan of a few thousand runs; move to a columnar cache if replay latency matters.
    audit = [{**{k: v for k, v in episode.items() if k != "leads"}, **lead}
             for episode in episodes for lead in episode["leads"]]
    (place["results"] / "episodes.jsonl").write_text(
        "\n".join(json.dumps(r, sort_keys=True) for r in audit) + ("\n" if audit else ""))
    with (place["results"] / "episodes.csv").open("w", newline="") as handle:
        fields = list(audit[0]) if audit else ["area_id", "storm_id", "outcome", "reason"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in audit:
            writer.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in row.items()})
    return {"status": scores["status"], "flood_episodes": scores["episodes"]["flood_episodes"],
            "episodes_scored": len(episodes), "runs_imported": len(manifest),
            "results": str(place["results"])}


def groundsource(root=None, fetch=fetch_bytes, stream=fetch_stream):
    """One-time import of Groundsource (Zenodo parquet) and Lagos-area candidate extraction.

    Candidates are leads for manual review, never verified events; approve evidence into
    the register only after checking the underlying sources.
    """
    place = paths(root)
    place["groundsource"].mkdir(parents=True, exist_ok=True)
    record = json.loads(fetch(ZENODO_API))
    files = [f for f in record["files"] if f["key"].endswith(".parquet")]
    if len(files) != 1:
        raise ValueError("Expected one Groundsource parquet file")
    [file] = files
    write_json(place["groundsource"] / "record.json", record)
    if Path(file["key"]).name != file["key"]:
        raise ValueError("Unsafe Groundsource filename")
    expected = file["checksum"].split(":")[-1]
    target = place["groundsource"] / file["key"]
    if not (target.exists() and target.stat().st_size == file["size"]
            and file_digest(target, "md5") == expected):
        partial = target.with_suffix(".part")
        digest, size = stream(file["links"]["self"], partial)
        if digest != expected or size != file["size"]:
            partial.unlink(missing_ok=True)
            raise ValueError(f"Groundsource download failed its checksum (md5 {digest}, expected {expected})")
        partial.replace(target)
    try:
        import pyarrow.parquet as pq
        import shapely
    except ImportError as exc:  # importer-only dependency
        raise ValueError("Groundsource import needs pyarrow and shapely: "
                         ".venv/bin/pip install -r backend/requirements-dev.txt") from exc
    parquet = pq.ParquetFile(target)
    required = {"uuid", "geometry", "start_date", "end_date"}
    if not required.issubset(parquet.schema_arrow.names):
        raise ValueError("Groundsource schema changed: expected uuid, geometry, start_date and end_date")
    geo = json.loads((parquet.schema_arrow.metadata or {}).get(b"geo", b"{}"))
    geometry_meta = geo.get("columns", {}).get("geometry", {})
    if geometry_meta.get("encoding") != "WKB" or geometry_meta.get("crs", {}).get("id") != {"authority": "EPSG", "code": 4326}:
        raise ValueError("Groundsource geometry must be WKB in EPSG:4326")
    region = shapely.box(*LAGOS_SEARCH_BOUNDS)
    candidates, total_matches = [], 0
    for batch in parquet.iter_batches(batch_size=8192):
        geometries = shapely.from_wkb(batch.column("geometry").to_pylist())
        indices = shapely.intersects(geometries, region).nonzero()[0]
        total_matches += len(indices)
        for index in indices:
            row = batch.slice(int(index), 1).to_pylist()[0]
            geometry = geometries[index]
            row["geometry"] = json.loads(shapely.to_geojson(geometry))
            row["pilot_points_intersected"] = [a["id"] for a in AREAS
                if geometry.intersects(shapely.Point(a["lng"], a["lat"]))]
            row["timing_precision"] = "day"
            row["status"] = "pending"
            row["archive_overlap"] = row["end_date"] >= ARCHIVE_START.date().isoformat()
            candidates.append(row)
    write_json(place["groundsource"] / "candidates.json", {
        "source": record["links"]["self_html"], "file": file["key"], "md5": expected,
        "search_bounds_wgs84": LAGOS_SEARCH_BOUNDS, "total_matches": total_matches,
        "note": "Spatial candidate leads; not verified events. The published parquet contains dates and "
                "polygons, no article URLs or neighborhood names. Find independent source evidence for "
                "timing, location and cause before approving anything. Polygon intersection is not proof "
                "that a pilot street flooded. Dates alone cannot support hourly scoring.",
        "candidates_truncated": False, "candidates": candidates})
    return {"file": file["key"], "md5_verified": True, "matches": len(candidates), "total_matches": total_matches,
            "archive_period_candidates": sum(c["archive_overlap"] for c in candidates),
            "candidates": str(place["groundsource"] / "candidates.json")}
