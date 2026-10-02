import HistoricalReplay from '@/pages/HistoricalReplay';
import { useState } from 'react';
import { usePilot, lagosTime } from '@/api/pilot';
import DataState from '@/components/DataState';

const percent = (value) => value == null ? 'Not yet available' : `${Math.round(value * 100)}%`;

export default function Performance() {
  const query = usePilot('/evaluation');
  const data = query.data;
  return <div className="max-w-6xl mx-auto px-5 py-10">
    <h1 className="text-3xl font-semibold">Research performance</h1>
    <p className="text-slate-600 mt-3 max-w-3xl">These results compare archived rainfall screening with reviewed flood and non-flood observations. Unknown outcomes stay unknown. This is not a validated flood warning service.</p>
    <HistoricalReplay embedded />
    <details className="mt-6 border rounded-xl p-5"><summary className="cursor-pointer font-semibold">Full 2024–2025 audit and candidate review</summary><HistoricalResults /></details>
    <h2 className="text-xl font-semibold mt-12">Live archive · hourly evaluation</h2>
    <DataState query={query} />
    {data && !query.isError && <>
      <p className="mt-6 text-sm text-slate-500">{data.version} · {data.archived_forecasts} archived forecasts · {data.approved_reports} reviewed observations · {data.pending_reports} awaiting review</p>
      <div className="grid sm:grid-cols-3 gap-4 mt-6">
        <Stat label="Flood detection at 6h lead" value={percent(data.summary.detection_rate)} interval={data.summary.detection_interval} />
        <Stat label="False alarms at 6h lead" value={percent(data.summary.false_alarm_ratio)} interval={data.summary.false_alarm_interval} />
        <Stat label="Mean lead time for matched events" value={data.summary.mean_lead_hours == null ? 'Not yet available' : `${data.summary.mean_lead_hours}h`} />
      </div>
      <h2 className="text-lg font-semibold mt-10 mb-4">By forecast lead time</h2>
      <div className="grid sm:grid-cols-3 gap-4">{data.by_lead.map((s) => <article key={s.lead_hours} className="border rounded-xl p-5">
        <h3 className="font-semibold">{s.lead_hours} hours ahead</h3>
        <p className="text-sm mt-3">{s.hits} days flagged · {s.misses} missed</p>
        <p className="text-sm mt-2">{s.false_alarms} false alarms · {s.correct_negatives} correct non-events</p>
        <p className="text-sm text-slate-500 mt-2">{s.excluded} excluded for timing or coverage</p>
      </article>)}</div>
      {Object.entries(data.by_area).length > 0 && <><h2 className="text-lg font-semibold mt-8">By area · 6h lead</h2>
        <div className="grid sm:grid-cols-2 gap-4 mt-4">{Object.entries(data.by_area).map(([area, s]) => <article key={area} className="border rounded-xl p-5">
          <h3 className="font-semibold">{area}</h3><p className="text-sm mt-2">Detection {percent(s.detection_rate)} · False alarms {percent(s.false_alarm_ratio)}</p>
        </article>)}</div></>}
      <p className="text-sm text-slate-500 mt-6 max-w-4xl">{data.limitations}</p>
      <p className="mt-4 text-sm text-slate-500">Research targets: ≥80% detection and ≤40% false alarms. Reaching these targets in a small sample does not establish accuracy. Thresholds remain uncalibrated; prospective monitoring must span a wet season and enough verified events.</p>
    </>}
  </div>;
}
function Stat({ label, value, interval = null }) {
  return <article className="rounded-xl border p-5"><h2 className="text-sm text-slate-500">{label}</h2>
    <p className="text-xl font-semibold mt-2">{value}</p>
    {interval && <p className="text-xs text-slate-500 mt-2">95% descriptive interval: {percent(interval[0])}–{percent(interval[1])}</p>}
  </article>;
}


