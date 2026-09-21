import { useEffect, useState } from "react";
import { base44 } from "@/api/base44Client";
import { useLanguage } from "@/lib/LanguageContext";
import { languageNames } from "@/lib/translations";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { CheckCircle2 } from "lucide-react";

export default function Signup() {
  const { t, lang } = useLanguage();
  const urlParams = new URLSearchParams(window.location.search);
  const [areas, setAreas] = useState([]);
  const [phone, setPhone] = useState("");
  const [areaKey, setAreaKey] = useState(
    urlParams.get("area") && urlParams.get("country") ? `${urlParams.get("area")}|${urlParams.get("country")}` : ""
  );
  const [language, setLanguage] = useState(lang);
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    base44.entities.Area.list().then(setAreas);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!areaKey) return setError(t("signup_error_area"));
    if (!consent) return setError(t("signup_error_consent"));
    setError("");
    setSubmitting(true);
    const [area_name, country] = areaKey.split("|");
    await base44.entities.Registration.create({ phone_number: phone, area_name, country, language, consent, status: "pending" });
    setSubmitting(false);
    setDone(true);
  };

  if (done) {
    return (
      <div className="max-w-md mx-auto px-5 py-20 text-center">
        <CheckCircle2 className="w-12 h-12 text-teal-700 mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-slate-900">{t("signup_success_title")}</h1>
        <p className="text-slate-600 mt-2 leading-relaxed">{t("signup_success_desc")}</p>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto px-5 py-14">
      <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">{t("signup_title")}</h1>
      <p className="text-slate-600 mt-2 leading-relaxed">{t("signup_subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-5">
        <div>
          <Label>{t("signup_phone_label")}</Label>
          <Input required type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder={t("signup_phone_placeholder")} className="mt-1.5" />
        </div>

        <div>
          <Label>{t("signup_area_label")}</Label>
          <Select value={areaKey} onValueChange={setAreaKey}>
            <SelectTrigger className="mt-1.5"><SelectValue placeholder={t("signup_area_placeholder")} /></SelectTrigger>
            <SelectContent>
              {areas.map((a) => (
                <SelectItem key={a.id} value={`${a.name}|${a.country}`}>{a.name}, {a.country}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label>{t("signup_language_label")}</Label>
          <Select value={language} onValueChange={setLanguage}>
            <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
            <SelectContent>
              {Object.entries(languageNames).map(([code, name]) => (
                <SelectItem key={code} value={code}>{name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-start gap-2.5">
          <Checkbox id="consent" checked={consent} onCheckedChange={setConsent} className="mt-0.5" />
          <Label htmlFor="consent" className="text-sm leading-relaxed font-normal text-slate-600">
            {t("signup_consent_label")}
          </Label>
        </div>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <Button type="submit" disabled={submitting} size="lg" className="bg-teal-800 hover:bg-teal-900 w-full">
          {submitting ? t("signup_submitting") : t("signup_submit")}
        </Button>
      </form>
    </div>
  );
}