import { useMemo, useState } from "react";
import { usePilot } from "@/api/pilot";
import DataState from "@/components/DataState";
import { Input } from "@/components/ui/input";
import { Search, Map as MapIcon, List as ListIcon } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import AreaListItem from "@/components/risk/AreaListItem";
import RiskMapView from "@/components/risk/RiskMapView";
import { sortByRiskDesc } from "@/lib/riskTiers";

export default function RiskMap() {
  const { t } = useLanguage();
  const queryState = usePilot('/areas');
  const areas = useMemo(() => [...(queryState.data || [])].sort(sortByRiskDesc), [queryState.data]);
  const [query, setQuery] = useState("");
  const [view, setView] = useState("list");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return areas;
    return areas.filter((a) => a.name.toLowerCase().includes(q) || a.country.toLowerCase().includes(q));
  }, [areas, query]);

  return (
    <div className="max-w-6xl mx-auto px-5 py-10">
      <h1 className="text-3xl font-semibold mb-3">Lagos rainfall screening</h1>
      <p className="text-slate-600 mb-6">Markers are representative research locations, not predicted flood extents. Grey means stale or unavailable data.</p>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div className="relative w-full md:max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Search research areas"
            placeholder={t("map_search_placeholder")}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1 self-start">
          <button
            onClick={() => setView("map")}
            className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md transition-colors ${view === "map" ? "bg-white shadow-sm text-slate-900" : "text-slate-500"}`}
          >
            <MapIcon className="w-4 h-4" />{t("map_view_map")}
          </button>
          <button
            onClick={() => setView("list")}
            className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md transition-colors ${view === "list" ? "bg-white shadow-sm text-slate-900" : "text-slate-500"}`}
          >
            <ListIcon className="w-4 h-4" />{t("map_view_list")}
          </button>
        </div>
      </div>

      {queryState.isPending || queryState.isError ? (
        <DataState query={queryState} />
      ) : filtered.length === 0 ? (
        <p className="text-sm text-slate-500 py-10 text-center">{t("map_no_results")}</p>
      ) : view === "map" ? (
        <><RiskMapView areas={filtered} /><p className="text-sm my-4">Map tiles need internet. Area details remain available below.</p><div className="grid gap-3">{filtered.map((area) => <AreaListItem key={area.id} area={area} />)}</div></>
      ) : (
        <div className="grid gap-2.5">
          {filtered.map((area) => <AreaListItem key={area.id} area={area} />)}
        </div>
      )}
    </div>
  );
}