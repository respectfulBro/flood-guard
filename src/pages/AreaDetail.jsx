import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { base44 } from "@/api/base44Client";
import { ArrowLeft, MessageSquareText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/lib/LanguageContext";
import RiskBadge from "@/components/risk/RiskBadge";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import { format } from "date-fns";

export default function AreaDetail() {
  const { id } = useParams();
  const { t } = useLanguage();
  const [area, setArea] = useState(null);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    base44.entities.Area.get(id)
      .then((a) => { setArea(a); setStatus("ready"); })
      .catch(() => setStatus("not_found"));
  }, [id]);

  if (status === "loading") return <div className="max-w-2xl mx-auto px-5 py-16 text-sm text-slate-400">…</div>;
  if (status === "not_found" || !area) {
    return (
      <div className="max-w-2xl mx-auto px-5 py-16 text-center">
        <p className="text-slate-600">{t("area_not_found")}</p>
        <Link to="/map" className="text-teal-700 text-sm mt-3 inline-block">{t("area_back")}</Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-5 py-10">
      <Link to="/map" className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-teal-800 mb-6">
        <ArrowLeft className="w-4 h-4" />{t("area_back")}
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">{area.name}</h1>
          <p className="text-slate-500 text-sm mt-1">{area.region ? `${area.region}, ` : ""}{area.country}</p>
        </div>
        <RiskBadge tier={area.risk_tier} size="lg" />
      </div>

      <div className="grid grid-cols-2 gap-4 mt-8">
        <div className="rounded-xl border border-slate-100 p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">{t("area_time_window_label")}</p>
          <p className="text-slate-900 font-medium mt-1">{area.time_window || "—"}</p>
        </div>
        <div className="rounded-xl border border-slate-100 p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wide">{t("confidence_label")}</p>
          <p className="text-slate-900 font-medium mt-1">{t(`confidence_${area.confidence || "medium"}`)}</p>
        </div>
      </div>

      <div className="mt-6">
        <p className="text-xs text-slate-400 uppercase tracking-wide mb-2">{t("area_what_this_means")}</p>
        <p className="text-slate-700 leading-relaxed">{t(`tier_${area.risk_tier}_desc`)}</p>
      </div>

      <p className="text-xs text-slate-400 mt-6">
        {t("area_updated_label")}: {area.updated_date ? format(new Date(area.updated_date), "PPp") : "—"}
      </p>

      <DisclaimerBanner className="mt-8" />

      <Button asChild size="lg" className="bg-teal-800 hover:bg-teal-900 mt-6 w-full sm:w-auto">
        <Link to={`/signup?area=${encodeURIComponent(area.name)}&country=${encodeURIComponent(area.country)}`}>
          <MessageSquareText className="w-4 h-4 mr-2" />{t("area_signup_cta")}
        </Link>
      </Button>
    </div>
  );
}