"""Run with: .venv/bin/python -m unittest backend.test_pilot -v"""
import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from .app import app
from .core import AREAS, HOUR, UTC, LIVE_VERSION, VERSION, database, ingest, iso, list_areas, predict, rescreen
from .evaluation import evaluate, score

NOW = datetime(2026, 7, 1, 10, tzinfo=UTC)


def weather(mm=0):
    times = [NOW + (n - 72) * HOUR for n in range(144)]
    return {"latitude": 6.4, "longitude": 3.4, "utc_offset_seconds": 0,
            "hourly_units": {"precipitation": "mm"},
            "hourly": {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in times], "precipitation": [mm] * len(times)}}


def source(_url):
    if "meta.json" in _url:
        return {"last_run_initialisation_time": (NOW - 4 * HOUR).timestamp(),
                "last_run_availability_time": (NOW - HOUR).timestamp()}
    return weather()


def observation(**overrides):
    return {"area_id": "lekki", "storm_id": "storm-one", "status": "approved", "cause": "rainfall",
            "start_at": iso(NOW + 6 * HOUR), "end_at": iso(NOW + 6 * HOUR), "flooded": True, **overrides}


class PilotChecks(unittest.TestCase):
    def test_sensitive_version_preserves_baseline_and_does_not_invent_confidence(self):
        original = predict(weather(1), NOW)
        sensitive = predict(weather(1), NOW, LIVE_VERSION)
        self.assertEqual(original['version'], VERSION)
        self.assertTrue(all(w['risk_tier'] == 'low' for w in original['windows']))
        self.assertTrue(all(w['risk_tier'] == 'moderate' for w in sensitive['windows']))
        self.assertEqual(sensitive, rescreen(original, LIVE_VERSION))
        self.assertEqual(rescreen(sensitive, VERSION), original)
        self.assertIsNone(sensitive['probability'])
        self.assertEqual(sensitive['confidence']['status'], 'unvalidated')
        self.assertTrue(all(w['risk_tier'] == 'low' for w in predict(weather(), NOW, LIVE_VERSION)['windows']))
        self.assertTrue(all(w['risk_tier'] == 'high' for w in predict(weather(20), NOW, LIVE_VERSION)['windows']))
        with self.assertRaises(ValueError):
            predict(weather(), NOW, 'made-up-version')

    def test_rainfall_windows_units_boundaries_and_missing_inputs(self):
        data = weather(1)
        f = predict(data, NOW)
        self.assertEqual(len(f["windows"]), 4)
        self.assertEqual(f["windows"][0]["rainfall_mm"], 6)
        self.assertEqual(f["windows"][0]["peaks_mm"], {"1": 1, "3": 3, "6": 6, "24": 24})
        self.assertEqual(f["windows"][0]["start_at"], iso(NOW))
        self.assertEqual(predict(data, NOW + timedelta(minutes=1))["valid_from"], iso(NOW + HOUR))
        # A 20 mm hour is high, and accumulation is backward-looking.
        data["hourly"]["precipitation"][73] = 20
        self.assertEqual(predict(data, NOW)["windows"][0]["risk_tier"], "high")
        for value in [None, -1, float("nan"), True]:
            bad = weather()
            bad["hourly"]["precipitation"][73] = value
            with self.assertRaises(ValueError):
                predict(bad, NOW)
        bad = weather()
        bad["hourly_units"]["precipitation"] = "inch"
        with self.assertRaises(ValueError):
            predict(bad, NOW)
        bad = weather()
        bad["hourly"]["time"][73] = bad["hourly"]["time"][72]
        with self.assertRaises(ValueError):
            predict(bad, NOW)
        with self.assertRaises(ValueError):
            predict(weather(), NOW + 100 * HOUR)

    def test_ingestion_archive_idempotency_failure_and_staleness(self):
        with tempfile.TemporaryDirectory() as directory:
            path = directory + "/pilot.db"
            self.assertTrue(all(a["risk_tier"] == "unavailable" for a in list_areas(path, NOW)))
            self.assertTrue(all(r["success"] for r in ingest(path, source, lambda: NOW)))
            ingest(path, source, lambda: NOW)
            with database(path) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM forecasts").fetchone()[0], len(AREAS))
                raw = conn.execute("SELECT payload FROM inputs LIMIT 1").fetchone()[0]
                self.assertEqual(json.loads(raw), weather())
            self.assertTrue(all(a["data_status"] == "fresh" for a in list_areas(path, NOW + HOUR)))
            def broken(_url):
                raise OSError("Feed offline")
            ingest(path, broken, lambda: NOW + 3 * HOUR)
            stale = list_areas(path, NOW + 3 * HOUR)
            self.assertTrue(all(a["risk_tier"] == "stale" for a in stale))
            self.assertTrue(all(a["forecast"] and not a["last_check"]["success"] for a in stale))
            self.assertTrue(all(a["data_status"] == "stale" for a in list_areas(path, NOW + 30 * HOUR)))

    def test_event_scoring_deduplicates_excludes_unknowns_and_counts_misses(self):
        low = {**predict(weather(), NOW), "area_id": "lekki"}
        high = {**predict(weather(20), NOW), "area_id": "lekki"}
        report = observation()
        self.assertEqual(score([report, report], [low])["misses"], 1)
        result = score([report], [high, high])
        self.assertEqual(result["hits"], 1)
        self.assertEqual(result["mean_lead_hours"], 6)
        self.assertEqual(score([observation(flooded=False)], [high])["false_alarms"], 1)
        self.assertIsNone(score([observation(flooded=False)], [high])["mean_lead_hours"])
        self.assertEqual(score([observation(status="pending")], [high])["hits"], 0)
        self.assertEqual(score([observation(cause="coastal")], [high])["hits"], 0)
        self.assertEqual(score([report], [])["excluded"], 1)
        late = copy.deepcopy(high)
        late["issued_at"] = iso(NOW + 7 * HOUR)
        self.assertEqual(score([report], [late])["hits"], 0)
        self.assertEqual(score([report, observation(flooded=False)], [high])["excluded"], 1)
        self.assertEqual(score([observation(end_at=iso(NOW + 14 * HOUR))], [high])["excluded"], 1)
        uncertain = observation(start_at=iso(NOW + 5 * HOUR), end_at=iso(NOW + 7 * HOUR))
        mixed = copy.deepcopy(high)
        mixed["issued_at"] = iso(NOW - HOUR)
        mixed["windows"][1]["risk_tier"] = "low"
        self.assertEqual(score([uncertain], [mixed])["excluded"], 1)

    def test_private_api_validates_and_persists_pending_reports(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {
            "FLOODGUARD_DB": directory + "/pilot.db", "PILOT_PASSWORD": "local-test-password-only", "PILOT_INGEST": "0"
        }):
            with TestClient(app) as client:
                for route in ["/", "/api/areas", "/api/evaluation", "/api/health", "/assets/app.js"]:
                    self.assertEqual(client.get(route).status_code, 401)
                client.auth = ("researcher", "local-test-password-only")
                self.assertEqual(client.get("/api/areas/unknown").status_code, 404)
                self.assertEqual(client.get("/api/areas").json()[0]["risk_tier"], "unavailable")
                payload = {k: v for k, v in observation().items() if k not in ("storm_id", "status")}
                payload["description"] = "Observed flooding across the road at the research location."
                self.assertEqual(client.post("/api/reports", json=payload).status_code, 403)
                headers = {"X-Pilot-Request": "1"}
                self.assertEqual(client.post("/api/reports", json={**payload, "area_id": "unknown"}, headers=headers).status_code, 422)
                self.assertEqual(client.post("/api/reports", json={**payload, "status": "approved"}, headers=headers).status_code, 422)
                self.assertEqual(client.post("/api/reports", json={**payload, "source_url": "javascript:alert(1)"}, headers=headers).status_code, 422)
                self.assertEqual(client.post("/api/reports", json=payload, headers={**headers, "Sec-Fetch-Site": "cross-site"}).status_code, 403)
                result = client.post("/api/reports", json=payload, headers=headers)
                self.assertEqual(result.status_code, 201, result.text)
                self.assertEqual(result.json()["status"], "pending")
                self.assertEqual(client.post("/api/reports", content=b"x" * 33000, headers={**headers, "Content-Type": "application/json"}).status_code, 413)
            # A new connection/process sees the same pending observation.
            with database() as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM reports").fetchone()[0], 1)
            self.assertEqual(evaluate()["pending_reports"], 1)
            self.assertIsNone(evaluate()["summary"]["detection_rate"])

