"""Run: .venv/bin/python -m unittest backend.test_evidence -v"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from . import backtest as bt, evidence as ev
from .test_backtest import seeded


class EvidenceChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value))
        return path

    def source(self, body=b'<html><meta property="article:published_time" content="2025-07-02"><p>Lekki flooded</p></html>'):
        return ev.add_source('https://example.org/article', root=self.root,
                             fetcher=lambda _: (body, 'text/html', 'https://example.org/article'))

    def candidate(self):
        source = self.source()
        return {"id": "observation-1", "area_id": "lekki", "source_ids": [source['id']],
                "location": "Named street in Lekki", "location_precision": "street",
                "location_note": "Reporter located the street within the pilot area",
                "timing_note": "Witness explicitly gave the onset time",
                "description": "Witness reported rainfall flooding", "storm_id": "storm-1",
                "start_at": "2025-07-01T13:00:00+01:00", "end_at": "2025-07-01T13:00:00+01:00",
                "timing_precision": "hour", "observation_kind": "onset", "cause": "rainfall", "flooded": True}

    def imported(self):
        path = self.save('import.json', {"events": [self.candidate()]})
        ev.import_events(path, self.root)
        return path

    def approve(self, **extra):
        path = self.save('decision.json', {"status": "approved", "reviewer": "Test reviewer",
                         "review_note": "Checked local witness evidence independently", **extra})
        return ev.review_event('observation-1', path, self.root)

    def test_cache_versions_text_and_no_network_reuse(self):
        first = self.source()
        with patch.object(ev, 'urlopen', side_effect=AssertionError('offline')):
            self.assertEqual(ev.add_source(first['url'], root=self.root), first)
        second = ev.add_source(first['url'], refresh=True, root=self.root,
                               fetcher=lambda _: (b'Changed source', 'text/plain', first['url']))
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(len(ev.sources(self.root)), 2)
        self.assertEqual(first['metadata']['article:published_time'], '2025-07-02')
        self.assertIn('Lekki flooded', (self.root / first['text_file']).read_text())
        (self.root / first['cache_file']).write_bytes(b'altered')
        with self.assertRaisesRegex(ValueError, 'altered'):
            ev.verify_source(first, self.root)

    def test_discover_then_collect_and_record_failures(self):
        documents = {
            'https://example.org/sitemap.xml': b'<sitemapindex><sitemap><loc>https://example.org/archive.xml</loc></sitemap></sitemapindex>',
            'https://example.org/archive.xml': b'<urlset><url><loc>https://example.org/2024/lekki-flood</loc><lastmod>2026-01-01</lastmod></url><url><loc>https://example.org/sports</loc></url></urlset>'}
        fetcher = lambda u: (documents[u], 'application/xml', u)
        result = ev.discover('https://example.org/sitemap.xml', root=self.root, fetcher=fetcher)
        self.assertEqual(len(result['candidates']), 1)
        self.assertNotIn('start_at', result['candidates'][0])
        def failed(_):
            raise OSError('blocked')
        result = ev.collect([result['candidates'][0]['url']], self.root, failed)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(len(ev.sources(self.root)), 2)
        self.assertTrue((self.root / 'collection.json').exists())

    def test_review_idempotence_corrections_and_atomic_rejection(self):
        path = self.imported()
        approved = self.approve()
        self.assertEqual(approved['start_at'], '2025-07-01T12:00:00Z')
        self.assertEqual(ev.import_events(path, self.root)['imported'], 0)
        before = (self.root / 'events.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'correction_reason'):
            self.approve()
        self.assertEqual((self.root / 'events.json').read_bytes(), before)
        corrected = self.approve(correction_reason='Corrected street description', location='Corrected street, Lekki')
        self.assertEqual(len(corrected['review_history']), 2)
        self.assertEqual(corrected['review_history'][-1]['before']['location'], approved['location'])
        with self.assertRaises(ValueError):
            self.approve(correction_reason='Coarse evidence only', timing_precision='month')
        self.assertEqual(bt.read_json(self.root / 'events.json')['events'][0], corrected)

    def test_negative_requires_monitoring_and_coarse_location_cannot_be_approved(self):
        self.imported()
        with self.assertRaisesRegex(ValueError, 'monitored'):
            self.approve(flooded=False)
        with self.assertRaisesRegex(ValueError, 'pilot area'):
            self.approve(location_precision='lga')
        negative = self.approve(flooded=False, observation_kind='monitored_interval',
                               monitoring_method='Continuous camera observation of the stated street',
                               end_at='2025-07-01T18:00:00Z')
        self.assertFalse(negative['flooded'])
        seeded(self.root, [negative])
        forecasts, _ = bt.replay(self.root)
        by_area = {'lekki': [f for f in forecasts if f['area_id'] == 'lekki']}
        whole = bt.score_episode([negative], by_area)
        self.assertEqual(whole['leads'][0]['outcome'], 'false_alarm')
        partial = bt.score_episode([{**negative, 'end_at': '2025-07-01T13:00:00Z'}], by_area)
        self.assertEqual(partial['leads'][0]['outcome'], 'unknown')
        self.assertIn('Monitoring', partial['leads'][0]['reason'])

    def test_offline_replay_is_identical_and_checks_reviewed_sources(self):
        self.imported()
        self.approve()
        register = bt.read_json(self.root / 'events.json')
        seeded(self.root, register['events'])
        with patch.object(bt, 'urlopen', side_effect=AssertionError('network disabled')), \
                patch.object(ev, 'urlopen', side_effect=AssertionError('network disabled')):
            bt.run(self.root)
            first = {p.name: p.read_bytes() for p in (self.root / 'results').iterdir()}
            bt.run(self.root)
            second = {p.name: p.read_bytes() for p in (self.root / 'results').iterdir()}
        self.assertEqual(first, second)
        audit = json.loads(first['episodes.jsonl'].splitlines()[0])
        self.assertEqual(audit['report_ids'], ['observation-1'])
        self.assertTrue(audit['evidence_records'][0]['source_checksums'])
        record = next(iter(ev.sources(self.root).values()))
        (self.root / record['cache_file']).unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or altered'):
            bt.run(self.root)

    def test_rainfall_preserves_missing_and_rejects_invalid_values(self):
        source = self.source()
        path = self.root / 'rain.csv'
        header = 'start_at,end_at,latitude,longitude,station_or_grid,kind,product_version,rainfall_mm,quality\n'
        path.write_text(header + '2025-07-01T00:00:00Z,2025-07-01T00:30:00Z,6.45,3.47,grid-1,satellite,IMERG-v07,,missing\n')
        result = ev.import_rainfall(path, source['id'], self.root)
        ev.import_rainfall(path, source['id'], self.root)
        register = bt.read_json(self.root / 'rainfall-observations.json')
        self.assertEqual(len(register), 1)
        self.assertIsNone(register[result['sha256']]['observations'][0]['rainfall_mm'])
        path.write_text(header + '2025-07-01T00:00:00Z,2025-07-01T00:30:00Z,6.45,3.47,grid-1,satellite,IMERG-v07,nan,valid\n')
        with self.assertRaisesRegex(ValueError, 'Invalid rainfall'):
            ev.import_rainfall(path, source['id'], self.root)

    def test_local_observation_and_rainfall_diagnosis(self):
        photo = self.root / 'photo.txt'
        photo.write_text('Witness observation, retained locally')
        source = ev.add_source(None, file=photo, root=self.root)
        self.assertTrue(source['url'].startswith('local:'))
        candidate = self.candidate()
        candidate['source_ids'] = [source['id']]
        ev.import_events(self.save('local.json', {'events': [candidate]}), self.root)
        self.approve()
        _, events = bt.load_events(self.root)
        seeded(self.root, events)
        rain = self.root / 'gauge.csv'
        rain.write_text('start_at,end_at,latitude,longitude,station_or_grid,kind,product_version,rainfall_mm,quality\n'
                        '2025-07-01T12:00:00Z,2025-07-01T13:00:00Z,6.45,3.47,gauge-1,gauge,export-v1,15,valid\n')
        ev.import_rainfall(rain, source['id'], self.root)
        with patch('urllib.request.urlopen', side_effect=AssertionError('offline')):
            first = ev.check_rainfall(self.root)
            second = ev.check_rainfall(self.root)
        self.assertEqual(first, second)
        self.assertEqual(first['matched_pairs'], 2)
        lekki = first['cases'][0]
        self.assertEqual((lekki['forecast_mm'], lekki['error_mm']), (0, -15))
        self.assertEqual(lekki['run_at'], '2025-07-01T06:00:00Z')
        self.assertLessEqual(lekki['simulated_issue_at'], candidate['start_at'])
        rain.write_text(rain.read_text().replace(',15,valid', ',,valid'))
        with self.assertRaises(ValueError):
            ev.import_rainfall(rain, source['id'], self.root)


if __name__ == '__main__':
    unittest.main()
