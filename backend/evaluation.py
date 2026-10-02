"""Prospective evaluation against explicitly reviewed observations; unknown is not dry."""
import json
import math
from statistics import mean

from .core import HOUR, LIVE_VERSION, database, dt


def wilson(successes, total):
    if not total:
        return None
    p, z = successes / total, 1.96
    center = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [round(max(0, center - half), 4), round(min(1, center + half), 4)]


def score(reports, forecasts, lead_hours=6):
    groups = {}
    for report in reports:
        if report["status"] != "approved" or not report["storm_id"]:
            continue
        if report["flooded"] and report["cause"] != "rainfall":
            continue
        groups.setdefault((report["area_id"], report["storm_id"]), []).append(report)
    counts = dict(hits=0, misses=0, false_alarms=0, correct_negatives=0, excluded=0)
    leads, cases = [], []
    for (area, storm), observations in groups.items():
        start = min(dt(r["start_at"]) for r in observations)
        end = max(dt(r["end_at"]) for r in observations)
        labels = {r["flooded"] for r in observations}
        case = {"area_id": area, "storm_id": storm, "start_at": start.isoformat(), "outcome": "excluded"}
        # Broad/contradictory observations cannot establish six-hour timing skill.
        if len(labels) != 1 or end - start > 6 * HOUR:
            counts["excluded"] += 1
            case["reason"] = "Conflicting labels or onset/observation interval wider than six hours"
            cases.append(case)
            continue
        cutoff = start - lead_hours * HOUR
        candidates = [f for f in forecasts if f["area_id"] == area
                      and cutoff - 2 * HOUR <= dt(f["issued_at"]) <= cutoff
                      and dt(f["valid_from"]) <= start and dt(f["valid_until"]) >= end]
        if not candidates:
            counts["excluded"] += 1
            case["reason"] = "No archived forecast available at this lead time"
            cases.append(case)
            continue
        forecast = max(candidates, key=lambda f: f["issued_at"])
        windows = [w for w in forecast["windows"] if dt(w["start_at"]) <= end and dt(w["end_at"]) > start
                   and (start == end or dt(w["start_at"]) < end)]
        alarms = {w["risk_tier"] in ("moderate", "high") for w in windows}
        if len(alarms) != 1:
            counts["excluded"] += 1
            case["reason"] = "Uncertain timing spans different risk classifications"
            cases.append(case)
            continue
        alarm, flooded = alarms.pop(), bool(next(iter(labels)))
        outcome = "hits" if alarm and flooded else "misses" if flooded else "false_alarms" if alarm else "correct_negatives"
        counts[outcome] += 1
        case.update(outcome=outcome, issued_at=forecast["issued_at"])
        if outcome == "hits":
            lead = (start - dt(forecast["issued_at"])).total_seconds() / 3600
            leads.append(lead)
            case["lead_time_hours"] = round(lead, 2)
        cases.append(case)
    h, m, fa = counts["hits"], counts["misses"], counts["false_alarms"]
    has_negatives = fa + counts["correct_negatives"] > 0
    return {**counts, "lead_hours": lead_hours, "detection_rate": h / (h + m) if h + m else None,
            "false_alarm_ratio": fa / (h + fa) if has_negatives and h + fa else None,
            "detection_interval": wilson(h, h + m), "false_alarm_interval": wilson(fa, h + fa) if has_negatives else None,
            "mean_lead_hours": round(mean(leads), 2) if leads else None, "cases": cases}


def evaluate(path=None, split="prospective"):
    # ponytail: scan the small pilot archive; aggregate in SQL when archive size affects latency.
    with database(path) as conn:
        reports = [dict(r) for r in conn.execute("SELECT * FROM reports WHERE split=?", (split,))]
        forecasts = [{**json.loads(r["payload"]), "area_id": r["area_id"]}
                     for r in conn.execute("SELECT * FROM forecasts WHERE version=?", (LIVE_VERSION,))]
        pending = conn.execute("SELECT count(*) FROM reports WHERE status='pending'").fetchone()[0]
    summary = score(reports, forecasts)
    return {"version": LIVE_VERSION, "split": split, "status": "research_only", "pending_reports": pending,
            "approved_reports": sum(r["status"] == "approved" for r in reports),
            "archived_forecasts": len(forecasts), "summary": summary,
            "by_lead": [summary, score(reports, forecasts, 12), score(reports, forecasts, 18)],
            "by_area": {area: score([r for r in reports if r["area_id"] == area], forecasts)
                        for area in sorted({r["area_id"] for r in reports})},
            "limitations": "Moderate/high rainfall screening counts as an alert. One case per area/storm at each lead. "
                            "Unreported outcomes are unknown. Wilson intervals are descriptive; areas in the same storm are correlated. "
                            "No accuracy claim or release decision follows from a small or selectively reported sample."}
