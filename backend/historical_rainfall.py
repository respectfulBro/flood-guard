"""Pre-2024 rainfall diagnostic, explicitly NOT an archived forecast backtest.

python -m backend.historical_rainfall download  # one-time network collection
python -m backend.historical_rainfall run       # deterministic offline analysis
"""
import argparse
import csv
import io
import json
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode

from . import backtest as bt, evidence as ev
from .core import AREAS, HOUR, VERSION, LIVE_VERSION, dt, predict, thresholds_for
from .daily_backtest import day_bounds
from .rainfall_audit import STATION, distance_km, precipitation

ROOT = bt.BACKTEST / 'historical'
DOC = 'https://open-meteo.com/en/docs/historical-weather-api'


def review(root):
    data = bt.read_json(root / 'review.json')
    seen, storms = set(), set()
    for event in data['events']:
        if event['id'] in seen:
            raise ValueError('Duplicate event ID')
        seen.add(event['id'])
        if event['status'] not in ('accepted_day', 'pending', 'context', 'rejected'):
            raise ValueError('Unknown review decision')
        if event['status'] != 'accepted_day':
            continue
        day = date.fromisoformat(event['event_date'])
        if not date(2015, 1, 1) <= day <= date(2023, 12, 31):
            raise ValueError('Diagnostic only covers 2015-2023')
        if (event['area_id'] not in {a['id'] for a in AREAS} or event['cause'] != 'rainfall'
                or event['timing_precision'] != 'day' or event['location_precision'] != 'named_area'
                or not event['source_urls'] or not event['reviewer'] or not event['review_note'] or not event['storm_id']):
            raise ValueError('Accepted day lacks required evidence')
        key = (event['area_id'], event['storm_id'])
        if key in storms:
            raise ValueError('Duplicate area/storm; resolve review before scoring')
        storms.add(key)
    return data


def rain_url(day):
    return 'https://archive-api.open-meteo.com/v1/archive?' + urlencode({
        'latitude': ','.join(str(a['lat']) for a in AREAS),
        'longitude': ','.join(str(a['lng']) for a in AREAS),
        'start_date': str(date.fromisoformat(day) - timedelta(days=2)), 'end_date': day,
        'hourly': 'precipitation', 'models': 'era5', 'timezone': 'UTC', 'cell_selection': 'nearest'})


def station_url(year):
    return f'https://www.ncei.noaa.gov/data/global-summary-of-the-day/access/{year}/{STATION}.csv'


def download(root=ROOT):
    data = review(root)
    accepted = [e for e in data['events'] if e['status'] == 'accepted_day']
    urls = {u for e in data['events'] for u in e['source_urls']}
    urls.update(rain_url(e['event_date']) for e in accepted)
    urls.update(station_url(e['event_date'][:4]) for e in accepted)
    result = ev.collect(urls, root=root)
    # Print failures without dumping downloaded article content.
    return {'failed': result['failed'], 'sources': len(result['results']),
            'failures': [r for r in result['results'] if r['status'] == 'unavailable']}


def cached(address, root, index):
    rows = [s for s in index.values() if s['url'] == address]
    if not rows:
        raise ValueError(f'Source not cached: {address}')
    if len(rows) != 1:
        raise ValueError('Multiple source versions: pin the intended version before analysis')
    source = rows[0]
    return ev.verify_source(source, root).read_bytes(), source


def classify(payload, day):
    if payload.get('utc_offset_seconds') != 0 or payload.get('hourly_units', {}).get('precipitation') != 'mm':
        raise ValueError('ERA5 must be UTC hourly precipitation in mm')
    times, values = payload['hourly']['time'], payload['hourly']['precipitation']
    if len(times) != len(values) or not times:
        raise ValueError('Malformed hourly series')
    stamps = [dt(t if t.endswith('Z') else t + 'Z') for t in times]
    if any(b-a != HOUR for a,b in zip(stamps, stamps[1:])):
        raise ValueError('Missing or duplicated hourly timestamps')
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Missing or invalid rainfall; cannot assume zero')
    start, end = day_bounds(day)
    output = {}
    for version in (VERSION, LIVE_VERSION):
        screen = predict(payload, start, version)
        output[version] = {'outcome': 'threshold_triggered' if any(w['risk_tier'] != 'low' for w in screen['windows'])
                          else 'threshold_not_triggered', 'windows': screen['windows']}
    windows = output[VERSION]['windows']
    return {'day_start_utc': start.isoformat(), 'day_end_utc': end.isoformat(),
            'local_day_rainfall_mm': round(sum(w['rainfall_mm'] for w in windows),2),
            'peaks_mm': {str(n):max(w['peaks_mm'][str(n)] for w in windows) for n in (1,3,6,24)},
            'versions': output}


