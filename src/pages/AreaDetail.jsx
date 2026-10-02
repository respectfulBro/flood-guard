import { Link, useParams } from 'react-router-dom';
import { usePilot, lagosTime } from '@/api/pilot';
import DataState from '@/components/DataState';
import RiskBadge from '@/components/risk/RiskBadge';
import DisclaimerBanner from '@/components/DisclaimerBanner';

export default function AreaDetail() {
  const { id } = useParams();
  const query = usePilot(`/areas/${encodeURIComponent(id)}`);
  const area = query.data;
  const f = area?.forecast;
  const historical = area?.data_status === 'historical';
  const fresh = area?.data_status === 'fresh';
  return <div className="max-w-4xl mx-auto px-5 py-10">
    <Link to="/map" className="text-teal-700 text-sm">← Back to Lagos map</Link>
    <DataState query={query} />
    {area && !query.isError && <>
      <div className="flex flex-wrap justify-between items-center gap-4 mt-6">
        <div><h1 className="text-3xl font-semibold">{area.name}</h1><p className="text-slate-500 mt-1">Lagos State · Candidate research area</p></div>
        <div>{historical && <p className="text-sm text-amber-900 mb-2">Historical screen · {area.event_date}</p>}<RiskBadge tier={area.risk_tier} /></div>
      </div>
      <p className="mt-5 text-slate-600">Rainfall screening, uncalibrated for local flooding. No numerical flood probability is available.</p>
      {historical && <p role="status" className="bg-amber-50 p-4 rounded-xl mt-5">Historical demo · {area.event_date}. These are cached rainfall screening results, not today’s risk. <Link className="underline" to="/replay">Explore all historical events and evidence</Link>.</p>}
      {!fresh && !historical && <p role="status" className="bg-slate-100 p-4 rounded-xl mt-5">{area.demo_message || (f ? 'This forecast is stale. Historical values below must not be read as current risk.' : 'No usable forecast has been received. Risk is unknown.')}</p>}
      {area.last_check && <p className="text-sm text-slate-500 mt-4">Last weather check: {lagosTime(area.last_check.checked_at)} · {area.last_check.success ? 'Completed' : 'Failed; awaiting a successful update'}</p>}
      {f && <>
        <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm">
          <p className="font-medium">{f.version === 'rainfall-screen-sensitive-v2' ? 'Sensitive rainfall screening · unvalidated' : 'Original rainfall screening'}</p>
          <p className="mt-2">Confidence: {f.confidence?.label || 'Flood likelihood not yet measured'}.</p>
          <p className="mt-1">{f.confidence?.reason || 'This rule has not been calibrated against a representative set of flood and non-flood observations.'}</p>
          <p className="mt-1">Low screening does not rule out flooding. Moderate/high describes a rainfall threshold crossing, not certainty that flooding will occur.</p>
        </div>
        <dl className="grid sm:grid-cols-2 gap-4 my-6 text-sm">
          <div><dt className="text-slate-500">{historical ? 'Simulated daily decision' : 'Forecast issued'}</dt><dd>{lagosTime(f.issued_at)}</dd></div>
          <div><dt className="text-slate-500">Source model initialization (metadata)</dt><dd>{lagosTime(f.source_run_at)}</dd></div>
          <div><dt className="text-slate-500">Forecast period</dt><dd>{lagosTime(f.valid_from)} – {lagosTime(f.valid_until)}</dd></div>
          <div><dt className="text-slate-500">Weather grid point</dt><dd>{f.grid_lat.toFixed(3)}, {f.grid_lng.toFixed(3)} · not a flood boundary</dd></div>
        </dl>
        <h2 className="text-lg font-semibold">Six-hour windows</h2>
        <div className="grid sm:grid-cols-2 gap-4 mt-4">{f.windows.map((w) => {
          const current = fresh && new Date(w.end_at) > new Date();
          return <article key={w.start_at} className="border rounded-xl p-5">
            <p className="text-sm text-slate-600 mb-3">{lagosTime(w.start_at)}<br />to {lagosTime(w.end_at)}</p>
            <RiskBadge tier={current || historical ? w.risk_tier : 'stale'} />
            {!current && !historical && <p className="text-xs text-slate-500 mt-2">Archived screening: {w.risk_tier}</p>}
            <p className="text-2xl font-semibold mt-4">{w.rainfall_mm} <span className="text-sm font-normal">mm forecast rain</span></p>
            <ul className="text-sm text-slate-600 mt-3 space-y-1">{w.factors.map((factor) => <li key={factor}>{factor}</li>)}</ul>
          </article>;
        })}</div>
        <p className="text-sm text-slate-500 mt-6">{f.basis}. Accumulations may include rain before a window starts. Screening version: {f.version}.</p>
      </>}
      <DisclaimerBanner className="mt-8" />
      <Link className="inline-block mt-5 text-teal-700 underline" to={`/report?area=${area.id}`}>Record flooding or a confirmed non-flood observation</Link>
    </>}
  </div>;
}
