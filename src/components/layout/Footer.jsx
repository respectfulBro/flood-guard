import { useLanguage } from "@/lib/LanguageContext";

export default function Footer() {
  const { t } = useLanguage();
  return (
    <footer className="border-t border-slate-100 mt-12">
      <div className="max-w-6xl mx-auto px-5 py-8 text-sm text-slate-500 flex flex-col gap-2">
        <p>{t("footer_disclaimer")}</p>
        <p>Weather data: <a className="underline" href="https://open-meteo.com/">Open-Meteo</a> / ECMWF · <a className="underline" href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a></p>
        <p className="text-slate-400">© {new Date().getFullYear()} {t("footer_rights")}</p>
      </div>
    </footer>
  );
}