import { useEffect, useMemo, useState } from "react";
import { base44 } from "@/api/base44Client";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { useLanguage } from "@/lib/LanguageContext";
import { format } from "date-fns";

export default function Performance() {
  const { t } = useLanguage();
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    base44.entities.AlertHistory.list("-sent_at", 100).then(setAlerts);
  }, []);

  const stats = useMemo(() => {
    const hits = alerts.filter((a) => a.outcome === "hit").length;
    const misses = alerts.filter((a) => a.outcome === "miss").length;
    const falseAlarms = alerts.filter((a) => a.outcome === "false_alarm").length;
    const pending = alerts.filter((a) => a.outcome === "pending").length;
    const hitRate = hits + misses > 0 ? Math.round((hits / (hits + misses)) * 100) : null;
    const farRate = hits + falseAlarms > 0 ? Math.round((falseAlarms / (hits + falseAlarms)) * 100) : null;
    const leadTimes = alerts.filter((a) => a.lead_time_hours != null && a.outcome !== "pending").map((a) => a.lead_time_hours);
    const avgLead = leadTimes.length ? (leadTimes.reduce((s, v) => s + v, 0) / leadTimes.length).toFixed(1) : null;
    return {
      hitRate, farRate, avgLead,
      chartData: [
        { name: t("outcome_hit"), value: hits },
        { name: t("outcome_miss"), value: misses },
        { name: t("outcome_false_alarm"), value: falseAlarms },
        { name: t("outcome_pending"), value: pending },
      ],
    };
  }, [alerts, t]);

  return (
    <div className="max-w-6xl mx-auto px-5 py-10">
      <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">{t("performance_title")}</h1>
      <p className="text-slate-600 mt-1">{t("performance_subtitle")}</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
        <StatCard label={t("performance_hit_rate")} value={stats.hitRate != null ? `${stats.hitRate}%` : "—"} />
        <StatCard label={t("performance_false_alarm")} value={stats.farRate != null ? `${stats.farRate}%` : "—"} />
        <StatCard label={t("performance_lead_time")} value={stats.avgLead != null ? stats.avgLead : "—"} />
      </div>

      <div className="mt-10 h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={stats.chartData}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#64748b" }} />
            <YAxis tick={{ fontSize: 12, fill: "#64748b" }} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" fill="#0f766e" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <h2 className="text-lg font-semibold text-slate-900 mt-10 mb-4">{t("performance_recent_alerts")}</h2>
      <div className="overflow-x-auto rounded-xl border border-slate-100">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="text-left font-medium px-4 py-3">{t("performance_table_area")}</th>
              <th className="text-left font-medium px-4 py-3">{t("performance_table_date")}</th>
              <th className="text-left font-medium px-4 py-3">{t("performance_table_outcome")}</th>
              <th className="text-left font-medium px-4 py-3">{t("performance_table_lead")}</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((a) => (
              <tr key={a.id} className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">{a.area_name}</td>
                <td className="px-4 py-3 text-slate-600">{a.sent_at ? format(new Date(a.sent_at), "PP p") : "—"}</td>
                <td className="px-4 py-3 text-slate-600">{t(`outcome_${a.outcome}`)}</td>
                <td className="px-4 py-3 text-slate-600">{a.lead_time_hours ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-100 p-5">
      <p className="text-xs text-slate-400 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-slate-900 mt-1.5">{value}</p>
    </div>
  );
}