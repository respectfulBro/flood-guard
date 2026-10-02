"""Named-area, local-day evidence comparison. No inference of precise onset or dry days."""
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import backtest as bt
from .core import HOUR, UTC, THRESHOLDS, VERSION, LIVE_VERSION, dt, iso, rescreen
from .evaluation import wilson


def day_bounds(day):
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=UTC) - HOUR
    return start, start + 24 * HOUR


def summarize(cases):
    counts = Counter(c["outcome"] for c in cases)
    storms = {c["storm_id"] for c in cases if c["outcome"] in ("hit", "miss")}
    floods = counts["hit"] + counts["miss"]
    negatives = counts["false_alarm"] + counts["correct_negative"]
    alerts = counts["hit"] + counts["false_alarm"]
    enough = len(storms) >= bt.MIN_VERIFIED_FLOODS
    return {"hits": counts["hit"], "misses": counts["miss"], "false_alarms": counts["false_alarm"],
            "correct_negatives": counts["correct_negative"], "unknowns": counts["unknown"],
            "independent_storms": len(storms), "flood_cases_scored": floods,
            "non_flood_cases_scored": negatives,
            "detection_rate": counts["hit"] / floods if enough else None,
            "detection_interval": wilson(counts["hit"], floods) if enough else None,
            "false_alarm_ratio": counts["false_alarm"] / alerts if enough and negatives and alerts else None,
            "status": "early_evaluation" if enough else "insufficient_evidence"}


def score(events, forecasts):
    indexed = {(f["area_id"], (dt(f["issued_at"]) + HOUR).date().isoformat()): f for f in forecasts}
    grouped = {}
    for event in events:
        if event["status"] == "approved":
            grouped.setdefault((event["area_id"], event["storm_id"]), []).append(event)
    cases = []
    for (area, storm), reports in sorted(grouped.items()):
        dates = {e.get("event_date") for e in reports}
        labels = {e["flooded"] for e in reports}
        day = next(iter(dates)) if len(dates) == 1 else None
        case = {"area_id": area, "storm_id": storm, "event_date": day,
                "outcome": "unknown", "reason": None, "forecast": None,
                "flooded": next(iter(labels)) if len(labels) == 1 else None,
                "location": reports[0]["location"], "description": reports[0]["description"],
                "source_urls": sorted({u for e in reports for u in e["source_urls"]}),
                "reviewer": reports[0]["reviewer"], "review_note": reports[0]["review_note"],
                "evidence": [source for e in reports for source in e.get("evidence", [])],
                "evidence_records": [{k: e.get(k) for k in ("id", "source_ids", "source_checksums", "review_history")}
                                     for e in reports],
                "report_ids": [e["id"] for e in reports], "split": "unassigned"}
        try:
            start, end = day_bounds(day)
            case["split"] = bt.split_of(start + HOUR)
        except (ValueError, TypeError):
            case["reason"] = "No single verified local event date; publication dates cannot substitute"
            cases.append(case)
            continue
        if len(labels) != 1:
            case["reason"] = "Conflicting observed outcomes in duplicate storm reports"
        elif any(e["timing_precision"] not in ("exact", "hour", "day") or dt(e["start_at"]) < start
                 or dt(e["end_at"]) > end for e in reports):
            case["reason"] = "Evidence does not establish one local day"
        elif case["flooded"] and any(e["cause"] != "rainfall" for e in reports):
            case["reason"] = "Rain-associated flooding not established"
        elif not case["flooded"] and not any(dt(e["start_at"]) == start and dt(e["end_at"]) == end for e in reports):
            case["reason"] = "A non-flood label requires explicit monitoring of the entire day"
        else:
            forecast = indexed.get((area, day))
            if not forecast:
                case["reason"] = "No complete cached forecast available for midnight Lagos"
            elif dt(forecast["available_at"]) > start or dt(forecast["issued_at"]) != start:
                case["reason"] = "Forecast was not available at the start of the local day"
            elif dt(forecast["valid_from"]) != start or dt(forecast["valid_until"]) != end:
                case["reason"] = "Forecast does not cover the entire local day"
            else:
                case["forecast"] = forecast
                alert = any(w["risk_tier"] in ("moderate", "high") for w in forecast["windows"])
                case["outcome"] = ("hit" if alert else "miss") if case["flooded"] else (
                    "false_alarm" if alert else "correct_negative")
        cases.append(case)
    # One storm cannot leak across calendar partitions, even when reported in two areas.
    storm_dates = {}
    for case in cases:
        if case["event_date"] and case["split"] != "unassigned":
            storm_dates[case["storm_id"]] = min(case["event_date"], storm_dates.get(case["storm_id"], case["event_date"]))
    for case in cases:
        if case["storm_id"] in storm_dates:
            case["split"] = bt.split_of(day_bounds(storm_dates[case["storm_id"]])[0] + HOUR)
    return cases


def input_hashes(root=None):
    place = bt.paths(root)
    files = {"events": place["events"], "review": place["base"] / "review.json", "manifest": place["manifest"],
             "core_code": Path(__file__).with_name("core.py"), "backtest_code": Path(bt.__file__),
             "daily_code": Path(__file__), "evidence_code": Path(__file__).with_name("evidence.py"),
             "evidence_sources": place["base"] / "sources.json", "rainfall_audit": place["base"] / "rainfall-audit.json"}
    return {k: bt.sha256_file(p) if p.exists() else None for k, p in files.items()}