class DemoChecks(unittest.TestCase):
    def test_demo_area_endpoints_use_dated_cache_and_reject_stale_results(self):
        from .app import areas, area, forecast
        f = {**predict(weather(1), NOW, LIVE_VERSION), 'run_at': iso(NOW), 'grid': [6.5, 3.5]}
        report = {'available': True, 'stale': False, 'sensitivity': {'comparisons': [
            {'version': LIVE_VERSION, 'cases': [{'area_id': a['id'], 'event_date': '2024-07-03', 'forecast': f} for a in AREAS]}]}}
        empty = [{**a, 'forecast': None, 'risk_tier': 'unavailable', 'data_status': 'unavailable'} for a in AREAS]
        with patch.dict(os.environ, {'PILOT_DEMO': '1'}), patch('backend.app.list_areas', side_effect=lambda: copy.deepcopy(empty)), patch('backend.app.read_report', return_value=report):
            self.assertTrue(all(a['data_status'] == 'historical' for a in areas()))
            self.assertEqual(area('lekki')['event_date'], '2024-07-03')
            self.assertEqual(forecast('lekki')['forecast']['windows'], f['windows'])
            self.assertEqual(area('lekki')['risk_tier'], 'moderate')
            report['stale'] = True
            self.assertIsNone(area('lekki')['forecast'])
            self.assertEqual(area('lekki')['data_status'], 'unavailable')
            with patch.dict(os.environ, {'PILOT_DEMO': '0'}):
                self.assertEqual(areas(), empty)

    def test_demo_isolates_reports_and_never_starts_ingestion(self):
        from pathlib import Path
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
            'PILOT_DEMO': '1', 'PILOT_INGEST': '1', 'PILOT_PASSWORD': 'local-test-password-only',
            'FLOODGUARD_DB': folder + '/live.db',
        }), patch('backend.app.DEMO_DB', Path(folder) / 'demo.db'), patch('backend.app.collect_hourly') as collect:
            with TestClient(app) as client:
                for route in ['/api/session', '/api/backtest', '/api/historical-rainfall']:
                    self.assertEqual(client.get(route).status_code, 401)
                client.auth = ('researcher', 'local-test-password-only')
                self.assertTrue(client.get('/api/session').json()['demo'])
                payload = {'area_id': 'lekki', 'start_at': '2024-07-03T08:00:00+01:00',
                           'end_at': '2024-07-03T09:00:00+01:00', 'flooded': True,
                           'cause': 'rainfall', 'description': 'Synthetic demo observation only'}
                response = client.post('/api/reports', json=payload, headers={'X-Pilot-Request': '1'})
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()['status'], 'pending')
                self.assertEqual(client.get('/api/evaluation').json()['pending_reports'], 1)
            collect.assert_not_called()
            self.assertFalse((Path(folder) / 'live.db').exists())
            with database(Path(folder) / 'demo.db') as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM reports').fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