function HistoricalResults() {
  const query = usePilot('/backtest');
  const [partition, setPartition] = useState('all');
  const data = query.data;
  const outcomeText = { hit: 'Day flagged', miss: 'Day not flagged', unknown: 'Not scoreable', false_alarm: 'False alarm', correct_negative: 'Correct non-flood' };
  const partitionText = { 'exploration-2024': '2024 · exploratory', 'test-2025': '2025 · reviewed during development' };
  const cases = data?.cases?.filter((item) => partition === 'all' || item.split === partition) || [];
  const summary = partition === 'all' ? data?.summary : data?.by_split?.[partition];
  return <section className="mt-8" aria-labelledby="historical-heading">
    <h2 id="historical-heading" className="text-2xl font-semibold">Historical evidence · daily comparison</h2>
    <p className="text-slate-600 mt-2">Did the rainfall screen flag a day when flooding was reported in the named area? Each forecast covers midnight to midnight Lagos time.</p>
    <DataState query={query} />
    {data && !query.isError && !data.available && <p className="mt-4">{data.message}</p>}
    {data?.available && !query.isError && <>
      {data.stale && <p role="alert" className="mt-4 rounded-lg bg-amber-100 p-4">These results are out of date because their inputs or code changed. Rerun the daily comparison before presenting them.</p>}
      <p className="mt-4 rounded-lg bg-amber-50 border border-amber-200 p-4">Historical model experiment · assistant-reviewed public reports · not validated street-level warnings.</p>
      {data.sensitivity && <section className="mt-6 rounded-xl border p-5" aria-labelledby="sensitivity-heading">
        <h3 id="sensitivity-heading" className="text-xl font-semibold">More sensitive screening</h3>
        <p className="text-sm mt-2">New live forecasts use {data.sensitivity.active_version}. Confidence: unvalidated; no flood probability percentage is available.</p>
        <div className="grid md:grid-cols-2 gap-4 mt-4">{data.sensitivity.comparisons.map((comparison) => <article key={comparison.version} className="rounded-lg bg-slate-50 p-4">
          <h4 className="font-semibold">{comparison.version === data.sensitivity.active_version ? 'Sensitive rules · active for new forecasts' : 'Original rules · comparison baseline'}</h4>
          <p className="mt-2">{comparison.summary.hits} days flagged · {comparison.summary.misses} days not flagged · {comparison.summary.unknowns} excluded</p>
          <p className="text-sm mt-2">Moderate thresholds: {Object.entries(comparison.thresholds_mm).map(([hours, limits]) => `${hours}h: ${limits[0]} mm`).join(' · ')}. High thresholds unchanged.</p>
          <p className="text-sm mt-2">August 2025: alerts on {comparison.background.alert_area_days} of {comparison.background.covered_area_days} covered area-days ({percent(comparison.background.alert_fraction)}). {comparison.background.missing_area_days} area-days lack usable forecasts.</p>
          <p className="text-sm mt-2">{comparison.background.alerts_without_reviewed_outcome} alerts have no reviewed outcome. These are unknown, not confirmed false alarms.</p>
          <details className="mt-3 text-sm"><summary className="cursor-pointer">Results for each documented case</summary>
            {comparison.cases.map((item) => <p key={`${item.storm_id}-${item.area_id}`} className="mt-2">{item.event_date} · {item.area_id} · {outcomeText[item.outcome]}{item.reason && `: ${item.reason}`}</p>)}
          </details>
        </article>)}</div>
        <p className="text-sm text-slate-600 mt-4">{data.sensitivity.interpretation}</p>
        <p className="text-sm mt-2">Always-alert comparison: {data.sensitivity.always_alert_baseline.hits} days flagged, 0 unflagged, alerts every day. Catching these known floods alone does not prove useful prediction.</p>
      </section>}
      {data.rainfall_audit && <details className="mt-5 border rounded-xl p-5">
        <summary className="cursor-pointer font-semibold">Rainfall investigation · nearby airport observations</summary>
        <p className="text-sm mt-3">{data.rainfall_audit.limitations}</p>
        {data.rainfall_audit.cases.map((item) => <div key={`${item.event_date}-${item.area_id}`} className="text-sm mt-4 border-t pt-3">
          <p className="font-medium">{item.event_date} · {item.area_id} · station {item.station_distance_km} km from representative point</p>
          {item.observations.map((observation) => <p key={observation.date} className="mt-1">{observation.date}: {observation.reported_mm == null ? 'No usable rainfall total' : `${observation.reported_mm} mm · ${observation.quality === '24h_report' ? 'reported 24-hour total' : 'partial reporting period'}`} (flag {observation.flag || 'absent'})</p>)}
        </div>)}
        <div className="flex flex-wrap gap-3 mt-4">{data.rainfall_audit.sources.map((source) => <a key={source.url} href={source.url} className="text-sm text-blue-700 underline" target="_blank" rel="noopener noreferrer">NOAA station data · {source.first_date.slice(0, 4)}</a>)}
          <a href={data.rainfall_audit.documentation} className="text-sm text-blue-700 underline" target="_blank" rel="noopener noreferrer">Quality flag definitions</a>
        </div>
      </details>}
      <h3 className="text-lg font-semibold mt-8">Original rules · detailed evidence</h3>
      <label className="block mt-5 text-sm font-medium" htmlFor="historical-partition">Evaluation period</label>
      <select id="historical-partition" value={partition} onChange={(event) => setPartition(event.target.value)} className="mt-2 rounded-lg border p-2 bg-white">
        <option value="all">All reviewed cases</option>
        {Object.keys(data.by_split).map((key) => <option key={key} value={key}>{partitionText[key] || key}</option>)}
      </select>
      {summary && <>
        <div className="grid sm:grid-cols-3 gap-4 mt-5">
          <Stat label="Documented flood cases" value={summary.flood_cases_scored} />
          <Stat label="Flood days flagged" value={summary.hits} />
          <Stat label="Flood days not flagged" value={summary.misses} />
        </div>
        <p className="mt-3 text-sm text-slate-600">{summary.independent_storms} independent storms · {summary.unknowns} cases excluded for evidence or forecast coverage.</p>
        <p className="mt-2 text-sm">{summary.status === 'insufficient_evidence' ? 'Too few independent storms for a reliability percentage. Individual results below are still meaningful.' : `Detection in this reviewed sample: ${percent(summary.detection_rate)}. This is not an overall accuracy score.`}</p>
        <p className="mt-2 text-sm">{summary.non_flood_cases_scored === 0 ? 'False alarms: not measured. No verified full-day non-flood observations are available.' : `False-alarm ratio in reviewed observations: ${percent(summary.false_alarm_ratio)}`}</p>
      </>}
      <div className="space-y-4 mt-6">{cases.map((item) => <article key={`${item.storm_id}-${item.area_id}`} className="rounded-xl border p-5 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-lg font-semibold">{item.event_date} · {item.area_id === 'lekki' ? 'Lekki' : 'Ikosi-Ketu'}</h3>
          <span className={`rounded-full px-3 py-1 text-sm font-medium ${item.outcome === 'miss' ? 'bg-red-100 text-red-900' : item.outcome === 'hit' ? 'bg-emerald-100 text-emerald-900' : 'bg-slate-100 text-slate-800'}`}>{outcomeText[item.outcome]}</span>
        </div>
        <p className="mt-2 text-sm">Observed location: {item.location}</p>
        <p className="mt-2 text-sm">{item.description}</p>
        {item.reason && <p className="mt-2 text-sm text-amber-800">{item.reason}</p>}
        {item.forecast && <>
          <p className="mt-3 text-sm text-slate-600">Simulated issue: {lagosTime(item.forecast.issued_at)} · Model initialized: {lagosTime(item.forecast.run_at)}</p>
          <div className="grid sm:grid-cols-4 gap-2 mt-3">{item.forecast.windows.map((window) => <div key={window.start_at} className="bg-slate-50 rounded-lg p-3">
            <p className="text-xs text-slate-600">{lagosTime(window.start_at)}</p>
            <p className="font-medium capitalize mt-1">{window.risk_tier} risk</p>
            <p className="text-xs mt-1">{window.rainfall_mm} mm forecast over 6h</p>
          </div>)}</div>
        </>}
        <details className="mt-4">
          <summary className="cursor-pointer font-medium text-sm">Evidence and review notes</summary>
          <p className="mt-3 text-sm">{item.review_note}</p>
          <p className="mt-2 text-xs text-slate-500">Reviewer: {item.reviewer}</p>
          {item.evidence.map((source, index) => <div key={`${source.url}-${index}`} className="mt-3 border-l-2 pl-3">
            <a className="text-sm underline text-blue-700" href={source.url} target="_blank" rel="noopener noreferrer">{source.publisher} · published {source.published_date}</a>
            <p className="text-sm mt-1">{source.finding}</p>
          </div>)}
        </details>
      </article>)}</div>
      <details className="mt-6 border rounded-xl p-4">
        <summary className="cursor-pointer font-medium">Candidate audit: {data.candidate_review.groups.length} groups reviewed</summary>
        <p className="text-sm text-slate-600 mt-3">{data.candidate_review.method}</p>
        <p className="text-sm text-slate-600 mt-2">{data.candidate_review.non_flood_review}</p>
        <div className="space-y-3 mt-4">{data.candidate_review.groups.map((group) => <div key={group.id} className="border-t pt-3 text-sm">
          <p className="font-medium">{group.start_date} to {group.end_date} · {group.status}</p>
          <p className="mt-1">{group.review_note}</p>
          {group.source_ids.map((id) => { const source = data.candidate_review.sources[id]; return <a key={id} href={source.url} target="_blank" rel="noopener noreferrer" className="inline-block mr-3 mt-1 text-blue-700 underline">{source.publisher}</a>; })}
        </div>)}</div>
      </details>
      <p className="mt-5 text-sm text-slate-600">{data.limitations}</p>
      <details className="mt-3 text-sm text-slate-500"><summary className="cursor-pointer">How this comparison works</summary><p className="mt-2">{data.protocol}</p></details>
    </>}
  </section>;
}
