import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { base44 } from "@/api/base44Client";
import { Button } from "@/components/ui/button";
import { Map, MessageSquareText } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import DisclaimerBanner from "@/components/DisclaimerBanner";
import AreaListItem from "@/components/risk/AreaListItem";
import { sortByRiskDesc } from "@/lib/riskTiers";

export default function Home() {
  const { t } = useLanguage();
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    base44.entities.Area.list().then((data) => {
      setAreas([...data].sort(sortByRiskDesc).slice(0, 6));
      setLoading(false);
    });
  }, []);

  return (
    <div>
      <section className="max-w-6xl mx-auto px-5 pt-14 pb-10 md:pt-20 md:pb-14">
        <p className="text-teal-700 text-sm font-medium tracking-wide uppercase mb-4">{t("tagline")}</p>
        <h1 className="text-3xl md:text-5xl font-semibold text-slate-900 tracking-tight leading-tight max-w-2xl">
          {t("home_hero_title")}
        </h1>
        <p className="text-slate-600 mt-5 max-w-xl leading-relaxed">{t("home_hero_subtitle")}</p>
        <div className="flex flex-wrap gap-3 mt-8">
          <Button asChild size="lg" className="bg-teal-800 hover:bg-teal-900">
            <Link to="/map"><Map className="w-4 h-4 mr-2" />{t("home_cta_map")}</Link>
          </Button>
          <Button asChild size="lg" variant="outline">
            <Link to="/signup"><MessageSquareText className="w-4 h-4 mr-2" />{t("home_cta_signup")}</Link>
          </Button>
        </div>
        <DisclaimerBanner className="mt-10 max-w-2xl" />
      </section>

      <section className="max-w-6xl mx-auto px-5 pb-16">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">{t("home_quick_list_title")}</h2>
        {loading ? (
          <div className="text-sm text-slate-400">…</div>
        ) : areas.length === 0 ? (
          <p className="text-sm text-slate-500">{t("home_quick_list_empty")}</p>
        ) : (
          <div className="grid gap-2.5">
            {areas.map((area) => <AreaListItem key={area.id} area={area} />)}
          </div>
        )}
      </section>
    </div>
  );
}