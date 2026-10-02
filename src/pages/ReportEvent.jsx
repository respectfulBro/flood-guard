import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { usePilot, request } from '@/api/pilot';
import DataState from '@/components/DataState';
import { Button } from '@/components/ui/button';

const inputClass = 'block w-full border border-slate-300 rounded-lg p-3 mt-2 bg-white';
export default function ReportEvent() {
  const query = usePilot('/areas');
  const session = usePilot('/session');
  const [params] = useSearchParams();
  const [state, setState] = useState({ pending: false, error: '', id: null });
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setState({ pending: true, error: '', id: null });
    try {
      const result = await request('/reports', { method: 'POST', body: JSON.stringify({
        area_id: form.get('area_id'), flooded: form.get('flooded') === 'yes',
        start_at: `${form.get('start_at')}:00+01:00`, end_at: `${form.get('end_at')}:00+01:00`,
        cause: form.get('cause'), description: form.get('description'), source_url: form.get('source_url') || null,
      }) });
      setState({ pending: false, error: '', id: result.id });
    } catch (error) { setState({ pending: false, error: error.message, id: null }); }
  }
  return <div className="max-w-xl mx-auto px-5 py-12">
    <h1 className="text-3xl font-semibold">Record an observation</h1>
    <p className="text-slate-600 mt-3">Reports are saved for review. For a flood, enter the earliest and latest possible onset. For no flooding, enter the interval you actively observed. All times are Lagos time (WAT, UTC+1).</p>
    <p className="text-sm text-slate-600 mt-3">Use the same named street or observation point each time, including rainy days without flooding. In the evidence field, record the observer, exact location, checks made, and any gaps. Missing checks or no news reports cannot confirm a non-flood interval.</p>
    <DataState query={query} />
    {state.id ? <div role="status" className="mt-8 p-5 rounded-xl bg-teal-50">{session.data?.demo ? 'Demo report' : 'Report'} #{state.id} saved{session.data?.demo ? ' in the separate demo database' : ''}. It will be excluded from evaluation until reviewed.<button className="block underline mt-4" onClick={() => setState({ pending: false, error: '', id: null })}>Record another observation</button></div> : query.data && !query.isError && <form onSubmit={submit} className="mt-8 space-y-5">
      <label className="block text-sm font-medium">Area<select name="area_id" defaultValue={params.get('area') || ''} required className={inputClass}>
        <option value="" disabled>Select an area</option>{query.data.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
      </select></label>
      <label className="block text-sm font-medium">Observation<select name="flooded" className={inputClass}><option value="yes">Flooding occurred</option><option value="no">Confirmed no flooding during this interval</option></select></label>
      <label className="block text-sm font-medium">Earliest onset / monitoring start (WAT)<input type="datetime-local" name="start_at" required className={inputClass} /></label>
      <label className="block text-sm font-medium">Latest onset / monitoring end (WAT)<input type="datetime-local" name="end_at" required className={inputClass} /></label>
      <label className="block text-sm font-medium">Suspected cause<select name="cause" defaultValue="unknown" className={inputClass}>
        <option value="unknown">Unknown / not applicable</option><option value="rainfall">Heavy rainfall / surface runoff</option><option value="coastal">Coastal or tidal</option><option value="river">River flooding</option>
      </select></label>
      <label className="block text-sm font-medium">Location, impact, and evidence<textarea name="description" minLength={10} maxLength={3000} required rows={4} className={inputClass} /></label>
      <label className="block text-sm font-medium">Source link (optional)<input type="url" name="source_url" maxLength={2000} className={inputClass} placeholder="https://…" /></label>
      {state.error && <p role="alert" className="text-red-700">{state.error}</p>}
      <Button disabled={state.pending} className="bg-teal-800 w-full" type="submit">{state.pending ? 'Saving…' : 'Save for review'}</Button>
    </form>}
  </div>;
}
