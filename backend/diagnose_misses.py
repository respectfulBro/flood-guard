"""Reproduce the four historical daily misses: python -m backend.diagnose_misses.

Read-only with respect to forecasts, thresholds and event labels. Writes diagnostic artifacts.
"""
import csv
import json
from pathlib import Path

from . import backtest as bt, daily_backtest as daily
from .core import AREAS, THRESHOLDS, LIVE_VERSION, dt, rescreen
from .rainfall_audit import distance_km, precipitation


def run():
    report = daily.read_report()
    if not report.get('available') or report['stale']:
        raise ValueError('Generate a current daily report before diagnosing it')
    missed = [c for c in report['cases'] if c['outcome'] == 'miss']
    forecasts, _ = bt.replay(daily_dates=[c['event_date'] for c in missed])
    index = {(f['area_id'], f['issued_at']): f for f in forecasts}
    audit = bt.read_json(bt.BACKTEST / 'rainfall-audit.json')
    station_rows = {}
    for source in audit['sources']:
        path = bt.BACKTEST / source['cache_file']
        assert bt.sha256_file(path) == source['sha256'], 'Station source checksum mismatch'
        with path.open() as handle:
            for row in csv.DictReader(handle):
                station_rows[row['DATE']] = row
    cases = []
    for c in missed:
        f = c['forecast']
        assert index[(c['area_id'], f['issued_at'])] == f, 'Daily forecast did not reproduce'
        peaks = {str(h): max(w['peaks_mm'][str(h)] for w in f['windows']) for h in THRESHOLDS}
        assert all(peaks[str(h)] < threshold[0] for h, threshold in THRESHOLDS.items())
        sensitive = rescreen(f, LIVE_VERSION)
        alert_windows = [w for w in sensitive['windows'] if w['risk_tier'] != 'low']
        station = precipitation(station_rows.get(c['event_date'], {}))
        area = next(a for a in AREAS if a['id'] == c['area_id'])
        if c['event_date'] == '2024-07-03':
            finding = ('The archive represents a much weaker rain event at the pilot grid than the substantial rainfall '
                       'reported at Ikeja. Spatial/temporal rainfall mismatch is a plausible contributor; this is not '
                       'a matched-location forecast-error measurement and does not establish the correct threshold.')
        elif c['event_date'] == '2025-08-04':
            finding = ('The archive predicts modest rain; Ikeja reports a larger amount from one 12-hour report. '
                       'Different locations and accumulation periods prevent attribution between rainfall error and '
                       'threshold sensitivity. Sensitive-v2 first alerts in the last six-hour window, so the daily '
                       'hit does not establish warning before the reported daytime flooding.')
        else:
            finding = ('The archive predicts appreciable rain but every original threshold remains unmet. '
                       'No station observation is available for this date. Threshold sensitivity demonstrably '
                       'changes the classification; whether the rain forecast was accurate remains unresolved.')
        cases.append({'area_id': c['area_id'], 'date': c['event_date'], 'storm_id': c['storm_id'],
                      'forecast_run_at': f['run_at'], 'daily_decision_at': f['issued_at'],
                      'forecast_total_local_day_mm': round(sum(w['rainfall_mm'] for w in f['windows']), 2),
                      'peak_accumulations_mm': peaks,
                      'shortfall_to_moderate_mm': {str(h): round(v[0]-peaks[str(h)], 2) for h,v in THRESHOLDS.items()},
                      'forecast_grid': f['grid'],
                      'grid_distance_from_pilot_point_km': distance_km(*f['grid'], area),
                      'station_observation': station,
                      'station_distance_from_pilot_point_km': distance_km(audit['station']['lat'], audit['station']['lng'], area),
                      'first_sensitive_alert_window': alert_windows[0] if alert_windows else None,
                      'finding': finding, 'source_urls': c['source_urls'], 'forecast_input_hashes': f['input_runs']})
    result = {'cases': cases, 'thresholds_mm': THRESHOLDS,
              'independent_storms': len({c['storm_id'] for c in cases}),
              'station_sources': audit['sources'], 'station_documentation': audit['documentation'],
              'input_hashes': daily.input_hashes(),
              'limitations': ['Day-level flood presence, not verified onset or street-level rainfall.',
                             'Trailing 24-hour peaks can include modelled antecedent rainfall; they are not daily totals.',
                             'Cycle 49R1 archive is provider-labelled hindcast, not proof of contemporaneous operational forecasts.',
                             'Sensitive-v2 was developed on these examples; no independent accuracy claim or false-alarm estimate.']}
    bt.write_json(bt.BACKTEST / 'diagnosis.json', result)
    lines = ['# Why the four daily flood observations were missed', '',
             'The original screen stayed below all four moderate-alert thresholds in every case. '
             'The calculations reproduce from the checksum-verified forecast cache. Four area-days represent three storms.', '',
             'Moderate thresholds: 10 mm / 1 hour, 20 mm / 3 hours, 30 mm / 6 hours, and 50 mm / 24 hours. '
             'The screen uses maximum trailing accumulations, not just the local-day total.', '']
    for c in cases:
        s = c['station_observation']
        lines += [f"## {c['date']} — {c['area_id']}", '',
                  f"- Forecast local-day total: **{c['forecast_total_local_day_mm']:g} mm**.",
                  '- Peak forecast accumulations: ' + ', '.join(f"{h}h: {v:g} mm" for h,v in c['peak_accumulations_mm'].items()) + '.',
                  '- Shortfalls below moderate thresholds: ' + ', '.join(f"{h}h: {v:g} mm" for h,v in c['shortfall_to_moderate_mm'].items()) + '.',
                  f"- Archive run: {c['forecast_run_at']}; daily decision: {c['daily_decision_at']} (midnight Lagos).",
                  f"- Returned forecast grid is {c['grid_distance_from_pilot_point_km']} km from the configured pilot point.",
                  f"- Ikeja station: {str(s['reported_mm']) + ' mm' if s['reported_mm'] is not None else 'no usable record'}; {s['quality']}; flag {s['flag'] or 'missing'}. "
                  f"Station is {c['station_distance_from_pilot_point_km']} km from the pilot point."]
        w = c['first_sensitive_alert_window']
        if w:
            lines += [f"- First sensitive-rule alert window: {w['start_at']} to {w['end_at']} (UTC). "
                      'Add one hour for Lagos local time; this is the forecast window, not a proven warning lead.']
        lines += ['', c['finding'], '', 'Evidence: ' + ', '.join(f'[source {i+1}]({u})' for i,u in enumerate(c['source_urls'])), '']
    lines += ['## Interpretation and next action', '',
              'July has the strongest regional rainfall discrepancy. August remains ambiguous, and its sensitive-rule '
              'daily hit occurs in the evening window. September has insufficient independent rainfall data to separate '
              'forecast error from threshold choice. Lowering thresholds changes all four labels but does not establish skill.', '',
              'Next, obtain rainfall observations aligned to the pilot locations and accumulation periods for these '
              'three storms (local gauge data or quality-controlled satellite estimates). Freeze sensitive-v2, collect '
              'new storms alongside explicitly monitored non-flood periods, and evaluate both detection and false alarms '
              'before further tuning. No model training or threshold change is justified by this diagnosis alone.', '',
              'The NOAA 2025 export was re-fetched on 2026-09-30 and matched the existing cached SHA-256 exactly; '
              'it still ends on August 24, so September is unavailable from this export, not a verified dry day.', '',
              'NOAA flag F means two 12-hour amounts; E means one 12-hour amount. Their reporting periods need not '
              'match midnight-to-midnight Lagos. No numerical pilot rainfall error is claimed.', '',
              '[NOAA definitions](' + audit['documentation'] + ')', '',
              *['- '+x for x in result['limitations']], '',
              'Reproduce offline: `.venv/bin/python -m backend.diagnose_misses`. '
              'Detailed values and provenance: [diagnosis.json](diagnosis.json).', '']
    (bt.BACKTEST / 'diagnosis.md').write_text('\n'.join(lines))
    return result


if __name__ == '__main__':
    result = run()
    print(json.dumps({'cases': len(result['cases']), 'storms': result['independent_storms'],
                      'report': str(bt.BACKTEST / 'diagnosis.md')}, indent=2))
