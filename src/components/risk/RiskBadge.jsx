import { CircleCheck, TriangleAlert, OctagonAlert } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";

const TIER_STYLES = {
  low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  moderate: "bg-amber-50 text-amber-700 border-amber-200",
  high: "bg-rose-50 text-rose-700 border-rose-200",
};

const TIER_ICONS = { low: CircleCheck, moderate: TriangleAlert, high: OctagonAlert };

export default function RiskBadge({ tier, size = "md" }) {
  const { t } = useLanguage();
  const Icon = TIER_ICONS[tier] || CircleCheck;
  const sizeClasses = size === "lg" ? "text-sm px-3 py-1.5 gap-2" : "text-xs px-2.5 py-1 gap-1.5";
  return (
    <span className={`inline-flex items-center rounded-full border font-medium ${TIER_STYLES[tier] || TIER_STYLES.low} ${sizeClasses}`}>
      <Icon className={size === "lg" ? "w-4 h-4" : "w-3.5 h-3.5"} />
      {t(`tier_${tier}`)}
    </span>
  );
}