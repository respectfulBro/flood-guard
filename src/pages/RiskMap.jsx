import { useEffect, useMemo, useState } from "react";
import { base44 } from "@/api/base44Client";
import { Input } from "@/components/ui/input";
import { Search, Map as MapIcon, List as ListIcon } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import AreaListItem from "@/components/risk/AreaListItem";
import RiskMapView from "@/components/risk/RiskMapView";
import { sortByRiskDesc } from "@/lib/riskTiers";

export default function RiskMap() {
  const { t } = useLanguage();
  const [areas, setAreas] = useState([]);
  const [query, setQuery] = useState("");
  const [view, setView] = useState("map");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    base44.entities.Area.list().then((data) => {
      setAreas([...data].sort(sortByRiskDesc));
      setLoading(false);
    });
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return areas;
    return areas.filter((a) => a.name.toLowerCase().includes(q) || a.country.toLowerCase().includes(q));
  }, [areas, query]);

  return (
    <div className="max-w-6xl mx-auto px-5 py-10">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div className="relative w-full md:max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
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

      {loading ? (
        <div className="text-sm text-slate-400 py-10 text-center">…</div>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-slate-500 py-10 text-center">{t("map_no_results")}</p>
      ) : view === "map" ? (
        <RiskMapView areas={filtered} />
      ) : (
        <div className="grid gap-2.5">
          {filtered.map((area) => <AreaListItem key={area.id} area={area} />)}
        </div>
      )}
    </div>
  );
}