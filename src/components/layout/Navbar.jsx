import { useState } from "react";
import { Link } from "react-router-dom";
import { Waves, Menu, X } from "lucide-react";
import { useLanguage } from "@/lib/LanguageContext";
import { languageNames } from "@/lib/translations";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function Navbar() {
  const { t, lang, setLang } = useLanguage();
  const [open, setOpen] = useState(false);

  const links = [
    { to: "/map", label: t("nav_map") },
    { to: "/signup", label: t("nav_signup") },
    { to: "/agency", label: t("nav_agency") },
    { to: "/performance", label: t("nav_performance") },
    { to: "/report", label: t("nav_report") },
  ];

  return (
    <header className="border-b border-slate-100 bg-white/95 backdrop-blur sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-5 h-16 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2 shrink-0">
          <span className="w-8 h-8 rounded-lg bg-teal-800 text-white flex items-center justify-center">
            <Waves className="w-4.5 h-4.5" />
          </span>
          <span className="font-semibold text-slate-900 tracking-tight text-[15px]">{t("brand")}</span>
        </Link>

        <nav className="hidden md:flex items-center gap-6">
          {links.map((l) => (
            <Link key={l.to} to={l.to} className="text-sm text-slate-600 hover:text-teal-800 transition-colors">
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Select value={lang} onValueChange={setLang}>
            <SelectTrigger className="w-[110px] h-9 text-sm">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(languageNames).map(([code, name]) => (
                <SelectItem key={code} value={code}>{name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <button className="md:hidden p-2 text-slate-600" onClick={() => setOpen(!open)}>
            {open ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {open && (
        <nav className="md:hidden border-t border-slate-100 px-5 py-3 flex flex-col gap-3">
          {links.map((l) => (
            <Link key={l.to} to={l.to} onClick={() => setOpen(false)} className="text-sm text-slate-700">
              {l.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}