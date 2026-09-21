import { ShieldAlert } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";

export default function DisclaimerBanner({ className = "" }) {
  const { t } = useLanguage();
  return (
    <div className={`flex items-start gap-3 rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-amber-900 ${className}`}>
      <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
      <p className="text-sm leading-relaxed">{t("disclaimer_full")}</p>
    </div>
  );
}