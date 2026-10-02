import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from . import backtest as bt
from . import daily_backtest as daily
from .app import app
from .core import HOUR, dt, iso
from .test_backtest import dry, event, init_from, run_payload
from .rainfall_audit import precipitation, run as rainfall_audit


def daily_event(**overrides):
    start, end = daily.day_bounds('2025-07-02')
    return event(event_date='2025-07-02', start_at=iso(start), end_at=iso(end),
                 timing_precision='day', **overrides)


class DailyChecks(unittest.TestCase):
    def test_station_quality_and_provenance_do_not_create_flood_labels(self):
        self.assertEqual(precipitation({'PRCP': '6.14', 'PRCP_ATTRIBUTES': 'F'})['reported_mm'], 155.96)
        self.assertEqual(precipitation({'PRCP': '1.42', 'PRCP_ATTRIBUTES': 'E'})['quality'], 'partial_period')
        for value, flag in [('99.99', 'F'), ('0', 'H'), ('0', 'I'), ('1', ''), ('nan', 'G'), ('-1', 'G')]:
            self.assertIsNone(precipitation({'PRCP': value, 'PRCP_ATTRIBUTES': flag})['reported_mm'])
        with tempfile.TemporaryDirectory() as root:
            register = Path(root) / 'events.json'
            bt.write_json(register, {'events': [daily_event()]})
            original = register.read_bytes()
            station = Path(root) / 'station.csv'
            station.write_text('STATION,DATE,LATITUDE,LONGITUDE,NAME,PRCP,PRCP_ATTRIBUTES\n'
                               '65201099999,2025-07-02,6.577,3.321,Ikeja,1.42,E\n')
            report = rainfall_audit([station], root)
            self.assertEqual(register.read_bytes(), original)
            self.assertEqual(report['cases'][0]['observations'][1]['reported_mm'], 36.07)
            self.assertFalse(report['cases'][0]['observations'][0]['record_present'])
            cached = Path(root) / report['sources'][0]['cache_file']
            self.assertEqual(bt.sha256_file(cached), report['sources'][0]['sha256'])

    def test_sensitive_background_keeps_unobserved_alerts_unknown(self):
        with tempfile.TemporaryDirectory() as root:
            def wet(url):
                return json.dumps([run_payload(init_from(url), {hour: 1 for hour in range(1, 49)}) for _ in bt.AREAS]).encode()
            bt.download(date(2025, 8, 2), date(2025, 8, 3), root, wet)
            start, end = daily.day_bounds('2025-08-04')
            e = {**daily_event(), 'event_date': '2025-08-04', 'start_at': iso(start), 'end_at': iso(end)}
            forecasts, _ = bt.replay(root, daily_dates=['2025-08-04'])
            comparison = daily.sensitivity([e], forecasts, root)
            original, sensitive = comparison['comparisons']
            self.assertEqual(original['summary']['misses'], 1)
            self.assertEqual(sensitive['summary']['hits'], 1)
            self.assertIsNone(sensitive['summary']['false_alarm_ratio'])
            self.assertGreater(sensitive['background']['alerts_without_reviewed_outcome'], 0)
            self.assertGreater(sensitive['background']['missing_area_days'], 0)

    def test_midnight_forecast_cannot_use_later_runs(self):
        with tempfile.TemporaryDirectory() as root:
            def fetch(url):
                init = init_from(url)
                # A later, unavailable run says heavy rain; the earlier available run is dry.
                return json.dumps([run_payload(init, {13: 40} if init.hour == 18 else {}) for _ in bt.AREAS]).encode()
            bt.download(date(2025, 7, 1), date(2025, 7, 1), root, fetch)
            rows, errors = bt.replay(root, daily_dates=['2025-07-02'])
            self.assertEqual(errors, [])
            self.assertEqual(len(rows), 2)
            for row in rows:
                self.assertEqual(row['run_at'], '2025-07-01T12:00:00Z')
                self.assertEqual(row['issued_at'], '2025-07-01T23:00:00Z')
                self.assertEqual(row['valid_until'], '2025-07-02T23:00:00Z')
                self.assertTrue(all(bt.parse_key(k) + bt.ISSUE_DELAY <= dt(row['issued_at']) for k in row['input_runs']))
                self.assertTrue(all(w['risk_tier'] == 'low' for w in row['windows']))
            cases = daily.score([daily_event(), daily_event(id='duplicate')], rows)
            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0]['outcome'], 'miss')
            rows[0]['windows'][0]['risk_tier'] = 'high'
            first_area = rows[0]['area_id']
            cases = daily.score([daily_event(area_id=first_area)], rows)
            self.assertEqual(cases[0]['outcome'], 'hit')
            rows[0]['available_at'] = '2025-07-02T00:00:00Z'
            self.assertEqual(daily.score([daily_event(area_id=first_area)], rows)[0]['outcome'], 'unknown')

    def test_uncertain_dates_conflicts_and_partial_non_flood_monitoring(self):
        with tempfile.TemporaryDirectory() as root:
            bt.download(date(2025, 7, 1), date(2025, 7, 1), root, dry)
            rows, _ = bt.replay(root, daily_dates=['2025-07-02'])
            e = daily_event()
            for reports in [[{**e, 'event_date': None}], [e, {**e, 'flooded': False}],
                            [{**e, 'end_at': '2025-07-03T23:00:00Z'}],
                            [{**e, 'flooded': False, 'end_at': '2025-07-02T00:00:00Z'}]]:
                self.assertEqual(daily.score(reports, rows)[0]['outcome'], 'unknown')
            negative = daily.score([{**e, 'flooded': False}], rows)[0]
            self.assertEqual(negative['outcome'], 'correct_negative')
            rows[0]['valid_until'] = '2025-07-02T22:00:00Z'
            self.assertEqual(daily.score([daily_event(area_id=rows[0]['area_id'])], rows)[0]['outcome'], 'unknown')
            self.assertEqual(daily.score([e], [])[0]['outcome'], 'unknown')

    def test_rates_require_independent_storms_and_negative_evidence(self):
        duplicate_storms = [{'storm_id': 'same', 'outcome': 'hit'}] * 8
        self.assertIsNone(daily.summarize(duplicate_storms)['detection_rate'])
        cases = [{'storm_id': str(i), 'outcome': 'hit'} for i in range(5)]
        self.assertEqual(daily.summarize(cases)['detection_rate'], 1)
        self.assertIsNone(daily.summarize(cases)['false_alarm_ratio'])
        cases.append({'storm_id': 'negative', 'outcome': 'false_alarm'})
        self.assertAlmostEqual(daily.summarize(cases)['false_alarm_ratio'], 1/6)

    def test_export_reproducibility_authenticated_api_and_stale_evidence(self):
        with tempfile.TemporaryDirectory() as root, patch.object(bt, 'BACKTEST', Path(root)), patch.dict(os.environ, {
            'PILOT_PASSWORD': 'test-password-long-enough', 'PILOT_INGEST': '0', 'FLOODGUARD_DB': str(Path(root)/'pilot.db')}):
            register = Path(root)/'events.json'
            bt.write_json(register, {'events': [daily_event()]})
            bt.download(date(2025, 7, 1), date(2025, 7, 1), root, dry)
            daily.run(root)
            output = Path(root)/'results/daily/report.json'
            original = output.read_bytes()
            bt.write_json(register, {'events': [{**daily_event(), 'event_date': 123}]})
            with self.assertRaisesRegex(ValueError, 'event_date'):
                daily.run(root)
            bt.write_json(register, {'events': [daily_event()]})
            daily.run(root)
            self.assertEqual(original, output.read_bytes())
            self.assertFalse(daily.read_report(root)['stale'])
            with TestClient(app) as client:
                self.assertEqual(client.get('/api/backtest').status_code, 401)
                auth = ('researcher', 'test-password-long-enough')
                response = client.get('/api/backtest', auth=auth)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['summary']['misses'], 1)
                self.assertEqual(client.post('/api/backtest', auth=auth, json={}, headers={'x-pilot-request':'1'}).status_code, 405)
                register.write_text(register.read_text() + '\n')
                self.assertTrue(client.get('/api/backtest', auth=auth).json()['stale'])


if __name__ == '__main__':
    unittest.main()