def sensitivity(events, forecasts, root=None):
    # One whole month, including days with unknown flood outcomes; not an accuracy sample.
    dates = [f"2025-08-{day:02d}" for day in range(1, 32)]
    background, errors = bt.replay(root, daily_dates=dates)
    comparisons = []
    for version in (VERSION, LIVE_VERSION):
        cases = score(events, [rescreen(f, version) for f in forecasts])
        month = [rescreen(f, version) for f in background]
        month_cases = score(events, month)
        reviewed = {(c["area_id"], c["event_date"]) for c in month_cases if c["outcome"] != "unknown"}
        alerts = [f for f in month if any(w["risk_tier"] != "low" for w in f["windows"])]
        comparisons.append({"version": version, "thresholds_mm": rescreen({"windows": []}, version)["thresholds_mm"],
                            "summary": summarize(cases), "cases": cases,
                            "background": {"period": [dates[0], dates[-1]], "expected_area_days": 62,
                                "covered_area_days": len(month), "missing_area_days": 62 - len(month),
                                "alert_area_days": len(alerts),
                                "alert_fraction": len(alerts) / len(month) if month else None,
                                "alerts_without_reviewed_outcome": sum(
                                    (f["area_id"], (dt(f["issued_at"]) + HOUR).date().isoformat()) not in reviewed
                                    for f in alerts)}})
    return {"active_version": LIVE_VERSION, "comparisons": comparisons, "background_errors": errors,
            "always_alert_baseline": {"hits": comparisons[0]["summary"]["flood_cases_scored"],
                                      "misses": 0, "alert_fraction": 1, "false_alarm_ratio": None},
            "interpretation": "Development comparison after inspecting these missed storms, not an independent test. "
                "The sensitive policy lowers moderate thresholds to one quarter and preserves high thresholds. "
                "A hit means an alert on a reported flood day, not proven advance warning. "
                "August alert frequency measures how often the screen would trigger, not its false-alarm rate. "
                "Always alerting also catches every documented case; these positives alone cannot establish skill. "
                "Future storms must be evaluated without changing this version; confidence is unvalidated."}


def run(root=None):
    place = bt.paths(root)
    _, events = bt.load_events(root)
    dates = sorted({e["event_date"] for e in events if e["status"] == "approved" and e.get("event_date")})
    for day in dates:
        day_bounds(day)  # fail cleanly on malformed trusted-register dates
    forecasts, errors = bt.replay(root, daily_dates=dates)
    cases = score(events, forecasts)
    summary = summarize(cases)
    review_path = place["base"] / "review.json"
    review = bt.read_json(review_path) if review_path.exists() else {"groups": [], "sources": {}}
    from .evidence import verify_events
    report = {"resolution": "daily", "evidence_sources": verify_events(events, root), "summary": summary, "cases": cases,
              "by_split": {split: summarize([c for c in cases if c["split"] == split])
                           for split in sorted({c["split"] for c in cases})},
              "by_cycle": {cycle: summarize([c for c in cases if c["forecast"] and c["forecast"]["cycle"] == cycle])
                           for cycle in sorted({f["cycle"] for f in forecasts})},
              "screen": {"version": VERSION, "thresholds_mm": THRESHOLDS, "thresholds_tuned": False},
              "inputs": input_hashes(root), "replay_errors": errors,
              "no_alert_baseline": {"hits": 0, "misses": summary["flood_cases_scored"],
                                    "false_alarms": 0, "false_alarm_ratio": None},
              "candidate_review": review, "sensitivity": sensitivity(events, forecasts, root),
              "rainfall_audit": bt.read_json(place["base"] / "rainfall-audit.json")
                  if (place["base"] / "rainfall-audit.json").exists() else None,
              "limitations": "Daily flood presence in a named area, not exact onset or flooding at the weather point. "
                  "Public-source review by an assistant, not independent field verification. Earlier forecasts supply "
                  "modelled antecedent rain. Cycle 49R1 inputs are hindcasts, not proof of operational forecast skill. "
                  "Reports are selective; unknown dates are not dry days. Small samples cannot establish reliability. "
                  "Flood presence can include water persisting from an earlier onset; daily hits do not prove advance warning.",
              "protocol": "Midnight Africa/Lagos (UTC+1), latest cached run initialized at least six hours earlier; "
                  "available run at most 18 hours old. Any moderate/high six-hour window is a daily alert. "
                  "2024 exploratory; 2025 examples were inspected during sensitive-v2 development and are not an untouched test for that version. Original v1 thresholds remain unchanged. Reserve future storms before further tuning."}
    folder = place["results"] / "daily"
    folder.mkdir(parents=True, exist_ok=True)
    bt.write_json(folder / "report.json", report)
    (folder / "predictions.jsonl").write_text("".join(json.dumps(f, sort_keys=True) + "\n" for f in forecasts))
    with (folder / "episodes.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event_date", "area_id", "storm_id", "split", "outcome", "reason",
                                                   "issued_at", "run_at", "source_urls"])
        writer.writeheader()
        for c in cases:
            writer.writerow({**{k: c[k] for k in ("event_date", "area_id", "storm_id", "split", "outcome", "reason")},
                             "issued_at": (c["forecast"] or {}).get("issued_at"),
                             "run_at": (c["forecast"] or {}).get("run_at"), "source_urls": json.dumps(c["source_urls"])})
    return {"version": VERSION, **summary, "results": str(folder), "reviewed_groups": len(review["groups"]),
            "sensitive_development_result": {"version": LIVE_VERSION,
                **report["sensitivity"]["comparisons"][1]["summary"],
                "background": report["sensitivity"]["comparisons"][1]["background"]}}


def read_report(root=None):
    path = bt.paths(root)["results"] / "daily" / "report.json"
    if not path.exists():
        return {"available": False, "message": "Run the daily historical comparison to generate results."}
    report = bt.read_json(path)
    return {**report, "available": True, "stale": report["inputs"] != input_hashes(root)}
