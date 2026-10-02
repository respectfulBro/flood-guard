import argparse
import getpass
import json
import os
from datetime import datetime, timedelta, timezone

from . import backtest
from .core import database, dt, ingest, iso, now_utc, predict
from .evaluation import evaluate


def main():
    parser = argparse.ArgumentParser(description="FloodGuard research data and review tools")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ingest")
    commands.add_parser("reports")
    commands.add_parser("serve")
    commands.add_parser("demo", help="Offline historical demo with a separate observations database")
    commands.add_parser("replay")
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--split", choices=["train", "validation", "test", "prospective"], default="prospective")
    download = commands.add_parser("backtest-download",
                                   help="One-time import of archived ECMWF IFS runs (needs network)")
    download.add_argument("--start", default="2024-03-14", help="First run date, from 2024-03-14")
    download.add_argument("--end", default=None, help="Last run date, defaults to yesterday UTC")
    commands.add_parser("backtest-groundsource",
                        help="One-time Groundsource import and Lagos candidate filter (needs network)")
    backtest_run = commands.add_parser("backtest-run", help="Offline replay, scoring and export from the cache")
    backtest_run.add_argument("--resolution", choices=["hourly", "daily"], default="hourly")
    rainfall = commands.add_parser("backtest-rainfall-audit", help="Import local NOAA Lagos/Ikeja CSVs for rainfall diagnosis")
    rainfall.add_argument("files", nargs="+")
    source = commands.add_parser("backtest-source-add", help="Cache an article, report, photo, or data source")
    source.add_argument("--url")
    source.add_argument("--file")
    source.add_argument("--refresh", action="store_true")
    collection = commands.add_parser("backtest-source-collect", help="Cache URLs from a JSON urls/candidates list")
    collection.add_argument("file")
    discovery = commands.add_parser("backtest-news-discover", help="Find candidate links in publisher RSS/Atom/sitemaps")
    discovery.add_argument("--url", required=True)
    discovery.add_argument("--terms", default="flood,lekki,ketu,lagos")
    discovery.add_argument("--limit", type=int, default=20)
    event_import = commands.add_parser("backtest-events-import", help="Import pending historical or prospective observations")
    event_import.add_argument("file")
    event_list = commands.add_parser("backtest-events-list")
    event_list.add_argument("--status", choices=backtest.STATUS_VALUES)
    event_review = commands.add_parser("backtest-event-review")
    event_review.add_argument("id")
    event_review.add_argument("--decision", required=True, help="JSON review decision; corrections preserve history")
    commands.add_parser("backtest-rainfall-check", help="Offline interval rainfall diagnosis against archived runs")
    rain_import = commands.add_parser("backtest-rainfall-import", help="Import canonical gauge/satellite interval CSV")
    rain_import.add_argument("file")
    rain_import.add_argument("--source-id", required=True)
    review = commands.add_parser("review")
    review.add_argument("id", type=int)
    review.add_argument("--status", choices=["approved", "rejected"], required=True)
    review.add_argument("--storm", required=True, help="Stable storm/monitoring episode ID shared by duplicate reports")
    review.add_argument("--reviewer", required=True)
    review.add_argument("--note", required=True, help="Verification evidence and reason; not just a confidence guess")
    review.add_argument("--split", choices=["train", "validation", "test", "prospective"], default="prospective")
    args = parser.parse_args()
    if args.command in {"backtest-source-add", "backtest-source-collect", "backtest-news-discover",
                        "backtest-events-import", "backtest-events-list", "backtest-event-review",
                        "backtest-rainfall-import", "backtest-rainfall-check"}:
        from . import evidence
        try:
            if args.command == "backtest-source-add":
                result = evidence.add_source(args.url, args.file, args.refresh)
            elif args.command == "backtest-source-collect":
                payload = backtest.read_json(args.file)
                entries = payload.get("urls", payload.get("candidates", []))
                if not isinstance(entries, list) or not entries:
                    raise ValueError("Supply a nonempty urls or candidates list")
                result = evidence.collect([e["url"] if isinstance(e, dict) else e for e in entries])
            elif args.command == "backtest-news-discover":
                result = evidence.discover(args.url, args.terms, args.limit)
            elif args.command == "backtest-events-import":
                result = evidence.import_events(args.file)
            elif args.command == "backtest-events-list":
                result = [e for e in evidence.read(backtest.paths()["events"], {"events": []})["events"]
                          if not args.status or e["status"] == args.status]
            elif args.command == "backtest-event-review":
                result = evidence.review_event(args.id, args.decision)
            elif args.command == "backtest-rainfall-check":
                result = evidence.check_rainfall()
            else:
                result = evidence.import_rainfall(args.file, args.source_id)
            print(json.dumps(result, indent=2))
            return int(isinstance(result, dict) and bool(result.get("failed") or result.get("errors")))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            print(f"Evidence workflow failed: {exc}")
            return 1
    if args.command in {"serve", "demo"}:
        if args.command == "demo":
            os.environ["PILOT_DEMO"] = "1"
            os.environ["PILOT_INGEST"] = "0"
            from .daily_backtest import run as daily_run
            from .historical_rainfall import run as older_run
            print("Rebuilding historical results from local caches (no downloads)…")
            daily_run()
            older_run()
        if not os.environ.get("PILOT_PASSWORD"):
            os.environ["PILOT_PASSWORD"] = getpass.getpass("Choose a private pilot password (at least 16 characters): ")
        import uvicorn
        uvicorn.run("backend.app:app", host="127.0.0.1", port=8000)
    if args.command == "replay":
        with database() as conn:
            rows = conn.execute("SELECT f.payload AS forecast, i.payload AS weather FROM forecasts f JOIN inputs i ON f.input_id=i.id").fetchall()
        for row in rows:
            forecast = json.loads(row["forecast"])
            reproduced = predict(json.loads(row["weather"]), dt(forecast["issued_at"]), forecast["version"])
            if reproduced["version"] != forecast["version"] or reproduced["windows"] != forecast["windows"]:
                parser.error("Replay differs: restore the archived model version before evaluating")
        print(f"Reproduced {len(rows)} archived forecasts")
    if args.command == "ingest":
        result = ingest()
        print(json.dumps(result, indent=2))
        return 0 if all(r["success"] for r in result) else 1
    if args.command == "evaluate":
        print(json.dumps(evaluate(split=args.split), indent=2))
    if args.command == "reports":
        with database() as conn:
            print(json.dumps([dict(r) for r in conn.execute("SELECT * FROM reports ORDER BY id DESC")], indent=2))
    if args.command == "review":
        if not args.storm.strip() or not args.reviewer.strip() or len(args.note.strip()) < 10:
            parser.error("Supply a storm ID, reviewer, and meaningful verification note")
        with database() as conn:
            report = conn.execute("SELECT * FROM reports WHERE id=?", (args.id,)).fetchone()
            if not report:
                parser.error("Report not found")
            if report["status"] != "pending":
                parser.error("Already reviewed: preserve the audit record; submit a corrected report instead")
            if conn.execute("SELECT 1 FROM reports WHERE storm_id=? AND split<>? AND status='approved'",
                            (args.storm, args.split)).fetchone():
                parser.error("A storm must stay in one evaluation split across all areas")
            conn.execute("UPDATE reports SET status=?,storm_id=?,reviewer=?,review_note=?,reviewed_at=?,split=? WHERE id=?",
                         (args.status, args.storm.strip(), args.reviewer.strip(), args.note.strip(), iso(now_utc()), args.split, args.id))
        print(f"Report {args.id}: {args.status}")
    if args.command == "backtest-download":
        try:
            start = datetime.strptime(args.start, "%Y-%m-%d").date()
            end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else (now_utc() - timedelta(days=1)).date()
        except ValueError:
            parser.error("--start and --end must be YYYY-MM-DD")
        if start < backtest.ARCHIVE_START.date() or end < start or end >= now_utc().date():
            parser.error("Dates must be ordered, from 2024-03-14 through yesterday UTC")
        try:
            result = backtest.download(start, end)
        except OSError as exc:
            print(f"Import failed: {exc}")
            return 1
        print(json.dumps(result, indent=2))
        return 1 if result["failed"] else 0
    if args.command == "backtest-groundsource":
        try:
            print(json.dumps(backtest.groundsource(), indent=2))
        except (ValueError, OSError) as exc:
            print(f"Groundsource import failed: {exc}")
            return 1
    if args.command == "backtest-run":
        try:
            if args.resolution == "daily":
                from .daily_backtest import run
            else:
                run = backtest.run
            print(json.dumps(run(), indent=2))
        except (ValueError, AssertionError) as exc:
            print(f"Backtest failed: {exc}")
            return 1
    if args.command == "backtest-rainfall-audit":
        from .rainfall_audit import run
        try:
            print(json.dumps(run(args.files), indent=2))
        except (ValueError, KeyError, OSError) as exc:
            print(f"Rainfall audit failed: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