def run(root=ROOT):
    data, index = review(root), ev.sources(root)
    cases, used = [], {}
    for event in data['events']:
        if event['status'] != 'accepted_day':
            continue
        area_index = next(i for i,a in enumerate(AREAS) if a['id'] == event['area_id'])
        area = AREAS[area_index]
        case = {'event': event, 'era5': None, 'station': None, 'errors': []}
        evidence_count = 0
        for address in event['source_urls']:
            try:
                raw, source = cached(address, root, index)
                used[source['id']] = source
                evidence_count += 1
            except (ValueError,OSError) as exc:
                case['errors'].append(str(exc))
        if evidence_count != len(event['source_urls']):
            case['errors'].append('Incomplete cached evidence: excluded from threshold evaluation')
            cases.append(case)
            continue
        try:
            raw, source = cached(rain_url(event['event_date']),root,index)
            used[source['id']] = source
            payloads = json.loads(raw)
            if not isinstance(payloads,list) or len(payloads) != len(AREAS):
                raise ValueError('Expected two ERA5 area payloads')
            payload = payloads[area_index]
            lat, lng = float(payload['latitude']), float(payload['longitude'])
            if not math.isfinite(lat) or not math.isfinite(lng) or abs(lat-area['lat']) > .26 or abs(lng-area['lng']) > .26:
                raise ValueError('ERA5 grid is outside the requested region')
            case['era5'] = {**classify(payload,event['event_date']), 'source_id': source['id'],
                            'grid': [lat,lng], 'distance_from_pilot_km': distance_km(lat,lng,area)}
        except (ValueError,OSError,KeyError,TypeError) as exc:
            case['errors'].append(str(exc))
        try:
            raw, source = cached(station_url(event['event_date'][:4]),root,index)
            used[source['id']] = source
            rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
            if not rows or any(r.get('STATION') != STATION for r in rows):
                raise ValueError('Wrong or malformed station export')
            matching = [r for r in rows if r['DATE'] == event['event_date']]
            if len(matching) > 1:
                raise ValueError('Duplicate station date')
            obs = precipitation(matching[0] if matching else {})
            case['station'] = {**obs, 'source_id':source['id'], 'station_id':STATION,
                               'distance_from_pilot_km': distance_km(float(rows[0]['LATITUDE']),float(rows[0]['LONGITUDE']),area),
                               'comparison':'24-hour threshold only; different location and reporting period',
                               'versions':{v:('threshold_triggered' if obs['reported_mm'] >= thresholds_for(v)[24][0]
                                              else 'threshold_not_triggered') if obs['quality'] == '24h_report' else 'unknown'
                                           for v in (VERSION,LIVE_VERSION)}}
        except (ValueError,OSError,KeyError,TypeError) as exc:
            case['errors'].append(str(exc))
        cases.append(case)
    counts = {v:dict(Counter(c['era5']['versions'][v]['outcome'] if c['era5'] else 'unknown' for c in cases))
              for v in (VERSION,LIVE_VERSION)}
    result = {'kind':'retrospective_rainfall_diagnostic_not_forecast_validation', 'search_period':data['search_period'],
              'accepted_area_days':len(cases),'independent_storms':len({c['event']['storm_id'] for c in cases}),
              'unscored_decisions':dict(Counter(e['status'] for e in data['events'] if e['status'] != 'accepted_day')),
              'thresholds':{v:thresholds_for(v) for v in (VERSION,LIVE_VERSION)}, 'era5_counts':counts,
              'accuracy':None,'false_alarm_ratio':None,'lead_time':None,
              'cases':cases,'sources':used,'review_sha256':bt.sha256_file(root/'review.json'),
              'code_sha256':{p.name:bt.sha256_file(p) for p in (Path(__file__),Path(bt.__file__).with_name('core.py'),
                                      Path(bt.__file__).with_name('rainfall_audit.py'))},
              'limitations':['Public-news review by an assistant, not independent field verification or an exhaustive flood census.',
                  'ERA5 is revised coarse-grid reanalysis, not measured street rainfall or a forecast available before the event.',
                  'Both pilot points can share a grid cell. Do not count them as independent rainfall measurements.',
                  'A day-level threshold coincidence is not proven advance warning. Floodwater may persist from previous days.',
                  'No verified negative sample: no false-alarm ratio, accuracy, or operational detection claim.',
                  'Station daily totals cannot test 1/3/6-hour rules; partial/missing reports remain unknown.']}
    bt.write_json(root/'results'/'report.json',result)
    lines=['# Older flood rainfall diagnostic (2015–2023 search)', '',
           'This is a retrospective rainfall diagnostic, not a forecast backtest. Thresholds are unchanged.', '',
           f"Accepted {len(cases)} area-days across {result['independent_storms']} storms. "
           f"Other candidate decisions: {result['unscored_decisions']}. Search gaps are not dry days.", '',
           f"Original rules: {counts[VERSION]}. Sensitive rules: {counts[LIVE_VERSION]}.", '']
    for c in cases:
        e,r,s=c['event'],c['era5'],c['station']
        lines += [f"## {e['event_date']} — {e['area_id']}", '', e['review_note'], '']
        if r:
            lines += [f"ERA5 local-day rainfall: **{r['local_day_rainfall_mm']:g} mm**. "
                      f"Peaks: {r['peaks_mm']} (keys are accumulation hours; values mm).",
                      f"Original: **{r['versions'][VERSION]['outcome']}**; sensitive: **{r['versions'][LIVE_VERSION]['outcome']}**.",
                      f"Grid: {r['grid']}; distance from pilot point: {r['distance_from_pilot_km']} km.", '']
        if s:
            lines += [f"Ikeja station reported amount: {str(s['reported_mm']) + ' mm' if s['reported_mm'] is not None else 'unavailable'}; {s['quality']}; flag {s['flag'] or 'missing'}. "
                      f"24-hour-only comparison: {s['versions']}. Station distance: {s['distance_from_pilot_km']} km.", '']
        lines += ['Evidence: '+', '.join(f'[source {i+1}]({u})' for i,u in enumerate(e['source_urls'])), '']
        lines += ['Collection/validation gap: '+x for x in c['errors']]
    disagreements = [c for c in cases if c['era5'] and c['station']
                     and c['era5']['versions'][VERSION]['outcome'] == 'threshold_not_triggered'
                     and c['station']['versions'][VERSION] == 'threshold_triggered']
    lines += ['## What this changes', '',
              f"On {len(disagreements)} accepted days, the original rules stay low on ERA5 while the nearby station's "
              'reported 24-hour amount crosses the original 50 mm threshold. Different measurement locations and '
              'reporting periods prevent calling these exact ERA5 errors. They do show that rainfall source choice '
              'can change the conclusion about threshold adequacy.', '',
              'Do not tune on this selected positive sample. Obtain rainfall aligned to pilot locations and periods, '
              'and monitored non-flood intervals, before estimating operational performance. The search included '
              '2015–2023, but this first pass found scoreable days only in 2017, 2020, 2021, 2022 and 2023. '
              'Other years remain unresolved, not flood-free.', '']
    lines += ['## Limits and reproducibility','',*['- '+x for x in result['limitations']], '',
              '[ERA5 provider documentation]('+DOC+'). [Review register](review.json).', '',
              'Offline rerun: `.venv/bin/python -m backend.historical_rainfall run`. '
              'One-time imports/retries: `.venv/bin/python -m backend.historical_rainfall download`.', '']
    (root/'report.md').write_text('\n'.join(lines))
    return {'cases':len(cases),'era5_counts':counts,'report':str(root/'report.md')}


def read_report(root=ROOT):
    try:
        report = bt.read_json(root / 'results/report.json')
    except (OSError, ValueError):
        return {'available': False, 'message': 'Run python -m backend.historical_rainfall run to build the cached diagnostic.'}
    try:
        stale = report['review_sha256'] != bt.sha256_file(root / 'review.json')
        stale |= any(bt.sha256_file(Path(__file__).with_name(name)) != digest
                     for name, digest in report['code_sha256'].items())
        for source in report['sources'].values():
            ev.verify_source(source, root)
    except (OSError, ValueError, KeyError):
        stale = True
    return {**report, 'available': True, 'stale': stale}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['download','run'])
    args=parser.parse_args()
    result=download() if args.command=='download' else run()
    print(json.dumps(result,indent=2))
    raise SystemExit(1 if result.get('failed') else 0)
