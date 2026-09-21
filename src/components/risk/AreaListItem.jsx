import { Link } from "react-router-dom";
import { MapPin, ChevronRight } from "lucide-react";
import RiskBadge from "@/components/risk/RiskBadge";

export default function AreaListItem({ area }) {
  return (
    <Link
      to={`/area/${area.id}`}
      className="flex items-center justify-between gap-4 rounded-xl border border-slate-100 px-4 py-3.5 hover:border-teal-200 hover:bg-teal-50/40 transition-colors"
    >
      <div className="flex items-center gap-3 min-w-0">
        <MapPin className="w-4 h-4 text-slate-400 shrink-0" />
        <div className="min-w-0">
          <p className="font-medium text-slate-900 truncate">{area.name}</p>
          <p className="text-xs text-slate-500 truncate">{area.region ? `${area.region}, ` : ""}{area.country}</p>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <RiskBadge tier={area.risk_tier} />
        <ChevronRight className="w-4 h-4 text-slate-300" />
      </div>
    </Link>
  );
}