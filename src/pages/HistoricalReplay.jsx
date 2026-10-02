import { useState } from 'react';
import { Link } from 'react-router-dom';
import { usePilot, lagosTime } from '@/api/pilot';
import DataState from '@/components/DataState';

const original = 'rainfall-screen-v1';
const sensitive = 'rainfall-screen-sensitive-v2';
const outcome = { hit: 'Day flagged', miss: 'Day not flagged', unknown: 'Unknown', threshold_triggered: 'Day flagged', threshold_not_triggered: 'Day not flagged' };

export default function HistoricalReplay({ embedded = false }) {
  const [dataset, setDataset] = useState('forecast');
  const [version, setVersion] = useState(sensitive);
  const [selected, setSelected] = useState('');
  const query = usePilot(dataset === 'forecast' ? '/backtest' : '/historical-rainfall');
  const data = query.data;
  const older = dataset === 'rainfall';
  const comparisons = older ? [] : data?.sensitivity?.comparisons || [];
  const comparison = comparisons.find((c) => c.version === version);
  const cases = older ? data?.cases || [] : comparison?.cases || [];
  const key = (c) => older ? c.event.id : `${c.storm_id}-${c.area_id}`;
  const item = cases.find((c) => key(c) === selected) || cases[0];
  const event = older ? item?.event : item;
  const screen = older ? item?.era5?.versions[version] : item?.forecast;
  const thresholds = older ? data?.thresholds?.[version] : comparison?.thresholds_mm;
  const counts = older ? data?.era5_counts?.[version] : null;
  const flagged = older ? counts?.threshold_triggered || 0 : comparison?.summary.hits;
  const missed = older ? counts?.threshold_not_triggered || 0 : comparison?.summary.misses;
  const unknown = older ? counts?.unknown || 0 : comparison?.summary.unknowns;
  return <section className={embedded ? 'mt-8 border rounded-xl p-5' : 'max-w-6xl mx-auto px-5 py-10'}>
    {embedded ? <h2 className="text-2xl font-semibold">Explore the historical analysis</h2> : <h1 className="text-3xl font-semibold">Replay a historical storm</h1>}
    <p className="mt-3 p-4 rounded-lg bg-amber-50 text-amber-950 border border-amber-200">Historical experiment · not current conditions. Day-level threshold crossings do not establish advance flood warning. Evidence is assistant-reviewed public reporting, not independent field verification.</p>
    <div className="grid sm:grid-cols-2 gap-4 mt-5">
      <label className="text-sm font-medium">Analysis<select className="block w-full mt-2 border rounded-lg p-3 bg-white" value={dataset} onChange={(e) => { setDataset(e.target.value); setSelected(''); }}>
        <option value="forecast">2024–2025 · archived model runs</option><option value="rainfall">2015–2023 search · ERA5 rainfall diagnostic</option>
      </select></label>
      <label className="text-sm font-medium">Rainfall rules<select className="block w-full mt-2 border rounded-lg p-3 bg-white" value={version} onChange={(e) => setVersion(e.target.value)}>
        <option value={sensitive}>Sensitive v2 · development-tuned</option><option value={original}>Original v1 · unchanged baseline</option>
      </select></label>
    </div>
    <DataState query={query} />
    {data && !data.available && !query.isError && <p className="mt-4">{data.message}</p>}
    {data?.available && !query.isError && <>
      {data.stale && <p role="alert" className="bg-red-50 text-red-900 p-4 mt-4">Saved results are stale or their source cache cannot be verified. Regenerate this analysis before presenting its counts.</p>}
      <div className="grid sm:grid-cols-3 gap-3 mt-5">{[[flagged, 'Flood days flagged'], [missed, 'Flood days not flagged'], [unknown, 'Unknown / excluded']].map(([value, label]) => <div key={label} className="border rounded-xl p-4"><p className="text-3xl font-semibold">{value ?? 'Unavailable'}</p><p className="text-sm text-slate-600 mt-1">{label}</p></div>)}</div>
      <p className="text-sm mt-3">{older ? data.independent_storms : comparison?.summary.independent_storms} independent storms. Selected positive examples: results are inconclusive for operational accuracy. False alarms and flood-onset lead times are not established.</p>
      <details className="mt-5 border rounded-xl p-4">
        <summary className="font-semibold cursor-pointer">Backtest strategy and limits</summary>
        <p className="mt-3 text-sm">{older ? 'ERA5 revised hourly rainfall is replayed through the same rules over midnight-to-midnight Lagos days. This is a retrospective rainfall diagnostic, not an archived forecast or a lead-time test. The search spans 2015–2023; only accepted, located, day-dated reports are scored. Other dates remain unknown.' : data.protocol}</p>
        {!older && <p className="mt-2 text-sm">Model availability is simulated as initialization plus six hours; the daily decision uses the latest eligible run at midnight Lagos. The provider’s early archive is a model hindcast, not proof of what users saw. The 2025 examples were examined during v2 development, so they are no longer an untouched test for v2. Keep 2026 and its model-cycle change separate. Hourly 6/12/18/24-hour scoring needs better flood-onset evidence.</p>}
        <p className="mt-2 text-sm">Unlabeled dates are not correct negatives. A no-alert baseline leaves all scoreable flood days unflagged; an always-alert baseline flags every day. Neither establishes useful forecasting. Reserve new storms and independently monitored non-flood intervals before further tuning.</p>
        <p className="mt-2 text-sm">Moderate / high thresholds: {Object.entries(thresholds || {}).map(([h, limits]) => `${h}h: ${limits[0]} / ${limits[1]} mm`).join(' · ')}. Any qualifying rolling accumulation triggers its tier; high thresholds are unchanged.</p>
        {older && data.limitations.map((text) => <p className="mt-2 text-sm text-slate-600" key={text}>{text}</p>)}
        {!older && comparison?.background && <p className="mt-2 text-sm">August 2025 background: {comparison.background.alert_area_days} alerts / {comparison.background.covered_area_days} covered area-days; {comparison.background.missing_area_days} missing. {comparison.background.alerts_without_reviewed_outcome} alerts have unknown outcomes, not confirmed false alarms.</p>}
      </details>
      {event && <>
        <label className="block mt-6 text-sm font-medium">Documented event<select value={key(item)} onChange={(e) => setSelected(e.target.value)} className="block w-full mt-2 border rounded-lg p-3 bg-white">{cases.map((c) => { const e = older ? c.event : c; return <option key={key(c)} value={key(c)}>{e.event_date} · {e.area_id === 'lekki' ? 'Lekki' : 'Ikosi-Ketu'}</option>; })}</select></label>
        <article className="mt-5 border rounded-xl p-5">
          <h3 className="text-xl font-semibold">{event.event_date} · {event.location}</h3>
          <p className="mt-2 font-medium">{outcome[older ? screen?.outcome : item.outcome] || 'Unknown'} · {version}</p>
          <p className="mt-2 text-sm">Timing precision: day. A flagged window may occur after the flood began.</p>
          {!older && screen && <p className="mt-3 text-sm">Model initialized: {lagosTime(screen.run_at)} · assumed available: {lagosTime(screen.available_at)} · daily decision: {lagosTime(screen.issued_at)} · cycle {screen.cycle}</p>}
          {older && item.era5 && <p className="mt-3 text-sm">ERA5 local-day rainfall: {item.era5.local_day_rainfall_mm} mm · grid {item.era5.grid.join(', ')} · {item.era5.distance_from_pilot_km} km from pilot point.</p>}
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-4">{screen?.windows.map((w) => <div key={w.start_at} className={`rounded-lg p-4 ${w.risk_tier === 'high' ? 'bg-red-50' : w.risk_tier === 'moderate' ? 'bg-amber-50' : 'bg-slate-50'}`}>
            <p className="text-xs">{lagosTime(w.start_at)}<br />to {lagosTime(w.end_at)}</p><p className="font-semibold capitalize mt-2">{w.risk_tier} rainfall screen</p><p className="text-sm mt-2">{w.rainfall_mm} mm over six hours</p>
            <p className="text-xs mt-2">Peak rolling totals: {Object.entries(w.peaks_mm).map(([h, mm]) => `${h}h ${mm} mm`).join(' · ')}</p>
            <p className="text-xs mt-2">{w.factors.join('; ')}</p>
          </div>)}</div>
          <h4 className="font-semibold mt-5">Evidence and review</h4><p className="text-sm mt-2">{event.review_note}</p><p className="text-xs text-slate-500 mt-2">Reviewer: {event.reviewer} · Storm: {event.storm_id}</p>
          <div className="flex flex-wrap gap-4 mt-3">{event.source_urls?.map((url, i) => <a className="text-sm underline text-teal-800" href={url} key={url} target="_blank" rel="noopener noreferrer">Source {i + 1}</a>)}</div>
          {older && item.station && <p className="text-sm mt-4">Nearby Ikeja station: {item.station.reported_mm == null ? 'unavailable' : `${item.station.reported_mm} mm`} · {item.station.quality} · {item.station.distance_from_pilot_km} km away. {item.station.comparison}.</p>}
          {item.errors?.map((error) => <p role="alert" key={error} className="text-sm text-red-800 mt-2">{error}</p>)}
          <Link className="inline-block mt-5 underline text-teal-800" to={`/report?area=${event.area_id}`}>Record an observation for this area</Link>
        </article>
      </>}
      <a className="inline-block text-sm underline mt-5" href={older ? '/api/historical-rainfall' : '/api/backtest'} download>Download audit results (JSON)</a>
    </>}
  </section>;
}
