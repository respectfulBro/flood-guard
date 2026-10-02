"""Run with: .venv/bin/python -m unittest backend.test_backtest -v"""
import hashlib
import io
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote

from . import backtest as bt
from .core import AREAS, HOUR, UTC, dt


def run_payload(init, spike=None):
    values = [0.0] * (bt.PAST_HOURS + bt.FORECAST_HOURS + 1)
    for offset, mm in (spike or {}).items():
        values[bt.PAST_HOURS + offset] = mm
    times = [init + (i - bt.PAST_HOURS) * HOUR for i in range(len(values))]
    return {"latitude": 6.4474, "longitude": 3.4723, "utc_offset_seconds": 0,
            "hourly_units": {"precipitation": "mm"},
            "hourly": {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in times], "precipitation": values}}


def init_from(url):
    run = unquote([part for part in url.split("&") if part.startswith("run=")][0][4:])
    return datetime.strptime(run, "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)


def spiked(url):
    # Lekki is the first requested coordinate, so its payload carries the spike.
    return json.dumps([run_payload(init_from(url), {13: 20}), run_payload(init_from(url))]).encode()


def dry(url):
    return json.dumps([run_payload(init_from(url)) for _ in AREAS]).encode()


def event(**overrides):
    base = {"id": "e1", "status": "approved", "area_id": "lekki", "storm_id": "storm-1",
            "location": "Lekki Phase 1, Lagos", "description": "Rainfall flooding on the pilot street.",
            "flooded": True, "cause": "rainfall", "start_at": "2025-07-01T12:00:00Z",
            "end_at": "2025-07-01T12:00:00Z", "timing_precision": "hour",
            "source_urls": ["https://example.org/report"], "satellite_evidence": "",
            "reviewer": "researcher", "reviewed_at": "2025-07-02T00:00:00Z",
            "review_note": "Checked against the reviewed flood-history report and news photos."}
    return {**base, **overrides}


def seeded(root, events, fetch=spiked, days=1):
    Path(root, "events.json").write_text(json.dumps({"events": events}))
    start = date(2025, 7, 1) - timedelta(days=days - 1)
    return bt.download(start, date(2025, 7, 1), root=root, fetch=fetch)


def score_cached(root):
    _, events = bt.load_events(root)
    rows, errors = bt.replay(root)
    return bt.score(events, rows, gaps=0, replay_errors=len(errors))


class BacktestChecks(unittest.TestCase):
    def test_download_caches_verifies_and_never_redownloads(self):
        with tempfile.TemporaryDirectory() as root:
            result = seeded(root, [])
            self.assertEqual(result["imported"], 4)  # four six-hourly runs per day
            self.assertEqual(result["failed"], 0)

            def offline(url):
                raise AssertionError("cached runs must not be refetched")

            repeat = bt.download(date(2025, 7, 1), date(2025, 7, 1), root=root, fetch=offline)
            self.assertEqual((repeat["imported"], repeat["skipped_cached"]), (0, 4))
            manifest = bt.read_json(bt.paths(root)["manifest"])
            for key, entry in manifest.items():
                self.assertEqual(bt.sha256_file(bt.paths(root)["runs"] / f"{key}.json"), entry["sha256"])
                self.assertEqual(bt.parse_key(key).hour % 6, 0)

    def test_replay_runs_unchanged_rules_with_simulated_issue_time(self):
        with tempfile.TemporaryDirectory() as root:
            seeded(root, [])
            rows, errors = bt.replay(root)
            self.assertEqual(errors, [])
            self.assertEqual(len(rows), 8)  # 4 runs x 2 pilot areas
            first = rows[0]
            self.assertEqual((first["run_at"], first["issued_at"], first["version"]),
                             ("2025-07-01T00:00:00Z", "2025-07-01T06:00:00Z", "rainfall-screen-v1"))
            self.assertEqual(len(first["windows"]), 4)
            self.assertEqual(first["cycle"], "ifs-49r1")
            spike = next(r for r in rows if r["area_id"] == "lekki" and r["run_at"] == "2025-07-01T00:00:00Z")
            self.assertEqual(spike["windows"][1]["risk_tier"], "high")  # 20 mm/h ending 13:00
            self.assertEqual(spike["windows"][0]["risk_tier"], "low")

    def test_scoring_counts_hits_misses_false_alarms_and_unknowns(self):
        with tempfile.TemporaryDirectory() as root:
            seeded(root, [
                event(),
                event(id="e2", storm_id="storm-1", end_at="2025-07-01T13:00:00Z"),  # duplicate report
                event(id="e3", storm_id="storm-2", flooded=False,
                      description="Rain fell, street stayed dry through the monitored window.",
                      start_at="2025-07-01T18:00:00Z", end_at="2025-07-01T18:00:00Z"),
                event(id="e4", storm_id="storm-3", start_at="2025-07-01T12:00:00Z",
                      end_at="2025-07-01T20:00:00Z", timing_precision="day"),  # too coarse to score
                event(id="e5", storm_id="storm-4", status="pending"),
            ])
            scores, episodes = score_cached(root)
            self.assertEqual(len(episodes), 3)  # duplicate merged; pending never scored
            merged = next(e for e in episodes if e["storm_id"] == "storm-1")
            self.assertEqual((merged["reports"], merged["event_outcome"]), (2, "detected"))
            lead6 = next(l for l in merged["leads"] if l["lead_target_hours"] == 6)
            self.assertEqual((lead6["outcome"], lead6["actual_lead_hours"], lead6["risk_tiers"]),
                             ("hit", 6.0, ["high"]))
            self.assertTrue(all(l["outcome"] == "unknown" and l["matched_run_at"] is None
                                for l in merged["leads"][1:]))  # no runs near the longer leads
            coarse = next(e for e in episodes if e["storm_id"] == "storm-3")
            self.assertTrue(all("coarse" in l["reason"] for l in coarse["leads"]))
            self.assertEqual(scores["episodes"]["unscored_register_entries"], {"pending": 1})
            self.assertEqual(scores["status"], "inconclusive")  # under the evidence floor
            self.assertIsNone(scores["overall"]["detection_rate"])  # no misleading percentage
            self.assertEqual((scores["overall"]["by_lead"][6]["hits"],
                              scores["overall"]["by_lead"][6]["false_alarms"],
                              scores["overall"]["by_lead"][6]["unknowns"]), (1, 1, 1))
            self.assertEqual(scores["lead_time_hours"]["values"], [6.0])
            self.assertEqual(scores["checks"]["duplicate_report_storms"], ["storm-1"])
            self.assertEqual(scores["checks"]["coarse_timing_episodes"], 1)
            self.assertEqual(scores["no_alert_baseline"]["missed"], 1)
            self.assertEqual(scores["by_split"]["test-2025"]["event_outcomes"]["detected"], 1)
        with tempfile.TemporaryDirectory() as root:  # a dry archive turns the same flood into a miss
            seeded(root, [event()], fetch=dry, days=2)  # two days cover the shorter leads
            scores, episodes = score_cached(root)
            self.assertEqual(scores["overall"]["by_lead"][6]["misses"], 1)
            self.assertEqual(episodes[0]["event_outcome"], "missed")
            self.assertEqual(scores["episodes"]["event_outcomes"], {"missed": 1})
            # The final horizon endpoint is included for a precisely timed onset.
            self.assertEqual(episodes[0]["leads"][3]["outcome"], "miss")

    def test_run_exports_deterministic_audit_and_score_files(self):
        with tempfile.TemporaryDirectory() as root:
            seeded(root, [event()])
            first = bt.run(root)
            outputs = {name: Path(bt.paths(root)["results"], name).read_text()
                       for name in ["scores.json", "episodes.jsonl", "predictions.jsonl"]}
            second = bt.run(root)
            self.assertEqual(first, second)
            for name, content in outputs.items():
                self.assertEqual(Path(bt.paths(root)["results"], name).read_text(), content)
            scores = bt.read_json(bt.paths(root)["results"] / "scores.json")
            self.assertTrue(scores["reproducible"])
            self.assertEqual(scores["inputs"]["runs_imported"], 4)
            self.assertEqual(scores["inputs"]["runs_by_cycle"], {"ifs-49r1": 4})
            audit = [json.loads(line) for line in
                     (bt.paths(root)["results"] / "episodes.jsonl").read_text().splitlines()]
            self.assertEqual(len(audit), 4)  # one auditable row per lead, evidence included
            hit = next(r for r in audit if r["outcome"] == "hit")
            self.assertEqual(hit["source_urls"], ["https://example.org/report"])
            self.assertEqual(hit["matched_run_at"], "2025-07-01T00:00:00Z")
            self.assertEqual(hit["split"], "test-2025")

    def test_register_validation_rejects_unusable_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "events.json").write_text(json.dumps({"events": [
                event(id="bad-tz", start_at="2025-07-01T12:00:00"),  # naive timestamp
                event(id="bad-area", area_id="ikoyi"),
                event(id="bad-urls", source_urls=["not-a-link"]),
                event(id="bad-note", review_note="ok"),
                event(id="e1"), event(id="e1"),
            ]}))
            with self.assertRaises(ValueError) as caught:
                bt.load_events(root)
            for fragment in ["bad-tz", "bad-area", "bad-urls", "bad-note", "duplicate id"]:
                self.assertIn(fragment, str(caught.exception))

    def test_split_and_cycle_labels_follow_the_documented_boundaries(self):
        self.assertEqual(bt.split_of(dt("2024-07-01T00:00:00Z")), "exploration-2024")
        self.assertEqual(bt.split_of(dt("2025-02-01T00:00:00Z")), "test-2025")
        self.assertEqual(bt.split_of(dt("2026-09-01T00:00:00Z")), "partial-2026")
        self.assertEqual(bt.cycle_of(dt("2026-05-12T05:00:00Z")), "ifs-49r1")
        self.assertEqual(bt.cycle_of(dt("2026-05-12T06:00:00Z")), "ifs-50r1")

    def test_window_boundary_straddle_is_unknown_not_guessed(self):
        with tempfile.TemporaryDirectory() as root:
            # The spike makes 06-12 low and 12-18 high; an 11:00-13:00 episode overlaps
            # both, so its alert state is genuinely ambiguous.
            seeded(root, [event(start_at="2025-07-01T11:00:00Z", end_at="2025-07-01T13:00:00Z")])
            scores, episodes = score_cached(root)
            lead6 = next(l for l in episodes[0]["leads"] if l["lead_target_hours"] == 6)
            self.assertEqual(lead6["outcome"], "unknown")
            self.assertIn("different risk tiers", lead6["reason"])

    def test_real_api_shape_uses_only_earlier_runs_for_antecedents(self):
        def archive(url):
            payloads = json.loads(dry(url))
            for p in payloads:
                for name in ("time", "precipitation"):
                    p["hourly"][name] = p["hourly"][name][bt.PAST_HOURS:bt.PAST_HOURS + 48]
                p["hourly"]["precipitation"][0] = None
            return json.dumps(payloads).encode()
        with tempfile.TemporaryDirectory() as root:
            seeded(root, [], fetch=archive, days=2)
            rows, errors = bt.replay(root)
            self.assertTrue(errors)  # first runs have no antecedents
            self.assertTrue(rows)
            for row in rows:
                self.assertTrue(all(bt.parse_key(k) <= dt(row["run_at"]) for k in row["input_runs"]))
            self.assertIn("single-runs-api.open-meteo.com", rows[0]["source_url"])

    def test_coverage_precision_and_small_subgroups_do_not_invent_skill(self):
        with tempfile.TemporaryDirectory() as root:
            seeded(root, [], days=2)
            rows, _ = bt.replay(root)
            coarse = event(timing_precision="day")
            scores, episodes = bt.score([coarse], rows)
            self.assertEqual(episodes[0]["event_outcome"], "unknown")
            flood_events = [event(id=str(i), storm_id=str(i)) for i in range(5)]
            scores, _ = bt.score(flood_events, rows)
            self.assertIsNone(scores["overall"]["false_alarm_ratio"])
            self.assertIsNone(scores["no_alert_baseline"]["false_alarm_ratio"])
            one = {**rows[-1], "area_id": "lekki"}
            onset = dt(one["valid_until"]) - HOUR
            episode = bt.score_episode([event(start_at=bt.iso(onset), end_at=bt.iso(onset + 2 * HOUR))], {"lekki": [one]})
            self.assertTrue(all(l["outcome"] == "unknown" for l in episode["leads"]))

    def test_cli_rejects_invalid_date_ranges(self):
        import subprocess
        import sys
        for start, end in [("2025-07-02", "2025-07-01"), ("2025-07-02", "nonsense")]:
            result = subprocess.run([sys.executable, "-m", "backend", "backtest-download",
                                     "--start", start, "--end", end], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)

    def test_groundsource_filters_candidates_and_verifies_checksum(self):
        import pyarrow as pa
        import pyarrow.parquet as pq

        import shapely
        buffer = io.BytesIO()
        table = pa.table({"uuid": ["lagos", "berlin", "lekki"],
                          "geometry": [shapely.box(3.3, 6.4, 3.5, 6.7).wkb,
                                       shapely.box(13, 52, 14, 53).wkb,
                                       shapely.box(3.4, 6.4, 3.5, 6.5).wkb],
                          "start_date": ["2024-07-03"] * 3, "end_date": ["2024-07-03"] * 3})
        table = table.replace_schema_metadata({b"geo": json.dumps({"columns": {"geometry": {
            "encoding": "WKB", "crs": {"id": {"authority": "EPSG", "code": 4326}}}}}).encode()})
        pq.write_table(table, buffer)
        blob = buffer.getvalue()
        record = {"links": {"self_html": "https://zenodo.org/records/18647054"},
                  "files": [{"key": "groundsource_2026.parquet", "size": len(blob),
                             "checksum": "md5:" + hashlib.md5(blob).hexdigest(),
                             "links": {"self": "https://zenodo.org/files/groundsource_2026.parquet/content"}}]}

        with tempfile.TemporaryDirectory() as root:
            def fake_stream(url, target):
                Path(target).write_bytes(blob)
                return hashlib.md5(blob).hexdigest(), len(blob)

            result = bt.groundsource(root, fetch=lambda url: json.dumps(record).encode(),
                                     stream=fake_stream)
            self.assertEqual(result["matches"], 2)  # Berlin row filtered out
            candidates = bt.read_json(result["candidates"])
            self.assertIn("not verified events", candidates["note"])
            self.assertEqual({c["uuid"] for c in candidates["candidates"]}, {"lagos", "lekki"})
            with self.assertRaises(ValueError):  # a corrupted download fails its checksum
                corrupted = dict(record["files"][0])
                corrupted["checksum"] = "md5:" + "0" * 32
                bad = {**record, "files": [corrupted]}
                Path(bt.paths(root)["groundsource"], "groundsource_2026.parquet").unlink()

                def corrupt_stream(url, target):
                    Path(target).write_bytes(blob + b"x")
                    return hashlib.md5(blob + b"x").hexdigest(), len(blob) + 1

                bt.groundsource(root, fetch=lambda url: json.dumps(bad).encode(),
                                stream=corrupt_stream)


if __name__ == "__main__":
    unittest.main()
