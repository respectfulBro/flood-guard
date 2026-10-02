import json
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from . import historical_rainfall as hr, evidence as ev, backtest as bt
from .core import dt, VERSION, LIVE_VERSION


def payload(spike=0):
    start = dt('2017-07-06T00:00:00Z')
    times = [(start + timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(72)]
    values = [0.0]*72
    values[48] = spike  # hour ending July 8 00 UTC, within the July 8 Lagos day
    return {'latitude':6.5,'longitude':3.5,'utc_offset_seconds':0,
            'hourly_units':{'precipitation':'mm'},'hourly':{'time':times,'precipitation':values}}


class HistoricalChecks(unittest.TestCase):
    def test_fixed_rules_and_local_midnight(self):
        for spike, expected in [(0, ('threshold_not_triggered','threshold_not_triggered')),
                                (2.5, ('threshold_not_triggered','threshold_triggered')),
                                (10, ('threshold_triggered','threshold_triggered'))]:
            r=hr.classify(payload(spike),'2017-07-08')
            self.assertEqual(tuple(r['versions'][v]['outcome'] for v in (VERSION,LIVE_VERSION)),expected)
            self.assertEqual(r['local_day_rainfall_mm'],spike)
            self.assertTrue(r['day_start_utc'].startswith('2017-07-07T23:00'))
        p=payload();p['hourly']['precipitation'][46]=50
        r=hr.classify(p,'2017-07-08')
        self.assertEqual(r['local_day_rainfall_mm'],0)
        self.assertEqual(r['versions'][VERSION]['outcome'],'threshold_triggered')

    def test_missing_rain_and_wrong_units_fail(self):
        for change in ('missing','units','gap'):
            p=payload()
            if change=='missing':p['hourly']['precipitation'][48]=None
            elif change=='units':p['hourly_units']['precipitation']='inch'
            else:p['hourly']['time'][48]=p['hourly']['time'][47]
            with self.assertRaises(ValueError):hr.classify(p,'2017-07-08')

    def test_offline_provenance_unknowns_and_repeatability(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            self.assertFalse(hr.read_report(root)["available"])
            event={'id':'case','event_date':'2017-07-08','area_id':'lekki','status':'accepted_day',
                   'cause':'rainfall','timing_precision':'day','location_precision':'named_area',
                   'source_urls':['https://example.org/news'],'reviewer':'test','review_note':'Synthetic test only',
                   'storm_id':'storm'}
            bt.write_json(root/'review.json',{'search_period':['2015-01-01','2023-12-31'],'events':[event]})
            bodies={'https://example.org/news':b'Test-only evidence',
                    hr.rain_url('2017-07-08'):json.dumps([payload(2.5),payload(2.5)]).encode(),
                    hr.station_url('2017'):b'STATION,DATE,PRCP,PRCP_ATTRIBUTES,LATITUDE,LONGITUDE\n65201099999,2017-07-08,2.00,E,6.577369,3.321156\n'}
            for url, raw in bodies.items():
                ev.add_source(url,root=root,fetcher=lambda u:(bodies[u],'application/octet-stream',u))
            with patch.object(ev,'urlopen',side_effect=AssertionError('offline')):
                hr.run(root)
                first=(root/'results/report.json').read_bytes()
                hr.run(root)
                self.assertEqual(first,(root/'results/report.json').read_bytes())
            self.assertFalse(hr.read_report(root)['stale'])
            report=json.loads(first)
            self.assertIsNone(report['accuracy'])
            self.assertEqual(report['cases'][0]['station']['versions'][VERSION],'unknown')
            source=next(s for s in ev.sources(root).values() if s['url']==hr.rain_url('2017-07-08'))
            (root/source['cache_file']).write_bytes(b'corrupted')
            self.assertTrue(hr.read_report(root)['stale'])
            hr.run(root)
            report=bt.read_json(root/'results/report.json')
            self.assertEqual(report['era5_counts'][VERSION],{'unknown':1})
            self.assertTrue(report['cases'][0]['errors'])


if __name__=='__main__':unittest.main()
