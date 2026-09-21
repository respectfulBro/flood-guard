import { Building2 } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";

export default function AgencyView() {
  const { t } = useLanguage();
  return (
    <div className="max-w-2xl mx-auto px-5 py-20 text-center">
      <div className="w-14 h-14 rounded-2xl bg-teal-50 text-teal-700 flex items-center justify-center mx-auto mb-6">
        <Building2 className="w-7 h-7" />
      </div>
      <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">{t("agency_title")}</h1>
      <p className="text-slate-600 mt-3 leading-relaxed">{t("agency_coming_soon_desc")}</p>
    </div>
  );
}