import { Link } from 'react-router-dom';
import { usePilot } from '@/api/pilot';
import { Button } from '@/components/ui/button';
import DisclaimerBanner from '@/components/DisclaimerBanner';
import AreaListItem from '@/components/risk/AreaListItem';
import DataState from '@/components/DataState';

export default function Home() {
  const query = usePilot('/areas');
  return <div className="max-w-6xl mx-auto px-5 py-14 md:py-20">
    <p className="text-teal-700 text-sm font-medium uppercase tracking-wide">Lagos · Private research pilot</p>
    <h1 className="text-3xl md:text-5xl font-semibold tracking-tight mt-4 max-w-3xl">Understanding the next 24 hours of rainfall risk.</h1>
    <p className="text-slate-600 mt-5 max-w-2xl leading-relaxed">Follow experimental rainfall screening for two candidate Lagos areas. We are collecting evidence to learn when heavy rain leads to flooding. Flood prediction accuracy has not yet been established.</p>
    <p className="text-sm text-amber-900 mt-4 max-w-2xl">New forecasts use more sensitive rainfall thresholds to prioritize detection. More false alarms are expected. Flood probability is not yet measured; a low screen does not rule out flooding.</p>
    <div className="flex flex-wrap gap-3 mt-8">
      <Button asChild className="bg-teal-800"><Link to="/replay">Replay a historical storm</Link></Button>
      <Button asChild variant="outline"><Link to="/performance">Strategy and results</Link></Button>
      <Button asChild variant="outline"><Link to="/report">Record an observation</Link></Button>
    </div>
    <DisclaimerBanner className="my-8 max-w-3xl" />
    <h2 className="text-lg font-semibold mb-4">Candidate research areas</h2>
    <DataState query={query} />
    {!query.isError && <div className="grid gap-3">{query.data?.map((area) => <AreaListItem key={area.id} area={area} />)}</div>}
    <p className="text-sm text-slate-500 mt-6">Weather inputs are checked hourly. A successful check does not mean a new weather model run. Nearby places can share the same weather grid cell.</p>
  </div>;
}
